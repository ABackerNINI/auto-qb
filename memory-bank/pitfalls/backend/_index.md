# backend — 后端 / qB / 平台

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 高风险业务操作的防护、qB API 与数据层契约、并发与状态机约束、平台 / 文件系统差异。
> **触发**: 后端, qB, qbapi, store, 主循环, 规则, 并发, 平台, Windows, Linux, 磁盘

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [behavior-core.md](behavior-core.md) | 后端一批"看着像 bug 其实是特性"的行为 —— 改之前先确认它是不是有意设计。 | 改规则, 改主循环, 改归组, 改缺文件扫描, 改限速, 改状态持久化, 改 web 服务生命周期 |
| [concurrency.md](concurrency.md) | 七条线程 / 状态机硬约束, 违反即引入难以复现的 bug。 | 加线程, 改队列, 改 state_file, 改校验流程, 视图组装, QbApi 写方法, 阻塞等待, 关停, stop, join |
| [high-risk-ops.md](high-risk-ops.md) | 代码里已有防护的高风险动作 —— 改动时**不得削弱**这些防护; 删种重加、强制汇报、限速覆盖都属于这一类。 | 跳检, reannounce, qB 版本兼容, 删除种子, 限速, or 默认值, 死防御, 状态观测 |
| [page-scraping.md](page-scraping.md) | 从 HTML 里抽一段小数字 / 小文本时, 不锤定结构的正则会匹配到页面上别处的同类文本 —— 结果**看着合法但值是错的**, 且不报错。 | 爬页面, 抓页面, 解析 HTML, 正则提取, 页脚区间, 分页判据, HR 统计页, 站点改版, 数字提取 |
| [platform-fs.md](platform-fs.md) | Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。 | 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, CRLF, OEM 码页, PATH, MSYS, Git Bash, HTTPServer, 端口被占, SO_REUSEADDR, allow_reuse_address, getfqdn |
| [qb-api.md](qb-api.md) | qB 版本差异、`sync/maindata` 增量语义、`torrents/add` 的响应形态与选项缺省语义、`TorrentRecord` 的唯一所有权 —— 改数据层前必读。 | 改 qbapi, 改 store, 改 TorrentRecord, 改 apply_sync, 加种子字段, 全局限速, qB 状态, 添加种子, torrents/add, 添加后开始, stopped, autoTMM, 自动种子管理, 添加选项, optional 缺省, 添加回执 |
| [web-package-split.md](web-package-split.md) | web.py → web/ 包拆分(plan 26-09-22-1857)实打实撞出来的四条 —— FastAPI 懒解析路由、包内 logger 命名、__file__ 基准降级、生成脚本转义陷阱。 | 拆 web/ 包, 改 factory, include_router, app.routes, getLogger, __file__, 生成脚本, 金清单守阵 |
