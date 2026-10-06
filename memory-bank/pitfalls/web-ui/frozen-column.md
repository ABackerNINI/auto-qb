# 首列吸左固定(冻结列)在本仓表格上的三处非显然约束

> 摘要: 给 `.group-row` 加「首列 `position: sticky; left: 0`」时, 三件事不显然 —— ①**表头 `.group-head` 在滚动容器之外**(纵向 sticky 的前提), 首格拿不到 sticky 锚, 必须用反向 `translateX` 抵消, 且要减掉表头 `padding-left`(三皮肤均 14px), 否则比行首格恒右偏 14px; ②sticky 首格必须**不透明**才挡得住滑过的兄弟列, 而行的状态底(下沉/选中)是 rgba 令牌 —— 直接取令牌会**双重上色**(atlas 选中态实测逐通道差 17/18/33, 超可辨阈 20), 须用「同色 `linear-gradient` 叠不透明 `--bg-row`」做合成(差 ≤8); ③行的左侧色条 `.group-row.selected::before` 挂在**行**上, 横滚后随行滚出, 且**不能**顺手改成 sticky(行是 grid 容器, 绝对定位伪元素一变 sticky 就进流成为网格项, 破坏行布局)。
> 触发: 首列吸左, 冻结列, frozen column, sticky 首格, 横向滚动, 表头横向同步, transform 桥接, 首格不透明, 半透明状态底, 双重上色, 左侧色条消失, 过渡中间值, 皮肤 CSS 700 行上限

**Refs:** memory-bank/tasks/26-10-06-webui-frozen-first-column.md

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
  - ⚠ **量底色别在点击后立刻读**: `.group-row` 有 `transition: background`, `getComputedStyle().backgroundColor`
    会拿到**过渡中间值**(实测读到 `rgba(64,72,124,.345)`, 既非旧值也非 `--sel-bg`), 极易误判成「规则没生效」。
  - ⚠ **落点选文件**: 皮肤 CSS 有**单文件 700 行**上限(守阵 `test_frontend_template_split_wiring`,
    只查 atlas / console)。atlas 的 `css/components.css` 已顶满 ⇒ 新增规则一律放该皮肤的 `css/views.css`
    (prism 的表格规则本就在 `views.css`, 且不受该上限约束)。
- **守阵**: 暂无(几何行为, 静态判不出); 验证 = 桩服务真浏览器量 `getBoundingClientRect().left`
  (横滚 400 后首格 == 容器左缘, 表头首格同值)。
