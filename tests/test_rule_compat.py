"""test_rule_compat 测试计划: 规则兼容层(config/compat.py 载入规范化单点, plan 26-11-01-0106 §3.2 W2-A/W2-B/W3-A/W3-B)

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
- test_normalize_idempotent: 幂等 —— normalize(normalize(x)) == normalize(x)(旧形输入与
  已规范形输入各验一次; 已规范形零改写, 缺 on_error 的规范形补缺省后收敛)
- test_normalize_conditions_builds_tree: 条件建树(W3-A) —— 扁平列表包隐式 all、树形 dict
  原样透传、叶子逐位零触碰; normalize_conditions 自身幂等
- test_combo_tree_evaluation: 组合树求值(W3-A) —— all/any/not 递归 + 嵌套 + 短路
  (all 首个 False / any 首个 True 后叶子不再求值)+ 叶子异常上抛(process 兜 verdict:error)
- test_condition_grouping_mapping: 「逗号分组」逐条件映射(W3-A/G4) —— tags 组内逗号=AND
  组间=OR、state 组内&=AND 组间=OR 等 13 条件叶子语义经建树+引擎求值与现行为逐条等价;
  hr 双语义分歧维持现状断言; CONDITION_GROUPING_MAP 覆盖 registry 全部条件
- test_condition_grouping_map_covers_registry: 映射表覆盖守卫 —— 逐条件核对表
  (CONDITION_GROUPING_MAP)与注册表条件集一致, 新增条件漏核对当场红
- test_condition_grouping_mapping_freespace: freespace 叶子映射 —— dict{path, amount} 原样,
  取数单点打桩(与 expr 侧 disk_usage_value 同口径)
- test_condition_tree_depth_limit: 组合树深度上限 —— 嵌套 <=16 层通过, >16 层 fail-fast
- test_engine_condition_tree_legacy_equivalent: 引擎等价 —— 旧扁平条件列表与规范化树形
  构造的 Rule 建树同构、求值同果(隐式 all = 现行 all(...))
- test_validator_accepts_tree_form: 校验器认树形 —— 手写 {all/any/not} 组合通过载入校验
  且零再变换, 叶子深度校验照常分发
- test_unknown_combo_key_fail_fast: 未知组合键 fail-fast(W3-A) —— all/any/not 拼错按
  未知条件报、多键节点/组合值非列表/not 孩子非节点报结构错、深度超上限拒绝
- test_condition_error_location_maps_back_flat: R1① 条件侧坐标回映射 —— 扁平列表条目的
  校验错报 conditions[i] 扁平坐标; 深度校验错报 conditions[i].<条件名>; 树形子树按树形
  坐标如实报出
- test_on_error_default_injection: 缺省 on_error 注入(W2-B) —— 无 on_error 补全缺省对象、
  部分缺省补缺失键、已配置值零改写; 伪动作不注入; on_error 非 dict 原样透传交校验器报
- test_on_error_mixed_form_normalized: webui 动作卡写出的混合形 {动作键: 值, on_error: {...}}
  经单点漏斗翻译成规范形 {type, params, on_error}(载入链与直达校验器两条路一致)
- test_conditions_empty_string_no_branch: hhan `conditions: ''` 注记 —— 空串被 _strip_none
  载入前整键剔除, normalize 不另建分支(不出现 all/any 组合键), 无条件 = 直过硬语义保持
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
  规范化形态(校验前归一), conditions 为隐式 all 树形(W3-A)
- test_rule_name_composite_passthrough_exec_history: 复合形「组.规则」命名透传 —— 规范化
  配置载入后 Rule.name 保持「规则集.规则名」, exec_history 去重键「规则名:hash」前半不变
  (W2-B: on_error 注入不触碰键输入 —— 去重键 hash = 种子 infohash, 不含 spec 序列化)
- test_old_state_exec_history_regression: 旧 state 文件载入回归 —— 既有 exec_history 键
  (规则名:hash)读入后 get_exec_record 判定不变, 新写入沿用同一键口径(core/state.py:281);
  on_error 注入前后同一种子的去重判定不变(去重窗口零重置)
- test_engine_legacy_and_normalized_equivalent: 引擎消费等价 —— 旧扁平形与规范化形构造的
  Rule 动作实例同型, 执行行为一致(add_tags 同参调用)
- test_choose_normalize_form: choose 归一形态(W3-B) —— {choose, default} 键面保留(编排块不翻
  {type, params} 形); when 扁平列表包隐式 all; then/default 动作项注入缺省 on_error; 块级/分支级
  未知键与非 dict 分支原样透传交校验器; normalize_choose_block 幂等
- test_choose_validator_accepts_normalized_form: 校验器认 choose(W3-B) —— 合法 choose 经真实
  载入链零再变换(when 树形保留、then/default 注入缺省 on_error)
- test_choose_validator_fail_fast: choose fail-fast(W3-B) —— 块级/分支级未知键、缺 when、缺 then、
  choose 非列表、空分支列表、then/default 非 list、嵌套 choose(then 与 default 两侧)、when 内
  未知条件全部拒绝, 坐标报 choose[i].when / choose[i].then[j] 树形
- test_choose_when_depth_limit: choose 的 when 条件树深度复用 CONDITION_TREE_MAX_DEPTH ——
  <=16 层通过, >16 层 fail-fast(独立计深度, 与顶层 conditions 同口径)
- test_choose_engine_branch_dispatch: choose 引擎求值(W3-B) —— 按序求 when 首个命中执行其 then
  (后续分支短路不再求值); 无命中走 default; 无命中无 default = 空操作(no_op 语义); 与普通动作
  混排按 steps 顺序执行
- test_choose_engine_when_error: choose 的 when 求值异常 -> 整条本轮 VERDICT_ERROR(保守: 求值
  出错不误入 default), 与顶层条件异常同语义
- test_choose_engine_on_error_dispatch: choose 内动作 on_error 三档分派(W3-B, 与顶层同语义) ——
  continue 继续分支后续动作; stop 中断整条链(分支后续与块后动作都不执行, 失败动作计已执行);
  retry 挂块首断点 + retry_delay=backoff(任务级 requeue, 无 run 内 sleep)
- test_choose_nested_construction_rejected: 嵌套 choose 构造期兜底(W3-B) —— 绕过校验器直构造
  Rule 遇 then/default 内嵌套 choose 报 ConfigError(编排块只允许一层)
- test_choose_deleted_trigger_whitelist: on_torrent_deleted 白名单覆盖 choose 块内动作(W3-B) ——
  then/default 内非白名单动作同样 fail-fast
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


# ------------------------------- 金标准快照 -------------------------------


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
    assert once["conditions"] == {"all": [{"size": ">=1MiB"}, {"path": ["/a"]}]}, "扁平条件列表包隐式 all(W3-A)"
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


# ------------------------- 组合树(W3-A): 建树 / 求值 / 映射 -------------------------


def test_normalize_conditions_builds_tree():
    """条件建树(W3-A): 扁平列表包隐式 all; 树形 dict 原样透传; 叶子逐位零触碰; 自身幂等"""
    # 旧扁平单键 dict 列表 -> {"all": 列表}(序号 1:1 保留, R1① 扁平坐标回映射的依据)
    flat = [{"size": ">=1MiB"}, {"path": ["/a"]}]
    tree = normalize_conditions(flat)
    assert tree == {"all": flat}, "隐式 all 包裹"
    assert tree["all"] == flat, "叶子逐位零触碰(逗号分组语义留在叶内)"
    # 已是树形(dict)原样透传: 组合节点 / 单条件节点 / 非法形状都交校验器, normalize 不吞
    assert normalize_conditions({"all": [{"size": "1MiB"}]}) == {"all": [{"size": "1MiB"}]}
    assert normalize_conditions({"any": [{"size": "1MiB"}]}) == {"any": [{"size": "1MiB"}]}
    assert normalize_conditions({"not": {"size": "1MiB"}}) == {"not": {"size": "1MiB"}}
    assert normalize_conditions({"path": "/a"}) == {"path": "/a"}
    assert normalize_conditions("not-a-tree") == "not-a-tree", "非法形状原样透传交校验器报"
    # 幂等: 建树一次后收敛稳定
    assert normalize_conditions(tree) == tree
    # normalize_legacy_rule 全链: 载入规范化对 conditions 建树, 其余键零触碰
    spec = {"enabled": "true", "conditions": [{"size": ">=1MiB"}]}
    norm = normalize_legacy_rule(spec)
    assert norm["conditions"] == {"all": [{"size": ">=1MiB"}]}
    assert spec["conditions"] == [{"size": ">=1MiB"}], "输入不被就地改写"


class _Fixed:
    """固定返回值的哑条件(求值/短路测试用): calls 记录被求值次数"""
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def match(self, ctx):
        self.calls += 1
        return self.value


class _Boom:
    """求值即抛的哑条件: 用于断言短路后不被触达 / 异常上抛路径"""
    def __init__(self):
        self.calls = 0

    def match(self, ctx):
        self.calls += 1
        raise RuntimeError("boom")


def _eval_rule(tmp_path, tree):
    """构造 Rule 并手动挂条件树(内存表示单测; spec 级路径由映射/载入测试覆盖)"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), FakeClient())
    rule = Rule("g.t", {"actions": []}, mgr)
    rule.condition_tree = tree
    return rule, ctx


