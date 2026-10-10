"""test_config_schema 测试计划: 图形化配置编辑器的 UI 元数据一致性守卫

## 测试计划(每个测试函数一条)
- test_top_level_keys_match_validation: schema 顶层键集合 == KNOWN_CONFIG_KEYS(防漏登记配置键)
- test_object_section_keys_match_validation: 各对象段子键集合 == 对应 KNOWN_*_KEYS
- test_notify_channels_hidden_from_ui_but_kept_in_contract: notify.channels 暂不图形化(2026-10-10 报障: 取消勾选写空列表 → 脏标记不消 + 保存被"必须是非空列表"拒) —— schema 保留该字段且打 hidden(键面守卫以 schema 为单点, 摘字段 = 判删键)/ hidden 声明面恰好一处 / KNOWN_NOTIFY_KEYS 仍有该键(存量配置合法)/ 校验仍接受 platform 条目、仍拒绝空列表
- test_tracker_fields_match_validation: 站点字段集合 == KNOWN_TRACKER_KEYS
- test_tracker_hr_fields_match_validation: 站点 hr 字段集合 == KNOWN_TRACKER_HR_KEYS
- test_hr_sites_fields_match_validation: hr_check.sites 条目字段集合 == KNOWN_HR_SITE_KEYS
- test_rule_fields_cover_rule_known_keys: 规则级字段(+conditions/actions 专段) == RULE_KNOWN_KEYS
- test_condition_plugins_cover_registry / test_action_plugins_cover_registry: 插件表覆盖全部已注册插件
- test_field_kinds_are_declared: 所有 Field.kind 在 KINDS 中
- test_readonly_fields_are_program_managed: readonly(程序托管)点位清单 == {schema_version, data_dir, state_file, fs};
  R 级段全部打标; fs 段与其叶子 path_map 都打标(前端叶子分支只认自身 Field.readonly)
- test_plugin_kinds_are_declared: 所有 Plugin.spec_kind/item_kind 在约定集合中, 且形态自洽
- test_enum_fields_have_options / test_object_fields_have_children: enum 有选项, object 有子字段
- test_optional_only_on_object_fields: optional(整段可省略, 前端以开关控制)仅用于 object 字段, 且与 required 互斥
- test_unit_default_only_on_unit_kinds: unit_default 仅用于 UNIT_KINDS 且在合法单位表内
- test_unit_kind_defaults_are_parseable: UNIT_KINDS 字段的 default 可拆为 数值+单位(单位合法)
- test_checking_action_spec_keys_match_validation: checking 动作 spec 字段 == CHECKING_ACTION_KNOWN_KEYS
- test_deleted_trigger_whitelist_matches_validation: 删除触发白名单与 validation 一致
- test_schema_payload_is_complete: schema_payload 含全部前端所需分区
- test_tri_state_marks_site_hr_str_fallback_keys: tri_state(站点级「覆盖为空」)声明面守卫 —— 全库仅
  站点 hr 回退链 4 个 str 键打标, bool/list 键不标(_strip_none 豁免按此派生, 打错位置 = '' 语义误翻转)
- test_strip_exempt_keys_derive_from_schema: validation 的站点剥离豁免键集合 == schema tri_state 声明
- test_grouping_cross_group_conflict_check_default_false / _valid_bool / _non_bool_aggregates:
  新键 grouping.cross_group_conflict_check(计划 26-10-04-0107 S1) —— dataclass 缺省 false /
  合法 bool 通过校验 / 非 bool 聚合报错
- test_readonly_config_paths_exact_and_order: readonly 点路径集合与**顺序**逐位钉住(4 条)
- test_readonly_config_paths_walk_contract: 用合成结构钉遍历契约 —— ui_only 段须 `continue`(不
  断链) · 前缀须逐层拼接 · 非 readonly object 段须递归(issue 26-10-08-0903-schema-surface)
- test_plugins_by_kind_condition_and_action_branches: plugins_by_kind 的 condition/action 两支
  分别返回对应插件表(旧守卫只走 action 一支) · 未知 kind 落到 action 兜底
- test_schema_payload_constants_keys_exact: constants 分区键集合逐位钉住(12 项)
- test_schema_payload_constants_values: 每个常量表与源常量的取值一致(顺序敏感)
- test_schema_payload_preset_key_metadata: hr_check_site_presets 每条键集合与逐字段取值钉住
"""
import re

import pytest

