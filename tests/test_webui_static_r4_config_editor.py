"""test_webui_static_r4_config_editor 测试计划: 存量评审 R4 static 主题清池 P05 —— config_editor* 域
1 修复回归 + 6 node 电池(R5#153 修复; R5#167/168/169/170/171/176 补测)

## 测试计划(每个测试函数一条)
- test_r4_cfgload_select_key_liveness: R5#153 修复回归 —— cfgLoad 对 trackerKey/ruleGroupKey 做
  存在性校验: 重拉树后键已消失(重命名 A→B 未保存点「放弃改动」, 磁盘仍是 A)即回落首项, 幽灵键
  不再渲染、编辑字段经 cfgSetPath 不再把 config.trackers.B 写回树(静默复活改名); 有效键保留、
  为空选首项、空容器回落 null(原语义不回归); cfgDiscard 三分支经真 cfgLoad 结算(净树直重拉/
  脏确认放弃回磁盘/脏取消不动)
- test_r4_unit_controls_family: R5#168(major) —— 数值+单位控件族: cfgUnitParts 三个 kind 的拆/
  拼往返(零漂移)与回退分支(空串/无单位/非法串/单位不在表内/unitDefault 优先于梯回退)、
  cfgUnitOptions/cfgHasUnit 未知 kind 回退、cfgUnitLabel time 中文映射与非字符串归一、
  cfgSetUnit 空数值写空串(不产生裸单位)与 trim
- test_r4_unsaved_guard_chain: R5#167(major) —— 未保存改动防护链: cfgGuardSync 挂摘幂等
  (净树不挂/脏挂一次/重复挂不叠/摘按同句柄)与双脏源(kbDirtyView 单独为真也挂)、
  _cfgOnBeforeUnload(脏 preventDefault+returnValue/净 undefined)、_cfgOnReloadKey 四道闸
  (defaultPrevented/IME/无脏/modal 已开全放行)与 F5/Ctrl+R/Cmd+R 命中、cfgReloadGuard 三分支
  结算(保存失败不刷新不摘兜底且 saveError/toast 落账/保存成功摘兜底后刷新且键位草稿后存/
  放弃改动并刷新不存键位/留页零动作零请求)、cfgSave 经真 api 桩走通成功与失败两形态
- test_r4_site_fallback_chain: R5#169(major) —— 站点回退链整族: cfgSiteFallbackPath 路径形态判据
  (链上 7 键 mid=[] 与 hr 两形态/全局页/链外键/短路径/非数组均 null)、cfgFallbackValue 回填链
  (全局值命中/全局缺失走 schema 默认/全局 '' 按缺失/链外键反例)、cfgInputValue 回填与 tri_state
  '' 原样、siteBadge(站点/全局/null 反例)、sitePlaceholder(有显示值回 schema/tri_state '' 显全局
  继承值/全局缺失回 schema/非链原样)、canFollowGlobal(存在含 ''/缺失/反例)、followGlobal
  (确认删键+toast/取消保留/不可跟随零交互/label 入标题)、cfgResetField 删键、boolValue 回填
  (全局 true 命中/站点覆盖优先)
- test_r4_curve_editor_battery: R5#170(major) —— 曲线编辑器: _sizeMultiplier 1024 vs 1000 进制判别
  (KiB 族 vs KB 族/B 与空=1/未知前缀 null)、_parseSizeValue 空串/null/非法串/未知单位 null、
  _parseSpeedValue /s 剥壳(含空格)与空串、_buildCurveChart 几何(阶梯断点跳变精确串/末档平线到
  右缘/多档 ∞ 区宽 30% 封顶/单档全宽/非法点与零阈值剔除/乱序排序/xTicks 间隔省略而 tierLines
  不省/area 闭合与 baseY/单档无有限刻度)、cfgCurveAddPeriod 新档展开、cfgCurveRemovePeriod
  openCurves 序号搬移(删中段后移前移/删尾清键/删空收 curves 段)、cfgCurvePointSet 重建档对象
  (改阈值保速度/省参沿用现值)
- test_r4_entity_skeleton_battery: R5#171(major) —— 命名实体三骨架 + hubAddEntity 入口:
  cfgEntityAdd(新增+select 回调/空白名拒绝/同名冲突 toast 且不覆盖)、cfgEntityRename(重建对象
  保序且值随迁/同名与空白与取消拒绝/冲突拒绝)、cfgEntityRemove(确认删键+after 回调/取消保留/
  无 name 删容器本身——曲线关闭路径)、cfgTrackerRemove 非末站点删后选中回落首项、最后站点删空
  收走 trackers 段且 trackerKey 归 null、cfgRuleGroupDef normalize 补 _rules 后缀且既有后缀不
  双写、hubAddTracker 入口(prompt 透传 title/prefill/取消与空白零写树/正常喂骨架并选中)
- test_r4_cfg_flatten_battery: R5#176 —— cfgFlatten 字段树展开: 四种 item.type 全产出
  (field/section/group/subcard)+open 平铺段同级拼接、group_of 分桶(bool→父行 inline/其余→子卡)、
  hidden 单点跳过(顶层与嵌套层)、allowGrouping=false 不再二次分组、_attachGrey greyBy 只在本层
  覆写(平铺段内层 greyBy 不被外层清掉/子卡灰显引用外层同段字段)、cfgGreyed 判定(greyBy 缺省
  兜底与同段覆写两态)、cfgGroupOpen/Toggle 三态(缺省折叠/跟随 schema open/显式翻转写出 false)

加载口径: config_editor 域经 webui_helpers.bundle_file("config_editor.js") 聚合(根 + tree/form/
curve 三片段清单序, 与拆分前同一份代码); cfgLoad/cfgSetTree 依赖的 cfgNormalizeRulesDraft 在
config_rules.js(真文件并入, 与 config_normalize_parity_support 同口径); hubAddEntity 在
config_hub 域(bundle 聚合, 尾部 HUB_FIELD_COMPONENT 依赖 CE_FIELD_BASE 先行); 曲线图轴标依赖
format.js 的 _fmtLadder(单位梯数据单点, 禁另抄)。方法经 window.CONFIG_EDITOR.methods /
window.CE_FIELD_BASE.methods 取出后 Object.assign 到最小状态 vm —— 方法体之间的 this 互调与
真实例等价(与 P03/P04 电池同范式)。confirmDialog/confirmThreeDialog/promptDialog/toast/api/
location.reload/window.addEventListener 按 ui_feedback/浏览器契约给桩。无 node 静默跳过(与既有
node 电池同口径, 不引入 pytest skip)。
"""

import os

from test_webui_static_r4_node_batteries import _assert_battery, _run_probe
from webui_helpers import STATIC_ROOT, bundle_file

_EDITOR_BUNDLE = bundle_file("config_editor.js")
_HUB_BUNDLE = bundle_file("config_hub.js")
_RULES_JS = os.path.join(STATIC_ROOT, "shared", "config_rules.js")
_FORMAT_JS = os.path.join(STATIC_ROOT, "shared", "format.js")

# node v24 的 -e 对「顶层 await + require」报 ERR_AMBIGUOUS_MODULE_SYNTAX: 电池体一律包 IIFE
# (与 P04 add_torrent 电池同款包装; 同步体包进去无副作用)。收尾报告 {ok, total, failed} 逐条带断言名
_IIFE_OPEN = "(async () => {\n"
_IIFE_CLOSE = (
    'console.log(JSON.stringify({\n'
    '  ok: checks.filter((c) => c[1]).length, total: checks.length,\n'
    '  failed: checks.filter((c) => !c[1]).map((c) => c[0]),\n'
    '}));\n'
    '})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });'
)

# R5#153 修复回归: cfgLoad 选中键存在性校验(幽灵站点复活改名) --------------------------------
_NODE_CFGLOAD_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(root + tree/form/curve)
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_rules.js(cfgSetTree -> cfgNormalizeRulesDraft)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods);

const DISK = { config: { trackers: { A: { hr: { add_tag: "keep" } } }, example_rules: { r1: { enabled: "true" } } } };
const SCHEMA = { groups: [], tracker_fields: [], plugins: { condition: [], action: [] } };

