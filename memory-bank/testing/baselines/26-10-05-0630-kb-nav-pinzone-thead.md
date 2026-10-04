# 基线切片 26-10-05-0630 — kb.nav 撤销顶栏配色改动 + 修置顶专区表头

> 摘要: 两件事。①**撤销** 26-10-05-0542 那一版顶栏配色改动 (`.topbar` 底色/下缘、`.brand small`
> 文字色、`.seg button.on` 选中底三处全部还原) —— 用户澄清当轮报的「标题栏」指的是台账列标题行,
> 顶栏是误认。②**修置顶专区表头**: 与置顶行只差 14 (<20), 根因是置顶行的淡 cyan 强调色吃掉了
> 可用明度空间; 解 = 把 `--chrome` 整体抬一档 (`#232e3b` → `#2b3947`), 三面 (数据行 / 工具栏 /
> 置顶行) 全过。守阵由 1 条扩成 2 条 (含一条**反向守**)。
> 基线时间: 2026-10-05 06:30

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md

- 分支: develop @ ef5d5008 (+ 本轮未提交改动: nav_page.html / tests/test_kb_nav.py /
  memory-bank/pitfalls/web-ui/layout-css.md 及其 `_index.md` / activeContext 切片 / 本切片)
- 命令: `commands run test.full`(Windows, **两次采样** —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2567 passed + 4 skipped, 46.0~47.6s, 覆盖率 TOTAL 99%**
  (15477 语句 / 162 未覆盖 / 5240 分支 / 136 partial; 门槛 98% 达标)
- 靶向 (tests/test_kb_nav.py): **35 passed** —— 用例总数与上基线相同 (本轮是**替换 + 扩条**, 不新增):
  · `test_ledger_thead_surface_distinguishable` 由 5 条红线扩到 **6 条**, 新增「置顶专区表头 vs
    置顶行**合成色** ≥24」—— 置顶行不是令牌而是 `rgba(86,200,215,.05)` over `.pinzone` 的 `--paper-2`,
    守阵按 alpha **真算**一遍再比;
  · `test_topbar_surface_distinguishable` → **`test_topbar_surface_is_left_at_paper`**(反向守:
    顶栏底色一旦不再是 `--paper` 就报错, 提示"要改先问用户")。
  **三处红验各实测报错**: ①顶栏底色改回 `--chrome` → 反向守报错; ②`--chrome` 退回 `#232e3b` →
  专区表头 vs 置顶行只有 14 (<24); ③专区表头留在 `--paper-3` → 同款表头不一致。恢复后 35 passed。
- 相对上一条基线 (26-10-05-0612: 2567 passed + 4 skipped / 99% / 43.5~43.7s): passed / skipped /
  语句 / 分支 / partial **五组数字完全相同** (改动仍只在前端静态资源与测试, 不在 `src/` 的 .py);
  耗时 47.61 / 45.95s 落在近几条切片 43.5~51.1s 的噪声带内, 非回归。
- 改动面: `.agents/skills/memory-bank/scripts/nav_page.html`(顶栏三处还原 + `--chrome` 值
  `#232e3b` → `#2b3947` + 令牌与顶栏注释重写) · `tests/test_kb_nav.py`(1 条扩红线 + 1 条改反向守 +
  测试计划 docstring 与"守什么"摘要同步) · `memory-bank/pitfalls/web-ui/layout-css.md`(同名条补
  「顺带发现≠顺带修」「强调过的行会挤掉明度空间」「合成色要真算」三条 + 现状留痕段)。
  **数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动。**
- 机检 (headless Chromium, 非 pytest, 点第一行图钉后截图取**众数填充色**):
  置顶专区表头↔置顶行 **14 → 26**; 主表表头↔数据行 **39 → 51**; 主表表头↔工具栏 **32 → 44**;
  专区表头↔专区底 (`--paper-2`) **23 → 35**; 专区表头↔主表表头 **0**(刻意相同)。
  表头文字 `--dim` 在新底色上对比度 **4.60:1**(≥4.5)。
- ⚠ **顶栏现状 (别重新"发现"再动手)**: 顶栏与侧栏 / 工具栏逐通道差仍是 **0** —— 用户 2026-10-05
  知情后明确保持原样。有反向守阵钉着, 要改先问用户。
- Linux 侧本轮未重测 —— 改动为纯前端静态资源 + 测试, 无平台分支; 下次 `test.linux` 自然复核。
