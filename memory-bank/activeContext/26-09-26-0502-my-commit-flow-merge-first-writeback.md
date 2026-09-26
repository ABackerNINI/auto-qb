# 提交流程「先合并远端, 再收尾回写」定稿 — 已入库 2b19f42
> 摘要: 用户点名「baseline 总是撞」—— 根因是收尾回写(baseline/切片/索引)落在陈旧基线上。流程收口为 预检(sync) → 落后按「同步路径」合并远端 → 再收尾回写 → ship.commit → ship.push; commit 阶段落后 WARN→STOP 且闸门不跑, push 分叉提示改指替代路径。
> 触发: my-commit-flow, 提交流程, baseline 冲突, 落后主线, 收尾 DoD, 同步路径
> 最后活动: 2026-09-26 05:02

## 状态

- **已入库 `2b19f42`** —— 实施与文档全部落地, 无遗留。
- 已落地面: preflight.py(behind_rows + commit 阶段 STOP + 闸门跳过) / commit.py / push.py / pipeline.md / 包配置×2 / AGENTS.md / memory-bank SKILL.md / pitfalls/git/sync-pull.md。
- 单点: `.commands/my-commit-flow/references/pipeline.md`「先合并远端, 再收尾回写」节; 档案 `tasks/26-09-26-my-commit-flow-merge-first-writeback.md`。
