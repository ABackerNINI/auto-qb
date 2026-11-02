"""test_rule_compat_misc 测试计划: 规则兼容层(config/compat.py 载入规范化单点, plan 26-11-01-0106 §3.2 W2-A/W2-B/W3-A/W3-B)

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

⚠ 快照金标准口径(W3-A 再重锚定): normalize 自 W3-A 起把旧扁平条件列表包成隐式
`all:` 组合树(normalize_conditions 单点; 语义 = 现行 matches 的 all(...)), 各条件的
行内分组/逗号语义全部留在叶子内(CONDITION_GROUPING_MAP 逐条件映射表), 快照 conditions
按树形重锚定 —— 叶子逐位不变, 行为零变化。

## 测试计划(每个测试函数一条)
- test_production_rules_snapshot: 生产 5 条规则(3 规则集)规范化快照比对 —— 金标准零差异:
  归一输出逐位等于预期快照(W2-B 动作含缺省 on_error; W3-A conditions 包隐式 all 树,
  叶子零差异; 来源: config.yml 191-285 行, 誊写夹具)
- test_snapshot_action_conversion_value_preserving: 快照动作转换保值 —— 每个规范化动作的
  (type, params) 与旧扁平形的 (键名, 值) 逐位相同(引擎 create_action 收到的 value 不变)
- test_validator_accepts_tree_form: 校验器认树形 —— 手写 {all/any/not} 组合通过载入校验
  且零再变换, 叶子深度校验照常分发
- test_unknown_combo_key_fail_fast: 未知组合键 fail-fast(W3-A) —— all/any/not 拼错按
  未知条件报、多键节点/组合值非列表/not 孩子非节点报结构错、深度超上限拒绝
- test_on_error_default_injection: 缺省 on_error 注入(W2-B) —— 无 on_error 补全缺省对象、
  部分缺省补缺失键、已配置值零改写; 伪动作不注入; on_error 非 dict 原样透传交校验器报
- test_conditions_empty_string_no_branch: hhan `conditions: ''` 注记 —— 空串被 _strip_none
  载入前整键剔除, normalize 不另建分支(不出现 all/any 组合键), 无条件 = 直过硬语义保持
- test_retired_pseudo_action_container_only: 伪动作 ignore_next_action_error 只做容器归一
  (params 原样透传, 不做 on_error 语义映射也不注入缺省 on_error —— D1 禁止);
  载入层识别/剔除对规范形与旧形都生效
- test_rule_name_composite_passthrough_exec_history: 复合形「组.规则」命名透传 —— 规范化
  配置载入后 Rule.name 保持「规则集.规则名」, exec_history 去重键「规则名:hash」前半不变
  (W2-B: on_error 注入不触碰键输入 —— 去重键 hash = 种子 infohash, 不含 spec 序列化)
- test_old_state_exec_history_regression: 旧 state 文件载入回归 —— 既有 exec_history 键
  (规则名:hash)读入后 get_exec_record 判定不变, 新写入沿用同一键口径(core/state.py:281);
  on_error 注入前后同一种子的去重判定不变(去重窗口零重置)
"""

import json

import os

import tempfile

import pytest

import yaml

from auto_qb.config import ConfigError, load_config

from auto_qb.config.compat import (
    CONDITION_TREE_MAX_DEPTH,
    CONDITION_GROUPING_MAP,
    normalize_action_entry,
    normalize_conditions,
    normalize_legacy_rule,
    normalize_legacy_rules,
)

from auto_qb.config.validation import _strip_none

from auto_qb.core.modules import rules_mod

from auto_qb.core.state import StateService

from auto_qb.rules import registry

from auto_qb.rules.actions import AddTagsAction

from auto_qb.rules.base import VERDICT_ERROR, VERDICT_EXECUTED, VERDICT_NO_OP, VERDICT_RETRY, Rule

from helpers import FakeClient, FakeTorrent, make_ctx, make_manager

from rule_compat_support import (
    _checking_params,
    _default_on_error,
    _load_config_from_text,
    _load_errors,
)

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

