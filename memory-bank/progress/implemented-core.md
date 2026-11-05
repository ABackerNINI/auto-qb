# 已实现 · 客户端 / 主循环 / 状态 / 内置功能

> 摘要: 后端主干与内置功能的落地记录 —— 客户端 / 主循环 / 数据层 / 任务队列 / 托盘 / 通知 / 标签 / HR / 分组。
> 触发: 做过没有, 主循环, 数据层, 任务队列, 托盘, 通知, 标签, HR, 分组, 单实例锁

## 已实现 (✅, 有单测覆盖)

- **WebUI 启动期 bind 失败 fail-fast + 占用者诊断 (2026-11-03, 计划 [26-11-03-0930](../plans/26-11-03-0930-plan-webui-bind-fail-fast.html) · 档案 [26-11-03-webui-bind-fail-fast](../tasks/26-11-03-webui-bind-fail-fast.md))**: `web.port` 被占时不再吞成一条 ERROR 日志继续跑 —— `WebUIModule.start` 检查 `handle.started` 失败后落 INFO 诊断块(原因/占用者/处置/退出)并抛 `WebUIBindError(AutoQbError)`, 走 CLI 既有的干净退出通道(退出码 1 / 单行 stderr / 无堆栈); 低层 `start_web_server` 保持返回 handle 的原契约(热重载 `apply` 语义不变, R1)。占用者取证新增 `infra/port_owner.py`(Windows netstat+tasklist / Linux ss / macOS lsof, 三态降级 + 1.5s 总预算 + 命令行截断 160 字符), 结果只进日志。连带修复: `qbmanager.run` 的 `start_all` 移入 `try`, `lifecycle_ready` 闸门阻止失败启动写空态 `state.json`, `lock`/`meta.json` 在任何路径释放 —— 既有 `HrChannelBindError` 启动期漏锁一并修掉。RM01-06 保留场景、判据反转为启动期 fail-fast(真机绿); 全量基线见 [26-11-03-1112](../testing/baselines/26-11-03-1112-webui-bind-fail-fast.md)。
- **已完成种子下载保险丝 (`download_fuse`) (2026-11-03, 计划 [26-11-03-0456](../plans/26-11-03-0456-plan-skip-check-download-fuse.html) Done)**: 新增 `core/modules/fuse_mod.py` —— 对「已完成 + `dl_limit==0`」种子写 13KiB/s 奇数哨兵; 连续 `confirm_ticks` 拍 `dlspeed>0` 且限速仍等于哨兵 → pause + 标签(默认 `zFusePaused`, 配置键 `fuse_tag`), 每拍零写、只在状态迁移写标签; 显式放行 `--fuse-release <hash>` / `--fuse-release-all` 按 CAS 恢复原限速并摘标签(不自动 resume), 未完成的 released 重新完成后回武装; state 丢失时 adopt 只按「完成 + 限速恰等于哨兵」重建(带标签且暂停 → triggered, 否则 armed, 零 qB 写); 默认关闭, dry-run 零写。真机验收(副实例 56590, qB v5.2.3): 武装/3 拍触发/放行/回武装/批量 10 拍单条汇总/adopt 11 条/enabled=false 与 dry-run 零写全部通过。⚠ 实测修出 CLI 放行缺快照同步(`cli.py` 先 `store.apply_sync` 再 CAS), 否则只标 released 不恢复限速。配置口径见 [config-reference/keys.md](../config-reference/keys.md)。

- **HR 排除落到取数侧: 稳态降频对「已排除种子」恢复生效 (2026-10-08~17, 计划 [26-10-08-1249](../plans/26-10-08-1249-plan-hr-exclude-steady.html) Done · 档案 [26-10-08-backend-hr-exclude-steady](../tasks/26-10-08-backend-hr-exclude-steady.md) Done · 报告 [26-10-08-1235](../reports/26-10-08-1235-report-hr-exclude-steady.html))**: 判据单点 `TorrentRecord.hr_excluded()` 原只被判定侧/展示侧消费, 取数侧 `_build_objects` 排除链只有终态/放行/超额三档 ⇒ 被排除种子仍进对账对象集 ⇒ `steady = anchors_known and not objects` 恒假 ⇒ `idle_refresh_interval`(24H) 永不生效(实测两波间隔 16h55m)。方案 B 落地: `HrAnchor` 末加 `excluded` 位 (`hr_anchor()` 透传 `self.hr_excluded()`), `_build_objects` 循环顶部第四档跳过(置于漂移回炉之前 ⇒ 撤销排除即恢复, 不产生不可逆残留); 命中集 `local_hashes` 仍从全量锚点构建 ⇒「排除 ≠ 不认识」, 站点行仍按本地命中处理、不误下 `.torrent`。守阵 4 条 + 红验。下游项(排除种子终态行身份下载)随计划 [26-10-09-1057](../plans/26-10-09-1057-plan-hr-exclude-terminal-download.html) 闭环: 名称候选面收窄为受管集 `local_names_managed`(对上游 §7.2 不变项的有意修正, 已在 1249 §08 追加指针)。**S5 真机复核 26-10-17 用户确认生效**(`wave.idle_mode=true` / 日志「稳态降频」/ 请求量下降); 全量套件与守卫证据见基线切片 [26-10-09-1124](../testing/baselines/attachments/26-10-09-1124-hr-exclude-terminal-download.md)(最终代码态, 其后 hr 域零改动)。

