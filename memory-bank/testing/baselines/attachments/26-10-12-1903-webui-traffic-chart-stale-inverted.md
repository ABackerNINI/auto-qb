# 3147 —— WEBUI 种子/分组流量图恒不加载(stale 谓词取反被写成双重取反)

**Refs:** memory-bank/pitfalls/web-ui/stale-predicate-inverted.md

> 摘要: 用户报「种子流量图加载不出来」并自注「可能是最近的多段限速线引入的」。取证推翻该假设: 限速分段提交(c892a447)只动 `_qbDrawLimits`/纯函数与 tooltip, 未碰 `_QB_SCOPES`。真根因在**更早的 0d07dbdd**(W2–W6 抽屉重构): 机械改名 `t.drawer.kind === "seed"` → `t.drawerIsSeed` 时, 把 `torrent` 与 `group` 两处 `stale` 谓词的 `!(...)` 整行重写成 `!!(...)`(`global` 那处保留 `!(` 未中招)。语义整个翻面 = 恰在「本图正在被看」时判「响应已过期」⇒ `_qbLoad` 数据不落袋 + `loading` 不复位 + 早退不建图 ⇒ `qbCurPending` 恒真、轮询被卡住的 `loading` 挡住 ⇒ 面板永远停在「正在加载流量数据…」。修 = 两处恢复否定式 `!(...)`(2 行) + 新增运行时守阵(node 电池真跑 `_QB_SCOPES` 三挂点 + `_qbLoad` 落袋断言, 配静态极性兜底)。
> 基线时间: 2026-10-12 19:03

上一基线: memory-bank/testing/baselines/26-10-12-1833-webui-frozen-col-shadow.md

## 本波改动面

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: `_QB_SCOPES.torrent.stale` 与 `_QB_SCOPES.group.stale`
  由 `!!(…)` 改回 `!(…)`(各 1 行, 连同注释说明「`!stale` 才是可落袋」的极性口径)。
  `active` 谓词、`global` 挂点、建图/注解层/限速分段代码**一行未动**(限速功能零回归)。
- `tests/test_webui_static_dom_panel.py`: 新增 `test_frontend_qb_traffic_scope_stale_polarity`(+1 用例)
  —— ①静态极性兜底(`stale` 必须 `!(t`, 禁 `!!(`); ②node 电池 `_NODE_QB_SCOPE_STALE_PROBE`:
  用 `new Function(源码 + "return _QB_SCOPES;")` 取出作用域表(模块级 `const` 不会被 sloppy 直接 eval 漏出),
  对三挂点喂五类真值上下文断言 `stale` 真假 + `active => stale === false` 同向性, 并用假 vm 真跑 `_qbLoad`
  断言成功响应落进 `qbTorrentData`/`qbGroupData` 且 `loading` 归位; 测试计划清单同步 +1 行。
- `memory-bank/pitfalls/web-ui/stale-predicate-inverted.md`: 新增(取反翻面 × 静态锚失明 × 卡加载态三特征 + 守阵)。

## 验收数字

- `test.full`: **3147 passed + 4 skipped, 0 failed** / 55.0s–59.3s(两次采样) / 覆盖率 `TOTAL 16708 161 5688 140 99%`。
- 红验两条(**两层各自独立**闭环): 把两处 `!(…)` 注入回 `!!(…)` ⇒
  ① 静态极性层**即红**(`AssertionError: torrent.stale 必须是否定式`), ② 绕开静态层单跑 node 电池
  **同样即红**(21 项里 14 项失败, 含「落袋: 种子流量响应进入 qbTorrentData」「落袋: 种子 loading 已复位」);
  还原**即绿**。
- 注: 本片只测 Windows 侧; Linux 侧未重测(改动为纯前端判据, 无平台面)。
- 注: 本波**零测试删除**, 新增 1 条守阵 —— 收集数 3151 = 3147 passed + 4 skipped。
- 注: 未做浏览器级端到端复现 —— e2e 桩服务(`scripts/ui_harness.py`)不下发 `qb_traffic_enabled` 也不提供
  `/api/traffic/qb/*`, 补这条链属另一件事; 本次以「node 真跑 `_qbLoad` 落袋」作为消费端判据, 真机走查待用户。
