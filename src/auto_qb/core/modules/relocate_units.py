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
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

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

# 闸门 id(稳定字符串: 测试与前端按它断言, 改文案不改 id)。执行侧一次性回执 gate
# (param/unavailable/pause_failed/dry_run/cost 等内联字面量)历来字面量属基线豁免, 不收进本块。
GATE_GONE = "gone"  # 种子已不在客户端
GATE_DISABLED = "disabled"  # relocate.enabled=false(纵深防御, 路由层已 403)
GATE_UNFINISHED = "unfinished"  # 已有未收尾迁移碰本组(§3.6 第 14 行 / S10; D15 收窄后只拦前段相位)
GATE_ALIAS_BUSY = "alias_busy"  # S5 搬前预检加项: 前任别名重建可行性(句柄占用)探测未过, 整体拒绝(D20)
GATE_INCOMPLETE = "incomplete"  # 组内存在未完成成员(progress < 1)
GATE_MOVING = "moving"  # 成员正处于 qB 搬迁态(state 含 moving)
GATE_TARGET_CONFLICT = "target_conflict"  # 目标已存在同名内容(qB 会走全量校验)
GATE_TARGET_UNKNOWN = "target_unknown"  # 目标路径存在性不可判定(容器映射 miss)
GATE_TARGET_TYPE = "target_type"  # 目标路径已存在但不是目录(qB 无法在其下创建内容, R2 #3)
GATE_QB_TEMP = "qb_temp"  # 本组文件处于 .!qB 未落定态(外组/无主 .!qB 降 notes: qB 逐文件搬运碰不到, plan 26-11-02-0134)
GATE_SPACE = "space"  # 目标卷剩余不足 / 不可判定
GATE_SAME_FS = "same_fs"  # 确定性不共享(路径级证据判负, P3; 未证明不再硬拦 —— 执行链强探测兜底)
GATE_PLATFORM = "platform"  # §3.3 能力矩阵不支持(跨 OS 容器 / 无链接能力)
GATE_HARDLINK = "hardlink"  # 组文件是第三方硬链接(st_nlink > 1, D11 拒迁)
GATE_THIRD_PARTY_LINK = "third_party_link"  # 组文件是第三方文件级链接(D11 拒迁)
GATE_FORM = "form"  # 形态分流本身的拒绝/需确认(plan() 产出)
GATE_CANCEL_ALIAS_LEFT = "cancel_alias_left"  # 撤销中止: 残留别名未删净拒绝搬回(exec 侧一次性回执, R1#25 口径)
# fastresume 收尾链(计划 26-11-05-0808 S1)五闸(§3.1 预检行; 嵌套/三态继承 0546 机制判定):
GATE_AUTO_TMM = "auto_tmm"  # 组内有 AutoTMM 成员(fastresume 无 qBt-savePath 键, N8 实测, 改写不生效)
GATE_BACKEND = "backend"  # qB fastresume 存储后端非 Legacy(部署矩阵 E 格: SQLite 无 fastresume 文件, D2/D4 fail-fast 禁用)
GATE_BT_BACKUP = "bt_backup"  # BT_backup 路径未配置/不可达不可写(部署矩阵 D 格)
GATE_NESTED = "nested"  # 嵌套目标: 形态分治 R1-R5(计划 26-11-07-1300)—— DIR_ALIAS 内容根互嵌硬拦 / 在途 job 作用域与目标拦 / 嵌旧声明源 confirm / FILE_LINKS 深嵌 note
GATE_SOURCE_MISSING = "source_missing"  # 源侧三态之缺失: 声明文件原名与 .!qB 孪生都不在(0546 机制1/E2.2 零搬移假成功)
GATE_SOURCE_UNKNOWN = "source_unknown"  # 源侧三态之不可判定: exists 探测判不了(容器映射 miss, 保守拒同 target_unknown 口径)

# job 相位机(计划 26-11-05-0808 S4 相位模型重定义; 主干单向推进, 旁支 terminal):
# 前段(搬迁+建链)三相位保留 —— 新链流程结构不变(setLocation 搬迁 -> 目标校验 -> 建别名
# -> 武装), 武装后进入收尾窗 {armed, rewritten}: armed = 别名在位、成员经别名做种、
# journal 改写账 pending(等 qB 下线窗口); rewritten = 回收 daemon 已把全体成员 fastresume
# 双键改写落盘(journal 相位翻 rewritten), 等 qB 重启加载新路径后由主循环核验+删链推进。
# 旧收尾窗三相位 removing/removed/finalizing(删别名 -> missingFiles -> ACT_FINALIZE 归位)
# 整链退役(0420 证伪); 旧账里的这三个值由 job_from_dict 前向映射到 armed(非终态不丢现场)。
PHASE_MOVING = "moving"
PHASE_WATCHING = "watching"  # moving 的长耗时变体: 仍在搬, 只降频提示, 不判失败
PHASE_MOVED = "moved"
PHASE_ARMED = "armed"
# 与 relocate_journal.PHASE_REWRITTEN 同值配对(协议 owner 在 journal 侧, daemon 写;
# 本侧是相位机判定用镜像 —— 不互相 import, 避免 core/modules <-> infra 反向依赖)
PHASE_REWRITTEN = "rewritten"
PHASE_DONE = "done"
PHASE_FAILED = "failed"
PHASE_CANCELLED = "cancelled"
TERMINAL_PHASES = frozenset({PHASE_DONE, PHASE_FAILED, PHASE_CANCELLED})
# 收尾窗口(D16 变更承重): armed/rewritten 期间数据已在新位置、成员经别名做种 —— 此窗口内
# 往旧根添加非本组种子, 其 save_path 记在旧根, 会成为删链门(等值 OR 前缀)的永久依赖,
# 别名将永不删; evaluate_add 的 confirm 是唯一预防面(§3.6 第 8 行 / D16)。
FINALIZE_WINDOW_PHASES = frozenset({PHASE_ARMED, PHASE_REWRITTEN})
# qB 待收尾标签镜像窗口(计划 26-11-04-1042 P3): 收尾窗全程算「待收尾」, 标签在 armed 时
# 加上、进入终态时摘除; 标签只写不读, 迁移状态判定仍只认 state。(与 FINALIZE_WINDOW_PHASES
# 同集: 收尾窗相位机重定义后标签窗口自动跟随, 保留独立名字以维持镜像语义的可读性。)
PENDING_TAG_PHASES = frozenset(FINALIZE_WINDOW_PHASES)
# 旧账相位前向映射(S4 迁移口径: 运行中的旧 job 遇新代码按终态/非终态映射):
# removing/removed/finalizing 都是旧链收尾窗非终态 -> 统一映射回 armed —— 别名在的照常
# 对账, 已删的由对账 ACT_REBUILD 重建(重建路径幂等), 改写账 pending 交回收 daemon 接管;
# 终态(done/failed/cancelled)与前段(moving/watching/moved)原样保留。
LEGACY_PHASE_MAP = {
    "removing": PHASE_ARMED,
    "removed": PHASE_ARMED,
    "finalizing": PHASE_ARMED,
}

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
    if not s:  # 防御支: _norm 底层 normpath 恒返回 ".", 现实调用不可达; 契约由 _norm 替身直驱用例钉住(issue 26-11-05-0200)
        return False
    return p == s or p.startswith(s + "/")


