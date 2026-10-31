"""test_rule_compat 测试计划: 规则兼容层(config/compat.py 载入规范化单点, plan 26-11-01-0106 §3.2 W2-A/W2-B)

normalize_legacy_rule 是 legacy 规则词汇的唯一容身处: 引擎/校验器只认规范化后形态,
禁止「读 legacy 键」的第二语义分支(防 G4 hr 双语义分歧重演)。本文件钉四件事:
生产 5 条规则规范化快照(金标准零差异) / 行为零变化的转换等价性 / R1 两条附注
(错误定位回映射 + 命名透传) / 旧 state 载入回归(exec_history 去重键口径不变)。

⚠ config.yml 是生产红线: 本文件**不 import、不读取**它 —— 生产 5 条规则的 spec 原样
誊写为下方 `_PRODUCTION_RULES_YAML` 夹具(来源注明, 逐字含注释誊写; config.yml 若有
改动须人工同步此夹具并重审快照)。

⚠ 快照金标准口径(W2-B 重锚定): normalize 自 W2-B 起对每个动作项注入缺省 on_error
({policy: stop, retries: 3, backoff: 60}, schema.fields.ON_ERROR_DEFAULTS 单点)——
「含缺省字段」与旧行为零变化等价(policy=stop 即现行失败即止), 快照按注入后形态重锚定。

## 测试计划(每个测试函数一条)
- test_production_rules_snapshot: 生产 5 条规则(3 规则集)规范化快照比对 —— 金标准零差异:
  归一输出逐位等于预期快照(W2-B 起动作含缺省 on_error), conditions 透传零差异
  (来源: config.yml 191-285 行, 誊写夹具)
- test_snapshot_action_conversion_value_preserving: 快照动作转换保值 —— 每个规范化动作的
  (type, params) 与旧扁平形的 (键名, 值) 逐位相同(引擎 create_action 收到的 value 不变)
- test_normalize_idempotent: 幂等 —— normalize(normalize(x)) == normalize(x)(旧形输入与
  已规范形输入各验一次; 已规范形零改写, 缺 on_error 的规范形补缺省后收敛)
- test_on_error_default_injection: 缺省 on_error 注入(W2-B) —— 无 on_error 补全缺省对象、
  部分缺省补缺失键、已配置值零改写; 伪动作不注入; on_error 非 dict 原样透传交校验器报
- test_on_error_mixed_form_normalized: webui 动作卡写出的混合形 {动作键: 值, on_error: {...}}
  经单点漏斗翻译成规范形 {type, params, on_error}(载入链与直达校验器两条路一致)
- test_conditions_empty_string_no_branch: hhan `conditions: ''` 注记 —— 空串被 _strip_none
  载入前整键剔除, normalize 不另建分支(不出现 all/any 组合键), 无条件 = 直接过语义保持
- test_normalize_bulk_names_and_keys_passthrough: normalize_legacy_rules 组键/规则键与
  spec 非 conditions/actions 键零触碰(R1② 命名透传; D1: 原内容不被载入规范化改写)
- test_retired_pseudo_action_container_only: 伪动作 ignore_next_action_error 只做容器归一
  (params 原样透传, 不做 on_error 语义映射也不注入缺省 on_error —— D1 禁止);
  载入层识别/剔除对规范形与旧形都生效
- test_action_error_location_maps_back_flat: R1① 错误定位回映射 —— 结构错报「第 N 个动作 +
  actions[i]」扁平坐标; 深度校验错报 actions[i].<动作名>(不暴露 params 结构路径)
- test_validator_accepts_normalized_form: 校验器只认规范化形态 —— 直接写 {type, params} 新形
  通过校验且载入零再变换; on_error(W2-B)合法取值通过、非法子键/取值/边界 fail-fast 拒绝
- test_load_config_rules_normalized: 载入链顺序 —— load_config 后 cfg.rules_config 已是
  规范化形态(校验前归一), conditions 原样透传
- test_rule_name_composite_passthrough_exec_history: 复合形「组.规则」命名透传 —— 规范化
  配置载入后 Rule.name 保持「规则集.规则名」, exec_history 去重键「规则名:hash」前半不变
  (W2-B: on_error 注入不触碰键输入 —— 去重键 hash = 种子 infohash, 不含 spec 序列化)
- test_old_state_exec_history_regression: 旧 state 文件载入回归 —— 既有 exec_history 键
  (规则名:hash)读入后 get_exec_record 判定不变, 新写入沿用同一键口径(core/state.py:281);
  on_error 注入前后同一种子的去重判定不变(去重窗口零重置)
- test_engine_legacy_and_normalized_equivalent: 引擎消费等价 —— 旧扁平形与规范化形构造的
  Rule 动作实例同型, 执行行为一致(add_tags 同参调用)
"""
import json
import os
import tempfile

