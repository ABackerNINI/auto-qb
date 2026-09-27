# Git 历史整合 (merge / rebase / 重放)

> 摘要: 历史整合(merge/rebase/stash)曾因删除拦截层批量删 `.git/objects` 而被禁 —— 该问题 2026-09-25 已修复, **禁令解除**; 本文件保留作事故档案与恢复手册, 高风险历史整合前仍建议 `cp -a .git <备份>`。**同步一律 `commands run my-commit-flow.sync`(自动快进 / 分叉自动 rebase 保线性), 本文的手工同步配方已退役删除。**
> 触发: 落后主线要同步, 想跑 git rebase, git merge, 合并, 变基, .git 损坏, 事故恢复

## ✅ 状态: 禁令已解除 (2026-09-25)

拦截层根因已修复, rebase / merge / stash 恢复可用; 以下为事故档案与仍有效的判据/恢复手册 —— 高风险历史整合前照旧先 `cp -a .git <备份>`。

## 两条禁令 (已解除)

### ❗「非快进合并 + 工作区脏」会删掉整个 `.git` 对象库 (重大事故)

- **触发**: 工作区有未提交改动时做**非快进**合并。
- **判别**: git 2.55 在**非快进合并**时**无条件**调 `git stash create`, 工作区脏就要真写 stash 对象,
  而工具环境的删除拦截层会顺着这次写入把 `.git/objects/**` **批量删进回收站**(git 原生 unlink 绝不会走回收站)。
  实测矩阵: 非快进 + 干净 = 安全; **非快进 + 脏 = 必炸**(关沙箱 / 换 git / `merge.autoStash=false` 都无效);
  快进 + 脏 = 安全。
- **处置**: **合并前先把工作区弄干净**(先提交, 或把改动移出仓库); 高风险 git 操作前 `cp -a .git <备份>`。
  **记不住细节就记这句: 非快进 + 脏 = 必炸。**

### ❗❗ `git rebase` 在本工具 shell 里同样会毁 `.git`, 而且「干净工作区」也照毁

- **触发**: 落后主线, 想用 rebase 变基(2026-09-21 连续两次 + 2026-09-22 第三次, 共 3 次事故)。
- **判别**: **根因** —— 本机 git config 里有 **`rebase.autosquash=true`** ⇒ 每次 rebase 都被当成**交互式** rebase
  起 sequencer, 而 `core.editor` 指向 `code --wait` ⇒ 第一次报
  `error: could not mark as interactive: No such file or directory`, 事后 `.git/refs/heads/` 整个目录 +
  `.git/logs/` 被删、当前提交对象也没了; 第二次加了 `GIT_SEQUENCE_EDITOR=:` + `GIT_EDITOR=:` +
  `-c rebase.autosquash=false` 仍以 **SIGTERM** 收场, `.git` 只剩 `COMMIT_EDITMSG` 与 `FETCH_HEAD`。
  ⇒ 只要 rebase 报 `could not mark as interactive`, **立刻停手, 别重试**。
- **处置**: ~~禁用 rebase~~(旧环境处置, 已解除), 改用下面的"可用替代"。

### ❗ rebase 第三次事故形态不同: 判别法要放宽到"HEAD 读不出来"

- **触发**: 第二次重试(以为换掉 editor 就好了)。
- **判别**: `git rebase FETCH_HEAD` 报 `fatal: unable to read tree <刚提交的 sha>`, 随后 `HEAD` 变
  `bad object`、`git status` 直接 `fatal` —— 现场是 **`.git/objects/<新提交前两位>/` 整个目录不存在**
  (本次 `objects/83/`), 而 `refs/heads/develop` 内容与 `.git/rebase-merge/` 都还在
  ⇒ 拦截层删的是"刚写入的**对象**", 与 09-21 那两次(删 `refs/heads/` 整目录)**不是同一种形态**。
- **处置**: **只要 rebase 后 HEAD 读不出来, 就是对象被删了, 别再试第二条 rebase 命令。**

## 同步路径 (v3): 脚本化 —— 手工配方已退役

落后 / 分叉一律 `commands run my-commit-flow.sync`(自动 fetch + 快进; 分叉自动 rebase 保线性, 2026-09-28 拍板; 树脏/冲突给一行失败原因与步骤)。旧版本节的手工配方(移出改动 → 快进 → 施回 / `reset --mixed` 舞蹈 / 单提交 commit-tree 重放)是 rebase 禁令年代的绕行产物, 已删除 —— 它们的教训并入下列各条; 高风险历史整合前照旧先 `cp -a .git <备份>`。

### rebase 冲突落在"已被你迁走"的方法上: 取上游的**意图**, 不是它的**位置**

- **触发**: 历史整合时冲突块很大, 但其中大部分是自己迁走代码后上游又把原方法带回来。
- **判别**: 先 `git diff <我方基线> <上游> -- <冲突文件>` 看上游到底加了几行 ——
  冲突块 100 行可能只有 5 行是真改动。
