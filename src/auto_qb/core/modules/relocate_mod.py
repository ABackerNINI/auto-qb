"""RelocateModule: 整组迁移(A/C 别名)模块 —— P2 别名单元 + 闸门(只读)

计划 26-10-18-1604 §04 分期:
- P1(已完成): 配置面接线 —— sections() 认领 relocate 顶层段, apply 按段相等短路;
- P2(本文件当前形态): **别名单元 + 闸门(只读)**。三个公开面:
  1. `relocate_precheck(hashes, location)`: 迁移预检。多选按组拆开逐组判定,
     产出三分流 item(ok / confirm / blocked)+ 自解释 reasons + 告知 notes;
  2. `precheck_add(save_path, name)`: 添加种子预检(§3.6.1)。落点命中别名作用域时
     返回「请求路径 -> 实际落点 -> 目标卷剩余」供确认框二次确认;
  3. `capability_view()`: §3.8 能力面板的六项探测事实(alias_fs.as_dict)。
  预检**零副作用**: 不写 state、无 qB 写 API、种子零变动(与跳检预检 T20 同口径) ——
  只读 store/record/files/server_state + 只触盘(能力探测的建删临时链接是 alias_fs
  既定的「真建真删」探测, 其本身就是只读能力的证明手段)。
- P3 起: 迁移执行体(相位机 + 建/删链接 + 未收尾拦截的真实 job 账); P5/P7 规则
  move_to 入口与 WebUI 迁移视图。本文件的 job 登记表与预检形状即那时的最小骨架,
  不留双份实现。

enabled=false(缺省)时行为为零(黄金法则 2): 路由层 403 fail-closed 挡掉两个预检端点,
模块侧另有一道纵深防御(relocate_precheck 内自查)。启动/热重载时的能力探测也只在
enabled 时做 —— 开关关着却开机建删探测链接, 属于为关着的功能做副作用(R15 口径)。

依赖方向: 本模块 -> infra(alias_fs/file_access/utils) + torrents + 兄弟模块**零**
import(需要别人能力经 ctx); 决策纯函数在 relocate_units(不触盘), 本文件只收集事实。
"""
import logging
import os
import stat
import time
from dataclasses import replace
from typing import Optional

from ...infra import alias_fs, file_access, utils
from ...infra.alias_fs import KIND_SYMLINK
from ...infra import relocate_journal
from ...torrents import TorrentRecord
from ..module import AppContext, ApplyResult, BaseModule
from . import relocate_units as ru
from .grouping_mod import group_key_of
from .relocate_units import (
    CLS_BLOCKED,
    AddFacts,
    GroupFacts,
    RelocateJob,
    evaluate_add,
    evaluate_group,
    same_volume_proof,
)

logger = logging.getLogger(__name__)

# P2 纵深防御: relocate.enabled=false 时预检的拒收文案(路由层已 403, 这里兜底)
_DISABLED_GATE = "disabled"

# qB 未完成文件的孪生后缀(单点 utils.QB_INCOMPLETE_SUFFIX / qb_incomplete_twin_path;
# 组内出现即判「数据未落定」, §3.1 拒绝行)
_QB_TEMP_SUFFIX = utils.QB_INCOMPLETE_SUFFIX

# 每 tick 建链接的条数上限(单步有界: 主循环零阻塞, 验收判据「单步 < 50ms」)
_LINK_CHUNK = 200


def _native(path: str, rel: str) -> str:
    """save_path + qB 相对路径(正斜杠) -> 本机路径(只拼接, 不触盘)"""
    parts = [p for p in str(rel).replace("\\", "/").split("/") if p]
    return os.path.join(path, *parts) if parts else path


def _top_children(files) -> set:
    """组文件在内容根下的直接子级名集合(用于目录 listing 的归属分类)"""
    out = set()
    for name, _size in files:
        parts = [p for p in str(name).replace("\\", "/").split("/") if p]
        if len(parts) > 1:
            out.add(parts[1])
        else:
            out.add(parts[0])
    return out