function makeVm(over) {
  const vm = Object.assign({}, M, {
    cfg: {
      schema: null, tree: null, baseline: "", loading: false, saving: false, error: "", saveError: "",
      trackerKey: null, trackerQuery: "", ruleGroupKey: null, openRuleMeta: {}, openSections: {},
      openGroups: {}, openLists: {}, openCurves: {}, picker: { open: false, groupKey: "", ruleName: "", list: "" },
      chartHover: null,
    },
    hub: { view: "hub" },
    hubRestored: 0,
    apiCalls: 0,
    async api(url) {
      vm.apiCalls++;
      if (url.indexOf("schema") >= 0) return JSON.parse(JSON.stringify(SCHEMA));
      return { tree: JSON.parse(JSON.stringify(DISK)) };  // cfgLoad 读 conf.tree 信封
    },
  }, over);
  vm.hubRestore = function () { vm.hubRestored++; };
  Object.defineProperty(vm, "cfgDirty", {
    get() { return vm.cfg.tree ? JSON.stringify(vm.cfg.tree) !== vm.cfg.baseline : false; },
  });
  return vm;
}
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// (1) 幽灵键回落(R5#153 核心): 重命名 A->B 未保存点「放弃改动」=> cfgDiscard -> cfgLoad 重拉磁盘树
//   修复前 trackerKey 仍是 B(非空不重选), 右栏渲染幽灵站点, cfgSetPath 把 config.trackers.B 写回树
const vm = makeVm({
  confirms: [],
  async confirmDialog() { vm.confirms.push(1); return true; },
});
vm.cfg.trackerKey = "B";
vm.cfg.ruleGroupKey = "GONE";
await vm.cfgLoad();
ok("重拉树后幽灵站点键回落首项(A)", vm.cfg.trackerKey === "A");
ok("幽灵规则集键回落首项(example_rules)", vm.cfg.ruleGroupKey === "example_rules");
ok("幽灵回落不误报加载错误", vm.cfg.error === "" && vm.cfg.loading === false);
// 右栏按 trackerKey 渲染并编辑字段: cfgSetPath 只落选中键, 不再复活 B
vm.cfgSetPath(["config", "trackers", vm.cfg.trackerKey, "hr", "add_tag"], "t1");
const trackersNow = vm.cfg.tree.config.trackers || {};
ok("编辑字段不再写回幽灵键(trackers 只有 A)", JSON.stringify(Object.keys(trackersNow)) === JSON.stringify(["A"]));
ok("编辑落在选中站点的既有键上", trackersNow.A.hr.add_tag === "t1");

// (2) 有效键保留(校验不误伤)
const vm2 = makeVm();
vm2.cfg.trackerKey = "A";
vm2.cfg.ruleGroupKey = "example_rules";
await vm2.cfgLoad();
ok("有效站点键保留", vm2.cfg.trackerKey === "A");
ok("有效规则集键保留", vm2.cfg.ruleGroupKey === "example_rules");

// (3) 为空选首项(原缺省语义)+ 空容器回落 null
const vm3 = makeVm();
await vm3.cfgLoad();
ok("trackerKey 为空选首项", vm3.cfg.trackerKey === "A" && vm3.hubRestored === 1);
ok("ruleGroupKey 为空选首项", vm3.cfg.ruleGroupKey === "example_rules");
const vm4 = makeVm();
vm4.api = async () => ({ tree: { config: {} } });
await vm4.cfgLoad();
ok("空容器回落 null(不抛错)", vm4.cfg.trackerKey === null && vm4.cfg.ruleGroupKey === null);

// (4) cfgDiscard 三分支经真 cfgLoad 结算
const vm5 = makeVm({
  confirms: [],
  async confirmDialog() { vm5.confirms.push(1); return true; },
});
await vm5.cfgLoad();
const calls0 = vm5.apiCalls;
await vm5.cfgDiscard();  // 净树: 不弹确认直重拉
ok("净树放弃: 不弹确认仍重拉(schema+config 两请求)", vm5.confirms.length === 0 && vm5.apiCalls === calls0 + 2);
vm5.cfgSetPath(["config", "trackers", "A", "note"], "dirty");
ok("净树放弃后可造脏", vm5.cfgDirty === true);
await vm5.cfgDiscard();  // 脏 + 确认: 回磁盘树
ok("脏确认放弃: 弹一次确认", vm5.confirms.length === 1);
ok("脏确认放弃: 编辑清零回磁盘原样", vm5.cfgDirty === false && vm5.cfgRaw(["config", "trackers", "A", "note"]) === undefined);
// 幽灵键场景经 cfgDiscard 全链收口: B 键态 -> 放弃 -> 回落 A
const vm6 = makeVm({
  confirms: [],
  async confirmDialog() { return true; },
});
await vm6.cfgLoad();
vm6.cfg.trackerKey = "B";  // 模拟改名 A->B 期间树内已有 B(此处只造键态)
await vm6.cfgDiscard();
ok("放弃改动后选中键必在重拉树内(幽灵键收口)", vm6.cfg.trackerKey === "A");
const vm7 = makeVm({
  confirms: [],
  async confirmDialog() { vm7.confirms.push(1); return false; },
});
await vm7.cfgLoad();
vm7.cfgSetPath(["config", "trackers", "A", "note"], "keep");
await vm7.cfgDiscard();  // 脏 + 取消: 什么都不动
ok("脏取消放弃: 弹确认且编辑保留", vm7.confirms.length === 1 && vm7.cfgDirty === true &&
   vm7.cfgRaw(["config", "trackers", "A", "note"]) === "keep");
""" + "\n" + _IIFE_CLOSE

# R5#168(major): 数值 + 单位控件族 --------------------------------------------------------------
_NODE_UNIT_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle
const M = window.CONFIG_EDITOR.methods;
const vm = Object.assign({}, M, { cfg: { tree: { config: {} } } });
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 单位梯与开关: 三个 kind 有表, 未知 kind 回退空/假
ok("cfgHasUnit 三 kind 真", vm.cfgHasUnit("time") && vm.cfgHasUnit("size") && vm.cfgHasUnit("speed"));
ok("cfgHasUnit 未知 kind 假", vm.cfgHasUnit("str") === false && vm.cfgHasUnit("") === false);
ok("cfgUnitOptions time 梯", eq(vm.cfgUnitOptions("time"), ["S", "M", "H", "D"]));
ok("cfgUnitOptions size 梯", eq(vm.cfgUnitOptions("size"), ["B", "KiB", "MiB", "GiB", "TiB"]));
ok("cfgUnitOptions speed 梯", eq(vm.cfgUnitOptions("speed"), ["B/s", "KiB/s", "MiB/s", "GiB/s"]));
ok("cfgUnitOptions 未知 kind 空梯", eq(vm.cfgUnitOptions("str"), []));

// cfgUnitLabel: time 中文映射, 其余原样, 非字符串归一(防模板插值抛 Cannot convert)
ok("time 单位中文", vm.cfgUnitLabel("time", "S") === "秒" && vm.cfgUnitLabel("time", "M") === "分" &&
   vm.cfgUnitLabel("time", "H") === "时" && vm.cfgUnitLabel("time", "D") === "天");
ok("size/speed 原样显示", vm.cfgUnitLabel("size", "MiB") === "MiB" && vm.cfgUnitLabel("speed", "KiB/s") === "KiB/s");
ok("表外单位原样返回", vm.cfgUnitLabel("time", "X") === "X" && vm.cfgUnitLabel("str", "x") === "x");
ok("非字符串单位归一(42 -> '42')", vm.cfgUnitLabel("time", 42) === "42");

// cfgUnitParts 拆: 三 kind 命中形
ok("time '30M' 拆", eq(vm.cfgUnitParts("time", "30M"), { num: "30", unit: "M" }));
ok("size '30MiB' 拆", eq(vm.cfgUnitParts("size", "30MiB"), { num: "30", unit: "MiB" }));
ok("speed '6MiB/s' 拆(斜杠入单位)", eq(vm.cfgUnitParts("speed", "6MiB/s"), { num: "6", unit: "MiB/s" }));
ok("小数与空白 ' 1.5 D ' 拆", eq(vm.cfgUnitParts("time", " 1.5 D "), { num: "1.5", unit: "D" }));
ok("纯数字拆出空单位再回退", eq(vm.cfgUnitParts("size", "30"), { num: "30", unit: "MiB" }));
ok("纯数字带 unitDefault 优先", eq(vm.cfgUnitParts("size", "30", "GiB"), { num: "30", unit: "GiB" }));

// cfgUnitParts 回退分支: 空串 / null / undefined / 非法串 / 单位不在表内
ok("空串回退 kind 缺省(time->S)", eq(vm.cfgUnitParts("time", ""), { num: "", unit: "S" }));
ok("空串回退 kind 缺省(size->MiB)", eq(vm.cfgUnitParts("size", ""), { num: "", unit: "MiB" }));
ok("空串回退 kind 缺省(speed->KiB/s)", eq(vm.cfgUnitParts("speed", ""), { num: "", unit: "KiB/s" }));
ok("unitDefault 优先于梯回退(空值)", eq(vm.cfgUnitParts("size", "", "GiB"), { num: "", unit: "GiB" }));
ok("null 同空串", eq(vm.cfgUnitParts("time", null), { num: "", unit: "S" }));
ok("undefined 同空串且 unitDefault 生效", eq(vm.cfgUnitParts("speed", undefined, "GiB/s"), { num: "", unit: "GiB/s" }));
ok("非法串(符号)整体回退", eq(vm.cfgUnitParts("size", "abc!@#"), { num: "", unit: "MiB" }));
ok("字母尾巴数字保留单位回退", eq(vm.cfgUnitParts("time", "3x"), { num: "3", unit: "S" }));
ok("单位不在表内回退", eq(vm.cfgUnitParts("speed", "5XB"), { num: "5", unit: "KiB/s" }));
ok("单位不在表内且 unitDefault 优先", eq(vm.cfgUnitParts("speed", "5XB", "MiB/s"), { num: "5", unit: "MiB/s" }));

// 拆拼往返零漂移: 拆出的 num/unit 经 cfgSetUnit 拼回与原串一致
for (const [kind, text] of [["time", "30M"], ["size", "30MiB"], ["speed", "6MiB/s"], ["time", "1.5D"]]) {
  const p = vm.cfgUnitParts(kind, text);
  vm.cfgSetUnit(["config", "k"], p.num, p.unit);
  ok("拆拼往返零漂移: " + text, vm.cfgRaw(["config", "k"]) === text);
}

// cfgSetUnit: 空数值写空串(不产生裸单位), trim, 缺单位拼空
vm.cfgSetUnit(["config", "a"], "30", "MiB");
ok("拼回 '30MiB'", vm.cfgRaw(["config", "a"]) === "30MiB");
vm.cfgSetUnit(["config", "b"], "", "MiB");
ok("空数值写空串(不产生 'MiB' 裸值)", vm.cfgRaw(["config", "b"]) === "");
vm.cfgSetUnit(["config", "c"], undefined, "MiB");
ok("null/undefined 数值同空串", vm.cfgRaw(["config", "c"]) === "");
vm.cfgSetUnit(["config", "d"], " 30 ", "MiB");
ok("数值 trim 后拼回", vm.cfgRaw(["config", "d"]) === "30MiB");
vm.cfgSetUnit(["config", "e"], "30", undefined);
ok("缺单位拼空串(值仍可写)", vm.cfgRaw(["config", "e"]) === "30");
""" + "\n" + _IIFE_CLOSE

