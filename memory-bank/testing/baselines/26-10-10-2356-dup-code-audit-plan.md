# 3111 —— 全仓重复代码审查分步计划立项基线

> 摘要: 用户要求「做一轮重复代码审查(用于后续重构, 增强一致性与减少维护点), 先写一个分步执行方案, 步骤拆细, 覆盖全仓含前端三皮肤」。本轮**只产出计划制品, 零代码改动**: 落盘单文件 dark HTML 计划 `plans/26-10-10-2333-plan-dup-code-audit.html`(四类口径 A 真重复 / B 分歧重复 / C 同一事实多表示 / D 表面相似, 27 轮分步清单 00–26, 每轮六步微步骤 S1–S6, 归档与验收), 命中立档阈值, 已立档 `tasks/26-10-10-backend-dup-code-audit.md`。
> 基线时间: 2026-10-10 23:56

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `f03b5d4a`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3111 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 57.4s, 其中跑测 54.96s)
- 增量明细(本轮真正新增, **全部是文档/知识库件, 无 `src/` 与 `tests/` 改动**):
  - `memory-bank/plans/26-10-10-2333-plan-dup-code-audit.html`(单文件 dark HTML 计划)
  - `memory-bank/tasks/26-10-10-backend-dup-code-audit.md`(立档)
  - `memory-bank/activeContext/26-10-10-2356-dup-code-audit.md`(会话切片)
  - `memory-bank/plans/_index.md` + `memory-bank/tasks/_index.md`(索引重建)
  - 本基线切片
- 已复核的机检(本轮相关): `test_docs_forms.py` 11 passed(计划 meta / 命名 / dark 主题 / 索引自洽); `kb.check` 主键纪律 / 认领链 / 回写措辞 / 日期守卫全过。
- 未纳入本轮(刻意不越界): 任何轮次执行(计划边界: 只定轮次不改码), 以及轮 00 的工具冒烟(pylint / jscpd 噪声阈值) —— 待计划拍板后另开会话执行。