# 数据层与状态

> 摘要: TorrentStore 独占种子数据与 rid 增量同步、QbApi 门面、配置加载与 fail-fast 校验单点、state_file 结构与持久化、流量采样 v4 存储与启动恢复。
> 触发: 数据层, store, TorrentRecord, rid, 增量同步, maindata, 变化集, QbApi, 配置加载, BaseLoader, validate_config, state_file, StateService, 流量存储, qb-traffic-v4, acc.dat, 流量恢复, raw_window, HourFold

## 种子数据: TorrentStore 独占 (torrents/ 包)

`torrents/`(store/record/view/compat)是种子数据的唯一所有者, 无中间投影视图。设计目标优先级: **速度 > 可读性 > 内存**。

- **TorrentRecord**(`torrents/record.py`, dataclass + slots): 快照字段名与 qB `TorrentDictionary` 完全一致(鸭子兼容); 惰性缓存槽(`_tags_set`/`_state_enum`/`_trackers_info`/`_files`); 非快照字段(跳检重加所需)存 `_raw` dict, `__getattr__` 兜底读。**对象身份跨轮不变** —— 增量轮只 patch 变化记录, 其余原样保留, 惰性缓存存活。
- **apply_delta(patch)**: 只遍历 patch 中的字段(增量轮成本 ∝ 变化字段数), 快照字段写 slot、其余写 `_raw`, 返回变化字段名集合。
- **惰性缓存**: trackers/files 首次访问才拉 API 并持久缓存(种子删除时随记录回收); all_tags/all_categories 全局缓存, 由 QbApi 写操作触发失效。
- **分组索引**: `groups`/`group_sizes`/`member_to_key`(O(1) 定位)/`state_since`(纯展示: 闸门文案「已 N 分钟」); 分组键 = (归一化 save_path, 排序后的文件相对路径元组)。
- **verified_references**: full-checking 通过的种子集合, **仅内存**(重启重新积累), 作同组跳检参考; 带跳检标签的种子被排除 —— 跳检未经哈希校验, 不可作参考。
- **确定性字段写后同步** `update_torrent_fields`(tags/category/限速/save_path); **state 不在此列** —— 运行状态只由 qB 同步驱动, 本地不写回。

## 增量同步 rid 语义 (torrents/store.py)

qB `/api/v2/sync/maindata`: rid 与上次一致时只回**变化种子的变化字段**, 删除列在 `torrents_removed`, rid 不匹配/为 0 回全量。**选型动机**: 每轮全量 `torrents/info` 要 qB 反复序列化全部种子, 库大时 CPU 明显上涨; **自愈性**: 漏 tick/rid 错位/qB 重启都只退化成一次全量, 不丢数据。

- `apply_sync(api)`: 拉取并应用; rid/need_validate/using_fallback 等同步态**内聚于 store**; `reset_sync()` 在重连/热重载时清基线强制下轮全量; 未知异常 rid 归零后原样上抛(主循环兜底)。
- **降级**: 端点不可用(旧版 qB/测试替身缺方法) → 回退全量 `torrents_info()`, 一次性 WARNING 去重, 语义与全量一致。
- **变化集驱动下游**: `delta_fields`(按 hash 的变化字段)/`state_changed`/`dirty_groups`(下载冲突待重算组, **跨轮累积**, 消费方取出并复位 —— 轮次外的写操作登记不丢)。下游由 O(全库) 扫描降为 O(变化数)。
- **字段齐平**: sync 与 `torrents/info` 共用 qB 同一序列化器, 快照字段在两种响应中等价存在。

## 客户端与 QbApi 门面 (core/qbclient.py, core/qbapi.py)

客户端构造单点 `new_client()`; 本地地址构造 `LocalQbClient`(强制 `trust_env=False`, 省每请求的环境代理/netrc 解析), 远程地址用原生 Client。所有对 qB 的调用统一走 `QbApi(client, store)` 门面(**store 必传**, 无"无 store"形态): 写方法调 raw client 后**同步 store 快照 + 失效相关缓存**; 读方法优先惰性缓存。dry_run 判定不在门面内, 由调用点负责。

## 配置: 加载与 fail-fast 校验 (config/)

- **加载**(`config/loaders.py:646` `load_config`): `yaml.BaseLoader` —— 标量**全为字符串**, 不自动转型。动机: 配置既被强类型消费端读取, 又要被 writer 按"读出来再写回去"完整保留用户格式(`config/writer.py` 同用 BaseLoader 保证 round-trip 无格式漂移); 类型转换只在加载层显式做(`_parse_*` 家族), 拒绝 YAML 隐式转型(版本号丢前导零/布尔意外等)。
- **校验单点**(`config/validation/core.py:280` `validate_config`): 全量校验并聚合返回错误列表, CLI 一次报完。**fail-fast 契约**: 校验之后的代码假定配置正确, 不再散布防御分支; **新配置键必须进 `validate_config` 并同步 `config/schema/`**(守卫测试强制)。配置键权威 = `config/schema/` + validate_config, 不存在第二份键清单。
- **schema 版本迁移**: 结构化落盘文件(config.yml/state.json/hr/<site>.json)统一带 `schema_version`, 框架单点 `infra/versioning.py`(CURRENT_VERSIONS + MIGRATIONS 相邻版本链, 每级恰好 +1, 纯函数; state 当前 v3)。口径: 字段缺失 = v1; 落后沿链迁移; 比程序新 fail-fast(**不算损坏**, 不触发 .bak 回退)。config 在 run() 开头由 writer 启动物化(磁盘落后才写, dry-run 只探测), 见 plans/26-09-27-2252-plan-config-migration-materialize.html。

## state_file: 结构与持久化 (core/state.py)

