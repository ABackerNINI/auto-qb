"""test_webui_ctx_menu_registry 测试计划: 行右键菜单注册表 + 布局解析守阵(计划 26-10-20-0024 W2)

## 背景
ctx-menus.html 四支菜单从静态模板直写改为注册表单点(shared/ctx_menu.js) + 布局数据(web.ctx_menu,
经 /api/webui/flags 下发)驱动。本文件守阵注册表层: 1. 合并语义(补尾/显隐槽位/跨层双向/
分隔线一等公民/次级空不显示入口/未知 id 容忍/门控串联)node 真跑; 2. 模板消费形态(W3 起四支
v-for 消费 ctxItems/ctxSubItems, 判据链与子面板交互原样); 3. 接线守阵(manifest/mixin/挂载面)。

## 测试计划(每个测试函数一条)
- test_ctx_menu_template_consumes_registry: 模板消费守阵(W3 + 2026-10-22 骨架单点) —— 支名
  只许走 ctxMenuKind()(无 ctxItems('<支>') 字面量) + 行菜单根块 .ctx-item 骨架恰 2 份
  (一级 + 次级面板) + 「更多操作」父项结构(has-sub/ctx-caret/ctxSubItems(ctxMenuKind())/
  CTX-05 交互三件/钳位状态) + 逐项 @click 直写回潮拦截(唯一允许 ctxRun(it) 与 toggleSub)。
  W2 期还另有一项「注册表 ↔ 静态模板计数对账」过渡锚
  (52 项 + 14 线逐支相等), W3 模板 v-for 化后如期退役 —— 渲染层零漂移由 e2e menus.spec 接棒,
  注册表层由本文件余两项与 W5 新守阵(注册表 id ↔ 默认布局 ↔ config 契约 ↔ flags 键)接棒
- test_ctx_menu_registry_node_battery: node 真跑电池(无 node 静默跳过, 不引入 skip) —— 默认布局
  硬编码钉(四支 + 次级逐位) + 注册表完整性(id 唯一/形状齐/gate·dyn 合法/次级默认仅 member) +
  无 cfg 渲染 == 默认序 + 补尾 + 隐藏槽位保留与恢复归位 + 跨层双向 + sep 增删与 token 分配 +
  次级空与只剩线不显示父项(D7) + 未知 id 容忍与 sep 一等公民 + 门控两态 + 结构项防嵌套 +
  动态 label + 置灰 title + ctxRun 分派 + 静态名(labelText)成对 + 动词族灰色后缀(四支 12 项,
  计划 26-10-20-0145) + 动态 submenu「转移到」(四支各一, 子项 vm 单点供给/无供给方空数组/
  advanced 空不压父项/次级防嵌套/布局可隐藏, 计划 26-10-31-0306 T6) + key 字段逐条对账 §05
  映射表(key 引用存在于 shortcuts 注册表/四条不映射项无 key/两条空位 key 照填, 计划
  26-11-12-0344 S2) + 键帽渲染(kbd 经 kbShortcutDisplay 现算/绑定项出键帽/danger 照常 D5/
  qb-traffic scope 口径差仍标/不映射与空位项无 kbd 字段/改绑即时跟随与显式禁用隐藏)
- test_ctx_menu_key_fields_reconcile_shortcut_registry: key 字段对账 python 静态面(计划
  26-11-12-0344 S2/§05, 不依赖 node) —— key 引用必须存在于 shortcuts 注册表(_registry 解析) /
  「不映射」四项(limits/skip_check/transfer/sub-more)无 key / 其余非 sep 项一律带 key /
  落点总数 == 44(multi 8 + episode 5 + member 一级 11 + group 10 + 次级 10)
- test_ctx_custom_panel_wiring: 设置页「WebUI」卡接线守阵(W4) —— 卡片注册/hubNow/hubGo 复位/
  hubRestore 认它 + 模板 v-else-if 分支内四支 tab 与两个固定区(D17)+ 跳检开关绑 cmSkipCheck(D6)
  + app.js mixin + 三 manifest 装载序(ctx_menu.js < ctx_menu_custom.js < app.js)+ .ctx-custom-* 样式在
- test_ctx_custom_write_shape_passes_config_contract: 契约闭环守阵(W5) —— node 真跑定制面板的
  **写路径**(真 vm 桩上调 cmToggleHidden/cmMoveLevel/cmAddSep/cmMoveStep; R5#28 起加跑拖拽
  cmDropAt/cmDropTail 与 cmDelSep/cmResetBranch), 产出的布局必须
  1. 只写动过的那一支 2. 支级/次级键集合 == 后端 _CTX_BRANCH_KEYS/_CTX_LAYER_KEYS 3. 过
  validate_config 零错误 4. 隐藏留槽位 / 跨层双向 / 用户线 sep:uN / 同层换位生效
  5. 拖拽落点三形态(同层向后回退一格/同层向前原位/跨层按目标 idx 插入)+ 表尾追加 + 删线无残迹 + 恢复默认两层同回
- test_ctx_menu_wiring: 接线守阵 —— 三份 manifest 成对登记 ctx_menu.js 且装载序
  menu.js < ctx_menu.js < app.js; app.js mixin 行在; REG/mixin 双挂载面在文件里
"""
import json
import os
import re
import shutil
import subprocess

from webui_helpers import read_shared
from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_CTX_MENU_JS = os.path.join(STATIC_ROOT, "shared", "ctx_menu.js")
_CTX_CUSTOM_JS = os.path.join(STATIC_ROOT, "shared", "ctx_menu_custom.js")
_CTX_MENUS_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "ctx-menus.html")
_SHORTCUTS_JS = os.path.join(STATIC_ROOT, "shared", "shortcuts.js")

# node 探针: 在真 vm 桩上跑**定制面板的写路径**(ctx_menu_custom.js 的 methods), 输出面板
# 实际写回的 ctx_menu 形状 —— 交 python 侧过 validate_config(两端对"合法布局"的认定必须一致)
# R5#28 起加跑第二阶段: 拖拽落点(cmDropAt/cmDropTail)与 cmDelSep/cmResetBranch —— 每场景
# 一新桩互不串台, 输出 drops 交 python 侧断言写回 order 语义与 _CTX_LAYER_KEYS 契约。
_NODE_CTX_WRITE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // ctx_menu.js: 注册表 + 合并语义
eval(fs.readFileSync(process.argv[2], "utf8"));   // ctx_menu_custom.js: 面板编辑面
const R = window.AQB_CTX_MENU_REG, C = window.AQB_CTX_CUSTOM;
const mkVm = () => {
  const vm = {
    cfg: { tree: { config: {} } },
    ctxCust: { branch: "member", drag: null, over: null },
    cfgConfig() { return this.cfg.tree.config; },
    toast() {},
  };
  /* 面板方法之间走 this.xxx 互调(cmToggleHidden -> cmDraft -> cmLayout ...), 得把整面方法
   * 挂到桩上 —— 只挂被测的那一个会立刻 "this.cmDraft is not a function" */
  for (const k of Object.keys(C.methods)) vm[k] = (...a) => C.methods[k].apply(vm, a);
  /* 拖拽写路径(cmDropAt/cmDropTail)经 computed cmBranch() 认支 —— 同 Vue 实例把 computed 一并求值挂上 */
  for (const k of Object.keys(C.computed)) vm[k] = C.computed[k].call(vm);
  return vm;
};
const call = (vm, name, ...args) => C.methods[name].call(vm, ...args);

