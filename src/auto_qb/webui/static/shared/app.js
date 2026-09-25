/* auto-qb WEB UI 前端内核(Vue 3 CDN, 无构建链): rid 增量轮询 + 命令投递 + 列宽记忆
 *
 * **2026-09-20 已按域拆分**: 本文件只留内核 —— 列模型常量(单一来源, 见下)、`data()` / `watch` /
 * 生命周期、HTTP 与鉴权、轮询主链(`refresh`)与视图切换。**其余业务方法在 15 个片段文件里**
 * (ui_feedback / filters / columns / format / decorate / hr / sort / menu / commands / add_torrent /
 * selection / shows / delete_flow / drawer / dialogs), 以 `window.AQB_*` 全局 mixin 注入 —— 与
 * `config_editor.js` / `config_rules.js` 同一范式, 方法体里的 this 仍是**同一个**组件实例。
 *
 * ❗两条硬约束(改动前先看 memory-bank/modules.md「前端契约速查 · 拆分」):
 *   ①片段文件在 HTML 里必须排在**本文件之前**(本文件末尾要读 window.AQB_*);
 *   ②下面的列模型常量是单一来源, 片段按裸名引用(运行时才求值) —— **不要再往下搬**,
 *     一搬就是上百处改名; 守阵第 10 项会盯住片段是否被 HTML 引用 + 是否被 app.mixin 注入。
 */
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
 * v5 = { v:5, origin, pages:{ page:{ hidden:[列key], order:[列key], w:{列key:"120px"} | null } } }
 * —— **存储只存用户意图**(hidden/order/w); 生效宽度是按当前窗口现算的派生值, **绝不落盘**(唯一铁律)。
 * w: null = 全自动页(各窗口各算各的); w 非空 = 用户固化过整页宽度。manual 标志位删除(w 非空即固化)。
 * v2(按列索引的稀疏覆盖) -> v3(**按列 key**) -> v4(加列) -> v5(意图/生效分轨, 挂 v4/v3 迁移)。
 *
 * R10-09 修订两条:
 * ① **不再靠"升版本"应对列集变更** —— 宽/隐/序一律按**列 key** 存, 新增列在旧缓存里只是
 *    "没有记录"(回退 tpl 默认宽), 不会错配; 历史上 v3->v4 升版本反而把用户手调的宽/隐/序
 *    清零, 正是"时不时被重置"的机制性来源。故本轮列模型增 `align` **不升版本**。
 * ② 保留旧键迁移: 当前键缺失/损坏时依次读 LEGACY_COLS_KEYS, 命中即按列 key 求交集洗净后
 *    内存迁移为 v5(不立即回写, 首次意图动作经 persistPage 落盘)。v2 是**按列索引**式,
 *    索引在支持隐藏列后会漂移, 无法可靠迁移 -> 刻意不读。
 *
 * 不被重置的保证: _logout()/换密钥只清 `autoqb_token`, 全仓尤 `localStorage.clear()`。
 * 仍存在的限制(已写入 pitfalls): localStorage 按 **origin** 隔离 —— localhost 与 127.0.0.1
 * 或换端口 = 不同站点, 各有自己的偏好(用户已明确要求只存浏览器, 不接受服务端化)。 */
const COLS_STORE_KEY = "autoqb_cols_v5";
const LEGACY_COLS_KEYS = ["autoqb_cols_v4", "autoqb_cols_v3"];  // v2 为索引式覆盖, 不可迁移(见上)
/* W4 origin 提示(plan 26-09-21-1551): 本 origin 首次出现"空列存储"时提示一次 —— 换地址/端口
 * 即另一个独立存储, 这是客户端唯一可观测的隔离信号(别的 origin 的存储读不到, 指纹跨站比对不可达)。 */
const COLS_ORIGIN_HINT_KEY = "autoqb_cols_origin_hint_v1";

