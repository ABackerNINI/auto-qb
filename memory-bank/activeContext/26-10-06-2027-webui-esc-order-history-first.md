# webui-esc-order-history-first — Esc 退栈顺序修正(历史弹层先于抽屉)

> 摘要: 用户报「qB 流量图与历史流量图同开时 Esc 应先关历史流量图」。根因 = lifecycle.js Esc 退栈链把抽屉分支排在历史弹层之前, 与视觉层叠(遮罩 130 > 抽屉 80)相反。已改链序 + 加顺序守阵 + 落坑档。
> 触发: ESC, 退栈顺序, Esc 关错层, 历史流量, qB 口径流量图, 两图同开, drawerVisible, historyOpen, overlays
> 最后活动: 2026-10-06 20:27

- **2026-10-06 20:27 实施完成(待提交)**: 用户报「WEBUI ESC 顺序错误: qB 流量图与历史流量图同时存在时, esc 应该先触发历史流量图」。根因 = `lifecycle.js` Esc 退栈链 `drawerVisible` 分支排在 `historyOpen` 之前; 而历史流量是 `.modal-mask` 遮罩层(z-index 130), 盖在停靠抽屉(z-index 80)之上 —— 第一次 Esc 穿过遮罩关了**底下被盖住**的抽屉, 与用户可见层叠相反。改动: ①`lifecycle.js` 把 `historyOpen` 分支上移到 `drawerVisible` 之前(链序 = 视觉层叠顺序), 更新文件头与链首注释; ②`tests/test_web.py::test_frontend_qb_traffic_chart_wiring` 加 `hist_at < drawer_at` 的**顺序**断言(原先只断言分支存在, 漏得掉顺序错) + 同步文件头「## 测试计划」; ③坑档 `pitfalls/web-ui/overlays.md` 新增「Esc 退栈顺序 = 视觉层叠顺序」一节(补三行头触发词)。`escBusy`(dialogs.js)是顺序无关布尔, 无需改。test.full **2682 passed + 4 skipped / 29.82s**(TMPDIR 指向 C 盘临时根跑, R 盘临时目录被污染会假红, 见 pitfalls/testing/tmpdir)。不满足立档阈值(单会话、2 文件 + 1 坑档, 无任务档案)。
