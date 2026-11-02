"""test_webui_static_dom_panel_drawer 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

## 测试计划(每个测试函数一条)
- test_drawer_tpl_registry_wiring: 详情面板模板核心层接线守阵(plan 26-10-06-0838 S1) —— 三份 manifest 成对含 drawer_templates.js 且装载序 drawer.js < 核心 < state.js(state data() 调 initialDrawerTpl 依赖注册表); 变体文件 (id, tab) 唯一且 tab 合法且三 manifest 成对登记(S1 变体数为 0, 断言按当前集合写); 变体 label 展示名禁档位后缀(Q4, 报告 26-10-07-0542 —— 档位是物理形态非信息组织, 三档语义全收进本变体, 写进下拉名冗余误导); 核心含 AQB_DRAWER_TPL_REG/dtHtml+dtRaw/autoqb.ui.drawerTpl/data-dt CSS 注入单点; 一行式钩子四类齐全(调用点随 W1 数据层抽离落 drawer_store.js: _loadDrawerTab 尾 _dtSync / 四 fetcher _dtNotify; closeDrawer _dtUnmountAll 与 collapse 通知仍在 drawer.js)+ 列表三 fetcher 通知在 loading 清掉之后(2026-10-07 用户页空列表停"正在加载…"报障)+ drawerTab 补强二; drawer.html 宿主 x6/合并列 data-dt-tab x4/摘要条 x2(2026-10-10 头部 .dt-select 退役, 模板选择迁右键)+ 经典包裹层 v-show 接 drawerTplSel; state.js 显式建字段 + app.js initialDrawerTpl + app.mixin; dt* 成员全仓无重名(mixin 覆盖静默故障, 核心书写形态不在 _scan_mixin_wiring 扫描面内, 此处补钉)
- test_drawer_tpl_variant_width_discipline: 详情面板变体宽度纪律守阵(Q1, 报告 26-10-07-0542) —— 核心注入 CSS 含四页签宿主(general/trackers/peers/content)的 max-width 1400px 居中收口(15 变体单点共享, 变体文件零复刻; traffic 双宿主排除 —— 图本体/工具条归经典链恒满宽, 13/15 KPI 头行限宽会与图缘错位, 14 解读栏自带 288px 固定右栏) + 全部变体与核心注入 CSS 禁 justify-content:space-between(label/value 两端推开病根, 标签在前值紧随; 非 kv 场景确需两端分布须显式改本守阵并注明)
- test_drawer_tpl_variant_field_icons: 详情面板变体字段行图标消费守阵(Q2, 报告 26-10-07-0542) —— general 三变体(01/02/03)字段行必须消费 drawerGeneralSections() 行级 icon 数据(sprite `<use href>` 静态引用)且含经典链 icoTone 同表派生 + .ico-t-* 着色 CSS(经典 .f-row 作用域在变体行不命中, 色表须自带); traffic 三变体(13/14/15)KPI/解读行含 sprite 图标引用; 全变体 #i-* 引用不越三皮肤 sprite 既有 symbol 集合(三皮肤集合两两相等)且不引入外部图标库(<img/iconfont/fontawesome/material-icons); shared/tpl/*.html 的 #i-* 引用同规则(26-10-29-1355, 模板与变体同文档载入 shell, 引到缺 symbol = 图标静默空白)
- test_drawer_tpl_table_variants_scrollleft_restore: 表格型变体横向滚动位自保守阵(P2-2, 报告 26-10-07-0542; 骨架收口 26-10-07-0845) —— 滚动自保单点收口在核心 H.withScroll(纵横两轴成对读写, 恢复次序 scrollLeft 先 scrollTop 后) + dt06/07/08/09 四变体整帧重建都包在 withScroll 回调内 + 变体内分散自保(scroller 直读写/host.parentElement)不得回潮, 任一变体绕开单点或核心两轴不成对即红
- test_drawer_tpl_trackers_per_tracker_reannounce: 06 变体逐行汇报倒计时真 per-tracker 口径守阵(P-02 升级, issue 26-10-07-0149, 2026-10-09) —— 真口径分支读行级 next_announce 且先减 nowSec(epoch 绝对时间当倒计时是事故根因) + 「全局」标(dt06-gb)只许出现在回退分支(真值行不标全局) + 回退分支仍在(qB < 5.2 无该字段, 保留种子级 detail.reannounce_in 全局近似) + nowSec 计入 sig(否则跳过重建把倒计时冻在上一帧) + 真口径分支不画微条(per-tracker interval 不可得, 不造假) + 调用点传行 t 与 nowSec
- test_drawer_tpl_a11y_and_fetch_error_states: 变体可访问性 + fetch 失败态区分守阵(P3-4/P3-5, 报告 26-10-07-0542) —— 核心层 drawer-close 钮 aria-label(种子/流量两头部成对) + 纯 div/span 模拟控件 role=button/tabindex=0(01/02/03/05/08 折叠组头含 aria-expanded、07/08/09 排序表头含 aria-sort 升/降/无随态输出、05/06 msg 展开行) + keydown 委托与 click 委托成对挂摘(挂摘纪律收口在核心 wireEvents/unwireEvents 单点, 26-10-07-0845; 变体只声明事件表)且转发前排除原生交互元素(防 Enter 双重触发) + 三 fetcher 失败标记(trackersError/filesError/peersError)显式建字段(初值在 drawer.js)/catch 落/成功清/换目标作废(随 W1 数据层抽离在 drawer_store.js) + 九个 fetch 型变体(04-12)错误态先于空态且文案对齐轮询事实(trackers/peers 5s 轮询可写自动重试, content 无轮询不得虚构承诺)
- test_drawer_tpl_content_row_keyboard_roving: content 组行级键盘 roving tabindex 守阵(issue 26-10-07-0846) —— 核心 helpers 四件套(roving 锚点/rowFocusKey 记账/rowRestore 回焦/rowMove 移焦)单点存在; dt10/11 [data-node] 与 dt12 [data-blk]/[data-row] 行容器 tabindex=-1 不进 Tab 序(整行不加 role=button, 行内原生控件自然参与 Tab)且 CSS 带 :focus-visible 可见焦点; keydown 委托成对挂宿主且只有 ev.target 是行容器自身才接管(行内原生控件键盘行为自持); 重建前记账/重建后回焦成对(原子换帧打断焦点链, 不回焦一次激活就甩回文档头); dt12 树图块焦点互联复用悬停 onOver/onOut(focusin/focusout 同语义)
- test_drawer_tpl_variant_no_singleton_shadowing: 变体单点 T/R/H 遮蔽禁令守阵(2026-10-09 用户报障「空间树图选了不显示、换种子回落经典」) —— dt12 layoutMap 曾写 `const W = mapEl.clientWidth, H = mapEl.clientHeight`, 局部 H 把文件头 helpers 单点(reg.helpers)遮蔽成数字, 同函数尾 H.rowFocusKey(...) 对数字取属性抛 TypeError -> 核心 _dtRender catch 把该页签选择复位 classic 并落盘: 树图块只在 layoutMap 绘制故永远空白 + 用户选择跨会话被静默复位。守阵 = 每个变体文件凡声明了 T/R/H 单点(const <N> = reg.dtHtml|dtRaw|helpers), 该名在全文件(单点声明行之外)禁止再被任何声明语句绑定 —— 含多声明符列表(let a = 1, H = 2, 本案根因形态)与解构(const { H } = ...); 未声明单点的名不查(15 号变体无 H 单点, 其局部 H = 22 是合法常量)

- test_drawer_tpl_cross_seed_fold: 折叠态跨种子口径统一守阵(P3-6, 报告 26-10-07-0542) —— dt10/11/12 换种子重置块(hash !== ui.lastHash)只许清选中/勾选/筛选、不得清折叠记账 ui.folded/ui.colG(口径统一为跨种子保持, 以 general 组 dt01/02 为准; 记账 key 是 path 不含 hash, 新种子旧条目自然不命中, 同名目录延续折叠选择) + dt11 勾选集必须继续重置(批量优先级真提交, 旧勾选落新种子是误操作面) + 其余变体(01-09/13-15, 记账 key 与种子无关或无折叠)不得出现 lastHash 机制 + 2026-10-10 模板选择迁右键后核心不得再注入 .dt-select
- test_drawer_tpl_menu_right_click_selection: 详情面板模板选择迁右键守阵(2026-10-10 用户动议「模板选择改为右键选择, 在对应的区域弹右键; 合并时左边弹常规、右边弹内容的模板选择」) —— 核心菜单 computed(dtMenuTab/dtMenuTplOptions/dtMenuTplCurrent/dtMenuMergeOn)与落点 dtMenuPick 齐全且选择器 API 退役; menu.js openDrawerMenu 放行 seed/traffic 形态且目标页签解析成对(变体宿主 data-dt-host 去 traffic-pre/post 后缀优先 / 合并列 data-dt-tab 兜列头空列 / 否则当前页签); ctx-menus 渲染模板选项(v-for)+勾选态(.ctx-tick)+条件合并开关(dtMenuMergeOn)
- test_drawer_tpl_default_sel: 详情面板模板**缺省档**守阵(原名 test_drawer_tpl_classic_default, plan 26-10-06-0838 S1; 2026-10-14 经典渲染链移除后缺省档按页签分化: 四内容页签 = 该页签首个变体, 流量页签 = classic) —— 有 node 时真跑核心层 node 电池(白名单脏值/未注册 id/坏 JSON 一律回落缺省档; 注册 fail-fast 四分支; dtHtml 转义 + dtRaw 豁免; options 不含 classic); 无 node 静态兜底: app.js initialDrawerTpl 缺核心时也必须返回可用映射(空对象会把正文藏掉)且字面量与 defaultSel 同口径(四内容页签 = 首个变体; 流量 = classic)
- test_drawer_tpl_render_error_fallback_default: 变体渲染抛错自动回落**缺省档**守阵(P2-1, 报告 26-10-07-0542; 原名 test_drawer_tpl_render_error_fallback_classic, 2026-10-14 经典渲染链移除后兜底不再是 classic) —— 有 node 时真跑 _dtRender 抛错电池钉回落五件(复位该页签缺省档 + 落盘 / 不牵连其它页签 / 摘挂载态 / 清宿主 + destroy 回调 / console.error 带页签与变体 id; 失败档恰为缺省档时不改写不落盘); 无 node 静态兜底: catch 块四要素缺一即红(只清宿主的空白降级不得回潮)
- test_drawer_seed_reentry_variant_remount: 种子详情面板回页变体宿主重挂守阵(2026-10-07 报障「面板打开时切设置页再切回, 面板空白」) ——
- test_frontend_drawer_form_judge_single_point: 面板形态判据收口守阵(计划 26-10-11-2106 W3; W7 保留) —— drawer.kind 字面量只许 drawer.js 定义处恰两处(menu.js/shortcuts.js/tpl/drawer.html/qb_traffic_chart.js 零处, 新增散点比较即红) + 调用点逐个钉走 drawerIsSeed/drawerIsTraffic 派生单点 + 判据自带 this.drawer 守卫(全局 mixin 会把 computed 注入 <transition> 的 BaseTransition 假实例, 手抄防御不得回潮)
- test_drawer_seed_reentry_variant_remount: 原「## 测试计划」条目见 test_webui_static_dom_panel_traffic.py(跨分文件共用同一用例条目, 文案未改)
- test_frontend_drawer_groups_shows_views: 辅种页/追剧页支持种子详情面板守阵(计划 26-10-08-1217) —— 可见性单点 drawerVisible 与打开单点 openTorrentDrawer 一律只挡主内容页(形态/视图分叉收归页面级, 此前辅种/追剧页调用 openTorrentDrawer 静默失效: 右键菜单项早已渲染且 hash 正确却点了没反应)+ 两处成员行(辅种明细/追剧集明细)必须有 @dblclick 打开入口(与种子页同款)+ 键盘光标链 _kbRows 纳入展开的成员行(辅种的组下成员/追剧的集下成员, 兑现原注释「成员行 vNext」—— 不在链上则 ↑↓ 走不到、Alt+1~5 解析不出目标)+ 跟随 _kbFollowDrawer / 5s 轮询 tick / 单种流量图 active 三处守卫一律只挡主内容页(换视图即停会让这两页的页签数据停在打开那一刻)
- test_frontend_drawer_open_switch_no_empty_flash: 详情面板显式换目标不闪空态守阵(2026-10-07 报障「切换种子时用户页闪'暂无已连接用户'」) —— openTorrentDrawer 已开(种子形态)重入分支先于重建副作用(同目标短路零副作用, 与 openDrawerTraffic 同口径 -> 换目标交棒 _switchDrawerTarget 软切换: 保留旧数据 + 160ms 延迟遮罩, 与键盘跟随同链路) + 冷启动重建(面板关着/流量形态换形)初值页签 loading 与空列表同帧置位(trackers/files/peers 三 flag 按 initialTab 落真, 详情在途窗口渲染加载态而非空态, 经典链与变体同免), 任一锚被拆或次序倒置即红
- test_drawer_peers_speed_keys_normalized: 抽屉 peers 速度键名适配守阵(2026-10-10 用户报障「种子详情用户页上下行始终为 0」) —— 真 qB sync/torrentPeers 的对端速度字段是 dl_speed / up_speed(与列表侧 torrents/info 的 dlspeed / upspeed 不同名), 前端全部 peers 消费点(经典表 drawerPeerRows + 变体 07/08/09 的 peerList 直读原始对端对象)统一按 dlspeed / upspeed 取名 ⇒ 落袋单点 _fetchDrawerPeers 必须过 _drawerNormPeers 补键(否则取不到值 → 上下行恒 0); 双形态(dict/数组)同归一; 桩服务 scripts/ui_harness.py 合成对端速度键名也必须与真 qB 同形(否则冒烟「看得见速度」而真机恒 0, 测假)
- test_drawer_tpl_trackers_card_uniform_height: 04「状态卡片栅格」卡片同排等高 + 虚拟合并卡去描述守阵(2026-10-10 用户报障「虚拟条目卡片高度与其它的不一致」) —— 口径(用户拍板「同排等高」)= 栅格 .dt04-grid 走 align-items:stretch(同排卡片自动齐平, 虚拟卡与同排实体卡恒等高) + 虚拟合并卡移除设计稿 footer 长描述只留 head + chips; 静态钉 .dt04-grid 必 stretch 且 align-items:start 不得回潮 + 描述文案(私有 tracker 种子…)不得回潮 + virtualCardHtml 内不得再现 dt04-vnote(实体『未启用』卡的短注仍用该类, 禁连类一起删)+ 卡片必须填满栅格格(width:auto 必配, 2026-10-12 用户报障「真实 tracker 卡与虚拟卡之间/虚拟卡后方有长空隙」根治: 引擎行容器继承三皮肤经典表 width:fit-content, grid 下不参与 stretch ⇒ 卡片收缩到内容宽, 两列卡片间 ~700px 永久空洞 + 卡宽随内容漂移)
- test_drawer_list_switch_no_loading_flash_wiring: 抽屉三列表(peers/trackers/files)软切换「不闪」守阵(2026-10-13 用户报障「种子详情用户页切换种子时『暂无已连接用户』闪烁」) —— 真根因(逐帧实测, 探针序列 `E→L→E`): 软切换保留的是**上一个目标的已落袋结果**, 而**空列表(没有对端/没有 tracker)是种子的常态**, 但三列表 fetcher 一律置 loading, 模板门 `loading && 无行` 把这份既有空态顶掉一帧换成「正在加载…」再换回 ⇒ 看起来就是空态在闪。修法 = 换目标窗口(`_drawerSoftSwitch`)内**不置**列表 loading 门(`_drawerListLoadingOn` = `!silent && !this._drawerSoftSwitch`), 保留旧结果直到被新结果取代。!**不得**改成「空响应视为未就绪→延迟渲染/重拉」—— 那会把常态的空推迟(首版固定 1s 重拉被用户否掉:「种子的常态就是没有对端」; 后端对空响应还有 1s 短缓存, 重拉只拿回空包)。本守阵钉静态接线与关键次序(行为回归由 e2e/drawer-switch-no-flash.spec.mjs 逐帧采样: 空态全程在 + 无「正在加载…」+ 无重试请求): ①门抑制单点判据; ②三 fetcher 的 loading 置位都经该单点(直写即回潮); ③标记须在 _loadDrawerTab **之前**置位(三 fetcher 在其内 await 前同步读); ④_stopDrawerPoll **不得**清标记(它在 `_loadDrawerTab→_startDrawerPoll` 途中被调用, 清了等于置前失效); ⑤_drawerSwitchEnd 必须清标记(否则粘住); ⑥旧「延迟重拉」机制(_drawerGraceHold/_DRAWER_GRACE_DELAYS/_drawerPeerCount)不得回潮
- test_dt_table_kernel_single_point: 详情面板表格内核守阵(计划 26-10-13-0811 W1; 用户 2026-10-13 报八项表格症状, 归三个根因簇, 本守阵解簇 A「几何与列被多处各算一遍且零校验」) —— ①三份 manifest 都登记 shared/dt_table.js 且文件在盘上; ②window.DT_TABLE 六口子齐全(layout/assertLayout/checkLabels/registerCell/cellOf/hasArrow); ③几何单一出口: 轨道串/对齐/列键同一个返回值里出来且 gridTemplate 恒等于 tracks.join(" ")(调用方再拼一次就是新事实源, 即红) + 固化宽度覆盖生效; ④L3 列名守卫: 列定义的 label 字段零方向符(扫 app.js 列定义单点 + drawer_tpl 全部变体), 「↑ 占用」不得回潮(密度雷达表头多箭头的出处) + 方向符号只能由排序态单点渲染(表壳 .arrow); ⑤渲染即自查: assertLayout 三处计数(网格轨道/列头格/数据行子格)必须相等, 不相等即报(视觉表现正是「速度列下方异常横带」与「多列内容挤在一起」), 未挂载/未渲染不算不一致(面板没开不得满屏报错); ⑥L2 落点: 单元格渲染器未登记即抛(不许渲染空白)。node 电池真跑 ③⑤⑥(无 node 静默跳过)
- test_drawer_variant_skeleton_single_point: 抽屉变体渲染器族三族重复收敛守阵(issue 26-10-20-2231) —— ①三态空帧单点 H.emptyFrame 在核心 HELPERS(has 闸 + loading→err→empty 优先级 + err 进 title 走 esc)且 04-12 九件桥变体各 1 处接线(槽类名/空态文案逐件对账), 内联三态块零残留(「正在加载…」态帧不得回潮; 01/02/03 裸空态形状不同刻意不收编, 接线数钉 0); ②peers 判据单点 reg.peers 五件(FLAG_META/flagTokens/isBad/bucketOf/isLanIp)在核心 + TPL_REG 挂载 + 07/08/09 经 const P 消费, 本地副本零残留(反向断言); ③dt 值格模板合一: 单一 tpl-aq-dt-peer-cells(类名经 pfx prop 计算, 渲染结果与旧逐字同; dt09 密度雷达特化经 occ prop) + table.js 三组件同名不变共享模板且 pfx/occ 默认值各表自己 + 旧三模板 id 零残留(双模板副本回潮即红)
- test_drawer_prio_text_single_point: 文件优先级码 -> 中文文案表单点守阵(issue 26-10-29-1340) —— 五份内联表(4 份含 legacy 4 档 + setFilePriority 那份缺 4 回退 String(p))收口成核心层 HELPERS.PRIO_TEXT 全键表 + 带回退取文 prioText(p, dash) 挂 reg.helpers; 守阵 = shared/ 递归扫五键表字面仅 1 处(全仓唯一硬约束) + drawer.js 两处(setFilePriority 回执 String(p) 兜底 / drawerFileRows 显示「正常」兜底, 方法内经 window.AQB_DRAWER_TPL_REG 取别名)与 10/11/12(H.prioText 消费)接线 + PRIO_LABEL/本地字面零残留 + node 真跑可达域 p∈{0,1,6,7} 新旧逐字同与 4 档补测 prioText(4, "4")==="高"(ctx-menus.html 静态菜单项文案属自身呈现不在表内, issue 范围外不改; 行为等价 e2e 盯 drawer-content-variant-tables)
- test_drawer_tracker_bucket_text_single_point: tracker 五桶文案表单点守阵(issue 26-10-29-1343) —— 04/05/06 三变体各持一份的桶文案(04/06 BUCKET{text,sev} 两份 + 05 GROUPS{text,cnt} 一份 + 04 PILLS 与 05 计数条内联字面, 共 5 处两形状)收口成核心层 TRACKERS(TRACKER_BUCKETS 全列 text/sev/order/cnt + TRACKER_BUCKET_ORDER 处理序数组, 05 分区顺序与 04/06 sev 升序同源写一次)挂 reg.trackers(reg.peers 同类判据命名空间); 守阵 = 核心表全列逐字钉住 + 桶文案词「未联系」drawer_tpl/ 零命中且核心层恰 1 处 + 三变体 TK 接线与本地 BUCKET/GROUPS/胶囊 text/tip 桶名字面零残留(cls/tip/色族/各版式桶序是呈现语义留各自文件) + node 真跑 text/sev/cnt 与旧表逐字对账(sev 0/1/2/3/9 不动 = 排序权值等价; 变体私有 bucketOf 三份属 R21-B-05/C-05 不在本项; 行为等价 e2e 盯 drawer-trackers-variant-tables / drawer-trackers-reannounce)
- test_drawer_content_file_tree_single_point: content 目录树构建/聚合单点守阵(issue 26-10-29-1343) —— 10/12 各持一份的 newDir/buildTree/aggregate/findNode 四件收口成核心 CONTENT(buildFileTree/findNode)挂 reg.content(reg.peers/reg.trackers 同类「按页签判据命名空间」, 不落 helpers —— 那里只住跨页签骨架机制); 统一节点模型「dirs + 标量 av」(目录 = 子树最低可用性, undefined/null 同为无值 —— 旧 12 把 null 当值聚合、旧 10 的 Infinity 哨兵会渲染出 "Infinity", 均属无判据漂移, 以单点为准); 守阵 = drawer_tpl/ 四函数定义零命中 + 10/12 FT 接线数逐件对账(10: buildFileTree 4 处/findNode 2 处; 12: 各 1 处) + 旧模型字面零残留(minAv/布尔对/裸 availability 叶子字段; 11 的 derive 扁平表第三算法不在本项, 自有模型不查) + 11 头注声明口径以 buildFileTree 为准 + node 真跑语义电池: 新旧三实现(新单点/旧 10/旧 12)对 fixture 组(嵌套两层/根单文件/size 缺失/availability null·负数·小数·零/空目录段/空名回退)逐节点归一化 JSON 全等(旧 10 布尔对 -> av、旧 12 null -> 无值、dirs 统一现算), 另钉 findNode 四态与新节点键集纯净; 行为等价 e2e 盯 drawer-content-variant-tables / drawer-content-dt11-sticky
- test_drawer_tpl_row_memoization_and_cheap_sig: 千级文件列表止血守阵(计划 26-11-02-0351 W1) —— 变体 10/11 行对象按 path 记忆化(输入未变的行复用上一轮对象, 桥 keyed diff 对引用相等行跳渲; _cls 挂行对象, 勾选/折叠/选中态进快照失效面)+ sig 廉价指纹(引用相等 O(1) 快路 / 引用变 O(F) 数值滚动指纹, JSON.stringify(files) 零回潮)+ dt11 O(D×F) 装配冗余消除(stats.ck 随 derive 单遍落账, dirRowOf 的 subtreeFiles 全表 filter 与 chkStateOf 双算退役)+ dt_table.css content-visibility:auto 屏外行渲染税; node 电池真跑两变体 rowsFn: 同一份数据二次派生全行引用相等 / 改一文件 progress 仅该行+祖先链新对象 / 选中与勾选翻转只重装配该行+祖先链且 _cls 正确翻转 / 折叠目录行重装配且子树不再 emit / dt11 目录聚合(大小/进度/文件数/最低可用性)与核心 buildFileTree 口径逐项相等; 静态断言钉 content-visibility/contain-intrinsic-size 规则在 dt_table.css; 行为等价 e2e 盯 dt-live-update(勾选单行长任务 + #8/#9 不跳动)
- test_drawer_general_hr_state_line_parity: 抽屉 general 三变体 HR 结论行对齐守阵(issue 26-10-29-1341) —— 同一颗 hr_triggered 种子的「删除安全档位结论 · 依据」行(hr_safety_text/hr_state_text + hr_reason)三变体都必须消费 hr_state: 01/02 从旧版就有, 03 手抄时字段集停在旧版整段漏掉, 后端 views.py 详情载荷字段齐全、hr.js::hrStateLine 注释成文「详情抽屉要显示这行」, 选 03 就看不到「能否删」是用户可见缺失; 守阵 = 三件源码各含 if (d.hr_state) 闸(空值路径被闸拦住, hr_state 为空不多出空行), 缺件即红
- test_drawer_merge_supply_seq_bump_conditional: 合并补给 seq bump 条件化守阵(issue 26-10-30-0622) —— _drawerMergeSupply 两源都被数据/门挡住时不得前进代际(否则在飞页签取数被打成 stale, finally 刻意不清 loading 门, 门成孤儿无重发路径 ⇒ 合并对双列停「正在加载…」); bump 移进「确有缺口要补」分支, 有缺口时代际仍只前进一次且 tp 对轮询照常起。行为面 node 电池真跑(无 node 静默跳过)
- test_drawer_fetcher_skeleton_single_point
- test_drawer_tpl_data_beat_no_anchor_move
- test_drawer_tpl_default_sel
- test_drawer_tpl_no_table_variants_out_of_scope
- test_drawer_tpl_render_error_fallback_default

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console, 按 _UI_ALL 枚举的接线守阵随常量自动收编; 单独点名的成对面(qb-tabs 生效面/
  --qb-gap-hatch 令牌/纵轴控件版式/.opt-pill.is-gated/.meta-dialog/ctx-item hover)已显式加 flux 档。
"""

import json

import os

import re

import shutil

import subprocess

from pathlib import Path

from auto_qb.webui.commands import REANNOUNCE_BLOCKED_STATES as _PY_BLOCKED_STATES

from auto_qb.webui.commands import REANNOUNCE_INACTIVE_SKIP as _PY_INACTIVE_SKIP

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
)


def _drawer_fetch_parts(store_js: str):
    """抽出「四 fetcher 唯一取数骨架」与「四数据源差异表」两段源文本(R21-A-01, 2026-10-21 收敛)。

    收敛前 detail/trackers/files/peers 各有一份 ~22 行的落地次序(每份三道 _drawerStale), 守阵只能
    逐个 fetcher 用正则钉次序 —— 而**新增第五份**、或某份偷偷改掉次序而正则仍匹配, 都拦不住。
    收敛后次序只在 `_fetchDrawerSource` 一份、差异项在顶层 `_DT_FETCH` 表, 故守阵改为:
    次序在骨架里钉一次 + 差异项在表里逐字段钉 + 四个具名入口只许是薄壳(见
    `test_drawer_fetcher_skeleton_single_point`)。

    返回 (骨架 body, 差异表 body); 两段缺失即判红(改名/挪走都要同步这里, 不许静默失配)。
    """
    skel = re.search(r"async _fetchDrawerSource\(src, silent = false, seq = 0\) \{(.*?)\n    \},", store_js, re.S)
    assert skel, "drawer_store.js 找不到四 fetcher 的唯一骨架 _fetchDrawerSource(改名或挪走了? 同步本守阵)"
    table = re.search(r"const _DT_FETCH = \{(.*?)\n\};", store_js, re.S)
    assert table, "drawer_store.js 找不到差异项表 _DT_FETCH(四源的端点/归一/状态键/空值形状单点)"
    return skel.group(1), table.group(1)


