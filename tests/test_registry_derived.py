"""test_registry_derived 测试计划: W5 单一 registry 派生收口的双跑守卫 + 演示测试

(plan 26-11-01-0106 W5/G9/G10/G11/G13; 方向 R6-a: schema 声明留在 config.schema,
registry 条目按名引用, 派生走延迟访问器)

## 测试计划(每个测试函数一条)
- test_deep_validator_dispatch_dual_run: 深度校验器分发双跑 —— 派生表(registry 条目
  validator 声明)与冻结手写基准逐位一致(键集合 + 校验器函数同一对象), diff 清零才允许切换
- test_registry_validator_decls_resolve: 全部条目的 validator 声明都在实现表中有对应项
  (registry 与 config.validation 脱节即红, 不静默缺省)
- test_deleted_allowed_actions_dual_run: 触发器 x 动作兼容表双跑 —— registry 条目
  deleted_ok 派生白名单(按注册序) == schema/fields 冻结手写基准 DELETED_ALLOWED_ACTIONS
- test_watch_fields_allowed_dual_run: watch_fields 取值域双跑 —— registry 条件条目
  watchable_field 派生(按注册序) == schema/fields 冻结手写基准 FIELD_WATCH_ALLOWED
- test_schema_plugin_table_derivation_order: schema.plugin_table() 派生序 == 手写声明序
  (两 kind 各一; payload/plugins 键面守卫依赖此序)
- test_registry_entries_schema_refs_resolve: 全部条目按名引用可解析且 kind/名字一致
  (声明零复制: 解析结果就是 config.schema 声明表的同一对象)
- test_choose_block_entry: choose 编排块入册 —— BLOCK_ENTRIES 有 choose, executor 是
  base.ChooseBlock, 键面按名引用解析 == compat.CHOOSE_KNOWN_KEYS, 文档片段非空
- test_plugin_doc_fragments_cover_rule_docs: 文档片段派生件一致性 —— ①全部条目
  doc_text() 非空(缺省取 schema 声明 help); ② conditions-and-actions.md 两张表的
  条目名集合 == registry 全部条件/动作名, 且标题计数(13/12)与注册数一致;
  ③ rules-and-triggers.md 的 on_torrent_deleted 行提到全部 deleted_ok 派生白名单动作
- test_demo_new_action_one_place: 演示(验收①)—— 新增一个哑动作只改 registry 一处
  (注册条目 + 自带 schema 声明), schema 插件表/校验/兼容表/执行分发全链路自动可用;
  对照组: 未声明 deleted_ok 的既有动作仍被 on_torrent_deleted 白名单拒绝(行为不回退)
"""
from pathlib import Path

from auto_qb.config import schema
from auto_qb.config.compat import CHOOSE_KNOWN_KEYS
from auto_qb.config.schema.fields import DELETED_ALLOWED_ACTIONS, FIELD_WATCH_ALLOWED
from auto_qb.config.validation import rules as validation_rules
from auto_qb.rules import registry
from auto_qb.rules.base import ChooseBlock

_RULE_DOCS = Path(__file__).resolve().parents[1] / "memory-bank" / "rule-system"

# ---------------------------------------------------------------------------
# 双跑守卫(验收②): 派生 vs 冻结手写基准, diff 清零
# ---------------------------------------------------------------------------


def test_deep_validator_dispatch_dual_run():
    """深度校验器分发双跑: 派生表 == 冻结手写基准(键集合一致 + 校验器同一函数对象)"""
    derived = validation_rules._plugin_spec_validators()
    baseline = validation_rules._PLUGIN_SPEC_VALIDATORS_BASELINE
    assert set(derived) == set(baseline), f"分发表键面 diff: {set(derived) ^ set(baseline)}"
    diff = [k for k in baseline if derived[k] is not baseline[k]]
    assert not diff, f"校验器函数对象不一致: {diff}"


