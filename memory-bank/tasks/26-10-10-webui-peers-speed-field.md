# 26-10-10-webui-peers-speed-field — 抽屉 peers 上下行恒 0 修复

**Status:** Done
**Added:** 2026-10-10
**Updated:** 2026-10-10 19:05
**Topics:** webui-peers-speed-field
**Summary:** 用户报「种子详情用户页中上下行始终为 0」。根因 = qB `sync/torrentPeers` 的对端速度字段是 `dl_speed` / `up_speed`(qB 原始命名), 而前端抽屉全部 peers 消费点(经典表经 `drawerPeerRows`、变体 07/08/09 的 `peerList`)统一按 `dlspeed` / `upspeed` 取名 ⇒ 取不到值 → 恒 0(其余列同名故正常, 「只坏上下行」即本坑指纹)。修 = 落袋单点新增 `drawer.js::_drawerNormPeers` 补键(dict/数组双形态同归一)—— 一处修好全部消费点。配套修桩保真: `scripts/ui_harness.py` 合成对端原本也用错键名(冒烟「看得见速度」而真机恒 0, 逃过全部 e2e), 已改回真 qB 形状; 补 e2e 速度列守卫 + 静态守阵。
**Refs:** memory-bank/testing/baselines/26-10-10-1905-webui-peers-speed-field.md,memory-bank/activeContext/26-10-10-1905-webui-peers-speed-field.md,memory-bank/pitfalls/backend/qb-api.md,memory-bank/pitfalls/testing/stubs-sim.md

## 原始请求

> 用户(2026-10-10): 「种子详情用户页中上下行始终为0」

## 思考过程与决策

- **请求边界判定**: 这是一条缺陷报告(执行任务), 非「问答/只读」—— 定位后直接修复, 不另出计划/报告。
- **根因定位**: 前端 `drawerPeerRows()` 读 `x.dlspeed` / `x.upspeed`, 变体 07/08/09 的 `peerList()` 也读 `p.dlspeed` / `p.upspeed`; 而 `/api/torrents/{hash}/peers` 是 qB `sync/torrentPeers` 整包**透传**, 其**对端对象**速度字段是 `dl_speed` / `up_speed`(核对 qB 源码 `synccontroller.cpp` `KEY_PEER_DOWN_SPEED`/`KEY_PEER_UP_SPEED`, 及第三方 Go/C# 客户端模型)。对端里 `downloaded`/`uploaded`/`flags`/`progress`/`relevance` 与列表侧同名 ⇒ **只有上下行坏**, 与用户描述吻合。
- **修法选型(单点)**: 两个方向可修 —— ①各消费点各读对键名(4 处, 易漂移); ②在**落袋单点** `_fetchDrawerPeers` 做一次键名适配, 全部消费点(含未来新增)自动受益。选 ②: 新增 `_drawerNormPeers(resp)`, 只补 `dlspeed`/`upspeed`(保留原键), 覆盖 peers 的 dict(真 qB 恒 dict)与数组两形态。
- **桩保真(关键)**: 本 bug 能逃过全部 e2e, 是因 `scripts/ui_harness.py` 合成 peer 数据时用了 `dlspeed`/`upspeed`(正是错名形状)—— 冒烟「看得见速度」、真机恒 0, 属测假。修桩用真 qB 键名, 并给 e2e 补「值」守卫(原断言只断「有行 + 地址有 ip:port」, 速度列全 `—` 也不红)。
- **不越界**: 未改后端路由的「整包透传」契约(适配落在前端落袋层); 未顺手改其它无关模块。

## 实现计划

- **S1** 前端落袋单点 `drawer.js::_drawerNormPeers` + `_fetchDrawerPeers` 改走该单点。
- **S2** 桩保真 `scripts/ui_harness.py`(合成对端速度键名 → `dl_speed`/`up_speed`)。
- **S3** 守阵: 静态 `test_drawer_peers_speed_keys_normalized` + e2e `drawer-peers.spec.mjs` 速度列守卫 + `drawer-peers-sticky-flush.spec.mjs` 内联桩键名同步。
- **S4** 验证(反向对照 + test.full + e2e)与知识库收尾(坑档/切片/基线/档案/kb.index)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 前端落袋单点键名适配 | Done |
| S2 | 桩保真(ui_harness 键名) | Done |
| S3 | 静态守阵 + e2e 守卫 | Done |
| S4 | 验证 + 知识库收尾 | Done |

## 进度日志

- **2026-10-10 19:05** 开工 sync 已同步 `ccc97d14` → 定位根因(qB `sync/torrentPeers` 对端速度键 `dl_speed`/`up_speed`, 前端读 `dlspeed`/`upspeed`)→ S1 落袋单点适配 + S2 桩保真 + S3 守阵/守卫 → 反向对照(撤销落袋适配 → 静态守阵如实报红) → `test.full` **2959 passed + 4 skipped / TOTAL 99%**、e2e fast **46 passed**(基线切片 `26-10-10-1905`)→ 坑档 `pitfalls/backend/qb-api.md`(新条)+ `pitfalls/testing/stubs-sim.md`(复发 +1)入库 → `kb.index` 重建。
