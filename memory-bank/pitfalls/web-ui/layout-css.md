# 样式 / 布局 / 表格

> 摘要: 行宽口径、表头吸顶、两表逐栏对齐、sticky 层叠、flex 挤压、flex 子项错行、特异性之争、状态色分不出 —— 前端版式类的固定判据。
> 触发: 改 CSS, 布局, 表格, 滚动条, 表头吸顶, sticky, flex, flex-basis, 对齐, 未对齐, 没对齐, 错行, 文字高低不一, 后者更高, 统计栏, 工具条, 图例, align-items, stretch, 垂直居中, 基线, align-items baseline, 省略号, 媒体查询, 颜色不对, 按钮, 控件变形过高, 控件尺寸, 两态分不出, 状态色, 徽章底色, 底色相近, 同亮度, 顶栏, 标题栏, 状态栏, 表头, 列标题行, thead, 底色与其余部分难区分, 同色, 明度差不足, chrome 底色, UA 默认色, 两表对齐, 逐栏对齐, 列宽不一致, table-layout, scrollbar-gutter, 置顶专区

### 行宽口径 = `fit-content; min-width: 100%`, 且行内单元格必须 `min-width: 0`

- **触发**: 表格出现"列没溢出却常驻一条横滚动条"。
- **判别**: 缺 `min-width: 0` 时单元格的自动最小尺寸(= 文本全长)会把行的 min-content 顶到容器之上。
  **判别口诀: 底色跟内容、滚动条看容器**, 两者同时满足才算对。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 表头吸顶: `.group-head` 必须移出 `.group-table`

- **触发**: 做 / 改表头吸顶。
- **判别**: `overflow-x:auto` 会把 `.group-table` 变成**双轴滚动容器** ⇒ sticky 上下文失效。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 生成式列对齐(`colAlignCss` 注入 `:nth-child`)的三个要点

- **触发**: 改列对齐生成逻辑。
- **判别**: ①**left 列也必须生成规则**(数值列的 `.g-stat`/`.m-stat` 会盖掉默认左对齐);
  ②选择器必须用 `:where()` 压到 0,1,0 —— 高于 `.g-stat` 才能覆盖, 又必须**低于** `.g-stat.zero` 以保留"0 值居中";
  ③必须**同时**写 `text-align` 与 `justify-content`(值单元格有的是 flex)。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### sticky 偏移与最大高度不能写死

- **触发**: 改吸顶条高度 / 偏移。
- **判别**: 写死会在字号 / 内容变化时错位。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 两个吸顶条各有 `backdrop-filter` ⇒ 各自建立层叠上下文

- **触发**: 浮层被另一个 sticky 条遮挡。
- **判别**: 子元素的 z-index **跨不出去**。判别法: 先看遮挡方是否**也有** `backdrop-filter` / `transform` / `filter`,
  **不要一味加大 z-index**。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 两个独立表格要「逐栏对齐」: 列定义单点 + `table-layout: fixed` + `scrollbar-gutter: stable`

- **触发**: 把一个表拆成两块(如 kb.nav 的「置顶专区 + 主表」), 要求列宽/列序逐栏一致 (2026-10-05 实测)。
- **判别**: ①auto 布局下两表各按**自身内容**算列宽, 内容不同就永远对不齐 —— "两处照抄同一份 `width`"也无效;
  ②更隐蔽的是**滚动条**: 主表有竖滚动条而专区没有时, 两表内容宽度差一个滚动条宽(本壳 9px), 整表栏位平移;
  ③滚动容器上的横向 `padding` 与 `border` 同样改内容宽度 —— 差几 px 就错位。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### `:focus-within` 在带 `tabindex` 的行上, 鼠标点击也会画 outline

- **触发**: 行可聚焦。
- **判别**: 鼠标点击也触发 `:focus-within`。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### `flex: 0 1 <px>` 跨方向串味: column 容器里它变成**高度**

- **触发**: 给横向排布的控件行写 `flex: 0 1 250px` 这类"定宽"简写, 而该控件又被复用到
  `flex-direction: column` 的容器里(2026-09-25 实测: 设置页站点「要跑哪些规则」的
  「从已有规则集/规则中选择…」下拉被撑成 **460×250** 的竖条, 用户报"按钮变形过高")。
- **判别**: 选择器是**后代**写法(`.hb-ct .hb-select`)⇒ 命中该容器内**所有嵌套层级**的同名控件;
  而 `flex-basis` 落在**主轴**上 —— row 容器里是宽度, column 容器里就是高度, 且容器高度 auto 时不会缩回去。
  判别法: 量 `getBoundingClientRect().height` 是否**等于那个 flex-basis 值**(正常下拉约 37px)。
  ⚠ 静态检查全过(语法 / 花括号 / 类名配对 / JS 语法都查不出来), **只有真浏览器量 computed 值才暴露**。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### flex 工具条「文本贴顶 vs 图例/按钮居中」= 父级缺 `align-items`(默认 stretch)

- **触发**: 收到「某条统计栏 / 工具条 / 图例那行没对齐」(2026-10-16 实测: 流量图统计栏 `.hist-summary` 里
  「上传/下载图例」与「窗口 N 桶」错开 **3.7px**, 后面的档位按钮组 / 纵轴按钮组再错 **4px**; 用户口语
  「后者更高」描述的正是这个)。
