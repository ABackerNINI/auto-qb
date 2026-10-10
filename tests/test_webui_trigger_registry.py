"""test_webui_trigger_registry 测试计划: 触发点登记表与作用域一致性守阵(计划 26-10-10-2001 S2)

口径单点 = `memory-bank/conventions/webui-scope.md`(专题 webui-selection-trigger-parity)。
登记表单点 = `static/shared/triggers.js` 的 `TRIGGER_DEFS`。本文件是「三张网」的第①张(静态守阵)。

本守阵要解决的问题: 现状把「动谁」拆在 7 个目标解析点 + 7 个动作出口 + 1 个平行变体判定上,
互不引用, 于是「选中 A 却动了 B」这类**静默作用对象偏移**既不被现有断言覆盖, 也没有声明可查。
把触发点收进一张声明表之后, 新增功能要么走统一出口(网②自动罩), 要么登记进表(本文件强制)。

## 测试计划(每个测试函数一条)
- test_trigger_registry_shape: 登记表自身形状 —— 必填字段齐、id 唯一、枚举值在词表内、
  scope 含 none 的投递点必须写 why(豁免也要说明, 白名单不复存在)
- test_trigger_registry_call_sites_exact: T1 —— `shared/*.js` 里**每一个** `method: "POST"`
  出现点所在方法必须与 `calls` 表**双向相等**(表外即红 = 新功能绕开登记; 表内残留 = 声明腐烂)
- test_trigger_registry_no_outlet_expansion: T2 —— 选中集合的展开只允许出现在 selection.js
  与 `_kbInvertSel`(反选是**改选中**, 不是解析目标); 出口之外不得再长出第三套展开
- test_ctx_menu_variants_match_registry: T3 —— `tpl/ctx-menus.html` 的四支与登记表
  `ui=ctx-menu` 的 variant 集合一一对应(治 pitfall ctx-menu-branch-parity: 加了一支漏另一支)
- test_ctx_menu_action_families_parity: T4 —— 四支的**动作族**奇偶: 四支都必须有
  {开始/暂停/汇报/删除}, multi/member/group 还必须各有 {重新校验/跳检/限速/移动/标签分类/导出}
  (2026-10-09 用户报「单组右键菜单缺选项」的回归位)
- test_trigger_registry_entries_exist: T5 —— 登记表里每个 entry / calls.fn 都必须是源码里
  真实存在的方法名(治「登记了不存在的入口」这类反向漂移)
"""
import json
import re
from collections import Counter
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "static"
SHARED = STATIC / "shared"

# 与 JS 侧同构的方法声明正则: 本仓库 mixin 片段的方法恒为 4 空格缩进、单行签名
_METHOD_RE = re.compile(r"^    (?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{$")
_JS_KEYWORDS = frozenset(
    "if for while switch catch return else do try function await typeof new void delete in of".split()
)

UI_KINDS = {"ctx-menu", "kbd", "drawer"}
VARIANTS = {"multi", "episode", "member", "group"}
SCOPES = {"sel", "anchor", "cursor", "sel-first-cursor", "panel", "none"}
DISPATCHES = {"action", "edit", "delete", "export", "folder", "panel", "none"}

# 模板四支 -> 登记表 variant 名(模板按数据字段取名, 登记表按语义取名)
BRANCH_TO_VARIANT = {"multi": "multi", "episode": "episode", "member": "member", "group": "group"}

# T4 动作族: 四支都必须有的基线 + 必须齐的扩展族(缺一即该路径上"找不到该动作")
FAMILY_BASE = {"resume", "pause", "reannounce", "delete"}
FAMILY_EXT = {"recheck", "skip_check", "limits", "move", "meta", "export"}
FAMILY_EXT_BRANCHES = {"multi", "member", "group"}


def _read(name: str) -> str:
    return (SHARED / name).read_text(encoding="utf-8")


def _shared_js() -> dict:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(SHARED.glob("*.js"))}


