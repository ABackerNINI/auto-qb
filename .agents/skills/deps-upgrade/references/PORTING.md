# PORTING — deps-upgrade(自制: 依赖巡检与抬升)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | `project/deps.toml`(watch 条目/`[joint]` 联动清单/`[[support]]` 支持矩阵/bump 白名单)+ `project/impact-map.md`(依赖盘点/联合分析 runbook/落盘口径) —— 项目事实单点, **移植 = 只替换 `project/` 目录**(schema 见 SKILL.md「project/ 目录(移植边界)」) |
| 配置键 | `<skill>/config/project.toml` `[user_agent] value`(HTTP User-Agent 项目标识, 计划 26-11-17-0010 S11 批9b 外置 —— 缺省回落通用 `deps-upgrade/1.0 …` + stderr 提示, 非静默); deps.toml `[paths]`(lockfile/pyproject 路径, 默认 `uv.lock`/`pyproject.toml`); 检测脚本只读无状态、硬编码零项目词 (本项目实例值在本仓两份配置里) |
| 可选守卫 | 无 |
| 其它 | 被测对象: 项目的 `uv.lock` + `pyproject.toml`; 网络(PyPI/GitHub API, 单源失败标 `[unreachable]` 不炸整体); 巡检决策消费项目的 task id(本项目实例: `test.full`/`env.sync`)与 memory-bank(`kb.new report`/`kb.wrap`) |

- **新项目绿地**: 拷 skill + 照 SKILL.md schema 新写 `project/` 两件。
- **开发中途存量(重点)**: 从现有 lockfile/pyproject 盘点依赖起稿 `project/deps.toml`(watch 型逐个挑、pin 型默认全扫), 支持矩阵留待首轮分析回填 —— 联合分析 runbook 模板照 `project/impact-map.md` 结构填。
