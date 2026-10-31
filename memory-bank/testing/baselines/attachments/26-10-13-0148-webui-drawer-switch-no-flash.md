# 3167 —— 抽屉三列表切换种子「闪空态/闪加载」: 软切换窗口抑制列表 loading 门(第九次复发定案)

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/activeContext/26-10-13-0027-webui-drawer-switch-empty-grace.md,memory-bank/testing/baselines/26-10-13-0054-webui-drawer-switch-empty-grace.md

> 摘要: 用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」, 续报定调「种子的常态就是没有对端」「我的目标是本地毫秒级的响应」。**真根因(逐帧实测定案)**: 软切换(FX-29)保留的是**上一个目标的已落袋结果**, 而**空列表(没有对端/没有 tracker)是种子的常态** —— 这份"已落袋的空"同样在屏上; 但三个列表 fetcher 一律置 `loading`, 模板门 `loading && !行数` 就把这份既有的空态顶掉一帧换成「正在加载…」, 数据(空)回来再换回 ⇒ 用户看到「『暂无已连接用户』闪烁」。临时探针(恒空桩 + 逐帧 rAF, 已删)实测序列 = **`E→L→E`**(E=空态 / L=加载门) —— 与本坑**第三次复发**(流量图 `qbCurLoading && !qbCurPoints.length`)是同一判据缺陷族。**修法**: `drawer_store.js` 新增 `_drawerListLoadingOn(silent)` = `!silent && !this._drawerSoftSwitch`, 三列表 fetcher 的 loading 置位一律改走它 —— 换目标窗口内**不置**列表 loading 门(屏上那份旧结果含空, 是归属上一目标的已确认状态), 「还没到新的」由 FX-29 遮罩(160ms 延迟点亮)表达。**本条取代前两版宽限方案**(首版 1s 重拉曾进 `3c1ef168`; 第二版毫秒级重拉 + 后端 `keep` 未上线即被回退)。
> 基线时间: 2026-10-13 01:48

上一基线：memory-bank/testing/baselines/26-10-13-0054-webui-drawer-switch-empty-grace.md(已取代)

## 验收数字

- `test.full`: **3167 passed + 4 skipped** / `TOTAL 16718 158 5688 139 99%`(与 `3c1ef168` 同计数 —— 本波**回退**后端 `keep` 与其守阵(-1)、**改造**静态守阵(等量), 净零)。
- e2e(全量 `dev.e2e`): **205 passed + 10 skipped + 1 failed**(6.6m)。唯一失败 = `delta-sync.spec.mjs` atlas「lastRid 置空后下一轮为全量」轮询时序用例(poll 8s 超时) —— **既发 flaky**, 单独复跑 **8/8 绿**, 与抽屉无关(本波只动抽屉数据层)。
- e2e(新 spec `drawer-switch-no-flash` 单跑): **6 passed / 0 failed**(用户/Tracker/内容 × prism+atlas)。
- 红验闭环: 禁用门抑制(`_drawerListLoadingOn` 回退成 `!silent`) ⇒ e2e 三页签 × 双皮肤 **6/6 全红**, 逐条命中「正在加载…」(即用户报障); 还原即绿。
- 复现探针(临时, 未进仓库): 恒空桩下软切换逐帧序列 `E→L→E`(定性根因; 探针已删)。

## 本波改动面

- **前端**(`src/auto_qb/webui/static/shared/drawer_store.js`): 新增 `_drawerListLoadingOn(silent)`(门抑制单点); 三 fetcher 的 loading 置位改走它; `_switchDrawerTarget` 于 `_loadDrawerTab` **之前**置 `_drawerSoftSwitch = true`; `_stopDrawerPoll` 加"不得清该标记"的显式说明与注释; `_drawerSwitchEnd` 清标记。**删除**上一轮新增的 `_drawerGraceHold` / `_drawerGrace` / `_drawerGraceRetry` / `_DRAWER_GRACE_DELAYS` / `_drawerPeerCount` 及三 fetcher 的 `deferred` 分支。
- **后端**: 上轮为"重拉"配套的 `RoCache`/`cached_read` `keep` 判据与三端点 `keep=` —— **已整体撤销**(`git checkout` 回滚), 现无动机。
- **测试**: `tests/test_webui_static_dom_panel.py` 守阵改为 `test_drawer_list_switch_no_loading_flash_wiring`(门抑制判据 + 三 fetcher 接入 + 置位在 `_loadDrawerTab` **之前** + `_stopDrawerPoll` 不清标记 + `_drawerSwitchEnd` 清标记 + 旧延迟重拉机制不得回潮); `test_web_seed_center.py` 的 `keep` 守阵撤销; e2e 以 `drawer-switch-no-flash.spec.mjs` 取代 `drawer-switch-empty-grace.spec.mjs`(恒空桩 + 逐帧: 空态全程在场 + 零「正在加载…」+ 切换目标零重试)。
- **知识库回写**: 坑档第九次条目**按真相重写**(病因/判别/处置/验证), 并留档"踩错的路"(没先证伪 / 拿工程直觉盖过领域事实 / 自愈把「闪」换成「等」)+ 探针纪律⑨⑩; `modules/webui-static-contract.md` 宽限描述改为门抑制; activeContext 切片重写; 两条历史基线(0027/0054)加"已被取代"标注。

## 已知偏差 / 移交

- 口径: 空列表**立即如实渲染**(没有对端/没有 tracker 是常态, 不延迟、不重试); 切换期间"还没到新的"由 FX-29 遮罩(160ms 延迟点亮)表达, 若 qB 真慢会亮遮罩药丸 —— 本地毫秒级响应下不可见。
- 唯一仍成立的副产品结论(留档未用于本坑): **后端对空响应的 1s 短路缓存会把"瞬时未就绪"放大成"持续未就绪"** —— 若将来确有"需重拉"的场景, 缓存必须放行。
- 存量债务(同前, 未动): `modules/webui-static-contract.md` 超 evergreen cap; activeContext 切片数债务(> 70)。
- 未 commit / 未 push(待用户指令)。