from auto_qb.config import schema
from auto_qb.config.validation import (
    CHECKING_ACTION_KNOWN_KEYS,
    DELETED_TRIGGER_ALLOWED_ACTIONS,
    KNOWN_CONFIG_KEYS,
    KNOWN_FS_KEYS,
    KNOWN_GROUPING_KEYS,
    KNOWN_HR_CHANNEL_KEYS,
    KNOWN_HR_CHECK_KEYS,
    KNOWN_HR_KEYS,
    KNOWN_LOG_KEYS,
    KNOWN_NOTIFY_KEYS,
    KNOWN_QBITTORRENT_KEYS,
    KNOWN_QB_TRAFFIC_KEYS,
    KNOWN_HR_SITE_KEYS,
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
        ("fs", KNOWN_FS_KEYS),
        ("web", KNOWN_WEB_KEYS),
        ("notify", KNOWN_NOTIFY_KEYS),
        ("qb_traffic", KNOWN_QB_TRAFFIC_KEYS),
        ("hr", KNOWN_HR_KEYS),
        ("hr_check", KNOWN_HR_CHECK_KEYS),
        ("channel", KNOWN_HR_CHANNEL_KEYS),
        ("add_episode_tags", KNOWN_ADD_EPISODE_TAGS_KEYS),
    ],
)
def test_object_section_keys_match_validation(top_key, known):
    """各对象段子键集合必须与 validation 的已知键一致

    "channel" 不是顶层键而是 hr_check 下的子段, 故单独取它的字段表。
    """
    sub = {"channel": schema.HR_CHECK_CHANNEL_FIELDS}.get(top_key)
    got = _field_map(sub) if sub is not None else _nested(top_key)
    assert set(got) == known


def test_notify_channels_hidden_from_ui_but_kept_in_contract():
    """notify.channels: 暂不图形化(2026-10-10 报障), 但配置契约一环都不能少 —— 四面各一条

    背景: v1 渠道值域只有 platform 一档, 而 loader 缺省即 ["platform"], 于是设置页那个
    keyed_list 勾选框两个方向都表达不出有效差异 —— 勾选只是写一条与缺省等价的键; 取消
    则写空列表, 既与"键缺失"不同构(全树 JSON 对比的脏标记消不掉, 用户看到"勾了又取消
    仍提示有改动未保存"), 又被校验层以「必须是非空列表」拒绝保存。处置 = 打 Field.hidden
    (不进 UI 渲染), **不是**从 schema 摘字段。

    四面(少一条就会以另一种方式复发):
    1. schema 的 notify 子字段里**仍有** channels 且 hidden=True —— 键面守卫
       (test_config_key_surface)以 schema 为键面单点, 直接摘字段会被判成"删键"(破坏性变更:
       抬版本 + 注册迁移), 而本次根本没有改配置契约;
    2. hidden 的声明面恰好是这一处 —— 该标记是"键合法但 UI 表达不出差异"的专用口, 别拿它
       藏别的字段(藏了等于配置项静默消失, 用户再也改不到);
    3. KNOWN_NOTIFY_KEYS 仍有 channels —— 存量配置里已落盘的这个键必须仍然合法, 从校验层
       摘掉 = 老配置启动即报"未知键"(比原报障严重得多);
    4. 校验仍接受 `- platform: {}`、仍拒绝空列表 —— 前者是存量配置形态, 后者是本次报障的
       保存报错面(放开空列表是另一件事, 需要先给出"空 = 一个渠道都不选"的语义)。
    """
    from auto_qb.config.validation import validate_config

    sub = _nested("notify")
    assert "channels" in sub, ("schema 的 notify 段没了 channels —— 键面守卫会把它判成删键(破坏性变更), 本次只是暂不图形化")
    assert sub["channels"].hidden is True, "notify.channels 未打 hidden —— 它在 UI 上表达不出有效差异(见报障 2026-10-10)"

    hidden = []
    for top in schema.real_config_fields():

        def walk(fields):
            for f in fields:
                if f.hidden:
                    hidden.append(f.key)
                walk(f.fields or ())

        walk((top, ))
    assert sorted(hidden) == ["channels"], f"hidden 声明面变了({sorted(hidden)}) —— 该标记只用于'键合法但 UI 表达不出差异'"

    assert "channels" in KNOWN_NOTIFY_KEYS, "KNOWN_NOTIFY_KEYS 丢了 channels —— 存量配置里的该键会变成'未知键'"
    assert validate_config({"config": {"notify": {"channels": [{"platform": {}}]}}}) == []
    errs = validate_config({"config": {"notify": {"channels": []}}})
    assert any("config.notify.channels: 必须是非空列表" in e for e in errs), errs


