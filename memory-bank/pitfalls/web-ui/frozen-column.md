# 首列吸左固定(冻结列)在本仓表格上的五处非显然约束

> 摘要: 给 `.group-row` 加「首列 `position: sticky; left: 0`」时, 五件事不显然 —— ①**表头 `.group-head` 在滚动容器之外**(纵向 sticky 的前提), 首格拿不到 sticky 锚, 必须用反向 `translateX` 抵消, 且要减掉表头 `padding-left`(三皮肤均 14px), 否则比行首格恒右偏 14px; ②sticky 首格必须**不透明**才挡得住滑过的兄弟列, 而行的状态底(下沉/选中)是 rgba 令牌 —— 直接取令牌会**双重上色**(atlas 选中态实测逐通道差 17/18/33, 超可辨阈 20), 须用「同色 `linear-gradient` 叠不透明 `--bg-row`」做合成(差 ≤8); ③行的左侧色条 `.group-row.selected::before` 挂在**行**上, 横滚后随行滚出, 且**不能**顺手改成 sticky(行是 grid 容器, 绝对定位伪元素一变 sticky 就进流成为网格项, 破坏行布局); ④**吸左边界要有视觉提示** —— 横滚时滑入首格下方的列会留一段未盖满的尾字紧贴首格右缘, 无边界线索时被读成渲染 bug(2026-10-11 用户报「状态列被名称列盖住」), 须在横滚非零时画右缘落影 + 发丝线; ⑤**首格必须 `align-self: stretch`** —— 行是 `align-items: center`, 网格项默认不拉伸, 首格只有单行内容高, 站点/标签等多 chip 格换行把行撑高时(小窗常态)滑入的 chip 从首格上下两段漏出(2026-10-11 用户复报「小窗时站点的徽标不会被名称列挡住」)。
> 触发: 首列吸左, 冻结列, frozen column, sticky 首格, 横向滚动, 表头横向同步, transform 桥接, 首格不透明, 半透明状态底, 双重上色, 左侧色条消失, 过渡中间值, 皮肤 CSS 700 行上限, 残根, 尾字粘连, 状态列被盖住, 吸左边界, is-hscrolled, 边界落影, 徽标漏出, chip 换行, align-items center, align-self stretch, 首格高度

**Refs:** memory-bank/tasks/26-10-06-webui-frozen-first-column.md,memory-bank/tasks/26-10-11-webui-frozen-col-boundary.md

### 首列吸左固定(冻结列)的三处非显然约束

- **触发**: 给行宽 `fit-content` > 容器的这些表(辅种 / 种子 / 追剧)加「首列常驻滚动容器左缘」。
- **判别**: 一行 `position: sticky` 完不了事 —— 表头、底色、左色条三处各有独立成因(见处置);
  另有一条量测陷阱: 点击后立刻读 `backgroundColor` 会拿到**过渡中间值**。
