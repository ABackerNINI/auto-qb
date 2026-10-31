# 经典表行 CSS width:fit-content 漏进变体卡片栅格(卡片不填格·两列间长空隙)

> 摘要: 三皮肤经典表对引擎行容器 `.group-row` 写了 `width:fit-content; min-width:100%`(经典 flex 列容器里靠 min-width 兜底成整行宽, 内容超宽才横滚)。变体把 `.group-table` 覆盖成 **grid** 并用 `min-width:0` 拆掉兜底后, `width:fit-content` 就**直接生效**了 —— grid 项宽度非 auto 时不参与默认 `justify-self:stretch`, 卡片收缩到内容宽(实测 ~330px / 695px 格), 两列卡片之间留下 ~700px 永久空洞, 且卡宽随内容漂移(实体 330 vs 虚拟 378, 违反「宽度统一」)。用户报障口径「真实 tracker 卡片与虚拟卡片之间有很长的空隙, 虚拟卡片后方也有空隙」(2026-10-12, 04 状态卡片栅格)。修法 = 变体卡片规则显式 `width:auto`(+ 静态守阵钉死)。
> 等级: L0
> 触发: width:fit-content, min-width, justify-self stretch, group-row, 卡片不填满, 栅格空隙, 两列中间大洞, 长空隙, 卡片宽度不一致, 虚拟卡后方空白, dt04, 状态卡片栅格, 经典表 CSS 继承, grid 项拉伸

**Refs:** memory-bank/testing/baselines/26-10-13-0008-webui-dt04-card-grid-fill-width.md,memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md

### 变体卡片栅格的行容器被经典表 CSS 缩成内容宽

- **触发**: 变体 CSS 把引擎行容器 `.group-row` 从「经典表格行」改造成「卡片」(04 状态卡片栅格: `.dt04-list .group-table` 覆盖成 `display:grid; grid-template-columns:repeat(2, minmax(0,1fr))`, 行容器 `display:block` + `min-width:0`)。三皮肤经典表 CSS(atlas/console/prism 的 components.css / views.css)对 `.group-row` 有 `width:fit-content; min-width:100%` —— `min-width:0` 只拆掉了 min-width 兜底, **width:fit-content 没人拆**。
- **判别**: 「grid 栅格里的项不填满格子」先查两项继承: ①`width` 是不是非 auto(fit-content / max-content / 具体值)—— grid 项只有 `width:auto` + 默认 `justify-self:stretch` 才填格; ②`min-width:100%` 在 grid 格里解析的是**格宽**而非容器宽, 经典 flex 列里的「整行宽」兜底语义在 grid 里不成立(所以 `min-width:0` 是对的, 但救不了 width)。判别手法: 真浏览器量卡片宽 vs 格宽(getBoundingClientRect vs `grid-template-columns` 实测轨宽), 或 getComputedStyle 的 width。同族判据: 任何「变体把引擎经典行容器(.group-row/.group-table)改用途」的地方, 都要对经典表那几条(width:fit-content / min-width:100% / display:grid + gap)逐条过一遍继承。05/07/08/09 等 flex 列形态不受影响(min-width:100% 照旧兜底), **只有改成 grid 的形态中招**。
- **处置**: 变体卡片规则显式 `width:auto`(04: `.drawer .dt04-list .group-row { … width:auto; min-width:0; … }`, 特异性 (0,3,0) 压过皮肤 (0,1,0)); 不要反向删皮肤规则(经典表依赖它横滚)。守阵双扣: 静态 `test_drawer_tpl_trackers_card_uniform_height` 第 4 节钉 `.group-row` 行含 `width:auto`; e2e `drawer-trackers-variant-tables.spec.mjs` dt04 用例量几何 —— 每张卡宽 = (表宽 - gap)/2 ±1px 且全部同宽(fit-content 回潮即红)。教训: 「卡片宽度统一」这类版式口径, 只用 CSS 字符串守阵拦不住继承链, 必须配一条真浏览器几何断言。
