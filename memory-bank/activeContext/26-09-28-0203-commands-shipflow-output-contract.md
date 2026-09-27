# commands-shipflow-output-contract — my-commit-flow 输出契约 v3

> 摘要: 用户判定 my-commit-flow 输出全属噪音(sync 失败态 10 行/commit 成功态 76 行), 推翻 v2 的「出示证据」方向。计划 26-09-28-0157 **已全量实施**(26-09-28): 成功一行、失败=原因+下一步、退出码 0/1; sync 自动 fetch+快进/rebase 保线性(D1); commit 编排合一(内部同步→闸门→逐路径暂存→提交→核 ref→内联推送); 镜像全程静默(D2); preflight 收编 _pipeline.py(D3); 引擎 FAILED 3→1(D4); warn_lines 保留一行(D5); 顺带修 issue 26-09-28-0128。任务树 4 入口: sync / ship.commit / ship.push / verify-ref。全量 1816 passed / 0 failed(基线 26-09-28-0321)。**待真机提交验收(等用户说「提交」)**。
> 最后活动: 2026-09-28 03:21

## 正在进行

- 等用户说「提交」→ 走一次真实 ship.commit 验收(成功一行 + 推送 + 镜像静默), 然后计划 doc-status 抬 Done。
- 遗留观察: 新测试用 tmp_path 后 test.pkg 需 TMPDIR 前缀(已修定义); doc-map 余压由 pitfalls/kb/cap-counting.md「两个出口」跟踪。

## 已完成

- v3 全量落地(任务档案 26-09-28-commands-shipflow-output-contract.md 进度日志 03:21 条有完整清单)。
- 诊断: 实贴 11 条症状逐条对到 file:line; 根因=v2 计划 L1「出示证据」成了默认输出。
- 计划文档: memory-bank/plans/26-09-28-0157-plan-commands-shipflow-v3.html(status In Progress)。