def _rel_under(path: str, base: str) -> str:
    """path 相对 base 的尾段(词法, 保留原大小写/斜杠形态); 相等或不在 base 之下 -> ""

    比对走 _norm(平台归一口径); 截取按「归一形测长、原形取尾」—— 现实输入(precheck-add
    的 save_path/name 词法拼接)不含 normpath 可折叠段, 归一前后长度恒一致, 尾段大小写
    得以保留; 防御支(折叠发生)返回 ""(调用侧 actual 退化为根本身, 不伪段)。
    """
    n_p, n_b = _norm(path), _norm(base)
    if not n_p or not n_b or n_p == n_b or not n_p.startswith(n_b + "/"):
        return ""
    tail = len(n_p) - len(n_b) - 1
    raw = path.replace("\\", "/").rstrip("/")
    if 0 < tail <= len(raw) and len(raw) == len(n_p):
        return raw[-tail:]
    return ""


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
        return RelocateUnitPlan(FORM_REJECT, 0, content_root, rel, flat, exclusive, False, 0, None, "文件列表为空, 无法判定内容布局")
    if not multi_member:
        return RelocateUnitPlan(
            FORM_DIRECT, count, content_root, rel, flat, exclusive, False, 0, None, "单成员组: qB 直接搬迁, 不需要别名(阈值与链接能力不参与判定)"
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
            reason + " —— 提议目录别名(需确认「该目录以后新增的种子也会落到新位置」; 不确认则拒绝)"
        )

    if not file_ok:
        # 能力校正(先于阈值): 文件级链接建不出来, 目录别名可行才提议
        if dir_ok:
            return _dir_alias_proposal(file_reason or "文件级链接不可建")
        why = [r for r in (file_reason, dir_reason if exclusive else "") if r]
        return RelocateUnitPlan(
            FORM_REJECT, count, content_root, rel, flat, exclusive, False, 0, None,
            "拒绝: " + "; ".join(why) + " —— 既不静默留裸奔状态, 也不猜测; 出路: 换同卷目标 / 缩短路径 / 先迁走同目录其它种子"
        )

    # ---- 3. 阈值分流 ----
    if count < threshold:
        return RelocateUnitPlan(
            FORM_FILE_LINKS, count, content_root, rel, flat, exclusive, False, count, file_link_kind,
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
            FORM_REJECT, count, content_root, rel, flat, exclusive, False, 0, None,
            f"拒绝: {why} —— 避免链接爆炸; 出路: 换更专属的目标布局 / 提高 hard_max_links"
        )
    return RelocateUnitPlan(
        FORM_FILE_LINKS, count, content_root, rel, flat, exclusive, False, count, file_link_kind,
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
    # 设置位置发起时间(job 登记时刻; 与 setLocation 下发同一动作窗口, 供 WebUI「设置时间」展示)。
    # 旧 state 条目缺该字段 = 0.0(无处可考, 前端显示 "—", 不拿 updated_at 冒充)。
    created_at: float = 0.0
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
    # 待收尾标签镜像账(plan 26-11-04-1042 P3 收窄): 仅本 job **成功 add 过**标签后为 True。
    # 终态摘除只对曾 add 的 job 发 remove —— 从未 armed 的 failed/cancelled 不发多余 qB 写。
    # 旧 state 条目缺该位 = False(未加过); 不读 qB 标签反推, 账即事实源。
    tag_on: bool = False
    # 发起入口(web / rule / cli; 旧 state 条目缺失时回落 "unknown") —— 只作展示归属,
    # 不参与任何闸门判定。写入端在 relocate_execute(origin=...); web/rule 调用方各自传值,
    # cli 为保留值(当前树无 CLI 入口, 仅保证跨端落账口径一致)。
    origin: str = "unknown"

    @property
    def is_terminal(self) -> bool:
        return self.phase in TERMINAL_PHASES

    @property
    def scope_covers_dir(self) -> bool:
        """作用域是否**覆盖整个目录**(目录别名形态才是)

        逐文件链接/直搬的 scope 只是 save_path(平铺内容根)或组自己的内容根 —— 别名只挂在
        组内文件上, **不会**把落进同目录的别组读写重定向到 T, 故作用域覆盖语义不成立。
        P7 真机实测(s3 步): 平铺逐文件链接组3 的 scope = 整个 save_path, 旧实现让
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
        组2 的直搬 job scope = 恶女目录, 旧逻辑把同目录的组1 也解析到 T, 组键漂移后
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
        """本 job 是否挡住对(这些 hash 组成的)组的再次迁移(§3.6 第 14 行 / S10; D15 收窄)

        D15 放行集 = 收尾窗 {armed, rewritten}: 同组再迁不再一刀切拦截(S5 未收尾再迁移的
        supersede 支线按此放行; 本期 S4 前半先收窄闸门, supersede 重定向本体在 S5 落地)。
        前段相位(moving/watching/moved)仍拦: 搬迁/建链在途时叠加第二次 setLocation 会互相
        覆盖, 链接套链接让旧 job 失效。

        作用域覆盖分支**只对目录别名成立**, 且对全部非终态相位(含 armed/rewritten)保留:
        目录别名是一条挂在内容根的 junction/symlink, 落入该目录的写入会被整体重定向到
        job 的目标 —— 别名建链在新链仍是第 3 步, dir_alias 形态字段就是别名形态记录, armed/
        rewritten 期间别名在位, 别组此刻再迁, 数据会穿链接搬进旧 job 的目标、混进旧 job 的
        删链门依赖集(P7 真机 S14b 实测依据不变)。逐文件链接只挂在组内文件上、不改变目录
        形态, 无重定向 hazard, 故不适用本分支; direct 单成员组同理(无别名即无链接可套)。
        """
        if self.is_terminal:
            return False
        if self.touches(hashes):
            return self.phase not in FINALIZE_WINDOW_PHASES
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
    - misc_entries/external_entries/qb_temp_entries: 内容根 listing 的归属分类
      (杂项 = 不属于任何种子, 含无主 .!qB 残留; 组外 = 属于别的种子, 含其未完成 .!qB
      —— 两者只进 notes: qB 逐文件搬运碰不到它们; qb_temp = 本组文件处于 .!qB
      未落定态, 唯一硬拦面, plan 26-11-02-0134)。
    - target_conflicts: 目标侧已存在的同名路径(任一命中 qB 就走 need_full_check)。
    - same_volume: 源/目标是否同卷(None = 不可判定, 按跨卷保守处理)。
    - target_free: 目标卷剩余字节(None = 不可判定 ⇒ space 闸门拒绝)。
    - same_fs_proved: 同机证明成立(P3 判据: assume_shared 直通 / E1 机器级缓存 passed /
      路径级证据 src 侧 D 级 positive; B′/visibility_only 弱证据正/负都不一锤定音, 降
      note 后照走执行链一次性强探测 —— 计划 26-11-04-0055 §03.1 + issue 26-11-07-0527
      R1#35; free-space 代理已退役为提示)。
    - same_fs_negative: 确定性不共享(路径级证据 **src 侧 D 级**判负)—— 未证明不再硬拦
      多成员组(P3 闸门重排, 执行链一次性强探测兜底), D 级判负仍然硬拦; B′ 级判负是
      弱证据, 降 note 交执行链强探测定夺, 不进本位(R1#35 同款逻辑)。
    - same_fs_note: 同机判定的告知性 note(assume_shared 越权/E1 凭据放行/判负详情/
      不可判定原因), evaluate_group 原样入 notes。
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
    target_not_dir: bool = False
    same_volume: Optional[bool] = None
    target_free: Optional[int] = None
    same_fs_proved: bool = False
    same_fs_negative: bool = False  # P3: src 侧 D 级判负(确定性不共享)—— 优先于 proved 的硬拦面; B′ 判负不入本位
    same_fs_note: str = ""  # P3: 同机判定告知性 note(assume_shared 越权/E1 凭据/判负详情), 原样入 notes
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
    # 组内 AutoTMM 成员 hash(计划 26-11-05-0808 S1): auto_tmm=true 的成员 fastresume 无
    # qBt-savePath 键(N8 实测), 改写收尾对它不生效 => 有即整组拒迁(evaluate_group 闸门)
    auto_tmm_hashes: Tuple[str, ...] = ()
    # 源侧三态检查(0808 S1 继承 0546 机制1, 逐声明文件、深层天然覆盖): 只收「缺失」与
    # 「不可判定」两态; .!qB 孪生态并入 qb_temp_entries(复用既有 GATE_QB_TEMP, 不另造闸)
    source_missing_files: Tuple[str, ...] = ()  # 原名与 .!qB 孪生都不在(数据藏走 -> 零搬移假成功, E2.2)
    source_unknown_files: Tuple[str, ...] = ()  # exists 不可判定(容器映射 miss, D2 按 target_unknown 同款保守拒)


def _reason(gate: str, cls: str, text: str) -> dict:
    return {"gate": gate, "cls": cls, "text": text}


def nested_target_on(
    target: str,
    jobs: Sequence["RelocateJob"],
    *,
    form: str,
    src_cr: str,
    dst_cr: str,
    mover_save_path: str,
) -> Tuple[str, str, str]:
    """嵌套目标判定(计划 26-11-07-1300 R1-R5, 形态分治 + 三输出): -> (blocked, confirm, note), 空串 = 无

    在 evaluate_group 的 plan() 分流**之后**调用并消费形态(旧版在形态判定之前跑 = 形态盲,
    文件级/单成员被按目录别名口径硬拦, E1/E4 实测拦空气)。全部判据成分级 _within(以分隔符
    为界: 兄弟目录(待删2)/前缀同串(待删除)/尾斜杠不误伤, 大小写按 _norm 平台口径折叠),
    严格嵌套 = 相等不算(相等 = 幂等, 由 evaluate_group 幂等分支先行返回, 本函数不得吞相等态):
    - R1(blocked, 仅 DIR_ALIAS): 新旧内容根互嵌, 双向对称。正向(新 ⊆ 旧): junction 落点
      会被搬入的新数据占住, 搬移后建链必失败(E5 实测「内容根目录非空」卡死); 反向
      (旧 ⊆ 新): junction 指向自身祖先, 目录列举成环(E6 实测)。锚 src_cr/dst_cr 由调用方
      按 layout_of 同源派生(evaluate_group: content_root 与 _join(target, rel))。
    - R2(blocked, 任意形态, 非终态 job): target ⊆ job.scope(含等于, 保守)。在途 job src
      分支锚点从 job.src 收窄到 job.scope(别名落点/搬移树, relocate_exec 建账既有产物)——
      停旧根兄弟目录的种子不再误拦(E7 实测); 作用域内写入仍会被重定向, hazard 保留。
    - R3(blocked, 维持现状): target ⊆ job.dst 且 target != job.dst(恰等 dst = 两组落同一
      根各放各的内容, 不是嵌套形态); dst 锚过宽记 known-limitation(计划 §03 D2)。
    - R4(confirm, 未被 R1/R2/R3 拦): target 严格 ⊆ mover 声明源 —— 新落点嵌在旧声明源树
      下, 旧根将来整组迁移时这片新数据会被覆盖扫描连带走(D19)。
    - R5(note, 仅 FILE_LINKS): target 严格 ⊆ src_cr —— 别名存续期链接叶与新数据混居,
      带文件删除被 D16 拦(收尾完成后消失)。
    blocked 与 confirm/note 并存时以 blocked 为准(cls 归并由调用方); R4 让位于 blocked,
    R5 独立照常产出(调用方决定是否展示)。
    """
    if not _norm(target):
        return "", "", ""
    blocked = ""
    if form == FORM_DIR_ALIAS and _norm(src_cr) != _norm(dst_cr):
        # R1: 新旧内容根互嵌(严格: 相等不算 —— 相等即幂等形态, 不在此拦)
        if _within(src_cr, dst_cr):
            blocked = (
                f"目标与旧内容根互嵌(正向: 新内容根 {dst_cr} 落于旧内容根 {src_cr} 之下): 目录别名落点会被"
                "搬入的新数据占住, 搬移后建链必失败 —— 请选旧内容根之外的独立目录(计划 26-11-07-1300 R1)"
            )
        elif _within(dst_cr, src_cr):
            blocked = (
                f"目标与旧内容根互嵌(反向: 旧内容根 {src_cr} 落于新内容根 {dst_cr} 之下): 目录别名会指向"
                "自身祖先, 目录列举成环 —— 请选与旧内容根互不嵌套的目标(计划 26-11-07-1300 R1)"
            )
    if not blocked:
        for job in jobs or ():
            if job.is_terminal:
                continue
            scope_eff = job.scope or job.src  # 旧账 scope 缺失回落声明源(与 R7 删链门回落同口径)
            if _within(scope_eff, target):
                blocked = (
                    f"目标位于在途迁移 job {job.job_id} 的别名作用域/搬移树之下({target} ⊆ {scope_eff}): "
                    "数据混入会干扰旧迁移的收尾与删链门 —— 请等旧迁移收尾或换目标(计划 26-11-07-1300 R2)"
                )
                break
            if _norm(target) != _norm(job.dst) and _within(job.dst, target):
                blocked = (
                    f"目标位于在途迁移 job {job.job_id} 的声明目标之下({target} ⊆ {job.dst}): 旧 job 后续收尾"
                    "或再迁移会连带这片目录 —— 请换独立目标(计划 26-11-07-1300 R3)"
                )
                break
    confirm = ""
    if not blocked and _norm(mover_save_path) != _norm(target) and _within(mover_save_path, target):
        confirm = (
            f"新落点仍在旧声明源树下({target} ⊆ {mover_save_path}): 旧根将来整组迁移时这片新数据会被覆盖"
            "扫描连带走(D19) —— 如非有意请换独立目录(计划 26-11-07-1300 R4)"
        )
    note = ""
    if form == FORM_FILE_LINKS and _norm(src_cr) != _norm(target) and _within(src_cr, target):
        note = (f"新落点在旧内容根内({target} ⊆ {src_cr}): 别名存续期链接叶与新数据混居, 带文件删除会被 D16 拦"
                "(收尾完成后消失)(计划 26-11-07-1300 R5)")
    return blocked, confirm, note


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

    # ---- 未收尾拦截(先于一切: §3.6 第 14 行 / S10; D15 收窄: 收尾窗放行, S5 文案新口径) ----
    # 新口径(计划 26-11-05-0808 S5): 收尾窗(armed/rewritten)的组**可**直接再迁移 ——
    # armed 态走 supersede 重定向(旧迁移自动改道新目标), rewritten 态链式独立双门;
    # 仍拦的只有两类: 同组前段相位(moving/watching/moved, 叠加 setLocation 互相覆盖)、
    # 别组落进目录别名作用域(写入会被整体重定向进旧 job 目标)。
    for job in facts.jobs:
        if not job.blocks_relocation(facts.hashes, content_root):
            continue
        if job.touches(facts.hashes):
            _block(
                GATE_UNFINISHED, f"该组有搬迁在途的迁移(job {job.job_id} 相位 {job.phase}): 叠加的 setLocation 会"
                "互相覆盖、链接套链接让旧迁移失效 —— 等搬迁完成建好别名进入收尾窗(armed/rewritten)后即可直接"
                "再迁移, 旧迁移会自动改道(supersede)新目标, 无需先撤销"
            )
        else:
            _block(
                GATE_UNFINISHED, f"该组落点位于在途迁移 job {job.job_id} 的目录别名作用域内(相位 {job.phase}): "
                "落入该目录的写入会被别名整体重定向进旧 job 的目标, 别组数据会混进旧迁移 —— 请等旧迁移收尾或换目标"
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
            "member_count": len(facts.hashes),
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

    # ---- AutoTMM 成员闸门(计划 26-11-05-0808 S1, §2.2「AutoTMM 成员」行) ----
    # auto_tmm=true 的成员 fastresume 不落 qBt-savePath 键(N8 实测 55 vs 57 键), 双键改写
    # 对它无从生效 —— 有即整组拒迁; 全组成员手动管理是收尾链的硬前提(部署无关, 组级闸门)。
    if facts.auto_tmm_hashes:
        _block(
            GATE_AUTO_TMM, "成员由 qB 自动管理(AutoTMM: " + ", ".join(h[:8] for h in facts.auto_tmm_hashes[:3]) +
            "): 其 fastresume 无 qBt-savePath 键, 改写收尾不生效 —— 请先在 qB 里改为手动管理或把它移出该组"
        )

    # ---- 源侧三态之缺失/不可判定(0546 机制1; .!qB 孪生态已并入 qb_temp_entries 走上方既有闸) ----
    # 缺失 = 数据已不在这两个名字下(qB 搬迁对 stat 不到的源文件忽略并算成功, storage_utils.cpp:151,
    # E2.2 实证零搬移假成功); 不可判定 = 容器映射 miss, 按 target_unknown 同款保守拒(D2)。
    if facts.source_missing_files:
        names = facts.source_missing_files
        shown = ", ".join(names[:3]) + (f" 等共 {len(names)} 个" if len(names) > 3 else "")
        _block(
            GATE_SOURCE_MISSING, f"源文件缺失({shown}): 声明文件在源盘既不在原名也不在 .!qB 孪生名下 —— "
            "qB 搬迁对读不到的源文件会忽略并算成功, 迁移只会零搬移假成功; 请先核对数据现场(找回或重种)后再迁"
        )
    if facts.source_unknown_files:
        _block(
            GATE_SOURCE_UNKNOWN, "源侧存在性不可判定(" + ", ".join(facts.source_unknown_files[:3]) +
            "): 容器映射未覆盖或探测失败 —— 不可判定一律拒绝(与目标侧 target_unknown 同口径), "
            "请检查 fs.path_map 是否覆盖源位置"
        )

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
    if facts.target_not_dir:
        _block(GATE_TARGET_TYPE, "目标路径已存在但不是目录: qB 无法在其下创建内容 —— 请改目标或先清理该路径(R2 #3)")
    if facts.qb_temp_entries:
        _block(GATE_QB_TEMP, "本组存在 .!qB 未落定文件(" + ", ".join(facts.qb_temp_entries[:3]) + "): 数据尚未落定, 不能迁")
    if facts.target_free is None and facts.same_volume is not True:
        _block(GATE_SPACE, "目标卷剩余空间不可判定(路径不可读或容器映射未覆盖): 不可判定一律拒绝")
    elif facts.target_free is not None and facts.target_free < needed and facts.same_volume is not True:
        _block(GATE_SPACE, f"目标卷剩余 {facts.target_free} 字节 < 本组数据 {needed} 字节: 空间不足, 拒绝迁移")
    # 同卷(True): rename 不占额外空间, 空间预检不适用(R2 #1) —— 数值仅展示, 见 same_volume note

    # ---- 同机证明(P3 判据重排, 计划 26-11-04-0055 §03.1) + 平台能力 ----
    # 三态: negative(确定性不共享)硬拦 / 未证明(不可判定)转 note 由执行链一次性强探测
    # 兜底 / proved 放行。单成员组维持 note 不拦(独占情形 qB 自搬, 免证明)。
    if facts.same_fs_negative and multi:
        _block(
            GATE_SAME_FS,
            "qB 侧目录证据与本机不符(确定性不共享): 本机建的链接 qB 读不了 —— "
            "请检查 fs.path_map 映射是否覆盖该路径, 或确认 qB 与 auto-qb 确实共享文件系统后配置 relocate.assume_shared",
        )
    elif not facts.same_fs_proved:
        text = ("无法证明 auto-qb 与 qB 看到同一块盘(路径级证据不可判定): "
                "远程 qB 或容器路径错位下, 本机建的链接 qB 读不了")
        if multi:
            notes.append("同机证明未成立 —— 首次执行迁移时将做一次性强探测(失败将拒绝)")
        else:
            notes.append(
                text +
                " —— 独占情形由 qB 自行搬运, 免同卷证明与链接能力; 其余闸门(冲突/空间/未落定/未收尾)照跑(plan 26-11-02-0134 R1 方案B: 原文「目标冲突/空间未预检」与实现不符)"
            )
    if facts.same_fs_note:
        notes.append(facts.same_fs_note)
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

    # ---- 嵌套目标闸门(计划 26-11-07-1300 R1-R5; 形态分治 + 三输出) ----
    # 在 plan() 分流之后跑并消费 unit.form(旧位置 :582 在形态判定之前 = 形态盲, §02):
    # R1 只拦 DIR_ALIAS 的内容根互嵌, DIRECT/FILE_LINKS 的嵌套按 R4 confirm/R5 note 披露;
    # FORM_REJECT 已被 GATE_FORM 拦, 嵌套判据跳过(不再拦空气)。锚点全部取 mover 声明空间
    # 派生物(与组键 resolve_physical 口径一致): src_cr = mover 内容根(上方 layout_of 产物),
    # dst_cr = target + 同源 rel, mover_save_path = mover 声明源; 相等态已由幂等分支先行返回。
    if unit.form != FORM_REJECT:
        nested, nested_confirm, nested_note = nested_target_on(
            facts.target,
            facts.jobs,
            form=unit.form,
            src_cr=content_root,
            dst_cr=_join(facts.target, rel),
            mover_save_path=facts.save_path,
        )
        if nested:
            _block(GATE_NESTED, nested)
        if nested_confirm:
            _confirm(GATE_NESTED, nested_confirm)
        if nested_note:
            notes.append(nested_note)

    # ---- 告知性 notes ----
    if facts.target_free is not None:
        notes.append(f"目标卷剩余 {facts.target_free} 字节; 本组数据 {needed} 字节")
    if facts.same_volume is True:
        notes.append("源与目标同卷: qB 走 rename 不占额外空间, 空间预检不适用(目标卷剩余仅展示, R2 #1)")
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
        "member_count": len(facts.hashes),  # 整组语义披露(计划 1300 R6b; P3 前端「来源(整组 N 个成员)」消费)
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


def _file_link_roots(src: str, alias_paths: Sequence[str]) -> tuple:
    """文件级 job 的成员链接根集合(alias_paths 在 src 下第一段派生; 纯函数)

    每条链接路径取其在 src 之下的第一段 -> 根 = src/<第一段>: 嵌套成员 = 内容根目录
    (同名目录碰撞由该根接住 —— 内容根目录本身不是链接), 平铺成员 = 链接文件自身
    (同名文件碰撞与 (1) 重合)。不在 src 下的条目跳过(账面异常形态不猜); 全部解析不出
    -> 空集, 调用侧按「账面不可得 -> 保守 confirm」处理(宁拦勿漏), 不猜「异名」。
    """
    if not _norm(src):
        return ()
    roots = []
    for ap in alias_paths or ():
        rel = _rel_under(ap, src)
        if not rel:
            continue
        seg = rel.split("/", 1)[0]
        if seg and _join(src, seg) not in roots:
            roots.append(_join(src, seg))
    return tuple(roots)


def evaluate_add(facts: AddFacts) -> dict:
    """往别名作用域添加种子的三分流(ok=无影响 / confirm=弹「请求路径→实际落点→卷剩余」二次确认)

    落点 = save_path/内容根(种子名)。判定顺序(§3.6 行号; D16 收尾窗重定义到 {armed,
    rewritten} 且**变更承重**; 收尾窗分支形态感知, 计划 26-11-13-0448 R1):
    1. 收尾窗口(armed/rewritten: 数据已在新位置、成员经别名做种), 按别名形态分流:
       - 目录别名: 双面真值(评审轮 1 勘误)—— 恰等 src(删链门等值面的账面依赖面)或 landing
         落在 anchor(job.scope or job.src, = junction 所在内容根)内的写入 ⇒ confirm; landing
         在 anchor 内 = 真重定向面(actual = dst 侧 scope 镜像 + rel-to-scope, 文案「经别名
         落到」); 仅等值面 landing 在 junction 外不经重定向, actual 展示按 D16 契约取账面
         建模镜像根、文案走账面/依赖语义; src 下 scope 外兄弟/前缀同串目录写入落真实目录、
         删链门不计依赖 ⇒ 不拦。账面记旧根 = 删链门(等值 OR 前缀)的**永久依赖**, confirm
         是唯一预防面;
       - 文件级别名: 旧根是真实目录, 别名只是成员内容里的逐文件链接 —— 落点按名字判定:
         (1) 撞链接路径(同名文件, §3.6 场景 2/3)confirm; (2) 撞成员链接根(alias_paths 在
         src 下第一段派生; 同名目录碰撞在此接住)confirm(保守); (3) 其余(异名)静默放行
         (场景 1: 数据落原盘真实目录, 不经别名、不依赖别名), 惟 save_path 恰等 src 的等值面
         临时 confirm —— R2 交集判据落地(计划 26-11-13-0448 §03 R2)前收尾窗删链门等值面
         (_chain_gate_deps equal_root=src)仍计依赖, 放行会收尾恒悬挂; 文案/actual 同
         目录级等值面口径(临时面: R2 交集判据落地后由放行闭合)。磁力/URL/NoSubfolder 布局
         不可判定不作第四分支 —— 残余碰撞由执行侧背网兜住(跨组交叉检测 = 场景 3 处置;
         同名共享 = 删链门交集判依赖)。账面不可得(alias_paths 空/解析不出根)⇒ 保守
         confirm 不猜「异名」(宁拦勿漏); 落点是账外链接(第三方/他组)交分支 4 拦;
       - direct(无别名): 判据维持旧面(恰等 src)不变;
    2. 目录别名作用域命中(前段相位 moved): 一切落点被重定向到 T ⇒ confirm(展示实际落点
       与目标卷剩余);
    3. 逐文件链接: 只有落点**本身就是链接**(同名)才 confirm(写入将覆盖 T 侧数据);
       异名落原盘真实目录, 无影响 ⇒ ok;
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

    # ---- 1. 收尾窗口(armed/rewritten; D16 变更承重; 形态感知分流, 计划 26-11-13-0448 R1) ----
    # 旧判据「save_path == job.src 一律 confirm」不分形态, 把文件级 job 的组外异名添加
    # 误拦成「删链门永久依赖」(数据本落原盘真实目录, 1604 §3.6 场景 1)。分流以形态为
    # 第一维: 目录级判据双面真值 = 恰等 src(删链门等值面)或 landing 落在 anchor(scope
    # or src, junction 所在内容根 = 真重定向面); 重定向面 actual 按真实落点算(dst 侧
    # scope 镜像 + rel-to-anchor), 等值面展示账面建模镜像根且文案分流(不经别名); 文件级
    # 按落点名字判定: (1)(2) confirm / (3) 异名放行(save_path 恰等 src 的等值面由临时守卫
    # 先拦 confirm, R2 交集判据落地前承重, 见下)。
    # (3) 的 ok 不即刻返回: 先扫完其余 job 的 confirm 面(宁拦勿漏), 全部无交叉才静默放行。
    finalize_ok = False  # 有文件级 job 认领本次落点且判定「异名无交叉」(§3.6 场景 1)
    link_pending = False  # 落点是链接但不在任一认领 job 账上(第三方/他组): 不可判「异名」
    for job in facts.jobs:
        if job.is_terminal:
            continue
        if job.phase not in FINALIZE_WINDOW_PHASES:
            continue
        if job.alias_kind == "dir":
            # 双面真值(评审轮 1 勘误, 计划 26-11-13-0448): junction 实际建在内容根 src+scope_rel
            # (relocate_exec._build_links / _scope_rel 单点), 只有 landing 落在其内的写入才被重定向
            # —— 该面取 anchor = job.scope or job.src(删链门 _chain_gate_deps 同款锚); 恰等 src 是
            # 删链门等值面的账面依赖(D16 契约, confirm 照旧承重)。src 下 scope 外兄弟/前缀同串
            # 目录: 写入落真实目录不经重定向、删链门也不计依赖 —— 不拦(原前缀扩面在该形态误拦,
            # 文案「经别名落到 actual」「删链门永久依赖」双双失实)。
            anchor = job.scope or job.src
            hit_redirect = under_alias_root(landing, (anchor, )) is not None
            if _norm(facts.save_path) != _norm(job.src) and not hit_redirect:
                continue
            # actual: 重定向面(hit_redirect)按真实落点算 —— junction target = dst+scope_rel, 写入
            # 映射 = dst 侧 scope 镜像 + landing 相对 anchor 的尾段(恰等 anchor = 镜像根; scope==src
            # 时镜像根 = dst, 与旧 rel-to-src 口径重合)。仅等值面(save_path 恰等 src 而 landing 不在
            # anchor 内): 账面 save_path 恒记 src → 删链门等值面必命中 ⇒ confirm 承重; 该形态 landing
            # 在 junction 外、写入不经别名落真实目录, actual 按 D16 契约取账面建模落点(镜像根)展示
            # —— 不把「恰等 src」推成「内容根=scope」(等值面建模前提是「经别名落进作用域」, 即
            # landing 在 anchor 内, 见 chain_gate_hits 等值面), 文案随之分流(下方)。
            actual = _join(_join(job.dst, _rel_under(anchor, job.src)), _rel_under(landing, anchor))
            if hit_redirect:
                text = (
                    f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}): "
                    f"新种子将经别名落到 {actual}, 但账面会记在旧路径 —— 成为删链门的永久依赖"
                    "(旧路径别名将永不删除) —— 请等 qB 重启收尾完成后再添加, 或确认接受依赖后继续"
                )
            else:
                text = (
                    f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}): "
                    f"新种子账面将记在旧根 {job.src} —— 成为删链门等值面依赖(旧路径别名将永不删除)"
                    " —— 请等 qB 重启收尾完成后再添加, 或确认接受依赖后继续"
                )
            return {
                **base,
                "cls": CLS_CONFIRM,
                "actual_path": actual,
                "volume_free": facts.target_free,
                "reasons": [_reason("finalize_window", CLS_CONFIRM, text)],
                "notes": [f"目标卷剩余 {facts.target_free} 字节" if facts.target_free is not None else "目标卷剩余不可判定"],
            }
        if job.alias_kind == "file":
            if under_alias_root(facts.save_path, (job.src, )) is None:
                continue  # 落点不在旧根面(祖先/平行路径): 不进收尾窗分支, 与旧判据行为一致
            alias_paths = job.alias_paths or ()
            roots = _file_link_roots(job.src, alias_paths)
            if not alias_paths or not roots:
                # 账面不可得(armed 落账必非空, 这里是账异常/防御面): 保守 confirm, 不猜「异名」
                return {
                    **base,
                    "cls": CLS_CONFIRM,
                    "reasons":
                        [
                            _reason(
                                "finalize_window", CLS_CONFIRM,
                                f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}, "
                                "成员经别名做种): 现在添加的种子账面会记在旧路径, 成为删链门的永久依赖"
                                "(旧路径别名将永不删除) —— 请等 qB 重启收尾完成后再添加, 或确认接受依赖后继续"
                            )
                        ],
                    "notes": [],
                }
            if any(_norm(landing) == _norm(ap) for ap in alias_paths):
                # (1) 落点撞链接路径(同名文件, §3.6 场景 2/3): 同内容 = 经链接共享、真依赖;
                #   不同内容 = 写入将覆盖链接目标数据
                return {
                    **base,
                    "cls": CLS_CONFIRM,
                    "reasons":
                        [
                            _reason(
                                "finalize_window", CLS_CONFIRM,
                                f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}, "
                                f"成员经别名做种): 落点 {landing} 与成员别名链接同名 —— 同内容辅种会经链接"
                                "共享同一份物理数据(账面成为删链门依赖, 收尾完成前别名不会删除); 不同内容则"
                                "写入将覆盖链接目标(已迁到新位置)的数据 —— 请等 qB 重启收尾完成后再添加,"
                                " 或确认接受依赖后继续"
                            )
                        ],
                    "notes": [],
                }
            if under_alias_root(landing, roots) is not None:
                # (2) 落点撞成员链接根(保守): 同名目录碰撞在此接住(内容根目录不是链接),
                #   深层落点顶进内容根面同样拦 —— 账面也会记在旧根成为删链门前缀依赖
                return {
                    **base,
                    "cls": CLS_CONFIRM,
                    "reasons":
                        [
                            _reason(
                                "finalize_window", CLS_CONFIRM,
                                f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}, "
                                f"成员经别名做种): 落点 {landing} 与成员别名的内容根重叠 —— 写入可能与别名"
                                "链接交叉(同名目录/深层落点), 账面也会记在旧路径成为删链门的永久依赖"
                                " —— 请等 qB 重启收尾完成后再添加, 或确认接受依赖后继续"
                            )
                        ],
                    "notes": [],
                }
            if facts.landing_is_link:
                # 落点是链接但不在本 job 账上(第三方/他组): 不可判「异名」, 交分支 4 拦
                link_pending = True
                continue
            if _norm(facts.save_path) == _norm(job.src):
                # 临时面: R2 交集判据落地(计划 26-11-13-0448 §03 R2)后由放行闭合 ——
                # save_path 恰等 src 账面必记旧根, 收尾窗删链门等值面(_chain_gate_deps
                # equal_root=job.src, R2 落地前未改交集判据)仍把该种子计依赖, 预检放行会收尾恒
                # 悬挂(REASON_CHAIN_DEPS, 文案失实); R2 落地前按目录级等值面同款 confirm
                # 承重(文案/actual/notes 同一口径, 不另造第二份)。
                anchor = job.scope or job.src
                actual = _join(_join(job.dst, _rel_under(anchor, job.src)), _rel_under(landing, anchor))
                text = (
                    f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}): "
                    f"新种子账面将记在旧根 {job.src} —— 成为删链门等值面依赖(旧路径别名将永不删除)"
                    " —— 请等 qB 重启收尾完成后再添加, 或确认接受依赖后继续"
                )
                return {
                    **base,
                    "cls": CLS_CONFIRM,
                    "actual_path": actual,
                    "volume_free": facts.target_free,
                    "reasons": [_reason("finalize_window", CLS_CONFIRM, text)],
                    "notes": [f"目标卷剩余 {facts.target_free} 字节" if facts.target_free is not None else "目标卷剩余不可判定"],
                }
            finalize_ok = True  # (3) 异名候选(§3.6 场景 1) —— 继续扫其余 job 的 confirm 面
            continue
        # 其余形态(direct, 无别名): 判据维持旧面(恰等 src), 形态感知分流不扩 direct
        if _norm(facts.save_path) == _norm(job.src):
            return {
                **base,
                "cls": CLS_CONFIRM,
                "reasons":
                    [
                        _reason(
                            "finalize_window", CLS_CONFIRM,
                            f"该目录的迁移待收尾(job {job.job_id} 相位 {job.phase}, 数据已迁到 {job.dst}, "
                            "成员经别名做种): 现在添加的种子账面会记在旧路径, 成为删链门的永久依赖"
                            "(旧路径别名将永不删除) —— 请等 qB 重启收尾完成后再添加, 或确认接受依赖后继续"
                        )
                    ],
                "notes": [],
            }
    if finalize_ok and not link_pending:
        # (3) 异名静默放行(§3.6 场景 1): 数据落原盘真实目录, 不经别名、不依赖别名
        return {**base, "cls": CLS_OK, "reasons": [], "notes": []}

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
        "created_at": job.created_at,
        "armed_at": job.armed_at,
        "updated_at": job.updated_at,
        "resume_hashes": list(job.resume_hashes),
        "attempts": job.attempts,
        "last_error": job.last_error,
        "plan": job.plan,
        "move_issued": job.move_issued,
        "tag_on": job.tag_on,
        "origin": job.origin,
    }


