# AGENTS.md

> 所有 AI 编码代理的统一入口 (Copilot / Codex / Cursor / Gemini CLI / Claude Code / ZCode / Trae 通用)。
> 完整知识库在 `memory-bank/` (Memory Bank 模式) — 本文件只放路由与硬约束; 不要凭印象回答项目问题, 按路由深入后再动代码。

## 会话协议

> 完整规程(含任务档案模板)见 [.agents/skills/memory-bank/SKILL.md](.agents/skills/memory-bank/SKILL.md); 机械守卫 `tests/test_memory_bank.py`。

- **开始**: **①先拉取远程分支** —— `git remote -v` 确认主线远端 (Gitee), 再 `git pull --rebase <remote> develop` (分支名**必须写**), 确认 `git status -sb` 不落后后再开工; **禁止在落后的分支上动手改代码** (2026-09-19 用户指定; 命令与机检见 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md) 的 S1, 或直接跑 `python .agents/skills/my-commit-flow/scripts/preflight.py`) —— 拉取前先把工作区弄干净, 理由见「⚠️ 环境硬约束: Git 操作」。再 ②读 [memory-bank/activeContext.md](memory-bank/activeContext.md) (当前焦点); **按任务读哪份文档看本文件「知识库路由」表(单点)**; 已有 `tasks/` 档案的任务从档案续作。
- **收尾 (5 步 DoD)**: ①更新 activeContext (已完成条目**迁出**到 `progress.md` / 主题文档, 不是追加流水账) ②命中阈值的任务在 `memory-bank/tasks/` 立档 (命名 `YY-MM-DD-<slug>.md`, **先按 slug 查重再建**) + 跑 `python scripts/gen_tasks_index.py` 重建索引 (不要手改 `_index.md`) ③代码事实变更回写 `memory-bank/` 对应文档与根 `README.md` (测试基线只改 `testing.md`) ④跑 `uv run pytest tests -q` 并把实测数字记进 `testing.md` ⑤新坑追加 `pitfalls.md`。
- **立档阈值** (满足任一条**必须**立档): ①跨 ≥2 次会话; ②单会话 ≥5 轮指令或改动 ≥3 个源文件; ③出现"计划/方案/波次/第 N 轮/后续阶段"等长周期表述; ④需产出计划文档或交付报告。其余小修与答疑只记 activeContext。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。发现文档漂移时以代码为准并回写文档。

