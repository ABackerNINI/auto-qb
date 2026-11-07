"""test_webui_static_r4_config_hub 测试计划: 存量评审 R4 static 主题清池 P06 —— config_hub*(tracker/hr/tm)域
1 修复回归 + 3 node 电池(R5#154 修复; R5#172/173/174 补测)

## 测试计划(每个测试函数一条)
- test_r4_tm_shutdown_rollback_presence: R5#154 修复回归 —— 「关闭工具」保存失败后的回滚尊重
  磁盘原态: enabled 键盘上本就不存在(默认真)时删键还原(cfgExists 假 + cfgDirty 不翻真),
  不再无条件写 "true" 把多余键留在内存树里(修复前 cfgDirty 凭空翻真, 下次保存把多余键写进
  YAML); 键盘上存在时行为不变(回滚写回 "true"); 两场景 shutdownErr 落账、shutting 复位
- test_r4_tracker_search_battery: R5#172(major) —— 站点搜索匹配语义四单点直跑:
  trackerNorm 的 CJK 归一(中文词不折空 —— 「中文搜索直接废掉」事故回归锚)、
  trackerParseQuery 负词/短语/孤立 -/未闭合引号宽容容错/negOnly、trackerRows 序列化兜底
  (名称行恒最前/布尔跳过/数字 String/列表逐项/dict 递归叶子/掩码哨兵跳过/空串与未知键不搜)、
  hubTrackerHits 负词整站排除 + 正词跨行 AND + chip 去重/组序/上限 3/more 计数
- test_r4_hr_site_binding_battery: R5#173 —— HR 站点接入绑定五分支: 显式 tracker 存在=已映射/
  不存在=warn 保存后校验报错/自动绑定唯一命中(精确相等/右向子域/反向子域)/多命中歧义/未绑定,
  endsWith 双向子域匹配正反例(伪装域 hhan.club.evil.com 与前缀粘连 nothhan.club 不命中);
  hrSiteSetEnabled「未配置不写垃圾键」守卫(关+缺键零写/关+有键写 false/开+缺键写 true)与
  hrSiteEnabled 读侧(cfgTruthy 口径)
- test_r4_tm_form_roundtrip_battery: R5#174 —— 工具参数表单往返: tmParams 全 12 键
  normalize->buildPayload 恒等(复合串与裸数值两形态, 「裸数值无损往返」注释承诺)、list 拆分
  (trim/空串/null)/未回显键不发明值/time·size·speed 复合串原样回传(不再 Number() 化)/
  text·int 归一(空串 int 兜 0)/tmNormalizeForm 列表折逗号串、tmPickApplyExe 路径分隔符选择
  (Windows 反斜杠与 POSIX 斜杠 + 尾斜杠剥离)与空名/空路径 no-op

加载口径: config_hub 域经 webui_helpers.bundle_file("config_hub.js") 聚合(根 + hr/tracker/tm
三片段清单序, 与拆分前同一份代码); tm 回滚电池与 hr 绑定电池依赖的 cfg* 读写单点
(cfgSave/cfgSetBool/cfgDelPath/cfgExists/cfgRaw/cfgTrackerNames/cfgSetPath)在 config_editor
bundle(真文件并入)。computed(hubTrackerHits/hubTrackerIndex)经 window.CONFIG_HUB.computed
取出后挂 getter(与真实例取值等价)。confirmDialog/api/toast 按浏览器契约给桩。无 node 静默跳过
(与既有 node 电池同口径, 不引入 pytest skip)。
"""

import os

from test_webui_static_r4_node_batteries import _assert_battery, _run_probe
from webui_helpers import STATIC_ROOT, bundle_file

_HUB_BUNDLE = bundle_file("config_hub.js")
_EDITOR_BUNDLE = bundle_file("config_editor.js")

