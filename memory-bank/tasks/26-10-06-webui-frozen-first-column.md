# 26-10-06-webui-frozen-first-column — 宽行点击落点: 表格首列吸左固定

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-06 18:40
**Summary:** 认领 issue 26-10-06-1717(question 类)并按用户拍板方向 ② 实施「首列吸左固定」。复验先把前提推翻了: `scrollIntoViewIfNeeded` 全仓只出现在 e2e 注释与本件 —— 居中滚动是 **Chromium 在 Playwright 点击「宽于滚动容器的元素」时的内部行为**, 产品代码零调用、真实用户鼠标点击不触发 ⇒ issue 建议 ①(滚动定位改道)在产品侧**没有现成改动点**。落地: 三皮肤在 `css/views.css` 加 `.group-row > :first-child { position: sticky; left: 0 }` 且首格给不透明底(基础态取 `--bg-row`; 半透明状态用同色 `linear-gradient` 叠 `--bg-row` 做合成); 表头在滚动容器之外, 首格用 `translateX(max(0px, calc(var(--head-pin-x) - 14px)))` 反向抵消, 位移量由三处 `sync*HeadScroll` 写进 `--head-pin-x`。验证: 桩服务(8137)真浏览器实测双皮肤 + 种子视图, 横滚 400 后首格 `left` 12 == 容器左缘 12、表头首格同值、首格底不透明。test.full **2677 passed + 4 skipped / 99%**(基线 [26-10-06-1840](../testing/baselines/26-10-06-1840-webui-frozen-first-column.md))。范围边界: 展开明细表(`.member-row`/`.detail-head`)不冻结; 选中态左色条横滚后仍丢(见坑档)。
**Topics:** webui-frozen-first-column
**Refs:** memory-bank/issues/26-10-06-1717-question-webui-wide-row-click-landing.html, memory-bank/testing/baselines/26-10-06-1840-webui-frozen-first-column.md, memory-bank/pitfalls/web-ui/frozen-column.md

## 原始请求

用户: 「认领issue并修复: memory-bank/issues/26-10-06-1717-question-webui-wide-row-click-landing.html」。
该件是 `question` 类(方向二选一、待定调)。复验后 Agent 把两个候选方向的成本 / 风险摆出并请用户圈选, 用户拍板 **② 首列吸左固定**。

## 思考过程与决策

- **复验推翻了 issue 的隐含前提**: issue 建议 ① 是「滚动定位改滚到行首语义」, 但 `grep -rn scrollIntoViewIfNeeded`
  全仓只命中本件与 `e2e/multiselect-shows.spec.mjs` 的注释 —— **产品代码零调用**; 产品自身的滚动跟随
  (`shortcuts.js::_kbScrollRowIntoView` / `config_hub.js::hubTrackerScrollActIntoView`)只做纵向 `scrollBy`,
  文件头还明写「禁 scrollIntoView」。⇒ 居中滚动是 Chromium 在 Playwright 点击「宽于滚动容器的元素」时的
  **内部行为**, 真实用户鼠标点击不触发; 产品侧**没有** ① 的落点, 故拍板改走 ②。
- **② 不是「让自动化不再需要对冲」**: 冻结的是**首格**, 行的盒子仍是 2038px ⇒ Chromium 的
  `scrollIntoViewIfNeeded` 照样居中, `clickRow` 的 `{8,8}`(相对**行盒**)仍会出界。② 交付的是**真机收益**
  (横滚时名称列 / 落点常驻) —— 这一点在请用户拍板时已明示, 用户知情后仍选 ②。
- **不按 issue 建议 ① 硬做**: 「行宽收窄(行盒 = 容器宽)」能根除居中滚动, 但与 `layout-css` 的既定口径
  (行一律 `fit-content; min-width: 100%`)冲突, 且会复发「右滚无底色」旧缺陷(该口径正是为它定的) ⇒ 不选。