def test_tracker_fields_match_validation():
    """站点段字段集合 == KNOWN_TRACKER_KEYS

    hr_check 例外: 旧键兼容保留在 KNOWN_TRACKER_KEYS(校验层接受但忽略), 但不再图形化 ——
    站点配置已整体上收到 hr_check.sites(计划 26-09-27-1318 REV2)。
    """
    assert set(_field_map(schema.TRACKER_FIELDS)) | {"hr_check"} == KNOWN_TRACKER_KEYS


def test_tracker_hr_fields_match_validation():
    """站点 hr 段字段集合 == KNOWN_TRACKER_HR_KEYS"""
    assert set(_field_map(schema.TRACKER_HR_FIELDS)) == KNOWN_TRACKER_HR_KEYS


def test_hr_sites_fields_match_validation():
    """hr_check.sites 条目字段集合 == KNOWN_HR_SITE_KEYS(站点接入卡片的数据驱动依据)"""
    assert set(_field_map(schema.HR_CHECK_SITES_FIELDS)) == KNOWN_HR_SITE_KEYS


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


def test_readonly_fields_are_program_managed():
    """readonly(程序托管)点位清单(issue 26-09-28-2135): 前端禁用渲染与 writer 写盘回退的共同单点

    漏标 = UI 渲染可编辑但保存被覆盖/回退且反馈误导(本 issue 的根因); 多标 = 用户改不了
    本该能改的字段。清单断言钉住当前 4 个点位; R 级段与 readonly 的包含关系一并钉住
    (新增 R 级段必须同时打 readonly 标, 否则重演「可编辑但不生效」)。
    """
    from auto_qb.config.impact import RESTART_SECTIONS

    assert set(schema.readonly_config_paths()) == {"schema_version", "data_dir", "state_file", "fs"}
    for key in ("schema_version", "data_dir", "state_file"):
        assert _top_field(key).readonly, f"{key} 缺 readonly 标"
    for key in sorted(RESTART_SECTIONS):
        assert _top_field(key).readonly, f"R 级段 {key} 缺 readonly 标(保存回退但 UI 可编辑, 反馈误导)"
    # fs 段整体 readonly, 其下叶子(path_map)也要打标 —— 前端叶子分支只认自身 Field.readonly
    path_map = _nested("fs")["path_map"]
    assert path_map.readonly, "fs.path_map 缺 readonly 标(叶子会渲染成可编辑控件)"


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
    for name in (
        "triggers", "execute_once", "stop_if", "checking_modes", "hr_modes", "state_attrs", "hr_check_site_presets"
    ):
        assert payload["constants"][name], f"constants 缺少 {name}"
    # 内置站点档案: 卡片渲染的数据源, 每条须含 id/adapter/双域(26-09-27-1930: web_domain 派生
    # 页面地址, tracker_domain 供映射制绑定状态行展示)
    presets = payload["constants"]["hr_check_site_presets"]
    assert all({"id", "adapter", "web_domain", "tracker_domain"} <= set(p) for p in presets), presets


def test_tri_state_marks_site_hr_str_fallback_keys():
    """tri_state(站点级「覆盖为空」, report 26-10-03-0504 方案 B 阶段 1)声明面守卫

    全库 schema 只允许站点 hr 回退链的 4 个 str 键打标(_strip_none 豁免按键集合派生, 打错位置 =
    全局段或其它键的 '' 语义被意外翻转); bool 键不标(config 层 "false" 本可区分), list 键不标
    (exclude_* 保持并集语义, 空 == 缺失)。
    """
    expected = {"add_tag", "add_category", "add_tag_for_satisfied", "add_category_for_satisfied"}
    marked = {f.key for f in _all_fields() if f.tri_state}
    assert marked == expected, f"tri_state 打标面漂移: {marked} != {expected}"
    hr_fields = _field_map(schema.HR_OUTPUT_FIELDS)
    for key in expected:
        assert hr_fields[key].kind == "str", f"{key}: tri_state 仅适用于 str 回退链键"
    unmarked = ("overwrite_category", "overwrite_category_for_satisfied", "exclude_tags", "exclude_categories")
    assert all(not hr_fields[k].tri_state for k in unmarked), "bool/list 键不得打 tri_state 标"