# node v24 的 -e 对「顶层 await + require」报 ERR_AMBIGUOUS_MODULE_SYNTAX: 电池体一律包 IIFE
# (与 P05 config_editor 电池同款包装)。收尾报告 {ok, total, failed} 逐条带断言名
_IIFE_OPEN = "(async () => {\n"
_IIFE_CLOSE = (
    'console.log(JSON.stringify({\n'
    '  ok: checks.filter((c) => c[1]).length, total: checks.length,\n'
    '  failed: checks.filter((c) => !c[1]).map((c) => c[0]),\n'
    '}));\n'
    '})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });'
)

# R5#154 修复回归: tmShutdownTool 保存失败回滚尊重磁盘原态 --------------------------------
_NODE_TM_ROLLBACK_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(cfgSave/SetBool/DelPath/Exists)
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_hub bundle(config_hub_tm.js 的 tmShutdownTool)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_HUB.methods);

const PUT_FAIL = async (url, opts) => { if (opts && opts.method === "PUT") throw new Error("2 处配置错误"); return {}; };

function makeVm(tree, apiImpl) {
  const vm = Object.assign({}, M, {
    cfg: {
      tree: JSON.parse(JSON.stringify(tree)), baseline: JSON.stringify(tree),
      schema: null, loading: false, saving: false, error: "", saveError: "",
      trackerKey: null, ruleGroupKey: null, openRuleMeta: {}, openSections: {}, openGroups: {},
      openLists: {}, openCurves: {}, picker: { open: false, groupKey: "", ruleName: "", list: "" },
      chartHover: null,
    },
    tm: { shutting: false, shutdownMsg: "", shutdownErr: "" },
    toasts: [],
    toast(msg, kind) { vm.toasts.push([msg, kind]); },
    async api(url, opts) { return (apiImpl || PUT_FAIL)(url, opts); },
    async confirmDialog() { return true; },
  });
  Object.defineProperty(vm, "cfgDirty", {
    get() { return vm.cfg.tree ? JSON.stringify(vm.cfg.tree) !== vm.cfg.baseline : false; },
  });
  return vm;
}
const ENABLED = ["config", "traffic_source", "enabled"];
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// (1) 键盘上本就不存在(默认真; traffic_source 段在但没写 enabled —— 盘上真实形态):
//   保存失败回滚必须删键还原, 而不是把 enabled:"true" 留在内存树里
const vm1 = makeVm({ config: { trackers: { A: {} }, traffic_source: { provider: "traffic_monitor" } } });
await vm1.tmShutdownTool();
ok("保存失败: shutdownErr 落账不谎报成功", vm1.tm.shutdownErr === "保存失败, 未停止工具(可重试)");
ok("保存失败: 不停工具(无 shutdown 成功回执)", vm1.tm.shutdownMsg === "");
ok("回滚后 shutting 复位(finally)", vm1.tm.shutting === false);
ok("键原不存在: 回滚删键(cfgExists 为假, 修复前写 true 必红)", vm1.cfgExists(ENABLED) === false);
ok("键原不存在: cfgDirty 不翻真(内存树回 baseline, 修复前必红)", vm1.cfgDirty === false);
ok("键原不存在: traffic_source 段既有键(provider)不受回滚牵连",
   vm1.cfgRaw(["config", "traffic_source", "provider"]) === "traffic_monitor");

