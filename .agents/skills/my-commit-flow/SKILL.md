---
name: my-commit-flow
description: '本机/本仓的提交推送流水线(用户说"提交" = commit + push): 预检 → 闸门 → 逐路径暂存 → 提交并核对 ref 三处 → 推 Gitee 主线 → 尝试一次 GitHub 直连 → 查幽灵 diff。USE FOR: 用户说"提交"/"推送"/"推上去"/"commit"; 收尾要把改动落到主线时。DO NOT USE FOR: 判断改不改(见 scope-guard skill)、要不要入池(见 create-issue skill)、纯答疑。**适用范围有限**: 依赖本仓库环境(Windows 工具 shell 的删除拦截层、Gitee 主线 + GitHub 镜像双远端、9 worktree 并行), 拿去别的项目前先看「可移植性」一节(多数项自动探测, 红线清单与闸门要改 <skill-dir>/scripts/_ship_config.py)。'
user-invocable: true
---

# 提交推送流水线 (my-commit-flow)

用户说"提交" = **commit + 推送**，一次流程走完。本 skill 把散在 `AGENTS.md`「提交 / PR」、环境硬约束与 `pitfalls.md` 三条事故记录里的纪律，收成一条必经路径：**能机检的交给脚本，必须人判的写成停手点**。

- 协作口径（Gitee 主线 / GitHub 镜像允许滞后）单点在 `AGENTS.md`「提交 / PR」，本 skill 不重复定义，只给步骤。
- 事故判据（脏工作区 + 非快进合并、分支 ref 被回退）正文在 `pitfalls.md`，本 skill 只留判据与链接。

> **路径约定（重要）**：下文 `<skill-dir>` = **本 skill 所在目录**（本仓库是 `.agents/skills/my-commit-flow`），
> **不是仓库根**。脚本一律按 `<skill-dir>/scripts/<脚本>.py` 调用 —— 仓库根下那个 `scripts/` 是项目的
> （`gen_tasks_index.py` / 模拟器等），别在那儿找本 skill 的脚本。

## 为什么需要它

2026-09-20 的一次提交对照规则漏了四处：用了两次 `git add -A`（规则要求逐路径）、push 前没再 fetch（被拒，远端另有 5 个提交）、没尝试 GitHub 直连、没查幽灵 diff。根因不是"不知道规则"，而是**规则不在执行路径上**。历史代价：2026-09-19 非快进合并丢 318 个对象 + 全部 reflog；同期分支 ref 被别的会话回退，冒出 2133 个 staged。

## 流水线（七步）

| 步 | 做什么 | 判据 / 不通过怎么办 |
|---|---|---|
| **S0 认远端** | `python <skill-dir>/scripts/preflight.py` | 主线远端必须指向 `gitee.com`；上游必须是 `<main>/<branch>`。`git pull <remote>` 不带分支名**只 fetch 不合并**，分支名必须写 |
| **S1 同步** | 同上（预检自带一次 fetch） | 落后就先 rebase —— **工作区必须干净**；脏 → 先按 S3 提交或把改动移出。**push 前再跑一次预检**（`status -sb` 的 ahead/behind 是上次 fetch 的快照） |
| **S2 闸门** | 预检会列出该跑的命令 | Python → `yapf -i` + `uv run pytest tests -q`；issue 池 → `gen_issues_index.py --check`；平台相关 → WSL 复现。红了就停 |
| **S3 暂存** | `python <skill-dir>/scripts/commit.py --message-file <文件> <路径...>` | **逐路径**，脚本直接拒绝 `-A` / `.` / `*`；暂存清单里出现 `config.yml` / `auto-qb-data/` → 脚本拒提交；`想法.md` → WARN，确认是用户自己的改动才可入 |
| **S4 信息** | 自己写（脚本只校验文件存在） | 中文首行 + 空行 + 细节（动机 / 取舍 / 影响面 / 实测数字）。**规模数字必须提交那一刻实测**（`git show HEAD^:<f> \| wc -l`），不沿用会话中途量的旧值 |
| **S5 提交 + 核 ref** | `commit.py` 提交完自动调 `verify_ref.py` | `HEAD` == `refs/heads/<branch>` == loose/packed-refs，不一致 → 退出码 2 并给处置步骤（format-patch 留底 + update-ref 建锚点） |
| **S6 推送** | `python <skill-dir>/scripts/push.py` | **顺序固定**：先 Gitee（必须成功）→ 核对远端 ref == 本地 → 再尝试一次 GitHub 直连（禁代理 `-c`）。直连失败**只报一次**：不重试、不换代理、不改 SSH、不回滚 Gitee |
| **S7 收尾** | 查幽灵 diff + 回写知识库 | `git status --short` 看两列：`M ` = 已暂存待提交，` M` = **已提交过**但工作区又脏（格式化工具在提交后重排）。权威判据：`git log --oneline -1 -- <文件>` 有记录 **且** `git diff --quiet -- <文件>` 退出码 0。有幽灵 diff → 补一次"格式化，无行为变化"提交，不要改写已入库的提交 |

