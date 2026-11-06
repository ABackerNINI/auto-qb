# 5467 —— 分批评审: 闸门 + skill 重写 + 报告/计划

> 摘要: 分批评审: 闸门 + skill 重写 + 报告/计划
> 基线时间: 2026-11-06 08:18
**Refs:** memory-bank/tasks/26-11-06-rule-review-batch-policy.md

## 验收数字

`commands run test.full` 实测(TMPDIR 须清空后跑, 见 pitfalls/testing/tmpdir.md):

- 汇总行: `5467 passed, 2 skipped, 1 warning in 190.75s (0:03:10)`
- 覆盖率: `Total coverage: 99.71%`(门槛 99.5%)
- TOTAL 表: 24538 statements / 57 miss / 8396 branch / 36 partial / 99%

## 本改动面

- 闸门: `.commands/review/scripts/check_review_trace.py`(新) + `.commands/review/config.toml`(`review.trace`) + `.commands/my-commit-flow/.my-commit-flow.toml`(闸门条目) + `commit.py`(消息路径 / 阶段标记注入) + `_pipeline.py`(`match=[""]` 恒命中)
- skill: `.agents/skills/code-review/SKILL.md`(整篇重写) + `.agents/skills/memory-bank/SKILL.md`(DoD 第 0 步) + `AGENTS.md`(收尾行、节号)
- 消息机检: `.commands/my-commit-flow/scripts/msg_check.py`(`Review`/`Review-Skip` 进标签集)
- 测试: `test_review_pkg.py`(+22: 12 纯判定 + 10 端到端) / `test_commit.py`(+3: 闸门守卫、空清单命中、msg_check 标签)
- 制品: 报告 `26-11-06-0723` / 计划 `26-11-06-0759` / 坑档 `pitfalls/testing/repo-snapshot-in-tree.md`
