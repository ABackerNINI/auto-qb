# 主表横条隐藏与底部横滚指示条: 几何链、隐藏口径与三处静默故障

> 摘要: 藏掉 `.group-table` 原生横条并补底部指示条时, 五件事不显然 —— ①**横条的位置是容器底边, 不是视口底边**: `.layout { align-items: start }` 让 `.content` 不被拉伸, `.torrents-dock` 虽是 flex column、`.group-table` 虽是 `flex: 1 1 auto`, 但**没有自由空间可占** ⇒ 容器高度 = 内容高度, 容器底边 = 最后一行下方。少种子时底边落在视口上半部(用户报「滚动条横在屏幕中间」), 种子多时底边在整页最底部(要滚到列表末尾才看得见, 实际不是可用控件)—— 这条推导正是「彻底隐藏」而非「条件隐藏 / 撑高容器推走」的根据: 撑高会动 `_winViewH` 行窗口化 / 吸底面板 / 吸顶表头共同依赖的高度链路; ②**隐藏要两条声明, 缺一即红**: `scrollbar-width: none`(Firefox) + `.group-table::-webkit-scrollbar { display: none }`(Chromium/WebKit) —— 三皮肤全局都有 `*::-webkit-scrollbar { height: 10px }`, Chromium 系「画不画」由**元素级**规则决定, `*` 规则挡不住, 只写 `scrollbar-width` 对 Chromium 无效; 元素级规则的特异性 (0,1,1) 压过 (0,0,1), 不依赖书写顺序; 单点在 `shared/hscroll.css`, 三皮肤 `index.html` 各一条 link 且排在各自 `views.css` **之后**, 皮肤自有 CSS 内**不得**出现第二份隐藏声明(副本 = 日后各自漂移); ③**替代物是挂 `body` 末尾的单例胶囊**, 召唤范围是**两个维度都要写闭区间**的带: 纵向 `[状态栏上缘 - 24px, 状态栏上缘)`(**不含状态栏** —— 初版只写下界, 状态栏那 34px 也命中)、横向只认**胶囊邻域**(胶囊宽 + 左右各 40px, 初版只判 `clientY` ⇒ 全屏宽都能召唤), 另有第二条路径 Shift+滚轮 / 触控板双指横滚亮出后停手 1.5s 自落; 150ms 淡入 / 200ms 淡出, 热区路径无停留定时器, `z-index: 25` 夹在吸顶表头 5 与状态栏 30 之间; ④**监听不能挂在惰性建 DOM 的路径上**: 初版把文档级 `mousemove` 绑进 `_hscrollPill()`, 而它只由 `_hscrollSync()` 调、`_hscrollSync()` 只由容器 `scroll` 调 ⇒ 从没横滚过的用户永远等不到胶囊 —— 而「纯鼠标用户没有拖拽入口」恰恰是本方案要补的洞, 这类人正是最需要指示条的人; 改由 `_ensureHeadObserver` 第一行调用(挂载即绑, 自带 `bound` 守卫), 且热区进入时**重新解析**当前主表容器(旧容器已 detach, `scrollWidth` 归零会把「有溢出」误判为假); ⑤**headless Chromium 的 overlay 滚动条让「量条槽高度」类断言变成安慰剂**: 原生条可见时 `offsetHeight - clientHeight` 同样是 0, 该断言在 CI 上永远不会红; 真正的非空过证据是计算样式 `getComputedStyle(el, "::-webkit-scrollbar").display === "none"` 且 `scrollbar-width === "none"`。
> 等级: L0
> 触发: 横向滚动条, 横条, 滚动条在中间, 少种子横条, 横条很丑, group-table, overflow-x, scrollbar-width, ::-webkit-scrollbar, 滚动条隐藏, hscroll, 指示条, 胶囊, 热区, 热区退化成半平面, 拖拽横滚, 拖不动, 指示条不出现, 惰性建 DOM, 监听没挂上, 挂载即绑, overlay 滚动条, 条槽高度, offsetHeight clientHeight, 安慰剂断言, 抽屉横条, 状态栏高度, statusbar-h, 状态栏也触发, 全屏宽触发, 横向范围太宽, shift滚轮, Shift+滚轮横滚, 触控板横滚, 滚轮时显示, 胶囊太小, 指示条尺寸
**Refs:** memory-bank/plans/26-11-01-0553-plan-webui-hscroll-indicator.html, memory-bank/testing/baselines/26-11-01-0638-webui-hscroll-indicator.md

### 主表横条隐藏 + 底部指示条: 五处非显然约束

- **触发**: 给 `.group-table`(种子 / 辅种 / 追剧三主表)藏掉原生横向滚动条, 并在底部补一根可拖的紧凑指示条。
- **判别**: 症状分在四个面 —— 横条「横在屏幕中部」(几何链, 见 ①); 藏了却仍有条或换浏览器复现(口径不全, 见 ②);
  纯鼠标用户永远看不到指示条(监听挂错位置, 见 ④); 本地断言绿、真环境却证明不了任何事(overlay 滚动条, 见 ⑤)。
