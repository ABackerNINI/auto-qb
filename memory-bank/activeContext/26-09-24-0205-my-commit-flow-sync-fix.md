# my-commit-flow 同步判据修复 — 预检崩行 + 假落后拒推
> 摘要: 外部走查发现两处潜在缺陷: classify_merge_probe 返回二元组导致检查表打印时 ValueError (expected 3, got 2); push.py / preflight.py 落后判据回退读 refs/remotes/gitee/* 跟踪 ref —— 本 clone 拦截层静默丢弃其写入, 陈年快照给出假"落后 5"拒推。已改为判据一律 ls-remote 现查远端 tip 对比本地 HEAD。
> 触发: my-commit-flow, 预检, push, 落后主线, refs/remotes, ls-remote, 合流预判, 假落后
> 最后活动: 2026-09-24 02:05

## 状态

**已完成** (本 clone, 待推送确认):

- `preflight.py`: classify_merge_probe 改返回三元组 (级别 / "合流预判" / 说明), 两处调用点解包不再崩;
  第 5 节删掉 `{MAIN}/{BRANCH}` 跟踪 ref 回退分支 —— 拿不到远端真值如实 WARN"无法验证", 不拿快照凑数;
  push 阶段 merge-tree 合流预判补 cat-file 对象在场守卫 (fetch 失败不再误报"预判会撞")。
- `push.py`: 推送前判据改 ls-remote 现查 + 对象库比对, 取不到远端真值 / 对象 → STOP 不推;
  删推送后两行 status -sb 输出 (跟踪 ref 被丢弃时 behind 是假象); 落后提示"先 rebase"改为 merge --ff-only (rebase 是红线)。
- `test_preflight.py`: +5 项回归 —— classify_merge_probe 四分支钉三元组; 源码扫描守阵禁止任何
  `--left-right` 判据引用 `{MAIN}/{BRANCH}` 快照。

## 实测 (提交时刻)

- 脚本自测 test_preflight.py: 39 项全过 (34 + 5)。
- preflight auto 闸门 5 条全过; test.full: 1201 passed + 1 skipped (8.49s), 与 testing/baseline.md 基线一致。
- README (.commands/my-commit-flow/) 口径核对: 早已写明"判落后一律 ls-remote、不读 refs/remotes", 代码此次才照做, 无漂移。

## 下一步

- 无遗留。外部报告者当时用裸 git push + ls-remote 顶替的路径, 现已由脚本自身落实。
