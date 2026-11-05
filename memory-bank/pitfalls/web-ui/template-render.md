# 渲染 / 静态资源 / 两套 UI

> 摘要: 模板与 CSS 的静默失效(挂件类名错配、规则被吞、变体被覆盖、注入落点找不到)与"两套 UI 必须成对改"的纪律; 另收 Vue 过渡钩子的接线与几何登记、详情面板变体的通知驱动渲染。
> 等级: L0
> 触发: 改模板, 改 CSS, 加挂件类, 改主题, 两套 UI, 白屏, 静默失效, 缓存, 过渡, 过渡动画, 过渡钩子, transition, before-enter, 组件变体, 删死代码, 死类判定, 混合选择器, 动态类名, 删模板连带清 CSS, boot.js, 注入落点, manifest into, 停靠面板, 变体, _dtNotify, 详情面板, 跳过重建, sig, skipUnchanged, 倒计时, next_announce, 时间基准, dtHtml, dtRaw, R(), 模板转义, 裸标签, 标签透出, offnote, 类名撞名, 容器类, 行修饰, hb-ro, 只读行变窄, 文字自动换行, max-width 接管, 折叠头, 可折叠段头, aria-expanded, aria-hidden, getByRole, aq-fold, aq-switch, aq-seg, 分段钮, 小控件, ctl-bits

### 变体渲染是通知驱动的: 状态翻转后必须补一发 _dtNotify, 否则停在旧态到下一拍轮询

- **触发**: 改 drawer.js 列表 fetcher(trackers/files/peers)或任何被详情面板变体
  (dt01~dt12)消费的响应式状态(2026-10-07 实测: 用户页空列表停"正在加载…"好几秒才翻到
  空态)。
- **判别**: 变体不是 Vue 组件 —— **只在收到 `_dtNotify` 时重渲染**(`_dtSync` 挂载时
  渲染一发, 之后全靠通知)。fetcher 原写法把 `_dtNotify` 放 try 块(数据落袋处), 而
  `xxLoading = false` 在 finally —— 通知那一刻 loading 还挂着, 空列表变体渲染出"正在
  加载…", 随后 loading 清掉但**没有通知** ⇒ 停在旧态, 要等下一拍 5s 轮询的下一发通知才
  翻到空态。经典包裹层走 Vue 响应式无此窗口, 所以只在变体皮肤下复现; 后端接口毫秒级,
  与网络无关。非空列表同样中招的场景: 状态只翻转、数据不变的分支(错误清 toast 后的
  loading 复位)。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### sig 跳过重建会把「随时间变化」的派生值冻帧: 时间基准必须计入 sig

- **触发**: 给走 `H.skipUnchanged`(sig 比对跳过重建)的变体加一个**随真实时间变化**的显示值
  (2026-10-09 实测: 06 变体逐行汇报倒计时从种子级相对秒 `detail.reannounce_in` 升级为行级
  `next_announce`(epoch 绝对秒)减 now, issue 26-10-07-0149)。
- **判别**: 跳过重建的判据是**数据派生 sig** —— 旧口径 `reannounce_in` 是**相对秒**(每轮询都变),
  天然进 sig ⇒ 每拍重建; 新口径 `next_announce` 是**绝对 epoch**(一个 announce 周期内恒定),
  数据未变时 sig 不变 ⇒ `skipUnchanged` 命中, **倒计时冻在上一帧**, 直到下次 announce 改了 epoch
  才跳一次。表上表现为"倒计时不走/隔很久才动", 无任何报错。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### Vue <transition> 接 JS 钩子做布局动画: 钩位/几何登记/迟到的 after 钩子三处静默坑

- **触发**: 给占文档流的元素(停靠面板/折叠区)加出入场动画, 想连布局高度一起平滑(只动
  transform/opacity 治不了布局一帧跳变), 用 Vue `<transition>` 的 JS 钩子驱动高度插值。
