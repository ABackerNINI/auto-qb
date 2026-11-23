# sync-unpushed-branch-error-line

> 摘要: 修复 my-commit-flow.sync 在远端无同名分支时误导性报『离线/联网后重跑』: remote_sha_probe 带出 ls-remote rc 分 absent/unreachable, 前者只报『远端该分支不存在(分支未推送, 非离线)』事实、不塞 push -u 指引(用户口径: 本地分支大多不需推送, 平时走 develop 同步), 离线仍原样; 新增守阵 test_remote_branch_absent_reports_unpushed + 坑档现行文案更新; 单批 62 行评审零发现, 闸门绿, 全量全绿见 kb.baseline 26-11-23-1815
> 最后活动: 2026-11-23 18:16

**R0(2026-11-23 18:16):** 修复 my-commit-flow.sync 在远端无同名分支时误导性报『离线/联网后重跑』: remote_sha_probe 带出 ls-remote rc 分 absent/unreachable, 前者只报『远端该分支不存在(分支未推送, 非离线)』事实、不塞 push -u 指引(用户口径: 本地分支大多不需推送, 平时走 develop 同步), 离线仍原样; 新增守阵 test_remote_branch_absent_reports_unpushed + 坑档现行文案更新; 单批 62 行评审零发现, 闸门绿, 全量全绿见 kb.baseline 26-11-23-1815
