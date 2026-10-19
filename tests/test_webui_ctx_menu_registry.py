"""test_webui_ctx_menu_registry 测试计划: 行右键菜单注册表 + 布局解析守阵(计划 26-10-20-0024 W2)

## 背景
ctx-menus.html 四支菜单从静态模板直写改为注册表单点(shared/ctx_menu.js) + 布局数据(web.ctx_menu,
经 /api/webui/flags 下发)驱动。本文件守阵注册表层: ①合并语义(补尾/显隐槽位/跨层双向/
分隔线一等公民/次级空不显示入口/未知 id 容忍/门控串联)node 真跑; ②模板消费形态(W3 起四支
v-for 消费 ctxItems/ctxSubItems, 判据链与子面板交互原样); ③接线守阵(manifest/mixin/挂载面)。

## 测试计划(每个测试函数一条)
- test_ctx_menu_template_consumes_registry: 模板消费守阵(W3) —— 四支判据链原样(与 triggers.js
  variant 口径一致, T3 比对面)+ 各支段 v-for 消费 ctxItems('<支>') + member 支子面板结构
  (has-sub/ctx-caret/ctxSubItems('member')/CTX-05 交互三件/钳位状态) + 逐项 @click 直写回潮
  拦截(唯一允许 ctxRun(it) 与 toggleSub)。W2 期还另有一项「注册表 ↔ 静态模板计数对账」过渡锚
  (52 项 + 14 线逐支相等), W3 模板 v-for 化后如期退役 —— 渲染层零漂移由 e2e menus.spec 接棒,
  注册表层由本文件余两项与 W5 新守阵(注册表 id ↔ 默认布局 ↔ config 契约 ↔ flags 键)接棒
- test_ctx_menu_registry_node_battery: node 真跑电池(无 node 静默跳过, 不引入 skip) —— 默认布局
  硬编码钉(四支 + 次级逐位) + 注册表完整性(id 唯一/形状齐/gate·dyn 合法/次级默认仅 member) +
  无 cfg 渲染 == 默认序 + 补尾 + 隐藏槽位保留与恢复归位 + 跨层双向 + sep 增删与 token 分配 +
  次级空与只剩线不显示父项(D7) + 未知 id 容忍与 sep 一等公民 + 门控两态 + 结构项防嵌套 +
  动态 label + 置灰 title + ctxRun 分派 + 静态名(labelText)成对 + 动词族灰色后缀(四支 12 项,
  计划 26-10-20-0145)
- test_ctx_custom_panel_wiring: 设置页「WebUI」卡接线守阵(W4) —— 卡片注册/hubNow/hubGo 复位/
  hubRestore 认它 + 模板 v-else-if 分支内四支 tab 与两个固定区(D17)+ 跳检开关绑 cmSkipCheck(D6)
  + app.js mixin + 三 manifest 装载序(ctx_menu.js < ctx_menu_custom.js < app.js)+ .ctx-custom-* 样式在
- test_ctx_custom_write_shape_passes_config_contract: 契约闭环守阵(W5) —— node 真跑定制面板的
  **写路径**(真 vm 桩上调 cmToggleHidden/cmMoveLevel/cmAddSep/cmMoveStep), 产出的布局必须
  ①只写动过的那一支 ②支级/次级键集合 == 后端 _CTX_BRANCH_KEYS/_CTX_LAYER_KEYS ③过
  validate_config 零错误 ④隐藏留槽位 / 跨层双向 / 用户线 sep:uN / 同层换位生效
- test_ctx_menu_wiring: 接线守阵 —— 三份 manifest 成对登记 ctx_menu.js 且装载序
  menu.js < ctx_menu.js < app.js; app.js mixin 行在; REG/mixin 双挂载面在文件里
"""
import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_CTX_MENU_JS = os.path.join(STATIC_ROOT, "shared", "ctx_menu.js")
_CTX_CUSTOM_JS = os.path.join(STATIC_ROOT, "shared", "ctx_menu_custom.js")
_CTX_MENUS_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "ctx-menus.html")