def test_registry_validator_decls_resolve():
    """全部条目的 validator 声明都在实现表中有对应项(脱节即红, fail-fast 不静默)"""
    impls = validation_rules._SPEC_VALIDATOR_IMPLS
    unknown = [e.name for e in registry.iter_entries() if e.validator and e.validator not in impls]
    assert not unknown, f"validator 声明无实现: {unknown}"


def test_deleted_allowed_actions_dual_run():
    """兼容表双跑: registry deleted_ok 派生白名单 == DELETED_ALLOWED_ACTIONS 冻结基准(含序)"""
    assert registry.deleted_allowed_actions() == DELETED_ALLOWED_ACTIONS


def test_watch_fields_allowed_dual_run():
    """watch_fields 双跑: registry watchable_field 派生取值域 == FIELD_WATCH_ALLOWED 冻结基准(含序)"""
    assert registry.watch_fields_allowed() == FIELD_WATCH_ALLOWED


def test_schema_plugin_table_derivation_order():
    """schema.plugin_table() 派生序 == 手写声明序(condition/action 两 kind 各一)"""
    table = schema.plugin_table()
    assert table["condition"] == schema.CONDITION_PLUGINS
    assert table["action"] == schema.ACTION_PLUGINS


def test_registry_entries_schema_refs_resolve():
    """全部条目按名引用可解析, 且解析结果就是 config.schema 声明表的同一对象(声明零复制)"""
    for e in registry.iter_entries():
        p = e.plugin()  # 未登记的按名引用在这里 KeyError 显式炸出
        assert p.name == (e.schema_ref or e.name)
        table = schema.CONDITION_PLUGINS if e.kind == "condition" else schema.ACTION_PLUGINS
        assert any(x is p for x in table), f"{e.name}: 解析结果不是 config.schema 声明表内的同一对象"


def test_choose_block_entry():
    """choose 编排块入册: 条目存在/执行形态类/键面按名引用/文档片段"""
    entry = registry.BLOCK_ENTRIES.get("choose")
    assert entry is not None, "choose 编排块未入册(W5 统一注册三元组)"
    assert entry.executor is ChooseBlock
    assert entry.block_keys() == tuple(CHOOSE_KNOWN_KEYS)
    assert entry.doc.strip()


# ---------------------------------------------------------------------------
# 文档片段派生件一致性(验收④)
# ---------------------------------------------------------------------------


def _doc_table_names(heading_prefix: str) -> set:
    """取 md 指定 ## 节内表格的条目名(行首 `| \\`name\\`` 形态)"""
    text = (_RULE_DOCS / "conditions-and-actions.md").read_text(encoding="utf-8")
    names, in_section = set(), False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.startswith(heading_prefix)
            continue
        if in_section and line.startswith("| `"):
            names.add(line.split("`")[1])
    return names


def _doc_heading_count(heading_prefix: str) -> int:
    """取 md 标题里声明的条目数(如 '## 13 种条件' -> 13)"""
    text = (_RULE_DOCS / "conditions-and-actions.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(heading_prefix):
            return int(line.split(" ")[1].replace("种", ""))
    raise AssertionError(f"未找到标题: {heading_prefix}")


def test_plugin_doc_fragments_cover_rule_docs():
    """文档片段派生件与 rule-system 文档一致性: 全条目 doc_text() 非空 + 两张表名集合/计数一致 + 删除触发行覆盖白名单"""
    # 1. 文档片段派生件: 全部条目非空(缺省取 schema 声明 help —— 声明零复制)
    empty = [e.name for e in registry.iter_entries() if not e.doc_text().strip()]
    assert not empty, f"条目缺文档片段: {empty}"

    # 2. conditions-and-actions.md 条件/动作两表与 registry 双向一致
    cond_doc = _doc_table_names("## 13 种条件")
    act_doc = _doc_table_names("## 12 种动作")
    assert cond_doc == set(registry.CONDITIONS
                          ), (f"conditions-and-actions.md 条件表与 registry 脱节: {cond_doc ^ set(registry.CONDITIONS)}")
    assert act_doc == set(registry.ACTIONS
                         ), (f"conditions-and-actions.md 动作表与 registry 脱节: {act_doc ^ set(registry.ACTIONS)}")
    assert _doc_heading_count("## 13 种条件") == len(registry.CONDITIONS)
    assert _doc_heading_count("## 12 种动作") == len(registry.ACTIONS)

    # 3. rules-and-triggers.md 触发表 on_torrent_deleted 行覆盖全部 deleted_ok 派生白名单动作
    text = (_RULE_DOCS / "rules-and-triggers.md").read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if l.startswith("| `on_torrent_deleted`"))
    missing = [n for n in registry.deleted_allowed_actions() if f"`{n}`" not in row]
    assert not missing, f"rules-and-triggers.md on_torrent_deleted 行缺白名单动作: {missing}"


