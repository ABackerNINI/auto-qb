"""test_webui_static_r4_addtorrent 测试计划: 存量评审 R4 static 主题清池 P04 —— add_torrent.js 域
行为修复回归 + node 电池(2 修复 + 4 补测)

## 测试计划(每个测试函数一条)
- test_r4_add_submit_gate_prelock_and_reset: R5#130(major) 修复回归 —— submitAddTorrent 提交闸
  前置: 落点预检网络往返窗口内 addSubmitting 已置位(修复前该窗口恒 false, 双击即并发提交)、
  预检取消 return 复位、FileReader 读失败异常照旧向上传播且复位、双击并发(读文件窗口内第二次
  submitAddTorrent 被 addCanSubmit 闸挡下)恰好一次 POST /api/torrents/add、成功回执关窗且复位
- test_r4_add_mkdir_receipt_created: R5#131 修复回归 —— dirMkdir 用回执 created 跳新目录
  (后端 /api/fs/mkdir 回执只有 {created, existed}, 旧代码 r.path 恒 undefined 恒留旧路径,
  新建文件夹后不会跳进新目录): 正常创建与幂等已存在两条回执都断言 loadDir 落到 created,
  输入框清空/busy 复位/ok toast 文案带新目录名; mkdir 失败不跳目录 + error toast + busy 复位
- test_r4_add_relocate_gate_vm_battery: R5#139(major) 落点预检关键分支(照 test_tf_open_flow_vm_probe
  的 node 真 vm 桩范式, 与 test_web_relocate.py 的字符串锚互补): 后端 cls==="confirm" 弹「落点确认」
  (verdict 行表: 落点提示/请求路径/实际落点/目标卷剩余 GiB 换算) + 确认放行后提交载荷逐字段核对
  (files_b64 去 dataURL 前缀/urls 逐行 trim/save_path/category/tags/paused 取反/四开关透传);
  confirm+弹窗取消 = 预检 false 零提交; 非 confirm(cls==="ok")与回执失败 = 放行不弹窗;
  预检抛 auth = false 且零 error toast(401 由 _logout 收口); 网络异常 = 放行; 全角逗号
  U+FF0C 标签口径五面一致(addTagList 拆分/addTagCurrent 尾段/addTagFiltered 剔除/pickAddTag
  追加/提交载荷多签, issue 26-11-08-1620, 与 dialogs.js submitMgrTags/metaAddNewTags 同口径)
- test_r4_add_esc_stack_battery: R5#141 Esc 逐层退栈(FIX-07) —— 目录浏览器层最优先(dirBrowse 开着
  时 cat/tag 菜单同开只收目录浏览器)、其次分类/标签下拉两菜单同收且 Hi 复位、其次路径面板、
  全关才关窗; addSubmitting=true 时 closeAddTorrent 拒绝误关(回执等待期退栈不可关窗)。
  按 node 电池逐层桩断言; 真浏览器多层渲染留给后续变体阶段 e2e
- test_r4_add_combo_keydown_battery: R5#143 五个自绘下拉共用键盘导航本体 —— IME 组词守卫
  (isComposing/keyCode 229 零接管)、ArrowDown/ArrowUp 取模环绕(尾→首/首→尾)、关层方向键先开层
  (openOnArrow 双形态: cat/tag 开, 保存路径面板不接管)、Enter 选中高亮项/enterFallback 落地
  (onEnter 优先于 onPick、空串仅 ctx 带 onEnter 时放行 = 无分类 R5#132, null 不落地、
  无 enterFallback 不吃回车)、Esc 只收面板(stopPropagation 冒泡交退栈链, 未开时零动作)
- test_r4_add_dnd_ingest_battery: R5#142 DND 进料分支 —— _addIngestFiles 同名同大小去重(纯重复
  toast「已在列表」/混合新增不误报)、非 .torrent 忽略(零开窗零入列 + warn toast)、混合进料忽略
  计数 toast、未开窗先开窗再填(先清空后 push, 两文件都在); _addIngestLinks uri-list 注释行
  (# 开头)按行过滤、追加不覆盖已输入、纯非链接文本零动作、未开窗先开窗并展开链接域;
  _addDragDrop 分流(空 FileList 走链接通道)

加载口径: add_torrent.js 整文件 eval(window 桩), 方法经 window.AQB_ADD.methods 挂载面取出后
Object.assign 到最小状态 vm —— 方法体之间的 this 互调与真实例等价(与
test_transfer_flow_confirm::test_tf_open_flow_vm_probe 同范式); addCanSubmit 等 computed 挂
getter 真算(this.addCanSubmit 不能是函数 truthy)。FileReader/KeyboardEvent 在 node 无 DOM,
按方法体裸名引用契约给全局桩/合成事件对象。无 node 静默跳过(与既有 node 电池同口径)。
"""

import os

from test_webui_static_r4_node_batteries import _assert_battery, _run_probe
from webui_helpers import STATIC_ROOT

_ADD_JS = os.path.join(STATIC_ROOT, "shared", "add_torrent.js")

