# Testing — 测试指南

> **单点事实源**: 全库的测试基线数字 (passed/skipped/覆盖率/耗时) 只在本文件维护 — README/AGENTS.md/progress.md 等一律引用此处, 更新基线时只改这里。

## 运行

```bash
# 依赖统一 uv 管理 (pyproject.toml + uv.lock, 2026-09-15 起); 首次/依赖变更后先 `uv sync`
# 基线: 1038 passed, 0 skipped, 0 failed (2026-09-19 实测 = 1036 + **架构审查 Wave 3/4 第二批** 2 项(`test_actions.py::test_stop_preserves_completeness` 暂停/恢复不得翻转完成位、`test_qbmanager.py::test_reconnect_backoff_and_reset` 重连指数退避与归零); 此前 1036 = 1022 + **架构审查 Wave 0/1/3/4 固化缺陷** 14 项: `test_utils.py` 原子写 3 项(`test_atomic_write_creates_file` / `test_atomic_write_failure_keeps_old_content` / `test_atomic_write_keep_backup`)、`test_checking.py` 跳检未确认也备份 1 项(`test_checking_skip_readd_unconfirmed_backs_up`)、`test_web.py` 密钥不进日志 + 配置树掩码 2 项(`test_web_token_not_printed_in_logs` / `test_config_tree_masks_secrets`)、`test_config_writer.py` 掩码还原 2 项(`test_mask_tree_hides_sensitive_scalars` / `test_unmask_tree_restores_from_disk`)、`test_config.py` 任务数范围校验 1 项(`test_validate_max_tasks_per_tick_range`)、`test_web.py` 视图并发原子发布 1 项(`test_views_published_atomically_when_rebuilt_concurrently`)、`test_tvshows.py` bare 集数 0 拦截 1 项(`test_bare_zero_not_episode`)、`test_conditions.py` HR 无站点判定 1 项(`test_hr_condition_no_tracker_conf`)、`test_web.py` 畸形分组 key 转 400 1 项(`test_api_group_malformed_key_returns_400`)、`test_notify.py` 免打扰不吃配额 + 去重表淘汰 2 项(`test_notify_quiet_hours_does_not_consume_quota` / `test_notify_throttle_dedup_table_evicted`); 此前 1022 = 1021 + 任务档案改名与索引生成化新增 `test_memory_bank.py::test_index_is_regenerated` 1 项; 1021 = 1018 + WEB UI **视图重建范围收口** 3 项(`test_flat_view_refreshed_by_main_loop_tick` / `test_rebuild_views_single_entry_point` / `test_api_state_status_carries_server_state`); 此前 = 1007 + **副作用记账器固化**(`tests/sidefx.py` 记账与判定策略 + `tests/test_sidefx.py` 10 项策略单测) + `test_notify.py` 1 项 "启用且不 mock" 真实路径回归; 此前 1007 = 1006 + **测试期禁止真实系统通知**(`tests/conftest.py` 会话夹具)新增 1 项 `test_notify_real_send_blocked_under_pytest`; 此前 1006 = 1001 + WEB UI **错误种子显示具体原因**(TASK015)5 项新测试: `test_error_reason_from_tracker_msg` / `test_error_reason_missing_files_without_api` / `test_refresh_error_reasons_budget_and_ttl` / `test_refresh_error_reasons_clears_when_recovered` / `test_refresh_error_reasons_skips_when_disconnected`; 此前 1001 = 1000 + `test_memory_bank.py::test_task_ids_and_slugs_are_unique` 1 项, 清理并行 worktree 造成的重复档案时新增的结构守卫; 此前 2026-09-17 实测 1000, uv 环境; 修复导出 .torrent 的 latin-1 头崩溃 + `test_content_disposition_encoding` 后 = 999 + 1; 此前 999 = 第十轮 996 + 3 项 fs 端点测试; WEB UI 第十轮 16 项修复后 = 996 + `test_open_path_select_file_per_platform` + `test_api_fs_dirs_endpoint` + `test_api_fs_mkdir_endpoint` 3 项; **第十一轮 7 项前端修复后复核同为 999**(无新增后端逻辑, 改动由静态守阵 + 双 UI 浏览器冒烟覆盖), 前端改动不影响单测, 双 UI 模板/CSS 由静态守阵 + 浏览器冒烟覆盖), 分支覆盖率 92%(ui.py 窗口/托盘本体不单测, 真机冒烟验证; WEB UI 端到端为后端单测 + 临时 Fake 服务浏览器冒烟; 真实 HTTP 栈的集成测试用 `helpers.FakeQbServer` 本地假服务, 不连真实 qBittorrent; 注意: test_ui.py::test_autostart_windows_registry 真写 HKCU 注册表, 沙箱化 shell 里会因写入受限失败, 常规终端应通过)
uv run pytest tests -q                 # pytest.ini 已带 --cov=src --cov-report=term-missing --cov-branch
uv run pytest tests/test_grouping.py -q
uv run pytest tests/test_checking.py -q -k "skip"   # 按关键词
```

