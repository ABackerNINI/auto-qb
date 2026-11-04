# 5146 passed + 2 skipped(根); 覆盖 TOTAL 23946 stmts / 210 miss / 8188 branches / 164 partial / 99% —— 提交后复审修复入库前全量

> 摘要: 收口 code review 机制提交后复审(27+6+1 条发现)修复完成后全量
> 基线时间: 2026-11-04 09:14
**Refs:** memory-bank/tasks/26-11-04-memory-bank-code-review.md

## 验收数字

- `commands run test.full` 实测(2026-11-04 09:14, 140.5s, 提交后三面复审 + 复查轮修复全部完成): **5146 passed + 2 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 23946 stmts / 210 miss / 8188 branches / 164 partial / **99%**
- 口径注记: 用例数与 TOTAL 比上一条切片(26-11-04-0704)上升, 原因是提交时 rebase 合流了远端 16 笔提交(带入新测试面); 本任务自身 `src/` 与 `tests/` 零改动。review 包自测 35 例不在 `tests/` 收集面(testpaths=tests), 由 `test.pkg.scoped` 单收, 不计入本切片。

## 本改动面

- `.commands/review/scripts/review_pack.py`: 提交后复审修复 —— 恢复 `-c core.quotepath=off`; diff 归因改 hunk 状态 + `+++ b/` 头(含空格路径尾随 TAB 用 `rstrip("\t")` 剥掉); 红线/警告匹配改子串(与提交闸门同口径); git 启动失败按 rc=2 收口; 统一 `file`/`quote`/`line` 类型校验与输出单行化。
- `.commands/review/scripts/test_review_pkg.py`: 用例 27 → 35, 修掉两处恒真断言(大 diff 分档改独立无敏感仓库; `+++` 头用例先 `git add`), 补字段类型/坏 TOML/尾斜杠规则/空文件/默认 root/提交后无后缀/非仓库 cwd, 归因与文件清单改精确元素断言。
- `.agents/skills/code-review/SKILL.md`: 豁免优先于阈值; 复查轮 `--base` 取上一轮基线; 非ASCII 条去掉假的「提交闸门已兜底」; schema 路径改实路径。
- sync 豁免收窄与统一: `AGENTS.md`、`.agents/skills/memory-bank/SKILL.md`、`.agents/skills/deps-upgrade/SKILL.md`、`.github/instructions/ai-lib.md`、`memory-bank/conventions/{collaboration,process}.md`、`memory-bank/pitfalls/git/sync-pull.md`、`memory-bank/pitfalls/kb/request-boundary.md` —— 只读评审子代理豁免、可写子代理不豁免; 术语统一为「自检锚(派遣时 HEAD)」, 与「基线(diff 起点)」分开。
- `memory-bank/tasks/26-11-04-memory-bank-code-review.md`(R3 复审与复查轮记录)、`memory-bank/plans/26-11-04-0554-*.html`(§01/§03/§09 术语与事实更正)、生成物索引(`kb.index` 重建)。
