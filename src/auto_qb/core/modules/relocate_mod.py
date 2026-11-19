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

依赖方向: 本模块 -> infra(alias_fs/file_access/relocate_journal) + torrents + 兄弟模块**零**
import(需要别人能力经 ctx); 决策纯函数在 relocate_units(不触盘), 本文件只收集事实。
"""
import copy
import os
import shutil
import time
from dataclasses import replace
from types import MappingProxyType
from typing import Any, Optional

from ...config.models import bt_backup_path_of
from ...infra import relocate_journal
from ...infra.clock import SYSTEM_CLOCK, Clock
from ..module import AppContext, BaseModule
from . import relocate_units as ru
from .relocate_units import RelocateJob
from .relocate_common import logger
from .relocate_lifecycle import LifecycleMixin
from .relocate_plan import PlanMixin
from .relocate_exec import ExecMixin, arm_members_of
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
        # 恢复确认(issue 26-11-14-1744 (1)+(2)): 跨拍退避时刻表 + 失败/穷尽计数 + 穷尽告警
        # 的开账回合去重(每开账回合一笔; 出口重开账有意重新武装 —— 防新回合的穷尽被
        # 旧去重吞掉; 重启清空 = 在途余量重启后再挂一次告警, 挂账本身随 job 账走 state
        # 持久, 重启续跑不丢)。仿 _tag_next_try/_tag_failures 形态。
        self._resume_next_try: dict = {}
        self._resume_failures = 0
        self._resume_exhausted_warned: set = set()
        # 已删成员闭账(issue 26-11-15-0345): (job_id, hash) -> 连续不在 store 的对账拍数,
        # 达 _DELETED_CONFIRM_TICKS 判真删除并闭账。键带 job_id: 同一 hash 可属不同 job,
        # 各自独立计数。内存态不入 state_file —— 重启清空 = 确认从头数(保守方向: 真删除
        # 至多多挂 N 拍账, 不引入误闭面); 与 _resume_next_try 同区同形态。
        self._deleted_streak: dict = {}
        # 热启用被拒标志(R2-1, S1b 旧账迁移 D8/R1): apply 捕获迁移 RuntimeError 后置位,
        # _live_conf 据此把全部执行入口按禁用收口 —— 内核 apply_new_config 在调 apply 前
        # 已换 ctx.config 对象, rejected 回执无人回滚, 不闸则相位机/执行入口仍按 enabled
        # True 放行(在途 legacy 账未恢复 = 未收尾拦截/让路失明; 用户再发起迁移会
        # _set_job 置 _jobs_loaded -> stop() 整段重写清掉 legacy 账)。清位 = 下次成功
        # _load_jobs(_load_jobs 尾部)或重启; 内存态不入 state_file。
        self._hot_enable_rejected = False

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

    # ---------- 探测意图 FIFO(relocate.probe_pending, S1 异步化基础设施 D6/D7) ----------
    # 计划 26-11-10-2350 §03/§06: 探测移出主循环后, 迁移意图以 {fingerprint, hashes, src,
    # dst, origin, ts} 入 state 持久(D7), verdict 消费后按意图重放 relocate_execute 全新鲜
    # (D6 只存意图不存快照)。读写单点在本组方法 + _state_probe_pending 访问器, 不允许第二份
    # 路径; 全部只在主循环线程面调用(黄金法则#5: 探测线程零 state 写)。条目极小零资源,
    # 不设上限(计划 §07: 故障窗口膨胀交 FIFO 恢复后自然清空)。超龄兜底常量在
    # relocate_probe.PROBE_PENDING_MAX_AGE_S(T3 启动清扫接线)。

    def _state_probe_pending(self) -> list:
        """state.json 的 relocate.probe_pending 容器(探测意图 FIFO 队列)

        仿 _state_probes 的 setdefault 先例(惰性物化; 上下文缺失返回空 list 不炸): 补键类
        新容器不走版本链、零迁移 —— 旧 state 无此键, 首次访问物化空 list(不做 state 版本
        bump, 与 relocate.probes 同口径)。坏箱(非 list, 外部手改/漂移)原位修复为空 list:
        意图队列必须可写, 坏箱体留着会让 append 当场炸 —— 与 probe_get 的「坏条目留原地」
        不同, 那是值级容错(覆盖写可修复), 这是箱体级(修复是唯一出路)。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return []
        relocate = data.setdefault("relocate", {})
        box = relocate.get("probe_pending")
        if not isinstance(box, list):
            box = []
            relocate["probe_pending"] = box
        return box

    @staticmethod
    def _probe_hashes_as_list(value: Any) -> list:
        """存储值 -> hash 列表(值级容错单点): str 按 [该串] 单 hash、非可迭代按空 list

        条目 hashes 真身被外部改坏(手改/漂移)时, str 值逐字符拆分、非可迭代值抛 TypeError
        都会从读/合并返回面炸出去 —— 与容器自称的坏形容错面不一致。容错口径与 append 的
        isinstance 分支对齐(字符串按单 hash), 其余可迭代原样拷贝(副本面忠实不筛不重排)。
        """
        if isinstance(value, str):
            return [value]
        try:
            return list(value or [])
        except TypeError:
            return []

    def _probe_pending_copy(self, entry: dict) -> dict:
        """条目副本(hashes 列表单层深拷) —— 调用方改不动队列真身(与 probe_get 副本口径一致)"""
        copied = dict(entry)
        copied["hashes"] = self._probe_hashes_as_list(entry.get("hashes"))
        return copied

    def probe_pending_append(self, fingerprint: str, hashes: Any, src: str, dst: str, origin: str) -> dict:
        """入队一条迁移意图(队尾; 返回条目副本)

        条目 {fingerprint, hashes, src, dst, origin, ts}: 只存意图不存快照(D6); hashes 去重
        保序(字符串按单 hash 容错, 空白 hash 丢弃); origin 是触发来源标记("web"/"rule" 形态,
        容器只透传); ts = 入队 epoch 秒(probe_put.at 同钟面, 超龄兜底判据)。
        """
        if isinstance(hashes, str):  # 字符串按单 hash 容错(逐字符拆分是真实 footgun)
            hashes = [hashes]
        entry = {
            "fingerprint": str(fingerprint or ""),
            "hashes": [str(h) for h in dict.fromkeys(hashes or ()) if str(h or "").strip()],
            "src": str(src or ""),
            "dst": str(dst or ""),
            "origin": str(origin or ""),
            "ts": int(self._clock.now()),
        }
        self._state_probe_pending().append(entry)
        return self._probe_pending_copy(entry)

    def probe_pending_list(self) -> tuple:
        """FIFO 顺序返回全部条目副本(坏条目跳过留原地, 与 probe_get 坏形按未命中同口径)"""
        return tuple(self._probe_pending_copy(e) for e in self._state_probe_pending() if isinstance(e, dict))

    def probe_pending_merge_hashes(self, fingerprint: str, hashes: Any) -> bool:
        """同指纹合并: 把 hashes 去重并入既有条目(保 FIFO 位不动); 无此指纹返回 False

        合并语义 = 计划 §03: 在飞/等位的同指纹请求把 hashes 并进已有 pending 条目(去重),
        绝不重复入队(否则重放会重复发起)。真身在队列条目上原地更新(主循环单写线程面)。
        """
        fp = str(fingerprint or "")
        if isinstance(hashes, str):
            hashes = [hashes]
        incoming = [str(h) for h in (hashes or ()) if str(h or "").strip()]
        for entry in self._state_probe_pending():
            if isinstance(entry, dict) and entry.get("fingerprint") == fp:
                merged = [
                    str(h) for h in dict.fromkeys((*self._probe_hashes_as_list(entry.get("hashes")), *incoming))
                    if str(h or "").strip()
                ]
                entry["hashes"] = merged
                return True
        return False

    def probe_pending_pop(self) -> Optional[dict]:
        """弹出队首条目(FIFO 单出口, T3 重放消费面): 队首坏条目(非 dict)丢弃继续, 弹空返回 None"""
        box = self._state_probe_pending()
        while box:
            entry = box.pop(0)
            if isinstance(entry, dict):
                return self._probe_pending_copy(entry)
        return None

    def probe_pending_drop(self, fingerprint: str) -> bool:
        """按指纹摘除一条 pending(T3 清条目面); 本就没有返回 False, 幂等

        同指纹在队内至多一条(单飞 + 同指纹合并的不变量), 摘首个命中即语义完整。
        """
        fp = str(fingerprint or "")
        box = self._state_probe_pending()
        for i, entry in enumerate(box):
            if isinstance(entry, dict) and entry.get("fingerprint") == fp:
                del box[i]
                return True
        return False

    def probe_pending_clear(self) -> int:
        """整箱清空(T3 超龄清扫面), 返回清掉的条目数(含坏条目, 清扫不留残骸)"""
        box = self._state_probe_pending()
        n = len(box)
        box.clear()
        return n

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

        内容相等时不换代也不置脏 —— 同一拍内的重复发布不该让 Web 每轮重建。
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

    # ---------- S1b 旧账迁移器(D8 + R1, 计划 26-11-15-2340 §03.5/§07-R1) ----------

    def _migrate_legacy_accounts(self) -> None:
        """重构版上线时自动迁移存量账(D8): 一条不丢, 失败 fail-fast 绝不带损入新模型

        触发与幂等: state.json 的 relocate.model_version 标记(ru.MODEL_VERSION; 缺失/0 =
        旧账), 两个接管点(lifecycle start / 热启用 apply)都经 _load_jobs 进入本方法。
        无 relocate 箱 / 无 jobs 箱 / 无 legacy 账 = 直接盖章跳过(零备份零写盘面, 只动
        内存 state.data, 落盘随 state 服务周期)。

        迁移内容(映射规则, 计划 26-11-15-2340 §03.5/§07-R1):
        - 识别面 = plan.superseded_from 在场的账(改道机器唯一落账证据; 该字段写入面已随
          三方法物理删除, 新账永不携带): 统一转为 superseded 只读历史记录(phase=superseded,
          reason=migrated_superseded), 原始落点(superseded_from)还原进账面 dst —— 记录的
          真实语义是「它自己把 A 搬到了 B」, 改道后的 dst 是机器翻转值不留;
        - 接管关系: 找到继任账(碰同组且改道后 dst == 继任 dst; 非终态优先, 同分取
          updated_at 最新)则把移交条目 {job_id/src/dst(原始落点)/scope/alias_kind/
          alias_paths/link_kind} 归集到继任链的**活着顶端**(展平, 镜像 _handover_predecessors
          的祖父辈归集 —— 旧改道链的别名已被旧机器统一改指链顶, 条目归集顶端才喂得进
          继任的删链门/继承面), 前任 hash 并入继任 plan.extra_members(改写义务随链归集);
          继任已武装(armed/rewritten: 旧机器时代 _arm 已落盘 spec, 不含前任成员/
          extra_srcs, armed 不重走 _arm)时同步重写继任 spec —— 不重写则前任未完成改写
          失主, 继任收官删移交别名后成员断粮(见 _migrate_rewrite_successor_spec);
          无继任 = 孤儿改道前任, 单独转 superseded 记录(alias_paths 保留作账面证据);
        - journal 投影: 被转换账的 journal 若非终态, 同步翻 superseded(+superseded_by=链顶,
          daemon 即时退休, 与 _handover_predecessors 收官同协议); 已终态的 journal 不动;
        - 在途账(无 superseded_from)零触碰: 相位语义原样, 由既有启动对账(_startup_reconcile)
          与 _recover 接管跑完 —— 迁移器不改变任何在途相位。

        盖章与转换的落盘时机(真机验收缺陷1, 2026-11-17): 本方法只动内存 state.data, 落盘
        单点在 _load_jobs 尾部的接管面写穿 —— 接管面突变即刻落盘, 不等「state 服务周期刷盘」
        (内核曾把 run() 的 _reload_state 挂在 start_all 之后, 刷盘前的盖章/转换会被那次
        整体替换静默丢弃 —— 真机实测 relocate.model_version 永不落盘; 该丢弃窗口已随
        issue 26-11-17-0214 在内核面消除, 写穿保留为「接管即持久」语义面, 见 _load_jobs
        尾部注释)。

        R1 备份/回滚: 有账可迁时先备份 state(+.bak)与 relocate 目录到
        <data_dir>/relocate-migration-backup/<时间戳>/; 备份/转换/journal 落盘任一步异常 =
        回滚(state 覆写还原 + relocate 目录镜像还原 + **内存 jobs_box 还原迁移前快照**;
        备份阶段失败 = 无转换写面, 仅内存还原, 盘面不动)并抛 RuntimeError —— start_all
        无捕获穿透(fail-fast 契约)拦截进程启动; 热启用路径由 apply 捕获转「拒绝本次
        热重载」回执, 并置模块级被拒标志(_live_conf 把全部执行入口按禁用收口直至下次
        成功 _load_jobs 或重启, R2-1; 主循环不带半迁移态继续)。
        """
        st = getattr(self._ctx, "state", None) if self._ctx is not None else None
        data = getattr(st, "data", None)
        if not isinstance(data, dict):
            return
        relocate_box = data.get("relocate")
        if not isinstance(relocate_box, dict):
            return
        try:
            marked = int(relocate_box.get("model_version") or 0)
        except (TypeError, ValueError):
            marked = 0
        if marked >= ru.MODEL_VERSION:
            return
        jobs_box = relocate_box.get("jobs")
        if not isinstance(jobs_box, dict):
            relocate_box["model_version"] = ru.MODEL_VERSION  # 空箱直接盖章(无账可迁)
            return
        legacy_ids = [
            jid for jid, d in jobs_box.items()
            if isinstance(d, dict) and isinstance(d.get("plan"), dict) and d["plan"].get("superseded_from")
        ]
        if not legacy_ids:
            relocate_box["model_version"] = ru.MODEL_VERSION  # 无 legacy 账, 只补版本标记
            return
        data_dir = self._data_dir()
        snapshot = copy.deepcopy(jobs_box)  # 内存快照: 回滚时还原内存(热启用吞异常面, R1)
        backup_dir = None
        try:
            # 备份也在 try 内(minor-R2-2): os.makedirs/shutil 的 OSError 裸抛不经回滚-拒绝
            # 文案会被 apply 的 except RuntimeError 漏掉 —— 备份此刻尚无任何转换写, 统一包成
            # RuntimeError(backup_dir=None = 无转换写面, 回滚只还原内存快照)
            backup_dir = self._migration_backup(data_dir)
            converted = self._migrate_convert(jobs_box, legacy_ids)
        except Exception as e:  # noqa: BLE001 - fail-fast: 回滚后穿透拦截启动
            self._migration_rollback(data_dir, backup_dir, jobs_box, snapshot)
            head = f"已回滚备份 {backup_dir}" if backup_dir else "备份未完成(无转换写面, 仅还原内存快照; 现场留人工核处)"
            raise RuntimeError(f"relocate 旧账迁移失败({e}); {head}, 启动拦截 —— "
                               "绝不带损入单活模型, 请检查备份后人工核处") from e
        relocate_box["model_version"] = ru.MODEL_VERSION
        logger.warning(
            f"relocate | 旧账迁移完成: {len(legacy_ids)} 个改道机器前任转 superseded 历史记录"
            f"(接管关系归集 {converted} 条), 备份在 {backup_dir}(model_version={ru.MODEL_VERSION})"
        )

    def _migration_successor_of(self, jobs_box: dict, jid: str, d: dict) -> str:
        """改道前任的继任账 id(碰同组且改道后 dst 相同; 非终态优先, 同分取 updated_at 最新)

        镜像旧机器 _predecessors_of 的判定方向(pred.dst == src 换算成继任侧 dst == 前任
        改道后 dst)。找不到 = ""(孤儿改道前任, 单独转历史记录)。
        """
        hashes = {str(h) for h in (d.get("hashes") or ()) if h}
        want = ru._norm(str(d.get("dst") or ""), fold_case=False)
        best, best_key = "", None
        for oid, od in jobs_box.items():
            if oid == jid or not isinstance(od, dict):
                continue
            if not (hashes & {str(h) for h in (od.get("hashes") or ()) if h}):
                continue
            if ru._norm(str(od.get("dst") or ""), fold_case=False) != want:
                continue
            terminal = str(od.get("phase") or "") in ru.TERMINAL_PHASES
            key = (not terminal, float(od.get("updated_at") or 0.0))
            if best_key is None or key > best_key:
                best, best_key = oid, key
        return best

    def _migrate_convert(self, jobs_box: dict, legacy_ids: list) -> int:
        """转换全部 legacy 账(账面字典手术 + journal 投影 + 继任 spec 重写); 返回归集的移交条目数

        任一步异常向上抛(调用方回滚备份/内存快照后 fail-fast)。条目归集目标 = 继任链的
        活着顶端: 继任本身也是改道前任时沿链上溯; 环形继任 = 无有效顶端, 按孤儿收口
        (条目无处归集留在前任账上, 绝不自归集)。
        """
        succ = {jid: self._migration_successor_of(jobs_box, jid, jobs_box[jid]) for jid in legacy_ids}
        target_of = {}
        for jid in legacy_ids:
            seen = {jid}
            cur = succ.get(jid) or ""
            while cur in legacy_ids and cur not in seen:
                seen.add(cur)
                cur = succ.get(cur) or ""
            # 环形收口: 走回已见 id(含自环)= 无有效顶端 -> 按孤儿处理("" = 条目不归集)
            target_of[jid] = "" if cur in seen else cur
        entries_merged = 0
        spec_needs = {}  # 继任 id -> {"hashes": [前任成员..], "srcs": [前任 src 根..]}(spec 重写面)
        for jid in legacy_ids:
            d = jobs_box[jid]
            plan = dict(d.get("plan") or {})
            old_dst = str(plan.get("superseded_from") or "")
            entry = {
                "job_id": jid,
                "src": str(d.get("src") or ""),
                # 条目 dst = 改指收敛前链接的真实指向 = 原始落点(改道翻转值不留)
                "dst": old_dst or str(d.get("dst") or ""),
                "scope": str(d.get("scope") or ""),
                "alias_kind": str(d.get("alias_kind") or ""),
                "alias_paths": [str(p) for p in (d.get("alias_paths") or ()) if str(p or "").strip()],
                "link_kind": str(plan.get("link_kind") or ""),
            }
            nd = dict(d)
            plan.pop("superseded_from", None)
            # 原始落点还原进账面 dst(统一规则, 孤儿/有继任同款): 记录的真实语义是
            # 「它自己把 src 搬到了 old_dst」, 改道机器翻转的 dst 不留
            if old_dst:
                nd["dst"] = old_dst
            target = target_of.get(jid) or ""
            if target:
                td = dict(jobs_box.get(target) or {})
                tplan = dict(td.get("plan") or {})
                inherited = [e for e in (tplan.get("inherited") or []) if isinstance(e, dict)]
                if not any(e.get("job_id") == jid for e in inherited):
                    inherited.append(entry)
                else:  # 同 id 已在(半程崩溃后的重跑): 原位替换为本次归集值, 幂等
                    inherited = [entry if e.get("job_id") == jid else e for e in inherited]
                entries_merged += 1
                tplan["inherited"] = inherited
                # 前任成员改写义务随链归集(镜像 _handover_predecessors 的 extra_members 并入)
                own = {str(h) for h in (td.get("hashes") or ())}
                extras = [
                    str(h) for h in dict.fromkeys((*(tplan.get("extra_members") or ()), *(d.get("hashes") or ())))
                    if str(h) and str(h) not in own
                ]
                if extras:
                    tplan["extra_members"] = extras
                # 前任自己的移交条目一并上提(展平归集, S1a 同款; 前任账不再持有)
                for sub in (plan.get("inherited") or []):
                    if isinstance(sub, dict) and sub.get("job_id"):
                        sub = dict(sub)
                        if not any(e.get("job_id") == sub["job_id"] for e in inherited):
                            inherited.append(sub)
                            tplan["inherited"] = inherited
                plan.pop("inherited", None)
                td["plan"] = tplan
                jobs_box[target] = td
                need = spec_needs.setdefault(target, {"hashes": [], "srcs": []})
                need["hashes"].extend(str(h) for h in (d.get("hashes") or ()) if str(h))
                if entry["src"]:
                    need["srcs"].append(entry["src"])
            nd["plan"] = plan
            nd["phase"] = ru.PHASE_SUPERSEDED
            nd["reason"] = "migrated_superseded"
            jobs_box[jid] = nd
            self._migrate_journal_flip(jid, target)
        # 继任 spec 重写(全部前任转换完之后按目标去重执行一次; major-1 断粮洞)
        for target, need in spec_needs.items():
            self._migrate_rewrite_successor_spec(target, jobs_box.get(target) or {}, need)
        return entries_merged

    def _migrate_rewrite_successor_spec(self, job_id: str, td: dict, need: dict) -> None:
        """已武装继任的 spec 同步重写(major-1 断粮洞, 评审轮 2 修)

        继任 armed/rewritten 时旧机器时代的 _arm 已落盘 spec(members 不含前任成员、无
        extra_srcs), 而 armed 不重走 _arm —— 迁移把前任 journal 翻 superseded 后, daemon
        按前任 spec 的改写驱动面消失, 归集进 plan.extra_members 的改写义务对 daemon 失主:
        继任收官(删移交别名)后未完成改写的成员断粮。修法: 按 _write_arm_spec 同形状重写
        继任 spec(members 并入前任成员、extra_srcs 取移交条目 src 根), 依据 daemon
        「窗口内逐成员现读 spec」契约(recycle_daemon 窗口段注释)支持窗口中段换账。
        - 只处理收尾窗继任(phase ∈ FINALIZE_WINDOW_PHASES): pre-arm 继任无 spec, 后续
          _arm 按已归集的 plan 落新 spec 自然覆盖; 终态继任 spec 惰性(journal 终态,
          daemon 不认领), 不需要。
        - spec 缺失/残缺跳过(与 daemon 残缺 spec 跳过同口径, 不猜不建);
        - 新成员经 arm_members_of 补双 hash 形态(bt_backup 取不到时 hash_v2 留空, 与
          arm 侧同一容错); 写盘经 write_spec 原子面, 盘错误上抛(调用方回滚)。
        """
        if str(td.get("phase") or "") not in ru.FINALIZE_WINDOW_PHASES:
            return
        data_dir = self._data_dir()
        spec = relocate_journal.read_spec(data_dir, job_id)
        if not isinstance(spec, dict):
            return
        backup = bt_backup_path_of(getattr(self._ctx, "config", None))
        members = [m for m in (spec.get("members") or ()) if isinstance(m, dict)]
        known = {relocate_journal.member_key(m) for m in members if relocate_journal.member_key(m)}
        added = False
        for h in dict.fromkeys(need.get("hashes") or ()):
            h = str(h or "").strip()
            if not h or h in known:
                continue
            for m in arm_members_of([h], backup):
                if relocate_journal.member_key(m) and relocate_journal.member_key(m) not in known:
                    members.append(m)
                    known.add(relocate_journal.member_key(m))
                    added = True
        if added:
            spec["members"] = members
        srcs = [
            s
            for s in dict.fromkeys((*(spec.get("extra_srcs") or ()), *(need.get("srcs") or ()))) if str(s or "").strip()
        ]
        own_src = ru._norm(str(spec.get("src") or ""), fold_case=False)
        srcs = [s for s in srcs if ru._norm(str(s), fold_case=False) != own_src]
        if srcs and srcs != list(spec.get("extra_srcs") or ()):
            spec["extra_srcs"] = srcs
            added = True
        if added:
            relocate_journal.write_spec(data_dir, job_id, spec)
            logger.warning(
                f"relocate | 旧账迁移: 继任 job {job_id} 的 arm spec 已重写"
                f"(members 并入前任成员, extra_srcs={srcs}) —— 前任未完成改写由本 spec 承载"
            )

    def _migrate_journal_flip(self, job_id: str, successor_id: str) -> None:
        """被转换账的 journal 投影翻 superseded(非终态才写; 已终态/无 journal 不动)

        与 _handover_predecessors 收官同协议: daemon 按 STOP_PHASES 即时退休, 前任 spec
        不再驱动改写。拒写分支不可达: 迁移写的是 superseded 终相位, 前向合并只拒
        「非终态覆盖终态」; 盘错误经 atomic_write 上抛(调用方回滚备份)—— 投影翻不动 =
        daemon 会继续按旧 spec 改写, 不算迁移成功, 绝不带损入新模型。
        """
        data_dir = self._data_dir()
        body = relocate_journal.read_journal(data_dir, job_id)
        if body is None or str(body.get("phase") or "") in relocate_journal.STOP_PHASES:
            return
        payload = {
            **body,
            "phase": ru.PHASE_SUPERSEDED,
            "ts": self._clock.now(),
        }
        if successor_id:
            payload["superseded_by"] = successor_id
        relocate_journal.write_journal(data_dir, job_id, payload)

    def _migration_backup(self, data_dir: str) -> str:
        """迁移前备份: state(+.bak) 与 relocate 目录 -> <data_dir>/relocate-migration-backup/<ts>

        同秒重试(热启用被拒后立即重试等形态)的目录相撞 = copytree 目标已存在会炸 ->
        时间戳带序号后缀保证目录恒新开(既有备份目录绝不复用/覆盖, 取证面原样)。
        """
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self._clock.now()))
        backup_dir = os.path.join(data_dir, "relocate-migration-backup", stamp)
        seq = 0
        while os.path.isdir(backup_dir):
            seq += 1
            backup_dir = os.path.join(data_dir, "relocate-migration-backup", f"{stamp}-{seq}")
        os.makedirs(backup_dir)
        state_file = str(getattr(getattr(self._ctx, "state", None), "state_file", "") or "")
        for src in (state_file, state_file + ".bak"):
            if src and os.path.exists(src):
                shutil.copy2(src, os.path.join(backup_dir, os.path.basename(src)))
        journal_dir = relocate_journal.relocate_dir(data_dir)
        if os.path.isdir(journal_dir):
            shutil.copytree(journal_dir, os.path.join(backup_dir, "relocate"))
        return backup_dir

    def _migration_rollback(
        self,
        data_dir: str,
        backup_dir: Optional[str],
        jobs_box: Optional[dict] = None,
        snapshot: Optional[dict] = None
    ) -> None:
        """迁移失败回滚: 内存 jobs_box 还原快照 + state 覆写还原 + relocate 目录镜像还原

        内存还原放最前(纯内存操作必成; 盘面回滚失败时内存也不带半迁移态)。热启用路径
        (apply)吞掉 RuntimeError 继续主循环, 回滚只还原磁盘不还原内存的话, maybe_flush
        到期无条件 save 会把半迁移态覆盖回滚后的盘面(major-2 分叉洞)—— 快照还原封该口。
        backup_dir=None = 备份阶段失败(minor-R2-2): 尚无任何转换写面, 只还原内存快照,
        盘面原样(不碰 relocate 目录 —— 部分备份目录绝不冒充还原源, 不足的镜像会被误删)。
        """
        try:
            if jobs_box is not None and snapshot is not None:
                jobs_box.clear()
                jobs_box.update(copy.deepcopy(snapshot))
                logger.warning("relocate | 旧账迁移失败: 内存 jobs_box 已还原迁移前快照")
            if not backup_dir:
                logger.warning(f"relocate | 旧账迁移失败于备份阶段(无转换写; 现场可能留有未完成的备份目录, "
                               f"人工核处: {data_dir})")
                return
            state_file = str(getattr(getattr(self._ctx, "state", None), "state_file", "") or "")
            if state_file:
                for name, dst in (
                    (os.path.basename(state_file), state_file),
                    (os.path.basename(state_file) + ".bak", state_file + ".bak"),
                ):
                    src = os.path.join(backup_dir, name)
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
                    elif os.path.exists(dst):
                        # 备份缺该文件 = 迁移前也不存在(迁移窗口新产物): 撤走还原
                        os.remove(dst)
            journal_dir = relocate_journal.relocate_dir(data_dir)
            src_dir = os.path.join(backup_dir, "relocate")
            if os.path.isdir(src_dir):
                if os.path.isdir(journal_dir):
                    shutil.rmtree(journal_dir)
                shutil.copytree(src_dir, journal_dir)
            elif os.path.isdir(journal_dir):
                # 备份时无 relocate 目录 = 现目录全部内容都是迁移窗口产物: 整目录撤走
                shutil.rmtree(journal_dir)
            logger.warning(f"relocate | 旧账迁移失败, 已回滚备份原样还原: {backup_dir}")
        except Exception as e:  # noqa: BLE001 - 回滚自身失败也要如实暴露(盘/权限)
            logger.error(f"relocate | 旧账迁移回滚失败({e}) —— 备份 {backup_dir} 请人工核处, 不带损继续")

    def _load_jobs(self) -> int:
        """启动/热重载时从 state 恢复 job 账; 入口先跑旧账迁移器(S1b D8, 见 _migrate_legacy_accounts);
        账灌回内存即恢复让路/拦截面 —— relocating/resuming/别名根(S5 起)都是派生查询,
        派生即最新, 不再有「重建登记」挂点(issue 26-11-15-0441 的让路窗口滞后窗结构性消失)。
        启动对账回写(评审 minor-6): state 盒按 state 服务周期刷盘而 journal 即时落盘 ——
        journal 写完终相位、state 刷前硬崩的窗口, 重启按陈旧 state 恢复前段相位而 journal
        已退休(daemon 不再认领)= 永久悬挂; journal 相位是收尾账的跨进程投影(I3), 终相位
        回写 = 按投影收敛且由主循环落笔(「终态只有主循环能写」不破), adopted failed 交
        既有启动对账重判(reconcile flag), superseded/done/cancelled 直接收敛为终态。
        采纳带生命周期锚定(评审 major-R2-1): 仅「journal ts 可解析且 >= job.created_at」
        的本世在途账才回写 —— 同键重发后上一世的终相位 journal 可能仍在盘上(_arm 前不清),
        无锚采纳会把在途迁移误终态化; 残留/锚定不上的一律搁置, 留给 _arm 侧既有清理口。"""
        # S1b 旧账迁移器(D8/R1): 重构版首次接管存量账时自动迁移(改道机器退役字段 -> 单活
        # 模型表示), 失败 fail-fast 启动拦截 + 回滚备份。dry-run 不动手(与 sweep 同判),
        # 留给下一次真启动迁移。两个调用点(lifecycle start 与热启用 apply)都经本方法进入,
        # 迁移无需另挂。
        if not self._dry_run():
            self._migrate_legacy_accounts()
        self._jobs_loaded = True  # 本会话已接管 job 账(stop() 补写闸的依据, 见 __init__ 注)
        box = self._state_jobs()
        n = 0
        reconciled = 0
        for jid, d in list(box.items()):
            job = ru.job_from_dict(d)
            if job is None:
                continue
            journal = relocate_journal.read_journal(self._data_dir(), jid) or {}
            j_phase = str(journal.get("phase") or "")
            if not job.is_terminal and j_phase in relocate_journal.STOP_PHASES:
                # 生命周期锚定(评审 major-R2-1): job_id = sha1(mover|src|dst) 同键复用 ——
                # 同键重发的新生命周期在前段相位(moving/watching/moved)全程, 盘上可能躺着
                # 上一世的终相位 journal(清理唯一入口 _reset_stale_terminal_journal 挂在
                # _arm, 前段不跑), 无锚采纳会把在途迁移误终态化且终态无恢复面(_recover 只
                # 认 MOVING)。只认「ts 可解析且 >= created_at」的本世在途账(journal 即时
                # 落盘先于 state 周期刷盘的失窗, ts 必不早于本世建账锚); ts < created_at =
                # 上一世残留、created_at 缺失的旧账 = 锚定不上 —— 一律搁置不采纳, state
                # 原样留给 _arm 侧既有清理口(_reset_stale_terminal_journal)。
                anchor = float(job.created_at or 0.0)
                try:
                    ts_f = float(journal.get("ts"))  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    ts_f = None
                if anchor > 0 and ts_f is not None and ts_f >= anchor:
                    job = replace(job, phase=j_phase)
                    reconciled += 1
                    logger.warning(
                        f"relocate | 启动对账: job {jid} state 相位陈旧({d.get('phase')}), "
                        f"按 journal 终相位回写 {j_phase}(journal 即时落盘先于 state 周期刷盘的失窗收敛)"
                    )
                else:
                    logger.debug(
                        f"relocate | 启动对账: job {jid} journal 终相位({j_phase})锚定不上本生命周期"
                        f"(created_at={anchor}, ts={journal.get('ts')}), 搁置不采纳(state 原样, "
                        "上一世残留交 _arm 侧既有清理口)"
                    )
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
        if reconciled:
            self._persist()  # 回写落账(状态盒; 磁盘刷盘由接管面写穿与 state 服务周期双兜底)
        self._publish_snapshot()
        # S3 终态分级保留(D3, 计划 26-11-15-2340 §03.4): 账接管完成后滚一次成功历史 ——
        # 覆盖迁移器转入的旧账与停机期间累积的超限 done 账(触发面口径见 prune_success_history)
        self.prune_success_history()
        # 接管即持久(真机验收缺陷1/2, 2026-11-17): 接管面突变(迁移器盖章/转换、启动对账
        # 回写、prune 滚出)在内存收敛完成后立即写盘一次, 不等 state 服务周期刷盘 —— 非优雅
        # 终止时这些突变的丢失窗口压到零。历史背景(issue 26-11-17-0214): 内核曾把 run() 的
        # _reload_state 挂在 start_all 之后, 本阶段写点会被那次整体替换静默丢弃(真机实测:
        # prune 滚出后三次刷盘仍是滚出前账面、relocate.model_version 永不落盘, 直到首个账面
        # 动作 _persist 才收敛), 写穿当时是规避手段; 丢弃窗口已随内核修复(加载挪到
        # start_all 之前)消除, 写穿保留为持久化语义面。save 原子写+.bak, 持锁已在
        # QbManager.__init__, 单一写线程不变; 运行期接管点(热启用 apply)多付一次落盘, 换
        # 「接管即持久」不变量。dry-run 不动手(真写); state 服务缺失/替身无 save 时跳过
        # (测试替身形态, 与 _state_jobs 同容错)。
        if not self._dry_run():
            save = getattr(getattr(self._ctx, "state", None), "save", None)
            if callable(save):
                save()
        # 账接管成功(含迁移器通过): 清热启用被拒标志(R2-1)—— 执行入口恢复按现配置放行
        self._hot_enable_rejected = False
        return n

    def _set_job(self, job: RelocateJob) -> RelocateJob:
        """登记相位推进后的 job(单点: 落内存 + 写 state + 可选 qB 标签镜像)

        标签镜像在 state 落盘之后做: state 是唯一事实源, 镜像失败(超时/不支持/权限)
        只告警计数, 绝不回滚相位或影响收尾判定。
        让路/拦截登记(S5 起)是派生查询(relocating_hashes/resuming_hashes/alias_roots),
        账面换代即最新, 本方法不再有登记重算挂点。
        """
        job = replace(job, updated_at=self._clock.now())
        self._jobs[job.job_id] = job
        self._jobs_loaded = True
        self._persist()
        self._publish_snapshot()
        self._sync_pending_tag(job)
        # S3 终态分级保留(D3, 计划 26-11-15-2340 §03.4): done 落账即滚出超限旧账 ——
        # 挂在标签镜像之后(本 job 是最新 done 恒保留, 滚出的只会是更老的 done 账),
        # 清理基元自带落盘/快照/登记重算, 失败账(failed/cancelled)不参与计数(Q11)。
        if job.phase == ru.PHASE_DONE:
            self.prune_success_history()
        # 标签镜像可能改写 tag_on(_note_tag_state); 返回账上现值, 免得调用方拿旧对象继续
        # 推进相位时把「曾加标签」这一位覆盖回 False(终态就会漏摘标签)。
        return self._jobs.get(job.job_id, job)
