# flaky 台账

> 摘要: flaky / 恒红测试候选的**登记单点** —— 用例名 / 根因类目 / 状态 / 处置 / 日期; 每轮冒头先对表归因再修, retry 不是修复。
> 触发: flaky, 台账, 恒红, 日期炸弹, 端口碰撞, timing flake, 登记候选, 归因, 巡检, skip 清单, retries, 探测器

> 口径单点: 计划 [26-11-05-0118](../plans/26-11-05-0118-plan-flaky-test-governance.html) §03(根因类目十类)§06 D5/D9。
> **retry 不是修复**: pytest 主套件 reruns 恒 0; e2e CI `retries:1` 只是**探测器**(Playwright 报 flaky
> 的用例当场记进本台账并当场修)。修不了的走 skip(reason + issue 入池), 不养隔离区。
> **登记纪律**: 新增一行 = 用例名 + 根因类目(对 §03 十类; 冒出无主类目先补类目再登记) + 状态 + 处置 + 日期;
> 修完当场翻状态留一行去向( issue 链接/基线切片)。本台账只管**登记与状态**, 不承载修法细节(归计划/档案)。
**Refs:** memory-bank/issues/26-11-11-0633-bug-webui-flags-boot-resilience.html

## 台账

| 用例 | 根因类目 | 状态 | 处置 | 登记日期 |
|---|---|---|---|---|
| `e2e/gtm-alert.spec.mjs` gtm 弹窗双皮肤组 —— 硬编码日期 2026-11-03, 桩 TTL 24h 已过, **恒红**(非概率 flaky) | time(边界/粒度) | Done | [26-11-06-0330](../issues/26-11-06-0330-test-e2e-gtm-alert-date-bomb.html): T1-T4 改相对当前时刻生成 + 补「超 TTL 判空」负向断言(2026-11-06 修, e2e fast 双皮肤绿) | 2026-11-05 |
| `e2e/views.spec.mjs` 「种子页筛选器有数据」双皮肤**恒红** —— relocate kind 恒空(桩数据缺该类目), 不进 fast | 共享状态(桩数据缺口) | Open | 已入池 [26-11-06-0330](../issues/26-11-06-0330-test-e2e-views-relocate-kind-empty.html) | 2026-11-05 |
| `tests/test_hr_discovery.py` 生命周期层真绑定用例 —— `-n 8` 全量并行下偶发端口碰撞 | 端口/资源 | Done | 已修(2026-11-06): 断言改「落在候选表」+ 占位收敛 `hold_run`(三条同形一起), 去向 [26-11-06-0330](../issues/26-11-06-0330-test-hr-discovery-port-collision.html) | 2026-11-05 |
| `tests/test_hr_discovery.py::test_start_all_busy_returns_false_and_retries` —— ~~疑似 timing flake~~ 经随机序巡检证据修正为端口/资源(10013 排除段拒绝) | 端口/资源 | Done | 已修(2026-11-06): 端口单点 `tests/_test_ports.py::hold_run` 整段自验替代「只验基址」, 守阵 +2; 去向 [26-11-06-0330](../issues/26-11-06-0330-test-hr-discovery-busy-retry-flake.html) | 2026-11-05 |
| `tests/test_webui_static_r4_static_batteries.py::test_r4_shortcuts_engine_table_and_keydown` 及同源 node 电池 —— `-n 8` 下共享临时 bundle 被并发截断, 偶发假红(单跑恒绿) | 并发/竞态 | Done | 已修(2026-11-09): 三处落点掺 `os.getpid()` + 两例守阵; 去向 [26-11-08-1955](../issues/26-11-08-1955-test-xdist-js-bundle-temp-race.html) | 2026-11-09 |
| `e2e/gtm-alert.spec.mjs:83` / `e2e/kbd-scroll-band.spec.mjs:102` 双皮肤 —— GitHub Linux runner 上稳定红、本地隔离与整片 `shard 2/3`(102 例)全绿; 非顺序污染, 是等待窗口不足 / 窗口化重渲晚于 `$nextTick` 的时序差异 | time(边界/粒度) · 并发/竞态 | Done | 已修(2026-11-10): `seenTs` 显式 20s + `_kbScrollRowIntoView` 跨帧按真实 DOM 补正落点; 去向 [26-11-07-0326](../issues/26-11-07-0326-test-ci-smoke-existing-red-backlog.html) / [任务档案](../tasks/26-11-10-test-github-ci-e2e-red-fix.md) | 2026-11-10 |
| `e2e/perf.spec.mjs:361` W5 —— 不定长交互窗按固定 4.4s 数拍子, CI 实测 4 拍即越界 | time(边界/粒度) | Done | 已修(2026-11-10): 上界按 `ceil(elapsed / vm.basePollMs()) + 1` 归一, 不按 CI 分档放宽; 去向 [基线切片](baselines/26-11-10-0121-test-github-ci-e2e-red-fix.md) | 2026-11-10 |
| `e2e/drawer-general-variants.spec.mjs:175/228` 双皮肤 —— 产品入口下线 / wide 条件式后, e2e 断言与桩数据未同步(本地可稳定复现, 非 flaky) | 共享状态(桩数据缺口) | Done | 已修(2026-11-10): 三处磁力钮断言改「不得回潮」+ `BASE_PATCH` 补三个非空路径值; 去向 [任务档案](../tasks/26-11-10-test-github-ci-e2e-red-fix.md) | 2026-11-10 |
| `tests/test_legacy_review4_scripts.py::test_qb_capture_dry_true_zero_requests`(同族假服: helpers FakeQB / test_tool_client)—— `-n 8` 并行下对自起假服的请求偶发 ConnectionError(被中止); 根因 = 裸 ThreadingHTTPServer 带 SO_REUSEADDR, Windows 并行双绑串线 | 端口/资源 | Done | 已修(2026-11-11): 假服收敛独占 bind 单点 `tests/_test_ports.py::http_server`(对齐生产 `_EndpointServer` 口径)+ 散落守卫禁裸实例化 + 守阵 2 条; 去向 [26-11-11-0114](../issues/26-11-11-0114-test-qb-conn-flake-parallel.html) | 2026-11-11 |
| `e2e/traffic-gap-zones.spec.mjs:203` [atlas] —— 全量 dev.e2e 并发下偶红(461 passed / 3 failed 那轮), 单跑即绿; @fast 门禁(318 全绿)含它且通过 —— ~~负载型, 未稳定复现, 根因类目待采样归因(先按并发/竞态候选登记)~~ 经取证复现改判: **async-wait/时序**(flags 单发 fail-closed × 键盘入口无等待), 已量化复现并修复 | async-wait/时序(flags 单发 fail-closed × 键盘入口无等待) | Done | 已修(2026-11-11): 按键前补 `expect.poll(vm.qbTrafficOn)` 显式等 flags 落袋(15s, 双皮肤共用一处); 修后单跑 4/4 + `--repeat-each 10` 40/40 + `--repeat-each 20` 80/80 全绿; 取证/修法去向 [26-11-11-0134](../issues/26-11-11-0134-test-e2e-traffic-gap-zones-load-flake.html); **既有红先例** [26-11-07-0536](../issues/26-11-07-0536-bug-legacy-review4-static.html) 终验(2026-11-08, 早于 flux 分支)同位红 + 定向重跑 4/4 绿; 与 flux 改动无关(完整论证见 issue 件) | 2026-11-11 |
| `tests/test_legacy_review4_scripts.py::test_qb_capture_dry_true_zero_requests` + `tests/test_traffic_sample_store.py::test_read_side_view_contract_table[1m]` —— `-n 8` 全量偶发各闪一次(五轮全量三轮各闪一个), 单跑均绿; 修后归因: 前者 = 进程内假服已建连被中止(10053 族, 坑档第 4 次复现 → 受控重试兑现), 后者 = 进程级 open 探针被同 worker 遗留线程跨 tmp_path 污染(探针按 data_dir 收窄) | 端口/资源(10053) · 并发/竞态(探针污染) | Done | 已修(2026-11-12): 对照组受控重试(每轮新假服+独立台账)+守阵; `_v4_open_paths` 按 data_dir 前缀收窄+守阵; 两面断言语义零放松; 去向 [26-11-12-0318](../issues/26-11-12-0318-test-testing-parallel-flaky.html) | 2026-11-12 |
| `e2e/traffic-source-switch.spec.mjs` :94/:169 双条(atlas 读路径 / prism 规则卡, 共用同文件 stubDisk 桩) —— env3 全量轮 2/344 偶红; 修前 clone2 单跑 6 例即复现 2 红; 断言本体全绿, 纯收尾竞态假红(桩回调内 await route.fetch 飞行中撞用例结束 → "Test ended" 归账记红; GET 分支每次都 fetch, 任何末段 config GET 都在窗内) | 并发/竞态(page 关闭 × route 回调收尾竞速) | Done | 已修(2026-11-13): `e2e/lib/route-cleanup.mjs` 单点兜底(file 级 afterEach unrouteAll ignoreErrors), 8 个同模式 spec 全接线(一并纳入; 评审轮守阵点名补 drawer-merge); 静态接线守阵(test_flaky_timing_guards 扫描器 5)钉 wiring; 运行期差分守阵经实证不可构造(三形态归账实测见坑档), 差分=复验证据(修前 2/6 红 ↔ 修后全绿); 坑档 route-callback-teardown-race.md; 去向 [26-11-13-0234](../issues/26-11-13-0234-test-e2e-stubdisk-teardown-race.html) | 2026-11-13 |
| `e2e/dt-live-update.spec.mjs` #10/#11 双皮肤 —— 44.8m 全量负载轮偶红(349P/1F 那轮唯一 1F), 静机单跑 14/14 复绿, prism 孪生同轮 0/0 过; W4 收紧(2026-11-02)的 longtask `count==0` 预算在负载态被 1 个 63ms GC/调度毛刺混进 500/800ms 测量窗打穿 —— 计数不随时长线性, 归一化不适用, 负载型产量具假红 | time(边界/粒度)(JS 侧窗口内事件计数零容差, timing-tolerance ③ 同族④) | Done | 已修(2026-11-13): 量具口径改「无回归量级长任务」`Math.max(0, ...lt) < 100`(单点 `LT_REGRESSION_MS`, 锚: 噪声实测上限 63ms / 回归面 W1 长任务预算 <150ms / 长任务定义界 2 倍; 同形先例 perf.spec W5 灾难冻结帧 <500ms); 行侧零重建主守阵是 mut 预算(DOM 记录数与负载无关)不放松; 红验: 注入 130ms 双皮红 + 注入 63ms 复刻假红条件双皮绿; 去向 [26-11-13-0519](../issues/26-11-13-0519-test-e2e-dt-live-update-longtask-budget-flake.html) | 2026-11-13 |
| `e2e/drawer-dock-stability.spec.mjs` T7 顶界带 / S-A 首开遮挡(flux 两条) —— ~~整 spec 顺序 flake~~ 经复验改判: 行窗口化 `_rowHs` 陈旧行高 × 窗口滑动 pad 超量替换(padTop Δ69.609 vs 实际行高 65.781, 单次 +3.83px), 漂移骑在像素判据带边缘(T7 前置带 (0,4] / S-A 公式 ±2 窗), 环境敏感 —— 立档日过滤单跑恰绿, 11-15 起零前置单跑也确定性红; bisect 抽查 5 点含 good 锚点全红, 无回归提交 | platform(环境敏感几何判据 × 窗口化陈旧行高) | Done | 已修(2026-11-15): 像素级对齐/让位前加 `preheatRowWindow` 预热滚动(下 900 滚回, 途经区间存值回程重量刷新鲜, 测试侧 +27 行零产品改动, 判据零放松); 修后整 spec 两轮全绿(38P/4S ×2) + 两用例 repeat-each 5 全绿; **2026-11-16 产品侧修复落地, 测试侧预热退役**: `_reprobeRenderedRowH` 出窗最后一探(顶掉 `_rowHs` 陈旧存值) + 占位估算基准冻结(消掉「每量一行均值微动 δ, pad 区上百行连坐搬 δ×N」的第二根因), `preheatRowWindow` 删除, T7/S-A/S-C 去预热后仍全绿(撤修复即红: T7 前置带 5.8>4 / S-A 公式落点 -11>-14); 去向 [26-11-14-1323](../issues/26-11-14-1323-bug-drawer-dock-flux-fullspec-flake.html) → 产品面 [26-11-15-0332](../issues/26-11-15-0332-bug-webui-rowwin-stale-rowh-scroll-jump.html) | 2026-11-15 |
| `e2e/settings-bt-backup.spec.mjs` 「探测 ambiguous」双皮肤 x2(2026-11-12 容器全量轮 4 败之一, 与 traffic-source-switch :94/:169 同轮) —— 当轮初判「计时探测类」待采样, 经 issue 26-11-13-0234 修后复验改判: 与 traffic-source-switch 同为收尾竞态假红(本文件四处 /api/config 桩回调含 await route.fetch), route-cleanup 兜底已覆盖 | 并发/竞态(page 关闭 × route 回调收尾竞速) | Done | 已修(2026-11-13 随 58d443a8 八 spec 接线一并纳入; 2026-11-15 认领复验: 两锚点 spec 容器 --full 形态 14 例全绿 2.1m, 阈值面零改动); 去向 [26-11-13-0212](../issues/26-11-13-0212-test-e2e-testbed-timing-sensitive-specs.html) | 2026-11-15 |
| `e2e/settings-backup.spec.mjs` 8 例双皮肤恒红 —— 桩进程漏读宿主用户级 GTM 指针(工具在线) => bundle.gtm 非 null / gtm pill 可选 / POST sections 带 gtm 段, 与 spec「工具不运行」前提相反 | 共享状态(桩环境污染) | Done | 已修(2026-11-18): `scripts/ui_harness.py::_isolate_gtm_discovery` 在 create_app 前把 `agent.pointer_dir()` 重定向到桩私有临时目录; 产品/spec 零改动; 修后单跑 12 passed(修前 4P/8F); 去向 [26-11-18-0308](../issues/26-11-18-0308-test-e2e-settings-backup-gtm-bundle-drift.html) | 2026-11-18 |
| `e2e/perf.spec.mjs:143` atlas P1-2/P1-3 A/B 埋点 —— ~~负载/时长敏感候选~~ 经认领复现改判: **量具计数窗口错位**, `__gbr` 整页累计但预算只描述 B 段, A 段全量渲染计数被算进 B 段(短跑即可复现: atlas 累计 139 > 130, prism 102 < 125); 另一 clone W2 独立归因补双根因: 背景轮询 tick 恒回传 status 触发根重渲+逐行量高(拖穿不含墙钟项的预算) + off 侧 rowWin 复原重开窗迁移探测(prism 24/atlas 54 次, 与轮数无关, 纯净窗口下 atlas 仍 139>130) | time(边界/粒度)(量具计数窗口错位+墙钟敏感混入, 非负载型; 同族先例 dt-live-update 26-11-13-0519 / perf W5 26-11-10; 坑档 bench-assertion-calibration) | Done | 已修(2026-11-18, 两 clone 同题合流): `benchRun` 每段起清零 `window.__gbr`(判据只看 on 侧) + bench 前轮询隔离(stopPolling+stopEvents+影子 scheduleNext) + off 侧宽松上限反面断言 OFF_GBR_CEILING=130(红验 930/964), 预算公式/阈值/rounds 零改动; 修后整 spec 8P/4S 两轮全绿(远端) + 另一 clone 本机 5 轮全绿+红验三断言双皮红+test.quick 6443 绿; **容器 --full 原始红形态已复验绿**(2026-11-18 W4, 会话 aqb-54659 完整轮: 646P/3F/23S 1.5h, perf.spec 12 满额 8 passed + 4 skip(300 档条件门控 :305/:442 双皮, 与判据无关), P1-2/P1-3 prism 7.4s / atlas 7.8s passed, 3 failed 均与本 spec 无关); Windows 全量串行形态未单独复验; 去向 [26-11-18-0308](../issues/26-11-18-0308-test-e2e-perf-ab-metrics-load-red.html) | 2026-11-18 |
| `e2e/kbd-scroll-band.spec.mjs:102` atlas「Home/End 到首末行」 —— shard 2/3 轮闪一次(pollBand 几何判据, 1红/146绿, 共147例), 串行全量同轮绿; 同族 2026-11-10 修过 GitHub runner 面(本表上方), 本次是新形态偶红待采样 | 并发/竞态(几何判据等待窗口候选) | Open | 已入池 [26-11-18-0308](../issues/26-11-18-0308-test-e2e-kbd-scroll-band-shard-flake.html); 已采样(2026-11-18 W3, 3 轮 shard=3 并发形态 0 复现): 轮1 全量三 shard 全并发该例绿(8.9s) / 轮2 grep 该例 repeat-each=20 共 20 例全绿 / 轮3 repeat-each=60 共 60 例全绿 —— 合计 81 例, 挂起待自然复现 | 2026-11-18 |
| `e2e/menus.spec.mjs:425` prism「CTX-fit 右缘钳进视口」 —— 容器 testbed --full 闪一次(右缘 1440 > 1432, 整 8px 差), Windows 同轮绿; 容器慢 CPU/渲染家族候选待采样 | platform(容器形态差候选, 整 8px 像机制问题非噪声) | Open | 已入池 [26-11-18-0308](../issues/26-11-18-0308-test-e2e-menus-ctx-right-edge-container-red.html); 已采样(2026-11-18 W4, 0 复现): 阶梯 1 容器单 spec `-g "CTX-fit 右缘" --repeat-each=10` 双皮共 20 例全绿(1.2m) + 容器 --full 两轮(轮1 aqb-18412 跑至 settings-backup 段被杀, menus 段零失败工件; 轮2 aqb-54659 完整 646P/3F/23S 1.5h, CTX-fit 右缘双皮绿 6.3/6.7s) —— 根因候选(settle 复核链 retries=10 预算耗尽)未证实, 产品面零改动, 挂起待自然复现 | 2026-11-18 |

