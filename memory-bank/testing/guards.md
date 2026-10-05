# 守阵清单

> 摘要: 全库**机械守阵**的汇总 —— 一条 = 守阵名 + 钉住的结论 + 怎么红验。新增守阵时登记到这里。
> 触发: 守阵, 静态守卫, 防回潮, 红验, 钉住, 加守卫, 守卫清单

> **守阵 = 把"靠人记的规则"变成"违反就红"的测试。** 必要性有两条反向实证: 已机检化的
> 「提交后核 ref 三处」与「脚本改名漏改的未定义名」此后**一次都没再犯**; 而只写在文档里、
> 靠人记的 `git rebase` 禁令在工具 shell 里出了**三次**事故。
> ⇒ **能变成红的, 从文本搬进守阵; 搬不动的, 必须在做那个动作的决策点可见。**
>
> **登记规则**: 新增守阵必须同时 ①在本表加一行 ②在被测文件头部 docstring 的「测试计划」清单加一行
> ③**做一次红验**(把被测修复临时还原 / 注入违例, 确认它真的变红)。

## 知识库结构(`tests/test_memory_bank.py`, 检查器在 skill 的 `check_kb_structure.py`)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_index_is_regenerated` | `tasks/_index.md` == 生成器输出 | 手改 `_index.md` |
| `test_tasks_index_and_files_are_bijective` | 索引登记项 ↔ `tasks/*.md` 双向一致 | 建个不登记的档案 |
| `test_slug_is_unique_ignoring_date_prefix` | 忽略日期前缀后 slug 唯一 + 索引不重复登记 | 复制一份档案 |
| `test_task_file_naming_and_sections` | 命名 `YY-MM-DD-<slug>.md` + 五个必备章节 | 删一个章节 |
| `test_task_status_matches_index_section` | 档案 `Status` 与索引分区一致 | 改 `Status` 不重跑生成器 |
| `test_active_context_has_no_rolled_up_session_log` | `activeContext.md` 不出现 `^- 2026-` 纪要行 | 追加一行纪要 |
| `test_session_protocol_is_exposed_in_always_on_entries` | skill 载体存在 + `AGENTS.md` / `copilot-instructions.md` 都声明立档阈值并指向 skill | 删掉声明 |
| `test_kb_index_is_regenerated` | 各目录 `_index.md` == `gen_kb_index.py` 输出 | 手改任一 `_index.md` |
| `test_kb_index_and_files_are_bijective` | 索引 ↔ 目录双向一致(含类目录) | 删一个主题文件 |
| `test_kb_topic_files_have_metadata` | 主题文件与 `_about.md` 都有三行头 | 去掉 `> 触发:` 行 |
| `test_kb_files_respect_caps` | **硬规定** cap 必须绿(2026-09-30 后 `check_caps` 的 problems 只剩 `agents` = AGENTS.md) + 硬规定角色集不许被搬走 | 把 `AGENTS.md` 撑到 8,001 字符 / 把 `agents` 从 `HARD_CAP_ROLES` 里拿掉 |
| `test_kb_cap_debt_is_discoverable_not_blocking` | 尺寸超限必须报成 **warn(债务)** 而不是 problem —— 降级后"断言现行文档都不超"会退化成恒绿 | 把尺寸超限塞回 `problems` |
| `test_agents_md_cap_is_hard_not_debt` | AGENTS.md 超限仍是 problem, 且**不出现在债务清单里** | 把 `agents` 挪进债务组 |
| `test_kb_slice_cap_and_count_are_debt_not_blocking` | 切片尺寸 / 条数 → warns(债务); 命名 / 三行头 → problems | 把尺寸/条数塞回 `problems`, 或把命名塞进 warns |
| `test_context_caps_hard_and_debt_split` | `check_context_caps.py`: AGENTS.md 只在 `HARD_CAPS`, 不进任何债务组 | 把它挪进 `SKILL_CAPS` |
| `test_kb_class_names_and_topic_filenames` | 类名 ∈ 固定枚举 + 文件名 `^[a-z0-9]+(-[a-z0-9]+)*\.md$` | 建一个枚举外的类目录 |
| `test_kb_no_orphan_index_dirs` | 每个顶层 `_index.md` 都被 `memory-bank/README.md` 引用 | 新建目录不在 README 登记 |
| `test_kb_stubs_are_valid` | 被拆文档原路径是 ≤1 KB 存根(含「已迁至」、无 `##`/列表) | 往存根里写正文 |
| `test_kb_pitfall_entries_have_required_fields` | pitfalls 条目含 触发 / 判别 / 处置 | 删掉一个字段 |
| `test_kb_scripts_import_cleanly` | skill 的 4 个脚本都能 import | 引入模块级错误 |