def test_combo_tree_evaluation(tmp_path):
    """组合树求值(W3-A): all/any/not 递归 + 嵌套 + 短路 + 叶子异常上抛 -> verdict:error"""
    t1, t2, f1, f2 = _Fixed(True), _Fixed(True), _Fixed(False), _Fixed(False)
    boom = _Boom()

    # all: 全真才真; any: 一真即真; not: 取反
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", t1), ("leaf", t2)]))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", t1), ("leaf", f1)]))
    assert rule.matches(ctx) is False
    rule, ctx = _eval_rule(tmp_path, ("any", [("leaf", f1), ("leaf", t1)]))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("not", ("leaf", f1)))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("not", ("leaf", t1)))
    assert rule.matches(ctx) is False

    # 嵌套: any( all(T,T), F ) = True; all( any(F,T), F ) = False
    rule, ctx = _eval_rule(tmp_path, ("any", [("all", [("leaf", t1), ("leaf", t2)]), ("leaf", f1)]))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("all", [("any", [("leaf", f1), ("leaf", t1)]), ("leaf", f2)]))
    assert rule.matches(ctx) is False

    # 短路: all 首个 False 后 / any 首个 True 后, 其后叶子不再求值
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", f1), ("leaf", boom)]))
    assert rule.matches(ctx) is False and boom.calls == 0, "all 短路: False 后不再求值"
    rule, ctx = _eval_rule(tmp_path, ("any", [("leaf", t1), ("leaf", boom)]))
    assert rule.matches(ctx) is True and boom.calls == 0, "any 短路: True 后不再求值"

    # 叶子异常上抛: matches 抛 RuntimeError; process 兜成 verdict:error 本条本轮不命中(W2 语义)
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", _Boom())]))
    with pytest.raises(RuntimeError):
        rule.matches(ctx)
    rule.actions = [AddTagsAction(["X"])]
    assert rule.process(ctx) == VERDICT_ERROR, "条件异常 -> verdict:error, 本条本轮不命中"


