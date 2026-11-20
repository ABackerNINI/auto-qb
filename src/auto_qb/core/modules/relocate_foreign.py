"""ForeignMixin: 外部旧路径种子侦测面(计划 26-11-20-0434 T2/S2, D7 落点 relocate 模块内新面)

IYUU 等外部工具按其缓存的旧 save_path 经 qB WEBUI 直接添加辅种种子 —— 整组迁移改过路径后,
这些种子落在旧路径上但不是任何 job 的成员(§02 两类坏法)。本面只做**侦测与分类**:

- 每拍消费同步层原始 added 差集(D12): store.last_added_diff 在 qbmanager tracker 匹配门
  之前现算(T1 批地基), 未匹配 tracker 配置的新种子同样进入 —— 本面每拍读、入候选池,
  判定成本 O(本拍新增), 与库内种子总数无关; 差集是「最近一拍」语义(每拍覆盖, 消费方只读
  不排空, T1 已定口径), 多拍间被覆盖的差集属 R3 接受的漏消费边界(时机兜底自愈)。
- 四时机全量兜底(D12/D13, 无周期兜底):
  1. 启动首轮 / 2. foreign_torrent 开关翻 true —— 两者共用「侦测闸门激活」信号面: 本面
     每 tick 观测 enabled AND foreign_torrent, 假->真跳变置待扫位(基线轮在位后触发)。
     开关翻转是真实信号: 配置热重载整体替换 Config 对象, ctx.config 即时可见;
  3. job arm(收尾窗开窗): 逐拍比对 armed/rewritten job_id 集合, 新进窗即触发(相位翻
     armed 的落点分散在 exec 多处, 集合比对免逐点接线);
  4. qB 重连首轮: store.sync_epoch(reset_sync 单点自增, T2 批新增)跨拍比对, 复位后首个
     成功应用轮(rounds_applied 前进)即触发。
- 候选判定(路径单点复用): save_path 归一(_norm 既有单点)恰等活跃 job 的旧根(job.src,
  含 plan.inherited 继承根) => 场景 A; 恰等终态账(done)的 src 旧根 => 场景 B, 数据现位置
  经 _foreign_resolve_old_root 单点解析(本批 = 直连边, T4 扩成传递闭包)。
- 文件清单比对(D4): 命中候选比对 rec 文件表 vs 命中 job 的 plan.files(单点复用
  PlanMixin._file_map / ExecMixin._plan_files 同归一口径含大小); **一致才进入分类处置,
  不一致只告警**(WARNING + 记 mismatch 账去重)。
- 去重(黄金法则 3 状态持久化): 活跃 job 成员(job.hashes 并集)幂等跳过 —— pre-arm 成员
  save_path 仍记旧根, 是「相位机在管」不是外部种子; 已通知 hash 记 state
  ``relocate.foreign.notified``(hash -> 简要信息: 来源旧根/类别/首见时刻/相位/现位置,
  T5 WebUI 面板直接消费本结构), 种子不在当前快照即清条目(重现 = 重新 first-seen 重处理)。
- 单拍有界 FIFO(R4): 一拍差集可能数十条(IYUU 批量辅种), 候选池内存队列 + 每拍处理
  预算(_FOREIGN_TICK_BUDGET)分拍消化; 预算只扣「文件表比对」这类真 qB API 成本, 纯路径
  判定的候选出队不受预算限。队列只存内存(重启丢失 = D13 接受的漏消费边界, 下次时机
  全量扫自愈), 池超上限丢最老(同样 D13 边界)。
- 相位信息(黄金法则 5 只读不写): 命中活跃 job 时把 job 现相位带进分类结果(T3 的
  暂停/恢复判据消费: 前段相位 = pre-armed 到达, armed/rewritten = 收尾窗到达)。

**本批(T2)只分类不处置**: 场景 A/场景 B 的处置动作分别在 T3/T5 批 —— 接缝
_foreign_on_scenario_a / _foreign_on_scenario_b 本批为空操作(DEBUG 留痕), 不得提前实现
任何纳入/通知动作; 清单不一致的 WARNING 是本批范围(D4, S2 验收判据)。

线程模型: 全部方法只在主循环线程执行(on_task_line hook, 黄金法则 5), 无新线程、无锁。
state 写面: 只写 relocate.foreign.notified 容器(仿 _state_jobs 的 setdefault 先例),
落盘沿用既有 state 机制(周期刷盘 + 优雅退出 save), 不自建。dry-run 全关(相位机同口径:
state 容器虽是内存账, 侦测面按「不真写」整体不跑, 与 on_task_line 的 dry 早退一致)。
"""
from dataclasses import dataclass
from typing import Any, Optional

