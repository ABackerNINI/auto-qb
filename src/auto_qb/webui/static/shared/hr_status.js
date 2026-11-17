/* auto-qb WEB UI · HR 站点级状态(设置页「HR 在线核实」分区的页尾「站点状态」块)
 *
 * 数据来自只读端点 `/api/hr/status`, 字段口径单点在 `auto_qb/hr/status.py`(与 `--hr-status`
 * 同一层) —— 本文件**只做展示**: 不重算阈值、不重算新鲜度, 只把后端给的人话与数字摆出来
 * (前端重算 = 自定义阈值/周期一改就静默失效, 见 pitfalls: HR 判定前后端各写一遍)。
 *
 * !加载时机: 打开「HR 在线核实」分区时拉一次(config_hub.js hubGo), 之后手动刷新
 *   (不轮询: 站点数据的小时级节奏不需要前端高频拉, 而轮询会给 Web 线程添无谓负载)。
 * !种子明细(表(1), 计划 26-10-01-2216 阶段2): /api/hr/sites/<site>/entries 按站点**按需**
 *   拉一次(打开分区/手动刷新时随 loadHrStatus 触发, 拍板(2)b), 不进 /api/hr/status 全量
 *   响应也不进 /api/state 轮询载荷(pitfalls/web-ui/contract-api.md: 只在用户显式动作时才
 *   需要的字段不塞轮询载荷); 单站点失败只置该站错误态(.empty 错误行), 不阻塞分区其余内容;
 *   无新增定时器。
 * !排障视图(表(2), 计划 26-10-01-2216 阶段3): 站点级 kv 行(hrsKvRows)+ 各档波次明细
 *   (hrsWaveCutoff/hrsWaveCount)全部取自 /api/hr/status 现有载荷, **零新请求**; 收进
 *   <details> 默认收起, 展开态不持久化(临时排障动作)。
 * !拉取历史(表(3), 计划 26-10-04-0312): 只读端点 /api/hr/history 按需拉一次(limit=300,
 *   表(3) <details> 首次展开 @toggle 触发 hrsHistEnsureLoaded), 「刷新」手动重拉, 不轮询;
 *   站点 chips 与「仅看异常」纯前端本地过滤不回后端; 行人话(22 键)全由后端算好, 前端只挑
 *   徽章色档与排版。状态挂 hrsHist —— 与 hrs 同一份 mixin data 的伴生键(hrs 根对象键集被
 *   test_frontend_hr_status_fields_match_backend 闭集钉住, 不往里加新键), 方法前缀 hrsHist*。
 * !入口只有一个(2026-09-25 合并): Console Hub「HR 在线核实」分区页尾 —— 曾经的经典设置页
 *   章节与独立首页卡片都已随旧版设置页移除, 别再加回第二套入口。
 * !表身份(P5, 计划 26-10-11-1722; 26-11-17-0059 W1 E6 并入 + W1(3) grid 迁移落地; W2(2)(3)(4)):
 *   三张 HR 表的列定义单点在模块级 HR_TABLE_DEFS, 经 window.AQB_HR_TABLE_DEFS 并进 app.js 的
 *   ALL_TABLE_DEFS(page 键 hrDetail/hrWave/hrKv) —— 几何/交互/持久化全量走主表同款链路:
 *   gridTemplate/列序/隐藏经 _gridTemplate/DT_TABLE.layout 单点, 表头四项交互由 <aq-table> grid
 *   根自带, 列偏好落 autoqb_cols_v5 新 page 子树(不升版本, 读侧还原 = loadColState 全集遍历),
 *   HR 分组进列选择器 = 隐藏列恢复入口(E6; 旧口径「不进 TABLE_PAGES 防列选择器多分组」是零交互
 *   时代的理由, 交互化后作废: 那时右键隐藏不可逆才怕多分组)。详情表表头不再借 <aq-table> thead
 *   模式(该模式已随本迁移退役)。渲染自查(W2(3))走 headDom: true 锚进根 updated 的
 *   _assertLayouts(未展开 v-show 无盒 = 未挂载豁免, R4 口径); 值格渲染注册化(W2(4) E2)见
 *   HR_CELL_RENDERERS / AQB_HR_CELLS_REGISTER / mixin 方法 hrCellOf。几何面 W3(1) 起由 parity
 *   守阵 e2e/dt-table-layout-parity.spec.mjs 增 HR 三面钉住单点输出(hrDetail 10 / hrWave 8 /
 *   hrKv 2 列; route 拦截喂合成载荷)。
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾 mixin window.AQB_HR_STATUS)。
 */

/* ---------------- 表(1) 排序纯函数(计划 26-10-02-1936 §3.4, 阶段3) ----------------
 * 模块级单例(不走 app.mixin, 被 hrsDetailRows 与守阵的 node 单测直接消费 —— frontend-split
 * 「非 mixin 单例」书写形态)。排序语义对齐 shared/sort.js 三态, 但比较器收在这里:
 * - 按原始值排不按人话: bytes/ratio/秒/epoch 数值比较, 名称/tid/done_iso 字符串比较,
 *   档位按 A<B<C<D 固定秩(不存在档排最后);
 * - 空值恒排最后(两个方向都不参与反转): null/undefined/空串是通用空; verified_ts/last_seen
 *   的 0 是哨兵(未核实/未见, hrsVerifiedText 同纪律), 也算空;
 * - 比较器不写 dir 进空值分支 —— dir 只乘在非空比较结果上; 同值靠 Array.sort 稳定性
 *   保住后端默认序(档位·下载量), 不另设 tiebreak。 */
const HRS_LANE_RANK = { A: 0, B: 1, C: 2, D: 3, _UNK: 9 };
const HRS_SORT_VAL = {
  lane: (e) => HRS_LANE_RANK[e.lane] === undefined ? HRS_LANE_RANK._UNK : HRS_LANE_RANK[e.lane],
  name: (e) => e.name || "",
  tid: (e) => e.tid,
  uploaded_bytes: (e) => e.uploaded_bytes,
  downloaded_bytes: (e) => e.downloaded_bytes,
  ratio: (e) => e.ratio,
  need_seed_seconds: (e) => e.need_seed_seconds,
  done_iso: (e) => e.done_iso || "",
  verified_ts: (e) => e.verified_ts || 0,
  last_seen: (e) => e.last_seen || 0,
};
/* 空值判据(key 维度): verified_ts/last_seen 用 0 当哨兵, 其余 null/undefined/空串 */
function hrsValEmpty(key, v) {
  if (v === null || v === undefined || v === "") return true;
  return (key === "verified_ts" || key === "last_seen") && v === 0;
}
/* 终态档判据(B3 中间态用): B 已达标 / C 未达标 / D 已免罪 —— 非 A 考察中即终态;
 * 与后端 lane_is_terminal 同口径(仅挡 A), 但前端只用于**展示措辞**不参与判定 */
