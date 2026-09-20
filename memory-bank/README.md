# auto-qb Memory Bank (AI 知识库索引)

> 面向 AI 助手的项目知识库。目标: 让 AI 在不重读全部源码的前提下, 快速建立对项目的准确心智模型, 并安全地修改代码。
>
> 所有内容均基于 2026-09-05 的 `develop` 分支源码逐文件核实 (commit `51374bd` 后: 同步 README 文档漂移 + tracker 匹配统一为精准匹配)。若代码与本文冲突, 以代码为准并回写更新本文。
>
> 2026-09-14 知识库改造: 新增根级 [AGENTS.md](../AGENTS.md) 统一跨 agent 入口与 [activeContext.md](activeContext.md) 易变层; 测试基线数字单点维护于 [testing.md](testing.md), 其它文档一律引用不手抄。
>
> 2026-09-15 全面迁移为 Memory Bank 结构: 原 `ai/` 整体迁入 `memory-bank/` 并按六核心文件语义重命名 (01→productContext, 02→systemPatterns, 09→progress, 10→activeContext), 新增 projectbrief / techContext / tasks/; `.github/instructions/memory-bank.instructions.md` 恢复原版 (applyTo: 'memory-bank/**')。核心文件职责: projectbrief=目标与范围, productContext=为什么存在/领域知识, systemPatterns=架构与技术决策, techContext=技术栈与环境, **activeContext=当前焦点 (会话入口)**, progress=完成与规划。
>
> 2026-09-17 会话协议加固: 新增 skill 载体 [../.agents/skills/memory-bank/SKILL.md](../.agents/skills/memory-bank/SKILL.md) (可 `/memory-bank` 调用; 先建于 `.github/skills/`, 同日按仓库技能根惯例搬到 `.agents/skills/`), **立档阈值与收尾 DoD 同时写进 always-on 入口** (`AGENTS.md` / `.github/copilot-instructions.md`) — 修掉"规则只在 applyTo memory-bank/** 的 instruction 里⇒决策时看不见"的错位; `tasks/` 按专题回填 TASK001~TASK010, `activeContext.md` 瘦身回易变层; 守卫 [../tests/test_memory_bank.py](../tests/test_memory_bank.py)。
> 2026-09-19 计划外问题入池: 拆成两个 skill —— [scope-guard](../.agents/skills/scope-guard/SKILL.md) 只管"该不该现在修"(**计划外的代码/文档缺陷一行都不改**, 协作开发时"顺手修"会让提交混进两条意图并撞车), [create-issue](../.agents/skills/create-issue/SKILL.md) 可**单独使用**, 负责在 `issues/<YY-MM-DD-HHMM>-<slug>.html` 写够别人直接开工的详细报告; 索引 `issues/_index.md` 是**生成物**(每行 = 状态 · 日期 · 简述 · 链接), 由 [../.agents/skills/create-issue/scripts/gen_issues_index.py](../.agents/skills/create-issue/scripts/gen_issues_index.py) 重建; 状态五取值 `Open` / `In Progress` / `Fixed` / `WontFix` / `Duplicate`。
>
> 2026-09-18 任务档案改名与索引生成化: `tasks/TASKnnn-<slug>.md` → `tasks/YY-MM-DD-<slug>.md` —— 全局单调序号在 9 个并行 worktree 下必然撞号 (实测: TASK014/TASK015 同一专题两份且逐字节相同、zcode 分支把同一提交编成 TASK012 而主线编成 TASK014), 改成"日期到天 + 专题 slug"后, 同一天同一专题必然撞到同一路径, 重复当场暴露而不是静默变两份; 旧编号保留在各档案 `**Legacy-ID:**` 供历史引用回溯; `_index.md` 降级为**生成物**, 由 [../scripts/gen_tasks_index.py](../scripts/gen_tasks_index.py) 产出 (分区内按 `Updated` 倒序), 合并冲突只需重跑脚本。计划: [docs/plans/26-09-18-1928-memory-bank-task-id-plan.html](../docs/plans/26-09-18-1928-memory-bank-task-id-plan.html)。

## 按任务选择文档