def job_from_dict(d: Any) -> Optional[RelocateJob]:
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
            # 旧账相位前向映射(S4 迁移口径): removing/removed/finalizing -> armed(非终态
            # 不丢现场); 终态与新相位原样。未知值原样透传(旧 reader 不炸原则: 非终态且
            # 不在任何相位分支里 = 推进分派静默跳过, 不炸不误判终态)。
            phase=LEGACY_PHASE_MAP.get(str(d.get("phase") or ""), str(d.get("phase") or PHASE_MOVING)),
            reason=str(d.get("reason") or ""),
            created_at=float(d.get("created_at") or 0.0),
            armed_at=float(d.get("armed_at") or 0.0),
            updated_at=float(d.get("updated_at") or 0.0),
            resume_hashes=tuple(d.get("resume_hashes") or ()),
            attempts=int(d.get("attempts") or 0),
            last_error=str(d.get("last_error") or ""),
            plan=d.get("plan") if isinstance(d.get("plan"), dict) else None,
            move_issued=bool(d.get("move_issued")),
            tag_on=bool(d.get("tag_on")),
            origin=str(d.get("origin") or "unknown"),
        )
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class RelocateSnapshot:
    """主循环发布的 job **只读快照**(WebUI 构建期消费, plan 26-11-04-1042 P0-1)

    - `jobs`: 全部 job 的只读视图(元组, 元素为 MappingProxyType 包住的 job dict)
    - `by_hash`: hash -> 该 hash 的**最佳 job**(非终态优先, 同态取 updated_at 最新)
    - `generation`: 每次内容变化 +1, 供 Web 侧判断快照是否换代

    Web 线程只读 `by_hash` 做 O(1) 成员判定; 不再遍历 `_jobs`, 也不再在构建期
    调 jobs_view()。发布动作只发生在主循环的 job 变更路径(register/_set/_start/_load)。
    """

    generation: int = 0
    jobs: Tuple[Mapping, ...] = ()
    by_hash: Mapping[str, Mapping] = field(default_factory=lambda: MappingProxyType({}))

    def job_for(self, torrent_hash: str) -> Optional[Mapping]:
        return self.by_hash.get(torrent_hash)


