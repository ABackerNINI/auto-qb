# 全局流量图开着时 Alt+1~5 打不出详情面板修复 — _kbDrawerTab 形态守卫 (Done)

> 摘要: 用户报「WEBUI 打开 qb 全局流量图时, 快捷键尝试打开详情面板触发 "tracker 列表获取失败: Not Found" / "peer 列表获取失败: Not Found", 且无法切到种子详情面板」。根因 = `shortcuts.js::_kbDrawerTab`(Alt+1~5 双态入口)的"开态"判据只看 `drawer.open`: 流量形态(全局/分组流量图, 26-10-05 三挂点并入抽屉)开着的抽屉 `hash` 恒空、`tab` 恒为 `general` —— Alt+1 落在 `drawerTab` 的 `tab === tab` 早退上(按了没反应, 即「无法切换到详情面板」), Alt+2/3 走 `drawerTab("trackers"/"peers")` 把**空 hash** 打进 `/api/torrents//trackers`、`/peers`(404 → 两条 toast; 流量形态头部不渲染种子页签, UI 路径无此问题, 唯一跨形态路径就是快捷键)。修法 = 开态判据收紧为 `drawer.open && drawer.kind === "seed"`, 流量形态视同关态落到既有"解析目标 + `drawerLastTab` 定位页签 + `openTorrentDrawer(hash)`"路径 —— `openTorrentDrawer` 整体重建抽屉为种子形态并落在请求的页签(含 Alt+5: 全局图开着按 Alt+5 = 换到该种子的流量页签)。守阵: `test_web_shortcuts.py` 双锚改形(开态判据锚 + 流量形态必须落到 `openTorrentDrawer` 锚)+ docstring 测试计划同步。不满足立档阈值(单会话、1 处源文件小修, 无任务档案)。test.full **2689 passed + 4 skipped / 99%**(基线切片 26-10-07-0251)。
> 最后活动: 2026-10-07 02:51

**Refs:** memory-bank/activeContext/26-10-07-0241-webui-ctrl-backslash-idempotent.md

## 现状

- **修复完成, 待提交**。改动面: `src/auto_qb/webui/static/shared/shortcuts.js`(_kbDrawerTab 开态判据 + 块注释口径) · `tests/test_web_shortcuts.py`(两处守阵锚点改形 + 新增流量形态锚 + docstring 测试计划同步) · 本切片 · 基线切片 · `kb.index` 重建生成物。
- 验证: `commands run test.quick` 2689 passed(两轮, 中途锚点改形失败修复后复跑全绿); `commands run test.full` 结果见基线切片。
- 未验证面 / 残留风险: 未做真机 Playwright 冒烟(需真实 qB); 判据为静态锚 + 逻辑推演 —— 流量形态开态下 Alt+1~5 现走与关态完全相同的 `openTorrentDrawer` 路径(该路径在流量图与详情面板互切场景已被 Enter/KeyI/双击长期使用)。
- 判据沉淀: 「`drawer.open` 为真不等于种子详情形态 —— 三挂点并入抽屉后 open(开合)与 kind(形态)是两个正交维度, 操作抽屉内数据(页签/页签数据/hash 定向请求)的入口必须连 kind 一起判」。
