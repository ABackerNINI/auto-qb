# 4908 passed + 10 skipped —— full-checking 假失败自愈落盘修复后全量基线

> 摘要: full-checking 假失败自愈落盘修复后全量基线
> 基线时间: 2026-11-03 02:26
**Refs:**

## 验收数字

`commands run test.full` 实测(合流远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22532    152    7732    134    99%
4908 passed, 10 skipped, 3 warnings in 192.28s (0:03:12)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `src/auto_qb/rules/actions/full_checking.py`: 决策链 1.6 假失败自愈 `recheck_fails.pop` 后补
  `manager.ctx.state.save()`, 与 `checking_meta.bump_recheck_fail` 的写点即时落盘纪律一致。
- `tests/test_checking_group.py`: 新增 2 条用例(自愈发生即落盘 / 未发生不落盘)并同步头部「测试计划」清单。
- 本轮不涉及其它 `src/` 写点、配置、前端与知识库主题文档正文。
