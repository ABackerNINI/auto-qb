"""`webui_dom_page_support` 支撑: 从 `test_webui_static_dom_page.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import base64

import json

import os

import re

import shutil

import subprocess

import time

from auto_qb.infra.utils import encode_group_key

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _UI_ALL,
    _ui_shell_inline,
    _ui_aggregate,
    _ui_css_aggregate,
    _app_bundle_files,
    _app_bundle_text,
)


def _bundle_iter():
    """(rel, text) 对迭代: 整包按清单序 —— 「恰好只在一处」类不变量改整包扫描用"""
    for p, rel in _app_bundle_files():
        yield rel, open(p, encoding="utf-8").read()


def _computed_member_names(lines):
    """取一个片段文件里所有 `computed: {` 块的成员名(块缩进 + 2 的成员行)

    比 `_section_members` 多两件事: 1.**所有** computed 块都要取(组件里的 computed 也在内,
    不只看顶层 mixin); 2.终止行按**块的缩进**判定 —— 用 `line.strip() in ("},", "}")`
    会被深层嵌套的 `},`(如 `return {...};` 之后那一行)提前关掉块, 从而漏掉后面的成员。
    """
    out, in_block, indent = set(), False, 0
    for line in lines:
        if not in_block:
            if line.strip() == "computed: {":
                in_block = True
                indent = len(line) - len(line.lstrip())
            continue
        if line.rstrip() in (" " * indent + "},", " " * indent + "}"):
            in_block = False
            continue
        m = re.match(r"^\s{%d}(?:async\s+)?([A-Za-z_$][\w$]*)\s*[(:]" % (indent + 2), line)
        if m:
            out.add(m.group(1))
    return out


# ---- 模板保留前缀守阵(issue 26-10-03-1412 / 26-10-11-2030)扫描单点 ----
# 指令正则组 1 = 引号本身(为 \1 回引用而捕获), 表达式在组 2 —— issue 26-10-11-2030:
# 旧版消费处取 group(1) 当表达式, 组 1 是引号字符, 指令分支检出能力恒为 0(死分支)且全绿无征兆。
_RESERVED_PREFIX_SPAN_PATS = (
    (r"\{\{(.*?)\}\}", 1),  # 插值: 组 1 = 表达式
    (r"""(?:^|\s)(?:v-[\w:.\-]+|@[\w.\-]+|:[\w.\-]+)\s*=\s*(["'])(.*?)\1""", 2),  # 指令: 组 2 = 表达式
)

_RESERVED_PREFIX_WHITELIST = ("$event", "$root", "$emit", "$slots")  # Vue 内建(口径见守阵 docstring), 模板里合法