def _defs() -> dict:
    """从 triggers.js 文本里取出 TRIGGER_DEFS —— 严格 JSON 字面量, 保证两侧同一份声明。"""
    text = _read("triggers.js")
    m = re.search(r"const TRIGGER_DEFS = (\{.*?\n\});", text, re.S)
    assert m, "triggers.js 里找不到 `const TRIGGER_DEFS = {...};`(登记表被改名/搬走? 同步本守阵)"
    return json.loads(m.group(1))


def _methods(text: str) -> list:
    """[(方法名, 起始行号)] —— 只认 4 空格缩进的 mixin 方法声明(本仓库统一风格)。"""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = _METHOD_RE.match(line)
        if m and m.group(1) not in _JS_KEYWORDS:
            out.append((m.group(1), i))
    return out


def _enclosing(text: str, lineno: int):
    """行号所在的方法名 —— 方法顺序排列, 取最后一个起始行 <= lineno 的。"""
    cur = None
    for name, start in _methods(text):
        if start <= lineno:
            cur = name
        else:
            break
    return cur


def _post_call_sites() -> Counter:
    """shared/*.js 里所有 `method: "POST"` 出现点 -> (文件名, 所在方法名) 多重集。

    !判据用 `method: "POST"` 而不是端点字符串: 端点可能来自变量(如 reannounce 的计划投递),
      只认字面量会留下盲区。POST 动词是**投递**这一动作本身的唯一可靠印记。
    !排除 triggers.js 自身: 它是这张登记表, 不是投递点(唯一方法 triggerDefs 只返回常量);
      它的文件头注释里就写着 `method: "POST"` 这个词, 不排除会把自己扫成表外项。
    """
    sites = Counter()
    for name, text in _shared_js().items():
        if name == "triggers.js":
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if 'method: "POST"' in line:
                sites[(name, _enclosing(text, i))] += 1
    return sites


def _ctx_menu_branches() -> dict:
    """ctx-menus.html 第一块 .ctx-menu 的四支 -> 各支的 @click 处理器列表(原文, 未归族)。"""
    src = _read("tpl/ctx-menus.html")
    body = src.split("<!-- 表头右键菜单")[0]  # 只取行右键菜单根块, 排除表头/文件优先级/抽屉菜单
    marks = [
        ("multi", 'v-if="menu.multi"'),
        ("episode", 'v-else-if="menu.episode"'),
        ("member", 'v-else-if="menu.hash"'),
        ("group", "<template v-else>"),
    ]
    positions = []
    for name, needle in marks:
        assert needle in body, f"ctx-menus.html 找不到 {name} 支的锚点 {needle}(四支结构变了? 同步本守阵)"
        positions.append((name, body.index(needle)))
    branches = {}
    for i, (name, pos) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(body)
        seg = body[pos:end].split("</template>")[0]
        branches[name] = re.findall(r'@click(?:\.stop)?="([^"]+)"', seg)
    return branches


def _scopes_ok(value: str) -> bool:
    """scope 串: `a` 或 `a|b`, 每个分量都在词表内。"""
    parts = str(value).split("|")
    return bool(parts) and all(p in SCOPES for p in parts)


def _handler_family(handler: str):
    """处理器原文 -> 规范动作族名(不属任何族的返回 None)。"""
    h = re.sub(r"\s+", " ", handler).strip()
    m = re.match(r"^(?:act|actTorrent|actEpisode|ctxAct)\('([a-z_]+)'", h)
    if m:
        arg = m.group(1)
        return {"location": "move"}.get(arg, arg)  # 批量菜单的"移动…"走 ctxAct('location')
    m = re.match(r"^torrentCmd\('([a-z\-]+)'", h)
    if m:
        return "recheck" if m.group(1) == "recheck" else None
    name = h.split("(")[0]
    for cand, fam in [
        ("ctxDelete", "delete"),
        ("delEpisode", "delete"),
        ("delTorrent", "delete"),
        ("delGroup", "delete"),
        ("recheckGroup", "recheck"),
        ("skipCheckTorrent", "skip_check"),
        ("skipCheckGroup", "skip_check"),
        ("editLimits", "limits"),
        ("editLimitsGroup", "limits"),
        ("editMove", "move"),
        ("editMoveGroup", "move"),
        ("openMetaDialog", "meta"),
        ("metaGroup", "meta"),
        ("ctxMeta", "meta"),
        ("exportTorrent", "export"),
        ("exportGroup", "export"),
    ]:
        if name == cand:
            return fam
    return None


