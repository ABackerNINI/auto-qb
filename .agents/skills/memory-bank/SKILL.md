---
name: memory-bank
description: 'Memory Bank 会话协议与知识库维护。USE FOR: 会话开始/收尾、更新知识库/回写文档、任务立档 (tasks/)、activeContext/progress/pitfalls/testing 维护; 用户说"更新 memory bank"/"更新知识库"/"记一下这个任务"/"收尾"/"做到哪了"/"立档" 时。DO NOT USE FOR: 单纯写代码或回答技术问题 (那只需按 AGENTS.md 路由读主题文档)。'
user-invocable: true
---

# Memory Bank 会话协议

本仓库用 Memory Bank 模式维护跨会话上下文: 知识库在 `memory-bank/`, 统一入口是根 `AGENTS.md`。
本 skill 只负责**会话的两个端点**(开始 / 收尾)与**任务立档**; 领域知识(架构/规则/配置/约定…)由 `memory-bank/` 主题文档承担, 不要写进本 skill。

## 会话开始 (3 步)

1. 读 `memory-bank/activeContext.md` — 最后更新、进行中事项、下一步候选。
2. 读 `memory-bank/README.md` 路由表, 按任务深入对应主题文档(动代码前必读 `pitfalls.md` 与 `conventions.md`)。
3. 判断任务是否**已有 tasks/ 档案**: 有 → 读该档案续作并按"子任务状态表"推进; 无 → 按下方阈值决定是否立档。

## 立档阈值 (可判定: 满足任一条**必须**立档)

| # | 条件 |
|---|---|
| 1 | 任务跨越 ≥2 次会话 (上下文重置后仍需继续) |
| 2 | 单会话用户指令 ≥5 轮, 或改动 ≥3 个源文件 |
| 3 | 出现"计划 / 方案 / 波次 / 第 N 轮 / 后续阶段"等长周期表述 |
| 4 | 已产出或需要产出计划文档 / 交付报告 (`docs/*.html`, `DELIVERY/`) |

不立档(只记 `activeContext.md`): 单文件小修、错字、单轮问答、纯答疑。

> 阈值命中时**不得跳过**。2026-09-17 复盘: 3 天 25 条长纪要全堆在 `activeContext.md` 而 `tasks/` 只有 1 条 — 根因是"大任务"不可判定 + 立档成本高于"追加一行"的低成本出口。改成硬阈值后按表执行。

## 收尾 DoD (5 步, 缺一不可)

1. **activeContext**: 更新"最后更新"与"正在进行"; 已完成条目沉淀到 `progress.md` 或主题文档后**从本文件删除** — 它是易变层, 不是流水账。
2. **tasks/**: 命中阈值 → 建/更新 `memory-bank/tasks/TASKnnn-*.md`(追加进度日志 + 更新子任务状态表)并同步 `tasks/_index.md` 状态分区。
3. **事实回写**: 代码事实变更 → 回写对应 `memory-bank/` 主题文档与根 `README.md`; 测试基线数字**只改** `testing.md` 顶部(单点事实源, 其它文档一律引用不手抄)。
4. **闸门**: 跑 `uv run pytest tests -q`, 把实测数字记进 `testing.md` 与本次结论。
5. **新坑**: 遇到非显然的失败 / 陷阱 → 追加 `pitfalls.md` 条目(带日期与判别法)。

## 任务档案规范

- 路径 `memory-bank/tasks/TASKnnn-<slug>.md`(slug 英文小写连字符), 编号连续不复用。
- 必备章节: 标题行 `# TASKnnn - 名称`、状态行(`Status`/`Added`/`Updated`)、`## 原始请求`、`## 思考过程与决策`、`## 实现计划`、`## 子任务状态表`、`## 进度日志`。
- 状态取值仅四种: `In Progress` / `Pending` / `Completed` / `Abandoned`; `_index.md` 的分区必须用同样的词。
- 一个专题一个档案(不逐会话建文件): 新会话追加**结论与决策**; 历史流水账原文归档在该档案的 `## 历史会话纪要 (原文归档)` 段。
- 守卫: `tests/test_memory_bank.py` 校验索引↔文件双向一致、命名规范、状态分区、必备章节 — 登记了没文件 / 有文件没登记都会让 pytest 失败。

## 反模式 (本仓库已踩过, 勿重犯)

- ❌ 只在 `activeContext.md` 追加长纪要 → 文件膨胀成流水账, 跨会话定位不到"任务档案在哪"。
- ❌ 规则写成"跨会话的**大**任务要立档"这类不可判定措辞 → 无阈值 = 不执行。
- ❌ 把维护规则只放在 `applyTo: 'memory-bank/**'` 的 instruction 里 → 编辑 `src/` 时该规则不在上下文, **决策点(该不该立档)与生效点错位**。
- ❌ 基线数字手抄到 README/AGENTS/progress → 必然漂移; 只改 `testing.md`。
