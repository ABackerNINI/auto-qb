# Git 同步上游 (fetch / pull / 镜像线)

> 摘要: `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒; 双 UI 镜像线何时该重放。
> 触发: git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, keep 分支, 镜像线

### `git status -sb` 的 ahead/behind 是上次 fetch 时的快照, 不会自己刷新

- **触发**: 判断"我是不是落后主线"。
- **判别**: 多 clone / 多 session 并行时几分钟内就可能落后 ⇒ 拿旧快照判断必然出错。
- **处置**: 判断与同步一律 `commands run my-commit-flow.sync` —— 自动 fetch + 快进 / 分叉自动 rebase,
  判据是 ls-remote 现查远端真值, 不读快照; 失败行自带原因与步骤。
  ⚠ 协作主线是 **Gitee 的 `develop`**, **不要用 GitHub 镜像判断进度**。

### 落后 + 树脏: 快进被拒的判别与处置(sync 失败行之后)

- **触发**: `my-commit-flow.sync` 失败行报「本地改动与远端新提交重叠」。
- **判别**: **卡点** —— `git diff --stat` 为空但 `git status` 仍显示 ` M` 且工作区文件比 blob 大 ⇒
  **是行尾不是内容**(行尾幽灵 `M`)。
- **处置**: 先提交或 stash 承载本地改动(脚本不代做清理), 再重跑 sync。
  行尾幽灵 `M`: `git add <file>` + `git reset -q -- <file>` 刷新索引视图即可 ff, 实测有效。
  ❗旧版「`git diff --output=备份.patch` 移出 → 快进 → 施回」补丁配方**已删除**(rebase/stash 解禁后由
  sync + stash/提交取代); 补丁路线的 PowerShell 编码事故记录见下条, 引以为戒。

### 双 UI 镜像线: 首选"以一方模板为基线重建"再回填专有部分

- **触发**: 两套 UI(星图 atlas / 棱镜 prism)的模板出现分叉, 想合并。
- **判别**: 实测两套模板 **86% 同构**; `keep/*` 孤儿标签是**留档**不是待合并分支。
  判这类线要不要合: `git merge-base --is-ancestor <关键重构提交> <旧线>` —— 不含关键重构就应**重放**。
- **处置**: 以一方为基线重建再回填专有部分; 重建后做**静态 class 覆盖检查**。
  ⚠ 重放提交时必须**逐文件核验**, 判定"跳过"的要写明理由并**登记缺口** ——
  整文件跳过会造成"CSS 已入库但模板没切"的两不管缺口(见 `web-ui/template-render.md`)。

### ❗PowerShell 里 `git diff > x.patch` 会把补丁按控制台编码转码, 中文内容不可逆损坏

- **触发**: 旧版「同步上游」补丁配方(已退役)的第 ① 步 `git diff > 备份.patch`(2026-09-22 实测, 工具 shell)。
- **判别**: PowerShell 的 `>` 是先解码再编码 —— git 的 UTF-8 字节被按控制台编码(本机 GBK)解码后写 UTF-16: 中文行变 mojibake 且出现 `?` 替换符(不可逆), 部分行被并进相邻行, 9 个 `diff --git` 头只剩 5 个; `git apply` 报 `corrupt patch` / `No valid patches in input`。本次错误在施回前被 `git apply` 拦下 —— 若直接施回会把 mojibake 写进工作区; 即便把 UTF-16 转回 UTF-8 也救不回内容。
- **处置**: 出仓补丁一律用 git 自带输出参数 `git diff --output=<路径> [<路径>...]`(字节原样, 不经控制台编码); 高风险同步前照例 `cp -a .git` 备份。本次靠会话内编辑记录逐文件重建, 重建后用 `git diff --stat` 与改前数字逐项对账(8 files, +82/-43)确认无缺漏后再提交。

### 收尾回写落在陈旧基线上 → 合并时 baseline/切片必撞 (多 clone 最热写点)

- **触发**: 多 clone 并行下收到「提交」, 直接按收尾 DoD 回写 (基线切片 / activeContext 切片 / 各 _index) 再提交 —— 开工时同步过, 但会话期间别的 clone 已推进 develop (2026-09-26 用户点名: "baseline 总是撞")。
- **判别**: 齐平与否交给 `commands run my-commit-flow.sync` 判(内部 ls-remote 现查远端真值, 不信 `status -sb` 快照), **不需要手工对比**; 撞车现场是 push 被拒后已分叉, `apply --3way` 在 baseline.md / 切片上报冲突 (两边都在文件尾追加)。
- **处置**: 收到「提交」先 `commands run my-commit-flow.sync`(自动合流, 落后即快进 / 分叉自动 rebase) → **然后**才收尾回写 → `commands run ship.commit`(内部同步 + 闸门 + 提交 + 内联推送, 一行契约)。流程单点: `.commands/my-commit-flow/references/pipeline.md`。
