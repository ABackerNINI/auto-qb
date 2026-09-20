---
name: my-commit-flow
description: '提交推送流水线(用户说"提交" = commit + push): 预检与同步 → 闸门 → 逐路径暂存 → 提交并核对 ref 三处 → 推主线 → 尝试一次镜像 → 查幽灵 diff。USE FOR: 用户说"提交"/"推送"/"推上去"/"commit"; 收尾要把改动落到主线时。DO NOT USE FOR: 判断改不改(见 scope-guard skill)、要不要入池(见 create-issue skill)、纯答疑。仓库根 / 分支 / 主线远端 / 镜像 / 代理均运行期探测; 项目特有项(红线文件、提交前闸门)**强制外置**在 <仓库根>/.commit-flow.toml, 缺失即停手并引导生成。'
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
| **S0 配置**（每仓库一次） | 确认 `<仓库根>/.commit-flow.toml` 存在且 `confirmed = true` | **没有就停手**，跑 `preflight.py --init` 生成初稿 → **人工确认/修改**（红线必须手填）→ 置 `confirmed = true`。本 skill 不内置项目配置，也不猜默认值；未确认 / 空红线 / 命令还是 `<未填…>` 都会被预检报出来 |
| **S1 预检与同步** | `python <skill-dir>/scripts/preflight.py` | 一张表报出：配置来源 / 主线远端 / 上游 / 落后几个 / 工作区脏不脏 / 有没有红线文件 / 该跑哪些闸门。有 **STOP** 就先处理；**推送前再跑一次**（`status -sb` 的 ahead/behind 是上次 fetch 的快照，不会自己刷新） |
| **S2 闸门** | 跑预检列出的命令（测试、生成器 `--check`、格式化…） | 红了不提交 |
| **S3 暂存** | `python <skill-dir>/scripts/commit.py --message-file <文件> <路径...>` | **逐路径**，脚本直接拒绝 `-A` / `.` / `*`；红线文件（配置的 `red_lines`）直接拒交；高危文件（`warn_lines`）需人工确认 |
| **S4 信息** | 自己写 | 首行一句话说清"改了什么 / 为什么"，空一行后写动机 / 取舍 / 影响面 / 实测数字。**数字必须提交那一刻实测**，不沿用会话中途量的旧值 |
| **S5 提交并核 ref** | `commit.py` 提交完自动调 `verify_ref.py` | `HEAD` == `refs/heads/<branch>` == loose/packed-refs 三处一致；不一致按脚本给的处置步骤走，**不要只看 commit 输出** |
| **S6 推送** | `python <skill-dir>/scripts/push.py` | **顺序固定**：先推主线（必须成功）→ 核对远端 ref == 本地 → 再**尝试一次**镜像。镜像失败**只报一次**：不重试、不换代理、不改走 SSH、不回滚主线 |
| **S7 收尾** | 查幽灵 diff + 回写知识库 | `git status --short` 看两列：`M `(第一列) = 待提交，` M`(第二列) = 已提交过但工作区又脏。权威判据：`git log --oneline -1 -- <文件>` 有记录 **且** `git diff --quiet -- <文件>` 退出码 0。补一次提交，不要改写已入库的提交 |

脏工作区不 rebase / 不 merge（先提交或移出改动）；高风险操作前先备份 `.git`。

## 停手点（脚本只报，不替你判断）

0. **缺外置配置** —— 生成并确认 `.commit-flow.toml` 后再动。
1. **需要 rebase / merge** —— 脚本只报"落后 N 个提交"就退出。
2. **改动里混有他人 / 用户在途改动** —— 高危清单见配置的 `warn_lines`。
3. **staged 数量暴增**（阈值见配置）—— 大概率是分支 ref 被回退，**不要**用 `add -A` 或全量提交去"解决"。
4. **ref 三处不一致** —— 按 `verify_ref.py` 打印的步骤走。
5. **镜像推送失败** —— 报告一次就结束，镜像允许滞后。
6. **测试红 / 闸门未过** —— 不提交。

## 脚本

