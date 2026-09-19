/* auto-qb WEB UI 前端(Vue 3 CDN, 无构建链): rid 增量轮询 + 命令投递 + 列宽记忆 */
/* global Vue, localStorage, confirm, alert */  // 声明浏览器全局, 消除编辑器 no-undef 红线
const { createApp } = Vue;

/* ---------------- 列表列模型(分组表 / 明细表) ----------------
 *
 * **单一来源**: 列头 / 行单元格 / grid 模板 / 列选择器 全部由这一份数组派生 —— 顺序天然一致。
 * (旧实现把"顺序"分散在表头、行内单元格与模板三处, 加列/改序极易错位, 且列宽按**索引**记忆,
 *  一旦支持隐藏列索引就会漂移。)
 *
 * locked: 不可隐藏(承载展开 caret / 组状态徽标 / 站点名, 隐藏后行就失去身份)
 * tpl:    默认列宽模板(minmax(最小px, 权重fr) 或 固定 px), 用于首次渲染与"恢复默认"
 * align:  对齐口径(R10-08) —— **表头与值单元格的唯一来源**, 由 colAlignCss 生成规则注入,
 *         不在模板里逐格挂类(67 个值单元格 × 4 视图 × 2 套 UI, 逐格挂必漏)。
 *         取值 left | right | center; 缺省 = left。
 *         用户清单(2026-09-17): 名称/进度/状态/站点/分类/标签/添加于/做种时长/最近活动/
 *         hashv1/hash/tracker/保存路径 = 左, 其余数值/大小/速度/比率 = 右, 计数类(站数/H&R/版本)
 *         保持既有居中口径。
 */
