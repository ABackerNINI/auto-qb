# WEBUI fx 皮肤 S1a 桌面调研笔记(原料,未成文)

> 归属计划: `memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html` (S1 桌面调研步)
> 性质: 调研原始笔记,喂给下一代理成报告/进 showcase 用。纯 CSS + 原生 JS 约束下的可借鉴模式提炼。
> 调研日: 2026-10-31。来源: MD3 motion 官方 token 页、Apple HIG Motion、GSAP Eases 文档、easings.net、OpenProps `src/easing.css` 源码、animate.css 官网、motion.dev 快速上手、chrome.dev View Transitions/scroll-driven 文档、uiverse.io/prismic 等 demo 集。

---

## A. easing 曲线库

### A1. Material Design 3 token 体系(系统级锚点)

来源: https://m3.material.io/styles/motion/easing-and-duration/tokens-specs (页面为 Angular SPA,数值经搜索摘要核对)

| token | cubic-bezier | 适用 |
|---|---|---|
| `emphasized` | (0.2, 0.0, 0.0, 1.0) | 大型/表达性过渡的默认,带轻微慢起快收 + 急收尾,是 M3 的"签名曲线" |
| `emphasized-accelerate` | (0.3, 0.0, 0.8, 0.15) | **退场**专用,元素离开屏幕 |
| `emphasized-decelerate` | (0.05, 0.7, 0.1, 1.0) | **入场**专用,元素进入屏幕,快起缓收 |
| `standard` | (0.2, 0.0, 0.0, 1.0) | 小型功能过渡(与 emphasized 同值,语义区分用) |
| `standard-accelerate` | (0.3, 0.0, 1.0, 1.0) | 小型元素退场 |
| `standard-decelerate` | (0.0, 0.0, 0.0, 1.0) | 小型元素入场 |
| `linear` | (0.0, 0.0, 1.0, 1.0) | 进度/倒计时类,不用于空间移动 |

M2 遗留曲线(大量现成 CSS 抄的是这套,识别用): `standard` (0.4, 0, 0.2, 1) 即浏览器 `ease-in-out` 加强版;`decelerate` (0, 0, 0, 1) 即 `ease-out` 终极版;`accelerate` (0.3, 0, 1, 1)。

### A2. easings.net 家族(带精确 cubic-bezier,零依赖直接可用)

来源: https://easings.net/ (数值为该项目 canonical 值)

| 家族 | out 变体 | in 变体 | inOut 变体 | 视觉性格 |
|---|---|---|---|---|
| sine | (0.61, 1, 0.88, 1) | (0.12, 0, 0.39, 0) | (0.37, 0, 0.63, 1) | 最柔,适合缓慢/循环 |
| quad (=GSAP power1) | (0.5, 1, 0.89, 1) | (0.11, 0, 0.5, 0) | (0.45, 0, 0.55, 1) | 温和通用 |
| cubic (=power2) | (0.33, 1, 0.68, 1) | (0.32, 0, 0.67, 0) | (0.65, 0, 0.35, 1) | UI 过渡主力 |
| quart (=power3) | (0.25, 1, 0.5, 1) | (0.5, 0, 0.75, 0) | (0.76, 0, 0.24, 1) | 干脆利落 |
| quint (=power4) | (0.22, 1, 0.36, 1) | (0.64, 0, 0.78, 0) | (0.83, 0, 0.17, 1) | 冲刺感,大位移入场 |
| expo | (0.16, 1, 0.3, 1) | (0.7, 0, 0.84, 0) | (0.87, 0, 0.13, 1) | 极快起/急收,戏剧性 |
| circ | (0, 0.55, 0.45, 1) | (0.55, 0, 1, 0.45) | (0.85, 0, 0.15, 1) | 类 power 但中段更陡 |
| back | (0.34, 1.56, 0.64, 1) | (0.36, 0, 0.66, -0.56) | (0.68, -0.6, 0.32, 1.6) | 过冲回弹,弹性强调 |
| elastic / bounce | 不可用 cubic-bezier 表达 | 同 | 同 | 必须 `@keyframes` 或 CSS `linear()` |

### A3. GSAP 体系(映射到 bezier 与场景)

来源: https://gsap.com/docs/v3/Eases/