## 前端 / WEB UI

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_frontend_computed_not_invoked_as_function` | computed 不得当函数调用(`this.xxx()`); 注释行跳过 | 写 `this.unitParts()` |
| `test_frontend_member_window_functions_live_in_methods` | 成员行窗口的带参函数必须在 `methods:` 内 | 挪进 `computed:` |
| `test_frontend_static_bundle_health` | 静态资源健康 **11 项**: 冲突标记残留 / JS 注释孤儿续行 / `node --check` 真语法校验 / CSS 规则块漏闭合 / `<transition>` 吞弹窗 / 模板引用的静态资源存在 / `STATE_RANK` 与后端逐项一致 + `seeding` 严格先于 `paused` / 集成员取 hash 必含 `memberHashesOf(` / 筛选器走 `facetRows`+`_facetOptions` 单点 / 挂件类名在 CSS 有定义 | 注入各类违例(实测 5 种) |
| `test_frontend_dist_segments_aggregates_per_view` | 状态分布必须按 `viewMode` 分支取数 | 改回只数 `groups` |
| `test_frontend_cols_store_single_setitem_site` | 全仓**唯一** `setItem` 漏斗 | 加第二个 `setItem` |
| `test_frontend_persist_page_takes_intent_only` | 派生值(自适应 px)进不了持久化路径 | 把 `colWidths` 落盘 |
| `test_frontend_col_manual_flag_not_revived` | 已删的 `colManual` 标志不得复活 | 写回 `colManual` |
| `test_frontend_toast_duration_floor_by_kind` | toast 停留下限单点 `TOAST_MS_FLOOR` 对 error / timeout ≥8s 生效 + `toast()` / `_finishToast()` 两条排期路径都走 `toastMs(kind, ms)` 且 `ms` 缺省为 `null` | 下限降到 4s / 排期改回裸 `ms` / `ms = null` 写死 4000(三例实测全红) |
| `test_api_state_skips_jsonable_encoder` | 热路径不得走 `jsonable_encoder`(计数替身; 清单排除 `/api/config/schema`) | `return payload` |
| `test_api_state_view_scoped_payload` | 按视图回传 + 未知 `view` 全回(保守默认) | 改 `VIEW_ARRAYS` |
| `test_ensure_group_state_show_view_carries_member_index` | 追剧页回传必须**连带成员索引**(groups+singles, 不回 torrents) | 只回 shows |
| `test_api_readonly_endpoints_short_cache` | 短缓存四边界: 窗口内合并 / **写命令后立即失效** / 断连仍 503 | 去掉失效接线 |
| `test_view_rebuild_waits_for_client_consume` | 上一版没被取走就不产下一版; **脏标记必须保留** + **`force=True` 必须绕过** | 去掉门控 |
| `test_api_fs_dirs_case_sibling_is_outside_whitelist` | 大小写兄弟目录判越界(**仅 Linux 真跑**, win32 skip) | 让 `_fs_real` 做 NTFS 折叠 |

## 主循环 / WEB 解耦 / 命令链路

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_qbmanager_source_has_no_web_state_fields` | `qbmanager.py` 不得再出现 19 个表现层字段名 | 注入 `self._group_view = []` |
| `test_web_state_alias_proxies_to_runtime` | 兼容代理**只转发不存值**(读写同一对象) | 改成赋值进实例字典 |
| `test_drain_web_commands_bumps_write_seq` | 写命令后 `_web_write_seq` 自增; **自投递命令不得自增** | 把自增挪走 |
| `test_drain_bumps_write_seq_before_writing_receipt` | 回执必须先失效缓存再宣布成功 | 换回旧顺序(报 "实际 0 vs 期望 1") |
| `test_new_client_sets_request_timeout` | 客户端必须带请求超时 | 去掉 timeout |
| `test_run_loop_layered_cadence` | 同步线按 `sync_interval` / 任务线按 `main_tick`, 两线次数不等 | 合成单拍 |
| `test_wake_drains_commands_without_extra_ticks` | 命令唤醒只走命令线, tick 次数不增加 | 让唤醒跑整轮 tick |
| `test_drain_web_commands_reports_resync_needed` | 只有**改种子状态**的命令置 `changed` | 放宽判据 |
| `test_command_batch_triggers_single_resync` | 一批命令后只补**一次**完整刷新 | 每条命令都补 |
| `test_api_enqueue_wakes_main_loop` | 投递用户命令唤醒主循环 + **自投递命令须登记**防自激 | 去掉登记 |
| `test_run_loop_throttles_without_stop_event` / `test_run_loop_managed_never_sleeps` | 节流按**真实经过时间**判定(非 mocked sleep) | 换成 `time.sleep(main_tick)` |

## 后端高风险动作 / 状态持久化

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_checking_skip_backup_precedes_delete_and_cleared_on_success` | .torrent 备份**先于** `torrents_delete` 落盘, 成功后清理 | 只在流程末尾断言即失效; 在客户端 `torrents_delete` 里快照 |
| `test_checking_skip_delete_unconfirmed_clears_backup` | 删除未生效也清备份(不留孤儿) | 只在成功分支清 |
| `test_checking_skip_backup_failure_aborts_before_delete` | 备份写不进 ⇒ **不删除** | 改成先删后备份 |
| `test_checking.py::make_mgr` | 未指定 `state_file` 时**自动发临时 state 文件**(否则写到 CWD=仓库根) | 留空 |
| `test_load_state_corrupt_falls_back_to_bak` | 主文件损坏 ⇒ 回退 `.bak` **并自愈写回主文件** | 打回旧实现 |
| `test_load_state_corrupt_without_backup_warns` | 备份也不可用 ⇒ 仍空状态但留两条 WARNING | 静默清空 |
| `test_load_state_missing_file_is_silent` | **首启不告警**(反向钉住"损坏 vs 首启"分开处置) | 把首启也告警 |
| `test_load_state_recovered_writeback_failure_is_nonfatal` | 自愈写回失败**只告警不抛** | 让异常外抛 |
| `test_cleanup_orphan_tmp_removes_only_state_leftovers` | 只删 `<state_file>.<随机>.tmp`; **`.bak` 是关键反例**; 二次调用幂等 | 放宽成"同目录所有 .tmp" |
| `test_cleanup_orphan_tmp_missing_dir_is_nonfatal` / `..._delete_failure_is_nonfatal` | 列不出目录 / 一个删不掉都只告警 | — |
| `test_cleanup_orphan_tmp_is_wired_after_lock` | **接线守阵**: 挂在 `self._lock.acquire()` **之后**且落在 `if not no_lock` 内 | 挪到持锁之前 |
| `test_utils.py::test_atomic_write_*` | 原子写三态 + `keep_backup` 路径按 `utils.BACKUP_SUFFIX` | — |
| `test_utils.py::test_atomic_write_rejects_empty_path` | 空路径必须 `raise`(否则往仓库外丢 `.tmp`) | 去掉校验 |
| `test_no_o_trunc_write.py::test_src_has_no_o_trunc_write` | src 下 .py **非注释 token 零 O_TRUNC**(NAME 拦 `os.O_TRUNC`, STRING 拦 `getattr(os, "O_TRUNC")` 绕行; 注释豁免) —— token/凭据写入只走 `utils.atomic_write` 唯一单点, 确需直写走 `_WHITELIST` 注明理由 | src 下放探针 `.py` 写 `os.O_TRUNC` 即红, 删探针回绿 |
| `test_grouping.py::test_group_key_of_is_single_source_of_truth` | 归组 key 纯函数 == 真实 mixin 输出 | 内联公式分叉 |

## S2 健壮性批次守阵 (26-10-06-0028 ×6, 红验 26-10-06 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_qbmanager.py::test_refresh_suppress_window_exception_closes_window_in_finally` (A-01) | suppress 窗内异常上抛后 live 旗标不残留(try/finally 关窗), 下一成功轮 full_round 相位照常广播不被吞(边沿驱动事件不可重放) | 还原 qbmanager 关窗点为裸 `set_suppressed(False)` |
| `test_hr_store.py::test_non_utf8_file_is_quarantined_and_recovered_from_backup` + `..._never_raise_on_unlocked_read_and_backup` (B2-01) | 非 UTF-8 字节(GBK 重存)归「坏文件」recoverable 类走 quarantine → .bak 自愈链; 无锁只读/备份路径「读坏不抛」如实带回错误(status.py 契约对 encoding 类成立) | `except (OSError, UnicodeDecodeError)` 还原为 `except OSError` |
| `test_traffic_sample.py::test_agg_trim_engages_for_runtime_created_series` (C-01) | 运行期新建系列(不经 _recover_series)earliest_hour 随 hour 行入账初始化/min 更新, 满窗后裁剪生效(agg.dat hour 行有界, v3 §04.5 契约落地) | 删掉 `_agg_ingest_hour` 里的 earliest_hour 维护 |
| `test_config.py::test_validate_checking_action_spec` (D-02, 扩展既有用例) | checking 动作子段(with_reference/without_reference)键面 fail-fast: enabeld/autostart 拼错报未知键, enabled 非布尔报错, 全键面合法不报 | 还原 `_validate_checking_action_spec` 为只查 mode |
| `test_notify.py::test_notify_icon_ico_points_to_real_file` (H-02) | ICON_ICO 两级 dirname 指向真实存在的 icon.ico(与 tray/app.py 同口径), AUMID IconUri 不再恒写不存在路径 | 还原为一级 dirname |
| `test_utils.py::test_convert_bool_in_dict_list_branch_keeps_decimal_strings` (H-03) | convert_bool_in_dict 列表分支与字典分支同口径: 列表内纯数字串保持原样不 True 化(导出模板回填类型不漂移) | 还原列表分支为无条件递归 |

## S3 竞态/回执批次守阵 (26-10-06-0028 ×4, 红验 26-10-06 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_web.py::test_web_store_iteration_snapshot_race_guard` (E-01) | Web 读侧迭代面(search_torrents / _build_* 系 / mark_local_present)取快照引用(tuple/list)后再遍历 —— 写线程高频原地增删 by_hash/groups/cross_group_conflict_warned 期间零 "dictionary changed size during iteration"(读侧快照对偶「主循环唯一写线程」, 口径同 build_search_index 原子交换) | 还原 views.py/hr.py/fs.py 的 tuple() 快照包装(实测 4s 内必抛 RuntimeError) |
| `test_web.py::test_modal_identity_stamp_landing_guard` (F1-01) | 模态身份戳落袋守卫单点: ui_feedback._openModal 每框发自增 `mid` + `_modalIsCurrent`(visible+mid 双比对)单点 + drawer._skipPrecheck 落袋守卫 = seq 代际 + 身份戳且先于任何 this.modal 写 —— 取消跳检框后开无关 modal(seq 不递增)只有身份戳拦得住迟到回执 | 还原 drawer.js/ui_feedback.js 身份戳四处(实测红在「_openModal 未随框发 mid」) |
| `test_web.py::test_reannounce_group_empty_snapshot_error_receipt` (E-03) | _cmd_reannounce_group 空组(成员执行时刻全不在快照)显式 error 回执、不发指令不登记跟踪 —— 对齐单发 reannounce_torrent 回执口径, 前端 waitCmd 不再挂 40s 超时 | 还原 commands.py else 分支(实测红在 KeyError: 'r-gone', 即无回执) |
| `test_web.py::test_frontend_dir_browse_and_search_stale_guard` (F2-03) | 请求代际守卫与 drawer._drawerStale 同式收口: loadDir 发请求即记 `_dirReqPath` 戳(落袋/报错/finally 三处比对, 过期请求不动 loading 态) + doSearch 落袋/报错前比对当前 searchQuery 词 —— 慢响应不覆盖新状态 | 还原 add_torrent.js/view.js 守卫(实测红在「loadDir 未记 path 戳」) |

## S4 死代码/杂项批次守阵 (26-10-06-0028 chore ×4, 红验 26-10-06 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_hr_service.py::test_store_prebuilt_per_site_confs` (B1-01) | HrRefreshService 站点存储构造期预建(site_confs 全键) —— 取数线程 × Web 线程并发首访拿到同一实例, 「每站点一把锁/单实例」契约不再依赖首访时序; conf 外点名仍走 store() 惰性分支兜底(CLI --hr-confirm-empty 手输) | 还原 `self._stores: Dict = {}` 惰性建(实测红在「构造期 _stores 非空」) |
| `test_config_writer.py::test_backup_atomic_write_no_partial_bak` (D-03) | writer._backup 保存前备份经 `utils.atomic_write`(与 backup_versioned 统一): 内容写到一半抛异常的干净路径上零半截 .bak, 已存在旧备份不被截断 —— 恢复资产完整性 | 还原 `_backup` 的 `open(backup_path, "w")` 直写(实测红在「备份未经 atomic_write」) |
| `test_qbmanager.py::test_export_torrents_info` (A-02) | export_torrents_info 编码恒 `utf-8` —— GBK 外字符种子名(语料 U+20000)如实落盘不崩(Windows 默认 cp936 会 UnicodeEncodeError 中途崩); **静态钉**(inspect.getsource 断言 encoding="utf-8") + 行为面双保险 | 还原 `open(path, "w")` 无编码(实测红在静态断言 —— 本机默认编码恰为 utf-8, 行为面红验不可达, 与 O_TRUNC 守阵同判) |
| `test_web.py::test_api_speed_mode_reads_client_with_alt_fields` (E-02) | /api/speed/mode 三读成败口径对齐: 任一失败(含首读成功后续读抛的**部分成功组合**)整组回 None + DEBUG 一行异常摘要 —— 前端浮层不出「一半真一半未知」, 排障有日志 | 还原 `except Exception: pass`(实测红在「部分成功 current 有值」) |

## S5 refactor/语义批次守阵 (26-10-06-0028 ×6, 红验 26-10-06 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_module_host.py::test_exec_history_prune_bounded_and_active_kept` (A-03) | exec_history 键面有界: 超保留期(30 天)日期淘汰 + 超存量上限(2000)淘汰最旧**非当日**记录; 当日活跃键(同日窗口 daily/hourly 去重依据)即便 ts 最旧也不被误清 | 还原 record_execution 无 _prune_exec_history(键面只增不减) |
| `test_speed_curve.py::test_curve_state_day_keys_pruned` (A-03) | speed_limit_curve 日键保 7 天: 写入时顺带淘汰保留期外旧日键(调试快照无正确性消费方), 保留期内与当日键不受影响 | 还原 _record_curve_state 直写不淘汰 |
| `test_actions.py::test_pause_resume_sync_store_snapshot` (A-04) | QbApi pause/resume 写后同步 store 快照(与 start/stop 对称, 坑档 concurrency「写方法必须同步 store」): 同 tick 读 is_paused 为新值, 完成位不翻转 | 还原 torrents_pause/resume 纯透传(实测红在「pause 后 state 仍是 downloading」) |
| `test_qbmanager.py::test_a07_connect_non_api_error_transition_throttled` (A-07) | 非 API 类连接异常(凭据错 LoginError)与连接类同用 _last_conn_ok 转换节流: 失败态重复 connect 不重复 ERROR; 恢复后再失败重新报一次 | 还原 except Exception 无条件 logger.error |
| `test_qbmanager.py::test_a07_managed_first_connect_retry_warns_once` (A-07) | 托管模式首连重试循环的 WARNING 只说明白一次, 停止信号仍即时响应(不抛 QbConnectError 干净返回) | 还原逐拍 logger.warning |
| `test_hr_resolve.py::test_tie_*` 六条 (B2-02, P-04) | judge_record 双 hash 平局合并兑现 docstring: 同为放行取依据更强者(D 免罪>B>缺席), 同为管束取剩余时间更少(None 未知视为无穷大), 两态同为 SAFE 无判定翻转, 无证据平局保先到; C 终态未达标(failed 展示)恒保留不被洗成可删 | 还原 `_rank(res) > _rank(best)` 严格大于(平局恒取先到, 实测红在 D 免罪被缺席式放行压住) |
| `test_traffic_store.py::test_v4_bad_line_ratio_warning_once_throttled` (C-04, P-05) | 坏行占比超阈(>=2 行且 >5%, v2 口径; 撕裂尾豁免)读侧 WARNING 恰一次(按文件节流); 正常文件零告警 —— 真实损坏不再静默丢行 | 还原 read_day 不调 _warn_bad_lines |
| `test_web.py` SEED_ITEM 契约测试(E-04, P-06) | /api/state 平铺 SEED_ITEM 载荷**不含** magnet_uri(按需取详情契约, 坑档 contract-api 正向口径); 磁力复制走 /api/torrents/{hash} 详情端点(该端点 to_dict 全字段含 magnet_uri) | 还原 _seed_view 的 `"magnet_uri": r.magnet_uri` 行 |

## 仿真 / 语料 / 平台语义

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_sim_is_within_host_semantics` | B2 逃逸判定在**宿主语义**下成立(win32 与 linux 各真跑一次) | — |
| `test_sim_is_within_linux_equivalent` | 把 `os` 换成 `posixpath` ⇒ 本机复现 Linux 语义 | — |
| `test_sim_is_within_red_on_fold_without_sep` | **红验**: 只换折叠不换分隔符 ⇒ 真子路径被误拒 | 换 `ntpath.normcase` |
| `test_safe_delete_rejects_path_outside_fs_root` | B2 拒绝时**文件没被真删** + **记进 `violations`** | `is_within` 恒 True |
| `test_safe_delete_rejects_bulk_over_declared` | B3 数量上限, **钉两侧**(超 declared×2 要拒、恰好 2 倍不拒) | 阈值改 `*99` |
| `test_delete_group_files_removes_them_from_disk` | D4 删组文件, ❗必须走**合成档** + 显式断言 `before > 0` | 改成"假装删了" |
| `test_fsmock_case_folding_does_not_follow_platform` | 归一**不得跟随平台**(运行时把模块的 `os` 换成 `posixpath`) | 还原 `os.path.normcase` |
| `test_fsmock_long_path_prefix_and_case` | 长路径前缀 + 大小写折叠(语料语料取自 NTFS) | — |
| `CORPUS.group_exact` + `group_exact_diff` 三道红验 | 语料真值分组 == auto-qb 实际分组(**成员串组 / 一组拆两组 / 真值组没被分出** 都要红) | 只比组数会放过串组 |
| `CORPUS.maindata_lag_modeled` | 两个滞后都为 0 时判据必须转红 | issue 26-09-20-2145 的验收凭据 |
| `test_write_corpus_end_to_end_minimal` (test_qb_capture.py) | **write_corpus 落盘全链**(T0 ⊕ 增量 ⊕ closure 最小 capture, sanitize_all → write_corpus): 落盘成功不 NameError; meta.sanitize_map.known_tags 经 `san._revs["tag"]` 伪名反查命中 auto-qb 自有标签(MISSING/zSkipChecked)、站点标签不入; 流内标签已伪名化; group_conservation 绿(H-01, issue 26-10-06-0027) | 还原 `_sanitize_mapping` 旧体(引用未定义 `seen`) ⇒ write_corpus 必 NameError、整场语料不落盘 |
| `CORPUS.fs_mock_coverage` | FS mock 的入口覆盖(把探测换成 pathlib 必须红) | 换 `pathlib` |
| `tests/test_sidefx.py`(10 项策略单测) | 记账 / 放行清单判定 + **临时目录判定必须剥 `\\?\` 前缀** | — |
| `test_notify_real_send_blocked_under_pytest` | 测试期不发真实系统通知 | 去掉会话夹具 |
| `test_config_schema.py`(20 项) | UI 元数据 vs 配置键 / 插件**一致** | 加配置键不改 `schema.py` |
| `test_impact.py` | 分级表直测(未列出默认 L2) | 加配置项不补表 |

## src 结构卫生(全 src 静态扫描)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_no_ghost_pkg_dirs.py::test_src_has_no_ghost_pkg_dirs` | src 下不存在「只剩 `__pycache__` 而无任何 `.py`」的幽灵包目录 —— 历史退役源码的空壳会误导「包还在」的排障判断(issue 26-10-01-1946) | 在 src 下建一个只含 `__pycache__` 的目录 |

## 规则表达式内核 (test_expr_eval.py)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_cross_container_list_equality` | `==`/`!=` 对 LIST 两侧做**容器形态归一化**(转 set 再比): `tor.tags`(frozenset)/`tracker.groups`(list)对列表字面量(tuple)精确匹配不再恒错(修复前 == 恒 False / != 恒 True, issue 26-10-06-0027); 标量比较不受归一化影响 | 还原 eval.py `_EQ` 的直接 `left == right`(P-01 拍板 = 求值侧归一化, 不做编译期拒绝) |

## 配置键面 / loader 消费 (test_config_key_surface.py)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_loader_probe_table_covers_named_leaf_surface` | loader 消费探针表恰好覆盖键面命名叶键(扣动态段与 `_LOADER_PROBE_EXCLUDED` 豁免) —— 新增配置键不配「YAML 显式值」探针当场红, 键在面上但 loader 漏读(D-01 形态, issue 26-10-06-0027)被结构性堵住 | 删表里任一键条目 |
| `test_named_leaf_keys_round_trip_through_load_config` | 每个命名叶键的 YAML 显式值(≠字段默认, 空转自断言)经 load_config 真链路回读 == 期望解析值; 还原 D-01 缺陷实测红在 `grouping.cross_group_conflict_check: 期望 True, 实得 False` | 还原 loaders.py 漏读 fix |

## 通用纪律

- **红验优先用运行时 monkeypatch 还原旧实现**(不碰工作区), `lru_cache` 记得先 `cache_clear()`。
- **一条守阵只钉一个结论**; 想同时钉两侧(过严 / 过松)就写两条断言 —— 只钉一侧会被"更严格"或"更宽松"两头骗过。
- **静态扫描类守阵必须先剥注释**: `os.path.normcase` / `colManual` 这些串就写在 docstring 与注释里当反例,
  纯文本扫描会被注释骗过(冒烟的 `_scan_filter_facets` 同理, 见 `_strip_js_comments`)。
- 相关坑的完整判据见 [../pitfalls/testing/assertions.md](../pitfalls/testing/assertions.md) 与
  [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)。
