# backend — 后端 / qB / 平台 · 卷 2/2

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `page-scraping.md` … `windows-relocate-traps.md`(共 25 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [page-scraping.md](page-scraping.md) | 从 HTML 里抽一段小数字 / 小文本时, 不锤定结构的正则会匹配到页面上别处的同类文本 —— 结果**看着合法但值是错的**, 且不报错。 | 爬页面, 抓页面, 解析 HTML, 正则提取, 页脚区间, 分页判据, HR 统计页, 站点改版, 数字提取 |
| [platform-fs.md](platform-fs.md) | Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。 | 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, C… |
| [qb-api.md](qb-api.md) | qB 版本差异、`sync/maindata` 增量语义、`torrents/add` 的响应形态与选项缺省语义、`TorrentRecord` 的唯一所有权 —— 改数据层前必读。 | 改 qbapi, 改 store, 改 TorrentRecord, 改 apply_sync, 加种子字段, 全局限速, qB 状态, 添加种子, torrents/add, 添加后开始, stopped, autoTMM, 自动种子管理… |
| [qb-content-path-semantics.md](qb-content-path-semantics.md) | qB Web API 的 `content_path` 报的是**逻辑完成形态**的路径 —— 单文件种子在文件尚未落盘、或启用了「未完成文件加 .!qB 扩展名」时, 该路径在磁盘上**不存在**, qB 不会报空也不会报后缀名。对它做存在性分流时若写「非目录即文件」(`isd… | content_path, root_path, open-path, open_path, 单文件种子, 下载中, 未落盘, .!qB, 未完成扩展名, 目标文件不存在, 打开目标文件夹失败, 定位选中, select, 解析顺序, 辅种… |
| [qb-fastresume-edit.md](qb-fastresume-edit.md) | 改 qB 的 BT_backup fastresume 有四条铁律 —— ①qB 在线时写入必被秒级覆盖(pause/start/标签等 ~20 类操作挂 `deferredRequestResumeData`, 实测 0.5s), 只能写 qB 下线窗口; ②save path… | fastresume, BT_backup, qBt-savePath, save_path, 改路径, relocate 收尾 |
| [qbmanager-retired-names.md](qbmanager-retired-names.md) | QbManager 上抽新方法/加新属性时, 命名会撞**别名冻结守阵**(`tests/test_qbmanager_alias_freeze.py`)——退役旧名(分诊清单 `26-10-01-0350-plan-web-state-alias-disposal.triage… | qbmanager, 抽方法, 抽私有方法, 重构命名, _load_state, 退役名, alias_freeze, 复活, 分诊清单, QbManager 新方法 |
| [release-record-baseline.md](release-record-baseline.md) | 一份凭据(放行/授权/豁免记录)若靠「与签发时的状态快照比对」来判断是否失效, 快照就是 | 放行记录, verified, 签发, 锚点, 快照, 漂移, drift, 永续有效, 永久记录, 凭据, 三处写入点, 签发即作废 |
| [relocate-restore-issued-marker.md](relocate-restore-issued-marker.md) | 「先落账、后下发」的恢复点若按相位一律置 issue=False, 崩溃窗口(外部系统从未收到指令)在两处现场上与「发了没动静」同形 ⇒ 静默等到停滞超时误判失败; 判据必须靠账上「已下发」位分流, 且两条下发路径都要落账 | 重启恢复, 崩溃恢复, 崩溃窗口, setLocation 补发, move_issued, 恢复判据, 账上事实, 下发路径, _load_jobs, recover_exec_phase, 死代码判据 |
| [schema-stamp-writeback.md](schema-stamp-writeback.md) | 带 schema 版本链的写回(writer)若「校验走迁移后的临时副本、落盘写原始提交树 + 新版章」, | schema 迁移, 版本链, 写回, writer, 盖章, schema_version, WebUI 保存, read_tree, |
| [sentinel-epoch-arith.md](sentinel-epoch-arith.md) | 哨兵值泄漏进算术比较: 「0 = 无位置概念」被当成 epoch 0, 覆盖判据静默恒通过 | cutoff_done, 哨兵, 0 = 没有位置概念, 位置证明, 覆盖判据, 减法, 比较, epoch 0, 恒通过, 退化, 永续放行, 缺席证明, 观察期, HR 管束 |
| [suppress-request-vs-live-flag.md](suppress-request-vs-live-flag.md) | EventBus suppress 曾把「重放保护请求」与「事件分派相位的抑制」混在一个 `_suppressed` 字段上 —— 注释宣称"窗口只盖两个事件相位", 实现却在置位点到下轮轮首之间吞掉一切 emit, 连续两次 L2 重建时第二次的 queue_rebuilt 静… | 改 EventBus, 改 suppress, 抑制窗口, 重建窗口内 emit, 相位丢失, 事件被吞, queue_rebuilt, 重放保护, 一符两义, 注释与实现不符, set_suppressed, take_suppresse… |
| [task-interval-tick-quantization.md](task-interval-tick-quantization.md) | TaskQueue 周期任务的两条同族陷阱。①**节拍量化**: 到期判据只在主循环 tick 边界评估(next_run 只能被 tick「看见」), 真实节奏 = ceil(max(interval, main_tick)/main_tick)×main_tick —— 3s… | 周期采样任务, 按配置间隔推算数据粒度, 读侧栅格/桶宽, 伪断线, 图上有规律缺口, 行距比配置间隔大, 采样节奏不对齐, 采样被饿死, 重启后静默, 队列积压, 补建任务, max_tasks_per_tick, 周期任务轮不到, 假平… |
| [traffic-agg-reseal.md](traffic-agg-reseal.md) | 小时/日/月聚合行的封口有两条非显然约束 —— ①已封口的桶**仍会**收到迟到信用(长空闲 z 游程 | 逐级聚合无有效覆盖, cov_s 只留残余, 同 epoch 重封, 替换丢覆盖, 覆盖率偏小, agg 停写, 全系列小时行不落盘, 一个系列坏全批不写, 每轮 flush 复现, pending.pop, ZRUN_FLUSH_S, 延… |
| [traffic-row-format-extension.md](traffic-row-format-extension.md) | 给按列数白名单解析的行型加列(本仓 v4 天文件 z 行加「末端快照对」, plan 26-10-16-1509 形态 D)有两处非显然约束 —— ①新列位次不能追加在**可选尾列**之后: 会产生歧义列数(6 列既可读成「尾列 + 半对」也可读成「无尾列的整对」), 必须插在可… | 行型扩列, 加列, 可选尾列, 列数歧义, 位次定约, 回滚, 旧解析器整行判坏, z 行末端对, v4 天文件, 格式定约, 向后兼容 |
| [traffic-source-discovery-pointer.md](traffic-source-discovery-pointer.md) | 工具发现层若把指针/锁放进 data_dir 或拿 pid 判存活, 一旦 `--data-dir` 改过、进程崩了留 pid、或按 cwd 推目录(自启时 cwd 是 system32)就全错。正解: 指针与锁锚用户级平台目录(与数据目录解耦)、就绪只认 `GET /statu… | endpoint.json, 发现指针, 全局流量来源, global-traffic-monitor, 探活, 未运行, 拉不起来, data_dir, pid, 残留指针 |
| [traffic-source-random-port.md](traffic-source-random-port.md) | 控制面端口改成 `http_port: 0`(内核分配)后, 文档示例 / 排障 curl / 订阅注册键里任何写死端口都成了错答案; 端口唯一出口是发现指针(手工看用 `endpoint` 子命令), 且端口一变订阅必须重注册。 | http_port 0, 随机端口, 8099, endpoint 子命令, 端口占用, 订阅注册, 重注册, 端口变 |
| [traffic-window-edge-floor.md](traffic-window-edge-floor.md) | `traffic_grid.v4_series_points` 的真空/断连 null 标记时间**向下取整**(`int(prev_chain_end)` / `floor(ts)`), 而观测点的保留判据是「覆盖桶触及窗口左界」(`ceil(ts) >= t0`)—— 两判据… | 改读侧窗过滤, 改窗首种子外扩, 改归桶/真空判定, 改 null 点, 改 v4_series_points, 假尖峰, 恢复首桶, 取整, 边界带 |
| [tray-sigterm-teardown.md](tray-sigterm-teardown.md) | 主线程阻塞在 GUI mainloop 时, 「raise KeyboardInterrupt」版信号 handler 的异常会跳过 mainloop 之后的收尾编排; 只要进程里还有非 daemon 线程(如 pystray run_detached), 进程退出就挂在 thr… | 信号 handler, SIGTERM, KeyboardInterrupt, 托盘, mainloop, Tk, pystray, 非 daemon 线程, threading._shutdown, 进程不退出, 收尾被跳过, 退出挂死 |
| [unreachable-wait.md](unreachable-wait.md) | 与外部通道(浏览器扩展 / 本机端点 / 代理 / 设备)打交道时, 若「对面能不能收到」在本机 | 等待回传, 超时, request_timeout, 白等, 端点未监听, 端口未绑定, 快速失败, fail-fast, 假线索, 排查方向, 通道不可用, listening |
| [verdict-scope-parity.md](verdict-scope-parity.md) | 一条业务判据(排除表 / 白名单 / 开关 / 门槛)常有多个消费侧 —— 各侧若**各自实现一遍**该判据, 漏掉任一侧就会「配了不生效」, 且不报错、不告警, 只在行为上体现 (多为「频率 / 数量 / 展示」与预期不符)。 | 加/改一条作用于某类对象的判定; 给已有判据补新的消费点; 用户报「配置了没反应」。 |
| [web-package-split.md](web-package-split.md) | web.py → web/ 包拆分(plan 26-09-22-1857)实打实撞出来的四条 —— FastAPI 懒解析路由、包内 logger 命名、__file__ 基准降级、生成脚本转义陷阱。 | 拆 web/ 包, 改 factory, include_router, app.routes, getLogger, __file__, 生成脚本, 金清单守阵 |
| [webui-h11-request-line-cap.md](webui-h11-request-line-cap.md) | 组级路由把整组 key(base64url(组路径+全组文件相对路径))放进请求行; h11 缺省 16KB「未完成事件」上限在**头分片到达且停在未完成态**时判非法 —— 头一次性完整到达反而不触发, 所以症状间歇(大组「启动整组」时好时坏)。修法 = uvicorn.Con… | WEB 传输层,h11,请求行,组 key,Invalid HTTP request received,Receive buffer too long,MUST_CLOSE,uvicorn,启动整组,间歇性 400 |
| [windows-long-path.md](windows-long-path.md) | 超过 MAX_PATH 的路径在 Windows 上**裸路径一律失败**, 而失败方式有**三种**(给假 / 抛错 / 静默退化), 同一根因会在不同层伪装成不同症状 —— 前缀、比较、打开、删除四处各有坑。 | 长路径, MAX_PATH, 260, `\\?\`, 扩展长度前缀, 路径过长, 打不开文件夹, 打开目标文件夹, open_path, PIDL, SHParseDisplayName, SHOpenFolderAndSelectIte… |
| [windows-onlogon-autostart-elevation.md](windows-onlogon-autostart-elevation.md) | Windows ONLOGON 计划任务注册需提权: 非提权进程 rc=1「拒绝访问」, 与 Program Blacklist 的 WinError 5 同指纹 | 开机自启, autostart, schtasks, ONLOGON, 计划任务, 拒绝访问, 提权, UAC, 自启注册失败, HKCU Run, 注册表自启, Run 值 260 |
| [windows-relocate-traps.md](windows-relocate-traps.md) | Windows 进程探测/长路径/组键迁移三处陷阱> | os.kill, TerminateProcess, guardian, 进程探测, 长路径, os.path.getsize, 组键迁移, 增量视图, 孤儿行, scope_hit |