- **判别**: 父 flex **没写** `align-items` ⇒ 默认 `stretch`, 每个子项被拉到**同行最高项**的高度; 于是两类
  子项分道扬镳 —— ①**纯文本**子项(block container)文字**贴顶**; ②自带 `align-items:center` 的子项
  (图例 `.hs-leg` 是 inline-flex / 控件组 `.qb-statctl`)内容**居中**。
  判别法: 真浏览器量每个子项的 `Range` 矩形 y(**文字墨迹盒**), 而不是元素盒 —— 元素盒会全部相等
  (实测都是 h=26), 看起来"没问题", 差的只有文字。⚠ **静态守阵(类名 / CSS 文本 / 模板结构)全绿**,
  只有真浏览器量布局才现形, 与「控件变形过高」「两态底色相近」同族。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### flex 行里"输入框缩成一截 + 按钮文字竖排" = 父容器缺增长因子

- **触发**: 改 flex 行布局。
- **判别**: `input` 的 `flex-basis:auto` 在自动宽度父级里**回退成内容宽**。
  判别法: 容器宽 / 输入框宽 / 按钮宽三者加起来**远小于**容器宽 = 父级没涨。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### flex / grid 子元素里 ellipsis 不生效 = 被省略的是**裸文本节点**

- **触发**: 省略号不出现。
- **判别**: 匿名文本节点**不可压缩**。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### `min-height` 是含边框的

- **触发**: 想让"有/无某段内容"行高一致。
- **判别**: `box-sizing: border-box` 下 `min-height` 含边框 ⇒ 必须把 `border-bottom` 算进去。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 入场动效不要给含 sticky 子元素的容器加 `fill-mode: forwards`

- **触发**: 给容器加入场动画。
- **判别**: transform 常驻会**创建层叠上下文**, 影响内部 fixed / 浮层定位。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 「例外色」规则别靠书写顺序赢: 同特异性时**后者压前者**

- **触发**: 给某处数值 / 图标写例外色(2026-09-20 实测)。
- **判别**: 状态栏今日流量的 `.sb-today .v-down` 与后面的 `.sb-item .val` 特异性同为 (0,2,0), **谁写在后面谁生效** ——
  棱镜 views.css 里前者在前 ⇒ 数值与数值里的箭头图标掉回白色; 星图 style.css 里前者在后 ⇒ 碰巧正确
  (**同一份改动只坏一边**, 极易误判成"棱镜主题缺令牌")。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### `<button>` 的文字色**不继承 body**: UA 默认色跟随系统配色(暗色主题下黑字)

- **触发**: 新增 / 改造按钮, 尤其是整块内容当按钮用的卡片、可点行(2026-09-22 实测: 设置页 Console Hub 卡片标题「连接 qBittorrent」暗色下发黑)。
- **判别**: 按钮只写了 `font: inherit` 没设 `color` ⇒ 文字色走 UA 默认 `buttontext`,
  它跟随**系统/浏览器 color-scheme** 而非页面主题令牌; 页面又未声明 `color-scheme` ⇒
  系统浅色时按钮内未显式着色的文字恒为纯黑。同卡片里的描述、徽章都有显式 `color`
  所以只有标题出事, 极易误判成"主题缺令牌"。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 既有窄屏媒体查询会吞掉新加的信息

- **触发**: 加 pill / 加状态槽位。
- **判别**: 某个 `@media` 段里已经把该区域隐藏 / 改版。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 同一语义不要用两种视觉重复表达

- **触发**: 加状态提示。
- **判别**: "组内不一致"是**提示性**信息, 不该占用强对比资源。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 状态徽章「两态底色相近」= 同亮度令牌 + 同透明度, 换色相救不了

- **触发**: 加 / 调状态色, 或收到"两个状态的底色分不出来"的反馈 (2026-10-05 kb.nav 用户报
  「open/done 状态底色相近, 需要优化」)。
- **判别**: **先量, 别按色相推断**。截徽章元素图, 采内侧填充像素: kb.nav 的 Open / Done 实测
  `#16272b` / `#1b2624` —— 差 (R+5, G−1, B−7), 肉眼不可分。根因不是色相写错, 而是 cyan `#56c8d7`
  与 green `#7fc79a` 的**相对亮度几乎相同**(≈177 / ≈180): 低透明度叠在暗底上时色相差异被压没,
  只剩亮度差 —— 而亮度差本来就是 0。这也解释为什么"明明换了青/绿两个很不一样的色却还是分不出"。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

- 顶栏 / 表头 / 状态栏底色与相邻面「同色」= 复用同一枚令牌, 换色相救不了: 详见 [attachments/layout-css-details.md](attachments/layout-css-details.md)

### 平行两态「同色相只差明度」= 必混淆, 要专用色相族分家 (不是拉 alpha)

- **触发**: 给同一行/元件加第二种选中类状态, 且两个状态是**平行关系**(无主次层级) ——
  2026-10-31 kb.nav 多选验收: msel(批量目标) 首版用单击预览 tr.sel 的 cyan 降透明度(.45 vs 满亮),
  用户报「单击的左条比选中的更亮, 且色系一致, 容易搞混」。
- **判别**: 两态是**层级关系**(如 待办实 / 完结虚) → 拉明度(上一条状态徽章口径); 两态是**平行关系**
  (单击预览 vs 批量选中, 语义无主次) → 明度差只会让用户猜"更亮的是不是更重要", 必须换专用色相族。
  auto-qb views.css R10-07 同款定案: 选中态专用 `--sel-*` 靛蓝族, 与品牌 accent/状态色彻底分家。
- **处置**: 详细步骤与实测证据见 [attachments/layout-css-details.md](attachments/layout-css-details.md)
