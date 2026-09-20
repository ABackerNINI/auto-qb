# 仓库级指令 (Copilot)

统一入口为根目录 [AGENTS.md](../AGENTS.md) — 所有代理通用, 先读它, 并按其"会话协议"工作。
会话生命周期(开始 / 收尾 / 任务立档)的完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md) — **会话开始与收尾时必须加载**。

## 硬约束 (always-on, 细则见 skill)

- **开始**: **①先拉取远程分支** —— `git remote -v` 确认主线远端 (Gitee), 再 `git pull --rebase <remote> develop` (分支名**必须写**), 确认不落后后再改代码; **禁止在落后的分支上动手** (细则见 [AGENTS.md](../AGENTS.md)「会话协议 · 开始」与「提交 / PR」)。再 ②读 `memory-bank/activeContext.md` (当前焦点); **按任务读哪份文档看 [AGENTS.md](../AGENTS.md)「知识库路由」表(单点)**; 已有 `tasks/` 档案的任务从其档案续作。
- **收尾 (5 步 DoD)**: ①更新 activeContext (已完成条目**迁出**到 progress.md / 主题文档, 不是追加流水账) ②命中阈值的任务在 `memory-bank/tasks/` 立档 (命名 `YY-MM-DD-<slug>.md`, **先按 slug 查重再建**) + 跑 `python scripts/gen_tasks_index.py` 重建索引 (不要手改 `_index.md`) ③代码事实变更回写 `memory-bank/` 对应文档与根 `README.md`, 测试基线只改 `testing.md` ④跑 `uv run pytest tests -q` 并把实测数字记进 `testing.md` ⑤新坑追加 `pitfalls.md`。
- **立档阈值** (满足任一条**必须**立档): ①跨 ≥2 次会话 ②单会话 ≥5 轮指令或改动 ≥3 个源文件 ③出现"计划/方案/波次/第 N 轮/后续阶段"等长周期表述 ④需产出计划文档或交付报告。其余小修与答疑只记 activeContext。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。
