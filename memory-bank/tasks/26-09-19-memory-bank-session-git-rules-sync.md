# 26-09-19-memory-bank-session-git-rules-sync — 会话协议与 git 口径统一 (开工先拉分支 + 提交即推送)

**Status:** Completed (全部入库, 最新 `4bb7f03`; 剩 GitHub 镜像滞后 3 个提交, 允许滞后)
**Started:** 2026-09-19
**Owner:** 本 worktree 会话 (auto-qb-clone2, 单会话连续实施)
**Plan doc:** (无 —— 用户指定规则 + 撞见的文档漂移, 未产出计划文档)
**Summary:** 用户要求「记录进 AGENTS.md: 开始工作前先拉取远程分支, 避免在落后的分支上工作」。落地时发现同一条会话协议有 **4 处 always-on 入口** (`AGENTS.md` / `.github/copilot-instructions.md` / `.agents/skills/memory-bank/SKILL.md` / `.github/instructions/ai-lib.md`), 只改一处等于其它三条路径下规则不存在 ⇒ 四处全改, 并把 memory-bank SKILL 的「会话开始 (3 步)」扩为 4 步。过程中撞见 `conventions.md` 仍写「🔴 绝对不要 push」与 `AGENTS.md` 现行「提交 = commit + 自动推送」矛盾 ⇒ 先入池 issue `26-09-19-2359-memory-bank-push-rule-drift`(Open), 用户拍板方案 A 后改为 **入口文件单点定义 + 知识库只留指针**, issue 转 **Fixed**。共 7 笔提交, 闸门 `uv run pytest tests -q` **1054 passed** 全程未变。

## 原始请求

> 记录进 AGENTS.md: 开始工作前先拉取远程分支, 避免在落后的分支上工作

后续指令: 「提交」(= commit + 自动推送, 2026-09-19 用户指定口径) → 「Please continue」(授权继续收口: 补 SKILL.md / ai-lib.md / conventions.md / activeContext.md, 并处理撞见的 push 口径漂移)。

## 思考过程与决策

- **为什么不是只改 `AGENTS.md` 一行就收工**: 本项目的规矩是「规则要出现在**决策时能看见**的地方」(2026-09-17 会话协议加固时就因"规则只在 applyTo memory-bank/** 的 instruction 里 ⇒ 决策时看不见"而返工过一次)。同一条「会话开始」规程在本仓库有 4 份副本, 改一处 = 其它三条入口下的 agent 完全不知道有新规则。⇒ 决定**一次改全**, 并在 `conventions.md` 里写明"共 4 处入口, 改规则要一次改全", 让下一个改规则的人不再漏。
- **`.agents/skills/memory-bank/SKILL.md` 是真正的执行入口**: `AGENTS.md` 明文写"完整规程(含任务档案模板)见该 SKILL.md", agent 会话开始/收尾时加载的是它。它原本的「会话开始 (3 步)」从"读 activeContext"起步 ⇒ 与新规则直接冲突, 不补则新规则对它无效。⇒ 3 步扩为 4 步, 拉取作为第 1 步。
- **`.codebuddy/skills/memory-bank/SKILL.md` 不要单独改**: 它与 `.agents/` 那份是**同一 inode 的硬链接**, 且 `.codebuddy` 不被 git 跟踪 —— 改 `.agents/` 那份即自动同步。当成两份分别改会立刻制造漂移。
- **知识库只留指针, 不复述全文** (本次确立并沿用了两次的心法): `conventions.md` 与 `activeContext.md` 只写「判据 + 回指 `AGENTS.md` + 共几处入口」。理由: 规则的第五、第六份副本必然各自演化 —— 本次撞见的 push 口径漂移就是活例子(2026-09-19 改了 `AGENTS.md`, `conventions.md` 自 2026-09-10 起没动过)。
- **撞见的 push 口径漂移为什么先入池而不是当场改**: 它是计划外缺陷, 按 scope-guard 只记录不改码; 且该条带 🔴 属用户 2026-09-10 亲自立下的强约束, 覆盖它需要用户授权。⇒ 走 create-issue skill 入池(含 5 处原文证据/行号、根因、A/B 两案), 用户拍板 A 后才动。
- **根因值得单记**: `AGENTS.md` 的冲突裁决链是 `代码 > memory-bank > README > 想法.md`, 它只对"代码事实漂移"有效; 本次冲突两边**都是文档**, 裁决链给不出方向 ⇒ 谁先被读到谁生效。⇒ 修的时候额外在 `AGENTS.md:126` 补一句"本条是提交/push 口径的**单点定义**, 优先于 memory-bank 里的历史表述", 把优先级写死。
- **提交流程全程守 git 红线**: 每次提交前 `git fetch origin develop` 核对落后; 需要 rebase 时一律**先 commit 让工作区干净再 `git pull --rebase`**(脏工作区 + rebase 触发 stash 会顺着本环境的文件删除拦截层批量删掉 `.git/objects`, 2026-09-19 事故已丢过 318 个对象)。6 次 push 里有 1 次撞上并发会话(落后 2) ⇒ 先 commit 后 rebase, 无冲突, sha `0811ac5` → `67b3828`。
- **GitHub 镜像**: 今天 6 次尝试, 3 成功 3 失败(连接重置 / 21s 超时 / `send-pack: unexpected disconnect`)。按规矩**失败只报告一次、不重试**, 交付以 Gitee 为准。