def _reserved_prefix_problems(rel, text):
    """单份模板源的保留前缀扫描, 返回违规描述列表 —— 真实分片与活性探针共用这一份逻辑

    抽单点的动机(issue 26-10-11-2030): 扫描型守阵「没扫到」与「扫了没有违规」不可分辨,
    死分支不会让任何真实模板变红; 活性探针拿已知违规样本喂同一函数并断言命中,
    才能把「每条形态分支必须活」钉进断言。
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # 注释里的"别这么写"示例不算违规, 否则守阵会逼人删文档
    problems = []
    for pat, expr_group in _RESERVED_PREFIX_SPAN_PATS:
        for m in re.finditer(pat, text, re.S):
            expr, pos = m.group(expr_group), m.start()
            for t in re.finditer(r"(?<![\w$.])([_$][A-Za-z_$][\w$]*)", expr):
                tok = t.group(1)
                if tok in _RESERVED_PREFIX_WHITELIST:
                    continue
                ln = text[:pos].count("\n") + 1
                problems.append(
                    f"{rel}:{ln} 模板表达式含保留前缀标识符 `{tok}` —— Vue 解析不到(_/$ 前缀不对模板暴露, "
                    f"成员定义在 methods/data 里也会抛 ReferenceError 且整块渲染失败); "
                    f"模板处理器一律去前缀, 内部 `_` 方法经无前缀别名中转(issue 26-10-03-1412)"
                )
    return problems


# node 语义电池(不落盘): 加载**真实** config_editor.js + config_rules.js, 用合成 schema 跑
# 「schema → 默认值」阶梯。钉的是**行为**而非文本 —— 单点被拆回三份、或某条口径被改错, 这里红;
# 无 node 静默跳过(与 _scan_js_syntax_with_node 同口径, 不引入 pytest skip)。
_NODE_CFG_DEFAULT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
eval(fs.readFileSync(process.argv[2], "utf8"));
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods);
const IDX = {
  pBool: { name: "pBool", spec_kind: "bool" },
  pList: { name: "pList", spec_kind: "list" },
  pEnum: { name: "pEnum", spec_kind: "enum", options: ["a", "b"] },
  pStr: { name: "pStr", spec_kind: "str", placeholder: ">=1GiB" },
  pObj: { name: "pObj", spec_kind: "object", fields: [
      { key: "req_enum", kind: "enum", options: ["x", "y"], required: true },
      { key: "req_bool", kind: "bool", required: true },
      { key: "req_str", kind: "str", required: true, placeholder: "ph" },
      { key: "opt_str", kind: "str" },
      { key: "sub", kind: "object", required: true, fields: [
          { key: "s_enum", kind: "enum", options: ["p", "q"] },
          { key: "s_bool", kind: "bool" },
          { key: "s_str", kind: "str", placeholder: "sph" },
      ]},
  ]},
  pUnknown: { name: "pUnknown", spec_kind: "zzz", fields: [{ key: "k1", kind: "str", required: true, placeholder: "u" }] },
};
const ctx = Object.assign({ cfgPluginIndex: IDX }, M);
const J = (v) => JSON.stringify(v);
const spec = (n) => ctx.cfgDefaultForPlugin(IDX[n]);
const objSpec = spec("pObj");
const checks = [
  ["插件 bool spec 初值 = \"true\"(与字段级 \"false\" 的分歧点)", spec("pBool") === "true"],
  ["插件 list spec 初值 = []", Array.isArray(spec("pList")) && spec("pList").length === 0],
  ["插件 enum spec 初值 = options[0]", spec("pEnum") === "a"],
  ["插件 str spec 初值 = placeholder(不吃 default)", spec("pStr") === ">=1GiB"],
  ["未知插件 → \"\"(不抛)", ctx.cfgDefaultForPlugin(undefined) === ""],
  ["object spec 只填必填子字段(不含 opt_str)",
    J(objSpec) === J({ req_enum: "x", req_bool: "false", req_str: "ph", sub: { s_enum: "p", s_bool: "false", s_str: "sph" } })],
  ["object spec 的 object 子段按 section 口径(全字段、不再递归)",
    J(objSpec.sub) === J({ s_enum: "p", s_bool: "false", s_str: "sph" })],
  ["未知 spec_kind 沿用旧口径(按子表单造对象)", J(spec("pUnknown")) === J({ k1: "u" })],
  ["可选段 object 字段: 必填优先 + object 子段不递归(走 placeholder/default)",
    J(ctx.cfgDefaultForField({ kind: "object", fields: [
        { key: "a", kind: "enum", options: ["m", "n"], required: true },
        { key: "b", kind: "bool", required: true },
        { key: "c", kind: "str" },
        { key: "d", kind: "object", required: true, placeholder: "dph" },
    ]})) === J({ a: "m", b: "false", d: "dph" })],
  ["可选段非 object 字段 → [](历史口径)", J(ctx.cfgDefaultForField({ kind: "str" })) === "[]"],
  ["字段级 bool = \"false\" / 默认值兜底走 cfgScalar / 空 options 兜底空串",
    J(ctx.cfgDefaultForFields([
      { key: "b", kind: "bool" }, { key: "n", kind: "int", default: 7 }, { key: "e", kind: "enum", options: [] },
    ], {})) === J({ b: "false", n: "7", e: "" })],
];
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

_NODE_RETIRED_KEYS_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods, window.CONFIG_HUB.methods);
const RULES = {
  clean: { enabled: "true", trigger: "interval", conditions: [], actions: [{ add_tags: ["x"] }] },
  stopOnly: { enabled: "true", stop_following_rules_if: "conditions-met", conditions: [], actions: [{ add_tags: ["x"] }] },
  ignoreOnly: { enabled: "true", conditions: [], actions: [{ ignore_next_action_error: "true" }, { add_tags: ["x"] }] },
  both: { enabled: "true", stop_following_rules_if: "never", conditions: [], actions: [{ ignore_next_action_error: "true" }] },
  nestedThen: { enabled: "true", conditions: [], actions: [
      { choose: [{ when: { all: [] }, then: [{ ignore_next_action_error: "true" }, { add_tags: ["t"] }] }] }, { add_tags: ["x"] }] },
  nestedDefault: { enabled: "true", conditions: [], actions: [
      { choose: [{ when: { all: [] }, then: [{ add_tags: ["t"] }] }], default: [{ ignore_next_action_error: "true" }] }] },
  nestedClean: { enabled: "true", conditions: [], actions: [
      { choose: [{ when: { all: [] }, then: [{ add_tags: ["t"] }] }], default: [{ add_tags: ["d"] }] }] },
};
const ctx = Object.assign({
  cfg: { tree: { config: { example_rules: RULES } } },
  cfgConfigPath() { return ["config"]; },
  cfgPluginIndex: { add_tags: { name: "add_tags", label: "添加标签", spec_kind: "list" } },
}, M);
const J = (v) => JSON.stringify(v);
const keys = (rn) => ctx.cfgRuleRetiredKeys("example_rules", rn);
const hint = (rn) => ctx.cfgRuleRetiredHint("example_rules", rn);
const checks = [
  ["无退役键规则 → [](徽标/卡脚不渲染)", J(keys("clean")) === "[]" && hint("clean") === ""],
  ["规则级 stop_following_rules_if 被识别", J(keys("stopOnly")) === J(["stop_following_rules_if"])],
  ["actions 域伪动作被识别", J(keys("ignoreOnly")) === J(["ignore_next_action_error"])],
  ["两键并存全识别(口径=后端 retired_control_keys_in)", J(keys("both")) === J(["stop_following_rules_if", "ignore_next_action_error"])],
  ["choose 分支 then 内嵌套伪动作被识别(issue 26-11-03-1120)", J(keys("nestedThen")) === J(["ignore_next_action_error"])],
  ["块级 default 内嵌套伪动作被识别(issue 26-11-03-1120)", J(keys("nestedDefault")) === J(["ignore_next_action_error"])],
  ["choose 无退役键不误报(嵌套递归零行为变化)", J(keys("nestedClean")) === "[]"],
  ["cfgIsRetiredAction 只认伪动作项", ctx.cfgIsRetiredAction({ ignore_next_action_error: "true" }) && !ctx.cfgIsRetiredAction({ add_tags: ["x"] })],
  ["stop-only 提示宣称转未启用且不开 on_error 空票(等价写法尚未落地)", hint("stopOnly").includes("未启用") && !hint("stopOnly").includes("on_error")],
  ["含 ignore 的提示给等价新写法 on_error: {policy: continue}", hint("ignoreOnly").includes("on_error: {policy: continue}")],
  ["退役伪动作行显示退役标记(不再当动作)", ctx.hubPluginText({ ignore_next_action_error: "true" }) === "已退役: ignore_next_action_error"],
  ["正常动作行人话不受影响", ctx.hubPluginText({ add_tags: ["x"] }).indexOf("添加标签") === 0],
];
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

_NODE_ON_ERROR_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
eval(fs.readFileSync(process.argv[2], "utf8"));
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods);
const RULES = {
  flat: { enabled: "true", actions: [{ add_tags: ["x"] }, { checking: { basic_check: "filelist" } }] },
  mixed: { enabled: "true", actions: [{ add_tags: ["x"], on_error: { policy: "retry", retries: "5", backoff: "30" } }] },
  canonical: { enabled: "true", actions: [{ type: "add_tags", params: ["x"], on_error: { policy: "continue" } }] },
};
const ctx = Object.assign({
  cfg: {
    tree: { config: { example_rules: RULES } },
    schema: {
      constants: {
        on_error_policies: ["stop", "continue", "retry"],
        on_error_defaults: { policy: "stop", retries: 3, backoff: 60 },
      },
    },
  },
  cfgConfigPath() { return ["config"]; },
  cfgPluginIndex: { add_tags: { name: "add_tags", label: "添加标签", spec_kind: "list" } },
}, M);
const J = (v) => JSON.stringify(v);
const val = (rn, i, k) => ctx.cfgOnErrorValue("example_rules", rn, i, k);
const checks = [
  ["缺省 policy = schema constants.on_error_defaults(stop)", val("flat", 0, "policy") === "stop"],
  ["缺省 retries/backoff 同源(3/60)", val("flat", 0, "retries") === "3" && val("flat", 0, "backoff") === "60"],
  ["混合形读已配置值", val("mixed", 0, "retries") === "5" && val("mixed", 0, "backoff") === "30"],
  ["规范形读 policy", val("canonical", 0, "policy") === "continue"],
  ["retry 档开关", ctx.cfgOnErrorIsRetry("example_rules", "mixed", 0) && !ctx.cfgOnErrorIsRetry("example_rules", "flat", 0)],
  ["取值域单源 schema constants", J(ctx.cfgOnErrorPolicies()) === J(["stop", "continue", "retry"])],
  ["写侧: 非缺省 policy 写混合形 on_error",
    (ctx.cfgOnErrorSet("example_rules", "flat", 1, "policy", "continue"),
     J(ctx.cfg.tree.config.example_rules.flat.actions[1].on_error) === J({ policy: "continue" }))],
  ["写侧: retry 档附 retries/backoff 入树",
    (ctx.cfgOnErrorSet("example_rules", "flat", 0, "policy", "retry"),
     ctx.cfgOnErrorSet("example_rules", "flat", 0, "retries", "2"),
     J(ctx.cfg.tree.config.example_rules.flat.actions[0].on_error) === J({ policy: "retry", retries: "2" }))],
  ["写侧: 全缺省整键摘除(YAML 保持简洁)",
    (ctx.cfgOnErrorSet("example_rules", "flat", 0, "policy", "stop"),
     ctx.cfgOnErrorSet("example_rules", "flat", 0, "retries", "3"),
     !("on_error" in ctx.cfg.tree.config.example_rules.flat.actions[0]))],
  ["cfgPluginName 混合形取动作键(on_error 不是插件名)",
    ctx.cfgPluginName({ add_tags: ["x"], on_error: {} }) === "add_tags"],
  ["cfgPluginName 规范形取 type", ctx.cfgPluginName({ type: "add_tags", params: [] }) === "add_tags"],
  ["cfgSpecPath 规范形落 params",
    J(ctx.cfgSpecPath("example_rules", "canonical", "actions", 0)) === J(["config", "example_rules", "canonical", "actions", 0, "params"])],
  ["cfgIsRetiredAction 规范形识别伪动作",
    ctx.cfgIsRetiredAction({ type: "ignore_next_action_error", params: "true" })],
];
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

_NODE_RULE_TREE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
eval(fs.readFileSync(process.argv[2], "utf8"));
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods);
const ctx = Object.assign({
  cfg: {
    tree: { config: { example_rules: {
      legacy: { enabled: "true",
                conditions: [{ size: ">=1MiB" }, { path: ["/a"] }],
                actions: [{ add_tags: ["x"] }, { checking: { basic_check: "filelist" } }] },
      treeform: { enabled: "true",
                  conditions: { any: [{ size: ">=1MiB" }, { not: { tags: "HR" } }] },
                  actions: [{ type: "add_tags", params: ["y"] }] },
      chooser: { enabled: "true",
                 actions: [{ choose: [{ when: [{ size: ">=1MiB" }], then: [{ add_tags: ["T"] }] }],
                            default: [{ add_tags: ["D"] }] }] },
      leafroot: { enabled: "true", conditions: { size: "" } },
      switcher: { enabled: "true", conditions: { all: [{ size: "" }] } },
    } } },
    schema: { constants: {
      on_error_policies: ["stop", "continue", "retry"],
      on_error_defaults: { policy: "stop", retries: 3, backoff: 60 },
    } },
  },
  cfgConfigPath() { return ["config"]; },
  cfgPluginIndex: {
    add_tags: { name: "add_tags", label: "添加标签", spec_kind: "list" },
    size: { name: "size", label: "大小", spec_kind: "str", placeholder: "" },
  },
}, M);
const J = (v) => JSON.stringify(v);
const t = () => ctx.cfg.tree.config.example_rules;
const rp = (rn) => ctx.cfgCondRootPath("example_rules", rn);
const DEF_OE = J({ policy: "stop", retries: 3, backoff: 60 });
// mini ctx(R5#175 摘要/风险段专用): 干净可数的 actions 与规则级字段, 不与前文用例共树;
// cfgPluginIndex 给风险元数据(cfgRuleRisk 的点名与去重敏感名单判据)
const miniRiskCtx = (ruleSpec, meta) => Object.assign({}, M, {
  cfg: { tree: { config: { g: { r: Object.assign({ enabled: "true" }, ruleSpec, meta) } } } },
  cfgPluginIndex: {
    add_tags: { name: "add_tags", label: "添加标签", spec_kind: "list" },
    reannounce: { name: "reannounce", label: "重新汇报", risk: true },
    checking: { name: "checking", label: "校验", risk: true },
    delete_files: { name: "delete_files", label: "删除文件", risk: true },
  },
});
const checks = [
  // ---- 草稿规范化(D2): 打开即归一形, 保存即写新形态 ----
  // 红验式三步(issue 26-11-04-0504): 先钉输入确为扁平列表(fixture 漂成树形则红) -> 调归一
  // -> 再钉变树形(归一没真执行则红)。原来归一塞在逗号表达式里, 绿与"电池没跑到"不可判
  ["cfgNormalizeRulesDraft: 扁平 conditions 包隐式 all(叶子零触碰)",
    (J(t().legacy.conditions) === J([{ size: ">=1MiB" }, { path: ["/a"] }])
     && (ctx.cfgNormalizeRulesDraft(), true)
     && J(t().legacy.conditions) === J({ all: [{ size: ">=1MiB" }, { path: ["/a"] }] }))],
  ["cfgNormalizeRulesDraft: 树形 conditions 零改写",
    J(t().treeform.conditions) === J({ any: [{ size: ">=1MiB" }, { not: { tags: "HR" } }] })],
  ["cfgNormalizeRulesDraft: 扁平动作翻译规范形 + 缺省 on_error 注入",
    J(t().legacy.actions[0]) === J({ type: "add_tags", params: ["x"], on_error: { policy: "stop", retries: 3, backoff: 60 } })],
  ["cfgNormalizeRulesDraft: choose 键面保留 + when 包 all + then/default 注入缺省",
    J(t().chooser.actions[0].choose[0].when) === J({ all: [{ size: ">=1MiB" }] })
    && J(t().chooser.actions[0].choose[0].then[0]) === J({ type: "add_tags", params: ["T"], on_error: { policy: "stop", retries: 3, backoff: 60 } })
    && t().chooser.actions[0].default[0].type === "add_tags"],
  // 幂等改快照深比较(issue 26-11-04-0504): 原来两次返回值被逗号表达式丢弃、第三元素字面量
  // true 恒绿; 归一本身无返回值, 改比整棵 example_rules 前后快照 —— 非幂等必红。
  // 专桩: 同一比较模式喂非幂等样本必须抓出差异, 自证该模式可红(否则又是一条恒绿)
  ["cfgNormalizeRulesDraft 幂等(重复归一零差异)",
    (() => {
      const snap1 = J(ctx.cfg.tree.config.example_rules);
      ctx.cfgNormalizeRulesDraft();
      const snap2 = J(ctx.cfg.tree.config.example_rules);
      ctx.cfgNormalizeRulesDraft();
      return snap1 === snap2 && snap2 === J(ctx.cfg.tree.config.example_rules);
    })()],
  ["幂等比较模式活性专桩: 非幂等样本必须被抓出",
    (() => {
      const s = { conditions: { all: [{ size: "" }] } };
      const step = () => { s.conditions.all.push({ size: "" }); return J(s); };
      return step() !== step();
    })()],
  // ---- 条件树读侧 ----
  ["cfgCondNodeKey: 树形根键", ctx.cfgCondNodeKey(rp("treeform")) === "any"],
  ["cfgCondChildren: 组合孩子数", ctx.cfgCondChildren(rp("treeform")).length === 2],
  ["cfgCondCount: 叶子计数(not 孩子计入)", ctx.cfgCondCount(rp("treeform")) === 2],
  // ---- 条件树写侧 ----
  ["cfgCondRootAdd: 无树建隐式 all",
    (ctx.cfgCondRootAdd("example_rules", "none", "leaf", "size"),
     t().none.conditions.all.length === 1 && t().none.conditions.all[0].size !== undefined)],
  ["cfgCondRootAdd: 组合根追加孩子(any 列表尾插)",
    (ctx.cfgCondRootAdd("example_rules", "treeform", "leaf", "size"),
     J(t().treeform.conditions) === J({ any: [{ size: ">=1MiB" }, { not: { tags: "HR" } }, { size: "" }] }))],
  ["cfgCondRootAdd: 叶子根包 all 再加(合法树形)",
    (ctx.cfgCondRootAdd("example_rules", "leafroot", "leaf", "size"),
     t().leafroot.conditions.all.length === 2 && t().leafroot.conditions.all[0].size !== undefined)],
  ["cfgCondSetCombo: all 切 not 收敛单孩子 / not 切回 all 包列表",
    (ctx.cfgCondSetCombo(rp("switcher"), "all", "not"),
     J(t().switcher.conditions) === J({ not: { size: "" } }),
     ctx.cfgCondSetCombo(rp("switcher"), "not", "all"),
     J(t().switcher.conditions) === J({ all: [{ size: "" }] }))],
  ["cfgCondRemoveAt: 空列表向上收敛删 conditions 键(无条件直过)",
    (ctx.cfgCondRemoveAt(rp("none").concat(["all", 0])),
     !("conditions" in t().none))],
  // ---- choose 编辑器 ----
  ["cfgIsChooseEntry 识别 choose 编排块", ctx.cfgIsChooseEntry(t().chooser.actions[0]) && !ctx.cfgIsChooseEntry(t().legacy.actions[0])],
  ["cfgChooseBranches / cfgThenList 读侧",
    ctx.cfgChooseBranches("example_rules", "chooser", 0).length === 1
    && ctx.cfgThenList("example_rules", "chooser", 0, 0).length === 1],
  ["cfgChooseBranchAdd: 追加分支(when 初始 {all: []})",
    (ctx.cfgChooseBranchAdd("example_rules", "chooser", 0),
     J(t().chooser.actions[0].choose[1].when) === J({ all: [] }))],
  ["cfgActionEntryAddAt: then 加动作写规范形(缺省 on_error)",
    (ctx.cfgActionEntryAddAt(ctx.cfgThenListPath("example_rules", "chooser", 0, 1), "add_tags"),
     J(ctx.cfgThenList("example_rules", "chooser", 0, 1)[0]) === J({ type: "add_tags", params: [], on_error: { policy: "stop", retries: 3, backoff: 60 } }))],
  ["cfgOnErrorValueAt/SetAt 路径版: 非缺省写树/全缺省摘除",
    (ctx.cfgOnErrorSetAt(ctx.cfgThenEntryPath("example_rules", "chooser", 0, 1, 0), "policy", "continue"),
     ctx.cfgOnErrorValueAt(ctx.cfgThenEntryPath("example_rules", "chooser", 0, 1, 0), "policy") === "continue",
     ctx.cfgOnErrorSetAt(ctx.cfgThenEntryPath("example_rules", "chooser", 0, 1, 0), "policy", "stop"),
     !("on_error" in ctx.cfgThenList("example_rules", "chooser", 0, 1)[0]))],
  ["cfgListEntryRemove: then 删动作后 then 键随空摘除",
    (ctx.cfgListEntryRemove(ctx.cfgThenEntryPath("example_rules", "chooser", 0, 1, 0)),
     !("then" in t().chooser.actions[0].choose[1]))],
  ["cfgChooseDefaultToggle: 关 = default 键摘除 / 开 = 空列表落位",
    (ctx.cfgChooseDefaultToggle("example_rules", "chooser", 0, false),
     !("default" in t().chooser.actions[0]),
     ctx.cfgChooseDefaultToggle("example_rules", "chooser", 0, true),
     J(t().chooser.actions[0].default) === J([]))],
  // ---- 规则卡摘要与风险聚合(R5#175): cfgRuleRisk / cfgTriggerLabel / cfgRuleMetaSummary ----
  // 喂 hubRiskList -> 首页 LED 与「N 条含风险」徽标。用独立 mini-ctx(主 ctx 的 example_rules
  // 已被前面用例改写, 风险判定要的是干净可数的 actions/规则级字段), 方法体仍是同一份。
  ["cfgRuleRisk: 高风险动作点名 + noDedup 双记(reannounce 无执行一次/冷却)",
    (() => {
      const c = miniRiskCtx({ actions: [{ type: "reannounce", params: [] }] }, {});
      const s = c.cfgRuleRisk("g", "r");
      return s.indexOf("含高风险动作: reannounce") >= 0 && s.indexOf("未配置去重") >= 0 && s.indexOf("; ") >= 0;
    })()],
  ["cfgRuleRisk: noDedup 判据边界(执行一次=once 或 冷却非零 都算已去重)",
    (() => {
      const risky = [{ type: "reannounce", params: [] }];
      return miniRiskCtx({ actions: risky }, { execute_once: "once" }).cfgRuleRisk("g", "r").indexOf("未配置去重") < 0
        && miniRiskCtx({ actions: risky }, { cooldown: "10S" }).cfgRuleRisk("g", "r").indexOf("未配置去重") < 0
        && miniRiskCtx({ actions: risky }, { cooldown: "0" }).cfgRuleRisk("g", "r").indexOf("未配置去重") >= 0
        && miniRiskCtx({ actions: risky }, { cooldown: "" }).cfgRuleRisk("g", "r").indexOf("未配置去重") >= 0;
    })()],
  ["cfgRuleRisk: 高风险但非去重敏感动作只点名不劝去重; 无高风险动作为空串",
    (() => {
      const del = miniRiskCtx({ actions: [{ type: "delete_files", params: [] }] }, {});
      const clean = miniRiskCtx({ actions: [{ type: "add_tags", params: [] }] }, {});
      const sDel = del.cfgRuleRisk("g", "r");
      return sDel.indexOf("含高风险动作: delete_files") >= 0 && sDel.indexOf("未配置去重") < 0
        && clean.cfgRuleRisk("g", "r") === "";
    })()],
  ["cfgTriggerLabel: 五张中文短标签 + 未知值原样 + 空值兜「周期检查」",
    (() => {
      const c = miniRiskCtx({}, {});
      return c.cfgTriggerLabel("interval") === "周期检查"
        && c.cfgTriggerLabel("on_torrent_added") === "种子新增时"
        && c.cfgTriggerLabel("on_torrent_deleted") === "种子删除时"
        && c.cfgTriggerLabel("on_torrent_state_enum_changed") === "状态变化时"
        && c.cfgTriggerLabel("on_torrent_field_changed") === "字段变化时"
        && c.cfgTriggerLabel("weird_trigger") === "weird_trigger"
        && c.cfgTriggerLabel("") === "周期检查" && c.cfgTriggerLabel(null) === "周期检查";
    })()],
  ["cfgRuleMetaSummary: 触发时机 + 非默认间隔/去重/冷却全拼; 缺省只剩触发时机",
    (() => {
      const full = miniRiskCtx({}, { trigger: "interval", interval: "5M", execute_once: "once", cooldown: "10S" });
      const bare = miniRiskCtx({}, {});
      return full.cfgRuleMetaSummary("g", "r") === "周期检查 · 间隔 5M · 仅执行一次 · 冷却 10S"
        && bare.cfgRuleMetaSummary("g", "r") === "周期检查";
    })()],
  ["cfgRuleMetaSummary: 间隔零值不占摘要(0/0S/空), 去重档位中文映射",
    (() => {
      const zero = (iv) => miniRiskCtx({}, { trigger: "interval", interval: iv }).cfgRuleMetaSummary("g", "r");
      const daily = miniRiskCtx({}, { execute_once: "daily" }).cfgRuleMetaSummary("g", "r");
      const hourly = miniRiskCtx({}, { execute_once: "hourly" }).cfgRuleMetaSummary("g", "r");
      const never = miniRiskCtx({}, { execute_once: "never" }).cfgRuleMetaSummary("g", "r");
      return zero("0") === "周期检查" && zero("0S") === "周期检查" && zero("") === "周期检查"
        && daily.indexOf("每天一次") >= 0 && hourly.indexOf("每小时一次") >= 0 && never === "周期检查";
    })()],
  ["cfgRuleMetaSummary: 非 interval 触发不吃间隔段(键在也不显)",
    (() => {
      const c = miniRiskCtx({}, { trigger: "on_torrent_added", interval: "5M", cooldown: "10S" });
      return c.cfgRuleMetaSummary("g", "r") === "种子新增时 · 冷却 10S";
    })()],
];
// 活性注入(issue 26-11-04-0504, 坑档 pitfalls/testing/guard-dead-branch 手法): Python 侧
// 二次运行传 "liveness" 追加一例必红期望, 供端到端红验 —— 电池空转(某条语句早退/结果
// 未真实比对)时注入的红不会出现在 failed, Python 侧即报。正常运行不带此参, 不含本条。
if (process.argv[3] === "liveness") {
  checks.push(["活性探针: 故意注入必红期望(端到端红验专用)", false]);
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

_NODE_LIST_EMPTY_PROBE = r"""
const fs = require("fs");
const vm = require("vm");
const window = {};
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), { window, console, Set, Map, Math, JSON });
const F = window.AQB_FILTERS;
//  computed 里的三个 *EmptyText 会调 methods 里的单点, 与 app 里 methods+computed 合成同一实例等价
function ctx(o) {
  const c = Object.assign({
    searchQuery: "", searchNegativeOnly: false, searchBuilding: false,
    filtersActive: false, l10nGroup: "辅种",
  }, o);
  for (const k of Object.keys(F.methods)) c[k] = F.methods[k];
  return c;
}
const NEG = "只有排除词 — 请补一个要包含的词";
const BUILD = "正在构建文件索引…";
// 三张列表 × 五种空态场景 = 15 项。三个名词位的分工: 「无匹配」走 hitNoun、面筛走 noun、全空走 noneText
const EXPECT = {
  plain:    { groupsEmptyText: "暂无辅种", torrentsEmptyText: "暂无种子", showsEmptyText: "暂无剧集可展示" },
  filter:   { groupsEmptyText: "当前筛选下没有辅种", torrentsEmptyText: "当前筛选下没有种子", showsEmptyText: "当前筛选下没有剧集" },
  negative: { groupsEmptyText: NEG, torrentsEmptyText: NEG, showsEmptyText: NEG },
  building: { groupsEmptyText: BUILD, torrentsEmptyText: BUILD, showsEmptyText: BUILD },
  hit:      { groupsEmptyText: "无匹配种子", torrentsEmptyText: "无匹配种子", showsEmptyText: "无匹配剧集" },
};
const STATES = {
  plain:    {},
  filter:   { filtersActive: true },
  negative: { searchQuery: "-abc", searchNegativeOnly: true },
  building: { searchQuery: "abc", searchBuilding: true },
  hit:      { searchQuery: "abc" },
};
const failed = [];
let total = 0;
for (const [scene, state] of Object.entries(STATES)) {
  const c = ctx(state);
  for (const [fn, want] of Object.entries(EXPECT[scene])) {
    total++;
    const got = F.computed[fn].call(c);
    if (got !== want) failed.push(`${scene}/${fn} = ${JSON.stringify(got)}(应为 ${JSON.stringify(want)})`);
  }
}
console.log(JSON.stringify({ total: total, failed: failed }));
"""

_NODE_WIN_SRC_PROBE = r"""
const fs = require("fs");
// 桩浏览器全局: window(文档滚动几何 + 绑定录制) / rAF(同步执行) / 行窗口化常量(单点在 app.js, 电池自给)
global.__winBind = [];
global.window = {
  scrollY: 1000, innerHeight: 800,
  addEventListener: (t, h, o) => global.__winBind.push(["on", t, h, o]),
  removeEventListener: (t, h) => global.__winBind.push(["off", t, h]),
};
global.requestAnimationFrame = (fn) => { fn(); return 1; };
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
// 首访估算开窗阈值(2026-11-02 二轮按拐点实测从 1000 下移到 200, 与 ROW_WIN_MIN 合并;
// 单点仍在 app.js, 电池自给)
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = { M: window.AQB_COLUMNS.methods, DOC: WIN_SRC_DOC, SRC: WIN_SOURCES, ctr: winSrcContainer };");
const { M, DOC, SRC, ctr } = globalThis.__W2__;