const GROUP_COLUMNS = [
  { key: "name", label: "名称", tpl: "minmax(210px, 2.4fr)", sortable: true, locked: true, align: "left" },
  { key: "dlspeed", label: "下载", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "uploaded", label: "总上传", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "total_size", label: "总大小", tpl: "minmax(100px, 1fr)", sortable: true, align: "right" },
  // 分类在标签之前(用户要求分组表/明细表口径一致); 列宽按**列 key**记忆 -> 换序不丢宽度
  { key: "category", label: "分类", tpl: "minmax(100px, 1.1fr)", align: "left" },
  { key: "tags", label: "标签", tpl: "minmax(130px, 1.4fr)", align: "left" },
  { key: "sites", label: "站点", tpl: "minmax(170px, 1.6fr)", align: "left" },
  // H&R: 未满足做种时长/分享率的成员数 / 已触发 HR 的成员数(组级计数由后端算好, 见 qbmanager._build_group_view)
  { key: "hr", label: "H&R", tpl: "minmax(88px, 1fr)", sortable: true, align: "center" },
  { key: "count", label: "站数", tpl: "56px", sortable: true, align: "center" },
  // TBL-06: 组级"最近添加"(组内成员最大 added_on, 后端 _build_group_view 已透出);
  // DEFAULT_SORT 默认排序键本就是 added_on —— 补列后排序箭头有了落点
  // R10-08: 时间列由右改左(表头与值同源, 不会再出现"表头左、值右"的错位)
  { key: "added_on", label: "添加于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // 保存路径(用户 2026-09-17): 辅种表的路径取**首位成员**值(与路径筛选器同口径); 明细表
  // 相应取消该列 —— 组内成员路径本就一致(组 key 首元即规范化 save_path), 重复展示无信息量。
  { key: "save_path", label: "保存路径", tpl: "minmax(150px, 1.6fr)", sortable: true, align: "left" },
];
const DETAIL_COLUMNS = [
  { key: "site", label: "站点", tpl: "110px", sortable: true, locked: true, align: "left" },
  { key: "state", label: "状态", tpl: "76px", sortable: true, align: "left" },
  // TBL-06: 做种/用户(与种子页同口径 "已连接 (总数)", fmtPeersQb) —— 字段 W1a-BE 已在 _member_view 透出;
  // sortable 标记与 TORRENT_COLUMNS 同字段对齐(明细表头已接排序, 2026-09-17)
  { key: "num_seeds", label: "做种", tpl: "92px", sortable: true, align: "right" },
  { key: "num_leechs", label: "用户", tpl: "92px", sortable: true, align: "right" },
  { key: "dlspeed", label: "下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "uploaded", label: "总上传", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  // 与分组表同序: 分类在标签之前
  { key: "category", label: "分类", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },
  { key: "tags", label: "标签", tpl: "minmax(140px, 1.3fr)", sortable: true, align: "left" },
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)", sortable: true, align: "left" },
  { key: "seeding_time", label: "做种时长", tpl: "minmax(124px, 1.1fr)", sortable: true, align: "left" },
  // 分享率: 显示 实际/HR 要求(未配置分享率要求时只显示实际值); Hash 不可排序(无语义), 其余列均可
  { key: "ratio", label: "分享率", tpl: "minmax(104px, 1fr)", sortable: true, align: "right" },
  // TBL-06: 添加于(_member_view 已透出), 与 Hash 同置表尾低频区
  // (保存路径列 2026-09-17 移出本表 -> 见 GROUP_COLUMNS: 组内路径天然一致, 只保留组级一处)
  { key: "added_on", label: "添加于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  { key: "hash", label: "Hash", tpl: "80px", align: "left" },
];
/* 种子页列模型(前端第一轮 R1A, 原 R08 单种子视图扩列升级): name 锁定; 数据源 = SEED_ITEM
 * 平铺数组(/api/state.torrents, 全量种子)。默认可见列 = 种子页核心口径(名称/大小/进度/状态/
 * 站点/做种/用户/下载/上传/ETA/分享率/总上传/分类/标签/添加于); SEED_ITEM 其余扩展字段
 * (已下载/剩余量/可用性/做种时长/活跃时间/最近活动/完成于/限速/Hash v1/tracker/保存路径/Hash)
 * 全部进列选择器按需开启。列宽按列 key 记忆在独立 page 名 "torrent" 下 —— 新增 page 属向后
 * 兼容扩展, 旧存储缺该 page 时 loadColState 返回空, 无需升 COLS_STORE_KEY 版本 */
const TORRENT_COLUMNS = [
  { key: "name", label: "名称", tpl: "minmax(220px, 2.6fr)", sortable: true, locked: true, align: "left" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)", sortable: true, align: "left" },
  { key: "state", label: "状态", tpl: "76px", align: "left" },
  { key: "site", label: "站点", tpl: "110px", sortable: true, align: "left" },
  { key: "num_seeds", label: "做种", tpl: "92px", sortable: true, align: "right" },  // "已连接 (总数)" 格式(TBL-04), 64px 放不下
  { key: "num_leechs", label: "用户", tpl: "92px", sortable: true, align: "right" },
  { key: "dlspeed", label: "下载", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "eta", label: "ETA", tpl: "minmax(84px, 1fr)", sortable: true, align: "right" },
  { key: "ratio", label: "分享率", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "uploaded", label: "总上传", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  // 与分组表/明细表同序: 分类在标签之前
  { key: "category", label: "分类", tpl: "minmax(100px, 1.1fr)", align: "left" },
  { key: "tags", label: "标签", tpl: "minmax(130px, 1.4fr)", align: "left" },
  { key: "added_on", label: "添加于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // ---- 以下为列选择器可选列(默认隐藏; 字段集 = SEED_ITEM 扩展段) ----
  { key: "downloaded", label: "已下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "amount_left", label: "剩余量", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "availability", label: "可用性", tpl: "minmax(80px, 1fr)", sortable: true, align: "right" },
  { key: "seeding_time", label: "做种时长", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },
  { key: "time_active", label: "活跃时间", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "right" },
  { key: "last_activity", label: "最近活动", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  { key: "completion_on", label: "完成于", tpl: "minmax(110px, 1fr)", sortable: true, align: "right" },
  { key: "up_limit", label: "限速上行", tpl: "minmax(96px, 1fr)", align: "right" },
  { key: "dl_limit", label: "限速下行", tpl: "minmax(96px, 1fr)", align: "right" },
  { key: "infohash_v1", label: "Hash v1", tpl: "90px", align: "left" },
  { key: "tracker", label: "Tracker", tpl: "minmax(150px, 1.4fr)", align: "left" },
  { key: "save_path", label: "保存路径", tpl: "minmax(150px, 1.6fr)", align: "left" },
  { key: "hash", label: "Hash", tpl: "80px", align: "left" },
];
/* 追剧视图列模型: 剧行(剧名) / 季子标题 / 集行共用同一套列; 集行是展示主体(聚合层后端算好,
 * 明细成员经 memberByHash 索引取, 不随 shows 重复回传)。列宽按列 key 记忆在独立 page "show" 下
 * (同 R08 torrent page 先例: 新增 page 向后兼容, 不升 COLS_STORE_KEY 版本) */
const SHOW_COLUMNS = [
  { key: "name", label: "剧名 / 集", tpl: "minmax(220px, 2.4fr)", sortable: true, locked: true, align: "left" },
  { key: "state", label: "状态", tpl: "76px", align: "left" },
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)", sortable: true, align: "left" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "versions", label: "版本", tpl: "64px", sortable: true, align: "center" },
  { key: "sites", label: "站点", tpl: "minmax(150px, 1.4fr)", align: "left" },
  { key: "dlspeed", label: "下载", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "uploaded", label: "总上传", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  { key: "hr", label: "H&R", tpl: "minmax(88px, 1fr)", sortable: true, align: "center" },
  // 最近动静: 与分组表"最近活动"同族(时间列), 一律左对齐
  { key: "latest", label: "最近动静", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
];
const TABLE_COLUMNS = { group: GROUP_COLUMNS, detail: DETAIL_COLUMNS, torrent: TORRENT_COLUMNS, show: SHOW_COLUMNS };
const MIN_COL_PX = 56;    // 拖拽下限: 再窄列头就无法点击排序/再次拖拽了
const MAX_FIT_PX = 520;   // 双击自适应内容的上限(超长种子名不该把某一列撑爆)
const RESIZE_DRAG_THRESHOLD = 3;  // 拖列宽超过该位移(px)即视为"真拖拽", 释放时拦掉冒泡到 .h-cell 的 click(避免误触排序)
/* 列状态持久化(决策 D3 = **只存浏览器**, 不上服务端):
 * {widths:{page:{列key:"120px"}}, hidden:{page:[列key]}, manual:{page:bool}, order:{page:[列key]}}
 * v2(按列索引的稀疏覆盖) -> v3(**按列 key** + 自适应策略变更) -> v4(新增 H&R/分享率列)。
 *
 * R10-09 修订两条:
 * ① **不再靠"升版本"应对列集变更** —— 宽/隐/序一律按**列 key** 存, 新增列在旧缓存里只是
 *    "没有记录"(回退 tpl 默认宽), 不会错配; 历史上 v3->v4 升版本反而把用户手调的宽/隐/序
 *    清零, 正是"时不时被重置"的机制性来源。故本轮列模型增 `align` **不升版本**。
 * ② 保留旧键迁移: 当前键缺失/损坏时依次读 LEGACY_COLS_KEYS, 命中即按列 key 求交集洗净后
 *    立刻回写当前键 —— 升级/换键都不再清空偏好。v2 是**按列索引**式, 索引在支持隐藏列后
 *    会漂移, 无法可靠迁移 -> 刻意不读。
 *
 * 不被重置的保证: _logout()/换密钥只清 `autoqb_token`, 全仓尤 `localStorage.clear()`。
 * 仍存在的限制(已写入 pitfalls): localStorage 按 **origin** 隔离 —— localhost 与 127.0.0.1
 * 或换端口 = 不同站点, 各有自己的偏好(用户已明确要求只存浏览器, 不接受服务端化)。 */
const COLS_STORE_KEY = "autoqb_cols_v4";
const LEGACY_COLS_KEYS = ["autoqb_cols_v3"];  // v2 为索引式覆盖, 不可迁移(见上)

/* 默认排序: 辅种组按组内**最近添加**时间降序(新补进来的种子最需要被看到);
 * 其它列点击 3 次回到这里(见 setSort 的三态语义)
 */
const DEFAULT_SORT = { key: "added_on", dir: -1 };

/* ---------------- P1-2 行窗口化(windowed rows) ----------------
 *
 * 背景(实测, 3000 种子, 见 scripts/ui_smoke.cjs): 每轮全量回传后前端整表替换,
 * **主线程被单个长任务占住 240~350ms** —— 这就是"点一下要等一会儿"的真身:
 * 每 2s 一次的刷新把 3000 行 × 13 列重新 patch 一遍, 期间点击/滚动全部排队。
 *
 * 做法: 只渲染视口附近的行, 上下各用占位 div 撑住总高度(滚动条长度与滚到底都照旧)。
 * 与"虚拟滚动"常见实现的区别 —— 这里**不改布局模型**: 行仍在原地流式排列(flex column),
 * 占位只是两个空盒子, 因此:
 *   ① 每行仍渲染**完整单元格序列**(CSS 的 :nth-child 列对齐与 data-table 都依赖它);
 *   ② 横向滚动/sticky 表头/列宽拖拽全部不受影响;
 *   ③ 多选 shift 区间、右键、搜索高亮仍按**数据索引**走(filteredTorrents 原数组不变),
 *      窗口只决定"渲染哪一段", 不参与任何业务语义。
 *
 * 三条硬约束(漏了就出事):
 *   ① 占位高度必须等于被折叠掉的行高之和 —— 而**行高是不齐的**(带 H&R 要求的行多渲染一行,
 *      实测 43.7px 与 65.4px 混排), 故一律**逐行实测 + 前缀和**, 不做"等高"近似
 *      (等高假设在 3000 行上会漂 218px ⇒ 滚到底够不着)。首轮先全量渲染一次量齐。
 *   ② 视图有"插队元素"时必须退避: 分组页展开的 .detail 面板高度不定, 会让后续行整体下移,
 *      此时窗口的"第 i 行在 pre[i]"假设失效 —— 有展开即回退全量。
 *   ③ 阈值以下不开窗: 小库(<ROW_WIN_MIN)开窗只是平白多一次测量, 且更容易露白。
 *
 * ⚠️ 行间距必须**实测**, 不能硬编码(2026-09-19 修 BUG-1): 三个行容器的真实 gap 并不相同 ——
 * atlas `.group-table` 是 6px, prism `.group-table` 是 5px, 而成员容器 `.detail` 是**块级容器**
 * (没有 flex gap, 行间距为 0)。曾按 6px 写死, 结果 prism 的占位总高比全量渲染多 2973px
 * (3000 行实测) ⇒ 滚动条长度失真、中段位置最多偏 49 行。真值由 `_measureRowH` 读
 * `getComputedStyle(container).rowGap` 实测, 三层各存一份。
 */
const ROW_WIN_MIN = 200;        // 行数低于此值不开窗口
const ROW_WIN_OVERSCAN = 10;    // 视口上下各多渲染的行数(快速滚动时不露白)
// 首帧还没量到行高时的估算值(px)。估错只会让第一帧窗口略偏, 测到真值后同一帧即纠正;
// 若没有它, 首轮就得先全量渲染 3000 行才能量到行高 —— 白付一次 300ms。
const ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34 };
// 行间距兜底值: 仅在容器还没量到(或 rowGap 解析不出, 如块级容器的 "normal")时使用。
const ROW_WIN_GAP_FALLBACK = 0;


/* 业务名词单点表(FX-10): "分组"这个叫法不够具体, **面向用户**的文案统一改称"辅种"。
 * 只改文案 —— 代码标识(变量 / 后端键 / API 路径 / CSS 类)一律不动, 否则会牵动后端契约
 * 与列宽存储键; 集中成常量便于下次口径统一时单点替换, 也让"哪些是业务名词"在代码里可检索。
 * 设置页里的"配置分组"是 schema 分组(无关语义), 不适用本常量。 */
const L10N_GROUP = "辅种";

const emptyColState = () => ({ widths: {}, hidden: {}, manual: {}, order: {} });

function columnKeys(page) {
  return TABLE_COLUMNS[page].map((c) => c.key);
}

function columnDef(page, key) {
  return TABLE_COLUMNS[page].find((c) => c.key === key) || null;
}

/* 模板里的最小宽度(minmax 首参 或 固定 px) —— 新显示的列/自适应失败时用它兜底 */
function templateMinPx(tpl) {
  const m = String(tpl).match(/^minmax\((\d+(?:\.\d+)?)px/) || String(tpl).match(/^(\d+(?:\.\d+)?)px$/);
  return m ? Math.round(parseFloat(m[1])) : MIN_COL_PX;
}

/* 读列状态原始对象: 当前键优先; 缺失/损坏时回退旧键(跨版本迁移), 迁移命中即回写当前键。
 * 单点收口在这里 —— loadColState 只管洗净与兜底, 不关心键从哪来。 */
function readColStateRaw() {
  for (const key of [COLS_STORE_KEY, ...LEGACY_COLS_KEYS]) {
    try {
      const raw = JSON.parse(localStorage.getItem(key));
      if (raw && typeof raw === "object") {
        if (key !== COLS_STORE_KEY) {
          try { localStorage.setItem(COLS_STORE_KEY, JSON.stringify(raw)); } catch { /* 私隐模式: 本次会话内仍生效 */ }
        }
        return raw;
      }
    } catch { /* 该键缺失/损坏: 继续尝试旧键 */ }
  }
  return null;
}

function loadColState() {
  try {
    const raw = readColStateRaw();
    if (!raw || typeof raw !== "object") return emptyColState();
    const out = emptyColState();
    for (const page of ["group", "detail", "torrent", "show"]) {
      const keys = columnKeys(page);
      const w = (raw.widths || {})[page];
      if (w && typeof w === "object") {
        const clean = {};
        for (const [k, v] of Object.entries(w)) {
          if (keys.includes(k) && /^\d+px$/.test(v)) clean[k] = v;
        }
        if (Object.keys(clean).length) out.widths[page] = clean;
      }
      const h = (raw.hidden || {})[page];
      if (Array.isArray(h)) {
        // locked 列即使被写进存储也忽略(列定义变更后可能残留)
        out.hidden[page] = h.filter((k) => keys.includes(k) && !(columnDef(page, k) || {}).locked);
      }
      const o = (raw.order || {})[page];
      if (Array.isArray(o)) {
        // 列序(TBL-05): 只收合法列 key 并去重; 缺失列(新增列)由 _visibleCols/_orderedKeys 按定义序补尾
        const seen = new Set();
        const clean = [];
        for (const k of o) {
          if (keys.includes(k) && !seen.has(k)) { seen.add(k); clean.push(k); }
        }
        if (clean.length) out.order[page] = clean;
      }
      out.manual[page] = !!(raw.manual || {})[page];
    }
    return out;
  } catch {
    return emptyColState();
  }
}

const initialColState = loadColState();  // 模块级只读一次(data() 的初值来源)

/* 视图/信息栏模式初值(持久化用户偏好; 异常时回退默认) */
function initialViewMode() {
  try {
    const saved = localStorage.getItem("autoqb.ui.view");
    return saved === "torrents" || saved === "shows" ? saved : "groups";
  } catch {
    return "groups";
  }
}

/* 状态优先级**单点表**(数值越小越"该被看到"): "一组/一集种子的聚合状态取哪个"。
 *
 * 必须与后端 `auto_qb/mixins/web_view.py::_SHOW_STATE_RANK` **逐项一致** —— 追剧页的集状态
 * (`e.state`) 是后端按那张表算好后回传的, 而辅种页的组状态 (`decoratedGroups.status.primary`)
 * 是前端按这张表算的。两张表一旦不一致, **同一批种子在两个页面会显示成不同颜色**;
 * 更糟的是乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
 * 两表一致性由 `tests/test_web.py::test_frontend_state_rank_matches_backend` 机械守卫(改一边必须改另一边)。
 *
 * 曾用顺序 ["error","checking","downloading","seeding","paused","other"] —— 与后端差两处:
 * {downloading,checking} 组后端取 downloading、前端取 checking; {paused,seeding} 组后端取 paused、
 * 前端取 seeding(BUG-7)。统一到后端表 = 语义变成"先报需要处理的, 再报在跑的, 最后报已完成的"。
 */
const STATE_RANK = { error: 0, downloading: 1, checking: 2, paused: 3, seeding: 4, other: 5 };
// 表里没有的 kind 排到最后(与后端 `_SHOW_STATE_RANK.get(k, 9)` 同口径)
const STATE_RANK_LAST = 9;

const app = createApp({
  data() {
    return {
      token: "",  // 已验证通过的密钥(唯一可信身份); 仅 bootstrap 验证成功后提交
      l10nGroup: L10N_GROUP,  // FX-10: 模板里的业务名词(单点, 见文件顶部常量)
      pendingToken: "",  // 验证中的候选密钥(不参与渲染门控/请求头); 服务不可达时供"重试连接"复用
      tokenInput: "",
      authRequired: true,  // 遮罩唯一开关: 仅在密钥验证成功后置 false —— 与 token 赋值解耦, 防错误密钥瞬间主界面闪现
      authPending: false,  // 密钥验证中: 禁用提交、按钮显示"验证中…", 防重复提交
      authError: "",
      authErrorKind: "",   // "auth" = 密钥被拒(401); "unavailable" = 服务不可达(保留候选密钥供重试)
      // R10-01: 鉴权模式显式化 —— 旧实现把"有身份"与"有密钥串"绑死, 本机免鉴权时 token 为空串,
      // 于是进主界面后首个请求就被自己的守卫判成无凭证 -> 登出回密钥页("必须先输一次才进得去")。
      // 现在守卫一律看 authMode: "local" = 本机免鉴权(直接放行, 且不发空 Bearer), "token" = 密钥流程。
      authMode: "token",
      page: "groups",
      groups: [],
      singles: [],            // 未归组种子(后端与 groups 同快照同门控回传, 供搜索兜底/总数回退)
      torrents: [],           // 种子页数据源: 全量种子平铺数组(SEED_ITEM, 与 groups 同门控回传)
      shows: { list: [], unrecognized: [] },  // 追剧视图(剧→季→集聚合, 与 groups 同门控回传)
      // 辅种页视图: groups(分组表) | torrents(单种子平铺) | shows(追剧); 列模型/列宽/排序独立, 筛选与搜索共用
      viewMode: initialViewMode(),
      status: {},
      // ⚠️ 轮询间隔不在这里 —— 见 computed.basePollMs(): 前端是服务端状态的**封顶**
      // (后端数据再快也要等下一轮轮询才可见), P1 落地后改成按种子量分档。
      // P0-0 埋点(排查用, 不参与渲染): 单次命令端到端耗时与单轮视图赋值耗时
      cmdStats: null,  // { cmdId, totalMs, waitMs, execMs } —— waitMs 排队等主循环, execMs 执行
      renderMs: 0,  // 单轮 refresh() 中"赋值 + 多选交集"的耗时(不含网络)
      pendingOps: {},  // P0-3 乐观 UI: hash -> { patch, prev, ts }, 见 isPending/applyOptimistic
      /* P0-3 组行乐观: 组 key -> { primary, ts }。与 pendingOps 同一套语义, 但**只存"结果"**
       * 不存 prev —— 组对象是 decoratedGroups 的**拷贝**(非响应式), 直接改 g.status 不会触发
       * 重渲染, 所以补丁走这个响应式覆盖表, 由 groupPrimary(g) 现问现用; 回滚 = 删掉覆盖,
       * 真值本来就没被改过(比成员行的 prev 回滚更不容易留假状态)。 */
      pendingGroupOps: {},
      // P1-2 行窗口化(常量与原理见文件顶部 ROW_WIN_* 注释)
      rowWin: true,          // 总开关(诊断用): 关掉即全量渲染。窗口的"退避"不走这里 ——
                             // 展开分组/行数不足阈值时由 _rowWindow 直接返回 inactive(见其注释)
      _winScrollY: 0,        // 最近一次窗口滚动位置(rAF 合帧写入; 响应式 -> 触发窗口重算)
      _winViewH: 0,          // 视口高度
      _winResize: 0,         // resize 计数(签名里带上它, 让窗口/列宽变化后重算)
      // 实测行高**均值**(未量过的行的兜底值; 逐行真值在 _rowHs); 响应式 —— 变了要重排窗口
      _rowH: { torrent: 0, group: 0, member: 0 },
      _rowHVer: 0,       // 行高表版本: 每量到新高度就 +1, 触发窗口重算(逐行真值是非响应式的)
      expandedKey: null,
      // 排序: 默认 = 组内最近添加时间降序(见 DEFAULT_SORT); 点击列头按 降序->升序->恢复默认 三态循环
      sortKey: DEFAULT_SORT.key,
      sortDir: DEFAULT_SORT.dir,
      // 展开明细表排序(与三视图正交, 三个视图的明细共用): 空键 = 后端原序
      detailSortKey: "",
      detailSortDir: -1,
      // 单种子视图独立排序键(与分组表互不干扰, 同三态语义)
      torrentSortKey: DEFAULT_SORT.key,
      torrentSortDir: DEFAULT_SORT.dir,
      // 追剧视图: 默认按最近动静降序(后端同序); 剧展开列表与集明细展开键(Vue 内存态)
      showSortKey: "latest",
      showSortDir: -1,
      expandedShows: [],
      expandedShowEp: null,
      unrecognizedOpen: false,  // 未识别折叠区展开态(追剧视图)
      groupColumns: GROUP_COLUMNS,
      detailColumns: DETAIL_COLUMNS,
      // 种子详情抽屉(R1B): 各 tab 数据与加载态; _drawerTimer 轮询句柄挂实例(非响应式)
      drawer: {
        open: false, hash: "", tab: "general", loading: false, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false,
      },
      torrentColumns: TORRENT_COLUMNS,  // 单种子视图列模型(列选择器第三段)
      showColumns: SHOW_COLUMNS,        // 追剧视图列模型(列选择器第四段)
      // 列状态(定义见文件顶部列模型; 列宽按**列 key** 记忆, 隐藏列由列选择器管理)
      colWidths: initialColState.widths,  // {page: {列key: "120px"}}
      colHidden: initialColState.hidden,  // {page: [列key]}
      colManual: initialColState.manual,  // {page: bool}: 是否手动调过列宽(调过则不再随窗口自适应)
      colOrder: initialColState.order,    // {page: [列key]}: 列顺序(TBL-05 表头拖动重排; 空 = 定义顺序)
      colMenuOpen: false,                 // 列选择器弹层开关
      colMenuAt: null,                    // 列选择器 fixed 锚点(表头右键路径 {x,y,mh}; null = 按钮路径走 CSS 定位)
      colDrag: null,                      // 表头拖动重排进行中(TBL-05): {page, key, idx, x} — idx=可视列插入边界, x=指示线位置
      // FX-25: 拖动虚影(跟随光标的列名胶囊)。刻意不用 HTML5 draggable 的原生拖影 —— 它会与
      // "点击排序"与"列宽拖拽"互相干扰; 自绘虚影与现有 mousedown 阈值手势完全解耦。
      colGhost: null,                     // {label, x, y} | null
      menu: { visible: false, x: 0, y: 0, key: null, hash: null },
      // FX-15: 右键菜单的次级菜单(flyout)展开态与翻转态 —— "高级能力"/"复制" 两个子面板
      subMenu: "",        // "" | "advanced" | "copy"
      subFlip: false,     // 子面板向左翻(父项靠右, 右展会伸出视口)
      // 表头右键菜单(TBL-05): 针对**该列**的操作 —— 隐藏「列名」(隐藏单列)/升序/降序/打开列选择器
      headMenu: { visible: false, x: 0, y: 0, page: "", key: "", label: "", sortable: false, locked: false },
      // 内容页签文件优先级小菜单(复用 .ctx-menu 视觉): 锚定单元格, 视口吸附; index = 文件在种子内的原始下标
      filePrio: { visible: false, x: 0, y: 0, index: -1 },
      drawerSelPath: "",    // 内容页签选中行(文件/目录完整相对路径); 顶部"重命名…"的作用对象
      serviceDown: false,  // 服务不可达(程序退出): 显示全局横幅, 轮询继续以便恢复后自动接上
      pollFails: 0,        // 连续失败次数(轮询退避: 2s→4s→8s→15s 上限)
      pollTimer: null,     // setTimeout 链式轮询句柄(上一轮结束后再计时, 不堆叠请求)
      lastRid: null,       // 已持有的分组视图版本(服务端 rid); null = 尚未取到(强制全量)
      searchQuery: "",       // 搜索关键字
      searchHits: new Set(),  // 命中种子 hash 集合(名称/文件匹配)
      searchUncovered: [],    // 未归组的命中种子(分组未启用/文件列表不可读), 以虚拟行兜底展示
      searchBuilding: false,  // 文件索引构建中(增量限流可能多轮, 需稍后重查)
      searchError: "",        // 搜索请求失败提示(不再静默)
      searchTimer: null,      // 防抖 + 索引构建自动重查定时器
      kindFilter: "",         // 状态筛选(seeding/downloading/... ; 空 = 不筛选)
      // 多选筛选(组内任一成员命中任一选中值即保留该组; 同一筛选器内多选为"或")
      // pathFilter 与其它筛选器同形(数组多选) —— 四个筛选器共用一份 filterDefs 与渲染模板
      pathFilter: [],
      tagFilter: [],
      categoryFilter: [],
      siteFilter: [],
      hrFilter: [],          // H&R 筛选(达标/未达标; 与其它多选筛选器同形, 口径见 _hrBucket)
      filterMenu: "",         // 当前展开的筛选弹层: "" | "tag" | "category" | "site" | "hr" | "path"
      popFlip: false,         // 筛选弹层视口翻转(锚点靠右时改为右对齐, 避免伸出屏幕)
      colFlip: false,         // 列选择器弹层视口翻转(同上)
      toasts: [],             // 站内提示条(替代 alert)
      modal: {                // 站内确认/输入框(替代 confirm/prompt); 结构见 _modalInit
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
      },
      _toastSeq: 0,           // 提示条自增 id
      _modalResolve: null,    // 模态 Promise 的 resolve(单例, 关闭时结算)
      _colAlignCss: "",       // 已注入的列对齐 CSS(值未变不重写 <style>)
      _headH: 0,              // 顶栏+状态条实测高度(写 :root --head-h, 供左栏吸顶定位; 含批量段, FIX-06)
      // P1-3 顶栏尺寸观察器: 元素引用 / 观察器 / rAF 句柄(字段名避开同名方法 _headEl)
      _headObsEl: null,
      _headObs: null,
      _headRaf: 0,
      // 多选(分组表/明细表): Ctrl/⌘+点击切换, Shift+点击锚点范围; 普通点击行为不变(组=展开)
      selGroups: [],          // 选中组 key
      selMembers: [],         // 选中成员 hash
      selAnchorGroup: null,   // 分组表 Shift 锚点(组 key; shift 后不更新, 便于多次扩展同一范围)
      selAnchorMember: null,  // 明细表 Shift 锚点(成员 hash)
      selAnchorUnit: null,    // FX-12: 追剧页 Shift 锚点(剧/集单元 id)
      // 历史流量弹层(今日流量面板入口; 数据源 /api/traffic/history, 按日原始行)
      historyOpen: false,
      historyGran: "day",     // day | month | year
      historyData: [],
      historyLoading: false,
      historyError: "",
      histHoverIdx: -1,       // 悬停柱桶索引(-1 = 无)
      // 登录"验证中"加载态(本地密钥 bootstrap 期间 true): 修复刷新时闪现输入密钥界面。
      // FX-01: 初值必须为 true —— 首帧状态**未知**, 不能当作"未授权"渲染密钥表单。
      // 离开该状态只有三条明确路径(见 mounted/bootstrap): 本机免鉴权 / 密钥验证通过 / 无密钥或验证被拒。
      bootstrapping: true,
      // 添加种子对话框(R1B): 来源 = .torrent 多选 + magnet/URL 文本域混合; 提交走 JSON(base64 文件)
      addOpen: false,
      addSubmitting: false,   // 提交中(按钮 loading, 阻止重复提交与误关闭)
      addFiles: [],           // 已选 .torrent File 对象(展示用元信息; 前端读为 base64 随 JSON 上送)
      addUrls: "",            // magnet / http(s) 链接, 每行一条
      addShowUrls: false,     // DLG-03: 链接输入框展开态(默认隐藏, 「添加链接」按钮切换)
      addSavePath: "",        // 保存路径(空 = qB 默认)
      addCategory: "",        // 分类(可空; combobox = 下拉候选 + 自由输入)
      addTags: "",            // 标签(逗号分隔, 可空; combobox)
      addStart: false,        // DLG-03: 添加后开始(勾选 = 立即开始; 默认不勾 = paused 添加)
      addSkipCheck: false,    // 跳过校验(危险选项: 勾选后选项区下出警告行)
      addSequential: false,   // 顺序下载
      addFirstLast: false,    // 首末块优先
      addTmm: false,          // 自动种子管理(TMM)
      addCatOptions: [],      // DLG-03: 分类候选(GET /api/categories, 打开窗口时拉取)
      addTagOptions: [],      // DLG-03: 标签候选(GET /api/tags, 打开窗口时拉取)
      addCatMenu: false,      // 分类下拉展开态
      addTagMenu: false,      // 标签下拉展开态
      addCatHi: -1,           // 分类下拉键盘高亮
      addTagHi: -1,           // 标签下拉键盘高亮
      addPathOptions: [],     // DLG-04: 保存路径候选(GET /api/paths, 已排序去重)
      addPathPop: false,      // DLG-04: 选择位置面板展开态
      addPathHi: -1,          // 位置面板键盘高亮
      // R10-11 路径选择器(决策 D2-A): 服务端目录浏览 —— 浏览器拿不到本地绝对路径
      // (目录上传控件只暴露相对路径), 所以"像选 .torrent 那样"只能由服务端给路径。
      // 只列目录 + 上遒 + 新建文件夹; 安全边界(允许根白名单/.. 穿越/符号链接逃逸)在后端。
      dirBrowse: {
        open: false, path: "", parent: "", roots: [], dirs: [],
        loading: false, error: "", newName: "", busy: false,
      },
      // 统计面板(FE-2C): /api/stats → {server: qB server_state | null}; 打开时取一次, 卡内可手动刷新
      statsOpen: false,
      statsLoading: false,
      statsError: "",
      statsServer: null,
      // 日志页(FE-2C): /api/log 只读 tail; 无自动轮询(等级/行数变更与刷新按钮均手动触发)
      logs: {
        loading: false, error: "", loaded: false,
        lines: [], file: "",
        level: "",            // ""=全部 | INFO | WARNING | ERROR(后端按 [LEVEL 标记过滤)
        num: 300,             // tail 行数(后端钳制 10..2000)
      },
      // 限速托管状态(FE-2C D2): /api/speed/mode 展示 + /api/speed/override 临时覆盖
      speedMode: { loaded: false, curveEnabled: false, target: null, current: null, error: "" },
      speedOverride: { up: "", down: "", busy: false },  // 两方向都必填数字(后端语义: 两方向都设置, 0=不限)
      speedOpen: false,  // SPD-04: 限速修改浮层(qB 式「点击限速 → 弹窗」, 表单从信息栏收进窗内)
      // FX-08: 浮层锚点 —— left 由点击坐标算出(状态栏"限制速度"按钮左缘 - 12), dir 为预聚焦方向
      speedAt: { left: 0, dir: "up" },
      // 分类/标签管理对话框(FE-2C2): GET /api/categories|tags 拉列表 + 新建行; 行级改路径/删除走既有确认/输入原语
      mgrOpen: "",           // "" | "category" | "tag"(同一时刻只开一个)
      mgrLoading: false,
      mgrError: "",
      mgrCategories: [],     // [{name, save_path}](GET /api/categories 的 map 展平)
      mgrTags: [],           // [名字...](GET /api/tags 原样)
      mgrNewCatName: "",     // 新建分类行: 名称
      mgrNewCatPath: "",     // 新建分类行: 保存路径(可空)
      mgrNewTags: "",        // 新建标签行: 逗号分隔可批量
      mgrBusy: false,        // 写操作回执等待中(防重复提交 + 关闭窗口误触)
    };
  },
  computed: {
    pollLabel() {
      // 顶栏展示当前轮询间隔(自适应: 按种子量分档 + 服务不可达时退避)
      return Math.round(this.currentPollMs() / 1000);
    },
    statusBadge() {
      if (this.status.paused) return { text: "已暂停", kind: "warn" };
      if (this.status.connected === false) return { text: "qB 断开", kind: "error" };
      if (this.status.connected === true) return { text: "运行中", kind: "ok" };
      return { text: "连接中…", kind: "warn" };
    },
    /* R10-01 鉴权判据单点: 所有"能不能发请求"的守卫(api/轮询续排/标签页可见性)都用它,
     * 避免"改两处漏一处"导致轮询静默停摆。本机免鉴权下 token 为空是合法状态。 */
    authOk() {
      return this.authMode === "local" || !!this.token;
    },
    sortedGroups() {
      const key = this.sortKey, dir = this.sortDir;
      return [...this.decoratedGroups].sort((a, b) => {
        const va = a[key], vb = b[key];
        let r;
        if (typeof va === "string") r = (va || "").localeCompare(vb || "");
        else r = (va || 0) - (vb || 0);
        // 同值时按名称稳定排序(avoid_on 同秒添加的组不会因排序抖动而互换位置)
        if (r === 0 && key !== "name") r = (a.name || "").localeCompare(b.name || "");
        return dir * r;
      });
    },
    /* 是否有任何乐观补丁在飞(computed 缓存)。给"逐成员问 isPending"的调用点做 O(1) 短路 ——
     * 集行动辄上百成员, 若无补丁还逐个查, 每次重渲染都是几百次无用查找(见 isEpPending)。 */
    pendingAny() {
      return Object.keys(this.pendingOps).length > 0;
    },
    /* 组级派生展示数据(依赖 groups, 仅在分组数据变化时算一次; 渲染多帧不重算):
     * 保存路径(筛选器)、状态摘要(图标+配色+计数)、共同标签/分类(含差异标记)、大小一致性
     *
     * 交集/共同值在**前端**计算: 后端只透出成员原始值, 避免每次视图重建做集合运算。
     */
    decoratedGroups() {
      return this.groups.map((g) => {
        return {
          ...g,
          save_path: (g.members[0] && g.members[0].save_path) || "",
          status: this._aggStatus(g.members),
          commonTags: this._commonTags(g.members),
          commonCategory: this._commonCategory(g.members),
          sizeMismatch: new Set(g.members.map((m) => m.size)).size > 1,
        };
      });
    },
    /* 保存路径筛选选项(按组数排序) —— 与标签/分类/站点同形, 供统一的 filterDefs 直接取用 */
    pathOptions() {
      const counts = new Map();
      for (const g of this.decoratedGroups) counts.set(g.save_path, (counts.get(g.save_path) || 0) + 1);
      return [...counts.entries()].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count);
    },
    filtersActive() {
      return !!(this.kindFilter || this.pathFilter.length || this.tagFilter.length || this.categoryFilter.length ||
        this.siteFilter.length || this.hrFilter.length || (this.searchQuery || "").trim());
    },
    /* 四个筛选器的定义(模板只遍历这一份, 不再手写四块相同结构)
     * 路径筛选器与其它三个同形(多选数组): 选中项存 field 指向的数组, 计数口径 = 组数
     */
    filterDefs() {
      return [
        { kind: "tag", label: "标签", icon: "i-tag", options: this.tagOptions, selected: this.tagFilter, field: "tagFilter" },
        { kind: "category", label: "分类", icon: "i-folder", options: this.categoryOptions, selected: this.categoryFilter, field: "categoryFilter" },
        { kind: "site", label: "站点", icon: "i-globe", options: this.siteOptions, selected: this.siteFilter, field: "siteFilter" },
        // H&R 筛选(R07): 固定两档, 计数口径 = 组数(与其它筛选器一致); 分组/单种子两视图共用同一份筛选状态
        { kind: "hr", label: "H&R", icon: "i-hr", options: this.hrOptions, selected: this.hrFilter, field: "hrFilter" },
        { kind: "path", label: "路径", icon: "i-folder-open", options: this.pathOptions, selected: this.pathFilter, field: "pathFilter" },
      ];
    },
    /* H&R 两档计数(只消费后端算好的组级计数, 前端不重算模板/阈值, 见 pitfalls):
     * 达标 = 触发过 HR 且已全部满足; 未达标 = 仍有成员未满足; 无 HR 组不匹配任何档 */
    hrOptions() {
      let done = 0;
      let pending = 0;
      for (const g of this.decoratedGroups) {
        if (!g.hr_triggered) continue;
        if (g.hr_pending > 0) pending += 1;
        else done += 1;
      }
      return [{ value: "达标", count: done }, { value: "未达标", count: pending }];
    },
    tagOptions() {
      return this._memberValueOptions((m) => m.tags || []);
    },
    categoryOptions() {
      return this._memberValueOptions((m) => (m.category ? [m.category] : []));
    },
    siteOptions() {
      return this._memberValueOptions((m) => (m.site ? [m.site] : []));
    },
    /* 列模板: computed 缓存(列宽/列显隐变化才变), 行渲染只取同一引用, 不再每行拼字符串 */
    groupGrid() {
      return { gridTemplateColumns: this._gridTemplate("group") };
    },
    detailGrid() {
      return { gridTemplateColumns: this._gridTemplate("detail") };
    },
    torrentGrid() {
      return { gridTemplateColumns: this._gridTemplate("torrent") };
    },
    showGrid() {
      return { gridTemplateColumns: this._gridTemplate("show") };
    },
    /* 列对齐规则(R10-08): align 定义在列模型里, 这里按**当前可见列**生成 :nth-child 规则注入 <head>。
     *
     * 为何生成而非在模板里逐格挂类: 值单元格共 67 个 × 4 视图 × 2 套 UI, 逐格挂类必然漏改;
     * 生成则"列模型改一处, 表头与值同源"(表头同样按可见列索引渲染, 顺序天然一致)。
     *
     * 选择器用 :where() 把特异性压到 0,1,0(只剩 :nth-child 那一位), 于是:
     *   - 胜过 .g-stat/.m-stat(0,1,0, 同权重靠源顺序: 注入的 <style> 在样式表之后) -> 非默认对齐生效;
     *   - 输给 .g-stat.zero/.m-stat.zero(0,2,0) -> 保留既有"0 值居中"口径。
     * 同时写 text-align 与 justify-content: 值单元格有的是块级文本, 有的是 flex(进度条/
     * 分享率对/芯片组), 只写 text-align 会漏掉后者。
     * ⚠ **left 也必须生成**: 数值列的值格子带 .g-stat/.m-stat(right), 若因为"left 是默认值"就跳过,
     *    左对齐的口径会被这两条通用规则盖掉(实测: 添加于列表头左、值右)。
     */
    colAlignCss() {
      const out = [];
      for (const page of ["group", "detail", "torrent", "show"]) {
        const cols = this._visibleCols(page);
        for (let i = 0; i < cols.length; i++) {
          const align = cols[i].align || "left";
          const just = align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start";
          out.push(`:where([data-table="${page}"]) > :nth-child(${i + 1}) { text-align: ${align}; justify-content: ${just}; }`);
        }
      }
      return out.join("\n");
    },
    // 搜索是辅种管理的筛选: 在真实辅种组上筛选——组内任一成员命中即保留整组(组行沿用真实 key,
    // 组级操作可用), 仅命中成员 search-hit 高亮; 未归组的命中种子(分组未启用/文件列表不可读等)
    // 以单种子虚拟行兜底展示(虚拟行无组级操作, 右键退化为该种子的单种子菜单)。
    // 状态筛选(kindFilter)与之叠加: 先按成员状态筛组(组内任一成员为该状态即保留), 再做搜索匹配。
    filteredGroups() {
      const q = (this.searchQuery || "").trim();
      let base = this.sortedGroups;
      if (this.kindFilter) base = base.filter((g) => g.members.some((m) => m.kind === this.kindFilter));
      // 多选筛选: 同一筛选器内为"或"(任一命中), 不同筛选器之间为"且"; H&R 见 _hrBucket 口径
      if (this.hrFilter.length) {
        base = base.filter((g) => this.hrFilter.includes(this._hrBucket(g)));
      }
      if (this.pathFilter.length) {
        base = base.filter((g) => this.pathFilter.includes(g.save_path));
      }
      if (this.tagFilter.length) {
        base = base.filter((g) => g.members.some((m) => (m.tags || []).some((t) => this.tagFilter.includes(t))));
      }
      if (this.categoryFilter.length) {
        base = base.filter((g) => g.members.some((m) => this.categoryFilter.includes(m.category || "")));
      }
      if (this.siteFilter.length) {
        base = base.filter((g) => g.members.some((m) => this.siteFilter.includes(m.site)));
      }
      if (!q) return base;
      const hits = this.searchHits;
      const kept = [];
      for (const g of base) {
        let hit = false;
        const members = g.members.map((m) => {
          const isHit = hits.has(m.hash);
          if (isHit) hit = true;
          return { ...m, hit: isHit };
        });
        if (hit) kept.push({ ...g, members: members, virtual: false, hit: true });
      }
      for (const r of this.searchUncovered) {
        if (this.kindFilter && r.kind !== this.kindFilter) continue;
        if (this.hrFilter.length && !this.hrFilter.includes(this._hrBucketMember(r))) continue;
        if (this.pathFilter.length && !this.pathFilter.includes(r.save_path || "")) continue;
        if (this.tagFilter.length && !(r.tags || []).some((t) => this.tagFilter.includes(t))) continue;
        if (this.categoryFilter.length && !this.categoryFilter.includes(r.category || "")) continue;
        if (this.siteFilter.length && !this.siteFilter.includes(r.site)) continue;
        kept.push({
          key: "u-" + r.hash, name: r.name, count: 1, virtual: true,
          dlspeed: r.dlspeed, upspeed: r.upspeed, uploaded: r.uploaded, size: r.size,
          total_size: r.size, save_path: r.save_path || "",
          // 未归组种子同样携带排序与 HR 字段, 保证搜索视图内排序/列显示与真实组一致
          added_on: r.added_on || 0,
          hr_triggered: r.hr_triggered ? 1 : 0,
          hr_pending: r.hr_triggered && !r.hr_satisfied ? 1 : 0,
          status: { primary: r.kind, text: this.kindText(r.kind) },
          commonTags: { list: this.mTags(r), diff: false },
          commonCategory: { value: r.category || "", diff: false },
          sizeMismatch: false,
          members: [{ ...r, hit: true }],
        });
      }
      return kept;
    },
    /* 种子页(R1A, 原 R08 单种子视图升级): 数据源 = state.torrents 全量平铺数组(SEED_ITEM),
     * 每个种子独立过同一套筛选(与分组视图的"组内任一命中保留整组"语义不同: 这里逐种子判定);
     * 搜索为**客户端文本过滤**(名称/站点/分类/标签/保存路径, 子串不区分大小写), 不依赖服务端
     * 文件搜索结果 —— 文件命中(searchHits)仅用作高亮; 排序独立(三态同分组表) */
    filteredTorrents() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const out = [];
      for (const r of this.torrents) {
        if (!this._memberPass(r)) continue;
        if (q && !this._torrentTextMatch(r, q)) continue;
        /* ❗刻意**不复制**成 { ...r, hit }: 每条 74 个字段, 复制要经一遍响应式代理的 get 陷阱
         * (3000 条 = 22 万次), 实测**仅这一句就 68ms** —— 比整个窗口渲染还贵。
         * 命中高亮改由模板问 searchHits(见 isHit), 语义不变; 顺带每轮少建 3000 个临时对象。 */
        out.push(r);
      }
      const key = this.torrentSortKey;
      const dir = this.torrentSortDir;
      out.sort((a, b) => {
        const va = a[key];
        const vb = b[key];
        let r;
        if (typeof va === "string") r = (va || "").localeCompare(vb || "");
        else r = (va || 0) - (vb || 0);
        if (r === 0 && key !== "name") r = (a.name || "").localeCompare(b.name || "");
        return dir * r;
      });
      return out;
    },
    /* ---------------- P1-2 行窗口: 只决定"渲染哪一段", 不参与任何业务语义 ----------------
     * 三个窗口共用 _rowWindow(); 未启用时 win.active=false, 切片 = 全量、上下占位 = 0,
     * 模板与不开窗时完全等价(因此关掉开关就是老行为, 回退路径零成本)。 */
    torrentWin() {
      return this._rowWindow("torrent", this.filteredTorrents, "torrentTable");
    },
    visibleTorrents() {
      const w = this.torrentWin;
      return w.active ? this.filteredTorrents.slice(w.start, w.end) : this.filteredTorrents;
    },
    torrentPadTop() {
      return this.torrentWin.padTop;
    },
    torrentPadBottom() {
      return this.torrentWin.padBottom;
    },
    /* 分组页: **有展开面板时退避** —— .detail 高度不定(含明细表头 + N 行成员), 会让后续行的
     * 位置偏离"第 i 行在 i×step"的假设(硬约束 ②); 此时回退全量渲染, 宁可慢也不能错位。 */
    groupWin() {
      const n = this.filteredGroups.length;
      if (this.expandedKey) return { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      return this._rowWindow("group", this.filteredGroups, "groupTable");
    },
    visibleGroups() {
      const w = this.groupWin;
      return w.active ? this.filteredGroups.slice(w.start, w.end) : this.filteredGroups;
    },
    groupPadTop() {
      return this.groupWin.padTop;
    },
    groupPadBottom() {
      return this.groupWin.padBottom;
    },
    /* 成员行(展开明细): 行数 = **当前展开单元**的成员数。容器是 .detail(不是 .group-table),
     * 用 ref=detailHead 的父元素定位; 成员数通常很小(阈值以下自动不开窗)。
     * ❗参数是当前展开单元的成员数组, 由模板传入(分组页传 g.members, 追剧页传 e.members) ——
     * 曾经写死读 expandedGroup, 而追剧页的展开态是 expandedShowEp(expandedKey 恒为 null)
     * ⇒ 追剧页的成员窗口恒为空、占位恒为 0, 与模板注释"集成员行同样走窗口"相反(BUG-2)。 */
    memberWin(list) {
      return this._rowWindow("member", list || [], null);
    },
    memberPadTop(list) {
      return this.memberWin(list).padTop;
    },
    memberPadBottom(list) {
      return this.memberWin(list).padBottom;
    },
    totalTorrents() {
      // 种子页数据源到位后直接取平铺数组长度(权威口径); 旧响应缺 torrents 时回退 分组+未归组 合计
      if (this.torrents.length) return this.torrents.length;
      return this.groups.reduce((n, g) => n + g.count, 0) + this.singles.length;
    },
    totalDl() {
      return this.groups.reduce((n, g) => n + g.dlspeed, 0);
    },
    totalUl() {
      return this.groups.reduce((n, g) => n + g.upspeed, 0);
    },
    /* 底部状态栏左侧常显统计摘要(TBL-08 修订; **FX-07 精简**): "统计不应该藏到弹出框中" ——
     * 取 /api/stats 的 server_state(纯内存快照, 与主轮询同周期静默同步)。
     * FX-07: 退役 本次 / 累计 / DHT 三项(本次与累计与"今日流量"口径重叠, DHT 属低频诊断),
     * 只留 连接 与 剩余 两个运行态指标; 今日流量改由模板单独渲染(数据源不同, 见 todayTraffic)。
     * server_state 未同步时返回空数组 → 显示未同步提示 */
    sbStats() {
      const s = this.statsServer;
      if (!s) return [];
      const items = [
        {
          key: "peers",
          icon: "#i-link",
          cls: "ico-peers",
          label: "连接",
          value: this.statVal(s.total_peer_connections),
          title: "当前 peer 连接总数 · 连接状态: " + this.connText(s.connection_status),
        },
        {
          key: "disk",
          icon: "#i-hdd",
          cls: "ico-disk",
          label: "剩余",
          value: this.statVal(s.free_space_on_disk, (v) => this.fmtSize(v)),
          title: "qB 保存目录所在磁盘剩余空间",
        },
      ];
      return items;
    },
    /* 状态分布(纯前端聚合 members[].kind): 供顶栏下方堆叠条与可点击图例使用 */
    distSegments() {
      const order = ["seeding", "downloading", "checking", "paused", "error", "other"];
      const count = {};
      for (const g of this.groups) for (const m of g.members) count[m.kind] = (count[m.kind] || 0) + 1;
      const total = order.reduce((n, k) => n + (count[k] || 0), 0);
      if (!total) return [];
      return order.filter((k) => count[k]).map((k) => ({
        kind: k, count: count[k], pct: (count[k] / total) * 100, text: this.kindText(k),
      }));
    },
    distTotal() {
      return this.distSegments.reduce((n, s) => n + s.count, 0);
    },
    distTitle() {
      return this.distSegments.map((s) => `${s.text} ${s.count}`).join(" · ");
    },
    /* ---------------- 限速/流量快照(后端 SpeedCurveMixin 发布, 随 status 恒回传) ----------------
     * state: disabled(未启用限速曲线) / ok / dry_run / stale(数据源不可用)
     * periods[].up|down 为**字节**; limit.target|actual 为 **KiB/s**(0 = 不限速, null = 该方向不管理)
     */
    traffic() {
      return this.status.traffic || { state: "disabled", periods: [], limit: {} };
    },
    trafficOn() {
      return this.traffic.state !== "disabled";
    },
    todayTraffic() {
      return (this.traffic.periods || []).find((p) => p.period === "day") || null;
    },
    /* 今日流量悬浮说明: 把口径写清楚(数据源 = Traffic Monitor dat 的按日行, 单位字节) */
    todayTrafficTitle() {
      const t = this.todayTraffic;
      if (!t) return "";
      return `今日流量(Traffic Monitor 按日口径): 下载 ${this.fmtSize(t.down)} / 上传 ${this.fmtSize(t.up)}`
        + ` · 数据状态: ${this.traffic.state}`;
    },
    /* 全局限速取数单点(R10-04): qB server_state 的全局限速键是 **dl_rate_limit / up_rate_limit**
     * (bytes/s, 0 = 不限速), **不是 dl_limit/up_limit** —— 后者是**单种子**级字段(TorrentRecord,
     * 见 mixins/web_view.py 的种子限速列)。前端曾读 s.dl_limit/s.up_limit ⇒ 恒 undefined ⇒
     * 状态栏"限制速度"永远显示 "—", 同时作速度染色分母时也恒缺失 ⇒ 色阶从未生效(连带故障)。
     * 现在状态栏文案、速度染色分母两处全部引用本单点, 改口径只改这里。
     * 单位维持 bytes/s(与 fmtSpeed 同源); 浮层内的编辑仍走 /api/speed/mode 的 KiB/s 口径,
     * 两套单位各在自己的显示层换算, 不在同一函数里混用。
     * 语义: null = 未知(字段缺失), 0 = 不限速。 */
    speedLimitBytes() {
      const s = this.statsServer || {};
      const pick = (v) => (v === null || v === undefined || v === "" ? null : Number(v) || 0);
      return { down: pick(s.dl_rate_limit), up: pick(s.up_rate_limit) };
    },
    /* 状态栏"限制速度"文案(决策 D3 的收窄版: **只取 qB 当前生效值**)。
     * 0 = 不限速 -> "不限"; 字段缺失 -> "—"(区分"未知"与"不限")。
     * 刻意不从限速曲线快照的 limit.actual 取数: 状态栏并列两个口径会变成"限速对照面板"
     * (那是已退役的信息栏形态); 曲线的目标/命中信息在限速浮层内的 .speed-mode-line 展示。 */
    sbLimits() {
      const { down, up } = this.speedLimitBytes;
      const f = (v) => (v === null ? "—" : (v ? this.fmtSpeed(v) : "不限"));
      return { down: f(down), up: f(up) };
    },
    /* 限速对照行: 每个受管方向一行(该方向无曲线则不显示该行);
     * mismatch = 实际值已知且与命中目标不同 -> 前端据此"显示两个 + 原因"
     * tip 在**这里**算好(按方向取原因), 避免每个 pill 都展示全部方向的原因
     */
    limitRows() {
      const lim = this.traffic.limit || {};
      const target = lim.target || {}, actual = lim.actual || {}, reasons = lim.reasons || [];
      // 无方向特定原因时的默认说明(按快照状态区分: 试运行/数据不可用/正常)。
      // 必须在此内联为局部量 —— 本区段是 computed, 任何"看似方法的辅助函数"都会变成属性,
      // 在 computed 内以 this.xxx() 调用会抛 TypeError 导致整块渲染失败(2026-09-14 实测)。
      const fallback = this.traffic.state === "dry_run"
        ? "试运行(dry_run): 只显示命中限速, 不读取/不写入 qB"
        : this.traffic.state === "stale"
          ? "流量数据暂不可用, 限速沿用上一轮生效值"
          : "命中 = 曲线目标值, 实际 = qB 当前生效值";
      const rows = [];
      for (const [dir, label] of [["up", "上传"], ["down", "下载"]]) {
        const tg = target[dir];
        if (tg === null || tg === undefined) continue;
        const ac = actual[dir];
        const reason = reasons.find((r) => r.dir === dir) || null;
        const known = ac !== null && ac !== undefined;
        rows.push({
          dir,
          label,
          target: tg,
          actual: ac,
          mismatch: known && ac !== tg,
          reason,
          tip: reason ? reason.text : fallback,
        });
      }
      return rows;
    },
    /* 限速托管状态一行文案(FE-2C D2): 曲线托管中显示目标值; 未托管显示 qB 当前生效值 */
    speedModeLine() {
      const sm = this.speedMode;
      if (!sm.loaded) return "";
      if (sm.curveEnabled) {
        const t = sm.target || {};
        return `曲线托管中 · 目标 上${this.fmtLimit(t.upload_kib) || "不限速"} / 下${this.fmtLimit(t.download_kib) || "不限速"}`;
      }
      const c = sm.current || {};
      if (c.upload_limit === undefined && c.download_limit === undefined) return "未托管 · qB 限速未知";
      return `未托管 · qB 当前 上${this.fmtLimit(c.upload_limit) || "不限速"} / 下${this.fmtLimit(c.download_limit) || "不限速"}`;
    },
    /* 覆盖表单可提交: 两方向都已有数字(空串/非数字不放行 —— 后端两方向都设置, 漏传会被当 0=不限) */
    speedOvReady() {
      const o = this.speedOverride;
      return o.up !== "" && o.down !== "" && Number.isFinite(Number(o.up)) && Number.isFinite(Number(o.down));
    },
    /* 可见列(列选择器只改 colHidden; 顺序取 colOrder(表头拖动重排 TBL-05), 无自定义序时按列定义序) —— 表头/行/grid 模板共用 */
    visibleGroupCols() {
      return this._visibleCols("group");
    },
    visibleDetailCols() {
      return this._visibleCols("detail");
    },
    visibleTorrentCols() {
      return this._visibleCols("torrent");
    },
    visibleShowCols() {
      return this._visibleCols("show");
    },
    /* 成员索引: groups ∪ singles = 全量种子(shows 明细只带 hash, 从这里取完整成员视图,
     * 避免响应体重复成员数据; bulkDelete 摘要计数同源于此) */
    memberByHash() {
      const map = new Map();
      for (const g of this.groups) for (const m of g.members) map.set(m.hash, m);
      for (const r of this.singles) if (!map.has(r.hash)) map.set(r.hash, r);
      for (const r of this.torrents) if (!map.has(r.hash)) map.set(r.hash, r);  // SEED_ITEM 全量(magnet_uri 等扩展字段在这份)
      return map;
    },
    /* 追剧视图(R10): 后端已按剧→季→集聚合并算好聚合层; 前端只做 筛选/搜索(任一成员命中
     * 保留整集) + 剧级搜索命中(剧名含关键字保留全剧) + 排序。showHit 与 epHit 分开:
     * 剧名命中高亮整剧行, 集命中高亮集行(与分组视图"组内任一命中保留整组"同语义) */
    decoratedShows() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const hits = this.searchHits;
      const out = [];
      for (const s of this.shows.list) {
        let showHit = !!(q && (s.name || "").toLowerCase().includes(q));
        let keptEps = 0;
        let keptMembers = 0;
        const seasons = [];
        for (const sn of s.seasons) {
          const eps = [];
          for (const e of sn.episodes) {
            const members = e.members
              .map((h) => {
                const m = this.memberByHash.get(h);
                return m ? { ...m, hit: hits.has(h) } : null;
              })
              .filter(Boolean);
            if (!members.length) continue;
            if (!members.some((m) => this._memberPass(m))) continue;
            const epHit = members.some((m) => m.hit);
            if (q && !showHit && !epHit) continue;
            keptEps += 1;
            keptMembers += members.length;
            eps.push({ ...e, members, hit: epHit, epKeyStr: e.key.join("-") });
          }
          if (eps.length) seasons.push({ ...sn, episodes: eps });
        }
        if (showHit || seasons.length) {
          if (showHit) keptEps = s.episode_count;
          out.push({ ...s, seasons, hit: showHit, keptEps, keptMembers });
        }
      }
      const key = this.showSortKey;
      const dir = this.showSortDir;
      out.sort((a, b) => {
        let r;
        if (key === "name") r = dir * (a.name || "").localeCompare(b.name || "");
        else if (key === "episode_count") r = dir * (a.episode_count - b.episode_count);
        else r = dir * ((a.latest || 0) - (b.latest || 0));
        // 平局兜底按名升序且不随方向翻转(否则降序时同 latest 的剧会倒序排, 难以预期)
        if (r === 0) r = (a.name || "").localeCompare(b.name || "");
        return r;
      });
      return out;
    },
    /* 未识别折叠区: hash → 成员解析, 过同一套筛选/搜索, 按种子名排序 */
    unrecognizedTorrents() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const hits = this.searchHits;
      const out = [];
      for (const h of this.shows.unrecognized) {
        const m = this.memberByHash.get(h);
        if (!m) continue;
        if (!this._memberPass(m)) continue;
        const hit = hits.has(h);
        if (q && !hit) continue;
        out.push({ ...m, hit: q ? hit : false });
      }
      out.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      return out;
    },
    /* 追剧视图统计(状态条计数): 剧/集/成员三层 */
    showStats() {
      let eps = 0;
      let members = 0;
      for (const s of this.decoratedShows) {
        eps += s.keptEps;
        members += s.keptMembers;
      }
      return { shows: this.decoratedShows.length, eps, members, unrecognized: this.unrecognizedTorrents.length };
    },
    /* 多选总数(组 + 独立成员), 供批量浮条显隐 */
    selectedCount() {
      return this.selGroups.length + this.selMembers.length;
    },
    /* FX-12: 选择权威 -> 派生集合。**唯一权威**仍是 selGroups(组 key) 与 selMembers(成员 hash)
     * (FX-11 起两者互斥, 同一时刻只有一侧非空); 所有视图的"已选"一律读这里 ——
     * 组选择展开为成员 hash 闭包, 于是"辅种页选了 1 组"在种子页/追剧页同样看得出选中。 */
    selHashSet() {
      const s = new Set(this.selMembers);
      for (const k of this.selGroups) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) {
          if (g.members[0]) s.add(g.members[0].hash);
          continue;
        }
        for (const m of g.members || []) s.add(m.hash);
      }
      return s;
    },
    /* 添加种子对话框: 保存路径前缀比对已有辅种组(输入变化时轻量计数, 不发请求)。
     * 双向前缀: 输入是某组路径的父目录、或子目录, 都算同一路径树(尾部斜杠/大小写归一后比对)。 */
    addPathGroupCount() {
      const norm = (p) => (p || "").trim().replace(/[\\/]+$/, "").toLowerCase();
      const input = norm(this.addSavePath);
      if (!input) return 0;
      let n = 0;
      for (const g of this.decoratedGroups) {
        const p = norm(g.save_path);
        if (!p) continue;
        if (p.startsWith(input) || input.startsWith(p)) n += 1;
      }
      return n;
    },
    /* 添加可提交条件: 有文件或有非空链接行, 且不在提交中 */
    addCanSubmit() {
      if (this.addSubmitting) return false;
      if (this.addFiles.length) return true;
      return this.addUrls.split(/\r?\n/).some((l) => l.trim());
    },
    /* ---------------- 历史流量(弹层): 按日原始行 -> 天(最近30)/月(近12)/年(全部)聚合 ---------------- */
    historyBuckets() {
      const rows = this.historyData || [];
      if (this.historyGran === "month") {
        const m = new Map();
        for (const r of rows) {
          const k = r.date.slice(0, 7);
          const cur = m.get(k) || { up: 0, down: 0 };
          cur.up += r.up;
          cur.down += r.down;
          m.set(k, cur);
        }
        return [...m.entries()].slice(-12).map(([k, v]) => ({ label: k.slice(2), tip: k, up: v.up, down: v.down }));
      }
      if (this.historyGran === "year") {
        const y = new Map();
        for (const r of rows) {
          const k = r.date.slice(0, 4);
          const cur = y.get(k) || { up: 0, down: 0 };
          cur.up += r.up;
          cur.down += r.down;
          y.set(k, cur);
        }
        return [...y.entries()].map(([k, v]) => ({ label: k, tip: `${k} 年`, up: v.up, down: v.down }));
      }
      return rows.slice(-30).map((r) => ({ label: r.date.slice(5), tip: r.date, up: r.up, down: r.down }));
    },
    historyMax() {
      return Math.max(1, ...this.historyBuckets.map((b) => Math.max(b.up, b.down)));
    },
    historySummary() {
      const rows = this.historyBuckets;
      const up = rows.reduce((s, b) => s + b.up, 0);
      const down = rows.reduce((s, b) => s + b.down, 0);
      const peak = rows.reduce((m, b) => Math.max(m, b.up + b.down), 0);
      const avg = rows.length ? (up + down) / rows.length : 0;
      return { up, down, peak, avg };
    },
    /* 折线图几何(常量 + 桶数派生): 无参 computed, 模板以属性访问(不加括号);
     * 尺寸放大(第七轮用户要求"改大一点"): 弹层 860px, viewBox 920×380 */
    histGeom() {
      const n = Math.max(1, this.historyBuckets.length);
      const w = 920, h = 380, padL = 64, padR = 16, padT = 16, padB = 30;
      const chartH = h - padT - padB;
      const bw = (w - padL - padR) / n;
      return { w, h, padL, padR, padT, padB, chartH, n, bw };
    },
    histViewBox() {
      return `0 0 ${this.histGeom.w} ${this.histGeom.h}`;
    },
    histTicks() {
      // Y 轴 5 档网格线(含 0 与最大值), 标签用与柱色无冲突的暗色
      const g = this.histGeom;
      const out = [];
      for (let k = 0; k <= 4; k++) {
        out.push({ y: g.padT + g.chartH * (1 - k / 4), label: k === 0 ? "0" : this.fmtSize((this.historyMax * k) / 4) });
      }
      return out;
    },
    histXTicks() {
      // X 轴标签均匀采样(最多 8 个, 防止柱多时文字重叠)
      const g = this.histGeom;
      const n = this.historyBuckets.length;
      const step = Math.max(1, Math.ceil(n / 8));
      const out = [];
      for (let i = 0; i < n; i += step) {
        out.push({ x: g.padL + i * g.bw + g.bw / 2, label: this.historyBuckets[i].label });
      }
      return out;
    },
    /* 双系列折线点(上传/下载): x = 槽位中心, y 按桶值比例 */
    histSeries() {
      const g = this.histGeom;
      const max = this.historyMax;
      const mk = (key) => this.historyBuckets.map((b, i) => ({
        x: g.padL + i * g.bw + g.bw / 2,
        y: g.padT + g.chartH * (1 - Math.min(1, b[key] / max)),
        v: b[key],
      }));
      return { up: mk("up"), down: mk("down") };
    },
    histPaths() {
      const toPath = (pts) => pts.map((p, i) => `${i ? "L" : "M"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
      return { up: toPath(this.histSeries.up), down: toPath(this.histSeries.down) };
    },
    histAreaUp() {
      return this._histArea("up");
    },
    histAreaDown() {
      return this._histArea("down");
    },
    /* 悬停态(容器级 mousemove 连续追踪, 修复旧逐桶 enter/leave 在桶间空隙的闪烁):
     * crosshair x / 两系列高亮点 / tooltip 定位 */
    histHover() {
      if (this.histHoverIdx < 0 || this.histHoverIdx >= this.historyBuckets.length) return null;
      const g = this.histGeom;
      const i = this.histHoverIdx;
      return {
        bucket: this.historyBuckets[i],
        x: this.histSeries.up[i].x,
        up: this.histSeries.up[i],
        down: this.histSeries.down[i],
        leftPct: (this.histSeries.up[i].x / g.w) * 100,
      };
    },
  },
  created() {
    /* P1-2 窗口化的**非响应式**缓存: 刻意不放进 data —— 容器偏移与签名每轮都会写,
     * 放进 data 会让它参与依赖追踪, 每次写入都额外触发一轮重渲染(白付一次整表 patch)。
     * 窗口重算真正需要的响应式输入只有 _winScrollY / _winViewH / _winResize / _rowH。 */
    this._winTop = { torrent: 0, group: 0, member: 0 };        // 容器顶边相对文档的偏移
    this._winTopSig = { torrent: "", group: "", member: "" };
    this._rowHSig = { torrent: "", group: "", member: "" };    // 行高签名(列集合/窗口宽变化才重量)
    /* 逐行实测高度 {kind:hash -> px}: 行高**本来就不齐** —— 带 H&R 要求的行多渲染一行
     * ("22时00分 / 3天12时"), 实测 3000 种子里 27% 是 65.4px、其余 43.7px。按"等高"算占位
     * 会在几千行上累积成**上百像素**的漂移(滚到底够不着 / 滚动条长度不对), 必须逐行记。 */
    this._rowHs = {};
    this._winMeasured = { torrent: false, group: false, member: false };  // 该 kind 是否量齐
    /* 行间距(px)**实测**缓存: 三个容器的真实 gap 不同(atlas .group-table 6px / prism 5px /
     * 成员容器 .detail 是块级容器 = 0), 硬编码会让占位总高失真(见文件头 BUG-1 注释)。 */
    this._winGap = {};
    this._winRaf = 0;      // 滚动合帧句柄
    this._winListening = false;
  },
  async mounted() {
    /* P1-2: 视口高度 + 页面滚动监听(被动 + rAF 合帧, 滚动本身不做任何布局读取) */
    this._winViewH = window.innerHeight;
    window.addEventListener("scroll", this._onWinScroll, { passive: true });
    window.addEventListener("resize", this._onWinResize);
    this._winListening = true;
    // 点击页面空白处: 关闭右键菜单与列选择器(两者都是临时浮层)
    window.addEventListener("click", () => {
      this.menu.visible = false;
      this.headMenu.visible = false;   // 表头右键菜单(TBL-05)与右键菜单同层
      this.colMenuOpen = false;
      this.filterMenu = "";
      this.filePrio.visible = false;
      this.addCatMenu = false;  // 添加种子对话框内浮层: 点空白处统一收起(触发元素自身已 @click.stop 拦截)
      this.addTagMenu = false;
      this.addPathPop = false;
      // FX-08: 限速浮层无遮罩 -> 点空白视为"放弃本次修改"直接收起(与 Esc 同语义)
      if (this.speedOpen) this.closeSpeedDialog();
    });
    // Esc: 逐层退栈(FIX-07) —— 确认框/弹窗 → 抽屉内浮层/抽屉 → 筛选器下拉/弹层(pop) → 右键菜单 → 清选择/收展开兜底
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (this.modal.visible) this.resolveModal(false);
      else if (this.addOpen) this.escAddTorrent();  // 添加种子对话框: 先收内部浮层(分类/标签下拉 → 位置面板), 再关对话框
      else if (this.statsOpen) this.closeStats();  // 统计面板对话框: 与添加对话框同层(先后于确认框)
      else if (this.speedOpen) this.closeSpeedDialog();  // 限速弹窗(SPD-04): 与统计面板同层
      else if (this.mgrOpen) this.closeMgr();  // 分类/标签管理对话框: 与添加对话框同层(内部确认框仍最优先)
      else if (this.filePrio.visible) this.filePrio.visible = false;  // 文件优先级小菜单: 抽屉内浮层先于抽屉关闭
      else if (this.drawer.open) this.closeDrawer();  // 详情抽屉: 确认框优先, 其后于其它浮层
      else if (this.historyOpen) this.historyOpen = false;  // 历史弹层(pop): 弹层先于右键菜单关闭
      else if (this.headMenu.visible) this.headMenu.visible = false;  // 表头右键菜单(TBL-05)
      else if (this.colMenuOpen) this.colMenuOpen = false;  // 列选择器弹层(pop)
      else if (this.filterMenu) this.filterMenu = "";  // 筛选器下拉(pop)
      else if (this.menu.visible) this.menu.visible = false;  // 右键菜单: pop 层之后
      else if (this.selGroups.length || this.selMembers.length) this.clearSelection();  // 兜底: 清除行/组选择(复用现有逻辑)
      else if (this.expandedKey) this.expandedKey = null;  // 兜底: 收起分组展开
      else if (this.expandedShowEp) this.expandedShowEp = null;  // 兜底: 收起追剧集展开
      else if (this.expandedShows.length) this.expandedShows = [];  // 兜底: 收起追剧剧展开
    });
    // 列宽: 未手动调过时"实体化"为当前渲染 px(见 materializeColumns); 窗口变化后重新实体化,
    // 保持"填满容器 + 自适应"的观感; 手动调过则冻结(拖一列不再影响其它列)
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        this._syncHeadHeight();
        this.materializeColumns();
      }, 120);
    });
    this.$nextTick(() => {
      this._syncHeadHeight();
      this.materializeColumns();
    });
    // 页面可见性(与 qB 自带 WebUI 同策略): 后台标签停止轮询; 恢复可见立即刷新并续排
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.stopPolling();
      else if (this.authOk) this.refresh();  // 登出态切回标签不发空 Bearer; R10-01: 判据 = 鉴权模式
    });
    // 全局右键屏蔽(CTX-03): 除顶部导航栏(header.topbar, atlas/prism 两套 UI 共用类名)与输入类
    // 元素(input/textarea/contenteditable, 保留复制粘贴的原生菜单)外, 一律阻止原生右键菜单;
    // 各处 .ctx-menu 自定义菜单由 Vue @contextmenu.prevent 触发, 与本监听器共存(preventDefault 幂等无害)
    document.addEventListener("contextmenu", (e) => {
      const t = e.target;
      if (t && t.closest && (t.closest("header.topbar") || t.closest("input, textarea, [contenteditable]"))) return;
      e.preventDefault();
    });
    // 本地存储密钥必须重新验证后才放行遮罩; 密钥已轮换则由 401 收口清除。
    // 验证期间显示"验证中"加载态(bootstrapping)而非密钥输入表单 —— 修复刷新时闪现输入界面。
    // 跳过本地验证: 先读公开只读标志, 本机免鉴权则直接进入, 不弹登录表单
    const savedToken = localStorage.getItem("autoqb_token");
    fetch("/api/config/public").then((r) => (r.ok ? r.json() : null)).then((pub) => {
      if (pub && pub.web && pub.web.skip_local_verify) {
        this.authRequired = false;  // 唯一放行点(与 bootstrap 成功后语义一致)
        this.bootstrapping = false;  // FX-01: 本机免鉴权 -> 直接离开"验证中", 不经过密钥表单
        this.authMode = "local";  // R10-01: 身份来源 = 本机免鉴权(不再要求非空密钥串)
        this.token = savedToken || "";  // 有旧密钥仍留着: 关掉开关后无需重新输入
        this.lastRid = null;
        this.startPolling();
        return;
      }
      if (savedToken) {
        this.bootstrapping = true;
        this.bootstrap(savedToken);  // 成功/失败均由 bootstrap 的 finally 落 bootstrapping = false
        return;
      }
      this.bootstrapping = false;  // FX-01: 无本地密钥 -> 才渲染密钥表单
    }).catch(() => {
      // 公开标志读取失败(服务未就绪/网络异常): 退到密钥表单, 不能让加载卡永久占位
      this.bootstrapping = false;
    });
  },
  watch: {
    // 切回辅种页时表格 DOM 是新建的, 需要重新实体化列宽(设置页期间表格不存在)
    page() {
      this.$nextTick(() => {
        this._syncHeadHeight();
        this.materializeColumns();
      });
    },
    // CTX-02: 任一浮层菜单关闭 -> 撤掉触发源强调(浮层可以多种方式关闭: Esc/点空白/执行动作)
    "menu.visible"(v) {
      if (!v) {
        this._clearCtxSource();
        this.subMenu = "";  // FX-15: 一级菜单关闭时子面板一并收起
      }
    },
    "headMenu.visible"(v) {
      if (!v) this._clearCtxSource();
    },
    "filePrio.visible"(v) {
      if (!v) this._clearCtxSource();
    },
  },
  unmounted() {
    // P1-2: 滚动/缩放监听随组件销毁撤掉(否则热重载后句柄堆叠, 滚动一次算 N 次)
    if (this._winListening) {
      window.removeEventListener("scroll", this._onWinScroll);
      window.removeEventListener("resize", this._onWinResize);
      this._winListening = false;
    }
    if (this._winRaf) {
      cancelAnimationFrame(this._winRaf);
      this._winRaf = 0;
    }
    // P1-3: 顶栏尺寸观察器随组件销毁断开(ResizeObserver 不随元素消失自动停)
    if (this._headObs) {
      this._headObs.disconnect();
      this._headObs = null;
    }
    if (this._headRaf) {
      cancelAnimationFrame(this._headRaf);
      this._headRaf = 0;
    }
  },
  updated() {
    // P1-3: 顶栏高度改由 ResizeObserver 驱动 —— **只在尺寸真变时量一次**。
    // 旧实现每次渲染都调 _syncHeadHeight() → getBoundingClientRect 是**强制同步布局**,
    // 在大 DOM(3000 行)下每次渲染都要付一次, 是"不跟手"的直接来源之一。
    // 这里只做"元素换没换"的引用比较(不触发布局), 换了才重新挂观察器并立即量一次。
    this._ensureHeadObserver();
    this._syncColAlignCss();  // 列对齐规则(R10-08): 值未变时内部直接返回
    // P1-2: 行高/容器偏移都只在签名变化时量(见 _measureRowH / _ensureWinTop), 不是每渲染一次
    this._measureRowH();
    this._ensureWinTop();
  },
  methods: {
    async api(path, options = {}) {
      if (!this.authOk) {
        // 无凭证不出网: 否则会发出 "Bearer " 空头(被 HTTP 层裁剪成裸 "Bearer"),
        // 后端白记一次 401。调用方按 401 同路径处理(回密钥输入界面/静默)。
        // R10-01: 判据改为**鉴权模式**而非"密钥串非空" —— 本机免鉴权下 token 为空是合法状态。
        this._logout();
        const noAuth = new Error("unauthorized");
        noAuth.auth = true;
        throw noAuth;
      }
      return this._request(path, options, this.token);
    },
    async _request(path, options, token) {
      // R10-01: **无密钥就不带 Authorization 头**(本机免鉴权模式)。旧实现无条件拼
      // `Bearer ${token}`, token 为空时发出裸 "Bearer", 而后端的免鉴权分支会把它当"未带凭证"
      // 每次请求记一条 WARNING(噪音); 带上真实密钥时后端也是忽略, 两种都不如干脆不发。
      const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
      if (token) headers.Authorization = `Bearer ${token}`;
      const resp = await fetch(path, { ...options, headers });
      if (resp.status === 401) {
        this._logout("密钥无效或已更换");
        const err = new Error("unauthorized");
        err.auth = true;
        throw err;
      }
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${resp.status}`);
      }
      return resp.json();
    },
    _logout(message = "") {
      // 鉴权失败唯一收口: 遮罩、凭证、定时器与所有已加载的受保护数据一并清空——
      // 防错误密钥提交瞬间主界面(含上一会话残留的分组/设置)闪现, 也避免数据滞留内存视图
      this.authRequired = true;
      this.authPending = false;
      this.bootstrapping = false;
      this.pendingToken = "";
      this.token = "";
      localStorage.removeItem("autoqb_token");
      this.stopPolling();
      if (this.searchTimer) clearTimeout(this.searchTimer);  // 登出后停掉搜索防抖/重试, 防空头竞态
      this.searchTimer = null;
      this.groups = [];
      this.status = {};
      this.lastRid = null;
      this.pollFails = 0;
      this.serviceDown = false;
      this.expandedKey = null;
      this.kindFilter = "";
      this.pathFilter = [];
      this.tagFilter = [];
      this.categoryFilter = [];
      this.siteFilter = [];
      this.hrFilter = [];
      this.singles = [];
      this.torrents = [];
      this.shows = { list: [], unrecognized: [] };
      this.expandedShows = [];
      this.expandedShowEp = null;
      this.filterMenu = "";
      this.colMenuOpen = false;
      this.toasts = [];
      this.modal = this._modalInit();
      this._modalResolve = null;
      this.clearSelection();
      this.historyOpen = false;
      this.histHoverIdx = -1;
      this.statsOpen = false;
      this.statsServer = null;
      this.statsError = "";
      this.mgrOpen = "";
      this.mgrBusy = false;
      this.logs = { loading: false, error: "", loaded: false, lines: [], file: "", level: "", num: 300 };
      this.speedMode = { loaded: false, curveEnabled: false, target: null, current: null, error: "" };
      this.speedOverride = { up: "", down: "", busy: false };
      this.speedOpen = false;
      this.speedAt = { left: 0, dir: "up" };
      this.cfgReset();  // 配置树同样是受保护内容, 一并清除(编辑器状态复位)
      this.page = "groups";
      this.searchQuery = "";
      this.resetSearch();
      if (message) {
        this.authError = message;
        this.authErrorKind = "auth";
      }
    },
    /* ---------------------------------------------------------- 站内提示条(toast) */
    toast(text, kind = "info", ms = 4000, opts = {}) {
      const id = ++this._toastSeq;
      this.toasts.push({ id, text, kind });
      // sticky = 常驻不自动消失(强制汇报"等待中"): 由 _finishToast 更新终态后退场
      if (opts.sticky) return id;
      setTimeout(() => this._dropToast(id), ms);
      return id;
    },
    /* 常驻提示条结算: 原位更新文案与样式(kind)后停留 ms 再退场 —— "等待中"->"成功/超时"的强反馈 */
    _finishToast(id, kind, text, ms = 4000) {
      this._updateToast(id, { kind, text });
      setTimeout(() => this._dropToast(id), ms);
    },
    _updateToast(id, patch) {
      const t = this.toasts.find((x) => x.id === id);
      if (t) Object.assign(t, patch);
    },
    _dropToast(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    /* ------------------------------------------- 站内确认/输入框(替代 confirm/prompt) */
    _modalInit() {
      return {
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
        checkbox: "", checked: false,  // 额外选项勾选框(如删除时"同时删除磁盘文件")
        checks: null,   // 多选项 [{key,label,checked}](删除确认框: 强制汇报 + 删除文件并存)
        details: null,  // 目标信息区 [{icon,label,value}](删除确认框显示待删种子信息)
        fields: null,   // 多字段输入 [{key,label,value,placeholder}](编辑类对话框: 限速/分享率/移动/重命名)
        wide: false,    // 加宽形态(删除确认框: 摘要与选项宽松可读; DLG-01 成员明细区已移除)
        icon: "",       // 标题图标覆盖(如删除用 i-trash-x); 缺省按 danger 取 warn/info
      };
    },
    confirmDialog(title, body, opts = {}) {
      // 返回 Promise<boolean>; 取消/遮罩/Esc 均结算为 false(不做任何写操作)
      return this._openModal({
        title, body, input: false,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    /* 带"额外选项勾选框"的确认框: 返回 Promise<{checked:boolean}|null>(取消 = null)
     *
     * 与 confirmDialog 的**布尔契约分开**, 互不影响 —— 删除类操作需要"一个确认动作 + 一个可选附加项"
     * (是否连带磁盘文件), 拆成两个菜单项(保留文件/含文件)反而需要用户先判断自己点的是哪个。
     */
    confirmWithOption(title, body, opts = {}) {
      return this._openModal({
        title, body, checkbox: opts.checkbox || "", checked: !!opts.checked,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    promptDialog(title, value, opts = {}) {
      // 返回 Promise<string|null>; 取消返回 null(与原生 prompt 语义一致)
      return this._openModal({
        title, body: opts.body || "", input: true, value: value || "", placeholder: opts.placeholder || "",
        okText: opts.okText || "确定", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    _openModal(cfg) {
      if (this.modal.visible) this.resolveModal(false);  // 单例: 上一个悬空 Promise 先结算为取消
      return new Promise((resolve) => {
        this._modalResolve = resolve;
        this.modal = { ...this._modalInit(), ...cfg, visible: true };
        this.$nextTick(() => {
          // 多字段形态聚焦第一个输入框(fields), 单输入形态聚焦 modalInput
          const el = (this.modal.fields && this.$refs.modalFields)
            ? this.$refs.modalFields.querySelector("input")
            : this.$refs.modalInput;
          if (el) {
            el.focus();
            el.select();
          }
        });
      });
    },
    resolveModal(ok) {
      if (!this.modal.visible) return;
      const { input, value, checkbox, checked, checks, fields } = this.modal;
      const resolve = this._modalResolve;
      this._modalResolve = null;
      this.modal = this._modalInit();
      if (!resolve) return;
      const hasChecks = !!(checkbox || (checks && checks.length));
      const hasFields = !!(fields && fields.length);
      if (ok) {
        if (input) resolve(value);
        else if (hasFields) {
          // 多字段编辑对话框: 返回 {key: value}(字符串, 调用方自行解析数字/判空)
          const vals = {};
          for (const f of fields) vals[f.key] = String(f.value ?? "").trim();
          resolve(vals);
        } else if (hasChecks) {
          // 勾选类确认返回 {checked, checks:{key:bool}}(向后兼容单 checkbox 的 checked 字段)
          const map = {};
          for (const c of checks || []) map[c.key] = c.checked;
          resolve({ checked, checks: map });
        } else resolve(true);
      } else resolve(input || hasChecks || hasFields ? null : false);
    },
    /* ------------------------------------------- 筛选(状态/路径/标签/分类/站点)与搜索清除 */
    /* 成员值 -> 选项(带计数, 按出现组数降序): 标签/分类/站点三个筛选器共用
     * 计数口径 = "包含该值的组数"(与保存路径筛选一致), 而非成员总数 —— 筛选针对的是组。
     */
    _memberValueOptions(pick) {
      const counts = new Map();
      for (const g of this.groups) {
        const seen = new Set();
        for (const m of g.members) {
          for (const v of pick(m)) {
            if (!seen.has(v)) {
              seen.add(v);
              counts.set(v, (counts.get(v) || 0) + 1);
            }
          }
        }
      }
      return [...counts.entries()]
        .map(([value, count]) => ({ value, count }))
        .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
    },
    toggleFilterValue(field, value) {
      const cur = this[field] || [];
      this[field] = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
      this.expandedKey = null;  // 筛选后组集合变化, 复位展开态
    },
    isFilterOn(field, value) {
      return (this[field] || []).includes(value);
    },
    clearFilter(field) {
      this[field] = [];
      this.expandedKey = null;
    },
    toggleKindFilter(kind) {
      this.kindFilter = this.kindFilter === kind ? "" : kind;
      this.expandedKey = null;  // 筛选后组集合变化, 复位展开态
    },
    /* 筛选弹层互斥展开(同一时刻只开一个: 避免多个浮层叠在一起);
     * 打开时测量锚点位置: 靠右(左对齐会伸出视口)则翻转成右对齐 —— 消除横向滚动条 */
    toggleFilterMenu(kind, ev) {
      if (this.filterMenu === kind) { this.filterMenu = ""; return; }
      this.filterMenu = kind;
      this.popFlip = this._menuOverflowsRight(ev && ev.currentTarget, 260);
    },
    toggleColMenu(ev) {
      this.colMenuAt = null;  // 按钮路径: 清掉右键锚点, 弹层回到 .col-picker 下的常规 CSS 定位
      this.colMenuOpen = !this.colMenuOpen;
      if (this.colMenuOpen) this.colFlip = this._menuOverflowsRight(ev && ev.currentTarget, 300);
    },
    /* 表头右键(TBL-05): 就地打开列选择器弹层(复用 col-menu 与 colHidden 勾选逻辑),
     * fixed 定位锚在右键坐标; 右/下边界自钳制(宽 300 与 .col-menu 一致, 高度按剩余空间截断
     * 由 colMenuStyle 给 maxHeight+滚动), 不走 flip-x(inline left 优先级高于类, 翻转不生效)。
     * page 参数当前仅区分语义(弹层四段全量展示), 留作按视图段落定位的扩展点 */
    openColMenuAt(ev, page) {
      const W = 300, PAD = 8;
      const y = Math.max(PAD, ev.clientY);
      this.colFlip = false;
      this.colMenuAt = {
        x: Math.max(PAD, Math.min(ev.clientX, window.innerWidth - W - PAD)),
        y,
        mh: Math.max(160, window.innerHeight - y - PAD),
      };
      this.colMenuOpen = true;
    },
    /* 弹层内联样式: 仅右键路径给 fixed 坐标与视口内最大高度; 按钮路径返回 null 走原 CSS */
    colMenuStyle() {
      const at = this.colMenuAt;
      if (!at) return null;
      return { position: "fixed", left: at.x + "px", top: at.y + "px", maxHeight: at.mh + "px", overflowY: "auto" };
    },
    /* 锚点左缘 + 弹层宽度是否超出视口(留 8px 边距); ev.currentTarget 在同步代码内有效 */
    _menuOverflowsRight(anchor, menuW) {
      if (!anchor || !anchor.getBoundingClientRect) return false;
      return anchor.getBoundingClientRect().left + menuW > window.innerWidth - 8;
    },
    clearFilters() {
      this.kindFilter = "";
      this.pathFilter = [];
      this.tagFilter = [];
      this.categoryFilter = [];
      this.siteFilter = [];
      this.hrFilter = [];
      this.filterMenu = "";
      this.expandedKey = null;
    },
    clearSearch() {
      if (this.searchTimer) clearTimeout(this.searchTimer);
      this.searchTimer = null;
      this.searchQuery = "";
      this.resetSearch();
    },
    /* 右键菜单定位: 视口边界吸附(菜单尺寸取常量估算, 避免先渲染再测量造成的抖动) */
    _menuPos(event, w = 214, h = 222) {
      const x = Math.min(event.clientX, Math.max(8, window.innerWidth - w - 8));
      const y = Math.min(event.clientY, Math.max(8, window.innerHeight - h - 8));
      return { x: Math.max(8, x), y: Math.max(8, y) };
    },
    async bootstrap(candidate) {
      if (this.authPending) return;  // 防重复提交(验证中按钮已禁用, 双保险)
      this.authPending = true;
      this.authError = "";
      this.authErrorKind = "";
      this.pendingToken = candidate;
      this.lastRid = null;  // 重新鉴权/换密钥: 强制全量取一次分组视图
      try {
        // 用候选密钥直接验证: 成功前 this.token 不提交、authRequired 不解除, 主界面 DOM 绝不渲染
        const state = await this._request("/api/state", {}, candidate);
        this.status = state.status;
        this.groups = state.groups || [];
        this.singles = state.singles || [];
        this.torrents = state.torrents || [];
        this.shows = state.shows || { list: [], unrecognized: [] };
        if (typeof state.rid === "number") this.lastRid = state.rid;
        this.serviceDown = false;
        this.token = candidate;  // 验证通过才提交为当前身份
        this.authMode = "token";  // R10-01: 显式声明身份来源(覆盖可能残留的 local 模式)
        this.authRequired = false;  // 唯一放行点
        localStorage.setItem("autoqb_token", candidate);
        this.pendingToken = "";
        this.tokenInput = "";
        this.startPolling();
      } catch (e) {
        if (!e.auth) {
          // 服务不可达 ≠ 密钥错误: 不否定候选密钥(本地存储亦保留), 给出重试入口, 防误清凭证
          this.authError = "服务不可用, 请确认 auto-qb 程序正在运行";
          this.authErrorKind = "unavailable";
        }
        // e.auth(401/无凭证): _request 已走 _logout() 完成遮罩/数据/文案收口
      } finally {
        this.authPending = false;
        this.bootstrapping = false;  // 验证结束(成功进主界面/失败回表单), 卸载加载态
      }
    },
    saveToken() {
      const candidate = this.tokenInput.trim();
      if (!candidate || this.authPending) return;  // 空提交/验证中拦截: 不触发任何请求与界面切换
      this.bootstrap(candidate);
    },
    retryAuth() {
      // 仅"服务不可达"分支保留候选密钥; 401 已清空, 重试按钮不渲染
      if (this.pendingToken && !this.authPending) this.bootstrap(this.pendingToken);
    },
    startPolling() {
      this.stopPolling();
      this.loadSpeedMode();  // 限速托管状态(非轮询: 登录/重连时取一次, 卡内可手动刷新)
      // 状态栏常显统计(server_state)已随 /api/state.status.server 每轮回传 —— 登录首轮的
      // refresh() 即可填上, 不再需要为"限制速度/连接/剩余"单独补一次 /api/stats(FX-08 旧做法)。
      this.refresh();
    },
    stopPolling() {
      if (this.pollTimer) clearTimeout(this.pollTimer);
      this.pollTimer = null;
    },
    scheduleNext() {
      // 用 setTimeout 链式续排(而非 setInterval): 保证上一轮请求结束后再计时, 不堆叠请求
      this.stopPolling();
      if (document.hidden || !this.authOk) return;  // R10-01: 按鉴权模式判断(本机免鉴权下 token 为空)
      this.pollTimer = setTimeout(() => this.refresh(), this.currentPollMs());
    },
    /* P1 落地后按种子量分档(2026-09-19)。档位是**实测**定的, 不是拍的 —— 用
     * scripts/ui_harness.py + ui_smoke.cjs 的 A/B 量出"窗口化后单轮 refresh 的真实耗时":
     *   1000 种子 143ms | 3000 种子 309ms | 5000 种子 396~501ms
     * 再把每档的**主线程占用率**压到 ~15% 上下(单轮耗时 / 间隔), 于是:
     *   ≤1000 → 1.5s(≈10%)  1000~3000 → 2s(≈15%)  >3000 → 3s(≈17%)
     * 两个边界条件: ①**下界 1.5s = 服务端 sync_interval** —— 后端每 1.5s 才刷一次数据,
     *   再快也只是多拿一次"版本未变"的空响应(此时响应体趋近于零, 但不产生新数据);
     * ②**不是"无变化退避"** —— 那只按 rid 是否变化放慢, 会把行数据新鲜度直接卖掉(见下)。
     */
    basePollMs() {
      const n = this.status && this.status.torrents;
      if (typeof n !== "number") return 2000;  // 总量未知(首轮/异常): 取中间档, 不冒进
      if (n > 3000) return 3000;
      if (n > 1000) return 2000;
      return 1500;  // 与服务端 sync_interval 对齐; 大库才往上让
    },
    currentPollMs() {
      // 失败退避: 连续失败翻倍至上限 15s(减少服务不可达时的空转)
      if (this.pollFails) return Math.min(15000, this.basePollMs() * 2 ** this.pollFails);
      // 恒定间隔(按种子量分档), **不做"无变化退避"**: 曾按"视图版本未变"逐步放慢(2s→5s→10s),
      // 但状态栏的全局速度走 /api/stats(不受 rid 门控, 每轮都刷)⇒ 两个速度来源刷新频率被解耦,
      // 观感上变成"状态栏正常、种子行滞后"。版本未变时响应体已趋近于零(不回传 groups),
      // 退避省不下什么, 却直接牺牲行数据新鲜度 —— 收益与代价不对等, 故只保留失败退避。
      return this.basePollMs();
    },
    async refresh() {
      try {
        // rid 增量: 带上已持有的视图版本, 服务端版本未变时不回传数组(响应体趋近于零)。
        // P1-1: 同时带上当前视图名, 服务端只回该视图需要的数组(响应体 ≈1/4)。
        // 切视图时 goView 会把 lastRid 置空 ⇒ 强制取一次全量, 别的视图不会停在旧数据上。
        const qs = [];
        if (this.lastRid !== null) qs.push(`rid=${this.lastRid}`);
        if (this.viewMode === "torrents") qs.push("view=torrent");
        else if (this.viewMode === "shows") qs.push("view=show");
        else qs.push("view=group");
        const query = qs.length ? `?${qs.join("&")}` : "";
        const state = await this.api("/api/state" + query);
        this.status = state.status;
        // qB 全局状态(server_state)随 status **恒回传**(与 traffic 同口径: 不受 rid 门控) ——
        // 状态栏常显统计与"限制速度"取它, 不再单独打 /api/stats ⇒ 每轮只剩 1 条请求,
        // 且状态栏与行数据**同源同轮**(不再出现"状态栏新鲜 / 种子行滞后"的错位观测)。
        if (state.status && state.status.server !== undefined) this.statsServer = state.status.server || null;
        if (state.updated !== false) {
          // P0-0 埋点: 这段赋值 + 多选交集是"点了没反应"里唯一发生在前端的部分,
          // 超过 50ms 就在控制台留痕 —— 大库下这是 P1(行窗口化)要不要做的直接判据。
          const _t0 = performance.now();
          // 视图有变化: 整表替换并记录新版本; 无变化时保留原数组, 不触发重渲染。
          // P1-1: 服务端只回当前视图的数组 —— **键不存在时必须保留原引用**, 绝不能 `|| []` 清空
          // (否则每次轮询都把另外两个视图抹成空, 切回去要等一轮全量)。
          if (state.groups !== undefined) this.groups = state.groups;
          if (state.singles !== undefined) this.singles = state.singles;  // 未归组种子(搜索兜底/总数回退)
          if (state.torrents !== undefined) this.torrents = state.torrents;  // 种子页平铺数组(SEED_ITEM)
          if (state.shows !== undefined) this.shows = state.shows;  // 追剧视图(R10)
          if (typeof state.rid === "number") this.lastRid = state.rid;
          // 增量替换后按现存 key/hash 交集保留多选(避免轮询把用户选择清空);
          // 虚拟行 key(u-<hash>)不做存在性校验(搜索视图由 filteredGroups 重建)
          if (this.selectedCount) {
            const keys = new Set(this.groups.map((g) => g.key));
            const hashes = new Set(this.groups.flatMap((g) => g.members.map((m) => m.hash)));
            for (const r of this.singles) hashes.add(r.hash);
            for (const r of this.torrents) hashes.add(r.hash);  // 平铺数组 = 全量种子(超集, 覆盖种子页多选)
            this.selGroups = this.selGroups.filter((k) => keys.has(k) || k.startsWith("u-"));
            this.selMembers = this.selMembers.filter((h) => hashes.has(h));
          }
          this.renderMs = Math.round((performance.now() - _t0) * 10) / 10;
          if (this.renderMs > 50) console.warn(`[perf] 单轮视图赋值 ${this.renderMs}ms(>50ms)` +
            ` —— 稳态应远低于此; 首次切视图要全量渲染一帧量行高, 那一帧超属预期(P1-2 已落地)`);
        }
        this.reapplyPending();  // P0-3: 整表替换后把仍 pending 的乐观值重新贴上
        this.serviceDown = false;
        this.pollFails = 0;
      } catch (e) {
        // 服务不可达(程序退出/网络失败): 置 serviceDown 显示横幅; 轮询继续, 服务恢复后自动消失。
        // 401(密钥无效): 停止轮询并回到密钥输入界面(防无谓空转)。
        if (e.auth) {
          this.stopPolling();
          return;
        }
        this.serviceDown = true;
        this.pollFails = Math.min(4, this.pollFails + 1);
      }
      this.scheduleNext();
    },
    onSearchInput(event) {
      // 输入防抖: 停止输入 400ms 后触发搜索; 清空则立即恢复辅种管理视图(不等防抖)
      if (this.searchTimer) clearTimeout(this.searchTimer);
      if (!(event.target.value || "").trim()) {
        this.resetSearch();
        return;
      }
      this.searchTimer = setTimeout(() => this.doSearch(), 400);
    },
    resetSearch() {
      // 清空搜索结果并复位展开态: 搜索结果与普通分组结构不同(含虚拟行), 展开状态不跨视图残留
      this.searchHits = new Set();
      this.searchUncovered = [];
      this.searchBuilding = false;
      this.searchError = "";
      this.expandedKey = null;
    },
    async doSearch() {
      const q = (this.searchQuery || "").trim();
      if (!q) {
        this.resetSearch();
        return;
      }
      try {
        const data = await this.api(`/api/search?q=${encodeURIComponent(q)}`);
        const results = data.results || [];
        this.searchHits = new Set(results.map((r) => r.hash));
        // 实际归组的种子由分组筛选展示; 未归组的命中(分组未启用/文件列表不可读)单独兜底
        const grouped = new Set();
        for (const g of this.groups) for (const m of g.members) grouped.add(m.hash);
        this.searchUncovered = results.filter((r) => !grouped.has(r.hash));
        this.searchBuilding = !!data.building;
        this.searchError = "";
        if (this.searchBuilding) {
          // 文件索引构建中(增量限流可能需多轮): 1s 后自动重查, 直至 building 消除
          if (this.searchTimer) clearTimeout(this.searchTimer);
          this.searchTimer = setTimeout(() => this.doSearch(), 1000);
        }
      } catch (e) {
        // 不再静默(否则与"无匹配结果"无法区分): 401 由 api() 回登录框, 其余在搜索框旁提示
        if (!e.auth) {
          const msg = e.message || "搜索失败";
          this.resetSearch();
          this.searchError = msg;
        }
      }
    },
    fmtSpeed(v) {
      if (!v) return "0 B/s";
      for (const [unit, div] of [["GiB/s", 1073741824], ["MiB/s", 1048576], ["KiB/s", 1024]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B/s";
    },
    fmtSize(v) {
      if (v === null || v === undefined) return "-";
      if (!v) return "0 B";
      for (const [unit, div] of [["PiB", 2 ** 50], ["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B";
    },
    /* 0 值不显示 "0 B/s"/"0 B"(满屏零值噪声): 只留极淡占位符, 列对齐不受影响 */
    fmtSpeedOrDash(v) {
      return v ? this.fmtSpeed(v) : "";  // TBL-01: 主页面表格空值空白(抽屉调用方自行兜回"—")
    },
    fmtSizeOrDash(v) {
      return v ? this.fmtSize(v) : "";  // 同上(TBL-01)
    },
    /* 时间点显示(追剧视图"最近动静"列): 今年省年份, 往年只到日 */
    fmtTime(ts) {
      if (!ts) return "";  // TBL-01: 表格空值空白
      const d = new Date(ts * 1000);
      const p = (n) => String(n).padStart(2, "0");
      if (d.getFullYear() !== new Date().getFullYear()) return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
      return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },
    fmtDuration(sec) {
      // 做种时长: 后端已按分钟取整(torrents._VIEW_QUANTUM), 故不展示秒位
      sec = Math.floor(sec || 0);
      if (sec < 3600) return `${Math.floor(sec / 60)}分钟`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}时${String(Math.floor((sec % 3600) / 60)).padStart(2, "0")}分`;
      return `${Math.floor(sec / 86400)}天${String(Math.floor((sec % 86400) / 3600)).padStart(2, "0")}时`;
    },
    /* ETA(秒): qB 哨兵 8640000 = 无 ETA, 非正数 = 未知/缺失 —— 均显示空白(TBL-01, 种子页 R1A) */
    fmtEta(sec) {
      if (!sec || sec <= 0 || sec >= 8640000) return "";
      return this.fmtDuration(sec);
    },
    /* 时间点(unix 秒): -1/0 = 从未(qB 哨兵) —— 空白(TBL-01); 其余与追剧"最近动静"同格式 */
    fmtTs(ts) {
      if (!ts || ts < 0) return "";
      return this.fmtTime(ts);
    },
    /* 种子限速(qB 原始 bytes/s; 0 = 不限速/跟随全局): 与限速曲线的 KiB/s 口径区分开 */
    fmtLimitBytes(v) {
      if (v === null || v === undefined) return "";  // 缺失: 空白(TBL-01)
      if (!v) return "";  // 0 = 不限速: 不再显示字样(TBL-02)
      return this.fmtSpeed(v);
    },
    /* 做种/用户列(TBL-04): qB 口径 "已连接 (总数)" —— 总数缺失(-1/null)只显示已连接 */
    fmtPeersQb(connected, total) {
      if (connected === null || connected === undefined || connected < 0) return "";
      return total === null || total === undefined || total < 0 ? String(connected) : `${connected} (${total})`;
    },
    /* ---------------- 单元格口径单点化(FX-02/03/04) ----------------
     * 以下三个函数是这三列口径的**唯一来源**: 明细表 / 种子页 / 追剧集明细各自引用它们,
     * 不再把表达式写在模板里(上一版同一口径在模板里各写三份, 改口径必须三处同改, 必漏)。
     * 返回值语义 = 单元格显示文本, 空串即"该状态不显示"; 刻意用空串而非 v-if 摘除节点 ——
     * 单元格仍在 grid 中占位, 列宽与表头不会错位。 */
    cellSeedingTime(m) {
      const t = m.seeding_time || 0;
      // 0 分钟且无 HR 要求 -> 不显示; HR 已触发但尚未开始做种(0 分钟)的种子**必须保留**
      // (那正是最需要被看见的一类), 故隐藏判据带上 HR 条件豁免
      if (t <= 0 && !(m.hr_triggered && m.hr_req_time)) return "";
      return this.fmtDuration(t);
    },
    /* dir = "seeds"(做种/已连接) | "leechs"(用户/下载中) */
    cellPeers(m, dir) {
      if (m.kind === "paused") return "";  // FX-03: 暂停中的种子不显示 用户/做种
      return dir === "seeds"
        ? this.fmtPeersQb(m.num_seeds, m.num_complete)
        : this.fmtPeersQb(m.num_leechs, m.num_incomplete);
    },
    cellRatio(m) {
      if (!m.progress) return "";  // FX-04: 进度为 0(未开始/未下载)的种子不显示分享率
      return (m.ratio || 0).toFixed(2);
    },
    /* 数值色阶(TBL-03): value/denom 比值分两档底色 —— ratio<0.75 → tone-low(偏弱), >=0.75 → tone-high(接近满档);
     * value<=0 或分母缺失/<=0 返回空串(交给 zero/空白机制)。全局限速分母来自 /api/stats 的 statsServer
     * (懒加载, 未开过统计面板时为 null → 速度列自动无色阶, 属预期降级, 规则内自然兜住) */
    numTone(value, denom) {
      if (!value || value <= 0 || !denom || denom <= 0) return "";
      return value / denom < 0.75 ? "tone-low" : "tone-high";
    },
    /* ------------------------------------------- 组级"共同值"计算(组级标签/分类列)
     *
     * 后端只透出成员原始值, 共同值(交集/一致值)在**前端**计算: 这类派生展示数据不参与
     * 后端视图重建判定, 且 computed 缓存后可复用, 无需让后端每轮做集合运算。
     */
    /* 组状态聚合口径(**单点**): 按 STATE_RANK 取"最该被看到"的成员状态 + 计数文案。
     *
     * `decoratedGroups` 与组行乐观补丁共用这一份 —— 两处各写一套必然漂移, 那就会出现
     * "点了暂停, 乐观算出的颜色和真值算出来的不一样"的抖动(见 STATE_RANK 注释)。
     */
    _aggStatus(members) {
      const counts = {};
      for (const m of members || []) counts[m.kind] = (counts[m.kind] || 0) + 1;
      const present = Object.keys(counts).sort((a, b) => this._rank(a) - this._rank(b));
      return {
        primary: present[0] || "other",
        // 计数文案按同一优先级排(与主色同序, 避免"颜色说 A、文案先说 B")
        text: present.map((k) => `${this.kindText(k)} ${counts[k]}`).join(" · "),
      };
    },
    /* kind -> 优先级数值(表里没有的 kind 排最后, 与后端 `_SHOW_STATE_RANK.get(k, 9)` 同口径) */
    _rank(kind) {
      return STATE_RANK[kind] === undefined ? STATE_RANK_LAST : STATE_RANK[kind];
    },
    /* 一组种子按同一张表聚合出的状态(供集行乐观补丁用: 与后端 e.state 同口径) */
    _aggKind(members) {
      let best = null;
      for (const m of members || []) {
        if (!m) continue;
        if (best === null || this._rank(m.kind) < this._rank(best)) best = m.kind;
      }
      return best;
    },
    _commonTags(members) {
      const sets = members.map((m) => new Set(m.tags || []));
      if (!sets.length) return { list: [], diff: false };
      const first = sets[0];
      let common = [...first];
      for (const s of sets.slice(1)) common = common.filter((t) => s.has(t));
      // 与站点名一致的标签(忽略大小写, 多为辅种工具自动打的"站点身份"标签)不展示: 站点列已有同名值, 纯冗余
      common = this._filterSiteTags(common, members);
      common.sort();
      // ± = 成员标签集合不完全相同(组级只显示共同标签, 差异提示避免误读为"全组一致")
      const diff = sets.some((s) => s.size !== first.size || [...s].some((t) => !first.has(t)));
      return { list: common, diff };
    },
    /* 过滤与成员站点名一致(忽略大小写)的标签 —— 组级共同标签与明细行共用 */
    _filterSiteTags(tags, members) {
      const names = new Set((members || []).map((m) => (m.site || "").toLowerCase()).filter(Boolean));
      return (tags || []).filter((t) => !names.has(t.toLowerCase()));
    },
    /* 明细行标签: 先滤掉与站点名一致的标签再展示(折叠计数/悬浮 title 口径一致) */
    mTags(m) {
      return this._filterSiteTags(m.tags, [m]);
    },
    /* 站点配色已改回状态色(2026-09-15, 字体与背景都表示种子状态): 原 siteHue djb2 函数与 .sc-0..7 一起删除, 站点身份由 chip 文字表达 */
    /* 站点专属配色已移除(2026-09-15 用户要求回退): 字体与背景都用状态色, 原 siteHue djb2
     * 哈希机制与 .sc-0..7 一起删除, 站点身份由 chip 文字表达(见 memory-bank/pitfalls.md 回写) */
    _commonCategory(members) {
      const vals = members.map((m) => m.category || "");
      if (!vals.length) return { value: "", diff: false };
      const diff = vals.some((v) => v !== vals[0]);
      return { value: diff ? "" : vals[0], diff };
    },
    kindText(kind) {
      return { seeding: "做种", downloading: "下载", checking: "校验中", paused: "已暂停", error: "错误", other: "其他" }[kind] || kind;
    },
    /* 单种子状态文案: 错误状态优先显示**后端算好的具体原因**(error_reason: "文件丢失" /
     * tracker 报错原文), 其余状态回落 kindText。原因文本一律由后端给出(取数单点), 前端不得
     * 按 state 猜原因。kindText 仍用于状态图例/筛选器/组级与集级聚合文案 —— 那里没有
     * "某一种子的原因"可言。 */
    stateText(m) {
      if (!m || !m.kind) return "";
      if (m.kind === "error" && m.error_reason) return m.error_reason;
      return this.kindText(m.kind);
    },
    kindIcon(kind) {
      // 状态图标(与 sprite symbol 一一对应): 校验中用 i-pulse(配合 CSS 呼吸动画, 语义=进行中)
      return {
        seeding: "#i-upload", downloading: "#i-download", checking: "#i-pulse",
        paused: "#i-pause", error: "#i-warn", other: "#i-info",
      }[kind] || "#i-info";
    },
    tagSlice(list, n) {
      // 标签 chip 最多显示 n 个(其余折叠为 +N), 保持行高与列宽稳定
      return (list || []).slice(0, n);
    },
    /* HR 标签分类色(与后端 qbmanager._hr_view_tags 对应)
     *
     * pending = 已触发 HR 条件但尚未满足做种时长/分享率(需关注, 用最鲜亮的颜色);
     * done    = 已满足(可以放宽, 用另一组镇静的颜色)。判定依据是后端解析后的标签文本
     * (已展开 ${required_seeding_time} 变量), 因此与真正写入 qB 的标签逐字相等。
     * 组级列展示的是"共同标签"——若某标签全组共有, 则组内 HR 状态必然一致, 故用代表成员即可。
     */
    tagClass(tag, member) {
      if (!member) return "";
      if (member.hr_tag && tag === member.hr_tag) return "hr-pending";
      if (member.hr_tag_done && tag === member.hr_tag_done) return "hr-done";
      return "";
    },
    /* ---------------- HR 展示辅助(布尔/阈值均由后端算好, 前端只做比较与着色) ----------------
     * hr_triggered / hr_satisfied: 是否触发 HR / 是否已达成要求
     * hr_req_time: 要求做种时长(秒); hr_req_ratio: 要求分享率(0 = 不要求)
     * 绝不在前端重算模板或阈值(自定义标签格式与要求值会立即失效), 见 ai/08-pitfalls。
     */
    hrTimeReached(m) {
      return m.hr_req_time > 0 && m.seeding_time >= m.hr_req_time;
    },
    hrRatioReached(m) {
      return m.hr_req_ratio > 0 && (m.ratio || 0) >= m.hr_req_ratio;
    },
    /* 对照列配色: **按列各自的要求**判定 —— 未配要求的列(如只要求时长不要求分享率)必须
     * 保持中性色, 否则会给一个"本来就没要求的数值"染上警示色, 反而是误读。
     */
    hrTimeClass(m) {
      if (!m.hr_triggered || !(m.hr_req_time > 0)) return "";
      return this.hrTimeReached(m) ? "reached" : "pending";
    },
    hrRatioClass(m) {
      if (!m.hr_triggered || !(m.hr_req_ratio > 0)) return "";
      return this.hrRatioReached(m) ? "reached" : "pending";
    },
    hrGroupClass(g) {
      if (!g.hr_triggered) return "";
      return g.hr_pending ? "pending" : "done";
    },
    /* H&R 筛选档位(R07): 组级消费组级计数、成员级消费布尔, 标签一致;
     * 只比较后端算好的字段, 前端不重算模板/阈值(pitfalls: HR 判定前后端各写一遍 = 自定义标签立即失效) */
    /* 成员级筛选谓词: 单种子平铺/追剧集行/未识别桶共用同一套条件
     * (状态/路径/标签/分类/站点/H&R; 多选筛选器内为或, 筛选器之间为且) */
    _memberPass(m) {
      if (this.kindFilter && m.kind !== this.kindFilter) return false;
      if (this.pathFilter.length && !this.pathFilter.includes(m.save_path || "")) return false;
      if (this.tagFilter.length && !(m.tags || []).some((t) => this.tagFilter.includes(t))) return false;
      if (this.categoryFilter.length && !this.categoryFilter.includes(m.category || "")) return false;
      if (this.siteFilter.length && !this.siteFilter.includes(m.site)) return false;
      if (this.hrFilter.length && !this.hrFilter.includes(this._hrBucketMember(m))) return false;
      return true;
    },
    _hrBucket(g) {
      if (!g.hr_triggered) return "";
      return g.hr_pending > 0 ? "未达标" : "达标";
    },
    _hrBucketMember(m) {
      if (!m.hr_triggered) return "";
      return m.hr_satisfied ? "达标" : "未达标";
    },
    /* 种子页客户端文本过滤(R1A): 名称/站点/分类/标签/保存路径任一命中即保留(不区分大小写) */
    _torrentTextMatch(m, q) {
      return (m.name || "").toLowerCase().includes(q)
        || (m.site || "").toLowerCase().includes(q)
        || (m.category || "").toLowerCase().includes(q)
        || (m.save_path || "").toLowerCase().includes(q)
        || (m.tags || []).some((t) => t.toLowerCase().includes(q));
    },
    hrGroupTitle(g) {
      if (!g.hr_triggered) return `该${L10N_GROUP}没有成员触发 HR 条件`;
      if (!g.hr_pending) return `已触发 HR 的 ${g.hr_triggered} 个成员均已满足做种时长/分享率要求`;
      return `已触发 HR ${g.hr_triggered} 个, 其中 ${g.hr_pending} 个尚未满足做种时长/分享率要求`;
    },
    /* 限速显示: 后端单位 KiB/s(0 = 不限速, null = 该方向不管理) */
    fmtLimit(kib) {
      if (kib === null || kib === undefined) return "—";
      if (!kib) return "";  // 0 = 不限速: 不再显示字样(TBL-02); 提示/toast 文案处调用方用 || "不限速" 兜回
      return this.fmtSpeed(kib * 1024);
    },
    setSort(key, scope) {
      // 三态(想法.md): 首次点击按该列降序 -> 再点升序 -> 第三次恢复默认排序(最近添加时间降序);
      // 单种子/追剧视图操作独立排序键, 各视图互不干扰; scope="detail" 走展开明细表自己的键
      const { gk, gd } = this._sortKeys(scope);
      if (this[gk] !== key) {
        this[gk] = key;
        this[gd] = -1;
        return;
      }
      if (this[gd] === -1) {
        this[gd] = 1;
        return;
      }
      this._resetSort(scope);
    },
    /* 当前视图的排序键/方向(data 属性名) —— 分组/种子/追剧三视图各自独立;
     * scope="detail" = 展开明细表(与视图正交: 三视图的明细共用同一套排序键) */
    _sortKeys(scope) {
      if (scope === "detail") return { gk: "detailSortKey", gd: "detailSortDir" };
      if (this.viewMode === "torrents") return { gk: "torrentSortKey", gd: "torrentSortDir" };
      if (this.viewMode === "shows") return { gk: "showSortKey", gd: "showSortDir" };
      return { gk: "sortKey", gd: "sortDir" };
    },
    /* 恢复默认排序: 追剧视图 = 最近动静降序(后端同序); 明细表 = 后端原序(成员扫描顺序);
     * 其余 = 最近添加降序 */
    _resetSort(scope) {
      const { gk, gd } = this._sortKeys(scope);
      if (scope === "detail") {
        this[gk] = "";
        this[gd] = -1;
        return;
      }
      this[gk] = this.viewMode === "shows" ? "latest" : DEFAULT_SORT.key;
      this[gd] = DEFAULT_SORT.dir;
    },
    /* 明细表行序(展开的组明细 / 追剧集明细共用): 空键 = 后端原序, 点击列头后按该列三态排序;
     * 同值时按站点名稳定排序(与分组表"同值按名称"同思路, 避免刷新抖动)。
     * 数组字段(标签)先归并成字符串再比 —— 否则相减得到 NaN, 比较器语义失义。 */
    sortedMembers(list) {
      const key = this.detailSortKey;
      if (!key || !list) return list || [];
      const dir = this.detailSortDir;
      const val = (m) => {
        const v = m[key];
        return Array.isArray(v) ? v.join(",") : v;
      };
      return [...list].sort((a, b) => {
        const va = val(a);
        const vb = val(b);
        let r;
        if (typeof va === "string") r = (va || "").localeCompare(vb || "");
        else r = (va || 0) - (vb || 0);
        if (r === 0) r = (a.site || "").localeCompare(b.site || "");
        return dir * r;
      });
    },
    /* ---------------- 表头右键菜单(TBL-05): 按列操作 ----------------
     * 用户明确该菜单指的是"隐藏xxx"(隐藏**这一列**), 而不是笼统的列选择器;
     * 排序项直接从表头一键指定方向(与表头左键的三态循环互补)。
     */
    openHeadMenu(event, page, col) {
      event.preventDefault();
      this._markCtxSource(event);
      const pos = this._menuPos(event);
      this.headMenu = {
        visible: true,
        x: pos.x,
        y: pos.y,
        page,
        key: col.key,
        label: col.label,
        sortable: !!col.sortable,
        locked: !!col.locked,
      };
    },
    headMenuHide() {
      const m = this.headMenu;
      this.headMenu.visible = false;
      if (!m.page || !m.key) return;
      if (m.locked) {
        this.toast(`「${m.label}」是必显列(承载展开/标识), 不可隐藏`, "info");
        return;
      }
      this.toggleColumn(m.page, m.key);
      this.toast(`已隐藏「${m.label}」列(右键表头或"列"按钮可恢复)`);
    },
    headMenuSort(dir) {
      const m = this.headMenu;
      this.headMenu.visible = false;
      if (!m.sortable) return;
      // 明细表头右键的排序项也走明细表自己的键(m.page 已是列所属的表名)
      const { gk, gd } = this._sortKeys(m.page === "detail" ? "detail" : undefined);
      this[gk] = m.key;
      this[gd] = dir;
    },
    headMenuPicker() {
      const m = this.headMenu;
      this.headMenu.visible = false;
      // 在右键处就地展开完整列选择器(复用 openColMenuAt 的视口钳位)
      this.openColMenuAt({ clientX: m.x, clientY: m.y }, m.page);
    },
    /* 排序箭头已图标化(i-arrow-up/down sprite), 直接在模板按 sortKey/sortDir 渲染 */
    /* 分组表横向滚动时同步表头位移(表头已脱离 .group-table 容器做纵向 sticky,
       横向滚动靠 JS 桥接避免列头与列体错位)。用 transform 而非 scrollLeft,
       避免反向触发自身 scroll 事件形成回环; 不带 transition 跟手不滞后 */
    syncGroupHeadScroll(ev) {
      const head = this.$refs.groupHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    toggleExpand(key, event) {
      // 仅左键触发展开: 右键菜单不应连带展开明细(旧实现在 openMenu 里主动展开, 已移除)
      if (event && event.button !== 0) return;
      const next = this.expandedKey === key ? null : key;
      this.expandedKey = next;
      // 展开的组作为 Shift 多选默认起点(用户要求); 收起不改锚点(保留上一次起点)
      if (next) this.selAnchorGroup = next;
      this.menu.visible = false;
    },
    /* ---------------- CTX-02 触发源强调 ----------------
     * 右键菜单弹出期间把"是在操作谁"标出来(被点的行/按钮挂 .ctx-src)。
     * 用 DOM 标记而不是状态字段: 触发点分布在 组行/种子行/整集行/文件优先级单元格 以及
     * 若干按钮, 逐个加模板绑定既啰嗦又容易漏; 直接标记事件目标所在的行, 双 UI 模板零改动即生效。
     * 清理走 watch(menu.visible/filePrio.visible), 覆盖 Esc/点空白/执行动作全部关闭路径。
     */
    _markCtxSource(event) {
      this._clearCtxSource();
      const t = event && event.target;
      if (!t || typeof t.closest !== "function") return;
      const el = t.closest(".group-row, .member-row, .ep-row, .show-row, .tb-row, .ctx-anchor") || t;
      if (el && el.classList) el.classList.add("ctx-src");
    },
    _clearCtxSource() {
      document.querySelectorAll(".ctx-src").forEach((el) => el.classList.remove("ctx-src"));
    },
    openMenu(event, group) {
      event.preventDefault();
      this._markCtxSource(event);
      if (group.virtual) {
        // 虚拟行(未归组命中种子): 无真实组 key(组级路由会解析失败), 退化为该种子的单种子菜单
        this.openMemberMenu(event, group.members[0]);
        return;
      }
      // 仅弹菜单, **不展开明细**(用户需要看明细时自己左键点行)
      this.menu = { visible: true, ...this._menuPos(event), key: group.key, hash: null };
    },
    openMemberMenu(event, member) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      this.menu = { visible: true, ...this._menuPos(event), key: null, hash: member.hash };
    },
    /* ---------------- FX-15 次级菜单(flyout) ----------------
     * 入口按"PT 日常高频"与"qB 通用能力"分层: 一级只放高频动作, 队列/TMM/超级做种/
     * 强制开始/分享率限制/复制族 一律进次级菜单(原则已写入 memory-bank conventions.md)。
     * hover 与点击都能展开(键盘走 Enter/Space); 子面板按父项右缘判定是否需要向左翻。
     */
    openSub(name, ev) {
      this.subMenu = name;
      this.subFlip = this._menuOverflowsRight(ev && ev.currentTarget, 200);
    },
    toggleSub(name, ev) {
      if (this.subMenu === name) {
        this.subMenu = "";
        return;
      }
      this.openSub(name, ev);
    },
    /* FX-14: 打开目标文件夹 —— 路径由**服务端**从自己的快照派生(web.py /api/open-path),
     * 前端只传 kind + 标识: 后端绝不接受客户端传路径(防"任意文件执行"), 且只允许目录/单文件种子的文件。
     * R10-10: 单文件种子返回 `select: true`(打开所在目录并**定位选中**该文件) —— 文案随之区分,
     * 否则用户会以为"只是打开了文件夹"。 */
    async openTargetPath(kind, id) {
      this.menu.visible = false;
      if (!id) return;
      try {
        const r = await this.api("/api/open-path", {
          method: "POST",
          body: JSON.stringify(kind === "group" ? { kind: "group", key: id } : { kind: "torrent", hash: id }),
        });
        const how = r.select ? "已在文件夹中选中该文件" : "已打开目标文件夹";
        this.toast(`${how}: ${r.opened}`, "ok", 3000);
      } catch (e) {
        if (!e.auth) this.toast("打开目标文件夹失败: " + e.message, "error", 8000);
      }
    },
    // 命令 => 中文动作名(用于投递成功/失败的提示文案)
    _actionText(action) {
      return { pause: "暂停", resume: "开始", reannounce: "强制汇报", delete: "删除" }[action] || action;
    },
    /* ---------------- P0-3 埋点(点击侧): 「点击 → 补丁」/「点击 → POST 返回」 ----------------
     * 原先 cmdStats 只量**回执段**(wait_ms / exec_ms / 端到端), 「点击 → 命令投递」这一段
     * 既没打点也没超时, 是**盲区**: 真机上 POST 慢到秒级时, 前端日志全绿、只有用户肉眼能看见
     * "点了 2-4s 才有反应"(issue 26-09-19-1939-webui-optimistic-latency 就是这么报上来的)。
     * 埋点没有消费者就是死字段 —— 这两段一并写进 cmdStats, 由 waitCmd 的 [perf] 统一消费。 */
    _newCmdStats(action) {
      this.cmdStats = {
        action: action || null,
        patchMs: null,  // 点击 -> 乐观补丁贴上(补丁先于 POST, 正常 ~0ms)
        postMs: null,   // 点击 -> 命令 POST 返回(真机大库可能秒级 —— 本埋点要的就是它)
        totalMs: null,
        waitMs: null,
        execMs: null,
        cmdId: null,
      };
      return performance.now();
    },
    _markCmdPatch(t0) {
      if (this.cmdStats && t0) this.cmdStats.patchMs = Math.round(performance.now() - t0);
    },
    _markCmdPost(t0) {
      if (this.cmdStats && t0) this.cmdStats.postMs = Math.round(performance.now() - t0);
    },
    /* ---------------- 命令回执(轮询 /api/cmd/{id}): 主循环执行完/确认完才出结果 ----------------
     * pause/resume 等命令几乎即时; reannounce 的回执由后端 tracker 确认跟踪器在
     * "status 变 working / next_announce 被重置"或超时后写入(窗口 30s, 前端多留余量)。
     */
    async waitCmd(cmdId, timeoutMs = 40000, opts = {}) {
      /* 首查后退避(原实现第一查也要先睡 500ms —— 快命令平白多 500ms):
       * 快命令曲线 0 → 150 → 300 → 500 封顶; reannounce 走宽松曲线 500 → 1000 封顶
       * (tracker 确认本来就要几秒, 密轮询只增请求数不减延迟)。
       * 多发的请求只落在"命令在途"的极短窗口内, 空闲时没有任何额外轮询。
       * P0-0 埋点: 后端回执带 wait_ms/exec_ms 时记入 this.cmdStats, 并在超阈值时打一条
       * [perf](见下方 —— 埋点没有消费者就是死字段)。 */
      const start = Date.now();
      const firstMs = opts.firstMs || 0;
      const capMs = opts.capMs || 500;
      let delay = firstMs;
      while (Date.now() - start < timeoutMs) {
        if (delay > 0) await new Promise((r) => setTimeout(r, delay));
        try {
          const r = await this.api(`/api/cmd/${cmdId}`);
          if (r.status === "ok" || r.status === "error") {
            if (typeof r.wait_ms === "number") {
              // 合并而非替换: 点击侧的两段(_newCmdStats 写入)不能在这里被冲掉
              this.cmdStats = {
                ...(this.cmdStats || {}),
                totalMs: Date.now() - start,
                waitMs: r.wait_ms,
                execMs: r.exec_ms,
                cmdId,
              };
              /* 埋点必须有消费者, 否则就是死字段(2026-09-19 复核: 此前 cmdStats 只写不读,
               * 计划里那张"走查表"从未产出)。超阈值时打一条 [perf] —— 冒烟脚本会收集并打印。
               * patchMs 大 = 补丁没做到"点击即变"(被同步工作或 POST 挡住); postMs 大 = 命令投递慢
               * (真机大库长 tick / GIL 争用); waitMs 大 = 命令没被及时消费(P0-1 唤醒退化);
               * totalMs 大 = 轮询曲线或网络慢。 */
              const c = this.cmdStats;
              if (c.waitMs > 100 || c.totalMs > 400 || (c.postMs || 0) > 400 || (c.patchMs || 0) > 50) {
                console.warn(
                  `[perf] 命令 ${cmdId}${c.action ? "(" + c.action + ")" : ""}: 补丁 ${c.patchMs}ms` +
                  ` / POST ${c.postMs}ms / 排队 ${c.waitMs}ms / 执行 ${c.execMs}ms` +
                  ` / 端到端 ${c.totalMs}ms(补丁>50 或 POST>400 或 排队>100 或 端到端>400 属异常)`
                );
              }
            }
            return r.status === "ok" ? { ok: true } : { ok: false, error: r.error || "执行失败" };
          }
        } catch (e) {
          if (e.auth) throw e;  // 401 由统一收口处理(回登录)
          // 网络抖动: 继续轮询(服务恢复后回执仍可取到)
        }
        delay = delay === 0 ? 150 : Math.min(capMs, delay * 2);
      }
      return { ok: false, error: `执行等待超时(${Math.round(timeoutMs / 1000)}s), 结果以程序日志为准` };
    },
    /* ---------------- P0-3 乐观 UI: 点击即变 ----------------
     * 只对"结果可预测"的动作做乐观(白名单: pause/resume); 强制汇报/重新校验/添加种子这类
     * "结果在远端"的动作不做, 由"等待中"常驻 toast 承担。
     * pending 行的乐观字段每轮 refresh 后被重新贴上(整表替换会盖掉), 直到服务端数据与预期
     * 一致或 3s 超时 —— 避免"先变过去、下一轮又弹回来"的抖动; 回执 error 立即回滚原值,
     * 绝不留假状态(断网/qB 未启动时必须能看到失败)。 */
    isPending(hash) {
      const op = this.pendingOps[hash];
      if (!op) return false;
      if (Date.now() - op.ts > 3000) {
        delete this.pendingOps[hash];  // 超时回落真值: 不再贴补丁, 下轮以服务端为准
        return false;
      }
      return true;
    },
    _optimisticPatch(action, row) {
      if (action === "pause") return { kind: "paused" };
      if (action === "resume") return { kind: row && row.progress >= 1 ? "seeding" : "downloading" };
      return null;  // 不在白名单 -> 不做乐观
    },
    _forEachRow(hash, fn) {
      for (const r of this.torrents || []) if (r.hash === hash) fn(r);
      for (const r of this.singles || []) if (r.hash === hash) fn(r);
      for (const g of this.groups || []) for (const m of g.members || []) if (m.hash === hash) fn(m);
    },
    applyOptimistic(hashes, action) {
      const now = Date.now();
      for (const h of hashes || []) {
        if (!h) continue;
        this._forEachRow(h, (row) => {
          const patch = this._optimisticPatch(action, row);
          if (!patch) return;
          const prev = {};
          for (const k of Object.keys(patch)) prev[k] = row[k];
          Object.assign(row, patch);
          this.pendingOps[h] = { patch, prev, ts: now, action };
        });
      }
    },
    resolveOptimistic(hashes, ok) {
      for (const h of hashes || []) {
        const op = this.pendingOps[h];
        if (!op) continue;
        if (ok) {
          /* 成功: 保留到服务端数据一致或 3s 超时(见 isPending)。
           * ❗3s 兜底**从回执到达重算**, 不再从点击算起: 补丁已提前到 POST 之前, 若仍按点击
           * 起算, 慢 POST(真机 2-4s)会把整个兜底窗口在命令刚完成时就烧光 ⇒ 立刻弹回陈旧真值、
           * 再等下一轮轮询才对上(抖动比单纯慢更难看)。**无回执(hang)时不重置** —— 3s 后照旧
           * 回落真值, "失败/未知绝不留永久假状态"这条不变。 */
          op.ts = Date.now();
          continue;
        }
        this._forEachRow(h, (row) => Object.assign(row, op.prev));  // 失败: 回滚
        delete this.pendingOps[h];
      }
    },
    reapplyPending() {
      // 每轮 refresh 整表替换会盖掉乐观值, 这里把仍 pending 的补丁重新贴上
      for (const h of Object.keys(this.pendingOps)) {
        if (!this.isPending(h)) continue;  // 顺带清掉已超时的
        this._forEachRow(h, (row) => Object.assign(row, this.pendingOps[h].patch));
      }
    },
    /* 组行是否有成员在飞(模板绑 is-pending)。**组行的颜色本身不需要额外补丁** ——
     * 组行状态色取自 decoratedGroups 的 status.primary, 而它是 _aggStatus(成员 kind) 算出来的
     * computed, 成员 kind 被 applyOptimistic 改过之后会自动重算(2026-09-19 实测:
     * 整组暂停后组行 class 由 s-checking 变 s-paused)。缺的只是"在飞"这个视觉标记。 */
    isGroupPending(g) {
      if (!this.pendingAny) return false;   // 常见路径 O(1)
      return (g.members || []).some((m) => this.isPending(m.hash));
    },
    /* 集行是否有成员在飞(同 isGroupPending, 但集的成员是 memberByHash 的**拷贝**)。
     * 取 hash 走 memberHashesOf(项目约定: 集成员在前端已是对象, 直接取 .hash 会被静态守阵拦下 ——
     * 那个守阵防的是"把对象当 hash 发给后端", 这里虽是本地查表, 但统一走归一函数没有代价)。 */
    isEpPending(e) {
      if (!this.pendingAny) return false;
      return this.memberHashesOf(e.members).some((h) => this.isPending(h));
    },
    /* 集行状态色。真值 `e.state` 是后端按 _SHOW_STATE_RANK 聚合后**当标量拷贝**进来的 ——
     * decoratedShows 每轮重建 {...e}, 但 e.state 只在下一次 /api/state 回包时才更新,
     * 所以成员 kind 被乐观补丁改掉后集行颜色不动(BUG-3: 整集暂停后仍是 s-seeding)。
     * 有成员在飞时按**同一张 STATE_RANK 表**现算; 没有在飞时一律用后端真值 ——
     * 不碰"筛选后成员子集"与后端全量成员口径不一致的语义(那是另一件事)。 */
    epState(e) {
      if (!this.isEpPending(e)) return e.state;
      return this._aggKind(e.members) || e.state;
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      /* P0-3「点击即变」: 补丁必须**先于** POST 贴上(与 actEpisode / bulk 同一顺序)。
       * 放在 await 之后 = 把即时反馈押在网络往返上 —— 真机大库下 POST 可达秒级, 用户看到的就是
       * "点了 2-4s 才变"(issue 26-09-19-1939-webui-optimistic-latency; 受控测量: 注入 2000ms
       * POST 延迟时补丁 2012ms 才贴, 改顺序后恒 ~0ms)。reannounce 结果在远端, 不做乐观。 */
      const g = isRe ? null : this._findGroup(this.menu.key);
      const hashes = isRe ? [] : (g && g.members ? g.members : []).map((m) => m.hash);
      const t0 = isRe ? 0 : this._newCmdStats(action);
      if (!isRe) {
        this.applyOptimistic(hashes, action);
        this._markCmdPatch(t0);
      }
      try {
        const resp = await this.api(`/api/groups/${this.menu.key}/${action}`, { method: "POST" });
        if (isRe) {
          // 强反馈状态机: 常驻"等待中" -> 原位换成 成功(绿) / 超时失败(琥珀), 不再用红色警告样式
          const tid = this.toast("强制汇报等待中…(已投递, tracker 确认最长 30s)", "busy", 0, { sticky: true });
          const r = await this.waitCmd(resp.cmd_id, 40000, { firstMs: 500, capMs: 1000 });
          if (r.ok) this._finishToast(tid, "ok", "强制汇报成功(tracker 已确认)", 3000);
          else this._finishToast(tid, "timeout", `强制汇报超时失败: ${r.error}`, 6000);
        } else {
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          if (r.ok) this.toast(`已执行: ${label}整组`, "ok", 2500);
          else this.toast(`${label}整组失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!isRe) this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* ---------------- 添加种子对话框(R1B): multipart 提交不走 this.api()(它强制 application/json 会破坏 multipart boundary),
     * 用原生 fetch + Bearer(this.token); 回执仍复用 waitCmd 轮询 /api/cmd/{id} ---------------- */
    openAddTorrent() {
      this.addFiles = [];
      this.addUrls = "";
      this.addShowUrls = false;  // DLG-03: 链接输入框默认收起
      this.addSavePath = "";
      this.addCategory = "";
      this.addTags = "";
      this.addStart = false;  // 默认不勾 = paused 添加
      this.addSkipCheck = false;
      this.addSequential = false;
      this.addFirstLast = false;
      this.addTmm = false;
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addCatHi = -1;
      this.addTagHi = -1;
      this.addPathPop = false;
      this.addPathHi = -1;
      this.addOpen = true;
      this.loadAddOptions();  // DLG-03/04: 异步拉取分类/标签/历史路径候选, 不阻塞窗口打开
    },
    closeAddTorrent() {
      if (this.addSubmitting) return;  // 回执等待期不允许误关
      this.addOpen = false;
      this.dirBrowse.open = false;  // R10-11: 目录浏览器是添加窗口的子层, 一并关闭
    },
    async loadAddOptions() {
      // DLG-03/04: 并行拉取分类/标签/历史路径候选; 单个端点失败静默降级为空候选(不阻塞窗口)
      const safe = async (url, pick) => {
        try {
          return pick(await this.api(url));
        } catch (e) {
          return [];
        }
      };
      const [cats, tags, paths] = await Promise.all([
        safe("/api/categories", (r) => Object.keys(r.categories || {}).sort((a, b) => a.localeCompare(b))),
        safe("/api/tags", (r) => (r.tags || []).slice().sort((a, b) => a.localeCompare(b))),
        safe("/api/paths", (r) => r.paths || []),
      ]);
      if (this.addOpen) {  // 仅窗口仍开着时回填(慢响应不得污染下一次打开)
        this.addCatOptions = cats;
        this.addTagOptions = tags;
        this.addPathOptions = paths;
      }
    },
    escAddTorrent() {
      // Esc 逐层退栈(FIX-07)接入: 对话框内浮层(目录浏览器 → 分类/标签下拉 → 位置面板)先收起, 再关对话框
      if (this.dirBrowse.open) {
        this.closeDirBrowse();
      } else if (this.addCatMenu || this.addTagMenu) {
        this.addCatMenu = false;
        this.addTagMenu = false;
        this.addCatHi = -1;
        this.addTagHi = -1;
      } else if (this.addPathPop) {
        this.addPathPop = false;
        this.addPathHi = -1;
      } else {
        this.closeAddTorrent();
      }
    },
    toggleAddUrls() {
      this.addShowUrls = !this.addShowUrls;  // 收起不清空已输入链接, 再展开仍可继续编辑
    },
    openAddCatMenu() {
      this.addTagMenu = false;
      this.addCatHi = -1;
      this.addCatMenu = true;
    },
    openAddTagMenu() {
      this.addCatMenu = false;
      this.addTagHi = -1;
      this.addTagMenu = true;
    },
    addCatFiltered() {
      const q = this.addCategory.trim().toLowerCase();
      if (!q) return this.addCatOptions;
      return this.addCatOptions.filter((c) => c.toLowerCase().includes(q));
    },
    addTagCurrent() {
      const m = this.addTags.match(/([^,]*)$/);  // 从简: 只按最后一个逗号后的片段过滤
      return (m ? m[1] : "").trim();
    },
    addTagFiltered() {
      const q = this.addTagCurrent().toLowerCase();
      const picked = new Set(this.addTags.split(",").map((t) => t.trim()).filter(Boolean));
      return this.addTagOptions.filter((t) => !picked.has(t) && (!q || t.toLowerCase().includes(q)));
    },
    pickAddCat(name) {
      this.addCategory = name;
      this.addCatMenu = false;
      this.addCatHi = -1;
    },
    pickAddTag(tag) {
      const parts = this.addTags.split(",").map((t) => t.trim()).filter(Boolean);
      if (!parts.includes(tag)) parts.push(tag);
      this.addTags = parts.join(", ") + ", ";  // 尾随逗号: 便于继续挑选下一个
      this.addTagMenu = false;
      this.addTagHi = -1;
    },
    onAddCatKeydown(e) {
      this._comboKeydown(e, "cat");
    },
    onAddTagKeydown(e) {
      this._comboKeydown(e, "tag");
    },
    _comboKeydown(e, kind) {
      // 分类/标签 combobox 共用键盘导航: 上下循环高亮, 回车选中, Esc 只收下拉(阻断冒泡, 不关对话框)
      const opts = kind === "cat" ? this.addCatFiltered() : this.addTagFiltered();
      const menuKey = kind === "cat" ? "addCatMenu" : "addTagMenu";
      const hiKey = kind === "cat" ? "addCatHi" : "addTagHi";
      const listRef = kind === "cat" ? "addCatList" : "addTagList";
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && opts.length) {
        e.preventDefault();
        if (!this[menuKey]) {
          this[menuKey] = true;
          this[hiKey] = e.key === "ArrowDown" ? -1 : 0;
        }
        this[hiKey] = (this[hiKey] + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
        this._hiScroll(listRef);
      } else if (e.key === "Enter" && this[menuKey] && this[hiKey] >= 0 && opts[this[hiKey]]) {
        e.preventDefault();
        if (kind === "cat") this.pickAddCat(opts[this[hiKey]]);
        else this.pickAddTag(opts[this[hiKey]]);
      } else if (e.key === "Escape" && this[menuKey]) {
        e.stopPropagation();
        this[menuKey] = false;
        this[hiKey] = -1;
      }
    },
    /* ---------------- R10-11 路径选择器(服务端目录浏览) ----------------
     * “选择位置”不再只是自绘下拉: 由服务端给真实目录树(浏览器物理上拿不到绝对路径)。
     * 只列目录 + 可上溯到允许根 + 可新建文件夹; 选中后回填输入框(绝对路径)。
     * 安全边界全部在后端(GET /api/fs/dirs, POST /api/fs/mkdir)。 */
    async openDirBrowse() {
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addPathPop = false;
      this.dirBrowse = {
        open: true, path: "", parent: "", roots: [], dirs: [],
        loading: true, error: "", newName: "", busy: false,
      };
      await this.loadDir("");
    },
    closeDirBrowse() {
      this.dirBrowse.open = false;
    },
    async loadDir(path) {
      this.dirBrowse.loading = true;
      this.dirBrowse.error = "";
      try {
        const r = await this.api("/api/fs/dirs?path=" + encodeURIComponent(path || ""));
        this.dirBrowse.path = r.path || "";
        this.dirBrowse.parent = r.parent || "";
        this.dirBrowse.roots = r.roots || [];
        this.dirBrowse.dirs = r.dirs || [];
      } catch (e) {
        if (!e.auth) this.dirBrowse.error = e.message || "读取目录失败";
      } finally {
        this.dirBrowse.loading = false;
      }
    },
    dirEnter(p) {
      this.loadDir(p);
    },
    dirUp() {
      if (this.dirBrowse.parent) this.loadDir(this.dirBrowse.parent);
    },
    async dirMkdir() {
      const name = (this.dirBrowse.newName || "").trim();
      if (!name || this.dirBrowse.busy) return;
      this.dirBrowse.busy = true;
      try {
        const r = await this.api("/api/fs/mkdir", {
          method: "POST",
          body: JSON.stringify({ path: this.dirBrowse.path, name }),
        });
        this.dirBrowse.newName = "";
        await this.loadDir(r.path || this.dirBrowse.path);
        this.toast(`已新建文件夹: ${r.created}`, "ok", 3000);
      } catch (e) {
        if (!e.auth) this.toast("新建文件夹失败: " + e.message, "error", 8000);
      } finally {
        this.dirBrowse.busy = false;
      }
    },
    /* 选定当前目录(首层/未进入具体目录时落到首个允许根) */
    dirPick() {
      const p = this.dirBrowse.path || (this.dirBrowse.dirs[0] && this.dirBrowse.dirs[0].path) || "";
      if (!p) {
        this.toast("请先选择一个目录", "warn");
        return;
      }
      this.addSavePath = p;
      this.dirBrowse.open = false;
    },
    /* FX-17: 输入框聚焦即展开候选面板。旧实现写在模板上的 @focus 是 `addPathPop = false`
     * —— 聚焦反而把面板关掉(为让位于原生 datalist 的建议浮层), 而那个浮层会自行超时消失,
     * 于是表现为"下拉 2 秒后不见了"。datalist 退役后聚焦 = 展开。 */
    openAddPathPop() {
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addPathHi = this.addPathOptions.indexOf(this.addSavePath.trim());
      this.addPathPop = true;
      this._hiScroll("addPathList");
    },
    pickAddPath(p) {
      this.addSavePath = p;  // 单选回填(覆盖自由输入框内容)
      this.addPathPop = false;
      this.addPathHi = -1;
    },
    onAddPathKeydown(e) {
      // 面板未开时不接管按键(按钮默认行为); 开启后: 上下移动高亮, 回车回填, Esc 只收面板(阻断冒泡不关对话框)
      if (!this.addPathPop) return;
      const n = this.addPathOptions.length;
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && n) {
        e.preventDefault();
        if (this.addPathHi < 0) this.addPathHi = e.key === "ArrowDown" ? -1 : 0;
        this.addPathHi = (this.addPathHi + (e.key === "ArrowDown" ? 1 : -1) + n) % n;
        this._hiScroll("addPathList");
      } else if (e.key === "Enter") {
        e.preventDefault();
        const p = this.addPathOptions[this.addPathHi];
        if (p) this.pickAddPath(p);
      } else if (e.key === "Escape") {
        e.stopPropagation();
        this.addPathPop = false;
        this.addPathHi = -1;
      }
    },
    _hiScroll(refName) {
      // 键盘高亮项滚动进可视区(block: nearest 不跳动)
      this.$nextTick(() => {
        const box = this.$refs[refName];
        if (!box) return;
        const el = box.querySelector('[data-hi="1"]');
        if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
      });
    },
    onAddFilePick(event) {
      const picked = Array.from((event.target && event.target.files) || []);
      for (const f of picked) {
        // 同名同大小视为重复(同一文件二次误选); File 对象只存引用不读内容
        if (!this.addFiles.some((x) => x.name === f.name && x.size === f.size)) this.addFiles.push(f);
      }
      event.target.value = "";  // 重置原生 input, 允许再次选择同一文件补选
    },
    removeAddFile(i) {
      this.addFiles = this.addFiles.filter((_, idx) => idx !== i);
    },
    addUrlCount() {
      return this.addUrls.split(/\r?\n/).filter((l) => l.trim()).length;
    },
    async submitAddTorrent() {
      if (!this.addCanSubmit) return;
      // .torrent 读取为 base64 随 JSON 提交(后端解码后 bytes 内存直传 qB —— 零临时文件零新依赖)
      const filesB64 = [];
      for (const f of this.addFiles) {
        filesB64.push(
          await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const result = String(reader.result || "");
              resolve(result.includes(",") ? result.slice(result.indexOf(",") + 1) : result);
            };
            reader.onerror = () => reject(new Error(`无法读取文件: ${f.name}`));
            reader.readAsDataURL(f);
          })
        );
      }
      const payload = {
        files_b64: filesB64,
        urls: this.addUrls.split("\n").map((u) => u.trim()).filter(Boolean),
        save_path: this.addSavePath.trim(),
        category: this.addCategory.trim(),
        tags: this.addTags.split(",").map((t) => t.trim()).filter(Boolean),
        paused: !this.addStart,  // DLG-03: 「添加后开始」勾选 = 立即开始; 默认不勾 = paused 添加
        skip_checking: this.addSkipCheck,
        sequential: this.addSequential,
        first_last_piece_prio: this.addFirstLast,
        auto_tmm: this.addTmm,
      };
      this.addSubmitting = true;
      try {
        // 不设 Content-Type, 浏览器自动生成 multipart boundary
        const queued = await this.api("/api/torrents/add", { method: "POST", body: JSON.stringify(payload) });
        const r = await this.waitCmd(queued.cmd_id);
        if (r.ok) {
          this.toast("添加种子已受理, 列表稍后自动刷新", "ok", 4000);
          this.addOpen = false;
        } else {
          this.toast(`添加种子失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!e.auth) this.toast("添加种子失败: " + e.message, "error", 8000);
      } finally {
        this.addSubmitting = false;
      }
    },
    /* ---------------- 多选与批量操作(Ctrl/⌘ 选中, Shift 范围; 普通点击行为不变) ---------------- */
    isGroupSelected(g) {
      return this.selGroups.includes(g.key);
    },
    onGroupClick(g, event) {
      this.menu.visible = false;
      if (event.ctrlKey || event.metaKey) {
        this.toggleGroupSel(g);
        return;
      }
      if (event.shiftKey) {
        this.shiftGroupSel(g);
        return;
      }
      this.toggleExpand(g.key, event);  // 普通点击保持"展开明细"原行为(不清除已有选择, 清除走浮条)
    },
    toggleGroupSel(g) {
      // FX-11: 组选择与种子选择互斥(同一时刻只一种口径, 否则批量目标混发、计数含义不明)
      this.selMembers = [];
      this.selAnchorMember = null;
      this.selGroups = this.selGroups.includes(g.key)
        ? this.selGroups.filter((k) => k !== g.key)
        : [...this.selGroups, g.key];
      this.selAnchorGroup = g.key;
    },
    shiftGroupSel(g) {
      // FX-11: Shift 扩展同样属"组选择口径" -> 清掉另一侧
      this.selMembers = [];
      this.selAnchorMember = null;
      // 从锚点到当前行整段加入选择(锚点不更新: 多次 Shift 可从同一起点扩展)
      // 锚点解析: Ctrl+点击设置的锚点 -> 当前展开的组(用户要求) -> 可见列表首行
      const list = this.filteredGroups.map((x) => x.key);
      let anchor = this.selAnchorGroup;
      if (!list.includes(anchor) && list.includes(this.expandedKey)) anchor = this.expandedKey;
      if (!list.includes(anchor)) anchor = list[0];
      const from = list.indexOf(anchor);
      const to = list.indexOf(g.key);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selGroups = [...new Set([...this.selGroups, ...list.slice(a, b + 1)])];
    },
    onMemberClick(m, event) {
      // 普通点击**不再选中**(用户 2026-09-17 明确: 点击种子不触发选择); 仅修饰键选择:
      // Ctrl/⌘ 切换单行, Shift 从锚点整段范围
      if (event.ctrlKey || event.metaKey) {
        this.toggleMemberSel(m);
        return;
      }
      if (event.shiftKey) this.shiftMemberSel(m);
    },
    toggleMemberSel(m) {
      // FX-11: 选种子 -> 清空辅种组选择(两个口径不共存)
      this.selGroups = [];
      this.selAnchorGroup = null;
      this.selMembers = this.selMembers.includes(m.hash)
        ? this.selMembers.filter((h) => h !== m.hash)
        : [...this.selMembers, m.hash];
      this.selAnchorMember = m.hash;
    },
    shiftMemberSel(m) {
      this.selGroups = [];  // FX-11: 同 toggleMemberSel
      this.selAnchorGroup = null;
      // 当前展开明细的成员内连续选择(跨组范围由分组表的多选承担)
      const g = this.filteredGroups.find((x) => x.key === this.expandedKey);
      if (!g) return;
      const list = g.members.map((x) => x.hash);
      const anchor = list.includes(this.selAnchorMember) ? this.selAnchorMember : list[0];
      const from = list.indexOf(anchor);
      const to = list.indexOf(m.hash);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selMembers = [...new Set([...this.selMembers, ...list.slice(a, b + 1)])];
    },
    /* ---------------- 单种子视图交互(R08)与信息栏模式(R09) ---------------- */
    /* W4: 顶栏一级导航(分组/种子/追剧)入口 — 复用 viewMode 三态; 从设置页点击时先回到辅种页,
     * 列宽重实体化契约由 watch(page) 与 setViewMode 内的 $nextTick 各自兜底, 路径与既有切页一致 */
    goView(mode) {
      if (this.page !== "groups") this.page = "groups";
      this.setViewMode(mode);
    },
    setViewMode(mode) {
      if (this.viewMode === mode) return;
      this.viewMode = mode;
      try { localStorage.setItem("autoqb.ui.view", mode); } catch { /* 持久化失败不影响功能 */ }
      // P1-1: 服务端只回当前视图的数组, 切视图后本地持有的 rid 与新视图的数据不再对应
      // ⇒ 置空强制下一轮取全量(切页首帧多一次全量, 换来的是之后每轮只传 1/4)
      this.lastRid = null;
      this.expandedKey = null;  // 展开态属于分组视图, 切换不跨视图残留
      this.expandedShows = [];  // 追剧视图展开态同理不跨视图残留
      this.expandedShowEp = null;
      this.$nextTick(() => {
        this._syncHeadHeight();
        this.materializeColumns();
      });
      // 立刻取一次新视图的数据, 不等下轮轮询(否则首次切到某视图要空/旧 ≤2s)。
      // scheduleNext 内部先 stopPolling 再排下一次, 所以这里不会造成双份轮询。
      if (this.authOk) this.refresh();
    },
    /* ---------------- 追剧视图(R10): 剧/集展开与整集操作 ---------------- */
    syncShowHeadScroll(ev) {
      const head = this.$refs.showHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    toggleShow(key) {
      const i = this.expandedShows.indexOf(key);
      if (i >= 0) this.expandedShows.splice(i, 1);
      else this.expandedShows.push(key);
    },
    isShowExpanded(key) {
      return this.expandedShows.includes(key);
    },
    showEpRowId(showKey, season, epKeyStr) {
      return `${showKey}|${season === null || season === undefined ? "~" : season}|${epKeyStr}`;
    },
    toggleShowEp(showKey, season, epKeyStr) {
      const id = this.showEpRowId(showKey, season, epKeyStr);
      this.expandedShowEp = this.expandedShowEp === id ? null : id;
      this.menu.visible = false;
    },
    /* 集键 -> 展示文本(与后端 tvshows.ParsedRelease.episode_key 三形态对应) */
    epLabel(key) {
      if (!key || !key.length) return "—";
      if (key[0] === "ep") return "E" + String(key[1]).padStart(2, "0");
      if (key[0] === "range") return `E${String(key[1]).padStart(2, "0")}-E${String(key[2]).padStart(2, "0")}`;
      if (key[0] === "date") return key[1];
      return "整季包";
    },
    seasonLabel(season) {
      return season === null || season === undefined ? "日播 / 特别篇" : `第 ${season} 季`;
    },
    /* 集成员 -> hash 列表: 后端 shows 视图的 members 是 **hash 数组**, 而 decoratedShows 会把它们
     * 换成**成员对象**(带 hit 标记, 供行内渲染/筛选)。菜单与命令只认 hash —— 两种形态都要能取到,
     * 否则对象被字符串化后变成 "[object Object]": 后端查不到该 hash ⇒ 404「种子不存在」,
     * 整集/整剧的 开始/暂停/强制汇报/打开目标文件夹/删除 全线哑火(单种子菜单传的是 member.hash,
     * 不受影响 —— 这正是"种子右键能打开、剧/集右键打不开"的差异来源)。 */
    memberHashesOf(list) {
      return (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
    },
    /* 整集右键菜单: 目标 = 该集全部成员(多版本), 操作走单种子命令(与批量同语义) */
    openShowEpMenu(event, show, ep) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      this.menu = {
        visible: true,
        ...this._menuPos(event),
        key: null,
        hash: null,
        episode: { hashes: this.memberHashesOf(ep.members), label: `${show.name} ${this.epLabel(ep.key)}`, scope: "ep" },
      };
    },
    /* FX-13: 整剧右键菜单。追剧页的"剧"这一层此前只有左键展开、没有 @contextmenu ——
     * 越级的整剧操作(开始/暂停/汇报/打开目录/删除)无处可做。目标 = 该剧全部集的全部成员(去重),
     * 与整集菜单共用同一分支与动作链, 仅用 scope 区分文案与确认框标题。 */
    openShowMenu(event, show) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      const hashes = [];
      const seen = new Set();
      for (const sn of show.seasons || []) {
        for (const e of sn.episodes || []) {
          for (const h of this.memberHashesOf(e.members)) {
            if (!seen.has(h)) {
              seen.add(h);
              hashes.push(h);
            }
          }
        }
      }
      if (!hashes.length) return;
      this.menu = { visible: true, ...this._menuPos(event), key: null, hash: null, episode: { hashes, label: show.name, scope: "show" } };
    },
    async actEpisode(action) {
      this.menu.visible = false;
      const ep = this.menu.episode || {};
      const hashes = ep.hashes || [];
      if (!hashes.length) return;
      const what = ep.scope === "show" ? "整剧" : "整集";
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      // P0-4: pause/resume 合单为一条 bulk 命令 —— 整剧动辄上百集, 逐条投递要发上百次请求
      if (!isRe) {
        const t0 = this._newCmdStats(action);
        // P0-3: 与整组/单种子同一条乐观链路(整集/整剧此前**完全没接**, 点了没有任何即时反馈)
        this.applyOptimistic(hashes, action);
        this._markCmdPatch(t0);
        try {
          const resp = await this.api("/api/torrents/bulk", {
            method: "POST",
            body: JSON.stringify({ action, hashes }),
          });
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          if (r.ok) this.toast(`已执行: ${label}${what}(${hashes.length} 个种子)`, "ok", 2500);
          else this.toast(`${label}${what}失败: ${r.error}`, "error", 8000);
        } catch (e) {
          this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
          if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
        }
        return;
      }
      const tid = this.toast(`强制汇报等待中…(${hashes.length} 个目标, tracker 确认最长 30s)`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        hashes.map((h) =>
          this.api(`/api/torrents/${h}/${action}`, { method: "POST" }).then((r) =>
            this.waitCmd(r.cmd_id, 40000, { firstMs: 500, capMs: 1000 })
          )
        )
      );
      const fails = results.filter((r) => r.status === "rejected" || !r.value.ok);
      if (!fails.length) {
        this._finishToast(tid, "ok", `强制汇报成功(tracker 已确认, ${hashes.length} 个目标)`, 3000);
        return;
      }
      const firstErr = fails[0].status === "rejected" ? fails[0].reason.message : fails[0].value.error;
      this._finishToast(
        tid,
        "timeout",
        `强制汇报: 成功 ${hashes.length - fails.length}, 失败 ${fails.length}${firstErr ? ` (${firstErr})` : ""}`,
        6000
      );
    },
    /* 删除整集/整剧(全部版本; FX-13 起两者共用): 目标名与种子数进 body, 详情行由 _deleteFlow 统一派生 */
    async delEpisode() {
      this.menu.visible = false;
      const ep = this.menu.episode;
      if (!ep || !ep.hashes.length) return;
      const members = ep.hashes.map((h) => this.memberByHash.get(h)).filter(Boolean);
      if (!members.length) return;
      const what = ep.scope === "show" ? "整剧" : "整集";
      // FX-16: 与右键/批量/该种子共用同一条删除链; R10-16: 详情行由 _deleteFlow 统一派生
      await this._deleteFlow({
        keys: [],
        hashes: ep.hashes.slice(),
        title: `删除${what}`,
        body: `将删除"${ep.label}"的全部 ${members.length} 个种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText: `${what}(${members.length} 个种子)`,
        label: ep.label,
      });
    },
    /* 单种子表横向滚动 -> 表头位移同步(与分组表同款 transform 桥接, 避免双向 scroll 回环) */
    syncTorrentHeadScroll(ev) {
      const head = this.$refs.torrentHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    /* 单种子行点击: 修饰键语义与明细行一致(Ctrl 切换 / Shift 平铺范围); 普通点击不选中 */
    onTorrentClick(m, event) {
      this.menu.visible = false;
      if (event.ctrlKey || event.metaKey) {
        this.toggleMemberSel(m);
        return;
      }
      if (event.shiftKey) this.shiftTorrentSel(m);
    },
    shiftTorrentSel(m) {
      this.selGroups = [];  // FX-11: 同 toggleMemberSel
      this.selAnchorGroup = null;
      // 平铺列表内的连续范围选择(锚点不更新, 可从同一起点多次扩展)
      const list = this.filteredTorrents.map((x) => x.hash);
      const anchor = list.includes(this.selAnchorMember) ? this.selAnchorMember : list[0];
      const from = list.indexOf(anchor);
      const to = list.indexOf(m.hash);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selMembers = [...new Set([...this.selMembers, ...list.slice(a, b + 1)])];
    },
    clearSelection() {
      this.selGroups = [];
      this.selMembers = [];
      this.selAnchorGroup = null;
      this.selAnchorMember = null;
      this.selAnchorUnit = null;
    },
    /* ---------------- FX-12: 追剧页选中态与修饰键选择 ----------------
     * 剧行/集行保留"点击 = 展开"的原行为; **修饰键才选中**(与表格一致):
     * Ctrl/⌘+点击 = 切换该剧/该集全部成员; Shift+点击 = 从锚点单元整段选择。
     * "全部成员被选" = selected, "命中但非全选" = partial(indeterminate 语义)。
     */
    _selState(hashes) {
      const list = hashes || [];
      if (!list.length) return { selected: false, partial: false };
      const set = this.selHashSet;
      let hit = 0;
      for (const h of list) if (set.has(h)) hit += 1;
      return { selected: hit === list.length, partial: hit > 0 && hit < list.length };
    },
    isMemberSelected(m) {
      return this.selHashSet.has(m.hash);
    },
    /* 组行选中态: 组本身被选 -> selected; 否则派生集合命中其**部分**成员 -> partial。
     * (典型场景: 在种子页选了某辅种组的几个种子, 切回辅种页该组应显示"半选"而非"没选") */
    groupSelState(g) {
      if (this.isGroupSelected(g)) return { selected: true, partial: false };
      const st = this._selState((g.members || []).map((m) => m.hash));
      return { selected: false, partial: st.partial };
    },
    _showHashes(s) {
      const out = [];
      for (const sn of s.seasons || []) {
        for (const e of sn.episodes || []) {
          out.push(...this.memberHashesOf(e.members));
        }
      }
      return [...new Set(out)];
    },
    _showUnits() {
      return this.decoratedShows.map((s) => ({ id: "show|" + s.key, hashes: this._showHashes(s) }));
    },
    _epUnits(s) {
      const out = [];
      for (const sn of s.seasons || []) {
        for (const e of sn.episodes || []) {
          out.push({ id: this.showEpRowId(s.key, sn.season, e.epKeyStr), hashes: this.memberHashesOf(e.members) });
        }
      }
      return out;
    },
    showSelState(s) {
      const u = this._showUnits().find((x) => x.id === "show|" + s.key);
      return this._selState(u ? u.hashes : []);
    },
    epSelState(e) {
      return this._selState(this.memberHashesOf(e.members));
    },
    /* 整单元切换: 全选中则整段取消, 否则整段加入(并清掉辅种组口径) */
    _toggleUnit(unit) {
      if (!unit || !unit.hashes.length) return;
      this.selGroups = [];
      this.selAnchorGroup = null;
      const all = unit.hashes;
      const cur = this.selMembers;
      const allIn = all.every((h) => cur.includes(h));
      this.selMembers = allIn ? cur.filter((h) => !all.includes(h)) : [...new Set([...cur, ...all])];
      this.selAnchorUnit = unit.id;
    },
    _extendUnit(unit, list) {
      if (!unit) return;
      const units = list || [];
      const anchorIdx = units.findIndex((u) => u.id === this.selAnchorUnit);
      const curIdx = units.findIndex((u) => u.id === unit.id);
      if (anchorIdx < 0 || curIdx < 0) {
        this._toggleUnit(unit);
        return;
      }
      this.selGroups = [];
      this.selAnchorGroup = null;
      const [a, b] = anchorIdx <= curIdx ? [anchorIdx, curIdx] : [curIdx, anchorIdx];
      const add = [];
      for (const u of units.slice(a, b + 1)) add.push(...u.hashes);
      this.selMembers = [...new Set([...this.selMembers, ...add])];
    },
    onShowClick(s, event) {
      if (event.ctrlKey || event.metaKey) {
        this._toggleUnit(this._showUnits().find((u) => u.id === "show|" + s.key));
        return;
      }
      if (event.shiftKey) {
        this._extendUnit(this._showUnits().find((u) => u.id === "show|" + s.key), this._showUnits());
        return;
      }
      this.toggleShow(s.key);
    },
    onShowEpClick(s, sn, e, event) {
      const id = this.showEpRowId(s.key, sn.season, e.epKeyStr);
      const units = this._epUnits(s);
      if (event.ctrlKey || event.metaKey) {
        this._toggleUnit(units.find((u) => u.id === id));
        return;
      }
      if (event.shiftKey) {
        this._extendUnit(units.find((u) => u.id === id), units);
        return;
      }
      this.toggleShowEp(s.key, sn.season, e.epKeyStr);
    },
    _findGroup(key) {
      // **必须先查 decoratedGroups**(groups 的前端派生超集, 同 key): 原始组字典没有 save_path
      // 等派生字段 —— 曾致删除确认框的保存路径恒为"—"(R03)。filteredGroups 兼容虚拟行(u-<hash>)
      return this.decoratedGroups.find((g) => g.key === key) || this.filteredGroups.find((g) => g.key === key) || null;
    },
    /* 选中集合拆解: 虚拟行(未归组命中种子)无真实组 key, 转为单种子命令; 已消失的目标跳过 */
    _bulkTargets() {
      const groupKeys = [];
      const memberHashes = [...this.selMembers];
      for (const k of this.selGroups) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) memberHashes.push(g.members[0].hash);
        else groupKeys.push(k);
      }
      return { groupKeys, memberHashes };
    },
    /* 批量动作: pause/resume/recheck **合单**为一条 bulk 命令(一次 POST + 一个聚合回执);
     * reannounce 仍逐目标投递(后端 _BULK_ACTIONS 不含它 —— tracker 确认要逐个跟踪)。
     * 合单前 100 个目标 = 100 次 POST + 100 条回执轮询, 后端还要串行跑 100 次 qB 调用
     * (在主循环线程上, 期间界面"卡住"); 合单后是 1 + 1。 */
    async bulkAct(action) {
      const { groupKeys, memberHashes } = this._bulkTargets();
      const label = action === "recheck" ? "重新校验" : this._actionText(action);
      if (action !== "reannounce") {
        // 后端 bulk 会自己展开 keys 的组成员并与 hashes 合并去重, 组级端点不支持的
        // recheck 也因此不必在前端展开 —— 只有组没有成员时后端计一个"缺失组"。
        if (!groupKeys.length && !memberHashes.length) return;
        const hashes = [...memberHashes];
        for (const k of groupKeys) {
          const g = this._findGroup(k);
          if (g) for (const m of g.members) hashes.push(m.hash);
        }
        const t0 = this._newCmdStats(action);
        this.applyOptimistic(hashes, action);  // P0-3: 点击即变(失败会回滚)
        this._markCmdPatch(t0);
        try {
          const resp = await this.api("/api/torrents/bulk", {
            method: "POST",
            body: JSON.stringify({ action, keys: groupKeys, hashes: memberHashes }),
          });
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          const n = groupKeys.length + memberHashes.length;
          if (r.ok) this.toast(`已执行: ${label}(${n} 个目标)`, "ok", 2500);
          else this.toast(`${label}失败: ${r.error}`, "error", 8000);
        } catch (e) {
          this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
          if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
        }
        return;
      }
      const jobs = [
        ...groupKeys.map((k) => `/api/groups/${k}/${action}`),
        ...memberHashes.map((h) => `/api/torrents/${h}/${action}`),
      ];
      if (!jobs.length) return;
      // 批量汇报: 常驻"等待中"(含目标数), 回执齐后原位换汇总终态(成功/超时, 琥珀不用红警告)
      const tid = this.toast(`强制汇报等待中…(${jobs.length} 个目标, tracker 确认最长 30s)`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        jobs.map((p) =>
          this.api(p, { method: "POST" }).then((r) => this.waitCmd(r.cmd_id, 40000, { firstMs: 500, capMs: 1000 }))
        )
      );
      const fails = results.filter((r) => r.status === "rejected" || !r.value.ok);
      if (!fails.length) {
        this._finishToast(tid, "ok", `强制汇报成功(tracker 已确认, ${jobs.length} 个目标)`, 3000);
        return;
      }
      const firstErr = fails[0].status === "rejected" ? fails[0].reason.message : fails[0].value.error;
      this._finishToast(
        tid,
        "timeout",
        `强制汇报: 成功 ${jobs.length - fails.length}, 失败 ${fails.length}${firstErr ? ` (${firstErr})` : ""}`,
        6000
      );
    },
    /* DLG-02: 批量删除文案按选择构成计数(仅辅种=N 个辅种 / 仅种子=N 个种子)。
     * 用 _bulkTargets 的有效口径 —— 虚拟行(未归组命中)无真实组 key、按种子投递, 计入"种子"
     * 而非"辅种", 保证批量条按钮/确认框标题/提交体三处一致; 空串 = 选中项均已失效。
     * FX-12: 批量条直接渲染它 —— 计数随**权威选择**而非当前视图漂移
     * (在种子页看"N 个辅种"不变, 这正是"三视图打通"的直观体现)。
     * ⚠ 方法名不得以 `_` 开头: Vue 模板编译器不解析下划线前缀标识符
     *   (会报 "_xxx is not defined" 且整块渲染失败 —— 2026-09-17 浏览器冒烟实测)。
     */
    bulkCountText() {
      const { groupKeys, memberHashes } = this._bulkTargets();
      const parts = [];
      if (groupKeys.length) parts.push(`${groupKeys.length} 个${L10N_GROUP}`);
      if (memberHashes.length) parts.push(`${memberHashes.length} 个种子`);
      return parts.join("、");
    },
    /* 批量条删除按钮文案: 计数文本前缀"删除", 空选中退化为纯"删除" */
    bulkDeleteLabel() {
      const t = this.bulkCountText();
      return t ? `删除 ${t}` : "删除";
    },
    async bulkDelete() {
      const { groupKeys, memberHashes } = this._bulkTargets();
      if (!groupKeys.length && !memberHashes.length) return;
      const countText = this.bulkCountText();
      // 摘要计数(DLG-01 收缩: 确认框不再列逐条成员明细, 只保留目标摘要+计数):
      // 组展开到成员级, 与选中的种子并集去重 —— 与后端 bulk 组键展开(级联在册成员,
      // 与 hashes 合并去重)同口径; 成员大小经 memberByHash 解析(groups ∪ singles ∪ torrents 全量)。
      // R10-16: 确认框的详情行改由 _deleteFlow 统一派生, 这里只算 body 要用的**种子数**(seen.size)。
      const seen = new Set();
      const countMember = (m) => {
        if (!m || seen.has(m.hash)) return;
        seen.add(m.hash);
      };
      for (const k of groupKeys) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) countMember(g.members[0]);
        else for (const m of g.members || []) countMember(m);
      }
      for (const h of memberHashes) countMember(this.memberByHash.get(h));
      // FX-16: 统一走 _deleteFlow(与右键同一套: 目标明细 + 汇报前置 + 等聚合回执 + 收尾清选择)
      // R10-16: 不再自传 details(由 _deleteFlow 从目标集合派生), 四个入口的窗口结构由此完全一致
      await this._deleteFlow({
        keys: groupKeys,
        hashes: memberHashes,
        title: `删除 ${countText}`,
        body: `将删除选中目标内的全部种子, 共 ${seen.size} 个。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText,
        label: countText,
      });
    },
    /* ---------------- FX-16 删除链统一 ----------------
     * 旧实现是**两条链**: 右键(逐目标专用端点, 不等回执)与 批量(bulk 单命令, 等聚合回执),
     * 确认框内容也分叉(逐目标详情 vs 纯计数)。统一成一条链, **以右键的行为为准**
     * (目标明细 + 汇报前置 + 汇报失败即中止保留), 并保留批量侧更稳的两点(单命令聚合回执、
     * 收尾清选择)。四个入口(delGroup / delTorrent / delEpisode / bulkDelete)只负责组织 targets。
     *
     * targets = { keys[], hashes[], title, body, details[], countText, label }
     * 注: /api/groups/{k}/delete 与 /api/torrents/{h}/delete 端点**保留不动**(旧 UI 与第三方脚本仍可用)。
     */
    /* R10-16 删除详情行统一派生: 四个入口(右键组/右键种子/批量/整集整剧)过去各自拼 details,
     * 结果"同壳不同构"(右键 5 行含站点/保存路径, 批量只有 2 行摘要) —— 用户看到的就是
     * "不是同一个删除窗口"。现在入口只交目标集合, 明细行一律由本函数算: 目标 -> 计数 ->
     * 站点集合 -> 保存路径集合 -> 总大小; 单目标自然退化成逐项明细(站点/路径回到单体值)。
     * 多目标走集合摘要(决策 D8-A): 避免几十个目标把弹窗撑爆。 */
    _deleteDetails(keys, hashes) {
      const seen = new Map();  // hash -> member(组展开与 hashes 去重)
      const collect = (m) => {
        if (m && m.hash && !seen.has(m.hash)) seen.set(m.hash, m);
      };
      const names = [];
      for (const k of keys || []) {
        const g = this._findGroup(k);
        if (!g) continue;
        names.push(g.name);
        if (g.virtual) collect(g.members[0]);
        else for (const m of g.members || []) collect(m);
      }
      for (const h of hashes || []) collect(this.memberByHash.get(h));
      const members = [...seen.values()];
      const sites = [...new Set(members.map((m) => m.site).filter(Boolean))];
      const paths = [...new Set(members.map((m) => m.save_path).filter(Boolean))];
      const totalSize = members.reduce((n, m) => n + (m.size || 0), 0);
      const single = (keys || []).length + (hashes || []).length <= 1 && members.length <= 1;
      // 目标: 单目标退化为**它的名字**(单辅种 = 辅种名, 单种子 = 种子名), 多目标走集合摘要
      const target = single && names.length === 1 ? names[0]
        : single && members.length === 1 ? (members[0].name || members[0].hash.slice(0, 12))
          : `${(keys || []).length} 个${L10N_GROUP} · ${members.length} 个种子`;
      return [
        { icon: "#i-cards", label: "目标", value: target, wide: true },
        { icon: "#i-layers", label: "成员", value: `${members.length} 个种子` },
        { icon: "#i-globe", label: "站点", value: sites.join(", ") || "—" },
        { icon: "#i-folder-open", label: "保存路径", value: paths.join(" · ") || "—", wide: true },
        { icon: "#i-hdd", label: "总大小", value: this.fmtSize(totalSize) },
      ];
    },
    async _deleteFlow(targets) {
      const keys = targets.keys || [];
      const hashes = targets.hashes || [];
      if (!keys.length && !hashes.length) return;
      const res = await this._confirmDelete({
        title: targets.title,
        body: targets.body,
        // R10-16: 入口不再传 details(传了也忽略) —— 四入口看到的窗口结构完全一致
        details: this._deleteDetails(keys, hashes),
      });
      if (!res) return;
      const deleteFiles = res.checks.delete_files;
      if (res.checks.reannounce) {
        const jobs = [
          ...keys.map((k) => `/api/groups/${k}/reannounce`),
          ...hashes.map((h) => `/api/torrents/${h}/reannounce`),
        ];
        const ok = await this._reannounceAll(jobs, targets.label);
        if (!ok) return;  // 汇报失败: 已提示且保留未删除
      }
      // 投递删除: 统一走 bulk 单命令并等聚合回执(比旧右键的"已投递"更可信: 失败可见)
      try {
        const resp = await this.api("/api/torrents/bulk", {
          method: "POST",
          body: JSON.stringify({ action: "delete", keys, hashes, delete_files: deleteFiles }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已删除: ${targets.countText}${deleteFiles ? "(含文件)" : ""}`, "ok", 3000);
        else this.toast(`删除未完全成功: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast("删除命令发送失败: " + e.message, "error");
      }
      this.clearSelection();  // 列表交下一轮 rid 轮询自然刷新(不主动 refresh)
    },
    /* 汇报前置: 逐目标投递并**全部等回执**; 全部成功返回 true(任一失败 -> 已提示且保留未删除) */
    async _reannounceAll(jobs, label) {
      if (!jobs.length) return true;
      const tid = this.toast(`正在向 tracker 汇报 ${jobs.length} 个目标, 等待确认…`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        jobs.map((p) => this.api(p, { method: "POST" }).then((r) => this.waitCmd(r.cmd_id)))
      );
      const fails = results.filter((r) => r.status === "rejected" || !r.value.ok);
      if (fails.length) {
        this._finishToast(tid, "timeout", `${fails.length}/${jobs.length} 个目标汇报确认失败${label ? `(${label})` : ""}, 已保留未删除`, 6000);
        return false;
      }
      this._finishToast(tid, "ok", "汇报确认成功, 开始删除…", 2000);
      return true;
    },
    /* ---------------- 删除确认框: 目标信息 + 强制汇报(默认勾选)/删除文件两选项 ---------------- */
    _confirmDelete(opts) {
      return this._openModal({
        title: opts.title,
        body: opts.body,
        details: opts.details || null,
        wide: true,  // 删除类确认框一律加宽: 摘要与选项宽松可读(DLG-01 成员明细已移除, 宽度见 --modal-wide-w)
        checks: [
          { key: "reannounce", label: "删除前先强制汇报(等待 tracker 确认, 失败则不删除)", checked: true },
          { key: "delete_files", label: "同时删除磁盘文件(不可恢复)", checked: false },
        ],
        okText: "删除",
        cancelText: "取消",
        danger: true,
        icon: "#i-trash-x",
      });
    },
    /* 删除前汇报编排已被 _reannounceAll 取代(FX-16: 右键/批量/整集/整剧 四条入口统一走
     * _deleteFlow -> _reannounceAll 一套链), 旧单目标版本删除 —— 不再保留两条链。 */
    /* 删除该辅种(DLG-02: 旧"整组"叫法退役, 组删除一律计数语义): 单一菜单项 + 确认框显示目标信息
     * (辅种名/成员/站点/路径/总大小)与两个选项; FX-16 起删除动作本身交由 _deleteFlow 统一驱壳。 */
    async delGroup() {
      this.menu.visible = false;
      const key = this.menu.key;
      if (!key) return;
      const g = this._findGroup(key);
      if (!g) return;
      // R10-16: 详情行(辅种名/成员/站点/保存路径/总大小)改由 _deleteFlow 统一派生 ——
      // 单目标时自然退化成逐项明细, 与批量/整集入口结构一致
      await this._deleteFlow({
        keys: [key],
        hashes: [],
        title: `删除该${L10N_GROUP}`,
        body: `将删除"${g.name}"的全部 ${g.count} 个种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText: `该${L10N_GROUP}(${g.count} 个种子)`,
        label: `"${g.name}"`,
      });
    },
    async actTorrent(action) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      // 同 act(): 补丁先于 POST(见那里的注释与 issue 26-09-19-1939-webui-optimistic-latency)
      const hashes = isRe ? [] : [this.menu.hash];
      const t0 = isRe ? 0 : this._newCmdStats(action);
      if (!isRe) {
        this.applyOptimistic(hashes, action);
        this._markCmdPatch(t0);
      }
      try {
        const resp = await this.api(`/api/torrents/${this.menu.hash}/${action}`, { method: "POST" });
        if (isRe) {
          const tid = this.toast("强制汇报等待中…(已投递, tracker 确认最长 30s)", "busy", 0, { sticky: true });
          const r = await this.waitCmd(resp.cmd_id, 40000, { firstMs: 500, capMs: 1000 });
          if (r.ok) this._finishToast(tid, "ok", "强制汇报成功(tracker 已确认)", 3000);
          else this._finishToast(tid, "timeout", `强制汇报超时失败: ${r.error}`, 6000);
        } else {
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          if (r.ok) this.toast(`已执行: ${label}该种子`, "ok", 2500);
          else this.toast(`${label}该种子失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!isRe) this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 复制种子信息(种子页右键 R1A): clipboard API 优先, execCommand 降级(非安全上下文/权限拒绝);
     * 无论成功失败都给 toast 反馈 */
    async _copyText(text, label) {
      let ok = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          ok = true;
        }
      } catch { ok = false; }
      if (!ok) {
        // 降级: 离屏 textarea + execCommand(旧浏览器 / file:// 等 clipboard API 不可用场景)
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try { ok = document.execCommand("copy"); } catch { ok = false; }
        document.body.removeChild(ta);
      }
      if (ok) this.toast(`已复制${label}`, "ok", 2000);
      else this.toast("复制失败: 浏览器未授权剪贴板访问", "error");
    },
    /* 右键菜单复制项: field = name | hash | magnet(数据取 memberByHash 的 SEED_ITEM 完整字段) */
    /* 导出 .torrent(种子页右键 R2 补遗): fetch 字节 → blob 下载(Bearer 走 header, 不能用 a href 直链;
     * 不能用 this.api —— 它固定 resp.json(), 而这里是二进制流) */
    async exportTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      try {
        const resp = await fetch(`/api/torrents/${hash}/export`, { headers: { Authorization: `Bearer ${this.token}` } });
        if (resp.status === 401) {
          this._logout("密钥无效或已更换");
          return;
        }
        if (!resp.ok) {
          const detail = await resp.json().catch(() => ({}));
          throw new Error(detail.detail || `HTTP ${resp.status}`);
        }
        const buf = await resp.arrayBuffer();
        const m = this.memberByHash.get(hash) || {};
        const name = String(m.name || hash).replace(/["\\/]/g, "_") + ".torrent";
        const url = URL.createObjectURL(new Blob([buf], { type: "application/x-bittorrent" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
        this.toast("已导出 .torrent", "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("导出失败: " + e.message, "error", 8000);
      }
    },
    /* 自动种子管理开关(种子页右键 R2 补遗): 复用 torrentCmd 回执链 */
    autoTmmToggle() {
      const m = this.menuTorrent();
      this.torrentCmd("auto-tmm", { enable: !m.auto_tmm }, m.auto_tmm ? "关闭自动种子管理" : "开启自动种子管理");
    },
    /* 右键菜单当前种子(SEED_ITEM 完整字段): 供菜单项动态文案/开关初值 */
    menuTorrent() {
      return this.memberByHash.get(this.menu.hash) || {};
    },
    /* 种子控制命令(R2): 带 body 的单种命令(校验/超级做种/强制开始/队列) —— 走既有回执链 */
    async torrentCmd(action, body = null, okText = "") {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已执行: ${okText || action}`, "ok", 2500);
        else this.toast(`${okText || action}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 抽屉内命令: 与 torrentCmd 同链路, 但 hash 取自抽屉(菜单未开时 menu.hash 为空) */
    drawerCmd(action, body = null, okText = "") {
      this.menu.hash = this.drawer.hash;
      this.torrentCmd(action, body, okText);
    },
    /* ---------------- 种子编辑对话框(D 轮): 限速/分享率限制/移动/重命名 ----------------
     * 统一形态: 多字段 .modal(modal.fields) + 回执 toast; 预填当前值, 空输入 = 不修改。
     * hash 约定: 菜单调用不传参取 menu.hash, 抽屉调用显式传 drawer.hash(与 drawerCmd 同约定)。 */
    _editTargetHash(h) {
      const hash = h || this.menu.hash;
      this.menu.visible = false;
      return hash || "";
    },
    /* 编辑类对话框取当前值: 抽屉已开且同一 hash 直接用 drawer.detail, 否则现拉一次详情 */
    async _editDetail(hash) {
      if (this.drawer.open && this.drawer.hash === hash && this.drawer.detail) return this.drawer.detail;
      try {
        const r = await this.api(`/api/torrents/${hash}`);
        return (r && r.torrent) || null;
      } catch (e) {
        if (!e.auth) this.toast("当前值获取失败: " + e.message, "error");
        return null;
      }
    },
    /* 编辑类命令统一投递: api + waitCmd 回执 + toast 三态; 成功后按动作刷新抽屉对应页签数据 */
    async _editPost(hash, action, body, okText) {
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(`已执行: ${okText}`, "ok", 2500);
          if (this.drawer.open && this.drawer.hash === hash) {
            this._fetchDrawerDetail();
            if (action.startsWith("trackers/")) this._fetchDrawerTrackers(true);
            else if (action === "files/priority" || action === "rename-fs") this._fetchDrawerFiles(true);
          }
          return true;
        }
        this.toast(`${okText}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast(`${okText}命令发送失败: ` + e.message, "error");
      }
      return false;
    },
    /* 限速…: 上传/下载两输入(KiB/s; 空=不改, 0=不限) → POST limits(×1024 转 bytes, 0 原样传) */
    async editLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const kiB = (bytes) => (bytes > 0 ? String(Math.round(bytes / 1024)) : "");  // 不限/未设(≤0)留空
      const res = await this._openModal({
        title: "限速",
        body: "设置该种子的上传/下载速度上限(KiB/s)。留空 = 保持不变, 填 0 = 不限速。",
        fields: [
          { key: "up", label: "上传上限(KiB/s)", value: d ? kiB(d.up_limit) : "", placeholder: "留空不修改, 0 = 不限" },
          { key: "dl", label: "下载上限(KiB/s)", value: d ? kiB(d.dl_limit) : "", placeholder: "留空不修改, 0 = 不限" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      for (const [k, key] of [["up", "up_limit"], ["dl", "dl_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || n < 0) {
          this.toast("限速需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(n * 1024);  // KiB/s → bytes/s; 0 原样传(后端语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "limits", body, "限速已更新");
    },
    /* 分享率限制…: 分享率/做种时长(h)/不活跃做种时长(h) → POST share-limits(-1 = 恢复全局默认) */
    async editShareLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const hrs = (sec) => (sec > 0 ? String(Math.round((sec / 3600) * 100) / 100) : "");  // -1/0(未设)留空
      const res = await this._openModal({
        title: "分享率限制",
        body: "达到任一限制后该种子将停止做种。留空 = 保持不变, 填 -1 = 恢复全局默认。",
        fields: [
          { key: "ratio", label: "分享率上限", value: d && d.max_ratio >= 0 ? String(d.max_ratio) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "time", label: "做种时长上限(小时)", value: d ? hrs(d.max_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "inactive", label: "不活跃做种上限(小时)", value: d ? hrs(d.max_inactive_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      if (res.ratio !== "") {
        const n = Number(res.ratio);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("分享率需为非负数字(或 -1)", "warn");
          return;
        }
        body.ratio_limit = n;
      }
      for (const [k, key] of [["time", "seeding_time_limit"], ["inactive", "inactive_seeding_time_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("时长需为非负小时数(或 -1)", "warn");
          return;
        }
        body[key] = n === -1 ? -1 : Math.round(n * 3600);  // 小时 → 秒; -1 原样(未设/全局)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "share-limits", body, "分享率限制已更新");
    },
    /* 移动…: 新保存路径输入(确认文案注明离开辅种组) → POST location */
    async editMove(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "移动种子",
        body: "将种子文件移动到新路径。注意: 移动后该种子将离开当前辅种组。",
        fields: [{ key: "location", label: "新保存路径", value: d ? d.save_path || "" : "", placeholder: "D:\\downloads\\target" }],
        okText: "移动", cancelText: "取消",
      });
      if (!res) return;
      if (!res.location) {
        this.toast("路径不能为空", "warn");
        return;
      }
      await this._editPost(hash, "location", { location: res.location }, "已移动");
    },
    /* 重命名…: 种子显示名(不改磁盘文件名) → POST rename */
    async editRename(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "重命名种子",
        body: "修改种子显示名(不影响磁盘上的文件/目录名)。",
        fields: [{ key: "name", label: "新名称", value: d ? d.name || "" : "", placeholder: "新种子名" }],
        okText: "重命名", cancelText: "取消",
      });
      if (!res) return;
      if (!res.name) {
        this.toast("名称不能为空", "warn");
        return;
      }
      await this._editPost(hash, "rename", { name: res.name }, "已重命名");
    },
    /* ---------------- 抽屉 Tracker 页签编辑(D 轮): 添加/编辑/删除 ---------------- */
    async trackerAdd() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const raw = await this.promptDialog("添加 Tracker", "", {
        placeholder: "announce URL(多条用换行/逗号分隔)", okText: "添加",
      });
      if (raw === null) return;
      const urls = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
      if (!urls.length) {
        this.toast("请输入至少一条 tracker URL", "warn");
        return;
      }
      await this._editPost(hash, "trackers/add", { urls }, urls.length > 1 ? `已添加 ${urls.length} 条 tracker` : "tracker 已添加");
    },
    async trackerEdit(url) {
      const hash = this.drawer.hash;
      if (!hash) return;
      const nu = await this.promptDialog("编辑 Tracker", url, { placeholder: "新的 announce URL", okText: "保存" });
      if (nu === null) return;
      const newUrl = String(nu || "").trim();
      if (!newUrl) {
        this.toast("URL 不能为空", "warn");
        return;
      }
      if (newUrl === url) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "trackers/edit", { orig_url: url, new_url: newUrl }, "tracker 已更新");
    },
    async trackerRemove(url) {
      const hash = this.drawer.hash;
      if (!hash) return;
      const ok = await this.confirmDialog("删除 Tracker", `将删除该 tracker: ${url}`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._editPost(hash, "trackers/remove", { url }, "tracker 已删除");
    },
    /* ---------------- 抽屉内容页签编辑(D 轮): 行选中/优先级/文件重命名 ---------------- */
    /* 行点击选中(文件/目录均可): 再点同一行取消 —— 顶部"重命名…"的作用对象 */
    fileRowSelect(r) {
      this.drawerSelPath = this.drawerSelPath === r.path ? "" : r.path;
    },
    /* 文件优先级小菜单: 锚定单元格下方, 视口吸附(@click.stop 防止开菜单的点击立即被窗口关闭) */
    openFilePrio(ev, index) {
      this._markCtxSource(ev);
      const rect = ev.currentTarget.getBoundingClientRect();
      const w = 150, h = 176;
      this.filePrio = {
        visible: true, index,
        x: Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - w - 8)),
        y: Math.min(rect.bottom + 4, Math.max(8, window.innerHeight - h - 8)),
      };
    },
    /* 优先级 4 档(0=跳过 1=普通 6=高 7=最高) → POST files/priority(单文件) */
    async setFilePriority(p) {
      this.filePrio.visible = false;
      const index = this.filePrio.index;
      const hash = this.drawer.hash;
      if (!hash || index < 0) return;
      const label = { 0: "跳过", 1: "普通", 6: "高", 7: "最高" }[p] || String(p);
      await this._editPost(hash, "files/priority", { indices: [index], priority: p }, `优先级已设为「${label}」`);
    },
    /* 文件/目录重命名(选中行; 单文件种子免选): POST rename-fs, new_path = 原目录前缀 + 新名 */
    async renameFileRow() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const rows = this.drawerFileRows();
      let row = rows.find((r) => r.path === this.drawerSelPath);
      if (!row && rows.length === 1) row = rows[0];  // 单文件种子: 免选中直接改
      if (!row) {
        this.toast("请先点击选中要重命名的文件或目录", "warn");
        return;
      }
      const res = await this.promptDialog(row.dir ? "重命名目录" : "重命名文件", row.name, {
        body: `当前路径: ${row.path}`,
        okText: "重命名",
      });
      if (res === null) return;
      const nn = String(res || "").trim();
      if (!nn) {
        this.toast("名称不能为空", "warn");
        return;
      }
      if (nn === row.name) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      const parent = row.path.includes("/") ? row.path.slice(0, row.path.lastIndexOf("/") + 1) : "";
      await this._editPost(hash, "rename-fs", {
        old_path: row.path, new_path: parent + nn, is_folder: !!row.dir,
      }, row.dir ? "目录已重命名" : "文件已重命名");
    },
    async copyTorrentInfo(field) {
      this.menu.visible = false;
      const hash = this.menu.hash;
      const m = this.memberByHash.get(hash);
      if (!m) return;
      let value = field === "name" ? m.name
        : field === "hash" ? (m.infohash_v1 || m.hash)
          : (m.magnet_uri || "");
      /* magnet_uri **不在成员索引里**: 只有种子页的平铺 SEED_ITEM 数组带它(见 memberByHash
       * 注释), 而索引优先取分组/未归组条目 —— 那两份都出自后端 _member_view, 没有该字段
       * ⇒ 索引条目恒为 undefined, "复制磁力"曾 100% 落到"该种子没有 magnet 链接"(BUG-9)。
       * 改成**点的时候按需取一次详情**(复用 _editDetail: 抽屉已开则连请求都不发),
       * 而不是给每 1.5~3s 一轮的响应体加一个几十字节的字段(3000 种子 ≈ +0.6MB/轮)。 */
      if (!value && field === "magnet") {
        const d = await this._editDetail(hash);
        value = (d && d.magnet_uri) || "";
      }
      if (!value) {
        this.toast("该种子没有 magnet 链接", "warn");
        return;
      }
      const label = field === "name" ? "种子名" : field === "hash" ? "信息哈希" : "magnet 链接";
      this._copyText(value, label);
    },
    /* ---------------- 种子详情抽屉(R1B: WEB UI 替代 qB 界面的详情面板) ----------------
     * 数据: /api/torrents/{hash} 全字段详情; /trackers /files /peers 按需拉取。
     * trackers/peers 在对应 tab 激活期间 3s 轮询(页面隐藏时暂停), 关闭抽屉即停 —— 不进主循环 tick;
     * General 分组行在 drawerGeneralSections 预格式化(qB 哨兵 -1/-2/8640000 在此统一翻译)。 */
    async openTorrentDrawer(hash) {
      this.menu.visible = false;
      this._stopDrawerPoll();
      this.drawer = {
        open: true, hash, tab: "general", loading: true, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false,
      };
      await this._fetchDrawerDetail();
    },
    closeDrawer() {
      this.drawer.open = false;
      this.filePrio.visible = false;
      this.drawerSelPath = "";
      this._stopDrawerPoll();
    },
    _stopDrawerPoll() {
      if (this._drawerTimer) {
        clearInterval(this._drawerTimer);
        this._drawerTimer = null;
      }
    },
    _startDrawerPoll() {
      this._stopDrawerPoll();
      // P1-4: 3s → 5s。抽屉是观察用途, peers/trackers 秒级变化对操作没有意义;
      // 而每次轮询都要 Web 线程直连 qB(peers 走 sync/torrentPeers, 响应体随 peer 数增长),
      // 在主循环之外额外占用 qB。5s 仍远快于人工观察节奏。
      this._drawerTimer = setInterval(() => {
        if (!this.drawer.open || document.hidden) return;
        if (this.drawer.tab === "trackers") this._fetchDrawerTrackers(true);
        else if (this.drawer.tab === "peers") this._fetchDrawerPeers(true);
      }, 5000);
    },
    async _fetchDrawerDetail() {
      this.drawer.loading = true;
      this.drawer.error = "";
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}`);
        this.drawer.detail = (r && r.torrent) || null;
        if (!this.drawer.detail) this.drawer.error = "种子不存在或已被删除";
      } catch (e) {
        if (!e.auth) this.drawer.error = e.message || "详情获取失败";
      } finally {
        this.drawer.loading = false;
      }
    },
    async _fetchDrawerTrackers(silent = false) {
      if (!silent) this.drawer.trackersLoading = true;
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}/trackers`);
        this.drawer.trackers = Array.isArray(r) ? r : [];
      } catch (e) {
        if (!silent && !e.auth) this.toast("tracker 列表获取失败: " + e.message, "error");
      } finally {
        this.drawer.trackersLoading = false;
      }
    },
    async _fetchDrawerFiles(silent = false) {
      if (!silent) this.drawer.filesLoading = true;
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}/files`);
        this.drawer.files = Array.isArray(r) ? r : [];
      } catch (e) {
        if (!silent && !e.auth) this.toast("文件列表获取失败: " + e.message, "error");
      } finally {
        this.drawer.filesLoading = false;
      }
    },
    async _fetchDrawerPeers(silent = false) {
      if (!silent) this.drawer.peersLoading = true;
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}/peers`);
        this.drawer.peers = r || { peers: [] };
      } catch (e) {
        if (!silent && !e.auth) this.toast("peer 列表获取失败: " + e.message, "error");
      } finally {
        this.drawer.peersLoading = false;
      }
    },
    /* tab 切换: general 重新拉详情(反映最新状态); trackers/peers 拉一次并启动轮询; content 拉一次 */
    drawerTab(tab) {
      if (this.drawer.tab === tab) return;
      this.drawer.tab = tab;
      this.filePrio.visible = false;  // 换页签时收起文件优先级小菜单(内容页签专属)
      this._stopDrawerPoll();
      if (tab === "general") this._fetchDrawerDetail();
      else if (tab === "trackers") {
        this._fetchDrawerTrackers();
        this._startDrawerPoll();
      } else if (tab === "peers") {
        this._fetchDrawerPeers();
        this._startDrawerPoll();
      } else if (tab === "content") this._fetchDrawerFiles();
    },
    /* 抽屉头部动作: 复用 actTorrent(它读 menu.hash 并自带回执/toast) */
    drawerAct(action) {
      this.menu.hash = this.drawer.hash;
      this.actTorrent(action);
    },
    /* 抽屉删除: 复用 delTorrent(确认框流程一致); 删除成功(成员消失)后自动收起抽屉 */
    drawerDel() {
      this.menu.hash = this.drawer.hash;
      this._drawerDeletePending = true;
      Promise.resolve(this.delTorrent()).then(() => {
        if (this._drawerDeletePending && !this.memberByHash.get(this.drawer.hash)) this.closeDrawer();
        this._drawerDeletePending = false;
      });
    },
    /* General tab 分组行(预格式化): qB 哨兵在此统一翻译 —— -1=从未/未设, 8640000=无 ETA。
     * W5-RFB-01 展示重构: 分组重组为 基础/传输/时间/路径, 每行带 sprite 图标(icon)供字段行渲染(f-row) */
    drawerGeneralSections() {
      const d = this.drawer.detail;
      if (!d) return [];
      const dur = (v, dash) => (v === null || v === undefined || v < 0) ? (dash || "未设") : this.fmtDuration(v);
      const ts = (v) => this.fmtTs(v) || "—";  // 抽屉保留"—"(TBL-01 只改主页面表格)
      const size = (v) => this.fmtSizeOrDash(v) || "—";
      const yn = (v) => (v ? "是" : "否");
      const lim = (v) => (v === null || v === undefined || v < 0) ? "未设" : (v === 0 ? "不限" : this.fmtDuration(v));
      return [
        {
          title: "基础",
          sum: `容量 ${size(d.size)} · 分享率 ${(d.ratio ?? 0).toFixed(2)}`,
          rows: [
            { icon: "#i-percent", label: "进度", text: `${((d.progress || 0) * 100).toFixed(1)}%` },
            { icon: "#i-hdd", label: "大小", text: size(d.size) },
            { icon: "#i-layers", label: "总大小", text: size(d.total_size) },
            { icon: "#i-download", label: "剩余量", text: size(d.amount_left) },
            { icon: "#i-pulse", label: "可用性", text: (d.availability ?? 0).toFixed(2) },
            { icon: "#i-percent", label: "分享率", text: (d.ratio ?? 0).toFixed(3) },
            { icon: "#i-lock", label: "私有", text: yn(d.private) },
            // FX-22: 哈希/备注可能极长 -> 块行 + 右侧"复制"(不再只能悬停看 title)
            { icon: "#i-hash", label: "信息哈希 v1", text: d.infohash_v1 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-hash", label: "信息哈希 v2", text: d.infohash_v2 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-columns", label: "分块", text: d.piece_size ? `${d.pieces_have ?? 0} / ${d.pieces_num ?? 0} × ${this.fmtSize(d.piece_size)}` : "—" },
            { icon: "#i-info", label: "已含元数据", text: yn(d.has_metadata) },
            { icon: "#i-calendar", label: "创建于", text: ts(d.creation_date) },
            { icon: "#i-settings", label: "创建工具", text: d.created_by || "—" },
            { icon: "#i-list", label: "备注", text: d.comment || "—", wide: true },
          ],
        },
        {
          title: "传输",
          sum: `实时 ↓${this.fmtSpeedOrDash(d.dlspeed) || "—"} ↑${this.fmtSpeedOrDash(d.upspeed) || "—"}`,
          rows: [
            { icon: "#i-download", label: "下载速度", text: this.fmtSpeedOrDash(d.dlspeed) || "—" },
            { icon: "#i-upload", label: "上传速度", text: this.fmtSpeedOrDash(d.upspeed) || "—" },
            { icon: "#i-hourglass", label: "ETA", text: this.fmtEta(d.eta) || "—" },
            { icon: "#i-download", label: "已下载", text: size(d.downloaded) },
            { icon: "#i-upload", label: "已上传", text: size(d.uploaded) },
            { icon: "#i-download", label: "本次会话下载", text: size(d.downloaded_session) },
            { icon: "#i-upload", label: "本次会话上传", text: size(d.uploaded_session) },
            { icon: "#i-warn", label: "浪费", text: size(d.total_wasted) },
            { icon: "#i-arrow-up", label: "做种", text: String(d.num_seeds ?? 0) },
            { icon: "#i-arrow-down", label: "用户(下载)", text: String(d.num_leechs ?? 0) },
            { icon: "#i-globe", label: "完整/下载中", text: `${d.num_complete ?? 0} / ${d.num_incomplete ?? 0}` },
            { icon: "#i-globe", label: "tracker 数", text: String(d.trackers_count ?? 0) },
            { icon: "#i-link", label: "连接数", text: `${d.connections_count ?? 0} / ${d.connections_limit ?? 0}` },
            { icon: "#i-refresh", label: "下次汇报", text: dur(d.reannounce_in || d.reannounce, "—") },
            { icon: "#i-x-circle", label: "tracker 错误", text: yn(d.has_tracker_error) },
            { icon: "#i-warn", label: "tracker 警告", text: yn(d.has_tracker_warning) },
            { icon: "#i-percent", label: "分享率限制", text: (d.max_ratio ?? -1) < 0 ? "未设" : d.max_ratio.toFixed(2) },
            { icon: "#i-timer", label: "做种时长限制", text: lim(d.max_seeding_time) },
            { icon: "#i-timer", label: "不活跃做种限制", text: lim(d.max_inactive_seeding_time) },
            { icon: "#i-bolt", label: "限制动作", text: d.share_limit_action || "—" },
          ],
        },
        {
          title: "时间",
          sum: `添加 ${ts(d.added_on)}`,
          rows: [
            { icon: "#i-calendar", label: "添加于", text: ts(d.added_on) },
            { icon: "#i-check-circle", label: "完成于", text: ts(d.completion_on) },
            { icon: "#i-eye", label: "见到完整副本", text: ts(d.seen_complete) },
            { icon: "#i-clock", label: "最近活动", text: ts(d.last_activity) },
            { icon: "#i-timer", label: "活跃时间", text: dur(d.time_active, "—") },
            { icon: "#i-timer", label: "做种时间", text: dur(d.seeding_time, "—") },
          ],
        },
        {
          title: "路径",
          sum: `自动种子管理 ${yn(d.auto_tmm)}`,
          // FX-22: 路径行一律块行 + 右侧"打开目录"(走后端 /api/open-path) —— 路径是本页最长、
          // 最常需要"去磁盘上看一眼"的一类值
          rows: [
            { icon: "#i-folder-open", label: "保存路径", text: d.save_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "内容路径", text: d.content_path || "—", wide: true, act: "open" },
            { icon: "#i-folder-open", label: "下载路径", text: d.download_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "根路径", text: d.root_path || "—", wide: true, act: "open" },
            { icon: "#i-sliders", label: "自动种子管理", text: yn(d.auto_tmm) },
            { icon: "#i-play", label: "强制开始", text: yn(d.force_start) },
            { icon: "#i-upload", label: "超级做种", text: yn(d.super_seeding) },
            { icon: "#i-sort", label: "顺序下载", text: yn(d.seq_dl) },
            { icon: "#i-bolt", label: "首末块优先", text: yn(d.f_l_piece_prio) },
          ],
        },
      ];
    },
    /* FX-22: 字段行图标着色 —— 由**图标名派生**色调类, 而不是给 48 行逐个加 tone 字段:
     * 图标本身已隐含语义(下载/上传/日历/文件夹/哈希...), 派生表是单点, 新增行自动生效。
     * 色值全在 views.css 的 .ico-t-* 族里走主题令牌。 */
    icoTone(icon) {
      const map = {
        "#i-download": "ico-t-io", "#i-upload": "ico-t-io", "#i-arrow-up": "ico-t-io", "#i-arrow-down": "ico-t-io",
        "#i-hdd": "ico-t-cap", "#i-layers": "ico-t-cap", "#i-columns": "ico-t-cap",
        "#i-calendar": "ico-t-time", "#i-clock": "ico-t-time", "#i-timer": "ico-t-time",
        "#i-hourglass": "ico-t-time", "#i-eye": "ico-t-time",
        "#i-globe": "ico-t-site", "#i-link": "ico-t-site",
        "#i-lock": "ico-t-sw", "#i-sliders": "ico-t-sw", "#i-play": "ico-t-sw", "#i-sort": "ico-t-sw",
        "#i-bolt": "ico-t-sw", "#i-settings": "ico-t-sw", "#i-refresh": "ico-t-sw",
        "#i-hash": "ico-t-id", "#i-info": "ico-t-id", "#i-tag": "ico-t-id", "#i-list": "ico-t-id",
        "#i-folder": "ico-t-path", "#i-folder-open": "ico-t-path",
        "#i-percent": "ico-t-state", "#i-pulse": "ico-t-state", "#i-check-circle": "ico-t-state",
        "#i-x-circle": "ico-t-state", "#i-warn": "ico-t-state",
      };
      return map[icon] || "";
    },
    /* Content tab: qB files[].name 为 '/' 分隔相对路径 -> 构树后扁平化(缩进渲染);
     * 目录行聚合大小; 文件行展示 进度/优先级(0=跳过 1=普通 4|6=高 7=最高), 优先级可点改(小菜单);
     * 每行带 index(种子内原始下标, files/priority 用)与 path(完整相对路径, 选中/rename-fs 用) */
    drawerFileRows() {
      const files = this.drawer.files || [];
      const root = { dirs: new Map(), files: [], size: 0, path: "" };
      for (let fi = 0; fi < files.length; fi++) {
        const f = files[fi];
        const parts = String(f.name || "").split("/").filter(Boolean);
        let node = root;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!node.dirs.has(parts[i])) {
            node.dirs.set(parts[i], { dirs: new Map(), files: [], size: 0, path: node.path ? node.path + "/" + parts[i] : parts[i] });
          }
          node = node.dirs.get(parts[i]);
          node.size += f.size || 0;
        }
        node.files.push({ ...f, index: fi });
      }
      const prio = (p) => ({ 0: "跳过", 1: "普通", 4: "高", 6: "高", 7: "最高" }[p] ?? "普通");
      const rows = [];
      const walk = (node, name, depth) => {
        if (name !== null) rows.push({ depth, dir: true, name, path: node.path, text: this.fmtSize(node.size) });
        for (const [dn, d] of node.dirs) walk(d, dn, name === null ? 0 : depth + 1);
        for (const f of node.files) {
          const last = String(f.name || "").split("/").pop();
          rows.push({
            depth: name === null ? 0 : depth + 1, dir: false,
            name: last,
            path: node.path ? node.path + "/" + last : last,
            index: f.index,
            text: this.fmtSize(f.size), progress: Math.round((f.progress || 0) * 100),
            prio: prio(f.priority), skipped: f.priority === 0,
          });
        }
      };
      walk(root, null, -1);
      return rows;
    },
    /* Peers tab: qB 响应 peers 可能为 dict(以 ip:port 为键)或数组 —— 双形态归一 */
    drawerPeerRows() {
      const p = this.drawer.peers || {};
      const list = Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
      return list.map((x) => ({
        addr: `${x.ip || "?"}${x.port ? ":" + x.port : ""}`,
        client: x.client || "—",
        flags: x.flags || "—",
        progress: Math.round((x.progress || 0) * 100),
        dlspeed: this.fmtSpeedOrDash(x.dlspeed || 0) || "—",  // 抽屉 peers 表保留"—"
        upspeed: this.fmtSpeedOrDash(x.upspeed || 0) || "—",
        downloaded: this.fmtSizeOrDash(x.downloaded || 0) || "—",
        uploaded: this.fmtSizeOrDash(x.uploaded || 0) || "—",
        relevance: `${Math.round((x.relevance || 0) * 100)}%`,
      }));
    },
    drawerTrackerStatus(s) {
      return { 0: "未启用", 1: "未连接", 2: "正常", 3: "更新中", 4: "未连接" }[s] ?? "—";
    },
    drawerTrackerVirtual(url) {
      const u = String(url || "");
      return u.startsWith("**") || ["[DHT]", "[PeX]", "[LSD]"].some((p) => u.startsWith(p));
    },
    /* 删除单个种子: 确认框显示种子名/站点/状态/路径/大小 + 两个选项 */
    async delTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      let m = null;
      for (const g of this.filteredGroups) {
        const hit = (g.members || []).find((x) => x.hash === hash);
        if (hit) {
          m = hit;
          break;
        }
      }
      if (!m) m = this.singles.find((x) => x.hash === hash) || null;  // 单种子视图里的未归组种子
      if (!m) m = this.torrents.find((x) => x.hash === hash) || null;  // 种子页平铺数组(全量兑底)
      if (!m) return;
      // FX-16: 删除链统一 —— 走 _deleteFlow(目标明细 + 汇报前置 + 等聚合回执 + 收尾清选择)
      // R10-16: 不再自传 details(条目与右键/批量/整集同构)
      await this._deleteFlow({
        keys: [],
        hashes: [hash],
        title: "删除该种子",
        body: "将删除该种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。",
        countText: "该种子",
        label: m.name || hash.slice(0, 12),
      });
    },
    /* ---------------- 统计面板(FE-2C): 全局状态(server_state, 缺失显示 —) ----------------
     * 数据源随 /api/state.status.server 每轮回传(见 refresh()), 状态栏常显统计直接取
     * `statsServer`; 打开面板 / 卡内"刷新"按钮才走 /api/stats 重取一次(统计是低频信息,
     * 且"刷新"按钮语义上就该真的发一次请求)。server 为 null(qB 未同步/降级全量不可用)
     * 时空态文案; 请求失败给重试。
     */
    async openStats() {
      this.statsOpen = true;
      await this.loadStats();
    },
    closeStats() {
      this.statsOpen = false;
    },
    async loadStats() {
      this.statsLoading = true;
      this.statsError = "";
      try {
        const r = await this.api("/api/stats");
        this.statsServer = r.server || null;
      } catch (e) {
        if (!e.auth) this.statsError = e.message || "加载失败";
        // FIX-04b: 失败不清空已有数据(骨架常驻防闪烁); 仅首次加载失败保持 null → 错误占位重试
      } finally {
        this.statsLoading = false;
      }
    },
    /* 统计值兜底: 字段缺失(null/undefined)显示 —; 0 是合法值(如 DHT 0 节点)原样展示 */
    statVal(v, fmt) {
      if (v === null || v === undefined || v === "") return "—";
      return fmt ? fmt(v) : String(v);
    },
    /* qB connection_status 文案(原值兜底; 缺失显示 —) */
    connText(v) {
      if (v === null || v === undefined || v === "") return "—";
      return { connected: "已连接", firewalled: "已连接(防火墙限制)", disconnected: "未连接" }[v] || String(v);
    },
    /* ---------------- 分类/标签管理对话框(FE-2C2): qB 分类/标签的增删改 ----------------
     * 列表数据源 GET /api/categories|tags; 写操作走 POST /api/categories(/edit|/remove) 与 /api/tags(/remove)。
     * CRUD 成功后重拉列表刷新对话框; 对话框关闭后主列表随下一轮 rid 轮询自然更新(不强刷)。
     */
    openMgr(kind) {
      this.filterMenu = "";  // 从筛选弹层进入: 先收起弹层再开对话框
      this.mgrOpen = kind;
      this.mgrCategories = [];
      this.mgrTags = [];
      this.mgrNewCatName = "";
      this.mgrNewCatPath = "";
      this.mgrNewTags = "";
      this.mgrError = "";
      this.loadMgr();
    },
    closeMgr() {
      if (this.mgrBusy) return;  // 写操作回执等待期不允许误关
      this.mgrOpen = "";
    },
    async loadMgr() {
      this.mgrLoading = true;
      this.mgrError = "";
      try {
        if (this.mgrOpen === "category") {
          // qB categories: {名字: {save_path, ...}} → 行数组(名字字典序)
          const r = await this.api("/api/categories");
          const cats = r.categories || {};
          this.mgrCategories = Object.keys(cats)
            .map((name) => ({ name, save_path: (cats[name] && cats[name].save_path) || "" }))
            .sort((a, b) => a.name.localeCompare(b.name));
        } else {
          const r = await this.api("/api/tags");
          this.mgrTags = (r.tags || []).slice().sort((a, b) => a.localeCompare(b));
        }
      } catch (e) {
        if (!e.auth) this.mgrError = e.message || "加载失败";
      } finally {
        this.mgrLoading = false;
      }
    },
    async submitMgrCategory() {
      if (this.mgrBusy) return;  // 回车提交与按钮同源: 防回执等待期重复投递
      const name = this.mgrNewCatName.trim();
      if (!name) { this.toast("分类名称不能为空", "warn"); return; }
      this.mgrBusy = true;
      try {
        const payload = { name };
        const savePath = this.mgrNewCatPath.trim();
        if (savePath) payload.save_path = savePath;  // 可空: 留空 = 仅建分类不带路径
        await this.api("/api/categories", { method: "POST", body: JSON.stringify(payload) });
        this.toast(`已创建分类: ${name}`, "ok", 2500);
        this.mgrNewCatName = "";
        this.mgrNewCatPath = "";
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`创建分类失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async submitMgrTags() {
      if (this.mgrBusy) return;  // 回执等待期防重复投递
      // 支持中英文逗号分隔批量创建(空段剔除; 与添加种子对话框的标签口径一致)
      const tags = this.mgrNewTags.split(/[,,]/).map((t) => t.trim()).filter(Boolean);
      if (!tags.length) { this.toast("请输入至少一个标签", "warn"); return; }
      this.mgrBusy = true;
      try {
        await this.api("/api/tags", { method: "POST", body: JSON.stringify({ tags }) });
        this.toast(`已创建 ${tags.length} 个标签`, "ok", 2500);
        this.mgrNewTags = "";
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`创建标签失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async mgrEditCatPath(name) {
      const cur = (this.mgrCategories.find((c) => c.name === name) || {}).save_path || "";
      const p = await this.promptDialog("修改分类保存路径", cur, {
        body: `分类: ${name}`, placeholder: "如 D:\\Torrents\\TV", okText: "保存",
      });
      if (p === null) return;  // 取消/遮罩/Esc 均不写
      const savePath = p.trim();
      if (!savePath) { this.toast("保存路径不能为空", "warn"); return; }
      if (savePath === cur) { this.toast("未作修改", "ok", 2000); return; }
      this.mgrBusy = true;
      try {
        await this.api("/api/categories/edit", { method: "POST", body: JSON.stringify({ name, save_path: savePath }) });
        this.toast(`已更新分类路径: ${name}`, "ok", 2500);
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`修改分类路径失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async mgrDeleteCategory(name) {
      const ok = await this.confirmDialog("删除分类", `将删除分类「${name}」(不删除种子与文件)`, { okText: "删除", danger: true });
      if (!ok) return;
      this.mgrBusy = true;
      try {
        await this.api("/api/categories/remove", { method: "POST", body: JSON.stringify({ names: [name] }) });
        this.toast(`已删除分类: ${name}`, "ok", 2500);
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`删除分类失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async mgrDeleteTag(tag) {
      const ok = await this.confirmDialog("删除标签", `将删除标签「${tag}」(自动规则可能重新打上)`, { okText: "删除", danger: true });
      if (!ok) return;
      this.mgrBusy = true;
      try {
        await this.api("/api/tags/remove", { method: "POST", body: JSON.stringify({ tags: [tag] }) });
        this.toast(`已删除标签: ${tag}`, "ok", 2500);
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`删除标签失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    /* ---------------- 日志页(FE-2C): /api/log 只读 tail(等级过滤 + 行数选择 + 手动刷新, 不轮询) ---------------- */
    async openLogs() {
      // W4: 日志迁入设置页"运行日志"章节; 顶层 page 收敛为 groups/settings, 不再有 'logs'
      await this.openSettings();
      this.cfg.activeGroup = "__logs";
      if (!this.logs.loaded) await this.loadLogs();
    },
    async loadLogs() {
      this.logs.loading = true;
      this.logs.error = "";
      try {
        const q = new URLSearchParams({ lines: String(this.logs.num || 300) });
        if (this.logs.level) q.set("level", this.logs.level);
        const r = await this.api(`/api/log?${q.toString()}`);
        this.logs.lines = r.lines || [];
        this.logs.file = r.file || "";
        this.logs.loaded = true;
      } catch (e) {
        if (!e.auth) this.logs.error = e.message || "日志加载失败";
      } finally {
        this.logs.loading = false;
      }
    },
    /* ---------------- 限速托管状态与临时覆盖(FE-2C D2) ----------------
     * /api/speed/mode 只读快照; /api/speed/override 两方向都必填(0=不限),
     * 曲线启用时覆盖是临时的(下一档位切换即恢复), 停用时为常态设置。
     */
    async loadSpeedMode(force = false) {
      if (this.speedMode.loaded && !force) return;
      try {
        const r = await this.api("/api/speed/mode");
        this.speedMode = {
          loaded: true,
          curveEnabled: !!r.curve_enabled,
          target: r.curve_target || null,
          current: r.current || null,
          error: "",
        };
      } catch (e) {
        if (!e.auth) this.speedMode.error = e.message || "状态获取失败";
      }
    },
    async submitSpeedOverride() {
      if (!this.speedOvReady || this.speedOverride.busy) return false;
      const up = Math.max(0, Math.round(Number(this.speedOverride.up)));
      const down = Math.max(0, Math.round(Number(this.speedOverride.down)));
      const text = `上 ${this.fmtLimit(up) || "不限速"} / 下 ${this.fmtLimit(down) || "不限速"}`;  // toast 保留"不限速"字样(TBL-02)
      this.speedOverride.busy = true;
      try {
        const resp = await this.api("/api/speed/override", {
          method: "POST",
          body: JSON.stringify({ upload_kib: up, download_kib: down }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(`已临时覆盖全局限速: ${text}`, "ok", 3000);
          this.speedOverride = { up: "", down: "", busy: false };
          await this.loadSpeedMode(true);  // 覆盖后刷新托管状态(qB 当前值已变)
          return true;  // SPD-04: 供弹窗判断成功关窗
        } else {
          this.toast(`限速覆盖失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!e.auth) this.toast("限速覆盖发送失败: " + e.message, "error");
      } finally {
        this.speedOverride.busy = false;
      }
      return false;
    },
    /* ---------------- 限速修改浮层(SPD-04; FX-08 改为**就近弹出**) ----------------
     * FX-08: 不再居中 + 遮罩弹出, 而是锚在点击的"限制速度"按钮附近向上弹(该方向输入框预聚焦),
     * 位置夹取到视口内(左右各留 12px), 不会跑到屏幕外; 点空白/Esc 关闭(无遮罩, 页面其余部分仍可操作)。
     * 打开时取一次 /api/speed/mode 并回填 qB 当前生效值(KiB/s, 0 = 不限); 提交沿用 submitSpeedOverride,
     * 成功即关窗, 失败留在窗内看报错并重试。
     */
    async openSpeedAt(ev, dir) {
      const el = ev && ev.currentTarget;
      const rect = el && el.getBoundingClientRect ? el.getBoundingClientRect() : null;
      const W = 380;  // 与 .speed-pop 的 width 单点一致
      const left = rect ? rect.left - 12 : window.innerWidth - W - 12;
      this.speedAt = { left, dir: dir === "down" ? "down" : "up" };
      this.speedOpen = true;
      await this.loadSpeedMode(true);  // 开窗取当前值(强制刷新, 不吃缓存)
      const c = this.speedMode.current || {};
      const pick = (v) => (v === undefined || v === null ? "" : String(v));
      this.speedOverride.up = pick(c.upload_limit);
      this.speedOverride.down = pick(c.download_limit);
      this.$nextTick(() => {
        // 只在当前方向预聚焦(点击"限制速度"就是为改这一方向), 并全选便于直接覆写
        const inp = this.$refs.speedPop && this.$refs.speedPop.querySelector("#sp-" + this.speedAt.dir);
        if (inp) {
          inp.focus();
          inp.select();
        }
      });
    },
    /* 浮层内联定位: 只写 left(纵向由 CSS 锚定状态栏上缘), 并夹取到视口内 */
    speedPopStyle() {
      const W = 380, PAD = 12;
      return { left: Math.max(PAD, Math.min(this.speedAt.left, window.innerWidth - W - PAD)) + "px" };
    },
    /* 旧入口(居中弹窗)保留为薄包装: 无点击坐标时锚在视口右侧(第三方链接/键盘触发路径) */
    openSpeedDialog() {
      return this.openSpeedAt(null, "up");
    },
    closeSpeedDialog() {
      this.speedOpen = false;
      this.speedAt = { left: 0, dir: "up" };
    },
    async submitSpeedDialog() {
      const ok = await this.submitSpeedOverride();
      if (ok) this.speedOpen = false;
    },
    /* ---------------- 历史流量弹层(今日流量面板入口; 天/月/年切换 + 悬停取值) ---------------- */
    async openHistory() {
      this.historyOpen = true;
      await this.loadHistory();
    },
    async loadHistory() {
      this.historyLoading = true;
      this.historyError = "";
      try {
        const data = await this.api("/api/traffic/history");
        this.historyData = data.history || [];
      } catch (e) {
        if (!e.auth) this.historyError = e.message || "加载失败";
      } finally {
        this.historyLoading = false;
      }
    },
    /* 悬停追踪: 事件挂在 .hist-chart容器(mousemove), 指针 x 折算进 viewBox 坐标再换算
     * 桶索引 —— 连续无空隙; 旧版逐桶 enter/leave + 命中区只盖单柱的闪烁根因即在此 */
    histMove(ev) {
      if (!this.historyBuckets.length) return;
      const rect = ev.currentTarget.getBoundingClientRect();
      const g = this.histGeom;
      const x = ((ev.clientX - rect.left) / rect.width) * g.w;
      const idx = Math.floor((x - g.padL) / g.bw);
      this.histHoverIdx = Math.max(0, Math.min(this.historyBuckets.length - 1, idx));
    },
    histLeave() {
      this.histHoverIdx = -1;
    },
    /* 面积填充路径(折线下方淡渐染; 带参辅助放 methods —— pitfalls: computed不能加括号调用) */
    _histArea(key) {
      const pts = this.histSeries[key];
      if (!pts.length) return "";
      const base = (this.histGeom.padT + this.histGeom.chartH).toFixed(1);
      return `${this.histPaths[key]} L ${pts[pts.length - 1].x.toFixed(1)} ${base} L ${pts[0].x.toFixed(1)} ${base} Z`;
    },
    gridStyle(page) {
      // 列模板由 computed 缓存(见 *_Grid): 行渲染只取同一引用, 不每行拼字符串
      return { group: this.groupGrid, detail: this.detailGrid, torrent: this.torrentGrid, show: this.showGrid }[page];
    },

    /* ------------------------------------------------ 列状态(宽/隐/自适应) */

    _visibleCols(page) {
      const hidden = this.colHidden[page] || [];
      const defs = TABLE_COLUMNS[page];
      const order = this.colOrder[page];
      if (!order || !order.length) return defs.filter((c) => !hidden.includes(c.key));  // 无自定义序 = 定义序(向后兼容)
      // 按 colOrder 输出; 未入序的列(新增/残留 key)按定义序补尾 —— 宽/隐仍按列 key 对应, 换序不丢宽度
      const rest = new Map(defs.map((c) => [c.key, c]));
      const out = [];
      for (const k of order) {
        const c = rest.get(k);
        if (!c) continue;
        rest.delete(k);
        if (!hidden.includes(k)) out.push(c);
      }
      for (const c of defs) if (rest.has(c.key) && !hidden.includes(c.key)) out.push(c);
      return out;
    },
    /* 列模板: 有 px 覆盖用覆盖值, 否则用默认模板(仅首次渲染会出现这种混合态) */
    _gridTemplate(page) {
      const w = this.colWidths[page] || {};
      return this._visibleCols(page).map((c) => w[c.key] || c.tpl).join(" ");
    },
    /* 从列头行(真正的 grid 容器)读取**当前渲染**的列宽 px; 列数不符(渲染未完成)返回 null */
    _renderedWidths(headEl, page) {
      const rendered = (getComputedStyle(headEl).gridTemplateColumns || "")
        .split(" ")
        .map((v) => parseFloat(v))
        .filter((v) => !isNaN(v) && v > 0);
      const vis = this._visibleCols(page);
      if (rendered.length !== vis.length) return null;
      const out = {};
      vis.forEach((c, i) => {
        out[c.key] = Math.round(rendered[i]) + "px";
      });
      return out;
    },
    _headEl(page) {
      const ref = this.$refs[{ group: "groupHead", detail: "detailHead", torrent: "torrentHead", show: "showHead" }[page]];
      return Array.isArray(ref) ? ref[0] : ref || null;
    },
    /* 列对齐规则注入(单例 <style id="col-align-css">): 首次创建后只改 textContent ——
     * 不能重建元素: 重建会让它排到 <head> 末尾的其它运行时样式之后, 层叠顺序不再稳定。 */
    _syncColAlignCss() {
      const css = this.colAlignCss;
      if (css === this._colAlignCss) return;
      this._colAlignCss = css;
      let el = document.getElementById("col-align-css");
      if (!el) {
        el = document.createElement("style");
        el.id = "col-align-css";
        document.head.appendChild(el);
      }
      el.textContent = css;
    },
    /* 顶栏(+状态分布条)的实测高度写入 :root 的 --head-h: 吸顶元素的偏移与最大可用
     * 高度都依赖它。**不写死数值** —— 高度会随媒体查询、状态条是否渲染、窄屏折行而变化;
     * 值未变时直接返回, 避免每帧都写一次 CSS 变量(updated 会频繁触发)。
     */
    _syncHeadHeight() {
      const el = document.querySelector(".sticky-head");
      const h = el ? Math.round(el.getBoundingClientRect().height) : 0;
      if (h === this._headH) return;
      this._headH = h;
      document.documentElement.style.setProperty("--head-h", h + "px");
    },
    /* P1-3: 用 ResizeObserver 取代"每次渲染量一次顶栏"。
     * - 观察 .sticky-head 的**盒尺寸**: 状态条是否渲染 / 窄屏折行 / 批量段并入都会改高度, 都会被捕获;
     * - 回调用 rAF 合并写入(同一帧多次变化只量一次);
     * - 元素被 v-if 换掉时(引用变化)重新挂观察器并立即量一次 —— 这是唯一仍走同步路径的时机,
     *   而且只在元素真的换了才发生, 不是每帧。
     * 降级: 无 ResizeObserver(很老的浏览器)时退回"每次渲染同步一次", 行为与改动前一致。 */
    _ensureHeadObserver() {
      if (typeof ResizeObserver === "undefined") {
        this._syncHeadHeight();
        return;
      }
      const el = document.querySelector(".sticky-head");
      // 字段名不能叫 _headEl: 与下方取表头元素的方法 `_headEl(page)` 同名(data 与 methods 共命名空间)
      if (el === this._headObsEl) return;  // 元素没换: 什么都不做(不触发任何布局读取)
      this._headObsEl = el;
      if (this._headObs) {
        this._headObs.disconnect();
        this._headObs = null;
      }
      if (!el) return;
      this._headObs = new ResizeObserver(() => this._queueHeadSync());
      this._headObs.observe(el);
      this._queueHeadSync();  // 新元素: 立刻量一次拿到初值
    },
    _queueHeadSync() {
      if (this._headRaf) return;  // 同一帧内多次变化合并为一次
      this._headRaf = requestAnimationFrame(() => {
        this._headRaf = 0;
        this._syncHeadHeight();
      });
    },
    /* ---------------- P1-2 行窗口化 ----------------
     * 模板只消费三个产物: 可见切片、上占位高、下占位高。窗口关闭时 == 全量渲染(零差异回退)。 */
    _winContainer(kind, refName) {
      if (refName) return this.$refs[refName] || null;
      // 成员行: 容器 = .detail —— 明细表头(ref="detailHead")的父元素
      const head = this.$refs.detailHead;
      return head && head.parentElement ? head.parentElement : null;
    },
    /* 行容器的**真实**行间距(px): 三个容器并不相同 —— atlas `.group-table` 是 6px、
     * prism 是 5px、成员容器 `.detail` 是块级容器(没有 flex gap = 0)。硬编码任何一个值
     * 都会让另外两层的占位总高失真, 所以一律读计算样式实测(见文件头 BUG-1 注释)。
     * 块级容器的 rowGap 计算值是 "normal" ⇒ parseFloat 得 NaN ⇒ 回落 0, 正是我们要的值。
     * ❗返回 **null = 容器当前没渲染**(如种子页未打开时问 .group-table) —— 调用方**不得**
     * 把它当 0 缓存: 否则在分组页问一次就把种子页的间距永久记成 0(实测占位总高少 5px×2999)。 */
    _winGapOf(kind) {
      const el = kind === "torrent" ? this._winContainer(kind, "torrentTable")
        : kind === "group" ? this._winContainer(kind, "groupTable")
          : this._winContainer(kind, null);
      if (!el) return null;
      if (typeof getComputedStyle !== "function") return ROW_WIN_GAP_FALLBACK;
      const g = parseFloat(getComputedStyle(el).rowGap);
      return Number.isFinite(g) ? g : 0;
    },
    /* 取该层的行间距(带缓存)。容器未渲染时返回 null, 由调用方决定回退策略。 */
    _winGapFor(kind) {
      if (this._winGap[kind] === undefined) {
        const g = this._winGapOf(kind);
        if (g === null) return null;
        this._winGap[kind] = g;
      }
      return this._winGap[kind];
    },
    _winSigExtra() {
      // 会改变"容器上方内容高度"的因子: 状态分布条是否渲染 / 搜索态 / 筛选态
      return `${this.distTotal ? 1 : 0}${this.searchQuery && this.searchQuery.trim() ? 1 : 0}${this.filtersActive ? 1 : 0}`;
    },
    /* 容器顶边相对文档的偏移: 只在签名变化时读一次(getBoundingClientRect = 强制同步布局,
     * 每帧读会把 P1-3 的收益又吐回去)。签名含 lastRid ⇒ 每轮数据最多读一次。 */
    _ensureWinTop() {
      const base = `${this.viewMode}|${this.page}|${this._winResize}|${this._winSigExtra()}|${this.lastRid}`;
      for (const kind of ["torrent", "group", "member"]) {
        const sig = `${base}|${kind}`;
        if (this._winTopSig[kind] === sig) continue;
        const el = kind === "torrent" ? this._winContainer(kind, "torrentTable")
          : kind === "group" ? this._winContainer(kind, "groupTable")
            : this._winContainer(kind, null);
        this._winTop[kind] = el ? el.getBoundingClientRect().top + window.scrollY : 0;
        this._winTopSig[kind] = sig;
      }
    },
    /* 行高: **逐行实测**(不是采样几行取均值)。行高本就不齐(带 H&R 要求的行多一行),
     * 用"等高"近似会在几千行上累积成上百像素漂移 —— 表现为滚到底够不着、滚动条长度不对。
     * 首次(或列集合变化后)由一轮**全量渲染**量齐所有行, 之后每轮只更新当前窗口里的行。 */
    _measureRowH() {
      if (!this.rowWin) return;
      const sig = `${this.viewMode}|${this._winResize}|${this.visibleGroupCols.length}|${this.visibleTorrentCols.length}|${this.visibleDetailCols.length}`;
      // ❗用 getBoundingClientRect().height 而不是 offsetHeight: 后者取整, 0.4px 的误差 ×
      // 3000 行就是 1200px 的漂移。
      const probes = [["torrent", ".torrent-row[data-hash]"], ["group", ".group-row:not(.torrent-row)[data-key]"], ["member", ".member-row[data-hash]"]];
      for (const [kind, sel] of probes) {
        if (this._rowHSig[kind] !== sig) {
          // 列集合/窗口宽变了: 旧高度作废, 下一轮走全量重新量齐(只多付一次全量渲染)
          for (const k of Object.keys(this._rowHs)) {
            if (k.startsWith(kind + ":")) delete this._rowHs[k];
          }
          this._rowHSig[kind] = sig;
          this._winMeasured[kind] = false;
          this._rowHVer++;
          continue;
        }
        const rows = document.querySelectorAll(sel);
        if (!rows.length) continue;
        let sum = 0, changed = false;
        for (const r of rows) {
          const h = r.getBoundingClientRect().height;
          const key = kind + ":" + (r.getAttribute("data-hash") || r.getAttribute("data-key") || "");
          if (this._rowHs[key] === undefined || Math.abs(this._rowHs[key] - h) > 0.5) {
            this._rowHs[key] = h;
            changed = true;
          }
          sum += h;
        }
        const avg = sum / rows.length;  // 未量过的行(新种子)用它兜底
        if (this._rowH[kind] === undefined || Math.abs(this._rowH[kind] - avg) > 0.01) {
          this._rowH = { ...this._rowH, [kind]: avg };
          changed = true;
        }
        if (!this._winMeasured[kind]) {
          this._winMeasured[kind] = true;  // 这一轮是全量渲染, 高度已量齐
          changed = true;
        }
        if (changed) this._rowHVer++;  // 响应式: 让窗口按新高度重算
      }
    },
    _rowKeyOf(kind, item) {
      return kind + ":" + (kind === "group" ? item.key : item.hash);
    },
    /* 前缀和 y(i) = 第 i 行的顶边偏移(含行间距)。每帧重算: 3000 次加法 ≈ 0.03ms,
     * 比维护"失效缓存 + 增量更新"简单得多, 也不会因为漏失效而算错。 */
    _rowWindow(kind, list, refName) {
      const n = list.length;
      const off = { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      void this._rowHVer;  // 依赖: 行高表更新后重算
      if (!this.rowWin || n < ROW_WIN_MIN || this._winViewH <= 0) return off;
      // 行高还没量齐 -> 这一轮先全量渲染(首轮/改列之后各一次), 下次就走窗口了
      if (!this._winMeasured[kind]) return off;
      const est = this._rowH[kind] || ROW_WIN_EST_H[kind];
      // 行间距实测(见 _winGapFor); 容器还没渲染时本轮先全量, 免得按错的间距撑占位
      const gap = this._winGapFor(kind);
      if (gap === null) return off;
      const hs = this._rowHs;
      const pre = new Array(n + 1);
      pre[0] = 0;
      let y = 0;
      for (let i = 0; i < n; i++) {
        const h = hs[this._rowKeyOf(kind, list[i])];
        y += (h === undefined ? est : h) + gap;
        pre[i + 1] = y;
      }
      const rel = this._winScrollY - (this._winTop[kind] || 0);
      let start = this._prefixFloor(pre, rel) - ROW_WIN_OVERSCAN;
      let end = this._prefixFloor(pre, rel + this._winViewH) + 1 + ROW_WIN_OVERSCAN;
      if (!(start >= 0) || start > n) start = 0;
      if (!(end > 0) || end > n) end = n;
      if (start >= end) return off;  // 数值异常: 宁可全渲染, 也不渲染"空窗口"
      // 占位两侧各多出一个 gap(顶替了行块内部原有的间距), 故减一个 gap 对齐
      return {
        active: true, start, end,
        padTop: start > 0 ? pre[start] - gap : 0,
        padBottom: end < n ? pre[n] - gap - pre[end] : 0,
      };
    },
    _prefixFloor(pre, y) {
      // 最大的 i 使 pre[i] <= y(pre 单调不减, 二分)
      let lo = 0, hi = pre.length - 1;
      while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (pre[mid] <= y) lo = mid;
        else hi = mid - 1;
      }
      return lo;
    },
    _onWinScroll() {
      if (this._winRaf) return;
      this._winRaf = requestAnimationFrame(() => {
        this._winRaf = 0;
        this._winScrollY = window.scrollY;
      });
    },
    _onWinResize() {
      this._winResize++;
      this._winViewH = window.innerHeight;
      this._winScrollY = window.scrollY;
    },
    /* 搜索命中高亮: 种子页不再逐条复制出 hit 字段(见 filteredTorrents), 高亮由模板现问现用 */
    isHit(row) {
      return !!row && this.searchHits.has(row.hash);
    },
    /* 模板用: 成员行切片(展开明细)。窗口未启用时原样返回, 与改动前完全等价 */
    winMembers(list) {
      const rows = this.sortedMembers(list);
      const w = this.memberWin(list);
      return w.active ? rows.slice(w.start, w.end) : rows;
    },
    /* 把默认模板"实体化"为 px:
     * - 未手动调过 -> 每次窗口变化后重新实体化(保留"填满容器 + 自适应"的观感)
     * - 手动调过   -> 跳过(冻结, 拖一列不再动其它列)
     */
    materializeColumns() {
      for (const page of ["group", "detail", "torrent", "show"]) {
        if (this.colManual[page]) continue;
        const headEl = this._headEl(page);
        if (!headEl) continue;
        const widths = this._renderedWidths(headEl, page);
        if (widths) this.colWidths = { ...this.colWidths, [page]: widths };
      }
    },
    saveColState() {
      // 写失败(私隐模式/配额满)不得影响功能: 本次会话内的调整仍在内存里生效
      try {
        localStorage.setItem(
          COLS_STORE_KEY,
          JSON.stringify({ widths: this.colWidths, hidden: this.colHidden, manual: this.colManual, order: this.colOrder })
        );
      } catch { /* 忽略: 仅失去跨会话记忆 */ }
    },
    colVisible(page, key) {
      return !(this.colHidden[page] || []).includes(key);
    },
    toggleColumn(page, key) {
      const col = columnDef(page, key);
      if (!col || col.locked) return;  // locked 列不可隐藏(模板中不渲染其勾选框, 这里是双保险)
      const cur = this.colHidden[page] || [];
      const hidden = cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key];
      this.colHidden = { ...this.colHidden, [page]: hidden };
      // 已手动调过: 新显示的列需要一个 px 宽度才能维持"只改一列"的策略
      if (this.colManual[page] && !hidden.includes(key)) {
        const widths = { ...(this.colWidths[page] || {}) };
        if (!widths[key]) {
          widths[key] = templateMinPx(col.tpl) + "px";
          this.colWidths = { ...this.colWidths, [page]: widths };
        }
      }
      this.saveColState();
      this.$nextTick(() => this.materializeColumns());
    },
    resetAllColumnWidths(page) {
      // 恢复默认列宽: 清空 px 覆盖与手动标记 -> 回到默认弹性模板并重新实体化
      const widths = { ...(this.colWidths[page] || {}) };
      for (const c of TABLE_COLUMNS[page]) delete widths[c.key];
      this.colWidths = { ...this.colWidths, [page]: widths };
      this.colManual = { ...this.colManual, [page]: false };
      this.saveColState();
      this.$nextTick(() => this.materializeColumns());
    },
    fitColumnsToWindow(page) {
      // 适应窗口宽度: 先回到默认弹性模板(它会重新填满容器), 下一帧固化 —— 等价按比例缩放填满
      this.colWidths = { ...this.colWidths, [page]: {} };
      this.colManual = { ...this.colManual, [page]: false };
      this.$nextTick(() => {
        this.materializeColumns();
        this.colManual = { ...this.colManual, [page]: true };
        this.saveColState();
      });
    },

    /* 列宽拖拽: 拖某列**只改该列**
     *
     * 关键在于起始时把**全部可见列**固化为当前渲染 px —— 它们原本可能是 minmax/fr 弹性值,
     * 不固化的话被拖列会把余量从邻居那儿抢走(表现为"调一列, 其它列跟着变")。
     * 按住 Shift 拖拽 = 与相邻列互相挤占(总宽不变), 对应主流表格的 shift-resize。
     *
     * 拖拽抑制误触排序: resizer 与 .h-cell 共父级, mouseup 后浏览器仍派发 click 冒泡到
     * .h-cell 触发 setSort(用户感知为"调列宽顺手把排序变了")。这里累计位移超过阈值时,
     * 在 capture 阶段拦截下一次 click(stopPropagation+preventDefault), 拦完即注销。
     * 未拖动(纯点击 resizer)不拦截, 保持原行为。
     */
    startResize(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const widths = this._renderedWidths(headEl, page);
      if (!widths) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const startX = event.clientX;
      const startVal = parseFloat(widths[key]);
      const neighbor = event.shiftKey ? vis[idx + 1] : null;
      const startNeighbor = neighbor ? parseFloat(widths[neighbor.key]) : 0;
      let dragged = false;  // 位移超过 RESIZE_DRAG_THRESHOLD 即置真, up 时用于决定是否拦 click
      const move = (e) => {
        if (!dragged && Math.abs(e.clientX - startX) > RESIZE_DRAG_THRESHOLD) dragged = true;
        const w = Math.max(MIN_COL_PX, Math.round(startVal + e.clientX - startX));
        const next = { ...widths, [key]: `${w}px` };
        if (neighbor) {
          next[neighbor.key] = `${Math.max(MIN_COL_PX, Math.round(startNeighbor - (w - startVal)))}px`;
        }
        this.colWidths = { ...this.colWidths, [page]: next };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        this.colManual = { ...this.colManual, [page]: true };  // 手动调过 -> 不再随窗口自适应
        this.saveColState();
        if (!dragged) return;  // 未拖动 = 纯点击 resizer, 不拦 click(保持原行为)
        // 拖拽尾处浏览器会冒泡一次 click 到 .h-cell 触发 setSort —— capture 阶段拦掉即停
        const swallow = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          document.removeEventListener("click", swallow, true);
        };
        document.addEventListener("click", swallow, true);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },
    /* 双击分隔线 = 按内容自适应宽度(表头 + 当前已渲染行), 夹在 [最小宽, MAX_FIT_PX] */
    autoFitColumn(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const container = headEl.parentElement;
      const rowSel = page === "detail" ? ".member-row" : ".group-row";
      let max = headEl.children[idx] ? headEl.children[idx].scrollWidth : MIN_COL_PX;
      for (const row of container.querySelectorAll(rowSel)) {
        const cell = row.children[idx];
        if (cell) max = Math.max(max, cell.scrollWidth);
      }
      const width = Math.min(MAX_FIT_PX, Math.max(MIN_COL_PX, Math.ceil(max) + 18));
      const widths = this._renderedWidths(headEl, page) || {};
      this.colWidths = { ...this.colWidths, [page]: { ...widths, [key]: `${width}px` } };
      this.colManual = { ...this.colManual, [page]: true };
      this.saveColState();
    },

    /* ------------------------------------------------ 列序(表头拖动重排 TBL-05) */

    /* 当前生效的全列序(可见+隐藏): colOrder 优先, 未入序的列(新增/残留)按定义序补尾 */
    _orderedKeys(page) {
      const defs = TABLE_COLUMNS[page].map((c) => c.key);
      const order = this.colOrder[page];
      if (!order || !order.length) return [...defs];
      const head = order.filter((k) => defs.includes(k));
      return [...head, ...defs.filter((k) => !head.includes(k))];
    },

    /* 落点换算: dropIdx 是**可视列空间**的插入边界(表头只渲染可见列), 存储的 colOrder 是
     * **全序列**(含隐藏列) —— 移除自身后按"第 b 个可见列之前"折算插入点, 隐藏列的相对
     * 次序不动(之后取消隐藏时插回原相对位)。落库后下一帧 materializeColumns 重实体化宽度。 */
    applyColOrder(page, key, dropIdx) {
      const full = this._orderedKeys(page);
      const vis = full.filter((k) => this.colVisible(page, k));
      const fromVis = vis.indexOf(key);
      if (fromVis < 0 || dropIdx < 0 || dropIdx > vis.length) return;
      const at = dropIdx > fromVis ? dropIdx - 1 : dropIdx;  // 移除自身后的插入边界(可视空间)
      full.splice(full.indexOf(key), 1);
      let inserted = false;
      for (let i = 0, seen = 0; i < full.length; i++) {
        if (!this.colVisible(page, full[i])) continue;
        if (seen++ === at) { full.splice(i, 0, key); inserted = true; break; }
      }
      if (!inserted) full.push(key);  // 边界在末个可见列之后
      this.colOrder = { ...this.colOrder, [page]: full };
      this.saveColState();
      this.$nextTick(() => this.materializeColumns());
    },

    /* 表头拖动重排手势: mousedown 阈值方案(与列宽拖拽 startResize 同款) —— 不用 HTML5
     * draggable, 避免原生拖影/文本选择与"点击排序""列宽拖拽"互相干扰。resizer 的
     * mousedown 已 .stop(不会进到这里); 位移超阈值才进入重排, 释放时若真拖过用 capture
     * 阶段 swallow 拦掉冒泡 click(防误触排序, 同 startResize 手法)。
     * 指示线: head 容器内绝对定位 .col-drop-line(不占 grid 轨道), left 由 move 实时更新。 */
    startColDrag(event, page, key) {
      if (event.button !== 0) return;  // 仅左键; 右键 = openColMenuAt(contextmenu), 中键不劫持
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      if (this._visibleCols(page).length < 2) return;  // 单列无从重排
      event.preventDefault();  // 抑制表头文本选择(拖拽手势的先决条件; 纯点击不受影响)
      const startX = event.clientX, startY = event.clientY;
      const TH = 6;  // 位移阈值(px): 之内视为普通点击(排序照旧), 超过才进入重排
      const label = (columnDef(page, key) || {}).label || key;  // FX-25 虚影文案
      let dragging = false;
      const cells = () => Array.from(headEl.children).filter((el) => el.classList.contains("h-cell"));
      const move = (e) => {
        if (!dragging) {
          if (Math.abs(e.clientX - startX) <= TH && Math.abs(e.clientY - startY) <= TH) return;
          dragging = true;
          headEl.classList.add("col-dragging");
          document.body.style.cursor = "col-resize";
        }
        const list = cells();
        const base = headEl.getBoundingClientRect();
        let idx = list.length;  // 默认插到末尾之后
        for (let i = 0; i < list.length; i++) {
          const cr = list[i].getBoundingClientRect();
          if (e.clientX < cr.left + cr.width / 2) { idx = i; break; }
        }
        // 指示线落在插入边界的列间隙中线(idx<len 取该列左缘-半间隙; 末尾取末列右缘+半间隙)
        const edge = idx < list.length ? list[idx].getBoundingClientRect().left : list[list.length - 1].getBoundingClientRect().right;
        this.colDrag = { page, key, idx, x: edge - base.left - headEl.clientLeft + (idx < list.length ? -5 : 5) };
        // FX-25: 虚影只更新 x/y(走 transform, 不触发重排); 无虚影时鼠标无处可依, 用户分不清"拖的是什么"
        this.colGhost = { label, x: e.clientX, y: e.clientY };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        headEl.classList.remove("col-dragging");
        document.body.style.cursor = "";
        const drag = this.colDrag;
        this.colDrag = null;
        this.colGhost = null;   // FX-25: 松手即消失
        if (!dragging) return;  // 未过阈值 = 普通点击, click 正常冒泡(排序不受影响)
        if (drag && drag.page === page) this.applyColOrder(page, key, drag.idx);
        // 拖拽尾冒泡 click 会触发 setSort(同列释放时) —— capture 阶段拦掉即停(同 startResize)
        const swallow = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          document.removeEventListener("click", swallow, true);
        };
        document.addEventListener("click", swallow, true);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },

    /* 落点指示线内联样式(仅本 page 的表头渲染; top/height 走 CSS 全高, left 相对 head 盒) */
    colDropLineStyle(page) {
      const d = this.colDrag;
      if (!d || d.page !== page) return {};
      return { left: d.x + "px" };
    },
  },
});

// 图形化配置编辑器以全局 mixin 注入(设置页控件/状态/接口全在其中)
app.mixin(window.CONFIG_EDITOR);
app.mixin(window.CONFIG_RULES);
app.component("ce-field", window.CE_FIELD_COMPONENT);
app.mount("#app");
