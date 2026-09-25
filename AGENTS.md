# AGENTS.md

> 所有 AI 编码代理的统一入口 (Copilot / Codex / Cursor / Gemini CLI / Claude Code / ZCode / Trae 通用)。完整知识库在 `memory-bank/` (Memory Bank 模式) — 本文件只放**路由与硬约束**; 不要凭印象回答项目问题, 按路由深入后再动代码。
> ⚠ **本文件有 8000 字符硬上限** —— IDE 注入时超出即被 `slice` 掉, 尾部内容模型根本看不到。改完用 `commands run doc.caps` 自查 (已挂 `my-commit-flow` 包的闸门, 改动本文件时预检会自动提示)。

## 知识库路由 (两层: 本文件粗路由 → `memory-bank/README.md` 细路由)

> **「按任务读哪份文档」的单点在 [memory-bank/README.md](memory-bank/README.md) 的细路由表** —— 本文件不复述, 免得两处各自演化。三条动作级提示:
> - **改代码前**: 读 [pitfalls/_index.md](memory-bank/pitfalls/_index.md) —— 7 类 (git · web-ui · backend · testing · ops · kb · docs), 按动作选类再进类索引。
> - **跑 git 命令前**: 必读 [pitfalls/git/_index.md](memory-bank/pitfalls/git/_index.md) —— ref 静默丢弃 / 推送只认 `ls-remote` 等本机硬约束单点在里面 (旧 rebase/merge/stash 毁库禁令已随拦截层修复于 2026-09-25 解除)。
> - **检索纪律**: 先索引、后 grep、**禁止整读**任一目录; 不确定关键词时 `grep -rn "<词>" memory-bank/` 兜底。

## 会话协议

> 完整规程 (会话开始 / 收尾 DoD 5 步 / 立档阈值 4 条 / 任务档案模板) 见 [memory-bank skill](.agents/skills/memory-bank/SKILL.md); 机械守卫 `tests/test_memory_bank.py`。本节只留入口。

