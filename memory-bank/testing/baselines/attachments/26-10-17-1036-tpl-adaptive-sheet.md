# 3502 passed + 4 skipped(根) —— 模板版面自适应: 正文与表格同宽(1280 封顶 + clamp 侧距)

> 摘要: 模板版面自适应: 正文与表格同宽(1280 封顶 + clamp 侧距)
> 基线时间: 2026-10-17 10:36

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮模板改动与知识库回写的同一棵树上): **3502 passed + 4 skipped in 121.51s**; TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。与上条基线逐位一致 —— 纯模板 CSS 改动, 零测试面影响。
- `kb.check` 全绿(新增面检查 / 回写措辞守卫 / 日期守卫)。
- 渲染量化验收(playwright, tmp 夹具, 三档视口实测 `getBoundingClientRect().right`): 1024 → 正文/表格/代码块右缘均为 991; 1280 → 均为 1239; 1920(sheet 封顶 1280) → 均为 1556; 三档 `pageScroll` 全为 false —— 右缘完全一致且无横向溢出。改前(74ch 封顶)同内容下正文右缘比表格短约 470px。
- 模拟建档: `kb.new plan`(临时目录)一件, 10 处 SLOT 全派生, `check_doc_templates` 新增面检查通过。

## 本改动面

- `.agents/skills/memory-bank/templates/plan.html` 与 `report.html`(两模板同改): `.sheet` 改 `max-width: 1280px; padding: 48px clamp(18px, 3.2vw, 44px) 80px`(自适应: 随视口流动 + 侧距伸缩); 移除 `p` / `ul,ol` / `.lede` / `.aside` 的 `max-width: 64~74ch` —— 正文与表格同宽; 新增 `@media (max-width: 1180px)` 让表格内代码断行, 防窄视口页面横向溢出。
- `memory-bank/conventions/webui.md`: 制品模板正文区规格条同步为自适应口径(含窄视口断行规则)。
- 测试零改动; 无产品代码(`src/`)改动。