# 公共桩面: add_torrent.js 整文件 eval + 最小状态 vm(真方法 + computed getter + 交互面桩) --------
_COMMON_PRELUDE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // add_torrent.js
const M = window.AQB_ADD.methods;
const C = window.AQB_ADD.computed || {};

function makeVm(over) {
  const vm = {
    // 添加对话框状态(与 state.js data 对齐的最小集)
    addOpen: false, addSubmitting: false,
    addFiles: [], addUrls: "", addShowUrls: false,
    addSavePath: "", addCategory: "", addTags: "",
    addStart: false, addSkipCheck: false, addSequential: false, addFirstLast: false, addTmm: false,
    addCatMenu: false, addTagMenu: false, addCatHi: -1, addTagHi: -1,
    addPathPop: false, addPathHi: -1,
    dirBrowse: { open: false, path: "", parent: "", roots: [], dirs: [], loading: false, error: "", newName: "", busy: false },
    viewMode: "groups", singles: [], torrents: [], decoratedGroups: [],
    // 交互面桩
    apiCalls: [], toasts: [], modalCfg: null, confirmRes: null, cmdResult: null,
    waitCalls: [], hiScrolls: [], apiReply: {}, apiShouldThrow: null,
    toast(text, kind, ms) { vm.toasts.push({ text, kind, ms: ms || 0 }); },
    api(path, options) {
      vm.apiCalls.push([path, options]);
      if (vm.apiShouldThrow) return Promise.reject(vm.apiShouldThrow);
      if (vm.apiReply[path]) return Promise.resolve(vm.apiReply[path]);
      if (path.indexOf("/api/fs/dirs?path=") === 0) {  // dirs 回显请求路径(loadDir 落袋可断言)
        const p = decodeURIComponent(path.slice("/api/fs/dirs?path=".length));
        return Promise.resolve({ path: p, parent: "", roots: [], dirs: [] });
      }
      return Promise.resolve({ cmd_id: "c1" });
    },
    waitCmd(id, ms) { vm.waitCalls.push([id, ms]); return Promise.resolve(vm.cmdResult); },
    _openModal(cfg) { vm.modalCfg = cfg; return Promise.resolve(vm.confirmRes); },
    _popBlurCancel() {}, _fitAddPop() {},
  };
  Object.assign(vm, M);  // 真方法(this=vm, 方法体互调与真实例等价)
  for (const k of Object.keys(C)) Object.defineProperty(vm, k, { get: () => C[k].call(vm) });  // computed 真算
  vm._hiScroll = (ref) => { vm.hiScrolls.push(ref); };  // DOM 桩: 滚动跟随只记录
  Object.assign(vm, over || {});
  return vm;
}
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
/* FileReader 桩: submitAddTorrent 方法体按裸名 new FileReader()(走全局作用域), node 无 DOM 按契约给桩。
 * __fail -> onerror(reject); hold 模式挂起等人工放行(双击并发窗口)。 */