# node 探针: 在真 vm 桩上跑**定制面板的写路径**(ctx_menu_custom.js 的 methods), 输出面板
# 实际写回的 ctx_menu 形状 —— 交 python 侧过 validate_config(两端对"合法布局"的认定必须一致)
_NODE_CTX_WRITE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // ctx_menu.js: 注册表 + 合并语义
eval(fs.readFileSync(process.argv[2], "utf8"));   // ctx_menu_custom.js: 面板编辑面
const R = window.AQB_CTX_MENU_REG, C = window.AQB_CTX_CUSTOM;
const vm = {
  cfg: { tree: { config: {} } },
  ctxCust: { branch: "member", drag: null, over: null },
  cfgConfig() { return this.cfg.tree.config; },
  toast() {},
};
const call = (name, ...args) => C.methods[name].call(vm, ...args);
/* 面板方法之间走 this.xxx 互调(cmToggleHidden -> cmDraft -> cmLayout ...), 得把整面方法
 * 挂到桩上 —— 只挂被测的那一个会立刻 "this.cmDraft is not a function" */
for (const k of Object.keys(C.methods)) vm[k] = (...a) => C.methods[k].apply(vm, a);
call("cmToggleHidden", "member", 0, "info");      // 隐藏一项
call("cmToggleHidden", "member", 0, "sep:d2");    // 隐藏一条默认线
call("cmMoveLevel", "member", 0, "rename");       // 一级 -> 「更多操作」
call("cmAddSep", "member", 1);                    // 次级加一条用户线
call("cmMoveStep", "member", 0, "resume", 1);     // ↑↓ 换位
const lay = vm.cfg.tree.config.web.ctx_menu;
console.log(JSON.stringify({
  layout: lay,
  topKeys: Object.keys(lay.member).sort(),
  subKeys: Object.keys(lay.member.sub).sort(),
  userSeps: lay.member.sub.order.filter((t) => t.indexOf("sep:u") === 0),
}));
"""

# node 电池: 加载 ctx_menu.js(global.window 沙箱, 与 _NODE_QB_TRAFFIC_PROBE 同范式),
# 对默认布局与合并语义跑断言电池, 末行输出 JSON 报告。
_NODE_CTX_MENU_BATTERY = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
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

// ---- ① 默认布局硬编码钉(与静态模板四支 + 次级逐位平移; 改此项 = 默认菜单形态漂移, 必须显式 review)
const EXPECT = {
  multi: { order: ["resume", "pause", "reannounce", "sep:d1", "recheck", "skip_check", "limits", "move", "meta", "export", "sep:d2", "delete"], hidden: [], sub: { order: [], hidden: [] } },
  episode: { order: ["resume", "pause", "reannounce", "sep:d1", "open-path", "sep:d2", "delete"], hidden: [], sub: { order: [], hidden: [] } },
  member: { order: ["resume", "pause", "reannounce", "sep:d1", "info", "sep:d2", "limits", "move", "rename", "meta", "sep:d3", "recheck", "skip_check", "export", "open-path", "sep:d4", "sub-more", "sep:d5", "delete"], hidden: [], sub: { order: ["queue-top", "queue-up", "queue-down", "queue-bottom", "sep:s1", "super-seeding", "force-start", "auto-tmm", "share-limits", "sep:s2", "copy-name", "copy-hash", "copy-magnet"], hidden: [] } },
  group: { order: ["resume", "pause", "reannounce", "sep:d1", "recheck", "skip_check", "limits", "move", "meta", "export", "sep:d2", "open-path", "qb-traffic", "sep:d3", "delete"], hidden: [], sub: { order: [], hidden: [] } },
};
for (const b of ["multi", "episode", "member", "group"]) {
  checks.push(["默认布局 " + b, eq(R.DEFAULT_CTX_LAYOUT[b], EXPECT[b])]);
}
let nItem = 0, nSep = 0;
for (const b of ["multi", "episode", "member", "group"]) {
  for (const t of EXPECT[b].order) { if (t.indexOf("sep:") === 0) nSep++; else nItem++; }
}
checks.push(["一级计数 41 项 + 12 线", nItem === 41 && nSep === 12]);
let sItem = 0, sSep = 0;
for (const t of EXPECT.member.sub.order) { if (t.indexOf("sep:") === 0) sSep++; else sItem++; }
checks.push(["次级计数 11 项 + 2 线", sItem === 11 && sSep === 2]);

// ---- ② 注册表完整性
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

// ---- ③ 无 cfg = 默认布局渲染(flags 全开): 渲染 id 序 == 默认 order
{
  const vm = stubVm();
  for (const b of R.CTX_BRANCHES) {
    checks.push([b + " 无 cfg 渲染 == 默认 order", eq(ids(M.methods.ctxItems.call(vm, b)), R.DEFAULT_CTX_LAYOUT[b].order)]);
  }
  checks.push(["member 次级无 cfg 渲染 == 默认 sub order", eq(ids(M.methods.ctxSubItems.call(vm, "member")), R.DEFAULT_CTX_LAYOUT.member.sub.order)]);
}

// ---- ④ 补尾: 用户序只有两项 -> 其余按定义序追加(不丢项)
{
  const vm = vmWith({ member: { order: ["resume", "pause"], hidden: [] } });
  const got = ids(M.methods.ctxItems.call(vm, "member"));
  checks.push(["补尾: 用户序两项打头", got[0] === "resume" && got[1] === "pause"]);
  checks.push(["补尾: 其余按定义序", eq(got.slice(2), R.DEFAULT_CTX_LAYOUT.member.order.slice(2))]);
}

// ---- ⑤ 隐藏槽位保留 + 取消隐藏归位
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

// ---- ⑥ 跨层双向: rename 入次级 / queue-top 入一级; 补尾不得把对层认领的项拽回
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

// ---- ⑦ 分隔线一等公民: 用户添加 / 删除(隐藏)/ token 分配
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

// ---- ⑧ D7: 次级为空(全隐藏/全移走)不渲染「更多操作」父项
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

// ---- ⑨ 未知 id 容忍(换版本不丢布局): 幽灵项忽略; sep token 一等公民(格式合法即渲染)
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

// ---- ⑩ 门控串联: flags 关 = v-if 不渲染(槽位在布局里保留)
{
  const vmOff = vmWith(null, { skip_check_menu: false, qb_traffic_enabled: false });
  checks.push(["skip_check 门控关不渲染", ids(M.methods.ctxItems.call(vmOff, "group")).indexOf("skip_check") < 0]);
  checks.push(["qb-traffic 门控关不渲染", ids(M.methods.ctxItems.call(vmOff, "group")).indexOf("qb-traffic") < 0]);
  const merged = R.ctxMergeLayout("group", null);
  checks.push(["门控关槽位仍在布局", merged.order.indexOf("skip_check") >= 0 && merged.order.indexOf("qb-traffic") >= 0]);
  const vmOn = vmWith(null, { skip_check_menu: true, qb_traffic_enabled: true });
  checks.push(["门控开即渲染", ids(M.methods.ctxItems.call(vmOn, "group")).indexOf("skip_check") >= 0 && ids(M.methods.ctxItems.call(vmOn, "group")).indexOf("qb-traffic") >= 0]);
}

// ---- ⑪ 结构项防嵌套: sub-more 进次级用户序不渲染(不可嵌套)
{
  const vm = vmWith({ member: { order: R.DEFAULT_CTX_LAYOUT.member.order.filter((t) => t !== "sub-more"), hidden: [], sub: { order: ["sub-more", "queue-top"], hidden: [] } } });
  checks.push(["次级不渲染 submenu 父项", ids(M.methods.ctxSubItems.call(vm, "member")).indexOf("sub-more") < 0]);
}

// ---- ⑫ 动态 label 与置灰 title
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

// ---- ⑭ 动词族灰色后缀(计划 26-10-20-0145 D1/D3)
{
  /* 只有 启动/停止/删除 三项带 note(值 = ctxSeedCount + " 个种子"); 其余项一律空 —
   * note 空字符串时模板 v-if 不渲染 span, 所以"没给 note"与"给了空串"在渲染层等价,
   * 第⑮条用 items 全表扫一遍防"顺手给别的项也挂后缀"。 */
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

// ---- ⑬ ctxRun 分派: 调注册表 act 并透传 vm
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

// ---- ⑭ 静态名成对(W4 定制面板用): label 是函数 => labelText 必须给(面板没有菜单上下文)
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

console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length, failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_ctx_menu_template_consumes_registry():
    """模板消费守阵(W3): 四支判据链原样 + 各支 v-for 消费注册表 + member 支子面板结构

    W3 起 ctx-menus.html 四支从静态逐项直写改为注册表单点消费。本守阵钉住替换后的模板
    形态, 防回潮(回潮 = 四支人肉奇偶复发, 即 pitfall ctx-menu-branch-parity 的 root cause):
      1. 四支判据链原样(v-if="menu.multi" / v-else-if="menu.episode" / v-else-if="menu.hash" /
         v-else; 与 triggers.js variant 口径一致, 静态守阵 T3 的比对面);
      2. 每支段内必须 v-for 消费 ctxItems('<支>') —— 项集只能来自注册表单点;
      3. member 支含「更多操作」父项结构: has-sub + ctx-caret + 子面板 v-for 消费
         ctxSubItems('member') + CTX-05/06 交互三件(openSub/scheduleSubClose/toggleSub,
         收起语义在 menu.js, 模板必须挂上)+ 钳位状态消费(subFlip/subTop);
      4. 行菜单段不得再出现逐项 @click 分派(ctxAct/actTorrent/actEpisode/ctxDelete/… 直写)——
         项级唯一允许 ctxRun(it), 父项级唯一允许 toggleSub。
    """
    with open(_CTX_MENUS_TPL, encoding="utf-8") as f:
        tpl = f.read()
    row = tpl[:tpl.index("<!-- 表头右键菜单")]  # 只取行右键菜单根块, 排除表头/文件优先级/抽屉菜单
    anchors = [
        ("multi", 'v-if="menu.multi"'),
        ("episode", 'v-else-if="menu.episode"'),
        ("member", 'v-else-if="menu.hash"'),
        ("group", "<template v-else>"),
    ]
    pos = []
    for name, needle in anchors:
        assert needle in row, f"ctx-menus.html 缺 {name} 支判据链锚点 {needle}(四支结构变了? 同步本守阵)"
        pos.append((name, row.index(needle)))
    for i, (name, p) in enumerate(pos):
        end = pos[i + 1][1] if i + 1 < len(pos) else len(row)
        seg = row[p:end]
        assert f"ctxItems('{name}')" in seg, (f"{name} 支未 v-for 消费注册表 ctxItems('{name}') —— 项集必须来自 ctx_menu.js 单点")
        for handler in re.findall(r'@click(?:\.stop)?="([^"]+)"', seg):
            assert handler.startswith("ctxRun(") or handler.startswith("toggleSub("), (
                f"{name} 支出现逐项 @click 直写 {handler} —— 回退静态直写 = 四支人肉奇偶复发"
                f"(pitfall ctx-menu-branch-parity); 分派归注册表 act, 模板只调 ctxRun(it)"
            )
    # member 支子面板结构(CTX-05/06 交互 + 钳位消费; D7 下次级空时注册表不出父项, 面板恒有内容)
    member_seg = row[pos[2][1]:pos[3][1]]
    assert "has-sub" in member_seg and "ctx-caret" in member_seg, \
        "member 支缺「更多操作」父项结构(has-sub/ctx-caret)"
    assert "ctxSubItems('member')" in member_seg, "member 支子面板未消费 ctxSubItems('member')"
    for call in ("openSub('advanced'", "scheduleSubClose()", "toggleSub('advanced'", "keepSub()"):
        assert call in member_seg, f"member 支子面板缺交互 {call}(CTX-05 收起语义在 menu.js, 模板必须挂上)"
    assert "subFlip" in member_seg and "subTop" in member_seg, \
        "子面板缺钳位状态消费(flip-x / top; _subFitViewport 钳位结果要有绑定)"


def test_ctx_menu_registry_node_battery():
    """node 真跑注册表 + 合并语义电池(无 node 静默跳过, 不引入 skip)"""
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_CTX_MENU_BATTERY, _CTX_MENU_JS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"ctx_menu node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"ctx_menu 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


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
    with open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8") as f:
        hub = f.read()
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
    assert "cmSkipCheck" in blk and "cmSetSkipCheck(" in blk, "跳检开关未绑 cmSkipCheck(D6 迁入的开关)"
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

    with open(os.path.join(STATIC_ROOT, "shared", "console_hub.css"), encoding="utf-8") as f:
        css = f.read()
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
