# 07 测试指南

## 运行

```bash
# 项目 venv (.venv, Python 3.12), 基线: 604 passed ~1s, 分支覆盖率 95%
.venv/Scripts/python.exe -m pytest tests -q                 # pytest.ini 已带 --cov=src --cov-report=term-missing --cov-branch
.venv/Scripts/python.exe -m pytest tests/test_grouping.py -q
.venv/Scripts/python.exe -m pytest tests/test_checking.py -q -k "skip"   # 按关键词
```

- `pytest.ini`: `pythonpath = src` (无需安装包), `testpaths = tests`, addopts 含覆盖率 → 每次 pytest 输出 coverage 表 (会稍慢, 调试单个测试可加 `--no-cov`)。
- 测试**全部使用 Fake, 不连真实 qBittorrent**, 可随时全量运行。
- 覆盖率现状 (cov-report.txt): 总 94%; 低洼: `logging.py` 58% (文件 handler 分支), `cli.py` 76%, `qbapi.py` 85% (store 为 None 的分支); 近乎全绿: utils 99%, episodes 99%, conditions 98%, taskqueue 98%, rule_engine/grouping/tags 94-100%。补测试优先看 term-missing 输出。

## 测试文件约定

1. **每个测试文件头部 docstring 维护 "## 测试计划" 清单** — 项目明文规定: 新增测试必须同步更新对应文件的清单 (README 也强调)。
2. 文件名与被测模块对应 (`test_actions.py` ↔ `rules/actions.py`); 一个模块可以有多个文件 (如 test_rules_core/test_rule_base/test_rule_engine 拆分)。
3. 测试粒度小而多 (582 个), 名字用中文/英文短语描述场景。

## tests/helpers.py 基础设施 (写测试前必读)

### Fake 对象

- **FakeClient**: 模拟 qbittorrentapi Client。记录所有调用到 `calls` 列表 (断言用, 如 `("add_tags", tags)`); `tags` set / `category` / `torrents` (dict: hash→FakeTorrent) 是可变状态; `torrents_delete_tags` 模拟真实行为 (同时从所有种子移除); `files_map` 按 hash 返回文件列表 (分组测试); `files_calls` 计数 (断言不再全量拉文件列表); `add_error` 模拟重加失败。
- **FakeTorrent**: 鸭子类型兼容 `TorrentRecord`/`TorrentDictionary` (快照字段一致 + `tags_set`/`state_enum`/`tracker_name`/`log_repr` + `trackers_info(client)`/`files(client)` 惰性接口)。**`state_enum`/`tags_set` 是属性不缓存** — 测试常直接改 `.state`/`.tags` 后重跑动作。默认: hash="HASH123", state="stalledUP", save_path=r"R:\Downloads", size/downloaded=100MiB。
- **FakeTracker**: name="HHan", domains=["tracker.hhanclub.net"], tags=["HHan"], hr/rules/limits 可注入。
- **FakeConfig**: 类属性默认全关 (grouping.enabled=False, add_episode_tags=False 等); 测试按需覆盖实例属性。

### 构造函数 (最常用)

- **`make_manager(state_file, tracker_rules=None, tracker_kw=None)`**: 建 FakeConfig + QbManager (不连客户端) + 注入 3 条示例规则集 `example_rules` (add_site_tag/hr_done/stop_low_ratio, 分别覆盖 never+变量/`satisfied`+daily/`once`+action-failed) + `_load_rules()` (run() 才自动加载, 测试须手动)。
- **`make_ctx(mgr, tor, client, dry_run=False)`**: 构造 RuleContext。保证: ①client 绑定到 mgr (动作走 QbApi 门面) ②tracker_conf 已匹配 ③**对象身份直写** `store.by_hash[hash] is tor` — 后续改 `tor.xxx` 属性对 `ctx.torrent` 实时可见 (无需重建)。
- **`seed_store(mgr, torrents=None)`**: 把种子灌入 store (对象身份保留, 语义同 refresh 的 diff), 返回 (added, removed)。
- **`_hr_rule(**kw)`**: 默认 3D@70%+12H 的 HRRule。

### 典型测试模式

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

- 事件驱动测试: 改 tor 状态 → `seed_store` 两次 diff 造 added/removed, 或直接调 `_handle_removed_torrents` 等私有方法。
- 快照同步测试 (test_snapshot_sync.py): 断言 FakeClient 调用后 store 内字段同步变化。
- 校验轮询测试: 手动调 `poll(task, dry_run)` 或推进 task_queue。

### 注意

- `FakeTorrent.tracker_conf` 默认 None — 需要变量替换 (`${required_seeding_time}`)/HR 判定的测试要传 tracker_conf (含 hr) 或依赖 make_ctx 自动匹配 (FakeTracker 带 hr)。
- `FakeConfig.check_missing_files = False` 但 `GroupingConfig` 实际字段是 `check_missing_files` — 分组测试记得开 `mgr.config.grouping.enabled = True` (+ check_missing_files)。
- helpers 在未安装 qbittorrentapi 时降级 (`TorrentState=None`), 但项目 venv 已装, 一般无需考虑。
