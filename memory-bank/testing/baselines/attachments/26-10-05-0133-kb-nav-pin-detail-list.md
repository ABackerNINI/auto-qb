# 基线切片 26-10-05-0133 — kb.nav 置顶专区改为与主表同栏的详细列表

> 摘要: 用户「kb.nav 的 pin 区样式改为详细信息列表, 即与主区域一样, 只是置顶展示, 可以做强调样式等,
> 但栏需要保持与主区域的一致」的改版后全量实测。核心 = 页面壳 `nav_page.html` 的置顶专区从紧凑 chip
> 列表改为与主表**逐栏一致**的七栏详细列表, 且**不做"两处各写一份列定义再对表"**, 而是结构性单点:
> ①列定义单点 = 主表 thead(专区渲染时克隆 `thead.outerHTML`), 全壳仅一处表头; ②行单元格共用
> `ledgerCells()`(主表与专区同一份栏序/栏宽); ③`table-layout: fixed` + 两滚动容器 `scrollbar-gutter: stable`
> + 专区横向 padding 归零 + 左 accent 用 `inset` 阴影(都不许改内容宽度) + 窄屏 `min-width: 720px` 兜底。
> 强调样式 = `.pzhead` 吸顶 + 操作提示、置顶行淡 cyan 底 + 悬停加深、专区表头粘在 `.pzhead`(28px) 之下。
> 踩坑与机检判据见 [pitfalls/web-ui/layout-css.md](../../pitfalls/web-ui/layout-css.md)「两个独立表格逐栏对齐」节。

> 基线时间: 2026-10-05 01:33
> 档案: memory-bank/activeContext/26-10-04-0952-kb-nav-page.md (第七跟进轮)

**Refs:** memory-bank/pitfalls/web-ui/layout-css.md · memory-bank/progress/implemented-tooling.md · memory-bank/testing/baseline.md

- 分支: develop @ b4292805 (+ 本轮未提交改动: .agents/skills/memory-bank/scripts/nav_page.html /
  tests/test_kb_nav.py / 本切片 / activeContext 切片 / pitfalls/web-ui/layout-css.md / progress/implemented-tooling.md)
- 命令: `commands run test.full`(Windows; 本轮跑了 3 次, 耗时 **40.5s ~ 53.1s**(引擎计 42.1s ~ 53.1s)
  —— 口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2537 passed + 4 skipped, 覆盖率 TOTAL 99%**
  (14868 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向单文件(tests/test_kb_nav.py): **21 passed**(10.09s, `--no-cov`) —— 19 既有 + 1 新增
  (`test_pin_zone_reuses_ledger_columns`), 另 2 条既有守阵改指共用单点 `ledgerCells`
  (`test_ledger_status_column_between_form_and_title` / `test_pinned_rendered_in_both_zones`)。
- 相对上基线 (26-10-05-0115: 2534 passed + 4 skipped / 99% / 42.47s): passed **+3** —— 本切片新增 1 条守阵
  与其同步改动; skip 集合不变(Windows 侧 4 条 POSIX 专属)。
- **运行时验证 (headless Chromium 真渲染, 非桩)**: 静态导出 + 注入 3 条 pin, 量四组 `th`/`td` 的
  `getBoundingClientRect()` `left:width` —— 主表表头 / 专区表头 / 主表首行 / 专区首行 **在 760 / 1100 /
  1600 / 1900 四档窗口宽度下逐栏全等**(如 1600 档: `224:34 258:96 354:46 400:84 484:835 1319:200 1519:54`);
  两容器 `offsetWidth - clientWidth` 均 9(scrollbar-gutter 生效); 另截图验专区内部滚动时 `.pzhead`(28px)
  与专区表头各自吸顶不错位; `node --check` 过壳内联脚本。
- 改动面: .agents/skills/memory-bank/scripts/nav_page.html(CSS 表格布局 + 专区渲染 + 事件委托)·
  tests/test_kb_nav.py(1 条新守阵 + 2 条改指共用单点 + docstring 清单)。**数据层 / 服务层零改动**。
