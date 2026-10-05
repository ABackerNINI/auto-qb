# 流量图抽屉加页面守卫(修「全局流量图出现在设置页」)

> 摘要: 用户报「qb 全局流量图会错误地出现在设置页中」。根因 = 2026-10-04 三挂点并入底部抽屉时, `drawerVisible`
> 对流量形态**无条件为真**(口径「任意页可开」), 把**入口可达性**当成了**面板可见性** —— 落点上提 app 级解决的是
> "任意页都能触发", 而面板是 sticky 吸底元素, 在设置页会压住页面底部内容、看着像设置页自带的一块(即
> pitfalls/web-ui/dock-panel「停靠面板隐藏后轮询要随可见性收口」的复发, 复发 +1)。
> 本轮口径: **面板只在主内容页 (`page === "groups"`) 渲染**, 状态位 `drawer.open` 不随切页翻(回主内容页连数据与
> 窗口选择一起回来); 连带三处同原子面 —— ①三挂点 `active` 加同款 page 守卫(隐藏期不发请求) ②非主内容页触发入口
> (状态栏 / Ctrl+Backslash)先切回主内容页再开(否则"点了没反应") ③`watch(drawerVisible)` 退场销毁图 / 进场补拉重画
> (v-if 拆装换掉了 uPlot 宿主, 实例不自愈)+ Esc 两处名单改判 `drawerVisible`(看不见的面板不吃 Esc)。
> 验证: 新增守阵 `test_frontend_qb_traffic_drawer_page_guard`(四点逐个捋过 + 摘守卫红验), `tests/test_web.py` + `test_web_shortcuts.py` 全绿;
> test.quick 2637 passed + 4 skipped / 36.5s。
> 最后活动: 2026-10-06 03:30

**Refs:** [pitfalls/web-ui/dock-panel.md](../pitfalls/web-ui/dock-panel.md) ·
[progress/implemented-webui-history.md](../progress/implemented-webui-history.md) ·
[activeContext/26-10-04-0405](../activeContext/26-10-04-0405-webui-qb-traffic-drawer-merge.md)

## 现状

- **实施完成, 待用户提交**。改动面 6 文件(5 源码 + 测试 2 处同步):
  - `shared/drawer.js` — `drawerVisible` 加单行 `if (this.page !== "groups") return false;`, 位置在形态分支**之前**
    (按形态各写一遍 = 又一处会漏的分叉); 种子详情形态收敛为 `return this.viewMode === "torrents"`。
  - `shared/qb_traffic_chart.js` — `_QB_SCOPES.global/group.active` 加 `t.page === "groups"`(与 torrent 挂点同款);
    `openDrawerTraffic` 开头加页面归一 `if (this.page !== "groups") this.page = "groups";`;
    新增 `_qbReloadOnEnter(scope)`(进场补拉, 内含 `loading` 在途不叠加守卫 —— 防止打开路径的首发请求被 watcher 翻倍)。
  - `shared/state.js` — 新增 `watch(drawerVisible)`: 退场 `_qbChartDestroy(s)` / 进场 `_qbReloadOnEnter(s)`。
  - `shared/dialogs.js` + `shared/lifecycle.js` — Esc 两处名单 `drawer.open` → `drawerVisible`(同名单同步纪律)。
  - `shared/tpl/dock.html` — 注释订正: 落点 app 级 = 入口任意页可达, **不等于**面板任意页可见。
  - `tests/test_web.py::test_frontend_qb_traffic_drawer_page_guard`(新) + 既有 `test_frontend_qb_traffic_chart_wiring`
    两处 Esc 断言同步 + `tests/test_web_shortcuts.py::test_drawer_dock_keyboard_w2` Esc 断言同步。
- 关键取舍:
  - **保留状态 vs 关闭**: 选「面板 DOM 退场、状态保留」(= 种子详情形态既有语义, "切页再回原样"), 而不是切到设置页
    就 `closeDrawer()` —— 后者会丢用户选的窗口档位与抽屉高度, 且丢得悄无声息。
  - **入口主动切页**: 状态栏按钮与 Ctrl+Backslash 在设置页可达, 若只加面板守卫不改入口, 症状会退化成"点了没反应"。
    用户点图是想看图, 故由打开方法先切回主内容页(不是隐藏入口按钮)。
- 验证:
  - 守阵红验: 摘 `drawerVisible` 的 page 守卫 / 摘 active 的 page 判据 / 摘 `_qbReloadOnEnter` / 把 Esc 写回
    `drawer.open` → 逐条转红, 恢复转绿。
  - `commands run test.one -- tests/test_web.py tests/test_web_shortcuts.py -q` 全绿; `node --check` 五文件全过。
  - `commands run test.quick` **2637 passed + 4 skipped / 36.5s**。
- 未验证面 / 遗留: ①**真浏览器走查**——本 clone 缺 Playwright(`dev.harness` 跑不起来), 未能肉眼确认「设置页不再
  出现流量图 / 回主内容页图正常重建 / Esc 首响」; ②面板退场期数据会陈旧到什么程度取决于用户停留时长, 当前用
  「回页即补拉」兜住; ③`kb.active` 报的切片数债务(86 > 70)非本轮引入, 转告用户另开会话清理。
