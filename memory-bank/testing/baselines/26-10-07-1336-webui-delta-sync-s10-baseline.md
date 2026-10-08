# 2745 —— WebUI rid 式增量同步实施计划 S10 收尾基线 (feat/webui-delta-sync, e2e 复测归档 + 收尾)

> 摘要: 计划 [26-10-07-0414-plan-webui-delta-sync.html](../../plans/26-10-07-0414-plan-webui-delta-sync.html)
> S10 收尾步(P-03 门控裁决落地 / 口径回写 / e2e 复测归档 / 收尾 DoD)的最终基线,
> 对比 S9 基线(2744+4 / 32.47s / 99%)。e2e 复测含分档实测(before/after)与
> 存量缺陷记录(见「e2e 复测」段, 均非 S10 引入)。
> 基线时间: 2026-10-07 13:36

**Refs:** memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html, [26-10-07-1213-webui-delta-sync-s9-baseline.md](26-10-07-1213-webui-delta-sync-s9-baseline.md), [26-10-07-0514-webui-delta-sync-s0-baseline.md](26-10-07-0514-webui-delta-sync-s0-baseline.md), memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md, memory-bank/activeContext/26-10-07-0204-webui-delta-sync-feasibility.md, memory-bank/tasks/26-10-08-webui-perf-issues-closing.md, memory-bank/issues/26-10-08-0818-test-webui-e2e-stub-fidelity-s7-memo.html

## test.full 实测

