# 停靠面板 (drawer-dock)

> 摘要: 底部停靠面板 (sticky 吸底) 与滚动几何 / 轮询生命周期 —— 面板从浮层改停靠后, 一切拿视口当滚动边界的算式都变了; 让位下界收单点后, 键盘与显式打开 (双击/右键/Enter) 各路径都要接; 面板 DOM 随可见性退场 (区分于状态位) 时, 轮询 / canvas 宿主 / Esc 三处都要跟着收口。
> 触发: 停靠面板, drawer-dock, 吸底, sticky, 滚动跟随, 光标行被遮, 看不见当前行, 下界, innerHeight, 轮询, 面板隐藏, 双击被挡, 显式打开, 设置页出现流量图, drawerVisible, 页面守卫, canvas 宿主, uPlot 不自愈, Esc 无反应

### 停靠面板吸底会遮蔽以 `window.innerHeight` 为下界的滚动几何

- **触发**: 把浮层改造成 sticky 吸底停靠面板后, 复用既有的"滚动到可见"算式
  (2026-10-03 抽屉重设计 W4 几何走查实测: 列表底部光标行被面板顶缘压住, 键盘下移到底部时当前行看不见)。
- **判别**: 浮层形态下 `window.innerHeight` 就是列表可视下界, 算式一直是对的 —— 病灶不在算式而在**前提**:
  停靠面板占据文档流后, 可视下界 = 面板顶缘, 不再是视口底。全站 grep `innerHeight` 找同族算式逐处核对,
  别只修撞出来的那一处。
- **处置**: 可见性下界收成**单点方法** (`shortcuts.js` `_kbViewBottom()`: 面板开着返回面板顶缘坐标,
  否则返回视口底), 所有滚动跟随/就近回落算式统一消费该单点 (W4 已落地两处消费点)。
  以后新增任何"元素是否在视口内"判定一律走这个单点, 不许现写 `innerHeight`。
- **复发: 1** —— 2026-10-03 双击列表末尾几行, 面板一开把被点行盖住(用户报障): 显式打开路径
  `openTorrentDrawer` 漏接让位单点。**为什么没命中**: 本条处置只覆盖「新写算式要走单点」,
  没覆盖「既有路径族是否全部接入」—— 键盘路径 W4 走查接上了, 鼠标路径没走查到; 已补
  第三条判别(路径族逐条核对)与守阵 `test_drawer_open_reveal_row`。

### 停靠面板隐藏后激活期轮询要随可见性收口

- **触发**: 浮层时代的轮询挂在"抽屉开着"这个状态上; 停靠化后面板随视图 `v-if` 隐藏
  (切到站点/设置页, 或种子视图整个不在 DOM), 状态位还开着 ⇒ 5s 轮询对着不存在的面板继续发请求。
- **判别**: 状态位 (`drawer.open`) 与面板**实际在 DOM 里**是两回事 —— 切页不触发 closeDrawer, 状态不会自己翻。
  Network 面板里切页后仍见 drawer 详情请求周期性出现即中招。
- **处置**: 轮询 tick 前加**可见性守卫**: 面板节点不在 DOM (或种子视图非当前视图) 即停止本轮并注销定时器,
  回到种子视图重新唤起时再起轮询 (W4 已收口)。判断"该不该继续轮询"永远以 DOM 可见性为准, 不以状态位为准。
- **复发: 1** —— 2026-10-06, 同一条在 qB 口径流量图上重现: 2026-10-04 三挂点并入抽屉时
  `drawerVisible` 对流量形态无条件为真("任意页可开"), `_QB_SCOPES.global/group.active` 也随之省了
  页面守卫 ⇒ 切到设置页后面板仍挂在页面底部 (用户报「qB 全局流量图错误地出现在设置页」), 隐藏期
  `/api/traffic/qb/global` 也照拉。**为什么没命中**: 本条处置写的是"面板隐藏后收口", 而真正该先问的
  一句是"**先别让面板显示在不属于它的页**" —— 前者治症状, 后者治入口。据此补三条同族纪律:
  ① `drawerVisible` 是**唯一可见性单点**, 两形态一律先挡 `page !== "groups"`(守卫写在形态分支**之前**,
     按形态各写一遍 = 又一处会漏的分叉);
  ② 每挂点轮询/建图的 `active` 必须与 `drawerVisible` **同宽**(少一处 page 判据就是隐藏期的幽灵请求);
     入口若不限页(状态栏 / 全局快捷键), 打开方法必须先切回主内容页 —— 否则面板不在 DOM = "点了没反应";
  ③ 退场/进场在同一处接管, 见下一条(canvas 宿主)与 Esc 连带 — 面板可见性一改, 这三处是同一原子的三面。

