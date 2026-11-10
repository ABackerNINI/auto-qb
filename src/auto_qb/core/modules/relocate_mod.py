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
from dataclasses import replace
from types import MappingProxyType
from typing import Optional

from ...infra.clock import SYSTEM_CLOCK, Clock
from ..module import AppContext, BaseModule
from . import relocate_units as ru
from .relocate_units import RelocateJob
from .relocate_lifecycle import LifecycleMixin
from .relocate_plan import PlanMixin
from .relocate_exec import ExecMixin
from .relocate_probe import new_probe_salt

# 同机强探测(E1)结论的合法取值(计划 26-11-04-0055 §03.2); 其余一律按坏条目/未命中处理
_PROBE_STATUSES = ("passed", "failed")


class RelocateModule(LifecycleMixin, PlanMixin, ExecMixin, BaseModule):
    """整组迁移模块: relocate 段认领 + P2 只读预检引擎(执行体随 P3)

    三入口(均只读, 经 WEB 命令队列在主循环线程执行, 与写命令串行化):
    relocate_precheck(迁移) / precheck_add(添加种子) / capability_view(能力面板)。
    job 登记表 _jobs 是 P3 执行体落账(state.json relocate.jobs)前的内存形态:
    P2 无执行体故恒空, 但「未收尾拦截」闸门已按真实 job 判定(S10 语义在 P3/P7 前
    即可被单测注入验证)。
    """

    name = "relocate"

    def __init__(self, ctx: Optional[AppContext] = None, clock: Optional[Clock] = None) -> None:
        self._ctx: Optional[AppContext] = ctx
        # 取时注入(D8): Lifecycle/Exec 两 mixin 与本体的取时点共用; 缺省单点经模块属性现取(测试可换假钟)
        self._clock = SYSTEM_CLOCK if clock is None else clock
        self._conf = None  # 生效的 RelocateConfig(热重载换对象即更新)
        self._jobs: dict = {}  # job_id -> RelocateJob(P3 执行体写入; P2 恒空)
        # 本会话是否接管过 job 账(_load_jobs 恢复过 / register_job/_set_job 动过): stop()
        # 补写闸的依据 —— 未接管时内存空表不代表账空, _persist 整段重写会把 state 里的
        # 历史在途 job 清掉(优雅退出紧跟 ctx.state.save() 落盘, 清账即永久失账)。
        self._jobs_loaded = False
        self._rt: dict = {}  # job_id -> 运行期进度(采样式, 不落盘; 重启由 qB 现场恢复)
        self._qb_up_cache: Optional[tuple] = None  # (monotonic, up) 「qB 在?」探测缓存
        self._dry = False  # dry_run(启动期透传; 干跑不落盘不建链, 与全局口径一致)
        # WebUI 只读快照(plan 26-11-04-1042 P0-1): 只在主循环 job 变更路径发布, Web 构建期
        # 零遍历 _jobs; 初值 generation=0 / 空表 = 正常「无 job」态。
        self._snapshot = ru.RelocateSnapshot()
        # qB 标签镜像(P3, 只写不读): job_id -> 已推到的目标态(add/remove) + 失败退避时刻。
        # 重启后清空 = 非终态 job 的标签在恢复首轮由 _reconcile_pending_tags 补写。
        self._tag_applied: dict = {}
        self._tag_next_try: dict = {}
        self._tag_failures = 0

    def sections(self) -> tuple:
        # relocate 整段(bt_backup 已收编为 relocate.bt_backup, 计划 26-11-11-0259 S1)由本模块
        # 消费(预检部署闸 bt_backup_path_of 现读), 段认领完备守阵(P6)要求登记认领面
        return ("relocate", )

    def _state_jobs(self) -> dict:
        """state.json 的 relocate.jobs 容器(惰性创建; 上下文缺失返回空 dict 不炸)"""
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return {}
        return data.setdefault("relocate", {}).setdefault("jobs", {})

    def _state_probes(self) -> dict:
        """state.json 的 relocate.probes 容器(同机强探测缓存, 计划 26-11-04-0055 §03.2)

        形状: {指纹哈希: {"status": "passed"|"failed", "evidence": {...}, "at": <epoch秒>}}。
        仿 _state_jobs 的 setdefault 先例(惰性创建; 上下文缺失返回空 dict 不炸)。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return {}
        return data.setdefault("relocate", {}).setdefault("probes", {})

    def probe_get(self, fingerprint: str) -> Optional[dict]:
        """按连接身份指纹查探测缓存; 未命中(无条目/坏条目)返回 None, 不抛异常

        坏条目(非 dict / 缺字段 / status 非法)按未命中处理 —— 留在原地不删,
        由下一次 probe_put 覆盖; 返回条目深副本(调用方改不动缓存真身)。
        **只读不建箱**(P3 起 precheck 经它消费缓存 —— 预检承诺零副作用, state 深比对
        不变; 箱的惰性创建只属于写路径 probe_put/probe_drop)。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        relocate = data.get("relocate") if isinstance(data, dict) else None
        box = relocate.get("probes") if isinstance(relocate, dict) else None
        entry = box.get(fingerprint) if isinstance(box, dict) else None
        if not isinstance(entry, dict):
            return None
        if entry.get("status") not in _PROBE_STATUSES:
            return None
        evidence = entry.get("evidence")
        if not isinstance(evidence, dict):
            return None
        at = entry.get("at")
        if isinstance(at, bool) or not isinstance(at, (int, float)):
            return None
        return {"status": entry["status"], "evidence": dict(evidence), "at": at}

    def probe_put(self, fingerprint: str, status: str, evidence: dict) -> dict:
        """覆盖写一条探测结果(同指纹重探直接覆盖, 幂等); 返回写入的条目副本"""
        entry = {
            "status": status,
            "evidence": dict(evidence or {}),
            "at": int(self._clock.now()),
        }
        self._state_probes()[fingerprint] = entry
        return {"status": entry["status"], "evidence": dict(entry["evidence"]), "at": entry["at"]}

    def probe_drop(self, fingerprint: str) -> bool:
        """删单条指纹缓存(指纹变更失效/手动清缓存); 本就没有也返回 False, 幂等"""
        box = self._state_probes()
        return box.pop(fingerprint, None) is not None

    def probe_salt(self) -> str:
        """读指纹盐(只读面): state 无盐返回空串, 绝不在读路径生成/持久化

        预检零副作用契约(本文件头)要求读缓存面不写 state —— 盐的惰性生成只在写路径
        probe_salt_ensure。无盐计算的指纹与带盐缓存必不同键, 预检按未命中处理(执行闸
        会经 ensure 面补盐后正常命中/重探), 语义安全。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        relocate = data.get("relocate") if isinstance(data, dict) else None
        salt = relocate.get("probe_salt") if isinstance(relocate, dict) else None
        return salt if isinstance(salt, str) and salt else ""

    def probe_salt_ensure(self) -> str:
        """读/惰性生成并持久化指纹盐(写路径单点: 执行闸 _ensure_probe 消费)

        盐存 state relocate.probe_salt(与 relocate.probes 缓存同键族): 换盐 => 全部旧指纹
        键失效 => E1 缓存自然整体重探(语义不变, 生成单点见 relocate_probe.new_probe_salt)。
        生成新盐分支同时整箱清空 relocate.probes(面 B 补, R1#42): 该时刻箱内全部既有条目
        按构造必为旧键死条目 —— 含升级前遗留的无盐 SHA1 指纹(原爆破面, 不清则 state 泄露
        下仍可爆破), 且 probe_drop 无人调用孤儿键只累积不回收; 清空仅损失下次重探一次。
        state 缺失(上下文不全)返回空串不炸, 与 probe_get 的退化形态一致。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return ""
        relocate = data.setdefault("relocate", {})
        salt = relocate.get("probe_salt")
        if not isinstance(salt, str) or not salt:
            salt = new_probe_salt()
            relocate["probe_salt"] = salt
            probes = relocate.get("probes")
            if isinstance(probes, dict) and probes:
                probes.clear()
        return salt

    def _persist(self) -> None:
        """job 账写回 state(整段重写: 条数 = 组数, 极小; 周期落盘由 state 服务负责)"""
        box = self._state_jobs()
        if not isinstance(box, dict):
            return
        box.clear()
        for jid, job in self._jobs.items():
            box[jid] = ru.job_to_dict(job)

    def _publish_snapshot(self) -> None:
        """发布不可变 job 快照(主循环写线程单点; Web 只读引用)

        内容相等时不换代也不置脏 —— _sync_relocating 之后的重复发布不该让 Web 每轮重建。
        内容变化时置 full 脏: 迁移标注会影响组行内嵌成员数组与组级聚合, 局部桶无法覆盖
        未显式登记的组键, 用 full 保证整份视图与快照同代。
        """
        jobs = tuple(MappingProxyType(d) for d in self.jobs_view())
        if jobs == self._snapshot.jobs:
            return
        by_hash: dict = {}
        for job in jobs:
            for h in job.get("hashes") or ():
                prev = by_hash.get(h)
                if prev is None or ru.job_rank(job) > ru.job_rank(prev):
                    by_hash[h] = job
        self._snapshot = ru.RelocateSnapshot(
            generation=self._snapshot.generation + 1,
            jobs=jobs,
            by_hash=MappingProxyType(by_hash),
        )
        web = getattr(self._ctx, "web", None) if self._ctx is not None else None
        mark_dirty = getattr(web, "mark_dirty", None)
        if callable(mark_dirty):
            mark_dirty(full=True, reason="relocate_jobs")

    def _load_jobs(self) -> int:
        """启动/热重载时从 state 恢复 job 账; 非终态的重挂 relocating 登记(抑制缺文件误判)"""
        self._jobs_loaded = True  # 本会话已接管 job 账(stop() 补写闸的依据, 见 __init__ 注)
        box = self._state_jobs()
        n = 0
        for jid, d in list(box.items()):
            job = ru.job_from_dict(d)
            if job is None:
                continue
            self._jobs[jid] = job
            # 恢复运行期进度: 已建链接不重建; 要不要补发 setLocation 由 _recover 按 qB 现场
            # 定夺(不能一律 False —— 账先落、指令后发, 两步之间崩溃的 job 会永远等不到搬迁)
            self._rt[jid] = {
                "issue": False,
                "started": self._clock.monotonic(),
                "sample_ts": 0.0,
                "last_size": -1,
                "stall_since": 0.0,
                "link_pos": len(job.alias_paths),
                "links": list(job.alias_paths),
                "recover": job.phase == ru.PHASE_MOVING,  # MOVING 现场待判(_recover 一个 tick 判一次)
                # 启动对账待判(计划 26-11-10-0721 §03.4): failed 账在首轮 qB 连接成功的
                # tick 按物理现状重推相位一次(运行期 flag, 零新持久状态; 消费即清不重判)
                "reconcile": job.phase == ru.PHASE_FAILED,
            }
            n += 1
        self._sync_relocating()
        self._publish_snapshot()
        return n

    def _sync_relocating(self) -> None:
        """relocating 登记 = 非终态 job 的成员并集(P4: 缺文件扫描与跳检闸门据此让路)

        S4b(D16 删种拦截)追加: 活动别名根登记 store.relocating_alias_roots
        ({src: job_id}) —— QbApi.torrents_delete 的拦截面据此判「save_path 位于活动
        别名之下」, 随本单点(每次 job 变更整表重算)自动增删, 终态即撤拦。
        """
        store = getattr(self._ctx, "store", None) if self._ctx is not None else None
        if store is None:
            return
        reg = getattr(store, "relocating_hashes", None)
        if reg is None:  # 老 store 替身无该字段: 自建一份, 不打扰既有测试形状
            reg = set()
            store.relocating_hashes = reg
        reg.clear()
        roots = getattr(store, "relocating_alias_roots", None)
        if roots is None:  # 同上: 老 store 替身按需自建(QbApi 读侧 getattr 缺省不拦)
            roots = {}
            store.relocating_alias_roots = roots
        roots.clear()
        for job in self.active_jobs():
            reg.update(job.hashes)
            reg.update(job.resume_hashes)
        for src, job_id in ru.alias_roots_of(self.active_jobs()):
            roots[src] = job_id

    def _set_job(self, job: RelocateJob) -> RelocateJob:
        """登记相位推进后的 job(单点: 落内存 + 刷登记 + 写 state + 可选 qB 标签镜像)

        标签镜像在 state 落盘之后做: state 是唯一事实源, 镜像失败(超时/不支持/权限)
        只告警计数, 绝不回滚相位或影响收尾判定。
        """
        job = replace(job, updated_at=self._clock.now())
        self._jobs[job.job_id] = job
        self._jobs_loaded = True
        self._sync_relocating()
        self._persist()
        self._publish_snapshot()
        self._sync_pending_tag(job)
        # 标签镜像可能改写 tag_on(_note_tag_state); 返回账上现值, 免得调用方拿旧对象继续
        # 推进相位时把「曾加标签」这一位覆盖回 False(终态就会漏摘标签)。
        return self._jobs.get(job.job_id, job)
