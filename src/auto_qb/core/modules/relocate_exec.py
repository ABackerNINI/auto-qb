"""relocate 执行叶: 相位推进、建链/穿透/收尾、对账、执行入口与撤销(自 relocate_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 relocate_mod.py 原文件逐字一致。
"""
import os
import time
from dataclasses import replace

from ...infra import alias_fs, file_access, relocate_journal, utils
from . import relocate_units as ru
from .relocate_probe import probe_fingerprint, run_probe
from .relocate_units import RelocateJob, evaluate_group
from .relocate_common import _LINK_CHUNK, _native, logger


class ExecMixin:
    # ---------- 搬: 轮询 / 停滞判据 / 长耗时转 watching ----------

    def _recover(self, job: RelocateJob, rt: dict, mover) -> None:
        """重启/重载后 MOVING job 的现场判据(每 job 只判一次, 判完交常规轮询)

        账先落 state、setLocation 后下发(§3.5.1), 两步之间崩溃 ⇒ 重启后 qB 从未收到搬迁:
        dst 恒空且 qB 不在 moving —— 这与「下发了但没动静」在 qB 侧**不可分辨**, 只有账上
        move_issued 这一位能分开两者。判据走 ru.recover_exec_phase(qB 现场三分流):

        - qB 仍在搬 ⇒ 继续轮询(不重发 setLocation, 会排队/覆盖);
        - 数据已到 dst ⇒ 补做 moved 之后的步骤(不再从头等一轮停滞);
        - 都没发生 ⇒ 未下发过就补发一次(此刻 qB 不在 moving, 无排队/覆盖风险); 已下发过
          则只留一行日志并把停滞起点交常规判据 —— 快照滞后会让「刚下发还没动」看起来
          和真停滞一样, 立刻判失败会误杀正常迁移(保守默认: 宁可等, 不可错杀)。
        """
        rt.pop("recover", None)
        moving = "moving" in str(getattr(mover, "state", "") or "").lower()
        at_dst = self._norm(getattr(mover, "save_path", "") or "") == self._norm(job.dst)
        verdict = ru.recover_exec_phase(moving, at_dst, self._dst_size(job) > 0)
        if verdict == ru.RECOVER_STALLED and not job.move_issued:
            rt["issue"] = True
            logger.warning(
                f"relocate | job {job.job_id}: 恢复发现搬迁指令未发出(落账与下发之间中断), 补发 "
                f"setLocation 一次(mover {job.mover[:8]} -> {job.dst})"
            )
            return
        if verdict == ru.RECOVER_POLL:
            logger.info(f"relocate | job {job.job_id}: 恢复: qB 仍在搬, 继续轮询(不重发 setLocation)")
            return
        if verdict == ru.RECOVER_RESUME:
            logger.info(f"relocate | job {job.job_id}: 恢复: 数据已到 dst, 补做 moved 之后的步骤")
            rt["stage"] = "verify"
            self._set_job(replace(job, phase=ru.PHASE_MOVED))
            return
        logger.info(f"relocate | job {job.job_id}: 恢复: 未见搬迁现场(qB 不在 moving 且 dst 无数据), "
                    f"交停滞判据(不重发不下判失败)")

    def _step_move(self, job: RelocateJob, rt: dict) -> None:
        store = self._ctx.store
        mover = store.by_hash.get(job.mover)
        if mover is None:
            self._fail(job, "torrent_gone", "搬迁中种子已不存在")
            return
        if rt.get("recover"):
            self._recover(job, rt, mover)  # 一个 tick 只做「定夺现场」这一件事
            return
        if rt.get("issue", True):
            # 等自有暂停的快照回流(own_write_pending 语义): 未回流前不下发, 免得与暂停排队冲突
            pending = getattr(store, "own_write_pending", None)
            if pending is not None and pending(job.mover):
                return
            try:
                self._ctx.api.torrents_set_location(torrent_hashes=[job.mover], location=job.dst)
            except Exception as e:  # noqa: BLE001 - qB 拒绝: 落 failed, 不自动搬回
                self._fail(job, "move_rejected", f"setLocation 被拒: {e}")
                return
            rt["issue"] = False
            rt["started"] = time.monotonic()
            rt["sample_ts"] = 0.0
            rt["last_size"] = -1
            rt["stall_since"] = 0.0
            self._mark_issued(job)  # 补发路径同样要落账, 否则下次重启还会当成崩溃窗口
            logger.info(f"relocate | job {job.job_id}: 已下发 qB 搬迁(mover {job.mover[:8]} -> {job.dst})")
            return

        now = time.monotonic()
        moving = "moving" in str(getattr(mover, "state", "") or "").lower()
        interval = 5.0 if job.phase == ru.PHASE_MOVING else 30.0
        if now - float(rt.get("sample_ts") or 0.0) >= interval:
            size = self._dst_size(job)
            grew = size > int(rt.get("last_size", -1))
            rt["sample_ts"] = now
            rt["last_size"] = size
            if moving or grew:
                rt["stall_since"] = 0.0
            elif not rt.get("stall_since"):
                rt["stall_since"] = now

        conf = self._live_conf()
        verdict = ru.stall_verdict(
            sample_grew=False,
            qb_moving=moving,
            elapsed=now - float(rt.get("started") or now),
            warn_after=float(getattr(conf, "move_warn_after", 0) or 0),
            stall_timeout=float(getattr(conf, "move_stall_timeout", 0) or 0),
            stalled_for=(now - float(rt.get("stall_since") or 0.0)) if rt.get("stall_since") else 0.0,
        )
        if verdict == ru.STALL_FAILED:
            self._fail(job, "move_stalled", "搬迁停滞(dst 不再增长且 qB 已不在 moving)")
            return
        if verdict == ru.STALL_WARN and job.phase == ru.PHASE_MOVING:
            logger.info(
                f"relocate | job {job.job_id}: 搬运已超预期时间({getattr(conf,'move_warn_after',0)}s), 转 watching(不判失败)"
            )
            rt["stall_since"] = 0.0
            self._set_job(replace(job, phase=ru.PHASE_WATCHING))
            return
        # 完成判据: qB 已不在 moving 且目标侧数据齐全
        if not moving and self._dst_ready(job):
            self._set_job(replace(job, phase=ru.PHASE_MOVED))
            rt["stage"] = "verify"

    @staticmethod
    def _native(path: str, rel: str) -> str:
        """save_path + qB 相对路径 -> 本机路径(委托模块级单点, 见文件头 _native)"""
        return _native(path, rel)

    def _dst_size(self, job: RelocateJob) -> int:
        """目标侧已落数据的体积采样(体积只增不减; 缺失文件计 0)"""
        fa = file_access.get_file_access()
        total = 0
        for rel, _size in self._plan_files(job):
            try:
                if fa.exists(self._native(job.dst, rel)) is True:
                    total += int(fa.getsize(self._native(job.dst, rel)))
            except Exception:  # noqa: BLE001 - 采样失败静默(每 5s 一次, 不刷屏)
                continue
        return total

    def _dst_ready(self, job: RelocateJob) -> bool:
        """目标侧文件数与总大小对齐(verify=size 口径; §3.5.1)"""
        files = self._plan_files(job)
        if not files:
            return False
        fa = file_access.get_file_access()
        for rel, size in files:
            p = self._native(job.dst, rel)
            try:
                if fa.exists(p) is not True or int(fa.getsize(p)) != int(size):
                    return False
            except Exception:  # noqa: BLE001
                return False
        return True

    def _plan_files(self, job: RelocateJob) -> tuple:
        """job 计划里的文件表 [(相对路径, 大小)](重启恢复的来源)"""
        plan = job.plan or {}
        raw = plan.get("files") or []
        return tuple((str(a), int(b)) for a, b in raw)

    # ---------- moved: 校验 -> 建链接 -> 穿透校验 -> 重归组 -> 武装 ----------

    def _step_moved(self, job: RelocateJob, rt: dict) -> None:
        stage = rt.get("stage") or "verify"
        conf = self._live_conf()
        if stage == "verify":
            if not self._dst_ready(job):
                self._fail(job, "verify_mismatch", "目标侧文件数/大小不符")
                return
            rt["stage"] = "link"
            # 已建链接不重建(崩溃恢复: 重启后 alias_paths 非空, 从断点续建)
            rt["link_pos"] = len(job.alias_paths)
            rt["links"] = list(job.alias_paths)
            return
        if stage == "link":
            if job.plan and job.plan.get("form") == ru.FORM_DIRECT:
                self._finish_direct(job)  # 单成员组: qB 自搬, 无别名无收尾
                return
            done = self._build_links(job, rt)
            if not done:
                return
            rt["stage"] = "penetrate"
            return
        if stage == "penetrate":
            if job.alias_paths and not self._penetration_ok(job):
                # 穿透失败: 保留链接现场(便于排查), 不删链接不搬回
                self._fail(job, "alias_unreadable", "经原路径读不到已迁数据")
                return
            rt["stage"] = "arm"
            return
        if stage == "arm":
            self._arm(job, rt)
            return
        logger.debug(f"relocate | job {job.job_id}: 未知 stage {stage}(按 arm 收口)")
        self._arm(job, rt)

    def _build_links(self, job: RelocateJob, rt: dict) -> bool:
        """按形态建一批链接(每 tick 一批, 单步有界); 中途失败 ⇒ 删已建链接转收尾路径

        返回 True = 本形态链接已建完。失败时不做任何数据搬迁(§3.5.1: 链接失败通常是权限
        问题, 修好重试是零数据移动的; 搬回则要再复制一遍全部数据)。
        """
        plan = job.plan or {}
        form = plan.get("form")
        kind = plan.get("link_kind")
        links = rt.setdefault("links", list(job.alias_paths))
        try:
            if form == ru.FORM_DIR_ALIAS:
                rel = self._scope_rel(job)
                link = self._native(job.src, rel)
                target = self._native(job.dst, rel)
                if os.path.isdir(link) and not os.path.islink(link):
                    if os.listdir(link):
                        raise RuntimeError(f"内容根目录非空({link}), 目录别名建不出来")
                    os.rmdir(link)  # qB 搬走文件后留下的空目录
                alias_fs.create_dir_alias(link, target, kind)
                links.append(link)
            else:
                files = self._plan_files(job)
                pos = int(rt.get("link_pos") or 0)
                chunk = files[pos:pos + _LINK_CHUNK]
                for rel, _size in chunk:
                    link = self._native(job.src, rel)
                    target = self._native(job.dst, rel)
                    os.makedirs(os.path.dirname(link), exist_ok=True)
                    alias_fs.create_file_alias(link, target, kind)
                    links.append(link)
                rt["link_pos"] = pos + len(chunk)
                if rt["link_pos"] < len(files):
                    self._set_job(replace(job, alias_paths=tuple(links)))  # 逐条落账(崩溃可回滚)
                    return False
        except Exception as e:  # noqa: BLE001 - 链接失败: 零成本回滚 + 转收尾路径
            logger.warning(f"relocate | job {job.job_id}: 建链接失败({e}) —— 删已建 {len(links)} 条链接, 转收尾路径(不搬回)")
            self._remove_links(links)
            self._set_job(
                replace(
                    job,
                    alias_paths=(),
                    phase=ru.PHASE_REMOVED,
                    reason="alias_partial",
                    last_error=str(e),
                    # 记账: 重建配额由对账侧消费(建链必失败的环境不能无限重建, 见 REBUILD_MAX_ATTEMPTS)
                    attempts=int(job.attempts or 0) + 1,
                )
            )
            return False
        self._set_job(replace(job, alias_paths=tuple(links)))
        return True

    def _penetration_ok(self, job: RelocateJob) -> bool:
        """穿透校验: 经**原路径**逐文件 stat, 大小一致(§4.1)"""
        fa = file_access.get_file_access()
        for rel, size in self._plan_files(job):
            try:
                p = self._native(job.src, rel)
                if fa.exists(p) is not True or int(fa.getsize(p)) != int(size):
                    return False
            except Exception:  # noqa: BLE001
                return False
        return True

    def _arm(self, job: RelocateJob, rt: dict) -> None:
        """重归组 + 落账(armed) + 拉起 guardian + 恢复运行态"""
        grouping = getattr(self._ctx, "grouping", None)
        if grouping is not None:
            try:
                grouping.regroup_scope(job.scope, job.src, job.hashes)
            except Exception as e:  # noqa: BLE001 - 重归组失败不影响落账(下轮 save_path 变化还会再归)
                logger.warning(f"relocate | job {job.job_id}: 重归组失败({e})")
        # attempts 归零: 重建链接成功即本轮重试周期结束, 上次的历史失败不该占着下次的配额
        armed = replace(job, phase=ru.PHASE_ARMED, armed_at=time.time(), reason="", attempts=0)
        self._set_job(armed)
        self._spawn_guardian(armed)
        self._resume_members(armed)
        logger.info(
            f"relocate | job {armed.job_id}: 已武装收尾(别名 {len(armed.alias_paths)} 条, "
            f"形态 {armed.alias_kind or 'direct'}) —— 下次 qB 退出时自动收尾"
        )

    def _finish_direct(self, job: RelocateJob) -> None:
        """单成员组收口: 重归组 + 恢复运行态 + done(无别名 ⇒ 无 guardian、无收尾窗口)"""
        grouping = getattr(self._ctx, "grouping", None)
        if grouping is not None:
            try:
                grouping.regroup_scope(job.scope, job.src, job.hashes)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"relocate | job {job.job_id}: 重归组失败({e})")
        self._resume_members(job)
        self._set_job(replace(job, phase=ru.PHASE_DONE, reason="direct"))
        logger.info(f"relocate | job {job.job_id}: 单成员组迁移完成(qB 自搬, 无需别名)")

    def _scope_rel(self, job: RelocateJob) -> str:
        """内容根相对 src 的段(目录别名的链接位置; 平铺 = "")"""
        sp = job.src.replace("\\", "/").rstrip("/")
        scope = job.scope.replace("\\", "/").rstrip("/")
        return scope[len(sp):].lstrip("/") if scope.startswith(sp + "/") else ""

    # ---------- P6 对账: journal 合并 + 对账表处置 ----------

    def _qb_up(self) -> bool:
        """「qB 在?」= 连得上(三证之一); 结果缓存 10s, 免得每 tick 一次请求"""
        now = time.monotonic()
        cached = self._qb_up_cache
        if cached is not None and now - cached[0] < 10.0:
            return cached[1]
        up = False
        try:
            client = self._ctx.api.client if self._ctx.api is not None else None
            if client is not None:
                client.app_preferences()
                up = True
        except Exception:  # noqa: BLE001 - 连不上即判「qB 不在」(这是收尾窗口的判据, 不是故障)
            up = False
        self._qb_up_cache = (now, up)
        return up

    def _seed_state(self, job: RelocateJob) -> str:
        """种子态三值: gone(全部不在) / missingFiles(任一成员缺文件) / normal"""
        store = self._ctx.store
        recs = [store.by_hash.get(h) for h in job.hashes]
        live = [r for r in recs if r is not None]
        if not live:
            return "gone"
        for r in live:
            if "missingfiles" in str(getattr(r, "state", "") or "").lower():
                return "missingFiles"
        return "normal"

    def _all_at_dst(self, job: RelocateJob) -> bool:
        """全组成员是否都已在目标位置(外部完成判据)"""
        for h in job.hashes:
            rec = self._ctx.store.by_hash.get(h)
            if rec is None or utils.path_normalize(rec.save_path) != utils.path_normalize(job.dst):
                return False
        return True

    def _step_reconcile(self, job: RelocateJob, rt: dict) -> None:
        """对账一步: 读 journal -> 查链接/qB/种子现场 -> 按 §3.5 对账表处置"""
        journal = relocate_journal.read_journal(self._data_dir(), job.job_id) or {}
        j_phase = str(journal.get("phase") or "")
        # journal 只能**向前**合并: removing/removed 是收尾意图, 只覆盖 armed/removing ——
        # 不覆盖 moved(那是「重建链接」把我们拉回执行期), 否则重建好的 job 会被旧 journal 再降级
        if j_phase in (ru.PHASE_REMOVING,
                       ru.PHASE_REMOVED) and job.phase in (ru.PHASE_ARMED, ru.PHASE_REMOVING, ru.PHASE_REMOVED):
            if j_phase != job.phase:
                job = self._set_job(replace(job, phase=j_phase))
        link_present = bool(job.alias_paths) and any(alias_fs.alias_kind_of(p) for p in job.alias_paths)
        qb_up = self._qb_up()
        seed_state = self._seed_state(job)
        # 「已被外部完成」判据 = **全组成员**都已到目标位置(不是只看 mover: mover 本就是本 job
        # 搬过去的, 用它会把自己刚武装的 job 立刻判成 done)
        at_dst = self._all_at_dst(job)
        hb = journal.get("ts")
        heartbeat_age = max(0.0, time.time() - float(hb)) if hb else float("inf")
        elapsed = time.time() - float(job.armed_at or job.updated_at or time.time())
        conf = self._live_conf()
        action = ru.reconcile(
            job,
            journal_phase=j_phase,
            link_present=link_present,
            qb_up=qb_up,
            seed_state=seed_state,
            save_path_at_dst=at_dst,
            heartbeat_age=heartbeat_age,
            elapsed=elapsed,
            finalize_timeout=float(getattr(conf, "finalize_timeout", 0) or 0),
        )
        self._apply_reconcile(job, rt, action)

    def _apply_reconcile(self, job: RelocateJob, rt: dict, action: str) -> None:
        if action == ru.ACT_WAIT:
            return
        if action == ru.ACT_RESPAWN or action == ru.ACT_REDELETE:
            logger.info(f"relocate | job {job.job_id}: guardian 心跳过期/未在工作, 重拉({action})")
            self._respawn_guardian(job, rt)
            return
        if action == ru.ACT_REVERT_INTENT:
            logger.info(f"relocate | job {job.job_id}: 删别名期间 qB 回来了 —— 撤销删除意图, 回 armed")
            relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_ARMED, "ts": time.time()})
            self._set_job(replace(job, phase=ru.PHASE_ARMED))
            self._respawn_guardian(job, rt)
            return
        if action == ru.ACT_REBUILD:
            if int(job.attempts or 0) >= ru.REBUILD_MAX_ATTEMPTS:
                self._fail(
                    job,
                    "rebuild_exhausted",
                    f"重建链接已失败 {int(job.attempts or 0)} 次(上限 {ru.REBUILD_MAX_ATTEMPTS}) —— "
                    f"保留现场交人处理: 通常是权限不足, 修好后重新发起即可",
                )
                return
            # None = 从未重建过, 不吃退避; 旧写法 or 0.0 会把开机后前 REBUILD_BACKOFF 秒全算成退避窗口
            # (monotonic 0 点是开机时刻, 见 pitfalls/testing/monotonic-warn-sentinel.md, issue 26-10-31-0932)
            rebuild_ts = rt.get("rebuild_ts")
            if rebuild_ts is not None and time.monotonic() - float(rebuild_ts) < ru.REBUILD_BACKOFF:
                logger.debug(f"relocate | job {job.job_id}: 重建链接退避中(距上次 < {ru.REBUILD_BACKOFF}s), 本轮跳过")
                return
            rt["rebuild_ts"] = time.monotonic()
            logger.warning(f"relocate | job {job.job_id}: 链接不在而 qB 在线(删的时候 qB 其实在跑) —— 重建链接")
            rt["stage"] = "link"
            rt["link_pos"] = 0
            rt["links"] = []
            job = replace(job, phase=ru.PHASE_MOVED, alias_paths=(), reason="")
            self._set_job(job)
            # 意图回滚: journal 也退回 armed —— 否则旧「removed」会反复把 job 拉回收尾判定
            relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_ARMED, "ts": time.time()})
            if self._build_links(job, rt):
                rt["stage"] = "penetrate"
            return
        if action == ru.ACT_FINALIZE:
            members = self._finalize_members(job)
            if not members:
                self._set_job(replace(job, phase=ru.PHASE_DONE, reason="finalized"))
                return
            try:
                self._ctx.api.torrents_set_location(torrent_hashes=list(members), location=job.dst)
            except Exception as e:  # noqa: BLE001
                self._fail(job, "finalize_rejected", str(e))
                return
            rt["finalize"] = list(members)
            rt["finalize_ts"] = time.time()
            self._set_job(replace(job, phase=ru.PHASE_FINALIZING))
            return
        if action == ru.ACT_FAILED_GONE:
            self._fail(job, "torrent_gone", "收尾前种子已被删除")
            return
        if action == ru.ACT_FAILED_TIMEOUT:
            self._fail(
                job,
                "finalize_timeout",
                "数据已在目标位置, qB 仍指向原路径 —— 已超收尾等待上限, 请手动 setLocation",
            )
            return
        if action == ru.ACT_DONE_EXTERNAL:
            self._set_job(replace(job, phase=ru.PHASE_DONE, reason="external"))
            # 通知 guardian 退休: 否则已终结 job 的守护进程会永远每 10s 写心跳
            relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_DONE, "ts": time.time()})
            return
        logger.debug(f"relocate | job {job.job_id}: 对账动作 {action} 无处置")

    def _finalize_members(self, job: RelocateJob) -> tuple:
        """动态收尾集合(§3.5 / D7): 创建时成员 ∪ 当前落在该作用域的成员, mover 跳过

        取数顺序(26-10-30-0616): 先零成本过滤再取文件表 —— 创建时成员与 mover 的
        判定不看内容根, 新增候选先按 save_path==src 筛(单点 ru.finalize_scope_candidate),
        只对筛剩者发 files API 算内容根; 全库逐条先取文件表会让大库主循环单 tick
        串行 N 次 HTTP 停摆分钟级。判定单点仍在 ru.finalize_members(这里只是预筛)。
        """
        store = self._ctx.store
        api = self._ctx.api
        members = []
        for h, rec in store.by_hash.items():
            if h == job.mover or h in job.hashes:
                # 判定对这两类短路不看内容根 —— root 以 save_path 占位, 免文件表
                members.append((h, rec.save_path, rec.save_path))
                continue
            if not ru.finalize_scope_candidate(job, rec.save_path):
                continue
            fmap = self._file_map(rec, api.client) if api is not None else {}
            root = ru.content_root_of(rec.save_path, list(fmap.keys()))
            members.append((h, rec.save_path, root))
        return ru.finalize_members(job, members)

    def _step_finalize(self, job: RelocateJob, rt: dict) -> None:
        """收尾轮询: 成员 save_path 到 dst 且 progress 回 1 ⇒ done(零校验)"""
        targets = rt.get("finalize") or list(job.hashes)
        store = self._ctx.store
        ok = True
        for h in targets:
            rec = store.by_hash.get(h)
            if rec is None:
                continue
            if utils.path_normalize(rec.save_path) != utils.path_normalize(job.dst):
                ok = False
            elif float(getattr(rec, "progress", 0.0) or 0.0
                      ) < 1.0 and "checking" not in str(getattr(rec, "state", "") or "").lower():
                ok = False
        if not ok:
            conf = self._live_conf()
            if time.time() - float(rt.get("finalize_ts") or time.time()) > float(
                getattr(conf, "finalize_timeout", 0) or 0
            ):
                self._fail(job, "finalize_timeout")
            return
        self._set_job(replace(job, phase=ru.PHASE_DONE, reason="finalized"))
        relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_DONE, "ts": time.time()})
        logger.info(f"relocate | job {job.job_id}: 收尾完成({len(targets)} 个成员已到目标位置)")

    # ---------- P3 执行入口(三入口共用) ----------

    def relocate_execute(self, hashes, location: str = "", confirm: bool = False) -> list:
        """整组迁移执行入口(三入口共用): 预检 -> 暂停 -> qB 搬 -> (后续相位由任务线推进)

        **只做零成本的前置动作**: 闸门不过 ⇒ 一条 blocked 回执, 零副作用; 通过 ⇒
        暂停运行中的成员 + 下发 setLocation(mover) 并落 job 账(phase=moving)。
        搬字节一律由 qB 完成(D2), 本方法绝不复制/移动任何数据文件。
        """
        req = [str(h) for h in (hashes or []) if h]
        target = str(location or "").strip()
        conf = self._live_conf()
        items: list = []
        if conf is None or not getattr(conf, "enabled", False):
            return [self._receipt(req, target, "blocked", "disabled", "整组迁移未启用(配置键 relocate.enabled)")]
        if not req:
            return [self._receipt(req, target, "blocked", "param", "未提供任何 hash")]
        if not target:
            return [self._receipt(req, target, "blocked", "param", "未提供目标位置(location 不能为空)")]
        ctx = self._ctx
        if ctx is None or ctx.store is None or ctx.api is None or ctx.api.client is None:
            return [self._receipt(req, target, "blocked", "unavailable", "模块上下文或 qB 客户端不可用")]

        client = ctx.api.client
        gone, groups = self._buckets(req)
        items.extend(gone)
        for records in groups:
            # 幂等(T3)先于一切闸门: 同一组同一目标的 job 已在途 ⇒ skip —— 规则 move_to 每轮都会
            # 命中同一目标, 若落到「未收尾拦截」会天天报失败, 那是把幂等写成故障
            hashes = [r.hash for r in records]
            same = next(
                (j for j in self.active_jobs() if j.touches(hashes) and self._norm(j.dst) == self._norm(target)),
                None,
            )
            if same is not None:
                items.append(
                    {
                        "hashes": hashes,
                        "mover": same.mover,
                        "name": records[0].name,
                        "save_path": records[0].save_path,
                        "target": target,
                        "cls": "skip",
                        "job_id": same.job_id,
                        "phase": same.phase,
                        "reasons": [],
                        "notes": [f"同一组同一目标的迁移已在途(job {same.job_id}, 相位 {same.phase}): 未重复发起"],
                    }
                )
                continue
            if all(self._norm(r.save_path) == self._norm(target) for r in records):
                items.append(
                    {
                        "hashes": hashes,
                        "mover": records[0].hash,
                        "name": records[0].name,
                        "save_path": records[0].save_path,
                        "target": target,
                        "cls": "skip",
                        "reasons": [],
                        "notes": ["全组已在目标位置(幂等): 未发起迁移"],
                    }
                )
                continue
            facts = self._group_facts(records, target, client)
            verdict = evaluate_group(facts)
            if verdict["cls"] == ru.CLS_BLOCKED:
                items.append({**verdict, "cls": "blocked"})
                continue
            if verdict["cls"] == ru.CLS_CONFIRM and not confirm:
                items.append({**verdict, "cls": "confirm"})
                continue
            if self._norm(target) == self._norm(records[0].save_path):
                items.append({**verdict, "cls": "skip", "notes": list(verdict["notes"]) + ["已在目标位置(幂等): 未发起迁移"]})
                continue
            gate = self._ensure_probe(records, facts, verdict)
            if gate is not None:
                items.append(gate)
                continue
            items.append(self._start_job(records, target, facts, verdict, client))
        logger.info(f"relocate | 迁移执行({len(req)} 个 hash -> {len(items)} 项): {self._summ(items)}")
        return items

    def _ensure_probe(self, records, facts, verdict: dict):
        """执行链一次性同机强探测闸(计划 26-11-04-0055 §04 P3 行后半 + §06 D1-D7)

        位置契约(D5): 必须在建账(_start_job)与任何 torrents_set_location 之前调用 ——
        探测失败 => 零建账、零 setLocation; 规则引擎自动迁移共用本入口, 无旁路(D6)。

        决策表(按序短路, 返回 None = 放行, verdict 的 notes 可能被追加; 返回 dict =
        blocked 回执, 与 evaluate_group 现行 blocked item 同形: reasons 元素 gate/cls/text):
        - 单成员组(D2): 完全跳过, 零动作零 note —— 独占内容由 qB 自搬, 免同机证明;
        - dry-run: 零副作用承诺(不落探针文件、不动 qB), note「dry-run: 跳过强探测」;
        - assume_shared=true(D7): 用户显式越权, 跳过探测, note 注明「未经 auto-qb 验证」;
        - 路径级已证明(facts.same_fs_proved, D4 组合口径的 D 复查面): E1 无增量, 放行;
        - 指纹缓存(D3: host+port+username+secret)命中 passed => 放行;
          命中 failed => blocked(D7① 同指纹不重试);
        - 未命中 => run_probe 同步执行(常态 ~1.3s): passed => probe_put(passed) 放行;
          failed env=False(FS 不可达) => probe_put(failed) + blocked(D7①);
          failed env=True(环境性) => 不写缓存 + blocked(下次迁移重试, D7②)。
        """
        if len(records) <= 1:
            return None
        if self._dry_run():
            verdict["notes"] = list(verdict.get("notes") or []) + ["dry-run: 跳过强探测"]
            return None
        conf = self._live_conf()
        if bool(getattr(conf, "assume_shared", False)):
            verdict["notes"] = list(verdict.get("notes") or []) + \
                ["assume_shared: 未经 auto-qb 验证(用户显式越权), 跳过同机强探测"]
            return None
        if facts.same_fs_proved:
            return None
        qb_conf = getattr(getattr(self._ctx, "config", None), "qbittorrent", None)
        fp = probe_fingerprint(qb_conf)
        hit = self.probe_get(fp)
        if hit is not None:
            if hit["status"] == "passed":
                # 缓存放行的组合口径(拍板 D4): E1 机器级强证明是「一次性」的 —— 同连接身份
                # 缓存(D3), 之后每次多成员迁移仍由预检 D 级路径证据复查(降级链 D->B'),
                # 运行时 F 兜底不变; 见 memory-bank/plans/26-11-04-0055-plan-relocate-same-fs-proof.html §06 D4。
                return None
            reason = str((hit.get("evidence") or {}).get("reason") or "fs_unreachable")
            return {
                **verdict,
                "cls":
                    "blocked",
                "reasons":
                    list(verdict.get("reasons") or []) + [
                        {
                            "gate": ru.GATE_SAME_FS,
                            "cls": ru.CLS_BLOCKED,
                            "text": f"上次同机探测失败({reason}): 已缓存, 更改 qB 连接配置或清除 state.relocate.probes 后重试",
                        }
                    ],
            }
        probe = run_probe(self._ctx, facts.save_path, facts.target)
        if probe.status == "passed":
            self.probe_put(fp, probe.status, probe.evidence)
            return None
        if probe.env:
            # 环境性失败(网络/凭据/连接中断/本机写探针失败): 与 FS 可达性无关, 不缓存(D7②)
            text = f"探测环境性失败: {probe.reason}(未缓存, 下次迁移将重试)"
        else:
            # FS 不可达(证读/证写超时): 硬拦 + 缓存失败(D7① 同指纹不重试 —— 探测要真写一次
            # 目标盘, 缓存免得每次迁移都白搬一遍探针); 坏缓存可经 probe_put 覆盖写修复
            self.probe_put(fp, probe.status, {**probe.evidence, "reason": probe.reason})
            text = (
                "qB 读不到本机 src 或写不进 dst: " + probe.reason + " —— 出路: 检查 fs.path_map 映射是否覆盖源/目标路径, "
                "或确认 qB 与 auto-qb 确实共享文件系统后配置 relocate.assume_shared"
            )
        return {
            **verdict,
            "cls":
                "blocked",
            "reasons":
                list(verdict.get("reasons") or []) + [{
                    "gate": ru.GATE_SAME_FS,
                    "cls": ru.CLS_BLOCKED,
                    "text": text,
                }],
        }

    def _start_job(self, records, target: str, facts, verdict: dict, client) -> dict:
        """建账 + 暂停 + 下发搬迁(一步到位, 后续相位交任务线)"""
        mover = records[0]
        src = mover.save_path
        job_id = ru.job_id_for(mover.hash, target, src)
        existing = self._jobs.get(job_id)
        if existing is not None and not existing.is_terminal:
            return {
                **verdict,
                "cls":
                    "blocked",
                "job_id":
                    job_id,
                "reasons":
                    [{
                        "gate": ru.GATE_UNFINISHED,
                        "text": f"该组已有在途迁移(job {job_id}, 相位 {existing.phase}): 先收尾或先撤销"
                    }],
            }
        unit = ru.plan(
            src,
            [n for n, _s in facts.files],
            facts.threshold,
            facts.hard_max,
            multi_member=len(records) > 1,
            content_root_exclusive=facts.content_root_exclusive,
            file_link_kind=facts.file_link_kind,
            file_link_error=facts.file_link_error,
            dir_link_kind=facts.dir_link_kind,
            dir_link_error=facts.dir_link_error,
            link_path_limit=facts.link_path_limit,
        )
        if unit.form == ru.FORM_REJECT:
            return {**verdict, "cls": "blocked", "reasons": [{"gate": ru.GATE_FORM, "text": unit.reason}]}
        scope = ru.content_root_of(src, [n for n, _s in facts.files])
        running = [r.hash for r in records if not getattr(r.state_enum, "is_stopped", True)]
        if running and not self._dry_run():
            try:
                self._ctx.api.torrents_pause(torrent_hashes=running)
            except Exception as e:  # noqa: BLE001 - 暂停失败不继续: 搬迁窗口必须先把组按住
                return {**verdict, "cls": "blocked", "reasons": [{"gate": "pause_failed", "text": f"暂停成员失败: {e}"}]}
        job = RelocateJob(
            job_id=job_id,
            hashes=tuple(r.hash for r in records),
            mover=mover.hash,
            src=src,
            dst=target,
            scope=scope,
            alias_kind=self._alias_kind_of_form(unit.form),
            phase=ru.PHASE_MOVING,
            resume_hashes=tuple(running),
            updated_at=time.time(),
            plan={
                "form": unit.form,
                "link_kind": unit.link_kind,
                "scope": scope,
                "files": [[n, s] for n, s in facts.files],
            },
        )
        self._jobs[job_id] = job
        self._rt[job_id] = {
            "issue": True,
            "started": time.monotonic(),
            "sample_ts": 0.0,
            "last_size": -1,
            "stall_since": 0.0
        }
        self._sync_relocating()
        self._persist()
        if self._dry_run():
            return {
                **verdict, "cls": "ok",
                "job_id": job_id,
                "phase": job.phase,
                "notes": list(verdict["notes"]) + ["dry-run: 未下发搬迁"]
            }
        self._ctx.api.torrents_set_location(torrent_hashes=[job.mover], location=job.dst)
        self._rt[job_id]["issue"] = False
        self._mark_issued(job)  # 重启恢复靠这一位区分崩溃窗口(未下发)与真停滞(见 _recover)
        logger.info(f"relocate | job {job_id}: 迁移发起({len(records)} 成员, 形态 {unit.form}, mover {job.mover[:8]})")
        return {
            **verdict,
            "cls": "started",
            "job_id": job_id,
            "phase": job.phase,
            "alias_kind": job.alias_kind,
            "link_count": unit.link_count,
            "notes": list(verdict["notes"]) + ["qB 正在搬迁, 完成后自动建别名并武装收尾"],
        }

    @staticmethod
    def _alias_kind_of_form(form: str) -> str:
        return {"file_links": "file", "dir_alias": "dir"}.get(form, "")

    # ---------- 撤销(唯一会移动数据的旁支: 先算成本, 需显式确认) ----------

    def relocate_cancel(self, job_id: str, cost_confirmed: bool = False) -> dict:
        """撤销迁移: 删链接 + qB 搬回(目标为空 ⇒ 零校验) —— 必须先给用户看成本

        未确认成本时只回「将把 X 从 T 搬回 S(预计)」, 不动任何东西(§3.5.1)。

        dry_run 时不执行(删链接 + qB 搬回都是真写, 且搬回要再复制一遍全量数据)。
        """
        job = self._jobs.get(job_id)
        if job is None:
            return {"cls": "blocked", "reasons": [{"gate": "gone", "text": f"未找到迁移任务 {job_id}"}]}
        if self._dry_run():
            return {
                "cls": "blocked",
                "job_id": job_id,
                "reasons": [{
                    "gate": "dry_run",
                    "text": "dry-run: 撤销不执行(不删链接、不搬回)"
                }],
            }
        total = sum(int(s) for _r, s in self._plan_files(job))
        cost = {
            "job_id": job_id,
            "bytes": total,
            "from": job.dst,
            "to": job.src,
            "note": f"将把 {total} 字节从 {job.dst} 搬回 {job.src}(qB 执行), 期间该组不可用",
        }
        if not cost_confirmed:
            return {"cls": "confirm", "cost": cost, "reasons": [{"gate": "cost", "text": cost["note"]}]}
        self._remove_links(list(job.alias_paths))
        try:
            self._ctx.api.torrents_set_location(torrent_hashes=[job.mover], location=job.src)
        except Exception as e:  # noqa: BLE001
            self._fail(job, "cancel_failed", str(e))
            return {"cls": "blocked", "cost": cost, "reasons": [{"gate": "cancel_failed", "text": f"搬回被拒: {e}"}]}
        cancelled = self._set_job(replace(job, phase=ru.PHASE_CANCELLED, alias_paths=(), reason="cancelled"))
        # 通知 guardian 退休(它可能在等 qB 退出; 撤销后没有它要干的活了)
        relocate_journal.write_journal(self._data_dir(), job_id, {"phase": ru.PHASE_CANCELLED, "ts": time.time()})
        self._resume_members(cancelled)
        return {"cls": "ok", "cost": cost, "job_id": job_id, "phase": ru.PHASE_CANCELLED}

    # ---------- 链接删除与 guardian 拉起 ----------

    def _remove_links(self, paths) -> int:
        """逐条删链接(非递归, 幂等); 返回实际删除条数"""
        n = 0
        for p in list(paths or ()):
            if not p:
                continue
            try:
                if alias_fs.alias_kind_of(p) is not None:
                    alias_fs.remove_alias(p)
                    n += 1
            except Exception as e:  # noqa: BLE001 - 单条失败继续(幂等重删靠下一次对账)
                logger.warning(f"relocate | 删链接失败({p}): {e}")
        return n

    def _data_dir(self) -> str:
        cfg = getattr(self._ctx, "config", None) if self._ctx is not None else None
        return str(getattr(cfg, "data_dir", "") or "auto-qb-data")

    def _respawn_guardian(self, job: RelocateJob, rt: dict) -> None:
        """对账驱动的重拉(带退避): 心跳一过期就每 tick 拉一次进程是纯浪费

        退避窗口内跳过 —— 判断依据(心跳/链接/qB)没变, 下一轮还会判到同一个动作;
        首次拉起(rt 无记录)不受退避影响, 与「刚武装」时的 _spawn_guardian 直调同口径。
        """
        now = time.monotonic()
        # None = 首拉不受退避(方法 docstring 口径); 旧写法 or 0.0 会把开机后前 RESPAWN_BACKOFF 秒全算成退避窗口
        # (monotonic 0 点是开机时刻, 见 pitfalls/testing/monotonic-warn-sentinel.md, issue 26-10-31-0932)
        respawn_ts = rt.get("respawn_ts")
        if respawn_ts is not None and now - float(respawn_ts) < ru.RESPAWN_BACKOFF:
            logger.debug(f"relocate | job {job.job_id}: guardian 重拉退避中(距上次 < {ru.RESPAWN_BACKOFF}s), 本轮跳过")
            return
        rt["respawn_ts"] = now
        self._spawn_guardian(job)

    def _spawn_guardian(self, job: RelocateJob) -> bool:
        """拉起 guardian 独立进程(不随 auto-qb 消亡; 规格经文件传, Unicode 路径不经命令行)"""
        data_dir = self._data_dir()
        try:
            spec = {
                "job_id": job.job_id,
                "src": job.src,
                "dst": job.dst,
                "scope": job.scope,
                "hashes": list(job.hashes),
                "mover": job.mover,
                "alias_kind": job.alias_kind,
                "alias_paths": list(job.alias_paths),
                "files": [list(f) for f in self._plan_files(job)],
                "host": self._qb_host(),
                "port": self._qb_port(),
            }
            relocate_journal.write_spec(data_dir, job.job_id, spec)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"relocate | job {job.job_id}: guardian 规格落盘失败({e})")
            return False
        try:
            self._spawn(data_dir, job.job_id)
        except Exception as e:  # noqa: BLE001 - 拉起失败只告警: 下轮心跳巡检会重拉
            logger.warning(f"relocate | job {job.job_id}: guardian 拉起失败({e})")
            return False
        return True

    def _spawn(self, data_dir: str, job_id: str) -> None:
        """进程拉起单点(测试替换本方法; 生产 detached + 无窗口, 与 traffic_source.agent 同口径)"""
        import subprocess
        import sys

        args = [sys.executable, "-m", "auto_qb.tools.finalize_watch", "--data-dir", data_dir, "--job", job_id]
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if utils.is_windows():
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(args, **kwargs)

    def _qb_host(self) -> str:
        cfg = getattr(self._ctx, "config", None) if self._ctx is not None else None
        qbt = getattr(cfg, "qbittorrent", None) if cfg is not None else None
        return str(getattr(qbt, "host", "") or "127.0.0.1")

    def _qb_port(self) -> int:
        cfg = getattr(self._ctx, "config", None) if self._ctx is not None else None
        qbt = getattr(cfg, "qbittorrent", None) if cfg is not None else None
        try:
            return int(getattr(qbt, "port", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _norm(path: str) -> str:
        return utils.path_normalize(path or "")

    @staticmethod
    def _receipt(hashes, target: str, cls: str, gate: str, text: str) -> dict:
        return {"hashes": list(hashes), "target": target, "cls": cls, "reasons": [{"gate": gate, "text": text}]}