# R5#167(major): 未保存改动防护链 ----------------------------------------------------------------
_NODE_GUARD_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
const listeners = [];  // {t, fn, op}
global.window = {
  addEventListener: (t, fn) => listeners.push({ t: t, fn: fn, op: "add" }),
  removeEventListener: (t, fn) => listeners.push({ t: t, fn: fn, op: "remove" }),
};
const reloads = [];
global.location = { reload: () => reloads.push(1) };
const timers = [];
global.setTimeout = (fn, ms) => { timers.push({ fn: fn, ms: ms }); return timers.length; };
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_rules.js(cfgSetTree -> cfgNormalizeRulesDraft)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_RULES.methods);

const DISK = { config: { trackers: { A: {} }, example_rules: { r1: { enabled: "true" } } } };

function makeVm(over) {
  const vm = Object.assign({}, M, {
    cfg: {
      schema: null, tree: null, baseline: "", loading: false, saving: false, error: "", saveError: "",
      trackerKey: null, ruleGroupKey: null, openRuleMeta: {}, openSections: {}, openGroups: {},
      openLists: {}, openCurves: {}, picker: { open: false, groupKey: "", ruleName: "", list: "" },
      chartHover: null,
    },
    kbDirtyView: false,
    modal: { visible: false },
    hub: { view: "hub" },
    disk: DISK,
    failPut: false,
    apiCalls: [],
    async api(url, opts) {
      vm.apiCalls.push(opts ? "PUT" : "GET");
      if (opts && opts.method === "PUT" && vm.failPut) throw new Error("共 2 处配置错误");
      if (opts) return { changes: ["x"], restart_required: [] };
      return { tree: JSON.parse(JSON.stringify(vm.disk)) };
    },
    toasts: [],
    toast(msg, kind) { vm.toasts.push([msg, kind]); },
    webFlagLoads: 0,
    loadWebFlags() { vm.webFlagLoads++; },
    ttReloads: 0,
    transferTargetsReload() { vm.ttReloads++; },
    kbSaves: 0,
    async kbSaveKeys() { vm.kbSaves++; return true; },
    hubRestore() {},
  }, over);
  Object.defineProperty(vm, "cfgDirty", {
    get() { return vm.cfg.tree ? JSON.stringify(vm.cfg.tree) !== vm.cfg.baseline : false; },
  });
  return vm;
}
const evOf = (over) => Object.assign({
  code: "F5", ctrlKey: false, metaKey: false, shiftKey: false, isComposing: false, keyCode: 0,
  defaultPrevented: false, pd: false,
  preventDefault() { this.defaultPrevented = true; this.pd = true; },
}, over);
const byType = (t, op) => listeners.filter((l) => l.t === t && l.op === op);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- cfgGuardSync 挂摘幂等 ---
const vm = makeVm();
vm.cfgGuardSync(true);
ok("净树且键位净: 不挂 beforeunload(守卫只在 dirty 期存在)", byType("beforeunload", "add").length === 0);
vm.cfg.tree = { config: { a: "1" } };
vm.cfg.baseline = JSON.stringify(vm.cfg.tree);
vm.cfgSetPath(["config", "b"], "2");  // 造脏
vm.cfgGuardSync(true);
ok("脏: 挂一次 beforeunload", byType("beforeunload", "add").length === 1);
const handler = byType("beforeunload", "add")[0].fn;
vm.cfgGuardSync(true);
ok("重复 sync(true) 幂等(不叠句柄)", byType("beforeunload", "add").length === 1);
vm.cfgGuardSync(false);
ok("摘除按同一句柄", byType("beforeunload", "remove").length === 1 &&
   byType("beforeunload", "remove")[0].fn === handler);
vm.cfgGuardSync(false);
ok("重复 sync(false) 幂等(不重复注销)", byType("beforeunload", "remove").length === 1);
// 双脏源第二源: 键位草稿单独为真也挂
const vmKb = makeVm();
vmKb.kbDirtyView = true;
vmKb.cfgGuardSync(true);
ok("键位草稿单独为真也挂(双脏源)", byType("beforeunload", "add").length === 2);

// --- _cfgOnBeforeUnload ---
const vm2 = makeVm();
const evClean = evOf();
ok("净: 返回 undefined 不拦", vm2._cfgOnBeforeUnload(evClean) === undefined && evClean.pd === false);
vm2.cfg.tree = { config: {} };
vm2.cfg.baseline = "{}";
vm2.cfgSetPath(["config", "x"], "1");
const evDirty = evOf();
const ret = vm2._cfgOnBeforeUnload(evDirty);
ok("脏: preventDefault + returnValue 弹原生框", ret === "" && evDirty.pd === true && evDirty.returnValue === "");
const evDirty2 = evOf();
vm2.kbDirtyView = true;
vm2.cfg.tree = vm2.cfg.baseline;  // 树回净, 只剩键位脏
ok("键位脏单独也拦(双脏源判据)", vm2._cfgOnBeforeUnload(evDirty2) === "" && evDirty2.pd === true);

// --- _cfgOnReloadKey 四道闸 + 键位命中 ---
const vmR = makeVm({ guardCalls: 0 });
vmR.cfgReloadGuard = function () { vmR.guardCalls++; };
vmR.cfg.tree = null;  // 净
vmR._cfgOnReloadKey(evOf());
ok("闸0: 无脏不拦刷新(不 preventDefault 不弹框)", vmR.guardCalls === 0);
vmR.cfg.tree = { config: {} };
vmR.cfg.baseline = "{}";
vmR.cfgSetPath(["config", "x"], "1");
vmR._cfgOnReloadKey(evOf({ defaultPrevented: true }));
ok("闸1: 先到先得(defaultPrevented)不接管", vmR.guardCalls === 0);
vmR._cfgOnReloadKey(evOf({ isComposing: true }));
vmR._cfgOnReloadKey(evOf({ keyCode: 229 }));
ok("闸2: IME 组合期不接管", vmR.guardCalls === 0);
vmR.modal.visible = true;
vmR._cfgOnReloadKey(evOf());
ok("闸3: 已有弹窗不叠框(交原生兜底)", vmR.guardCalls === 0);
vmR.modal.visible = false;
vmR._cfgOnReloadKey(evOf({ code: "KeyA", ctrlKey: true }));
ok("闸4: 非 F5/Ctrl+R 族放行", vmR.guardCalls === 0);
const evF5 = evOf();
vmR._cfgOnReloadKey(evF5);
ok("F5: 取消默认刷新并弹自绘框", evF5.pd === true && vmR.guardCalls === 1);
vmR._cfgOnReloadKey(evOf({ code: "KeyR" }));
ok("裸 R 放行", vmR.guardCalls === 1);
const evCR = evOf({ code: "KeyR", ctrlKey: true });
vmR._cfgOnReloadKey(evCR);
ok("Ctrl+R 命中", evCR.pd === true && vmR.guardCalls === 2);
vmR._cfgOnReloadKey(evOf({ code: "KeyR", metaKey: true }));
ok("Cmd+R 命中", vmR.guardCalls === 3);
vmR._cfgOnReloadKey(evOf({ code: "KeyR", ctrlKey: true, shiftKey: true }));
ok("Ctrl+Shift+R(硬刷新)也命中", vmR.guardCalls === 4);

