# 配置机制（排障 / 迁移才读）

> 索引在 [../README.md](../README.md)。**项目特有项一律外置**在 `<包>/.my-commit-flow.toml`：
> 红线文件 `red_lines`、高危文件 `warn_lines`、提交前闸门 `[[gates]]`、平台关键词 `platform_hints`、
> `staged_panic`。**缺这个文件就停手并引导生成**（不猜默认值 —— 猜错比停下来更贵）。

```bash
python <包>/scripts/preflight.py --init          # 按仓库特征生成初稿(confirmed = false)
# 打开逐项确认/修改: red_lines 必须手填; [[gates]] 看注释里的"判据"是否判对; 然后 confirmed = true
python <包>/scripts/preflight.py --show-config    # 看生效值与来源
python <包>/scripts/preflight.py --config <路径>  # 临时用另一份配置
```

**初稿不是成品**：`--init` 只做两件安全的事 —— 红线**只给候选不代填**（靠猜的红线会漏掉最要命的那条），
闸门**多证据才下判断、判断不出就不猜**（猜错的闸门会让人以为该跑的跑过了）。判据写进注释便于核对。
预检会把「未确认 / 空红线 / 空 gates / 命令仍含 `<未填…>`」逐条报出来，防止照单全收
（空 `gates` 意味着提交前没有任何机检，零依赖仓库最容易踩）。平台关键词按识别出的技术栈给
（Python / Node / Make 各不相同），未识别则留空让人手写。

## 闸门字段：auto / timeout / each_limit

| 字段 | 默认 | 含义 |
|---|---|---|
| `auto` | `false` | `true` = 预检**真的执行**它（红了即 STOP）；`false` = 只打印给人 |
| `timeout` | `600` | 单条命令超时秒数；超时按失败计（不让卡死的命令挂住预检） |
| `each_limit` | `99` | `<each:>` 展开条数上限（顶层键；超了说明提交范围该拆） |

**未知键 / `timeout` 非法一律 STOP**（不是 WARN）：闸门可能很贵（全量测试 / 格式化 / 索引自洽），
一个拼错的键让它**静默失效**，比它直接报错坏得多 —— 报错会立刻被发现，静默失效会让人以为
"该跑的跑过了"，而且 WARN 会被淹没在十来行的检查表里。付的价钱：新增配置键必须先加进
`KEY_DEFAULTS` / `GATE_KEYS`，否则一写就挡住提交。

## 占位符（由预检展开，展开不了即 STOP，不降级成打印）

| 占位符 | 展开为 |
|---|---|
| `<root>` | 仓库根绝对路径 |
| `<skill-dir:NAME>` | skill 目录（`.agents/skills` → `.codebuddy/skills` → 用户级），**找不到即 STOP** |
| `<changed:GLOB>` | 本次改动里匹配的文件 → 拼成**一条**命令（排除已删除的） |
| `<each:GLOB>` | 按匹配文件把这条 `run` **复制成多条**命令，每条替换一个文件；条数上限 `each_limit` |

自造占位符（如 `<改过的 py 文件>`）不会被猜 —— 残留的尖括号直接报 STOP。

## 运行期自动探测（换项目直接能用）

| 项 | 怎么探测 | 覆盖办法 |
|---|---|---|
| 仓库根 | 从脚本目录向上找 `.git`（目录或 worktree 的 `.git` 文件） | — |
| 分支 | 跟当前分支 | 配 `branch` |
| 主线远端 | 候选名（`main_candidates`）里第一个 **URL 含 `main_host_mark`** 的（按 URL 特征而非名字）；都不匹配则回退到候选里第一个存在的 | 配 `main_host_mark` / `main_candidates` |
| 镜像远端 | 按 URL 含 `mirror_host_mark` 找并**排除主线自己**；没有镜像也正常 | 配 `mirror_host_mark` |
| 禁用代理的 `-c` | 从 `git config` 读 per-URL 代理 key，没配就不加参数 | — |

上面这些只是**探测规则**，取值来源仍是外置配置 —— 也就是说：流程内置、项目事实外置，两边不混。