- **首格底必须自己合成**: 行的状态底是 rgba 令牌, 直接给首格会双重上色(实测差 17/18/33 > 可辨阈 20)。
  详见坑档 `pitfalls/web-ui/frozen-column.md`。
- **表头必须一起吸**: 表头 `.group-head` 在滚动容器之外(纵向 sticky 的前提), 横向靠 transform 桥接
  ⇒ 首格拿不到 sticky 锚, 只能反向位移; 且要减掉表头 `padding-left`(14px)才与行首格同缘。
- **落点选文件**: 皮肤 CSS 单文件 700 行上限(守阵只查 atlas / console)。atlas `css/components.css` 已顶满
  ⇒ 规则统一放各皮肤 `css/views.css`(prism 的表格规则本就在此)。
- **范围边界(明示不做)**: 展开明细表 `.member-row` / `.detail-head` 不冻结 —— 它在 `.detail`
  (有 14px 内边距 + 边框 + 圆角)内缩, 首格吸 0 会盖住面板左框; 且 e2e 的 `clickRow` 落点纪律从未覆盖
  `.member-row`(issue 证据链也只涉组行 / 剧行 / 种子行)。选中态左色条横滚后仍随行滚出(不能改 sticky:
  行是 grid 容器, 伪元素会变网格项)。

## 实现计划

1. 三皮肤 CSS: 在 `atlas|console|prism` 的 `css/views.css` 加冻结首列规则(sticky + 首格底合成)
   与表头首格反向位移规则。
2. 三处 `sync*HeadScroll`(`menu.js` / `selection.js` / `shows.js`): 写 `--head-pin-x`。
3. 验证: 桩服务真浏览器量几何 + 底色; `test.one` 跑皮肤 CSS 体量守阵。
4. 收尾: 本档案 + activeContext 切片 + 基线切片 + 坑档 `pitfalls/web-ui/frozen-column.md` + issue 置 Done
   + `kb.index` + `test.full`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 三皮肤 CSS 冻结首列 + 表头反向位移 | ✅ 完成 | 均落 `css/views.css`(atlas `components.css` 已顶 700 行上限) |
| 三处 `sync*HeadScroll` 写 `--head-pin-x` | ✅ 完成 | menu.js / selection.js / shows.js 各 +1 行 |
| 真浏览器几何与底色验证 | ✅ 完成 | 双皮肤 + 种子视图; 横滚 400 后首格 == 容器左缘 |
| 皮肤 CSS 体量守阵 | ✅ 完成 | 首版落 atlas/components.css 撞 700 行上限, 改放 views.css 后过 |
| 收尾(档案 / 切片 / 基线 / 坑档 / issue / 索引) | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-06 18:2x** 开工 `commands run my-commit-flow.sync` → `已同步 aaff8b3a`。复验 issue 前提(见上),
  向用户摆两个方向的成本 / 风险。
- **2026-10-06 18:3x** 用户拍板 ②。实施 1-2; 真浏览器验证: atlas / prism 双皮肤 + 种子视图, 横滚 400 后
  首格 `left` 12 == 容器左缘 12、表头首格同值、首格底不透明(prism 默认主题为**浅色** frost, 同样正确);
  选中态首格 `#252c48` vs 行 `#232840`(差 ≤8)。
- **2026-10-06 18:3x** `test.full` 首跑 **2 failed**(`test_gen_all_check_is_green` 索引未重建 +
  `test_frontend_template_split_wiring` atlas/components.css 722 > 700 行上限)。后者是本轮引入:
  规则从 `components.css` 移到 `views.css` 后单跑即绿。
- **2026-10-06 18:4x** `kb.index` 重建 20 生成物; `test.full` **2677 passed + 4 skipped / 99%**
  (16021/163/5472/143, 59.21s)全绿。
- **2026-10-06 18:4x** 收尾: 本档案 + activeContext 切片 + 基线切片 + 坑档 `pitfalls/web-ui/frozen-column.md`
  + issue 置 Done(补实际修法 / 验证方式 / 数字)。