def job_rank(job: Mapping) -> tuple:
    """同一 hash 多 job 时的选取序: 非终态优先, 再按 updated_at 新→旧, 最后 job_id 稳定兜底"""
    terminal = str(job.get("phase") or PHASE_MOVING) in TERMINAL_PHASES
    return (not terminal, float(job.get("updated_at") or 0.0), str(job.get("job_id") or ""))


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


# (S4 退役注记) 旧链的 finalize_scope_candidate/finalize_members「动态收尾集合」随
# ACT_FINALIZE 归位链整体退役(0420 证伪): 新链收尾 = qB 重启后全员 save_path 等值核验
# + 删链门依赖扫描(核验+删链推进单点在 relocate_exec._step_verify, S4 后半落地),
# 不再需要「把落进作用域的新成员一并 setLocation」的账面恢复链。

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


# ---------------------------------------------------------------- 对账表(S4 新链, 计划 26-11-05-0808 §3.2「对账与生命周期」行)
# 旧表 9 动作(S4 退役注记):
# - ACT_RESPAWN/ACT_REDELETE -> ACT_ENSURE_DAEMON 合并替代(回收 daemon 重拉, per-job
#   pid 锁/心跳/RESPAWN_BACKOFF 退避一并退役, D12);
# - ACT_REVERT_INTENT -> 随「先删别名再归位」意图链退役(新链无删别名意图相位);
# - ACT_FINALIZE -> 随 missingFiles 预期输入/setLocation 归位链退役(0420 证伪);
# - ACT_DONE_EXTERNAL -> 并入核验+删链推进(ACT_VERIFY: 全员 save_path==dst 就是核验
#   通过的充分证据, 后续删链在 _step_verify 单点);
# - ACT_FAILED_TIMEOUT -> 退役(D10 收敛公理: journal 悬挂是良性态, 反馈面提示「重启 qB
#   即完成」, 不判 failed —— 失败态必须收敛到「别名在/成员可读/journal 待重放」);
# - ACT_FAILED_GONE -> 退役(种子被删的现场处置并入 S4 后半核验面的依赖扫描口径,
#   悬挂态单项良性, 不再在判据层抢判 failed)。

