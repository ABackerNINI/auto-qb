# AGENTS.md

> 所有 AI 编码代理的统一入口 (Copilot / Codex / Cursor / Gemini CLI / Claude Code / ZCode / Trae 通用)。
> 完整知识库在 `memory-bank/` (Memory Bank 模式) — 本文件只放路由与硬约束; 不要凭印象回答项目问题, 按路由深入后再动代码。

## 会话协议

> 完整规程(含任务档案模板)见 [.agents/skills/memory-bank/SKILL.md](.agents/skills/memory-bank/SKILL.md); 机械守卫 `tests/test_memory_bank.py`。

- **开始**: **①先拉取远程分支** —— `git remote -v` 确认主线远端 (Gitee), 再 `git pull --rebase <remote> develop` (分支名**必须写**), 确认 `git status -sb` 不落后后再开工; **禁止在落后的分支上动手改代码** (2026-09-19 用户指定; 命令与机检见 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md) 的 S1, 或直接跑 `python .agents/skills/my-commit-flow/scripts/preflight.py`) —— 拉取前先把工作区弄干净, 理由见「⚠️ 环境硬约束: Git 操作」。再 ②读 [memory-bank/activeContext.md](memory-bank/activeContext.md) (当前焦点) + [memory-bank/README.md](memory-bank/README.md) 路由表, 按任务选择深入文档; 已有 `tasks/` 档案的任务从档案续作。
- **收尾 (5 步 DoD)**: ①更新 activeContext (已完成条目**迁出**到 `progress.md` / 主题文档, 不是追加流水账) ②命中阈值的任务在 `memory-bank/tasks/` 立档 (命名 `YY-MM-DD-<slug>.md`, **先按 slug 查重再建**) + 跑 `python scripts/gen_tasks_index.py` 重建索引 (不要手改 `_index.md`) ③代码事实变更回写 `memory-bank/` 对应文档与根 `README.md` (测试基线只改 `testing.md`) ④跑 `uv run pytest tests -q` 并把实测数字记进 `testing.md` ⑤新坑追加 `pitfalls.md`。
- **立档阈值** (满足任一条**必须**立档): ①跨 ≥2 次会话; ②单会话 ≥5 轮指令或改动 ≥3 个源文件; ③出现"计划/方案/波次/第 N 轮/后续阶段"等长周期表述; ④需产出计划文档或交付报告。其余小修与答疑只记 activeContext。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。发现文档漂移时以代码为准并回写文档。

- **计划产出**: 列计划时使用 `delivery-artifact` skill 产出文档, 将计划文档放入 `docs/plans/` 中; **格式一律为单文件 HTML (`.html`), 不使用 Markdown (`.md`)** —— `docs/plans/` 下的计划文档若出现 `.md` 即为违规, 需转为 HTML; 命名统一为"日期-时间-标题", 如 `26-09-17-0906-improve-webui-plan.html`, 意思为"26年9月17日上午9点6分的改进webui计划", 方便检索, 注意需通过命令获取当前准确的日期和时间, 不要靠记忆!
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
   - 踩过的坑 (2026-09-20): 用户只问"本项目能启用 Playwright 吗", 代理一路做到入池 + 认领 +
     出计划 + 4 次推送, 最后全部 revert。根因是把"提议 → 用户说继续"当成了全权授权, 又拿
     「收尾 DoD / 立档阈值 / 入池」三条规则给自己加码 —— 那三条的前提都是"正在执行任务"。

## 红线 (生产文件, 禁止改动/提交)

- **`config.yml`**: 用户真实生产配置 (真实 PT 站点域名、tracker 规则、qB 凭据引用), 不是示例! 示例用 `minimal.yml` / `test_yamls/`。
- **`auto-qb-data/`**: 运行时数据目录 (state.json / 锁 / 日志 / 跳检备份), 已 gitignore; 不要"顺手"格式化或重排。

## 命令

```bash
# 依赖统一走 uv (pyproject.toml + uv.lock); 首次/依赖变更后先 `uv sync`
uv run pytest tests -q                                 # 全量测试 (pytest.ini 已带分支覆盖率; 基线数字单点见 memory-bank/testing.md 顶部)
uv run pytest tests/test_grouping.py -q
uv run pytest tests -q --no-cov                        # 快速迭代 (跳过覆盖率报表)
uv run python src/auto-qb.py config.yml --dry-run      # 运行 (需真实 qBittorrent; 一律先 --dry-run 观察)
yapf -i src/auto_qb/**/*.py                            # 格式化 (.style.yapf: facebook 风格, 列宽 120)
```

- 测试命令 2026-09-17 实测通过; 命令与 `memory-bank/testing.md` 同源维护 (基线数字单点见该文件顶部)。
- 新增测试必须同步该测试文件头部 docstring 的 "## 测试计划" 清单 (项目明文规定)。