def test_engine_condition_tree_legacy_equivalent(tmp_path):
    """引擎等价: 旧扁平条件列表与规范化树形构造的 Rule 求值同型同果(隐式 all = 现行 all(...))"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    tor = FakeTorrent(tags="HR", size=100 * 1024**2)
    ctx = make_ctx(mgr, tor, FakeClient())
    legacy = Rule("g.t", {"conditions": [{"size": ">=1MiB"}, {"tags": "HR"}], "actions": []}, mgr)
    tree = Rule(
        "g.t",
        {
            "conditions": {
                "all": [{
                    "size": ">=1MiB"
                }, {
                    "tags": "HR"
                }]
            },
            "actions": []
        },
        mgr,
    )

    def tree_shape(node):
        """树的类型形状(叶子按插件类名比, 实例身份不比)"""
        kind, payload = node
        if kind == "leaf":
            return (kind, type(payload).__name__)
        if kind == "not":
            return (kind, tree_shape(payload))
        return (kind, [tree_shape(c) for c in payload])

    assert tree_shape(legacy.condition_tree) == tree_shape(tree.condition_tree), ("扁平形经单点漏斗建树后与手写树形同构")
    assert legacy.matches(ctx) is True and tree.matches(ctx) is True


def _mapping_rule(tmp_path, conditions, tor_kw=None, tracker_kw=None, no_tracker=False):
    """映射测试辅助: 条件叶子经真实建树漏斗(normalize_legacy_rule -> Rule)构造, 返回求值结果"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"), tracker_kw=tracker_kw)
    tor = FakeTorrent(**(tor_kw or {}))
    ctx = make_ctx(mgr, tor, FakeClient())
    if no_tracker:
        tor.tracker_conf = None  # make_ctx 只在 None 时回填, 此后置 None = 模拟未匹配站点
    spec = normalize_legacy_rule({"conditions": conditions, "actions": []})
    return Rule("g.t", spec, mgr).matches(ctx)