// 行集: 300 行, 两种行高混排(43.7 / 65.4, 同主表实测口径); 键字段按 kind 分流(hash / k)
const N = 300;
const mkRows = (fld) => Array.from({ length: N }, (_, i) => ({ [fld]: fld + i }));
const hOf = (i) => (i % 2 ? 65.4 : 43.7);
const fillHs = (kind, rows, hs) => rows.forEach((r, i) => { hs[kind + ":" + r[kind === "ctr" ? "k" : "hash"]] = hOf(i); });
const GAP = 6;

// 滚动容器桩: scrollTop/clientHeight/rect 全可控; 监听录制
const mkSc = () => {
  const rec = [];
  const sc = {
    scrollTop: 1200, clientHeight: 800,
    getBoundingClientRect: () => ({ top: 0 }),
    addEventListener: (t, h, o) => rec.push(["on", t, h, o]),
    removeEventListener: (t, h) => rec.push(["off", t, h]),
  };
  return { sc, rec };
};

// 窗口化引擎态: 表顶在内容偏移 1200 / 视口 800; rel 与 _rowHs 逐场景覆写
// W3: 滚动几何按源族分流 —— 文档型读 _winScrollY/_winViewH, 容器型读 _winCtnState()
// (抽屉 .drawer-body 一对, 与文档对分家: 主表与抽屉同屏, 两套坐标系混用会互相漂移)。
const mkCtx = () => Object.assign({}, M, {
  rowWin: true,
  _winMeasured: { torrent: true, group: true, member: true, ctr: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, ctr: 50, drawerContent: 50 },
  _rowHVer: 7,
  _winViewH: 800,
  _winScrollY: 0,
  _winCtn: { y: 0, h: 800 },  // 容器族引擎态(真机由 _winCtnState 惰性建 Vue.reactive 版)
  _winTop: { torrent: 0, group: 0, member: 0, ctr: 0, drawerContent: 0 },
  _rowHs: {},
  _rowPre: {},  // 前缀和留存(created 初始化, 电池自给)
  _winGapFor: () => GAP,
});