// --- cfgReloadGuard 三分支结算(真 cfgSave 走 api 桩) ---
// 分支1: 保存并刷新 + 保存成功 => 摘兜底 + 刷新 + 键位草稿后存
listeners.length = 0;
reloads.length = 0;
timers.length = 0;
const vm3 = makeVm({ confirmAnswer: true });
vm3.confirmThreeDialog = async () => true;
vm3.cfg.tree = { config: { a: "1" } };
vm3.cfg.baseline = JSON.stringify(vm3.cfg.tree);
vm3.cfgSetPath(["config", "b"], "2");
vm3.kbDirtyView = true;
vm3.cfgGuardSync(true);  // 真实时序: 脏期兜底在册(watcher 挂), 出框才摘
const armedOk = byType("beforeunload", "add")[0].fn;
await vm3.cfgReloadGuard();
ok("保存成功分支: 恰好刷新一次", reloads.length === 1);
ok("保存成功分支: PUT+重拉 GET 两次请求", vm3.apiCalls.join(",") === "PUT,GET");
ok("保存成功分支: 键位草稿后存(双脏源第二源)", vm3.kbSaves === 1);
ok("保存成功分支: ok toast + 成功后立即刷功能旗标", vm3.webFlagLoads === 1 && vm3.ttReloads === 1 &&
   vm3.toasts.some((t) => t[1] === "ok"));
ok("保存成功分支: 延时补拉已排程(2s)", timers.some((t) => t.ms === 2000));
ok("保存成功分支: 守卫已摘除(同句柄注销)", vm3._cfgGuardOn === false &&
   byType("beforeunload", "remove").length === 1 && byType("beforeunload", "remove")[0].fn === armedOk);
ok("保存成功分支: saving 复位且 saveError 空", vm3.cfg.saving === false && vm3.cfg.saveError === "");

// 分支2: 保存并刷新 + 保存失败 => 不刷新不摘兜底(改动还在, 留页看报错)
listeners.length = 0;
reloads.length = 0;
const vm4 = makeVm({ failPut: true });
vm4.confirmThreeDialog = async () => true;
vm4.cfg.tree = { config: { a: "1" } };
vm4.cfg.baseline = JSON.stringify(vm4.cfg.tree);
vm4.cfgSetPath(["config", "b"], "2");
vm4.cfgGuardSync(true);  // 脏期兜底在册
await vm4.cfgReloadGuard();
ok("保存失败分支: 不刷新(绝不能带着改动刷新)", reloads.length === 0);
ok("保存失败分支: 兜底未摘(仍拦刷新)", vm4._cfgGuardOn === true && byType("beforeunload", "remove").length === 0);
ok("保存失败分支: saveError 原文落账 + error toast", vm4.cfg.saveError.indexOf("配置错误") >= 0 &&
   vm4.toasts.some((t) => t[1] === "error"));
ok("保存失败分支: saving 复位", vm4.cfg.saving === false);
ok("保存失败分支: 未重拉树", vm4.apiCalls.join(",") === "PUT");

// 分支3: 放弃改动并刷新 => 摘兜底 + 刷新, 不存键位草稿(只在内存, 刷新自然清零)
listeners.length = 0;
reloads.length = 0;
const vm5 = makeVm();
vm5.confirmThreeDialog = async () => "extra";
vm5.cfg.tree = { config: { a: "1" } };
vm5.cfg.baseline = JSON.stringify(vm5.cfg.tree);
vm5.cfgSetPath(["config", "b"], "2");
vm5.kbDirtyView = true;
vm5.cfgGuardSync(true);
await vm5.cfgReloadGuard();
ok("放弃分支: 刷新一次且零请求(不保存)", reloads.length === 1 && vm5.apiCalls.length === 0);
ok("放弃分支: 键位草稿不显式回滚", vm5.kbSaves === 0);
ok("放弃分支: 守卫已摘除", vm5._cfgGuardOn === false && byType("beforeunload", "remove").length === 1);

// 分支4: 留在此页 => 零动作(已挂兜底保持原样)
listeners.length = 0;
reloads.length = 0;
const vm6 = makeVm();
vm6.confirmThreeDialog = async () => false;
vm6.cfg.tree = { config: { a: "1" } };
vm6.cfg.baseline = JSON.stringify(vm6.cfg.tree);
vm6.cfgSetPath(["config", "b"], "2");
vm6.cfgGuardSync(true);
await vm6.cfgReloadGuard();
ok("留页分支: 不刷新不保存不摘兜底", reloads.length === 0 && vm6.apiCalls.length === 0 && vm6.kbSaves === 0 &&
   vm6._cfgGuardOn === true && byType("beforeunload", "remove").length === 0);

