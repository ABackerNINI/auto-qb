---
description: 会话开始时的知识库入口
---

统一入口是仓库根的 `AGENTS.md` (跨 agent 开放标准, Copilot 自动读取)。按其"会话协议"执行: 先读 `memory-bank/activeContext.md` (当前焦点) 与 `memory-bank/README.md` 路由表, 按任务深入对应文档; 会话收尾更新 `memory-bank/activeContext.md`。
