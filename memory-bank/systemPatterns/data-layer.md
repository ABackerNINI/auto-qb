# 数据层 (TorrentStore / 增量同步)

> 摘要: `torrents.py` 的增量同步、变化集与 `TorrentStore` —— rid 语义一处说清。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: 数据层, store, 增量同步, maindata, rid, 变化集, apply_sync

## 增量同步 (torrents.py, 2026-09-13)

**动机**: 原先每 tick 全量 `torrents/info`, qB 端必须反复序列化**全部**种子 (~45 字段 × N), 种子库大时 qB CPU 明显上涨。改走 qB 自带 WebUI 同款的 `/api/v2/sync/maindata`:

- **qB 端语义** (`src/webui/api/synccontroller.cpp`): rid 与上次一致时只回**变化种子的变化字段** (`processMap` 逐字段 diff), **未变化种子完全不出现在响应中**; 删除的种子列在 `torrents_removed`; 新增种子(基线缺失)回全量字段; rid 不匹配/为 0 时 `full_update=true` 回全量。**自愈性**: 漏 tick/rid 错位/qB 重启都只会退化成一次全量, 不会丢数据。
- **字段齐平**: sync 与 `torrents/info` 共用同一 C++ 序列化器 `serialize/serialize_torrent.{h,cpp}` (sync 仅额外移除 `"id"` 键) —— 故 `REQUIRED_TORRENT_FIELDS` 全部字段(含 `share_limit_action`/`inactive_seeding_time_limit`)在 sync 响应中同样存在。
- **`TorrentStore.apply_sync(api)`**: 拉取一轮并应用; `rid`/`need_validate`/`using_fallback`/`validate_sample` 等同步态内聚于 store(无独立同步对象); `reset_sync()` 在重连/热重载时清基线强制下轮全量; 未知异常 rid 归零后原样上抛(由主循环兜底)。
- **`_apply(patches, removed, full)`**: 增量时只对 `patches` 中的记录调 `TorrentRecord.apply_delta`(其余记录原样保留 —— 对象身份跨轮不变, 惰性缓存存活); 全量时以响应为全集重建(未出现者视为删除)。**无变化轮提前返回, 不重建 `by_hash`**。
- **单调基数据归属**: 快照字段存 `TorrentRecord` 的 slots(C 级属性访问); 非快照必需字段(`RE_ADD_FIELDS`, 跳检重加用)存 `_raw` dict, 属性访问经 `__getattr__` 兜底(缺失抛 `AttributeError`, 与 `AttrDict` 语义一致, 故 `hasattr` 版本校验照常工作)。
- **降级**: 端点不可用(旧版 qB / 测试替身缺 `sync_maindata`) → 捕获 `AttributeError`/`NotFound404Error` → 回退全量 `torrents_info()`(一次性 WARNING 去重), 语义与改造前一致。

### 本轮变化集 O(变化数) 驱动下游

`store` 在应用时顺手收集变化集, 使下游 O(N) 扫描可以按变化数进行(2026-09-13 性能修复):

| 字段 | 含义 | 消费方 |
|------|------|--------|
| `delta_fields` | `{hash: 变化字段名集合}` | `_handle_save_path_changes`(只看 save_path 变化) |
| `state_changed` | `[(hash, fetch 时 state_enum)]` | `_handle_state_transitions`、`_dispatch_events` 状态变化分支 |
| `dirty_groups` | 需重算下载冲突的组 key | `_check_download_conflicts`(登记于字段变化/成员增删/归组/自有停种打标) |

`dirty_groups` 跨轮累积(`_apply` 不清空), 由 `_check_download_conflicts` 取出并复位 —— 故轮次外的写操作(Web 命令/任务队列)登记不会丢。`rounds_applied` 为 0(直接驱动该方法的白盒测试/外部调用, 无变化集)时退回全量扫描。

**本地 qB 跳过 env/netrc 解析** (2026-09-14 修复为真正生效): `_new_client()` 对本地地址(`127.0.0.1`/`localhost`/`::1`, 取 `base_url` 解析后的 hostname 判定)构造 `LocalQbClient`(Client 子类, 覆盖 `_session` property 强制 `trust_env=False`), 省掉每请求的 `get_environ_proxies`/`get_netrc_auth`(环境代理与 `~/.netrc` 解析; 实测单请求 0.276ms -> 0.043ms); 远程地址用原生 `Client`(企业代理/`~/.netrc` 可能真实需要)。旧实现 `client._session.trust_env = False` **从未生效**(库在首次请求/登录重建时丢弃 Session), 详见 [pitfalls.md](../pitfalls.md)。