let readerHold = null;  // { held: [{reader, file}] }
global.FileReader = class {
  readAsDataURL(f) {
    if (f && f.__fail) { queueMicrotask(() => this.onerror && this.onerror(new Error("read fail"))); return; }
    if (readerHold) { readerHold.held.push({ reader: this, file: f }); return; }
    const b64 = (f && f.__b64) || "QUJD";
    queueMicrotask(() => { this.result = "data:application/x-bittorrent;base64," + b64; this.onload && this.onload(); });
  }
};
"""

_IIFE_OPEN = "(async () => {\n"

_IIFE_CLOSE = r"""
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));

})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#130 修复回归: submitAddTorrent 提交闸前置 + 各提前返回路径复位 ----------------------------
_SUBMIT_GATE_BODY = r"""
const releaseHold = () => {
  for (const h of readerHold.held) {
    h.reader.result = "data:application/x-bittorrent;base64," + ((h.file && h.file.__b64) || "QUJD");
    h.reader.onload();
  }
};

// ---- 1. 闸前置: 落点预检网络往返窗口内 addSubmitting 已置位(修复前该窗口恒 false) ----
{
  const vm = makeVm();
  vm.addSavePath = "/downloads/a";
  vm.addFiles = [{ name: "Ubuntu.torrent", size: 1 }];
  vm.cmdResult = { ok: true, truth: { cls: "confirm", reasons: [], requested_path: "/downloads/a", actual_path: "" } };
  let resolveGate = null;
  const gatePromise = new Promise((res) => { resolveGate = () => res({ cmd_id: "g1" }); });
  vm.api = (path, options) => {
    vm.apiCalls.push([path, options]);
    if (path === "/api/relocate/precheck-add") return gatePromise;  // 挂起 = 网络往返进行中
    return Promise.resolve({ cmd_id: "c1" });
  };
  const done = vm.submitAddTorrent();
  await Promise.resolve();
  ok("预检已投出(往返进行中)", vm.apiCalls.length === 1 && vm.apiCalls[0][0] === "/api/relocate/precheck-add");
  ok("闸前置: 预检网络往返窗口内 addSubmitting 已置位(修复前恒 false, 双击即并发提交)", vm.addSubmitting === true);
  vm.confirmRes = null;  // 用户在落点确认弹窗点取消
  resolveGate();
  await done;
  ok("预检取消: 提前 return 复位闸", vm.addSubmitting === false);
  ok("预检取消: 零提交", vm.apiCalls.every((c) => c[0] !== "/api/torrents/add"));
}

// ---- 2. 双击并发: 读文件窗口内第二次 submitAddTorrent 被闸挡下, 恰好一次 POST ----
{
  const vm = makeVm();
  vm.addSavePath = "";  // 空 savePath 跳过预检(直达读文件段)
  vm.addFiles = [{ name: "A.torrent", size: 1, __b64: "QUE=" }, { name: "B.torrent", size: 2, __b64: "QkI=" }];
  vm.cmdResult = { ok: true };
  readerHold = { held: [] };
  const first = vm.submitAddTorrent();
  await Promise.resolve(); await Promise.resolve();  // 推进到逐文件 FileReader 挂起
  ok("读文件窗口内 addCanSubmit 已为假(闸落下来了)", vm.addCanSubmit === false);
  await vm.submitAddTorrent();  // 双击第二次
  ok("双击第二次被闸挡下(零预检零提交)", vm.apiCalls.length === 0);
  releaseHold();
  readerHold = null;
  await first;
  ok("双击并发: /api/torrents/add 恰好一次", vm.apiCalls.filter((c) => c[0] === "/api/torrents/add").length === 1);
  ok("提交完成闸复位", vm.addSubmitting === false);
  ok("成功回执关窗", vm.addOpen === false);
}

// ---- 3. FileReader 读失败: 异常照旧向上传播(保留原行为), 闸复位 ----
{
  const vm = makeVm();
  vm.addSavePath = "";
  vm.addFiles = [{ name: "Bad.torrent", size: 1, __fail: true }];
  let err = null;
  await vm.submitAddTorrent().catch((e) => { err = e; });
  ok("读文件失败: 异常向上传播(不吞)", !!err);
  ok("读文件失败: 闸复位(读文件窗口内闸已落, 不复位 = 提交按钮永久锁死)", vm.addSubmitting === false);
}
"""

_NODE_SUBMIT_GATE_PROBE = _COMMON_PRELUDE + _IIFE_OPEN + _SUBMIT_GATE_BODY + _IIFE_CLOSE

# R5#131 修复回归: dirMkdir 用回执 created 跳新目录 --------------------------------------------
_MKDIR_RECEIPT_BODY = r"""
// 1. 正常创建: 回执 {created, existed:false} -> loadDir 落到 created(修复前 r.path 恒 undefined)
{
  const vm = makeVm();
  vm.dirBrowse = { open: true, path: "/downloads", parent: "", roots: [], dirs: [], loading: false, error: "", newName: "新目录", busy: false };
  vm.apiReply["/api/fs/mkdir"] = { created: "/downloads/新目录", existed: false };
  await vm.dirMkdir();
  ok("mkdir 后跳进回执 created 的新目录(修复前 r.path 恒 undefined 恒留旧路径)", vm.dirBrowse.path === "/downloads/新目录");
  ok("dirs 请求带新目录 query", vm.apiCalls.some((c) => c[0] === "/api/fs/dirs?path=" + encodeURIComponent("/downloads/新目录")));
  ok("输入框清空 + busy 复位", vm.dirBrowse.newName === "" && vm.dirBrowse.busy === false);
  ok("ok toast 文案带新目录名", vm.toasts.some((t) => t.kind === "ok" && t.text.indexOf("新目录") >= 0));
}

// 2. 幂等已存在回执({created, existed:true})同样跳进该目录
{
  const vm = makeVm();
  vm.dirBrowse = { open: true, path: "/downloads", parent: "", roots: [], dirs: [], loading: false, error: "", newName: "dup", busy: false };
  vm.apiReply["/api/fs/mkdir"] = { created: "/downloads/dup", existed: true };
  await vm.dirMkdir();
  ok("幂等已存在回执同样跳进该目录", vm.dirBrowse.path === "/downloads/dup");
}

// 3. mkdir 失败: 不跳目录, error toast, busy 复位
{
  const vm = makeVm();
  vm.dirBrowse = { open: true, path: "/downloads", parent: "", roots: [], dirs: [], loading: false, error: "", newName: "x", busy: false };
  vm.apiShouldThrow = new Error("文件夹名不合法");
  await vm.dirMkdir();
  ok("mkdir 失败不跳目录", vm.dirBrowse.path === "/downloads");
  ok("mkdir 失败 error toast", vm.toasts.some((t) => t.kind === "error" && t.text.indexOf("新建文件夹失败") >= 0));
  ok("mkdir 失败 busy 复位", vm.dirBrowse.busy === false);
}
"""

