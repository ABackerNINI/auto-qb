# 26-11-06-test-flaky-governance — flaky 测试结构化治理: 时钟注入与抖动消除 (S1-S6 收口)

**Status:** Done
**Added:** 2026-11-06
**Updated:** 2026-11-06
**Summary:** 把时序/抖动类 flaky 从逐案打地鼠升级为结构化消除: 生产代码全量时钟注入(src 裸取时 161 点清零, 白名单仅 infra/clock.py 本体)、tests/ 统一假钟(4 套旧假钟迁 tests/clock.py 后删除)+裸 sleep 归零、e2e waitForTimeout/setTimeout 清零+shard=3 并行化(串行对照实测 3 倍差)、四类守阵+平台容差单点+pytest-randomly 周巡检+flaky 台账上线; 最终验收=全量+e2e fast 连续 5 次绿(无新增失败, gtm-alert 2 条既有日期炸弹按台账排除), 回写齐(覆盖表/坑档/计划 Done/基线切片含 e2e fast 门禁时长)
**Topics:** test-flaky-governance
**Refs:** memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html, memory-bank/pitfalls/testing/fakeclock-migration-missed-forms.md, memory-bank/testing/baselines/26-11-06-0302-flaky-governance-s6-baseline.md

## 原始请求

1. 用户在会话中 grilling 逐项拍板 D1–D13(后追加 D14): 治理主轴=结构性消除为主+轻量兜底, 不做 retry 遮羞布; 全量时钟注入(44 文件 161 点); 测试侧假钟统一单点; e2e waitForTimeout 全量替换; 不建隔离区(flaky 当场修, 修不了 skip+入池); 平台差异机制化(容差单点, 不做生产抽象层); tests-real 只做规范/坑档层; retry 政策(pytest reruns 恒 0, e2e retries=1 只作探测器+台账); 随机序周巡检/性能断言迁出/flaky 台账三项全纳入。
2. 分期骨架 S1 基建 → S2 生产时钟注入(按域 4 提交) → S3 tests/ 清理 → S4 e2e 清理 → S5 e2e 并行化(shard 隔离桩) → S6 收口; 验收口径(D11)= 守阵零违例 + 假钟统一 + 注入全覆盖 + 全量(含 e2e fast)连续 5 次绿 + 回写齐。
3. S6 第 2/2 步(本档案续作轮): 文档回写(覆盖表入档/坑档回写/计划翻 Done)+最终验收(10 轮)+基线切片补 e2e fast 门禁时长。

## 思考过程与决策

- **口径单点是计划文档** `memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html`(§01 验收五条 / §03 十类根因覆盖表 / §04 分期 / §06 D1–D14), 本档案只记执行与验证, 不复述方案。
- **拍板要点回放**: 时间控制权在测试(生产不裸取时/测试不真睡等); 断言区间不精确值; retry 不是修复; skip 必带理由+issue; 不新增生产配置键; 黄金法则不冲突(守阵只读扫描)。
- **e2e 并行化形态**: shard 多进程隔离桩(每 shard 独立 webServer), 不是 workers:N 多线程——单共享桩确定性口径刻意保留(shard 内 workers:1 不动); CPU 敏感量具 spec(perf/drawer-content-perf)排除出 shard、由 dev.e2e-perf-serial 串行补跑, 相加==全量。
- **shard 数拍板**: S4 清完睡等后按实测定, **shard=3**(fast 全套+perf-serial 实测约 263s+60s, 串行对照 690s), 为推荐口径。
- **验收口径细化**: 「连续 5 次绿」= **无新增失败**——gtm-alert 2 条是既有日期炸弹(2026-11-03 硬编码日期过 TTL, 台账在案、有意不修), 按台账排除并注明。
- **回写裁决**: 根因十类覆盖表独立成档 `testing/root-cause-taxonomy.md`(静态参照系, 与台账的动态登记分离); `.venv` trampoline 失效坑判**同族不同症**, 并入既有 `pitfalls/testing/sandbox-venv-in-workspace.md` 加条目而非另立 ops 新档。

