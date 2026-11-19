"""WebUIRuntime 伴生组件: transfer 验证中心(作业/结果队列 + daemon worker + 批次聚合)

计划 26-11-20-0127: transfer 批次的目标侧整段(add -> 验证 -> 暂停)移出主循环。
生产段(读源 -> 门 -> 导出 -> 准备)留主循环(S3 起由命令面 _cmd_transfer_run 接线), 产出的
验证作业(TransferVerifyJob)与生产段已结算结果(槽位初值, 按入参顺序混列)经本中心递交
daemon worker 串行执行(D7 FIFO), 结论经 queue.Queue 回灌, 由命令线尾部(consume_commands
尾部调 drain, D6)在主循环线程消费: 删源 -> 填槽 -> 批次齐写回执。

线程契约(黄金法则 #5, 计划 §01 底线):
- 主循环线程: submit_batch / drain / 批次聚合容器(单写者); 恒不持有目标 adapter 调用面
  (D1 隔离断言面);
- worker(daemon, 单线程): 只碰作业/结果两个队列 + 自己的批次级 adapter(D1: adapter
  批次级创建、仅线程使用, 不与主循环共用 Session; 案乙的共用形态被拒绝);
- 结论只经结果队列回灌; 删源/回执经注入端口, 消费全在主循环线程。

端口(S3 接真实, WebUIRuntime.__init__ 注入):
- 删源端口 -> 门面 _transfer_delete_source(复用 orchestrator._delete_source: torrents_delete
  delete_files=False 恒定 + store.remove_torrent; 失败兜 False+注记) —— 「验证未成不删源、
  数据文件永不删」不变量保持在 orchestrator 单点; stop 置位后删源意图一律丢弃(绝不自动删源);
- 回执端口 -> 门面 _transfer_receipt(与命令 handler 自写回执同面 set_result, 无 cmd_id 不写)
  —— transfer_run 在 DEFERRED_RECEIPT_COMMANDS, drain 命令分发层不补写, 终态回执只经本端口。

关停(D4a): 退出不 join —— stop Event 让轮询等待即时醒(Event.wait(poll_interval)):
空闲等待与在途验证的轮询 sleep 都挂在 stop Event 上, stop 置位后等待即时返回。stop 只
保证「作业队列余量不再处理」; **在途作业自然结算、结论仍回灌**, 回执是否落取决于主循环
是否再 drain(进程随即退出时即等效「作废/不写」, 与今天进程崩溃一致); 验证任务/删除意图
不持久化(重启不续跑)。stop 已接进 web 停止序列(WebUIModule.stop, S4), 并在 stop 时枚举
「已验证成功但删源未完成」的槽位逐条 WARNING(丢弃清单, 见 stop()/_warn_delete_pending)。

回执契约(D5): 单段终态回执形状不变 —— drain 组装的 truth 与命令面 handler 现行
{results(按入参顺序), summary, target} 逐字节同形, 前端零改动。

兜底双保险(§07 行 1「线程死 -> 结论永不到 -> 回执挂死」):
- worker 循环级全异常捕获 -> 合成 UNEXPECTED 结果回灌(线程保活, 结论必达);
- drain 对「全局无结论产出超过预算」的未结算槽位按 VERIFY_TIMEOUT 口径兜底结算并记
  WARNING(最后防线: 连回灌都失败的病理性场景; 预算按验证轮询口径估算、随串行深度缩放,
  判定与单种子墙钟解耦 —— 见 _force_settle_aged)。
"""
import logging
import math
import queue
import threading
from dataclasses import dataclass, field, replace
from itertools import count
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Sequence, Tuple, Union, cast

from ..core.qbclient import REQUESTS_TIMEOUT
from ..infra.clock import SYSTEM_CLOCK, Clock
from ..transfer.adapters import DownloaderAdapter, create_adapter
from ..transfer.orchestrator import (
    TorrentTransferResult,
    TransferOutcomeCode,
    TransferOrchestrator,
    TransferStatus,
    TransferVerifyJob,
    _join_notes,
)

if TYPE_CHECKING:  # 仅注解用途: 运行期不需要
    from ..config.models import TransferTargetConfig
    from ..core.qbapi import QbApi

logger = logging.getLogger(__name__)

# 超龄兜底的单次 HTTP 最坏墙钟(秒): 验证轮询的 find 与 add/pause 各是一次 qB HTTP, 最坏
# connect+read = REQUESTS_TIMEOUT 之和(单点 core.qbclient.REQUESTS_TIMEOUT, import 钉住
# 防漂移)。超龄预算按轮询口径由此估算(见 _force_settle_aged) —— 宁晚勿早: 过早兜底会把
# 还在正常推进的批次误写成 VERIFY_TIMEOUT 失败, 比回执晚到严重得多(黄金法则 2)。
_SEED_HTTP_WORST_S = float(REQUESTS_TIMEOUT[0] + REQUESTS_TIMEOUT[1])


