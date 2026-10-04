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
  recheck 提交点实时复核(R1, plan 26-10-04-1824)、跳检实时复核(R2)、跳检同日去重
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
import logging
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Optional

from ...infra import file_access, utils
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

logger = logging.getLogger(__name__)

# R1/R2 拒绝文案(自解释: checking 态在种子列表可见, 用户能对上原因)
_RECHECK_BUSY_MSG = "校验进行中, 请等待当前校验完成"
_SKIP_GONE_MSG = "种子已被移除(可能被用户删除), 放弃跳检"
_RECHECK_GONE_MSG = "种子已被移除(可能被用户删除), 放弃校验"  # R1 实时复核 live 空时用(与 _SKIP_GONE_MSG 同族)

# 跳检闸门三分流标签(plan 26-10-05-0314 §03/§04, cls 与谓词同点定义):
#   blocked = 确定性危害/零收益, 一律硬拒(force 也不放行, case 1);
#   force   = 真不确定(判决窗口抢跑), 可被 skip_check(force=True) 显式豁越(case 2);
#   ok      = 通过(不进未过列表 —— _skip_gates_detail 只返回未过闸门)。
GATE_BLOCKED = "blocked"
GATE_FORCE = "force"
GATE_OK = "ok"


@dataclass(frozen=True)
class GateVerdict:
    """单道跳检闸门的判定结果(不可变值对象): gate 闸门 id / cls 三分流标签 / text 拒绝文案

    gate 取值: "G3"(已完成) / "G4"(活跃中) / "G5"(同 hash 校验在途) / "G6"(组内活跃下载) /
    "G7"(组内其它成员校验在途) / "G8"(组内成员校验失败推断) /
    "partial"(部分下载) / "dedup"(同日去重) / "filelist"(前置文件检查) / "gone"(预检时种子已不在
    客户端, 仅 skip_check_precheck 产出)。拒绝文案按「原因+后果+出路」三段式(plan §03)。
    """
    gate: str
    cls: str
    text: str


def _poll_until(predicate, attempts: int, interval: float) -> bool:
    """轮询直至 predicate 为真或次数耗尽(异常视为未满足); 返回是否满足

    供跳检的删除/重加确认共用: qB 的删除与重加均为异步生效, 需短间隔轮询客户端状态。
    """
    for _ in range(attempts):
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


