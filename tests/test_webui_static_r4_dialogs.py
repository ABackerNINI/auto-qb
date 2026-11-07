"""test_webui_static_r4_dialogs 测试计划: 存量评审 R4 static 主题清池 P10 —— dialogs 域(dialogs.js / dialogs_meta.js / dialogs_history.js)行为修复回归 + node 电池(2 修复 + 4 补测)

## 测试计划(每个测试函数一条)

- test_r4_dialogs_meta_chain_battery: R5#140(major) meta 标签/分类编辑对话框行为面 + R5#133 修复回归 ——
  node vm 真跑 openMetaDialog→metaToggleTag/metaSetCategory 全链: 目标锁定(单种子/组级联展开去重/
  空目标早退)、_metaCommonTags 交集方向(双方都有才留)、共同分类与分歧清空、loadMetaOptions 候选
  并回 metaCommonTags(共同携带标签不在候选也不丢)、metaToggleTag 有则删无则加(bulk 载荷 keys/hashes/
  tags 与回执失败交集不动)、metaAddNewTags 半角逗号拆分(全角不支持, 清单外已知项) + 先建后打标、
  metaSetCategory 先建后设链
  (创建 POST 在 bulk 之前)/清除分类空串直投/已存在只设不建/未变化静默零投递、投递载荷逐字段;
  R5#133: metaBusy 在飞时 metaSetCategory 被入口闸拒绝零投递(与 metaToggleTag 同口径), 新分类创建
  POST /api/categories 在途窗口内 metaBusy 已同步置真、第二次调用被拒(闸后同步占闸), metaAddNewTags
  同构占闸(新标签创建 POST /api/tags 在途窗口第二发被拒), 在飞期
  closeMeta 拒绝误关(闸保证保护对仍在途命令不失效), metaBusy 清零后正常关窗
- test_r4_dialogs_meta_enter_empty_battery: R5#132 修复回归 —— 清空输入框后回车的「含清空 = 无分类」
  路径真达: onMetaCatKeydown 的 ctx 带 onEnter 钩子, comboKeydown 对带 onEnter 的 ctx 放行空串回退,
  清空回车 -> onEnter 收到空串 -> metaSetCategory("") -> bulk set_category category="" (清除分类);
  非空手输回车照常提交(先建后设); 高亮项回车走 onPick 单次投递不重复; 已是无分类时清空回车静默
  零投递(不给假反馈); metaBusy 在飞时空串回车被入口闸拒绝(R5#132 x R5#133 交叉)
- test_r4_dialogs_mgr_crud_battery: R5#144 管理对话框 CRUD 行为面 —— node 电池真跑 openMgr(收筛选
  弹层 + 清态 + loadMgr 拉平)、loadMgr 双分支(标签数组字典序 / 分类字典展开成行 + save_path 缺省
  空串 + 字典序)、submitMgrTags 半角逗号批量拆分(全角不支持, 清单外已知项; 空段剔除/成功清草稿重拉/
  空输入 warn 零投递)、
  submitMgrCategory(名称必填/保存路径可空 = payload 无 save_path 键/路径 trim 随投递/成功清双草稿)、
  mgrBusy 在飞双入口拒绝重复投递
- test_r4_dialogs_history_math_battery: R5#147 历史流量弹层聚合数学 —— node 电池喂 historyData 断言
  三档桶: 天档 slice(-30)(标签 MM-DD/条数/首尾桶值)、月档 slice(-12)(按月键聚合/标签 YY-MM/裁旧月)、
  年档按年汇总(标签 YYYY/tip 带「年」)、historyMax/historySummary(up/down/peak=单桶 up+down 最大/
  avg=桶均)、histGranItems 三档清单单点、histMove 悬停索引换算(clientX->viewBox->桶索引 + 双侧
  clamp + 空数据零接管)、histLeave 复位、histHover 悬停态(桶引用/系列点/leftPct/越界 null)、
  histGeom/histViewBox/histXTicks 均匀采样、histPaths/_histArea 面积路径(空数据空串)
- test_r4_dialogs_speed_overlay_battery: R5#146 限速浮层编排 —— node 电池真跑 openSpeedAt(就近弹出
  定位 = 点击锚点 left - SPEED_PAD / 无锚退视口右侧 / 方向归一化 + 匹配方向输入框预聚焦全选 /
  开窗强制重取 /api/speed/mode 并回填主备两组)、openSpeedDialog 旧入口薄包装、closeSpeedDialog 复位、
  submitSpeedDialog 双分支(双成功关窗 + speedOverride 清空重取 / 主速成功备用失败留窗重试并按新
  快照回填)、主速空表单 speedOvReady 闸零投递留窗

加载口径: dialogs 域经 webui_helpers.bundle_file("dialogs.js") 聚合(根 + dialogs_meta.js +
dialogs_history.js 清单序, 与四套皮肤 index.html 装载序一致), eval 后方法经 window.AQB_DIALOGS
挂载面取出 —— 方法体之间的 this 互调与真实例等价; 三单点骨架(_mgrRun/_panelLoad/_postWaitCmd)
走真身, 外部原语(api/waitCmd/toast/遥测记账/$nextTick/_hiScroll)按方法体裸名引用契约打桩, computed
以 defineProperty getter 现算(this.historyBuckets 等链式引用与 Vue 实例同形)。meta 回车电池另 eval
add_torrent.js(comboKeydown 单点, 与四套皮肤同序: add_torrent.js 先于 dialogs 域被 this 互调)。
无 node 静默跳过(与既有 node 电池同口径, 不引入 pytest skip)。
"""

import os

from test_webui_static_r4_node_batteries import _assert_battery, _run_probe
from webui_helpers import STATIC_ROOT, bundle_file

_ADD_JS = os.path.join(STATIC_ROOT, "shared", "add_torrent.js")
_DLGS_JS = bundle_file("dialogs.js")