def test_condition_grouping_mapping(tmp_path):
    """「逗号分组」逐条件映射(W3-A/G4): 13 条件叶子语义经建树+求值与现行为逐条等价

    映射结论 = compat.CONDITION_GROUPING_MAP: 行内分隔符/列表 OR 语义全部留在叶子内,
    normalize 零改写(只承诺生产已出现形态); hr 双语义分歧维持现状不单边改齐
    (conditions.py:154-164 vs rules/expr/env.py _hr, 注释证据在叶内)。
    """
    # path: 列表=OR(无行内分组) —— 生产唯一在用条件, regex: 前缀原样
    assert _mapping_rule(tmp_path, [{"path": ["regex:^R:/", "/nope/"]}]) is True
    assert _mapping_rule(tmp_path, [{"path": ["/nope/", "/nada/"]}]) is False
    # size: 单比较串
    assert _mapping_rule(tmp_path, [{"size": ">=1MiB"}], tor_kw={"size": 100 * 1024**2}) is True
    assert _mapping_rule(tmp_path, [{"size": ">=1TiB"}], tor_kw={"size": 100 * 1024**2}) is False
    # tags: 组内逗号=AND, 组间列表=OR(叶子内语义, 不展开成 any)
    assert _mapping_rule(tmp_path, [{"tags": ["HR,low", "z"]}], tor_kw={"tags": "HR,low"}) is True
    assert _mapping_rule(tmp_path, [{"tags": ["HR,low"]}], tor_kw={"tags": "HR"}) is False, "组内逗号=AND"
    assert _mapping_rule(tmp_path, [{"tags": ["nope", "HR"]}], tor_kw={"tags": "HR"}) is True, "组间列表=OR"
    # category: 列表=OR
    assert _mapping_rule(tmp_path, [{"category": ["regex:^HR", "x"]}], tor_kw={"category": "HR"}) is True
    assert _mapping_rule(tmp_path, [{"category": ["x", "y"]}], tor_kw={"category": "HR"}) is False
    # trackers: 列表=OR(默认 manager 装配 HHan 假站点, make_ctx 已匹配)
    assert _mapping_rule(tmp_path, [{"trackers": ["nope", "HHan"]}]) is True
    assert _mapping_rule(tmp_path, [{"trackers": "nope"}]) is False
    # tracker_group: 列表=OR(站点 groups 声明)
    assert _mapping_rule(tmp_path, [{"tracker_group": ["nope", "国内"]}], tracker_kw={"groups": ["国内"]}) is True
    assert _mapping_rule(tmp_path, [{"tracker_group": "国外"}], tracker_kw={"groups": ["国内"]}) is False, "分组不符恒 False"
    # state: 组内 &=AND(非逗号), 组间列表=OR(stalledUP: is_complete/is_uploading 真, is_downloading 假)
    assert _mapping_rule(tmp_path, [{"state": ["is_complete&is_uploading", "is_downloading"]}]) is True
    assert _mapping_rule(tmp_path, [{"state": ["is_complete&is_downloading"]}]) is False, "组内 &=AND"
    assert _mapping_rule(tmp_path, [{"state": ["is_downloading", "is_uploading"]}]) is True, "组间列表=OR"
    # hr: 单模式串; 双语义分歧维持现状(conditions.py:154-164 显式分支, 勿单边改齐):
    # 分支一 tracker_conf=None(未匹配站点) —— 仅 condition-not-met 为真
    assert _mapping_rule(tmp_path, [{"hr": "condition-not-met"}], no_tracker=True) is True
    assert _mapping_rule(tmp_path, [{"hr": "condition-met"}], no_tracker=True) is False
    assert _mapping_rule(tmp_path, [{"hr": "satisfied"}], no_tracker=True) is False
    # 分支二 站点已匹配但无 HR 配置(conf.hr=None, tracker_kw 显式置空) —— 非 condition-met 全真;
    # 其中 satisfied=True 与表达式侧 tor.hr_satisfied 同场景恒 false 有意分歧(那里答「可打标/可删」
    # 达标语义, 本处答「有无义务」, 见 rules/expr/env.py _hr 注释)
    hr_none = {"hr": None}
    assert _mapping_rule(tmp_path, [{"hr": "condition-not-met"}], tracker_kw=hr_none) is True
    assert _mapping_rule(tmp_path, [{"hr": "condition-met"}], tracker_kw=hr_none) is False
    assert _mapping_rule(tmp_path, [{"hr": "satisfied"}], tracker_kw=hr_none) is True
    # date_time: dict 区间串(确定性区间: 当日/当周必在 1-31 / 1-7 内)
    assert _mapping_rule(tmp_path, [{"date_time": {"day_of_month": "1-31", "day_of_week": "1-7"}}]) is True
    assert _mapping_rule(tmp_path, [{"date_time": {"day_of_month": "32"}}]) is False
    # seedtime / upload_ratio: 单比较串
    assert _mapping_rule(tmp_path, [{"seedtime": "<24H"}], tor_kw={"seeding_time": 0}) is True
    assert _mapping_rule(tmp_path, [{"seedtime": ">24H"}], tor_kw={"seeding_time": 0}) is False
    assert _mapping_rule(tmp_path, [{"upload_ratio": "<1.5"}], tor_kw={"ratio": 0.0}) is True
    assert _mapping_rule(tmp_path, [{"upload_ratio": ">1.5"}], tor_kw={"ratio": 0.0}) is False
    # expr: 单表达式串(叶子原样, 编译/语义校验不变)
    assert _mapping_rule(tmp_path, [{"expr": "tor.size > 1MiB"}], tor_kw={"size": 100 * 1024**2}) is True