- `pytest.ini`: `pythonpath = src` (uv sync 也会把项目 editable 装入 venv, 双保险), `testpaths = tests`, addopts 含覆盖率 → 每次 pytest 输出 coverage 表 (会稍慢, 调试单个测试可加 `--no-cov`)。
- 测试**基本全部使用 Fake, 不连真实 qBittorrent**(随时可全量运行)。唯一例外是 `test_local_qb_service.py` + `test_ui.py::test_connect_failure_throttles_logging`: 它们用 `helpers.FakeQbServer`(标准库 `http.server` 监听回环随机端口)承载**真实** `qbittorrent-api`/requests 栈, 因为"trust_env 是否真的生效"“库重建 Session 是否弄丢我们的设置”这类行为在进程内替身上根本无法暴露(历史教训)。
- 覆盖率现状 (2026-09-19 实测, 全量): 总 92%; 低洼: `ui.py`(GUI 本体真机冒烟不单测); 近乎全绿: `config/impact.py`/`config/schema.py`/`logging.py`/`registry.py`/`taskqueue.py`/`qbapi.py`/`speed_curve.py`/`tracker.py` 100%, `notify.py` 98%, `utils.py` 98%, `qbmanager.py` 96%, `tvshows.py` 94%, `web.py` 92%(较 2026-09-14 的 75% 提升: 架构审查 Wave 0 补了配置掩码/密钥日志/畸形 key 等分支), conditions 99%。补测试优先看 term-missing 输出。
- **耗时实测 (2026-09-19, 空载)**: `uv run pytest tests -q`(含 `--cov-branch`)≈ **32 秒**; 加 `--no-cov` ≈ **25 秒**。此前文档写的"约 12 秒"已过时 —— 另注意**不要并发起多个 pytest**: 本项目有绑定本地端口的 `FakeQbServer` 用例, 且 sidefx 守卫按**会话**记账(任何进程删了越界文件都会算到当前会话头上), 并发跑会出现假的失败。

> **图形化配置编辑器测试**: `test_config_schema.py`(UI 元数据与配置键/插件的**一致性守卫**, 20 项: 顶层键 vs `KNOWN_CONFIG_KEYS`、各段子键 vs `KNOWN_*_KEYS`、插件表 vs `registry`、kind/optional/enum 形态自检) 与 `test_config_writer.py`(结构化写回: 读取语义/校验拒绝不碰磁盘/注释与标量风格保留/增删键/R 级回退/预览不落盘/有损数字串不被规范化)。**新增配置键或插件时必须同步 schema.py**, 否则守卫测试直接失败。

## 测试文件约定