// (2) 键盘上存在(enabled: "true"): 行为不变 —— 回滚写回 "true"
const vm2 = makeVm({ config: { traffic_source: { enabled: "true", provider: "traffic_monitor" } } });
await vm2.tmShutdownTool();
ok("键原存在: 回滚写回 true(原行为保持)", vm2.cfgRaw(ENABLED) === "true");
ok("键原存在: cfgDirty 不翻真", vm2.cfgDirty === false);
ok("键原存在: shutdownErr 同样落账", vm2.tm.shutdownErr.indexOf("保存失败") >= 0);
""" + "\n" + _IIFE_CLOSE

# R5#172(major): 站点搜索匹配语义四单点 ----------------------------------------------------
_NODE_TRACKER_SEARCH_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(cfgConfig/cfgTrackerNames)
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_hub bundle(tracker 三单点 + hits computed)
const HC = window.CONFIG_HUB.computed;
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_HUB.methods);

const TRACKERS = {
  "HHan": { domains: ["hhan.club", "www.hhan.club"], tags: ["汉化组"], rules: ["auto-skip"] },
  "Plain": { domains: ["plain.io"], tags: ["eng"], upload_speed_limit: "10MiB/s" },
  "Masked": { domains: ["masked.net"], hr: "********", secret: "notsearchable" },
  "Chip": { tags: ["mx"], domains: ["mx.club", "mx.club"], groups: ["mx2"], remove_tags: ["mx3"], rules: ["mx4"] },
};
const vm = Object.assign({}, M, {
  cfg: { tree: { config: { trackers: TRACKERS } }, trackerQuery: "", trackerKey: null },
});
Object.defineProperty(vm, "hubTrackerIndex", {
  get() { return HC.hubTrackerIndex.call(vm); },
});
const hits = (q) => { vm.cfg.trackerQuery = q; return HC.hubTrackerHits.call(vm); };
const norm = (s) => M.trackerNorm.call(vm, s);
const parse = (q) => M.trackerParseQuery.call(vm, q);
const rows = (name, entry) => M.trackerRows.call(vm, name, entry);
const J = (v) => JSON.stringify(v);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ---- trackerNorm: CJK 归一(ASCII \W 会把整个中文词折成空格, 中文搜索直接废掉 —— 事故锚) ----
ok("norm: 分隔符折单空格 + 小写", norm("HH.club--Misc") === "hh club misc");
ok("norm: 中文词原样保留(u 标志 [^\\p{L}\\p{N}] 口径)", norm("汉化组") === "汉化组");
ok("norm: 中英混排 CJK 不折空", norm("HH 汉化 v2") === "hh 汉化 v2");

// ---- trackerParseQuery: 负词 / 短语 / 宽容容错 / negOnly ----
ok("parse: 空格分词 = 隐式 AND", J(parse("alpha beta")).includes('"pos":["alpha","beta"]'));
ok("parse: -词 进排除表", J(parse("alpha -beta")) === J({ pos: ["alpha"], neg: ["beta"], negOnly: false }));
ok("parse: 短语整串保留空格", J(parse('"big row"')).includes('"pos":["big row"]'));
ok("parse: -短语 进排除表", J(parse('-"big row"')).includes('"neg":["big row"]'));
ok("parse: 孤立 - 忽略(归一后空串丢弃)", J(parse(" - ")).includes('"pos":[]') && J(parse(" - ")).includes('"neg":[]'));
ok("parse: 未闭合引号宽容容错(内容不丢, 收到行尾)",
   J(parse('alpha "beta gamma')) === J({ pos: ["alpha", "beta", "gamma"], neg: [], negOnly: false }));
ok("parse: 只有负词时 negOnly 置位", parse("-a -b").negOnly === true && parse("a -b").negOnly === false);

// ---- trackerRows: 序列化兜底口径 ----
const r0 = rows("HHan", TRACKERS.HHan);
ok("rows: 名称行恒在最前", r0[0].grp === "名称" && r0[0].raw === "HHan" && r0[0].n === "hhan");
ok("rows: 列表逐项 + 归一", r0.slice(1).some((r) => r.grp === "域名" && r.raw === "hhan.club" && r.n === "hhan club"));
const rMask = rows("Masked", TRACKERS.Masked);
ok("rows: 掩码哨兵整行跳过(R 级值不可搜)", !rMask.some((r) => r.raw === "********" || r.raw.indexOf("*") >= 0));
ok("rows: 表外键不入搜索面(secret/note 不产行)", !rMask.some((r) => r.raw === "notsearchable"));
const rScal = rows("S", { tags: true, upload_speed_limit: 42, groups: ["", "g"], hr: { add_tag: "deep" } });
ok("rows: 布尔跳过(无可读文本)", !rScal.some((r) => r.raw === "true"));
ok("rows: 数字 String() 化", rScal.some((r) => r.grp === "上传限速" && r.raw === "42" && r.n === "42"));
ok("rows: 空串项跳过(不出空 chip), 非空项保留",
   rScal.filter((r) => r.grp === "分组").length === 1 && rScal.some((r) => r.raw === "g"));
ok("rows: dict 递归到叶子(组标签跟随所在键)", rScal.some((r) => r.grp === "HR" && r.raw === "deep"));

// ---- hubTrackerHits: 负词整站排除 / 正词 AND / chip 组序与上限 ----
ok("hits: 空词不激活", hits("").active === false && hits("").total === 4);
ok("hits: 只有排除词 = negOnly 空结果", (() => { const r = hits("-plain"); return r.active && r.kind === "negOnly" && r.hits.length === 0 && r.total === 4; })());
ok("hits: CJK 正词命中(中文搜索活的)", hits("汉化").hits.map((h) => h.name).join(",") === "HHan");
ok("hits: 正词跨行 AND(名称+标签各中一词才留)", hits("汉化 hhan").hits.length === 1 && hits("汉化 hhan").hits[0].nameHit === true);
ok("hits: 负词整站排除(标签命中也救不回)", hits("汉化 -hhan").hits.length === 0);
ok("hits: 负词排除其余照常(命中名单精确)", J(hits("汉化 -plain").hits.map((h) => h.name)) === J(["HHan"]));
ok("hits: 掩码/表外键的站点按名称仍可搜", hits("masked").hits.length === 1 && hits("notsearchable").hits.length === 0);
const chipHit = hits("mx");
ok("hits: chip 组序(标签<域名<分组)与上限 3",
   chipHit.hits.length === 1 && J(chipHit.hits[0].chips.map((c) => c.grp)) === J(["标签", "域名", "分组"]));
ok("hits: 超限折进 more 计数", chipHit.hits[0].chips.length === 3 && chipHit.hits[0].more === 2);
ok("hits: chip 去重(同组同值只留一条)",
   chipHit.hits[0].chips.filter((c) => c.grp === "域名").length === 1);
ok("hits: 名称行不产 chip, nameHit 独立标记", chipHit.hits[0].nameHit === false);
""" + "\n" + _IIFE_CLOSE

