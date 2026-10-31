# 4304 passed + 10 skipped —— 快照 _find_repo_root 判据加 .git/HEAD 有效性校验

> 摘要: 快照 _find_repo_root 判据加 .git/HEAD 有效性校验
> 基线时间: 2026-10-31 22:01

## 验收数字

- `commands run test.full` (2026-10-31 21:59, 137.07s): **4304 passed, 10 skipped**, 覆盖率 TOTAL 21812 stmts / 99%(较上基线 +1 passed / +6 stmts = 同步进来的 926b66c3 组命令空组回执新用例, 与本改动无关)。
- `commands run test.pkg` (2026-10-31 21:5x, 56.1s): **188 passed** —— 本改动的直接验证面(.commands 包脚本套件, 全量测试收不到); 含 `_find_repo_root` 四例: 真标记 walk-up / worktree 文件命中 / 空壳 `.git` 不算仓库(26-10-31 事故回归阵) / 仓库外 None。

## 本改动面

- `.commands/my-commit-flow/scripts/_snapshot.py`: `_find_repo_root` 判据分形态 —— `.git` 目录必须含 `HEAD`(空壳/半初始化不算仓库根, 26-10-31 家目录空 `.git` + R: 未挂载 TMPDIR 回落事故的根治), `.git` 文件(worktree 指针)保持直接命中; docstring 记事故与判据。
- `.commands/my-commit-flow/scripts/test_snapshot.py`: walk-up 用例改真标记, 新增 worktree 命中与空壳豁免两例, 头部「## 测试计划」SnapshotUnitTest 行同步。
- 立档 `tasks/26-10-31-test-snapshot-git-marker-validity.md`(Status Done)。
