"""test_webui_static_dom_panel 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

## 测试计划(每个测试函数一条)
- test_frontend_qb_traffic_chart_wiring: qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07) —— enabled=false 三挂点入口不渲染不请求(全局入口按钮 v-if="qbHistEntryOn" / 抽屉流量页签与组右键菜单项 v-if="qbTrafficOn", 门在 flags.qb_traffic_enabled, /api/webui/flags 下发 fail-closed)+ uPlot 双系列 spanGaps=false 断线不连线 + 桶序->_qbPointsToData 栅格重建与 null 语义 node 真跑(全 null 回落/前导 null 锚推算/interval 非法防御 + S3b 月行真值落点/空槽内插/anchor.xs) + 轮询下界常量 1500(A4, S3b §05.5)+ 三挂点作用域表与低频轮询口径(interval_s 夹取 + document.hidden 跳过 + 关闭/切走 clearInterval)+ 静默续拉(loading 空态只在「尚无落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误) + 同宿主 setData 原地快路 + 换肤先销毁再重建 + 错误态由成功落袋清除, 2026-10-04 修轮询期闪烁 / 2026-10-05 补齐空态与错误态闪烁)+ FX-29 软切换落定登记(_qbLoad 落袋 _drawerDone("traffic") 与 _drawerWaitSources 成对, 2026-10-04 修流量页签单击换行遮罩挂死)+ 三主题登记链(tpl/vendor/mixin/manifest)+ escBusy 与 Esc 退栈链同步(含退栈顺序: 历史弹层遮罩 130 先于抽屉 80, 2026-10-06 两图同开报障)+ 建图后宿主 ResizeObserver 自适应与销毁断开(便签 26-10-04-0134)+ 缺口三态文案与空态钉住(P4, plan 26-10-04-0721 §05: 0 桶状态行/缺口合并文案/图例 hint 两处/单种空态收窄为从未传输 + node 三段混排回归)
- test_frontend_qb_traffic_window_persist_and_single_source: 流量图「视图选择」持久化 + 窗口档位单点(2026-10-05) —— QB_WINDOW_NAMES 十三档与后端 traffic_qb.WINDOW_NAMES 逐字一致, 为展示(模板 v-for 走 qbWindowNames)/前后切换(qbCycleWindow)/持久化校验(qbInitialWindow)三处唯一来源(任一处硬编码即与后端 400 校验漂移); 持久化粒度 = 全局单独(autoqb.ui.qbWinGlobal)/组与种子共用(autoqb.ui.qbWinShared), 键按 scope 单点分派, 初值只认合法档位且坏值回落默认, 换窗即落盘并吞写入异常; 初值函数在 qb_traffic_chart.js 且三份 tpl-manifest 里排在 state.js 之前(否则 state data() 调它未定义 = 启动白屏)
- test_drawer_tpl_registry_wiring: 详情面板模板核心层接线守阵(plan 26-10-06-0838 S1) —— 三份 manifest 成对含 drawer_templates.js 且装载序 drawer.js < 核心 < state.js(state data() 调 initialDrawerTpl 依赖注册表); 变体文件 (id, tab) 唯一且 tab 合法且三 manifest 成对登记(S1 变体数为 0, 断言按当前集合写); 变体 label 展示名禁档位后缀(Q4, 报告 26-10-07-0542 —— 档位是物理形态非信息组织, 三档语义全收进本变体, 写进下拉名冗余误导); 核心含 AQB_DRAWER_TPL_REG/dtHtml+dtRaw/autoqb.ui.drawerTpl/data-dt CSS 注入单点; drawer.js 一行式钩子四类齐全(_loadDrawerTab 尾 _dtSync / 四 fetcher _dtNotify / closeDrawer _dtUnmountAll / collapse 通知)+ 列表三 fetcher 通知在 loading 清掉之后(2026-10-07 用户页空列表停"正在加载…"报障)+ drawerTab 补强二; drawer.html 宿主 x6/切换器 x2/摘要条 x2 + 经典包裹层 v-show 接 drawerTplSel; state.js 显式建字段 + app.js initialDrawerTpl + app.mixin; dt* 成员全仓无重名(mixin 覆盖静默故障, 核心书写形态不在 _scan_mixin_wiring 扫描面内, 此处补钉)
- test_drawer_tpl_variant_width_discipline: 详情面板变体宽度纪律守阵(Q1, 报告 26-10-07-0542) —— 核心注入 CSS 含四页签宿主(general/trackers/peers/content)的 max-width 1400px 居中收口(15 变体单点共享, 变体文件零复刻; traffic 双宿主排除 —— 图本体/工具条归经典链恒满宽, 13/15 KPI 头行限宽会与图缘错位, 14 解读栏自带 288px 固定右栏) + 全部变体与核心注入 CSS 禁 justify-content:space-between(label/value 两端推开病根, 标签在前值紧随; 非 kv 场景确需两端分布须显式改本守阵并注明)
- test_drawer_tpl_variant_field_icons: 详情面板变体字段行图标消费守阵(Q2, 报告 26-10-07-0542) —— general 三变体(01/02/03)字段行必须消费 drawerGeneralSections() 行级 icon 数据(sprite `<use href>` 静态引用)且含经典链 icoTone 同表派生 + .ico-t-* 着色 CSS(经典 .f-row 作用域在变体行不命中, 色表须自带); traffic 三变体(13/14/15)KPI/解读行含 sprite 图标引用; 全变体 #i-* 引用不越三皮肤 sprite 既有 symbol 集合(三皮肤集合两两相等)且不引入外部图标库(<img/iconfont/fontawesome/material-icons)
- test_drawer_tpl_table_variants_scrollleft_restore: 表格型变体横向滚动位自保守阵(P2-2, 报告 26-10-07-0542; 骨架收口 26-10-07-0845) —— 滚动自保单点收口在核心 H.withScroll(纵横两轴成对读写, 恢复次序 scrollLeft 先 scrollTop 后) + dt06/07/08/09 四变体整帧重建都包在 withScroll 回调内 + 变体内分散自保(scroller 直读写/host.parentElement)不得回潮, 任一变体绕开单点或核心两轴不成对即红
- test_drawer_tpl_trackers_per_tracker_reannounce: 06 变体逐行汇报倒计时真 per-tracker 口径守阵(P-02 升级, issue 26-10-07-0149, 2026-10-09) —— 真口径分支读行级 next_announce 且先减 nowSec(epoch 绝对时间当倒计时是事故根因) + 「全局」标(dt06-gb)只许出现在回退分支(真值行不标全局) + 回退分支仍在(qB < 5.2 无该字段, 保留种子级 detail.reannounce_in 全局近似) + nowSec 计入 sig(否则跳过重建把倒计时冻在上一帧) + 真口径分支不画微条(per-tracker interval 不可得, 不造假) + 调用点传行 t 与 nowSec
- test_drawer_tpl_a11y_and_fetch_error_states: 变体可访问性 + fetch 失败态区分守阵(P3-4/P3-5, 报告 26-10-07-0542) —— 核心层 drawer-close 钮 aria-label(种子/流量两头部成对) + 纯 div/span 模拟控件 role=button/tabindex=0(01/02/03/05/08 折叠组头含 aria-expanded、07/08/09 排序表头含 aria-sort 升/降/无随态输出、05/06 msg 展开行) + keydown 委托与 click 委托成对挂摘(挂摘纪律收口在核心 wireEvents/unwireEvents 单点, 26-10-07-0845; 变体只声明事件表)且转发前排除原生交互元素(防 Enter 双重触发) + drawer.js 三 fetcher 失败标记(trackersError/filesError/peersError)显式建字段/catch 落/成功清/换目标作废 + 九个 fetch 型变体(04-12)错误态先于空态且文案对齐轮询事实(trackers/peers 5s 轮询可写自动重试, content 无轮询不得虚构承诺)
- test_drawer_tpl_content_row_keyboard_roving: content 组行级键盘 roving tabindex 守阵(issue 26-10-07-0846) —— 核心 helpers 四件套(roving 锚点/rowFocusKey 记账/rowRestore 回焦/rowMove 移焦)单点存在; dt10/11 [data-node] 与 dt12 [data-blk]/[data-row] 行容器 tabindex=-1 不进 Tab 序(整行不加 role=button, 行内原生控件自然参与 Tab)且 CSS 带 :focus-visible 可见焦点; keydown 委托成对挂宿主且只有 ev.target 是行容器自身才接管(行内原生控件键盘行为自持); 重建前记账/重建后回焦成对(原子换帧打断焦点链, 不回焦一次激活就甩回文档头); dt12 树图块焦点互联复用悬停 onOver/onOut(focusin/focusout 同语义)
- test_drawer_tpl_variant_no_singleton_shadowing: 变体单点 T/R/H 遮蔽禁令守阵(2026-10-09 用户报障「空间树图选了不显示、换种子回落经典」) —— dt12 layoutMap 曾写 `const W = mapEl.clientWidth, H = mapEl.clientHeight`, 局部 H 把文件头 helpers 单点(reg.helpers)遮蔽成数字, 同函数尾 H.rowFocusKey(...) 对数字取属性抛 TypeError -> 核心 _dtRender catch 把该页签选择复位 classic 并落盘: 树图块只在 layoutMap 绘制故永远空白 + 用户选择跨会话被静默复位。守阵 = 每个变体文件凡声明了 T/R/H 单点(const <N> = reg.dtHtml|dtRaw|helpers), 该名在全文件(单点声明行之外)禁止再被任何声明语句绑定 —— 含多声明符列表(let a = 1, H = 2, 本案根因形态)与解构(const { H } = ...); 未声明单点的名不查(15 号变体无 H 单点, 其局部 H = 22 是合法常量)

- test_drawer_tpl_cross_seed_fold_and_select_width: 折叠态跨种子口径统一 + 变体头选择器宽度守阵(P3-6/P3-7, 报告 26-10-07-0542) —— dt10/11/12 换种子重置块(hash !== ui.lastHash)只许清选中/勾选/筛选、不得清折叠记账 ui.folded/ui.colG(口径统一为跨种子保持, 以 general 组 dt01/02 为准; 记账 key 是 path 不含 hash, 新种子旧条目自然不命中, 同名目录延续折叠选择) + dt11 勾选集必须继续重置(批量优先级真提交, 旧勾选落新种子是误操作面) + 其余变体(01-09/13-15, 记账 key 与种子无关或无折叠)不得出现 lastHash 机制 + 核心 .dt-select 定宽(160->240 后 26-10-09 用户报框太长收窄 240->150, 定宽口径不变; 定宽化归 test_drawer_tpl_select_fixed_width_tab_independent)
- test_drawer_tpl_select_fixed_width_tab_independent: 详情面板切换器占位宽与页签/选项集解耦守阵(26-10-07 用户报「切页签其它元素跟着变」) —— 核心 .dt-select 定宽(26-10-09 用户报框太长收窄至 width:150px, 只收窄不回退内容驱动宽)且不带 max-width(原生 select 自动最小宽=最宽 option 宽, dtTplOptions 按页签变化, 上限挡不住内容驱动宽的病根) + text-overflow:ellipsis 长 label 保险丝在位, 定宽单点在核心 00-core 注入层(三皮肤共享)
- test_drawer_tpl_classic_default: 详情面板模板 P-01 初装默认 classic 守阵(plan 26-10-06-0838 S1) —— 有 node 时真跑核心层 node 电池(readSel 白名单: 脏值/未注册 id/坏 JSON 一律回落 classic; register fail-fast 四分支: 重复 (id,tab)/非法 tab/非法字符 id/缺 render; dtHtml 插值自动转义 + dtRaw 显式豁免; options 不含 classic); 无 node 静态兜底: app.js initialDrawerTpl 核心未载入时也必须返回全 classic 映射(返回空对象会把经典包裹层藏掉)
- test_drawer_tpl_render_error_fallback_classic: 变体渲染抛错自动回落经典层守阵(P2-1, 报告 26-10-07-0542) —— 有 node 时真跑 _dtRender 抛错电池(该页签 drawerTplSel 复位 classic 且随 dtPersistSel 落盘 / 其它页签选择不受牵连 / 挂载态摘除(_dtMounted 置空, 后续通知按 classic 续走)/ 宿主清空 + 变体 destroy 回调 / console.error 不吞栈且带页签与变体 id / sel 已 classic 时稳态不重复复位); 无 node 静态兜底: _dtRender catch 块必须含复位/落盘/摘挂载/带 id 报错四要素(只清宿主的旧空白降级不得回潮)
- test_drawer_seed_reentry_variant_remount: 种子详情面板回页变体宿主重挂守阵(2026-10-07 报障「面板打开时切设置页再切回, 面板空白」) ——
  state.js watch(drawerVisible) 的种子详情支路(!s 分支)进场(v 为真)必须补一发重挂
  `$nextTick(() => this._dtSync())`($nextTick 等 Vue 把重建的 aside 补进 DOM 再定位宿主);
  两支路互不越界(重挂只归种子支路, 流量支路退场 _qbChartDestroy / 进场 _qbReloadOnEnter 原样)
- test_frontend_drawer_groups_shows_views: 辅种页/追剧页支持种子详情面板守阵(计划 26-10-08-1217) —— 可见性单点 drawerVisible 与打开单点 openTorrentDrawer 一律只挡主内容页(形态/视图分叉收归页面级, 此前辅种/追剧页调用 openTorrentDrawer 静默失效: 右键菜单项早已渲染且 hash 正确却点了没反应)+ 两处成员行(辅种明细/追剧集明细)必须有 @dblclick 打开入口(与种子页同款)+ 键盘光标链 _kbRows 纳入展开的成员行(辅种的组下成员/追剧的集下成员, 兑现原注释「成员行 vNext」—— 不在链上则 ↑↓ 走不到、Alt+1~5 解析不出目标)+ 跟随 _kbFollowDrawer / 5s 轮询 tick / 单种流量图 active 三处守卫一律只挡主内容页(换视图即停会让这两页的页签数据停在打开那一刻)
- test_frontend_drawer_open_switch_no_empty_flash: 详情面板显式换目标不闪空态守阵(2026-10-07 报障「切换种子时用户页闪'暂无已连接用户'」) —— openTorrentDrawer 已开(种子形态)重入分支先于重建副作用(同目标短路零副作用, 与 openDrawerTraffic 同口径 -> 换目标交棒 _switchDrawerTarget 软切换: 保留旧数据 + 160ms 延迟遮罩, 与键盘跟随同链路) + 冷启动重建(面板关着/流量形态换形)初值页签 loading 与空列表同帧置位(trackers/files/peers 三 flag 按 initialTab 落真, 详情在途窗口渲染加载态而非空态, 经典链与变体同免), 任一锚被拆或次序倒置即红
- test_removed_redundant_tooltips_stay_removed: 复述型 tooltip 不得复活守阵(报告 26-10-04-0815 + 详情面板二轮清理) —— 模板已移除的复述型原生 title 文案(statusbar「点击修改」「数据状态」/ topbar 页签「按分组展示」「全部种子一行一条」/ drawer「关闭(Esc)」/ dialogs 族 title="关闭" / settings-detail·xtpl「点击收起」/ columns.js H1 横幅「点击关闭」/ drawer_tpl 二轮: 05 图例五色与条级顺序说明·06 等待响应与仅看异常说明·07-09 求和口径/客户端 Top 复述/qB flags 前缀/会话累计/对端整行复述·10-11 展开折叠全部目录与全选与目录文件数·12 优先级跳过与占比细条·13-15 kpis 容器派生口径与窗口累计复述)不得写回, 悬浮提示一律走 shared/ui_feedback.js 拦截层
- test_recheck_confirm_wired_all_mouse_entries: 重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3) —— commands.js _recheckConfirm 单点(helper 存在 + 文案与 okText 调用形态沿键盘路径原样)+ bulkAct 批量通道 / drawer.js torrentCmd 单选通道各含 recheck 确认分支 + shortcuts.js _kbAct 改调共用 helper 不再内联 confirmDialog 文案 + 共用文案字符串全仓只此一份, 任一接入点被重构摘除即红
- test_skip_check_dialog_precheck_wired: 跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4) —— ui_feedback.js _modalInit 声明 okDisabled/busy/verdict 三字段 + popovers.html 确认钮 :disabled="modal.okDisabled" 绑定 / busy 行 / verdict 行式渲染区(强制钮复用 extraText 第三钮 danger-solid) + drawer.js 两入口(skipCheckTorrent/skipCheckMulti, 后者带可选 targets 供单组入口 skipCheckGroup 复用)均交棒 _skipCheckDialog 且不再自带 _openModal + _skipCheckDialog 进框即禁用(busy + 固定警示区)并发预检(_skipPrecheck), 任一被重构摘除即红
- test_skip_check_dialog_verdict_render: 跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4) —— _skipPrecheck 状态机分支(预检失败降级=启用普通确认且无强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认钮文案「跳检 N 个可跳检的」+ 强制钮「强制跳检全部」/ force-only=确认保持禁用 / 全 ok=只启用确认)+ ok 子集派生(cls==="ok" 过滤)+ 确认路径送 ok 子集而强制路径送全量+force(_skipExec 单发 body 仅 force 时带 force 键, 批量确认只走 hashes 通道)+ 降级文案「后端闸门仍会在执行时拦截」+ _skipVerdictRows 计数行与分组上限截断(slice(0,5)+等 X 个), 任一分支被改写即红
- test_modal_identity_stamp_landing_guard: 模态身份戳落袋守卫单点(F1-01, issue 26-10-06-0028) —— ui_feedback.js _openModal 每框发自增 mid + _modalIsCurrent 单点(visible + mid 双比对) + drawer.js _skipCheckDialog 把 this.modal.mid 交棒 _skipPrecheck 且落袋守卫为 seq + 身份戳双条件(取消跳检框后开无关 modal, 只有身份戳拦得住迟到回执)
- test_frontend_ctx_menu_multi_select_targets_selection: 多选右键菜单守阵 —— 四个 open*Menu 必须写 menu.multi、三套 UI 必须有批量分支且调 ctxAct/ctxDelete、ctxAct/ctxDelete 必须复用 bulkAct/bulkDelete
- test_frontend_ctx_menu_group_actions_parity: 单组右键菜单与多选批量菜单项集一致守阵(2026-10-09 用户报「单组右键菜单缺选项」)—— 单组 v-else 分支必含六个组级入口(重新校验/跳检/限速/移动/标签分类/导出, 与批量分支同项集)、跳检项吃 flags.skip_check_menu 门控、六入口复用多选同一套下游链路(recheckGroup->_actCore / 限速移动跳检->drawer.js 多选对话框 / metaGroup->openMetaDialog / exportGroup->_exportHashes)不为组级另开旁路
- test_frontend_meta_dialog_paired: 标签/分类编辑对话框守阵 —— 三套 UI 成对(metaOpen 对话框 + 批量菜单/单种子菜单两处入口, 批量控制条退役后模板层不再直接调 openMetaDialog(null))、shared 逻辑接线(openMetaDialog 锁定目标 + metaToggleTag 走 bulk 链路 + ctxMeta 先收菜单)、.meta-dialog/.opt-pill 三套 CSS 成对定义
- test_frontend_add_torrent_drag_drop_wiring: DND-01 全局拖拽添加种子接线守阵(静态) —— window 级 drag 四事件 add/remove 对称、drop handler 必 preventDefault(否则浏览器直接打开文件)、接管判据只认 Files/text-uri-list(不误拦页面内拖文本)、双 UI 落点遮罩成对 + app.js addDragOver 状态
- test_frontend_add_combo_blur_close_and_fit: 添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障) —— 三输入框 @focusout 收层 + 收层必须 40ms 合帧守卫(label 转发回焦同步收 = 闪烁) + 三开层方法撤销挂起收层 + 开层 watcher 量「输入行→滚动容器可见底沿」净空限高(滚动条留在窗口内) + 候选异步到位重限 + 三浮层互斥双向(closeAddPopsExcept 单点, 三开层各调一次, 26-10-04-0130)
- test_frontend_ctx_menu_refit_by_measured_size: 浮层菜单开层实测钳位守阵(issue 26-10-06-1717) —— _menuFit 按 offsetWidth/offsetHeight 实测算(退回常量估算即红)且以视口为界、每次复位兜底限高; 三个菜单容器 ref(ctxMenu/headMenuEl/filePrioEl)与三个开层 watcher 的 (stateKey, refName) 一一对上且都在 $nextTick 里量; _menuFitRefit 现读 this[stateKey]/this.$refs[refName] 并守 visible
- test_frontend_add_combo_label_clear_mask_and_refit: 添加种子三下拉「第二轮遗留四项」守阵(2026-10-03, label 闪烁 2026-10-04 三修+四轮 JS 守卫) —— 四个 combo 的字段 label 一律 @mousedown.prevent + @click.stop(mousedown 默认动作 blur 武装的 40ms 合帧定时器在人手按住期间先收层、松手转发回焦再重开 = 闪烁; stop 挡 window click 收层; 缺一即回归)+ 收层 JS 单点守卫 _popBlurShouldHold(收层前判「焦点已回本族输入框 / 本族 label 转发 click 仍在途」→ 不收, 模板修饰符缺位(旧页签残留)时独立根除闪烁, add 三字段 + meta 分类全接)+ 三输入框内嵌清空 x(@mousedown.prevent 保焦点 + @click.stop 挡 window 收层, 缺一即「清完下拉没了」)+ 遮罩关窗改「mousedown 记臂位 + mouseup.self 才关」(全仓 11 处, @click.self 会被"拖选文字终点落在遮罩上抬手"误判成点空白关窗, 零残留)+ 过滤词变化重限高(三个输入值 watcher + meta 侧三处)+ meta 分类下拉补失焦收层与 window click 兜底名单 + 清空钮样式三皮肤成对
- test_frontend_ctx_submenu_single_entry_and_hover_close: 右键次级菜单守阵 —— 一级只留「更多操作」一个入口(复制族并入, CTX-06)、移出父项后延迟收起(CTX-05)、hover 图标规则必须限定直接子级且压特异性否则整片子面板变灰(CTX-04)
- test_frontend_qb_traffic_yaxis_and_annotation: 流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做) —— _qbYRange/_qbGapRuns 纯函数 node 真跑(自动 = peak*1.05 / 固定上限取 max(cap, peak*1.05) 峰值超上限按峰值显示 / 缺口 = 上下行皆 null 才算); 限速三作用域同源 = qB 全局限速上下行**较大者**(_qbGlobalLimit -> speedLimitBytes); 上限派生单点 _qbYCapOf(limit×1.2 / manual MiB); 三作用域**各自独立**持久化(qbYAxisStoreKey 三键 + qbInitialYAxis 只认合法模式与正数 + persistQbYAxis 吞异常) + 切档落盘重排(qbSetYAxisMode/qbSetYAxisManual -> _qbChartRescale 走 setData 重算 scale 不重建) + 限速变化重排 watcher(mounted 注册, this.drawer 守卫剔除 BaseTransition 假实例); 建图 y range 接纯函数 + draw/drawClear 两钩子画限速虚线/缺口斜纹(共享图面三挂点全生效, uPlot.pxRatio 设备像素换算, 限速线只画落在可视值域内的); 模板 .qb-tools/.qb-seg 控件 + qbYAxisCapText 读数 + CSS 三皮肤成对 + **两处控件组**(流量形态头部 + 种子「流量」页签头部, 2026-10-09 修版式改回归: 种子流量图走种子形态头部, 版式改漏接 ⇒ 档位/纵轴控件消失; 内层标记守阵钉逐字同源)
- test_frontend_add_options_recent_order: 添加种子三候选「最近使用」排序守阵(2026-10-09 用户动议: 保存路径/分类/标签按最近使用排序) —— 口径 = 由种子记录派生(非本机存储): 「最近使用」= 该值下种子 added_on 最大值, 数据面**跨视图自取数** `_addRecencyRows`(与 filters.js::facetRows 同族; 添加入口是顶栏常驻而 /api/state 按 viewMode 裁剪阵列, 直读 this.torrents 会在默认辅种页拿到空表 ⇒ 排序静默退化成字母序, 2026-10-09 e2e 首跑实测) ⇒ 零新存储; node 真跑 _addOrderByRecent(最近使用降序 -> 未用过落末尾并按字母序 -> 表空/表 null/值未命中一律退化纯字母序 + 纯函数不改入参)与 _addNormPath(与后端 infra/utils.path_normalize 同口径; 两侧不同径则 /api/paths 已归一路径与取数行的 qB 原文 save_path 对不上, 时间表恒不命中 ⇒ 静默退化成纯字母序); 静态钉接线(三候选都过 _addOrderByRecent 单点 + pick 不得再内联 .sort + _addRecencyMaps 经 _addRecencyRows 现算且三键齐全 + 路径键过 _addNormPath + _addRecencyRows 按 viewMode 分支且三来源齐全)
"""
import json
import os
import re
import shutil
import subprocess

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_aggregate,
    _app_bundle_files,
    _app_bundle_text,
)

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
      流量面板内; 抽屉「流量」页签按钮与组右键「qB 口径流量图」菜单项 v-if="qbTrafficOn";
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
    statusbar = open(os.path.join(shared, "tpl", "statusbar.html"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    dock_tpl = open(os.path.join(shared, "tpl", "dock.html"), encoding="utf-8").read()
    ctx_menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. enabled 门(fail-closed 单点; 三挂点共用 qbTrafficOn, 全局入口另挂今日流量面板本体)
    assert 'flags: { skip_check_menu: false, qb_traffic_enabled: false }' in state_js, \
        "state.js flags 默认缺 qb_traffic_enabled: false(fail-closed 初值必须显式建)"
    assert "qb_traffic_enabled: !!(f && f.qb_traffic_enabled)" in lifecycle_js, \
        "loadWebFlags 必须写回 qb_traffic_enabled(缺了旗标恒 false = 功能永不可见)"
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
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
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
    assert 'tab === "traffic" && this.qbTrafficOn' in drawer_js and 'this._qbPollStart("torrent")' in drawer_js, \
        "drawer.js _loadDrawerTab 缺流量页签分支(加载 + 起轮询)"
    assert 'this._qbPollStop("torrent")' in drawer_js, \
        "drawer.js _stopDrawerPoll 缺流量轮询收口(关抽屉/切页签/换目标全走这里 = 关闭即停)"
    assert 'last === "traffic" && !this.qbTrafficOn' in drawer_js, \
        "drawer.js 打开抽屉缺流量页签初值归一(功能关闭时上次停留页签须落回常规页)"
    # 全局/分组挂点: 组右键菜单项(v-if 门) + 抽屉流量形态(共用正文块/建图落点/关闭/窗口切换)
    assert 'v-if="qbTrafficOn"' in ctx_menus and 'openQbGroup(menu.key)' in ctx_menus, \
        "ctx-menus.html 缺组右键「qB 口径流量图」菜单项(v-if 门 + menu.key 直用的 encode_group_key 通道)"
    assert ctx_menus.count("openQbGroup(menu.key)") == 1, "组右键菜单项只能挂在单组菜单(多选/剧集菜单不得出现)"
    assert 'v-if="qbTrafficActive"' in drawer_tpl and 'ref="qbChartHost"' in drawer_tpl \
        and 'qbSetWindow(w)' in drawer_tpl and 'qbCurSummary' in drawer_tpl, \
        "drawer.html 缺流量形态正文块(三挂点共用: qbTrafficActive 门 / 建图落点 / 窗口切换 / 汇总)"
    assert 'drawer.kind === \'traffic\'' in drawer_tpl and 'qbTrafficTitle' in drawer_tpl, \
        "drawer.html 缺流量形态头部(标题取 qbTrafficTitle)"
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
    assert "if (!def.active(this) || document.hidden || this[def.loading]) return;" in js, \
        "轮询 tick 缺 document.hidden / 不活跃 / 在途未落袋跳过(先例 _startDrawerPoll)"
    assert js.count("clearInterval(") == 1, \
        "组件内 clearInterval 只允许在 _qbPollStop 单点(轮询停止收口)"
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
    wait_blk = re.search(r"_drawerWaitSources\(tab\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert wait_blk and 'return ["detail", tab]' in wait_blk.group(1), \
        "drawer.js _drawerWaitSources 通用分支必须覆盖 traffic 页签(与 _qbLoad 的落定登记成对, 拆开即挂死)"
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
    assert 'v-if="qbCurHover.up + qbCurHover.dl === 0">0 B/s · 空闲/做种中</span>' in drawer_tpl, \
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
    # 版式改结构钉住: ①时间档位与纵轴控件在流量形态头部(标题栏)内, 不在正文; ②图例(上行/下行)
    # 在统计栏 .hist-summary 内, 不再是独立的 .hist-legend 行
    head_blk = re.search(
        r'<header v-if="drawer\.kind === .traffic." class="drawer-head">(.*?)</header>', drawer_tpl, re.S
    )
    assert head_blk and 'class="qb-tabs"' in head_blk.group(1) and 'class="qb-tools"' in head_blk.group(1), \
        "时间档位(.qb-tabs)与纵轴控件(.qb-tools)必须落在流量形态头部标题栏内(2026-10-08 版式改: 自正文上提, 把高度还给图)"
    # 2026-10-09 第 2 轮(用户动议): 种子流量图(kind === "seed" + tab === "traffic")的档位/纵轴
    # 控件组**从种子头部挪走** —— 头部已承载五页签导航 + 模板切换器, 13 档再并进去太挤、窄视口下
    # 会变形; 改落**图下统计栏** .hist-summary, 排在「下载累计」之后(用户: 「即『下载累计』后」)。
    seed_head_blk = re.search(r'<header v-else class="drawer-head">(.*?)</header>', drawer_tpl, re.S)
    assert seed_head_blk and 'class="qb-statctl"' not in seed_head_blk.group(1) \
        and 'class="qb-headctl"' not in seed_head_blk.group(1), \
        "种子头部不得再挂流量档位/纵轴控件组(2026-10-09 第 2 轮: 已改落图下统计栏, 头部保持单行 44px)"
    stat_blk = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('data-dt-host="traffic-post"')]
    assert 'class="qb-statctl"' in stat_blk and 'class="qb-tabs"' in stat_blk and 'class="qb-tools"' in stat_blk, \
        "种子「流量」页签的档位/纵轴控件组必须落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮)"
    assert "v-if=\"qbCurScope === 'torrent'\"" in stat_blk, \
        "统计栏内的档位/纵轴控件组必须门在 qbCurScope === 'torrent'(种子形态 + 流量页签 + 功能开启的单点派生)"
    # 统计栏本体的门放宽一档(有汇总 **或** 种子流量形态): 首载/错误态没有汇总, 控件仍必须可见 ——
    # 否则「数据取不到 ⇒ 连换档位都点不到」; 与 2026-10-08 之前正文工具条恒可见的语义对齐。
    assert 'v-if="qbCurSummary || qbCurScope === \'torrent\'"' in drawer_tpl, \
        "统计栏本体必须门在「有汇总 或 种子流量形态」上(否则首载/错误态控件整组消失)"
    # 落点次序(用户口径「即『下载累计』后」): 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 控件组
    _order = [stat_blk.index(k) for k in ("hs-leg", "窗口", "上传累计", "下载累计", "qb-statctl")]
    assert _order == sorted(_order), \
        "统计栏次序必须为 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 档位/纵轴控件组"
    assert 'hs-leg' in stat_blk and '上行' in stat_blk and '下行' in stat_blk, \
        "统计栏(.hist-summary)必须含上行/下行图例(.hs-leg), 且排在「窗口 N 桶」之前"
    # 口径注解(2026-10-09 第 3 轮, 用户动议): 常驻文案退场, 改为两个累计读数的悬浮提示。
    # title 走全局断供管道(ui_feedback.js 落 DOM 即迁 data-aq-tip), 文案单点仍是 qbCurSummaryHint。
    assert stat_blk.count(':title="qbCurSummaryHint"') == 2, \
        "「上传累计 / 下载累计」两处都要挂口径注解的悬浮提示(文案单一来源 qbCurSummaryHint)"
    assert 'class="hist-hint"' not in drawer_tpl, \
        "统计栏常驻口径文案(.hist-hint)必须退场(已改为两个累计读数的 tooltip; 弹层 popovers.html 里那处是另一用途)"

    # 两处控件组必须同源: 内层 .qb-tabs/.qb-tools 逐字一致(空白归一后比较), 一处改了另一处必须同步
    def _ctl_inner(blk):
        i = blk.index('<div class="qb-tabs">')
        j = blk.index('</div>', blk.index('qbYAxisCapText'))
        return re.sub(r"\s+", " ", blk[i:j])

    assert _ctl_inner(head_blk.group(1)) == _ctl_inner(stat_blk), \
        "两处流量档位/纵轴控件组已漂移(流量形态头部 vs 图下统计栏; 内层 .qb-tabs/.qb-tools 必须逐字同源)"
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

    # 1. 档位清单单点 + 与后端逐字一致 + 展示面走 computed(模板不再硬编码)
    m = re.search(r"const QB_WINDOW_NAMES = \[(.*?)\];", js, re.S)
    assert m, "qb_traffic_chart.js 缺 QB_WINDOW_NAMES 单点(档位清单)"
    names = re.findall(r'"([^"]+)"', m.group(1))
    assert tuple(names) == tuple(WINDOW_NAMES), \
        f"前端档位清单与后端 traffic_qb.WINDOW_NAMES 漂移: 前端 {names} / 后端 {list(WINDOW_NAMES)}"
    assert 'QB_WINDOW_DEFAULT = "24h"' in js, "缺 QB_WINDOW_DEFAULT(初值 / 非法档回落值)"
    assert re.search(r"qbWindowNames\(\) \{\n\s*return QB_WINDOW_NAMES;", js), \
        "qbWindowNames computed 必须直返 QB_WINDOW_NAMES(模板 v-for 的唯一来源)"
    assert 'v-for="w in qbWindowNames"' in drawer_tpl, "drawer.html 窗口按钮必须 v-for qbWindowNames"
    assert "v-for=\"w in ['1m'" not in drawer_tpl, "drawer.html 仍硬编码档位清单(与单点漂移)"
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


# 纵轴固定模式 + 缺口游程 node 电池(2026-10-08): 两个模块级纯函数 _qbYRange/_qbGapRuns 真跑。
# 无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
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
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


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
       证伪, 设了就是假锚)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()

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
    for member in ("_qbCanvasScale(u)", "_qbDrawGaps(u, tk)", "_qbDrawLimits(u, tk)"):
        assert member in js, f"缺画布注解层成员 {member}"
    assert "uPlot.pxRatio" in js, "画布注解层必须按 uPlot.pxRatio 换算设备像素(uPlot ctx 无 transform)"
    dl = re.search(r"_qbDrawLimits\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert dl and "lim.up < ymax" in dl.group(1) and "lim.down < ymax" in dl.group(1), \
        "限速虚线必须只画落在可视值域内的限速(超顶沿的线不可见, 自动模式峰值未超限速即不画)"

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
    for comp in ("qbCurYAxis()", "qbYAxisMode()", "qbYAxisManual()", "qbYAxisCapText()"):
        assert comp in js, f"缺纵轴 computed {comp}"

    # 9. 模板控件(2026-10-08 版式改: 自正文上提到流量形态头部标题栏) + 生效上限读数
    hdr = re.search(r'<header v-if="drawer\.kind === .traffic." class="drawer-head">(.*?)</header>', drawer_tpl, re.S)
    assert hdr, "drawer.html 缺流量形态头部(标题栏)"
    assert 'class="qb-tools"' in hdr.group(1) and 'class="qb-seg"' in hdr.group(1), \
        "drawer.html 纵轴控件(.qb-tools/.qb-seg)必须落在流量形态头部内(2026-10-08 版式改上提)"
    assert drawer_tpl.count("qbSetYAxisMode(") == 6, \
        "纵轴三态各一个按钮(自动/限速+20%/手动) × 两处控件组(流量形态头部 + 种子「流量」页签头部)"
    assert "v-if=\"qbYAxisMode === 'manual'\"" in hdr.group(1) \
        and "qbSetYAxisManual($event.target.value)" in hdr.group(1), \
        "手动模式必须给输入框且 @change 走 qbSetYAxisManual"
    assert "{{ qbYAxisCapText }}" in hdr.group(1), "缺生效上限读数(qbYAxisCapText)"
    # 2026-10-09 第 2 轮: 种子「流量」页签同款控件组改落图下统计栏(.qb-statctl, qbCurScope === 'torrent' 门)
    stat_hdr = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('data-dt-host="traffic-post"')]
    assert 'class="qb-tools"' in stat_hdr and 'class="qb-seg"' in stat_hdr, \
        "drawer.html 纵轴控件(.qb-tools/.qb-seg)必须同时落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮)"
    assert "v-if=\"qbYAxisMode === 'manual'\"" in stat_hdr \
        and "qbSetYAxisManual($event.target.value)" in stat_hdr, \
        "统计栏内的手动模式必须给输入框且 @change 走 qbSetYAxisManual"

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
ok("mixin 挂上 window.AQB_DRAWER_TPL", typeof window.AQB_DRAWER_TPL.methods.dtPick === "function"
  && typeof window.AQB_DRAWER_TPL.computed.dtTplCurrent === "function");

const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed }));
if (failed.length) process.exit(1);
"""


def test_drawer_tpl_registry_wiring():
    """详情面板模板核心层接线守阵(plan 26-10-06-0838 S1) —— 三份 manifest 成对含核心且装载序正确;
    变体文件 (id, tab) 唯一且 tab 合法; 核心含 dtHtml / autoqb.ui.drawerTpl 单点; drawer.js 一行式
    钩子四类齐全; drawer.html 宿主/切换器/摘要条成对加挂; 变体 label 展示名禁档位后缀(Q4, 报告
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

    # 4. drawer.js 一行式钩子四类齐全(方法本体在核心层, 这里只有调用点)
    m = re.search(r"_loadDrawerTab\(tab\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert m and "this._dtSync()" in m.group(1), "_loadDrawerTab 尾部缺 _dtSync(换页签不挂/不卸变体)"
    for typ in ("detail", "trackers", "files", "peers"):
        assert f'this._dtNotify("{typ}")' in drawer_js, f"四 fetcher 落袋处缺 _dtNotify(\"{typ}\")"
    # 4a. 列表三 fetcher 的落袋通知必须在 loading 清掉之后(变体只在 _dtNotify 时重渲染,
    #     通知先于清 loading = 空列表停在"正在加载…"到下一拍 5s 轮询; 2026-10-07 用户页报障。
    #     detail 不在列: general 变体不渲染 loading 态, 经典层走 Vue 响应式无此窗口)
    for fname, flag in (("Trackers", "trackersLoading"), ("Files", "filesLoading"), ("Peers", "peersLoading")):
        fm = re.search(rf"async _fetchDrawer{fname}\(.*?\n    \}},", drawer_js, re.S)
        assert fm, f"_fetchDrawer{fname} 形态漂移(守阵正则失配, 同步本守阵)"
        clear = fm.group(0).find(f"this.drawer.{flag} = false")
        notify = fm.group(0).find(f'this._dtNotify("{fname.lower()}")')
        assert clear != -1 and notify != -1 and clear < notify, \
            f"_fetchDrawer{fname}: _dtNotify 必须在 {flag} 清掉之后(次序反 = 空列表停\"正在加载…\"一拍轮询)"
    m = re.search(r"closeDrawer\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert m and "this._dtUnmountAll()" in m.group(1), "closeDrawer 缺 _dtUnmountAll(变体定时器/监听不清)"

    # 5. drawer.html 加挂面: 宿主 x6(单栏)+ x4(合并双列, v-if/v-else 与单栏互斥)/ 切换器 x2
    for host in ("general", "trackers", "peers", "content", "traffic-pre", "traffic-post"):
        assert f'data-dt-host="{host}"' in drawer_tpl, f"drawer.html 缺变体宿主 {host}"
    assert drawer_tpl.count('class="dt-select"') == 2, "drawer.html 切换器应恰 2 处(种子头部/流量头部)"
    # R2 S1(计划 26-10-09-2219): 经典包裹层退役 —— classic 是注册表正式条目(drawer_pages/),
    # 与变体同宿主挂载; drawer.html 不再允许 v-show 读 drawerTplSel 的经典包裹层回潮
    assert 'v-show="drawerTplSel.general === \'classic\'"' not in drawer_tpl, \
        "经典包裹层回潮(classic 已是页插件, 显隐只走 dt-host 自身)"
    for tab in ("general", "trackers", "peers", "content"):
        for ui in _UI_ALL:
            assert f"/shared/drawer_pages/{tab}-classic.js" in _ui_manifest(ui)["scripts"], \
                f"{ui}: manifest 缺 classic 插件 drawer_pages/{tab}-classic.js"
    # R2 S2/S3 接线: 合并标志显式建字段 + 双列宿主 + 右键菜单
    assert "drawerMerge: initialDrawerMerge()" in state_js, "state.js 缺 drawerMerge 显式建字段(vue-reactivity 坑)"
    assert "dtWinW:" in state_js, "state.js 缺 dtWinW 显式建字段(dtSplitOn 响应式消费)"
    assert "drawerMenu: { visible: false, x: 0, y: 0 }" in state_js, "state.js 缺 drawerMenu 显式建字段"
    assert 'class="drawer-split"' in drawer_tpl, "drawer.html 缺合并双列宿主(R2 S2)"
    assert "@contextmenu.prevent=\"openDrawerMenu($event)\"" in drawer_tpl, "drawer.html 缺右键菜单接线(R2 S3)"
    assert "function initialDrawerMerge()" in app_js, "app.js 缺 initialDrawerMerge"

    # 6. state/app 接线 + dt* 成员全仓无重名(mixin 覆盖形态, 静默故障)
    assert "drawerTplSel: initialDrawerTpl()" in state_js, "state.js 缺 drawerTplSel 显式建字段(vue-reactivity 坑)"
    assert "function initialDrawerTpl()" in app_js, "app.js 缺 initialDrawerTpl"
    assert "app.mixin(window.AQB_DRAWER_TPL)" in app_js, "app.js 未注入 AQB_DRAWER_TPL(核心方法域整体消失)"
    dt_members = {
        n
        for n in re.findall(r"^      (?:async )?([A-Za-z_$][\w$]*)\s*[(:]", core, re.M)
        if n.startswith("dt") or n.startswith("_dt")
    }  # 只收 dt* 成员(裸 if/for 同缩进形态不收)
    assert {"dtPick", "dtHostOn", "_dtSync", "_dtNotify", "_dtUnmountAll"} <= dt_members, \
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


def test_drawer_tpl_variant_field_icons():
    """详情面板变体字段行图标消费守阵(Q2, 报告 26-10-07-0542) —— general 三变体(01/02/03)
    字段行必须消费 drawerGeneralSections() 自带的行级 icon 数据(sprite `<use href>` 静态引用,
    字符串拼 HTML 不走 Vue 绑定)且含经典链 icoTone 同表派生 + .ico-t-* 着色 CSS(经典选择器
    .f-row .ico-t-* 在变体行不命中, 变体必须自带重定作用域的色表); traffic 三变体(13/14/15)
    KPI/解读行必须含 sprite 图标引用; 全部六变体的 #i-* 引用都不得超出三皮肤 index.html
    sprite 的既有 symbol 集合(三皮肤集合还必须两两相等, 防单边加图标), 且不得引入外部图标库
    (<img / iconfont / fontawesome / material-icons)。"""
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

    # 3. traffic 三变体: KPI/解读行含 sprite 图标引用(上下行累计为基线, 任一变体缺即退化为纯文字)
    for name in (
        "13-traffic-chart-led-tall.js", "14-traffic-annotated-split-low.js", "15-traffic-adaptive-collapsed.js"
    ):
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        for icon in ("#i-upload", "#i-download"):
            assert icon in text, \
                f"drawer_tpl/{name}: KPI 行缺 sprite 图标 {icon}(Q2: traffic 变体零图标复发)"

    # 4. 引用不越界 + 不引入外部图标库(全变体扫描, 含未来新增文件)
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
    ④nowSec 计入 sig(否则跳过重建把倒计时冻在上一帧); ⑤真口径分支不画微条(per-tracker interval
    不可得, 分母不存在, 不造假); ⑥调用点 nextHtml 必须拿到行 t 与 nowSec。"""
    vdir = os.path.join(STATIC_ROOT, "shared", "drawer_tpl")
    text = open(os.path.join(vdir, "06-trackers-table-collapsed.js"), encoding="utf-8").read()
    # ① 真口径: 读行级 next_announce + 先减 now
    assert "t.next_announce" in text, "06 逐行倒计时未读行级 next_announce(P-02 真口径回退)"
    assert "Math.round(na - nowSec)" in text, "06 未以 epoch 减 nowSec 得剩余(epoch 当倒计时 = 事故根因)"
    # 真口径分支 = nextHtml 里回退行(const d = ...)之前的那段
    real_branch = text[text.index("function nextHtml"):text.index("const d = (ctx.drawer")]
    # ②「全局」标只在回退分支
    assert "dt06-gb" not in real_branch, "06 真口径行仍带「全局」标(真值不该标全局)"
    # ③ 回退分支仍在
    assert "dt06-gb" in text, "06 回退分支(全局近似)被删(qB < 5.2 无 next_announce 会整列空白)"
    assert "detail.reannounce_in" in text, "06 回退分支未用种子级 detail.reannounce_in"
    # ④ nowSec 计入 sig(否则跳过重建冻帧)
    assert re.search(r'"\|" \+ nowSec\b', text), "06 未把 nowSec 计入 sig(跳过重建会把倒计时冻在上一帧)"
    # ⑤ 真口径分支不画微条
    assert "dt06-tbar" not in real_branch, "06 真口径行仍画微条(per-tracker interval 不可得, 属造假)"
    # ⑥ 调用点传参
    assert "nextHtml(ctx, t, nowSec)" in text, "06 nextHtml 调用点未传行 t / nowSec(真口径拿不到数据)"


def test_drawer_tpl_a11y_and_fetch_error_states():
    """详情面板变体可访问性 + fetch 失败态区分守阵(P3-4/P3-5, 报告 26-10-07-0542) ——
    核心层 drawer-close 钮 aria-label(种子/流量两头部成对, 仅 svg 无文字读屏不可达);
    纯 div/span 模拟控件 role="button" tabindex="0": 01/02/03/05/08 折叠组头(含 aria-expanded)
    + 07/08/09 排序表头(含 aria-sort 升/降/无随排序态输出)+ 05/06 msg 展开行; keydown 委托与
    click 委托成对挂宿主(wire 挂 / destroy 摘)且 Enter/Space 转发前排除原生 button/summary 等
    自身发 click 的元素(防双重触发); 三个列表 fetcher 失败标记(trackersError/filesError/
    peersError)成功落袋即清、换目标作废; 九个 fetch 型变体(04/05/06/07/08/09/10/11/12)
    空列表先判错误态再判空态, trackers/peers 文案带自动刷新重试口径(5s 轮询真实存在)、
    content 文案不承诺自动重试(content 页签无轮询)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    vdir = os.path.join(shared, "drawer_tpl")

    # 1. 核心层关闭钮 aria-label(种子/流量两头部成对各一处; 原生 button 键盘本可达, 缺的只是可访问名)
    assert drawer_tpl.count('<button class="drawer-close" aria-label="关闭详情面板"') == 2, \
        "drawer.html: drawer-close 两钮缺 aria-label(种子/流量两头部成对)"

    # 1.5 挂摘纪律单点(骨架收口 26-10-07-0845): 核心 wireEvents/unwireEvents 挂摘必须成对
    # (同一张 host.__dtEvents 记账表), 变体不再各自维护 __dtNNWired 标志
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    assert "for (var k in map) host.addEventListener(k, map[k]);" in core \
        and "for (var k in host.__dtEvents) host.removeEventListener(k, host.__dtEvents[k]);" in core, \
        "核心 wireEvents/unwireEvents 挂摘不成对(换变体监听叠加回潮)"

    # 2. 纯 div/span 模拟控件 role/tabindex/aria(只盘模拟控件; 原生 button 有 title 充当可访问名不动)
    fold_variants = (
        "01-general-hero-tall.js", "02-general-cards-low.js", "03-general-dossier-collapsed.js",
        "05-trackers-health-groups-low.js", "08-peers-groups-low.js"
    )
    sort_variants = ("07-peers-dashboard-tall.js", "08-peers-groups-low.js", "09-peers-density-collapsed.js")
    msg_variants = ("05-trackers-health-groups-low.js", "06-trackers-table-collapsed.js")
    all_a11y = sorted(set(fold_variants + sort_variants + msg_variants))
    for name in all_a11y:
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        if name in fold_variants:
            assert re.search(r'data-fold[^>]*role="button"|role="button"[^>]*data-fold', text.replace("\n", " ")), \
                f"drawer_tpl/{name}: 折叠组头缺 role=button(P3-4: 纯 div+click 键盘不可达)"
            assert 'aria-expanded="' in text, \
                f"drawer_tpl/{name}: 折叠组头缺 aria-expanded(读屏不知道折叠态)"
        if name in sort_variants:
            assert re.search(r'role="button"[^>]*aria-sort="|aria-sort="[^>]*data-sort', text.replace("\n", " ")), \
                f"drawer_tpl/{name}: 排序表头缺 role=button + aria-sort(P3-4: 升/降/无随排序态输出)"
            assert 'ui.sortDir === 1 ? "ascending" : "descending"' in text, \
                f"drawer_tpl/{name}: aria-sort 未按当前排序态输出升降(只在渲染函数里随态输出)"
        if name in msg_variants:
            assert re.search(r'data-msg[^>]*role="button"|role="button"[^>]*data-msg', text.replace("\n", " ")), \
                f"drawer_tpl/{name}: msg 展开行缺 role=button(P3-4: 纯 span+click 键盘不可达)"
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

    # 3. drawer.js 失败标记: 显式建字段(vue-reactivity 口径) + catch 落标记 + 成功清 + 换目标作废
    for fld in ("trackersError", "filesError", "peersError"):
        assert f'{fld}: ""' in drawer_js, \
            f"drawer.js: drawer 初值缺 {fld} 显式建字段(vue-reactivity 坑: 后补属性不进响应式)"
        assert f"this.drawer.{fld} = e.message" in drawer_js, \
            f"drawer.js: {fld} 未在 fetcher catch 落失败标记(P3-5: 变体拿不到区分信号)"
        assert f'this.drawer.{fld} = "";' in drawer_js, \
            f"drawer.js: {fld} 成功落袋后未清(上一次失败永久钉住错误态)"
    assert 'this.drawer.trackersError = this.drawer.filesError = this.drawer.peersError = "";' in drawer_js, \
        "drawer.js: 换目标(软切换)未作废三个失败标记(旧目标错误态串显到新目标)"

    # 4. 九个 fetch 型变体: 错误态先于空态; 文案与轮询事实对应(trackers/peers 5s 轮询=可写自动重试;
    #    content 无轮询=只陈述失败, 不得虚构「稍后自动重试」)
    err_expect = {
        "04-trackers-status-cards-tall.js": ("trackersError", "tracker 列表加载失败, 将在下次自动刷新时重试", "暂无 tracker"),
        "05-trackers-health-groups-low.js": ("trackersError", "tracker 列表加载失败, 将在下次自动刷新时重试", "暂无 tracker"),
        "06-trackers-table-collapsed.js": ("trackersError", "tracker 列表加载失败", "暂无 tracker"),
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
            # trackers/peers 组 5s 轮询真实存在(_startDrawerPoll): 可写「下次自动刷新时重试」
            assert "下次自动刷新时重试" in text, \
                f"drawer_tpl/{name}: trackers/peers 组失败文案应带自动刷新重试口径(5s 轮询真实)"


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

    # 2. 三变体接入面: 行容器 tabindex=-1 + 锚点/回焦/移焦走核心单点 + keydown 委托挂宿主
    cases = {
        "10-content-tree-detail-tall.js": ["H.roving(host, \"data-node\"", "ev.target !== row"],
        "11-content-treegrid-batch-low.js": ["H.roving(host, \"data-node\"", "ev.target !== row"],
        "12-content-space-treemap-collapsed.js":
            ["H.roving(mapEl, \"data-blk\"", "H.roving(host, \"data-row\"", "ev.target !== el"],
    }
    for name, hooks in cases.items():
        text = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert 'tabindex="-1"' in text, \
            f"drawer_tpl/{name}: 行/块容器缺 tabindex=-1(roving 基线, 容器混进 Tab 序)"
        assert 'role="button"' not in text, \
            f"drawer_tpl/{name}: 整行加了 role=button(行内已含原生控件, 嵌套交互语义更糟 —— 入池根因段口径)"
        for hook in hooks:
            assert hook in text, f"drawer_tpl/{name}: 缺接入点 {hook}(锚点/接管守卫被摘)"
        assert "H.rowFocusKey(" in text and "H.rowRestore(" in text, \
            f"drawer_tpl/{name}: 重建前记账/重建后回焦不成对(原子换帧打断焦点链, 一次激活就甩回文档头)"
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


def test_drawer_tpl_cross_seed_fold_and_select_width():
    """详情面板折叠态跨种子口径统一 + 变体头选择器宽度守阵(P3-6/P3-7, 报告 26-10-07-0542) ——
    content 组 dt10/11/12 换种子重置块(hash !== ui.lastHash)只许清选中/勾选/筛选, 不得清折叠
    记账(ui.folded/ui.colG; 用户拍板统一为跨种子保持, 以 general 组 dt01/02 口径为准; 记账 key
    是 path 不含 hash, 新种子 path 空间不同则旧条目自然不命中, 同名目录延续上一部折叠选择;
    dt11 勾选集必须继续重置 —— 批量优先级真提交, 旧勾选落到新种子文件上是误操作面); 折叠态与
    种子无关或无折叠的变体(01-09/13-15, 组头 key 是节名/组键/tracker url)不得引入 lastHash
    重置机制; 核心 .dt-select 定宽(现 150px: P3-7 160px 硬上限截断长 label -> 26-10-07
    定宽化 240 -> 26-10-09 用户报框太长收窄 150; 见 test_drawer_tpl_select_fixed_width_tab_independent)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    vdir = os.path.join(shared, "drawer_tpl")

    # 1. P3-6: dt10/11/12 的换种子重置块不再清折叠记账, 且按 path 记账的容器仍在
    fold_accounts = {
        "10-content-tree-detail-tall.js": ("folded", 'data-tgl="${n.path}"'),
        "11-content-treegrid-batch-low.js": ("folded", 'data-tgl="${r.path}"'),
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

    # 4. P3-7: .dt-select 定宽(160px 旧上限不得回潮); 26-10-09 用户报框太长收窄 240->150
    #    (只收窄, 定宽口径不变); 26-10-07 用户报的「切页签选择器宽度变」归新守阵
    #    test_drawer_tpl_select_fixed_width_tab_independent
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    assert "width: 150px" in core, \
        "核心 .dt-select 缺 150px 定宽(26-10-09 用户报选择框太长收窄; 不得回退内容驱动宽)"
    assert "width: 240px" not in core, "核心 .dt-select 仍残留 240px 旧宽(26-10-09 收窄未落地)"
    assert "max-width: 160px" not in core, "核心仍残留 .dt-select 160px 旧上限(P3-7 回潮)"


def test_drawer_tpl_select_fixed_width_tab_independent():
    """详情面板切换器占位宽与页签/选项集解耦守阵(26-10-07 用户报: 切页签时切换模板的元素宽度
    变化导致其它元素跟着变化) —— 病根: 原生 select 的自动最小宽 = 最宽 option 的宽, 而
    dtTplOptions 按当前页签变化, max-width 上限挡不住内容驱动宽, 选择器占位宽随页签变, 同排
    .drawer-title(flex:1 1 auto)跟着让位回弹。修法单点在核心 00-core 注入层(三皮肤共享):
    .dt-select 定宽且不再依赖 max-width(26-10-09 用户报框太长, 定宽值 240 收窄至 150 ——
    只改值, 定宽口径是本守阵的钉子); text-overflow:
    ellipsis 是定宽后长 label 的截断保险丝。"""
    core = open(os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"), encoding="utf-8").read()
    m = re.search(r'"\.drawer \.dt-select \{([^"]*)"', core)
    assert m, "核心 .dt-select 规则形态漂移(守阵正则失配, 同步本守阵)"
    decls = m.group(1)
    assert "width: 150px" in decls, \
        "核心 .dt-select 未定宽 150px(26-10-09 收窄值漂移, 或占位宽回退由最宽 option 决定则切页签即抖)"
    assert "max-width" not in decls, \
        "核心 .dt-select 仍带 max-width(上限不改变内容驱动宽的病根, 26-10-07 用户报回归)"
    assert "text-overflow: ellipsis" in decls, \
        "核心 .dt-select 缺长 label 截断保险丝(定宽后超宽 option 文本无省略号语义)"


def test_drawer_tpl_classic_default():
    """详情面板模板 P-01 初装默认 classic 守阵(plan 26-10-06-0838 S1) —— 有 node 时真跑核心层
    node 电池: 白名单脏值/未注册 id/坏 JSON 一律回落 classic; 注册 fail-fast 四分支; dtHtml 转义
    与 dtRaw 豁免; classic 恒在切换器首位。无 node 静态兜底: app.js initialDrawerTpl 缺核心时
    也必须返回全 classic 映射(不能返回空对象 —— 经典包裹层 v-show 读 drawerTplSel.<tab>, 缺键
    会把经典正文藏掉, 与"零观感差异"验收门冲突)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    for tab in ("general", "trackers", "peers", "content", "traffic"):
        assert f'{tab}: "classic"' in app_js, f"initialDrawerTpl 兜底映射缺 {tab}(核心未载入时经典正文会被藏掉)"
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

window.AQB_DRAWER_TPL_REG.register({ id: "boom", tab: "general", label: "B",
  render() { throw new Error("boom-render"); },
  destroy(h) { h.destroyed = true; } });

/* 主场景: 变体渲染抛错 -> 该页签复位 classic + 落盘 + 摘挂载 + 清宿主 + destroy + 不吞栈 */
const sel = { general: "boom", trackers: "classic", peers: "classic", content: "classic", traffic: "classic" };
const ctx = makeCtx(sel);
const host = makeHost();
const st = { tab: "general", entry: window.AQB_DRAWER_TPL_REG.get("general", "boom"), host: host };
ctx._dtMounted = st;
M._dtRender.call(ctx, st);

ok("渲染抛错后该页签复位 classic(经典层 v-show 接管)", ctx.drawerTplSel.general === "classic");
ok("复位随 dtPersistSel 落盘(autoqb.ui.drawerTpl)",
  (() => { try { return JSON.parse(store["autoqb.ui.drawerTpl"]).general === "classic"; } catch (e) { return false; } })());
ok("其它页签选择不受牵连",
  (() => { try { return JSON.parse(store["autoqb.ui.drawerTpl"]).trackers === "classic"; } catch (e) { return false; } })());
ok("挂载态已摘除(后续 _dtNotify 按 classic 路径续走)", ctx._dtMounted === null);
ok("宿主子树已清空", host.cleared === true && host.children.length === 0);
ok("变体 destroy 已回调(定时器/监听清理不丢)", host.destroyed === true);
ok("console.error 未吞栈且带页签与变体 id",
  errors.length === 1 && errors[0].indexOf("boom") >= 0 && errors[0].indexOf("general") >= 0);

/* 稳态: sel 已 classic(重复回落/经典渲染自身抛错路径不触及本函数, 但要稳) */
errors.length = 0;
delete store["autoqb.ui.drawerTpl"];
const ctx2 = makeCtx({ general: "classic", trackers: "classic", peers: "classic", content: "classic", traffic: "classic" });
M._dtRender.call(ctx2, { tab: "general", entry: st.entry, host: makeHost() });
ok("sel 已 classic 时稳态不重复复位不落盘", ctx2.drawerTplSel.general === "classic" && !("autoqb.ui.drawerTpl" in store));

console.error = realErr;
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed }));
if (failed.length) process.exit(1);
"""


def test_drawer_tpl_render_error_fallback_classic():
    """变体渲染抛错自动回落经典层守阵(P2-1, 报告 26-10-07-0542) —— 旧实现 catch 里只清宿主:
    经典包裹层因 drawerTplSel.<tab> !== 'classic' 仍被 v-show 藏住 + .dt-host:empty 把空宿主
    藏住, 两条退路同时断掉 = 该页签整幅空白。有 node 时真跑 _dtRender 抛错电池钉住回落五件
    (复位 classic + 落盘 / 不牵连其它页签 / 摘挂载态 / 清宿主 + destroy 回调 / console.error
    带页签与变体 id); 无 node 静态兜底: catch 块四要素缺一即红(只清宿主的空白降级不得回潮)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    core = open(os.path.join(shared, "drawer_templates.js"), encoding="utf-8").read()
    m = re.search(r"_dtRender\(st\) \{\n(.*?)\n      \},", core, re.S)
    assert m, "_dtRender 形态漂移(守阵正则失配, 同步本守阵)"
    catch = m.group(1)
    # R2 S1: 主列挂载态经 ownerKey 通道摘除(合并次列同式), 缺省键即主列 —— 语义等价旧直写
    assert 'this[st.ownerKey || "_dtMounted"] = null' in catch, \
        "回落必须摘挂载态(否则后续通知拿旧 st 重渲染已弃变体)"
    assert 'this.drawerTplSel[st.tab] = CLASSIC' in catch and "this.dtPersistSel()" in catch, \
        "回落必须复位该页签 drawerTplSel 并落盘(状态单点仍是 drawerTplSel, classic 插件接管)"
    assert 'st.entry.id' in catch and "console.error" in catch, \
        "回落必须 console.error 且带变体 id(不静默吞栈)"
    assert "st.entry.destroy" in catch and "replaceChildren" in catch, \
        "回落必须按 classic 语义卸载变体(destroy + 清宿主)"
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
    assert 'this.drawer.kind === "traffic"' in ob and "this.qbGroupKey === key" in ob, \
        "openDrawerTraffic 缺同目标幂等短路: 再按 Ctrl+\\ 会把收图+重建+首拉各闪一遍"
    assert ob.index('this.drawer.kind === "traffic"') < ob.index("this._stopDrawerPoll()"), \
        "同目标短路必须在收图/重建副作用之前(落在后面 = 短路失效, 闪烁回归)"

    # 4. watch(drawerVisible): 退场销毁图 / 进场补拉重建(uPlot 宿主随 v-if 拆装被换掉)
    #    种子详情支路的回页重挂(!s 分支 _dtSync)归 test_drawer_seed_reentry_variant_remount
    wt = re.search(r"drawerVisible\(v\) \{\n(.*?)\n    \},", state_js, re.S)
    assert wt, "state.js 缺 watch(drawerVisible)(换宿主后图不自愈 = 回页只剩文字)"
    wb = wt.group(1)
    assert "const s = this.qbCurScope;" in wb and "if (!s) {" in wb, \
        "watcher 缺流量形态作用域分支(种子详情归 !s 支路, 回页重挂见专用守阵)"
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
    poll = re.search(r"_drawerTimer = setInterval\(\(\) => \{(.*?)\n      \}, 5000\);", drawer_js, re.S)
    assert poll and "viewMode" not in poll.group(1), \
        "5s 轮询 tick 不得再挡视图(换视图即停会让这两页的页签数据停在打开那一刻)"
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
    assert 'if (this.drawer.open && this.drawer.kind === "seed") {' in ob, \
        "openTorrentDrawer 缺已开重入分支: 面板开着换种子仍走整体重建 = 空态->加载态->数据三连闪"
    assert ob.index('this.drawer.open && this.drawer.kind === "seed"') < ob.index("this._stopDrawerPoll()"), \
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
        ("shared/drawer_tpl/13-traffic-chart-led-tall.js", ("前端派生自 points/totals", )),
        ("shared/drawer_tpl/14-traffic-annotated-split-low.js", (
            "窗口内上传字节累计",
            "窗口内下载字节累计",
            "上下行字节占比",
        )),
        (
            "shared/drawer_tpl/15-traffic-adaptive-collapsed.js", (
                "当前窗口累计上传",
                "当前窗口累计下载",
                "当前窗口上行峰值",
                "前端派生自 points/totals",
            )
        ),
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
    m = re.search(r"async torrentCmd\(action, body = null, okText = \"\"\)\s*\{(.*?)\n    \},", drawer, re.S)
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
    # busy 行(整行锚定)与 verdict 渲染区(行式明细, 复用 modal-details 范式)
    assert '<p v-if="modal.busy" class="modal-body">正在检查前置条件…</p>' in tpl, \
        "popovers.html 缺预检 busy 行 —— 预检在途无反馈(计划 26-10-05-0314 S4)"
    assert '<div v-if="modal.verdict && modal.verdict.length" class="modal-details">' in tpl, \
        "popovers.html 缺 verdict 三分流渲染区(modal-details 行式范式)"
    assert 'v-for="(d, i) in modal.verdict"' in tpl, "verdict 区缺行式 v-for 渲染"
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
      2. 两套 UI 的批量分支必须**成对存在**且逐项一致(双 UI 是两条独立模板, 只改一边 = 另一边
         用户看不到批量菜单), 且只能调 ctxAct/ctxDelete;
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

    # 2. 两套 UI 的批量分支成对且逐项一致
    branches = {}
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        m = re.search(r'<template v-if="menu\.multi">(.*?)</template>', text, re.S)
        assert m, (
            f"{ui}/index.html 的右键菜单没有 v-if=\"menu.multi\" 批量分支 —— "
            f"多选右键拿不到批量动作(双 UI 必须成对改, 另一套有而它没有 = 半边用户没有该功能)"
        )
        branch = m.group(1)
        # 归一空白后逐项比对: 两套 UI 的批量菜单是同一套语义, 不该各自演化
        branches[ui] = re.sub(r"\s+", " ", branch).strip()
        for call in ("ctxAct('resume')", "ctxAct('pause')", "ctxAct('reannounce')", "ctxAct('recheck')", "ctxDelete()"):
            assert call in branch, f"{ui}/index.html 批量分支缺少 {call}"
        assert "actTorrent(" not in branch and "actEpisode(" not in branch, (
            f"{ui}/index.html 批量分支里出现了单目标/单集动作 —— 批量菜单必须整份走 ctxAct/ctxDelete"
        )
    assert branches["atlas"] == branches["prism"], (
        "两套 UI 的批量右键菜单不一致(星图 vs 棱镜)—— 双 UI 必须成对改; 差异: "
        f"atlas={branches['atlas'][:120]!r} / prism={branches['prism'][:120]!r}"
    )

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
      1. 单组分支必须含六个组级入口(与批量分支同项集; 组菜单独有的 打开文件夹/流量图 除外);
      2. 跳检项必须吃 flags.skip_check_menu 门控(fail-closed, 与单选/批量两处同口径);
      3. 六个入口方法必须在 commands.js/drawer.js 落地且复用多选同一套下游链路
         (recheckGroup->_actCore / 限速移动跳检->drawer.js 多选对话框 / metaGroup->openMetaDialog /
          exportGroup->_exportHashes), 不为组级另开旁路。
    """
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "ctx-menus.html"), encoding="utf-8").read()
    # v-else 精确匹配单组分支(v-else-if 带 -if 后缀, 不会误命中)
    m = re.search(r"<template v-else>(.*?)</template>", tpl, re.S)
    assert m, "ctx-menus.html 找不到单组菜单 v-else 分支(结构被改? 同步本守阵)"
    group = m.group(1)

    # 1. 六个组级入口(与多选批量菜单同项集)
    for token in (
        "recheckGroup()", "skipCheckGroup()", "editLimitsGroup()", "editMoveGroup()", "metaGroup()", "exportGroup()"
    ):
        assert token in group, (f"单组右键菜单缺少 {token} —— 与多选批量菜单项集不一致(2026-10-09 报障: 单组缺选项)")

    # 2. 跳检项 fail-closed 门控(v-if 对 undefined 静默隐藏; 与单选/批量两处同口径)
    assert re.search(r'v-if="flags\.skip_check_menu"[^>]*@click="skipCheckGroup\(\)"',
                     group), ("单组菜单「跳检…」项缺 flags.skip_check_menu 门控 —— 关态仍渲染 = fail-closed 破口")

    # 3. 六个入口方法落地 + 复用多选同一套下游链路
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    drw = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()
    assert "_groupTargets()" in cmd, "commands.js 缺 _groupTargets(组级目标集合单点)"
    assert "this.memberHashesOf(g.members)" in cmd, (
        "commands.js _groupTargets 未走 memberHashesOf 单点(成员对象直接取 .hash 会被静态守阵拦下)"
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
      1. 双 UI 是两条独立模板, 只改一边 = 另一边用户没有入口(两套 UI 必须成对改);
      2. 对话框的投递必须走 bulk 链路(/api/torrents/bulk), 目标集合口径单点在
         _bulkTargets/openMetaDialog —— 自己再拆一遍就会与批量浮条口径漂移;
      3. .opt-pill(atlas 此前没有该组件)与 .meta-dialog 的 CSS 必须两套成对定义,
         模板用到的类在 CSS 无定义 = 静默裸样式(挂件类名错配的变体)。
    """
    # 1. 三套 UI 成对: metaOpen 对话框 + 两处入口(批量菜单 ctxMeta / 单种子菜单)
    #    (2026-10-05 批量控制条退役: 模板层不再直接调 openMetaDialog(null), 批量入口统一走 ctxMeta)
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert 'v-if="metaOpen"' in text, f"{ui}/index.html 缺少标签/分类对话框(三套 UI 必须成对改)"
        assert "openMetaDialog(null)" not in text, (
            f"{ui}/index.html 又出现模板层直接调 openMetaDialog(null) —— 批量控制条已退役, "
            f"批量入口应统一走 ctxMeta(右键批量菜单)"
        )
        assert 'openMetaDialog(menu.hash)' in text, f"{ui}/index.html 单种子右键菜单缺少标签/分类入口"
        assert "ctxMeta()" in text, f"{ui}/index.html 批量右键菜单缺少 ctxMeta 入口"
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
            "prism/css/components.css",
            open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read()
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

    # 1. 三个输入框全部挂 @focusout 收层(漏一个 = 那个下拉点空白不收)
    for input_id in ("ad-save-path", "ad-category", "ad-tags"):
        m = re.search(rf'<input id="{input_id}"(.*?)>', mgr, re.S)
        assert m, f"dialogs-mgr.html 找不到 #{input_id}(添加窗口三下拉的输入框, 改名或挪走了? 同步本守阵)"
        assert '@focusout="addPopBlurClose"' in m.group(1), \
            f"#{input_id} 缺 @focusout=\"addPopBlurClose\"(失焦即收是收层主判据, 漏挂 = 该下拉点窗口其它位置不收)"

    # 2. 失焦收层必须带合帧守卫: 同步收层会被 label 的焦点转回打断(闪烁回潮)
    body = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert body, "add_torrent.js 找不到 addPopBlurClose(失焦收层单点, 改名或挪走了? 同步本守阵)"
    assert "setTimeout" in body.group(1) and "clearTimeout" in body.group(1), \
        "addPopBlurClose 必须用定时器合帧(同步收层 + label 转发回焦 = 关了又开闪烁); 定时窗内焦点回来由开层方法撤销"
    for field in ("addCatMenu", "addTagMenu", "addPathPop"):
        assert f"this.{field} = false" in body.group(1), f"addPopBlurClose 漏收 {field}"

    # 3. 三个开层方法先撤销挂起的收层(焦点回到输入框 = 菜单保持, 不闪)
    for fnname in ("openAddCatMenu", "openAddTagMenu", "openAddPathPop"):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and "_addPopBlurCancel()" in body.group(1), \
            f"{fnname} 必须先 _addPopBlurCancel()(焦点转回输入框时撤销挂起的失焦收层, 否则菜单闪烁)"

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
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()
    dg = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    lf = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    mgr = open(os.path.join(shared, "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()

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

    # 2. 三个 combobox 内嵌清空(x): 行挂 has-clear + 按钮 @mousedown.prevent + 走 clearAddField
    for input_id, kind, field in (
        ("ad-save-path", "path", "addSavePath"), ("ad-category", "cat", "addCategory"), ("ad-tags", "tag", "addTags")
    ):
        i = mgr.index(f'id="{input_id}"')
        seg = mgr[mgr.rindex('class="add-input-row', 0, i):i + 900]
        assert "has-clear" in seg, f"#{input_id} 的输入行缺 has-clear(清空钮靠它让出右内边距)"
        assert 'class="add-pop-clear"' in seg, f"#{input_id} 行内缺 .add-pop-clear 清空按钮"
        assert '@mousedown.prevent' in seg, \
            f"#{input_id} 的清空钮缺 @mousedown.prevent(不拦默认动作会抢焦点 → 下拉被失焦收掉)"
        assert f"clearAddField('{kind}')" in seg, f"#{input_id} 的清空钮没接 clearAddField('{kind}')"
        assert f'v-if="{field}"' in seg, f"#{input_id} 的清空钮没按 {field} 非空才显形"
        btn = re.search(r'<button[^>]*add-pop-clear[\s\S]{0,200}?>', seg)
        assert btn and "@click.stop" in btn.group(0), \
            (f"#{input_id} 的清空钮缺 @click.stop —— 它的 click 会冒泡到 lifecycle 的 window "
             f"收层名单, 点一下 x 顺手把下拉一起收了(真机走查实测: 清空后菜单消失)")
    clear_body = re.search(r"clearAddField\(kind\) \{(.*?)\n    \},", at, re.S)
    assert clear_body, "add_torrent.js 找不到 clearAddField(三个 combobox 的清空单点)"
    for field in ("addSavePath", "addCategory", "addTags"):
        assert f"this.{field} = \"\";" in clear_body.group(1), f"clearAddField 不清空 {field}"

    # 3. 遮罩关窗: mousedown 记臂位 + mouseup.self 才关; 全仓不许再有 @click.self
    masks = 0
    for name in ("dialogs-mgr.html", "dialogs.html", "popovers.html"):
        txt = open(os.path.join(shared, "tpl", name), encoding="utf-8").read()
        for m in re.finditer(r'<div v-if="[^"]*" class="modal-mask[\s\S]{0,240}?>', txt):
            masks += 1
            tag = m.group(0)
            assert '@mousedown="maskDownSelf"' in tag and '@mouseup.self="maskCloseIfArmed(' in tag, \
                (f"{name} 的遮罩没接「mousedown 记臂位 + mouseup.self 才关」: {tag[:80]} —— "
                 f"@click.self 会被『拖选文字终点落在遮罩上抬手』误判成点空白关窗")
        live = re.sub(r"<!--[\s\S]*?-->", "", txt)  # 注释里讲原理不算(只查真接线)
        assert "@click.self" not in live, \
            f"{name} 仍残留 @click.self 遮罩关窗(拖选文字抬手会误关窗)"
    # 2026-10-04: qb-traffic.html 两个模态弹层并入底部详情抽屉(无遮罩) -> 阈值 11 -> 9
    assert masks >= 9, f"只数到 {masks} 处 modal-mask(漏挂? 或守阵正则失配, 复核)"
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
    assert 'if (!this.addOpen && !this.metaOpen) return;' in at, \
        "_fitAddPop 必须同时放行 meta 对话框(两处共用同一套限高, 只认 addOpen 会让 meta 侧恒不生效)"

    # 5. meta 分类下拉补失焦收层 + 进 window click 兜底名单(原本两处都漏 = 点对话框别处下拉不收)
    m = re.search(r'<input id="meta-category"(.*?)>', pv, re.S)
    assert m and '@focusout="metaCatBlurClose"' in m.group(1), \
        "#meta-category 缺 @focusout 收层(点对话框里别的地方下拉悬着不收)"
    blur = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert blur and "setTimeout" in blur.group(1) and "clearTimeout" in blur.group(1), \
        "metaCatBlurClose 必须定时合帧(同步收层会被 label 转发回焦打断 = 闪烁)"
    open_meta = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dg, re.S)
    assert open_meta and "_metaPopBlurCancel()" in open_meta.group(1), \
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
    add_close = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert add_close and '_popBlurShouldHold(["ad-save-path", "ad-category", "ad-tags"])' in add_close.group(1), \
        "addPopBlurClose 收层前没问守卫(三字段的家族 id 名单缺一即该字段守卫失效)"
    meta_close = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert meta_close and '_popBlurShouldHold(["meta-category"])' in meta_close.group(1), \
        "metaCatBlurClose 收层前没问守卫(meta 分类下拉与三下拉同族, 缺位同闪)"


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

    # 2. 两套 UI 的次级菜单: 一级只有一个入口, 复制三项在面板内
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        m = re.search(r'<div class="ctx-item has-sub".*?\n            </div>\n', text, re.S)
        assert m, f"{ui}/index.html 找不到次级菜单父项(改名或挪走了? 同步本守阵)"
        block = m.group(0)
        assert "更多操作" in block, f"{ui} 的次级菜单入口文案不是「更多操作」"
        assert "@mouseleave=\"scheduleSubClose()\"" in block, (
            f"{ui} 次级菜单父项缺 @mouseleave=\"scheduleSubClose()\" —— 鼠标移出后子面板不会消失(CTX-05)"
        )
        assert "@mouseenter=\"keepSub()\"" in block, (
            f"{ui} 子面板缺 @mouseenter=\"keepSub()\" —— 跨过父项与面板之间 4px 缝隙时会被收掉, 鼠标进不去子面板"
        )
        assert block.count("class=\"ctx-sub\""
                          ) == 1, (f"{ui} 一级菜单出现 {block.count('class=\"ctx-sub\"')} 个子面板 —— 只允许「更多操作」一个入口(CTX-06)")
        for kind in ("name", "hash", "magnet"):
            assert f"copyTorrentInfo('{kind}')" in block, (
                f"{ui} 的复制族缺 copyTorrentInfo('{kind}') —— 复制项必须并进「更多操作」(CTX-06)"
            )
        assert "subMenu === 'copy'" not in text, (f"{ui} 仍残留 subMenu === 'copy' 分支 —— 复制已并入「更多操作」, 双入口会回潮(CTX-06)")

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
