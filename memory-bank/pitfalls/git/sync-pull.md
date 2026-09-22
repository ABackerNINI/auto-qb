# Git 同步上游 (fetch / pull / 镜像线)

> 摘要: `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒; 双 UI 镜像线何时该重放。
> 触发: git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, keep 分支, 镜像线

### `git status -sb` 的 ahead/behind 是上次 fetch 时的快照, 不会自己刷新

- **触发**: 判断"我是不是落后主线"。
- **判别**: 多 clone / 多 session 并行时几分钟内就可能落后 ⇒ 拿旧快照判断必然出错。
- **处置**: **push 前先 `git fetch`**; 分支落后主线时**先 fetch 再动手**, 否则会把别人已修好的问题重做一遍。
  真有重叠: ①`stash push -u` 留档 ②rebase 到主线 ③只把**主线没有的增量**重做 ④被取代的计划文档**必须加存档声明**。
  ⚠ 协作主线是 **Gitee 的 `develop`**, **不要用 GitHub 镜像判断进度**;
  ⚠ 本 shell 里 rebase 禁用(见 [history-integration.md](history-integration.md)), 第 ② 步改走 `merge --ff-only`。

### 同步上游(未提交改动 + 行尾导致快进合并被拒)的安全流程

- **触发**: 本地有未提交改动, 想同步上游。
- **判别**: **卡点** —— `git diff --stat` 为空但 `git status` 仍显示 ` M` 且工作区文件比 blob 大 ⇒
  **是行尾不是内容**。
- **处置**: ①`git diff > 备份.patch` + 原文件另存 ②只对被改的跟踪文件 `git restore --source=HEAD -- <文件>`
  ③`git merge --ff-only origin/develop` ④`git apply --3way --ignore-whitespace 备份.patch`
  ⑤`.md` 的冲突基本是"两边各追加一段", **取并集**(`tasks/_index.md` 是生成物, 直接重跑
  `python .agents/skills/memory-bank/scripts/gen_tasks_index.py`)⑥`git add` 标记已解决后 `git reset` 变回未暂存。
  行尾那条的处置: 把文件强制成纯 LF 即可(**别急着 stash**)。

### 双 UI 镜像线: 首选"以一方模板为基线重建"再回填专有部分

- **触发**: 两套 UI(星图 atlas / 棱镜 prism)的模板出现分叉, 想合并。
- **判别**: 实测两套模板 **86% 同构**; `keep/*` 孤儿标签是**留档**不是待合并分支。
  判这类线要不要合: `git merge-base --is-ancestor <关键重构提交> <旧线>` —— 不含关键重构就应**重放**。
- **处置**: 以一方为基线重建再回填专有部分; 重建后做**静态 class 覆盖检查**。
  ⚠ 重放提交时必须**逐文件核验**, 判定"跳过"的要写明理由并**登记缺口** ——
  整文件跳过会造成"CSS 已入库但模板没切"的两不管缺口(见 `web-ui/template-render.md`)。