import yaml

from auto_qb.config import ConfigError, load_config
from auto_qb.config.compat import normalize_action_entry, normalize_legacy_rule, normalize_legacy_rules
from auto_qb.config.validation import _strip_none
from auto_qb.core.modules import rules_mod
from auto_qb.core.state import StateService
from auto_qb.rules.actions import AddTagsAction
from auto_qb.rules.base import VERDICT_EXECUTED, Rule
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager

# ---------------------------------------------------------------------------
# 生产规则夹具(红线声明: config.yml 零改零读, 以下为 191-285 行的逐字誊写, 注释保留)
# ---------------------------------------------------------------------------
_PRODUCTION_RULES_YAML = """\
config:
    # 来源: config.yml `add_drive_letter_tag_rules` / `skip_checking_rules` /
    # `hhan_checking_rules` 三段逐字誊写(2026-11-01, plan 26-11-01-0106 W2-A 快照基线)
    add_drive_letter_tag_rules:
        add_r_tag: # 为R盘的两个目录添加"R"标签
            enabled: true
            trigger: on_torrent_added
            cooldown: 5M
            conditions:
              - path:
                  - "regex:^R:/Download/PTing/"
                  - "regex:^R:/Download/ing/"
            actions:
              - add_tags:
                  - "R"     # 添加"R"标签

    skip_checking_rules:
        i_rule: # I盘: 种子全量校验
            enabled: true
            interval: 30M
            cooldown: 5M
            conditions:
              - path:
                  - "regex:^I:/"
            actions:
              - checking:
                    basic_check: filelist
                    with_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false
                    without_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false
        h_rule: # H盘: 有参考的跳检, 无参考的全量校验
            enabled: true
            interval: 30M
            cooldown: 5M
            conditions:
              - path:
                  - "regex:^H:/"
            actions:
              - checking:
                    basic_check: filelist
                    with_reference:
                        enabled: true
                        mode: skip-checking
                        auto_start: false
                    without_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false
        r_rule: # R盘: 种子全量校验
            enabled: true
            interval: 5M
            cooldown: 5M
            conditions:
              - path:
                  - "regex:^R:/"
            actions:
              - checking:
                    basic_check: filelist
                    with_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false
                    without_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false

    hhan_checking_rules:
        rule: # 全量校验
            enabled: true
            interval: 5M
            cooldown: 5M
            conditions: ''
            actions:
              - checking:
                    basic_check: filelist
                    with_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false
                    without_reference:
                        enabled: true
                        mode: full-checking
                        auto_start: false
"""


def _checking_params(with_mode: str) -> dict:
    """checking 动作参数(生产 4 条校验规则共用形状; BaseLoader 标量全为字符串)"""
    return {
        "basic_check": "filelist",
        "with_reference": {
            "enabled": "true",
            "mode": with_mode,
            "auto_start": "false"
        },
        "without_reference": {
            "enabled": "true",
            "mode": "full-checking",
            "auto_start": "false"
        },
    }


def _default_on_error() -> dict:
    """缺省 on_error(W2-B normalize 注入值; schema.fields.ON_ERROR_DEFAULTS 单点的快照副本)"""
    return {"policy": "stop", "retries": 3, "backoff": 60}