- 分支: feat/webui-delta-sync(本地分支, S10 不做 sync; 工作树含 S10 注释/文档未提交改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2745 passed + 4 skipped, 0 failed, 35.4s, 覆盖率 TOTAL 99%**
  (16259 语句 / 166 未覆盖 / 5686 分支 / 150 partial; 门槛 98% 达标)
- 相对 S9 基线 [26-10-07-1213](26-10-07-1213-webui-delta-sync-s9-baseline.md)
  (2744 passed + 4 skipped @ 32.47s, 16254 语句 / 166 未覆盖 / 5684 分支 / 150 partial):
  passed **+1**(S6补 1ad13659 入库的组行重建为空转 removed 守阵, 在 S9 切片之后)/
  未覆盖持平 / 分支 +2 / partial 持平; 语句 +5 在在账 ±200 摆动簇内。满足
  「passed 只升不降、未覆盖 / partial 不升」判据。4 skipped 为 Windows 侧 POSIX 专属存量。
- S10 本步 src 侧仅注释/docstring(P-03 裁决 + 口径回写 + 指纹注释修正), pytest 面零新增。

## e2e 复测(分档实测, 桩环境口径)

**口径总注**: 全部实测于本机桩环境(`scripts/ui_harness.py` 真实 create_app + 合成种子,
200 组两两归组 + 未归组单种子; chromium 1440x900)。S0 切片「before」段是 2026-09-19
**真机**口径, 数据构成与桩不同源 —— **绝对值不可直接比**, 可比的是同树同数据下的
全量 vs 增量差与随档位的标度; 真机网络延迟桩测不了, 如实标注。

### 服务端(进程内实测, dumps 与 JSONResponse.render 同参 separators)

| 指标 @档位 | 1000 | 3000 | 5000 |
|---|---|---|---|
| 全量回包(四数组)字节 | 2,957,336 | 8,679,926 | 14,402,499 |
| 全量 json.dumps ms | 19.79 | 55.72 | 86.33 |
| **delta 回包(1 脏行, view=torrent)字节** | **1,809** | **1,809** | **1,809** |
| delta json.dumps ms | 0.02 | 0.01 | 0.01 |
| 全量 rebuild_views ms | 37.03 | 118.37 | 257.21 |
| 1 脏行 flush_views(局部重聚合)ms | 8.69 | 32.82 | 114.72 |

- before(S0 在账, 3000 真机): 全量回包 **6.3 MiB** / dumps **26.4ms**。after 桩 3000
  全量 8.28 MiB / 55.7ms —— 桩数据构成不同(2600 singles 全量行 + 组行 members 内嵌),
  绝对值不可比; **可比项 = delta 载荷 1,809 字节 ≈ 同数据全量回包的 1/4800**, 且不随档位增长。
- 局部重聚合剩余成本的大头是 `speed_totals` 现算(O(全库) 扫描, docstring 明言
  "无行键可归约, 仍现算")—— 在账口径, 非缺陷, 记录供后续优化立项参考。

### HTTP 往返(环回, http.client 连接复用; 「一轮序列化+网络+解析」的桩替代口径)

| 指标 ms @档位 | 1000 | 3000 | 5000 |
|---|---|---|---|
| 全量 GET /api/state(四数组) | 25.41 | 93.75 | 109.81 |
| **delta GET(1 脏行)** | **3.44** | **3.96** | **3.85** |
| 零回传(rid==ver, 轮询稳态) | 2.21 | 2.26 | 1.74 |

- before(S0 在账, 3000 真机): 一轮 ≈**63ms**(runtime 注释口径)。after 桩 3000:
  全量 93.8ms(真机网络段测不了)/ **delta 4.0ms / 零回传 2.3ms** —— 稳态轮询成本
  从 O(全库) 降到 O(1), 1 脏行轮 O(脏行); 均不随档位增长(5000 档与 1000 档持平)。

### 前端 refresh(perf.spec A/B bench, refresh + 2×rAF settle 口径, 稳态=后两轮均值)

| 档位 | 全量整表替换(prism / atlas) | 窗口化(prism / atlas) | delta 轮(1 脏行, prism) |
|---|---|---|---|
| 300(dev.e2e 默认档) | 83 / 84 ms | 40-50 / 49-50 ms | - |
| 1000 | 197 / 262 ms | 92 / 98 ms | 36-40 ms |
| 3000 | 562 / 816 ms | 223 / 243 ms | 29-40 ms |
| 5000 | 1832 / 1712 ms | 372 / 416 ms | 33-43 ms |

- before(S0 在账, 2026-09-19 真机全量渲染): 1000 **143ms** / 3000 **309ms** / 5000
  **396~501ms**。after 桩全量(非窗口)数字显著更高 —— 主因是桩数据构成不同
  (8.3 MiB @3000 vs 真机 6.3 MiB)叠加双 rAF 帧同步底噪, 不可直接比;
  **可比项 = 同口径同数据下 delta 轮(1 脏行)29-43ms, 与档位无关**(S7 窗口化
  与 S4 增量合并叠加后, 前端每轮成本 = O(窗口/脏行) 而非 O(全库))。
- delta 轮计时方法: 真实 vm.refresh 全链路(fetch + JSON.parse + applyStateRows +
  Vue 调度 + 2×rAF settle), 桩命令泵真 pause 手势喂脏行(2×rAF ≈ 32ms 帧同步底噪)。

## e2e 复测结论与存量缺陷(计划外, 未改, 留报告)

- `commands run dev.e2e`(默认 300 档): **86 passed / 10 skipped / 6 failed (4.1m)**。
  S4 切片对照点为 90/10/0 —— 6 条失败为 S5b-S9 期间积累的**存量问题**, S4 之后 e2e
  未重跑(S9 切片明言"e2e 复测归档排在 S10"), 本次 S10 复测首次暴露; 与 S10 改动
  (纯注释/docstring)无关。perf.spec 全档全绿(8 passed × 3 档), delta-sync.spec 全绿。
- **失败根因 A(4 条)**: `2ca5491f`(S6/S7 间回归修复)让桩命令真值轮改走真 `store._apply`
  后, `_apply` 会把 `store.hr_link`(HR 运行时对象)回写到记录上(helpers.py :607 为此给
  FakeTorrent 补了 `hr_link=None` 属性); 桩里 `FakeTorrent.to_dict()` 按 `vars(self)`
  导出且跳过清单 `{tor, tracker_conf}` 不含 `hr_link` ⇒ `/api/torrents/{hash}` 详情端点
  把 HrRuntime 对象塞进 JSON 序列化 → **恒 500**。受害: drawer-dock-stability 2 条
  (运行期错误守卫捕到 console.error 500)+ optimistic BUG-9 复制磁力 2 条(详情拉不到
  → toast「该种子没有 magnet 链接」+ 500 守卫)。
- **失败根因 B(2 条)**: optimistic「真值事件后不被陈旧快照打回」× 双皮肤 ——
  `applyOptimistic` 对成员行**原地** `Object.assign`(对象引用不变), 而 S7(582d1acd)
  的 decoratedGroups WeakMap 装饰记忆化按**组行对象身份**命中缓存 ⇒ 乐观补丁改了
  成员 kind 后组行 `status.primary` 不再自动重算(commands.js :395 的 2026-09-19
  口径注释被 S7 记忆化破坏), `afterPatch` 停留 "seeding"。
- 处置: 按范围守恒(黄金法则 6)一行未改 —— 根因 A 属 S6 补的桩保真回归面, 根因 B 属
  S7 记忆化与乐观 UI 的交互缺口, 各需独立小步(给 FakeTorrent.to_dict 跳过 hr_link /
  applyOptimistic 失配 _decoCache), 由编排方决定入池或另立小步。

## S10 步改动面

- `src/auto_qb/webui/runtime.py`(仅注释): P-03 裁决落地(pending_ver 字段声明 +
  flush_views 门控 + _publish_locked 赋值点三处注明「保留, 增量下成本=一次键集追加,
  纯冗余实测确认后另立小步移除」); flush_views / _publish_locked docstring 口径回写
  (时间线只存键/值回放现取/四视图同轮发布/单一写线程不破); HR 段「按内容指纹去重」
  错误注释修正(报告 26-10-07-0054 §06 指出, 张冠李戴)。
- `memory-bank/systemPatterns/web-runtime.md`: 新增「rid 式增量同步」机制单点段
  (时间线结构/变化源清单含 R11 全部降级源与 tracker_error_refresh 行级源/启用矩阵/
  delta=1 协商协议/full 触发面 R10/守阵指针); 涉改段落行号锚全部重锚(内容基线
  2026-10-07 @ 1ad13659)。
- 本切片 + activeContext 迁出 + tasks 档案追加 + pitfalls 两条(见收尾记录)。

## 对照判据(后续沿用)

- 以本切片(2745+4 / 16259 / 166 / 5686 / 150)为 S10 后对照点: 预期 passed 只升不降、
  未覆盖 / partial 不升; 回退先查该段改动。计划 S0-S10 全部完成, 本切片即该计划终态基线。
- e2e 对照点: dev.e2e 86 passed / 10 skipped / 6 failed(存量, 见上) —— 修根因 A/B 后
  应回到 92 passed / 10 skipped / 0 failed(86+6)。