- **计划产出**: 列计划时使用 `delivery-artifact` skill 产出文档, 将计划文档放入 `docs/plans/` 中; **格式一律为单文件 HTML (`.html`), 不使用 Markdown (`.md`)** —— `docs/plans/` 下的计划文档若出现 `.md` 即为违规, 需转为 HTML; 命名统一为"日期-时间-标题"(`YY-MM-DD-HHMM-<slug>.html`), 日期时间须用命令取当前值。
- **HTML 一律 dark 主题 (2026-09-20 用户指定)**: 所有产出的单文件 HTML 文档 (计划文档 / issue 报告 / 交付物 / 演示页) **一律用 dark 主题** —— 深色底 (`--bg`/`--paper` 亮度 ≈ #0f…~#18…) + 浅色字 (`--ink` 亮度 ≥ #d8…), 并在样式里写 `color-scheme: dark`(浏览器原生控件、滚动条、表单才会跟着变深)。**禁止浅底黑字**。存量 HTML 已按此口径统一: `docs/plans/` 25 份与 `memory-bank/issues/` 9 份全为深色; 新产出若不是深色即为违规, 需改。

## 黄金法则 (来自设计原则, 违反即破坏设计)

1. **幂等性**: 动作重复执行不得产生副作用; "每天一次"等窗口语义必须靠 state_file 去重 (`record_execution`), 不依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置范围生效。
3. **状态持久化**: 跨轮次状态统一进 state_file, 程序退出时才落盘。
4. **fail-fast**: 配置在 `config.validate_config` 全量校验并聚合报错; 校验之后的代码假定配置正确, 不做防御性检查; **新配置键必须加入 validate_config 并同步 `config/schema.py`** (守卫测试会查)。
5. **单一写线程**: 只有主循环线程修改任务队列结构与 state_file; 不要引入绕开该假设的并发代码。
6. **范围守恒**: 计划外的代码/文档缺陷**一行都不改** —— 入池到 `memory-bank/issues/`: 报告文件名 = `<时间>-<类型>-<slug>.html`(类型 8 类: `bug` / `perf` / `docs` / `test` / `refactor` / `feat` / `chore` / `question`), 档位由类型定(便签档一两句话 / 标准档取证), `_index.md` 登记类型+简述+链接(生成物, 重跑脚本更新)。**入池不为填单做代码分析**(结论会过期)。该不该现在修见 [scope-guard skill](.agents/skills/scope-guard/SKILL.md); 建报告与改状态见 [create-issue skill](.agents/skills/create-issue/SKILL.md)。
7. **请求边界 (2026-09-20 用户指定)**: 开工先判这一轮是**问答 / 只读**还是**执行任务**。
   - 用户只是问("能不能 X""是什么""怎么看""有没有") ⇒ **只在回复里作答**, 不得入池 issue、
     不得立档 `tasks/`、不得产出计划文档、不得改动任何文件、不得 commit / push。
     **想延伸排查(跑测试、跑冒烟、写探针、做实验)先问**, 别把"回答"做成"交付"。
   - 只有**执行任务**那一类才适用上面的收尾 DoD 与立档阈值。
   - ❗**"继续 / continue / 接着做 / 你看着办"不构成授权** —— 它只表示"把你手上这一步做完",
     不表示"可以开始下一件更大的事"。下面四类动作必须**逐项**拿到显式确认:
     ①新建文件(计划文档 / 任务档案 / 报告) ②入池 issue ③认领 issue(置 `In Progress`)
     ④commit / push。
   - 踩过的坑 (2026-09-20): 把"提议 → 用户说继续"当全权授权, 一路做到入池 + 出计划 + 4 次推送, 最后全部 revert。

## 红线 (生产文件, 禁止改动/提交)

- **`config.yml`**: 用户真实生产配置 (真实 PT 站点域名、tracker 规则、qB 凭据引用), 不是示例! 示例用 `minimal.yml` / `test_yamls/`。
- **`auto-qb-data/`**: 运行时数据目录 (state.json / 锁 / 日志 / 跳检备份), 已 gitignore; 不要"顺手"格式化或重排。

## 命令

```bash
# 依赖统一走 uv (pyproject.toml + uv.lock); 首次/依赖变更后先 `uv sync`
uv run pytest tests -q                                 # 全量测试 (pytest.ini 已带分支覆盖率; 基线数字单点见 memory-bank/testing.md 顶部)
uv run pytest tests -q --no-cov                        # 快速迭代 (跳过覆盖率报表)
uv run python src/auto-qb.py config.yml --dry-run      # 运行 (需真实 qBittorrent; 一律先 --dry-run 观察)
yapf -i src/auto_qb/**/*.py                            # 格式化 (.style.yapf: facebook 风格, 列宽 120)
```

- 新增测试必须同步该测试文件头部 docstring 的 "## 测试计划" 清单 (项目明文规定)。

## 知识库路由 (先查这里再动代码)

| 任务 | 读 |
|---|---|
| **会话开始/收尾** (现在做什么/做到哪) | [memory-bank/activeContext.md](memory-bank/activeContext.md) |
| 项目目标与范围 (纲领) | [memory-bank/projectbrief.md](memory-bank/projectbrief.md) |
| 项目是什么 / 领域知识 | [memory-bank/productContext.md](memory-bank/productContext.md) |
| 主循环/任务队列/数据层/异步校验 | [memory-bank/systemPatterns.md](memory-bank/systemPatterns.md) |
| 找功能位置 / 加新模块 | [memory-bank/modules.md](memory-bank/modules.md) |
| 规则/条件/动作 | [memory-bank/rule-system.md](memory-bank/rule-system.md) |
| 配置解析 / 新配置键 | [memory-bank/config-reference.md](memory-bank/config-reference.md) |
| 命名/风格/约定 | [memory-bank/conventions.md](memory-bank/conventions.md) |
| 技术栈/开发环境/约束 | [memory-bank/techContext.md](memory-bank/techContext.md) |
| 写/跑测试 | [memory-bank/testing.md](memory-bank/testing.md) |
| **CI 报错 / 平台差异复现** | [pitfalls.md](memory-bank/pitfalls.md)「Windows 全绿 / Linux 全红」条目 (含本机 WSL 复现命令) |
| **撞见计划外问题: 该不该现在修** | [scope-guard skill](.agents/skills/scope-guard/SKILL.md) |
| **建 issue 报告 / 改 issue 状态** | [create-issue skill](.agents/skills/create-issue/SKILL.md) + [issues/_index.md](memory-bank/issues/_index.md) |
| **提交 / 推送 (commit + push)** | [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md) (口径在本文件「提交 / PR」节) |
| 改代码前必读 (风险点/陷阱) | [memory-bank/pitfalls.md](memory-bank/pitfalls.md) |
| XX 做了吗 / 计划怎么做 | [memory-bank/progress.md](memory-bank/progress.md) |
| 跨会话任务档案 | [memory-bank/tasks/_index.md](memory-bank/tasks/_index.md) |

## ⚠️ 环境硬约束: Git 操作 (AI 工具 shell 特有, 用户自己的普通终端无此问题)

> 本仓库多个 worktree 共享同一个对象库 `D:/Projects/auto-qb/.git`, **任一处出事波及全部**, 备份要备份主 gitdir。

- **禁止在工具 shell 里跑「非快进合并 + 工作区脏」**: 记死一句 **非快进 + 脏 = 必炸** —— git 2.55 非快进合并时无条件调 `git stash create`, 工作区脏就真写对象, 而本环境的文件删除拦截层会顺着这次写入把 `.git/objects` 批量删进回收站, 表现为 `fatal: <oid> is not a valid object` 并导致对象库大面积损坏 (2026-09-19 事故, 详见 [pitfalls](memory-bank/pitfalls.md))。
- **唯一可靠规避: 合并前先把工作区弄干净**(先提交, 或把改动移出去)。同理避免在工具 shell 里跑 `git stash` / `git rebase` / `git checkout`(脏工作区时)等会触发 stash 的操作; 高风险 git 操作请让用户在自己的普通终端执行。
- **提交后必查 ref**: 本 worktree 每次 `git commit` 的 ref 更新都可能被拦截层静默丢弃, 必须核对 `HEAD` == `refs/heads/<branch>` == loose/packed-refs; 用 `.agents/skills/my-commit-flow/scripts/verify_ref.py` 核并按它打印的步骤修复 —— **不要只看 commit 输出**。
- 高风险 git 操作前先整份备份 `.git`(`cp -a .git <备份路径>`)。
- 机检与停手点一律走 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md)(预检自动查落后/脏工作区/红线文件/staged 暴增; rebase 与 push 仍由执行者按判据手动跑)。

