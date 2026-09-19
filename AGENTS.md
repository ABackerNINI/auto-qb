# AGENTS.md

> 所有 AI 编码代理的统一入口 (Copilot / Codex / Cursor / Gemini CLI / Claude Code / ZCode / Trae 通用)。
> 完整知识库在 `memory-bank/` (Memory Bank 模式) — 本文件只放路由与硬约束; 不要凭印象回答项目问题, 按路由深入后再动代码。

## 会话协议

> 完整规程(含任务档案模板)见 [.agents/skills/memory-bank/SKILL.md](.agents/skills/memory-bank/SKILL.md); 机械守卫 `tests/test_memory_bank.py`。

- **开始**: 读 [memory-bank/activeContext.md](memory-bank/activeContext.md) (当前焦点) + [memory-bank/README.md](memory-bank/README.md) 路由表, 按任务选择深入文档; 已有 `tasks/` 档案的任务从档案续作。
- **收尾 (5 步 DoD)**: ①更新 activeContext (已完成条目**迁出**到 `progress.md` / 主题文档, 不是追加流水账) ②命中阈值的任务在 `memory-bank/tasks/` 立档 (命名 `YY-MM-DD-<slug>.md`, **先按 slug 查重再建**) + 跑 `python scripts/gen_tasks_index.py` 重建索引 (不要手改 `_index.md`) ③代码事实变更回写 `memory-bank/` 对应文档与根 `README.md` (测试基线只改 `testing.md`) ④跑 `uv run pytest tests -q` 并把实测数字记进 `testing.md` ⑤新坑追加 `pitfalls.md`。
- **立档阈值** (满足任一条**必须**立档): ①跨 ≥2 次会话; ②单会话 ≥5 轮指令或改动 ≥3 个源文件; ③出现"计划/方案/波次/第 N 轮/后续阶段"等长周期表述; ④需产出计划文档或交付报告。其余小修与答疑只记 activeContext。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。发现文档漂移时以代码为准并回写文档。

- **计划产出**: 列计划时使用 `delivery-artifact` skill 产出文档, 将计划文档放入 `docs/plans/` 中; **格式一律为单文件 HTML (`.html`), 不使用 Markdown (`.md`)** —— `docs/plans/` 下的计划文档若出现 `.md` 即为违规, 需转为 HTML; 命名统一为"日期-时间-标题", 如 `26-09-17-0906-improve-webui-plan.html`, 意思为"26年9月17日上午9点6分的改进webui计划", 方便检索, 注意需通过命令获取当前准确的日期和时间, 不要靠记忆!

## 黄金法则 (来自设计原则, 违反即破坏设计)

1. **幂等性**: 动作重复执行不得产生副作用; "每天一次"等窗口语义必须靠 state_file 去重 (`record_execution`), 不依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置范围生效。
3. **状态持久化**: 跨轮次状态统一进 state_file, 程序退出时才落盘。
4. **fail-fast**: 配置在 `config.validate_config` 全量校验并聚合报错; 校验之后的代码假定配置正确, 不做防御性检查; **新配置键必须加入 validate_config 并同步 `config/schema.py`** (守卫测试会查)。
5. **单一写线程**: 只有主循环线程修改任务队列结构与 state_file; 不要引入绕开该假设的并发代码。

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
| 改代码前必读 (风险点/陷阱) | [memory-bank/pitfalls.md](memory-bank/pitfalls.md) |
| XX 做了吗 / 计划怎么做 | [memory-bank/progress.md](memory-bank/progress.md) |
| 跨会话任务档案 | [memory-bank/tasks/_index.md](memory-bank/tasks/_index.md) |

## 提交 / PR

- 日常开发在 `develop` 分支; 提交信息为中文一句话概述 (参照 `git log` 风格)。
- **用户说"提交"= 只 `commit`, 不 `push`**; 需要推送时用户会明说。
- **推送顺序与策略 (2026-09-19 用户指定)**:
  - 远端: `origin` = Gitee (`https://gitee.com/ABacker/auto-qb.git`); `github` = `https://github.com/ABackerNINI/auto-qb.git` (没有就 `git remote add github <url>`)。
  - **先推 Gitee**: `git push origin develop` —— 稳定, 正常推。
  - **再尝试 GitHub, 且必须直连不走代理**: 全局 git config 里给 github.com 配了 per-URL 代理
    (`http.https://github.com.proxy=http://127.0.0.1:10808`), 推送时用 `-c` 覆盖为空即禁用:
    ```bash
    git -c http.https://github.com.proxy= push github develop
    ```
  - **GitHub 直连失败不重试**: 直连本来就不稳定 (2026-09-19 实测 `fatal: ... Recv failure: Connection was reset`)。
    失败即**如实报告**, 不重试、不换代理再试、不改走 SSH、不调整超时反复试 —— 交由用户决定。
  - **不要因为 GitHub 失败而回滚或改写 Gitee 上已完成的推送**: 两个远端互不影响, Gitee 成功就算推送达成。
- 提交前: 全量测试通过; 用户可见行为变更需同步 `README.md` 与 `memory-bank/`。
- **只暂存本次范围**: 逐路径写 `git add <文件...>`, 不用 `git add -A`; 暂存清单里不得混入用户自己的未提交改动 (`想法.md` 属高危, `config.yml` 是红线)。
- **提交前先格式化**: 改过的 Python 文件先过 `yapf -i <file>` (含 `tests/`)。
- **提交后必查"幽灵 diff"**: 格式化工具 / 编辑器在**提交之后**重排文件, 文件其实已入库但工作区又变脏 — 极易被误判成"没提交上"。发现后**把收尾差异补一次提交** (信息注明"格式化, 无行为变化"), 不要改写已入库的提交。
- **判别"是否已提交"看 `git status --short` 两列, 别只看 `M`**:
  - `M ` (M 在**第一列**) = 已暂存待提交; ` M` (M 在**第二列**) = **已提交过**、工作区又有新改动;
  - 权威判据 (两者同时成立才算已提交): `git log --oneline -1 -- <文件>` 有记录 **且** `git diff --quiet -- <文件>` 退出码 0;
  - 提交完成后 `git status --short` 只应剩下已知的、用户自己的改动 (如 `M 想法.md`) — 仍看到本次改动文件即为幽灵 diff。