- **开始**: ①**先同步** (问答/只读轮次跳过; **首个执行动作 —— 改文件 / 跑测试 / 任何 git 写操作 —— 之前必须完成**) —— `git fetch gitee develop` (远端与分支名**必须写**; 远端名不同先 `git remote -v` 确认 Gitee 主线); 落后与否只认 `git ls-remote gitee develop` 对比本地 HEAD (`status -sb` 的 ahead/behind 是快照, 会给假绿灯); 纯落后且工作区干净 → `git merge --ff-only FETCH_HEAD` 快进; 树脏 → **停下报告, 禁止自行清理**; 已分叉 (本地有独有提交) → 直接开工, 提交时按 my-commit-flow 合流; **禁止在落后分支上改代码** (机检: 开工自检 `commands run my-commit-flow.sync` —— 只读, 结果贴进回复; 提交/推送时跑完整 preflight)。②看会话滚动状态: `commands run kb.active` 列 [memory-bank/activeContext/](memory-bank/activeContext/_about.md) 切片(全量按最后活动倒序 + 陈旧标记, 只打印不写文件); 该读哪份文档走上面的路由。③**只动当前这一个 clone** —— 跨仓库操作**绝对禁止**, 须用户显式说「授权」(见「🔴 跨仓库操作」节)。
- **收尾**: 按 skill 的 5 步 DoD —— 更新 activeContext 切片(已完成条目**迁出**到 progress) / 达阈值则立档 + `commands run kb.index` 重建索引 / 代码事实变更回写 `memory-bank/` 与根 README / 跑 `commands run test.full` 并新建基线切片记实测数字(`testing/baselines/`, 体例见 `testing/baseline.md` 口径段) / **新坑按动作写进 `pitfalls/<类>/<主题>.md`(补三行头元数据)并重跑 `commands run kb.index`**。若这一轮踩到了**已记的坑**, 把该条 `复发` +1, 并在档案里写一句为什么没命中(路由没到 / 文件没读 / 读了没照做)。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`; 漂移以代码为准并回写。

## 产出口径

- **计划文档**: 用 `delivery-artifact` skill, 放 `memory-bank/plans/`; **一律单文件 HTML** (出现 `.md` 即违规)。
- **报告**: 审计 / 故障取证 / 可行性分析 → `memory-bank/reports/`; 四工位决策树与 `doc-*` 协议单点见 [conventions/doc-forms.md](memory-bank/conventions/doc-forms.md)。
- **HTML 一律 dark 主题**: 深色底 + 浅色字 + 样式里写 `color-scheme: dark`, **禁止浅底黑字**; 配色规格与文件命名见 [conventions/webui.md](memory-bank/conventions/webui.md)「HTML 文档一律 dark 主题」。

## 黄金法则 (来自设计原则, 违反即破坏设计)

1. **幂等性**: 重复执行不得有副作用; "每天一次"等窗口语义靠 state_file 去重 (`record_execution`), 不依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置范围生效。
3. **状态持久化**: 跨轮次状态统一进 state_file; 优雅退出立即落盘 + 运行期按 state_save_interval 周期落盘(配置端下限 30s, 0=关), 非优雅终止丢失窗口 ≤ 间隔。
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

**命令一律经 `commands` 引擎调, 不在文档里抄** —— `commands run <task>` 里的 `<task>` 是包里的一条命令
(映射表在 [.commands/](.commands/) 各包的 `config.toml`, 引擎是 [commands skill](.agents/skills/commands/SKILL.md))。
❗`commands run <task>` **先直接试跑**, 报 command not found 才装一次 wrapper(幂等, 生成物已 gitignore):
`uv run python .agents/skills/commands/scripts/install_wrapper.py`(落仓库根 + PATH 目录,
PATH 那份用户级、跨 clone 共享 —— 装过一次就一直命中, 多数会话免装); 没装时也可展开
`uv run python .agents/skills/commands/scripts/run.py run <task>`。
`<task>` 用 `list` 里的 id(子包可写 `ship.commit`, 也可写全 `包/子包.<task>`)。
不知道调哪个就 `list` 逐级下钻(一级只出包 + 常显命令)。遇到**反复要跑 / 难拼 / 有陷阱写法**的命令,
按 SKILL.md 的收录协议自己 `add` 进包 —— 命令集靠这个长大, 不是靠人维护。

```text
commands run test.full    # 全量测试 (最新基线: commands run kb.baseline 列最近 3 条; 排障 --all)
commands run test.quick   # 快速迭代, 跳过覆盖率报表
commands run dev.run -- config.yml --dry-run   # 真机跑主程序 (需真实 qB; 一律先 --dry-run)
commands run dev.fmt -- <改过的 .py>           # 格式化 (.style.yapf: facebook, 列宽 120)
commands run env.sync     # 首次 / 依赖变更后同步依赖
```

- 依赖统一走 `uv` (`pyproject.toml` + `uv.lock`)。
- ⚠ `TMPDIR` 已内置在 `test.*` 里, **不要再手工加前缀** —— POSIX 的 `TMPDIR=x cmd` 在本 shell 不生效
  (实测 rc=1), 加了还会盖掉包里那个正确的值。判据见 [pitfalls/testing/tmpdir.md](memory-bank/pitfalls/testing/tmpdir.md)。
- 新增测试必须同步该文件头部 docstring 的 "## 测试计划" 清单。

## ⚠️ 环境硬约束: Git 操作 (AI 工具 shell 特有)

> **工作区模式: 多 clone 并行** (2026-09-20 用户决定, **已弃用 git worktree**): 每个 AI 实例用**一份独立克隆**, 跨 clone 同步一律走 Gitee `develop`。细则见 [conventions/collaboration.md](memory-bank/conventions/collaboration.md)「协作约定」。
> **完整判据与事故档案单点在 [pitfalls/git/_index.md](memory-bank/pitfalls/git/_index.md)**; 本节只留最容易致命的几条:

- ✅ **rebase / merge / stash 禁令已解除** (2026-09-25): 历史上删除拦截层会在这几类操作写入 `.git` 时批量删对象 (3 次事故), 该问题已修复, 恢复可用 —— 高风险历史整合前仍建议先 `cp -a .git <备份>`。落后主线首选「移出改动 → `merge --ff-only` 快进 → 施回改动 → 提交」(先同步后提交, 推送即快进)。
- **提交后必查 ref 三处**: `HEAD` == `refs/heads/<branch>` == loose/packed-refs, 用 `commands run my-commit-flow.verify-ref` 并按它打印的步骤修。**不要只看 commit 输出**。
- **判"推没推上"只看 `git ls-remote <远端> <分支>`** —— 本 shell 里 `refs/remotes/*` 的写入会被静默丢弃, 且 `git push --dry-run` 永远"成功"。
- 机检与停手点一律走 **task id**: `commands run my-commit-flow.preflight` / `ship.commit` / `ship.push` / `my-commit-flow.verify-ref`(`list my-commit-flow/ship` 看全流程, `show <task>` 看展开的命令与深读指针)。**包内 README 与 `references/` 只在排障 / 迁移时读** —— 日常整读它, 等于把"读整份文档找命令"的成本又搬回来。

## 🔴 跨仓库操作: 绝对禁止 (需显式强授权)

> **完整定义(含事故实证与止损纪律)见 [conventions/collaboration.md](memory-bank/conventions/collaboration.md)「🔴 跨仓库操作」节**; 本节只留红线。

- **除当前工作 clone 外, 对其它 clone 的任何写操作一律绝对禁止** —— 改文件 / `git apply` / 复制覆盖 / 跑 git 命令。
- **授权指令只认 `授权`**, 须用户**显式**说出; **「提交」不算** —— 它只授权 commit + push 到远端。
- 未授权时**停下来问**: 发现"改动在别的 clone 上不生效"该报告交由用户决定, **不能自己动手**。
- **跨工作区同步一律走 Gitee `develop`**, 没有第二种路径。

## 提交 / PR

> **步骤与机检一律走 task id**(不是文档): 收到"提交" → ①预检 `my-commit-flow.sync`, **远端有更新先按「同步路径」合并远端** → ②收尾回写文档(落在合并后的新基线上 —— 回写件是全体 clone 最热写点, 陈旧基线上写合并必撞) → ③`ship.commit`(**内含预检 + 闸门 + 核 ref 三处**; 落后未合流被预检 STOP) → ④推 Gitee `ship.push`(推送前预检 + 核远端 ref + 一次 GitHub 镜像尝试) → ⑤查幽灵 diff。**本节只留口径**; 原理与完整判据在包内 `references/pipeline.md`(排障才读)。

- **协作主线**: 日常在 `develop`, 以 **Gitee 的 `develop`** 为准; **交付与否只看 Gitee**。GitHub 只作镜像、**允许滞后** —— 别用 GitHub 状态判断进度。
- **用户说"提交" = commit + push**, 一次走完; **触发词只认"提交 / 入库 / 推上去"这类显式指令**, "继续 / 接着做 / ok / 你看着办"一律不算。**本条是提交口径的单点定义**, 优先于 `memory-bank/` 里的历史表述。
- **推送顺序固定**: 先推 Gitee (必须成功) → 核远端 ref == 本地 → 再**尝试一次** GitHub 直连; 失败**只如实报告一次**, 不重试 / 不换代理 / 不改走 SSH / 不回滚改写 Gitee 已完成的推送。
- **提交信息 = gitmoji + 中文**: 首行 `<gitmoji> <中文一句话概述>`, 空一行后写动机 / 取舍 / 影响面 / 实测数字; 小改只写首行。**数字必须是提交那一刻实测的**。选哪个 emoji 走 [gitmoji skill](.agents/skills/gitmoji/SKILL.md)。
- **先合并远端, 再收尾** (2026-09-26 定稿, 治「baseline 总是撞」): 收尾回写 (基线切片 / activeContext 切片 / 各 _index) 必须落在**合并远端之后**的新基线上 —— 预检落后即按「同步路径」合并, 再进入收尾; 回写文件**随主提交一并暂存**, 不推完再补一笔 (已推送的提交不能 amend + 强推)。
- **红线与闸门清单外置在 `.commands/my-commit-flow/.my-commit-flow.toml`** (包脚本强制读取, 缺了就停手引导生成)。