def test_frontend_drawer_form_judge_single_point():
    """面板形态判据收口守阵(计划 26-10-11-2106 W3; W6 收全)

    面板两形态由一个字段裁决: `drawer.kind === "seed"`(种子详情, 五页签)/ `"traffic"`(qB 口径
    流量图, 三挂点: 全局/分组/单种)。表 B 问题 4「同功能多形态各一份, 改一处漏一处」正是从
    「同一个判据散点比较」长出来的 —— W3 收成 drawer.js 的 drawerIsSeed / drawerIsTraffic 两个
    派生单点(自带 `this.drawer &&` 守卫, 顺带替掉各处手抄的假实例防御)。本守阵钉四件:

    1. **字面量只许出现在定义处**: drawer.js 恰两处, 其余三件(menu.js / shortcuts.js /
       tpl/drawer.html)与 qb_traffic_chart.js 零处 —— 新增一处散点比较即红;
    2. **调用点确实走单点**(逐个钉, 不按总数): 抽掉任一处 = 那处退回散点, 将来改 kind 词汇时
       静默漏改(这正是坑档 pitfalls/web-ui/drawer-multi-form-hosts 那一族的成因);
    3. **判据自带守卫**: 全局 mixin 会把 computed 注入 <transition> 的 BaseTransition 假实例,
       那时 this.drawer 不存在 —— 缺 `this.drawer &&` 即抛(旧写法靠每个调用点自己防, 漏一处
       就是 pageerror)。
    4. **W6 兑现 W3 停手点**: qb_traffic_chart.js 的 _QB_SCOPES.active/stale 与 qbCurScope /
       openDrawerTraffic 短路原写 `drawer.kind === "traffic"/"seed"` 字面量(W3 停手点「uPlot 与
       图表模块零改动」), W6 起改吃单点 —— 散点不得回潮。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    menu_js = open(os.path.join(shared, "menu.js"), encoding="utf-8").read()
    shortcuts_js = open(os.path.join(shared, "shortcuts.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    traffic_js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()

    # 1. 两个派生单点本体(判据值 + 假实例守卫)
    for name, kind in (("drawerIsSeed", "seed"), ("drawerIsTraffic", "traffic")):
        m = re.search(rf"^    {name}\(\) \{{\n(.*?)\n    \}},", drawer_js, re.M | re.S)
        assert m, f"drawer.js 缺形态判据单点 {name}()(散点比较会重新长回来)"
        body = m.group(1).strip()
        assert body == f'return !!(this.drawer && this.drawer.kind === "{kind}");', \
            f"{name} 判据形态漂移(须为 `return !!(this.drawer && this.drawer.kind === \"{kind}\");`," \
            f" 实际: {body})"

    # 2. 字面量只许出现在定义处
    assert drawer_js.count("this.drawer.kind ===") == 2, \
        "drawer.js 里 drawer.kind 字面量必须恰两处(两个判据的定义), 不得再散落调用点"
    for name, text in (
        ("menu.js", menu_js),
        ("shortcuts.js", shortcuts_js),
        ("tpl/drawer.html", drawer_tpl),
    ):
        assert "drawer.kind" not in text, \
            f"{name} 仍写 drawer.kind 散点比较(形态判据必须走 drawerIsSeed / drawerIsTraffic 单点)"
    assert 'drawer.kind === "traffic"' not in traffic_js and 'drawer.kind === "seed"' not in traffic_js, \
        "qb_traffic_chart.js 仍写 drawer.kind 散点比较(W6 已改吃单点, W3 停手点豁免已摘)"

    # 3. 调用点逐个钉(全部形态判据调用面)
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    assert "dtMenuMergeOn() {\n        return this.drawerIsSeed;" in core, \
        "drawer_templates.js dtMenuMergeOn 未走判据单点(右键菜单「合并页签」项的放行判据; W7 随选择层归位原家)"
    assert "drawer.kind" not in core, \
        "drawer_templates.js 仍写 drawer.kind 散点比较(形态判据必须走 drawerIsSeed / drawerIsTraffic 单点)"
    assert "if (!this.drawerIsSeed && !this.drawerIsTraffic) return;" in menu_js, \
        "menu.js openDrawerMenu 未走判据单点(seed/traffic 两形态放行, 流量形态模板选择靠它)"
    assert shortcuts_js.count("this.drawerIsSeed") == 2 and shortcuts_js.count("this.drawerIsTraffic") == 1, \
        "shortcuts.js 未全走判据单点(Alt+1..5 切页签 / Alt+3 开合面板 / Ctrl+\\ 全局流量图 三处)"
    assert drawer_js.count("this.drawerIsSeed") == 2, \
        "drawer.js 未全走判据单点(openTorrentDrawer 已开重入分支 + drawerAfterEnterHook 让位)"
    for form, what in (
        (':class="{ \'drawer-traffic\': drawerIsTraffic }"', "面板 .drawer-traffic 布局类"),
        (":aria-label=\"drawerIsTraffic ? 'qB 口径流量图' : '种子详情'\"", "面板 aria-label"),
        ('<aq-drawer-head v-if="drawerIsTraffic"', "流量形态头部调用点"),
    ):
        assert form in drawer_tpl, f"tpl/drawer.html 的{what}未走判据单点: {form}"
    # 4. W6: qb_traffic_chart.js 全量吃单点(_QB_SCOPES 谓词 t.drawerIs* + this.drawerIs* 调用面)
    assert traffic_js.count("t.drawerIsTraffic") == 4 and traffic_js.count("t.drawerIsSeed") == 2, \
        "qb_traffic_chart.js _QB_SCOPES 谓词未全走单点(global/group 各 active+stale 用 drawerIsTraffic," \
        " torrent active+stale 用 drawerIsSeed)"
    assert traffic_js.count("this.drawerIsTraffic") == 2 and traffic_js.count("this.drawerIsSeed") == 1, \
        "qb_traffic_chart.js 调用面未全走单点(qbCurScope 两形态分派 + openDrawerTraffic 同目标短路)"


_DT_REGISTRY_NODE_PROBE = r"""
const fs = require("fs");
global.window = {};
/* localStorage 桩(readSel/dtPersistSel 走它); document 保持 undefined —— 核心的 dtInjectCss
 * 有 typeof document 守卫, node 探针环境跳过 CSS 注入。 */
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
eval(fs.readFileSync(process.argv[1], "utf8"));
const reg = window.AQB_DRAWER_TPL_REG;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const CLASSIC = JSON.stringify({ general: "classic", trackers: "classic", peers: "classic", content: "classic", traffic: "classic" });

ok("五页签注册表", JSON.stringify(reg.tabs) === JSON.stringify(["general", "trackers", "peers", "content", "traffic"]));
ok("无存储全 classic(P-01)", JSON.stringify(reg.readSel()) === CLASSIC);
store["autoqb.ui.drawerTpl"] = '{"general":"t1","traffic":123,"peers":"classic"}';
ok("脏值/未注册 id/数字值一律 classic", JSON.stringify(reg.readSel()) === CLASSIC);
store["autoqb.ui.drawerTpl"] = "not-json{";
ok("坏 JSON 回落 classic", JSON.stringify(reg.readSel()) === CLASSIC);
store["autoqb.ui.drawerTpl"] = '{"general":"t1"}';
reg.register({ id: "t1", tab: "general", label: "T1", render() {} });
ok("注册后合法 id 被白名单接受", reg.readSel().general === "t1");
ok("其余页签不受影响", reg.readSel().trackers === "classic");
let threw = "";
try { reg.register({ id: "t1", tab: "general", render() {} }); } catch (e) { threw = e.message; }
ok("重复 (id, tab) fail-fast", threw.indexOf("duplicate") >= 0);
threw = "";
try { reg.register({ id: "t2", tab: "bogus", render() {} }); } catch (e) { threw = e.message; }
ok("非法 tab fail-fast", threw.indexOf("bad tab") >= 0);
threw = "";
try { reg.register({ id: "a b", tab: "peers", render() {} }); } catch (e) { threw = e.message; }
ok("非法字符 id fail-fast", threw.indexOf("bad id") >= 0);
threw = "";
try { reg.register({ id: "t3", tab: "peers" }); } catch (e) { threw = e.message; }
ok("缺 render fail-fast", threw.indexOf("render") >= 0);
ok("dtHtml 插值自动转义", reg.dtHtml`<b>${"<script>&\"'"}</b>` === "<b>&lt;script&gt;&amp;&quot;&#39;</b>");
ok("dtRaw 显式豁免", reg.dtHtml`${reg.dtRaw("<i>ok</i>")}` === "<i>ok</i>");
ok("options 不含 classic(classic 恒由模板置首位)",
  JSON.stringify(reg.options("general")) === JSON.stringify([{ id: "t1", label: "T1" }]));
ok("mixin 挂上 window.AQB_DRAWER_TPL", typeof window.AQB_DRAWER_TPL.methods.dtMenuPick === "function"
  && typeof window.AQB_DRAWER_TPL.computed.dtMenuTab === "function");

