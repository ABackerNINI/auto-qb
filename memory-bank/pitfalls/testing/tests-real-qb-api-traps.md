# tests-real 手工压测的 qB WebAPI 陷阱集

> 摘要: 手工压测/relocate 取证直接打 qB WebAPI 时的五类坑 —— 短 hash 静默 200、renameFolder 账面级假成功(ENOENT 也算成功且零日志)、addTrackers 参数是单数 hash、FakeTracker 的 peer 表是构造时静态注入、lib/bencode.decode 返回 (值, pos) 元组
> 触发: tests-real, 手工压测, renameFolder, renameFile, addTrackers, FakeTracker, 短hash, 静默200, bencode decode, 真机实验, relocate 取证, 内存盘, R 盘
**Refs:** memory-bank/issues/26-11-05-0420-bug-relocate-zero-move.html

### 短 hash 调 WebAPI 被静默忽略(HTTP 200 零效果)

- **触发**: 用 8 字符短 hash 调 `/torrents/setLocation`、`/torrents/start` 等 POST 端点(qB 5.2.3)。
- **判别**: 回执 200 + 空 body,但种子毫无变化、日志零条目 —— 与「bogus hash 静默 200」同形,极易误判为「下发成功但 qB 没执行」。
- **处置**: 一律用全 40 位 infohash(`torrents/info` 取回的 `hash` 字段);封装层(`lib/qb.py`)收短 hash 时应拒跑。

### renameFolder/renameFile 的「账面级假成功」与零日志

- **触发**: 对磁盘文件名与账面名错位的种子(如 `.!qB` 冻结态)调 renameFolder/renameFile —— libtorrent 对源文件 stat 不到(ENOENT)时**照样返回成功**,只改账面映射不动磁盘(`storage_utils.cpp:343` 注释原文 "just succeed and change the filename")。
- **判别**: HTTP 200 但磁盘 listing 零变化;qB 主日志对 rename 全程零条目(成功也不写)。
- **处置**: rename 的成败判定**只认磁盘证据**(目标路径出现/消失 + 后缀有无),不认 HTTP 200 与账面;两步改名之间必须等磁盘证据(内存盘 <1ms,机械盘亚秒),不能盲发。

### addTrackers 的参数名是单数 `hash`

- **触发**: `/torrents/addTrackers` 用 `hashes=` 传参 → HTTP 400 Bad Request(其余多数端点是 `hashes`)。
- **判别**: 400 且 body 为空;`urls` 还要求**换行分隔**的 tracker 列表(单个也要带 `\n`)。
- **处置**: `{"hash": <40位>, "urls": url + "\n"}`;`lib/qb.py` 未封装该端点,手调时注意。

### FakeTracker 的 peer 表是构造时静态注入,announce 不自动注册

- **触发**: `FakeTracker().start()` 后直接给双侧种子用 —— tracker 回给 announce 者的 peer 列表**永远是构造参数 `peers`**,双实例互连必须显式注入对端 `(local_host(), BT监听口)`(36595=26803 / 36596=60539)。
- **判别**: 双方 tracker status=2(已 announce)但 `num_peers=0`,互传建立不起来,零字节。
- **处置**: `FakeTracker(interval=3, peers=[(ip, 对端BT口), ...])`;BT 监听口以 `env_registry.bt_listen`/real.env 为准。

### lib/bencode.decode 返回 (值, 新位置) 元组

- **触发**: 拿 `decode(raw)` 当纯值用(如 `dict(decode(raw))` 改 .torrent 的 announce 字段)。
- **判别**: `TypeError: 'tuple' object does not support item assignment` 或 `dictionary update sequence element #0 has length 1`。
- **处置**: 用 `decode_all(raw)`(返回纯值);元数据注入类操作记得外层 dict 是可变的,内层嵌套结构仍是共享引用,改前 deepcopy。