// --- cfgDiscard 已在 cfgLoad 电池覆盖三分支, 这里补守卫联动: 放弃后守卫随脏消失 ---
listeners.length = 0;
const vm7 = makeVm({
  confirms: [],
  async confirmDialog() { return true; },
});
vm7.cfg.tree = { config: {} };
vm7.cfg.baseline = "{}";
vm7.cfgSetPath(["config", "x"], "1");
vm7.cfgGuardSync(true);
ok("脏期兜底在册", byType("beforeunload", "add").length === 1);
await vm7.cfgDiscard();
vm7.cfgGuardSync(false);
ok("放弃后树回净: 摘除路径可用(挂摘配对不抛错)", byType("beforeunload", "remove").length === 1);
""" + "\n" + _IIFE_CLOSE

# R5#169(major): 站点回退链整族 ------------------------------------------------------------------
_NODE_FALLBACK_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(CE_FIELD_BASE 亦在此)
const M = window.CONFIG_EDITOR.methods;
const FM = window.CE_FIELD_BASE.methods;

const TREE = { config: {
  hr: { add_tag: "GLB", add_category: "GCAT", overwrite_category: "GOVR", overwrite_category_for_satisfied: "true" },
  remove_similar_tags: ["g1"],
  whatever: "W",
  trackers: {
    S1: { hr: { add_tag: "S1V", overwrite_category: "", add_category_for_satisfied: "" } },
  },
} };
const vm = Object.assign({}, M, { cfg: { tree: JSON.parse(JSON.stringify(TREE)) } });
vm.toasts = [];
vm.toast = (msg, kind) => vm.toasts.push([msg, kind]);  // followGlobal 删键后的回执(根实例方法)
const SITE = ["config", "trackers", "S1"];
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// cfgSiteFallbackPath: 路径形态判据
ok("链上键(hr 中间段)映射", eq(vm.cfgSiteFallbackPath([...SITE, "hr", "add_tag"]), ["config", "hr", "add_tag"]));
ok("链上键(mid=[] 顶层)映射", eq(vm.cfgSiteFallbackPath([...SITE, "remove_similar_tags"]), ["config", "remove_similar_tags"]));
ok("链上键(hr 直挂)映射", eq(vm.cfgSiteFallbackPath([...SITE, "add_category"]), ["config", "hr", "add_category"]));
ok("全局页同名字段不命中", vm.cfgSiteFallbackPath(["config", "hr", "add_tag"]) === null);
ok("链外键不命中", vm.cfgSiteFallbackPath([...SITE, "whatever"]) === null);
ok("短路径(<4)不命中", vm.cfgSiteFallbackPath(["config", "trackers", "S1"]) === null);
ok("非数组不命中", vm.cfgSiteFallbackPath("config.trackers.S1.hr.add_tag") === null);
ok("非 config 根不命中", vm.cfgSiteFallbackPath(["other", "trackers", "S1", "hr", "add_tag"]) === null);

// cfgFallbackValue: 站点值缺失时的回填链(全局 -> schema 默认)
ok("回填: 全局值命中", vm.cfgFallbackValue([...SITE, "hr", "add_category"], "DEF") === "GCAT");
ok("回填: 全局缺失走 schema 默认", vm.cfgFallbackValue([...SITE, "hr", "add_category_for_satisfied"], "DEF") === "DEF");
ok("回填: 全局顶层键命中", eq(vm.cfgFallbackValue([...SITE, "remove_similar_tags"], "DEF"), ["g1"]));
ok("反例: 链外键即使全局同名也回 schema 默认", vm.cfgFallbackValue([...SITE, "whatever"], "DEF") === "DEF");
ok("反例: 全局页路径回 schema 默认", vm.cfgFallbackValue(["config", "hr", "add_tag"], "DEF") === "DEF");

// cfgInputValue 回填 + tri_state '' 原样(站点显式空是覆盖, 不落回退)
ok("回填经 cfgInputValue 生效", vm.cfgInputValue({ default: "" }, [...SITE, "hr", "add_category"]) === "GCAT");
ok("站点值优先于回填", vm.cfgInputValue({ default: "" }, [...SITE, "hr", "add_tag"]) === "S1V");
ok("tri_state '' 原样返回(不落全局)", vm.cfgInputValue({ default: "" }, [...SITE, "hr", "overwrite_category"]) === "");

// CE_FIELD_BASE 行组件三件套(siteBadge/sitePlaceholder/canFollowGlobal/followGlobal)
const fieldVm = (f, path) => Object.assign({}, FM, { ce: vm, f: f, path: path });
ok("徽标: 站点键存在标站点", fieldVm({}, [...SITE, "hr", "add_tag"]).siteBadge() === "站点");
ok("徽标: tri_state '' 也是站点覆盖", fieldVm({}, [...SITE, "hr", "overwrite_category"]).siteBadge() === "站点");
ok("徽标: 键缺失标全局", fieldVm({}, [...SITE, "hr", "add_category"]).siteBadge() === "全局");
ok("徽标: 链外键不打徽标", fieldVm({}, [...SITE, "whatever"]).siteBadge() === null);
ok("徽标: 全局页不打徽标", fieldVm({}, ["config", "hr", "add_tag"]).siteBadge() === null);

const fPh = { label: "标签", placeholder: "PH", default: "" };
ok("占位: 有显示值回 schema 占位", fieldVm(fPh, [...SITE, "hr", "add_tag"]).sitePlaceholder() === "PH");
ok("占位: tri_state '' 显全局继承值", fieldVm(fPh, [...SITE, "hr", "overwrite_category"]).sitePlaceholder() === "GOVR");
ok("占位: tri_state '' 且全局缺失回 schema 占位",
   fieldVm(fPh, [...SITE, "hr", "add_category_for_satisfied"]).sitePlaceholder() === "PH");
ok("占位: 非链键原样", fieldVm(fPh, [...SITE, "whatever"]).sitePlaceholder() === "PH");

ok("跟随全局: 站点键存在可见", fieldVm({}, [...SITE, "hr", "add_tag"]).canFollowGlobal() === true);
ok("跟随全局: tri_state '' 可见", fieldVm({}, [...SITE, "hr", "overwrite_category"]).canFollowGlobal() === true);
ok("跟随全局: 键缺失不可见(本就跟随)", fieldVm({}, [...SITE, "hr", "add_category"]).canFollowGlobal() === false);
ok("跟随全局: 全局页不可见", fieldVm({}, ["config", "hr", "add_tag"]).canFollowGlobal() === false);

// followGlobal: 确认删键 + toast; 取消保留; 不可跟随零交互
const fFg = { label: "添加标签" };
const vmFg = fieldVm(fFg, [...SITE, "hr", "add_tag"]);
vmFg.ce.confirms = [];
vmFg.ce.toasts = [];
vmFg.ce.confirmDialog = async (title, body, opts) => { vmFg.ce.confirms.push([title, opts && opts.okText]); return false; };
await vmFg.followGlobal();
ok("跟随全局: 取消则键保留零 toast", vm.cfgRaw([...SITE, "hr", "add_tag"]) === "S1V" && vmFg.ce.toasts.length === 0);
vmFg.ce.confirmDialog = async (title, body, opts) => { vmFg.ce.confirms.push([title, opts && opts.okText]); return true; };
await vmFg.followGlobal();
ok("跟随全局: 确认后删站点覆盖键", vm.cfgExists([...SITE, "hr", "add_tag"]) === false);
ok("跟随全局: 确认框带字段名与跟随文案", vmFg.ce.confirms[1][0].indexOf("添加标签") >= 0 && vmFg.ce.confirms[1][1] === "跟随全局");
ok("跟随全局: 删后 toast 提醒保存生效", vmFg.ce.toasts.length === 1 && vmFg.ce.toasts[0][1] === "ok");
const vmFgLabel = fieldVm(fFg, [...SITE, "hr", "overwrite_category"]);
vmFgLabel.ce.confirmDialog = async (title) => { vmFgLabel.ce.confirms.push([title, ""]); return true; };
await vmFgLabel.followGlobal(null, "自定义名");  // 签名 (path, label): 省 path 用本行, label 入标题
ok("跟随全局: label 参数入标题", vmFgLabel.ce.confirms[vmFgLabel.ce.confirms.length - 1][0].indexOf("自定义名") >= 0);
const vmFgNo = fieldVm(fFg, ["config", "hr", "add_tag"]);
vmFgNo.ce.confirmDialog = async () => { throw new Error("不可跟随不应弹框"); };
await vmFgNo.followGlobal();
ok("跟随全局: 全局页零交互", vm.cfgRaw(["config", "hr", "add_tag"]) === "GLB");

// cfgResetField: 删键单点(缺失键 no-op, 兄弟键不动)
vm.cfgResetField([...SITE, "hr", "add_category"]);
ok("cfgResetField 删既有键", vm.cfgExists([...SITE, "hr", "add_category"]) === false);
vm.cfgResetField([...SITE, "hr", "nonexistent"]);
ok("cfgResetField 缺失键 no-op 不抛错", vm.cfgExists([...SITE, "hr", "add_tag"]) === false &&
   vm.cfgRaw(["config", "hr", "add_category"]) === "GCAT");

// boolValue 回填(CE_FIELD_BASE computed 真算)
const fBool = { label: "b", kind: "bool", default: "false" };
ok("bool 回填: 站点缺失按全局生效值", FM.boolValue.call(fieldVm(fBool, [...SITE, "hr", "overwrite_category_for_satisfied"])) === true);
ok("bool 站点覆盖优先于回填", FM.boolValue.call(fieldVm(fBool, [...SITE, "hr", "add_tag"])) === false);
""" + "\n" + _IIFE_CLOSE

# R5#170(major): 曲线编辑器 ----------------------------------------------------------------------
_NODE_CURVE_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle
eval(fs.readFileSync(process.argv[2], "utf8"));  // format.js(_fmtBytes/_fmtSpeed 的单位梯单点)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.AQB_FORMAT.methods);

const GiB = 1024 * 1024 * 1024;
const MiB = 1024 * 1024;
const mkTree = (curves) => ({ config: { global_speed_limit_curve: { curves: curves } } });
function makeVm(curves) {
  return Object.assign({}, M, { cfg: { tree: mkTree(curves), openCurves: {}, chartHover: null } });
}
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// _sizeMultiplier: 1024 vs 1000 进制判别
ok("KiB=1024 进制", M._sizeMultiplier("KiB") === 1024);
ok("MiB=1024^2", M._sizeMultiplier("MiB") === 1024 * 1024);
ok("GiB=1024^3", M._sizeMultiplier("GiB") === GiB);
ok("TiB=1024^4", M._sizeMultiplier("TiB") === 1024 * 1024 * 1024 * 1024);
ok("KB=1000 进制(无 i)", M._sizeMultiplier("KB") === 1000);
ok("MB=1000^2", M._sizeMultiplier("MB") === 1000 * 1000);
ok("Gb=1000^3(大小写只看 i)", M._sizeMultiplier("Gb") === 1000 * 1000 * 1000);
ok("kiB 小写前缀也判 1024", M._sizeMultiplier("kiB") === 1024);
ok("B/空/b = 1", M._sizeMultiplier("B") === 1 && M._sizeMultiplier("") === 1 && M._sizeMultiplier("b") === 1);
ok("未知前缀 null", M._sizeMultiplier("XB") === null && M._sizeMultiplier("XiB") === null);

// _parseSizeValue: 空串/非法/未知单位 null, 合法换算
ok("size: 空串 null", M._parseSizeValue("") === null);
ok("size: null/undefined null", M._parseSizeValue(null) === null && M._parseSizeValue(undefined) === null);
ok("size: 纯字母 null", M._parseSizeValue("abc") === null);
ok("size: 未知单位 null", M._parseSizeValue("10XB") === null);
ok("size: 无单位 = 字节数", M._parseSizeValue("10") === 10);
ok("size: 10GiB 换算", M._parseSizeValue("10GiB") === 10 * GiB);
ok("size: 2.5MiB 小数换算", M._parseSizeValue("2.5MiB") === 2.5 * MiB);
ok("size: '10 KB' 1000 进制带空格", M._parseSizeValue("10 KB") === 10 * 1000);

// _parseSpeedValue: /s 剥壳
ok("speed: 空串 null", M._parseSpeedValue("") === null);
ok("speed: 6MiB/s 剥壳换算", M._parseSpeedValue("6MiB/s") === 6 * MiB);
ok("speed: '6 MiB / s' 空格剥壳", M._parseSpeedValue("6 MiB / s") === 6 * MiB);
ok("speed: 缺 /s 按字节解析", M._parseSpeedValue("6MiB") === 6 * MiB);
ok("speed: 非法值 null", M._parseSpeedValue("xx/s") === null);