## 💡 CI 报错排查: 建议先在本机 WSL 复现 (推荐, 非强制)

> GitHub Actions 跑 **Linux (ubuntu-latest, Python 3.12/3.13 矩阵)**, 而本机是 Windows ——
> 存在一整类"**Windows 全绿 / Linux 全红**"的失败 (2026-09-19 实测: 一次 CI 红 4 项, 本地却 0 失败)。
> 与其推上去等 CI 一轮, **建议先在本机 WSL 里复现再改** —— 15~22 秒出结果, 还能反复跑。
> 这是**推荐做法不是硬性要求**: 情形明显、或改动不涉及平台行为时, 直接改直接推也可以。

```bash
# ① 首次: 建一份 Linux 沙箱(ext4 上跑, 别直接在 /mnt/d 的 drvfs 上跑 —— 符号链接/权限语义不一样)
wsl -- bash -c 'cp -r /mnt/d/Projects/<仓库> ~/aqb && cd ~/aqb && rm -rf .venv __pycache__'
#   (或更干净: 在仓库根 tar --exclude=./.venv --exclude=./.git ... | tar -xf - 到 ~/aqb)
wsl -- bash -c 'curl -LsSf https://astral.sh/uv/install.sh -o ~/uv-install.sh && sh ~/uv-install.sh'  # 装 uv, 只需一次
wsl -- bash -c 'export PATH="$HOME/.local/bin:$PATH"; cd ~/aqb && uv sync && uv run pytest tests -q'

# ② 之后每次改动: 只同步改过的文件再跑
wsl -- bash -c 'export PATH="$HOME/.local/bin:$PATH"; cd ~/aqb && uv run pytest tests -q'
# 对上 CI 的矩阵版本: uv sync -p 3.12 / -p 3.13 再跑
```

- **判据**: 凡是涉及 ①副作用记账器判越界 ②平台专属模块 (`winreg` 等) ③真实 socket/子进程 的改动,
  **"本机全量绿"不算数**, 必须在 Linux 上验一遍。典型三类坑与修法见 [pitfalls.md](memory-bank/pitfalls.md)
  「Windows 全绿 / Linux 全红」条目 (POSIX `shutil.rmtree` 传纯文件名 + `dir_fd` / `atomic_write("")` 往仓库外
  写临时文件 / 用例 patch 错名字导致真连网络)。
- 沙箱是**可复用**的: `~/aqb` 一直留着, 改完 `cp` 同步改过的文件即可; 不必每次重建。
- 推上去之后想确认 CI 结果时 (本机没装 `gh`), 用
  `curl -s https://api.github.com/repos/ABackerNINI/auto-qb/actions/runs?per_page=6` 看 `head_sha` 与 `conclusion`。

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
| **CI 报错 / 平台差异复现** | 本文件「💡 CI 报错排查: 建议先在本机 WSL 复现」+ [pitfalls.md](memory-bank/pitfalls.md)「Windows 全绿 / Linux 全红」 |
| **撞见计划外问题: 该不该现在修** | [scope-guard skill](.agents/skills/scope-guard/SKILL.md) |
| **建 issue 报告 / 改 issue 状态** | [create-issue skill](.agents/skills/create-issue/SKILL.md) + [issues/_index.md](memory-bank/issues/_index.md) (8 类类型 × 便签/标准两档) |
| **提交 / 推送 (commit + push)** | [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md) (口径在本文件「提交 / PR」节) |
| 改代码前必读 (风险点/陷阱) | [memory-bank/pitfalls.md](memory-bank/pitfalls.md) |
| XX 做了吗 / 计划怎么做 | [memory-bank/progress.md](memory-bank/progress.md) |
| 跨会话任务档案 | [memory-bank/tasks/_index.md](memory-bank/tasks/_index.md) |

## ⚠️ 环境硬约束: Git 操作 (AI 工具 shell 特有, 用户自己的普通终端无此问题)

> 本仓库 9 个 worktree 共享同一个对象库 `D:/Projects/auto-qb/.git`, **任一处出事波及全部**, 备份要备份主 gitdir。

