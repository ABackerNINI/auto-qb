"""取数线程 + 只读视图发布(计划 §8 · M2)。

线程三段职责的最后一段落地:

- **端点线程**只入队(server.py) → **取数线程**(本模块)持站点锁抓数、解析、写盘、发布视图
  → **主循环**只读视图做判定(M3)。
- 取数线程按 `poll_interval` **自唤醒**, 与主循环 2s 节拍无关: HR 粒度是小时~天, 不需要高频
  (计划 §6/§7)。主循环从不与它同步握手 —— 需要时只 `wake()`(非阻塞), 所以抓取再慢也卡不住节拍。
- 视图只在**数据实质变化**时抬 `revision` 并原子发布(单次属性赋值 = 读方零等待);
  「是否过期」这类时间敏感判定在读取时现算, 不为时间流逝重发布。
- ❗取数线程**不碰 state_file / 任务队列 / store**(静态守阵) —— 它只读写 `hr/` 目录与视图对象。

告警节流(重要): 本项目的 WARNING 会被 notify 处理器推成**系统通知**, 而取数线程是分钟级轮询 ——
"通道不可用"这类持续状态若每轮都 WARNING, 用户会被通知淹没。故: 状态**变化**时立刻告警,
持续状态按 `channel_silence_warn` 周期提醒一次。
"""
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .resolve import HrSiteView, HrViewSet
from .service import (
    ACTION_ERROR,
    ACTION_NO_CHANNEL,
    ACTION_PARTIAL,
    ACTION_REFRESHED,
    ACTION_REUSED,
    ACTION_WAITING,
    HrRefreshResult,
    HrRefreshService,
)

logger = logging.getLogger(__name__)

#: 视为「本轮正常」的动作(不告警, 只在状态变化时记 INFO)
_OK_ACTIONS = (ACTION_REFRESHED, ACTION_REUSED, ACTION_WAITING)


def view_signature(views: HrViewSet) -> Tuple:
    """视图的**实质内容**指纹(不含 generated_at 这类每轮都变的展示字段)

    参与指纹的每一项都可能改变判定结果: 文件 revision(数据变了) / 覆盖证明 / 通道状态 /
    最近成功刷新时刻 / 清单与放行规模 / 模式。
    """
    return tuple(
        sorted(
            (
                site,
                view.revision,
                view.mode,
                view.complete,
                view.channel_state,
                round(view.last_success_ts, 3),
                len(view.by_infohash),
                len(view.verified),
            ) for site, view in views.views.items()
        )
    )


class HrViewPublisher:
    """只读视图的原子发布点(单写多读)。

    状态存在**一个元组**里, 读方一次属性读取就拿全 `(revision, signature, views)` ——
    不会出现「读到新 revision 却配旧视图」的撕裂(那会让主循环漏一次更新)。
    """

    __slots__ = ("_state", )

    def __init__(self) -> None:
        self._state: Tuple[int, Tuple, HrViewSet] = (0, (), HrViewSet.empty())

    @property
    def revision(self) -> int:
        return self._state[0]

    def latest(self) -> HrViewSet:
        return self._state[2]

    def snapshot(self) -> Tuple[int, HrViewSet]:
        """一次性取 (revision, views) —— 主循环的比较基准"""
        rev, _sig, views = self._state
        return rev, views

    def publish(self, views: HrViewSet) -> bool:
        """发布视图; 内容实质变化才抬 revision 并返回 True"""
        signature = view_signature(views)
        rev, old_sig, _old_views = self._state
        if signature == old_sig:
            return False
        self._state = (rev + 1, signature, views)
        return True