ACT_WAIT = "wait"  # 等(armed 做种中 / qB 不在等下线窗口 / pending 由 daemon 处理)
ACT_REBUILD = "rebuild_links"  # 别名丢失 + qB 在 ⇒ 从 job 账重建别名回 armed(rebuild-from-journal 判据侧)
ACT_VERIFY = "verify_chain"  # 全员 save_path 已在目标位置 ⇒ 核验+删链推进(体在 relocate_exec._step_verify)
ACT_ENSURE_DAEMON = "ensure_daemon"  # pending 非空且回收 daemon 死/心跳过期 ⇒ 重拉 recycle_daemon
# journal failed 相位的三个处置(issue 26-11-07-0527 #3: 收尾校验失败写下的 journal 相位
# failed 原先无任何消费者, daemon 重拉后整包覆盖失败证据, job 永不收敛 failed 终态):
ACT_FAIL_TERMINAL = "fail_terminal"  # 证据可信(有 reason 且 ts 不早于本生命周期)⇒ 转 job failed 终态
ACT_FAIL_SUSPECT = "fail_suspect"  # 证据形态可疑(reason/ts 缺失坏形)⇒ 保守搁置: WARNING 留人工, 不转终态
# 陈旧残留(ts 早于本生命周期锚点 = 同 job_id 再迁移的上一世账)⇒ 执行体清账
# (relocate_journal.clear_journal)后按无账现场重评常规表 —— failed 入 STOP_PHASES 后
# daemon 对该 job_id 退休, 残留账不清则新生命周期的改写/重放被永久堵死(死锁在 armed)
ACT_FAIL_STALE = "fail_stale"