- **禁止在工具 shell 里跑「非快进合并 + 工作区脏」**: git 2.55 在**非快进合并**时**无条件**调用 `git stash create`; 工作区脏时它要真写对象, 而本环境的文件删除拦截层会顺着这次写入把 `.git/objects` **批量删掉**(走回收站), 表现为 `fatal: <oid> is not a valid object` / `unable to read tree`, 随后对象库大面积损坏。2026-09-19 事故即由此丢 318 个对象 + 全部 reflog。详见 [pitfalls](memory-bank/pitfalls.md)。
- **安全矩阵 (2026-09-19 实测)**: 非快进合并 + 干净工作区 = 安全; 快进合并 + 脏工作区 = 安全; **非快进合并 + 脏工作区 = 必炸**。
- **唯一可靠规避: 合并前先把工作区弄干净**(先提交, 或把改动移出去)。`merge.autoStash=false` **挡不住**(全局配置与 `-c` 均实测无效); 关沙箱、换系统 git、剔除 PATH 里的 safe-bin 同样无效 —— `rm` 是 **bash 函数**, 拦截层仍在。
- 同理**避免**在工具 shell 里跑 `git stash` / `git rebase` / `git checkout`(脏工作区时)等会触发 stash 的操作; 高风险 git 操作请让用户在自己的普通终端执行。
- **提交后必查 ref**: 本 worktree 每次 `git commit` 的 ref 更新都可能被拦截层静默丢弃, 必须核对 `HEAD` == `refs/heads/<branch>` == loose/packed-refs; 用 `.agents/skills/my-commit-flow/scripts/verify_ref.py` 核并按它打印的步骤修复(旧的 `.workbuddy-ai/fix-branch-ref.sh` 已不存在, 勿再引用) —— **不要只看 commit 输出**。
- 高风险 git 操作前先整份备份 `.git`(`cp -a .git <备份路径>`)。
- **本节是事故说明, 不重复步骤**: 把上述红线做成机检与停手点的, 是 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md)(预检会自动查落后/脏工作区/红线文件/staged 暴增; rebase 与 push 仍由执行者按判据手动跑)。

## 提交 / PR

> **步骤、命令与机检脚本一律走 [my-commit-flow skill](.agents/skills/my-commit-flow/SKILL.md)** —— 预检 → 闸门 → 逐路径暂存 → 提交并核 ref 三处 → 推 Gitee → 尝试一次 GitHub 直连 → 查幽灵 diff(脚本: `preflight.py` / `commit.py` / `verify_ref.py` / `push.py`)。**本节只留口径与红线, 不重复命令**。

- **协作主线**: 日常开发在 `develop`, 统一以 **Gitee 的 `develop`** 为准; **交付与否只看 Gitee 上有没有该提交**。GitHub 只作镜像, **允许滞后** —— 不要用 GitHub 的提交状态判断进度(直连不稳定, 会误判成"改动没推上去")。
- **用户说"提交" = commit + push**, 一次流程走完 —— **触发词只认"提交 / 入库 / 推上去"这类显式指令; "继续 / 接着做 / ok / 你看着办"一律不算** (2026-09-20 用户指定): 没等到触发词就**只 commit 不 push**(或先问一句)。**本条是"提交 / push"口径的单点定义, 优先于 `memory-bank/` 里的历史表述** (`conventions.md` 2026-09-10 的"绝对不要 push"已作废, 仅作沿革保留)。
- **推送顺序固定**: 先推 Gitee(必须成功)→ 核对远端 ref == 本地 → 再**尝试一次** GitHub 直连; 直连失败**只如实报告一次** —— 不重试 / 不换代理 / 不改走 SSH / 不回滚改写 Gitee 上已完成的推送。
- **提交信息**: 中文, **一句话概述 + 详细描述** —— 首行说清"改了什么 / 为什么"(参照 `git log` 风格), 空一行后写动机 / 取舍 / 影响面 / 实测数字; 单句能说清的小改只写首行。**数字必须提交那一刻实测**, 不沿用会话中途量的旧值。
- **硬纪律(逐条都有机检, 命令见 skill)**:
  - 远端先确认指向 Gitee(历史 clone 的 `origin` 可能是 GitHub 镜像);`git pull <remote>` **必须带分支名**, 不带只 fetch 不合并。
  - **push 前再 fetch 一次** —— `git status -sb` 的 ahead/behind 是上次 fetch 的快照, 不会自己刷新。
  - **只暂存本次范围**: 逐路径 `git add <文件...>`, 不用 `-A`; 清单里不得混入用户自己的未提交改动(`想法.md` 高危, `config.yml` 红线)。
  - 提交前: 全量测试通过; 改过的 Python 先过 `yapf -i`; 用户可见行为变更同步 `README.md` 与 `memory-bank/`。
  - **提交后必核 ref 三处**(`HEAD` == `refs/heads/<branch>` == loose/packed-refs), 不要只看 commit 输出 —— 见下节。
  - **提交后必查幽灵 diff**: `git status --short` 看两列 —— `M `(第一列) = 待提交, ` M`(第二列) = 已提交过但工作区又脏。权威判据(两者同时成立才算已提交): `git log --oneline -1 -- <文件>` 有记录 **且** `git diff --quiet -- <文件>` 退出码 0。发现后补一次"格式化, 无行为变化"提交, 不要改写已入库的提交。