# R5#173: HR 站点接入绑定五分支 + 未配置不写垃圾键守卫 --------------------------------------
_NODE_HR_BINDING_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(cfgRaw/cfgTrackerNames/SetBool/Exists)
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_hub bundle(config_hub_hr.js)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_HUB.methods);

const TRACKERS = {
  Uniq: { domains: ["sub.uniq.club"] },     // 右向子域: t.endsWith("." + trackerDomain)
  Exact: { domains: ["exact.club"] },       // 精确相等
  Rev: { domains: ["rev.club"] },           // 反向子域: trackerDomain.endsWith("." + t)
  Amb1: { domains: ["amb.club"] },
  Amb2: { domains: ["amb.club"] },          // 多命中歧义
  Evil: { domains: ["hhan.club.evil.com"] },   // endsWith 反例: 后缀粘连不算
  Noth: { domains: ["nothhan.club"] },         // endsWith 反例: 前缀粘连不算
};
function makeVm(sites) {
  const vm = Object.assign({}, M, {
    cfg: { tree: { config: { trackers: TRACKERS, hr_check: { sites: JSON.parse(JSON.stringify(sites || {})) } } } },
  });
  return vm;
}
const binding = (vm, id, dom) => M.hrSiteBinding.call(vm, { id: id, tracker_domain: dom });
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ---- hrSiteBinding 五分支 ----
const vmE = makeVm({ p_ok: { tracker: "Exact", enabled: "true" }, p_ghost: { tracker: "Ghost" }, p_both: { tracker: "Exact" } });
let b = binding(vmE, "p_ok", "whatever.club");
ok("分支1: 显式 tracker 存在 = 已映射(绿)", b.cls === "" && b.text === "已映射: Exact");
b = binding(vmE, "p_ghost", "whatever.club");
ok("分支2: 显式 tracker 不存在 = warn(保存后校验会报错)", b.cls === "warn" && b.text.indexOf("Ghost 不存在") >= 0);
const vmA = makeVm({});
b = binding(vmA, "p_sub", "uniq.club");
ok("分支3a: 自动绑定唯一命中(右向子域 sub.uniq.club)", b.cls === "" && b.text === "已自动绑定: Uniq（档案默认映射）");
b = binding(vmA, "p_exact", "exact.club");
ok("分支3b: 自动绑定(精确相等)", b.cls === "" && b.text.indexOf("已自动绑定: Exact") >= 0);
b = binding(vmA, "p_rev", "announce.rev.club");
ok("分支3c: 自动绑定(反向子域容错, announce 域 -> 裸域档案)", b.cls === "" && b.text.indexOf("已自动绑定: Rev") >= 0);
b = binding(vmA, "p_amb", "amb.club");
ok("分支4: 多命中歧义 = warn 并点名全部", b.cls === "warn" && b.text.indexOf("歧义") >= 0 &&
   b.text.indexOf("Amb1") >= 0 && b.text.indexOf("Amb2") >= 0);
