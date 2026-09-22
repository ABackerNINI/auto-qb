# 客户端 / QbApi / 状态持久化

> 摘要: 启动期兼容校验、`QbApi` Facade 与状态持久化 —— 三个小主题合成一份。
> 触发: QbApi, Facade, 兼容校验, 状态持久化, state_file, RuleEngineMixin

## 启动期版本兼容校验 (2026-09-06, 2026-09-13 调整)

`_refresh_torrents` 在**全量轮**(`store.need_validate`: 首轮/rid 失效/降级)对 `store.validate_sample` 校验 `REQUIRED_TORRENT_FIELDS` (快照字段 + 跳检重加字段, 共 27 个), 缺失抛 `QbCompatError(AutoQbError)` → tick 循环 `except AutoQbError: raise` 穿透"主循环异常"捕获 → CLI stderr 干净退出。

样本为 **qB 响应原始字段映射**: sync 路径取全量响应首个 patch dict 并**补回 `hash`**(值是 `torrents[hash]`, hash 只在键上 —— 不补会误报缺字段导致启动退出); 降级路径取首个非 dict 的真实种子对象 —— 测试注入的 plain dict 不作样本。`missing_torrent_fields` 因此支持两类来源: 映射按键判定(`f not in tor`)、对象按 `hasattr` 判定。**增量轮不校验** (响应只含变化字段, 校验必误报), 由 `need_validate` 闸门控制。通过后置 `_schema_validated` 不再重复 (qB 版本运行期不变); 空 qB 时样本为 `None` → 跳过。设计动机: 快照字段缺失会**静默零值** (规则基于假数据决策), 比崩溃更危险 —— qB 5.0 preferences 键漂移前科。

## QbApi Facade (qbapi.py)

所有对 qB 的调用统一走 `self.api` (不直接用 raw client):

- **写方法**: 调 raw client 后同步 store 快照 + 失效相关缓存 (add_tags/remove_tags/delete_tags/create_category/set_category/start(→stalledUP)/stop(→pausedUP)/set_upload_limit/set_download_limit/set_location/delete)。
- **读方法**: 优先 store 惰性缓存 (trackers/files/tags/categories); 快照缺 hash 时 trackers/files 回退 client; `torrents_info` 透传; `sync_maindata(rid)` 增量同步透传 (应用由 `store.apply_sync` 完成)。
- **store 必传**: `QbApi(client, store)` / `bind(client, store)` 中 store 为必传参数 (QbManager 恒持有数据层), 无"无 store 透传"形态 — 不为测试留专用通道 (见 06 可测试性原则)。
- **透传**: torrents_add / recheck / reannounce / piece_hashes / export / auth_log_in。
- **全局限速 (qB 5.0+)**: `get_global_speed_limits`/`set_global_speed_limits` 走 `transfer_*` 端点 (bytes/s), 不用 `app/preferences` 旧键 (已失效)。内部 KiB/s ↔ bytes/s 换算。
- dry_run 判定**不在Facade内**, 由调用点负责。

## 状态持久化 (RuleEngineMixin)

- `_load_state()`: JSON 读入 `self.state` (构造时 + run 时 + 热重载 L2 各一次); `save_state()`: **仅程序退出时**调用 (减少磁盘写入)。
- **损坏回退 (2026-09-22, issue 26-09-21-1347)**: `_load_state` 经 `_read_state_file` 判**三态** —— `dict` 可用 / `None` 文件不存在(首启, **静默**) / `_CORRUPT` 存在但非法 JSON、非 dict、非法 UTF-8(**损坏**)。损坏时记 WARNING(损坏文件**原样保留、不删**)并回退 `<state_file>.bak`(`save_state` 的 `keep_backup` 每次写盘前复制的上一代内容), 读到合法 dict 即用以 INFO 记「用了备份」, 并**自愈写回主文件**(刻意不带 `keep_backup`: 否则下次 `save_state` 会把损坏内容复制成新的 `.bak`, 把唯一一份好备份盖掉); 备份也不可用才返回 `{}` 并再告警说清后果。`OSError`(权限等)**故意不吞** —— 那是环境问题不是内容问题。备份后缀单点常量 `utils.BACKUP_SUFFIX`(写侧 `atomic_write` 与读侧共用)。
- **启动清场(同上 issue 的附带发现)**: `_cleanup_orphan_tmp()` 在 `QbManager.__init__` **持锁之后**调用, 清理 `<state_file>.<随机>.tmp`(崩溃落在 `mkstemp` 与 `os.replace` 之间的遗留, `atomic_write` 只清自己的异常路径)。**持锁才清**是硬前提(没锁 = 有别的实例在写); 只认这一个形状, `.bak` 与别人的 `.tmp` 不碰; `no_lock=True` 的只读模式不调用。
- `record_execution(rule_name, hash)`: 写 `state["exec_history"]["{rule}:{hash}"] = {ts, date, hour}` — execute_once/cooldown 去重依据。
- `begin_round(torrents)`: 维护 `state["upload_snapshots"][daily/weekly/monthly] = {key, baseline{hash: uploaded}}` — upload_size_today/week/month 条件的基线; 周期切换时清空重建。
- `upload_delta(torrent, kind)`: `max(0, uploaded - baseline)` (下限 0, 防种子重加/客户端重启归零导致负数)。
- 其它 state 键: `auto_categories` (自动设置过的分类, 判断能否覆盖), `speed_limit_curve` (当日曲线计算结果, 调试用), `skip_check_backup` (跳检删除前备份的 .torrent 元数据; 重加确认成功后清理, 仅失败/崩溃时保留作手动恢复凭据)。
