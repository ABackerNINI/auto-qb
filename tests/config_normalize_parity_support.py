"""`config_normalize_parity` 支撑: 前端 cfgNormalize* 与后端 compat 规范化的**跨语言对拍**单点(issue 26-11-03-1120)

背景: `shared/config_rules.js` 的 `cfgNormalizeActionEntryDraft` / `cfgNormalizeRulesDraft` 是
`config/compat.py` 的 `normalize_action_entry` / `normalize_legacy_rule` 的 JS 镜像(**手抄**) —— 打开
设置页显示的即归一形, 保存即写新形态。两侧各有自己的期望电池(Python 侧 pytest 断言, JS 侧 DOM
电池手写期望), 但**没有一份输入同时喂两边、比对两侧输出的用例**: 任一侧改归一语义(新增缺省键、
改退役动作处理、调 choose 键面), 只要各自电池跟着改, 全部能绿。

本文件把"同一输入"收敛到一处:
- `PARITY_CASES`: (case_id, rule_spec) 清单 —— 覆盖旧扁平动作 / 混合形 / 规范形 / 退役伪动作 /
  choose 编排块 / 条件侧扁平与树形 / 非法形状透传;
- `python_normalize(spec)` = `normalize_legacy_rule` —— Python 侧真身(不是再手写一份期望);
- `_NODE_PARITY_PROBE` = 同一批 spec 走 `cfgNormalizeRulesDraft` 后 dump 回 stdout 的 node 电池;

两侧产出在 `test_webui_config_normalize_parity.py` 里 `==` 比对。⚠ 期望不写在这里: 写了就是
"第三份手抄", 又在两侧之外漂流。这里只放输入; 输出以 Python 侧为基准, JS 侧追平 —— 谁改了
语义, 对拍用例就红, 逼改动方同时改两侧(或明确退役前端镜像)。
"""

import json

from auto_qb.config.compat import normalize_legacy_rule

