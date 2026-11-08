# 数据层与状态

> 摘要: TorrentStore 独占种子数据与 rid 增量同步、QbApi 门面、配置加载与 fail-fast 校验单点、state_file 结构与持久化。
> 触发: 数据层, store, TorrentRecord, rid, 增量同步, maindata, 变化集, QbApi, 配置加载, BaseLoader, validate_config, state_file, StateService

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

- **主要键**: `exec_history`(`{rule}:{hash}` → ts/date/hour, execute_once/cooldown 去重依据, `record_execution` 写) / `auto_categories`(自动设置过的分类) / `skip_check_day` / `recheck_fails` / `skip_check_backup`(跳检删除前的 .torrent 元数据, 仅失败/崩溃时保留作手动恢复凭据) / `speed_limit_curve` / 各模块自有键。
- **load 三态**: dict 可用 / None 不存在(首启, 静默) / 损坏(存在但非法 JSON/非 dict/非法 UTF-8)。损坏时记 WARNING(**原样保留不删**)并回退 `.bak`(每次写盘前复制的上一代内容), 自愈写回主文件(刻意不带 keep_backup —— 防止把损坏内容复制成新 .bak 盖掉唯一好备份); 备份也不可用才返回 `{}`。`OSError` 故意不吞 —— 环境问题不是内容问题。
- **持久化时机**: 周期 `maybe_flush` + 优雅退出 `save` + 两键写点直落, 全景见 main-loop-queue.md 落盘节。**热重载不重读 state** —— 内存态即真相, 磁盘只有上次快照, 重读等于回滚运行期状态(守阵 `test_apply_new_config_l2_preserves_runtime_state`)。
- **启动清场**: `cleanup_orphan_tmp` 在 `QbManager.__init__` **持锁之后**调用, 清崩溃遗留的 `<state_file>.<随机>.tmp`; 只认这一个形状, `.bak` 不碰; 无锁只读模式不调用。
- **启动兼容校验**: 全量轮(`need_validate`: 首轮/rid 失效/降级)对样本校验 `REQUIRED_TORRENT_FIELDS`, 缺失抛 `QbCompatError` 干净退出 —— 动机: 快照字段缺失会**静默零值**, 规则基于假数据决策比崩溃更危险; 增量轮不校验(响应只含变化字段, 必误报)。