| 你要做的事 | 先读 |
|-----------|------|
| **会话开始/收尾** (现在做什么/做到哪) | [activeContext.md](activeContext.md) |
| **会话协议 / 立档阈值 / 收尾 DoD** | [../.agents/skills/memory-bank/SKILL.md](../.agents/skills/memory-bank/SKILL.md) |
| 项目目标与范围 (纲领) | [projectbrief.md](projectbrief.md) |
| 技术栈/开发环境/约束 | [techContext.md](techContext.md) |
| 第一次接触本项目 / 问"这是什么" | [productContext.md](productContext.md) |
| 理解主循环/任务队列/数据层/异步校验 | [systemPatterns.md](systemPatterns.md) |
| 找某个功能在哪个文件 / 加新模块 | [modules.md](modules.md) |
| 改规则、条件、动作相关代码 | [rule-system.md](rule-system.md) |
| 改配置解析 / 加配置键 / 排查配置问题 | [config-reference.md](config-reference.md) |
| 写任何代码之前 (命名/风格/约定) | [conventions.md](conventions.md) |
| 写测试 / 跑测试 | [testing.md](testing.md) |
| 改代码前必读 (魔法值/风险点/文档漂移) | [pitfalls.md](pitfalls.md) |
| 问"XX做了吗 / XX计划怎么做" | [progress.md](progress.md) |
| 跨会话任务档案 (立档/查档) | [tasks/_index.md](tasks/_index.md) |
| **撞见计划外问题: 该不该现在修** | [../.agents/skills/scope-guard/SKILL.md](../.agents/skills/scope-guard/SKILL.md) |
| **建 issue 报告 / 改 issue 状态** | [../.agents/skills/create-issue/SKILL.md](../.agents/skills/create-issue/SKILL.md) + [issues/_index.md](issues/_index.md) (8 类类型 × 便签/标准两档) |
| **提交 / 推送 (commit + push)** | [../.agents/skills/my-commit-flow/SKILL.md](../.agents/skills/my-commit-flow/SKILL.md) (口径在根 AGENTS.md「提交 / PR」节) |
| 做 UI/视觉设计: 找可挑选的风格与组件参考 (20 套) | [../resources/ui-component-libraries/modelscope.dsv4.1flash/README.md](../resources/ui-component-libraries/modelscope.dsv4.1flash/README.md) |

## 一分钟速览

- **项目**: `auto-qb` — 基于 `qbittorrent-api` 的 PT 种子自动化管理工具 (标签/分类/HR 管理、辅种分组与缺文件检查、自定义规则引擎、tracker 级限速、全局限速曲线)。
- **形态**: 单机长驻 Python 程序, 无包管理配置 (pip 装依赖即用), 入口 `python src/auto-qb.py [config.yml]`, 主循环 2s tick, 任务队列驱动。
- **核心设计**: `QbManager` 由 6 个 mixin 组合; 所有工作 (种子刷新/规则/内置功能/校验轮询) 统一为带内置 interval 的任务, 进单一时间优先堆; `TorrentStore.apply_sync` 走 qB `/api/v2/sync/maindata` rid 增量同步(只对变化种子调 `apply_delta`), `TorrentRecord` 是种子数据的唯一所有者(快照 slot + `_raw` 兜底); `QbApi` Facade写后同步快照; 主循环单线程, 唯一修改队列与 state_file 的线程。
- **测试**: `pytest` + `tests/helpers.py` 全 Fake (无需真实 qBittorrent; 另有 `FakeQbServer` 本地假 HTTP 服务, 供真实 `qbittorrent-api`/requests 栈的集成测试)。基线数字 (passed/skipped/覆盖率) 单点维护于 [testing.md](testing.md) 顶部, 勿在他处手抄; 全量运行约 12 秒(含覆盖率报表)。
- **文档**: `README.md` (用户视角) 与 `想法.md` (设计草稿) 是上游文档, 已于 2026-09-05 与代码核对同步; 本知识库是代码实况的核对版, 发现漂移时回写更新 (遗留差异见 [pitfalls.md](pitfalls.md))。

## 修改代码的黄金法则 (来自项目设计原则)

1. **幂等性**: 动作重复执行不得产生副作用; "每天一次"等窗口语义必须靠 state_file 去重 (`record_execution`), 不能依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置的范围生效。
3. **状态持久化**: 跨轮次状态统一进 `state_file`, 程序退出时才落盘 (减少磁盘写入)。
4. **fail-fast**: 配置在 `config.validate_config` 全量校验并聚合报错, 校验之后的解析与运行代码**假定配置正确**, 不做防御性检查; 新配置键必须加入 `validate_config` 校验。
5. **单一写线程**: 只有主循环线程修改任务队列结构与 state_file; 不要引入绕开该假设的并发代码。

## 快速命令

```bash
# 测试 (项目 venv: .venv, Python 3.12)
.venv/Scripts/python.exe -m pytest tests -q            # 全量 (基线数字见 testing.md 顶部)
.venv/Scripts/python.exe -m pytest tests/test_grouping.py -q
.venv/Scripts/python.exe -m pytest --cov=src --cov-report=term-missing tests -q

# 运行 (需真实 qBittorrent; 干跑用 -n)
python src/auto-qb.py config.yml --dry-run

# 代码格式 (yapf, 配置见 .style.yapf: facebook 风格, 列宽 120)
yapf -i src/auto_qb/**/*.py
```