# (case_id, 规则 spec) —— spec 是 YAML BaseLoader 载入后的形态: 所有标量都是字符串
PARITY_CASES = (
    # ---- 动作侧: 旧扁平单键形 ----
    ("flat_action", {
        "enabled": "true",
        "actions": [{
            "add_tags": ["x"]
        }]
    }),
    (
        "flat_actions_multi", {
            "actions": [{
                "add_tags": ["a", "b"]
            }, {
                "remove_tags": ["c"]
            }, {
                "checking": {
                    "basic_check": "filelist"
                }
            }]
        }
    ),
    # ---- 动作侧: webui 动作卡写出的混合形(动作键 + on_error, 可能缺子键) ----
    (
        "mixed_full_on_error", {
            "actions": [{
                "add_tags": ["x"],
                "on_error": {
                    "policy": "retry",
                    "retries": "5",
                    "backoff": "30"
                }
            }]
        }
    ),
    ("mixed_partial_on_error", {
        "actions": [{
            "add_tags": ["x"],
            "on_error": {
                "policy": "continue"
            }
        }]
    }),
    ("mixed_empty_on_error", {
        "actions": [{
            "add_tags": ["x"],
            "on_error": {}
        }]
    }),
    # ---- 动作侧: 已规范形 ----
    ("canonical_no_on_error", {
        "actions": [{
            "type": "add_tags",
            "params": ["y"]
        }]
    }),
    (
        "canonical_with_on_error", {
            "actions":
                [{
                    "type": "add_tags",
                    "params": ["y"],
                    "on_error": {
                        "policy": "stop",
                        "retries": 3,
                        "backoff": 60
                    }
                }]
        }
    ),
    # ---- 动作侧: 退役伪动作(容器归一但**不注入** on_error) ----
    ("retired_pseudo_flat", {
        "actions": [{
            "ignore_next_action_error": "true"
        }, {
            "add_tags": ["x"]
        }]
    }),
    ("retired_pseudo_canonical", {
        "actions": [{
            "type": "ignore_next_action_error",
            "params": "true"
        }]
    }),
    # ---- 动作侧: choose 编排块(键面保留; when 建树; then/default/blog 内动作归一; 未知键透传) ----
    (
        "choose_flat_when", {
            "actions":
                [
                    {
                        "choose": [{
                            "when": [{
                                "size": ">=1MiB"
                            }],
                            "then": [{
                                "add_tags": ["T"]
                            }]
                        }],
                        "default": [{
                            "add_tags": ["D"]
                        }]
                    }
                ]
        }
    ),
    (
        "choose_tree_when", {
            "actions":
                [
                    {
                        "choose":
                            [
                                {
                                    "when": {
                                        "any": [{
                                            "size": ">=1MiB"
                                        }, {
                                            "not": {
                                                "tags": "HR"
                                            }
                                        }]
                                    },
                                    "then":
                                        [
                                            {
                                                "type": "add_tags",
                                                "params": ["T"]
                                            }, {
                                                "checking": {
                                                    "basic_check": "filelist"
                                                }
                                            }
                                        ]
                                }
                            ]
                    }
                ]
        }
    ),
    (
        "choose_unknown_keys", {
            "actions": [{
                "choose": [{
                    "when": {
                        "all": []
                    },
                    "then": [{
                        "add_tags": ["T"]
                    }],
                    "extra": "keep"
                }]
            }]
        }
    ),
    ("choose_invalid_shapes", {
        "actions": [{
            "choose": [{
                "when": [],
                "then": {
                    "add_tags": ["T"]
                }
            }, "raw-branch"]
        }]
    }),
    ("choose_missing_default", {
        "actions": [{
            "choose": []
        }, {
            "choose": "not-a-list"
        }]
    }),
    # ---- 动作侧: 非法形状原样透传(交校验器按扁平坐标报) ----
    ("actions_invalid", {
        "actions": ["scalar", {
            "a": 1,
            "b": 2
        }, {
            "on_error": {
                "policy": "stop"
            }
        }, 7]
    }),
    # ---- 条件侧: 扁平列表包隐式 all / 树形零改写 / 非 list 非 dict 透传 ----
    ("conditions_flat", {
        "conditions": [{
            "size": ">=1MiB"
        }, {
            "path": ["/a"]
        }, {
            "tags": "HR"
        }]
    }),
    ("conditions_tree", {
        "conditions": {
            "any": [{
                "size": ">=1MiB"
            }, {
                "not": {
                    "tags": "HR"
                }
            }]
        }
    }),
    ("conditions_leaf", {
        "conditions": {
            "size": ">=1MiB"
        }
    }),
    ("conditions_invalid", {
        "conditions": "bogus"
    }),
    ("conditions_empty_list", {
        "conditions": []
    }),
    # ---- 命名透传 + 其它键零触碰 ----
    (
        "name_passthrough", {
            "name": "组.规则",
            "enabled": "true",
            "trigger": "interval",
            "cooldown": "0S",
            "unknown_key": {
                "nested": [1, 2]
            },
            "actions": [{
                "add_tags": ["x"]
            }]
        }
    ),
    # ---- 无 conditions / 无 actions 的规则 ----
    ("actions_only", {
        "actions": [{
            "add_tags": ["x"]
        }]
    }),
    ("conditions_only", {
        "conditions": [{
            "size": ">=1MiB"
        }]
    }),
    ("empty_spec", {}),
)


def python_normalize(spec):
    """Python 侧归一(前端镜像的目标语义: `compat.normalize_legacy_rule` 单点)"""
    return normalize_legacy_rule(spec)


def cases_json():
    """PARITY_CASES 的 JSON 形态, 带进 node 电池当输入(避免两侧各写一遍 spec 字面量)"""
    return json.dumps([[cid, spec] for cid, spec in PARITY_CASES], ensure_ascii=False)


# node 电池: 加载真实 config_rules.js(取 methods) + shared 依赖的 config_editor.js,
# 逐条喂 PARITY_CASES 的 spec 走 cfgNormalizeRulesDraft, 按同便结构 dump 回 stdout
# (`{ <case_id>: <normalized spec | null> }`)。与 tests/webui_dom_page_support.py 的
# _NODE_RULE_TREE_PROBE 同口径: global.window 打桩 + eval 两个域脚本 + Object.assign methods。
_NODE_PARITY_PROBE = r"""
const fs = require("fs");
const CASES = JSON.parse(process.argv[3]);
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
eval(fs.readFileSync(process.argv[2], "utf8"));
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods);
const out = {};
for (const [cid, spec] of CASES) {
  const ctx = Object.assign({
    cfg: { tree: { config: { example_rules: { [cid]: spec } } } },
    cfgPluginIndex: {},
  }, M);
  ctx.cfgConfigPath = function () { return ["config"]; };
  try {
    ctx.cfgNormalizeRulesDraft();
    const got = ctx.cfg.tree.config.example_rules[cid];
    out[cid] = got === undefined ? null : got;
  } catch (e) {
    out[cid] = { "__error__": String(e && e.message || e) };
  }
}
process.stdout.write(JSON.stringify(out));
"""
