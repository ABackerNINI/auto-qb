---
name: my-commit-flow
description: '提交推送流水线(用户说"提交" = commit + push): 预检与同步 → 闸门 → 逐路径暂存 → 提交并核对 ref 三处 → 推主线 → 尝试一次镜像 → 查幽灵 diff。USE FOR: 用户说"提交"/"推送"/"推上去"/"commit"; 收尾要把改动落到主线时。DO NOT USE FOR: 判断改不改(见 scope-guard skill)、要不要入池(见 create-issue skill)、纯答疑。仓库根 / 分支 / 主线远端 / 镜像 / 代理均运行期探测; 项目特有项(红线文件、提交前闸门)集中在 <skill-dir>/scripts/_ship_config.py。'
user-invocable: true
---

# 提交推送流水线

用户说"提交" = **commit + 推送**，一次走完。把散落各处的提交纪律收成一条必经路径：**能机检的交给脚本，必须人判的写成停手点**。

> **路径约定**：`<skill-dir>` = 本 skill 所在的目录。安装位置因项目而异 —— **先用 Glob 定位**
> （`**/my-commit-flow/scripts/*.py`），别照抄路径，也别在仓库根的 `scripts/` 里找。

## 为什么需要它

提交是高频动作，而纪律通常散在好几份文档里，靠执行时想起来 —— **漏一条只是时间问题**，而漏掉的那条往往正是事后最难查的：提交没落稳、混进了别人的改动、把"已提交"误判成"没提交"。本 skill 的解法是把纪律摆到执行路径上：能机检的用脚本报出来，必须人判的到点停下报告。

## 流水线（七步）

| 步 | 做什么 | 判据 / 不通过怎么办 |
|---|---|---|
| **S1 预检与同步** | `python <skill-dir>/scripts/preflight.py` | 一张表报出：主线远端 / 上游 / 落后几个 / 工作区脏不脏 / 有没有红线文件 / 该跑哪些闸门。有 **STOP** 就先处理；**推送前再跑一次**（`status -sb` 的 ahead/behind 是上次 fetch 的快照，不会自己刷新） |
| **S2 闸门** | 跑预检列出的命令（测试、生成器 `--check`、格式化…） | 红了不提交 |
| **S3 暂存** | `python <skill-dir>/scripts/commit.py --message-file <文件> <路径...>` | **逐路径**，脚本直接拒绝 `-A` / `.` / `*`；红线文件（见 `_ship_config.RED_LINES`）直接拒交；高危文件（见 `WARN_LINES`）需人工确认 |
| **S4 信息** | 自己写 | 首行一句话说清"改了什么 / 为什么"，空一行后写动机 / 取舍 / 影响面 / 实测数字。**数字必须提交那一刻实测**，不沿用会话中途量的旧值 |
| **S5 提交并核 ref** | `commit.py` 提交完自动调 `verify_ref.py` | `HEAD` == `refs/heads/<branch>` == loose/packed-refs 三处一致；不一致按脚本给的处置步骤走，**不要只看 commit 输出** |
| **S6 推送** | `python <skill-dir>/scripts/push.py` | **顺序固定**：先推主线（必须成功）→ 核对远端 ref == 本地 → 再**尝试一次**镜像。镜像失败**只报一次**：不重试、不换代理、不改走 SSH、不回滚主线 |
| **S7 收尾** | 查幽灵 diff + 回写知识库 | `git status --short` 看两列：`M `(第一列) = 待提交，` M`(第二列) = 已提交过但工作区又脏。权威判据：`git log --oneline -1 -- <文件>` 有记录 **且** `git diff --quiet -- <文件>` 退出码 0。补一次提交，不要改写已入库的提交 |

脏工作区不 rebase / 不 merge（先提交或移出改动）；高风险操作前先备份 `.git`。

## 停手点（脚本只报，不替你判断）

1. **需要 rebase / merge** —— 脚本只报"落后 N 个提交"就退出。
2. **改动里混有他人 / 用户在途改动** —— 高危清单见 `_ship_config.WARN_LINES`。
3. **staged 数量暴增**（阈值见配置）—— 大概率是分支 ref 被回退，**不要**用 `add -A` 或全量提交去"解决"。
4. **ref 三处不一致** —— 按 `verify_ref.py` 打印的步骤走。
5. **镜像推送失败** —— 报告一次就结束，镜像允许滞后。
6. **测试红 / 闸门未过** —— 不提交。

## 脚本

| 脚本 | 职责 | 退出码 |
|---|---|---|
| `<skill-dir>/scripts/preflight.py` | 只读预检（+ 一次安全 fetch）：远端 / 上游 / 落后 / 脏 / 红线 / 闸门 / staged 异常 | 0 可继续 · 1 有 STOP |
| `<skill-dir>/scripts/commit.py` | 逐路径 `add` + `commit -F` + 提交后自动核 ref | 4 参数/红线 · 5 git 失败 · 2 ref 不一致 |
| `<skill-dir>/scripts/verify_ref.py [sha]` | ref 三处一致核对 | 0 一致 · 2 不一致 · 3 staged 暴增 |
| `<skill-dir>/scripts/push.py [--skip-mirror]` | fetch → 推主线 → 核对远端 → 尝试一次镜像 | 0 主线成功 · 1 落后 · 5 主线失败 · 6 取不到远端 ref |

## 配置与自动探测（`<skill-dir>/scripts/_ship_config.py`）

**运行期自动探测**（换项目直接能用）：

| 项 | 怎么探测 | 覆盖办法 |
|---|---|---|
| 仓库根 | 从脚本目录向上找 `.git`（目录或 worktree 的 `.git` 文件） | — |
| 分支 | 跟当前分支 | 配 `BRANCH` |
| 主线远端 | 候选名里第一个 **URL 含 `MAIN_HOST_MARK`** 的（按 URL 特征而非名字）；都不匹配则回退到候选里第一个存在的 | 配 `MAIN_HOST_MARK` / `REMOTE_MAIN_CANDIDATES` |
| 镜像远端 | 按 URL 含 `MIRROR_HOST_MARK` 找并**排除主线自己**；没有镜像也正常 | 配 `MIRROR_HOST_MARK` |
| 禁用代理的 `-c` | 从 `git config` 读 per-URL 代理 key，没配就不加参数 | — |

**项目特有项**（换项目要改这几个）：`RED_LINES` / `WARN_LINES`（红线与高危文件）、`GATES`（提交前该跑什么）、`LINUX_CHECK_HINTS`（平台差异关键词）、镜像策略。

## 反模式

- ❌ `git add -A` / `git add .` —— 会把他人或用户的在途改动混进提交；脚本已直接拒绝。
- ❌ 只看 `git commit` 的输出就当成功 —— ref 更新可能没落稳，必须核三处。
- ❌ 脏工作区直接 rebase / merge —— 触发 stash 的合并路径在本环境下有毁库风险。
- ❌ 用几分钟前的 `git status -sb` 判断"与主线一致" —— 那是上次 fetch 的快照。
- ❌ push 被拒后立刻 `--force` —— 先看清远端多了什么。
- ❌ 镜像失败就重试 / 换代理 / 改走 SSH —— 规则是尝试一次、失败只报一次。
- ❌ 提交消息里沿用会话中途量的规模数字 —— 必须在提交那一刻实测。
- ❌ 把"已提交但工作区又脏"误判成"没提交上" —— 看 `status --short` 的两列，别只看 `M`。