function hrsTerminalLane(lane) {
  return lane === "B" || lane === "C" || lane === "D";
}
function hrsCompareRows(a, b, key, dir) {
  const acc = HRS_SORT_VAL[key];
  const va = acc(a);
  const vb = acc(b);
  const ea = hrsValEmpty(key, va);
  const eb = hrsValEmpty(key, vb);
  if (ea || eb) {
    if (ea && eb) return 0;
    return ea ? 1 : -1; /* 空值恒末位: 不随 dir 反转 */
  }
  const r = typeof va === "string" ? va.localeCompare(vb) : va - vb;
  return r * dir;
}

/* ---------------- 表(3) 拉取历史常量与判据(计划 26-10-04-0312 §3.5, 模块级单例) ----------------
 * token 都是后端字面量, 只比对不重算: BAD_ACTIONS = 波终态里算「异常」的四个 action
 * (kind='defer' 的拦下载不论 action 一律算异常, 计划 §3.5 拍板); TONES = result_tone 徽章
 * 色档白名单(后端 HISTORY_RESULT_BADGES 色档族), 未知档回落 dim(与后端未知 action 回落
 * dim 同款兜底); LIMIT = 单页拉取条数(拍板值, 与端点缺省一致)。 */
const HRS_HIST_LIMIT = 300;
const HRS_HIST_BAD_ACTIONS = ["error", "no-channel", "waiting", "skipped-locked"];
const HRS_HIST_TONES = ["ok", "warn", "dim", "err", "blue"];
function hrsHistIsBad(r) {
  return HRS_HIST_BAD_ACTIONS.indexOf(r.action) >= 0 || r.kind === "defer";
}

/* ---------------- HR 表注册表(计划 26-10-11-1722 P5; 26-11-17-0059 W1 并入全局枚举 + grid 迁移) ----------------
 * 「HR 表身份」单点: 与主视图 TABLE_DEFS 同**模型**(label + columns + features + 描述符字段),
 * 本体保留在本文件(HR 列语义与 hrs* 方法同址), 经 window.AQB_HR_TABLE_DEFS 桥并进 app.js 的
 * ALL_TABLE_DEFS(E6: page 键 hrDetail/hrWave/hrKv) —— 枚举面(列偏好持久化/对齐注入/选择器
 * 枚举/断言)与交互面(拖宽/拖序/右键隐藏)都由 grid 表头 DOM + ALL_TABLE_PAGES 遍历驱动,
 * W1(3) grid 迁移落地后全量生效。HR 分组进列选择器 = E6 拍板的隐藏列恢复入口(过桥门
 * pickerHold 已随 W1(3) 摘除; 旧口径「不并防多分组」是零交互时代的理由, 已作废, 见头注)。
 * window 桥 + app.js 侧空对象兜底 = node 沙箱(app.js 截断切片, 无本文件)里 ALL_TABLE_DEFS
 * 仍可求值(AQB_DRAWER_TPL_DEFS 同款先例); 生产四皮肤 manifest 本文件恒先于 app.js 载入,
 * 恒有值(装载序守阵: test_frontend_table_registry_single_point 四皮肤断言)。
 * 加一张 HR 表 = 在此加一行 + 模板里挂调用点(aq-table grid 根 + .group-row 行) +
 * columns_computed.js 挂一对 computed。
 *
 * columns: 列定义(key/label 与既有表头逐字一致)。26-11-17-0059 W1(1) 起每列补 tpl(轨道串,
 *   直接喂 DT_TABLE.layout 单点)与 align(colAlignCss 注入消费)。R1 实证拍板: HR 面在
 *   .hr-full-modal v-show 未展开时 display:none, 窗口实测轨拿不到可用宽度(columns_persist
 *   recomputeEffective 的 _headEl 对无盒表头返回 null), 故三表默认走 **tpl 显式宽度**(固化轨);
 *   tpl 首切值按现网原生表观感估定, W1(3) 迁 HTML 时按逐列保真清单手验。
 *   hrDetail 十列全带 sortable: true —— 判据 = HRS_SORT_VAL 十键全有访问器(真能排的才标);
 *   漏标 = grid 表头行为侧 headActivate 按 col.sortable 早退, 该列静默失去排序(issue
 *   26-10-29-1348: 曾十列全漏, 表壳却按「可排序」画箭头/挂可点类, 视觉与行为各取一半)。
 * features: 只声明差异 —— hrDetail 有 sort(E8: 排序并入引擎 setSort, W1(4) 落地);
 *   hrWave / hrKv 无排序(sortable 零标记, headActivate 按 col.sortable 早退; 波次表行数 ≤4
 *   不接排序, 计划 26-10-02-1936 §3.4 的旧「纯展示不接线」口径仅指排序面) —— 拖宽/拖序/右键
 *   隐藏按 E1 全量统一拍板, grid 迁移后与主表同链路(W1(3) 落地), 不按表裁剪。
 * locked: hrKv k 列 locked(E7, 拆散 k/v 对不可表达); hrDetail 无 locked 身份列 —— 零列态
 *   (全隐藏)恢复入口 = 列选择器(E6 分组), 不另设 locked(不扩大 E7 拍板范围, 终验可再议)。
 * sort: dyn 形态(排序状态进根 data 的 dtSortState 映射, 与抽屉变体表同款) —— 随并入登记,
 *   使 grid 表头点击的 $root.setSort(key, tableId) 对 HR 面良定义(sort.js _sortKeys 读
 *   ALL_TABLE_DEFS[id].sort, 缺描述符即 TypeError); 行消费侧 hrsDetailRows 读 dtSortCell,
 *   E8(W1(4))已切换。hrWave/hrKv 无 sortable 列, 描述符纯为 registry 良定义(点击不可达)。
 * header: false 已删(E7, 26-11-17-0059): hrKv 补列头「项/值」, k 列 locked —— 拆散 k/v 对的
 *   操作(隐藏 k/拖走 k)不可表达(隐藏侧 headMenuHide/toggleColumn 引擎既有守卫, 拖序侧 W2)。
 * stickyHead: false(三表, W1(3) T2 拍板): sticky-head 是「参与主视图吸顶几何」的标记类
 *   (_ensureHeadObserver/_syncHeadHeight 按 .sticky-head 量顶栏高写 :root --head-h), HR 模态头
 *   在 .hr-full-modal 内、无吸顶语义且 v-show 关闭态高度 0, 不进那套测量 —— 表壳组件按本字段
 *   出 group-head 裸形(table.js headRootCls 单点)。
 * 表头渲染: 三表全走表壳组件 grid 模式(thead 借壳模式已随迁移退役, shared/table.js)。 */
