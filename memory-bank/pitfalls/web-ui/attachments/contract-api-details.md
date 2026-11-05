# 前后端数据契约的完整处置与实测证据 — 外迁详情(原 `pitfalls/web-ui/contract-api.md` 段落原文)

> 摘要: `pitfalls/web-ui/contract-api.md` 的详细处置/实测证据原文外迁(主档为控 cap 原位留指针); 判据与实测证据原样保留。
> 触发: 同主档 `pitfalls/web-ui/contract-api.md` 的触发词(完整列表见主档头部)。

> 本文件是**外迁存档**: 主档该段原文一字未改搬来 (仅相对链接整体下移一层 —— 本文件在 `pitfalls/web-ui/attachments/`); 本目录不计 cap, 主档原位留指针。
## 不能只看后端载荷, 前端还有一层派生

- **处置**: 动手前先做**最小验证**。

## 追剧视图 `members` 是**双形态**(后端 hash 数组 / 前端成员对象)

- **处置**: 必须先 `memberHashesOf()` 归一成 hash。
  守阵: `test_frontend_static_bundle_health` 第 7 项(集成员取 hash 的行必须含 `memberHashesOf(`)。
- **守阵是**按行**匹配的, 分不清「逐个取 hash」与「整串当 hash 传」(2026-10-09 实测)**: 它的判据是
  「该行含 `e.members` 且含 `.hash`/`hashes`/`for (const h of`, 却没有 `memberHashesOf(`」——
  于是**语义安全**的写法 `for (const m of this.sortedMembers(e.members)) ... m.hash` 同样被判红
  (模板 `shows.html` 的 `v-for="m in e.members" :key="m.hash"` 就是同款安全写法, 只是不进扫描面)。
  ⚠ **正确反应是改代码不是放宽守阵**: 该守阵拦的是"整集/整剧动作全线哑火"这种无声故障,
  放宽它的代价远大于多套一层函数。套法 = `memberHashesOf(sortedMembers(e.members))` ——
  先按明细表口径排好行序(`sortedMembers` 需要**对象**, 读 `m[key]`/`m.site`), 再由单点抽出 hash;
  两者都保留, 行序与屏幕顺序才一致(只写 `memberHashesOf(e.members)` 会丢排序)。
- **复发**: 1 (2026-09 首记; 2026-10-09 键盘光标链纳入集成员行时再撞 —— 路由命中了但只读到"必须归一",
  没读到"守阵按行匹配会误伤安全写法", 故补此条)。

## P1-1 按视图回传: 前端赋值必须"**键不存在则保留原引用**"

- **处置**: `if (state.groups !== undefined)` 这类守卫; 切视图时把 `lastRid` **置空**强制取一次全量;
  服务端 `view` 取**保守默认**(未知 / 缺省 ⇒ 全回)。

## 每条视图的数组集必须覆盖"该视图渲染所需的**全部**数据源"

- **处置**: 改 `VIEW_ARRAYS` 时**逐个视图问"它渲染时还读哪些数组"**, 并**用刷新页面的方式验证**
  (切视图会掩盖问题)。

## 跨视图的派生聚合(状态分布 / chip / 状态条)必须按 `viewMode` **自取数**

- **处置**: `distSegments` 按 viewMode 分支: groups 走 groups + singles / torrents 走 `torrents[].kind` /
  shows 走 `shows.list[].seasons[].episodes[].state`(**`shows` 是 `{list, unrecognized}` 不是数组**, 第一脚就踩过)。
  判定口诀"**凡跨视图呈现的派生值, 都问一次'它在另两个视图下还成立吗'**";
  守阵: `tests/test_webui_static_dom_page_layout.py::test_frontend_dist_segments_aggregates_per_view`。

## 上游从「空/未接入」变「有值」会点亮下游**从未跑过**的展示分支 (2026-09-29)

- **处置**: ①上游修复的验收加**下游展示回归**(拿真实数据走一遍此前不可达那档); ②优先"**有值就显示**"(`v-if="cellSeedingTime(m) && m.hr_req_time"`); ③守阵 `test_frontend_hr_safety_wiring` +2 断言。

## ⚠️ 跨视图的常驻消费者**不能**依赖按视图裁剪的阵列 (同类**已第四次**)

- **处置**: 全局聚合一律**服务端算好放进 `status` 恒回传**(与 `traffic` / `server` 同口径),
  不参与 `VIEW_ARRAYS` 分片、不参与 rid 门控。**不要**反过来把阵列加回 `VIEW_ARRAYS`(会废掉 P1-1 的体积优化)。
  ③的修法是"**取数面单点**": `facetRows` 按 `viewMode` 自取数(种子页 = `torrents`, 其余 = `decoratedGroups`),
  选项一律走 `_facetOptions(kind)` —— 计数口径**随行走**(组视图 = 含该值的组数, 种子页 = 含该值的种子数),
  与各自页面真正在筛的行一致; 静态守阵 `tests/test_webui_static_skins_*.py::_scan_filter_facets` 钉住"不许再有第二条按组算的实现"
  (`_memberValueOptions` 已删, 复活即红); 冒烟断言按"计数 == 用 `vm.torrents` 现数的真值"判 ——
  **只判非空会放过"仍按组算"的错误口径**(先开过辅种页再切过来时 groups 还在, 按组也能算出非零)。
  ④同③, 取数面单点 = `add_torrent.js::_addRecencyRows`(种子页平铺 / 其余 `singles ∪ decoratedGroups[].members`),
  时间表只从它算; 常规入口下三视图的行并集都等于全量, 故「最近使用」口径与视图无关。