b = binding(vmA, "p_none", "missing.club");
ok("分支5: 未绑定 = warn 给补配指引", b.cls === "warn" && b.text.indexOf("未绑定") >= 0 && b.text.indexOf("missing.club") >= 0);
b = binding(vmA, "p_spoof", "hhan.club");
ok("endsWith 反例: 伪装域(hhan.club.evil.com)与前缀粘连(nothhan.club)不命中 -> 未绑定",
   b.cls === "warn" && b.text.indexOf("未绑定") >= 0);
b = binding(vmE, "p_both", "amb.club");
ok("显式 tracker 优先于自动查表(歧义域名下仍走已映射)", b.cls === "" && b.text === "已映射: Exact");
const vmT = makeVm({ p_trim: { tracker: "  Exact  " } });
b = binding(vmT, "p_trim", " UNIQ.CLUB ");
ok("归一口径: 显式名 trim / 档案域 trim+小写", b.cls === "" && b.text.indexOf("已映射: Exact") >= 0);

// ---- hrSiteSetEnabled: 未配置不写垃圾键守卫 + hrSiteEnabled 读侧 ----
const vmS = makeVm({ p_on: { enabled: "true" }, p_off: { enabled: "false", note: "keep" } });
ok("读侧: enabled true 为开", M.hrSiteEnabled.call(vmS, "p_on") === true);
ok("读侧: enabled false 为关", M.hrSiteEnabled.call(vmS, "p_off") === false);
ok("读侧: 无条目 = 关", M.hrSiteEnabled.call(vmS, "absent") === false);
M.hrSiteSetEnabled.call(vmS, "fresh", false);
ok("守卫: 关 + 键未配置 = 零写(不产垃圾键)", vmS.cfgExists(["config", "hr_check", "sites", "fresh"]) === false);
M.hrSiteSetEnabled.call(vmS, "p_off", false);
ok("关 + 键已配置 = 写 false", vmS.cfgRaw(["config", "hr_check", "sites", "p_off", "enabled"]) === "false");
ok("关 + 键已配置: 同条目其它键不牵连", vmS.cfgRaw(["config", "hr_check", "sites", "p_off", "note"]) === "keep");
M.hrSiteSetEnabled.call(vmS, "fresh2", true);
ok("开 + 键未配置 = 写 true(启用本来就要落键)", vmS.cfgRaw(["config", "hr_check", "sites", "fresh2", "enabled"]) === "true");
""" + "\n" + _IIFE_CLOSE

# R5#174: 工具参数表单往返(tmNormalizeForm -> tmBuildPayload) -------------------------------
_NODE_TM_FORM_PROBE = _IIFE_OPEN + r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // config_editor bundle(cfgSetPath/cfgRaw)
eval(fs.readFileSync(process.argv[2], "utf8"));  // config_hub bundle(config_hub_tm.js)
const M = Object.assign({}, window.CONFIG_EDITOR.methods, window.CONFIG_HUB.methods);

function makeVm() {
  const vm = Object.assign({}, M, {
    cfg: { tree: { config: {} } },
    tm: { form: {}, pick: { open: false, name: "", error: "", path: "" } },
  });
  return vm;
}
const J = (v) => JSON.stringify(v);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const vm = makeVm();
ok("tmParams 全 12 键(键面漂移先红这里)", vm.tmParams().length === 12);
const kinds = {};
for (const p of vm.tmParams()) kinds[p.key] = p.kind;
ok("12 键 kind 面: time5/size2/speed1/text1/int1/list2",
   J(["sample_interval", "flush_interval_s", "lease_ttl_s", "heartbeat_interval_s", "notify_timeout_s"].every((k) => kinds[k] === "time")) &&
   kinds.flush_delta_bytes === "size" && kinds.notify_threshold_bytes === "size" &&
   kinds.sample_rate_warn_bps === "speed" && kinds.http_host === "text" && kinds.http_port === "int" &&
   kinds.adapter_include === "list" && kinds.adapter_exclude === "list");

// 往返恒等(形态1: 工具侧复合串 + 裸 int + 列表) —— normalize -> buildPayload 原样
const TOOL = {
  sample_interval: "5S", flush_delta_bytes: "1MiB", flush_interval_s: "30S",
  notify_threshold_bytes: "100MiB", sample_rate_warn_bps: "1GiB/s",
  http_host: "127.0.0.1", http_port: 0,
  lease_ttl_s: "3M", heartbeat_interval_s: "1M", notify_timeout_s: "3S",
  adapter_include: ["eth[0-9]+", "ETH"], adapter_exclude: ["VPN", "vEth"],
};
vm.tm.form = vm.tmNormalizeForm(TOOL);
ok("往返恒等: 复合串/裸 int/列表 12 键全量", J(vm.tmBuildPayload()) === J(TOOL));

// 往返恒等(形态2: 旧版工具回显裸数值) —— 「裸数值无损往返」是注释明确承诺的语义
const BARE = {
  sample_interval: 5, flush_delta_bytes: 1048576, flush_interval_s: 30,
  notify_threshold_bytes: 104857600, sample_rate_warn_bps: 1073741824,
  http_host: "127.0.0.1", http_port: 0,
  lease_ttl_s: 180, heartbeat_interval_s: 60, notify_timeout_s: 3,
  adapter_include: [], adapter_exclude: [],
};
vm.tm.form = vm.tmNormalizeForm(BARE);
ok("往返恒等: 裸数值无损往返(不再 Number() 化丢单位)", J(vm.tmBuildPayload()) === J(BARE));

// list 拆分: trim / 空串 / null
vm.tm.form = { adapter_include: "a, b,,c" };
ok("list: 逗号拆分 + trim + 空段滤除", J(vm.tmBuildPayload().adapter_include) === J(["a", "b", "c"]));
vm.tm.form = { adapter_include: "" };
ok("list: 空串 -> 空数组(不是 [''])", J(vm.tmBuildPayload().adapter_include) === J([]));
vm.tm.form = { adapter_include: null };
ok("list: null -> 空数组", J(vm.tmBuildPayload().adapter_include) === J([]));

// 未回显键不发明值(丢给工具侧默认)
vm.tm.form = { http_host: "0.0.0.0" };
ok("未回显键不发明值(载荷只含回显过的键)", J(vm.tmBuildPayload()) === J({ http_host: "0.0.0.0" }));

// time/size/speed 复合串原样回传(旧版 Number() 化会 NaN 丢单位)
vm.tm.form = { sample_interval: "30S", flush_delta_bytes: "10MiB", sample_rate_warn_bps: "1GiB/s" };
const outC = vm.tmBuildPayload();
ok("复合串原样回传(不做数值化)", outC.sample_interval === "30S" && outC.flush_delta_bytes === "10MiB" &&
   outC.sample_rate_warn_bps === "1GiB/s");

// text/int 归一: text String() 化与空兜、int Number() 化与空兜 0
vm.tm.form = { http_host: 42, http_port: "8080" };
ok("text 归一 String()/int 归一 Number()", vm.tmBuildPayload().http_host === "42" && vm.tmBuildPayload().http_port === 8080);
vm.tm.form = { http_host: null, http_port: "" };
ok("text 空 -> 空串/int 空 -> 0", vm.tmBuildPayload().http_host === "" && vm.tmBuildPayload().http_port === 0);

// tmNormalizeForm: 列表折逗号串, 其余原样; 空入参 {}
ok("normalize: 列表折逗号串", J(vm.tmNormalizeForm({ a: ["x", "y"], b: "z" })) === J({ a: "x, y", b: "z" }));
ok("normalize: null 入参 -> {}", J(vm.tmNormalizeForm(null)) === J({}));

// tmPickApplyExe: 路径分隔符选择 + 尾斜杠剥离 + 空名/空路径 no-op
const EXE = ["config", "traffic_source", "global_traffic_monitor", "tool_exe"];
vm.tm.pick = { open: true, name: "gtm.exe", error: "", path: "D:\\Tools\\GTM\\" };
vm.tmPickApplyExe();
ok("exe: Windows 分隔符 + 尾斜杠剥离", vm.cfgRaw(EXE) === "D:\\Tools\\GTM\\gtm.exe");
vm.tm.pick = { open: true, name: "gtm", path: "/usr/local/bin" };
vm.tmPickApplyExe();
ok("exe: POSIX 分隔符", vm.cfgRaw(EXE) === "/usr/local/bin/gtm");
const vm2 = makeVm();
vm2.tm.pick = { open: true, name: "", path: "/x" };
vm2.tmPickApplyExe();
vm2.tm.pick = { open: true, name: "g.exe", path: "" };
vm2.tmPickApplyExe();
ok("exe: 空名/空路径 no-op(不写半截路径)", vm2.cfgExists(EXE) === false);
""" + "\n" + _IIFE_CLOSE