## 实现计划

1. `AGENTS.md`: 「会话协议 · 开始」加第 ① 步拉取; 「提交 / PR」的"开工先同步主线"升级为硬要求
2. `.github/copilot-instructions.md` + `.github/instructions/ai-lib.md` 两份 always-on 入口同步
3. `.agents/skills/memory-bank/SKILL.md` 会话开始 3 步 → 4 步
4. 提交 + 推送 (开工先校验不落后)
5. 撞见 push 口径漂移 ⇒ 入池 issue (不改码)
6. 用户拍板方案 A ⇒ 改 `conventions.md` 五处 + `AGENTS.md` 单点定义声明, issue 转 Fixed
7. `memory-bank/conventions.md` 与 `activeContext.md` 各补一条指针 (只留指针)
8. 立档本档案 + 重建 `tasks/_index.md`

## 子任务状态表

| # | 子任务 | 状态 | 产出 / 提交 |
|---|---|---|---|
| 1 | `AGENTS.md` 会话协议 + 提交/PR 两处 | ✅ | `72a45f9` |
| 2 | `copilot-instructions.md` 同步 | ✅ | `72a45f9` (同一笔) |
| 3 | memory-bank SKILL 会话开始 3 → 4 步 | ✅ | `738fe0d` |
| 4 | `ai-lib.md` 同步 (第 4 份入口) | ✅ | `67b3828` (rebase 后 sha) |
| 5 | `conventions.md` 补指针 | ✅ | `dc9a854` |
| 6 | push 口径漂移入池 | ✅ | `363458e` (issue Open) |
| 7 | 方案 A 修漂移 + issue 转 Fixed | ✅ | `a786a1f` |
| 8 | `activeContext.md` 定案口径补指针 | ✅ | `4bb7f03` |
| 9 | 立档 + 索引重建 | ✅ | 本档案 + `scripts/gen_tasks_index.py` |

## 进度日志

