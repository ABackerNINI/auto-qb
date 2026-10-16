# 26-10-16-backend-global-traffic-monitor — 全局流量监视小工具 (TrafficMonitor 替代)

**Status:** In Progress
**Added:** 2026-10-16
**Updated:** 2026-10-16 06:01
**Summary:** 自写独立整机流量历史记录小工具(TM 替代): 独立进程+开机自启+TM 兼容 dat 原子落盘+阈值变化主动通知多 auto-qb 实例刷新 WebUI 历史图。计划 26-10-16-0541(S0–S10 逐步显式授权); S0 包骨架已落地。
**Refs:** memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html, memory-bank/pitfalls/testing/nested-pytest-config.md, memory-bank/testing/baselines/26-10-16-0601-global-traffic-monitor-s0.md
**Topics:** global-traffic-monitor

## 原始请求

用户要求自写独立监视全局流量的小工具: 独立于 auto-qb 主进程、开机自启、整机流量变化超阈值时主动通知 auto-qb、工具配置与自启开关进入 auto-qb WebUI 设置页、支持多个 auto-qb 实例同时接入。grilling 三轮 16 问收敛中用户两次纠正需求范围: ①工具定位 = TrafficMonitor 替代, 仅记录整机流量历史(非限速/provider 抽象); ②工具是共享服务, auto-qb 是其配置方与消费者之一。

## 思考过程与决策

全部决策见计划 §01 拍板结论表(监控口径/进程形态/自启/采集库/落盘格式/控制面/通知/配置主权/多实例/接收面/过渡共十项), 实施不得再自行变更; 确需变更按「计划改版 = 同文件内变更记录 + 抬 doc-updated」处理。黄金法则映射见计划 §07, 验收 E1–E6 见 §08, 风险对策见 §09。

## 实现计划

计划文档 S0–S10 共 11 步(包骨架→采样→落盘→控制面→通知→自启→auto-qb 配置面→接收面→过渡→守阵→验收), 每步带改动面、要点与出口判据。顺序与依赖见计划 §06: S0–S2 先出「记录+落盘」闭环(手动跑即可验证, 不等 auto-qb 改动); S3/S4 完成后与 S7 联调; S6 依赖控制面; S5 依赖 S6 开关入口; S8–S10 收口。每步需用户逐项显式授权, 「继续」不算。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 包骨架与依赖隔离 | Done (26-10-16-0601) |
| S1 | 采样器 sampler | Open |
| S2 | 落盘 storage | Open |
| S3 | 控制面 server | Open |
| S4 | 通知 notifier | Open |
| S5 | 自启 installer | Open |
| S6 | auto-qb 配置面 | Open |
| S7 | auto-qb 接收面 | Open |
| S8 | 集成与过渡 | Open |
| S9 | 守阵测试 | Open |
| S10 | 真机验收 | Open |

## 进度日志

### R1 · S0 实施 (2026-10-16 06:01)

用户指令「实施计划S0:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S0 的显式授权(S1–S10 不动)。开工同步 46d2ea11(快进)。

**落点**(纯新增, 零 auto-qb 文件触碰): `tools/global-traffic-monitor/` 11 文件 —— `pyproject.toml`(hatchling、src 布局、包名 global-traffic-monitor、入口 `gtm = gtm.__main__:main`、运行时依赖仅 psutil+filelock、dev 组 pytest、自带 `[tool.pytest.ini_options]`)、`src/gtm/` 八文件(`__init__`/`__main__` + config/sampler/storage/server/notifier/installer 六个模块均为 S1–S5 占位)、`README.md`、`tests/test_smoke.py`。

**出口判据全过**: ①独立 venv(`uv sync`;psutil 7.2.2 / filelock 4.2.0 / pytest 9.1.1 仅入工具 `.venv`)下 `gtm --version` 输出 `gtm 0.1.0`; ②隔离验证: 仓库根 `uv run python -c "import psutil"` 仍 ModuleNotFoundError —— 装/卸验证两环境互不污染; ③工具冒烟 4 条全过(版本一致性/模块可导入/--version/骨架提示)。根 `test.full` 回归数字见基线切片 `baselines/26-10-16-0601-global-traffic-monitor-s0.md`(工具测试不在根 testpaths 内)。

**实施期坑**: 工具目录内 `uv run pytest` 向上拾取仓库根 pytest.ini(rootdir 上移, addopts 的 `-n`/`--cov` 在工具 venv 不可用 → unrecognized arguments)。已在工具 pyproject 补 `[tool.pytest.ini_options]`(更近的配置优先), 坑档 `pitfalls/testing/nested-pytest-config.md`。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-0601, §04 增 R0 实施记录, 补 CSS color-scheme: dark 过 dark 守卫, doc-refs 补本档案) · activeContext 切片追加 R1 · 本档案新建(立档阈值 #4 命中: 已产出计划) · kb.index 重建 · 基线切片新建。

**行号基准**: S0 为纯新目录, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。未提交(待用户「提交」指令)。
