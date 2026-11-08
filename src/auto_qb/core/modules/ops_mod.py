"""OpsModule: 危险操作独立操作层的模块化封装(rules → ops ← web, plan 26-09-30-0109 P2')

OpsMixin(474 行) + CheckingMixin(39 行, 决策点 D2: 与 recheck/跳检同属「动种子文件」域)
整体迁入本模块, 经 ctx.ops 服务暴露(plan kernel-module-refactor P4, §3.2) —— 规则动作
(CheckAction 执行体)与 WEB 命令都只做调用方; WEB 命令改走 ctx.ops(plan P4), 规则侧经
manager 旧名单行委托(plan §7.2, P5 收口时随规则模块一起改 ctx.ops)。

recheck / 跳检的 qB 交互序列、提交点检查与保护策略单点归本模块。保护策略按来源(source)
区分(计划 §3.5, D1 拍板口径):
- 防「自动化频率失控」的保护只作用 source="rule": 3 次/日校验失败冷却(recheck_fails)。
  WEB 源是手动排障, 不受限 —— 限制它就是「按钮为什么不生效」。
- 防「真实冲突」的作用所有来源: 在途互斥(_active_checks 登记 / 快照 checking 态, R1)、
  recheck 提交点检查(R1: 在途 + 快照)、跳检相位机 + 同日去重(提交前不直查, 见 26-10-21-2323 S3)
  (skip_check_day)、跳检前置闸门组(G3-G8/filelist, 三分流判定单点
  _skip_gates_detail + 执行路径 _skip_gates 派生 + 预检 skip_check_precheck, plan 26-10-05-0314)。
  判据: 被拒时用户能否从界面自行看出原因 —— checking 态种子列表可见
  (拒绝可自解释), 保留; 不可见窗口的拒绝一律不对 WEB 设。

执行模型不变: 两个调用方都在主循环线程(WEB 命令线 drain + 规则任务线), 单一写线程约束
原样成立。阻塞执行体 + 单一写线程是当前安全模型的一半 —— recheck/skip_check 必须留在
主循环线程调用; 新来源(HR 联动 / 外部 API / 定时任务)接入 = 新增一个 source, 不复制操作
语义、不开旁路。新异步操作接入 = 新 source, 判定必须走证据门控(参照 recheck 的
poll_verdict 范式, 见 memory-bank/pitfalls/backend/effect-confirmation.md)。

依赖方向(单向, 防环): 本模块 -> rules 包**中性叶**(rules/checking_meta: 轮询常量与冷却
helper)与 rules.base(ActionResult) —— 这是 ops 与 rules 之间唯一允许的 import 方向
(plan §5「ops 与 rules 单向依赖」); rules 侧消费本模块一律经 ctx.ops 运行时调用,
**不得**反向 import 本模块 —— 否则 ops -> rules 包初始化 -> actions 成环。

!冷却计数 helper 的宿主是 StateService: 本模块传 self._ctx.state(checking_meta 契约,
plan 别名层处置 W1 起 manager 侧同样传 manager.ctx.state)。state / save_state 门面属性
仍保留, 供本模块自有落盘路径(冷却清零 / 跳检去重 / 备份元数据)使用。
!client 经 ctx.api.client **现取**(不缓存): 重连换客户端时 QbApi.bind 同步更新。
"""
import os
import time
from typing import Callable, Optional

from ...infra.clock import SYSTEM_CLOCK, Clock

from ...rules.base import ActionResult
from ...rules.checking_meta import (
    CHECK_RESULT_INTERVAL,
    CHECK_START_GIVEUP,
    RECHECK_FAIL_LIMIT,
    PollVerdict,
    bump_recheck_fail,
    is_piece_checking,
    poll_verdict,
    recheck_fail_count,
)
from ...torrents import TorrentRecord
from ..module import AppContext, BaseModule
from ..taskqueue import FINISHED, REQUEUE, Task
from .ops_common import (
    _RECHECK_BUSY_MSG,
    _RECHECK_GONE_MSG,
    logger,
)
from .ops_jobs import JobsMixin
from .ops_skip import SkipMixin
from .ops_verdict import VerdictMixin


