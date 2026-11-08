"""relocate 生命周期叶: 启动/停止/热重载/job 登记/推进分派(自 relocate_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 relocate_mod.py 原文件逐字一致。
"""
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Optional

from ...infra import alias_fs
from ..module import AppContext, ApplyResult
from . import relocate_units as ru
from .relocate_units import RelocateJob
from .relocate_common import logger
from .relocate_probe import sweep_probe_residue

if TYPE_CHECKING:
    from ...config import Config

# 标签镜像失败后的重试间隔(秒): qB 失联/超时/版本不支持时只告警, 不阻塞迁移主流程,
# 也不每 tick 撞一次 qB。配置关闭时该常量不参与任何路径。
_TAG_RETRY_SECONDS = 30.0


class LifecycleMixin:
    def start(self, ctx: AppContext, dry_run: bool) -> None:
        """记录上下文与初始配置; enabled 时探测一次链接能力 + 恢复 job 账(开关关时零副作用, R15)"""
        self._ctx = ctx if ctx is not None else self._ctx
        self._dry = bool(dry_run)
        self._conf = ctx.config.relocate
        if getattr(self._conf, "enabled", False):
            alias_fs.get_capability(refresh=True)
            n = self._load_jobs()
            # E1 探测崩溃残留扫描(计划 26-11-04-0055 P2-⑥): add 之后 delete 之前被杀会在用户
            # qB 留探测种子+文件, 启动时按 tag 清理(R2); dry-run 不动手(真写, 与相位机同口径)
            swept = 0 if self._dry_run() else sweep_probe_residue(ctx)
            swept_note = f", 启动扫描清理探测残留 {swept} 条" if swept else ""
            logger.info(f"relocate | 启动: 整组迁移已启用(恢复在途 job {n} 条), 已完成本机链接能力探测{swept_note}")
        else:
            logger.debug("relocate | 启动: 未启用(enabled=false), 不探测不建链不恢复 job")

    def stop(self) -> None:
        """优雅退出: job 账已在每次推进时落 state(周期落盘由 state 服务兜底), 此处只补一次

        补写只在本会话接管过 job 账(_load_jobs 恢复过 / register_job/_set_job 动过)时做:
        _persist 是整段重写(内存表覆盖 state 的 relocate.jobs), 而 enabled=false 启动且未
        热启用时内存 _jobs 为空 —— 无条件补写会把 state 里的历史在途 job 整段清空, 紧随
        stop_all 的 ctx.state.save() 落盘后清账即永久失账(别名链接无人收口、未收尾拦截失明)。
        跳过补写 = state 维持上次会话的账, 下次启用时由 _load_jobs 正常恢复。

        回收 daemon 是独立进程, 不随 auto-qb 消亡(D10 收敛公理: 它要在 auto-qb 不在时
        也能捕窗改写) —— 故 stop() 不碰 daemon(退位走 pid 抢占自检自杀, 绝不 taskkill),
        也不删别名(qB 可能还在跑, 删链接会造假种)。
        """
        if not self._jobs_loaded:
            logger.debug("relocate | stop: 本会话未接管 job 账, 跳过补写(state 既有账原样保留)")
            return None
        try:
            self._persist()
        except Exception:  # noqa: BLE001 - 退出路径不抛: state 落盘失败不影响进程退出
            logger.debug("relocate | stop: state 补写跳过(上下文不可用)")
        return None

    def apply(self, old: "Config", new: "Config") -> ApplyResult:
        """段相等短路; 段变化 = 换对象即生效(enabled 开时重探链接能力)

        认领面含 bt_backup(计划 26-11-05-0808 S1): 预检部署闸经 bt_backup_path_of 现读
        ctx.config(L0, 无缓存), 段变化换对象即生效 —— 这里只做「变化可感知」的回执,
        不换缓存。relocate 与 bt_backup 两段独立比较, 任一变化即 reloaded。
        热启用(enabled 假 -> 真)与 start() 的启用分支同口径: 补一次 _load_jobs ——
        以 disabled 启动后热启用的会话, state 里的历史在途 job(崩溃/停用期残留)不恢复
        就永久休眠(on_task_line 只推内存账), _sync_relocating 也不重建, 未收尾拦截对
        这批成员失明。仅在「假 -> 真」跳变时灌: 持续启用下的段变化不重灌(重灌会重置
        在途 job 的运行期账 _rt, 无谓回到恢复判据)。
        """
        relocate_changed = getattr(old, "relocate", None) != getattr(new, "relocate", None)
        bt_backup_changed = getattr(old, "bt_backup", None) != getattr(new, "bt_backup", None)
        if not relocate_changed and not bt_backup_changed:
            return ApplyResult(self.name)
        if bt_backup_changed and not relocate_changed:
            return ApplyResult(self.name, "reloaded", "bt_backup 路径表已更新(部署闸现读, 下轮预检即生效)")
        was_enabled = bool(getattr(getattr(old, "relocate", None), "enabled", False))
        self._conf = getattr(new, "relocate", None)
        enabled = bool(getattr(self._conf, "enabled", False))
        restored = 0
        if enabled:
            alias_fs.get_capability(refresh=True)
            if not was_enabled:
                restored = self._load_jobs()
        detail = "relocate 段已更新(生效配置已缓存" + (", 已重探链接能力" if enabled else ", 未启用不重探")
        if restored:
            # 不写「在途」: _load_jobs 整箱恢复, 计数含终态 job(终态永久留账), 长期部署热启用几乎必然多报
            detail += f", 恢复 job {restored} 条"
        return ApplyResult(self.name, "reloaded", detail + ")")

    # ---------- job 登记(P3 执行体的账; P2 只读消费) ----------

    def register_job(self, job: RelocateJob) -> None:
        """登记/更新一个在途迁移(job_id 同键覆盖; P3 相位推进时逐次调用)"""
        self._jobs[job.job_id] = job
        self._jobs_loaded = True  # 本会话动过账(stop() 补写闸的依据, 见 RelocateModule.__init__ 注)
        self._publish_snapshot()

    def active_jobs(self) -> tuple:
        """非终态 job 视图(未收尾拦截与别名作用域判定的数据源)"""
        return tuple(j for j in self._jobs.values() if not j.is_terminal)

    def jobs_view(self) -> list:
        """全部 job 的界面视图(终态一并列出: 失败现场要可见 —— §3.5.1「保留现场交人处理」)"""
        return [ru.job_to_dict(j) for j in self._jobs.values()]

    def jobs_snapshot(self) -> ru.RelocateSnapshot:
        """WebUI 消费的只读 job 快照(主循环发布; 调用方不得遍历/改写)"""
        return self._snapshot

    def get_job(self, job_id: str) -> Optional[RelocateJob]:
        return self._jobs.get(job_id)

    # ---------- 物理位置解析(§3.4 第 1 层; P4 组判定消费) ----------

    def resolve_physical(self, save_path: str, content_root: str = "") -> str:
        """组判定用的物理目录解析: 命中活跃 job 作用域 ⇒ dst, 否则原样(开关关 = 逐字节现状)"""
        if not save_path:
            return save_path
        try:
            return ru.resolve_physical(save_path, content_root or save_path, self.active_jobs())
        except Exception:  # noqa: BLE001 - 解析失败退回原路径: 组判定绝不因迁移功能而崩
            return save_path

    def _mark_issued(self, job: RelocateJob) -> RelocateJob:
        """落账「已向 qB 下发过 setLocation」(重启恢复判据 _recover 消费; 幂等)

        与 _persist 的先后是**账先落、指令后发**(§3.5.1): 本方法在 setLocation 返回之后才调,
        故账上出现这一位 ⇔ qB 确实收到过搬迁。缺了它, 重启后「从未下发」与「下发了没动静」
        在 qB 侧同形, 只能靠猜。
        """
        return job if job.move_issued else self._set_job(replace(job, move_issued=True))

    def _resume_members(self, job: RelocateJob) -> None:
        """恢复本 job 发起时被暂停的成员(幂等: 无暂停成员即 no-op)

        _start_job 为按住搬迁窗口先暂停组内运行中成员并记进 resume_hashes; 此后任何出口
        要么「迁移成了」(武装/单成员收口/撤销成功)要么「没成」—— 后者不恢复的话, 整组
        成员会永久停在暂停态而日志一字不提(做种静默中断, 用户只能靠猜)。故恢复与置相位
        一样是收口的必做项, 不是可选的美化。恢复失败只告警: 数据面未动, 用户可手动起。
        """
        if not job.resume_hashes:
            return
        try:
            self._ctx.api.torrents_resume(torrent_hashes=list(job.resume_hashes))
        except Exception as e:  # noqa: BLE001 - 恢复失败只记: 数据面未动, 用户可手动恢复
            logger.warning(
                f"relocate | job {job.job_id}: 恢复成员运行态失败({e}) —— "
                f"{len(job.resume_hashes)} 个成员仍被暂停, 需手动恢复: {', '.join(job.resume_hashes)}"
            )
            return
        logger.info(f"relocate | job {job.job_id}: 已恢复 {len(job.resume_hashes)} 个成员的运行态")

    def _fail(self, job: RelocateJob, reason: str, last_error: str = "") -> RelocateJob:
        """失败收口单点: 置 FAILED + 消费 resume_hashes(把发起时暂停的成员放回去)

        失败 = 「这次迁移没成」: 被暂停的成员必须回到运行态(见 _resume_members 的为什么);
        数据面一律保留现场 —— 不搬回、不删链接, 交人处理(§3.5.1)。相位机所有失败出口
        一律走这里, 免得漏一个就留一批静默暂停的种子。
        """
        failed = self._set_job(replace(job, phase=ru.PHASE_FAILED, reason=reason, last_error=last_error))
        self._resume_members(failed)
        return failed

    # ---------- qB 待收尾标签镜像(P3 可选, 只写不读) ----------

    def _tag_name(self) -> str:
        """生效的待收尾标签名(空 = 配置关闭; 只读配置, 绝不读 qB 标签反推状态)"""
        conf = self._live_conf()
        if conf is None:
            return ""
        return str(getattr(conf, "pending_tag", "") or "").strip()

    def _tag_goal(self, job: RelocateJob) -> Optional[str]:
        """标签镜像目标: 待收尾窗口 = add, 终态 = remove(**仅曾 add 过**), 其余相位不动

        从未 armed 的 failed/cancelled job 账上 tag_on=False —— 不发 remove: 那既没清到
        东西, 又是一次多余 qB 写(轻则噪声, 重则打爆 qB 请求上限)。
        """
        if job.is_terminal:
            return "remove" if job.tag_on else None
        if job.phase in ru.PENDING_TAG_PHASES:
            return "add"
        return None

    def _sync_pending_tag(self, job: RelocateJob) -> None:
        """把单个 job 的标签镜像推到 qB(幂等; 失败降级只记日志/计数, 不影响迁移主流程)

        只在「目标态变化」时发请求(armed 一次 add, 终态对曾 add 的 job 一次 remove), 平时靠
        _reconcile_pending_tags 补写 —— 非终态的缺失在重启/断连恢复后自然补上; 终态摘除
        失败按账上 tag_on 退避重试(仅针对曾 add 的 job, 跨重启同样成立)。
        失败不记 applied, 按 _TAG_RETRY_SECONDS 退避重试; 标签被用户手动删掉时
        本函数不会重加(不读标签), WebUI/state 结论完全不受影响。
        """
        tag = self._tag_name()
        if not tag or self._dry_run():
            return
        want = self._tag_goal(job)
        if want is None or not job.hashes:
            return
        if self._tag_applied.get(job.job_id) == want:
            return
        now = self._clock.monotonic()  # 标签重试退避: 单调钟(D8; 宿主 RelocateModule 注入)
        if now < self._tag_next_try.get(job.job_id, 0.0):
            return
        api = getattr(self._ctx, "api", None)
        try:
            if want == "add":
                api.torrents_add_tags(tags=tag, torrent_hashes=list(job.hashes))
            else:
                api.torrents_remove_tags(tags=tag, torrent_hashes=list(job.hashes))
        except Exception as e:  # noqa: BLE001 - 镜像失败绝不改迁移相位/收尾判定
            self._tag_next_try[job.job_id] = now + _TAG_RETRY_SECONDS
            self._tag_failures += 1
            action = "加" if want == "add" else "摘"
            logger.warning(
                f"relocate | job {job.job_id}: {action}待收尾标签 {tag!r} 失败({e}) —— "
                f"仅镜像失败, 迁移状态与收尾判定不受影响(稍后重试)"
            )
            return
        self._tag_applied[job.job_id] = want
        self._tag_next_try.pop(job.job_id, None)
        self._note_tag_state(job, want == "add")

    def _note_tag_state(self, job: RelocateJob, added: bool) -> None:
        """把「标签已镜像到 qB」的事实落 state(曾 add 才 remove 的唯一依据; 不读 qB 标签)

        只改 tag_on 一位, 不重走 _set_job —— 后者会在同一 job 上再次触发镜像(递归),
        也会把相位推进的 updated_at 反复后移。落盘 + 换代快照, Web 侧 job 视图随之带上该位。
        """
        cur = self._jobs.get(job.job_id)
        if cur is None or cur.tag_on == added:
            return
        self._jobs[job.job_id] = replace(cur, tag_on=added)
        self._persist()
        self._publish_snapshot()

    def _reconcile_pending_tags(self) -> None:
        """每 tick 补写标签镜像: 非终态 job + 账上曾 add 的终态 job

        终态 job 会永久留在账上, 若全扫会批量发 remove —— 那是无意义写放大。故只扫两类:
        非终态 job; **tag_on=True**(确实加过、尚未摘成功)的终态 job —— 不补扫一次 qB
        抖动就会让标签永久残留。从未 add 的终态 job(tag_on=False)一律跳过: 它本来就没有
        标签可摘, 历史 job 也不会被写。摘除成功即把 tag_on 落成 False, 跨重启也不会再写。
        """
        if not self._tag_name() or self._dry_run():
            return
        for job in self._jobs.values():
            if job.is_terminal and not job.tag_on:
                continue
            self._sync_pending_tag(job)

    # ---------- 任务线: 每 tick 推进一步(P3 状态机) ----------

    def on_task_line(self, force: bool = False) -> None:
        """任务线 hook: 逐非终态 job 推进一步(单步零阻塞, 黄金法则 5 单一写线程)

        未启用时零动作(保守默认); 每步只做「一个可观测推进」(一次采样 / 一批链接 /
        一次 setLocation), 绝不在一个 tick 里跑完整个迁移 —— 大种子搬运要跨很多 tick,
        卡住主循环会让整库同步停滞。

        dry_run 时同样零动作: 相位机每一步都是真写(setLocation / 建删链接 / 拉 guardian /
        恢复运行态), 而 relocate_execute 那道闸只挡了「新建 job」这一条路 —— start() 从
        state 恢复的非终态 job 不经任何入口闸(崩溃/重启窗口即常态), 闸门必须落在这里,
        否则 --dry-run 启动会照着昨天的账真写。与 ops_mod.on_micro_line 同款。
        """
        conf = self._live_conf()
        if conf is None or not getattr(conf, "enabled", False):
            return
        if self._dry_run():
            logger.debug("relocate | dry-run: 相位机不推进(含 state 恢复的在途 job —— 不真写)")
            return
        if self._ctx is None or self._ctx.store is None:
            return
        for job in self.active_jobs():
            try:
                self._advance(job)
            except Exception as e:  # noqa: BLE001 - 单 job 异常不得拖垮任务线(其它 job 照常推进)
                logger.exception(f"relocate | job {job.job_id} 推进异常: {e}")
                self._fail(job, "internal_error", str(e))
        # qB 标签镜像补写(可选功能): 重启/断连期间错过 armed 的 job 在恢复后补上标签
        self._reconcile_pending_tags()

    def _advance(self, job: RelocateJob) -> None:
        """按相位分派一步(S4 相位模型: 前段 moving/watching/moved + 收尾窗 armed/rewritten)"""
        rt = self._rt.setdefault(job.job_id, {})
        phase = job.phase
        if phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING):
            self._step_move(job, rt)
        elif phase == ru.PHASE_MOVED:
            self._step_moved(job, rt)
        elif phase in ru.FINALIZE_WINDOW_PHASES:
            self._step_reconcile(job, rt)

    def _dry_run(self) -> bool:
        """干跑标志(start 期透传; 直接构造模块时取上下文的 dry_run, 缺省 False)"""
        if self._dry:
            return True
        return bool(getattr(self._ctx, "dry_run", False))

    def _live_conf(self) -> Optional[Any]:
        """预检面现取生效配置(ctx 单一真相; _conf 缓存只供 P3 相位机, 预检不消费旧值)"""
        if self._ctx is not None:
            return getattr(self._ctx.config, "relocate", None)
        return self._conf