const checks = [
  // --- 首访路径边界(空档2, issue 26-11-02-0902 二轮): EST_MIN 两侧必须真的分路径 ---
  // _winMeasured=false 模拟首访 + _rowHs 空(未量行走 EST/均值兜底); gap 由 mkCtx 给 6(非
  // null, 跳过 fallback 分支)。门控被误改成"恒窗口"或"恒 off"时, 下面两条必有一条红。
  ["边界 EST_MIN-1: n=199 首访走 off(全量渲染, 无窗口)", (() => {
      const c = mkCtx(); c._winMeasured.torrent = false; c._rowHs = {};
      const rows = Array.from({ length: 199 }, (_, i) => ({ hash: "b" + i }));
      const w = M._rowWindow.call(c, "torrent", rows, null);
      return w.active === false && w.end === 199;
  })()],
  ["边界 EST_MIN: n=200 首访走估算开窗(active 窗口)", (() => {
      const c = mkCtx(); c._winMeasured.torrent = false; c._rowHs = {};
      const rows = Array.from({ length: 200 }, (_, i) => ({ hash: "b" + i }));
      const w = M._rowWindow.call(c, "torrent", rows, null);
      return w.active === true;
  })()],
  // --- 文档型描述符几何(主表现行为原样) ---
  ["DOC.scrollY 直读 window.scrollY", DOC.scrollY() === 1000],
  ["DOC.viewH 直读 window.innerHeight", DOC.viewH() === 800],
  ["DOC.topOffset = rect.top + scrollY", DOC.topOffset({ getBoundingClientRect: () => ({ top: 200 }) }) === 1200],
  ["DOC.bindScroll 挂 window passive", (() => { const h = () => {}; DOC.bindScroll(h); DOC.unbindScroll(h);
      return JSON.stringify(global.__winBind) === JSON.stringify([["on", "scroll", h, { passive: true }], ["off", "scroll", h]]); })()],
  // --- 容器型描述符几何(下桩 scrollTop/clientHeight) ---
  ["CTR.scrollY = scrollTop", (() => { const { sc } = mkSc(); const d = ctr(() => sc); return d.scrollY() === 1200 && (sc.scrollTop = 1600) && d.scrollY() === 1600; })()],
  ["CTR.viewH = clientHeight", ctr(() => mkSc().sc).viewH() === 800],
  ["CTR.topOffset = 相对容器内容顶", (() => { const { sc } = mkSc(); const d = ctr(() => sc);
      const el = { getBoundingClientRect: () => ({ top: 90 }) };
      return d.topOffset(el) === 90 - 0 + 1200 && d.topOffset(null) === 0; })()],
  ["CTR.topOffset 容器未渲染回落 0(零差异回退)", ctr(() => null).topOffset({ getBoundingClientRect: () => ({ top: 1 }) }) === 0
      && ctr(() => null).scrollY() === 0 && ctr(() => null).viewH() === 0],
  ["CTR.bindScroll 挂元素 passive + unbind 摘除(无 RO 环境不挂)", (() => { const { sc, rec } = mkSc(); const d = ctr(() => sc);
      const h = () => {}; d.bindScroll(h); d.unbindScroll(h);
      return JSON.stringify(rec) === JSON.stringify([["on", "scroll", h, { passive: true }], ["off", "scroll", h]]); })()],
  // --- kind 解析与行键 ---
  ["主表三 kind 注册齐全: torrent/member 共用文档型, group 克隆换行键但同族(doc)", SRC.torrent === DOC && SRC.member === DOC
      && SRC.group !== DOC && SRC.group.keyOf({ key: "a" }) === "a" && SRC.group.scrollY() === 1000
      && DOC.family === "doc" && SRC.torrent.family === "doc" && SRC.member.family === "doc"
      && SRC.group.family === "doc" && SRC.drawerContent.family === "container"],
  ["未注册 kind 回落文档型", M._winSrc("nope") === DOC && M._winSrc("torrent") === DOC && M._winSrc("member") === DOC],
  ["主表行键: group=item.key 其余=item.hash", M._rowKeyOf("group", { key: "g1" }) === "group:g1"
      && M._rowKeyOf("torrent", { hash: "t1" }) === "torrent:t1" && M._rowKeyOf("member", { hash: "m1" }) === "member:m1"],
  ["容器 kind 注册后行键从描述符给(W3 接线路径)", (() => {
      const { sc } = mkSc();
      SRC.ctr = Object.assign({}, ctr(() => sc), { keyOf: (it) => it.k });
      const ok = M._rowKeyOf("ctr", { k: "x" }) === "ctr:x";
      delete SRC.ctr;  // 注册动作本身也是 W3 的活, 电池不留痕
      return ok; })()],
  // --- 合帧写回走描述符 ---
  ["_onWinResize/_onWinScroll 经描述符写回引擎态", (() => {
      const c = Object.assign({}, M, { _winResize: 0, _winViewH: 0, _winScrollY: 0, _winRaf: 0 });
      window.scrollY = 1555; window.innerHeight = 900;
      c._onWinResize(); const a = c._winViewH === 900 && c._winScrollY === 1555 && c._winResize === 1;
      c._winScrollY = 0; c._onWinScroll(); const b = c._winScrollY === 1555;
      window.scrollY = 1000; window.innerHeight = 800;  // 还原桩
      return a && b; })()],
];

