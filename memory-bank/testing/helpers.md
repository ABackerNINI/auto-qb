# tests/helpers.py 基础设施

> 摘要: 全 Fake 测试基座的四个替身 + 本地假 qB 服务 + 四个最常用的构造函数 —— 写测试前必读。
> 触发: 写测试, helpers, FakeClient, FakeTorrent, FakeQbServer, make_manager, make_ctx, seed_store, 替身

## Fake 对象

### `FakeClient` —— 模拟 qbittorrentapi Client

- 记录所有调用到 `calls` 列表(断言用, 如 `("add_tags", tags)`)。
- `tags` set / `category` / `torrents`(dict: hash→FakeTorrent)是**可变状态**;
  `torrents_delete_tags` 模拟真实行为(同时从所有种子移除);
  `files_map` 按 hash 返回文件列表(分组测试); `files_calls` 计数(断言不再全量拉文件列表); `add_error` 模拟重加失败。
- **`sync_maindata(rid)` 忠实模拟 qB 增量语义**(内部 `_sync_rid` / `_sync_snapshot`, 返回 diff 字段 /
  `torrents_removed` / `full_update`; 用 `sync_calls` 计数而**不写 `calls`** —— 避免破坏既有调用序列断言)。
- **种子控制方法齐全**(2026-09-13 补 `pause` / `resume`): 缺方法时 Web 命令执行路径会直接 `AttributeError` 暴露 ——
  此前 Fake 缺这两个方法, 导致组级 / 单种子暂停开始命令在 Fake 环境不可端到端验证(只能测到路由与入队)。
- **记法约定**: `start` / `stop` / `recheck` / `reannounce` 记 `None`(**历史断言依赖, 勿改**),
  新增的 `pause` / `resume` 记 hash 列表(便于断言"整组 / 单种"作用范围)。

### `FakeTorrent` —— 鸭子类型兼容 `TorrentRecord` / `TorrentDictionary`

- 快照字段一致 + `tags_set` / `state_enum` / `tracker_name` / `log_repr` + `trackers_info(client)` / `files(client)` 惰性接口。
- **`state_enum` / `tags_set` 是属性不缓存** —— 测试常直接改 `.state` / `.tags` 后重跑动作。
- 默认: `hash="HASH123"`, `state="stalledUP"`, `save_path=r"R:\Downloads"`, `size` / `downloaded` = 100MiB。

### `FakeTracker` / `FakeConfig`

- `FakeTracker`: `name="HHan"`, `domains=["tracker.hhanclub.net"]`, `tags=["HHan"]`, hr / rules / limits 可注入。
- `FakeConfig`: 类属性默认**全关**(`grouping.enabled=False`, `add_episode_tags=AddEpisodeTagsConfig()` 等);
  测试按需覆盖实例属性。

## 本地假 qB 服务(`FakeQbServer`, 2026-09-14 新增)

- **`FakeQbServer(client=None, abort=False)`**: 标准库 `ThreadingHTTPServer`(线程)+ 随机回环端口,
  `with` 进入 / 退出保证回收; 数据来源是内部 `FakeClient`(**单一口径**), 服务端只做 HTTP 适配。
- **用途**: 让测试用**真实** `qbittorrent-api` Client 走完整 HTTP 往返 —— 专门覆盖替身永远暴露不了的行为
  (session / `trust_env` / 库内部重建 Session / rid 增量语义)。典型: `test_local_qb_service.py`(6 测)与
  `test_ui.py::test_connect_failure_throttles_logging`。
- **端点**: POST `auth/login`; HEAD 任意路径(库会先探测协议); GET `app/webapiVersion` / `app/version`;
  **路由分派不按方法区分读端点**(库对 `info` / `files` / `trackers` / `maindata` 用 POST,
  对 `tags` / `categories` / `transfer` 用 GET), 参数合并 body 与 query;
  未列出的 GET → 404 JSON, 未列出的 POST → `"Ok."`。
- **`abort=True`**: 收到任何请求即断开(不写响应)—— 确定地制造 `APIConnectionError`(实测回环约 0.7s/次),
  用于连接失败节流类测试; **不要用"指向死端口"代替**(部分环境是超时等待, 库内超时重试曾使该测试耗时 74s 而被 skip)。
- **辅助**: `srv.port`(接配置)、`srv.client`(预置种子 / 断言写调用)、
  `srv.hits(endpoint)`(端点命中次数, 可断言"每 tick 只拉一次 sync"或"节流生效")、`srv.requests` 台账。
- **限制**: 写端点只回 `"Ok."` **不改 FakeClient 状态**(不做忠实状态机);
  需要状态流转的测试请继续用进程内 `FakeClient` 替身。

## 构造函数(最常用)

- **`make_manager(state_file, tracker_rules=None, tracker_kw=None)`**: 建 FakeConfig + QbManager(不连客户端)
  + 注入 3 条示例规则集 `example_rules`(`add_site_tag` / `hr_done` / `stop_low_ratio`,
  分别覆盖 never+变量 / `satisfied`+daily / `once`+action-failed)+ `_load_rules()`
  (**`run()` 才自动加载, 测试须手动**)。
- **`make_ctx(mgr, tor, client, dry_run=False)`**: 构造 `RuleContext`。保证:
  ①client 绑定到 mgr(动作走 QbApi Facade)②`tracker_conf` 已匹配
  ③**对象身份直写** `store.by_hash[hash] is tor` —— 后续改 `tor.xxx` 属性对 `ctx.torrent` **实时可见**(无需重建)。
- **`seed_store(mgr, torrents=None)`**: 把种子灌入 store(对象身份保留, 语义同 refresh 的 diff), 返回 `(added, removed)`。
- **`_hr_rule(**kw)`**: 默认 3D@70%+12H 的 `HRRule`。

## 典型测试模式

```python
def test_xxx(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"), tracker_kw={...})
    tor = FakeTorrent(tags="a,b", state="pausedUP")
    mgr.client = FakeClient()
    seed_store(mgr, [tor])
    # 直接调用 mixin 方法 / 构造 ctx 跑动作 / 跑 mgr._refresh_torrents(...) 造事件
    ...
    assert ("add_tags", [...]) in mgr.client.calls
```

- **事件驱动测试**: 改 tor 状态 → `seed_store` 两次 diff 造 added / removed, 或直接调 `_handle_removed_torrents` 等私有方法。
- **快照同步测试**(`test_snapshot_sync.py`): 断言 FakeClient 调用后 store 内字段同步变化。
- **校验轮询测试**: 手动调 `poll(task, dry_run)` 或推进 task_queue。

## 注意

- `FakeTorrent.tracker_conf` 默认 `None` —— 需要变量替换(`${required_seeding_time}`)/ HR 判定的测试
  要传 `tracker_conf`(含 hr)或依赖 `make_ctx` 自动匹配(FakeTracker 带 hr)。
- `FakeConfig` 的类属性 `check_missing_files = False` 是**历史遗留**(真实配置在 grouping 段:
  `config.grouping.check_missing_files`, 默认 True)——
  分组测试记得开 `mgr.config.grouping.enabled = True`; 缺文件扫描由 `grouping.check_missing_files` 控制。
- helpers 在**未安装 qbittorrentapi 时降级**(`TorrentState=None`), 但项目 venv 已装, 一般无需考虑。