_NODE_MKDIR_RECEIPT_PROBE = _COMMON_PRELUDE + _IIFE_OPEN + _MKDIR_RECEIPT_BODY + _IIFE_CLOSE

# R5#139: 落点预检 _relocateAddGate 关键分支(三路) + 确认放行后提交载荷 ------------------------
_RELOCATE_GATE_BODY = r"""
const CONFIRM_TRUTH = {
  cls: "confirm",
  reasons: [{ text: "整组迁移别名生效中" }],
  requested_path: "/downloads/req",
  actual_path: "/data/alias",
  volume_free: 3 * 1024 * 1024 * 1024,
};

// ---- 1. cls==="confirm" + 弹窗确认: 放行提交, 弹窗行表与提交载荷逐字段核对 ----
{
  const vm = makeVm();
  vm.addSavePath = "/downloads/req";
  vm.addFiles = [{ name: "Ubuntu.torrent", size: 1, __b64: "QUE=" }];
  vm.addUrls = "magnet:?xt=a\n\nhttps://x.example/y  \n";
  vm.addCategory = " linux "; vm.addTags = "iso, x86,";
  vm.addStart = true; vm.addSkipCheck = true; vm.addSequential = true; vm.addFirstLast = true; vm.addTmm = true;
  vm.apiReply["/api/relocate/precheck-add"] = { cmd_id: "g1" };
  vm.cmdResult = { ok: true, truth: CONFIRM_TRUTH };
  vm.confirmRes = { ok: true };  // 用户在落点确认弹窗点「确认添加」
  await vm.submitAddTorrent();
  ok("confirm: 弹「落点确认」", !!vm.modalCfg && vm.modalCfg.title === "落点确认");
  const labels = (vm.modalCfg.verdict || []).map((r) => r.label);
  ok("verdict 行表: 落点提示/请求路径/实际落点/目标卷剩余",
     JSON.stringify(labels) === JSON.stringify(["落点提示", "请求路径", "实际落点", "目标卷剩余"]));
  ok("卷剩余字节换算 GiB", (vm.modalCfg.verdict.find((r) => r.label === "目标卷剩余") || {}).value === "3 GiB");
  const preBody = JSON.parse(vm.apiCalls[0][1].body);
  ok("预检 POST 携带 save_path + name(首个文件名去 .torrent 后缀)",
     preBody.save_path === "/downloads/req" && preBody.name === "Ubuntu");
  ok("预检 waitCmd 20s 上限", vm.waitCalls.some((w) => w[1] === 20000));
  const addCall = vm.apiCalls.find((c) => c[0] === "/api/torrents/add");
  ok("confirm: 确认后提交放行", !!addCall);
  const body = JSON.parse(addCall[1].body);
  ok("载荷 files_b64: 去 dataURL 前缀只留 base64", JSON.stringify(body.files_b64) === JSON.stringify(["QUE="]));
  ok("载荷 urls: 逐行 trim 去空行", JSON.stringify(body.urls) === JSON.stringify(["magnet:?xt=a", "https://x.example/y"]));
  ok("载荷 save_path/category/tags: trim 归一", body.save_path === "/downloads/req" && body.category === "linux"
     && JSON.stringify(body.tags) === JSON.stringify(["iso", "x86"]));
  ok("载荷 paused: 「添加后开始」取反(勾选 = false)", body.paused === false);
  ok("载荷四开关透传", body.skip_checking === true && body.sequential === true
     && body.first_last_piece_prio === true && body.auto_tmm === true);
  ok("提交 waitCmd 不带预检 20s(用默认轮询)", vm.waitCalls.some((w) => w[0] === "c1" && w[1] === undefined));
}

// ---- 2. cls==="confirm" + 弹窗取消: 预检 false, 零提交 ----
{
  const vm = makeVm();
  vm.addSavePath = "/downloads/req";
  vm.addFiles = [{ name: "Ubuntu.torrent", size: 1 }];
  vm.apiReply["/api/relocate/precheck-add"] = { cmd_id: "g1" };
  vm.cmdResult = { ok: true, truth: CONFIRM_TRUTH };
  vm.confirmRes = null;  // 用户点「取消」
  const gate = await vm._relocateAddGate();
  ok("confirm+取消: 预检返回 false", gate === false);
  await vm.submitAddTorrent();
  ok("confirm+取消: 零提交(取消 = 零副作用)", vm.apiCalls.every((c) => c[0] !== "/api/torrents/add"));
}

// ---- 3. 非 confirm(cls==="ok")与回执失败: 放行不弹窗(预检不构成闸门) ----
{
  const vm = makeVm();
  vm.addSavePath = "/downloads/req";
  vm.addFiles = [{ name: "Ubuntu.torrent", size: 1 }];
  vm.apiReply["/api/relocate/precheck-add"] = { cmd_id: "g1" };
  vm.cmdResult = { ok: true, truth: { cls: "ok" } };
  const gate = await vm._relocateAddGate();
  ok("非 confirm(cls=ok): 放行且不弹窗", gate === true && vm.modalCfg === null);
  vm.cmdResult = { ok: false, error: "预检命令失败" };
  ok("回执失败(rec.ok=false): 放行", (await vm._relocateAddGate()) === true);
  vm.cmdResult = null;
  ok("truth 缺失: 放行", (await vm._relocateAddGate()) === true);
}

// ---- 4. 预检抛 auth: false 且零 error toast(401 由 _logout 收口); 网络异常: 放行 ----
{
  const vm = makeVm();
  vm.addSavePath = "/downloads/req";
  vm.addFiles = [{ name: "Ubuntu.torrent", size: 1 }];
  vm.apiShouldThrow = Object.assign(new Error("401"), { auth: true });
  ok("预检抛 auth: 返回 false(不提交)", (await vm._relocateAddGate()) === false);
  ok("auth: 零 error toast(前端不重复报)", !vm.toasts.some((t) => t.kind === "error"));
  vm.apiShouldThrow = new Error("网络断了");
  ok("预检网络异常(非 auth): 放行", (await vm._relocateAddGate()) === true);
}

// ---- (5) 全角逗号 U+FF0C 标签口径(issue 26-11-08-1620): 拆分/尾段/过滤/挑选/载荷五面一致 ----
{
  const vm = makeVm();
  vm.addTags = "iso\uFF0Cx86, hd\uFF0C";  // 全角半角混排
  ok("#1620 addTagList: 全角逗号拆出多个标签(与半角同口径)",
     JSON.stringify(vm.addTagList()) === JSON.stringify(["iso", "x86", "hd"]));
  vm.addTags = "iso\uFF0Cx";
  ok("#1620 addTagCurrent: 尾段按最后一个逗号(含全角)取片段", vm.addTagCurrent() === "x");
  vm.addTags = "iso\uFF0Cx86,";
  vm.addTagOptions = ["iso", "x86", "hd"];
  ok("#1620 addTagFiltered: 全角串已选照常剔除",
     JSON.stringify(vm.addTagFiltered()) === JSON.stringify(["hd"]));
  vm.addTags = "iso\uFF0Cx86";
  vm.pickAddTag("hd");
  ok("#1620 pickAddTag: 全角串上追加不重复",
     JSON.stringify(vm.addTagList()) === JSON.stringify(["iso", "x86", "hd"]));
  // 提交载荷: 全角逗号串不再整串当一个标签提交
  const vm2 = makeVm();
  vm2.addSavePath = "/downloads/req";
  vm2.addFiles = [{ name: "Ubuntu.torrent", size: 1, __b64: "QUE=" }];
  vm2.addTags = "iso\uFF0Cx86";
  vm2.apiReply["/api/relocate/precheck-add"] = { cmd_id: "g1" };
  vm2.cmdResult = { ok: true, truth: { cls: "ok" } };
  await vm2.submitAddTorrent();
  const addCall2 = vm2.apiCalls.find((c) => c[0] === "/api/torrents/add");
  ok("#1620 提交载荷: 全角逗号串拆成多签", !!addCall2
     && JSON.stringify(JSON.parse(addCall2[1].body).tags) === JSON.stringify(["iso", "x86"]));
}
"""

