# 提交推送流水线 (v3 · 沉默即成功)

> 本包是 `my-commit-flow` skill 退役后的形态: 流程与纪律全在包里, 配置(`.my-commit-flow.toml`)也在包里 —— 整包复制即可带走。`commands` 引擎只按 task id 调它, 对"提交"一无所知。
> 本文件只是索引 —— 日常只要 task id; 完整判据 / 配置机制在 `references/`(排障或迁移才读)。

用户说"提交" = **commit + 推送**, 一次走完。v3 输出契约(计划 26-09-28-0157): **成功一行, 失败一行(原因 + 下一步)**; 全部检查内联进脚本, 沉默 = 全过。

## 任务 (4 个入口)

| task | 做什么 | 输出 |
|---|---|---|
| `my-commit-flow.sync` | 开工 / 提交前同步: fetch + 快进 / 分叉自动 rebase(保线性) | `已同步 / 同步成功 <hash>`; 失败一行含原因与步骤 |
| `ship.commit` | 提交全流程: 内部同步 → 闸门 → 逐路径暂存 → 提交 → 核 ref → 内联推送 | `提交成功 <hash>`; 推送未完成不改退出码(补 ship.push) |
| `ship.push` | 补推 / 重验: 同步核对 → 推主线 → 核远端 → 镜像(全程静默) | `推送成功 <hash>` |
| `my-commit-flow.verify-ref` | 排障: ref 三处核对 | `ref 一致 <hash>`; 不一致给处置步骤 |

## 停手点 (脚本只报, 不替你判断)

0. **缺外置配置** —— `python <包>/scripts/_pipeline.py --init` 生成初稿 → 人工确认(红线必须手填) → 置 `confirmed = true`。
1. **树脏 + 落后/分叉** —— 失败行写明; 先提交或 stash 再重跑(脚本不代做清理)。
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

本环境专属的 git 事实(判"推没推上"只看 `git ls-remote`、ref 三处核对)单点在
`memory-bank/pitfalls/git/_index.md` —— 换仓库要重新确认, 本包不复制一份。

> 路径约定：`<包>` = 本包目录（`<仓库根>/.commands/my-commit-flow`），先用 Glob 定位，别照抄路径。
