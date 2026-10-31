# 基线切片 26-10-05-0353 — kb.nav 状态徽章底色分层 (open/done 底色相近修复)

> 摘要: kb.nav 状态徽章改**三层底色口径** —— 台账 `.chip.st-*` 与控制台 `.rs.st-*` 共用同一套透明度阶梯
> (Open .24 / In Progress .16 / Done .14 / 出局态无底), 底 / 边 / 字三条通道同时区分。修两个根因:
> ①`.chip{color:var(--dim)}` 与 `.chip.st-*` 同特异性且写得更靠后, 把状态文字色整个盖掉 (改前实测五个
> 状态 chip 文字全是 `--dim` 灰); ②cyan `#56c8d7` 与 green `#7fc79a` 令牌亮度几乎相同(≈177 / ≈180),
> 同 12% 透明度下底色实测 `#16272b` / `#1b2624` 肉眼不可分。新增 1 条守阵。
> 基线时间: 2026-10-05 03:53

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md

- 分支: develop @ 40fd3355 (+ 本轮未提交改动: nav_page.html / tests/test_kb_nav.py /
  memory-bank/pitfalls/web-ui/layout-css.md 及其 `_index.md` / activeContext 切片 / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2554 passed + 4 skipped, 57.21s, 覆盖率 TOTAL 99%**
  (14871 语句 / 152 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向 (tests/test_kb_nav.py): **33 passed** —— 含本轮新增 1 条 `test_status_badge_colors_distinguishable`
  (状态文字色须落在 `.chip.st-*` 上 / Open 底色比 Done 实 / 控制台 `.rs` 与台账逐档对齐 / 出局态无底)。
- 相对上基线 (26-10-05-0324: 2553 passed + 4 skipped / 99% / 45.07s): passed **+1** = 本轮新守阵 1 条
  (语句 / 分支 / partial 三组数字与上基线**完全相同** —— 改动只在前端静态资源与测试, 不在 `src/` 的 .py);
  skip 集合不变(Windows 侧 4 条 POSIX 专属)。耗时 57.21s 落在近几条切片 40.5~57.9s 的噪声带内, 非回归。
- 改动面: `.agents/skills/memory-bank/scripts/nav_page.html`(仅状态色 CSS 两处: `.chip.st-*` 四条 +
  `.rs.st-*` 四条) · `tests/test_kb_nav.py`(+1 守阵 + 测试计划 docstring 同步) ·
  `memory-bank/pitfalls/web-ui/layout-css.md`(新增「状态徽章两态底色相近」条 + 「例外色靠书写顺序赢」复发 +1)。
  **数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动。**
- 机检 (headless Chromium, 非 pytest): 截徽章元素图采内侧填充像素, **同视图内**两两算 RGB 距离 ——
  台账 Open↔Done 由 ~7 提到 **33.3**, 控制台由 ~8 提到 **31.1**; 全部同视图配对数 ≥20 (判「分不出」的阈值)。
  复现脚本已随手清理, 判别法落在坑档 (截图采像素 + 同视图两两距离)。
