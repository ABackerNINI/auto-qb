# Git 同步上游 (fetch / pull / 镜像线)

> 摘要: 开工同步**无豁免** —— 问答/只读分析轮次也必须先同步; `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒(树脏场景两条出路: stash 配方或提交先行 —— 2026-10-04 起 ship.commit 提交先行, 旧「先提交是死锁」作废); 双 UI 镜像线何时该重放。
> 等级: L1
> 触发: git fetch, git pull, 同步上游, 落后, 只读轮次, 问答轮次, 开工同步口径, 行尾, 快进合并被拒, 树脏, 重叠, stash, 死锁, keep 分支, 镜像线

**Refs:** memory-bank/tasks/26-09-22-memory-bank-sync-rule-rework-check-started.md

### 开工同步无豁免: 只读分析轮次也必须先同步

- **触发**: 会话开工 —— **任何轮次**, 含只答问题 / 只做只读分析的轮次; 念头「先看完再同步」。
- **判别**: 没有豁免面 —— 任何轮次都在第一个动作前先同步; 落后基线上给出的只读结论(路由 / 口径 / 数字)
  是陈旧树的, 而多 clone 并行下几分钟就可能落后。口径单点: `AGENTS.md`「会话协议 · 开始」① 与黄金法则 7
  的「开工同步不受本条豁免」子条。
- **处置**: 第一个动作前跑 `commands run my-commit-flow.sync`, 结果行「已同步 <hash>」贴进回复, 然后才读 / 答;
  **禁止在落后的分支上工作 —— 只读分析同样禁止**。同步失败(树脏 / 冲突): **只读轮次贴失败行并停下, 不代做
  stash**(那是写操作); 执行轮次照失败行自带的两条出路走。该规则是多入口副本(`AGENTS.md` /
  `.agents/skills/memory-bank/SKILL.md` / `.github/instructions/ai-lib.md`), **改规则必须一次改全**。

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
- **处置**: **先看重叠/冲突是不是全在生成物上**（`_index.md` / `_doc-map` 这类可重跑的索引）——
  2026-10-03 起（计划 `26-10-03-1544`）sync 会**自动化解**：白名单（生成器 `--list`）→ 任取一侧 + 重跑
  → `--check` 自证，成功行带「自动重跑生成物 N 处」，**无需人工**。只要有一个手写文件参与（或白名单取不到 /
  重跑失败 / 自证红），才回落到下面的手工配方。
- **处置（手写文件参与时）**: **只走 stash**(脚本不代做清理), 再重跑 sync —— 配方: `git stash push -u` → `commands run my-commit-flow.sync` → `git stash pop` → 测试 → `commands run ship.commit`。
  ❗`stash push` 必须带 **`-u`**: 收尾产物里常有未跟踪新文件(新档案 / 新基线切片 / 新 pitfall), 默认 stash 不收, pop 后它们留在旧基线上且 sync 快进可能被拒; `-u` 一并收走, pop 时无冲突。
  ❗**`pop` 撞生成物冲突(both modified)时**(2026-10-04 实测): 该冲突**autoresolve 管不到**(三步化解接线在 sync 内部的快进/rebase 分支, 手工 stash pop 在其外) —— 处置: `git checkout HEAD -- <冲突生成物>` → 重跑 `commands run kb.index`(未跟踪新产物 pop 时已回工作树, 重建即全) → `git stash drop`(pop 冲突时 stash entry 保留, 解完手动 drop); **不要手工解冲突**。
  ❗**「先提交」曾是死锁, 2026-10-04 起已解**: ship.commit 翻转为**提交先行**(先提交后同步, 树净 rebase 恒可自动)
  —— 工作已完成待入库就直接 `commands run ship.commit`, 与远端的冲突改在 rebase 时暴露; 想先同步再继续手头
  工作才走上面的 stash 配方。sync 失败行自带两条出路(单点 `UNLOCK_STEPS`, `.commands/my-commit-flow/scripts/sync.py`), 照行内指引走即可。
  行尾幽灵 `M`: `git add <file>` + `git reset -q -- <file>` 刷新索引视图即可 ff, 实测有效。
  - 仓库根已有 `.gitattributes`(`* text=auto eol=lf`, 2026-10-02 起)对 blob 侧设防 —— 存量工作区一次性转 LF(层3, 暂缓)完成前本条仍适用。
  (旧版「`git diff --output=备份.patch` 移出 → 快进 → 施回」补丁配方已删除, 由 sync + stash/提交先行取代。)

### 双 UI 镜像线: 首选"以一方模板为基线重建"再回填专有部分

- **触发**: 两套 UI(星图 atlas / 棱镜 prism)的模板出现分叉, 想合并。
- **判别**: 实测两套模板 **86% 同构**; `keep/*` 孤儿标签是**留档**不是待合并分支。
  判这类线要不要合: `git merge-base --is-ancestor <关键重构提交> <旧线>` —— 不含关键重构就应**重放**。
- **处置**: 以一方为基线重建再回填专有部分; 重建后做**静态 class 覆盖检查**。
  ⚠ 重放提交时必须**逐文件核验**, 判定"跳过"的要写明理由并**登记缺口** ——
  整文件跳过会造成"CSS 已入库但模板没切"的两不管缺口(见 `web-ui/template-render.md`)。

### ❗PowerShell 里 `git diff > x.patch` 会把补丁按控制台编码转码, 中文内容不可逆损坏

- **触发**: 在工具 shell(PowerShell)里用 `>` 重定向导出 git 补丁 / 文本内容。
- **判别**: PowerShell 的 `>` 是先解码再编码 —— git 的 UTF-8 字节被按控制台编码(本机 GBK)解码后写 UTF-16: 中文行变 mojibake 且出现 `?` 替换符(**不可逆**), 部分行被并进相邻行; `git apply` 报 `corrupt patch` / `No valid patches in input`。
- **处置**: 出仓补丁一律用 git 自带输出参数 `git diff --output=<路径> [<路径>...]`(字节原样, 不经控制台编码); 高风险同步前照例 `cp -a .git` 备份。

### 收尾回写落在陈旧基线上 → 合并时 baseline/切片必撞 (多 clone 最热写点)

- **触发**: 多 clone 并行下收到「提交」, 直接按收尾 DoD 回写 (基线切片 / activeContext 切片 / 各 _index) 再提交 —— 开工时同步过, 但会话期间别的 clone 已推进 develop (2026-09-26 用户点名: "baseline 总是撞")。
- **判别**: 齐平与否交给脚本判(内部 ls-remote 现查远端真值, 不信 `status -sb` 快照), **不需要手工对比**; 撞车现场是 push 被拒后已分叉, `apply --3way` 在 baseline.md / 切片上报冲突 (两边都在文件尾追加)。
- **处置**: 收尾回写直接写在本地基线上, 与远端的合流**交脚本**: `commands run ship.commit` **提交先行**(闸门 → 暂存 → 提交 → 内部同步 rebase 树净恒可自动 → 推送) —— 回写件与远端 `_index` 的撞车由生成物自动化解兜底(重跑发生在含两边切片的树上, 结果天然是并集), 手写件冲突改在 rebase 里合流才停下要人; 独立 `my-commit-flow.sync` 只剩会话开工用途。流程单点: `.commands/my-commit-flow/references/pipeline.md`。
- **注**: 本条曾复发 12 次(2026-09-26~10-04), 两次机制修复后收口 —— ①生成物自动化解(2026-10-03, 计划 `26-10-03-1544`, 三步接线进 `run_sync()` 单点); ②ship.commit 提交先行(2026-10-04, 翻转编排消灭「同步发生在树脏时」这个共同温床)。复发流水已裁剪。
