# 5127 passed + 2 skipped(根); 覆盖 TOTAL 23893 stmts / 212 miss / 8158 branches / 167 partial / 99% —— 收口 code review 制度化入库前全量

> 摘要: 收口 code review 制度化(code-review skill + review 命令包 + 协议挂钩)入库前全量
> 基线时间: 2026-11-04 07:04
**Refs:** memory-bank/tasks/26-11-04-memory-bank-code-review.md

## 验收数字

- `commands run test.full` 实测(2026-11-04 08:25, 158.9s, 收口评审实施 + 二轮评审修复 + review 包测试文件重写后复测): **5127 passed + 2 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 23893 stmts / 212 miss / 8158 branches / 167 partial / **99%**
- 口径注记: 首测(挂钩件守卫未修时)5124 passed + 3 failed 且覆盖率闸门红(98.78%) —— 3 failed 全为本任务挂钩件的生成索引过期与认领链单向(修复: `kb.index` 重建 + 计划 doc-refs 改仓库根相对路径), 复测一次性绿; 三次 TOTAL 表逐位一致, 覆盖率红绿差与那 3 个失败测试的执行路径耦联, 非本任务 src 改动(本轮 `src/` 与 `tests/` 零改动)。07:04 与 08:25 两次的用例数/TOTAL 完全相同, 差异仅在 review 包测试文件(不在 `tests/` 收集面)被重写后复验。

## 本改动面

- 新增 `.agents/skills/code-review/SKILL.md`: 八节收口评审规程(触发豁免/评审包/派遣三件套/产出裁决/16 条 checklist/留痕/降级)
- 新增 `.commands/review/` 包: `config.toml`(review.pack / review.check 两 task)+ `scripts/review_pack.py`(评审包生成与发现引文校验, 二轮加固后含根外拒绝/输出单行化/latin-1 兜底等 11 处)+ `scripts/test_review_pkg.py`(27 例)
- 挂钩: `.agents/skills/memory-bank/SKILL.md`(收尾 DoD 第 0 步收口评审 + 会话开始子代理同步豁免句)、`AGENTS.md`(收尾 bullet 路由句 + 同步条目子代理豁免句 + 守卫指针改 `test_memory_bank_*.py` + 两处「5步」去数字)
- sync 豁免改全(二轮评审发现治本层未闭环): `memory-bank/pitfalls/git/sync-pull.md`(摘要+判别)、`memory-bank/pitfalls/kb/request-boundary.md`、`memory-bank/conventions/collaboration.md`、`.github/instructions/ai-lib.md`(该文件既有「5步/死守卫路径」漂移一并修正)
- 计划/档案: `memory-bank/plans/26-11-04-0554-plan-memory-bank-code-review.html`(R1: 二轮指路修正 + doc-refs 修认领链)、`memory-bank/tasks/26-11-04-memory-bank-code-review.md`(R1)
- 生成物索引(`tasks/_index.md` 等)由 `kb.index` 重建; `src/` 与 `tests/` 零改动
