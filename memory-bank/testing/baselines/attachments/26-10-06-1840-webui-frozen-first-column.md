# 2677 —— 宽行点击落点: 表格首列吸左固定 (@ aaff8b3a + 未提交)

> 摘要: 本轮改 `src/auto_qb/webui/static/`(三皮肤 `css/views.css` + 三个 `shared/*.js` 各 +1 行)与知识库 ——
> `src/` 侧只有 CSS / JS 静态资源, **不进 `--cov=src` 的 Python 统计, 也不在 `testpaths(tests/)` 里** ⇒
> 语句 / 未覆盖 / 分支 / partial 与 develop 线上一条 [26-10-06-1818](26-10-06-1818-commands-git-retry-timeout.md)
> **四项逐位相同**, passed 也相同。真正被本轮触碰的守阵是 `test_frontend_template_split_wiring`
> (皮肤 CSS 单文件 700 行上限) —— 首版把规则放 atlas `css/components.css` 撞线(722 > 700), 移入
> `css/views.css` 后过。
> 基线时间: 2026-10-06 18:40

**Refs:** memory-bank/tasks/26-10-06-webui-frozen-first-column.md, memory-bank/activeContext/26-10-06-1840-webui-frozen-first-column.md

- 分支: develop @ **aaff8b3a**(开工 `commands run my-commit-flow.sync` = `已同步 aaff8b3a`; 工作树含本轮
  `src/auto_qb/webui/static/` 6 个文件与知识库改动, **未提交**)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2677 passed + 4 skipped, 覆盖率 TOTAL 99%**; 耗时 **59.21s**(单次采样, 不作基准,
  见 [../baseline.md](../baseline.md)「必须带区间」)。语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对 develop 线上一条 [26-10-06-1818](26-10-06-1818-commands-git-retry-timeout.md)
  (2677 + 4 / 16021 / 163 / 5472 / 143): **五项全同**。⚠ 归因: 本轮改动是浏览器侧静态资源(CSS / JS),
  不参与 Python 覆盖率, 也不进 pytest 收集面 ⇒ 数字相同是**预期而非漏测**; 本轮唯一被触发的相关守阵是
  `test_frontend_template_split_wiring`(单跑绿)。
- **浏览器侧验证(本轮真正受影响的一侧)**: 桩服务 `scripts/ui_harness.py --torrents 300 --port 8137`,
  Chromium 1440x900 实测 —— 容器左缘 12 / 宽 1416, 行宽 2038(> 容器, 复现 issue 的溢出前提);
  `scrollLeft=400` 后首格 `getBoundingClientRect().left` = **12 == 容器左缘**, 表头首格同值(对齐);
  首格 `background-color` 不透明(atlas `rgb(17,23,34)` = `--bg-row`; prism 默认主题 frost 为浅色 `rgb(247,250,253)`);
  选中态首格合成 `#252c48` vs 行 `#232840`(逐通道差 ≤8 < 可辨阈 20)。种子视图同样通过;
  展开明细表 `.member-row` 未冻结(本轮范围边界)。
- 改动面: `src/auto_qb/webui/static/{atlas,console,prism}/css/views.css` ·
  `src/auto_qb/webui/static/shared/{menu,selection,shows}.js` ·
  `memory-bank/{issues/26-10-06-1717-question-webui-wide-row-click-landing.html, issues/_index.md,
  tasks/26-10-06-webui-frozen-first-column.md, activeContext/26-10-06-1840-webui-frozen-first-column.md,
  testing/baselines/26-10-06-1840-webui-frozen-first-column.md,
  pitfalls/web-ui/frozen-column.md, pitfalls/web-ui/_index.md}`。
