"""relocate 执行叶: 相位推进、建链/穿透/收尾、对账、执行入口与撤销(自 relocate_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 relocate_mod.py 原文件逐字一致。
"""
import os
from dataclasses import replace
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from ...config.models import bt_backup_path_of
from ...infra import alias_fs, file_access, relocate_journal, utils
from .. import fastresume
from . import relocate_proof as rp
from . import relocate_units as ru
from .relocate_probe import probe_fingerprint, run_probe
from ...torrents import TorrentRecord
from .relocate_units import GroupFacts, RelocateJob, evaluate_group
from .relocate_common import _LINK_CHUNK, _native, logger

_DAEMON_MODULE = "auto_qb.tools.recycle_daemon"  # S3 回收 daemon 拉起目标(与 _spawn 同款 detached)


def _torrent_v2_of(backup_dir: str, torrent_hash: str) -> str:
    """BT_backup 侧 <hash>.torrent 现算成员 v2 infohash(S3a members 口径的半个单点)

    按成员 hash 直取 <hash>.torrent(不扫目录), compute_infohashes 双算后**对账回落**:
    - hash == v1(v1 种子 / hybrid 的 qB hash 形态)⇒ 返回 v2;
    - hash == v2(v2-only 种子, qB >= 4.4 的 hash 字段即 v2 infohash)⇒ 返回 ""(成员保持
      hash_v1 位携带该 v2 hash —— locate_fastresume 的 <h1>.fastresume 直查同样命中,
      v2-only 的 fastresume/torrent 都以 v2 infohash 命名, N 系列实测);
    - 文件缺失/坏 torrent/对不上号 ⇒ ""(不猜命名, daemon 侧 locate 兜底扫描仍可命中)。
    """
    h = str(torrent_hash or "").strip().lower()
    path = os.path.join(backup_dir, f"{h}.torrent")
    try:
        with open(path, "rb") as f:
            v1, v2, _info = fastresume.compute_infohashes(f.read())
    except (OSError, ValueError):
        return ""
    if v1.lower() == h:
        return v2
    return ""


def arm_members_of(hashes: Iterable[str], backup_dir: str) -> List[dict]:
    """arm 侧 spec.members 成员清单(S3a 协议: 与 relocate_journal.spec_members 消费侧配对)

    v1 可从 hashes 派生(spec_members 缺省口径), 但 hybrid/v2 需显式双 hash(pending 口径
    docstring 钉死「不猜命名」)—— arm 是唯一同时知道组成员与 BT_backup 位置的单点, 在此
    落账。backup_dir 为空(实例未启用 fastresume 收尾)或成员取证不到时 hash_v2 留 "",
    消费侧逐字段兜底, 账形恒为 [{"hash_v1": <str>, "hash_v2": <str>}, ...]。
    """
    backup = str(backup_dir or "").strip()
    out: List[dict] = []
    for h in hashes or ():
        h1 = str(h or "").strip()
        out.append({"hash_v1": h1, "hash_v2": _torrent_v2_of(backup, h1) if backup and h1 else ""})
    return out


