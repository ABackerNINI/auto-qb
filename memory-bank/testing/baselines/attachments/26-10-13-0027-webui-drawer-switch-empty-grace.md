# 3166 —— 用户页切换种子空态闪现修复(软切换首个空 peers 响应宽限, 第九次复发)

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/activeContext/26-10-13-0027-webui-drawer-switch-empty-grace.md

> 摘要: 用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」。前八次都在锚契约面/渲染驱动面, 本次在**数据落袋语义面**: 软切换(FX-29)「保留旧数据撑几何 + 遮罩防串显, 数据全部到手才掀罩」中, 「到手」只判"响应回来了"—— **空响应同样算**: 覆盖 `drawer.peers` 成 `{peers:{}}`(旧数据没了)+ 登记 `_drawerDone("peers")`(掀罩)⇒ 渲染层判 `!list.length` ⇒ 一帧空态; 真机换目标后 qB 对新种子的**首个** `/peers` 常瞬时为空(连接/状态未就绪)⇒「表格 → 暂无已连接用户 →(下一拍 5s)表格」。临时探针复现(已清): 80 对端真量级 + route 让切换目标首拍 /peers 返空 ⇒ classic/07/08/09 全部 `C80`→`E0`(~180 空态帧); 恒非空对照 0 帧。逃逸因: 桩 `_make_peers_response` 每个种子恒有 1~7 对端**从不返回空** + e2e 全部用例只 `dblclick nth=0` 单次打开(无"切换"用例)⇒ 双零覆盖。修复(方案A, 3 文件): `drawer_store.js::_fetchDrawerPeers` 换目标窗口内首个空响应判「未就绪」(不落袋/不掀罩/1s 后快速重拉一次, 仍空才接受); `_switchDrawerTarget` 于 `_loadDrawerTab` **之后**置 `_drawerPeerGrace`; `_stopDrawerPoll` 收口重拉 timer。守阵: 新 `test_drawer_peers_switch_empty_grace_wiring`(钉接线与次序) + 新 e2e「切换种子首个空 peers 响应不得闪现空态」(逐帧采样); 红验闭环(拆宽限 ⇒ 150 帧空态红 / 还原即绿)。
> 基线时间: 2026-10-13 00:27

上一基线：memory-bank/testing/baselines/26-10-12-2236-webui-drawer-tpl-flicker-fix3.md

## 验收数字

- `test.full`: **3166 passed + 4 skipped** / 覆盖率 `TOTAL 16718 158 5688 139 99%`(98.65%; 与上一基线相比 +1 = 本波新增守阵 `test_drawer_peers_switch_empty_grace_wiring`)。
- e2e(全量 `dev.e2e`): **197 passed + 10 skipped + 1 亚像素 flaky**(`drawer-peers-sticky-flush` atlas › dt07 吸顶, `gapAboveHead=1.399px` 略过 1px 容差 —— 与本改动无关的既有几何抖动, **复跑 4/4 绿**)。
- 抽屉 peers 套件(单跑): **22 passed / 0 failed**(含新增用例 × 2 皮肤)。
- 红验(拆 `_drawerPeerGrace` 置位): 新 e2e 用例 **150 帧空态** ⇒ 红; 还原即绿(闭环)。
- 复现探针(临时, 未进仓库): classic/07/08/09 全 `C80`→`E0`(80 对端真量级 + 切换目标首拍 /peers 返空); 恒非空对照 275 帧全 `C80`、0 空态帧。

## 本波改动面

- **生产代码**(1 文件): `src/auto_qb/webui/static/shared/drawer_store.js` —— `_fetchDrawerPeers` 加软切换宽限分支(`deferred` 短路 finally, 不落袋/不 `_drawerDone`/保持 `peersLoading`)+ `_drawerPeerRetry` 1s 重拉; `_switchDrawerTarget` 末尾置 `_drawerPeerGrace = true`(必须在 `_loadDrawerTab` 之后); `_stopDrawerPoll` 收口 `clearTimeout(this._drawerPeerRetry)` + 清标记; 新增 `_drawerPeerCount` 判空 helper。
- **测试**: `tests/test_webui_static_dom_panel.py` —— 新增 `test_drawer_peers_switch_empty_grace_wiring`; `test_drawer_peers_speed_keys_normalized` 落袋断言形改 `this.drawer.peers = norm;`(原意不变); 头部计划清单同步。`e2e/drawer-peers.spec.mjs` —— 新增 `@fast` 用例「切换种子首个空 peers 响应不得闪现空态」+ 头注覆盖说明。
- **知识库回写**: 坑档 `pitfalls/web-ui/drawer-switch-flicker.md`「复发 +1(第九次)」(数据落袋语义面 + 探针纪律⑥「恒非空桩本身是盲区制造机」) + 头部摘要/触发词; `modules/webui-static-contract.md` 抽屉数据层条补宽限事实; activeContext 切片 `26-10-13-0027-webui-drawer-switch-empty-grace.md`。

## 已知偏差 / 移交

- **trackers / files 未纳入宽限**(范围守恒: 用户报的是用户页)。二者有同族隐患(换目标后首拍空同样会闪现空态), 属既有缺陷面 —— 若复发按同法处理(未入池, 未认领)。
- `drawer-peers-sticky-flush` atlas › dt07 亚像素 flaky(1.399px vs 1px 容差): 与本波无关的既有几何抖动, 复跑绿; 未入池。
- 口径取舍: 「空响应 = 未就绪 vs 真没有」前端无法区分, 本方案取「宁可多等 1s 也不误报空」—— 真没对端的种子会先显示 1s 加载态再落空态(已记坑档)。
- 存量债务(同前, 未动): `modules/webui-static-contract.md` 超 evergreen cap(本波 +~250 字符); activeContext 切片数债务(> 70, 本波 +1)。
- 未 commit / 未 push(用户未发「提交」指令)。

> ⚠ **已被取代(2026-10-13)**: 本条描述的「宽限 + 重拉」诊断与机制已被用户否掉并整体回退
> (「种子的常态就是没有对端」—— 空响应不是"未就绪"); 诊断更正与最终修法见
> `26-10-13-0148-webui-drawer-switch-no-flash.md` 与坑档 `drawer-switch-flicker.md` 第九次条目。
