# webui-traffic-chart-stale-inverted — 种子/分组流量图恒不加载(stale 谓词取反翻面)

> 摘要: 用户报「种子流量图加载不出来」并自注「可能是最近的多段限速线引入的」。取证**推翻该假设** —— 限速分段提交(c892a447)只动 `_qbDrawLimits`/纯函数/tooltip, 未碰 `_QB_SCOPES`。真根因在**更早的 W2–W6 抽屉重构**(0d07dbdd): 机械改名 `t.drawer.kind === "seed"` → `t.drawerIsSeed` 时, `torrent` 与 `group` 两处 `stale` 谓词被整行重写成 `!!(...)`(`global` 那处保留 `!(` 未中招)。语义翻面 = 恰在「本图正在被看」时判「响应已过期」⇒ `_qbLoad` 数据不落袋 + `loading` 不复位 + 早退不建图 ⇒ `qbCurPending` 恒真、轮询被卡住的 `loading` 挡住 ⇒ 面板永远停在「正在加载流量数据…」。修 = 两处恢复否定式 `!(...)`(2 行) + 新增运行时守阵(node 电池真跑三挂点谓词与 `_qbLoad` 落袋, 配静态极性兜底), 全量测试绿(见 `commands run kb.baseline`)。**真机走查待用户**。

**创建:** 2026-10-12 19:03
**最后活动:** 2026-10-12 19:03
**主题:** webui-traffic-chart-stale-inverted
**摘要:** 缺陷面 = `src/auto_qb/webui/static/shared/qb_traffic_chart.js` 的 `_QB_SCOPES.torrent.stale` 与 `.group.stale`。症状链(为什么是「加载不出来」而不是报错): `stale=true` ⇒ ①数据不落袋 ②`finally` 里 `if (!stale) loading = false` 不复位 ③`if (stale) return` 早退不建图 ⇒ `qbCurPending`(`loading && 无数据 && 无错误`)恒真 ⇒ 恒显「正在加载流量数据…」, 且轮询 tick 被 `loading` 挡住 ⇒ 永不自愈。为什么既有守阵没拦住: 本仓对 `_QB_SCOPES` 的断言全是**源码字符串级**, 而 `!` 与 `!!` 的差别只在运行时语义; 且这两处 `!!(` 与合法的布尔强制转换(`drawerIsSeed` 定义处、`active` 谓词)在文本上完全同形, 按形态扫 `!!(` 会误伤。守阵 = `tests/test_webui_static_dom_panel.py::test_frontend_qb_traffic_scope_stale_polarity`(静态极性兜底 + node 电池: `new Function(源码 + "return _QB_SCOPES;")` 取作用域表 —— 模块级 `const` 不会被 sloppy 直接 eval 漏出; 三挂点五类上下文断言 `stale` 真假 + `active => stale === false` 同向性 + 假 vm 真跑 `_qbLoad` 断言落袋与 `loading` 归位)。红验两层各自独立闭环。未做浏览器级端到端复现: e2e 桩服务不下发 `qb_traffic_enabled` 也不提供 `/api/traffic/qb/*`。
**Refs:** memory-bank/pitfalls/web-ui/stale-predicate-inverted.md,memory-bank/testing/baselines/26-10-12-1903-webui-traffic-chart-stale-inverted.md