// --- 切片等价电池: 同输入(行高/间距/rel/视口)下文档型与容器型起点/终点/占位逐位相同, 三个滚动位 ---
const sliceEq = () => {
  const sc = mkSc();
  const d = ctr(() => sc.sc);
  SRC.ctr = Object.assign({}, d, { keyOf: (it) => it.k });
  const rowsT = mkRows("hash"), rowsC = mkRows("k");
  const ctxT = mkCtx(), ctxC = mkCtx();
  fillHs("torrent", rowsT, ctxT._rowHs);
  fillHs("ctr", rowsC, ctxC._rowHs);
  const out = [];
  for (const into of [1000, 3000, 8000]) {  // 滚进表块 1000 / 3000 / 8000(全部窗内, 避开端点钳位)
    // 文档型: 表顶文档偏移 1200(= 200 rect.top + 1000 scrollY), 滚到 1200+into
    ctxT._winTop.torrent = 1200; ctxT._winScrollY = 1200 + into;
    // 容器型: 表顶内容偏移 1200; el 的 rect.top 按物理随滚动走(content 偏移 - scrollTop),
    // 故无论何时量 topOffset 恒得 1200 —— 与引擎「签名变化时量一次、滚动只动 scrollTop」同构
    sc.sc.scrollTop = 1200 + into;
    ctxC._winTop.ctr = d.topOffset({ getBoundingClientRect: () => ({ top: 1200 - sc.sc.scrollTop }) });
    ctxC._winCtn = { y: d.scrollY(), h: sc.sc.clientHeight };
    const a = ctxT._rowWindow("torrent", rowsT, "torrentTable");
    const b = ctxC._rowWindow("ctr", rowsC, null);
    out.push(JSON.stringify(a) === JSON.stringify(b)
      && a.active && a.start > 0 && a.end < N && a.padTop > 0 && a.padBottom > 0);
  }
  delete SRC.ctr;
  return out.every(Boolean);
};
checks.push(["容器型切片与文档型同输入同输出(三滚动位, 活窗+占位齐)", sliceEq()]);

