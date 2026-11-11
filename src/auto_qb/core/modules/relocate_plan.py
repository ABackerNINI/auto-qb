"""relocate 预检/规划叶: 迁移预检、添加预检、能力面板与事实收集(自 relocate_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 relocate_mod.py 原文件逐字一致。
"""
import os
import stat
from typing import Any, Iterable, List, Optional, Tuple

from ...config.models import bt_backup_path_of
from ...infra import alias_fs, file_access, utils
from ...infra.alias_fs import KIND_SYMLINK
from ...infra.file_access import FileAccess
from ...torrents import TorrentRecord, TorrentStore
from . import relocate_proof as rp
from . import relocate_units as ru
from .grouping_mod import group_key_of
from .relocate_probe import probe_fingerprint
from .relocate_units import (
    CLS_BLOCKED,
    AddFacts,
    GroupFacts,
    RelocateJob,
    evaluate_add,
    evaluate_group,
    same_volume_proof,
)
from .relocate_common import (
    _QB_TEMP_SUFFIX,
    _native,
    _same_volume_resolved,
    _top_children,
    _volume_free_resolved,
    logger,
)


def is_legacy_resume_storage(raw: Any) -> bool:
    """qB resume_data_storage_type 是否 Legacy 文件后端(计划 26-11-05-0808 S1, D2 运行时检测)

    WebAPI app/preferences 直读: qB 4.6+ 返回整数 0 = Legacy 文件 / 1 = SQLite; qB 5.x 改
    返回字符串枚举(实测 5.2.3 = "Legacy"), 两代形状都接受 —— str().strip().lower() 后比对
    ("0", "legacy"), 字符串字样与整数同路容错。键缺失/空 = SQLite 选项出现之前的 qB,
    只有文件后端, 按 Legacy 放行
    (后端检测拦的是「存在但非 Legacy」, 不是「读不到版本特征」; 读不到偏好整体属连接
    故障, 由调用方 fail-closed 另行拒绝)。
    """
    if raw is None:
        return True
    text = str(raw).strip().lower()
    if not text:
        return True
    return text in ("0", "legacy")


def probe_bt_backup_reject(path: str) -> str:
    """BT_backup 目录可达可写探测(计划 26-11-05-0808 S1, 部署矩阵 D 格): 返回拒绝文案, "" = 通过

    最保守探测方案(任务拍板): 只做存在性(os.path.isdir)+ 权限位(os.access R_OK|W_OK),
    **不往目录里写探测文件** —— BT_backup 是 qB 私有账本目录, 运行期零写入是 N1 实测
    (0.5s 覆盖)换来的铁律, 预检的只读承诺(T20)也不含任何写入。已知局限按保守方向接受:
    Windows os.access 只查只读属性不验 ACL —— 误报拒(目录被打只读属性/ACL 收紧)会给出
    明确文案由用户核实; 漏报放(探测通过但真实写入失败)由 S2 编辑器原子写失败兜底告警,
    不会静默半效。Windows 长路径经 add_long_path_prefix_for_win 前缀(与本叶既有探测同款)。
    """
    p = str(path or "").strip()
    if not p:
        return "BT_backup 路径为空(config.relocate.bt_backup 配了空值)"
    full = utils.add_long_path_prefix_for_win(p)
    if not os.path.isdir(full):
        return (
            f"BT_backup 目录不存在({p}): 请核对 qB profile 下 data/BT_backup 的实际位置"
            "(--profile 便携实例路径不同; 部署矩阵 D 格 fail-fast 禁用)"
        )
    if not os.access(full, os.R_OK | os.W_OK):
        return (f"BT_backup 目录不可读写({p}): auto-qb 运行身份需要读写权限"
                "(docker qB 需卷映射 + uid 对齐; 部署矩阵 D 格 fail-fast 禁用)")
    return ""


