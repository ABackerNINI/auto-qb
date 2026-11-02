# testing-tmpdir-bootstrap

> 摘要: TMPDIR 自举+互斥锁五步实施完毕, 逐条判据实测通过; coverage 改走 retarget_cov_data_file 修正面(pytest-cov 早于 conftest 绑定 .coverage, env 无效); 计划 26-11-02-0657 转 Done
> 最后活动: 2026-11-02 09:44
**Refs:**

**R0(2026-11-02 07:45):** TMPDIR 自举+互斥锁五步实施完毕, 逐条判据实测通过; coverage 改走 retarget_cov_data_file 修正面(pytest-cov 早于 conftest 绑定 .coverage, env 无效); 计划 26-11-02-0657 转 Done

**R1(2026-11-02 07:45):** TMPDIR 自举+互斥锁五步实施完毕, 逐条判据实测通过; coverage 改走 retarget_cov_data_file 修正面(pytest-cov 早于 conftest 绑定 .coverage, env 无效); 计划 26-11-02-0657 转 Done

**R2(2026-11-02 08:00):** 拍板轮收尾: 计划09节/边界②明示本轮未跑test.full(留提交轮不标已验证); AGENTS.md的TMPDIR旧句回写新机制(自举R→H→C:\Users\11059\AppData\Local\Temp/外部拒收rc=4/换根改TMP_ROOT_CANDIDATES); 计划补变更记录段+kb.bump(R1); .tmp_s3_t1.py核实已被git追踪(e2fa1625)按用户条件停手未删

**R3(2026-11-02 08:39):** 提交轮: 全量 test.full 实测跑绿(首跑一红=新建 test_tmp_bootstrap.py 缺「测试计划」清单, 补 7 条后复跑); 新建基线切片 26-11-02-0838; 计划边界②/09节改记为提交轮已验证(kb.bump R2); git rm .tmp_s3_t1.py; kb.index 23 生成物

**R4(2026-11-02 09:44):** 端口分层补做提交轮: 全量 test.full 全绿(增量为端口守卫新用例, 数字见 kb.baseline 切片 26-11-02-0943); 走 ship.commit 入库
