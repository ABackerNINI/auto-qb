# 基线切片 26-10-05-0115 — kb.nav 筛选器持久化全量基线

> 摘要: 用户报「kb.nav 筛选器未保存在浏览器, 每次刷新重置」的修复后全量实测。核心 = 页面壳
> `nav_page.html` 新增筛选器 localStorage 持久化 (`mb-nav-filters`): 各筛选入口落盘、boot()
> 装载一次并回填受控控件 (搜索框 / 排序下拉); 还原时 `KNOWN_ST` 先并入 `statusSeeded` 台账 ——
> 否则刷新后首轮 `derive()` 把用户取消的已知状态又 `add` 回来 (与 2026-10-04「状态筛选器自动
> 重置」同源, 坑 pitfalls/web-ui/poll-reseed-filter.md), 且还原对 schema 校验 (非法值丢弃 /
> 空集回落默认, 坑 pitfalls/web-ui/ui-location-persist.md)。

> 基线时间: 2026-10-05 01:15
> 档案: memory-bank/activeContext/26-10-04-0952-kb-nav-page.md

**Refs:** memory-bank/pitfalls/web-ui/poll-reseed-filter.md · memory-bank/pitfalls/web-ui/ui-location-persist.md · memory-bank/testing/baseline.md

- 分支: develop @ 2223c853 (+ 本轮未提交改动: .agents/skills/memory-bank/scripts/nav_page.html / tests/test_kb_nav.py / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2534 passed + 4 skipped, 42.47s (引擎计 44.0s), 覆盖率 TOTAL 99%**
  (14868 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向单文件(tests/test_kb_nav.py): **20 passed**(4.25s, `--no-cov`) —— 16 既有 + 4 新增
- 相对上基线 (26-10-04-2256: 2530 passed + 4 skipped / 99% / 36.76s): passed **+4** —— 本切片新增
  4 条守阵(持久化骨架 / derive 不读写筛选器 / KNOWN_ST 播种 / 各筛选入口落盘); skip 集合不变(Windows 侧 4 条 POSIX 专属)。
- 运行时行为: Node 最小桩回放 `nav_page.html` 脚本 **12 项全绿** —— 无持久化默认 / 持久化+seeded 刷新不被
  derive 重播种 / 缺 statusSeeded 旧格式 / 存取 round-trip / schema 校验(非法值丢弃 · 空集回落默认 · 非布尔忽略)。
- 改动面: .agents/skills/memory-bank/scripts/nav_page.html(筛选器持久化)· tests/test_kb_nav.py(4 条守阵 + docstring 清单)。