# 规范化金标准快照: 5 条规则(3 规则集)归一后的预期形态 —— 与引擎现行消费逐位等价
# (conditions 原样; 动作 {type, params, on_error} 参数值与旧扁平形逐位相同 + W2-B 注入的
# 缺省 on_error: policy=stop 即现行失败即止, 行为零变化), 快照按「含缺省字段」口径重锚定
_SNAPSHOT = {
    "add_drive_letter_tag_rules":
        {
            "add_r_tag":
                {
                    "enabled": "true",
                    "trigger": "on_torrent_added",
                    "cooldown": "5M",
                    "conditions": [{
                        "path": ["regex:^R:/Download/PTing/", "regex:^R:/Download/ing/"]
                    }],
                    "actions": [{
                        "type": "add_tags",
                        "params": ["R"],
                        "on_error": _default_on_error()
                    }],
                },
        },
    "skip_checking_rules":
        {
            "i_rule":
                {
                    "enabled":
                        "true",
                    "interval":
                        "30M",
                    "cooldown":
                        "5M",
                    "conditions": [{
                        "path": ["regex:^I:/"]
                    }],
                    "actions":
                        [
                            {
                                "type": "checking",
                                "params": _checking_params("full-checking"),
                                "on_error": _default_on_error()
                            }
                        ],
                },
            "h_rule":
                {
                    "enabled":
                        "true",
                    "interval":
                        "30M",
                    "cooldown":
                        "5M",
                    "conditions": [{
                        "path": ["regex:^H:/"]
                    }],
                    "actions":
                        [
                            {
                                "type": "checking",
                                "params": _checking_params("skip-checking"),
                                "on_error": _default_on_error()
                            }
                        ],
                },
            "r_rule":
                {
                    "enabled":
                        "true",
                    "interval":
                        "5M",
                    "cooldown":
                        "5M",
                    "conditions": [{
                        "path": ["regex:^R:/"]
                    }],
                    "actions":
                        [
                            {
                                "type": "checking",
                                "params": _checking_params("full-checking"),
                                "on_error": _default_on_error()
                            }
                        ],
                },
        },
    "hhan_checking_rules":
        {
            "rule":
                {
                    # conditions: '' 经 _strip_none 整键剔除, 快照中无 conditions 键(勿另建分支)
                    "enabled":
                        "true",
                    "interval":
                        "5M",
                    "cooldown":
                        "5M",
                    "actions":
                        [
                            {
                                "type": "checking",
                                "params": _checking_params("full-checking"),
                                "on_error": _default_on_error()
                            }
                        ],
                },
        },
}


def _normalized_production_rules() -> dict:
    """生产夹具走真实载入链前半: yaml.BaseLoader 解析 -> _strip_none -> normalize_legacy_rules"""
    data = yaml.load(_PRODUCTION_RULES_YAML, Loader=yaml.BaseLoader)
    data = _strip_none(data)
    normalize_legacy_rules(data)
    return data["config"]


# ------------------------------- 金标准快照 -------------------------------


def test_production_rules_snapshot():
    """生产 5 条规则规范化快照比对: 归一输出逐位等于预期快照(金标准零差异), conditions 透传"""
    cfg = _normalized_production_rules()
    for group_name, group in _SNAPSHOT.items():
        assert group_name in cfg, f"缺规则集 {group_name}"
        for rule_name, expected in group.items():
            actual = cfg[group_name][rule_name]
            assert actual == expected, f"{group_name}.{rule_name} 规范化快照零差异被破坏"
            # conditions 透传锚定: 归一前后 conditions 逐位相同(本期为现行消费形态, W3-A 才建树)
            if "conditions" in expected:
                raw = yaml.load(_PRODUCTION_RULES_YAML, Loader=yaml.BaseLoader)["config"][group_name][rule_name]
                assert actual["conditions"] == raw["conditions"], f"{group_name}.{rule_name} conditions 应零差异透传"


def test_snapshot_action_conversion_value_preserving():
    """快照动作转换保值: 规范形 (type, params) 与旧扁平形 (键名, 值) 逐位相同(引擎 value 不变)"""
    cfg = _normalized_production_rules()
    for group_name, group in cfg.items():
        if not group_name.endswith("_rules"):
            continue
        for rule_name, spec in group.items():
            for act in spec.get("actions") or []:
                assert set(act) == {"type", "params", "on_error"}, f"{group_name}.{rule_name} 动作应为规范三键形"
                legacy = {act["type"]: act["params"]}  # 旧扁平形还原
                assert normalize_action_entry(legacy) == act, f"{group_name}.{rule_name} 动作转换须保值"


