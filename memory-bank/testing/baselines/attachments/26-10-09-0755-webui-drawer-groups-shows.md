# 2818 —— 辅种页/追剧页支持种子详情面板 (计划 26-10-08-1217)

> 摘要: 详情面板三视图一体化实施轮收尾基线。面板原先被 `drawerVisible` 与 `openTorrentDrawer` 两处守卫锁在种子页, 辅种页/追剧页成员行右键「详细信息」点了静默失效; 本轮解除六处同族视图守卫、成员行补双击入口、键盘光标链纳入成员行。
> 计划: memory-bank/plans/26-10-08-1217-plan-webui-drawer-groups-shows.html (Status: Done)
> 基线时间: 2026-10-09 07:55

**Refs:** memory-bank/plans/26-10-08-1217-plan-webui-drawer-groups-shows.html

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2818 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16479 语句 / 162 未覆盖 / 5696 分支 / 146 partial; 门槛 98% 达标)
- **耗时**: 35.97s(墙时 38.6s)
- **新增测试**: 1 个守阵函数(`test_frontend_drawer_groups_shows_views`,挂在 `tests/test_webui_static_dom_panel.py`)+ `e2e/drawer-groups-shows.spec.mjs` 6 条(双皮肤 × 3 场景, 真浏览器全绿 11.4s)。

## 本轮三处闸门插曲(都属"改了就得重跑生成物 / 措辞"类, 非功能缺陷)

1. `test_frontend_static_bundle_health` 判红: 键盘链里 `sortedMembers(e.members)` 后直读 `m.hash` 命中集成员守阵(该守阵分不清「逐个取 hash」与「把对象当 hash 传」)。改为 `memberHashesOf(sortedMembers(...))` —— 既走单点又保住行序, 不动守阵本身。
2. `test_docs_forms.py::test_docs_index_is_regenerated` + `test_memory_bank.py::test_gen_all_check_is_green` 判红: 计划 doc-status 改 Open→Done 后索引陈旧, `commands run kb.index` 重跑即绿。
3. e2e 首跑 4 条失败: 点击落在行中心的站点挂件上(挂件 `@click.stop` 走筛选, 不展开行)。改点名称格(`.g-name` / `.ep-name`)后 6 条全绿 —— 是测试手势问题, 非产品缺陷。

## 代码事实变更(需回写的口径)

- 六处守卫从「按视图分叉」收归「只挡主内容页 `page !== "groups"`」: `drawerVisible` / `openTorrentDrawer` / `_kbFollowDrawer` / `_drawerPeekTarget` / 5s 轮询 tick / `qb_traffic_chart.js` 的 `torrent` 挂点 `active`。
- `.torrents-dock` 几何钩子改为三视图恒挂(类名沿用, 三套 CSS 选择器未动)。
- `onMemberClick` 补上与 `onTorrentClick` 同款的跟随·peek 分流。
- `_kbRows` 纳入展开的成员行(`kind: "torrent"`, 序 = 父行紧邻其子行), 兑现原注释的「成员行 vNext」。
- 契约回写: `memory-bank/modules/webui-static-contract.md` 新增「详情面板三视图共用」条。
