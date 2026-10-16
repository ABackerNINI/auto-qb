# GitHub 镜像 develop 同补丁分叉

> 摘要: 镜像远端 develop 领先 N 笔 ≠ 有新内容 —— 可能是与本地某笔**同补丁不同 SHA** 的重复件(双端各推了一份)。直接 merge 会撞出成片 add/add + content 假冲突。判据三件套: git cherry → patch-id → 逐文件 blob 比对; 证明同源后冲突全取我方, 合并树必须与 HEAD 零差异。
> 触发: GitHub, 镜像, 远端分叉, develop 领先, merge 冲突, add/add, 同补丁, 补丁等价, patch-id, git cherry, blob 比对, 取我方, FETCH_HEAD, ls-remote 真值

### 镜像同补丁分叉的判别与合并 (2026-10-16 实证: 06edcbcb ≡ 本地 9a80bd00)

- **触发**: 镜像远端 develop 与本地分叉, 想把它 merge 进来; 或 merge 撞出成片冲突但对方内容「看着全是自己这边的旧改动」。
- **判别**(实例: GitHub 侧 1 笔 / 本地侧 67 笔, merge-base cea6397a, 对方 10 个文件全部撞冲突或自动合并):
  1. `git cherry HEAD <对方sha>` —— 输出 `-` 前缀 = 该笔与本地某笔**补丁等价**(对方的 diff 本地已有);
  2. `git show <sha> | git patch-id` 两侧对比 —— 全等 = 同一份补丁(sha 不同只因双端各推 / rebase 分叉);
  3. 逐文件 `git rev-parse "<对方sha>:<path>"` 与孪生提交比对 blob —— 全 SAME = 对方树是本地历史的祖先态。
  孪生提交定位: `git log <merge-base>..HEAD -- <对方动过的任一文件>` 取命中的一笔。
- **处置**: 冲突**全取我方**(`git checkout --ours` + `git add`) —— 对方改动已含在我方演化史里, 取我方零丢失;
  生成物 _index 不必重跑生成器(见下方自证)。**完成后自证**: `git diff HEAD` 必须为空(合并树 == HEAD,
  即对方零新增); 非空 = 对方真有新内容, 回到判别重新取证, 不得凭「取我方」惯性继续。
  合并前照例先备份 .git(见 history-integration); fetch 后用 FETCH_HEAD + ls-remote 现查真值(refs/remotes/github/* 写入会被静默丢弃)。
