# testing — 测试 / 冒烟 / 仿真

> **本文件是生成物, 不要手改** —— 由 `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 怎么跑全量、基线数字的单点、逐条测试约定、全部机械守阵的清单、helpers 基座、5000 种子仿真、浏览器冒烟与它的环境。
> **触发**: 测试, pytest, 跑全量, 基线, 覆盖率, 写测试, 守阵, 红验, helpers, 替身, 仿真, 冒烟, 浏览器, 断言

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [baseline-history.md](baseline-history.md) | 测试基线的**逐次增量流水**(最近在上), 每次增删用例都记一条 —— 用来回答"这个数字是怎么来的"。 | 基线为什么是这个数, 某条用例何时加的, 覆盖率变化, 历史增量 |
| [baseline.md](baseline.md) | 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** —— | 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上 |
| [browser-env.md](browser-env.md) | 冒烟用哪个浏览器、装在哪、版本怎么对齐、换机器怎么一条命令自检 —— 环境侧的全部事实。 | 浏览器, 冒烟环境, agent-browser, Playwright, chromium, NODE_PATH, 浏览器版本, 换机器自检 |
| [file-conventions.md](file-conventions.md) | 十条逐条约定 —— 从 docstring 清单、命名、平台固定, 到"不得产生真实系统副作用"与"不得依赖宿主环境能力"。 | 写测试, 加测试文件, 测试命名, 平台相关测试, monkeypatch, 副作用, 环境能力, 测试计划清单 |
| [guards.md](guards.md) | 全库**机械守阵**的汇总 —— 一条 = 守阵名 + 钉住的结论 + 怎么红验。新增守阵时登记到这里。 | 守阵, 静态守卫, 防回潮, 红验, 钉住, 加守卫, 守卫清单 |
| [helpers.md](helpers.md) | 全 Fake 测试基座的四个替身 + 本地假 qB 服务 + 四个最常用的构造函数 —— 写测试前必读。 | 写测试, helpers, FakeClient, FakeTorrent, FakeQbServer, make_manager, make_ctx, seed_store, 替身 |
| [run.md](run.md) | 跑全量的完整命令、工具 shell 必须设的 `TMPDIR`、耗时画像、WSL 侧复现 —— 以及"别并发跑"这类环境纪律。 | 跑测试, 全量, pytest, uv sync, TMPDIR, 覆盖率, 耗时, 并发, WSL, 图形化配置编辑器 |
| [sim-5000.md](sim-5000.md) | 独立 HTTP 仿真服务端 + 驱动器, 用于 5000 种子规模的安全 / 性能测试; 固化阈值与关键实测数字在此。 | 仿真, 5000 种子, sim_qb, sim_run, sim_baseline, 性能基线, 漂移, 首轮灌入, 任务吞吐 |
| [smoke.md](smoke.md) | 前端渲染逻辑只能靠真浏览器验 —— 桩服务 + 双 UI 断言脚本的用法、断言清单、以及断言设计的全部已知坑。 | 冒烟, 浏览器, 前端改动, ui_harness, ui_smoke, Playwright, agent-browser, 双 UI, 乐观 UI 断言, 红绿双验 |