### 显式打开路径 (双击/右键/Enter) 同样要让位 —— 单点收口不等于路径都接上

- **触发**: 2026-10-03 用户报障: 鼠标双击列表最后几个种子看详情, 面板一开恰好把被点行盖住。
  W4 的下界单点 `_kbViewBottom()` 只被键盘跟随消费; 显式打开 `openTorrentDrawer` 是浮层时代
  遗留路径 (浮层不占文档流, 从不需要让位), 停靠化时漏接。
- **判别**: 「算式收成单点」只治"别再写错", 不治"还有路径没接" —— 症状即「某条路径打开时被点
  行被面板顶缘压住, 换键盘路径却正常」, 路径相关 = 有路径没接。收口后 grep 单点方法名逐条核对
  消费者, 凡「面板开合/收起/拖高改变列表可视范围」的交互都要按路径族 (键盘 / 双击 / 右键 /
  Enter / Alt+数字) 走一遍, 不能只修撞出来的那一条。
- **处置**: 显式打开挂上面板状态后调 `shortcuts.js::_kbRevealRow(hash)` —— 内部 $nextTick 等
  面板挂载再量 (面板 DOM 随 open 状态 v-if, 同帧量不到), 目标行下缘低于 `_kbViewBottom() - 4`
  才 scrollBy, 本来可见不动, 行不在 DOM(窗口化折叠)静默放弃 —— 滚动位置宁可不动也不猜(P1-2 退避口径)。
- **守阵**: `tests/test_web_shortcuts.py::test_drawer_open_reveal_row` —— openTorrentDrawer 必须调
  _kbRevealRow, 让位必须 nextTick + _kbViewBottom 单点, 禁 scrollIntoView 与 innerHeight, 行不在
  DOM 必须静默放弃。
- **复发: 1** —— 2026-10-04 用户再报同一症状(「已修但回归」)。为什么没命中: 修复的让位调用确实
  在, 但**量测时机与滚动时机都错**(见下一条: 量的是 loading 态几何 + 文档底 scrollBy 被钳制),
  守阵只断言「调用了让位」, 探不到这类「调用存在但几何/时机错」的缺陷 —— 静态守阵全绿而真机必红。

### 让位量测必须读「落定几何」, 文档底打开时下滚余量是槽位长高才创造的

- **触发**: 2026-10-04 用户报「双击查看最后几个种子被抽屉挡住(已修但回归)」。
  26-10-03 的让位在 openTorrentDrawer 挂状态后 nextTick 量一次就收工, 但那一刻: ①面板还在
  loading 空态(≈百来px), 详情几十 ms 后到手、面板长到 42vh 顶格 —— 量到的顶缘(实量与动画期
  登记的 _drawerAnimTop 起拍值同病)是 loading 态快照; ②用户在文档底, `scrollBy(+Δ)` 被浏览器
  钳制成 0 —— 下滚余量是停靠槽位(.drawer-dock 流内元素)长高才创造的, 而槽位长高发生在让位之后。
  真浏览器逐帧取证: scrollY 全程一字不动。键盘跟随不踩这两个坑(面板早已长好、余量已存在),
  症状即「键盘正常、双击被盖」。
- **判别**: 静态守阵全绿 + 真机必红 —— 必须走 ui_harness + 真浏览器探针(双击末行 → 等落定 →
  量行底缘 vs 面板顶缘)。修复前取证值: animTop=616(loading 登记) vs 落定顶缘 488; scrollBy
  y1==y0(被 max 钳死)。