_NODE_RELOCATE_GATE_PROBE = _COMMON_PRELUDE + _IIFE_OPEN + _RELOCATE_GATE_BODY + _IIFE_CLOSE

# R5#141: Esc 逐层退栈(FIX-07) ------------------------------------------------------------------
_ESC_STACK_BODY = r"""
// 1. 目录浏览器层最优先: dirBrowse 与 cat/tag 菜单同开, 只收目录浏览器(退栈顺序)
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.dirBrowse.open = true;
  vm.addCatMenu = true; vm.addTagMenu = true;
  vm.escAddTorrent();
  ok("第一层: 目录浏览器先收(dirBrowse 开着时菜单同开也只收它)", vm.dirBrowse.open === false);
  ok("第一层: 分类/标签菜单不动(留待下一次 Esc)", vm.addCatMenu === true && vm.addTagMenu === true);
  ok("第一层: 对话框保持打开", vm.addOpen === true);
}

// 2. 分类/标签下拉层: 两菜单同收 + Hi 复位, 对话框保持
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.addCatMenu = true; vm.addTagMenu = true; vm.addCatHi = 1; vm.addTagHi = 2;
  vm.escAddTorrent();
  ok("第二层: 分类/标签两菜单同收", vm.addCatMenu === false && vm.addTagMenu === false);
  ok("第二层: 两 Hi 复位", vm.addCatHi === -1 && vm.addTagHi === -1);
  ok("第二层: 对话框保持打开", vm.addOpen === true);
}

// 3. 路径面板层: 收面板 + Hi 复位
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.addPathPop = true; vm.addPathHi = 3;
  vm.escAddTorrent();
  ok("第三层: 路径面板收起 + Hi 复位", vm.addPathPop === false && vm.addPathHi === -1);
  ok("第三层: 对话框保持打开", vm.addOpen === true);
}

// 4. 全关 -> 关窗
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.escAddTorrent();
  ok("第四层: 全关才关窗", vm.addOpen === false);
  ok("第四层: 子层一并关闭", vm.dirBrowse.open === false);
}

// 5. addSubmitting=true: 回执等待期 Esc 拒绝误关
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.addSubmitting = true;
  vm.escAddTorrent();
  ok("提交中 Esc 不关窗(closeAddTorrent 守卫)", vm.addOpen === true);
}
"""

