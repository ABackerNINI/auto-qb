# 3118 —— webui 重复代码修复轮(报告 26-10-11-0033 §18/§19, 7 条 issue)执行基线

> 摘要: 用户「修复 webui 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」→ 追问拍板「新建修复轮任务档案 + 先做低风险 7 条」。按报告 §18(R15 路由层)/ §19(R16 表现层)认领 webui 10 条 refactor issue 中的 7 条并修完(virtual-tracker-prefix / status-payload / sidecar-dir / hr-route-guard / cmd-pair-handlers / bulk-receipt / seed-view-restate), 另 3 条(partial-publish 热路径 merge / cross-layer 常量 / route-cmd 表驱动)按拍板留 `Open` 只登记。全程**行为逐字不变**(日志文案/状态码/响应字段一字未改), 五条新守阵均过红验。数字相对上基线(`26-10-11-0354`)+5 = 新增守阵条数, 无回归信号。
> 基线时间: 2026-10-11 16:10

**Refs:** memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 `727b72e2`→`c0038049`, 快进 17 笔; 工作树含本轮改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3118 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**

| 面 | 语句 | 未覆盖 | 分支 | partial | 覆盖率 |
|---|---|---|---|---|---|
| TOTAL | 16586 | 153 | 5696 | 137 | 99% |

- 耗时: 29.15s(单次采样, 区间口径见 `testing/baseline.md`)
- 新增守阵 5 个测试函数(逐条红验通过): `test_seed_view_no_member_view_restatement` / `test_api_status_and_state_share_status_payload` / `test_web_sidecar_dir_single_point` / `test_virtual_tracker_prefix_single_point` / `test_hr_route_guard_single_point`
- Linux (WSL 沙箱) 本轮未重测 —— 改动全在 Windows/Linux 同构路径(纯 Python 重构 + 静态守阵), 无平台分支。

## 包内脚本测试

- 本轮未触碰 `.commands/` 与 `.agents/skills/commands/`, 未跑 `test.pkg`; 提交闸门按 match 规则自判。