# ---------------------------------------------------------------------------
# 演示测试(验收①): 新增哑动作只改 1 处
# ---------------------------------------------------------------------------


def test_demo_new_action_one_place():
    """新增哑动作只改 registry 一处: schema/校验/兼容表/执行分发全链路自动可用

    注册即声明三元组(执行函数 + 自带 schema 声明 + 文档片段) + deleted_ok 兼容声明,
    不触碰 config.schema 声明表 / config.validation / 兼容表 —— 四个消费面全部从
    registry 条目派生, 注册后即时可见。
    """
    from auto_qb.config.schema import Plugin
    from auto_qb.config.validation import validate_config
    from auto_qb.rules.base import ActionResult
    from auto_qb.rules.registry import register_action

    @register_action(
        deleted_ok=True,
        doc="W5 演示哑动作: 只读不改种子, 注册即全链路可用",
        decl=Plugin("w5_demo_noop", "演示哑动作", "action", "bool", "只演示注册, 不做任何事"),
    )
    class W5DemoNoopAction:
        name = "w5_demo_noop"

        def __init__(self, spec):
            self.spec = spec

        def execute(self, ctx):
            return ActionResult.ok("w5 demo noop")

    try:
        # 1. schema 链路: 插件表派生自动可见(按名引用缺省 = 自带 decl)
        assert schema.plugins_by_kind("action")["w5_demo_noop"].name == "w5_demo_noop"
        payload_names = [p.name for p in schema.schema_payload()["plugins"]["action"]]
        assert "w5_demo_noop" in payload_names

        # 2. 校验链路: 校验器按 registry 派生, 哑动作不再报「未知动作」
        errs = validate_config(
            {"config": {
                "demo_rules": {
                    "r": {
                        "actions": [{
                            "type": "w5_demo_noop",
                            "params": True
                        }]
                    }
                }
            }}
        )
        assert errs == [], errs

        # 3. 兼容表链路: deleted_ok 声明即入 on_torrent_deleted 白名单
        assert "w5_demo_noop" in registry.deleted_allowed_actions()
        errs = validate_config(
            {
                "config":
                    {
                        "demo_rules":
                            {
                                "r":
                                    {
                                        "trigger": "on_torrent_deleted",
                                        "actions": [{
                                            "type": "w5_demo_noop",
                                            "params": True
                                        }]
                                    }
                            }
                    }
            }
        )
        assert errs == [], errs

        # 4. 执行分发: 工厂可创建、可执行
        inst = registry.create_action("w5_demo_noop", True)
        assert inst.execute(None).is_ok

        # 对照组(等价重构, 行为不回退): 未声明 deleted_ok 的既有动作仍被拒
        assert "add_tags" not in registry.deleted_allowed_actions()
        errs = validate_config(
            {
                "config":
                    {
                        "demo_rules":
                            {
                                "r":
                                    {
                                        "trigger": "on_torrent_deleted",
                                        "actions": [{
                                            "type": "add_tags",
                                            "params": ["X"]
                                        }]
                                    }
                            }
                    }
            }
        )
        assert any("不适用于 trigger 'on_torrent_deleted'" in e for e in errs), errs
    finally:
        registry.ACTIONS.pop("w5_demo_noop", None)
        registry.ACTION_ENTRIES.pop("w5_demo_noop", None)