# 重试退避与上限(防无界重试): 建链必失败的环境(权限不足 / 未开 Windows 开发者模式且
# allow_uac 关 —— 预检文案自己点名的常见环境)里, 「别名丢失 → 对账 REBUILD → 置 MOVED
# 重建 → 再失败」会每 1-2 个 tick 一轮 create-fail-delete 且永不终态(WARNING 刷屏)。
# 这类失败不是抖动, 靠退避拉开间隔 + 达到上限转 failed 留现场才能收敛。
# 取常量而非配置键: 这是执行体的内部节拍, 不是用户该调的策略面 —— 重试次数由
# job.attempts 记账(落 state, 重启不丢)。
REBUILD_MAX_ATTEMPTS = 3  # 重建别名的重试上限(超出 ⇒ failed 留现场交人)
REBUILD_BACKOFF = 300.0  # 秒; 两次重建之间的最小间隔
DAEMON_RESPAWN_BACKOFF = 60.0  # 秒; 回收 daemon 两次重拉之间的最小间隔(ACT_ENSURE_DAEMON 节流;
# 旧 RESPAWN_BACKOFF 随 per-job guardian 退役, 本常量承接其「防 Popen 每 tick 空拉」职责)

#: 回收 daemon 心跳过期线(daemon 侧节拍常量在 tools/recycle_daemon.py HEARTBEAT_MAX_AGE,
#: 两处同值是「daemon 写侧节拍 / 对账读侧判线」的配对 —— 不互相 import, 避免 core→tools 依赖)。
DAEMON_HEARTBEAT_MAX_AGE = 60.0