def test_trigger_registry_shape() -> None:
    """登记表自身形状: 必填字段、id 唯一、枚举值在词表内、豁免项必须写 why。

    「豁免也要登记」是本表与普通白名单的分界 —— 白名单会越长越宽直到失去意义, 而一张
    每行都要写理由的表, 加宽的成本是可见的。
    """
    defs = _defs()
    assert set(defs) == {"ui", "calls"}, f"TRIGGER_DEFS 顶层键应只有 ui/calls, 实际 {sorted(defs)}"
    assert defs["ui"], "ui 表为空"
    assert defs["calls"], "calls 表为空"

    ids = []
    for row in defs["ui"]:
        missing = {"id", "ui", "entry", "scope", "dispatch"} - set(row)
        assert not missing, f"ui 行缺字段 {sorted(missing)}: {row}"
        assert row["ui"] in UI_KINDS, f"ui 行的 ui 值非法: {row}"
        assert row["dispatch"] in DISPATCHES, f"ui 行的 dispatch 非法: {row}"
        assert _scopes_ok(row["scope"]), f"ui 行的 scope 非法: {row}"
        if row["ui"] == "ctx-menu":
            assert row.get("variant") in VARIANTS, f"ctx-menu 行必须有合法 variant: {row}"
        else:
            assert "variant" not in row, f"非 ctx-menu 行不该有 variant: {row}"
        ids.append(row["id"])
    dup = [i for i, c in Counter(ids).items() if c > 1]
    assert not dup, f"ui 行 id 重复: {dup}"

    for row in defs["calls"]:
        missing = {"file", "fn", "ep", "scope", "why"} - set(row)
        assert not missing, f"calls 行缺字段 {sorted(missing)}: {row}"
        assert _scopes_ok(row["scope"]), f"calls 行的 scope 非法: {row}"
        if "none" in row["scope"].split("|"):
            assert row["why"].strip(), f"scope 含 none 的投递点必须写 why(豁免要说明理由): {row}"


def test_trigger_registry_call_sites_exact() -> None:
    """T1: POST 调用点与 calls 表双向相等 —— 这张表是「自动停靠」的强制网。

    表外项 = 有人加了投递点却没登记(新功能绕开作用域模型); 表内残留 = 声明腐烂(函数改名/删除)。
    两个方向都判红, 于是表与代码不会各自演化。
    """
    detected = _post_call_sites()
    registered = Counter((r["file"], r["fn"]) for r in _defs()["calls"])

    unregistered = sorted(k for k in detected if k not in registered)
    assert not unregistered, (
        "这些 POST 调用点的所在方法没有登记进 TRIGGER_DEFS.calls —— "
        "要么把动作改走统一出口, 要么在 triggers.js 里加一行并写明 scope/why: " + ", ".join(f"{f}::{fn}" for f, fn in unregistered)
    )
    stale = sorted(k for k in registered if k not in detected)
    assert not stale, (
        "TRIGGER_DEFS.calls 里这些登记项在源码里已找不到对应 POST 调用点"
        "(方法改名/删除/搬文件后忘了同步表): " + ", ".join(f"{f}::{fn}" for f, fn in stale)
    )


