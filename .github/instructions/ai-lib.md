---
description: 会话开始与收尾时的知识库入口 (Memory Bank)
---

统一入口是仓库根的 `AGENTS.md` (跨 agent 开放标准, Copilot 自动读取)。完整会话协议(开始 / 收尾 DoD / 立档阈值)见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md), **会话开始与收尾时加载它**:

- **开始**: **①先同步** (问答/只读轮次跳过; **首个执行动作 —— 改文件 / 跑测试 / 任何 git 写操作 —— 之前必须完成**) —— `git fetch gitee develop` (远端与分支名**必须写**), `git ls-remote gitee develop` 对比本地 HEAD 确认不落后 (`status -sb` 是快照); 纯落后且工作区干净 → `git merge --ff-only FETCH_HEAD`; 树脏 → **停下报告, 禁止自行清理**; **禁止在落后分支上动手** (细则见 `AGENTS.md`「会话协议 · 开始」与「⚠️ 环境硬约束: Git 操作」)。再 ②读 `memory-bank/activeContext.md` (当前焦点) 与 `memory-bank/README.md` 路由表, 按任务深入对应文档; 已有 `memory-bank/tasks/` 档案的任务从档案续作。
- **收尾**: 按 skill 的 5 步 DoD 执行 (activeContext 迁出已完成条目 / 命中阈值立档 / 回写事实与 README / 跑闸门 pytest / 记新坑); 守卫 `tests/test_memory_bank.py` 校验档案一致性。
