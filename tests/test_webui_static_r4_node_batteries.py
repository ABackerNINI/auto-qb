"""test_webui_static_r4_node_batteries 测试计划: 存量评审 R4 static 主题清池 P03 —— 行为修复回归 + 纯逻辑 node 电池

## 测试计划(每个测试函数一条)
- test_r4_winmembers_sorted_window_same_source: R5#35(major) 修复回归 —— winMembers/memberPadTop/memberPadBottom 先 sortedMembers 再开窗: 明细列排序激活且成员 >= ROW_WIN_EST_MIN 时, 切片/占位/前缀和(_rowPre.member)与渲染数组同源同序, 键盘行序(shortcuts _kbRows 同走 sortedMembers)与前缀和逐行对齐(修复前 memberWin 按未排序 list 开窗必红)
- test_r4_groupwin_expand_backoff: R5#57 —— groupWin 退避判据 = 「当前真的有面板」: expandedKey 命中在场组才退避全量; 原组被筛掉/已删与未展开都保持 active 窗口(不得为一个不存在的面板永久退化成全量渲染)
- test_r4_apply_col_order_boundaries: R5#53 —— applyColOrder 落点折算四类边界: 向后移 at=dropIdx-1 / 向前移原位插入 / 末尾边界兜底 push / 非法输入(隐藏列/越界)no-op; 全程隐藏列相对次序不动且尊重既有 colOrder 头部
- test_r4_col_persist_intent_merge_and_gates: R5#52(major) + R5#37/R5#38 修复回归 —— 意图升格三层 merge: 拖拽/双击自适应后既有隐藏列 px 仍在、可见列被渲染快照冻结、被拖/适配列被终值覆盖; 纯点击零位移不升格意图不落盘不拦 click(R5#37); 拖拽尾 capture 拦截下一拍自清(R5#38); 微动未过阈值不把起始快照写进生效轨(issue 26-11-08-0229 #10)
- test_r4_selection_state_machine: R5#51(major) —— AQB_SELECTION 真跑: _selSyncGroups 四态(补选/移出/未知 key 保留/种子页降级: 不补选但降级照做)、_selAnchor 兜底链四态(显式锚点/光标/展开组/首行)、selSizeSummaryOf occ_key 取 max 去重
- test_r4_load_col_state_seeding: R5#18 —— loadColState 默认隐藏播种三态: 空存储播种 / 仅空 hidden 不播(「刻意全开」合法偏好) / 有任一偏好键不播; 附坏 JSON 走完整流程、locked 列忽略、w 白名单洗净(洗净后三键全缺照播)
- test_r4_sort_domain: R5#54 —— AQB_SORT 真跑: setSort 三态循环(经典 gk/gd 与 dyn dtSortState 两形态) + _dtStrCompare(IPv4 逐段数值序/端口数值/等值/非 IP localeCompare 回落) + sortedDrawer 空值两方向恒末位与 IPv4 数值序
- test_r4_format_ladder_family: R5#55 —— format 函数族档位边界: _fmtLadder 梯顶回落(top 命中/缺省/档名写错回落整梯)与字节/速度两族、fmtEta 8640000 哨兵与非正值、fmtDuration 三段进位边界、fmtPeersQb 缺省只显已连接
- test_r4_fx_mount_toast_split_and_rows_ghost: R5#193 —— flux fx 挂载层 node 电池(fx-mount.js 是 IIFE,
  桩 DOM/BOM 后真跑): TOAST_SPLIT 拆段正则族(主标题+说明两段落地/无分隔符与括号头与超 14 字头与
  说明不足 2 字单行 —— trim 后计长, 分隔符后连接空格不算门槛/全角冒号与逗号分隔/单行也挂 toast-txt)+ toastSync 差分 stamp(rise/队列牌/倒计时
  只归 own 条/danger 原位升级)+ rows 行差分(首轮只建缓存/增删检出排一帧/退场幽灵克隆定格 row-out
  附回原容器/入场行 stamp row-in/无增删不排帧)
- test_r4_dt05_advice_dispatch: R5#95(P13) —— 05 adviceFor 五类关键词分派经 rowsFn 真跑(失败桶
  failRowOf 装配路径, 不经字符串锚): not registered/passkey/ban/timeout/maintenance 每类一条
  命中各自文案 + 通用兜底分支(零覆盖的纯判据, node 电池直跑)
- test_r4_dt05_tier_sort_missing_last: R5#81(P13) 修复回归 —— 05 ok 组 tier 升序对缺失/非法
  tier 记 9 殿后(与 04/06 的 tierN 兜底同口径), 稳定序保 qB 原序; 修复前折算 0 把 tier 缺失
  tracker 插到所有 tier0 之前必红
- test_r4_drawer_general_rows_qb_sentinels: issue 26-11-08-0229 #2 修复回归 —— drawerGeneralSections
  契约层传输行(做种数/完整下载中/连接)对 qB -1/null 哨兵降级(单值槽 —, 连接上限 -1 译「不限」,
  与 fmtPeersQb/01 英雄行 peerNum/connLimit 同口径), 真值形态逐字不变; 01/02/03 三变体共同消费
  该单点, 电池直跑生产函数不经字符串锚

加载口径: columns 域经 webui_helpers.bundle_file("columns.js") 聚合(根 + 五片段清单序, 与拆分前
同一份代码); 单文件域(selection/sort/format)直接 eval。app.js 以 loadColState 截断切片加载
(该函数依赖的列模型常量/洗净函数全部在其上方, createApp 接线段不进沙箱)。
窗口化/列模型常量(单点在 app.js)由电池自给 —— 与 webui_dom_page_support._NODE_WIN_SRC_PROBE 同口径。
无 node 静默跳过(与既有 node 电池同口径, 不引入 pytest skip)。
"""

import json
import os
import shutil
import subprocess
import tempfile

from webui_helpers import STATIC_ROOT, bundle_file