/* FX-28: 时间列显示口径(相对/绝对)持久化, **按列**独立而非全局 —— 用户可能想"添加于看绝对、
 * 最近活动看相对", 一把切会互相打架。刻意**不**塞进 COLS_STORE_KEY: 那个键管的是列集合/列宽/
 * 顺序(按 page 分段 + 跨标签合并), 显示口径是另一条生命周期, 混进去要多背一段 read-modify-write。
 * 默认值 = 改造前的现状(添加于/完成于/最近动静原本就是绝对时间, 最近活动已改相对) —— 加开关不该
 * 顺手改掉既有观感。⚠ 只收**时间点**列: 做种时长/活跃时间/ETA 是时长, 没有绝对/相对之分。 */
const TIME_FMT_STORE_KEY = "autoqb_timefmt_v1";
const TIME_FMT_KEYS = ["added_on", "last_activity", "completion_on", "latest"];
const TIME_FMT_DEFAULT = { added_on: "abs", last_activity: "rel", completion_on: "abs", latest: "abs" };
function loadTimeFmt() {
  const out = Object.assign({}, TIME_FMT_DEFAULT);
  try {
    const raw = JSON.parse(localStorage.getItem(TIME_FMT_STORE_KEY) || "{}");
    for (const k of TIME_FMT_KEYS) {
      if (raw[k] === "rel" || raw[k] === "abs") out[k] = raw[k];
    }
  } catch (e) {
    /* 无存储 / 坏数据: 回落默认(偏好类读取失败不该影响启动) */
  }
  return out;
}

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

const TABLE_PAGES = ["group", "detail", "torrent", "show"];
const emptyColState = () => ({ hidden: {}, order: {}, w: {} });  // 运行时意图态: w[page] = null | {列key: "Npx"}

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

/* 旧版载荷(v4/v3 四段式) -> v5 按页子树(内存迁移, plan 26-09-21-1551 §3.3):
 * hidden/order 原样带过(洗净交给 loadColState); w 只保留**固化页**(manual 标志为真)的宽度段,
 * 非固化页一律 null —— 旧模型往非固化页写的 px 是"别的窗口算出的自适应快照"(历史污染),
 * 迁移即清零, 正是用户要的"从头算"。 */
function migrateLegacyToV5(raw) {
  const pages = {};
  for (const page of TABLE_PAGES) {
    const fixed = !!((raw.manual || {})[page]);
    const widths = (raw.widths || {})[page];
    pages[page] = {
      hidden: Array.isArray((raw.hidden || {})[page]) ? raw.hidden[page].slice() : [],
      order: Array.isArray((raw.order || {})[page]) ? raw.order[page].slice() : [],
      w: fixed && widths && typeof widths === "object" ? { ...widths } : null,
    };
  }
  return { v: 5, origin: "", pages };
}

/* v5 载荷归一化: pages 段缺失/损坏时回空(新增 page 属向后兼容扩展, 缺该 page 即空)。 */
function normalizeV5(raw) {
  const pages = raw.pages && typeof raw.pages === "object" ? raw.pages : {};
  return { v: 5, origin: typeof raw.origin === "string" ? raw.origin : "", pages };
}

/* 读列状态(归一化为 v5 形态): 当前键优先; 缺失/损坏时读旧键做**内存迁移** —— 不立即回写,
 * 首次意图动作经 persistPage(唯一写入口)落 v5; 期间每次加载重迁移, 成本可忽略。
 * 单点收口: loadColState 只管洗净, persistPage 只管写。 */
