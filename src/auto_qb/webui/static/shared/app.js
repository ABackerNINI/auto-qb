/* auto-qb WEB UI 前端内核(Vue 3 CDN, 无构建链): rid 增量轮询 + 命令投递 + 列宽记忆
 *
 * **2026-09-27 W2b 续拆后的形态**: 本文件只留**常量单点**(列模型/排序/时间口径, 见下)与**接线**
 * (createApp 根选项展开 + app.mixin 注册 + mount)。根组件的 data/computed/watch 在 state.js、
 * 生命周期在 lifecycle.js(二者经 `...window.X` 展开进根选项 —— !不能走 app.mixin, 否则全局
 * mixin 会波及 hub-field 等组件实例, watch/mounted 双份执行); HTTP 鉴权(auth.js)/轮询推送
 * (polling.js)/视图切换与搜索(view.js)以 `window.AQB_*` 全局 mixin 方法域注入。**其余业务方法
 * 在 15 个片段文件里**(ui_feedback / filters / columns / format / decorate / hr / sort / menu /
 * commands / add_torrent / selection / shows / delete_flow / drawer / dialogs), 同一 mixin 范式,
 * 方法体里的 this 仍是**同一个**组件实例。**组件片段**(table.js: 表壳 <aq-table> + 行模型单元格渲染器
 * <aq-member-cells>/<aq-group-cells>/<aq-torrent-cells>/<aq-show-cells>/<aq-ep-cells>)同样走全局注册,
 * 但只贡献**模板** —— 行为一律经 $root 回调根实例。
 *
 * !三条硬约束(改动前先看 memory-bank/modules.md「前端契约速查 · 拆分」):
 *   1.片段文件在清单里必须排在**本文件之前**(本文件要读 window.AQB_*; boot.js 按清单序放行);
 *   2.下面的列模型常量是单一来源, 片段按裸名引用(运行时才求值) —— **不要再往下搬**,
 *     一搬就是上百处改名; 守阵盯住片段是否被清单引用 + 是否被 app.mixin 注入/根选项展开;
 *   3.data/watch/生命周期**只能**在 state.js/lifecycle.js 经根选项展开承载, 新增同类成员别写进
 *     app.mixin 片段(会波及全部组件实例); 反之方法域成员别塞回根选项(两套 UI 的组件树共用)。
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
 * hide:   已废除(2026-10-12, issue 26-10-12-1911) —— 默认隐藏不再逐列声明, 收口到唯一单点
 *         DEFAULT_HIDDEN_KEYS(定义见 TABLE_COLUMNS 上方); 播种语义不变 —— 首载时该页
 *         **从无任何偏好**(hidden/order/w 全缺)才按此注入 colHidden;
 *         一旦该页有过任何偏好(哪怕用户清空过 hidden)一律以存储为准, 不再播种
 *         (否则"刻意全开"的偏好会被默认值反复覆盖 —— 列偏好"时不时被重置"的同形陷阱)。
 *         已隐藏的列仍在列选择器里勾选开启。
 * tpl:    默认列宽模板(minmax(最小px, 权重fr) 或 固定 px), 用于首次渲染与"恢复默认"
 * align:  对齐口径(R10-08) —— **表头与值单元格的唯一来源**, 由 colAlignCss 生成规则注入,
 *         不在模板里逐格挂类(67 个值单元格 × 4 视图 × 2 套 UI, 逐格挂必漏)。
 *         取值 left | right | center; 缺省 = left。
 *         用户清单(2026-09-17): 名称/进度/状态/站点/分类/标签/添加于/做种时间/最近活动/
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
  // ---- 辅种扩列(2026-09-28): 组级聚合一律后端 _build_group_view 算好(派生值后端算约定) ----
  // 聚合总原则: 组内成员指向同一份文件(磁盘只占一份) —— 字节量类取"单份"视角, 网络流量类才可求和。
  // 进度 = 组内最高(最完整副本): "内容是否已完整到手"的信号, 与状态徽标互补
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)", sortable: true, align: "left" },
  // 剩余时间 = 组内最小有效 eta(同组至多一个成员在下载 —— 下载冲突检查兜底; 后端排除哨兵)
  { key: "eta", label: "剩余时间", tpl: "minmax(84px, 1fr)", sortable: true, align: "right" },
  // 已下载 = 全组求和: 多站切换下载的流量总消耗(recheck 承接不计入, 恰为真实网络成本)
  { key: "downloaded", label: "已下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  // 分类在标签之前(用户要求分组表/明细表口径一致); 列宽按**列 key**记忆 -> 换序不丢宽度
  { key: "category", label: "分类", tpl: "minmax(100px, 1.1fr)", align: "left" },
  { key: "tags", label: "标签", tpl: "minmax(130px, 1.4fr)", align: "left" },
  { key: "sites", label: "站点", tpl: "minmax(170px, 1.6fr)", align: "left" },
  // H&R: 未满足做种时间/分享率的成员数 / 已触发 HR 的成员数(组级计数由后端算好, 见 WebviewMixin._build_group_view)
  { key: "hr", label: "H&R", tpl: "minmax(88px, 1fr)", sortable: true, align: "center" },
  { key: "count", label: "站数", tpl: "56px", sortable: true, align: "center" },
  // TBL-06: 组级"最近添加"(组内成员最大 added_on, 后端 _build_group_view 已透出);
  // DEFAULT_SORT 默认排序键本就是 added_on —— 补列后排序箭头有了落点
  // R10-08: 时间列由右改左(表头与值同源, 不会再出现"表头左、值右"的错位)
  { key: "added_on", label: "添加于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // 最近活动 = 组内最新(-1/0 = 从未 哨兵不参与); 判断组活跃度, 比"添加于"贴近现状
  { key: "last_activity", label: "最近活动", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // 保存路径(用户 2026-09-17): 辅种表的路径取**首位成员**值(与路径筛选器同口径); 明细表
  // 相应取消该列 —— 组内成员路径本就一致(组 key 首元即规范化 save_path), 重复展示无信息量。
  { key: "save_path", label: "保存路径", tpl: "minmax(150px, 1.6fr)", sortable: true, align: "left" },
  // ---- 以下为可选列(默认隐藏口径见 DEFAULT_HIDDEN_KEYS 单点; 表头名称与种子页同名列对齐) ----
  // 剩余 = 组内最小: 组内指向同一份文件, 补齐一份即可 —— 最完整成员还差的字节
  { key: "amount_left", label: "剩余", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  // 做种时间 = 组内平均(最老/最新成员都不代表整组), 分钟取整
  { key: "seeding_time", label: "做种时间", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },
  // 可用性 = 组内最高(内容获取由最好的 swarm 决定); 全组未知(qB 负值)后端回 null
  { key: "availability", label: "可用性", tpl: "minmax(80px, 1fr)", sortable: true, align: "right" },
  // 组分享率 = 总上传 ÷ 单份大小(分母不能是 total_size —— N 份会稀释 N 倍)
  { key: "ratio", label: "分享率", tpl: "minmax(92px, 1fr)", sortable: true, align: "left" },
];
const DETAIL_COLUMNS = [
  { key: "site", label: "站点", tpl: "110px", sortable: true, locked: true, align: "left" },
  { key: "state", label: "状态", tpl: "76px", sortable: true, align: "left" },
  // TBL-06: 做种/用户(与种子页同口径 "已连接 (总数)", fmtPeersQb) —— 字段 W1a-BE 已在 _member_view 透出;
  // sortable 标记与 TORRENT_COLUMNS 同字段对齐(明细表头已接排序, 2026-09-17)
  { key: "num_seeds", label: "做种数", tpl: "92px", sortable: true, align: "right" },
  { key: "num_leechs", label: "用户", tpl: "92px", sortable: true, align: "right" },
  // 做种(总)/用户(总): tracker 汇报的 swarm 全量(即"做种/用户"列括号里的那个数), 独立成列可按它排序
  { key: "num_complete", label: "做种数(总)", tpl: "92px", sortable: true, align: "right" },
  { key: "num_incomplete", label: "用户(总)", tpl: "92px", sortable: true, align: "right" },
  { key: "dlspeed", label: "下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  // 剩余时间: 只有下载中的成员有值(与组级"最小有效 eta"口径呼应); 表头名称与种子页对齐
  { key: "eta", label: "剩余时间", tpl: "minmax(84px, 1fr)", sortable: true, align: "right" },
  // 单种子(成员)视角: 与分组表"总上传"(组内求和)区分 —— 成员是单颗种子, 表头用 qB 的"已上传"
  { key: "uploaded", label: "已上传", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  // 已下载: 各站点切换下载时的真实网络消耗(组级"已下载"求和的分站点拆分)
  { key: "downloaded", label: "已下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  // 限速: 每站点独立(0 = 不限速显示空白, fmtLimitBytes); 2026-10-12 起默认可见(默认隐藏口径统一收口 DEFAULT_HIDDEN_KEYS, 不再含限速)
  { key: "up_limit", label: "上传限制", tpl: "minmax(96px, 1fr)", align: "right" },
  { key: "dl_limit", label: "下载限制", tpl: "minmax(96px, 1fr)", align: "right" },
  // 与分组表同序: 分类在标签之前
  { key: "category", label: "分类", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },
  { key: "tags", label: "标签", tpl: "minmax(140px, 1.3fr)", sortable: true, align: "left" },
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)", sortable: true, align: "left" },
  { key: "seeding_time", label: "做种时间", tpl: "minmax(124px, 1.1fr)", sortable: true, align: "left" },
  // 分享率: 显示 实际/HR 要求(未配置分享率要求时只显示实际值); Hash 不可排序(无语义), 其余列均可
  // 2026-09-26 用户要求: 分享率列左对齐(与相邻数值列的右对齐不同, 值含 "实际 / HR 要求" 两段,
  // 左对齐起读更稳); 对齐单点在列模型, 由 colAlignCss 同时作用于表头与值(两套 UI 同源)
  { key: "ratio", label: "分享率", tpl: "minmax(104px, 1fr)", sortable: true, align: "left" },
  // 可用性: swarm 健康度(组级取最高, 这里看最高值来自哪个站); 负数/暂停不显示(cellAvailability)
  { key: "availability", label: "可用性", tpl: "minmax(80px, 1fr)", sortable: true, align: "right" },
  // 最后完整可见: swarm 侧最近一次出现完整拷贝的时间(保种/HR 诊断); 文案与详情抽屉一致
  { key: "seen_complete", label: "最后完整可见", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // TBL-06: 添加于(_member_view 已透出), 与 Hash 同置表尾低频区
  // (保存路径列 2026-09-17 移出本表 -> 见 GROUP_COLUMNS: 组内路径天然一致, 只保留组级一处)
  { key: "added_on", label: "添加于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // 完成于/最近活动/活动时间: 成员差异时间列, 表头名称与种子页同名列对齐
  // 时间/时长族一律左对齐(2026-09-29 列对齐审计 R4: 与添加于/最近活动/做种时间同族同口径)
  { key: "completion_on", label: "完成于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  { key: "last_activity", label: "最近活动", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  { key: "time_active", label: "活动时间", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },
  // Tracker: 每站点各自 announce; 信息哈希值 v1(40 hex, 老快照缺字段时前端回落 hash)/v2(64 hex):
  // v2 种子的信息哈希 —— 均成员各异; 命名与 qB WebUI 列名(Info Hash v1/v2)对齐; 默认隐藏口径见 DEFAULT_HIDDEN_KEYS
  { key: "tracker", label: "Tracker", tpl: "minmax(150px, 1.4fr)", align: "left" },
  { key: "infohash_v1", label: "信息哈希值 v1", tpl: "80px", align: "left" },
  { key: "infohash_v2", label: "信息哈希值 v2", tpl: "90px", align: "left" },
];
/* 种子页列模型(前端第一轮 R1A, 原 R08 单种子视图扩列升级): name 锁定; 数据源 = SEED_ITEM
 * 平铺数组(/api/state.torrents, 全量种子)。默认可见列 = 种子页核心口径(名称/大小/进度/状态/
 * 站点/做种/用户/下载/上传/剩余时间/分享率/已上传/分类/标签/添加于); 默认隐藏列 = 主页三表
 * 单点 DEFAULT_HIDDEN_KEYS 与本表列 key 的交集(剩余/信息哈希值 v1/Tracker/完成于) ——
 * 2026-10-12 起不再逐列写 hide 标志(issue 26-10-12-1911); SEED_ITEM 其余扩展字段
 * (已下载/可用性/做种时间/活动时间/最近活动/限速/保存路径)全部进列选择器按需开启。列宽按列
 * key 记忆在独立 page 名 "torrent" 下 —— 新增 page 属向后兼容扩展, 旧存储缺该 page 时
 * loadColState 返回空, 无需升 COLS_STORE_KEY 版本 */
