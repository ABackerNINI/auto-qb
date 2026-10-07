# test-webui-peers-harness — 桩服务 peers 数据补全与 e2e 内容覆盖

> 摘要: 用户指派认领并修复 issue 26-10-07-2309 —— 桩服务 `scripts/ui_harness.py` 的 `FakeClient.peers_map` 恒空, 抽屉 peers 页签在桩下永远空态、e2e 零覆盖。修法 = 桩按种子灌合成 `sync/torrentPeers`(dict 形态, flags/速度/进度/客户端多样性) + 新增 `e2e/drawer-peers.spec.mjs`(双皮肤 @fast)。已闭环, 档案 tasks/26-10-08-test-webui-peers-harness.md Done。
> 最后活动: 2026-10-08 02:23

## 已完成(详情见档案, 不在此复述)

- 桩 `_PEER_SCENES`/`_make_peers_response` 按种子序号灌 1~7 个合成对端(覆盖方向五桶/吸血嫌疑/内网/IPv6/渐进字段), 起盘写入 `mgr.client.peers_map`。
- 新增 `e2e/drawer-peers.spec.mjs` 双皮肤 @fast: 开抽屉 → 切「用户」页签 → 断言对端表非空 + 首行地址列 `ip:port` + 空态不出现。红验 2 failed → 还原 2 passed。
- e2e 全量 **94 passed / 10 skipped / 0 failed(3.4m)**; test.full 见基线 [26-10-08-0223](../testing/baselines/26-10-08-0223-test-webui-peers-harness.md)。

## 正在进行

- 无 —— 本专题已收口。

## 未决项

- 变体 07/08/09 的 peers 渲染(四卡派生/筛选/排序)未纳入本次断言(默认模板为 classic); 如后续需要, 另立断言。