_NODE_ESC_STACK_PROBE = _COMMON_PRELUDE + _IIFE_OPEN + _ESC_STACK_BODY + _IIFE_CLOSE

# R5#143: 五个自绘下拉共用键盘导航本体 -----------------------------------------------------------
_COMBO_KEYDOWN_BODY = r"""
/* 合成 KeyboardEvent 桩(node 无 DOM; 方法体只读 key/isComposing/keyCode 与 preventDefault/stopPropagation) */
const ev = (key, extra) => Object.assign({
  key, isComposing: false, keyCode: 0, prevented: 0, stopped: 0,
  preventDefault() { this.prevented += 1; },
  stopPropagation() { this.stopped += 1; },
}, extra || {});
/* ctx 桩(与 onAddCatKeydown 注入形态同构): 三候选 items + 可注入覆盖 */
function mkCtx(over) {
  const st = { open: false, hi: -1, picks: [], enters: [] };
  const ctx = Object.assign({}, M, {
    items: () => ["a", "b", "c"],
    open: () => st.open,
    setOpen: (v) => { st.open = v; },
    hi: () => st.hi,
    setHi: (v) => { st.hi = v; },
    onPick: (item) => { st.picks.push(item); },
    enterFallback: () => null,
    onEnter: (v) => { st.enters.push(v); },
    listRef: null,        // 非 null 时走 _hiScroll(vm 桩记录)
    openOnArrow: true,
  }, over || {});
  return { ctx, st };
}
const v = makeVm();  // comboKeydown 只经 this 走 _hiScroll(listRef 非空时), 其余全在 ctx

// 1. IME 组词守卫: isComposing / keyCode 229 零接管
{
  const { ctx, st } = mkCtx();
  v.comboKeydown(ctx, ev("ArrowDown", { isComposing: true }));
  ok("IME isComposing: 方向键零接管(不开层不动高亮)", st.open === false && st.hi === -1);
  v.comboKeydown(ctx, ev("Enter", { keyCode: 229 }));
  ok("IME keyCode 229: 回车零接管", st.picks.length === 0 && st.enters.length === 0);
}

// 2. 取模环绕: 尾->首 / 首->尾(面板开着)
{
  const { ctx, st } = mkCtx();
  st.open = true; st.hi = 2;
  v.comboKeydown(ctx, ev("ArrowDown"));
  ok("ArrowDown 环绕: 尾(2)->首(0)", st.hi === 0);
  st.hi = 0;
  v.comboKeydown(ctx, ev("ArrowUp"));
  ok("ArrowUp 环绕: 首(0)->尾(2)", st.hi === 2);
}

// 3. 关层方向键先开层(openOnArrow=true), 首击落位区分上下
{
  const { ctx, st } = mkCtx();
  v.comboKeydown(ctx, ev("ArrowDown"));
  ok("关层 ArrowDown: 先开层且落首项", st.open === true && st.hi === 0);
  st.open = false; st.hi = -1;
  v.comboKeydown(ctx, ev("ArrowUp"));
  ok("关层 ArrowUp: 先开层且落末项", st.open === true && st.hi === 2);
}

// 4. openOnArrow=false(保存路径面板形态): 关层不接管任何键
{
  const { ctx, st } = mkCtx({ openOnArrow: false });
  const e = ev("ArrowDown");
  v.comboKeydown(ctx, e);
  ok("保存路径面板关层: 方向键不接管(preventDefault 不调)", st.open === false && e.prevented === 0);
}

// 5. Enter 选中高亮项 / enterFallback 落地(onEnter 优先) / 空串仅带 onEnter 放行(=无分类), null 不落地
{
  const { ctx, st } = mkCtx();
  st.open = true; st.hi = 1;
  v.comboKeydown(ctx, ev("Enter"));
  ok("Enter: 选中高亮项 items[1]", JSON.stringify(st.picks) === JSON.stringify(["b"]));
  st.open = false; st.hi = -1;
  ctx.enterFallback = () => "手输值";
  v.comboKeydown(ctx, ev("Enter"));
  ok("Enter 无高亮: enterFallback 走 onEnter(优先于 onPick, 不重复走 onPick)",
     JSON.stringify(st.enters) === JSON.stringify(["手输值"]) && st.picks.length === 1 && st.picks[0] === "b");
  ctx.enterFallback = () => "";
  v.comboKeydown(ctx, ev("Enter"));
  ok("enterFallback 空串 + ctx 带 onEnter: 放行落地(=无分类, R5#132; 原「不落地」语义已改)",
     JSON.stringify(st.enters) === JSON.stringify(["手输值", ""]));
  delete ctx.onEnter;  // 无 onEnter 形态(cat/tag/path 三处): 空串回退仍丢弃
  ctx.enterFallback = () => "";
  v.comboKeydown(ctx, ev("Enter"));
  ok("enterFallback 空串 + ctx 无 onEnter: 不落地也不误投 onPick",
     st.enters.length === 2 && st.picks.length === 1 && st.picks[0] === "b");
  ctx.enterFallback = () => null;
  v.comboKeydown(ctx, ev("Enter"));
  ok("enterFallback null: 不落地", st.enters.length === 2);
  delete ctx.enterFallback;
  const e = ev("Enter");
  v.comboKeydown(ctx, e);
  ok("无 enterFallback: 回车不吃(preventDefault 不调)", e.prevented === 0);
}

// 6. Esc 只收面板(stopPropagation 冒泡交 Esc 退栈链), 未开时零动作
{
  const { ctx, st } = mkCtx();
  st.open = true; st.hi = 1;
  const e = ev("Escape");
  v.comboKeydown(ctx, e);
  ok("Esc: 只收面板 + Hi 复位", st.open === false && st.hi === -1);
  ok("Esc: stopPropagation(不直接关对话框, 冒泡交退栈链)", e.stopped === 1);
  const e2 = ev("Escape");
  v.comboKeydown(ctx, e2);
  ok("Esc 面板未开: 零动作", e2.prevented === 0 && e2.stopped === 0 && st.open === false);
}

// 7. 滚动跟随: listRef 非空时 ArrowDown 调 _hiScroll(listRef)
{
  const { ctx } = mkCtx({ listRef: "addCatList" });
  v.comboKeydown(ctx, ev("ArrowDown"));
  ok("listRef 非空: 高亮项滚动跟随被调", JSON.stringify(v.hiScrolls) === JSON.stringify(["addCatList"]));
}
"""

