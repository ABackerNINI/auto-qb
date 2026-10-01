# 基线 · 2288 passed + 3 skipped / 99% —— W1 收官: web 鉴权加固双件(CSRF/Host 跨站闸 + 三小件)

> 摘要: issue 清偿路线图 W1 波 3/3 收官基线 —— A) skip_local_verify 开启时跨站防护(auth.require_token 单点: Host 白名单废 DNS rebinding + 写方法 Origin 同源废 CSRF, 默认关闭路径零变化, 提交 36dc8ba6); B) SSE 票据化(?ticket= 取代 ?token= 长期密钥进查询串)+ /api/config/public 限 loopback + uvicorn 显式 proxy_headers=False。双 issue(26-09-21-1408 bug-web-skip-local-verify-csrf / bug-web-auth-hardening-minors)翻 Done, 档案 tasks/26-10-02-web-auth-hardening.md。
> 档案: [tasks/26-10-02-web-auth-hardening.md](../../tasks/26-10-02-web-auth-hardening.md)。
> 基线时间: 2026-10-02 05:09, develop @ 36dc8ba6 + B 笔工作树(阈值 98 下 test.full 实测; 收尾回写未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2288 passed + 3 skipped / 99%**(13,259 语句 / 88 未覆盖 / 4,448 分支 / 85 partial,
test.full 28.39s, rc=0)。**精确综合口径**(coverage json 导出, 行 + 分支出口合计):
**17,532 / 17,707 = 99.01%**(语句 13,171/13,259 = 99.34%, 分支 4,361/4,448 = 98.04%)。
相对 P2 收官基线(26-10-02-0426: 17,541/17,708 = 99.06%)**−9 已覆盖单位 / 分母 −1** ——
本批新增产品代码(auth 跨站闸 + runtime 票据存储/消费 + events 换票端点 + config loopback 闸
约 +72 语句/24 分支)全部带测试覆盖, 分母微涨与部分既有未覆盖行收敛相抵后综合口径
99.06% → 99.01%(−0.05 个点, 远高于阈值 98)。守阵 +11(A 6 + B 5), 金清单路由 67→68
(POST /api/events/ticket)。已知 flaky `test_hr_service::test_budget_unit_wait_and_caps`
(issue 26-10-02-0306)本基线两采样(26.18s quick / 28.39s full)均未复现。
