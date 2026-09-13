"""test_config_schema 测试计划: 图形化配置编辑器的 UI 元数据一致性守卫

## 测试计划(每个测试函数一条)
- test_top_level_keys_match_validation: schema 顶层键集合 == KNOWN_CONFIG_KEYS(防漏登记配置键)
- test_object_section_keys_match_validation: 各对象段子键集合 == 对应 KNOWN_*_KEYS
- test_tracker_fields_match_validation: 站点字段集合 == KNOWN_TRACKER_KEYS
- test_tracker_hr_fields_match_validation: 站点 hr 字段集合 == KNOWN_TRACKER_HR_KEYS
- test_rule_fields_cover_rule_known_keys: 规则级字段(+conditions/actions 专段) == RULE_KNOWN_KEYS
- test_condition_plugins_cover_registry / test_action_plugins_cover_registry: 插件表覆盖全部已注册插件
- test_field_kinds_are_declared: 所有 Field.kind 在 KINDS 中
- test_plugin_kinds_are_declared: 所有 Plugin.spec_kind/item_kind 在约定集合中, 且形态自洽
- test_enum_fields_have_options / test_object_fields_have_children: enum 有选项, object 有子字段
- test_unit_default_only_on_unit_kinds: unit_default 仅用于 UNIT_KINDS 且在合法单位表内
- test_unit_kind_defaults_are_parseable: UNIT_KINDS 字段的 default 可拆为 数值+单位(单位合法)
- test_deleted_trigger_whitelist_matches_validation: 删除触发白名单与 validation 一致
- test_schema_payload_is_complete: schema_payload 含全部前端所需分区
"""
import re

import pytest

from auto_qb.config import schema
from auto_qb.config.validation import (
    CHECKING_ACTION_KNOWN_KEYS,
    DELETED_TRIGGER_ALLOWED_ACTIONS,
    KNOWN_CONFIG_KEYS,
    KNOWN_GROUPING_KEYS,
    KNOWN_HR_KEYS,
    KNOWN_LOG_KEYS,
    KNOWN_NOTIFY_KEYS,
    KNOWN_QBITTORRENT_KEYS,
    KNOWN_TRACKER_HR_KEYS,
    KNOWN_TRACKER_KEYS,
    KNOWN_WEB_KEYS,
    RULE_KNOWN_KEYS,
)
from auto_qb.rules import registry

# 规则级 spec 中由专段编辑器承担的两个键(不在 RULE_FIELDS 中)
RULE_PLUGIN_KEYS = {"conditions", "actions"}
# add_episode_tags 段键集合(validation 中无独立常量, 由 _validate_add_episode_tags 隐式定义)
KNOWN_ADD_EPISODE_TAGS_KEYS = {"enabled", "add_tag_single", "add_tag_multi"}


def _field_map(fields):
    return {f.key: f for f in fields}


def _top_field(key: str) -> schema.Field:
    """按顶层键取字段(找不到直接失败, 避免测试静默通过)"""
    fields = _field_map(schema.config_fields())
    assert key in fields, f"schema 缺少顶层字段 {key}"
    return fields[key]


def _nested(top_key: str) -> dict:
    """取顶层 object 字段的子字段映射"""
    return _field_map(_top_field(top_key).fields)


def test_top_level_keys_match_validation():
    """schema 顶层必须覆盖且仅覆盖 validate_config 允许的键(漏一个 = 该配置无法图形化)

    "rules" 为 UI 专段入口(真实配置键是动态的 "<名称>_rules"), 单独断言其存在。
    """
    assert set(_field_map(schema.real_config_fields())) == KNOWN_CONFIG_KEYS
    assert {f.key for f in schema.config_fields() if f.ui_only} == {"rules"}


@pytest.mark.parametrize(
    "top_key, known",
    [
        ("log", KNOWN_LOG_KEYS),
        ("qbittorrent", KNOWN_QBITTORRENT_KEYS),
        ("grouping", KNOWN_GROUPING_KEYS),
        ("web", KNOWN_WEB_KEYS),
        ("notify", KNOWN_NOTIFY_KEYS),
        ("hr", KNOWN_HR_KEYS),
        ("add_episode_tags", KNOWN_ADD_EPISODE_TAGS_KEYS),
    ],
)
def test_object_section_keys_match_validation(top_key, known):
    """各对象段子键集合必须与 validation 的已知键一致"""
    assert set(_nested(top_key)) == known


def test_tracker_fields_match_validation():
    """站点段字段集合 == KNOWN_TRACKER_KEYS"""
    assert set(_field_map(schema.TRACKER_FIELDS)) == KNOWN_TRACKER_KEYS


def test_tracker_hr_fields_match_validation():
    """站点 hr 段字段集合 == KNOWN_TRACKER_HR_KEYS"""
    assert set(_field_map(schema.TRACKER_HR_FIELDS)) == KNOWN_TRACKER_HR_KEYS


def test_rule_fields_cover_rule_known_keys():
    """规则级字段 + conditions/actions 专段 == RULE_KNOWN_KEYS"""
    assert set(_field_map(schema.RULE_FIELDS)) | RULE_PLUGIN_KEYS == RULE_KNOWN_KEYS


def test_condition_plugins_cover_registry():
    """条件插件表必须覆盖 registry 中全部已注册条件(数量与名称双向一致)"""
    assert {p.name for p in schema.CONDITION_PLUGINS} == set(registry.CONDITIONS)
    assert len(schema.CONDITION_PLUGINS) == len(registry.CONDITIONS)


def test_action_plugins_cover_registry():
    """动作插件表必须覆盖 registry 中全部已注册动作(数量与名称双向一致)"""
    assert {p.name for p in schema.ACTION_PLUGINS} == set(registry.ACTIONS)
    assert len(schema.ACTION_PLUGINS) == len(registry.ACTIONS)