## 实现计划

按计划文档 §04 分期执行, 每步独立可验、每步全量+基线切片:

1. **S1 基建**: infra/clock.py 单点(Clock protocol+SystemClock) / tests/clock.py 统一假钟 / wait_until helper / 四类守阵(裸 sleep·waitForTimeout·裸取时·bind 位固定口)。
2. **S2 生产时钟注入**: 44 文件 161 点按域 4 提交(core / hr / webui+traffic / 其余叶子), src 裸取时仅剩 clock.py 白名单。
3. **S3 tests/ 清理**: 裸 sleep 逐域清零(线程协作改 Event/wait_until, 时间语义改注入假钟) / 旧假钟 4 套(+1 计划外)迁删 / monkeypatch time 收敛 / 挂钟性能断言裁决。
4. **S4 e2e 清理**: waitForTimeout 全量替换(expect 系/expect.poll/toPass) / setTimeout 审计 / retry 探测口径 / flaky 台账上线。
5. **S5 e2e 并行化**: shard-run.mjs 包装(--shard=x/N, 每 shard 独立 webServer; E2E_SHARD_TOTAL 排除量具 spec) / 实测定 shard=3 / 门禁时长入基线。
6. **S6 收口**: 平台容差单点(tests/platform_tolerance.py)+pytest-randomly 周巡检(test.random-order) → 文档回写(覆盖表/坑档/计划 Done)+最终验收(10 轮)+基线切片(含 e2e fast 门禁时长)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 基建: clock 单点+统一假钟+wait_until+四类守阵 | Done(2026-11-05) |
| S2 | 生产时钟注入 161 点按域 4 提交收口 | Done(2026-11-05) |
| S3 | tests/ 清理: 裸 sleep 归零+旧假钟迁删+monkeypatch 收敛 | Done(2026-11-05) |
| S4 | e2e 清理: waitForTimeout/setTimeout 清零+台账上线 | Done(2026-11-05) |
| S5 | e2e 并行化: shard 隔离桩+shard=3 拍板 | Done(2026-11-06) |
| S6a | 平台容差单点+周巡检 job | Done(2026-11-06) |
| S6b | 文档回写(覆盖表/坑档/计划 Done)+验收 10 轮+基线切片 | Done(2026-11-06) |

## 进度日志

### R0 · 立档 (2026-11-06)

S1–S5 与 S6a 在前序会话完成(11 个提交, 每步全量+基线切片, 见 `commands run kb.baseline`); 本轮(第 2/2 步)完成 S6b 收口: 根因十类覆盖表入档 `testing/root-cause-taxonomy.md`(含 tests-real 真时序轨职责边界)、坑档两件(假钟批量迁移形态坑新立 / `.venv` trampoline 失效并入 sandbox-venv-in-workspace 同族不同症)、计划文档翻 Done、最终验收 10 轮(全量×5+e2e fast×5, 无新增失败, gtm-alert 2 条按台账排除)、基线切片补 e2e fast 门禁时长(见 kb.baseline)。

- 2026-11-06 01:18 S6 收口第 2/2 步: 覆盖表入档 root-cause-taxonomy.md(含 tests-real 职责边界)+坑档两件(假钟迁移形态新立/venv trampoline 并入 sandbox-venv-in-workspace 同族不同症)+计划翻 Done+验收 10 轮全绿+基线切片补 e2e fast 门禁时长
- 2026-11-06 03:02 续作轮收口: 验收 10 轮实跑完毕(test.full ×5 与 e2e fast ×5 全绿, gtm-alert 2 条既有日期炸弹按台账排除, 零新增失败), 基线切片落盘 `memory-bank/testing/baselines/26-11-06-0302-flaky-governance-s6-baseline.md`(逐轮数字见 kb.baseline, 本档案不手抄), 档案状态翻 Done