## 数据层 TorrentStore (torrents.py)

设计目标优先级: **速度 > 可读性 > 内存**。

- `TorrentRecord` (dataclass, slots): 种子数据的**唯一所有者**(无中间投影视图)。快照字段名与 qB `TorrentDictionary` 完全一致 (鸭子兼容), 外加惰性缓存槽 `_tags_set`/`_state_enum`/`_trackers_info`/`_files`、非快照字段容器 `_raw`、以及 `tracker_conf` (匹配结果引用)。派生属性: `tags_set`(frozenset), `state_enum`(TorrentState 枚举, **有缓存**, 按类别判定与 qB 版本无关), `log_repr`, `tracker_name`。`__getattr__` 从 `_raw` 兜底读非快照字段(如跳检所需 `seq_dl`/`ratio_limit`)。
- `apply_delta(patch) -> frozenset[str]`: **只遍历 patch 中的字段**(增量轮成本 ∝ 变化字段数: Mapping 源走 `.items()`, 真机 `TorrentDictionary` 因此走 C 级迭代); 快照字段写入 slot, 非快照字段写入 `_raw`; 返回**变化字段名集合**(视图字段按 `_VIEW_QUANTUM` 量化后比较)。`from_torrent(tor, hash=)` 为构造入口。
- `apply_sync(api)`: 主循环入口(增量); `refresh(tors)`: 全量入口(测试/降级路径); 二者共用 `_apply`。
- **视图展示字段 `_VIEW_FIELDS`**: name/save_path/state/dlspeed/upspeed/uploaded/size/progress/seeding_time/ratio/tags/category/added_on (与 `_build_group_view` 取值集合一致); 其余快照字段(如 downloaded/dl_limit)变化**不**置脏 `view_changed`(但仍计入 `delta_fields`)。`view_dirty(changed)` 判定变化集是否触及视图。**`tags`/`category` 自 2026-09-14 起计入**(组级“共同标签/共同分类”列的数据源): 随之 `update_torrent_fields` 的 tags/category 分支与 `apply_tag_removal` 均需置 `view_changed`(旧实现明确注释“不影响展示”, 改视图字段时容易漏掉这类写侧置脏)。**`added_on` 同批加入**(组级默认排序键; 同时加入 `_SNAPSHOT_FIELDS` —— 加快照字段必须同步 `tests/helpers.py` 的 `FakeTorrent._SNAPSHOT_FIELDS`, 否则 `REQUIRED_TORRENT_FIELDS` 版本校验会直接报缺字段)。
- **字段量化 `_VIEW_QUANTUM` + `view_field_value(field, value)`**: 该表内的字段按步长向下取整后再比较与展示 —— 目前仅 `seeding_time: 60`(秒级递增但前端只展示到分钟, 不量化会让做种中的种子每轮置脏, 惰性重建对绝大多数种子失效)。**重建判定与 `_build_group_view` 展示值共用同一函数**, 保证"视图内容"与"脏标记依据"不脱钩; 新增需量化的字段只需加进该表。
- **惰性缓存**: `trackers_info`/`files` 首次访问才拉 API 并持久缓存 (种子删除时随记录回收); 全局 `all_tags()`/`all_categories()` 缓存 + `invalidate_*()` (由 QbApi 写操作触发失效)。
- **分组索引** (GroupingMixin 直接读写): `groups[key]`/`group_sizes[key]`/`member_to_key[hash]`(O(1) 定位)/`state_snapshot`/`download_conflict_warned`。分组键 = `(path_normalize(save_path), 排序后的文件相对路径元组)`。
- **删除/恢复**: `remove_torrent(h)` 立即从 `by_hash` 摘除并登记 `_pending_removed`(下轮 added/removed 上报); `restore_torrent(rec)` 撤销登记并放回记录(跳检重加, 保留 tracker_conf/惰性缓存)。
- `verified_references: Set[str]`: full-checking 通过的种子, **仅内存** (重启重新积累), 作为同组跳检参考。注意: 带跳检标签 (标签名是全局配置 `config.skip_checking_tag`, 默认 zSkipChecked, 全局统一不按规则覆盖, 动作运行时经 ctx 读取; 跳检成功后打在种子上、跨重启) 的种子即便在此集合中, 也会被 `_find_reference` 排除 —— 跳检未经哈希校验, 不可作参考。
- `update_torrent_fields(...)`: 写后同步快照 (tags/category/state/限速/save_path), 保证同 tick 内后续读取一致。