class OpsModule(SkipMixin, VerdictMixin, JobsMixin, BaseModule):
    """ops 模块: recheck/跳检执行体 + 提交点检查 + 按 source 保护策略 + 文件完整性检查

    sections 认领 skip_checking_tag(跳检成功打标的标签名, 全局键); 其余消费面(api/store/
    state/task_queue)都是 ctx 服务, 无配置段。
    """

    name = "ops"

    def __init__(self, ctx: AppContext, clock: Optional[Clock] = None) -> None:
        self._ctx = ctx
        # 取时注入(D8): 本体与 SkipMixin 各取时点共用; 缺省单点经模块属性现取(测试可换假钟)
        self._clock = SYSTEM_CLOCK if clock is None else clock
        # 在途跳检 job(相位机; 同步入口内联驱动, 异步入口由微步线推进)
        self._skip_jobs: dict = {}
        # 最近终态结果 {hash: ActionResult}(供规则侧/测试取异步终态, 也供进度事件回放);
        # 有界: 只留最近 _SKIP_RESULT_KEEP(ops_common)条(纯观测面, 不参与判定)
        self._skip_results: dict = {}
        # 启动对账一次性开关(第一轮 sync 落地后跑一次; 进程内不复位)
        self._skip_recovered = False

    def sections(self) -> tuple[str, ...]:
        return ("skip_checking_tag", )

    # ---------- ctx.state 门面(checking_meta 冷却 helper 的鸭子类型面) ----------

    @property
    def state(self) -> dict:
        """运行期状态 dict(ctx.state 服务的落盘载荷, 与 manager.state 同一对象)"""
        return self._ctx.state.data

    def save_state(self) -> None:
        """状态立即落盘(冷却计数/跳检去重/备份元数据等非常规路径的即时写)"""
        self._ctx.state.save()

    # ---------- 日志 ----------

    @staticmethod
    def _ops_repr(torrent: Optional[TorrentRecord]) -> str:
        """日志标识: 活记录用 log_repr(名字+tracker+hash8), 记录已不在时退化裸 hash8"""
        return torrent.log_repr if torrent is not None else "(已不在库)"

    # ---------- full-checking: 提交点检查 + 提交 + 轮询 ----------

    def recheck(
        self,
        hash: str,
        source: str = "rule",
        torrent: Optional[TorrentRecord] = None,
        auto_start: bool = False,
        on_success: Optional[Callable[[], None]] = None,
        origin: Optional[Task] = None,
    ) -> ActionResult:
        """full-checking 操作: R1 提交点检查(在途 -> 快照 -> 冷却) -> 登记轮询子任务 ->
        发送 recheck -> 轮询结果

        自 rules/actions/full_checking.py._execute_full_checking 迁入(行为等价), 规则侧差异
        全部收进参数:
        - source: 保护策略按来源区分 —— 失败冷却(recheck_fails)仅 rule 源生效(D1);
          WEB 源手动排障不受冷却限制, on_success=None(成功即消亡, 无晋升无重入队)。
        - on_success: 校验成功时的**语义回调**(规则侧传晋升 verified_references; WEB 源 None),
          冷却清除与 auto_start 由本模块统一收尾(它们是操作语义, 不属调用方)。
        - origin: 规则任务(重入队由本模块负责: 成功 keep_progress 断点续跑, 失败/删除/
          宽限耗尽/异常 默认重置重走决策链); WEB 源 None —— 轮询结束即消亡, 无重入队副作用。
        - torrent: 可选活记录; None 时经 store 取(store 原地更新的活记录, 显式传参与缺省等价)。

        轮询单跳判定统一走 checking_meta.poll_verdict 证据门控(plan 26-10-04-1824): 成功结论
        必须有生效证据(真全量校验态, 排除启动期简历校验伪证据)背书 —— 未见证据时对 completed
        旧快照不下成功结论(WAITING 继续等), 未见证据而 progress 回落(数据缺损签名)提前判败。
        宽限耗尽的启动超时分支在判超时前做一次性仲裁直查(D5): 快照同步线暂停/滞后时对 qB
        单 hash 直查核实, 见真校验态延长一次宽限(仍纯快照观测), 未见或直查异常判败(fail-closed)。

        提交前**不直查**(26-10-21-2323 S3): 运行状态按 qB 的 RefreshInterval(默认 1500ms)节流
        刷新, 命令后直查与快照读到的是同一份缓存, 多这一次只增加维护面; 不存在的种子提交任何
        命令本就是 no-op。重复提交保护由「在途登记 + 快照 checking 态」承担(R1 两半), 代价是
        qB 自家 WebUI 刚发起的校验可能被重复提交一次(qB 侧幂等)。进度基线改取快照 progress。

        返回 ActionResult: rule 源 pending(规则断点, 规则任务本轮不重入队, 恢复由轮询负责) /
        web 源 ok(已提交, 结果经快照可见) / skip(R1 拒绝(在途/快照 checking) / 冷却 / 种子不在库) /
        fail(发送失败)。
        """
        prefix = f"ops[{source}]"

        # ---- R1 提交点检查(在途互斥, 全来源): 规则轮询在途或快照已在校验态 -> 拒绝 ----
        # WEB->规则半边: 不重启规则正在轮询的校验(进度回落会误判失败/污染当日计数);
        # 规则->WEB/规则: 决策链 1.5 组内串行化经 _active_checks 感知到本模块登记(双向闭环)。
        if hash in self._ctx.task_queue.active_check_hashes():
            logger.info(
                f"{prefix} {self._ops_repr(torrent or self._ctx.store.get(hash))} | recheck 拒绝: {_RECHECK_BUSY_MSG}"
            )
            return ActionResult.skip(_RECHECK_BUSY_MSG)
        snap = self._ctx.store.get(hash)
        if snap is not None and snap.state_enum.is_checking:
            logger.info(f"{prefix} {snap.log_repr} | recheck 拒绝: {_RECHECK_BUSY_MSG}(快照 checking 态)")
            return ActionResult.skip(_RECHECK_BUSY_MSG)

        # ---- 失败冷却: 仅规则源(自动化 recheck 死循环自限频; WEB 手动排障不受限, D1) ----
        if source == "rule" and recheck_fail_count(self._ctx.state, hash) >= RECHECK_FAIL_LIMIT:
            logger.info(f"{prefix} {self._ops_repr(torrent or snap)} | "
                        f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")
            return ActionResult.skip(f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")

        tor = torrent if torrent is not None else snap
        if tor is None:
            # 快照与显式传入都没有该种子: 干净放弃(真正的"已不在"由导出/轮询各自收口)
            return ActionResult.skip(_RECHECK_GONE_MSG)
        tq = self._ctx.task_queue

        # 进度基线取**快照**(26-10-21-2323 S3): 提交前不再直查 qB 运行状态 —— 它按
        # RefreshInterval(默认 1500ms)节流刷新, 直查读到的与快照是同一份缓存, 多这一次
        # 只增加维护面(不存在的种子提交 recheck 本就是 no-op)。闭包内存态, 不入 state_file。
        baseline_progress = tor.progress

        def poll(task: Task, dry_run: bool) -> bool:
            """校验结果轮询: 证据门控状态机 —— 读 store 活记录(原地更新, 不发 API 重查真值), 每
            CHECK_RESULT_INTERVAL 一跳

            单跳判定序(plan 26-10-04-1824, 判定序单点在 checking_meta.poll_verdict, 本闭包只分派):
            1. 生效证据闩: 快照处于真全量校验态(checkingDL/checkingUP; is_piece_checking 排除
               qB 启动期 checkingResumeData 简历校验伪证据) -> 置 seen_checking, 继续等;
            2. seen_checking 已立 -> 结果判定: progress>=1.0 即 SUCCESS, 否则 FAILED(成功结论
               必须有生效证据背书 —— 已完成种子的陈旧快照 progress=1.0 不再误判成功,
               issue 26-10-03-1140);
            3. 未见证据而 progress 回落(< baseline_progress) -> FAILED(数据缺损签名, 标签
               「progress 回落」, 先于超时判定);
            4. 宽限耗尽仍无证据 -> START_TIMEOUT: 判超时前先做一次性仲裁直查(plan 26-10-04-1824
               D5, 事件驱动, 本轮询生命周期至多 1 次)—— 快照同步线可能暂停/滞后而 qB 真在校验,
               对 qB 单 hash 直查核实: 见真校验态 -> 重置宽限窗口延长一次, 回到纯快照观测;
               未见或直查异常 -> 判败(活锁保险丝, fail-closed);
            5. 其余歧义 -> WAITING 继续等(recheck 异步应用 + 快照按 sync_interval 节拍滞后,
               首样本竞态修复语义并入)。

            等价性红线(plan §3.4): 这里必须继续读 store 活记录 —— 记录对象被同步线程原地
            更新, 逐轮读到最新 state/progress; 不得改为闭包创建时缓存字段值(快照失真),
            也不得改为每次 torrents_info 直查(把 2s 轮询变成 API 轰炸) —— 周期观测是纯
            快照读, 零 API; 终局处置里的写动作(auto_start)不受此限。
            """
            nonlocal submitted, submitted_at, seen_checking, arbitrated
            try:
                if not submitted:
                    return FINISHED  # recheck 发送失败: 登记的轮询直接消亡(释放在途登记)
                rec = self._ctx.store.get(hash)
                if rec is None:
                    # 种子已删除: 规则源默认重置重新入队 origin, 由其删除守卫(_handle_rule)判死
                    logger.warning(f"{prefix} {hash[:8]} | 校验轮询: 种子已删除")
                    self.state.get("recheck_fails", {}).pop(hash, None)
                    if origin is not None:
                        tq.add_task(origin)
                    return FINISHED
                if is_piece_checking(rec.state):
                    seen_checking = True  # 生效证据闩: 本轮 recheck 确已生效(别名收窄, 简历校验不算)
                    return REQUEUE  # 仍在校验中, 下一轮轮询
                verdict = poll_verdict(
                    seen_checking=seen_checking,
                    progress=rec.progress,
                    baseline_progress=baseline_progress,
                    elapsed=self._clock.now() - submitted_at,
                    giveup=CHECK_START_GIVEUP,  # 显式透传(与默认同值): 宽限上限保持 ops_mod 命名空间可打桩
                )
                if verdict is PollVerdict.WAITING:
                    # 歧义继续等: recheck 尚未被 qB 应用(异步应用 + 快照滞后)或排队未开检 ——
                    # 不计失败(首样本竞态修复); 含「无证据的 progress>=1.0 旧快照」, 不对陈旧
                    # 快照下成功结论(事故 26-10-03-1140 的结构性排除点)
                    return REQUEUE
                if verdict is PollVerdict.SUCCESS:
                    # 生效证据之后的完成: 真校验成功(到这必 seen_checking=True, 结构性排除假成功)
                    logger.info(f"{prefix} {rec.log_repr} | 校验成功")
                    if on_success is not None:
                        on_success()
                    self.state.get("recheck_fails", {}).pop(hash, None)  # 校验通过: 清除失败冷却计数
                    if auto_start:
                        self._ctx.api.torrents_start(torrent_hashes=hash)
                        logger.info(f"{prefix} {rec.log_repr} | 校验成功自动开始")
                    if origin is not None:
                        tq.add_task(origin, keep_progress=True)  # 显式保存进度: 断点续跑后续动作
                elif verdict is PollVerdict.FAILED:
                    # 生效后未完成(seen_checking=True)或未见证据而 progress 回落(数据缺损签名):
                    # 均为真实校验未通过(冷却仅规则源, D1); 两到达路径只是标签差异, 处置相同
                    if source == "rule":
                        fail_count = bump_recheck_fail(self._ctx.state, hash)
                        if seen_checking:
                            logger.warning(f"{prefix} {rec.log_repr} | 校验未通过(第{fail_count}次, progress={rec.progress})")
                        else:
                            logger.warning(
                                f"{prefix} {rec.log_repr} | "
                                f"校验未通过(progress 回落 {rec.progress} < 基线 {baseline_progress}, 第{fail_count}次)"
                            )
                    else:
                        if seen_checking:
                            logger.warning(f"{prefix} {rec.log_repr} | 校验未通过(progress={rec.progress})")
                        else:
                            logger.warning(
                                f"{prefix} {rec.log_repr} | "
                                f"校验未通过(progress 回落 {rec.progress} < 基线 {baseline_progress})"
                            )
                    if origin is not None:
                        tq.add_task(origin)  # 默认重置: 重走完整决策链(重新校验)
                else:  # PollVerdict.START_TIMEOUT
                    # 宽限耗尽仍未见校验启动: 判超时前先仲裁直查(D5, 事件驱动一次性)—— 快照
                    # 同步线可能暂停/滞后(暂停旁观 pause_event / 同步线故障), qB 可能真在校验
                    # 而快照看不见; 本生命周期内至多仲裁 1 次, 第二次宽限耗尽直接判败
                    elapsed_now = self._clock.now() - submitted_at  # 真实等待时长(日志用; 须在宽限重置前取)
                    if not arbitrated:
                        arbitrated = True
                        try:
                            live = self._ctx.api.torrents_info(torrent_hashes=hash)
                        except Exception as e:
                            # 直查异常与「未见」同判(fail-closed): 异常在分支内吃掉, 不走外层
                            # 「校验轮询异常」路径, 判败序列原样(计划 26-10-04-1824)
                            logger.warning(f"{prefix} {rec.log_repr} | 启动超时仲裁直查失败({e}), 按未见校验判败")
                            live = []
                        if live and is_piece_checking(live[0].state):
                            # qB 实际在校验(快照看不见): 延长一次宽限, 重置窗口后继续纯快照观测
                            # (证据照常经闩/verdict 判定, 观测零 API 不变)
                            submitted_at = self._clock.now()
                            logger.info(
                                f"{prefix} {rec.log_repr} | "
                                f"启动超时仲裁: qB 实际在校验而快照未见, 已等 {elapsed_now:.0f}s, 延长一次宽限继续观测"
                            )
                            return REQUEUE
                        # 直查未见真校验态(空=种子已不在 / 非 checking / 异常): 落判败序列
                    # 判败防轮询活锁(qB 重启丢请求等极端情形); 判败后 origin 重走决策链会重新
                    # 提交, 请求恢复生效后自然续上; 日志报真实等待时长(计划 §10 R4, 判「启动超时」语义不变)
                    if source == "rule":
                        fail_count = bump_recheck_fail(self._ctx.state, hash)
                        logger.warning(
                            f"{prefix} {rec.log_repr} | "
                            f"校验启动超时({elapsed_now:.0f}s 未见 checking, 第{fail_count}次, progress={rec.progress})"
                        )
                    else:
                        logger.warning(
                            f"{prefix} {rec.log_repr} | "
                            f"校验启动超时({elapsed_now:.0f}s 未见 checking, progress={rec.progress})"
                        )
                    if origin is not None:
                        tq.add_task(origin)  # 默认重置: 重走完整决策链(重新校验)
                return FINISHED  # 轮询子任务消亡(释放在途登记)
            except Exception as e:
                logger.error(f"{prefix} {hash[:8]} | 校验轮询异常: {e}")
                if origin is not None:
                    tq.add_task(origin)  # 默认重置: 重走完整决策链
                return FINISHED

        submitted = False  # recheck 是否发送成功(先登记后发送; 失败时轮询子任务据此消亡)
        submitted_at = self._clock.now()  # 校验启动宽限窗口起点(recheck 发送成功时刻)
        seen_checking = False  # 本轮询周期内是否观察到过生效证据(成功结论的必要背书)
        arbitrated = False  # 本轮询生命周期内是否已仲裁过(启动超时判败前的一次性直查, D5 至多 1 次)
        # (baseline_progress 取提交时的快照 progress, 见上方说明)

        task = Task(
            "check",
            "check-checking-result",
            hash=hash,
            store=self._ctx.store,
            interval=CHECK_RESULT_INTERVAL,
            handler=poll,
        )
        if not tq.add_task(task):
            # R1 已先行拒绝在途, 这里是单线程模型下的兜底(不可达; 保留防将来有第二个登记点)
            return ActionResult.skip("该校验任务已在队列中")
        try:
            self._ctx.api.torrents_recheck(torrent_hashes=hash)
            submitted = True
            submitted_at = self._clock.now()
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        logger.info(f"{prefix} {self._ops_repr(tor)} | full-checking 校验已提交")
        if source == "rule":
            # pending: 规则记录断点, 规则任务本轮不重入队 —— 恢复由轮询子任务负责
            return ActionResult.pending("full-checking 校验已提交")
        return ActionResult.ok("校验已提交")

    def _backup_torrent(self, tor: TorrentRecord, data: bytes, content_layout: Optional[str] = None) -> str:
        """删除前把 .torrent 落盘备份并记录元数据(便于手动恢复), 返回备份路径

        用删除前捕获的 tor 记录(删除后 store 记录已移除)。元数据立即落盘(非常规路径,
        不适用"仅退出时落盘"的写放大规避): 备份后程序一旦崩溃, 没有 state 里的元数据指引,
        用户不知道 .torrent 备份的存在与原始保存路径。

        元数据除恢复凭据(path/save_path/category/tags)外, 还按 skip_readd_kwargs 的消费键
        记全重加回传面(content_layout + 限速/分享限制, R1#94): 崩溃恢复重加
        (_recover_skip_backups)按账本原样回传 —— 账本缺记的字段恢复无从回传, 恢复出的
        种子会被 qB 默认值静默重置(contentLayout 布局错位 / 单种限速与分享限制丢失)。

        调用时机是崩溃安全的关键: 必须**先于** torrents_delete(第一个不可逆步骤), 而不是
        挂在重加的失败路径上 —— 重加前那几秒缝隙内崩溃, 谁也来不及备份(issue 26-09-21-1347)。
        """
        backup_dir = os.path.join(os.path.dirname(self._ctx.state.state_file) or ".", "skip-check-backup")
        os.makedirs(backup_dir, exist_ok=True)
        path = os.path.join(backup_dir, f"{tor.hash}.torrent")
        with open(path, "wb") as f:
            f.write(data)
        backup_meta = self.state.setdefault("skip_check_backup", {})
        backup_meta[tor.hash] = {
            "path": path,
            "save_path": tor.save_path,
            "category": tor.category,
            "tags": tor.tags,
            "ts": self._clock.now(),
            # 重加回传面(skip_readd_kwargs 消费键, 键名 = TorrentRecord 属性名, R1#94 起记全):
            # content_layout 是 _skip_step_prepare 的推断产物, 经入参传入(不在 tor 上)
            "content_layout": content_layout,
            "up_limit": tor.up_limit,
            "dl_limit": tor.dl_limit,
            "seq_dl": tor.seq_dl,
            "f_l_piece_prio": tor.f_l_piece_prio,
            "ratio_limit": tor.ratio_limit,
            "seeding_time_limit": tor.seeding_time_limit,
            "inactive_seeding_time_limit": tor.inactive_seeding_time_limit,
            "share_limit_action": tor.share_limit_action,
            "share_limits_mode": tor.share_limits_mode,
        }
        self.save_state()
        return path