def test_r4_tm_shutdown_rollback_presence():
    """R5#154 修复回归: 关闭工具保存失败回滚尊重磁盘原态(键缺失删键还原, cfgDirty 不翻真)"""
    report = _run_probe(_NODE_TM_ROLLBACK_PROBE, _EDITOR_BUNDLE, _HUB_BUNDLE)
    _assert_battery(report, "tm 关闭工具回滚电池")


def test_r4_tracker_search_battery():
    """R5#172(major): 站点搜索四单点真跑(norm CJK/parse 负词短语/rows 兜底/hits 排除 AND chip)"""
    report = _run_probe(_NODE_TRACKER_SEARCH_PROBE, _EDITOR_BUNDLE, _HUB_BUNDLE)
    _assert_battery(report, "站点搜索语义电池")


def test_r4_hr_site_binding_battery():
    """R5#173: HR 站点接入绑定五分支(显式/自动唯一/歧义/未绑定 + 子域双向正反例) + 垃圾键守卫"""
    report = _run_probe(_NODE_HR_BINDING_PROBE, _EDITOR_BUNDLE, _HUB_BUNDLE)
    _assert_battery(report, "HR 站点接入绑定电池")


def test_r4_tm_form_roundtrip_battery():
    """R5#174: 工具参数表单往返(12 键恒等/裸数值无损/list 拆分/复合串原样/路径分隔符)"""
    report = _run_probe(_NODE_TM_FORM_PROBE, _EDITOR_BUNDLE, _HUB_BUNDLE)
    _assert_battery(report, "工具参数表单往返电池")