- **处置**: 三发让位, 各治一层, 全走 `_kbRevealRow` 单点(只在被点行被盖时 scrollBy, 不抢滚轮):
  ①追赶循环**逐帧重登记**落定顶缘(`dock 底缘 - 面板自然高`; sticky 吸底期底缘恒定, 面板自身
  布局高不受槽位裁剪)——修量测; ②开场按 FX-29 待到集合登记数据源(detail + 初值页签; 流量页签
  定高不进集合), 全到手在 `_drawerDone` 兑现挂单 `_drawerOpenReveal`(open/hash 双守卫防迟到
  误发)——修「页签数据中途长高」; ③`drawerAfterEnterHook` 槽位落定后补发——修「文档底钳制」
  (槽位长高后余量足额; 流量形态无种子行不发)。
- **守阵**: `test_drawer_open_reveal_row`(三发挂点 + 挂单守卫) +
  `test_drawer_transition_dock_anim`(逐帧重登记)。

### 落点从视图内上提到 app 级: 内边距要补回, 失效的父容器 flex 规则要删

- **触发**: 2026-10-04 把 qB 口径流量图三挂点并入底部抽屉, `.drawer-dock` 自 `tpl/torrents.html`
  上提到 app 级分片 `tpl/dock.html`(面板要任意页可开, 见 activeContext 26-10-04-0405)。
- **判别**: 落点原先在 `.layout` / `.ce-page` 内部, 面板宽度靠**父容器的水平内边距**收边(两页都是 12px);
  上提到 `#app` 直下后父容器没了 ⇒ 面板变全宽贴边。sticky 吸底本身不受影响(仍以文档滚动容器为准),
  但 `.torrents-dock > .drawer-dock { flex: 0 0 auto }` 这类"面板是父容器 flex 子项"的规则**静默失效**
  (不再有匹配节点), 留着就是骗后来人。
- **处置**: `.drawer-dock` 自己补 `padding: 0 12px`(三皮肤成对改, 值与原父容器内边距对齐);
  删掉随落点一起失效的父容器子项规则; 落点分片只放一个 `.drawer-dock`(boot.js `findSlot` 只认**第一个**
  匹配 —— 摆两个等于第二个永远空着)。面板可见性改由 `drawer.js::drawerVisible` 按形态把守, 替代原先
  "DOM 随视图 v-if 出入"的隐式门。
- **2026-10-06 修正**: 这里一度写成"流量图全局(任意页)可见", 是把**入口可达性**当成了**面板可见性** ——
  落点上提到 app 级解决的是"任意页都能触发", 不等于"面板该在任意页显示": 面板是吸底元素, 在设置页
  压住页面底部内容, 看着像设置页自带的一块。现口径 = 两形态都限 `page === "groups"` + 状态位不随切页翻
  (见上一条, 回主内容页连数据和窗口选择一起回来)。

### 面板 v-if 退场会换掉 canvas 宿主, uPlot 不自愈; Esc 名单要跟着改用可见性

- **触发**: 2026-10-06 给面板加页面守卫后派生出来的两条 —— 面板 DOM 由 `drawerVisible` 的 `v-if` 拆装,
  Vue 拆了再装时**装回来的宿主是新节点**: uPlot 的 root/canvas 挂在被拆走的旧 `.qb-chart-host` 上, 既不可见
  也不自愈(下一次 `setData` 快路还会以为"图还活着", 而要到下一次轮询落袋才重画 —— 间隔可能夹到 600s),
  症状是「回主内容页后面板里有文字没图」; 同时 `drawer.open` 还留在 Esc 名单(`escBusy` + lifecycle
  退栈链)里, 看不见的面板会把设置页那次 Esc 吃掉(用户按一次 Esc 毫无反应)。
- **判别**: 凡「画布 / ResizeObserver / 第三方实例挂在模板节点上」的组件, **宿主身份**是它的生命周期边界 ——
  不能用"数据还在 / 状态位还开着"代替"实例还活着"; Esc 名单同理, 判据必须与屏幕上能看见的东西同名。
