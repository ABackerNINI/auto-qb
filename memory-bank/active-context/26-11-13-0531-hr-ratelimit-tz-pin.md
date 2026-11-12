# hr-ratelimit-tz-pin

> 摘要: 修复 issue 26-11-12-2347: test_hr_ratelimit TZ 敏感用例根治(模块内 autouse 夹具 POSIX 钉 TZ=Asia/Shanghai+tzset, Windows 早退维持宿主; +守阵钉固定 UTC+8/翻日 86400s), LA 宿主裸跑红转绿 18 passed, 全量 6076+19 覆盖 99%(基线切片 26-11-13-0526, env3 首次无 TZ 前置全绿); issue 翻 Done; 坑档 env3-test-run-prereqs TZ 前置口径回写已根治; 评审 2 轮 2 nit 全修零 actionable
> 最后活动: 2026-11-13 05:31

**R0(2026-11-13 05:31):** 修复 issue 26-11-12-2347: test_hr_ratelimit TZ 敏感用例根治(模块内 autouse 夹具 POSIX 钉 TZ=Asia/Shanghai+tzset, Windows 早退维持宿主; +守阵钉固定 UTC+8/翻日 86400s), LA 宿主裸跑红转绿 18 passed, 全量 6076+19 覆盖 99%(基线切片 26-11-13-0526, env3 首次无 TZ 前置全绿); issue 翻 Done; 坑档 env3-test-run-prereqs TZ 前置口径回写已根治; 评审 2 轮 2 nit 全修零 actionable
