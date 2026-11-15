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

    # ---------- 启动对账: 终态 failed 账按物理现状重推相位(计划 26-11-10-0721) ----------

    def _startup_reconcile_tick(self) -> None:
        """启动对账消费面(§03.4): 对 _load_jobs 推导的 rt["reconcile"] 逐笔判一次

        消费窗 = 首轮 qB 连接成功的 tick(与 rt["recover"] 的消费窗同窗 —— recover 由
        _step_move 转 _recover 消费, 两者都只落在启动后的头几个 tick; 本消费挂在
        on_task_line 的活跃推进之后)。qB 探不活时 flag 保持留待首连, 无超时(§07: qB
        恒离线则账维持 failed 现状); 消费即清 flag —— 每进程每笔至多判一次, 运行期新
        失败/新现状不属于本口(失败当下已判对)。判定在 _startup_reconcile_one(只读),
        本方法管触发窗 / flag 卫生 / 重入落账(置 armed_at)与日志(§03.5)。
        """
        pending = [jid for jid, rt in self._rt.items() if rt.get("reconcile")]
        if not pending:
            return
        if not self._qb_up():
            return
        reentered = 0
        kept = 0
        for jid in pending:
            rt = self._rt.get(jid)
            if rt is not None:
                rt.pop("reconcile", None)  # 消费即清: 之后 qB 再抖动/物理现状再变都不重判
            job = self._jobs.get(jid)
            if job is None or job.phase != ru.PHASE_FAILED:
                continue  # 消费窗内账已变(撤销/re-issue): 以账上现值为准, 不凭 flag 重判
            if not self._startup_reconcile_one(job):
                kept += 1
                continue
            reentered += 1
            if rt is not None:
                rt["stage"] = "verify"  # 重入动线与 _recover 同款: 从 moved 校验步走既有链
            self._set_job(replace(job, phase=ru.PHASE_MOVED, armed_at=self._clock.now()))
            logger.info(
                f"relocate | job {job.job_id}: 启动对账重入(mover 已在 dst 且 dst 内容全量在位) —— "
                "恢复 moved 走既有收尾链; 重入落账即置 armed_at(本生命周期自动链配额已用, A1)"
            )
        logger.info(f"relocate | 启动对账 {reentered + kept} 笔: 重入 {reentered} / 保留 {kept}")

    def _startup_reconcile_one(self, job: RelocateJob) -> bool:
        """启动对账判定表(§03.1/§03.2) -> True = 重入 moved(调用方落账并置 armed_at)

        前置闸(A1): armed_at>0 的 failed 一律保持 failed —— 本生命周期的自动链运行
        配额(常规武装或对账重入)已用掉一次, 不进判定表; 重入落账即置位, 闸对所有失败
        形态闭环(含 pre-arm 自检 NEGATIVE 的 armed_at 恒 0 形态), 之后出路 = 人审
        re-issue。armed_at==0 才按双证据分流(G2, 同时成立才重入):
        - 证据一: mover 的 qB 现值 save_path == dst(_member_at_dst 等值比较单点, store
          快照 path_normalize 等值 —— 与 _recover/_step_verify 同口径, 不折叠大小写,
          大小写病态形态落保守保持 failed); save_path 是 qB 自己的搬迁完成记录;
        - 证据二: dst 内容全量在位(_dst_ready 全量真值: plan.files 逐条存在且 size 相等,
          缺文件或 size 不等即不在位) —— 不复用 B′ 抽样口径(rp._bprime_evidence 的
          any-hit 语义会放走「部分在位」态, 对账要全量真值)。
        任一证据不成立或取不到(mover 不在快照/stat 异常/plan 缺失) => False 保持 failed
        (保守默认: 账面服从现实)。判定表行 3(全员==src)与行 4(矛盾/证据不可得)都落
        本支; 行 2(全员==dst)蕴含证据一, 与行 1 同一重入支。
        """
        if job.armed_at > 0:
            return False
        if not self._member_at_dst(job.mover, job):
            return False
        return self._dst_ready(job)

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
            rt["stage"] = "handover"
            # S1a 单活任务模型(D4/I2, 硬约束沿用 D20「先搬后重定向」): 搬移完成(本拍
            # verify 过 = 目标数据落位)才统一改指移交别名 —— 前任已在发起瞬间收官为
            # 只读历史(收官点在 _start_job), 其别名清单在本 job 的 plan.inherited 上,
            # 此处逐条改指到本 job 终位置(别名始终直指物理数据, 无 A→B→C 链)。无移交
            # = 纯查表零动作, 同拍落链(常规迁移的单步预算口径不变); 有移交且未收敛
            # (改指失败)留在 handover stage 下一拍重试, 不回滚不判失败(D20 搬后失败
            # 语义: 别名幂等重试、告警)。
            if self._handover_redirect(job, rt):
                self._stage_link(job, rt)
            return
        if stage == "handover":
            if self._handover_redirect(job, rt):
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
                # 崩溃窗口孤儿(issue 26-11-08-1608): 别名位已建且恰指向目标 = 上次建成而账
                # 未落(目录别名整条不落账), 幂等跳过(黄金法则 1, 与文件支同一 alias_points_to
                # 探测单点); 指向别处/悬空 = 真冲突, 照旧 create 抛错(保守默认: 不覆盖不静默)。
                # 探测必须在「真目录占位」支之前: junction 在 os.path.islink 判假(Python 3.13
                # 实测, 仅 lstat 的 st_reparse_tag 可识别), 先走占位支会把指向目标的孤儿别名
                # 当真目录判非空误杀。
                # append 一律去重(Phase3 评审 major): 目录支不看 link_pos(文件支的账面口径
                # 保护在这里不成立)—— 最终落账后 _arm 前崩溃的重启续建经 _stage_link 进来时
                # links 已含账面条目, 盲 append 会账面翻倍且每次重启复利。孤儿形态(账空)仍
                # 必须 append 入账 —— 不然别名在盘而账面空, 穿透校验与收尾删链都失管。
                if alias_fs.alias_kind_of(link) is not None and alias_fs.alias_points_to(link, target):
                    if link not in links:
                        links.append(link)
                else:
                    if os.path.isdir(link) and not os.path.islink(link):
                        if os.listdir(link):
                            raise RuntimeError(f"内容根目录非空({link}), 目录别名建不出来")
                        os.rmdir(link)  # qB 搬走文件后留下的空目录
                    alias_fs.create_dir_alias(link, target, kind)
                    if link not in links:
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
            removed = self._rollback_links(job, links)
            logger.warning(
                f"relocate | job {job.job_id}: 建链接失败({e}) —— 按 plan 全量清单回滚删链接 {removed} 条"
                "(含崩溃窗口孤儿), 交对账重建(不搬回)"
            )
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

    def _rollback_links(self, job: RelocateJob, built: Iterable[str]) -> int:
        """建链失败回滚: 按 plan 全量链接清单清理(含崩溃窗口孤儿), 不止已落账条目

        issue 26-11-08-1608: 建链与落账间崩溃窗口会在盘上留下「已建成、账上无」的孤儿
        链接, 旧实现只删 built(账面条目 + 本拍已建/已遇), 本拍没走到位的孤儿清不掉 ——
        此后每轮 ACT_REBUILD 撞 FileExistsError 直至 attempts 耗尽 rebuild_exhausted。
        这里按 plan 文件表(dir_alias 形态 = 目录别名位)重扫全量链接位: 命中链接且
        (本拍账面条目 或 恰指向本 job 目标(alias_points_to, 与建链幂等探测同一单点))
        = 我们建的, 一并删; 指向别处 = 真冲突外来链接, 保守默认不动(黄金法则 2, 不删
        别人的链接, 留给报错路径/人工)。单条失败只告警继续(残余交下一次对账), 返回
        实际删除条数。
        """
        plan = job.plan or {}
        if plan.get("form") == ru.FORM_DIR_ALIAS:
            rels = [self._scope_rel(job)]
        else:
            rels = [rel for rel, _size in self._plan_files(job)]
        built_set = {p for p in (built or ()) if p}
        removed = 0
        seen = set()
        for rel in rels:
            p = self._native(job.src, rel)
            if p in seen:
                continue
            seen.add(p)
            try:
                if alias_fs.alias_kind_of(p) is None:
                    continue
                if p not in built_set and not alias_fs.alias_points_to(p, self._native(job.dst, rel)):
                    continue  # 指向别处 = 不是本 job 的链接, 不删(保守默认)
                alias_fs.remove_alias(p)
                removed += 1
            except Exception as e:  # noqa: BLE001 - 单条失败继续(残余交下一次对账/重建)
                logger.warning(f"relocate | job {job.job_id}: 回滚删链接失败({p}): {e}")
        # 账面兜底: built 里不在 plan 清单上的条目(plan 不随生命周期变, 理论不出现)也清掉
        # —— 旧实现保证删净 built, 这里不回退该保证。
        for p in built_set - seen:
            try:
                if alias_fs.alias_kind_of(p) is not None:
                    alias_fs.remove_alias(p)
                    removed += 1
            except Exception as e:  # noqa: BLE001 - 单条失败继续
                logger.warning(f"relocate | job {job.job_id}: 回滚删链接失败({p}): {e}")
        return removed

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
        - skipped(端点 404/400/权限/qB<5.0/客户端缺失等不可判定, 或 qB 列目录返回链接对象
          元数据 —— 文件级 symlink 未解析, 抽样真伪不可判, 计划 26-11-10-0230 §03.1) =>
          行为与无自检一致, rt 记一笔供排查(不 fail、不往回执 notes 刷屏)。
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
        """单成员组收口: 重归组 + done + 恢复运行态(无别名 ⇒ 无 guardian、无收尾窗口)

        恢复放在终态落账之后: _resume_members 的确认账挂账读的是账面现值, 若在 _set_job
        之前下发, 挂账会被本方法尾部 replace(旧对象) 整体覆盖丢失(issue 26-11-14-1744
        修复面; 其余三出口本来就是先 _set_job 后恢复, 无需动)。
        """
        grouping = getattr(self._ctx, "grouping", None)
        if grouping is not None:
            try:
                grouping.regroup_scope(job.scope, job.src, job.hashes)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"relocate | job {job.job_id}: 重归组失败({e})")
        done = self._set_job(replace(job, phase=ru.PHASE_DONE, reason="direct"))
        self._resume_members(done)
        logger.info(f"relocate | job {job.job_id}: 单成员组迁移完成(qB 自搬, 无需别名)")

    def _scope_rel(self, job: RelocateJob) -> str:
        """内容根相对 src 的段(目录别名的链接位置; 平铺 = "")"""
        sp = job.src.replace("\\", "/").rstrip("/")
        scope = job.scope.replace("\\", "/").rstrip("/")
        return scope[len(sp):].lstrip("/") if scope.startswith(sp + "/") else ""

    # ---------- S1a 单活任务模型: 前任认领与锚点(计划 26-11-15-2340 §03.2 D4/D5) ----------

    def _predecessors_of(self, src: str, hashes: Iterable[str]) -> list:
        """本 job 的前任迁移(收尾窗 {armed, rewritten} 且碰本组且旧目标 = 本 job 源根)

        消费方: _start_job 的搬前预检(alias_busy/形态x卷位)与收官点(_handover_predecessors)
        —— 判定一律读 state 当前相位(active_jobs 现值), 收官在本 tick 内完成(单一写线程,
        无中间态)。前任收官即出活集, 重复调用不会二次认领(幂等, 黄金法则 1)。
        """
        hs = set(hashes or ())
        out = []
        for p in self.active_jobs():
            if p.phase not in ru.FINALIZE_WINDOW_PHASES or not p.touches(hs):
                continue
            if self._norm(p.dst) == self._norm(src):
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

    # ---------- S1a 单活任务模型: 收官与移交(D4/D5, 计划 26-11-15-2340 §03.2) ----------

    def _handover_predecessors(self, preds: list, job: RelocateJob) -> RelocateJob:
        """续迁即收官(单活任务模型 D4/D5, I1): 旧任务立即落只读历史, 链接工作整体移交

        在 _start_job 的 committed 点(全部闸门/暂停通过之后、setLocation 之前)调用:
        - **先落承接账再收官, 全部前任单窗落盘**(评审 should1 + minor-5): 新 job(含
          plan.inherited 移交条目)先入 _jobs, 全部前任在内存一次翻相位后**单次** _persist
          —— 同一份 state.json 窗口带上「承接账 + 全部前任收官」, 多前任中途硬崩不会留
          「pred1 superseded / pred2 仍活」混合态, 也不会出现「前任已 superseded 而移交
          别名无人认领」的孤儿态;
        - 前任逐个置 PHASE_SUPERSEDED(终态: 不可推进/不可撤销/无删除入口; 记录随新任务
          存在而保留, 随新任务整链消亡)并写 journal 同相位(rj.STOP_PHASES 已收
          superseded —— daemon 对前任 spec 即时退休, 不再按 {A→B} 改写成员)。state 盒
          落盘走 state 服务周期刷盘而 journal 即时落盘: journal 写后刷前硬崩的窗口, 重启
          由 _load_jobs 启动对账按 journal 终相位回写收敛(评审 minor-6, failed 交既有启动
          对账重判), 不再悬挂; journal 写前硬崩 = 磁盘 state 陈旧前任仍活, 与既有周期刷盘
          失窗同族(qB 现场/接管 spec 幂等收敛, 用户可重新发起);
        - 前任账面**冻结不动**(dst/别名/alias_paths 原样 —— 原地改道机器退役的账面证据),
          其别名清单与前任终位置(dst, 改指收敛前的真实落点建模锚)进新任务
          plan.inherited(持久, 重启可重建断点形态), 改指施工统一在新任务 moved 段的
          handover stage(_handover_redirect)。前任账上已结转的祖父辈条目(pred.plan.
          inherited)一并**展平归集**(评审 minor-R3-1, 链深 >= 3 不失主), 按 job_id 去重
          原位替换/append —— 整链别名与成员改写义务随每次收官向最新任务归集, 整链一个
          清理单元(计划 §03.2);
        - 前任成员并入 plan.extra_members(D19 补条目语义移交至收官点: 前任成员的
          fastresume 改写由新任务的 spec 承载, 不动新任务核验集合)。
        幂等: 收官后前任出活集, 重复执行不会二次认领(黄金法则 1)。
        """
        inherited = list((job.plan or {}).get("inherited") or [])
        extras = list((job.plan or {}).get("extra_members") or ())
        own = set(job.hashes)
        # 同 id 条目原位替换(评审 major-R2-2 其一): 与 _carry_prev_state 的「inherited 按
        # job_id 去重并入」不变量配对 —— 结转条目与活集认领同 id 相撞时(同键重发 J 失败,
        # K 也被重发重新入活集进收尾窗), 用当前账面值原位替换而非无条件 append: 双条目会
        # 令 _repoint_inherited 按 job_id 分桶的进度游标共享 pos, 第二条目从 pos=len(第一
        # 条目) 处续切, 排前段的链接被永久跳过(I2 破坏)。不变量: plan.inherited 同
        # job_id 恒恰一条。
        carried = {e.get("job_id"): i for i, e in enumerate(inherited) if isinstance(e, dict)}
        for pred in preds:
            if pred.is_terminal:
                continue  # 已收官(重复执行/竞态): 跳过, 不重复进账
            entry = {
                "job_id": pred.job_id,
                "src": pred.src,
                "dst": pred.dst,
                "scope": pred.scope,
                "alias_kind": pred.alias_kind,
                "alias_paths": list(pred.alias_paths),
                "link_kind": str((pred.plan or {}).get("link_kind") or ""),
            }
            if pred.job_id in carried:
                inherited[carried[pred.job_id]] = entry
            else:
                inherited.append(entry)
                carried[pred.job_id] = len(inherited) - 1
            extras = [h for h in dict.fromkeys((*extras, *pred.hashes)) if h and h not in own]
        # 祖父辈条目展平归集(评审 minor-R3-1): pred 自己接管的前任条目(pred.plan.inherited)
        # 一并并入 —— 链深 >= 3 时(J1→J2→J3)若丢弃 J2 账上的 J1 条目, 祖父辈移交别名失主
        # (J3 不改指/终态不删/删链门不扫 A 根), 永久悬空违背「整链一个清理单元」(计划
        # §03.2)。按 job_id 去重: 已在 carried 映射中则原位替换(刷新为最新账面值), 否则
        # append —— 整链别名义务随每次收官向最新任务归集, _handover_redirect /
        # _finalize_verified / 删链门三个既有消费面自动覆盖祖父辈, 无需另改。
        # extra_members 同款归集: 前任账上结转的成员改写义务(J1 混合成员等)不失主, 否则其
        # fastresume 指向祖父辈旧根而 spec 无此成员, 改写通道断裂(与别名归集对称)。
        # 祖父辈条目的 dst 一并刷新为 pred.dst(评审 minor-R4-1: pred 收尾窗 = 改指已收敛,
        # 冻结 dst 已失真) —— 未收敛窗的 actual 建模与现场一致。
        for pred in preds:
            if pred.is_terminal:
                continue  # 已收官(重复执行/竞态): 跳过, 不重复进账
            for sub in (pred.plan or {}).get("inherited") or []:
                if not isinstance(sub, dict) or not sub.get("job_id"):
                    continue  # 坏形条目逐条跳过(不猜不炸)
                sub = dict(sub)
                # 落点锚刷新(评审 minor-R4-1): pred 进收尾窗(armed/rewritten)即其 handover
                # 已收敛 —— 账上继承条目的别名已物理改指 pred.dst, 祖父辈条目里冻结的
                # dst(其自己收官时刻的终位置)在本次收官时刻已失真; 刷新为 pred.dst 使
                # _inherited_add_confirm 未收敛窗的 actual 建模与现场别名真实指向一致。
                sub["dst"] = pred.dst
                if sub.get("job_id") in carried:
                    inherited[carried[sub["job_id"]]] = sub
                else:
                    inherited.append(sub)
                    carried[sub["job_id"]] = len(inherited) - 1
            extras = [
                h
                for h in dict.fromkeys((*extras, *((pred.plan or {}).get("extra_members") or ()))) if h and h not in own
            ]
        plan = dict(job.plan or {})
        if inherited:
            plan["inherited"] = inherited
        if extras and extras != list(plan.get("extra_members") or ()):
            plan["extra_members"] = extras
        job = replace(job, plan=plan)
        # ---- 先落承接账(含 inherited) + 全部前任内存一次翻相位, 单次 _persist 同窗落盘
        # (评审 should1 + minor-5)。终态标签镜像不在此发: 终态 tag 摘除由
        # _reconcile_pending_tags 每拍对 tag_on 终态 job 补扫, 无账面损失。
        self._jobs[job.job_id] = job
        self._jobs_loaded = True
        for pred in preds:
            if pred.is_terminal:
                continue  # 已收官(重复执行/竞态): 跳过, 不重复进账
            self._jobs[pred.job_id
                      ] = replace(pred, phase=ru.PHASE_SUPERSEDED, reason="superseded", updated_at=self._clock.now())
        self._persist()
        data_dir = self._data_dir()
        for pred in preds:
            if pred.is_terminal:
                continue  # 已收官(重复执行/竞态): 跳过, 不重复进账
            # journal 相位写 superseded(读-改-写保留 rewrites 等既有账): daemon 据此即时
            # 退休(STOP_PHASES 含 superseded), 前任 spec 不再驱动改写 —— 其成员的改写
            # 由新任务 spec 承载
            body = relocate_journal.read_journal(data_dir, pred.job_id) or {}
            relocate_journal.write_journal(
                data_dir, pred.job_id, {
                    **body, "phase": ru.PHASE_SUPERSEDED,
                    "superseded_by": job.job_id,
                    "ts": self._clock.now()
                }
            )
            logger.warning(
                f"relocate | 单活模型: job {pred.job_id}({pred.phase}) 续迁即收官 -> 只读历史"
                f"(superseded); 链接工作移交 {job.job_id} 统一改指 -> {job.dst}"
            )
        return job

    def _handover_redirect(self, job: RelocateJob, rt: dict) -> bool:
        """移交 + 统一改指一步(D4/I2): 全部移交别名收敛 = True, 否则 False(下一拍重试)

        stage 在 moved verify 之后(硬约束沿用 D20: 先搬后重定向 —— 搬移完成、目标数据
        落位才动移交别名)。逐条移交别名把旧路径统一改指本 job 的终位置(别名始终直指
        物理数据, 不存在 A→B→C 链): 每个移交条目各跑一批(_LINK_CHUNK/条目/tick),
        幂等(已指向目标 = skipped, retarget_alias 单点), 失败告警留进度下一拍续跑
        (重试至收敛, 不回滚不判失败)。
        断点重建: 进度账在 rt(运行期), 重启后从 0 续跑即可 —— 已改指条目由 skipped 面
        幂等跳过, 移交条目本身在 plan.inherited 随 state 持久(与 _stage_link 从账面
        link_pos 反推断点同一形态, 无独立进度账)。收敛即落持久标记 plan.handover_done
        (评审 minor-4): 改指在 moved 相位内完成, 相位词表无法表达「已收敛」—— 消费面
        (evaluate_add 移交面 actual 建模)按标记分流, 不用相位近似。
        """
        entries = job.inherited
        if not entries:
            return True
        ok = True
        for seq, entry in enumerate(entries):
            if not self._repoint_inherited(entry, job, rt, seq):
                ok = False
        if ok and not (job.plan or {}).get("handover_done"):
            self._set_job(replace(job, plan={**(job.plan or {}), "handover_done": True}))
        return ok

    def _repoint_inherited(self, entry, job: RelocateJob, rt: dict, seq: int = 0) -> bool:
        """单个移交条目的统一改指(逐条幂等; 每 tick 一批, 失败留进度下一拍续)

        进度桶键 = job_id#seq(评审 major-R2-2 其二): 各条目游标独立 —— 若只按 job_id 分桶,
        「结转条目与活集认领同 id 相撞」形态(现由 _handover_predecessors 同 id 原位替换
        防住, 双保险)下双条目会共享 pos, 第二条目从 pos=len(第一条目) 处续切, 排前段的
        链接被永久跳过(I2 破坏)。
        """
        state = rt.setdefault("handover", {}).setdefault(f"{entry.job_id}#{int(seq)}", {"pos": 0})
        links = list(entry.alias_paths)
        pos = int(state.get("pos") or 0)
        chunk = links[pos:pos + _LINK_CHUNK]
        kind = entry.link_kind or None
        for link in chunk:
            rel = self._rel_under(entry.src, link)
            if rel is None:
                logger.warning(
                    f"relocate | handover: 前任 {entry.job_id} 别名 {link} 不在移交声明源 {entry.src} 下, "
                    "跳过改指(账不自洽, 交人处理)"
                )
                pos += 1
                continue
            target = _native(job.dst, rel)
            try:
                what = alias_fs.retarget_alias(link, target, kind)
                logger.info(
                    f"relocate | handover: 前任 {entry.job_id} 别名统一改指 {link} -> {target}({what})"
                    f"(移交自单活模型, 终位置 {job.dst})"
                )
            except Exception as e:  # noqa: BLE001 - D20 沿用: 重试至收敛, 不回滚
                state["pos"] = pos
                logger.warning(
                    f"relocate | handover: 前任 {entry.job_id} 别名改指失败({link} -> {target}): {e} —— "
                    "保留现场下一拍重试(重试至收敛, 不回滚; 搬前占用类预检已前置)"
                )
                return False
            pos += 1
        state["pos"] = pos
        return pos >= len(links)

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

    def _step_absence_shrink(self, job: RelocateJob, rt: dict, *, qb_up: bool) -> Optional[RelocateJob]:
        """R4 成员收缩一步(计划 26-11-13-0448 §03 R4, D5; 判据纯函数 ru.absence_shrink)

        收尾窗内成员从 qB 快照消失 -> 连续 N 拍(ru.ABSENCE_SHRINK_ROUNDS)权威缺席 ->
        从 job.hashes 收缩(_set_job 单点: state 落账 + relocating 登记整表重算 + 快照发布),
        WARNING 留痕 + reason/last_error 注记(ru.REASON_MEMBERS_GONE, 收缩事件本身;
        D16 出路文案归 R5, 不在本面)。全部成员删光后 job.hashes 空集 -> all_at_dst 空转
        通过 -> reconcile 判 VERIFY -> _step_verify 空核验 -> 删链门(R2 交集判据, 计划 26-11-13-0448)-> 收尾,
        链上无空集坑(逐成员循环对空表零迭代)。

        证据与门槛(宁慢勿误删, §07「收缩误判」对策; 全部同源于 store 既有同步机制,
        不造平行快照):
        - qB 在线: _qb_up()(既有单点)—— 离线拍既不计数也不复位;
        - 快照非陈旧: store.rounds_applied(主循环成功应用轮计数, store 文档「轮次基线」
          单点; runtime_views 的 _drained_sync_rounds 同款用法)自本 job 上次判定后有前进
          —— rt["absence_round"] 每轮只判一次(一拍一判, 防「最近一轮」证据跨拍重复计数);
          无轮次基线(=0 或替身缺字段)不可判 -> 跳过;
        - 全量轮不采信: need_validate=True 的拍 = 基线刚由全量响应重建(qB 重启加载窗 /
          重连首轮) —— 全量轮的 last_removed 是「上一基线差集」, 含「还没加载完」的活成员
          (假删除证据), 整拍跳过; 增量轮的 last_removed = qB torrents_removed + 本程序
          自删待报集, 是权威删除证据(确认起点);
        - 静默缺席(无权威证据且计数 0)不计数: 与加载窗同形, 绝不当删除(确认延续只在
          计数已 >0 时生效 —— 删除只在增量轮上报一次, 此后缺席按已确认延续计数)。
        计数账随 job.absent_counts 持久(黄金法则 3), 重启不清零; 成员回归即复位。

        披露(计划 26-11-13-0448 §07「停机期删除不收缩」行, R4 评审轮 1 修 5; 入池
        26-11-14-0401): 本判据把缺席证据**锚定在增量轮删除上报**上, 比计划 R4 字面的
        「qB 在线 + 快照非陈旧」更保守 —— 这是取舍不是疏漏: 计划字面判据无法分辨
        「qB 重启加载窗未加载完」与「真已删除」(全量轮差集把未加载完的活成员当删除,
        误收缩 + 删别名 = 死种), 故宁可不收缩。残余时机: 成员在**本程序离线/qB 同步
        失效期间**被删(恢复轮必为全量轮, 证据被弃用)或删于两判定拍之间被覆盖的多轮里
        (main_tick > 2x sync_interval 配置), 该成员永不进入确认 -> job 维持悬挂(现状
        行为, 非回归); 出口 = 重新添加该种子(成员回归即复位计数, 走 D16「仅删除种子」
        出路再删一次即可在在线稳态下被确认收缩)。
        """
        store = self._ctx.store
        rounds = getattr(store, "rounds_applied", None)
        if not isinstance(rounds, int) or rounds <= 0:
            return None  # 无同步轮基线(store 未被主循环驱动/替身): 判定不可用, 不动账
        if rt.get("absence_round") == rounds:
            return None  # 本轮已判定过(一拍一判): 「最近一轮」证据不得跨拍重复计数
        rt["absence_round"] = rounds
        if not qb_up:
            return None  # qB 离线: 既不计数也不复位
        if bool(getattr(store, "need_validate", True)):
            return None  # 全量轮(基线重建面): 差集含「未加载完」的活成员, 不采信
        removals = getattr(store, "last_removed", None)
        kept, counts, shrunk = ru.absence_shrink(
            job.hashes,
            set(getattr(store, "by_hash", {}) or ()),
            dict(job.absent_counts or ()),
            removals=list(removals) if removals else [],
            gate=True,
        )
        if not shrunk:
            if counts != tuple(sorted(job.absent_counts or ())):
                # 计数有推进/复位但尚未达收缩线: 落账持久(黄金法则 3), 不动 reason
                return self._set_job(replace(job, absent_counts=counts))
            return None
        text = (f"成员已删除, 组账收缩 {len(shrunk)} 个({', '.join(h[:8] for h in shrunk)}); "
                f"剩余 {len(kept)} 个成员继续收尾")
        logger.warning(f"relocate | job {job.job_id}: {text}")
        return self._set_job(
            replace(job, hashes=kept, absent_counts=counts, reason=ru.REASON_MEMBERS_GONE, last_error=text)
        )

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
        - R4 成员收缩(计划 26-11-13-0448 §03 R4, D5): 常规表判定前先走一步
          _step_absence_shrink —— 收尾窗内成员经 N 拍权威确认消失即从 job.hashes 收缩
          (补 0808 丢失的「种子已不存在」收敛行); 收缩后 at_dst 按新账重算, 全部删光即
          空集核验顺 VERIFY -> 删链门 -> 收尾; journal failed 相位不收缩(证据消费优先);
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
        if j_phase != ru.PHASE_FAILED:
            # R4 成员收缩(计划 26-11-13-0448 §03 R4, D5): 收尾窗内成员经多拍确认消失 ->
            # 从 job.hashes 收缩(补 0808 丢失的「种子已不存在」收敛行); 收缩后 job 换新账,
            # at_dst 按收缩后重算 —— 全部删光即空集核验, 本拍就能顺 VERIFY -> 删链门 -> 收尾。
            # journal failed 相位不收缩(证据消费优先, job 即将终态, 收缩是噪音)。
            shrunk = self._step_absence_shrink(job, rt, qb_up=qb_up)
            if shrunk is not None:
                job = shrunk
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
          job.src → job.scope + 本组成员豁免, 计划 26-11-07-1300 D9), 命中面为候选,
          文件级 job 再按「文件清单 x alias_paths 交集」精判 verdict(R2, 计划
          26-11-13-0448 §03 R2, 见 _chain_gate_deps), 命中=0(含组外共享者零依赖)→ 主循环
          在线删别名(alias_fs.remove_alias 非递归绝不跟随)+ job 终态 done; 命中>0 →
          维持别名, 依赖未清零永不删, 反馈面给出解法文案。
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
        形态感知 verdict(R2, 计划 26-11-13-0448 §03 R2, D4): chain_gate_hits 命中面只是
        **候选**(scope 前缀 + src 等值面预过滤, 便宜, files API 只对候选取数); 文件级
        job(alias_kind="file")的最终判定换「文件清单 x job.alias_paths 交集」谓词
        (ru.file_alias_intersects 单点)—— 相交 = 依赖, 不相交(组外异名, 数据落原盘真实
        目录不经别名) = 豁免, 清单不可得(取数失败/空表/client 缺席) = 保守计依赖(宁拦
        勿漏, E8 口径); 取数走 PlanMixin._file_map 既有缓存单点(TorrentRecord.files 惰性
        缓存; 本类与 PlanMixin 同属 RelocateModule 的 MRO, self._file_map 即该方法本体,
        无第二份取数口径)。目录级与 direct(无别名)维持命中即依赖原样
        (direct 判据面零变化 —— issue 26-11-13-0711)。
        单活任务模型(D4)追加**继承面**: 接管的前任作用域(移交条目)各自作为独立的门
        扫一遍(前任收官为历史后不再有自己的门)—— 旧根上的组外种子/未改写成员账面
        同样是依赖, 依赖清零前移交别名不删(前任的门由活任务承接)。
        """
        members = set(job.hashes)
        records = list(self._ctx.store.by_hash.values())
        save_paths = [getattr(r, "save_path", "") or "" for r in records]
        surfaces = [(job.scope or job.src, job.src, job.alias_kind, job.alias_paths)]
        surfaces += [(e.scope or e.src, e.src, e.alias_kind, e.alias_paths) for e in job.inherited]
        api = getattr(self._ctx, "api", None)
        client = getattr(api, "client", None) if api is not None else None
        deps = []
        seen = set()
        for anchor, equal_root, kind, alias_paths in surfaces:
            hits = set(ru.chain_gate_hits(save_paths, anchor, equal_root=equal_root))
            if not hits:
                continue
            file_job = kind == "file"
            for r, sp in zip(records, save_paths):
                if sp not in hits or r.hash in members:
                    continue
                if file_job:
                    fmap = self._file_map(r, client)
                    if ru.file_alias_intersects(sp, list(fmap.keys()), alias_paths) is False:
                        continue  # R2 交集豁免: 组外异名种子数据不经别名, 不是删链门依赖
                key = (r.hash, sp)
                if key not in seen:
                    seen.add(key)
                    deps.append((r.hash, sp))
        return deps

    def _chain_deps_text(self, job: RelocateJob, deps: list) -> str:
        """删链门依赖的反馈面文案(数量 + 样例 + 解法; R7 锚口径 = 别名作用域 + 旧根等值面)

        文件级 job 随 R2 语义改措辞(依赖谓词 = 文件清单 x alias_paths 交集, 计划
        26-11-13-0448 §03 R2/R5): 「N 个种子的文件与别名链接重叠」+ 出路带「立即收尾」
        加速器(依赖清零即自动收尾); 目录级/direct 保留现行 save_path 面措辞
        (scope 前缀 + src 等值面语义仍真)。分流按 job.alias_kind, 同一格式不造第二份。
        """
        samples = ", ".join(h[:8] for h, _sp in deps[:3])
        more = f" 等共 {len(deps)} 个" if len(deps) > 3 else ""
        if job.alias_kind == "file":
            return (
                f"仍有 {len(deps)} 个种子的文件与别名链接重叠{more}({samples}): "
                "别名删除会让它们找不到数据 —— 请把这些种子迁移到新位置或删除后自动重判; "
                "依赖清零即自动收尾, 也可用「立即收尾」按钮加速收尾"
            )
        anchor = job.scope or job.src
        return (
            f"仍有 {len(deps)} 个种子的保存路径在别名作用域 {anchor} 之下或恰在旧根 {job.src}"
            f"(等值){more}({samples}): "
            "别名删除会让它们找不到数据 —— 请把这些种子迁移到新位置或删除后自动重判"
        )

    def _finalize_verified(self, job: RelocateJob) -> None:
        """核验通过 + 依赖清零: 主循环在线删别名(非递归绝不跟随)-> 终态 done

        删除面 = 自有别名 + 移交别名(单活任务模型 D4/D5: 整链一个清理单元 —— 接管的
        前任别名随本 job 终态一并删除, 前任历史账面记录保留不删)。
        """
        targets = [p for p in (job.alias_paths or ()) if p]
        targets += [p for entry in job.inherited for p in entry.alias_paths if p]
        removed = self._remove_links(targets)
        self._set_job(replace(job, phase=ru.PHASE_DONE, reason=ru.REASON_FINALIZED, last_error="", alias_paths=()))
        relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_DONE, "ts": self._clock.now()})
        logger.info(
            f"relocate | job {job.job_id}: 收尾完成(全员核验通过, 删链门依赖清零, 已在线删除别名 "
            f"{removed} 条, 含移交别名) —— 成员直读新位置 {job.dst}"
        )

    # ---------- S1b 整链清理单元(D5, 计划 26-11-15-2340 §03.2/D5) ----------

    def purge_terminal_chain(self, job_id: str) -> list:
        """终态 job + 其整条上游链的清理基元(D5: 整链一个清理单元, 随新任务整链消亡)

        单活模型的清理关系: 新任务账上 plan.inherited 的 job_id 即链上游 —— 清理一个终态
        job 时, 递归沿 inherited 上溯, 全部 superseded 前任一并带走(账 + journal + spec
        三面同删; **先 spec 后 journal**: spec 是 daemon 的发现面(扫 *.spec.json), 先撤
        发现面再撤相位投影, 任一中间态都不会让 daemon 把无主账当活账改写)。

        守卫(黄金法则 2, 保守默认):
        - 头部必须存在且已是终态(在途账无清理入口, D5);
        - 上游只带走 PHASE_SUPERSEDED 前任 —— done/failed/cancelled 记录不属「随新任务
          整链消亡」的移交历史, 保留(分级保留/清空历史是 S3 面);
        - I1 引用保护(比任务口径「活任务引用不可清」更保守): 任一候选仍被**保留账**
          (不在本次候选集内的任何账, 活或终)的 plan.inherited 引用则该候选及其上游一并
          缓行 —— 终态账的移交条目同为有效引用, 强删会让引用方悬空失主; 引用它的账若
          随后被清理, 下一次调用自然补清。

        返回实际清除的 job_id 清单(含头部; 空清单 = 头部不存在/在途/被守卫缓行)。
        消费面: S3 的终态分级保留(成功滚动清理)与「清空历史」按钮直接调用本基元;
        现行代码不存在终态账自动删除面(逐字核实, 计划 26-11-15-2340 §03.2/D3), 故本步无自动消费点。
        """
        data_dir = self._data_dir()
        head = self._jobs.get(job_id)
        if head is None or not head.is_terminal:
            return []
        # 沿 inherited 上溯收集候选(头部 + 全部可达的 superseded 前任; 坏形条目跳过)
        candidates = {job_id: head}
        frontier = [head]
        while frontier:
            cur = frontier.pop()
            for entry in cur.inherited:
                uid = entry.job_id
                if not uid or uid in candidates:
                    continue
                up = self._jobs.get(uid)
                if up is None or up.phase != ru.PHASE_SUPERSEDED:
                    continue  # 非移交历史(不存在/已是其它终态): 不属整链消亡面, 保留
                candidates[uid] = up
                frontier.append(up)
        # I1 引用保护: 被保留账引用的候选缓行; 被缓行候选自己引用的候选一并缓行(至不动点)
        # —— 缓行的账还活着, 其移交条目不能指向已删记录(悬空引用); 引用被缓行候选的候选
        # 不受牵连(它整条记录被删, 引用随记录一起消失, 不悬空)。
        blocked = set()
        for other_id, other in self._jobs.items():
            if other_id in candidates:
                continue
            for entry in other.inherited:
                if entry.job_id in candidates:
                    blocked.add(entry.job_id)
        changed = True
        while changed:
            changed = False
            for cid, cjob in candidates.items():
                if cid not in blocked:
                    continue
                for entry in cjob.inherited:
                    if entry.job_id in candidates and entry.job_id not in blocked:
                        blocked.add(entry.job_id)
                        changed = True
        purged = []
        for cid, cjob in candidates.items():
            if cid in blocked:
                logger.info(f"relocate | 整链清理: job {cid} 仍被保留账引用(I1 保护), 本次缓行")
                continue
            # 证据契约(clear_journal 同款): 删除前留痕 phase/ts, 结果行删后另记
            logger.info(
                f"relocate | 整链清理: job {cid}(phase={cjob.phase}, updated_at={cjob.updated_at}) "
                "即将随链清除(账 + journal + spec)"
            )
            if not self._unlink_account_files(data_dir, cid):
                logger.warning(f"relocate | 整链清理: job {cid} 盘面删除失败(journal/spec), 账保留待重试")
                continue
            self._jobs.pop(cid, None)
            purged.append(cid)
            logger.info(f"relocate | 整链清理: job {cid} 已随链清除")
        if purged:
            self._persist()
            self._sync_relocating()
            self._publish_snapshot()
            self._sync_resuming()
        return purged

    @staticmethod
    def _unlink_account_files(data_dir: str, job_id: str) -> bool:
        """删单账的盘面(journal + spec; 「已不在」按成功计, 幂等)

        顺序钉死: 先 spec(journal 还在时 daemon 即便扫到也没有相位投影可读? 反了 ——
        daemon 扫 spec 命中后读 journal, spec 先删 = 发现面先撤, journal 短暂残留无害);
        再 journal。任一 OSError(非 FileNotFoundError)返回 False, 调用方保留账待重试。
        """
        ok = True
        for path in (relocate_journal.spec_path(data_dir, job_id), relocate_journal.journal_path(data_dir, job_id)):
            try:
                os.remove(path)
            except FileNotFoundError:
                continue
            except OSError as e:
                logger.warning(f"relocate | 整链清理: {path} 删除失败({e})")
                ok = False
        return ok

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
        - 指纹缓存(D3: host+port+username+secret; R1#42 起指纹=HMAC+随机盐, 盐存 state
          relocate.probe_salt, 换盐即全缓存失效重探)命中 passed => 放行;
          命中 failed => blocked(D7 1 同指纹不重试);
        - 未命中 => run_probe 同步执行(常态 ~1.3s): passed => probe_put(passed) 放行;
          failed env=False(FS 不可达) => probe_put(failed) + blocked(D7 1);
          failed env=True(环境性) => 不写缓存 + blocked(下次迁移重试, D7 2)。
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
        # 指纹盐(R1#42): 写路径惰性生成并持久化(换盐 => 旧缓存键全部失效重探); 先于
        # probe_get/probe_put 取盐, 保证同一闸内读/写同键
        fp = probe_fingerprint(qb_conf, self.probe_salt_ensure())
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
            # 环境性失败(网络/凭据/连接中断/本机写探针失败): 与 FS 可达性无关, 不缓存(D7 2)
            text = (
                f"探测环境性失败: {probe.reason}(与 FS 可达性无关, 未缓存, 下次迁移将重试) —— 出路: 排查环境后重试"
                "(磁盘满/队列满/权限/连接; 容器部署检查 fs.path_map), 或配置 relocate.assume_shared 显式越权"
                "(未经 auto-qb 验证, 由用户承担)"
            )
        else:
            # FS 不可达(证读/证写超时): 硬拦 + 缓存失败(D7 1 同指纹不重试 —— 探测要真写一次
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

    def _carry_prev_state(self, job_id: str, job: RelocateJob) -> RelocateJob:
        """同一 job_id 重发时继承上一轮的账:「曾加标签」+「恢复确认余量」+「移交义务」

        job_id 由 mover|src→dst 派生, 撤销/失败后重发会复用同一 id; 直接覆盖 ``_jobs[job_id]``
        会丢掉旧账:
        - tag_on=True: 进程内 ``_tag_applied="add"`` 会让新 job 的 armed 跳过 add、终态也不再
          remove —— 旧标签永久留在 qB。继承 tag_on 并清掉进程内镜像记忆, 让本轮 armed 重新
          确认 add(幂等)、终态照常摘除。
        - resume_pending 非空: 旧生命周期未确认回运行态的余量随覆盖消失, 该组恢复确认失明
          一次(穷尽挂账的成员无人再补发)。把余量并进新 job 的 resume_hashes(现场名单在前、
          结转余量在后、去重), 随出口开账走正常补发确认链。不看 prev 终态(穷尽挂账与中途
          撤销同权结转); resume_retries 是 job 级 int, 新账天然从 0 重计, 结转成员按新生命
          周期重获补发预算。
        - plan.inherited / plan.extra_members(单活任务模型, 评审 major-3): 携带移交条目的
          job 失败/撤销后同键重发, 新账必须结转未消化的移交义务 —— _predecessors_of 只扫
          活集, 前任已收官终态后只能从同键旧账认领, 否则移交别名与前任成员改写失主。
          inherited 按 job_id 去重并入(handover 幂等, 重复条目不叠加), extra_members 并入
          且不进本 job 核验集合; handover_done 不结转(新生命周期重走改指, 幂等收敛)。
        """
        prev = self._jobs.get(job_id)
        if prev is None:
            return job
        if prev.tag_on:
            self._tag_applied.pop(job_id, None)
            self._tag_next_try.pop(job_id, None)
            job = replace(job, tag_on=True)
        carried = tuple(h for h in prev.resume_pending if h not in job.resume_hashes)
        if carried:
            job = replace(job, resume_hashes=tuple(job.resume_hashes) + carried)
        prev_plan = prev.plan or {}
        prev_inherited = [e for e in (prev_plan.get("inherited") or []) if isinstance(e, dict) and e.get("job_id")]
        if prev_inherited:
            merged = list((job.plan or {}).get("inherited") or [])
            seen = {e.get("job_id") for e in merged}
            for e in prev_inherited:
                if e.get("job_id") not in seen:
                    merged.append(e)
                    seen.add(e.get("job_id"))
            job = replace(job, plan={**(job.plan or {}), "inherited": merged})
        prev_extras = [str(h) for h in (prev_plan.get("extra_members") or ()) if str(h)]
        if prev_extras:
            plan = job.plan or {}
            merged_extras = [
                h for h in dict.fromkeys((*prev_extras, *(plan.get("extra_members") or ())))
                if h and h not in set(job.hashes)
            ]
            if merged_extras != list(plan.get("extra_members") or ()):
                job = replace(job, plan={**plan, "extra_members": merged_extras})
        return job

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
                                "(旧迁移立即收官为只读历史并移交链接工作, 单活任务模型 D4), 同目标在途由幂等 skip 去重"
                        }
                    ],
            }
        # ---- 前任认领(单活任务模型 D4): 收官与移交在 committed 点执行(下方), 此处先取
        # 名单供搬前预检消费 —— 预检失败 = 整体拒绝零副作用, 前任保持原样不收官
        preds = self._predecessors_of(src, [r.hash for r in records])
        # ---- S5 搬前预检加项(D20): 别名重建可行性(句柄占用) —— 失败=整体拒绝, 零副作用
        # (此刻尚未暂停/未下发 setLocation; 探测只独占打开链接本体, 不写不删)
        busy = []
        for pred in preds:
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
                                "前任别名统一改指到新目标(先删后建), 探测判「此刻删除也会失败」; 请关闭占用者后重试"
                                "(qB 做种句柄带共享删除不会误报; 探测判不了的形态由搬移后重试至收敛兜底)",
                        }
                    ],
            }
        # ---- S5 搬前预检加项(收口评审 #2, D20): 前任别名形态 x 新目标卷位可行性 ——
        # hardlink 形态文件别名改指到跨卷目标只能回落 symlink(见 alias_fs.retarget_alias 跨卷
        # 回落), symlink 也不可用时改指永不可能收敛; 与其搬完把移交别名吊死在 handover stage
        # (成员已被搬走, 搬后回滚无法恢复服务), 不如搬前整体拒绝 —— 此刻零副作用, 账面/文件
        # 指纹原样。卷位关系借用本 job 的 src/dst 同卷判定: hardlink 建链约束保证别名与所指
        # 数据同卷, 所指数据根 = pred.dst = 本 job 源根(_predecessors_of 按 pred.dst==src
        # 匹配), 故别名所在 pred.src 与本 job src 同卷; 改指目标 = job.dst(=target), 两者
        # 同/跨卷关系与 facts.same_volume 一致(等价破形由 retarget_alias 内层 same_volume
        # 探测 + symlink 回落兜底, 不在此处复判)。
        infeasible = []
        for pred in preds:
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
        # 单成员 direct 免暂停(计划 26-11-14-1741 §03): 单成员组且成员完成态(做种)时跳过
        # 暂停/恢复, qB 直接搬运行中种子(可靠性由 qB 自身维持, D3; 失败由既有停滞看护 +
        # 失败回执兜底)。多成员组暂停不可免 —— 搬 mover = 把其它成员脚下的共享文件搬走,
        # 全组必须按住, 本豁免只对 len(records)==1 生效。resume 语义只做减法: 豁免路径
        # resume_hashes=(), 交 _resume_members 既有幂等 no-op 兜住, 不新增机制。
        exempt = len(records) == 1 and ru.is_complete_state(records[0])
        if exempt:
            running = []
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
        # ---- S1a 续迁即收官(D4/I1): 旧任务立即落只读历史, 链接工作整体移交本 job
        # (committed 点: 全部闸门/暂停已过, 只余 setLocation; dry-run 零副作用不收官;
        # 同键旧账结转(_carry_prev_state)先于收官 —— 收官会把本 job 先登进 _jobs,
        # 后结转会读到自己, 同键终态前任的 tag/resume 结转就丢了)
        job = self._carry_prev_state(job_id, job)
        if preds and not self._dry_run():
            job = self._handover_predecessors(preds, job)
        self._jobs[job_id] = job
        self._jobs_loaded = True  # 会话级不变量: 动 job 账必置位(stop() 补写闸的依据, 见 RelocateModule.__init__ 注)
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
        # 回执按形态分型(计划 26-11-14-1741 §03 顺带面): direct 无别名无武装收尾,
        # 旧文案「完成后自动建别名并武装收尾」对它是误导 —— direct 换专文案, 多成员保留原文;
        # 豁免路径(单成员完成态)再追加一条免暂停说明。
        notes = list(verdict["notes"])
        if unit.form == ru.FORM_DIRECT:
            notes.append("qB 自搬中(无别名)")
        else:
            notes.append("qB 正在搬迁, 完成后自动建别名并武装收尾")
        if exempt:
            notes.append("单种子搬迁: 做种中不暂停, qB 自搬")
        return {
            **verdict,
            "cls": "started",
            "job_id": job_id,
            "phase": job.phase,
            "alias_kind": job.alias_kind,
            "link_count": unit.link_count,
            "notes": notes,
        }

    @staticmethod
    def _alias_kind_of_form(form: str) -> str:
        return {"file_links": "file", "dir_alias": "dir"}.get(form, "")

    # ---------- 撤销(D6 停手语义: 数据与下载器路径零触碰, 需显式确认) ----------

    # D7 三段式确认文案(计划 26-11-15-2340 §03.3, 硬性验收项; 撤销用户引导单点):
    # 其一 后果 / 其二 半途撤销警示 / 其三 手动处置推荐(查看位置/缺件/残留链接/重来)。
    # 现无前端弹窗(确认面 = 本模块两步契约的 cls=confirm 回执, 经 /api/relocate/cancel
    # 的 confirm 开关消费), 三段文案随 guide 字段结构化下发, web 级 drain 测试钉三段在位。
    _CANCEL_GUIDE = {
        "consequence":
            "数据保留在当前位置, 不会搬回: 已搬到目标位置的整份/部分数据原样留在新位置, 源位置不做恢复。",
        "halfway":
            (
                "半途撤销警示: 若撤销时 qB 仍在搬迁途中, 搬迁本身不会被中断, 半搬的数据留在新位置; "
                "撤销不碰成员的下载器路径, 缺件由下载器按成员当前位置自行补下"
                "(未完成路径改写的成员会在源位置回填), 期间该组可能短暂显示缺件/校验中, 属预期现象。"
            ),
        "manual":
            [
                "查看数据当前位置: 迁移浮窗/路径链视图显示该组当前位置, 也可在 qBittorrent 中查看该组种子的保存路径。",
                "缺件处理: 无需人工干预, 下载器按成员当前位置自动补下(位置以 qBittorrent 中该组种子的保存路径为准); "
                "长时间无动作时可在 qBittorrent 中对该组执行「强制重新校验」。",
                "残留链接排查清理: 撤销只删除本任务自己建立的链接; 如源目录仍有可疑残留, 检查其中指向新位置的链接"
                "(符号链接/硬链接), 确认没有其他种子依赖后手动删除。",
                "如需重来: 像首次一样重新发起一次整组迁移即可(会建立新的迁移任务), 无需先清理现场。",
            ],
    }

    def relocate_cancel(self, job_id: str, cost_confirmed: bool = False) -> dict:
        """撤销迁移(D6 停手语义, 计划 26-11-15-2340 §03.3): 停手 + 清账 + 删除自己已建的链接

        数据与下载器路径一律不动(零 setLocation; 含半途撤销: 半搬数据留新位置, 缺件由
        下载器按成员当前位置自行补下 —— 撤销链不碰成员 fastresume, 未完成改写的成员会在
        源位置回填) —— 旧「删链接后 setLocation 搬回源位置」的能力已整体删除(D6),
        不是加开关。未确认时只回三段式确认面(D7: 后果/半途警示/手动处置推荐), 不动任何东西。

        dry_run 时不执行(删链接是真写)。终态 job(DONE/FAILED/CANCELLED/SUPERSEDED)拒绝
        撤销 —— 终态相位没有撤销面(失败现场要保留, 历史记录不改写)。
        继承别名(plan.inherited)不在撤销清理面(D6): 它们是前任的, handover 已统一改指
        本任务终位置, 数据留在新位置后别名与服务连续性成立, 撤销不删不撤 —— 该连续性
        论证有相位前置条件: handover 在 moved 段才跑(D20 先搬后重定向), 只在改指收敛后
        成立; MOVING/WATCHING 期半途撤销时改指未发生, 继承别名仍指前任 dst(= 本任务
        src), qB 撤销后继续搬完即清空该处, 继承别名悬空且任务已终态(无对账无重试无改指)
        —— 这是退役 cancel_inherited 守卫后新开放的窗口, 已接受为遗留风险(确认面其二
        警示缺件由下载器自行补下)。
        """
        job = self._jobs.get(job_id)
        if job is None:
            return {"cls": "blocked", "reasons": [{"gate": ru.GATE_GONE, "text": f"未找到迁移任务 {job_id}"}]}
        # ---- 终态守卫(issue 26-11-08-1608 面 1): DONE/FAILED/CANCELLED/SUPERSEDED 无撤销面
        # —— 历史记录不改写: FAILED 的失败证据(last_error/reason)不得被 CANCELLED 覆盖,
        # 已收尾数据没有「撤销」语义。与 _start_job 的 not existing.is_terminal 同口径;
        # 放在最前 —— 连 dry_run 与确认面都不给, 不误导可撤。
        if job.is_terminal:
            return {
                "cls":
                    "blocked",
                "job_id":
                    job_id,
                "reasons":
                    [
                        {
                            "gate": "cancel_terminal",
                            "text":
                                f"该迁移已落终态(相位 {job.phase}), 当前相位没有撤销面: "
                                "终态记录不改写, 失败账(last_error/reason)保留现场 —— "
                                "失败任务请按失败现场交人处理, 需要回迁时重新发起反向迁移",
                        }
                    ],
            }
        if self._dry_run():
            return {
                "cls": "blocked",
                "job_id": job_id,
                "reasons": [{
                    "gate": "dry_run",
                    "text": "dry-run: 撤销不执行(不删链接、不动数据)"
                }],
            }
        # ---- 三道旧守卫随「搬回」能力一并退役(D6, 计划 26-11-15-2340 §03.3), 能力整体删除
        # 而非加开关 —— 三者的核心动因都是「撤销会搬回数据」, 撤销不再动数据与下载器路径后
        # 前提全部消失:
        # 其一 MOVING/WATCHING 硬拒撤(旧 R1#24): 在途搬迁叠加回搬指令会排队互覆; 新语义下
        #      半途撤销就是停手(落 CANCELLED + 恢复成员, 零 setLocation 零删链), 半搬数据留
        #      新位置、缺件由下载器自行补下, 成员恢复时的短暂 missingFiles 属预期并由确认面
        #      三段式其二警示(D7);
        # 其二 cancel_inherited 过渡守卫(S1a): 撤销搬回会留下悬空继承别名指向已搬空目标;
        #      新语义下继承别名本就不在清理面(不删不撤, 见下), 数据留在新位置后别名与服务
        #      连续性成立, 悬空前提消失;
        # 其三 cancel_rewritten 冻结守卫(REWRITE_SETTLED_FROZEN 判据): 删别名+搬回会留下
        #      指向 dst 的 fastresume 而数据已回源(冻结态无人兜底); 新语义下数据就在 dst,
        #      fastresume 改写与数据位置一致, 冻结态前提消失。member_gone 不冻结的既有边界
        #      语义(卡死悬挂 job 的人工出口)随守卫退役自然豁免, 不存在误伤面。
        if not cost_confirmed:
            return {
                "cls": "confirm",
                "job_id": job_id,
                "reasons": [{
                    "gate": "cost",
                    "text": self._CANCEL_GUIDE["consequence"]
                }],
                "guide": self._CANCEL_GUIDE,
            }
        # (旧 cancel_chain 护栏已随改道机器退役, 计划 26-11-15-2340 §03.2: 单活任务模型下
        # 同组续迁发起瞬间前任即收官终态, 「同目标在途同伴」结构性不存在; 同目标重复发起
        # 在 relocate_execute 幂等 skip 去重, 不再需要撤销面护栏。)
        # ---- 清理面 = 自己已建的链接(job.alias_paths); 继承别名(plan.inherited)不删不撤(D6,
        # 见方法 docstring)。
        # ---- R1#23 校验式收窄保留: _remove_links 逐条删、单条失败只告警继续。残留别名不再有
        # 「回搬穿别名」危险(搬回已退役), 但 CANCELLED 清空 alias_paths 后残留链接会脱离 job
        # 账失管 —— 删不净仍拦下。校验式不用「返回数 == 账面数」: 账面里已被先行删掉的链接
        # (撤销失败后重试 / 外部删除)永远数不齐, 会把撤销永久卡死 —— 直接验「还有没有认得出
        # 的别名留在现场」, 已消失 ≠ 残留(幂等重删语义)。blocked 时现场原样保留(相位与链接
        # 账面未动, 对账照常看到活别名不重建), 修好后重试即可。
        targets = [p for p in (job.alias_paths or ()) if p]
        self._remove_links(targets)
        leftover = [p for p in targets if alias_fs.alias_kind_of(p) is not None]
        if leftover:
            shown = ", ".join(leftover[:3]) + (f" 等共 {len(leftover)} 条" if len(leftover) > 3 else "")
            logger.warning(
                f"relocate | job {job_id}: 撤销中止: {len(leftover)} 条别名删除失败仍残留"
                f"(目标共 {len(targets)} 条), 不清账 —— 留现场交人处理"
            )
            return {
                "cls":
                    "blocked",
                "job_id":
                    job_id,
                "reasons":
                    [
                        {
                            "gate": ru.GATE_CANCEL_ALIAS_LEFT,
                            "text":
                                f"撤销中止: {len(leftover)} 条别名未删净({shown}), 仍指向 {job.dst} —— "
                                "撤销落 CANCELLED 会清空链接账面, 残留链接将脱离任务账失管。"
                                "请解除占用/修复权限后重试撤销, 或人工删除残留链接后再撤销; "
                                "现场已保留(相位与链接账面未动, 数据与下载器路径本就不动)",
                        }
                    ],
            }
        cancelled = self._set_job(replace(job, phase=ru.PHASE_CANCELLED, alias_paths=(), reason="cancelled"))
        # 通知 guardian 退休(它可能在等 qB 退出; 撤销后没有它要干的活了)
        relocate_journal.write_journal(self._data_dir(), job_id, {"phase": ru.PHASE_CANCELLED, "ts": self._clock.now()})
        self._resume_members(cancelled)
        return {"cls": "ok", "job_id": job_id, "phase": ru.PHASE_CANCELLED}

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
        - bt_backup: bt_backup_path_of(relocate.bt_backup 标量现读, 计划 26-11-11-0259 S1);
          未配置 = fastresume 收尾功能未启用 ⇒ **不写字段**(S1 五闸本应拦下该形态 ——
          这里防御性降级并告警, job 停在 armed 等人工, 绝不静默丢收尾);
        - members: S3a 成员清单(arm_members_of, hash_v2 经 <hash>.torrent 现算, 取不到
          留空)。新链 daemon 以此为 pending 账底。S1a(单活任务模型 D4)追加
          plan.extra_members: 收官移交的前任成员并入改写清单(不改写则其 fastresume
          仍指旧根, 移交别名删除后断粮), 不进本 job 的核验集合(hashes 不动);
        - extra_srcs: 移交条目的旧根清单(S1a)—— daemon 按 {每个旧根 -> dst} 逐根改写
          (前任成员的 fastresume 可能仍指前任源根 A), 归一去重(与 src 等值的不重复)。
          无移交时零新键(旧 spec 形状不变)。
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
            extra_srcs = []
            seen_roots = {self._norm(job.src)}
            for entry in job.inherited:
                if not entry.src or self._norm(entry.src) in seen_roots:
                    continue
                seen_roots.add(self._norm(entry.src))
                extra_srcs.append(entry.src)
            if extra_srcs:
                spec["extra_srcs"] = extra_srcs
            if backup:
                spec["bt_backup"] = backup
            relocate_journal.write_spec(data_dir, job.job_id, spec)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"relocate | job {job.job_id}: arm 规格落盘失败({e})")
            return False
        if not backup:
            logger.warning(
                f"relocate | job {job.job_id}: bt_backup 未配置, fastresume 改写收尾不会发生 —— "
                "job 停在 armed(别名维持、成员经别名可读), 请检查 config.relocate.bt_backup 配置"
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
