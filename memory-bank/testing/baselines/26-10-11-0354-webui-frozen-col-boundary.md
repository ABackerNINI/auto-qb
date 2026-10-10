# 3113 —— WEBUI 首列吸左边界提示(横滚残根读成"状态列被名称列盖住")基线

> 摘要: 用户报「向右滚动时状态列被名称列盖住」。取证确认非 z 序 bug: 吸左首格(26-10-06-1717)横滚时相邻列从其下方滑过是冻结列正确行为, 缺边界视觉线索 —— 未盖满的尾字紧贴首格右缘, 读成渲染错乱。修 = 三个横滚同步单点(`sync*HeadScroll`: shared/menu.js、shared/selection.js、shared/shows.js)在 scrollLeft>0 时给 `.group-table` 与吸顶表头打 `.is-hscrolled`(回 0 摘标), 三皮肤 `css/views.css` 据此给行吸左首格与表头吸左首格成对画右缘落影 + 发丝线。**用户复报「小窗时站点的徽标不会被名称列挡住」**: `.group-row { align-items: center }` 网格项不拉伸, 吸左首格只有单行内容高(22px), 多 chip 格换行撑高行(71px)后徽标上下两段漏出 —— 三皮肤吸左首格补 `align-self: stretch`。新守阵 `test_frontend_frozen_column_boundary_wiring`(钉打标/成对规则/stretch, 红验通过)。机理入坑档 `pitfalls/web-ui/frozen-column.md` 第④⑤条。
> 基线时间: 2026-10-11 04:07(复报修复后复测)

**Refs:** memory-bank/tasks/26-10-11-webui-frozen-col-boundary.md,memory-bank/pitfalls/web-ui/frozen-column.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已快进 8503f4d5→86138d33; 工作树含本专题全部改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3113 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 26.59s)
- 前置机检: `test.quick` 全绿(3112, 新守阵入列前); `npm run test:e2e:fast` 60 passed(1.8m)。
- 改动面(摘要): `src/auto_qb/webui/static/shared/`(menu.js / selection.js / shows.js 各 +2 行打标)、`src/auto_qb/webui/static/{prism,atlas,console}/css/views.css`(各 +1 条 .is-hscrolled 规则 + 吸左首格 `align-self: stretch`)、`tests/test_webui_static_skins.py`(新增 1 守阵 + 测试计划 1 行)。
- 真浏览器验证: prism ocean(暗)与 frost(亮)双主题截图 —— 横滚 60px 残根(".00 GiB")与名称省略号之间现边界线 + 渐隐落影; 回滚 scrollLeft=0 后 class 摘除、无任何绘制; atlas 同验。复报项: 注入多 chip 撑高行 + 骑线横滚, 修复前徽标从名称格上下成排透出 / 修复后全盖(`align-self` 开关对比, 首格 22px→71px)。