// --- W3 源族分流: 容器族滚动不写文档对, 文档族滚动不写容器对(主表与抽屉同屏不互相漂移) ---
const familySplit = () => {
  const rows = mkRows("hash");
  const c = mkCtx();
  fillHs("torrent", rows, c._rowHs);
  c._winTop.torrent = 1200; c._winScrollY = 2200;   // 文档族滚动位
  const wDoc = c._rowWindow("torrent", rows, "torrentTable");
  const docY1 = c._winScrollY;
  c._winCtn = { y: 9999, h: 800 };                  // 容器族滚动位(抽屉滚到别处)
  c._winMeasured.ctr2 = true;                       // 未注册 kind 的量齐位(回落文档族路径)
  const wCtn = c._rowWindow("ctr2", mkRows("k"), null);  // 未注册 kind 回落文档族(现行为)
  // 未注册 kind 仍走文档对(不受容器态影响); 容器族 kind 只读 _winCtn
  SRC.dctr = Object.assign({}, ctr(() => mkSc().sc), { keyOf: (it) => it.k });
  const rowsD = mkRows("k");
  const c2 = mkCtx();
  fillHs("dctr", rowsD, c2._rowHs);
  c2._winMeasured.dctr = true; c2._rowH.dctr = 50;  // dctr 的量齐位(电池自给, mkCtx 未含)
  c2._winScrollY = 2200; c2._winCtn = { y: 9999, h: 800 }; c2._winTop.dctr = 0;
  const wD = c2._rowWindow("dctr", rowsD, null);
  const okCtn = wD.active && wD.start > 0 && wD.padTop > 0;  // 按容器 y=9999 切片(与文档 y 无关)
  const docStill = c._winScrollY === docY1 && wDoc.active;   // 文档族态未被容器读路径动过
  delete SRC.dctr;
  return okCtn && docStill && wCtn.active;
};
checks.push(["源族分流: 容器族只读 _winCtn / 文档族只读 _winScrollY 对, 未注册 kind 回落文档族", familySplit()]);

