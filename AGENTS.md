# AGENTS.md

> 所有 AI 编码代理的统一入口 (Copilot / Codex / Cursor / Gemini CLI / Claude Code / ZCode / Trae 通用)。完整知识库在 `memory-bank/` (Memory Bank 模式) — 本文件只放**路由与硬约束**; 不要凭印象回答项目问题, 按路由深入后再动代码。
> ⚠ **本文件有 8000 字符硬上限** —— IDE 注入时超出即被 `slice` 掉, 尾部内容模型根本看不到。改完用 `python scripts/check_context_caps.py` 自查 (已挂 `.commit-flow.toml` 的 `[[gates]]`, 改动本文件时预检会自动提示)。

## 知识库路由 (两层: 本文件粗路由 → `memory-bank/README.md` 细路由)

> **「按任务读哪份文档」的单点在 [memory-bank/README.md](memory-bank/README.md) 的细路由表** —— 本文件不复述, 免得两处各自演化。三条动作级提示:
> - **改代码前**: 读 [pitfalls/_index.md](memory-bank/pitfalls/_index.md) —— 7 类 (git · web-ui · backend · testing · ops · kb · docs), 按动作选类再进类索引。
> - **跑 git 命令前**: 必读 [pitfalls/git/_index.md](memory-bank/pitfalls/git/_index.md) —— 本工具 shell 里 `rebase` / `merge` / `stash` 都会毁 `.git`。
> - **检索纪律**: 先索引、后 grep、**禁止整读**任一目录; 不确定关键词时 `grep -rn "<词>" memory-bank/` 兜底。

## 会话协议

> 完整规程 (会话开始 / 收尾 DoD 5 步 / 立档阈值 4 条 / 任务档案模板) 见 [memory-bank skill](.agents/skills/memory-bank/SKILL.md); 机械守卫 `tests/test_memory_bank.py`。本节只留入口。

