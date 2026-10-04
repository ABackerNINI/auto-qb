# 基线切片 26-10-05-0542 — kb.nav 顶栏底色与其余部分难区分修复

> 摘要: kb.nav 顶栏底色改**专用令牌** `--chrome: #232e3b`。根因 = 顶栏与台账左侧栏 / 工具栏 /
> 控制台面板**共用同一枚 `--paper`** —— 实测顶栏 `#12161b` 与侧栏 / 工具栏逐通道差 **0**,
> 与表格区 `--bg #0e1114` 只差 **7**, 按判据 (同视图内两两 RGB 最大通道差 <20 即"分不出") 两条都不合格。
> 修法 = 抬**明度**(不换色相) + 下缘 cyan 缝; 连带修副标题对比度 (3.92:1 → 2.97:1 跌破 3:1) 与
> 段选钮选中态 (.12 只比栏亮 19 → .22 亮 34)。新增 1 条守阵。
> 基线时间: 2026-10-05 05:42

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md

- 分支: develop @ ee52e57d (+ 本轮未提交改动: nav_page.html / tests/test_kb_nav.py /
  memory-bank/pitfalls/web-ui/layout-css.md / activeContext 切片 / 本切片)
- 命令: `commands run test.full`(Windows, **两次采样** —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2566 passed + 4 skipped, 49.0~51.1s, 覆盖率 TOTAL 99%**
  (15477 语句 / 162 未覆盖 / 5240 分支 / 136 partial; 门槛 98% 达标)
- 靶向 (tests/test_kb_nav.py): **34 passed** —— 含本轮新增 1 条 `test_topbar_surface_distinguishable`
  (顶栏不得借回 `--paper` / `--paper-2` + 与 `--paper` / `--bg` 最大通道差 ≥24 + 下缘必须是 cyan 缝)。
  红验两分支各实测报错: ①把 `.topbar` 的 background 改回 `var(--paper)` → 借令牌分支报错;
  ②令牌值改贴侧栏 (`#161b21`, 与 `--paper` 差 6) → 距离分支报错。恢复后绿。
- 相对上一条 kb.nav 基线 (26-10-05-0353: 2554 passed + 4 skipped / 99% / 57.21s): passed **+12**
  —— 本轮只有 **+1**(新守阵), 其余 +11 是两条基线之间**其它会话合入 develop** 的用例 (v3 流量存储 S5
  退役 v1/v2 死代码 + 新增用例; 语句数 14871 → 15477)。**不是本轮引入的增量**, 别拿这 12 当回归判据。
  skip 集合不变 (Windows 侧 4 条 POSIX 专属)。耗时 51.13 / 48.96s 两次采样落在近几条切片 45.1~57.9s 的
  噪声带内, 非回归。
- 改动面: `.agents/skills/memory-bank/scripts/nav_page.html`(仅顶栏 CSS 三处: 新增 `--chrome` 令牌 +
  `.topbar` 底色/下缘 + `.brand small` 文字色 + `.seg button.on` 选中底) · `tests/test_kb_nav.py`
  (+1 守阵 + 测试计划 docstring 与"守什么"摘要同步) · `memory-bank/pitfalls/web-ui/layout-css.md`
  (新增「顶栏底色与相邻面同色」条 + 触发关键词行)。**数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动。**
- 机检 (headless Chromium, 非 pytest): 截元素图取**众数填充色**(顶栏内有搜索框 / 分段钮, 采单点会拿到假数字),
  顶栏↔侧栏 / 工具栏由 **0** 提到 **32**, 顶栏↔表格区由 **7** 提到 **39**(全部 ≥20 判据);
  下缘 1px 实测 `(50,92,106)` = cyan 缝; 段选钮 选中↔未选中 **57** / 选中↔栏 **34**。
  复现脚本 (`tmp-analysis/nav_shot.py` + 静态导出快照) 属 gitignored 临时物, 判别法落在坑档。
- Linux 侧本轮未重测 —— 改动为纯前端静态资源 + 测试, 无平台分支; 下次 `test.linux` 自然复核。