- **判别**: 三个坑都无报错: ①钩位写成 `@before-enter` —— 同帧元素尚未插入 DOM,
  `el.parentElement` 为 null, 整段动画静默失效(必须 `@enter`); ②动画期元素的几何量测
  (滚动跟随/让位/下界类)读到的是插值中间值 —— 必须把"落定几何"登记进单点变量供消费方优先读,
  动画结束/被打断/悬空(元素已卸载)都要清零; ③快速开关往返时, 被打断那拍的 `after-enter`/
  `after-leave` 钩子**照常点火** —— 迟到的清场会把新拍的动画循环/内联样式杀掉, after 钩子必须
  按当前状态位(如 `drawer.open`)自弃。另: 重开打断收场时, 被打断面板身上的内联高要**清掉**
  (压成 0 会把下一拍的自然高量成 0, 整段动画失效)。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

- 挂件类名错配 ⇒ 整页静默废掉: 详见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 静态资源不加 `Cache-Control` 会被浏览器启发式缓存

- **触发**: 升级前端后"界面改了但没变"。
- **判别**: `StaticFiles` **只给 ETag** ⇒ 浏览器启发式缓存旧前端, 并**误导排查**。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 自建冒烟桩缺 `/api/config/public` 会被登录遮罩挡死

- **触发**: 自建桩挂静态 UI 做浏览器冒烟, 页面只渲染「请输入 WEB 访问密钥」, 主界面 DOM 完全不渲染。
- **判别**: boot 先读 `/api/config/public`, 响应里 `web.skip_local_verify` 非 true 就走密钥表单分支 ——
  纯静态桩不带这个端点 ⇒ 遮罩永不放行(`authRequired` 初值 true, 唯一放行点在验证成功/免鉴权标志)。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 前端表达式错误只有浏览器能发现

- **触发**: 改任何前端渲染逻辑。
- **判别**: 后端字段 / 接口全对、pytest 全绿而**页面崩**是常态。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 未闭合的 `<transition>` 会静默吞掉其后所有弹窗

- **触发**: 加弹窗 / 改过渡。
- **判别**: `<Transition>` 只渲染**第一个**子节点, 其余全部被丢弃 —— 点击毫无反应、**控制台零报错**、
  DOM 里**连元素都没有**。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### CSS 规则漏 `; }`(或选择器头被吞)会让其后规则整段被丢弃

- **触发**: CSS 改了没生效。
- **判别**: 全文件花括号可能**仍配平** ⇒ 数括号查不出来。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 组件变体用 CSS 变量承载时, 后写的直接属性会让变体静默失效

- **触发**: 主题里同时写变量与属性。
- **判别**: `.btn{background:var(--btn-bg)}` + 主题里又写 `.btn{background:#000}` ⇒ 变量声明变**死代码**。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 两套 UI(星图 atlas / 棱镜 prism)必须**成对改**

- **触发**: 改状态色 / 令牌族 / 修饰符类。
- **判别**: 同一个状态开关(`v-if="xxxOpen"`)在模板里出现**两次以上**基本可断定是遗漏的旧实现(实测"点一次开两窗")。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### "CSS 已入库但模板从未切换"的两不管缺口

- **触发**: 迁移 / 重放模板提交时。
- **判别**: 静态 class 覆盖检查必须**双向**做 —— "模板用到但 CSS 未定义"**与**"CSS 定义了但模板从不使用"。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

- 删死模板要连带清它独占的 CSS —— 但"死类"判定不能只看带前缀的类名: 详见 [attachments/template-render-details.md](attachments/template-render-details.md)

### `cfgFlatten` 的 `group_of` 分组判定不能递归复用

- **触发**: 改设置页配置扁平化 / 分组。
- **判别**: 子卡内字段**已归属父字段**, 再参与分组会把它们收进 children 而 **roots 为空** ⇒
  子卡渲染成**空壳且不报错**。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### boot.js 的 manifest `"into"` 落点在嵌套 template content 内时, querySelector 够不到

- **触发**: 给 tpl-manifest 条目换注入落点(2026-10-03 抽屉重设计: drawer 从 `"into": "app"` 改指种子视图模板内部的
  `.drawer-dock`) —— 落点容器写在某个 `<template>` 的 content 里, 外层模板本身又是 boot.js 先注入的。
