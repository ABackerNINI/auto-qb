# 仓库级指令 (Copilot)

统一入口为根目录 [AGENTS.md](../AGENTS.md) — 所有代理通用, 先读它, 并按其"会话协议"工作:

- 会话开始: 读 `memory-bank/activeContext.md` (当前焦点) 与 `memory-bank/README.md` 路由表, 按任务深入对应文档。
- 会话收尾: 更新 `memory-bank/activeContext.md`; 代码事实变更时回写 `memory-bank/` 对应文档。