def _unwired_delete_port(source_hash: str) -> bool:
    """S2 占位删源端口(构造默认, 测试替身面; 生产真实端口已接线): 恒 False(源保留)

    生产真实端口已接线(WebUIRuntime.__init__ 注入 delete_port=_transfer_delete_source,
    复用 orchestrator._delete_source -> qbapi.torrents_delete(delete_files=False) 含
    store.remove_torrent 快照摘除), 生产路径永不触达本占位; 本函数只在未注入端口的
    构造面(测试替身)被调到。契约 = True 已删 / False 删失败(结果按「源删除失败,
    源已保留」注记, 与 run_batch 同口径; 未知 hash 的静默无操作也返 True —— qB 对
    不存在 hash 回 200)。
    """
    logger.warning("transfer: 删源端口为构造默认占位(生产真实端口已接线), 源未删 %s", source_hash)
    return False


def _unwired_receipt_port(cmd_id: str, payload: dict) -> None:
    """S2 占位回执端口(构造默认, 测试替身面; 生产真实端口已接线): 落 WARNING 不写回执

    生产真实端口已接线(WebUIRuntime.__init__ 注入 receipt_port=_transfer_receipt,
    与命令 handler 自写回执同面 set_result(cmd_id, "ok", truth=payload)), 生产路径
    永不触达本占位; 本函数只在未注入端口的构造面(测试替身)被调到。
    """
    logger.warning("transfer: 回执端口为构造默认占位(生产真实端口已接线), 批次回执未写 cmd_id=%r", cmd_id)


@dataclass(frozen=True)
class _QueuedJob:
    """作业队列条目(worker 侧消费): 批次键 + 目标配置(建批次级 adapter 用) + 验证作业

    slot_idx: 该作业在批次槽位数组中的下标(S3: 槽位数组 = 入参顺序混合列, 已结算槽位
    作初值占位, 结论按此下标落槽 —— 单 worker FIFO 下结论回灌序 = 作业递交序, 显式
    下标保证交错入参顺序下的槽位对应关系)。
    """

    batch_key: str
    target: "TransferTargetConfig"
    job: TransferVerifyJob
    slot_idx: int


@dataclass
class _SlotState:
    """批次内单槽位(主循环线程唯一读写): 入参 hash(回执键)/源 hash(删源操作键)

    hash 与 source_hash 分置(S1 双 hash 语义): 回执键恒用入参 hash, 删源操作键用源
    maindata hash(与 run_batch 的 _delete_source(stage.source_hash) 同口径)。
    生产段已结算槽位(S3 槽位初值)source_hash 恒空串且 keep_source 置 True —— 未验证
    成功路径不碰源(不变量 2), keep_source 闸让它永不进删源分支。
    source_deleted: 删源意图是否已成功执行(主循环单写者)。None/False = 未删(删源未
    尝试/端口失败/stop 丢弃), True = 已删 —— stop 丢弃清单的判定面(_warn_delete_pending)。
    """

    hash: str
    source_hash: str
    keep_source: bool
    result: Optional[TorrentTransferResult] = None
    source_deleted: bool = False


@dataclass
class _BatchRecord:
    """批次聚合条目(容器键 -> 槽位数组/剩余计数; 主循环线程单写者, 黄金法则 #5)

    批次 = 任务分组(D3a): 多批次自然共存, 与今天命令串行的最终语义等价(单 worker FIFO)。
    remaining 只计验证作业槽位(已结算槽位随初值入账, 不计)。
    """

    key: str
    cmd_id: str
    target_name: str
    slots: List[_SlotState]
    remaining: int
    enqueued_ts: float  # 入队时刻(仅诊断/日志; 超龄判定走全局 _last_progress_ts 信号)
    retry: List[Tuple[int, TorrentTransferResult]] = field(default_factory=list)
    receipt_retry: bool = False