> 状态词与四形态 5 词表同源: `Open` → `In Progress` → `Done` | `Dropped`。

## 巡检约定(S6 周巡检 job 引用)

**巡检入口单点**: `commands run test.random-order`(pytest-randomly 随机序采样; 主套件默认顺序
不受影响 —— 插件在 pytest.ini addopts 以 `-p no:randomly` 整体禁用, 只在该入口经 `-o addopts=`
替换加载)。每轮头部打印 `--randomly-seed=<N>` 可复现; 红灯固定 seed 复现归因后登记本台账,
reruns 不是修复(`-- --samples N` 多轮统计采样)。

周巡检(pytest-randomly 随机序采样)除随机序本身外, **顺带过两遍清单**, 偏离即红/登记:

1. **skip 清单**: 全库 `skip` 必须**带 reason + issue**(入池链接); 裸 skip(无 reason 或无 issue)按
   D5 口径当场补或当场修 —— 扫法: `grep -rn "test.skip\|pytest.skip\|skipif" tests/ e2e/` 对本台账与
   `issues/_index.md` 核对。
2. **本台账条目**: 逐条核状态 —— `Open` 超两周未动升优先级或显式 Dropped(写明理由);
   `Done` 的抽查一遍去向链接(基线切片/issue)未断; CI 探测器(retries:1)报出的 flaky 标记
   当场登记进台账并当场修(见上口径)。