def test_condition_grouping_mapping_freespace(tmp_path, monkeypatch):
    """freespace 叶子映射: dict{path, amount} 原样; 取数单点打桩(与 expr 侧同口径)"""
    monkeypatch.setattr("auto_qb.rules.conditions.disk_usage_value", lambda p, k: 100 * 1024**3)
    assert _mapping_rule(tmp_path, [{"freespace": {"path": "R:/", "amount": ">1MiB"}}]) is True
    assert _mapping_rule(tmp_path, [{"freespace": {"path": "R:/", "amount": "<1MiB"}}]) is False


def test_condition_grouping_map_covers_registry():
    """映射表覆盖守卫: 逐条件核对表(CONDITION_GROUPING_MAP)与注册表条件集一致"""
    registered = set(registry.CONDITIONS)
    assert set(CONDITION_GROUPING_MAP) == registered, (
        "逗号分组映射表漏核对条件 —— 新增条件必须在 compat.CONDITION_GROUPING_MAP 补行内分组语义 "
        "(计划 §3.2/G4: 以 conditions.py 现行为准逐条件核对)"
    )


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


def test_condition_tree_depth_limit():
    """组合树深度上限(W3-A): 嵌套 <=16 层通过, >16 层 fail-fast(防递归爆炸)"""
    def nested(k: int) -> dict:
        node = {"size": ">=1MiB"}
        for _ in range(k):
            node = {"all": [node]}
        return node

    def _try_load(k: int) -> str:
        flow = yaml.safe_dump(nested(k), default_flow_style=True).strip()
        return _load_errors(
            "config:\n  my_rules:\n    r1:\n"
            f"      conditions: {flow}\n"
            "      actions:\n        - add_tags: [\"A\"]\n"
        )

    assert _try_load(CONDITION_TREE_MAX_DEPTH - 1) == "", "上限内(16 层组合节点)合法"
    err = _try_load(CONDITION_TREE_MAX_DEPTH)
    assert f"组合树嵌套超过上限 {CONDITION_TREE_MAX_DEPTH} 层" in err, err


def test_condition_error_location_maps_back_flat():
    """R1① 条件侧坐标回映射: 扁平列表条目报 conditions[i]; 树形子树按树形坐标如实报"""
    # 扁平列表条目的未知条件 -> conditions[0](不是 conditions.all[0])
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions:\n        - bogus_cond: 1\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions[0]: 未知条件 'bogus_cond'" in err, err
    assert "conditions.all" not in err, err
    # 深度校验错: 扁平坐标 conditions[i].<条件名>
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions:\n        - tags: ['regex:[x']\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions[0].tags[0]: 非法正则" in err, err
    # 用户手写树形的子树错误 -> 树形坐标如实报(那里本就是树形写法, 无扁平坐标可回映射)
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {any: [{bogus_cond: 1}]}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions.any[0]: 未知条件 'bogus_cond'" in err, err
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {not: {bogus_cond: 1}}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions.not: 未知条件 'bogus_cond'" in err, err


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
    assert norm["conditions"] == {"all": spec["conditions"]}, "conditions 建树(W3-A), 叶子逐位不变"
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
    """载入链顺序: load_config 后 cfg.rules_config 已是规范化形态(校验前归一), conditions 为隐式 all 树"""
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
    assert spec["conditions"] == {"all": [{"path": ["regex:^I:/"]}]}, "conditions 建树为隐式 all(W3-A)"
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


# --------------------------- choose 编排块(W3-B, plan G6/D3) ---------------------------


