---
description: 会话开始与收尾时的知识库入口 (Memory Bank)
---

统一入口是仓库根的 `AGENTS.md` (跨 agent 开放标准, Copilot 自动读取)。完整会话协议(开始 / 收尾 DoD / 立档阈值)见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md), **会话开始与收尾时加载它**:

- **开始**: **①先同步** (**硬性, 无豁免 —— 问答/只读分析轮次同样先同步**) —— `commands run my-commit-flow.sync` (自动 fetch + 快进 / 分叉自动 rebase; 成功行「已同步 <hash>」贴进回复, 失败行自带原因与下一步, 照做后重跑)。**禁止在落后的分支上工作 (含只读分析)**; 判据与细则的单点在 `AGENTS.md`「会话协议 · 开始」与「⚠️ 环境硬约束: Git 操作」。再 ②跑 `commands run kb.active` 看 `memory-bank/activeContext/` 切片(会话滚动状态) 与 `memory-bank/README.md` 路由表, 按任务深入对应文档; 已有 `memory-bank/tasks/` 档案的任务从档案续作。
- **收尾**: 按 skill 的 5 步 DoD 执行 (更新 activeContext 切片 + 已完成条目迁出 / 命中阈值立档 / 回写事实与 README / 跑闸门 pytest / 记新坑); 守卫 `tests/test_memory_bank.py` 校验档案一致性。
