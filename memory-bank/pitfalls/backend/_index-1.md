# backend — 后端 / qB / 平台 · 卷 1/2

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `alias-links.md` … `platform-fs.md`(共 27 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [alias-links.md](alias-links.md) | 链接能力探测: reparse 结构 / 1314 二义性 / drvfs 只在挂载选项里 | 别名, junction, symlink, 硬链接, reparse, REPARSE_DATA_BUFFER, MountPointReparseBuffer, 1314, 提权, 长路径, drvfs, WSL, 9p, /proc/… |
| [announce-epoch-semantics.md](announce-epoch-semantics.md) | qB 5.2(WebAPI 2.13.0)起 `torrents/trackers` 的 `next_announce`/`min_announce` 是 **Unix epoch 绝对秒**(qB 源码 `toSecondsSinceEpoch`, PR #23045 "sec… | next_announce, min_announce, epoch, 前跳, 倒计时, 绝对时间, 相对时间, 汇报确认, 强制汇报, reannounce, trackers, 确认超时, 恒误报, 误报失败, TOL, updatin… |
| [backend-gtm-sampler.md](backend-gtm-sampler.md) | psutil 的 Windows 网卡全集来自 GetAdaptersAddresses, 不等于 if-table 全集 | psutil,net_io_counters,net_if_stats,GetIfTable2,GetAdaptersAddresses,网卡全集,过滤层,WFP,虚拟网卡,双计,接口口径,gtm 采样 |
| [behavior-core.md](behavior-core.md) | 后端一批"看着像 bug 其实是特性"的行为 —— 改之前先确认它是不是有意设计。 | 改规则, 改主循环, 改归组, 改缺文件扫描, 改限速, 改状态持久化, 改 web 服务生命周期 |
| [cold-start-view-gap.md](cold-start-view-gap.md) | 数据/结论已经写进磁盘或内存, 但**广播/发布的时机**排在一个长达数小时的任务之后 —— | 重启后功能像没生效, 视图, 发布, publish, 广播, 冷启动, 判定真空期, 回落本地, 第一波, 长任务, 取数波 |
| [concurrency.md](concurrency.md) | 七条线程 / 状态机硬约束, 违反即引入难以复现的 bug。 | 加线程, 改队列, 改 state_file, 改校验流程, 视图组装, QbApi 写方法, 阻塞等待, 关停, stop, join |
| [config-duplicates-runtime-fact.md](config-duplicates-runtime-fact.md) | 运行期事实既不能存进配置(必然漂移), 也不能算进「配置是否变了」的指纹(判定不可复现) | 配置键重复, 数据目录不在配置里, 取数路径为空, 状态区显示值与取数不一致, 单一事实源, 迁移漏搬键, 指针 endpoint.json, data_dir, 看着已就绪却没数据, 配置变更指纹, 保存后误触发刷新, 判定不可复现 |
| [config-section-retire-across-steps.md](config-section-retire-across-steps.md) | 把一个配置段的退休拆进多步计划(本仓常态)时, 若该段仍有消费者被计划排到**后续步骤**, | 分步退休配置段, 删配置键, Config 字段与 KNOWN key 不一致, 运行期 AttributeError, 消费者属后续步骤, 过渡 stub, 一步一提交, 动态设属性假绿, 测试替身掩盖缺字段 |
| [crlf-lf-mixed-endings.md](crlf-lf-mixed-endings.md) | 仓库存量文件 CRLF/LF 混行尾: 补丁按统一行尾假设必失配 | 行尾不同, CRLF, LF, 批量替换未命中, count=0, edit 匹配失败, 补丁失配, here-string 转义 |
| [ctypes-x64-argtypes.md](ctypes-x64-argtypes.md) | 用 `ctypes.windll.user32.XXX(...)` 直调 Windows API 时**不声明 argtypes/restype**, 参数按 32 位 int 传, 而 `HWND` / `HWND_TOPMOST` 这类"指针宽度"参数的高 32 位是寄存器残… | ctypes, windll, WinDLL, argtypes, restype, 静默失败, GetLastError 为 0, x64, 传参, HWND, 指针宽度, 寄存器残留, 有概率, SetWindowPos, SetFor… |
| [deps-upgrade-2026-10.md](deps-upgrade-2026-10.md) | fastapi 0.x 升级后 body: dict 注解把 JSON null 拦成 422 | fastapi 升级, 0.x minor, body dict, 422, 400 契约, Optional, pydantic 校验, notify, 签名 |
| [effect-confirmation.md](effect-confirmation.md) | 「从陈旧观测直接下确定性结论」—— 异步操作(recheck 这类 qB 异步应用 + 快照按节拍滞后)的成败宣称若只凭一份快照观测, 而该快照在「生效前」与「生效后」**不可分辨**(已完成种子 progress=1.0 且非 checking, 既是校验前的完成态也是校验通过… | 异步操作, 成败判定, 轮询, recheck, 校验成功, 校验启动超时, seen_checking, poll_verdict, is_piece_checking, checkingResumeData, 伪证据, 快照滞后, 首跳… |
| [explorer-foreground.md](explorer-foreground.md) | 后台进程经 `SHOpenFolderAndSelectItems` / `os.startfile` 弹资源管理器时, 新窗口**有概率被压在当前前台窗口后面** —— Windows 前台锁不允许后台进程抢前台; 必须打开后找回窗口、抬 Z 序, 再尽力争取焦点。⚠ 2026… | 打开目标文件夹, open-path, open_path, 资源管理器, explorer, 不弹到顶层, 不置前, 后台窗口, 前台锁, foreground, SetForegroundWindow, AttachThreadInpu… |
| [fault-domain-classification.md](fault-domain-classification.md) | 分类模型缺一层时, **通道 / 环境类**故障会掉进基类, 被下游当「站点故障」处理 —— 于是环境噪音进持久证据链(站点文件 `wave.notes`)、推进档位失败(连关几晚升成「疑似改版」ERROR), 并出现在前端错误历史。判据: **异常即分类** —— 「能不能靠重… | 告警文案与真实根因不符, 环境态被当站点结论, 错误历史里出现「浏览器 / 网络 / 本机」字样, 通道静默, 取数超时, 新增告警出口, 想给日志打静默标记 |
| [format-driven-parse.md](format-driven-parse.md) | 解析"按 format 渲染出来的文本"(日志行首当其冲)时, 把字段的**书写形状**写死成字面量 —— 默认配置下侥幸能跑, 用户换一种 format 就**静默失效**; 过滤类失效的表现是"恒空", 与"确实没有"完全同形。 | 日志过滤, 按等级, 日志行解析, levelname, 日志格式, format, 正则提取, 文本解析, 恒空, 结果为空 |
| [fs-pathmap-tristate.md](fs-pathmap-tristate.md) | 文件访问层(2026-09-27 审查轮)踩出的两条 —— ①casefold 折叠空间匹配后回原串切片, | casefold, 大小写无关, 前缀匹配, 路径映射, path_map, 切片, 变长折叠, UNDETERMINED, |
| [fuzzy-match-noise.md](fuzzy-match-noise.md) | 用「够长的连续重合段」判两个发布名是否同一内容时, 若不先把分辨率 / 来源 / 编码 / 音轨这些 | 粗配, 相似度, 重合段, 名称匹配, fuzzy, 阈值 K, 假重合, 假阳性, 质量标签, 判据收紧, 白烧配额, 下载触发器 |
| [gate-order-reachability.md](gate-order-reachability.md) | 闸门顺序=语义回归面: 前置闸门与后置闸门同判时, 后置结构性不可达 | 闸门顺序, 新增闸门, 插闸门, dedup, 跳检, G3, 遮蔽, 不可达, 前置闸门, 顺序调整 |
| [gtm-total-baseline.md](gtm-total-baseline.md) | 合计基线在过滤集收缩时被网卡生命周期累计污染 | GTM,采样,合计基线,网卡消失,断连恢复,当日流量虚高 |
| [high-risk-ops.md](high-risk-ops.md) | 代码里已有防护的高风险动作 —— 改动时**不得削弱**这些防护; 删种重加、强制汇报、限速覆盖都属于这一类。 | 跳检, reannounce, qB 版本兼容, 删除种子, 限速, or 默认值, 死防御, 状态观测 |
| [hot-reload-held-config.md](hot-reload-held-config.md) | 影响分级标 L0 只保证「新配置对象已被替换」; 若消费方(服务/线程)构造时把配置**按值**拷走, | 加配置键, 定热重载级别, impact, L0, 热重载, apply, 按值持有, 站点接入, 服务重建 |
| [hot-reload-stale-bindings-derived-views.md](hot-reload-stale-bindings-derived-views.md) | 「换对象 ≠ 下游自动跟进」家族三段 —— ①存量 `TorrentRecord.tracker_conf` 仍指向旧 Config 的 `TrackerConfig`, 重绑只有 L2 结构重建与 full_round 补 None 两条路, 配置值类变更(如 `hr_chec… | 热重载, apply, 重绑, tracker_conf, hr_check, hr 规则段, 判定不刷新, 本地·达标, WebUI 快照, 置脏, revision, 取数, rebuild_runtime, 种子级任务, 补建, ha… |
| [last-round-snapshot-stale.md](last-round-snapshot-stale.md) | 增量快照(`last_added` / `last_removed` / `delta_fields`)是「最近一轮」语义 —— **不排空, 下一轮 `_apply` 才覆盖写**。无新应用轮时它们是**残值**: 单独当键源会把上一轮的变更重复发布或把无键轮误判成有键轮(归约… | last_added, last_removed, delta_fields, rounds_applied, 残值, 最近一轮, keyed, 增量键源, 快照语义, 消费判定, fuzz, 纯命令源 |
| [lazy-property-parse-error.md](lazy-property-parse-error.md) | 给解析器套 `try/except` 做 fail-closed 时, 若只把**构造函数**包进去, 而真正会抛的是结果对象的**惰性 property**(如 `urlsplit(...).port`), 异常照样穿透 —— 安全闸门于是变成 500, 而不是它该给的 403… | 给解析/判定函数加 try 收口; 同族解析器有两侧(如 Host 头 / Origin 头); 生产路径出现「畸形输入报 500」。 |
| [nested-container-recursion.md](nested-container-recursion.md) | 动作域加嵌套容器(choose)后, 遍历 actions 的检测/剔除判定不递归 = 校验放行而载入崩 | choose, 编排块, then, default, 嵌套, 递归, 遍历 actions, 退役伪动作, 校验放行, 载入崩 |
| [page-scraping.md](page-scraping.md) | 从 HTML 里抽一段小数字 / 小文本时, 不锤定结构的正则会匹配到页面上别处的同类文本 —— 结果**看着合法但值是错的**, 且不报错。 | 爬页面, 抓页面, 解析 HTML, 正则提取, 页脚区间, 分页判据, HR 统计页, 站点改版, 数字提取 |
| [platform-fs.md](platform-fs.md) | Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。 | 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, C… |