def _source_three_states(save_path: str, names: Iterable[str], unwanted: Any,
                         fa: FileAccess) -> Tuple[List[str], List[str], List[str]]:
    """源侧三态逐声明文件判定(计划 26-11-05-0808 S1 继承 0546 机制1/D2; E2.1/E2.2 实证判据)

    对每个声明名(按 files API 声明路径逐文件 stat, 深层路径天然覆盖 —— 现行 GATE_QB_TEMP
    的内容根**顶层**扫描漏深层孪生, E2.1 漏拦面即此): -> (缺失, 不可判定, .!qB 孪生)
    - exists(声明名) True = 「在」(放行);
    - False 且 exists(声明名 + .!qB 孪生) True = 「.!qB 态」(未落定, 孪生名归入第三表 ——
      收集侧并入 GroupFacts.qb_temp_entries, 复用既有 GATE_QB_TEMP 闸, 不另造 gate id);
    - 两个名字都不在 = 「缺失」(GATE_SOURCE_MISSING; qB 搬迁对 stat 不到的源文件忽略并算
      成功, storage_utils.cpp:151 —— 数据已不在这两个名字下, 迁移只会零搬移假成功, E2.2);
    - 任一 exists 不可判定(容器映射 miss) = 「不可判定」(GATE_SOURCE_UNKNOWN; D2 按现行
      target_unknown 同款保守拒, 声明名判不了即不继续查孪生)。
    unwanted(priority=0, 未勾选)文件不参与: 它们本就不落盘, 不是缺失形态(误报防线)。
    """
    missing: List[str] = []
    unknown: List[str] = []
    twins: List[str] = []
    for n in names:
        if n in unwanted:
            continue
        declared = _native(save_path, n)
        try:
            hit = fa.exists(declared)
        except Exception:  # noqa: BLE001 - 单文件探测异常按不可判定(保守默认, 不猜)
            hit = file_access.UNDETERMINED
        if hit is file_access.UNDETERMINED:
            unknown.append(n)
            continue
        if hit:
            continue
        try:
            twin = fa.exists(_native(save_path, n + _QB_TEMP_SUFFIX))
        except Exception:  # noqa: BLE001
            twin = file_access.UNDETERMINED
        if twin is file_access.UNDETERMINED:
            unknown.append(n)
        elif twin:
            twins.append(n + _QB_TEMP_SUFFIX)
        else:
            missing.append(n)
    return missing, unknown, twins


