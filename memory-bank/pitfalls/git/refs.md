# Git ref 核对

> 摘要: 提交后必查 ref 三处(只看 commit 输出会被骗); 本 shell 里 `refs/remotes/*` 的写入会被静默丢弃。
> 触发: 提交后核对, ref, packed-refs, 分支被回退, staged 暴增, 上游未设置, 领先落后算不出

### 提交后必查 ref 三处: `HEAD` == `refs/heads/<branch>` == packed-refs

- **触发**: 每次提交之后。
- **判别**: **只看 `git commit` 的输出会被骗** —— ref 更新可能被拦截层静默丢弃。
- **处置**: 用 `my-commit-flow/scripts/verify_ref.py` 核三处; 不一致按脚本打印的步骤修。

### 「分支 ref 被回退」的判别法: 提交后突然冒出成百上千 staged

- **触发**: 提交后 `git status` 里忽然出现大量 staged 文件。
- **判别**: **先别急着 stage/commit** —— 用 `git write-tree` 对比 `git rev-parse <刚才的提交>^{tree}`:
  一致说明工作区 / 索引完好, 只是**分支指针被回退了**, **改动一个字都没丢**。
- **处置**: `git format-patch -1 <sha> --stdout > 备份.patch` + `git update-ref refs/heads/tmp-xxx <sha>`
  建锚点防 GC, 再 `git reset --soft <sha>`。
  ❌ **不要**用 `git add -A` 去"解决"那批 staged(那会把回退的差异当成正常改动提交)。

### packed-refs 陈旧会导致核 ref 假红

- **触发**: `verify_ref.py` 报 packed-refs 与 HEAD 不一致。
- **判别**: 被 pack 过的分支更新时只写 **loose ref**(优先级更高), packed-refs 保留旧值直到下次 pack。
  先看 `HEAD` 与 `refs/heads/<branch>` 是否一致 —— **一致即落稳**。
- **处置**: 备份 `.git` 后 `git pack-refs --all`。
  ⚠ 不要靠 `update-ref` —— 它只写 loose, 治不了 packed-refs。

### 本工具 shell 里 `refs/remotes/<远端>/*` 的写入会被静默丢弃

- **触发**: `git fetch gitee` 之后, 预检连着报「上游(未设置)」+「没能算出领先/落后」。
- **判别**: fetch 会打印 `[new branch] develop -> gitee/develop`, 但 `git for-each-ref refs/remotes` 里
  **只有 `origin/*`** ⇒ 随后 `git status -sb` 显示 `[gitee/develop: gone]`、
  `git log HEAD..gitee/develop` 直接报 unknown revision。
  ⇒ **不是远端没了、也不是分支坏**。
- **处置**: 判领先/落后与"推没推上"一律走 `git ls-remote <远端> <分支>`, **不要依赖远端跟踪 ref**;
  `push.py` 走的正是这条路, 所以**推送本身不受影响** —— 那两行 WARN 可以放心跳过。