const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed }));
if (failed.length) process.exit(1);
"""


def test_drawer_tpl_registry_wiring():
    """详情面板模板核心层接线守阵(plan 26-10-06-0838 S1) —— 三份 manifest 成对含核心且装载序正确;
    变体文件 (id, tab) 唯一且 tab 合法; 核心含 dtHtml / autoqb.ui.drawerTpl 单点; drawer.js 一行式
    钩子四类齐全; drawer.html 宿主成对加挂 + 合并列 data-dt-tab(2026-10-10 头部切换器迁右键,
    .dt-select 退役); 变体 label 展示名禁档位后缀(Q4, 报告
    26-10-07-0542 —— 档位只是物理形态且三档语义全收进本变体, 写进名字冗余误导); dt* 成员全仓
    无重名(mixin 合并后者覆盖前者, 静默不报错 —— drawer_templates.js 书写形态不在
    _scan_mixin_wiring 的扫描面内, 此处补钉)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    tabs = ("general", "trackers", "peers", "content", "traffic")

    # 1. 三份 manifest 成对含核心, 装载序 drawer.js < 核心 < state.js(后者是硬约束:
    #    state data() 调 initialDrawerTpl -> readSel 白名单依赖注册表, 序错则已存合法 id 静默回落 classic)
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/drawer_templates.js" in scripts, f"{ui}: manifest 缺模板核心层"
        assert scripts.index("/shared/drawer.js") < scripts.index("/shared/drawer_templates.js"), \
            f"{ui}: 核心必须排在 drawer.js 之后(同域阅读序, 守阵钉住防漂移)"
        assert scripts.index("/shared/drawer_templates.js") < scripts.index("/shared/state.js"), \
            f"{ui}: 核心必须排在 state.js 之前(state data() 调 initialDrawerTpl, 序错 = 启动白屏)"

    # 2. 核心单点: 注册表 / dtHtml 转义标签模板 / autoqb.ui.drawerTpl 键 / CSS 注入 data-dt 单点
    assert "window.AQB_DRAWER_TPL_REG" in core, "核心缺注册表单点(变体自注册入口)"
    assert "dtHtml" in core and "dtRaw" in core, "核心缺 dtHtml/dtRaw 转义标签模板(XSS 单点收口)"
    assert '"autoqb.ui.drawerTpl"' in core or "'autoqb.ui.drawerTpl'" in core, \
        "核心缺 autoqb.ui.drawerTpl 存储键(选择持久化单点)"
    assert "data-dt" in core, "核心缺 CSS 注入单点(style data-dt)"
    for tab in tabs:
        assert f'"{tab}"' in core, f"核心注册表缺页签 {tab}"

    # 3. 变体文件(S1 为 0, 断言按"当前已注册变体集合"写, 不写死 15):
    #    每个变体必须 (id, tab) 唯一、tab 合法、且三份 manifest 成对登记
    vdir = os.path.join(shared, "drawer_tpl")
    seen_pairs = set()
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert scripts.index("/shared/drawer_templates.js") < scripts.index("/shared/state.js")
    if os.path.isdir(vdir):
        for name in sorted(os.listdir(vdir)):
            if not name.endswith(".js"):
                continue
            text = open(os.path.join(vdir, name), encoding="utf-8").read()
            mo = re.search(r'id:\s*"([^"]+)"\s*,\s*tab:\s*"([^"]+)"', text)
            assert mo, f"drawer_tpl/{name}: 缺 (id, tab) 注册对(变体自注册形态漂移)"
            vid, vtab = mo.group(1), mo.group(2)
            assert vtab in tabs, f"drawer_tpl/{name}: 非法 tab {vtab}"
            assert (vid, vtab) not in seen_pairs, f"drawer_tpl/{name}: (id, tab) 重复 ({vid}, {vtab})"
            seen_pairs.add((vid, vtab))
            # Q4: label 展示名禁档位后缀 —— 档位(tall/low/collapsed)只是物理形态, 三档语义
            # 全收进本变体(各文件头注声明), 写进下拉展示名冗余且误导(报告 26-10-07-0542 §2 Q4)
            mo = re.search(r'label:\s*"([^"]+)"', text)
            assert mo, f"drawer_tpl/{name}: 缺 label 注册字段(变体自注册形态漂移)"
            bad = [s for s in ("(高)", "(矮)", "(收起)") if s in mo.group(1)]
            assert not bad, \
                f"drawer_tpl/{name}: label \"{mo.group(1)}\" 含档位后缀 {bad}(Q4: 档位写进展示名冗余误导, 改描述性命名)"
            assert "reg.register(" in text or "AQB_DRAWER_TPL_REG.register(" in text, \
                f"drawer_tpl/{name}: 缺 register 调用"
            for ui in _UI_ALL:
                assert f"/shared/drawer_tpl/{name}" in _ui_manifest(ui)["scripts"], \
                    f"{ui}: manifest 缺变体 drawer_tpl/{name}"

    # 4. 数据层一行式钩子四类齐全(方法本体在核心层, 这里只有调用点;
    #    W1 起 _loadDrawerTab/四 fetcher 落 drawer_store.js, 调用点随迁)
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()
    m = re.search(r"_loadDrawerTab\(tab\) \{\n(.*?)\n    \},", store_js, re.S)
    assert m and "this._dtSync()" in m.group(1), "_loadDrawerTab 尾部缺 _dtSync(换页签不挂/不卸变体)"
    # R21-A-01(2026-10-21): 四 fetcher 收敛为「唯一骨架 + 差异表」—— 通知点由骨架按 src 发一份,
    # 四个源是否都在表里、通知时机是否仍然分化, 改在表上钉(逐 fetcher 钉已不可能: 具名入口是薄壳)。
    skel, ftable = _drawer_fetch_parts(store_js)
    for typ in ("detail", "trackers", "files", "peers"):
        assert re.search(rf"^  {typ}: \{{", ftable, re.M), f"差异表缺 {typ} 源(该源没有取数差异项 = 拉不到数)"
    assert "this._dtNotify(src);" in skel, "骨架落袋/落定处缺 _dtNotify(变体只在 _dtNotify 时重渲染)"
    # 4a. 列表三源的通知必须在 loading 清掉之后(变体只在 _dtNotify 时重渲染,
    #     通知先于清 loading = 空列表停在"正在加载…"到下一拍 5s 轮询; 2026-10-07 用户页报障。
    #     detail 不在列: general 变体不渲染 loading 态, 经典层走 Vue 响应式无此窗口 —— 故
    #     notifyAtLand 只在 detail 为 true, 其余三源走 finally 那条)
    clear = skel.find("this.drawer[cfg.loadingKey] = false")
    notify_after_clear = skel.find("if (!cfg.notifyAtLand) this._dtNotify(src);")
    assert clear != -1 and notify_after_clear != -1 and clear < notify_after_clear, \
        "列表源 _dtNotify 必须在 loading 清掉之后(次序反 = 空列表停\"正在加载…\"一拍轮询)"
    assert ftable.count("notifyAtLand: true") == 1 and ftable.count("notifyAtLand: false") == 3, \
        "通知时机分化漂移(应只有 detail 落袋即通知, 三列表源清 loading 后通知)"
    m = re.search(r"closeDrawer\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert m and "this._dtUnmountAll()" in m.group(1), "closeDrawer 缺 _dtUnmountAll(变体定时器/监听不清)"

    # 5. drawer.html 加挂面: 四内容页签各一个宿主(单栏 x4 + 合并双列 x4 共用同一模板)
    #    2026-10-10 模板选择迁右键(用户动议「在对应的区域弹右键」): 头部 .dt-select 下拉退役,
    #    选择入口移到 openDrawerMenu 右键菜单; 合并双列各列带 data-dt-tab(右键按命中区域定页签)
    #    2026-10-14: 流量变体(13/14/15)与图前/图后双宿主(traffic-pre/post)已移除 —— 流量正文
    #    由模板内联的经典图渲染, 无变体宿主。
    #    2026-10-30 (26-10-29-1354): 非合并态四宿主/桥的页签清单收进 dtTabItems(drawer.js 对
    #    单点 DT_TAB_LABELS 的投影) —— 模板不再逐字写四个宿主 div, 页签名静态字面量归零。
    assert drawer_tpl.count('v-for="t in dtTabItems"') == 2, \
        "drawer.html 非合并态宿主与桥应各有一个 dtTabItems v-for(共两处; 页签清单第二份拷贝回潮)"
    m = re.search(r"const DT_TAB_LABELS = \{([^}]*)\}", drawer_js)
    assert m and set(re.findall(r"(\w+):", m.group(1))) == {"general", "trackers", "peers", "content"}, \
        "drawer.js DT_TAB_LABELS 应恰四键(general/trackers/peers/content; 宿主页签清单的投影单点)"
    assert "traffic-pre" not in drawer_tpl and "traffic-post" not in drawer_tpl, \
        "drawer.html 又出现流量变体宿主(traffic-pre/post) —— 流量页签已无变体(2026-10-14)"
    assert 'class="dt-select"' not in drawer_tpl, \
        "drawer.html 仍残留 .dt-select 头部下拉(2026-10-10 模板选择已迁右键菜单)"
    assert "dtPick(" not in drawer_tpl and "dtTplOptions" not in drawer_tpl and "dtTplCurrent" not in drawer_tpl, \
        "drawer.html 仍引用退役的选择器 API(dtPick/dtTplOptions/dtTplCurrent)"
    # W4: 合并列由 dtPairCols v-for 渲染, data-dt-tab 为动态绑定单点(:data-dt-tab="col.tab",
    #     四页签一份数据面; 静态逐列字面量已退役)
    assert ':data-dt-tab="col.tab"' in drawer_tpl, \
        "drawer.html 合并列缺 :data-dt-tab=\"col.tab\" 动态绑定(右键按命中区域定位目标页签)"
    assert drawer_tpl.count(":data-dt-tab=") == 1, \
        "drawer.html :data-dt-tab 绑定超一处(应由 dtPairCols v-for 单点渲染)"
    # W2(计划 26-10-11-2106): 「经典」收回 Vue 组件(drawer_tabs.js) —— drawer_pages 经典插件
    # 已删(表格统一接公共表壳, 本计划正主), 不得复活; 正文走 dtVueTab v-if 组件 / v-else 宿主
    # 互斥双分支(同一 data-dt-host 全 DOM 唯一), 显隐门 dtHostOn 在组件根与宿主上同源。
    assert not os.path.isdir(os.path.join(shared, "drawer_pages")), \
        "drawer_pages/ 不得复活(W2 经典链已收回 Vue 组件并接公共表壳)"
    # 2026-10-14: 四内容页签的经典渲染链(drawer_tabs.js / drawer-tabs.html / aq-drawer-*)整体
    # 移除 —— drawer.html 正文恒走变体宿主, 不得再有 dtVueTab 分支(注释不算, 先剥注释再判)。
    tpl_code = re.sub(r"<!--.*?-->", "", drawer_tpl, flags=re.S)
    assert "dtVueTab" not in tpl_code, \
        "drawer.html 又出现 dtVueTab 分支 —— 经典渲染链已整体移除(2026-10-14), 正文恒走变体宿主"
    assert "aq-drawer-general" not in tpl_code and "aq-drawer-trackers" not in tpl_code \
        and "aq-drawer-peers" not in tpl_code and "aq-drawer-content" not in tpl_code, \
        "drawer.html 又引用经典页签组件(aq-drawer-*) —— 四组件已删(2026-10-14)"
    # 2026-10-30 (26-10-29-1354): 非合并态四宿主改 dtTabItems v-for 驱动 —— :data-dt-host 动态
    # 绑定恰两处(合并列 col.tab + 非合并 v-for t.v), 静态逐页签字面量归零; 宿主与桥两个 v-for
    # 分立(兄弟序 = 4 宿主 + 4 桥), 不得合成一个 v-for 插花。
    assert drawer_tpl.count(":data-dt-host=") == 2, \
        "drawer.html :data-dt-host 绑定应恰两处(合并列 :data-dt-host=\"col.tab\" + 非合并 :data-dt-host=\"t.v\")"
    assert ':data-dt-host="t.v"' in drawer_tpl and ":key=\"'dth-' + t.v\"" in drawer_tpl, \
        "drawer.html 非合并态宿主未走 dtTabItems v-for(页签清单第二份拷贝回潮)"
    assert "['general', 'trackers'" not in drawer_tpl, \
        "drawer.html 桥循环又写死页签名数组(dtTabItems 单点回潮)"
    for tab in ("general", "trackers", "peers", "content"):
        assert f'data-dt-host="{tab}"' not in drawer_tpl, \
            f"drawer.html: data-dt-host={tab} 静态字面量回潮(应由 dtTabItems v-for 驱动)"
    # R2 S2/S3 接线 + R3 修订(计划 26-10-09-2219 R3): 合并开关显式建字段 + 双列宿主 + 右键单开关
    assert "drawerMerge: initialDrawerMerge()" in state_js, "state.js 缺 drawerMerge 显式建字段(vue-reactivity 坑)"
    assert "dtWinW:" in state_js, "state.js 缺 dtWinW 显式建字段(dtSplitOn 响应式消费)"
    assert "drawerMenu: { visible: false, x: 0, y: 0, tab: \"\" }" in state_js, \
        "state.js 缺 drawerMenu 显式建字段(含 tab 右键目标页签, undefined 是响应式盲区)"
    assert 'class="drawer-split"' in drawer_tpl, "drawer.html 缺合并双列宿主(R2 S2)"
    assert "@contextmenu.prevent=\"openDrawerMenu($event)\"" in drawer_tpl, "drawer.html 缺右键菜单接线(R2 S3)"
    assert "function initialDrawerMerge()" in app_js, "app.js 缺 initialDrawerMerge"
    # R3 钉子: 开关模型(off|on, 列组由当前页签所属对决定) + 页签栏合并两页签 + 单开关入口。
    # 旧两选项模型(标志值 gc/tp 决定渲染哪一对)是 R2 空列 bug 的根 —— dtSetMerge 不得残留,
    # 否则新旧两套模型并存(标志值与当前页签各说各话)。
    # W4(计划 26-10-11-2106): 合并机械收进 drawer.js(面板核心) —— 判据/方法 4 空格缩进;
    # dtMergeTabActive 已随「高亮与列组同源」删除(模板内联 mt.id === dtPair), 不得回潮;
    # 核心层(选择层)零合并成员(双份判据 = R2 空列 bug 根因形态)。
    for member in ("dtMergeOn", "dtMergeTabsOn", "dtPair", "dtMergeTabPick", "dtToggleMerge"):
        assert re.search(rf"^    {member}[(:]", drawer_js, re.M), f"drawer.js 缺 R3 合并成员 {member}"
        assert not re.search(rf"^      {member}[(:]", core, re.M), \
            f"drawer_templates.js 不得自建合并成员 {member}(W4 起单点在 drawer.js)"
    assert "dtMergeTabActive" not in core and "dtMergeTabActive" not in drawer_js \
        and "dtMergeTabActive" not in drawer_tpl, \
        "dtMergeTabActive 不得残留(W4 已删: 高亮判据必须与列组同源, 模板内联 mt.id === dtPair)"
    # W4: 核心层零自建合并数据面(对结构/宽度计算单点在 drawer.js AQB_DRAWER_MERGE 命名空间);
    # _dtMountSplit 挂载机械留在核心层, 只做 pairOf 机械消费(见下一条 pin), 不得复制对数据。
    assert "mergeMinWidth" not in core and "mergePairs" not in core and "mergeValues" not in core, \
        "drawer_templates.js 不得自建合并对数据/宽度计算(W4 起单点在 drawer.js)"
    m = re.search(r"_dtMountSplit\(\) \{\n(.*?)\n      \},", core, re.S)
    assert m and "window.AQB_DRAWER_MERGE.pairOf" in m.group(1), \
        "_dtMountSplit 必须经 AQB_DRAWER_MERGE.pairOf 消费对结构(W4: 插件层零自建映射)"
    assert 'this._unwatchMerge = this.$watch("drawerMerge"' in drawer_js \
        and 'window.addEventListener("resize", this._mergeOnResize)' in drawer_js, \
        "drawer.js 缺合并两条监听(resize 回写 dtWinW + drawerMerge $watch; W4 自核心层注册)"
    ctx_menus_tpl = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()
    assert "dtSetMerge" not in core and "dtSetMerge" not in ctx_menus_tpl, \
        "dtSetMerge 残留(R3 已改单开关 dtToggleMerge; 双模型并存 = 空列 bug 根因复发)"
    assert "dtToggleMerge()" in ctx_menus_tpl, "ctx-menus 缺合并单开关入口(dtToggleMerge)"
    # W4: 合并页签按钮与标签由 dtMergeTabList(对单点)经 <aq-seg> 驱动, 模板零硬编码;
    # 标签文案单点在 drawer.js MERGE_PAIRS(列头 .dt-col-head 同一份对数据)。
    # 26-10-20-2231: 两态都改 <aq-seg> —— 非合并态那四个按钮原先是 DT_TAB_LABELS 的第二份拷贝,
    # 现由 dtTabItems 投影; 高亮判据从内联 `mt.id === dtPair` 变为组件内 `v === value`。
    assert ':items="dtMergeTabList" :value="dtPair"' in drawer_tpl \
        and ':items="dtTabItems" :value="drawer.tab"' in drawer_tpl, \
        "drawer.html 页签栏缺 <aq-seg> 数据驱动(按钮清单/高亮与列组同源, 模板零硬编码按钮)"
    assert re.search(r"dtMergeTabList\(\) \{\n\s*return window\.AQB_DRAWER_MERGE\.PAIRS\.map\(", drawer_js), \
        "dtMergeTabList 必须投影自 MERGE_PAIRS(对结构仍只有一份)"
    for label in ("常规&内容", "Tracker&用户"):
        assert f'label: "{label}"' in drawer_js, f"drawer.js 合并对缺标签 {label}(W4 标签随对数据走)"
    assert ':data-merge="dtPair"' in drawer_tpl, \
        "drawer.html 双列列组必须读 dtPair(R3 bug: 按标志值渲染固定一对 -> 切对页签列头在而宿主空)"

    # 6. state/app 接线 + dt* 成员全仓无重名(mixin 覆盖形态, 静默故障)
    assert "drawerTplSel: initialDrawerTpl()" in state_js, "state.js 缺 drawerTplSel 显式建字段(vue-reactivity 坑)"
    assert "function initialDrawerTpl()" in app_js, "app.js 缺 initialDrawerTpl"
    assert "app.mixin(window.AQB_DRAWER_TPL)" in app_js, "app.js 未注入 AQB_DRAWER_TPL(核心方法域整体消失)"
    dt_members = {
        n
        for n in re.findall(r"^      (?:async )?([A-Za-z_$][\w$]*)\s*[(:]", core, re.M)
        if n.startswith("dt") or n.startswith("_dt")
    }  # 只收 dt* 成员(裸 if/for 同缩进形态不收)
    assert {"dtMenuPick", "dtHostOn", "_dtSync", "_dtNotify", "_dtUnmountAll"} <= dt_members, \
        "核心方法面清单与守阵预期漂移, 同步本守阵"
    for path, rel in _app_bundle_files():
        if rel == "shared/drawer_templates.js":
            continue
        other = open(path, encoding="utf-8").read()
        for name in dt_members:
            assert not re.search(rf"^      (?:async )?{name}\s*[(:]", other, re.M) \
                and not re.search(rf"^    (?:async )?{name}\s*[(:]", other, re.M), \
                f"{rel} 与核心层成员重名 {name}(mixin 合并后者覆盖前者, 静默不报错)"


def test_drawer_tpl_variant_width_discipline():
    """详情面板变体宽度纪律守阵(Q1, 报告 26-10-07-0542) —— 核心注入 CSS 必须含四页签宿主的
    max-width 居中收口(15 个变体单点共享, 变体文件零复刻; traffic 双宿主排除 —— 图本体/工具条
    归经典链恒满宽, 13/15 KPI 头行限宽会与图缘错位, 14 解读栏自带 288px 固定右栏无拉伸);
    全部变体与核心注入 CSS 禁 justify-content:space-between(4K 下 label/value 两端推开病根,
    改为标签在前值紧随; 非 kv 场景确需两端分布须显式改本守阵并注明场景)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    # 注入的 CSS 字符串在 JS 源里是双引号转义形态(\"), 先还原再对选择器做子串断言
    core_css = core.replace('\\"', '"')

    # 1. 共享 max-width 收口单点: 四页签宿主各出现在限宽规则里, 值与居中写法一起钉住。
    #    R2 S1(计划 26-10-09-2219): 收口收窄到 .dt-tpl(变体挂载态) —— classic 也挂进宿主
    #    (页插件化)而经典链历史上恒满宽, 限宽误伤即行为回归; 核心挂载时按 entry 加/摘类。
    for tab in ("general", "trackers", "peers", "content"):
        assert f'.dt-host.dt-tpl[data-dt-host="{tab}"]' in core_css, \
            f"核心缺 {tab} 宿主限宽收口(变体内容层 4K 等分拉伸复发)"
    assert "max-width: 1400px; margin-left:auto; margin-right:auto" in core_css, \
        "核心宿主收口缺 max-width/margin 居中(规则形态漂移, 同步本守阵)"

    # 2. traffic 双宿主不得进限宽收口(与经典链图缘对齐, 判据见核心注入处注释)
    for slot in ("traffic-pre", "traffic-post"):
        hit = [l for l in core_css.splitlines() if f'data-dt-host="{slot}"' in l]
        assert not hit, \
            f"traffic 宿主 {slot} 不得进限宽收口(图本体归经典链恒满宽, 限宽与图缘错位)"

    # 3. label/value 两端推开零容忍: 15 个变体 + 核心注入 CSS(比较前去空格, 兼容空格写法)
    vdir = os.path.join(shared, "drawer_tpl")
    for name in sorted(os.listdir(vdir)):
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "justify-content:space-between" not in text.replace(" ", ""), \
            f"drawer_tpl/{name}: justify-content:space-between 复活(Q1 label/value 两端推开病根; 非 kv 场景确需请改本守阵并注明)"
    assert "justify-content:space-between" not in core.replace(" ", ""), \
        "核心注入 CSS 不得用 justify-content:space-between(同上)"


def test_drawer_tpl_trackers_card_uniform_height():
    """04「状态卡片栅格」卡片同排等高 + 虚拟合并卡去描述守阵(2026-10-10 用户报障) ——
    缺陷: 虚拟合并卡沿用设计稿 footer 的长描述后, 卡身比实体卡高出一截 —— 同一栅格里同为
    「未启用」的实体卡(真浏览器实测 69px)与虚拟卡(100px)高度不一致。口径(用户拍板「同排
    等高」): 栅格走 align-items:stretch, 同排卡片自动齐平(虚拟卡与其同排实体卡恒等高, 无需
    给虚拟卡任何特判); 虚拟合并卡的描述行整个移除, 只留 head + chips。静态钉四件事:
    ①stretch 机制在且 align-items:start 不得回潮; ②描述文案不得回潮; ③虚拟合并卡装配
    (virtualRowOf, U3 起为 rowsFn 合成行)内不得再出现 dt04-vnote(实体『未启用』卡的同名
    短注是另一回事, 别顺手连类一起删); ④卡片必须填满栅格格(width:auto 必配)——
    2026-10-12 用户报障「真实 tracker 卡与虚拟卡之间/虚拟卡后方有长空隙」根治: 引擎行容器
    被三皮肤经典表 CSS 继承 width:fit-content(与 min-width:100% 成对, 经典 flex 列容器里
    靠 min-width 兜底成整行宽); 本栅格是 grid + min-width:0, fit-content 直接生效 ⇒ 卡片
    收缩到内容宽(实测 ~330px / 695px 格) = 两列卡片间 ~700px 永久空洞 + 卡宽随内容漂移
    (实体 330 vs 虚拟 378, 违反「宽度统一」)。grid 项 width:auto + 默认 justify-self:
    stretch 才填格。U3 改版: 卡片 = 引擎行容器(.group-row 样成卡), 双列栅格落
    .dt04-list .group-table(引擎 .group-table 基础是 flex 列, 变体覆盖为 grid)。"""
    vdir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    name = "04-trackers-status-cards-tall.js"
    text = open(os.path.join(vdir, name), encoding="utf-8").read()

    # 1. 同排等高机制: .dt04-list .group-table 必须 grid + stretch(与 align-items:start 互斥)
    grid = [l for l in text.splitlines() if ".dt04-list.group-table{display:grid" in l.replace(" ", "")]
    assert grid, f"drawer_tpl/{name}: 缺 .dt04-list .group-table 双列栅格规则(形态漂移, 同步本守阵)"
    assert "align-items:stretch" in text.replace(" ", ""), \
        f"drawer_tpl/{name}: 卡片栅格必须 align-items:stretch(同排等高口径; 缺则虚拟卡与同排实体卡高度不一致复发)"
    assert "align-items:start" not in text.replace(" ", ""), \
        f"drawer_tpl/{name}: 出现 align-items:start(卡片栅格等高机制被改回, 2026-10-10 报障复发)"

    # 2. 虚拟合并卡: 描述文案 + 描述行都不许回来
    assert "私有 tracker 种子" not in text, \
        f"drawer_tpl/{name}: 虚拟条目描述文案回潮(2026-10-10 用户要求移除)"
    m = re.search(r"function virtualRowOf\([^)]*\) \{(.*?)\n  \}", text, re.S)
    assert m, f"drawer_tpl/{name}: virtualRowOf 形态漂移(守阵正则失配, 同步本守阵)"
    assert "dt04-vnote" not in m.group(1), \
        f"drawer_tpl/{name}: 虚拟合并卡又挂 dt04-vnote 描述行(卡身再次高出实体卡)"

    # 3. 实体「未启用」卡的短注(vnote 类)必须保留 —— 别把整个类连带删掉
    assert ".drawer .dt04-vnote {" in text, \
        f"drawer_tpl/{name}: .dt04-vnote 类被整体删除(实体『未启用』卡的短注仍用它)"

    # 4. 卡片必须填满栅格格(2026-10-12 用户报障「真实卡与虚拟卡之间/虚拟卡后方有长空隙」根治):
    #    引擎行容器被三皮肤经典表 CSS 继承 width:fit-content(配 min-width:100%, 经典 flex
    #    列容器里靠 min-width 兜底 = 整行宽); 本栅格是 grid + min-width:0 ⇒ fit-content 直接
    #    生效, 卡片收缩到内容宽(实测 ~330px / 695px 格)= 两列卡片间 ~700px 永久空洞 + 卡宽
    #    随内容漂移(实体 330 vs 虚拟 378, 违反「宽度统一」)。grid 项 width:auto + 默认
    #    justify-self:stretch 才填格 —— 显式声明缺失即回归。
    rowline = [l for l in text.splitlines() if ".dt04-list.group-row{position:relative" in l.replace(" ", "")]
    assert rowline, f"drawer_tpl/{name}: 缺 .dt04-list .group-row 卡片规则(形态漂移, 同步本守阵)"
    assert "width:auto" in rowline[0].replace(" ", ""), \
        (f"drawer_tpl/{name}: .group-row 必须显式 width:auto(引擎行容器继承三皮肤经典表 "
         "width:fit-content, grid 下不参与 stretch ⇒ 卡片收缩到内容宽, 两列卡片间出现长空隙; 2026-10-12 报障复发)")


def test_drawer_tpl_variant_field_icons():
    """详情面板变体字段行图标消费守阵(Q2, 报告 26-10-07-0542) —— general 三变体(01/02/03)
    字段行必须消费 drawerGeneralSections() 自带的行级 icon 数据(sprite `<use href>` 静态引用,
    字符串拼 HTML 不走 Vue 绑定)且含经典链 icoTone 同表派生 + .ico-t-* 着色 CSS(经典选择器
    .f-row .ico-t-* 在变体行不命中, 变体必须自带重定作用域的色表); 全部变体的 #i-* 引用都不得
    超出三皮肤 index.html sprite 的既有 symbol 集合(三皮肤集合还必须两两相等, 防单边加图标),
    且不得引入外部图标库(<img / iconfont / fontawesome / material-icons)。
    (2026-10-14: traffic 三变体(13/14/15)已随流量页签变体移除, 其 KPI 行图标断言同步退役。)"""
    shared = os.path.join(STATIC_ROOT, "shared")
    vdir = os.path.join(shared, "drawer_tpl")

    # 1. sprite 单点: 三皮肤 index.html 的 symbol id 集合两两相等(变体引用的前提交底)
    sprite_ids = None
    for ui in _UI_ALL:
        html = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        ids = set(re.findall(r'id="(i-[a-z0-9-]+)"', html))
        assert ids, f"{ui}: index.html 未找到 sprite symbol(图标引用的解析基点缺失)"
        if sprite_ids is None:
            sprite_ids = ids
        else:
            assert ids == sprite_ids, f"{ui}: sprite symbol 集合与其它皮肤不一致(单边加图标)"

    # 2. general 三变体: 消费 r.icon + icoTone 同表 + 自带 .ico-t-* 着色 CSS
    for name in ("01-general-hero-tall.js", "02-general-cards-low.js", "03-general-dossier-collapsed.js"):
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert 'href="${r.icon}"' in text or 'href="${icon}"' in text, \
            f"drawer_tpl/{name}: 字段行未消费行级 icon 数据(Q2: 变体丢弃 drawerGeneralSections 图标字段复发)"
        assert '"#i-download": "ico-t-io"' in text, \
            f"drawer_tpl/{name}: 缺 icoTone 同表派生(着色机制与经典链漂移)"
        for tone in (
            "ico-t-io", "ico-t-cap", "ico-t-time", "ico-t-site", "ico-t-sw", "ico-t-id", "ico-t-path", "ico-t-state"
        ):
            assert f".{tone} {{" in text, \
                f"drawer_tpl/{name}: 缺 .{tone} 着色 CSS(经典 .f-row .ico-t-* 作用域在变体行不命中, 必须自带色表)"

    # 3. 引用不越界 + 不引入外部图标库(全变体扫描, 含未来新增文件)
    #    (2026-10-14: 原第 3 节 traffic 三变体(13/14/15)的 KPI 行图标断言随流量变体移除而退役。)
    for name in sorted(os.listdir(vdir)):
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        unknown = {r for r in re.findall(r"#(i-[a-z0-9-]+)", text) if r not in sprite_ids}
        assert not unknown, f"drawer_tpl/{name}: 引用了 sprite 不存在的图标 {sorted(unknown)}(不得凭空造 id)"
        low = text.lower()
        for bad in ("<img", "iconfont", "fontawesome", "material-icons"):
            assert bad not in low, \
                f"drawer_tpl/{name}: 引入外部图标形态 {bad}(图标只许用站内 SVG sprite)"

    # 4. shared/tpl/*.html 同规则(2026-10-30, 26-10-29-1355): 这些模板与变体同文档载入三皮肤
    #    shell(sprite 恒在, settings.html 分区卡 <use :href> 已是旁证), 引用到 sprite 缺的
    #    symbol = 图标静默空白 —— 含未来新增模板文件。动态拼接('#' + 变量)不落字面量, 天然不查。
    tdir = os.path.join(shared, "tpl")
    for name in sorted(os.listdir(tdir)):
        if not name.endswith(".html"):
            continue
        text = open(os.path.join(tdir, name), encoding="utf-8").read()
        unknown = {r for r in re.findall(r"#(i-[a-z0-9-]+)", text) if r not in sprite_ids}
        assert not unknown, f"tpl/{name}: 引用了 sprite 不存在的图标 {sorted(unknown)}(不得凭空造 id)"


def test_drawer_tpl_table_variants_scrollleft_restore():
    """表格型变体横向滚动位自保守阵(P2-2, 报告 26-10-07-0542; 骨架收口 26-10-07-0845) ——
    dt06/07/08/09 四个定宽 grid 表格变体最小宽约 990-1000px, 窄窗口(含 <=900px 固定全屏态)下
    drawer-body overflow:auto 必然横向滚动; 整帧重建(sig 变)只还 scrollTop 会把用户的横向滚动位
    打回最左。骨架收口后单点在核心 H.withScroll(纵横两轴成对读写, 恢复次序 scrollLeft 先
    scrollTop 后), 守阵钉住: 核心实现两轴成对且恢复次序正确 + 四变体整帧重建都包在 withScroll
    回调内 + 变体内分散自保(scroller 直读写/host.parentElement)不得回潮。"""
    core = open(os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"), encoding="utf-8").read()
    for axis in ("scrollTop", "scrollLeft"):
        assert f"sc ? sc.{axis} : 0" in core, \
            f"核心 withScroll 缺 {axis} 读取(纵横成对自保)"
    restore_l = "sc.scrollLeft = left;"
    restore_t = "sc.scrollTop = top;"
    assert restore_l in core and restore_t in core, \
        "核心 withScroll 缺滚动位恢复(纵横成对自保纪律)"
    assert core.index(restore_l) < core.index(restore_t), \
        "核心 withScroll 恢复次序漂移(应 scrollLeft 先 scrollTop 后)"
    vdir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    for name in (
        "06-trackers-table-collapsed.js", "07-peers-dashboard-tall.js", "08-peers-groups-low.js",
        "09-peers-density-collapsed.js"
    ):
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "H.withScroll(host, () => {" in text, \
            f"drawer_tpl/{name}: 整帧重建未走核心 withScroll(滚动自保单点回潮/漂移)"
        rebuild = "host.replaceChildren(document.createRange().createContextualFragment(html));"
        assert text.count(rebuild) == 1, \
            f"drawer_tpl/{name}: 整帧重建调用点形态漂移(守阵按单点定位, 同步本守阵)"
        assert text.index("H.withScroll(host") < text.index(rebuild), \
            f"drawer_tpl/{name}: 整帧重建必须落在 withScroll 回调内(滚动位自保失效)"
        assert "host.parentElement" not in text and "scroller" not in text, \
            f"drawer_tpl/{name}: 变体内再现分散滚动自保(收口后单点在核心 withScroll, 报告 26-10-07-0845)"


def test_drawer_tpl_trackers_per_tracker_reannounce():
    """06 变体逐行汇报倒计时真 per-tracker 口径守阵(P-02 升级, issue 26-10-07-0149, 2026-10-09) ——

    逐行倒计时从「种子级 detail.reannounce_in 全局近似」升级为「行级 next_announce(qB 5.2+ 随
    /trackers 透传, Unix epoch 秒)减 now」。钉住: ①真口径分支读行级 t.next_announce 且先减
    nowSec(epoch 是绝对时间不是倒计时, 直接当剩余秒数是已记录的事故根因); ②「全局」标(dt06-gb)
    只许出现在回退分支 —— 真口径行不得带它; ③回退分支仍在(qB < 5.2 无该字段, 保留旧全局近似);
    ④sig 只含结构态(加载/失败/空态), nowSec 与数据**不进** sig(U4 26-10-12-2253 复发根治:
    旧口径 nowSec 进 sig ⇒ 5s 轮询每拍必整帧重建 ⇒ anchFill 换锚位时锚被移动(换父节点)
    ⇒ Teleport 表格整树重排, 80 对端实测 56-75ms longtask/拍 = 用户所报「表格闪烁, 数据
    随闪烁刷新」); 倒计时新鲜度改走桥响应式 —— nowSec 在 rowsFn 内现读, 每拍随
    drawer.trackers 新数组引用重算, 粒度恒 5s 与旧设计一致(nowSec 进 sig 从来不产生更细
    粒度: _dtNotify 只随数据落袋触发), 壳上工具条注走 paintHtml 原地回填; ⑤真口径分支
    不画微条(per-tracker interval 不可得, 分母不存在, 不造假); ⑥调用点 nextOf 必须拿到行
    t 与 nowSec。
    U3(26-10-12-0527)改版: 判据(nextOf/rowOf/rowsFn)与 sig 口径仍在变体文件, 「全局」标与
    微条的呈现随表格体重写迁渲染器分片(xtpl-cells-dt.html tpl-aq-dt06-cells) —— 呈现锚同轮
    迁移, 判据锚不放宽。"""
    vdir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    text = open(os.path.join(vdir, "06-trackers-table-collapsed.js"), encoding="utf-8").read()
    # ① 真口径: 读行级 next_announce + 先减 now
    assert "t.next_announce" in text, "06 逐行倒计时未读行级 next_announce(P-02 真口径回退)"
    assert "Math.round(na - nowSec)" in text, "06 未以 epoch 减 nowSec 得剩余(epoch 当倒计时 = 事故根因)"
    # 真口径分支 = nextOf 里回退行(const d = ...)之前的那段
    real_branch = text[text.index("function nextOf"):text.index("const d = (ctx.drawer")]
    # ②「全局」标只在回退分支(呈现已迁分片: 判据侧 nextOf 真口径分支不出「全局」字样;
    #   .dt06-gb 的着色 CSS 留在变体注入层, 不在此限)
    assert "全局" not in real_branch, "06 真口径行仍算「全局」标(真值不该标全局)"
    # ③ 回退分支仍在(呈现侧在分片, 全局分支带 dt06-gb 且只此一处)
    frag = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl-cells-dt.html"), encoding="utf-8").read()
    sec06 = frag.split('id="tpl-aq-dt06-cells"', 1)[-1].split("</script>", 1)[0]
    assert "dt06-gb" in sec06, "06 回退分支(全局近似)被删(qB < 5.2 无 next_announce 会整列空白)"
    real_frag = sec06[sec06.index("kind === 'real'"):sec06.index('v-else class="dt06-next"')]
    assert "dt06-gb" not in real_frag, "06 真口径行仍带「全局」标(真值不该标全局)"
    assert "detail.reannounce_in" in text, "06 回退分支未用种子级 detail.reannounce_in"
    # ④ sig 结构态(U4 26-10-12-2253): nowSec/数据不进 sig; 倒计时走 rowsFn 每拍现读 + 壳上回填
    sig_lines = [l for l in text.splitlines() if l.strip().startswith("const sig =")]
    assert len(sig_lines) == 1, "06 const sig 定位漂移(守阵按单行定位, 同步本守阵)"
    for bad in ("nowSec", "Date.now", "reannounce", "next_announce"):
        assert bad not in sig_lines[0], \
            f"06 sig 含 {bad}(每拍整帧重建移动锚 = 表格重排 56-75ms longtask/拍, 复发根因)"
    assert "const nowSec = Math.floor(Date.now() / 1000);" in text, \
        "06 未在 rowsFn 内现读 nowSec(倒计时失去新鲜基准)"
    assert text.index("const nowSec =") > text.index("function rowsFn"), \
        "06 nowSec 不在 rowsFn 内(每拍重算路径断)"
    assert 'H.paintHtml(host, ".dt06-toolbar", toolbarHtml(ctx, ts, d))' in text, \
        "06 跳过重建分支未原地回填工具条(数据拍工具条注陈旧)"
    # ⑤ 真口径分支不画微条(变体判据侧不出 bar; 分片微条只随 global 分支)
    assert "bar" not in real_branch, "06 真口径行仍算微条(per-tracker interval 不可得, 属造假)"
    assert "dt06-tbar" in sec06 and "dt06-tbar" not in real_frag, \
        "06 微条呈现漂移(只许在回退分支)"
    # ⑥ 调用点传参
    assert "nextOf(ctx, t, nowSec)" in text, "06 nextOf 调用点未传行 t / nowSec(真口径拿不到数据)"


def test_drawer_tpl_data_beat_no_anchor_move():
    """抽屉轮询变体数据拍不整帧重建守阵(U4, 26-10-12-2253, 第八次复发根治) ——

    用户报障「种子详情页所有表格闪烁, 数据不实时刷新而是随闪烁刷新」的病根链: 变体 sig 含
    整包数据(旧 06 还含 nowSec 倒计时基准) ⇒ 5s 轮询每拍 sig 必变 ⇒ 每拍整帧重建 ⇒
    anchFill 把保活锚换回 slot 位时锚被移动(换父节点) ⇒ Teleport 进锚的表格整树重排
    —— 80 对端实测每拍 56-75ms longtask + 52-93ms 慢帧(经典表同数据量 0ms), 视觉即
    「每 5s 全表卡顿闪烁」; 数据更新与整帧重建同拍发生, 即「随闪烁刷新」。

    修复口径: sig 收窄为结构态(加载/失败/空态/在场分组集/折叠态), 数据拍 skipUnchanged
    命中后只对**不含锚**的壳上子树原地回填, 行走桥响应式(rowsFn 每拍随 drawer.trackers
    新数组引用重算)。守阵钉住六个轮询变体(04/05/06/07/08/09): ①sig 块不含数据口径标识
    (nowSec/Date.now/reannounce/next_announce/JSON.stringify 整包序列化); ②原地回填先于
    首个整帧重建调用点(file order —— 回填必须在"跳过"路径上); ③skip 路径含原地回填
    (H.paintHtml 或受比对的 textContent/innerHTML 直写); ④核心 paintHtml 判空 + 同值
    跳过(空选择器不炸, 同值不写)。"""
    vdir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    core = open(os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"), encoding="utf-8").read()
    # ④ 核心回填 helper: 判空 + 同值跳过
    assert "paintHtml: function (host, sel, html)" in core, \
        "核心缺 paintHtml helper(数据拍原地回填单点漂移)"
    assert "if (el && el.innerHTML !== html) el.innerHTML = html;" in core, \
        "核心 paintHtml 缺判空/同值跳过(空选择器会炸, 同值重写引入无谓抖动)"
    for name in (
        "04-trackers-status-cards-tall.js", "05-trackers-health-groups-low.js", "06-trackers-table-collapsed.js",
        "07-peers-dashboard-tall.js", "08-peers-groups-low.js", "09-peers-density-collapsed.js"
    ):
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "H.skipUnchanged(host, ui, sig)" in text, \
            f"drawer_tpl/{name}: 缺 skipUnchanged 跳过重建路径"
        # ① sig 块 = const sig 起至首个分号结尾行(含续行)
        lines = text.splitlines()
        start = next(i for i, l in enumerate(lines) if l.strip().startswith("const sig ="))
        sig_block = []
        for l in lines[start:]:
            sig_block.append(l)
            if l.rstrip().endswith(";"):
                break
        sig_text = "\n".join(sig_block)
        for bad in ("nowSec", "Date.now", "reannounce", "next_announce", "JSON.stringify"):
            assert bad not in sig_text, \
                f"drawer_tpl/{name}: sig 含数据口径 {bad}(每拍整帧重建移动锚 = 表格重排, 复发根因)"
        # ③ skip 路径含原地回填(paintHtml 或受比对直写)
        fill_at = min(
            [text.index(m) for m in ("H.paintHtml(", ".textContent !== ", ".innerHTML !== ") if m in text] or [-1]
        )
        assert fill_at >= 0, f"drawer_tpl/{name}: 无原地回填手段(数据拍只能整帧重建)"
        # ② 回填先于首个整帧重建调用点(在"跳过"路径上)
        assert text.index("H.skipUnchanged") < fill_at < text.index("host.replaceChildren"), \
            f"drawer_tpl/{name}: 原地回填不在 skip 分支与首个整帧重建之间(数据拍仍走重建)"


def test_drawer_tpl_a11y_and_fetch_error_states():
    """详情面板变体可访问性 + fetch 失败态区分守阵(P3-4/P3-5, 报告 26-10-07-0542) ——
    核心层 drawer-close 钮 aria-label(种子/流量两头部成对, 仅 svg 无文字读屏不可达);
    纯 div/span 模拟控件 role="button" tabindex="0": 01/02/03/05/08 折叠组头(含 aria-expanded)
    + 05/06 msg 展开行; keydown 委托与 click 委托成对挂宿主(wire 挂 / destroy 摘)且 Enter/Space
    转发前排除原生 button/summary 等自身发 click 的元素(防双重触发)。
    U2(计划 26-10-12-0527)改版: 07/08/09 手搓排序表头退役(D3 排序并引擎 aq-table, 变体文件
    零手搓表头由 test_drawer_table_bridge_wiring ⑪ 钉), 其 aria-sort pin 随载体退役; 07/09
    交互面只剩原生 <button> 筛选 chips(键盘天然可达), 08 折叠组头仍走 P3-4 模拟控件件套。
    三个列表 fetcher 失败标记(trackersError/filesError/peersError)成功落袋即清、换目标作废;
    九个 fetch 型变体(04/05/06/07/08/09/10/11/12)空列表先判错误态再判空态, trackers/peers
    文案带自动刷新重试口径(5s 轮询真实存在)、content 文案不承诺自动重试(content 页签无轮询)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    vdir = os.path.join(shared, "drawer_tpl")

    # 1. 核心层关闭钮 aria-label(种子/流量两头部成对各一处; 原生 button 键盘本可达, 缺的只是可访问名)
    # W3(计划 26-10-11-2106): 关闭钮收进 <aq-drawer-head> 外壳(组件模板恰一枚, 两形态同源);
    # drawer.html 零复写(复写即「两份实现」回潮)
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()
    assert head_tpl.count('<button class="drawer-close" aria-label="关闭详情面板"') == 1, \
        "drawer-head.html: drawer-close 钮缺 aria-label 或不在外壳组件内(W3 单点)"
    assert 'drawer-close' not in drawer_tpl, "drawer.html 复写 drawer-close 钮(W3 起归 <aq-drawer-head>)"

    # 1.5 挂摘纪律单点(骨架收口 26-10-07-0845): 核心 wireEvents/unwireEvents 挂摘必须成对
    # (同一张 host.__dtEvents 记账表), 变体不再各自维护 __dtNNWired 标志
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    assert "for (var k in map) host.addEventListener(k, map[k]);" in core \
        and "for (var k in host.__dtEvents) host.removeEventListener(k, host.__dtEvents[k]);" in core, \
        "核心 wireEvents/unwireEvents 挂摘不成对(换变体监听叠加回潮)"

    # 2. 纯 div/span 模拟控件 role/tabindex/aria(只盘模拟控件; 原生 button 有 title 充当可访问名不动)
    # U2(计划 26-10-12-0527, D3): 07/08/09 手搓排序表头退役 —— 排序交互/表头/箭头全归引擎 aq-table
    # (xtpl.html tpl-aq-table: col.sortable 走激活单点 headActivate → $root.setSort), 变体文件零手搓
    # 排序表头由 test_drawer_table_bridge_wiring ⑪ 钉死。引擎 .h-cell 是 click 表头, 与主视图各表同款
    # 同形态; 引擎级表头 a11y 件套(role=columnheader / aria-sort / tabindex / keydown)已于 2026-10-12
    # 补课 —— 计划 26-10-12-2330 方案 C(issue 26-10-12-0800), 落表壳组件单点, 守阵
    # test_frontend_table_head_a11y(本段只盘变体侧模拟控件, 引擎侧归那条)。
    fold_variants = (
        "01-general-hero-tall.js", "02-general-cards-low.js", "03-general-dossier-collapsed.js",
        "05-trackers-health-groups-low.js", "08-peers-groups-low.js"
    )
    msg_variants = ("05-trackers-health-groups-low.js", "06-trackers-table-collapsed.js")
    all_a11y = sorted(set(fold_variants + msg_variants))
    for name in all_a11y:
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        if name in fold_variants:
            assert re.search(r'data-fold[^>]*role="button"|role="button"[^>]*data-fold', text.replace("\n", " ")), \
                f"drawer_tpl/{name}: 折叠组头缺 role=button(P3-4: 纯 div+click 键盘不可达)"
            assert 'aria-expanded="' in text, \
                f"drawer_tpl/{name}: 折叠组头缺 aria-expanded(读屏不知道折叠态)"
        # U3(26-10-12-0527): 05/06 的 msg 展开行随表格体重写迁渲染器分片(件套在下方 2.1 钉),
        # 变体侧只保留键盘转发/挂摘纪律 —— data-msg 行在引擎行容器内, 委托经宿主照常命中。
        # 06 外壳已无任何纯 div 模拟控件(其 tabindex 随 msg 迁分片), 05 的折叠组头仍在
        if name != "06-trackers-table-collapsed.js":
            assert 'tabindex="0"' in text, f"drawer_tpl/{name}: 模拟控件缺 tabindex=0(键盘不可聚焦)"
        # keydown 委托与 click 委托成对挂宿主(纯 div 模拟无原生 click, Enter/Space 手动转发):
        # 挂摘纪律收口在核心 wireEvents/unwireEvents 单点(26-10-07-0845), 变体只声明事件表
        assert "click: onClick" in text and "keydown: onKeyDown" in text, \
            f"drawer_tpl/{name}: keydown 委托与 click 委托未成对挂宿主(模拟控件键盘不触发)"
        assert "H.wireEvents(host" in text and "H.unwireEvents(host)" in text, \
            f"drawer_tpl/{name}: 挂摘未走核心成对 helper(监听叠加回潮)"
        # 双重触发去重: 焦点在原生交互元素上时不转发(原生 Enter 本来就发 click)
        assert 'closest("button, input, select, textarea, a[href], summary")' in text, \
            f"drawer_tpl/{name}: keydown 转发未排除原生交互元素(Enter 会 click+keydown 双重触发)"

    # 2.1 U3(26-10-12-0527): 05/06 msg 展开行的 P3-4 件套随载体迁 xtpl-cells-dt.html 分片
    # (role=button + tabindex + aria-expanded + data-msg 逐段钉; 键盘 Enter/Space 转发仍在变体)
    cells_dt = open(os.path.join(shared, "tpl", "xtpl-cells-dt.html"), encoding="utf-8").read()
    for sec in ("tpl-aq-dt05-cells", "tpl-aq-dt06-cells"):
        sec_txt = cells_dt.split(f'id="{sec}"', 1)[-1].split("</script>", 1)[0].replace("\n", " ")
        assert re.search(r'data-msg[^>]*role="button"|role="button"[^>]*data-msg', sec_txt), \
            f"xtpl-cells-dt/{sec}: msg 展开行缺 role=button(P3-4: 纯 span+click 键盘不可达)"
        assert 'tabindex="0"' in sec_txt and "aria-expanded=" in sec_txt, \
            f"xtpl-cells-dt/{sec}: msg 展开行缺 tabindex/aria-expanded(键盘不可聚焦/读屏不知展开态)"

    # 2.5 peers 三变体(U2 重写后)的 a11y/挂摘口径: 07/09 交互面只剩原生 <button> 筛选 chips
    # (键盘天然可达, 无模拟控件故无 role/tabindex/keydown 转发件套); 08 归上面 fold 组
    # (折叠组头仍是纯 div 模拟控件)。排序/表头 a11y 归引擎(见本段头注)。
    for name in ("07-peers-dashboard-tall.js", "08-peers-groups-low.js", "09-peers-density-collapsed.js"):
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "H.wireEvents(host" in text and "H.unwireEvents(host)" in text, \
            f"drawer_tpl/{name}: 挂摘未走核心成对 helper(监听叠加回潮)"
        if name != "08-peers-groups-low.js":
            assert 'type="button"' in text, \
                f"drawer_tpl/{name}: 筛选 chips 必须是原生 <button>(键盘可达; 换纯 div 模拟须补 P3-4 件套)"

    # 3. 失败标记: 显式建字段(vue-reactivity 口径) + catch 落标记 + 成功清 + 换目标作废
    #    W1 起四 fetcher/软切换作废落 drawer_store.js(数据层), 初值显式建字段仍住 drawer.js;
    #    R21-A-01(2026-10-21) 起落/清在唯一骨架里按 cfg.errKey 做, 字段名只在差异表声明。
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()
    skel, ftable = _drawer_fetch_parts(store_js)
    for fld in ("trackersError", "filesError", "peersError"):
        assert f'{fld}: ""' in drawer_js, \
            f"drawer.js: drawer 初值缺 {fld} 显式建字段(vue-reactivity 坑: 后补属性不进响应式)"
        assert f'errKey: "{fld}"' in ftable, \
            f"drawer_store.js: 差异表未把 {fld} 认作失败标记(P3-5: 变体拿不到区分信号)"
    assert "this.drawer[cfg.errKey] = e.message || cfg.failText;" in skel, \
        "drawer_store.js: 骨架 catch 未落失败标记(P3-5: 变体拿不到区分信号)"
    assert 'this.drawer[cfg.errKey] = "";' in skel, \
        "drawer_store.js: 骨架成功落袋后未清失败标记(上一次失败永久钉住错误态)"
    assert 'this.drawer.trackersError = this.drawer.filesError = this.drawer.peersError = "";' in store_js, \
        "drawer_store.js: 换目标(软切换)未作废三个失败标记(旧目标错误态串显到新目标)"

    # 4. 九个 fetch 型变体: 错误态先于空态; 文案与轮询事实对应(trackers/peers 5s 轮询=可写自动重试;
    #    content 无轮询=只陈述失败, 不得虚构「稍后自动重试」)
    err_expect = {
        "04-trackers-status-cards-tall.js": ("trackersError", "Tracker 列表加载失败, 将在下次自动刷新时重试", "暂无 tracker"),
        "05-trackers-health-groups-low.js": ("trackersError", "Tracker 列表加载失败, 将在下次自动刷新时重试", "暂无 tracker"),
        "06-trackers-table-collapsed.js": ("trackersError", "Tracker 列表加载失败", "暂无 tracker"),
        "07-peers-dashboard-tall.js": ("peersError", "用户列表加载失败, 将在下次自动刷新时重试", "暂无已连接用户"),
        "08-peers-groups-low.js": ("peersError", "用户列表加载失败, 将在下次自动刷新时重试", "暂无已连接用户"),
        "09-peers-density-collapsed.js": ("peersError", "用户列表加载失败", "暂无已连接用户"),
        "10-content-tree-detail-tall.js": ("filesError", "文件列表加载失败, 数据不可用", "无文件列表"),
        "11-content-treegrid-batch-low.js": ("filesError", "文件列表加载失败, 数据不可用", "无文件列表"),
        "12-content-space-treemap-collapsed.js": ("filesError", "文件列表加载失败, 数据不可用", "无文件列表"),
    }
    for name, (fld, err_text, empty_text) in err_expect.items():
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert f"ctx.drawer.{fld}" in text, \
            f"drawer_tpl/{name}: 变体未读 {fld}(P3-5: 失败与空列表同形态回潮)"
        assert err_text in text, \
            f"drawer_tpl/{name}: 缺错误态文案「{err_text}」(P3-5: 失败态分支被摘)"
        assert text.index(err_text) < text.index(empty_text), \
            f"drawer_tpl/{name}: 错误态分支必须先于空态分支(空态先行 = 失败仍显示「{empty_text}」)"
        if name[:2] in ("10", "11", "12"):
            # content 组无轮询: 失败文案只陈述失败, 不得虚构「稍后自动重试」承诺(P3-5 口径)
            assert "自动重试" not in text and "自动刷新" not in text, \
                f"drawer_tpl/{name}: content 组无轮询, 失败文案不得虚构自动重试承诺(P3-5 口径)"
        else:
            # trackers/peers 组主节拍轮询真实存在(_startDrawerPoll): 可写「下次自动刷新时重试」
            assert "下次自动刷新时重试" in text, \
                f"drawer_tpl/{name}: trackers/peers 组失败文案应带自动刷新重试口径(轮询真实)"


def test_drawer_tpl_content_row_keyboard_roving():
    """content 组行级键盘 roving tabindex 守阵(issue 26-10-07-0846) ——
    dt10/11 可点击行 [data-node] 与 dt12 树图块 [data-blk]/体积榜行 [data-row] 原为纯 div+click,
    键盘/读屏不可达(修复轮 P3-4 缩围转来的已记未做项)。按 issue 建议候选① roving tabindex 落地:
    核心 helpers 四件套单点(roving 锚点/rowFocusKey 记账/rowRestore 回焦/rowMove 移焦);
    行容器 tabindex=-1 不进 Tab 序(行内原生控件自然参与 Tab; 整行不加 role=button —— 行内已含
    原生控件, 嵌套交互语义反而更糟, 入池报告根因段口径); :focus-visible 焦点可见; keydown 委托
    成对挂宿主且只有 ev.target 是行容器自身才接管; 重建前记账/重建后回焦成对(原子换帧打断焦点
    链); dt12 树图块焦点互联复用悬停 onOver/onOut(focusin/focusout 与 mouseover/out 同语义)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    vdir = os.path.join(shared, "drawer_tpl")

    # 1. 核心 helpers 四件套单点(变体各自复刻会漂移, 口径同 26-10-07-0845 骨架收口)
    for fn in ("roving: function", "rowFocusKey: function", "rowRestore: function", "rowMove: function"):
        assert fn in core, f"核心 helpers 缺 {fn.split(':')[0]}(行级键盘单点被拆散/摘除)"

    # 2. 三变体接入面: 行/块容器 tabindex=-1 + 锚点/回焦/移焦走核心单点 + keydown 委托挂宿主
    #    (U4 改锚: dt10/11 表格体接引擎(计划 26-10-12-0527) —— 行容器 tabindex=-1 与
    #    data-dt-key 身份锚由桥模板单点输出(描述符 rowTab/rowKey 声明位), roving 锚点/回焦
    #    经描述符 rowAfter → 变体 rowAfterFn 在锚换代重挂后跑(与原 replaceChildren 后
    #    roving 同语义); 12 树图块仍是自管 DOM, 断言不变。)
    bridge = open(os.path.join(shared, "tpl", "xtpl.html"), encoding="utf-8").read()
    assert ':tabindex="$root.dtBridgeRowTab(tab) ? -1 : null"' in bridge, \
        "桥行容器缺 tabindex=-1 输出(rowTab 声明位, 行容器混进 Tab 序)"
    assert ':data-dt-key="r[$root.dtBridgeRowKey(tab)]"' in bridge, \
        "桥行容器缺 data-dt-key 身份锚(变体键盘委托/roving 的行锚没了)"
    appjs = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    assert "rowTab: true, rowAfter: true" in appjs, \
        "app.js: drawerContentV10/V11 描述符缺 rowTab/rowAfter 声明位(U4 行级键盘面)"
    cases = {
        "10-content-tree-detail-tall.js": ["H.roving(el, \"data-dt-key\"", "ev.target !== row"],
        "11-content-treegrid-batch-low.js": ["H.roving(el, \"data-dt-key\"", "ev.target !== row"],
        "12-content-space-treemap-collapsed.js":
            ["H.roving(mapEl, \"data-blk\"", "H.roving(host, \"data-row\"", "ev.target !== el"],
    }
    for name, hooks in cases.items():
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        if name[:2] in ("10", "11"):
            assert "rowAfterFn" in text, \
                f"drawer_tpl/{name}: 缺 rowAfterFn 接入点(锚换代重挂后的 roving/回焦被摘)"
        else:
            assert 'tabindex="-1"' in text, \
                f"drawer_tpl/{name}: 行/块容器缺 tabindex=-1(roving 基线, 容器混进 Tab 序)"
        assert 'role="button"' not in text, \
            f"drawer_tpl/{name}: 整行加了 role=button(行内已含原生控件, 嵌套交互语义更糟 —— 入池根因段口径)"
        for hook in hooks:
            assert hook in text, f"drawer_tpl/{name}: 缺接入点 {hook}(锚点/接管守卫被摘)"
        # W5(计划 26-10-13-0811 L5): 交互态反应式化后 anchTouch 换代已退役(10/11 的
        # rowFocusKey 记账随 touch() 退役 —— 交互不再重挂, 焦点不再被打断); rowRestore
        # 仍在 rowAfterFn, 服务真换代(数据帧)后的回焦。
        assert "H.rowRestore(" in text, \
            f"drawer_tpl/{name}: 缺回焦接入点(rowAfterFn 的 rowRestore 被摘)"
        assert "H.rowMove(" in text, \
            f"drawer_tpl/{name}: 方向键移焦未走核心 rowMove(键盘用户无法在行间转移焦点)"
        assert "keydown: onKeyDown" in text, \
            f"drawer_tpl/{name}: keydown 委托未挂宿主(Enter/Space/方向键不触发)"
        assert "H.wireEvents(host" in text and "H.unwireEvents(host)" in text, \
            f"drawer_tpl/{name}: 挂摘未走核心成对 helper(监听叠加回潮)"
        assert ":focus-visible" in text, \
            f"drawer_tpl/{name}: 行/块容器缺 :focus-visible 样式(键盘焦点不可见)"

    # 3. dt12 树图块焦点互联: 复用悬停 onOver/onOut(focusin/focusout 冒泡同语义, 对侧加/摘 hl)
    t12 = open(os.path.join(vdir, "12-content-space-treemap-collapsed.js"), encoding="utf-8").read()
    assert "focusin: onOver" in t12 and "focusout: onOut" in t12, \
        "drawer_tpl/12: 树图块焦点互联未复用悬停 onOver/onOut(键盘选中块时体积榜无联动高亮)"


def test_drawer_tpl_variant_no_singleton_shadowing():
    """变体单点 T/R/H 遮蔽禁令守阵(2026-10-09 用户报障「空间树图选了不显示、换种子回落经典」)。

    根因: dt12 layoutMap 写了 `const W = mapEl.clientWidth, H = mapEl.clientHeight`, 局部 H 把
    文件头 helpers 单点(`const H = reg.helpers`)遮蔽成数字, 同函数尾 `H.rowFocusKey(...)` 对数字
    取属性抛 TypeError —— 树图块只在 layoutMap 里绘制, 抛错 = 树图区永远空白; 经 _dtRender catch
    走「渲染抛错回落 classic」分支后选择被复位并落盘, 用户选择跨会话静默丢失。
    守阵不变式: 变体文件凡声明了 T/R/H 单点(const <N> = reg.dtHtml|dtRaw|helpers), 该名在全文件
    (单点声明行之外)禁止再被任何声明语句绑定 —— 含多声明符列表(let a = 1, H = 2, 本案根因形态)
    与解构(const { H } = ...); 未声明单点的名不查(15 号变体无 H 单点, 其局部 H = 22 是合法常量)。
    """
    vdir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    if not os.path.isdir(vdir):
        return
    for name in sorted(os.listdir(vdir)):
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        # 先摘掉单点声明行(整行, 含行内尾注), 只对文件里真实声明了单点的名做禁令
        singletons = set()
        kept = []
        for line in text.splitlines():
            m = re.match(r"^\s*const\s+([TRH])\s*=\s*reg\.(?:dtHtml|dtRaw|helpers)\b", line)
            if m:
                singletons.add(m.group(1))
                continue  # 整行摘除: 单点声明自身形如 "const H =", 不摘会自证违例
            kept.append(line)
        if not singletons:
            continue
        body = "\n".join(kept)
        for n in sorted(singletons):
            # 形态一: 声明语句(至分号/行尾)内出现 "<n> =" —— 覆盖 const H = x 与
            # let a = 1, H = 2(本案根因形态); [^;\n]* 把搜索域限制在单条声明语句内
            m = re.search(r"\b(?:const|let|var)\b[^;\n]*\b%s\s*=" % n, body)
            assert not m, (
                f"drawer_tpl/{name}: 单点 {n} 被局部声明遮蔽({m.group(0).strip()!r}) —— "
                f"遮蔽后 {n}.xxx / T` / R() 对非对象取属性抛 TypeError, 变体渲染回落 classic; "
                f"局部名一律改名(如 mapH/RH)"
            )
            # 形态二: 解构声明绑定名(const { H } = ... / const { a, H: y } = ...);
            # const { num } = H 是"读单点"不是"绑同名", 不得误伤
            m = re.search(r"\b(?:const|let|var)\s*\{[^};\n]*\b%s\b\s*[}:,]" % n, body)
            assert not m, f"drawer_tpl/{name}: 单点 {n} 被解构声明遮蔽(const {{ {n} }} = ...)"


def test_drawer_tpl_cross_seed_fold():
    """详情面板折叠态跨种子口径统一守阵(P3-6, 报告 26-10-07-0542) —— content 组 dt10/11/12
    换种子重置块(hash !== ui.lastHash)只许清选中/勾选/筛选, 不得清折叠记账(ui.folded/ui.colG;
    用户拍板统一为跨种子保持, 以 general 组 dt01/02 口径为准; 记账 key 是 path 不含 hash, 新种子
    path 空间不同则旧条目自然不命中, 同名目录延续上一部折叠选择; dt11 勾选集必须继续重置 ——
    批量优先级真提交, 旧勾选落到新种子文件上是误操作面); 折叠态与种子无关或无折叠的变体
    (01-09/13-15, 组头 key 是节名/组键/tracker url)不得引入 lastHash 重置机制; 2026-10-10
    模板选择迁右键后, 头部 .dt-select 下拉与整套定宽规则一并从核心退役(旧 P3-7 宽度守阵作废,
    核心不得再注入 .dt-select)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    vdir = os.path.join(shared, "drawer_tpl")

    # 1. P3-6: dt10/11/12 的换种子重置块不再清折叠记账, 且按 path 记账的容器仍在
    #    (U4 改锚: dt10/11 表格体接引擎 —— 折叠钮迁渲染器分片(data-act="fold" +
    #    :data-path), 变体侧按 path 落账的判据 = onClick 委托读 data-path; 12 不变。)
    fold_accounts = {
        "10-content-tree-detail-tall.js": ("folded", 'data-path'),
        "11-content-treegrid-batch-low.js": ("folded", 'data-path'),
        "12-content-space-treemap-collapsed.js": ("colG", 'data-gh="${dir.path}"'),
    }
    for name, (fold_key, path_attr) in fold_accounts.items():
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        m = re.search(r"if \(hash !== ui\.lastHash\) \{(.*?)\n    \}", text, re.S)
        assert m, f"drawer_tpl/{name}: 换种子重置块形态漂移(守阵正则失配, 同步本守阵)"
        block = m.group(1)
        assert "ui.lastHash = hash" in block, \
            f"drawer_tpl/{name}: lastHash 更新丢失(选中/筛选的重置锚点没了)"
        assert fold_key not in block, \
            f"drawer_tpl/{name}: 换种子重置块清了折叠记账 {fold_key}(P3-6: 口径已统一为跨种子保持, 不得回潮)"
        assert f"{fold_key}: new Set()" in text, \
            f"drawer_tpl/{name}: 折叠记账容器 {fold_key} 消失(跨种子保持的载体)"
        assert path_attr in text, \
            f"drawer_tpl/{name}: 折叠交互未按 path 落账({path_attr} 形态漂移, 记账 key 不再是 path)"

    # 2. dt11 勾选集仍随换种子重置(批量优先级真提交, 不许跨种子残留; 折叠是纯视图语义, 不同)
    text11 = open(os.path.join(vdir, "11-content-treegrid-batch-low.js"), encoding="utf-8").read()
    block11 = re.search(r"if \(hash !== ui\.lastHash\) \{(.*?)\n    \}", text11, re.S).group(1)
    assert "ui.checked = new Set()" in block11, \
        "drawer_tpl/11: 换种子重置块丢了勾选集清空(批量优先级会落到新种子文件上)"

    # 3. 其余变体(01-09/13-15)不得出现换种子重置机制 —— 它们没有折叠态或记账 key 与种子
    #    无关(dt01/02/03 节名·卡片id / 05 组键·tracker url / 06 tracker url / 08 组键;
    #    04/07/09 仅筛选, 13/14/15 traffic 无折叠), lastHash 机制进它们即口径漂移
    for name in sorted(os.listdir(vdir)):
        if not name.endswith(".js") or name[:2] in ("10", "11", "12"):
            continue
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "lastHash" not in text, \
            f"drawer_tpl/{name}: 出现 lastHash 换种子重置机制(该变体折叠/展开 key 与种子无关或无折叠, 不应有此机制)"

    # 4. 2026-10-10 模板选择迁右键: 头部 .dt-select 下拉与整套定宽规则一并退役(旧 P3-7/P3-6
    #    宽度守阵随之作废) —— 核心不得再注入任何 .dt-select 规则(「选择器占位宽随页签变」的病根
    #    随原生 select 一并消失, 选择入口改由 openDrawerMenu 右键菜单承担, 见
    #    test_drawer_tpl_menu_right_click_selection)
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    assert '".drawer .dt-select {' not in core, \
        "核心仍残留 .dt-select 规则(2026-10-10 模板选择已迁右键菜单, 下拉定宽规则应一并删除)"


def test_drawer_tpl_menu_right_click_selection():
    """详情面板模板选择迁右键守阵(2026-10-10 用户动议「模板选择改为右键选择, 在对应的区域弹右键;
    合并时左边弹常规的模板选择, 右边弹内容的模板选择」) —— 头部 .dt-select 下拉退役; 右键命中区域
    决定菜单目标页签: 变体宿主 data-dt-host 优先(2026-10-14 起宿主 id 恒等于页签名 ——
    traffic-pre/post 双宿主已随流量变体移除), 合并列 data-dt-tab 兜列头/列空白, 否则当前页签;
    菜单 = 该页签模板候选(注册表 choices: 有经典的页签「经典」在首位, 四内容页签只有变体, 勾选态
    .ctx-tick)+ 分隔线 + 合并开关(仅种子详情形态 dtMenuMergeOn); 候选 < 2 的页签(流量)不弹菜单。
    2026-10-10 用户报「合并后右侧空白右键弹左列模板」: 命不中 host/col 时(列间隙/分栏两侧留白
    不落列元素上)不得直接回落当前页签, 正文区内按指针 x 归列(_drawerMenuColByX)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    menu_js = open(os.path.join(shared, "menu.js"), encoding="utf-8").read()
    ctx_menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. 核心层: 菜单 computed/落点方法齐全, 退役的选择器 API 不得残留
    for member in ("dtMenuTab", "dtMenuTplOptions", "dtMenuTplCurrent", "dtMenuMergeOn"):
        assert re.search(rf"^      {member}\(\)", core, re.M), f"核心缺右键菜单 computed {member}"
    assert re.search(r"^      dtMenuPick\(id\) \{", core, re.M), "核心缺 dtMenuPick 落点方法"
    # 注册表三件: 经典可用性 / 缺省档 / 菜单候选(2026-10-14 经典移除后的档制单点)
    for api in ("hasClassic: function (tab)", "defaultSel: function (tab)", "choices: function (tab)"):
        assert api in core, f"注册表缺 {api}(经典可用性/缺省档/候选集的单点)"
    assert 'var CLASSIC_TABS = ["traffic"]' in core, \
        "CLASSIC_TABS 不再是「只有流量页签有经典」(四内容页签经典 UI 已移除)"
    assert "dtMenuTplOptions() {" in core and "choices(this.dtMenuTab)" in core, \
        "dtMenuTplOptions 未走注册表 choices(菜单候选集单点断了)"
    for retired in ("dtTplOptions", "dtTplCurrent"):
        assert not re.search(rf"^      {retired}\(\)", core, re.M), f"核心仍定义退役的 computed {retired}"
    assert not re.search(r"^      dtPick\(", core, re.M), "核心仍定义退役方法 dtPick"
    assert '".drawer .dt-select {' not in core, "核心仍注入 .dt-select(头部下拉已退役)"

    # 2. menu.js: openDrawerMenu 放行 seed+traffic(流量形态也要能选流量模板), 目标页签解析成对
    assert re.search(r"openDrawerMenu\(event\) \{", menu_js), "menu.js 缺 openDrawerMenu"
    assert "!this.drawerIsSeed && !this.drawerIsTraffic" in menu_js, \
        "openDrawerMenu 未同时放行 seed/traffic 形态(流量形态模板选择无入口; W3 走判据单点)"
    assert "_drawerMenuTab(event)" in menu_js, "openDrawerMenu 未落目标页签(_drawerMenuTab)"
    assert 'closest("[data-dt-host]")' in menu_js and 'closest("[data-dt-tab]")' in menu_js, \
        "_drawerMenuTab 缺区域解析(宿主 data-dt-host / 合并列 data-dt-tab)"
    # 2026-10-14: 流量变体(13/14/15)移除后流量页签只剩经典一档 —— 模板菜单在该页签无内容,
    # openDrawerMenu 必须按候选数 < 2 早退(单选项菜单 = 半残 UI); 原先的 traffic-pre/post
    # 去后缀改写随双宿主移除一并退役。
    assert "AQB_DRAWER_TPL_REG.choices(tab).length < 2" in menu_js, \
        "openDrawerMenu 缺「候选 < 2 不弹菜单」早退(流量页签会弹出只有一个「经典」项的菜单)"
    assert "replace(/-(?:pre|post)$/" not in menu_js, \
        "menu.js 又出现 traffic-pre/post 去后缀改写 —— 流量双宿主已移除(2026-10-14)"

    # 2b. 合并双列兜底(2026-10-10 用户报「合并后右侧空白右键弹左列模板」): 列间隙/分栏两侧留白
    #     不属于任何 .dt-col, 命不中 host/col 时必须在正文区内按指针 x 归列, 不得直接回落当前页签。
    assert "_drawerMenuColByX(event)" in menu_js, \
        "menu.js 缺合并列按 x 归列的兜底(_drawerMenuColByX, 右侧空白右键会回落左列模板)"
    assert 'this.dtSplitOn && el.closest(".drawer-body")' in menu_js, \
        "x 归列兜底未限定在合并双列 + 正文区内(页签栏/头部仍应回落当前页签)"
    assert 'querySelectorAll(".drawer .drawer-split .dt-col[data-dt-tab]")' in menu_js, \
        "_drawerMenuColByX 未按合并列 DOM(.dt-col[data-dt-tab])取列"

    # 3. ctx-menus.html: 菜单渲模板选项 + 勾选态 + 条件合并开关
    assert 'v-for="o in dtMenuTplOptions"' in ctx_menus, "ctx-menus 缺模板选项渲染"
    assert "dtMenuPick(o.id)" in ctx_menus, "ctx-menus 缺模板选择落点 dMenuPick"
    assert "dtMenuTplCurrent === o.id" in ctx_menus, "ctx-menus 缺模板选项勾选态"
    assert "dtMenuMergeOn" in ctx_menus and "dtToggleMerge()" in ctx_menus, \
        "ctx-menus 缺合并开关(条件渲染 dtMenuMergeOn)"


def test_drawer_tpl_default_sel():
    """详情面板模板**缺省档**守阵(原名 test_drawer_tpl_classic_default; 2026-10-14 经典渲染链
    移除后缺省档按页签分化 —— 四内容页签 = 该页签首个变体, 流量页签 = classic)。有 node 时真跑
    核心层 node 电池: 白名单脏值/未注册 id/坏 JSON 一律回落缺省档; 注册 fail-fast 四分支;
    dtHtml 转义与 dtRaw 豁免; options 不含 classic。无 node 静态兜底: app.js initialDrawerTpl
    缺核心时也必须返回**可用**映射(不能返回空对象 —— 宿主显隐门 dtHostOn 读 drawerTplSel.<tab>,
    缺键会把正文藏掉), 且字面量须与 defaultSel 同口径(四内容页签 = 首个变体; 流量 = classic)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    for tab, dflt in (
        ("general", "01"), ("trackers", "04"), ("peers", "07"), ("content", "10"), ("traffic", "classic")
    ):
        assert f'{tab}: "{dflt}"' in app_js, \
            f"initialDrawerTpl 兜底映射缺 {tab} -> {dflt}(核心未载入时正文会被藏掉)"
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _DT_REGISTRY_NODE_PROBE,
         os.path.join(shared, "drawer_templates.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"drawer_templates node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"classic 默认电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


_DT_FALLBACK_NODE_PROBE = r"""
const fs = require("fs");
global.window = {};
/* localStorage 桩(dtPersistSel 落盘走它); document 保持 undefined —— dtInjectCss 有守卫跳过注入 */
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
eval(fs.readFileSync(process.argv[1], "utf8"));
const M = window.AQB_DRAWER_TPL.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

/* 假 ctx: 只带回落路径触碰的面(drawerTplSel + 挂载态 + 持久化方法, 与真根实例的字段面对齐) */
function makeCtx(sel) {
  const ctx = { drawerTplSel: Object.assign({}, sel), _dtMounted: null };
  ctx.dtPersistSel = M.dtPersistSel;
  ctx._dtSel = M._dtSel;   /* 生效档取值口(dtPersistSel 走它: 缺键/脏值回落 defaultSel) */
  return ctx;
}
function makeHost() {
  const host = { children: [], cleared: false, destroyed: false,
    replaceChildren() { host.children.length = 0; host.cleared = true; } };
  return host;
}
const errors = [];
const realErr = console.error;
console.error = (...a) => errors.push(a.map(String).join(" "));

/* 先注册一个正常变体 ok —— 它是 general 的**首个**变体, 即 defaultSel(general)(回落目标) */
window.AQB_DRAWER_TPL_REG.register({ id: "ok", tab: "general", label: "OK", render() {} });
window.AQB_DRAWER_TPL_REG.register({ id: "boom", tab: "general", label: "B",
  render() { throw new Error("boom-render"); },
  destroy(h) { h.destroyed = true; } });

/* 主场景: 变体渲染抛错 -> 该页签复位缺省档 + 落盘 + 摘挂载 + 清宿主 + destroy + 不吞栈 */
const sel = { general: "boom", trackers: "classic", peers: "classic", content: "classic", traffic: "classic" };
const ctx = makeCtx(sel);
const host = makeHost();
const st = { tab: "general", entry: window.AQB_DRAWER_TPL_REG.get("general", "boom"), host: host };
ctx._dtMounted = st;
M._dtRender.call(ctx, st);

ok("渲染抛错后该页签复位缺省档(该页签首个变体 ok)", ctx.drawerTplSel.general === "ok");
ok("复位随 dtPersistSel 落盘(autoqb.ui.drawerTpl)",
  (() => { try { return JSON.parse(store["autoqb.ui.drawerTpl"]).general === "ok"; } catch (e) { return false; } })());
ok("其它页签选择不受牵连",
  (() => { try { return JSON.parse(store["autoqb.ui.drawerTpl"]).trackers === "classic"; } catch (e) { return false; } })());
ok("挂载态已摘除(后续 _dtNotify 按缺省档路径续走)", ctx._dtMounted === null);
ok("宿主子树已清空", host.cleared === true && host.children.length === 0);
ok("变体 destroy 已回调(定时器/监听清理不丢)", host.destroyed === true);
ok("console.error 未吞栈且带页签与变体 id",
  errors.length === 1 && errors[0].indexOf("boom") >= 0 && errors[0].indexOf("general") >= 0);

/* 稳态: sel 已 = 缺省档(缺省档自身抛错路径不触及本函数, 但要稳) */
errors.length = 0;
delete store["autoqb.ui.drawerTpl"];
const ctx2 = makeCtx({ general: "ok", trackers: "classic", peers: "classic", content: "classic", traffic: "classic" });
M._dtRender.call(ctx2, { tab: "general", entry: st.entry, host: makeHost() });
ok("sel 已缺省档时稳态不重复复位不落盘", ctx2.drawerTplSel.general === "ok" && !("autoqb.ui.drawerTpl" in store));

console.error = realErr;
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed }));
if (failed.length) process.exit(1);
"""


def test_drawer_tpl_render_error_fallback_default():
    """变体渲染抛错自动回落**缺省档**守阵(P2-1, 报告 26-10-07-0542; 原名 ..._fallback_classic)。
    旧实现 catch 里只清宿主, 该页签整幅空白。有 node 时真跑 _dtRender 抛错电池钉住回落五件
    (复位该页签缺省档 + 落盘 / 不牵连其它页签 / 摘挂载态 / 清宿主 + destroy 回调 / console.error
    带页签与变体 id); 无 node 静态兜底: catch 块四要素缺一即红(只清宿主的空白降级不得回潮)。
    !2026-10-14: 经典渲染链移除后兜底不再是 classic —— 四内容页签的缺省档 = 该页签首个变体
    (defaultSel), 失败档恰为缺省档时不改写不落盘(宿主留空 + console.error 留痕)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    m = re.search(r"_dtRender\(st\) \{\n(.*?)\n      \},", core, re.S)
    assert m, "_dtRender 形态漂移(守阵正则失配, 同步本守阵)"
    catch = m.group(1)
    # R2 S1: 主列挂载态经 ownerKey 通道摘除(合并次列同式), 缺省键即主列 —— 语义等价旧直写
    assert 'this[st.ownerKey || "_dtMounted"] = null' in catch, \
        "回落必须摘挂载态(否则后续通知拿旧 st 重渲染已弃变体)"
    assert "window.AQB_DRAWER_TPL_REG.defaultSel(st.tab)" in catch and "this.dtPersistSel()" in catch, \
        "回落必须复位该页签到 defaultSel(缺省档)并落盘(状态单点仍是 drawerTplSel)"
    assert 'st.entry.id' in catch and "console.error" in catch, \
        "回落必须 console.error 且带变体 id(不静默吞栈)"
    assert "st.entry.destroy" in catch and "replaceChildren" in catch, \
        "回落必须按缺省档语义卸载变体(destroy + 清宿主)"
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _DT_FALLBACK_NODE_PROBE,
         os.path.join(shared, "drawer_templates.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"回落 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"回落电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_drawer_seed_reentry_variant_remount():
    """种子详情面板回页变体宿主重挂守阵(2026-10-07 报障「面板打开时切设置页再切回, 面板空白」)

    drawerVisible 要求 page === "groups"(drawer.js), tpl/drawer.html 的 <aside v-if> 在切到设置页
    时被整体拆掉(抽屉数据状态保留), 切回时 Vue 重建 aside —— 变体宿主(dt-host)随之换成新节点,
    而核心层 _dtMounted 持有的还是被拆走的旧宿主。trackers/peers 页签有 5s 轮询兜底(下一拍
    _dtNotify 自愈, 延迟 <=5s), general/content 页签没有轮询与通知源, 变体永不重挂:
    .dt-host:empty 藏住空宿主 + 经典包裹层 v-show 为 false(选中变体时)= 整幅正文空白。
    钉住(state.js watch drawerVisible):
    1. 种子详情支路(!s 分支)进场(v 为真)必须补一发重挂 `$nextTick(() => this._dtSync())` ——
       $nextTick 等 Vue 把重建的 aside 补进 DOM 后再定位宿主(_dtFindHost 按 document 现查);
    2. 退场(v 为假)不发重挂(种子形态退场无图可销毁, 重挂只服务进场);
    3. 两支路互不越界: 流量支路(qbCurScope 非空)退场 _qbChartDestroy / 进场 _qbReloadOnEnter
       原样保留, _dtSync 不得跑进流量支路(_qbReloadOnEnter 不得跑进种子支路);
    4. 重挂必须走 _dtSync 单点(卸旧挂新), 不得在 watcher 里自写宿主定位/渲染。"""
    state_js = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()

    wt = re.search(r"drawerVisible\(v\) \{\n(.*?)\n    \},", state_js, re.S)
    assert wt, "state.js 缺 watch(drawerVisible)(回页重挂挂点, 移动了就同步本守阵)"
    wb = wt.group(1)
    assert "if (!s) {" in wb, "watcher 缺种子详情支路(!s 分支)——回页重挂的挂点"
    # 1+2. 进场补一发重挂, 且只认进场(v 为真): $nextTick 等 aside 补进 DOM 再 _dtSync
    seed_branch = wb[wb.index("if (!s) {"):wb.index("if (!v) {")]
    assert "if (v)" in seed_branch and "$nextTick(() => this._dtSync())" in seed_branch, \
        "种子详情支路进场(v 为真)必须补一发重挂: $nextTick 等 DOM 补进后 _dtSync 卸旧挂新" \
        "(general/content 页签无轮询无通知源, 不补 = 回页整幅空白)"
    # 3. 两支路互不越界: 流量支路生命周期原样, _dtSync 不进流量支路
    traffic_branch = wb[wb.index("if (!v) {"):]
    assert "this._qbChartDestroy(s);" in traffic_branch and "this._qbReloadOnEnter(s);" in traffic_branch, \
        "流量支路退场销毁/进场补拉不得被回页重挂改动(uPlot 宿主生命周期单点)"
    assert "_dtSync" not in traffic_branch, \
        "重挂不得跑进流量支路(流量宿主重挂归 _qbReloadOnEnter -> _dtNotify 链)"
    assert "_qbReloadOnEnter" not in seed_branch, \
        "流量补拉不得跑进种子支路(种子页签无流量数据源)"
    # 4. 重挂走 _dtSync 单点, watcher 内不自写宿主定位/渲染
    assert "querySelector" not in seed_branch and "replaceChildren" not in seed_branch, \
        "watcher 不得自写宿主定位/渲染(重挂单点在核心层 _dtSync, 绕开即双写挂载态)"


def test_frontend_drawer_groups_shows_views():
    r"""辅种页/追剧页支持种子详情面板守阵(计划 26-10-08-1217)

    面板原先被两处守卫锁在种子页: drawerVisible 的 `viewMode === "torrents"` 与 openTorrentDrawer
    首行的同款守卫。辅种页/追剧页的成员行右键菜单早已复用单种子菜单(menu.hash 分支含「详细信息」),
    菜单项渲染且 hash 正确, 点下去却因守卫**静默失效**(不报错不提示)。本守阵钉住三视图一体化:

    1. 可见性单点 drawerVisible 只挡主内容页(形态分支已收归页面级);
    2. 打开单点 openTorrentDrawer 同样只挡主内容页;
    3. 两处成员行(辅种明细 / 追剧集明细)必须有 @dblclick 打开入口(与种子页同款);
    4. 键盘光标链 _kbRows 必须纳入展开的成员行(辅种的组下成员 / 追剧的集下成员), 否则 ↑↓
       走不到成员行、Alt+1~5 也解析不出目标(注释里原标「成员行 vNext」);
    5. 跟随 _kbFollowDrawer / 轮询 tick / 单种流量图 scope 三处守卫
       一律只挡主内容页 —— 换视图即停会让这两页的页签数据停在打开那一刻。

    任一守卫被改回按视图分叉即红(按视图各写一遍 = 又一处会漏的分叉)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()  # W1: 5s 轮询收口在数据层
    groups_tpl = open(os.path.join(shared, "tpl", "groups.html"), encoding="utf-8").read()
    shows_tpl = open(os.path.join(shared, "tpl", "shows.html"), encoding="utf-8").read()
    eng = open(os.path.join(shared, "shortcuts.js"), encoding="utf-8").read()
    chart_js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()

    # 1/2. 两个打开/可见单点都只挡主内容页
    vis = re.search(r"drawerVisible\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert vis, "drawer.js 缺 drawerVisible(面板可见性单点)"
    vb = vis.group(1)
    assert 'this.viewMode' not in vb, "drawerVisible 不得再按 viewMode 分叉(三视图共用面板)"
    op = re.search(r"async openTorrentDrawer\(hash\) \{\n(.*?)\n      this\.menu\.visible", drawer_js, re.S)
    assert op, "drawer.js 缺 openTorrentDrawer(打开单点, 守阵正则失配则同步本守阵)"
    assert 'if (this.page !== "groups") return;' in op.group(1), \
        "openTorrentDrawer 必须保留主内容页守卫(设置页没有 .drawer-dock)"
    assert "viewMode" not in op.group(1), "openTorrentDrawer 不得再按 viewMode 拒绝(成员行入口即静默失效)"

    # 3. 两处成员行的双击打开入口(与种子页 torrents.html 同款)
    for name, tpl in (("groups.html(辅种明细)", groups_tpl), ("shows.html(追剧集明细)", shows_tpl)):
        seg = tpl.split('class="member-row"')[1] if 'class="member-row"' in tpl else ""
        assert seg, f"{name} 缺 .member-row(守阵正则失配)"
        # 取该行的标签段(到下一个 `>` 为止), 避免吃到后续单元格里的同名字串
        tag = seg.split(">")[0]
        assert "@dblclick" in tag and "openTorrentDrawer(m.hash)" in tag, \
            f"{name} 成员行缺 @dblclick=\"openTorrentDrawer(m.hash)\"(双击打开详情)"

    # 4. 键盘光标链纳入展开的成员行(三视图 ↑↓ 可达成员行 -> Alt+1~5 目标解析可命中)
    rows = re.search(r"_kbRows\(\) \{\n(.*?)\n    \},", eng, re.S)
    assert rows, "shortcuts.js 缺 _kbRows(光标线性链)"
    rb = rows.group(1)
    assert 'kind: "torrent"' in rb, "_kbRows 必须能产出 kind=torrent 的成员行条目"
    assert "expandedKey" in rb, \
        "_kbRows 辅种分支必须纳入展开组的成员行(组内成员此前不在链上, 键盘走不进去)"
    assert "expandedShowEp" in rb, \
        "_kbRows 追剧分支必须纳入展开集的成员行(集内版本此前不在链上)"

    # 5. 三处守卫一律只挡主内容页
    follow = re.search(r"_kbFollowDrawer\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert follow and "viewMode" not in follow.group(1), \
        "_kbFollowDrawer 不得再挡视图(三视图共用: 辅种/追剧成员行光标同样要跟随)"
    poll = re.search(r"_startDrawerPoll\(\) \{\n(.*?)\n    \},", store_js, re.S)
    assert poll, "drawer_store.js 找不到主节拍轮询 _startDrawerPoll(2026-10-22 起走骨架 startPoll 声明式)"
    assert "viewMode" not in poll.group(1), \
        "主节拍轮询不得再挡视图(换视图即停会让这两页的页签数据停在打开那一刻)"
    assert 'this.page === "groups"' in poll.group(1), \
        "主节拍轮询必须带主内容页守卫(2026-10-22 起写在骨架的 guard 声明里: 面板开 + 在主内容页)"
    tor = re.search(r"  torrent: \{(.*?)\n  \},", chart_js, re.S)
    assert tor, "qb_traffic_chart.js 缺 torrent 作用域(单种流量图)"
    assert "viewMode" not in tor.group(1), \
        "单种流量图 active 不得再挡视图(辅种/追剧页打开的种子详情其流量页签同样要拉要画)"


def test_frontend_drawer_open_switch_no_empty_flash():
    """详情面板显式换目标不闪空态守阵(2026-10-07 报障「切换种子时用户页闪'暂无已连接用户'」)

    显式入口(双击/Enter/右键「详情」)与键盘跟随不同: openTorrentDrawer 走整体重建, 把
    peers/trackers/files 清成空列表且 loading=false, 详情在途的整个等待期被渲染成一帧空态
    (空态 -> 加载态 -> 数据三连闪, 高度自适应面板还会塌一下; 经典链与变体两路都中)。
    两半修法钉住(pitfalls/web-ui/drawer-switch-flicker):
    1. 面板已开(种子形态)不得重建: 换目标交棒 _switchDrawerTarget 软切换(保留旧数据 + 160ms
       延迟遮罩, 与键盘跟随同链路), 同目标重入短路零副作用(与 openDrawerTraffic 同口径,
       「打开入口的重入语义」)—— 分支必须落在 _stopDrawerPoll 等重建
       副作用之前才算短路(同 test_frontend_qb_traffic_drawer_page_guard 第 5 锚口径);
    2. 冷启动重建(面板关着/流量形态换形, 无旧数据可保留): 初值页签的 loading 必须与空列表
       同帧置位, 详情在途窗口渲染加载态而非空态; 翻转仍归 fetcher 落袋单点(loading 清掉后才
       _dtNotify), 这里只保证等待期不落空态。"""
    drawer_js = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()

    m = re.search(r"async openTorrentDrawer\(hash\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert m, "drawer.js 缺 openTorrentDrawer(守阵正则失配, 同步本守阵)"
    ob = m.group(1)

    # 1. 已开(种子形态)重入分支: 同目标短路 + 换目标软切换, 先于重建副作用
    # (W3 计划 26-10-11-2106: 判据走单点 drawerIsSeed —— 口径不变, 断言面随之)
    assert 'if (this.drawer.open && this.drawerIsSeed) {' in ob, \
        "openTorrentDrawer 缺已开重入分支: 面板开着换种子仍走整体重建 = 空态->加载态->数据三连闪"
    assert ob.index('this.drawer.open && this.drawerIsSeed') < ob.index("this._stopDrawerPoll()"), \
        "重入分支必须落在重建副作用(_stopDrawerPoll)之前(落在后面 = 短路失效, 闪烁回归)"
    assert "if (this.drawer.hash === hash) return;" in ob, \
        "缺同目标幂等短路: 面板开着重按同一目标, 整体重建把旧数据连 loading 各闪一遍"
    assert "this._switchDrawerTarget(hash);" in ob, \
        "已开换目标必须交棒软切换单点(保留旧数据 + 160ms 延迟遮罩), 不得自写清空/重建"
    i_short = ob.index("if (this.drawer.hash === hash)")
    i_switch = ob.index("this._switchDrawerTarget(hash);")
    assert i_short < i_switch, \
        "重入分支次序必须为 同目标短路 -> 换目标交棒"

    # 2. 冷启动重建: 初值页签 loading 与空列表同帧置位(等待期渲染加载态, 不落空态)
    dm = re.search(r"this\.drawer = \{\n(.*?)\n      \};", ob, re.S)
    assert dm, "openTorrentDrawer 缺 drawer 重建字面量(守阵正则失配, 同步本守阵)"
    db = dm.group(1)
    assert 'trackersLoading: initialTab === "trackers"' in db, \
        "重建初值 trackersLoading 恒 false: 初值页签=trackers 时详情在途窗口闪一帧「暂无 tracker」"
    assert 'filesLoading: initialTab === "content"' in db, \
        "重建初值 filesLoading 恒 false: 初值页签=content 时详情在途窗口闪一帧「无文件列表」"
    assert 'peersLoading: initialTab === "peers"' in db, \
        "重建初值 peersLoading 恒 false: 初值页签=peers 时详情在途窗口闪一帧「暂无已连接用户」"


def test_drawer_peers_speed_keys_normalized():
    """抽屉 peers 速度键名适配守阵(2026-10-10 用户报障「种子详情用户页上下行始终为 0」)。

    真 qB sync/torrentPeers 的对端速度字段是 dl_speed / up_speed(与列表侧 torrents/info 的
    dlspeed / upspeed **不同名**)—— 前端抽屉的全部 peers 消费点(经典表经 drawerPeerRows,
    变体 07/08/09 的 peerList 直读原始对端对象)统一按 dlspeed / upspeed 取名, 故落袋单点
    _fetchDrawerPeers 必须过 _drawerNormPeers 做键名适配(补 dlspeed / upspeed), 否则取不到值
    → 上下行恒 0(用户报障)。本守阵钉三件事:
    ① _drawerNormPeers 存在且 dl_speed/up_speed 两键映射齐全、dict/数组双形态同归一;
    ② peers 落袋必须走该单点(直存 qB 原始响应 ⇒ 原始键名漏进消费点);
    ③ 桩服务 scripts/ui_harness.py 合成对端的速度键名也是 qB 原始 dl_speed / up_speed
       —— 曾按 dlspeed / upspeed 造假数据, 冒烟「看得见速度」而真机恒 0(测假逃逸本 bug)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()  # W1: 数据/行为层

    # ① 键名适配单点
    norm = re.search(r"_drawerNormPeers\(resp\) \{(.*?)\n    \},", store_js, re.S)
    assert norm, "drawer_store.js 缺 _drawerNormPeers(qB 对端速度键名适配单点; 缺则上下行恒 0)"
    nb = norm.group(1)
    assert "x.dlspeed === undefined && x.dl_speed !== undefined" in nb, \
        "_drawerNormPeers 未把 qB dl_speed 适配到 dlspeed"
    assert "x.upspeed === undefined && x.up_speed !== undefined" in nb, \
        "_drawerNormPeers 未把 qB up_speed 适配到 upspeed"
    assert "Array.isArray(r.peers)" in nb and "Object.entries(r.peers)" in nb, \
        "_drawerNormPeers 必须同时覆盖 peers 的 dict 与数组双形态(真 qB 恒 dict)"

    # ② 落袋单点走适配(直存 r 即漏原始键名)。2026-10-13 软切换宽限引入 norm 局部量
    #    (首个空响应「未就绪」时保留旧数据不落袋, 见下条守阵), 故断言形改为「归一结果才是落袋值」。
    #    R21-A-01(2026-10-21): 归一外置到差异表 peers 条目(norm(vm, r)), 落袋在唯一骨架 —— 两处各钉一半。
    skel, ftable = _drawer_fetch_parts(store_js)
    peers = re.search(r"\n  peers: \{(.*?)\n  \},", ftable, re.S)
    assert peers, "差异表找不到 peers 条目(改名或书写形态漂移? 同步本守阵)"
    pb = peers.group(1)
    # W5(26-10-13-0811): 落袋改「norm → 引用稳定合并」两步 —— 归一仍是落袋前置单点,
    # 合并(_dtMergeRows)保行对象引用稳定(写字段不重建, 行 DOM 身份恒定)。
    assert "const norm = vm._drawerNormPeers(r);" in pb, \
        "peers 归一未过 _drawerNormPeers(直存 qB 原始响应 ⇒ 原始键名漏进消费点, 上下行恒 0)"
    assert "Object.values(norm.peers || {})" in pb, \
        "peers 归一必须覆盖 dict 形态(真 qB 恒 dict, 只认数组 = 真机恒空)"
    assert 'pack: (rows) => ({ peers: rows }),' in pb, \
        "peers 的目标状态键形状必须是 { peers }(消费点按 drawer.peers.peers 读, 裸数组即整页空)"
    assert "_dtMergeRows(" in skel, \
        "落袋未走引用稳定合并(W5/L5: 整组换数组 = 行重建, 速度格节点身份不保)"

    # ③ 桩保真: 合成对端的键名必须与真 qB 同形(dl_speed / up_speed)
    harness = (Path(__file__).resolve().parents[1] / "scripts" / "ui_harness.py").read_text(encoding="utf-8")
    assert '"dl_speed": dl_speed,' in harness and '"up_speed": up_speed,' in harness, \
        "ui_harness 合成 peer 的速度键必须用 qB 原始 dl_speed / up_speed(用 dlspeed/upspeed 即测假, 真机恒 0)"
    assert '"dlspeed": dlspeed,' not in harness and '"upspeed": upspeed,' not in harness, \
        "ui_harness 合成 peer 残留错误的速度键名(dlspeed/upspeed) —— 与真 qB 不同形, 冒烟测假"


def test_drawer_list_switch_no_loading_flash_wiring():
    """抽屉三列表软切换「不闪」守阵(2026-10-13 用户报障「切换种子时用户页闪『暂无已连接用户』」)。

    真根因(逐帧实测, 坑档 drawer-switch-flicker 第九次形态): 软切换(FX-29)保留的是**上一个目标的
    已落袋结果**, 而**空列表(没有对端 / 没有 tracker)是种子的常态** —— 但三个列表 fetcher 一律
    `loading = true`, 模板门 `loading && 无行` 就把这份既有的空态顶掉一帧换成「正在加载…」, 数据(空)
    回来再换回 ⇒ 用户看到「『暂无已连接用户』闪烁」(临时探针实测序列 `E→L→E`)。
    修法 = 换目标窗口(`_drawerSoftSwitch`)内**不置**列表 loading 门(`_drawerListLoadingOn`), 保留那份
    旧结果直到被新结果取代。⚠ **不得**改成「空响应视为未就绪 → 延迟渲染/重拉」: 那会把常态的空推迟
    (首版固定 1s 重拉被用户否掉 —— 「种子的常态就是没有对端」, 且后端对空响应还有 1s 短缓存)。
    行为回归由 e2e/drawer-switch-no-flash.spec.mjs 逐帧采样值守(空态全程在 + 无「正在加载…」+ 无重试
    请求); 本守阵只钉静态接线与关键次序, 防机制被无声拆除。
    """
    store_js = open(os.path.join(STATIC_ROOT, "shared", "drawer_store.js"), encoding="utf-8").read()

    # ① 门抑制单点: 判据 = 非静默 且 不在软切换窗口
    m = re.search(r"_drawerListLoadingOn\(silent\) \{(.*?)\n    \},", store_js, re.S)
    assert m, "drawer_store.js 找不到 _drawerListLoadingOn(改名或挪走了? 同步本守阵)"
    assert "return !silent && !this._drawerSoftSwitch;" in m.group(1), \
        "门抑制判据不符(应 = 非静默 且 不在软切换窗口)"

    # ② 三列表的 loading 置位必须都经该单点(直写 `if (!silent) xxxLoading = true` = 软切换时门会闪)
    #    R21-A-01(2026-10-21): 置位动作收在唯一骨架里, 字段名由差异表 loadingKey 给 ——
    #    表里缺哪个源, 那个源就退回「直写」或干脆不置门, 故这里逐个字段钉表 + 骨架只此一处写法。
    skel, ftable = _drawer_fetch_parts(store_js)
    assert "if (this._drawerListLoadingOn(silent)) this.drawer[cfg.loadingKey] = true;" in skel, \
        "骨架的列表 loading 置位未走 _drawerListLoadingOn(软切换时门会闪)"
    assert "if (!silent) this.drawer[cfg.loadingKey] = true;" not in skel, \
        "骨架回潮为直写 loading(软切换时会闪『正在加载…』)"
    for flag in ("peersLoading", "trackersLoading", "filesLoading"):
        assert f'loadingKey: "{flag}"' in ftable, \
            "差异表缺 %s 的 loading 门字段(该源不经门抑制单点, 软切换时门会闪)" % flag

    # ③ 标记置位必须在 _loadDrawerTab **之前**(三 fetcher 在其内 await 前同步读它)
    sw = re.search(r"_switchDrawerTarget\(hash\) \{(.*?)\n    \},", store_js, re.S)
    assert sw, "drawer_store.js 找不到 _switchDrawerTarget(改名或挪走了? 同步本守阵)"
    sb = sw.group(1)
    i_flag = sb.find("this._drawerSoftSwitch = true;")
    i_load = sb.find("this._loadDrawerTab(this.drawer.tab);")
    assert i_flag >= 0 and i_load >= 0, "软切换标记置位或 _loadDrawerTab 调用缺失"
    assert i_flag < i_load, \
        "软切换标记必须在 _loadDrawerTab **之前**置位(置后 = 本次 fetcher 读不到, 门照闪)"

    # ④ _stopDrawerPoll **不得**清该标记(它在 _loadDrawerTab→_startDrawerPoll 途中被调用)
    stop = re.search(r"_stopDrawerPoll\(\) \{(.*?)\n    \},", store_js, re.S)
    assert stop, "drawer_store.js 找不到 _stopDrawerPoll(改名或挪走了? 同步本守阵)"
    assert "this._drawerSoftSwitch =" not in stop.group(1), \
        "_stopDrawerPoll 赋值/清空了 _drawerSoftSwitch —— 它会在 _loadDrawerTab→_startDrawerPoll 途中被调用, 等于置前失效, 门照闪"

    # ⑤ 落定/打断必须清标记(否则标记粘住, 此后切页签不再置 loading); 且"延迟渲染空态"类机制不得回潮
    end = re.search(r"_drawerSwitchEnd\(\) \{(.*?)\n    \},", store_js, re.S)
    assert end, "drawer_store.js 找不到 _drawerSwitchEnd(改名或挪走了? 同步本守阵)"
    assert "this._drawerSoftSwitch = false;" in end.group(1), \
        "_drawerSwitchEnd 未清 _drawerSoftSwitch(标记会粘住, 后续切页签不再置 loading)"
    for gone in ("_drawerGraceHold", "_DRAWER_GRACE_DELAYS", "_drawerPeerCount"):
        assert gone not in store_js, \
            "旧的『空响应视为未就绪→延迟重拉』机制(%s)不得回潮(会把常态空态推迟)" % gone


_NODE_DRAWER_FETCH_PROBE = r"""
const path = process.argv[1];
global.window = {};
require(path);
const M = global.window.AQB_DRAWER_STORE.methods;
const checks = [];
const ck = (name, cond) => checks.push({ name: name, ok: !!cond });

/* 假 vm: 只把「抽屉状态 + 四个外部触点(api/toast/_dtNotify/_drawerDone)」换成探针可观测的桩,
 * 骨架/_drawerStale/_drawerNormPeers/_fetchDrawer* 全用真实现。gateAtRequest 记录「请求发出那一刻」
 * 三个 loading 门的值 —— 门是同步置的, 只有在这一刻看才分得清 silent / 软切换窗口的抑制。 */
const mk = (over) => {
  const vm = Object.assign({}, M);
  vm.drawer = Object.assign({
    open: true, hash: "h1", tab: "trackers", loading: false, error: "", detail: null,
    trackers: [], files: [], peers: { peers: [] },
    trackersLoading: false, filesLoading: false, peersLoading: false,
    trackersError: "", filesError: "", peersError: "",
  }, over || {});
  vm._drawerLoadSeq = 0;
  vm._drawerSoftSwitch = false;
  vm.calls = [];
  vm.notify = [];
  vm.done = [];
  vm.toasts = [];
  vm.gateAtRequest = [];
  vm.reply = async () => null;
  vm.toast = (m) => vm.toasts.push(m);
  vm._dtNotify = (src) => vm.notify.push({ src: src, detail: vm.drawer.detail,
    t: vm.drawer.trackersLoading, f: vm.drawer.filesLoading, p: vm.drawer.peersLoading });
  vm._drawerDone = (src, hash, seq) => vm.done.push([src, hash, seq]);
  vm.api = async (url) => {
    vm.calls.push(url);
    vm.gateAtRequest.push({ t: vm.drawer.trackersLoading, f: vm.drawer.filesLoading,
      p: vm.drawer.peersLoading, l: vm.drawer.loading });
    return vm.reply(url);
  };
  return vm;
};

(async () => {
  /* ---- detail: 恒置 loading / 空载荷=种子不存在 / 失败不 toast / 鉴权失败不写 error ---- */
  let vm = mk({ tab: "general" });
  vm.reply = async () => ({ torrent: { name: "n1" } });
  await vm._fetchDrawerDetail();
  ck("detail 端点", vm.calls[0] === "/api/torrents/h1");
  ck("detail 落袋", vm.drawer.detail && vm.drawer.detail.name === "n1");
  ck("detail 请求期置 loading", vm.gateAtRequest[0].l === true);
  ck("detail 清 loading", vm.drawer.loading === false);
  ck("detail 通知一次且已落袋", vm.notify.length === 1 && vm.notify[0].src === "detail" && vm.notify[0].detail.name === "n1");
  ck("detail 落定登记", vm.done.length === 1 && vm.done[0].join(",") === "detail,h1,0");

  vm = mk({ tab: "general" });
  vm.reply = async () => ({});
  await vm._fetchDrawerDetail();
  ck("detail 空载荷=种子不存在", vm.drawer.detail === null && vm.drawer.error === "种子不存在或已被删除");

  vm = mk({ tab: "general" });
  vm.reply = async () => { throw new Error("boom"); };
  await vm._fetchDrawerDetail();
  ck("detail 失败落 error", vm.drawer.error === "boom");
  ck("detail 失败不 toast", vm.toasts.length === 0);
  ck("detail 失败也登记落定", vm.done.length === 1);

  vm = mk({ tab: "general" });
  vm.reply = async () => Promise.reject(Object.assign(new Error("401"), { auth: true }));
  await vm._fetchDrawerDetail();
  ck("detail 鉴权失败不写 error", vm.drawer.error === "");

  /* ---- trackers: 引用稳定合并 / 行键 url / 门抑制 / 失败标记与 toast ---- */
  const oldRow = { url: "u1", seeds: 1 };
  vm = mk({ trackers: [oldRow] });
  vm.reply = async () => ([{ url: "u2", seeds: 3 }, { url: "u1", seeds: 2 }]);
  await vm._fetchDrawerTrackers(false);
  ck("trackers 端点", vm.calls[0] === "/api/torrents/h1/trackers");
  ck("trackers 行对象引用稳定", vm.drawer.trackers.length === 2 && vm.drawer.trackers[1] === oldRow && oldRow.seeds === 2);
  ck("trackers 按服务端序重建", vm.drawer.trackers[0].url === "u2");
  ck("trackers 请求期置门", vm.gateAtRequest[0].t === true);
  ck("trackers 通知在清门之后", vm.notify.length === 1 && vm.notify[0].t === false);

  vm = mk({ trackersError: "旧错" });
  vm.reply = async () => ([]);
  await vm._fetchDrawerTrackers(false);
  ck("trackers 成功清失败标记", vm.drawer.trackersError === "");
  ck("trackers 空响应=空列表", Array.isArray(vm.drawer.trackers) && vm.drawer.trackers.length === 0);

  vm = mk();
  vm.reply = async () => { throw new Error("net"); };
  await vm._fetchDrawerTrackers(true);
  ck("silent 不置门", vm.gateAtRequest[0].t === false);
  ck("silent 失败仍落标记", vm.drawer.trackersError === "net");
  ck("silent 失败不 toast", vm.toasts.length === 0);

  vm = mk();
  vm.reply = async () => { throw new Error("net"); };
  await vm._fetchDrawerTrackers(false);
  ck("失败 toast 带源前缀", vm.toasts.length === 1 && vm.toasts[0] === "tracker 列表获取失败: net");

  vm = mk();
  vm._drawerSoftSwitch = true;
  vm.reply = async () => ([]);
  await vm._fetchDrawerTrackers(false);
  ck("软切换窗口不置门", vm.gateAtRequest[0].t === false);
  ck("软切换窗口通知仍在", vm.notify.length === 1);

  /* ---- files: 行键 index(缺则 name) ---- */
  const oldFile = { index: 2, name: "b.mkv", size: 1 };
  vm = mk({ files: [oldFile] });
  vm.reply = async () => ([{ name: "a.mkv", size: 1 }, { index: 2, name: "b.mkv", size: 9 }]);
  await vm._fetchDrawerFiles(false);
  ck("files 端点", vm.calls[0] === "/api/torrents/h1/files");
  ck("files 行键 index 优先(引用稳定)", vm.drawer.files.length === 2 && vm.drawer.files[1] === oldFile && oldFile.size === 9);
  ck("files 缺 index 用 name 作行键", vm.drawer.files[0].name === "a.mkv");

  /* ---- peers: 键名适配 + { peers } 形状 + 行键 ---- */
  vm = mk();
  vm.reply = async () => ({ peers: { a: { ip: "1.1.1.1", port: 5, dl_speed: 100, up_speed: 20 } } });
  await vm._fetchDrawerPeers(false);
  const plist = vm.drawer.peers && vm.drawer.peers.peers;
  ck("peers 端点", vm.calls[0] === "/api/torrents/h1/peers");
  ck("peers 目标状态键形状 {peers}", Array.isArray(plist));
  ck("peers 归一键名适配", plist[0].dlspeed === 100 && plist[0].upspeed === 20);
  ck("peers 行键 ip:port", plist.length === 1);

  vm = mk();
  vm.reply = async () => { throw new Error("x"); };
  await vm._fetchDrawerPeers(false);
  ck("失败也登记落定(遮罩不挂死)", vm.done.length === 1 && vm.done[0][0] === "peers");

  /* ---- 竞态: 过期代际 / 换目标后旧响应一律丢弃 ---- */
  vm = mk({ trackers: [{ url: "old" }] });
  vm._drawerLoadSeq = 9;
  vm.reply = async () => ([{ url: "new" }]);
  await vm._fetchDrawerTrackers(false, 8);
  ck("过期代际不落袋", vm.drawer.trackers.length === 1 && vm.drawer.trackers[0].url === "old");
  ck("过期代际不通知", vm.notify.length === 0);
  ck("过期代际不动 loading", vm.drawer.trackersLoading === true);

  vm = mk({ tab: "general" });
  let release = null;
  vm.reply = () => new Promise((res) => { release = () => res({ torrent: { name: "old" } }); });
  const inflight = vm._fetchDrawerDetail();
  vm.drawer.hash = "h2";
  release();
  await inflight;
  ck("换目标后旧响应不落袋", vm.drawer.detail === null);
  ck("换目标后旧响应不通知", vm.notify.length === 0);

  const failed = checks.filter((c) => !c.ok).map((c) => c.name);
  console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
})();
"""


def test_drawer_fetcher_skeleton_single_point():
    """抽屉四 fetcher 收敛守阵(R21-A-01, issue 26-10-20-2231-refactor-fe-drawer-fetcher-boilerplate-dup)。

    现象(入池 2026-10-20 22:31, 认领复验 2026-10-21 05:34 仍在): detail / trackers / files / peers
    四份 fetcher 骨架相同(每份 ~22 行) —— 「hash 快照 → loading 门 → stale 守卫 → 合并落袋 → 清标记 →
    catch → finally(清 loading → _dtNotify → _drawerDone)」的次序是有心之作, 却抄了四遍(全层 13 个
    `_drawerStale` 判点)。次序错一处不报错, 只静默变成用户可见故障: 旧响应覆盖新目标(W2) /
    空列表停「正在加载…」一拍轮询(2026-10-07 报障) / FX-29 遮罩等一个永不到手的源挂死(2026-10-04)。

    修法 = **唯一骨架** `_fetchDrawerSource(src, silent, seq)` + 顶层差异表 `_DT_FETCH`
    (端点 url / 归一 norm / 目标状态键 key / 空值形状 rows+pack, 外加 loading 门字段 / 失败标记 /
    通知时机)。本守阵钉四件事:

    ① 骨架只有一份、`await this.api(` 全层只有一处, 四个具名入口必须是**单行薄壳**(自带请求 = 又一份
      次序; 薄壳里写第二行 = 差异项没进表);
    ② `this._drawerStale(hash, seq)` 全层恰 4 处(骨架成功/异常/finally 三路 + `_drawerDone` 一处),
      多一处即回潮;
    ③ 差异表四源齐全、每源字段逐项在位(端点/归一/状态键/空值形状/loadingKey/errKey), 且端点字面量
      只许出现在表里(骨架与薄壳都不认 `/api/torrents/`);
    ④ 有 node 时真跑 37 项行为电池 —— 同一电池对**收敛前的四份实现**同样 37/37 全绿(实测), 所以它证明
      的是「行为不变」, 不是「形态变成这样」。电池覆盖: 四源成功/空载荷/鉴权/静默/失败、软切换窗口与
      silent 都不置门、引用稳定合并(行对象身份)、三张行键口径、peers 键名适配、过期代际与换目标丢弃、
      失败也登记落定。
    """
    store_js = open(os.path.join(STATIC_ROOT, "shared", "drawer_store.js"), encoding="utf-8").read()
    skel, ftable = _drawer_fetch_parts(store_js)

    # ① 骨架单份 + 具名入口只许是薄壳
    assert len(re.findall(r"async _fetchDrawerSource\(", store_js)) == 1, \
        "取数骨架出现多份(落地次序又分裂了)"
    assert store_js.count("await this.api(") == 1, \
        "drawer_store.js 出现第二处 api 调用(应只有骨架一处, 否则就是又一份次序)"
    for fn in ("_fetchDrawerDetail", "_fetchDrawerTrackers", "_fetchDrawerFiles", "_fetchDrawerPeers"):
        body = re.search(rf"async {fn}\(.*?\) \{{(.*?)\n    \}},", store_js, re.S)
        assert body, f"{fn} 形态漂移(守阵正则失配, 同步本守阵)"
        lines = [ln for ln in body.group(1).strip().splitlines() if ln.strip()]
        assert len(lines) == 1 and "this._fetchDrawerSource(" in lines[0], \
            f"{fn} 不再是单行薄壳(任何额外逻辑都应进 _DT_FETCH 表或骨架, 不许在各入口各写一份)"

    # ② stale 判点收敛
    assert skel.count("this._drawerStale(hash, seq)") == 3, \
        "骨架必须成功/异常/finally 三路都过 _drawerStale(任一路缺失 = 慢响应覆盖新目标)"
    assert store_js.count("this._drawerStale(hash, seq)") == 4, \
        "stale 判点应恰为骨架 3 路 + _drawerDone 1 处(多出来的 = 又有一份落地次序)"

    # ③ 差异表字段齐全 + 端点单点
    assert len(re.findall(r"^  (\w+): \{", ftable, re.M)) == 4, "差异表条目数不是 4(多源少源都要同步本守阵)"
    for src in ("detail", "trackers", "files", "peers"):
        entry = re.search(rf"\n  {src}: \{{(.*?)\n  \}},", ftable, re.S)
        assert entry, f"差异表缺 {src} 源或书写形态漂移(同步本守阵)"
        e = entry.group(1)
        for field in ("url:", "key:", "norm:", "rowKey:", "failText:", "notifyAtLand:"):
            assert field in e, f"差异表 {src} 条目缺 {field}(该源的差异项没声明全)"
        if src == "detail":  # 不合并: 整值落袋, 无 loading 门/失败标记/提示
            assert "rowKey: null" in e and "loadingKey: null" in e and "errKey: null" in e, \
                "detail 应声明 rowKey/loadingKey/errKey 为 null(它走 drawer.loading 与 drawer.error)"
        else:
            assert "rows:" in e and "pack:" in e, f"{src} 未声明空值形状(rows 取旧行 / pack 写回)"
            assert f'errKey: "{src}Error"' in e, f"{src} 的失败标记字段没在表里声明(P3-5)"
            assert 'loadingKey: "' in e, f"{src} 的 loading 门字段没在表里声明(软切换守不住)"
    assert len(re.findall(r"url: \(hash\) => `/api/torrents/", store_js)) == 4, \
        "四个端点应只在差异表各声明一次(散回骨架/入口 = 端点双份)"
    assert "/api/torrents/" not in skel, "骨架里出现端点字面量(它不该认识具体数据源)"

    # ④ 有 node 时真跑行为电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_DRAWER_FETCH_PROBE,
             os.path.join(STATIC_ROOT, "shared", "drawer_store.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"抽屉取数电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"抽屉取数电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


_NODE_DT_TABLE_PROBE = r"""
const path = process.argv[1];
global.window = {};
require(path);
const DT = global.window.DT_TABLE;
const checks = [];
const ck = (name, cond) => checks.push({ name: name, ok: !!cond });

const cols = [{ key: "a", tpl: "10px", align: "right" }, { key: "b" }];
const lay = DT.layout(cols);
ck("count=列数", lay.count === 2);
ck("缺宽回缺省轨道", lay.tracks[1] === DT.DEFAULT_TRACK);
ck("gridTemplate=tracks 拼接", lay.gridTemplate === lay.tracks.join(" "));
ck("aligns 随列出", lay.aligns[0] === "right" && lay.aligns[1] === "left");
ck("keys 随列出", lay.keys.join(",") === "a,b");
const lay2 = DT.layout(cols, { a: "99px" });
ck("固化宽度覆盖", lay2.tracks[0] === "99px");
ck("覆盖后仍单一出口", lay2.gridTemplate === lay2.tracks.join(" "));

ck("hasArrow 认方向符", DT.hasArrow("↑ 占用") === true);
ck("hasArrow 放过纯文案", DT.hasArrow("占用") === false);
ck("checkLabels 命中违规列", DT.checkLabels([{ key: "x", label: "↑ 占用" }]).join() === "x");
ck("checkLabels 干净列零报", DT.checkLabels(cols).length === 0);

DT.registerCell("t", () => "T");
ck("登记后取得到", DT.cellOf("t")() === "T");
let threw = false;
try { DT.cellOf("nope"); } catch (e) { threw = true; }
ck("未登记即抛(不许渲染空白)", threw);

/* assertLayout: 三处计数 —— 网格轨道 / 列头格 / 数据行子格 */
global.window.getComputedStyle = () => ({ gridTemplateColumns: "10px 20px" });
const head = { querySelectorAll: () => ({ length: 2 }) };
ck("一致时零问题", DT.assertLayout(head, { children: { length: 2 } }, cols).length === 0);
const bad = DT.assertLayout(head, { children: { length: 3 } }, cols);
ck("多一格即报", bad.length === 1 && /子格数 3 != 列数 2/.test(bad[0]));
const bad2 = DT.assertLayout({ querySelectorAll: () => ({ length: 1 }) }, { children: { length: 2 } }, cols);
ck("少一列头即报", bad2.some((p) => /列头格数 1 != 列数 2/.test(p)));
ck("未挂载不算不一致", DT.assertLayout(null, null, cols).length === 0);

const failed = checks.filter((c) => !c.ok).map((c) => c.name);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""


def test_dt_table_kernel_single_point():
    """详情面板表格内核守阵(计划 26-10-13-0811 W1)

    用户报的八项表格症状归三个根因簇, 簇 A 是「一张表的几何与列被互不相识的几处各算一遍,
    且没有任何一处做一致性校验」—— 表现是表头错位 / 多出的横带 / 内容挤成一堆 / 对齐不一致 /
    列名自带方向符号再叠一个排序箭头。本守阵钉内核这条解:

    ① 三份 manifest 都登记 dt_table.js 且文件在盘上(缺一份 = 该皮肤整块功能静默消失);
    ② 四个对外口子齐全(layout / assertLayout / checkLabels / registerCell);
    ③ 几何单一出口 —— 轨道串 / 对齐 / 列键**同一个返回值**里出来, 且 gridTemplate 恒等于
       tracks.join(" ")(调用方不许再自己拼一次, 拼了就又是一处事实源);
    ④ L3 守卫 —— 列名是纯文案, 方向符号只能由排序态单点渲染(表壳 .arrow); 全仓列定义的
       label 字段零方向符, 用户报的「密度雷达占用表头前多一个箭头」不得回潮;
    ⑤ 渲染即自查 —— assertLayout 三处计数(轨道 / 列头格 / 数据行子格)必须相等, 不相等就是
       「多一格 / 少一列」, 而它的视觉表现正是「速度列下方有异常横带」与「多列内容挤在一起」;
       未挂载/未渲染一律不算不一致(面板没开时不得满屏报错)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js_path = os.path.join(shared, "dt_table.js")
    assert os.path.isfile(js_path), "shared/dt_table.js 不在盘上(内核失踪)"

    # ① 三皮肤清单登记(与 qb_traffic_chart.js 同款纪律)
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        assert "/shared/dt_table.js" in mf["scripts"], f"{ui} 清单缺 dt_table.js(该皮肤无内核)"

    js = open(js_path, encoding="utf-8").read()

    # ② 对外口子
    for port in ("layout:", "assertLayout:", "checkLabels:", "registerCell:", "cellOf:", "hasArrow:"):
        assert port in js, f"dt_table.js 缺对外口子 {port}(内核契约不全)"
    assert "window.DT_TABLE" in js, "dt_table.js 未挂 window.DT_TABLE(调用方取不到)"

    # ④ L3: 列定义的 label 字段零方向符(扫列定义单点 app.js + 变体文件)
    arrow_re = re.compile(r"[\u2190-\u21ff\u25b2\u25bc\u25c0-\u25ff\u2b00-\u2bff\u27a1\u2b05\u2b06\u2b07]")
    app_js = _app_bundle_text()
    for m in re.finditer(r'label:/s*"([^"]*)"', app_js):
        assert not arrow_re.search(m.group(1)), \
            f"列名 {m.group(1)!r} 自带方向符号 —— 方向只能由排序态单点渲染(表壳 .arrow), " \
            "写在 label 里会与它叠加成两个箭头"
    # 具体回潮钉: 只针对列定义书写形态(注释里提到旧名不算回潮, 但会被上面那条正则误伤, 故分开)
    assert 'label: "\u2191 \u5360\u7528"' not in app_js, \
        "09 密度雷达的列名不得回潮成「↑ 占用」(用户 2026-10-13 报障: 表头前多一个箭头)"
    tpl_dir = os.path.join(shared, "drawer_tpl")
    for name in sorted(os.listdir(tpl_dir)):
        if not name.endswith(".js"):
            continue
        txt = open(os.path.join(tpl_dir, name), encoding="utf-8").read()
        for m in re.finditer(r'label:/s*"([^"]*)"', txt):
            assert not arrow_re.search(m.group(1)), \
                f"{name} 的列名 {m.group(1)!r} 自带方向符号(与排序箭头叠加)"

    # ③⑤ 有 node 时真跑电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_DT_TABLE_PROBE, js_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"dt_table node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"表格内核电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_drawer_tpl_no_table_variants_out_of_scope():
    """范围守恒(计划 26-10-13-0811 §10/W0): 四个无表格变体一行不改的自动化断言。

    01/02/03(常规页)/ 12(空间树图)不含表格体 —— 表格重写的改动面是「八个含表格变体的表格体
    + 引擎侧列派生」, 这四个文件必须在引擎契约之外。
    判据: 文件内零引擎表格契约引用(tableId / rowsFn / dt-table-anchor / .group-head /
    .group-row / DT_TABLE / dt_table)—— 谁往后把表格体塞进这四个变体, 必须先来改本守阵
    (把该文件挪进含表格名单), 不允许静默越界。
    (2026-10-14: 原列的 13/14/15(流量图)三变体已随流量页签变体移除, 从名单消失。)
    """
    tpl_dir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    no_table = (
        "01-general-hero-tall.js",
        "02-general-cards-low.js",
        "03-general-dossier-collapsed.js",
        "12-content-space-treemap-collapsed.js",
    )
    for name in no_table:
        path = os.path.join(tpl_dir, name)
        assert os.path.isfile(path), f"drawer_tpl/{name} 缺文件(变体失踪)"
        txt = open(path, encoding="utf-8").read()
        for marker in ("tableId", "rowsFn", "dt-table-anchor", "group-head", "group-row", "DT_TABLE", "dt_table"):
            assert marker not in txt, \
                f"drawer_tpl/{name} 引用了引擎表格契约 {marker!r} —— 无表格变体越界进改动面" \
                "(范围守恒 §10; 若确要接表, 先把该文件挪进含表格名单并更新本守阵)"


def test_drawer_variant_skeleton_single_point():
    """抽屉变体渲染器族三族重复收敛守阵(issue 26-10-20-2231) ——
    ① 三态空帧单点 H.emptyFrame: 核心 HELPERS 在册(has 闸 + loading→err→empty
       优先级 + err 进 title 走 esc)+ 04-12 九件桥变体各 1 处接线(槽类名/空态文案
       逐件对账)+ 内联三态块零残留(「正在加载…」态帧回潮即红); general 三件的裸空态
       (无槽无文案 + lastSig 记账)形状不同, 刻意不收编(接线数钉 0);
    ② peers 判据单点 reg.peers: 五件(FLAG_META/flagTokens/isBad/bucketOf/isLanIp)
       在核心 + TPL_REG 挂载 + 07/08/09 经 const P 消费 + 本地副本零残留;
    ③ dt 值格模板合一: 单一 tpl-aq-dt-peer-cells(类名经 pfx prop 计算, 渲染结果与
       旧逐字同; dt09 密度雷达特化经 occ prop) + table.js 三组件同名不变共享模板且
       pfx/occ 默认值各表自己 + 旧三模板 id 零残留。
    行为等价(空帧三态 DOM/dt 单元格 DOM)由 e2e 盯(drawer-peers-columns /
    drawer-peers-variant-tables / dt-table-* 诸 spec)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    cells = open(os.path.join(shared, "tpl", "xtpl-cells.html"), encoding="utf-8").read()
    table = open(os.path.join(shared, "table.js"), encoding="utf-8").read()

    # ---- ① 三态空帧单点(04-12 九件桥变体的 27 块 → 9 处接线 + 1 个 helper) ----
    m = re.search(r"emptyFrame: function \(host, o\) \{.*?\n    \},", core, re.S)
    assert m, "drawer_templates.js 缺三态空帧单点 emptyFrame(改名或挪走了? 同步本守阵)"
    body = m.group(0)
    assert "o.has" in body and "i-hourglass" in body and "i-warn" in body, \
        "emptyFrame 形状漂了(应 = has 闸 + 沙漏加载态 + 警告错态 + esc 转义)"
    assert "esc(o.err)" in body, "emptyFrame 的 err 进 title 必须走 esc(与 dtHtml 插值同口径)"
    BRIDGE = {
        "04-trackers-status-cards-tall": ("dt04-empty", "暂无 tracker"),
        "05-trackers-health-groups-low": ("dt05-empty", "暂无 tracker"),
        "06-trackers-table-collapsed": ("dt06-empty", "暂无 tracker"),
        "07-peers-dashboard-tall": ("dt07-empty", "暂无已连接用户"),
        "08-peers-groups-low": ("dt08-empty", "暂无已连接用户"),
        "09-peers-density-collapsed": ("dt09-empty", "暂无已连接用户"),
        "10-content-tree-detail-tall": ("dt10-load", "无文件列表"),
        "11-content-treegrid-batch-low": ("dt11-load", "无文件列表"),
        "12-content-space-treemap-collapsed": ("dt12-load", "无文件列表"),
    }
    for name, (cls, empty_text) in BRIDGE.items():
        v = open(os.path.join(shared, "drawer_tpl", name + ".js"), encoding="utf-8").read()
        assert v.count("H.emptyFrame(") == 1, f"{name} emptyFrame 接线数漂了(应 1 处)"
        assert f'cls: "{cls}"' in v, f"{name} 空帧槽类名应为 {cls}(以同步后代码为准)"
        assert f'emptyText: "{empty_text}"' in v, f"{name} 空态文案应为 {empty_text}"
        assert "正在加载…" not in v, f"{name} 又出现内联加载态帧(应走 H.emptyFrame 单点)"
    # general 三件裸空态形状不同(无槽无文案 + lastSig 复位记账), 刻意不收编
    for name in ("01-general-hero-tall", "02-general-cards-low", "03-general-dossier-collapsed"):
        v = open(os.path.join(shared, "drawer_tpl", name + ".js"), encoding="utf-8").read()
        assert "H.emptyFrame(" not in v, f"{name} 不应接 emptyFrame(裸空态是变体记账, 形状不同)"

    # ---- ② peers 判据单点(07/08/09 各手抄一份 → 核心层 reg.peers) ----
    for token in (
        "FLAG_META: {",
        "flagTokens: function (p)",
        "isBad: function (p)",
        "bucketOf: function (p)",
        "isLanIp: function (ip)",
    ):
        assert token in core, f"drawer_templates.js 缺 peers 判据单点 {token}"
    assert "peers: PEERS," in core, "TPL_REG 未挂 peers 命名空间(变体经 reg.peers 消费)"
    for name in ("07-peers-dashboard-tall", "08-peers-groups-low", "09-peers-density-collapsed"):
        v = open(os.path.join(shared, "drawer_tpl", name + ".js"), encoding="utf-8").read()
        assert "const P = reg.peers;" in v, f"{name} 未接 peers 判据单点(const P = reg.peers)"
        for gone in (
            "function isBad(",
            "function bucketOf(",
            "function isLanIp(",
            "function flagTokens(",
            "const FLAG_META = {",
        ):
            assert gone not in v, f"{name} 又出现 peers 判据本地副本 {gone}(应走 reg.peers 单点)"

    # ---- ③ dt 值格模板合一(dt07≡dt08 逐字同, dt09 三处特化 → pfx/occ 两 prop) ----
    assert 'id="tpl-aq-dt-peer-cells"' in cells, "xtpl-cells.html 缺 peers 共用值格模板"
    for gone in ('id="tpl-aq-dt07-cells"', 'id="tpl-aq-dt08-cells"', 'id="tpl-aq-dt09-cells"'):
        assert gone not in cells, f"xtpl-cells.html 残留旧分片 {gone}(已合一, 回潮 = 双模板副本)"
    tpl_blk = re.search(r'<script type="text/x-template" id="tpl-aq-dt-peer-cells">(.*?)</script>', cells,
                        re.S).group(1)
    assert ":class=\"pfx + '-addr'\"" in tpl_blk, "共用模板类名应经 pfx prop 计算(渲染结果与旧逐字同)"
    assert "occ ? '-occ' : '-spd u'" in tpl_blk, "upspeed 分支缺 occ 密度雷达特化"
    assert "[pfx + '-dn'" in tpl_blk, "dlspeed 分支缺 occ 平铺特化"
    for comp, pfx, occ in (
        ("DT07", "dt07", "false"),
        ("DT08", "dt08", "false"),
        ("DT09", "dt09", "true"),
    ):
        m = re.search(r"window.AQ_%s_CELLS_COMPONENT = \{(.*?)\n\};" % comp, table, re.S)
        assert m, f"table.js 缺 AQ_{comp}_CELLS_COMPONENT(组件名不变, 动态名接线依赖它)"
        blk = m.group(1)
        assert 'template: "#tpl-aq-dt-peer-cells"' in blk, f"{comp} 未共享共用值格模板"
        assert f'pfx: {{ type: String, default: "{pfx}" }}' in blk, f"{comp} 的 pfx 默认值应为 {pfx}"
        assert f"occ: {{ type: Boolean, default: {occ} }}" in blk, f"{comp} 的 occ 默认值应为 {occ}"


def test_drawer_prio_text_single_point():
    """文件优先级码 -> 中文文案表单点守阵(issue 26-10-29-1340) ——
    ① 字面表全仓唯一(硬约束): shared/ 递归扫五键表字面仅核心层 PRIO_TEXT 1 处;
    ② 取文函数带回退参数: prioText 内部查表缺键回落 dash, 与 PRIO_TEXT 一并挂 reg.helpers
       (dur/size 同族「带回退小工具」通道); 表含 legacy 4 档(「高」);
    ③ 五处消费接线: drawer.js 两处(setFilePriority 回执 String(p) 兜底 / drawerFileRows 显示
       「正常」兜底, 方法内经 window.AQB_DRAWER_TPL_REG 取别名, FIT 先例)+ 10/11/12 各经
       H.prioText 消费, 本地 PRIO_LABEL 与字面表零残留;
    ④ node 真跑(无 node 静默跳过): p∈{0,1,6,7} 可达域新旧输出逐字同(旧内联表作对账基准),
       4 档补测 prioText(4, "4") === "高"(旧 setFilePriority 表缺 4 会打「4」, 收敛后绿)。
    行为等价由 e2e 盯(drawer-content-variant-tables)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()

    # ---- ① 字面表全仓唯一 ----
    LITERAL = '{ 0: "不下载", 1: "正常", 4: "高", 6: "高", 7: "最高" }'
    hits = []
    for root, _dirs, files in os.walk(shared):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                text = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, ValueError):
                continue  # vendor 二进制/字体等非源码文件
            if LITERAL in text:
                hits.append(os.path.relpath(p, shared).replace("\\", "/"))
    assert hits == ["drawer_templates.js"], f"优先级文案表字面回潮(应仅核心层 1 处): {hits}"

    # ---- ② 核心层: 全键表 + 带回退取文 ----
    assert f"var PRIO_TEXT = {LITERAL};" in core, \
        "核心层缺 PRIO_TEXT 全键表(缺 legacy 4 档 = setFilePriority 回执打码原文的旧坑回潮)"
    assert "prioText: function (p, dash)" in core, "核心层缺带回退参数的 prioText 取文函数"
    assert "PRIO_TEXT: PRIO_TEXT," in core, "HELPERS 未随表挂出 PRIO_TEXT(消费方取不到表面)"

    # ---- ③ 五处消费接线, 本地副本零残留 ----
    assert "prioText(p, String(p))" in drawer_js, "drawer.js setFilePriority 回执未接 prioText(兜底码原文)"
    assert 'window.AQB_DRAWER_TPL_REG.helpers.prioText(p, "正常")' in drawer_js, \
        "drawer.js drawerFileRows 显示未接 prioText(兜底「正常」)"
    assert LITERAL not in drawer_js, "drawer.js 又出现本地字面表(应走 reg.helpers 单点)"
    for name in ("10-content-tree-detail-tall", "11-content-treegrid-batch-low", "12-content-space-treemap-collapsed"):
        v = open(os.path.join(shared, "drawer_tpl", name + ".js"), encoding="utf-8").read()
        assert "H.prioText(" in v, f"{name} 未接 H.prioText 单点"
        assert "PRIO_LABEL" not in v, f"{name} 残留本地 PRIO_LABEL(应走 reg.helpers::prioText)"

    # ---- ④ node 真跑: 可达域等价 + 4 档补测 ----
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _PRIO_TEXT_NODE_PROBE,
         os.path.join(shared, "drawer_templates.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"prioText node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"prioText 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


_PRIO_TEXT_NODE_PROBE = r"""
const fs = require("fs");
global.window = {};
/* localStorage 桩; document 保持 undefined —— dtInjectCss 有守卫跳过注入 */
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
eval(fs.readFileSync(process.argv[1], "utf8"));
const H = window.AQB_DRAWER_TPL_REG.helpers;
/* 旧五处内联表(等价性对账基准, 只活在测试里): 显示侧 ?? "正常" / 回执侧 || String(p) */
const OLD = { 0: "不下载", 1: "正常", 4: "高", 6: "高", 7: "最高" };
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
for (const p of [0, 1, 6, 7]) {
  ok(`显示侧 p=${p} 与旧表逐字同(兜底正常)`, H.prioText(p, "正常") === (OLD[p] ?? "正常"));
  ok(`回执侧 p=${p} 与旧表逐字同(兜底码原文)`, H.prioText(p, String(p)) === (OLD[p] || String(p)));
}
ok("4 档(legacy 高)补测: prioText(4, '4') === 高", H.prioText(4, "4") === "高");
ok("PRIO_TEXT 五键全在册", [0, 1, 4, 6, 7].every((p) => H.PRIO_TEXT[p] !== undefined));
console.log(JSON.stringify({ total: checks.length, ok: checks.filter((c) => c[1]).length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_drawer_tracker_bucket_text_single_point():
    """tracker 五桶文案表单点守阵(issue 26-10-29-1343) ——
    ① 桶文案/桶集单源: 核心 TRACKERS(TRACKER_BUCKETS 全列 text/sev/order/cnt 逐字钉住 +
       TRACKER_BUCKET_ORDER)挂 reg.trackers(reg.peers 同类判据命名空间);
    ② 桶文案词唯一: 「未联系」(只在桶文案出现的词)在 drawer_tpl/ 零命中、核心层表内恰 1 处
       (drawer.js 的 drawerTrackerStatus 状态码表是另一张表, 不在本项范围);
    ③ 04/05/06 各经 reg.trackers 消费(TK 别名), 本地 BUCKET/GROUPS 字面与 04 PILLS 的
       text/tip 桶名字面零残留(cls/tip/色族/各版式桶序是呈现语义, 留各自文件);
    ④ node 真跑(无 node 静默跳过): text/sev/cnt 与旧表逐字对账, sev 权值 0/1/2/3/9 不动
       (04/06 排序权值等价), order 与 TRACKER_BUCKET_ORDER 下标同源。
    行为等价由 e2e 盯(drawer-trackers-variant-tables / drawer-trackers-reannounce)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()

    # ---- ① 核心层单源表(全列逐字钉住) ----
    for row in (
        'err: { text: "未工作", sev: 0, order: 0, cnt: "正在拖后腿 · 优先处理" }',
        'warn: { text: "未联系", sev: 1, order: 1, cnt: "可用但需关注" }',
        'upd: { text: "更新中", sev: 2, order: 2, cnt: "汇报进行时" }',
        'ok: { text: "工作", sev: 3, order: 3, cnt: "按 tier 升序" }',
        'off: { text: "禁用", sev: 9, order: 4, cnt: "qB 合成 / 已禁用" }',
    ):
        assert row in core, f"TRACKER_BUCKETS 行漂了: {row}"
    assert 'TRACKER_BUCKET_ORDER: ["err", "warn", "upd", "ok", "off"]' in core, \
        "TRACKER_BUCKET_ORDER 漂了(05 分区顺序与 04/06 sev 升序同源)"
    assert "trackers: TRACKERS," in core, "TPL_REG 未挂 trackers 命名空间(变体经 reg.trackers 消费)"

    # ---- ② 桶文案词唯一 ----
    tpl_dir = os.path.join(shared, "drawer_tpl")
    for fn in os.listdir(tpl_dir):
        if not fn.endswith(".js"):
            continue
        v = open(os.path.join(tpl_dir, fn), encoding="utf-8").read()
        assert "未联系" not in v, f"drawer_tpl/{fn} 出现桶文案字面「未联系」(应读 reg.trackers 单点)"
    assert core.count("未联系") == 1, "核心层桶文案字面应恰 1 处(TRACKER_BUCKETS 表内)"

    # ---- ③ 三变体接线, 本地副本零残留 ----
    for name, gone in (
        ("04-trackers-status-cards-tall", ('const BUCKET = {', 'text: "工作"', 'tip: "工作 = 绿"')),
        ("05-trackers-health-groups-low", ("const GROUPS = [", 'cnt: "正在拖后腿 · 优先处理"')),
        ("06-trackers-table-collapsed", ("const BUCKET = {", )),
    ):
        v = open(os.path.join(tpl_dir, name + ".js"), encoding="utf-8").read()
        assert "reg.trackers" in v, f"{name} 未接 trackers 判据单点(reg.trackers)"
        for g in gone:
            assert g not in v, f"{name} 又出现桶表本地副本 {g!r}(应读 reg.trackers 单点)"

    # ---- ④ node 真跑: text/sev/cnt/order 与旧表逐字对账 ----
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _TRACKER_BUCKETS_NODE_PROBE,
         os.path.join(shared, "drawer_templates.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"tracker buckets node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"tracker buckets 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


_TRACKER_BUCKETS_NODE_PROBE = r"""
const fs = require("fs");
global.window = {};
/* localStorage 桩; document 保持 undefined —— dtInjectCss 有守卫跳过注入 */
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
eval(fs.readFileSync(process.argv[1], "utf8"));
const TK = window.AQB_DRAWER_TPL_REG.trackers;
/* 旧五处文案/权值对账基准(只活在测试里): 04/06 BUCKET{text,sev} + 05 GROUPS{cnt} */
const OLD_TEXT_SEV = {
  err: { text: "未工作", sev: 0 }, warn: { text: "未联系", sev: 1 }, upd: { text: "更新中", sev: 2 },
  ok: { text: "工作", sev: 3 }, off: { text: "禁用", sev: 9 },
};
const OLD_CNT = { err: "正在拖后腿 · 优先处理", warn: "可用但需关注", upd: "汇报进行时",
  ok: "按 tier 升序", off: "qB 合成 / 已禁用" };
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
for (const k of Object.keys(OLD_TEXT_SEV)) {
  const b = TK.TRACKER_BUCKETS[k];
  ok(`${k} text 与旧表逐字同`, !!b && b.text === OLD_TEXT_SEV[k].text);
  ok(`${k} sev 权值不动(04/06 排序等价)`, !!b && b.sev === OLD_TEXT_SEV[k].sev);
  ok(`${k} cnt 副标题话术与旧表逐字同`, !!b && b.cnt === OLD_CNT[k]);
}
ok("处理序数组与 05 分区顺序逐字同",
  JSON.stringify(TK.TRACKER_BUCKET_ORDER) === JSON.stringify(["err", "warn", "upd", "ok", "off"]));
ok("order 与 TRACKER_BUCKET_ORDER 下标同源",
  TK.TRACKER_BUCKET_ORDER.every((k, i) => TK.TRACKER_BUCKETS[k].order === i));
console.log(JSON.stringify({ total: checks.length, ok: checks.filter((c) => c[1]).length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_drawer_content_file_tree_single_point():
    """content 目录树构建/聚合单点守阵(issue 26-10-29-1343) ——
    ① 核心单点: CONTENT(buildFileTree/findNode)在核心层并挂 TPL_REG.content
       (reg.peers/reg.trackers 同类「按页签判据命名空间」; 不落 helpers —— 那里只住
       跨页签骨架机制, 树构建只有 content 组消费);
    ② 单点唯一性: drawer_tpl/ 全体 function buildTree/aggregate/newDir/findNode 零命中;
    ③ 接线与零残留: 10/12 各 const FT = reg.content; 一处 + FT.buildFileTree/FT.findNode
       调用数逐件对账(10: 4/2 —— rowsFn/render/onClick 优先级段/onClick 折叠全收;
       12: 1/1) + 旧模型字面零残留(minAv/布尔对/裸 availability 叶子字段; 11 的 derive
       扁平表是第三算法不在本项, 自有 stats 模型不查)+ 11 头注声明口径以 buildFileTree 为准;
    ④ node 语义电池(等价性主证据, 无 node 静默跳过): 新旧三实现(新单点/旧 10/旧 12)
       对 fixture 组逐节点归一化 JSON 全等 —— 归一只做两件已裁定的事: 旧 10 的布尔对
       (hasAv/minAv)换算成标量 av、旧 12 的 null 值归一成无值(单一哨兵 undefined 的
       语义收敛, 见核心 CONTENT 头注); dirs 统一按聚合公式现算(旧 12 无该字段)。
    行为等价由 e2e 盯(drawer-content-variant-tables / drawer-content-dt11-sticky)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    tpl_dir = os.path.join(shared, "drawer_tpl")

    # ---- ① 核心单点(模型取两份并集 + 标量 av 单一哨兵) ----
    assert "buildFileTree: function (files)" in core, "核心层缺 content 目录树单点 buildFileTree"
    assert "findNode: function (n, path)" in core, "核心层缺 findNode(应随树单点一并导出)"
    assert "content: CONTENT," in core, "TPL_REG 未挂 content 命名空间(变体经 reg.content 消费)"
    for shape in (
        'files: 0, dirs: 0, prog: 100, av: undefined',
        "av: (f.availability === undefined || f.availability === null) ? undefined"
    ):
        assert shape in core, f"核心树节点模型形状漂了: {shape}(dirs 恒有 / null 同为无值)"

    # ---- ② 单点唯一性: 变体层四函数定义零命中 ----
    for fn in sorted(os.listdir(tpl_dir)):
        if not fn.endswith(".js"):
            continue
        v = open(os.path.join(tpl_dir, fn), encoding="utf-8").read()
        for gone in ("function buildTree", "function aggregate", "function newDir", "function findNode"):
            assert gone not in v, f"drawer_tpl/{fn} 又出现树构建本地副本 {gone!r}(应走 reg.content 单点)"

    # ---- ③ 接线逐件对账 + 旧模型零残留 ----
    for name, ft_calls, fn_calls in (
        ("10-content-tree-detail-tall", 4, 2),
        ("12-content-space-treemap-collapsed", 1, 1),
    ):
        v = open(os.path.join(tpl_dir, name + ".js"), encoding="utf-8").read()
        assert v.count("const FT = reg.content;") == 1, f"{name} 未接 reg.content 单点(const FT 别名应恰 1 处)"
        assert v.count("FT.buildFileTree(") == ft_calls, f"{name} buildFileTree 接线数漂了(应 {ft_calls} 处)"
        assert v.count("FT.findNode(") == fn_calls, f"{name} findNode 接线数漂了(应 {fn_calls} 处)"
        assert "minAv" not in v, f"{name} 残留旧最小可用性哨兵字段 minAv(应读统一标量 n.av)"
        assert "n.hasAv" not in v and "hasAv: " not in v, f"{name} 残留旧布尔对可用性表示(应读 n.av !== undefined)"
        assert "availability: f.availability" not in v and "av: f.availability" not in v, \
            f"{name} 叶子节点残留裸 availability 直传(null 会穿进聚合, 应走单点的无值归一)"
    v11 = open(os.path.join(tpl_dir, "11-content-treegrid-batch-low.js"), encoding="utf-8").read()
    assert "buildFileTree" in v11, "11 头注缺「口径以核心 buildFileTree 为准」声明(第三算法未并入, 口径须对齐)"

    # ---- ④ node 语义电池: 新旧三实现逐节点 JSON 全等 ----
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _CONTENT_TREE_NODE_PROBE,
         os.path.join(shared, "drawer_templates.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"content tree node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"content tree 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


_CONTENT_TREE_NODE_PROBE = r"""
const fs = require("fs");
global.window = {};
/* localStorage 桩; document 保持 undefined —— dtInjectCss 有守卫跳过注入 */
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
eval(fs.readFileSync(process.argv[1], "utf8"));
const FT = window.AQB_DRAWER_TPL_REG.content;

/* ---- 旧实现对账基准(只活在测试里; 逐字取自收编前的 10/12 本地四件, 仅函数改名) ---- */
const num = (v) => Number(v) || 0;
/* 旧 10: dirs 计数 + hasAv/minAv 布尔对(Infinity 哨兵) */
function old10NewDir(name, parentPath, parentDepth) {
  return {
    dir: true, name, path: parentPath ? parentPath + "/" + name : name,
    depth: parentDepth + 1, children: [], size: 0, done: 0, miss: 0,
    files: 0, dirs: 0, prog: 100, minAv: Infinity, hasAv: false,
  };
}
function old10Build(files) {
  const root = old10NewDir("", "", -1);
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    const parts = String(f.name || "").split("/").filter(Boolean);
    let node = root;
    for (let d = 0; d < parts.length - 1; d++) {
      let next = null;
      for (const c of node.children) {
        if (c.dir && c.name === parts[d]) { next = c; break; }
      }
      if (!next) {
        next = old10NewDir(parts[d], node.path, node.depth);
        node.children.push(next);
      }
      node = next;
    }
    const last = parts[parts.length - 1] || "文件 " + i;
    node.children.push({
      dir: false, name: last, path: node.path ? node.path + "/" + last : last,
      depth: node.depth + 1, index: i, size: num(f.size),
      prog: Math.round(num(f.progress) * 1000) / 10,
      prio: num(f.priority), availability: f.availability,
    });
  }
  old10Agg(root);
  return root;
}
function old10Agg(n) {
  if (!n.dir) {
    n.done = n.size * (n.prog / 100);
    n.miss = Math.max(0, n.size - n.done);
    n.files = 1;
    if (n.availability !== undefined && n.availability !== null) {
      n.hasAv = true;
      n.minAv = num(n.availability);
    }
    return;
  }
  for (const c of n.children) {
    old10Agg(c);
    n.size += c.size; n.done += c.done; n.miss += c.miss; n.files += c.files;
    if (c.dir) n.dirs += c.dirs + 1;
    if (c.hasAv && c.minAv < n.minAv) n.minAv = c.minAv;
    n.hasAv = n.hasAv || c.hasAv;
  }
  n.prog = n.size > 0 ? n.done / n.size * 100 : 100;
}
/* 旧 12: 标量 av(undefined = 无值; null 会当值聚合 —— 已知漂移) */
function old12NewDir(name, parentPath, parentDepth) {
  return {
    dir: true, name, path: parentPath ? parentPath + "/" + name : name,
    depth: parentDepth + 1, children: [], size: 0, done: 0, miss: 0,
    files: 0, prog: 100, av: undefined,
  };
}
function old12Build(files) {
  const root = old12NewDir("", "", -1);
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    const parts = String(f.name || "").split("/").filter(Boolean);
    let node = root;
    for (let d = 0; d < parts.length - 1; d++) {
      let next = null;
      for (const c of node.children) {
        if (c.dir && c.name === parts[d]) { next = c; break; }
      }
      if (!next) {
        next = old12NewDir(parts[d], node.path, node.depth);
        node.children.push(next);
      }
      node = next;
    }
    const last = parts[parts.length - 1] || "文件 " + i;
    node.children.push({
      dir: false, name: last, path: node.path ? node.path + "/" + last : last,
      depth: node.depth + 1, index: i, size: num(f.size),
      prog: Math.round(num(f.progress) * 1000) / 10,
      prio: num(f.priority), av: f.availability,
    });
  }
  old12Agg(root);
  return root;
}
function old12Agg(n) {
  if (!n.dir) {
    n.done = n.size * (n.prog / 100);
    n.miss = Math.max(0, n.size - n.done);
    n.files = 1;
    return;
  }
  let avSet = false, minAv = Infinity;
  for (const c of n.children) {
    old12Agg(c);
    n.size += c.size; n.done += c.done; n.miss += c.miss; n.files += c.files;
    if (c.av !== undefined) {
      if (!avSet || c.av < minAv) minAv = c.av;
      avSet = true;
    }
  }
  n.prog = n.size > 0 ? n.done / n.size * 100 : 100;
  if (avSet) n.av = minAv;
}

/* ---- 归一化: 三份产出折到同一「统一节点模型」视图再比 JSON ----
 * 折算只做两件已裁定的事: 旧 10 布尔对 -> 标量 av; 旧 12 null -> 无值(单一哨兵)。
 * dirs 三边统一按聚合公式现算(旧 12 本无该字段, 收编后为并集模型恒有)。
 * 等价域口径: null 在入参侧归一(旧实现跑 null->undefined 后的同一 fixture) —— 旧 10 对
 * null 的原生判定与此同值; 旧 12 会把 null 当值且**毒化整条祖先链**(min 被 null 占位),
 * 属裁定消除的缺陷, 2) 段留取证。另注: 旧 10 的叶子无 hasAv 键, 目录聚合 false||undefined
 * 会产出 undefined(仍为假值语义), 归一后不受影响。 */
const dirsOf = (n) => (!n.dir ? 0 : n.children.reduce((s, c) => s + (c.dir ? dirsOf(c) + 1 : 0), 0));
const norm = (n, avOf) => {
  const o = {};
  for (const k of Object.keys(n).sort()) {
    if (k === "av" || k === "minAv" || k === "hasAv" || k === "availability" || k === "dirs") continue;
    const v = n[k];
    o[k] = v && typeof v === "object" ? (Array.isArray(v) ? v.map((x) => norm(x, avOf)) : norm(v, avOf)) : v;
  }
  o.av = avOf(n);
  if (n.dir) o.dirs = dirsOf(n);
  return o;
};
const avNew = (n) => n.av;
const avOld10 = (n) => (n.hasAv ? n.minAv : undefined);
const avOld12 = (n) => n.av; /* 入参已无 null, 直传 */

/* ---- fixture 组(issue 验证手段②: 嵌套两层/根单文件/size 缺失/null·负数·小数/空目录段/空名) ---- */
const FIXTURES = [
  { name: "嵌套两层+根单文件+零/负/小数可用性", files: [
    { name: "tv/Show/S01E01.mkv", size: 1073741824, progress: 0.5, priority: 1, availability: 2.5 },
    { name: "tv/Show/S01E02.mkv", size: 1073741824, progress: 1, priority: 6, availability: 1 },
    { name: "tv/Extras/notes.txt", size: 1024, progress: 0, priority: 0, availability: 0 },
    { name: "readme.txt", size: 128, progress: 1, priority: 1, availability: -0.5 },
  ] },
  { name: "size/availability 缺失+null 可用性", files: [
    { name: "a/b/c.bin", progress: 0.25, priority: 1 },
    { name: "a/top.iso", size: 2048, progress: 0.75, priority: 6, availability: null },
    { name: "loose.mp4", size: 512, progress: 1, priority: 0, availability: 3 },
  ] },
  { name: "空目录段+前导空段+空名回退", files: [
    { name: "x//y.mp4", size: 10, progress: 0.5, priority: 1, availability: 1.25 },
    { name: "/root.bin", size: 20, progress: 0, priority: 6, availability: 0.5 },
    { name: "", size: 30, progress: 0.5, priority: 1, availability: 2 },
  ] },
  { name: "无 availability 键+目录最低值跨层传播", files: [
    { name: "d1/f.bin", size: 100, progress: 0.5, priority: 1 },
    { name: "d2/d3/g.bin", size: 200, progress: 0, priority: 0, availability: 0.125 },
    { name: "d2/h.bin", size: 300, progress: 1, priority: 1, availability: 9.5 },
  ] },
];

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

/* 1) 逐 fixture 逐节点: 新 vs 旧 10(归一) vs 旧 12(归一) JSON 全等
 * 旧实现跑 null->undefined 归一后的同一 fixture(等价域 = 无 null 数据, 见上方归一注) */
const noNull = (files) => files.map((f) => (f.availability === null ? { ...f, availability: undefined } : f));
for (const fx of FIXTURES) {
  const tNew = FT.buildFileTree(fx.files);
  const t10 = old10Build(noNull(fx.files));
  const t12 = old12Build(noNull(fx.files));
  const walk = (a, b, c, path) => {
    const ja = JSON.stringify(norm(a, avNew));
    const jb = JSON.stringify(norm(b, avOld10));
    const jc = JSON.stringify(norm(c, avOld12));
    ok(`[${fx.name}] node ${path || "(根)"} 新 vs 旧10 归一全等`, ja === jb);
    ok(`[${fx.name}] node ${path || "(根)"} 新 vs 旧12 归一全等`, ja === jc);
    if (a.dir) for (let i = 0; i < a.children.length; i++) {
      walk(a.children[i], b.children[i], c.children[i], path + "/" + a.children[i].name);
    }
  };
  walk(tNew, t10, t12, "");
}

/* 2) 语义收敛取证(null 漂移是裁定消除的, 不是碰巧不等; 这里跑**原始** fixture) */
const f2 = FIXTURES[1].files;
const dirA = (t) => t.children.find((c) => c.dir && c.name === "a");
ok("null 可用性: 统一后目录 = 无值(旧 10 口径)", dirA(FT.buildFileTree(f2)).av === undefined);
ok("null 可用性: 旧 12 确实把 null 当值并毒化根(dirA.av === null)", dirA(old12Build(f2)).av === null);
ok("null 可用性: 旧 12 毒化到根(根 av === null, 尽管 loose.mp4 有 3)", old12Build(f2).av === null);
ok("null 可用性: 旧 10 同为无值(dirA.hasAv 假值 —— 叶子无该键的既有怪癖)",
  !dirA(old10Build(f2)).hasAv);
ok("旧 10 Infinity 哨兵不再进统一模型(无可用性目录 av=undefined)",
  FT.buildFileTree([{ name: "d/f.bin", size: 1, progress: 1, priority: 1 }]).children[0].av === undefined);

/* 3) 统一模型键集纯净: 新树全节点无旧分叉字段; dir 有 dirs/children, 叶子有 index/prio */
{
  let bad = null;
  const scan = (n, path) => {
    if ("minAv" in n || "hasAv" in n || "availability" in n) bad = path + " 残留旧分叉字段";
    else if (n.dir && !("dirs" in n) || !n.dir && "dirs" in n) bad = path + " dirs 字段位形不对";
    else if (!n.dir && !("index" in n && "prio" in n)) bad = path + " 叶子缺 index/prio";
    for (const c of n.children || []) scan(c, path + "/" + (c.name || "?"));
  };
  for (const fx of FIXTURES) scan(FT.buildFileTree(fx.files), "");
  ok("统一模型键集纯净(无 minAv/hasAv/availability, dirs 位形, 叶子 index/prio)", bad === null);
}

/* 4) findNode 四态 */
{
  const t = FT.buildFileTree(FIXTURES[0].files);
  const hitDir = FT.findNode(t, "tv/Show");
  ok("findNode 命中目录", !!hitDir && hitDir.dir === true && hitDir.files === 2);
  const hitLeaf = FT.findNode(t, "readme.txt");
  ok("findNode 命中叶子", !!hitLeaf && hitLeaf.dir === false && hitLeaf.index === 3);
  ok("findNode 空 path 不命中(根不可选中)", FT.findNode(t, "") === null);
  ok("findNode 未命中返 null", FT.findNode(t, "no/such") === null);
}

console.log(JSON.stringify({ total: checks.length, ok: checks.filter((c) => c[1]).length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_drawer_tpl_row_memoization_and_cheap_sig():
    """千级文件列表止血守阵(计划 26-11-02-0351 W1) ——
    ① sig 廉价指纹: 10/11 两变体 JSON.stringify(files) 零回潮(引用相等 O(1) 快路 + 引用变
       O(F) 数值滚动指纹, filesSig 单点各一份);
    ② 行对象按 path 记忆化: 两变体各持模块级 rowMem(path -> 输入快照 + 上轮行对象), 行装配
       (rowOf/dirRowOf/fileRowOf)命中即复用 —— 桥 keyed diff 对引用相等行跳渲; _cls 挂行
       对象, 勾选/折叠/选中态必须进快照失效面(漏键 = 染色停旧值);
    ③ dt11 O(D×F) 装配冗余消除: stats.ck 随 derive 单遍前缀归并落账, dirRowOf 不再
       subtreeFiles 每目录全表 filter、chkStateOf 不再双算(全文件只剩定义 + toggleSet +
       master 三处);
    ④ CSS: dt_table.css content-visibility:auto + contain-intrinsic-size 覆盖 dt10/dt11
       行容器(定值 = 各自行高 29px/27px, 屏外行渲染税立收);
    ⑤ node 电池(无 node 静默跳过): 同一份数据二次派生全行引用相等 / 改一文件 progress 仅
       该行+祖先目录链为新对象 / 选中与勾选翻转只重装配该行+祖先链且 _cls 正确翻转 / 折叠
       目录行重装配且子树不再 emit / dt11 目录聚合(大小/进度/文件数/最低可用性)与核心
       buildFileTree 口径逐项相等。行为等价 e2e 盯 dt-live-update。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl_dir = os.path.join(shared, "drawer_tpl")
    v10 = open(os.path.join(tpl_dir, "10-content-tree-detail-tall.js"), encoding="utf-8").read()
    v11 = open(os.path.join(tpl_dir, "11-content-treegrid-batch-low.js"), encoding="utf-8").read()

    # ---- ① sig 廉价指纹(计划验收机检点: JSON.stringify(files) 零回潮) ----
    for name, v in (("10-content-tree-detail-tall", v10), ("11-content-treegrid-batch-low", v11)):
        assert "JSON.stringify(files)" not in v, f"{name}: sig 仍全量序列化 files(W1 廉价指纹回潮)"
        assert "function filesSig(files)" in v and "filesSig(files)" in v, \
            f"{name}: sig 未走 filesSig 廉价指纹单点"
        # ---- ② 记忆化: 模块级缓存 + 命中快照(命名避开 T/R/H 单点) ----
        assert "const rowMem = new Map()" in v, f"{name}: 缺模块级行记忆化缓存 rowMem"
        assert "rowMem.clear()" in v, f"{name}: 记忆化缓存无清空路径(换种子/卸载)"

    # ---- ③ dt11 O(D×F) 消除: subtreeFiles 只剩定义 + toggleRow/onChange 两交互点;
    #      chkStateOf 只剩定义 + toggleSet + master 三处; 勾选计数随 derive 落 stats.ck ----
    assert v11.count("subtreeFiles(") == 3, \
        f"11: subtreeFiles 调用面漂了(应 3 处 = 定义 + toggleRow + onChange; dirRowOf 全表 filter 应已退役, 实测 {v11.count('subtreeFiles(')})"
    assert v11.count("chkStateOf(") == 3, \
        f"11: chkStateOf 调用面漂了(应 3 处 = 定义 + toggleSet + master; dirRowOf 双算应已退役, 实测 {v11.count('chkStateOf(')})"
    assert "ck: 0" in v11 and "if (isCk) s.ck++;" in v11, "11: 勾选计数未随 derive 单遍落 stats.ck"

    # ---- ④ CSS: content-visibility 规则在位(行高定值与各面行高对齐) ----
    css = open(os.path.join(shared, "dt_table.css"), encoding="utf-8").read()
    assert "content-visibility: auto" in css, "dt_table.css 缺 content-visibility:auto(W1 屏外行渲染税)"
    for lst, h in ((".dt10-list .group-row", "29px"), (".dt11-list .group-row", "27px")):
        assert f".drawer-body {lst}" in css, f"dt_table.css 缺 {lst} 选择器"
        assert f"contain-intrinsic-size: auto {h}" in css, f"dt_table.css 缺 {lst} 的 contain-intrinsic-size 定值 {h}"

    # ---- ⑤ node 电池: 两变体 rowsFn 真跑(记忆化引用相等 / 失效面 / 聚合口径) ----
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [
            node, "-e", _NODE_ROW_MEMO_PROBE,
            os.path.join(shared, "drawer_templates.js"),
            os.path.join(tpl_dir, "10-content-tree-detail-tall.js"),
            os.path.join(tpl_dir, "11-content-treegrid-batch-low.js")
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"行记忆化 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"行记忆化电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


_NODE_ROW_MEMO_PROBE = r"""
const fs = require("fs");
global.window = {};
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
global.Vue = { reactive: (o) => o };
eval(fs.readFileSync(process.argv[1], "utf8")); /* 核心层 */
/* 变体是 IIFE, ui(Vue.reactive 视图态)是模块私有 —— 探针在 "use strict"; 后插一行把 ui
 * 递出来(只活在测试里, 产品代码零改动)。 */
function loadVariant(p) {
  const src = fs.readFileSync(p, "utf8");
  eval(src.replace('"use strict";', '"use strict"; window.__PROBE_UI = function () { return ui; };'));
  const ui = window.__PROBE_UI();
  window.__PROBE_UI = null;
  return ui;
}
const ui10 = loadVariant(process.argv[2]); /* 10 树+详情 */
const ui11 = loadVariant(process.argv[3]); /* 11 树表批量 */
const reg = window.AQB_DRAWER_TPL_REG;
const e10 = reg.get("content", "10");
const e11 = reg.get("content", "11");

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const fmtSize = (v) => "SZ" + (Number(v) || 0);
/* dt11 的 derive 吃 ctx.drawerFileRows()(drawer.js 树扁平化: 目录行 + 文件行带 index/progress%)
 * —— 探针按其消费字段复刻同构桩(dir/name/path/depth/index/progress) */
const drawerFileRows = (files) => {
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
    node.files.push(Object.assign({}, f, { index: fi }));
  }
  const rows = [];
  const walk = (node, name, depth) => {
    if (name !== null) rows.push({ depth, dir: true, name, path: node.path });
    for (const [dn, d] of node.dirs) walk(d, dn, name === null ? 0 : depth + 1);
    for (const f of node.files) {
      const last = String(f.name || "").split("/").pop();
      rows.push({
        depth: name === null ? 0 : depth + 1, dir: false,
        name: last,
        path: node.path ? node.path + "/" + last : last,
        index: f.index,
        progress: Math.round((f.progress || 0) * 100),
      });
    }
  };
  walk(root, null, -1);
  return rows;
};
/* ctx 模拟生产形态: ctx 恒定(根 vm), 静默补拉 = ctx.drawer.files 引用换新 */
const mkCtx = (files) => ({ drawer: { files, hash: "h1" }, fmtSize, drawerFileRows() { return drawerFileRows(this.drawer.files); } });
const byKey = (rows) => new Map(rows.map((r) => [r.k, r]));
/* 失效面: 按 k 对齐比引用(行序可能因折叠变化, 不能按下标) */
const changedKeys = (before, after) => {
  const mb = byKey(before);
  return after.filter((x) => mb.get(x.k) !== x).map((x) => x.k).sort();
};
const reuseCount = (before, after) => {
  const mb = byKey(before);
  return after.filter((x) => mb.get(x.k) === x).length;
};

const F1 = [
  { name: "a/one.bin", size: 100, progress: 1, priority: 1, availability: 1 },
  { name: "a/two.bin", size: 200, progress: 0.5, priority: 6, availability: 0.5 },
  { name: "b/c/three.bin", size: 300, progress: 0, priority: 0, availability: 0 },
  { name: "b/c/four.bin", size: 400, progress: 1, priority: 1 },
  { name: "b/five.bin", size: 500, progress: 1, priority: 1, availability: 2 },
  { name: "top.bin", size: 50, progress: 1, priority: 7, availability: 1 },
];
const reuse = {};

/* ================= dt10: 树 + 详情 ================= */
{
  const ctx = mkCtx(F1);
  const r1 = e10.rowsFn(ctx);
  const r2 = e10.rowsFn(ctx);
  ok("dt10 二次派生全行引用相等(" + r1.length + " 行)",
    r1.length === r2.length && r1.every((x, i) => x === r2[i]));
  reuse.dt10_same = reuseCount(r1, r2) + "/" + r1.length;

  /* 改一个文件进度: 仅该文件行 + 祖先目录链新对象, 其余引用相等 */
  const F2 = F1.map((f, i) => (i === 1 ? Object.assign({}, f, { progress: 0.9 }) : f));
  ctx.drawer.files = F2; /* 模拟静默补拉(引用换新) */
  const r3 = e10.rowsFn(ctx);
  ok("dt10 改 a/two.bin 进度: 行数不变", r3.length === r1.length);
  ok("dt10 改 a/two.bin 进度: 仅该行+祖先链 a 新对象, 实测翻 " + JSON.stringify(changedKeys(r1, r3)),
    JSON.stringify(changedKeys(r1, r3)) === JSON.stringify(["a", "a/two.bin"]));
  reuse.dt10_1file = reuseCount(r1, r3) + "/" + r3.length;
  ok("dt10 改进度后 a/two 进度随新值", byKey(r3).get("a/two.bin").progTxt === "90.0");

  /* 选中翻转: 该行重装配且 _cls 正确翻转(sel 挂 _cls, 行对象必须换新) */
  ui10.selPath = "top.bin";
  const r4 = e10.rowsFn(ctx);
  ok("dt10 选中 top.bin: 仅该行重装配", JSON.stringify(changedKeys(r3, r4)) === JSON.stringify(["top.bin"]));
  ok("dt10 选中行 _cls 翻转", byKey(r4).get("top.bin")._cls === "file sel");
  ui10.selPath = "";
  const r5 = e10.rowsFn(ctx);
  ok("dt10 取消选中: _cls 复位", byKey(r5).get("top.bin")._cls === "file");

  /* 折叠目录: 目录行重装配(folded 翻转)且子树不再 emit */
  ui10.folded.add("b");
  const r6 = e10.rowsFn(ctx);
  ok("dt10 折叠 b: 目录行重装配", JSON.stringify(changedKeys(r5, r6)) === JSON.stringify(["b"]));
  ok("dt10 折叠 b: 行对象 folded=true 且子树不 emit",
    byKey(r6).get("b").folded === true && !byKey(r6).has("b/c") && r6.length === 5);
  ui10.folded.delete("b");
}

/* ================= dt11: 树表批量 ================= */
{
  const ctx = mkCtx(F1);
  const q1 = e11.rowsFn(ctx);
  const q2 = e11.rowsFn(ctx);
  ok("dt11 二次派生全行引用相等(" + q1.length + " 行)",
    q1.length === q2.length && q1.every((x, i) => x === q2[i]));
  reuse.dt11_same = reuseCount(q1, q2) + "/" + q1.length;

  /* 改一个文件进度: 该文件行 + 祖先目录链(b 与 b/c)新对象 */
  const G2 = F1.map((f, i) => (i === 2 ? Object.assign({}, f, { progress: 0.25 }) : f));
  ctx.drawer.files = G2;
  const q3 = e11.rowsFn(ctx);
  ok("dt11 改 b/c/three.bin 进度: 仅该行+祖先链 b/b/c 新对象, 实测翻 " + JSON.stringify(changedKeys(q1, q3)),
    JSON.stringify(changedKeys(q1, q3)) === JSON.stringify(["b", "b/c", "b/c/three.bin"]));
  reuse.dt11_1file = reuseCount(q1, q3) + "/" + q3.length;

  /* 勾选翻转: 该文件行 + 祖先链重装配, ckState/_cls 正确(三态框染色挂 _cls) */
  ui11.checked.add("a/one.bin");
  const q4 = e11.rowsFn(ctx);
  ok("dt11 勾选 a/one.bin: 仅该行+祖先 a 重装配, 实测翻 " + JSON.stringify(changedKeys(q3, q4)),
    JSON.stringify(changedKeys(q3, q4)) === JSON.stringify(["a", "a/one.bin"]));
  ok("dt11 文件行 ckState=2 且 _cls 翻转 is-chk",
    byKey(q4).get("a/one.bin").ckState === 2 && byKey(q4).get("a/one.bin")._cls === "file is-chk");
  ok("dt11 目录行部分勾选 ckState=1 且 _cls 无 is-chk",
    byKey(q4).get("a").ckState === 1 && byKey(q4).get("a")._cls === "dir");
  ui11.checked.add("a/two.bin");
  const q5 = e11.rowsFn(ctx);
  ok("dt11 全勾目录 ckState=2 且 _cls 翻转",
    byKey(q5).get("a").ckState === 2 && byKey(q5).get("a")._cls === "dir is-chk");
  ui11.checked.delete("a/one.bin");
  ui11.checked.delete("a/two.bin");

  /* 聚合口径对表: dt11 目录行显示值与核心 buildFileTree 逐项相等(大小/进度/文件数/最低可用性) */
  const tree = reg.content.buildFileTree(G2);
  const nodeBy = new Map();
  (function scan(n) { nodeBy.set(n.path, n); for (const c of (n.children || [])) scan(c); })(tree);
  const q6 = e11.rowsFn(ctx);
  let why = "";
  for (const r of q6) {
    if (!r.dir) continue;
    const n = nodeBy.get(r.path);
    if (!n) { why = r.path + " 树中无此目录"; break; }
    const avTxt = n.av !== undefined ? n.av.toFixed(2) : "—";
    if (r.sizeTxt !== "SZ" + n.size) { why = r.path + " 大小不等(" + r.sizeTxt + " vs SZ" + n.size + ")"; break; }
    if (r.progTxt !== n.prog.toFixed(1)) { why = r.path + " 进度不等(" + r.progTxt + " vs " + n.prog.toFixed(1) + ")"; break; }
    if (r.meta !== n.files + " 文件") { why = r.path + " 文件数不等(" + r.meta + ")"; break; }
    if (r.avTxt !== avTxt) { why = r.path + " 最低可用性不等(" + r.avTxt + " vs " + avTxt + ")"; break; }
  }
  ok("dt11 目录聚合与核心 buildFileTree 口径逐项相等(大小/进度/文件数/最低可用性)" + (why ? " — " + why : ""),
    why === "");
}

console.log(JSON.stringify({ total: checks.length, ok: checks.filter((c) => c[1]).length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]), reuse }));
if (checks.some((c) => !c[1])) process.exit(1);
"""


def test_drawer_general_hr_state_line_parity():
    """抽屉 general 三变体 HR 结论行对齐守阵(issue 26-10-29-1341) ——
    同一颗 hr_triggered 种子的「删除安全档位结论 · 依据」行(hr_safety_text/hr_state_text
    + hr_reason)三变体都必须消费 hr_state: 01/02 从旧版就有, 03 手抄时字段集停在旧版
    整段漏了 hr_state —— 后端 views.py 详情载荷字段齐全, hr.js::hrStateLine 注释成文
    「详情抽屉要显示这行」, 选 03 就看不到「能否删」是用户可见缺失。守阵 = 三件源码各含
    if (d.hr_state) 闸(空值路径被闸拦住, hr_state 为空不多出空行), 缺件即红。"""
    tpl = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    for name in ("01-general-hero-tall", "02-general-cards-low", "03-general-dossier-collapsed"):
        v = open(os.path.join(tpl, name + ".js"), encoding="utf-8").read()
        assert "if (d.hr_state)" in v, (
            f"{name} 缺 hr_state 结论行(同颗 hr_triggered 种子比其它版式少一行"
            "「能否删」结论与依据; 参照 01-general-hero-tall.js hrStrip 同措辞分支补齐)"
        )


# node 单测探针(issue 26-10-30-0622): 提取 drawer_store.js 的 _drawerMergeSupply 方法体真跑,
# 用桩 this 验证 seq bump 的条件化 —— 两源都被数据/门挡住时不得前进代际(否则在飞取数被打成
# stale, 其 finally 刻意不清 loading 门, 门成孤儿 ⇒ 合并对双列停「正在加载…」)。
# 无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_MERGE_SUPPLY_PROBE = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
const checks = [];
const push = (name, ok) => checks.push([name, !!ok]);
const m = src.match(/_drawerMergeSupply\(\) \{([\s\S]*?)\n    \},/);
if (!m) {
  push("drawer_store.js 找到 _drawerMergeSupply(改名或挪走了? 同步本探针)", false);
} else {
  const store = {};
  eval("store._drawerMergeSupply = function () {" + m[1] + "}");
  const mkInst = (over) => Object.assign({
    dtSplitOn: true,
    _drawerLoadSeq: 5,
    fetched: [],
    polled: 0,
    drawer: { open: true, tab: "general", hash: "HA", detail: null, loading: false,
              files: [], filesLoading: false, trackers: [], trackersLoading: false, peersLoading: false },
    _dtPairOf(tab) { return (tab === "general" || tab === "content") ? "gc"
      : (tab === "trackers" || tab === "peers") ? "tp" : null; },
    _fetchDrawerFiles(s, seq) { this.fetched.push(["files", seq]); },
    _fetchDrawerDetail() { this.fetched.push(["detail"]); },
    _fetchDrawerTrackers(s, seq) { this.fetched.push(["trackers", seq]); },
    _fetchDrawerPeers(s, seq) { this.fetched.push(["peers", seq]); },
    _startDrawerPoll() { this.polled += 1; },
    drawerPeerRows() { return []; },
  }, over);
  // ① 双源都有数据(「已有数据不重发」): 不 bump 代际、零补发
  let vm = mkInst({ drawer: { open: true, tab: "general", hash: "HA", detail: { name: "x" },
                              loading: false, files: [{ index: 0 }], filesLoading: false } });
  store._drawerMergeSupply.call(vm);
  push("双源都有数据: 代际不前进", vm._drawerLoadSeq === 5);
  push("双源都有数据: 零补发", vm.fetched.length === 0);
  // ② 双源都在途(loading 门持有, issue 本体场景): 不 bump —— 在飞取数(旧 seq)不被打成 stale
  vm = mkInst({ drawer: { open: true, tab: "general", hash: "HA", detail: null,
                          loading: true, files: [], filesLoading: true } });
  store._drawerMergeSupply.call(vm);
  push("双源都在途: 代际不前进(在飞取数不被孤儿化)", vm._drawerLoadSeq === 5);
  push("双源都在途: 零补发", vm.fetched.length === 0);
  // ③ 单源缺口: 代际恰好前进一次, 只补缺的那源且带新代际
  vm = mkInst({ drawer: { open: true, tab: "general", hash: "HA", detail: { name: "x" },
                          loading: false, files: [], filesLoading: false } });
  store._drawerMergeSupply.call(vm);
  push("单源缺口: 代际恰好前进一次", vm._drawerLoadSeq === 6);
  push("单源缺口: 只补 files 且带新代际", vm.fetched.length === 1 && vm.fetched[0][0] === "files" && vm.fetched[0][1] === 6);
  // ④ 双源都缺: 代际只 bump 一次, 两源同代际(与旧口径一致)
  vm = mkInst();
  store._drawerMergeSupply.call(vm);
  push("双源都缺: 代际恰好前进一次", vm._drawerLoadSeq === 6);
  push("双源都缺: detail+files 同代际补发", vm.fetched.map((f) => f[0]).join(",") === "files,detail" && vm.fetched[0][1] === 6);
  // ⑤ tp 对双源在途: 不 bump、零补发, 但页签轮询照常起(轮询与代际无关, 不得因早退丢起轮)
  vm = mkInst({ drawer: { open: true, tab: "trackers", hash: "HA", trackers: [],
                          trackersLoading: true, peersLoading: false }, peerRows: [1, 2] });
  vm.drawerPeerRows = function () { return this.peerRows; };
  store._drawerMergeSupply.call(vm);
  push("tp 双源在途: 代际不前进", vm._drawerLoadSeq === 5);
  push("tp 双源在途: 零补发且轮询照常起", vm.fetched.length === 0 && vm.polled === 1);
  // ⑥ tp 对有缺口: 代际恰好前进一次, 两源同代际 + 轮询照常起
  vm = mkInst({ drawer: { open: true, tab: "peers", hash: "HA", trackers: [],
                          trackersLoading: false, peersLoading: false } });
  store._drawerMergeSupply.call(vm);
  push("tp 有缺口: 代际恰好前进一次且两源同代际", vm._drawerLoadSeq === 6 && vm.fetched.length === 2 && vm.fetched.every((f) => f[1] === 6));
  push("tp 有缺口: 轮询照常起", vm.polled === 1);
  // ⑦ 合并关: 代际与取数都不动(既有早退守卫仍在)
  vm = mkInst({ dtSplitOn: false });
  store._drawerMergeSupply.call(vm);
  push("合并关: 代际与取数都不动", vm._drawerLoadSeq === 5 && vm.fetched.length === 0);
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_drawer_merge_supply_seq_bump_conditional():
    """合并补给 seq bump 条件化守阵(issue 26-10-30-0622, 第二次全项目 code review 批F2 F2-03)

    故障链: _drawerMergeSupply 的 seq bump 无条件执行 —— 即使两个源的取数都因「有数据/门在途」
    被跳过, 代际照样前进, 把**正在飞行**的页签取数(seq N)整体打成 stale: 响应在
    _fetchDrawerSource 被 stale 分支丢弃, 而 finally 的 stale 分支刻意**不清 loading 门**(注释
    前提是「新在途请求持有它」, 在补给方没补发的场景不成立), 门成孤儿且无重发路径 ⇒ gc 对
    (general+files, 页签无轮询)双列停「正在加载…」, 无 _dtNotify 到来则变体不重渲, 直到用户
    切页签/换种子/重开抽屉。修法 = bump 移进「确有缺口要补」分支(两 fetch 都被门挡住不 bump)。
    行为面 node 电池真跑(无 node 静默跳过): 双源有数据 / 双源在途 / 单源缺口 / 双源都缺 /
    tp 对同款五型 + 合并关早退。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_MERGE_SUPPLY_PROBE,
         os.path.join(shared, "drawer_store.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, f"合并补给 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"合并补给电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
