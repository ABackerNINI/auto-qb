# 重按 Ctrl+\ 流量图闪烁修复 — openDrawerTraffic 同目标幂等短路 (Done)

> 摘要: 用户报「WEBUI ctrl+\ 打开 qb 全局流量图, 再按 ctrl+\ 会闪烁」。根因 = `openDrawerTraffic` 无重入分支: 抽屉已开着同一流量图时重按入口把全量路径重走一遍 —— `_qbTeardown`(停轮询+销毁 uPlot 图) + 整体重建 `drawer` 对象 + `_qbLoad` 首拉, 收图/重建/首拉 loading 各闪一遍(稳定复现)。修法 = 在页面归一之后、全部副作用之前加同目标幂等短路(`drawer.open && kind === "traffic" && scope` 相同, 分组再比 `qbGroupKey`): 命中即返回(顺带收右键菜单、收起态重按 = 展开); 页面归一刻意留在短路前 —— 非主内容页重按仍先切页, 面板进场补拉由 watch(drawerVisible) 负责。命中既有坑档 [drawer-switch-flicker](../pitfalls/web-ui/drawer-switch-flicker.md)(同族第四次复发, 前三次都在数据/续拉渲染侧, 这次病灶在上游入口重入语义)→ 该条复发 +1 + 补「打开类入口必须问重入语义」判别, kb.index 重建。守阵: `test_web.py::test_frontend_qb_traffic_drawer_page_guard` 补第 5 锚(短路存在且先于 `_stopDrawerPoll` 副作用)。不满足立档阈值(单会话、1 处源文件小修, 无任务档案)。test.full **2689 passed + 4 skipped / 99% / 34.43s**(基线切片 26-10-07-0241)。
> 最后活动: 2026-10-07 02:41

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md

## 现状

- **修复完成**。改动面: `src/auto_qb/webui/static/shared/qb_traffic_chart.js`(openDrawerTraffic 短路 + 块注释口径) · `tests/test_web.py`(守阵第 5 锚 + docstring 补第 5 类) · 坑档 drawer-switch-flicker 复发行 + 摘要/触发词扩充 · 本切片 · 基线切片 · `kb.index` 重建生成物。
- 验证: `commands run test.quick` 2689 passed(两轮, 改码后与收尾各一); `commands run test.full` 2689 passed + 4 skipped / 99% / 34.43s。守阵锚点正则以改动后源码实文校验过。
- 未验证面 / 残留风险: 未做真机 Playwright 冒烟(需真实 qB); 判据为静态锚 + 逻辑推演 —— 短路命中路径不触碰轮询/图/数据, 理论零观感变化。分组入口重复点击同 key 同样受益。
- 判据沉淀: 「打开类入口要问重入同一目标会怎样 —— 已开着的东西再'打开'一次应当是零副作用, 不是重新表演一遍开动作」入坑档 drawer-switch-flicker 第四次复发行。