- **开始**: ①**先拉远程** —— `git pull --rebase <remote> develop` (分支名**必须写**), `git status -sb` 不落后再开工; **禁止在落后分支上改代码** (机检: `python .agents/skills/my-commit-flow/scripts/preflight.py`)。拉取前先把工作区弄干净, 理由见下节。②读 [activeContext.md](memory-bank/activeContext.md) (当前焦点); 该读哪份文档走上面的路由。③**只动当前这一个 clone** —— 跨仓库操作**绝对禁止**, 须用户显式说「授权」(见「🔴 跨仓库操作」节)。
- **收尾**: 按 skill 的 5 步 DoD —— 更新 activeContext (已完成条目**迁出**到 progress) / 达阈值则立档 + `python .agents/skills/memory-bank/scripts/gen_tasks_index.py` 重建索引 / 代码事实变更回写 `memory-bank/` 与根 README / 跑 `uv run pytest tests -q` 并把实测数字记进 `testing.md` / **新坑按动作写进 `pitfalls/<类>/<主题>.md`(补三行头元数据)并重跑 `gen_kb_index.py`**。若这一轮踩到了**已记的坑**, 把该条 `复发` +1, 并在档案里写一句为什么没命中(路由没到 / 文件没读 / 读了没照做)。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`; 漂移以代码为准并回写。

## 产出口径

- **计划文档**: 用 `delivery-artifact` skill, 放 `docs/plans/`; **一律单文件 HTML** (出现 `.md` 即违规)。
- **HTML 一律 dark 主题**: 深色底 + 浅色字 + 样式里写 `color-scheme: dark`, **禁止浅底黑字**; 配色规格与文件命名见 [conventions.md](memory-bank/conventions.md)「HTML 文档一律 dark 主题」。

## 黄金法则 (来自设计原则, 违反即破坏设计)

1. **幂等性**: 重复执行不得有副作用; "每天一次"等窗口语义靠 state_file 去重 (`record_execution`), 不依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置范围生效。
3. **状态持久化**: 跨轮次状态统一进 state_file, 程序退出时才落盘。
4. **fail-fast**: 配置在 `config.validate_config` 全量校验并聚合报错; 之后的代码假定配置正确。**新配置键必须加进 validate_config 并同步 `config/schema.py`** (守卫测试会查)。
5. **单一写线程**: 只有主循环线程改任务队列结构与 state_file; 不引入绕开该假设的并发代码。
6. **范围守恒**: 计划外的代码/文档缺陷**一行都不改** —— 入池 `memory-bank/issues/` (命名 / 8 类类型 / 档位 / `_index.md` 登记见 [create-issue skill](.agents/skills/create-issue/SKILL.md)); **入池不为填单做代码分析**。该不该现在修见 [scope-guard skill](.agents/skills/scope-guard/SKILL.md)。
7. **请求边界**: 开工先判这一轮是**问答 / 只读**还是**执行任务** —— 只是问就**只在回复里作答**, 不得入池 issue / 立档 / 出计划 / 改文件 / commit push; 想延伸排查先问。只有执行任务才适用上面的收尾 DoD 与立档阈值。
   - ❗**"继续 / continue / 接着做 / 你看着办"不构成授权** —— 只表示"把你手上这一步做完"。四类动作必须**逐项**显式确认: ①新建文件 ②入池 issue ③认领 issue ④commit / push。
   - 反面案例见 [pitfalls/kb/request-boundary.md](memory-bank/pitfalls/kb/request-boundary.md)。

## 红线 (生产文件, 禁止改动/提交)

- **`config.yml`**: 用户真实生产配置 (真实 PT 域名 / tracker 规则 / qB 凭据引用), 不是示例! 示例用 `minimal.yml` / `test_yamls/`。
- **`auto-qb-data/`**: 运行时数据 (state.json / 锁 / 日志 / 跳检备份), 已 gitignore; 不要"顺手"格式化或重排。
- 明细见 [pitfalls/ops/prod-files.md](memory-bank/pitfalls/ops/prod-files.md)。

## 命令

```bash
uv run pytest tests -q                              # 全量测试 (基线数字见 memory-bank/testing.md 顶部)
uv run pytest tests -q --no-cov                     # 快速迭代, 跳过覆盖率报表
uv run python src/auto-qb.py config.yml --dry-run   # 运行 (需真实 qB; 一律先 --dry-run 观察)
yapf -i src/auto_qb/**/*.py                         # 格式化 (.style.yapf: facebook 风格, 列宽 120)
```

- 依赖统一走 `uv` (`pyproject.toml` + `uv.lock`); 首次/依赖变更后 `uv sync`。
- ⚠ 工具 shell 里跑全量前先设 `TMPDIR="R:/Temp/auto-qb/tests"`, 否则会话收尾会崩 (测试其实全过) —— 见 [pitfalls/testing/tmpdir.md](memory-bank/pitfalls/testing/tmpdir.md)。
- 新增测试必须同步该文件头部 docstring 的 "## 测试计划" 清单。

## ⚠️ 环境硬约束: Git 操作 (AI 工具 shell 特有)

> **工作区模式: 多 clone 并行** (2026-09-20 用户决定, **已弃用 git worktree**): 每个 AI 实例用**一份独立克隆**, 跨 clone 同步一律走 Gitee `develop`。细则见 [conventions.md](memory-bank/conventions.md)「协作约定」。
> **完整禁令与事故判据单点在 [pitfalls/git/_index.md](memory-bank/pitfalls/git/_index.md)**; 本节只留最容易致命的几条:

- 🔴 **禁用 `git rebase`** (已炸 3 次, 工作区干净也照炸) 与 **`git stash`**; **非快进合并 + 工作区脏 = 必炸** (拦截层会顺着这次写入批量删 `.git/objects`)。落后主线改走「移出改动 → `merge --ff-only` 快进 → 施回改动 → 提交」(先同步后提交, 推送即快进)。
- **提交后必查 ref 三处**: `HEAD` == `refs/heads/<branch>` == loose/packed-refs, 用 `my-commit-flow/scripts/verify_ref.py` 并按它打印的步骤修。**不要只看 commit 输出**。
- **判"推没推上"只看 `git ls-remote <远端> <分支>`** —— 本 shell 里 `refs/remotes/*` 的写入会被静默丢弃, 且 `git push --dry-run` 永远"成功"。
- 机检与停手点一律走 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md)。

## 🔴 跨仓库操作: 绝对禁止 (需显式强授权)

> **完整定义(含事故实证与止损纪律)见 [conventions.md](memory-bank/conventions.md)「🔴 跨仓库操作」节**; 本节只留红线。

- **除当前工作 clone 外, 对其它 clone 的任何写操作一律绝对禁止** —— 改文件 / `git apply` / 复制覆盖 / 跑 git 命令。
- **授权指令只认 `授权`**, 须用户**显式**说出; **「提交」不算** —— 它只授权 commit + push 到远端。
- 未授权时**停下来问**: 发现"改动在别的 clone 上不生效"该报告交由用户决定, **不能自己动手**。
- **跨工作区同步一律走 Gitee `develop`**, 没有第二种路径。

## 提交 / PR

> **步骤、命令与机检脚本一律走 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md)** —— 预检 → 闸门 → 逐路径暂存 → 提交并核 ref 三处 → 推 Gitee → 尝试一次 GitHub 直连 → 查幽灵 diff。**本节只留口径, 不重复命令**。

- **协作主线**: 日常在 `develop`, 以 **Gitee 的 `develop`** 为准; **交付与否只看 Gitee**。GitHub 只作镜像、**允许滞后** —— 别用 GitHub 状态判断进度。
- **用户说"提交" = commit + push**, 一次走完; **触发词只认"提交 / 入库 / 推上去"这类显式指令**, "继续 / 接着做 / ok / 你看着办"一律不算。**本条是提交口径的单点定义**, 优先于 `memory-bank/` 里的历史表述。
- **推送顺序固定**: 先推 Gitee (必须成功) → 核远端 ref == 本地 → 再**尝试一次** GitHub 直连; 失败**只如实报告一次**, 不重试 / 不换代理 / 不改走 SSH / 不回滚改写 Gitee 已完成的推送。
- **提交信息 = gitmoji + 中文**: 首行 `<gitmoji> <中文一句话概述>`, 空一行后写动机 / 取舍 / 影响面 / 实测数字; 小改只写首行。**数字必须是提交那一刻实测的**。选哪个 emoji 走 [gitmoji skill](.agents/skills/gitmoji/SKILL.md)。
- **提交前先收尾**: 收到"提交"先按「会话协议 · 收尾」跑完, 回写文件**随主提交一并暂存** —— 不推完再补一笔 (已推送的提交不能 amend + 强推)。
- **红线与闸门清单外置在 `.commit-flow.toml`** (skill 强制读取, 缺了就停手引导生成)。