// _buildCurveChart: 两档阶梯几何(精确串)
const vm = makeVm([
  { curve: { upload_curve: [
    { "100GiB": { upload_speed_limit: "10MiB/s" } },
    { "10GiB": { upload_speed_limit: "5MiB/s" } },
  ] } },
]);
const c = vm._buildCurveChart(0, "upload_curve");
ok("两档图产出", !!c && c.points.length === 2);
ok("阶梯线精确串(断点跳变 + 末档平线到右缘)",
   c.line === "M 58.0 96.0 L 399.6 96.0 L 399.6 12.0 L 546.0 12.0");
ok("面积闭合到底边", c.area === c.line + " L 546.0 180.0 L 58.0 180.0 Z" && c.baseY === 180);
ok("多档 ∞ 区宽 = 图体 30% 封顶", Math.abs(c.W_inf - 488 * 0.3) < 1e-9 && c.W_inf <= 488 * 0.3 + 1e-9);
ok("有限区 = 图体 - ∞ 区", Math.abs(c.W_finite - (488 - 146.4)) < 1e-9);
ok("span = 末档下限(排序后 10GiB)", c.span === 10 * GiB);
ok("xTicks: 0 / 断点 / 右缘 ∞", c.xTicks.length === 3 && c.xTicks[0].label === "0" &&
   c.xTicks[1].label === "10.0 GiB" && c.xTicks[2].label === "∞" && c.xTicks[2].pos === 546);
ok("yTicks: 5 等距档(顶=最大限速)", c.yTicks.length === 5 && c.yTicks[0].label === "0 B/s" &&
   c.yTicks[4].label === "10.0 MiB/s");
ok("tierLines 只画真变档断点", c.tierLines.length === 1 && Math.abs(c.tierLines[0].x - 399.6) < 1e-9);
ok("note 带档数与纵轴上限", c.note === "2 档 · 纵轴上限 10.0 MiB/s");

// 单档: ∞ 区独占全宽, 无有限刻度与 tierLines
const c1 = makeVm([{ curve: { upload_curve: [{ "5GiB": { upload_speed_limit: "3MiB/s" } }] } }]);
const g1 = c1._buildCurveChart(0, "upload_curve");
ok("单档 ∞ 区全宽", g1.W_inf === 488 && g1.span === 0);
ok("单档线 = 平线到底", g1.line === "M 58.0 12.0 L 546.0 12.0");
ok("单档无有限刻度与参考线", g1.xTicks.length === 2 && g1.xTicks[1].label === "∞" && g1.tierLines.length === 0);

// 非法点剔除(阈值/限速不可解析、零阈值)——解析失败不阻断, 只剩合法档
const c2 = makeVm([{ curve: { upload_curve: [
  { "abc": { upload_speed_limit: "5MiB/s" } },
  { "10GiB": { upload_speed_limit: "xx" } },
  { "0B": { upload_speed_limit: "1MiB/s" } },
  { "10GiB": { upload_speed_limit: "5MiB/s" } },
] } }]);
const g2 = c2._buildCurveChart(0, "upload_curve");
ok("非法点全部剔除只留合法档", !!g2 && g2.points.length === 1 && g2.note === "1 档 · 纵轴上限 5.0 MiB/s");

// 刻度间隔省略: 相邻断点像素距 < 46 时 xTick 省略, tierLines 不省
const c3 = makeVm([{ curve: { upload_curve: [
  { "10GiB": { upload_speed_limit: "5MiB/s" } },
  { "11GiB": { upload_speed_limit: "6MiB/s" } },
  { "100GiB": { upload_speed_limit: "10MiB/s" } },
] } }]);
const g3 = c3._buildCurveChart(0, "upload_curve");
ok("3 档产出且过近刻度省略", g3.points.length === 3 &&
   JSON.stringify(g3.xTicks.map((t) => t.label)) === JSON.stringify(["0", "10.0 GiB", "∞"]));
ok("刻度省略时参考线不省", g3.tierLines.length === 2);

// 全解析失败 => null(不画图)
const c4 = makeVm([{ curve: { upload_curve: [{ "abc": { upload_speed_limit: "xx" } }] } }]);
ok("全解析失败返回 null", c4._buildCurveChart(0, "upload_curve") === null);

// cfgCurveAddPeriod: 追加 + 新档顺手展开
const vmA = makeVm([{ curve: { period: "1D" } }]);
vmA.cfg.openCurves = { 0: true };
vmA.cfgCurveAddPeriod();
const list = vmA.cfgCurveList();
ok("加档: 追加 {curve:{period:'1D'}}", list.length === 2 && JSON.stringify(list[1]) === JSON.stringify({ curve: { period: "1D" } }));
ok("加档: 新档展开既有展开保留", vmA.cfg.openCurves[0] === true && vmA.cfg.openCurves[1] === true);

// cfgCurveRemovePeriod: openCurves 序号搬移
const vmR = makeVm([
  { curve: { period: "1D" } }, { curve: { period: "2D" } }, { curve: { period: "3D" } },
]);
vmR.cfg.openCurves = { 0: true, 1: true, 2: true };
vmR.cfgCurveRemovePeriod(1);
ok("删中档: 列表收窄且后续序号前移", vmR.cfgCurveList().length === 2 &&
   vmR.cfgCurveList()[1].curve.period === "3D");
ok("删中档: 展开态搬移(0 留 2->1, 被删 1 清)", vmR.cfg.openCurves[0] === true &&
   vmR.cfg.openCurves[1] === true && vmR.cfg.openCurves[2] === undefined);
vmR.cfg.openCurves = { 1: true };
vmR.cfgCurveRemovePeriod(0);
ok("删首档: 后续展开态前移到 0", vmR.cfg.openCurves[0] === true && vmR.cfg.openCurves[1] === undefined);
const vmR2 = makeVm([{ curve: { period: "1D" } }]);
vmR2.cfg.openCurves = { 0: true };
vmR2.cfgCurveRemovePeriod(0);
ok("删空: curves 段收走且展开态清空", vmR2.cfgExists(["config", "global_speed_limit_curve", "curves"]) === false &&
   JSON.stringify(vmR2.cfg.openCurves) === "{}");

// cfgCurvePointSet: 重建档对象(改阈值保速度/省参沿用现值)
const vmP = makeVm([{ curve: { download_curve: [
  { "5GiB": { download_speed_limit: "1MiB/s" } },
  { "9GiB": { download_speed_limit: "2MiB/s" } },
] } }]);
vmP.cfgCurvePointSet(0, "download_curve", 0, "7GiB", "3MiB/s");
ok("改档: 阈值与限速都换", JSON.stringify(vmP.cfgCurvePoints(0, "download_curve")[0]) ===
   JSON.stringify({ "7GiB": { download_speed_limit: "3MiB/s" } }));
ok("改档: 兄弟档不动", JSON.stringify(vmP.cfgCurvePoints(0, "download_curve")[1]) ===
   JSON.stringify({ "9GiB": { download_speed_limit: "2MiB/s" } }));
vmP.cfgCurvePointSet(0, "download_curve", 0, undefined, "9MiB/s");
ok("省参沿用现阈值只换限速", JSON.stringify(vmP.cfgCurvePoints(0, "download_curve")[0]) ===
   JSON.stringify({ "7GiB": { download_speed_limit: "9MiB/s" } }));
vmP.cfgCurvePointSet(0, "download_curve", 0);
ok("全省参 = 原值重建(幂等)", JSON.stringify(vmP.cfgCurvePoints(0, "download_curve")[0]) ===
   JSON.stringify({ "7GiB": { download_speed_limit: "9MiB/s" } }));
