# 26-10-13-0027 WEBUI 抽屉三列表切换种子「闪空态 / 闪加载」修复(第九次复发)

> 摘要: 用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」, 续报定调「种子的常态就是没有对端」「我的目标是本地毫秒级的响应」。**真根因(逐帧实测定案)**: 软切换(FX-29)「保留旧数据撑几何 + 遮罩防串显」保留的是**上一个目标的已落袋结果**, 而**空列表(没有对端 / 没有 tracker)是种子的常态** —— 这份"已落袋的空"同样在屏上; 但三个列表 fetcher 一律置 `loading`, 模板门 `loading && !行数` 就把这份既有的空态顶掉一帧换成「正在加载…」, 数据(空)回来再换回 ⇒ 用户看到「『暂无已连接用户』闪烁」。临时探针(恒空桩 + 逐帧 rAF, 已删)实测序列 = **`E→L→E`**(E=空态 / L=加载门); 与本坑**第三次复发**(流量图 `qbCurLoading && !qbCurPoints.length`)是**同一判据缺陷族**。**修法**: `drawer_store.js` 新增 `_drawerListLoadingOn(silent)` = `!silent && !this._drawerSoftSwitch`, 三列表 fetcher 的 loading 置位一律改走它 —— 换目标窗口内**不置**列表 loading 门。!**首版走错路(留档)**: 曾误判为"空响应=未就绪"并加延迟重拉(还改了后端缓存), 被用户否掉(「切换后亮 1-2s 加载」) —— 错在没先证伪(复现的是注入空响应造出的另一条路径)、且拿"空=未就绪"的工程直觉盖过用户领域事实。

> 最后活动: 2026-10-13 01:48

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/testing/baselines/26-10-13-0148-webui-drawer-switch-no-flash.md

## 背景

用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」(与 2026-10-07 那次同现象, 是本坑**第九次**
复发)。前八次都在**锚契约面 / 渲染驱动面**; 本次在**渲染门的判据面**。

## 根因(实测复现, 非推理)

1. `_switchDrawerTarget` 保留旧列表数据(软切换本意)✓ —— 屏上是**上一个目标的已落袋结果**,
   而**空列表是种子的常态**(用户明确: 没有对端/没有 tracker 是常态)。
2. 三个列表 fetcher 在 fetcher 开头同步置 `loading = true`。
3. 模板门 `loading && !行数`(drawer-tabs.html 三处; 变体 04–12 同判据)把**既有的空态**顶掉,
   换成「正在加载…」。
4. 响应(空)回来 ⇒ `loading = false` ⇒ 空态换回 ⇒ 用户看到空文案闪。
   探针实测(恒空桩, 逐帧 rAF, 已删): `E → L → E`。

**为什么逃逸**: ①桩服务对每个种子**恒有**数据、**从不返回空**; ②e2e 全部 drawer spec 只
`dblclick nth=0` **单次打开**(无"切换种子"用例) ⇒ 「切换种子 + 常态空列表」这条真机路径
pytest 与 e2e **双零覆盖**。

## 修复(三列表共用单点)

- `src/auto_qb/webui/static/shared/drawer_store.js`:
  - 新增 `_drawerListLoadingOn(silent)` = `!silent && !this._drawerSoftSwitch`(门抑制单点);
    `_fetchDrawerPeers|Trackers|Files` 的 loading 置位一律改走它。
  - `_switchDrawerTarget` 于 `_loadDrawerTab` **之前**置 `this._drawerSoftSwitch = true`
    (三 fetcher 在 `_loadDrawerTab` 内、await 之前**同步**读它)。
  - `_stopDrawerPoll` **不得**清该标记(它在 `_loadDrawerTab→_startDrawerPoll` 途中被调用 ——
    若在此清, 等于置前失效; 已在方法内写明并加守阵负钉)。
  - `_drawerSwitchEnd`(落定/打断)清标记。
  - 冷启动 `openTorrentDrawer` 不走该门(无旧结果可保留, loading 由该方法按 initialTab 同帧置位)。
  - **删除**上一轮的 `_drawerGraceHold` / `_drawerGrace` / `_drawerGraceRetry` / `_DRAWER_GRACE_DELAYS`
    / `_drawerPeerCount`(= 首版误判的延迟重拉机制)。
- `e2e/drawer-switch-no-flash.spec.mjs`(新增, 取代 `drawer-switch-empty-grace.spec.mjs`): 三页签 ×
  双皮肤; route 让本页签**对所有种子恒返回空**(常态无数据), 逐帧 rAF 采样: ①空态全程在场;
  ②零「正在加载…」; ③切换目标**零重试**请求(钉住"不准把空当未就绪去重拉")。
- `tests/test_webui_static_dom_panel.py`: 守阵改为 `test_drawer_list_switch_no_loading_flash_wiring`
  (门抑制判据 + 三 fetcher 接入 + 置位在 `_loadDrawerTab` **之前** + `_stopDrawerPoll` 不清标记 +
  `_drawerSwitchEnd` 清标记 + 旧延迟重拉机制不得回潮)。
- 后端上轮的 `keep`(空结果不入缓存)改动**已撤销**(其动机是那条被否掉的重拉, 现无需要)。

## 验证

| 项 | 结果 |
|---|---|
| 红验(禁用门抑制) | e2e 三页签 × 双皮肤 **6/6 全红**, 逐条命中「正在加载…」(即用户报障); 还原即绿 |
| e2e(新 spec 单跑) | 6/6 绿(prism+atlas) |
| 探针(复现) | 恒空桩下软切换序列 `E→L→E`(定性根因) |
| 全量 e2e / test.full | 见基线切片(`commands run kb.baseline`) |

## 遗留 / 范围外

- 本坑**第三次复发**(流量图 loading 门判据)与本次同族 —— 本坑第一条判别「loading 门判据要穷举取值域」
  再获实证; 该纪律已写进坑档第九次条目。
- 上一轮的「宽限 + 重拉」两版**均未最终上线**(首版 1s 版虽进过 `3c1ef168` 提交, 本波已回退);
  其唯一仍成立的副产品结论: **后端对空响应的 1s 短路缓存会把"瞬时未就绪"放大成"持续未就绪"**
  (若将来确有需要重拉的场景, 缓存必须放行) —— 已留档坑档, 未用于本坑。
- 存量债务(未动): `modules/webui-static-contract.md` 超 evergreen cap; activeContext 切片数债务(> 70)。
