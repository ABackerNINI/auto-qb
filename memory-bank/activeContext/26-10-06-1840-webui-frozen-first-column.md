# 宽行点击落点 — 表格首列吸左固定

> 摘要: 认领 issue 26-10-06-1717(question 类)并按用户拍板方向 ② 实施**首列吸左固定**。复验推翻了 issue
> 的隐含前提: `scrollIntoViewIfNeeded` 全仓只出现在 e2e 注释与本件 —— 居中滚动是 Chromium 在 Playwright
> 点击「宽于滚动容器的元素」时的**内部行为**, 产品零调用、真实用户不触发 ⇒ 建议 ① 在产品侧没有落点。
> 落地: 三皮肤 `css/views.css` 给 `.group-row > :first-child` 上 `position: sticky; left: 0` + 不透明底
> (半透明状态用同色 `linear-gradient` 叠 `--bg-row` 合成); 表头 `.group-head` 在滚动容器之外, 首格用
> `translateX(max(0px, calc(var(--head-pin-x) - 14px)))` 反向抵消, 由三处 `sync*HeadScroll` 写位移量。
> 真浏览器实测: 横滚 400 后首格 `left` == 容器左缘, 表头首格同值。
> 最后活动: 2026-10-06 18:40

**Refs:** memory-bank/tasks/26-10-06-webui-frozen-first-column.md, memory-bank/testing/baselines/26-10-06-1840-webui-frozen-first-column.md

## 现状

- **改动面**(6 源文件 + 知识库): `src/auto_qb/webui/static/{atlas,console,prism}/css/views.css` ·
  `src/auto_qb/webui/static/shared/{menu,selection,shows}.js`(各 +1 行写 `--head-pin-x`)。
- **机制**: 行内首格 = 原生 `position: sticky; left: 0`(语义 `max(0, 自然位 - scrollLeft)`, 连续无跳变);
  表头首格 = 反向 `translateX(max(0px, calc(var(--head-pin-x) - 14px)))`(14px = 表头 `padding-left`)。
- **首格底**: 基础 / 悬浮取不透明令牌; `.expanded` / `.selected` / `.partial` 用
  `linear-gradient(<tint>, <tint>), var(--bg-row)` 合成(直接取 rgba 令牌会双重上色, 差 17/18/33 > 可辨阈 20)。
- **验证**: 桩服务(8137)真浏览器 —— atlas + prism(默认主题 frost 是**浅色**)+ 种子视图, `scrollLeft=400`
  时首格 `left` 12 == 容器左缘 12, 表头首格同值; 首格底不透明。`test.full` 2677 + 4 / 99%。

## 关键决策

- **不按 issue 建议 ① 硬做**: 复验证明产品侧无 `scrollIntoView` 调用, ① 没有现成改动点; 而「行宽收窄」
  与 `layout-css` 的行宽口径冲突且会复发「右滚无底色」旧缺陷。用户拍板改走 ②。
- **② 不解决自动化落点**: 冻结的是首格, 行盒仍是 2038px ⇒ Chromium 仍会居中滚动, e2e 的 `clickRow`
  对冲(`scrollLeft` 归零 + 落点验证)**仍然必要**。拍板时已向用户明示。
- **规则落点**: 皮肤 CSS 单文件 700 行上限(守阵只查 atlas / console); atlas `components.css` 已顶满
  ⇒ 统一放 `css/views.css`。

## 未闭环

- **展开明细表未冻结**: `.member-row` / `.detail-head` 保持横滚(在 `.detail` 内缩, 首格吸 0 会盖住面板左框);
  若要冻结需先决定面板左框的处置。
- **选中态左色条横滚后仍丢**: `.group-row.selected::before` 挂在行上, 随行滚出; 不能改 sticky
  (grid 容器里伪元素会变网格项), 换承载物会在未横滚时并出双线 —— 待有需求时定。
- **`.is-pending` 的 `opacity: .55` 会让首格变半透明**(横滚时能看到滑过的兄弟列): 3s 瞬态, 未处理。
- 真机走查(真实浏览器手工横滚三皮肤)未做 —— 本轮只走桩服务。