const TORRENT_COLUMNS = [
  { key: "name", label: "名称", tpl: "minmax(220px, 2.6fr)", sortable: true, locked: true, align: "left" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)", sortable: true, align: "left" },
  { key: "state", label: "状态", tpl: "76px", align: "left" },
  { key: "site", label: "站点", tpl: "110px", sortable: true, align: "left" },
  { key: "num_seeds", label: "做种数", tpl: "92px", sortable: true, align: "right" },  // "已连接 (总数)" 格式(TBL-04), 64px 放不下
  { key: "num_leechs", label: "用户", tpl: "92px", sortable: true, align: "right" },
  { key: "dlspeed", label: "下载", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传", tpl: "minmax(88px, 1fr)", sortable: true, align: "right" },
  // 2026-09-26 用户要求: 表头文案改中文「剩余时间」(列 key 仍是 eta —— 列宽/隐/序按 key 存, 改名不影响既有偏好)
  { key: "eta", label: "剩余时间", tpl: "minmax(84px, 1fr)", sortable: true, align: "right" },
  // 2026-09-26 用户要求: 与明细表同口径(见 DETAIL_COLUMNS 的 ratio 注释) —— 分享率左对齐
  { key: "ratio", label: "分享率", tpl: "minmax(92px, 1fr)", sortable: true, align: "left" },
  // 单种子视角(用户 2026-10-10): 表头「已上传」(与「已下载」对称), 不再叫"总上传" —— 分组表仍叫"总上传"(组内求和)
  { key: "uploaded", label: "已上传", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  // 与分组表/明细表同序: 分类在标签之前
  { key: "category", label: "分类", tpl: "minmax(100px, 1.1fr)", align: "left" },
  { key: "tags", label: "标签", tpl: "minmax(130px, 1.4fr)", align: "left" },
  { key: "added_on", label: "添加于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  // ---- 以下为列选择器可选列(默认隐藏口径见 DEFAULT_HIDDEN_KEYS 单点; 字段集 = SEED_ITEM 扩展段) ----
  { key: "downloaded", label: "已下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "amount_left", label: "剩余", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "availability", label: "可用性", tpl: "minmax(80px, 1fr)", sortable: true, align: "right" },
  { key: "seeding_time", label: "做种时间", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },
  { key: "time_active", label: "活动时间", tpl: "minmax(110px, 1.1fr)", sortable: true, align: "left" },  // 时间/时长族左对齐(R4, 同 DETAIL_COLUMNS)
  { key: "last_activity", label: "最近活动", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
  { key: "completion_on", label: "完成于", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },  // 时间点族左对齐(R4)
  { key: "up_limit", label: "上传限制", tpl: "minmax(96px, 1fr)", align: "right" },
  { key: "dl_limit", label: "下载限制", tpl: "minmax(96px, 1fr)", align: "right" },
  { key: "infohash_v1", label: "信息哈希值 v1", tpl: "90px", align: "left" },
  { key: "tracker", label: "Tracker", tpl: "minmax(150px, 1.4fr)", align: "left" },
  { key: "save_path", label: "保存路径", tpl: "minmax(150px, 1.6fr)", align: "left" },
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
  // 追剧集行: 表头与种子页/明细表单种子口径对齐(用户 2026-10-10) —— 不再叫"总上传"
  { key: "uploaded", label: "已上传", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  { key: "hr", label: "H&R", tpl: "minmax(88px, 1fr)", sortable: true, align: "center" },
  // 最近动静: 与分组表"最近活动"同族(时间列), 一律左对齐
  { key: "latest", label: "最近动静", tpl: "minmax(110px, 1fr)", sortable: true, align: "left" },
];
/* ---------------- 详情面板三张列表的列模型(计划 26-10-11-2106 W2) ----------------
 * 与主视图四张表**同模型**(label/tpl/sortable/locked/align 全套), 但**只共用列交互引擎, 不并身份**:
 * 抽屉表另立注册表 DRAWER_TABLE_DEFS(与 hr_status.js 的 HR_TABLE_DEFS 同法, 见计划 §07 表 D)。
 *
 * !为什么另立而不并进 TABLE_DEFS: `TABLE_PAGES = Object.keys(TABLE_DEFS)` 驱动的是"页面"语义 ——
 *   列选择器分组 / 行窗口化的 kind 分派 / 「恢复默认列宽·适应窗口宽度」两动作; 抽屉表没有视图,
 *   也没有 3000 行的窗口化需求。列的**交互引擎**(拖宽/拖序/右键隐藏/持久化/对齐注入)在
 *   columns.js, 它按**表 id 集合**(ALL_TABLE_PAGES)工作, 两侧都吃得到。
 *
 * !列 key 与行模型字段同名(表头 / 排序 / 值单元格三处靠它对齐)。抽屉行的数值字段有"显示值"与
 *   "原始值"两份(dlspeed 等是 fmtSpeedOrDash 出的字符串), 排序一律读 `_raw` 侧 —— 否则 "1.2 MiB"
 *   会按字典序排。见 shared/drawer_tabs.js 的行装配与 columns.js 的 `_sortVal`。
 *
 * !act(操作)列是**动作槽**不是数据列: 无 label(表头留空)、不可排序、locked(隐藏了就没法删 tracker)。
 */
const DRAWER_TRACKER_COLUMNS = [
  { key: "url", label: "URL", tpl: "minmax(240px, 2.6fr)", sortable: true, locked: true, align: "left" },
  { key: "status", label: "状态", tpl: "88px", sortable: true, align: "left" },
  // 种子/用户两列沿用主视图口径 fmtPeersQb("已连接 (总数)"), 排序按**已连接数**原始值
  { key: "num_seeds", label: "种子", tpl: "104px", sortable: true, align: "right" },
  { key: "num_leeches", label: "用户", tpl: "104px", sortable: true, align: "right" },
  { key: "msg", label: "消息", tpl: "minmax(180px, 2fr)", sortable: true, align: "left" },
  { key: "act", label: "", tpl: "64px", locked: true, align: "right" },
];
const DRAWER_PEER_COLUMNS = [
  { key: "addr", label: "IP/地址", tpl: "minmax(170px, 1.6fr)", sortable: true, locked: true, align: "left" },
  { key: "client", label: "客户端", tpl: "minmax(150px, 1.6fr)", sortable: true, align: "left" },
  { key: "flags", label: "标志", tpl: "88px", sortable: true, align: "left" },
  // 进度左对齐(2026-10-18 用户报障): 与主表四张列集同口径(TORRENT/GROUP/DETAIL/SHOW 的
  // progress 全是 align:"left"), 值格条身 flex:1 占满轨道, 观感只动表头
  { key: "progress", label: "进度", tpl: "84px", sortable: true, align: "left" },
  { key: "dlspeed", label: "下载速度", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  { key: "upspeed", label: "上传速度", tpl: "minmax(96px, 1fr)", sortable: true, align: "right" },
  { key: "downloaded", label: "已下载", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "uploaded", label: "已上传", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "relevance", label: "文件关联", tpl: "96px", sortable: true, align: "right" },
];

/* 变体表格体列子集(计划 26-10-12-0527 U1 stub): 以经典用户列集为底裁剪(D2: 变体列个性 =
 * 数据声明) —— 5 列演示子集; U2 起各变体照此模式声明自己的子集/专属列。 */
const DRAWER_STUB_V0_COLUMNS = [
  DRAWER_PEER_COLUMNS[0], /* addr */
  DRAWER_PEER_COLUMNS[1], /* client */
  DRAWER_PEER_COLUMNS[3], /* progress */
  DRAWER_PEER_COLUMNS[4], /* dlspeed */
  DRAWER_PEER_COLUMNS[5], /* upspeed */
];
/* 变体表格体列集(U2, 计划 26-10-12-0527 D2/D6): 每变体一份 —— 列子集/专属列/默认序/可排性
 * 都是**数据声明**(以经典用户列集为底裁剪/重排/追加)。omisEmpty = 渐进列(qB files 字段随
 * 版本浮动, 无任何对端携带时整列省略 —— 原变体口径; 引擎单点在 columns.js _colsOmitEmpty,
 * 省略态下表头/行/grid/对齐同走一条 _visibleCols, nofiles 9 列错位 bug 类结构性根除)。
 * 2026-10-13(26-10-13-0811): files 渐进声明已删 —— 列常驻 + — 占位达成同款根除,
 * 且轨道数不再随数据浮动。 */
/* omitEmpty 已删(计划 26-10-13-0811): 渐进列轨道数随数据浮动, 是「多一格/少一列」类症状
 * 温床; 列常驻, 缺值由渲染器出 — 占位(dt07/dt08-files 的 dimc 暗色)。 */
const DRAWER_PEER_FILE_COLUMN = {
  key: "files", label: "文件", tpl: "minmax(110px, 1fr)", sortable: false, align: "left",
};
/* 07 四卡仪表: 10 列(上传速度在下载速度之前 —— 变体惯例), files 列常驻(渐进已删) */
const DRAWER_PEER_V07_COLUMNS = [
  DRAWER_PEER_COLUMNS[0], DRAWER_PEER_COLUMNS[1], DRAWER_PEER_COLUMNS[2], DRAWER_PEER_FILE_COLUMN,
  DRAWER_PEER_COLUMNS[3], DRAWER_PEER_COLUMNS[5], DRAWER_PEER_COLUMNS[4],
  DRAWER_PEER_COLUMNS[7], DRAWER_PEER_COLUMNS[6], DRAWER_PEER_COLUMNS[8],
];
/* 08 五区分组: 同 07 的 10 列, 但「文件关联」不可排序(原口径: 分区语义已隐含关联度) */
const DRAWER_PEER_V08_COLUMNS = [
  DRAWER_PEER_COLUMNS[0], DRAWER_PEER_COLUMNS[1], DRAWER_PEER_COLUMNS[2], DRAWER_PEER_FILE_COLUMN,
  DRAWER_PEER_COLUMNS[3], DRAWER_PEER_COLUMNS[5], DRAWER_PEER_COLUMNS[4],
  DRAWER_PEER_COLUMNS[7], DRAWER_PEER_COLUMNS[6],
  { ...DRAWER_PEER_COLUMNS[8], sortable: false },
];
/* 09 密度雷达: 9 列, 「占用」= upspeed 列的变体语义(条长 = 占当前上传合计比重, 渲染器出),
 * 排序仍按 upspeed 原始值 —— 列个性 = 声明(改 label), 排序语义不换键(R7 口径) */
const DRAWER_PEER_V09_COLUMNS = [
  DRAWER_PEER_COLUMNS[0], DRAWER_PEER_COLUMNS[1], DRAWER_PEER_COLUMNS[2], DRAWER_PEER_COLUMNS[3],
  /* 列名是纯文案: 方向符号由排序态单点渲染(表壳的 .arrow), 写在 label 里会与它叠加 ——
   * 用户报的「密度雷达占用表头前多了一个箭头」即此。详见计划 26-10-13-0811 L3。 */
  { ...DRAWER_PEER_COLUMNS[5], label: "占用" }, DRAWER_PEER_COLUMNS[4],
  DRAWER_PEER_COLUMNS[7], DRAWER_PEER_COLUMNS[6], DRAWER_PEER_COLUMNS[8],
];
/* ---------------- U3: Tracker 三变体列集(计划 26-10-12-0527, D2/D5) ----------------
 * 04 状态卡片栅格 / 05 健康分组: 行 = 卡片/处置块(非列状数据), 引擎行容器走**单列满宽**;
 * 列头在两变体无语义 → CSS 隐藏(.dt04-list/.dt05-list .group-head display:none)。
 * 排序键不占列(引擎 sortedDrawer 只按 _raw[key] 取值, 不要求 key ∈ cols):
 * 04 的分段钮(sev/tier 复合权值)经 dtSortSet 直设 dyn 键 —— 排序态仍归引擎单点。
 * Q3 记档: 两变体无列头, 拖宽/右键隐藏/列偏好持久化**不适用**(非缺能力, 是无列可拖)。 */
const DRAWER_TRACKER_V04_COLUMNS = [
  { key: "card", label: "卡片", tpl: "minmax(0, 1fr)", sortable: false, align: "left" },
];
const DRAWER_TRACKER_V05_COLUMNS = [
  { key: "card", label: "行", tpl: "minmax(0, 1fr)", sortable: false, align: "left" },
];
/* 06 增强表格: 8 列 = 原手搓 grid 逐列转声明(84px minmax(0,1fr) 44px 78px 78px 70px 122px 84px)。
 * 「下次重新汇报」不可排(R7 记档: 行级 next_announce / 种子级回退 / 正在汇报 三态混合口径,
 * 无单一排序原值, 不造假键); 其余可排; 默认序 sev 升序 = 原口径「异常置顶, 同档保 qB 原序」
 * (引擎比较器同值返回 0, Array.sort 稳定)。 */
const DRAWER_TRACKER_V06_COLUMNS = [
  { key: "sev", label: "状态", tpl: "84px", sortable: true, align: "left" },
  { key: "host", label: "Tracker", tpl: "minmax(0, 1fr)", sortable: true, align: "left" },
  { key: "tier", label: "tier", tpl: "44px", sortable: true, align: "right" },
  { key: "seeds", label: "种子", tpl: "78px", sortable: true, align: "right" },
  { key: "leeches", label: "用户", tpl: "78px", sortable: true, align: "right" },
  { key: "downloaded", label: "完成下载", tpl: "70px", sortable: true, align: "right" },
  { key: "next", label: "下次重新汇报", tpl: "122px", sortable: false, align: "left" },
  { key: "ops", label: "操作", tpl: "84px", sortable: false, align: "right" },
];
/* ---------------- U4: 内容树两变体列集(计划 26-10-12-0527, D2/D4/D5) ----------------
 * 10 树 + 详情 / 11 树表批量: 原 grid `18px minmax(0,1fr) 78px 128px 62px`(10) 与
 * `26px 18px minmax(0,1fr) 78px 130px [62px] 64px`(11) 逐列转声明, 树缩进格(name 列) =
 * D4 拍板「树是行模型的一部分」(折叠钮/勾选框/缩进/图标/名称/徽章都在格内, 判据在变体
 * rowsFn)。排序不适用(树序 = 树语义, 原口径无排序 → 全列 sortable:false + dyn 空键,
 * 非借壳 —— 本来就没有手搓排序状态机, Q3 不增项)。Q3 记档: 10 无表头设计 → 列头 CSS
 * 隐藏(05 先例), 拖宽/右键隐藏/列偏好**不适用**; 11 表头保留, 拖宽/右键隐藏首次落地。
 * 11 可用性列原 omitEmpty 渐进已删(26-10-13-0811): 轨道数随数据浮动, 列常驻 + — 占位。
 *
 * !2026-10-14 用户复查修法(背景报告 26-10-14-0136 §02 两项呈现缺陷):
 *   「操作按钮独立成列」—— 优先级徽章曾是 prio 一条独立轨道(修的是「不可隐藏」的能力,
 *     没解决「按钮占一列」的呈现); 徽章收编进 **name 格尾部**(margin-left:auto 右对齐,
 *     仍在同一竖线对齐但不占轨道)。
 *   「展开按钮没有层级」—— 折叠钮曾是 tgl 一条独立轨道: 全部展开钮钉在行首同一条竖线上,
 *     树层级只由 name 格的 paddingLeft 表达; 折叠钮收编进 **name 格首部随缩进**(与节点
 *     同层, 层级直接可视)。
 *   tgl/prio 两列自此删除(终态: 10 = name/size/prog 三列; 11 = ck/name/size/prog/av 五列),
 *   交互件随 name 格走 ⇒ **name 列 locked**(L4 续效: 隐藏 name = 一并废掉折叠钮与徽章
 *   两个交互件; ck 列同口径)。用户已存列偏好按 key 求交, tgl/prio 陈旧键自然失效, 免迁移。
 *   !2026-10-14 用户二次复查(报告 26-10-14-0136 §02 续): ck 勾选框仍独立成列且拖宽可调 ——
 *   勾选框收进 **name 格首部随缩进**(与节点同层, 不占轨道); ck 列自此删除(终态: 11 =
 *   name/size/prog/av 四列), 勾选框随 name 格走 ⇒ name 列 locked 续效(隐藏 name = 一并废
 *   掉勾选框/折叠钮/徽章三个交互件)。用户已存列偏好按 key 求交, ck 陈旧键自然失效, 免迁移。 */
const DRAWER_CONTENT_V10_COLUMNS = [
  { key: "name", label: "名称", tpl: "minmax(0, 1fr)", sortable: false, locked: true, align: "left" },  /* L4: 折叠钮+徽章在格内, 隐藏即废 */
  { key: "size", label: "大小", tpl: "78px", sortable: false, align: "right" },
  { key: "prog", label: "进度", tpl: "128px", sortable: false, align: "left" },
];
const DRAWER_CONTENT_V11_COLUMNS = [
  { key: "name", label: "名称", tpl: "minmax(0, 1fr)", sortable: false, locked: true, align: "left" },  /* L4: 勾选框+折叠钮+徽章在格内, 隐藏即废 */
  { key: "size", label: "大小", tpl: "78px", sortable: false, align: "right" },
  { key: "prog", label: "进度", tpl: "130px", sortable: false, align: "left" },
  /* omitEmpty 已删(计划 26-10-13-0811 L1 铁律: 渐进列轨道数随数据浮动, 是「多一格/少一列」
   * 类症状的温床); 列常驻, 缺值由渲染器 avTxt 出 — 占位. */
  { key: "av", label: "可用性", tpl: "62px", sortable: false, align: "right" },
];
const DRAWER_FILE_COLUMNS = [
  { key: "name", label: "文件", tpl: "minmax(220px, 3fr)", sortable: true, locked: true, align: "left" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true, align: "right" },
  { key: "progress", label: "进度", tpl: "84px", sortable: true, align: "right" },
  { key: "prio", label: "优先级", tpl: "104px", align: "left", locked: true },  /* L4: 内含优先级菜单按钮, 隐藏即废功能 */
];
/* ---------------- 主页三表(辅种/明细/种子)默认隐藏列单点 ----------------
 * 2026-10-12 issue 26-10-12-1911: 默认隐藏曾逐列写 hide:true, 三表各自演化 —— 种子页扩展段
 * 整段漏写(注释声称"默认隐藏"实际 28 列全显); 现收口到**这一处**, 三表同口径。
 * 形态 = 列 key 集合(不是列名) —— 种子页/明细表的哈希列命名已统一并与 qB 对齐(qB WebUI 列名
 * "Info Hash v1"/"Info Hash v2", 见 qB transferlistmodel.cpp 的 TR_INFOHASH_V1/V2): 明细表
 * 旧 key hash 已并入 infohash_v1, 种子页的重复列(key hash)已删。
 * 播种语义未变(loadColState 尾部): 只给**从无任何偏好**的页注入本表列 key 与集合的交集
 * (集合含某表没有的 key 时静默跳过); 有任何已存偏好一律以存储为准。
 * 用户暂定(2026-10-12): 剩余 / 最后完整可见 / Tracker / 信息哈希值 v1 / v2 / 完成于。
 * 后续要加默认隐藏列: 只在此集合加 key, 不许回列定义写 hide(守阵判红, 见 test_webui_static_skins)。 */
const DEFAULT_HIDDEN_KEYS = new Set([
  "amount_left", // 剩余
  "seen_complete", // 最后完整可见
  "tracker", // Tracker
  "infohash_v1", // 信息哈希值 v1
  "infohash_v2", // 信息哈希值 v2
  "completion_on", // 完成于
]);
const TABLE_COLUMNS = {
  group: GROUP_COLUMNS, detail: DETAIL_COLUMNS, torrent: TORRENT_COLUMNS, show: SHOW_COLUMNS,
  /* 变体表格体列集(26-10-12-0527): 与 DRAWER_TABLE_DEFS 同步注册(声明即事实源)。
   * 2026-10-14: 经典三表(drawerTracker/drawerPeer/drawerFile)随经典渲染链退役 ——
   * 列定义常量 DRAWER_*_COLUMNS 仍保留(变体列集由它们派生), 但不再各自登记一张表。 */
  drawerStubV0: DRAWER_STUB_V0_COLUMNS,
  drawerPeerV07: DRAWER_PEER_V07_COLUMNS,
  drawerPeerV08: DRAWER_PEER_V08_COLUMNS,
  drawerPeerV09: DRAWER_PEER_V09_COLUMNS,
  drawerTrackerV04: DRAWER_TRACKER_V04_COLUMNS,
  drawerTrackerV05: DRAWER_TRACKER_V05_COLUMNS,
  drawerTrackerV06: DRAWER_TRACKER_V06_COLUMNS,
  drawerContentV10: DRAWER_CONTENT_V10_COLUMNS,
  drawerContentV11: DRAWER_CONTENT_V11_COLUMNS,
};
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
 * 1. **不再靠"升版本"应对列集变更** —— 宽/隐/序一律按**列 key** 存, 新增列在旧缓存里只是
 *    "没有记录"(回退 tpl 默认宽), 不会错配; 历史上 v3->v4 升版本反而把用户手调的宽/隐/序
 *    清零, 正是"时不时被重置"的机制性来源。故本轮列模型增 `align` **不升版本**。
 * 2. 保留旧键迁移: 当前键缺失/损坏时依次读 LEGACY_COLS_KEYS, 命中即按列 key 求交集洗净后
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
 * 顺手改掉既有观感。WARN: 只收**时间点**列: 做种时间/活动时间/ETA 是时长, 没有绝对/相对之分。 */
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

/* ---------------- 表注册表(计划 26-10-11-1722 P0) ----------------
 * 「表身份」的单点: 每张表一行 —— 列定义 / 宿主 ref / grid 与可见列 computed 名 / 行窗口化 kind /
 * 排序键字段。取代此前散在 columns.js 里的四页硬编码(`["group","detail","torrent","show"]`)。
 *
 * !本轮(P0)是**零行为变化**的地基: 列定义常量(GROUP_COLUMNS 等)保持原样(守阵
 *   `_scan_column_cells_paired` 按 const 名 + 模板字面扫), 注册表只引用它们; 模板与 DOM 结构不动
 *   (表壳抽取在 P1)。TABLE_PAGES 由本表派生, 顺序即定义序(与旧字面量逐位一致)。
 * !新增一张表 = 在此加一行(列定义 + 宿主 + 排序键), 并在 state.js 加对应的排序字段;
 *   **不升 COLS_STORE_KEY 版本**(见 pitfalls/web-ui/columns-persist: 升版本会清空用户手调的宽/隐/序)。
 *
 * 字段:
 *   columns  列定义数组(单一来源)
 *   label    面向用户的表名(列选择器分组标题 / 契约文档用)
 *   headRef  吸顶表头元素 ref(_headEl 与横滚同步消费)
 *   tableRef 行容器 ref(行窗口化测量消费; null = 明细成员容器 .detail, 无独立滚动容器)
 *   grid     表头/行 grid 模板 computed 名(模板 gridStyle 消费)
 *   cols     可见列 computed 名(模板 visible*Cols 消费)
 *   window   行窗口化 kind(与 _rowWindow 的 kind 对齐; 明细 = member)
 *   sort     排序键/方向 data 字段名 + 恢复默认序的目标值(三态排序第三击落点)
 */
const TABLE_DEFS = {
  group: {
    columns: GROUP_COLUMNS, label: "辅种表",
    headRef: "groupHead", tableRef: "groupTable",
    grid: "groupGrid", cols: "visibleGroupCols", window: "group",
    sort: { gk: "sortKey", gd: "sortDir", defKey: DEFAULT_SORT.key, defDir: DEFAULT_SORT.dir },
  },
  detail: {
    columns: DETAIL_COLUMNS, label: "明细表",
    headRef: "detailHead", tableRef: null,
    grid: "detailGrid", cols: "visibleDetailCols", window: "member",
    sort: { gk: "detailSortKey", gd: "detailSortDir", defKey: "", defDir: -1 },
  },
  torrent: {
    columns: TORRENT_COLUMNS, label: "种子页",
    headRef: "torrentHead", tableRef: "torrentTable",
    grid: "torrentGrid", cols: "visibleTorrentCols", window: "torrent",
    sort: { gk: "torrentSortKey", gd: "torrentSortDir", defKey: DEFAULT_SORT.key, defDir: DEFAULT_SORT.dir },
  },
  show: {
    columns: SHOW_COLUMNS, label: "追剧视图",
    headRef: "showHead", tableRef: "showTable",
    grid: "showGrid", cols: "visibleShowCols", window: "show",
    sort: { gk: "showSortKey", gd: "showSortDir", defKey: "latest", defDir: -1 },
  },
};
/* 视图模式 -> 表 id(排序 scope 解析单点; groups 是默认视图, 未知值回落 group) */
const VIEW_TABLE = { groups: "group", torrents: "torrent", shows: "show" };

/* ---------------- 详情面板变体表的表身份(计划 26-10-11-2106 W2; 2026-10-14 经典三表退役) ----------------
 * 与 TABLE_DEFS **同形但独立** —— 拖宽 / 拖序 / 右键隐藏 / 列偏好持久化与主视图**同源**
 * (同一套 columns.js 引擎), 但**不进 TABLE_PAGES**(否则列选择器多出"页面"分组、行窗口化多出 kind)。
 * !2026-10-14(用户令「移除种子详情面板除流量页外的 4 个经典 UI」): 原经典三表
 *   (drawerTracker / drawerPeer / drawerFile —— 由已删的 drawer_tabs.js 渲染)连同行装配方法
 *   drawerTrackerRows 一并退役; 四内容页签的表格体此后**全部**走变体桥描述符(下表 variantTab 行)。
 *   列定义常量 DRAWER_*_COLUMNS 保留 —— 变体列集(DRAWER_*_V*_COLUMNS)仍由它们派生。
 *
 * 与 TABLE_DEFS 的两处形态差异:
 *   headRef  恒为 null —— 抽屉表头渲染在变体外壳/桥模板内部, 子组件模板里的 ref 只登记在子
 *            组件上, 根实例的 $refs 取不到; 故走 columns.js `_headEl` 的 **DOM 兜底**
 *            (按 `.group-head[data-table="<id>"]` 查, 表头根自带 data-table)。
 *   window   恒为 null —— 抽屉列表最多百级行, 远低于 ROW_WIN_MIN, 不开窗口化。
 *   grid/cols 走各自 computed(columns.js 里每表一对) —— 与主视图同一条 `_gridTemplate` 生成路径。
 *
 * sort 描述符: 变体表恒走 dyn(排序状态进根 data 的 dtSortState 映射, 按 table-id 通用存取)。
 */
const DRAWER_TABLE_DEFS = {
  /* ---------------- 变体表格体(计划 26-10-12-0527, D1 Teleport 锚桥) ----------------
   * 变体表格体接入 = 这里注册一行 + 变体外壳 dtHtml 输出锚(`data-dt-table-anchor="<id>"`)
   * + (新行模型才需)一个渲染器 —— 表壳/交互/持久化/对齐零改动(对外契约见 table.js 头注)。
   * 与经典三表的形态差异(增量, 经典三表不动):
   *   sort.dyn   排序状态进根 data 的 `dtSortState` 映射(按 table-id 通用存取, sort.js
   *              dyn 分支) —— 不再每表往 state.js 加两个 data 字段(注册一行即完事);
   *   variantTab/variantId  归属页签与变体 id —— ① columns.js `tableDefs` 据此过滤列选择器
   *              (变体表只在对应变体被选中时出现, 不泄进生产选择器); ② drawer.html 桥按
   *              dtBridgeTbl(tab) 反查(选择变体 → 桥表格)。
   *   rows/rowProp/rowModel  行来源(根方法名)/渲染器 prop 名/渲染器模型(aq-<rowModel>-cells)。
   * drawerStubV0 = U1 spike 的 stub(真实变体一行不改): 列 = DRAWER_PEER_COLUMNS 列子集
   * (D2 口径), 行复用 peer 行模型与 drawerPeerRows 装配 —— 只由 ?dtstub 查询参数激活的
   * 测试变体(stubbridge)输出锚, 生产不可见。 */
  drawerStubV0: {
    columns: DRAWER_STUB_V0_COLUMNS, label: "桥验证表(测试)",
    headRef: null, tableRef: null,
    grid: "drawerStubV0Grid", cols: "visibleDrawerStubV0Cols", window: null,
    sort: { dyn: true, defKey: "", defDir: -1 },
    variantTab: "peers", variantId: "stubbridge",
    rows: "drawerPeerRows", rowKey: "addr", rowModel: "peer", rowProp: "p",
  },
  /* ---------------- U2: 用户表三变体(07/08/09, 计划 26-10-12-0527; 拍板 D2/D3/D5/D6 = A) ----------------
   * rows: "dtTplRows" = 行来源与筛选(07/09 筛选 chips、08 五区分桶/只看在传)回变体注册条目的
   * rowsFn(版式语义); 排序/拖宽/右键隐藏/偏好持久化全走引擎(dyn 排序键 + table-id 偏好键)。
   * 默认序(2026-10-18 用户报障改口径): addr 升序(原 upspeed 降序) —— IP/地址列按点分
   * 数值比较(见 sort.js _dtStrCompare), 三态第三击复位同键。值格观感不变。
   * rowCls = 行装配预挂的修饰类串(红行/内网标/握手半透明 —— 行级个性经引擎行容器保留)。
   * 08 加 segs: true —— rowsFn 返回 [{key, rows}] 分段, 每组一个锚, 分组头留在外壳(D5:
   * 分组是版式, 行是引擎表体); 组内排序跨组共享一座键(与原手搓状态机同口径)。 */
  drawerPeerV07: {
    columns: DRAWER_PEER_V07_COLUMNS, label: "用户表·四卡仪表",
    headRef: null, tableRef: null,
    grid: "drawerPeerV07Grid", cols: "visibleDrawerPeerV07Cols", window: null,
    sort: { dyn: true, defKey: "addr", defDir: 1 },
    variantTab: "peers", variantId: "07",
    rows: "dtTplRows", rowKey: "addr", rowModel: "dt07", rowProp: "p", rowCls: "_cls",
  },
  drawerPeerV08: {
    columns: DRAWER_PEER_V08_COLUMNS, label: "用户表·五区分组",
    headRef: null, tableRef: null,
    grid: "drawerPeerV08Grid", cols: "visibleDrawerPeerV08Cols", window: null,
    sort: { dyn: true, defKey: "addr", defDir: 1 },
    variantTab: "peers", variantId: "08", segs: true,
    rows: "dtTplRows", rowKey: "addr", rowModel: "dt08", rowProp: "p", rowCls: "_cls",
  },
  drawerPeerV09: {
    columns: DRAWER_PEER_V09_COLUMNS, label: "用户表·密度雷达",
    headRef: null, tableRef: null,
    grid: "drawerPeerV09Grid", cols: "visibleDrawerPeerV09Cols", window: null,
    sort: { dyn: true, defKey: "addr", defDir: 1 },
    variantTab: "peers", variantId: "09",
    rows: "dtTplRows", rowKey: "addr", rowModel: "dt09", rowProp: "p", rowCls: "_cls",
  },
  /* ---------------- U3: Tracker 三变体(04/05/06, 计划 26-10-12-0527; 同 U2 法) ----------------
   * 04 状态卡片栅格: 行 = 卡片(引擎行容器单列满宽, 列头 CSS 隐藏 —— 卡片无列语义, D5);
   *   手搓分段钮排序并引擎(R7): _raw 挂复合权值(sev*10+tier / tier*10+sev, 虚拟合并卡恒 95),
   *   分段钮经 dtSortSet 直设 dyn 键(模式选择语义, 非 h-cell 三态循环), 默认 sev 升序 =
   *   异常优先。筛选 pills 是版式语义 → rowsFn + anchTouch(同 07)。
   * 05 健康分组: segs:true 五组(err/warn/upd/ok/off, 空组整段缺席), 组头/折叠留外壳
   *   (分组是版式, 行是引擎表体); 无排序(dyn 空键 = 组内 qB 原序, 原口径); 行三形态
   *   (失败处置块/普通行/off 组 chips 合成行)经 kind 分支 + rowCls, msg 展开态 rowsFn 读。
   * 06 增强表格: 8 列引擎表头(拖宽/右键隐藏/偏好持久化首次落地), 默认 sev 升序(异常置顶);
   *   「下次重新汇报」不可排(R7 记档: 三态混合口径无单一原值); onlyBad = 外壳容器类切换
   *   (行不重装配, 与原口径同); msg 展开态 rowsFn 读(重建后恢复)。 */
  drawerTrackerV04: {
    columns: DRAWER_TRACKER_V04_COLUMNS, label: "Tracker 表·状态卡片栅格",
    headRef: null, tableRef: null,
    grid: "drawerTrackerV04Grid", cols: "visibleDrawerTrackerV04Cols", window: null,
    sort: { dyn: true, defKey: "sev", defDir: 1 },
    variantTab: "trackers", variantId: "04",
    rows: "dtTplRows", rowKey: "k", rowModel: "dt04", rowProp: "p", rowCls: "_cls",
  },
  drawerTrackerV05: {
    columns: DRAWER_TRACKER_V05_COLUMNS, label: "Tracker 表·健康分组",
    headRef: null, tableRef: null,
    grid: "drawerTrackerV05Grid", cols: "visibleDrawerTrackerV05Cols", window: null,
    sort: { dyn: true, defKey: "", defDir: 1 },
    variantTab: "trackers", variantId: "05", segs: true,
    rows: "dtTplRows", rowKey: "k", rowModel: "dt05", rowProp: "p", rowCls: "_cls",
  },
  drawerTrackerV06: {
    columns: DRAWER_TRACKER_V06_COLUMNS, label: "Tracker 表·增强表格",
    headRef: null, tableRef: null,
    grid: "drawerTrackerV06Grid", cols: "visibleDrawerTrackerV06Cols", window: null,
    sort: { dyn: true, defKey: "sev", defDir: 1 },
    variantTab: "trackers", variantId: "06",
    rows: "dtTplRows", rowKey: "k", rowModel: "dt06", rowProp: "p", rowCls: "_cls",
  },
  /* ---------------- U4: 内容树两变体(10/11, 计划 26-10-12-0527; D4=A 树缩进格进渲染器) ----------------
   * 10 树 + 详情: 左树 = 引擎表体(行容器单行 grid), 右详情/工具条/foot 留外壳(版式);
   *   无表头设计 → 列头 CSS 隐藏(05 先例), 拖宽/右键隐藏不适用(Q3 记档)。行选中(selPath)
   *   驱动右详情 + 行 _cls, 行来源含非响应式 UI 态 → anchTouch(同 04/07)。
   * 11 树表批量: 7 列(勾选/折叠列 locked —— 隐藏即废勾选/折叠功能, 引擎 locked 消费);
   *   可用性列常驻(omitEmpty 已删, 26-10-13-0811); 批量优先级条留外壳, 勾选集
   *   (checked/子树三态)是版式语义 → rowsFn + anchTouch; 行内勾选框三态经分片
   *   :indeterminate 声明式(原生 property, Vue patch 直持)。
   * 两表行级键盘(issue 26-10-07-0846): rowTab = 行容器 tabindex=-1 声明位;
   *   rowAfter = 锚换代重挂后回调变体 rowAfterFn(roving 锚点/回焦) —— 行身份锚 =
   *   行容器 data-dt-key(rowKey 值, 桥模板单点输出)。排序不适用(树序 = 树语义)。 */
  drawerContentV10: {
    columns: DRAWER_CONTENT_V10_COLUMNS, label: "内容表·树 + 详情",
    headRef: null, tableRef: null,
    grid: "drawerContentV10Grid", cols: "visibleDrawerContentV10Cols", window: null,
    sort: { dyn: true, defKey: "", defDir: 1 },
    variantTab: "content", variantId: "10", rowTab: true, rowAfter: true,
    rows: "dtTplRows", rowKey: "k", rowModel: "dt10", rowProp: "p", rowCls: "_cls",
  },
  drawerContentV11: {
    columns: DRAWER_CONTENT_V11_COLUMNS, label: "内容表·树表批量",
    headRef: null, tableRef: null,
    grid: "drawerContentV11Grid", cols: "visibleDrawerContentV11Cols", window: null,
    sort: { dyn: true, defKey: "", defDir: 1 },
    variantTab: "content", variantId: "11", rowTab: true, rowAfter: true,
    rows: "dtTplRows", rowKey: "k", rowModel: "dt11", rowProp: "p", rowCls: "_cls",
  },
};
/* 列**交互引擎**的表 id 全集(columns.js 的列态/grid/对齐/生效宽度都按它遍历):
 * 主视图"页面" + 抽屉表。两者的差集只有一个用途 —— 见 columns.js `tableDefs` 的取法。 */
const ALL_TABLE_DEFS = { ...TABLE_DEFS, ...DRAWER_TABLE_DEFS };
const ALL_TABLE_PAGES = Object.keys(ALL_TABLE_DEFS);
/* 变体表格体桥(计划 26-10-12-0527)的描述符读取口: drawer_templates.js 的桥方法按 table-id
 * 反查(注册表在模板层, 描述符在数据层, 装载序 app.js 先于 drawer_templates.js —— 经 window
 * 中转, 运行时才求值)。 */
window.AQB_DRAWER_TPL_DEFS = DRAWER_TABLE_DEFS;

/* ---------------- P1-2 行窗口化(windowed rows) ----------------
 *
 * 背景(实测, 3000 种子, 见 e2e/perf.spec.mjs「P1-2/P1-3 A/B 埋点」): 每轮全量回传后前端整表替换,
 * **主线程被单个长任务占住 240~350ms** —— 这就是"点一下要等一会儿"的真身:
 * 每 2s 一次的刷新把 3000 行 × 13 列重新 patch 一遍, 期间点击/滚动全部排队。
 *
 * 做法: 只渲染视口附近的行, 上下各用占位 div 撑住总高度(滚动条长度与滚到底都照旧)。
 * 与"虚拟滚动"常见实现的区别 —— 这里**不改布局模型**: 行仍在原地流式排列(flex column),
 * 占位只是两个空盒子, 因此:
 *   1. 每行仍渲染**完整单元格序列**(CSS 的 :nth-child 列对齐与 data-table 都依赖它);
 *   2. 横向滚动/sticky 表头/列宽拖拽全部不受影响;
 *   3. 多选 shift 区间、右键、搜索高亮仍按**数据索引**走(filteredTorrents 原数组不变),
 *      窗口只决定"渲染哪一段", 不参与任何业务语义。
 *
 * 三条硬约束(漏了就出事):
 *   1. 占位高度必须等于被折叠掉的行高之和 —— 而**行高是不齐的**(带 H&R 要求的行多渲染一行,
 *      实测 43.7px 与 65.4px 混排), 故一律**逐行实测 + 前缀和**, 不做"等高"近似
 *      (等高假设在 3000 行上会漂 218px ⇒ 滚到底够不着)。首轮先全量渲染一次量齐。
 *   2. 视图有"插队元素"时必须退避: 分组页展开的 .detail 面板高度不定, 会让后续行整体下移,
 *      此时窗口的"第 i 行在 pre[i]"假设失效 —— 有展开即回退全量。
 *   3. 阈值以下不开窗: 小库(<ROW_WIN_MIN)开窗只是平白多一次测量, 且更容易露白。
 *
 * WARN: 行间距必须**实测**, 不能硬编码(2026-09-19 修 BUG-1): 三个行容器的真实 gap 并不相同 ——
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

/* 表页清单由注册表派生(顺序即定义序) —— 旧字面量 ["group","detail","torrent","show"] 的唯一来源 */
const TABLE_PAGES = Object.keys(TABLE_DEFS);
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
  // 遍历全集(含抽屉表): 旧载荷里没有它们的段 -> 生成空意图, 与"缺该 page 即空"同义
  for (const page of ALL_TABLE_PAGES) {
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
 * 单点收口: loadColState 只管洗净 + 默认隐藏播种, persistPage 只管写。 */
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
  // 空存储/坏数据也走完整流程: 默认隐藏播种对"该页从无偏好"的所有情形(全新浏览器/坏 JSON/
  // 只定制过别的 page)都必须生效 —— 提前 return 会把默认隐藏列全部放出来(冒烟实测)。
  let out = emptyColState();
  try {
    const raw = readColStateRaw();
    if (raw && typeof raw === "object") {
      // 遍历全集(含抽屉表): 抽屉表的列偏好存在同一份 v5 载荷的独立 page 子树下 —— 新增 page
      // 是向后兼容扩展(缺该 page 即空), **不升 COLS_STORE_KEY 版本**(R1: 升版本会清空用户手调的宽/隐/序)
      for (const page of ALL_TABLE_PAGES) {
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
    }
  } catch {
    /* 无存储 / 坏数据: out 保持空意图态, 下方默认隐藏播种照常发生 */
  }
  // 默认隐藏列播种(策略单点 DEFAULT_HIDDEN_KEYS, 见其定义处): 该页**从无任何偏好**
  // (hidden/order/w 全缺)时注入本表列 key 与该集合的交集。有任何已存偏好(哪怕空 hidden)
  // 一律不播 —— "刻意全开"是合法偏好, 被默认值反复覆盖就是"列偏好时不时被重置"的同形陷阱
  // (pitfalls web-ui/columns-persist)。
  // 播种只进内存意图态, 随首次 persistPage 自然落盘; 用户之后显隐任何列都以存储为准。
  for (const page of ALL_TABLE_PAGES) {
    if (!out.hidden[page] && !out.order[page] && !out.w[page]) {
      const defaults = TABLE_COLUMNS[page].filter((c) => DEFAULT_HIDDEN_KEYS.has(c.key)).map((c) => c.key);
      if (defaults.length) out.hidden[page] = defaults;
    }
  }
  return out;
}

const initialColState = loadColState();  // 模块级只读一次(data() 的初值来源)
/* 生效宽度初值: 固化页取意图(首帧即正确), 全自动页空(等 recomputeEffective 按当前窗口现算)。 */
const initialEffectiveWidths = (() => {
  const out = {};
  for (const page of ALL_TABLE_PAGES) out[page] = initialColState.w[page] ? { ...initialColState.w[page] } : {};
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

/* 顶层页面初值(持久化用户偏好, 与 initialViewMode 同口径)。
 *
 * 为什么要有: `page` 原本是**纯内存态**、初值恒 "groups" ⇒ 在设置页按 F5 必掉回辅种页
 * (2026-09-25 用户报"设置页刷新会回到种子页"), 编辑到一半的位置全丢。
 * 白名单式取值: 只认 "settings", 其余(含脏值/被清空)一律落回 "groups" —— 不信任存储内容。
 * WARN: 只把初值改成读存储**还不够**: 设置页的配置树是按需加载的, 启动路径必须补一次
 * cfgLoad(见 startPolling 尾部), 否则首屏停在「配置加载失败 + 重试」。 */
function initialPage() {
  try {
    return localStorage.getItem("autoqb.ui.page") === "settings" ? "settings" : "groups";
  } catch {
    return "groups";
  }
}

/* 种子详情抽屉标签页初值(持久化用户偏好, 与 initialViewMode/initialPage 同口径)。
 * 记住上次停留的 tab(常规/内容/用户/Tracker), 跨种子打开与刷新保持 ——
 * 用户报"在内容页打开一个种子, 点开另一个种子却回到常规页"。
 * 白名单取值: 只认 4 个合法 tab, 脏值/被清空一律回落 "general"。 */
function initialDrawerTab() {
  try {
    const saved = localStorage.getItem("autoqb.ui.drawerTab");
    return ["general", "trackers", "peers", "content"].includes(saved) ? saved : "general";
  } catch {
    return "general";
  }
}

/* 种子详情面板高度初值(方案A W3 持久化, 与 initialDrawerTab 同口径): 用户拖拽调高后记录 px。
 * null = 从未拖拽过 —— 面板回落默认 42vh 并**锁死**(2026-10-18 用户硬约束: 高度绝不随内容
 * 自行调整, 内容超高由 .drawer-body 内部滚动消化, 见 drawer.js drawerPanelStyle)。
 * 读侧只挡明显脏值(非数字/出界); 视口夹取 [240px, 70vh] 在应用时做(窗口尺寸跨刷新可能变),
 * 见 drawer.js::_drawerClampHeight。 */
function initialDrawerHeight() {
  try {
    const n = parseInt(localStorage.getItem("autoqb.ui.drawerHeight"), 10);
    return Number.isFinite(n) && n >= 240 && n <= 4000 ? n : null;
  } catch {
    return null;
  }
}

/* 详情面板模板选择初值(计划 26-10-06-0838 S1, P-01): 读 autoqb.ui.drawerTpl(按页签记模板 id)。
 * 白名单校验与缺省档口径单点在核心层 readSel/defaultSel(drawer_templates.js); 这里薄封装 ——
 * 核心未载入(清单序错)时也要返回**可用**映射, 不能返回空对象/undefined: 宿主显隐门 dtHostOn
 * 读 drawerTplSel.<tab>, 缺键会藏正文。下方字面量是与 defaultSel 同口径的**防御副本**
 * (四内容页签 = 首个变体; 流量 = classic), 只在核心层未载入这条坏路径上生效。 */
function initialDrawerTpl() {
  const out = { general: "01", trackers: "04", peers: "07", content: "10", traffic: "classic" };
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return out;
  return Object.assign(out, reg.readSel());
}

/* 页签合并开关初值(R2 计划 26-10-09-2219 S2 · R3 名单模型): 读 autoqb.ui.drawerMerge。
 * 白名单只认 off/on; R2 旧两选项值 gc/tp 迁移为 "on"(旧语义=某一对并排, 新语义=开关; 列组
 * 改由当前页签所属对决定, 故旧值只要"开着"即可无缝续用)。脏值/坏 JSON/读失败一律回落 "off"
 * —— 与 initialDrawerTab 同口径。生效还受宽度门约束(dtSplitOn), 这里只还原用户的布局意图。 */
function initialDrawerMerge() {
  try {
    const v = JSON.parse(localStorage.getItem("autoqb.ui.drawerMerge") || '"off"');
    if (v === "on" || v === "gc" || v === "tp") return "on";
    return "off";
  } catch {
    return "off";
  }
}

/* 状态优先级**单点表**(数值越小越"该被看到"): "一组/一集种子的聚合状态取哪个"。
 *
 * 必须与后端 `auto_qb/mixins/web_view.py::_SHOW_STATE_RANK` **逐项一致** —— 追剧页的集状态
 * (`e.state`) 是后端按那张表算好后回传的, 而辅种页的组状态 (`decoratedGroups.status.primary`)
 * 是前端按这张表算的。两张表一旦不一致, **同一批种子在两个页面会显示成不同颜色**;
 * 更糟的是乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
 * 两表一致性由 `tests/test_webui_static_skins.py::_scan_state_rank`(test_frontend_static_bundle_health 第 8 项)
 * 机械守卫(改一边必须改另一边), 该项同时钉住"做种排在暂停之前"的顺序语义。
 *
 * 语义 = "先报需要处理的, 再报在跑的, 最后报已完成的"; 但 **seeding 必须排在 paused 之前** ——
 * 组内"部分暂停部分做种"是常态(整组只有个别站点被暂停), 取 paused 会把整个做种的组刷成灰的。
 * 曾用顺序 ["error","checking","downloading","seeding","paused","other"] 与后端差两处:
 * {downloading,checking}(后端取 downloading —— 保留) 与 {paused,seeding}(前端取 seeding —— 恢复)。
 * !2026-09-19 的 BUG-7 把前端表整体对齐到后端, 顺手把 {paused,seeding} 也翻成 paused ⇒
 * 辅种页"部分暂停部分做种"的组由绿变灰(2026-09-21 用户报"以前是对的"), 本次两表一起改回做种优先。
 */
const STATE_RANK = { error: 0, downloading: 1, checking: 2, seeding: 3, paused: 4, other: 5 };
// 表里没有的 kind 排到最后(与后端 `_SHOW_STATE_RANK.get(k, 9)` 同口径)
const STATE_RANK_LAST = 9;

/* 根组件选项经展开注入(见 state.js/lifecycle.js 头注释: 不走 app.mixin 的原因);
 * 方法域(auth/polling/view)仍走全局 mixin, 与既有 AQB_* 同范式。 */
const app = createApp({
  ...window.AQB_STATE,
  ...window.AQB_LIFECYCLE,
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
app.mixin(window.AQB_CTX_MENU);  // 行右键菜单注册表 + 布局解析(计划 26-10-20-0024 W2): 数据在 AQB_CTX_MENU_REG, 模板消费在 W3
app.mixin(window.AQB_CTX_CUSTOM);  // 设置页「WebUI」卡右键菜单定制块(W4): 读写同一份 web.ctx_menu 草稿, 合并语义复用 AQB_CTX_MENU_REG
app.mixin(window.AQB_COMMANDS);
app.mixin(window.AQB_ADD);
app.mixin(window.AQB_SELECTION);
app.mixin(window.AQB_TRIGGERS);  // 触发点登记表(计划 26-10-10-2001 S2): 声明式单点, 守阵与 e2e 消费
app.mixin(window.AQB_SCOPE_AUDIT);  // 作用域运行时审计(S4): 默认关, 只记账不改行为
app.mixin(window.AQB_SHOWS);
app.mixin(window.AQB_DELETE);
app.mixin(window.AQB_DRAWER);
app.mixin(window.AQB_DRAWER_STORE);  // 抽屉数据/行为层(计划 26-10-11-2106 W1): 取数/竞态/等待集合/软切换序号, 与渲染无关
app.mixin(window.AQB_DRAWER_TPL);  // 详情面板模板核心层(W7 恢复): 菜单/读侧/显隐判据 + 变体挂载机械(原家 drawer_templates.js)
app.mixin(window.AQB_DIALOGS);
app.mixin(window.AQB_QB_TRAFFIC);  // qB 口径流量图(P5a, plan 26-10-03-0946 §07): uPlot 双系列组件 + 弹层方法域
app.mixin(window.AQB_HR_STATUS);
app.mixin(window.CONFIG_EDITOR);
app.mixin(window.CONFIG_RULES);
app.mixin(window.CONFIG_HUB);
app.mixin(window.AQB_AUTH);
app.mixin(window.AQB_POLL);
app.mixin(window.AQB_VIEW);
app.mixin(window.AQB_SHORTCUTS);  // 键盘快捷键引擎(计划 26-09-28-0354 W1; data 在 state.js / 监听在 lifecycle.js)
app.component("hub-field", window.HUB_FIELD_COMPONENT);
/* 「流量与限速」合并卡(计划 26-10-18-0813 B3): 设置页二级页的一个分区整体抽成组件,
 * 卡内三区(数据来源 / 限速曲线 / 流量图采样)见 shared/tpl/traffic-card.html 头注。
 * 模板件 + $root 回调, 方法仍在 config_hub.js —— 这里只注册渲染器。 */
app.component("aq-traffic-card", window.AQ_TRAFFIC_CARD_COMPONENT);
// 表格公共组件(计划 26-10-11-1722 P1/P2/P3): 表壳 <aq-table> + 行模型单元格渲染器
// (<aq-member-cells> / <aq-group-cells> / <aq-torrent-cells> / <aq-show-cells> / <aq-ep-cells>)。
// 它们只包**模板**(表头块 / 单元格分支链), 行为与状态仍在既有单点上 —— 组件模板经 $root 回调根实例。
// 这组注册即「渲染器注册表」单点(行模型 → 组件), 守阵 test_frontend_table_shell_single_point 钉住。
app.component("aq-table", window.AQ_TABLE_COMPONENT);
/* combobox 输入行 + 候选面板(收敛 issue 26-10-20-2230 / R23-A-01): 五个自绘下拉(添加窗口
 * 保存路径/分类/标签 · 设定位置 movePath · 编辑弹窗 metaCat)的骨架此前逐字复写五份, 现只此
 * 一份组件(模板 tpl/xtpl.html#tpl-combo-input, 定义在 add_torrent.js); 行为仍是既有单点
 * (comboHoverIdx/comboKeydown/_fitAddPop/_popBlurShouldHold), 组件只贡献模板。 */
app.component("aq-combo-input", window.AQ_COMBO_INPUT_COMPONENT);
/* 模板层「小控件」三件套(收敛 issue 26-10-20-2231 / 台账 R23-B-01·02·16·17): 7 处 hb-switch
 * 开关块、5 处 hb-sub-toggle 可折叠段头、4 套分段单选钮此前各写各的(还有四种可访问性不一的
 * 折叠实现); 现三段名为一套 —— 模板在 shared/tpl/ctl-bits.html, 定义在 shared/ctl_bits.js。
 * !这三件套与上面那些组件一样**只贡献模板**: 状态与动作仍在各自的方法域(config_hub.js 的
 * hubSub* / cfgRuleMeta* / cmSetSkipCheck 等), 组件经回调 prop 反调回去 —— 在这里补方法会
 * 触发 _scan_mixin_wiring 的重名守阵(被盖掉的那份永不执行)。 */
app.component("aq-switch", window.AQ_SWITCH_COMPONENT);
app.component("aq-fold", window.AQ_FOLD_COMPONENT);
app.component("aq-seg", window.AQ_SEG_COMPONENT);
app.component("aq-member-cells", window.AQ_MEMBER_CELLS_COMPONENT);
app.component("aq-group-cells", window.AQ_GROUP_CELLS_COMPONENT);
app.component("aq-torrent-cells", window.AQ_TORRENT_CELLS_COMPONENT);
app.component("aq-show-cells", window.AQ_SHOW_CELLS_COMPONENT);
app.component("aq-ep-cells", window.AQ_EP_CELLS_COMPONENT);
/* 变体表格体桥(计划 26-10-12-0527 U1): 外壳锚 → Teleport 表壳 + 行渲染器(见 table.js 尾注) */
app.component("aq-dt-bridge", window.AQ_DT_BRIDGE_COMPONENT);
/* U2 变体格渲染器(计划 26-10-12-0527): 用户表三变体的行模型(桥模板按 rowModel 动态解析) */
app.component("aq-dt07-cells", window.AQ_DT07_CELLS_COMPONENT);
app.component("aq-dt08-cells", window.AQ_DT08_CELLS_COMPONENT);
app.component("aq-dt09-cells", window.AQ_DT09_CELLS_COMPONENT);
app.component("aq-dt04-cells", window.AQ_DT04_CELLS_COMPONENT);
app.component("aq-dt05-cells", window.AQ_DT05_CELLS_COMPONENT);
app.component("aq-dt06-cells", window.AQ_DT06_CELLS_COMPONENT);
/* U4 变体格渲染器(计划 26-10-12-0527): 内容树两变体 —— drawerFileTree 树缩进格口径
 * (折叠钮/勾选框/缩进/图标/名称/徽章)两段同构单份, 列集 D2 各表声明(桥按 rowModel 解析) */
app.component("aq-dt10-cells", window.AQ_DT10_CELLS_COMPONENT);
app.component("aq-dt11-cells", window.AQ_DT11_CELLS_COMPONENT);
// 详情面板头部外壳与流量控件组(计划 26-10-11-2106 W3): 两形态此前各写一份 <header>, 标题块与
// 关闭按钮逐字复写(表 B 问题 4 的温床); 现外壳一份 + 中部插槽, 形态差异只在调用点。控件组
// <aq-qb-ctl> 是**多根片段**, 两挂点(流量形态头部 / 种子流量页签图下统计栏)共用同一份实现 ——
// 三皮肤 CSS 的直接子选择器(.drawer-head > .qb-tabs / .qb-statctl > .qb-tools)依赖它不留 wrapper。
app.component("aq-drawer-head", window.AQ_DRAWER_HEAD_COMPONENT);
app.component("aq-qb-ctl", window.AQ_QB_CTL_COMPONENT);
/* 列表外壳两件套(收敛 issue 26-10-20-2231 / R23-A-05 · R23-B-06): 行窗口化上下占位 <aq-row-pad>
 * (四处手写同一撑高 div)与空态块 <aq-empty>(12 处手写同一三件套, 其中 4 处无图标)各自只剩
 * 一份组件, 定义在 table.js(模板 tpl/list-shell.html 的两个 x-template), 这里只注册渲染器。 */
app.component("aq-row-pad", window.AQ_ROW_PAD_COMPONENT);
app.component("aq-empty", window.AQ_EMPTY_COMPONENT);
app.mount("#app");
