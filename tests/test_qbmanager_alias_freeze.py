"""QbManager 旧名委托面冻结守阵(plan web-state-alias-disposal W0)。

守什么: 内核化重构在 `core/qbmanager.py` 上留下的迁移过渡层 —— `_WEB_STATE_ALIAS`(20 字段 +
`__getattr__`/`__setattr__` 双 dunder)与七节旧名单行委托 —— 已由分诊清单逐名定性
(`memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json`)。处置纪律
(conventions/modules.md「兼容层现状」)是**新代码一律用新名, 不再往委托层加东西**; 本守阵把
这句纪律变成机检: 清单之外出现新的单行转发 / 别名表加字段, 立即红。清单与代码的双向一致
同时保证 W1–W3 各波删除时清单同步更新(删除提交只允许包含清单标「转发」的名字)。

判定是纯 AST 静态扫描, 不构造 QbManager(零运行期依赖)。形状判定 = 去掉 docstring 后恰一条
语句, 且该语句的自表达式/赋值目标以 `self.<svc>`(svc ∈ ctx/web/hr/host/store/api/state/
config/task_queue)起链 —— 即「单行委托」的形态学定义; 内核自有方法(多语句体 / 事件广播 /
`self._client` 一类自有属性)天然不命中, 分诊清单把它们显式标「kernel/保留」防误删。

## 测试计划

- test_alias_table_matches_triage: `_WEB_STATE_ALIAS` 字段与映射 == 清单 alias_layer(双向), dunder 存在性与清单一致
- test_delegation_surface_is_frozen: AST 扫出的单行转发集合 == 清单标 forward/facade 的成员集合(双向: 清单外新增 / 清单内已删)
- test_kernel_members_stay_non_forward: 清单标 kernel 的成员不得退化为单行转发
- test_triage_counts_are_consistent: 清单 meta.counts 与条目自洽
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QBMANAGER = ROOT / "src" / "auto_qb" / "core" / "qbmanager.py"
TRIAGE = ROOT / "memory-bank" / "plans" / "26-10-01-0350-plan-web-state-alias-disposal.triage.json"

# 单行委托的服务根: 表达式自 self.<svc> 起链即视为转发(events/自持属性不在此列 —— 内核语义)
_SERVICE_ROOTS = {"ctx", "web", "hr", "host", "store", "api", "state", "config", "task_queue"}


def _triage() -> dict:
    assert TRIAGE.exists(), f"分诊清单缺失: {TRIAGE} —— 旧名冻结以清单为基准, 缺了先补清单"
    return json.loads(TRIAGE.read_text(encoding="utf-8"))


def _roots_at_service(node: ast.AST) -> bool:
    """表达式是否自 self.<svc> 起链(Attribute/Call 连降到 Name('self'), 取紧邻 self 的属性)。"""
    last = None
    while True:
        if isinstance(node, ast.Name):
            return node.id == "self" and last in _SERVICE_ROOTS
        if isinstance(node, ast.Attribute):
            last = node.attr
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            return False


def _is_single_line_forward(fn) -> bool:
    """单行转发形状: 去 docstring 后恰一条语句, 其表达式/赋值目标或值自 self.<svc> 起链。"""
    body = list(fn.body)
    if (
        body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and
        isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Return):
        return stmt.value is not None and _roots_at_service(stmt.value)
    if isinstance(stmt, ast.Expr):
        return _roots_at_service(stmt.value)
    if isinstance(stmt, ast.Assign):
        return any(_roots_at_service(t) for t in stmt.targets) or _roots_at_service(stmt.value)
    return False


def _scan_qbmanager():
    """扫描 QbManager 类体: (别名表, 双 dunder, 单行转发名集合, 全部 def)。"""
    tree = ast.parse(QBMANAGER.read_text(encoding="utf-8"))
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "QbManager"), None)
    assert cls is not None, "qbmanager.py 里找不到 QbManager 类"
    alias_table, dunders, forwards, defs = None, [], set(), {}
    for node in cls.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_WEB_STATE_ALIAS":
                    alias_table = {k.value: v.value for k, v in zip(node.value.keys, node.value.values)}
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs[node.name] = node
            if node.name.startswith("__") and node.name.endswith("__") and node.name != "__init__":
                dunders.append(node.name)
            if _is_single_line_forward(node):
                forwards.add(node.name)
    return alias_table, dunders, forwards, defs


def test_alias_table_matches_triage():
    alias_table, dunders, _, _ = _scan_qbmanager()
    doc = _triage()
    fields = doc["alias_layer"]["fields"]
    assert alias_table is not None, ("_WEB_STATE_ALIAS 已被删除? 只允许发生在 W3(删别名层本体), 且同波更新分诊清单")
    expected = {old: spec["new"] for old, spec in fields.items()}
    added = sorted(set(alias_table) - set(expected))
    removed = sorted(set(expected) - set(alias_table))
    changed = sorted(k for k in set(alias_table) & set(expected) if alias_table[k] != expected[k])
    assert not (added or removed or changed), (
        f"别名表与分诊清单不一致 —— 新增 {added} / 缺失 {removed} / 映射变更 {changed}; "
        "清单之外不得新增旧字段(conventions/modules.md), 确需变更先改清单再改表"
    )
    assert sorted(dunders) == sorted(
        doc["alias_layer"]["dunders"]
    ), (f"别名层 dunder 集合变化: 代码 {sorted(dunders)} vs 清单 {sorted(doc['alias_layer']['dunders'])}")


def test_delegation_surface_is_frozen():
    _, _, forwards, _ = _scan_qbmanager()
    frozen = {m["name"] for m in _triage()["members"] if m["category"] in ("forward", "facade")}
    unexpected = sorted(forwards - frozen)
    stale = sorted(frozen - forwards)
    assert not unexpected, (
        f"清单之外新增旧名单行委托: {unexpected} —— conventions/modules.md 明文禁止新代码走旧名; "
        "确属迁移过渡需要的, 先更新分诊清单 JSON 并在任务档案记录理由"
    )
    assert not stale, (f"清单成员已不是单行转发(已删除或改写?): {stale} —— 同步更新分诊清单 JSON; "
                       "删除提交只允许包含清单标「forward」的名字")


def test_kernel_members_stay_non_forward():
    _, _, forwards, defs = _scan_qbmanager()
    kernel = [m["name"] for m in _triage()["members"] if m["category"] == "kernel" and m["name"] in defs]
    became_forward = sorted(n for n in kernel if n in forwards)
    assert not became_forward, (f"内核自有方法退化为单行转发: {became_forward} —— 分诊清单标「kernel/保留」的连接/节拍/相位"
                                "方法是内核语义, 不是委托层成员")


def test_triage_counts_are_consistent():
    doc = _triage()
    members = doc["members"]
    counts = doc["meta"]["counts"]
    actual = {
        "alias_fields": len(doc["alias_layer"]["fields"]),
        "forward": sum(1 for m in members if m["category"] == "forward"),
        "facade": sum(1 for m in members if m["category"] == "facade"),
        "kernel": sum(1 for m in members if m["category"] == "kernel"),
    }
    for key, value in actual.items():
        assert counts.get(key) == value, f"清单 meta.counts.{key}({counts.get(key)})与条目实测({value})不一致"