- **23:39** 收到"记录进 AGENTS.md: 开工前先拉取远程分支"。确认 `origin` = Gitee (协作主线), `git fetch` 左右各 0 不落后。
- **23:43** `72a45f9`: `AGENTS.md`「开始」改为 ①先拉取(`git remote -v` 确认远端 → `git pull --rebase <remote> develop`, 分支名必须写 → `git status -sb` 不落后) ②再读 activeContext; 「提交 / PR」的"开工先同步主线"标为硬要求并注明与 ① 同源。同步 `.github/copilot-instructions.md`(守卫用例把两者当一对校验)。守阵 8 passed。推 Gitee `81f5a47..72a45f9` ✅; GitHub 连接重置, 不重试。
- **23:50** `738fe0d`: 发现 SKILL.md 的「会话开始 (3 步)」仍是旧口径 ⇒ 扩为 4 步。核对 `HEAD` == `refs/heads/develop`; Gitee ✅, GitHub ✅(`fed62a8..738fe0d`)。
- **23:55** `67b3828`: `.github/instructions/ai-lib.md` 是第 4 份入口, 同步。提交时主线被并发会话推进 2 个 ⇒ 先 commit(`0811ac5`)再 `git pull --rebase` 无冲突 → `67b3828`。Gitee ✅ GitHub ✅。
- **23:58** `dc9a854`: `conventions.md`「Git 约定」补指针(不复述)。Gitee ✅ GitHub ✅。
- **23:59** 同一节紧邻的「🔴 绝对不要 push (2026-09-10)」与新规则矛盾被暴露 ⇒ 入池 `memory-bank/issues/26-09-19-2359-memory-bank-push-rule-drift.html`(Open, 5 处证据 + 根因 + A/B 两案 + 验收方式), `363458e`; Gitee ✅, GitHub 超时, 不重试。
- **00:05** 用户拍板方案 A ⇒ `a786a1f`: `conventions.md` 五处改为「以 `AGENTS.md` 为单点定义」+ 历史沿革(09-10 越界事故与"推送须经授权"的教训**保留**, 标"已被上面取代, 别照抄"); `AGENTS.md:126` 补"本条为单点定义, 优先于 memory-bank 历史表述"直击根因。验证: 全文搜四个关键词, 残留命中只剩 `conventions.md:9` 沿革句与 `:137`「已作废」句; 两入口答案一致; 1054 passed。issue 转 **Fixed**(meta + 封面徽标两处一起改), `_index.md` 由 `gen_issues_index.py` 重建。Gitee ✅; GitHub `send-pack: unexpected disconnect`, 不重试。
- **00:11** `4bb7f03`: `activeContext.md`「定案口径」补两条规则的指针(各会话开工第一件事读的是它)。守阵 8 passed。Gitee `a786a1f..4bb7f03` ✅; GitHub 21s 超时, 不重试。
- **00:15** 立档本档案并重建 `tasks/_index.md`。⚠ 立档时踩到一个守阵坑: 档案规范没写 `**Status:**` 的合法取值, 照其它档案的观感写成 `✅ 完成` ⇒ `test_memory_bank.py` 两条守阵同时红(缺合法状态行 + 索引分区不一致), 因为守阵正则只认 `In Progress|Pending|Completed|Abandoned`。改成 `Completed` 并重跑 `gen_tasks_index.py` 后才全绿。
- **00:20** `a85bb9c`: 把上面这个坑补进 `.agents/skills/memory-bank/SKILL.md` 的档案规范(枚举 + 失效表现), 免得下次立档再猜。守阵 8 passed, 全量 1054 passed。Gitee `a2256b5..a85bb9c` ✅; GitHub 21s 超时, 不重试(镜像累计滞后 5 个)。

## 涉及文件清单

| 文件 | 角色 |
|---|---|
| `AGENTS.md` | **规则单点定义** (会话协议 · 开始 / 提交 · PR) |
| `.github/copilot-instructions.md` | always-on 入口 2/4 |
| `.agents/skills/memory-bank/SKILL.md` | always-on 入口 3/4 (**真正执行入口**, 与 `.codebuddy/` 那份硬链接) |
| `.github/instructions/ai-lib.md` | always-on 入口 4/4 |
| `memory-bank/conventions.md` | 只留指针 (Git 约定 / 协作约定两节) |
| `memory-bank/activeContext.md` | 只留指针 (定案口径节) |
| `memory-bank/issues/26-09-19-2359-memory-bank-push-rule-drift.html` + `_index.md` | 漂移的 issue 报告 (Fixed) + 生成物索引 |

不涉及: `src/` / `tests/` / `config.yml` / `auto-qb-data/` —— 全程纯文档, 未动一行代码。

## 遗留

- GitHub 镜像滞后 3 个提交 (`363458e` / `a786a1f` / `4bb7f03`)。镜像允许滞后, 交付以 Gitee 为准; 网络好时一条 `git -c http.https://github.com.proxy= push github develop` 即可补上。
- 规则落点清单已写进 `conventions.md` 与 `activeContext.md`: 以后改会话协议 / git 口径要**一次改全 4 处入口**, 知识库与易变层只留指针不复述。
