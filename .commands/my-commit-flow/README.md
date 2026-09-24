# 提交推送流水线

> **本包是 `my-commit-flow` skill 退役后的形态**：流程与纪律全在包里，配置（`.my-commit-flow.toml`）也在包里 ——
> 整包复制即可带走。`commands` 引擎只按 task id 调它，对"提交"一无所知。
> **本文件只是索引** —— 日常只要 task id；完整判据 / 配置机制 / 反模式在 `references/`（排障或迁移才读）。

用户说"提交" = **commit + 推送**，一次走完。把散落各处的提交纪律收成一条必经路径：**能机检的交给脚本，必须人判的写成停手点**。

## 流水线（七步）

| 步 | 做什么 | 判据 / 不通过怎么办 |
|---|---|---|
| **S0 配置**（每仓库一次） | 确认 `<包>/.my-commit-flow.toml` 存在且 `confirmed = true` | **没有就停手**：`commands run my-commit-flow.preflight -- --init` 生成初稿 → **人工确认**（红线必须手填）→ 置 `confirmed = true`。未确认 / 空红线 / 命令还是 `<未填…>` 都会被预检报出来 |
| **S1 预检与同步** | `commands run my-commit-flow.preflight` | 一张表报出：配置来源 / 主线远端 / 上游 / 落后几个 / **合流预判撞不撞** / 工作区脏不脏 / 红线文件 / 该跑哪些闸门。落后或分叉时会额外跑一次 `git merge-tree --write-tree`（**只读**：只在对象库里算合并树，不写工作区 / ref / index）报「撞 / 不撞」，把冲突从"push 被拒才发现"提前到提交前。**有 STOP 先处理**（唯一例外：落后 + 脏，要先提交）；**推送前再跑一次** |
| **S2 闸门** | 预检**已经跑掉** `auto = true` 的那些，结果写在检查表里；没标 `auto` 的照单跑 | 红了不提交 —— STOP 由预检给出，不用自己判退出码 |
| **S3 暂存** | `commands run ship.commit -- --message-file <文件> <路径...>` | **逐路径**，脚本直接拒绝 `-A` / `.` / `*`；红线文件直接拒交，高危文件需人工确认。**暂存前先把收尾做完**（知识库 / 文档 DoD 先回写再一起暂存） |
| **S4 信息** | 自己写 | 首行一句话说清"改了什么 / 为什么"，空一行后写动机 / 取舍 / 影响面 / 实测数字。**数字必须提交那一刻实测** |
| **S5 提交并核 ref** | `commit.py` 提交完自动核 | `HEAD` == `refs/heads/<branch>` == loose/packed-refs 三处一致；不一致按 `commands run my-commit-flow.verify-ref` 给的步骤走，**不要只看 commit 输出** |
| **S6 推送** | `commands run ship.push` | **顺序固定**：先推主线（必须成功）→ 核对远端 ref → 再**尝试一次**镜像。镜像失败**只报一次**：不重试 / 不换代理 / 不改走 SSH / 不回滚主线 |
| **S7 收尾** | 查幽灵 diff | `git status --short` 看两列：`M `（第一列）待提交，` M`（第二列）已提交过但工作区又脏。权威判据：`git log --oneline -1 -- <文件>` 有记录 **且** `git diff --quiet -- <文件>` rc=0 |

## 停手点（脚本只报，不替你判断）

0. **缺外置配置** —— 生成并确认后再动。
1. **需要合流** —— 脚本只报"落后 N 个提交"就退出；**若同时工作区脏，先提交再快进**（顺序见 `references/pipeline.md`）。
2. **改动里混有他人 / 在途改动** —— 高危清单见配置的 `warn_lines`。
3. **staged 数量暴增** —— 大概率分支 ref 被回退，**不要**用全量提交去"解决"。
4. **ref 三处不一致** —— 按 `verify-ref` 打印的步骤走。
5. **测试红 / 闸门未过** —— 不提交。

## 反模式（最致命的六条，全集见 `references/anti-patterns.md`）

- ❌ `git add -A` / `git add .` —— 混进他人改动；脚本已直接拒绝。
- ❌ 只看 commit 输出就当成功 —— ref 可能没落稳，必须核三处。
- ❌ 脏工作区直接 rebase / merge —— **rebase 一律禁用**，快进用 `merge --ff-only`。
- ❌ 看到「落后主线」的 STOP 就先去 rebase —— 工作区脏时那是最危险的一步，先提交。
- ❌ 推完才回写知识库 / 文档 —— 已推送不能 amend 强推，只能再补一笔。
- ❌ 提交消息沿用会话中途量的数字 —— 必须提交那一刻实测。

## 深读才看

| 想知道 | 看哪份 |
|---|---|
| 落后+脏的处理顺序 / 分叉替代路径 / 闸门跑几次 / 脚本与退出码 | `references/pipeline.md` |
| 外置配置 / 占位符 / `auto`·`timeout`·`each_limit` / 探测规则 | `references/config.md` |
| 反模式全集 | `references/anti-patterns.md` |

本环境专属的 git 事实（rebase / stash 为何禁用、判"推没推上"只看 `git ls-remote`）单点在
`memory-bank/pitfalls/git/_index.md` —— 换仓库要重新确认，本包不复制一份。

> 路径约定：`<包>` = 本包目录（`<仓库根>/.commands/my-commit-flow`），先用 Glob 定位（`**/my-commit-flow/scripts/*.py`），别照抄路径。