function readColStateRaw() {
  for (const key of [COLS_STORE_KEY, ...LEGACY_COLS_KEYS]) {
    try {
      const raw = JSON.parse(localStorage.getItem(key));
      if (raw && typeof raw === "object") {
        return key === COLS_STORE_KEY ? normalizeV5(raw) : migrateLegacyToV5(raw);
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
    for (const page of TABLE_PAGES) {
      const keys = columnKeys(page);
      const src = (raw.pages || {})[page] || {};
      const w = src.w;
      if (w && typeof w === "object") {
        // 意图宽度白名单: 只收合法列 key 的 "<num>px"(非法/残留键丢弃); 洗完全空 = 全自动页
        const clean = {};
        for (const [k, v] of Object.entries(w)) {
          if (keys.includes(k) && /^\d+px$/.test(v)) clean[k] = v;
        }
        if (Object.keys(clean).length) out.w[page] = clean;
      }
      const h = src.hidden;
      if (Array.isArray(h)) {
        // locked 列即使被写进存储也忽略(列定义变更后可能残留)
        out.hidden[page] = h.filter((k) => keys.includes(k) && !(columnDef(page, k) || {}).locked);
      }
      const o = src.order;
      if (Array.isArray(o)) {
        // 列序(TBL-05): 只收合法列 key 并去重; 缺失列(新增列)由 _visibleCols/_orderedKeys 按定义序补尾
        const seen = new Set();
        const clean = [];
        for (const k of o) {
          if (keys.includes(k) && !seen.has(k)) { seen.add(k); clean.push(k); }
        }
        if (clean.length) out.order[page] = clean;
      }
    }
    return out;
  } catch {
    return emptyColState();
  }
}

const initialColState = loadColState();  // 模块级只读一次(data() 的初值来源)
/* 生效宽度初值: 固化页取意图(首帧即正确), 全自动页空(等 recomputeEffective 按当前窗口现算)。 */
const initialEffectiveWidths = (() => {
  const out = {};
  for (const page of TABLE_PAGES) out[page] = initialColState.w[page] ? { ...initialColState.w[page] } : {};
  return out;
})();

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
 * 两表一致性由 `tests/test_web.py::_scan_state_rank`(test_frontend_static_bundle_health 第 8 项)
 * 机械守卫(改一边必须改另一边), 该项同时钉住"做种排在暂停之前"的顺序语义。
 *
 * 语义 = "先报需要处理的, 再报在跑的, 最后报已完成的"; 但 **seeding 必须排在 paused 之前** ——
 * 组内"部分暂停部分做种中"是常态(整组只有个别站点被暂停), 取 paused 会把整个做种中的组刷成灰的。
 * 曾用顺序 ["error","checking","downloading","seeding","paused","other"] 与后端差两处:
 * {downloading,checking}(后端取 downloading —— 保留) 与 {paused,seeding}(前端取 seeding —— 恢复)。
 * ❗2026-09-19 的 BUG-7 把前端表整体对齐到后端, 顺手把 {paused,seeding} 也翻成 paused ⇒
 * 辅种页"部分暂停部分做种中"的组由绿变灰(2026-09-21 用户报"以前是对的"), 本次两表一起改回做种优先。
 */
const STATE_RANK = { error: 0, downloading: 1, checking: 2, seeding: 3, paused: 4, other: 5 };
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
      /* FX-28: 各**时间点列**的显示口径 { 列key: "rel" | "abs" } —— 由该列表头右键菜单切换并持久化
       * (见 TIME_FMT_STORE_KEY); 键集合 = TIME_FMT_KEYS, 未登记的列不受影响 */
      timeFmt: loadTimeFmt(),
      /* 相对时间时钟(FX-27): 只喂"最近活动"这类相对时间显示(fmtRelTime), 30s 一跳 ——
       * 为什么必须有: 后端 last_activity 按分钟量化且只在**活动发生时**才变, 暂停的种子行对象
       * 长期不变 ⇒ Vue 不重渲染 ⇒ 相对值会永久停在渲染那一刻("刚刚"挂一整天)。粒度只到分钟,
       * 不必比 30s 更密(更密只会白付整表 patch, 与 P1-2 的窗口化成果相抵)。 */
      nowSec: Math.floor(Date.now() / 1000),
      pendingOps: {},  // P0-3 乐观 UI: hash -> { patch, prev, ts }, 见 isPending/applyOptimistic
      /* 本轮 /api/state 的**真值快照**: hash -> { 补丁键: 服务端原始值 }。
       * 判"真值是否已对齐"必须比这个, 不能比行上的当前值 —— 见 _snapshotTruth。 */
      truthSnapshot: null,
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
      // 列状态双轨(plan 26-09-21-1551): 意图态(唯一持久化对象)与生效态(易变, 绝不落盘)分开
      colHidden: initialColState.hidden,  // 意图: {page: [列key]}
      colOrder: initialColState.order,    // 意图: {page: [列key]} (TBL-05 表头拖动重排; 空 = 定义顺序)
      colW: initialColState.w,            // 意图: {page: null | {列key: "Npx"}} —— null/缺失 = 全自动页
      colWidths: initialEffectiveWidths,  // 生效: 固化页 = 意图, 全自动页 = recomputeEffective 现算
      colMenuOpen: false,                 // 列选择器弹层开关
      colMenuAt: null,                    // 列选择器 fixed 锚点(表头右键路径 {x,y,mh}; null = 按钮路径走 CSS 定位)
      colDrag: null,                      // 表头拖动重排进行中(TBL-05): {page, key, idx, x} — idx=可视列插入边界, x=指示线位置
      // FX-25: 拖动虚影(跟随光标的列名胶囊)。刻意不用 HTML5 draggable 的原生拖影 —— 它会与
      // "点击排序"与"列宽拖拽"互相干扰; 自绘虚影与现有 mousedown 阈值手势完全解耦。
      colGhost: null,                     // {label, x, y} | null
      menu: { visible: false, x: 0, y: 0, key: null, hash: null, multi: false },
      // FX-15: 右键菜单的次级菜单(flyout)展开态与翻转态 —— 一级只有一个「更多操作」子面板,
      // 队列/TMM/超级做种/强制开始/分享率限制/复制族 都在它里面(见 conventions/webui.md)
      subMenu: "",        // "" | "advanced"
      subFlip: false,     // 子面板向左翻(父项靠右, 右展会伸出视口)
      // CTX-05: 移出后延迟收起的定时器句柄(0 = 无挂起); 延迟只用于跨过父项与子面板之间的缝隙
      _subCloseTimer: 0,
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
      addDragOver: false,     // 全局拖拽遮罩(拖 .torrent 文件/链接进页面任意位置时点亮, drop/拖离即灭)
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
        note: "",             // 后端"筛不了"的说明(格式无等级字段 / 已存行与格式不符)
        level: "",            // ""=全部 | INFO | WARNING | ERROR(后端按配置格式串定位等级字段)
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
    // 生效宽度: 全自动页按当前渲染现算(见 recomputeEffective); 窗口变化后重算, 保持
    // "填满容器 + 自适应"的观感; 固化页(colW 非空)用意图值, 不随窗口变(拖一列不再影响其它列)
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        this._syncHeadHeight();
        this.recomputeEffective();
      }, 120);
    });
    this.$nextTick(() => {
      this._syncHeadHeight();
      this.recomputeEffective();
    });
    /* W4(origin 提示, plan 26-09-21-1551): localStorage 按 origin 隔离, 换地址/端口 = 另一个
     * 独立存储。客户端唯一能观测到的信号是"本 origin 从没有任何列偏好"(空存储) —— 指纹跨站
     * 比对不可达(别的 origin 的存储读不到)。命中即提示一次, 把看不见的隔离变成可见。 */
    if (!readColStateRaw()) this._showColsOriginHint();
    /* 跨标签同步(F2, issue 26-09-20-1800): 别的标签改了列 -> 本标签整份采用存储值。
     * 若不同步, 本标签下一次 persistPage 会以旧底整段覆盖该页, 把别的标签的改动静默吞掉
     * (用户感知 = "列设置被重置")。双轨模型下采纳的是意图, 采纳永远安全。
     * storage 事件**只在其它标签**触发(写入方自己收不到) ⇒ 无需去重, 也不会自激。 */
    this._onColStore = (e) => {
      if (e.key === COLS_STORE_KEY) this.adoptColState();
    };
    window.addEventListener("storage", this._onColStore);
    /* FX-28: 时间口径跨标签同步(F2) —— 与列偏好同一套机制(整份采用存储值), 但**独立监听**:
     * 两个 key 的生命周期不同(列集合/列宽 vs 显示口径), 塞进同一个监听只会让判据互相纠缠。
     * 写入方自己收不到 storage 事件 ⇒ 无需去重, 也不会自激。 */
    this._onTimeFmtStore = (e) => {
      if (e.key === TIME_FMT_STORE_KEY) this.adoptTimeFmt();
    };
    window.addEventListener("storage", this._onTimeFmtStore);
    // FX-27: 相对时间时钟(30s 一跳) —— 见 data.nowSec 注释; 不挂 visibilitychange:
    // 后台标签本来就不会重排渲染, 回到可见时 refresh() 一并刷新, 无需额外开关
    this._clockTimer = setInterval(() => {
      this.nowSec = Math.floor(Date.now() / 1000);
    }, 30000);
    // 页面可见性(与 qB 自带 WebUI 同策略): 后台标签停止轮询; 恢复可见立即刷新并续排
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.stopPolling();
      else {
        this.adoptColState();  // F3: 补漏 —— 标签被冻结 / storage 事件丢失时, 回到可见即对齐一次
        this.adoptTimeFmt();   // 同上(FX-28): 时间口径也在回到可见时补对齐一次
        if (this.authOk) this.refresh();  // 登出态切回标签不发空 Bearer; R10-01: 判据 = 鉴权模式
      }
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
        this.recomputeEffective();
      });
    },
    // CTX-02: 任一浮层菜单关闭 -> 撤掉触发源强调(浮层可以多种方式关闭: Esc/点空白/执行动作)
    "menu.visible"(v) {
      if (!v) {
        this._clearCtxSource();
        this.keepSub();     // CTX-05: 撤掉挂起的延迟收起(否则一级关了之后还会再触发一次)
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
    this.stopEvents();  // P2: 断开 SSE(否则热重载后句柄堆叠)
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
    // 跨标签同步(F2): storage 监听随组件销毁撤掉(否则热重载后句柄堆叠, 一次改动 adopt 多次)
    if (this._onColStore) {
      window.removeEventListener("storage", this._onColStore);
      this._onColStore = null;
    }
    // FX-28: 时间口径跨标签监听随组件销毁撤掉(同上, 防热重载后句柄堆叠)
    if (this._onTimeFmtStore) {
      window.removeEventListener("storage", this._onTimeFmtStore);
      this._onTimeFmtStore = null;
    }
    // FX-27: 相对时间时钟随组件销毁撤销(同上, 防热重载后句柄堆叠)
    if (this._clockTimer) {
      clearInterval(this._clockTimer);
      this._clockTimer = 0;
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
      this.logs = { loading: false, error: "", loaded: false, lines: [], file: "", note: "", level: "", num: 300 };
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
    /* ---------------- P2 事件驱动(SSE /api/events) ----------------
     * 目的: 把「命令回执」与「视图版本变更」从轮询改成推送 ——
     *   前者省掉回执轮询的退避粒度(0→150→300→500ms), 后者省掉 1.5/2/3s 的定时触发。
     * ❗轮询**保留**作为兜底: 断线 / 首帧 / 浏览器不支持 / 反代缓冲时自动退回, 语义不变。
     * ⚠ EventSource 发不出 Authorization 头 ⇒ 密钥走 ?token=(服务端已放行, 见 web.py);
     *   本机 skip_local_verify(默认)下不需要带密钥。
     */
    startEvents() {
      if (this._es || typeof EventSource === "undefined") return;
      const q = this.token ? `?token=${encodeURIComponent(this.token)}` : "";
      let es = null;
      try {
        es = new EventSource(`/api/events${q}`);
      } catch (e) {
        return;  // 不支持就用轮询, 不报错(推送是加速手段, 不是必需)
      }
      this._es = es;
      es.addEventListener("cmd", (e) => {
        // 命令回执: 兑现 commands.js 里等待这条命令的 Promise(省掉轮询粒度)
        try { this.onCmdEvent(JSON.parse((e && e.data) || "{}")); } catch (_) { /* 坏帧忽略 */ }
      });
      es.addEventListener("truth", (e) => {
        // 真值事件: 服务端确认命令已生效后推来; 前端据此把行换成真值并结束值覆盖
        // (见 commands.js onTruthEvent —— 服务端只在真值落地时才推, 所以可以放心采纳)
        try { this.onTruthEvent(JSON.parse((e && e.data) || "{}")); } catch (_) { /* 坏帧忽略 */ }
      });
      es.addEventListener("ver", (e) => {
        // 只带版本号、**不含数据** —— 收到后拉一次 /api/state。密集发布时去抖合并,
        // 免得一轮 sync 触发 N 次全量拉取(3000 种子一轮 63ms, 打满主线程的坑踩过)。
        if (this._verTimer) clearTimeout(this._verTimer);
        this._verTimer = setTimeout(() => { this._verTimer = null; this.refresh(); }, 60);
      });
      es.onerror = () => {
        // EventSource 自带重连(默认 3s); 这里不干预, 轮询兜底照旧在跑
      };
    },
    stopEvents() {
      if (this._verTimer) { clearTimeout(this._verTimer); this._verTimer = null; }
      if (this._es) { this._es.close(); this._es = null; }
    },
    startPolling() {
      this.stopPolling();
      this.startEvents();  // P2: 先接上推送通道(失败也无害, 轮询仍在)
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
          this._snapshotTruth(state);  // ❗必须在 reapplyPending **之前**: 快照要的是服务端原始值
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
        this._expirePending();    // ❗先回滚超时的(不回滚会留永久假状态, issue 26-09-19-2141)
        this.reapplyPending();    // P0-3: 整表替换后把仍 pending 的乐观值重新贴上
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
        this.recomputeEffective();
      });
      // 立刻取一次新视图的数据, 不等下轮轮询(否则首次切到某视图要空/旧 ≤2s)。
      // scheduleNext 内部先 stopPolling 再排下一次, 所以这里不会造成双份轮询。
      if (this.authOk) this.refresh();
    },
  },
});

// 图形化配置编辑器以全局 mixin 注入(设置页控件/状态/接口全在其中)
app.mixin(window.AQB_FEEDBACK);
app.mixin(window.AQB_FILTERS);
app.mixin(window.AQB_COLUMNS);
app.mixin(window.AQB_FORMAT);
app.mixin(window.AQB_DECORATE);
app.mixin(window.AQB_HR);
app.mixin(window.AQB_SORT);
app.mixin(window.AQB_MENU);
app.mixin(window.AQB_COMMANDS);
app.mixin(window.AQB_ADD);
app.mixin(window.AQB_SELECTION);
app.mixin(window.AQB_SHOWS);
app.mixin(window.AQB_DELETE);
app.mixin(window.AQB_DRAWER);
app.mixin(window.AQB_DIALOGS);
app.mixin(window.AQB_HR_STATUS);
app.mixin(window.CONFIG_EDITOR);
app.mixin(window.CONFIG_RULES);
app.mixin(window.CONFIG_HUB);
app.component("ce-field", window.CE_FIELD_COMPONENT);
app.component("hub-field", window.HUB_FIELD_COMPONENT);
app.mount("#app");