- **复发**: 4 —— 2026-10-09 ④。**为什么没命中**(本条第③次已记在案仍重踩): 本轮按「候选集从哪来」
  思考数据源, **没按本条问一遍「这个取数点是不是常驻」**; 由本次新增 e2e 首跑当场抓出(桩已补候选数据面,
  渲染序却仍是字母序)。若无该 e2e, 缺陷会以"排序在辅种页静默不生效"的形态留在生产里 —— 这也是
  本条末句的实践依据: **这类"点了没反应/没生效"的形状静态守阵看不出来, 只能真浏览器钉**。

## "真值到达" ≠ "值覆盖结束"

- **处置**: 真值事件**只改覆盖的值**(`op.patch` / `op.prev` 都写成已落地的真值), **不结束覆盖**;
  收尾判据保持"服务端快照同意"(`_optimisticSettled`)或 8s 兜底。
  ⚠ `prev` **必须一起改**: 兜底回滚要回"最后已知真值", 回命令前的旧值等于把已暂停的种子显示成做种中。
  **判别法**: 任何"由 A 推导出的状态"若 A 比它的**消费源**(这里: 快照驱动的行数据)**更新**,
  就不能用它当收尾判据 —— 先问"这个值比我要覆盖的那份数据新多久"。
  冒烟断言「真值事件后不被陈旧快照打回」用 `page.route` 注入陈旧 payload 复现
  (红验: 撤掉修复 ⇒ 报 `陈旧快照 seeding`、`覆盖保持=0 条`)。

## rid 门控下"下轮以服务端为准"是**不成立**的

- **处置**: 兜底必须**显式回滚 `op.prev`**; 且回滚放在每轮 `refresh()` 里,
  **不要在渲染函数里改响应式字段**(`isPending()` 每帧被调用, 有递归更新风险)。

## "服务端的值"不等于"**已落地**的值"

- **处置**: 前端只在真值**匹配**时撤下(不一致保留乐观值继续等)+ 服务端发回执前等真值落地
  (上限 1200ms, **超时必须照发**, 等待期间按 0.2s 快速补刷新)。
  **代价排序: 显示错误状态 >> 多等一会儿。**

## 同一概念两张表必须对齐(前端 `STATE_RANK` 与后端 `_SHOW_STATE_RANK`)

- **处置**: **统一两张表前, 逐项问一遍"这一项翻过去, 用户会看到什么变化"**;
  语义有争议的项不要夹在"消除漂移"里一起改。
  ⚠ `distSegments` 里那张是**图例展示顺序**不是优先级, 别顺手统一。

## 取数单点放后端, 前端只展示

- **处置**: 前端不得重算; ⚠ `missingFiles` 状态自明, 必须**排除在 tracker 拉取分支外**(省预算)。

## 只在用户显式动作时才需要的字段不要塞进轮询载荷

- **处置**: 按需取一次详情即可。
- **复发**: 1 —— 2026-10-06 (S5 批 E-04, 计划 26-10-06-0103): 本条的**正向口径已落地** ——
  `_seed_view` 的平铺 SEED_ITEM 数组此前仍每轮携带全量 `magnet_uri`(magnet 添加型库 MB 级/轮),
  且 drawer 按需兜底因"种子页索引由 torrents 补齐"恒短路成死路径, 两组注释口径互相矛盾
  (decorate.js「扩展字段在这份」vs drawer.js「不给响应体加字段」)。修复 = `_seed_view` 去掉
  `magnet_uri`, `copyTorrentInfo` 按需取 `/api/torrents/{hash}` 详情成唯一路径, 注释收口;
  守阵 = test_web_seed_center.py SEED_ITEM 契约测试(断言载荷**不含** magnet_uri)。

## HR 标签着色靠"**文本逐字相等**"

- **处置**: 只比字符串; H&R 筛选同理 —— 只消费后端算好的组级计数 / 成员布尔, 前端**不做阈值重算**。

## "某列 / 某值恒为占位符"且同一取数点被多处复用 ⇒ **先核字段名**

- **处置**: 修口径时收成**单一取数点**。
- **复发**: 1 —— 2026-10-01 (计划 26-10-01-2216 阶段4 契约守阵首次通电抓出): 表② 波次明细表消费 `ls.lane_text`, 但 `LaneStatus` 没有该字段(`to_dict`=asdict 不含, 路由也不补)⇒ 档位徽章的人话渲染为空、只剩档位字母(色义仍走 `hrsLaneCls(ls.lane)`, 真机不细看发现不了)。守阵 `test_frontend_hr_contract_keys_match_backend`(前端消费键 ⊆ `EntryDetail`/`SiteStatus`/`LaneStatus` 的 to_dict 键集, 从模板锚段 + hr_status.js 源码双向提取)当场抓出; 修复在 src/ 侧, 不在阶段4(只动 tests)范围 —— **已修 7cff3adb**(`LaneStatus` 补 `lane_text` 字段由 `_lane_statuses` 填充, 复用 LANE_TEXTS 单点), 守阵白名单已收空恢复严格闭集, 并加 lane_text 逐档值断言。

## 候选集的"展示序"从另一数据源派生时, **键的口径必须与候选集同径** (2026-10-09)

- **处置**: 排序基准的键**必须过与候选集同源的那把归一函数**(前端 `add_torrent.js::_addNormPath`
  与后端 `infra/utils.path_normalize` 口径逐字一致: 转斜杠 + 压重复斜杠 + 保留首尾斜杠)。
  且**必须配真跑纯函数的 node 电池**(命中/不命中两态都钉) —— 静态守阵只验接线,
  看不出"键对不上", 而这正是本坑唯一可观测的面。
- **守阵**: `tests/test_webui_static_dom_panel_dialogs.py::test_frontend_add_options_recent_order`
  (node 电池真跑 `_addOrderByRecent`/`_addNormPath` + 静态钉接线, 已红验)。