# ------------------------------- 幂等 / 透传 -------------------------------


def test_normalize_idempotent():
    """幂等: normalize(normalize(x)) == normalize(x); 已规范形输入原样返回零改写"""
    legacy = {
        "enabled": "true",
        "conditions": [{
            "size": ">=1MiB"
        }, {
            "path": ["/a"]
        }],
        "actions": [{
            "add_tags": ["X"]
        }, {
            "checking": _checking_params("full-checking")
        }],
    }
    once = normalize_legacy_rule(legacy)
    assert normalize_legacy_rule(once) == once
    # 已规范形(含完整 on_error): 原样返回(同一内容), 且不新建 actions 列表项
    assert normalize_legacy_rule(once) == once
    # W2-B: 缺 on_error 的规范形在第一次 normalize 即补齐缺省, 其后收敛稳定(幂等不破坏)
    bare = {"actions": [{"type": "add_tags", "params": ["X"]}]}
    filled = normalize_legacy_rule(bare)
    assert filled["actions"][0] == {"type": "add_tags", "params": ["X"], "on_error": _default_on_error()}
    assert normalize_legacy_rule(filled) == filled
    # 顶层输入非 dict / 动作项非 dict / 无法识别的多键 dict: 原样透传交校验器报
    assert normalize_legacy_rule("oops") == "oops"
    assert normalize_action_entry("oops") == "oops"
    assert normalize_action_entry({}) == {}
    assert normalize_action_entry({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_on_error_default_injection():
    """缺省 on_error 注入(W2-B): 无 on_error 补全 / 部分缺省补缺失键 / 已配置值零改写; 异形透传"""
    # 无 on_error: 注入完整缺省对象(ON_ERROR_DEFAULTS 单点值)
    assert normalize_action_entry({"add_tags": ["X"]}) == {
        "type": "add_tags",
        "params": ["X"],
        "on_error": _default_on_error(),
    }
    # 部分缺省(policy=retry 自定义): 只补缺失的 retries/backoff, 已配置值零改写
    partial = {"type": "add_tags", "params": ["X"], "on_error": {"policy": "retry", "retries": 5}}
    assert normalize_action_entry(partial) == {
        "type": "add_tags",
        "params": ["X"],
        "on_error": {
            "policy": "retry",
            "retries": 5,
            "backoff": 60
        },
    }
    # 完整 on_error: 原样返回(同一内容, 零改写零补键)
    full = {"type": "add_tags", "params": ["X"], "on_error": {"policy": "continue", "retries": 0, "backoff": 1}}
    assert normalize_action_entry(full) == full
    # on_error 非 dict: 形状非法原样透传, 交校验器 fail-fast(normalize 不吞错误)
    bad = {"type": "add_tags", "params": ["X"], "on_error": "continue"}
    assert normalize_action_entry(bad) == bad
    # 输入不被就地改写(D1: 配置原内容原样保留)
    src = {"type": "add_tags", "params": ["X"]}
    normalize_action_entry(src)
    assert src == {"type": "add_tags", "params": ["X"]}


def test_on_error_mixed_form_normalized():
    """webui 动作卡混合形 {动作键: 值, on_error: {...}} -> 规范形(单点漏斗, 载入链直达一致)"""
    mixed = {"add_tags": ["X"], "on_error": {"policy": "continue"}}
    norm = normalize_action_entry(mixed)
    assert norm == {
        "type": "add_tags",
        "params": ["X"],
        "on_error": {
            "policy": "continue",
            "retries": 3,
            "backoff": 60
        },
    }
    # 混合形 + 非 dict on_error: 容器归一照做, on_error 原样透传交校验器报
    bad = normalize_action_entry({"add_tags": ["X"], "on_error": 1})
    assert bad == {"type": "add_tags", "params": ["X"], "on_error": 1}
    # 两键但无 on_error 且非单键旧形(动作键 + 未知键): 原样透传交校验器按扁平坐标报
    assert normalize_action_entry({"add_tags": ["X"], "bogus": 1}) == {"add_tags": ["X"], "bogus": 1}
    # 只剩 on_error(动作键缺失): 原样透传交校验器报结构错
    assert normalize_action_entry({"on_error": {"policy": "stop"}}) == {"on_error": {"policy": "stop"}}
    # 混合形经真实载入链等价: load 后 actions 已是规范形且校验通过
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - add_tags: [\"M\"]\n"
        "          on_error: {policy: continue}\n"
    )
    assert cfg.rules_config["my_rules"]["r1"]["actions"] == [
        {
            "type": "add_tags",
            "params": ["M"],
            "on_error": {
                "policy": "continue",
                "retries": 3,
                "backoff": 60
            },
        }
    ]


def test_normalize_bulk_names_and_keys_passthrough():
    """R1② 命名透传: 组键/规则键与 spec 非 conditions/actions 键零触碰; 输入 spec 不被就地改写"""
    spec = {
        "enabled": "true",
        "trigger": "on_torrent_added",
        "cooldown": "5M",
        "conditions": [{
            "path": ["regex:^R:/"]
        }],
        "actions": [{
            "add_tags": ["R"]
        }],
    }
    original = json.dumps(spec, ensure_ascii=False)
    data = {"config": {"组名_rules": {"规则名": spec}}}
    normalize_legacy_rules(data)
    group = data["config"]["组名_rules"]
    assert list(group) == ["规则名"], "规则键(命名后半)不得被改写"
    norm = group["规则名"]
    assert norm["enabled"] == "true" and norm["trigger"] == "on_torrent_added" and norm["cooldown"] == "5M"
    assert norm["conditions"] == spec["conditions"]
    assert norm["actions"] == [{"type": "add_tags", "params": ["R"], "on_error": _default_on_error()}]
    # 载入规范化不就地改写原 spec(D1: 配置原内容原样保留)
    assert json.dumps(spec, ensure_ascii=False) == original


# --------------------------- hhan 空串注记 / 两键边界 ---------------------------


def test_conditions_empty_string_no_branch():
    """hhan `conditions: ''` 注记: 空串被 _strip_none 载入前整键剔除, normalize 不另建分支"""
    raw = yaml.load("rule:\n  conditions: ''\n  actions:\n    - add_tags: ['X']\n", Loader=yaml.BaseLoader)
    stripped = _strip_none(raw)
    assert "conditions" not in stripped["rule"], "空串 conditions 应被 _strip_none 前置剔除"
    norm = normalize_legacy_rule(stripped["rule"])
    assert "conditions" not in norm, "normalize 不得为空串 conditions 另建分支"
    dumped = json.dumps(norm, ensure_ascii=False)
    assert "all" not in dumped and "any" not in dumped, "不得引入组合树键(无条件 = 直过语义, W3-A 才建树)"


def test_retired_pseudo_action_container_only():
    """伪动作 ignore_next_action_error 只做容器归一(params 原样透传), 不做 D1 禁止的语义映射"""
    spec = {"enabled": "true", "actions": [{"add_tags": ["A"]}, {"ignore_next_action_error": "yes"}]}
    original = json.dumps(spec, ensure_ascii=False)
    norm = normalize_legacy_rule(spec)
    assert norm["actions"][1] == {"type": "ignore_next_action_error", "params": "yes"}, "容器归一, 参数原样"
    # 伪动作不注入缺省 on_error(W2-B: 它不被引擎消费, 注入徒增噪音); 真动作照常注入缺省
    assert norm["actions"][0] == {"type": "add_tags", "params": ["A"], "on_error": _default_on_error()}
    # 禁止 ignore -> on_error 自动映射(D1): 伪动作键面仍恰为 {type, params}, 无语义映射键
    assert set(norm["actions"][1]) == {"type", "params"}, "不得出现 on_error 等语义映射键"
    # 载入层识别/剔除对规范形与旧扁平形都生效(经 compat 单点漏斗)
    assert rules_mod.retired_control_keys_in(norm) == ("ignore_next_action_error", )
    assert rules_mod.retired_control_keys_in(spec) == ("ignore_next_action_error", )
    disabled = rules_mod.disable_retired_rule_spec(norm)
    assert disabled["enabled"] is False
    assert disabled["actions"] == [
        {
            "type": "add_tags",
            "params": ["A"],
            "on_error": _default_on_error()
        }
    ], "伪动作从内存副本剔除(真动作保留缺省 on_error)"
    # 原 spec 与 normalize 输入零改写(D1: 配置原内容原样保留)
    assert json.dumps(spec, ensure_ascii=False) == original


# --------------------------- 错误定位回映射(R1①) ---------------------------


def _load_config_from_text(text: str):
    """文本 -> 临时文件 -> load_config(真实载入链: _strip_none -> normalize -> validate)"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "c.yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return load_config(path)


def _load_errors(text: str) -> str:
    """载入失败聚合错误全文(成功返回空串)"""
    try:
        _load_config_from_text(text)
        return ""
    except ConfigError as e:
        return str(e)


def test_action_error_location_maps_back_flat():
    """R1① 错误定位回映射: 结构错报「第 N 个动作」+ actions[i]; 深度错报 actions[i].<动作名>"""
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        - size: \">=1MiB\"\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
        "        - add_tags: [\"B\"]\n"
        "          stop: true\n",
    )
    assert "actions[1]" in err, err
    assert "第 2 个动作" in err, err
    assert "必须是单键字典" in err, err

    # 深度校验错: 归一形 params 的错误以动作名扁平坐标报出(不暴露 params 结构路径)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
        "        - checking:\n"
        "            basic_check: bogus\n",
    )
    assert "r1.actions[1].checking" in err, err
    assert "basic_check 取值非法" in err, err
    assert "params" not in err, "报错话术不得暴露归一形结构路径 params"


def test_validator_accepts_normalized_form():
    """校验器只认规范化形态: {type, params} 新形直接通过; on_error(W2-B)合法通过/非法 fail-fast"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        - size: \">=1MiB\"\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params:\n"
        "            - \"NEW\"\n"
    )
    acts = cfg.rules_config["my_rules"]["r1"]["actions"]
    assert acts == [
        {
            "type": "add_tags",
            "params": ["NEW"],
            "on_error": _default_on_error()
        }
    ], "新形输入经 normalize 注入缺省 on_error(幂等收敛)"

    # on_error 合法取值(三档 + 边界值)直接通过校验
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {policy: retry, retries: 2, backoff: 30}\n"
    )
    assert cfg.rules_config["my_rules"]["r1"]["actions"][0]["on_error"] == {
        "policy": "retry",
        "retries": "2",
        "backoff": "30",
    }, "on_error 合法取值零改写(用户配置值保留 BaseLoader 字符串标量口径, 引擎构造期 int/float 解析)"

    # 非法 policy 聚合报错(fail-fast)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {policy: bogus}\n"
    )
    assert "policy 取值非法" in err, err
    assert "可选: stop/continue/retry" in err, err

    # retries/backoff 边界校验(负数 / 非数字 / 未知子键), 聚合一次报全
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {retries: -1, backoff: 0, bogus: 1}\n"
    )
    assert "retries 必须 >= 0" in err, err
    assert "backoff 必须 > 0" in err, err
    assert "未知键 ['bogus']" in err, err

    # on_error 整体形状错(非 dict)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: continue\n"
    )
    assert "on_error: 必须是字典" in err, err

    # retries/backoff 非数字(聚合报错)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {policy: retry, retries: abc, backoff: xyz}\n"
    )
    assert "retries 必须是整数" in err, err
    assert "backoff 必须是数字" in err, err

    # 未知动作名与未知动作项键(fail-fast 键面, 与 on_error 扩展无关的老路径守住)
    err = _load_errors("config:\n"
                       "  my_rules:\n"
                       "    r1:\n"
                       "      actions:\n"
                       "        - bogus_action: [1]\n")
    assert "未知动作 'bogus_action'" in err, err
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"A\"]\n"
        "          bogus: 1\n"
    )
    assert "未知键 ['bogus']" in err, err

    # 未知条件名(conditions 侧同口径)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        - bogus_cond: 1\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
    )
    assert "未知条件 'bogus_cond'" in err, err