const HR_TABLE_DEFS = {
  hrDetail: {
    label: "HR 明细表", features: { sort: true },
    grid: "hrDetailGrid", cols: "visibleHrDetailCols", headRef: null, tableRef: null, window: null,
    stickyHead: false,
    /* headDom(W2(3), 计划 26-11-17-0059): assertLayout 挂载锚 —— 表头/行同在根模板(设置页),
     * 根 updated 后置队列盖得住, 但 aq-table 子组件 ref 不进根 $refs(headRef 保持 null),
     * 故走 columns_grid._assertLayouts 的 headDom 分支: _headEl DOM 兜底取**首个有盒**表头
     * (模态未展开 v-show display:none / details 收起 = 无盒 = 未挂载豁免, R4 口径), 不逐面扫桥。 */
    headDom: true,
    sort: { dyn: true, defKey: "", defDir: -1 },
    columns: [
      { key: "lane", label: "档位", tpl: "84px", align: "left", sortable: true },
      { key: "name", label: "名称", tpl: "minmax(180px, 2.2fr)", align: "left", sortable: true },
      { key: "tid", label: "tid", tpl: "minmax(110px, 1.1fr)", align: "left", sortable: true },
      { key: "uploaded_bytes", label: "上传量", num: true, tpl: "minmax(92px, 1fr)", align: "right", sortable: true },
      { key: "downloaded_bytes", label: "下载量", num: true, tpl: "minmax(92px, 1fr)", align: "right", sortable: true },
      { key: "ratio", label: "分享率", num: true, tpl: "84px", align: "right", sortable: true },
      { key: "need_seed_seconds", label: "还需做种", num: true, tpl: "minmax(96px, 1fr)", align: "right", sortable: true },
      { key: "done_iso", label: "完成时间", tpl: "104px", align: "left", sortable: true },
      { key: "verified_ts", label: "核实结论", tpl: "minmax(150px, 1.4fr)", align: "left", sortable: true },
      { key: "last_seen", label: "在列", tpl: "minmax(130px, 1.2fr)", align: "left", sortable: true },
    ],
  },
  hrWave: {
    label: "HR 波次表", features: {},
    grid: "hrWaveGrid", cols: "visibleHrWaveCols", headRef: null, tableRef: null, window: null,
    stickyHead: false,
    headDom: true,  /* W2(3): 同 hrDetail(headDom 分支注释在彼处) */
    sort: { dyn: true, defKey: "", defDir: -1 },
    columns: [
      { key: "lane", label: "档位", tpl: "84px", align: "left" },
      { key: "status", label: "状态", tpl: "minmax(110px, 1.2fr)", align: "left" },
      { key: "pages", label: "页数", num: true, tpl: "72px", align: "right" },
      { key: "rows", label: "行数", num: true, tpl: "72px", align: "right" },
      { key: "cutoff", label: "截至深度", num: true, tpl: "minmax(96px, 1fr)", align: "right" },
      { key: "fail_streak", label: "连续失效", num: true, tpl: "84px", align: "right" },
      { key: "count", label: "对平(声称/命中)", num: true, tpl: "minmax(96px, 1fr)", align: "right" },
      { key: "detail", label: "说明", tpl: "minmax(160px, 2fr)", align: "left" },
    ],
  },
  hrKv: {
    label: "HR 诊断表", features: {},
    grid: "hrKvGrid", cols: "visibleHrKvCols", headRef: null, tableRef: null, window: null,
    stickyHead: false,
    headDom: true,  /* W2(3): 同 hrDetail(headDom 分支注释在彼处) */
    sort: { dyn: true, defKey: "", defDir: -1 },
    columns: [
      { key: "k", label: "项", tpl: "minmax(104px, 0.8fr)", align: "left", locked: true },
      { key: "v", label: "值", tpl: "minmax(260px, 2.6fr)", align: "left" },
    ],
  },
};
/* 并入桥(app.js 的 ALL_TABLE_DEFS 消费; 头注与注册表段注有完整口径) */
window.AQB_HR_TABLE_DEFS = HR_TABLE_DEFS;

/* ---------------- 值格渲染器注册表(26-11-17-0059 W2(4) E2, dt_table 六口子全活) ----------------
 * 三表手写值格 v-if 链(settings-detail.html W1(3) 迁 grid 后的 DOM 载体)收敛为**数据描述符**:
 * 每列一个渲染器, 注册进 DT_TABLE.CELLS(registerCell, 名字 = "<tableId>.<列key>"), 模板经
 * mixin 方法 hrCellOf(见 AQB_HR_STATUS.methods) -> DT_TABLE.cellOf 消费 —— 单元格渲染化后
 * 「哪列渲染什么」单点在本表, 模板只剩一份通用壳(div + tokens 循环 + act 按钮)。
 *
 * 渲染器签名 (api, row) -> 描述符, 纯函数零状态:
 *   root    值格根 div 的 class 串(""/"wrap"/"mono-cell"/"kv-k"/组合, 逐列 = W1(3) 迁移前的
 *           DOM 载体, 保真基准 = 26-10-01-2216/26-10-02-1936 逐列清单)
 *   tokens  格内容有序段: { cls, text } = 带 class 的 span(徽章 hr-lane/hr-vsrc/hr-pres +
 *           副行 hr-sub), { text } 无 cls = 裸文本(与模板插值同形, 不多包 span)
 *   act     该格挂「确认空清单」按钮位(hrKv 零行未确认行) —— 按钮本体仍是模板元素
 *           (site/confirming 绑定在模板作用域), 注册化不吞交互(E2 硬要求)
 * api = 根实例: 人话/配色全复用既有 hrs* 单点(hrsLaneCls/hrsVerdictText/hrsSize…), 渲染器
 * 只做「列 -> 描述符」装配, 零语义复制。行对象字段消费与迁移前逐列一致(契约守阵
 * test_frontend_hr_contract_keys_match_backend 的提取器同步覆盖本块)。
 * !注册时机: hr_status.js 在四皮肤 manifest 里先于 dt_table.js 载入, 模块层 registerCell
 *   不可达 —— 注册动作收进 AQB_HR_CELLS_REGISTER(), 由 app.js 装载序末位调用(与 mixin
 *   注入同段); 本文件只定义, 不自注册。 */
