# PORTING — scope-guard(自制: 范围守卫, 纯协议)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 无 —— 单文件协议(仅 SKILL.md), 零脚本零数据件 |
| 配置键 | 无 |
| 可选守卫 | 无 |
| 其它 | 唯一外部依赖 = create-issue skill(入池动作, `kb.new issue` task id); 判据表里"属于本次计划"的对照物是项目自己的计划/档案面(memory-bank `tasks/`/`plans/`, 随 KB 走) |

- **新项目绿地**: 拷 SKILL.md 即生效, 无任何配置动作。
- **开发中途存量(重点)**: 同样零配置; 只确认搭档 create-issue 与 kb 命令包已就位(入池走不通时本 skill 的"默认入池"出口会卡)。