# 公共桩面: dialogs 域整包 eval + 最小 vm(真方法 + 交互原语桩) ---------------------------------
_COMMON_PRELUDE = r"""
const fs = require("fs");
global.window = { innerWidth: 1000 };
eval(fs.readFileSync(process.argv[1], "utf8"));  // dialogs 域聚合(根 + meta/history 片段)
const D = window.AQB_DIALOGS.methods;
const C = window.AQB_DIALOGS.computed;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const flush = () => new Promise((r) => setImmediate(r));

// 最小 vm: 三单点骨架(_mgrRun/_panelLoad/_postWaitCmd)走真身, 外部原语打桩(方法体裸名引用契约)
function mkVm(over) {
  const vm = {
    posts: [], apiLog: [], toasts: [],
    api: async (url, opt) => {
      const method = (opt && opt.method) || "GET";
      vm.apiLog.push(method + " " + url);
      if (method === "POST") vm.posts.push({ url, body: JSON.parse(opt.body) });
      return {};
    },
    waitCmd: async () => ({ ok: true }),
    toast: (msg, kind, ms) => { vm.toasts.push([msg, kind, ms || 0]); },
    _finishToast: () => {},
    _auditScope: () => {},
    _newCmdStats: (action) => ({ action }),
    _markCmdPatch: () => {},
    _markCmdPost: () => {},
    $nextTick: (fn) => fn(),
  };
  Object.assign(vm, D);
  Object.assign(vm, over || {});
  return vm;
}
const bulkPosts = (vm) => vm.posts.filter((p) => p.url === "/api/torrents/bulk");
const lastBulk = (vm) => bulkPosts(vm).slice(-1)[0].body;
"""

