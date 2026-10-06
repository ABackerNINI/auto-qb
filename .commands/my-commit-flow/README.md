# 提交推送流水线 (v3.1 · 沉默即成功 + 改写留痕)

> 本包是 `my-commit-flow` skill 退役后的形态: 流程与纪律全在包里, 配置(`.my-commit-flow.toml`)也在包里 —— 整包复制即可带走。`commands` 引擎只按 task id 调它, 对"提交"一无所知。
> 本文件只是索引 —— 日常只要 task id; 完整判据 / 配置机制在 `references/`(排障或迁移才读)。

用户说"提交" = **commit + 推送**, 一次走完。v3 输出契约(计划 26-09-28-0157): **成功一行, 失败一行(原因 + 下一步)**; 全部检查内联进脚本, 沉默 = 全过。
v3.1(2026-10-06)只补一件事: 一次命令内部 HEAD 会被改写多次(提交自身 → 内部 rebase → 闸门改后 amend), 结果行只给终值 ⇒
**凡真改写 HEAD 的步骤, 在结果行上面各留一行 `旧hash→新hash`**(没发生的一律不报)。结果行本身逐字未变。

网络容错(2026-10-06): 每条 git 命令都走 `_pipeline.run_git` —— **单次超时 20s + 有界重试(默认 3 次, 全部失败才判失败)**。
Gitee 间歇性卡住时不再被拆成「未推送 + 手工补推」: 网络子命令(push / fetch / ls-remote …)**失败即重试**,
非幂等的本地写(commit / rebase / merge …)只给超时不给重试, GitHub 镜像只给超时(`attempts=1`)。判据单点见 `references/pipeline.md`。

## 任务 (4 个入口)

| task | 做什么 | 输出 |
|---|---|---|
| `my-commit-flow.sync` | 开工同步: fetch + 快进 / 分叉自动 rebase(保线性)。提交路径已不需要它(2026-10-04 起 ship.commit 提交先行) | `已同步 / 同步成功 <hash>`; 上面可能带「快进 / rebase 重放」步骤行; 失败一行含原因与步骤 |
| `ship.commit` | 提交全流程: 闸门 → 逐路径暂存 → 提交 → 核 ref → 内部同步(树净 rebase 恒可自动) → 内联推送 | `提交成功 <hash>`; 上面可能有同步 + 闸门 amend 步骤行; 推送未完成(含同步冲突/断网)不改退出码(补 ship.push) |
| `ship.push` | 补推 / 重验: 同步核对 → 推主线 → 核远端 → 镜像(全程静默) | `推送成功 <hash>`; 上面可能带内部同步的步骤行 |
| `my-commit-flow.verify-ref` | 排障: ref 三处核对 | `ref 一致 <hash>`; 不一致给处置步骤 |

## 停手点 (脚本只报, 不替你判断)

0. **缺外置配置** —— `python <包>/scripts/_pipeline.py --init` 生成初稿 → 人工确认(红线必须手填) → 置 `confirmed = true`。
1. **树脏 + 落后/分叉(仅独立 sync 会撞)** —— 失败行写明并**自带两条出路**: ① `git stash push -u` → `my-commit-flow.sync` → `git stash pop` → 测试 → `ship.commit`(脚本不代做清理); ② 工作已完成待入库 → 直接 `ship.commit`(2026-10-04 起提交先行, 树净 rebase 恒可自动)。
2. **改动混有 warn_lines(用户在途文件)** —— 成功行后附一行 ⚠, 确认是有意的。
3. **staged 数量暴增** —— 分支 ref 可能被回退; 不要 add -A "解决", 走 `my-commit-flow.verify-ref`。
4. **闸门红** —— 失败输出附闸门名 + 末 20 行; 处理后重跑。

## 反模式 (最致命的几条, 全集见 `references/anti-patterns.md`)

- ❌ `git add -A` / `git add .` —— 混进他人改动; 脚本已直接拒绝。
- ❌ 只看 commit 输出就当成功 —— ref 核对已内联; 排障用 `my-commit-flow.verify-ref`。
- ❌ 推完才回写知识库 / 文档 —— 已推送不能 amend 强推, 只能再补一笔。
- ❌ 提交消息沿用会话中途量的数字 —— 必须提交那一刻实测。

## 深读才看

| 想知道 | 看哪份 |
|---|---|
| 同步/合流判据 / 编排顺序 / 输出契约 / 脚本与退出码 | `references/pipeline.md` |
| 外置配置 / 占位符 / `auto`·`timeout`·`each_limit` / 探测规则 | `references/config.md` |
| 反模式全集 | `references/anti-patterns.md` |

本环境专属的 git 事实(refs/remotes 写入静默丢弃; 同步/推送核验与 ref 三处核对已内联进脚本)单点在
`memory-bank/pitfalls/git/_index.md` —— 换仓库要重新确认, 本包不复制一份。

> 路径约定：`<包>` = 本包目录（`<仓库根>/.commands/my-commit-flow`），先用 Glob 定位，别照抄路径。