const HR_CELL_RENDERERS = {
  /* -- hrDetail 十列(行 = EntryDetail e; 三列重组拍板 4: 档位徽章/核实结论/在列) -- */
  "hrDetail.lane": (api, e) => ({ root: "", tokens: [
    { cls: "hr-lane " + api.hrsLaneCls(e.lane), text: `${e.lane ?? ""} ${e.lane_text ?? ""}` }] }),
  "hrDetail.name": (api, e) => ({ root: "wrap", tokens: [{ text: e.name || "—" }] }),
  "hrDetail.tid": (api, e) => ({ root: "mono-cell", tokens: [{ text: e.tid ?? "" }] }),
  "hrDetail.uploaded_bytes": (api, e) => ({ root: "", tokens: [{ text: api.hrsSize(e.uploaded_bytes) }] }),
  "hrDetail.downloaded_bytes": (api, e) => ({ root: "", tokens: [{ text: api.hrsSize(e.downloaded_bytes) }] }),
  "hrDetail.ratio": (api, e) => ({ root: "", tokens: [{ text: api.hrsRatio(e.ratio) }] }),
  "hrDetail.need_seed_seconds": (api, e) => ({ root: "", tokens: [{ text: api.hrsNeedSeed(e.need_seed_text) }] }),
  "hrDetail.done_iso": (api, e) => ({ root: "mono-cell", tokens: [{ text: api.hrsDone(e.done_iso) }] }),
  "hrDetail.verified_ts": (api, e) => ({ root: "", tokens: [
    { cls: ("hr-vsrc " + api.hrsSrcCls(e)).trim(), text: api.hrsVerdictText(e) },
    { cls: "hr-sub", text: api.hrsVerdictSub(e) }] }),
  "hrDetail.last_seen": (api, e) => ({ root: "", tokens: [
    { cls: "hr-pres " + api.hrsPresenceCls(e), text: api.hrsPresenceText(e) },
    { cls: "hr-sub", text: api.hrsPresenceSub(e) }] }),
  /* -- hrWave 八列(行 = LaneStatus ls) -- */
  "hrWave.lane": (api, ls) => ({ root: "", tokens: [
    { cls: "hr-lane " + api.hrsLaneCls(ls.lane), text: `${ls.lane ?? ""} ${ls.lane_text ?? ""}` }] }),
  "hrWave.status": (api, ls) => ({ root: ("mono-cell " + api.hrsLaneClass(ls)).trim(), tokens: [{ text: ls.status_text ?? "" }] }),
  "hrWave.pages": (api, ls) => ({ root: "", tokens: [{ text: ls.pages }] }),
  "hrWave.rows": (api, ls) => ({ root: "", tokens: [{ text: ls.rows }] }),
  "hrWave.cutoff": (api, ls) => ({ root: "", tokens: [{ text: api.hrsWaveCutoff(ls) }] }),
  "hrWave.fail_streak": (api, ls) => ({ root: "", tokens: [{ text: ls.fail_streak }] }),
  "hrWave.count": (api, ls) => ({ root: "", tokens: [{ text: api.hrsWaveCount(ls) }] }),
  "hrWave.detail": (api, ls) => ({ root: "mono-cell", tokens: [{ text: ls.detail || "—" }] }),
  /* -- hrKv 两列(行 = hrsKvRows 拼行 kv; E7 k 列 locked 在列定义, 拆散 k/v 不可表达) -- */
  "hrKv.k": (api, kv) => ({ root: "kv-k", tokens: [{ text: kv.k }] }),
  "hrKv.v": (api, kv) => ({ root: ("mono-cell " + (kv.cls || "")).trim(), tokens: [{ text: kv.v ?? "" }], act: !!kv.act }),
};
/* 注册单点(fail-fast): DT_TABLE 不在场 = 装载序破坏, 立刻抛错而不是让三表渲染成空白
 * (dt_table 注册表纪律: 查不到即报错, 不许「渲染空白」—— 注册侧同口径)。 */
window.AQB_HR_CELLS_REGISTER = function () {
  const DT = window.DT_TABLE;
  if (!DT || typeof DT.registerCell !== "function") {
    throw new Error("HR 值格渲染器注册失败: DT_TABLE 不在场(装载序: dt_table.js 必须先于 app.js)");
  }
  for (const name of Object.keys(HR_CELL_RENDERERS)) DT.registerCell(name, HR_CELL_RENDERERS[name]);
};

