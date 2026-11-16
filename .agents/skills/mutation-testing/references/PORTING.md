# PORTING — mutation-testing(自制: 变异测试定期审计)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 排期锚 issue(`issues/*-test-mutation-audit-standing.html`, 常驻 Open, 含覆盖进度总表)+ 每轮一条基线切片(`testing/baselines/`)—— 都属 memory-bank KB |
| 配置键 | skill 本体零配置零脚本; 全部机械面在 `.commands/mutants/` 包(config.toml + scripts) —— 该包深度项目绑定(本项目实例: Docker testbed 常驻容器 `auto-qb-testbed`), **原包不移植**, 目标项目照自身基建写自己的 mutants 包 |
| 可选守卫 | `check_mutation_anchor.py`(锚文件缺失即红, fail-closed —— 显式挂载走 `kb.anchor`, **勿默认移植**, runbook 可选守卫清单第一条; 没做变异审计的项目不需要) |
| 其它 | 运行依赖: mutmut(Windows 侧兜底 pytest-gremlins)+ 容器/隔离环境方案 + 存量测试套全绿基线; 流程约束与坑清单以 SKILL.md 与 pitfalls 为准 |

- **新项目绿地**: 通常最后接入 —— 先有全绿测试基线与容器方案, 再建 mutants 包与排期锚。
- **开发中途存量(重点)**: 从现状测试套挑定向目标包起跑(按包/按模块, 永不一把跑全 src), 三特殊依赖联动分析等复杂面按需才建 —— 审计四工位(锚/计划/执行/记录)分工见 SKILL.md 表。
