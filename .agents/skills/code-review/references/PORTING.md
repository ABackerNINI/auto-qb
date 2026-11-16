# PORTING — code-review(自制: 分批评审)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 无自有数据件; 消费 memory-bank KB(收尾回写 `pitfalls/`、评审记录入任务档案) |
| 配置键 | 本 skill 无自有配置; 机械面全在 review 包(`review.pack` / `review.check` task id, 引文校验与基哈希口径单点 `review_content.py`); **存量评审**的项目数据 = `.commands/review/lane.toml`(批次矩阵/分支策略, 缺失 = 引导性报错) |
| 可选守卫 | `check_review_trace.py` 提交闸门(挂 my-commit-flow, Review trailer 强制; 无待评改动即静默) |
| 其它 | 前置依赖: commands 引擎 + review 包 + my-commit-flow 包(pack 前置 sync/ship.gate) + memory-bank KB; 自查清单引用项目红线面(本项目实例: `config.yml`/`auto-qb-data/`, 目标项目换自己的红线) |

- **新项目绿地**: 轨道装好后按 SKILL.md 走, lane.toml 只做存量评审才建。
- **开发中途存量(重点)**: 填 lane.toml 批次矩阵(按现状目录划路线, globs 宁缺勿滥) → 生成 manifest 冻结基线 → 逐批派只读评审 —— 启用路径详版 = runbook 双场景 B「存量评审 lane 用法」。
