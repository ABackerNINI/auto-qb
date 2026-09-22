# qB API 与数据层

> 摘要: qB 版本差异、`sync/maindata` 增量语义、`TorrentRecord` 的唯一所有权 —— 改数据层前必读。
> 触发: 改 qbapi, 改 store, 改 TorrentRecord, 改 apply_sync, 加种子字段, 全局限速, qB 状态

### qB 5.0+ 全局限速: `app.preferences` 的限速字段**已静默失效**

- **触发**: 读写全局限速。
- **判别**: 必须走 `transfer_upload_limit` / `transfer_set_upload_limit`(**bytes/s, 0=不限**);
  `app.preferences` 的 `upload_limit` / `download_limit` 已失效。
  另: qbittorrent-api 新版 `app.preferences` 是 **property 不是方法**。
- **处置**: 一律走 transfer 端点。

### qB 状态枚举: 用 `is_*` 属性判定, 不要比较 state 字符串

- **触发**: 判断种子状态。
- **判别**: `pausedUP` / `stoppedUP` **跨版本漂移** ⇒ 用 `qbittorrentapi.TorrentState` 的 `is_*`。
  ❗ 仿真数据里 `"errored"` **不是合法状态名**(解析成 UNKNOWN、**缺文件扫描完全不触发**),
  合法名是 `"error"` / `"missingFiles"`。
- **处置**: 一律 `is_*`; 写仿真语料时核对状态名。

### `sync/maindata` 是增量接口, 单次响应不是种子全集

- **触发**: 改 `TorrentStore._apply` / sync 解析。
- **判别**: rid 匹配时只回**变化种子的变化字段**; 删除列在 `torrents_removed`; 新增种子回全量;
  rid 不匹配 / 为 0 时 `full_update=true`(自愈信号, 漏 tick / qB 重启只退化成一次全量)。
  ⇒ `_apply` 必须区分 **full**(以响应为全集)与 **delta**(只改 `patches`、删除以 `torrents_removed` 为准)。
- **处置**: ❗**全量轮不可早退** —— `full=True` 时即使 `patches` 为空也要走完(需检测删除)。
  ❗**rid 在 POST body**, 只解析 query 恒得 0 ⇒ **永远退化全量**。

### sync 响应的 hash 是 `torrents` 字典的**键**, 值内不含 hash

- **触发**: 写 sync 的字段校验 / 测试替身。
- **判别**: 直接把 `torrents[h]` 当校验样本会报"缺少字段: ['hash']"并抛 `QbCompatError`(**启动即退**)。
- **处置**: 校验前必须补齐 `{**patch, "hash": h}`;
  ⚠ **测试替身同样不能在值里塞 hash**, 否则掩盖该 bug。

### sync 与 `torrents/info` 字段齐平, 但**只能在全量轮校验**

- **触发**: 复用 `REQUIRED_TORRENT_FIELDS` 做 sync 校验。
- **判别**: 两者同一 C++ 序列化器 ⇒ 字段齐平可复用; 但**增量响应只含变化字段**, 做存在性校验必误报。
- **处置**: 校验由 `store.need_validate` 闸门隔离(只在全量轮);
  `missing_torrent_fields` 必须**同时支持 dict(按键)与对象(`hasattr`)**。

### sync 不可降级为"少几个字段": 只捕获两类异常

- **触发**: 改 `apply_sync` 的异常处理。
- **判别**: 旧 qB 无该端点抛 `NotFound404Error`, 替身缺方法抛 `AttributeError` ——
  `apply_sync` **只**捕获这两类并降级 `torrents_info()`。
- **处置**: 其它异常(网络 / 鉴权)必须 rid 归零后**原样上抛**, 否则掩盖断连。

### `TorrentRecord` 是唯一数据所有者, 不要再引入投影视图

- **触发**: 想给种子数据加一层视图 / 缓存对象。
- **判别**: 现有结构是快照字段存 slots, 非快照字段(`RE_ADD_FIELDS`)存 `_raw` + `__getattr__`,
  `apply_delta` **只遍历 patch 的键**。
- **处置**: 新增字段 —— 快照字段进 `_SNAPSHOT_FIELDS`, 其余进 `_raw` **自动生效**; 别另起投影。

### `apply_delta` 返回**变化字段集**而非 bool

- **触发**: 改 `apply_delta` 返回值 / 下游消费。
- **判别**: 下游据此把 O(N) 扫描降为 O(变化数)。变化集对视图字段按 `_VIEW_QUANTUM` 量化后比较 ⇒
  `seeding_time` 秒级递增**不进**变化集(但仍写入 slot)。
- **处置**: 别把它改成 bool; 加视图字段时同步考虑量化。

### `dirty_groups` 跨轮累积, 不能用 `_apply` 清空

- **触发**: 改脏标记清理时机。
- **判别**: 轮次外的写操作发生在 `_check_download_conflicts` **之后** ⇒ 清早了会丢脏标记。
- **处置**: `store.rounds_applied == 0` 时**退回全量扫描** —— 别删这个兼容分支,
  否则直接调用该方法的测试会**静默不再暂停**。

### 本地 qB 关闭 requests `trust_env`

- **触发**: 改客户端构造 / 代理相关。
- **判别**: 本地地址经 `qbmanager._new_client()` 构造 `LocalQbClient`(覆盖 `_session` property,
  每次返回前强制 `trust_env=False`), 跳过每请求代理 / netrc 解析; 远程域名用原生 `Client`。
  ❗ 旧写法 `client._session.trust_env = False` **从未生效** —— `_session` 是**只读 property**,
  且 `build_base_url()` / `_initialize_context()` 会**重建 Session**。
- **处置**: 本地判定取 `base_url` **解析后的 hostname**; 覆盖点必须落在 property 上。

### `yaml.BaseLoader`: 配置全是字符串, 不要假设已给原生类型

- **触发**: 读配置段。
- **判别**: 空段(如空 `trackers:`)会解析成 `None` / `str`。
- **处置**: 新增类似段同样要防; 别用 round-trip loader 的语义去比较(BaseLoader 下 `true` 是字符串)。