""" + "\n" + _IIFE_CLOSE

# R5#171(major): 命名实体三骨架 + hubAddEntity 入口 ----------------------------------------------
_NODE_ENTITY_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(CE_FIELD_BASE 先行)
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_hub bundle(hubAddEntity 入口)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_HUB.methods);

function makeVm(tree, over) {
  const vm = Object.assign({}, M, {
    cfg: {
      tree: tree, baseline: "", schema: null, trackerKey: null, ruleGroupKey: null, trackerQuery: "",
      openRuleMeta: {}, openSections: {}, openGroups: {}, openLists: {}, openCurves: {},
      picker: { open: false, groupKey: "", ruleName: "", list: "" }, chartHover: null,
      loading: false, saving: false, error: "", saveError: "",
    },
    hub: { view: "hub" },
    toasts: [],
    toast(msg, kind) { vm.toasts.push([msg, kind]); },
    confirms: [],
    async confirmDialog(title, body, opts) { vm.confirms.push([title, opts && opts.okText]); return vm.confirmAnswer !== false; },
    prompts: [],
    async promptDialog(title, value, opts) { vm.prompts.push([title, value, opts]); return vm.promptAnswer; },
  }, over);
  return vm;
}
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const keysOf = (vm, path) => Object.keys(vm.cfgRaw(path) || {});

// --- cfgEntityAdd ---
const vm1 = makeVm({ config: { trackers: {} } });
const sel1 = [];
ok("新增: 成功返回真", vm1.cfgEntityAdd({ path: ["config", "trackers"], name: "  NewSite  ", label: "站点",
  initial: { tags: [] }, select: (n, o) => sel1.push([n, o]) }) === true);
ok("新增: 键 trim 后写树带初值", JSON.stringify(vm1.cfgRaw(["config", "trackers", "NewSite"])) === JSON.stringify({ tags: [] }));
ok("新增: select 回调(新名, null)", JSON.stringify(sel1) === JSON.stringify([["NewSite", null]]));
ok("新增: 空白名拒绝", vm1.cfgEntityAdd({ path: ["config", "trackers"], name: "   ", label: "站点" }) === false &&
   keysOf(vm1, ["config", "trackers"]).join(",") === "NewSite");
vm1.cfgRaw(["config", "trackers", "NewSite"]).marker = 1;
vm1.toasts = [];
ok("新增: 同名冲突拒绝且不覆盖", vm1.cfgEntityAdd({ path: ["config", "trackers"], name: "NewSite", label: "站点",
  initial: {} }) === false && vm1.cfgRaw(["config", "trackers", "NewSite"]).marker === 1 &&
   vm1.toasts.length === 1 && vm1.toasts[0][1] === "error" && vm1.toasts[0][0].indexOf("名称冲突") >= 0);

// --- cfgEntityRename: 重建对象保序 ---
const vm2 = makeVm({ config: { trackers: { A: { v: "1" }, C: { v: "2" } } }, });
vm2.cfg.trackerKey = "A";
vm2.promptAnswer = " B ";
ok("重命名: 成功返回真", await vm2.cfgTrackerRename("A") === true);
ok("重命名: 重建对象保序(B 占原 A 位)", JSON.stringify(keysOf(vm2, ["config", "trackers"])) === JSON.stringify(["B", "C"]));
ok("重命名: 值随迁", JSON.stringify(vm2.cfgRaw(["config", "trackers", "B"])) === JSON.stringify({ v: "1" }));
ok("重命名: 选中键同步到新名", vm2.cfg.trackerKey === "B");
vm2.promptAnswer = "B";
ok("重命名: 同名拒绝(无变化)", await vm2.cfgTrackerRename("B") === false &&
   JSON.stringify(keysOf(vm2, ["config", "trackers"])) === JSON.stringify(["B", "C"]));
vm2.promptAnswer = "   ";
ok("重命名: 空白名拒绝", await vm2.cfgTrackerRename("B") === false);
vm2.promptAnswer = null;
ok("重命名: 取消拒绝", await vm2.cfgTrackerRename("B") === false);
vm2.promptAnswer = "C";
vm2.toasts = [];
ok("重命名: 冲突拒绝 + toast", await vm2.cfgTrackerRename("B") === false &&
   keysOf(vm2, ["config", "trackers"]).join(",") === "B,C" &&
   vm2.toasts.some((t) => t[0].indexOf("名称冲突") >= 0));
// 规则重命名同骨架: 保序
const vm2r = makeVm({ config: { mygroup_rules: { r1: { enabled: "true" }, r0: { enabled: "false" } } } });
vm2r.promptAnswer = "r2";
ok("规则重命名: 同骨架保序", await vm2r.cfgRuleRename("mygroup_rules", "r1") === true &&
   JSON.stringify(keysOf(vm2r, ["config", "mygroup_rules"])) === JSON.stringify(["r2", "r0"]));

// --- cfgEntityRemove ---
const vm3 = makeVm({ config: { trackers: { A: {}, B: {}, C: {} } } });
vm3.cfg.trackerKey = "C";
vm3.confirmAnswer = true;
ok("删除站点: 成功返回真", await vm3.cfgTrackerRemove("C") === true);
ok("删除站点: 键移除且选中回落剩余首项", keysOf(vm3, ["config", "trackers"]).join(",") === "A,B" &&
   vm3.cfg.trackerKey === "A");
vm3.confirmAnswer = false;
ok("删除站点: 取消保留", await vm3.cfgTrackerRemove("B") === false &&
   keysOf(vm3, ["config", "trackers"]).join(",") === "A,B" && vm3.cfg.trackerKey === "A");
vm3.confirmAnswer = true;
await vm3.cfgTrackerRemove("B");
await vm3.cfgTrackerRemove("A");
ok("最后站点删空: trackers 段收走", vm3.cfgExists(["config", "trackers"]) === false);
ok("最后站点删空: 选中键归 null", vm3.cfg.trackerKey === null);
// 无 name 变体: 对容器本身动手(限速曲线关闭路径)
const vm3b = makeVm({ config: { global_speed_limit_curve: { curves: [] } } });
vm3b.confirmAnswer = true;
ok("无 name 删除: 整段移除", await vm3b.cfgEntityRemove({ path: ["config", "global_speed_limit_curve"],
  title: "t", body: "b", okText: "关闭并移除" }) === true &&
   vm3b.cfgExists(["config", "global_speed_limit_curve"]) === false);
const vm3c = makeVm({ config: { global_speed_limit_curve: { curves: [] } } });
vm3c.confirmAnswer = false;
await vm3c.cfgEntityRemove({ path: ["config", "global_speed_limit_curve"], title: "t", body: "b" });
ok("无 name 删除: 取消保留整段", vm3c.cfgExists(["config", "global_speed_limit_curve"]) === true);

// --- _rules 后缀 normalize(补后缀; 既有后缀不双写) ---
const vm4 = makeVm({ config: {} });
ok("规则集新增: 补 _rules 后缀", vm4.cfgEntityAdd({ ...vm4.cfgRuleGroupDef(""), name: "mygroup" }) === true &&
   vm4.cfgExists(["config", "mygroup_rules"]) === true && vm4.cfg.ruleGroupKey === "mygroup_rules");
ok("规则集新增: 既有后缀不双写", vm4.cfgEntityAdd({ ...vm4.cfgRuleGroupDef(""), name: "other_rules" }) === true &&
   vm4.cfgExists(["config", "other_rules"]) === true && !vm4.cfgExists(["config", "other_rules_rules"]));
vm4.toasts = [];
ok("规则集新增: 规范名冲突也拒绝", vm4.cfgEntityAdd({ ...vm4.cfgRuleGroupDef(""), name: "mygroup" }) === false &&
   vm4.toasts.length === 1);
// 删除规则集: after 回落首项
const vm4r = makeVm({ config: { a_rules: {}, b_rules: {} } });
vm4r.cfg.ruleGroupKey = "b_rules";
vm4r.confirmAnswer = true;
await vm4r.cfgRuleRemoveGroup("b_rules");
ok("规则集删除: 选中回落剩余首项", keysOf(vm4r, ["config"]).indexOf("b_rules") < 0 && vm4r.cfg.ruleGroupKey === "a_rules");

// --- hubAddEntity 入口(命名交互单点, cfgEntityAdd 只收骨架) ---
const vm5 = makeVm({ config: { trackers: {} } });
vm5.promptAnswer = "NewB";
await vm5.hubAddTracker("pref");
ok("入口: prompt 带标题与预填词", vm5.prompts.length === 1 && vm5.prompts[0][0] === "新增站点配置" &&
   vm5.prompts[0][1] === "pref");
ok("入口: 正常喂骨架并选中", vm5.cfgExists(["config", "trackers", "NewB"]) === true && vm5.cfg.trackerKey === "NewB");
vm5.promptAnswer = null;
await vm5.hubAddTracker();
ok("入口: 取消零写树", keysOf(vm5, ["config", "trackers"]).join(",") === "NewB");
vm5.promptAnswer = "   ";
await vm5.hubAddTracker();
ok("入口: 空白名零写树", keysOf(vm5, ["config", "trackers"]).join(",") === "NewB");
vm5.promptAnswer = "NewB";
vm5.toasts = [];
await vm5.hubAddTracker();
ok("入口: 重复名经骨架查重拒绝", vm5.toasts.some((t) => t[0].indexOf("名称冲突") >= 0));
""" + "\n" + _IIFE_CLOSE

# R5#176: cfgFlatten 字段树展开 ------------------------------------------------------------------
_NODE_FLATTEN_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_hub bundle(cfgPathKey -> hubKey 单点)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_HUB.methods);

