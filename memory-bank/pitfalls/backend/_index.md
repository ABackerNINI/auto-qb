# backend — 后端 / qB / 平台

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 高风险业务操作的防护、qB API 与数据层契约、并发与状态机约束、平台 / 文件系统差异。
> **触发**: 后端, qB, qbapi, store, 主循环, 规则, 并发, 平台, Windows, Linux, 磁盘

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [alias-links.md](alias-links.md) | 链接能力探测: reparse 结构 / 1314 二义性 / drvfs 只在挂载选项里 | 别名, junction, symlink, 硬链接, reparse, REPARSE_DATA_BUFFER, MountPointReparseBuffer, 1314, 提权, 长路径, drvfs, WSL, 9p, /proc/… |
| [announce-epoch-semantics.md](announce-epoch-semantics.md) | qB 5.2(WebAPI 2.13.0)起 `torrents/trackers` 的 `next_announce`/`min_announce` 是 **Unix epoch 绝对秒**(qB 源码 `toSecondsSinceEpoch`, PR #23045 "sec… | next_announce, min_announce, epoch, 前跳, 倒计时, 绝对时间, 相对时间, 汇报确认, 强制汇报, reannounce, trackers, 确认超时, 恒误报, 误报失败, TOL, updatin… |
| [behavior-core.md](behavior-core.md) | 后端一批"看着像 bug 其实是特性"的行为 —— 改之前先确认它是不是有意设计。 | 改规则, 改主循环, 改归组, 改缺文件扫描, 改限速, 改状态持久化, 改 web 服务生命周期 |
| [cold-start-view-gap.md](cold-start-view-gap.md) | 数据/结论已经写进磁盘或内存, 但**广播/发布的时机**排在一个长达数小时的任务之后 —— | 重启后功能像没生效, 视图, 发布, publish, 广播, 冷启动, 判定真空期, 回落本地, 第一波, 长任务, 取数波 |
| [concurrency.md](concurrency.md) | 七条线程 / 状态机硬约束, 违反即引入难以复现的 bug。 | 加线程, 改队列, 改 state_file, 改校验流程, 视图组装, QbApi 写方法, 阻塞等待, 关停, stop, join |
| [config-duplicates-runtime-fact.md](config-duplicates-runtime-fact.md) | 运行期事实既不能存进配置(必然漂移), 也不能算进「配置是否变了」的指纹(判定不可复现) | 配置键重复, 数据目录不在配置里, 取数路径为空, 状态区显示值与取数不一致, 单一事实源, 迁移漏搬键, 指针 endpoint.json, data_dir, 看着已就绪却没数据, 配置变更指纹, 保存后误触发刷新, 判定不可复现 |
| [config-section-retire-across-steps.md](config-section-retire-across-steps.md) | 把一个配置段的退休拆进多步计划(本仓常态)时, 若该段仍有消费者被计划排到**后续步骤**, | 分步退休配置段, 删配置键, Config 字段与 KNOWN key 不一致, 运行期 AttributeError, 消费者属后续步骤, 过渡 stub, 一步一提交, 动态设属性假绿, 测试替身掩盖缺字段 |
| [ctypes-x64-argtypes.md](ctypes-x64-argtypes.md) | 用 `ctypes.windll.user32.XXX(...)` 直调 Windows API 时**不声明 argtypes/restype**, 参数按 32 位 int 传, 而 `HWND` / `HWND_TOPMOST` 这类"指针宽度"参数的高 32 位是寄存器残… | ctypes, windll, WinDLL, argtypes, restype, 静默失败, GetLastError 为 0, x64, 传参, HWND, 指针宽度, 寄存器残留, 有概率, SetWindowPos, SetFor… |
| [effect-confirmation.md](effect-confirmation.md) | 「从陈旧观测直接下确定性结论」—— 异步操作(recheck 这类 qB 异步应用 + 快照按节拍滞后)的成败宣称若只凭一份快照观测, 而该快照在「生效前」与「生效后」**不可分辨**(已完成种子 progress=1.0 且非 checking, 既是校验前的完成态也是校验通过… | 异步操作, 成败判定, 轮询, recheck, 校验成功, 校验启动超时, seen_checking, poll_verdict, is_piece_checking, checkingResumeData, 伪证据, 快照滞后, 首跳… |
| [explorer-foreground.md](explorer-foreground.md) | 后台进程经 `SHOpenFolderAndSelectItems` / `os.startfile` 弹资源管理器时, 新窗口**有概率被压在当前前台窗口后面** —— Windows 前台锁不允许后台进程抢前台; 必须打开后找回窗口、抬 Z 序, 再尽力争取焦点。⚠ 2026… | 打开目标文件夹, open-path, open_path, 资源管理器, explorer, 不弹到顶层, 不置前, 后台窗口, 前台锁, foreground, SetForegroundWindow, AttachThreadInpu… |
| [fault-domain-classification.md](fault-domain-classification.md) | 分类模型缺一层时, **通道 / 环境类**故障会掉进基类, 被下游当「站点故障」处理 —— 于是环境噪音进持久证据链(站点文件 `wave.notes`)、推进档位失败(连关几晚升成「疑似改版」ERROR), 并出现在前端错误历史。判据: **异常即分类** —— 「能不能靠重… | 告警文案与真实根因不符, 环境态被当站点结论, 错误历史里出现「浏览器 / 网络 / 本机」字样, 通道静默, 取数超时, 新增告警出口, 想给日志打静默标记 |
| [format-driven-parse.md](format-driven-parse.md) | 解析"按 format 渲染出来的文本"(日志行首当其冲)时, 把字段的**书写形状**写死成字面量 —— 默认配置下侥幸能跑, 用户换一种 format 就**静默失效**; 过滤类失效的表现是"恒空", 与"确实没有"完全同形。 | 日志过滤, 按等级, 日志行解析, levelname, 日志格式, format, 正则提取, 文本解析, 恒空, 结果为空 |
| [fs-pathmap-tristate.md](fs-pathmap-tristate.md) | 文件访问层(2026-09-27 审查轮)踩出的两条 —— ①casefold 折叠空间匹配后回原串切片, | casefold, 大小写无关, 前缀匹配, 路径映射, path_map, 切片, 变长折叠, UNDETERMINED, |
| [fuzzy-match-noise.md](fuzzy-match-noise.md) | 用「够长的连续重合段」判两个发布名是否同一内容时, 若不先把分辨率 / 来源 / 编码 / 音轨这些 | 粗配, 相似度, 重合段, 名称匹配, fuzzy, 阈值 K, 假重合, 假阳性, 质量标签, 判据收紧, 白烧配额, 下载触发器 |
| [high-risk-ops.md](high-risk-ops.md) | 代码里已有防护的高风险动作 —— 改动时**不得削弱**这些防护; 删种重加、强制汇报、限速覆盖都属于这一类。 | 跳检, reannounce, qB 版本兼容, 删除种子, 限速, or 默认值, 死防御, 状态观测 |
| [hot-reload-held-config.md](hot-reload-held-config.md) | 影响分级标 L0 只保证「新配置对象已被替换」; 若消费方(服务/线程)构造时把配置**按值**拷走, | 加配置键, 定热重载级别, impact, L0, 热重载, apply, 按值持有, 站点接入, 服务重建 |
| [hot-reload-stale-bindings-derived-views.md](hot-reload-stale-bindings-derived-views.md) | 「换对象 ≠ 下游自动跟进」家族三段 —— ①存量 `TorrentRecord.tracker_conf` 仍指向旧 Config 的 `TrackerConfig`, 重绑只有 L2 结构重建与 full_round 补 None 两条路, 配置值类变更(如 `hr_chec… | 热重载, apply, 重绑, tracker_conf, hr_check, hr 规则段, 判定不刷新, 本地·达标, WebUI 快照, 置脏, revision, 取数, rebuild_runtime, 种子级任务, 补建, ha… |
| [last-round-snapshot-stale.md](last-round-snapshot-stale.md) | 增量快照(`last_added` / `last_removed` / `delta_fields`)是「最近一轮」语义 —— **不排空, 下一轮 `_apply` 才覆盖写**。无新应用轮时它们是**残值**: 单独当键源会把上一轮的变更重复发布或把无键轮误判成有键轮(归约… | last_added, last_removed, delta_fields, rounds_applied, 残值, 最近一轮, keyed, 增量键源, 快照语义, 消费判定, fuzz, 纯命令源 |
| [page-scraping.md](page-scraping.md) | 从 HTML 里抽一段小数字 / 小文本时, 不锤定结构的正则会匹配到页面上别处的同类文本 —— 结果**看着合法但值是错的**, 且不报错。 | 爬页面, 抓页面, 解析 HTML, 正则提取, 页脚区间, 分页判据, HR 统计页, 站点改版, 数字提取 |
| [platform-fs.md](platform-fs.md) | Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。 | 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, C… |
| [qb-api.md](qb-api.md) | qB 版本差异、`sync/maindata` 增量语义、`torrents/add` 的响应形态与选项缺省语义、`TorrentRecord` 的唯一所有权 —— 改数据层前必读。 | 改 qbapi, 改 store, 改 TorrentRecord, 改 apply_sync, 加种子字段, 全局限速, qB 状态, 添加种子, torrents/add, 添加后开始, stopped, autoTMM, 自动种子管理… |
| [qb-content-path-semantics.md](qb-content-path-semantics.md) | qB Web API 的 `content_path` 报的是**逻辑完成形态**的路径 —— 单文件种子在文件尚未落盘、或启用了「未完成文件加 .!qB 扩展名」时, 该路径在磁盘上**不存在**, qB 不会报空也不会报后缀名。对它做存在性分流时若写「非目录即文件」(`isd… | content_path, root_path, open-path, open_path, 单文件种子, 下载中, 未落盘, .!qB, 未完成扩展名, 目标文件不存在, 打开目标文件夹失败, 定位选中, select, 解析顺序, 辅种… |
| [qbmanager-retired-names.md](qbmanager-retired-names.md) | QbManager 上抽新方法/加新属性时, 命名会撞**别名冻结守阵**(`tests/test_qbmanager_alias_freeze.py`)——退役旧名(分诊清单 `26-10-01-0350-plan-web-state-alias-disposal.triage… | qbmanager, 抽方法, 抽私有方法, 重构命名, _load_state, 退役名, alias_freeze, 复活, 分诊清单, QbManager 新方法 |
| [release-record-baseline.md](release-record-baseline.md) | 一份凭据(放行/授权/豁免记录)若靠「与签发时的状态快照比对」来判断是否失效, 快照就是 | 放行记录, verified, 签发, 锚点, 快照, 漂移, drift, 永续有效, 永久记录, 凭据, 三处写入点, 签发即作废 |
| [schema-stamp-writeback.md](schema-stamp-writeback.md) | 带 schema 版本链的写回(writer)若「校验走迁移后的临时副本、落盘写原始提交树 + 新版章」, | schema 迁移, 版本链, 写回, writer, 盖章, schema_version, WebUI 保存, read_tree, |
| [suppress-request-vs-live-flag.md](suppress-request-vs-live-flag.md) | EventBus suppress 曾把「重放保护请求」与「事件分派相位的抑制」混在一个 `_suppressed` 字段上 —— 注释宣称"窗口只盖两个事件相位", 实现却在置位点到下轮轮首之间吞掉一切 emit, 连续两次 L2 重建时第二次的 queue_rebuilt 静… | 改 EventBus, 改 suppress, 抑制窗口, 重建窗口内 emit, 相位丢失, 事件被吞, queue_rebuilt, 重放保护, 一符两义, 注释与实现不符, set_suppressed, take_suppresse… |
| [task-interval-tick-quantization.md](task-interval-tick-quantization.md) | TaskQueue 周期任务的两条同族陷阱。①**节拍量化**: 到期判据只在主循环 tick 边界评估(next_run 只能被 tick「看见」), 真实节奏 = ceil(max(interval, main_tick)/main_tick)×main_tick —— 3s… | 周期采样任务, 按配置间隔推算数据粒度, 读侧栅格/桶宽, 伪断线, 图上有规律缺口, 行距比配置间隔大, 采样节奏不对齐, 采样被饿死, 重启后静默, 队列积压, 补建任务, max_tasks_per_tick, 周期任务轮不到, 假平… |
| [traffic-agg-reseal.md](traffic-agg-reseal.md) | 小时/日/月聚合行的封口有两条非显然约束 —— ①已封口的桶**仍会**收到迟到信用(长空闲 z 游程 | 逐级聚合无有效覆盖, cov_s 只留残余, 同 epoch 重封, 替换丢覆盖, 覆盖率偏小, agg 停写, 全系列小时行不落盘, 一个系列坏全批不写, 每轮 flush 复现, pending.pop, ZRUN_FLUSH_S, 延… |
| [traffic-row-format-extension.md](traffic-row-format-extension.md) | 给按列数白名单解析的行型加列(本仓 v4 天文件 z 行加「末端快照对」, plan 26-10-16-1509 形态 D)有两处非显然约束 —— ①新列位次不能追加在**可选尾列**之后: 会产生歧义列数(6 列既可读成「尾列 + 半对」也可读成「无尾列的整对」), 必须插在可… | 行型扩列, 加列, 可选尾列, 列数歧义, 位次定约, 回滚, 旧解析器整行判坏, z 行末端对, v4 天文件, 格式定约, 向后兼容 |
| [traffic-source-discovery-pointer.md](traffic-source-discovery-pointer.md) | 工具发现层若把指针/锁放进 data_dir 或拿 pid 判存活, 一旦 `--data-dir` 改过、进程崩了留 pid、或按 cwd 推目录(自启时 cwd 是 system32)就全错。正解: 指针与锁锚用户级平台目录(与数据目录解耦)、就绪只认 `GET /statu… | endpoint.json, 发现指针, 全局流量来源, global-traffic-monitor, 探活, 未运行, 拉不起来, data_dir, pid, 残留指针 |
| [traffic-source-random-port.md](traffic-source-random-port.md) | 控制面端口改成 `http_port: 0`(内核分配)后, 文档示例 / 排障 curl / 订阅注册键里任何写死端口都成了错答案; 端口唯一出口是发现指针(手工看用 `endpoint` 子命令), 且端口一变订阅必须重注册。 | http_port 0, 随机端口, 8099, endpoint 子命令, 端口占用, 订阅注册, 重注册, 端口变 |
| [traffic-window-edge-floor.md](traffic-window-edge-floor.md) | `traffic_grid.v4_series_points` 的真空/断连 null 标记时间**向下取整**(`int(prev_chain_end)` / `floor(ts)`), 而观测点的保留判据是「覆盖桶触及窗口左界」(`ceil(ts) >= t0`)—— 两判据… | 改读侧窗过滤, 改窗首种子外扩, 改归桶/真空判定, 改 null 点, 改 v4_series_points, 假尖峰, 恢复首桶, 取整, 边界带 |
| [unreachable-wait.md](unreachable-wait.md) | 与外部通道(浏览器扩展 / 本机端点 / 代理 / 设备)打交道时, 若「对面能不能收到」在本机 | 等待回传, 超时, request_timeout, 白等, 端点未监听, 端口未绑定, 快速失败, fail-fast, 假线索, 排查方向, 通道不可用, listening |
| [verdict-scope-parity.md](verdict-scope-parity.md) | 一条业务判据(排除表 / 白名单 / 开关 / 门槛)常有多个消费侧 —— 各侧若**各自实现一遍**该判据, 漏掉任一侧就会「配了不生效」, 且不报错、不告警, 只在行为上体现 (多为「频率 / 数量 / 展示」与预期不符)。 | 加/改一条作用于某类对象的判定; 给已有判据补新的消费点; 用户报「配置了没反应」。 |
| [web-package-split.md](web-package-split.md) | web.py → web/ 包拆分(plan 26-09-22-1857)实打实撞出来的四条 —— FastAPI 懒解析路由、包内 logger 命名、__file__ 基准降级、生成脚本转义陷阱。 | 拆 web/ 包, 改 factory, include_router, app.routes, getLogger, __file__, 生成脚本, 金清单守阵 |
| [windows-long-path.md](windows-long-path.md) | 超过 MAX_PATH 的路径在 Windows 上**裸路径一律失败**, 而失败方式有**三种**(给假 / 抛错 / 静默退化), 同一根因会在不同层伪装成不同症状 —— 前缀、比较、打开、删除四处各有坑。 | 长路径, MAX_PATH, 260, `\\?\`, 扩展长度前缀, 路径过长, 打不开文件夹, 打开目标文件夹, open_path, PIDL, SHParseDisplayName, SHOpenFolderAndSelectIte… |
| [windows-onlogon-autostart-elevation.md](windows-onlogon-autostart-elevation.md) | Windows ONLOGON 计划任务注册需提权: 非提权进程 rc=1「拒绝访问」, 与 Program Blacklist 的 WinError 5 同指纹 | 开机自启, autostart, schtasks, ONLOGON, 计划任务, 拒绝访问, 提权, UAC, 自启注册失败, HKCU Run, 注册表自启, Run 值 260 |
| [windows-relocate-traps.md](windows-relocate-traps.md) | Windows 进程探测/长路径/组键迁移三处陷阱> | os.kill, TerminateProcess, guardian, 进程探测, 长路径, os.path.getsize, 组键迁移, 增量视图, 孤儿行, scope_hit |