// ---- 阶段一(原五写路径, 输出契约不变): 隐藏/跨层/加线/换位 ----
const vm = mkVm();
call(vm, "cmToggleHidden", "member", 0, "info");      // 隐藏一项
call(vm, "cmToggleHidden", "member", 0, "sep:d2");    // 隐藏一条默认线
call(vm, "cmMoveLevel", "member", 0, "rename");       // 一级 -> 「更多操作」
call(vm, "cmAddSep", "member", 1);                    // 次级加一条用户线
call(vm, "cmMoveStep", "member", 0, "resume", 1);     // ↑↓ 换位
const lay = vm.cfg.tree.config.web.ctx_menu;

// ---- 阶段二(R5#28): 拖拽落点/删线/恢复默认 —— member 默认序里 rename idx=8 / info idx=4 ----
const row = (id, level, idx) => ({ id, level, idx, movable: true });
const memberOf = (v) => v.cfg.tree.config.web.ctx_menu.member;
const drops = {};
// 同层向后: resume(idx0) 拖到 info(idx4) —— 摘除后 from<row.idx 回退一格, 插在 sep:d1 与 info 之间
{
  const v = mkVm();
  call(v, "cmDragStart", row("resume", 0, 0), null);
  call(v, "cmDropAt", row("info", 0, 4));
  drops.sameLater = memberOf(v);
  drops.sameLaterDragCleared = v.ctxCust.drag === null && v.ctxCust.over === null;
}
// 同层向前: info(idx4) 拖到 resume(idx0) —— from>row.idx 原位插入表头
{
  const v = mkVm();
  call(v, "cmDragStart", row("info", 0, 4), null);
  call(v, "cmDropAt", row("resume", 0, 0));
  drops.sameEarlier = memberOf(v);
}
// 跨层插入: 次级 queue-top(idx0) 拖到一级 info(idx4) —— 跨层不回退, 按目标行 idx 插入
{
  const v = mkVm();
  call(v, "cmDragStart", row("queue-top", 1, 0), null);
  call(v, "cmDropAt", row("info", 0, 4));
  drops.crossInsert = memberOf(v);
}
// cmDropTail 跨层追加: 一级 rename 拖到次级表尾空白
{
  const v = mkVm();
  call(v, "cmDragStart", row("rename", 0, 8), null);
  call(v, "cmDropTail", "member", 1);
  drops.tailSub = memberOf(v);
}
// cmDropTail 同层追加: resume 拖到一级表尾空白
{
  const v = mkVm();
  call(v, "cmDragStart", row("resume", 0, 0), null);
  call(v, "cmDropTail", "member", 0);
  drops.tailTop = memberOf(v);
}
// cmDelSep: 加一条用户线再删掉(order/hidden 两处都不留残迹)
{
  const v = mkVm();
  call(v, "cmAddSep", "member", 0);
  drops.delSepAdded = memberOf(v).order.slice();
  call(v, "cmDelSep", "member", 0, "sep:u1");
  drops.delSep = memberOf(v);
}
// cmResetBranch: 定制后一键回默认(整对象替换, 两层同回)
{
  const v = mkVm();
  call(v, "cmToggleHidden", "member", 0, "info");
  call(v, "cmMoveLevel", "member", 0, "rename");
  call(v, "cmResetBranch", "member");
  drops.reset = memberOf(v);
  drops.resetMatchesDefault = JSON.stringify(drops.reset.order) === JSON.stringify(R.DEFAULT_CTX_LAYOUT.member.order)
    && JSON.stringify(drops.reset.hidden) === JSON.stringify([])
    && JSON.stringify(drops.reset.sub.order) === JSON.stringify(R.DEFAULT_CTX_LAYOUT.member.sub.order)
    && JSON.stringify(drops.reset.sub.hidden) === JSON.stringify([]);
}
console.log(JSON.stringify({
  layout: lay,
  topKeys: Object.keys(lay.member).sort(),
  subKeys: Object.keys(lay.member.sub).sort(),
  userSeps: lay.member.sub.order.filter((t) => t.indexOf("sep:u") === 0),
  drops,
}));
"""

# node 电池: 加载 ctx_menu.js(global.window 沙箱, 与 _NODE_QB_TRAFFIC_PROBE 同范式),
# 对默认布局与合并语义跑断言电池, 末行输出 JSON 报告。
# 计划 26-11-12-0344 S2 起与 shortcuts.js **同一次 eval**(键帽取数链 AQB_SHORTCUT_DEFS/
# kbShortcutDisplay 与 ctx_menu.js 的 ctxKeycapOf 共处同一 eval 词法域 —— 顶层 const 不跨
# eval 可见, 分两次 eval 会让 ctxKeycapOf 静默回空串把键帽断言全部架空); 电池体(probe 侧)
# 自身也在 eval 外, 故再补一行把注册表挂到 window.__SHORTCUT_DEFS 供 §05 对账读 —— 仅
# 电池沙箱用, 生产文件零改动。
_NODE_CTX_MENU_BATTERY = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8") + "\n;\n" + fs.readFileSync(process.argv[1], "utf8") + "\n;window.__SHORTCUT_DEFS = AQB_SHORTCUT_DEFS;");
const R = window.AQB_CTX_MENU_REG;
const M = window.AQB_CTX_MENU;
const checks = [];
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ids = (arr) => arr.map((i) => i.id);

function stubVm(over) {
  return Object.assign({
    flags: { skip_check_menu: true, qb_traffic_enabled: true },
    menu: { visible: true, key: "G1", hash: "H1", multi: true, episode: { hashes: ["H1"], scope: "ep" } },
    reannounceMenuGate: () => ({ ok: true, title: "" }),
    menuTorrent: () => ({ super_seeding: false, force_start: false, auto_tmm: false }),
    l10nGroup: "辅种组",
    ctxSeedCount: () => 42,   // 菜单灰色后缀的计数单点(真机上来自 menu.js; 电池只验渲染形态)
  }, over || {});
}
const vmWith = (ctxMenu, flagOver) => stubVm({
  flags: Object.assign({ skip_check_menu: true, qb_traffic_enabled: true }, flagOver || {}, ctxMenu ? { ctx_menu: ctxMenu } : {}),
});

// ---- 1. 默认布局硬编码钉(与静态模板四支 + 次级逐位平移; 改此项 = 默认菜单形态漂移, 必须显式 review)
// transfer(计划 26-10-31-0306 T6): 四支各一项「转移到」, 同位次 = 删除线前(D5 一级项 + 动态子面板)
const EXPECT = {
  multi: { order: ["resume", "pause", "reannounce", "sep:d1", "recheck", "skip_check", "limits", "move", "meta", "export", "transfer", "sep:d2", "delete"], hidden: [], sub: { order: [], hidden: [] } },
  episode: { order: ["resume", "pause", "reannounce", "sep:d1", "open-path", "transfer", "sep:d2", "delete"], hidden: [], sub: { order: [], hidden: [] } },
  member: { order: ["resume", "pause", "reannounce", "sep:d1", "info", "sep:d2", "limits", "move", "rename", "meta", "sep:d3", "recheck", "skip_check", "export", "open-path", "transfer", "sep:d4", "sub-more", "sep:d5", "delete"], hidden: [], sub: { order: ["queue-top", "queue-up", "queue-down", "queue-bottom", "sep:s1", "super-seeding", "force-start", "auto-tmm", "share-limits", "sep:s2", "copy-name", "copy-hash"], hidden: [] } },
  group: { order: ["resume", "pause", "reannounce", "sep:d1", "recheck", "skip_check", "limits", "move", "meta", "export", "sep:d2", "open-path", "qb-traffic", "transfer", "sep:d3", "delete"], hidden: [], sub: { order: [], hidden: [] } },
};
for (const b of ["multi", "episode", "member", "group"]) {
  checks.push(["默认布局 " + b, eq(R.DEFAULT_CTX_LAYOUT[b], EXPECT[b])]);
}
let nItem = 0, nSep = 0;
for (const b of ["multi", "episode", "member", "group"]) {
  for (const t of EXPECT[b].order) { if (t.indexOf("sep:") === 0) nSep++; else nItem++; }
}
checks.push(["一级计数 45 项 + 12 线", nItem === 45 && nSep === 12]);
let sItem = 0, sSep = 0;
for (const t of EXPECT.member.sub.order) { if (t.indexOf("sep:") === 0) sSep++; else sItem++; }
checks.push(["次级计数 10 项 + 2 线", sItem === 10 && sSep === 2]);  // copy-magnet 退役(issue 26-11-09-0639): 11 -> 10

// ---- 2. 注册表完整性
for (const b of R.CTX_BRANCHES) {
  const defs = R.CTX_ITEM_DEFS[b];
  const idl = defs.map((d) => d.id);
  checks.push([b + " 一级 id 唯一", new Set(idl).size === idl.length]);
  for (const d of defs) {
    if (d.kind === "sep") { checks.push([b + "." + d.id + " sep 无 label/act", !d.label && !d.act]); continue; }
    checks.push([b + "." + d.id + " 有 label+icon", !!d.label && !!d.icon && !!d.icon.use]);
    if (d.kind === "submenu") checks.push([b + "." + d.id + " submenu 无 act", !d.act]);
    else checks.push([b + "." + d.id + " 有 act", typeof d.act === "function"]);
    if (d.gate) checks.push([b + "." + d.id + " gate 合法", d.gate === "skip_check_menu" || d.gate === "qb_traffic"]);
    if (d.dyn) checks.push([b + "." + d.id + " dyn 合法", d.dyn === "reannounce"]);
  }
}
checks.push(["次级默认仅 member", eq(Object.keys(R.CTX_SUB_ITEM_DEFS), ["member"])]);
{
  const subIds = R.CTX_SUB_ITEM_DEFS.member.map((d) => d.id);
  checks.push(["次级 id 唯一", new Set(subIds).size === subIds.length]);
  const topIds = R.CTX_ITEM_DEFS.member.map((d) => d.id);
  checks.push(["同支两层 token 不撞名", subIds.every((s) => topIds.indexOf(s) < 0)]);
}

// ---- 3. 无 cfg = 默认布局渲染(flags 全开): 渲染 id 序 == 默认 order
{
  const vm = stubVm();
  for (const b of R.CTX_BRANCHES) {
    checks.push([b + " 无 cfg 渲染 == 默认 order", eq(ids(M.methods.ctxItems.call(vm, b)), R.DEFAULT_CTX_LAYOUT[b].order)]);
  }
  checks.push(["member 次级无 cfg 渲染 == 默认 sub order", eq(ids(M.methods.ctxSubItems.call(vm, "member")), R.DEFAULT_CTX_LAYOUT.member.sub.order)]);
}

// ---- 4. 补尾: 用户序只有两项 -> 其余按定义序追加(不丢项)
{
  const vm = vmWith({ member: { order: ["resume", "pause"], hidden: [] } });
  const got = ids(M.methods.ctxItems.call(vm, "member"));
  checks.push(["补尾: 用户序两项打头", got[0] === "resume" && got[1] === "pause"]);
  checks.push(["补尾: 其余按定义序", eq(got.slice(2), R.DEFAULT_CTX_LAYOUT.member.order.slice(2))]);
}

// ---- 5. 隐藏槽位保留 + 取消隐藏归位
{
  const cfg = { member: { order: R.DEFAULT_CTX_LAYOUT.member.order.slice(), hidden: ["export", "sep:d3"] } };
  const merged = R.ctxMergeLayout("member", cfg);
  checks.push(["隐藏项仍在 order 占位", merged.order.indexOf("export") >= 0 && merged.order.indexOf("sep:d3") >= 0]);
  const vm = vmWith(cfg);
  const got = ids(M.methods.ctxItems.call(vm, "member"));
  checks.push(["隐藏项不渲染", got.indexOf("export") < 0 && got.indexOf("sep:d3") < 0]);
  checks.push(["隐藏后其余不重排", eq(got, R.DEFAULT_CTX_LAYOUT.member.order.filter((x) => x !== "export" && x !== "sep:d3"))]);
  cfg.member.hidden = [];
  checks.push(["取消隐藏即归位", eq(ids(M.methods.ctxItems.call(vm, "member")), R.DEFAULT_CTX_LAYOUT.member.order)]);
}

// ---- 6. 跨层双向: rename 入次级 / queue-top 入一级; 补尾不得把对层认领的项拽回
{
  const cfg = { member: {
    order: R.DEFAULT_CTX_LAYOUT.member.order.filter((t) => t !== "rename").concat(["queue-top"]),
    hidden: [],
    sub: { order: R.DEFAULT_CTX_LAYOUT.member.sub.order.filter((t) => t !== "queue-top").concat(["rename"]), hidden: [] },
  } };
  const vm = vmWith(cfg);
  const top = ids(M.methods.ctxItems.call(vm, "member"));
  const sub = ids(M.methods.ctxSubItems.call(vm, "member"));
  checks.push(["跨层: rename 入次级", top.indexOf("rename") < 0 && sub.indexOf("rename") >= 0]);
  checks.push(["跨层: queue-top 入一级", sub.indexOf("queue-top") < 0 && top.indexOf("queue-top") >= 0]);
  checks.push(["跨层: 父项仍在(次级非空)", top.indexOf("sub-more") >= 0]);
  checks.push(["跨层: 无重复渲染", top.filter((t) => sub.indexOf(t) >= 0).length === 0]);
}

// ---- 7. 分隔线一等公民: 用户添加 / 删除(隐藏)/ token 分配
{
  const cfg = { group: { order: R.DEFAULT_CTX_LAYOUT.group.order.slice(), hidden: [] } };
  cfg.group.order.splice(2, 0, "sep:u1");   // 在第三项后插一条用户线
  const vm = vmWith(cfg);
  const got = ids(M.methods.ctxItems.call(vm, "group"));
  checks.push(["用户线可添加且占位", got.indexOf("sep:u1") === 2]);
  cfg.group.hidden = ["sep:u1", "sep:d1"];
  const got2 = ids(M.methods.ctxItems.call(vm, "group"));
  checks.push(["线可删(隐藏)且不渲染", got2.indexOf("sep:u1") < 0 && got2.indexOf("sep:d1") < 0]);
  checks.push(["删线后项不重排", eq(got2, got.filter((t) => t !== "sep:u1" && t !== "sep:d1"))]);
  checks.push(["下一个用户线 token 递增", R.ctxNextSepToken(got) === "sep:u2"]);
  cfg.group.hidden = ["sep:d1", "sep:d2", "sep:d3", "sep:u1"];
  checks.push(["全删线不报错", ids(M.methods.ctxItems.call(vm, "group")).every((t) => t.indexOf("sep:") < 0)]);
}

// ---- 8. D7: 次级为空(全隐藏/全移走)不渲染「更多操作」父项
{
  const vmAllHidden = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.slice(), hidden: [], sub: { order: R.DEFAULT_CTX_LAYOUT.member.sub.order.slice(), hidden: R.DEFAULT_CTX_LAYOUT.member.sub.order.slice() } } });
  checks.push(["次级全隐藏 -> 无父项", ids(M.methods.ctxItems.call(vmAllHidden, "member")).indexOf("sub-more") < 0]);
  checks.push(["次级全隐藏 -> 次级渲染空", M.methods.ctxSubItems.call(vmAllHidden, "member").length === 0]);
  const vmMovedOut = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.slice().concat(R.DEFAULT_CTX_LAYOUT.member.sub.order.filter((t) => t.indexOf("sep:") < 0)), hidden: [], sub: { order: [], hidden: [] } } });
  checks.push(["次级全移走 -> 无父项", ids(M.methods.ctxItems.call(vmMovedOut, "member")).indexOf("sub-more") < 0]);
  const vmGateOff = vmWith(null, { skip_check_menu: false });
  checks.push(["门控关不计入次级可见(无 gate 项时父项仍在)", ids(M.methods.ctxItems.call(vmGateOff, "member")).indexOf("sub-more") >= 0]);
  const vmSepOnly = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.slice(), hidden: [], sub: { order: R.DEFAULT_CTX_LAYOUT.member.sub.order.slice(), hidden: R.DEFAULT_CTX_LAYOUT.member.sub.order.filter((t) => t.indexOf("sep:") < 0) } } });
  checks.push(["次级只剩线 -> 无父项(线是结构不撑入口)", ids(M.methods.ctxItems.call(vmSepOnly, "member")).indexOf("sub-more") < 0]);
}

// ---- 9. 未知 id 容忍(换版本不丢布局): 幽灵项忽略; sep token 一等公民(格式合法即渲染)
{
  const vm = vmWith({ group: { order: ["ghost-item", "resume", "sep:u9"], hidden: [] } });
  const got = ids(M.methods.ctxItems.call(vm, "group"));
  checks.push(["未知项 id 忽略", got.indexOf("ghost-item") < 0]);
  checks.push(["合法 sep token 原位数渲染(D10 一等公民)", got.indexOf("sep:u9") === 1]);
  checks.push(["未知 id 不影响其余(补尾按定义序)", got[0] === "resume" && eq(got.slice(2), R.DEFAULT_CTX_LAYOUT.group.order.filter((t) => t !== "resume"))]);
  checks.push(["总数 = 默认 + 用户线", got.length === R.DEFAULT_CTX_LAYOUT.group.order.length + 1]);
  const vmBad = vmWith({ group: "not-dict" });
  checks.push(["支级畸形回落默认", eq(ids(M.methods.ctxItems.call(vmBad, "group")), R.DEFAULT_CTX_LAYOUT.group.order)]);
}

// ---- 10. 门控串联: flags 关 = v-if 不渲染(槽位在布局里保留)
{
  const vmOff = vmWith(null, { skip_check_menu: false, qb_traffic_enabled: false });
  checks.push(["skip_check 门控关不渲染", ids(M.methods.ctxItems.call(vmOff, "group")).indexOf("skip_check") < 0]);
  checks.push(["qb-traffic 门控关不渲染", ids(M.methods.ctxItems.call(vmOff, "group")).indexOf("qb-traffic") < 0]);
  const merged = R.ctxMergeLayout("group", null);
  checks.push(["门控关槽位仍在布局", merged.order.indexOf("skip_check") >= 0 && merged.order.indexOf("qb-traffic") >= 0]);
  const vmOn = vmWith(null, { skip_check_menu: true, qb_traffic_enabled: true });
  checks.push(["门控开即渲染", ids(M.methods.ctxItems.call(vmOn, "group")).indexOf("skip_check") >= 0 && ids(M.methods.ctxItems.call(vmOn, "group")).indexOf("qb-traffic") >= 0]);
}

// ---- 11. 结构项防嵌套: sub-more 进次级用户序不渲染(不可嵌套)
{
  const vm = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.filter((t) => t !== "sub-more"), hidden: [], sub: { order: ["sub-more", "queue-top"], hidden: [] } } });
  checks.push(["次级不渲染 submenu 父项", ids(M.methods.ctxSubItems.call(vm, "member")).indexOf("sub-more") < 0]);
}

// ---- 12. 动态 label 与置灰 title
{
  /* 计划 26-10-20-0145: 四支的 启动/停止/删除 已统一为「动词 + 灰色 N 个种子」——
   * label 里不再有 scope 词(批量/该种子/整组/整剧/整集), 于是 episode 支不再按 scope 变文案,
   * 整剧/整集两支渲染出的 label + note 必须**逐字相同**(这正是本轮的验收点)。 */
  const vmEp = stubVm();
  const ep = M.methods.ctxItems.call(vmEp, "episode");
  checks.push(["episode scope=ep 文案", ep[0].label === "启动" && ep[1].label === "停止" && ep[ep.length - 1].label === "删除…"]);
  const vmShow = stubVm({ menu: { visible: true, key: null, hash: null, episode: { hashes: ["H1"], scope: "show" } } });
  const epShow = M.methods.ctxItems.call(vmShow, "episode");
  checks.push(["整集/整剧文案与 scope 无关", eq(ep.map((i) => i.label + "|" + i.note), epShow.map((i) => i.label + "|" + i.note))]);
  const grp = M.methods.ctxItems.call(stubVm(), "group");
  checks.push(["组删除文案不再出现辅种名词", grp[grp.length - 1].label === "删除…"]);
  const sub = M.methods.ctxSubItems.call(stubVm(), "member");
  const ss = sub.filter((i) => i.id === "super-seeding")[0];
  checks.push(["超级做种开关态文案(关->开)", ss.label === "开启超级做种"]);
  const vmGated = stubVm({ reannounceMenuGate: () => ({ ok: false, title: "目标全部非活跃" }) });
  const gated = M.methods.ctxItems.call(vmGated, "group").filter((i) => i.id === "reannounce")[0];
  checks.push(["置灰态 is-gated + title", gated.gated === true && gated.title === "目标全部非活跃"]);
  const okItem = M.methods.ctxItems.call(stubVm(), "group").filter((i) => i.id === "reannounce")[0];
  checks.push(["可用态 title 恒空串(非 null)", okItem.gated === false && okItem.title === ""]);
}

// ---- 14. 动词族灰色后缀(计划 26-10-20-0145 D1/D3)
{
  /* 只有 启动/停止/删除 三项带 note(值 = ctxSeedCount + " 个种子"); 其余项一律空 —
   * note 空字符串时模板 v-if 不渲染 span, 所以"没给 note"与"给了空串"在渲染层等价,
   * 第 15 条用 items 全表扫一遍防"顺手给别的项也挂后缀"。 */
  const VERBS = ["resume", "pause", "delete"];
  let bad = [];
  for (const b of R.CTX_BRANCHES) {
    const items = M.methods.ctxItems.call(stubVm(), b);
    for (const it of items) {
      const want = VERBS.indexOf(it.id) >= 0;
      if (want && it.note !== "42 个种子") bad.push(b + "/" + it.id + "=" + JSON.stringify(it.note));
      if (!want && it.note) bad.push(b + "/" + it.id + " 不该有后缀");
    }
  }
  checks.push(["四支 12 个动词项各带「N 个种子」后缀且其余项无后缀", bad.length === 0 ? true : bad.join(", ")]);
  const seps = M.methods.ctxItems.call(stubVm(), "multi").filter((i) => i.kind === "sep");
  checks.push(["分隔线项 note 恒空(不炸模板)", seps.every((i) => i.note === "")]);
}

// ---- 16. 动态 submenu「转移到」(计划 26-10-31-0306 T6): 父项走注册表(布局可定制), 子项由 vm 单点供给
{
  const sent = [{ id: "transfer:QB2", kind: "item", label: "QB2", act: () => {} }];
  const vmProv = stubVm({ ctxTransferMenuItems: () => sent });
  const par = M.methods.ctxItems.call(vmProv, "multi").filter((i) => i.id === "transfer")[0];
  checks.push(["transfer 父项渲染且子项来自 vm 单点", !!par && par.kind === "submenu" && par.subName === "transfer" && par.subItems === sent]);
  checks.push(["四支各有一个 transfer 父项", ["multi", "episode", "member", "group"].every((b) => M.methods.ctxItems.call(vmProv, b).filter((i) => i.id === "transfer").length === 1)]);
  const vmNo = stubVm();
  const bare = M.methods.ctxItems.call(vmNo, "group").filter((i) => i.id === "transfer")[0];
  checks.push(["无供给方时子项空数组(父项仍在)", !!bare && bare.kind === "submenu" && Array.isArray(bare.subItems) && bare.subItems.length === 0]);
  // D7 只管注册表次级: multi 支的 advanced 次级为空, 不得压掉 transfer 父项(空态在子面板里给)
  checks.push(["multi 支 advanced 空不压 transfer 父项", ids(M.methods.ctxItems.call(stubVm(), "multi")).indexOf("transfer") >= 0]);
  // 不可嵌套: 用户把 transfer 拖进次级用户序也不渲染
  const vmNest = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.filter((t) => t !== "transfer"), hidden: [], sub: { order: ["transfer", "queue-top"], hidden: [] } } });
  checks.push(["次级不渲染 transfer 父项", ids(M.methods.ctxSubItems.call(vmNest, "member")).indexOf("transfer") < 0]);
  // 定制一等公民: transfer 可经 web.ctx_menu 隐藏(槽位保留)
  const vmHide = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.slice(), hidden: ["transfer"], sub: { order: R.DEFAULT_CTX_LAYOUT.member.sub.order.slice(), hidden: [] } } });
  const mergedHide = R.ctxMergeLayout("member", { member: { order: R.DEFAULT_CTX_LAYOUT.member.order.slice(), hidden: ["transfer"] } });
  checks.push(["transfer 可经布局隐藏且槽位保留", ids(M.methods.ctxItems.call(vmHide, "member")).indexOf("transfer") < 0 && mergedHide.order.indexOf("transfer") >= 0]);
}

// ---- 13. ctxRun 分派: 调注册表 act 并透传 vm
{
  let seen = null;
  const vm = stubVm();
  const item = { id: "x", kind: "item", act: (v) => { seen = v; } };
  M.methods.ctxRun.call(vm, item);
  checks.push(["ctxRun 调 act 且透传 vm", seen === vm]);
  M.methods.ctxRun.call(vm, null);
  M.methods.ctxRun.call(vm, { id: "y", kind: "sep" });
  checks.push(["ctxRun 对空/sep 静默", seen === vm]);
}

// ---- 14. 静态名成对(W4 定制面板用): label 是函数 => labelText 必须给(面板没有菜单上下文)
{
  const bad = [];
  for (const branch of R.CTX_BRANCHES) {
    for (const level of [0, 1]) {
      for (const d of R.ctxDefsOf(branch, level)) {
        if (typeof d.label === "function" && !(typeof d.labelText === "string" && d.labelText)) bad.push(branch + "/" + d.id);
      }
    }
  }
  checks.push([bad.length === 0 ? "动态文案项都有静态名" : "动态文案项缺静态名: " + bad.join(","), bad.length === 0]);
  // 静态名不许与动态文案的空壳同形(占位符型 labelText 在面板里会露出 "undefined")
  const shells = [];
  for (const branch of R.CTX_BRANCHES) {
    for (const d of R.ctxDefsOf(branch, 0).concat(R.ctxDefsOf(branch, 1))) {
      if (typeof d.labelText === "string" && d.labelText.indexOf("undefined") >= 0) shells.push(d.id);
    }
  }
  checks.push([shells.length === 0 ? "静态名不含未填占位" : "静态名含占位: " + shells.join(","), shells.length === 0]);
}

// ---- 17. key 字段逐条对账(计划 26-11-12-0344 §05 映射表钉死): key = 引用的 shortcuts 注册表
//      shortcut id; 「不映射」四项(limits/skip_check/transfer/sub-more)不给 key 字段; 「空位」
//      两项(super-seeding/share-limits, 注册表 def:"")key 照填 —— 默认不显示, 绑键后自动出现
const EXPECT_KEY = {
  multi: { resume: "act-resume", pause: "act-pause", reannounce: "act-reannounce", recheck: "act-recheck", skip_check: null, limits: null, move: "edit-move", meta: "act-meta", export: "export-torrent", transfer: null, delete: "act-delete" },
  episode: { resume: "act-resume", pause: "act-pause", reannounce: "act-reannounce", "open-path": "act-open-folder", transfer: null, delete: "act-delete" },
  member: { resume: "act-resume", pause: "act-pause", reannounce: "act-reannounce", info: "act-detail", limits: null, move: "edit-move", rename: "edit-rename", meta: "act-meta", recheck: "act-recheck", skip_check: null, export: "export-torrent", "open-path": "act-open-folder", transfer: null, "sub-more": null, delete: "act-delete" },
  group: { resume: "act-resume", pause: "act-pause", reannounce: "act-reannounce", recheck: "act-recheck", skip_check: null, limits: null, move: "edit-move", meta: "act-meta", export: "export-torrent", "open-path": "act-open-folder", "qb-traffic": "open-qb-traffic", transfer: null, delete: "act-delete" },
};
const EXPECT_SUB_KEY = {
  member: { "queue-top": "queue-top", "queue-up": "queue-up", "queue-down": "queue-down", "queue-bottom": "queue-bottom", "super-seeding": "super-seeding", "force-start": "force-start", "auto-tmm": "auto-tmm", "share-limits": "share-limits", "copy-name": "copy-name", "copy-hash": "copy-hash" },
};
{
  const bad = [];
  const audit = (branch, defs, wantMap, tag) => {
    for (const d of defs) {
      if (d.kind === "sep") continue;
      const want = wantMap && wantMap[d.id] !== undefined ? wantMap[d.id] : undefined;
      if (want === undefined) { bad.push(tag + d.id + " 缺期望映射(新增项? 同步 §05 表与 EXPECT_KEY)"); continue; }
      if ((d.key || null) !== want) bad.push(tag + d.id + " key=" + JSON.stringify(d.key || null) + " want=" + JSON.stringify(want));
      if (d.key && !window.__SHORTCUT_DEFS.some((it) => it.id === d.key)) bad.push(tag + d.id + " key 引用不存在的 shortcut id: " + d.key);
    }
  };
  for (const b of R.CTX_BRANCHES) audit(b, R.CTX_ITEM_DEFS[b], EXPECT_KEY[b], b + "/");
  for (const b of Object.keys(R.CTX_SUB_ITEM_DEFS)) audit(b, R.CTX_SUB_ITEM_DEFS[b], EXPECT_SUB_KEY[b], b + "(sub)/");
  checks.push([bad.length === 0 ? "key 字段逐条对账 §05(引用存在/不映射无 key/空位照填)" : "key 对账失败: " + bad.join("; "), bad.length === 0]);
}

// ---- 18. 键帽渲染(计划 26-11-12-0344 S2): kbd 字段经 kbShortcutDisplay 现算(I1), 空串不产出
{
  const find = (arr, id) => arr.filter((i) => i.id === id)[0];
  const vm = stubVm();
  const items = M.methods.ctxItems.call(vm, "member");
  const sub = M.methods.ctxSubItems.call(vm, "member");
  const grp = M.methods.ctxItems.call(vm, "group");
  checks.push(["绑定项键帽现算(resume -> S)", find(items, "resume").kbd === "S"]);
  checks.push(["次级绑定项键帽(copy-name -> Shift + C)", find(sub, "copy-name").kbd === "Shift + C"]);
  checks.push(["danger 项键帽照常显示(D5, reannounce -> Shift + A)", find(items, "reannounce").kbd === "Shift + A"]);
  checks.push(["qb-traffic 键帽仍标(scope 口径差声明, Ctrl + \\)", find(grp, "qb-traffic").kbd === "Ctrl + \\"]);
  checks.push(["不映射项无 kbd 字段(limits)", !("kbd" in find(items, "limits"))]);
  checks.push(["空位项默认无 kbd 字段(share-limits def:'')", !("kbd" in find(sub, "share-limits"))]);
  checks.push(["sep 渲染对象无 kbd 字段", !("kbd" in find(items, "sep:d1"))]);
  // 改绑即时跟随(I1): window.AQB_KEYS.apply = 设置键位面板「即时试用稿」同一单点 —— 草稿胜出
  // 模板基准; 显式禁用(空串)键帽隐藏; 空位绑键后键帽出现
  window.AQB_KEYS.apply({ schema_version: 1, template: "aqb-default", overrides: { "act-resume": "KeyX", "copy-name": "", "share-limits": "KeyL" } });
  const items2 = M.methods.ctxItems.call(stubVm(), "member");
  const sub2 = M.methods.ctxSubItems.call(stubVm(), "member");
  checks.push(["改绑后键帽即时跟随(resume -> X)", find(items2, "resume").kbd === "X"]);
  checks.push(["显式禁用(空串)键帽隐藏(copy-name)", !("kbd" in find(sub2, "copy-name"))]);
  checks.push(["空位绑键后键帽出现(share-limits -> L)", find(sub2, "share-limits").kbd === "L"]);
  window.AQB_KEYS.apply(null); // 回滚试用稿, 不污染后续电池场景
}

console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length, failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_ctx_menu_template_consumes_registry():
    """模板消费守阵(W3 + 2026-10-22 骨架单点): 一条骨架消费注册表 + 子面板结构

    W3 起 ctx-menus.html 的项集从静态逐项直写改为注册表单点消费; 2026-10-22(issue
    26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup)起**渲染骨架本身**也收成一条 ——
    四支各一份 `.ctx-item` 骨架(5 份, 其中 4 份逐字同)合并为 `ctxItems(ctxMenuKind())`
    单 v-for, 支名改由 menu.js::ctxMenuKind() 单点给出。本守阵钉住合并后的形态, 防两种回潮
    (回潮 = 四支人肉奇偶复发, 即 pitfall ctx-menu-branch-parity 的 root cause):
      1. 支名只许走 `ctxMenuKind()`: 模板里出现 `ctxItems('multi')` 这类字面量就是"四支各一份"
         的开端(字面量要分四支, 分四支就要四份骨架);
      2. 行菜单根块里 `.ctx-item` 骨架恰 2 份(一级项 + 次级面板项) —— 给项加属性只改这两处,
         多一份 = 有人又按支抄了一遍;
      3. submenu 父项结构: has-sub + ctx-caret + 子面板 v-for 消费 `it.subItems`(子项由注册表
         渲染层就地解析 —— 2026-10-31 计划 26-10-31-0306 T6 起与动态「转移到」子面板共用一条
         骨架, 面板名走 it.subName)+ CTX-05/06 交互三件(openSub/scheduleSubClose/toggleSub,
         收起语义在 menu.js, 模板必须挂上) + 钳位状态消费(subFlip/subTop);
      4. 行菜单段不得再出现逐项 @click 分派(ctxAct/actTorrent/actEpisode/ctxDelete/… 直写)——
         项级唯一允许 ctxRun(it), 父项级唯一允许 toggleSub。
    """
    with open(_CTX_MENUS_TPL, encoding="utf-8") as f:
        tpl = f.read()
    row = tpl[:tpl.index("<!-- 表头右键菜单")]  # 只取行右键菜单根块, 排除表头/文件优先级/抽屉菜单

    # 1. 支名单点(字面量 = 四支各一份骨架的开端)
    assert "ctxItems(ctxMenuKind())" in row, (
        "ctx-menus.html 行菜单未 v-for 消费 ctxItems(ctxMenuKind()) —— 支名必须来自"
        " menu.js::ctxMenuKind() 单点(四支各写一份 ctxItems('<支>') = 骨架分家, pitfall ctx-menu-branch-parity)"
    )
    for name in ("multi", "episode", "member", "group"):
        assert f"ctxItems('{name}')" not in row and f'ctxItems("{name}")' not in row, (
            f"ctx-menus.html 出现支名字面量 ctxItems('{name}') —— 支名只许走 ctxMenuKind()"
            f"(字面量回潮 = 四支各一份骨架, 同族缺陷复发)"
        )

    # 2. 骨架份数: 一级项 + 次级面板项(共 2); 「更多操作」父项恰 1
    n_item = row.count('class="ctx-item"')
    assert n_item == 2, (
        f"行菜单根块有 {n_item} 份 .ctx-item 骨架 —— 只允许 2 份(一级项 + 次级面板项);"
        f" 多出来的是按支抄的骨架(issue 26-10-20-2231 已合并, 别再分家)"
    )
    assert row.count('class="ctx-item has-sub"') == 1, "「更多操作」父项骨架应恰 1 份(has-sub)"

    # 3. 子面板结构(CTX-05/06 交互 + 钳位消费; D7 下次级空时注册表不出父项, 面板恒有内容)。
    #    2026-10-31(计划 26-10-31-0306 T6)起子面板两种质料共用一条骨架: 「更多操作」(advanced)
    #    与「转移到」(transfer, 动态目标列表)—— 子项内容由注册表渲染层就地解析成 it.subItems,
    #    子面板名走 it.subName(state.js subMenu: "" | "advanced" | "transfer"), 模板不再区分质料。
    assert "it.subItems" in row, "子面板未消费 it.subItems(子项由注册表渲染层就地解析, 模板不区分质料)"
    assert "subMenu === it.subName" in row, "子面板开合判据未走 it.subName(动态子面板与「更多操作」共用骨架)"
    assert "has-sub" in row and "ctx-caret" in row, "缺 submenu 父项结构(has-sub/ctx-caret)"
    for call in ("openSub(it.subName", "scheduleSubClose()", "toggleSub(it.subName", "keepSub()"):
        assert call in row, f"子面板缺交互 {call}(CTX-05 收起语义在 menu.js, 模板必须挂上)"
    assert "subFlip" in row and "subTop" in row, \
        "子面板缺钳位状态消费(flip-x / top; _subFitViewport 钳位结果要有绑定)"

    # 4. 逐项 @click 直写回潮拦截(项级唯一 ctxRun, 父项级唯一 toggleSub)
    for handler in re.findall(r'@click(?:\.stop)?="([^"]+)"', row):
        assert handler.startswith("ctxRun(") or handler.startswith("toggleSub("), (
            f"行菜单段出现逐项 @click 直写 {handler} —— 回退静态直写 = 四支人肉奇偶复发"
            f"(pitfall ctx-menu-branch-parity); 分派归注册表 act, 模板只调 ctxRun(it)"
        )


def test_ctx_menu_registry_node_battery():
    """node 真跑注册表 + 合并语义电池(无 node 静默跳过, 不引入 skip)"""
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_CTX_MENU_BATTERY, _CTX_MENU_JS, _SHORTCUTS_JS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"ctx_menu node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"ctx_menu 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_ctx_menu_key_fields_reconcile_shortcut_registry():
    """key 字段对账(python 静态面, 计划 26-11-12-0344 S2/§05): 菜单侧 key 引用必须落在注册表

    node 电池(§17)已把 §05 映射表逐条钉死; 本测试是 python 侧的对账兜底(不依赖 node):
      1. 两条注册表里每个 key: 引用的 shortcut id 必须存在于 shortcuts.js 注册表(_registry 解析);
      2. 「不映射」四项(limits/skip_check/transfer/sub-more, 计划 §05)不得给 key 字段;
      3. 其余非 sep 项一律带 key(§05 表内没有"可给可不给"的中间态 —— 新增项漏给 key 在这里红);
      4. key 落点总数 == 44(multi 8 + episode 5 + member 一级 11 + group 10 + 次级 10, §05 表口径)。
    """
    from web_shortcuts_support import _registry

    with open(_CTX_MENU_JS, encoding="utf-8") as f:
        text = f.read()
    reg_text = text[text.index("const CTX_ITEM_DEFS = {"):text.index("const DEFAULT_CTX_LAYOUT")]
    reg_ids = {r["id"] for r in _registry()}

    no_key_ids = {"limits", "skip_check", "transfer", "sub-more"}  # §05「不映射」四项
    keys = []
    for chunk in reg_text.split('{ id: "')[1:]:
        item_id = chunk.split('"', 1)[0]
        if item_id.startswith("sep:"):
            continue
        m = re.search(r'key: "([^"]+)"', chunk)
        if item_id in no_key_ids:
            assert not m, f"「{item_id}」是 §05 不映射项, 不得给 key 字段(拿到键位显示会误导: 界面/端点与注册表条目不同)"
        elif m:
            assert m.group(1) in reg_ids, (
                f"「{item_id}」的 key={m.group(1)} 不在 shortcuts.js 注册表里 —— 渲染层查不到条目,"
                "键帽恒空串(死引用); 改名/退役 shortcut 时必须同步 §05 映射"
            )
            keys.append(m.group(1))
        else:
            assert False, f"「{item_id}」无 key 字段也不在 §05 不映射清单里 —— 新增项漏映射(同步 §05 表)"
    assert len(keys) == 44, (
        f"key 落点 {len(keys)} != §05 表口径 44(multi 8 + episode 5 + member 一级 11 + group 10 + 次级 10)"
        " —— 逐条对账以计划 26-11-12-0344 §05 映射审计表为准"
    )


def test_ctx_custom_panel_wiring():
    """设置页「WebUI」卡接线守阵(W4): 卡片注册 + 分区分支 + 定制块结构 + 三 manifest + 样式

    定制块是**客户端块**(分区本身不进 schema), 与「快捷键」卡同款: 少写一处就静默消失
    (卡片在但点进去空白 / 点得进去但样式裸奔 / 样式在但方法没 mixin), pytest 与
    node --check 都看不见 —— 逐点钉住:
      1. config_hub.js: 卡片注册(key=webui) + hubNow 元信息 + hubGo 进分区复位 + hubRestore 认它;
      2. settings-detail.html: v-else-if 分支 + 四支 tab(v-for ctxBranchList) + 一级/次级两个
         固定区(D17) + 跳检开关绑 cmSkipCheck(D6 迁入);
      3. app.js: AQB_CTX_CUSTOM mixin(漏了整块面板方法全 undefined);
      4. 三份 manifest: ctx_menu_custom.js 在 ctx_menu.js 之后、app.js 之前(合并语义复用);
      5. console_hub.css: .ctx-custom-* 样式段在(三皮肤同吃, 漏了面板裸奔)。
    """
    hub = read_shared("config_hub.js")
    assert re.search(r'key: "webui"', hub), "config_hub.js 未注册「WebUI」卡(首页看不到入口)"
    assert 'this.hub.view === "webui"' in hub, "hubNow 缺 webui 分支(页头/面包屑拿不到标题)"
    assert 'if (key === "webui") this.cmPanelEnter()' in hub, "hubGo 未在进入时复位定制面板(tab 残留)"
    assert 'v === "webui"' in hub, "hubRestore 不认 webui(刷新后回不到定制页)"

    with open(os.path.join(STATIC_ROOT, "shared", "tpl", "settings-detail.html"), encoding="utf-8") as f:
        detail = f.read()
    assert "hub.view === 'webui'" in detail, "settings-detail.html 缺 hub.view === 'webui' 分支(点进去空白)"
    m = re.search(r"<template v-else-if=\"hub\.view === 'webui'\">(.*?)</template>\s*(?:<!--|$)", detail, re.S)
    assert m, "webui 分区块切不出来(结构变了? 同步本守阵)"
    blk = m.group(1)
    assert "v-for=\"b in ctxBranchList\"" in blk, "四支 tab 未由 ctxBranchList 驱动(D15)"
    assert "v-for=\"sec in cmSections\"" in blk, "两个固定区未由 cmSections 驱动(D17: 同一张表渲染两次, 不写两份)"
    assert 'class="ctx-custom-sec"' in blk and "ctx-custom-sec-hd" in blk, "定制块缺区标题结构(一级/次级)"
    with open(os.path.join(STATIC_ROOT, "shared", "ctx_menu_custom.js"), encoding="utf-8") as f:
        cust = f.read()
    assert cust.count("level: 0, title:") == 1 and cust.count("level: 1, title:") == 1, \
        "cmSections 必须正好两个区(一级 / 次级「更多操作」)"
    # 26-10-20-2231: 开关收敛为 <aq-switch>, 回调以 prop 形式传方法引用(:on-change,
    # 不再内联 @change + $event.target.checked) —— 判据随之从 "cmSetSkipCheck(" 改成 prop 绑定。
    assert "cmSkipCheck" in blk and ':on-change="cmSetSkipCheck"' in blk, \
        "跳检开关未绑 cmSkipCheck(D6 迁入的开关)"
    assert 'ctxCust.branch = b.key' in blk, "tab 点击未切 ctxCust.branch"
    for call in (
        "cmRows(cmBranch, sec.level)", "cmMoveStep(", "cmMoveLevel(", "cmToggleHidden(", "cmAddSep(", "cmDelSep(",
        "cmResetBranch("
    ):
        assert call in blk, f"定制块缺方法接线 {call}(面板会有按钮但点了不动)"

    with open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8") as f:
        app_js = f.read()
    assert "app.mixin(window.AQB_CTX_CUSTOM)" in app_js, "app.js 未注入 AQB_CTX_CUSTOM(面板方法全 undefined)"

    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/ctx_menu_custom.js" in scripts, f"{ui} 清单缺 ctx_menu_custom.js(面板按钮点了报错)"
        i_reg = scripts.index("/shared/ctx_menu.js")
        i_cust = scripts.index("/shared/ctx_menu_custom.js")
        i_app = scripts.index("/shared/app.js")
        assert i_reg < i_cust < i_app, (
            f"{ui} 装载序错误(ctx_menu.js < ctx_menu_custom.js < app.js): {i_reg}/{i_cust}/{i_app} —— "
            "定制块要用 REG 的合并语义, 排在它前面 = 运行期 undefined"
        )

    css = read_shared("console_hub.css")
    for cls in (".ctx-custom-tab", ".ctx-custom-row", ".ctx-custom-sec", ".ctx-custom-empty", ".ctx-custom-tag"):
        assert cls in css, f"console_hub.css 缺 {cls}(面板裸奔/不可读)"


def test_ctx_custom_write_shape_passes_config_contract():
    """契约闭环守阵(W5): 定制面板真写路径 → 后端 validate_config 必须认

    前端与后端对"合法布局"各有一套认定(JS 合并语义 / python 形状校验), 两边漂移的形态
    极隐蔽: 面板照常能点、保存照常 200, 只是下次启动读到"未知键"或"必须是字符串数组"时
    整段被拒 —— 用户会觉得"我的定制自己消失了"。故在 node 里用真 vm 桩跑**面板的方法**
    (不是手搓一份布局), 把写出来的东西直接喂给后端校验器:
      1. 只写动过的那一支(其余支不落盘 —— 换版本时未动过的支仍能自动补尾/收新项);
      2. 层键集合与校验器认的 _CTX_BRANCH_KEYS / _CTX_LAYER_KEYS 逐字一致;
      3. 整份布局过 validate_config 零错误;
      4. 语义四项: 隐藏留槽位 / 跨层双向 / 用户线 token 形如 sep:uN / 同层换位生效。
    """
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_CTX_WRITE_PROBE, _CTX_MENU_JS, _CTX_CUSTOM_JS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"定制面板写路径探针跑挂: {proc.stderr.strip()}"
    rep = json.loads(proc.stdout.strip().splitlines()[-1])
    lay = rep["layout"]

    assert list(lay) == ["member"], f"面板只动了一支却写了 {sorted(lay)} —— 未动过的支不该落盘(会冻住它们的默认布局)"

    from auto_qb.config.validation import validate_config
    from auto_qb.config.validation.sections import _CTX_BRANCH_KEYS, _CTX_LAYER_KEYS

    assert set(rep["topKeys"]) == _CTX_BRANCH_KEYS, (
        f"面板写的支级键 {rep['topKeys']} != 后端认的 {sorted(_CTX_BRANCH_KEYS)} —— "
        "两端各认一套键: 保存会 400(或更糟: 校验放宽后存进读不出来的键)"
    )
    assert set(rep["subKeys"]) == _CTX_LAYER_KEYS, f"面板写的次级键 {rep['subKeys']} != 后端认的 {sorted(_CTX_LAYER_KEYS)}"
    assert validate_config({"config": {"web": {"ctx_menu": lay}}}) == [], ("面板真写路径产出的布局过不了后端校验 —— 用户点得动、保存被拒(或反过来)")

    member = lay["member"]
    assert "info" in member["hidden"] and "info" in member["order"], "隐藏项必须留在 order 里(槽位保留, 勾回来才归位)"
    assert "sep:d2" in member["hidden"] and "sep:d2" in member["order"], "默认线隐藏同款留槽位"
    assert "rename" not in member["order"] and "rename" in member["sub"]["order"], "跨层移动没有双向生效(一级 -> 次级)"
    assert rep["userSeps"] == ["sep:u1"], f"用户线 token 不合 sep:uN 口径: {rep['userSeps']}"
    assert member["order"][0] == "pause", f"同层 ↑↓ 换位没生效: {member['order'][:3]}"

    # ---- R5#28: 拖拽落点/删线/恢复默认 —— 写回 order 语义与后端 _CTX_LAYER_KEYS 契约 ----
    drops = rep["drops"]
    d_same_later = drops["sameLater"]
    assert set(d_same_later) == _CTX_BRANCH_KEYS and set(
        d_same_later["sub"]
    ) == _CTX_LAYER_KEYS, ("拖拽写回的支级/次级键集合与后端 _CTX_BRANCH_KEYS/_CTX_LAYER_KEYS 不一致 —— 面板点得动、保存被拒")
    assert d_same_later["order"][:5] == ["pause", "reannounce", "sep:d1", "resume",
                                         "info"], (f"同层向后落点没回退一格: {d_same_later['order'][:5]}(from<row.idx 应插到目标行前一格)")
    assert drops["sameLaterDragCleared"] is True, "落完拖拽态没清(ctxCust.drag/over 残留会让下一次落点误判)"
    assert drops["sameEarlier"]["order"][:2] == ["info",
                                                 "resume"], (f"同层向前落点没原位插入表头: {drops['sameEarlier']['order'][:2]}")
    cross = drops["crossInsert"]
    assert cross["order"][:5] == ["resume", "pause", "reannounce", "sep:d1",
                                  "queue-top"], (f"跨层插入没按目标行 idx 落位: {cross['order'][:5]}(跨层不回退)")
    assert "queue-top" not in cross["sub"]["order"] and cross["sub"]["order"][0] == "queue-up", (
        "跨层插入没把 queue-top 从次级摘除(同一目标两层并存 = 重复渲染)"
    )
    assert drops["tailSub"]["sub"]["order"][-1] == "rename" and "rename" not in drops["tailSub"]["order"], (
        "cmDropTail 跨层追加没把 rename 追到次级表尾"
    )
    assert drops["tailTop"]["order"][-1] == "resume" and drops["tailTop"]["order"][0] == "pause", (
        "cmDropTail 同层追加没把 resume 追到一级表尾"
    )
    assert "sep:u1" in drops["delSepAdded"], "cmAddSep 没产出 sep:u1(删线用例的输入不成立)"
    assert "sep:u1" not in drops["delSep"]["order"] and "sep:u1" not in drops["delSep"]["hidden"], (
        "cmDelSep 删线后 order/hidden 两处都该无残迹"
    )
    assert drops["resetMatchesDefault"] is True, "cmResetBranch 没把两层布局回写为默认(定制残留会赖在配置里)"
    assert validate_config({"config": {
        "web": {
            "ctx_menu": {
                "member": drops["crossInsert"]
            }
        }
    }}) == [], ("拖拽写回的布局过不了后端校验 —— 用户拖得动、保存被拒")


def test_ctx_menu_wiring():
    """接线守阵: 三份 manifest 成对登记 + 装载序 menu.js < ctx_menu.js < app.js + mixin 行 + 双挂载面"""
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/ctx_menu.js" in scripts, f"{ui} 清单缺 ctx_menu.js(注册表加载不上 = 菜单渲染空)"
        i_menu = scripts.index("/shared/menu.js")
        i_ctx = scripts.index("/shared/ctx_menu.js")
        i_app = scripts.index("/shared/app.js")
        assert i_menu < i_ctx < i_app, (
            f"{ui} 装载序错误(menu.js < ctx_menu.js < app.js): {i_menu}/{i_ctx}/{i_app} —— "
            "app.js 末尾要读 window.AQB_CTX_MENU, 排在它之后 = mixin 注入 undefined"
        )
    with open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8") as f:
        app_js = f.read()
    assert "app.mixin(window.AQB_CTX_MENU)" in app_js, "app.js 未注入 AQB_CTX_MENU(整块功能静默消失)"
    with open(_CTX_MENU_JS, encoding="utf-8") as f:
        reg = f.read()
    assert re.search(r"window\.AQB_CTX_MENU_REG = \{", reg), "ctx_menu.js 缺 AQB_CTX_MENU_REG 数据挂载面"
    assert re.search(r"window\.AQB_CTX_MENU = \{", reg), "ctx_menu.js 缺 AQB_CTX_MENU mixin 挂载面"
    # mixin 面只放 methods(数据/纯函数在 REG 面, 与 drawer_templates.js 同范式)
    assert "methods: {" in reg and "ctxItems(branch)" in reg and "ctxSubItems(branch)" in reg and "ctxRun(it)" in reg
