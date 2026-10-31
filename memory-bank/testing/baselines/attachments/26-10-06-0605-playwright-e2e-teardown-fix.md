# 2662 —— 修 Playwright webServer 收尾挂死 (`e2e/global-teardown.mjs`)

> 摘要: 修 `dev.e2e` 在工具 shell 里"用例全 PASS 但命令永不退出"——真因是 `spawnSync` **带管道 stdio**
> 必 `EBUSY`(非"全线 EBUSY", 非句柄/杀软占用), 而 Playwright 停 webServer 的 taskkill 正是默认管道。
> 修法是 `e2e/global-teardown.mjs` 用异步 taskkill 抢在 Playwright 之前杀进程树。
> **本轮零 Python 改动 ⇒ pytest 数字与上一条基线完全相同 (2662 + 4 / 99%)**;
> 新增的实测在 e2e 侧: `dev.e2e` **14.8s / exit 0 / 4 passed (12.3s)**, 8137 无残留。
> 基线时间: 2026-10-06 06:05

**Refs:** memory-bank/activeContext/26-10-06-0508-playwright-e2e.md, memory-bank/pitfalls/testing/playwright-teardown.md

- 分支: develop @ **3a6e676c**(工作树: 本轮未提交改动 + `M TODO.md`)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2662 passed + 4 skipped, 覆盖率 TOTAL 99%**, 单次采样 **66.14s**(引擎 67.8s)
  - 语句 15952 / 未覆盖 166 / 分支 5444 / partial 144 —— 与上一条基线
    [26-10-06-0547](26-10-06-0547-playwright-e2e-merged.md)(15952 / 163~166 / 5444 / 143~144) **一致**,
    差值全在并行抖动区间内。
- **为何数字一条不差**: 本轮改的是 `e2e/*.mjs` · `playwright.config.mjs` · `.commands/dev/config.toml`
  的 note · `memory-bank/` 文档 —— **没有一行 Python**, 增删用例数为 0。记录本条是为了让
  "最新一条 = 单点事实源" 落在**当前树**上(0547 那条的树与本轮不同), 不是因为有数字变化。
- 旁证(同批核过):
  - `commands run test.quick` **2662 passed + 4 skipped / 47.90s**(与 test.full 的 passed 数一致)
  - `commands run test.pkg` **103 passed / 135.40s**(本轮改了 `.commands/dev/config.toml`, 必须跑)
  - `commands run dev.e2e` **4 passed / 12.3s, 命令 14.8s 退出 exit 0**(改前: 4/4 PASS 后挂死 4 分钟以上)
  - 端口占用负例: 8137 被外来服务占用时 `dev.e2e` exit 1 且报 `already used`, **外来服务未被误杀**
    (webServer setup 失败会中断任务链, `globalTeardown` 根本不会被注册)
  - `commands run kb.index` 重建 20 个生成物
