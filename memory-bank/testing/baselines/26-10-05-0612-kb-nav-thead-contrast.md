# 基线切片 26-10-05-0612 — kb.nav 台账列标题行底色与数据行同色修复

> 摘要: kb.nav 台账**列标题行** (`#v-ledger thead th`, 时间戳 / 形态 / 状态 / 标题 …) 底色由 `--bg`
> 改 `--chrome`, 文字 `--faint` 抬到 `--dim`; 置顶专区表头对齐到同一枚令牌。根因 = 列头与**数据行
> 共用同一枚 `--bg`** —— 实测逐通道差 **0** (与紧挨其上的 `.toolbar` 也只差 7), 列头读不出"这是一行
> 表头"。选值排除了 `--paper-3`(与数据行 26 过线, 与工具栏只有 19 <20 ⇒ 会读成"工具栏的延伸")。
> 新增 1 条守阵 + 把颜色守阵的 CSS 取值 helper 提成模块级 (按令牌真值算)。
> 基线时间: 2026-10-05 06:12

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md

- 分支: develop @ ef5d5008 (+ 本轮未提交改动: nav_page.html / tests/test_kb_nav.py /
  memory-bank/pitfalls/web-ui/layout-css.md 及其 `_index.md` / activeContext 切片 / 本切片)
- 命令: `commands run test.full`(Windows, **两次采样** —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2567 passed + 4 skipped, 43.5~43.7s, 覆盖率 TOTAL 99%**
  (15477 语句 / 162 未覆盖 / 5240 分支 / 136 partial; 门槛 98% 达标)
- 靶向 (tests/test_kb_nav.py): **35 passed** —— 含本轮新增 1 条
  `test_ledger_thead_surface_distinguishable`(列标题行不得借回 `--bg` / `--paper` / `--paper-2` +
  与数据行 (`--bg`) 和工具栏 (`--paper`) **两面**最大通道差均 ≥24 + 表头文字对比度 ≥4.5:1 +
  置顶专区表头与主表表头同一枚令牌)。**四分支红验各实测报错**: ①底色改回 `var(--bg)` → 借令牌分支;
  ②改 `var(--paper-3)` → 工具栏轴 (19 <24); ③专区表头留在 `--paper-3` → 同款表头不一致;
  ④文字改 `var(--faint)` → 对比度 2.97:1 (<4.5)。恢复后绿。
- 相对上一条基线 (26-10-05-0542: 2566 passed + 4 skipped / 99% / 49.0~51.1s): passed **+1** = 本轮
  新守阵 1 条。语句 / 分支 / partial 三组数字与上基线**完全相同** (改动只在前端静态资源与测试,
  不在 `src/` 的 .py); skip 集合不变 (Windows 侧 4 条 POSIX 专属)。耗时 43.70 / 43.46s 两次采样,
  比上一条快约 6s, 落在近几条切片 40.5~57.9s 的噪声带内, 非回归。
- 改动面: `.agents/skills/memory-bank/scripts/nav_page.html`(顶栏/表头共用令牌 `--chrome` 的注释订正 +
  `#v-ledger thead th` 底色与文字色 + `.pinzone thead th` 底色对齐) · `tests/test_kb_nav.py`
  (+1 守阵 + 模块级 CSS 取值 helper 组 `_shell_css`/`_rule`/`_hex_token`/`_bg_token`/`_color_token`/
  `_max_channel_diff`/`_contrast` + 三条既有颜色守阵改用 helper + 测试计划 docstring 与"守什么"摘要同步)
  · `memory-bank/pitfalls/web-ui/layout-css.md`(那条扩成两个实例 + 新增「口语名先钉元素」「相邻面逐面过」
  「克隆同款元素必须跟着改」三条处置)。**数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动。**
- 机检 (headless Chromium, 非 pytest): 截元素图取**众数填充色** —— 列标题行↔数据行由 **0** 提到 **39**,
  列标题行↔工具栏由 **7** 提到 **32**(均 ≥20 判据); 吸顶态实测底色仍为不透明 `(35,46,59)`(滚动 600px 后);
  置顶专区表头↔主表表头 **0**(刻意相同)、专区表头↔置顶行由 **2** 提到 **14**(仍 <20 —— 属专区自身的
  既有弱项, 未修, 见 activeContext「后续注意」)。复现脚本与快照属 gitignored 临时物, 判别法落在坑档。
- ⚠ **本轮归属更正**: 用户原话「标题栏颜色与其余部分难区分」指的是**列标题行**, 上一条基线
  (26-10-05-0542) 把它记成顶栏。顶栏那处是排查途中实测出的**同款**缺陷、经用户同意保留,
  但**不是用户报的那个** —— 两处缺陷都在, 修法同源, 均已落守阵。
- Linux 侧本轮未重测 —— 改动为纯前端静态资源 + 测试, 无平台分支; 下次 `test.linux` 自然复核。
