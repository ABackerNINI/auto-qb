# 辅种页/追剧页支持种子详情面板 (实施轮 · 已闭环)

> 摘要: 用户命题「WEBUI 辅种页/追剧页需要支持种子详情面板」。诊断: 面板被 `drawerVisible` 与 `openTorrentDrawer` 两处守卫锁在种子页(`viewMode === "torrents"`), 而辅种页/追剧页成员行的右键**早已**复用单种子菜单(`openMemberMenu` 设 `menu.hash`, ctx 的 `menu.hash` 分支含「详细信息」)—— 菜单项渲染、hash 正确, 点下去却被守卫**静默吞掉**(不报错不提示)。计划 [26-10-08-1217](../plans/26-10-08-1217-plan-webui-drawer-groups-shows.html)(Status: **Done**), S1–S5 全部落地。
>
> 最后活动: 2026-10-09 07:55

**Refs:** memory-bank/plans/26-10-08-1217-plan-webui-drawer-groups-shows.html

## 本轮完成 (实施轮)

- **S1 槽位与可见性**: `drawerVisible` 与 `openTorrentDrawer` 的视图守卫解除, 一律只挡 `page !== "groups"`; `.torrents-dock` 几何钩子由「仅种子视图」改为三视图恒挂(类名沿用, 三套 CSS 的 `.torrents-dock > .group-table` 选择器未动)。
- **S2 双击入口**: groups.html / shows.html 两处成员行补 `@dblclick="openTorrentDrawer(m.hash)"`。
- **S3 键盘链**: `_kbRows` 纳入展开的成员行(`kind: "torrent"`, 序 = 父行紧邻其子行), 兑现原注释的「成员行 vNext」; `_kbDrawerTab` 守卫放宽(三视图 Alt+1~5 可用)。
- **S4 跟随/peek/轮询**: `_kbFollowDrawer` / `_drawerPeekTarget` / 5s 轮询 tick / `qb_traffic_chart.js` 的 `torrent` 挂点 `active` 四处守卫一并只挡主内容页; `onMemberClick` 补上与 `onTorrentClick` 同款的跟随·peek 分流(此前成员行点击对开着的面板毫无反应)。
- **S5 收尾**: 新增守阵 `test_frontend_drawer_groups_shows_views` + e2e `drawer-groups-shows.spec.mjs`(双皮肤 × 3 场景); 契约回写 `modules/webui-static-contract.md` 新增「详情面板三视图共用」条。实测数字见基线 [26-10-09-0755](../testing/baselines/26-10-09-0755-webui-drawer-groups-shows.md)(`commands run kb.baseline`)。

## 三处与预估不同的实况(下轮别再踩)

1. **右键入口无需新增** —— 成员行右键本就走单种子菜单, 缺的只是守卫。先读 `menu.js::openMemberMenu` 再动手可省一半工作量。
2. **键盘链取 hash 必须经 `memberHashesOf` 单点** —— `sortedMembers(e.members)` 后直读 `m.hash` 会被 `test_frontend_static_bundle_health` 的集成员守阵判红(该守阵分不清「逐个取 hash」与「把对象当 hash 传」)。改 `memberHashesOf(sortedMembers(...))` 后既守规矩又保住行序, **不要去放宽那条守阵**。
3. **e2e 点行要点名称格** —— 行中心多半落在站点/标签挂件上, 挂件带 `@click.stop` 走筛选、不展开行(首跑 4 条失败全因这个, 是手势问题非产品缺陷)。

## 为什么这两条没在改代码前命中(已记坑的复发)

两条都**已立档**, 本轮仍各撞一次 —— 不是没路由, 是路由到了但没读到关键那一句:

- `pitfalls/web-ui/contract-api.md`「追剧视图 members 是双形态」原本只写「必须先 `memberHashesOf()` 归一」,
  没写「守阵按行匹配、安全写法也会被判红」。读到的是"要归一", 缺的是"按行匹配会误伤" ⇒ 撞上后第一反应
  是"这守阵太粗该放宽", 差点改错方向。**已补进该条 + 复发 1。**
- `pitfalls/testing/smoke.md`「行内可交互后代会吞修饰键点击」原本只针对 Ctrl+click, 没写"普通点击/双击
  同样被吞、且 `force: true` 只跳过 actionability 不改落点坐标"。**已补进该条 + 复发 2**(含集行名称格是
  `.ep-name` 不是 `.g-name`)。

⇒ 两条都**没有新建坑档文件**(一处事实一处记, 另起文件必然漂移)。

## 待办 / 移交

- 无遗留。计划已 Done, 未立任务档案(单会话、主题集中在抽屉守卫族, 未达立档阈值)。
