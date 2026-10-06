# 2689 —— WebUI 重按 Ctrl+\ 闪烁修复收尾 (develop @ a5577646, 源码小修轮)

> 摘要: 修复「ctrl+\ 打开 qb 全局流量图, 再按一次会闪烁」—— `openDrawerTraffic` 缺同目标幂等
> 短路, 重按入口把收图销毁+抽屉重建+首拉各闪一遍; 修法 = 头部加同目标短路(分组比 `qbGroupKey`,
> 页面归一留在短路前), 坑档 drawer-switch-flicker 复发 +1(第四次, 入口重入语义), 守阵补第 5 锚
> (test_frontend_qb_traffic_drawer_page_guard)。改动: qb_traffic_chart.js + test_web.py + 坑档/切片。
> 基线时间: 2026-10-07 02:38

**Refs:** memory-bank/activeContext/26-10-07-0241-webui-ctrl-backslash-idempotent.md

- 分支: develop @ **a5577646**(开工 sync 已在最新, 本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2689 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句 / 163 未覆盖 /
  5472 分支 / 143 partial)**; pytest 自报 **34.43s**。
- 相对上一条 [26-10-07-0115](26-10-07-0115-webui-perf-issues-recheck.md)
  (2686 + 4 / 15823 / 163 / 5472 / 143): passed **+3** 与语句 15823→**16021**(+198)均来自
  开工同步已在库的远端提交(详情面板模板重构 S2-S7 一族, 2ca5fe66..a5577646); 本轮改动
  (qb_traffic_chart.js 静态 JS 不进 `--cov=src` 统计, test_web.py 只加锚不动收集面)
  对覆盖四项**零增量**; 未覆盖 / 分支 / partial 三项与 0115 逐位相同, 覆盖率 99% 持平。