from . import relocate_units as ru
from .relocate_common import logger

# 每拍文件表比对的预算上限(R4 有界 FIFO 的定界常量): 一次比对 = 一次 qB files API 拉取
# (record 级惰性缓存, 二次判定零请求)。10 = 主循环单拍最坏附加时延与「一次预检级批量
# 事实收集」同量级(任务线既有文件 API 批量调用同挂点); 数十条的 IYUU 突发(计划 R4 场景)
# 在 2s 节拍下数拍内消化完。非配置键(产品决策, 与 DONE_HISTORY_KEEP 同形态)。
_FOREIGN_TICK_BUDGET = 10

# 候选池内存上限(R4): 超限丢最老 —— 极端突发下接受 D13 漏消费边界(下次时机全量扫自愈),
# 不为消化洪峰扩内存或加周期兜底。1000 = 远超现实突定量级(单拍差集数十条)的防御值。
_FOREIGN_PENDING_MAX = 1000

# 已通知账的类别取值(kind 字段; T5 WebUI 面板按此分流呈现)
_KIND_SCENARIO_A = "A"  # 活跃 job 作用域命中(收尾窗内到达; T3 纳入)
_KIND_SCENARIO_B = "B"  # 终态账旧根命中(收尾完成后到达; T5 通知)
_KIND_MISMATCH = "mismatch"  # 清单不一致(D4: 只告警不处置)


@dataclass(frozen=True)
class ForeignEdge:
    """旧根 -> 现位置的直连边记录(_foreign_resolve_old_root 的产出形状)

    T4 把解析器扩成传递闭包(A->B->C 链)时沿本形状回多跳事实(经手 job 链); T2 只产
    单边, phase 恒 done(边来自终态账)。
    """

    job_id: str
    src: str
    dst: str
    phase: str


@dataclass(frozen=True)
class ForeignHit:
    """候选判定产出(单条候选的完整分类事实; 接缝方法与 T3/T5 的消费面)"""

    hash: str
    save_path: str
    scenario: str  # "A" | "B"(kind 取值同 _KIND_*)
    job_id: str  # 命中的 job(场景 A = 活跃 job; 场景 B = 终态账那条)
    phase: str  # 命中 job 的现相位(A: 活跃相位, T3 暂停/恢复判据; B: "done")
    old_root: str  # 命中的旧路径根(job.src / 继承条目 src 原形)
    location: str  # 数据现位置(A: job.dst; B: 终态账直连边解析值)


