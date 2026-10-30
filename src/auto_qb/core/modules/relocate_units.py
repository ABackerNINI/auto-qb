"""relocate_units: 别名单元与迁移闸门的纯决策层(plan 26-10-18-1604 §3.2/§3.4/§3.6, 实施期 P2)

本文件是 P2「别名单元 + 闸门(只读)」的**纯函数单点**: 不触盘、不读 qB、不写 state ——
所有事实由调用方(relocate_mod)收集后经 GroupFacts/AddFacts 传入, 本文件只做判定。

两个入口:
- `plan(save_path, files, ...)`: 别名形态分流纯函数(§3.2 五行表)。按**组内文件数** F 分流:
  F < threshold ⇒ 逐文件链接; F >= threshold 且内容根是独立子目录且恰好只含本组文件
  ⇒ 目录别名(需显式确认); 平铺/目录不专属 ⇒ 逐文件链接; F > hard_max 且不能用目录
  别名 ⇒ 拒绝。**长路径能力校正先于阈值生效**(§3.2「能力校正」/T6): 文件级符号链接
  路径 >= link_path_limit(Windows 260)建不出来时, 若内容根是目录且其路径 <260 且
  目录专属 ⇒ 改为提议目录别名, 否则拒绝 —— 绝不静默降级成「不建链接」。
- `evaluate_group(facts)` / `evaluate_add(facts)`: 闸门判定(§3.1 拒绝行 + §3.6 影响面),
  产出与 WEB 回执同形的 item dict(cls 三分流 ok/confirm/blocked + reasons + notes)。

单成员组(只有 1 个种子引用这些文件)不需要别名: qB 直接搬完 save_path 就是 T,
没有第二个种子还指着 S —— 阈值与链接能力对单成员组一律不参与判定(§3.2「阈值只对
多成员组生效」), plan(multi_member=False) 直接给 direct。

相位机与 job 登记(§3.5): RelocateJob 是 state.json 里 relocate.jobs.<job_id> 的
**值对象镜像**(P3 执行体落账, P6 guardian 对账消费); 本文件只定义终态判定与
「挡不挡这次迁移」的谓词, 不建不删 job。
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

# ---------------------------------------------------------------- 常量

# 别名形态(与 alias_fs 的链接形态字符串并列使用; 进 state/界面, 不随代码改名)
FORM_DIRECT = "direct"  # 单成员组: qB 自己搬, 不建任何链接
FORM_FILE_LINKS = "file_links"  # 逐文件链接(同卷硬链接 / 跨卷 symlink)
FORM_DIR_ALIAS = "dir_alias"  # 目录别名(Windows junction / 目录 symlink)
FORM_REJECT = "reject"  # 拒绝(不迁移, 零副作用)

# 预检三分流(与跳检预检同类; confirm = 需用户在确认框显式点头才执行)
CLS_OK = "ok"
CLS_CONFIRM = "confirm"
CLS_BLOCKED = "blocked"

# 闸门 id(稳定字符串: 测试与前端按它断言, 改文案不改 id)
GATE_GONE = "gone"  # 种子已不在客户端
GATE_DISABLED = "disabled"  # relocate.enabled=false(纵深防御, 路由层已 403)
GATE_UNFINISHED = "unfinished"  # 已有未收尾迁移碰本组(§3.6 第 14 行 / S10)
GATE_INCOMPLETE = "incomplete"  # 组内存在未完成成员(progress < 1)
GATE_MOVING = "moving"  # 成员正处于 qB 搬迁态(state 含 moving)
GATE_TARGET_CONFLICT = "target_conflict"  # 目标已存在同名内容(qB 会走全量校验)
GATE_TARGET_UNKNOWN = "target_unknown"  # 目标路径存在性不可判定(容器映射 miss)
GATE_QB_TEMP = "qb_temp"  # 内容根存在 .!qB 临时文件
GATE_SPACE = "space"  # 目标卷剩余不足 / 不可判定
GATE_SAME_FS = "same_fs"  # 无法证明 auto-qb 与 qB 看同一块盘(§2.4 同卷证明)
GATE_PLATFORM = "platform"  # §3.3 能力矩阵不支持(跨 OS 容器 / 无链接能力)
GATE_HARDLINK = "hardlink"  # 组文件是第三方硬链接(st_nlink > 1, D11 拒迁)
GATE_THIRD_PARTY_LINK = "third_party_link"  # 组文件是第三方文件级链接(D11 拒迁)
GATE_FORM = "form"  # 形态分流本身的拒绝/需确认(plan() 产出)

# job 相位机(§3.5; 主干单向推进, 旁支 terminal)
PHASE_MOVING = "moving"
PHASE_WATCHING = "watching"  # moving 的长耗时变体: 仍在搬, 只降频提示, 不判失败
PHASE_MOVED = "moved"
PHASE_ARMED = "armed"
PHASE_REMOVING = "removing"
PHASE_REMOVED = "removed"
PHASE_FINALIZING = "finalizing"
PHASE_DONE = "done"
PHASE_FAILED = "failed"
PHASE_CANCELLED = "cancelled"
TERMINAL_PHASES = frozenset({PHASE_DONE, PHASE_FAILED, PHASE_CANCELLED})
# 收尾窗口(链接已删、qB 重启后 setLocation 之前): 此窗口内往原路径加种子会落原盘,
# 可能与已迁到新位置的数据重复(§3.6 第 8 行)
FINALIZE_WINDOW_PHASES = frozenset({PHASE_REMOVING, PHASE_REMOVED, PHASE_FINALIZING})

# ---------------------------------------------------------------- 路径纯函数


def _norm(path: str) -> str:
    """词法归一(斜杠统一 + 大小写折叠): 作用域/同路径判定的统一口径

    与 group_key_of 的 path_normalize 分层: 那里保持词法形态做组键, 这里叠加
    normcase(§3.3: POSIX 大小写敏感 / Windows 不敏感, 组键解析后仍需 normcase 兜底)。
    normcase 在 Windows 上的分隔符是反斜杠 —— 归一后再折回正斜杠, 让比较与平台无关
    (POSIX 无影响; 反斜杠作合法文件名字符的 POSIX 边角场景不在此判定域内)。
    """
    n = os.path.normcase(os.path.normpath((path or "").replace("\\", "/")))
    return n.replace("\\", "/")


def _join(save_path: str, rel: str) -> str:
    """save_path + qB 风格相对路径(正斜杠)拼接(纯字符串, 不触盘)"""
    base = save_path.replace("\\", "/").rstrip("/")
    return f"{base}/{rel.strip('/')}" if rel else base


def _within(scope: str, path: str) -> bool:
    """path 是否落在 scope 目录内(含等于); 归一后比较"""
    s, p = _norm(scope), _norm(path)
    if not s:
        return False
    return p == s or p.startswith(s + "/")


def _too_long(path: str, limit: Optional[int]) -> bool:
    """路径长度是否达到链接创建上限(实测: 259 可建, 260 起一律 WinError 1314)"""
    return limit is not None and len(path) >= limit


def layout_of(save_path: str, files: Sequence[str]) -> Tuple[bool, str]:
    """内容布局判定(§3.2) -> (flat, content_root_rel)

    - flat=True:  所有文件直接铺在 save_path 下(NoSubfolder/单文件平铺) —— 内容根就是
                  save_path 本身, **整目录别名一律不提供**(§3.2, D8)。
    - flat=False, rel="":  文件跨多个顶层段(混合布局) —— 无单一专属内容根, 目录别名不可用。
    - flat=False, rel=<段>: 唯一顶层子目录, 内容根 = save_path/<段>(目录别名候选)。
    """
    segs = [str(f).replace("\\", "/").strip("/") for f in files if str(f).strip()]
    if not segs:
        return True, ""
    if all("/" not in s for s in segs):
        return True, ""
    firsts = {s.split("/", 1)[0] for s in segs}
    if len(firsts) == 1:
        return False, next(iter(firsts))
    return False, ""


# ---------------------------------------------------------------- 别名单元计划


@dataclass(frozen=True)
class RelocateUnitPlan:
    """plan() 的产出: 本次迁移的别名单元(形态/链接数/是否需确认/自解释理由)"""

    form: str  # FORM_*(direct/file_links/dir_alias/reject)
    file_count: int
    content_root: str  # 内容根路径(flat 时 = save_path)
    content_root_rel: str  # 内容根相对 save_path 的段(flat/混合 = "")
    flat: bool  # 内容根 = save_path 本身(平铺/NoSubfolder)
    exclusive: bool  # 内容根恰好只含本组文件(目录别名的硬前提)
    needs_confirm: bool  # 目录别名必须显式确认「以后新增也落新位置」
    link_count: int  # 预计链接条数(dir_alias=1; file_links=F; 其余 0)
    link_kind: Optional[str]  # 拟用链接形态(junction/symlink/hardlink; direct/reject=None)
    fallback: str  # 用户拒绝确认后的回落形态(file_links 或 "")
    reason: str  # 自解释文案(为什么是这个形态/为什么拒绝/为什么需确认)


def plan(
    save_path: str,
    files: Sequence[str],
    threshold: int = 8,
    hard_max: int = 2000,
    *,
    multi_member: bool = True,
    content_root_exclusive: Optional[bool] = None,
    file_link_kind: Optional[str] = None,
    file_link_error: str = "",
    dir_link_kind: Optional[str] = None,
    dir_link_error: str = "",
    link_path_limit: Optional[int] = None,
) -> RelocateUnitPlan:
    """别名形态分流纯函数(§3.2 五行表 + 能力校正/T6 + §3.2.1 阈值只对多成员组生效)

    入参里的 kind/error/limit 都是**已探测事实**(alias_fs 能力探测 + 目标卷同卷判定),
    本函数不触盘; 判定顺序(§3.2「能力校正先于阈值生效」):
      1. 单成员组 / 空文件列表先行(direct / reject);
      2. 文件级链接可建性(能力 + 长路径): 不可建 ⇒ 能力校正(目录别名可行则提议, 否则拒绝);
      3. 阈值: F < threshold ⇒ 逐文件链接; F >= threshold 且目录专属且目录别名可建 ⇒ 目录别名;
      4. hard_max: 逐文件链接条数超硬上限且不能用目录别名 ⇒ 拒绝(链接爆炸防护)。
    """
    names = [str(f).replace("\\", "/").strip("/") for f in files if str(f).strip()]
    count = len(names)
    flat, rel = layout_of(save_path, names)
    content_root = _join(save_path, rel) if rel else save_path
    exclusive = bool(content_root_exclusive) and rel != ""

    # 空文件表先于「单成员组直搬」: 读不到文件表时连「搬什么」都不知道, 不能按 direct 放行
    # (单成员组确实不需要别名, 但空表是事实缺失, 不是「不需要」)
    if count == 0:
        return RelocateUnitPlan(
            FORM_REJECT, 0, content_root, rel, flat, exclusive, False, 0, None, "", "文件列表为空, 无法判定内容布局"
        )
    if not multi_member:
        return RelocateUnitPlan(
            FORM_DIRECT, count, content_root, rel, flat, exclusive, False, 0, None, "",
            "单成员组: qB 直接搬迁, 不需要别名(阈值与链接能力不参与判定)"
        )

    # ---- 2. 文件级链接可建性(能力 + 长路径校正) ----
    file_ok = file_link_kind is not None
    file_reason = file_link_error
    if file_ok and file_link_kind == "symlink" and link_path_limit is not None:
        longest = max(len(_join(save_path, f)) for f in names)
        if longest >= link_path_limit:
            file_ok = False
            file_reason = (
                f"路径过长({longest} 字符 >= {link_path_limit}): Windows 上文件级符号链接建不出来 "
                "(实测 259 可建、260 起一律 WinError 1314, 带 \\\\?\\ 前缀同样失败)"
            )
    # 目录别名可建性(能力 + 内容根路径长度)
    dir_ok = dir_link_kind is not None and exclusive
    dir_reason = dir_link_error
    if dir_ok and _too_long(content_root, link_path_limit):
        dir_ok = False
        dir_reason = (dir_reason + " " if dir_reason else "") + \
            f"内容根路径过长({len(content_root)} 字符 >= {link_path_limit}), 目录别名也建不出来"

    def _dir_alias_proposal(reason: str) -> RelocateUnitPlan:
        return RelocateUnitPlan(
            FORM_DIR_ALIAS, count, content_root, rel, flat, exclusive, True, 1, dir_link_kind,
            FORM_FILE_LINKS if file_link_kind is not None else "", reason + " —— 提议目录别名(需确认「该目录以后新增的种子也会落到新位置」; 不确认则拒绝)"
        )

    if not file_ok:
        # 能力校正(先于阈值): 文件级链接建不出来, 目录别名可行才提议
        if dir_ok:
            return _dir_alias_proposal(file_reason or "文件级链接不可建")
        why = [r for r in (file_reason, dir_reason if exclusive else "") if r]
        return RelocateUnitPlan(
            FORM_REJECT, count, content_root, rel, flat, exclusive, False, 0, None, "",
            "拒绝: " + "; ".join(why) + " —— 既不静默留裸奔状态, 也不猜测; 出路: 换同卷目标 / 缩短路径 / 先迁走同目录其它种子"
        )

    # ---- 3. 阈值分流 ----
    if count < threshold:
        return RelocateUnitPlan(
            FORM_FILE_LINKS, count, content_root, rel, flat, exclusive, False, count, file_link_kind, "",
            f"文件数 {count} < 阈值 {threshold}: 逐文件链接(对未来种子零影响)"
        )
    if dir_ok:
        return _dir_alias_proposal(f"文件数 {count} >= 阈值 {threshold} 且内容根目录专属")

    # ---- 4. hard_max 防护 ----
    if count > hard_max:
        why = f"文件数 {count} 超过逐文件链接硬上限 {hard_max}"
        if exclusive and dir_link_kind is None:
            why += f", 且目录别名不可用({dir_link_error or '未探测到可用形态'})"
        return RelocateUnitPlan(
            FORM_REJECT, count, content_root, rel, flat, exclusive, False, 0, None, "",
            f"拒绝: {why} —— 避免链接爆炸; 出路: 换更专属的目标布局 / 提高 hard_max_links"
        )
    return RelocateUnitPlan(
        FORM_FILE_LINKS, count, content_root, rel, flat, exclusive, False, count, file_link_kind, "",
        f"文件数 {count} >= 阈值 {threshold} 但目录别名不适用"
        f"({'平铺布局, 整目录别名不提供' if flat else '目录不专属(含组外文件/杂项)'}): 逐文件链接"
    )


# ---------------------------------------------------------------- job 登记(§3.5)


@dataclass(frozen=True)
class RelocateJob:
    """一个在途迁移的登记值对象(state.json relocate.jobs.<job_id> 的镜像; P3 落账)

    两本账(§3.5): state 只由主循环线程写(auto-qb), guardian 只写自己的 journal ——
    本类只是判定侧读的那一份。字段口径与相位机同 §3.5; alias_kind: "file" | "dir" | ""
    (direct 无别名); scope 是**内容根目录**(作用域按「save_path == src 且内容根落在
    scope 内」判定, 不按 hash 列表 —— D7: 别名是作用域不是快照)。
    """

    job_id: str
    hashes: Tuple[str, ...]
    mover: str
    src: str
    dst: str
    scope: str
    alias_kind: str = ""
    alias_paths: Tuple[str, ...] = ()
    phase: str = PHASE_MOVING
    reason: str = ""
    armed_at: float = 0.0
    updated_at: float = 0.0
    resume_hashes: Tuple[str, ...] = ()
    attempts: int = 0
    last_error: str = ""
    # 执行计划快照(P3 落账, 供重启后继续执行与 P6 收尾): {form, link_kind, scope,
    # files: [[相对路径, 大小], ...]}。不进纯判定, 只作恢复用事实。
    plan: Optional[dict] = None
    # 是否已向 qB 下发过 setLocation(P3 落账, 供重启恢复判据消费): 账先落 state、指令后发
    # (§3.5.1), 两步之间崩溃时这一位仍是 False —— 「qB 从未收到搬迁」在 qB 侧与「下发了
    # 但没动静」不可分辨, 只有账上这一位能把两者分开, 重启据此补发一次而非静默等停滞超时。
    move_issued: bool = False

    @property
    def is_terminal(self) -> bool:
        return self.phase in TERMINAL_PHASES

    @property
    def scope_covers_dir(self) -> bool:
        """作用域是否**覆盖整个目录**(目录别名形态才是)

        逐文件链接/直搬的 scope 只是 save_path(平铺内容根)或组自己的内容根 —— 别名只挂在
        组内文件上, **不会**把落进同目录的别组读写重定向到 T, 故作用域覆盖语义不成立。
        P7 真机实测(s3 步): 平铺逐文件链接组③ 的 scope = 整个 save_path, 旧实现让
        scope_hit 把同目录别组(A/B)的组键解析到 T —— job 结束后 _buckets 用 S 键查不到,
        退化为「仅本次选中成员」→ 单成员 direct 误判(数据被搬走却不建链接, 组裂);
        finalize_members 同样会把同目录别组一并 setLocation 到 T。两处都靠本谓词收窄。
        """
        return (self.plan or {}).get("form") == FORM_DIR_ALIAS

    def touches(self, hashes: Sequence[str]) -> bool:
        """本组(这些 hash)是否被该 job 碰过(成员交集)"""
        return bool(set(self.hashes) & set(hashes))

    def scope_hit(self, save_path: str, landing: str) -> bool:
        """落点是否命中该 job 的作用域(src 匹配且 landing 落在 scope 内)

        目录别名: 落在 scope 目录内(含等于)即命中 —— 整条链接重定向整目录。
        逐文件链接: 只认 landing **恰等于** scope(平铺组的内容根就是 save_path,
        它自己的成员才该并组), 子目录里的别组不命中。
        直搬(direct): **恒不命中** —— 没有建任何别名, 作用域不覆盖任何落点(P7 真机:
        组② 的直搬 job scope = 恶女目录, 旧逻辑把同目录的组① 也解析到 T, 组键漂移后
        _buckets 查不到组, 误判单成员直搬)。

        形态判据优先 alias_kind(落账字段, 历史/测试构造的 job 可能没有 plan), plan.form 兜底。
        """
        if _norm(save_path) != _norm(self.src):
            return False
        kind = self.alias_kind or {"dir_alias": "dir", "file_links": "file"}.get((self.plan or {}).get("form"), "")
        if kind == "dir":
            return _within(self.scope, landing)
        if kind == "file":
            return _norm(landing) == _norm(self.scope)
        return False

    def blocks_relocation(self, hashes: Sequence[str], content_root: str) -> bool:
        """本 job 是否挡住对(这些 hash 组成的)组的再次迁移(§3.6 第 14 行 / S10)

        非终态且成员相交 ⇒ 挡(同组再迁, 链接套链接让旧 job 收尾失效, 必须先收尾或先撤销)。
        作用域覆盖分支**只对目录别名成立**: 目录别名是一条挂在内容根的 junction/symlink,
        落入该目录的写入会被整体重定向到 T —— 同目录别组此刻再迁, 数据会穿链接搬进旧
        job 的目标、与收尾语义冲突(P7 真机 S14b 实测: 逐文件链接组③ 的 scope = save_path
        (平铺内容根), 旧实现把同 save_path 下的无关组 C 一并挡下, 与 §08「多选按组拆开
        各迁各的」相悖)。逐文件链接只挂在组内文件上、不改变目录形态, 无重定向 hazard,
        故不适用本分支; direct 单成员组同理(无别名即无链接可套)。
        """
        if self.is_terminal:
            return False
        if self.touches(hashes):
            return True
        if (self.plan or {}).get("form") == FORM_DIR_ALIAS:
            return _within(self.scope, content_root)
        return False


# ---------------------------------------------------------------- 组闸门判定()


@dataclass(frozen=True)
class GroupFacts:
    """一个组(同内容种子集合)的只读事实包 —— 由 relocate_mod 收集, 本文件只判定

    字段口径:
    - files: (相对路径, 大小) 元组(qB files API 口径, 正斜杠); 组内共享同一份物理
      文件, needed = 文件大小总和(一份拷贝)。
    - progresses/states: 与 hashes 同序的成员事实。
    - content_root_exclusive: 内容根恰好只含本组文件(目录别名的硬前提, §3.2); None =
      不可判定(目录不存在/读不了) —— 按不专属处理(保守)。
    - misc_entries/external_entries/qb_temp_entries: 内容根 listing 的分类结果
      (杂项 = 不属于任何种子; 组外 = 属于别的种子; .!qB = qB 临时文件)。
    - target_conflicts: 目标侧已存在的同名路径(任一命中 qB 就走 need_full_check)。
    - same_volume: 源/目标是否同卷(None = 不可判定, 按跨卷保守处理)。
    - target_free: 目标卷剩余字节(None = 不可判定 ⇒ space 闸门拒绝)。
    - same_fs_proved: §2.4 同卷证明(qB 上报 free_space_on_disk 与本机源卷剩余**相等**)。
    - file_link_kind/dir_link_kind: alias_fs 能力探测 + 同卷判定后的可用形态(None = 不可用)。
    - jobs: 活跃 job 视图(模块侧给非终态; 这里仍自查终态)。
    - link_path_limit: 链接路径长度上限(Windows 260 / POSIX None)。
    """

    hashes: Tuple[str, ...]
    mover: str
    name: str
    save_path: str
    target: str
    files: Tuple[Tuple[str, int], ...]
    progresses: Tuple[float, ...] = ()
    states: Tuple[str, ...] = ()
    content_root_exclusive: Optional[bool] = None
    misc_entries: Tuple[str, ...] = ()
    external_entries: Tuple[str, ...] = ()
    qb_temp_entries: Tuple[str, ...] = ()
    target_conflicts: Tuple[str, ...] = ()
    target_unknown: bool = False
    same_volume: Optional[bool] = None
    target_free: Optional[int] = None
    same_fs_proved: bool = False
    capability_ok: bool = True
    capability_reason: str = ""
    file_link_kind: Optional[str] = None
    file_link_error: str = ""
    dir_link_kind: Optional[str] = None
    dir_link_error: str = ""
    jobs: Tuple[RelocateJob, ...] = ()
    link_path_limit: Optional[int] = None
    threshold: int = 8
    hard_max: int = 2000
    third_party_link_files: Tuple[str, ...] = ()
    hardlink_files: Tuple[str, ...] = ()
    third_party_dir_note: str = ""


def _reason(gate: str, cls: str, text: str) -> dict:
    return {"gate": gate, "cls": cls, "text": text}


def evaluate_group(facts: GroupFacts) -> dict:
    """组级迁移预检: 闸门全跑 + 形态分流, 产出 WEB 回执同形 item(只读, 零副作用)

    cls 三分流: blocked(硬拒) > confirm(需用户在确认框显式点头: 目录别名/长路径校正
    提议) > ok。reasons 只放未过闸门与需确认项; notes 放告知性事实(不影响 cls)。
    """
    reasons: list = []
    notes: list = []
    cls = CLS_OK
    names = [n for n, _s in facts.files]
    needed = sum(s for _n, s in facts.files)
    multi = len(facts.hashes) > 1
    flat, rel = layout_of(facts.save_path, names)
    content_root = _join(facts.save_path, rel) if rel else facts.save_path

    def _block(gate: str, text: str) -> None:
        nonlocal cls
        reasons.append(_reason(gate, CLS_BLOCKED, text))
        cls = CLS_BLOCKED

    def _confirm(gate: str, text: str) -> None:
        nonlocal cls
        reasons.append(_reason(gate, CLS_CONFIRM, text))
        if cls != CLS_BLOCKED:
            cls = CLS_CONFIRM

    # ---- 未收尾拦截(先于一切: §3.6 第 14 行 / S10) ----
    for job in facts.jobs:
        if job.blocks_relocation(facts.hashes, content_root):
            _block(
                GATE_UNFINISHED, f"该组有未收尾的迁移(job {job.job_id} 相位 {job.phase}): 收尾完成或撤销后才能再次迁移, "
                "否则链接套链接会让旧迁移的收尾失效"
            )
            break

    # ---- 幂等: 全组已在目标位置(§05 T3; 目标冲突等闸门对同路径无意义, 直接返回) ----
    if _norm(facts.save_path) == _norm(facts.target):
        notes.append("所有成员已在目标位置(幂等): 规则 move_to 语义为 skip, 无需迁移")
        return {
            "hashes": list(facts.hashes),
            "mover": facts.mover,
            "name": facts.name,
            "save_path": facts.save_path,
            "target": facts.target,
            "file_count": len(names),
            "form": FORM_DIRECT,
            "alias_kind": None,
            "link_count": 0,
            "needs_confirm": False,
            "cls": cls,
            "reasons": reasons,
            "notes": notes,
            "target_free": facts.target_free,
            "same_volume": facts.same_volume,
        }

    # ---- 完成度 / qB 搬迁态 ----
    for h, p in zip(facts.hashes, facts.progresses):
        if p is not None and p < 1:
            _block(GATE_INCOMPLETE, f"成员 {h[:8]} 尚未完成(progress={p:.0%}): 免重启迁移只面向已完成的辅种组 "
                   "(未完成成员的进度与统计经不起别名的间接读写)")
            break
    for h, st in zip(facts.hashes, facts.states):
        if st and "moving" in str(st).lower():
            _block(GATE_MOVING, f"成员 {h[:8]} 正处于 qB 搬迁态({st}): 等本次搬迁结束后再发起(排队下发会互相覆盖)")
            break

    # ---- 目标冲突 / .!qB / 空间 ----
    if facts.target_conflicts:
        _block(
            GATE_TARGET_CONFLICT, "目标已存在同名内容(" + ", ".join(facts.target_conflicts[:3]) + "): qB 会走全量校验"
            "(进度清零), 请先清理目标或改迁别处"
        )
    if facts.target_unknown:
        _block(GATE_TARGET_UNKNOWN, "目标路径存在性不可判定(容器映射未覆盖): 不可判定一律拒绝 —— 请检查 fs.path_map 是否覆盖目标位置")
    if facts.qb_temp_entries:
        _block(GATE_QB_TEMP, "内容根存在 .!qB 临时文件(" + ", ".join(facts.qb_temp_entries[:3]) + "): 数据尚未落定, 不能迁")
    if facts.target_free is None:
        _block(GATE_SPACE, "目标卷剩余空间不可判定(路径不可读或容器映射未覆盖): 不可判定一律拒绝")
    elif facts.target_free < needed:
        _block(GATE_SPACE, f"目标卷剩余 {facts.target_free} 字节 < 本组数据 {needed} 字节: 空间不足, 拒绝迁移")

    # ---- 同卷证明 + 平台能力(多成员组需要 qB 能读到本机建的链接) ----
    if not facts.same_fs_proved:
        text = ("无法证明 auto-qb 与 qB 看到同一块盘(qB 上报的剩余空间与本机源卷不一致或读不到): "
                "远程 qB 或容器路径错位下, 本机建的链接 qB 读不了")
        if multi:
            _block(GATE_SAME_FS, text + " —— 只有独占情形(单成员组)可迁移")
        else:
            notes.append(text + " —— 独占情形由 qB 自行搬运, 目标冲突/空间未预检")
    if not facts.capability_ok:
        text = facts.capability_reason or "无法建出 qB 能读的链接"
        if multi:
            _block(GATE_PLATFORM, text)
        else:
            notes.append(text + " —— 独占情形不需要别名, 不受影响")

    # ---- 第三方链接与硬链接识别(D11: 文件级与硬链接拒迁; 目录级只识别) ----
    if facts.third_party_link_files:
        _block(
            GATE_THIRD_PARTY_LINK, "组文件是第三方文件级链接(" + ", ".join(facts.third_party_link_files[:3]) + "): qB 搬走的是"
            "链接本身, 数据留在原地, 种子反而指向悬空链接 —— 请先在整理工具侧处理"
        )
    if facts.hardlink_files:
        _block(
            GATE_HARDLINK, "组文件是硬链接(" + ", ".join(facts.hardlink_files[:3]) + "): qB 会复制出一份新数据并让去重失效"
            " —— 请改迁物理本体(执行期可显式强制)"
        )
    if facts.third_party_dir_note:
        notes.append(facts.third_party_dir_note)

    # ---- 形态分流(plan 纯函数; 结果映射到 cls) ----
    unit = plan(
        facts.save_path,
        names,
        facts.threshold,
        facts.hard_max,
        multi_member=multi,
        content_root_exclusive=facts.content_root_exclusive,
        file_link_kind=facts.file_link_kind,
        file_link_error=facts.file_link_error,
        dir_link_kind=facts.dir_link_kind,
        dir_link_error=facts.dir_link_error,
        link_path_limit=facts.link_path_limit,
    )
    if unit.form == FORM_REJECT:
        _block(GATE_FORM, unit.reason)
    elif unit.needs_confirm:
        _confirm(GATE_FORM, unit.reason)

    # ---- 告知性 notes ----
    if facts.target_free is not None:
        notes.append(f"目标卷剩余 {facts.target_free} 字节; 本组数据 {needed} 字节")
    if facts.same_volume is True:
        notes.append("源与目标同卷: qB 走 rename, 不实际占用额外空间(预检仍按目标卷剩余展示)")
    elif facts.same_volume is False:
        notes.append("源与目标跨卷: qB 走复制; 逐文件别名将使用符号链接")
    elif facts.same_volume is None:
        notes.append("源/目标卷关系不可判定: 按跨卷保守处理")
    if facts.misc_entries:
        notes.append("内容根含非种子杂项(只链路本组文件, 不动杂项): " + ", ".join(facts.misc_entries[:5]))
    if facts.external_entries:
        notes.append("内容根含组外种子的文件(目录别名不可用, 只链路本组文件): " + ", ".join(facts.external_entries[:5]))

    return {
        "hashes": list(facts.hashes),
        "mover": facts.mover,
        "name": facts.name,
        "save_path": facts.save_path,
        "target": facts.target,
        "file_count": len(names),
        "form": unit.form,
        "alias_kind": unit.link_kind,
        "link_count": unit.link_count,
        "needs_confirm": unit.needs_confirm,
        "cls": cls,
        "reasons": reasons,
        "notes": notes,
        "target_free": facts.target_free,
        "same_volume": facts.same_volume,
    }


# ---------------------------------------------------------------- 添加种子预检(§3.6.1)


@dataclass(frozen=True)
class AddFacts:
    """precheck-add 的只读事实包: 添加对话框提交前的落点预检(§3.6 第 1/3/8/15 行)"""

    save_path: str
    name: str
    jobs: Tuple[RelocateJob, ...] = ()
    landing_is_link: bool = False
    landing_link_kind: Optional[str] = None
    landing_link_target: Optional[str] = None
    target_free: Optional[int] = None


def evaluate_add(facts: AddFacts) -> dict:
    """往别名作用域添加种子的三分流(ok=无影响 / confirm=弹「请求路径→实际落点→卷剩余」二次确认)

    落点 = save_path/内容根(种子名)。判定顺序(§3.6 行号):
    1. 收尾窗口(链接已删、qB 未起/未 finalize): 新种子落原盘, 可能与 T 侧旧数据重复 ⇒ confirm;
    2. 目录别名作用域命中: 一切落点被重定向到 T ⇒ confirm(展示实际落点与目标卷剩余);
    3. 逐文件链接: 只有落点**本身就是链接**(同名)才 confirm(写入将覆盖 T 侧数据);
       异名落原盘真实目录, 无影响(row 1) ⇒ ok;
    4. 落点是链接但无 job 登记(第三方): confirm 警示;
    5. 其余 ok。
    """
    landing = _join(facts.save_path, facts.name)
    base = {
        "save_path": facts.save_path,
        "name": facts.name,
        "requested_path": landing,
        "actual_path": None,
        "volume_free": None,
    }

    # ---- 1. 收尾窗口 ----
    for job in facts.jobs:
        if job.is_terminal:
            continue
        if job.phase in FINALIZE_WINDOW_PHASES and _norm(facts.save_path) == _norm(job.src):
            return {
                **base,
                "cls": CLS_CONFIRM,
                "reasons":
                    [
                        _reason(
                            "finalize_window", CLS_CONFIRM,
                            f"该目录的迁移正在收尾(job {job.job_id} 相位 {job.phase}, 旧链接已删): 现在添加会落在"
                            "原盘, 可能与已迁到新位置的数据重复 —— 等 qB 重启完成收尾, 或确认重复后继续"
                        )
                    ],
                "notes": [],
            }

    # ---- 2/3. 别名作用域 ----
    # !这里用「落点是否落在作用域目录内」的本地判定, **不用** job.scope_hit: scope_hit 是
    # 组键解析语义(平铺 job 只认 landing == scope, 见 scope_covers_dir), 而添加预检问的是
    # 「这次写入会不会被别名带走」—— 文件级别名下, 落点(具体文件路径)在内容根内且同名
    # 是链接即命中(gate 3 的 landing_is_link 才是真闸门, 本判定只决定提示口径)。
    for job in facts.jobs:
        if job.is_terminal:
            continue
        if _norm(facts.save_path) != _norm(job.src) or not _within(job.scope, landing):
            continue
        if job.alias_kind == "dir":
            sp = facts.save_path.replace("\\", "/").rstrip("/")
            rel = landing[len(sp):].lstrip("/") if landing.startswith(sp + "/") else ""
            actual = _join(job.dst, rel)
            return {
                **base,
                "cls": CLS_CONFIRM,
                "actual_path": actual,
                "volume_free": facts.target_free,
                "reasons":
                    [
                        _reason(
                            "alias_scope", CLS_CONFIRM, f"该目录已迁移到 {job.dst}(目录别名): 新种子将落到 {actual} 而非请求路径 —— "
                            "如这是有意的请确认继续; 取消则不改动落点"
                        )
                    ],
                "notes": [f"目标卷剩余 {facts.target_free} 字节" if facts.target_free is not None else "目标卷剩余不可判定"],
            }
        if facts.landing_is_link:
            return {
                **base,
                "cls": CLS_CONFIRM,
                "actual_path": facts.landing_link_target,
                "volume_free": facts.target_free,
                "reasons":
                    [
                        _reason(
                            "alias_file", CLS_CONFIRM, "该路径当前是迁移别名链接: 写入将直接覆盖已迁到新位置的数据"
                            "(同名不同内容会损坏原组数据) —— 确认是同内容辅种再继续"
                        )
                    ],
                "notes": [],
            }
        # 异名落原盘真实目录: 无影响(§3.6 第 1 行)
        return {**base, "cls": CLS_OK, "reasons": [], "notes": ["落在原盘真实目录, 与别名作用域无交叉"]}

    # ---- 4. 落点本身是链接(无 job 登记: 第三方链接) ----
    if facts.landing_is_link:
        return {
            **base,
            "cls": CLS_CONFIRM,
            "actual_path": facts.landing_link_target,
            "volume_free": facts.target_free,
            "reasons":
                [
                    _reason(
                        "alias_path", CLS_CONFIRM,
                        f"该路径当前是一条链接({facts.landing_link_kind} -> {facts.landing_link_target}): "
                        "添加将写入链接目标而非请求路径"
                    )
                ],
            "notes": [],
        }
    return {**base, "cls": CLS_OK, "reasons": [], "notes": []}


# ---------------------------------------------------------------- 同卷证明(§2.4)


def same_volume_proof(qb_free: Optional[int], local_free: Optional[int]) -> bool:
    """§2.4 同卷证明: qB 上报的 free_space_on_disk 与本机源卷剩余**同量级**才算同盘

    任一侧读不到(未同步/容器) ⇒ False(不可判定 ⇒ 按不同盘处理, 保守)。证据口径来自
    §2.4 真机实测(两侧完全相等), 但作为**闸门**必须带写盘抖动容差: qB 上报与本机读取
    之间隔着一个同步周期, 期间任何写盘都会让剩余空间漂移 —— 完全相等做判据必然间歇性
    误拒(实测并行写盘下漂移即可触发)。容差 = max(2% 相对, 1GiB 绝对): 真不同盘的剩余
    空间通常差数量级, 不会落进容差带。
    """
    if qb_free is None or local_free is None:
        return False
    tolerance = max(1 << 30, int(local_free * 0.02))
    return abs(qb_free - local_free) <= tolerance


# ---------------------------------------------------------------- job 落账与恢复(P3/P6)


def job_id_for(mover: str, dst: str, src: str = "") -> str:
    """job_id = (mover, src, dst) 的稳定摘要 —— 同组同目标重复发起落同一条(幂等)

    不做时间戳: 同一组迁到同一目标的第二次发起应在「未收尾拦截」闸门被挡(S10),
    而不是靠 id 不同绕过; 同一 job 的重复 execute 命中同一条, 不产生第二份账。
    """
    import hashlib

    raw = f"{mover}|{src}|{dst}"
    return "jr-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def job_to_dict(job: RelocateJob) -> dict:
    """job -> state.json 落账形态(纯数据: 元组转 list, 供 JSON 序列化)"""
    return {
        "job_id": job.job_id,
        "hashes": list(job.hashes),
        "mover": job.mover,
        "src": job.src,
        "dst": job.dst,
        "scope": job.scope,
        "alias_kind": job.alias_kind,
        "alias_paths": list(job.alias_paths),
        "phase": job.phase,
        "reason": job.reason,
        "armed_at": job.armed_at,
        "updated_at": job.updated_at,
        "resume_hashes": list(job.resume_hashes),
        "attempts": job.attempts,
        "last_error": job.last_error,
        "plan": job.plan,
        "move_issued": job.move_issued,
    }


def job_from_dict(d) -> Optional[RelocateJob]:
    """state.json 条目 -> RelocateJob; 形状不符/缺 job_id 返回 None(坏条目跳过, 不炸)"""
    if not isinstance(d, dict) or not d.get("job_id"):
        return None
    try:
        return RelocateJob(
            job_id=str(d["job_id"]),
            hashes=tuple(d.get("hashes") or ()),
            mover=str(d.get("mover") or ""),
            src=str(d.get("src") or ""),
            dst=str(d.get("dst") or ""),
            scope=str(d.get("scope") or ""),
            alias_kind=str(d.get("alias_kind") or ""),
            alias_paths=tuple(d.get("alias_paths") or ()),
            phase=str(d.get("phase") or PHASE_MOVING),
            reason=str(d.get("reason") or ""),
            armed_at=float(d.get("armed_at") or 0.0),
            updated_at=float(d.get("updated_at") or 0.0),
            resume_hashes=tuple(d.get("resume_hashes") or ()),
            attempts=int(d.get("attempts") or 0),
            last_error=str(d.get("last_error") or ""),
            plan=d.get("plan") if isinstance(d.get("plan"), dict) else None,
            move_issued=bool(d.get("move_issued")),
        )
    except (TypeError, ValueError):
        return None


def content_root_of(save_path: str, files: Sequence[str]) -> str:
    """内容根路径(目录别名的作用域; 平铺/混合 = save_path 本身)"""
    _flat, rel = layout_of(save_path, files)
    return _join(save_path, rel) if rel else save_path


def resolve_physical(save_path: str, content_root: str, jobs: Sequence[RelocateJob]) -> str:
    """三层物理位置解析之**第 1 层**: 自有 job 作用域登记表(零 syscall, §3.4)

    逐文件链接不改变目录 realpath, 故组键必须靠登记表才能把「还指着 S 的成员」与
    「已被 qB 搬到 T 的 mover」并成同一组 —— 解析命中返回 dst, 未命中原样返回
    (与今天逐字节一致, 开关关/无 job 时零行为差)。
    """
    for job in jobs:
        if job.is_terminal:
            continue
        if job.scope_hit(save_path, content_root):
            return job.dst
    return save_path


def finalize_members(job: RelocateJob, members: Sequence[Tuple[str, str, str]]) -> Tuple[str, ...]:
    """动态收尾集合(§3.5 / D7: 别名是作用域不是快照)

    members = [(hash, save_path, content_root), ...]; 集合 = 创建时 hashes ∪
    「当前 save_path == src 且内容根落在 scope 内」的所有成员, mover 已在 dst 故跳过。
    别名期间新加的同内容辅种因此自动纳入 —— 不会留「收尾后新成员留在原地、
    链接已删 ⇒ 缺文件」的坑。

    作用域覆盖分支只对**目录别名**成立(scope_covers_dir): 逐文件链接/直搬的 scope 是
    平铺 save_path, 覆盖整目录会把同目录别组一并 setLocation 到 T(P7 真机实测, 见
    scope_covers_dir) —— 那类 job 只收自己的成员(创建时 hashes)。
    """
    out = []
    seen = set()
    covers = job.scope_covers_dir
    for h, sp, root in members:
        if h == job.mover or h in seen:
            continue
        if h in job.hashes or (covers and _norm(sp) == _norm(job.src) and _within(job.scope, root)):
            seen.add(h)
            out.append(h)
    return tuple(out)


# ---------------------------------------------------------------- 停滞判据与执行期恢复(P3)

STALL_OK = "ok"  # 正常搬运中
STALL_WARN = "warn"  # 超过 move_warn_after 仍在搬: 只提示, 不判失败
STALL_FAILED = "stalled"  # 停滞: dst 不增长且 qB 不在 moving 超过 move_stall_timeout


def stall_verdict(
    sample_grew: bool, qb_moving: bool, elapsed: float, warn_after: float, stall_timeout: float, stalled_for: float
) -> str:
    """停滞判据(D12/D13): 不做墙钟超时 —— 长耗时只提示, 只有「停滞」才判失败

    - qB 在 moving ⇒ 永远不判失败(几十 GB~TB 级搬运可能远超预期, 等得久不是失败理由);
      超过 warn_after ⇒ warn(转 watching, 界面显示「已超预期时间」)。
    - 不在 moving 且 dst 体积不增长 ⇒ 累计 stalled_for; 超过 stall_timeout ⇒ stalled。
    """
    if qb_moving:
        return STALL_WARN if elapsed >= warn_after else STALL_OK
    if sample_grew:
        return STALL_WARN if elapsed >= warn_after else STALL_OK
    if stalled_for >= stall_timeout:
        return STALL_FAILED
    return STALL_WARN if elapsed >= warn_after else STALL_OK


RECOVER_POLL = "poll"  # qB 仍在搬(moving): 继续轮询, 不重新下发
RECOVER_RESUME = "resume"  # save_path 已到 dst: 补做 moved 之后的步骤
RECOVER_STALLED = "failed_stalled"  # 已不在 moving 且 dst 无数据/部分数据: 失败, 现场保留


def recover_exec_phase(qb_moving: bool, save_path_at_dst: bool, dst_has_data: bool) -> str:
    """执行期崩溃恢复(phase ∈ {moving, moved}, guardian 尚未武装, journal 可能不存在)

    只按 qB 现场判(§3.5): moving ⇒ 继续轮询(不重发 setLocation, 会排队/覆盖);
    save_path==dst ⇒ 补做后续; 否则按停滞失败(现场保留, 不搬回)。
    """
    if qb_moving:
        return RECOVER_POLL
    if save_path_at_dst or dst_has_data:
        return RECOVER_RESUME
    return RECOVER_STALLED


# ---------------------------------------------------------------- 对账表(P6, §3.5)

ACT_WAIT = "wait"  # 等(含 guardian 心跳正常 / qB 未起)
ACT_RESPAWN = "respawn_guardian"  # guardian 心跳过期 ⇒ 重拉
ACT_REDELETE = "reguardian_delete"  # removing + 链接在 + qB 不在 ⇒ guardian 重删(不在则重拉)
ACT_REVERT_INTENT = "revert_intent"  # removing + 链接在 + qB 回来了 ⇒ 撤销删除意图回 armed
ACT_REBUILD = "rebuild_links"  # 链接不在 + qB 在 + 种子正常 ⇒ 重建链接回 armed
ACT_FINALIZE = "finalize"  # 链接不在 + qB 在 + missingFiles ⇒ setLocation 收尾
ACT_FAILED_GONE = "failed_gone"  # 种子已不存在(用户删了): failed, 保留链接现场交人
ACT_FAILED_TIMEOUT = "failed_timeout"  # 超过 finalize_timeout 仍未收尾: failed
ACT_DONE_EXTERNAL = "done_external"  # 已被外部完成(save_path==dst): done

GUARDIAN_HEARTBEAT_MAX_AGE = 60.0  # guardian 心跳过期判据(§3.5 对账表第 1 行)

# 重试退避与上限(防无界重试): 建链必失败的环境(权限不足 / 未开 Windows 开发者模式且
# allow_uac 关 —— 预检文案自己点名的常见环境)里, 「REMOVED(alias_partial) → 对账
# REBUILD → 置 MOVED 重建 → 再失败」会每 1-2 个 tick 一轮 create-fail-delete 且永不终态
# (WARNING 约 4s 一条刷屏); guardian 心跳一过期就每 tick 重拉一次进程同理。这类失败不是
# 抖动, 靠退避拉开间隔 + 达到上限转 failed 留现场才能收敛。
# 取常量而非配置键: 这是执行体的内部节拍(与 GUARDIAN_HEARTBEAT_MAX_AGE 同档), 不是用户
# 该调的策略面 —— 重试次数由 job.attempts 记账(落 state, 重启不丢)。
REBUILD_MAX_ATTEMPTS = 3  # 重建链接的重试上限(超出 ⇒ failed 留现场交人)
REBUILD_BACKOFF = 300.0  # 秒; 两次重建之间的最小间隔
RESPAWN_BACKOFF = 60.0  # 秒; 两次 guardian 拉起之间的最小间隔(与心跳过期判据同档)


def reconcile(
    job: RelocateJob,
    *,
    journal_phase: str = "",
    link_present: bool = True,
    qb_up: bool = True,
    seed_state: str = "normal",
    save_path_at_dst: bool = False,
    heartbeat_age: float = 0.0,
    elapsed: float = 0.0,
    finalize_timeout: float = 0.0,
) -> str:
    """§3.5 对账表: (journal 相位, 链接在?, qB 在?, 种子态) -> 处置动作(纯函数)

    收尾的充分条件是**证据**而非事件 —— 不检测「qB 是否重启过」, qB 在线 + 种子
    missingFiles + save_path==src + 链接不在 即充分。seed_state 取值:
    "normal" / "missingFiles" / "gone"。
    """
    if seed_state == "gone":
        return ACT_FAILED_GONE
    if link_present and qb_up and save_path_at_dst:
        return ACT_DONE_EXTERNAL
    if journal_phase in (PHASE_REMOVING, PHASE_REMOVED) and not link_present:
        if not qb_up:
            return ACT_FAILED_TIMEOUT if (finalize_timeout and elapsed > finalize_timeout) else ACT_WAIT
        return ACT_FINALIZE if seed_state == "missingFiles" else ACT_REBUILD
    if journal_phase == PHASE_REMOVING and link_present:
        return ACT_REVERT_INTENT if qb_up else ACT_REDELETE
    if link_present:
        return ACT_RESPAWN if heartbeat_age > GUARDIAN_HEARTBEAT_MAX_AGE else ACT_WAIT
    # 链接不在且无 removing/removed 意图: 现场已变(qB 在且种子正常 ⇒ 重建; 否则等)
    if qb_up and seed_state == "missingFiles":
        return ACT_FINALIZE
    if qb_up:
        return ACT_REBUILD
    return ACT_FAILED_TIMEOUT if (finalize_timeout and elapsed > finalize_timeout) else ACT_WAIT