- **处置**: 上游的改动**不能丢**(丢了等于静默回退); `git add` 之后、`rebase --continue` **之前**先跑一次全量测试。
  ⚠ 另: rebase 下 `-X theirs` = 正在重放的"**我的**提交"(与 merge 相反)。

## 通用教训与事故恢复

### 通用教训: 与 `my-commit-flow` skill 的建议冲突时, 以本机事实为准

- **触发**: 落后 + 脏, 想照 skill 的《最常见组合》节做(它写"**先提交 → rebase → 推送**")。
- **判别**: 那条对**普通环境**是对的, 但**本环境下 rebase 这一步必炸**(见上)。
  skill 是**跨项目通用资产**, conventions 规定不得往里写本仓库事实 ⇒ 这个冲突**永远不会在 skill 里被提示**
  (第三次事故就是照 skill 踩的)。
- **处置**: 执行者自己要在跑 rebase 前先读本条; 同步走脚本化路径(见「同步路径 (v3)」)。
  `fetch` / `add` / `commit` / `reset` / `push` 实测安全; 涉及历史整合的优先让用户在自己终端做。
- **复发**: 1 —— 2026-09-24 "让工作区变干净再 rebase"被原样搬进包内 `commit.py` docstring 与
  references/README(顺序写成"先提交再快进"); 为什么没命中: 没有任何机检扫包内文档;
  三处已订正为"先同步远端、后提交", 再复发就加 grep 闸门。

### 事故恢复: 成本取决于有没有 `cp -a .git` 备份

- **触发**: 已经炸了, 要复原。
- **判别**: 本次两次都靠 rebase 前的备份 **30 秒复原**(`HEAD` 与全部 10 个文件对象逐一 `cat-file -s` 校验通过)
  ⇒ **"高风险 git 操作前先备份 .git"这条不是形式主义。**
- **处置**: ①被删对象基本都在**回收站**(`$I` 偏移 16-24 是 FILETIME **UTC**, 偏移 28 起是 UTF-16LE 原始路径;
  内容在同名 `$R`); ②**还原后必须先删掉被一起还原的陈旧 `*.lock`**
  (`index.lock`/`HEAD.lock`/`AUTO_MERGE.lock`/`packed-refs.lock`/`objects/maintenance.lock`),
  否则任何 git 命令都报 `Unable to create '.git/index.lock'`; ③工作区文件成片消失但 HEAD 里还在 ⇒
  `git checkout -- <file>`; ④收尾 `git fsck --no-progress` 确认 0 broken link。

### 合并后(**快进也一样**), **未触及**的文件也可能整片从工作区消失(HEAD 与索引都还在)

- **触发**: 工具 shell 里跑 `merge` —— **`--ff-only` 快进同样会触发**, 不只是非快进; 规律是"一次性改写大量文件的检出"。
- **判别**: 两次实例, 共同点是**丢的都是本次改动之外的文件**:
  - 2026-09-22 **非快进**合并 W1–W3: 只报 1 处冲突, 提交后冒出 **12 条 ` D`**(`scripts/` 整目录没了)。
  - 2026-09-23 **快进**合并(`merge --ff-only`, 208 个文件变更): 冒出 **19 条 ` D`**, 而
    **被删文件 ∩ 本次改动文件 = 0**(`git diff --name-only <旧> <新>` 比对得出) —— 全是被改动之外的。
  - 两次 `git ls-tree HEAD <path>` 与 `git ls-files <path>` 都在 ⇒ **丢失只在工作区**, 提交与索引完好。
  - 症状: pytest **收集阶段**就崩(`FileNotFoundError`)或 `uv` 报文件占用 —— 极易被误读成
    "上游把文件删了"或"仓库损坏"而跑去改代码/改测试。**别改, 先按处置①判。**
- **处置**: ①判哪一侧丢(`git ls-tree HEAD` / `git ls-files` 都在 ⇒ 只是工作区丢);
  ②**全量核对存在性**(遍历 `git ls-files` 逐个查, 比只看 `git status` 更硬 —— 实例②靠它确认 1629 个文件零缺失);
  ③`git restore --worktree -- <路径...>` 从索引还原(**不动 HEAD、不动索引**, 比 `checkout --` 更窄);
  ④还原后**立刻复查** `git status --short`, 确认没有再次被删;
  ⑤`git fsck --no-progress` 确认 0 broken link(排除对象库受损这种更严重的情况)。
- **复发**: 1 —— 2026-09-23 快进后复踩(19 个文件)。**为什么没命中**: 本条上一版的标题写的是
  "**非快进**合并后…", 执行者读到的是一条"不适用于我"的规则, 于是没做预防性检查。
  **教训: 标题里的适用限定要写到事实的最宽边界, 别拿单次实例的形态去限定整条规则。**