_NODE_COMBO_KEYDOWN_PROBE = _COMMON_PRELUDE + _IIFE_OPEN + _COMBO_KEYDOWN_BODY + _IIFE_CLOSE

# R5#142: DND 进料分支(同名同大小去重 / 非 .torrent 忽略 / uri-list 过滤追加 / 未开窗先开窗) ------
_DND_INGEST_BODY = r"""
const torrent = (name, size) => ({ name, size });
const noLoad = { loadAddOptions() {} };  // 未开窗分支会触发 openAddTorrent->loadAddOptions(候选拉取与本电池无关)

// ---- _addIngestFiles ----

// 1. 同名同大小去重: 已在列表的同名同大小文件不重复入列, 新文件照常补入
{
  const vm = makeVm(noLoad);
  vm.addOpen = true;
  vm.addFiles = [torrent("a.torrent", 100)];
  vm._addIngestFiles([torrent("a.torrent", 100), torrent("b.torrent", 200)]);
  ok("同名同大小去重: 只补新文件 b", JSON.stringify(vm.addFiles.map((f) => f.name)) === JSON.stringify(["a.torrent", "b.torrent"]));
  ok("混合场景(有新增)不误报「已在列表」", vm.toasts.length === 0);
}

// 2. 纯重复: toast「文件已在列表中」
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.addFiles = [torrent("a.torrent", 100)];
  vm._addIngestFiles([torrent("a.torrent", 100)]);
  ok("纯重复零新增入列", vm.addFiles.length === 1);
  ok("纯重复 toast 提示已在列表", vm.toasts.some((t) => t.kind === "warn" && t.text.indexOf("文件已在列表中") >= 0));
}

// 3. 非 .torrent 忽略: 零开窗零入列 + warn toast
{
  const vm = makeVm(noLoad);
  vm._addIngestFiles([torrent("a.txt", 1), torrent("b.zip", 2)]);
  ok("全非种子: 不开窗", vm.addOpen === false);
  ok("全非种子: 零入列", vm.addFiles.length === 0);
  ok("全非种子: warn toast「不是 .torrent 文件」", vm.toasts.some((t) => t.kind === "warn" && t.text.indexOf("不是 .torrent") >= 0));
}

// 4. 混合进料: picks 入列 + 忽略计数 toast
{
  const vm = makeVm(noLoad);
  vm.addOpen = true;
  vm._addIngestFiles([torrent("a.torrent", 1), torrent("x.txt", 1), torrent("y.txt", 1)]);
  ok("混合进料: picks 入列", JSON.stringify(vm.addFiles.map((f) => f.name)) === JSON.stringify(["a.torrent"]));
  ok("混合进料: 忽略计数 toast(2 个)", vm.toasts.some((t) => t.kind === "warn" && t.text.indexOf("2 个") >= 0));
}

// 5. 未开窗先开窗再填: 先 openAddTorrent(清空)再 push —— 两文件都在(顺序错了会被清掉)
{
  const vm = makeVm(noLoad);
  vm._addIngestFiles([torrent("a.torrent", 1), torrent("b.torrent", 2)]);
  ok("未开窗: 先开窗", vm.addOpen === true);
  ok("未开窗: 开窗清空后再填, 两文件都在", JSON.stringify(vm.addFiles.map((f) => f.name)) === JSON.stringify(["a.torrent", "b.torrent"]));
}

// ---- _addIngestLinks ----

// 6. uri-list 注释行过滤(# 标题行不进链接域)
{
  const vm = makeVm(noLoad);
  vm.addOpen = true;
  const dt = { getData: (t) => (t === "text/uri-list" ? "# 从浏览器拖来的标题行\nmagnet:?xt=a\nhttps://x.example/y\n" : "") };
  vm._addIngestLinks(dt);
  ok("uri-list: 注释行按行过滤, 链接逐行入域", vm.addUrls === "magnet:?xt=a\nhttps://x.example/y");
  ok("uri-list: 拖链接自动展开链接域", vm.addShowUrls === true);
}

// 7. 追加不覆盖已输入
{
  const vm = makeVm();
  vm.addOpen = true;
  vm.addUrls = "magnet:?xt=old\n";
  const dt = { getData: () => "magnet:?xt=a\nhttps://x.example/y\n" };
  vm._addIngestLinks(dt);
  ok("追加不覆盖: 旧输入在前, 新链接换行追加", vm.addUrls === "magnet:?xt=old\nmagnet:?xt=a\nhttps://x.example/y");
}

// 8. 纯非链接文本: 零动作
{
  const vm = makeVm(noLoad);
  const dt = { getData: () => "hello world\nnot a link" };
  vm._addIngestLinks(dt);
  ok("纯非链接文本: 零开窗零写入", vm.addOpen === false && vm.addUrls === "" && vm.addShowUrls === false);
}

// 9. 链接进料未开窗: 先开窗再填
{
  const vm = makeVm(noLoad);
  const dt = { getData: () => "magnet:?xt=a" };
  vm._addIngestLinks(dt);
  ok("链接进料未开窗: 先开窗 + 展开链接域 + 内容在", vm.addOpen === true && vm.addShowUrls === true && vm.addUrls === "magnet:?xt=a");
}

// ---- _addDragDrop 分流 ----

// 10. 空 FileList 走链接通道(files 判定 length)
{
  const vm = makeVm(noLoad);
  vm.addOpen = true;
  const dt = { files: [], types: ["text/uri-list"], getData: () => "magnet:?xt=drop" };
  let prevented = 0;
  vm._addDragDrop({ preventDefault() { prevented += 1; }, dataTransfer: dt });
  ok("drop 分流: 空 FileList 走链接通道且 preventDefault(不跳转)", prevented === 1 && vm.addUrls === "magnet:?xt=drop");
}
"""

