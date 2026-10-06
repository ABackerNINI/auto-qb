# 2689 —— WebUI 流量图开着时 Alt+1~5 详情面板修复收尾 (develop @ 651bfab9, 源码小修轮)

> 摘要: 修复「打开 qb 全局流量图后, Alt+1~5 快捷键打不出详情面板且触发 "tracker/peer 列表获取失败:
> Not Found"」—— `_kbDrawerTab` 开态判据只看 `drawer.open`, 流量形态抽屉(hash 恒空)走切页签
> 分支把空 hash 打进 `/api/torrents//trackers` 等端点; 修法 = 开态判据收紧为
> `drawer.open && drawer.kind === "seed"`, 流量形态视同关态走 `openTorrentDrawer` 换形打开。
> 改动: shortcuts.js + test_web_shortcuts.py(锚点改形) + 切片。
> 基线时间: 2026-10-07 02:51

**Refs:** memory-bank/activeContext/26-10-07-0251-webui-drawer-tab-traffic-form-guard.md

- 分支: develop @ **651bfab9**(开工 sync 已在最新, 本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2689 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句 / 163 未覆盖 /
  5472 分支 / 143 partial)**; pytest 自报 **33.75s**。
- 相对上一条 [26-10-07-0241](26-10-07-0241-webui-ctrl-backslash-idempotent.md)
  (2689 + 4 / 16021 / 163 / 5472 / 143): 四项覆盖指标与 passed 数**逐位相同零增量** —— 本轮改动
  (shortcuts.js 静态 JS 不进 `--cov=src` 统计; test_web_shortcuts.py 只改锚不动收集面)不改变收集面;
  2689 中含两处改形的既有守阵与新增锚(均在原测试函数内, 不增测试数)。