高风险动作前（rebase / 批量提交 / 修 ref）先整份备份 `.git`：`cp -a .git <备份路径>`。

## 停手点（脚本不代替你判断）

1. **需要 rebase / merge** —— 脚本只报"落后 N 个提交"并退出，不动手。脏工作区绝不做非快进合并。
2. **改动里混有他人/用户在途改动** —— 尤其是 `想法.md`；`add -A` 正是把这类改动混进提交的动作。
3. **staged 数量暴增（> 200）** —— 大概率是分支 ref 被别的会话回退，**不要**用 `add -A` 或全量提交去"解决"。
4. **ref 三处不一致** —— 按 `verify_ref.py` 打印的处置步骤走，先确认没有别的会话在操作同一个 `.git`。
5. **GitHub 直连失败** —— 报告一次就结束，镜像允许滞后。
6. **测试红 / 闸门未过** —— 不提交。

## 脚本

| 脚本 | 职责 | 退出码 |
|---|---|---|
| `<skill-dir>/scripts/preflight.py` | 只读预检（+ 一次安全 fetch）：远端 / 上游 / 落后 / 脏 / 红线 / 闸门 / staged 异常 | 0 可继续 · 1 有 STOP |
| `<skill-dir>/scripts/commit.py` | 逐路径 `add` + `commit -F` + 提交后自动核 ref | 4 参数/红线 · 5 git 失败 · 2 ref 不一致 |
| `<skill-dir>/scripts/verify_ref.py [sha]` | ref 三处一致核对 | 0 一致 · 2 不一致 · 3 staged 暴增 |
| `<skill-dir>/scripts/push.py [--skip-mirror]` | fetch → 推主线 → 核对远端 → 尝试一次镜像 | 0 主线成功 · 1 落后 · 5 主线失败 |

配置与探测工具在 `<skill-dir>/scripts/_ship_config.py`。

## 可移植性（哪些是探测的、哪些是写死的）

**运行期自动探测（不写死，换项目直接能用）**：

| 项 | 怎么探测 | 想覆盖怎么办 |
|---|---|---|
| 仓库根 | 从脚本目录向上找 `.git`（目录或 worktree 的 `.git` 文件），不按 skill 安装深度反推 | — |
| 分支 | 跟当前分支 | 配 `BRANCH`（如 `"main"`） |
| 主线远端 | 候选名 `("gitee", "origin")` 里第一个 **URL 含 `gitee.com`** 的（按 URL 特征而非名字，避开"origin 其实是镜像"的坑） | 配 `MAIN_HOST_MARK` / `REMOTE_MAIN_CANDIDATES` |
| 镜像远端 | 按 URL 含 `github.com` 找，找不到再退回 `REMOTE_MIRROR` 这个名字 | 配 `MIRROR_HOST_MARK` |
| 禁用代理的 `-c` | 从 `git config --get-regexp '^http\..*\.proxy$'` 读 key，**不写死 key 与端口**；没配代理就不加参数 | — |

**写死的都是项目特有项（换项目必须改）**：`RED_LINES` / `WARN_LINES`（红线与高危文件）、`GATES`（提交前闸门，含 create-issue 的 `--check`）、`LINUX_CHECK_HINTS`（平台差异关键词）、镜像策略（允许滞后、只尝试一次）。

## 反模式

- ❌ `git add -A` / `git add .` —— 会把他人或用户的在途改动混进提交；脚本已直接拒绝。
- ❌ 只看 `git commit` 的输出就当成功 —— 本 worktree 的 ref 更新可能被拦截层静默丢弃，必须核三处。
- ❌ 脏工作区直接 rebase / merge —— 非快进合并会触发 `git stash create`，拦截层会顺着这次写入批量删 `.git/objects`。
- ❌ 用几分钟前的 `git status -sb` 判断"与主线一致" —— 那是上次 fetch 的快照；多 worktree 并行时随时可能变。
- ❌ push 被拒后立刻 `--force` —— 先看清远端多了什么。
- ❌ GitHub 直连失败就重试 / 换代理 / 改走 SSH —— 直连本就不稳定，规则是"尝试一次，失败只报一次"。
- ❌ 提交消息里沿用会话中途量的规模数字 —— 必须在提交那一刻实测。
- ❌ 把"已提交但工作区又脏"误判成"没提交上" —— 看 `status --short` 的两列，别只看 `M`。
