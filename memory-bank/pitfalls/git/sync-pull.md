# Git 同步上游 (fetch / pull / 镜像线)

> 摘要: `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒(树脏场景只走 stash, 「先提交」是死锁); 双 UI 镜像线何时该重放。
> 触发: git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, 树脏, 重叠, stash, 死锁, keep 分支, 镜像线

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
  ❗**`pop` 撞生成物冲突(both modified)时**(2026-10-04 实测): 该冲突**autoresolve 管不到**(三步化解接线在 sync 内部的快进/rebase 分支, 手工 stash pop 在其外) —— 处置: `git checkout HEAD -- <冲突生成物>` → 重跑 `commands run kb.index`(未跟踪新产物 pop 时已回工作树, 重建即全) → `git stash drop`(pop 冲突时 stash entry 保留, 解完手动 drop); **不要手工解冲突**。
  ❗**「先提交」是死锁, 不是处置**: 提交入口 `ship.commit` 内部第一步就是这条 sync, 树脏没解除必再撞同一处
  —— sync 要你先提交 / ship.commit 要你先 sync, 两端互斥谁都进不去(2026-10-03 实测)。
  2026-10-03 起 sync / ship.commit 的失败行**自带这条解锁配方**(单点 `UNLOCK_STEPS`, `.commands/my-commit-flow/scripts/sync.py`), 照行内配方走即可。
  行尾幽灵 `M`: `git add <file>` + `git reset -q -- <file>` 刷新索引视图即可 ff, 实测有效。
  - **2026-10-02**: 仓库根已加 `.gitattributes`(`* text=auto eol=lf`)对 blob 侧设防 —— 存量工作区一次性转 LF(层3, 暂缓)完成后此类幽灵 M 应根除, 完成前本条仍适用。
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
- **复发**: 3(1 + 计划 26-10-01-2216 阶段1/阶段2 两度) —— 2026-10-01 (auto-qb-clone2): 收到「提交」时点已按本条 sync 过, 会话中途远端仍被并行 clone 推进(f0ddd486), `ship.commit` 首跑失败(重叠文件为生成物 `plans/_index.md`); 按失败行指引合流重跑成功, 无实际冲突。**为什么没命中**: 本条处置只保证「提交时点齐平」, 会话中途的推进属 sync 的固有窗口防不住 —— 本轮正是靠 ship.commit 内部同步 + 失败行拦下的; 处置无需改, 复踩代价 ≈ 一次重跑, 勿为消掉这次失败加手工预检。
- **复发** +2 —— 2026-10-01 (auto-qb-clone1, 同一计划阶段1/阶段2 的提交点): `ship.commit` 内部同步两度撞「远端前移 + 树脏」, 均按 `cp -a .git <备份>` → stash → sync → pop 预案**命中即化解**, 无冲突无损(数字以最终重跑的 test.full 为准); 处置照旧, 无需改。
- **复发** +1 —— 2026-10-02 (auto-qb-clone2, U1-b 未保存改动守卫提交点): 收到「提交」时 sync 报「本地 300f8aa5 / 远端 4a883385 重叠」, 按 `cp -a .git <仓库外备份>` → **`git stash push -u`** → sync(4a883385) → `git stash pop` 化解, 无冲突; `kb.index` 在新基线上重跑后再 `test.full` 2289 passed / 99%。**为什么没命中**: 同上一行 —— 会话中途的远端推进属 sync 固有窗口, 防不住, 处置无需改。
  ❗本轮补一条**未写进处置的细节**: stash 必须带 **`-u`** —— 收尾产物里通常有未跟踪新文件(新档案 / 新基线切片 / 新 pitfall), 默认 stash 不收未跟踪, pop 后新文件会留在旧基线上、且 sync 的快进可能因它们被拒; `-u` 一并收走, pop 时无冲突(远端不会新增同名文件)。旧做法「`git checkout --` 掉生成物索引再 sync」只对**可重跑的生成物**安全, 对未跟踪新产物不适用。
- **复发** +1 —— 2026-10-02 (auto-qb-clone1, 行尾统一 LF 层1/2/4 提交点): 会话开局 sync 过(0d286cc5), 收尾时远端已被并行 clone 推进至 a6b5b5b0(纯文档回写, 未触 src/tests), `ship.commit` 首跑失败行拦下; 按 `cp -a .git <仓库外备份>` → `stash push -u` → sync → pop 预案化解, tasks/_index.md 自动合并无冲突, 重跑提交成功。**为什么没命中**: 同上 —— 会话中途的远端推进属 sync 固有窗口防不住, 处置无需改。
- **复发** +1 —— 2026-10-03 (另一会话, `_copyText` 别名修复提交点): 远端 20545039(别的会话改 `tpl/drawer.html`)与本轮改动的**同一文件**重叠, sync 判「落后 + 树脏重叠」拒绝快进, 而 `ship.commit` 要求先 sync —— **双向死锁**; 按 `git stash push -u` → sync 快进 → `git stash pop`(两处改动上下文不重叠, 自动合并零冲突) → 测试 → 提交化解。**为什么没命中**: 前几轮复发都写「先提交或 stash」两条并列, 「先提交」这条实为死路(2026-10-03 实测)；当日已改**失败行自带 stash 解锁配方** + 死锁护栏提示(本条处置已同步改成只走 stash), 复发成本从「自己想明白」降到「照行内配方走」。
- **复发** +1 —— 2026-10-03 (auto-qb-clone5, 死锁提示修复自身的提交点): 提交时点远端已推进至 aec24d69, sync 首跑即报**新版的**「树脏挡路 …」失败行; 照行内配方 `cp -a .git /tmp/...` → `stash push -u` → sync → `pop`(零冲突) → 新基线上 `kb.index` + `test.full` 2408+3/99% + `test.pkg` 78 → `ship.commit` 一次走完, 提交 `7ef83e63`。**为什么没命中**: 同前 —— 会话中途远端推进防不住; **本条价值已变**: 配方现在由失败行自带, 这一步不再需要人自己想起 stash(同一天两条复发, 改提示前后各一次, 可直接对照)。
- **复发** +1 —— 2026-10-02 (auto-qb-clone1, 控制台编码坑档补写提交点): 会话内 18:24 sync 过(cfbfa712), 「提交」时远端已推进至 d354745b(纯文档 roadmap), sync 首跑报「本地改动与远端新提交重叠」; 按 `cp -a .git <仓库外备份>` → `stash push -u` → sync → pop 预案化解, 无冲突。**为什么没命中**: 同上 —— 会话中途远端推进属固有窗口, 防不住, 处置无需改。
- **机制修复 (2026-10-03, 计划 `26-10-03-1544`)**: 本条 7 次复发里,**绝大多数重叠文件是生成物索引**
  (`plans/_index.md` / `tasks/_index.md` / `baselines` 等 —— 多 clone 收尾都会重跑生成器, 于是同一批
  `_index.md` 在两边各自产生新版本)。这类冲突的正确处置一直是「任取一侧 + 重跑脚本」, 只是没接线到脚本里。
  现已把三步(白名单 → 重跑 → 自证)落在 `run_sync()` 单点, sync / commit / push 三条入口同时受益:
  **生成物冲突零人工**, 手写冲突行为逐字不变。⇒ 再遇「重叠」失败行, 先判断重叠是否全在生成物上。
- **复发** +1 —— 2026-10-03 (本 clone, 生成物自动化解计划的提交点): 开工 sync 过 `7ef83e63`, 实施期间远端连推 4 笔(webui 三下拉失焦收窗 / 流量图 P5a / P5b / 死锁复发登记)至 `181d90c3`; 提交时 sync 首跑报**新版**「树脏挡路 …」失败行, 照行内配方 `cp -a .git <仓库外备份>` → `stash push -u` → sync(`同步成功 181d90c3`) → `pop` **零冲突**(重叠仅手写件 `pitfalls/git/sync-pull.md`, 两边改动落在不同段)。**为什么没命中**: 同前 —— 会话中途远端推进属固有窗口防不住; 但本轮是**新机制第一次在真机验证保守默认**: 重叠含手写件 ⇒ 自动化解正确地**没有**动作(未猜意图), 直接给失败行 + 配方。
- **复发** +1 —— 2026-10-04 (本 clone, 跨组文件交叉计划轮提交点): 开工 sync 过 `926d1f66`, 首跑报「fetch 未落稳」(暂态), 重跑撞**新版**「树脏挡路」失败行(远端推进至 `908fbf28`); 照行内配方 `stash push -u` → sync → `pop` —— 本轮 **pop 撞了生成物冲突**(`plans/_index.md` both modified): 按 `checkout HEAD --` 该件 → 重跑 `kb.index` → `stash drop` 化解, 零残留落在新基线。**为什么没命中**: 三步自动化解接线在 `run_sync()` 单点, 只覆盖 sync 内部的快进/rebase 分支, 手工 stash pop 环节在其外 —— 配方行已补 pop 冲突处置, 后续照走即可。
