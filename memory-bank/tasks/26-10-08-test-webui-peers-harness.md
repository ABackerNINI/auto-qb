# 26-10-08-test-webui-peers-harness — ui_harness 补合成 peers 数据 + e2e 覆盖 peers 页签内容渲染

**Status:** Done
**Added:** 2026-10-08
**Updated:** 2026-10-08
**Summary:** 用户指派认领并修复 issue 26-10-07-2309 —— 桩服务 `scripts/ui_harness.py` 的 `FakeClient.peers_map` 恒空 ⇒ `/api/torrents/{hash}/peers` 恒回 `{peers: []}`, 详情抽屉 peers 页签在桩下**永远**只走空态(「暂无已连接用户」), e2e 与截图目检从未覆盖有数据渲染路径。修法 = 桩新增 `_PEER_SCENES`/`_make_peers_response(i)` 按种子序号灌合成 `sync/torrentPeers` 整包(dict 形态, flags/速度/进度/客户端多样性), 并新增 `e2e/drawer-peers.spec.mjs`(双皮肤 @fast)钉住对端表渲染。红验: 禁用桩注入 ⇒ 2 failed(表不可见), 还原 2 passed。e2e 全量 94 passed / 10 skipped / 0 failed(3.4m)。
**Topics:** webui-peers-harness

**Refs:** memory-bank/issues/26-10-07-2309-test-webui-peers-harness.html,memory-bank/testing/baselines/26-10-08-0223-test-webui-peers-harness.md

> 背景关联(不进机器认领链): 本缺口在 tooltip 修复轮(专题 `webui-tooltip-declutter`, 档案 [26-10-04-webui-tooltip-declutter](26-10-04-webui-tooltip-declutter.md))真浏览器实测时发现并入池; 当时靠 Playwright route 拦截注入合成 peers 才完成 peers 场景验证。

## 原始请求

用户指令: 「认领并修复 issue: memory-bank/issues/26-10-07-2309-test-webui-peers-harness.html」 —— 即 create-issue 流程的「修一条 issue 时」路径: 用户显式指派认领(非 agent 自认领) → 复验 → 修复 → 置 Done + 补实测数字 → 认领链双向闭合。

## 思考过程与决策

- **复验(先红后绿)**: 按 create-issue 防过期原则第 5 条, 先按锚点核对 —— `scripts/ui_harness.py` 起盘只填 `mgr.client.torrents`, **从不填** `mgr.client.peers_map`; `e2e/` 目录 grep `peers` 零命中(无任何 peers 内容断言)。现象**仍在**。
- **修法选择(按 issue 建议, 未改道)**: ①桩侧灌数据, ②补 @fast 内容断言。二者缺一不可 —— 只补断言会恒红(桩无数据), 只灌数据无断言则下次改桩仍会静默丢覆盖。
- **保真口径(桩失真红线)**: peers 响应用 **dict**(以 `"ip:port"` 为键)而非数组 —— 真 qB `sync/torrentPeers` 恒为 dict, 前端 `drawerPeerRows` 做 dict/数组双形态归一; 桩若图省事给数组, 归一的 **dict 分支就永远测不到**(与 `tests/helpers.py::FakeClient.sync_torrent_peers` 同口径, 见 pitfalls/testing/stubs-sim.md)。
- **多样性设计**: 对端数与组合按种子序号 `i` 轮转(1~7 个, 首尾相接地错开), 单种全量轮转只覆盖一种形态(冒烟会"自以为测过")。场景集覆盖前端全部派生分支: 方向五桶(U/D/u/K/握手未完成)、吸血嫌疑启发式(迅雷/XL)、内网(192.168/10.)与公网/IPv6、速度/进度/关联度的零值与非零值、`files` 渐进字段。
- **断言落点**: 默认模板为 classic(`drawerTplSel.peers` 初值), 故断言落在经典表 `.drawer-table` 上(非空 + 首行地址列有 `ip:port` + 空态文案不出现)。变体 07/08/09 同吃这份数据(其空态文案同为「暂无已连接用户」), 但本次不新增变体切换断言(默认 classic 覆盖主路径, 变体切换属另一专题)。
- **范围守恒**: 只动桩数据面(`scripts/ui_harness.py`)+ 新增 1 个 spec 文件; 未触碰生产端点/前端渲染逻辑/其它 spec。

## 实现计划

单步(单会话可闭): ① 复验(核对桩恒空 + e2e 零覆盖)→ ② 桩加 `_PEER_SCENES`/`_make_peers_response` 并在起盘按种子灌 `peers_map` → ③ 新增 `e2e/drawer-peers.spec.mjs`(双皮肤 @fast)→ ④ 红验(禁用注入 ⇒ 红)+ 还原绿 → ⑤ `dev.e2e` 全量轮 + `test.full` + 基线切片 → ⑥ 收尾回写(issue 状态/认领链、档案、切片、spec 数文档、kb.index)。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| F0 | 复验(桩 `peers_map` 恒空 + e2e 零覆盖) | ✅ | 现象仍在 |
| F1 | 桩补合成 peers(`_PEER_SCENES` + `_make_peers_response` + 起盘注入) | ✅ | `scripts/ui_harness.py` |
| F2 | 新增 @fast e2e 内容断言 | ✅ | `e2e/drawer-peers.spec.mjs`(双皮肤) |
| F3 | 红验(禁用注入 ⇒ 2 failed; 还原 ⇒ 2 passed) | ✅ | 断言非恒真 |
| F4 | 收口: e2e 全量 + test.full + 基线 + 回写 | ✅ | e2e 94+10 / test.full 见基线 26-10-08-0223; 档案/切片/issue 回写; kb.index 重建 |

## 进度日志

- **2026-10-08 02:17** 会话开工: 同步 `已同步 f5315a8d`; 读 issue 26-10-07-2309(Open/light/test)+ tooltip 档案 + `scripts/ui_harness.py` + `e2e/` 全量 + 抽屉 peers 渲染链(`drawer.js::drawerPeerRows` / `tpl/drawer.html` 经典表 / 变体 07)。
- **2026-10-08 02:1x** 复验: 桩起盘只填 `client.torrents`, `peers_map` 恒空; `e2e/` 无 peers 内容断言 ⇒ 现象仍在, 用户已显式指派认领(非自认领)。
- **2026-10-08 02:1x** 落码: `_PEER_SCENES`(7 场景) + `_make_peers_response(i)`(1~7 对端轮转, dict 形态) + 起盘按 `enumerate(torrents)` 灌 `mgr.client.peers_map`; 新增 `e2e/drawer-peers.spec.mjs`。
- **2026-10-08 02:1x** 红验: 临时把注入循环置空 ⇒ 本 spec **2 failed**(prism/atlas, 表不可见); 还原 ⇒ **2 passed**。
- **2026-10-08 02:22** 收口: `commands run dev.e2e` 全量轮 **94 passed / 10 skipped / 0 failed(3.4m)**(含新增 2 条); `npm run test:e2e:fast` **8 passed(19.4s)**(改前 6); `commands run test.full` **2771 passed + 4 skipped / 0 failed / 57.8s / TOTAL 99%**(pytest 侧零改动, 与上基线逐位持平; 见基线切片 [26-10-08-0223](../testing/baselines/26-10-08-0223-test-webui-peers-harness.md)); issue 置 Done + 认领链回填; 三处「七个 spec」文档改「八个 spec」; `kb.index` 重建。
