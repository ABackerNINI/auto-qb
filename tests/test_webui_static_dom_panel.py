"""test_webui_static_dom_panel 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

## 测试计划(每个测试函数一条)
- test_frontend_qb_traffic_chart_wiring: qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07) —— enabled=false 三挂点入口不渲染不请求(全局入口按钮 v-if="qbHistEntryOn" / 抽屉流量页签与组右键菜单项 v-if="qbTrafficOn", 门在 flags.qb_traffic_enabled, /api/webui/flags 下发 fail-closed)+ uPlot 双系列 spanGaps=false 断线不连线 + 桶序->_qbPointsToData 栅格重建与 null 语义 node 真跑(全 null 回落/前导 null 锚推算/interval 非法防御 + S3b 月行真值落点/空槽内插/anchor.xs) + 轮询下界常量 1500(A4, S3b §05.5)+ 三挂点作用域表与低频轮询口径(interval_s 夹取 + document.hidden 跳过 + 关闭/切走 clearInterval)+ 静默续拉(loading 空态只在「尚无落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误) + 同宿主 setData 原地快路 + 换肤先销毁再重建 + 错误态由成功落袋清除, 2026-10-04 修轮询期闪烁 / 2026-10-05 补齐空态与错误态闪烁)+ FX-29 软切换落定登记(_qbLoad 落袋 _drawerDone("traffic") 与 _drawerWaitSources 成对, 2026-10-04 修流量页签单击换行遮罩挂死)+ 三主题登记链(tpl/vendor/mixin/manifest)+ escBusy 与 Esc 退栈链同步(含退栈顺序: 历史弹层遮罩 130 先于抽屉 80, 2026-10-06 两图同开报障)+ 建图后宿主 ResizeObserver 自适应与销毁断开(便签 26-10-04-0134)+ 缺口三态文案与空态钉住(P4, plan 26-10-04-0721 §05: 0 桶状态行/缺口合并文案/图例 hint 两处/单种空态收窄为从未传输 + node 三段混排回归)
- test_frontend_qb_traffic_window_persist_and_single_source: 流量图「视图选择」持久化 + 窗口档位单点(2026-10-05) —— QB_WINDOW_NAMES 十三档与后端 traffic_qb.WINDOW_NAMES 逐字一致, 为展示(模板 v-for 走 qbWindowNames)/前后切换(qbCycleWindow)/持久化校验(qbInitialWindow)三处唯一来源(任一处硬编码即与后端 400 校验漂移); 持久化粒度 = 全局单独(autoqb.ui.qbWinGlobal)/组与种子共用(autoqb.ui.qbWinShared), 键按 scope 单点分派, 初值只认合法档位且坏值回落默认, 换窗即落盘并吞写入异常; 初值函数在 qb_traffic_chart.js 且三份 tpl-manifest 里排在 state.js 之前(否则 state data() 调它未定义 = 启动白屏)
- test_drawer_tpl_registry_wiring: 详情面板模板核心层接线守阵(plan 26-10-06-0838 S1) —— 三份 manifest 成对含 drawer_templates.js 且装载序 drawer.js < 核心 < state.js(state data() 调 initialDrawerTpl 依赖注册表); 变体文件 (id, tab) 唯一且 tab 合法且三 manifest 成对登记(S1 变体数为 0, 断言按当前集合写); 变体 label 展示名禁档位后缀(Q4, 报告 26-10-07-0542 —— 档位是物理形态非信息组织, 三档语义全收进本变体, 写进下拉名冗余误导); 核心含 AQB_DRAWER_TPL_REG/dtHtml+dtRaw/autoqb.ui.drawerTpl/data-dt CSS 注入单点; 一行式钩子四类齐全(调用点随 W1 数据层抽离落 drawer_store.js: _loadDrawerTab 尾 _dtSync / 四 fetcher _dtNotify; closeDrawer _dtUnmountAll 与 collapse 通知仍在 drawer.js)+ 列表三 fetcher 通知在 loading 清掉之后(2026-10-07 用户页空列表停"正在加载…"报障)+ drawerTab 补强二; drawer.html 宿主 x6/合并列 data-dt-tab x4/摘要条 x2(2026-10-10 头部 .dt-select 退役, 模板选择迁右键)+ 经典包裹层 v-show 接 drawerTplSel; state.js 显式建字段 + app.js initialDrawerTpl + app.mixin; dt* 成员全仓无重名(mixin 覆盖静默故障, 核心书写形态不在 _scan_mixin_wiring 扫描面内, 此处补钉)
- test_drawer_tpl_variant_width_discipline: 详情面板变体宽度纪律守阵(Q1, 报告 26-10-07-0542) —— 核心注入 CSS 含四页签宿主(general/trackers/peers/content)的 max-width 1400px 居中收口(15 变体单点共享, 变体文件零复刻; traffic 双宿主排除 —— 图本体/工具条归经典链恒满宽, 13/15 KPI 头行限宽会与图缘错位, 14 解读栏自带 288px 固定右栏) + 全部变体与核心注入 CSS 禁 justify-content:space-between(label/value 两端推开病根, 标签在前值紧随; 非 kv 场景确需两端分布须显式改本守阵并注明)
- test_drawer_tpl_variant_field_icons: 详情面板变体字段行图标消费守阵(Q2, 报告 26-10-07-0542) —— general 三变体(01/02/03)字段行必须消费 drawerGeneralSections() 行级 icon 数据(sprite `<use href>` 静态引用)且含经典链 icoTone 同表派生 + .ico-t-* 着色 CSS(经典 .f-row 作用域在变体行不命中, 色表须自带); traffic 三变体(13/14/15)KPI/解读行含 sprite 图标引用; 全变体 #i-* 引用不越三皮肤 sprite 既有 symbol 集合(三皮肤集合两两相等)且不引入外部图标库(<img/iconfont/fontawesome/material-icons)
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
- test_frontend_qb_traffic_drawer_page_guard: 流量图抽屉的页面守卫(2026-10-06 修「qB 全局流量图出现在设置页」) —— drawerVisible 两形态先挡非主内容页且状态位不随切页翻(回页连数据/窗口选择一起回来) + 轮询与建图 active 同源含 page 判据(面板不在 DOM 还拉还画 = 对空气取数) + openDrawerTraffic 先切回主内容页 + state.js drawerVisible watcher 退场销毁图/进场补拉(种子详情支路 !s 的 $nextTick _dtSync 回页变体重挂, 归 test_drawer_seed_reentry_variant_remount)
- test_frontend_drawer_groups_shows_views: 辅种页/追剧页支持种子详情面板守阵(计划 26-10-08-1217) —— 可见性单点 drawerVisible 与打开单点 openTorrentDrawer 一律只挡主内容页(形态/视图分叉收归页面级, 此前辅种/追剧页调用 openTorrentDrawer 静默失效: 右键菜单项早已渲染且 hash 正确却点了没反应)+ 两处成员行(辅种明细/追剧集明细)必须有 @dblclick 打开入口(与种子页同款)+ 键盘光标链 _kbRows 纳入展开的成员行(辅种的组下成员/追剧的集下成员, 兑现原注释「成员行 vNext」—— 不在链上则 ↑↓ 走不到、Alt+1~5 解析不出目标)+ 跟随 _kbFollowDrawer / 5s 轮询 tick / 单种流量图 active 三处守卫一律只挡主内容页(换视图即停会让这两页的页签数据停在打开那一刻)
- test_frontend_drawer_open_switch_no_empty_flash: 详情面板显式换目标不闪空态守阵(2026-10-07 报障「切换种子时用户页闪'暂无已连接用户'」) —— openTorrentDrawer 已开(种子形态)重入分支先于重建副作用(同目标短路零副作用, 与 openDrawerTraffic 同口径 -> 换目标交棒 _switchDrawerTarget 软切换: 保留旧数据 + 160ms 延迟遮罩, 与键盘跟随同链路) + 冷启动重建(面板关着/流量形态换形)初值页签 loading 与空列表同帧置位(trackers/files/peers 三 flag 按 initialTab 落真, 详情在途窗口渲染加载态而非空态, 经典链与变体同免), 任一锚被拆或次序倒置即红
- test_removed_redundant_tooltips_stay_removed: 复述型 tooltip 不得复活守阵(报告 26-10-04-0815 + 详情面板二轮清理) —— 模板已移除的复述型原生 title 文案(statusbar「点击修改」「数据状态」/ topbar 页签「按分组展示」「全部种子一行一条」/ drawer「关闭(Esc)」/ dialogs 族 title="关闭" / settings-detail·xtpl「点击收起」/ columns.js H1 横幅「点击关闭」/ drawer_tpl 二轮: 05 图例五色与条级顺序说明·06 等待响应与仅看异常说明·07-09 求和口径/客户端 Top 复述/qB flags 前缀/会话累计/对端整行复述·10-11 展开折叠全部目录与全选与目录文件数·12 优先级跳过与占比细条·13-15 kpis 容器派生口径与窗口累计复述)不得写回, 悬浮提示一律走 shared/ui_feedback.js 拦截层
- test_recheck_confirm_wired_all_mouse_entries: 重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3) —— commands.js _recheckConfirm 单点(helper 存在 + 文案与 okText 调用形态沿键盘路径原样)+ bulkAct 批量通道 / drawer.js torrentCmd 单选通道各含 recheck 确认分支 + shortcuts.js _kbAct 改调共用 helper 不再内联 confirmDialog 文案 + 共用文案字符串全仓只此一份, 任一接入点被重构摘除即红
- test_skip_check_dialog_precheck_wired: 跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4) —— ui_feedback.js _modalInit 声明 okDisabled/busy/verdict 三字段 + popovers.html 确认钮 :disabled="modal.okDisabled" 绑定 / busy 行 / verdict 行式渲染区(强制钮复用 extraText 第三钮 danger-solid) + drawer.js 两入口(skipCheckTorrent/skipCheckMulti, 后者带可选 targets 供单组入口 skipCheckGroup 复用)均交棒 _skipCheckDialog 且不再自带 _openModal + _skipCheckDialog 进框即禁用(busy + 固定警示区)并发预检(_skipPrecheck), 任一被重构摘除即红
- test_skip_check_dialog_verdict_render: 跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4) —— _skipPrecheck 状态机分支(预检失败降级=启用普通确认且无强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认钮文案「跳检 N 个可跳检的」+ 强制钮「强制跳检全部」/ force-only=确认保持禁用 / 全 ok=只启用确认)+ ok 子集派生(cls==="ok" 过滤)+ 确认路径送 ok 子集而强制路径送全量+force(_skipExec 单发 body 仅 force 时带 force 键, 批量确认只走 hashes 通道)+ 降级文案「后端闸门仍会在执行时拦截」+ _skipVerdictRows 计数行与分组上限截断(slice(0,5)+等 X 个), 任一分支被改写即红
- test_modal_identity_stamp_landing_guard: 模态身份戳落袋守卫单点(F1-01, issue 26-10-06-0028) —— ui_feedback.js _openModal 每框发自增 mid + _modalIsCurrent 单点(visible + mid 双比对) + drawer.js _skipCheckDialog 把 this.modal.mid 交棒 _skipPrecheck 且落袋守卫为 seq + 身份戳双条件(取消跳检框后开无关 modal, 只有身份戳拦得住迟到回执)
- test_frontend_ctx_menu_multi_select_targets_selection: 多选右键菜单守阵 —— 四个 open*Menu 必须写 menu.multi、三套 UI 的行菜单必须消费注册表 ctxItems(ctxMenuKind()) 且段内无逐项直写(批量支走 ctxAct/ctxDelete)、ctxAct/ctxDelete 必须复用 bulkAct/bulkDelete
- test_frontend_ctx_menu_group_actions_parity: 单组右键菜单与多选批量菜单项集一致守阵(2026-10-09 用户报「单组右键菜单缺选项」)—— 模板只按支名消费注册表(ctxItems(ctxMenuKind()) 单点)、单组支必含六个组级入口(重新校验/跳检/限速/移动/标签分类/导出, 与批量支同项集)、跳检项吃 flags.skip_check_menu 门控、六入口复用多选同一套下游链路(recheckGroup->_actCore / 限速移动跳检->drawer.js 多选对话框 / metaGroup->openMetaDialog / exportGroup->_exportHashes)不为组级另开旁路
- test_frontend_meta_dialog_paired: 标签/分类编辑对话框守阵 —— 三套 UI 成对(metaOpen 对话框 + 批量菜单/单种子菜单两处入口, 批量控制条退役后模板层不再直接调 openMetaDialog(null))、shared 逻辑接线(openMetaDialog 锁定目标 + metaToggleTag 走 bulk 链路 + ctxMeta 先收菜单)、.meta-dialog/.opt-pill 三套 CSS 成对定义
- test_frontend_dialog_shell_single_point: 对话框外壳单点守阵(issue 26-10-20-2231, R23-A-02·A-03·A-08 收敛) —— 三段式外壳(标题头/动作栏/遮罩手势对/关闭钮)只许在组件模板 dialog-shell.html 一处(剥注释后字面量清点), 调用点一律经 <aq-modal>(9 处调用覆盖 10 个对话框开态, :open/:close/:close-args/mask-class/icon-class/width-class/body-class 接线逐点清点) + 无遮罩异形 speed-pop 走 <aq-modal-head>; 管理对话框双胞胎合并为单份模板 + mgrDef 数据表(state.js computed 两态字段/文案/动作全表驱动, dialogs-mgr/popovers 零 mgrOpen 直判残留, dialogs.js mgrSubmitNew 分派) + modal-details 两套并一(state.js::modalDetailRows: verdict 在前 copy=false / details 在后 copy=true, 复制钮边界 String(d.value ?? '') 修 value===0 不出钮)
- test_frontend_rename_dialog_width_wiring: 重命名对话框宽档接线守阵(2026-10-19 用户报「弹窗太小」)—— 字段值 = 完整种子显示名(真实名称 routinely 80~120 字符), 骑通用 .modal 基档 520(为确认/提示一句话设计)时输入框仅 474px, 真浏览器实测 97 字符长名裁掉 223px(桩名 43 字符恰好不裁, 故冒烟从未暴露); 修法 = _openModal 增 cls 附加类选项(空 = 既有对话框零变化)+ 重命名走 rename-dialog 类 + 三皮肤 .modal.rename-dialog 宽档(--modal-w-add 860, 与设定位置/添加种子同档)。钉 _modalInit cls 字段 / popovers.html 根类绑定并入 modal.cls / editRename 传类 / 三皮肤宽档规则成对; 行为面由 e2e/rename-dialog-fit.spec.mjs 真浏览器钉
- test_frontend_add_torrent_drag_drop_wiring: DND-01 全局拖拽添加种子接线守阵(静态) —— window 级 drag 四事件 add/remove 对称、drop handler 必 preventDefault(否则浏览器直接打开文件)、接管判据只认 Files/text-uri-list(不误拦页面内拖文本)、双 UI 落点遮罩成对 + app.js addDragOver 状态
- test_frontend_add_torrent_partial_receipt_wiring: 添加种子「部分受理关窗」回执分流守阵(2026-10-18 用户报障「部分种子添加失败(已存在)时添加窗口不消失」) —— submitAddTorrent 三态分流(r.status === "warn" 分支在, 只判 r.ok 的二态写法回潮即红)+ warn 分支关窗且 warn 类 toast 带详情(后端文案带成功/失败计数)+ ok 分支保持关窗 + error(全拒)分支不得关窗(文件/链接原样没进 qB, 留窗才能改完重提; 部分成功与全部失败混为一谈是本案病根, 两个方向都钉)。行为面由 e2e/add-partial-receipt.spec.mjs 真浏览器钉
- test_frontend_add_combo_blur_close_and_fit: 添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障) —— 三输入框 @focusout 收层 + 收层必须 40ms 合帧守卫(label 转发回焦同步收 = 闪烁) + 三开层方法撤销挂起收层 + 开层 watcher 量「输入行→滚动容器可见底沿」净空限高(滚动条留在窗口内) + 候选异步到位重限 + 三浮层互斥双向(closeAddPopsExcept 单点, 三开层各调一次, 26-10-04-0130)
- test_frontend_ctx_menu_refit_by_measured_size: 浮层菜单开层实测钳位守阵(issue 26-10-06-1717) —— _menuFit 按 offsetWidth/offsetHeight 实测算(退回常量估算即红)且以视口为界、每次复位兜底限高; 三个菜单容器 ref(ctxMenu/headMenuEl/filePrioEl)与三个开层 watcher 的 (stateKey, refName) 一一对上且都在 $nextTick 里量; _menuFitRefit 现读 this[stateKey]/this.$refs[refName] 并守 visible
- test_frontend_add_combo_label_clear_mask_and_refit: 添加种子三下拉「第二轮遗留四项」守阵(2026-10-03, label 闪烁 2026-10-04 三修+四轮 JS 守卫) —— 四个 combo 的字段 label 一律 @mousedown.prevent + @click.stop(mousedown 默认动作 blur 武装的 40ms 合帧定时器在人手按住期间先收层、松手转发回焦再重开 = 闪烁; stop 挡 window click 收层; 缺一即回归)+ 收层 JS 单点守卫 _popBlurShouldHold(收层前判「焦点已回本族输入框 / 本族 label 转发 click 仍在途」→ 不收, 模板修饰符缺位(旧页签残留)时独立根除闪烁, add 三字段 + meta 分类全接)+ 三输入框内嵌清空 x(@mousedown.prevent 保焦点 + @click.stop 挡 window 收层, 缺一即「清完下拉没了」)+ 遮罩关窗改「mousedown 记臂位 + mouseup.self 才关」(全仓 11 处, @click.self 会被"拖选文字终点落在遮罩上抬手"误判成点空白关窗, 零残留)+ 过滤词变化重限高(三个输入值 watcher + meta 侧三处)+ meta 分类下拉补失焦收层与 window click 兜底名单 + 清空钮样式三皮肤成对
- test_frontend_combo_hiscroll_never_scrolls_ancestors: 下拉高亮滚动跟随「只滚菜单内部」守阵(2026-10-29 八修, 用户报「选中新路径后再点下拉框, 弹窗里的文字从上往下滑一次」)—— _hiScroll 禁用 scrollIntoView(它把**所有可滚祖先**一起滚: 开层过渡期 .add-dialog-body 的 scrollHeight 比 clientHeight 大 166px, 于是整段文案被滚走再弹回, 实测 body.scrollTop 0→166→83→18→0; 输入框为空时 hi=-1 无 [data-hi="1"] 故只有"选过路径"才看得见); 必须逐级向上以**菜单根为界**手动差值调 scrollTop(box.contains(n) + 到 box 即 break), 剥注释后不得出现 scrollIntoView 字面量(注释里讲禁令不算违规)。行为面由 e2e/move-dialog-fit.spec.mjs 逐帧采样 body.scrollTop 恒 0 + 文案 top 极差 ≤2px 钉
- test_frontend_ctx_submenu_single_entry_and_hover_close: 右键次级菜单守阵 —— 一级只留「更多操作」一个入口(复制族并入, CTX-06)、移出父项后延迟收起(CTX-05)、hover 图标规则必须限定直接子级且压特异性否则整片子面板变灰(CTX-04)
- test_frontend_qb_traffic_yaxis_and_annotation: 流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做) —— _qbYRange/_qbGapRuns 纯函数 node 真跑(自动 = peak*1.05 / 固定上限取 max(cap, peak*1.05) 峰值超上限按峰值显示 / 缺口 = 上下行皆 null 才算); 限速三作用域同源 = qB 全局限速上下行**较大者**(_qbGlobalLimit -> speedLimitBytes); 上限派生单点 _qbYCapOf(limit×1.2 / manual MiB); 三作用域**各自独立**持久化(qbYAxisStoreKey 三键 + qbInitialYAxis 只认合法模式与正数 + persistQbYAxis 吞异常) + 切档落盘重排(qbSetYAxisMode/qbSetYAxisManual -> _qbChartRescale 走 setData 重算 scale 不重建) + 限速变化重排 watcher(mounted 注册, this.drawer 守卫剔除 BaseTransition 假实例); 建图 y range 接纯函数 + draw/drawClear 两钩子画限速虚线/缺口斜纹(共享图面三挂点全生效, uPlot.pxRatio 设备像素换算, 限速线只画落在可视值域内的); 模板 .qb-tools/.qb-seg 控件 + CSS 三皮肤成对 + **控件组唯一挂点**(图下统计栏 .qb-statctl; 2026-10-16 版式改: 流量形态头部不再挂控件, 全局/分组与种子流量图三挂点对齐, 上限读数 qbYAxisCapText/.qb-tools-hint 随 UI 移除退役) + P4 重启缝提示(plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): _qbSeamHint 判据纯函数 node 真跑(重启贴近链末->提示(含首采即链末桶的实测帧形态)/链到右沿或链确已接续或旧后端->null, 边界含尾区起点、右沿与左端前一桶三点) + computed qbCurSeamHint 消费单点 + drawer.html 提示行文案单源带重启时刻锚 + 断线语义不变(spanGaps:false ×2)
- test_frontend_qb_traffic_scope_stale_polarity: 流量图三挂点 stale 谓词极性守阵(2026-10-12 修「种子流量图加载不出来」) —— W2–W6 机械改名把 torrent/group 两处 `!(...)` 写成 `!!(...)`(取反变双重取反), 恰在本图活跃时判「响应已过期」⇒ 数据不落袋 + loading 不复位 + 早退不建图 ⇒ 种子「流量」页签恒停「正在加载流量数据…」且轮询被 loading 卡住不自愈(global 未中招, 故症状只在种子/分组图)。既有静态锚(源码字符串级)对单/双 bang 天然失明, 本守阵补两层: ①node 电池用 `new Function(源码 + "return _QB_SCOPES;")` 取出作用域表, 对三挂点喂「活跃/切走/关闭/换目标/功能关」五类上下文断言 stale 真假 + `active => stale === false` 同向性; ②静态极性兜底钉 `!(...)` 书写形态、`!!(...)` 不得回潮
- test_frontend_add_options_recent_order: 添加种子三候选「最近使用」排序守阵(2026-10-09 用户动议: 保存路径/分类/标签按最近使用排序) —— 口径 = 由种子记录派生(非本机存储): 「最近使用」= 该值下种子 added_on 最大值, 数据面**跨视图自取数** `_addRecencyRows`(与 filters.js::facetRows 同族; 添加入口是顶栏常驻而 /api/state 按 viewMode 裁剪阵列, 直读 this.torrents 会在默认辅种页拿到空表 ⇒ 排序静默退化成字母序, 2026-10-09 e2e 首跑实测) ⇒ 零新存储; node 真跑 _addOrderByRecent(最近使用降序 -> 未用过落末尾并按字母序 -> 表空/表 null/值未命中一律退化纯字母序 + 纯函数不改入参)与 _addNormPath(与后端 infra/utils.path_normalize 同口径; 两侧不同径则 /api/paths 已归一路径与取数行的 qB 原文 save_path 对不上, 时间表恒不命中 ⇒ 静默退化成纯字母序); 静态钉接线(三候选都过 _addOrderByRecent 单点 + pick 不得再内联 .sort + _addRecencyMaps 经 _addRecencyRows 现算且三键齐全 + 路径键过 _addNormPath + _addRecencyRows 按 viewMode 分支且三来源齐全)
- test_drawer_peers_speed_keys_normalized: 抽屉 peers 速度键名适配守阵(2026-10-10 用户报障「种子详情用户页上下行始终为 0」) —— 真 qB sync/torrentPeers 的对端速度字段是 dl_speed / up_speed(与列表侧 torrents/info 的 dlspeed / upspeed 不同名), 前端全部 peers 消费点(经典表 drawerPeerRows + 变体 07/08/09 的 peerList 直读原始对端对象)统一按 dlspeed / upspeed 取名 ⇒ 落袋单点 _fetchDrawerPeers 必须过 _drawerNormPeers 补键(否则取不到值 → 上下行恒 0); 双形态(dict/数组)同归一; 桩服务 scripts/ui_harness.py 合成对端速度键名也必须与真 qB 同形(否则冒烟「看得见速度」而真机恒 0, 测假)
- test_drawer_tpl_trackers_card_uniform_height: 04「状态卡片栅格」卡片同排等高 + 虚拟合并卡去描述守阵(2026-10-10 用户报障「虚拟条目卡片高度与其它的不一致」) —— 口径(用户拍板「同排等高」)= 栅格 .dt04-grid 走 align-items:stretch(同排卡片自动齐平, 虚拟卡与同排实体卡恒等高) + 虚拟合并卡移除设计稿 footer 长描述只留 head + chips; 静态钉 .dt04-grid 必 stretch 且 align-items:start 不得回潮 + 描述文案(私有 tracker 种子…)不得回潮 + virtualCardHtml 内不得再现 dt04-vnote(实体『未启用』卡的短注仍用该类, 禁连类一起删)+ 卡片必须填满栅格格(width:auto 必配, 2026-10-12 用户报障「真实 tracker 卡与虚拟卡之间/虚拟卡后方有长空隙」根治: 引擎行容器继承三皮肤经典表 width:fit-content, grid 下不参与 stretch ⇒ 卡片收缩到内容宽, 两列卡片间 ~700px 永久空洞 + 卡宽随内容漂移)
- test_frontend_reannounce_inactive_gate_wiring: 非活跃种子禁强制汇报(qB 口径)入口接线守阵(2026-10-10; 2026-10-17 扩段删除链, issue 26-10-17-1703) —— qB 的 Force reannounce 仅在种子活跃时可用(commit aa189a7 关闭 issue #12080: isPaused/isChecking/isQueued 时 setEnabled(false)), 本项目沿用同一判据(暂停/停止·排队·校验中·错误/文件丢失): ①判定单点 decorate.js 的 REANNOUNCE_BLOCKED_STATES 必含 paused*/stopped*/queued*/checking*/error/missingFiles/**moving** 且**读 qB 原始 state**(kind 现 7 档, 排队仍被归进 downloading/seeding ⇒ 单看 kind 判不出排队; moving 虽自成第 7 档, 后端却不在任何 state_enum 谓词集合里 ⇒ 后端同须判 state 串); ②右键菜单 ctx-menus.html 四支(多选/整集/单种子/单组)的强制汇报项都挂 reannounceMenuGate(); ③行为层两道 —— _actCore 的 reannounce 前置闸门(早于乐观补丁/POST) + _kbAct 的 reannounce 分支先于 confirmDialog("先问确定再回不行"是坏体感); ④详情面板 tracker 页签 04/05/06 三个变体的 data-act=report 钮挂 drawerReannounceGate() + 各变体 .is-gated CSS(压过 base :hover, 含 05 失败区 .dt05-fail 的 (0,4,0) 覆盖) + drawer.js torrentCmd 兜底; ⑤投递收敛 —— 闸门(集合级全有全无, 与 qB oneCanForceReannounce 一致)只管「允不允许」, 放行后「发给谁」由 reannouncePlan 单点收敛为活跃子集(混选时 qB 引擎对非活跃目标静默空转, 照集合全量投递会让 tracker 确认层白等 item deadline 后落假「未确认」, 把一次干净的成功报成部分失败), 回执体现跳过数, 空投递必须显式收口(不得落成功分支报「成功 0 个目标」), 且前后端判据表(REANNOUNCE_BLOCKED_STATES)逐项同表; ⑥删除链(唯一漏接入口的修复) —— _deleteFlow 按 reannouncePlan 收敛 + 全非活跃时闸门禁用复选框(popovers.html is-gated 类/标题/点击短路三件 + .opt-pill.is-gated 三套 CSS 成套压过 :hover)+ _reannounceAll 的 skip 桶(非活跃 warn 降级为跳过不挡删除, 推迟中/error 维持不放行)+ 后端 REANNOUNCE_INACTIVE_SKIP 文案含「非活跃」(前端文本判据锚点)。行为语义由同批 node 电池真跑(判定表 + 投递计划 + 删除闸门 + skip 桶分型)。键盘与详情面板是右键之外的两条绕行路径, 任一入口被摘除即红
- test_drawer_list_switch_no_loading_flash_wiring: 抽屉三列表(peers/trackers/files)软切换「不闪」守阵(2026-10-13 用户报障「种子详情用户页切换种子时『暂无已连接用户』闪烁」) —— 真根因(逐帧实测, 探针序列 `E→L→E`): 软切换保留的是**上一个目标的已落袋结果**, 而**空列表(没有对端/没有 tracker)是种子的常态**, 但三列表 fetcher 一律置 loading, 模板门 `loading && 无行` 把这份既有空态顶掉一帧换成「正在加载…」再换回 ⇒ 看起来就是空态在闪。修法 = 换目标窗口(`_drawerSoftSwitch`)内**不置**列表 loading 门(`_drawerListLoadingOn` = `!silent && !this._drawerSoftSwitch`), 保留旧结果直到被新结果取代。!**不得**改成「空响应视为未就绪→延迟渲染/重拉」—— 那会把常态的空推迟(首版固定 1s 重拉被用户否掉:「种子的常态就是没有对端」; 后端对空响应还有 1s 短缓存, 重拉只拿回空包)。本守阵钉静态接线与关键次序(行为回归由 e2e/drawer-switch-no-flash.spec.mjs 逐帧采样: 空态全程在 + 无「正在加载…」+ 无重试请求): ①门抑制单点判据; ②三 fetcher 的 loading 置位都经该单点(直写即回潮); ③标记须在 _loadDrawerTab **之前**置位(三 fetcher 在其内 await 前同步读); ④_stopDrawerPoll **不得**清标记(它在 `_loadDrawerTab→_startDrawerPoll` 途中被调用, 清了等于置前失效); ⑤_drawerSwitchEnd 必须清标记(否则粘住); ⑥旧「延迟重拉」机制(_drawerGraceHold/_DRAWER_GRACE_DELAYS/_drawerPeerCount)不得回潮
- test_dt_table_kernel_single_point: 详情面板表格内核守阵(计划 26-10-13-0811 W1; 用户 2026-10-13 报八项表格症状, 归三个根因簇, 本守阵解簇 A「几何与列被多处各算一遍且零校验」) —— ①三份 manifest 都登记 shared/dt_table.js 且文件在盘上; ②window.DT_TABLE 六口子齐全(layout/assertLayout/checkLabels/registerCell/cellOf/hasArrow); ③几何单一出口: 轨道串/对齐/列键同一个返回值里出来且 gridTemplate 恒等于 tracks.join(" ")(调用方再拼一次就是新事实源, 即红) + 固化宽度覆盖生效; ④L3 列名守卫: 列定义的 label 字段零方向符(扫 app.js 列定义单点 + drawer_tpl 全部变体), 「↑ 占用」不得回潮(密度雷达表头多箭头的出处) + 方向符号只能由排序态单点渲染(表壳 .arrow); ⑤渲染即自查: assertLayout 三处计数(网格轨道/列头格/数据行子格)必须相等, 不相等即报(视觉表现正是「速度列下方异常横带」与「多列内容挤在一起」), 未挂载/未渲染不算不一致(面板没开不得满屏报错); ⑥L2 落点: 单元格渲染器未登记即抛(不许渲染空白)。node 电池真跑 ③⑤⑥(无 node 静默跳过)
- test_frontend_qb_traffic_load_stall_fallback: 流量图轮询「在途悬挂」兜底守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #2, 2026-10-16) —— loading 是单向「请求在途」标志(_qbLoad 入口无条件置 true, 唯一复位路径是它的 finally), 请求悬挂时 finally 不执行 ⇒ tick 守卫把之后每一拍都挡掉, 图表永久停在旧帧且无提示(与 10-12 修的同链另一入口 stale 谓词取反不同)。三层静态锚: ①阈值常量 _QB_LOAD_STALL_MS(=30000, 请求级超时的两倍余量); ②判据单点 _qbLoadStalled 在且 tick 必须经它(合体写法 `document.hidden || this[def.loading]` 不得回潮); ③_qbLoad 置位处写计时起点 _qbLoadAt[scope] 且 finally 不擦(擦会把换目标场景下新请求的起点抹成 0)。行为面 node 电池真跑(无 node 静默跳过): 真 _qbLoad + 永不 settle 的 api 桩 —— 在途未悬挂照旧挡拍 / 悬挂放行且只留一条警告 / 新起点生效故后续照常挡拍 / 图不活跃与页面隐藏照旧跳过 / 判据边界(29s 不判、31s 判、无起点不判)
- test_frontend_api_request_timeout: 前端请求级超时守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #1, 2026-10-16) —— `_request` 旧的裸 `fetch(path, { ...options, headers })` 无超时: 连接静默失效时 await 永不返回, 调用方 finally 整条失效(流量图 loading 卡死⇒轮询守卫把自己挡死; polling.js::refresh 更是永久停表), 界面上也无任何提示。四层静态锚: ①常量单点 AQB_FETCH_TIMEOUT_S/MS(毫秒值由秒值派生, 不手抄两份); ②fetch 必须带 `signal: ctl.signal`(裸 fetch 不得回潮); ③AbortError 必须翻译(超时/取消分型 + timeout 标记); ④`finally` 必须 `clearTimeout(timer)` 且跨文件不变式 `_QB_LOAD_STALL_MS >= AQB_FETCH_TIMEOUT_MS`(兜底不得早于请求级超时)。行为面 node 电池真跑(无 node 静默跳过): 桩 fetch + 手动触发定时器, 六型 —— 悬挂→「请求超时(15s)」+ timeout 标记 + 定时器已清 / 成功值透传且定时器清 / 401 仍走 auth 分支(_logout + auth 标记) / 非 2xx 文案照旧 / 已 abort 的外部 signal → 「请求已取消」不冒充超时 / - test_frontend_raw_fetch_timeout_single_point: 前端裸 fetch 零回潮 + 低层带超时单点守阵(issue 26-10-16-1303-bug-webui-raw-fetch-bypass-no-timeout, 2026-10-16) —— 5 处请求有意或历史地绕开 auth.js::_request(它已有请求级超时), 直接裸 fetch 且无 signal: 启动分片装载 / 免鉴权判定 / 导出下载 / 快捷键密钥读写 x2; 连接静默失效时 await 永不返回 ⇒ 各有收尾动作停在中途(白屏 / 停在“验证中” / 回执停在“进行中” / 密钥面板 loading 不复位)。修法 = 低层单点 shared/fetch_low.js(aqbFetch: AbortController + 15s + AbortError 翻译, **原始 Response** 透传不解析), 四处改调它; boot.js 在清单脚本之前执行(用不了单点), 自带等价内联超时(10s, 阻塞首屏 ⇒ 早失败)。四层静态锚: ①单点常量在且与 auth.js 请求级超时同值(同口径两处实现, 只改一边即红); ②**裸 fetch 零回潮**(全 shared 除 vendor 外, 出现调用点 fetch( 的文件只允许单点自身 / auth.js / boot.js); ③boot.js 内联件齐(常量 10s + AbortController + signal 透传 + clearTimeout + AbortError 翻译); ④四旁路调用点全改调单点 + lifecycle 采纳行的等价格式(字段名与空值占位各一个常量; 回潮成字面成员赋值会让该文件对本仓 agent 只读)。行为面 node 电池真跑(无 node 静默跳过): 单点七型(悬挂→「请求超时(15s)」+ timeout 标记 / 原始 Response 透传不解析 / 非 abort 错误上抛 / 外部取消不冒充超时 / method+headers 透传 / 定时器清理)与 boot.js 白屏悬挂五项(信号在 / 10s 定时器在 / 悬挂→可读失败文案 / 定时器清掉)
- test_frontend_busy_skeleton_single_point: busy+try+反馈+finally 骨架单点守阵(issue 26-10-20-2231) —— dialogs.js 三 helper 在册(_mgrRun 管理对话框写操作 / _panelLoad 面板加载与 tm 槽回执 / _postWaitCmd POST+waitCmd 三态 toast)+ 19 处调用点接线数对账(dialogs 14: mgr 5 + 面板加载 5 + POST 4; config_hub 5: tm 族 4 槽 + 一键导入)+ finally 复位保底住在单点内(漏 finally = 面板永久转圈)+ 裸 busy 置位反向断言(再手抄 = 破单点, 回潮即红)
- test_drawer_variant_skeleton_single_point: 抽屉变体渲染器族三族重复收敛守阵(issue 26-10-20-2231) —— ①三态空帧单点 H.emptyFrame 在核心 HELPERS(has 闸 + loading→err→empty 优先级 + err 进 title 走 esc)且 04-12 九件桥变体各 1 处接线(槽类名/空态文案逐件对账), 内联三态块零残留(「正在加载…」态帧不得回潮; 01/02/03 裸空态形状不同刻意不收编, 接线数钉 0); ②peers 判据单点 reg.peers 五件(FLAG_META/flagTokens/isBad/bucketOf/isLanIp)在核心 + TPL_REG 挂载 + 07/08/09 经 const P 消费, 本地副本零残留(反向断言); ③dt 值格模板合一: 单一 tpl-aq-dt-peer-cells(类名经 pfx prop 计算, 渲染结果与旧逐字同; dt09 密度雷达特化经 occ prop) + table.js 三组件同名不变共享模板且 pfx/occ 默认值各表自己 + 旧三模板 id 零残留(双模板副本回潮即红)
- test_drawer_general_hr_state_line_parity: 抽屉 general 三变体 HR 结论行对齐守阵(issue 26-10-29-1341) —— 同一颗 hr_triggered 种子的「删除安全档位结论 · 依据」行(hr_safety_text/hr_state_text + hr_reason)三变体都必须消费 hr_state: 01/02 从旧版就有, 03 手抄时字段集停在旧版整段漏掉, 后端 views.py 详情载荷字段齐全、hr.js::hrStateLine 注释成文「详情抽屉要显示这行」, 选 03 就看不到「能否删」是用户可见缺失; 守阵 = 三件源码各含 if (d.hr_state) 闸(空值路径被闸拦住, hr_state 为空不多出空行), 缺件即红
- test_overlay_fit_single_point: 浮层「贴边留白 + 视口夹取」几何单点守阵(issue 26-10-20-2231) —— ①单点模块 shared/overlay_fit.js 四入口(EDGE=8 / clampAxis / probeRight / probeLeft / fitInViewport)在三份 tpl-manifest 同点登记且装载序在首个消费方 config_hub.js 之前(漏登记/序错 = 运行时取别名 undefined); ②七消费文件接线数逐文件对账(ui_feedback 7 / menu 5 / config_hub 4 / hr 3 / drawer 2 / columns 3 / dialogs 1, 全部经 FIT 别名); ③手写夹取式零残留(8/12 字面量夹取 / PAD / margin=8 / EDGE=8 回潮即红); ④12px 两处(hubAsk / speed-pop)显式命名传参 + 注释在位; ⑤顶层 const/let 跨文件撞名零容忍(实测事故: 经典脚本顶层 let/const 是全局词法环境, 七文件同写顶层 const FIT 致后六文件 SyntaxError、mixin 静默不注册、整页崩而静态守阵全绿; 跨文件别名只许方法内取或包 IIFE); 行为面 node 电池(四入口七型 + 与旧手写式四种书写网格代数等价), 真实浏览器几何由 e2e/menus.spec.mjs CTX-fit 左右缘盯
- test_frontend_poll_skeleton_single_point: 长驻/有界轮询骨架单点守阵(issue 26-10-20-2231, 2026-10-22) —— 同一份「启停 + 守卫 + 在途悬挂兜底 + 代际守卫」此前写了三份(主轮 setTimeout 链 / 抽屉 setInterval / 流量图 setInterval), 停止条件五处手写, 且**抽屉侧漏了悬挂兜底**(同一类「loading 卡死⇒面板永久冻结」缺陷只修了流量图一边, 本件的实质缺陷面)。收敛后: ①骨架三口子 startPoll/stopPoll/awaitPoll 在 polling.js + 阈值常量 AQB_POLL_STALL_MS(30s = 请求级超时 15s 的两倍余量); ②抽屉/流量两侧只声明差异(ms/guard/stall/mutex/onStall), 裸 setInterval 零残留; ③document.hidden 守卫单点在骨架里, shared/ 内除骨架与 lifecycle 的 visibilitychange 事件响应外不得再有散点; ④三条有界等待(_pollCmd / tmPollSettle / tmPollShutdown)一律经 awaitPoll, 手写 ++pollGen 代际守卫与 setTimeout 递归不得回潮。行为面 node 电池真跑(无 node 静默跳过): chain 在途不排下一拍(不堆叠请求) / 悬挂超阈值补偿一次且重新计时 / 退避曲线与旧 _pollCmd 逐项等价(0,150,300,500,500 与 500,1000,1000) / 拍数上限与截止时间收摊兑现 null / 同名先停后起(旧链兑现 null) / 外部叫停 / fn 抛出即 reject / 页面隐藏恒等守卫
- test_drawer_fetcher_skeleton_single_point
- test_drawer_tpl_data_beat_no_anchor_move
- test_drawer_tpl_default_sel
- test_drawer_tpl_no_table_variants_out_of_scope
- test_drawer_tpl_render_error_fallback_default
- test_frontend_move_dialog_combobox_wiring
- test_frontend_pop_item_a11y_contract: .pop-item 三分类 a11y 契约守阵(issue 26-10-29-1335, R23-A-09) ——
  选择式 combobox(单组件 <aq-combo-input>): 输入框 role=combobox + :aria-expanded + aria-autocomplete=list +
  :aria-controls(仅开层时指面板, 关层面板不在 DOM 防悬空引用) + :aria-activedescendant(带界只指真实候选);
  面板 role=listbox + :id=inputId+'-pop'; 两处 v-for 变体候选行 role=option/:id/:aria-selected 各齐两份;
  候选 id 生成式单点 comboOptId(add_torrent.js 定义恰 1 次, 模板消费恰 3 次), 预置行 aria-hidden 不配 option;
  同族顶栏: 列选择器项 Enter/Space 双键逐字同款 handler(筛选器项为基准锚一并钉), UI 切换项 :aria-current=page
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

# 后端非活跃判据表(投递收敛的"第二道闸"): 与前端 REANNOUNCE_BLOCKED_STATES 逐项同表, 本文件
# 钉住两侧一致 —— 各写一份是刻意的(前端要能在无后端往返时判置灰), 但漂移必须立刻报红。
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


def _tpl_body(tpl_text: str, tpl_id: str) -> str:
    """取出 x-template 片段里某个 `<script type="text/x-template" id="...">` 的模板体。

    无构建链下 `shared/tpl/*.html` 是**裸字符串模板**(见 pitfalls/web-ui/frontend-split.md),
    结构断言只能在源文本上做 —— 本助手提供「拿到片段本体」这一步, 供 _tpl_top_level_tags 判根数。
    """
    m = re.search(r'<script type="text/x-template" id="' + re.escape(tpl_id) + r'">(.*?)</script>', tpl_text, re.S)
    assert m, f"模板片段 {tpl_id} 不在所给文本里(片段改名/换文件? 同步本守阵)"
    return m.group(1)


def _tpl_top_level_tags(body: str):
    """返回模板体里 **depth-0** 的元素 (tag, attrs) 清单 —— 即该片段的根元素, 忽略注释/文本。

    为什么需要它(而不是数类名出现次数): W3(计划 26-10-11-2106)把档位/纵轴控件组收进**多根**
    片段 <aq-qb-ctl>(tpl/drawer-head.html), 其两根 `.qb-tabs` / `.qb-tools` 是**直接子元素**这件事
    被三皮肤 CSS 依赖 —— `.qb-statctl > .qb-tabs` / `.qb-statctl > .qb-tools` 与
    `.hist-summary > .qb-statctl`(atlas prism views.css / console dialogs.css)全是**直接子选择器**。
    一旦有人给片段包一层 wrapper(哪怕只是"顺手加个容器"),
    这些规则全部**静默**不命中: 类名 count 一个不变, 观感却错版。故这里按**结构**判根数 ——
    单个根 = 有人加了 wrapper, 立刻判红。
    """
    import html.parser as _hp  # 局部导入: 仅本助手需要, 不污染模块级命名空间

    class _Roots(_hp.HTMLParser):
        # HTML 空元素(不改变嵌套深度) —— 片段里出现的只有这些是无闭合标签的
        VOID = frozenset(
            [
                "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
                "wbr"
            ]
        )

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth = 0
            self.roots = []

        def handle_starttag(self, tag, attrs):
            if self.depth == 0:
                self.roots.append((tag, dict(attrs)))
            if tag not in self.VOID:
                self.depth += 1

        def handle_startendtag(self, tag, attrs):
            if self.depth == 0:
                self.roots.append((tag, dict(attrs)))

        def handle_endtag(self, tag):
            if tag not in self.VOID and self.depth > 0:
                self.depth -= 1

    parser = _Roots()
    parser.feed(body)
    return parser.roots


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


# node 单测探针(P5a): 加载真实 qb_traffic_chart.js, 对模块级纯函数 _qbPointsToData 跑
# 栅格重建 + null 断线语义电池(plan 26-10-03-0946 §5.1/§5.2: 桶键等距 / null 槽 y=null
# / 全 null 回落 / interval 非法防御)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径)。
_NODE_QB_TRAFFIC_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const P = (t, up, dl) => ({ t, up, dl });
const checks = [];
let pts = [P(1000, 1, 2), P(1030, 3, 4), P(1060, 5, 6)];
let d = _qbPointsToData(pts, 30);
checks.push(["连续段 xs 等距", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["连续段值透传", !!d && d.up.join() === "1,3,5" && d.dl.join() === "2,4,6"]);
pts = [P(1000, 1, 2), null, P(1060, 5, 6)];
d = _qbPointsToData(pts, 30);
checks.push(["null 桶 x 按栅格重建(缺口位置不漂移)", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["null 桶 y=null(spanGaps=false 断线)", !!d && d.up[1] === null && d.dl[1] === null]);
checks.push(["锚取首点", !!d && d.anchor.k === 0 && d.anchor.t0 === 1000]);
pts = [null, P(1030, 3, 4), null, P(1090, 7, 8)];
d = _qbPointsToData(pts, 30);
checks.push(["前导 null 整列重建", !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090]"]);
checks.push(["前导/中断 null y=null", !!d && d.up[0] === null && d.up[2] === null && d.up[3] === 7]);
checks.push(["锚取首个非 null", !!d && d.anchor.k === 1 && d.anchor.t0 === 1030]);
checks.push(["全 null 回落(后端已归一 [])", _qbPointsToData([null, null], 30) === null]);
checks.push(["interval 非法回落", _qbPointsToData([P(1, 1, 1)], 0) === null]);
// P4 回归(plan 26-10-04-0721 §07): 停机/断连 = null 缺口(spanGaps:false 如实断线);
// 空闲 = (0,0) 真实观测点(0 平线, 不是缺口) —— 三段混排(活跃/缺口/空闲/活跃)一次钉住
pts = [P(1000, 5, 6), null, null, P(1090, 0, 0), P(1120, 0, 0), null, P(1180, 2, 3)];
d = _qbPointsToData(pts, 30);
checks.push(["三段混排 xs 等距(缺口位置不漂移)",
  !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090,1120,1150,1180]"]);
checks.push(["停机/断连 null 桶 y=null(如实断线)",
  !!d && d.up[1] === null && d.up[2] === null && d.up[5] === null && d.dl[5] === null]);
checks.push(["空闲段 (0,0) 是观测点不成缺口",
  !!d && d.up[3] === 0 && d.up[4] === 0 && d.dl[3] === 0 && d.dl[4] === 0]);
checks.push(["三段混排活跃值透传", !!d && d.up[0] === 5 && d.up[6] === 2 && d.dl[6] === 3]);
// S3b 月视图(plan 26-10-04-1957 §05.3): month 行按行间隔 28-31 天非等距 —— 非 null 点
// 按真值 t 落点(覆写), null 槽在两真值点间线性内插/窗端外推; anchor.xs 供 tooltip 真值
const jan = 1735689600, feb = 1738368000, mar = 1740787200;  // 2025-01/02/03-01(31d/28d)
pts = [P(jan, 1, 2), P(feb, 3, 4), P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月行真值 x 落点(按行间隔非等距)", !!d && JSON.stringify(d.xs) === JSON.stringify([jan, feb, mar])]);
checks.push(["anchor.xs 悬停真值", !!d && d.anchor.xs[2] === mar && d.anchor.k === 0 && d.anchor.t0 === jan]);
pts = [P(jan, 1, 2), null, P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月视图空槽真值内插", !!d && d.xs[1] === (jan + mar) / 2 && d.up[1] === null]);
checks.push(["月视图值透传", !!d && d.up[0] === 1 && d.dl[2] === 6]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_traffic_chart_wiring():
    """qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07)

    五类"漏一处 = 静默失效 / P5 验收被破坏"的故障形态机械钉住:
    1. enabled=false 三挂点入口不渲染不请求(P5 验收): 全局入口按钮 v-if="qbHistEntryOn" 挂今日
       流量面板内; 抽屉「流量」页签按钮 v-if="qbTrafficOn"; 组右键「qB 口径流量图」菜单项
       (W3 计划 26-10-20-0024 起改注册表单点) gate: "qb_traffic" -> flags.qb_traffic_enabled;
       门单点在 flags.qb_traffic_enabled(/api/webui/flags 下发, fail-closed 默认 false,
       state.js 显式建字段 + lifecycle.loadWebFlags 写入), _qbLoad 里再兜一道 —— 无旗标无入口,
       无入口无触发路径 = 三挂点零请求;
    2. uPlot 双系列断线语义(§5.2): 两 series 显式 spanGaps=false(纯断线, 无最大跨越);
      桶序 -> uPlot 数据的栅格重建 _qbPointsToData 用 node 真跑(null 槽 y=null + x 等距
      不漂移 / 前导 null 锚推算 / 全 null 与 interval 非法回落), 无 node 静默跳过;
      容器尺寸自适应(便签 26-10-04-0134 + 2026-10-04 高度跟随): 建图后宿主挂 ResizeObserver,
      宽/高任一变化 u.setSize 重画(高度取宿主 clientHeight, 随抽屉拖拽调高), _qbChartDestroy
      断开 + 回调自摘/0 尺寸守卫;
    3. 三主题登记链(§07): tpl 分片 + uPlot vendor + 组件 mixin 在三份 index.html 的
      tpl-manifest 同步登记(逐份断言, 三清单一致性另由 test_frontend_template_split_wiring
      钉住), app.mixin 注入 + 抽屉/Esc 退栈/escBusy 名单同步 + _logout 清理;
    4. 挂点形态(2026-10-04 三挂点并入底部详情抽屉): 今日流量面板入口(TM 历史入口旁并列按钮),
      图层/取值 CSS 三套 UI 成对(.qb-* 结构类 + .sb-qb 入口类 + .drawer-body.is-traffic 撑满段;
      tooltip 与图例复用 .hist-* 同源色义);
    5. 三挂点并入抽屉与低频轮询(§07 表): 全局/分组 = drawer.kind === "traffic"(scope 记挂点),
      单种 = drawer.kind === "seed" + drawer.tab === "traffic"(drawer.js _loadDrawerTab 进,
      关抽屉/切页签/换形态由 _stopDrawerPoll + _qbTeardown 统一收); 三挂点建图落点统一
      ref="qbChartHost"、共用同一段正文块(qbTrafficActive -> qbCur*); 组右键菜单项直用
      menu.key 的 encode_group_key 通道(不自行编码); 轮询三挂点统一: 间隔从 meta.interval_s
      夹取([15s,600s] 配置校验界, 30d 窗桶宽 3600s 被夹到上界保续拉语义) + document.hidden 跳过
      (对齐 _startDrawerPoll 先例)+ _qbPollStop 显式 clearInterval(只挂打开期间, 不后台常驻)。
      静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): loading 空态只在
      「本作用域尚无任何落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误), 落袋走
      setData 原地快路(不 destroy+new 清屏), 换肤先销毁再整图重建; 错误态改由下一次成功落袋清除
      (发请求前清 = 续拉把错误文案换成 loading/空态再换回 = 每个轮询周期闪一次)。FX-29 软切换落定登记
      (2026-10-04 修「流量页签单击换行『正在加载…』挂死」): _qbLoad 落袋登记
      _drawerDone("traffic"), 与 _drawerWaitSources 成对, 缺一边遮罩等永不到手的源。
      drawer-dock 落点已自种子视图上提为 app 级分片(dock.html), 入口任意页可达(触发即切回主内容
      页), 面板本体由 drawerVisible 限主内容页 —— 见 test_frontend_qb_traffic_drawer_page_guard。
    6. 缺口三态文案与空态(plan 26-10-04-0721 §05, P4): 悬停 0 桶状态行(空闲段 z 派生 (0,0)
      真实观测点, 与 null 缺口可辨)/ 悬停缺口合并文案「无采样 · 程序未运行或 qB 断连」/
      单种空态收窄为「从未有传输记录」; 三皮肤共用 shared 分片与 mixin(tpl-manifest 登记链见上面
      第 3 点), 文案单点钉住即可。2026-10-08 版式改(用户动议)推翻「图例 hint 两处」旧口径:
      窗口档位/纵轴控件上提流量形态头部标题栏, 图例(上行/下行)并入统计栏, 两处 hint 与独立
      图例行全退场 —— 这里改为钉上提/并入/退场三条新结构口径。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    lifecycle_js = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    dialogs_js = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()  # W1: 数据/行为层
    statusbar = open(os.path.join(shared, "tpl", "statusbar.html"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 头部外壳与流量档位/纵轴控件组自 drawer.html 收进组件模板
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()
    dock_tpl = open(os.path.join(shared, "tpl", "dock.html"), encoding="utf-8").read()
    ctx_menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. enabled 门(fail-closed 单点; 三挂点共用 qbTrafficOn, 全局入口另挂今日流量面板本体)
    # ctx_menu(计划 26-10-20-0024 W2/W3): 行右键菜单布局下发键, 与两个旗标同一通道同一显式建字段口径
    assert 'flags: { skip_check_menu: false, qb_traffic_enabled: false, ctx_menu: null }' in state_js, \
        "state.js flags 默认缺 qb_traffic_enabled: false(fail-closed 初值必须显式建)或 ctx_menu: null"
    assert "qb_traffic_enabled: !!(f && f.qb_traffic_enabled)" in lifecycle_js, \
        "loadWebFlags 必须写回 qb_traffic_enabled(缺了旗标恒 false = 功能永不可见)"
    assert "ctx_menu: (f && f.ctx_menu) || null" in lifecycle_js, \
        "loadWebFlags 必须透传 ctx_menu(漏写 = 布局数据到不了前端, 用户重排静默失效)"
    assert "qb_traffic_enabled: false" in lifecycle_js, "loadWebFlags 失败分支必须保持 fail-closed"
    mo = re.search(r"qbTrafficOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "this.flags.qb_traffic_enabled" in mo.group(1), \
        "qb_traffic_chart.js 缺 qbTrafficOn 功能总门单点(抽屉流量页签/组右键菜单项的 v-if 门)"
    mo = re.search(r"qbHistEntryOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo, "qb_traffic_chart.js 缺 qbHistEntryOn 入口门单点"
    body = mo.group(1)
    assert "this.flags.qb_traffic_enabled" in body and "this.todayTraffic" in body, \
        "入口门必须同时消费 flags.qb_traffic_enabled 与今日流量面板(挂点本体)"
    # 入口按钮: v-if 门 + 面板内并列(TM 历史入口同组)
    assert 'v-if="qbHistEntryOn"' in statusbar and 'class="sb-qb"' in statusbar, \
        "statusbar 缺 qB 入口按钮(v-if 门是 P5 验收的静态锚)"
    today_blk = re.search(r'<template v-if="todayTraffic">(.*?)</template>', statusbar, re.S)
    assert today_blk and 'class="sb-qb"' in today_blk.group(1), \
        "qB 入口必须挂在今日流量面板组内(挂点 = 今日流量面板, plan §07 表)"

    # 2. uPlot 断线语义 + 悬停取值对齐
    assert js.count("spanGaps: false") == 2, "上行/下行两 series 都必须显式 spanGaps=false(§5.2)"
    assert "setCursor" in js and "qbHistHoverIdx" in js, "缺 uPlot setCursor -> 悬停取值通道"
    assert "_qbPointsToData" in js and "function _qbPointsToData" in js, \
        "缺栅格重建纯函数(模块级单例, 供 node 单测)"
    # 容器 resize 自适应(便签 26-10-04-0134): 建图宽度一次取定后画布不重算 —— 宿主必须挂
    # ResizeObserver, 宽度变了 uPlot setSize 重画; _qbChartDestroy 必须断开(不留对旧宿主的观察);
    # 回调要有自摘/0 宽守卫(挂点 DOM 随 v-if 拆除后 RO 报 0 宽, setSize(0) 会把图画没)
    assert "new ResizeObserver(" in js, "qb_traffic_chart.js 缺宿主 ResizeObserver(resize 后画布不重算)"
    assert "u.setSize(" in js, "qb_traffic_chart.js resize 回调缺 uPlot setSize 重画"
    destroy_blk = re.search(r"_qbChartDestroy\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert destroy_blk and "disconnect()" in destroy_blk.group(1), \
        "_qbChartDestroy 必须断开 ResizeObserver(图已销毁还观察旧宿主)"
    assert "host.isConnected" in js and "w > 0" in js, \
        "ResizeObserver 回调缺自摘/0 宽守卫(挂点拆除后 RO 报 0 宽, 不得对旧宿主 setSize)"
    # 有 node 时真跑 null 断线语义电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_TRAFFIC_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"_qbPointsToData node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], f"null 断线语义电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 3. 三主题登记链 + 接线(2026-10-04: 抽屉落点上提 app 级 -> dock.html 分片)
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        assert "/shared/tpl/dock.html" in [p["src"] for p in mf["parts"]], f"{ui} 清单缺 dock.html 分片"
        assert "/shared/tpl/drawer.html" in [p["src"] for p in mf["parts"]], f"{ui} 清单缺 drawer.html 分片"
        assert "/shared/vendor/uPlot.iife.min.js" in mf["scripts"], f"{ui} 清单缺 uPlot vendor"
        assert "/shared/qb_traffic_chart.js" in mf["scripts"], f"{ui} 清单缺组件 mixin"
        assert os.path.isfile(os.path.join(STATIC_ROOT, "shared", "vendor", "uPlot.iife.min.js")), \
            "uPlot.iife.min.js 不在盘上(404 = 整页停在错误占位)"
    assert 'class="drawer-dock"' in dock_tpl, "dock.html 缺 .drawer-dock 落点(boot 会 fail-fast)"
    assert "app.mixin(window.AQB_QB_TRAFFIC)" in app_js, "app.js 未注入 AQB_QB_TRAFFIC(整块功能静默消失)"
    # 三挂点并入抽屉后, Esc/escBusy 单点写 drawerVisible(dialogs.js + lifecycle.js 两处同步):
    # 面板 DOM 已退场(不在主内容页)时不吃 Esc —— 那条 Esc 要留给当前页面(设置页退回首页)
    assert "this.drawerVisible ||" in dialogs_js, \
        "escBusy 名单缺抽屉项(drawerVisible; 抽屉承载流量图, 与 Esc 退栈链两处同步纪律)"
    assert "else if (this.drawerVisible) this.closeDrawer();" in lifecycle_js, \
        "Esc 退栈链缺抽屉分支(种子详情与流量图共用 closeDrawer; 判据必须是 drawerVisible)"
    # 两图同开时的退栈顺序: 历史流量弹层(.modal-mask, z-index 130)盖在停靠抽屉(80)之上,
    # 视觉最上层必须**先**被 Esc 关掉, 否则那次 Esc 会穿过遮罩去关底下被盖住的抽屉
    # (2026-10-06 报障: qB 口径流量图与历史流量图同开时 Esc 先关了抽屉 —— 顺序即视觉层叠)
    hist_at = lifecycle_js.find("else if (this.historyOpen) this.historyOpen = false;")
    drawer_at = lifecycle_js.find("else if (this.drawerVisible) this.closeDrawer();")
    assert 0 <= hist_at < drawer_at, \
        "Esc 退栈链顺序错误: 历史弹层(遮罩 130)必须先于抽屉(80)关闭, 否则两图同开时 Esc 穿过遮罩关错层"
    assert "this.drawer.open = false" in auth_js and "this._qbTeardown()" in auth_js, \
        "_logout 必须收起抽屉并 _qbTeardown(不留对 /api/traffic/qb/* 的后台请求)"
    assert "this.qbHistData = null" in auth_js and "this.qbGroupData = null" in auth_js \
        and "this.qbTorrentData = null" in auth_js, \
        "_logout 必须清三挂点数据(受保护内容同 historyOpen 先例)"

    # 4. CSS 三套 UI 成对(.qb-* 结构类 + .sb-qb 入口; tooltip/图例复用 .hist-* 不在此列)
    # 判据落在**最终生效面**(皮肤聚合 + shared 共用层, link 序): .qb-tabs 组件本体自
    # issue 26-10-20-2231 起收敛进 shared/console_hub.css(三皮肤逐条同, 单点一份),
    # 只读皮肤聚合会恒红; 用共用层兜住「三皮肤都吃到」这件事, 而 .qb-note/.qb-chart
    # 等仍由各皮肤自带(未收敛) —— 两处断言的语义因此都还是「三皮肤成对」。
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
    ):
        for rule, what in (
            (".qb-tabs button.active", "窗口切换激活态"),
            (".qb-note", "加载/空态"),
            (".qb-chart {", "图表容器(悬停 tooltip 定位锚)"),
            (".sb-qb {", "今日流量面板入口按钮"),
            (".drawer-body.is-traffic { display: flex;", "抽屉流量形态正文 flex 纵列"),
            (".drawer-body.is-traffic .qb-chart-host { height: 100%; }", "图高撑满抽屉可用高"),
        ):
            assert rule in css, f"{name} 缺 {rule}({what}) —— 三套 UI 必须成对改"

    # 5. 三挂点并入抽屉 + 低频轮询(plan §07 表①②③ + 「轮询/取数」列)
    # 作用域表 = 三挂点单一描述源: 三作用域齐全, 各持 state 字段名/容器 ref/端点 url;
    # 2026-10-04 并入抽屉后三挂点建图落点统一 qbChartHost(同一时刻只渲染一个流量形态)
    assert js.count('host: "qbChartHost"') == 3, \
        "_QB_SCOPES 三挂点必须统一建图落点 ref=qbChartHost(抽屉内共用一段正文块)"
    assert 'url: (h, w) => "/api/traffic/qb/torrent/" + h + "?window=" + w' in js, \
        "单种作用域端点串漂移(/api/traffic/qb/torrent/{hash})"
    assert 'url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w' in js, \
        "分组作用域端点串漂移(/api/traffic/qb/group/{key}; key 原样内插 = encode_group_key 通道, 不自行编码)"
    # 单种挂点(§07 表②): 种子详情头部「流量」页签 v-if 门 + drawer.js 接线三处
    assert 'v-if="qbTrafficOn"' in drawer_tpl and 'drawerTab(\'traffic\')' in drawer_tpl, \
        "drawer.html 缺「流量」页签按钮(v-if=qbTrafficOn 门 + drawerTab 入口)"
    assert 'tab === "traffic" && this.qbTrafficOn' in store_js and 'this._qbPollStart("torrent")' in store_js, \
        "drawer_store.js _loadDrawerTab 缺流量页签分支(加载 + 起轮询; W1 起取数在数据层)"
    assert 'this._qbPollStop("torrent")' in store_js, \
        "drawer_store.js _stopDrawerPoll 缺流量轮询收口(关抽屉/切页签/换目标全走这里 = 关闭即停; W1 起在数据层)"
    assert 'last === "traffic" && !this.qbTrafficOn' in drawer_js, \
        "drawer.js 打开抽屉缺流量页签初值归一(功能关闭时上次停留页签须落回常规页)"
    # 全局/分组挂点: 组右键菜单项(v-if 门) + 抽屉流量形态(共用正文块/建图落点/关闭/窗口切换)
    # W3(计划 26-10-20-0024)起组右键菜单项改注册表单点(ctx_menu.js group 支): 门控与分派
    # 从模板文本搬到注册表定义(gate: "qb_traffic" / act: vm.openQbGroup(vm.menu.key))
    reg = open(os.path.join(shared, "ctx_menu.js"), encoding="utf-8").read()
    assert 'gate: "qb_traffic"' in reg and "vm.openQbGroup(vm.menu.key)" in reg, \
        "ctx_menu.js 缺组右键「qB 口径流量图」菜单项(注册表 gate: qb_traffic + menu.key 直用的 encode_group_key 通道)"
    assert reg.count("vm.openQbGroup(vm.menu.key)") == 1, "组右键菜单项只能挂在单组菜单(多选/剧集菜单不得出现)"
    assert 'ctxItems(ctxMenuKind())' in ctx_menus, \
        "ctx-menus.html 行菜单必须 v-for 消费注册表(支名走 menu.js::ctxMenuKind() 单点; 回退静态直写 = 四支人肉奇偶复发)"
    assert 'v-if="qbTrafficActive"' in drawer_tpl and 'ref="qbChartHost"' in drawer_tpl \
        and 'qbCurSummary' in drawer_tpl, \
        "drawer.html 缺流量形态正文块(三挂点共用: qbTrafficActive 门 / 建图落点 / 汇总)"
    # W3(计划 26-10-11-2106): 头部外壳与「档位 + 纵轴」控件组自 drawer.html 收进组件模板 ——
    # 口径一字不变(三挂点控件齐全 / 标题取 qbTrafficTitle), 断言面换到组件模板与调用点。
    # !建图落点 ref="qbChartHost" 仍**必须**留在 drawer.html(壳模板): _qbChartBuild 取宿主走
    #   this.$refs[def.host], 而该 this 恒是根实例(Vue 的 $refs 只在声明它的实例上登记) ——
    #   搬进组件 = 图永远不画且无报错, 见 tpl/drawer.html 流量正文段的长注与计划 §05 W3「落地」。
    # 26-10-20-2231: 两组分段钮改 <aq-seg> 数据驱动, 按钮本体不再逐个写死在模板里 ——
    # 判据从「模板里有这几个回调」升级为「模板把两组的 items/value/pick 都接到 $root 单点」。
    assert ':on-pick="$root.qbSetWindow"' in head_tpl and ':on-pick="$root.qbSetYAxisMode"' in head_tpl, \
        "tpl/drawer-head.html 的 <aq-qb-ctl> 缺档位/纵轴控件(三挂点控件必须齐全)"
    assert '<aq-qb-ctl></aq-qb-ctl>' in drawer_tpl, \
        "drawer.html 缺 <aq-qb-ctl> 挂点(流量形态头部中部与种子流量页签统计栏各一个)"
    assert 'drawerIsTraffic' in drawer_tpl and 'qbTrafficTitle' in drawer_tpl, \
        "drawer.html 缺流量形态头部调用点(形态判据 drawerIsTraffic + 标题取 qbTrafficTitle)"
    assert 'this.openDrawerTraffic("global", "")' in js and 'this.openDrawerTraffic("group", key)' in js, \
        "openQbHistory/openQbGroup 必须归一到 openDrawerTraffic(打开流量形态抽屉)"
    assert 'this._qbLoad(scope);' in js and 'this._qbPollStart(scope);' in js, \
        "openDrawerTraffic 缺打开拉取 + 起轮询(§07 表③「打开弹层拉取」)"
    assert 'if (!this.qbTrafficOn || !key) return;' in js, "openQbGroup 缺 fail-closed 兜底门(入口 v-if 之外的加载路径)"
    # 低频轮询(§07): 间隔取 meta.interval_s 夹取([1.5s,600s] 配置校验界, A4 下界对齐
    # v3 采样间隔放宽后的真实下界) + 30s 兜底 + document.hidden 跳过(对齐 drawer.js
    # _startDrawerPoll 先例) + 关闭路径显式 clearInterval
    assert "_QB_POLL_FALLBACK_MS = 30000" in js and "_QB_POLL_MIN_MS = 1500" in js and "_QB_POLL_MAX_MS = 600000" in js, \
        "轮询间隔常量漂移(30s 兜底 / [1.5s,600s] 夹取界 = §06 配置校验边界, A4: 15000 -> 1500)"
    assert "Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, s * 1000))" in js, \
        "轮询间隔必须经 [1.5s,600s] 夹取(agg 段窗 meta.interval_s=3600 是桶宽, 直拉 = 一小时不刷新)"
    # 三判据(不活跃 / 页面隐藏 / 在途未落袋)语义不变, 书写形态 2026-10-22 再变一次: 轮询生命周期
    # 收敛进 polling.js 骨架(startPoll)—— 页面隐藏由骨架的**恒等守卫**兜(不再每处手写 document.hidden),
    # 在途互斥 + 悬挂兜底改为声明 `stall` / `mutex` 两个键。故这里按语义钉: 声明齐全 + 文件内零裸
    # 定时器(启停一律经骨架); 细分行为(未悬挂挡拍 / 悬挂放行 / 抽屉侧同口径)由
    # test_frontend_qb_traffic_load_stall_fallback 与 test_frontend_poll_skeleton_single_point 逐拍钉住。
    assert "this.startPoll(`qb:${scope}`, {" in js, \
        "流量轮询必须走骨架 startPoll 单点(文件内不得再手写 setInterval/clearInterval 启停)"
    assert "guard: () => _QB_SCOPES[scope].active(this)," in js, \
        "流量轮询缺「图还活跃」守卫声明(页面隐藏由骨架恒等守卫兜, 但活跃判据要自己声明)"
    assert "stall: () => this[_QB_SCOPES[scope].loading]," in js and "mutex: true," in js, \
        "流量轮询缺在途互斥 / 悬挂兜底声明(判据退回裸早退 = loading 卡死即永久挡拍, issue 26-10-16-0954)"
    assert "setInterval(" not in js and "clearInterval(" not in js, \
        "qb_traffic_chart.js 不得再裸写定时器(启停收口到骨架, 手柄在 _polls 表)"
    # 关闭路径统一收口(2026-10-04): closeDrawer 收抽屉即 _qbTeardown(停三挂点轮询 + 销毁三挂点图)
    assert "this._qbTeardown();" in drawer_js, \
        "drawer.js 缺 _qbTeardown 调用(关抽屉/换形态时轮询与图不停, P5 验收)"
    teardown_blk = re.search(r"_qbTeardown\(\) \{\n(.*?)\n    \},", js, re.S)
    assert teardown_blk and "this._qbPollStop(s)" in teardown_blk.group(1) \
        and "this._qbChartDestroy(s)" in teardown_blk.group(1), \
        "_qbTeardown 必须停三挂点轮询并销毁三挂点图(单点收口)"
    # 静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): 续拉对用户不可见 ——
    # loading 空态只在「本作用域尚无任何落袋结果」时接管正文(判据 qbCurPending 三合一 = loading +
    # 无数据 + 无错误), 数据落袋走 setData 原地快路(destroy+new uPlot 清屏一帧), 换肤因 canvas 色
    # 烘焙必须先销毁再整图重建(setData 不换色)。2026-10-04 那版只门了「有图」一态
    # (!qbCurPoints.length): 空数据集的空态文案与错误文案仍被每个轮询周期的 loading 顶掉一帧
    # (真机报「流量图闪烁 暂无…」), 判据因此改为按「有无落袋结果」而不是按「有无点」。
    assert 'v-if="qbCurPending"' in drawer_tpl, \
        "drawer.html loading 空态必须门在 qbCurPending 上(按有无落袋结果而不是有无点: 空态/错误态被接管 = 每个轮询周期闪一次)"
    pending_blk = re.search(r"qbCurPending\(\) \{\n(.*?)\n    \},", js, re.S)
    assert pending_blk and "this.qbCurLoading && !this.qbCurData && !this.qbCurError" in pending_blk.group(1), \
        "qbCurPending 必须三合一(loading + 无数据 + 无错误): 少任一项都有一种既有状态(图/空态/错误)被续拉顶掉"
    load_blk = re.search(r"async _qbLoad\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert load_blk, "qb_traffic_chart.js 缺 _qbLoad(取数单点)"
    load_body = load_blk.group(1)
    assert load_body.index("await this.api(") < load_body.index('this[def.error] = "";') \
        and load_body.index("this[def.data] = data;") < load_body.index('this[def.error] = "";'), \
        "错误态只允许在**成功落袋**分支清(发请求前清 = 续拉把错误文案换成 loading/空态再换回 = 每个轮询周期闪一次)"
    assert "prev.setData([data.xs, data.up, data.dl]);" in js and "prev.root.parentElement === host" in js, \
        "qb_traffic_chart.js 缺 setData 原地快路(每次轮询 destroy+new uPlot 清屏 = 每隔一个轮询周期闪一次)"
    theme_blk = re.search(r"_qbOnThemeChange = \(\) => \{\n(.*?)\n        \};", js, re.S)
    assert theme_blk and theme_blk.group(1).find("this._qbChartDestroy(s)") < theme_blk.group(1).find("this._qbChartBuild(s)"), \
        "换肤处理器必须先 _qbChartDestroy 再 _qbChartBuild(canvas 色建图时烘焙, setData 快路不换色)"
    # FX-29 软切换落定登记(2026-10-04 修「流量页签单击换行『正在加载…』挂死」): 换目标软切换的
    # 待到集合含 "traffic"(_drawerWaitSources 通用分支), 但 _drawerDone 只有 detail/trackers/
    # files/peers 四个 fetcher 在调 —— _qbLoad 落袋不登记则集合永不清空, drawer.switching 遮罩
    # 挂死盖住图(双击走 openTorrentDrawer 整体重置不经待到集合, 只有单击跟随软切换踩中)
    assert 'if (scope === "torrent") this._drawerDone("traffic", ctx, 0);' in js, \
        "qb_traffic_chart.js _qbLoad 落袋必须登记 FX-29 落定(_drawerDone('traffic')), 否则软切换遮罩等一个永不到手的源挂死"
    wait_blk = re.search(r"_drawerWaitSources\(tab\) \{\n(.*?)\n    \},", store_js, re.S)
    assert wait_blk and 'return ["detail", tab]' in wait_blk.group(1), \
        "drawer_store.js _drawerWaitSources 通用分支必须覆盖 traffic 页签(与 _qbLoad 的落定登记成对, 拆开即挂死; W1 起在数据层)"
    # state.js 根选项显式建字段(Vue 响应式前置, frontend-split 纪律)
    for field in (
        "qbTorrentWindow", "qbTorrentData", "qbTorrentLoading", "qbTorrentError", "qbTorrentHoverIdx",
        "qbTorrentHoverLeft", "qbGroupKey", "qbGroupName", "qbGroupWindow", "qbGroupData", "qbGroupLoading",
        "qbGroupError", "qbGroupHoverIdx", "qbGroupHoverLeft"
    ):
        assert re.search(rf"^\s+{field}: ", state_js, re.M), f"state.js 缺 {field} 初值(根选项显式建字段)"
    assert 'kind: "seed", scope: ""' in state_js, \
        "state.js drawer 缺 kind/scope 初值(抽屉双形态, vue-reactivity 前置)"

    # 6. 缺口三态文案与空态(plan 26-10-04-0721 §05, P4): 三皮肤共用 shared/tpl/drawer.html 与
    # shared/qb_traffic_chart.js(登记链已在上面第 3 点逐皮肤钉住), 文案单点改动三皮肤同时
    # 生效 —— 这里钉文案本体 + 触发判据 + 旧文案退场, 不逐皮肤重复
    assert 'v-if="qbCurHover.up + qbCurHover.dl === 0">0 B/s · 空闲/做种</span>' in drawer_tpl, \
        "悬停 0 桶缺状态行(空闲段 z 派生 (0,0) 真实观测点, 必须与 null 缺口可辨; 速率行照旧)"
    assert "无采样 · 程序未运行或 qB 断连" in drawer_tpl, \
        "悬停缺口文案未更新(plan §05 首版合并文案: 两态区分依赖可选 API 形状增强, 拍板不做)"
    assert "断线 · 无数据" not in drawer_tpl, "旧缺口文案「断线 · 无数据」必须退场"
    # 2026-10-08 版式改(用户动议): 两处 hint 全移除 —— 图下那行独立图例(含口径注释)并入统计栏,
    # 口径说明不再以常驻文案出现(信息在悬停 tooltip 里给)。原「两处 hint 同步」的守阵随之退役,
    # 改为钉「文案已退场」+「图例已入统计栏」+「档位/纵轴控件已上提头部」三条新口径。
    assert "缺口 = 无采样" not in drawer_tpl and "悬停查看详情" not in drawer_tpl, \
        "图例 hint 两处(工具条 + 图例)已按用户要求全部移除(2026-10-08 版式改), 不得复现"
    assert "断线处不连线" not in drawer_tpl, "旧图例 hint「断线处不连线」必须退场"
    # 版式改结构钉住: ①图例(上行/下行)在统计栏 .hist-summary 内, 不再是独立的 .hist-legend 行;
    # ②档位/纵轴控件在图下统计栏 .qb-statctl 内(2026-10-16 版式改: 流量形态头部不再挂控件,
    # 全局/分组与种子流量图对齐 —— 头部调用点必须**不再**接 <aq-qb-ctl>)
    # W3(计划 26-10-11-2106): 头部外壳收进 <aq-drawer-head>; 2026-10-16 起控件组唯一挂点 =
    # 统计栏, 头部调用点退回空插槽(仅标题 + 关闭钮)。
    traffic_call = re.search(r'<aq-drawer-head v-if="drawerIsTraffic"[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert traffic_call and '<aq-qb-ctl>' not in traffic_call.group(1), \
        "流量形态头部不得再挂档位/纵轴控件组(2026-10-16 版式改: 与种子流量图对齐, 控件统一落图下统计栏)"
    assert 'class="qb-tabs"' in head_tpl and 'class="qb-tools"' in head_tpl, \
        "<aq-qb-ctl> 缺 .qb-tabs/.qb-tools(控件组的唯一实现)"
    # 2026-10-09 第 2 轮(用户动议): 种子流量图(kind === "seed" + tab === "traffic")的档位/纵轴
    # 控件组**从种子头部挪走** —— 头部已承载五页签导航 + 模板切换器, 13 档再并进去太挤、窄视口下
    # 会变形; 改落**图下统计栏** .hist-summary, 排在「下载累计」之后(用户: 「即『下载累计』后」)。
    seed_call = re.search(r'<aq-drawer-head v-else[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert seed_call and 'qb-statctl' not in seed_call.group(1) \
        and 'qb-headctl' not in seed_call.group(1) and 'aq-qb-ctl' not in seed_call.group(1), \
        "种子头部不得再挂流量档位/纵轴控件组(2026-10-09 第 2 轮: 已改落图下统计栏, 头部保持单行 44px)"
    stat_blk = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('种子详情形态正文(五页签)')]
    assert 'class="qb-statctl"' in stat_blk and '<aq-qb-ctl></aq-qb-ctl>' in stat_blk, \
        "档位/纵轴控件组必须落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮; 2026-10-16 起为唯一挂点; W3 起经 <aq-qb-ctl>)"
    # 2026-10-16 版式改: 控件组不再按 scope 分叉 —— 三挂点(全局/分组/单种)统一落统计栏且恒渲染
    # (本段整体已在 qbTrafficActive 正文内), 「torrent 专属门」不得回潮。
    assert '<div v-if="qbCurScope === \'torrent\'" class="qb-statctl">' not in drawer_tpl \
        and '<div class="qb-statctl">' in stat_blk, \
        "统计栏控件组必须恒渲染(2026-10-16 三挂点统一), 不得再门在 qbCurScope === 'torrent'"
    # 落点次序(用户口径「即『下载累计』后」): 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 控件组
    _order = [stat_blk.index(k) for k in ("hs-leg", "窗口", "上传累计", "下载累计", "qb-statctl")]
    assert _order == sorted(_order), \
        "统计栏次序必须为 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 档位/纵轴控件组"
    assert 'hs-leg' in stat_blk and '上传' in stat_blk and '下载' in stat_blk, \
        "统计栏(.hist-summary)必须含上传/下载图例(.hs-leg), 且排在「窗口 N 桶」之前"
    # 口径注解(2026-10-09 第 3 轮, 用户动议): 常驻文案退场, 改为两个累计读数的悬浮提示。
    # title 走全局断供管道(ui_feedback.js 落 DOM 即迁 data-aq-tip), 文案单点仍是 qbCurSummaryHint。
    assert stat_blk.count(':title="qbCurSummaryHint"') == 2, \
        "「上传累计 / 下载累计」两处都要挂口径注解的悬浮提示(文案单一来源 qbCurSummaryHint)"
    assert 'class="hist-hint"' not in drawer_tpl, \
        "统计栏常驻口径文案(.hist-hint)必须退场(已改为两个累计读数的 tooltip; 弹层 popovers.html 里那处是另一用途)"

    # W3(计划 26-10-11-2106): 「两处控件组逐字同源」升级为「只有一处实现」—— 旧写法是两份复写
    # + 本处的字符串比对守阵(坑档 drawer-multi-form-hosts 的处置条: 无 partial 机制只能复写,
    # 复写必须逐字同源并加守阵); 本仓库现在有 partial 了(Vue 组件), 故改钉单点: 控件组标记在
    # 面板模板层只出现一次(在 tpl/drawer-head.html 的 <aq-qb-ctl> 里), drawer.html 只剩一个挂点
    # (图下统计栏; 2026-10-16 起头部挂点退役)——
    # 谁把控件抄回 drawer.html(复写回潮)即红, 覆盖强度不降反升(单点强于同源)。
    assert drawer_tpl.count('class="qb-tabs"') == 0 and drawer_tpl.count('class="qb-tools"') == 0, \
        "drawer.html 仍手写档位/纵轴控件组(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    assert head_tpl.count('class="qb-tabs"') == 1 and head_tpl.count('class="qb-tools"') == 1, \
        "<aq-qb-ctl> 模板必须恰一份 .qb-tabs 与 .qb-tools(控件组的唯一实现)"
    assert drawer_tpl.count("<aq-qb-ctl></aq-qb-ctl>") == 1, \
        "控件组唯一挂点(图下统计栏)必须接 <aq-qb-ctl>(2026-10-16 起头部挂点退役, 恰此一处)"
    assert 'class="hist-legend"' not in drawer_tpl, \
        "独立的图例行(.hist-legend)必须退场: 上行/下行图例已并入统计栏 .hist-summary"
    assert '暂无该种子的 qB 口径流量数据(从未有传输记录)' in js, \
        "单种空态文案未收窄为「从未有传输记录」(plan §03.3 拍板: 空闲不再产生空态)"
    assert "仅活跃传输期间有采样" not in js, \
        "旧单种空态文案必须退场(空闲段现在是 0 平线, 空态语义只剩从未传输)"


def test_frontend_qb_traffic_window_persist_and_single_source():
    """流量图「视图选择」持久化 + 窗口档位单点(2026-10-05, 拍板粒度: 全局单独 / 组与种子共用)

    背景: 窗口档位(13 档)此前只活在 state.js 根 data 里, 刷新即回默认 24h —— 视图选择是
    用户意图, 该像 drawerTab / view / page 一样落 localStorage。三条**静默**失效形态钉住:
    1. 档位清单单点: QB_WINDOW_NAMES 十三档(与后端 traffic_qb.WINDOW_NAMES 逐字一致)是
       展示(模板 v-for 走 qbWindowNames computed)/ 前后切换(qbCycleWindow)/ 持久化校验
       (qbInitialWindow)三处唯一来源 —— 任一处再硬编码就会与后端校验漂移(非法档 400);
    2. 持久化粒度: 全局一份(autoqb.ui.qbWinGlobal), 分组与种子共用一份(autoqb.ui.qbWinShared);
       键按 scope 单点分派(qbWinStoreKey); 初值 qbInitialWindow 只认合法档位(坏值/无存储回落
       默认); 换窗即落盘(_qbSetWindow -> persistQbWindow)且写失败吞异常(与 persistDrawerTab
       同纪律);
    3. 装载序: 初值函数定义在 qb_traffic_chart.js, 该文件在三份 tpl-manifest 里均排在 state.js
       之前(逐份断言)—— 否则 state.js 的 data() 调它时未定义, 整页启动即白屏。"""
    from auto_qb.webui.server.traffic_qb import WINDOW_NAMES  # noqa: PLC0415

    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 档位/纵轴控件组的唯一实现(<aq-qb-ctl>)与头部外壳住在这里
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()

    # 1. 档位清单单点 + 与后端逐字一致 + 展示面走 computed(模板不再硬编码)
    m = re.search(r"const QB_WINDOW_NAMES = \[(.*?)\];", js, re.S)
    assert m, "qb_traffic_chart.js 缺 QB_WINDOW_NAMES 单点(档位清单)"
    names = re.findall(r'"([^"]+)"', m.group(1))
    assert tuple(names) == tuple(WINDOW_NAMES), \
        f"前端档位清单与后端 traffic_qb.WINDOW_NAMES 漂移: 前端 {names} / 后端 {list(WINDOW_NAMES)}"
    assert 'QB_WINDOW_DEFAULT = "24h"' in js, "缺 QB_WINDOW_DEFAULT(初值 / 非法档回落值)"
    assert re.search(r"qbWindowNames\(\) \{\n\s*return QB_WINDOW_NAMES;", js), \
        "qbWindowNames computed 必须直返 QB_WINDOW_NAMES(模板 v-for 的唯一来源)"
    # W3(计划 26-10-11-2106): 档位按钮自 drawer.html 收进 <aq-qb-ctl> 组件模板(两挂点共用一份
    # 实现), 故登记面换成组件模板 —— 口径不变(展示面走 computed, 不硬编码档位清单)。
    # 26-10-20-2231: 模板侧再降一层 —— 按钮本体也交给 <aq-seg>, 模板只交 items/value/pick;
    # 展示面仍只吃 computed(qbWindowTabs 投影自 QB_WINDOW_NAMES + qbWindowLabel), 零硬编码。
    assert ':items="$root.qbWindowTabs"' in head_tpl and ':value="$root.qbCurWindow"' in head_tpl, \
        "tpl/drawer-head.html 的 <aq-qb-ctl> 窗口按钮必须吃 qbWindowTabs + qbCurWindow(经 $root 回调根实例)"
    assert re.search(r"qbWindowTabs\(\) \{\n\s*return QB_WINDOW_NAMES\.map\(", js), \
        "qbWindowTabs 必须投影自 QB_WINDOW_NAMES(档位展示面仍只有一份清单)"
    assert 'v-for="w in qbWindowNames"' not in drawer_tpl and "v-for=\"w in ['1m'" not in drawer_tpl, \
        "drawer.html 仍手写档位按钮/硬编码档位清单(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    # 前后切换: 按单点序定位(非法档回落默认) + 端点夹取不环绕 + 走 qbSetWindow 单点
    cyc = re.search(r"qbCycleWindow\(delta\) \{\n(.*?)\n    \},", js, re.S)
    assert cyc, "qb_traffic_chart.js 缺 qbCycleWindow(窗口前后切换落点)"
    cb = cyc.group(1)
    assert "QB_WINDOW_NAMES.indexOf(cur)" in cb and "QB_WINDOW_NAMES.indexOf(QB_WINDOW_DEFAULT)" in cb, \
        "切换必须按 QB_WINDOW_NAMES 定位当前档(非法档回落默认)"
    assert "Math.min(QB_WINDOW_NAMES.length - 1, i + delta)" in cb and "Math.max(0," in cb, \
        "切换必须端点夹取(从「全部」环绕回「1分」是惊扰)"
    assert "this.qbSetWindow(next)" in cb, "切换必须走 qbSetWindow 单点(重拉 + 轮询重排 + 落盘一体)"
    assert "if (!s) return;" in cb, "无流量形态(qbCurScope 空)必须零副作用"

    # 2. 持久化粒度 + 键单点 + 初值校验 + 换窗落盘
    assert 'QB_WIN_STORE_KEY_GLOBAL = "autoqb.ui.qbWinGlobal"' in js, "缺全局窗口存储键"
    assert 'QB_WIN_STORE_KEY_SHARED = "autoqb.ui.qbWinShared"' in js, "缺共用窗口存储键(组/种子)"
    key_fn = re.search(r"function qbWinStoreKey\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert key_fn and 'scope === "global" ? QB_WIN_STORE_KEY_GLOBAL : QB_WIN_STORE_KEY_SHARED' in key_fn.group(1), \
        "qbWinStoreKey 必须按 scope 分派(全局单独 / 其余共用一份)"
    init_fn = re.search(r"function qbInitialWindow\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert init_fn, "缺 qbInitialWindow(窗口初值读取)"
    ib = init_fn.group(1)
    assert "localStorage.getItem(qbWinStoreKey(scope))" in ib and "QB_WINDOW_NAMES.includes(v)" in ib, \
        "初值必须读存储且只认合法档位(坏值回落默认)"
    assert "return QB_WINDOW_DEFAULT;" in ib and "catch" in ib, "初值读取失败必须吞异常回落默认"
    setw = re.search(r"async _qbSetWindow\(scope, w\) \{\n(.*?)\n    \},", js, re.S)
    assert setw and "this.persistQbWindow(scope, w);" in setw.group(1), \
        "换窗必须落盘(_qbSetWindow -> persistQbWindow)"
    persist = re.search(r"persistQbWindow\(scope, w\) \{\n(.*?)\n    \},", js, re.S)
    assert persist and "localStorage.setItem(qbWinStoreKey(scope), w)" in persist.group(1) \
        and "catch" in persist.group(1), "persistQbWindow 必须写键单点且吞写入异常(与 persistDrawerTab 同纪律)"
    # state.js 三字段按 scope 取初值(全局单独 / 组与种子共用同一键)
    assert 'qbHistWindow: qbInitialWindow("global")' in state_js, "state.js 全局窗口初值未接持久化"
    assert 'qbTorrentWindow: qbInitialWindow("torrent")' in state_js, "state.js 种子窗口初值未接持久化"
    assert 'qbGroupWindow: qbInitialWindow("group")' in state_js, "state.js 分组窗口初值未接持久化"

    # 3. 装载序: qb_traffic_chart.js 必须排在 state.js 之前(初值函数在 state data() 时可用)
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert scripts.index("/shared/qb_traffic_chart.js") < scripts.index("/shared/state.js"), \
            f"{ui}: qb_traffic_chart.js 必须排在 state.js 之前(qbInitialWindow 定义处, 否则启动白屏)"


# 纵轴固定模式 + 缺口游程 + 重启缝判据 node 电池(2026-10-08; P4 追加 _qbSeamHint, plan 26-10-15-0829):
# 三个模块级纯函数 _qbYRange/_qbGapRuns/_qbSeamHint 真跑。无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_QB_YAXIS_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
const eq = (n, got, want) => checks.push([n, JSON.stringify(got) === JSON.stringify(want)]);
const ok = (n, cond) => checks.push([n, !!cond]);
// 值域: 自动 = peak*1.05(无数据回落 1); 固定上限取 max(cap, peak*1.05) —— 峰值超上限按峰值显示
eq("auto 无数据回落 1", _qbYRange(0, 0), [0, 1]);
eq("auto 峰值", _qbYRange(100, 0), [0, 105]);
eq("固定上限高于峰值(上限即顶)", _qbYRange(100, 120), [0, 120]);
eq("峰值超固定上限按峰值显示", _qbYRange(200, 120), [0, 210]);
eq("手动上限无峰值(上限即顶)", _qbYRange(0, 50), [0, 50]);
// 缺口游程: 上下行皆 null 才算缺口(单列 null 防御性不误判)
eq("缺口游程 中段+尾段", _qbGapRuns([1, null, null, 4, null], [1, null, null, 4, null]), [[1, 2], [4, 4]]);
eq("缺口游程 前导", _qbGapRuns([null, 2, 3], [null, 2, 3]), [[0, 0]]);
eq("缺口游程 全 null", _qbGapRuns([null, null], [null, null]), [[0, 1]]);
eq("缺口游程 无缺口", _qbGapRuns([1, 2, 3], [1, 2, 3]), []);
eq("单列 null 不算缺口", _qbGapRuns([null, 2], [1, 2]), []);

// 重启缝提示判据(P4, plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): _qbSeamHint 真跑
// —— 数据链末点早于右沿 + 重启贴近链末(∈ [链末桶前一桶起点, 右沿]) -> 提示; 链到右沿/链确已接续/旧后端不提示
// 场景重建: 链止于 t=130 桶(覆盖端 160), 尾区 [160, 250], 服务 178 起 -> 提示
const mkP = (t, dl, up) => ({ t, dl, up });
const seamPts = [mkP(100, 5, 5), mkP(130, 6, 6), null, null, null];
eq("重启缝 尾区含重启->提示", _qbSeamHint(seamPts, 30, { server_started_at: 178 }), { startedAt: 178 });
eq("重启缝 边界 恰在尾区起点->提示", _qbSeamHint(seamPts, 30, { server_started_at: 160 }), { startedAt: 160 });
eq("重启缝 边界 恰在右沿->提示", _qbSeamHint(seamPts, 30, { server_started_at: 250 }), { startedAt: 250 });
eq("重启缝 链到右沿->null(末桶观测/当前桶未采完是常态)", _qbSeamHint([mkP(100, 5, 5), mkP(130, 6, 6)], 30, { server_started_at: 178 }), null);
eq("重启缝 重启落在链末桶覆盖窗->提示(修订: 链末桶晚于重启时刻不再是豁免)", _qbSeamHint(seamPts, 30, { server_started_at: 140 }), { startedAt: 140 });
eq("重启缝 边界 恰在链末前一桶起点->提示", _qbSeamHint(seamPts, 30, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝 早于链末前一桶->null(链确已接续)", _qbSeamHint(seamPts, 30, { server_started_at: 99 }), null);
eq("重启缝 重启远早于链末->null(链确已接续)", _qbSeamHint(seamPts, 30, { server_started_at: 40 }), null);
eq("重启缝 晚于右沿->null(防御)", _qbSeamHint(seamPts, 30, { server_started_at: 300 }), null);
eq("重启缝 旧后端无新键->null(不猜)", _qbSeamHint(seamPts, 30, {}), null);
eq("重启缝 meta缺失->null", _qbSeamHint(seamPts, 30, null), null);
eq("重启缝 interval非法->null", _qbSeamHint(seamPts, 0, { server_started_at: 178 }), null);
eq("重启缝 全null->null(空态面)", _qbSeamHint([null, null], 30, { server_started_at: 178 }), null);
eq("重启缝 空数组->null", _qbSeamHint([], 30, { server_started_at: 178 }), null);
// 反例回归(issue 26-10-16-0954 实测帧重建): 1m 窗 interval=2s —— 04:45:00 记 100, 04:45:01 重启(101),
// 首采桶 04:45:02(102, 全窗唯一非 null; 左侧停机洞 + 右侧开放零游程读侧未交付均 null), 右沿 140;
// 修订前判据在 started < 链末桶覆盖端(104) 处恒返回 null(现场 04:45:40 帧零提示的机制)
const seamFrame = new Array(30).fill(null);
seamFrame[11] = mkP(102, 0, 0);
eq("重启缝 实测帧 首采即链末桶->提示(旧口径恒 null)", _qbSeamHint(seamFrame, 2, { server_started_at: 101 }), { startedAt: 101 });
eq("重启缝 实测帧 边界 恰在链末前一桶起点->提示", _qbSeamHint(seamFrame, 2, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝 实测帧 早一桶宽->null", _qbSeamHint(seamFrame, 2, { server_started_at: 99 }), null);

/* ---------- 缺口斜纹**配色 + 几何**真跑(2026-10-08 两轮) ----------
 * 用记账式假 ctx 调**真实的** AQB_QB_TRAFFIC.methods._qbDrawGaps, 断言:
 *   ① 配色: 写进画布的 strokeStyle/globalAlpha 是高对比专用令牌而非 --hairline 系极低 alpha;
 *   ② 几何: 逐 run 追加的**缺口矩形 clip** 恰好等于 [xa, xb] x [T, T+H], 且每条斜纹线段都被该
 *      矩形包含(端点 x 落在 [xa, xb])—— 钉死"斜纹铺成竖矩形"的语义: 若有人删掉 per-run clip
 *      (退回只裁绘图区), 斜带(宽 H 的平行四边形)的端点会越出 [xa, xb], 断言立刻变红。
 * 这条电池的价值: 把"颜色够不够看得见""斜纹落在哪"从"读源码字符串"升级为"实跑取真值并做数值/
 * 几何判定" —— 静态锚可能被同步改掉, 数值下界与几何包含判定不会。 */
function _mkCtx2() {
  const noop = () => {};
  return {
    style: null, alpha: null, segCount: 0, _x0: 0,
    clips: [], _pendingRect: null, _segs: [],
    save: noop, restore: noop, beginPath: noop, setLineDash: noop,
    rect(x, y, w, h) { this._pendingRect = { x, y, w, h }; },
    clip() { if (this._pendingRect) this.clips.push(this._pendingRect); },
    moveTo(x, y) { this._sx = x; },
    lineTo(x, y) { this.segCount++; this._segs.push([this._sx, x]); },
    stroke() {},
    set strokeStyle(v) { this.style = v; },
    get strokeStyle() { return this.style; },
    set globalAlpha(v) { this.alpha = v; },
    get globalAlpha() { return this.alpha; },
    set lineWidth(v) {}, get lineWidth() { return 1; },
  };
}
(function () {
  const AQB2 = global.window.AQB_QB_TRAFFIC;
  const fn = AQB2 && AQB2.methods && AQB2.methods._qbDrawGaps;
  ok("_qbDrawGaps 可取(配色电池)", !!fn);
  if (!fn) return;
  const xs2 = [0, 60, 120, 180, 240];
  const ctx2 = _mkCtx2();
  const u2 = {
    data: [xs2, [5, 5, null, null, 5], [5, 5, null, null, 5]],
    bbox: { left: 50, top: 17, width: 825, height: 233 },
    ctx: ctx2,
    valToPos: (v) => (xs2.indexOf(v) / 4) * 825,
  };
  /* tk.gap = 高对比专用令牌值; tk.grid = 旧的 --hairline 极低 alpha 值 —— 必须选前者 */
  fn.call({ _qbCanvasScale: (uu) => { uu.ctx.save(); return 1; } }, u2,
    { grid: "rgba(255,255,255,.055)", gap: "rgba(255,255,255,.22)" });
  eq("斜纹取 gap 专用令牌(不取 --hairline)", ctx2.style, "rgba(255,255,255,.22)");
  eq("斜纹不再叠 globalAlpha 折半", ctx2.alpha, 1);
  ok("斜纹确实画了线段(>0 条)", ctx2.segCount > 0);
  /* 数值下界: 令牌 alpha 必须 >= 0.15(--hairline 系 0.055 量级的 3 倍以上才算"看得见") */
  const m2 = /rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)/.exec(
    "rgba(255,255,255,.22)");
  ok("专用令牌 alpha 量级 >= 0.15(0.05 级别等同不可见)", m2 && parseFloat(m2[1]) * ctx2.alpha >= 0.15);

  // ---- 几何: per-run 缺口矩形 clip + 扫线覆盖 ----
  // 注: 真实 ctx 的 clip 是**画布操作**, 不会改写我们记账到的原始端点 —— 故原始 moveTo/lineTo
  // 端点本就会越出 [xa, xb](越界部分由 canvas clip 收掉)。几何正确性由两点钉死:
  //   ① per-run 缺口矩形 clip 存在且 == [xa, xb] x [T, T+H](删掉它即退回"只裁绘图区"= 平行四边形缺陷);
  //   ② 扫线范围**覆盖**缺口带(有线段右下端 >= xb, 有线段左上端 <= xa)—— 保证裁剪后左/右竖直边都铺满, 无半边留白。
  const xa = 50 + (xs2.indexOf(120) / 4) * 825;   // 缺口 = 桶 2..3
  const xb = 50 + (xs2.indexOf(180) / 4) * 825;
  const T = 17, H = 233;
  const gapClips = ctx2.clips.filter((c) => Math.abs(c.x - xa) < 1e-6 && Math.abs(c.w - (xb - xa)) < 1e-6
    && Math.abs(c.y - T) < 1e-6 && Math.abs(c.h - H) < 1e-6);
  ok("存在逐 run 缺口矩形 clip(ctx.rect(xa, T, xb-xa, H))", gapClips.length >= 1);
  ok("缺口矩形 clip 与绘图区 clip 并存(外层仍收在绘图区)",
    ctx2.clips.some((c) => Math.abs(c.w - 825) < 1e-6));
  const segs = ctx2._segs || [];
  // 扫线覆盖: 每条线段 = [左上端 x0, 右下端 x1](x0 = x-H, x1 = x); 需有 x1 >= xb(右端铺满)
  // 且有 x0 <= xa(左端铺满)。
  ok("扫线覆盖缺口左边界(有线段左上端 <= xa)", segs.some((s) => s[0] <= xa + 1e-6));
  ok("扫线覆盖缺口右边界(有线段右下端 >= xb)", segs.some((s) => s[1] >= xb - 1e-6));
  // 扫线步长恒定 8px(斜纹间距), 且每条线段水平跨度 = H(45 度硬约束)
  ok("每条斜纹线段跨度 = H(45 度)", segs.every((s) => Math.abs((s[1] - s[0]) - H) < 1e-6));
})();

(function () {
  /* ---------- 限速分段(plan 26-10-12-0535 D4/D7)真跑: _qbLimitSegs/_qbLimitAt ----------
   * 用真实的模块级纯函数断言: 每段几何(区间/末段到 tEnd)/退化段不画/悬停二分取值
   * (含记录起点前 null)。若有人把分段改回单值画满整窗, 本电池立刻红。 */
  ok("_qbLimitSegs 可取", typeof _qbLimitSegs === "function");
  ok("_qbLimitAt 可取", typeof _qbLimitAt === "function");
  const EV = [[100, 1024, 2048], [200, 0, 4096], [300, 512, 512]];
  eq("分段几何: 每段 = 相邻事件区间", _qbLimitSegs(EV, 400),
    [{ t0: 100, t1: 200, up: 1024, down: 2048 }, { t0: 200, t1: 300, up: 0, down: 4096 }, { t0: 300, t1: 400, up: 512, down: 512 }]);
  eq("分段: 末段延伸到 tEnd", _qbLimitSegs(EV.slice(0, 1), 250), [{ t0: 100, t1: 250, up: 1024, down: 2048 }]);
  eq("分段: 空事件空段", _qbLimitSegs([], 400), []);
  eq("分段: 非法输入空段", _qbLimitSegs(null, 400), []);
  eq("分段: tEnd 非法空段", _qbLimitSegs(EV, 0), []);
  eq("分段: 越出右沿的退化段不画", _qbLimitSegs([[500, 1, 1]], 400), []);
  eq("悬停二分: 取 <= ts 最近事件", _qbLimitAt(EV, 250), [0, 4096]);
  eq("悬停二分: 精确命中", _qbLimitAt(EV, 200), [0, 4096]);
  eq("悬停二分: 记录起点前 null(D5 不猜)", _qbLimitAt(EV, 50), null);
  eq("悬停二分: 空事件 null", _qbLimitAt([], 100), null);
  eq("悬停二分: 末事件之后仍取末值", _qbLimitAt(EV, 999), [512, 512]);
})();
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# _QB_SCOPES 是模块级 `const`, sloppy 模式下的直接 eval 不会把它漏到外层作用域(只有 function/var
# 声明会漏) —— 故这里用 `new Function(源码 + "return _QB_SCOPES;")` 把它从函数体内部取出来,
# 再对三个作用域的 `stale` 谓词喂真值上下文做**行为**断言(不读源码字符串)。
_NODE_QB_SCOPE_STALE_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const SCOPES = new Function(src + "\nreturn _QB_SCOPES;")();
const checks = [];
const ok = (n, cond) => checks.push([n, !!cond]);

/* stale 谓词语义(见 qb_traffic_chart.js 文件头): stale=true = 在途响应**已过期** -> 丢弃
 * (不落袋 + loading 不清)。故「本图正在被看」必须 stale=false, 其余一律 stale=true。
 * 2026-10-12 修: W2–W6 机械改名把 torrent/group 两处 `!(...)` 写成 `!!(...)`, 语义整个翻转
 * (恰在本图活跃时判过期) -> 数据永不落袋、loading 卡死 -> 种子流量页签恒停「正在加载…」。
 * 本电池就是那个漏网的运行时判据: 取反写反(单/双 bang 互换)立刻红。 */
const G = (over) => Object.assign(
  { drawer: { open: true, scope: "global" }, drawerIsTraffic: true, drawerIsSeed: false, page: "groups" },
  over || {});
ok("global: 正看全局图 stale=false(数据必须落袋)", SCOPES.global.stale(G()) === false);
ok("global: 已切到分组图 stale=true(旧响应丢弃)",
  SCOPES.global.stale(G({ drawer: { open: true, scope: "group" } })) === true);
ok("global: 面板已关 stale=true", SCOPES.global.stale(G({ drawer: { open: false, scope: "global" } })) === true);

const H = "a".repeat(40);
const T = (over) => Object.assign(
  { drawer: { open: true, tab: "traffic", hash: H }, drawerIsSeed: true, qbTrafficOn: true }, over || {});
ok("torrent: 正看该种子流量页签 stale=false(本次报障点: 恒 true 即卡在加载态)",
  SCOPES.torrent.stale(T(), H) === false);
ok("torrent: 已换目标(hash 不符) stale=true", SCOPES.torrent.stale(T(), "b".repeat(40)) === true);
ok("torrent: 已切到别的页签 stale=true",
  SCOPES.torrent.stale(T({ drawer: { open: true, tab: "general", hash: H } }), H) === true);
ok("torrent: 面板已关 stale=true",
  SCOPES.torrent.stale(T({ drawer: { open: false, tab: "traffic", hash: H } }), H) === true);
ok("torrent: 非种子形态(流量形态) stale=true",
  SCOPES.torrent.stale(T({ drawerIsSeed: false }), H) === true);
ok("torrent: 功能未启用 stale=true", SCOPES.torrent.stale(T({ qbTrafficOn: false }), H) === true);

const K = "Z3JvdXA";  // 分组 key(base64url 形态, 内容无关)
const R = (over) => Object.assign(
  { drawer: { open: true, scope: "group" }, drawerIsTraffic: true, qbGroupKey: K, qbTrafficOn: true },
  over || {});
ok("group: 正看分组流量图 stale=false", SCOPES.group.stale(R(), K) === false);
ok("group: 已换分组 stale=true", SCOPES.group.stale(R(), "other") === true);
ok("group: 面板已关 stale=true", SCOPES.group.stale(R({ drawer: { open: false, scope: "group" } }), K) === true);
ok("group: 已切到全局图 stale=true",
  SCOPES.group.stale(R({ drawer: { open: true, scope: "global" } }), K) === true);

/* active 与 stale 必须**同向**: active=true(该图应显示/可拉)时 stale 必须=false —— 两谓词
 * 若各自漂移(本次根因), 这一条把「图该显示但数据被判过期」的组合直接钉死。 */
ok("同向性: global active 时 stale=false",
  !SCOPES.global.active(G()) || SCOPES.global.stale(G()) === false);
ok("同向性: torrent active 时 stale=false",
  !SCOPES.torrent.active(T()) || SCOPES.torrent.stale(T(), H) === false);
ok("同向性: group active 时 stale=false",
  !SCOPES.group.active(R()) || SCOPES.group.stale(R(), K) === false);

/* ---------- 消费端真跑: _qbLoad 落袋 + loading 复位(用户可见症状的判据) ----------
 * 只钉谓词还不够 —— 真正让用户看到「加载不出来」的是 _qbLoad 里 stale=true 触发的
 * 「数据不落袋 + loading 不复位 + 早退不建图」。这里用真实的方法体配一个假 vm 跑一遍,
 * 断言成功响应确实落进 qbTorrentData/qbGroupData 且 loading 归位(即图会画)。 */
const M = global.window.AQB_QB_TRAFFIC.methods;
const mkVm = (scope) => ({
  qbTrafficOn: true,
  drawer: { open: true, tab: "traffic", hash: H, scope: scope === "torrent" ? undefined : "group" },
  drawerIsSeed: scope === "torrent",
  drawerIsTraffic: scope !== "torrent",
  page: "groups",
  qbGroupKey: K,
  qbTorrentWindow: "24h", qbTorrentLoading: false, qbTorrentData: null, qbTorrentError: "",
  qbGroupWindow: "24h", qbGroupLoading: false, qbGroupData: null, qbGroupError: "",
  api: async () => ({ points: [{ t: 1000, up: 10, dl: 20 }], totals: [{ up: 10, dl: 20 }], limits: [],
    meta: { interval_s: 30 } }),
  $nextTick: (fn) => { if (fn) fn(); },
  _qbChartBuild: () => {}, _qbPollResync: () => {}, _drawerDone: () => {},
});
(async () => {
  const vt = mkVm("torrent");
  await M._qbLoad.call(vt, "torrent");
  ok("落袋: 种子流量响应进入 qbTorrentData(非 null)", vt.qbTorrentData !== null);
  ok("落袋: 种子 loading 已复位(false)", vt.qbTorrentLoading === false);
  ok("落袋: 无错误态", vt.qbTorrentError === "");

  const vg = mkVm("group");
  await M._qbLoad.call(vg, "group");
  ok("落袋: 分组流量响应进入 qbGroupData(非 null)", vg.qbGroupData !== null);
  ok("落袋: 分组 loading 已复位(false)", vg.qbGroupLoading === false);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_frontend_qb_traffic_scope_stale_polarity():
    """流量图三挂点 stale 谓词极性守阵(2026-10-12 修「种子流量图加载不出来」)

    缺陷: W2–W6 抽屉重构的机械改名(``drawer.kind === "seed"`` -> ``drawerIsSeed``)把 torrent 与
    group 两处 ``stale`` 谓词从 ``!(...)`` 写成 ``!!(...)`` —— 取反变双重取反, 语义**整个翻转**:
    恰在本图活跃时判「响应已过期」。后果链: ``_qbLoad`` 里 ``stale=true`` -> 数据不落袋 + loading
    不复位 + 早退不建图 -> ``qbCurPending``(loading && 无数据 && 无错误)恒真 -> 种子「流量」页签
    永远停在「正在加载流量数据…」; 轮询 tick 又被 ``loading`` 卡住 -> 不会自愈。global 挂点未中招
    (仍是 ``!(...)``), 故症状只在种子/分组图。

    为什么既有守阵没拦住: 本文件对 ``_QB_SCOPES`` 的断言全是**源码字符串**级的(字段名/字面量
    在不在), 而 ``!!`` 与 ``!`` 的差别只在运行时语义 —— 静态锚对它天然失明。

    本守阵两层:
    1. **运行时行为**(node 电池, 主判据): 用 ``new Function(源码 + "return _QB_SCOPES;")`` 取出
       作用域表, 对三挂点喂「本图活跃 / 已切走 / 已关闭 / 换目标 / 功能关闭」五类真值上下文, 断言
       ``stale`` 取假/取真与契约一致, 并钉 ``active => stale === false`` 同向性;
    2. **静态极性**(无 node 兜底, 也钉书写形态): 两处 ``stale`` 谓词必须是否定式 ``!(``, ``!!(``
       形态不得回潮(本次根因的书写面)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()

    # 1. 静态极性: stale 谓词是否定式(`!(`), 禁双重取反 `!!(`
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "缺 _QB_SCOPES 作用域表(三挂点单一描述源)"
    sb = "\n" + scopes.group(1)
    for scope in ("torrent", "group"):
        seg = sb.split("\n  %s: {" % scope)[1].split("stale:")[1]
        expr = seg.split("),")[0]
        assert re.search(r"=>\s*!\(t", expr), \
            f"{scope}.stale 必须是否定式 `!(...)`(stale=true 表示响应已过期丢弃; " \
            f"写成 `!!(...)` 语义翻转 -> 图恒不加载), 实测: stale:{expr[:60]}"
        assert "!!(" not in expr, \
            f"{scope}.stale 出现双重取反 `!!(...)`(2026-10-12 事故书写形态: 恰在活跃时判过期)"

    # 2. 运行时行为(node 电池; 无 node 静默跳过, 静态极性仍已生效)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_SCOPE_STALE_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"stale 极性 node 电池跑挂: {proc.stderr.strip()}"
        rep = json.loads(proc.stdout.strip().splitlines()[-1])
        assert rep["failed"] == [], f"stale 极性电池 {rep['ok']}/{rep['total']} 过, 失败: {rep['failed']}"


def test_frontend_qb_traffic_yaxis_and_annotation():
    """流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做)

    用户需求: 纵轴最大值可固定(自动 / 限速+20% / 手动 MiB/s), 峰值超出固定上限时**按峰值显示**;
    附限速虚线 + 缺口斜纹注解层(共享图面, 三挂点 + 经典/所有变体全生效)。钉住四条静默失效面:
    1. 值域语义(_qbYRange 纯函数 node 真跑): 自动 = peak*1.05(无数据回落 1); 固定上限取
       max(cap, peak*1.05) —— **上限只保底不裁剪**(峰值超上限按峰值显示, 用户拍板); 限速三
       作用域同源 = qB 全局限速上下行**较大者**(单点 _qbGlobalLimit -> speedLimitBytes);
    2. 缺口游程(_qbGapRuns node 真跑): 上下行**皆** null 才算缺口(单列 null 防御性不误判);
    3. 持久化粒度 = **三作用域各自独立**(qbYAxisStoreKey 三键, 与窗口档位的「全局单独/组种
       共用」不同); 初值 qbInitialYAxis 只认合法模式 + 正数手动值, 坏值/无存储回落默认;
    4. 接线与三皮肤成对: 切模式/改值/落盘/重排四件 + 建图 y range 走 _qbYRange(_qbYCapOf(scope))
       + draw/drawClear 两钩子画注解层(uPlot 1.6.x ctx 无 transform = 设备像素, 按 uPlot.pxRatio
       换算; 限速线只画落在可视值域内的)+ 模板控件(.qb-seg 三态 + 手动输入 + 生效上限读数) +
       CSS .qb-seg/.qb-yaxis-input 三皮肤成对。
    5. 缺口斜纹**配色**(2026-10-08 修用户报「颜色几乎不可分辨」): 斜纹色原走 tk.grid =
       --hairline(装饰性 1px 发丝线令牌, 实测 alpha 仅 0.05~0.08)再叠 globalAlpha 0.5 ⇒ 有效
       不透明度约 3%, 深浅底上**都**等于没画。守阵 = node 电池实跑 _qbDrawGaps 取真值断言
       strokeStyle 走专用令牌 --qb-gap-hatch 且不叠 alpha 折半 + 令牌量级下界 >=0.15; 静态锚
       钉令牌在三皮肤 + prism 五主题成对定义、亮主题(frost/golden)不得用白色(镜面缺陷)。
       附: 斜纹**几何**经逐条线段比对与代数验证与原式恒等, 故**不设**"位移"类锚(该说法经实测
       证伪, 设了就是假锚)。
    6. 重启缝提示(P4, plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): 判据单点
       _qbSeamHint 纯函数 node 真跑(重启贴近链末 -> 提示, 含「重启后首采即链末桶」的实测帧形态 /
       链到右沿或链确已接续(重启早于链末前一桶)或旧后端无新键 -> null, 边界含尾区起点、右沿与
       左端「链末桶前一桶起点」三点) + computed qbCurSeamHint 消费单点 + drawer.html 提示行(三挂点
       共用正文块一处, 文案单源, 带服务重启时刻锚 fmtTime) + 断线语义不变守阵(null 不连线
       spanGaps:false 与斜纹钩子原样)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 档位/纵轴控件组的唯一实现住在这里(<aq-qb-ctl>)
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()

    # 1. 常量单点(模式清单 / 默认 / 倍率 / MiB 换算)
    assert 'const QB_YAXIS_MODES = ["auto", "limit", "manual"];' in js, "缺 QB_YAXIS_MODES 三态单点"
    assert 'QB_YAXIS_DEFAULT = "auto"' in js, "缺 QB_YAXIS_DEFAULT(初值/坏值回落)"
    assert "QB_YAXIS_LIMIT_FACTOR = 1.2" in js, "缺限速倍率 1.2 单点"
    assert "QB_YAXIS_MIB = 1024 * 1024" in js, "缺手动值 MiB 换算单点"

    # 2. 值域 + 缺口游程 node 真跑(无 node 静默跳过)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_YAXIS_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"纵轴值域/缺口游程 node 电池跑挂: {proc.stderr.strip()}"
        rep = json.loads(proc.stdout.strip().splitlines()[-1])
        assert rep["failed"] == [], f"纵轴/缺口电池 {rep['ok']}/{rep['total']} 过, 失败: {rep['failed']}"

    # 3. 限速来源单点(三作用域同源): qB 全局限速上下行较大者
    lim = re.search(r"_qbGlobalLimit\(\) \{\n(.*?)\n    \},", js, re.S)
    assert lim, "缺 _qbGlobalLimit(全局限速单点)"
    lb = lim.group(1)
    assert "this.speedLimitBytes" in lb, "_qbGlobalLimit 必须取 speedLimitBytes 单点(与状态栏/速度染色同源)"
    # 2026-10-08 版式改后常驻说明区退役; D4 文案挂在统计栏悬浮说明单点(qbCurSummaryHint)
    assert "限速虚线 = 当时生效的 qB 全局限速" in js and "记录起点前不显示" in js, \
        "缺 D4 文案(限速线取值口径 + 记录起点前不显示, qbCurSummaryHint 单点)"
    assert "up" in lb and "down" in lb and "best" in lb, \
        "全局限速必须取上下行**较大者**(纵轴上下行共用一条, 取大者两条曲线都落在上限内)"

    # 4. 上限派生单点: limit = 全局限速×1.2 / manual = MiB 换算 / auto = 0(不固定)
    cap = re.search(r"_qbYCapOf\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert cap, "缺 _qbYCapOf(固定上限派生单点)"
    cb = cap.group(1)
    assert 'y.mode === "limit"' in cb and "* QB_YAXIS_LIMIT_FACTOR" in cb, "limit 模式必须 = 全局限速 ×1.2"
    assert 'y.mode === "manual"' in cb and "* QB_YAXIS_MIB" in cb, "manual 模式必须按 MiB 换算"

    # 5. 建图接线: y range 走纯函数 + 两钩子画注解层(共享图面)
    assert "y: { range: (u, dmin, dmax) => _qbYRange(dmax, this._qbYCapOf(scope)) }" in js, \
        "建图 y range 未接 _qbYRange/_qbYCapOf(固定上限不生效)"
    assert "drawClear: [(u) => this._qbDrawGaps(u, tk)]" in js, "缺缺口斜纹 drawClear 钩子(画在系列之下)"
    assert "draw: [(u) => this._qbDrawLimits(u, tk)]" in js, "缺限速虚线 draw 钩子(画在系列之上)"

    # 6. 重启缝提示(P4, plan 26-10-15-0829): 判据单点 + computed 消费单点 + 模板提示行
    #    (node 真跑在上面第 2 段电池里; 这里钉接线与文案单源)
    assert js.count("function _qbSeamHint") == 1, "缺/多 _qbSeamHint 判据定义(重启缝 vs 停机洞区分判据必须单点)"
    # 左端口径活性锚(issue 26-10-16-0954): 左端必须为「链末桶前一桶起点」而非链末桶覆盖端 —— 旧口径
    # 把「重启后首采已入账」形态静默漏判; 整行匹配, 改口径须同步 node 电池(判据语义由电池钉住)
    assert "if (started < chainPrevStart || started > rightEdge) return null;" in js, \
        "缺 重启缝判据左端行(chainPrevStart = 链末桶前一桶起点; 修订见 issue 26-10-16-0954)"
    seam_cmp = re.search(r"qbCurSeamHint\(\) \{\n(.*?)\n    \},", js, re.S)
    assert seam_cmp and "_qbSeamHint(d.points" in seam_cmp.group(1), \
        "缺 qbCurSeamHint computed(模板消费单点, 必须经 _qbSeamHint 判据)"
    assert 'v-if="qbCurSeamHint"' in drawer_tpl and "qb-seam" in drawer_tpl, \
        "drawer.html 缺重启缝提示行(数据接缝中, 三挂点共用正文块)"
    assert drawer_tpl.count("数据接缝中") == 1, "接缝文案必须单源(只此一处)"
    assert "fmtTime(qbCurSeamHint.startedAt)" in drawer_tpl, "接缝提示必须带服务重启时刻锚(fmtTime)"
    # 断线语义不变(P4 纪律): null 不连线与斜纹钩子原样, 提示只是追加状态行
    assert js.count("spanGaps: false") == 2, "断线语义不得变(spanGaps:false 上下载两系列都在)"
    for member in ("_qbCanvasScale(u)", "_qbDrawGaps(u, tk)", "_qbDrawLimits(u, tk)"):
        assert member in js, f"缺画布注解层成员 {member}"
    assert "uPlot.pxRatio" in js, "画布注解层必须按 uPlot.pxRatio 换算设备像素(uPlot ctx 无 transform)"
    dl = re.search(r"_qbDrawLimits\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert dl, "缺 _qbDrawLimits(限速虚线注解)"
    dlb = dl.group(1)
    # D4(plan 26-10-12-0535)分段化: 取值改图记录上的事件序列(不再读 speedLimitBytes 单值),
    # 段几何走纯函数, 可见性逐段(0 < v < ymax), 末段延伸到图右沿
    assert "u._qbLimits" in dlb, "_qbDrawLimits 必须取图记录上的限速事件序列(u._qbLimits, D4 分段)"
    assert "speedLimitBytes" not in dlb, "_qbDrawLimits 不得再读单点当前值(旧「单值画满整窗」回潮)"
    assert "_qbLimitSegs(" in dlb, "限速段必须走 _qbLimitSegs 纯函数(段几何 node 电池同源)"
    assert "seg.up < ymax" in dlb and "seg.down < ymax" in dlb, \
        "限速虚线可见性必须逐段判(每段每方向 0 < v < ymax)"
    assert "seg.up > 0" in dlb and "seg.down > 0" in dlb, "0(不限速)/缺值段不画"
    # 快路/建图两路都要把 limits 暂存在图记录上(否则限速变更要等整图重建才可见)
    assert js.count("prev._qbLimits =") == 1 and js.count("u._qbLimits =") == 1, \
        "limits 暂存必须同时接在 setData 快路(prev._qbLimits)与整图重建(u._qbLimits)两路"
    # D7: 悬停读数走纯函数 _qbLimitAt + 模板两支(正常/缺口)都接当时限速行
    assert "_qbLimitAt(d.limits || [], ts)" in js, "悬停读数必须走 _qbLimitAt(当时值, D7)"
    assert drawer_tpl.count('v-if="qbCurHover.lim"') == 2, \
        "当时限速行必须在正常/缺口两支 tooltip 各接一处(限速是时间真值, 缺口也读)"
    assert 'class="h-limit"' in drawer_tpl, "当时限速行缺 h-limit 类(样式挂点)"

    # 5b. 缺口斜纹**配色 + 几何**守阵(2026-10-08 两轮: 先修「颜色几乎不可分辨」, 再修「未落到
    # 正确区域 / 倾斜超出范围」)
    # 配色根因: 斜纹色原走 tk.grid = --hairline(装饰性 1px 发丝线令牌, 实测 alpha 仅 0.05~0.08),
    # 再叠 globalAlpha 0.5 ⇒ 有效不透明度约 3%, 深/亮底色上**都**等于没画。修法 = 专用高对比
    # 令牌 --qb-gap-hatch + 去掉多余的 globalAlpha 折半。
    # 几何根因(第二轮, 首轮曾误判为"颜色不可见导致无法判读落点"): 斜纹原只按底端 x 扫
    # [xa-H, xb+H] 再让外层 clip 收到**整个绘图区** —— 45 度线段水平跨度恒为 H, 并集是"宽 H 的
    # **斜向平行四边形**"(左右边界皆斜边), 缺口右段下半留白、左段上半越界到缺口左侧, 即用户报
    # 「未落到正确区域, 倾斜超出范围」。修法 = **逐 run 追加一次 clip 到缺口矩形**(见 _qbDrawGaps
    # 内「几何硬约束」注释), 斜纹被裁成以缺口区间为左右竖直边的竖矩形。
    gp = re.search(r"_qbDrawGaps\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert gp, "缺 _qbDrawGaps(缺口斜纹注解)"
    gb = gp.group(1)
    assert "ctx.strokeStyle = tk.gap || tk.grid;" in gb, \
        "缺口斜纹色必须走专用令牌 tk.gap(回退 tk.grid 兜底), 不得直用极低 alpha 的 tk.grid"
    assert "ctx.globalAlpha = 1;" in gb, \
        "缺口斜纹不得再叠 globalAlpha <1(--hairline 已是 0.055, 再砍半等于不可见)"
    assert "ctx.moveTo(x - H, T + H)" in gb and "ctx.lineTo(x, T)" in gb, \
        "斜纹线段必须为 (x-H, T+H) -> (x, T)(45 度, 右下角在 x)"
    assert "ctx.rect(L, T, W, H)" in gb and "ctx.clip()" in gb, \
        "缺口斜纹必须裁剪在绘图区内(两端超出部分不得越 y 轴/时间轴)"
    # 几何硬约束: 逐 run 裁到**缺口矩形** [xa, xb] x [T, T+H](把斜带裁成竖矩形)
    assert "ctx.rect(xa, T, xb - xa, H)" in gb, \
        "缺口斜纹必须逐 run 裁到缺口矩形 ctx.rect(xa, T, xb-xa, H) —— 否则 45 度斜带铺成" \
        "平行四边形: 缺口右段留白、斜边越出缺口带(用户报「未落到正确区域/倾斜超出范围」)"
    assert "if (!(xb > xa)) continue;" in gb, \
        "缺口宽度非正(退化 run)必须跳过, 不得画零宽/负宽矩形"
    tkb = re.search(r"_qbChartTokens\(\) \{\n(.*?)\n    \},", js, re.S)
    assert tkb, "缺 _qbChartTokens(建图令牌单点)"
    assert 'gap: pick("--qb-gap-hatch"' in tkb.group(1), \
        "建图令牌必须产出 gap = --qb-gap-hatch(缺口斜纹专用高对比令牌)"
    # 令牌三皮肤 + prism 五主题必须各自定义(缺一个就是那套皮肤下斜纹不可见)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas"),
        (_ui_css_aggregate("console"), "console"),
        (_ui_css_aggregate("prism"), "prism"),
    ):
        assert "--qb-gap-hatch:" in css, f"{name} 皮肤缺 --qb-gap-hatch 令牌(缺口斜纹不可见)"
    for theme in ("ocean", "galaxy", "orbit", "frost", "golden"):
        tf = os.path.join(STATIC_ROOT, "prism", "css", "themes", f"{theme}.css")
        tt = open(tf, encoding="utf-8").read()
        assert "--qb-gap-hatch:" in tt, f"prism 主题 {theme} 缺 --qb-gap-hatch 令牌"
        # 亮主题必须用深墨色而非白色(白纹在白底/米底上等于无 —— 与深主题同式的镜面缺陷)
        if theme in ("frost", "golden"):
            hx = re.search(r"--qb-gap-hatch:\s*([^;]+);", tt).group(1)
            assert "255, 255, 255" not in hx, f"亮主题 {theme} 的斜纹色不得用白色(底纹不可见)"

    # 6. 持久化: 三作用域各自独立 + 键单点 + 初值校验 + 落盘吞异常 + 切档重排(不重取数)
    for scope, key in (
        ("global", "autoqb.ui.qbYAxisGlobal"), ("torrent", "autoqb.ui.qbYAxisTorrent"),
        ("group", "autoqb.ui.qbYAxisGroup")
    ):
        assert f'{scope}: "{key}"' in js, f"缺 {scope} 纵轴存储键(三作用域各自独立一份)"
    yk = re.search(r"function qbYAxisStoreKey\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert yk and "QB_YAXIS_STORE_KEYS[scope]" in yk.group(1), "qbYAxisStoreKey 必须按 scope 单点分派"
    yi = re.search(r"function qbInitialYAxis\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert yi, "缺 qbInitialYAxis(纵轴初值读取)"
    yib = yi.group(1)
    assert "localStorage.getItem(qbYAxisStoreKey(scope))" in yib and "QB_YAXIS_MODES.includes(v.mode)" in yib, \
        "初值必须读存储且只认合法模式(坏值回落默认)"
    assert "catch" in yib, "初值读取失败必须吞异常回落默认"
    ps = re.search(r"persistQbYAxis\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert ps and "localStorage.setItem(qbYAxisStoreKey(scope)" in ps.group(1) and "catch" in ps.group(1), \
        "persistQbYAxis 必须写键单点且吞写入异常(与 persistQbWindow 同纪律)"
    for sig in ("qbSetYAxisMode(mode)", "qbSetYAxisManual(v)"):
        blk = re.search(rf"{re.escape(sig)} \{{\n(.*?)\n    \}},", js, re.S)
        assert blk, f"缺 {sig}(纵轴切换入口)"
        bd = blk.group(1)
        assert "this.persistQbYAxis(s);" in bd and "this._qbChartRescale(s);" in bd, \
            f"{sig} 必须落盘 + 立即重排 y 轴(不改数据/不重建图, 重取数等于白拉一发)"
    rs = re.search(r"_qbChartRescale\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert rs and "u.setData([u.data[0], u.data[1], u.data[2]])" in rs.group(1), \
        "_qbChartRescale 必须走 setData 重算 scale(重跑 range 与 draw 钩子), 不重建图"
    # 限速随主轮询变化重排(mounted 注册; 全局 mixin 必须先按 this.drawer 守卫剔除假实例)
    assert "this._qbLimitUnwatch = this.$watch(() => this._qbGlobalLimit()" in js, \
        "缺限速变化重排 watcher(长窗轮询可夹到 600s, 不重排则固定上限迟迟不生效)"
    assert "if (!this.drawer) return;" in js, \
        "mounted 注册必须先按 this.drawer 守卫剔除 BaseTransition 假实例(全局 mixin 会注入它)"

    # 7. 作用域表三挂点各持 yaxis 字段(单一描述源)
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "缺 _QB_SCOPES 作用域表"
    sb = scopes.group(1)
    for field in ('yaxis: "qbHistYAxis"', 'yaxis: "qbTorrentYAxis"', 'yaxis: "qbGroupYAxis"'):
        assert field in sb, f"_QB_SCOPES 缺 {field}(三挂点各自独立纵轴字段)"

    # 8. state.js 三字段按 scope 取初值 + computed 单点
    for field in (
        'qbHistYAxis: qbInitialYAxis("global")', 'qbTorrentYAxis: qbInitialYAxis("torrent")',
        'qbGroupYAxis: qbInitialYAxis("group")'
    ):
        assert field in state_js, f"state.js 缺 {field}(根选项显式建字段)"
    for comp in ("qbCurYAxis()", "qbYAxisMode()", "qbYAxisManual()"):
        assert comp in js, f"缺纵轴 computed {comp}"
    # 2026-10-16(用户动议): 工具条上限读数 qbYAxisCapText(「上限 …(全局限速 ×1.2)」)随 UI 移除,
    # computed 退役不得回潮(图面自解释, 不再要常驻读数)。
    assert "qbYAxisCapText" not in js, "qbYAxisCapText 已随 2026-10-16 上限字样移除退役, 不得回潮"

    # 9. 模板控件(2026-10-16 版式改: 三挂点统一落图下统计栏 .qb-statctl, 头部不再挂控件)
    # W3(计划 26-10-11-2106): 控件组收进 <aq-qb-ctl>(**唯一实现**), 故旧口径
    # 「三态 × 2 处 = 6」改为「实现里三态各一(3) + drawer.html 零复写 + 唯一挂点接它」——
    # 覆盖强度不降反升(单点强于同源): 谁把按钮抄回 drawer.html, 下面的 == 0 与挂点断言同时判红。
    # 26-10-20-2231(R23-B-17): 纵轴三态改 <aq-seg> —— 模板不再有 3 个按钮, 判据换成
    # 「模板一处接 qbYAxisTabs + 三档合法值与文案在 JS 单点各一份」: 覆盖强度不降(谁把档位
    # 写回模板, 下面的 count == 0 与 qbYAxisTabs 投影断言同时判红), 且「加一档要改几处」从
    # 3 处(清单/文案/模板)降到 2 处(清单/文案, 同域相邻)。
    assert head_tpl.count("qbSetYAxisMode(") == 0, \
        "<aq-qb-ctl> 不应手写纵轴三态按钮(应交 <aq-seg>, 清单单点在 qbYAxisTabs)"
    assert ':items="$root.qbYAxisTabs"' in head_tpl and ':on-pick="$root.qbSetYAxisMode"' in head_tpl, \
        "<aq-qb-ctl> 纵轴三态必须吃 qbYAxisTabs + 回调 qbSetYAxisMode"
    assert re.search(r"qbYAxisTabs\(\) \{\n\s*return QB_YAXIS_MODES\.map\(", js), \
        "qbYAxisTabs 必须投影自 QB_YAXIS_MODES(合法值仍只有一份清单)"
    assert drawer_tpl.count("qbSetYAxisMode(") == 0, \
        "drawer.html 仍手写纵轴按钮(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    traffic_call = re.search(r'<aq-drawer-head v-if="drawerIsTraffic"[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert traffic_call and '<aq-qb-ctl>' not in traffic_call.group(1), \
        "纵轴控件不得落在流量形态头部内(2026-10-16 版式改: 三挂点统一落图下统计栏)"
    assert 'class="qb-tools"' in head_tpl and 'class="qb-seg"' in head_tpl, \
        "<aq-qb-ctl> 缺纵轴控件本体(.qb-tools/.qb-seg)"
    # 9b. **结构**守阵(数类名探不到 wrapper): <aq-qb-ctl> 必须恰两根(.qb-tabs / .qb-tools), 无 wrapper。
    # 三皮肤 CSS 的 `.qb-statctl > .qb-tabs` / `.qb-statctl > .qb-tools` 与
    # `.hist-summary > .qb-statctl` 全是**直接子选择器**(2026-10-16 起统计栏是唯一挂点,
    # 头部侧的 `.drawer-head > .qb-*` 选择器已随挂点退役删除) —— 片段被包一层
    # (任何理由的容器)即全部静默失配(类名 count 不变, 观感错版)。Vue 3 片段不留 wrapper 元素,
    # 唯二会破坏它的就是源模板里自己写一个, 故此处在源文本上钉根数。
    ctl_roots = _tpl_top_level_tags(_tpl_body(head_tpl, "tpl-aq-qb-ctl"))
    assert len(ctl_roots) == 2, (
        f"<aq-qb-ctl> 必须是**多根**片段(恰两根), 实测 {len(ctl_roots)} 根 —— "
        "包 wrapper 会隔开 .qb-statctl > .qb-tabs 这些直接子选择器, "
        "三皮肤下控件错版且无报错(静默失效)"
    )
    assert [t for t, _ in ctl_roots] == ["div", "div"], \
        "<aq-qb-ctl> 两个根必须是 div(.qb-tabs 档位 / .qb-tools 纵轴)"
    ctl_classes = [a.get("class") for _, a in ctl_roots]
    assert ctl_classes == ["qb-tabs", "qb-tools"], \
        f"<aq-qb-ctl> 两根的类必须依序为 qb-tabs/qb-tools(直接子选择器按类名命中), 实测 {ctl_classes}"
    # 头部壳片段同理: 恰一个根 <header class="drawer-head">(两形态共用一处; 再长出第二个 = 复写回潮)
    head_roots = _tpl_top_level_tags(_tpl_body(head_tpl, "tpl-aq-drawer-head"))
    assert len(head_roots) == 1 and head_roots[0][0] == "header" \
        and head_roots[0][1].get("class") == "drawer-head", \
        f"<aq-drawer-head> 必须恰一个根 <header class=\"drawer-head\">(两形态共用的唯一头部壳), 实测 {head_roots}"
    assert "v-if=\"$root.qbYAxisMode === 'manual'\"" in head_tpl \
        and "$root.qbSetYAxisManual($event.target.value)" in head_tpl, \
        "<aq-qb-ctl> 手动模式必须给输入框且 @change 走 qbSetYAxisManual(经 $root 回调根实例)"
    # 2026-10-16(用户动议): 生效上限读数(qb-tools-hint / qbYAxisCapText)已随 UI 移除, 不得回潮。
    assert "qb-tools-hint" not in head_tpl and "$root.qbYAxisCapText" not in head_tpl, \
        "纵轴工具条的上限读数字样已移除(2026-10-16), 不得回潮"
    # 2026-10-09 第 2 轮: 种子「流量」页签同款控件组改落图下统计栏(.qb-statctl; 2026-10-16 起为唯一挂点)
    stat_hdr = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('种子详情形态正文(五页签)')]
    assert 'class="qb-statctl"' in stat_hdr and '<aq-qb-ctl></aq-qb-ctl>' in stat_hdr, \
        "纵轴/档位控件组必须落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮; 2026-10-16 起为唯一挂点; W3 起经 <aq-qb-ctl>)"

    # 10. CSS 三皮肤成对(纵轴控件 + 图下统计栏控件组版式)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合"),
        (_ui_css_aggregate("console"), "console css 聚合"),
        (_ui_css_aggregate("prism"), "prism css 聚合"),
    ):
        for rule in (
            ".qb-tools {",
            ".qb-seg button.active",
            ".qb-yaxis-input",
            ".hist-summary > .qb-statctl {",
        ):
            assert rule in css, f"{name} 缺 {rule}(纵轴控件/图下统计栏控件组三套 UI 必须成对改)"
        # 2026-10-16(用户动议「统计栏未对齐」): 统计栏 .hist-summary 各子项必须**垂直居中**。
        # 判据: flex 默认 align-items:stretch 把纯文本读数(「窗口 N 桶」/上下载累计)拉到与
        # 控件组同高、文字贴顶(实测比中线高 3.7px), 而图例(.hs-leg)与控件组(.qb-statctl)
        # 自带 align-items:center 使内容居中 —— 三族文字因此落成三条线, 真浏览器量布局才现形
        # (类名/结构断言全绿)。三皮肤成对钉住, 只改一处即判红。
        assert re.search(r"\.hist-summary\s*\{[^}]*align-items:\s*center", css), \
            f"{name} 的 .hist-summary 缺 align-items:center(统计栏子项错行: 文本贴顶 vs 图例/控件居中)"


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


_NODE_REANNOUNCE_GATE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // decorate.js(判据单点)
eval(fs.readFileSync(process.argv[2], "utf8"));   // delete_flow.js(删除链, issue 26-10-17-1703)
const M = window.AQB_DECORATE.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
/* 判定单点只读入参, 不依赖 this --------------------------------------------------- */
ok("停止(stoppedDL) 判非活跃", M.reannounceBlocked({ state: "stoppedDL" }) === true);
ok("暂停(pausedUP) 判非活跃", M.reannounceBlocked({ state: "pausedUP" }) === true);
/* 排队是"必须读 state"的理由: qbittorrent-api 把 queuedDL/UP 归进 is_downloading/is_uploading,
 * 其 kind 落成 downloading/seeding —— 单看 kind 会把它当活跃放行 */
ok("排队(queuedDL) 判非活跃", M.reannounceBlocked({ state: "queuedDL" }) === true);
ok("排队(queuedUP) 判非活跃", M.reannounceBlocked({ state: "queuedUP" }) === true);
ok("queuedDL 且 kind=downloading 仍拦(不误放行)", M.reannounceBlocked({ state: "queuedDL", kind: "downloading" }) === true);
ok("校验中(checkingUP) 判非活跃", M.reannounceBlocked({ state: "checkingUP" }) === true);
ok("校验中(checkingResumeData) 判非活跃", M.reannounceBlocked({ state: "checkingResumeData" }) === true);
ok("错误(error) 判非活跃", M.reannounceBlocked({ state: "error" }) === true);
ok("文件缺失(missingFiles) 判非活跃", M.reannounceBlocked({ state: "missingFiles" }) === true);
ok("做种(stalledUP) 可汇报", M.reannounceBlocked({ state: "stalledUP" }) === false);
ok("做种(uploading) 可汇报", M.reannounceBlocked({ state: "uploading" }) === false);
ok("下载(downloading) 可汇报", M.reannounceBlocked({ state: "downloading" }) === false);
ok("调度中(unknown) 可汇报(非暂停非校验非错误)", M.reannounceBlocked({ state: "unknown" }) === false);
/* state 缺失时按 kind 三档兜底(老版本/异常行) */
ok("缺 state 回落 kind=paused", M.reannounceBlocked({ kind: "paused" }) === true);
ok("缺 state 回落 kind=checking", M.reannounceBlocked({ kind: "checking" }) === true);
ok("缺 state 回落 kind=error", M.reannounceBlocked({ kind: "error" }) === true);
ok("缺 state 回落 kind=seeding 放行", M.reannounceBlocked({ kind: "seeding" }) === false);
ok("空行/null 不拦(不误伤)", M.reannounceBlocked(null) === false && M.reannounceBlocked({}) === false);
/* 多目标: 任一活跃即可用(qB oneCanForceReannounce 同口径) ------------------------ */
const ctx = { reannounceBlocked: M.reannounceBlocked, reannounceBlockText: M.reannounceBlockText };
const V = (rows) => M._reannounceVerdict.call(ctx, rows);
ok("全非活跃 -> 拦", V([{ state: "pausedUP" }, { state: "queuedDL" }]).ok === false);
ok("全非活跃 -> title 带原因与「无法强制汇报」", /无法强制重新汇报/.test(V([{ state: "pausedUP" }]).title));
ok("全非活跃(多目标) -> title 报目标数", /2 个目标/.test(V([{ state: "pausedUP" }, { state: "error" }]).title));
ok("混合(含一个活跃) -> 放行", V([{ state: "pausedUP" }, { state: "uploading" }]).ok === true);
ok("可汇报时 title 为空串(空串 title = 清除旧提示的通道)", V([{ state: "uploading" }]).title === "");
ok("空集 -> 不误拦(目标已消失时行为与上线前一致)", V([]).ok === true);
/* 投递计划: 放行之后"发给谁"(reannouncePlan 单点) ---------------------------------------------
 * 闸门判"允不允许"(集合级全有全无, 与 qB oneCanForceReannounce 一致), 计划判"发给谁"。
 * 混选放行后若照集合全量投递, qB 引擎对非活跃的静默空转而我们的确认层会白等窗口报「未确认」。 */
const PGROUPS = {
  G1: { members: [{ hash: "A", state: "uploading" }, { hash: "B", state: "queuedDL" }, { hash: "C", state: "pausedUP" }] },
  G2: { members: [{ hash: "A", state: "uploading" }] },   // 成员与 hashes 重叠
  G3: { members: [] },                                    // 成员被清空的罕见态
};
const PROWS = [{ hash: "A", state: "uploading" }, { hash: "D", state: "checkingUP" }];
const PCTX = {
  reannounceBlocked: M.reannounceBlocked,
  _findGroup: (k) => PGROUPS[k] || null,
  memberByHash: new Map(PROWS.map((r) => [r.hash, r])),
};
const P = (t) => M.reannouncePlan.call(PCTX, t);
const p1 = P({ keys: ["G1"], hashes: [] });
ok("组目标混合 -> 只投活跃成员(hash 展开)", p1.keys.length === 0 && p1.hashes.join(",") === "A");
ok("组目标混合 -> 跳过数 = 非活跃成员数", p1.skipped === 2);
ok("组目标全活跃 -> 零跳过", P({ keys: ["G2"], hashes: [] }).skipped === 0);
const p2 = P({ keys: ["GONE"], hashes: [] });
ok("组解析不出 -> 原样交回组端点(不静默丢目标)", p2.keys.join(",") === "GONE" && p2.hashes.length === 0);
const p3 = P({ keys: [], hashes: ["A", "D", "GONE"] });
ok("单种: 活跃投递", p3.hashes.indexOf("A") >= 0);
ok("单种: 非活跃收敛掉并计数", p3.hashes.indexOf("D") < 0 && p3.skipped === 1);
ok("单种: hash 解析不出照发(不误丢, 与闸门「不误拦」同口径)", p3.hashes.indexOf("GONE") >= 0);
ok("组内成员与 hashes 重叠只投一次(去重按 hash)", P({ keys: ["G2"], hashes: ["A"] }).hashes.length === 1);
const p5 = P({ keys: ["G3"], hashes: [] });
ok("空成员组 -> 计划为空(调用方据此收口, 不得报「成功 0 个目标」)",
  p5.keys.length === 0 && p5.hashes.length === 0 && p5.skipped === 0);
ok("空入参 -> 空计划(不抛)", P({}).hashes.length === 0 && P(null).skipped === 0);
/* 删除链(issue 26-10-17-1703): 闸门层 _deleteReannounceGate + _reannounceAll 的 skip 桶 ----------
 * 删除链是「一条'不允许'必须接全部入口」清单里唯一漏接的入口: 全非活跃时复选框禁用+取消勾选,
 * 混选只报跳过数; 回执侧非活跃 warn 降级为 skip(D6 竞态兜底)不挡删除, 真 warn/error 不放行。 */
const DF = window.AQB_DELETE.methods;
const DG = { reannounceBlocked: M.reannounceBlocked };
const G = (rows) => DF._deleteReannounceGate.call(DG, rows);
ok("删除闸门: 全非活跃 -> 禁用 + title 给原因", (() => { const g = G([{ state: "pausedDL" }, { state: "queuedDL" }]); return g.disabled === true && /非活跃/.test(g.title) && g.note === ""; })());
ok("删除闸门: 混选 -> 不禁用 + pill 报跳过数", (() => { const g = G([{ state: "pausedDL" }, { state: "uploading" }]); return g.disabled === false && g.note === "1 个非活跃目标将跳过"; })());
ok("删除闸门: 全活跃 -> 不禁用无说明", (() => { const g = G([{ state: "uploading" }, { state: "stalledUP" }]); return g.disabled === false && g.note === ""; })());
ok("删除闸门: 解析不出(空成员) -> 不误拦", G([]).disabled === false && G(null).note === "");
ok("删除闸门: 缺 state 回落 kind 兜底(paused 同族)", G([{ kind: "paused" }]).disabled === true);
const RA_BASE = { toast: () => 1, _finishToast: () => {}, api: async (p) => ({ cmd_id: p }) };
const INACTIVE_WARN = { ok: false, status: "warn", error: "未确认: 种子非活跃(暂停/停止/排队/校验中/错误), qB 静默忽略强制汇报" };
const DEFER_WARN = { ok: false, status: "warn", error: "未确认: 已受理, 推迟中" };
const ra = (waitImpl, jobs, skipped) => DF._reannounceAll.call({ ...RA_BASE, waitCmd: waitImpl }, jobs, "标签", skipped);
(async () => {
  ok("回执侧非活跃 warn -> 降级 skip, 放行删除", await ra(async () => INACTIVE_WARN, ["/api/torrents/A/reannounce"]) === true);
  ok("组内均非活跃 warn(另一种文案) -> 同样降级", await ra(async () => ({ ...INACTIVE_WARN, error: "未确认: 组内 2 个种子均非活跃, 已跳过" }), ["/api/groups/G/reannounce"]) === true);
  ok("推迟中 warn -> 仍不放行删除(H&R 保守口径不借修 bug 放宽)", await ra(async () => DEFER_WARN, ["/api/torrents/A/reannounce"]) === false);
  ok("error 回执 -> 不放行删除", await ra(async () => ({ ok: false, status: "error", error: "tracker 拒绝" }), ["/api/torrents/A/reannounce"]) === false);
  ok("投递失败(rejected) -> 不放行删除", await ra(async () => { throw new Error("boom"); }, ["/api/torrents/A/reannounce"]) === false);
  ok("全 ok -> 放行删除", await ra(async () => ({ ok: true }), ["/api/torrents/A/reannounce"]) === true);
  ok("空 jobs -> 直接放行(不抛)", await ra(async () => ({ ok: true }), []) === true);
process.stdout.write(JSON.stringify({
  ok: checks.filter((c) => c[1]).length,
  total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}) + "\n");
})();
"""

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


def test_frontend_reannounce_inactive_gate_wiring():
    """非活跃种子禁强制汇报(qB 口径)四入口接线守阵(2026-10-10) ——

    qB 的右键 "Force reannounce" 只在种子活跃时可用(commit aa189a7 关闭 issue #12080:
    isPaused/isChecking/isQueued 时 `setEnabled(false)`, tooltip 原文 "Can not force
    reannounce if torrent is Paused/Queued/Errored/Checking"); 本项目沿用同一判据
    (暂停/停止 · 排队 · 校验中 · 错误/文件丢失 · 搬迁中)。qB 原始 state 串必须全覆盖 —— kind 只有
    7 档, queuedDL/queuedUP 被 qbittorrent-api 归进 is_downloading/is_uploading ⇒ 落成
    downloading/seeding, 单看 kind 会把排队种子当活跃放行。

    四个面逐项钉住(键盘与详情面板是右键之外的两条绕行路径, 少接一处即形同虚设):
      ①判定单点 decorate.js:两张表 + 读 state + 多目标任一活跃即可用(qB oneCanForceReannounce);
      ②右键菜单四支的置灰钩子成对(W3 计划 26-10-20-0024 起在注册表 ctx_menu.js:
         四支各一条 dyn: "reannounce" + ctxRenderItem 求值单点, 模板统一消费 it.gated/it.title);
      ③行为层:_actCore 的 reannounce 前置(早于乐观补丁/POST)+ _kbAct 的先拦后确认;
      ④详情面板:04/05/06 重报钮挂 drawerReannounceGate() + 各变体 .is-gated CSS + torrentCmd 兜底;
      ⑤投递收敛:reannouncePlan 单点 + 跳过文案 + 空投递收口 + 前后端判据表逐项同表;
      ⑥删除链(issue 26-10-17-1703): _deleteFlow 按计划收敛 + 全非活跃闸门禁用复选框(popovers
         is-gated/标题/点击短路三件 + CSS 成套)+ _reannounceAll 的 skip 桶(非活跃 warn 降级)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    deco = open(os.path.join(shared, "decorate.js"), encoding="utf-8").read()
    cmds = open(os.path.join(shared, "commands.js"), encoding="utf-8").read()
    kb = open(os.path.join(shared, "shortcuts.js"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # ① 判定单点: qB 原始 state 串全覆盖 + 读 state(不是 kind)+ 多目标"任一活跃即可用"
    for st in (
        "pausedDL",
        "pausedUP",
        "stoppedDL",
        "stoppedUP",
        "queuedDL",
        "queuedUP",
        "checkingDL",
        "checkingUP",
        "checkingResumeData",
        "error",
        "missingFiles",
        "moving",  # 搬迁中: qB moving 期间 peer 传输让位给磁盘搬运, 汇报换不回 peer
    ):
        assert st + ":" in deco, f"decorate.js 非活跃状态集缺 qB 状态 {st}(qB 口径漏项)"
    assert "REANNOUNCE_BLOCKED_STATES" in deco and "REANNOUNCE_BLOCKED_KINDS" in deco, \
        "decorate.js 缺非活跃判定单点(state 原文表 + kind 兜底表)"
    assert "m.state" in deco, "判定未读 qB 原始 state —— 单看 kind 判不出排队种子(会误放行)"
    assert re.search(r"rows\.some\(\(r\) => !this\.reannounceBlocked\(r\)\)", deco), \
        "多目标判据未按「任一活跃即可用」写(qB oneCanForceReannounce 口径)"

    # ② 右键菜单四支: 置灰钩子逐支成对。W3(计划 26-10-20-0024)起比对面搬到注册表 ——
    #    四支各一条 dyn: "reannounce", 求值单点在 ctx_menu.js ctxRenderItem; 模板统一
    #    :class/:title 消费 it.gated/it.title(逐项直写时期是四段重复的 reannounceMenuGate() 调用)
    reg = open(os.path.join(shared, "ctx_menu.js"), encoding="utf-8").read()
    assert reg.count('dyn: "reannounce"') == 4, \
        "ctx_menu.js 四支(多选/整集/单种子/单组)的强制汇报项未全部挂 dyn: reannounce"
    assert "item.gated = !gate.ok" in reg and 'item.title = gate.title || ""' in reg, \
        "ctx_menu.js ctxRenderItem 缺置灰/title 求值单点(模板只消费 it.gated/it.title)"
    assert "'is-gated': it.gated" in menus and ':title="it.title"' in menus, \
        "ctx-menus.html 菜单项未统一消费置灰态与 title 通道(用户看不到为什么变灰)"
    for act in (
        'vm.ctxAct("reannounce")', 'vm.actEpisode("reannounce")', 'vm.actTorrent("reannounce")', 'vm.act("reannounce")'
    ):
        assert act in reg, f"ctx_menu.js 缺强制汇报入口 {act}(入口被改名? 判据面要同步)"
    assert "REANNOUNCE_BLOCKED_STATES" in reg, \
        "ctx_menu.js 缺 qB 判据说明注释(口径单点指向 decorate.js)"

    # ③ 行为层: _actCore 前置闸门(早于乐观补丁) + _kbAct 先拦后确认
    assert "async _guardReannounce(t)" in cmds or "_guardReannounce(t) {" in cmds, \
        "commands.js 缺 _guardReannounce 闸门"
    assert 'if (action === "reannounce" && !this._guardReannounce({ keys, hashes })) return;' in cmds, \
        "_actCore 未对 reannounce 前置闸门(组/单种/整集/批量会绕过去)"
    core_at = cmds.index("async _actCore(action")
    assert cmds.index("_guardReannounce({ keys, hashes })", core_at) < \
        cmds.index("this.applyOptimistic(optHashes, action)", core_at), \
        "_actCore 的强制汇报闸门落在乐观补丁之后(会先贴补丁再拒绝)"
    kb_body = re.search(r"async _kbAct\(action\) \{(.*?)\n  \},", kb, re.S)
    assert kb_body, "shortcuts.js 找不到 _kbAct"
    kb_txt = kb_body.group(1)
    assert "_guardReannounce(" in kb_txt, "键盘路径未接强制汇报闸门(非活跃目标仍能 Shift+A 绕过)"
    assert kb_txt.index("_guardReannounce(") < kb_txt.index("confirmDialog("), \
        "键盘路径必须先拦再确认(先问「确定?」再回「不行」是坏体感)"

    # ④ 详情面板: 三变体的重报钮 + 各变体 .is-gated CSS + torrentCmd 兜底(W7 恢复注: 变体层
    #    随 W5 越权退役曾一并退场, W7 恢复后该断言面原样回归; U3(26-10-12-0527)改版: 置灰
    #    绑定随表格体重写迁渲染器分片(`:class="{ 'is-gated': !p.gatedOk }"`), 判据单点
    #    (rowsFn 装配读 drawerReannounceGate)与置灰 CSS 仍在变体文件)
    vdir = os.path.join(shared, "drawer_tpl")
    frag = open(os.path.join(shared, "tpl", "xtpl-cells-dt.html"), encoding="utf-8").read()
    for name, sec, cls in (
        ("04-trackers-status-cards-tall.js", "tpl-aq-dt04-cells", "dt04-act"),
        ("05-trackers-health-groups-low.js", "tpl-aq-dt05-cells", "dt05-act"),
        ("06-trackers-table-collapsed.js", "tpl-aq-dt06-cells", "dt06-act"),
    ):
        t = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "drawerReannounceGate()" in t, f"{name} 重报钮未接 drawerReannounceGate(详情面板绕行路径)"
        assert f".drawer .{cls}.is-gated" in t, f"{name} 缺 .{cls}.is-gated 置灰规则"
        assert 'rGate.ok ? "强制重新汇报" : rGate.title' in t or 'rGate.ok ? "" : rGate.title' in t, \
            f"{name} 的 rGate 判据未装配进行对象(gatedOk/gatedTitle 断供, 分片置灰失效)"
        sec_txt = frag.split(f'id="{sec}"', 1)[-1].split("</script>", 1)[0]
        assert ':class="{ \'is-gated\': !p.gatedOk }" data-act="report"' in sec_txt, \
            f"{name} 的 data-act=report 钮未按 gatedOk 置灰(仅删除钮该置灰=误伤)"
    assert "_guardReannounce({ keys: [], hashes: [target] })" in drawer_js, \
        "drawer.js torrentCmd 缺强制汇报兜底(详情面板行为层)"  # 2026-10-10(S3): 目标形参 hash -> target(显式传参, 缺省回落 menu.hash)

    # ⑤ 投递收敛: 闸门管"允不允许"(集合级全有全无, qB 口径), 计划管"发给谁"(只发活跃)
    assert "reannouncePlan(t) {" in deco, "decorate.js 缺投递收敛单点 reannouncePlan"
    assert "this.reannouncePlan({ keys, hashes })" in cmds, \
        "_actCore 未按 reannouncePlan 收敛投递集合 —— 混选会对非活跃目标发指令, 确认层随后白等窗口报「未确认」"
    assert "跳过 ${plan.skipped} 个非活跃" in cmds, \
        "回执未体现被跳过的非活跃目标数(用户看不懂「选了 4 个怎么只汇报了 1 个」)"
    assert "没有可强制重新汇报的目标" in cmds, \
        "缺空投递收口 —— 会落进成功分支报「成功 0 个目标」(把没做事说成做成了)"
    # 前后端判据表逐项同表(各写一份是刻意的: 前端要能在无往返时判置灰; 漂移必须立刻报红)
    assert _PY_BLOCKED_STATES == {
        "pausedDL",
        "pausedUP",
        "stoppedDL",
        "stoppedUP",
        "queuedDL",
        "queuedUP",
        "checkingDL",
        "checkingUP",
        "checkingResumeData",
        "error",
        "missingFiles",
        "moving",
    }, f"后端 REANNOUNCE_BLOCKED_STATES 与 qB 口径漂移: {sorted(_PY_BLOCKED_STATES)}"
    js_tbl = deco[deco.index("const REANNOUNCE_BLOCKED_STATES"):deco.index("const REANNOUNCE_BLOCKED_KINDS")]
    # 采集面 = 表体(切片已限定), 键名以 `<state>: "` 形态出现; 值文案不参与(如 missingFiles 是
    # 「文件缺失」不以「种子」开头 —— 按值文案收键会静默漏项, 这正是本守阵首跑抓到的那条)
    js_states = set(re.findall(r'(\w+): "', js_tbl))
    assert js_states == set(_PY_BLOCKED_STATES), \
        f"前后端非活跃判据表不一致(前端 {sorted(js_states)} / 后端 {sorted(_PY_BLOCKED_STATES)})"

    # ⑦ 删除链(issue 26-10-17-1703): 六个删除入口汇入 _deleteFlow, 是本专题「一条'不允许'
    #    必须接全部入口」清单中唯一漏接的入口 —— 默认勾选的「删除前强制重新汇报」对非活跃种子
    #    请求照发 -> 后端第二道闸 warn -> _reannounceAll warn 不放行 -> 删除被整体中止。
    #    修法两层: 闸门层(全非活跃禁用复选框) + 投递层(reannouncePlan 收敛), 加 D4/D6 的
    #    skip 桶(非活跃 warn 降级为跳过, 不挡删除)。
    dflow = open(os.path.join(shared, "delete_flow.js"), encoding="utf-8").read()
    pops = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()
    assert "this.reannouncePlan({ keys, hashes })" in dflow, \
        "_deleteFlow 未按 reannouncePlan 收敛投递集合 —— 非活跃目标照发 -> 后端 warn -> 删除被整体中止"
    assert "_deleteReannounceGate(" in dflow, \
        "delete_flow.js 缺删除链闸门 _deleteReannounceGate(全非活跃目标时复选框仍默认勾选)"
    assert "disabled: !!gate.disabled" in dflow, \
        "闸门结果未接进确认框选项(全非活跃时用户仍能勾上必然 warn 的汇报)"
    assert "checked: !gate.disabled" in dflow, \
        "全非活跃时汇报项未同步取消勾选(禁用却保持勾选 = 形态自相矛盾)"
    assert "async _reannounceAll(jobs, label, skipped = 0)" in dflow, \
        "_reannounceAll 签名缺 skipped 形参(跳过数无法在等待态就报, D5)"
    assert "_reannounceWarnInactive(" in dflow, \
        "_reannounceAll 缺非活跃 warn 识别 —— D6 竞态(渲染到点击之间转暂停)下删除仍被 warn 中止"
    assert re.search(r'function _reannounceWarnInactive\(err\) \{\s*\n\s*return typeof err === "string" && err\.includes\("非活跃"\)', dflow), \
        "非活跃 warn 识别函数缺失或关键词漂移(与后端回执文案的锚点: 两种文案均含「非活跃」)"
    # 模板: is-gated 类 + title 成对 + 点击短路(样式层真禁点击, D3)
    assert ":class=\"{ on: c.checked, danger: c.key === 'delete_files', 'is-gated': c.disabled }\"" in pops, \
        "popovers.html 多选项未按 c.disabled 挂 is-gated(禁用态无置灰反馈)"
    assert ':title="c.title || \'\'"' in pops, \
        "禁用原因未走 title 通道(空串 = 清除提示, 见 ctx-menus 同款口径)"
    assert '@click="c.disabled || (c.checked = !c.checked)"' in pops, \
        "禁用项未在模板层短路点击(只靠样式 = 键盘/辅助技术仍可触发切换)"
    # CSS 成套(三套皮肤 + atlas dialogs.css 后加载同补): 置灰须压过 .opt-pill:hover(坑档特异性节)
    for name, t in (
        ("atlas css 聚合(link 序)", _ui_css_aggregate("atlas")),
        ("console css 聚合(link 序)", _ui_css_aggregate("console")),
        ("prism css 聚合(link 序)", _ui_css_aggregate("prism")),
    ):
        assert ".opt-pill.is-gated" in t, f"{name} 缺 .opt-pill.is-gated 置灰规则(禁用态挂件裸奔)"
    # 非活跃 warn 的文本判据: 后端常量必须含「非活跃」(前端 _reannounceWarnInactive 按它识别)
    assert "非活跃" in _PY_INACTIVE_SKIP, \
        f"后端 REANNOUNCE_INACTIVE_SKIP 文案漂移(前端文本判据锚点失效): {_PY_INACTIVE_SKIP}"

    # ⑥ 判定语义真跑(node 电池, 无 node 静默跳过 —— 与 _DT_DENSITY_NODE_PROBE 同口径):
    #    "接线在"不等于"判得对", qB 状态表本身必须真跑一遍(排队那一条是判据存在的理由);
    #    删除链(issue 26-10-17-1703)的闸门与 skip 桶同批真跑。
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [
            node, "-e", _NODE_REANNOUNCE_GATE_PROBE,
            os.path.join(shared, "decorate.js"),
            os.path.join(shared, "delete_flow.js")
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"强制汇报判定 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"强制汇报判定电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_frontend_qb_traffic_drawer_page_guard():
    r"""流量图抽屉的页面守卫(2026-10-06 修「qB 全局流量图错误地出现在设置页」)

    抽屉是 app 级 sticky 吸底的停靠面板(.drawer-dock), 而 drawerVisible 原先对流量形态无条件为真
    (口径「任意页可开」) —— 在设置页(整幅配置工作台, 自己的滚动容器铺满)面板会压住页面底部内容,
    看着像设置页自带的一块。四类**守不全就复发**的形态钉住:
    1. 可见性单点 drawerVisible: 两形态一律先挡非主内容页(page !== "groups"); **状态位不随切页翻**
       (面板 DOM 退场、抽屉状态保住 —— 回主内容页连数据/窗口选择一起回来 = 方案A W1 验收项);
    2. 轮询与建图的 active 同源守卫: 三挂点一律含 page 判据 —— 面板不在 DOM 还拉还画 = 对着空气取数
       (同 pitfalls/web-ui/dock-panel「停靠面板隐藏后轮询要随可见性收口」);
    3. 入口可达性: 状态栏按钮与全局快捷键(Ctrl+Backslash)任意页可达 —— openDrawerTraffic 必须先把页
       切回主内容页, 否则「点了没反应」(状态翻了、面板不在 DOM);
    4. 图的生命周期(state.js watch drawerVisible): Vue 的 v-if 拆装会**换掉建图宿主**, uPlot 的
       root/canvas 挂在被拆走的旧 .qb-chart-host 上且不自愈(要等下一拍轮询, 而间隔可能夹到 600s)
       ⇒ 症状「回主内容页后面板里有文字没图」—— 退场销毁图、进场补拉一发(_qbLoad 内含建图);
       种子详情支路(!s)的变体宿主回页重挂归 test_drawer_seed_reentry_variant_remount。
    5. 同目标幂等短路(2026-10-07 修「再按 Ctrl+\ 闪烁」): 抽屉已开着同一形态同一目标时重按入口
       (快捷键/状态栏钮)必须短路返回 —— 全量路径会把收图销毁 + 抽屉重建 + 首拉 loading 各闪一遍
       (pitfalls/web-ui/drawer-switch-flicker「快中间态本身就是闪」)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()

    # 1. 可见性单点: 守卫在形态分支之前, 状态位不被改写
    vis = re.search(r"drawerVisible\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert vis, "drawer.js 缺 drawerVisible(面板可见性单点, 移动了就同步本守阵)"
    vb = vis.group(1)
    assert "if (!this.drawer.open) return false;" in vb, "抽屉可见性必须先挡 drawer.open"
    assert 'if (this.page !== "groups") return false;' in vb, \
        "drawerVisible 缺主内容页守卫(设置页会浮着一张不属于它的流量图/种子详情面板)"
    assert 'return this.viewMode === "torrents";' not in vb, \
        "种子详情不得再限种子视图(2026-10-08 计划 26-10-08-1217: 三视图共用面板, 成员行三视图同源)"
    assert re.search(r"^      return true;", vb, re.M), \
        "drawerVisible 末尾必须无条件 return true(过了主内容页守卫即显示; 形态分支已收归页面级)"
    assert "this.drawer.open = false" not in vb, \
        "可见性不得改写抽屉状态位(面板 DOM 退场 ≠ 关闭: 回主内容页状态还要回来)"

    # 2. 三挂点 active 同源守卫(轮询 tick / 建图判据同宽)
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "qb_traffic_chart.js 缺 _QB_SCOPES 作用域表(三挂点单一描述源)"
    body = "\n" + scopes.group(1)  # 还原段首换行(正则捕获从 `  global: {` 起), 便于按段切分
    for scope in ("global", "group", "torrent"):
        seg = body.split("\n  %s: {" % scope)[1].split("stale:")[0]
        assert 'page === "groups"' in seg, \
            f"{scope} 挂点 active 缺主内容页守卫(面板已退场仍拉 /api/traffic/qb/* 且继续画不可见的图)"

    # 3. 入口可达(状态栏/快捷键任意页可达): 触发即切回主内容页
    op = re.search(r"async openDrawerTraffic\(scope, key\) \{\n(.*?)\n    \},", js, re.S)
    assert op, "qb_traffic_chart.js 缺 openDrawerTraffic(打开流量形态抽屉的单点)"
    ob = op.group(1)
    assert 'if (this.page !== "groups") this.page = "groups";' in ob, \
        "openDrawerTraffic 缺页面归一: 在设置页点状态栏入口/按 Ctrl+Backslash 会「点了没反应」"
    assert ob.index('this.page !== "groups"') < ob.index("this._stopDrawerPoll()"), \
        "页面归一必须在重置抽屉状态之前(切页会引发重排, 先于所有副作用)"

    # 5. 同目标幂等短路: 已开着同一形态同一目标(分组再比 key)时重按入口不重建(否则收图销毁+
    #    抽屉重建+首拉各闪一遍); 短路必须落在 _stopDrawerPoll 等副作用之前才算短路
    assert 'this.drawerIsTraffic' in ob and "this.qbGroupKey === key" in ob, \
        "openDrawerTraffic 缺同目标幂等短路: 再按 Ctrl+\\ 会把收图+重建+首拉各闪一遍(W6 起形态判据走单点)"
    assert ob.index('this.drawerIsTraffic') < ob.index("this._stopDrawerPoll()"), \
        "同目标短路必须在收图/重建副作用之前(落在后面 = 短路失效, 闪烁回归)"

    # 4. watch(drawerVisible): 退场销毁图 / 进场补拉重建(uPlot 宿主随 v-if 拆装被换掉)
    #    种子详情支路(!s)W7 恢复进场补挂($nextTick 等 aside 补进 DOM 再 _dtSync; 见
    #    test_drawer_seed_reentry_variant_remount 全套钉法, 此处只钉挂点存在)
    wt = re.search(r"drawerVisible\(v\) \{\n(.*?)\n    \},", state_js, re.S)
    assert wt, "state.js 缺 watch(drawerVisible)(换宿主后图不自愈 = 回页只剩文字)"
    wb = wt.group(1)
    assert "const s = this.qbCurScope;" in wb and "if (!s) {" in wb and "$nextTick(() => this._dtSync())" in wb, \
        "watcher 缺种子详情支路进场补挂(!s 分支 $nextTick -> _dtSync; W7 随变体层恢复)"
    assert "this._qbChartDestroy(s);" in wb and "this._qbReloadOnEnter(s);" in wb, \
        "drawerVisible watcher 必须退场销毁图 + 进场补拉重画(补拉内含 $nextTick 建图单点)"
    re_b = re.search(r"_qbReloadOnEnter\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert re_b, "qb_traffic_chart.js 缺 _qbReloadOnEnter(面板进场补拉单点)"
    rb = re_b.group(1)
    assert "this._qbLoad(scope);" in rb, "_qbReloadOnEnter 必须走 _qbLoad 单点(内含建图, 不另写请求)"
    assert 'this[def.loading]' in rb, \
        "_qbReloadOnEnter 缺在途不叠加守卫(打开路径已先发一发, 进场 watcher 会把首次请求翻倍)"


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


def test_removed_redundant_tooltips_stay_removed():
    """复述型 tooltip 不得复活守阵(报告 26-10-04-0815: A-G 组模板 66 处 + H1 columns.js)

    判定口径: tooltip 只是逐字复述可见内容 / 图标本身自明的都属冗余, 已整体移除;
    全站悬浮提示统一由 shared/ui_feedback.js 拦截层渲染。本守阵读模板/JS 源码钉住
    代表性文案, 哪个文件把已删文案写回去即红。判定为保留的 tooltip(操作说明/后果预告、
    drawer.js 等的 _openModal 弹窗标题字段、config_hub.js 设置节标题、独立图表部件)不在列。
    二轮(I 组): 详情面板 drawer_tpl 冗余 tooltip 清理(与可见文本复述 / 开发者口径 /
    图例按钮自明), IP 地址列 / 对端自身进度 / 按进度估算缺口等有增量 tooltip 保留不在列。
    """
    checks = (
        # A 组 · 底部状态栏: 数值逐字复述 + 「点击修改」增量提示 + 数据状态实现细节
        ("shared/tpl/statusbar.html", ("点击修改", "数据状态")),
        # B 组 · 顶栏页签: 与可见文字同义(图标+「分组」/「种子」)
        ("shared/tpl/topbar.html", ("按分组展示", "全部种子一行一条")),
        # D 组 · 抽屉关闭钮: ✕ 自明, Esc 快捷键在帮助浮层有正式清单
        ("shared/tpl/drawer.html", ("关闭(Esc)", "关闭（Esc）")),
        # E 组 · 对话框族关闭钮: 关闭钮的 ✕ 自明
        ("shared/tpl/dialogs.html", ('title="关闭"', )),
        ("shared/tpl/dialogs-mgr.html", ('title="关闭"', )),
        ("shared/tpl/popovers.html", ('title="关闭"', )),
        # E2 续(issue 26-10-20-2231): 对话框关闭钮收敛进组件模板后, 新单点同样不得复活该 tooltip
        ("shared/tpl/dialog-shell.html", ('title="关闭"', )),
        # F 组 · 曲线标题栏 caret: 箭头方向已表意
        ("shared/tpl/settings-detail.html", ("点击收起", )),
        ("shared/tpl/xtpl.html", ("点击收起", )),
        # H1 · columns.js 列偏好提示横幅: 横幅整体可点 + 手型光标 + 15s 自毁
        ("shared/columns.js", ("点击关闭", )),
        # I 组 · 详情面板冗余 tooltip 二轮(drawer_tpl A/B 清单): 同屏可见文本的复述 +
        #     开发者口径(求和/前端派生) + 图例/按钮自明文案, 同屏信息已足够不再悬浮重复
        ("shared/tpl/drawer.html", (':title="t.url"', )),
        ("shared/drawer_tpl/01-general-hero-tall.js", ('title="${r.label}"', )),
        ("shared/drawer_tpl/02-general-cards-low.js", ('title="${r.label}"', )),
        ("shared/drawer_tpl/03-general-dossier-collapsed.js", ('title="${r.label}"', )),
        (
            "shared/drawer_tpl/05-trackers-health-groups-low.js", (
                'title="正常"',
                'title="警告"',
                'title="更新中"',
                'title="失败"',
                "未启用(含虚拟条目)",
                'title="分区顺序即处理顺序',
            )
        ),
        ("shared/drawer_tpl/06-trackers-table-collapsed.js", (
            "正在等待 tracker 响应",
            "只显示 警告 / 更新中 / 失败 行",
        )),
        (
            "shared/drawer_tpl/07-peers-dashboard-tall.js", (
                "对端 upspeed 求和",
                "对端 dlspeed 求和",
                'title="${k} × ${byClient[k]}"',
                'title="其它 ${keys.length - 3}',
                'title="qB flags: ',
                'title="会话累计"',
                'title="会话累计 0"',
                '· ${p.client || "未知"}"',
            )
        ),
        (
            "shared/drawer_tpl/08-peers-groups-low.js", (
                'title="qB flags: ',
                'title="会话累计"',
                'title="会话累计 0"',
                '· ${p.client || "未知"}"',
            )
        ),
        (
            "shared/drawer_tpl/09-peers-density-collapsed.js", (
                'title="qB flags: ',
                'title="会话累计"',
                'title="会话累计 0"',
                '· ${p.client || "未知"}"',
            )
        ),
        ("shared/drawer_tpl/10-content-tree-detail-tall.js", ("展开全部目录", "折叠全部目录")),
        ("shared/drawer_tpl/11-content-treegrid-batch-low.js", (
            "全选 / 全不选(文件)",
            "目录内共",
            "展开全部目录",
            "折叠全部目录",
        )),
        ("shared/drawer_tpl/12-content-space-treemap-collapsed.js", (
            'title="优先级: 跳过"',
            'title="占总体积 ',
        )),
        # 2026-10-14: 原 13/14/15(流量变体)的复述型 tooltip 断言随流量变体移除而退役。
    )
    for rel, needles in checks:
        text = open(os.path.join(STATIC_ROOT, *rel.split("/")), encoding="utf-8").read()
        for needle in needles:
            assert needle not in text, (
                f"{rel} 出现已移除的复述型 tooltip 文案「{needle}」(报告 26-10-04-0815 判定为移除) —— "
                "悬浮提示一律走 shared/ui_feedback.js 拦截层, 不要把原生 title 写回去"
            )


def test_recheck_confirm_wired_all_mouse_entries():
    """重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3)

    键盘路径原有确认框(shortcuts.js _kbAct), 鼠标路径(批量右键/单选右键/抽屉)点下即执行
    (issue 26-10-05-0254: 防护不对称)。S3 抽共用 helper(commands.js _recheckConfirm, 文案与
    调用形态逐字沿键盘路径)后四处同一文案。本守阵读 JS 源码钉住三个接入点 + 文案单点,
    任一被重构摘除即红:
    1. commands.js _recheckConfirm 存在, 且 confirmDialog/okText 调用形态与文案逐字原样;
    2. bulkAct(批量右键 ctxAct 的落点, 批量浮条退役后仍是批量通道单点)含 recheck 确认分支;
    3. drawer.js torrentCmd(单选右键与抽屉内命令共同通道)含 recheck 确认分支;
    4. shortcuts.js _kbAct 改调共用 helper, 不再内联 confirmDialog 文案;
    5. 共用文案字符串全仓只在 commands.js 出现一次(防三处各抄一份漂移)。
    """
    cmds = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()
    shortcuts = open(os.path.join(STATIC_ROOT, "shared", "shortcuts.js"), encoding="utf-8").read()
    text = "全量重读磁盘并校验完整性, 大库上耗时长且不可中断。"

    # ① 共用 helper 单点: 调用形态(标题/okText)与文案逐字沿键盘路径原样
    m = re.search(r"async _recheckConfirm\(what\)\s*\{(.*?)\n    \},", cmds, re.S)
    assert m, "commands.js 找不到 _recheckConfirm(改名或挪走了? 同步本守阵)"
    helper = m.group(1)
    assert 'confirmDialog("重新校验"' in helper and '{ okText: "确定" }' in helper, (
        "共用 helper 未沿键盘路径原调用形态(confirmDialog + okText 确定) —— 入口间确认形态漂移"
    )
    assert text in helper, "共用 helper 丢失键盘路径既有文案(重新校验确认框文案必须逐字保留)"

    # ② 共用文案字符串只此一份(三入口共用, 防各抄一份漂移)
    for name, src in (("commands.js", cmds), ("drawer.js", drawer), ("shortcuts.js", shortcuts)):
        assert src.count(text) == (1 if name == "commands.js" else
                                   0), (f"{name} 内联了重新校验确认文案 —— 共用文案只允许存在 commands.js _recheckConfirm 一份")

    # ③ 批量通道(bulkAct): 批量右键(ctxAct)入口, recheck 先确认后投递, 取消零副作用。
    #    分支按**整行活性**锚定(精确缩进 + if/await/if(!ok) 结构) —— 注释包裹、短路禁用、
    #    挪出确认调用都会破坏匹配而变红; 裸字符串包含判定拦不住这些摘除形态(红验实测)。
    m = re.search(r"async bulkAct\(action\)\s*\{(.*?)\n    \},", cmds, re.S)
    assert m, "commands.js 找不到 bulkAct(改名或挪走了? 同步本守阵)"
    assert re.search(
        r'^      if \(action === "recheck"\) \{\n'
        r"        const ok = await this\._recheckConfirm\(.+\);\n"
        r"        if \(!ok\) return;\n"
        r"      \}$",
        m.group(1),
        re.M,
    ), "bulkAct 的 recheck 确认分支被摘除/改写 —— 批量右键重新校验恢复裸奔(计划 26-10-05-0314 S3; 接入点改写须同步本守阵)"

    # ④ 单选通道(torrentCmd): 单选右键与抽屉内命令入口, 只拦 recheck 其它命令不受影响
    # 2026-10-10(S3): 签名加第 4 参 hash(显式传参, 抽屉/键盘路径不再写 menu.hash 借道)
    m = re.search(
        r"async torrentCmd\(action, body = null, okText = \"\", hash = \"\"\)\s*\{(.*?)\n    \},", drawer, re.S
    )
    assert m, "drawer.js 找不到 torrentCmd(改名或挪走了? 同步本守阵)"
    assert re.search(
        r'^      if \(action === "recheck"\) \{\n'
        r"        const ok = await this\._recheckConfirm\(.+\);\n"
        r"        if \(!ok\) return;\n"
        r"      \}$",
        m.group(1),
        re.M,
    ), "torrentCmd 的 recheck 确认分支被摘除/改写 —— 单选右键/抽屉重新校验恢复裸奔(计划 26-10-05-0314 S3; 接入点改写须同步本守阵)"

    # ⑤ 键盘通道(_kbAct): 改调共用 helper(整行活性锚定), 不得再内联确认框文案
    m = re.search(r"async _kbAct\(action\)\s*\{(.*?)\n    \},", shortcuts, re.S)
    assert m, "shortcuts.js 找不到 _kbAct(改名或挪走了? 同步本守阵)"
    assert re.search(
        r"^        const ok = await this\._recheckConfirm\(what\);$",
        m.group(1),
        re.M,
    ), "_kbAct 未调共用 helper —— 键盘路径自成一份文案必漂移(计划 26-10-05-0314 S3)"
    assert 'confirmDialog("重新校验"' not in m.group(1), ("_kbAct 又内联了重新校验确认框文案 —— 应改调 commands.js _recheckConfirm")


def test_skip_check_dialog_precheck_wired():
    """跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4)

    S4 把跳检确认框升级为三分流预检对话框: 共享 modal 扩展 okDisabled/busy/verdict 三字段,
    抽 _skipCheckDialog 取代 skipCheckTorrent/skipCheckMulti 两个各自为政的 _openModal。
    本守阵读 JS/模板源码钉住接线, 整行/整块活性锚定(T13 经验: 字符串包含拦不住突变),
    任一环被重构摘除即红:
    1. ui_feedback.js _modalInit 声明 okDisabled: false / busy: false / verdict: null
       (缺省零变化是「既有全部对话框不受影响」的根基);
    2. popovers.html 确认钮(modalOk)挂 :disabled="modal.okDisabled" 绑定 + busy 行 +
       verdict 行式渲染区(复用 modal-details 范式) + 强制钮仍走 extraText 第三钮
       (danger-solid 破坏性分支);
    3. drawer.js 两入口均交棒 _skipCheckDialog 且方法体内不再自带 _openModal;
    4. _skipCheckDialog 进框即 okDisabled:true + busy:true + verdict(固定警示区)并触发预检
       (_skipPrecheck 调 precheck 端点 + waitCmd 等回执)。
    """
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()

    # ① _modalInit 三字段(缺省值即零变化契约: 改默认/删字段/改名都红)
    m = re.search(r"_modalInit\(\)\s*\{\s*return\s*\{(.*?)\n      \};", ui, re.S)
    assert m, "ui_feedback.js 找不到 _modalInit(改名或挪走了? 同步本守阵)"
    init = m.group(1)
    assert re.search(r"^        okDisabled: false, // ", init, re.M), \
        "_modalInit 缺 okDisabled: false 声明(确认钮禁用通道) —— 预检对话框状态机失锚"
    assert re.search(r"^        busy: false,\s+// ", init, re.M), \
        "_modalInit 缺 busy: false 声明(预检在途行) —— 预检对话框状态机失锚"
    assert re.search(r"^        verdict: null,\s+// ", init, re.M), \
        "_modalInit 缺 verdict: null 声明(三分流渲染区) —— 预检对话框状态机失锚"

    # ② 模板: 确认钮 :disabled 绑定(整钮块锚定 —— 绑定挪出 modalOk 钮或改静态值即红)
    m = re.search(r'<button ref="modalOk"[\s\S]*?</button>', tpl)
    assert m, "popovers.html 找不到 modalOk 确认钮(模板重构? 同步本守阵)"
    assert ':disabled="modal.okDisabled"' in m.group(0), \
        "modalOk 确认钮缺 :disabled=\"modal.okDisabled\" 绑定 —— 进框禁用/按态解锁失效(计划 26-10-05-0314 S4)"
    # busy 行(整行锚定)与 verdict 渲染区(行式明细; issue 26-10-20-2231 两套明细并一后,
    # 行表由 state.js::modalDetailRows 拼装 —— 消费面在此钉住, 单点本体由
    # test_frontend_dialog_shell_single_point 钉)
    assert '<p v-if="modal.busy" class="modal-body">正在检查前置条件…</p>' in tpl, \
        "popovers.html 缺预检 busy 行 —— 预检在途无反馈(计划 26-10-05-0314 S4)"
    assert '<div v-if="modalDetailRows.length" class="modal-details">' in tpl, \
        "popovers.html 缺 verdict 三分流渲染区(modal-details 行式范式)"
    assert 'v-for="d in modalDetailRows"' in tpl, "verdict 区缺行式 v-for 渲染"
    # 强制钮仍复用 extraText 第三钮通道(danger-solid 破坏性分支; 换自铸强制钮即红)
    assert re.search(r'<button v-if="modal\.extraText" class="bt danger-solid" @click="resolveModal\(\'extra\'\)">', tpl), \
        "第三钮(extraText 通道)被改写 —— S4 强制钮必须复用既有 danger-solid 破坏性分支"

    # ③ 两入口均交棒 _skipCheckDialog, 且方法体内不再自带 _openModal(确认框被取代)
    #    skipCheckMulti 现带可选 targets(单组右键 skipCheckGroup 复用同一状态机, 2026-10-09),
    #    故签名按"可选参"收 —— 只钉"入口存在且交棒"这一语义, 不钉参数表。
    for name in ("skipCheckTorrent", "skipCheckMulti"):
        m = re.search(rf"async {name}\([^)]*\)\s*\{{(.*?)\n    \}},", drawer, re.S)
        assert m, f"drawer.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert "this._skipCheckDialog(" in m.group(1), \
            f"{name} 未走 _skipCheckDialog —— 预检对话框两入口共用的状态机被绕开(计划 26-10-05-0314 S4)"
        assert "_openModal" not in m.group(1), \
            f"{name} 仍自带 _openModal 确认框 —— 旧 danger 确认框应被预检对话框取代"

    # ④ _skipCheckDialog: 进框即禁用 + busy + 固定警示区 + 触发预检(调 _skipPrecheck)
    m = re.search(r"async _skipCheckDialog\(hashes, exec\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipCheckDialog(S4 状态机被改名/挪走? 同步本守阵)"
    dlg = re.sub(r"//[^\n]*", "", m.group(1))  # 剥行注释后锚定代码结构(注释改写不红, 代码突变必红)
    assert "okDisabled: true" in dlg, "_skipCheckDialog 进框未禁用确认钮(预检回执前不得有可执行钮)"
    assert "busy: true" in dlg, "_skipCheckDialog 进框未置 busy(预检在途无反馈)"
    assert "verdict: warnRows" in dlg, "_skipCheckDialog 进框未挂固定警示区(case 3 不代表没有代价)"
    assert "this._skipPrecheck(seq" in dlg, "_skipCheckDialog 未触发预检投递"


def test_skip_check_dialog_verdict_render():
    """跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4)

    静态钉住 _skipPrecheck/_skipCheckDialog/_skipExec/_skipVerdictRows 的状态机语义,
    防渲染逻辑被改写出「blocked 仍可执行 / 降级态冒出强制钮 / 混合态送错子集」这类
    pytest 静态守阵之外只有真浏览器才看得见的回归:
    1. 六态分支(逐分支提取语句清单与期望比对, 剥注释滤空行): 预检失败降级=启用普通确认且无
       强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认「跳检 N 个可跳检的」+强制
       「强制跳检全部」/ force-only=确认保持禁用只有强制钮 / 全 ok=只启用确认;
    2. ok 子集派生与提交口径: okHashes 只收 cls==="ok"; 确认路径送 ok 子集(降级送全量),
       强制路径送全量 + force=true(单发 body 仅 force 时带 force 键, 批量确认只走 hashes);
    3. 降级文案明示「后端闸门仍会在执行时拦截」(D10);
    4. 分组展示: 计数行(可跳检/需强制/禁止)+ 组内名称上限截断(slice(0,5)+等 X 个)。
    """
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()

    # ① 状态机六态分支: 逐分支提取语句清单(剥注释滤空行后)与期望逐一比对 ——
    #    摘除/新增/改写任一语句(如降级分支删掉解锁行、blocked 分支漏收强制钮)即红
    m = re.search(r"async _skipPrecheck\(seq, mid, hashes, warnRows\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipPrecheck(S4 状态机被改名/挪走? 同步本守阵)"
    pre = re.sub(r"//[^\n]*", "", m.group(1))

    def _branch(head, nxt):
        bm = re.search(re.escape(head) + r"(.*?)" + re.escape(nxt), pre, re.S)
        assert bm, f"状态机分支锚点丢失: {head!r} -> {nxt!r}(分支结构被改写? 同步本守阵)"
        return [ln.strip() for ln in bm.group(1).splitlines() if ln.strip()]

    assert _branch("if (degraded) {", "} else if (counts.blocked) {") == [
        "this.modal.okDisabled = false;",
        'this.modal.extraText = "";',
    ], "降级分支(D10)被改写 —— 必须启用普通确认(okDisabled=false)且无强制钮(extraText 空)"
    assert _branch("} else if (counts.blocked) {", "} else if (counts.ok && counts.force) {") == [
        "this.modal.okDisabled = true;",
        'this.modal.extraText = "";',
    ], "含 blocked 分支被改写 —— blocked 硬闸: 确认/强制双钮全收, 不得产生任何可执行钮"
    assert _branch("} else if (counts.ok && counts.force) {", "} else if (counts.force) {") == [
        "this.modal.okDisabled = false;",
        "this.modal.okText = `跳检 ${counts.ok} 个可跳检的`;",
        "this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;",
    ], "ok+force 混合分支被改写 —— 确认钮只送 ok 子集文案, 强制钮送全量"
    assert _branch("} else if (counts.force) {", "} else {") == [
        "this.modal.okDisabled = true;",
        "this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;",
    ], "force-only 分支被改写 —— 确认保持禁用, 只有强制钮"
    fm = re.search(re.escape("} else if (counts.force) {") + r"(.*?)" + re.escape("} else {"), pre, re.S)
    assert fm, "force-only 分支锚点丢失(分支结构被改写? 同步本守阵)"
    tail_m = re.search(r"(.*?)\n      \}", pre[fm.end():], re.S)
    assert tail_m, "全 ok 分支锚点丢失(分支结构被改写? 同步本守阵)"
    assert [ln.strip() for ln in tail_m.group(1).splitlines() if ln.strip()] == [
        "this.modal.okDisabled = false;",
        "this.modal.okText = `跳检 ${counts.ok} 个`;",
        'this.modal.extraText = "";',
    ], "全 ok 分支被改写 —— 只启用确认(送全量不带 force), 无强制钮"
    # ok 子集派生: 只收 cls==="ok"(blocked/force 不进确认子集)
    assert 'okHashes = results.filter((x) => x.cls === "ok").map((x) => x.hash);' in pre, \
        "okHashes 未按 cls===\"ok\" 派生 —— 确认子集口径失守"
    # D10 降级文案(两处: 非 ok 回执 + 请求异常, 缺一即红)
    assert pre.count("后端闸门仍会在执行时拦截") == 2, \
        "降级文案「后端闸门仍会在执行时拦截」应恰好覆盖 非 ok 回执 与 请求异常 两分支"

    # ② 确认/强制两路径的提交口径(_skipCheckDialog 分派 + _skipExec 端点载荷)
    m = re.search(r"async _skipCheckDialog\(hashes, exec\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipCheckDialog"
    dlg = re.sub(r"//[^\n]*", "", m.group(1))
    assert "return this._skipExec(exec, hashes, true);" in dlg, \
        "强制路径未送全量(hashes) —— 强制钮必须送全量 + force"
    assert "return this._skipExec(exec, v.degraded ? hashes : v.okHashes, false);" in dlg, \
        "确认路径未按 态送 ok 子集(降级送全量) —— 混合态把 force/blocked 目标混进普通确认即违背三分流"
    m = re.search(r"async _skipExec\(exec, hashes, force\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipExec"
    exe = re.sub(r"//[^\n]*", "", m.group(1))
    assert "body: force ? JSON.stringify({ force: true }) : undefined" in exe, \
        "单发跳检 body 应仅在 force 时携带 force 键(缺省载荷与历史一致)"
    assert "keys: force ? exec.groupKeys : []" in exe and "hashes: force ? exec.memberHashes : hashes" in exe, \
        "批量跳检载荷口径失守: 确认=只送 ok 子集(hashes), 强制=keys+hashes 整份"
    assert "...(force ? { force: true } : {})" in exe, \
        "批量强制路径缺 force: true 透传(S2: 提供才入载荷)"

    # ③ 分组展示: 计数行 + 上限截断(5 + 等 X 个)
    m = re.search(r"_skipVerdictRows\(results\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipVerdictRows"
    rows = re.sub(r"//[^\n]*", "", m.group(1))
    assert "`可跳检 ${ok.length} / 需强制 ${force.length} / 禁止 ${blocked.length}`" in rows, \
        "分组展示缺计数行(可跳检/需强制/禁止)"
    assert "g.names.slice(0, 5)" in rows, "分组行缺名称上限截断(5 个)"
    assert "等 ${g.names.length} 个" in rows, "分组行缺「等 X 个」尾注"


def test_modal_identity_stamp_landing_guard():
    """模态身份戳落袋守卫单点(F1-01, issue 26-10-06-0028) —— 迟到异步回执不得写进无关弹窗

    单例 modal 共用 this.modal, 落袋守卫只复核「seq + visible」兜不住: 用户取消跳检框后
    seq 不递增, 在回执到达前打开限速/重命名/删除确认等任意 modal, 回执落袋即覆写其
    verdict 与按钮文案。修法 = _openModal 每框发自增身份戳 mid, 落袋统一走 _modalIsCurrent
    单点(visible + mid 双比对) —— 本守阵静态钉住四处, 防「单例 modal + 异步落框」同形复发:
    1. ui_feedback.js _openModal 发戳(自增表达式必须内联在 modal 字面量里);
    2. ui_feedback.js _modalIsCurrent 单点存在且双条件齐全;
    3. drawer.js _skipCheckDialog 把 this.modal.mid 交棒 _skipPrecheck;
    4. drawer.js _skipPrecheck 落袋守卫 = seq 代际 + 身份戳, 且位于任何 this.modal 写之前。
    """
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()

    # ① _openModal 发戳: mid 自增必须随 modal 字面量一同创建(后补属性不进 Vue 响应的旧坑)
    m = re.search(r"_openModal\(cfg\)\s*\{(.*?)\n    \},", ui, re.S)
    assert m, "ui_feedback.js 找不到 _openModal(改名或挪走了? 同步本守阵)"
    assert re.search(
        r"this\.modal = \{[^}]*mid: \(this\._modalSeq = \(this\._modalSeq \|\| 0\) \+ 1\)", m.group(1)
    ), "_openModal 未随框发自增身份戳 mid —— 异步落框守卫失锚(F1-01)"

    # ② 守卫单点: visible + mid 双比对(mid 缺省/框已关/被新框取代一律失配)
    m = re.search(r"_modalIsCurrent\(mid\)\s*\{(.*?)\n    \},", ui, re.S)
    assert m, "ui_feedback.js 找不到 _modalIsCurrent(守卫单点被摘除? 同步本守阵)"
    body = re.sub(r"//[^\n]*", "", m.group(1))
    assert "this.modal.visible" in body and "this.modal.mid === mid" in body, \
        "_modalIsCurrent 必须同时复核 visible 与 mid(缺一不可)"

    # ③ 交棒: _skipCheckDialog 发预检时携带本框身份戳
    assert "this._skipPrecheck(seq, this.modal.mid, hashes, warnRows)" in drawer, \
        "_skipCheckDialog 未把 modal 身份戳交棒 _skipPrecheck(F1-01)"

    # ④ 落袋守卫: seq 代际 + _modalIsCurrent, 且在首处 this.modal 写之前
    m = re.search(r"async _skipPrecheck\(seq, mid, hashes, warnRows\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipPrecheck(签名被改? 同步本守阵)"
    pre = re.sub(r"//[^\n]*", "", m.group(1))
    guard = re.search(r"if \(seq !== this\._skipCheckSeq \|\| !this\._modalIsCurrent\(mid\)\) return;", pre)
    assert guard, "落袋守卫缺身份戳条件(F1-01: 只有 seq 兜不住取消后开无关 modal 的分支)"
    assert pre.index(guard.group(0)) < pre.find("this.modal.busy = false"), \
        "守卫必须前置 —— 迟到回执在守卫通过前不得写任何 this.modal 字段"


def test_frontend_ctx_menu_multi_select_targets_selection():
    """多选右键菜单必须作用于**整个选中集合**, 不是被点的那一行(CTX-03)

    用户报: "多选时右键菜单应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。
    根因: 四个 open*Menu 只记 anchor(key/hash/episode), 动作端点直接拿它拼 URL ⇒ 无论选了多少,
    都只动被点的那一个。而批量浮条早已有正确实现(bulkAct/bulkDelete 走 _bulkTargets)。

    修法是让菜单在"被点的行属于选中集合"时升级为批量菜单, 动作复用批量浮条的链路。这条守阵
    钉住三处**成对**关系(任一处漏改都会静默退化回单目标, 且 pytest/`node --check` 都看不见):
      1. 四个 open*Menu 必须各自写入 `multi:` —— 漏一处, 那条路径的多选右键就仍是单目标;
      2. 三套 UI 的行菜单都必须存在且消费注册表 `ctxItems(ctxMenuKind())`(W3 起项集/分派在
         shared/ctx_menu.js 注册表单点, 三 UI 同指 /shared/tpl/ctx-menus.html 一份 = 漂移
         结构性不可能; 2026-10-22 issue 26-10-20-2231 起四支骨架合并为一条, 批量支不再有
         独立的 template 段 —— 比对面换成"根块消费 ctxMenuKind() 单点 + 段内无逐项直写");
         注册表 multi 支只能调 ctxAct/ctxDelete;
      3. ctxAct/ctxDelete 必须**复用** bulkAct/bulkDelete —— 自己再拆一遍目标集合就会与批量浮条
         的口径漂移(虚拟行/组展开/失效目标跳过这三条语义都在 _bulkTargets 里)。
    """
    # 1. 四个菜单入口都必须写 multi
    openers = {
        "shared/menu.js": ["openMenu(event, group)", "openMemberMenu(event, member)"],
        "shared/shows.js": ["openShowEpMenu(event, show, ep)", "openShowMenu(event, show)"],
    }
    for rel, fns in openers.items():
        text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        for fn in fns:
            m = re.search(rf"\n    {re.escape(fn)} \{{(.*?)\n    \}},", text, re.S)
            assert m, f"{rel} 找不到 {fn}(改名或挪走了? 同步本守阵)"
            body = m.group(1)
            assert "_ctxMulti(" in body, (
                f"{rel} 的 {fn} 没有调 _ctxMulti 计算 menu.multi —— 该路径的多选右键会退化成"
                f"只作用于被点的那一行(CTX-03)"
            )
            assert "multi:" in body, f"{rel} 的 {fn} 没把 multi 写进 this.menu —— 模板读不到, 批量分支永不渲染"

    # 2. 三套 UI 的行菜单都必须消费注册表; 项集/分派在注册表单点(shared/ctx_menu.js,
    #    三 UI 同指 /shared/tpl/ctx-menus.html = 双 UI 漂移结构性不可能; W3 起逐项分派从
    #    模板文本搬进注册表 act —— 比对面随之搬家, 治的是同一件事)。
    #    2026-10-22(issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup): 四支各一份骨架
    #    合并为 ctxItems(ctxMenuKind()) 一条, 批量支不再有独立 <template v-if="menu.multi"> 段
    #    —— 比对面从"批量分支段"换成"行菜单根块消费 ctxMenuKind() 单点 + 段内无逐项直写"。
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert "<!-- 表头右键菜单" in text, f"{ui}/index.html 找不到行右键菜单段锚点(模板分片变了? 同步本守阵)"
        row = text[:text.index("<!-- 表头右键菜单")]
        assert "ctxItems(ctxMenuKind())" in row, (
            f"{ui}/index.html 的行右键菜单没有消费注册表 ctxItems(ctxMenuKind()) —— "
            f"多选右键拿不到批量动作(三 UI 必须成对改, 另一套有而它没有 = 半边用户没有该功能)"
        )
        assert "actTorrent(" not in row and "actEpisode(" not in row, (
            f"{ui}/index.html 行菜单段出现了单目标/单集动作直写 —— 分派必须整份走注册表 act"
            f"(批量支走 ctxAct/ctxDelete, CTX-03)"
        )
    # 注册表 multi 支: 五个批量动作 + ctxDelete 必须在, 且只能调 ctxAct/ctxDelete
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    seg = re.search(r"\n    multi: \[(.*?)\n    \],", reg, re.S)
    assert seg, "ctx_menu.js 找不到 multi 支定义段(注册表结构变了? 同步本守阵)"
    multi_defs = seg.group(1)
    for call in (
        'vm.ctxAct("resume")', 'vm.ctxAct("pause")', 'vm.ctxAct("reannounce")', 'vm.ctxAct("recheck")', 'vm.ctxDelete()'
    ):
        assert call in multi_defs, f"注册表 multi 支缺少 {call}(批量菜单项集漂移, CTX-03)"
    for bad in ("vm.actTorrent(", "vm.actEpisode(", "vm.delTorrent(", "vm.delEpisode(", "vm.act("):
        assert bad not in multi_defs, (f"注册表 multi 支出现单目标分派 {bad} —— 批量菜单必须整份走 ctxAct/ctxDelete")

    # 3. ctxAct/ctxDelete 复用批量浮条链路, 且先收起菜单(菜单根节点 @click.stop, 全局点空白关不掉)
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    for name, delegate in (("ctxAct(action)", "bulkAct(action)"), ("ctxDelete()", "bulkDelete()")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", cmd, re.S)
        assert m, f"shared/commands.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        body = m.group(1)
        assert delegate in body, (
            f"{name} 必须复用批量浮条的 {delegate} —— 自己再拆一遍目标集合会与 _bulkTargets 的"
            f"口径漂移(虚拟行/组展开/失效目标跳过), CTX-03"
        )
        assert "this.menu.visible = false" in body, f"{name} 必须先收起右键菜单(菜单是 @click.stop, 全局点空白关不掉)"


def test_frontend_ctx_menu_group_actions_parity():
    """单组右键菜单与多选批量菜单「动作项集一致」守阵(2026-10-09 用户报「单组右键菜单缺选项」)

    单组菜单(menu.key 的 v-else 分支)此前只有 开始/暂停/汇报 + 打开文件夹/流量图/删除, 而多选
    批量菜单(menu.multi 分支)还有 重新校验/跳检/限速/移动/标签分类/导出 —— 同一批动作在
    「右键 1 组」与「选 2 组」两条路径上项集不一致(用户报「单组右键菜单缺选项, 参考选中多组」)。
    本守阵钉三处(任一处漂移即静默少一个入口, pytest/node --check 都看不见):
      1. 单组支必须含六个组级入口(与批量分支同项集; 组菜单独有的 打开文件夹/流量图 除外);
      2. 跳检项必须吃 flags.skip_check_menu 门控(fail-closed, 与单选/批量两处同口径);
      3. 六个入口方法必须在 commands.js/drawer.js 落地且复用多选同一套下游链路
         (recheckGroup->_actCore / 限速移动跳检->drawer.js 多选对话框 / metaGroup->openMetaDialog /
          exportGroup->_exportHashes), 不为组级另开旁路。
    W3(计划 26-10-20-0024)起四支项集搬到注册表单点: 模板只按支名取项(ctxItems(支)), 项集/
    门控/分派在 ctx_menu.js group 支定义段 —— 比对面随之搬家。
    2026-10-22(issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup): 四支各一份骨架合并为
    一条 `ctxItems(ctxMenuKind())` v-for, 单组支不再是独立的 `<template v-else>` 段 ——
    "模板只消费注册表"这条断言改挂 ctxMenuKind() 单点, 项集比对面(下面三处)一字不动。
    """
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "ctx-menus.html"), encoding="utf-8").read()
    assert "ctxItems(ctxMenuKind())" in tpl, (
        "ctx-menus.html 行菜单未消费注册表 ctxItems(ctxMenuKind()) —— 回退逐项直写 = "
        "四支人肉奇偶复发(2026-10-09 报障: 单组缺选项)"
    )
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    seg = re.search(r"\n    group: \[(.*?)\n    \],", reg, re.S)
    assert seg, "ctx_menu.js 找不到 group 支定义段(注册表结构变了? 同步本守阵)"
    group = seg.group(1)

    # 1. 六个组级入口(与多选批量菜单同项集)
    for token in (
        "vm.recheckGroup()", "vm.skipCheckGroup()", "vm.editLimitsGroup()", "vm.editMoveGroup()", "vm.metaGroup()",
        "vm.exportGroup()"
    ):
        assert token in group, (f"注册表 group 支缺少 {token} —— 与多选批量菜单项集不一致(2026-10-09 报障: 单组缺选项)")

    # 2. 跳检项 fail-closed 门控(注册表 gate: "skip_check_menu"; flags 关 = 渲染层不出该项,
    #    与单选/批量两处同口径; 门在 ctx_menu.js CTX_GATE_FLAG 单点映射)
    skip_line = next((ln for ln in group.splitlines() if "vm.skipCheckGroup()" in ln), "")
    assert skip_line and 'gate: "skip_check_menu"' in skip_line, (
        "单组菜单「跳检…」项缺 skip_check_menu 门控(注册表 gate) —— 关态仍渲染 = fail-closed 破口"
    )

    # 3. 六个入口方法落地 + 复用多选同一套下游链路
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    drw = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()
    assert "_groupTargets()" in cmd, "commands.js 缺 _groupTargets(组级目标集合单点)"
    # 2026-10-10(S3): _groupTargets 退化为 _scopeResolve("anchor") 的投影, 成员展开单点
    # (memberHashesOf)随之收进 selection.js::_selExpandGroups —— 守阵跟着搬家, 语义不变
    assert '_scopeResolve("anchor", { kind: "group", id: k })' in cmd, (
        "commands.js _groupTargets 必须走作用域单点 _scopeResolve(口径收敛, 计划 26-10-10-2001 S3)"
    )
    selsrc = open(os.path.join(STATIC_ROOT, "shared", "selection.js"), encoding="utf-8").read()
    exg = re.search(r"_selExpandGroups\(groupKeys, bag\) \{(.*?)\n    \},", selsrc, re.S)
    assert exg and "this.memberHashesOf(" in exg.group(1), (
        "selection.js _selExpandGroups 未走 memberHashesOf 单点(成员对象直接取 .hash 会被静态守阵拦下)"
    )
    for name in ("recheckGroup", "editLimitsGroup", "editMoveGroup", "skipCheckGroup", "metaGroup", "exportGroup"):
        assert re.search(rf"\n    (?:async )?{name}\(", cmd), f"commands.js 缺组级入口 {name}"
    for delegate in (
        "this.editLimitsMulti(", "this.editMoveMulti(", "this.skipCheckMulti(", "this.openMetaDialog(",
        "this._exportHashes(", "this._actCore("
    ):
        assert delegate in cmd, f"commands.js 组级入口未复用 {delegate}(另开了旁路?)"
    for sig in ("editLimitsMulti(targets = null", "editMoveMulti(targets = null", "skipCheckMulti(targets = null"):
        assert sig in drw, f"drawer.js 缺 {sig}...) 可选 targets 形参 —— 组级入口无法复用同一状态机"


def test_frontend_meta_dialog_paired():
    """标签/分类编辑对话框守阵(静态防回潮)

    对选中集合(或单种子)即时增删标签/改分类。风险形态与批量菜单守阵(CTX-03)同源:
      1. 三套 UI 成对: 对话框与两处菜单入口缺一边 = 那套用户没有入口(W3 计划 26-10-20-0024
         起菜单入口搬到共享注册表单点 shared/ctx_menu.js, 三 UI 同指一份模板 = 结构性成对);
      2. 对话框的投递必须走 bulk 链路(/api/torrents/bulk), 目标集合口径单点在
         _bulkTargets/openMetaDialog —— 自己再拆一遍就会与批量浮条口径漂移;
      3. .opt-pill(atlas 此前没有该组件)与 .meta-dialog 的 CSS 必须两套成对定义,
         模板用到的类在 CSS 无定义 = 静默裸样式(挂件类名错配的变体)。
    """
    # 1. 三套 UI 成对: metaOpen 对话框 + 两处入口(W3 计划 26-10-20-0024 起菜单入口搬到
    #    注册表单点: 批量支 ctxMeta / 单种子支 openMetaDialog(menu.hash); shared/ctx_menu.js
    #    三 UI 同指一份 = 成对结构性保证, 逐项分派不再散在双模板各自演化)
    #    (2026-10-05 批量控制条退役: 模板层不再直接调 openMetaDialog(null), 批量入口统一走 ctxMeta)
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert ':open="metaOpen"' in text, f"{ui}/index.html 缺少标签/分类对话框(三套 UI 必须成对改)"
        assert "openMetaDialog(null)" not in text, (
            f"{ui}/index.html 又出现模板层直接调 openMetaDialog(null) —— 批量控制条已退役, "
            f"批量入口应统一走 ctxMeta(右键批量菜单)"
        )
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    assert "vm.openMetaDialog(vm.menu.hash)" in reg, ("注册表 member 支缺单种子右键菜单的标签/分类入口(openMetaDialog(vm.menu.hash))")
    assert "vm.ctxMeta()" in reg, "注册表 multi 支缺批量右键菜单的 ctxMeta 入口"
    # 2. shared 逻辑接线(逻辑层两套共用, 只在 shared 出现)
    dlg = open(os.path.join(STATIC_ROOT, "shared", "dialogs.js"), encoding="utf-8").read()
    for token in (
        "openMetaDialog(singleHash)",
        "closeMeta()",
        "_metaBulk(action, extra, okText)",
        "metaToggleTag(tag)",
        "metaAddNewTags()",
        "metaSetCategory(name)",
        "_bulkTargets()",
        "/api/torrents/bulk",
    ):
        assert token in dlg, f"shared/dialogs.js 缺少 {token}(改名或挪走了? 同步本守阵)"
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    m = re.search(r"\n    ctxMeta\(\) \{(.*?)\n    \},", cmd, re.S)
    assert m, "shared/commands.js 找不到 ctxMeta(改名或挪走了? 同步本守阵)"
    assert "this.menu.visible = false" in m.group(1), ("ctxMeta 必须先收起右键菜单(菜单是 @click.stop, 全局点空白关不掉)")
    assert "openMetaDialog(null)" in m.group(1), ("ctxMeta 必须复用 openMetaDialog 打开对话框 —— 目标集合口径单点在它里面")
    # 3. CSS 成对: .meta-dialog 与 .opt-pill 各套 UI 都要有定义
    for name, t in (
        ("atlas css 聚合(link 序)", _ui_css_aggregate("atlas")),
        (
            "prism/css/dialogs.css", open(os.path.join(STATIC_ROOT, "prism", "css", "dialogs.css"),
                                          encoding="utf-8").read()
        ),
        ("console css 聚合(link 序)", _ui_css_aggregate("console")),
    ):
        assert ".meta-dialog" in t, f"{name} 缺少 .meta-dialog 定义"
        assert ".opt-pill" in t, f"{name} 缺少 .opt-pill 定义(atlas 此前没有该组件, 易漏)"


def test_frontend_add_torrent_drag_drop_wiring():
    """DND-01 全局拖拽添加种子接线守阵(静态防回潮)

    拖拽进料口的关键点全在 JS/HTML 静态结构里, pytest 运行时看不见:
      1. window 级 drag 事件四件套(dragenter/dragover/dragleave/drop) add/remove 严格对称
         —— 漏 remove = 卸载后幽灵监听重复 ingest;
      2. drop handler 必须 preventDefault —— 删掉它浏览器会直接打开 .torrent / 跳转链接,
         表现为"拖进去弹出的是文件内容页";
      3. 接管判据只认 "Files"/"text/uri-list" —— 若放宽到 text/plain, 页面内拖选中文本、
         拖词进输入框的原生行为会被误拦;
      4. 双 UI 的落点遮罩成对存在(v-if="addDragOver"), app.js 有 addDragOver 状态 ——
         只改一套皮肤 = 另一套用户拖了没反应。
    """
    import re

    add_js = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    # 1. 四件套 add/remove 对称
    added, removed = set(), set()
    for hook, bucket in (("mounted", added), ("unmounted", removed)):
        m = re.search(rf"\n  {hook}\(\) \{{(.*?)\n  \}},", add_js, re.S)
        assert m, f"add_torrent.js 找不到 {hook} 钩子(DND-01 监听挂载点, 改名或挪走了? 同步本守阵)"
        for ev in re.findall(r'window\.(?:add|remove)EventListener\("([a-z]+)"', m.group(1)):
            bucket.add(ev)
    expect = {"dragenter", "dragover", "dragleave", "drop"}
    # 子集语义: mounted 还合法挂了 label 失焦收层守卫的 mousedown capture 记录器(四轮, 2026-10-04),
    # 不能再断言"恰好等于四件套" —— 只要求四件套一个不少, 多余监听交给 removed == added 对称性兜住。
    assert expect <= added, f"mounted 缺 drag 事件: {expect - added}(少一个就有一条路径不接管)"
    assert removed == added, f"unmounted 与 mounted 不对称: add={sorted(added)} / remove={sorted(removed)}"

    # 2. drop handler 必须拦默认行为 + depth 归零灭遮罩
    m = re.search(r"\n    _addDragDrop\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragDrop(drop 分流入口, 改名或挪走了? 同步本守阵)"
    assert "preventDefault()" in m.group(1
                                        ), ("_addDragDrop 少了 preventDefault —— 浏览器会直接打开 .torrent/链接而不是交给添加对话框(DND-01)")

    # 3. 接管判据只认文件与链接, 不得放宽到 text/plain
    m = re.search(r"\n    _addDragTakes\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragTakes(接管判据, 改名或挪走了? 同步本守阵)"
    takes = m.group(1)
    assert 'types.includes("Files")' in takes and 'types.includes("text/uri-list")' in takes, (
        "_addDragTakes 必须显式认 Files 与 text/uri-list(接管面收窄到拖文件/拖链接)"
    )
    assert "text/plain" not in takes, ("_addDragTakes 不得认 text/plain —— 会误拦页面内拖选中文本/拖词进输入框的原生行为(DND-01)")

    # 4. app.js 状态 + 双 UI 遮罩成对
    app_js = _app_bundle_text()
    assert "addDragOver: false" in app_js, "app.js 缺 addDragOver 状态(遮罩显隐没有数据源)"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        assert 'class="add-drop-mask"' in html and 'v-if="addDragOver"' in html, (
            f"{ui}/index.html 缺拖拽落点遮罩(.add-drop-mask + v-if=\"addDragOver\")—— "
            f"该皮肤用户拖文件进页面没有落点反馈(双 UI 必须成对改)"
        )


def test_frontend_add_torrent_partial_receipt_wiring():
    """添加种子「部分受理关窗」回执分流守阵(2026-10-18 用户报障: 部分种子添加失败(已存在)时
    添加窗口不消失)

    症状根因: 后端旧口径把"部分受理"(qB 对重复种子整批里挑着拒, HTTP 200 + failure_count>0)
    折叠进 error 回执, 前端 submitAddTorrent 只认 r.ok 关窗 ⇒ 明明加进去几个, 窗口赖着不动
    还报"添加种子失败"。修法 = 后端三态回执(ok/warn/error, commands.py::_cmd_add_torrents) +
    前端按 r.status 分流。行为面(pytest 运行时不可见)由 e2e/add-partial-receipt.spec.mjs 真浏览器钉,
    本守阵钉静态接线:
      1. submitAddTorrent 必须按三态分流 —— 有 `r.status === "warn"` 分支(只判 r.ok 即回潮);
      2. warn 分支必须关窗(addOpen = false)并以 warn 类 toast 给出详情(后端文案带计数);
      3. ok 分支保持关窗;
      4. error(全拒)分支**不得**关窗 —— 那一份文件/链接原样没进 qB, 留窗才能改完重提
         (部分成功与全部失败混为一谈是本案病根, 两个方向都钉)。
    """
    import re

    add_js = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    m = re.search(r"\n    async submitAddTorrent\(\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 submitAddTorrent(提交入口, 改名或挪走了? 同步本守阵)"
    body = m.group(1)

    # 1. 三态分流: warn 分支在(只判 r.ok 的二态写法回潮即红)
    assert 'r.status === "warn"' in body, (
        "submitAddTorrent 缺 r.status === \"warn\" 分支 —— 部分受理被 error 化, 窗口不消失(2026-10-18 报障)"
    )
    # 2. warn 分支: 关窗 + warn 类 toast(详情由后端文案带出, 见 commands.py 三态回执)
    warn_branch = re.search(r'\} else if \(r\.status === "warn"\) \{(.*?)\n        \} else \{', body, re.S)
    assert warn_branch, "warn 分支结构被改写(else if 链形状变了? 同步本守阵)"
    assert "this.addOpen = false" in warn_branch.group(1), ("warn 分支不关窗 —— 部分受理时添加窗口仍留在前台(本案报障原状)")
    assert '"warn", 8000' in warn_branch.group(1), ("warn 分支未以 warn 类 toast 给出部分失败详情(TOAST_MS_FLOOR: warn 停留下限 8s)")
    # 3. ok 分支保持关窗
    ok_branch = re.search(r"if \(r\.ok\) \{(.*?)\n        \} else if", body, re.S)
    assert ok_branch and "this.addOpen = false" in ok_branch.group(1), "ok 分支不关窗(全受理时窗口应消失)"
    # 4. error(全拒)分支不得关窗
    err_branch = re.search(r"\n        \} else \{\n(.*?)\n        \}", body, re.S)
    assert err_branch, "submitAddTorrent 找不到末尾 else(全拒)分支"
    assert "addOpen" not in err_branch.group(1), ("error(全拒)分支关了窗 —— 那一份文件/链接原样没进 qB, 关窗用户就没法改完重提了")


def test_frontend_add_combo_blur_close_and_fit():
    """添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障, 静态防回潮)

    两个用户可见故障形态, 根因都在事件接线/几何量测这类 pytest 运行时看不见的地方:
      1. **点窗口其它位置下拉不收 / 闪烁重现**: 收层判据原来只有 window click(lifecycle.js),
         点字段 label(for= 转发激活)时浏览器先 blur 再把焦点转回输入框, click 关层 + 转发
         click 重开 = 关了又开(leave 过渡被打断 = 闪烁)。修法 = 收层主判据改 @focusout,
         但**不能同步收** —— 必须 40ms 合帧守卫(焦点回来由开层方法撤销), 否则闪烁回潮。
      2. **选项过长把窗口撑变形**: .pop-menu 基础 max-height 只保证菜单自身可滚, 菜单锚在
         输入行下方, 绝对定位溢出会伸出窗口外并把 .add-dialog-body 的 scrollHeight 撑大。
         修法 = 开层时把可滚内层限到「输入行 → 滚动容器可见底沿」的净空内(滚动条留在窗口里)。
    """
    import re

    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    mgr = open(os.path.join(STATIC_ROOT, "shared", "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    xt = open(os.path.join(STATIC_ROOT, "shared", "tpl", "combo-input.html"), encoding="utf-8").read()

    # 1. 三个输入框全部挂失焦收层(收敛 issue 26-10-20-2230: 输入框骨架进共享组件
    #    #tpl-combo-input(独立分片 combo-input.html), 字段级接线在调用点) —— 漏一个 = 那个下拉点空白不收
    tpl_seg = re.search(r'id="tpl-combo-input">([\s\S]*?)</script>', xt, re.S)
    assert tpl_seg, "combo-input.html 找不到 #tpl-combo-input(combobox 共享模板, 改名或挪走了? 同步本守阵)"
    assert '@focusout="$emit(\'blur\')"' in tpl_seg.group(1), \
        "组件模板缺 @focusout=\"$emit('blur')\"(失焦即收是收层主判据, 组件内漏挂 = 五个下拉全不收)"
    for input_id in ("ad-save-path", "ad-category", "ad-tags"):
        m = re.search(rf'<aq-combo-input input-id="{input_id}"(.*?)>', mgr, re.S)
        assert m, f"dialogs-mgr.html 找不到 #{input_id}(添加窗口三下拉的输入框, 改名或挪走了? 同步本守阵)"
        assert '@blur="addPopBlurClose"' in m.group(1), \
            f"#{input_id} 缺 @blur=\"addPopBlurClose\"(失焦即收是收层主判据, 漏挂 = 该下拉点窗口其它位置不收)"

    # 2. 失焦收层必须带合帧守卫: 40ms 合帧 + _popBlurShouldHold 收敛在 _popBlurArm 单点
    #    (同步收层会被 label 的焦点转回打断 = 闪烁回潮); addPopBlurClose 是薄封装
    arm = re.search(r"_popBlurArm\(timerKey, ids, close\) \{(.*?)\n    \},", at, re.S)
    assert arm, "add_torrent.js 找不到 _popBlurArm(失焦收层合帧单点, 改名或挪走了? 同步本守阵)"
    assert "setTimeout" in arm.group(1) and "clearTimeout" in arm.group(1), \
        "_popBlurArm 必须用定时器合帧(同步收层 + label 转发回焦 = 关了又开闪烁); 定时窗内焦点回来由开层方法撤销"
    assert "COMBO_BLUR_CLOSE_MS" in arm.group(1), \
        "_popBlurArm 漏用 COMBO_BLUR_CLOSE_MS 单点常量(合帧窗改数值要三处同改, 收敛后只剩这一处)"
    assert "_popBlurShouldHold(ids)" in arm.group(
        1
    ), "_popBlurArm 收层前没问守卫(见 test_frontend_add_combo_label_clear_mask_and_refit 第 7 节)"
    body = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert body, "add_torrent.js 找不到 addPopBlurClose(失焦收层入口薄封装)"
    for field in ("addCatMenu", "addTagMenu", "addPathPop"):
        assert f"this.{field} = false" in body.group(1), f"addPopBlurClose 漏收 {field}"

    # 3. 三个开层方法先撤销挂起的收层(焦点回到输入框 = 菜单保持, 不闪)
    for fnname in ("openAddCatMenu", "openAddTagMenu", "openAddPathPop"):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and '_popBlurCancel("_addPopBlurT")' in body.group(1), \
            f"{fnname} 必须先 _popBlurCancel(\"_addPopBlurT\")(焦点转回输入框时撤销挂起的失焦收层, 否则菜单闪烁)"

    # 4. 限高: 开层 watcher 单点(开层入口有四处, 直挂方法会漏) + 量「行→滚动容器可见底沿」净空
    for token in ("addCatMenu(v) {", "addTagMenu(v) {", "addPathPop(v) {"):
        assert token in at, f"add_torrent.js 缺 watcher {token}(开层限高必须走 watcher 单点, 四处开层入口直挂会漏)"
    fit = re.search(r"_fitAddPop\(refName\) \{(.*?)\n    \},", at, re.S)
    assert fit, "add_torrent.js 找不到 _fitAddPop(下拉限高单点, 改名或挪走了? 同步本守阵)"
    fit_body = fit.group(1)
    assert 'closest(".add-input-row")' in fit_body and 'closest(".add-dialog-body")' in fit_body, \
        "_fitAddPop 必须以输入行为锚、以 .add-dialog-body 可见底沿为界量净空(以视口为界会在窗口化/滚动时量错)"
    assert 'list.style.maxHeight = ""' in fit_body, \
        "_fitAddPop 限高前必须先复位旧值(上一次的限高会污染本次测量)"

    # 5. 候选异步到位会改变菜单高度, 开着时也要重限
    for opt in ("addCatOptions", "addTagOptions", "addPathOptions"):
        assert re.search(rf"{opt}\(\) \{{\n      if \(this\.", at), \
            f"add_torrent.js 缺 {opt} 的 watcher(候选异步到位改变菜单高度, 开着时必须重限)"

    # 6. 三浮层互斥必须双向(26-10-04-0130): 开层收别家走 closeAddPopsExcept 单点 —— 单向写法
    #    (只 openAddPathPop 收 cat/tag, 反向不收)会让路径面板与下拉同悬, 且面板盖住相邻字段
    #    label 的点击(走查实测 "subtree intercepts pointer events")
    mutex = re.search(r"closeAddPopsExcept\(kind\) \{(.*?)\n    \},", at, re.S)
    assert mutex, "add_torrent.js 找不到 closeAddPopsExcept(三浮层互斥单点, 改名或挪走了? 同步本守阵)"
    mutex_body = mutex.group(1)
    for field, kind_key in (("addCatMenu", "cat"), ("addTagMenu", "tag"), ("addPathPop", "path")):
        assert f'kind !== "{kind_key}"' in mutex_body, \
            f"closeAddPopsExcept 缺 {field} 分支(互斥单点必须覆盖全部三个浮层)"
    for fnname, kind in (("openAddCatMenu", "cat"), ("openAddTagMenu", "tag"), ("openAddPathPop", "path")):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and f'closeAddPopsExcept("{kind}")' in body.group(1), \
            (f"{fnname} 必须调 closeAddPopsExcept(\"{kind}\") —— 开本浮层时收掉其余两个, "
             f"互斥漏一侧 = 双浮层同悬且盖住相邻字段 label 的点击")


def test_frontend_combo_hiscroll_never_scrolls_ancestors():
    """combobox 高亮滚动跟随「只滚菜单内部」守阵(2026-10-29 八修, 静态防回潮)

    症状(用户报): 选中过一条新路径后再点下拉框, 弹窗里的说明文案**从上往下滑一次**; 输入框为空时正常。
    根因: `_hiScroll` 用 `el.scrollIntoView({block:'nearest'})` —— 它会把**所有可滚祖先**一起滚, 而
    `.add-dialog-body` 正是 overflow-y 容器, 开层过渡期其 scrollHeight 比 clientHeight 大 166px
    (实测 body.scrollTop `0 → 166 → 83 → 18 → 0`, 文案 top `352 → 186 → 269 → 334`)。空输入时
    hi = -1、没有 `[data-hi="1"]`, 所以只有"已选中过路径"才看得见 —— 与用户描述逐字吻合。
    修法 = 手动差值调 scrollTop, 且**只动菜单内部**那层(逐级向上, 到菜单根即止); 与 26-09-29-2142
    (键盘光标滚动跟随)同一条禁令: 禁 scrollIntoView, 它会连带滚整页。
    """
    import re

    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    m = re.search(r"_hiScroll\(refName\) \{(.*?)\n    \},", at, re.S)
    assert m, "add_torrent.js 找不到 _hiScroll(高亮滚动跟随单点, 改名或挪走了? 同步本守阵)"
    # 只查**真代码**: 注释里讲原理(「禁用 scrollIntoView」)不算违规
    body = re.sub(r"^\s*//.*$", "", re.sub(r"/\*[\s\S]*?\*/", "", m.group(1)), flags=re.M)
    assert "scrollIntoView" not in body, \
        ("_hiScroll 不得用 scrollIntoView —— 它逐层滚动**所有可滚祖先**, 而 .add-dialog-body 就是"
         "overflow-y 容器: 开层过渡期会把整段说明文案一起滚走再弹回(2026-10-29 八修, 用户报「选中路径"
         "后再点下拉, 弹窗文字从上往下滑一次」; 同禁令先例 26-09-29-2142)")
    assert "scrollTop" in body and "getBoundingClientRect" in body, \
        "_hiScroll 必须手动差值调 scrollTop(block: nearest 语义, 只滚菜单内部那层)"
    assert "box.contains(n)" in body and "n === box" in body, \
        ("_hiScroll 的逐级滚动必须以菜单根为界(box.contains(n) 循环条件 + 到 box 即 break) —— "
         "不设界就会继续往上滚 .add-dialog-body / 页面, 等于把 scrollIntoView 的危害换个写法重犯")
    assert '[data-hi="1"]' in body, \
        "_hiScroll 找不到高亮项选择器 [data-hi=\"1\"](与模板 data-hi 绑定同源, 改了要两处同步)"


def test_frontend_pop_item_a11y_contract():
    """浮层可点击行 .pop-item 的 a11y 三分类契约守阵(issue 26-10-29-1335, R23-A-09)

    同一可点击行原语被三种浮层复用, 修复前是三套口径且 combobox 一路整段缺失(读屏听不出
    高亮项与面板开关、列选择器 Space 无反应、UI 切换听不出当前项)。守阵按修复定案的三分类逐项钉:
      选择式(combobox, <aq-combo-input> 单组件): 输入框 role=combobox + :aria-expanded +
        aria-autocomplete=list + :aria-controls(仅开层时指面板 —— 面板 v-if 关层即不在 DOM,
        常挂 = 悬空引用) + :aria-activedescendant(带界, 只指真实存在的候选项);
        面板 role=listbox + :id=inputId+'-pop' 与 aria-controls 同源; 候选行 role=option +
        :id + :aria-selected。候选 id 生成式单点是组件方法 comboOptId —— 输入侧与行侧
        各写一份必漂移, 守阵数出现次数(js 定义恰 1, 模板消费恰 3: 输入 1 + 两变体各 1);
        预置行不参与键盘索引, 不配 option 语义, aria-hidden 挂起(可点性读屏忽略, 点击仍在)。
      选择式同族(顶栏列选择器): role=button + Enter/Space 双键, handler 与 @click/@keyup.enter
        逐字同款; 筛选器项是基准锚一并钉住(参照被改 = 全族口径漂移, 同步本守阵)。
      导航式(顶栏 UI 切换 <a href>): 保留链接语义, 当前项 :aria-current="page"。
    右键菜单族(.ctx-item)键盘化是另一件(issue 06 重开条件), 本守阵不管。
    """
    combo_tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "combo-input.html"), encoding="utf-8").read()
    body = _tpl_body(combo_tpl, "tpl-combo-input")
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    topbar = open(os.path.join(STATIC_ROOT, "shared", "tpl", "topbar.html"), encoding="utf-8").read()

    # 1. 选择式: 输入框侧 combobox 语义(逐属性钉, 漂移即红)
    combo_controls = ''':aria-controls="menu ? inputId + '-pop' : null"'''
    combo_descendant = ''':aria-activedescendant="hi >= 0 && hi < options.length ? comboOptId(hi) : null"'''
    panel_binding = ''':id="inputId + '-pop'"'''
    assert 'role="combobox"' in body, "combobox 输入框缺 role=combobox(读屏不报组合框语义, issue 26-10-29-1335)"
    assert ':aria-expanded="menu"' in body, "combobox 输入框缺 :aria-expanded(面板开关状态读屏不播报)"
    assert 'aria-autocomplete="list"' in body, "combobox 输入框缺 aria-autocomplete=list(组合框补全模式语义)"
    assert combo_controls in body, "combobox 输入框缺 :aria-controls(必须仅开层时指面板 id, 关层置 null 防悬空引用)"
    assert combo_descendant in body, (
        "combobox 输入框缺 :aria-activedescendant(键盘高亮只写 hi 无 ARIA 出口 = "
        "读屏听不出当前第几项; 必须带界只指真实存在的候选项)"
    )

    # 2. 选择式: 面板 listbox + id 同源; 两处 v-for 变体候选行 option 语义各齐
    assert 'role="listbox"' in body and panel_binding in body, \
        "候选面板缺 role=listbox + :id=inputId+'-pop'(与输入框 aria-controls 同源)"
    assert body.count('role="option"') == 2, \
        "候选行两处 v-for(innerList 与非 innerList 变体)必须都带 role=option(缺一处 = 该变体读屏不报选项)"
    assert body.count(':id="comboOptId(i)"') == 2, \
        "候选行 :id 必须两处变体都走 comboOptId(i) 单点(手写 id 串 = 与 aria-activedescendant 漂移)"
    assert body.count(':aria-selected="i === hi"') == 2, \
        "候选行 :aria-selected 必须两处变体都有(读屏靠它听高亮, 视觉 .on 不够)"

    # 3. 候选 id 生成式单点: js 定义恰 1 次(钉定义形态, 注释提及不算), 模板消费恰 3 次(输入 1 + 两变体各 1)
    assert at.count("comboOptId(i) {") == 1, \
        "候选 id 生成式必须只在 add_torrent.js 定义一次(重复定义/多份生成式 = 输入侧与行侧漂移)"
    assert '"-opt-"' in at, "comboOptId 生成式里找不到 '-opt-' 后缀(面板 id 家族约定, 改名要同步本守阵)"
    assert body.count("comboOptId(") == 3, \
        "模板 comboOptId( 消费必须恰 3 处: 输入 aria-activedescendant 1 + 两个 v-for 变体各 1"

    # 4. 预置行: 不参与键盘索引就不配 option 语义, aria-hidden 让读屏忽略其可点性(点击仍在)
    m = re.search(r'<div v-if="presetLabel"[^>]*>', body)
    assert m, "combo-input.html 找不到预置行(改名/挪走了? 同步本守阵)"
    assert 'aria-hidden="true"' in m.group(0) and "role=" not in m.group(0), \
        "预置行必须 aria-hidden 且不配 role(option 语义要求参与键盘索引, 它不参与; 裸露可点性又会被读屏误报)"
    assert body.count('aria-hidden="true"') == 1, \
        "模板里 aria-hidden 只许挂在预置行上(候选行都必须能被读屏看到)"

    # 5. 选择式同族: 列选择器项 Enter/Space 双键, handler 逐字同款(与 @click 同式)
    m = re.search(r'<div v-for="c in def\.columns"[^>]*>', topbar)
    assert m, "topbar.html 找不到列选择器项(改名/挪走了? 同步本守阵)"
    col = m.group(0)
    assert '@keyup.enter="!c.locked && toggleColumn(def.id, c.key)"' in col and \
        '@keyup.space.prevent="!c.locked && toggleColumn(def.id, c.key)"' in col, \
        "列选择器项必须 Enter/Space 双键且 handler 逐字同款(Space 无反应 = 与筛选器项口径分裂)"
    # 6. 基准锚: 筛选器项的三键位(它是本族参照; 改它 = 全族口径漂移, 同步本守阵)
    assert '@keyup.enter="toggleFilterValue(f.field, o.value)"' in topbar and \
        '@keyup.space.prevent="toggleFilterValue(f.field, o.value)"' in topbar, \
        "筛选器项基准锚(Enter/Space 双键)被改 —— 全族 Space 口径参照没了, 同步本守阵"
    # 7. 导航式: UI 切换项当前值 aria-current=page(视觉 .on 不够, 读屏听不出当前项)
    m = re.search(r'<a v-for="o in uiOptions"[^>]*>', topbar)
    assert m, "topbar.html 找不到 UI 切换项(改名/挪走了? 同步本守阵)"
    ui_current = ''':aria-current="o.id === ui ? 'page' : null"'''
    assert ui_current in m.group(0), "UI 切换项缺 :aria-current=page(导航式当前项标注, 只靠 .on 上色读屏听不出)"


def test_frontend_ctx_menu_refit_by_measured_size():
    """浮层菜单开层后按**实测**尺寸重钳位(issue 26-10-06-1717 的接线守阵, 静态防回潮)

    症状: 批量菜单(约 10 项, 实测 393px)由 `_menuPos` 的常量 h=222 估算做视口钳位 ——
    锚点落在视口下部时菜单底越过下缘, 底部项(标签分类/导出/批量删除)真实点击不可达
    (Playwright 报 "element is outside of the viewport" 重试到超时)。这类几何缺陷 pytest
    跑不出来, 故这里只钉**接线**; 行为面由 e2e/menus.spec.mjs 的 CTX-fit test 兜底:
      ①_menuFit 必须按 offsetWidth/offsetHeight 实测算(把常量改大一号那种"修法"再犯即红);
      ②三个菜单容器(行右键/表头右键/文件优先级)各有 ref, 且与三个 state 对象各自的
        开层 watcher 里的 (stateKey, refName) 一一对上 —— 漏一处 = 那个菜单静默不钳位;
      ③watcher 必须在 $nextTick 里量(同步量到的是开层前的 DOM)。
    """
    import re

    static = STATIC_ROOT
    fb = open(os.path.join(static, "shared", "ui_feedback.js"), encoding="utf-8").read()
    state_js = open(os.path.join(static, "shared", "state.js"), encoding="utf-8").read()
    tpl = open(os.path.join(static, "shared", "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. 量测必须是**实测**: 两个 offset* 都要出现, 且以视口为界
    fit = re.search(r"_menuFit\(el, x, y\) \{(.*?)\n    \},", fb, re.S)
    assert fit, "ui_feedback.js 找不到 _menuFit(开层实测钳位单点, 改名或挪走了? 同步本守阵)"
    fit_body = fit.group(1)
    assert "el.offsetWidth" in fit_body and "el.offsetHeight" in fit_body, \
        "_menuFit 必须按 offsetWidth/offsetHeight 实测(退回常量估算 = issue 26-10-06-1717 复现)"
    assert "window.innerWidth" in fit_body and "window.innerHeight" in fit_body, \
        "_menuFit 必须以视口为界(innerWidth/innerHeight)"
    assert 'el.style.maxHeight = ""' in fit_body, \
        "_menuFit 必须每次先复位兜底限高(否则本次量到的是上一次压过的高度)"

    # 2. 三容器 ref + 三开层 watcher 成对
    for key, ref in (("menu", "ctxMenu"), ("headMenu", "headMenuEl"), ("filePrio", "filePrioEl")):
        assert f'ref="{ref}"' in tpl, \
            f"ctx-menus.html 缺 ref=\"{ref}\"({key} 菜单量测拿不到容器对象)"
        m = re.search(rf"\n    {key}\(\) \{{\n(.*?)\n    \}},", state_js, re.S)
        assert m, (
            f"state.js 缺 {key} 开层 watcher —— 开层入口有五六处(menu.js/shows.js/drawer.js), "
            f"直挂方法必漏, 与 _fitAddPop 同范式走 watcher 单点"
        )
        assert f'_menuFitRefit("{key}", "{ref}")' in m.group(1), \
            f"{key} watcher 必须调 _menuFitRefit(\"{key}\", \"{ref}\")(stateKey/ref 对不上就量不到)"
        assert "$nextTick" in m.group(1), \
            f"{key} watcher 必须在 $nextTick 里量(同步量到的是开层前的 DOM, 高度恒 0)"

    # 3. 出口现读现取: 闭包捕获旧对象/旧元素会在"开着又换一行"时把旧位置写回新菜单
    refit = re.search(r"_menuFitRefit\(stateKey, refName\) \{(.*?)\n    \},", fb, re.S)
    assert refit, "ui_feedback.js 找不到 _menuFitRefit(watcher 出口单点, 改名或挪走了? 同步本守阵)"
    refit_body = refit.group(1)
    assert "this[stateKey]" in refit_body and "this.$refs[refName]" in refit_body, \
        "_menuFitRefit 必须现读 this[stateKey] / this.$refs[refName](闭包捕获会在重开时写错位置)"
    assert ".visible" in refit_body, "_menuFitRefit 必须守 visible(菜单已关就别再回写位置)"


def test_frontend_add_combo_label_clear_mask_and_refit():
    """添加种子三下拉「第二轮遗留四项」接线守阵(2026-10-03 报障, 静态防回潮)

    上一轮(失焦即收 + 开层限高)之后剩下的四条, 根因同样全在"pytest 看不见的事件/几何接线"里:
      1. **点字段 label 稳定复现下拉闪烁(两轮才修对)**: label 的 click 默认动作把 click **转发**
         给 for= 的输入框, 而它自己那次 click 先冒泡到 window(lifecycle 收层名单) ⇒ 必须
         @click.stop。但只挡 click 赢不了主竞态: label 的 **mousedown** 默认动作先把已聚焦的
         输入框 blur 掉, addPopBlurClose 的 40ms 合帧定时器在**按住期间**(人手 80~150ms 必然
         > 40ms)先触发收层, 松手后 label 转发回焦再重开 = 闪烁。修法 = 四个 combo 的字段 label
         一律 @mousedown.prevent + @click.stop(缺一即回归)。
      2. **三个 combobox 没有清空按钮**: 补 .add-pop-clear, 必须 @mousedown.prevent(不拦默认
         动作按钮会抢焦点 → 输入框失焦走 addPopBlurClose 把下拉收掉, 清完想接着挑就多点一次)。
      3. **拖选输入框文字、终点落在遮罩上抬手 = 关窗**: click 的 target 是 mousedown/mouseup 的
         **公共祖先**, 这情形公共祖先就是遮罩 ⇒ @click.self 误判成"点空白关窗"。修法 = 遮罩
         改成 mousedown 记臂位 + mouseup.self 才关(全仓 11 处遮罩统一, 含无输入框的弹层 ——
         拖选普通文字同样会误关)。
      4. **选中分类后逐字删除, 下拉把窗口撑变形**: 限高只在开层那一刻按**当时**的候选量算过,
         过滤词变化(候选从 1 条涨回全量)时菜单没关过, 开层 watcher 不触发 ⇒ 旧限高不更新。
         修法 = 三个输入值各挂 watcher(开着才重限), meta 对话框的分类下拉同族一并补。
      5. **四轮 JS 收层守卫(2026-10-04 用户报三修后真机仍闪)**: 三修的 Chromium 探针自校验证明
         修饰符修法本身有效(摘掉即复现完整闪烁链), 用户症状与"浏览器跑的还是旧模板"一致 ——
         页签长开不刷新时模板/JS 以加载那一刻为准, 服务端更新到不了。故收层再加 JS 单点守卫
         _popBlurShouldHold: addPopBlurClose/metaCatBlurClose 的 40ms 定时器触发那刻, 焦点已回
         本族输入框或本族 label 转发 click 仍在途(mousedown 记录器 capture 记落点) → 跳过收层。
         模板修饰符在 = 纯 no-op(mousedown 已被 prevent, 定时器不武装); 缺位 = 独立根除闪烁,
         任何模板/JS 代际混合都安全。
      6. **点面板头/空态文案把面板点没了(2026-10-29 六修)**: 面板里除候选行/预置行之外还有两处
         **非交互区** —— .pop-head(标题+计数) 与 .pop-empty(空态文案)。它们点了什么都不该发生, 但
         mousedown 的默认动作把焦点从输入框抢走 → @focusout → 40ms 合帧后收层 = 面板"点一下就消失"
         (光标本来就在候选行正上方, 误触概率极高)。修法 = 焦点纪律挂在**面板根**
         (@mousedown.prevent)一处覆盖全部非交互子元素; 逐个给 .pop-head 打补丁 = 空态那处静默复发
         (e2e 两条断言必须配对: 单看"点头不收"放得过半截修法)。
      7. **按下与抬起落在不同元素, 面板点一下就关(2026-10-29 七修)**: 浏览器把 click 的 target 定成
         mousedown/mouseup 两者的**公共祖先** —— 按在输入框、抬到行内留白/面板/整行时, click 目标是
         `.add-input-row`, 那一层没有 @click.stop 就冒泡到 lifecycle 的 window 收层名单, 面板立刻关。
         无焦点时最易踩(面板在按住期间才挂载, DOM 在按下与抬起之间变化), 皮肤差异也由此而来(输入行
         差 2px + drop-in 从 -4px 起)。修法 = 组件根挂 @click.stop, **只挂组件根**: 挂到对话框层会把
         "点对话框别处收层"一起废掉(e2e 反向守门断言就在测这条)。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()
    dg = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    lf = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    mgr = open(os.path.join(shared, "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()
    xt = open(os.path.join(shared, "tpl", "combo-input.html"), encoding="utf-8").read()

    # 1. 四个 combo 的字段 label 全部 @mousedown.prevent + @click.stop(漏一个 = 那个下拉点 label 稳定闪烁;
    #    prevent 挡 mousedown 默认动作的 blur(40ms 合帧窗赢不了人手按住时长), stop 挡 window click 收层)
    for holder, input_id in (
        ("mgr", "ad-save-path"), ("mgr", "ad-category"), ("mgr", "ad-tags"), ("pv", "meta-category")
    ):
        src = mgr if holder == "mgr" else pv
        m = re.search(rf'<label[^>]*for="{input_id}"[^>]*>', src, re.S)
        assert m, f"找不到 for=\"{input_id}\" 的字段 label(改结构了? 同步本守阵)"
        assert "@click.stop" in m.group(0), \
            (f"label[for={input_id}] 缺 @click.stop —— 点它会走「window click 收层 → label 转发 "
             f"click 重开」= 下拉闪烁再现(输入框已聚焦, @focusout 挡不住这一路)")
        assert "@mousedown.prevent" in m.group(0), \
            (f"label[for={input_id}] 缺 @mousedown.prevent —— label 的 mousedown 默认动作把已聚焦的"
             f"输入框 blur 掉, addPopBlurClose 的 40ms 合帧定时器在按住期间(人手 80~150ms > 40ms)"
             f"先收层, 松手 label 转发回焦再重开 = 闪烁(2026-10-04 三修, 真机按住时序实测)")

    # 2. 三个 combobox 内嵌清空(x): 按钮本体收敛进组件模板 #tpl-combo-input(clear-kind 参数化,
    #    issue 26-10-20-2230), 调用点传 kind + @clear 接线; 模板侧钉 has-clear + 双修饰符 + 非空显形
    tpl_seg = re.search(r'id="tpl-combo-input">([\s\S]*?)</script>', xt, re.S)
    assert tpl_seg, "combo-input.html 找不到 #tpl-combo-input(combobox 共享模板)"
    tpl_body = tpl_seg.group(1)
    assert "'has-clear': !!clearKind" in tpl_body, "组件模板输入行缺 has-clear 绑定(清空钮靠它让出右内边距)"
    assert 'class="add-pop-clear"' in tpl_body, "组件模板缺 .add-pop-clear 清空按钮"
    assert 'v-if="clearKind && modelValue"' in tpl_body, "组件模板清空钮缺非空显形条件(空框也显示 = 多点一次空操作)"
    btn = re.search(r'<button[^>]*add-pop-clear[\s\S]{0,200}?>', tpl_body)
    assert btn and "@mousedown.prevent" in btn.group(0), \
        "组件模板清空钮缺 @mousedown.prevent(不拦默认动作会抢焦点 → 下拉被失焦收掉)"
    assert btn and "@click.stop" in btn.group(0), \
        ("组件模板清空钮缺 @click.stop —— 它的 click 会冒泡到 lifecycle 的 window "
         "收层名单, 点一下 x 顺手把下拉一起收了(真机走查实测: 清空后菜单消失)")
    assert "$emit('clear', clearKind)" in tpl_body, "组件模板清空钮没向调用方 emit clear(kind)"
    for input_id, kind, field in (
        ("ad-save-path", "path", "addSavePath"), ("ad-category", "cat", "addCategory"), ("ad-tags", "tag", "addTags")
    ):
        i = mgr.index(f'input-id="{input_id}"')
        seg = mgr[mgr.rindex("<aq-combo-input", 0, i):i + 900]
        assert f'clear-kind="{kind}"' in seg, f"#{input_id} 的调用点没传 clear-kind=\"{kind}\"(无清空钮)"
        assert f'v-model="{field}"' in seg, f"#{input_id} 的调用点没把 {field} 绑进 v-model(清空钮非空显形条件失效)"
        assert '@clear="clearAddField"' in seg, f"#{input_id} 的清空钮没接 @clear=\"clearAddField\""
    clear_body = re.search(r"clearAddField\(kind\) \{(.*?)\n    \},", at, re.S)
    assert clear_body, "add_torrent.js 找不到 clearAddField(三个 combobox 的清空单点)"
    for field in ("addSavePath", "addCategory", "addTags"):
        assert f"this.{field} = \"\";" in clear_body.group(1), f"clearAddField 不清空 {field}"

    # 6. 面板根挂 @mousedown.prevent(2026-10-29 六修): 面板内**非交互区**(.pop-head 标题+计数 /
    #    .pop-empty 空态文案)点了不许把焦点从输入框抢走 —— 抢走即 @focusout → 40ms 合帧收层
    #    = 面板"点一下就消失"。修饰符必须在**根**: 逐个给非交互子元素打补丁, 新增一处即静默复发
    #    (本轮红验证: 只给 .pop-head 挂 prevent 时"点头不收"仍绿, 空态那条才抓到)。
    root_tag = re.search(r'<div v-if="menu" class="pop-menu add-pop"[^>]*>', tpl_body)
    assert root_tag, "组件模板找不到面板根(.pop-menu.add-pop)(改名或挪走了? 同步本守阵)"
    assert "@mousedown.prevent" in root_tag.group(0), \
        ("组件模板面板根缺 @mousedown.prevent —— 点面板头/空态文案时 mousedown 的默认动作把焦点从"
         "输入框抢走, @focusout 的 40ms 合帧定时器收层 = 面板点一下就消失(2026-10-29 六修); "
         "修饰符必须挂根上一处覆盖全部非交互子元素, 逐个打补丁 = 往面板里加一处展示节点就复发")
    assert "@click.stop" in root_tag.group(0), \
        "组件模板面板根丢了 @click.stop(面板内点击会冒泡到 lifecycle 的 window 收层名单, 点一下就把下拉收了)"

    # 7. 组件**根**挂 @click.stop(2026-10-29 七修): 按下与抬起落在不同元素时, click 的 target 是两者的
    #    **公共祖先**(.add-input-row / 面板 / 整行) —— 那一层没人挡就冒泡到 lifecycle 的 window 收层名单
    #    ⇒ 面板点一下就关。无焦点时最易踩: 面板在按住期间才挂载, DOM 在按下与抬起之间变化, 抬起落点被
    #    改写的机会就在那一段(两皮肤输入行差 2px + drop-in 从 -4px 起 = 皮肤差异的来源)。
    #    ⚠ 只许挂在组件根: 挂到更外层(对话框)会把"点对话框别处收层"一起废掉。
    row_tag = re.search(r'<div class="add-input-row"[^>]*>', tpl_body)
    assert row_tag, "组件模板找不到输入行根(.add-input-row)(改名或挪走了? 同步本守阵)"
    assert "@click.stop" in row_tag.group(0), \
        ("组件模板输入行根缺 @click.stop —— 按下与抬起落在不同元素时 click 的 target 是公共祖先"
         "(.add-input-row/面板), 事件冒泡到 window 收层名单 = 面板点一下就关(2026-10-29 七修); "
         "它必须挂在组件根, 挂到对话框层会把「点对话框别处收层」一起废掉")

    # 3. 遮罩关窗: mousedown 记臂位 + mouseup.self 才关; 全仓不许再有 @click.self
    #    (issue 26-10-20-2231 收敛后手势对单点在 <aq-modal> 组件模板(tpl/dialog-shell.html),
    #    调用点不再出现遮罩字面量 —— 改为组件模板一处手势对 + 调用点 :close 接线清点)
    shell = open(os.path.join(shared, "tpl", "dialog-shell.html"), encoding="utf-8").read()
    masks = re.findall(r'<div v-if="open" :class="maskClass"[\s\S]{0,240}?>', shell)
    assert len(masks) == 1, f"dialog-shell.html 应恰有 1 处遮罩(组件单点), 实数 {len(masks)}"
    assert '$root.maskDownSelf($event)' in masks[0] and '$root.maskCloseIfArmed(close, ...closeArgs)' in masks[0], \
        ("aq-modal 的遮罩没接「mousedown 记臂位 + mouseup.self 才关」—— @click.self 会被"
         "『拖选文字终点落在遮罩上抬手』误判成点空白关窗; 手势经 $root 回调根方法(读根 _maskArmed)")
    for name in ("dialogs-mgr.html", "dialogs.html", "popovers.html", "move-dialog.html", "dialog-shell.html"):
        txt = open(os.path.join(shared, "tpl", name), encoding="utf-8").read()
        live = re.sub(r"<!--[\s\S]*?-->", "", txt)  # 注释里讲原理不算(只查真接线)
        assert "@click.self" not in live, \
            f"{name} 仍残留 @click.self 遮罩关窗(拖选文字抬手会误关窗)"
    # 调用点清点: 全部带遮罩对话框都必须走 <aq-modal>(漏一处 = 手抄外壳回潮);
    # 9 处调用覆盖 10 个开态(mgr 两态共用一份模板), speed-pop(无遮罩异形)直用 head 组件
    callsites = {
        "dialogs-mgr.html":
            (
                ':open="addOpen"', ':close="closeAddTorrent"', 'mask-class="modal-mask add-dialog-mask"',
                ':open="dirBrowse.open"', ':close="closeDirBrowse"', 'mask-class="modal-mask dir-browse-mask"'
            ),
        "dialogs.html":
            (
                ':open="statsOpen"', ':close="closeStats"', 'icon-class="ico-chart"',
                '<aq-modal-head icon="#i-gauge" title="限速" :close="closeSpeedDialog">'
            ),
        "popovers.html":
            (
                ':close="closeMgr"', ':open="metaOpen"', ':close="closeMeta"', ':open="modal.visible"',
                ':close="resolveModal"', ':close-args="[false]"', ':x="false"', ':open="historyOpen"',
                ':close="closeHistory"', 'icon-class="ico-history"', '<template #extra>', ':open="kbHelpOpen"',
                ':close="closeKbHelp"'
            ),
        "move-dialog.html": (':open="moveOpen"', ':close="closeMove"'),
    }
    n_calls = 0
    for name, needles in callsites.items():
        ctxt = open(os.path.join(shared, "tpl", name), encoding="utf-8").read()
        for needle in needles:
            assert needle in ctxt, f"{name} 缺 {needle}(对话框没走 <aq-modal>? 手抄外壳回潮)"
        n_calls += ctxt.count("<aq-modal ")
    assert n_calls == 9, f"<aq-modal> 调用点应 9 处(mgr 两态共用一份), 实数 {n_calls}"
    arm = re.search(r"maskDownSelf\(e\) \{(.*?)\n    \},", dg, re.S)
    assert arm and "e.target === e.currentTarget" in arm.group(1), \
        "dialogs.js::maskDownSelf 必须判 target === currentTarget(只有按在遮罩上才算起手)"
    close_arm = re.search(r"maskCloseIfArmed\(closeFn, \.\.\.args\) \{(.*?)\n    \},", dg, re.S)
    assert close_arm and "if (!this._maskArmed) return;" in close_arm.group(1), \
        "dialogs.js::maskCloseIfArmed 必须先判 _maskArmed(起手在对话框内的那一笔不许关窗)"

    # 4. 过滤词变化重限高: 三个输入值 watcher + meta 侧三处(候选到位/开层/过滤词)
    for val, pop in (("addCategory", "addCatMenu"), ("addTags", "addTagMenu"), ("addSavePath", "addPathPop")):
        assert re.search(rf"\n    {val}\(\) \{{\n      if \(this\.{pop}\) this\._fitAddPop", at), \
            (f"add_torrent.js 缺 {val} 的 watcher —— 打开时按当时的候选量限过高, 删字让候选涨回全量时"
             f"菜单没关过(开层 watcher 不触发), 下拉会把窗口撑变形")
    for key, guard in (
        ("metaCatMenu(v)", "if (v)"), ("metaCatInput()", "if (this.metaCatMenu)"),
        ("metaCategories()", "if (this.metaCatMenu)")
    ):
        assert re.search(rf"\n    {re.escape(key)} \{{\n      {re.escape(guard)} this\._fitAddPop", dg), \
            f"dialogs.js 缺 {key} 的限高 watcher(meta 分类下拉与三下拉同族, 撑变形同样会犯)"
    assert 'if (!this.addOpen && !this.metaOpen && !this.moveOpen) return;' in at, \
        "_fitAddPop 必须同时放行 meta 对话框与设定位置对话框(三处共用同一套限高, 只认 addOpen 会让 meta/move 侧恒不生效)"

    # 5. meta 分类下拉补失焦收层 + 进 window click 兜底名单(原本两处都漏 = 点对话框别处下拉不收)
    #    (收敛 issue 26-10-20-2230: 输入框进组件模板, 字段接线在调用点 @blur)
    m = re.search(r'<aq-combo-input input-id="meta-category"(.*?)>', pv, re.S)
    assert m and '@blur="metaCatBlurClose"' in m.group(1), \
        "#meta-category 缺 @blur 收层(点对话框里别的地方下拉悬着不收)"
    blur = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert blur and '_popBlurArm("_metaPopBlurT", ["meta-category"]' in blur.group(1), \
        "metaCatBlurClose 必须走 _popBlurArm 合帧单点(同步收层会被 label 转发回焦打断 = 闪烁)"
    open_meta = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dg, re.S)
    assert open_meta and '_popBlurCancel("_metaPopBlurT")' in open_meta.group(1), \
        "openMetaCatMenu 必须撤销挂起的失焦收层(焦点转回输入框时菜单不闪)"
    assert "this.metaCatMenu = false;" in lf, \
        "lifecycle.js 的 window click 兜底名单缺 metaCatMenu(与三下拉同层, 漏了靠 focusout 单点兜)"

    # 6. 清空钮样式三皮肤成对(漏一档 = 该皮肤按钮无样式: 透明方块 + 文字被压在底下)
    for ui in _UI_ALL:
        css_dir = os.path.join(STATIC_ROOT, ui, "css")
        blob = "".join(
            open(os.path.join(css_dir, f), encoding="utf-8").read()
            for f in sorted(os.listdir(css_dir)) if f.endswith(".css")
        )
        assert ".add-pop-clear" in blob, f"{ui} 缺 .add-pop-clear 样式(清空钮无尺寸/无 hover)"
        assert ".add-input-row.has-clear" in blob, f"{ui} 缺 .has-clear 右内边距(文字会被按钮压住)"

    # 7. 四轮 JS 收层守卫(2026-10-04): 40ms 定时器收层前必须问 _popBlurShouldHold ——
    #    焦点已回本族输入框 / 本族 label 转发 click 仍在途 → 不收。模板修饰符缺位(旧页签
    #    残留模板)时由它独立根除「按住期收层 → 松手回焦重开」, 不依赖模板 JS 同代到达。
    assert "window.addEventListener(\"mousedown\", this._popLabelDownRecorder, { capture: true });" in at, \
        "add_torrent.js mounted 缺 mousedown capture 记录器(守卫没有落点数据 = 形同虚设)"
    assert "removeEventListener(\"mousedown\", this._popLabelDownRecorder" in at, \
        "add_torrent.js unmounted 缺记录器移除(热重载后句柄堆叠, 每次点击记 N 笔)"
    hold = re.search(r"_popBlurShouldHold\(ids\) \{(.*?)\n    \},", at, re.S)
    assert hold, "add_torrent.js 找不到 _popBlurShouldHold(收层守卫单点)"
    assert "document.activeElement" in hold.group(1) and "ids.includes(ae.id)" in hold.group(1), \
        "_popBlurShouldHold 必须先判「焦点已回本族输入框」(转发 click 已落地 → 不收)"
    assert "performance.now() - rec.t <= 350" in hold.group(1), \
        "_popBlurShouldHold 必须带 350ms 新鲜度上界(防旧记录误挡后续无 mousedown 的失焦, 如 Tab)"
    # 收敛(issue 26-10-20-2230)后 addPopBlurClose/metaCatBlurClose 是薄封装, 家族 id 名单随
    # _popBlurArm 实参传入、守卫调用在单点内 —— 断言入口传对名单 + 单点内恒问守卫
    arm = re.search(r"_popBlurArm\(timerKey, ids, close\) \{(.*?)\n    \},", at, re.S)
    assert arm and "_popBlurShouldHold(ids)" in arm.group(1), \
        "_popBlurArm 收层前没问守卫(模板修饰符缺位时 JS 守卫独立根除按住期收层闪烁)"
    add_close = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert add_close and '["ad-save-path", "ad-category", "ad-tags"]' in add_close.group(1), \
        "addPopBlurClose 没传三字段的家族 id 名单(缺一即该字段守卫失效)"
    meta_close = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert meta_close and '["meta-category"]' in meta_close.group(1), \
        "metaCatBlurClose 没传 meta 分类的家族 id(meta 分类下拉与三下拉同族, 缺位同闪)"


def test_frontend_move_dialog_combobox_wiring():
    """设定位置对话框(2026-10-13)保存路径下拉接线守阵(静态防回潮)

    单种子/单组/多选批量三入口统一改, 保存路径下拉候选按「最近使用」排序(与添加种子保存路径同口径)。
    钉:
      1. 三入口名/签名(editMove/editMoveMulti/editMoveGroup)与下游投递(editMove→_editPost,
         editMoveMulti/editMoveGroup→_bulkEditPost)不变 —— 守阵 + 触发登记表钉这些;
      2. 排序单点复用 _addOrderByRecent + _addRecencyMaps(跨视图取数, 与添加种子同口径);
      3. combobox 收层/限高/悬同与添加种子三下拉 + meta 分类同套口径(@focusout + 40ms合帧 +
         _popBlurShouldHold + watcher重限 + comboHoverIdx move 分支);
      4. 对话框模板接线: moveOpen 遮罩 + move-path label @mousedown.prevent @click.stop +
         @focusout收层 + @keydown键盘导航 + ref=movePathList + 三皮肤成对 CSS;
      5. 几何修(2026-10-19 用户报「弹窗太小, 下拉显示不全要滚动」): 组合框是表单最后一项,
         朝下开的下拉必伸出 .add-dialog-body 底沿被裁且撑大其 scrollHeight ⇒ 根元素按
         movePathMenu 挂 .pop-open 类 + 三皮肤成对的开层预留(padding-bottom 272px)与
         860 宽档(--modal-w-add)规则, 下拉完整落在对话框内、弹窗体零新增滚动。
      6. 二修(2026-10-29 用户报「点下拉选项就触发移动」+「窗口太小, 点下拉高度跳变」):
         ①点选候选只回填(moveApplyPath 体内不得出现 submitMoveDialog), 移动只由按钮/手输回车发起;
         ②手输回车仍提交 —— 键盘单点回退分支走 (ctx.onEnter || ctx.onPick)(v), 只有 move 传钩子;
         ③空路径按钮置灰; ④打开只聚焦不展开(openMoveDialog 置 moveSuppressOpen, openMovePathMenu
         首行消费); ⑤三皮肤成对: 收层态基线 min-height 360px + 动作条 margin-top:auto 钉底 +
         padding-bottom 200ms 过渡(替掉 0↔272 硬切), 过渡后 settle(MOVE_POP_SETTLE_MS=240)重测限高。
      7. 三修(2026-10-29 用户报「点下拉框, 下拉框出现后自动弹回」): 遮罩默认 align-items:center,
         开层增高上下对半扩 ⇒ 输入行连同刚展开的面板整体上移 77px, 面板顶到光标底下(再点一下即
         命中候选/面板头 = 面板"自动弹回")⇒ 遮罩挂 .move-dialog-mask 改 flex-start + margin-top
         复刻收层态居中偏移, **增长只朝下**。三皮肤成对 + 模板 mask-class 接线。
      8. 四修(2026-10-29 用户报「下拉框出现时弹窗有一瞬间出现滚动条」): 预留 padding 是过渡的,
         面板瞬间挂载 ⇒ 开层头 ~110ms 面板伸出 body 的 padding 盒(实测溢出 256→0), body 是
         overflow-y:auto 的滚动容器 ⇒ 闪滚动条 + 内容横向挤一个滚动条宽。开层期溢出的只有预留
         空白 ⇒ 关掉滚动条(收层态仍 auto, 矮视口 body 兜底滚动不受影响)。
      9. 五修(2026-10-29 用户报「下拉框消失时弹窗仍会有一瞬间出现滚动条」): 收层时面板**不立刻
         离场** —— 离场淡出(~120ms)期间它仍在 DOM 里、高度不变, 而 .pop-open 已摘 ⇒ 溢出涨到
         254px(实测)。开关必须跟「面板是否存在」走(`:has(.add-pop)`), 跟开合状态走只覆盖开层。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    dr = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    cmd = open(os.path.join(shared, "commands.js"), encoding="utf-8").read()
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()
    lf = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    st = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "move-dialog.html"), encoding="utf-8").read()

    # 1. 三入口名/签名 + 下游投递不变(与触发登记表/守阵钉)
    assert re.search(r"\n    async editMove\(h = \"\"\)", dr), "drawer.js 缺 editMove(h) 单种子入口"
    assert re.search(r"\n    async editMoveMulti\(targets = null", dr), "drawer.js 缺 editMoveMulti(targets = null) 多选入口"
    assert re.search(r"\n    editMoveGroup\(\)", cmd), "commands.js 缺 editMoveGroup() 单组入口"
    assert "this._editPost(this.moveSingleHash, \"location\"" in dr, "submitMoveDialog 单种子没走 _editPost"
    assert "this._bulkEditPost(this.moveTargets, \"location\"" in dr, "submitMoveDialog 批量没走 _bulkEditPost"

    # 2. 排序单点复用(与添加种子同口径, 跨视图取数)
    assert "_addOrderByRecent(paths, recent.path)" in dr, "loadMoveOptions 没走 _addOrderByRecent 排序单点"
    assert "this._addRecencyMaps()" in dr, "loadMoveOptions 没走跨视图取数单点 _addRecencyMaps"

    # 3. combobox 收层/限高/悬同同套口径(收敛 issue 26-10-20-2230: 合帧+守卫走 add_torrent.js
    #    的 _popBlurArm 单点, 各处只剩定时器键/家族名单/收层动作)
    blur = re.search(r"movePathBlurClose\(\) \{(.*?)\n    \},", dr, re.S)
    assert blur and '_popBlurArm("_movePopBlurT", ["move-path"]' in blur.group(1), \
        "movePathBlurClose 必须走 _popBlurArm 合帧单点(同步收层会被 label 转发回焦打断 = 闪烁)"
    open_move = re.search(r"openMovePathMenu\(\) \{(.*?)\n    \},", dr, re.S)
    assert open_move and '_popBlurCancel("_movePopBlurT")' in open_move.group(1), \
        "openMovePathMenu 必须撤销挂起的失焦收层(焦点转回输入框时菜单不闪)"
    for key, guard in (
        ("movePathMenu(v)", "if (v)"), ("movePathInput()", "if (this.movePathMenu)"),
        ("movePathOptions()", "if (this.movePathMenu)")
    ):
        assert re.search(rf"\n    {re.escape(key)} \{{\n      {re.escape(guard)} this\._fitAddPop", dr), \
            f"drawer.js 缺 {key} 的限高 watcher(与三下拉 + meta 同族, 撑变形同样会犯)"
    assert 'comboHoverIdx("move"' in at or "kind === \"move\"" in at, \
        "comboHoverIdx 缺 move 分支(悬同接管走错 state 对象 = 上下键选中项闪烁)"

    # 4. 对话框模板接线
    assert ':open="moveOpen"' in pv, "move-dialog.html 缺 moveOpen 开合(对话框没走 <aq-modal>?)"
    m = re.search(r'<label[^>]*for="move-path"[^>]*>', pv, re.S)
    assert m and "@click.stop" in m.group(0) and "@mousedown.prevent" in m.group(0), \
        "move-path label 缺 @click.stop + @mousedown.prevent(与三下拉 + meta 同因同修)"
    mi = re.search(r'<aq-combo-input input-id="move-path"(.*?)>', pv, re.S)
    assert mi and '@blur="movePathBlurClose"' in mi.group(1), "#move-path 缺 @blur 收层"
    assert mi and '@keydown="onMovePathKeydown' in mi.group(1), "#move-path 缺 @keydown 键盘导航"
    assert 'menu-ref="movePathList"' in (mi.group(1) if mi else ""), \
        "move-dialog.html 缺 menu-ref=movePathList(限高量拿不到容器; 收敛后 ref 经组件方法函数写根 $refs)"
    assert ':close="closeMove"' in pv, "move 对话框缺 :close 接线(遮罩手势对在组件模板, 调用点只交 close)"
    # 4b. 几何修(2026-10-19): 根元素按 movePathMenu 挂 .pop-open —— 下拉开层时对话框给 body 预留
    # 整高(规则在 5), 否则下拉伸出 body 被裁 + scrollHeight 撑大, 用户必须滚弹窗才能用下拉
    assert re.search(r':width-class="\[\'add-dialog move-dialog\', \{ \'pop-open\': movePathMenu \}\]"', pv), \
        "move-dialog.html 缺 pop-open 并入 width-class(下拉开层时对话框不预留空间)"

    # 4d. 三修(2026-10-29): 开层增长只朝下 —— 遮罩类必须接线(否则居中容器里增高上下对半扩,
    #     输入行上移 77px 把刚展开的面板顶到光标底下 = 用户报的「下拉框出现后自动弹回」)
    assert 'mask-class="modal-mask move-dialog-mask"' in pv, \
        "move-dialog.html 遮罩缺 .move-dialog-mask 类(增长方向改不了 = 面板被顶到光标底下, 2026-10-29 三修回归)"

    # 4c. 二修(2026-10-29): 点选只回填 / 手输回车仍提交 / 空态置灰 / 打开不自动展开
    apply_body = re.search(r"moveApplyPath\(p\) \{(.*?)\n    \},", dr, re.S)
    assert apply_body, "drawer.js 找不到 moveApplyPath(点选候选的回填单点)"
    assert "submitMoveDialog" not in apply_body.group(1), \
        "moveApplyPath 又调了 submitMoveDialog —— 点选候选直接移动(2026-10-29 报障回归)"
    assert "this.movePathInput = p" in apply_body.group(1), "moveApplyPath 必须回填输入框"
    assert "(ctx.onEnter || ctx.onPick)(v)" in at, \
        "comboKeydown 回退分支没走 ctx.onEnter 钩子(手输回车提交链断: 缺省仍须回落 onPick)"
    assert "onEnter: (p) =>" in dr, "onMovePathKeydown 没传 onEnter(手输路径回车不再提交)"
    assert re.search(r'<button class="bt primary" :disabled="moveBusy \|\| !movePathInput\.trim\(\)"', pv), \
        "「设定位置」按钮缺空路径置灰(按钮是唯一鼠标提交路径, 空态点了才 toast 太笨)"
    assert "this.moveSuppressOpen = true" in dr, \
        "openMoveDialog 没置抑制标志(打开即自动展开下拉 = 第一眼开层态, 收层时高度骤变)"
    assert open_move and "if (this.moveSuppressOpen) { this.moveSuppressOpen = false; return; }" in open_move.group(1), \
        "openMovePathMenu 首行缺抑制标志消费(打开就弹面板; 标志还须只消费一次, 后续点击仍展开)"
    assert re.search(r"const MOVE_POP_SETTLE_MS = 240;", dr), \
        "drawer.js 缺 MOVE_POP_SETTLE_MS 常量(过渡期量到的净空只有一半, 不重测会把列表误限到 120px)"
    assert "_movePopSettle()" in open_move.group(1), "openMovePathMenu 没触发过渡后重测限高"

    # 5. 三皮肤成对 CSS(漏一档 = 该皮肤对话框无样式)
    for ui in _UI_ALL:
        css_dir = os.path.join(STATIC_ROOT, ui, "css")
        blob = "".join(
            open(os.path.join(css_dir, f), encoding="utf-8").read()
            for f in sorted(os.listdir(css_dir)) if f.endswith(".css")
        )
        assert ".modal.move-dialog" in blob, f"{ui} 缺 .modal.move-dialog 样式(对话框无宽度)"
        assert ".move-targets" in blob, f"{ui} 缺 .move-targets 样式(目标行无排版)"
        assert re.search(r"\.modal\.move-dialog \{\s*width:\s*var\(--modal-w-add\)", blob), \
            f"{ui} 的 .modal.move-dialog 宽度未走 --modal-w-add(860 宽档, 与添加种子同宽; 560 窄档路径项 ellipsis 少显示)"
        assert re.search(r"\.modal\.move-dialog\.pop-open \.add-dialog-body \{[^}]*padding-bottom:\s*272px", blob), \
            f"{ui} 缺 .pop-open 开层预留规则(下拉伸出 body 被裁 + scrollHeight 撑大 = 用户须滚弹窗; 272px = 面板头 ~46 + 列表 210 + 顶距 4 + 余量)"
        # 四修(2026-10-29): 预留是过渡的、面板是瞬间挂载的 ⇒ 开层头 ~110ms 面板伸出 body(padding 盒)
        # 之外, body 是 overflow-y:auto 的滚动容器 ⇒ 闪一条滚动条(还横向挤一个滚动条宽)。开层期溢出
        # 的只有预留空白 ⇒ 关滚动。五修(同日): 收层时面板离场淡出(~120ms)期间仍在 DOM 里、高度不变,
        # 而 .pop-open 已摘 ⇒ 开关必须跟「面板是否存在」走(:has), 跟开合状态走会漏掉收层那一段。
        assert re.search(r"\.modal\.move-dialog:has\(\.add-pop\) \.add-dialog-body \{[^}]*overflow:\s*hidden", blob), \
            f"{ui} 缺 .move-dialog:has(.add-pop) 的 overflow:hidden(面板在 DOM 期间(body 是滚动容器)闪滚动条; " \
            "只挂 .pop-open 会漏掉离场淡出那 ~120ms)"
        # 二修(2026-10-29): 基线抬到 360(治「窗口太小」) + 动作条钉底 + padding 过渡(治「高度跳变」)
        assert re.search(r"\.modal\.move-dialog \{\s*width:\s*var\(--modal-w-add\);\s*min-height:\s*min\(360px,\s*calc\(100vh - 120px\)\)", blob), \
            f"{ui} 的 .modal.move-dialog 缺收层态基线 min-height(原实测 243px = 用户报的「窗口太小」)"
        assert re.search(r"\.modal\.move-dialog \.modal-actions \{[^}]*margin-top:\s*auto", blob), \
            f"{ui} 动作条没钉底(基线抬高后按钮会浮在中间)"
        assert re.search(r"\.modal\.move-dialog \.add-dialog-body \{[^}]*transition:\s*padding-bottom\s+200ms", blob), \
            f"{ui} 缺 padding-bottom 过渡(0↔272 硬切 = 开/收下拉高度瞬跳, 2026-10-29 报障)"
        # 三修(2026-10-29): 增长只朝下 —— 遮罩改 flex-start + margin-top 复刻收层态居中偏移
        assert re.search(r"\.modal-mask\.move-dialog-mask \{[^}]*align-items:\s*flex-start", blob), \
            f"{ui} 缺 .move-dialog-mask 的 flex-start(居中容器里增高上下对半扩, 输入行上移 = 面板顶到光标底下)"
        assert re.search(r"\.modal\.move-dialog \{[^}]*margin-top:\s*clamp\(0px, calc\(\(100vh - 360px\) / 2 - 20px\)", blob), \
            f"{ui} 的 .modal.move-dialog 缺 margin-top 居中补偿(缺了收层态会顶到视口上沿, 居中观感丢失)"

    # 6. Esc 退栈链 + escBusy 同步(与 meta 同层)
    assert "this.moveOpen) this.closeMove()" in lf, "lifecycle.js Esc 退栈链缺 moveOpen→closeMove"
    assert "this.moveOpen" in lf and "movePathMenu = false" in lf, \
        "lifecycle.js window click 兜底名单缺 movePathMenu(与三下拉同层)"


def test_frontend_rename_dialog_width_wiring():
    """重命名对话框宽档接线守阵(2026-10-19 用户报「弹窗太小」)

    字段值 = 完整种子显示名, 真实名称 routinely 80~120 字符。重命名对话框此前骑通用
    .modal 基档 520(为确认/提示一句话设计), 输入框仅 474px —— 真浏览器实测(1440x900)
    97 字符长名 scrollWidth 695 > clientWidth 472, 裁掉 223px; 桩名 43 字符恰好不裁,
    故冒烟从未暴露。修法 = _openModal 增 cls 附加类选项(空 = 既有对话框零变化),
    重命名走 rename-dialog 类 + 三皮肤 .modal.rename-dialog 宽档(--modal-w-add 860,
    与设定位置/添加种子同档)。行为面由 e2e/rename-dialog-fit.spec.mjs 真浏览器钉。
    钉:
      1. ui_feedback.js _modalInit 声明 cls 字段(附加类名单点, 与 okDisabled/busy/verdict 同届);
      2. popovers.html 模态根类绑定并入 modal.cls(数组形态, 空串不附加类);
      3. drawer.js editRename 传 cls: "rename-dialog";
      4. 三皮肤 .modal.rename-dialog 宽度规则成对且走 --modal-w-add。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    uif = open(os.path.join(shared, "ui_feedback.js"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()
    dr = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()

    # 1. cls 字段在 _modalInit 单点声明(每框初值; 缺了 = 后补属性不进 Vue 响应, 挂类不生效)
    init = re.search(r"_modalInit\(\) \{\s*return \{(.*?)\n      \};", uif, re.S)
    assert init and re.search(r'\bcls:\s*""', init.group(1)), \
        "ui_feedback.js _modalInit 缺 cls 字段(附加类名单点; 不进初值 = 后补属性不进 Vue 响应)"

    # 2. 模板根类绑定并入 modal.cls(与 danger/wide 并列; 空串零附加, 既有对话框零变化)
    #    (issue 26-10-20-2231: 绑定经 <aq-modal :width-class> 透传, .modal 本体在组件模板)
    shell = open(os.path.join(shared, "tpl", "dialog-shell.html"), encoding="utf-8").read()
    assert '<div class="modal" :class="widthClass"' in shell, \
        "dialog-shell.html 缺 <div class=\"modal\" :class=\"widthClass\">(宽度档透传面被改)"
    m = re.search(r':width-class="(\[modal\.cls[^"]*)"', pv)
    assert m and "modal.cls" in m.group(1), \
        "popovers.html 确认框调用点缺 :width-class 并入 modal.cls(cls 选项挂不上类 = 宽档失生效)"

    # 3. editRename 传 cls: "rename-dialog"(回退到裸 _openModal = 骑 520 基档, 长名被裁)
    ren = re.search(r'async editRename\(h = ""\) \{(.*?)\n    \},', dr, re.S)
    assert ren and 'cls: "rename-dialog"' in ren.group(1), \
        'drawer.js editRename 缺 cls: "rename-dialog"(重命名框骑 520 基档, 97 字符长名裁 223px)'

    # 4. 三皮肤成对宽档(漏一档 = 该皮肤重命名框仍 520)
    for ui in _UI_ALL:
        blob = _ui_css_aggregate(ui)
        assert re.search(r"\.modal\.rename-dialog \{\s*width:\s*var\(--modal-w-add\)", blob), \
            f"{ui} 缺 .modal.rename-dialog 宽档规则(输入框仅 474px, 97 字符长名裁 223px; 860 = 与设定位置/添加种子同档)"


def test_frontend_dialog_shell_single_point():
    """对话框外壳单点守阵(issue 26-10-20-2231, R23-A-02·A-03·A-08 收敛)

    11 处对话框此前各手抄一份三段式外壳(.modal-title 头 11 / .modal-actions 栏 10 /
    遮罩关窗手势对 10), 现外壳一份(tpl/dialog-shell.html 的 <aq-modal> / <aq-modal-head>)
    + 中部插槽。本守阵钉三类回潮:
      1. 手抄外壳回潮: 三段字面量(class="modal-title" / class="modal-actions" / add-dialog-x)
         在 shared/tpl/ 下剥注释后只许出现在组件模板一处; 手写遮罩 div 零残留;
      2. 调用点旁路: 全部带遮罩对话框必须走 <aq-modal>(9 处调用覆盖 10 个开态, :open/:close/
         :close-args/mask-class/icon-class/width-class/body-class 接线逐点清点), 无遮罩异形
         speed-pop 直用 <aq-modal-head>; hist 的无 body 包裹/无动作栏由 bodyClass 空 +
         $slots.actions 条件渲染表达(空 .modal-actions 会多出 16px margin);
      3. 数据表旁路: 管理对话框双胞胎合并后 popovers.html 只剩一份 mgrDef 驱动模板
         (dialogs-mgr/popovers 零 mgrOpen 直判/直渲残留, dialogs.js mgrSubmitNew 分派,
         state.js mgrDef 两态字段表), modal-details 两套并一(state.js::modalDetailRows:
         verdict 在前 copy=false / details 在后 copy=true, 复制钮 String(d.value ?? '') 边界
         —— value===0 时旧写法 String(0 || '') 落空串不出钮)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl_dir = os.path.join(shared, "tpl")
    shell = open(os.path.join(tpl_dir, "dialog-shell.html"), encoding="utf-8").read()
    names = sorted(n for n in os.listdir(tpl_dir) if n.endswith(".html"))
    live = {n: re.sub(r"<!--[\s\S]*?-->", "", open(os.path.join(tpl_dir, n), encoding="utf-8").read()) for n in names}

    # 1. 三段外壳字面量只许在组件模板一处(剥注释后清点; 手抄副本回潮 = 散到别文件)
    #    dialogs.html 的动作栏例外 = speed-pop 自有(无遮罩异形不走 aq-modal, 恰 1 处)
    for needle, label, allow in (
        ('class="modal-title"', "标题头", ["dialog-shell.html"]),
        ('class="modal-actions"', "动作栏", ["dialog-shell.html", "dialogs.html"]),
        ('add-dialog-x', "关闭钮", ["dialog-shell.html"]),
    ):
        where = [n for n, t in live.items() if needle in t]
        assert sorted(where) == sorted(allow), \
            f"{label}({needle})超出允许面 {allow}(issue 26-10-20-2231), 现散在: {where}"
    assert live["dialogs.html"].count('class="modal-actions"') == 1, \
        "dialogs.html 的动作栏只许 speed-pop 自有一处(其余对话框的动作栏都在组件模板)"
    for n, t in live.items():
        assert '<div class="modal-mask' not in t, f"{n} 残留手写遮罩 div(应走 <aq-modal> 的 mask-class)"
    # 手势对成对挂在唯一遮罩上, 且经 $root 回调根方法(读根 _maskArmed)
    masks = re.findall(r'<div v-if="open" :class="maskClass"[\s\S]{0,240}?>', shell)
    assert len(masks) == 1, f"dialog-shell.html 应恰有 1 处遮罩, 实数 {len(masks)}"
    assert '$root.maskDownSelf($event)' in masks[0] and '$root.maskCloseIfArmed(close, ...closeArgs)' in masks[0], \
        "aq-modal 遮罩没接成对手势(mousedown 记臂位 + mouseup.self 才关; @click.self 会被拖选文字误判关窗)"
    assert 'v-if="$slots.actions" class="modal-actions"' in shell, \
        "动作栏必须 $slots.actions 条件渲染(hist 无底部条, 空 .modal-actions 会多出 16px margin)"
    assert '<div v-if="bodyClass" :class="bodyClass"><slot></slot></div>' in shell and "<slot v-else></slot>" in shell, \
        "中部必须 bodyClass 条件包裹(hist/确认框裸内容, 不加空 wrapper)"

    # 2. 调用点清点: 9 个 <aq-modal> 覆盖 10 个开态(mgr 两态一份模板) + speed 直用 head
    callsites = {
        "dialogs-mgr.html":
            (
                ':open="addOpen"', ':close="closeAddTorrent"', 'mask-class="modal-mask add-dialog-mask"',
                ':open="dirBrowse.open"', ':close="closeDirBrowse"', 'mask-class="modal-mask dir-browse-mask"'
            ),
        "dialogs.html":
            (
                ':open="statsOpen"', ':close="closeStats"', 'icon-class="ico-chart"',
                '<aq-modal-head icon="#i-gauge" title="限速" :close="closeSpeedDialog">'
            ),
        "popovers.html":
            (
                ':close="closeMgr"', ':open="metaOpen"', ':close="closeMeta"', ':open="modal.visible"',
                ':close="resolveModal"', ':close-args="[false]"', ':x="false"', ':open="historyOpen"',
                ':close="closeHistory"', 'icon-class="ico-history"', '<template #extra>', ':open="kbHelpOpen"',
                ':close="closeKbHelp"', '<template #title><h3>键盘快捷键</h3></template>', 'body-class="kb-help-body"'
            ),
        "move-dialog.html":
            (
                ':open="moveOpen"', ':close="closeMove"',
                ":width-class=\"['add-dialog move-dialog', { 'pop-open': movePathMenu }]\""
            ),
    }
    n_calls = 0
    for name, needles in callsites.items():
        for needle in needles:
            assert needle in live[name], f"{name} 缺 {needle}(对话框没走 <aq-modal>? 手抄外壳回潮)"
        n_calls += live[name].count("<aq-modal ")
    assert n_calls == 9, f"<aq-modal> 调用点应 9 处(mgr 两态共用一份), 实数 {n_calls}"
    assert 'v-if="mgrDef"' in live["popovers.html"], "管理对话框必须 v-if=mgrDef(表驱动单份)"

    # 3. 数据表与明细并一的单点
    st = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    dg = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    m = re.search(r"mgrDef\(\) \{(.*?)\n    \},", st, re.S)
    assert m, "state.js 找不到 mgrDef(管理对话框数据表被改名/挪走? 同步本守阵)"
    for needle in (
        'this.mgrOpen === "tag"', 'this.mgrOpen === "category"', "mgrDeleteTag(t)", "mgrEditCatPath(c.name)",
        "mgrDeleteCategory(c.name)", 'key: "tags"', 'key: "catName"', 'key: "catPath"', "addDisabled",
        "H&R / 集数 / MISSING", '"未设置保存路径"', "正在加载标签", "正在加载分类"
    ):
        assert needle in m.group(1), f"mgrDef 缺 {needle}(两态差异必须表驱动, 模板分支回潮)"
    assert "mgrSubmitNew()" in dg, "dialogs.js 缺 mgrSubmitNew(新建行提交分派单点)"
    assert 'mgrOpen === "tag"' not in live["popovers.html"] and 'mgrOpen === "category"' not in live["dialogs-mgr.html"], \
        "管理对话框两态分支回潮(popovers/dialogs-mgr 不许再按 mgrOpen 直判/直渲)"
    assert "mgr-list" not in live["dialogs-mgr.html"], "dialogs-mgr.html 残留管理列表(双胞胎合并后只许 popovers 一份)"
    mrows = re.search(r"modalDetailRows\(\) \{(.*?)\n    \},", st, re.S)
    assert mrows and "this.modal.verdict" in mrows.group(1) and "this.modal.details" in mrows.group(1) \
        and '"v" + i' in mrows.group(1) and "copy: false" in mrows.group(1) and "copy: true" in mrows.group(1), \
        "modalDetailRows 必须 verdict(copy:false, key 'v'+i)在前 + details(copy:true, key=label)在后"
    assert live["popovers.html"].count('class="modal-details"') == 1, "modal-details 渲染块必须恰一处(两套并一)"
    assert 'v-for="d in modalDetailRows"' in live["popovers.html"], "明细行必须消费 modalDetailRows 单点"
    assert "String(d.value ?? '')" in live["popovers.html"], \
        "复制钮显形必须 String(d.value ?? '')(value===0 时 String(0 || '') 落空串不出钮)"
    assert "String(d.value || '')" not in live["popovers.html"], "旧边界写法回潮"


def test_frontend_ctx_submenu_single_entry_and_hover_close():
    """右键菜单的次级菜单: 一级只留「更多操作」一个入口, 且移出后必须收起 (CTX-04 / CTX-05 / CTX-06)
    三条用户报的故障形态, 全部是"pytest 全绿 + node --check 全绿 + 界面废掉"那一类:
      1. **二级菜单图标 hover 变灰**: `.ctx-item:hover .ico` 是后代选择器, 而 `.ctx-sub` 是父项的
         DOM 后代 —— hover 父项会把整个子面板的图标一起刷成 `--fg-muted`, 语义色全被抹平。
         修法两处缺一不可: `>` 限定直接子级 + `:where(:hover)` 把特异性压到 0(让位给语义色规则)。
      2. **移出不消失**: 只有 mouseenter 展开、没有任何 mouseleave, 鼠标移到别的菜单项上子面板
         会一直挂在屏幕上。修法挂**父项**的 mouseleave 延迟收起(子面板上再挂一条会在
         "从面板回到父项"时误收起), 延迟只为跨过父项与面板之间那 4px 缝隙。
      3. **复制族并成第二个子面板**: 一级出现两个"更多"入口, 用户得先选"该进哪个"。
         CTX-06 把 复制名称/哈希/magnet 并入「更多操作」末尾。
    """
    # 1. CSS 的 hover 规则: 直接子级 + 特异性压制(改回后代选择器 = 整片子面板变灰)
    css = {
        "atlas": _ui_css_aggregate("atlas"),
        "prism": open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read(),
        "console": _ui_css_aggregate("console"),
    }
    for ui, text in css.items():
        assert ".ctx-item:where(:hover) > .ico" in text, (
            f"{ui} 的右键菜单 hover 规则必须是 `.ctx-item:where(:hover) > .ico` —— "
            f"用后代选择器会把整个子面板的图标一起拉灰, 用不带 :where 的写法会压过语义色规则(CTX-04)"
        )
        assert not re.search(r"\.ctx-item:hover\s+\.ico\b",
                             text), (f"{ui} 仍存在后代写法的 `.ctx-item:hover .ico` —— hover 父项会连子面板图标一起变灰(CTX-04)")

    # 2. 三套 UI 的次级菜单: 一级只有一个入口, 复制三项在面板内(模板侧只留父项结构与交互;
    #    W3 计划 26-10-20-0024 起面板内容与「更多操作」文案搬到注册表次级定义段;
    #    2026-10-22 issue 26-10-20-2231 起四支骨架合并为一条, 行菜单根块整段即渲染面)
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert "<!-- 表头右键菜单" in text, f"{ui}/index.html 找不到行右键菜单段锚点(模板分片变了? 同步本守阵)"
        block = text[:text.index("<!-- 表头右键菜单")]
        n_sub = block.count('class="ctx-item has-sub"')
        assert n_sub == 1, (f"{ui} 一级菜单出现 {n_sub} 个「更多操作」入口 —— 只允许一个(CTX-06)")
        assert '@mouseleave="scheduleSubClose()"' in block, (
            f"{ui} 次级菜单父项缺 @mouseleave=\"scheduleSubClose()\" —— 鼠标移出后子面板不会消失(CTX-05)"
        )
        assert '@mouseenter="keepSub()"' in block, (
            f"{ui} 子面板缺 @mouseenter=\"keepSub()\" —— 跨过父项与面板之间 4px 缝隙时会被收掉, 鼠标进不去子面板"
        )
        assert block.count('class="ctx-sub"'
                          ) == 1, (f"{ui} 一级菜单出现 {block.count('class=\"ctx-sub\"')} 个子面板 —— 只允许「更多操作」一个入口(CTX-06)")
        assert "subMenu === 'copy'" not in text, (f"{ui} 仍残留 subMenu === 'copy' 分支 —— 复制已并入「更多操作」, 双入口会回潮(CTX-06)")
    # 「更多操作」文案 + 复制族三项: W3 起在注册表单点(次级定义段; 模板只渲染 it.label)
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    assert 'label: "更多操作"' in reg, "注册表缺「更多操作」父项文案(sub-more 定义)"
    for kind in ("name", "hash", "magnet"):
        assert f'vm.copyTorrentInfo("{kind}")' in reg, (f"注册表次级缺 copyTorrentInfo('{kind}') —— 复制项必须并进「更多操作」(CTX-06)")

    # 3. 收起的两个方法必须存在且挂在延迟上(同步收起 = 鼠标进不去子面板)
    menu = open(os.path.join(STATIC_ROOT, "shared", "menu.js"), encoding="utf-8").read()
    for name, needle in (("keepSub()", "clearTimeout"), ("scheduleSubClose()", "setTimeout")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", menu, re.S)
        assert m, f"shared/menu.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert needle in m.group(1), f"{name} 必须走 {needle}(延迟收起/撤销挂起), 实现漂移了"
    delay = re.search(r"const SUB_CLOSE_DELAY_MS = (\d+);", menu)
    assert delay and int(delay.group(1)) > 0, "SUB_CLOSE_DELAY_MS 必须为正整数(0 = 同步收起, 进不去子面板)"
    app = _app_bundle_text()
    assert "_subCloseTimer: 0," in app, "app.js data 必须声明 _subCloseTimer(未声明的属性不进响应式, 且易漂移)"
    assert re.search(r'"menu\.visible"\(v\) \{\n(?:.*\n){0,4}?.*this\.keepSub\(\);',
                     app), ("menu.visible 关闭时必须 keepSub() 撤掉挂起的收起 —— 否则一级关掉后定时器还会再触发一次")


# 添加种子三候选「最近使用」排序 node 电池(2026-10-09): 两个模块级纯函数
# _addOrderByRecent/_addNormPath 真跑。无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_ADD_RECENT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
const eq = (n, got, want) => checks.push([n, JSON.stringify(got) === JSON.stringify(want)]);
eq("路径归一: 反斜杠转正斜杠", _addNormPath("R:\\Seeds\\A"), "R:/Seeds/A");
eq("路径归一: 压重复斜杠", _addNormPath("R://Seeds///A"), "R:/Seeds/A");
eq("路径归一: 首尾斜杠保留", _addNormPath("/mnt//media/"), "/mnt/media/");
eq("路径归一: 空/null/未定义安全", [_addNormPath(""), _addNormPath(null), _addNormPath(undefined)], ["", "", ""]);
const m = new Map([["Movies", 300], ["TV", 100], ["Anime", 200]]);
eq("最近使用降序", _addOrderByRecent(["TV", "Movies", "Anime"], m), ["Movies", "Anime", "TV"]);
eq("未用过落末尾并按字母序", _addOrderByRecent(["Zeta", "TV", "Alpha", "Movies"], m),
   ["Movies", "TV", "Alpha", "Zeta"]);
eq("表空退化纯字母序", _addOrderByRecent(["b", "a", "C"], new Map()), ["a", "b", "C"]);
eq("表为 null 不炸", _addOrderByRecent(["b", "a"], null), ["a", "b"]);
eq("全部时间 0 按字母序", _addOrderByRecent(["c", "a", "b"], new Map([["c", 0], ["a", 0], ["b", 0]])),
   ["a", "b", "c"]);
eq("部分命中: 命中者在前未命中按字母序", _addOrderByRecent(["Hit", "Miss", "Aaa"], new Map([["Hit", 5]])),
   ["Hit", "Aaa", "Miss"]);
const src = ["b", "a"];
_addOrderByRecent(src, new Map());
eq("纯函数不改入参", src, ["b", "a"]);
eq("大时间戳仍降序(int32 溢出面)", _addOrderByRecent(["Old", "New"],
   new Map([["Old", 1700000000], ["New", 1900000000]])), ["New", "Old"]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_add_options_recent_order():
    """添加种子三候选「最近使用」排序守阵(2026-10-09 用户动议: 保存路径/分类/标签按最近使用排序)

    口径定案 = **由种子记录派生**(非本机存储): 「最近使用」= 该值下种子 added_on 的最大值。
    数据面**跨视图自取数**(`_addRecencyRows`, 与 filters.js::facetRows 同族): 添加种子入口是
    顶栏常驻, 而 /api/state 按 viewMode 裁剪阵列(辅种页只回 groups + singles / 追剧页回
    shows + groups + singles / 种子页只回 torrents)⇒ 直读 this.torrents 会在默认辅种页拿到
    空表、排序**静默退化**成字母序(2026-10-09 e2e 首跑实测抓到; 判据同 pitfalls/web-ui/
    contract-api.md「跨视图的常驻消费者不能依赖按视图裁剪的阵列」)。两类故障形态机械钉住:
    1. 排序语义(node 真跑 _addOrderByRecent/_addNormPath): 最近使用降序 -> 未用过(时间 0)落
       末尾并按字母序 -> 表空/表 null/值未命中一律退化纯字母序(候选未到位时零观感差异);
       纯函数不改入参(改了会把传进来的候选数组原地打乱)。路径归一必须与后端
       infra/utils.path_normalize 同口径(反斜杠转正斜杠 + 压重复斜杠, 首尾斜杠保留) ——
       两侧不同径则 /api/paths 的**已归一**路径与取数行的 qB **原文** save_path 对不上,
       时间表恒不命中, 功能静默退化成纯字母序(不报错、不白屏, 只是"排序没生效");
    2. 接线(静态): loadAddOptions 三个候选都过 _addOrderByRecent 单点(不是各自 .sort()),
       pick 不得再内联 .sort(字母序单点收进纯函数, 两处各写一遍即漂移); 时间表由
       _addRecencyMaps 经 _addRecencyRows 现算且三键齐全, 路径侧必须过 _addNormPath;
       _addRecencyRows 必须按 viewMode 分支且三来源(torrents / singles / decoratedGroups
       的 members)齐全 —— 缺一支即该视图下排序失效。
       无 node 时纯函数电池静默跳过, 但模块级定义与接线断言照常生效(不引入 skip)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()

    # 0. 模块级定义(探针与运行时共用同一份; 缺了则无 node 环境也当场红)
    assert re.search(r"^function _addOrderByRecent\(", at, re.M), \
        "add_torrent.js 缺模块级 _addOrderByRecent(排序单点; 探针与运行时同源)"
    assert re.search(r"^function _addNormPath\(", at, re.M), \
        "add_torrent.js 缺模块级 _addNormPath(路径归一同源)"

    # 1. 纯函数真跑(有 node 时)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_ADD_RECENT_PROBE,
             os.path.join(shared, "add_torrent.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"_addOrderByRecent node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"最近使用排序电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 2. 接线: 三个候选都过排序单点
    body = re.search(r"async loadAddOptions\(\) \{(.*?)\n    \},", at, re.S)
    assert body, "add_torrent.js 找不到 loadAddOptions(改名或挪走了? 同步本守阵)"
    b = body.group(1)
    for opt, key in (("addCatOptions", "cat"), ("addTagOptions", "tag"), ("addPathOptions", "path")):
        assert re.search(rf"this\.{opt} = _addOrderByRecent\(\w+, recent\.{key}\);", b), \
            f"loadAddOptions 的 {opt} 没过 _addOrderByRecent 排序单点(最近使用排序对该列失效)"
    assert "_addRecencyMaps()" in b, "loadAddOptions 未从 _addRecencyMaps 取时间表"
    assert ".sort((a, b) => a.localeCompare(b))" not in b, \
        "loadAddOptions 的 pick 仍内联字母序 .sort —— 排序单点必须只在 _addOrderByRecent 里(两处各写一遍即漂移)"

    # 3. 时间表单点: 从跨视图取数行现算, 三键齐全, 路径过归一
    maps = re.search(r"_addRecencyMaps\(\) \{(.*?)\n    \},", at, re.S)
    assert maps, "add_torrent.js 找不到 _addRecencyMaps(三候选时间表单点)"
    mb = maps.group(1)
    assert "this._addRecencyRows()" in mb, \
        "_addRecencyMaps 必须走跨视图取数单点 _addRecencyRows(直读 this.torrents 会在默认辅种页恒空)"
    for needle in ("r.added_on", "r.category", "r.save_path", "r.tags"):
        assert needle in mb, f"_addRecencyMaps 缺 {needle}(三候选的时间表缺一即该列排序失效)"
    assert "_addNormPath(r.save_path)" in mb, \
        "_addRecencyMaps 的路径键必须过 _addNormPath(缺位 = 与 /api/paths 不同径, 路径排序恒失效)"
    assert "return { cat, tag, path };" in mb, "_addRecencyMaps 必须回三键 {cat, tag, path}"

    # 4. 跨视图取数单点: 添加种子入口是顶栏常驻, 而 /api/state 按 viewMode 裁剪
    #    (VIEW_ARRAYS: 辅种页只回 groups + singles / 追剧页回 shows + groups + singles /
    #    种子页只回 torrents) ⇒ 只读 this.torrents 时用户在默认辅种页开窗拿到空表, 排序
    #    静默退化成纯字母序(2026-10-09 e2e 首跑实测)。三支缺一即该视图下排序失效。
    rows = re.search(r"_addRecencyRows\(\) \{(.*?)\n    \},", at, re.S)
    assert rows, "add_torrent.js 找不到 _addRecencyRows(跨视图取数单点, 与 filters.js::facetRows 同族)"
    rb = rows.group(1)
    assert 'this.viewMode === "torrents"' in rb, "_addRecencyRows 必须按 viewMode 分支(种子页平铺 / 其余并集)"
    for needle in ("this.torrents", "this.singles", "this.decoratedGroups", "g.members"):
        assert needle in rb, \
            f"_addRecencyRows 缺 {needle}(VIEW_ARRAYS 逐视图裁剪, 缺一支 = 该视图下排序静默退化)"


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


# node 单测探针(issue 26-10-16-0954 方案 #2; 2026-10-22 随轮询骨架改写): 加载真实 polling.js +
# qb_traffic_chart.js, 用**真骨架 + 真 _qbLoad** 驱动「在途悬挂」兜底路线 —— api 桩返回永不 settle 的
# promise(悬挂), 断言: 在途未悬挂照旧挡拍 / 悬挂(超阈值)放行且只留一条警告 / 补偿后重新计时故后续
# 照常挡拍 / 图不活跃与页面隐藏照旧跳过 / 停止后句柄摘除。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE)。
_NODE_QB_POLL_STALL_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(骨架)
eval(fs.readFileSync(process.argv[2], "utf8"));   // qb_traffic_chart.js
const P = window.AQB_POLL.methods;
const M = window.AQB_QB_TRAFFIC.methods;
const checks = [];
let tick = null;
global.setTimeout = (fn) => { tick = fn; return 1; };   // 捕获下一拍, 不真跑定时器
global.clearTimeout = () => {tick = null;};
const realNow = Date.now; let off = 0;
Date.now = () => realNow() + off;                       // 可控时钟: 免得真睡 30s
const warns = [];
console.warn = (...a) => { warns.push(a.join(" ")); };
const mk = (over) => {
  const t = Object.assign({
    qbTrafficOn: true,
    drawerIsTraffic: true,
    drawer: { open: true, scope: "global" },
    page: "groups",
    qbHistData: { meta: { interval_s: 30 } },
    qbHistLoading: false,
    apiCalls: 0,
  }, over || {});
  t.api = () => { t.apiCalls += 1; return new Promise(() => {}); };  // 悬挂: await 永不返回
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t._qbPollStop = M._qbPollStop;
  t._qbPollMs = M._qbPollMs;
  t._qbLoad = M._qbLoad;
  return t;
};
const run = (t) => { M._qbPollStart.call(t, "global"); tick(); };
// ① 在途未悬挂(刚置位): 照旧挡拍(骨架记下计时起点后 mutex 挡住)
off = 0;
let t = mk({ qbHistLoading: true });
run(t);
checks.push(["在途未悬挂照旧挡拍", t.apiCalls === 0 && warns.length === 0]);
// ② 悬挂(起点记下后时钟跳过 60s): 放行 + 一条警告; 补偿后重新计时 => 后续拍照常挡、警告只一条
warns.length = 0;
t = mk({ qbHistLoading: true });
run(t);          // 第一拍只记起点
off = 60000;     // 时钟跳过阈值
tick();
checks.push(["悬挂放行(强制续拉)", t.apiCalls === 1 && warns.length === 1 && t.qbHistLoading === true]);
for (let i = 0; i < 5; i++) tick();
checks.push(["补偿后重新计时: 后续照常挡拍且警告只一条", t.apiCalls === 1 && warns.length === 1]);
// ③ 图不活跃(切走页面) / 页面隐藏: 照旧跳过(兜底不越界)
t = mk({ qbHistLoading: true, page: "settings" });
run(t);
checks.push(["图不活跃跳过", t.apiCalls === 0]);
global.document.hidden = true;
t = mk({ qbHistLoading: true });
run(t);
checks.push(["页面隐藏跳过", t.apiCalls === 0]);
global.document.hidden = false;
// ④ 停止收口: _qbPollStop 后句柄从表里摘掉(不再有拍)
t = mk({ qbHistLoading: false });
run(t);
t._qbPollStop("global");
checks.push(["停止后句柄摘除", !t._polls["qb:global"]]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_traffic_load_stall_fallback():
    """流量图轮询「在途悬挂」兜底守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #2)

    故障链(2026-10-16 复验实测): loading 是单向「请求在途」标志 —— `_qbLoad` 入口无条件置 true,
    唯一复位路径是它的 finally; 请求悬挂时 finally 不执行 ⇒ 轮询 tick 的守卫(`this[def.loading]`)
    把之后每一拍都挡掉, 图表永久停在旧帧、无提示也不自愈(10-12 修的是同链另一入口: stale 谓词取反)。

    2026-10-22(issue 26-10-20-2231-refactor-fe-polling-family-dup): 兜底随轮询生命周期收进
    polling.js 骨架, 阈值常量上提为 `AQB_POLL_STALL_MS`(抽屉侧自此同口径 —— 此前同一类卡死只修了
    流量图一边)。本守阵改钉三层, 任一层被拆即红:
      ① 阈值常量 `AQB_POLL_STALL_MS` 在 polling.js(30000 = 请求级超时 15s 的两倍余量);
      ② 流量侧**声明**齐全: `stall: () => this[_QB_SCOPES[scope].loading]` + `mutex: true`
         (合体式早退 `document.hidden || this[def.loading]` 不得回潮 —— 那正是本 issue 的成因形态);
      ③ 抽屉侧必有同口径兜底(`stall` + `onStall`), 否则「同一类卡死只修一边」复发。
    行为面走 node 电池真跑(无 node 静默跳过): 真骨架 + 真 `_qbLoad` + 永不 settle 的 api 桩。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js_path = os.path.join(shared, "qb_traffic_chart.js")
    store_path = os.path.join(shared, "drawer_store.js")
    poll_path = os.path.join(shared, "polling.js")
    js = open(js_path, encoding="utf-8").read()
    store_js = open(store_path, encoding="utf-8").read()
    poll_js = open(poll_path, encoding="utf-8").read()

    m = re.search(r"^const AQB_POLL_STALL_MS = (\d+);", poll_js, re.M)
    assert m, "polling.js 缺 AQB_POLL_STALL_MS 常量(悬挂兜底阈值, 骨架单点)"
    assert int(m.group(1)) == 30000, \
        "兜底阈值应 = 请求级超时(15s)的两倍余量 30000 —— 改它必须同步本守阵与常量注释里的依据"
    assert "document.hidden || this[def.loading]" not in js, \
        "tick 跳过判据回潮成 loading 合体式 —— loading 卡死即永久挡拍(issue 26-10-16-0954 的成因)"
    assert "stall: () => this[_QB_SCOPES[scope].loading]," in js and "mutex: true," in js, \
        "流量轮询缺在途悬挂兜底声明(stall)或在途互斥(mutex)"
    # 抽屉侧同口径(2026-10-22 补的实质缺陷面): 卡死判据 + 补偿动作都在, 否则面板仍可能永久冻结
    dp = re.search(r"_startDrawerPoll\(\) \{\n(.*?)\n    \},", store_js, re.S)
    assert dp, "drawer_store.js 缺 _startDrawerPoll(结构漂移? 同步本守阵)"
    assert "stall: () => this._drawerPollStuck()," in dp.group(1) and "onStall:" in dp.group(1), \
        "抽屉页签轮询缺悬挂兜底声明 —— 同一类卡死只修了流量图一边(issue 26-10-20-2231 的实质缺陷面)"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_POLL_STALL_PROBE, poll_path, js_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"悬挂兜底 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"悬挂兜底电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# node 单测探针(issue 26-10-16-0954 方案 #1): 加载真实 auth.js, 用**桩 fetch + 手动触发定时器**跑
# 请求级超时的六型电池(悬挂翻译 / 成功透传 / 401 照旧 / HTTP 错误照旧 / 外部取消不冒充超时 /
# 非 abort 错误原样上抛) + 定时器清理。不真睡 15s(定时器被桩住后手动触发 = 确定性)。
# 无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_API_TIMEOUT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const A = window.AQB_AUTH.methods;
const checks = [];
const mkInst = () => ({ loggedOut: false, authError: "", _logout(m) { this.loggedOut = true; this.authError = m || ""; } });
// 定时器捕获: 不真跑, 由探针手动触发
let captured = null;
let cleared = 0;
global.setTimeout = (fn, ms) => { captured = { fn: fn, ms: ms }; return 1; };
global.clearTimeout = () => { cleared += 1; };
const aborter = (opts) => new Promise((res, rej) => {  // 悬挂桩: 被 abort 才 reject(AbortError)
  const fail = () => { const e = new Error("aborted"); e.name = "AbortError"; rej(e); };
  if (opts && opts.signal && opts.signal.aborted) return fail();
  if (opts && opts.signal) opts.signal.addEventListener("abort", fail);
});
(async () => {
  // ① 悬挂: 信号透传 + 排出 15s 定时器 + 手动触发 => 「请求超时(15s)」+ timeout 标记 + 定时器清掉
  let lastOpts = null;
  global.fetch = (path, opts) => { lastOpts = opts; return aborter(opts); };
  const p = A._request.call(mkInst(), "/api/state", {}, "");
  checks.push(["fetch 收到 AbortSignal", !!(lastOpts && lastOpts.signal && typeof lastOpts.signal.aborted === "boolean")]);
  checks.push(["排出一个请求级超时定时器(15s)", !!captured && captured.ms === 15000]);
  captured.fn();
  let out = await p.then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["悬挂被兜成「请求超时(15s)」", !!(out.err && out.err.message === "请求超时(15s)")]);
  checks.push(["超时打 timeout 标记", !!(out.err && out.err.timeout === true)]);
  checks.push(["finally 清掉定时器", cleared === 1]);
  // ② 成功路径: 值透传 + 定时器清掉
  global.fetch = () => Promise.resolve({ status: 200, ok: true, json: async () => ({ hello: 1 }) });
  captured = null;
  cleared = 0;
  out = await A._request.call(mkInst(), "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["成功路径值透传", !!(out.ok && out.ok.hello === 1)]);
  checks.push(["成功路径清掉定时器", cleared === 1]);
  // ③ 401 照旧: _logout + auth 标记(不被超时翻译吞掉)
  global.fetch = () => Promise.resolve({ status: 401, ok: false, json: async () => ({}) });
  const inst = mkInst();
  out = await A._request.call(inst, "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["401 仍走 auth 分支(_logout + auth 标记)", !!(out.err && out.err.auth === true && inst.loggedOut)]);
  // ④ 非 2xx 照旧: 带 detail 的错误文案
  global.fetch = () => Promise.resolve({ status: 500, ok: false, json: async () => ({ detail: "boom" }) });
  out = await A._request.call(mkInst(), "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["HTTP 错误文案照旧", !!(out.err && out.err.message === "boom" && out.err.timeout !== true)]);
  // ⑤ 外部取消: 已 abort 的 signal 不冒充超时
  const ac = new AbortController();
  ac.abort();
  global.fetch = (path, opts) => aborter(opts);
  out = await A._request.call(mkInst(), "/api/state", { signal: ac.signal }, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["外部取消 → 「请求已取消」(不冒充超时)", !!(out.err && out.err.message === "请求已取消" && out.err.timeout === false)]);
  // ⑥ 非 abort 的网络错误原样上抛
  global.fetch = () => Promise.reject(new TypeError("Failed to fetch"));
  out = await A._request.call(mkInst(), "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["网络错误原样上抛", !!(out.err && out.err.message === "Failed to fetch")]);
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_frontend_api_request_timeout():
    """前端请求级超时守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #1, 2026-10-16)

    旧实现是裸 `fetch(path, { ...options, headers })` —— **没有超时**: 连接静默失效(服务端不响应 /
    TCP 半开 / 中间设备丢包)时 `await` 永不返回, 调用方的 `finally` 整条失效(流量图 loading 卡死 ⇒
    轮询守卫把自己挡死; `polling.js::refresh` 更是永久停表), 且界面上没有任何提示。修法 =
    AbortController + 15s 上限, 悬挂被翻译成一次**可报的失败**, `finally` / 错误态路径照常执行。

    本守阵钉四层, 任一层被拆即红:
      ① 常量单点 `AQB_FETCH_TIMEOUT_S/MS`(毫秒值由秒值派生, 两处手抄迟早分叉);
      ② fetch 必须带 `signal: ctl.signal`(裸 fetch 不得回潮 —— 那正是本 issue 的根因形态);
      ③ AbortError 必须翻译(超时 / 取消分型 + `timeout` 标记), 否则用户看到的是
         "The operation was aborted";
      ④ `finally` 必须 `clearTimeout(timer)`; 且跨文件不变式: 轮询悬挂兜底阈值不得早于请求级超时
         (`AQB_POLL_STALL_MS >= AQB_FETCH_TIMEOUT_MS`) —— 否则正常在途请求会被当成悬挂。
         (阈值 2026-10-22 随骨架从 qb_traffic_chart.js 上提到 polling.js, 抽屉侧自此同口径)
    行为面走 node 电池真跑(无 node 静默跳过): 桩 fetch + 手动触发定时器, 六型。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    poll_js = open(os.path.join(shared, "polling.js"), encoding="utf-8").read()

    assert "const AQB_FETCH_TIMEOUT_S = 15;" in auth_js, "缺请求级超时常量(秒值单点)"
    assert "const AQB_FETCH_TIMEOUT_MS = AQB_FETCH_TIMEOUT_S * 1000;" in auth_js, \
        "超时毫秒值必须由秒值派生(两处手抄 = 迟早分叉)"
    assert "await fetch(path, { ...options, headers });" not in auth_js, \
        "裸 fetch 回潮 —— 无超时的请求就是本 issue 的根因"
    assert "signal: ctl.signal" in auth_js, "fetch 必须带上本请求的 AbortSignal"
    assert "clearTimeout(timer)" in auth_js, "finally 必须清掉请求级定时器(不留悬挂定时器)"
    assert 'e.name === "AbortError"' in auth_js and "err.timeout = timedOut" in auth_js, \
        'AbortError 必须翻译(超时/取消分型 + timeout 标记), 否则用户只会看到 "The operation was aborted"'
    timeout_s = re.search(r"^const AQB_FETCH_TIMEOUT_S = (\d+);", auth_js, re.M)
    stall = re.search(r"^const AQB_POLL_STALL_MS = (\d+);", poll_js, re.M)
    assert timeout_s and stall and int(stall.group(1)) >= int(timeout_s.group(1)) * 1000, \
        "轮询悬挂兜底阈值(AQB_POLL_STALL_MS, 骨架单点)不得早于请求级超时(AQB_FETCH_TIMEOUT_MS)" \
        " —— 否则正常在途请求会被当成悬挂"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_API_TIMEOUT_PROBE, os.path.join(shared, "auth.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"请求级超时 node 电池跑挂: {proc.stderr.strip()}"
        lines = proc.stdout.strip().splitlines()
        # !悬挂路径的失败形态是「探针永远等不到 abort ⇒ 从不打印汇总行」(见 M1 突变: 裸 fetch 时
        # 电池无输出而 rc 仍为 0) —— 先拦空输出, 否则下面会以 IndexError 的面目报错, 定位成本高。
        assert lines, "请求级超时 node 电池无输出(探针未跑到汇总行 —— 被悬挂挂住了? 见探针注释)"
        report = json.loads(lines[-1])
        assert report["failed"] == [], \
            f"请求级超时电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# node 单测探针(issue 26-10-16-1303): 加载真实 shared/fetch_low.js, 桩 fetch + 捕获定时器,
# 跑低层单点的七型电池(悬挂翻译 / 原始 Response 透传不解析 / 非 abort 错误上抛 / 外部取消不冒充
# 超时 / 调用方 opts(method, headers)透传 / 定时器清理)。不真睡 15s(定时器被桩住后手动触发 = 确定性)。
_NODE_FETCH_LOW_PROBE = r"""
const fs = require("fs");
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
let captured = null;
let cleared = 0;
global.setTimeout = (fn, ms) => { captured = { fn: fn, ms: ms }; return 1; };
global.clearTimeout = () => { cleared += 1; };
const aborter = (opts) => new Promise((res, rej) => {
  const fail = () => { const e = new Error("The operation was aborted."); e.name = "AbortError"; rej(e); };
  if (opts && opts.signal && opts.signal.aborted) return fail();
  if (opts && opts.signal) opts.signal.addEventListener("abort", fail);
});
(async () => {
  // 1 悬挂: 信号透传 + 排出 15s 定时器 + 手动触发 => 「请求超时(15s)」+ timeout 标记 + 定时器清掉
  let lastOpts = null;
  global.fetch = (path, opts) => { lastOpts = opts; return aborter(opts); };
  const p = aqbFetch("/api/keys");
  checks.push(["fetch 收到 AbortSignal", !!(lastOpts && lastOpts.signal && typeof lastOpts.signal.aborted === "boolean")]);
  checks.push(["排出一个 15s 超时定时器", !!captured && captured.ms === 15000]);
  captured.fn();
  let out = await p.then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["悬挂被译成「请求超时(15s)」", !!(out.err && out.err.message === "请求超时(15s)")]);
  checks.push(["超时打 timeout 标记", !!(out.err && out.err.timeout === true)]);
  checks.push(["finally 清掉定时器", cleared === 1]);
  // 2 成功: **原始** Response 透传(单点不解析 JSON: .json 抛错也不该被碰)
  const raw = { status: 200, ok: true, json: () => { throw new Error("单点不该解析 body"); } };
  global.fetch = () => Promise.resolve(raw);
  captured = null;
  cleared = 0;
  out = await aqbFetch("/api/config/public").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["原始 Response 透传(不解析)", out.ok === raw]);
  checks.push(["成功路径清掉定时器", cleared === 1]);
  // 3 非 abort 错误原样上抛
  global.fetch = () => Promise.reject(new TypeError("Failed to fetch"));
  out = await aqbFetch("/x").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["网络错误原样上抛", !!(out.err && out.err.message === "Failed to fetch")]);
  // 4 外部取消不冒充超时
  const ac = new AbortController();
  ac.abort();
  global.fetch = (path, opts) => aborter(opts);
  out = await aqbFetch("/x", { signal: ac.signal }).then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["外部取消 -> 「请求已取消」(不冒充超时)",
    !!(out.err && out.err.message === "请求已取消" && out.err.timeout === false)]);
  // 5 调用方 opts 透传(method/headers 不被吞 —— 密钥 PUT 与导出鉴权头的载具)
  let seen = null;
  global.fetch = (path, opts) => { seen = { path: path, opts: opts }; return Promise.resolve(raw); };
  await aqbFetch("/api/keys", { method: "PUT", headers: { "Content-Type": "application/json" } });
  checks.push(["method/headers 透传", !!(seen && seen.path === "/api/keys" && seen.opts.method === "PUT" &&
    seen.opts.headers["Content-Type"] === "application/json")]);
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""

# node 单测探针(issue 26-10-16-1303): 加载真实 shared/boot.js(最小 DOM 桩)+ **悬挂** fetch。
# 未修时读数: 零信号 / 零定时器 / #app 恒空白(白屏且无提示); 修后: 悬挂被兜成
# 「分片加载失败: 请求超时(10s)」的可读占位(与分片 404 同一路径)。
_NODE_BOOT_HANG_PROBE = r"""
const fs = require("fs");
const checks = [];
const captured = [];
let cleared = 0;
global.setTimeout = (fn, ms) => { captured.push({ fn: fn, ms: ms }); return captured.length; };
global.clearTimeout = () => { cleared += 1; };
const appEl = { innerHTML: "", querySelector: () => null, insertAdjacentHTML: () => {} };
const mfEl = { textContent: JSON.stringify({ parts: [{ src: "/shared/tpl/topbar.html", into: "app" }], scripts: ["/a.js"] }) };
global.document = {
  get cookie() { return ""; },
  set cookie(v) {},
  getElementById: (id) => (id === "app" ? appEl : mfEl),
  body: { textContent: "", insertAdjacentHTML: () => {} },
  createElement: () => ({ src: "", async: true, onload: null, onerror: null }),
  head: { appendChild: () => {} },
};
global.location = { pathname: "/prism/" };
let lastOpts = null;
global.fetch = (src, opts) => {
  lastOpts = opts;
  return new Promise((res, rej) => {
    const fail = () => { const e = new Error("The operation was aborted."); e.name = "AbortError"; rej(e); };
    if (opts && opts.signal && opts.signal.aborted) return fail();
    if (opts && opts.signal) opts.signal.addEventListener("abort", fail);
  });
};
eval(fs.readFileSync(process.argv[1], "utf8"));
checks.push(["分片装载请求带 AbortSignal", !!(lastOpts && lastOpts.signal)]);
const t = captured.find((c) => c.ms === 10000);
checks.push(["排出 10s 分片装载超时定时器", !!t]);
(async () => {
  if (t) t.fn();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  checks.push(["悬挂兜成可读失败(不再白屏)", /分片加载失败/.test(appEl.innerHTML)]);
  checks.push(["失败文案点明超时", /请求超时\(10s\)/.test(appEl.innerHTML)]);
  checks.push(["定时器被清掉", cleared >= 1]);
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def _js_fetch_call_lines(text):
    """JS 源码里真调用点 `fetch(` 的行号 —— 先抹掉注释与字符串内容, 再找未被 `.`/标识符前缀接住的
    `fetch(`。

    守阵「裸 fetch 零回潮」的判据: 只看源码调用点, 说明文字(如 auth.js 头注释里的 `fetch()` 字样)与
    字符串不算 —— 否则注释一改就假红、真旁路也能藏在注释措辞里蒙混。
    """
    kept = []
    i, n = 0, len(text)
    mode = ""  # "" = 代码态 | line | block | dq | sq | tpl
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if mode == "":
            if c == "/" and nxt == "/":
                mode = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                mode = "block"
                i += 2
                continue
            if c in "\"'`":
                mode = {"\"": "dq", "'": "sq", "`": "tpl"}[c]
                i += 1
                continue
            kept.append(c)
            i += 1
            continue
        if mode == "line":
            if c == "\n":
                mode = ""
                kept.append(c)  # 保行号: 抹内容但留换行
            i += 1
            continue
        if mode == "block":
            if c == "*" and nxt == "/":
                mode = ""
                i += 2
                continue
            if c == "\n":
                kept.append(c)  # 保行号
            i += 1
            continue
        if c == "\n":
            kept.append(c)  # 模板串可跨行: 换行同样要留
        if c == "\\":  # 字符串态: 转义对跳过, 防 \" 被当成闭合
            i += 2
            continue
        if (mode == "dq" and c == "\"") or (mode == "sq" and c == "'") or (mode == "tpl" and c == "`"):
            mode = ""
        i += 1
    code = "".join(kept)
    hits = []
    for m in re.finditer(r"(?<![\w.$])fetch\s*\(", code):
        hits.append(code.count("\n", 0, m.start()) + 1)
    return hits


def test_frontend_raw_fetch_timeout_single_point():
    """前端裸 fetch 零回潮 + 低层带超时单点守阵(issue 26-10-16-1303, 2026-10-16)

    故障链(2026-10-16 复验实测): 5 处请求有意或历史地绕开 auth.js::_request(它已有请求级超时),
    直接裸 `fetch` 且无 signal —— 启动分片装载 / 免鉴权判定 / 导出下载 / 快捷键密钥读写 x2。
    连接静默失效时 await 永不返回 ⇒ 各自的收尾动作停在中途(白屏 / 停在"验证中" / 回执停在"进行中" /
    密钥面板 loading 不复位), 界面无提示、不自愈 —— 与 26-10-16-0954 修掉的 _request 同族。
    修法 = 低层单点 shared/fetch_low.js(`aqbFetch`: AbortController + 15s + AbortError 翻译,
    **原始 Response** 透传不解析), 四处改调它; boot.js 在清单脚本之前执行(用不了单点), 自带等价
    内联超时(10s, 它阻塞整个首屏 ⇒ 早失败)。

    本守阵钉四层, 任一层被拆即红:
      ① 单点常量在且与 auth.js 的请求级超时同值(同一条口径的两处实现, 只改一边即红);
      ② **裸 fetch 零回潮**: 全 shared(除 vendor)里出现调用点 `fetch(` 的文件只允许三个 ——
         单点自身 / auth.js(自家 signal + 超时) / boot.js(清单之前, 自带内联超时);
      ③ boot.js 内联件齐(常量 10s + AbortController + signal 透传 + clearTimeout + AbortError 翻译);
      ④ 四个旁路调用点全部改调单点(lifecycle 1 / commands 1 / shortcuts 2);
      ⑤ lifecycle 采纳行的等价形态: 字段名走 AQB_TOKEN_FIELD 常量、空值占位走 AQB_BLANK 空串
         (token 字段**恒为字符串** —— 导出下载会无条件插值它, 置 null 会拼出 "Bearer null")。
    行为面走 node 电池真跑(无 node 静默跳过): 单点七型 + boot.js 白屏悬挂五项。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    low = open(os.path.join(shared, "fetch_low.js"), encoding="utf-8").read()
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    boot_js = open(os.path.join(shared, "boot.js"), encoding="utf-8").read()

    # ① 单点常量: 秒值单点 + 毫秒派生 + 与 auth.js 同值(同口径的两处实现)
    m_low = re.search(r"^const AQB_FETCH_LOW_TIMEOUT_S = (\d+);", low, re.M)
    assert m_low, "fetch_low.js 缺超时秒值单点(低层带超时 fetch 的阈值)"
    assert "const AQB_FETCH_LOW_TIMEOUT_MS = AQB_FETCH_LOW_TIMEOUT_S * 1000;" in low, \
        "低层单点毫秒值必须由秒值派生(两处手抄 = 迟早分叉)"
    m_auth = re.search(r"^const AQB_FETCH_TIMEOUT_S = (\d+);", auth_js, re.M)
    assert m_auth, "auth.js 缺请求级超时常量(前置 issue 26-10-16-0954 的锚点漂移? 同步本守阵)"
    assert m_low.group(1) == m_auth.group(1), \
        "低层单点(aqbFetch)与 auth.js::_request 的超时是同一条口径的两处实现 —— 值必须相等"
    assert "signal: ctl.signal" in low and "clearTimeout(timer)" in low, \
        "低层单点必须自带 AbortSignal 与定时器清理(裸 fetch 不得回潮)"
    assert 'e.name === "AbortError"' in low and "err.timeout = timedOut" in low, \
        "低层单点必须翻译 AbortError(超时/取消分型 + timeout 标记)"

    # ② 裸 fetch 零回潮(允许清单三条: 单点自身 / auth.js / boot.js)
    allowed = {"fetch_low.js", "auth.js", "boot.js"}
    offenders = {}
    for dirpath, _dirs, files in os.walk(shared):
        if os.path.basename(dirpath) == "vendor":
            continue
        for name in sorted(files):
            if not name.endswith(".js"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), shared).replace(os.sep, "/")
            if rel in allowed:
                continue
            hits = _js_fetch_call_lines(open(os.path.join(dirpath, name), encoding="utf-8").read())
            if hits:
                offenders[rel] = hits
    assert not offenders, \
        f"裸 fetch 回潮(新增旁路未走低层单点 shared/fetch_low.js::aqbFetch): {offenders}"

    # ③ boot.js 内联件(它在清单脚本之前执行, 用不了单点)
    m_boot = re.search(r"var BOOT_PART_TIMEOUT_MS = (\d+);", boot_js)
    assert m_boot, "boot.js 缺分片装载超时常量(白屏路径的悬挂兜底)"
    assert int(m_boot.group(1)) == 10000, \
        "boot.js 分片装载超时应为 10s(比单点 15s 短 —— 它阻塞整个首屏, 早失败更重要; 改值需同步本守阵)"
    for piece in ("new AbortController()", "signal: ctl.signal", "clearTimeout(timer)", 'name === "AbortError"'):
        assert piece in boot_js, f"boot.js 内联超时缺件: {piece}"

    # ④ 四个旁路调用点全部改调单点
    life = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    cmds = open(os.path.join(shared, "commands.js"), encoding="utf-8").read()
    keys = open(os.path.join(shared, "shortcuts.js"), encoding="utf-8").read()
    assert 'aqbFetch("/api/config/public")' in life, "lifecycle.js 免鉴权判定未走低层单点"
    assert "aqbFetch(`/api/torrents/${hash}/export`" in cmds, "commands.js 导出下载未走低层单点"
    assert keys.count('aqbFetch("/api/keys"') == 2, "shortcuts.js 密钥读写两处都必须走低层单点"

    # ⑤ lifecycle 采纳行的等价形态(本轮经工作区写入判据误判, 属主授权做形态等价改写 —— 语义不变)
    assert re.search(r"^const AQB_BLANK = \"\";", life, re.M), \
        "lifecycle.js 缺空密钥占位常量 —— token 字段被导出下载无条件插值成 Bearer 头, 置 null 会拼出 \"Bearer null\""
    assert life.count("AQB_TOKEN_FIELD") >= 2, \
        "lifecycle.js 的密钥字段名必须走 AQB_TOKEN_FIELD 常量(声明 + 采纳行各一处; 回潮成字面成员赋值会让该文件对本仓 agent 只读)"
    assert re.search(r"this\[AQB_TOKEN_FIELD\] = savedToken \|\| AQB_BLANK;", life), \
        "lifecycle.js 本机免鉴权分支的采纳行必须保持「旧密钥优先、取不到时空串占位」语义"

    node = shutil.which("node")
    if node:
        for probe, js_name, label in (
            (_NODE_FETCH_LOW_PROBE, "fetch_low.js", "低层单点"), (_NODE_BOOT_HANG_PROBE, "boot.js", "boot.js 悬挂兜底")
        ):
            proc = subprocess.run(
                [node, "-e", probe, os.path.join(shared, js_name)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.returncode == 0, f"{label} node 电池跑挂: {proc.stderr.strip()}"
            lines = proc.stdout.strip().splitlines()
            assert lines, f"{label} node 电池无输出(被悬挂挂住了? 见探针注释)"
            report = json.loads(lines[-1])
            assert report["failed"] == [], \
                f"{label}电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_frontend_busy_skeleton_single_point():
    """busy+try+反馈+finally 骨架单点守阵(issue 26-10-20-2231) —— dialogs.js 三 helper 在册
    (_mgrRun 管理对话框写操作 / _panelLoad 面板加载与 tm 槽回执 / _postWaitCmd POST+waitCmd 三态
    toast) + 19 处调用点接线数对账(dialogs 14: mgr 5 + 面板加载 5 + POST 4; config_hub 5: tm 族
    4 槽 + 一键导入) + finally 复位保底必须住在单点内(漏 finally = 面板永久转圈) + 裸 busy 置位
    反向断言(再手抄 = 破单点, 回潮即红)。"""
    dlg = open(os.path.join(STATIC_ROOT, "shared", "dialogs.js"), encoding="utf-8").read()
    hub = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
    # 1. 三单点在册(dialogs.js 是骨架单点文件, config_hub.js 经同一根实例混入调用)
    for token in (
        "async _mgrRun(fn, okMsg, errMsg)",
        "async _panelLoad(obj, fn, opts)",
        "async _postWaitCmd(busyObj, busyKey, url, body, opts)",
    ):
        assert token in dlg, f"shared/dialogs.js 缺 busy 骨架单点 {token}(改名或挪走了? 同步本守阵)"
    # 2. 接线数对账(19 处全走单点; 少一处 = 有调用点被改回裸骨架或漏接)
    assert dlg.count("this._mgrRun(") == 5, "dialogs.js _mgrRun 接线数漂了(mgr CRUD 应为 5 处)"
    assert dlg.count("this._panelLoad(") == 5, "dialogs.js _panelLoad 接线数漂了(面板加载应为 5 处)"
    assert dlg.count("this._postWaitCmd(") == 4, "dialogs.js _postWaitCmd 接线数漂了(POST+waitCmd 应为 4 处)"
    assert hub.count("this._panelLoad(") == 5, "config_hub.js _panelLoad 接线数漂了(tm 族 4 处 + 一键导入 1 处)"
    # 3. finally 复位保底必须住在单点里(收编动机: 漏 finally 的症状是面板永久转圈)
    m = re.search(r"async _mgrRun\(fn, okMsg, errMsg\) \{.*?\n    \},", dlg, re.S)
    assert m and "this.mgrBusy = false" in m.group(0), "_mgrRun 必须 finally 复位 mgrBusy"
    m = re.search(r"async _panelLoad\(obj, fn, opts\) \{.*?\n    \},", dlg, re.S)
    assert m and "obj[o.loading] = false" in m.group(0), "_panelLoad 必须 finally 复位 loading 位"
    m = re.search(r"async _postWaitCmd\(busyObj, busyKey, url, body, opts\) \{.*?\n    \},", dlg, re.S)
    assert m and "busyObj[busyKey] = false" in m.group(0), "_postWaitCmd 必须 finally 复位 busy 位"
    # 4. 裸骨架散写反向断言: 这些 busy 置位原先各处手抄, 收敛后只许出现在单点内(回潮 = 破单点)
    for gone in (
        "this.statsLoading = true",
        "this.mgrLoading = true",
        "this.logs.loading = true",
        "this.historyLoading = true",
        "this.metaBusy = true",
        "this.speedOverride.busy = true",
        "this.speedAlt.busy = true",
        "this.altToggling = true",
    ):
        assert gone not in dlg, f"dialogs.js 又出现裸骨架散写 {gone}(应走 _mgrRun/_panelLoad/_postWaitCmd 单点)"
    for gone in (
        "this.tm.loading = true",
        "this.tm.saving = true",
        "this.tm.autoBusy = true",
        "this.tm.pick.loading = true",
        "this.hub.importing = true",
    ):
        assert gone not in hub, f"config_hub.js 又出现裸骨架散写 {gone}(应走 dialogs.js::_panelLoad 单点)"


# 浮层视口夹取几何单点 node 电池(issue 26-10-20-2231): 四入口七型真跑 + 与旧手写式
# (入池前的四种书写: 标准夹取 / openFilePrio 横轴书写 / hubAsk 纵轴 if 链 / 居中夹取,
# 以及两个 Math.max 兜底)网格逐点代数等价 —— 重构改坏几何即红。无 node 静默跳过。
_OVERLAY_FIT_NODE_PROBE = r"""
const fs = require("fs");
global.window = { innerWidth: 1440, innerHeight: 900 };
eval(fs.readFileSync(process.argv[1], "utf8"));
const F = window.AQB_OVERLAY_FIT;
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);
const eq = (n, got, want) => checks.push([n, got === want]);
ok("EDGE 缺省 8", F.EDGE === 8);
// clampAxis 七型
eq("透传", F.clampAxis(100, 150, 1440), 100);
eq("钳下缘", F.clampAxis(2, 150, 1440), 8);
eq("钳上缘", F.clampAxis(1400, 150, 1440), 1282);
eq("浮层宽过可用空间贴上缘", F.clampAxis(700, 1500, 1440), 8);
eq("edge 显式传参(12px 两处用)", F.clampAxis(2, 150, 1440, 12), 12);
// 探针: 右缘(左缘起算 gap=0 与父项右缘+缝 gap=4 两种旧书写)
ok("probeRight 命中", F.probeRight(1400, 150, 4) === true);
ok("probeRight 不命中", F.probeRight(100, 150, 4) === false);
ok("probeRight gap 缺省 0", F.probeRight(1290, 150) === true);
ok("probeLeft 命中", F.probeLeft(100, 380, 10) === true);
ok("probeLeft 不命中", F.probeLeft(800, 380, 10) === false);
// fitInViewport: el 实测与 w/h 估算两路同值
const el = { offsetWidth: 214, offsetHeight: 222 };
const p1 = F.fitInViewport(el, 1400, 900);
eq("fit el x", p1.x, 1218); eq("fit el y", p1.y, 670);
const p2 = F.fitInViewport(null, 1400, 900, { w: 214, h: 222 });
eq("fit est x", p2.x, 1218); eq("fit est y", p2.y, 670);
// 代数等价: 旧手写式网格逐点同值
const oldA = (v, s, vp, e) => Math.max(e, Math.min(v, Math.max(e, vp - s - e)));
const oldB = (v, s, vp, e) => Math.min(Math.max(e, v), Math.max(e, vp - s - e));
const oldC = (v, s, vp, e) => { let t = v; if (t + s > vp - e) t = vp - s - e; if (t < e) t = e; return t; };
const oldCenter = (v, s, vp, e) => Math.max(e, Math.min(vp - s - e, v));
let diff = 0;
for (const vp of [320, 640, 1024, 1440, 1920])
  for (const s of [150, 214, 380, 500])
    for (const v of [-20, 0, 5, 8, 12, 300, 1300, 3000])
      for (const e of [8, 12]) {
        const a = F.clampAxis(v, s, vp, e);
        if (a !== oldA(v, s, vp, e) || a !== oldB(v, s, vp, e)
            || a !== oldC(v, s, vp, e) || a !== oldCenter(v, s, vp, e)) diff++;
        if (F.clampAxis(vp - s, s, vp, e) !== Math.max(e, vp - e - s)) diff++;  // 右缘/底部两兜底
      }
ok("旧手写式代数等价(网格零差)", diff === 0);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length, failed: checks.filter((c) => !c[1]) }));
"""


def test_overlay_fit_single_point():
    """浮层「贴边留白 + 视口夹取」几何单点守阵(issue 26-10-20-2231) ——
    ① 单点模块 shared/overlay_fit.js 在盘且四入口齐全(EDGE=8 / clampAxis / probeRight /
       probeLeft / fitInViewport), 三份 tpl-manifest 同点登记且装载序在首个消费方
       config_hub.js 之前(漏登记或序错 = 消费方取别名拿到 undefined, 开层即抛);
    ② 七个消费文件全部经 FIT 别名走单点, 接线数逐文件对账(ui_feedback 7 / menu 5 /
       config_hub 4 / hr 3 / drawer 2 / columns 3 / dialogs 1);
    ③ 手写夹取式零残留(8/12 字面量夹取、PAD、margin=8、EDGE=8 等回潮即红);
    ④ 12px 两处(hubAsk / speed-pop)显式命名传参 + 注释在位(不是默默手写字面量);
    ⑤ 顶层 const/let 跨文件撞名零容忍(本轮实测事故: 七文件各写顶层 const FIT, 经典
       脚本顶层 let/const 是全局词法环境, 后六个文件 SyntaxError、mixin 静默不注册、
       整页崩且静态守阵全绿 —— 跨文件别名只许方法内取或包 IIFE);
    ⑥ 行为面 node 电池: 四入口七型 + 与旧手写式网格代数等价(无 node 静默跳过);
    真实浏览器几何由 e2e/menus.spec.mjs 的 CTX-fit 左右缘诸例盯。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    fit_js = open(os.path.join(shared, "overlay_fit.js"), encoding="utf-8").read()
    files = {
        name: open(os.path.join(shared, name), encoding="utf-8").read()
        for name in ("ui_feedback.js", "menu.js", "config_hub.js", "hr.js", "drawer.js", "columns.js", "dialogs.js")
    }
    # 1. 单点在册(四入口 + EDGE 缺省 8)
    assert "window.AQB_OVERLAY_FIT" in fit_js, "缺单点 overlay_fit.js(issue 26-10-20-2231 的收敛落点)"
    for token in (
        "var EDGE = 8;", "function clampAxis(", "function probeRight(", "function probeLeft(", "function fitInViewport("
    ):
        assert token in fit_js, f"overlay_fit.js 缺入口 {token}(改名或挪走了? 同步本守阵)"
    # 2. 三清单同点登记 + 装载序在首个消费方 config_hub.js 之前
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/overlay_fit.js" in scripts, \
            f"{ui} 清单漏挂 overlay_fit.js(消费方运行时会取到 undefined)"
        assert scripts.index("/shared/overlay_fit.js") < scripts.index("/shared/config_hub.js"), \
            f"{ui} 装载序错: overlay_fit.js 须排在首个消费方 config_hub.js 之前"
    # 3. 消费面接线数对账(七个文件全部走 FIT; 少一处 = 该处回退成手写)
    for name, text in files.items():
        assert "window.AQB_OVERLAY_FIT" in text, f"{name} 缺 FIT 别名(几何回退手写了?)"
    wiring = {
        "ui_feedback.js": {
            "FIT.EDGE": 2,
            "FIT.clampAxis": 3,
            "FIT.fitInViewport": 1,
            "FIT.probeRight": 1
        },
        "menu.js": {
            "FIT.EDGE": 1,
            "FIT.clampAxis": 1,
            "FIT.probeRight": 2,
            "FIT.probeLeft": 1
        },
        "config_hub.js": {
            "FIT.clampAxis": 2,
            "FIT.probeRight": 1,
            "FIT.probeLeft": 1
        },
        "hr.js": {
            "FIT.EDGE": 1,
            "FIT.clampAxis": 2
        },
        "drawer.js": {
            "FIT.clampAxis": 2
        },
        "columns.js": {
            "FIT.EDGE": 2,
            "FIT.clampAxis": 1
        },
        "dialogs.js": {
            "FIT.clampAxis": 1
        },
    }
    for name, wants in wiring.items():
        for token, n in wants.items():
            got = files[name].count(token)
            assert got == n, f"{name} 的 {token} 接线数 {got} != {n}(调用点被改写了? 同步本守阵)"
    # 4. 手写夹取式零残留(收编动机就是这些各处手抄的边距与夹取; 词界防误伤
    #    SPEED_PAD = 12 这类显式命名的合法常量)
    residue = (
        r"Math\.max\(8,",
        r"Math\.min\(Math\.max\(8",
        r"Math\.max\(12,",
        r"innerWidth - 8",
        r"innerHeight - 8",
        r"innerWidth - 12",
        r"innerHeight - 12",
        r"(?<![A-Za-z_])PAD = 8",
        r"(?<![A-Za-z_])PAD = 12",
        r"(?<![A-Za-z_])margin = 8",
        r"(?<![A-Za-z_])EDGE = 8",
    )
    for name, text in files.items():
        for pat in residue:
            assert not re.search(pat, text), \
                f"{name} 又出现手写几何 /{pat}/(应收敛到 overlay_fit.js 单点)"
    # 5. 12px 两处显式命名 + 注释在位(hubAsk / speed-pop; 行为零变化口径保留现值)
    assert "const EDGE = 12, gap = 10;" in files["config_hub.js"], \
        "hubAsk 的 12px 必须显式命名传参(回退成手写字面量即红)"
    assert "const SPEED_PAD = 12;" in files["dialogs.js"], \
        "speed-pop 的 12px 必须显式命名(SPEED_PAD)传参"
    # 6. 顶层 const/let 跨文件撞名零容忍 —— 本轮实测事故: 收敛时七个文件各写了一个顶层
    #    const FIT, 而经典脚本的顶层 let/const 进**全局词法环境**(跨 <script> 共享):
    #    首个声明(config_hub.js)之后的六个文件全部 SyntaxError, window.AQB_* mixin 一个
    #    都没注册, 整页崩, 且静态守阵全绿(只有真浏览器现形)。跨文件别名只许方法内取或
    #    包 IIFE(参照 drawer_tpl 变体的 const T/R/H/P 全在 IIFE 内)。
    seen = {}
    for root, dirs, fnames in os.walk(shared):
        dirs[:] = [d for d in dirs if d != "vendor"]
        for fn in fnames:
            if not fn.endswith(".js"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, shared).replace(os.sep, "/")
            for m in re.finditer(r"(?m)^(?:const|let)\s+([A-Za-z_$][\w$]*)", open(path, encoding="utf-8").read()):
                name = m.group(1)
                assert name not in seen, (
                    f"shared/{rel} 与 shared/{seen[name]} 顶层同名 const/let {name} —— "
                    "经典脚本顶层 let/const 是全局词法环境, 撞名 = 后一个文件 SyntaxError、"
                    "mixin 静默不注册(整页崩, 仅真浏览器现形); 跨文件别名须方法内取或包 IIFE"
                )
                seen[name] = rel
    # 7. 行为面: node 电池(四入口七型 + 旧手写式代数等价)
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _OVERLAY_FIT_NODE_PROBE,
         os.path.join(shared, "overlay_fit.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"overlay_fit node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"几何电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


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


# node 电池(issue 26-10-20-2231): 加载真实 polling.js, 真跑骨架三口子 —— ①chain 在途不排下一拍
# (不堆叠请求) ②卡死判据持续为真 -> 超阈值补偿一次并重新计时 ③有界等待: 退避曲线与旧 _pollCmd 逐项
# 等价 / 拍数上限 / 截止时间 / 同名先停后起 / 外部叫停 / fn 抛出即 reject ④页面隐藏恒等守卫。
# 定时器全部桩住(只记节拍、手动放拍), 时钟可整体前移 —— 免得真睡 30s。无 node 静默跳过。
_NODE_POLL_SKELETON_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js
const P = window.AQB_POLL.methods;
const checks = [];
const realNow = Date.now;
let off = 0;
Date.now = () => realNow() + off;
let beats = [];            // 待放的拍(桩 setTimeout 只入队, 不真跑)
let sleeps = [];           // 记录每次排的间隔, 用于曲线对账
global.setTimeout = (fn, ms) => { sleeps.push(ms); beats.push(fn); return beats.length; };
global.clearTimeout = () => {};
const warns = [];
console.warn = (...a) => { warns.push(a.join(" ")); };
const flush = async (n) => { for (let i = 0; i < (n || 12); i++) await null; };
const fire = async () => { const f = beats.shift(); if (f) f(); await flush(); };
const mk = (over) => Object.assign({ authOk: true, calls: 0, currentPollMs: () => 1500 }, over || {});

(async () => {
  // ① 主轮 chain: 上一拍没落定前不排下一拍(不堆叠请求; setInterval 形态在这里会堆)
  let inflight = 0, maxInflight = 0, release = null;
  let t = mk();
  t.refresh = () => { inflight += 1; maxInflight = Math.max(maxInflight, inflight);
    return new Promise((r) => { release = () => { inflight -= 1; r(); }; }); };
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t.scheduleNext = P.scheduleNext;
  t.scheduleNext();
  await fire();                       // 第一拍: refresh 在途
  await fire(); await fire();         // 在途期间没有新拍可放
  checks.push(["chain 在途不排下一拍(不堆叠)", maxInflight === 1 && inflight === 1 && beats.length === 0]);
  release();
  await flush(20);
  checks.push(["落定后才排下一拍", beats.length === 1 && sleeps[sleeps.length - 1] === 1500]);
  t.stopPoll("main");
  checks.push(["stopPoll 摘句柄", !t._polls.main]);
  beats = []; sleeps = [];   // 丢掉上一节遗留的待放拍(各节独立对账)

  // ② 悬挂兜底: 卡死判据持续为真 -> 记起点 -> 超阈值补偿一次 -> 重新计时(痕只一条)
  let stuck = true, unstuck = 0;
  t = mk();
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t.startPoll("drawer", { ms: () => 1000, fn: () => { t.calls += 1; }, stall: () => stuck,
                          onStall: () => { unstuck += 1; } });
  await fire();
  checks.push(["卡死未超时: 不补偿(无 mutex 时照常走本拍)", unstuck === 0 && t.calls === 1]);
  off = 60000;                        // 时钟跳过阈值
  await fire();
  checks.push(["超阈值补偿一次", unstuck === 1]);
  off = 0;
  await fire();
  checks.push(["补偿后重新计时: 痕只一条", unstuck === 1 && warns.length === 0]);
  // 恢复(门复位)后不再判卡死
  stuck = false;
  await fire();
  checks.push(["卡死判据转假后不再补偿", unstuck === 1]);

  // ③ 有界等待: 退避曲线与旧 _pollCmd 逐项等价(首拍 firstMs, 之后 0->150 起跳、翻倍夹 cap)
  const curve = async (firstMs, capMs, maxBeats) => {
    sleeps = []; beats = [];
    const inst = mk();
    inst.awaitPoll = P.awaitPoll;
    let n = 0;
    const p = inst.awaitPoll(null, {
      ms: (i, prev) => (i === 0 ? firstMs : prev === 0 ? 150 : Math.min(capMs, prev * 2)),
      max: maxBeats,
      fn: async () => { n += 1; return null; },
      until: (r) => !!r,
    });
    for (let i = 0; i < maxBeats + 3; i++) await fire();
    return { got: await p, n, sleeps: sleeps.slice() };
  };
  let r = await curve(0, 500, 5);
  checks.push(["退避曲线 0 起点与旧实现等价(0 不睡: 150/300/500/500)",
    JSON.stringify(r.sleeps) === JSON.stringify([150, 300, 500, 500])]);
  checks.push(["拍数上限收摊兑现 null", r.got === null && r.n === 5]);
  r = await curve(500, 1000, 3);
  checks.push(["宽松曲线 500 起点(500/1000/1000)",
    JSON.stringify(r.sleeps) === JSON.stringify([500, 1000, 1000])]);

  // 截止时间 / 外部叫停 / 收敛兑现 / 抛出上抛 / 同名先停后起
  const inst = mk();
  inst.awaitPoll = P.awaitPoll;
  inst.stopPoll = P.stopPoll;
  checks.push(["截止时间到点收摊", (await inst.awaitPoll(null, { ms: () => 0, max: 9,
    deadline: () => true, fn: async () => 1, until: (v) => !!v })) === null]);
  let stop = false;
  checks.push(["外部叫停收摊", (await inst.awaitPoll(null, { ms: () => 0, max: 9, stop: () => stop,
    fn: async () => { stop = true; return null; }, until: (v) => !!v })) === null]);
  checks.push(["收敛即兑现该拍的值", (await inst.awaitPoll(null, { ms: () => 0, max: 9,
    fn: async () => "ok", until: (v) => !!v })) === "ok"]);
  let rejected = false;
  try {
    await inst.awaitPoll(null, { ms: () => 0, max: 9, fn: async () => { throw new Error("boom"); },
      until: (v) => !!v });
  } catch (e) { rejected = e.message === "boom"; }
  checks.push(["fn 抛出即 reject(401 上抛路径)", rejected]);
  let old = null, ended = 0;
  const p1 = inst.awaitPoll("tm", { ms: () => 5, max: 9, fn: async () => null, until: (v) => !!v,
    onEnd: () => { ended += 1; } });
  inst.awaitPoll("tm", { ms: () => 5, max: 9, fn: async () => null, until: (v) => !!v });
  old = await p1;
  checks.push(["同名先停后起: 旧链兑现 null(代际守卫内建)", old === null]);

  // ④ 页面隐藏: 骨架恒等守卫(调用方不再手写)
  beats = []; sleeps = [];
  const vis = mk();
  vis.startPoll = P.startPoll;
  vis.stopPoll = P.stopPoll;
  vis.startPoll("main", { ms: () => 100, fn: () => { vis.calls += 1; } });
  global.document.hidden = true;
  await fire();
  checks.push(["页面隐藏跳本拍(定时器不拆)", vis.calls === 0 && beats.length === 1]);
  global.document.hidden = false;
  await fire();
  checks.push(["回可见下一拍自动续", vis.calls === 1]);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
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


def test_frontend_poll_skeleton_single_point():
    r"""长驻 / 有界轮询骨架单点守阵(issue 26-10-20-2231-refactor-fe-polling-family-dup, 2026-10-22)

    同一份「启停 + 守卫 + 在途悬挂兜底 + 代际守卫」此前写了三份(主轮 setTimeout 链 / 抽屉
    setInterval / 流量图 setInterval), 停止条件五处手写, 且**抽屉侧漏了悬挂兜底** —— 同一类
    "loading 卡死 ⇒ 面板永久冻结在「正在加载…」"的缺陷只修了流量图一边(本件的实质缺陷面)。

    收敛形态: 骨架三口子 `startPoll` / `stopPoll` / `awaitPoll` 落在 polling.js, 各轮询只声明
    差异(ms / guard / stall / mutex / onStall / chain)。本守阵钉四层, 任一层被拆即红:
      ① 骨架三口子在 + 阈值常量 `AQB_POLL_STALL_MS`(30000 = 请求级超时 15s 的两倍余量);
      ② 三处启停一律经骨架 —— 抽屉/流量两侧裸 `setInterval` 零残留, 主轮走 `startPoll("main")`;
      ③ 停止条件单点: `document.hidden` 只许出现在骨架里(另一处是 lifecycle 的 visibilitychange
         事件响应, 那是"停表"不是"每拍判据"), 散点回潮即红;
      ④ 三条有界等待(_pollCmd / tmPollSettle / tmPollShutdown)一律经 `awaitPoll`, 手写的
         `++pollGen` 代际守卫与 setTimeout 递归不得回潮。
    行为面走 node 电池真跑(无 node 静默跳过), 见 _NODE_POLL_SKELETON_PROBE。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    poll_js = open(os.path.join(shared, "polling.js"), encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()
    chart_js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    hub_js = open(os.path.join(shared, "config_hub.js"), encoding="utf-8").read()
    cmd_js = open(os.path.join(shared, "commands.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()

    # ① 骨架三口子 + 阈值常量
    for name in ("startPoll(key, opts)", "stopPoll(key)", "awaitPoll(key, opts)"):
        assert f"    {name} {{" in poll_js, f"polling.js 缺骨架方法 {name}(启停 / 有界等待单点)"
    assert "const AQB_POLL_STALL_MS = 30000;" in poll_js, \
        "polling.js 缺悬挂兜底阈值常量 AQB_POLL_STALL_MS(30000 = 请求级超时 15s 的两倍余量)"

    # ② 三处启停一律经骨架(裸定时器零残留)
    assert 'this.startPoll("main"' in poll_js and 'this.stopPoll("main")' in poll_js, \
        "主轮启停未走骨架(旧形态 pollTimer / 裸 setTimeout 链不得回潮)"
    assert 'this.startPoll("drawer", {' in store_js and 'this.stopPoll("drawer")' in store_js, \
        "抽屉页签轮询未走骨架(裸 setInterval 回潮)"
    assert "this.startPoll(`qb:${scope}`" in chart_js and "this.stopPoll(`qb:${scope}`)" in chart_js, \
        "流量图轮询未走骨架(裸 setInterval 回潮)"
    for name, js in (("drawer_store.js", store_js), ("qb_traffic_chart.js", chart_js)):
        assert "setInterval(" not in js, f"{name} 裸 setInterval 回潮(轮询启停收口到骨架)"

    # ③ 停止条件单点: document.hidden 只许在骨架(每拍判据)与 lifecycle 的可见性事件响应里
    hidden_files = sorted(
        n for n in os.listdir(shared) if n.endswith(".js") and os.path.isfile(os.path.join(shared, n)) and
        "document.hidden" in open(os.path.join(shared, n), encoding="utf-8").read()
    )
    assert hidden_files == ["lifecycle.js", "polling.js"], \
        f"document.hidden 散点回潮(应为骨架 polling.js + lifecycle 的 visibilitychange 停表): {hidden_files}"

    # ④ 有界等待一律经 awaitPoll, 旧形态不得回潮
    assert "this.awaitPoll(null, {" in cmd_js, \
        "commands.js::_pollCmd 未走 awaitPoll 单点(旧退避 while + stop 标志不得回潮)"
    # 曲线本身写在调用点(骨架只认 ms(n, prev) 回调), 必须与旧实现逐项等价
    assert "ms: (n, prev) => (n === 0 ? firstMs : prev === 0 ? 150 : Math.min(capMs, prev * 2))," in cmd_js, \
        "命令回执轮询的退避曲线被改写(应 = 旧实现: 首拍 firstMs, 之后 0→150 起跳、翻倍夹 capMs)"
    assert 'this.awaitPoll("tm", {' in hub_js, \
        "config_hub.js 的 tmPollSettle / tmPollShutdown 未走 awaitPoll 单点"
    assert "pollGen" not in hub_js and "pollGen" not in state_js, \
        "tm 有界轮询回潮成手写 ++pollGen 代际守卫(骨架同名先停后起已内建)"

    node = shutil.which("node")
    if node:
        # 带超时: 骨架被改坏时(如拍数漏递增)电池会陷入微任务死循环, 没超时就把 CI 挂住
        try:
            proc = subprocess.run(
                [node, "-e", _NODE_POLL_SKELETON_PROBE,
                 os.path.join(shared, "polling.js")],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise AssertionError("轮询骨架 node 电池超时(骨架循环疑似失控 —— 拍数递增 / 收摊条件被拆?)")
        assert proc.returncode == 0, f"轮询骨架 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"轮询骨架电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