> 已外迁: 2026-09-15~09-29 的 15 条 → [attachments/implemented-core-archive-2026-09.md](attachments/implemented-core-archive-2026-09.md)

> 已外迁: 2026-10-05 的 1 条 → [attachments/implemented-core-archive-2026-10.md](attachments/implemented-core-archive-2026-10.md)

- **🆕 qB 口径流量 v4 格式换代: 块头基线 delta + 按落盘切块 + 自然推算结算 (2026-10-05~06, 计划
  [plans/26-10-05-2200](../plans/26-10-05-2200-plan-qb-traffic-v4-delta.html) 全段, 报告
  [26-10-05-1946](../reports/26-10-05-1946-report-qb-traffic-v4-delta.html) Done)**:
  v3 天文件逐行绝对 totals 的行宽随 all-time 计数无界增长, 换代打包四件事: 块头 B 行携带
  totals 基线(5 列; 块首 n 游程前缀拆 3 列无基线块, 块内 r/z 判坏行) + r/z 行存相对块基线的
  delta(内存结构恒绝对, delta 只存在于线格式 —— parse 以基线 cumsum 复原、format 减法序列化,
  读侧/agg/catch-up/WebUI 语义零改动) + 关块状态机「flush ∧ 块内有 r 行才关, 空闲块跨 flush
  开放」(空闲段盘上恰 1 条长 z 行, 空闲期写盘归零、解析缓存全天有效; ZRUN 保险闸退役为天级;
  计数器重置强制关块重立基线) + 覆盖结算判定函数单点 `v4_block_gap_continuous`(gap ≤ interval +
  DRIFT_TOL → 连续, 在线 _agg_feed 与离线 _agg_credit_day_file 两路同源复用)。v3 格式函数与旧写
  路径随翻转退役, 全仓 V3→V4 符号代际改名; 目录 `qb-traffic-v4/` 全新落点, 旧 v3 原样留存不读
  不迁移(删留决定权在用户)。B1 纯函数区并存(6a98c504, 2628 passed + 4 skipped / 99% / 25.7s) →
  B2 原子翻转(B2-1..B2-3 合并前 squash, 2632 passed + 4 skipped / 98.50% / 28.1s, 机检零残留) →
  B3 收尾(配置配比口径 N2 入 models/loaders 注释; v3 计划 §02.1 条款级取代; dry-run 真机零 ERROR)。
  字节对照三档全落报告 §07 推演区间: 满速活跃天 -12.5% / 低速 -22.3% / 空闲天 -98.9%(基线
  [26-10-06-0132](../testing/baselines/attachments/26-10-06-0132-qb-traffic-v4-delta-b3.md), test.full 2632
  passed + 4 skipped / 98% / 27.8s)。格式契约单点 = traffic_store.py 模块 docstring。档案
  [tasks/26-10-05-backend-qb-traffic-v4-delta](../tasks/26-10-05-backend-qb-traffic-v4-delta.md)。
  - **追加(2026-10-16): z 行扩「末端快照对」列(形态 D)** —— 修空闲 z 游程期 agg hour 行 totals 归属错位: 封口把已知
    末端观测写进 z 行末端列(`z,<run_len>,<dlt>,<upt>,<dl_end>,<up_end>[,<dt_ms>]`; 旧 4/5 列兼容 → 退化冻结), 在线/
    离线两路按共享纯函数 `v4_z_totals_ramp` 逐槽摊配「开启快照 → 末端快照」; raw 面零触碰。细节见 issue
    26-10-16-0020-bug「修复后补充」与坑档 pitfalls/backend/traffic-row-format-extension.md。