# ------------------------------- 载入链 / 引擎等价 -------------------------------


def test_load_config_rules_normalized():
    """载入链顺序: load_config 后 cfg.rules_config 已是规范化形态(校验前归一), conditions 透传"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      interval: 30M\n"
        "      conditions:\n"
        "        - path:\n"
        "            - \"regex:^I:/\"\n"
        "      actions:\n"
        "        - checking:\n"
        "            basic_check: filelist\n"
    )
    spec = cfg.rules_config["my_rules"]["r1"]
    assert spec["conditions"] == [{"path": ["regex:^I:/"]}], "conditions 透传零差异"
    assert spec["actions"] == [
        {
            "type": "checking",
            "params": {
                "basic_check": "filelist"
            },
            "on_error": _default_on_error()
        }
    ]


def test_rule_name_composite_passthrough_exec_history(tmp_path):
    """复合形「组.规则」命名透传: Rule.name 不变, exec_history 去重键前半不变"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"), bare=True, load_rules=False)
    mgr.config.rules_config = {"hhan_checking_rules": {"rule": {"enabled": "true", "actions": [{"add_tags": ["X"]}]}}}
    mgr.host.get("rules").load_rules()
    rules = mgr.host.get("rules").rules
    assert [r.name for r in rules] == ["hhan_checking_rules.rule"], "命名复合形零改写"

    client = FakeClient()
    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
    assert rules[0].process(ctx) == VERDICT_EXECUTED
    assert "hhan_checking_rules.rule:HASH123" in mgr.state["exec_history"], "去重键「规则名:hash」口径不变"