- 家族 = power1-4/sine/expo/circ/back/elastic/bounce/steps × in/out/inOut;GSAP 默认 ease 是 `power1.out`。
- UI 场景推荐: `power1.out`/`power2.out` = 最安全反馈/过渡;`back.out` = pop-in、按钮点击回弹;`elastic.out` = 通知/玩趣场景(慎用,弹跳多轮容易腻);`steps()` = 像素/CRT 风格(retro preset 预留)。
- `slow`(SlowMo: 慢-快-慢)、`rough`(抖动)在 EasePack,core 没有;对应需求用 bezier/linear() 近似。
- 结论: GSAP 的价值是"家族 × 方向 × 场景"命名法,而非曲线本身——曲线 A2 已全覆盖。

### A4. OpenProps 令牌设计(现成的零依赖 token 层,高度可抄结构)

来源: https://github.com/argyleink/open-props (src/easing.css, unpkg.com/open-props@latest/easing.css)

- 分级 1-5(不是 1-4/1-6): 越大越陡。`--ease-1..5`(对称), `--ease-in-1..5`, `--ease-out-1..5`, `--ease-in-out-1..5`。样例:
  - `--ease-out-2: cubic-bezier(0, 0, .50, 1)`、`--ease-out-3: cubic-bezier(0, 0, .3, 1)`、`--ease-out-5: cubic-bezier(0, 0, 0, 1)`
  - `--ease-in-out-2: cubic-bezier(.3, 0, .7, 1)`、`--ease-in-out-5: cubic-bezier(.9, 0, .1, 1)`
- **overshoot 家族用 cubic-bezier 可表达**: `--ease-elastic-1..5 = (.5, .75/1/1.25/1.5/1.75, .75, 1.25)` —— y2=1.25 过冲强度分 5 档,这就是纯 CSS 弹性。
- **spring / bounce 用 CSS `linear()` 函数**(cubic-bezier 表达不了的物理曲线): `--ease-spring-1..5`、`--ease-bounce-1..5` 全是超长 `linear(0, 0.006, 0.025 2.8%, ...)` 采样点列表。Chrome 113+ 支持——**正好命中 D5 "Chrome/Edge 全特性、其余降级"**: Firefox/Safari 声明整条作废,降级写法 = 先写 bezier 再写 linear() 覆盖。
- 设计启示: fx 库 token 分层照抄"家族 × 强度档位"结构,强度档位直接当 preset(neon 用大档/glass 用中档/crisp 用小档)是天然映射。

### A5. fx 库建议收敛集(候选,下一步成文时可裁)

| fx token | 建议值 | 场景 |
|---|---|---|
| `--fx-ease-out` | (0.2, 0, 0, 1) | 入场/浮现(M3 emphasized 兼容 most cases) |
| `--fx-ease-in` | (0.3, 0, 0.8, 0.15) | 退场 |
| `--fx-ease-standard` | (0.33, 1, 0.68, 1) | 小过渡/颜色/阴影 |
| `--fx-ease-snap` | (0.16, 1, 0.3, 1) | 快而狠的强调入场 |
| `--fx-ease-back` | (0.34, 1.56, 0.64, 1) | 过冲 pop |
| `--fx-ease-elastic` | (0.5, 1.25, 0.75, 1.25) | 强过冲(neon 档) |
| `--fx-ease-linear` | linear | 进度/扫过 |
| `--fx-ease-spring` | OpenProps `--ease-spring-3` 的 linear() 值 | Chrome 弹簧,带 bezier 降级 |

---

## B. 时长/距离分级表

### B1. 三方规范对照

| 语义 | MD3 token/建议 | Apple HIG | demo 集/社区常用 | fx 建议档 |
|---|---|---|---|---|
| hover 反馈 | short1-2 (50-100ms) | 极短,"brief and precise" | 100-200ms | **80-100ms** |
| 按下/active | short1 (50ms) | — | 50-100ms | **50-80ms** |
| 小元素过渡(开关/checkbox) | short4 (200ms) | — | 150-250ms | **120-200ms** |
| 入场(卡片/面板) | medium (250-450ms), emphasized-decelerate | 0.2-0.5s 总区间 | 250-350ms | **200-300ms**(项目上限 400ms) |
| 退场 | **比入场短**, emphasized-accelerate, ~150-250ms | — | 150-250ms | **150-200ms** |
| 弹窗/抽屉 | medium 长端 300-450ms 入 / 200ms 出 | — | 300ms/200ms | **300ms 入 / 200ms 出** |
| 页签切换 | short4-medium (200-300ms) | — | 200-250ms | **200-250ms** |
| 强调(pop/pulse) | — | — | 300-600ms | **300-500ms** |
| 全屏/大位移 | long 500-1000ms | — | — | 本项目基本用不到(P0 无全屏过渡) |
| toast 入场/退场 | — | — | 250ms/150-200ms | **250ms / 180ms**(展示时长与动画时长解耦) |

