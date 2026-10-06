# 抽屉 open 与 kind 是正交维度

> 摘要: 三挂点(全局/分组/单种流量图)并入抽屉后, `drawer.open`(开合)与 `drawer.kind`(形态: seed/traffic)是两个正交维度 —— 判"面板开着"不能代替判"面板是种子详情形态"。流量形态的抽屉 `hash` 恒空、`tab` 恒为 `general`、页签按钮不渲染种子四签: 只判 open 的入口会把空 hash 打进 `/api/torrents//<hash 为空的路径>` 拿 404, 或被 `tab === tab` 早退吃掉(按了没反应)。
> 触发: drawer.open, drawer.kind, 流量形态, 种子形态, 全局流量图, 分组流量图, Alt+1, Alt+5, 详情面板打不开, tracker 列表获取失败, peer 列表获取失败, Not Found, /api/torrents//trackers, 空 hash, 按了没反应, _kbDrawerTab, drawerTab

### 只判 `drawer.open` 的抽屉入口在流量形态下打出空 hash 请求

- **触发**: 抽屉承载多种形态(种子详情 / 全局流量图 / 分组流量图)后, 给"开面板做某事"类入口
  (快捷键双态、页签切换)写守卫时只判 `drawer.open`(2026-10-07 实测: 全局流量图开着按 Alt+2/3
  弹 "tracker/peer 列表获取失败: Not Found", Alt+1 无反应)。
- **判别**: 问一句"这个入口操作的是抽屉的**哪个形态**的数据" —— 流量形态的 `drawer.hash` 恒空、
  `tab` 恒为 `general`, 任何 hash 定向请求(`/api/torrents/{hash}/...`)或页签语义在该形态下都不成立。
  守卫写 `drawer.open` 单条件即嫌疑; 排查法: 打开流量形态后把每个抽屉入口快捷键按一遍,
  盯 network 面板里的 URL 有没有出现 `//`(空段)。
- **处置**: 操作抽屉内数据的入口, 开态判据一律写全 `drawer.open && drawer.kind === "seed"`
  (shortcuts.js `_kbDrawerTab` 单点已修); 流量形态开态视同关态落到解析目标 + `openTorrentDrawer(hash)`
  换形路径, 不要在入口里手工改流量形态抽屉的字段。UI 路径通常天然安全(形态头部模板各自独立),
  跨形态漏洞几乎只出在快捷键/程序化入口 —— 新增抽屉快捷键时必须覆盖"三种形态各自开着"的按键矩阵。