const FLAT_FIELDS = [
  { key: "flat_in", kind: "str", grey_if: ["flat_dep", "true"] },
  { key: "flat_dep", label: "Dep", kind: "bool", default: "true" },
];
const F = [
  { key: "plain", label: "Plain", kind: "str", default: "" },
  { key: "sec", label: "Sec", kind: "object", optional: true, fields: [{ key: "sec_in", kind: "str" }] },
  { key: "grp", label: "Grp", kind: "object", fields: [
    { key: "grp_in", kind: "str" },
    { key: "grp_hid", kind: "str", hidden: true },
  ] },
  { key: "grp2", label: "Grp2", kind: "object", fields: [{ key: "g2", kind: "str" }] },
  { key: "flat", label: "Flat", kind: "object", open: true, fields: FLAT_FIELDS },
  { key: "owner", label: "Owner", kind: "str" },
  { key: "inline_bool", label: "InlineBool", kind: "bool", group_of: "owner" },
  { key: "sub_card", label: "SubCard", kind: "str", group_of: "owner", grey_if: ["plain", "x"] },
  { key: "loner", label: "Loner", kind: "str", grey_if: ["nope", "1"] },
  { key: "hid", label: "Hid", kind: "str", hidden: true },
];
function makeVm(tree) {
  return Object.assign({}, M, {
    cfg: { tree: tree, openSections: {}, openGroups: {}, openLists: {}, openCurves: {}, openRuleMeta: {},
           picker: { open: false, groupKey: "", ruleName: "", list: "" }, chartHover: null,
           schema: null, baseline: "", trackerKey: null, ruleGroupKey: null },
  });
}
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const BASE = ["config", "basic"];

const vm = makeVm({ config: { basic: { flat: { flat_dep: "0" }, plain: "y" } } });
const items = vm.cfgFlatten(F, BASE, 0);

// 四种 item.type 全产出 + open 平铺段同级拼接
const types = [...new Set(items.map((it) => it.type))];
ok("四种 item.type 全产出", ["field", "section", "group", "subcard"].every((t) => types.includes(t)));
ok("open 平铺段不渲染折叠头(无 flat 容器项)", !items.some((it) => it.field && it.field.key === "flat"));
const hasKey = (list, key) => list.some((it) => (it.field && it.field.key === key) || (it.items && hasKey(it.items, key)));
ok("hidden 字段单点跳过(顶层)", !items.some((it) => it.field && it.field.key === "hid"));
ok("hidden 字段单点跳过(嵌套层)", !hasKey(items, "grp_hid") && !hasKey(items, "hid"));

// 顺序与结构
ok("顺序: plain/section/group/group2/平铺两子项拼入/owner/subcard/loner",
   JSON.stringify(items.map((it) => (it.field && it.field.key) || it.type)) ===
   JSON.stringify(["plain", "sec", "grp", "grp2", "flat_in", "flat_dep", "owner", "subcard", "loner"]));
const sec = items[1];
ok("section: 缩进一级子项", sec.depth === 0 && sec.items.length === 1 &&
   sec.items[0].depth === 1 && sec.items[0].field.key === "sec_in");
ok("group: 色条序循环", items[2].colorIndex === 0 && items[3].colorIndex === 1);
ok("平铺段子项与外层同级深度", items[4].depth === 0 && items[4].field.key === "flat_in");

// group_of 分桶: bool -> 父行 inline, 其余 -> 子卡
const owner = items.find((it) => it.type === "field" && it.field.key === "owner");
ok("bool 从属挂父行 inline", owner.inline.length === 1 && owner.inline[0].field.key === "inline_bool" &&
   JSON.stringify(owner.inline[0].path) === JSON.stringify([...BASE, "inline_bool"]));
ok("非 bool 从属不占根位", !items.some((it) => it.type === "field" && (it.field.key === "inline_bool" || it.field.key === "sub_card")));
const sub = items.find((it) => it.type === "subcard");
ok("子卡: 缩进一级/归属标注", sub.depth === 1 && sub.ownerField === owner.field &&
   JSON.stringify(sub.owner) === JSON.stringify(BASE) && sub.label.indexOf("Owner") >= 0);
ok("子卡内部不再二次分组(allowGrouping=false)", sub.items.length === 1 && sub.items[0].type === "field" &&
   sub.items[0].field.key === "sub_card");

// _attachGrey: greyBy 只在本层覆写(第七轮修复)
const flatIn = items[4];
const flatDep = FLAT_FIELDS[1];
ok("平铺段内层 greyBy 不被外层清掉", flatIn.greyBy === flatDep);
ok("子卡灰显引用同段外层字段表", sub.items[0].greyBy === F[0]);
const loner = items.find((it) => it.field && it.field.key === "loner");
ok("引用键不在本层不覆写(greyBy 缺省)", loner.greyBy === undefined);

// cfgGreyed 判定: 同段覆写值 / greyBy 缺省兜底
ok("灰显: 同段字段值不满足 grey_if", vm.cfgGreyed(flatIn) === true);
const vmOk = makeVm({ config: { basic: { plain: "x" } } });
const itemsOk = vmOk.cfgFlatten(F, BASE, 0);
ok("灰显: 同段字段值满足 grey_if", vmOk.cfgGreyed(itemsOk[4]) === false &&
   vmOk.cfgGreyed(itemsOk.find((it) => it.field && it.field.key === "loner")) === true);
ok("灰显: 无 grey_if 恒不灰", vm.cfgGreyed(items.find((it) => it.field && it.field.key === "plain")) === false);

// cfgGroupOpen/Toggle 三态: 缺省折叠 / 跟随 schema open / 显式翻转写出 false
const grpField = F[2];
const grpPath = [...BASE, "grp"];
ok("三态: 未点过且未声明 open = 折叠", vm.cfgGroupOpen(grpPath, grpField) === false);
vm.cfgGroupToggle(grpPath, grpField);
ok("三态: 点击展开(本地图生效)", vm.cfgGroupOpen(grpPath, grpField) === true);
vm.cfgGroupToggle(grpPath, grpField);
ok("三态: 再点收起(取反写显式值)", vm.cfgGroupOpen(grpPath, grpField) === false && vm.cfg.openGroups["config.basic.grp"] === false);
const flatField = F[4];
const flatPath = [...BASE, "flat"];
ok("三态: 声明 open 缺省展开", vm.cfgGroupOpen(flatPath, flatField) === true);
vm.cfgGroupToggle(flatPath, flatField);
ok("三态: 对缺省展开段点击写出显式 false(修复后可收起)", vm.cfgGroupOpen(flatPath, flatField) === false &&
   vm.cfg.openGroups["config.basic.flat"] === false);

// 空输入与无 grey_if 项
ok("空字段表 -> 空项", vm.cfgFlatten([], BASE, 0).length === 0);
ok("group 项无 grey_if 恒不灰(结构项不误灰)", vmOk.cfgGreyed(itemsOk[2]) === false);
""" + "\n" + _IIFE_CLOSE

# ---- pytest 入口 --------------------------------------------------------------------------------


def test_r4_cfgload_select_key_liveness():
    """R5#153 修复回归: cfgLoad 选中键存在性校验, 幽灵键回落首项且不再复活已放弃的改名"""
    report = _run_probe(_NODE_CFGLOAD_PROBE, _EDITOR_BUNDLE, _RULES_JS)
    _assert_battery(report, "cfgLoad 选中键存活电池")


def test_r4_unit_controls_family():
    """R5#168(major): 数值+单位控件族三 kind 拆拼往返与回退分支(空串/无单位/非法串/表外单位)"""
    report = _run_probe(_NODE_UNIT_PROBE, _EDITOR_BUNDLE)
    _assert_battery(report, "数值+单位控件族电池")


def test_r4_unsaved_guard_chain():
    """R5#167(major): 未保存改动防护链三分支结算 + beforeunload 挂摘幂等 + 键盘刷新四道闸"""
    report = _run_probe(_NODE_GUARD_PROBE, _EDITOR_BUNDLE, _RULES_JS)
    _assert_battery(report, "未保存改动防护链电池")


def test_r4_site_fallback_chain():
    """R5#169(major): 站点回退链 7 键族(路径判据/回填/徽标/占位/跟随全局/删键)与反例"""
    report = _run_probe(_NODE_FALLBACK_PROBE, _EDITOR_BUNDLE)
    _assert_battery(report, "站点回退链电池")


def test_r4_curve_editor_battery():
    """R5#170(major): 曲线编辑器进制判别/解析回退/阶梯几何/∞区封顶/刻度省略/增删档序号搬移"""
    report = _run_probe(_NODE_CURVE_PROBE, _EDITOR_BUNDLE, _FORMAT_JS)
    _assert_battery(report, "曲线编辑器电池")


def test_r4_entity_skeleton_battery():
    """R5#171(major): 命名实体三骨架(增/改/删保序与查重) + hubAddEntity 入口 + _rules normalize"""
    report = _run_probe(_NODE_ENTITY_PROBE, _EDITOR_BUNDLE, _HUB_BUNDLE)
    _assert_battery(report, "命名实体三骨架电池")


def test_r4_cfg_flatten_battery():
    """R5#176: cfgFlatten 四种 item.type/分桶/greyBy 本层覆写/hidden 跳过/组三态"""
    report = _run_probe(_NODE_FLATTEN_PROBE, _EDITOR_BUNDLE, _HUB_BUNDLE)
    _assert_battery(report, "字段树展开电池")