- **处置**: ① 在 `state.js` 加 `watch(drawerVisible)`: 退场 `_qbChartDestroy(scope)`(连 ResizeObserver 一起断),
  进场 `_qbReloadOnEnter(scope)` 补拉一发(`_qbLoad` 内含 `$nextTick` 建图), 并对在途 `loading` 让路
  (打开路径本就先发一发, 否则首次打开的请求翻倍); ② Esc 两处名单改判 `drawerVisible`。
- **守阵**: `tests/test_webui_static_dom_panel.py::test_frontend_qb_traffic_drawer_page_guard`(可见性单点 / 三挂点 active 同宽 /
  入口页面归一 / watcher 退场销毁 + 进场补拉)。

### 列表变短 = 文档变矮: sticky 吸底脱锚, 面板跟着内容末尾走

- **触发**: `.drawer-dock` 是流内 sticky 吸底元素, 「钉在视口底」只在**自然落点低于视口下界**时生效
  —— 列表被搜索/筛选筛短(或真 0 命中落空态)后文档变矮, 面板脱锚上浮到内容末尾; 列表长短一变,
  钉住/脱锚两态之间切换就是用户看到的"面板跳动"。视口越高跳幅越大(800px 视口 14px, 线性放大)。
- **判别**: 采样面板 `getBoundingClientRect().top` 贯穿整个交互: 搜索/筛选前后 top 变了 = 脱锚
  (内容列高度问题); top 恒定但背景列表跳 = 滚动钳制(结果确实变短, 属预期)。注意「调用存在但
  几何/时机错」静态守阵探不到, 必须真浏览器逐帧采样(dock-panel 2026-10-04 回归同教训)。
- **处置**: 让内容列(`.layout`)恒撑满首屏: `min-height: calc(100vh - var(--head-h))`(顶栏实测高
  走 `columns.js::_syncHeadHeight` 既有单点, **不写死** —— 顶栏随媒体查询/状态条/窄屏折行变高)。
  内容列恒撑满则面板自然落点恒在视口底, sticky 恒生效, 锚点与列表长短无关。三皮肤成对改
  (atlas/console 的 components.css + prism 的 views.css)。
- **守阵**: `test_webui_static_skins.py::test_frontend_search_pending_no_collapse`(三皮肤 .layout min-height 锚)+
  `e2e/drawer-dock-stability.spec.mjs`(行为: 搜索全程面板 top 偏差 ≤2px)。配套根因(待响应期
  塌列表)见 search-pending-collapse。
- **取证(2026-10-07)**: 修复前短列表态面板 top 416 vs 钉住态 430; 修复后三皮肤逐帧采样零变化。

**Refs:** memory-bank/tasks/26-10-07-webui-drawer-search-jump.md

### flex 纵列里"撑满可用高"必须配确定高度, 否则图塌到 min-height

- **触发**: 2026-10-04 让流量图高度跟随抽屉高度(`.drawer-body.is-traffic { display:flex; flex-direction:column }`
  + `.qb-chart { flex:1 }` + `.qb-chart-host { height:100% }`)。
- **判别**: flex 的 `flex:1` 只在容器高度**确定**时才有解。抽屉默认是内容自适应(只有 CSS `max-height: 42vh`),
  高度由内容撑出来 —— 此时"图撑满余量"是循环定义, 实测图会塌到 `min-height`。
- **处置**: 流量形态由 `drawer.js::drawerPanelStyle()` 给**确定高度**(`drawerHeightPx` 有值就用它,
  没有则回落 42vh = 与 CSS 默认上限同值), 高度因此也与种子详情**共用同一 drawerHeightPx**;
  建图侧 `_qbChartBuild` 量 `host.clientHeight` 当图高, ResizeObserver 宽高**双观察**才能跟着拖拽实时长。
- **守阵**: `tests/test_webui_static_dom_panel.py::test_frontend_qb_traffic_chart_wiring`(三皮肤 `.drawer-body.is-traffic`
  撑满段成对 + RO 宽高双观察) + `test_web_shortcuts.py::test_drawer_height_collapse_w3`(面板高度单点)。