def test_strip_exempt_keys_derive_from_schema():
    """validation._strip_none 的站点剥离豁免键集合必须恰等于 schema tri_state 声明(单一事实来源)

    豁免集合在 validation/core.py 按 HR_OUTPUT_FIELDS 的 tri_state 标派生 —— 本守卫钉住派生
    关系本身, 防未来有人绕开 schema 手写第二份清单造成「声明」与「剥离行为」漂移。
    """
    from auto_qb.config.validation.core import _TRI_STATE_SITE_KEYS

    assert _TRI_STATE_SITE_KEYS == {f.key for f in schema.HR_OUTPUT_FIELDS if f.tri_state}
    assert len(_TRI_STATE_SITE_KEYS) == 4


# ---------- grouping.cross_group_conflict_check(计划 26-10-04-0107 S1): 新键全链路守卫 ----------


def test_grouping_cross_group_conflict_check_default_false():
    """缺省时 dataclass 默认 false(保守默认, 行为与旧版逐字节一致)"""
    from auto_qb.config.models import GroupingConfig

    assert GroupingConfig().cross_group_conflict_check is False


def test_grouping_cross_group_conflict_check_valid_bool():
    """合法 bool(true/false)通过 fail-fast 校验"""
    from auto_qb.config.validation import validate_config

    assert validate_config({"config": {"grouping": {"cross_group_conflict_check": "true"}}}) == []
    assert validate_config({"config": {"grouping": {"cross_group_conflict_check": "false"}}}) == []


def test_grouping_cross_group_conflict_check_non_bool_aggregates():
    """非 bool 进 errors 聚合(走既有 _try(parse_bool, ...) 路径, 不打断其它键的报错)"""
    from auto_qb.config.validation import validate_config

    errors = validate_config({"config": {"grouping": {"cross_group_conflict_check": "maybe", "enabled": "also-bad"}}})
    assert any("config.grouping.cross_group_conflict_check" in e for e in errors)
    assert any("config.grouping.enabled" in e for e in errors)


# ---------- 键面/分支函数守阵(issue 26-10-08-0903-test-config-mutation-schema-surface) ----------
#
# 这组守阵对应变异审计里 schema/__init__.py 的 27 条「全套件杀不掉」候选:
# readonly_config_paths 8 · plugins_by_kind 3 · schema_payload 16。
# 旧守卫只钉了「当前输出」的一小部分(如 test_schema_payload_is_complete 只查了部分 constants 名),
# 于是字符串键名大小写、分支短路、递归参数这类「结果恰好一样」的变异全部存活。
# 这里改成: 能钉死的**逐位钉死**; 不能只靠当前扁平 schema 钉死的(遍历契约), 用**合成结构**探针钉住机制本身。


def test_readonly_config_paths_exact_and_order():
    """readonly 点路径 = 集合 + **顺序**逐位钉住

    顺序是契约的一部分: writer 的 _fallback_readonly_fields 按此顺序回退, 顺序漂移会让
    「段整体回退」的先后(如 fs 段与其叶子)对不上。旧守卫只用 set() 比较, 丢了顺序。
    """
    assert schema.readonly_config_paths() == ("data_dir", "state_file", "schema_version", "fs")


def test_readonly_config_paths_walk_contract(monkeypatch):
    """遍历契约(不依赖当前扁平 schema): ui_only 段须继续扫、前缀须逐层拼、非 readonly object 须递归

    现状里 4 条 readonly 路径**全在顶层**, 使 walk 的递归/前缀机制在真实数据上「看不出差别」——
    于是 `continue→break`、`if prefix else` 改假条件、`f.kind == "object"` 改成 `!=`/错串/错大小写、
    `walk(x, None)` 这类变异全部存活。这些恰恰是「未来把某个 readonly 叶挂进嵌套段」时最先炸的写法,
    所以用合成结构把机制钉住(比只断言当前输出更能挡住回归)。

    合成结构分两层, 每层各钉一条机制:
    - 顶层段: [ui_only 叶] [非 readonly object 段] —— ui_only 叶须被**跳过而非断链**, 否则后面的
      段再也扫不到(顶层经 real_config_fields 已滤掉 ui_only, 故只在**嵌套层**才真正可达);
    - 嵌套层: 非 readonly object 段里塞 [ui_only 叶] [readonly 叶] —— ui_only 叶必须 `continue`
      让 readonly 叶仍被收集(`break` 会断链丢它), 且 readonly 叶须带段前缀 `zz_seg.zz_inner`。
    """
    from auto_qb.config.schema import Field, Group

    inner = Field(
        key="zz_seg",
        label="zz_seg",
        kind="object",
        fields=(
            Field(key="zz_inner_ui", label="zz_inner_ui", kind="str", ui_only=True),
            Field(key="zz_inner", label="zz_inner", kind="str", readonly=True),
        ),
    )
    monkeypatch.setattr(schema, "GROUPS", (Group(key="zz", label="zz", fields=(inner, )), ))

    # ui_only 叶不断链(嵌套层) + 前缀逐层拼接 + 非 readonly object 段递归
    assert schema.readonly_config_paths() == ("zz_seg.zz_inner", )


