# 基线切片 26-10-04-0405 — WEBUI qB 流量图三挂点并入底部详情抽屉

> 摘要: qb流量图弹层(全局/分组两个模态)并入底部详情抽屉, 与种子详情的「流量」页签共用同一段正文块与同一
> 拖拽高度; `.drawer-dock` 落点自种子视图上提为 app 级分片(dock.html, 三清单同步), 删除 `tpl/qb-traffic.html`;
> 图高改量宿主 `clientHeight` 并让 ResizeObserver 宽高双观察 -> 拖拽调高图实时跟随。去 `qbHistOpen`/`qbGroupOpen`
> 两个开合字段, Esc/escBusy/登出清理归一到 `closeDrawer` + `_qbTeardown`。三主题 CSS 成对改。

- 时间: 2026-10-04 04:05 (GMT+8); 会话起点 sync 至 71251d61(远端无更新, 基线即此)
- 分支: develop @ 71251d61(+ 本轮未提交改动: 3 主题 index.html/css ×3 / shared 下 auth.js · dialogs.js ·
  drawer.js · lifecycle.js · qb_traffic_chart.js · state.js · tpl/{drawer,statusbar,torrents}.html +
  新增 tpl/dock.html + 删除 tpl/qb-traffic.html / tests/test_web.py · test_web_shortcuts.py + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2423 passed + 3 skipped, 39.92s, 覆盖率 TOTAL 99%**(14416 语句 / 132 未覆盖 / 4820 分支 / 105 partial)
- 相对上基线(26-10-04-0308: 2423 passed + 3 skipped / 99%)**用例数持平** —— 本轮是改造既有守阵而非新增用例:
  `test_frontend_qb_traffic_chart_wiring` 整段重写(弹层 -> 抽屉形态: dock.html 分片登记 / 三挂点统一
  ref=qbChartHost / openDrawerTraffic 归一 / _qbTeardown 收口 / 三皮肤 `.drawer-body.is-traffic` 成对),
  `test_web_shortcuts.py` 两处模板断言随 aside 的 `:class` 扩写放宽(加 `,` 后缀), `test_web.py` 遮罩计数
  阈值 11 -> 9(qb-traffic.html 两个 modal-mask 随弹层删除)。
- 浏览器冒烟(非 pytest 覆盖面, `scripts/ui_harness.py` + Playwright): 三形态实测 —— 默认页(dock 高 0,
  列表/状态栏布局未坏) / 强制全局流量形态(抽屉 378px, 图 194px; `drawerHeightPx=620` 后抽屉 620px,
  图 436px = 高度跟随成立) / 种子详情「流量」页签(scope=torrent, body 挂 `is-traffic`, 空态正常); 全程零 pageerror。
- 未验证面: 真机(真实 qB 数据 / 24h↔30d 换窗 / 低频轮询续拉 / 组右键入口)待用户走查; 原「弹窗滚轮穿透」
  报告(26-10-04-0128)按 12 个遮罩模态统计, 本轮删 2 个 -> 实为 10, 该报告停在拍板未开工, 实施时一并核对。

> 补记 (2026-10-04 04:20, 提交轮): 会话起点 sync 至 71251d61 时远端无更新, 但**提交前远端已推进到 800ccba2**
> (另一 clone 的「移除 .modal-members 死类」, 同样改了 atlas/console `views.css`); 按 `my-commit-flow.sync`
> 的失败行配方 (stash -u -> sync -> stash pop) 合流后, 本改动**实际落在 800ccba2 之上**, 提交为 `659eada8`
> (已推 Gitee develop, ls-remote 核验一致)。合并处无冲突(两处 CSS 改动区段不同), 合并后复跑:
> **test.full 2423 passed + 3 skipped / 99% / 51.21s** —— 正文那条 39.92s 是同一轮更早的一次采样(两次均实测)。