class TransferVerifyCenter:
    """transfer 验证中心: 作业/结果队列 + 单 daemon worker + 批次聚合容器(计划 26-11-20-0127)

    - 作业队列/结果队列: queue.Queue 线程安全 handoff, 结论只经队列回灌, 消费全在主循环;
    - 单 daemon worker: FIFO 逐种子(D7 串行), stop Event 驱动轮询等待(即时醒), 退出不
      join(D4a); 懒启动 —— 首个批次递交时拉起(快路径批次不递交, 不启动, 零空闲线程);
    - 批次聚合容器: cmd_id -> 槽位数组/剩余计数(主循环单写者), 槽位数组按入参顺序
      (S3: 已结算结果作槽位初值 + 验证作业混列), 批次记入队时刻(诊断);
      超龄兜底判定走全局「最近结论产出」信号(见 _force_settle_aged);
    - 删源计数(_deleted_this_drain): 本轮 drain 成功删源的槽位数, drain() 返回值据此并入
      consume_commands 的 cmd_changed_state(D6, 白享 P0-5 立即补刷新);
    - 可注入面: adapter 工厂 / 验证 runner / 删源端口 / 回执端口 / 时钟 / 超时参数 ——
      测试注入替身, 零新增配置键(黄金法则 #4, verify_timeout/poll_interval 维持
      orchestrator 构造常量口径)。生产默认端口接线见模块 docstring(S3)。
    """
    def __init__(
        self,
        *,
        adapter_factory: Optional[Callable[["TransferTargetConfig"], "DownloaderAdapter"]] = None,
        verify_runner: Optional[Callable[["DownloaderAdapter", TransferVerifyJob], TorrentTransferResult]] = None,
        delete_port: Optional[Callable[[str], bool]] = None,
        receipt_port: Optional[Callable[[str, dict], None]] = None,
        verify_timeout: float = 10.0,
        poll_interval: float = 0.5,
        overage_seed_budget: Optional[float] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._adapter_factory = adapter_factory or create_adapter
        self._verify_runner = verify_runner
        self._delete_port = delete_port or _unwired_delete_port
        self._receipt_port = receipt_port or _unwired_receipt_port
        self._verify_timeout = float(verify_timeout)
        self._poll_interval = float(poll_interval)
        # 超龄兜底的每槽位预算(秒): None = 按验证轮询口径自算(见 _force_settle_aged);
        # 测试注入收紧窗口(假钟推进不真等)
        self._overage_seed_budget = None if overage_seed_budget is None else float(overage_seed_budget)
        # 取时注入(D8 同款): 超龄判定是时长测量, 走 monotonic 语义(取时纪律见 infra/clock.py)
        self._clock = SYSTEM_CLOCK if clock is None else clock
        self._jobs: "queue.Queue" = queue.Queue()
        self._results: "queue.Queue" = queue.Queue()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._anon_seq = count(1)  # 空 cmd_id 的容器键合成序号(批次键唯一性)
        self._batches: Dict[str, _BatchRecord] = {}
        # 全局最近一次结论产出时刻(主循环单写者): 递交时容器无未结算工作则重置为递交
        # 时刻(空闲间隔不计入), 每次成功填槽刷新 —— 超龄兜底的判定信号(见
        # _force_settle_aged); None = 尚无参照(未递交过任何批次)
        self._last_progress_ts: Optional[float] = None
        # 本轮 drain 成功删源的槽位数(主循环单写者): drain() 入口清零, _fill_slot 删源
        # 成功时累加 —— 返回值并入 cmd_changed_state(D6, P0-5 立即补刷新)
        self._deleted_this_drain = 0
        # ---- worker 线程私面(主循环不读不写) ----
        # 批次级 adapter 缓存: FIFO 下同批作业连续入队(单生产者=主循环), 键变化即批次
        # 边界; 旧引用交给 GC。工厂异常按单种子兜底结算, 不缓存失败(下一作业重试工厂)。
        self._cur_adapter_key: Optional[str] = None
        self._cur_adapter: Optional["DownloaderAdapter"] = None
        # 默认 runner 的 worker 侧编排器: run_verify_job 不读 qb_api(只走 adapter),
        # sleep 挂 stop Event —— 在途验证的轮询等待也能即时醒(D4a), 不会拖住关停
        self._worker_orchestrator = TransferOrchestrator(
            cast("QbApi", None),  # run_verify_job 全程只用 adapter, qb_api 恒不触
            sleep=self._stop_wait_seconds,
            verify_timeout=self._verify_timeout,
            poll_interval=self._poll_interval,
        )

    def _stop_wait_seconds(self, seconds: float) -> None:
        """worker 侧验证轮询的 sleep 注入: 挂 stop Event —— stop 置位后等待即时醒(D4a)"""
        self._stop_event.wait(seconds)

    # ------------------------------------------------------------------ 主循环侧: 递交批次

    def submit_batch(
        self,
        cmd_id: str,
        target: "TransferTargetConfig",
        entries: Sequence[Union[TorrentTransferResult, TransferVerifyJob]],
    ) -> str:
        """递交一个批次(S3 生产段产出后调, 主循环线程调用): 已结算结果 + 验证作业按入参顺序混列

        entries = produce_transfer_job 的逐种子产出按入参顺序收集(TorrentTransferResult =
        生产段已结算终态, 作槽位初值入账不计剩余; TransferVerifyJob = 验证作业, 进作业队列)。
        批次聚合容器登记(cmd_id -> 槽位数组(= entries 顺序)/剩余计数)并记入队时刻, 作业逐条
        进作业队列(线程安全 handoff)。返回容器键(= cmd_id; 空则合成 anon-N —— 回执仍用原
        cmd_id, 合成键只为容器唯一性)。
        entries 为空 / 含 SUCCESS 状态的已结算条目 / 全部已结算(无验证作业)属命令面编程
        错误(空批与全批已结算应走快路径现场结算 —— 快路径判据单点在命令面; 已结算条目恒
        是未验证成功的终态, SUCCESS 必须走 worker 侧结算+删源), 按 fail-fast 抛 ValueError。
        已 stop 后递交: 丢弃(WARNING, 返回 "") —— 关停期新批次不入账; 在途作业的语义见
        stop()。
        """
        entry_list = list(entries)
        if not entry_list:
            raise ValueError("transfer: submit_batch 收到空条目列表(空批次应走快路径, 不入中心)")
        if any(not isinstance(e, TransferVerifyJob) and e.status is TransferStatus.SUCCESS for e in entry_list):
            raise ValueError(
                "transfer: submit_batch 收到 SUCCESS 状态的已结算条目"
                "(已结算条目恒是未验证成功的终态; SUCCESS 必须走 worker 侧结算+删源,"
                "作槽位初值会被 keep_source 闸静默禁删源)"
            )
        jobs = [e for e in entry_list if isinstance(e, TransferVerifyJob)]
        if not jobs:
            raise ValueError("transfer: submit_batch 无验证作业(全批已结算应走快路径, 不入中心)")
        if self._stop_event.is_set():
            logger.warning("transfer: 中心已停止, 批次作业丢弃(cmd_id=%r, %d 个)", cmd_id, len(jobs))
            return ""
        self.start()
        # 超龄判定起点(全局最近结论产出, 见 _force_settle_aged): !必须在登记本批**之前**
        # 判定 —— 递交前容器无未结算工作 -> 重置为递交时刻, 空闲间隔不计入 stalled(否则
        # 距上次产出超预算的下一次递交会在首个 drain 被立即整体兜底, 非病理性场景被误伤,
        # 违背宁晚勿早); 容器已有未结算工作则不重置: 那些槽位的等待起点不变(防挂死计时
        # 不被新递交洗掉; 新作业排在其后, 深度放大 bound, 仍是保守方向)。登记后再判恒为
        # 「有未结算」(本批自己的槽位), 重置会永不触发。
        if not any(b.remaining for b in self._batches.values()):
            self._last_progress_ts = self._clock.monotonic()
        key = cmd_id if cmd_id else f"anon-{next(self._anon_seq)}"
        slots: List[_SlotState] = []
        queued: List[_QueuedJob] = []
        for entry in entry_list:
            if isinstance(entry, TransferVerifyJob):
                slots.append(
                    _SlotState(
                        hash=str(entry.hash), source_hash=str(entry.source_hash), keep_source=bool(entry.keep_source)
                    )
                )
                queued.append(_QueuedJob(batch_key=key, target=target, job=entry, slot_idx=len(slots) - 1))
            else:
                # 生产段已结算槽位作初值(按入参顺序占位, D5 truth 按入参顺序): 该槽位未经验
                # 证成功, 不变量 2(不成功路径不碰源)要求永不删源 —— keep_source 置 True 复用
                # _fill_slot 的删源闸, source_hash 留空(无删源操作键可用)
                slots.append(_SlotState(hash=str(entry.hash), source_hash="", keep_source=True, result=entry))
        self._batches[key] = _BatchRecord(
            key=key,
            cmd_id=cmd_id,
            target_name=str(getattr(target, "name", "") or ""),
            slots=slots,
            remaining=len(jobs),
            enqueued_ts=self._clock.monotonic(),
        )
        for item in queued:
            self._jobs.put(item)
        settled_n = len(entry_list) - len(jobs)
        logger.info(
            "transfer: 批次已递交后台验证 cmd=%s(验证作业 %d 个%s)",
            key,
            len(jobs),
            f", 生产段已结算 {settled_n} 个随槽位初值" if settled_n else "",
        )
        return key

    def start(self) -> None:
        """拉起单 daemon worker(幂等: 已在跑不重拉; 懒启动, 首个批次递交时才有线程)"""
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._worker_loop, name="transfer-verify-worker", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        """请求 worker 停止(stop Event 即时醒; 退出不 join —— D4a): S4 已接进 web 停止序列

        实际语义(代码即真相): stop 只保证「作业队列余量不再处理」与「所有轮询等待即时
        返回」; **在途作业自然结算、结论仍回灌**, 回执是否落取决于主循环是否再 drain ——
        进程随即退出时才等效「作废/不写」(daemon 线程随进程终灭, 与今天进程崩溃一致)。
        幂等: 重复调用无副作用 —— 首次 stop 即落丢弃清单 WARNING(warned-once), 重复
        stop 不再枚举再记。

        S4 附加面(调用即生效, 不 join 不阻塞):
        - stop 后任何路径不得删源: _fill_slot 的删源闸检查 stop Event —— 删除意图一律
          丢弃, 重启不重放(保守默认: 绝不自动删源);
        - 已验证成功但删源未完成的槽位逐条 WARNING(「目标已建, 源未删, 请手动处置」,
          D4a/§07 行 4), 见 _warn_delete_pending。在途验证的结论在 stop 之后才回灌,
          不在本清单(与「回执不写」同族, 进程退出即作废)。
        """
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self._warn_delete_pending()

    def _warn_delete_pending(self) -> None:
        """关停丢弃清单(D4a/§07 行 4): 已验证成功但删源未完成的槽位逐条 WARNING

        三个枚举面按槽位互斥(同一槽位的结论只会出现在其中一处):
        - 容器槽位已填(结论已被 drain 消费): 删源已在填槽前执行过 —— 仅端口返 False
          (源保留, source_deleted 仍 False)的算「未完成」; 端口返 True 的已删, 不在清单;
        - 批次重试列表(结算时删源端口抛异常): 删源未完成 —— 等待重试的删除意图一并丢弃;
        - 结果队列在途(结论已回灌但主循环尚未消费): 删源从未开始 —— 在 mutex 内快照枚举
          (queue.Queue 内部落锁面, 只读不消费, 不改回灌语义)。!批次不在容器(典型 = 已被
          超龄兜底结算摘除、真实结论迟回灌)时 keep_source 不可考, SUCCESS 一律保守告警
          —— 宁多勿漏, 双份做种残留不得逃过本清单。
        keep_source 槽位与生产段已结算槽位(keep_source 置 True)不在清单 —— 保留源是意图内。
        """
        warned = 0
        for batch in self._batches.values():
            for slot in batch.slots:
                if (
                    slot.result is not None and slot.result.status is TransferStatus.SUCCESS and
                    not slot.keep_source and not slot.source_deleted
                ):
                    logger.warning("transfer: 关停丢弃删除意图 %s: 目标已建, 源未删, 请手动处置", slot.hash)
                    warned += 1
            for idx, result in batch.retry:
                if (
                    0 <= idx < len(batch.slots) and result.status is TransferStatus.SUCCESS and
                    not batch.slots[idx].keep_source
                ):
                    logger.warning("transfer: 关停丢弃删除意图 %s: 目标已建, 源未删, 请手动处置", result.hash)
                    warned += 1
        with self._results.mutex:
            inflight = list(self._results.queue)
        for batch_key, slot_idx, result in inflight:
            if result.status is not TransferStatus.SUCCESS:
                continue
            pending = self._batches.get(batch_key)
            if pending is not None and 0 <= slot_idx < len(pending.slots) and pending.slots[slot_idx].keep_source:
                continue  # 保留源是意图内(批次在场才可考; 不在则保守告警)
            logger.warning("transfer: 关停丢弃删除意图 %s: 目标已建, 源未删, 请手动处置", result.hash)
            warned += 1
        if warned:
            logger.warning("transfer: 关停共丢弃删除意图 %d 条(重启不重放, 绝不自动删源)", warned)

    # ------------------------------------------------------------------ worker 侧(daemon 线程)

    def _worker_loop(self) -> None:
        """单 daemon worker 主循环: stop Event 驱动轮询等待, FIFO 逐种子

        循环结构(计划 §03 / §07 行 1):
        - 空闲等待 = stop Event 的 Event.wait(poll_interval) —— stop 置位即时醒(返回
          True 即退出), 未置位则到拍泵一次队列;
        - 逐种子 try/except 兜底(_settle 内) —— 单种子异常合成 UNEXPECTED 结果回灌;
        - 循环级再套全异常捕获 —— 兜住逐种子兜底之外的病理性异常(如回灌本身失败),
          同样合成 UNEXPECTED 回灌, 防「线程死 -> 结论永不到 -> 回执挂死」; 它之后的
          最后防线才是主循环的超龄兜底(drain._force_settle_aged)。
        stop 置位后: 泵内即时停 —— 队列余量不再处理; 在途作业自然结算、结论仍回灌
        (回执是否落取决于主循环是否再 drain, 见 stop() docstring, D4a)。
        """
        while not self._stop_event.wait(self._poll_interval):
            item: Optional[_QueuedJob] = None
            try:
                while not self._stop_event.is_set():
                    try:
                        item = self._jobs.get_nowait()
                    except queue.Empty:
                        item = None
                        break
                    self._settle(item)
                    item = None  # 已回灌恰一条结论, in-flight 标记复位
            except Exception as exc:  # noqa: BLE001 —— 循环级兜底: 线程保活, 结论必达
                logger.error("transfer: 验证 worker 循环级异常(合成 UNEXPECTED 回灌)", exc_info=True)
                if item is not None:
                    try:
                        self._push_result(
                            item.batch_key,
                            item.slot_idx,
                            TorrentTransferResult(
                                item.job.hash,
                                TransferStatus.FAILED,
                                f"worker 循环级异常({exc})",
                                TransferOutcomeCode.UNEXPECTED,
                            ),
                        )
                    except Exception:  # noqa: BLE001 —— 最后防线: 交给超龄兜底结算
                        logger.critical("transfer: worker 循环级异常的合成结论回灌也失败 %s", item.job.hash, exc_info=True)

    def _settle(self, item: _QueuedJob) -> None:
        """单种子执行 + 回灌(恰产出一条结论; 任何异常都合成 UNEXPECTED, 不外抛)"""
        try:
            result = self._run_job(item)
        except Exception as exc:  # noqa: BLE001 —— 单种子兜底, 批次继续(run_batch D6 同口径)
            logger.error("transfer: 验证作业 %s 未预期异常", item.job.hash, exc_info=True)
            result = TorrentTransferResult(
                item.job.hash, TransferStatus.FAILED, f"未预期异常({exc})", TransferOutcomeCode.UNEXPECTED
            )
        self._push_result(item.batch_key, item.slot_idx, result)

    def _run_job(self, item: _QueuedJob) -> TorrentTransferResult:
        """worker 侧单种子: 取/建批次级 adapter -> orchestrator.run_verify_job(作业进结果出)"""
        adapter = self._adapter_for(item)
        runner = self._verify_runner or self._worker_orchestrator.run_verify_job
        return runner(adapter, item.job)

    def _adapter_for(self, item: _QueuedJob) -> "DownloaderAdapter":
        """批次级 adapter(仅 worker 线程调用, D1): 批次切换即换新, 旧引用交给 GC

        FIFO 下同批作业连续入队(单生产者 = 主循环线程), 「键变化即批次边界」成立;
        即便未来出现多生产者交错, 语义仍正确(每个实例仍只被 worker 单线程使用),
        只是可能多建几次连接。!工厂调用先于缓存改写: 工厂抛异常时缓存键与实例都保持
        原值, 本作业按单种子兜底结算(UNEXPECTED), 同批下一作业自然重试工厂 —— 缓存
        失败(把键先写进去)会让后续作业静默复用上一批次的旧 adapter, 把种子
        add/verify 到错误目标。
        """
        if self._cur_adapter_key != item.batch_key or self._cur_adapter is None:
            adapter = self._adapter_factory(item.target)  # 先建 —— 抛异常则缓存原样不动
            self._cur_adapter_key = item.batch_key
            self._cur_adapter = adapter
        return self._cur_adapter

    def _push_result(self, batch_key: str, slot_idx: int, result: TorrentTransferResult) -> None:
        """结论回灌(线程安全 handoff; 消费全在主循环 drain; 槽位下标随结论携带)"""
        self._results.put((batch_key, slot_idx, result))

    # ------------------------------------------------------------------ 主循环侧: 消费回灌(命令线尾部)

    def drain(self) -> bool:
        """收结果 -> 删源 -> 填槽 -> 批次齐写回执; 超龄批次兜底结算(主循环线程调用)

        返回本轮是否有删源动作成功执行: 删源改了 qB 种子状态, 消费方(consume_commands
        尾部)据此并入 cmd_changed_state(D6)白享 P0-5 立即补刷新 —— 与命令面的
        RESYNC_COMMANDS 同判据; 删源失败(端口 False)/stop 丢弃/纯回执不算。
        消费挂点 = consume_commands 尾部(D6): 每轮必跑、暂停分支也跑 —— run_command_line
        在暂停判断之前(qbmanager.py:597-602 先命令后 continue 的既有形态)。逐结果
        try/except(§07 行 5): 单条失败不影响其余, 异常轮次下轮重试同一槽位; 批次计数只
        由主循环改。
        """
        self._deleted_this_drain = 0
        self._retry_receipts()
        self._settle_retries()
        self._collect_results()
        self._force_settle_aged()
        return self._deleted_this_drain > 0

    def _retry_receipts(self) -> None:
        """回执端口写失败的批次重写(§07 行 5: 回执写入抛异常 -> 下轮重试)"""
        for batch in list(self._batches.values()):
            if batch.receipt_retry:
                self._complete_if_ready(batch)

    def _settle_retries(self) -> None:
        """上轮结算异常的槽位重试(槽位下标固定; 槽位已被兜底结算的迟到重试丢弃)"""
        for batch in list(self._batches.values()):
            if not batch.retry:
                continue
            pending = batch.retry
            batch.retry = []
            for idx, result in pending:
                if idx >= len(batch.slots) or batch.slots[idx].result is not None:
                    continue
                self._fill_slot(batch, idx, result)

    def _collect_results(self) -> None:
        """收全部回灌结论, 按结论携带的槽位下标逐条结算

        单 worker FIFO ⇒ 结论序 = 作业递交序; S3 槽位数组按入参顺序(已结算槽位作初值),
        下标由作业条目显式携带(_QueuedJob.slot_idx) —— 混列入参下槽位对应关系不依赖游标。
        """
        while True:
            try:
                batch_key, slot_idx, result = self._results.get_nowait()
            except queue.Empty:
                return
            batch = self._batches.get(batch_key)
            if batch is None:
                # 批次已被兜底结算移除: 迟到结论无槽可落, 丢弃(DEBUG; 兜底回执已给出终态)
                logger.debug("transfer: 迟到结论丢弃(批次不在容器) %s/%s", batch_key, result.hash)
                continue
            if not 0 <= slot_idx < len(batch.slots):
                logger.warning("transfer: 结论槽位越界(不变量破), 丢弃 %s/%s", batch_key, result.hash)
                continue
            if batch.slots[slot_idx].result is not None:
                # 重复结论(不变量破): 已有终态的槽位不覆盖, 丢弃并留痕
                logger.warning("transfer: 重复结论(不变量破), 丢弃 %s/%s", batch_key, result.hash)
                continue
            self._fill_slot(batch, slot_idx, result)

    def _fill_slot(self, batch: _BatchRecord, idx: int, result: TorrentTransferResult) -> None:
        """单条结算: 成功且未保留源 -> 经删除端口删源 -> 填槽 -> 批次齐写回执

        删除失败不翻已成功的转移, 只补注记「源删除失败, 源已保留」(与 run_batch 同
        口径, issue 26-11-03-0824)。stop 置位后删源意图一律丢弃(D4a: 关停绝不删源,
        丢弃清单由 stop() 落 WARNING), 槽位照常填、回执照常齐(是否落取决于主循环是否
        再 drain)。本函数内任何异常(删源端口抛出等)都不填槽 —— 条目进批次重试列表,
        下轮 drain 重试同一槽位(§07 行 5); 槽位下标在递交时已定, 重试不改变它与后续
        结果的槽位对应关系。
        """
        try:
            slot = batch.slots[idx]
            if (result.status is TransferStatus.SUCCESS and not slot.keep_source and not self._stop_event.is_set()):
                if self._delete_port(slot.source_hash):
                    slot.source_deleted = True
                    self._deleted_this_drain += 1
                else:
                    result = replace(result, reason=_join_notes(result.reason, "源删除失败, 源已保留"))
            slot.result = result
            batch.remaining -= 1
            # 结论产出 = 进展: 刷新全局判定时刻(超龄兜底的信号源, 见 _force_settle_aged);
            # 异常路径(进重试列表)不算进展, 不刷新
            self._last_progress_ts = self._clock.monotonic()
            self._complete_if_ready(batch)
        except Exception as exc:  # noqa: BLE001 —— 单条失败不影响其余(§07 行 5)
            batch.retry.append((idx, result))
            logger.warning("transfer: 结论结算异常, 下轮重试同一槽位 %s/%s: %s", batch.key, result.hash, exc)

    def _complete_if_ready(self, batch: _BatchRecord) -> None:
        """批次齐(剩余计数归零) -> 组装回执经端口写出(单段终态, 形状与命令面 handler 逐字节同形)

        truth = {results(按入参顺序), summary{success, skipped, failed}, target} ——
        与 commands._cmd_transfer_run 现行形状一致(D5: 前端零改动)。写出失败不摘批次,
        下轮 drain 重试(§07 行 5)。
        """
        if batch.remaining > 0:
            return
        summary = {status.value: 0 for status in TransferStatus}
        results: List[TorrentTransferResult] = []
        for slot in batch.slots:
            result = slot.result
            if result is None:
                # 不变量破(剩余计数归零恒有结论 —— 计数只随填槽递减): 不应到达; 不写回执
                # 不摘批次, 留待下轮 drain 重试
                logger.error("transfer: 批次槽位缺结论(不变量破), 本轮不写回执 %s/%s", batch.key, slot.hash)
                return
            results.append(result)
            summary[result.status.value] += 1
        payload = {
            "results": [r.to_receipt() for r in results],
            "summary": summary,
            "target": batch.target_name,
        }
        try:
            self._receipt_port(batch.cmd_id, payload)
        except Exception as exc:  # noqa: BLE001 —— 回执写入抛异常: 下轮 drain 重试
            batch.receipt_retry = True
            logger.warning("transfer: 批次回执写出失败, 下轮重试 %s: %s", batch.key, exc)
            return
        # 批次生命周期日志(S4: 结算, 批次口径 —— 逐条结果回执自带, 不逐条刷屏)
        logger.info(
            "transfer: 批次结算完成 cmd=%s target=%s: 成功 %d / 跳过 %d / 失败 %d",
            batch.cmd_id,
            batch.target_name,
            summary["success"],
            summary["skipped"],
            summary["failed"],
        )
        self._batches.pop(batch.key, None)

    def _force_settle_aged(self) -> None:
        """全局无结论产出超预算的未结算槽位按 VERIFY_TIMEOUT 口径兜底结算 + WARNING(§07 行 1)

        防线定位: worker 循环级兜底之后的最后防线(线程被杀 / 卡死 / 合成回灌也失败的
        病理性场景)。
        - 判定信号 = 「全局最近一次结论产出以来的时长」(_last_progress_ts, 递交时容器无
          未结算工作则重置为递交时刻 —— 空闲间隔不计入; 每次成功填槽刷新): 单 worker
          全局 FIFO 下, 任何批次的产出都证明 worker 活着且本批作业终会被处理 —— 只盯
          「worker 是否还在产出」, 与单种子墙钟解耦, 慢而活着的目标(每轮 find 都顶满
          HTTP 超时)不会被误判(宁晚勿早, 黄金法则 2)。
        - 预算按验证轮询口径估算、随串行深度缩放:
            bound = budget x total_unsettled
            budget = (ceil(verify_timeout / poll_interval) 次 find + add + pause) x 单轮
                     HTTP 最坏(_SEED_HTTP_WORST_S, 对齐 REQUESTS_TIMEOUT)
                     + 轮询 sleep 墙钟(rounds x poll_interval, verify_timeout 本身)
          深度 = 容器内未结算槽位总数(本批结论被其它批次的在途作业串行延迟的面, 也在
          预算内)。
        - 触发时容器内全部未结算槽位一起兜底(全局信号下无法按批区分 —— worker 卡死时
          全体挂)。兜底结算按「验证超时」口径落 FAILED/VERIFY_TIMEOUT(与
          orchestrator._verify 的超时文案同形), 源一律不删(不成功路径不碰源); 批次随之
          结算出回执并摘除, 迟到结论由 _collect_results/_settle_retries 丢弃。
        测试可注入 overage_seed_budget 收紧窗口(假钟推进不真等)。
        """
        now = self._clock.monotonic()
        total_unsettled = sum(b.remaining for b in self._batches.values())
        if total_unsettled <= 0 or self._last_progress_ts is None:
            return
        budget = self._overage_seed_budget
        if budget is None:
            rounds = math.ceil(self._verify_timeout / self._poll_interval)
            # find 每轮一次 + add + pause 的 HTTP, 再加轮询 sleep 墙钟(verify_timeout 本身
            # 的节拍在轮与轮之间真实流逝, 不计入会把单种子最坏墙钟低估 10s)
            budget = (rounds + 3) * _SEED_HTTP_WORST_S + rounds * self._poll_interval
        bound = budget * total_unsettled
        stalled = now - self._last_progress_ts
        if stalled <= bound:
            return
        logger.warning(
            "transfer: 全局 %.1fs 无结论产出(> 预算 %.1fs x 深度 %d), 按 VERIFY_TIMEOUT 兜底结算未结算槽位(%d 个)",
            stalled,
            budget,
            total_unsettled,
            total_unsettled,
        )
        for batch in list(self._batches.values()):
            for idx, slot in enumerate(batch.slots):
                if slot.result is not None:
                    continue
                batch.slots[idx].result = TorrentTransferResult(
                    slot.hash,
                    TransferStatus.FAILED,
                    f"验证超时({self._verify_timeout:g}s 内目标未出现该种子)",
                    TransferOutcomeCode.VERIFY_TIMEOUT,
                )
                batch.remaining -= 1
            self._complete_if_ready(batch)
        # 兜底结算本身视为一次进展: 防残留批次(如回执重试)在下轮判定里重复触发
        self._last_progress_ts = now
