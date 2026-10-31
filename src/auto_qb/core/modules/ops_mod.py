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
import logging
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from ...infra import file_access, utils
from ...rules.base import ActionResult
from ...rules.checking_meta import (
    CHECK_RESULT_INTERVAL,
    CHECK_START_GIVEUP,
    INFLIGHT_TTL,
    RECHECK_FAIL_LIMIT,
    PollVerdict,
    bump_recheck_fail,
    is_piece_checking,
    poll_verdict,
    recheck_fail_count,
)
from ...torrents import TorrentRecord
from ..module import AppContext, BaseModule
from ..state import prune_day_keys
from ..taskqueue import FINISHED, REQUEUE, Task

logger = logging.getLogger(__name__)

# R1/R2 拒绝文案(自解释: checking 态在种子列表可见, 用户能对上原因)
_RECHECK_BUSY_MSG = "校验进行中, 请等待当前校验完成"
_SKIP_GONE_MSG = "种子已被移除(可能被用户删除), 放弃跳检"
_RECHECK_GONE_MSG = "种子已被移除(可能被用户删除), 放弃校验"  # 快照无记录时用(与 _SKIP_GONE_MSG 同族)

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


# 跳检相位机(计划 26-10-21-1857 §5): 每步至多 1 次写 + 1 次存在性读, 步间用毫秒级退避
# 代替原来的 500ms 轮询; 运行状态一个字不写(等 qB 上报), 删除也不摘记录(keep_record)。
SKIP_PHASE_PREPARING = "preparing"
SKIP_PHASE_DELETING = "deleting"
SKIP_PHASE_GONE = "gone"
SKIP_PHASE_ADDING = "adding"
SKIP_PHASE_APPEARED = "appeared"
SKIP_PHASE_FINISHING = "finishing"
SKIP_PHASE_DONE = "done"
SKIP_PHASE_FAILED = "failed"

_SKIP_TERMINAL = frozenset({SKIP_PHASE_DONE, SKIP_PHASE_FAILED})
# 相位重试退避(毫秒): 10/20/50/50/50 —— 覆盖 qB 删除/重加异步生效的典型窗口
_SKIP_BACKOFF_MS = (10, 20, 50, 50, 50)
# 单条跳检的总上限(秒): 删除→重加窗口不许无限拉长(PT/HR 视角种子长期不在客户端)
SKIP_DRIVE_TIMEOUT = 30.0
# 终态结果缓存条数(纯观测面: 规则侧/测试取异步终态 + 进度事件回放; 不参与判定)
_SKIP_RESULT_KEEP = 64


@dataclass
class SkipJob:
    """一条跳检的相位机状态(纯内存; 崩溃恢复账本见计划 S4)

    字段即相位推进所需的全部上下文: tor 是**删除前**的记录快照(备份/布局推断/打标判断都用它),
    data/content_layout 在 PREPARING 一次备齐(删除后取不到)。
    """

    hash: str
    tor: TorrentRecord
    source: str
    auto_start: bool
    has_reference: bool
    phase: str = SKIP_PHASE_PREPARING
    attempts: int = 0
    next_run: float = 0.0
    started_at: float = 0.0
    data: bytes = b""
    content_layout: Optional[str] = None
    backup: str = ""
    error: str = ""
    # 终态结算面(同步入口不传; 异步入口经 skip_submit 传入)
    on_done: Any = None  # 终态回调(web 批量聚合回执)
    origin: Any = None  # 规则任务(终态重新入队, 与 recheck 同构)
    result: Any = None  # 终态 ActionResult(同步入口直接返回它)
    settled: bool = False