来源: MD3 tokens-specs + 搜索摘要(https://m3.material.io/styles/motion/easing-and-duration/tokens-specs);Apple HIG Motion 全文(https://developer.apple.com/design/human-interface-guidelines/motion.md);animate.css 速度档(`faster 500ms / fast 800ms / 默认 1s / slow 2s / slower 3s`——**UI 组件库不应照抄 animate.css 的秒级时长,那是展示动画规模**);motion.dev stagger 例 0.1s。

### B2. 距离/位移建议

- 小反馈位移(hover 抬升): 1-2px;入场位移: 8-16px(元素级)/ 24-100%(抽屉全宽);弹窗 scale: 0.96-1(≤4% 差,过大显廉价)。
- M3 "距离越长时长越长"原则: 位移每翻倍,时长约 ×1.3-1.5。
- Apple HIG 额外原则(见 C 节): 频繁交互的 UI 不加动效、动效应可被取消(不必等动画播完才能继续操作)——对 torrent 表格行和按钮这类高频交互,时长档取各档**下限**。

---

## C. 值得借鉴的编排模式清单

### C1. stagger(sequential transition,MD2 choreography)

- 适用边界: **卡片/弹窗内部区块**、toast 队列、抽屉内段落这类"少量(≤8 个)表面"的顺序浮现;每项 delay 步进 20-50ms(不是逐项串行),同 duration 同 easing 级联。
- **明确不适用: torrent 高密度表格行**(项目硬约束)。列表刷新的替代: 整表一次 cross-fade 或 View Transitions root 默认交叉淡化,不做行级 stagger。
- 来源: https://m2.material.io/design/motion/choreography.html (sequential/symmetric/radial reaction);motion.dev `stagger(0.1)` 工具形态(https://motion.dev/docs/quick-start)。

### C2. enter/exit 非对称编排

- M3 系统性结论: **入场 decelerate + 时长长,退场 accelerate + 时长短**(dialog 400ms 入 / 200ms 出是官方例)。退场快是因为用户已经拿到结果,退场只需"干净消失"。
- fx 库应把这对(曲线+时长)作为一个"编排骨对"成对定义,而不是两条独立 token。
- 来源: https://m3.material.io/styles/motion/easing-and-duration/tokens-specs 及 applying-easing-and-duration(官方例: emphasized-decelerate 入 / emphasized-accelerate 出)。

### C3. View Transitions API(零依赖库里最"免费"的编排工具)

- 同文档用法: `document.startViewTransition(() => updateDOM())` + 共享元素打 `view-transition-name`;浏览器自动做旧/新快照交叉过渡与 FLIP 位移。`if (document.startViewTransition)` 一行探测,Firefox/Safari 天然走无动效终态——与 D5 完美对齐。
- 适合: **页签切换**(old/new 内容交叉淡化+自定义曲线)、**弹窗共享元素放大**(按钮→dialog)、**列表过滤/排序的行位移**(row 移动自动 FLIP)、**抽屉开合**。
- 成本/风险: transition 期间整页被快照伪元素盖住,动效 250-400ms 内 UI 不响应指针——必须短;`::view-transition-old/new()` 可用 CSS 换曲线;大量行打 `view-transition-name` 有内存成本(torrent 表只在选中的行上打)。
- 来源: https://developer.chrome.com/docs/web-platform/view-transitions ;https://css-tricks.com/spice-up-user-interactions-with-same-document-view-transitions/ ;MDN https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API 。

### C4. CSS scroll-driven animations

- `animation-timeline: scroll()/view()` 把动画进度绑到滚动位置,纯 CSS 无 JS。适合: 侧栏阅读进度、列表视口边缘渐隐遮罩、P1 的长列表视差。P0 七组组件里基本没有刚需——登记为 P1 工具,不为 P0 强加。
- 来源: https://developer.chrome.com/docs/css-ui/scroll-driven-animations/ ;https://scroll-driven-animations.style/ ;MDN animation-timeline。

### C5. @starting-style + discrete transition(Chrome 117+,纯 CSS enter/exit 的另一半拼图)

- `dialog[open]`、`.toast` 这类从 `display:none` 出现的元素,`@starting-style` 提供初始态,`transition-behavior: allow-discrete` 让 display 参与过渡——**零 JS 的弹窗/toast 入退场**,退场靠关闭前加 class + `transitionend` 兜底或 View Transitions。Firefox/Safari 下作废=无动效终态,符合降级哲学。
- 来源: https://developer.chrome.com/docs/css-ui/transitions-after-display-changes(同类模式);MDN @starting-style。

### C6. animate.css 命名法(变体命名参考,非曲线参考)

- 结构: `animate__` 前缀 + 基类 `animated` + 家族 × 方向 × In/Out × 强度(`Big`)/角方向(`TopLeft`);工具类时长(delay/repeat/speed)用 CSS 变量(`--animate-duration`)可覆盖——**与 fx 两层变体模型同构**: `data-fx-variant` 对应家族+强度,`data-fx-preset` 对应 duration 全局变量。
- 可抄: 方向词表(up/down/left/right/topLeft/…)、强度分级(Big)、"attention seekers" 家族名(pulse/headShake/tada/jello——toast/danger tone 可用)。
- 来源: https://animate.style/ 。

### C7. Apple HIG motion 语义(设计哲学输入)

- 三语义: **反馈**(跟手势、简短精准)、**引导/状态传达**、**过渡**。高频交互的 UI 避免加动效;动效应可取消;移动大对象用 fade 替代长距离滑动;不要用动效作为传达关键信息的唯一途径(reduced-motion 不只是降级,是可访问性要求)。
- 对 fx 的落点: 挂载器(fx.js)设计"重触发即跳终态"语义(动画未播完用户再点击→直接落到终态,不排队);toast 错误类信息必须有非动效冗余(声音/颜色/文本)。
- 来源: https://developer.apple.com/design/human-interface-guidelines/motion (全文已读,`.md` 端点可直取 markdown)。

---

## D. 每组件候选动效清单(核心,喂 showcase)

> 标注约定: 属性 = 合成器友好(transform/opacity/filter)或 layout(警示);JS = 纯 CSS 还是要 fx.js 配合;RM = prefers-reduced-motion 降级。时长均 ≤ 项目上限(hover ≤100ms,入场 ≤400ms)。

### D1. 按钮 `.bt` 一族(primary/ghost/danger/danger-solid/icon/sm)

1. **lift(抬升+阴影分层)** — hover `translateY(-1~2px)` + box-shadow 双层投影,active `translateY(0)`;transform 合成器友好;80-100ms `--fx-ease-standard`;纯 CSS;RM: 去 transform 与阴影,只留颜色。来源: sliderrevolution《55 Best CSS Button Hover Effects》(https://www.sliderrevolution.com/resources/css-button-hover-effects)。
2. **glow(辉光)** — hover `box-shadow: 0 0 Npx color-mix(in srgb, accent 45%, transparent)` 渐亮;box-shadow 为 paint 层但按钮面积小可接受;100-150ms;纯 CSS;RM: 保持常亮或只留边框变色。来源: uiverse.io 按钮集(prismic 汇编 https://prismic.io/blog/css-hover-effects)。
3. **sheen(高光扫过)** — `::after` 斜切高光条 `transform: translateX(-100%)→100%`,hover 触发一次 animation 400-500ms,需 `overflow:hidden`;transform 合成器友好;hover 首帧即有响应(高光 100ms 内进入可视区);纯 CSS;RM: 去动画。来源: uiverse.io Shiny Button(https://uiverse.io/KirbGaming/ancient-quail-89)。
4. **ripple(波纹,JS 配合)** — pointerdown 注入 span,`scale(0)→scale(2.5)` + opacity 衰减 350-400ms emphasized-decelerate;transform 合成器友好;需 fx.js(创建/清理节点、限制同按钮并发数);RM: 不注入,直接落 active 终态。来源: M2 choreography "radial reaction"(https://m2.material.io/design/motion/choreography.html)。
5. **press-scale(按压回弹)** — active `scale(0.96)`,松开回 1 时可用 `--fx-ease-back` 过冲;transform;50-80ms 触发/150ms 回弹;纯 CSS;RM: 去 scale。来源: GSAP `back.out` 场景(https://gsap.com/docs/v3/Eases/)。
6. **icon 变体附加** — 图标按钮 hover 图标 `scale(1.1)` 或 rotate ±8°,active 过冲回摆;transform;80-120ms;纯 CSS;RM: 无动效。来源: Apple HIG "animated symbols" 思路(HIG Motion)。

### D2. 弹窗 modal(含 tone 分级)

1. **fade+rise+scale(标准入场)** — backdrop opacity 0→1 200ms;面板 `opacity 0→1` + `translateY(12px) scale(0.96)→1` 300ms `--fx-ease-out`(emphasized-decelerate);transform/opacity 合成器友好;Chrome 纯 CSS(`@starting-style`)或 fx.js 加 class;RM: 全部去动效直接显示。来源: M3 dialog 模式(enter ~400ms emphasized-decelerate 官方例;此处压到 300ms)。
2. **退场对(编排骨对)** — 关闭时面板 opacity→0 + `translateY(6px) scale(0.98)` 180ms `--fx-ease-in`,backdrop 同步 fade;需 fx.js 等 `transitionend` 再 `dialog.close()`(或 View Transitions 包一层);RM: 立即关闭。来源: M3 退场 accelerate 模式(tokens-specs)。
3. **zoom-out(反差入场)** — 面板从 `scale(1.08)` 收缩落位(iOS 式 overlay 质感),250ms `--fx-ease-standard`;transform;纯 CSS;RM: 终态。来源: Apple HIG "transitions" 语义 + macOS sheet 惯例。
4. **backdrop blur 渐入** — `backdrop-filter: blur(0→8px) + brightness 0.6` 200ms;filter 合成器友好但大面积,showcase 标注实测帧率;纯 CSS;RM: 直接终态模糊。来源: M3 scrim + glass 惯例(uiverse/CodePen 常见配方)。
5. **danger tone 附加** — danger 弹窗打开时面板一次 headShake 微幅横摆(x ±4px,3 次衰减)300-400ms,或红色 glow 一次脉冲;transform/box-shadow;keyframes;纯 CSS;RM: 去动效留静态红边。来源: animate.css "attention seekers" 家族(headShake)(https://animate.style/)。
6. **View Transitions 共享元素(可选高配)** — 触发按钮打 `view-transition-name`,`startViewTransition` 包 showModal,按钮→弹窗自动缩放飞行 250-300ms;需 fx.js 一行探测;RM/不支持: 普通打开。来源: chrome.dev view-transitions(https://developer.chrome.com/docs/web-platform/view-transitions)。

### D3. 抽屉(共壳 12 变体,方向参数化: 四方向 × 语义)

1. **slide+fade(主候选)** — 面板 `translateX/Y(±100%)→0` + opacity 300ms emphasized-decelerate 入 / `±100%` 200ms accelerate 出;transform 合成器友好;纯 CSS(data-fx 挂 class)或 `@starting-style`;RM: 无动效直接开合。来源: M3 applying-transitions(entrances/exit 模式)。
2. **shadow-ahead(阴影先行)** — 移动中面板投影从无到 `-20px 0 40px rgba(...)` 渐强,落位后收缩为常规阴影;box-shadow paint 层,面积中等;与 slide 同步 300ms;纯 CSS;RM: 常规静态阴影。来源: M3 "elevation 提示空间关系"模式(choreography)。
3. **backdrop 渐暗+blur** — 遮罩 rgba 0→0.5 + 可选 blur 4px,250ms 与面板同步;opacity/filter;纯 CSS;RM: 静态半透明遮罩。来源: uiverse 弹层配方 + M3 scrim。
4. **push-content(内容让位)** — 主容器 `translateX(±drawer宽)` 300ms(与面板同曲线同曲线族,decouple 为对称 in-out),transform 方案避免动 width(layout 警示: 若必须真推挤布局,用 width 并标注 layout);transform 合成器友好;需 fx.js 或 CSS 变量同步宽度;RM: 直接切换。来源: M2 choreography "transform" 模式。
5. **spring-slip(弹簧滑入,Chrome 高配)** — 入场改 `--fx-ease-spring`(linear() 函数)300-400ms,过冲 3-5px 再回落;transform;纯 CSS(bezier 降级链: 先写 `cubic-bezier(0.34,1.3,0.64,1)` 再写 linear() 覆盖);RM: bezier 版或终态。来源: OpenProps `--ease-spring-*`(https://github.com/argyleink/open-props)。
6. **parallax-layer(视差微配)** — 遮罩层位移/透明度变化滞后面板 50-80ms(编排延迟),层次感;opacity;纯 CSS(第二动画 delay);RM: 同步。来源: M2 choreography sequential 原则。

### D4. 列表行 torrent 表格行(选中/锚点/光标三态;高密度,禁全行 stagger)

1. **cursor-hover 扫光** — hover 行 `background-color` + `outline-color` 过渡 60-80ms(高频交互取下限,Apple HIG);color 为 paint 但行区域小、并行行少;纯 CSS;RM: 保留 hover 底色(非动效信息,不降级)。来源: Apple HIG "frequent interactions avoid motion" + 常规表格惯例。
2. **selected 边条生长** — 行首 `::before` 竖条 `transform: scaleY(0)→1` 120ms `--fx-ease-standard` + 背景着色;transform 合成器友好;纯 CSS;RM: 无动画直接着色。来源: M3 navigation drawer active indicator 模式。
3. **anchor 锚点脉冲** — 定位行 background 一次 flash 脉冲 keyframes(600ms,2 次淡出)+ `scrollIntoView({behavior:'smooth'})`;keyframes 是 background paint(单行,可接受),滚动为合成;需 fx.js 触发 scrollIntoView + 加一次性 class;RM: `behavior:'auto'` 瞬时定位 + 去脉冲(保留静态高亮)。来源: 浏览器 find-in-page 高亮惯例 + animate.css flash 家族。
4. **row-insert 新行浮现** — 刷新插入的新行 `opacity 0→1 + translateY(-4px)` 150ms,**单行独立、无 stagger**;transform/opacity;纯 CSS(插入时 class)或 View Transitions(行 group 交叉过渡);RM: 无动效。来源: 本计划约束(禁 stagger)+ M3 medium 短端。
5. **row-remove 行退场** — 内容 opacity→0 + `scaleY(0.95)`/max-height 收拢二选一(max-height 版标注 **layout** 警示;纯 transform 版有下方行瞬跳问题,showcase 对照给出);150-200ms accelerate;JS 需监听结束再真删;RM: 立即删除。来源: animate.css fadeOut 家族 + M3 退场模式。
6. **checkbox 快勾** — 行内勾选框 `scale(0.6)→1` 过冲 120ms + 打勾 stroke-dashoffset 划线(SVG);transform 合成器友好;纯 CSS;RM: 直切。来源: animate.css bounceIn 微缩版(uiverse checkbox demo 常见)。

### D5. 输入框 focus 态

1. **下划线生长** — 底边 `::after scaleX(0)→1`,`transform-origin: left`,100-150ms;transform 合成器友好;纯 CSS(`:focus-within`);RM: focus 时直接显示静态下划线。来源: M2/M3 text field active indicator(https://m2.material.io/components/text-fields)。
2. **ring 辉光圈** — focus `box-shadow: 0 0 0 3px color-mix(accent 30%)` 100ms 展开;box-shadow paint 小面积;纯 CSS;RM: 保留静态 ring(焦点可见性是可访问性必需,不降级)。来源: Tailwind/uiverse focus ring 惯例。
3. **floating label(浮标签)** — label `translateY + scale(0.75)` 150ms 上浮;transform;纯 CSS(`:placeholder-shown` 技巧)或 fx.js;RM: 直接切换位置。来源: M3 filled text field 官方交互。
4. **底色微亮** — focus 时 `background-color` 从 input 底色过渡到 `color-mix(accent 6%)` 120ms;color paint 小面积;纯 CSS;RM: 保留。来源: uiverse 输入框集(https://uiverse.io/elements)。
5. **shake-invalid(校验失败微震)** — blur 校验失败时 `translateX` ±3px 摆动 3 次 300ms + 边框转 danger 色;transform;需 fx.js 判定或 `:user-invalid` 伪类(Chrome 119+ 支持差,实测后定);RM: 只变色不震动。来源: Apple HIG 反馈语义 + animate.css headShake。

### D6. toast / 通知

1. **slide+fade 入退场对** — 从顶部/底部边缘 `translateY(∓16px)+opacity 0→1` 250ms `--fx-ease-out` 入,反向 180ms `--fx-ease-in` 出;transform/opacity;入场纯 CSS(`@starting-style`),退场 fx.js 加 class 后 `transitionend` 移除;RM: 直接显示/移除。来源: M3 snackbar 模式 + animate.css fadeInUp/Down 命名。
2. **倒计时进度条** — 底缘细条 `transform: scaleX(1→0)` linear、时长=展示时长(由 fx.js 把秒数写进 CSS 变量,与自动关闭同一状态源,幂等);transform 合成器友好;需 fx.js;RM: 静态无进度条(信息冗余: 文本仍在)。来源: M3 snackbar 计时惯例(uiverse toast 常见配方)。
3. **队列重排 FLIP** — 新 toast 推入时旧 toast 用 View Transitions 或手写 FLIP(fx.js 记录 old rect→transform 反演→过渡回位)200ms;transform;需 fx.js;RM: 瞬时重排。来源: chrome.dev view-transitions(元素重排场景)+ FLIP 惯例(https://aerotwist.com/blog/flip-your-animations/)。
4. **icon spring 弹入** — tone 图标 `scale(0.5)→1` 用 `--fx-ease-spring` 300ms(Chrome linear(),bezier 降级);transform;纯 CSS;RM: 直切。来源: OpenProps spring 家族。
5. **danger glow 边缘脉冲** — error toast 出现时边框一次 glow 脉冲 keyframes 400ms(仅一次,不循环);box-shadow paint 小面积;纯 CSS;RM: 静态红边。来源: animate.css attention seekers(flash 一次化改造)。

### D7. 页签切换(groups/torrents/shows/settings)

1. **指示器滑移(animate indicator)** — 活动页签下条 `transform: translateX()+scaleX()` 从旧位滑到新位 200-250ms `--fx-ease-out`;transform 合成器友好;需 fx.js 量旧/新 rect(或用 View Transitions 让浏览器做 FLIP);RM: 瞬移。来源: M2/M3 tabs "animated indicator"(https://m2.material.io/components/tabs)。
2. **内容 cross-fade** — 旧面板 opacity→0 100ms,新面板 0→1 150ms(总 ≤250ms);opacity;纯 CSS(切换 class)或 View Transitions 默认交叉淡化;RM: 直切。来源: M3 transitions + chrome.dev view-transitions 默认行为。
3. **View Transitions 全接管(推荐主候选)** — `startViewTransition(() => swapTab())`,old/new 面板伪元素自定义 keyframes(emphasized 曲线),指示器元素打共享 `view-transition-name` 自动 FLIP;250-300ms;需 fx.js 一行探测;RM/不支持: 直切。来源: chrome.dev view-transitions + css-tricks 同文档实践(https://css-tricks.com/spice-up-user-interactions-with-same-document-view-transitions/)。
4. **方向感知滑动** — fx.js 判断目标页签相对位置,`data-fx-dir="left|right"` 决定新内容 `translateX(±12px)` 入场方向(轻位移+fade,不做全宽 slide),200ms;transform;需 fx.js 判方向;RM: fade 或直切。来源: M2 choreography 空间关系原则(iOS segmented 惯例)。
5. **页签文本+指示器同编队** — 活动文本 `scale(1.02)` 微强调与指示器滑移同曲线同起点(对称编排),120ms;transform;纯 CSS(配合 1);RM: 无。来源: M2 choreography "symmetric transition"。

---

## 附: 对 fx 库设计有直接影响的结构性结论

1. 入/退非对称"骨对"应作为一等公民: 入场 decelerate + 长(200-300ms),退场 accelerate + 短(150-200ms),成对定义不成对独立调参。
2. OpenProps 的 `linear()` spring/bounce 家族让零依赖库拥有纯 CSS 物理弹性(Chrome 113+),降级链 = cubic-bezier 近似在前、linear() 覆盖在后,契合 D5。
3. View Transitions + `@starting-style` 两个 Chrome 特性覆盖了"编排"与"display:none 进出场"两大原需 JS 的场景,fx.js 可瘦身为: 挂载器 + 重触发跳终态 + 少量 rect 测量。
4. stagger 适用边界以 MD2 choreography 为准: 少量表面级联 OK,高密度行禁(项目已有硬约束,与规范一致,showcase 可放心标注)。
5. Apple HIG 补的维度是"语义与礼仪": 高频交互不加动效、动效可取消、关键信息非动效冗余——建议进 fx 库 README 段与 showcase 标注体系。