1. **每个测试文件头部 docstring 维护 "## 测试计划" 清单** — 项目明文规定: 新增测试必须同步更新对应文件的清单 (README 也强调)。
2. 文件名与被测模块对应 (`test_actions.py` ↔ `rules/actions.py`); 一个模块可以有多个文件 (如 test_rules_core/test_rule_base/test_rule_engine 拆分)。
3. 测试粒度小而多 (756 个), 名字用中文/英文短语描述场景。
4. **平台相关测试必须以 `monkeypatch` 固定平台** — GitHub Actions 跑在 Linux, 而本项目以 Windows 为运行环境。纯 Windows 行为 (如长路径 `\\?\` 前缀) 的测试若直接断言, 在 Linux CI 上必失败 (2026-09-10 实测 3 例): `test_utils.py` 的 `test_add_long_path_prefix_for_win/unc/already_prefixed` 用 `monkeypatch.setattr(sys, "platform", "win32")` 模拟 Windows。规则: 测试主体行为的是"平台逻辑"而非"当前真实平台", 一律显式 monkeypatch, 不要依赖运行环境。
5. **`test_web.py` 不只测 FastAPI 路由**: 除鉴权/API/命令入队/设置读写/`?rid=` 视图版本门控/**静态资源 no-cache 响应头**/**前端静态资源守阵**(`test_frontend_static_bundle_health`: 冲突标记残留、JS 注释孤儿续行、**装了 node 时跑 `node --check` 真语法校验**、CSS 规则块漏闭合、`<transition>` 吞弹窗、模板引用的静态资源是否存在 —— 这类问题会让整页只剩背景色或整块功能静默失效)外, 还覆盖 WEB 功能的 manager 侧 —— 搜索索引构建与搜索、`_drain_web_commands` 各命令执行(含未知命令/异常的容错)、`ensure_group_view`/`ensure_group_state` 脏重建与版本自增、`_state_kind` 状态分类、`build_group_view` 字段(含单种子大小/总大小/标签/分类/保存路径/**组级 added_on 取组内最大值/组级 hr_triggered 与 hr_pending 计数**)、**错误原因展示**(TASK015: `_error_reason` 的 missingFiles→"文件丢失" / error→tracker `msg` / 非错误→空串, `refresh_error_reasons` 的预算与 TTL 限额、虚拟 tracker 条目跳过、离开错误态清空缓存、qB 断连跳过且不清值)、**HR 展示字段**(`hr_tag`/`hr_tag_done` 文本 + `hr_triggered`/`hr_satisfied` 布尔 + `hr_req_time`/`hr_req_ratio` 阈值)、`apply_new_config` 分级应用。找 WEB 功能的测试先看这个文件。`test_speed_curve.py` 另覆盖 **`_traffic_view` 只读快照**的各分支(disabled/ok 含 periods 与 target+actual/dry_run 无 actual/manual 原因/stale 的两种原因码)。

> ⚠ **前端渲染逻辑无法靠 pytest 覆盖**: 模板表达式错误(computed 当函数调用等)会让页面整块空白而测试全绿 —— 改前端必须做浏览器冒烟(假 qB + 临时 data_dir, 完事清理), 详见 [pitfalls.md](pitfalls.md)。**半个例外**: "整包 JS 语法损坏"(合并冲突残留、注释孤儿续行)与"模板引用缺失静态资源"属纯静态可判定, 已由 `test_frontend_static_bundle_health` 守阵(2026-09-17 实测白屏故障的防回归); 模板/表达式层面的错误仍只能靠真机页面看。
5.5 **`test_sync.py` 专测增量同步层**: `TorrentRecord.apply_delta`(只遍历 patch 字段/变化字段集/量化/双通道源/`_raw` 兜底/`state_enum` 缓存)、`TorrentStore.apply_sync`(首轮全量/增量只改变化记录/无变化零成本/增删/全量剪除/待报删除/降级/异常/`reset_sync`)、以及 QbManager 接线(增量轮不做 schema 校验、变化集与冲突脏组)。改 `torrents.py` 的同步层或 `_refresh_torrents` 时必须同步此文件。
6. **`test_impact.py` 直接测分级表而非被测端**: 用真实 `Config()`(字段默认即全默认实例) 构造新旧配置做 diff, 分级表外字段用 `SimpleNamespace` 替身(验证“未列出默认 L2”); 含 `_diff_flat`/`_diff_trackers`/`max_level`/`restart_required_paths` 直测。**改分级表或新增配置项时必须同步此文件**(新增配置项未补表 -> 默认 L2, 分级错误会让热重载静默不生效或误要求重启)。
7. **`test_memory_bank.py` 守知识库结构**(2026-09-17 新增, 不覆盖 src): `_index.md` 登记项 ↔ `tasks/TASK*.md` **双向一致** / 文件名 `TASKnnn-slug.md` / 五个必备章节齐全 / 档案 `**Status:**` 与索引分区一致 / 索引保留四个状态分区 / **档案 slug 唯一 + 索引同一 TASKID 只登记一次**(2026-09-18 补: 并行 worktree 各自立档会产出逐字节相同的重复档案与重复索引条目, 而 dict 式解析会静默覆盖, 双向一致与状态分区两个守卫都漏) / **`activeContext.md` 不得出现 `^- 2026-` 流水账纪要行** / skill 载体存在且 `AGENTS.md` 与 `copilot-instructions.md` 均声明立档阈值并指向 skill。改 `memory-bank/` 结构或会话协议时必须同步此文件 (红绿验证过: 幽灵任务与纪要回流两类违例都会失败)。
8. **测试期禁止真实系统副作用** (2026-09-18 新增, 两道会话级守卫): 全量测试实测会**真的发系统通知**(本机抓到一条 Windows toast `auto-qb 已停止`)。
   **主犯**: `test_cli.py::test_main_qb_compat_error_clean_exit` 把 `manager` 设成 `MagicMock`, `notify_fatal(msg, manager.config.notify)` 拿到恒真 MagicMock ⇒ 守卫 `if not config or not config.enabled` 放行 ⇒ 真发 toast —— 已改为 mock `auto_qb.cli.notify_fatal` 并断言调用。**通用规则: 给被测代码传 MagicMock 当配置对象时, `if not cfg.xxx` 形式的守卫一律会放行, 后面接着真实系统副作用的路径必须在测试里显式 mock**。
   **从犯**: `PlatformChannel("linux")` 只是**换后端, 不等于不发**, `NotifyHandler` 后台线程照样真跑 `notify-send`。
   **安全网**: `tests/conftest.py` 会话级夹具把通知器命令名(`notify-send`/`osascript`/`powershell`/`pwsh`)拦在 `subprocess.run` 之前(抛 `OSError` = "机器上没装通知器"), `send()` 仍走失败分支返回 False; 命令**构造**(`_build_*`)与非通知器子进程(`node --check` 等)不受影响, 需要真实 `subprocess.run` 的用例自行 monkeypatch 即可覆盖夹具。回归: `test_notify.py::test_notify_real_send_blocked_under_pytest`。
   **排查方法论**: 诊断插件输出**不能写 stderr**(pytest 按用例捕获、通过的用例直接丢弃 ⇒ 假阴性), 必须写**文件**; 统计用 **ASCII 标记**(中文串 grep 会误报 0)。
   **第二道守卫 · AUMID 注册表键** (2026-09-18 副作用普查发现): `PlatformChannel("win32")` 构造时会**真写** `HKCU\Software\Classes\AppUserModelId\AutoQB.UI` 且**写完不清理** —— 每跑一次测试就在用户注册表留一个持久键(与 `test_autostart_windows_registry` 的 Run 键不同, 那个在 `finally` 里自清理)。同一会话级夹具只把**AUMID 前缀**的 `CreateKeyEx`/`SetValueEx` 变成空操作(静默成功, 不抛异常 —— 否则 `_appid` 会回退成 `WINDOWS_TOAST_APPID_FALLBACK` 打乱断言), 其余注册表写入放行。
   **副作用普查结论**(全量 1007 项实测): 外部进程 0; 文件删除 157 条全在 `C:\TEMP\pytest-of-*`(仓库内外均 0); 建链 117 条全在临时目录; 网络监听全为 `127.0.0.1` 且自清理; 注册表仅剩 autostart Run 键(自清理)。手法与过滤临时目录的坑见 [pitfalls.md](pitfalls.md)。
9. **测试不得依赖宿主环境能力** (2026-09-18 新增): 断言"环境相关能力"(环境变量 / 符号链接权限 / 注册表 / 文件系统重定向)的用例必须**显式给定前提**, 否则会出现"单跑通过、全量失败"或"换台机器就红"的**假失败**。
   已修两例: ① `test_notify_legacy_shortcut_cleanup` 补 `monkeypatch.setenv("APPDATA", ...)` —— `_legacy_shortcut_paths()` 在 `APPDATA` 缺失时返回 `[]`, 不设等于空跑、断言必失败; ② `test_api_fs_dirs_endpoint` 第⑤条补 `os.path.islink()` 判定 —— 沙箱/重定向层会让 `os.symlink` "成功"却落成**真实目录**(实测 `islink=False`), 此时不存在"逃逸链接", 断言无意义(与原有的"Windows 无权限建链 -> 跳过"同口径)。
   **判据**: 单跑通过 + 全量失败, 或本机失败但逻辑上看不出问题 ⇒ **先查环境能力, 排除环境之前不要动 `src/`**(这两例生产代码都是对的)。
10. **测试期真实系统副作用有常驻守卫** (2026-09-18 普查后固化): `tests/sidefx.py` 记账器全程记录七类真实副作用(`POPEN` 外部进程 / **`LAUNCH`** `os.startfile`·`os.system`·`webbrowser.open` / `REG`+`REGVAL` 注册表 / `FSDEL` 文件删除 / `SYMLINK` 建链 / `BIND` 监听 / **`CONNECT`** 出站连接), 由会话级 autouse 夹具安装, **收尾按放行清单判定 —— 有越界项直接让本次 pytest 失败**(报告含分类计数与逐条明细)。**实测测试全部走回环、零外网连接**。
    台账在**每次** pytest 收尾打印(`pytest_terminal_summary`)—— 没有越界时守卫本来完全静默, 不打印就没人知道它在工作, 久了会被当死代码删掉; 打印形态即上面的分类计数(全量约 1742 条 / 越界 0)。
    `LAUNCH` 单列是因为它们**不走 `subprocess`**(`POPEN` 抓不到)却同样会弹窗口(资源管理器/浏览器/shell) —— `utils.open_path()` 在 Windows 上走 `os.startfile`, `/api/open-path` 能触达; 这类放行清单**为空**。
    **放行清单**(只有确实必需的副作用才在此登记): `node` 子进程(前端静态守阵的 `node --check`) / autostart 的 HKCU Run 键及其 `auto-qb` 值(用例在 `finally` 自清理) / 临时目录内的删除与建链 / 回环地址监听。
    判定策略本身有单测 `tests/test_sidefx.py`(含"临时目录判定必须剥掉 `\\?\` 前缀"这一回归点 —— 普查时 157 条假阳性就栽在这) —— **改清单时同步**。
    **不要**为了让测试变绿而随意放宽清单: 先确认该副作用是测试必需的。要临时诊断可取用 `sidefx_recorder` 夹具(如断言某操作未产生副作用)。

## tests/helpers.py 基础设施 (写测试前必读)

### Fake 对象

- **FakeClient**: 模拟 qbittorrentapi Client。记录所有调用到 `calls` 列表 (断言用, 如 `("add_tags", tags)`); `tags` set / `category` / `torrents` (dict: hash→FakeTorrent) 是可变状态; `torrents_delete_tags` 模拟真实行为 (同时从所有种子移除); `files_map` 按 hash 返回文件列表 (分组测试); `files_calls` 计数 (断言不再全量拉文件列表); `add_error` 模拟重加失败。**`sync_maindata(rid)` 忠实模拟 qB 增量语义**(内部 `_sync_rid`/`_sync_snapshot`, 返回 diff 字段/`torrents_removed`/`full_update`; 用 `sync_calls` 计数而**不写 `calls`** —— 避免破坏既有调用序列断言)。**种子控制方法齐全(2026-09-13 补 `pause`/`resume`)**: 缺方法时 Web 命令执行路径会直接 `AttributeError` 暴露 —— 此前 Fake 缺这两个方法, 导致组级/单种子暂停开始命令在 Fake 环境不可端到端验证(只能测到路由与入队)。记法约定: `start`/`stop`/`recheck`/`reannounce` 记 `None`(历史断言依赖, 勿改), 新增的 `pause`/`resume` 记 hash 列表(便于断言“整组/单种”作用范围)。
- **FakeTorrent**: 鸭子类型兼容 `TorrentRecord`/`TorrentDictionary` (快照字段一致 + `tags_set`/`state_enum`/`tracker_name`/`log_repr` + `trackers_info(client)`/`files(client)` 惰性接口)。**`state_enum`/`tags_set` 是属性不缓存** — 测试常直接改 `.state`/`.tags` 后重跑动作。默认: hash="HASH123", state="stalledUP", save_path=r"R:\Downloads", size/downloaded=100MiB。
- **FakeTracker**: name="HHan", domains=["tracker.hhanclub.net"], tags=["HHan"], hr/rules/limits 可注入。
- **FakeConfig**: 类属性默认全关 (grouping.enabled=False, add_episode_tags=AddEpisodeTagsConfig() 等); 测试按需覆盖实例属性。

### 本地假 qB 服务 (FakeQbServer, 2026-09-14 新增)

- **`FakeQbServer(client=None, abort=False)`**: 标准库 `ThreadingHTTPServer`(线程) + 随机回环端口, `with` 进入/退出保证回收; 数据来源是内部 `FakeClient`(单一口径), 服务端只做 HTTP 适配。
- 用途: 让测试用**真实** `qbittorrent-api` Client 走完整 HTTP 往返 —— 专门覆盖替身永远暴露不了的行为(session/trust_env/库内部重建 Session/rid 增量语义)。典型: `test_local_qb_service.py`(6 测)与 `test_ui.py::test_connect_failure_throttles_logging`。
- 端点: POST `auth/login`; HEAD 任意路径(库会先探测协议); GET `app/webapiVersion|app/version`; **路由分派不按方法区分读端点**(库对 `info`/`files`/`trackers`/`maindata` 用 POST, 对 `tags`/`categories`/`transfer` 用 GET), 参数合并 body 与 query; 未列出的 GET -> 404 JSON, 未列出的 POST -> `"Ok."`。
- **`abort=True`**: 收到任何请求即断开(不写响应) —— 确定地制造 `APIConnectionError`(实测回环约 0.7s/次), 用于连接失败节流类测试; 不要用"指向死端口"代替(部分环境是超时等待, 库内超时重试曾使该测试耗时 74s 而被 skip)。
- 辅助: `srv.port`(接配置)、`srv.client`(预置种子/断言写调用)、`srv.hits(endpoint)`(端点命中次数, 可断言"每 tick 只拉一次 sync"或"节流生效")、`srv.requests` 台账。
- 限制: 写端点只回 `"Ok."` 不改 FakeClient 状态(不做忠实状态机); 需要状态流转的测试请继续用进程内 `FakeClient` 替身。

### 构造函数 (最常用)

- **`make_manager(state_file, tracker_rules=None, tracker_kw=None)`**: 建 FakeConfig + QbManager (不连客户端) + 注入 3 条示例规则集 `example_rules` (add_site_tag/hr_done/stop_low_ratio, 分别覆盖 never+变量/`satisfied`+daily/`once`+action-failed) + `_load_rules()` (run() 才自动加载, 测试须手动)。
- **`make_ctx(mgr, tor, client, dry_run=False)`**: 构造 RuleContext。保证: ①client 绑定到 mgr (动作走 QbApi Facade) ②tracker_conf 已匹配 ③**对象身份直写** `store.by_hash[hash] is tor` — 后续改 `tor.xxx` 属性对 `ctx.torrent` 实时可见 (无需重建)。
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
- `FakeConfig` 的类属性 `check_missing_files = False` 是历史遗留 (真实配置在 grouping 段: `config.grouping.check_missing_files`, 默认 True) — 分组测试记得开 `mgr.config.grouping.enabled = True`; 缺文件扫描由 `grouping.check_missing_files` 控制, 测试时按需在 `mgr.config.grouping` 上设置。
- helpers 在未安装 qbittorrentapi 时降级 (`TorrentState=None`), 但项目 venv 已装, 一般无需考虑。