def test_choose_normalize_form():
    """choose 归一形态(W3-B): {choose, default} 键面保留(编排块不翻 {type, params} 形);
    when 扁平列表包隐式 all; then/default 动作项注入缺省 on_error; 异形原样透传; 幂等"""
    entry = {
        "choose": [{
            "when": [{
                "size": ">=1MiB"
            }],
            "then": [{
                "add_tags": ["T"]
            }]
        }, ],
        "default": [{
            "add_tags": ["D"]
        }],
    }
    norm = normalize_action_entry(entry)
    assert set(norm) == {"choose", "default"}, "choose 是编排块不是插件动作, 不翻译成 {type, params} 形"
    assert norm["choose"] == [
        {
            "when": {
                "all": [{
                    "size": ">=1MiB"
                }]
            },
            "then": [{
                "type": "add_tags",
                "params": ["T"],
                "on_error": _default_on_error()
            }],
        }
    ], "when 扁平列表包隐式 all(与 conditions 同款建树), then 注入缺省 on_error"
    assert norm["default"] == [{"type": "add_tags", "params": ["D"], "on_error": _default_on_error()}]
    assert normalize_action_entry(norm) == norm, "choose 归一幂等(归一一次后收敛稳定)"
    # 块级/分支级未知键原样保留交校验器 fail-fast(normalize 不吞错误)
    bad = normalize_action_entry({"choose": [{"when": {"size": "1MiB"}, "then": [], "bogus": 1}], "bogus2": 2})
    assert bad["bogus2"] == 2 and bad["choose"][0]["bogus"] == 1
    # 非 list choose / 非 dict 分支原样透传
    assert normalize_action_entry({"choose": "oops"})["choose"] == "oops"
    assert normalize_action_entry({"choose": [1]})["choose"] == [1]
    # 树形 when 原样透传(幂等收敛); 无 default 不造键
    tree_entry = {"choose": [{"when": {"any": [{"size": ">=1MiB"}]}, "then": []}]}
    assert normalize_action_entry(tree_entry) == {"choose": [{"when": {"any": [{"size": ">=1MiB"}]}, "then": []}]}
    assert "default" not in normalize_action_entry({"choose": []})