# 规范化金标准快照: 5 条规则(3 规则集)归一后的预期形态 —— 与引擎现行消费逐位等价
# (conditions W3-A 起为隐式 all 树形, 叶子逐位不变; 动作 {type, params, on_error} 参数值
# 与旧扁平形逐位相同 + W2-B 注入的缺省 on_error: policy=stop 即现行失败即止, 行为零变化),
# 快照按「含缺省字段 + 条件树形」口径重锚定
_SNAPSHOT = {
    "add_drive_letter_tag_rules":
        {
            "add_r_tag":
                {
                    "enabled": "true",
                    "trigger": "on_torrent_added",
                    "cooldown": "5M",
                    "conditions": {
                        "all": [{
                            "path": ["regex:^R:/Download/PTing/", "regex:^R:/Download/ing/"]
                        }]
                    },
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
                    "conditions": {
                        "all": [{
                            "path": ["regex:^I:/"]
                        }]
                    },
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
                    "conditions": {
                        "all": [{
                            "path": ["regex:^H:/"]
                        }]
                    },
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
                    "conditions": {
                        "all": [{
                            "path": ["regex:^R:/"]
                        }]
                    },
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


def test_production_rules_snapshot():
    """生产 5 条规则规范化快照比对: 归一输出逐位等于预期快照(金标准零差异), 叶子零差异建树"""
    cfg = _normalized_production_rules()
    for group_name, group in _SNAPSHOT.items():
        assert group_name in cfg, f"缺规则集 {group_name}"
        for rule_name, expected in group.items():
            actual = cfg[group_name][rule_name]
            assert actual == expected, f"{group_name}.{rule_name} 规范化快照零差异被破坏"
            # 条件建树锚定(W3-A): 归一后 conditions = 隐式 all 树, 叶子与旧扁平列表逐位相同
            if "conditions" in expected:
                raw = yaml.load(_PRODUCTION_RULES_YAML, Loader=yaml.BaseLoader)["config"][group_name][rule_name]
                assert actual["conditions"] == {
                    "all": raw["conditions"]
                }, (f"{group_name}.{rule_name} conditions 应为隐式 all 树且叶子零差异")


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


def test_unknown_combo_key_fail_fast():
    """未知组合键 fail-fast(W3-A): 拼错组合键按未知条件报; 多键/形状错/深度超限拒绝"""
    # 组合键拼错(al/Al) -> 未知条件(不静默当叶子, 也不静默丢弃)
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n      conditions:\n        - al: [{size: \">=1MiB\"}]\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "未知条件 'al'" in err, err
    # 多键节点(组合键 + 条件名混写)
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {all: [{size: \">=1MiB\"}], path: /a}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "必须是单键字典" in err, err
    # all/any 的值必须是列表; not 的孩子必须是节点
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {all: {size: \">=1MiB\"}}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "conditions.all: 必须是列表" in err, err
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {not: \"size\"}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "conditions.not" in err and "必须是字典" in err, err
    # 空节点/顶层非字典
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {all: []}\n      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "conditions: 值不能为空" not in err, "all: [] 空列表 = 恒真, 与旧空列表语义一致, 合法: " + err
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n      conditions: \"oops\"\n      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "conditions: 必须是字典" in err, err


def test_validator_accepts_tree_form():
    """校验器认树形: 手写 {all/any/not} 组合通过载入校验且零再变换; 叶子深度校验照常分发"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        all:\n"
        "          - any:\n"
        "              - path: [\"regex:^I:/\"]\n"
        "              - size: \">=1MiB\"\n"
        "          - not: {trackers: nope}\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
    )
    spec = cfg.rules_config["my_rules"]["r1"]
    assert spec["conditions"] == {
        "all": [
            {
                "any": [{
                    "path": ["regex:^I:/"]
                }, {
                    "size": ">=1MiB"
                }]
            },
            {
                "not": {
                    "trackers": "nope"
                }
            },
        ]
    }, "树形输入零再变换(幂等收敛), 引擎按树形求值"


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