class HrWorker:
    """取数线程: 按自己的节奏驱动刷新管道, 并把结果发布成只读视图"""
    def __init__(
        self,
        *,
        service: HrRefreshService,
        publisher: HrViewPublisher,
        endpoint: Any = None,
        poll_interval: float = 60.0,
        now_fn: Callable[[], float] = time.time,
        anchors_fn: Optional[Callable[[], Mapping[str, Mapping[str, Any]]]] = None,
        name: str = "auto-qb-hr-fetch",
    ) -> None:
        self.service = service
        self.publisher = publisher
        self.endpoint = endpoint
        self.poll_interval = max(1.0, float(poll_interval))
        self._now = now_fn
        self._anchors_fn = anchors_fn
        self._name = name
        self._cond = threading.Condition()
        self._wake_seq = 0
        self._stopped = False
        self._thread: Optional[threading.Thread] = None
        self._rounds = 0
        self._last_run_ts = 0.0
        self._last_results: List[HrRefreshResult] = []
        self._last_action: Dict[str, str] = {}
        self._last_warn_at: Dict[str, float] = {}
        self._silence_warned_at = 0.0
        #: 静默告警的时间基准: 构造即记(否则「只调 run_once 不 start」的用法会拿 0 当基准, 立刻误报)
        self._started_at = self._now()

    # ---------- 生命周期 ----------

    def start(self) -> None:
        """启动线程(幂等)"""
        with self._cond:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stopped = False
            self._started_at = self._now()
            self._last_run_ts = self._now()
            self._thread = threading.Thread(target=self._loop, name=self._name, daemon=True)
        self._thread.start()
        logger.info(
            f"HR 取数线程已启动: 每 {self.poll_interval:g}s 自唤醒检查一次站点"
            f"(与主循环节拍无关); 站点: {', '.join(self.service.enabled_sites()) or '(无)'}"
        )

    def stop(self, timeout: float = 10.0) -> bool:
        """请求停止并等线程退出; 返回是否已退出

        ❗先**叫停取数通道**再等: 本线程可能在锁内阻塞等扩展回传最多 `channel.request_timeout`
        (默认 180s)。不叫停的话, 一次正常关停要白等到超时 —— 该站点在此期间被锁死,
        进程退出也被拖住。叫停后等待方立刻醒来, 本轮以「通道不可用」收尾(不计失败/熔断)。
        """
        channel_queue = getattr(self.service.fetcher, "queue", None)
        if channel_queue is not None:
            channel_queue.cancel_all("HR 取数线程正在停止")
        with self._cond:
            self._stopped = True
            self._cond.notify_all()
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        alive = thread.is_alive()
        with self._cond:
            self._thread = None if not alive else self._thread
        if not alive:
            logger.info("HR 取数线程已停止")
        else:
            logger.warning(f"HR 取数线程在 {timeout:g}s 内未退出(可能仍在等扩展回传)")
        return not alive

    def wake(self) -> None:
        """叫醒线程立刻检查一轮(**非阻塞**, 主循环绝不等它)"""
        with self._cond:
            self._wake_seq += 1
            self._cond.notify_all()

    @property
    def started(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def rounds(self) -> int:
        return self._rounds

    @property
    def last_run_ts(self) -> float:
        return self._last_run_ts

    @property
    def last_results(self) -> List[HrRefreshResult]:
        return list(self._last_results)

    # ---------- 主循环 ----------

    def _loop(self) -> None:
        while True:
            with self._cond:
                if self._stopped:
                    return
                seq = self._wake_seq
            try:
                self.run_once()
            except Exception as e:  # 单轮异常绝不打死线程(下一轮再来)
                logger.error(f"HR 取数线程单轮异常: {e}", exc_info=True)
            with self._cond:
                if self._stopped:
                    return
                # 只等「poll_interval 到点」或「被 wake() 打断」; wait_for 的谓词涵盖停止位
                self._cond.wait_for(lambda: self._stopped or self._wake_seq != seq, timeout=self.poll_interval)

    def run_once(self) -> List[HrRefreshResult]:
        """跑一轮: 逐站点刷新(站点之间互不阻塞) -> 发布视图 -> 通道静默检查"""
        anchors_by_site = self._collect_anchors()
        results: List[HrRefreshResult] = []
        for site in self.service.enabled_sites():
            result = self.service.refresh_site(site, anchors_by_site.get(site))
            results.append(result)
            self._note(site, result)
        if results:
            self.publisher.publish(self._build_views(results))
        self._check_channel_silence()
        self._rounds += 1
        self._last_run_ts = self._now()
        self._last_results = results
        return results

    # ---------- 内部 ----------

    def _collect_anchors(self) -> Mapping[str, Mapping[str, Any]]:
        """本地种子锚点(infohash -> HrAnchor): 由主循环以**不可变数据**交接

        取数线程不读 store(线程边界) —— M3 接入 TorrentRecord 后由主循环提供;
        现在没有提供者就返回空(锚点只用于「提前作废本实例放行」, 缺了不影响刷新)。
        """
        if self._anchors_fn is None:
            return {}
        try:
            return self._anchors_fn() or {}
        except Exception as e:  # 主循环侧取数失败不该影响刷新
            logger.warning(f"HR 取数线程获取本地锚点失败(本轮忽略): {e}")
            return {}

    def _build_views(self, results: List[HrRefreshResult]) -> HrViewSet:
        """本轮视图: 优先用**内存快照**(未落盘时也能反映本轮结果), 其余站点读已落盘数据"""
        views: Dict[str, HrSiteView] = dict(self.service.build_views())
        for result in results:
            if result.snapshot is not None and result.site in self.service.site_confs:
                views[result.site] = self.service.build_view_for(result.site, result.snapshot)
        return HrViewSet(views=views, generated_at=self._now())

    def _note(self, site: str, result: HrRefreshResult) -> None:
        """按「状态变化立刻记 + 持续异常周期提醒」记日志(见模块 docstring)"""
        prev = self._last_action.get(site)
        self._last_action[site] = result.action
        if result.action == prev and result.action == ACTION_WAITING:
            return  # 同一种等待态持续: 不重复记(间隔/配额未到是常态)
        if result.action in _OK_ACTIONS:
            if result.action != prev:
                logger.info(f"HR 站点 {site} | {result.action}: {result.reason or '正常'}")
            return
        now = self._now()
        warn_gap = max(60.0, float(self.service.global_conf.channel_silence_warn))
        if result.action != prev or now - self._last_warn_at.get(site, 0.0) >= warn_gap:
            self._last_warn_at[site] = now
            detail = result.reason or result.action
            # 「无可用取数通道」由 service 报过一次(每站只报一次), 这里只记状态变化免重复;
            # 持续静默的**周期提醒**交给 _check_channel_silence(它是唯一知道通道接触时间的角色)。
            # 但「刷新不完备」不同: 那可能意味着页面改版/字段缺失却不是取数失败, service 不会报
            # ⇒ 必须在这里告警(改版会让放行证明不成立, 漏了这条用户就只会看到"没数据").
            if result.action in (ACTION_PARTIAL, ACTION_ERROR):
                logger.warning(f"HR 站点 {site} | {result.action}: {detail}")
            else:
                logger.info(f"HR 站点 {site} | {result.action}: {detail}")

    def _check_channel_silence(self) -> None:
        """通道静默告警: 浏览器长期未开 / 扩展被停用 / token 配错(每 warn_gap 提醒一次)"""
        endpoint = self.endpoint
        if endpoint is None:
            return
        warn_gap = max(60.0, float(self.service.global_conf.channel_silence_warn))
        now = self._now()
        last = float(getattr(endpoint, "last_contact_ts", 0.0) or 0.0)
        reference = last or self._started_at or now
        silent = now - reference
        if silent < warn_gap:
            return
        if now - self._silence_warned_at < warn_gap:
            return  # 已提醒过, 本周期内不重复(防通知轰炸)
        self._silence_warned_at = now
        where = "启动以来" if last <= 0 else f"上次联系后"
        logger.warning(
            f"HR 取数通道已静默 {silent / 3600:.1f}h({where}扩展未联系端点): "
            "浏览器是否在运行 / 扩展是否启用 / 端点端口与 token 是否与扩展配置一致?"
        )


__all__ = ["HrViewPublisher", "HrWorker", "view_signature"]