- **处置**:
  - **① 表头不在滚动容器里, 首格只能用反向位移**: `.group-head` 为做纵向 sticky 被移出 `.group-table`,
    横向靠 `sync*HeadScroll` 写 `transform: translateX(-scrollLeft)` 桥接 ⇒ 它**没有滚动祖先**,
    `position: sticky` 对它无效。首格改 `transform: translateX(max(0px, calc(var(--head-pin-x, 0px) - 14px)))`,
    位移量由三个 `sync*HeadScroll` 写进 `--head-pin-x`。**减 14px 是必须的** —— 表头 `padding: 7px 14px`,
    不减的话表头首格恒比行首格右偏 14px; 行内首格用原生 sticky, 语义是 `max(0, 自然位 - scrollLeft)`,
    两者同形才对得上(实测: 横滚后两格 `left` 同为容器左缘)。
  - **② 首格必须不透明, 半透明状态底要自己做合成**: 兄弟列从首格下面滑过, 半透明底挡不住。
    基础 / 悬浮态行底是不透明 hex, 直接取即可; 但 `.expanded`(`--bg-sunken`)/`.selected`/`.partial`
    (`--sel-bg`)是 **rgba** —— 把令牌直接给首格会叠在行底之上**双重上色**: atlas 选中态实测
    首格 `#333a61` vs 行 `#232840`(差 17/18/33 > 20, 肉眼可辨)。修法 =
    `linear-gradient(<tint>, <tint>), var(--bg-row)`(同色渐变当纯色层 + 一层不透明基色)
    ⇒ 首格 = tint over `--bg-row`、行 = tint over 页底 `--bg`, 实测差 ≤8。
  - **③ 左侧色条不跟着吸, 且不能顺手改 sticky**: `.group-row.selected::before` 挂在**行**上
    (`left: 0` = 滚动内容左缘), 横滚后随行滚出视野 ⇒ 选中行横滚时只剩底色、丢色条(已知残留)。
    **别把它改成 `position: sticky`** —— `.group-row` 是 grid 容器, 绝对定位的伪元素一旦变 sticky
    就**进流成为网格项**被自动摆进单元格, 直接破坏行布局。要保住它得换承载物(如首格 `box-shadow: inset`),
    但那样未横滚时会与行上那条并出双线。
  - **④ 吸左边界要有视觉提示, 否则滑入列的残根被读成渲染 bug**: 兄弟列滑进首格下方是**逐步**的
    —— 未盖满的尾字("做种"的"种")会紧贴首格右缘露出, 与名称省略号之间没有任何分隔,
    读成"名称后面多了个坏字"(2026-10-11 用户报「向右滚动时状态列被名称列盖住」)。
    盖住本身是冻结列的正确行为, 缺的是**边界线索**: CSS 感知不了 scrollLeft, 由三个
    `sync*HeadScroll` 在横滚非零时给 `.group-table` 与吸顶表头打 `.is-hscrolled`(回 0 摘标),
    CSS 据此给吸左首格(行 + 表头**成对**, 漏表头 = 列名残根仍裸露)画右缘落影 + 发丝线,
    尾字在边界渐隐、读成 pane 边界; 未滚动不画(无物可盖, 视觉保持安静)。
  - **⑤ 首格必须 `align-self: stretch`, 否则高行时盖不住**: `.group-row { align-items: center }`
    —— grid 项默认不拉伸, 吸左首格只有**单行内容高**(实测 22px), 且垂直居中。站点(`.g-sites`
    flex-wrap)/标签(`.g-tags`)等多 chip 格在窄轨(小窗常态)换行把行撑高(实测 71px)后, 横滚时
    滑入首格下方的 chip 从首格**上下两段**成排漏出(2026-10-11 用户复报「小窗时站点的徽标不会
    被名称列挡住」)。修 = 首格 `align-self: stretch`(撑满行内容高; `.g-name` 自身
    `align-items:center` 内容仍居中不改观感)。方角疑虑不成立: 行 `padding: 10px 14px` ≥
    圆角半径, 拉伸后的首格方角落不到行圆角曲线区, 不戳行缘。
  - ⚠ **量底色别在点击后立刻读**: `.group-row` 有 `transition: background`, `getComputedStyle().backgroundColor`
    会拿到**过渡中间值**(实测读到 `rgba(64,72,124,.345)`, 既非旧值也非 `--sel-bg`), 极易误判成「规则没生效」。
  - ⚠ **落点选文件**: 皮肤 CSS 有**单文件 700 行**上限(守阵 `test_frontend_template_split_wiring`,
    只查 atlas / console)。atlas 的 `css/components.css` 已顶满 ⇒ 新增规则一律放该皮肤的 `css/views.css`
    (prism 的表格规则本就在 `views.css`, 且不受该上限约束)。
- **守阵**: `test_frontend_frozen_column_boundary_wiring`(静态钉 is-hscrolled 打标、三皮肤成对
  规则与首格 `align-self: stretch`);
  几何行为静态判不出, 验证仍 = 桩服务真浏览器量 `getBoundingClientRect().left`
  (横滚 400 后首格 == 容器左缘, 表头首格同值) + 残根边界与高行遮盖的截图目检。