class ExecMixin:
    # ---------- 搬: 轮询 / 停滞判据 / 长耗时转 watching ----------

    def _recover(self, job: RelocateJob, rt: dict, mover: TorrentRecord) -> None:
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
            rt["started"] = self._clock.monotonic()
            rt["sample_ts"] = 0.0
            rt["last_size"] = -1
            rt["stall_since"] = 0.0
            self._mark_issued(job)  # 补发路径同样要落账, 否则下次重启还会当成崩溃窗口
            logger.info(f"relocate | job {job.job_id}: 已下发 qB 搬迁(mover {job.mover[:8]} -> {job.dst})")
            return

        now = self._clock.monotonic()
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
            rt["stage"] = "supersede"
            # S5 未收尾再迁移(D15/D20, 硬约束①「先搬后重定向」): 搬移完成(本拍 verify
            # 过 = 目标数据落位)才允许改道 —— 前任 job 的 journal/spec 条目 {A→B}→{A→C}
            # 重定向 + 别名重建指向新目标。无前任 = 纯查表零动作, 同拍落链(常规迁移的
            # 单步预算口径不变); 有前任且未收敛(重定向失败)留在 supersede stage 下一拍
            # 重试, 不回滚不判失败(D20 搬后失败语义: journal 留守、别名幂等重试、告警)。
            if self._supersede_redirect(job, rt):
                self._stage_link(job, rt)
            return
        if stage == "supersede":
            if self._supersede_redirect(job, rt):
                self._stage_link(job, rt)
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
            if job.alias_paths:
                if not self._penetration_ok(job):
                    # 穿透失败: 保留链接现场(便于排查), 不删链接不搬回
                    self._fail(job, "alias_unreadable", "经原路径读不到已迁数据")
                    return
                # 本机穿透过了再补一次 qB 侧自检(运行时 F 兜底, 计划 26-11-04-0055 §04 P4):
                # 本机先判(失败优先级高), qB 侧不可用只跳过不挡武装
                if self._qb_side_check(job, rt) == "failed":
                    # qB 侧不一致: 与本机穿透失败同路径 —— 保留链接现场, 不删链接不搬回
                    self._fail(
                        job,
                        "qb_side_check_failed",
                        "qB 经原路径读到的文件元数据与本机 dst 不一致: 链接可能未被 qB 跟随",
                    )
                    return
            rt["stage"] = "arm"
            return
        if stage == "arm":
            self._arm(job, rt)
            return
        logger.debug(f"relocate | job {job.job_id}: 未知 stage {stage}(按 arm 收口)")
        self._arm(job, rt)

    def _stage_link(self, job: RelocateJob, rt: dict) -> None:
        """moved 段进入建链 stage 的单点(verify→link 与 supersede 收敛共用)"""
        cur = self._jobs.get(job.job_id, job)
        rt["stage"] = "link"
        # 已建链接不重建(崩溃恢复: 重启后 alias_paths 非空, 从断点续建)
        rt["link_pos"] = len(cur.alias_paths)
        rt["links"] = list(cur.alias_paths)

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
                    # 链式再迁移(S5): 经别名搬迁会在 src 留下已指向目标的孪生(硬链接同
                    # inode / 重放半途已建的链接)—— 已在目标指向即幂等跳过(黄金法则 1);
                    # 真文件/真目录撞位(alias_kind_of None)仍走 create 报错, 不静默吞。
                    if alias_fs.alias_kind_of(link) is not None and alias_fs.alias_points_to(link, target):
                        links.append(link)
                        continue
                    os.makedirs(os.path.dirname(link), exist_ok=True)
                    alias_fs.create_file_alias(link, target, kind)
                    links.append(link)
                rt["link_pos"] = pos + len(chunk)
                if rt["link_pos"] < len(files):
                    self._set_job(replace(job, alias_paths=tuple(links)))  # 逐条落账(崩溃可回滚)
                    return False
        except Exception as e:  # noqa: BLE001 - 链接失败: 零成本回滚 + 交对账重建
            logger.warning(f"relocate | job {job.job_id}: 建链接失败({e}) —— 删已建 {len(links)} 条链接, 交对账重建(不搬回)")
            self._remove_links(links)
            self._set_job(
                replace(
                    job,
                    alias_paths=(),
                    phase=ru.PHASE_ARMED,
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

    def _qb_side_check(self, job: RelocateJob, rt: dict) -> str:
        """qB 侧自检(运行时 F 兜底, 计划 26-11-04-0055 §04 P4 / §06 D4): -> passed/failed/skipped

        链接建成后 qB 经 src 原路径读到的就是 dst 的数据 —— 用 rp.link_follow_evidence
        列 src 内容根(qB 视角路径复用计划期 content_root_of 产物, 即 job.scope)带元数据,
        与本机 dst 内容根同相对路径文件的 stat 比对(抽样语义与预检 D 级一致):

        - passed(任一代表文件 size+mtime 一致) => 通过, 照常武装;
        - failed(抽中文件全不一致) => 调用方按本机穿透失败同路径判失败(保留链接现场);
        - skipped(端点 404/400/权限/qB<5.0/客户端缺失等不可判定) => 行为与无自检一致,
          rt 记一笔供排查(不 fail、不往回执 notes 刷屏)。
        """
        try:
            ev = rp.link_follow_evidence(
                self._ctx,
                job.scope,  # qB 视角内容根(计划期既有单点, save_path 派生)
                _native(job.dst, self._scope_rel(job)),  # 本机 dst 内容根(证据侧走 map_to_container 单点)
                names=self._scope_names(job),
            )
        except Exception as e:  # noqa: BLE001 - 自检自身意外炸了按跳过(保守默认: 不挡武装)
            rt["qb_side_check"] = f"skipped: 自检异常({type(e).__name__}: {e})"
            logger.info(f"relocate | job {job.job_id}: qB 侧自检异常按跳过({type(e).__name__}: {e})")
            return "skipped"
        if ev.status == rp.POSITIVE:
            return "passed"
        if ev.status == rp.NEGATIVE:
            return "failed"
        rt["qb_side_check"] = f"skipped: {ev.detail}"
        logger.info(f"relocate | job {job.job_id}: qB 侧自检跳过({ev.detail})")
        return "skipped"

    def _scope_names(self, job: RelocateJob) -> tuple:
        """成员文件表换算到内容根相对名(自检比对集; 复用 _cr_files 既有换算单点)"""
        return tuple(name for name, _size in self._cr_files(self._plan_files(job), job.scope, job.src))

    def _reset_stale_terminal_journal(self, job: RelocateJob, rt: dict) -> bool:
        """arm 前重置上一生命周期残留的终态 journal(issue 26-11-08-0827)

        job_id=sha1(mover|src|dst) 同组同目标再发起复用同 id: 上一世 done/cancelled/failed
        终态账不清, daemon 因 STOP_PHASES 对该 id 退休(scan 剔除 + record_rewrites 拒写),
        且 write_journal 前向合并拒绝新世非终态记账 —— 新迁移收不到 fastresume 改写(靠核验
        路径偶然收敛, 数据不在目标位则悬挂)。arm 是新生命周期的收尾链入口, 重置落在这里
        (对账的陈旧支只覆盖 failed 相位, done/cancelled 残留无裁决面)。
        守卫 = clear_journal 既有协议(确证属于上一世才删): 盘上相位 ∈ STOP_PHASES 且 ts
        可解析且早于本生命周期锚点(created_at; _start_job 再发起必重打)。终态互覆与可疑
        failed 证据的裁决面仍在对账表(_journal_failed_action), arm 侧不裁证据只清残留。
        返回 False = 有残留但本拍清不成(盘/权限)或锚定不上: 调用方(_arm)必须收口本拍
        不武装 —— daemon 退休未解除, 武装了也收不到改写; rt["stage"] 保持 arm, 下拍重试。
        证据契约与 _clear_stale_failed_journal 同款: 含 phase/reason/ts 的证据行在删除
        **之前**落盘, 结果行删后另记。
        """
        journal = relocate_journal.read_journal(self._data_dir(), job.job_id)
        if journal is None:
            # 读失败(OSError/坏 JSON 被读单点吞成 None)与「账不存在」不可混淆: 文件在位
            # 而读不出 = 是否上一世残留无从判读, 保守搁置下拍重试(评审 26-11-08-0827
            # finding 1, 与 _clear_stale_failed_journal 读失败保守搁置同向); 确认不在才放行
            if not os.path.exists(relocate_journal.journal_path(self._data_dir(), job.job_id)):
                return True
            if not rt.get("journal_terminal_unreadable_warned"):
                rt["journal_terminal_unreadable_warned"] = True
                logger.warning(
                    f"relocate | job {job.job_id}: journal 文件在位但读不出(IO 抖动/坏形?) —— "
                    "是否上一世终态残留无从判读, 保守不武装, 下拍重试(持续读不出留人工核处)"
                )
            return False
        if str(journal.get("phase") or "") not in relocate_journal.STOP_PHASES:
            return True  # 非终态(在途生命周期/本世 rebuild 再武装): 不属于本口
        try:
            ts_f = float(journal.get("ts"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            ts_f = None
        anchor = float(job.created_at or 0)
        if ts_f is None or anchor <= 0 or ts_f >= anchor:
            # 锚定不上: 机制上不可达(终态 job 出 active 集, 本世 _arm 不可再入), 真发生
            # = 现场存疑 —— 保守不删留人工(黄金法则 2), 绝不把存疑账当残留误删
            if not rt.get("journal_terminal_suspect_warned"):
                rt["journal_terminal_suspect_warned"] = True
                logger.warning(
                    f"relocate | job {job.job_id}: journal 终相位({journal.get('phase')})但 ts "
                    f"不早于本生命周期锚点(created_at={anchor}) —— 无法确证属上一世, 保守不清账"
                    "不武装, 留人工核处(人工出口 = 撤销, journal 终态互覆通道仍开放)"
                )
            return False
        if not rt.get("journal_terminal_clear_evidence_logged"):
            rt["journal_terminal_clear_evidence_logged"] = True
            reason = str(journal.get("reason") or "") or "(无 reason 字段)"
            logger.info(
                f"relocate | job {job.job_id}: 上一世终态账证据留痕(phase={journal.get('phase')}, "
                f"reason={reason}, ts={journal.get('ts')}) —— 同 id 再发起, 即将重置(删除前留痕)"
            )
        if not relocate_journal.clear_journal(self._data_dir(), job.job_id):
            if not rt.get("journal_terminal_clear_warned"):
                rt["journal_terminal_clear_warned"] = True
                logger.warning(
                    f"relocate | job {job.job_id}: 上一世终态账重置失败(盘/权限?), 下拍 arm 重试; "
                    "本拍不武装(journal 仍终态, daemon 尚未解除退休)"
                )
            return False
        logger.info(f"relocate | job {job.job_id}: 已重置上一世终态账 —— daemon 退休随新生命周期解除")
        return True

    def _arm(self, job: RelocateJob, rt: dict) -> None:
        """重归组 + 落账(armed) + 落 arm spec + 确保回收 daemon 在位 + 恢复运行态(S4 新链)

        收尾链(S3a/S3b): arm spec(members 双 hash + bt_backup)落盘 -> _ensure_daemon
        判回收 daemon 缺位即重拉(pending 非空 + daemon 缺位/心跳过期) —— 旧 guardian
        spawn 已随 finalize_watch.py 整文件退役。
        入口先重置上一世残留终态账(_reset_stale_terminal_journal, issue 26-11-08-0827):
        清不成(盘/权限)或锚定不上则本拍不武装, 下拍重试。
        """
        if not self._reset_stale_terminal_journal(job, rt):
            return
        grouping = getattr(self._ctx, "grouping", None)
        if grouping is not None:
            try:
                grouping.regroup_scope(job.scope, job.src, job.hashes)
            except Exception as e:  # noqa: BLE001 - 重归组失败不影响落账(下轮 save_path 变化还会再归)
                logger.warning(f"relocate | job {job.job_id}: 重归组失败({e})")
        # attempts 归零: 重建链接成功即本轮重试周期结束, 上次的历史失败不该占着下次的配额
        armed = replace(job, phase=ru.PHASE_ARMED, armed_at=self._clock.now(), reason="", attempts=0)
        self._set_job(armed)
        self._write_arm_spec(armed)
        self._ensure_daemon(armed, rt)
        self._resume_members(armed)
        logger.info(
            f"relocate | job {armed.job_id}: 已武装收尾(别名 {len(armed.alias_paths)} 条, "
            f"形态 {armed.alias_kind or 'direct'}) —— 回收 daemon 将在 qB 下线窗口改写 fastresume"
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

    # ---------- S5 未收尾再迁移: supersede 重定向(计划 26-11-05-0808 §3.4/D15/D19/D20) ----------

    def _predecessors_of(self, src: str, hashes: Iterable[str]) -> list:
        """本 job 的前任迁移(收尾窗 {armed, rewritten} 且碰本组且旧目标 = 本 job 源根)

        §07「supersede 与对账竞态」行: 判定一律读 state 当前相位(active_jobs 现值),
        判定后的翻转在本 tick 内完成(单一写线程, 无中间态)。改道进行中的前任按
        plan.superseded_from(改道起点根, 翻账时落)补认 —— dst 已翻到新值, 靠它才能
        在重试拍里重新匹配上(D20 重试至收敛)。
        """
        hs = set(hashes or ())
        out = []
        for p in self.active_jobs():
            if p.phase not in ru.FINALIZE_WINDOW_PHASES or not p.touches(hs):
                continue
            if self._norm(p.dst) == self._norm(src) or \
                    self._norm((p.plan or {}).get("superseded_from") or "") == self._norm(src):
                out.append(p)
        return out

    def _physical_anchor(self, mover_save_path: str, files: Sequence[Tuple[str, int]]) -> str:
        """链式再迁移的搬迁锚点根: mover 声明根经活跃 job 作用域解析到**物理根**

        收尾窗再迁移的 mover 账面可能还在旧根(经前任别名做种, N10 实测 setLocation 经
        别名搬 B→C): 直接拿账面 save_path 当 src 会把新 job 的别名/spec/删链门锚到前任
        的别名根上(建链相撞、删链门失锚)。作用域命中 ⇒ 物理保存根 = 前任 dst(setLocation
        落位根, 文件在其 <内容根相对段> 下 —— 内容根段由 _build_links/spec 的 rel 换算
        承担, 不在这里拼)。无命中(常规首迁/账面已在物理根)= 原样返回, 零行为差。
        """
        names = [n for n, _s in files]
        content_root = ru.content_root_of(mover_save_path, names)
        for p in self.active_jobs():
            if p.is_terminal:
                continue
            if p.scope_hit(mover_save_path, content_root):
                return p.dst
        return mover_save_path

    def _supersede_redirect(self, job: RelocateJob, rt: dict) -> bool:
        """supersede 重定向一步(D15 重心): 全部前任改道收敛 = True, 否则 False(下一拍重试)

        顺序钉死(硬约束①/D20): 本 stage 在 moved verify 之后 —— 搬移完成、目标数据落位
        才动前任的账与别名。每任前任按「先账后链」两段提交:
        1. 账面改道(提交点): D19 通用补条目 -> spec.dst {A→B}→{A→C} -> journal 记 retarget
           -> job.dst 翻 C(附 plan.superseded_from=B)—— 全幂等, 失败下一拍重放;
        2. 别名重指向: 逐条 retarget_alias(读旧目标→删→建→穿透校验), 每 tick 一批
           (_LINK_CHUNK), 失败告警留进度, 下一拍幂等续跑(已是目标指向则跳过)。
        任一段失败不回滚不判失败(D20: N12 实测搬后回滚无法恢复成员服务 —— 数据已在 C);
        反馈面 = 本 job 停在 supersede stage(相位 moved)+ WARNING 日志。
        """
        preds = self._predecessors_of(job.src, job.hashes)
        if not preds:
            return True
        ok = True
        for pred in preds:
            if not self._retarget_predecessor(pred, job, rt):
                ok = False
        return ok

    def _retarget_predecessor(self, pred: RelocateJob, job: RelocateJob, rt: dict) -> bool:
        """单个前任的改道(先账后链); 返回是否已收敛"""
        data_dir = self._data_dir()
        old_dst = str((pred.plan or {}).get("superseded_from") or "") or pred.dst
        # ---- D19 旧 mover 覆盖: 扫「save_path 位于被搬离根」的本组成员, 一律补 {B→C} 条目
        # (改道后前任 spec 只会改写 {A→C}, 账面/已改写落在被搬离根 B 的成员只能由本 job
        # 的 spec {B→C} 覆盖 —— 不在本 job 成员清单里的前任成员经 extra_members 并入)。
        self._supersede_cover_movers(pred, job, old_dst)
        # ---- 账面改道(提交点; 各自幂等, 重复执行无副作用)
        n_spec = relocate_journal.retarget_spec(data_dir, pred.job_id, job.dst)
        if n_spec:
            logger.info(f"relocate | supersede: job {pred.job_id} 改写账已改道 {old_dst} -> {job.dst}(spec.dst)")
        if not relocate_journal.mark_journal_retarget(data_dir, pred.job_id, old_dst, job.dst):
            logger.debug(f"relocate | supersede: job {pred.job_id} journal 未记 retarget(已终态/无 journal, 不承重)")
        if self._norm(pred.dst) != self._norm(job.dst):
            pred = self._set_job(replace(
                pred,
                dst=job.dst,
                plan={
                    **(pred.plan or {}), "superseded_from": old_dst
                },
            ))
            logger.warning(
                f"relocate | supersede: job {pred.job_id}({pred.phase}) 已改道 -> {job.dst}"
                f"(原目标 {old_dst}; 收尾窗再迁移 D15, 先搬后重定向)"
            )
        # ---- 别名重指向(逐条幂等; 每 tick 一批, 失败留进度下一拍续)
        plan = pred.plan or {}
        kind = plan.get("link_kind")
        state = rt.setdefault("supersede", {}).setdefault(pred.job_id, {"pos": 0})
        links = list(pred.alias_paths)
        pos = int(state.get("pos") or 0)
        chunk = links[pos:pos + _LINK_CHUNK]
        for link in chunk:
            rel = self._rel_under(pred.src, link)
            if rel is None:
                logger.warning(
                    f"relocate | supersede: job {pred.job_id} 别名 {link} 不在声明源 {pred.src} 下, 跳过重定向(账不自洽, 交人处理)"
                )
                pos += 1
                continue
            target = _native(job.dst, rel)
            try:
                what = alias_fs.retarget_alias(link, target, kind)
                logger.info(f"relocate | supersede: job {pred.job_id} 别名重指向 {link} -> {target}({what})")
            except Exception as e:  # noqa: BLE001 - D20: 重试至收敛, 不回滚
                state["pos"] = pos
                logger.warning(
                    f"relocate | supersede: job {pred.job_id} 别名重指向失败({link} -> {target}): {e} —— "
                    "保留现场下一拍重试(重试至收敛, 不回滚; 搬前占用类预检已前置)"
                )
                return False
            pos += 1
        state["pos"] = pos
        return pos >= len(links)

    def _supersede_cover_movers(self, pred: RelocateJob, job: RelocateJob, moved_away: str) -> None:
        """D19 通用补条目: 被搬离根上的组成员并入本 job 的改写清单(plan.extra_members)

        扫描面 = 前任成员 ∪ 本 job 成员 中「账面 save_path 位于被搬离根(等值 OR 前缀,
        under_alias_root 单点)」者, 加上前任成员全集兜底(改写已落 B 的成员账面还挂在
        A, 账面扫描看不见 —— 前任成员并入本 job spec 后 {B→C} 改写自然命中, 未落 B 的
        成员按 unmatched 出账零副作用)。只进改写清单(spec.members), 不动本 job 的
        hashes/核验集合 —— 补写成员的收敛由删链门(扫全量 save_path)托底。
        """
        store = getattr(self._ctx, "store", None)
        by_hash = getattr(store, "by_hash", {}) or {}
        group = set(pred.hashes) | set(job.hashes)
        hit = set()
        for h, rec in by_hash.items():
            if h in group and ru.under_alias_root(getattr(rec, "save_path", "") or "", (moved_away, )) is not None:
                hit.add(h)
        extras = [h for h in dict.fromkeys((*pred.hashes, *hit)) if h not in set(job.hashes)]
        if not extras:
            return
        plan = job.plan or {}
        merged = [h for h in dict.fromkeys((*extras, *(plan.get("extra_members") or ())))]
        if merged == list(plan.get("extra_members") or ()):
            return
        self._set_job(replace(job, plan={**plan, "extra_members": merged}))
        logger.info(
            f"relocate | supersede: D19 补条目 {len(merged)} 个成员并入 job {job.job_id} 改写清单"
            f"({', '.join(h[:8] for h in merged[:5])} 覆盖被搬离根 {moved_away} 上的任意混合态)"
        )

    def _rel_under(self, root: str, path: str) -> Optional[str]:
        """path 相对 root 的段(重定向目标换算); 不在根下返回 None(账不自洽, 交人处理)"""
        r, p = self._norm(root), self._norm(path)
        if p == r:
            return ""
        if p.startswith(r + "/"):
            return p[len(r) + 1:]
        return None

    # ---------- P6 对账: journal 合并 + 对账表处置 ----------

    def _qb_up(self) -> bool:
        """「qB 在?」= 连得上(三证之一); 结果缓存 10s, 免得每 tick 一次请求"""
        now = self._clock.monotonic()
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

    def _all_at_dst(self, job: RelocateJob) -> bool:
        """全组成员是否都已在目标位置(核验的充分证据; 改写生效+qB 重启加载后成立)"""
        for h in job.hashes:
            rec = self._ctx.store.by_hash.get(h)
            if rec is None or utils.path_normalize(rec.save_path) != utils.path_normalize(job.dst):
                return False
        return True

    def _step_reconcile(self, job: RelocateJob, rt: dict) -> None:
        """收尾窗(armed/rewritten)对账一步(S4 新链): journal 镜像合并 -> 查现场 -> 对账表处置

        - journal rewritten 相位向前合并(S3a 协议: daemon 翻账, state.json 镜像由主循环
          合并 —— D13): journal.phase == rewritten 且 job 还在 armed ⇒ 镜像跟进 rewritten
          (只前进不后退; 终态合并不在此 —— active_jobs 已滤终态, 终态写权在主循环);
        - journal 相位 failed(issue 26-11-07-0527 #3): 处置优先于 daemon 重拉判据 ——
          消费(转 failed 终态)与搁置(证据可疑留人工)两态经 _apply_reconcile 收口并
          提前返回, 不再走 _ensure_daemon(failed 相位对 daemon 已退休, 重拉只会空转);
          陈旧残留(ACT_FAIL_STALE, ts 早于本生命周期锚点)先清账(_clear_stale_failed_
          journal, 删前证据留痕, 解除 daemon 对该 job_id 的退休)再按无账现场重评常规表
          —— 重拉判据一并恢复, 否则同 job_id 再迁移死锁在 armed; 清账未成本拍直接收口
          (不重评不重拉, 下拍重试);
        - 现场三输入(别名在? qB 在? 全员已到目标?)交 ru.reconcile 新表判 WAIT/REBUILD/
          VERIFY; ACT_ENSURE_DAEMON 判据独立(pending + daemon_stale), 每拍顺带判;
        - 旧链输入(seed_state/心跳)已随对账表重定义退役。
        """
        journal = relocate_journal.read_journal(self._data_dir(), job.job_id) or {}
        j_phase = str(journal.get("phase") or "")
        if j_phase == ru.PHASE_REWRITTEN and job.phase == ru.PHASE_ARMED:
            job = self._set_job(replace(job, phase=ru.PHASE_REWRITTEN))
        alias_present = bool(job.alias_paths) and any(self._alias_live(p) for p in job.alias_paths)
        qb_up = self._qb_up()
        at_dst = self._all_at_dst(job)
        action = ru.reconcile(
            job,
            alias_present=alias_present,
            qb_up=qb_up,
            all_at_dst=at_dst,
            journal_phase=j_phase,
            journal_reason=str(journal.get("reason") or ""),
            journal_ts=journal.get("ts"),
        )
        if action == ru.ACT_FAIL_STALE:
            # 陈旧残留(上一生命周期账): 清账解除 daemon 对该 job_id 的退休, 清成后按无账
            # 现场走常规对账(重拉判据一并恢复) —— 残留不清则再迁移死锁在 armed; 清账未成
            # (盘/权限)本拍直接收口: journal 仍 failed, 重评常规表/重拉只会空转, 下拍重试
            if not self._clear_stale_failed_journal(job, rt):
                return
            action = ru.reconcile(job, alias_present=alias_present, qb_up=qb_up, all_at_dst=at_dst)
        elif j_phase == ru.PHASE_FAILED:
            # 消费/搁置: 收口即提前返回, 本拍起不再判重拉 —— 证据消费先于任何重拉动作
            self._apply_reconcile(job, rt, action)
            return
        self._ensure_daemon(job, rt)
        self._apply_reconcile(job, rt, action)

    @staticmethod
    def _alias_live(path: str) -> bool:
        """单条别名存活判定(对账现场输入; S5 链式再迁移的必要修正)

        形态可识(junction/symlink/硬链接 nlink>=2)即活; 形态不可识但路径在也判活 ——
        硬链接别名在孪生(目标侧副本)被搬走后 nlink 收敛到 1, alias_kind_of 认不出它,
        但该路径**本身就是完整数据**, 成员经它照常做种(nlink 数值是「识别」判据, 不是
        「存活」判据)。链式迁移的搬移窗(B 侧被搬空)正落在这个形态上, 旧判据(nlink)
        会误判别名丢失 -> 误触发 REBUILD 清账重建, 打断 supersede 重定向。
        """
        if alias_fs.alias_kind_of(path) is not None:
            return True
        try:
            os.lstat(utils.add_long_path_prefix_for_win(path))
        except OSError:
            return False
        return True

    def _apply_reconcile(self, job: RelocateJob, rt: dict, action: str) -> None:
        """对账动作处置(S4 新链三动作; ACT_ENSURE_DAEMON 的处置在 _ensure_daemon 独立走;
        journal failed 相位的两态在 _consume_failed_journal/_warn_suspect_failed_journal)"""
        if action == ru.ACT_WAIT:
            return
        if action == ru.ACT_FAIL_TERMINAL:
            # 收尾校验失败证据消费: 转 failed 终态, 证据原文保留(_fail 单点)
            self._consume_failed_journal(job)
            return
        if action == ru.ACT_FAIL_SUSPECT:
            # 可疑失败证据: 保守搁置留人工, 不转终态(绝不把可疑证据误判成终态)
            self._warn_suspect_failed_journal(job, rt)
            return
        if action == ru.ACT_VERIFY:
            # 核验+删链推进单点(S4 后半): 全员逐成员等值核验 -> 删链门依赖扫描 ->
            # 在线删别名 + 终态; 核验不过 = journal 悬挂(良性态), 走重放入口/告警。
            self._step_verify(job, rt)
            return
        if action == ru.ACT_REBUILD:
            if int(job.attempts or 0) >= ru.REBUILD_MAX_ATTEMPTS:
                self._fail(
                    job,
                    "rebuild_exhausted",
                    f"重建别名已失败 {int(job.attempts or 0)} 次(上限 {ru.REBUILD_MAX_ATTEMPTS}) —— "
                    f"保留现场交人处理: 通常是权限不足, 修好后重新发起即可",
                )
                return
            # None = 从未重建过, 不吃退避; 旧写法 or 0.0 会把开机后前 REBUILD_BACKOFF 秒全算成退避窗口
            # (monotonic 0 点是开机时刻, 见 pitfalls/testing/monotonic-warn-sentinel.md, issue 26-10-31-0932)
            rebuild_ts = rt.get("rebuild_ts")
            if rebuild_ts is not None and self._clock.monotonic() - float(rebuild_ts) < ru.REBUILD_BACKOFF:
                logger.debug(f"relocate | job {job.job_id}: 重建别名退避中(距上次 < {ru.REBUILD_BACKOFF}s), 本轮跳过")
                return
            rt["rebuild_ts"] = self._clock.monotonic()
            logger.warning(f"relocate | job {job.job_id}: 别名不在而 qB 在线 —— 从 job 账重建别名")
            rt["stage"] = "link"
            rt["link_pos"] = 0
            rt["links"] = []
            job = replace(job, phase=ru.PHASE_MOVED, alias_paths=(), reason="")
            self._set_job(job)
            # journal 同步回 armed(重建要重走 MOVED 执行段; 拒写只可能因已终态, 不炸)
            relocate_journal.write_journal(
                self._data_dir(), job.job_id, {
                    "phase": ru.PHASE_ARMED,
                    "ts": self._clock.now()
                }
            )
            if self._build_links(job, rt):
                rt["stage"] = "penetrate"
            return
        logger.debug(f"relocate | job {job.job_id}: 对账动作 {action} 无处置")

    def _consume_failed_journal(self, job: RelocateJob) -> None:
        """对账消费 journal failed 相位 -> job failed 终态(issue 26-11-07-0527 #3 单点)

        journal 里的 failed 相位 = 收尾窗校验写下的失败证据(guardian 时代的
        reason=verify_mismatch 形态; 对账表已按「reason 非空 + ts 不早于本生命周期锚点」
        判可消费)。处置:
        - job 转 failed 终态, 走 _fail 单点(暂停成员恢复; 现场保留: 不搬回、不删别名);
        - 证据保留: journal 的 reason 原文进 job.reason, ts 与出处进 last_error —— 不丢弃;
        - journal 本身已是终相位(failed 随 STOP_PHASES 扩展纳入停止语义): 不重写不覆盖,
          daemon 与重拉判据据此退休, 且 write_journal 前向合并保证任何非终态写者都抹不掉
          这份证据;
        - 再发起路径: 用户排除故障后重新发起同 id 迁移, 新生命周期对账把本账判陈旧
          (ts 早于新 created_at)清掉(_clear_stale_failed_journal), daemon 退休随之解除
          —— 「排除故障后可重新发起迁移」的承诺成立, 不死锁在 armed。
        幂等(黄金法则 1): 消费后 job 终态, 对账不再触及(active_jobs 滤终态); 直接再入由
        终态闸挡下(以账上现值为准, 不依赖调用方传进来的相位)。
        """
        cur = self.get_job(job.job_id) or job
        if cur.is_terminal:
            return
        journal = relocate_journal.read_journal(self._data_dir(), job.job_id) or {}
        if str(journal.get("phase") or "") != ru.PHASE_FAILED:
            return  # 消费瞬间账已变(单线程下不应发生): 以盘上现值为准, 不凭旧读误判
        reason = str(journal.get("reason") or "").strip()
        if not reason:
            return  # 判定与执行之间证据形变: 回到下拍对账重判(可疑分支会兜住)
        text = (
            f"收尾校验失败(journal 相位 failed, reason={reason}, ts={journal.get('ts')}): "
            "转 failed 终态, 现场保留(别名不删, 成员经别名可读); 排除故障后可重新发起迁移"
        )
        logger.warning(f"relocate | job {job.job_id}: {text}")
        self._fail(cur, reason, text)

    def _warn_suspect_failed_journal(self, job: RelocateJob, rt: dict) -> None:
        """可疑 failed journal 的保守搁置面: WARNING 一次(对账每拍都来, 不设门会刷屏),
        不转终态、不推进、不重拉 —— 留人工核处(黄金法则 2 保守默认; 人工出口 = 撤销,
        journal 终态互覆通道仍开放)。"""
        if rt.get("journal_failed_suspect_warned"):
            return
        rt["journal_failed_suspect_warned"] = True
        logger.warning(
            f"relocate | job {job.job_id}: journal 相位 failed 但证据形态可疑"
            "(reason/ts 缺失或坏形, 或无法锚定所属生命周期) —— 保守不转终态, 留人工核处; "
            "该 job 对账不再推进, 回收 daemon 已按终态退休"
        )

    def _clear_stale_failed_journal(self, job: RelocateJob, rt: dict) -> bool:
        """清理确证陈旧的 failed journal(上一生命周期残留; issue 26-11-07-0527 #3 评审 finding 1)

        failed 入 STOP_PHASES 后 daemon 对该 job_id 退休(scan 剔除 + record_rewrites
        拒写), 而同 job_id 再迁移(_arm 不重置 journal)会带着上一世的失败账进入新生命
        周期 —— 残留账不清, 新生命周期的改写/重放被永久堵死。清理 = 删文件
        (relocate_journal.clear_journal 主循环专属口, 幂等); state.json 旧条目随再发起
        登记被覆盖是既有语义(新世接管)。
        证据契约: 含 reason/ts 的证据行在调用 clear_journal **之前**落盘(进程在删除成功
        与任何后续动作之间退出, 上一世失败证据也有痕可查), 删后只记结果行 —— failed 是
        终相位、内容冻结, 证据行一次留痕即覆盖其后任何一次成功删除。
        只在对账表判 ACT_FAIL_STALE(ts 早于本生命周期锚点)时进入; 落手前对盘上现相位
        再核一次(单线程下不应变, 变了 = 以盘上现值为准不删, 下拍对账重判)。
        返回 False = 本拍未清成(盘/权限或现相位已变): 调用方必须直接收口本拍 —— journal
        仍 failed、daemon 尚未解除退休, 此刻重评常规表/重拉只会空转; 留待下拍对账重试。
        证据行与失败 WARNING 各按 rt 键限频一次(对账每拍都来, 不设门会刷屏)。
        """
        journal = relocate_journal.read_journal(self._data_dir(), job.job_id) or {}
        if str(journal.get("phase") or "") != ru.PHASE_FAILED:
            return False
        if not rt.get("journal_failed_clear_evidence_logged"):
            rt["journal_failed_clear_evidence_logged"] = True
            reason = str(journal.get("reason") or "") or "(空)"
            logger.info(
                f"relocate | job {job.job_id}: 陈旧失败账证据留痕(reason={reason}, "
                f"ts={journal.get('ts')}) —— 上一生命周期残留, 即将清理(删除前留痕)"
            )
        if not relocate_journal.clear_journal(self._data_dir(), job.job_id):
            if not rt.get("journal_failed_clear_warned"):
                rt["journal_failed_clear_warned"] = True
                logger.warning(
                    f"relocate | job {job.job_id}: 陈旧失败账清理失败(盘/权限?), 下拍对账重试; "
                    "本拍不重评常规表不重拉(journal 仍 failed, daemon 尚未解除退休)"
                )
            return False
        logger.info(f"relocate | job {job.job_id}: 已清理陈旧失败账 —— daemon 退休随新生命周期解除")
        return True

    def _step_verify(self, job: RelocateJob, rt: dict) -> None:
        """核验+删链推进(S4 后半单点; 计划 26-11-05-0808 §3.1「qB 重启 → 主循环核验」段)

        - 逐成员核验: API 全员 save_path == dst(等值比较, store 为 qB 镜像)。全部通过
          → 进删链门; 任一不过(未到目标/成员已不在客户端)→ journal 悬挂维持(别名保持,
          daemon 等下一窗口重放), 不判 failed(S4a 已退役 FAILED_TIMEOUT, 悬挂是良性态)。
          首次不过经重放入口(rj.reset_rewrites 清 settled 使重回 pending)请求重放一轮;
          重放一次后仍不过则维持悬挂+告警(防无限改写循环, 保守节奏)。
        - 删链门(N5 教训): 扫 qB 全量种子的 save_path(不限于本组)——「save_path == 别名
          作用域(等值)或位于其下(前缀)」双判据(判据单点 ru.under_alias_root; R7 重锚
          job.src → job.scope + 本组成员豁免, 计划 26-11-07-1300 D9), 命中=0(含组外共享者
          零依赖)→ 主循环在线删别名(alias_fs.remove_alias 非递归绝不跟随)+
          job 终态 done; 命中>0 → 维持别名, 依赖未清零永不删, 反馈面给出解法文案。
        """
        bad = [(h, self._verify_member_state(h, job)) for h in job.hashes if not self._member_at_dst(h, job)]
        if bad:
            self._verify_hang(job, bad)
            return
        deps = self._chain_gate_deps(job)
        if deps:
            text = self._chain_deps_text(job, deps)
            if job.reason != ru.REASON_CHAIN_DEPS or job.last_error != text:
                self._set_job(replace(job, reason=ru.REASON_CHAIN_DEPS, last_error=text))
            logger.info(f"relocate | job {job.job_id}: 删链门依赖未清({len(deps)} 个), 维持别名等依赖消失")
            return
        self._finalize_verified(job)

    def _member_at_dst(self, h: str, job: RelocateJob) -> bool:
        """单成员核验: 在客户端且 save_path == dst(等值比较)"""
        rec = self._ctx.store.by_hash.get(h)
        return rec is not None and self._norm(getattr(rec, "save_path", "") or "") == self._norm(job.dst)

    def _verify_member_state(self, h: str, job: RelocateJob) -> str:
        """核验未过的成员状态描述(文案面: 不在客户端 / 仍在旧路径)"""
        rec = self._ctx.store.by_hash.get(h)
        if rec is None:
            return "已不在客户端"
        return f"save_path 仍在 {getattr(rec, 'save_path', '') or '(空)'}"

    def _verify_hang(self, job: RelocateJob, bad: list) -> None:
        """核验不过: journal 悬挂维持 + 首次请求重放一轮(保守节奏), 不判 failed

        重放 = rj.reset_rewrites 清 settled 记录使其重回 pending(daemon 下一窗口重放改写,
        qB 再重启后核验重判)。verify_replays 计数闸: 重放一次后仍不过 → 维持悬挂 + 告警,
        不再清账(防「改写→重启→核验不过→再改写」无限循环)。日志与账只在状态变化时写
        一笔(对账每拍都会走到这里, 不设变化门会每 tick 刷屏/推 updated_at)。
        """
        detail = "; ".join(f"{h[:8]} {state}" for h, state in bad[:3])
        more = f" 等共 {len(bad)} 个" if len(bad) > 3 else ""
        text = f"核验未过: {detail}{more}(别名维持, 成员经别名可读)"
        data_dir = self._data_dir()
        replays = relocate_journal.verify_replays_of(data_dir, job.job_id)
        changed = job.reason != ru.REASON_VERIFY_FAILED or job.last_error != text
        if replays < 1:
            n = relocate_journal.reset_rewrites(data_dir, job.job_id)
            if n > 0:
                logger.warning(
                    f"relocate | job {job.job_id}: {text} —— 已清改写账请求重放一轮"
                    f"({n} 个成员重回 pending, 待 qB 下线窗口改写后重启 qB 重判)"
                )
                # 镜像回 armed(pending 期): 反馈面转「待收尾」, 对账/ensure_daemon 按 pending 期节拍走
                self._set_job(replace(job, phase=ru.PHASE_ARMED, reason="", last_error=""))
                return
            if changed:
                logger.warning(f"relocate | job {job.job_id}: {text} —— 改写账无 settled 记录可重放, 维持悬挂等 daemon")
                self._set_job(replace(job, reason=ru.REASON_VERIFY_FAILED, last_error=text))
            return
        if changed:
            logger.warning(f"relocate | job {job.job_id}: {text} —— 重放一轮后仍不过, 维持悬挂(不重复清账, 防无限改写循环)")
            self._set_job(replace(job, reason=ru.REASON_VERIFY_FAILED, last_error=text))
        else:
            logger.debug(f"relocate | job {job.job_id}: 核验仍未过(悬挂维持): {text}")

    def _chain_gate_deps(self, job: RelocateJob) -> list:
        """删链门依赖扫描: qB 全量种子的 save_path 对照别名作用域(等值 OR 前缀, N5 双判据);
        本组成员豁免(R7, 计划 26-11-07-1300 D9)—— 成员是否到位由核验步(_step_verify 前置
        的全员 save_path==dst)先行把关, 依赖集只关组外种子: 嵌套放行形态(R4/R5)下成员搬后
        save_path=dst ⊆ src 恒命中 = 收尾自锁(别名永不删, T1a 实测 240s 无收敛)。
        锚 job.src → job.scope(别名真实落点/搬移树, 建账 content_root_of 既有产物): 组外
        种子停旧根兄弟目录不再顶进依赖集(T1b/E7 实测假依赖); 旧账 scope 缺失回落 job.src
        (保守, 与旧锚同口径)。等值面并列 job.src(R7 评审修复): dir_alias 收尾窗内经别名
        落进作用域的组外种子账面 save_path 恰等 job.src —— 只按 scope 前缀判会漏计(D16
        契约对齐, 误放删链 = 该种子断粮)。
        """
        anchor = job.scope or job.src
        members = set(job.hashes)
        records = list(self._ctx.store.by_hash.values())
        save_paths = [getattr(r, "save_path", "") or "" for r in records]
        hits = set(ru.chain_gate_hits(save_paths, anchor, equal_root=job.src))
        return [(r.hash, sp) for r, sp in zip(records, save_paths) if sp in hits and r.hash not in members]

    def _chain_deps_text(self, job: RelocateJob, deps: list) -> str:
        """删链门依赖的反馈面文案(数量 + 样例 + 解法; R7 锚口径 = 别名作用域 + 旧根等值面)"""
        anchor = job.scope or job.src
        samples = ", ".join(h[:8] for h, _sp in deps[:3])
        more = f" 等共 {len(deps)} 个" if len(deps) > 3 else ""
        return (
            f"仍有 {len(deps)} 个种子的保存路径在别名作用域 {anchor} 之下或恰在旧根 {job.src}"
            f"(等值){more}({samples}): "
            "别名删除会让它们找不到数据 —— 请把这些种子迁移到新位置或删除后自动重判"
        )

    def _finalize_verified(self, job: RelocateJob) -> None:
        """核验通过 + 依赖清零: 主循环在线删别名(非递归绝不跟随)-> 终态 done"""
        removed = self._remove_links(job.alias_paths)
        self._set_job(replace(job, phase=ru.PHASE_DONE, reason=ru.REASON_FINALIZED, last_error="", alias_paths=()))
        relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_DONE, "ts": self._clock.now()})
        logger.info(
            f"relocate | job {job.job_id}: 收尾完成(全员核验通过, 删链门依赖清零, 已在线删除别名 "
            f"{removed} 条) —— 成员直读新位置 {job.dst}"
        )

    # ---------- P3 执行入口(三入口共用) ----------

    def relocate_execute(
        self, hashes: Iterable[str] | None, location: str = "", confirm: bool = False, origin: str = "unknown"
    ) -> list:
        """整组迁移执行入口(三入口共用): 预检 -> 暂停 -> qB 搬 -> (后续相位由任务线推进)

        **只做零成本的前置动作**: 闸门不过 ⇒ 一条 blocked 回执, 零副作用; 通过 ⇒
        暂停运行中的成员 + 下发 setLocation(mover) 并落 job 账(phase=moving)。
        搬字节一律由 qB 完成(D2), 本方法绝不复制/移动任何数据文件。

        origin = 发起入口(web / rule / cli 保留值), 只随 job 落账供 WebUI 展示归属, 不参与判定。
        """
        req = [str(h) for h in (hashes or []) if h]
        target = str(location or "").strip()
        conf = self._live_conf()
        items: list = []
        if conf is None or not getattr(conf, "enabled", False):
            return [self._receipt(req, target, "blocked", ru.GATE_DISABLED, "整组迁移未启用(配置键 relocate.enabled)")]
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
            # 部署维闸门(S1 D/E 格)在执行路径同样 fail-fast: 预检(relocate_precheck)不是
            # 唯一入口, web 按钮/规则 move_to 都经本执行体 —— SQLite 后端/bt_backup 不可达
            # 时收尾链整体不可用(D2), 新发起必须拒绝, 不得只靠用户先跑预检。
            # 放在幂等 skip 之后: 同目标在途 job 照旧 skip(T3 降噪), 部署闸不产生假失败。
            deployment = self._deployment_gate(client, hashes)
            if deployment is not None:
                items.append(deployment)
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
            items.append(self._start_job(records, target, facts, verdict, client, origin))
        logger.info(f"relocate | 迁移执行({len(req)} 个 hash -> {len(items)} 项): {self._summ(items)}")
        return items

    def _ensure_probe(self, records: List[TorrentRecord], facts: GroupFacts, verdict: dict) -> Optional[dict]:
        """执行链一次性同机强探测闸(计划 26-11-04-0055 §04 P3 行后半 + §06 D1-D7)

        位置契约(D5): 必须在建账(_start_job)与任何 torrents_set_location 之前调用 ——
        探测失败 => 零建账、零 setLocation; 规则引擎自动迁移共用本入口, 无旁路(D6)。

        决策表(按序短路, 返回 None = 放行, verdict 的 notes 可能被追加; 返回 dict =
        blocked 回执, 与 evaluate_group 现行 blocked item 同形: reasons 元素 gate/cls/text):
        - 单成员组(D2): 完全跳过, 零动作零 note —— 独占内容由 qB 自搬, 免同机证明;
        - dry-run: 零副作用承诺(不落探针文件、不动 qB), note「dry-run: 跳过强探测」;
        - assume_shared=true(D7): 用户显式越权, 跳过探测, note 注明「未经 auto-qb 验证, 由用户承担」;
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
                ["assume_shared: 未经 auto-qb 验证, 由用户承担(用户显式越权) —— 跳过同机强探测"]
            return None
        if facts.same_fs_proved:
            return None
        qb_conf = getattr(getattr(self._ctx, "config", None), "qbittorrent", None)
        if qb_conf is None:
            # qB 连接配置缺失: 指纹无从谈起, 按环境性失败短路(不缓存, 下次迁移重试) ——
            # 退化常量指纹会让多组共享同一缓存键(环境性失败, 不得缓存)
            return {
                **verdict,
                "cls":
                    "blocked",
                "reasons":
                    list(verdict.get("reasons") or []) + [
                        {
                            "gate": ru.GATE_SAME_FS,
                            "cls": ru.CLS_BLOCKED,
                            "text": "qB 连接配置缺失, 无法执行同机探测(环境性失败, 未缓存, 下次迁移将重试)",
                        }
                    ],
            }
        fp = probe_fingerprint(qb_conf)
        hit = self.probe_get(fp)
        if hit is not None:
            if hit["status"] == "passed":
                # 缓存放行的组合口径(拍板 D4): E1 机器级强证明是「一次性」的 —— 同连接身份
                # 缓存(D3), 之后每次多成员迁移仍由预检 D 级路径证据复查(降级链 D->B'),
                # 运行时 F 兜底不变; 见 memory-bank/plans/26-11-04-0055-plan-relocate-same-fs-proof.html §06 D4。
                verdict["notes"] = list(verdict.get("notes") or []) + [f"同机强探测: 命中缓存(指纹 {fp}), 跳过重复探测"]
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
                            "text":
                                f"上次同机探测失败({reason}): 已缓存(FS 不可达方向, 同指纹不重试) —— 出路: 检查 fs.path_map 映射是否覆盖源/目标路径, "
                                "或确认 qB 与 auto-qb 确实共享文件系统后配置 relocate.assume_shared; 确已修复可清除 state.relocate.probes 后重试",
                        }
                    ],
            }
        probe = run_probe(self._ctx, facts.save_path, facts.target)
        if probe.status == "passed":
            self.probe_put(fp, probe.status, probe.evidence)
            return None
        if probe.env:
            # 环境性失败(网络/凭据/连接中断/本机写探针失败): 与 FS 可达性无关, 不缓存(D7②)
            text = (
                f"探测环境性失败: {probe.reason}(与 FS 可达性无关, 未缓存, 下次迁移将重试) —— 出路: 排查环境后重试"
                "(磁盘满/队列满/权限/连接; 容器部署检查 fs.path_map), 或配置 relocate.assume_shared 显式越权"
                "(未经 auto-qb 验证, 由用户承担)"
            )
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

    def _carry_prev_tag_state(self, job_id: str, job: RelocateJob) -> RelocateJob:
        """同一 job_id 重发时继承上一轮的「曾加标签」账

        job_id 由 mover|src→dst 派生, 撤销/失败后重发会复用同一 id; 直接覆盖 ``_jobs[job_id]``
        会丢掉旧账 tag_on=True, 而进程内 ``_tag_applied="add"`` 又会让新 job 的 armed 跳过 add、
        终态也不再 remove —— 旧标签永久留在 qB。继承 tag_on 并清掉进程内镜像记忆, 让本轮
        armed 重新确认 add(幂等)、终态照常摘除。
        """
        prev = self._jobs.get(job_id)
        if prev is None or not prev.tag_on:
            return job
        self._tag_applied.pop(job_id, None)
        self._tag_next_try.pop(job_id, None)
        return replace(job, tag_on=True)

    def _start_job(
        self,
        records: List[TorrentRecord],
        target: str,
        facts: GroupFacts,
        verdict: dict,
        client: Any,
        origin: str = "unknown"
    ) -> dict:
        """建账 + 暂停 + 下发搬迁(一步到位, 后续相位交任务线)

        S5 链式再迁移(D15): src 取**搬迁锚点根**(mover 账面经活跃 job 作用域解析到
        物理根, _physical_anchor), mover 优先选账面已在锚点根的成员(免经别名搬迁留下
        硬链接孪生)—— 常规首迁两者都恒等于 mover 账面, 零行为差。
        """
        mover = records[0]
        src = self._physical_anchor(mover.save_path, facts.files)
        mover = next((r for r in records if self._norm(r.save_path) == self._norm(src)), mover)
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
                    [
                        {
                            "gate": ru.GATE_UNFINISHED,
                            "text":
                                f"该组已有在途迁移(job {job_id}, 相位 {existing.phase}): 同键(同 mover/源/目标)"
                                "重复发起不能并行 —— 收尾窗(armed/rewritten)相位的组可换新目标直接再迁移"
                                "(旧迁移自动改道 supersede), 同目标在途由幂等 skip 去重"
                        }
                    ],
            }
        # ---- S5 搬前预检加项(D20): 别名重建可行性(句柄占用) —— 失败=整体拒绝, 零副作用
        # (此刻尚未暂停/未下发 setLocation; 探测只独占打开链接本体, 不写不删)
        busy = []
        for pred in self._predecessors_of(src, [r.hash for r in records]):
            for link in pred.alias_paths:
                why = alias_fs.probe_alias_rebuild_busy(self._syscall(link))
                if why:
                    busy.append(f"{link}: {why}")
        if busy:
            shown = "; ".join(busy[:3]) + (f" 等共 {len(busy)} 条" if len(busy) > 3 else "")
            return {
                **verdict,
                "cls":
                    "blocked",
                "reasons":
                    [
                        {
                            "gate": ru.GATE_ALIAS_BUSY,
                            "text":
                                f"别名重建可行性预检未过(句柄占用, S5 搬前预检加项): {shown} —— 收尾窗再迁移要把"
                                "前任别名改道到新目标(先删后建), 探测判「此刻删除也会失败」; 请关闭占用者后重试"
                                "(qB 做种句柄带共享删除不会误报; 探测判不了的形态由搬移后重试至收敛兜底)",
                        }
                    ],
            }
        # ---- S5 搬前预检加项(收口评审 #2, D20): 前任别名形态 x 新目标卷位可行性 ——
        # hardlink 形态文件别名改道到跨卷目标只能回落 symlink(见 alias_fs.retarget_alias 跨卷
        # 回落), symlink 也不可用时改道永不可能收敛; 与其搬完把前任吊死在 supersede stage
        # (成员已被搬走, 搬后回滚无法恢复服务), 不如搬前整体拒绝 —— 此刻零副作用, 账面/文件
        # 指纹原样。卷位关系借用本 job 的 src/dst 同卷判定: hardlink 建链约束保证别名与所指
        # 数据同卷, 所指数据根 = pred.dst = 本 job 源根(_predecessors_of 按 pred.dst==src
        # 匹配), 故别名所在 pred.src 与本 job src 同卷; 改道目标 = job.dst(=target), 两者
        # 同/跨卷关系与 facts.same_volume 一致。中途改道链(superseded_from 命中)下该等价
        # 可破(pred.dst 已翻新值), 由 retarget_alias 内层 same_volume 探测 + symlink 回落
        # 兜底, 不在此处复判。
        infeasible = []
        for pred in self._predecessors_of(src, [r.hash for r in records]):
            plan_kind = (pred.plan or {}).get("link_kind")
            for link in pred.alias_paths:
                form = alias_fs.alias_kind_of(self._syscall(link)) or plan_kind
                if form != alias_fs.KIND_HARDLINK:
                    continue  # 非 hardlink 形态: junction/symlink 天然跨卷可建, 不设此闸
                if facts.same_volume is True:
                    continue  # 同卷: hardlink 原形态改道可行
                if facts.file_link_kind == alias_fs.KIND_SYMLINK:
                    continue  # 跨卷但 symlink 回落可行(retarget_alias 会自动降级)
                infeasible.append(link)
        if infeasible:
            shown = "; ".join(infeasible[:3]) + (f" 等共 {len(infeasible)} 条" if len(infeasible) > 3 else "")
            return {
                **verdict,
                "cls":
                    "blocked",
                "reasons":
                    [
                        {
                            "gate": ru.GATE_ALIAS_BUSY,
                            "text":
                                f"前任别名改道可行性预检未过(形态 x 卷位): {shown} —— hardlink 形态别名改道到跨卷"
                                "目标只能回落符号链接, 而本次源/目标组合探不到可用的文件符号链接能力; 强行迁移会把"
                                "前任吊死在 supersede stage。出路: 换同卷目标, 或先修好符号链接能力(提权/开发者模式)",
                        }
                    ],
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
        stamp = self._clock.now()  # 设置位置发起时刻: created_at 与首笔 updated_at 同一窗口, 不取两次
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
            created_at=stamp,
            updated_at=stamp,
            origin=str(origin or "unknown"),
            plan={
                "form": unit.form,
                "link_kind": unit.link_kind,
                "scope": scope,
                "files": [[n, s] for n, s in facts.files],
            },
        )
        job = self._carry_prev_tag_state(job_id, job)
        self._jobs[job_id] = job
        self._rt[job_id] = {
            "issue": True,
            "started": self._clock.monotonic(),
            "sample_ts": 0.0,
            "last_size": -1,
            "stall_since": 0.0
        }
        self._sync_relocating()
        self._persist()
        self._publish_snapshot()
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
            return {"cls": "blocked", "reasons": [{"gate": ru.GATE_GONE, "text": f"未找到迁移任务 {job_id}"}]}
        if self._dry_run():
            return {
                "cls": "blocked",
                "job_id": job_id,
                "reasons": [{
                    "gate": "dry_run",
                    "text": "dry-run: 撤销不执行(不删链接、不搬回)"
                }],
            }
        # ---- 收口评审 #3(§1.2): journal 已有 settled 改写记录时拒绝撤销 —— daemon 已在
        # 窗口把成员 fastresume 改写到 dst; 此时删别名 + 搬回 src, 成员重启会从 dst 载入而
        # 数据已回 src(0420 同款冻结态), 且 journal 落 cancelled 是终态、daemon 不再管 ——
        # 没有任何机制再把 fastresume 改回来, 违反「失败态永远收敛到别名还在、成员可读、
        # journal 待重放」。检查放在成本确认前: 连 confirm 面都不给, 不误导可撤。
        # D15 cancel_chain 只挡同目标在途同伴, 挡不住这种「改写已落账」形态。
        settled = [
            h for h, rec in relocate_journal.read_rewrites(self._data_dir(), job_id).items()
            if isinstance(rec, dict) and rec.get("status") in relocate_journal.REWRITE_SETTLED
        ]
        if settled:
            shown = ", ".join(h[:8] for h in settled[:3]) + (f" 等共 {len(settled)} 个" if len(settled) > 3 else "")
            return {
                "cls":
                    "blocked",
                "job_id":
                    job_id,
                "reasons":
                    [
                        {
                            "gate": "cancel_rewritten",
                            "text":
                                f"该迁移的 fastresume 改写已部分/全部落账({shown}): 成员重启将从 {job.dst} 载入, "
                                f"此时撤销(删别名+搬回 {job.src})会留下指向 {job.dst} 的 fastresume 而数据已回源, "
                                "冻结态无人兜底 —— 请等收尾完成后成员自动落终态(别名退场, 无需撤销), "
                                "需要回迁时重新发起反向迁移",
                        }
                    ],
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
        # ---- S5 护栏: 有改道到同一目标的在途链式迁移时拒绝撤销 —— 撤销会把数据从本 job
        # 目标搬回源, 掏空已改道前任(A→C)的成员数据服务(D15 零悬空纪律的撤销面)。
        # 常规单迁移无同目标在途同伴, 护栏恒不触发(零行为差)。
        codest = [
            p for p in self.active_jobs()
            if p.job_id != job.job_id and p.touches(job.hashes) and self._norm(p.dst) == self._norm(job.dst)
        ]
        if codest:
            names = ", ".join(p.job_id for p in codest[:3])
            return {
                "cls":
                    "blocked",
                "job_id":
                    job_id,
                "reasons":
                    [
                        {
                            "gate": "cancel_chain",
                            "text":
                                f"存在改道到同一目标({job.dst})的在途迁移({names}): 撤销会把共享数据搬回 {job.src}, "
                                "使已改道前任的成员断粮 —— 请先撤销或等其收尾后再撤销本迁移",
                        }
                    ],
            }
        self._remove_links(list(job.alias_paths))
        try:
            self._ctx.api.torrents_set_location(torrent_hashes=[job.mover], location=job.src)
        except Exception as e:  # noqa: BLE001
            self._fail(job, "cancel_failed", str(e))
            return {"cls": "blocked", "cost": cost, "reasons": [{"gate": "cancel_failed", "text": f"搬回被拒: {e}"}]}
        cancelled = self._set_job(replace(job, phase=ru.PHASE_CANCELLED, alias_paths=(), reason="cancelled"))
        # 通知 guardian 退休(它可能在等 qB 退出; 撤销后没有它要干的活了)
        relocate_journal.write_journal(self._data_dir(), job_id, {"phase": ru.PHASE_CANCELLED, "ts": self._clock.now()})
        self._resume_members(cancelled)
        return {"cls": "ok", "cost": cost, "job_id": job_id, "phase": ru.PHASE_CANCELLED}

    # ---------- 链接删除与 guardian 拉起 ----------

    def _remove_links(self, paths: Iterable[str]) -> int:
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

    def _write_arm_spec(self, job: RelocateJob) -> bool:
        """arm 侧规格落盘(S3a/S3 spec 接线, 全仓唯一 write_spec 调用点; S4: guardian spawn
        已随 finalize_watch.py 退役, daemon 拉起走 _ensure_daemon)

        规格经文件传(Unicode 路径不经命令行):
        - bt_backup: bt_backup_path_of(当前 qB 实例查表); 查不中 = 该实例 fastresume 收尾
          功能未启用 ⇒ **不写字段**(S1 五闸本应拦下该形态 —— 这里防御性降级并告警,
          job 停在 armed 等人工, 绝不静默丢收尾);
        - members: S3a 成员清单(arm_members_of, hash_v2 经 <hash>.torrent 现算, 取不到
          留空)。新链 daemon 以此为 pending 账底。S5(D19)追加 plan.extra_members:
          supersede 补条目成员(被搬离根上的前任成员)并入改写清单, 不进本 job 的
          核验集合(hashes 不动)。
        """
        data_dir = self._data_dir()
        backup = bt_backup_path_of(getattr(self._ctx, "config", None))
        extras = [str(h) for h in ((job.plan or {}).get("extra_members") or ()) if str(h)]
        members = list(dict.fromkeys((*job.hashes, *extras)))
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
                "members": arm_members_of(members, backup),
            }
            if backup:
                spec["bt_backup"] = backup
            relocate_journal.write_spec(data_dir, job.job_id, spec)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"relocate | job {job.job_id}: arm 规格落盘失败({e})")
            return False
        if not backup:
            logger.warning(
                f"relocate | job {job.job_id}: bt_backup 未配置, fastresume 改写收尾不会发生 —— "
                "job 停在 armed(别名维持、成员经别名可读), 请检查 bt_backup 配置"
            )
        return True

    def _spawn_daemon(self, data_dir: str, host: str, port: int) -> None:
        """回收 daemon 进程拉起(ACT_ENSURE_DAEMON 处置; 测试替换本方法)

        生产 detached + 无窗口(_popen_detached 单点); 规格不经命令行传 --
        daemon 自扫 <data_dir>/relocate/*.spec.json(S3a 发现面), 命令行只给实例身份。
        """
        import sys

        args = [
            sys.executable,
            "-m",
            _DAEMON_MODULE,
            "--data-dir",
            data_dir,
            "--host",
            str(host or ""),
            "--port",
            str(int(port or 0)),
        ]
        self._popen_detached(args)

    @staticmethod
    def _popen_detached(args: list) -> None:
        """detached 拉起(kernel 单点; 绝不 taskkill —— 退位走 daemon 侧 pid 抢占自检自杀)"""
        import subprocess

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

    def _ensure_daemon(self, job: RelocateJob, rt: dict) -> None:
        """S3 新增对账动作 ACT_ENSURE_DAEMON 的处置(判据独立, 不进 reconcile 旧表)

        判据三段(ensure_daemon_action 纯函数, 任一不成立即静默返回):
        - job 非终态且 spec 带 bt_backup 字段(新链 opt-in; 旧链 spec daemon 不认领,
          拉了也只会空转一个宽限周期 —— 不给旧链 job 白白造进程);
        - pending 集非空(rj.pending_members 现读 spec+journal.rewrites);
        - 回收 daemon 死/心跳过期(rj.daemon_stale 判据单点, 健康在位绝不重复拉起)。
        处置 = _spawn_daemon 重拉 recycle_daemon(subprocess, D12 形制); 拉起节流走
        DAEMON_RESPAWN_BACKOFF(独立 rt 键 ensure_daemon_ts) --
        Popen 失败不留痕迹时, 没有节流就会每 tick 空拉一次进程。
        """
        if job.is_terminal:
            return
        data_dir = self._data_dir()
        spec = relocate_journal.read_spec(data_dir, job.job_id)
        if not isinstance(spec, dict) or not str(spec.get("bt_backup") or "").strip():
            return
        journal = relocate_journal.read_journal(data_dir, job.job_id) or {}
        rewrites = journal.get("rewrites") if isinstance(journal.get("rewrites"), dict) else {}
        pending = relocate_journal.pending_members(spec, rewrites)
        host, port = self._qb_host(), self._qb_port()
        key = relocate_journal.instance_key(host, port)
        stale = relocate_journal.daemon_stale(data_dir, key, max_age=ru.DAEMON_HEARTBEAT_MAX_AGE)
        if ru.ensure_daemon_action(pending=len(pending), daemon_stale=stale) != ru.ACT_ENSURE_DAEMON:
            return
        now = self._clock.monotonic()
        ensure_ts = rt.get("ensure_daemon_ts")
        if ensure_ts is not None and now - float(ensure_ts) < ru.DAEMON_RESPAWN_BACKOFF:
            logger.debug(f"relocate | job {job.job_id}: 回收 daemon 重拉退避中, 本轮跳过")
            return
        rt["ensure_daemon_ts"] = now
        logger.info(f"relocate | job {job.job_id}: 回收 daemon 缺位/心跳过期(pending {len(pending)}), 重拉")
        try:
            self._spawn_daemon(data_dir, host, port)
        except Exception as e:  # noqa: BLE001 - 拉起失败只告警: 下轮 daemon_stale 仍会再判
            logger.warning(f"relocate | job {job.job_id}: 回收 daemon 拉起失败({e})")

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
    def _receipt(hashes: Iterable[str], target: str, cls: str, gate: str, text: str) -> dict:
        return {"hashes": list(hashes), "target": target, "cls": cls, "reasons": [{"gate": gate, "text": text}]}