> 已外迁: 2026-10-01~10-04 的 6 条 → [attachments/implemented-core-archive-2026-10.md](attachments/implemented-core-archive-2026-10.md)

- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 托盘常驻 UI (2026-09-12, --tray): `ui.py` —— CustomTkinter 深色窗口(状态卡片/最近日志/暂停恢复/通知热切换/开机自启)+ pystray 托盘(6 项菜单, 勾选态实时); 运行时暂停/恢复 = pause_event 完全旁观, 恢复后增量 diff 补上; 双开唤起 = 单实例锁 + localhost IPC(ui.port, 第二实例静默退出 0); 托管模式主循环移入后台线程(单一写线程约束保持), 首连失败重试常驻; GUI 栈仅 tray 分支加载; 通知开关支持从未配置状态热挂载(setup_notify force, 会话级); toast 点击激活唤起窗口(launch_arguments 经 AUMID 快捷方式 Arguments); 窗口图标 CTk iconbitmap 防 CTk 默认覆盖(assets/icon.ico); 打开日志目录前绝对化路径并确保目录存在, 托盘事件单点失败不中断 UI 轮询链; 新依赖 pystray/Pillow/customtkinter
- 主动通知 (2026-09-12): `notify.py` 零第三方依赖 —— NotifyHandler 挂 `auto_qb` logger 复用日志规范, PlatformChannel 按平台分派(win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript), quiet_hours 免打扰(与 date_time 共用 utils.time_in_range) + 每小时上限 + 同键去重窗(内存态); CLI 致命退出补发 notify_fatal; dry-run 不挂载; toast 来源显示 "AutoQB" —— 首次运行幂等注册开始菜单快捷方式 AutoQB.lnk(%APPDATA% Programs 目录, 隐式 AppUserModelID), 注册失败回退 PowerShell 来源
- 任务队列: 单 heapq 队列 + `add_task(keep_progress=...)` 断点语义 + check 轮询在途去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi Facade 确定性字段写后同步(运行状态只等 qB 同步)
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- 单实例锁 (2026-09-05): 基于第三方 `filelock`, 锁文件 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`; 仅正常 `run()` 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 失败抛 `SingleInstanceLockError(AutoQbError)`, CLI 单点捕获 AutoQbError 体系干净退出 (退出码 1, stderr 无堆栈); 陈旧锁不接管 (OS 句柄随进程退出自动释放, 必要时手动删除)

## HR 故障归属分层 (2026-10-09, 计划 26-10-09-0821)

用户实报: 关浏览器过夜, WebUI 错误历史里出现 4 条 `[HR 页面改版] 页面取数失败(等待浏览器扩展取数超时 180s)`
与 2 条 `[HR 通道静默]`。根因是**分类模型上的一个洞**: 「等扩展回传超时」在 `hr/fetcher.py` 抛的是**裸的**
`HrFetchError`, 于是掉进 service 的 `except HrFetchError` ⇒ 被当「页面取数失败」: 套 `[HR 页面改版]` 标签、
写 `wave.notes`、推进 `fail_streak`(连关几晚就升成「疑似改版」ERROR)。即**环境态被伪装成站点结论**。

- **归位**: 新增 `HrChannelTimeout(HrChannelUnavailable)` 并于超时处抛出 ⇒ 落进既有的通道层出口
  (`ACTION_NO_CHANNEL`、`_warn_no_channel` 每站一次), 上面三处污染一并消失。
- **层贯穿出口**: `events.DOMAINS`(事件→层, 单点)+ 新增 `hr/log.py`(生产点挂 `hr_domain`/`hr_silent`)
  + `infra/logging.is_record_suppressed`; 出口 `WebErrLogHandler` / `NotifyHandler` 按「层 × 档位」收放 ——
  **通道层的静默子类只进后端 log**, 不进前端错误历史、不弹通知。
- **可分辨边界**: `ChannelStatus` 增「被拒接触」面(401/403; 不污染 `last_contact_ts`); 401 日志由每分钟 ERROR
  改为状态变化 + 6h 的 WARNING; 通道静默文案按 `rejected` / `web_active` / `none` 三档分叉, 不再用一句问句让用户猜。
- **WebUI 活跃信号**: 判据取「WebUI 是否活跃」单信号(不判断同机/同源) —— 活跃 ⇒ 可见告警, 不活跃 ⇒ 静默。
- 基线: [testing/baselines/26-10-09-0931-hr-fault-domain.md](../testing/baselines/attachments/26-10-09-0931-hr-fault-domain.md)(2836 passed)。
