# PORTING — create-issue(自制: 计划外问题入池)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | issues 池目录 `memory-bank/issues/`(路径固定, 随 KB 骨架建); HTML 模板与脚本已并入 memory-bank skill(建件 `kb.new issue` 派生, 本目录无脚本) |
| 配置键 | 本 skill 无自有配置; 类型枚举(8 类)单点 = memory-bank skill `scripts/_common.py` 的 `TYPES`; 翻状态走 `kb.status`(词表校验同源) |
| 可选守卫 | 认领链守卫 `gen_doc_map --check`(认领后必须回填 `doc-refs` 反向声明; 显式挂载走 `kb.docmap`, 勿默认移植 —— runbook「可选守卫」清单第二条) |
| 其它 | 随整套 memory bank 走(2026-11-07 D2 拍板, 本 skill 不单飞); 判定"该不该修"的搭档 = scope-guard skill |

- **新项目绿地**: 随 runbook 清单表 #1 一并带走, 无独立动作; 首条 issue 用 `kb.new issue` 冒烟。
- **开发中途存量(重点)**: 项目已有 issues 目录则原样沿用(查重靠时间戳 slug 与 grep, 无索引可重建), 只需把建件/翻状态 task id 挂进 kb 包 —— 细节见 SKILL.md「可移植性」节与 runbook。
