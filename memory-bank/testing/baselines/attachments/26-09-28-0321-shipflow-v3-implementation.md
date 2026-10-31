# 基线 · 1816 passed + 3 skipped · 0 failed —— shipflow-v3 实施落地(my-commit-flow 推翻重构)

> 摘要: 计划 26-09-28-0157 全量实施(M1 脚本/配置/测试 + M2 文档回写 + M3 引擎退出码统一)。
> my-commit-flow v3: 成功一行 / 失败一行(原因+下一步) / 退出码统一 0/1; sync 自动 fetch+快进/rebase
> 保线性(D1); commit 编排合一(内部同步→闸门→暂存→提交→核 ref→内联推送); 镜像全程静默(D2);
> preflight 收编 _pipeline.py(D3); risky 回显移除(E1); 引擎 FAILED 3→1(E2); 顺带修 issue 26-09-28-0128
> (逐路径 add 撞已暂存删除)。包测试 57 + 引擎 9 全绿; 真机 sync 成功/失败双路径冒烟通过。
> 基线时间: 2026-09-28 03:21
> 档案: memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md

TOTAL 1816 passed + 3 skipped / 0 failed / 19.2s(并行 4 worker; test.full 口径 22.4s)
覆盖率 91%(12504 语句 / 914 未覆盖 / 4204 分支 / 388 partial)
对比前基线(26-09-28-0041): 1813 passed —— passed +3(包场景测试并入: test_sync 11 项 / test_commit 重写
/ test_pipeline 改编; tests/ 增 test_commands_engine 用例来自远端合并), failed 归零(前基线期的 docs
守阵红已由上游 gen_doc_map 渲染口径收口解决, issue 26-09-28-0219 标 Superseded)。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