class RelocateModule(BaseModule):
    """整组迁移模块: relocate 段认领 + P2 只读预检引擎(执行体随 P3)

    三入口(均只读, 经 WEB 命令队列在主循环线程执行, 与写命令串行化):
    relocate_precheck(迁移) / precheck_add(添加种子) / capability_view(能力面板)。
    job 登记表 _jobs 是 P3 执行体落账(state.json relocate.jobs)前的内存形态:
    P2 无执行体故恒空, 但「未收尾拦截」闸门已按真实 job 判定(S10 语义在 P3/P7 前
    即可被单测注入验证)。
    """

    name = "relocate"

    def __init__(self, ctx: Optional[AppContext] = None) -> None:
        self._ctx: Optional[AppContext] = ctx
        self._conf = None  # 生效的 RelocateConfig(热重载换对象即更新)
        self._jobs: dict = {}  # job_id -> RelocateJob(P3 执行体写入; P2 恒空)
        self._rt: dict = {}  # job_id -> 运行期进度(采样式, 不落盘; 重启由 qB 现场恢复)
        self._qb_up_cache: Optional[tuple] = None  # (monotonic, up) 「qB 在?」探测缓存
        self._dry = False  # dry_run(启动期透传; 干跑不落盘不建链, 与全局口径一致)

    def sections(self) -> tuple:
        return ("relocate", )

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        """记录上下文与初始配置; enabled 时探测一次链接能力 + 恢复 job 账(开关关时零副作用, R15)"""
        self._ctx = ctx if ctx is not None else self._ctx
        self._dry = bool(dry_run)
        self._conf = ctx.config.relocate
        if getattr(self._conf, "enabled", False):
            alias_fs.get_capability(refresh=True)
            n = self._load_jobs()
            logger.info(f"relocate | 启动: 整组迁移已启用(恢复在途 job {n} 条), 已完成本机链接能力探测")
        else:
            logger.debug("relocate | 启动: 未启用(enabled=false), 不探测不建链不恢复 job")

    def stop(self) -> None:
        """优雅退出: job 账已在每次推进时落 state(周期落盘由 state 服务兜底), 此处只补一次

        guardian 是独立进程, 不随 auto-qb 消亡(§3.5: 它要在 auto-qb 不在时也能收尾) ——
        故 stop() 不杀 guardian, 也不删链接(qB 可能还在跑, 删链接会造假种)。
        """
        try:
            self._persist()
        except Exception:  # noqa: BLE001 - 退出路径不抛: state 落盘失败不影响进程退出
            logger.debug("relocate | stop: state 补写跳过(上下文不可用)")
        return None

    def apply(self, old, new) -> ApplyResult:
        """段相等短路; 段变化 = 换对象即生效(enabled 开时重探链接能力)"""
        if getattr(old, "relocate", None) == getattr(new, "relocate", None):
            return ApplyResult(self.name)
        self._conf = getattr(new, "relocate", None)
        enabled = bool(getattr(self._conf, "enabled", False))
        if enabled:
            alias_fs.get_capability(refresh=True)
        return ApplyResult(
            self.name, "reloaded", "relocate 段已更新(生效配置已缓存" + (", 已重探链接能力" if enabled else ", 未启用不重探") + ")"
        )

    # ---------- job 登记(P3 执行体的账; P2 只读消费) ----------

    def register_job(self, job: RelocateJob) -> None:
        """登记/更新一个在途迁移(job_id 同键覆盖; P3 相位推进时逐次调用)"""
        self._jobs[job.job_id] = job

    def active_jobs(self) -> tuple:
        """非终态 job 视图(未收尾拦截与别名作用域判定的数据源)"""
        return tuple(j for j in self._jobs.values() if not j.is_terminal)

    def jobs_view(self) -> list:
        """全部 job 的界面视图(终态一并列出: 失败现场要可见 —— §3.5.1「保留现场交人处理」)"""
        return [ru.job_to_dict(j) for j in self._jobs.values()]

    def get_job(self, job_id: str):
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

    # ---------- P3/P6 落账(state.json 单一写者 = 主循环线程) ----------

    def _state_jobs(self) -> dict:
        """state.json 的 relocate.jobs 容器(惰性创建; 上下文缺失返回空 dict 不炸)"""
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return {}
        return data.setdefault("relocate", {}).setdefault("jobs", {})

    def _persist(self) -> None:
        """job 账写回 state(整段重写: 条数 = 组数, 极小; 周期落盘由 state 服务负责)"""
        box = self._state_jobs()
        if not isinstance(box, dict):
            return
        box.clear()
        for jid, job in self._jobs.items():
            box[jid] = ru.job_to_dict(job)

    def _load_jobs(self) -> int:
        """启动/热重载时从 state 恢复 job 账; 非终态的重挂 relocating 登记(抑制缺文件误判)"""
        box = self._state_jobs()
        n = 0
        for jid, d in list(box.items()):
            job = ru.job_from_dict(d)
            if job is None:
                continue
            self._jobs[jid] = job
            # 恢复运行期进度: **不重发 setLocation**(会排队/覆盖, §3.5.1); 已建链接不重建
            self._rt[jid] = {
                "issue": False,
                "started": time.monotonic(),
                "sample_ts": 0.0,
                "last_size": -1,
                "stall_since": 0.0,
                "link_pos": len(job.alias_paths),
                "links": list(job.alias_paths),
            }
            n += 1
        self._sync_relocating()
        return n

    def _sync_relocating(self) -> None:
        """relocating 登记 = 非终态 job 的成员并集(P4: 缺文件扫描与跳检闸门据此让路)"""
        store = getattr(self._ctx, "store", None) if self._ctx is not None else None
        if store is None:
            return
        reg = getattr(store, "relocating_hashes", None)
        if reg is None:  # 老 store 替身无该字段: 自建一份, 不打扰既有测试形状
            reg = set()
            store.relocating_hashes = reg
        reg.clear()
        for job in self.active_jobs():
            reg.update(job.hashes)
            reg.update(job.resume_hashes)

    def _set_job(self, job: RelocateJob) -> RelocateJob:
        """登记相位推进后的 job(单点: 落内存 + 刷登记 + 写 state)"""
        job = replace(job, updated_at=time.time())
        self._jobs[job.job_id] = job
        self._sync_relocating()
        self._persist()
        return job

    # ---------- 任务线: 每 tick 推进一步(P3 状态机) ----------

    def on_task_line(self, force: bool = False) -> None:
        """任务线 hook: 逐非终态 job 推进一步(单步零阻塞, 黄金法则 5 单一写线程)

        未启用时零动作(保守默认); 每步只做「一个可观测推进」(一次采样 / 一批链接 /
        一次 setLocation), 绝不在一个 tick 里跑完整个迁移 —— 大种子搬运要跨很多 tick,
        卡住主循环会让整库同步停滞。
        """
        conf = self._live_conf()
        if conf is None or not getattr(conf, "enabled", False):
            return
        if self._ctx is None or self._ctx.store is None:
            return
        for job in self.active_jobs():
            try:
                self._advance(job)
            except Exception as e:  # noqa: BLE001 - 单 job 异常不得拖垮任务线(其它 job 照常推进)
                logger.exception(f"relocate | job {job.job_id} 推进异常: {e}")
                self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="internal_error", last_error=str(e)))

    def _advance(self, job: RelocateJob) -> None:
        """按相位分派一步"""
        rt = self._rt.setdefault(job.job_id, {})
        phase = job.phase
        if phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING):
            self._step_move(job, rt)
        elif phase == ru.PHASE_MOVED:
            self._step_moved(job, rt)
        elif phase == ru.PHASE_FINALIZING:
            self._step_finalize(job, rt)
        elif phase in (ru.PHASE_ARMED, ru.PHASE_REMOVING, ru.PHASE_REMOVED):
            self._step_reconcile(job, rt)

    # ---------- 搬: 轮询 / 停滞判据 / 长耗时转 watching ----------

    def _step_move(self, job: RelocateJob, rt: dict) -> None:
        store = self._ctx.store
        mover = store.by_hash.get(job.mover)
        if mover is None:
            self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="torrent_gone", last_error="搬迁中种子已不存在"))
            return
        if rt.get("issue", True):
            # 等自有暂停的快照回流(own_write_pending 语义): 未回流前不下发, 免得与暂停排队冲突
            pending = getattr(store, "own_write_pending", None)
            if pending is not None and pending(job.mover):
                return
            try:
                self._ctx.api.torrents_set_location(torrent_hashes=[job.mover], location=job.dst)
            except Exception as e:  # noqa: BLE001 - qB 拒绝: 落 failed, 不自动搬回
                self._set_job(
                    replace(job, phase=ru.PHASE_FAILED, reason="move_rejected", last_error=f"setLocation 被拒: {e}")
                )
                return
            rt["issue"] = False
            rt["started"] = time.monotonic()
            rt["sample_ts"] = 0.0
            rt["last_size"] = -1
            rt["stall_since"] = 0.0
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
            self._set_job(
                replace(job, phase=ru.PHASE_FAILED, reason="move_stalled", last_error="搬迁停滞(dst 不再增长且 qB 已不在 moving)")
            )
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
                self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="verify_mismatch", last_error="目标侧文件数/大小不符"))
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
                self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="alias_unreadable", last_error="经原路径读不到已迁数据"))
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
        armed = replace(job, phase=ru.PHASE_ARMED, armed_at=time.time(), reason="")
        self._set_job(armed)
        self._spawn_guardian(armed)
        if armed.resume_hashes:
            try:
                self._ctx.api.torrents_resume(torrent_hashes=list(armed.resume_hashes))
            except Exception as e:  # noqa: BLE001 - 恢复失败只记: 数据面已就位, 用户可手动起
                logger.warning(f"relocate | job {armed.job_id}: 恢复运行态失败({e})")
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
        if job.resume_hashes:
            try:
                self._ctx.api.torrents_resume(torrent_hashes=list(job.resume_hashes))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"relocate | job {job.job_id}: 恢复运行态失败({e})")
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
            self._spawn_guardian(job)
            return
        if action == ru.ACT_REVERT_INTENT:
            logger.info(f"relocate | job {job.job_id}: 删别名期间 qB 回来了 —— 撤销删除意图, 回 armed")
            relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_ARMED, "ts": time.time()})
            self._set_job(replace(job, phase=ru.PHASE_ARMED))
            self._spawn_guardian(job)
            return
        if action == ru.ACT_REBUILD:
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
                self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="finalize_rejected", last_error=str(e)))
                return
            rt["finalize"] = list(members)
            rt["finalize_ts"] = time.time()
            self._set_job(replace(job, phase=ru.PHASE_FINALIZING))
            return
        if action == ru.ACT_FAILED_GONE:
            self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="torrent_gone", last_error="收尾前种子已被删除"))
            return
        if action == ru.ACT_FAILED_TIMEOUT:
            self._set_job(
                replace(
                    job,
                    phase=ru.PHASE_FAILED,
                    reason="finalize_timeout",
                    last_error="数据已在目标位置, qB 仍指向原路径 —— 已超收尾等待上限, 请手动 setLocation",
                )
            )
            return
        if action == ru.ACT_DONE_EXTERNAL:
            self._set_job(replace(job, phase=ru.PHASE_DONE, reason="external"))
            # 通知 guardian 退休: 否则已终结 job 的守护进程会永远每 10s 写心跳
            relocate_journal.write_journal(self._data_dir(), job.job_id, {"phase": ru.PHASE_DONE, "ts": time.time()})
            return
        logger.debug(f"relocate | job {job.job_id}: 对账动作 {action} 无处置")

    def _finalize_members(self, job: RelocateJob) -> tuple:
        """动态收尾集合(§3.5 / D7): 创建时成员 ∪ 当前落在该作用域的成员, mover 跳过"""
        store = self._ctx.store
        members = []
        for h, rec in store.by_hash.items():
            fmap = self._file_map(rec, self._ctx.api.client) if self._ctx.api is not None else {}
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
                self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="finalize_timeout"))
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
            items.append(self._start_job(records, target, facts, verdict, client))
        logger.info(f"relocate | 迁移执行({len(req)} 个 hash -> {len(items)} 项): {self._summ(items)}")
        return items

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
        """
        job = self._jobs.get(job_id)
        if job is None:
            return {"cls": "blocked", "reasons": [{"gate": "gone", "text": f"未找到迁移任务 {job_id}"}]}
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
            self._set_job(replace(job, phase=ru.PHASE_FAILED, reason="cancel_failed", last_error=str(e)))
            return {"cls": "blocked", "cost": cost, "reasons": [{"gate": "cancel_failed", "text": f"搬回被拒: {e}"}]}
        self._set_job(replace(job, phase=ru.PHASE_CANCELLED, alias_paths=(), reason="cancelled"))
        # 通知 guardian 退休(它可能在等 qB 退出; 撤销后没有它要干的活了)
        relocate_journal.write_journal(self._data_dir(), job_id, {"phase": ru.PHASE_CANCELLED, "ts": time.time()})
        if job.resume_hashes:
            try:
                self._ctx.api.torrents_resume(torrent_hashes=list(job.resume_hashes))
            except Exception:  # noqa: BLE001
                pass
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

    def _dry_run(self) -> bool:
        """干跑标志(start 期透传; 直接构造模块时取上下文的 dry_run, 缺省 False)"""
        if self._dry:
            return True
        return bool(getattr(self._ctx, "dry_run", False))

    @staticmethod
    def _norm(path: str) -> str:
        return utils.path_normalize(path or "")

    @staticmethod
    def _receipt(hashes, target: str, cls: str, gate: str, text: str) -> dict:
        return {"hashes": list(hashes), "target": target, "cls": cls, "reasons": [{"gate": gate, "text": text}]}

    # ---------- P2 预检面一: 迁移预检(只读) ----------

    def _live_conf(self):
        """预检面现取生效配置(ctx 单一真相; _conf 缓存只供 P3 相位机, 预检不消费旧值)"""
        if self._ctx is not None:
            return getattr(self._ctx.config, "relocate", None)
        return self._conf

    def relocate_precheck(self, hashes, location: str = "") -> list:
        """整组迁移预检(只读 dry-run): 多选按组拆开逐组判定, 三分流供确认框摊开

        只读承诺(T20 同口径): 不写 state、不 pop、无任何 qB 写 API、种子零变动 ——
        读的只有 store 记录 / record.files(files API 只读) / server_state(同卷证明) /
        文件系统 listing(内容根归属) / alias_fs 能力探测(建删临时链接是探测既定手段)。
        经命令队列在主循环线程执行(与写命令串行化, 快照无撕裂)。

        返回 list[dict]: 逐组一条 + gone 种子逐条; 字段形状与跳检预检对齐
        (hashes/mover/name/save_path/target/form/cls/reasons/notes ...), summary 由
        WEB 命令层聚合(ok/confirm/blocked)。
        """
        req = [str(h) for h in (hashes or []) if h]
        target = str(location or "").strip()
        conf = self._live_conf()
        items: list = []
        if conf is None or not getattr(conf, "enabled", False):
            return [
                {
                    "hashes":
                        req,
                    "cls":
                        CLS_BLOCKED,
                    "reasons":
                        [
                            {
                                "gate": _DISABLED_GATE,
                                "text": "整组迁移未启用(配置键 relocate.enabled) —— 路由层已 fail-closed, 此处为纵深防御"
                            }
                        ],
                }
            ]
        if not req:
            return [
                {
                    "hashes": [],
                    "cls": CLS_BLOCKED,
                    "reasons": [{
                        "gate": "param",
                        "text": "未提供任何 hash(预检目标不能为空)"
                    }],
                }
            ]
        if not target:
            return [
                {
                    "hashes": req,
                    "cls": CLS_BLOCKED,
                    "reasons": [{
                        "gate": "param",
                        "text": "未提供目标位置(location 不能为空)"
                    }],
                }
            ]
        ctx = self._ctx
        if ctx is None or ctx.store is None:
            return [
                {
                    "hashes": req,
                    "cls": CLS_BLOCKED,
                    "reasons": [{
                        "gate": "unavailable",
                        "text": "模块上下文或种子存储不可用, 无法预检"
                    }],
                }
            ]
        client = ctx.api.client if ctx.api is not None else None
        if client is None:
            return [
                {
                    "hashes": req,
                    "cls": CLS_BLOCKED,
                    "reasons": [{
                        "gate": "unavailable",
                        "text": "qB 客户端未连接, 无法只读预检"
                    }],
                }
            ]

        gone, groups = self._buckets(req)
        items.extend(gone)
        for records in groups:
            facts = self._group_facts(records, target, client)
            items.append(evaluate_group(facts))
        logger.info(f"relocate | 迁移预检({len(req)} 个 hash -> {len(items)} 项): {self._summ(items)}")
        return items

    def _buckets(self, req):
        """按组拆分(预检与执行共用): -> (gone 回执列表, 逐组 records 列表)

        组 key 经**物理位置解析**(§3.4): 已被 qB 搬到 T 的 mover 与仍指向 S 的其余成员
        在有活跃 job 时并成同一组 —— 否则「qB 搬第一个」之后组就地裂开(§2.2)。
        """
        ctx = self._ctx
        store = ctx.store
        client = ctx.api.client if ctx.api is not None else None
        gone_items = []
        present = {}
        for h in req:
            rec = store.get(h)
            if rec is None:
                gone_items.append({"hash": h, "cls": CLS_BLOCKED, "reasons": [{"gate": "gone", "text": "种子已不在客户端"}]})
            else:
                present[h] = rec
        buckets = {}  # group key -> [hashes](仅本次选中的)
        for h, rec in present.items():
            fmap = self._file_map(rec, client)
            root = ru.content_root_of(rec.save_path, list(fmap.keys()))
            key = group_key_of(self.resolve_physical(rec.save_path, root), fmap)
            buckets.setdefault(key, []).append(h)
        groups = []
        for key, selected in buckets.items():
            # 组成员取 store 全组(迁移影响的是整个内容组, 不只是选中的入口种子);
            # store 无该组(如 grouping 关过) 时退回本次选中集合
            members = [h for h in store.groups.get(key, []) if h in store.by_hash] or list(selected)
            records = [store.by_hash[h] for h in members if h in store.by_hash]
            if records:
                groups.append(records)
        return gone_items, groups

    # ---------- 事实收集(只读) ----------

    @staticmethod
    def _file_map(rec: TorrentRecord, client) -> dict:
        """种子的 {规范化相对路径: 大小}(files API 只读, 惰性缓存; 异常按空表保守处理)"""
        try:
            files = rec.files(client)
        except Exception as e:  # noqa: BLE001 - 预检边界: 读不到文件表不进判定, 不漏真相
            logger.warning(f"relocate | 读取文件列表失败({rec.log_repr}): {e}")
            return {}
        return {utils.path_normalize(f.name): f.size for f in files}

    @staticmethod
    def _summ(items) -> str:
        counts = {"ok": 0, "confirm": 0, "blocked": 0}
        for it in items:
            counts[it.get("cls", "blocked")] = counts.get(it.get("cls", "blocked"), 0) + 1
        return f"ok {counts['ok']} / confirm {counts['confirm']} / blocked {counts['blocked']}"

    def _group_facts(self, records, target: str, client) -> GroupFacts:
        """收集一个组的只读事实(内容根归属/目标冲突/空间/同卷证明/能力/链接识别)"""
        fa = file_access.get_file_access()
        store = self._ctx.store
        conf = self._live_conf()
        mover = records[0]
        save_path = mover.save_path
        fmap = self._file_map(mover, client)
        files = tuple(fmap.items())
        names = [n for n, _s in files]
        needed = sum(s for _n, s in files)
        hashes = tuple(r.hash for r in records)

        # ---- 内容根 listing(归属分类; 读不到 = 不可判定 = 不专属) ----
        exclusive: Optional[bool] = None
        misc, external, qb_temp = [], [], []
        if len(names) == 1 and "/" not in names[0]:
            content_root = save_path  # 单文件平铺: 内容根 = save_path
        else:
            firsts = {n.split("/", 1)[0] for n in names if "/" in n}
            content_root = os.path.join(save_path, next(iter(firsts))) if len(firsts) == 1 else save_path
        try:
            entries = fa.scandir(content_root)
        except Exception as e:  # noqa: BLE001 - listing 失败: 不猜归属, 目录别名直接不可用
            logger.debug(f"relocate | 内容根 listing 失败({content_root}): {e}")
            entries = None
        if entries is not None:
            own = _top_children(files)
            ext = [e.name for e in entries if e.name not in own]
            qb_temp = [n for n in ext if n.endswith(_QB_TEMP_SUFFIX)]
            qb_temp += [n for n in names if n.endswith(_QB_TEMP_SUFFIX)]
            rest = [n for n in ext if not n.endswith(_QB_TEMP_SUFFIX)]
            misc, external = self._classify_entries(rest, save_path, content_root, hashes, store, client)
            exclusive = not ext

        # ---- 目标同名冲突(逐文件判定: 同卷/跨卷都适用, 只查本组文件) ----
        conflicts = []
        target_unknown = False
        for n in names[:50]:
            try:
                hit = fa.exists(_native(target, n))
            except Exception:  # noqa: BLE001
                hit = file_access.UNDETERMINED
            if hit is True:
                conflicts.append(n)
            elif hit is file_access.UNDETERMINED:
                target_unknown = True  # 容器映射 miss: 不可判定一律拒绝, 不猜「不存在」
                break

        # ---- 空间 / 同卷 / 同卷证明 ----
        try:
            target_free = fa.disk_usage(target).free
        except Exception:  # noqa: BLE001
            target_free = None
        try:
            src_free = fa.disk_usage(save_path).free
        except Exception:  # noqa: BLE001
            src_free = None
        same_vol = alias_fs.same_volume(self._syscall(save_path), self._syscall(target))
        qb_free = (getattr(store, "server_state", None) or {}).get("free_space_on_disk")
        # 同卷证明的语义是「auto-qb 与 qB 看到同一批盘」: qB 的 free_space_on_disk 报的是
        # 它**默认保存路径**那块卷, 未必是本次迁移的源卷 —— 正向迁移(S->T)时源就是默认路径,
        # 反向迁移/回滚(T->S)时源是 T 而 qB 报 S, 只比源侧会必然误判(P7 真机: 复位搬回被
        # same_fs 拒)。与**任一侧**吻合即证明同机同盘, 安全性不变(远程 qB 两侧都对不上)。
        proved = same_volume_proof(qb_free, src_free) or same_volume_proof(qb_free, target_free)

        # ---- 能力探测 + 形态 kind(目标卷差异由 P3 复探; P2 用进程级能力) ----
        cap = alias_fs.get_capability()
        verdict = alias_fs.platform_verdict(
            cap, target_is_unc=alias_fs.is_unc(target), remote=not proved, same_volume=bool(same_vol)
        )
        file_kind = cap.file_alias_kind(bool(same_vol)) if cap.link_visible_to_host else None
        file_err = ""
        if file_kind is None and len(hashes) > 1:
            bits = []
            if cap.file_symlink.error:
                bits.append(f"文件符号链接: {cap.file_symlink.error}")
            if same_vol and cap.hardlink.error:
                bits.append(f"同卷硬链接: {cap.hardlink.error}")
            if bits and "提权" in " ".join(bits) and not conf.allow_uac:
                bits.append("配置 relocate.allow_uac=false: 不弹 UAC, 直接拒绝")
            file_err = (
                "文件级链接不可建: " + "; ".join(bits) + " —— 出路: ①以管理员身份运行 auto-qb"
                "或开启 Windows 开发者模式 ②换同卷目标走硬链接 ③改用目录别名(需目录专属) ④缩短路径"
            )
        if alias_fs.is_unc(target):
            dir_kind = KIND_SYMLINK if cap.dir_symlink.ok else None
            dir_err = "" if dir_kind else f"UNC 目标下 junction 不可用(reparse 点不能指向 UNC); 目录符号链接: {cap.dir_symlink.error or '不可建'}"
        else:
            dir_kind = cap.dir_alias_kind
            dir_err = "" if dir_kind else "目录别名不可建: " + "; ".join(
                f"{n}: {p.error}" for n, p in (("junction", cap.junction), ("目录链接", cap.dir_symlink)) if p.error
            )

        # ---- 第三方链接与硬链接识别(D11 三层; 只识别代表文件, 不遍历全组) ----
        tp_files, hl_files = (), ()
        tp_dir_note = ""
        # 空文件表(读不到文件列表)没有「代表文件」: save_path 是**目录**, 不能拿它去判链接。
        # !POSIX 目录 st_nlink 恒 >= 2(Linux CI 实测): 旧写法落到 names[0] 直接 IndexError;
        # Windows 目录 nlink=1 走不到那条分支, 于是本地全绿、CI 全红。
        if names:
            first_native = _native(save_path, names[0])
            try:
                st = os.lstat(utils.add_long_path_prefix_for_win(self._syscall(first_native)))
                tag = getattr(st, "st_reparse_tag", 0)
                if stat.S_ISLNK(st.st_mode) or tag:
                    tp_files = (names[0], )
                elif st.st_nlink > 1:
                    hl_files = (names[0], )
            except OSError:
                tp_dir_note = "代表文件不可读(远程/容器未映射?): 第三方链接与硬链接未识别"
        try:
            # 仅当内容根真实存在时才做别名解析比较: 不存在的路径 realpath 退化为
            # abspath(Windows 盘符大小写还会变), 拿它说「目录级链接」是误报
            if fa.exists(content_root) is True:
                resolved = fa.realpath_lexical(content_root)
                # !Windows 路径同一性**大小写不敏感**: realpath_lexical 出口带 normcase
                # (Windows 语义 = lowercase), 拿它与原始路径(含大写)做大小写**敏感**比较
                # 恒不等 —— 任何含大写字母的正常目录都会被误报成「目录级链接」(P7 真机
                # 首步即撞见: 恶女目录 285 字符全大写混合)。两侧同过 normcase 再比:
                # 比的是「真实差异」(真链接/换卷), 不是大小写。
                if os.path.normcase(utils.path_normalize(resolved)) != os.path.normcase(
                    utils.path_normalize(content_root)
                ):
                    tp_dir_note = (tp_dir_note + " " if tp_dir_note else "") + \
                        f"检测到目录级链接({content_root} -> {resolved}): 组判定按解析后路径并组(第三方链接三层之第二层, D11)"
        except Exception:  # noqa: BLE001 - 容器侧 realpath 词法退化, 无结论不加 note
            pass

        return GroupFacts(
            hashes=hashes,
            mover=mover.hash,
            name=mover.name,
            save_path=save_path,
            target=target,
            files=files,
            progresses=tuple(float(getattr(r, "progress", 0.0) or 0.0) for r in records),
            states=tuple(str(getattr(r, "state", "") or "") for r in records),
            content_root_exclusive=exclusive,
            misc_entries=tuple(misc),
            external_entries=tuple(external),
            qb_temp_entries=tuple(qb_temp),
            target_conflicts=tuple(conflicts),
            target_unknown=target_unknown,
            same_volume=same_vol,
            target_free=target_free,
            same_fs_proved=proved,
            capability_ok=verdict.supported,
            capability_reason=verdict.reason,
            file_link_kind=file_kind,
            file_link_error=file_err,
            dir_link_kind=dir_kind,
            dir_link_error=dir_err,
            jobs=self.active_jobs(),
            link_path_limit=alias_fs.WIN_MAX_PATH if utils.is_windows() else None,
            threshold=conf.alias_file_threshold,
            hard_max=conf.hard_max_links,
            third_party_link_files=tp_files,
            hardlink_files=hl_files,
            third_party_dir_note=tp_dir_note,
        )

    def _classify_entries(self, rest, save_path, content_root, hashes, store, client):
        """内容根多出的条目分类: (杂项, 组外种子文件)

        组外 = 同 save_path 的其它种子、且有文件落在该条目下(分集同目录场景, §8.1);
        其余(如散落的 .torrent) = 杂项。只做同 save_path 的比对, 不全局扫。
        """
        if not rest:
            return [], []
        own_hashes = set(hashes)
        src_norm = utils.path_normalize(save_path)
        cr_norm = utils.path_normalize(content_root)
        prefix = cr_norm[len(src_norm):].lstrip("/")  # 内容根相对 save_path 的目录段
        belongs = set()
        for h, rec in store.by_hash.items():
            if h in own_hashes:
                continue
            try:
                if utils.path_normalize(rec.save_path) != src_norm:
                    continue
                for f in self._file_map(rec, client):
                    tail = f[len(prefix):].lstrip("/") if prefix and f.startswith(prefix + "/") else f
                    top = tail.split("/", 1)[0]
                    if top in rest:
                        belongs.add(top)
            except Exception:  # noqa: BLE001 - 单条失败不影响其余分类
                continue
        external = [n for n in rest if n in belongs]
        misc = [n for n in rest if n not in belongs]
        return misc, external

    @staticmethod
    def _syscall(path: str) -> str:
        """逻辑路径 -> syscall 路径(容器映射; 未命中/无映射时原样返回)"""
        try:
            fa = file_access.get_file_access()
            return fa.map_to_container(path) or path
        except Exception:  # noqa: BLE001 - 映射查询失败按原路径(同卷/ free 判定随后自行降级)
            return path

    # ---------- P2 预检面二: 添加种子预检(§3.6.1, 只读) ----------

    def precheck_add(self, save_path: str, name: str) -> dict:
        """往某 save_path 添加种子前的落点预检(添加对话框提交前调用, 只读)

        落点 = save_path/内容根(种子名; 添加前无法知道子文件夹布局, 按名称一级判定)。
        三分流: ok(无影响) / confirm(弹「请求路径 -> 实际落点 -> 目标卷剩余」二次确认)。
        判定数据 = 活跃 job 的作用域登记 + 落点处的链接实况(alias_kind_of)。
        """
        save_path = str(save_path or "").strip()
        name = str(name or "").strip()
        if not save_path or not name:
            return {
                "save_path": save_path,
                "name": name,
                "requested_path": "",
                "actual_path": None,
                "volume_free": None,
                "cls": CLS_BLOCKED,
                "reasons": [{
                    "gate": "param",
                    "text": "save_path 与 name 均不能为空"
                }],
                "notes": [],
            }
        landing = _native(save_path, name)
        jobs = self.active_jobs()
        # 命中作用域时才需要目标卷剩余(确认框展示「实际落点所在卷还有多少空间」)
        scope_job = next((j for j in jobs if j.scope_hit(save_path, landing)), None)
        target_free = None
        if scope_job is not None:
            try:
                target_free = file_access.get_file_access().disk_usage(scope_job.dst).free
            except Exception:  # noqa: BLE001 - 读不到按「不可判定」展示, 不猜
                target_free = None
        kind = alias_fs.alias_kind_of(self._syscall(landing))
        link_target = alias_fs.alias_target(self._syscall(landing)) if kind else None
        result = evaluate_add(
            AddFacts(
                save_path=save_path,
                name=name,
                jobs=jobs,
                landing_is_link=kind is not None,
                landing_link_kind=kind,
                landing_link_target=link_target,
                target_free=target_free,
            )
        )
        logger.info(
            f"relocate | 添加预检 {name} @ {save_path}: {result['cls']}" +
            (f" -> {result.get('actual_path')}" if result.get("actual_path") else "")
        )
        return result

    # ---------- P2 预检面三: 能力面板(§3.8, 只读) ----------

    def capability_view(self) -> dict:
        """六项链接能力探测事实(alias_fs 单点) + 启用状态; 同卷证明按组预检随 notes 给出"""
        conf = self._live_conf()
        out = alias_fs.get_capability().as_dict()
        out["enabled"] = bool(getattr(conf, "enabled", False)) if conf is not None else False
        return out