def test_choose_validator_accepts_normalized_form():
    """校验器认 choose(W3-B): 合法 choose 经真实载入链零再变换(when 树形保留, then/default 注入缺省)"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - choose:\n"
        "            - when:\n"
        "                all:\n"
        "                  - size: \">=1MiB\"\n"
        "              then:\n"
        "                - add_tags: [\"T\"]\n"
        "                - add_tags: [\"T2\"]\n"
        "                  on_error: {policy: continue}\n"
        "            - when: {tags: HR}\n"
        "              then: []\n"
        "          default:\n"
        "            - add_tags: [\"D\"]\n"
    )
    acts = cfg.rules_config["my_rules"]["r1"]["actions"]
    assert acts == [
        {
            "choose":
                [
                    {
                        "when": {
                            "all": [{
                                "size": ">=1MiB"
                            }]
                        },
                        "then":
                            [
                                {
                                    "type": "add_tags",
                                    "params": ["T"],
                                    "on_error": _default_on_error()
                                },
                                {
                                    "type": "add_tags",
                                    "params": ["T2"],
                                    "on_error": {
                                        "policy": "continue",
                                        "retries": 3,
                                        "backoff": 60
                                    },
                                },
                            ],
                    },
                    {
                        "when": {
                            "tags": "HR"
                        },
                        "then": []
                    },
                ],
            "default": [{
                "type": "add_tags",
                "params": ["D"],
                "on_error": _default_on_error()
            }],
        }
    ], "choose 块经载入链零再变换(when 树形保留, then/default 缺省 on_error 注入)"


def test_choose_validator_fail_fast():
    """choose fail-fast(W3-B): 键面/分支结构/嵌套/when 未知条件全部拒绝, 坐标按树形如实报"""
    head = "config:\n  my_rules:\n    r1:\n      actions:\n"
    # 块级未知键
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n          bogus: 1\n")
    assert "未知键 ['bogus']" in err and "可用键: ['choose', 'default']" in err, err
    # 分支缺 when / 缺 then / 分支级未知键
    err = _load_errors(head + "        - choose: [{then: []}]\n")
    assert "choose[0]: 缺少 when" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}}]\n")
    assert "choose[0]: 缺少 then" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: [], bogus: 1}]\n")
    assert "choose[0]: 未知键 ['bogus']" in err and "可用键: ['then', 'when']" in err, err
    # choose 非列表 / 空分支列表 / then 非 list / default 非 list
    err = _load_errors(head + "        - choose: oops\n")
    assert "choose: 必须是分支列表" in err, err
    err = _load_errors(head + "        - choose: []\n")
    assert "分支列表不能为空" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: oops}]\n")
    assert "choose[0].then: 必须是列表" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n          default: oops\n")
    assert "default: 必须是列表" in err, err
    # 嵌套 choose(then 与 default 两侧)—— 编排块只允许一层
    nested = "- choose: [{when: {size: \">=1MiB\"}, then: [{choose: [{when: {size: \">=1MiB\"}, then: []}]}]}]\n"
    err = _load_errors(head + "        " + nested)
    assert "choose 内不允许嵌套 choose" in err, err
    err = _load_errors(
        head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n"
        "          default: [{choose: [{when: {size: \">=1MiB\"}, then: []}]}]\n"
    )
    assert "choose 内不允许嵌套 choose" in err, err
    # when 内未知条件 fail-fast(与 conditions 同款键面)
    err = _load_errors(head + "        - choose: [{when: {bogus_cond: 1}, then: []}]\n")
    assert "choose[0].when: 未知条件 'bogus_cond'" in err, err
    # then 内动作深度校验照常分发(未知动作同径报)
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: [{bogus_action: [1]}]}]\n")
    assert "choose[0].then[0]: 未知动作 'bogus_action'" in err, err


def test_choose_when_depth_limit():
    """choose 的 when 条件树深度复用 CONDITION_TREE_MAX_DEPTH(W3-B): <=16 层通过, >16 层拒绝"""
    head = "config:\n  my_rules:\n    r1:\n      actions:\n"

    def nested(k: int) -> str:
        node = {"size": ">=1MiB"}
        for _ in range(k):
            node = {"all": [node]}
        return json.dumps(node)

    ok = _load_errors(head + f"        - choose: [{{when: {nested(CONDITION_TREE_MAX_DEPTH - 1)}, then: []}}]\n")
    assert ok == "", f"when 深度上限内合法: {ok}"
    err = _load_errors(head + f"        - choose: [{{when: {nested(CONDITION_TREE_MAX_DEPTH)}, then: []}}]\n")
    assert f"组合树嵌套超过上限 {CONDITION_TREE_MAX_DEPTH} 层" in err, err


def test_choose_engine_branch_dispatch(tmp_path):
    """choose 引擎求值(W3-B): 首个命中执行其 then(后续分支短路不再求值); 无命中走 default;
    无命中无 default = 空操作(no_op 语义); 与普通动作混排按 steps 顺序执行"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    client = FakeClient()
    tor = FakeTorrent(tags="", size=100 * 1024**2)  # >=1MiB 命中, tags 不含 HR
    ctx = make_ctx(mgr, tor, client)

    def build(branches, default=None):
        acts = [{"choose": branches}]
        if default is not None:
            acts[0]["default"] = default
        return Rule("g.t", normalize_legacy_rule({"actions": acts}), mgr)

    def block_of(rule):
        assert rule.steps[0][0] == "choose"
        return rule.steps[0][1]

    # 首个命中短路: 第二分支恒真也不再求值, 只执行第一分支 then
    b1, b2 = _Fixed(True), _Fixed(True)
    rule = build(
        [
            {
                "when": {
                    "size": ">=1MiB"
                },
                "then": [{
                    "add_tags": ["THEN1"]
                }]
            },
            {
                "when": {
                    "size": ">=1MiB"
                },
                "then": [{
                    "add_tags": ["THEN2"]
                }]
            },
        ]
    )
    blk = block_of(rule)
    blk.branches[0].tree = ("leaf", b1)
    blk.branches[1].tree = ("leaf", b2)
    assert rule.process(ctx) == VERDICT_EXECUTED
    assert client.calls == [("add_tags", ["THEN1"])], f"首个命中分支执行且短路: {client.calls}"
    assert b2.calls == 0, "后续分支不再求值(短路)"

    # 无命中 -> default
    client.calls.clear()
    rule = build([{"when": {"size": ">=1TiB"}, "then": [{"add_tags": ["NOPE"]}]}], default=[{"add_tags": ["DEF"]}])
    assert rule.process(ctx) == VERDICT_EXECUTED
    assert client.calls == [("add_tags", ["DEF"])], "无命中分支走 default"

    # 无命中且无 default = 空操作(no_op, 与空动作表一致)
    client.calls.clear()
    rule = build([{"when": {"size": ">=1TiB"}, "then": [{"add_tags": ["NOPE"]}]}])
    assert rule.process(ctx) == VERDICT_NO_OP, "无命中无 default = no_op"

    # 与普通动作混排: TOP -> choose(THEN) -> TAIL 顺序执行
    rule = Rule(
        "g.t",
        normalize_legacy_rule(
            {
                "actions":
                    [
                        {
                            "add_tags": ["TOP"]
                        },
                        {
                            "choose": [{
                                "when": {
                                    "size": ">=1MiB"
                                },
                                "then": [{
                                    "add_tags": ["THEN"]
                                }]
                            }]
                        },
                        {
                            "add_tags": ["TAIL"]
                        },
                    ]
            }
        ),
        mgr,
    )
    assert [s[0] for s in rule.steps] == ["action", "choose", "action"], "choose 与普通动作混排进执行步"
    client.calls.clear()
    rule.process(ctx)
    assert client.calls == [("add_tags", ["TOP"]), ("add_tags", ["THEN"]), ("add_tags", ["TAIL"])]


