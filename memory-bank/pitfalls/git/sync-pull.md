# Git 同步上游 (fetch / pull / 镜像线)

> 摘要: `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒; 双 UI 镜像线何时该重放。
> 触发: git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, keep 分支, 镜像线

### `git status -sb` 的 ahead/behind 是上次 fetch 时的快照, 不会自己刷新

- **触发**: 判断"我是不是落后主线"。
- **判别**: 多 clone / 多 session 并行时几分钟内就可能落后 ⇒ 拿旧快照判断必然出错。
- **处置**: **push 前先 `git fetch`**; 分支落后主线时**先 fetch 再动手**, 否则会把别人已修好的问题重做一遍。
  真有重叠: ①`stash push -u` 留档 ②rebase 到主线 ③只把**主线没有的增量**重做 ④被取代的计划文档**必须加存档声明**。
  ⚠ 协作主线是 **Gitee 的 `develop`**, **不要用 GitHub 镜像判断进度**;
  (旧版注明"本 shell 里 rebase 禁用、第 ② 步改走 `merge --ff-only`" —— 该禁令 2026-09-25 已解除, 见 [history-integration.md](history-integration.md), 本流程可照跑。)

### 同步上游(未提交改动 + 行尾导致快进合并被拒)的安全流程

- **触发**: 本地有未提交改动, 想同步上游。
- **判别**: **卡点** —— `git diff --stat` 为空但 `git status` 仍显示 ` M` 且工作区文件比 blob 大 ⇒
  **是行尾不是内容**。
- **处置**: ①`git diff --output=备份.patch`(❗别用 `>`, 见文末新坑) + 原文件另存 ②只对被改的跟踪文件 `git restore --source=HEAD -- <文件>`
  ③`git merge --ff-only origin/develop` ④`git apply --3way --ignore-whitespace 备份.patch`
  ⑤`.md` 的冲突基本是"两边各追加一段", **取并集**(`tasks/_index.md` 是生成物, 直接重跑
  `commands run kb.index`)⑥`git add` 标记已解决后 `git reset` 变回未暂存。
  行尾那条的处置: 把文件强制成纯 LF 即可(**别急着 stash**)。
  (2026-09-22 复发 1 次, 新增更快的处置: **restore 到 HEAD 后仍可能有行尾幽灵 M, ff 仍被拒** ——
  `git add <file>` + `git reset -q -- <file>` 刷新索引视图即可 ff, 实测有效; 内容真有改动时仍走上面的补丁流程。)

### 双 UI 镜像线: 首选"以一方模板为基线重建"再回填专有部分

- **触发**: 两套 UI(星图 atlas / 棱镜 prism)的模板出现分叉, 想合并。
- **判别**: 实测两套模板 **86% 同构**; `keep/*` 孤儿标签是**留档**不是待合并分支。
  判这类线要不要合: `git merge-base --is-ancestor <关键重构提交> <旧线>` —— 不含关键重构就应**重放**。
- **处置**: 以一方为基线重建再回填专有部分; 重建后做**静态 class 覆盖检查**。
  ⚠ 重放提交时必须**逐文件核验**, 判定"跳过"的要写明理由并**登记缺口** ——
  整文件跳过会造成"CSS 已入库但模板没切"的两不管缺口(见 `web-ui/template-render.md`)。

### ❗PowerShell 里 `git diff > x.patch` 会把补丁按控制台编码转码, 中文内容不可逆损坏

- **触发**: 按本文件旧版「同步上游」流程第 ① 步照抄 `git diff > 备份.patch`(2026-09-22 实测, 工具 shell)。
- **判别**: PowerShell 的 `>` 是先解码再编码 —— git 的 UTF-8 字节被按控制台编码(本机 GBK)解码后写 UTF-16: 中文行变 mojibake 且出现 `?` 替换符(不可逆), 部分行被并进相邻行, 9 个 `diff --git` 头只剩 5 个; `git apply` 报 `corrupt patch` / `No valid patches in input`。本次错误在施回前被 `git apply` 拦下 —— 若直接施回会把 mojibake 写进工作区; 即便把 UTF-16 转回 UTF-8 也救不回内容。
- **处置**: 出仓补丁一律用 git 自带输出参数 `git diff --output=<路径> [<路径>...]`(字节原样, 不经控制台编码); 高风险同步前照例 `cp -a .git` 备份。本次靠会话内编辑记录逐文件重建, 重建后用 `git diff --stat` 与改前数字逐项对账(8 files, +82/-43)确认无缺漏后再提交。

### 收尾回写落在陈旧基线上 → 合并时 baseline/切片必撞 (多 clone 最热写点)

- **触发**: 多 clone 并行下收到「提交」, 直接按收尾 DoD 回写 (基线切片 / activeContext 切片 / 各 _index) 再提交 —— 开工时同步过, 但会话期间别的 clone 已推进 develop (2026-09-26 用户点名: "baseline 总是撞")。
- **判别**: 回写前 `git ls-remote gitee develop` 对比本地 HEAD (别信 `status -sb` 快照) —— 不齐平就是在陈旧基线上动手; 撞车现场是 push 被拒后已分叉, `apply --3way` 在 baseline.md / 切片上报冲突 (两边都在文件尾追加)。
- **处置**: 收到「提交」先 `commands run my-commit-flow.sync` 预检 → 落后按「同步路径」合并远端 → **然后**才收尾回写 → `ship.commit` (落后被 `--phase commit` 预检 STOP, 2026-09-26 起废除旧 WARN 放行) → `ship.push`。流程单点: `.commands/my-commit-flow/references/pipeline.md`。