def _all_fields():
    """递归展开全部字段(含插件子字段), 用于形态自检"""
    def walk(fields):
        for f in fields:
            yield f
            yield from walk(f.fields)

    top = list(schema.config_fields()) + list(schema.TRACKER_FIELDS) + list(schema.TRACKER_HR_FIELDS) + \
        list(schema.RULE_FIELDS)
    yield from walk(top)
    for plugins in schema.plugin_table().values():
        for p in plugins:
            yield from walk(p.fields)


def test_field_kinds_are_declared():
    """所有 Field.kind 必须是前端契约中声明过的类型(否则退化为文本框, 属于漏配)"""
    bad = [f.key for f in _all_fields() if f.kind not in schema.KINDS]
    assert not bad, f"未声明的 field kind: {bad}"


def test_plugin_kinds_are_declared():
    """插件 spec_kind 合法; list 形态必须声明 item_kind; enum 形态必须有 options"""
    for plugin in list(schema.CONDITION_PLUGINS) + list(schema.ACTION_PLUGINS):
        assert plugin.spec_kind in schema.SPEC_KINDS, f"{plugin.name}: 非法 spec_kind {plugin.spec_kind}"
        if plugin.spec_kind == "list":
            assert plugin.item_kind in schema.ITEM_KINDS, f"{plugin.name}: list 缺少合法 item_kind"
        if plugin.spec_kind == "enum":
            assert plugin.options, f"{plugin.name}: enum 形态必须有 options"
        if plugin.spec_kind == "object":
            assert plugin.fields, f"{plugin.name}: object 形态必须有子字段"


def test_enum_fields_have_options():
    """enum 字段必须有选项, 且默认值(若给出)必须在选项内"""
    for f in _all_fields():
        if f.kind == "enum":
            assert f.options, f"{f.key}: enum 字段缺少 options"
            if isinstance(f.default, str) and f.default:
                assert f.default in f.options, f"{f.key}: 默认值 {f.default} 不在选项中"


def test_object_fields_have_children():
    """object 字段必须有子字段(空子表单无意义)"""
    for f in _all_fields():
        if f.kind == "object":
            assert f.fields, f"{f.key}: object 字段缺少子字段"


def test_optional_only_on_object_fields():
    """optional(整段可省略, 前端以开关控制)只允许用于 object 字段"""
    for f in _all_fields():
        if f.optional:
            assert f.kind == "object", f"{f.key}: optional 仅适用于 object 字段"
            assert not f.required, f"{f.key}: optional 与 required 互斥"


def test_unit_default_only_on_unit_kinds():
    """unit_default(数值 + 单位下拉的首选单位)只允许用于 UNIT_KINDS, 且必须是合法单位

    否则前端会渲染一个永远取不到的默认单位(下拉框里没有该选项), 表现为"单位总是跳到第一个"。
    """
    units = {"time": schema.TIME_UNITS, "size": schema.SIZE_UNITS, "speed": schema.SPEED_UNITS}
    for f in _all_fields():
        if not f.unit_default:
            continue
        assert f.kind in schema.UNIT_KINDS, f"{f.key}: unit_default 仅适用于 {sorted(schema.UNIT_KINDS)}"
        assert f.unit_default in units[f.kind], f"{f.key}: unit_default {f.unit_default} 不在 {units[f.kind]} 中"


def test_unit_kind_defaults_are_parseable():
    """UNIT_KINDS 字段的 default(若非空)必须能被"数值 + 单位"正则拆开, 且单位在选项表内

    前端按该值预填下拉框; 若 default 写成 "30" 这类缺单位的串, 单位会退化为回退值,
    用户看到的首选单位与实际配置不一致。
    """
    units = {"time": schema.TIME_UNITS, "size": schema.SIZE_UNITS, "speed": schema.SPEED_UNITS}
    for f in _all_fields():
        if f.kind not in schema.UNIT_KINDS or not isinstance(f.default, str) or not f.default:
            continue
        m = re.match(r"^([\d.]*)\s*([A-Za-z/]*)$", f.default)
        assert m and m.group(1) and m.group(2), f"{f.key}: default {f.default!r} 无法拆为 数值+单位"
        assert m.group(2) in units[f.kind], f"{f.key}: default 单位 {m.group(2)} 不在 {units[f.kind]} 中"


def test_checking_action_spec_keys_match_validation():
    """checking 动作的 spec 字段 == validation.CHECKING_ACTION_KNOWN_KEYS"""
    plugin = schema.plugins_by_kind("action")["checking"]
    assert set(_field_map(plugin.fields)) == CHECKING_ACTION_KNOWN_KEYS


def test_deleted_trigger_whitelist_matches_validation():
    """删除触发可用动作白名单与 validation 一致(前端按 trigger 过滤动作下拉)"""
    assert set(schema.DELETED_ALLOWED_ACTIONS) == DELETED_TRIGGER_ALLOWED_ACTIONS


def test_schema_payload_is_complete():
    """schema_payload 必须含前端渲染所需的全部分区"""
    payload = schema.schema_payload()
    assert set(payload) == {"groups", "tracker_fields", "rule_fields", "plugins", "constants"}
    assert payload["plugins"]["condition"] == schema.CONDITION_PLUGINS
    assert payload["plugins"]["action"] == schema.ACTION_PLUGINS
    # 常量分区覆盖前端下拉所需的全部选项表
    for name in ("triggers", "execute_once", "stop_if", "checking_modes", "hr_modes", "state_attrs"):
        assert payload["constants"][name], f"constants 缺少 {name}"