- **处置**:
  - **① 先算清横条画在哪 —— 它画在容器底边, 而容器底边不在视口底边**。`.group-table` 是
    `overflow-x: auto` 的滚动容器, 原生横条贴着**它自己**的底边。`.torrents-dock` 是 flex column,
    `.group-table` 声明了 `flex: 1 1 auto`, 看似会撑满 —— 但 `.layout { align-items: start }` 让
    `.content` 不被拉伸, 父链上没有确定高度, `flex-grow` **没有自由空间可占** ⇒ 容器高度 = 内容高度,
    底边 = 最后一行下方。后果是双面的: 少种子时底边落在视口上半部(本次报障形态 —— 一条横线横在
    屏幕中部); 种子多到撑出整页时底边在整页最底部, 要滚到列表末尾才看得见, 作为控件等于不存在。
    **这条推导就是「彻底隐藏」的根据**: 想「撑高容器把条推到视口底部」会动
    `_winViewH` 行窗口化 / 吸底面板 / 吸顶表头共同依赖的高度链路 —— 为一个滚动条改三处几何的地基,
    收益与风险不成比例; 条件隐藏则两头都不满足(少种子时照样难看, 多时照样够不着)。
  - **② 隐藏要两条声明, 缺一条就在某个引擎上留条**。`scrollbar-width: none`(Firefox 标准属性) +
    `.group-table::-webkit-scrollbar { display: none }`(Chromium / WebKit 伪元素), 两条都必须写。
    原因: 三皮肤全局都有 `*::-webkit-scrollbar { width: 10px; height: 10px }`(prism `css/base.css` /
    atlas `style.css` / console `style.css`), Chromium 系「画不画」由**元素级**规则决定, 通配符那条
    挡不住; 反过来只写 `scrollbar-width` 对 Chromium 完全无效。**元素级规则不依赖书写顺序**:
    `.group-table::-webkit-scrollbar` 特异性 (0,1,1) 压过 `*::-webkit-scrollbar` (0,0,1), 本文件排在
    皮肤文件之后只是双保险, 不是唯一依据。
    单点在 `shared/hscroll.css`, 三皮肤 `index.html` 各挂一条 link, 位置在各皮肤 `views.css` **之后**
    (shell 里 link 序即级联序)。选择器只写 `.group-table` ⇒ **覆盖所有** `.group-table`, 含抽屉变体面
    (它们同样只有横向滚动、原生条同样难看); 页面竖条 / 状态栏 / 抽屉体天然不受影响。皮肤自有 CSS 里
    **不得**出现第二份隐藏声明 —— 副本 = 日后各自漂移, 静态守阵反向钉住这条。
  - **③ 替代物的契约(指示条)**: DOM 为 `.hscroll-pill`(轨道)内嵌一个 `<i>`(滑块), 挂 `body` 末尾的
    单例; `.on` = 可见, `.drag` = 拖拽中(与 hover 同观感)。几何: 居中 `left: 50%` +
    `translateX(-50%)`、宽 `min(300px, 48vw)`、`bottom: calc(var(--statusbar-h) + 8px)`、静息 5px /
    hover·drag 7px、`z-index: 25`(低于状态栏 30、高于吸顶表头 5)。滑块宽
    `max(32px, 轨道宽 × clientWidth / scrollWidth)`、位移按 `scrollLeft / (scrollWidth - clientWidth)`
    映射到 `(轨道宽 - 滑块宽)` —— 轨道宽要**实测**(`pill.clientWidth`), 不硬编码(窄屏 `48vw` 会把它压小)。
  - **③b 召唤范围是两个维度的**带, 不是半平面 —— 这里出过两个真 bug(2026-11-01 用户验收当场指出):
    - **纵向要上下界**: 带 = `[状态栏上缘 - 24px, 状态栏上缘)`, **不含状态栏本身**。初版只写下界
      `clientY >= innerHeight - 状态栏高 - 24`, 少了上界 ⇒ 状态栏那 34px 全落在带内; 而状态栏是
      **常用控件区**(铃铛/速度/限速/跳检), 指针扫过去就召唤滚动条是纯噪声。
    - **横向要限邻域**: 只认胶囊本身的范围(胶囊宽 + 左右各 40px), 不是全屏宽。初版只判 `clientY`
      ⇒ 鼠标在底部右侧的速度/限速区也能召唤。判据用**缓存**的 `pillW`(在 `_hscrollSync` 里量一次),
      热路径上不读布局 —— 否则每次 `mousemove` 都强制一次 layout。
    - 通用教训: 「热区 = 一条边 + 距离」的写法极易退化成半平面。凡是"某块区域的邻域", 两个维度都要
      写出闭区间, 并且**给每条边界配一条负例断言**(指针落在带外时不该亮), 否则退化后没有任何测试会红。
  - **③c 第二条召唤路径: Shift+滚轮 / 触控板双指横滚**(2026-11-01 用户追加)。这类用户不会把指针
    伸到内容区底缘, 但横滚时同样缺位置反馈。判据 = 指针落在**那张主表上**(`el.contains(ev.target)`,
    走节点关系不读布局) 且 有横向意图(`ev.shiftKey` 或 `|deltaX| > |deltaY|`); 亮出后**停手 1.5s 自落**。
    这是本方案**唯一**的时间驱动逻辑 —— 热区路径仍不加停留定时器(那条 D5 的取舍不变), 两者不要混。
    另: 拖动 `pointerup` 之后横向**不要**再判胶囊邻域(刚拖完手可能停在轨道两端之外, 一松手就消失
    显得突兀), 交给下一次 `mousemove` 按正常判据收。
  - **④ 陷阱一: 监听不能挂在惰性建 DOM 的路径上**。初版把文档级 `mousemove` 绑在 `_hscrollPill()`
    (惰性建 DOM)里, 而它只由 `_hscrollSync()` 调用、`_hscrollSync()` 只由容器 `scroll` 事件调用 ⇒
    **从没横滚过的用户永远等不到胶囊**: 不横滚 → 不建 DOM → 不挂监听 → 永远不建。而「纯鼠标用户
    没有拖拽入口」恰恰是本方案要补的那个洞, 这类用户正是最需要指示条的人(本轮真踩到并返工)。
    处置: 监听改由 `_ensureHeadObserver()` **第一行**调用(挂载即绑, 自带 `bound` 守卫, 重复调用零成本),
    与「是否滚过」彻底解耦; 热区进入那一刻用 `$refs.groupTable/torrentTable/showTable` **重新解析**
    当前主表容器, **不复用**缓存引用 —— 视图切换后旧容器已 detach, `scrollWidth` 归零会让
    「有溢出」误判为假(同源 bug, 一并修掉)。守阵双向钉住: `_ensureHeadObserver` 体内必须调
    `_hscrollBind()`, 且 `_hscrollPill()` 体内**不得**调。
  - **⑤ 陷阱二: headless Chromium 的 overlay 滚动条让几何断言变成安慰剂**。本仓库 headless
    Chromium 用 overlay 滚动条: 原生条**可见**时 `offsetHeight - clientHeight` 同样是 0。所以
    「无条槽 = `offsetHeight - clientHeight === 0`」这条断言在 CI 上**永远不会红**, 换成 classic
    滚动条环境才有效(e2e 阶段实测)。真正的非空过证据是**计算样式**:
    `getComputedStyle(el, "::-webkit-scrollbar").display === "none"` 且 `scrollbar-width === "none"` ——
    它证明隐藏规则真的命中该元素、该皮肤真的链到了 `hscroll.css`, 这是静态守阵证明不了的。
    教训: 凡「量条槽高度」类断言, 先确认环境用的是 classic 还是 overlay 滚动条, 否则是安慰剂。