class OpsModule(BaseModule):
    """ops 模块: recheck/跳检执行体 + 提交点检查 + 按 source 保护策略 + 文件完整性检查

    sections 认领 skip_checking_tag(跳检成功打标的标签名, 全局键); 其余消费面(api/store/
    state/task_queue)都是 ctx 服务, 无配置段。
    """

    name = "ops"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

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
        on_success=None,
        origin=None,
    ) -> ActionResult:
        """full-checking 操作: R1 提交点检查(快照 -> 冷却 -> 实时复核) -> 登记轮询子任务 ->
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

        提交点实时复核(plan 26-10-04-1824 P1): 快照 <=1.5s 龄, qB 自家 WebUI 刚发起的校验在
        该窗口内不可见, 此时提交会重复排队(no-op 或重扫文件挪队尾) —— 快照检查与冷却通过后、
        登记之前对 qB 单 hash 直查核实(跳检 R2 同款范式): live 空 = 种子已不在(放弃) /
        live checking = 拒绝 / 复核异常 fail-closed 拒绝; 进度基线一并改取 live 真值。成本为
        每次提交 +1 次 torrents_info(人工点击与规则决策链都是低频事件, 计划 §10 R3 已接受)。

        返回 ActionResult: rule 源 pending(规则断点, 规则任务本轮不重入队, 恢复由轮询负责) /
        web 源 ok(已提交, 结果经快照可见) / skip(R1 拒绝(快照/实时复核/种子已不在)或冷却) /
        fail(发送失败或实时复核异常)。
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
        tq = self._ctx.task_queue

        # ---- R1 实时复核(全来源, plan 26-10-04-1824 P1): 动手前对 qB 单 hash 直查核实(跳检 R2
        # 同款范式)。次序约束(计划 §6.1): 在冷却之后(冷却拒绝不付 API 成本)、登记之前(拒绝时
        # 不留任何登记); live 空 = 种子已不在(qB 侧已删, 快照尚在) -> 放弃。
        try:
            live = self._ctx.api.torrents_info(torrent_hashes=hash)
        except Exception as e:
            # 复核异常 fail-closed: 看不见就不提交(未执行任何变更), 与跳检 R2 同口径
            return ActionResult.fail(f"提交前实时复核失败(未执行任何变更): {e}")
        if not live:
            logger.info(f"{prefix} {self._ops_repr(tor)} | recheck 放弃: {_RECHECK_GONE_MSG}")
            return ActionResult.skip(_RECHECK_GONE_MSG)
        if is_piece_checking(live[0].state):
            # live 真值在校验(快照窗口内不可见, 典型: qB 自家 WebUI 刚发起) -> 拒绝重复提交
            logger.info(f"{prefix} {self._ops_repr(tor)} | recheck 拒绝: {_RECHECK_BUSY_MSG}(实时复核)")
            return ActionResult.skip(f"{_RECHECK_BUSY_MSG}(实时复核)")
        # 进度基线取 live 真值(P1, 取代 store 快照值): 快照 progress 与 qB 不一致时, 轮询期的
        # 回落证据(数据缺损签名)按 qB 真实进度判定 —— 闭包内存态, 不入 taskqueue/state_file
        baseline_progress = live[0].progress

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
                    elapsed=time.time() - submitted_at,
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
                    elapsed_now = time.time() - submitted_at  # 真实等待时长(日志用; 须在宽限重置前取)
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
                            submitted_at = time.time()
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
        submitted_at = time.time()  # 校验启动宽限窗口起点(recheck 发送成功时刻)
        seen_checking = False  # 本轮询周期内是否观察到过生效证据(成功结论的必要背书)
        arbitrated = False  # 本轮询生命周期内是否已仲裁过(启动超时判败前的一次性直查, D5 至多 1 次)
        # (baseline_progress 已在上方实时复核处取 live 真值, P1 起基线不再取 store 快照)

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
            submitted_at = time.time()
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        logger.info(f"{prefix} {self._ops_repr(tor)} | full-checking 校验已提交")
        if source == "rule":
            # pending: 规则记录断点, 规则任务本轮不重入队 —— 恢复由轮询子任务负责
            return ActionResult.pending("full-checking 校验已提交")
        return ActionResult.ok("校验已提交")

    # ---------- skip-checking: 跳检四阶段(含 R2 实时复核) ----------

    def skip_check(
        self,
        hash: str,
        source: str = "rule",
        torrent: Optional[TorrentRecord] = None,
        auto_start: bool = False,
        has_reference: bool = True,
        force: bool = False,
    ) -> ActionResult:
        """辅种跳检(高风险): 导出 → 删除(保留文件) → 确认消失 → 重加(跳过校验) → 确认出现 → 恢复快照

        自 rules/actions/skip_checking.py._execute_skip_checking 迁入(行为等价)。执行序(plan
        26-10-05-0314 §03/§04): R2 实时复核 → 前置闸门(filelist 排最后) → 导出 —— filelist 并入
        闸门后, 其插入点要求「R2 live 复核确认种子还在之后、导出等不可逆步骤之前」(live 都不在的
        种子不值得再跑任何闸门, 含 filelist 的 files API), 故 R2 前移到闸门之前; 拒绝仍然零副作用
        (R2 与全部闸门都在备份与删除这两个不可逆步骤之前)。

        来源差异:
        - has_reference 的「无参考跳检(高风险)」告警是规则侧语义, 仅 rule 源产生(WEB 前端
          危险确认框已承担风险告知, 不把规则告警泄漏进 WEB)。
        - 安全闸门全来源生效(三分流归类见 GateVerdict): 部分下载禁止跳检 / 跨规则同日去重
          (skip_check_day 跨来源共享, 拒绝文案「今日已跳检过」自解释) / 已完成与活跃中禁止(G3/G4) /
          组内活跃下载禁止(G6) / 同 hash 校验在途可强制(G5) / 组内其它成员校验在途可强制(G7) /
          组内成员校验失败推断禁止(G8) / 前置文件检查(filelist)。
        - force: 仅豁越 cls=force 的未过闸门(降级 warning + INFO 审计后放行), cls=blocked 一律硬拒;
          缺省 False —— 规则侧调用点不传(签名缺省即零变化不变式的证明)。
        - torrent: 可选活记录; None 时经 store 取(规则侧 ctx.torrent 与缺省取值等价)。
        """
        prefix = f"ops[{source}]"
        tor = torrent if torrent is not None else self._ctx.store.get(hash)
        if tor is None:
            return ActionResult.skip(_SKIP_GONE_MSG)

        # ---- R2 实时复核: 闸门读的是快照(≤2s 龄), 动手前重拉一次实时状态 ----
        # 种子已不在 -> 干净放弃: 发生在备份与删除之前, 零副作用、无孤儿备份(修 C2)。
        try:
            live = self._ctx.api.torrents_info(torrent_hashes=hash)
        except Exception as e:
            return ActionResult.fail(f"跳检前实时复核失败(未执行任何变更): {e}")
        if not live:
            logger.info(f"{prefix} {tor.log_repr} | 跳检放弃: {_SKIP_GONE_MSG}")
            return ActionResult.skip(_SKIP_GONE_MSG)

        # ---- 阶段 1: 前置闸门 (任一不过 → fail/skip 返回, 无副作用; filelist 排最后) ----
        gate = self._skip_gates(hash, tor, force=force)
        if gate is not None:
            return gate

        # ---- 阶段 2: 准备 (导出/校验属性/布局推断, 均须在删除前完成) ----
        try:
            data = self._ctx.api.torrents_export(torrent_hash=hash)
        except Exception as e:
            return ActionResult.fail(f"导出 .torrent 失败: {e}")
        if not data:
            return ActionResult.fail("导出 .torrent 为空")

        # 重加所需的 6 属性(RE_ADD_FIELDS)存在性已由启动期 schema 校验保证(refresh 首次
        # 拉取时验证 REQUIRED_TORRENT_FIELDS); 记录对象删除后仍持有这些字段(_raw),
        # 故直接读 tor 属性即可(无需中间投影对象)

        # 布局推断依赖 content_path/save_path/文件列表(惰性缓存, filelist 前置检查已填充);
        # 删除后 store 记录已移除, 必须在此之前完成
        content_layout = self._infer_content_layout(tor, self._ctx.api.client)

        # 备份先于删除(崩溃安全): 删除是整条链上第一个不可逆步骤。备份若挂在重加的失败路径上,
        # 那么「删除已生效 → 重加未被 qB 接受」这一缝隙(含删除确认轮询的约 5s)内崩溃/强杀,
        # 种子从客户端消失、data 只存在于内存、state 无在途标记 —— 重启后无任何恢复凭据
        # (issue 26-09-21-1347)。备份写不进去就不删除: 此时放弃跳检没有任何损失。
        try:
            self._backup_torrent(tor, data)
        except Exception as e:
            return ActionResult.fail(f"跳检备份 .torrent 失败(未删除, 无损失): {e}")

        # ---- 阶段 3: 执行 (删除 → 确认消失 → 重加 → 确认出现 → 恢复快照) ----
        failed = self._skip_delete(hash, tor, prefix)
        if failed is not None:
            return failed
        failed = self._skip_readd(hash, tor, data, content_layout)
        if failed is not None:
            return failed

        # ---- 阶段 4: 收尾 ----
        # 无参考高风险警告(规则侧语义; 用删除前捕获的 tor: 真实流程中删除后 store 记录已移除)
        if source == "rule" and not has_reference:
            logger.warning(f"{prefix} {tor.log_repr} | 无参考跳检(高风险): "
                           f"仅文件存在与大小对比, 内容错误会传垃圾数据")
        # 跳检成功打标(skip_checking_tag): 标记该种子未经哈希校验, 后续查找参考种子时排除;
        # 标签名直接读全局 config.skip_checking_tag(默认 zSkipChecked, 不按规则覆盖);
        # 打标失败不影响跳检结果(跳检本身已完成), 仅记 warning
        skip_tag = self._ctx.config.skip_checking_tag
        if skip_tag and skip_tag not in tor.tags_set:
            try:
                self._ctx.api.torrents_add_tags(tags=[skip_tag], torrent_hashes=hash)
                logger.info(f"{prefix} {tor.log_repr} | 跳检完成, 已打标签 {skip_tag}(该种子不作参考种子)")
            except Exception as e:
                logger.warning(f"{prefix} {tor.log_repr} | 跳检打标签失败(不影响跳检结果): {e}")
        if auto_start:
            try:
                self._ctx.api.torrents_start(torrent_hashes=hash)
            except Exception as e:
                return ActionResult.fail(f"自动开始失败: {e}")
            return ActionResult.ok("skip-checking 跳检完成并自动开始")
        return ActionResult.ok("skip-checking 跳检完成")

    def skip_check_precheck(self, hashes: list) -> list:
        """跳检预检(只读 dry-run, plan 26-10-05-0314 D6/D9): 逐 hash 给出三分流判定, 供 WEB 确认框
        在用户确认之前摊开「该不该跳检、赌什么」; 执行路径闸门原样全跑 —— 预检与执行之间无信任传递。

        只读承诺(T20): 不写 state(skip_check_day 不写入不 prune)、不 pop、无任何 qB 写 API、
        种子零变动 —— 内部仅走 _skip_gates_detail(零副作用判定)与 check_filelist(torrents_files
        只读); _skip_gates 的 prune 副作用不得经 detail 泄入本路径。经命令队列在主循环线程执行
        (与写命令串行化, 快照无撕裂)。

        返回 list[dict] 单 hash 一条, 字段命名对齐 S2 的 HTTP 回执形状
        {results: [{hash, name, cls, reasons}], summary: {ok, force, blocked}}(summary 由调用方聚合):
        - cls: 单 hash 总三分流, blocked > force > ok(任一未过闸门 blocked 即 blocked;
          否则存在 force 类未过即 force; 全过 ok);
        - reasons: [{gate, cls, text}, ...] 即 _skip_gates_detail 的全部未过闸门; tor 已不在
          客户端(store 无记录)时单条 gone/blocked, 文案「已不在客户端」(S2 端点测试 T21 依赖)。
        """
        results = []
        for h in hashes:
            tor = self._ctx.store.get(h)
            if tor is None:
                results.append(
                    {
                        "hash": h,
                        "name": "",
                        "cls": GATE_BLOCKED,
                        "reasons": [{
                            "gate": "gone",
                            "cls": GATE_BLOCKED,
                            "text": "已不在客户端(可能已被删除), 无法跳检"
                        }],
                    }
                )
                continue
            verdicts = self._skip_gates_detail(h, tor)
            if any(v.cls == GATE_BLOCKED for v in verdicts):
                cls = GATE_BLOCKED
            elif verdicts:  # 只剩 force 类未过
                cls = GATE_FORCE
            else:
                cls = GATE_OK
            results.append(
                {
                    "hash": h,
                    "name": tor.name,
                    "cls": cls,
                    "reasons": [{
                        "gate": v.gate,
                        "cls": v.cls,
                        "text": v.text
                    } for v in verdicts],
                }
            )
        return results

    def _skip_gates(self, hash: str, tor: TorrentRecord, force: bool = False) -> Optional[ActionResult]:
        """跳检前置闸门(执行路径): 从 _skip_gates_detail 派生 —— 取首个未过闸门转 ActionResult,
        谓词只写一遍、执行与预检两路径同源(防两套谓词漂移, T18 同源断言钉死)。

        - 返回形态与既有语义一致: dedup 沿用 skip, 其余闸门 fail; None = 全部通过。
        - force=True 仅把 cls=force 的未过闸门降级为 warning 日志后放行(另记 INFO 审计:
          哪个 hash 豁越了哪个闸门); cls=blocked 一律硬拒。
        - 全部通过(含 force 豁越后)时顺带清理非当日 skip_check_day 记录(防 state 无界增长)
          —— 这是本路径**专属副作用**, detail(预检)零写入(T20)。
        """
        for v in self._skip_gates_detail(hash, tor):
            if force and v.cls == GATE_FORCE:
                logger.warning(f"{tor.log_repr} | force 豁越跳检闸门 {v.gate}: {v.text}")
                logger.info(f"force 审计: hash={hash} 豁越闸门 {v.gate}(跳检继续)")
                continue
            if v.gate == "dedup":
                return ActionResult.skip(v.text)
            return ActionResult.fail(v.text)
        today = date.today().isoformat()
        skip_day = self.state.get("skip_check_day")
        if skip_day:
            for h in [h for h, d in skip_day.items() if d != today]:
                del skip_day[h]
        return None

    def _skip_gates_detail(self, hash: str, tor: TorrentRecord) -> list:
        """跳检前置闸门判定单点(只读): 按固定顺序逐闸门判定, 返回**全部未过**闸门(全过 = 空列表)

        三分流 cls 与谓词同点定义(见 GateVerdict)。执行路径 _skip_gates 取首个未过闸门, 预检
        skip_check_precheck 消费完整列表 —— 两路径同源。

        零副作用铁律(T20): 本判定不写 state、不 prune、不 pop、无任何 qB 写 API —— 预检
        「只是看看」不得改状态; skip_check_day 的清理留在执行路径(_skip_gates 尾部)。

        顺序与短路: G3 → G4 → G5 → G6 → G7 → G8 → partial → dedup → filelist(排最后, plan 插入点由
        skip_check 的执行序保证: R2 实时复核之后、导出之前)。前面已有 **blocked** 未过时短路
        跳过 filelist(省一次 files API + N 次 stat —— 结论已注定 blocked); 仅 force 类未过时
        **不**短路: force=True 豁越后 filelist 仍须真跑(case 1 硬闸不得被短路绕过)。

        各闸门口径:
        - G3 已完成(progress>=1, 无论状态) / G4 活跃中(非 stopped 且 p<1): 放行谓词逐字同
          rules/actions/checking.py:88 决策链 0(两处注释互指); stalledDL 等边缘态口径由
          state_enum 现有语义决定, 与规则侧天然一致(同一谓词), 不发明 WEB 特有口径(plan §03)。
        - G5 同 hash 校验在途(ctx.task_queue.active_check_hashes(), recheck 在途互斥同款原语):
          跳检删种会杀死在途校验轮询 —— case 2(组内其它成员校验在途同归 case 2, 见 G7)。
        - G6 组内有活跃下载成员(经 store.group_has_downloading, S1a 上移的组级判定单点):
          组内共享物理文件, 下载方正在写, 跳检把全部块标有效 = 脏数据。
        - G7 组内其它成员 full-checking 在途(case 2): 谓词逐字镜像
          rules/actions/full_checking.py _wait_for_group_checking.others_checking(决策链 1.5,
          others-only 排除自身), 两半视野: 队列登记 active_check_hashes(规则发起) ∪ store 快照
          is_checking(后半覆盖用户手动 recheck —— G5 的队列视野看不见它)。判决窗口抢跑是真不确定:
          判决通过即证明共享文件完好, 判决失败则洗白坏数据 —— 同 G5 给 force 逃生(D4/D8 拍板)。
        - G8 组内成员校验失败推断(case 1): 四要件逐字镜像
          rules/actions/full_checking.py _skip_on_group_check_failed(决策链 1.6, others-only):
          其它成员 / 当日计数(recheck_fails, 含宽限耗尽/异常噪声 —— 继承规则侧既有假阳性面,
          同日窗口+自愈条件兜底, 不发明更锐利谓词) / 假失败自愈**只读变体**: 记录指向已完成/
          已删成员时不参与推断且不 pop(规则侧此处 pop, full_checking.py:146) —— 清理仍归规则侧
          与次日重置, 本判定零副作用铁律(T20) / 文件映射一致(group_sizes)。出路 = 对该组做
          full-checking 修数据。
        - partial(0<p<1): 预分配使文件尺寸=完整尺寸, filelist 尺寸检查无法发现未下载的零块,
          is_skip_checking 会把全部块标记有效 -> 零块被上传(垃圾数据)。仅 progress==0(全新辅种,
          数据完整)可跳检; full-checking 对部分下载安全, 不设限。
        - dedup: 跨规则同日去重(全来源) —— 多条规则都配 checking 时, 同一种子当日只跳检一次
          (跳检必然清空本地统计, 重复跳检只会再丢一次而毫无收益)。
        - filelist: 前置文件检查, 调 check_filelist(checking.py:121 决策链 4 同一原语, 规则侧
          双查为计划明文接受); 失败语义 blocked(fail), 不是 skip; 映射 miss(路径不可判定)保守
          停住, 文案自带「修 fs.path_map 配置」出路。
        """
        verdicts: list = []
        progress = tor.progress
        state_enum = tor.state_enum

        # G3/G4 共用放行谓词 —— 逐字同 rules/actions/checking.py:88 决策链 0(两处注释互指):
        # 仅「暂停中未完成」放行; 做种态 p=1 落 G3, 下载中等非 stopped 态 p<1 落 G4。
        paused_incomplete = state_enum.is_stopped and progress < 1.0

        if not paused_incomplete:
            if progress >= 1.0:
                # G3 已完成: 数据已通过哈希校验, 跳检零收益纯损失(case 1, 用户点名项)
                verdicts.append(
                    GateVerdict(
                        "G3", GATE_BLOCKED, f"种子已完成(progress={progress}): 数据已通过哈希校验, 跳检无任何意义, "
                        f"只会清零本地做种统计; 无需跳检"
                    )
                )
            else:
                # G4 活跃中: 活跃且 p<1 = 下载中, 同部分下载的垃圾上传危害(case 1);
                # 出路 = 先暂停再跳检(暂停后 p=0 可过全部闸门, 不需要 force)
                verdicts.append(
                    GateVerdict(
                        "G4", GATE_BLOCKED, f"种子活跃中(state={tor.state}): 未暂停且未完成, 未验证块会被标有效并上传垃圾数据; "
                        f"请先暂停再跳检"
                    )
                )

        # G5 同 hash 校验在途(case 2): 判决窗口抢跑是真不确定 —— 强制 = 杀死在途校验
        # (已花 I/O 作废)且不经其判决断言数据有效; 用户明知本轮校验无意义(如误发起)时留逃生
        if hash in self._ctx.task_queue.active_check_hashes():
            verdicts.append(
                GateVerdict("G5", GATE_FORCE, "该种子校验中(在途): 跳检会删除种子并使在途校验作废, 且不经其判决断言数据有效"
                            "(若数据坏将被洗白); 确知本轮校验无意义时方可强制")
            )

        # G6 组内有活跃下载成员: 共享物理文件被下载方写入, force 也救不回确定性脏数据(case 1);
        # 出路 = 先暂停下载方(组内暂停后 G6 过, 流程合法)
        if self._ctx.store.group_has_downloading(hash):
            verdicts.append(
                GateVerdict("G6", GATE_BLOCKED, "组内有种子正在下载: 组内成员共享同一物理文件, 下载方正在写入, "
                            "跳检会把全部块标有效(脏数据); 请先暂停组内下载方再跳检")
            )

        # ---- G7/G8 组内镜像闸门(S1b-2): members 数据源与规则侧同一真相(checking.py:93
        # grouping._group_members 即委托 store.group_members), 谓词逐字镜像, 镜像注释互指在 ops 侧
        members = self._ctx.store.group_members(hash)

        # G7 组内其它成员 full-checking 在途(case 2): 谓词逐字镜像 rules/actions/full_checking.py
        # _wait_for_group_checking.others_checking(决策链 1.5, others-only 排除自身), 两半视野:
        # 队列登记 active_check_hashes(规则发起) ∪ store 快照 is_checking(后半覆盖用户手动 recheck
        # —— G5 的队列视野看不见它)。跳检删种会杀死组员在途校验, 且不经其判决断言共享数据有效;
        # 赌注两面: 判决通过即证明文件完好 / 判决失败则坏数据被永久洗白 —— 同 G5 给 force 逃生
        others = [h for h in members if h != hash]
        inflight = self._ctx.task_queue.active_check_hashes()
        by_hash = self._ctx.store.by_hash
        if others and any(h in inflight or (h in by_hash and by_hash[h].state_enum.is_checking) for h in others):
            verdicts.append(
                GateVerdict(
                    "G7", GATE_FORCE, "同组种子正在全量校验中: 等其结束后再跳检, 校验通过即证明共享文件完好; "
                    "强制跳检将不经其判决断言数据有效, 若判决为失败坏数据将被永久洗白"
                )
            )

        # G8 组内成员校验失败推断(case 1): 四要件逐字镜像 rules/actions/full_checking.py
        # _skip_on_group_check_failed(决策链 1.6, others-only): 其它成员 / 当日计数(recheck_fails,
        # 含宽限耗尽/异常噪声 —— 继承规则侧既有假阳性面, 同日窗口+自愈条件兜底, 不发明更锐利谓词) /
        # 假失败自愈只读变体 / 文件映射一致。当日校验失败+同映射 = 数据已被证伪, 强制跳检 = 明知坏
        # 仍标有效并上传, force 无正当用途(「赌已输」与 G7 的「赌未定」有本质区别)
        key = self._ctx.store.member_to_key.get(hash)
        if key is not None:
            sizes = self._ctx.store.group_sizes.get(key, {})
            mine = sizes.get(hash)
            if mine:
                for h in members:
                    if h == hash or recheck_fail_count(self._ctx.state, h) <= 0:
                        continue
                    rec = self._ctx.store.get(h)
                    if rec is None or rec.progress >= 1.0:
                        # 只读自愈(T20): 假失败记录不参与推断且**不 pop**(规则侧此处 pop 记录,
                        # full_checking.py:146) —— 清理仍归规则侧与次日重置, 本判定零副作用
                        continue
                    if sizes.get(h) == mine:
                        verdicts.append(
                            GateVerdict(
                                "G8", GATE_BLOCKED, f"同组种子 {h[:8]} 今日校验失败且文件映射一致, "
                                "共享数据已证实有问题, 禁止跳检; 请先对该组做 full-checking"
                            )
                        )
                        break  # 同规则侧返回语义: 首个同映射失败成员即成判

        # partial 部分下载(既有闸门并入 detail, 文案零变化)
        if 0.0 < progress < 1.0:
            verdicts.append(
                GateVerdict("partial", GATE_BLOCKED, f"部分下载的种子禁止跳检(progress={progress}), 请改用 full-checking")
            )

        # dedup 跨规则同日去重(既有闸门并入 detail, 文案零变化; 只读 —— 不 setdefault 不 prune)
        skip_day = self.state.get("skip_check_day") or {}
        if skip_day.get(hash) == date.today().isoformat():
            verdicts.append(GateVerdict("dedup", GATE_BLOCKED, "今日已跳检过该种子(跨规则去重)"))

        # filelist 前置文件检查(排最后): 前面已有 blocked 未过 -> 短路(结论已注定, 省 files API);
        # 仅 force 类未过不短路(force 豁越后本闸门仍须真跑)
        if not any(v.cls == GATE_BLOCKED for v in verdicts):
            err = self.check_filelist(self._ctx.api, tor)
            if err is not None:
                text = f"跳检前置文件检查未通过: {err}"
                if err.startswith("路径不可判定"):  # 与 check_filelist 的映射 miss 文案前缀同源(同模块单点)
                    text += "; 请修正 fs.path_map 配置后重试"
                verdicts.append(GateVerdict("filelist", GATE_BLOCKED, text))
        return verdicts

    def _skip_delete(self, hash: str, tor: TorrentRecord, prefix: str) -> Optional[ActionResult]:
        """跳检步骤: 删除种子(保留文件)并轮询确认已从客户端消失(qB 删除为异步)。

        返回 None = 已确认消失; ActionResult = 失败(种子未删除或消失未确认, 无损失,
        放弃跳检避免重加撞"种子已存在")。
        """
        try:
            logger.info(f"{prefix} {tor.log_repr} | 跳检删除种子(保留文件)")
            self._ctx.api.torrents_delete(torrent_hashes=hash, delete_files=False)
        except Exception as e:
            return ActionResult.fail(f"删除种子失败(未删除, 无损失): {e}")
        gone = _poll_until(lambda: not self._ctx.api.torrents_info(torrent_hashes=hash), attempts=10, interval=0.5)
        if not gone:
            # 种子没删掉(删除未生效) —— 删除前的备份也就没了意义, 清掉: 留着只剩一个孤儿
            # .torrent 文件 + 一条"待恢复"的误导性元数据(state 会指引用户去恢复一个还在的种子)
            self._clear_backup(hash)
            return ActionResult.fail("删除后种子仍在客户端, 放弃跳检(重加会撞已存在的种子)")
        return None

    def _skip_readd(self, hash: str, tor: TorrentRecord, data: bytes,
                    content_layout: Optional[str]) -> Optional[ActionResult]:
        """跳检步骤: 以跳过校验方式重加(先暂停), 轮询确认出现, 恢复删除前快照记录。

        属性直传不用 `or None` —— ratio/seeding limit 的 0/负值是有语义的(不限速/跟随
        全局), 吞掉会使重加后行为漂移到 qB 新种缺省。重加成功后 store.restore_torrent
        恢复删除前记录(保留 tracker_conf/惰性缓存): remove_torrent 会登记待报 removed,
        不恢复则重加的同 hash 种子下轮被误判为已删除(生产 BUG 2026-09-06)。

        返回 None = 成功; ActionResult = 失败(种子已从客户端移除, 已备份提示手动恢复)。
        """
        try:
            self._ctx.api.torrents_add(
                torrent_files=[data],
                save_path=tor.save_path,
                category=tor.category or None,
                tags=tor.tags or None,
                upload_limit=tor.up_limit,
                download_limit=tor.dl_limit,
                is_sequential_download=tor.seq_dl,
                is_first_last_piece_priority=tor.f_l_piece_prio,
                contentLayout=content_layout,
                ratio_limit=tor.ratio_limit,
                seeding_time_limit=tor.seeding_time_limit,
                inactive_seeding_time_limit=tor.inactive_seeding_time_limit,
                share_limit_action=tor.share_limit_action,
                is_skip_checking=True,
                is_stopped=True,
            )
        except Exception as e:
            # 备份在删除前已落盘(此处再调一次是幂等的覆盖写, 只为让失败信息带上备份路径)
            backup = self._backup_torrent(tor, data)
            return ActionResult.fail(f"重加种子失败: {e}; 种子已从客户端移除(文件保留), "
                                     f".torrent 已备份: {backup}, 请手动重加")
        appeared = _poll_until(lambda: self._ctx.api.torrents_info(torrent_hashes=hash), attempts=3, interval=0.3)
        if not appeared:
            # 种子已从客户端移除, 备份已在删除前落盘 —— 保留它(不清), 用户凭
            # skip-check-backup/<hash>.torrent + state 元数据可手动恢复; store 此刻也无记录,
            # 下轮不会执行 restore_torrent, 该种子会被误判为"用户主动删除"。
            backup = self._backup_torrent(tor, data)
            return ActionResult.fail(f"重加后未确认到种子(客户端可能尚未处理完), 请检查客户端; "
                                     f"种子已从客户端移除(文件保留), .torrent 已备份: {backup}")
        self._ctx.store.restore_torrent(tor)
        # 跳检完成: 记录跨规则同日去重(此后同种子当日任何来源的 checking 都不再跳检)
        self.state.setdefault("skip_check_day", {})[hash] = date.today().isoformat()
        # 去重标记即时落盘: 这是"今天已跳检过"的唯一凭据, 只靠退出/周期落盘的话, 跳检后
        # 崩溃会重复跳检(PT 本地统计再丢一次)。跳检是天级低频事件, 即时写一次代价可忽略 ——
        # 与备份路径的即时落盘同口径(issue 26-09-21-1347)。注意不能指望下面的 _clear_backup
        # 顺带落盘: 备份元数据为空时它提前 return, 不经过 save_state。
        self.save_state()
        # 种子已回到客户端: 删除前那份备份完成使命, 清掉(否则每次跳检都留一个孤儿文件)
        self._clear_backup(hash)
        return None

    def _infer_content_layout(self, tor, client) -> Optional[str]:
        """推断原内容布局(qB 种子信息无直接字段): 重加后数据路径必须与现存文件一致,
        跳检状态下布局错位不会自愈(直接 missingFiles/空传)。无法推断返回 None(用 qB 默认)。

        须在删除种子前调用(传入删除前捕获的记录): 删除后 store 记录已移除, 且文件列表
        惰性缓存挂在记录上(空缓存时会向已删除的种子发请求)。

        - 文件路径均以 种子名/ 开头(.torrent 自带根目录): content==save -> NoSubfolder(原布局剥根),
          content==save/种子名 -> Original
        - 无根目录(含单文件): content==save -> Original; content==save/种子名 -> Original
        """
        save = utils.path_normalize(tor.save_path)
        content = utils.path_normalize(tor.content_path or "")
        if not content:
            return None
        name = utils.path_normalize(tor.name)
        files = tor.files(client)  # store 惰性缓存(filelist 前置检查已填充)
        has_root = bool(files) and all(utils.path_normalize(f.name).startswith(f"{name}/") for f in files)
        if content == save:
            return "NoSubfolder" if has_root else "Original"
        if content == f"{save}/{name}":
            return "Original"
        return None

    def _clear_backup(self, hash: str) -> None:
        """跳检未真正移除种子时清掉删除前的备份(文件 + 元数据), 元数据立即落盘

        与 _backup_torrent 成对: 备份是"删除前的保险", 只在种子确实没回到客户端时才有意义。
        重加确认成功(种子已回)或删除未生效(种子没丢)时留着它只剩副作用 —— 一个孤儿
        .torrent 文件 + 一条指向"待恢复"的误导性元数据。清理失败只记 warning(跳检本身已完成)。
        """
        meta = self.state.get("skip_check_backup", {}).pop(hash, None)
        if not meta:
            return
        path = meta.get("path") or ""
        if path:
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(f"清理跳检备份失败({path}): {e}")
        self.save_state()  # 元数据已改: 立即落盘, 否则崩溃后仍指向已删除的备份文件

    def _backup_torrent(self, tor, data: bytes) -> str:
        """删除前把 .torrent 落盘备份并记录元数据(便于手动恢复), 返回备份路径

        用删除前捕获的 tor 记录(删除后 store 记录已移除)。元数据立即落盘(非常规路径,
        不适用"仅退出时落盘"的写放大规避): 备份后程序一旦崩溃, 没有 state 里的元数据指引,
        用户不知道 .torrent 备份的存在与原始保存路径。

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
            "ts": time.time(),
        }
        self.save_state()
        return path

    # ---------- 文件完整性检查(checking 前置检查, 决策点 D2 并入 ops) ----------

    @staticmethod
    def check_filelist(api, torrent: TorrentRecord) -> str:
        """检查种子文件是否存在且大小一致(api 为 QbApi Facade或兼容客户端). 返回错误描述字符串, 全部通过返回 None"""
        logger.debug(f"{torrent.log_repr} | 检查文件完整性")
        try:
            files = api.torrents_files(torrent.hash)
        except Exception as e:
            return f"获取文件列表失败: {e}"
        save_path = torrent.save_path
        fa = file_access.get_file_access()
        for f in files:
            full_path = os.path.normpath(os.path.join(save_path, f.name))
            exists = fa.exists(full_path)
            if exists is file_access.UNDETERMINED:
                # 映射 miss: 存在性不可判定 —— 显式报「不可判定」而非「文件缺失」,
                # 让跳检前置保守停住但不误报缺失语义(报告 §05 红线)
                return f"路径不可判定: '{full_path}'(未命中 fs.path_map 映射)"
            if not exists:
                # 孪生(.!qB)存在 -> 文案提示疑似 qB 搬运过渡态(仅诊断信息, 返回语义不变:
                # 跳检前置仍按缺失保守停住); 探测同样经文件访问层, 非 True 按无孪生处理
                if fa.exists(utils.qb_incomplete_twin_path(full_path)) is True:
                    return f"文件缺失: {f.name}(疑似 qB {utils.QB_INCOMPLETE_SUFFIX} 过渡态)"
                return f"文件缺失: {f.name}"
            try:
                if fa.getsize(full_path) != f.size:
                    return f"文件大小不一致: {f.name}"
            except OSError:
                return f"无法读取文件: {f.name}"
        return None