// --- group 克隆描述符两态(issue 26-11-03-1035): group 是 Object.assign 换行键的克隆, 旧码
// 按对象身份判族恒假 —— 抽屉关 = 窗口化关闭全量渲染; 抽屉开 = 切片跟抽屉滚(文档 y 被无视)。
// 两态都必须 active 且窗口逐位相同(同按文档坐标切片): 抽屉关 h=0 不许把 group 关进全量,
// 抽屉滚到 5000 不许把切片拽走(文档滚动位恒 2000)。
const groupCloneFamily = () => {
  const rows = Array.from({ length: N }, (_, i) => ({ key: "g" + i }));
  const mk = (ctnY, ctnH) => {
    const c = mkCtx();
    c._winTop.group = 0; c._winScrollY = 2000; c._winCtn = { y: ctnY, h: ctnH };
    rows.forEach((r, i) => { c._rowHs["group:" + r.key] = i % 2 ? 65.4 : 43.7; });
    return c;
  };
  const closed = mk(0, 0)._rowWindow("group", rows, null);      // 抽屉关: 容器视口 0
  const open = mk(5000, 800)._rowWindow("group", rows, null);   // 抽屉开滚到 5000
  return closed.active && closed.start > 0 && closed.end < N
    && closed.padTop > 0 && closed.padBottom > 0
    && JSON.stringify(closed) === JSON.stringify(open);
};
checks.push(["group 克隆描述符两态按文档坐标切片(抽屉关 h=0 / 抽屉开滚 5000, 窗口逐位相同)", groupCloneFamily()]);