- **判别**: 顶层 `root.querySelector(sel)` 查不到报"落点找不到"是显性的; 更隐蔽的是
  `querySelectorAll("template")` **不会下钻** `template.content` 片段, 而模板存在浏览器解析出的**嵌套**
  (template 套 template), 只展开一层照样漏 —— 症状是"落点偶发找不到", 取决于哪个嵌套分支被走到。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 变体模板里把 T 标签模板的结果「裸插值」会被全量转义 —— 整段标签当纯文本透出

- **触发**: 在详情面板变体(dt01~dt12)里给模板加条件子块(2026-10-10 用户报「种子详情面板出现
  `<span class="dt05-offnote">虚拟条目由 qBittorrent 合成, 不参与汇报</span>` 原文, 健康分组模板常显」)。
- **判别**: `dtHtml`(变体模板的 `T`)对**所有**插值一律 `esc()` —— 只有 `dtRaw`(即 `R()`)包过的才豁免。
  把内层 `` T`<span...>` `` 的结果**直接当插值**塞进外层模板, 内层已产出的标签会被再转义一次 ⇒ 页面上
  原样显示 `<span class="dt05-offnote">...</span>` 原文; 该元素独占的 CSS(`.dt05-offnote{...}`)**也从未命中**
  (无报错, 纯静默)。数组形态同理 —— `dtHtml` 对数组逐元素 `esc`。文件内既有约定一律 `` R(T`...`) ``,
  漏包的那处就是特例。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 同一个类名既当「容器」又当「行修饰」时, 容器的 max-width 会静默接管行宽

- **触发**: 给只读状态行加样式, 或在 `.hb-*` 家族里复用短类名(2026-10-19 用户报「WEBUI 流量与限速
  设置中工具状态页排版不正确, 文字自动换行」)。
- **判别**: `.hb-ro` 当时有两个含义 —— readonly 列表/对象摘要**容器**
  (`display:flex;flex-direction:column;max-width:460px`)与只读状态**行修饰**(`.hb-row.hb-ro`)。同名时
  两条规则都命中行元素: `display` 由后写的 `.hb-row{display:grid}` 赢(同权重、后出现), 但
  `max-width:460px` **无人重置** ⇒ 整行被压到 460px, 值列只剩 206px(178 标签 + 12 gap + 24 的 `?` 列),
  一条「端口 · PID · 版本 · 数据目录」被折成四行、右侧留一大片空白。静态读模板读不出来(模板里只是
  `class="hb-row hb-ro"`, 完全合理); 真浏览器量一次就现形: 行宽 460 vs 块宽 994。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)

### 折叠头「整栏可点」时, 里层钮要 aria-hidden —— 但 e2e 的 getByRole 也随之看不见它

- **触发**: 给可折叠段头统一可访问性(issue 26-10-20-2231 把 5 处 `hb-sub-toggle` 收进 `<aq-fold>`)。
  收口前每处自己写 role/tabindex/keyup.enter, 且多数把 `aria-expanded` 挂在**里层那个小钮**上 ——
  而实际整条段头都能点, 读屏用户会以为只有小钮能展开; 更糟的是内钮留在 tab 链里, Tab 到它按
  Enter 时「内钮 click」与「段头冒泡的 toggle」各打一次, 净效果是按了没反应。
- **判别**: 正确形态 = **段头** `role=button + tabindex=0 + aria-expanded`, 里层「收起/展开」钮降级为
  鼠标用户的重复入口(`aria-hidden="true" tabindex="-1"`)。代价是 Playwright 的 `getByRole('button')`
  默认**跳过 aria-hidden 子树** ⇒ `headingLocator.getByRole('button').click()` 从「点里层钮」变成
  「等 30s 超时」, 报错只说 locator 等不到, 看上去像渲染没出来(2026-10-21 实测: 两条 B4 用例红)。
- **处置**: 详细步骤与实测证据见 [attachments/template-render-details.md](attachments/template-render-details.md)