单点入口 `ctx.state.*`(StateService; `manager.state` 属性面永久保留, 运行期 dict 是同一对象)。JSON + 原子写(`infra/utils_paths.py` `atomic_write`: tmp + os.replace + 可选 .bak)。

- **主要键**: `exec_history`(`{rule}:{hash}` → ts/date/hour, execute_once/cooldown 去重依据, `record_execution` 写) / `auto_categories`(自动设置过的分类) / `skip_check_day` / `recheck_fails` / `recheck_cooldowns`(校验失败冷却窗口 `{hash: 失败时刻}`, rule 源 FAILED 记录, 校验成功全来源清除) / `skip_check_backup`(跳检删除前的 .torrent 元数据, 仅失败/崩溃时保留作手动恢复凭据) / `speed_limit_curve` / 各模块自有键。
- **load 三态**: dict 可用 / None 不存在(首启, 静默) / 损坏(存在但非法 JSON/非 dict/非法 UTF-8)。损坏时记 WARNING(**原样保留不删**)并回退 `.bak`(每次写盘前复制的上一代内容), 自愈写回主文件(刻意不带 keep_backup —— 防止把损坏内容复制成新 .bak 盖掉唯一好备份); 备份也不可用才返回 `{}`。`OSError` 故意不吞 —— 环境问题不是内容问题。
- **持久化时机**: 周期 `maybe_flush` + 优雅退出 `save` + 两键写点直落, 全景见 main-loop-queue.md 落盘节。**热重载不重读 state** —— 内存态即真相, 磁盘只有上次快照, 重读等于回滚运行期状态(守阵 `test_apply_new_config_l2_preserves_runtime_state`)。
- **启动清场**: `cleanup_orphan_tmp` 在 `QbManager.__init__` **持锁之后**调用, 清崩溃遗留的 `<state_file>.<随机>.tmp`; 只认这一个形状, `.bak` 不碰; 无锁只读模式不调用。
- **启动兼容校验**: 全量轮(`need_validate`: 首轮/rid 失效/降级)对样本校验 `REQUIRED_TORRENT_FIELDS`, 缺失抛 `QbCompatError` 干净退出 —— 动机: 快照字段缺失会**静默零值**, 规则基于假数据决策比崩溃更危险; 增量轮不校验(响应只含变化字段, 必误报)。

## 流量采样存储与启动恢复 (traffic_store*.py, core/modules/traffic_sample_*.py)

采样模块(`traffic_sample_mod`)的持久化面 = `<data_dir>/qb-traffic-v4/`: `global/`+`torrents/<infohash>/` 两级系列目录放 raw 天文件(`<日期>.dat`, B/r/z/n 文本行, 追加)与各系列 `agg.dat`(hour/day/month 封口行, 追加 + hour 按 rollup_window 裁剪重写); **根级 `acc.dat`** = 快照账本(2026-11-21-1546 新增)。恢复/封口/快照全在主循环线程, 唯一新线程 = 清理 daemon。

- **启动恢复(换代机制, 计划 plans/26-11-21-1546-plan-traffic-recovery.html)**: 旧机制(全量逐槽展开 + 水位过滤后置 + 累计器不落盘)已退役。现为**快路优先两级**: ①acc 账本整读 + 逐系列 agg.dat 指纹 stat 探针(size+mtime_ns)匹配 → 直采折叠态与游标, 零 agg 读零 raw 读; 游标 R3 两向: raw 尾 ≤ 游标 = 缓冲信用已在账本, raw 尾 > 游标 = 尾块轻量读回放 (游标, raw 尾] 尾段。②失配/缺失/损坏 = **该系列** fallback B1+B2(单系列隔离不放大): B1 字节级块定位(`\nB,` 扫块头, 只解析开放段 —— 水位封口块跳过解析与入账) + B2 游程级闭合式入账(成本 ∝ 行数, 与 `v4_block_slots` 逐位同式); 快照是加速器不承载正确性(D9)。
- **acc 账本语义**(组件单点 `core/traffic_store_acc_ledger.py`): 每变化系列一行追加(flush 随批 / stop 全系列终态行, last-wins; 撕裂尾跳过取上一有效行), 版本头行门闩(失守 = 整本无效全体 fallback —— 升级首启自举: 全体 fallback 重建后首轮 flush 补写账本行), 超 16MB 压实重写(tmp+fsync+os.replace 唯一重写点); 硬序 = agg 封口 append 成功后才写 acc 行(账本行不得领先 agg 现状, 失败系列下轮自愈)。
- **HourFold 折叠态**(traffic_sample_common.py): 开放小时内存表示从逐记录样本列表换成定长 fold 累计器(`merge`/`seal` 与 `v4_hour_agg` 同数学, 封口行 bitwise 等价, D2 对拍守阵钉住) —— 序列化 O(1)/系列(~300B), 这是 acc 账本可行的前提(D12)。
- **raw 保留窗清理**(raw_window 删除半边, D13/D14): 保留下界 = `raw_window` 天数 + 3 日界余量(单点 `v4_raw_keep_floor_date`, 盖读侧 24h 窗「常态 3/边角至多 4」个天文件与恢复复读 ≤2 文件, 不变量「保留下界 ≤ 读侧最大回看起点」守阵钉住); 清理 daemon(启动恢复完成后 spawn 一次 + flush 时点每日闸 ≤1 次/天, 自终止不持共享结构, 删除目标年龄与主线程写面结构性不相交), OSError 跳过下轮重试。首轮清扫删超窗天文件 = 已接受破坏点(D15: 聚合行全保留)。
- **实测数字单点**: reports/26-11-21-1650-report-traffic-recovery-s0.html(§05: S5 真机四判据与 236 生产对照实测, 具体数值以该报告为准)。