window.AQB_HR_STATUS = {
  data() {
    return {
      hrs: {
        loaded: false,
        loading: false,
        error: "",
        enabled: false,
        note: "",
        sites: [],
        channel: {},
        fetchEnabled: false,
        workerRunning: false,
        pollInterval: 0,
        confirming: false,
        refreshing: false,
        refreshNote: "",
        /* 表(1) 逐站点明细(键 = 站点名): { loading, loaded, error, entries, readError, now }
         * laneSel(键 = 站点名): 档位筛选 chips 的本地选择("" = 全部), 前端过滤不回后端
        * oldOn(键 = 站点名): 已删除种子切换钮状态(计划 26-10-02-1936 §3.3) —— false = 默认只看
        *   本地仍在列(local_present), true = 连已删除行一起显示; 不持久化(与 laneSel 同层)
         * (排序状态不在 hrs: E8 拍板并入引擎 —— 表级 dyn 状态进根 data 的 dtSortState.hrDetail,
         *  sort.js 单点, 26-11-17-0059 W1(4); 曾有的逐站点 sortSel/sortDir 随迁移删除) */
        details: {},
        laneSel: {},
        oldOn: {},
      },
      /* 表(3) 拉取历史(计划 26-10-04-0312 §3.5): 与 hrs 同一份 mixin data 的伴生状态 —— 不并进
       * hrs 根对象的原因: 模板对 hrs.* 的键引用被 test_frontend_hr_status_fields_match_backend
       * 闭集钉死, 加新键即红; hrsHist.* 前缀不落进那个扫描。首次展开才 fetch, 不轮询不持久化。 */
      hrsHist: {
        loading: false,
        loaded: false,
        error: "",
        rows: [],
        readErrors: {},
        now: 0,
        site: "", /* 站点 chips 本地选择("" = 全部站点), 前端过滤不回后端 */
        badOnly: false, /* 「仅看异常」toggle(判据 hrsHistIsBad) */
        expanded: {}, /* 行展开集(键 = ts|site), 展开态不持久化 */
      },
    };
  },
  methods: {
    async loadHrStatus(force = false) {
      if (this.hrs.loading) return;
      if (this.hrs.loaded && !force) return;
      this.hrs.loading = true;
      this.hrs.error = "";
      try {
        const r = await this.api("/api/hr/status");
        this.hrs.loaded = true;
        this.hrs.enabled = !!r.enabled;
        this.hrs.note = r.note || "";
        this.hrs.sites = r.sites || [];
        this.hrs.channel = r.channel || {};
        this.hrs.fetchEnabled = !!r.fetch_enabled;
        this.hrs.workerRunning = !!r.worker_running;
        this.hrs.pollInterval = r.poll_interval || 0;
        /* 表(1) 明细随站点各拉一次: 打开分区(loadHrStatus())首拉, 手动刷新/立即拉取
         * (loadHrStatus(true))重拉 —— 每站点自有 loaded/loading 守卫, 失败不阻塞彼此 */
        for (const s of this.hrs.sites) this.loadHrSiteEntries(s.site, force);
      } catch (e) {
        if (!e.auth) this.hrs.error = e.message || "状态读取失败";
      } finally {
        this.hrs.loading = false;
      }
    },
    /* ---------------- 表(1) 种子明细(计划 26-10-01-2216 阶段2) ----------------
     * 端点校验: HR 未启用 400 / 站点未接入 404 / 取数线程未启动 409; 站点文件读坏不抛,
     * read_error 随响应带出(前端单独显示, 与「明细请求本身失败」分开)。行字段与人话
     * (lane_text/need_seed_text/verified_source_text)全部后端算好, 排序(档位·下载量)与
     * 行集(含失踪行)也是后端口径 —— 这里只存取与筛选, 不重算任何 HR 语义。 */
    async loadHrSiteEntries(site, force = false) {
      const prev = this.hrs.details[site];
      if (prev && prev.loading) return;
      if (prev && prev.loaded && !force) return;
      /* force 重拉(手动刷新/立即拉取)期间保留旧行(loaded 维持 true), 表格不闪回加载态;
       * 只有首拉才显示 loading 占位 —— 手动刷新的语义是「换数据」不是「清空重来」 */
      const keep = !!(force && prev && prev.loaded);
      this.hrs.details[site] = {
        loading: true,
        loaded: keep,
        error: "",
        entries: keep ? prev.entries : [],
        readError: "",
        now: keep ? prev.now : 0,
      };
      try {
        const r = await this.api(`/api/hr/sites/${encodeURIComponent(site)}/entries`);
        this.hrs.details[site] = {
          loading: false,
          loaded: true,
          error: "",
          entries: r.entries || [],
          readError: r.read_error || "",
          now: r.now || 0,
        };
      } catch (e) {
        /* auth 失败由全局登出兜底, 不留站点级错误行 */
        this.hrs.details[site] = {
          loading: false,
          loaded: false,
          error: e.auth ? "" : (e.message || "站点明细读取失败"),
          entries: [],
          readError: "",
          now: 0,
        };
      }
    },
    /* 明细状态读取(模板经 v-for 单元素别名取一次, 避免 undefined 链) */
    hrsDetailOf(site) {
      return this.hrs.details[site] || { loading: false, loaded: false, error: "", entries: [], readError: "", now: 0 };
    },
    /* 档位筛选 chips(全部/A 考察中/B 达标/C 未达标/D 免罪; 拍板只筛 lane 字母, 文案单点在这) */
    hrsLaneChips() {
      return [["", "全部"], ["A", "A 考察中"], ["B", "B 达标"], ["C", "C 未达标"], ["D", "D 免罪"]];
    },
    hrsLaneSelOf(site) {
      return this.hrs.laneSel[site] || "";
    },
    hrsSetLaneSel(site, lane) {
      this.hrs.laneSel[site] = lane;
    },
    /* ---------------- 已删除种子切换钮(计划 26-10-02-1936 §3.3, 决策点(3)a) ----------------
     * 两个可见文案只描述「本地在不在」, 不描述做种状态(2026-10-03 用户二次驳回上轮文案:
     * 默认过滤实为「本地已删除/从未下载」而非「没在做种」, 反向态又含暂停/异常而非都在
     * 做种, 故按钮不再使用「做种」措辞):
     *   默认态 = 只看本地仍在列的(local_present=true), 按钮说「显示已删除种子 (N)」;
     *   切换后 = 连已删除行一起显示, 按钮说「只看本地仍在列 (M)」。
     * 与档位 chips 过滤 AND 叠加, 纯前端本地过滤不回后端不重拉。计数在站点全行集现算
     * (与 chips 同层, 不随 lane 过滤缩放): N = 本地已删除行数(默认态隐藏数), M = 本地仍在列行数。 */
    hrsOldOnOf(site) {
      return !!this.hrs.oldOn[site];
    },
    hrsToggleOld(site) {
      this.hrs.oldOn[site] = !this.hrs.oldOn[site];
    },
    hrsOldBtnText(site) {
      const rows = (this.hrs.details[site] && this.hrs.details[site].entries) || [];
      const present = rows.filter((e) => e.local_present).length;
      return this.hrsOldOnOf(site) ? `只看本地仍在列 (${present})` : `显示已删除种子 (${rows.length - present})`;
    },
    /* ---------------- 三态排序(计划 26-10-02-1936 §3.4; E8 并入引擎, 26-11-17-0059 W1(4)) ----------------
     * 排序状态与三态机归 sort.js 引擎单点: 表头点击走 aq-table grid 根的
     * setSort(key, 'hrDetail') -> dyn 状态进根 data 的 dtSortState.hrDetail(首点降 → 再点升 →
     * 第三击恢复后端默认序 defKey=""/defDir=-1 = 后端原序; 换列直接降序开始, 三态语义与旧
     * hrsSetSort 逐位一致); 行消费侧这里只读 dtSortCell('hrDetail') 取当前键/方向。
     * 行为差(E8 拍板接受): 排序选择从逐站点记忆变表级(全 HR 明细表共用一座键)。 */
    /* 行集 = 后端排好序的 entries 前端本地过筛(不回后端): 档位 chips × 已删除种子切换
     * AND 叠加, 再叠加三态排序(键/方向取引擎 dtSortCell 单点, 比较器走模块级 hrsCompareRows
     * 纯函数, 空值恒末位); 无排序键时保持后端默认序(档位·下载量)。 */
    hrsDetailRows(site) {
      const d = this.hrs.details[site];
      if (!d || !d.entries) return [];
      let rows = d.entries;
      const sel = this.hrsLaneSelOf(site);
      if (sel) rows = rows.filter((e) => e.lane === sel);
      if (!this.hrsOldOnOf(site)) rows = rows.filter((e) => e.local_present);
      const cell = this.dtSortCell("hrDetail");
      if (cell.key) rows = [...rows].sort((a, b) => hrsCompareRows(a, b, cell.key, cell.dir));
      return rows;
    },
    /* 过滤后空态文案(计划 §3.3): 区分「该站点本地没有 HR 种子」(本地仍在列视图全空)与
     * 「该档位暂无」(chips 过滤后空); 已删除视图空集单独说, 不与本地仍在列口径混。 */
    hrsEmptyText(site) {
      const rows = (this.hrs.details[site] && this.hrs.details[site].entries) || [];
      if (this.hrsLaneSelOf(site)) return "该档位暂无";
      if (!this.hrsOldOnOf(site)) {
        return rows.some((e) => e.local_present) ? "该档位暂无" : "该站点本地没有 HR 种子";
      }
      return rows.length ? "该档位暂无" : "该站点没有已删除的种子";
    },
    /* 值格消费口(W2(4) E2): settings-detail 模板通用壳经此走 DT_TABLE.cellOf 取列渲染器
     * (名字 = "<tableId>.<列key>", 注册表 HR_CELL_RENDERERS / 注册点 app.js AQB_HR_CELLS_REGISTER)。
     * 模板用单元素 v-for 绑定技巧(`v-for="cell in [hrCellOf(...)]"`, 本文件 hrsDetailOf 同款先例)
     * 每格只求值一次并拿到整个描述符; cellOf 对未注册名抛错(fail-fast, 不许渲染空白)。 */
    hrCellOf(tableId, col, row) {
      return window.DT_TABLE.cellOf(tableId + "." + col.key)(this, row);
    },
    /* 档位徽章色义(§5.4): A=warn(考察中) / B=green(达标) / C=error(未达标) / D=blue(免罪);
     * 失踪行由 CSS tr.missing 统一换 --paused 描边弱化, 这里不管 */
    hrsLaneCls(lane) {
      return `hr-lane-${String(lane || "").toLowerCase()}`;
    },
    /* 字节数复用共享 fmtSize(AQB_FORMAT 单点); null/undefined = 站点没给 -> — (0 是真值, 照显) */
    hrsSize(v) {
      return v === null || v === undefined ? "—" : this.fmtSize(v);
    },
    hrsRatio(v) {
      return v === null || v === undefined ? "—" : Number(v).toFixed(2);
    },
    /* 还需做种人话由后端给; 它的缺失占位是 "-"(need_seed_text 单点), 表格里统一 — */
    hrsNeedSeed(t) {
      return !t || t === "-" ? "—" : t;
    },
    /* 完成时间: 站点 ISO 字符串取日期段; 缺失 -> — */
    hrsDone(iso) {
      return iso ? String(iso).slice(0, 10) : "—";
    },
    /* ---------------- 核实结论列(计划 26-10-02-1936 §3.6, 决策点(4); 2026-10-03 修 B3) ----------------
     * 主徽章三态 —— 数据源只有后端给的 verified_source / lane / active, 前端不重算判定:
     *   (1) 有放行记录            : 「已核实」(色沿用 hr-vsrc 色义: satisfied=绿 / exempt·not-listed=蓝);
     *   (2) 无记录 + 行在列 + 档位为终态(B/C/D): 「在列·<档位人话>」中间态(蓝) —— 站侧已给结论
     *      (如 B 已达标)但行仍挂清单未消失 => _freeze_terminal 未触发 => 后端刻意不写 verified
     *      (防伪: 命中不是放行, 见 test_hr_service.py 守阵), 此时显「未核实」会掩盖「已达标」;
     *   (3) 其余(无记录 + A 考察中, 或已退役但无记录): 「未核实」(中性)。
     * WARN: 切勿改成「命中即写 verified」—— 那会破坏放行防伪语义(后端判定侧唯一写点是冻结/未列出)。
     * 副行 = 已核实时「<来源人话> · <verified_ts>」, 其余 = 中间态说明 / —。
     * verified_ts 的 0 哨兵纪律同旧 hrsVerifiedText: 绝不显示 epoch。 */
    hrsVerdictText(e) {
      if (e.verified_source) return "已核实";
      if (e.active && hrsTerminalLane(e.lane) && e.lane_text) return `在列·${e.lane_text}`;
      return "未核实";
    },
    hrsVerdictSub(e) {
      if (e.verified_source) return `${e.verified_source_text} · ${this.fmtTs(e.verified_ts)}`;
      if (e.active && hrsTerminalLane(e.lane)) return "站侧已定论, 行未移出(放行记录待移出后签发)";
      return "—";
    },
    /* 来源小徽章配色: satisfied(B 毕业文案已换已达标)=绿 / 其余有记录(absent 免罪,
     * not-listed 未列出)=蓝 / 中间态(终态档在列未核实)=蓝 / 无记录=默认中性(未核实)。
     * token 是后端 SOURCE_* 契约值, 只映射不重算。类名 hr-vsrc(verified source): hr-src 是
     * 列表页已退役的文字 chip 族(hr-tooltip-overlap, 守阵钉了 class="hr-src" 零残留), 新件
     * 不得复用该名字 */
    hrsSrcCls(e) {
      if (e.verified_source) return e.verified_source === "satisfied" ? "hr-vsrc-b" : "hr-vsrc-d";
      if (e.active && hrsTerminalLane(e.lane)) return "hr-vsrc-d";
      return "";
    },
    /* ---------------- 在列列(计划 26-10-02-1936 §3.6, 决策点(4)) ----------------
     * 主徽章两态按 active 分流(2026-10-03 修 B4: 退役行不再借「失踪 N 波」)—— 
     *   active=true : 「在列」(绿);
     *   active=false: 退役行 —— 有放行记录显「已移出」(蓝, 与「已核实」同义), 无记录显
     *                 「已退役」(中性)。退役行**不显示** missing_streak: 它是 A 档观察期计数器,
     *                 service.py 退役时已清零(结构性恒 0), 显示「失踪 0 波」纯属语义错位。
     * 副行 = 「(观察期 N ·)最近被见到 <last_seen>」—— 观察期只属活跃行, last_seen 未知
     * (0 哨兵)显示 —, 绝不显示 epoch。 */
    hrsPresenceText(e) {
      if (e.active) return "在列";
      return e.verified_source ? "已移出" : "已退役";
    },
    hrsPresenceCls(e) {
      if (e.active) return "hr-pres-on";
      return e.verified_source ? "hr-pres-out" : "hr-pres-off";
    },
    hrsPresenceSub(e) {
      const parts = [];
      if (e.active && e.missing_streak > 0) parts.push(`观察期 ${e.missing_streak}`);
      const seen = this.fmtTs(e.last_seen);
      if (seen) parts.push(`最近被见到 ${seen}`);
      return parts.length ? parts.join(" · ") : "—";
    },
    /* ---------------- 折叠 <-> 全屏覆盖层(计划 26-10-02-1936 阶段2) ----------------
     * 「展开」即打开覆盖式全屏弹窗(用户拍板(1)改判), 两态之间没有内嵌展开态; hrsOpen 在 state.js
     * 根 data(同 logs.open 先例), 不持久化、每次进分区回折叠(config_hub.js hubGo 复位)。
     * 取数时机(决策点(5)a): 首次展开才拉 —— 复用 loadHrStatus 既有链路, 无新定时器;
     * 覆盖层展示的就是同一份已加载明细(单节点 v-show 显隐), 关闭/打开零新请求。 */
    hrsToggle() {
      if (this.hrsOpen) {
        this.hrsCollapse();
        return;
      }
      this.hrsOpen = true;
      if (!this.hrs.loaded) this.loadHrStatus();
    },
    hrsCollapse() {
      this.hrsOpen = false;
    },
    /* 折叠态点「全部立即拉取 / 刷新」= 明确想看: 顺手展开再拉(config_hub.js hubLogsLoad 同款先例);
     * 已在覆盖层里时就是普通的拉取动作, 展开一步是空操作 */
    hrsExpandAndRefreshAll() {
      if (!this.hrsOpen) this.hrsToggle();
      this.hrsRefresh();
    },
    hrsExpandAndReload() {
      if (!this.hrsOpen) this.hrsToggle();
      this.loadHrStatus(true);
    },
    /* 头部摘要(计划 §3.1): 未加载一句话说明默认态(拉取进行中则说正在读, 覆盖层头部同用此文案);
     * 已加载给站点数与数据截至 —— 时间取各站点明细 now 的最大值(loadHrStatus 已带回的现成数据,
     * 不新拉), 一个站点都没拉到明细时只给站点数 */
    hrsSummaryText() {
      if (!this.hrs.loaded) return this.hrs.loading ? "正在读取站点状态…" : "默认折叠, 展开后读取";
      let ts = 0;
      for (const k of Object.keys(this.hrs.details)) {
        const d = this.hrs.details[k];
        if (d && d.loaded && d.now > ts) ts = d.now;
      }
      const seen = ts ? ` · 数据截至 ${this.fmtTs(ts)}` : "";
      return `${this.hrs.sites.length} 站点${seen}`;
    },
    /* ---------------- 展示辅助(值全由后端算好, 这里只挑文案与配色) ---------------- */
    hrsStateText(s) {
      if (s.listing === "none") return "全站型(本地兜底)";
      return s.releases_enabled ? "放行签发开启" : "放行签发冻结";
    },
    hrsStateClass(s) {
      return s.listing === "none" || s.releases_enabled ? "ok" : "warn";
    },
    /* 档位计数(A 考察中 / B 已达标 / C 未达标 / D 已免罪) —— 顺序固定, 便于多站点横向对比 */
    hrsLaneText(s) {
      const l = s.lane_counts || {};
      return `A=${l.A || 0} B=${l.B || 0} C=${l.C || 0} D=${l.D || 0}`;
    },
    /* ---------------- 表(2) 排障视图(计划 26-10-01-2216 阶段3, 拍板(1)a) ----------------
     * 排障性文本收进 <details> 默认收起的排障视图, 表格化为站点级 kv 行 + 各档波次明细;
     * kv 行集在这里拼好(模板 v-for 摆行, 保 settings-detail.html 体量守阵), 字段全来自
     * /api/hr/status 现有载荷的 SiteStatus/LaneStatus, 措辞与 CLI --hr-status 对齐
     * (report._print_status_site 同源字段) —— 不重算语义, 只挑文案与配色;
     * 展开态是临时排障动作: 不写 localStorage、不加定时器(pitfalls/web-ui/ui-location-persist)。 */
    hrsKvRows(s) {
      const confirmed = !!s.empty_confirmed;
      const attested = !!s.count_attested_empty;
      const unconfirmed = !!s.zero_rows && !confirmed && !attested;
      const zero = !s.zero_rows
        ? "非零行(零行未确认 / 计数自证空集均未触发)"
        : confirmed ? "零行波 · 已人工确认空清单"
        : attested ? "零行波 · 计数自证空集(无需人工确认)"
        : "零行波 · 未确认(零行波不签发放行)";
      const exp = this.fmtTs(s.expires_at);
      return [
        { k: "通道", v: s.channel_text || "—" },
        { k: "数据版本", v: `revision ${s.revision || 0}` },
        { k: "放行签发", v: s.releases_enabled ? "开" : "冻结", cls: s.releases_enabled ? "" : "warn" },
        { k: "取波", v: s.fresh_text || "—" },
        { k: "复用窗至", v: exp ? `${exp}${s.stale ? "(已过)" : ""}` : "—" },
        { k: "下次核对清单", v: (this.fmtTs(s.next_wave_at) || "—") + (s.next_wave_at && s.idle_mode ? "(稳态降频)" : "") },
        { k: "配额", v: (s.quota && s.quota.text) || "—" },
        { k: "零行三态", v: zero, cls: unconfirmed ? "warn" : "", act: unconfirmed },
        { k: "守恒", v: `索引 ${s.index_total} 条(活跃 ${s.index_active}) · 待回填 ${s.pending_infohash} 条(${this.hrsPct(s.backfill_ratio)}) · ${s.retention_text || "—"}` },
        { k: "存量", v: `档位 ${this.hrsLaneText(s)} · 考察中命中 ${s.managed} 个(键 ${s.keys} 个) · 观察期 ${s.observing} 个 · 已取种子 ${s.downloaded} · 取种失败 ${s.fails} · 放行记录 ${s.verified}` },
        { k: "时间窗", v: s.allow_window || "不限" },
        { k: "现在不放行", v: s.blocking || "—— 无", cls: s.blocking ? "warn" : "" },
        { k: "最近一波备注", v: s.notes || "—", cls: s.notes ? "warn" : "" },
        { k: "站点文件", v: s.read_error || "正常", cls: s.read_error ? "error" : "" },
      ];
    },
    /* 波次表「截至深度」列: full_depth = 覆盖证明达全深度; 否则显示已见最深行的完成时刻
     * (cutoff_done 是 epoch, model.HrLaneState 口径; 0 = 没有位置概念 -> —) */
    hrsWaveCutoff(ls) {
      if (ls.full_depth) return "全深";
      return this.fmtTs(ls.cutoff_done) || "—";
    },
    /* 波次表「对平(声称/命中)」列: 声称 = count_claim; 命中后端只给平/不平两态(count_match),
     * None = 无从对平 -> ?(与 CLI「声明 N 行 / 对不平」同源, 不重算) */
    hrsWaveCount(ls) {
      if (ls.count_claim === null || ls.count_claim === undefined) return "—";
      const m = ls.count_match === null || ls.count_match === undefined ? "?" : (ls.count_match ? "平" : "不平");
      return `${ls.count_claim} / ${m}`;
    },
    hrsLaneClass(ls) {
      if (ls.count_match === false) return "warn";
      return ls.status === "failed" ? "error" : "";
    },
    /* 人工对账戳(§5.3): 零行波默认不签发放行, 确认账号清单确实为空后写一次性戳 */
    async hrsConfirmEmpty(site) {
      if (this.hrs.confirming) return;
      if (!confirm(`确认站点 ${site} 的 HR 清单确实为空?
确认后零行波可正常签发放行; 清单再现非零行时确认戳自动失效。
页头计数可自证空集的站点(各档声明全为 0)无需此人工确认。`)) return;
      this.hrs.confirming = true;
      try {
        await this.api("/api/hr/confirm-empty", { method: "POST", body: JSON.stringify({ site }) });
        await this.loadHrStatus(true);
      } catch (e) {
        if (!e.auth) alert(e.message || "确认写入失败");
      } finally {
        this.hrs.confirming = false;
      }
    },
    /* 立即拉取(计划 26-09-30-0240): 请求后端置一次性 force 旗标, 取数线程跳过复用窗与
     * 拉取间隔立即开波(账号频控 min_interval/日额/Retry-After/时间窗仍生效)。
     * site 缺省 = 全部启用站点。受理后立即刷新状态; 波启动后首任务数秒内入队,
     * 后续任务由取数线程/扩展的既有轮询接管 —— 本页不需要轮询, 刷一次看「上次取波」即可。 */
    async hrsRefresh(site = "") {
      if (this.hrs.refreshing) return;
      this.hrs.refreshing = true;
      try {
        const r = await this.api("/api/hr/refresh", { method: "POST", body: JSON.stringify(site ? { site } : {}) });
        const n = (r.requested || []).length;
        this.hrs.refreshNote = n
          ? `已受理 ${n} 个站点, 取数线程执行中(跳过复用窗与拉取间隔, 频控仍生效)`
          : "";
        await this.loadHrStatus(true);
      } catch (e) {
        if (!e.auth) alert(e.message || "立即拉取请求失败");
      } finally {
        this.hrs.refreshing = false;
      }
    },
    hrsPct(v) {
      return `${Math.round((v || 0) * 100)}%`;
    },
    /* 通道一行话: 端点通不通 + 本实例能不能主动抓(没有浏览器时只能读别人抓的) */
    hrsChannelText() {
      const c = this.hrs.channel || {};
      if (!c.enabled) return "取数通道未启用(只会读共享数据, 不会主动抓)";
      const where = c.listening ? `监听 127.0.0.1:${c.port}` : "端点未启动";
      const who = this.hrs.fetchEnabled ? "本实例可主动取数" : "本实例只读共享数据";
      const seen = c.last_contact_ts ? "" : " · 还没有任何扩展联系过";
      const pend = c.pending ? ` · 待取任务 ${c.pending}` : "";
      return `${where} · ${who}${seen}${pend}`;
    },
    hrsPollText() {
      return this.hrs.pollInterval ? `每 ${this.hrs.pollInterval}s 检查一次站点` : "";
    },
    /* ---------------- 表(3) 拉取历史(计划 26-10-04-0312 §3.5) ----------------
     * 端点 /api/hr/history 只读; 行字段与人话(22 键)全部后端算好(hr.status.history_rows 单点),
     * 这里只存取 / 本地过滤 / 排版。取数时机同表(1) 范式: 首次展开才拉(模板 @toggle ->
     * hrsHistOnToggle -> hrsHistEnsureLoaded), 「刷新」手动重拉(hrsHistReload), 不轮询无定时器;
     * force 重拉期间 loaded 维持 true, 旧行留在表里不闪回加载态(表(1) loadHrSiteEntries 同款)。
     * fetch 错误处理随 loadHrStatus 范式: auth 失败交给全局登出, 其余落 hrsHist.error。 */
    async hrsHistLoad(force = false) {
      const h = this.hrsHist;
      if (h.loading) return;
      if (h.loaded && !force) return;
      h.loading = true;
      h.error = "";
      try {
        const r = await this.api(`/api/hr/history?limit=${HRS_HIST_LIMIT}`);
        h.loaded = true;
        h.rows = r.rows || [];
        h.readErrors = r.read_errors || {};
        h.now = r.now || 0;
        h.expanded = {};
      } catch (e) {
        if (!e.auth) h.error = e.message || "拉取历史读取失败";
      } finally {
        h.loading = false;
      }
    },
    /* details 的开与合都会发 toggle: 只有展开且未 loaded 才发请求(首次展开才拉一次) */
    hrsHistOnToggle(ev) {
      if (ev && ev.target && ev.target.open) this.hrsHistEnsureLoaded();
    },
    hrsHistEnsureLoaded() {
      if (!this.hrsHist.loaded) this.hrsHistLoad();
    },
    hrsHistReload() {
      this.hrsHistLoad(true);
    },
    /* 站点 chips(hrsLaneChips 的 [值, 文案] 对范式): 全部站点 + 行内站点集合现算(首现序),
     * 纯前端本地过滤不回后端 —— 端点的 site 参数是给单站深链用的, 本表不拼 */
    hrsHistSiteChips() {
      const seen = [];
      for (const r of this.hrsHist.rows) {
        if (r.site && !seen.includes(r.site)) seen.push(r.site);
      }
      return [["", "全部站点"]].concat(seen.map((st) => [st, st]));
    },
    hrsHistSiteSel() {
      return this.hrsHist.site;
    },
    hrsHistSetSite(site) {
      this.hrsHist.site = site;
    },
    hrsHistBadOn() {
      return !!this.hrsHist.badOnly;
    },
    hrsHistToggleBad() {
      this.hrsHist.badOnly = !this.hrsHist.badOnly;
    },
    /* 行集 = 后端排好序的 rows(ts 降序)前端本地过筛: 站点 chips × 仅看异常 AND 叠加 */
    hrsHistRows() {
      const h = this.hrsHist;
      let rows = h.rows;
      if (h.site) rows = rows.filter((r) => r.site === h.site);
      if (h.badOnly) rows = rows.filter(hrsHistIsBad);
      return rows;
    },
    /* 行展开(键 = ts|site): 点行展开各档明细子行, 再点收起; 展开态不持久化 */
    hrsHistKey(r) {
      return `${r.ts}|${r.site}`;
    },
    hrsHistIsOpen(r) {
      return !!this.hrsHist.expanded[this.hrsHistKey(r)];
    },
    hrsHistToggleRow(r) {
      const k = this.hrsHistKey(r);
      this.hrsHist.expanded[k] = !this.hrsHist.expanded[k];
    },
    /* 结果徽章色档: result_tone(ok/warn/dim/err/blue)后端单点给好, 直接映射 hr-hres-<tone>,
     * 未知档回落 dim —— 前端不重算语义 */
    hrsHistResCls(r) {
      const tone = HRS_HIST_TONES.includes(r.result_tone) ? r.result_tone : "dim";
      return `hr-hres-${tone}`;
    },
    /* 数值列: 取数语义只属 wave 行(defer/confirm_empty 没有, 显 —); pages/rows 的 0 = 没取到
     * 也显 —, 回填/放行的 0 计数照显(计划 mock 口径: 完成 3/0 与放行 0) */
    hrsHistWaveNum(r, key) {
      if (r.kind !== "wave") return "—";
      const v = r[key] || 0;
      return v > 0 ? v : "—";
    },
    hrsHistBackfill(r) {
      if (r.kind !== "wave") return "—";
      return `${r.torrents_ok || 0}/${r.torrents_fail || 0}`;
    },
    hrsHistVerified(r) {
      if (r.kind !== "wave") return "—";
      return r.verified > 0 ? `+${r.verified}` : "0";
    },
    /* 「数据截至」时间戳取响应 now(mock 口径「最近 N 条 · 数据截至 …」; fmtTs 对 0 回空串,
     * 无 now 时只给条数) */
    hrsHistFreshText() {
      const h = this.hrsHist;
      const asof = h.now ? ` · 数据截至 ${this.fmtTs(h.now)}` : "";
      return `最近 ${h.rows.length} 条${asof}`;
    },
    /* 展开明细子行(计划 §3.5 mock 表): 各档一段 <lane> <lane_text> · <status_text> · P 页 / R 行
     * (+档位 detail), 行级 notes 追加尾部 —— 全部人话后端算好, 这里只拼排版 */
    hrsHistSubText(r) {
      const parts = (r.lanes || []).map((ln) => {
        const seg = [`${ln.lane} ${ln.lane_text}`.trim(), ln.status_text || "", `${ln.pages || 0} 页 / ${ln.rows || 0} 行`];
        if (ln.detail) seg.push(ln.detail);
        return seg.filter(Boolean).join(" · ");
      });
      if (r.notes && r.notes.length) parts.push(r.notes.join("；"));
      return parts.join("；") || "无档位明细";
    },
  },
};
