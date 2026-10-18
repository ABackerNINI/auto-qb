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
from typing import Optional

from ...infra import alias_fs, file_access, utils
from ...infra.alias_fs import KIND_SYMLINK
from ...torrents import TorrentRecord
from ..module import AppContext, ApplyResult, BaseModule
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

    def sections(self) -> tuple:
        return ("relocate", )

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        """记录上下文与初始配置; enabled 时探测一次链接能力(开关关时零副作用, R15)"""
        self._ctx = ctx if ctx is not None else self._ctx
        self._conf = ctx.config.relocate
        if getattr(self._conf, "enabled", False):
            alias_fs.get_capability(refresh=True)
            logger.info("relocate | 启动: 整组迁移已启用, 已完成本机链接能力探测")
        else:
            logger.debug("relocate | 启动: 未启用(enabled=false), 不探测不建链")

    def stop(self) -> None:
        return None  # P2 无运行期资源可停(job 账随 P3, 停机语义同 P3)

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

        store = ctx.store
        # ---- 逐 hash gone 判定 + 按组拆分(组 key 单点复用 grouping_mod 公式) ----
        present = {}
        for h in req:
            rec = store.get(h)
            if rec is None:
                items.append({
                    "hash": h,
                    "cls": CLS_BLOCKED,
                    "reasons": [{
                        "gate": "gone",
                        "text": "种子已不在客户端"
                    }],
                })
            else:
                present[h] = rec
        buckets = {}  # group key -> [hashes](仅本次选中的)
        for h, rec in present.items():
            fmap = self._file_map(rec, client)
            buckets.setdefault(group_key_of(rec.save_path, fmap), []).append(h)

        for key, selected in buckets.items():
            # 组成员取 store 全组(迁移影响的是整个内容组, 不只是选中的入口种子);
            # store 无该组(如 grouping 关过) 时退回本次选中集合
            members = [h for h in store.groups.get(key, []) if h in store.by_hash] or list(selected)
            records = [store.by_hash[h] for h in members if h in store.by_hash]
            if not records:
                continue
            facts = self._group_facts(records, target, client)
            items.append(evaluate_group(facts))
        logger.info(f"relocate | 迁移预检({len(req)} 个 hash -> {len(items)} 项): {self._summ(items)}")
        return items

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
        proved = same_volume_proof(qb_free, src_free)

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
        first_native = _native(save_path, names[0]) if names else save_path
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
                if utils.path_normalize(resolved) != utils.path_normalize(content_root):
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