def test_old_state_exec_history_regression(tmp_path):
    """旧 state 文件载入回归: 既有 exec_history 键读入后去重判定不变, 新写入同键口径"""
    state_file = tmp_path / "state.json"
    legacy_state = {
        "exec_history":
            {
                "hhan_checking_rules.rule:ABCDEF123456": {
                    "ts": 1750000000.0,
                    "date": "2026-10-01",
                    "hour": 3
                },
            }
    }
    state_file.write_text(json.dumps(legacy_state, ensure_ascii=False), encoding="utf-8")
    svc = StateService(str(state_file))
    svc.data = svc.load()  # load 返回状态 dict, 由调用方装配(与 run() 启动加载同口径)
    rec = svc.get_exec_record("hhan_checking_rules.rule", "ABCDEF123456")
    assert rec is not None and rec["date"] == "2026-10-01", "旧键「规则名:hash」读回判定不变"
    # 新写入沿用同一键口径(core/state.py:281 单点)
    svc.record_execution("hhan_checking_rules.rule", "ABCDEF123456")
    assert "hhan_checking_rules.rule:ABCDEF123456" in svc.data["exec_history"]
    # W2-B hash 输入口径回归: on_error 注入只动 actions 条目形状, 去重键两个输入
    # (规则名 + 种子 infohash)零触碰 —— 去重键不含任何 spec 序列化, 注入前后判定一致
    assert svc.get_exec_record("hhan_checking_rules.rule", "ABCDEF123456") is not None
    assert svc.get_exec_record("hhan_checking_rules.rule", "OTHERHASH0000") is None
    spec_with_on_error = {
        "enabled":
            "true",
        "actions":
            [
                {
                    "type": "checking",
                    "params": {
                        "basic_check": "filelist"
                    },
                    "on_error": {
                        "policy": "retry",
                        "retries": 2,
                        "backoff": 30
                    }
                }
            ],
    }
    assert rules_mod.retired_control_keys_in(spec_with_on_error) == (), "on_error 不属退役键, 不触发转未启用"


def test_engine_legacy_and_normalized_equivalent(tmp_path):
    """引擎消费等价: 旧扁平形与规范化形构造的 Rule 动作同型, 执行行为一致"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    client = FakeClient()
    tor = FakeTorrent(tags="", size=100 * 1024**2)
    ctx = make_ctx(mgr, tor, client)
    legacy = Rule("g.t", {"actions": [{"add_tags": ["X"]}]}, mgr)
    normalized = Rule("g.t", {"actions": [{"type": "add_tags", "params": ["X"]}]}, mgr)
    assert [type(a) for a in legacy.actions] == [type(a) for a in normalized.actions]
    assert all(isinstance(a, AddTagsAction) for a in (*legacy.actions, *normalized.actions))
    assert normalized.process(ctx) == VERDICT_EXECUTED
    assert ("add_tags", ["X"]) in client.calls, "规范化动作以同参执行(零行为变化)"
