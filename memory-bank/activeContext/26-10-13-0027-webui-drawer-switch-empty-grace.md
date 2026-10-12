# 26-10-13-0027 WEBUI 用户页切换种子空态闪现修复(第九次复发)

> 摘要: 用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」。前八次都在锚契约面/渲染驱动面, 本次病根在**数据落袋语义面**: 软切换(FX-29)的立命之本「保留旧数据撑几何 + 遮罩防串显, 数据全部到手才掀罩」中, 「到手」只判「响应回来了」—— **空响应同样算到手**: 它覆盖 `drawer.peers` 成 `{peers:{}}`(旧数据没了)并登记 `_drawerDone("peers")`(掀罩) ⇒ 渲染层判 `!list.length` ⇒ 一帧空态; 而真机换目标后 qB 对新种子的**首个** `/peers` 常瞬时为空(连接/状态未就绪) ⇒ 观感「表格 → 暂无已连接用户 →(下一拍 5s)表格」。复现(探针, 已清): route 让切换目标首拍 /peers 返空 + 80 对端真量级 ⇒ classic 与 07/08/09 全部复现(逐帧 `C80`→`E0`, ~180 空态帧); 恒非空对照 0 空态帧。**为什么逃逸**: 桩 `ui_harness._make_peers_response` 对每个种子恒灌 1~7 对端**从不返回空**, 且 e2e 全部用例只 `dblclick nth=0` **单次打开**(无"切换种子"用例)⇒「切换 + 首拍空」真机路径双零覆盖。修复(方案A, 3 文件): `drawer_store.js::_fetchDrawerPeers` 加宽限 —— 换目标窗口内首个空响应视为「未就绪」: 不落袋/不掀罩/1s 后快速重拉一次, 仍空才接受; 收口 `_stopDrawerPoll`。验证: 红验闭环(拆宽限 ⇒ e2e 新用例 150 帧空态红/还原即绿) + 新静态守阵 + e2e 新用例; 全量数字见 `commands run kb.baseline`。

> 最后活动: 2026-10-13 00:27

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/testing/baselines/26-10-13-0027-webui-drawer-switch-empty-grace.md

## 背景

用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」—— 与 2026-10-07 那次(切片
`26-10-07-0411-webui-drawer-peers-empty-loading`)同一现象, 但那次修的是 `openTorrentDrawer`
入口「已开面板换目标交棒软切换」, 本次病根在更下游的**数据落袋语义**, 第五次的修法拦不住。
这是本坑第九次复发(`pitfalls/web-ui/drawer-switch-flicker.md`)。

## 根因(实测复现, 非推理)

前八次都在**锚契约面**或**渲染驱动面**; 本次在**数据落袋语义面**:

1. `_switchDrawerTarget` 保留旧 `peers`(FX-29 本意)✓
2. 但 `_fetchDrawerPeers` 的落袋判据只有「响应回来了」—— **空响应也算**: 覆盖 `drawer.peers`
   成 `{peers:{}}`(旧数据被清)+ 登记 `_drawerDone("peers")`(待到集合清空 ⇒ 掀罩)
3. 渲染层判 `!list.length` ⇒ 一帧「暂无已连接用户」
4. 真机换目标后 qB 对新种子的**首个** `/peers` 常瞬时为空(连接/状态未就绪) ⇒ 用户看到
   「闪一下」; 下一拍(5s)真实对端到达再顶回表格

**复现证据**(临时探针, 跑完即删): 注入 80 对端真量级 + route 让切换目标**首拍** /peers 返空
—— classic / 07 / 08 / 09 **全部复现**(逐帧 rAF 采样 `C80`=80 行表格 → `E0`=空态, ~180 帧);
**恒非空对照**全部 0 空态帧(275 帧全 `C80`)。

**为什么前八次没修到 / e2e 漏网**(两条同时成立才逃逸): ①桩 `ui_harness.py::_make_peers_response`
对每个种子恒灌 1~7 个对端, **从不返回空**; ②e2e 全部 drawer spec 只 `dblclick nth=0` 单次打开
(唯一涉及软切换的 `drawer-bridge-stub.spec.mjs` 路径C 只断言"桥稳定存活", 不断言无空态)。

## 修复(方案A, 3 文件)

- `src/auto_qb/webui/static/shared/drawer_store.js`:
  - `_fetchDrawerPeers` 加**宽限分支**: 换目标窗口内(`_drawerPeerGrace`)首个**空**响应(`_drawerPeerCount(norm) === 0`)
    视为「未就绪」—— 不落袋(保留旧数据)、`deferred` 短路 finally(不 `_drawerDone`/不 `_dtNotify`/
    保持 `peersLoading`)、`setTimeout` 1s 后快速重拉一次; 重拉仍空才接受(宽限标记已清, 走正常落袋)
  - `_switchDrawerTarget` 结束处置 `this._drawerPeerGrace = true`(必须在 `_loadDrawerTab` **之后**
    —— 其内 `_startDrawerPoll→_stopDrawerPoll` 会清零)
  - `_stopDrawerPoll` 收口 `clearTimeout(this._drawerPeerRetry)` + 清宽限标记(换页签/换目标/关面板)
  - 新增 `_drawerPeerCount(resp)` 判空 helper(dict/数组双形态)
- `e2e/drawer-peers.spec.mjs`: 新增 `@fast` 用例「切换种子首个空 peers 响应不得闪现空态」
  (route 让切换目标首拍返空, 逐帧 rAF 采样空态, 断言 0 帧 + 重拉后表就位); 头注补覆盖说明
- `tests/test_webui_static_dom_panel.py`: 新增守阵 `test_drawer_peers_switch_empty_grace_wiring`
  (钉接线 + 「宽限标记必须在 _loadDrawerTab 之后」这一静默失效点 + timer 收口); 同步修正
  `test_drawer_peers_speed_keys_normalized` 的落袋断言形(`this.drawer.peers = norm;`, 原意不变)

## 验证

| 项 | 结果 |
|---|---|
| 红验(拆宽限) | e2e 新用例 **150 帧空态** ⇒ 红; 还原即绿(闭环) |
| 探针(复现) | classic/07/08/09 均 `C80`→`E0`; 恒非空对照 0 空态帧 |
| e2e(drawer-peers 全量) | 见基线切片 |
| 全量 e2e | 见基线切片 |
| test.full | 见基线切片(`commands run kb.baseline`) |

## 遗留 / 范围外

- **trackers/files 未纳入宽限**(范围守恒: 用户报的是用户页)。二者有同族隐患(换目标后首拍空同样
  会闪现空态), 但属既有缺陷面, 未在本轮动 —— 若复发再按同法处理。
- 「空响应 = 未就绪 vs 真没有」前端无法区分, 本方案取「宁可多等 1s 也不误报空」; 真没对端的种子
  会先显示 1s 加载态再落空态(可接受的取舍, 已记坑档)。
