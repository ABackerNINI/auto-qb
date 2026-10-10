# 2959 —— 抽屉 peers 速度键名适配(用户页上下行恒 0 修复)基线

> 摘要: 用户报「种子详情用户页中上下行始终为 0」。根因 = qB `sync/torrentPeers` 的对端速度字段是 `dl_speed` / `up_speed`(qB 原始命名), 而前端抽屉全部消费点(经典表经 `drawerPeerRows`、变体 07/08/09 的 `peerList`)统一按 `dlspeed` / `upspeed` 取名 ⇒ 取不到值 → 恒 0。修 = 落袋单点 `drawer.js::_drawerNormPeers` 补键(dict/数组双形态同归一)。配套修 `scripts/ui_harness.py` 桩保真(合成对端速度键名改回真 qB 形状)+ 补 e2e「上下行至少一格含数字」守卫与静态守阵。机理入坑档 `pitfalls/backend/qb-api.md`。
> 档案: memory-bank/tasks/26-10-10-webui-peers-speed-field.md
> 基线时间: 2026-10-10 19:05

**Refs:** memory-bank/tasks/26-10-10-webui-peers-speed-field.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `ccc97d14`, 无快进; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2959 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 28.87s)
- e2e 实测: `npm run test:e2e:fast` **46 passed**(含 peers 两条 spec —— `drawer-peers.spec.mjs`「用户页签渲染对端表」新增速度列守卫, `drawer-peers-sticky-flush.spec.mjs` 桩键名改真 qB 形状后几何守阵不受影响)。

## 本轮改动面

- `shared/drawer.js` —— 新增 `_drawerNormPeers(resp)`; `_fetchDrawerPeers` 落袋改走该单点。
- `scripts/ui_harness.py` —— `_PEER_SCENES` / `_make_peers_response` 合成对端速度键名 `dlspeed`/`upspeed` → `dl_speed`/`up_speed`(桩保真)。
- 守阵 `tests/test_webui_static_dom_panel.py`(新增 `test_drawer_peers_speed_keys_normalized` + 头部 docstring 补一条); e2e `drawer-peers.spec.mjs`(加速度列守卫 + 文件头注释)、`drawer-peers-sticky-flush.spec.mjs`(内联桩键名同步真形状)。
- 知识库回写: activeContext 切片 + 坑档 `pitfalls/backend/qb-api.md`(新条 + 复发链)与 `pitfalls/testing/stubs-sim.md`(复发 +1) + 本切片。
- `src/` 后端零改动; Linux(WSL 沙箱)侧未重测 —— 本轮只改平台无关的前端静态 JS 与断言面(口径见 baseline.md 常驻警告; 与近几轮切片同处理)。

## 守卫收口

- 反向对照已做: 临时撤销 `_fetchDrawerPeers` 的落袋适配 → 静态守阵如实报红(`peers 落袋未过 _drawerNormPeers`), 还原即绿。
- `kb.check` / `doc.caps` 见收尾复跑结果。