## 提交 / PR

> **步骤、命令与机检脚本一律走 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md)** —— 预检 → 闸门 → 逐路径暂存 → 提交并核 ref 三处 → 推 Gitee → 尝试一次 GitHub 直连 → 查幽灵 diff(脚本: `preflight.py` / `commit.py` / `verify_ref.py` / `push.py`)。**本节只留口径与红线, 不重复命令**。

- **协作主线**: 日常开发在 `develop`, 统一以 **Gitee 的 `develop`** 为准; **交付与否只看 Gitee 上有没有该提交**。GitHub 只作镜像, **允许滞后** —— 不要用 GitHub 的提交状态判断进度(直连不稳定, 会误判成"改动没推上去")。
- **用户说"提交" = commit + push**, 一次流程走完 —— **触发词只认"提交 / 入库 / 推上去"这类显式指令; "继续 / 接着做 / ok / 你看着办"一律不算** (2026-09-20 用户指定): 没等到触发词就**只 commit 不 push**(或先问一句)。**本条是"提交 / push"口径的单点定义, 优先于 `memory-bank/` 里的历史表述**(2026-09-10 的"绝对不要 push"已作废, 不在知识库复述)。
- **推送顺序固定**: 先推 Gitee(必须成功)→ 核对远端 ref == 本地 → 再**尝试一次** GitHub 直连; 直连失败**只如实报告一次** —— 不重试 / 不换代理 / 不改走 SSH / 不回滚改写 Gitee 上已完成的推送。
- **提交信息**: 中文, **一句话概述 + 详细描述** —— 首行说清"改了什么 / 为什么"(参照 `git log` 风格), 空一行后写动机 / 取舍 / 影响面 / 实测数字; 单句能说清的小改只写首行。**数字必须提交那一刻实测**, 不沿用会话中途量的旧值。(本节只留口径; 逐条机检 —— 远端指向 / push 前 fetch / 逐路径暂存 / 提交前测试与 yapf / 核 ref 三处 / 查幽灵 diff —— 全部走 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md), 不在此复述。)
