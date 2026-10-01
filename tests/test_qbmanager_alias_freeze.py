"""QbManager 旧名兼容层退役守阵(plan web-state-alias-disposal, W3 起为反复活守阵)。

守什么: 内核化重构在 `core/qbmanager.py` 上留下的迁移过渡层 —— `_WEB_STATE_ALIAS`(20 字段 +
`__getattr__`/`__setattr__` 双 dunder)与五节旧名单行委托 —— 已于 W3(2026-10-01)整体删除。
退役名单与类别永久留档在分诊清单
(`memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json`), 本守阵据此做
**反复活机检**: 往 QbManager 加回清单里的旧名 / 重建别名表或转发 dunder, 立即红 —— 「清完又
长出来」正是历史上别名层的成因(plan §04 风险表), conventions/modules.md「兼容层现状」明文
禁止新代码走旧名。

同面机检两块不删的面: D1 拍板**永久保留**的属性对(config/store/api/state/web/task_queue/
state_file, manager 即外观的公共面)与 17 个内核自有方法(连接/节拍/相位, 内核语义)—— 属性对
缺失 / 内核方法缺失或退化为单行转发, 同样红。

判定是纯 AST 静态扫描, 不构造 QbManager(零运行期依赖)。形状判定 = 去掉 docstring 后恰一条
语句, 且该语句的自表达式/赋值目标以 `self.<svc>`(svc ∈ ctx/web/hr/host/store/api/state/
config/task_queue)起链 —— 即「单行委托」的形态学定义; 内核自有方法(多语句体 / 事件广播 /
`self._client` 一类自有属性)天然不命中。

## 测试计划

- test_alias_layer_stays_gone: `_WEB_STATE_ALIAS` 表与 `__getattr__`/`__setattr__` dunder 不得复活
- test_retired_names_stay_gone: 清单 alias 字段 + forward 成员不得作为 QbManager 成员复活
- test_facade_members_stay: 清单标 facade(D1 永久保留)的属性对必须在位
- test_kernel_members_stay_non_forward: 清单标 kernel 的成员必须在位且不得退化为单行转发
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
    assert TRIAGE.exists(), f"分诊清单缺失: {TRIAGE} —— 退役名单以清单为基准, 缺了先补清单"
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


def test_alias_layer_stays_gone():
    alias_table, dunders, _, _ = _scan_qbmanager()
    assert alias_table is None, (
        "_WEB_STATE_ALIAS 别名表复活 —— 旧字段名转发层已随别名层处置 W3 退役; "
        "新代码一律走 self.web.<新名>(conventions/modules.md「兼容层现状」)"
    )
    assert not dunders, f"转发 dunder 复活: {dunders} —— __getattr__/__setattr__ 旧名转发已随 W3 删除"


def test_retired_names_stay_gone():
    _, _, _, defs = _scan_qbmanager()
    doc = _triage()
    retired = set(doc["alias_layer"]["fields"]) | {m["name"] for m in doc["members"] if m["category"] == "forward"}
    resurrected = sorted(retired & set(defs))
    assert not resurrected, (
        f"退役旧名在 QbManager 上复活: {resurrected} —— 兼容层已随 W3 删除, 调用方一律走新名口"
        "(self.web.* / ctx.* / host.get(...)); 确需恢复先更新分诊清单并在任务档案记录理由"
    )


def test_facade_members_stay():
    _, _, _, defs = _scan_qbmanager()
    facade = {m["name"] for m in _triage()["members"] if m["category"] == "facade"}
    missing = sorted(facade - set(defs))
    assert not missing, (f"D1 拍板永久保留的外观属性对缺失: {missing} —— manager 即外观的公共面(340/309/134 处直读), "
                         "删除属决策点 D1 范围, 不是普通清理")


def test_kernel_members_stay_non_forward():
    _, _, forwards, defs = _scan_qbmanager()
    kernel = [m["name"] for m in _triage()["members"] if m["category"] == "kernel"]
    missing = sorted(n for n in kernel if n not in defs)
    became_forward = sorted(n for n in kernel if n in defs and n in forwards)
    assert not missing, f"内核自有方法缺失: {missing} —— 连接/节拍/相位方法是内核语义, 不随兼容层清理删除"
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