class ForeignMixin:
    """外部旧路径种子侦测面(混入 RelocateModule; 全部状态在宿主 __init__ 建档)"""

    # ---------- 每拍入口 ----------

    def _foreign_on_task_line(self, conf: Any) -> None:
        """外部旧路径种子侦测面每拍入口(on_task_line 首位调用, T2/S2)

        自查全部闸门后跑四件事: 时机观测(四时机全量兜底) -> 差集入池(D12) -> 候选池
        预算消费(R4) -> 已通知账清理。调用方无需预判开关 —— 闸门关时只做内存记账返回,
        门激活观测必须在 enabled 早退**之前**完成(否则「关->开」翻转漏观测, 重启用后
        漏启动首轮扫描)。

        闸门 = relocate.enabled AND relocate.foreign_torrent(D5 键门控; enabled 是前置 ——
        enabled=false 时 job 账不恢复, 候选判定无账可命中, 扫描纯空转)。dry-run 不跑
        (相位机同口径: 侦测面含 state 账写面, 干跑整体不启动; 记账面无副作用可继续)。
        """
        active = bool(conf is not None and getattr(conf, "enabled", False) and getattr(conf, "foreign_torrent", False))
        if self._foreign_seen_active is None or active != self._foreign_seen_active:
            if active:
                # 时机 1/2(启动首轮 / foreign_torrent 翻 true): 闸门激活 -> 待扫(基线轮在位
                # 才触发 —— 启动时 store 可能还没建过快照, 先等 baseline)
                self._foreign_need_first_scan = True
            self._foreign_seen_active = active
        if not active:
            return
        if self._dry_run():
            logger.debug("relocate | foreign | dry-run: 侦测面不启动(不记 notified 账)")
            return
        if self._ctx is None or self._ctx.store is None:
            return
        store = self._ctx.store
        reasons: list = []
        # rounds_applied 走 getattr 缺省 0: 替身 store(测试 SimpleNamespace)恒判「基线未建立 /
        # 无新应用轮」, 四时机全量与重连触发都不发生 —— 生产 TorrentStore 恒有该字段, 缺省只
        # 服务替身面(时机观测是纯内存记账, 不触 store 其它契约面)。
        rounds = getattr(store, "rounds_applied", 0)
        # 时机 1/2 触发: 基线轮已建立(首个成功应用轮之后)才扫 —— 扫的是存量不是空库
        if self._foreign_need_first_scan and rounds > 0:
            self._foreign_need_first_scan = False
            reasons.append("activation")
        # 时机 4(qB 重连首轮): sync_epoch 跨拍比对; 复位后首个成功应用轮(rounds_applied
        # 越过复位锚)即触发 —— 重连后第一拍可能全量轮已应用完, 锚落后即当拍触发
        epoch = getattr(store, "sync_epoch", 0)
        if self._foreign_sync_epoch is None:
            self._foreign_sync_epoch = epoch  # 首次观测只记基线(启动场景由时机 1 负责)
        elif epoch != self._foreign_sync_epoch:
            self._foreign_sync_epoch = epoch
            self._foreign_reconnect_round = rounds
        elif self._foreign_reconnect_round is not None and rounds > self._foreign_reconnect_round:
            self._foreign_reconnect_round = None
            reasons.append("reconnect")
        # 时机 3(job arm): 收尾窗(armed/rewritten)job_id 集合逐拍比对, 新进窗即触发
        window = frozenset(j.job_id for j in self.active_jobs() if j.phase in ru.FINALIZE_WINDOW_PHASES)
        if self._foreign_window is not None and not window <= self._foreign_window:
            reasons.append("arm")
        self._foreign_window = window
        if reasons:
            self._foreign_full_scan("+".join(reasons))
        # 每拍消费差集(D12): 原始 added 差集入候选池(只读不排空 store, 池即本面的消费游标)
        diff = getattr(store, "last_added_diff", None) or frozenset()
        for h in diff:
            self._foreign_enqueue(h)
        self._foreign_drain()
        self._foreign_cleanup_notified()

    # ---------- 四时机全量兜底(D12) ----------

    def _foreign_full_scan(self, reason: str) -> int:
        """全量兜底扫描: 遍历当前种子集, 命中候选入池(与差集共用同一条消费管线)

        只在四时机触发(启动首轮 / job arm / 开关翻转 / qB 重连首轮), 无周期兜底(D13)。
        判定是纯路径比对(零 qB 请求), O(库内总数) 只发生在时机拍; 命中入池后走预算管线
        (文件比对才是 API 成本面), 全量扫本身不绕过 R4 预算。返回本次入池候选数。
        """
        store = self._ctx.store
        notified = self._state_foreign_notified()
        members = self.relocating_hashes()
        enqueued = 0
        for rec in store.all():
            h = rec.hash
            if h in notified or h in members:
                continue  # 已记录 / 相位机在管: 不入池(去重单点在 _foreign_drain 消费面)
            try:
                hit = self._foreign_classify(rec)
            except Exception as e:  # noqa: BLE001 - 单记录坏不得拖垮整次扫描(逐 job 护栏同款)
                logger.debug(f"relocate | foreign | 扫描跳过坏记录 {h[:8]}: {e}")
                continue
            if hit is not None:
                enqueued += self._foreign_enqueue(h)
        logger.info(f"relocate | foreign | 全量兜底扫描({reason}): 入池候选 {enqueued} 条")
        return enqueued

    # ---------- 候选判定管线(纯路径, 零 qB 请求) ----------

    def _foreign_classify(self, rec: Any) -> Optional[ForeignHit]:
        """候选判定单点: save_path 命中活跃 job 旧根 => 场景 A; 命中终态账旧根 => 场景 B

        未命中返回 None。全量兜底与差集候选共用本管线(D12 口径: 全量扫 = 逐条跑同一判定)。
        命中判据 = save_path 归一(ru._norm 既有单点, 平台折叠口径)恰等于 job 旧根 ——
        IYUU 按其缓存的成员 save_path 添加, 与 job.src 同一根; 子目录落点由添加预检
        (precheck_add/evaluate_add 确认框)覆盖, 不在本面射程。
        """
        save_path = getattr(rec, "save_path", "") or ""
        if not save_path:
            return None
        n_sp = ru._norm(save_path)
        if not n_sp:
            return None
        # 场景 A: 活跃 job 旧根(job.src 直连 + plan.inherited 继承根 —— 继承别名改指收敛
        # 前后都挂在本 job 名下, 与 scope_hit 的继承面同口径)
        for job in self.active_jobs():
            if ru._norm(job.src) == n_sp:
                return ForeignHit(
                    hash=rec.hash,
                    save_path=save_path,
                    scenario=_KIND_SCENARIO_A,
                    job_id=job.job_id,
                    phase=job.phase,
                    old_root=job.src,
                    location=job.dst,
                )
            for entry in job.inherited:
                if entry.src and ru._norm(entry.src) == n_sp:
                    return ForeignHit(
                        hash=rec.hash,
                        save_path=save_path,
                        scenario=_KIND_SCENARIO_A,
                        job_id=job.job_id,
                        phase=job.phase,
                        old_root=entry.src,
                        location=job.dst,
                    )
        # 场景 B: 终态账旧根(现位置经单点解析器)
        edge = self._foreign_resolve_old_root(save_path)
        if edge is None:
            return None
        return ForeignHit(
            hash=rec.hash,
            save_path=save_path,
            scenario=_KIND_SCENARIO_B,
            job_id=edge.job_id,
            phase=edge.phase,
            old_root=edge.src,
            location=edge.dst,
        )

    def _foreign_resolve_old_root(self, old_root: str) -> Optional[ForeignEdge]:
        """旧根反查现位置(**单点**, 场景 B 命中面)

        本批(T2)实现 = 终态账 done job 的 src->dst **直连边**(同根多条按 updated_at 新->旧
        取最新, job_id 稳定兜底 —— 与 ru.job_rank 终态分支同序)。failed/cancelled 不产边
        (失败零成本收尾不搬回, 数据仍在旧根, 新种子落旧根是合法落位不是场景 B)。

        **T4 扩展点**(计划 S4: 链式闭包解析器): 链式再迁移 A->B->C 的老边在链上各代 job 账
        / plan.inherited 里, 本方法届时改写为「从 old_root 起沿终态账边反复行走至不再有边」
        的闭包解析(同根多条按 job_rank 取新), 入参/出参形状(ForeignEdge)不变, 消费方
        (classify/通知文案)无感。老边滚出终态账(20 条滚动) => 返回 None, 调用方按
        「映射已过期」处置(R7)。
        """
        n_root = ru._norm(old_root)
        if not n_root:
            return None
        best = None
        for job in self._jobs.values():
            if job.phase != ru.PHASE_DONE or ru._norm(job.src) != n_root:
                continue
            # 终态选取序 = ru.job_rank 的终态分支((not terminal, updated_at, job_id) 的
            # 终态退化形): 同根多条 done 按 updated_at 新->旧, job_id 稳定兜底
            if best is None or (best.updated_at, best.job_id) < (job.updated_at, job.job_id):
                best = job
        if best is None:
            return None
        return ForeignEdge(job_id=best.job_id, src=best.src, dst=best.dst, phase=best.phase)

    # ---------- 候选池(R4 有界 FIFO, 只存内存) ----------

    def _foreign_enqueue(self, h: str) -> int:
        """候选入池(去重; dict 当插入序集合用 —— O(1) 成员判定 + FIFO 出队序一体)

        返回实际入池数(0/1)。超上限丢最老: D13 接受的漏消费边界, 下次时机全量扫自愈。
        重启池清空(黄金法则 3 的刻意例外: 池是消费游标不是事实账, 丢失边界由 D13 承担)。
        """
        pending = self._foreign_pending
        if h in pending:
            return 0
        pending[h] = None
        while len(pending) > _FOREIGN_PENDING_MAX:
            oldest = next(iter(pending), None)
            if oldest is None:
                break
            del pending[oldest]
            logger.warning(f"relocate | foreign | 候选池超上限, 丢弃最老候选 {oldest[:8]}(时机兜底自愈)")
        return 1

    def _foreign_drain(self) -> None:
        """候选池预算消费(R4): 每拍至多 _FOREIGN_TICK_BUDGET 次文件表比对, 超出走下拍

        纯路径判定的候选(不命中/成员/已记录)出队不受预算限 —— 预算只定界真 qB API 成本
        (文件表拉取); 预算尽即止, 未及候选按插入序留池(FIFO 序不变, 下拍续)。

        **先处理后出队**: 出队一律在候选处理成功之后 —— 单候选处理抛异常(现实触发面 =
        ExecMixin._plan_files 的 int(b) 对 state 恢复畸形 plan.files)按 lifecycle 逐 job
        护栏(on_task_line 逐 _advance 的 try/except)同款纪律就地降级记日志**不传播**,
        候选原位留池待下拍重试(每拍至多重试一次, 账面修复即自愈) —— 单候选坏不得拖垮
        同拍其它候选与任务线; 同候选重复异常 WARNING 一次后转 DEBUG 静默重试, 不逐拍刷屏。
        文件表不可判定的候选出队不重试(重试靠时机兜底扫, 不占池位不空转)。
        """
        pending = self._foreign_pending
        if not pending:
            return
        store = self._ctx.store
        budget = _FOREIGN_TICK_BUDGET
        for h in list(pending):  # 插入序快照(= FIFO 序); 处理成功才出队
            if budget <= 0:
                break  # 预算尽: 余量按原序留池下拍续
            rec = store.get(h)
            if rec is None:
                self._foreign_pop(h)  # 排队期间消失: 出队(存活面由 notified 清理兜底)
                continue
            try:
                hit = self._foreign_classify(rec)
                if hit is None:
                    self._foreign_pop(h)  # 未命中(入池后旧根已被摘/账面变化): 出队
                    continue
                if rec.hash in self.relocating_hashes():
                    self._foreign_pop(h)  # 活跃 job 成员(相位机在管): 幂等出队
                    continue
                notified = self._state_foreign_notified()
                if rec.hash in notified:
                    self._foreign_pop(h)  # 已记录: 去重出队
                    continue
                budget -= 1
                verdict = self._foreign_files_match(rec, hit)
                if verdict is None:
                    logger.debug(f"relocate | foreign | {h[:8]} 文件表不可判定, 待时机兜底重扫")
                    self._foreign_pop(h)  # 出队不重试(不占池位不空转), 重试靠时机兜底扫
                elif not verdict:
                    self._foreign_record_mismatch(rec, hit)
                    self._foreign_pop(h)
                else:
                    self._foreign_record_hit(rec, hit)
                    self._foreign_pop(h)
            except Exception as e:  # noqa: BLE001 - 单候选异常不得拖垮同拍其它候选与任务线
                self._foreign_failed_once(h, e)
                continue  # 原位留池(先处理后出队的护栏面): 下拍重试一次

    def _foreign_pop(self, h: str) -> None:
        """候选出队单点(池摘除 + 异常告警去重位一并清)"""
        self._foreign_pending.pop(h, None)
        self._foreign_failed_warned.discard(h)

    def _foreign_failed_once(self, h: str, e: Exception) -> None:
        """单候选处理异常的降级记账(护栏面): WARNING 一次, 同候选重复异常转 DEBUG 静默重试

        去重位随候选出队(_foreign_pop)清 —— 账面修复后再次变坏的候选重新告警一次。
        """
        if h in self._foreign_failed_warned:
            logger.debug(f"relocate | foreign | 候选 {h[:8]} 处理异常(留池重试, 已告警过): {e}")
            return
        self._foreign_failed_warned.add(h)
        logger.warning(f"relocate | foreign | 候选 {h[:8]} 处理异常, 原位留池待下拍重试: {e}")

    # ---------- 文件清单比对(D4) ----------

    def _foreign_files_match(self, rec: Any, hit: ForeignHit) -> Optional[bool]:
        """种子文件清单 vs 命中 job 的 plan.files(D4: 同归一口径含大小)

        归一单点复用既有实现: 种子侧 PlanMixin._file_map(ru._norm 不折叠口径 + files API
        惰性缓存), 账面侧 ExecMixin._plan_files(plan.files 再过同一归一 —— plan.files 落账
        时已是归一形, 幂等)。返回 None = 不可判定(qB 不在 / job 账不在 / 种子文件表读空而
        账面非空 —— 不把事实缺失误报成「清单不一致」), 调用方不记账不告警, 重试靠时机兜底。
        """
        api = getattr(self._ctx, "api", None)
        client = getattr(api, "client", None) if api is not None else None
        if client is None:
            return None
        job = self.get_job(hit.job_id)
        if job is None:
            return None  # 账面已不在(撤销/清账竞态): 不可判定, 时机兜底重扫
        got = self._file_map(rec, client)  # {归一相对路径: 大小}
        plan_files = self._plan_files(job)  # [(相对路径, 大小)]
        want = {ru._norm(name, fold_case=False): int(size) for name, size in plan_files}
        if not got and want:
            return None
        return got == want

    # ---------- 记账与接缝(本批只分类不处置) ----------

    def _foreign_record_hit(self, rec: Any, hit: ForeignHit) -> None:
        """命中且清单一致: 记 notified 账 + 调场景接缝(本批接缝空操作, T3/T5 落点)"""
        notified = self._state_foreign_notified()
        notified[rec.hash] = {
            "root": ru._norm(hit.old_root),  # 来源旧根(归一形, 与判定口径一致)
            "kind": hit.scenario,  # 类别: A / B(T5 面板分流)
            "job_id": hit.job_id,
            "phase": hit.phase,  # A: 活跃相位(T3 暂停/恢复判据); B: "done"
            "location": hit.location,  # B: 数据现位置(通知文案用); A: job.dst
            "first_seen": self._clock.now(),  # 首见时刻(挂钟, 展示用)
        }
        logger.info(
            f"relocate | foreign | 发现旧路径外部种子 {rec.hash[:8]} (场景 {hit.scenario}, "
            f"job {hit.job_id}, 相位 {hit.phase}, 旧根 {hit.old_root}) —— 已记账, 处置在 T3/T5 批"
        )
        if hit.scenario == _KIND_SCENARIO_A:
            self._foreign_on_scenario_a(hit)
        else:
            self._foreign_on_scenario_b(hit)

    def _foreign_record_mismatch(self, rec: Any, hit: ForeignHit) -> None:
        """命中但清单不一致(D4): 只告警 + 记 mismatch 账(去重), 绝不进分类处置"""
        notified = self._state_foreign_notified()
        notified[rec.hash] = {
            "root": ru._norm(hit.old_root),
            "kind": _KIND_MISMATCH,
            "job_id": hit.job_id,
            "phase": hit.phase,
            "location": hit.location,
            "first_seen": self._clock.now(),
        }
        logger.warning(
            f"relocate | foreign | 旧路径种子 {rec.hash[:8]} 文件清单与 job {hit.job_id} 计划不符, "
            f"不处置只告警(D4) —— 旧根 {hit.old_root}, 请人工核对是否同目录异内容(R5)"
        )

    def _foreign_on_scenario_a(self, hit: ForeignHit) -> None:
        """**场景 A 接缝**(收尾窗内到达的旧路径同内容种子): T3 批落「零破坏纳入收尾」

        T3 在此实现(计划 S3): 追加 job.hashes + 读-改-写 spec["members"](hash_v1/v2 双
        hash, 复用 _torrent_v2_of); pre-armed(前段相位 moving/watching/moved)到达纳入即
        torrents_pause + 入 resume_hashes, arm 随成员恢复(D10); armed/rewritten 到达不动;
        pending_tag 增量补打。**本批(T2)空操作** —— 只在 DEBUG 留分类事实, 不得提前实现
        任何纳入/暂停/标签动作。入参 hit.phase 即 pre-arm 判据的现成位(黄金法则 5 只读)。
        """
        logger.debug(f"relocate | foreign | 场景 A 接缝(T3 落点): {hit.hash[:8]} 待纳入收尾")

    def _foreign_on_scenario_b(self, hit: ForeignHit) -> None:
        """**场景 B 接缝**(收尾完成后到达的旧路径种子): T5 批落「只通知」

        T5 在此实现(计划 S5): WARNING 日志(含数据现位置或「映射已过期」, R7) + WebUI
        relocate 面板「旧路径外部种子」列表/计数(数据源 = relocate.foreign.notified 账,
        结构见 _foreign_record_hit, T5 不要改结构)。**本批(T2)空操作** —— 不得提前实现
        任何通知动作(清单不一致的 WARNING 属 D4 判定面, 在 _foreign_record_mismatch)。
        """
        logger.debug(f"relocate | foreign | 场景 B 接缝(T5 落点): {hit.hash[:8]} 待通知")

    # ---------- state 账面 ----------

    def _state_foreign_notified(self) -> dict:
        """state.json 的 relocate.foreign.notified 容器(惰性创建; 上下文缺失返回空 dict 不炸)

        形状: {hash: {"root", "kind", "job_id", "phase", "location", "first_seen"}} ——
        T5 WebUI 面板的直接数据源(T5 只做呈现不改结构)。落盘沿用既有 state 机制: 容器
        挂 ctx.state.data(单一写线程 = 主循环), 周期刷盘 + 优雅退出 save 覆盖, 不自建
        (黄金法则 3; 仿 _state_jobs/_state_probes 的 setdefault 先例)。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return {}
        return data.setdefault("relocate", {}).setdefault("foreign", {}).setdefault("notified", {})

    def _foreign_cleanup_notified(self) -> None:
        """已通知账清理: 种子不在当前快照即清条目(重现 = 重新 first-seen, 重处理重告警)"""
        notified = self._state_foreign_notified()
        if not notified:
            return
        store = self._ctx.store
        for h in list(notified):
            if h not in store:
                del notified[h]
                logger.debug(f"relocate | foreign | 种子 {h[:8]} 已消失, 清理已通知账条目")