// --- 零差异回退不回潮 ---
const fallback = () => {
  const rows = mkRows("hash");
  const base = () => Object.assign({}, M, {
    rowWin: true, _winMeasured: { torrent: true }, _rowH: { torrent: 50 }, _rowHVer: 1,
    _winViewH: 800, _winScrollY: 1300, _winTop: { torrent: 1200 }, _rowHs: {}, _rowPre: {},
    _winGapFor: () => GAP,
  });
  const small = base(); small._rowHs = {}; fillHs("torrent", rows, small._rowHs);
  const off = base(); off.rowWin = false; fillHs("torrent", rows, off._rowHs);
  // 未量齐(issue 26-11-02-0902 二轮): 阈值 1000→200 后 n>=EST_MIN 的首访改走**估算开窗**
  // (EST/全局均值兜底, active 窗口), 不再退全量渲染 —— off 只剩 n<MIN / rowWin 关 / 视口 0。
  const unmeasured = base(); unmeasured._winMeasured = { torrent: false }; fillHs("torrent", rows, unmeasured._rowHs);
  const noVh = base(); noVh._winViewH = 0; fillHs("torrent", rows, noVh._rowHs);
  const rowsSmall = rows.slice(0, 199);
  const w1 = small._rowWindow("torrent", rowsSmall, "torrentTable");
  const w2 = off._rowWindow("torrent", rows, "torrentTable");
  const w3 = unmeasured._rowWindow("torrent", rows, "torrentTable");
  const w4 = noVh._rowWindow("torrent", rows, "torrentTable");
  const inert = (w, n) => !w.active && w.start === 0 && w.end === n && w.padTop === 0 && w.padBottom === 0;
  return inert(w1, rowsSmall.length) && inert(w2, rows.length) && w3.active
    && inert(w4, rows.length);
};
checks.push(["零差异回退: 行数<MIN / rowWin 关 / 视口 0 一律全量渲染; 未量齐+n>=EST_MIN 改估算开窗(active)", fallback()]);

console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""
