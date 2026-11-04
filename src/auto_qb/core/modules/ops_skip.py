"""ops 跳检叶: 相位机 / 同步与异步入口 / 微步线推进(自 ops_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 ops_mod.py 原文件逐字一致。
"""
import os
import time
from datetime import date
from typing import Optional

from ...infra import utils
from ...rules.base import ActionResult
from ...torrents import TorrentRecord
from .ops_common import (
    _SKIP_BACKOFF_MS,
    _SKIP_GONE_MSG,
    _SKIP_RESULT_KEEP,
    _SKIP_TERMINAL,
    SKIP_DRIVE_TIMEOUT,
    SKIP_PHASE_ADDING,
    SKIP_PHASE_APPEARED,
    SKIP_PHASE_DELETING,
    SKIP_PHASE_DONE,
    SKIP_PHASE_FAILED,
    SKIP_PHASE_FINISHING,
    SKIP_PHASE_GONE,
    SKIP_PHASE_PREPARING,
    SkipJob,
    logger,
)


class SkipMixin:
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
        now = self._clock.now()
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
        deadline = self._clock.now() + SKIP_DRIVE_TIMEOUT
        while not job.settled:
            self._skip_step(job)
            if job.settled:
                break
            now = self._clock.now()
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
        now = self._clock.now()
        due = sorted(
            (j for j in self._skip_jobs.values() if j.next_run <= now and not j.settled), key=lambda j: j.next_run
        )
        if not due:
            return 0
        deadline = self._clock.monotonic() + (budget_ms / 1000.0)
        stepped = 0
        for job in due:
            if stepped >= budget_calls or self._clock.monotonic() >= deadline:
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
        job.next_run = self._clock.now() + (_SKIP_BACKOFF_MS[job.attempts] / 1000.0)
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
        job.next_run = self._clock.now()

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
        job.next_run = self._clock.now()

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
            job.next_run = self._clock.now()
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
        job.next_run = self._clock.now()

    def _skip_step_appeared(self, job: SkipJob) -> None:
        try:
            appeared = bool(self._ctx.api.torrents_info(torrent_hashes=job.hash))
        except Exception as e:
            self._skip_retry(job, f"确认重加失败: {e}")
            return
        if appeared:
            job.phase = SKIP_PHASE_FINISHING
            job.attempts = 0
            job.next_run = self._clock.now()
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