| 脚本 | 职责 | 退出码 |
|---|---|---|
| `<skill-dir>/scripts/preflight.py` | 只读预检（+ 一次安全 fetch）：配置 / 远端 / 上游 / 落后 / 脏 / 红线 / 闸门 / staged 异常；`--init` 生成配置初稿、`--show-config` 看生效值 | 0 可继续 · 1 有 STOP（缺配置亦为 1） |
| `<skill-dir>/scripts/commit.py` | 逐路径 `add` + `commit -F` + 提交后自动核 ref | 4 参数/红线 · 5 git 失败 · 2 ref 不一致 |
| `<skill-dir>/scripts/verify_ref.py [sha]` | ref 三处一致核对 | 0 一致 · 2 不一致 · 3 staged 暴增 |
| `<skill-dir>/scripts/push.py [--skip-mirror]` | fetch → 推主线 → 核对远端 → 尝试一次镜像 | 0 主线成功 · 1 落后 · 5 主线失败 · 6 取不到远端 ref |

## 配置（外置，强制）与自动探测

**项目特有项一律外置**在 `<仓库根>/.commit-flow.toml`（可用 `--config` 临时换一份）：红线文件 `red_lines`、
高危文件 `warn_lines`、提交前闸门 `[[gates]]`、平台关键词 `platform_hints`、`staged_panic`。
**缺这个文件就停手并引导生成**（不猜默认值 —— 猜错比停下来更贵）：

```bash
python <skill-dir>/scripts/preflight.py --init          # 按仓库特征生成初稿(confirmed = false)
# 打开逐项确认/修改: red_lines 必须手填; [[gates]] 看注释里的"判据"是否判对; 然后 confirmed = true
python <skill-dir>/scripts/preflight.py --show-config    # 看生效值与来源
```

**初稿不是成品**：`--init` 只做两件安全的事 —— 红线**只给候选不代填**（靠猜的红线会漏掉最要命的那条），
闸门**多证据才下判断、判断不出就不猜**（猜错的闸门会让人以为该跑的跑过了）。判据写进注释便于核对。
预检会把「未确认 / 空红线 / 空 gates / 命令仍含 `<未填…>`」逐条报出来，防止照单全收
（空 `gates` 意味着提交前没有任何机检，零依赖仓库最容易踩）。平台关键词按识别出的技术栈给
（Python / Node / Make 各不相同），未识别则留空让人手写。
python <skill-dir>/scripts/preflight.py --config <路径>  # 临时用另一份配置
```

**运行期自动探测**（受配置里的 mark 与候选名驱动，换项目直接能用）：

| 项 | 怎么探测 | 覆盖办法 |
|---|---|---|
| 仓库根 | 从脚本目录向上找 `.git`（目录或 worktree 的 `.git` 文件） | — |
| 分支 | 跟当前分支 | 配 `branch` |
| 主线远端 | 候选名（`main_candidates`）里第一个 **URL 含 `main_host_mark`** 的（按 URL 特征而非名字）；都不匹配则回退到候选里第一个存在的 | 配 `main_host_mark` / `main_candidates` |
| 镜像远端 | 按 URL 含 `mirror_host_mark` 找并**排除主线自己**；没有镜像也正常 | 配 `mirror_host_mark` |
| 禁用代理的 `-c` | 从 `git config` 读 per-URL 代理 key，没配就不加参数 | — |

上面这些只是**探测规则**，取值来源仍是外置配置 —— 也就是说：流程内置、项目事实外置，两边不混。

## 反模式

- ❌ `git add -A` / `git add .` —— 会把他人或用户的在途改动混进提交；脚本已直接拒绝。
- ❌ 只看 `git commit` 的输出就当成功 —— ref 更新可能没落稳，必须核三处。
- ❌ 脏工作区直接 rebase / merge —— 触发 stash 的合并路径在本环境下有毁库风险。
- ❌ 用几分钟前的 `git status -sb` 判断"与主线一致" —— 那是上次 fetch 的快照。
- ❌ push 被拒后立刻 `--force` —— 先看清远端多了什么。
- ❌ 镜像失败就重试 / 换代理 / 改走 SSH —— 规则是尝试一次、失败只报一次。
- ❌ 提交消息里沿用会话中途量的规模数字 —— 必须在提交那一刻实测。
- ❌ 把"已提交但工作区又脏"误判成"没提交上" —— 看 `status --short` 的两列，别只看 `M`。
- ❌ 把项目红线写进 skill 代码 —— 那是项目事实，该进 `.commit-flow.toml`。
- ❌ 缺配置时"先猜一份默认继续提交" —— 猜错会放过红线文件，也会漏掉闸门。