class OpsModule(BaseModule):
    """ops 模块: recheck/跳检执行体 + 提交点检查 + 按 source 保护策略 + 文件完整性检查

    sections 认领 skip_checking_tag(跳检成功打标的标签名, 全局键); 其余消费面(api/store/
    state/task_queue)都是 ctx 服务, 无配置段。
    """

    name = "ops"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        # 在途跳检 job(相位机; 同步入口内联驱动, 异步入口由微步线推进)
        self._skip_jobs: dict = {}
        # 最近终态结果 {hash: ActionResult}(供规则侧/测试取异步终态, 也供进度事件回放);
        # 有界: 只留最近 _SKIP_RESULT_KEEP 条(纯观测面, 不参与判定)
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
        on_success=None,
        origin=None,
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
            submitted_at = time.time()
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        logger.info(f"{prefix} {self._ops_repr(tor)} | full-checking 校验已提交")
        if source == "rule":
            # pending: 规则记录断点, 规则任务本轮不重入队 —— 恢复由轮询子任务负责
            return ActionResult.pending("full-checking 校验已提交")
        return ActionResult.ok("校验已提交")

    # ---------- skip-checking: 相位机(准备/删除/确认/重加/确认/收尾) ----------

    def skip_check(
        self,
        hash: str,
        source: str = "rule",
        torrent: Optional[TorrentRecord] = None,
        auto_start: bool = False,
        has_reference: bool = True,
        force: bool = False,
    ) -> ActionResult:
        """辅种跳检(高风险): 准备(导出/布局/备份) → 删除(保留文件) → 确认消失 → 重加(跳过校验) → 确认出现 → 收尾

        执行体是相位机(`SkipJob`, 计划 26-10-21-1857 §5): 每步至多一次毫秒级调用, 等待用
        10~50ms 退避(原实现是 500ms × 10 轮询, 单条 ~6s)。两条硬约束: ①运行状态一个字不写 ——
        重加后的 state/progress 由 qB 下一轮上报落账(命令后直查不可靠); ②删除不摘记录
        (`keep_record=True`) —— delete+add 落在同一上报间隔内时, 摘了会踩「增量 diff 只给变化
        字段 → 新建记录缺字段」。执行序(plan 26-10-05-0314 §03/§04): R2 实时复核 → 前置闸门
        (filelist 排最后) → 准备 → 执行 —— 拒绝仍然零副作用(全部在备份与删除这两个不可逆步骤之前)。

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
        job, early = self._skip_begin(hash, source, torrent, auto_start, has_reference, force)
        if early is not None:
            return early
        job = self._skip_drive(job)
        return job.result

    def skip_submit(
        self,
        hash: str,
        source: str = "web",
        torrent: Optional[TorrentRecord] = None,
        auto_start: bool = False,
        has_reference: bool = True,
        force: bool = False,
        on_done=None,
        origin=None,
    ) -> ActionResult:
        """异步入口(批量 WEB): 只做前置与建 job, 相位推进交给主循环微步调度器

        与 `skip_check` 共用 `_skip_begin`(前置与闸门单点), 差别只在谁驱动相位:
        - 本入口返回 `pending`(已受理), 终态经 `on_done(job)` 回调(job.result 是终态结果);
        - 规则侧 `origin` 在终态重新入队(与 recheck 的 origin 重入队同构, S4 启用)。

        主循环每轮调 `advance_due()` 推进一步, 等待超时由 `next_run_at()` 并入(第三条时间线),
        因此批量 N 个 job 是并行推进的: 整批耗时 ≈ 相位深度 × 步间隔, 与 N 基本无关。
        """
        _, early = self._skip_begin(
            hash, source, torrent, auto_start, has_reference, force, on_done=on_done, origin=origin
        )
        if early is not None:
            return early
        return ActionResult.pending("跳检已受理")

    def _skip_begin(
        self,
        hash: str,
        source: str,
        torrent: Optional[TorrentRecord],
        auto_start: bool,
        has_reference: bool,
        force: bool,
        on_done=None,
        origin=None,
    ):
        """跳检共同前置(同步/异步两个入口共用): 存在性 → 幂等 → 自有写 → 搬迁 → R2 → 闸门

        返回 `(job, None)` 表示已建 job; `(None, ActionResult)` 表示被拒/放弃(零副作用)。
        """
        tor = torrent if torrent is not None else self._ctx.store.get(hash)
        if tor is None:
            return None, ActionResult.skip(_SKIP_GONE_MSG)
        if self.skip_job_active(hash):
            return None, ActionResult.skip("该种子的跳检已在执行中")

        # ---- S2 deferral 闸门(D-2, A 系 26-10-13-0540): 本程序刚对该种子或**其组任一成员**
        # 下发过停/起、qB 快照尚未回流 ⇒ 闸门读到的 state 陈旧, 本轮不出决策(免 G4/G6 陈旧-放行
        # ⇒ 脏数据洗白)。放置于执行路径入口(而非 _skip_gates_detail): 预检 skip_check_precheck
        # 是只读预览、其 cls 契约(blocked/force)不引入第四类; 执行路径拦下即可, 预检照旧摊开闸门。
        # WEB 命令路径不在 task 线(D-1 覆盖不到), 故在此单点补拦; 有界: own_writes 逐出/TTL 到期即恢复。
        if self._ctx.store.own_write_pending(hash):
            return None, ActionResult.skip("本程序刚下发过停/起操作, 状态尚未从 qB 回流(避免按陈旧快照误判); 请稍后重试")

        # ---- 搬迁窗口闸门(计划 26-10-18-1604 §2.3/P4): 组内正在整组迁移 ⇒ 跳检跳过
        # 跳检是「删除 + 以跳过校验方式重加」, 在文件正被 qB 搬走时重加会立刻进入缺文件态,
        # 且删除动作会打断搬运 —— 与 relocating 让路缺文件扫描是同一条纪律(登记单点在
        # RelocateModule, 这里只读)。
        if hash in (getattr(self._ctx.store, "relocating_hashes", None) or set()):
            return None, ActionResult.skip("该种子正在整组迁移(搬迁/建别名中): 迁移收尾后再跳检")

        # 提交前不再直查(26-10-21-2323 S3): 种子已不在时, 相位机的「导出 .torrent」会失败,
        # 失败路径据此撤掉快照里的残留记录 —— 比"提交前先查一次"少一条通道, 结果同样安全。

        # ---- 阶段 1: 前置闸门 (任一不过 → fail/skip 返回, 无副作用; filelist 排最后) ----
        gate = self._skip_gates(hash, tor, force=force)
        if gate is not None:
            return None, gate

        # ---- 阶段 2: 建 job(相位推进见 _skip_step / _skip_drive / advance_due) ----
        job = self._skip_job_new(hash, tor, source, auto_start, has_reference, on_done=on_done, origin=origin)
        return job, None

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
        skip_day = self.state.get("skip_check_day")
        if skip_day:
            # 只留当日 = 保留窗 keep_days=0 的特例(prune_day_keys 单点, 对齐
            # state/_prune_exec_history 与 speed_curve 的日键淘汰口径)
            prune_day_keys(skip_day, date.today(), 0, lambda k, v: v)
        return None

    @staticmethod
    def _dur_text(age: Optional[float]) -> str:
        """「已 N 分钟」文案片段(不足 1 分钟 / 时长未知 -> 空串); 纯展示, 不参与判定"""
        if age is None or age < 60:
            return ""
        return f", 已 {int(age // 60)} 分钟"

    def _checking_evidence(self, hash: str, tor: Optional[TorrentRecord]) -> Optional[tuple]:
        """「该种子有全量校验在途」的证据 -> (来源, 已进行秒数) 或 None(无)

        两半视野, 都只读本地已有的真相, **不发起任何 qB 查询**(命令后直查不可靠: 运行状态是
        qB 按 RefreshInterval 刷新的缓存, 见 issue 26-10-21-1812-bug-decision-moment-live-query):
        - 快照生效证据 is_piece_checking(checkingDL/checkingUP): 覆盖外部/手动发起的校验。
          !盲区: qB 对**停止态**种子不报 checking*(torrentimpl.updateState 的 checking_files
          分支要求 !isStopped, 停止时落回 stoppedDL/UP), 暂停中的校验在状态上看不见;
        - 队列在途登记(带 INFLIGHT_TTL): 覆盖本程序发起、qB 状态暂时看不见的校验; 超时视为
          登记泄漏(轮询任务已被丢弃) -> 记 WARNING 后忽略, 不让一个泄漏登记永久挡住闸门。
        """
        state = tor.state if tor is not None else ""
        if is_piece_checking(state):
            return ("state", self._ctx.store.state_age(hash))
        age = self._ctx.task_queue.active_check_age(hash)
        if age is None:
            return None
        if age > INFLIGHT_TTL:
            logger.warning(f"在途校验登记超时({age:.0f}s > {INFLIGHT_TTL:.0f}s): hash={hash[:8]} 视为登记泄漏并忽略"
                           f"(对应轮询任务已不存在)")
            return None
        return ("inflight", age)

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
        # 仅「暂停中未完成」放行; 做种态 p=1 落 G3/G5, 下载中等非 stopped 态 p<1 落 G4。
        paused_incomplete = state_enum.is_stopped and progress < 1.0
        evidence = self._checking_evidence(hash, tor)

        def g5_verdict() -> GateVerdict:
            """G5 同 hash 校验在途(case 2): 判决窗口抢跑是真不确定 —— 强制 = 杀死在途校验
            (已花 I/O 作废)且不经其判决断言数据有效; 用户明知本轮校验无意义(如误发起)时留逃生"""
            kind, age = evidence
            detail = f"state={tor.state}" if kind == "state" else "校验已提交, qB 状态尚未回流"
            return GateVerdict(
                "G5", GATE_FORCE, f"该种子正在全量校验({detail}{self._dur_text(age)}): 跳检会删除种子并使在途校验作废, "
                f"且不经其判决断言数据有效(若数据坏将被洗白); 确知本轮校验无意义时方可强制"
            )

        if not paused_incomplete:
            if progress >= 1.0:
                if evidence is not None:
                    # 已完成但在验(checkingUP): 必须走 G5 而不是 G3 —— 「已完成, 跳检无意义」在这里
                    # 是错话(它正在校验), 且 G3 是 blocked 无逃生, 会把「误发起的 recheck」堵死
                    verdicts.append(g5_verdict())
                else:
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
        elif evidence is not None:
            # 暂停未完成但在验: qB 对停止态种子不报 checking*(updateState 的 checking_files
            # 分支要求 !isStopped), 状态上看不见 —— 只能靠证据(在途登记/快照)提示
            verdicts.append(g5_verdict())

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
        others = [h for h in members if h != hash]

        # G7 组内其它成员 full-checking 在途(case 2): 与 G8 同口径 —— 只有**文件映射一致**的
        # 成员才参与(映射不同 = 校验的是另一份数据, 其判决与本次跳检的赌注无关; 组键
        # group_key_of 不含文件大小, 同路径不同大小的种子会落进同一组, 见 grouping_mod.py:49)。
        # 判定用 _checking_evidence(快照生效证据 ∪ 带 TTL 的在途登记), 不再用 state_enum.is_checking
        # —— 后者含 checkingResumeData(qB 启动/加种时的 resume data 比对, 通常几百 ms 内完成、
        # 批量加种还会排队, 且**不产生数据完整性判决**), 把它算作"在验"会让整组在 qB 重启期被挡。
        # 文案点名 blocker(hash8 + 名字 + state + 时长): 不点名时 N 个目标产出 N 条逐字相同的
        # 文案, 用户既不知道是谁在验、也无法去 qB 核对。
        key = self._ctx.store.member_to_key.get(hash)
        sizes = self._ctx.store.group_sizes.get(key, {}) if key is not None else {}
        mine = sizes.get(hash)
        for h in others:
            if mine and sizes.get(h) and sizes.get(h) != mine:
                continue  # 映射不一致: 不参与推断(对齐 G8 的 sizes.get(h) == mine)
            rec = self._ctx.store.get(h)
            ev = self._checking_evidence(h, rec)
            if ev is None:
                continue
            kind, age = ev
            detail = f"state={rec.state}" if kind == "state" and rec is not None else "校验已提交, qB 状态尚未回流"
            name = f"《{rec.name}》" if rec is not None and rec.name else ""
            verdicts.append(
                GateVerdict(
                    "G7", GATE_FORCE, f"同组种子 {h[:8]}{name}正在全量校验({detail}{self._dur_text(age)}): "
                    f"等其结束后再跳检, 校验通过即证明共享文件完好; 强制跳检将不经其判决断言数据有效, "
                    f"若判决为失败坏数据将被永久洗白"
                )
            )
            break  # 首个命中的 blocker 即成判(与 G8 同语义)

        # G8 组内成员校验失败推断(case 1): 四要件逐字镜像 rules/actions/full_checking.py
        # _skip_on_group_check_failed(决策链 1.6, others-only): 其它成员 / 当日计数(recheck_fails,
        # 含宽限耗尽/异常噪声 —— 继承规则侧既有假阳性面, 同日窗口+自愈条件兜底, 不发明更锐利谓词) /
        # 假失败自愈只读变体 / 文件映射一致。当日校验失败+同映射 = 数据已被证伪, 强制跳检 = 明知坏
        # 仍标有效并上传, force 无正当用途(「赌已输」与 G7 的「赌未定」有本质区别)
        # key / sizes / mine 与 G7 共用同一份组映射(上面已算), 不再各自重算
        if key is not None and mine:
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

    # ---------- 跳检崩溃恢复对账(计划 26-10-21-1857 §9) ----------

    def on_sync_line(self, force: bool) -> None:
        """同步线 hook: 首轮快照落地后做一次跳检备份对账(每进程一次)

        账本就是 `state.skip_check_backup` —— 它在删除**之前**落盘(崩溃安全的锚点), 所以
        "有备份" 等价于 "我们当时正准备删/已经删了这个 hash"。对账三分流:
        - 种子已回到客户端 -> 跳检已完成(或用户手动加回): 备份无意义, 清掉;
        - 种子不在且备份文件在 -> 崩溃发生在删除之后、重加之前: 用备份重加(seed_mode);
        - 种子不在且备份文件丢了 -> 只能报 ERROR 交人(没有恢复凭据)。
        """
        if self._skip_recovered or not self._ctx.store.by_hash:
            return
        self._skip_recovered = True
        self._recover_skip_backups()

    def _recover_skip_backups(self) -> None:
        """按备份账本对账(见 on_sync_line 三分流); 幂等: 处理过的条目会被清账"""
        backups = self.state.get("skip_check_backup") or {}
        if not backups:
            return
        for h in list(backups):
            meta = backups.get(h) or {}
            if h in self._ctx.store.by_hash:
                logger.info(f"跳检对账: {h[:8]} 已在客户端, 清理残留备份")
                self._clear_backup(h)
                continue
            path = meta.get("path") or ""
            if not path or not os.path.exists(path):
                logger.error(f"跳检对账: {h[:8]} 不在客户端且备份文件缺失({path or '无路径'}), 需人工处理")
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
                logger.warning(f"跳检对账: {h[:8]} 不在客户端(崩溃于删除之后), 用备份重加(未经哈希校验)")
                self._ctx.api.torrents_add(
                    torrent_files=[data],
                    save_path=meta.get("save_path"),
                    category=meta.get("category") or None,
                    tags=meta.get("tags") or None,
                    is_skip_checking=True,
                    is_stopped=True,
                )
            except Exception as e:
                logger.error(f"跳检对账: {h[:8]} 重加失败({e}), 备份保留: {path}")
                continue
            self._clear_backup(h)

    # ---------- 跳检相位机(计划 26-10-21-1857 §4/§5) ----------

    def _skip_job_new(
        self,
        hash: str,
        tor: TorrentRecord,
        source: str,
        auto_start: bool,
        has_reference: bool,
        on_done=None,
        origin=None
    ) -> SkipJob:
        """建 job 并入账(同 hash 在途即幂等覆盖: 调用方已先经 skip_job_active 拦过)

        同时把 hash 登记进 `store.skipping_hashes`: 删除→重加窗口内 sync 若报 torrents_removed,
        `_apply` 不把它当删除(记录不摘、不触发分组删除链路) —— 窗口抑制的登记点。
        """
        now = time.time()
        job = SkipJob(
            hash=hash,
            tor=tor,
            source=source,
            auto_start=auto_start,
            has_reference=has_reference,
            next_run=now,
            started_at=now,
            on_done=on_done,
            origin=origin,
        )
        self._skip_jobs[hash] = job
        self._ctx.store.skipping_hashes.add(hash)
        return job

    def skip_job_active(self, hash: str) -> bool:
        """该 hash 是否有跳检 job 在途(幂等判据; 内联驱动时仅覆盖调用栈内)"""
        return hash in self._skip_jobs

    def _skip_drive(self, job: SkipJob) -> SkipJob:
        """把 job 内联驱动到终态(保持规则侧同步 ActionResult 语义)

        每步一次调用, 等待用 `_SKIP_BACKOFF_MS` 退避; 总时长受 `SKIP_DRIVE_TIMEOUT` 约束。
        S3 起改为「提交即返回 + 主循环按 next_run_at 推进」, 本方法退化为同步驱动体。
        """
        deadline = time.time() + SKIP_DRIVE_TIMEOUT
        while not job.settled:
            self._skip_step(job)
            if job.settled:
                break
            now = time.time()
            if now >= deadline:
                self._skip_fail(job, "跳检执行超时(客户端未在期限内响应), 备份保留")
                break
            delay = min(job.next_run - now, deadline - now)
            if delay > 0:
                time.sleep(delay)
        return job

    def _skip_step(self, job: SkipJob) -> None:
        """推进一个相位(单步异常不逃逸: 规则侧按 ActionResult 收口)"""
        try:
            handler = {
                SKIP_PHASE_PREPARING: self._skip_step_prepare,
                SKIP_PHASE_DELETING: self._skip_step_delete,
                SKIP_PHASE_GONE: self._skip_step_gone,
                SKIP_PHASE_ADDING: self._skip_step_add,
                SKIP_PHASE_APPEARED: self._skip_step_appeared,
                SKIP_PHASE_FINISHING: self._skip_step_finish,
            }.get(job.phase)
            if handler is not None:
                handler(job)
        except Exception as e:
            self._skip_fail(job, f"跳检执行异常({job.phase}): {e}")
        if job.phase in _SKIP_TERMINAL and not job.settled:
            self._skip_settle(job)

    def _skip_settle(self, job: SkipJob) -> None:
        """终态结算(单点): 落 result → 出账 → 撤销窗口抑制 → 规则 origin 重入队 → 回调

        顺序有讲究: 先出账/撤抑制, 再重入队与回调 —— 回调里可能立刻提交同 hash 的新 job
        (用户连点), 此时旧 job 必须已经从 `_skip_jobs` 与 `skipping_hashes` 里消失。
        """
        job.settled = True
        if job.phase == SKIP_PHASE_DONE:
            job.result = ActionResult.ok("skip-checking 跳检完成并自动开始" if job.auto_start else "skip-checking 跳检完成")
        else:
            job.result = ActionResult.fail(job.error)
        self._skip_jobs.pop(job.hash, None)
        self._ctx.store.skipping_hashes.discard(job.hash)
        self._skip_results[job.hash] = job.result
        while len(self._skip_results) > _SKIP_RESULT_KEEP:
            self._skip_results.pop(next(iter(self._skip_results)), None)
        web = getattr(self._ctx, "web", None)  # 进度事件(前端 toast; web 未启用时静默跳过)
        if web is not None:
            try:
                web.notify(
                    "skip_check", {
                        "hash": job.hash,
                        "name": job.tor.name if job.tor is not None else "",
                        "ok": bool(job.result is not None and job.result.is_ok),
                        "message": job.result.message if job.result is not None else "",
                    }
                )
            except Exception as e:  # 事件广播失败不得影响已落定的终态
                logger.warning(f"ops[{job.source}] {job.hash[:8]} | 跳检进度事件广播失败: {e}")
        if job.origin is not None:
            self._ctx.task_queue.add_task(job.origin, keep_progress=(job.phase == SKIP_PHASE_DONE))
        if job.on_done is not None:
            try:
                job.on_done(job)
            except Exception as e:  # 回调异常不得影响已落定的终态
                logger.error(f"ops[{job.source}] {job.hash[:8]} | 跳检终态回调异常: {e}")

    def skip_result(self, hash: str):
        """该 hash 最近一次跳检的终态结果(异步入口用; 无记录 -> None)"""
        return self._skip_results.get(hash)

    def next_run_at(self) -> Optional[float]:
        """下一条跳检 job 的到期时刻(主循环等待超时的第三时间线); 无在途 job -> None"""
        if not self._skip_jobs:
            return None
        return min(job.next_run for job in self._skip_jobs.values())

    # 微步线 hook 契约(module.ModuleHost.run_micro_line / next_micro_run_at 认领口)

    def on_micro_line(self, dry_run: bool) -> None:
        """微步线: 每轮推进到期 job(dry-run 不写 qB)"""
        if dry_run:
            return
        self.advance_due()

    def next_micro_run_at(self) -> Optional[float]:
        """微步线最早到期时刻(= next_run_at; 契约名与内核 hook 对齐)"""
        return self.next_run_at()

    def advance_due(self, budget_ms: float = 50.0, budget_calls: int = 20) -> int:
        """推进到期的跳检 job: 每个 job 本轮至多一步, 预算(时间或步数)先到先止

        主循环每轮调用一次(命令线之后、暂停判断之后), 步间由 `next_run_at()` 并入等待超时 ——
        所以"等待"是 10~50ms 的退避, 不是任务节拍。返回本轮推进的 job 数(预算截断时 < 到期数)。
        """
        if not self._skip_jobs:
            return 0
        now = time.time()
        due = sorted(
            (j for j in self._skip_jobs.values() if j.next_run <= now and not j.settled), key=lambda j: j.next_run
        )
        if not due:
            return 0
        deadline = time.monotonic() + (budget_ms / 1000.0)
        stepped = 0
        for job in due:
            if stepped >= budget_calls or time.monotonic() >= deadline:
                break
            self._skip_step(job)
            stepped += 1
        return stepped

    def _skip_retry(self, job: SkipJob, message: str) -> bool:
        """本相位重试一次(10/20/50/50/50ms 退避); 次数耗尽 -> FAILED 并返回 False"""
        job.attempts += 1
        if job.attempts >= len(_SKIP_BACKOFF_MS):
            self._skip_fail(job, message)
            return False
        job.next_run = time.time() + (_SKIP_BACKOFF_MS[job.attempts] / 1000.0)
        return True

    def _skip_fail(self, job: SkipJob, message: str) -> None:
        """终态失败: 种子还在 -> 清掉无意义的备份(没有丢失, 无需恢复凭据);
        种子已不在 -> 保留备份, 并把快照里那条记录撤掉(它就是假账, 下轮上报按真删除处理);
        **看不见(直查异常) -> 什么都不动**: 备份可能是唯一恢复凭据, 宁可留着"""
        job.phase = SKIP_PHASE_FAILED
        job.error = message
        logger.warning(f"ops[{job.source}] {job.hash[:8]} | 跳检失败: {message}")
        try:
            live = self._ctx.api.torrents_info(torrent_hashes=job.hash)
        except Exception:
            return
        if live:
            self._clear_backup(job.hash)
            return
        self._ctx.store.remove_torrent(job.hash)

    def _skip_add_call(self, job: SkipJob) -> None:
        """下发重加(跳过校验 + 暂停): 属性直传, 0/负值有语义(不限速/跟随全局)不吞"""
        tor = job.tor
        self._ctx.api.torrents_add(
            torrent_files=[job.data],
            save_path=tor.save_path,
            category=tor.category or None,
            tags=tor.tags or None,
            upload_limit=tor.up_limit,
            download_limit=tor.dl_limit,
            is_sequential_download=tor.seq_dl,
            is_first_last_piece_priority=tor.f_l_piece_prio,
            contentLayout=job.content_layout,
            ratio_limit=tor.ratio_limit,
            seeding_time_limit=tor.seeding_time_limit,
            inactive_seeding_time_limit=tor.inactive_seeding_time_limit,
            share_limit_action=tor.share_limit_action,
            # qB 5.3 新增分享限制模式, 重加须原样回传(否则被静默重置为 Default);
            # camelCase kwarg: facade 纯透传, 库(2026.8.1 无具名参/2026.10.1 同理)对未知
            # kwargs 经 _format_payload 并进 POST data —— 键名必须与服务端 camelCase 一致;
            # 5.2 快照无该字段恒 None -> requests 对 None 值键不发(wire 完全不变)
            shareLimitsMode=tor.share_limits_mode,
            is_skip_checking=True,
            is_stopped=True,
        )

    def _skip_step_prepare(self, job: SkipJob) -> None:
        """准备: 导出 .torrent + 布局推断 + 备份落盘 —— 全部在删除之前完成(崩溃安全)"""
        try:
            job.data = self._ctx.api.torrents_export(torrent_hash=job.hash)
        except Exception as e:
            # 种子可能已不在客户端(提交前不再直查): 文案点明, 失败路径会撤掉残留记录
            self._skip_fail(job, f"导出 .torrent 失败(种子可能已不在客户端): {e}")
            return
        if not job.data:
            self._skip_fail(job, "导出 .torrent 为空")
            return
        job.content_layout = self._infer_content_layout(job.tor, self._ctx.api.client)
        try:
            job.backup = self._backup_torrent(job.tor, job.data)
        except Exception as e:
            self._skip_fail(job, f"跳检备份 .torrent 失败(未删除, 无损失): {e}")
            return
        job.phase = SKIP_PHASE_DELETING
        job.attempts = 0
        job.next_run = time.time()

    def _skip_step_delete(self, job: SkipJob) -> None:
        """删除种子(保留文件); keep_record=True: 不动快照(见 QbApi.torrents_delete 注)"""
        try:
            self._ctx.api.torrents_delete(torrent_hashes=job.hash, keep_record=True)
        except Exception as e:
            self._skip_fail(job, f"删除种子失败(未删除, 无损失): {e}")
            return
        logger.info(f"ops[{job.source}] {job.tor.log_repr} | 跳检删除种子(保留文件)")
        job.phase = SKIP_PHASE_GONE
        job.attempts = 0
        job.next_run = time.time()

    def _skip_step_gone(self, job: SkipJob) -> None:
        """确认消失(qB 删除是异步的; 存在性是会话级事实, 直查可靠)"""
        try:
            gone = not self._ctx.api.torrents_info(torrent_hashes=job.hash)
        except Exception as e:
            self._skip_retry(job, f"确认删除失败: {e}")
            return
        if gone:
            job.phase = SKIP_PHASE_ADDING
            job.attempts = 0
            job.next_run = time.time()
            return
        if not self._skip_retry(job, "删除后种子仍在客户端, 放弃跳检(重加会撞已存在的种子)"):
            return
        try:  # 重试一次删除(幂等)
            self._ctx.api.torrents_delete(torrent_hashes=job.hash, keep_record=True)
        except Exception:
            pass

    def _skip_step_add(self, job: SkipJob) -> None:
        try:
            self._skip_add_call(job)
        except Exception as e:
            self._skip_fail(job, f"重加种子失败: {e}; 种子已从客户端移除(文件保留), .torrent 已备份: {job.backup}, 请手动重加")
            return
        job.phase = SKIP_PHASE_APPEARED
        job.attempts = 0
        job.next_run = time.time()

    def _skip_step_appeared(self, job: SkipJob) -> None:
        try:
            appeared = bool(self._ctx.api.torrents_info(torrent_hashes=job.hash))
        except Exception as e:
            self._skip_retry(job, f"确认重加失败: {e}")
            return
        if appeared:
            job.phase = SKIP_PHASE_FINISHING
            job.attempts = 0
            job.next_run = time.time()
            return
        if not self._skip_retry(
            job, f"重加后未确认到种子(客户端可能尚未处理完), 请检查客户端; "
            f"种子已从客户端移除(文件保留), .torrent 已备份: {job.backup}"
        ):
            return
        try:  # 重试一次重加(撞"已存在"说明删除还没落地, 下一轮再看)
            self._skip_add_call(job)
        except Exception:
            pass

    def _skip_step_finish(self, job: SkipJob) -> None:
        """收尾: 无参考告警(规则语义) → 打标 → 自动开始 → 同日去重落盘 → 清备份"""
        prefix = f"ops[{job.source}]"
        tor = job.tor
        if job.source == "rule" and not job.has_reference:
            logger.warning(f"{prefix} {tor.log_repr} | 无参考跳检(高风险): 仅文件存在与大小对比, 内容错误会传垃圾数据")
        skip_tag = self._ctx.config.skip_checking_tag
        if skip_tag and skip_tag not in tor.tags_set:
            try:
                self._ctx.api.torrents_add_tags(tags=[skip_tag], torrent_hashes=job.hash)
                logger.info(f"{prefix} {tor.log_repr} | 跳检完成, 已打标签 {skip_tag}(该种子不作参考种子)")
            except Exception as e:
                logger.warning(f"{prefix} {tor.log_repr} | 跳检打标签失败(不影响跳检结果): {e}")
        if job.auto_start:
            try:
                self._ctx.api.torrents_start(torrent_hashes=job.hash)
            except Exception as e:
                self._skip_fail(job, f"自动开始失败: {e}")
                return
        # 跨规则同日去重: 此后同种子当日任何来源的 checking 都不再跳检; 即时落盘(崩溃即重复跳检)
        self.state.setdefault("skip_check_day", {})[job.hash] = date.today().isoformat()
        self.save_state()
        self._clear_backup(job.hash)
        job.phase = SKIP_PHASE_DONE

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