def _run_probe(probe, *args):
    """跑一个 node 电池: 无 node 静默跳过(返回 None); 输出末行必须是 {ok, total, failed} JSON"""
    node = shutil.which("node")
    if not node:
        return None
    proc = subprocess.run(
        [node, "-e", probe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"node 电池跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _assert_battery(report, what):
    assert report is not None, "无 node: 本电池静默跳过(与既有电池同口径)"
    assert report["failed"] == [], f"{what} {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# R5#35 修复回归: winMembers 三个入口先排序再开窗, 切片/前缀和/占位同源 ------------------
_NODE_WINMEMBER_PROBE = r"""
const fs = require("fs");
// 行窗口化常量(单点在 app.js, 电池自给 —— 与 _NODE_WIN_SRC_PROBE 同口径)
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
global.ROW_WIN_GAP_FALLBACK = 0;
global.window = {};
// winMembers 依赖排序域的 sortedMembers(AQB_SORT) —— 真机两域同混进一个组件实例, 这里同混
const srcCols = fs.readFileSync(process.argv[1], "utf8");
const srcSort = fs.readFileSync(process.argv[2], "utf8");
eval(srcCols + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
eval(srcSort + "\n;globalThis.__W3__ = window.AQB_SORT;");
const M = Object.assign({}, globalThis.__W2__.methods, globalThis.__W3__.methods);

const GAP = 6;
const N = 300;
// 成员: hash m0..m299; 排序键 uploaded = (i*7919)%300(与 N 互质 = 0..299 的真排列, 排序必打乱原序);
// 行高两档按**原序**交替(排序后相邻行高错落, 前缀和对"序"敏感 —— 按错序累积必对不上)
const mkMembers = () => Array.from({ length: N }, (_, i) => ({
  hash: "m" + i, uploaded: (i * 7919) % N, site: "s" + (i % 7), __i: i,
}));
const hOf = (i) => (i % 2 ? 65.4 : 43.7);
const mkCtx = () => Object.assign({}, M, {
  rowWin: true,
  detailSortKey: "uploaded", detailSortDir: -1,  // 明细列排序激活(R5#35 触发条件之一)
  _winMeasured: { torrent: true, group: true, member: true, ctr: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, ctr: 50, drawerContent: 50 },
  _rowHVer: 1,
  _winViewH: 800,
  _winScrollY: 3000,  // 滚到中段: padTop/padBottom 非零, 切片错位必现
  _winTop: { torrent: 0, group: 0, member: 0, ctr: 0, drawerContent: 0 },
  _rowHs: {},
  _rowPre: {},
  _winGapFor: () => GAP,
  memberHashesOf: (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean),
});
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const c = mkCtx();
const list = mkMembers();
list.forEach((m, i) => { c._rowHs["member:" + m.hash] = hOf(i); });
const hOfM = (m) => hOf(m.__i);
const sorted = M.sortedMembers.call(c, list);
ok("场景有效: 排序真的打乱了原序(否则本电池空转)",
   JSON.stringify(sorted.map((m) => m.hash)) !== JSON.stringify(list.map((m) => m.hash)));

// ① 渲染切片 = 在排序序上开窗的切片(窗口与前缀和同一数组)
const w = M.memberWin.call(c, sorted);
const rendered = M.winMembers.call(c, list);
const want = sorted.slice(w.start, w.end);
ok("winMembers 切片与渲染数组同序(排序激活下窗口按 sortedMembers 序开窗)",
   w.active && want.length < N &&
   JSON.stringify(rendered.map((m) => m.hash)) === JSON.stringify(want.map((m) => m.hash)));

// ② 前缀和按排序序逐行累积(_rowPre.member 供键盘视口换算文档 y, 必须与 _kbRows 同序)
const pre = c._rowPre.member;
let preOk = !!pre && pre.length === N + 1 && pre[0] === 0;
if (preOk) {
  for (let i = 0; i < N; i++) {
    if (Math.abs(pre[i + 1] - pre[i] - (hOfM(sorted[i]) + GAP)) > 1e-9) { preOk = false; break; }
  }
}
ok("_rowPre.member 前缀和按排序后行高累积(修复前按未排序序累积必红)", preOk);

// ③ 占位与排序序窗口一致(调用点同步传排序后数组)
const padTop = M.memberPadTop.call(c, list);
const padBottom = M.memberPadBottom.call(c, list);
ok("memberPadTop 与排序序窗口一致", padTop > 0 && Math.abs(padTop - w.padTop) < 1e-9);
ok("memberPadBottom 与排序序窗口一致", padBottom > 0 && Math.abs(padBottom - w.padBottom) < 1e-9);

// ④ 键盘视口回落取行不岔: 前缀和第 i 行 = 键盘行序(shortcuts 同走 sortedMembers)第 i 行
const kb = c.memberHashesOf(sorted);
ok("前缀和与键盘行序逐行对齐(切片首行 + 窗口末行)",
   M._rowKeyOf.call(c, "member", sorted[w.start]) === "member:" + kb[w.start] &&
   M._rowKeyOf.call(c, "member", sorted[w.end - 1]) === "member:" + kb[w.end - 1]);

// ⑤ 排序未激活/窗口关闭 = 原行为(零差异回退)
const c2 = mkCtx();
c2.detailSortKey = "";
c2.rowWin = false;
const r2 = M.winMembers.call(c2, mkMembers());
ok("窗口关闭且未排序时全量回退", r2.length === N);
ok("排序未激活时 sortedMembers 原样返回", M.sortedMembers.call(c2, list) === list);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#57: groupWin 退避判据(「当前真的有面板」) -------------------------------------
_NODE_GROUPWIN_BACKOFF_PROBE = r"""
const fs = require("fs");
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
global.ROW_WIN_GAP_FALLBACK = 0;
global.TABLE_DEFS = { group: { tableRef: null }, torrent: { tableRef: null } };
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;
const C = globalThis.__W2__.computed;

const GAP = 6;
const N = 300;
const mkGroups = () => Array.from({ length: N }, (_, i) => ({ key: "g" + i }));
const mkCtx = (expandedKey) => Object.assign({}, M, {
  rowWin: true,
  filteredGroups: mkGroups(),
  expandedKey,
  _winMeasured: { torrent: true, group: true, member: true, ctr: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, ctr: 50, drawerContent: 50 },
  _rowHVer: 1,
  _winViewH: 800,
  _winScrollY: 6000,
  _winTop: { torrent: 0, group: 0, member: 0, ctr: 0, drawerContent: 0 },
  _rowHs: {},
  _rowPre: {},
  _winGapFor: () => GAP,
});
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ① 展开组在场: 退避全量(.detail 高度不定, 窗口的"第 i 行在 pre[i]"假设失效)
const wOn = C.groupWin.call(mkCtx("g150"));
ok("expandedKey 命中在场组 -> 退避 off 全量(end=n, 占位 0)",
   wOn.active === false && wOn.end === N && wOn.padTop === 0 && wOn.padBottom === 0);
// ② 展开态跨视图带回后原组已被筛掉/已删: 不为一个不存在的面板退避, 保持 active 窗口
const wGone = C.groupWin.call(mkCtx("gone"));
ok("expandedKey 指向不在场的组 -> active 窗口(不误退避)", wGone.active === true);
// ③ 未展开: active 窗口
const wOff = C.groupWin.call(mkCtx(""));
ok("expandedKey 空 -> active 窗口", wOff.active === true);
// ④ 窗口切片与占位合理(②③的窗口是真窗口, 不是退到另一边)
ok("active 窗口切片是严格子集且占位非零", wOff.end - wOff.start < N && wOff.padTop > 0 && wOff.padBottom > 0);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#53: applyColOrder 落点折算四类边界 --------------------------------------------
_NODE_APPLY_COL_ORDER_PROBE = r"""
const fs = require("fs");
global.window = {};
// TABLE_COLUMNS 是 app.js 模块级常量, 方法体按裸名引用(走作用域链, 不走 this) —— 必须真挂全局
global.TABLE_COLUMNS = { p: [{ key: "a" }, { key: "b" }, { key: "c" }, { key: "d" }, { key: "e" }] };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

// 可视列空间 a b c e(d 隐藏); 全序列 a b c d e
const mkCtx = (order) => {
  const c = Object.assign({}, M, {
    colHidden: { p: ["d"] },
    colOrder: { p: order || [] },
    colWidths: {},
    colW: {},
    persisted: [],
    persistPage: (page) => c.persisted.push(page),
    $nextTick: (fn) => fn(),
    recomputeEffective() {},
  });
  return c;
};
const orderOf = (c) => c.colOrder.p;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ① 向后移: a(vis 0) 拖到 dropIdx 2(c 之前) -> 移除自身后 at=1, 插在 b 与 c 之间
let c = mkCtx();
M.applyColOrder.call(c, "p", "a", 2);
ok("向后移: dropIdx 2 -> [b,a,c,d,e](隐藏列相对次序不动)", JSON.stringify(orderOf(c)) === JSON.stringify(["b", "a", "c", "d", "e"]));
ok("落库即持久化该页", c.persisted.length === 1 && c.persisted[0] === "p");

// ② 向前移: e(vis 3) 拖到 dropIdx 0 -> 移除自身后 at=0, 插在最前
c = mkCtx();
M.applyColOrder.call(c, "p", "e", 0);
ok("向前移: dropIdx 0 -> [e,a,b,c,d]", JSON.stringify(orderOf(c)) === JSON.stringify(["e", "a", "b", "c", "d"]));

// ③ 末尾边界: a 拖到 dropIdx 4(== 可视列数) -> 跳隐藏列计 seen 后仍插不进, 兜底 push 到末尾
c = mkCtx();
M.applyColOrder.call(c, "p", "a", 4);
ok("末尾边界: dropIdx=vis.length -> [b,c,d,e,a](兜底 push)", JSON.stringify(orderOf(c)) === JSON.stringify(["b", "c", "d", "e", "a"]));

// ④ 非法输入一律 no-op: 负 dropIdx / 越界 / 隐藏列自身(可视空间里找不到)
c = mkCtx();
M.applyColOrder.call(c, "p", "a", -1);
M.applyColOrder.call(c, "p", "a", 5);
M.applyColOrder.call(c, "p", "d", 1);
ok("非法输入(负/越界/隐藏列)no-op(colOrder 不写)", !c.colOrder.p || c.colOrder.p.length === 0);
ok("非法输入不触发持久化", c.persisted.length === 0);

// ⑤ 尊重既有 colOrder 头部(_orderedKeys): 自定义序 e d c b a(d 隐藏) 下, a(vis 3) 移到 0
c = mkCtx(["e", "d", "c", "b", "a"]);
M.applyColOrder.call(c, "p", "a", 0);
ok("既有自定义序下向前移 -> [a,e,d,c,b]", JSON.stringify(orderOf(c)) === JSON.stringify(["a", "e", "d", "c", "b"]));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#52 意图升格三层 merge + R5#37 纯点击门槛 + R5#38 拦截自清 ----------------------
_NODE_COLPERSIST_MERGE_PROBE = r"""
const fs = require("fs");
// 列模型常量(单点在 app.js, 电池自给)
global.MIN_COL_PX = 56;
global.MAX_FIT_PX = 520;
global.RESIZE_DRAG_THRESHOLD = 3;
const listeners = [];   // {type, fn, capture, op: "add"|"remove"}
const timers = [];      // {fn, ms}
global.document = {
  addEventListener: (t, fn, cap) => { listeners.push({ type: t, fn, capture: !!cap, op: "add" }); },
  removeEventListener: (t, fn, cap) => { listeners.push({ type: t, fn, capture: !!cap, op: "remove" }); },
};
global.setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

const SNAP = { a: "200px", b: "150px", c: "120px", e: "90px" };  // 起始渲染快照(只含可见列)
const VIS = [{ key: "a" }, { key: "b" }, { key: "c" }, { key: "e" }];
const mkCtx = () => {
  const c = Object.assign({}, M, {
    colW: { p: { hid: "111px" } },      // 既有意图: 隐藏列的 px(merge 必须保住的那部分)
    colHidden: { p: ["hid"] },
    colWidths: {},
    persisted: [],
    recomputed: 0,
    persistPage: (page) => c.persisted.push(page),
    $nextTick: (fn) => fn(),
    recomputeEffective() { c.recomputed++; },
    _visibleCols: () => VIS,
    _renderedWidths: () => ({ ...SNAP }),
  });
  return c;
};
const evAt = (x) => ({ target: { closest: () => ({}) }, clientX: x, shiftKey: false });
const byType = (t) => listeners.filter((l) => l.type === t);
const fire = (t, ev) => {
  const reg = byType(t).filter((l) => l.op === "add");
  if (reg.length) reg[reg.length - 1].fn(ev);
};
const resetRec = () => { listeners.length = 0; timers.length = 0; };
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ① 拖拽意图升格三层 merge(R5#52): {colW 旧值(含隐藏列) ∪ 渲染快照 ∪ 拖拽终值}
let c = mkCtx();
M.startResize.call(c, evAt(100), "p", "a");   // 注册 move/up; startVal = 200
fire("mousemove", { clientX: 220 });          // 位移 120 > 阈值 3 -> dragged=true, w = max(56, 320) = 320
ok("拖拽中生效宽度已推到终值且邻居列按快照固化",
   c.colWidths.p && c.colWidths.p.a === "320px" && c.colWidths.p.b === "150px");
fire("mouseup", {});
ok("意图升格: 既有隐藏列 px 仍在(旧实现整段替换正是抹掉它的根因)", c.colW.p.hid === "111px");
ok("意图升格: 被拖列被拖拽终值覆盖", c.colW.p.a === "320px");
ok("意图升格: 可见列被起始渲染快照冻结", c.colW.p.b === "150px" && c.colW.p.e === "90px");
ok("拖拽落定走唯一持久化漏斗", c.persisted.length === 1 && c.persisted[0] === "p" && c.recomputed === 1);
// R5#38: 拦截下一拍自清 —— click capture 监听在册 + 定时器排了自清; 自清/自注销都指向同一函数
const clickAdds = byType("click").filter((l) => l.op === "add");
const timersBefore = timers.length;
ok("拖拽尾挂了 capture 拦截层", clickAdds.length === 1 && clickAdds[0].capture === true);
ok("mouseup 后下一拍自清已排程", timersBefore >= 1 && timers[timers.length - 1].ms === 0);
timers[timers.length - 1].fn();               // 触发自清
const lastRemove = byType("click").filter((l) => l.op === "remove").pop();
ok("自清按同一 (click, capture) 注销拦截层", !!lastRemove && lastRemove.fn === clickAdds[0].fn && lastRemove.capture === true);
const evFlags = { stopped: false, prevented: false };
clickAdds[0].fn({ stopPropagation: () => { evFlags.stopped = true; }, preventDefault: () => { evFlags.prevented = true; } });
ok("拦截层 stopPropagation+preventDefault 且拦完即注销", evFlags.stopped && evFlags.prevented);

// ② 纯点击零位移(R5#37 修复回归): 不升格意图/不落盘/不拦 click
resetRec();
c = mkCtx();
M.startResize.call(c, evAt(100), "p", "a");
fire("mouseup", {});                          // 零位移: move 从未触发
ok("纯点击: colW 意图不被污染(页面保持全自动)", c.colW.p.hid === "111px" && !c.colW.p.a);
ok("纯点击: 不落盘/不重算/不挂拦截层/不排自清",
   c.persisted.length === 0 && c.recomputed === 0 &&
   byType("click").filter((l) => l.op === "add").length === 0 && timers.length === 0);

// ②-b 微动未过阈值(issue 26-11-08-0229 #10 修复回归): 位移 <=3px 不把起始快照写进生效轨 colWidths
resetRec();
c = mkCtx();
M.startResize.call(c, evAt(100), "p", "a");
fire("mousemove", { clientX: 102 });          // 位移 2 <= 阈值 3: dragged 仍 false
ok("微动未过阈值: 生效轨不被起始快照污染", !c.colWidths.p);
fire("mousemove", { clientX: 220 });          // 位移 120 > 阈值: 过阈值后照常写生效轨
ok("过阈值后生效轨照常写入", c.colWidths.p && c.colWidths.p.a === "320px" && c.colWidths.p.b === "150px");
fire("mouseup", {});
ok("微动后真拖拽: 意图升格/落盘/拦截层照常",
   c.colW.p.a === "320px" && c.colW.p.hid === "111px" && c.persisted.length === 1 &&
   byType("click").filter((l) => l.op === "add").length === 1);

// ③ 双击自适应(R5#52 后半): 同一套 merge, 适配列被适配备覆盖、隐藏列 px 仍在
resetRec();
c = mkCtx();
const headEl = { children: [{ scrollWidth: 400 }], parentElement: { querySelectorAll: () => [] } };
M.autoFitColumn.call(c, { target: { closest: () => headEl } }, "p", "a");
ok("双击自适应: 适配备 = 内容宽 + 18(夹在 [MIN, MAX_FIT_PX])", c.colW.p.a === "418px");
ok("双击自适应: 隐藏列 px 仍在 + 可见列被快照冻结", c.colW.p.hid === "111px" && c.colW.p.b === "150px");
ok("双击自适应: 生效态同步且落盘", c.colWidths.p.a === "418px" && c.persisted.length === 1);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#51: AQB_SELECTION 选择联动状态机 ----------------------------------------------
_NODE_SELECTION_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_SELECTION;");
const M = globalThis.__W2__.methods;

const memberHashesOf = (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
// 真实组 A(两成员) / B(单成员) + 虚拟行 u-h9(未归组命中种子)
const GROUPS = [
  { key: "A", members: [{ hash: "h1" }, { hash: "h2" }] },
  { key: "B", members: [{ hash: "h3" }] },
  { key: "u-h9", virtual: true, members: [{ hash: "h9" }] },
];
const mkCtx = (over) => Object.assign({}, M, {
  memberHashesOf,
  decoratedGroups: GROUPS,
  filteredGroups: GROUPS,
  filteredTorrents: [],
  selGroups: [],
  selMembers: [],
  selAnchorGroup: null,
  selAnchorMember: null,
  selAnchorUnit: null,
  kbCursor: null,
  expandedKey: null,
  viewMode: "groups",
  page: "groups",
}, over);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- _selSyncGroups 四态 ---
// ① 补选: 成员凑齐 -> 组入选(成员 -> 组方向)
let c = mkCtx({ selMembers: ["h1", "h2"], selGroups: [] });
M._selSyncGroups.call(c);
ok("回扫补选: 组内成员全选 -> 组入选", JSON.stringify(c.selGroups) === JSON.stringify(["A"]));
// ② 移出: 撤到不全 -> 组移出
c = mkCtx({ selMembers: ["h1"], selGroups: ["A", "B"] });
M._selSyncGroups.call(c);
ok("回扫移出: 撤掉一个成员 -> 不完整的组移出", c.selGroups.length === 0);
// ③ 未知 key 保留: 虚拟行/已消失的组不在回扫面里, 一律保留
c = mkCtx({ selMembers: ["h1", "h2"], selGroups: ["A", "Z", "u-h9"] });
M._selSyncGroups.call(c);
ok("不可解析的 key(未知组/虚拟行)保留不清理",
   c.selGroups.includes("Z") && c.selGroups.includes("u-h9") && c.selGroups.includes("A"));
// ④ 种子页降级: 不补选(decoratedGroups 只是冻结快照)但降级照做(不残留组 key 卷进批量载荷)
c = mkCtx({ viewMode: "torrents", selMembers: ["h1", "h2"], selGroups: [] });
M._selSyncGroups.call(c);
ok("种子页: 凑齐的组不补选(用户心智是我选了这些种子)", c.selGroups.length === 0);
c = mkCtx({ viewMode: "torrents", selMembers: ["h1"], selGroups: ["B"] });
M._selSyncGroups.call(c);
ok("种子页: 不完整的组仍降级移出(撤选残留组 key 会卷进批量载荷)", c.selGroups.length === 0);

// --- _selAnchor 兜底链(组) ---
c = mkCtx({ selAnchorGroup: "g2" });
ok("起点兜底链①: 显式锚点在列表内 -> 用它", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g2");
c = mkCtx({ selAnchorGroup: "gX", kbCursor: { kind: "group", id: "g3" } });
ok("起点兜底链②: 锚点失效 -> 当前光标", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g3");
c = mkCtx({ selAnchorGroup: "gX", kbCursor: { kind: "torrent", id: "h1" }, expandedKey: "g1" });
ok("起点兜底链③: 光标不在此列表 -> 当前展开的组", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g1");
c = mkCtx({});
ok("起点兜底链④: 全缺 -> 列表首行", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g1");
c = mkCtx({});
ok("空列表 -> null(调用方按无起点处理)", M._selAnchor.call(c, "group", []) === null);
// 成员 kind: 光标 kind=torrent 映射 member(键鼠统一模型)
c = mkCtx({ kbCursor: { kind: "torrent", id: "h5" } });
ok("成员起点: 光标 torrent 即成员上下文", M._selAnchor.call(c, "member", ["h4", "h5"]) === "h5");

// --- selSizeSummaryOf: occ_key 取 max 去重 ---
const sum = M.selSizeSummaryOf([
  { hash: "h1", occ_key: "k", size: 100 },
  { hash: "h2", occ_key: "k", size: 250 },
  { hash: "h3", size: 70 },
]);
ok("实际占用按 occ_key 单元取 max 去重(250+70), 合计逐成员求和(420)",
   sum.total === 420 && sum.occupy === 320);
ok("无选中 -> {0,0}", JSON.stringify(M.selSizeSummaryOf([])) === JSON.stringify({ total: 0, occupy: 0 }));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


# R5#18: loadColState 默认隐藏播种语义 ---------------------------------------------
def _app_head_source():
    """app.js 截到 loadColState 结束(其后是模块级 initialColState 消费与 createApp 接线, 不进沙箱)"""
    src = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    marker = "const initialColState = loadColState();"
    return src[:src.index(marker)]


_NODE_LOADCOLSTATE_PROBE = r"""
const fs = require("fs");
global.Vue = { createApp: () => ({}) };   // app.js 头部 `const { createApp } = Vue;`
global.window = {};
let store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
const src = fs.readFileSync(process.argv[1], "utf8");
// 函数声明与 const 都在同一份 eval 里, 断言闭包捕获后从外面驱动
eval(src + "\n;globalThis.__X = { LC: loadColState, pages: ALL_TABLE_PAGES, cols: TABLE_COLUMNS, hidden: DEFAULT_HIDDEN_KEYS };");
const LC = globalThis.__X.LC;
const PAGES = globalThis.__X.pages;
const COLS = globalThis.__X.cols;
const DEF = globalThis.__X.hidden;
const lockedKey = (p) => { const c = COLS[p].find((c) => c.locked); return c ? c.key : null; };
const defaultsOf = (p) => COLS[p].map((c) => c.key).filter((k) => DEF.has(k));
const setStore = (pages) => {
  store = { autoqb_cols_v5: JSON.stringify({ v: 5, origin: "http://x", pages }) };
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ① 空存储: 每页播种 = 本表列 key 与 DEFAULT_HIDDEN_KEYS 的交集
setStore({});
let out = LC();
let seedOk = true;
let anyDefault = false;
for (const p of PAGES) {
  const want = defaultsOf(p);
  if (want.length) anyDefault = true;
  if (JSON.stringify(out.hidden[p] || []) !== JSON.stringify(want)) { seedOk = false; break; }
}
ok("空存储: 从无偏好的页按 DEFAULT_HIDDEN_KEYS 交集播种", seedOk && anyDefault);
ok("空存储: order/w 全空", Object.keys(out.order).length === 0 && Object.keys(out.w).length === 0);

// ② 仅空 hidden: 该页不播(「刻意全开」是合法偏好), 未定制过的页照播
setStore({ group: { hidden: [] } });
out = LC();
ok("仅空 hidden 的页不播(刻意全开不被默认值覆盖)", JSON.stringify(out.hidden.group || []) === "[]");
const torrentDefaults = defaultsOf("torrent");
ok("未定制过的页照常播种(提前 return 会把默认隐藏列全放出来)", torrentDefaults.length > 0 &&
   JSON.stringify(out.hidden.torrent || []) === JSON.stringify(torrentDefaults));

// ③ 有任一偏好键(哪怕只定制了 order): 该页不播; locked 列即使被写进存储也忽略
const lk = lockedKey("torrent");  // torrent 表的 locked 列 = "name"
setStore({ torrent: { hidden: [lk, "amount_left"] }, group: { order: ["name"] } });
out = LC();
ok("仅定制 order 的页不播(三键全缺才播)", !out.hidden.group && out.order.group[0] === "name");
ok("存储里的 locked 列被忽略, 非 locked 默认隐藏列保留",
   !(out.hidden.torrent || []).includes(lk) && (out.hidden.torrent || []).includes("amount_left"));

// ④ w 白名单洗净: 只收合法列 key 的 "<num>px"; 洗净后三键全缺照播
setStore({ torrent: { w: { name: "120px", bogus: "50px", size: "1.5px", eta: "0px" } } });
out = LC();
ok("w 白名单: 非法 key/小数 px 丢弃, 合法 <num>px 收下",
   JSON.stringify(out.w.torrent) === JSON.stringify({ name: "120px", eta: "0px" }));
ok("w 洗净后非空的页不播", !out.hidden.torrent);
setStore({ detail: { w: { bogus: "50px", size: "1.5px" } } });
out = LC();
ok("w 全被洗净 = 三键全缺 -> 该页照播(坏数据也走完整流程)", JSON.stringify(out.hidden.detail || []) === JSON.stringify(defaultsOf("detail")));

// ⑤ 坏 JSON: 归空意图 + 播种照常(与空存储同形)
store = { autoqb_cols_v5: "{broken" };
out = LC();
ok("坏 JSON: 走完整流程, 播种不缺席", JSON.stringify(out.hidden.torrent || []) === JSON.stringify(defaultsOf("torrent")));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#54: AQB_SORT 三态循环 + 比较器 ------------------------------------------------
_NODE_SORT_PROBE = r"""
const fs = require("fs");
// 排序注册表(单点在 app.js, 电池自给): 经典 gk/gd 形态 + dyn(dtSortState 映射)形态各一
global.ALL_TABLE_DEFS = {
  group: { sort: { gk: "sortKey", gd: "sortDir", defKey: "added_on", defDir: -1 } },
  d0: { sort: { dyn: true, defKey: "added_on", defDir: -1 } },
};
global.VIEW_TABLE = { groups: "group" };
global.DRAWER_TABLE_DEFS = { d0: { sort: { dyn: true, defKey: "", defDir: -1 } } };
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_SORT;");
const M = globalThis.__W2__.methods;
const mkCtx = (over) => Object.assign({}, M, {
  viewMode: "groups",
  sortKey: "added_on", sortDir: -1,
  dtSortState: {},
}, over);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ① 经典三态: 新键降序 -> 同键升序 -> 第三击回默认
let c = mkCtx();
M.setSort.call(c, "name");
ok("三态一击: 新键降序", c.sortKey === "name" && c.sortDir === -1);
M.setSort.call(c, "name");
ok("三态二击: 同键升序", c.sortKey === "name" && c.sortDir === 1);
M.setSort.call(c, "name");
ok("三态三击: 恢复默认(最近添加降序)", c.sortKey === "added_on" && c.sortDir === -1);

// ② dyn 形态(dtSortState 映射): 同一三态循环, 单元懒建
c = mkCtx();
M.setSort.call(c, "size", "d0");
ok("dyn 一击: 新键降序(cell 懒建保响应式)",
   c.dtSortState.d0 && c.dtSortState.d0.key === "size" && c.dtSortState.d0.dir === -1);
M.setSort.call(c, "size", "d0");
ok("dyn 二击: 同键升序", c.dtSortState.d0.dir === 1);
M.setSort.call(c, "size", "d0");
ok("dyn 三击: 回默认键", c.dtSortState.d0.key === "added_on" && c.dtSortState.d0.dir === -1);

// ③ _dtStrCompare: IPv4(+可选端口)逐段数值序; 端口数值; 等值 0; 非 IP localeCompare 回落
const cmp = (a, b) => M._dtStrCompare(a, b);
ok("IPv4 段内数值序: 10.10.2.3 < 10.10.10.1(字典序会排反)", cmp("10.10.2.3:51413", "10.10.10.1:80") < 0);
ok("端口按数值比较: 8080 > 443", cmp("1.2.3.4:8080", "1.2.3.4:443") > 0);
ok("等值 -> 0", cmp("1.2.3.4", "1.2.3.4") === 0);
ok("非 IP 回落 localeCompare", cmp("b", "a") > 0 && cmp("a", "b") < 0);

// ④ sortedDrawer: 空值两方向恒末位(不反转) + IPv4 数值序 + 数值走 _raw 侧
const rows = [
  { id: 1, _raw: { addr: "1.2.3.10" } },
  { id: 2, _raw: { addr: "1.2.3.9" } },
  { id: 3, _raw: { addr: "" } },
];
const draw = (dir) => M.sortedDrawer.call(mkCtx({ dtSortState: { d0: { key: "addr", dir } } }), "d0", rows).map((r) => r.id);
ok("升序: 1.2.3.9 在 1.2.3.10 前(段内数值序), 空值恒末位", JSON.stringify(draw(1)) === JSON.stringify([2, 1, 3]));
ok("降序: 空值仍恒末位(两方向不反转)", JSON.stringify(draw(-1)) === JSON.stringify([1, 2, 3]));
const nums = [{ id: 1, _raw: { size: 300 } }, { id: 2, _raw: { size: 20 } }];
const drawNum = (dir) => M.sortedDrawer.call(mkCtx({ dtSortState: { d0: { key: "size", dir } } }), "d0", nums).map((r) => r.id);
ok("数值键按 _raw 侧数值比较(显示值字符串比较会错序)", JSON.stringify(drawNum(1)) === JSON.stringify([2, 1]));
ok("空键 = 后端原序(排序永远可逆)", JSON.stringify(M.sortedDrawer.call(mkCtx({ dtSortState: {} }), "d0", rows.map((r) => r.id && { id: r.id })) ) === JSON.stringify([{ id: 1 }, { id: 2 }, { id: 3 }]));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#55: format 函数族档位边界 ------------------------------------------------------
_NODE_FORMAT_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_FORMAT;");
const M = globalThis.__W2__.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// _fmtLadder: 命中档位 / 梯下回落(roundFallback 取整) / 梯顶截断 / 档名写错回落整梯
ok("字节梯命中 GiB", M._fmtLadder(2 ** 31, "bytes", 2, false) === "2.00 GiB");
ok("字节梯命中 KiB 下界(1024 = 恰一档)", M._fmtLadder(2 ** 10, "bytes", 2, false) === "1.00 KiB");
ok("梯下原值不取整", M._fmtLadder(500.6, "bytes", 1, false) === "500.6 B");
ok("roundFallback 取整兜底", M._fmtLadder(500.6, "bytes", 1, true) === "501 B");
ok("梯顶截断: PiB 体量按 TiB 档显示(曲线图轴标口径)", M._fmtLadder(2 ** 50, "bytes", 2, false, "TiB") === "1024.00 TiB");
ok("top 档名写错回落整张梯(不静默错值)", M._fmtLadder(2 ** 50, "bytes", 2, false, "ZiB") === "1.00 PiB");
ok("速度梯: KiB/s 下界", M.fmtSpeed(2 ** 10) === "1.00 KiB/s");
ok("速度梯楼层 B/s", M._fmtLadder(512, "speed", 2, false) === "512 B/s");
ok("fmtSpeed 0 值口径", M.fmtSpeed(0) === "0 B/s");
ok("fmtSize 缺失/0 值口径", M.fmtSize(null) === "-" && M.fmtSize(0) === "0 B");

// fmtEta: qB 哨兵 8640000 = 无 ETA; 非正数 = 未知/缺失 —— 均空白
ok("ETA 哨兵 8640000 空白", M.fmtEta(8640000) === "");
ok("ETA 非正数空白", M.fmtEta(0) === "" && M.fmtEta(-5) === "");
ok("ETA 哨兵-1s 空白(最大合法值 8639999 正常显示)", M.fmtEta(8639999) === "99天23时");
ok("ETA 普通值走 fmtDuration", M.fmtEta(3600) === "1时00分");

// fmtDuration 三段进位边界
ok("0 -> 0分钟", M.fmtDuration(0) === "0分钟");
ok("<1h 不带秒位", M.fmtDuration(59) === "0分钟" && M.fmtDuration(60) === "1分钟" && M.fmtDuration(3599) === "59分钟");
ok("时段进位(分补零)", M.fmtDuration(3600) === "1时00分" && M.fmtDuration(3660) === "1时01分");
ok("天界(23时59分 -> 1天00时)", M.fmtDuration(86399) === "23时59分" && M.fmtDuration(86400) === "1天00时");
ok("天 + 时进位", M.fmtDuration(90000) === "1天01时");
ok("小数秒向下取整", M.fmtDuration(90.7) === "1分钟");
ok("undefined 兜 0", M.fmtDuration(undefined) === "0分钟");

// fmtPeersQb: qB 口径 "已连接 (总数)"; 总数缺失(-1/null)只显已连接; 已连接缺失全空白
ok("双值 -> c (t)", M.fmtPeersQb(5, 10) === "5 (10)");
ok("总数缺失/负哨兵 -> 只显已连接", M.fmtPeersQb(5, null) === "5" && M.fmtPeersQb(5, -1) === "5");
ok("已连接缺失(null/undefined/负)全空白", M.fmtPeersQb(null, 10) === "" && M.fmtPeersQb(undefined, 10) === "" && M.fmtPeersQb(-1, 10) === "");
ok("已连接 0 是有效值(确实零连接)", M.fmtPeersQb(0, 10) === "0 (10)");
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#193: fx 挂载层(fx-mount.js) -------------------------------------------------
# fx-mount.js 是 IIFE, 顶层就要 window.AQB_FX 与 document —— 桩最小 DOM/BOM 后 eval 真跑;
# TOAST_SPLIT/rows 是模块私有, 经导出面 toastSync/rows 驱动(与浏览器消费点同一入口)。
_NODE_FX_MOUNT_PROBE = r"""
const fs = require("fs");
const rafQ = [];
let scans = 0;
function mkEl(tag) {
  const el = {
    tagName: String(tag).toUpperCase(),
    children: [], className: "", textContent: "",
    _classes: [], attrs: {},
    parentElement: null, isConnected: true,
    scrollTop: 0, scrollLeft: 0,  // 真实 DOM 默认 0(幽灵定格几何要用)
    _rect: { top: 0, left: 0, width: 800, height: 40 },
    style: { _props: {}, setProperty(k, v) { el.style._props[k] = v; } },
    classList: {
      add: (c) => el._classes.push(c),
      remove: () => {}, toggle: () => {},
    },
    appendChild(c) { el.children.push(c); return c; },
    querySelector: () => null,
    setAttribute(k, v) { el.attrs[k] = v; },
    getAttribute(k) { return k in el.attrs ? el.attrs[k] : null; },
    hasAttribute(k) { return k in el.attrs; },
    removeAttribute(k) { delete el.attrs[k]; },
    cloneNode() { const c = mkEl("div"); c.attrs = Object.assign({}, el.attrs); c._rect = el._rect; return c; },
    getBoundingClientRect() { return el._rect; },
  };
  return el;
}
const bySel = {};
const wrap = mkEl("div");
wrap.querySelectorAll = () => wrap.children;
global.window = { CSS: null };
global.window.AQB_FX = { reduced: () => false, ripple() {}, dir() {}, scan() { scans++; }, viewTransition(fn) { fn(); } };
global.document = {
  addEventListener: () => {}, removeEventListener: () => {},
  documentElement: { classList: { add() {}, remove() {} } },
  querySelector: (sel) => (sel === ".toast-wrap" ? wrap : bySel[sel] || null),
  querySelectorAll: () => [],
  createElement: (tag) => mkEl(tag),
};
global.requestAnimationFrame = (cb) => { rafQ.push(cb); return rafQ.length; };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src);
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);
const MNT = window.AQB_FX_MOUNT;

// ---------- TOAST_SPLIT 拆段正则(经 toastSync 消费面驱动) ----------
function mkToast(text, cls, id) {
  const span = mkEl("span");
  span.textContent = text;
  const n = mkEl("div");
  n.children.push(span);
  n.attrs["class"] = cls || "toast";
  if (id != null) n.attrs["data-id"] = id;
  return { n, span };
}
const t1 = mkToast("已执行: 重命名", "toast", "id1");
const t2 = mkToast("无分隔符的一句话", "toast", "id2");
const t3 = mkToast("一二三四五六七八九十甲乙丙丁戊: 说明超限", "toast", "id3");  // 头 15 字 > 14 上限
const t4 = mkToast("一二三四五六七八九十甲乙丙丁: 边界十四字", "toast", "id4");  // 头恰 14 字
const t5 = mkToast("复制(3): 文件", "toast", "id5");                            // 括号不是分隔符
const t6 = mkToast("已执行:x", "toast", "id6");                                 // 说明不足 2 字(无空格)
const t7 = mkToast("已执行: 重命名", "toast", "id7");                           // 全角冒号
const t8 = mkToast("已复制, 名称已写入剪贴板", "toast", "id8");                  // 逗号分隔
const t9 = mkToast("保存失败: 磁盘已满", "toast error", "id9");                  // danger 原位升级
const t10 = mkToast("已执行: x", "toast", "id10");  // 说明侧 trim 后 1 字: 连接空格不算门槛 -> 单行(issue 26-11-08-0229 #12)
const t11 = mkToast("已复制: 名称 ", "toast", "id11");  // 尾随空格容忍: 说明 trim 后恰 2 字 -> 照拆
const toasts = [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11];
wrap.children.push(...toasts.map((t) => t.n));
MNT.toastSync(4000, "id1");
ok("拆段: 半角冒号两段落地(标题+说明)", t1.span.children.length === 2
  && t1.span.children[0].className === "toast-t" && t1.span.children[0].textContent === "已执行"
  && t1.span.children[1].className === "toast-s" && t1.span.children[1].textContent === "重命名");
ok("拆段: 全角冒号同族", t7.span.children.length === 2
  && t7.span.children[0].textContent === "已执行" && t7.span.children[1].textContent === "重命名");
ok("拆段: 逗号分隔(说明为名字/计数)", t8.span.children.length === 2
  && t8.span.children[0].textContent === "已复制" && t8.span.children[1].textContent === "名称已写入剪贴板");
ok("拆段: 头恰 14 字上界命中", t4.span.children.length === 2
  && t4.span.children[0].textContent === "一二三四五六七八九十甲乙丙丁");
ok("残留单行: 无分隔符", t2.span.children.length === 0 && t2.span._classes.includes("toast-txt"));
ok("残留单行: 头 15 字超上限(拆段退回单行)", t3.span.children.length === 0);
ok("残留单行: 括号不是分隔符", t5.span.children.length === 0);
ok("残留单行: 说明不足 2 字(无空格)", t6.span.children.length === 0);
ok("残留单行: 说明侧 trim 后 1 字(分隔符后连接空格不计入门槛, issue 26-11-08-0229 #12)", t10.span.children.length === 0);
ok("拆段: 说明 trim 后恰 2 字且带尾随空格照拆", t11.span.children.length === 2
  && t11.span.children[0].textContent === "已复制" && t11.span.children[1].textContent === "名称");
ok("单行也挂 toast-txt(flex:1/min-width:0 生效)", t2.span._classes.includes("toast-txt"));
ok("stamp: 新条 rise + 队列牌(栈内已有多条)", t1.n.attrs["data-fx"] === "rise" && t1.n.attrs["data-fx-queue"] === "");
ok("stamp: 倒计时只归 own 条(ttl 精确命中 data-id)", t1.n.attrs["data-fx-cd"] === "" && t2.n.attrs["data-fx-cd"] === undefined);
ok("stamp: danger 条原位升级 rise danger", t9.n.attrs["data-fx"] === "rise danger");
ok("文本安全: 标题/说明经 textContent 落地(非 innerHTML)", t1.span.children[0].textContent === "已执行");
ok("扫描: FX.scan 被触发", scans > 0);

// ---------- rows 行差分与幽灵退场 ----------
const cont = mkEl("div");
const rowN = { a: mkEl("div"), b: mkEl("div"), c: mkEl("div") };
rowN.a.parentElement = cont; rowN.a._rect = { top: 10, left: 0, width: 800, height: 44 };
rowN.b.parentElement = cont; rowN.b._rect = { top: 54, left: 0, width: 800, height: 44 };
rowN.c.parentElement = cont; rowN.c._rect = { top: 98, left: 0, width: 800, height: 44 };
bySel['[data-hash="a"]'] = rowN.a;
bySel['[data-hash="b"]'] = rowN.b;
bySel['[data-hash="c"]'] = rowN.c;
const row = (h) => ({ hash: h });
const scansBefore = scans;
MNT.rows([row("a"), row("b")], "hash");
ok("rows 首轮只建缓存(零 rAF 零扫描)", rafQ.length === 0 && scans === scansBefore);
MNT.rows([row("a"), row("c")], "hash");
ok("rows 差分: 检出增删后排一帧", rafQ.length === 1);
rafQ.shift()();
ok("幽灵退场: b 行克隆以 row-out 附回原容器", cont.children.length === 1
  && cont.children[0].getAttribute("data-fx") === "row-out");
ok("幽灵定格: top/宽写进内联样式", cont.children[0].style.top === "54px"
  && cont.children[0].style.width === "800px");
ok("幽灵定格: --fx-row-h 覆写实际行高(44px)", cont.children[0].style._props["--fx-row-h"] === "44px");
ok("入场行: c 行 stamp row-in", rowN.c.getAttribute("data-fx") === "row-in");
ok("差分扫描: FX.scan 被触发", scans > scansBefore);
MNT.rows([row("a"), row("c")], "hash");
ok("rows 无增删: 不排帧(幂等重扫不空转)", rafQ.length === 0);

console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_r4_winmembers_sorted_window_same_source():
    """R5#35(major) 修复回归: winMembers 三入口先排序再开窗, 切片/前缀和/占位/键盘行序同源"""
    report = _run_probe(
        _NODE_WINMEMBER_PROBE,
        bundle_file("columns.js"),
        os.path.join(STATIC_ROOT, "shared", "sort.js"),
    )
    _assert_battery(report, "winMembers 同源电池")


def test_r4_groupwin_expand_backoff():
    """R5#57: groupWin 退避判据 = 当前真的有面板; 不在场/未展开保持窗口"""
    report = _run_probe(_NODE_GROUPWIN_BACKOFF_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "groupWin 退避电池")


def test_r4_apply_col_order_boundaries():
    """R5#53: applyColOrder 落点折算四类边界 + 隐藏列相对次序不动 + 尊重既有 colOrder"""
    report = _run_probe(_NODE_APPLY_COL_ORDER_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "applyColOrder 边界电池")


def test_r4_col_persist_intent_merge_and_gates():
    """R5#52(major) + R5#37/R5#38: 意图升格三层 merge + 纯点击门槛 + 拦截自清"""
    report = _run_probe(_NODE_COLPERSIST_MERGE_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "列持久化意图升格电池")


def test_r4_selection_state_machine():
    """R5#51(major): _selSyncGroups 四态 / _selAnchor 兜底链 / selSizeSummaryOf 去重"""
    report = _run_probe(_NODE_SELECTION_PROBE, os.path.join(STATIC_ROOT, "shared", "selection.js"))
    _assert_battery(report, "选择联动状态机电池")


def test_r4_load_col_state_seeding():
    """R5#18: loadColState 播种三态(空存储/仅空 hidden/任一偏好键) + 坏数据 + 白名单洗净"""
    head_path = os.path.join(tempfile.gettempdir(), "aqb_app_head_for_probe.js")
    with open(head_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_app_head_source())
    report = _run_probe(_NODE_LOADCOLSTATE_PROBE, head_path)
    _assert_battery(report, "loadColState 播种电池")


def test_r4_sort_domain():
    """R5#54: setSort 三态循环(经典/dyn 两形态) + _dtStrCompare + sortedDrawer 空值恒末位"""
    report = _run_probe(_NODE_SORT_PROBE, os.path.join(STATIC_ROOT, "shared", "sort.js"))
    _assert_battery(report, "排序域电池")


def test_r4_format_ladder_family():
    """R5#55: _fmtLadder 梯顶回落 + fmtEta 哨兵 + fmtDuration 三段进位 + fmtPeersQb 缺省"""
    report = _run_probe(_NODE_FORMAT_PROBE, os.path.join(STATIC_ROOT, "shared", "format.js"))
    _assert_battery(report, "format 函数族电池")


def test_r4_fx_mount_toast_split_and_rows_ghost():
    """R5#193: fx 挂载层 node 电池 —— TOAST_SPLIT 拆段正则族 + rows 行差分与幽灵退场"""
    report = _run_probe(_NODE_FX_MOUNT_PROBE, os.path.join(STATIC_ROOT, "flux", "fx-mount.js"))
    _assert_battery(report, "fx 挂载层电池")


# R5#95/R5#81(P13): 05 变体 rowsFn 真跑(node 电池) ------------------------------------------
# 沙箱口径: drawer_templates.js 在无 DOM 下自发布 window.AQB_DRAWER_TPL_REG(dtInjectCss 等
# 载荷全部自带 typeof document 守卫); 05 IIFE 消费真 reg(dtHtml/helpers/trackers 单源)自注册,
# 电池经 reg.get 取回 rowsFn —— 判据走生产函数, 不经字符串锚。ctx 桩只给 rowsFn 需要的四件
# (drawer.trackers / drawerTrackerVirtual / drawerReannounceGate / fmtPeersQb)。
_NODE_DT05_ROWSFN_PRELUDE = r"""
const fs = require("fs");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
global.window = {};
let reg = null;
try {
  eval(fs.readFileSync(process.argv[1], "utf8"));  // drawer_templates.js -> window.AQB_DRAWER_TPL_REG
  reg = global.window.AQB_DRAWER_TPL_REG;
} catch (e) { ok("drawer_templates.js 加载失败: " + e.message, false); }
if (!reg || !reg.trackers) ok("reg/trackers 未发布(沙箱口径漂移)", false);
let def = null;
if (reg && reg.trackers) {
  try {
    eval(fs.readFileSync(process.argv[2], "utf8"));  // 05-trackers-health-groups-low.js
    def = reg.get("trackers", "05");
  } catch (e) { ok("05 变体加载失败: " + e.message, false); }
}
if (!def || typeof def.rowsFn !== "function") ok("05 rowsFn 未注册", false);
// rowsFn 需要的 ctx 四件(drawer.trackers / 虚拟判据 / 重报闸门 / peers 计数格式化)
const mkCtx = (trackers) => ({
  drawer: { trackers: trackers },
  drawerTrackerVirtual: () => false,
  drawerReannounceGate: () => ({ ok: true, title: "" }),
  fmtPeersQb: (a) => String(a == null ? 0 : a),
});
const segRow = (trackers, segKey, i) => {
  const segs = def.rowsFn(mkCtx(trackers));
  const seg = segs.find((s) => s.key === segKey);
  return seg && seg.rows[i] ? seg.rows[i] : null;
};
"""

_NODE_DT05_ADVICE_PROBE = _NODE_DT05_ROWSFN_PRELUDE + r"""
// R5#95: adviceFor 五类关键词分派(经 err 桶 failRowOf 装配路径 = 生产行对象 .advice)。
// 样本逐条核对过分派序(unregistered -> passkey -> ban -> timeout -> maintenance -> 兜底),
// 互不越档命中。
const CASES = [
  ["not registered 类", "torrent not registered with this tracker", "站点删除"],
  ["passkey 类", "invalid passkey", "鉴权信息疑似失效"],
  ["ban 类", "you are banned by the tracker", "客户端或行为可能被站点限制"],
  ["timeout 类", "connection timed out", "网络层不可达"],
  ["maintenance 类", "site is under maintenance", "站点侧暂时不可用"],
];
for (const [name, msg, marker] of CASES) {
  const row = segRow([{ url: "https://t.example/announce", status: 4, tier: 0, msg: msg }], "err", 0);
  ok(name + "走失败处置块形态(kind=fail)", !!row && row.kind === "fail");
  ok("adviceFor " + name + " 分派命中各自文案", !!row && String(row.advice).indexOf(marker) >= 0);
}
// 通用兜底分支: 零命中 -> 「先点强制重新汇报」通用话术(此前五类 + 兜底全无覆盖, R5#95)
const fb = segRow([{ url: "https://t.example/announce", status: 4, tier: 0, msg: "weird unknown failure" }], "err", 0);
ok("adviceFor 通用兜底分支", !!fb && String(fb.advice).indexOf("先点「强制重新汇报」") >= 0);
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""

_NODE_DT05_TIER_PROBE = _NODE_DT05_ROWSFN_PRELUDE + r"""
// R5#81: ok 组 tier 升序的缺失/非法 tier 兜底。a=T1 / b=缺 tier / c=T0 / d=非法 "x":
// 修后(记 9)序 = c(0), a(1), b(9), d(9)(9 档并列保 qB 原序: b 先于 d);
// 修前(折算 0)序 = b, c, d, a —— tier 缺失的 tracker 插到所有 tier0 之前。
const mk = (url, tier) => {
  const t = { url: url, status: 2, msg: "", num_seeds: 1, num_complete: 1,
    num_leeches: 0, num_incomplete: 0, num_downloaded: 0 };
  if (tier !== undefined) t.tier = tier;
  return t;
};
const trackers = [
  mk("https://a.example/announce", 1),
  mk("https://b.example/announce"),        // tier 缺失
  mk("https://c.example/announce", 0),
  mk("https://d.example/announce", "x"),   // 非法 tier(负值/非数值同档)
];
const segs = def.rowsFn(mkCtx(trackers));
const seg = segs.find((s) => s.key === "ok");
const order = (seg ? seg.rows : []).map((r) => r.host);
ok("ok 组恰 4 行(缺 tier 不得跌出 ok 桶)", order.length === 4);
ok("tier0(c)居首(修复前缺失 tier(b)插队最前)", order[0] === "c.example");
ok("tier 升序次位 = tier1(a)", order[1] === "a.example");
ok("缺失 tier(b)与非法 tier(d)殿后且保 qB 原序(记 9 稳定序)", order[2] === "b.example" && order[3] === "d.example");
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""


def test_r4_dt05_advice_dispatch():
    """R5#95(P13): 05 adviceFor 五类关键词分派 + 通用兜底 —— rowsFn 真跑不经字符串锚"""
    report = _run_probe(
        _NODE_DT05_ADVICE_PROBE,
        os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"),
        os.path.join(STATIC_ROOT, "shared", "drawer_tpl", "05-trackers-health-groups-low.js"),
    )
    _assert_battery(report, "05 adviceFor 分派电池")


def test_r4_dt05_tier_sort_missing_last():
    """R5#81(P13) 修复回归: 05 ok 组 tier 排序缺失/非法 tier 记 9 殿后(与 04/06 同口径)"""
    report = _run_probe(
        _NODE_DT05_TIER_PROBE,
        os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"),
        os.path.join(STATIC_ROOT, "shared", "drawer_tpl", "05-trackers-health-groups-low.js"),
    )
    _assert_battery(report, "05 tier 兜底电池")


# issue 26-11-08-0229 #2: drawerGeneralSections 契约层传输行 qB -1/null 哨兵守卫(node 电池) --
# 沙箱口径: drawer_rows.js 是 Object.assign(window.AQB_DRAWER.methods, ...) 片段, 电池自给
# AQB_DRAWER 域后 eval; this 桩只给 drawerGeneralSections 消费的格式化方法族(恒真值, 不参与
# 哨兵判据) —— 判据走契约层生产函数(peerNum/connLimit 本尊), 不经字符串锚。
_NODE_DRAWER_ROWS_SENTINEL_PROBE = r"""
const fs = require("fs");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
global.window = { AQB_DRAWER: { methods: {} } };
try {
  eval(fs.readFileSync(process.argv[1], "utf8"));  // drawer_rows.js -> AQB_DRAWER.methods
} catch (e) { ok("drawer_rows.js 加载失败: " + e.message, false); }
const M = global.window.AQB_DRAWER.methods;
if (typeof M.drawerGeneralSections !== "function") ok("drawerGeneralSections 未加载", false);
// this 桩: drawerGeneralSections 消费的格式化族(返回恒真值, 保证非哨兵行正常装配)
const mkVm = (detail) => ({
  drawer: { detail },
  fmtDuration: (v) => "d" + v, fmtTs: () => "ts", fmtSize: (v) => "s" + v,
  fmtSizeOrDash: (v) => "s" + v, fmtSpeedOrDash: () => "v", fmtEta: () => "e",
  relocateStateText: (s) => s, relocateOriginText: (s) => s,
});
const trRow = (detail, label) => {
  const secs = M.drawerGeneralSections.call(mkVm(detail));
  const tr = secs.find((s) => s.title === "传输");
  const r = tr && tr.rows.find((x) => x.label === label);
  return r ? r.text : null;
};

// 场景1 私有种子: num_complete/num_incomplete/connections_limit = -1 是「无数据/不限」哨兵
// (修复前裸拼渲染 完整/下载中 -1 / -1、连接 8 / -1)
ok("私有种子: 做种数真值照显", trRow({ num_seeds: 3, num_complete: -1, num_incomplete: -1, connections_count: 8, connections_limit: -1 }, "做种数") === "3");
ok("私有种子: 完整/下载中哨兵降级 — / —", trRow({ num_seeds: 3, num_complete: -1, num_incomplete: -1, connections_count: 8, connections_limit: -1 }, "完整/下载中") === "— / —");
ok("私有种子: 连接上限 -1 译「不限」", trRow({ num_seeds: 3, num_complete: -1, num_incomplete: -1, connections_count: 8, connections_limit: -1 }, "连接") === "8 / 不限");

// 场景2 字段缺失(null/undefined): ?? 0 只兜缺失, 守卫后统一降级 —
ok("缺失字段: 做种数 null 降级 —", trRow({ num_seeds: null, num_complete: null, num_incomplete: null, connections_count: null, connections_limit: null }, "做种数") === "—");
ok("缺失字段: 完整/下载中降级 — / —", trRow({ num_seeds: null, num_complete: null, num_incomplete: null, connections_count: null, connections_limit: null }, "完整/下载中") === "— / —");
ok("缺失字段: 连接降级 — / —", trRow({ num_seeds: null, num_complete: null, num_incomplete: null, connections_count: null, connections_limit: null }, "连接") === "— / —");

// 场景3 真值形态逐字不变(守卫不得改动正常数据的显示)
ok("真值: 做种数照显", trRow({ num_seeds: 3, num_complete: 10, num_incomplete: 5, connections_count: 8, connections_limit: 100 }, "做种数") === "3");
ok("真值: 完整/下载中照显", trRow({ num_seeds: 3, num_complete: 10, num_incomplete: 5, connections_count: 8, connections_limit: 100 }, "完整/下载中") === "10 / 5");
ok("真值: 连接照显", trRow({ num_seeds: 3, num_complete: 10, num_incomplete: 5, connections_count: 8, connections_limit: 100 }, "连接") === "8 / 100");

const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""


def test_r4_drawer_general_rows_qb_sentinels():
    """issue 26-11-08-0229 #2 修复回归: 传输行 做种数/完整下载中/连接 对 -1/null 哨兵降级, 真值不变"""
    report = _run_probe(_NODE_DRAWER_ROWS_SENTINEL_PROBE, os.path.join(STATIC_ROOT, "shared", "drawer_rows.js"))
    _assert_battery(report, "drawer 传输行哨兵电池")