_NODE_DND_INGEST_PROBE = _COMMON_PRELUDE + _IIFE_OPEN + _DND_INGEST_BODY + _IIFE_CLOSE


def test_r4_add_submit_gate_prelock_and_reset():
    """R5#130(major) 修复回归: 提交闸前置 —— 预检窗口内置位 / 取消与读失败复位 / 双击并发一次 POST"""
    report = _run_probe(_NODE_SUBMIT_GATE_PROBE, _ADD_JS)
    _assert_battery(report, "提交闸前置电池")


def test_r4_add_mkdir_receipt_created():
    """R5#131 修复回归: dirMkdir 用回执 created 跳新目录(旧 r.path 恒 undefined 恒留旧路径)"""
    report = _run_probe(_NODE_MKDIR_RECEIPT_PROBE, _ADD_JS)
    _assert_battery(report, "mkdir 回执电池")


def test_r4_add_relocate_gate_vm_battery():
    """R5#139(major): 落点预检三路(confirm 确认放行+载荷 / 取消零提交 / 非 confirm 放行 / auth)"""
    report = _run_probe(_NODE_RELOCATE_GATE_PROBE, _ADD_JS)
    _assert_battery(report, "落点预检电池")


def test_r4_add_esc_stack_battery():
    """R5#141: Esc 逐层退栈 —— 目录浏览器 > 分类/标签下拉 > 路径面板 > 关窗; 提交中拒绝误关"""
    report = _run_probe(_NODE_ESC_STACK_PROBE, _ADD_JS)
    _assert_battery(report, "Esc 退栈电池")


def test_r4_add_combo_keydown_battery():
    """R5#143 + R5#132: comboKeydown 键盘导航本体 —— IME 守卫 / 取模环绕 / 开层落位 / Enter+fallback(空串仅带 onEnter 放行 = 无分类) / Esc 收面板"""
    report = _run_probe(_NODE_COMBO_KEYDOWN_PROBE, _ADD_JS)
    _assert_battery(report, "下拉键盘导航电池")


def test_r4_add_dnd_ingest_battery():
    """R5#142: DND 进料分支 —— 去重 / 非 .torrent 忽略 / uri-list 过滤与追加 / 未开窗先开窗 / drop 分流"""
    report = _run_probe(_NODE_DND_INGEST_PROBE, _ADD_JS)
    _assert_battery(report, "DND 进料电池")
