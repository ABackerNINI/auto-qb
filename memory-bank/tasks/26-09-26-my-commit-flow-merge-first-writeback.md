# 26-09-26-my-commit-flow-merge-first-writeback — 提交流程「先合并远端, 再收尾回写」定稿

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26
**Summary:** 多 clone 下收尾回写落在陈旧基线上 → 合并时 baseline/切片必撞("baseline 总是撞")。提交流程收口为: 预检(my-commit-flow.sync) → 落后按「同步路径」合并远端 → 再收尾回写 → ship.commit → ship.push; commit 阶段落后由 WARN 收紧为 STOP 且闸门不跑, push 分叉提示改指替代路径。
**Topics:** my-commit-flow-merge-first-writeback

## 原始请求

用户 2026-09-26:「baseline 总是撞，将提交流程改为先预检，远端有更新的话合并远端，然后写回文档，可能涉及到 AGENTS.md 与 my-commit-flow」。

## 思考过程与决策

- **根因链**: 回写件 (testing/baseline.md / activeContext 切片 / 各 _index) 是全体 clone 收尾 DoD 都要写的最热写点; 旧流程让收尾回写先于任何提交期同步发生, 会话期间远端一推进, 回写就落在陈旧基线上 → 提交后 push 被拒 → 已分叉 → `apply --3way` 在 baseline/切片上报冲突。
- **旧口径自相矛盾**: commit.py docstring 教「落后+树脏时先提交再快进」(该顺序必然分叉), pipeline.md 又说「先同步后提交」; `--phase commit` 对落后只 WARN 放行, 等于把分叉陷阱留到 push 阶段才暴露。
- **决策**: 顺序收口为「预检 → 合并远端 → 收尾回写 → 提交 → 推送」, 并把 commit 阶段落后从 WARN 收紧为 STOP(机检强制, 不靠注意力); 合并**不自动化** —— 本环境历史整合风险高, 沿「不替执行者做历史整合」哲学, 由预检打印可执行「同步路径」配方(树干净直接快进 / 树脏移出→快进→施回 / 重叠或分叉停下报告), 执行者照跑。
- **闸门随之不跑**: 落后未合流时预检跳过 auto 闸门 —— 合并后反正要重跑提交预检, 先跑全量测试纯属白跑。
- **范围守恒**: collaboration.md 与三个常驻规则载体未教冲突顺序, 不动; 改动面 = 包脚本×3 + 包配置×2 + pipeline.md + AGENTS.md + SKILL.md + pitfalls/git/sync-pull.md。

## 实现计划

1. preflight.py: 新增纯函数 `behind_rows`(commit/push 两阶段 STOP + 复用 sync_recipe 打印「同步路径」+ 与远端改动重叠检测); `--phase commit` 落后 STOP(废除 WARN); 落后时跳过 auto 闸门; sync_recipe 分叉文案去掉「提交后」时序假设。
2. commit.py docstring 过时口径修正; push.py 落后提示区分「纯落后(ff-only)」与「已分叉(替代路径)」。
3. pipeline.md 三节改写(流程图加 S0 / 「先合并远端再收尾回写」定稿节 / 闸门触发点); 包 config 的 sync 任务 when 扩到「提交后第一步」; ship.commit when 注明 STOP。
4. AGENTS.md 提交/PR 节 + 收尾 bullet; SKILL.md 收尾 DoD 前言; pitfalls/git/sync-pull.md 新坑条目。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| preflight.py 行为收紧 + behind_rows | Completed | commit 阶段落后 STOP + 同步路径配方 + 闸门跳过 |
| commit.py / push.py 口径修正 | Completed | 过时「先提交再快进」删除; 分叉提示改指替代路径 |
| pipeline.md / 包配置 | Completed | S0 预检 + 定稿节; sync 任务 when 扩到提交期 |
| AGENTS.md / SKILL.md / pitfalls | Completed | doc.caps 全 PASS(AGENTS.md 7887/8000); 守卫 token 未动 |
| 回归 | Completed | test_preflight.py 52 项全过(+5); test.full 1640+1 skipped 持平 |

## 进度日志

- **2026-09-26 05:02**: 开工 sync 自检齐平(2712804f); 按上表实施完毕。实测: 包内自测 52 项全过(新增 5 项 behind_rows 回归, 钉住 commit 阶段 STOP 行为); test.full **1641 collected: 1640 passed + 1 skipped / 92%**(11013 语句 / 787 未覆盖 / 3656 分支 / 330 partial, 18.2s, 与基线持平); doc.caps 全 PASS。改动**未提交** —— 待用户显式说「提交」后按新流程走 ship.commit / ship.push。
