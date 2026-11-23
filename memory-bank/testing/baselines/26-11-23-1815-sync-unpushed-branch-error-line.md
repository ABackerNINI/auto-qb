# 7026 passed + 6 skipped(根) —— sync 无远端分支失败行纠偏后的基线

> 摘要: sync 无远端分支失败行纠偏后的基线
> 基线时间: 2026-11-23 18:15

## 验收数字

TOTAL                                                31412    108  11190     93    99%
7026 passed, 6 skipped, 4 warnings in 202.90s (0:03:22)

`commands run test.full` 实测(2026-11-23 18:15, Windows 本机, 覆盖率 99% 达标)。数字与上一条基线持平 —— 本轮改动全在 `.commands/my-commit-flow/` 包脚本与其测试(在 `testpaths(tests/)` 之外), 不计入全量 pytest 收集面; 包内脚本单独验: `commands run test.pkg.scoped -- .commands/my-commit-flow/scripts/sync.py .commands/my-commit-flow/scripts/test_sync.py` 235 passed, 另 `test_sync.py` 单跑 33 passed / `test_commit.py` 72 passed。

## 本改动面

- `.commands/my-commit-flow/scripts/sync.py`: 新增 `remote_sha_probe()` 把 `ls-remote` 的 rc 带出来, `run_sync()` 据此分 `absent`(rc=0 无 `refs/heads/<branch>` → 远端无此分支) / `unreachable`(rc≠0 → 离线) 两路; 前者失败行只报「远端 <remote>/<branch> 不存在(分支未推送, 非离线)」事实, 按用户口径不塞 `push -u` / 「联网后重跑」指引(本地分支大多不需要推送, 平时走 develop 同步); 只取 ref 真值的调用方(commit.py 旁证 / push.py 推后核对)仍走 `remote_sha()` 包装, 语义不变。
- `.commands/my-commit-flow/scripts/test_sync.py`: 新增 `test_remote_branch_absent_reports_unpushed`(真临时 bare 远端, 可达但无同名分支 → 断言新文案且 `push -u` 不出现), 离线守阵 `test_offline_reports_unreachable` 原样保留; 测试计划清单同步。
- `memory-bank/pitfalls/git/unpushed-branch-sync.md`: 摘要 / 判别段改现行文案(只报事实)并保留「旧文案(读历史档案用)」段; `push -u` 只留在「处置」段(真要推分支撞 sync-before-push 死锁时的出路); `commands run kb.index` 重建索引。
- 评审: 单批 62 行全能档, 只读评审零发现, `review.check` 0/0; 闸门 `commands run ship.gate` 全绿。零 `src/` 改动; `config.yml` / `auto-qb-data/` 红线未触碰。