def ensure_daemon_action(*, pending: int, daemon_stale: bool) -> str:
    """新链对账判据(纯函数)

    - pending 集空 ⇒ wait: 没有待改写成员, daemon 自会宽限退出, 对账不拉
      (拉了也只会空转一个宽限周期, 纯浪费);
    - daemon 健康在位(pid 活且心跳未过期)⇒ wait: 至多一个 watcher(D12), 重复拉起
      会被 pid 抢占退位, 无意义抖动;
    - 两者同时成立(pending 非空 + daemon 死/心跳过期)⇒ ensure_daemon: 重拉
      recycle_daemon(subprocess, 执行体侧处置, 绝不 taskkill)。
    """
    if pending <= 0 or not daemon_stale:
        return ACT_WAIT
    return ACT_ENSURE_DAEMON


def reconcile(
    job: RelocateJob,
    *,
    alias_present: bool = True,
    qb_up: bool = True,
    all_at_dst: bool = False,
    journal_phase: str = "",
    journal_reason: str = "",
    journal_ts: Optional[float] = None
) -> str:
    """收尾窗(armed/rewritten)对账表: (别名在?, qB 在?, 全员已到目标?) -> 处置动作(纯函数)

    新链判据只认**证据**而非意图相位 —— 收尾窗没有「先删别名再归位」的意图账, 三个
    输入把现场分干净:
    - journal 相位 failed(issue 26-11-07-0527 #3): 收尾校验失败的证据账, 处置优先于
      三输入现场推进 —— 证据可信 ⇒ ACT_FAIL_TERMINAL(消费转 failed 终态); 形态可疑 ⇒
      ACT_FAIL_SUSPECT(保守搁置留人工); 陈旧残留 ⇒ ACT_FAIL_STALE(执行体清账后按
      无账现场重评三输入 —— 本表不再回落, 重拉判据的恢复在执行体清账之后);
    - 全员已在目标位置(改写生效/qB 重启加载完成或外部归位)⇒ ACT_VERIFY: 核验+删链
      推进(全员逐成员等值核验、删链门依赖扫描与删别名在 _step_verify 单点);
    - 别名丢失而 qB 在线 ⇒ ACT_REBUILD: 从 job 账(alias_paths/plan)重建别名回 armed
      (journal 条目重建别名 = rebuild-from-journal 的判据面; qB 不在时不重建 —— 下线
      窗口是 daemon 的改写现场, 重建动作等 qB 回来);
    - 其余(armed 做种中 / qB 不在)⇒ ACT_WAIT。pending 集与 daemon 存活的对账不进本表
      —— ACT_ENSURE_DAEMON 判据独立(ensure_daemon_action), 由执行体每拍顺带判。
    """
    if journal_phase == PHASE_FAILED:
        # 失败证据三态(消费/搁置/陈旧清账)处置优先于现场推进; 陈旧清账与恢复重拉在执行体
        return _journal_failed_action(job, reason=journal_reason, ts=journal_ts)
    if all_at_dst and qb_up:
        return ACT_VERIFY
    if not alias_present and qb_up:
        return ACT_REBUILD
    return ACT_WAIT


