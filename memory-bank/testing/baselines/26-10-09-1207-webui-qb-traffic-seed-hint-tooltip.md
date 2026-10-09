# 2842 —— 种子流量图统计栏口径注解改为累计读数的悬浮提示

> 摘要: 「种子流量图控件落点」专题第 3 轮(用户动议)收尾基线。改动: `shared/tpl/drawer.html` 统计栏常驻口径注解「累计为窗口内增量(断线期不计)」(`.hist-hint` span)退场, 改为「上传累计 / 下载累计」两个读数 span 上的 `:title="qbCurSummaryHint"`(走全局断供管道 → `data-aq-tip`); 零 CSS 改动(`.hist-hint` 规则保留 —— `popovers.html` 今日流量弹层仍在消费)。守阵侧**只改写既有断言口径**(次序断言去掉 hint 位 + 新增「两处 tooltip 锚点」与「抽屉模板不得再有 `.hist-hint`」两条), 未新增测试函数。副作用: 统计栏由两行收回单行, 图高回升。
> 档案: memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md
> 基线时间: 2026-10-09 12:07

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2842 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 47.35s(命令墙时 49.8s)
- **新增/修正用例**: **零新增测试函数** —— 只**改写** `tests/test_webui_static_dom_panel.py::test_frontend_qb_traffic_chart_wiring` 的统计栏断言: ①次序断言的下标链去掉 `qbCurSummaryHint` 一项(它不再占位, 改为挂在两个累计读数上); ②新增 `stat_blk.count(':title="qbCurSummaryHint"') == 2`(两个读数都必须挂提示、文案单一来源); ③新增 `'class="hist-hint"' not in drawer_tpl`(常驻文案必须退场)。

## 说明

- **代码事实变更**: 有 —— 统计栏常驻口径注解改为两个累计读数的悬浮提示(`:title` → 全局断供管道迁 `data-aq-tip`), 抽屉模板里不再有 `.hist-hint` span。文案单点 `qbCurSummaryHint` 未动(分组作用域仍自动带「 · 组口径 = 当前成员集聚合」尾注)。零 JS / 零 CSS 改动。
- **真浏览器旁证**(临时桩复用 `scripts/ui_harness.py` 合成种子 + `qb_traffic` 旗标 + 合成流量响应, 已删; 截图 `tmp-analysis/seed-traffic-hint-tooltip.png` 留档): 三皮肤 1440x900 真实手势实测 —— 悬停「下载累计」/「上传累计」均弹 `.aq-tip`「累计为窗口内增量(断线期不计)」, 两处 span 的 `data-aq-tip` 就位且 `title` 已断供(迁走)/ 统计栏 **31~33px 单行**(上一轮 54~57px 两行)/ 图 **259~261px**(上一轮 235~238px)/ 分组形态尾注正确 / 零 pageerror。
- **未验证面**: ①15 个 `drawer_tpl/` 变体下统计栏的观感未逐变体走查; ②tooltip 在抽屉贴近屏幕底缘时的弹层避让未专项走查(全站 tooltip 共用同一避让实现)。
