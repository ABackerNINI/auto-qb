# 测试基线 · 变更流水 (外迁存档)

> 摘要: `baseline-history.md` 超 `log` 档 cap 后外迁的更早流水, 原文逐字未改。
> 触发: 基线为什么是这个数, 早期用例增量, 历史流水

> 外迁说明(2026-09-23): `baseline-history.md` 的 `log` 档 cap 是 24,000 字符, 新增一条后实测
> 24,466 越线(该文件此前只剩 170 字符余量) ⇒ 按轮转策略(`_common.LOG_ROTATE_KEEP`, **触顶即切约 1/3**)
> 把**最老一段**原样搬到这里 —— 本次恰好 1 条, 但它 ≈ 1/3 容量;
> ❌ 策略不是「只搬最老一条」, 那会让下次追加立刻再触顶。当前数字见 [../baseline.md](../baseline.md), 近期流水见
> [../baseline-history.md](../baseline-history.md)。

> 本目录是 `attachments/`: 不被 `iter_topic_files`(非递归 glob) 扫到, 因此不计入 cap 检查,
> 也不需要三行头之外的元数据。

- ↑ 1062 → 1077(W1 `tests/test_expr_parse.py` +15: 词法字面量/单位、一层一运算符红绿用例、前缀形态、
  函数调用、列表字面量、字面量类型冲突、AST 形状)
  → 1094(W2/W3 `tests/test_expr_eval.py` +17: 取值面/求值/短路与缓存/运行期类型错误/静态语义校验/
  数据源不可用与**配置期门控**/全局流量取值/**旧 16 条件 + 2 条 = 18 条等价对拍**)。
  ⚠ **Linux 侧未同步重测**(这两轮只在 Windows 跑), 按本节上方纪律, 下次动基线时两侧一起补。
  ❗TOTAL 覆盖率 91%; `src/auto_qb/rules/expr/` 未覆盖行主要是错误分支与防御路径。
  ❗两侧**收集数相同**(那 2 条在 Windows 上跑、在 Linux 上跳), 比较时别拿 "passed" 直接比:
  Windows 1057 passed == Linux 1055 passed + 2 skipped。跳的两条都是 Windows 专属 ——
  `test_sidefx.py::…`(AUMID 守卫: 非 Windows 无 winreg) 与 `test_ui.py::…`(注册表专属键)。
  改了基线就把**两侧都重测**, 只测一侧就更新会立刻产生漂移
  (本次就是把还停在 1049 的 Linux 数字补回来的)。
  ⚠ WSL 侧重测要 `cp -r` 一份**到 ~/ 下**(不要放 /tmp): 仓库副本落在临时目录里会让
  `test_sidefx.py::test_sidefx_is_temp_path` / `::test_sidefx_policy_flags_unknown_effects`
  两条**假红**(2026-09-20 实测: /tmp 副本 2 failed, 同代码挪到 ~/ 即 0 failed —— 不是回归)。
  = 1055 + **主循环 × WebUI 解耦(docs/plans/26-09-20-0234-webui-decoupling-plan.html)** 新增 2 项:
  ① `test_qbmanager.py::test_qbmanager_source_has_no_web_state_fields` —— **静态防回潮守阵**:
  扫 `qbmanager.py` 源码不得再出现 19 个表现层字段名(`self._group_view` 等)。必要性在于
  兼容代理 `_WEB_STATE_ALIAS` 会把这类回潮**静默转发** ⇒ 代码照样能跑、diff 里看不出问题,
  只有扫描能抓住。红绿双验过(注入 `self._group_view = []` ⇒ 报 `['_group_view']`)。
  ② `test_qbmanager.py::test_web_state_alias_proxies_to_runtime` —— 代理**只转发不存值**守阵:
  旧字段名与 `self.web.<新名>` 必须读同一对象、写双向可见。若退化成"赋值进实例字典"就出现
  两份真相(主循环改 runtime 那份、Web 线程读 manager 那份 ⇒ 视图静默停在旧快照且不报错)。
  本次另改 3 处既有守阵的**目标**(不是判据): `_drain_web_commands` → `web.consume_commands`、
  回执 spy → `web.set_result`、`_log_cmd_timing` 的宿主 → `WebUIRuntime`; 自投递静态守卫的正则
  扩到同时认 `web_commands.put(` 与 `web.post_command(` 两种写法(否则重构后守卫直接失效)。
  = 1053 + **节拍对齐门控(issues/26-09-19-1900-bug-webui-poll-cadence-mismatch, 方案 B)** 新增 1 项:
  `test_qbmanager.py::test_view_rebuild_waits_for_client_consume`(上一版没被 /api/state 取走就不生产下一版:
  >3000 种子时服务端 3s 产 2 版而客户端只取 1 版 ⇒ 实测 20 周期 40 次 → **20 次(省 50%)**;
  同时钉住两个边界: **脏标记必须保留**(只是不生产, 不是丢弃变化) 与 **force=True 必须绕过** ——
  本轮有命令改了种子状态时必须立刻重建, 否则与 P0-5「真值几十毫秒内进快照」相悖。红绿双验过)。
  = 1052 + **热路径跳过 FastAPI `jsonable_encoder`** 新增 1 项:
  `test_web.py::test_api_state_skips_jsonable_encoder`(用**计数替身**包住
  `fastapi.routing.jsonable_encoder`, 断言 8 条 URL(7 个端点)调用次数为 0: /api/state?view=torrent、/api/state、
  /api/groups、/api/search、/api/torrents/{hash} 及 /trackers、/files、/peers;
  **清单里明确排除 `/api/config/schema`** —— 它的载荷含 dataclass(Group/Field/Plugin), 必须保留
  编码器做转换(直返会 `TypeError: Object of type Group is not JSON serializable` ⇒ 500, 实测)。**这是"优化被后人重构掉"的守阵, 不是功能断言** ——
  返回裸 dict 时 FastAPI 会先递归遍历整个响应体做一次 jsonable_encoder(3000 种子实测
  **161 ms**, 占端点总耗时 189 ms 的 85%, 全程占 GIL); 改成 `JSONResponse` 直返即被
  `fastapi/routing.py` 的 `isinstance(raw_response, Response)` 短路。刻意用计数而非计时:
  计时在 CI 上不可靠。红绿双验过(注入 `return payload` → 报"走了 jsonable_encoder(1 次)")。
  = 1052 + **复核第二波(组/集乐观 BUG-3 + 追剧页空白 BUG-8 + 复制磁力 BUG-9 + 状态优先级表 BUG-7)** 新增 1 项:
  `test_web.py::test_ensure_group_state_show_view_carries_member_index`(BUG-8: 追剧页的按视图回传
  必须**连带成员索引** groups+singles, 但不回 4.5MB 的 torrents —— 只回 shows 时前端 memberByHash
  为空, 每个集的成员都被 filter(Boolean) 丢掉, 刷新后停在追剧页会得到**永久空白**且不会自愈)。
  另改 2 项既有测试的口径: `test_api_state_view_scoped_payload`(view=show 的期望从"只回 shows"
  改为"回 shows+groups+singles"), `test_frontend_static_bundle_health`(静态守阵新增第 8 项:
  `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致 —— BUG-7 就是两张表漂移, 人眼发现不了)。
  2026-09-21 第 8 项**再补一条顺序断言**: `seeding` 必须严格排在 `paused` 之前(混合态取做种色,
  用户口径) —— 逐项一致只管"两页同色", 管不了"同成哪个色"; `04cbc8e` 正是两表一起翻成 paused
  才让辅种页组行变灰。红绿双验过(注入旧顺序 ⇒ 报"把 paused 排在 seeding 之前或同级")。
  基线数字**不变**(只加断言, 未新增测试函数)。
  BUG-9(复制磁力)与 BUG-3(组行 is-pending / 集行 epState)是纯前端, 由冒烟覆盖;
  `tests/helpers.py::FakeTorrent.to_dict` 是**桩保真度**修复(缺它则详情端点恒 500, 详情抽屉与
  依赖详情的编辑对话框在冒烟里从未被跑过), 不影响单测基线。
  = 1051 + **复核缺陷修复批(1~4 + 8~9)** 新增 2 项(均为「接线」断言, 红绿双验):
  `test_qbmanager.py::test_drain_web_commands_bumps_write_seq`(P1-4 失效接线: 写命令执行后
  `_web_write_seq` 必须自增, **自投递命令不得自增** —— 此前全仓只测缓存机制、没测接线,
  字段改名或把自增挪走都会让测试全绿而只读缓存静默永不失效);
  `test_drain_bumps_write_seq_before_writing_receipt`(BUG-5 顺序: 用 spy 观察 `_set_web_result`
  内部看到的序号 —— 回执必须先失效缓存再宣布成功; 旧顺序下实测报 "实际 0 vs 期望 1")。
  其余修复项(P1-2 间距实测 / 冒烟读数时机 / 文档漂移 / harness 限回环 / cmdStats 出口)不改单测基线:
  前两项由**浏览器冒烟**覆盖(`P1-2 占位总高 == 全量渲染`, 见本节末), 后者为注释/脚本改动。
  此前 1049 —— 波次三(P1-2 行窗口化)为**纯前端**改动, 未新增/减少单测 —— 由静态守阵
  `test_frontend_static_bundle_health` + **真浏览器冒烟**覆盖(见本节末「浏览器冒烟」)。
  = 1046 + **WEB UI 响应性波次二(P1-5 超时 / P1-1 按视图回传 / P1-4 只读端点短缓存)** 新增 3 项:
  `test_qbmanager.py::test_new_client_sets_request_timeout`(P1-5 守卫: 客户端必须带请求超时,
  否则 qB 假死时主循环被占住、连重连退避都跑不起来);
  `test_web.py::test_api_state_view_scoped_payload`(P1-1: view=torrent/show 只回该视图数组;
  未知 view 回全部作保守默认; 版本一致时增量门控优先于 view);
  `test_web.py::test_api_readonly_endpoints_short_cache`(P1-4: 窗口内合并重复请求 /
  **写命令后立即失效** / 断连仍 503 —— 后两条是硬要求, 缺一条就会出现"改了没生效"或"断连被藏住")。
  P1-3(updated() 去布局抖动)纯前端, 由静态守阵 + 浏览器冒烟覆盖, 无新增单测。
  另: `test_web.py` 的 `_make_web_manager` 替身需同步 `ensure_group_state(rid, view)` 与
  `_web_write_seq` 字段 —— 真实 manager 加了参数/字段后, 替身不同步就会 TypeError。
  此前 1046 = 1041 + **WEB UI 响应性波次一** 新增 5 项, 见下。
  = 1041 + **WEB UI 响应性波次一(分层节拍 + P0-1 命令唤醒 + P0-5 命令后补刷新 + P0-0 埋点)** 新增 5 项:
  `test_qbmanager.py::test_run_loop_layered_cadence`(同步线按 sync_interval / 任务线按 main_tick, 两线次数不等)、
  `test_wake_drains_commands_without_extra_ticks`(命令唤醒只走命令线, 命令风暴下 tick 次数不增加)、
  `test_drain_web_commands_reports_resync_needed`(P0-5 门控: 只有改种子状态的命令置 changed)、
  `test_command_batch_triggers_single_resync`(P0-5 一批命令后只补**一次**完整刷新)、
  `test_web.py::test_api_enqueue_wakes_main_loop`(投递用户命令唤醒主循环 + 自投递命令须登记防自激)。
  ⚠️ 同时**改写**了 3 条既有用例的判据(不是新增): `test_run_loop_throttles_without_stop_event` /
  `test_run_loop_managed_never_sleeps` 的阻塞原语从 `time.sleep(main_tick)` 换成 `_wait_next`
  (按"真实经过时间"判定, 仍是防空转的回归守卫); `test_local_qb_service.py::test_main_loop_throttled_by_main_tick`
  需把 sync_interval 一并设成 0.2 —— 两线不同拍时 `_tick` 只在两线同时到期才走到, 原"每轮一次 sync"假设失效。
  此前 1041 = 修复前实测 1039 + **Linux CI 三处失败修复** 新增 2 项(`test_sidefx.py::test_sidefx_rmtree_dir_fd_entries_not_flagged`、
  `test_utils.py::test_atomic_write_rejects_empty_path`)。注: 修复前实测 1039, 比本文件此前记的 1038 多 1 —— 以实测为准,
  下面链条里的 1036/1022 等历史基数不再逐一追平。历史链条: 1036 = 1022 + **架构审查 Wave 3/4 第二批** 2 项(`test_actions.py::test_stop_preserves_completeness` 暂停/恢复不得翻转完成位、`test_qbmanager.py::test_reconnect_backoff_and_reset` 重连指数退避与归零); 此前 1036 = 1022 + **架构审查 Wave 0/1/3/4 固化缺陷** 14 项: `test_utils.py` 原子写 3 项(`test_atomic_write_creates_file` / `test_atomic_write_failure_keeps_old_content` / `test_atomic_write_keep_backup`)、`test_checking.py` 跳检未确认也备份 1 项(`test_checking_skip_readd_unconfirmed_backs_up`)、`test_web.py` 密钥不进日志 + 配置树掩码 2 项(`test_web_token_not_printed_in_logs` / `test_config_tree_masks_secrets`)、`test_config_writer.py` 掩码还原 2 项(`test_mask_tree_hides_sensitive_scalars` / `test_unmask_tree_restores_from_disk`)、`test_config.py` 任务数范围校验 1 项(`test_validate_max_tasks_per_tick_range`)、`test_web.py` 视图并发原子发布 1 项(`test_views_published_atomically_when_rebuilt_concurrently`)、`test_tvshows.py` bare 集数 0 拦截 1 项(`test_bare_zero_not_episode`)、`test_conditions.py` HR 无站点判定 1 项(`test_hr_condition_no_tracker_conf`)、`test_web.py` 畸形分组 key 转 400 1 项(`test_api_group_malformed_key_returns_400`)、`test_notify.py` 免打扰不吃配额 + 去重表淘汰 2 项(`test_notify_quiet_hours_does_not_consume_quota` / `test_notify_throttle_dedup_table_evicted`); 此前 1022 = 1021 + 任务档案改名与索引生成化新增 `test_memory_bank.py::test_index_is_regenerated` 1 项; 1021 = 1018 + WEB UI **视图重建范围收口** 3 项(`test_flat_view_refreshed_by_main_loop_tick` / `test_rebuild_views_single_entry_point` / `test_api_state_status_carries_server_state`); 此前 = 1007 + **副作用记账器固化**(`tests/sidefx.py` 记账与判定策略 + `tests/test_sidefx.py` 10 项策略单测) + `test_notify.py` 1 项 "启用且不 mock" 真实路径回归; 此前 1007 = 1006 + **测试期禁止真实系统通知**(`tests/conftest.py` 会话夹具)新增 1 项 `test_notify_real_send_blocked_under_pytest`; 此前 1006 = 1001 + WEB UI **错误种子显示具体原因**(TASK015)5 项新测试: `test_error_reason_from_tracker_msg` / `test_error_reason_missing_files_without_api` / `test_refresh_error_reasons_budget_and_ttl` / `test_refresh_error_reasons_clears_when_recovered` / `test_refresh_error_reasons_skips_when_disconnected`; 此前 1001 = 1000 + `test_memory_bank.py::test_task_ids_and_slugs_are_unique` 1 项, 清理并行工作区 (当时是 worktree) 造成的重复档案时新增的结构守卫; 此前 2026-09-17 实测 1000, uv 环境; 修复导出 .torrent 的 latin-1 头崩溃 + `test_content_disposition_encoding` 后 = 999 + 1; 此前 999 = 第十轮 996 + 3 项 fs 端点测试; WEB UI 第十轮 16 项修复后 = 996 + `test_open_path_select_file_per_platform` + `test_api_fs_dirs_endpoint` + `test_api_fs_mkdir_endpoint` 3 项; **第十一轮 7 项前端修复后复核同为 999**(无新增后端逻辑, 改动由静态守阵 + 双 UI 浏览器冒烟覆盖), 前端改动不影响单测, 双 UI 模板/CSS 由静态守阵 + 浏览器冒烟覆盖), 分支覆盖率 92%(ui.py 窗口/托盘本体不单测, 真机冒烟验证; WEB UI 端到端为后端单测 + 临时 Fake 服务浏览器冒烟; 真实 HTTP 栈的集成测试用 `helpers.FakeQbServer` 本地假服务, 不连真实 qBittorrent; 注意: test_ui.py::test_autostart_windows_registry 真写 HKCU 注册表, 沙箱化 shell 里会因写入受限失败, 常规终端应通过)