def _journal_failed_action(job: RelocateJob, *, reason: str, ts: Optional[float]) -> str:
    """journal failed 相位的消费判定(纯函数; reconcile 的 failed 分支单点)

    判定次序: **陈旧优先于可疑** —— ts 可解析且早于锚点 = 上一生命周期的残留账
    (job_id 由 mover/src/dst 摘要而来, 同组同目标再迁移复用同 id), 证据形态再残缺也
    只属于上一世, 清账让位新生命周期(否则同 id 再迁移死锁在 armed), 不落入可疑搁置。

    - ACT_FAIL_STALE: ts 可解析且早于本生命周期锚点 —— 锚点取 armed_at(arm 之后收尾链
      才可能写下失败), 缺则退 created_at; 执行体清账(clear_journal)后按无账现场重评;
    - ACT_FAIL_SUSPECT: reason 缺失/空 或 ts 缺失/坏形, 或锚点缺失(两账皆 0 = 既无法
      证明新鲜也无从证伪陈旧)—— 宁可保守: 不转终态留人工, 绝不把可疑证据误判成终态;
    - ACT_FAIL_TERMINAL: reason 非空且 ts 不早于锚点 —— 本生命周期内写下的失败证据,
      执行体据此转 failed 终态并把证据原文保留进 reason/last_error。
    """
    anchor = job.armed_at if job.armed_at > 0 else job.created_at
    ts_f: Optional[float] = None
    if ts is not None:
        try:
            ts_f = float(ts)
        except (TypeError, ValueError):
            ts_f = None
    if ts_f is not None and anchor > 0 and ts_f < anchor:
        return ACT_FAIL_STALE
    if not str(reason or "").strip() or ts_f is None or anchor <= 0:
        return ACT_FAIL_SUSPECT
    return ACT_FAIL_TERMINAL


# ---------------------------------------------------------------- 核验与删链门(S4 后半)

# 非终态 job 的 reason 码(收尾窗推进/悬挂语义; job_to_dict/job_from_dict 原样透传,
# WebUI 反馈面 finalize_face 按 reason 分流提示):
REASON_VERIFY_FAILED = "verify_failed"  # 核验未过: 成员 save_path 未到目标(journal 悬挂, 良性态)
REASON_CHAIN_DEPS = "chain_deps"  # 删链门依赖未清: 仍有种子 save_path 位于旧根(等值或前缀)
REASON_FINALIZED = "finalized"  # 收尾完成(核验通过 + 删链门依赖清零, 已在线删别名)


def under_alias_root(path: str, roots: Iterable[str]) -> Optional[str]:
    """path 是否落在任一根**之上**(等值)或**之内**(前缀); 命中返回该根的归一形, 未命中 None

    删链门与删种拦截**共用的判据单点**(计划 26-11-05-0808 §2.3 N5 教训): 纯前缀判据
    (p.startswith(root + "/"))会漏拦 save_path **恰等于**根的形态(N5 实测: 门外共享者
    的 save_path 与组根同值) —— 必须等值 OR 前缀双判据。比较走 _norm(斜杠统一 +
    normcase 平台折叠); 前缀以分隔符为界(前缀同串的兄弟目录不误伤)。
    """
    p = _norm(path)
    if not p:
        return None
    for root in roots or ():
        r = _norm(root)
        if r and (p == r or p.startswith(r + "/")):
            return r
    return None


def alias_roots_of(jobs: Iterable[RelocateJob]) -> tuple:
    """活动别名根集(删种拦截 D16 的数据源; 纯函数): [(src, job_id), ...]

    只有**确实建过别名**的非终态 job 才拦: alias_kind 非空(direct 单成员组无别名不拦)
    且 alias_paths 非空(账上有链接记录 —— moving 相位别名尚未建, 不拦; 链接随 moved
    建成后进入拦截, 直到终态随 _sync_relocating 退出登记)。
    """
    out = []
    for job in jobs or ():
        if job.is_terminal or not job.alias_kind or not job.alias_paths:
            continue
        out.append((job.src, job.job_id))
    return tuple(out)


def chain_gate_hits(save_paths: Iterable[str], root: str, equal_root: str = "") -> tuple:
    """删链门依赖扫描(纯函数): 作用域根上/内的 save_path 集合 + 恰等旧根的并列等值面
    (N5 双判据, 判据单点 under_alias_root)

    save_paths = qB 全量种子的 save_path(不限于本组 —— 门外共享者/落进作用域的组外种子
    都算依赖, §07 风险表「pending 期组外种子落旧根」行); root = 别名作用域(job.scope,
    计划 26-11-07-1300 R7 重锚: 旧锚 job.src 会把停进旧根兄弟目录的组外种子与嵌套放行形态
    下成员搬后的 save_path=dst 全数顶进依赖集 —— 收尾自锁/假依赖, T1a/E2+E7 实测)。
    equal_root = 旧声明根(job.src)的**仅等值**并列面(R7 评审修复): dir_alias 收尾窗内经
    别名落进作用域的组外种子, 账面 save_path 恰等 job.src(内容根=scope, evaluate_add D16
    分支同款建模并承诺其为删链门永久依赖)—— 只按 scope 前缀判会漏计, 别名被误删后该种子
    断粮且失去 D16 保护。仅并等值不并前缀: job.src 的前缀面正是 R2/E7 要摘掉的假依赖
    (旧根兄弟目录)。本组成员的豁免在调用侧按 hash 过滤(relocate_exec._chain_gate_deps)
    —— 豁免是成员身份语义不是路径语义, 路径层排除会误伤恰同路径的组外种子。
    返回命中的 save_path 原值元组(保持输入侧大小写/斜杠原样, 供文案展示)。
    """
    out = []
    eq = _norm(equal_root)
    for sp in save_paths or ():
        if sp and (under_alias_root(sp, (root, )) is not None or (eq and _norm(sp) == eq)):
            out.append(sp)
    return tuple(out)
