# 抽屉 peers 速度键名适配(用户页上下行恒 0)

> 摘要: 用户报「种子详情用户页中上下行始终为 0」。根因 = qB `sync/torrentPeers` 的对端速度字段是 `dl_speed` / `up_speed`(qB 原始命名, 源码 `synccontroller.cpp` 的 `KEY_PEER_DOWN_SPEED`/`KEY_PEER_UP_SPEED`), 而列表侧 `torrents/info` 才是 `dlspeed` / `upspeed` —— 前端抽屉全部 peers 消费点(经典表经 `drawer.js::drawerPeerRows`、变体 07/08/09 各自 `peerList` 直读原始对端对象)统一按 `dlspeed` / `upspeed` 取名 ⇒ 取不到值 → 上下行恒 0(其余列 downloaded/uploaded/flags/progress/relevance 同名故正常)。修 = 落袋单点新增 `_drawerNormPeers` 补键(dict/数组双形态同归一), 一处修好全部消费点。配套修桩保真: `scripts/ui_harness.py` 合成对端原本也用错键名(冒烟「看得见速度」而真机恒 0, 逃过全部 e2e), 已改回真 qB 形状; 补 e2e 速度列守卫 + 静态守阵。机理入坑档 `pitfalls/backend/qb-api.md`(新条), 桩教训入 `pitfalls/testing/stubs-sim.md`(复发 +1)。
> 最后活动: 2026-10-10 19:05

**Refs:** memory-bank/tasks/26-10-10-webui-peers-speed-field.md

## 正在进行

- 无 —— 本轮已完成并收口(见 kb.baseline)。

## 关键结论(供后续消费 qB 对端 / 写桩数据参考)

- **qB 两套接口同义字段不同名**: 列表侧(`torrents/info`、`sync/maindata` 的 torrents)用 `dlspeed`/`upspeed`; **对端**对象(`sync/torrentPeers`)用 `dl_speed`/`up_speed`。对端里只有速度两列不同名 —— 取错键时表现为「只坏上下行」。
- **落袋单点适配**: `_drawerNormPeers` 是唯一适配点, 经典表与 07/08/09 三个变体都吃同一份落袋数据, 不在消费点各写一遍(否则四处漂移)。
- **桩数据必须对字段「名」不只对「形」**: 只对形状(dict/数组)不够 —— 本 bug 正是桩用了错键名而 e2e 又只断「行存在」, 速度列全 `—` 也不红。写桩时对照真 qB 键名; 断言尽量覆盖「值」而非只覆盖「存在」。