- **守阵**: `tests/test_webui_static_skins.py::test_frontend_hscroll_indicator_wiring`(规则单点 / 三皮肤挂载级联 /
  接线锚点三族静默故障) · `e2e/hscroll-indicator.spec.mjs`(条槽 / 可滚 / 热区 / 拖动 / 宽窗五面)。
- **复发**: 0

### 抽屉变体面也走 `syncHeadScroll`, 指示条必须按页白名单挡掉

- **触发**: 给主表加「滚动即更新指示条」的尾部调用后, 抽屉里的变体表也跟着跑了。
- **判别**: `shared/tpl/xtpl.html:360` **也调** `syncHeadScroll`(传的是抽屉表 id)。若指示条判定只写
  「有溢出就建」, 抽屉每滚一次就在 `body` 里留一个永不使用的胶囊。
- **处置**: 判定必须留在**建 DOM 之前**, 且按 `page ∈ {group, torrent, show}` 白名单挡掉其余
  (抽屉列集窄、横滚罕见, 不配指示条; 且抽屉可多实例同屏, 单例胶囊语义不成立)。
  顺序反了就是「先建后判」, 节点已落地。

### 状态栏高度不写死 34

- **触发**: 指示条 `bottom` 与热区判定都要知道状态栏多高。
- **判别**: 状态栏可能整块不渲染(某些布局档), 也可能在窄屏折行变高 —— 写死 34 会让指示条压线或悬空,
  热区也跟着错位。
- **处置**: 三级回落 —— 先量 `.statusbar` 实测 `getBoundingClientRect().height`, 量不到读
  `--statusbar-h` 令牌, 再回落 34。两处(`bottom` 与热区)读同一来源; 值缓存, `window resize` 时清缓存重算。
