# 26-11-13-test-route-cleanup — 修复 issue 26-11-13-0234: e2e route 回调收尾竞态兜底

**Status:** Done
**Added:** 2026-11-13
**Updated:** 2026-11-13
**Summary:** 修复 issue 26-11-13-0234: e2e/lib/route-cleanup.mjs 单点兜底(file 级 afterEach unrouteAll ignoreErrors) + 8 个同模式 spec 接线 + 静态接线守阵(test_flaky_timing_guards 扫描器 5 + 八形态活性探针 + lib 本体静态钉); 运行期差分守阵经实证不可构造(三形态归账实测入坑档), 差分锚 = 复验证据 + 静态守阵; 评审 6 轮 20 发现(2 major + 14 minor + 4 nit)全修零 actionable; e2e 回归全绿(见 kb.baseline)
**Topics:** test-route-cleanup

## 本篇只回答

「e2e 桩回调内 await 撞用例结束的收尾竞态假红该怎么修、怎么守」——修法单点(installRouteCleanup)、接线面(7 spec)、守阵形态(静态接线守阵, 运行期差分为何不可行)、验证数字全在本篇; 机制细节单点在坑档 route-callback-teardown-race.md。

## 原始请求

1. 用户: 「fix memory-bank/issues/26-11-13-0234-test-e2e-stubdisk-teardown-race.html」(认领并修复该 issue; 复验/修法按 issue §06 建议与 §07 复验纪律)。
2. 拍板轮(AskUserQuestion ×2): ①复用面「一并纳入 7 个 spec」+ 兜底「新建共享 lib 助手」+ 坑档「立档」; ②运行期差分守阵实证不可构造后「静态接线守阵 + 撤 e2e 守阵 describe」。

## 思考过程与决策

- **修法**: issue §06 建议 A(afterEach unrouteAll ignoreErrors), 落成 `e2e/lib/route-cleanup.mjs` 的 `installRouteCleanup(test)`(errors.mjs 同款传 test 惯例), file 顶层调一次; 建议 B(try/catch 吞错)不采纳。
- **复验增强**: 修前本机单跑 6 例即复现 2 红(2/6, 报错同位 :62), 且澄清机制 —— GET 分支 route.fetch 每次 GET 都执行(不只首拉), 任何末段 config GET 都在窗内。
- **运行期差分守阵不可构造(实证, 三次构造全败)**: 「结束后才发起」的 route 调用(sleep→fetch / fetch→sleep→fulfill / 同组存活窗归账)被 playwright 静默吞掉不归账; 可归账的只有「运行期内发起、结束后才完成」, 其窗 = 服务端往返毫秒级不可控 ⇒ 差分锚改道静态面。
- **静态接线守阵**: test_flaky_timing_guards.py 扫描器 5 —— 违例侧原文 `route\.fetch\s*\(`(注释提及也算), 接线侧剥注释判 `installRouteCleanup\s*\(` 调用形态(只注释调用行留 import 的 bypass 经评审轮 1 抓出并堵死, 红验实测)。
- **环境面(本机 clone2)**: `commands run dev.e2e` 自检在本机撞 e2e_selfcheck powershell 缺口(后由远端 56b0a82e 修复, 本轮按 clone1 先例 npm 直跑); test 闸门须 `TZ=Asia/Shanghai`(撞已入池 TZ 用例 26-11-12-2347) + `PATH` 补 `~/.local/node/bin`。

## 实现计划

1. 复验锚点(修前红) → 2. lib 兜底 + 7 spec 接线 → 3. 守阵(红绿双验: 摘接线红/装回绿/bypass 形态红) → 4. e2e 回归(锚点 repeat-each / 接线 spec / fast 全量) → 5. 台账 + 坑档 + issue 翻 Done → 6. 分批评审循环 → 7. test.full + 基线切片 + 立档。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 复验锚点: 修前单跑 2/6 红(4P/2F/57.2s, Test ended @:62) | Done(2026-11-13) |
| S2 | route-cleanup.mjs 兜底 + spec 接线(拍板: 一并纳入 + 共享 lib; 终态 8 个 = 复用面 7 个 + 评审轮守阵点名补 drawer-merge) | Done(2026-11-13) |
| S3 | 静态接线守阵: 扫描器 5 + 八形态活性探针 + lib 本体静态钉; 摘接线红/装回绿/注释调用行 bypass 红验 | Done(2026-11-13) |
| S4 | e2e 回归: 锚点 repeat-each=3 18/18 + 6 接线 spec 28/28 + fast 349P/1F(1F = dt-live-update 产量具预算负载假红候选, 静机单跑 14/14 复绿, 与本件无因果) | Done(2026-11-13) |
| S5 | 台账行 + 坑档 + issue 翻 Done(复验行/修复后补充) | Done(2026-11-13) |
| S6 | 评审 6 轮 20 发现(2 major 悬挂引用/注释调用行 bypass + 14 minor 含 lib 本体无钉/顶层锚缺口/#11 同险/第8接线传播 + 4 nit)全修全过检, 零 actionable 出口; 接缝终审豁免(单批, 无跨批接缝) | Done(2026-11-13) | Done(2026-11-13) |
| S7 | test.full 全绿(见 kb.baseline) + 基线切片 26-11-13-0513 + 本档案 | Done(2026-11-13) |

## 进度日志

### R0 · 立档 (2026-11-13)

认领 issue 26-11-13-0234 并完成 S1-S7 全链: 修复 + 守阵 + 回归 + 评审 + 收尾回写一次走完(单会话)。**Refs:** memory-bank/issues/26-11-13-0234-test-e2e-stubdisk-teardown-race.html · 基线切片 memory-bank/testing/baselines/26-11-13-0513-route-cleanup-teardown-fix.md。真机自检: 本轮零生产代码改动(纯 e2e 测试面 + pytest 守阵 + 文档), 真机轨不适用。计划外发现处置: dt-live-update 产量具预算负载假红经用户拍板入池 [26-11-13-0519](../issues/26-11-13-0519-test-e2e-dt-live-update-longtask-budget-flake.html)(Open, 待认领)。提交经用户显式指令「提交」走 ship.commit。