class PlanMixin:
    def relocate_precheck(self, hashes: Iterable[str] | None, location: str = "") -> list:
        """整组迁移预检(只读 dry-run): 多选按组拆开逐组判定, 三分流供确认框摊开

        只读承诺(T20 同口径): 不写 state、不 pop、无任何 qB 写 API、种子零变动 ——
        读的只有 store 记录 / record.files(files API 只读) / server_state(同卷证明) /
        文件系统 listing(内容根归属) / alias_fs 能力探测(建删临时链接是探测既定手段)。
        经命令队列在主循环线程执行(与写命令串行化, 快照无撕裂)。

        返回 list[dict]: 逐组一条 + gone 种子逐条; 字段形状与跳检预检对齐
        (hashes/mover/name/save_path/target/form/cls/reasons/notes ...), summary 由
        WEB 命令层聚合(ok/confirm/blocked)。

        部署维闸门(计划 26-11-05-0808 S1, 先于分组判定): 后端非 Legacy(E 格)/BT_backup
        未配置或不可达(D 格) => 整个请求一条 blocked 回执(fail-fast, 不做降级双轨 D4)。
        组级五闸(§3.1 预检行, evaluate_group): AutoTMM/嵌套目标(0546 机制3)/源侧三态
        (0546 机制1, .!qB 态复用 GATE_QB_TEMP)+ 既有闸门照跑。
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
                                "gate": ru.GATE_DISABLED,
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
        deployment_gate = self._deployment_gate(client, req)
        if deployment_gate is not None:
            return [deployment_gate]

        gone, groups = self._buckets(req)
        items.extend(gone)
        for records in groups:
            facts = self._group_facts(records, target, client)
            items.append(evaluate_group(facts))
        logger.info(f"relocate | 迁移预检({len(req)} 个 hash -> {len(items)} 项): {self._summ(items)}")
        return items

    def _deployment_gate(self, client: Any, hashes: List[str]) -> Optional[dict]:
        """部署维闸门(计划 26-11-05-0808 S1, 部署矩阵 D/E 格): 后端 Legacy + BT_backup 可达

        两道闸任一不过 = fastresume 收尾整链对该 qB 实例不可用 => 整个请求一条 blocked
        回执(gate/text 与组级闸门同形, 结构化拒绝), 不做降级双轨(D4: 旧链已证伪, 无双轨可退)。
        只读承诺不变: 后端经 app/preferences 直读, BT_backup 只做存在性 + os.access 探测, 零写入。
        """
        # ---- E 格: 存储后端必须 Legacy(D2: app/preferences 直读 resume_data_storage_type) ----
        try:
            prefs = client.app_preferences() or {}
        except Exception as e:  # noqa: BLE001 - 读不到偏好无法确认后端: fail-closed(保守默认)
            return self._deployment_block(
                hashes, ru.GATE_BACKEND, f"无法读取 qB 偏好(app/preferences 失败: {e}): 无法确认 fastresume 存储后端 —— "
                "收尾链要求 Legacy 文件后端, 按不可用拒绝(fail-closed)"
            )
        raw = prefs.get("resume_data_storage_type")
        if not is_legacy_resume_storage(raw):
            return self._deployment_block(
                hashes, ru.GATE_BACKEND, f"qB fastresume 存储后端不是 Legacy(resume_data_storage_type={raw!r}): SQLite 后端没有 "
                "BT_backup fastresume 文件, 改写收尾链整体不可用 —— 请在 qB 设置里把「恢复数据存储」切回 "
                "Legacy 后重试(部署矩阵 E 格 fail-fast 禁用, 不做降级双轨)"
            )
        # ---- D 格: BT_backup 目录可达可写(relocate.bt_backup 标量现读, 读键口径单点 bt_backup_path_of) ----
        conf_root = getattr(self._ctx, "config", None)
        path = bt_backup_path_of(conf_root) if conf_root is not None else ""
        if not path:
            qb = getattr(conf_root, "qbittorrent", None) if conf_root is not None else None
            host = getattr(qb, "host", "?") if qb is not None else "?"
            port = getattr(qb, "port", "?") if qb is not None else "?"
            return self._deployment_block(
                hashes, ru.GATE_BT_BACKUP,
                f"当前 qB 实例({host}:{port})未配置 BT_backup 路径(配置键 config.relocate.bt_backup 为空): "
                f"fastresume 收尾功能未启用 —— 请在配置文件 relocate 段把 bt_backup 填为本实例 qB 的 "
                "<BT_backup 目录> 后重试(留空 = 功能不启用, 不影响其它功能)"
            )
        reject = probe_bt_backup_reject(path)
        if reject:
            return self._deployment_block(hashes, ru.GATE_BT_BACKUP, reject)
        return None

    @staticmethod
    def _deployment_block(hashes: List[str], gate: str, text: str) -> dict:
        """部署闸拒绝回执(与预检既有 early-return 同形: hashes/cls/reasons)"""
        return {"hashes": list(hashes), "cls": CLS_BLOCKED, "reasons": [{"gate": gate, "text": text}]}

    def _buckets(self, req: List[str]) -> Tuple[List[dict], List[List[TorrentRecord]]]:
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
                gone_items.append(
                    {
                        "hash": h,
                        "cls": CLS_BLOCKED,
                        "reasons": [{
                            "gate": ru.GATE_GONE,
                            "text": "种子已不在客户端"
                        }]
                    }
                )
            else:
                present[h] = rec
        buckets: dict[Tuple[str, Tuple[str, ...]], List[str]] = {}  # group key -> [hashes](仅本次选中的)
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
    def _file_map(rec: TorrentRecord, client: Any) -> dict:
        """种子的 {规范化相对路径: 大小}(files API 只读, 惰性缓存; 异常按空表保守处理)"""
        try:
            files = rec.files(client)
        except Exception as e:  # noqa: BLE001 - 预检边界: 读不到文件表不进判定, 不漏真相
            logger.warning(f"relocate | 读取文件列表失败({rec.log_repr}): {e}")
            return {}
        return {utils.path_normalize(f.name): f.size for f in files}

    @staticmethod
    def _summ(items: List[dict]) -> str:
        counts = {"ok": 0, "confirm": 0, "blocked": 0}
        for it in items:
            counts[it.get("cls", "blocked")] = counts.get(it.get("cls", "blocked"), 0) + 1
        return f"ok {counts['ok']} / confirm {counts['confirm']} / blocked {counts['blocked']}"

    def _group_facts(self, records: List[TorrentRecord], target: str, client: Any) -> GroupFacts:
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

        # ---- 源侧三态检查(0808 S1 继承 0546 机制1: 在/.!qB 孪生/缺失/不可判定, 逐声明文件) ----
        # 未勾选(priority=0)文件不参与 —— 它们本就不落盘, 不构成缺失形态(误报防线);
        # 文件表读不到时与 _file_map 同口径空转(缓存热, 二次调用零请求)。
        qb_temp: List[Any] = []  # .!qB 未落定收集面(顶层扫描 + 深层孪生双源; 归属分类见下方 listing 块)
        try:
            unwanted = {
                utils.path_normalize(str(f.name))
                for f in mover.files(client) if getattr(f, "priority", 1) == 0
            }
        except Exception:  # noqa: BLE001 - 文件表读不到: 三态检查空转(与 _file_map 同保守口径)
            unwanted = set()
        source_missing, source_unknown, qb_temp_twins = _source_three_states(save_path, names, unwanted, fa)
        qb_temp.extend(qb_temp_twins)  # 孪生态并入既有 qb_temp 收集面(复用 GATE_QB_TEMP, 深层补漏 E2.1)

        # ---- 内容根 listing(归属分类; 读不到 = 不可判定 = 不专属) ----
        exclusive: Optional[bool] = None
        # (三行拆开写只为逐个补注解; _classify_entries 回 List[Any], 故元素口径同 Any)
        misc: List[Any] = []
        external: List[Any] = []
        # qb_temp 已在三态检查块初始化并先收了深层孪生(本 listing 块继续收顶层命中)
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
            # .!qB 条目按归属三分(plan 26-11-02-0134): qB 的搬运(libtorrent 1.2/2.0
            # aux::move_storage 只遍历种子自己的文件表逐文件搬)碰不到外组/无主的 .!qB,
            # 它们与普通外来条目同走归属分类(外组 -> external note, 其余 -> misc note);
            # 只有「本组文件处于 .!qB 未落定态」(剥后缀对回本组, 或本组 names 自带后缀)
            # 才进 qb_temp 硬拦面 —— 这是 GATE_INCOMPLETE 之外的磁盘态竞态兜底。
            qb_ext = [n for n in ext if n.endswith(_QB_TEMP_SUFFIX)]
            rest = [n for n in ext if not n.endswith(_QB_TEMP_SUFFIX)]
            # extend 而非重绑: qb_temp 已先收了三态检查的深层孪生(0808 S1), 两源合并
            qb_temp.extend(n for n in qb_ext if n[:-len(_QB_TEMP_SUFFIX)] in own)
            qb_stripped = [n[:-len(_QB_TEMP_SUFFIX)] for n in qb_ext if n[:-len(_QB_TEMP_SUFFIX)] not in own]
            # belongs 单次扫描: rest 与剥后缀名一并送分类, 结果按名回流到带后缀原名
            misc, external = self._classify_entries(rest + qb_stripped, save_path, content_root, hashes, store, client)
            ext_set, misc_set = set(external), set(misc)
            external = [n for n in rest if n in ext_set] + [n for n in qb_ext if n[:-len(_QB_TEMP_SUFFIX)] in ext_set]
            misc = [n for n in rest if n in misc_set] + [n for n in qb_ext if n[:-len(_QB_TEMP_SUFFIX)] in misc_set]
            qb_temp += [n for n in names if n.endswith(_QB_TEMP_SUFFIX)]
            exclusive = not ext

        # ---- 目标同名冲突(逐文件全量判定: 同卷/跨卷都适用, 只查本组文件; R2 #2 去
        # names[:50] 静默截断 —— 漏拦的冲突会让 mover 撞 need_full_check 进度清零;
        # 上限受 plan hard_max 约束, 规则重复发起被 T3 幂等挡在闸门前, 成本仅新目标首查) ----
        conflicts = []
        target_unknown = False
        target_not_dir = False
        # R2 #3: 目标已存在但不是目录 => 迁移必然失败(qB create_directories 落不了), 预检直接拒;
        # 存在性抛错按不可判定(冲突循环同款), 由 target_unknown 兜底
        try:
            if fa.exists(target) is True and fa.isdir(target) is not True:
                target_not_dir = True
        except Exception:  # noqa: BLE001
            pass
        for n in names:
            try:
                hit = fa.exists(_native(target, n))
            except Exception:  # noqa: BLE001
                hit = file_access.UNDETERMINED
            if hit is True:
                conflicts.append(n)
            elif hit is file_access.UNDETERMINED:
                target_unknown = True  # 容器映射 miss: 不可判定一律拒绝, 不猜「不存在」
                break

        # ---- 空间 / 同卷 / 同机证明(P3 判据替换, 计划 26-11-04-0055 §03.1) ----
        # 目标叶子未创建是迁移正常输入 => 上溯最近存在祖先取卷剩余(plan R1 方案A);
        # 全链不可用 => None => GATE_SPACE 照旧硬拦(真不可判定)
        target_free = _volume_free_resolved(fa, target)
        try:
            src_free = fa.disk_usage(save_path).free
        except Exception:  # noqa: BLE001
            src_free = None
        # 同卷判定: 目标叶子未建时 st_dev 不可得会按跨卷保守处理、让形态降级/拒绝 ——
        # 上溯最近存在祖先比 st_dev(与 _volume_free_resolved 同一机制, plan R1 方案A)
        same_vol = _same_volume_resolved(alias_fs, self._syscall(save_path), self._syscall(target))
        qb_free = (getattr(store, "server_state", None) or {}).get("free_space_on_disk")
        # 同机证明换判据: free-space 代理(same_volume_proof)退出判定(它比的是 qB **默认
        # 保存路径**那块卷, 未必是本次迁移的源/目标卷 —— 比错盘与剩余空间巧合两类病,
        # 报告 26-11-03-2306 §06.1), 换成路径级证据(D 列目录元数据比对 -> B′ 元数据
        # size 降级); 代理只在两侧证据均不可判定时作参考 note 保留(函数本体与单测保留)。
        proved, same_fs_negative, same_fs_note = self._same_fs_proof(
            save_path, content_root, target, files, conf, fa, qb_free, src_free, target_free
        )

        # ---- 能力探测 + 形态 kind(目标卷差异由 P3 复探; P2 用进程级能力) ----
        # remote 喂**确定性不共享**(same_fs_negative)而非「未证明」: 未证明的多成员组
        # 预检不再硬拦(P3 闸门重排), 由执行链一次性强探测兜底; 只有证据判负才按远程
        # 处理(平台矩阵直接拒绝)。
        cap = alias_fs.get_capability()
        verdict = alias_fs.platform_verdict(
            cap, target_is_unc=alias_fs.is_unc(target), remote=same_fs_negative, same_volume=bool(same_vol)
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
                "文件级链接不可建: " + "; ".join(bits) + " —— 出路: 1. 以管理员身份运行 auto-qb"
                "或开启 Windows 开发者模式 2. 换同卷目标走硬链接 3. 改用目录别名(需目录专属) 4. 缩短路径"
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
                elif st.st_nlink > 1 and not self._own_alias_hardlink(st):
                    # S5(D15 收窄的必然推论): 收尾窗再迁移时组文件正被**前任 job 的逐文件
                    # 硬链接别名**挂着(nlink>=2 来源是自己的别名) —— 这是迁移设计的一部分,
                    # 不是第三方去重, 放行; D11 拦的第三方硬链接(别名之外的同 inode 名)照拦。
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
            target_not_dir=target_not_dir,
            same_volume=same_vol,
            target_free=target_free,
            same_fs_proved=proved,
            same_fs_negative=same_fs_negative,
            same_fs_note=same_fs_note,
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
            auto_tmm_hashes=tuple(r.hash for r in records if bool(getattr(r, "auto_tmm", False))),
            source_missing_files=tuple(source_missing),
            source_unknown_files=tuple(source_unknown),
        )

    def _own_alias_hardlink(self, st: os.stat_result) -> bool:
        """nlink>1 的代表文件是否挂着**自有别名硬链接**(S5 链式再迁移的放行面)

        判定: 任一活跃 job 的 alias_paths 中存在与代表文件同 inode(dev+ino)的路径 ——
        同一份数据的另一个名字正是前任 job 建的逐文件别名(hardlink 形态), 不是第三方
        去重。代表文件本身就是别名路径时同样命中(stat 同文件同 inode)。目录别名
        (junction/目录 symlink)不产生 nlink, 天然不进本判定。
        """
        for job in self.active_jobs():
            for p in job.alias_paths:
                try:
                    pst = os.stat(utils.add_long_path_prefix_for_win(self._syscall(p)))
                except OSError:
                    continue
                if pst.st_ino == st.st_ino and pst.st_dev == st.st_dev:
                    return True
        return False

    def _same_fs_proof(
        self,
        save_path: str,
        content_root: str,
        target: str,
        files: Iterable[Tuple[str, int]],
        conf: Any,
        fa: FileAccess,
        qb_free: Optional[int],
        src_free: Optional[int],
        target_free: Optional[int],
    ) -> Tuple[bool, bool, str]:
        """同机判定(计划 26-11-04-0055 §03.1/§04 P3 前半): -> (proved, negative, note)

        判据链(优先级从高到低):
        - assume_shared=true: 用户显式越权直通(note 注明「未经 auto-qb 验证, 由用户承担」);
        - 路径级证据(relocate_proof.path_evidence: D 列目录元数据比对 -> B′ 降级):
          src 侧 D 级 positive => 证明成立, src 侧 D 级 negative => 确定性不共享(硬拦);
          B′ 与 dst 侧 visibility_only 两面都是弱证据(证不了「qB 读得到本机盘/共享同一
          命名空间」), 正/负任何方向都不一锤定音, 降为 note 不参与证明: E1 机器级缓存
          passed => 凭缓存放行, 否则未证明(待执行链一次性强探测定夺);
        - 两侧都 unavailable: E1 机器级缓存 passed => 凭缓存放行(note 注明路径级复查
          不可用); 否则未证明(negative=False, 待执行链一次性强探测), free-space 代理
          结果只作参考 note 保留(不再参与判定)。
        """
        if bool(getattr(conf, "assume_shared", False)):
            return True, False, "同机判定: relocate.assume_shared=true —— 未经 auto-qb 验证, 由用户承担"
        e1_passed = False
        qb_conf = getattr(getattr(self._ctx, "config", None), "qbittorrent", None)
        if qb_conf is not None:
            try:
                e1 = self.probe_get(probe_fingerprint(qb_conf, self.probe_salt()))
                e1_passed = (e1 or {}).get("status") == "passed"
            except Exception:  # noqa: BLE001 - 缓存读失败按未命中(执行链会再探), 不挡预检
                e1_passed = False
        src_ev = rp.path_evidence(
            self._ctx, content_root, self._syscall(content_root), files=self._cr_files(files, content_root, save_path)
        )
        dst_probe = rp.nearest_existing_ancestor(fa, target)
        if dst_probe is None:
            dst_ev = rp.Evidence(rp.UNAVAILABLE, "", "目标链路本机不可读, 无法定位可列的最近存在祖先")
        else:
            dst_ev = rp.path_evidence(self._ctx, dst_probe, self._syscall(dst_probe), visibility_only=True)
        # 强证据只有 src 侧 D 级(实时 size+mtime 逐条比对): positive => 证明成立,
        # negative => 确定性判负。B′ 级(种子元数据 size)与 dst 侧 visibility_only(qB 能
        # 列出目标祖先目录, 路径串两侧同名不等于共享同一命名空间)都是弱证据: 任何方向
        # 都不一锤定音 —— 正/负都降为 note, 交执行链一次性强探测(E1 有指纹缓存, 成本
        # 有界)定夺, E1 机器级缓存 passed 时凭缓存放行(issue 26-11-07-0527 R1#35)。
        # dst 侧 visibility_only 永不产 NEGATIVE(列目录成功即 positive), 判负只可能来自 src。
        if src_ev.status == rp.POSITIVE and src_ev.level == rp.LEVEL_D:
            return True, False, "同机判定: 源侧路径级证据吻合(D 级)"
        if src_ev.status == rp.NEGATIVE and src_ev.level == rp.LEVEL_D:
            return False, True, f"同机判负详情: {src_ev.detail}"
        # ---- 弱证据汇合面(B′ 正/负与 dst visibility positive 都在这里) ----
        weak_bits = []
        if rp.POSITIVE in (src_ev.status, dst_ev.status):
            ev, side = (src_ev, "源侧") if src_ev.status == rp.POSITIVE else (dst_ev, "目标侧")
            weak = ("仅种子元数据 size 比对(B′)" if ev.level == rp.LEVEL_BPRIME else "仅证明 qB 能列出该目录(visibility_only)")
            weak_bits.append(f"{side}路径级证据仅弱证据吻合({weak})")
        if src_ev.status == rp.NEGATIVE:  # 走到这里必为 B′ 级(D 级判负已在上方返回)
            weak_bits.append(f"源侧弱证据判负(仅元数据 size 比对: {src_ev.detail}), 不作确定性结论")
        if weak_bits:
            joined = "; ".join(weak_bits)
            if e1_passed:
                return True, False, f"同机判定: {joined}, 凭机器级强证明(E1 缓存)放行"
            return False, False, f"同机判定: {joined} —— 执行迁移时将做一次性强探测(失败将拒绝)"
        # 两侧证据均不可判定: E1 机器级缓存兜底放行, 否则未证明(执行链强探测兜底)
        if e1_passed:
            return True, False, "同机判定: 路径级复查不可用(qB 列目录与元数据比对均不可判定), 凭机器级强证明(E1 缓存)放行"
        legacy = same_volume_proof(qb_free, src_free) or same_volume_proof(qb_free, target_free)
        hint = "; free-space 代理参考吻合(仅提示, 已从判据退役)" if legacy else ""
        return False, False, f"路径级同机证据不可判定({src_ev.detail}){hint}"

    @staticmethod
    def _cr_files(files: Iterable[Tuple[str, int]], content_root: str, save_path: str) -> List[Tuple[str, int]]:
        """成员文件表换算到内容根粒度((相对 content_root 的路径, size)), B′ 比对用

        files 是 save_path 相对路径(qB files API 口径); 内容根 = save_path 本身(flat)
        时原样透传, 否则剥掉内容根那一段前缀。
        """
        cr_norm = utils.path_normalize(content_root)
        sp_norm = utils.path_normalize(save_path)
        if cr_norm == sp_norm or not cr_norm.startswith(sp_norm + "/"):
            return [(utils.path_normalize(name), size) for name, size in files]
        prefix = cr_norm[len(sp_norm) + 1:]
        return [
            (norm[len(prefix) + 1:], size)
            for norm, size in ((utils.path_normalize(name), size) for name, size in files)
            if norm.startswith(prefix + "/")
        ]

    def _classify_entries(
        self, rest: List[Any], save_path: str, content_root: str, hashes: Iterable[str], store: TorrentStore,
        client: Any
    ) -> Tuple[List[Any], List[Any]]:
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
