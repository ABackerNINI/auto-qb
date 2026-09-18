# 26-09-17-memory-bank-trigger-fix — Memory Bank 触发机制修复 (skill 缺失 + 立档纪律失败)

**Status:** In Progress
**Added:** 2026-09-17
**Updated:** 2026-09-17
**专题:** 知识库治理 / 代理协作机制
**Legacy-ID:** TASK010
**Summary:** skill 载体 + always-on 阈值 + TASK001~TASK009 回填 + activeContext 瘦身 + 守卫测试完成; 待提交

## 原始请求

- 2026-09-17: "之前的对话没有正确触发 memory bank skill, 比如 `tasks/` 未正确记录, 分析原因并修复"。

## 思考过程与决策

### 根因 (证据已核实)

| # | 根因 | 证据 |
|---|------|------|
| 1 | **载体不存在** — 仓库没有 skill | `.github/skills/` 为空目录; 只有 `.github/instructions/memory-bank.instructions.md` (instruction ≠ skill, 发现机制不同) |
| 2 | **加载时机与决策时机错位** | `applyTo: 'memory-bank/**'` → 只有编辑 `memory-bank/` 时才注入; 而"该不该立档"的决策发生在编辑 `src/` 时, 那一刻规则不在上下文 |
| 3 | **规则不可判定** | `AGENTS.md` 只写"跨会话的**大**任务要立档" — 无阈值 ⇒ 模型无法判定 ⇒ 默认不立档 |
| 4 | **零机械后果** | 项目对代码约定有守卫测试, `memory-bank/` 无任何校验 (登记无文件 / 有文件无登记都不会被发现) |
| 5 | **低成本出口** | 往 `activeContext.md` 追加一行 ≪ 建文件 + 5 章节 + 状态表 + 登记索引 ⇒ 3 天堆 25 条长纪要, `tasks/` 仅 1 条 |

### 修复决策 (用户 2026-09-17 拍板)

- 立档粒度 = **专题粒度** (一个功能线/波次一个档案, 非逐会话)。
- `activeContext.md` = **迁入 tasks 后瘦身** (只留进行中 / 下一步 / 归档指针)。
- 机械保障 = **tasks 一致性守卫测试** (用户未选 hook 方案)。

## 实现计划

- [x] 新建 skill 载体 `.agents/skills/memory-bank/SKILL.md` (会话开始 3 步 / 收尾 DoD 5 步 / 立档阈值 4 条 / 档案规范 / 反模式; 先建于 `.github/skills/`, 后按仓库技能根惯例搬入 `.agents/skills/`)
- [x] always-on 入口加固: `AGENTS.md` 会话协议 + `.github/copilot-instructions.md` 硬约束 + `ai-lib.md` 指向 skill + `memory-bank.instructions.md` 顶部标注"本文件不负责触发"
- [x] 回填 `tasks/` 专题档案 `TASK001` ~ `TASK010` + 重写 `tasks/_index.md`
- [x] `activeContext.md` 瘦身 (会话纪要迁入各专题档案的"历史会话纪要 (原文归档)")
- [x] 新增守卫测试 `tests/test_memory_bank.py`
- [x] 跑全量 pytest 并回写 `testing.md` 基线
- [ ] 提交 (等用户指示)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 10.1 | skill 载体 | Complete | 2026-09-17 | `.agents/skills/memory-bank/SKILL.md` (由 `.github/skills/` 搬入) |
| 10.2 | always-on 入口与阈值 | Complete | 2026-09-17 | AGENTS.md / copilot-instructions.md / ai-lib.md |
| 10.3 | 历史专题档案回填 | Complete | 2026-09-17 | TASK001~TASK009 |
| 10.4 | activeContext 瘦身 | Complete | 2026-09-17 | 纪要原文按专题归档 |
| 10.5 | 守卫测试 | Complete | 2026-09-17 | `tests/test_memory_bank.py` |
| 10.6 | 闸门与基线回写 | Complete | 2026-09-17 | `uv run pytest tests -q` |
| 10.7 | 提交 | Complete | 2026-09-17 | 用户明确指示后提交入库 |

## 进度日志

### 2026-09-17

- 诊断 5 条根因 (见上表, 均有文件证据), 按用户拍板的三个范围决策实施修复。
- 交付: skill 载体 / always-on 阈值 (4 条) + 收尾 DoD (5 步) / 专题档案 TASK001~TASK010 (30 条历史纪要原文按专题归档) / `activeContext.md` 68 → 26 行 / 守卫 `tests/test_memory_bank.py` 6 项 (红绿验证: 幽灵任务与纪要回流两类违例均被精确拦截)。
- 闸门 `uv run pytest tests -q` = **995 passed** (989 + 6), 分支覆盖率 92%; 基线已单点回写 `testing.md`, 引用方 (AGENTS/README) 同步。
- skill 载体搬家 (`.github/skills/memory-bank/SKILL.md` → **`.agents/skills/memory-bank/SKILL.md`**, 仓库技能根惯例; `.github/skills/` 空目录已删): 同步更新全部引用 (AGENTS / copilot-instructions / ai-lib / memory-bank.instructions / activeContext / README / `_index.md` / progress / 守卫测试路径常量) 并复跑闸门。
- 关键认知沉淀: **decision point 必须与 rule exposure point 重合** — 规则写在只对某类文件生效的 instruction 里, 就等于在决策点隐身。已写入 `pitfalls.md`。
- 用户 2026-09-17 明确指示提交, 已入库。

## 历史会话纪要 (原文归档)

(本档案 2026-09-17 新建 — 修复过程即本档案的进度日志, 无更早的会话纪要原文。)