def test_plugins_by_kind_condition_and_action_branches():
    """plugins_by_kind 的 condition 与 action **两支**都要走对(旧守卫只覆盖 action 一支)

    test_checking_action_spec_keys_match_validation 只调了 plugins_by_kind("action"), 因此
    `kind == "condition"` 这个分支被改成恒假 / 错串 / 错大小写、以及 `and False` 短路, 全套件都杀不掉。
    这里两支都断言, 并补「未知 kind 落到 action 兜底」的现有语义(单一 else 分支)。
    """
    assert schema.plugins_by_kind("condition") == {p.name: p for p in schema.CONDITION_PLUGINS}
    assert schema.plugins_by_kind("action") == {p.name: p for p in schema.ACTION_PLUGINS}
    # 非 "condition" 一律走 action 兜底(现语义): 误把 condition 分支扩大会让前端拿错 spec 结构
    assert schema.plugins_by_kind("不存在的 kind") == {p.name: p for p in schema.ACTION_PLUGINS}


def test_schema_payload_constants_keys_exact():
    """constants 分区键集合逐位钉住(旧守卫只抽查了其中 7 个名字的存在性)

    ``test_schema_payload_is_complete`` 用 ``for name in (...)`` 只验了部分常量存在 —— 键名被改成
    ``XXlog_levelsXX`` / ``LOG_LEVELS`` 这类大小写或前缀变体时, 抽查表里没有它, 于是存活。
    """
    payload = schema.schema_payload()
    assert set(payload["constants"]) == {
        "log_levels",
        "notify_levels",
        "notify_channels",
        "execute_once",
        "stop_if",
        "triggers",
        "checking_basic",
        "checking_modes",
        "hr_modes",
        "state_attrs",
        "deleted_allowed_actions",
        "hr_check_site_presets",
    }


def test_schema_payload_constants_values():
    """每个常量表的取值与源常量一致(顺序敏感) —— 钉住映射关系本身而非仅键名"""
    payload = schema.schema_payload()["constants"]
    assert payload["log_levels"] == list(schema.LOG_LEVELS)
    assert payload["notify_levels"] == list(schema.NOTIFY_LEVELS)
    assert payload["notify_channels"] == list(schema.NOTIFY_CHANNELS)
    assert payload["execute_once"] == list(schema.EXECUTE_ONCE)
    assert payload["stop_if"] == list(schema.STOP_IF)
    assert payload["triggers"] == list(schema.TRIGGERS)
    assert payload["checking_basic"] == list(schema.CHECKING_BASIC)
    assert payload["checking_modes"] == list(schema.CHECKING_MODES)
    assert payload["hr_modes"] == list(schema.HR_MODES)
    assert payload["state_attrs"] == list(schema.STATE_ATTRS)
    assert payload["deleted_allowed_actions"] == list(schema.DELETED_ALLOWED_ACTIONS)


def test_schema_payload_preset_key_metadata():
    """hr_check_site_presets 每条键集合 + 逐字段取值钉住(旧守卫只查 4 个键存在, 漏 3 个)

    这些键标亮了前端「站点接入卡片」的字段名; page_path/download_path/page_param 只在卡片上展示,
    错了不会抛异常, 只表现为卡片少一列/值串位 —— 正是「结果一样」的静默漂移。
    """
    from auto_qb.config.site_presets import SITE_PRESETS

    presets = schema.schema_payload()["constants"]["hr_check_site_presets"]
    assert {p["id"] for p in presets} == set(SITE_PRESETS)
    for entry in presets:
        src = SITE_PRESETS[entry["id"]]
        assert set(entry) == {
            "id", "adapter", "web_domain", "tracker_domain", "page_path", "download_path", "page_param"
        }, entry["id"]
        assert entry["adapter"] == src.adapter
        assert entry["web_domain"] == src.web_domain
        assert entry["tracker_domain"] == src.tracker_domain
        assert entry["page_path"] == src.page_path
        assert entry["download_path"] == src.download_path
        assert entry["page_param"] == src.page_param
