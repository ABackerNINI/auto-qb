# 5621 passed + 2 skipped(根) —— 评审修复后终态基线(create-issue 融合 memory-bank)

> 摘要: 评审修复后终态基线(create-issue 融合 memory-bank)
> 基线时间: 2026-11-07 08:27

## 验收数字

`commands run test.full` 实测 (2026-11-07, 命令整体 147.1s):

```text
TOTAL                                                25497      5   8794     27    99%
5621 passed, 2 skipped, 1 warning in 145.17s (0:02:25)
```

- 相对上片 [26-11-07-0718](26-11-07-0718-memory-bank-issue-fusion.md) (5488 passed / miss+partial 93): passed **+133**, miss+partial **64** (5 + 27) 净额 **−29** —— 差异来源: ①本会话评审修复轮新增测试(e2e flip 步/双模板机读锚/CLOSED_KEEP 行为守阵/`set(TYPES)<=set(TIER_BY_TYPE)` 等 6+ 条); ②开工同步带入远端 20 笔新测试; ③上片数字录于修复与同步之前, 属快照时点差。pytest-cov 精确覆盖率行不在 silent_success 结论行内, 按裁定 A4 不转抄不推算。

## 本改动面

W1-W5 五波之上追加**评审修复轮**(三批评审 0 blocker / 1 major / 5 minor / 3 nit 全部当场修 + 终审 3 条留痕修正):

- 测试网: e2e 补 `kb.new issue → kb.status` 全链步(建件→翻状态→badge/meta/日志行/索引分区四断言); 注册表测试对双模板钉机读锚(BADGE_RE「状态」包裹层 + 「状态变更日志」h2+裸 ul) —— 顺手抓出并修正 light 模板 h2「状态史日志」→「状态变更日志」的锚漂移; `_index_section` 钉法替换近乎恒真的断言; 恢复 gen_issues_index 裁剪行为守阵(61→60+提示+归档全量)。
- 实现: flip_status 索引重建补 `except ValueError`([STOP] 指引同 new_doc 口径); new_doc `TIER_BY_TYPE.get` fail-fast + 注册表 `set(TYPES)<=set(TIER_BY_TYPE)` 守阵; issues 目录双口径收口(三候选探测退役, spec.dir 唯一落点); `_print_remaining` 按实际 slots 计数; 陈旧注释/死导入清理。
- 留痕: 前片 [26-11-07-0718](26-11-07-0718-memory-bank-issue-fusion.md) 的索引轮出记录按实库观测修正(plans 179→180 / tasks 270→271, issues 完结区 0 可见)并补分区序声明。