def test_trigger_registry_no_outlet_expansion() -> None:
    """T2: 选中集合的展开只允许出现在 selection.js 与 `_kbInvertSel`。

    `_bulkTargets` / `selHashSet` / `_kbTargets` 是**目标解析**的三个合法入口; 一旦别处又有
    人对 `selMembers` / `selGroups` 直接做展开, 就长出了第四套口径 —— 那正是「两套选中展开」
    的复发路径(conventions/webui-scope.md §3 机制 4)。
    `_kbInvertSel` 例外: 它产出一份**新的选中集合**(反选), 不是解析作用目标。
    """
    pattern = re.compile(
        r"\.\.\.this\.selMembers|this\.selMembers\.map|this\.selGroups\.map"
        r"|new Set\(this\.selMembers\)|\.\.\.this\.selGroups|new Set\(this\.selGroups\)"
    )
    offenders = []
    for name, text in _shared_js().items():
        for i, line in enumerate(text.splitlines(), start=1):
            if not pattern.search(line):
                continue
            fn = _enclosing(text, i)
            if name == "selection.js" or fn == "_kbInvertSel":
                continue
            offenders.append(f"{name}:{i}({fn}) {line.strip()}")
    assert not offenders, (
        "选中集合的展开出现在出口之外 —— 作用域口径必须收在 selection.js 的单点里, "
        "不要在触发点自己拆一遍(见 conventions/webui-scope.md §3):\n  " + "\n  ".join(offenders)
    )


def test_ctx_menu_variants_match_registry() -> None:
    """T3: 模板四支 ↔ 登记表 variant 集合一一对应(治 ctx-menu-branch-parity)。"""
    branches = _ctx_menu_branches()
    assert len(branches) == 4, f"ctx-menus.html 行右键菜单应有四支, 实际 {len(branches)}: {sorted(branches)}"
    template_variants = {BRANCH_TO_VARIANT[b] for b in branches}
    assert template_variants == VARIANTS, f"模板支到 variant 的映射不全: {sorted(template_variants)}"

    registered = {r["variant"] for r in _defs()["ui"] if r["ui"] == "ctx-menu"}
    assert registered == template_variants, (
        f"登记表 ctx-menu variant 集合 {sorted(registered)} 与模板四支 {sorted(template_variants)} 不一致"
        " —— 加了模板支没登记(或反之)"
    )


def test_ctx_menu_action_families_parity() -> None:
    """T4: 四支动作族奇偶 —— 2026-10-09「单组右键菜单缺选项」的回归位。

    症状是**不报错、不白屏**, 只是某条路径上「菜单里没这个选项」。人眼对不齐两批十几项,
    故由守阵对账: 四支都必须有基线四族(开始/暂停/汇报/删除), multi/member/group 还必须
    各自都有扩展六族(重新校验/跳检/限速/移动/标签分类/导出)。
    """
    branches = _ctx_menu_branches()
    families = {}
    for name, handlers in branches.items():
        fams = {f for f in (_handler_family(h) for h in handlers)}
        families[name] = {f for f in fams if f}
    for name, fams in sorted(families.items()):
        missing = FAMILY_BASE - fams
        assert not missing, f"{name} 支缺基线动作族 {sorted(missing)}(实际 {sorted(fams)})"
        if name in FAMILY_EXT_BRANCHES:
            missing = FAMILY_EXT - fams
            assert not missing, (f"{name} 支缺扩展动作族 {sorted(missing)}(实际 {sorted(fams)}) —— "
                                 "同一批动作在各入口的项集不允许分叉")


def test_trigger_registry_entries_exist() -> None:
    """T5: 登记表里的 entry / calls.fn 必须是源码里真实存在的方法名(治反向漂移)。"""
    all_text = _shared_js()
    every_method = set()
    for text in all_text.values():
        every_method |= {n for n, _ in _methods(text)}

    for row in _defs()["ui"]:
        for entry in row["entry"].split("|"):
            assert entry in every_method, f"ui 行 {row['id']} 声明的 entry `{entry}` 不是任何片段里的方法(登记腐烂)"
    for row in _defs()["calls"]:
        text = all_text.get(row["file"])
        assert text is not None, f"calls 行声明了不存在的片段文件 {row['file']}"
        assert row["fn"] in {n for n, _ in _methods(text)}, (f"calls 行 {row['file']}::{row['fn']} 在该片段里找不到同名方法")