def test_choose_engine_when_error(tmp_path):
    """choose 的 when 求值异常(W3-B 自定口径) -> 整条本轮 VERDICT_ERROR(保守: 不误入 default)"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), FakeClient())
    rule = Rule(
        "g.t",
        normalize_legacy_rule(
            {"actions": [{
                "choose": [{
                    "when": {
                        "size": ">=1MiB"
                    },
                    "then": []
                }],
                "default": [{
                    "add_tags": ["DEF"]
                }]
            }]}
        ),
        mgr,
    )
    rule.steps[0][1].branches[0].tree = ("leaf", _Boom())
    assert rule.process(ctx) == VERDICT_ERROR, "when 求值异常 -> error, 不误入 default"


class _Fail:
    """choose on_error 分派测试用的失败动作桩(不进注册表, 直换分支内插件实例)"""

    name = "fail_stub"

    def execute(self, ctx):
        return ActionResult.fail("stub fail")


def test_choose_engine_on_error_dispatch(tmp_path):
    """choose 内动作 on_error 三档分派(W3-B, 与顶层同语义; 无第二语义分支):
    continue 继续分支后续; stop 中断整条链; retry 挂块首断点 + retry_delay"""
    from auto_qb.core.taskqueue import Task
    from auto_qb.rules.base import VERDICT_RETRY

    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    client = FakeClient()

    def build(then, default=None):
        acts = [{"choose": [{"when": {"size": ">=1MiB"}, "then": then}]}]
        if default is not None:
            acts[0]["default"] = default
        return Rule("g.t", normalize_legacy_rule({"actions": acts}), mgr)

    def branch_of(rule):
        return rule.steps[0][1].branches[0]

    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)

    # continue: 分支内失败后续动作继续
    rule = build([{"add_tags": ["A"], "on_error": {"policy": "continue"}}, {"add_tags": ["B"]}])
    branch_of(rule).actions[0] = _Fail()
    assert rule.process(ctx) == VERDICT_EXECUTED
    assert ("add_tags", ["B"]) in client.calls, "continue 档: 分支内失败后续动作继续"

    # stop(默认): 中断整条链 —— 分支后续与块后动作都不执行; 失败动作本身计已执行
    client.calls.clear()
    rule = build([{"add_tags": ["A"]}, {"add_tags": ["B"]}], default=[{"add_tags": ["DEF"]}])
    rule.steps.append(("action", AddTagsAction(["TAIL"]), Rule._resolve_on_error(None)))
    branch_of(rule).actions[0] = _Fail()
    assert rule.process(ctx) == VERDICT_EXECUTED, "失败动作本身算已执行"
    assert ("add_tags", ["B"]) not in client.calls and ("add_tags", ["TAIL"]) not in client.calls, \
        f"stop 档中断整条链: {client.calls}"

    # retry: 挂块首断点(choose 步粒度, 续跑轮整块重新求值重新分派) + retry_delay=backoff
    client.calls.clear()
    rule = build([{"add_tags": ["A"], "on_error": {"policy": "retry", "retries": 2, "backoff": 30}}])
    branch_of(rule).actions[0] = _Fail()
    task = Task("rule", rule.name, hash=ctx.hash, store=mgr.store, interval=300)
    ctx.task = task
    assert rule.process(ctx) == VERDICT_RETRY, "choose 内 retry 同走任务级 requeue 信号"
    assert task.resume_index == 0, f"断点挂块首(choose 步索引): {task.resume_index}"
    assert task.retry_delay == 30, f"backoff 推迟意图挂 Task: {task.retry_delay}"


def test_choose_nested_construction_rejected(tmp_path):
    """嵌套 choose 构造期兜底(W3-B): 绕过校验器直构造 Rule 遇 then 内嵌套 choose 报 ConfigError"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    nested = {
        "choose": [{
            "when": {
                "size": ">=1MiB"
            },
            "then": [{
                "choose": [{
                    "when": {
                        "size": ">=1MiB"
                    },
                    "then": []
                }]
            }]
        }]
    }
    with pytest.raises(ConfigError, match="choose 内不允许嵌套 choose"):
        Rule("g.t", normalize_legacy_rule({"actions": [nested]}), mgr)


def test_choose_deleted_trigger_whitelist():
    """on_torrent_deleted 白名单覆盖 choose 块内动作(W3-B): then/default 内非白名单动作同样 fail-fast"""
    head = "config:\n  my_rules:\n    r1:\n      trigger: on_torrent_deleted\n      actions:\n"
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: [{add_tags: [\"X\"]}]}]\n")
    assert "choose[0].then[0]: 动作 'add_tags' 不适用于 trigger 'on_torrent_deleted'" in err, err
    err = _load_errors(
        head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n"
        "          default: [{add_tags: [\"X\"]}]\n"
    )
    assert "default[0]: 动作 'add_tags' 不适用于 trigger 'on_torrent_deleted'" in err, err
