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
| [cold-start-view-gap.md](cold-start-view-gap.md) | 数据/结论已经写进磁盘或内存, 但**广播/发布的时机**排在一个长达数小时的任务之后 —— | 重启后功能像没生效, 视图, 发布, publish, 广播, 冷启动, 判定真空期, 回落本地, 第一波, 长任务, 取数波 |
| [concurrency.md](concurrency.md) | 七条线程 / 状态机硬约束, 违反即引入难以复现的 bug。 | 加线程, 改队列, 改 state_file, 改校验流程, 视图组装, QbApi 写方法, 阻塞等待, 关停, stop, join |
| [ctypes-x64-argtypes.md](ctypes-x64-argtypes.md) | 用 `ctypes.windll.user32.XXX(...)` 直调 Windows API 时**不声明 argtypes/restype**, 参数按 32 位 int 传, 而 `HWND` / `HWND_TOPMOST` 这类"指针宽度"参数的高 32 位是寄存器残留值 —— 调用**返回失败却 GetLastError 为 0**, 且是否翻车取决于残留值 ⇒ 表现为"有概率失效"。2026-09-30 实测: `SetWindowPos(hwnd, HWND_TOPMOST, ...)` 同一窗口同一时刻, 未绑签名 ret=0 且 Z 序纹丝不动, 绑了签名 ret=1 立刻抬到顶层。 | ctypes, windll, WinDLL, argtypes, restype, 静默失败, GetLastError 为 0, x64, 传参, HWND, 指针宽度, 寄存器残留, 有概率, SetWindowPos, SetForegroundWindow, GetClassNameW, GetWindowTextW, Shell API, 封装注册键 |
| [explorer-foreground.md](explorer-foreground.md) | 后台进程经 `SHOpenFolderAndSelectItems` / `os.startfile` 弹资源管理器时, 新窗口**有概率被压在当前前台窗口后面** —— Windows 前台锁不允许后台进程抢前台; 必须打开后找回窗口、抬 Z 序, 再尽力争取焦点。⚠ 2026-09-30 二次报障查出**真根因另有其人**: 置前链路里所有 `ctypes.windll.user32.*` 调用都没绑 `argtypes`, HWND 按 32 位传 → **返回 0 且 GetLastError 为 0**的随机失效 —— 见 [ctypes-x64-argtypes.md](ctypes-x64-argtypes.md)。 | 打开目标文件夹, open-path, open_path, 资源管理器, explorer, 不弹到顶层, 不置前, 后台窗口, 前台锁, foreground, SetForegroundWindow, AttachThreadInput, SwitchToThisWindow, SetWindowPos, TOPMOST, argtypes, 托盘菜单, 弹窗在后面, 有概率 |
| [format-driven-parse.md](format-driven-parse.md) | 解析"按 format 渲染出来的文本"(日志行首当其冲)时, 把字段的**书写形状**写死成字面量 —— 默认配置下侥幸能跑, 用户换一种 format 就**静默失效**; 过滤类失效的表现是"恒空", 与"确实没有"完全同形。 | 日志过滤, 按等级, 日志行解析, levelname, 日志格式, format, 正则提取, 文本解析, 恒空, 结果为空 |
| [fs-pathmap-tristate.md](fs-pathmap-tristate.md) | 文件访问层(2026-09-27 审查轮)踩出的两条 —— ①casefold 折叠空间匹配后回原串切片, | casefold, 大小写无关, 前缀匹配, 路径映射, path_map, 切片, 变长折叠, UNDETERMINED, |
| [fuzzy-match-noise.md](fuzzy-match-noise.md) | 用「够长的连续重合段」判两个发布名是否同一内容时, 若不先把分辨率 / 来源 / 编码 / 音轨这些 | 粗配, 相似度, 重合段, 名称匹配, fuzzy, 阈值 K, 假重合, 假阳性, 质量标签, 判据收紧, 白烧配额, 下载触发器 |
| [high-risk-ops.md](high-risk-ops.md) | 代码里已有防护的高风险动作 —— 改动时**不得削弱**这些防护; 删种重加、强制汇报、限速覆盖都属于这一类。 | 跳检, reannounce, qB 版本兼容, 删除种子, 限速, or 默认值, 死防御, 状态观测 |
| [hot-reload-held-config.md](hot-reload-held-config.md) | 影响分级标 L0 只保证「新配置对象已被替换」; 若消费方(服务/线程)构造时把配置**按值**拷走, | 加配置键, 定热重载级别, impact, L0, 热重载, apply, 按值持有, 站点接入, 服务重建 |
| [page-scraping.md](page-scraping.md) | 从 HTML 里抽一段小数字 / 小文本时, 不锤定结构的正则会匹配到页面上别处的同类文本 —— 结果**看着合法但值是错的**, 且不报错。 | 爬页面, 抓页面, 解析 HTML, 正则提取, 页脚区间, 分页判据, HR 统计页, 站点改版, 数字提取 |
| [platform-fs.md](platform-fs.md) | Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。 | 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, CRLF, OEM 码页, PATH, MSYS, Git Bash, HTTPServer, 端口被占, SO_REUSEADDR, allow_reuse_address, getfqdn |
| [qb-api.md](qb-api.md) | qB 版本差异、`sync/maindata` 增量语义、`torrents/add` 的响应形态与选项缺省语义、`TorrentRecord` 的唯一所有权 —— 改数据层前必读。 | 改 qbapi, 改 store, 改 TorrentRecord, 改 apply_sync, 加种子字段, 全局限速, qB 状态, 添加种子, torrents/add, 添加后开始, stopped, autoTMM, 自动种子管理, 添加选项, optional 缺省, 添加回执 |
| [release-record-baseline.md](release-record-baseline.md) | 一份凭据(放行/授权/豁免记录)若靠「与签发时的状态快照比对」来判断是否失效, 快照就是 | 放行记录, verified, 签发, 锚点, 快照, 漂移, drift, 永续有效, 永久记录, 凭据, 三处写入点, 签发即作废 |
| [schema-stamp-writeback.md](schema-stamp-writeback.md) | 带 schema 版本链的写回(writer)若「校验走迁移后的临时副本、落盘写原始提交树 + 新版章」, | schema 迁移, 版本链, 写回, writer, 盖章, schema_version, WebUI 保存, read_tree, |
| [suppress-request-vs-live-flag.md](suppress-request-vs-live-flag.md) | EventBus suppress 曾把「重放保护请求」与「事件分派相位的抑制」混在一个 `_suppressed` 字段上 —— 注释宣称"窗口只盖两个事件相位", 实现却在置位点到下轮轮首之间吞掉一切 emit, 连续两次 L2 重建时第二次的 queue_rebuilt 静默丢失(issue 26-10-01-0750)。教训: 状态字段一符两义时注释只能描述其中一个语义, 判别与修复都以实现为准, 然后拆字段。 | 改 EventBus, 改 suppress, 抑制窗口, 重建窗口内 emit, 相位丢失, 事件被吞, queue_rebuilt, 重放保护, 一符两义, 注释与实现不符, set_suppressed, take_suppressed |
| [unreachable-wait.md](unreachable-wait.md) | 与外部通道(浏览器扩展 / 本机端点 / 代理 / 设备)打交道时, 若「对面能不能收到」在本机 | 等待回传, 超时, request_timeout, 白等, 端点未监听, 端口未绑定, 快速失败, fail-fast, 假线索, 排查方向, 通道不可用, listening |
| [web-package-split.md](web-package-split.md) | web.py → web/ 包拆分(plan 26-09-22-1857)实打实撞出来的四条 —— FastAPI 懒解析路由、包内 logger 命名、__file__ 基准降级、生成脚本转义陷阱。 | 拆 web/ 包, 改 factory, include_router, app.routes, getLogger, __file__, 生成脚本, 金清单守阵 |
| [windows-long-path.md](windows-long-path.md) | 超过 MAX_PATH 的路径在 Windows 上**裸路径一律失败**, 而失败方式有**三种**(给假 / 抛错 / 静默退化), 同一根因会在不同层伪装成不同症状 —— 前缀、比较、打开、删除四处各有坑。 | 长路径, MAX_PATH, 260, `\\?\`, 扩展长度前缀, 路径过长, 打不开文件夹, 打开目标文件夹, open_path, PIDL, SHParseDisplayName, SHOpenFolderAndSelectItems, ShellExecute, isdir, scandir, realpath, normcase, path_normalize, rmtree, WinError 3, WinError 2, 深目录, 中文长名 |