# R5#140 + R5#133: meta 编辑对话框全链 ----------------------------------------------------------
_NODE_META_CHAIN_BODY = r"""
(async () => {
  const vm = mkVm({
    catSrc: { b: {}, a: { save_path: "/x" } },
    tagSrc: ["t2", "t1"],
    memberByHash: new Map([
      ["h1", { tags: ["gamma", "alpha", "shared"], category: "tv" }],
      ["h2", { tags: ["alpha", "shared", "delta"], category: "tv" }],
      ["m1", { tags: ["shared"], category: "movies" }],
      ["m2", { tags: ["alpha"], category: "movies" }],
    ]),
    _findGroup: (k) => (k === "g1" ? { members: [{ hash: "m1" }, { hash: "m2" }] } : null),
    _bulkTargets: () => ({ groupKeys: [], memberHashes: [] }),
    menu: { visible: true },
  });
  vm.api = async (url, opt) => {
    const method = (opt && opt.method) || "GET";
    vm.apiLog.push(method + " " + url);
    if (method === "POST") vm.posts.push({ url, body: JSON.parse(opt.body) });
    if (url === "/api/categories" && method === "GET") return { categories: vm.catSrc };
    if (url.startsWith("/api/tags") && method === "GET") return { tags: vm.tagSrc };
    return { cmd_id: "c1" };
  };

  // ---- openMetaDialog: 单种子目标锁定 + 交集方向 + 候选并回 ----
  D.openMetaDialog.call(vm, "h1");
  ok("openMetaDialog: 先收右键菜单 + 锁定单种子目标 + 开框清态",
     vm.menu.visible === false && vm.metaOpen === true &&
     JSON.stringify(vm.metaTargets) === JSON.stringify({ groupKeys: [], memberHashes: ["h1"] }) &&
     vm.metaBusy === false && vm.metaNewTags === "");
  ok("openMetaDialog: metaCount = 展开去重后的目标数", vm.metaCount === 1);
  ok("openMetaDialog: 共同标签 = 交集(字典序)", JSON.stringify(vm.metaCommonTags) === JSON.stringify(["alpha", "gamma", "shared"]));
  ok("openMetaDialog: 共同分类无分歧(输入框回填)", vm.metaCat === "tv" && vm.metaCatDiff === false && vm.metaCatInput === "tv");
  await flush();
  ok("loadMetaOptions: 分类候选字典序", JSON.stringify(vm.metaCategories) === JSON.stringify(["a", "b"]));
  ok("loadMetaOptions: 标签候选并回共同携带标签(并集字典序; 共同标签不在候选也不丢)",
     JSON.stringify(vm.metaTags) === JSON.stringify(["alpha", "gamma", "shared", "t1", "t2"]));

  // 空目标早退(遮罩下选择被清光的守门)
  vm.metaOpen = false;
  D.openMetaDialog.call(vm, null);
  ok("openMetaDialog: 空目标早退不开框", vm.metaOpen === false);

  // 双种子交集方向: 双方都有才留, 单方独有丢弃
  D.openMetaDialog.call(vm, { groupKeys: [], memberHashes: ["h1", "h2"] });
  ok("双目标: 交集只留双方都有(alpha/shared; gamma/delta 单方独有不留)",
     JSON.stringify(vm.metaCommonTags) === JSON.stringify(["alpha", "shared"]));

  // 组级联展开 + 去重 + 分类分歧清空
  D.openMetaDialog.call(vm, { groupKeys: ["g1"], memberHashes: ["h9", "h1"] });
  ok("组级联: hashes 展开含组员且去重(h9 不在册仍计目标, 计数口径与后端展开一致)", vm.metaCount === 4);
  ok("组级联: 三成员交集为空(h1 与 m1/m2 无公共标签)", JSON.stringify(vm.metaCommonTags) === JSON.stringify([]));
  ok("组级联: 分类分歧 -> 输入框清空待选(diff=true)", vm.metaCat === "" && vm.metaCatDiff === true && vm.metaCatInput === "");

  // ---- metaToggleTag: 有则删无则加 + bulk 载荷 ----
  D.openMetaDialog.call(vm, { groupKeys: [], memberHashes: ["h1", "h2"] });
  await flush();
  await D.metaToggleTag.call(vm, "shared");
  ok("toggle 有则删: remove_tags 载荷(action/keys/hashes/tags 逐字段)",
     lastBulk(vm).action === "remove_tags" && JSON.stringify(lastBulk(vm).keys) === JSON.stringify([]) &&
     JSON.stringify(lastBulk(vm).hashes) === JSON.stringify(["h1", "h2"]) &&
     JSON.stringify(lastBulk(vm).tags) === JSON.stringify(["shared"]));
  ok("toggle 有则删: ok 回执后即时确认(交集摘除)", JSON.stringify(vm.metaCommonTags) === JSON.stringify(["alpha"]));
  await D.metaToggleTag.call(vm, "delta");
  ok("toggle 无则加: add_tags 载荷 + 交集补回并排序",
     lastBulk(vm).action === "add_tags" && JSON.stringify(lastBulk(vm).tags) === JSON.stringify(["delta"]) &&
     JSON.stringify(vm.metaCommonTags) === JSON.stringify(["alpha", "delta"]));
  vm.waitCmd = async () => ({ ok: false, error: "boom" });
  await D.metaToggleTag.call(vm, "alpha");
  ok("toggle 回执失败: 交集不动(即时确认只吃 ok 回执) + cmdFail toast",
     JSON.stringify(vm.metaCommonTags) === JSON.stringify(["alpha", "delta"]) &&
     vm.toasts.some((t) => t[1] === "error" && t[0].includes("移除标签")));
  vm.waitCmd = async () => ({ ok: true });

  // ---- metaAddNewTags: 逗号拆分 + 先建后打标(现状: split 字符类只有半角逗号, 见报告清单外发现) ----
  vm.metaNewTags = " x1 , x2,  ";
  await D.metaAddNewTags.call(vm);
  const tagPost = vm.posts.find((p) => p.url === "/api/tags" && p.body.tags);
  ok("addNewTags: 半角逗号拆分(全角不支持, 清单外已知项) + 空段剔除后先建定义(POST /api/tags)",
     JSON.stringify(tagPost.body.tags) === JSON.stringify(["x1", "x2"]));
  ok("addNewTags: bulk 打标载荷带全部输入段",
     lastBulk(vm).action === "add_tags" && JSON.stringify(lastBulk(vm).tags) === JSON.stringify(["x1", "x2"]));
  ok("addNewTags: 新定义并入候选 + 交集补回 + 草稿清空",
     vm.metaTags.includes("x1") && vm.metaTags.includes("x2") &&
     JSON.stringify(vm.metaCommonTags) === JSON.stringify(["alpha", "delta", "x1", "x2"]) && vm.metaNewTags === "");

  // ---- metaSetCategory: 先建后设链 / 清除 / 已存在 / 未变化 ----
  const catPosts = () => vm.posts.filter((p) => p.url === "/api/categories").length;
  await D.metaSetCategory.call(vm, "anime");
  ok("setCategory 新分类: 先建(POST /api/categories)后设(bulk set_category), 顺序不倒",
     catPosts() === 1 && vm.posts.map((p) => p.url).lastIndexOf("/api/categories") <
       vm.posts.map((p) => p.url).lastIndexOf("/api/torrents/bulk"));
  ok("setCategory: bulk 载荷 category=anime + 目标集合透传",
     lastBulk(vm).action === "set_category" && lastBulk(vm).category === "anime" &&
     JSON.stringify(lastBulk(vm).hashes) === JSON.stringify(["h1", "h2"]));
  ok("setCategory: 成功回执回填输入框", vm.metaCat === "anime" && vm.metaCatInput === "anime" && vm.metaCatDiff === false);
  ok("setCategory: 新分类并回候选(字典序)", JSON.stringify(vm.metaCategories) === JSON.stringify(["a", "anime", "b"]));

  await D.metaSetCategory.call(vm, "");
  ok("setCategory 清除: 空串不建号直接 bulk(零新增创建), 载荷 category 空串",
     catPosts() === 1 && lastBulk(vm).action === "set_category" && lastBulk(vm).category === "");
  ok("setCategory 清除: metaCat 复位为空(= 无分类)", vm.metaCat === "" && vm.metaCatInput === "");

  await D.metaSetCategory.call(vm, "b");
  ok("setCategory 已在候选: 只设不建(零新增创建 POST)", catPosts() === 1 && lastBulk(vm).category === "b");

  const n0 = vm.posts.length;
  await D.metaSetCategory.call(vm, "b");
  ok("setCategory 未变化: 静默返回(零投递, 不给「已设置」的假反馈)", vm.posts.length === n0);

  // ---- metaBusy 闸后同步占闸: 新分类创建的 POST /api/categories 在途窗口, 第二发拒绝(修复前红:
  // 闸只在 _metaBulk/_postWaitCmd 里置真, 创建 await 窗口内二次调用漏闸并发) ----
  {
    let releaseCreate;
    const vmG = mkVm({
      metaTargets: { groupKeys: [], memberHashes: ["h1"] },
      metaCategories: ["a", "b"], metaCat: "tv", metaCatDiff: false, metaCatInput: "tv",
    });
    const gate = new Promise((res) => { releaseCreate = res; });
    vmG.api = async (url, opt) => {
      const method = (opt && opt.method) || "GET";
      if (method === "POST") vmG.posts.push({ url, body: JSON.parse(opt.body) });
      if (url === "/api/categories" && method === "POST") { await gate; return {}; }  // 创建 POST 挂起在途
      return { cmd_id: "c1" };
    };
    const first = D.metaSetCategory.call(vmG, "anime");  // 过闸 -> 占闸 -> 卡在创建 POST
    await flush();
    ok("metaBusy 闸后同步占闸: 新分类创建在途(POST 未回执)时 metaBusy 已置真", vmG.metaBusy === true);
    await D.metaSetCategory.call(vmG, "anime2");  // 第二发: 落在创建 await 窗口内
    ok("metaBusy 闸后同步占闸: 创建在途窗口内第二次调用被拒(零新增创建, 零 bulk)",
       vmG.posts.filter((p) => p.url === "/api/categories").length === 1 && bulkPosts(vmG).length === 0);
    releaseCreate();
    await first;
    await flush();
    ok("metaBusy 闸后同步占闸: 第一发走完先建后设, busy 由既有收口(_postWaitCmd)复位",
       lastBulk(vmG).action === "set_category" && lastBulk(vmG).category === "anime" && vmG.metaBusy === false);
  }

  // ---- metaAddNewTags 同构占闸(增量评审): 新标签创建的 POST /api/tags 在途窗口, 第二发拒绝 ----
  {
    let releaseTags;
    const vmT = mkVm({
      metaTargets: { groupKeys: [], memberHashes: ["h1"] },
      metaTags: [], metaCommonTags: [], metaNewTags: "t1",
    });
    const gate = new Promise((res) => { releaseTags = res; });
    vmT.api = async (url, opt) => {
      const method = (opt && opt.method) || "GET";
      if (method === "POST") vmT.posts.push({ url, body: JSON.parse(opt.body) });
      if (url === "/api/tags" && method === "POST") { await gate; return {}; }  // 创建 POST 挂起在途
      return { cmd_id: "c1" };
    };
    const firstT = D.metaAddNewTags.call(vmT);  // 过闸 -> 占闸 -> 卡在创建 POST
    await flush();
    ok("metaAddNewTags 同构占闸: 新标签创建在途(POST 未回执)时 metaBusy 已置真", vmT.metaBusy === true);
    await D.metaAddNewTags.call(vmT);  // 第二发: 落在创建 await 窗口内
    ok("metaAddNewTags 同构占闸: 创建在途窗口内第二次调用被拒(零新增创建, 零 bulk)",
       vmT.posts.filter((p) => p.url === "/api/tags").length === 1 && bulkPosts(vmT).length === 0);
    releaseTags();
    await firstT;
    await flush();
    ok("metaAddNewTags 同构占闸: 第一发走完先建后打标, busy 由既有收口(_postWaitCmd)复位",
       lastBulk(vmT).action === "add_tags" && vmT.metaBusy === false);
  }

  // ---- R5#133: metaBusy 入口闸(修复前红: 双发并发 set_category + closeMeta 保护失效) ----
  vm.metaBusy = true;
  const n1 = vm.posts.length;
  await D.metaSetCategory.call(vm, "anime");
  ok("R5#133: metaBusy 在飞时 metaSetCategory 被入口闸拒绝(零投递, 与兄弟方法同口径)",
     vm.posts.length === n1);
  await D.metaToggleTag.call(vm, "alpha");
  ok("R5#133: 同口径对照 metaToggleTag 同样拒绝(既有闸, 零投递)", vm.posts.length === n1);
  vm.metaOpen = true;
  D.closeMeta.call(vm);
  ok("R5#133: 在飞期 closeMeta 拒绝误关(闸保证保护对仍在途命令不失效)", vm.metaOpen === true);
  vm.metaBusy = false;
  D.closeMeta.call(vm);
  ok("metaBusy 清零后 closeMeta 正常关窗", vm.metaOpen === false);

  process.stdout.write(JSON.stringify({
    title: "metaChain",
    ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

_NODE_META_CHAIN_PROBE = _COMMON_PRELUDE + _NODE_META_CHAIN_BODY

# R5#132: meta 分类下拉「含清空 = 无分类」回车路径 ------------------------------------------------
_NODE_META_ENTER_BODY = r"""
(async () => {
  eval(fs.readFileSync(process.argv[2], "utf8"));  // add_torrent.js(comboKeydown 单点, 皮肤装载序在 dialogs 域之前)
  const ADD = window.AQB_ADD.methods;
  const ev = (key) => ({ key, preventDefault() { this.prevented = (this.prevented || 0) + 1; }, stopPropagation() {} });
  function mkMetaVm() {
    const vm = mkVm({
      metaOpen: true, metaBusy: false,
      metaCatMenu: false, metaCatHi: -1, metaCatInput: "",
      metaCategories: ["a", "b"], metaCat: "tv", metaCatDiff: false,
      metaCommonTags: [], metaTags: [], metaNewTags: "",
      metaTargets: { groupKeys: [], memberHashes: ["h1"] },
      hiScrolls: [],
    });
    Object.assign(vm, ADD);  // comboKeydown 单点(add_torrent.js 域)并入同一实例, this 互调与真机一致
    vm._hiScroll = (r) => vm.hiScrolls.push(r);
    return vm;
  }

  // ① 清空输入框 + 回车 = 提交「无分类」: 空串回退经 onEnter 落到 metaSetCategory("")
  {
    const vm = mkMetaVm();
    const e = ev("Enter");
    D.onMetaCatKeydown.call(vm, e);
    await flush();
    const b1 = bulkPosts(vm)[0];
    ok("清空回车: 空串回退经 onEnter 直达 metaSetCategory(= 无分类), bulk set_category category 空串",
       !!b1 && b1.body.action === "set_category" && b1.body.category === "");
    ok("清空回车: ok 文案「已执行: 清除分类」", vm.toasts.some((t) => t[0] === "已执行: 清除分类"));
    ok("清空回车: 回车被吃(preventDefault)", e.prevented === 1);
  }

  // ② 非空手输回车: 照常提交(先建后设; onEnter 接管回退分支不破坏非空路径)
  {
    const vm = mkMetaVm();
    vm.metaCatInput = "新分类";
    D.onMetaCatKeydown.call(vm, ev("Enter"));
    await flush();
    ok("非空手输回车: 先建后设不破(创建 POST + bulk set_category 新分类)",
       vm.posts.some((p) => p.url === "/api/categories") && lastBulk(vm).category === "新分类");
  }

  // ③ 高亮项回车: 走 onPick 单次投递(选中路径不吃回退值, 不重复投递)
  {
    const vm = mkMetaVm();
    vm.metaCatMenu = true; vm.metaCatHi = 0;
    D.onMetaCatKeydown.call(vm, ev("Enter"));
    await flush();
    ok("高亮项回车: 只投一次 onPick 选中项(a), 无重复命令",
       bulkPosts(vm).length === 1 && lastBulk(vm).category === "a");
  }

  // ④ 已是无分类(metaCat="" 无分歧)再清空回车: 未变化静默零投递(不给假反馈)
  {
    const vm = mkMetaVm();
    vm.metaCat = ""; vm.metaCatDiff = false;
    D.onMetaCatKeydown.call(vm, ev("Enter"));
    await flush();
    ok("已无分类再清空回车: 未变化静默返回(零投递)", bulkPosts(vm).length === 0);
  }

  // ⑤ metaBusy 在飞: 空串回车被入口闸拒绝(R5#132 x R5#133 交叉, 双击/竞态下不并发第二发)
  {
    const vm = mkMetaVm();
    vm.metaBusy = true;
    D.onMetaCatKeydown.call(vm, ev("Enter"));
    await flush();
    ok("metaBusy 在飞: 空串回车零投递(入口闸先于投递)", bulkPosts(vm).length === 0);
  }

  process.stdout.write(JSON.stringify({
    title: "metaEnterEmpty",
    ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

_NODE_META_ENTER_PROBE = _COMMON_PRELUDE + _NODE_META_ENTER_BODY

# R5#144: 管理对话框 CRUD -----------------------------------------------------------------------
_NODE_MGR_BODY = r"""
(async () => {
  const vm = mkVm({
    tagSrc: ["z", "a", "m"],
    catSrc: { bb: { save_path: "/b" }, aa: {}, cc: { save_path: "" } },
    filterMenu: "tag", mgrOpen: "", mgrBusy: false, mgrLoading: false,
    mgrCategories: [{ name: "旧", save_path: "/old" }], mgrTags: ["旧"],
    mgrNew: { tags: "残留", catName: "残留", catPath: "残留" },
    mgrError: "旧错",
  });
  vm.api = async (url, opt) => {
    const method = (opt && opt.method) || "GET";
    vm.apiLog.push(method + " " + url);
    if (method === "POST") vm.posts.push({ url, body: JSON.parse(opt.body) });
    if (url === "/api/tags" && method === "GET") return { tags: vm.tagSrc };
    if (url === "/api/categories" && method === "GET") return { categories: vm.catSrc };
    return { cmd_id: "c1" };
  };

  // ---- openMgr 清态 + loadMgr 标签分支 ----
  D.openMgr.call(vm, "tag");
  await flush();
  ok("openMgr(tag): 先收筛选弹层 + 置 kind + 清态(列表/草稿/错误位)",
     vm.filterMenu === "" && vm.mgrOpen === "tag" && vm.mgrError === "" &&
     vm.mgrNew.tags === "" && vm.mgrNew.catName === "" && vm.mgrNew.catPath === "");
  ok("openMgr(tag): loadMgr 拉平标签列表(字典序)", JSON.stringify(vm.mgrTags) === JSON.stringify(["a", "m", "z"]));

  // ---- loadMgr 分类分支: 字典展开成行 + 字典序 + save_path 缺省空串 ----
  D.openMgr.call(vm, "category");
  await flush();
  ok("openMgr(category): 打开时清双列表", vm.mgrTags.length === 0);
  ok("loadMgr(category): 字典展开成行(名字字典序 + save_path 缺省空串)",
     JSON.stringify(vm.mgrCategories) === JSON.stringify([
       { name: "aa", save_path: "" }, { name: "bb", save_path: "/b" }, { name: "cc", save_path: "" },
     ]));

  // ---- submitMgrTags: 逗号批量拆分(现状: split 字符类只有半角逗号, 见报告清单外发现) ----
  D.openMgr.call(vm, "tag");  // 回到标签面板: _mgrRun 成功链会按 mgrOpen 分支重拉列表
  await flush();
  vm.mgrNew.tags = " a , b,c,中文, d,, ";
  await D.submitMgrTags.call(vm);
  const tagPost = vm.posts.find((p) => p.url === "/api/tags" && p.body.tags);
  ok("submitMgrTags: 半角逗号拆分(全角不支持, 清单外已知项) + 空段剔除(载荷 tags 逐字段)",
     JSON.stringify(tagPost.body.tags) === JSON.stringify(["a", "b", "c", "中文", "d"]));
  ok("submitMgrTags: 成功后清草稿 + 重拉列表(_mgrRun ok 链)", vm.mgrNew.tags === "" && vm.mgrTags.length === 3);
  ok("submitMgrTags: ok toast 带计数", vm.toasts.some((t) => t[1] === "ok" && t[0].includes("已创建 5 个标签")));

  vm.mgrNew.tags = " ,  ,  ";
  const n0 = vm.posts.length;
  await D.submitMgrTags.call(vm);
  ok("submitMgrTags 空输入: warn toast 零投递", vm.posts.length === n0 && vm.toasts.some((t) => t[0].includes("标签不能为空")));

  // ---- submitMgrCategory: 名称必填 / 保存路径可空 ----
  vm.mgrNew.catName = "  ";
  const n1 = vm.posts.length;
  await D.submitMgrCategory.call(vm);
  ok("submitMgrCategory 空名: warn 零投递", vm.posts.length === n1 && vm.toasts.some((t) => t[0].includes("分类名称不能为空")));

  vm.mgrNew.catName = "纪录片"; vm.mgrNew.catPath = "   ";
  await D.submitMgrCategory.call(vm);
  let catPost = vm.posts.filter((p) => p.url === "/api/categories").pop();
  ok("submitMgrCategory: 路径留空 = 仅建分类(payload 无 save_path 键)", catPost.body.name === "纪录片" && !("save_path" in catPost.body));
  ok("submitMgrCategory: 成功后清双草稿", vm.mgrNew.catName === "" && vm.mgrNew.catPath === "");

  vm.mgrNew.catName = "剧集"; vm.mgrNew.catPath = " /tv/新 ";
  await D.submitMgrCategory.call(vm);
  catPost = vm.posts.filter((p) => p.url === "/api/categories").pop();
  ok("submitMgrCategory: 路径 trim 后随投递", catPost.body.save_path === "/tv/新");

  // ---- busy 闸: 回执等待期双入口拒绝重复投递 ----
  vm.mgrBusy = true;
  const n2 = vm.posts.length;
  vm.mgrNew.tags = "x";
  await D.submitMgrTags.call(vm);
  vm.mgrNew.catName = "y";
  await D.submitMgrCategory.call(vm);
  ok("mgrBusy 在飞: 两个提交入口都拒绝(零投递)", vm.posts.length === n2);
  vm.mgrBusy = false;
  D.closeMgr.call(vm);
  ok("closeMgr: 非在飞正常关窗", vm.mgrOpen === "");

  process.stdout.write(JSON.stringify({
    title: "mgrCrud",
    ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

_NODE_MGR_PROBE = _COMMON_PRELUDE + _NODE_MGR_BODY

# R5#147: 历史流量弹层聚合数学 ------------------------------------------------------------------
_NODE_HISTORY_BODY = r"""
(async () => {
  const vm = mkVm({
    historyOpen: true, historyGran: "day", histHoverIdx: -1,
    fmtSize: (v) => "F" + v,
  });
  const CH = ["historyBuckets", "historyMax", "historySummary", "histGeom", "histViewBox",
    "histTicks", "histXTicks", "histSeries", "histPaths", "histAreaUp", "histAreaDown", "histHover"];
  for (const k of CH) Object.defineProperty(vm, k, { get: () => C[k].call(vm) });

  // 32 行原始日行(时间升序, 与后端 /api/traffic/history 同形):
  //   2022-05-18/19 两天(将被天档 slice(-30) 裁掉) + 2022-05-20 + 2023 两天 + 2024 十二个月行 + 2025-01 十五天
  const rows = [
    { date: "2022-05-18", up: 1, down: 2 },
    { date: "2022-05-19", up: 3, down: 4 },
    { date: "2022-05-20", up: 5, down: 6 },
    { date: "2023-06-08", up: 7, down: 8 },
    { date: "2023-06-10", up: 9, down: 10 },
  ];
  for (let m = 1; m <= 12; m++) rows.push({ date: `2024-${String(m).padStart(2, "0")}-01`, up: 100 + m, down: 50 + m });
  for (let d = 1; d <= 15; d++) rows.push({ date: `2025-01-${String(d).padStart(2, "0")}`, up: d, down: 2 * d });
  vm.historyData = rows;

  // ---- 天档: slice(-30) ----
  const day = vm.historyBuckets;
  ok("天档: 超过 30 行裁到近 30(裁掉最旧两天)", day.length === 30);
  ok("天档: 首桶 = 2022-05-20(标签 MM-DD + tip 全日期 + 原值透传)",
     day[0].label === "05-20" && day[0].tip === "2022-05-20" && day[0].up === 5 && day[0].down === 6);
  ok("天档: 末桶 = 2025-01-15", day[29].label === "01-15" && day[29].tip === "2025-01-15" && day[29].up === 15 && day[29].down === 30);
  ok("histGranItems: 三档清单单点(day/month/year)",
     JSON.stringify(C.histGranItems.call(vm).map((i) => i.v)) === JSON.stringify(["day", "month", "year"]));

  // ---- 月档: 按月键聚合 + slice(-12) ----
  vm.historyGran = "month";
  const mon = vm.historyBuckets;
  ok("月档: 15 个月键裁到近 12(2022-05/2023-06/2024-01 被裁)", mon.length === 12 && mon[0].label === "24-02");
  ok("月档: 首桶 tip 全月键 + 月内求和(2024-02: up 102 down 52)", mon[0].tip === "2024-02" && mon[0].up === 102 && mon[0].down === 52);
  ok("月档: 末桶 = 2025-01(15 个日行按月求和: up 120 down 240)", mon[11].label === "25-01" && mon[11].up === 120 && mon[11].down === 240);

  // ---- 年档: 按年汇总 ----
  vm.historyGran = "year";
  const yr = vm.historyBuckets;
  ok("年档: 四个年份桶(标签 YYYY + tip 带「年」)",
     yr.length === 4 && yr[0].label === "2022" && yr[0].tip === "2022 年" && yr[3].label === "2025");
  ok("年档: 2024 年汇总(12 个月行求和 up 1278 down 678)", yr[2].up === 1278 && yr[2].down === 678);

  // ---- historyMax / historySummary ----
  vm.historyGran = "day";
  ok("historyMax: 桶内 max(up,down) 全局最大(天档 = 112, 2024-12 up), 下限 1", vm.historyMax === 112);
  ok("historySummary: up/down 求和(1419/942)", vm.historySummary.up === 1419 && vm.historySummary.down === 942);
  ok("historySummary: peak = 单桶 up+down 最大(2024-12 = 174)", vm.historySummary.peak === 174);
  ok("historySummary: avg = (up+down)/桶数(2361/30 = 78.7)", Math.abs(vm.historySummary.avg - 78.7) < 1e-9);
  vm.historyGran = "year";
  ok("historyMax: 年档 = 1278(2024 up)", vm.historyMax === 1278);

  // ---- 几何与折线/面积路径 ----
  vm.historyGran = "day";
  const g = vm.histGeom;
  ok("histGeom: 30 桶 bw = (920-80)/30, chartH = 380-46", g.n === 30 && Math.abs(g.bw - 28) < 1e-9 && g.chartH === 334);
  ok("histViewBox: 0 0 920 380", vm.histViewBox === "0 0 920 380");
  ok("histXTicks: 最多 8 个均匀采样(30/8 -> step 4)", vm.histXTicks.length === 8 && vm.histXTicks[0].label === "05-20");
  ok("histTicks: Y 轴 5 档(含 0)", vm.histTicks.length === 5 && vm.histTicks[0].label === "0");
  const p2 = vm.histSeries.up[2];
  ok("histSeries: 槽位中心 x 与按比例 y(第 3 桶 up=9, y 按 historyMax 归一)",
     Math.abs(p2.x - (64 + 2 * 28 + 14)) < 1e-9 &&
     Math.abs(p2.y - (16 + 334 * (1 - 9 / vm.historyMax))) < 1e-9 && p2.v === 9);
  ok("histPaths: M 起笔 + L 连线(两系列)", vm.histPaths.up.startsWith("M ") && vm.histPaths.up.includes(" L ") &&
     vm.histPaths.down.startsWith("M "));
  const area = vm.histAreaUp;
  ok("_histArea: 折线接底边闭合(末点 x / 首点 x / 基线 350.0 / Z 收尾)",
     area.startsWith("M ") && area.endsWith(` L ${(64 + 29 * 28 + 14).toFixed(1)} 350.0 L ${(64 + 14).toFixed(1)} 350.0 Z`));
  ok("histAreaDown: 同构(方法按 key 分派)", vm.histAreaDown.startsWith("M "));

  // ---- 悬停: histMove 索引换算 + 双侧 clamp + histLeave 复位 + histHover 悬停态 ----
  const mkMove = (clientX) => ({ clientX, currentTarget: { getBoundingClientRect: () => ({ left: 0, width: 920 }) } });
  D.histMove.call(vm, mkMove(210));
  ok("histMove: clientX 折算 viewBox 后落桶索引(210 -> 5)", vm.histHoverIdx === 5);
  D.histMove.call(vm, mkMove(0));
  ok("histMove: 左越界 clamp 到 0", vm.histHoverIdx === 0);
  D.histMove.call(vm, mkMove(920));
  ok("histMove: 右越界 clamp 到末桶", vm.histHoverIdx === 29);
  vm.histHoverIdx = 2;
  const hov = vm.histHover;
  const b2 = vm.historyBuckets[2];
  ok("histHover: 桶值 + 系列点 + leftPct(x/920*100)",
     hov.bucket.label === b2.label && hov.bucket.up === b2.up && hov.bucket.down === b2.down &&
     Math.abs(hov.up.x - p2.x) < 1e-9 && Math.abs(hov.up.y - p2.y) < 1e-9 &&
     Math.abs(hov.leftPct - (134 / 920) * 100) < 1e-9);
  vm.histHoverIdx = 30;
  ok("histHover: 越界 null", vm.histHover === null);
  D.histLeave.call(vm);
  ok("histLeave: 复位 -1", vm.histHoverIdx === -1 && vm.histHover === null);

  // ---- 空数据: 三档零桶 + 面积空串 + histMove 零接管 ----
  const vm2 = mkVm({ historyOpen: true, historyGran: "day", histHoverIdx: 7, fmtSize: (v) => "F" + v });
  Object.defineProperty(vm2, "historyBuckets", { get: () => C.historyBuckets.call(vm2) });
  Object.defineProperty(vm2, "histGeom", { get: () => C.histGeom.call(vm2) });
  Object.defineProperty(vm2, "histSeries", { get: () => C.histSeries.call(vm2) });
  Object.defineProperty(vm2, "histPaths", { get: () => C.histPaths.call(vm2) });
  vm2.historyData = [];
  ok("空数据: 三档零桶", vm2.historyBuckets.length === 0);
  ok("空数据: _histArea 空串(不画面积)", D._histArea.call(vm2, "up") === "");
  D.histMove.call(vm2, mkMove(210));
  ok("空数据: histMove 零接管(索引不动)", vm2.histHoverIdx === 7);

  process.stdout.write(JSON.stringify({
    title: "historyMath",
    ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

_NODE_HISTORY_PROBE = _COMMON_PRELUDE + _NODE_HISTORY_BODY

# R5#146: 限速浮层编排 --------------------------------------------------------------------------
_NODE_SPEED_BODY = r"""
(async () => {
  const mkInp = () => ({ focused: 0, selected: 0, focus() { this.focused += 1; }, select() { this.selected += 1; } });
  const mk = (snaps) => {
    const method = (url, opt) => (opt && opt.method) || "GET";
    const vm = mkVm({
      speedOpen: false, speedAt: { left: 0, dir: "up" },
      speedMode: { loaded: false, curveEnabled: false, target: null, current: null, altOn: false, altCurrent: null, error: "" },
      speedOverride: { up: "", down: "", busy: false },
      speedAlt: { up: "", down: "", busy: false },
      modeSnaps: snaps, modeCalls: 0, overridePosts: [], altPosts: [],
      inputs: { "#sp-up": mkInp(), "#sp-down": mkInp() },
      $refs: null,
      fmtLimit: (kib) => (kib ? String(kib) : ""),
    });
    Object.defineProperty(vm, "speedOvReady", { get: () => C.speedOvReady.call(vm) });
    vm.$refs = { speedPop: { querySelector: (sel) => vm.inputs[sel] || null } };
    vm.api = async (url, opt) => {
      vm.apiLog.push(url);
      if (url === "/api/speed/mode") {
        vm.modeCalls += 1;
        return vm.modeSnaps[Math.min(vm.modeCalls - 1, vm.modeSnaps.length - 1)];
      }
      if (method(url, opt) === "POST") {
        const rec = { url, body: JSON.parse(opt.body) };
        vm.posts.push(rec);
        if (url === "/api/speed/override") vm.overridePosts.push(rec.body);
        if (url === "/api/speed/alt") vm.altPosts.push(rec.body);
      }
      return { cmd_id: "c1" };
    };
    return vm;
  };
  const snap = (up, down, aUp, aDown) => ({
    curve_enabled: false, target: null,
    current: { upload_limit: up, download_limit: down },
    alt_on: aUp !== null, alt_current: { upload_limit: aUp, download_limit: aDown },
  });

  // ---- openSpeedAt: 就近弹出定位 + 预聚焦 + 开窗重取回填 ----
  const vm = mk([snap(1024, 2048, 512, 256)]);
  const evUp = { currentTarget: { getBoundingClientRect: () => ({ left: 500 }) } };
  await D.openSpeedAt.call(vm, evUp, "up");
  ok("openSpeedAt: 就近弹出(left = 锚点 left - SPEED_PAD=12) + 方向归一化 + 开层",
     vm.speedAt.left === 488 && vm.speedAt.dir === "up" && vm.speedOpen === true);
  ok("openSpeedAt: 开窗强制重取 /api/speed/mode(不吃缓存)", vm.modeCalls === 1 && vm.speedMode.loaded === true);
  ok("openSpeedAt: 按快照回填主/备两组(KiB/s 字符串)",
     vm.speedOverride.up === "1024" && vm.speedOverride.down === "2048" &&
     vm.speedAlt.up === "512" && vm.speedAlt.down === "256");
  ok("openSpeedAt: 只预聚焦当前方向输入框并全选",
     vm.inputs["#sp-up"].focused === 1 && vm.inputs["#sp-up"].selected === 1 && vm.inputs["#sp-down"].focused === 0);

  const vmD = mk([snap(1024, 2048, 512, 256)]);
  await D.openSpeedAt.call(vmD, { currentTarget: { getBoundingClientRect: () => ({ left: 0 }) } }, "down");
  ok("openSpeedAt(down): 预聚焦下载方向", vmD.inputs["#sp-down"].focused === 1 && vmD.inputs["#sp-up"].focused === 0);

  const vmX = mk([snap(1024, 2048, 512, 256)]);
  await D.openSpeedAt.call(vmX, { currentTarget: { getBoundingClientRect: () => ({ left: 0 }) } }, "weird");
  ok("openSpeedAt: 非 down 一律归一化为 up", vmX.speedAt.dir === "up" && vmX.inputs["#sp-up"].focused === 1);

  // ---- openSpeedDialog 旧入口薄包装(无点击坐标: 锚视口右侧) ----
  const vmN = mk([snap(1, 2, 3, 4)]);
  await D.openSpeedDialog.call(vmN);
  ok("openSpeedDialog: 薄包装 openSpeedAt(null, up) -> left = innerWidth - 380 - 12",
     vmN.speedAt.left === 608 && vmN.speedAt.dir === "up" && vmN.speedOpen === true);

  // ---- closeSpeedDialog 复位 ----
  D.closeSpeedDialog.call(vmN);
  ok("closeSpeedDialog: 关层 + speedAt 复位", vmN.speedOpen === false &&
     JSON.stringify(vmN.speedAt) === JSON.stringify({ left: 0, dir: "up" }));

  // ---- submitSpeedDialog 双成功: 关窗 + speedOverride 清空重取 ----
  const vm1 = mk([snap(1024, 2048, 512, 256)]);
  await D.openSpeedAt.call(vm1, { currentTarget: { getBoundingClientRect: () => ({ left: 0 }) } }, "up");
  vm1.speedOverride.up = "2048";
  vm1.speedOverride.down = "4096";
  await D.submitSpeedDialog.call(vm1);
  ok("submitSpeedDialog 双成功: 主速 POST 载荷(0 下限取整)", JSON.stringify(vm1.overridePosts) === JSON.stringify([
    { upload_kib: 2048, download_kib: 4096 },
  ]));
  ok("submitSpeedDialog 双成功: 备用未改动不下发(零 alt POST)", vm1.altPosts.length === 0);
  ok("submitSpeedDialog 双成功: 关窗 + onOk 清空表单并重取托管状态",
     vm1.speedOpen === false && vm1.speedOverride.up === "" && vm1.speedOverride.down === "" && vm1.modeCalls === 2);

  // ---- submitSpeedDialog 主速成功备用失败: 留窗重试并按新快照回填 ----
  const vm2 = mk([snap(1024, 2048, 512, 256), snap(9999, 8888, 512, 256)]);
  vm2.waitCmd = async (id) => ({ ok: id === "main" });
  const origApi2 = vm2.api;
  vm2.api = async (url, opt) => {  // 拦截两组 POST 给可分辨 cmd_id(记录与分流都在本层, 不透传)
    if ((opt && opt.method) === "POST") {
      const body = JSON.parse(opt.body);
      if (url === "/api/speed/override") { vm2.overridePosts.push(body); return { cmd_id: "main" }; }
      if (url === "/api/speed/alt") { vm2.altPosts.push(body); return { cmd_id: "alt" }; }
    }
    return origApi2(url, opt);
  };
  await D.openSpeedAt.call(vm2, { currentTarget: { getBoundingClientRect: () => ({ left: 0 }) } }, "up");
  vm2.speedOverride.up = "2048";
  vm2.speedOverride.down = "4096";
  vm2.speedAlt.up = "1024";
  vm2.speedAlt.down = "512";
  await D.submitSpeedDialog.call(vm2);
  ok("submitSpeedDialog 部分失败: 两组都投递(主速 override + 备用 alt)",
     vm2.overridePosts.length === 1 && JSON.stringify(vm2.altPosts) === JSON.stringify([
       { upload_kib: 1024, download_kib: 512 },
     ]));
  ok("submitSpeedDialog 部分失败: 留在窗内重试(不关窗)", vm2.speedOpen === true);
  ok("submitSpeedDialog 部分失败: 失败路径重取快照并回填(主速按新快照 9999/8888, 备用同源)",
     vm2.modeCalls === 3 && vm2.speedOverride.up === "9999" && vm2.speedOverride.down === "8888" &&
     vm2.speedAlt.up === "512" && vm2.speedAlt.down === "256");

  // ---- 主速空表单: speedOvReady 闸零投递留窗 ----
  const vm3 = mk([snap(1024, 2048, 512, 256)]);
  await D.openSpeedAt.call(vm3, { currentTarget: { getBoundingClientRect: () => ({ left: 0 }) } }, "up");
  vm3.speedOverride.up = "";
  const before = vm3.posts.length;
  await D.submitSpeedDialog.call(vm3);
  ok("主速空表单: speedOvReady 闸零投递(备用未改动同样不下发) + 留窗",
     vm3.posts.length === before && vm3.speedOpen === true);

  process.stdout.write(JSON.stringify({
    title: "speedOverlay",
    ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

_NODE_SPEED_PROBE = _COMMON_PRELUDE + _NODE_SPEED_BODY


def test_r4_dialogs_meta_chain_battery():
    """R5#140(major) + R5#133: meta 编辑对话框全链 —— 交集方向/toggle 方向/先建后设/候选并回/载荷 + metaBusy 入口闸"""
    report = _run_probe(_NODE_META_CHAIN_PROBE, _DLGS_JS)
    _assert_battery(report, "meta 全链电池")


def test_r4_dialogs_meta_enter_empty_battery():
    """R5#132: 清空输入框回车 = 无分类 —— 空串回退经 onEnter 直达 metaSetCategory(修复前红)"""
    report = _run_probe(_NODE_META_ENTER_PROBE, _DLGS_JS, _ADD_JS)
    _assert_battery(report, "meta 清空回车电池")


def test_r4_dialogs_mgr_crud_battery():
    """R5#144: 管理对话框 CRUD —— 拆分/可空路径/字典展开字典序/清态 + busy 闸"""
    report = _run_probe(_NODE_MGR_PROBE, _DLGS_JS)
    _assert_battery(report, "管理对话框电池")


def test_r4_dialogs_history_math_battery():
    """R5#147: 历史流量聚合数学 —— 三档桶/摘要/悬停索引换算/面积路径"""
    report = _run_probe(_NODE_HISTORY_PROBE, _DLGS_JS)
    _assert_battery(report, "历史流量电池")


def test_r4_dialogs_speed_overlay_battery():
    """R5#146: 限速浮层编排 —— openSpeedAt 定位/预聚焦/回填 + submitSpeedDialog 双分支 + closeSpeedDialog"""
    report = _run_probe(_NODE_SPEED_PROBE, _DLGS_JS)
    _assert_battery(report, "限速浮层电池")
