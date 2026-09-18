# 26-09-14-memory-bank-migration — 知识库 (Memory Bank) 建设与仓库治理

**Status:** Completed
**Added:** 2026-09-14
**Updated:** 2026-09-17
**专题:** 知识库 / 跨 agent 协作 / worktree 同步
**Legacy-ID:** TASK001
**Summary:** `ai/` → `memory-bank/` 六核心文件迁移 + 跨 agent 入口统一 + 测试基线单点化 + worktree 同步 (2026-09-14 ~ 09-15)

## 原始请求

- 2026-09-14: 安装 awesome-copilot 资产并改造知识库 — 让 AI 在**不重读全部源码**的前提下建立对项目的准确心智模型; 需要一个跨 agent (Copilot / Codex / Cursor / Gemini CLI / Claude Code) 通用的统一入口。
- 2026-09-15: 把原 `ai/` 目录全面迁移为 Memory Bank 结构 (六核心文件 + `tasks/`)。

## 思考过程与决策

- 入口统一到根 `AGENTS.md` (开放标准, 各 agent 自动读取), 各指针文件 (`CLAUDE.md` / `.github/copilot-instructions.md` / `.github/instructions/ai-lib.md`) 只做路由, 不复制内容。
- 测试基线数字**单点维护**于 `memory-bank/testing.md` 顶部, 其它文档一律引用 — 手抄必然漂移 (历史多次发生)。
- 目录语义重命名: `01→productContext`, `02→systemPatterns`, `09→progress`, `10→activeContext`, 新增 `projectbrief` / `techContext` / `tasks/`。
- 冲突裁决顺序: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。

## 实现计划

- [x] 安装 awesome-copilot 资产 (10 agents / 9 skills / 7 instructions)
- [x] 根 `AGENTS.md` + 各指针文件改造
- [x] 测试基线单点化到 `testing.md`
- [x] `ai/` → `memory-bank/` 迁移 (git mv 保留历史) 与重命名
- [x] `README.md` 补齐路由表 (`memory-bank/README.md`)
- [ ] (2026-09-17 发现) `tasks/` 维护纪律未落地 → 转 [TASK010](26-09-17-memory-bank-trigger-fix.md)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 1.1 | 安装 awesome-copilot 资产 | Complete | 2026-09-14 | 10 agents / 9 skills / 7 instructions |
| 1.2 | 根 `AGENTS.md` 统一入口 | Complete | 2026-09-14 | 黄金法则 / 红线 / 命令 / 路由表 |
| 1.3 | 测试基线单点化 | Complete | 2026-09-14 | `testing.md` 顶部为唯一事实源 |
| 1.4 | `ai/` → `memory-bank/` 迁移 | Complete | 2026-09-15 | 六核心文件 + 主题文档 |
| 1.5 | worktree 分支同步 (仓库治理) | Complete | 2026-09-15 | 7 个 worktree 全量对齐 develop; stash 保数据 |
| 1.6 | tasks/ 维护纪律落地 | Not Started | 2026-09-17 | 转 TASK010 |

## 进度日志

### 2026-09-17

- 复盘发现: 本档案是整个 `tasks/` 里唯一被登记的条目, 而 09-14~09-17 的其它大专题 (WEB UI 各波次 / 大文件拆分 / 依赖现代化 / tracker 分组 / 追剧视图) 全部只沉淀在 `activeContext.md` 的会话纪要里 — 根因与修复见 [TASK010](26-09-17-memory-bank-trigger-fix.md)。

### 2026-09-15

- `ai/` 整体迁入 `memory-bank/` (git mv 保留历史), 按六核心文件语义重命名; 新增 `projectbrief` / `techContext` / `tasks/`; 指令文件恢复原版 `applyTo: 'memory-bank/**'`; `src` 注释与 `想法.md` 文档引用同步更新。
- 7 个 worktree 分支全部 `merge --ff-only` 快进对齐, `auto-qb-other` 工作区未提交改动先 stash 保数据再恢复 (同位置双条目冲突按"两侧全保留"惯例手工合并)。

### 2026-09-14

- 安装 awesome-copilot 资产; 知识库改造第一轮 — 根级 `AGENTS.md` 统一跨 agent 入口、测试基线单点化、各篇加基线锚点。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: worktree 分支同步(全部快进) — 6 个 worktree 分支(agentAutoClaw/agentTrae/agentZCode/backend/frontend/other)均无自有提交, 全部 `merge --ff-only` 快进到 develop HEAD 937e013; 其中 4 个工作区干净直接快进, backend 仅有未跟踪 .openclaw-attachments/ 不受影响, other 有工作区独有未提交改动(memory-bank/activeContext.md 会话纪要 + 未跟踪 docs/plans/26-09-16-0123-webui-qb-replacement-plan.html)非任何分支 → 先 stash push -u 保数据再快进, pop 时 activeContext.md 同位置双条目冲突(develop 的 skip_local_verify 条目 vs 本地 qB 替代计划条目), 按"两侧条目全保留"惯例手动合并后 add + stash drop 完成; 现 6 分支全部指向 937e013 与 develop 对齐, develop 领先 origin/develop 9 提交未推送。
- 2026-09-15: worktree 分支同步 — 7 个 worktree 的 6 个分支中, frontend/autoclaw/trae/zcode/other 5 个已在 develop 历史, 仅 backend/develop 的 tracker 分组 8b78992 未合入; merge 046c01a 解决 3 处冲突: README(保留 develop 追剧三视图文案 + backend 15→16 条件数字)、testing.md(基线 942+4=946)、activeContext(两侧条目全保留); 全量 pytest **946 passed / 91%** 实测复核基线一致; 顺手回写 README 用例数 872→946 与 Web UI 详情节 双视图→三视图(追剧提交遗留漂移); auto-qb-other 工作区有未提交改动(memory-bank/activeContext.md 改动 + 未跟踪 docs/plans/26-09-16-0123-webui-qb-replacement-plan.html)不在任何分支, 无法经 merge 同步; develop 现领先 origin/develop 3 提交, 未推送。
- 2026-09-14: 安装 awesome-copilot 资产 (10 agents / 9 skills / 7 instructions); 知识库改造第一轮 — 根级 AGENTS.md 统一跨 agent 入口、测试基线单点化到 testing.md、各篇加基线锚点。
- 2026-09-15: 知识库全面迁移为 Memory Bank 结构 — `ai/` 整体迁入 `memory-bank/` (git mv 保留历史), 按六核心文件语义重命名, 新增 projectbrief / techContext / tasks/; 指令文件恢复原版 (applyTo: 'memory-bank/**'); AGENTS.md 与各指针文件改指 memory-bank/ 路径; src 注释与想法.md 中的文档引用同步更新。
