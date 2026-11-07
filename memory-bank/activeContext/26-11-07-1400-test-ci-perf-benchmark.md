# test-ci-perf-benchmark

> 摘要: 修复 GitHub CI 两处红/告警: 5000 种子性能基准挂钟假红改两档阈值(开发机严格/CI 宽松, 只认 GITHUB_ACTIONS) + 2 条选档守阵; runpy RuntimeWarning 摘 sys.modules 根因 + recwarn 守阵; 分批评审 5 发现全修(1 blocker/1 major/3 minor, 引文 5/5); 坑档 timing-tolerance 复发+1 与新坑 ci-env-var-profile; 红绿双验三条; 待 test.full 与基线切片
> 最后活动: 2026-11-07 14:00

**R0(2026-11-07 14:00):** 修复 GitHub CI 两处红/告警: 5000 种子性能基准挂钟假红改两档阈值(开发机严格/CI 宽松, 只认 GITHUB_ACTIONS) + 2 条选档守阵; runpy RuntimeWarning 摘 sys.modules 根因 + recwarn 守阵; 分批评审 5 发现全修(1 blocker/1 major/3 minor, 引文 5/5); 坑档 timing-tolerance 复发+1 与新坑 ci-env-var-profile; 红绿双验三条; 待 test.full 与基线切片
