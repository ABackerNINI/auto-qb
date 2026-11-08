# gtm-auth-body-drain

> 摘要: 认领并修复 issue 26-11-03-1144: gtm 401 短路出口前置 _drain_body 按 Content-Length 读空请求体(修关链 RST 致 Win 客户端先收 WinError 10053 的间歇失败); 新增确定性 drain 断言回归 test_auth_401_drains_request_body_before_responding(修前必红); issue 置 Done; 全量与 gtm 定向数字见 kb.baseline(切片 26-11-04-0212)
> 最后活动: 2026-11-04 02:13
**Refs:**

**R0(2026-11-04 02:13):** 认领并修复 issue 26-11-03-1144: gtm 401 短路出口前置 _drain_body 按 Content-Length 读空请求体(修关链 RST 致 Win 客户端先收 WinError 10053 的间歇失败); 新增确定性 drain 断言回归 test_auth_401_drains_request_body_before_responding(修前必红); issue 置 Done; 全量与 gtm 定向数字见 kb.baseline(切片 26-11-04-0212)
