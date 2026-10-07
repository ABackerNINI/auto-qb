# 26-10-08-backend-test-web-split — tests/test_web.py 拆分(15 域 → 15 平铺模块)

**Status:** In Progress  
**Added:** 2026-10-08  
**Updated:** 2026-10-08  
**Summary:** 实施计划 [26-10-07-2336](../plans/26-10-07-2336-plan-test-web-split.html) 的执行档案(S0–S8)。把 tests/test_web.py(14,556 行 / 329 个被收集测试函数)按注释分节机械拆成 **16** 个平铺模块 + 共享件上收, 零逻辑改动、集合恒等。S0 已完成(同步 `34356f49` / 分支 `feat/test-web-split` / 基线复测 2771+4 逐位持平); S1 勘察已完成(映射表 329 fn 全覆盖, 嵌入本档 §S1); **P-01/P-02 已拍板**(节 3 拆两份 / 节 2 panel·page / 节 1 14-7 / 共享件 fixture→conftest + 辅助→`tests/webui_helpers.py`)。**S2 已完成**: `scripts/split_test_web.py` + 校验 4 条(内建, 另加内容/行守恒 2 条)+ 演练(临时目录全量拆, collect-only 337 项 / 329 名 == 源)+ 红验 3 条(6/6 先红后修), 见 §S2。S1/S2 实测对计划的纠偏: 函数数 323→**329**、docstring 条目 306→**312**、基线 2757→**2771**、节 3 内容异质(55 fn 仅 18 是流量 → 拆两份)、日志辅助类跨文件(非「内聚随节 13」→ 共享件实为 21 项)。**S3 已完成**: 批 1 试切(节 1 → `test_web_auth.py` 14 fn + `test_web_api_core.py` 7 fn)在 `develop` 落地 —— 新文件 409/189 行、`tests/webui_helpers.py` 437 行(21 件)、余量源文件 13,567 行(余 308 fn)、`conftest.py` +`web_env`; 校验 1–4 + 内容/行守恒全绿、collect-only **337 项 / 329 名 == 源**; `test.one` 14+7、`test.quick` **2771+4**、`test.full` **2771+4 / 99%**(与开工基线逐位持平)。**批模式暴露并修复了 S2 工具的 4 处「仅全量模式验证过」缺陷**(见 §S3)。  
**Topics:** test-web-split  
**Refs:** memory-bank/testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md

> 背景关联(不进机器认领链): 计划 26-10-07-2336 按 §2.3 声明「不声明 doc-refs, 豁免认领链」, 故本档不以 `**Refs:**` 挂计划, 只用散文引用; 计划与建档切片见 [26-10-07-2344-test-web-split-plan](../activeContext/26-10-07-2344-test-web-split-plan.md)。

## 原始请求

用户指令: 「实施计划S0-S1: 26-10-07-2336-plan-test-web-split.html」。即按计划 §04 的步进执行 **S0 开工前置** 与 **S1 勘察与映射表** 两步; S1 的门是 **P-01 拍板点**(请用户过目文件边界与命名后开工 S2)。

## 思考过程与决策

- **计划口径冻结, 但实测数字须重算**: 计划 §2.1 的行号/函数数是规划时点(基线 `0ae3212e`, 14,367 行)的实测; 当前 HEAD `34356f49` 已前进 5 笔, test_web.py 在流量图速率口径 S2/S3 中 +216/−27 行 → **14,556 行**。故 S1 的 AST 扫描一律以**当前文件**为真值, 不沿用计划数字。
- **S0 基线复测(计划要求「HEAD 显著前进则重跑 test.full」)**: 在 `feat/test-web-split`(从 `34356f49`)上 `commands run test.full` = **2771 passed + 4 skipped / 0 failed / TOTAL 16476/165/5694/149 / 99%**, 与最新切片 [26-10-08-0223](../testing/baselines/26-10-08-0223-test-webui-peers-harness.md)(测于含未提交改动的树)**逐位持平**。收尾 DoD 按「提交时落基线切片」新建 [26-10-08-0258](../testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md)(committed HEAD 复测, 同值), 作为本专题开工基线。
- **分支(落地改道)**: 按计划 S0 开了 `feat/test-web-split`, 但提交时发现**新分支流水线推不动** —— `run_sync` 假定远端分支已存在(先 `fetch <远端> <分支>` 再比 left-right), 取不到远端 ref 就报「拿不到远端」; `ship.push` 同样先走同步, 会卡在同一处。实测 Gitee 只有 `develop`/`master`/`feature_rules`, **无任何 `feat/*`**, 且 `gitee/develop` 已被另一 clone 推进(1a5f0262) —— 与 AGENTS.md「日常在 develop」「跨工作区同步一律走 Gitee develop」一致。经用户拍板**改落 `develop`**: develop 快进到远端 tip 后 cherry-pick 本次提交, 临时分支删除; S2–S7 亦在 develop 上做。
- **档案落名**: 计划 S0 写 `tasks/26-10-07-backend-test-web-split.md`, 但按 memory-bank skill 硬口径「档案日期取**创建日**(`commands run kb.time date`)」, 实际建档日为 **2026-10-08** ⇒ 落 `26-10-08-backend-test-web-split.md`(slug `backend-test-web-split` 不变, 已查本 clone 与跨工作区无同名)。
- **S1 关键纠偏(见 §S1 表)**: ①被收集测试函数 **329**(327 `test_*` + 2 `testhr_*`), 非计划说的 323; ②docstring 计划条目 **312**(0 幽灵 / 17 函数无条目), 非 306; ③计划「节 3 → test_web_traffic_qb.py」名不副实 —— 节 3(标记 5892→7884)实为 **18 个流量 fn + 37 个杂项 fn**(config/token/sites/group-view/error-reason/hr-status), 须 P-01 定夺拆分或改名; ④上收 conftest 的共享件远多于计划 §3.2 的 3 个(实测 **16 个辅助函数 + 3 个常量**, 含 164 行的 `_make_web_manager`)。
- **S2 校验器口径据此更新**: 校验①(集合恒等)面 = **329 个被收集函数**; 校验③(反幽灵+守恒)= 每文件条目指向本文件存在函数 + 15 文件条目总数 == **312**。
- **范围守恒**: S0–S1 只读勘察 + 建档 + 分支; 未动 tests/ 与 src/ 任何一行; 分析脚本落 gitignore 的 `tmp-analysis/`。

## 实现计划

计划 §04 的 S0–S8 步进(每批一 commit, 批间独立可停, 任何一批后中止仓库全绿)。本档跟踪各步状态。

## 子任务状态表

| #  | 子任务                                               | 状态 | 产出/说明                                                                                                                                                               |
| -- | ------------------------------------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S0 | 开工前置                                              | ✅  | 同步 `34356f49`; 分支 `feat/test-web-split`(提交时改落 `develop`, 见决策节); 基线复测 2771+4(见切片 26-10-08-0258); 本档; 忆坑四篇(bulk-rename/parallel-run/single-file-coverage-gate/tmpdir) |
| S1 | 勘察与映射表(只读轮)                                       | ✅  | AST 扫描 + 映射表 329 fn 全覆盖(§S1); 节 1/节 2 聚类定界与命名; 常量/辅助归属矩阵                                                                                                            |
| —  | **门: P-01/P-02 拍板**                               | ✅  | 2026-10-08 用户裁决(§P-01): 节 3 拆两份 / 节 2 panel·page / 节 1 14-7 / 共享件 fixture→conftest + 辅助→`tests/webui_helpers.py`                                                    |
| S2 | 拆分工具与红验                                           | ✅  | `scripts/split_test_web.py`(AST 切块 + 映射表 + 归属闭包 + import 裁剪 + docstring 逐条重分布); 校验 4 条内建(+内容/行守恒); 演练 collect-only **337 项 / 329 名 == 源**; 红验 3 条 6/6(§S2)          |
| S3 | 批 1 试切(节 1 → auth + api_core)                     | ✅  | 14 + 7 fn; 校验全绿; test.one 14+7 / test.quick 2771+4 / test.full 2771+4·99%; 2 处活注释已改; 批模式修工具 4 缺陷(§S3)                                                               |
| S4 | 批 2 webui 静态守阵(节 2 → 3 份)                         | ⬜  | skins(8) + panel(28) + page(27); + test.full 里程碑                                                                                                                    |
| S5 | 批 3 端点域(节 3 + 4 → traffic_qb + backend_misc + hr) | ⬜  | 18 + 37 + 51                                                                                                                                                        |
| S6 | 批 4 命令与视图域(节 5–9)                                 | ⬜  | commands(31) + views_reload(25) + admin(17) + seed_center(21); + test.full 里程碑                                                                                      |
| S7 | 批 5 结构守阵与长尾(节 10–15)                              | ⬜  | route_manifest(2) + keys(10) + skip_check(5) + longtail(28); 删原文件 + 一次性脚本                                                                                           |
| S8 | 收口验收                                              | ⬜  | 守阵全绿 + 新基线 + kb 回写                                                                                                                                                  |

## S1 勘察结论

### 现状实测(HEAD `34356f49`, 分支 `feat/test-web-split`)

| 指标                            | 数值         | 与计划差异                                                    |
| ----------------------------- | ---------- | -------------------------------------------------------- |
| test_web.py 行数                | **14,556** | 计划 14,367(规划基线 `0ae3212e`)                               |
| 顶层函数总数                        | **382**    | = 327 `test_*` + 2 `testhr_*` + 53 辅助                    |
| 被收集测试函数                       | **329**    | 计划 323                                                   |
| 被收集测试项(pytest --collect-only) | **337**    | `test_state_kind_maps_states` 参数化 ×9 展开                  |
| 文件内类                          | 2          | `_ListLogHandler`(L13760) / `module_log`(L13769), 均在节 13 |
| 顶层常量                          | 14         | 见归属表                                                     |
| docstring 计划条目                | **312**    | 计划 306; 0 幽灵, 17 函数无条目(存量缺口, 按计划 §3.3 不补写)               |

### 校验计划声明(逐条核对)

- ✅ **零跨文件导入** —— 全仓无 `import test_web` / `from test_web import`。
- ✅ **外部引用仅 2 处注释** —— `tests/helpers.py:277`(点名 `test_web.py::test_add_torrent_receipt_and_optional_flags`)与 `tests/test_facade_modules.py:39`(「与 test_web 同款」), S3 迁移时同步改。
- ✅ **pytest 配置零障碍** —— `pythonpath=src` + `testpaths=tests` + `-n 4 --cov-fail-under=98`, 平铺新文件自动收集。
- ✅ **唯一共享 fixture `web_env`** —— 及其私有依赖 `_make_web_manager`(内含嵌套 `_ensure_group_state`)。

### 节结构(注释标记实测, 当前行号)

15 节标记: 5892(流量) / 7884(HR refresh) / 7927(sites) / 8064(history) / 9390(命令) / 10399(强制汇报) / 10776(视图热重载) / 11624(管理端点) / 12229(种子中心) / 13067(W0 守阵) / 13209(快捷键) / 13512(跳检) / 13757(P1 运行时长尾) / 14126(P1 路由长尾) / 14370(v3 活尾)。节 1/2 无显式标记(隐式界: 节 1 = 代码起 L330 → L1111; 节 2 = L1112 → L5891)。


### 目标文件映射(329 fn 全覆盖, 零遗漏; 与 AST 清单逐名对账)

> 命名遵循计划 §3.1; 节 1/节 2 的聚类与命名由 S1 定稿(待 P-01 确认)。

#### test_web_auth.py  (14 fn, ~328 行测试体)

- test_api_requires_token
- test_config_public_endpoint_no_auth
- test_skip_local_verify_loopback_bypass
- test_skip_local_verify_cross_site_guard_host_whitelist
- test_skip_local_verify_cross_site_guard_write_origin
- test_skip_local_verify_cross_site_guard_all_write_endpoints
- test_skip_local_verify_cross_site_guard_credentials_bypass
- test_skip_local_verify_default_off_no_cross_site_guard
- test_auth_host_origin_parsing_helpers
- test_sse_ticket_flow
- test_sse_ticket_in_require_token_and_query_token_removed
- test_start_web_server_config_disables_proxy_headers
- test_frontend_sse_ticket_wiring
- test_skip_local_verify_default_off

#### test_web_api_core.py  (7 fn, ~158 行测试体)

- test_api_webui_flags_endpoint
- test_api_t_skip_check_gated_by_config
- test_api_status_and_groups
- test_api_expr_eval_endpoint
- test_static_assets_disable_heuristic_cache
- test_ui_root_and_legacy_newui_redirect
- test_frontend_ui_skin_cookie_persisted

#### test_webui_static_skins.py  (8 fn, ~627 行测试体)

- test_frontend_static_bundle_health
- test_frontend_template_split_wiring
- test_frontend_button_system_paired
- test_frontend_search_syntax_wiring
- test_frontend_search_pending_no_collapse
- test_frontend_hr_safety_wiring
- test_frontend_hr_detail_table_wiring
- test_frontend_hr_table_sort_filter_reorg_wiring

#### test_webui_static_dom_panel.py  (28 fn, ~1957 行测试体)

- test_frontend_qb_traffic_chart_wiring
- test_frontend_qb_traffic_window_persist_and_single_source
- test_drawer_tpl_registry_wiring
- test_drawer_tpl_variant_width_discipline
- test_drawer_tpl_variant_field_icons
- test_drawer_tpl_table_variants_scrollleft_restore
- test_drawer_tpl_a11y_and_fetch_error_states
- test_drawer_tpl_content_row_keyboard_roving
- test_drawer_tpl_cross_seed_fold_and_select_width
- test_drawer_tpl_select_fixed_width_tab_independent
- test_drawer_tpl_classic_default
- test_drawer_tpl_render_error_fallback_classic
- test_frontend_qb_traffic_drawer_page_guard
- test_drawer_seed_reentry_variant_remount
- test_frontend_drawer_collapsed_click_peek_target
- test_frontend_drawer_open_switch_no_empty_flash
- test_removed_redundant_tooltips_stay_removed
- test_recheck_confirm_wired_all_mouse_entries
- test_skip_check_dialog_precheck_wired
- test_skip_check_dialog_verdict_render
- test_modal_identity_stamp_landing_guard
- test_frontend_ctx_menu_multi_select_targets_selection
- test_frontend_meta_dialog_paired
- test_frontend_add_torrent_drag_drop_wiring
- test_frontend_add_combo_blur_close_and_fit
- test_frontend_ctx_menu_refit_by_measured_size
- test_frontend_add_combo_label_clear_mask_and_refit
- test_frontend_ctx_submenu_single_entry_and_hover_close

#### test_webui_static_dom_page.py  (27 fn, ~999 行测试体)

- test_frontend_hr_diag_view_wiring
- test_frontend_hr_full_modal_wiring
- test_frontend_hr_contract_keys_match_backend
- test_frontend_hr_history_wiring
- test_frontend_member_window_functions_live_in_methods
- test_frontend_computed_not_invoked_as_function
- test_frontend_template_no_reserved_prefix_identifiers
- test_frontend_dist_segments_aggregates_per_view
- test_frontend_cols_store_single_setitem_site
- test_frontend_persist_page_takes_intent_only
- test_frontend_col_manual_flag_not_revived
- test_frontend_cols_legacy_keys_have_migration
- test_frontend_cols_empty_hint_names_browser_clear_cause
- test_frontend_dir_browse_and_search_stale_guard
- test_web_store_iteration_snapshot_race_guard
- test_frontend_page_location_persisted
- test_frontend_unsaved_changes_guard_wiring
- test_frontend_expand_state_survives_view_switch
- test_frontend_hub_field_covers_non_leaf_items
- test_frontend_hub_field_renders_readonly_fields
- test_frontend_statusbar_speed_reads_server_totals
- test_frontend_bulk_bar_retired
- test_api_group_commands_enqueue
- test_api_group_malformed_key_returns_400
- test_api_delete_with_files_flag
- test_api_cmd_result_endpoint
- test_api_traffic_history_endpoint

#### test_web_traffic_qb.py  (18 fn, 节 3 流量半 —— P-01 拍板拆分)

- test_api_traffic_qb_disabled_empty_state
- test_api_traffic_qb_requires_token
- test_api_traffic_qb_window_validation
- test_api_traffic_qb_global_24h_points_totals_and_stale
- test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged
- test_api_traffic_qb_raw_seed_extension_window_start_baseline
- test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover
- test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band
- test_api_traffic_qb_global_30d_hour_segment
- test_api_traffic_qb_global_6mo_1y_day_segment
- test_api_traffic_qb_global_all_month_segment
- test_api_traffic_qb_torrent_endpoint
- test_api_traffic_qb_torrent_1y_single_agg_cold_read
- test_api_traffic_qb_global_24h_reads_only_involved_day_files
- test_api_traffic_qb_group_endpoint
- test_api_traffic_qb_group_30d_reads_member_agg_only
- test_api_traffic_qb_group_never_transferred_empty_state
- test_api_traffic_qb_group_member_only_zruns_not_empty

#### test_web_backend_misc.py  (37 fn, 节 3 杂项半 —— P-01 拍板拆分)

- test_config_schema_endpoint
- test_config_tree_roundtrip
- test_config_tree_invalid_rejected
- test_config_tree_requires_config_root
- test_config_tree_restart_field_fallback
- test_config_tree_preserves_comments
- test_web_token_not_printed_in_logs
- test_web_token_generated_atomic_and_readable
- test_web_token_existing_file_reused_without_rewrite
- test_web_token_write_interrupt_leaves_no_half_token
- test_config_tree_masks_secrets
- test_sites_missing_scans_and_builds_defaults
- test_sites_missing_name_conflict_suffix
- test_sites_missing_all_covered_returns_empty
- test_sites_missing_requires_connected_client
- test_sites_missing_api_failure_maps_502
- test_frontend_sites_import_wiring
- test_frontend_tracker_search_wiring
- test_frontend_dialog_combo_hover_takeover
- test_frontend_search_help_wiring
- test_group_key_codec_roundtrip
- test_build_group_view
- test_build_group_view_cross_group_conflict_flag
- test_build_group_view_member_num_seeds_fields
- test_build_group_view_group_aggregates
- test_member_view_extended_fields
- test_error_reason_from_tracker_msg
- test_error_reason_missing_files_without_api
- test_refresh_error_reasons_budget_and_ttl
- test_refresh_error_reasons_clears_when_recovered
- test_refresh_error_reasons_skips_when_disconnected
- test_build_group_view_hr_tags
- testhr_view_fields_three_state
- testhr_view_fields_excluded
- test_api_hr_status_disabled_returns_empty_state
- test_api_hr_status_reports_site_state
- test_api_hr_status_names_the_blocking_step

#### test_web_hr.py  (51 fn, ~1394 行测试体)

- test_api_hr_refresh_accepts_and_returns_requested
- test_api_hr_refresh_requires_enabled_hr
- test_api_hr_refresh_409_when_worker_not_running
- test_api_hr_site_entries_full_fields
- test_api_hr_site_entries_local_present
- test_api_hr_site_entries_verified_two_states
- test_api_hr_site_entries_empty_site
- test_api_hr_site_entries_guards
- test_api_hr_site_entries_409_worker_absent
- test_api_hr_history_rows_from_real_wave
- test_api_hr_history_site_filter
- test_api_hr_history_guards
- test_api_hr_history_limit_clamped
- test_api_hr_history_read_error_reported_not_raised
- test_api_state_excludes_hr_entry_details
- test_hr_user_visible_texts_no_graduation_wording
- test_api_hr_refresh_single_site_and_no_runtime
- test_api_hr_confirm_empty
- test_api_events_sse_stream_lifecycle
- test_api_events_sse_generator_error_still_unsubscribes
- test_frontend_hr_status_fields_match_backend
- test_build_group_view_hr_counts
- test_build_group_view_added_on_is_latest_member
- test_views_published_atomically_when_rebuilt_concurrently
- test_flush_views_marks_dirty_on_hr_revision_change
- test_flush_views_hr_facade_missing_null_defense
- test_build_search_index_files
- test_build_search_index_incremental_and_evict
- test_build_search_index_budget_resumes
- test_build_search_index_aborts_when_disconnected
- test_search_torrents_name_match
- test_search_torrents_separator_normalized
- test_parse_query_tokens
- test_search_torrents_cross_row_and
- test_search_torrents_negative_term
- test_search_torrents_negative_torrent_veto
- test_search_torrents_facet_rows
- test_search_torrents_phrase
- test_search_torrents_regression_envnv10
- test_search_torrents_negative_only_empty
- test_search_torrents_file_match
- test_search_torrents_building_triggers
- test_api_search_endpoint
- test_api_paths_endpoint
- test_api_open_path_endpoint
- test_api_fs_dirs_endpoint
- test_api_fs_dirs_case_sibling_is_outside_whitelist
- test_api_fs_mkdir_endpoint
- test_fs_endpoints_route_fs_calls_through_long_path_prefix
- test_fs_endpoints_unmapped_root_semantic_404
- test_fs_path_helpers_strip_long_path_prefix_before_compare

#### test_web_commands.py  (31 fn, ~1282 行测试体)  ← 节 5 + 节 6

- test_drain_web_commands_group_actions
- test_drain_web_commands_torrent_actions
- test_api_torrent_write_endpoints_enqueue
- test_api_t_bulk_group_keys_enqueue
- test_api_t_bulk_tags_category_enqueue
- test_api_t_bulk_limits_location_enqueue
- test_api_t_bulk_skip_check_enqueue
- test_drain_web_commands_torrent_write_actions
- test_drain_web_commands_torrent_write_unknown_hash_skips
- test_drain_web_commands_share_limits_and_queue_mapping
- test_drain_web_commands_torrent_write_param_errors
- test_drain_web_commands_bulk_torrents
- test_drain_web_commands_bulk_torrents_group_keys
- test_drain_web_commands_bulk_torrents_group_keys_mixed_and_missing
- test_drain_web_commands_bulk_torrents_tags_category
- test_drain_web_commands_bulk_torrents_limits_location
- test_cmd_trackers_write_invalidates_lazy_cache
- test_drain_web_commands_unknown_and_error_continues
- test_drain_web_commands_empty_queue
- test_verdict_reannounce_epoch_matrix
- test_verdict_reannounce_legacy_matrix
- test_verdict_reannounce_min_window_guard
- test_trackers_baseline_shape_and_epoch_mode
- test_reannounce_receipt_prefix_contract
- test_reannounce_confirm_success_and_timeout
- test_reannounce_confirm_group_aggregate
- test_reannounce_register_immediate_verdicts_and_deadline
- test_reannounce_stopped_midwindow_direct_verdict
- test_reannounce_background_verify_and_cap
- test_cmd_group_actions_skip_missing_group
- test_cmd_reload_config_delegates

#### test_web_views_reload.py  (25 fn, ~721 行测试体)

- test_ensure_group_view_rebuilds_when_dirty
- test_ensure_group_state_versioning
- test_ensure_group_state_show_view_carries_member_index
- test_build_singles_view_ungrouped_only
- test_build_singles_view_num_seeds_fields
- test_build_shows_view_aggregation
- test_shows_view_files_fallback_hook
- test_group_view_ver_seeded_from_start_time
- test_api_state_rid_gate
- test_api_state_skips_jsonable_encoder
- test_api_state_view_scoped_payload
- test_build_speed_totals_covers_ungrouped
- test_api_state_speed_totals_survives_view_scoping
- test_state_kind_maps_states
- test_apply_new_config_levels
- test_apply_new_config_l2_preserves_runtime_state
- test_stop_web_server_releases_port_for_restart
- test_start_web_server_started_message_is_info
- test_webui_module_apply_skips_restart_when_bind_unchanged
- test_start_web_server_reports_failure_when_port_taken
- test_web_loop_exception_handler_downgrades_connection_reset
- test_web_loop_noise_log_throttled_in_window
- test_web_loop_exception_handler_delegates_real_bug
- test_is_network_fluctuation_matrix
- test_uvicorn_config_installs_loop_exception_handler

#### test_web_admin.py  (17 fn, ~560 行测试体)

- test_api_category_tag_endpoints
- test_category_tag_commands_execute
- test_api_speed_mode_and_override
- test_api_speed_alt_and_toggle
- test_qbapi_alt_speed_limits_normalization
- test_api_speed_mode_curve_config_disabled
- test_api_add_torrent_endpoint
- test_add_torrent_receipt_and_optional_flags
- test_api_export_endpoint
- test_content_disposition_encoding
- test_api_category_tag_list_endpoints
- test_api_tags_exclude_auto
- test_api_log_endpoint
- test_api_log_level_filter_follows_config_format
- test_api_log_level_filter_keeps_multiline_record
- test_api_log_note_when_level_unfilterable
- test_webui_module_apply_toggle_enabled

#### test_web_seed_center.py  (21 fn, ~771 行测试体)

- test_seed_flat_view_fields_and_gating
- test_flat_view_refreshed_by_main_loop_tick
- test_rebuild_views_single_entry_point
- test_api_state_status_carries_server_state
- test_api_torrent_detail_endpoint
- test_api_torrent_subresources
- test_api_torrent_trackers_masked_response
- test_api_readonly_endpoints_short_cache
- test_api_torrent_peers_endpoint
- test_api_stats_endpoint
- test_api_enqueue_wakes_main_loop
- test_cmd_timing_is_logged_without_browser
- test_receipt_sent_immediately_truth_pushed_later
- test_affected_truth_reads_qb_directly_not_sync_snapshot
- test_truth_hold_matches_truth_push_cap
- test_cmd_trackers_log_sanitized
- test_cmd_remove_tracker_mask_roundtrip
- test_cmd_remove_tracker_same_host_distinct_passkeys
- test_tracker_edit_offline_route_and_static
- test_trackers_baseline_keys_are_raw_urls
- test_torrent_detail_trackers_route_mask_canary

#### test_web_route_manifest.py  (2 fn, ~33 行测试体)

- test_web_route_manifest_frozen
- test_create_app_is_thin_assembly

#### test_web_keys.py  (10 fn, ~276 行测试体)

- test_api_keys_get_default_when_missing
- test_api_keys_put_roundtrip
- test_api_keys_put_invalid_rejected
- test_api_keys_read_corrupt_fallback
- test_api_keys_unknown_schema_version_fallback
- test_drain_web_commands_recheck_rejected_while_checking
- test_drain_web_commands_bulk_recheck_skips_inflight
- test_drain_web_commands_bulk_skip_check_aggregated
- test_drain_web_commands_bulk_skip_check_gated
- test_drain_web_commands_skip_check_torrent

#### test_web_skip_check.py  (5 fn, ~232 行测试体)

- test_web_skip_check_completed_rejected_receipt
- test_web_bulk_skip_check_mixed_outcome
- test_web_precheck_endpoint
- test_web_force_passthrough
- test_webui_no_rules_import

#### test_web_longtail.py  (28 fn, ~699 行测试体)  ← 节 13 + 14 + 15

- test_web_runtime_notify_drops_are_counted
- test_web_runtime_check_pending_paths
- test_web_runtime_resync_elapsed_ms_logs_by_threshold
- test_web_runtime_set_result_prunes_stale_and_carries_truth
- test_web_runtime_affected_hashes_shapes
- test_web_runtime_affected_truth_queries_live_api
- test_web_commands_delete_with_files_and_reannounce_gone_receipt
- test_reannounce_group_empty_snapshot_error_receipt
- test_web_commands_recheck_and_skip_check_receipts
- test_web_commands_limits_partial_directions
- test_web_commands_rename_fs_folder_branch
- test_web_commands_bulk_argument_errors
- test_web_commands_bulk_missing_targets_reported
- test_web_commands_bulk_recheck_via_ops
- test_web_commands_add_torrents_receipt
- test_api_torrent_write_endpoints_extra_enqueue
- test_api_torrents_add_endpoint_errors_and_enqueue
- test_api_config_put_and_preview_tree_shape
- test_api_expr_eval_runtime_error
- test_api_keys_endpoint_roundtrip_and_validation
- test_api_keys_sanitize_rejects_non_dict
- test_api_category_and_tag_empty_rejections
- test_api_speed_mode_reads_client_with_alt_fields
- test_api_fs_error_semantics
- test_api_traffic_qb_global_live_tail_realtime
- test_api_traffic_qb_group_live_tail_member_only
- test_frontend_toast_duration_floor_by_kind
- test_aq_tip_anchor_watch_and_reacquire_wired

**合计 329 fn**(= 327 `test_*` + 2 `testhr_*`), 落 **16 个**目标文件(计划 15 —— 节 3 按拍板拆两份)。

### 共享件归属(实测「定义→使用」传递闭包; 按 P-02 拍板落法)

**唯一 fixture → `tests/conftest.py`**: `web_env`(conftest 内以 `from webui_helpers import _make_web_manager` 拿私有依赖)。

**跨文件非 fixture 辅助 + 常量 → 新建 `tests/webui_helpers.py`(16 辅助 + 3 常量)**, 由各测试文件按仓库既有 `from helpers import ...` 模式显式导入。**为什么不全放 conftest**: 非 fixture 放 conftest 需各文件 `from conftest import ...`(仓库零先例), 且 `_make_web_manager`/`_web_stub`/`_free_port` 均被测试**直接调用**(见 L6692/11256/11390 等), 必须可导入 —— 故除 fixture 外的共享件走模块。

| 名                                                                                | 被哪些目标文件使用                                 |
| -------------------------------------------------------------------------------- | ----------------------------------------- |
| `_make_web_manager`(含嵌套 `_ensure_group_state`, ~164 行)                           | 14 文件(含 web_env 内调用)                      |
| `_web_stub`                                                                      | admin / views_reload                      |
| `_ui_manifest` / `_ui_shell_inline` / `_ui_aggregate` / `_tpl_path`              | skins / panel / page / hr / backend_misc  |
| `_ui_css_files` / `_ui_css_aggregate` / `_app_bundle_files` / `_app_bundle_text` | skins / panel / page                      |
| `_enable_qb_traffic`                                                             | api_core / longtail / traffic_qb          |
| `_qb_v4`                                                                         | longtail / traffic_qb                     |
| `_hr_status_env`                                                                 | hr / backend_misc                         |
| `_make_grouped_manager`                                                          | commands / keys / longtail / views_reload |
| `_iter_api_routes`                                                               | auth / route_manifest / seed_center       |
| `_attach_live_tail_host`                                                         | longtail / traffic_qb                     |
| `KEY` / `STATIC_ROOT` / `_UI_ALL`                                                | 顶层常量(多域共用)                                |

**随唯一使用域(36 个辅助 + 11 个常量)**: `_auth_request`→auth; 静态扫描器群(`_assert_tags_balanced`/`_scan_css_blocks`/`_scan_css_comments`/`_scan_template_transitions`/`_scan_js_syntax_with_node`/`_section_members`/`_scan_mixin_wiring`/`_scan_episode_member_hashes`/`_scan_state_rank`/`_scan_pending_settle`/`_computed_body`/`_strip_js_comments`/`_scan_filter_facets`/`_scan_page_class_wiring`/`_scan_backdrop_filter`/`_extract_column_keys`/`_scan_column_cells_paired`/`_scan_progress_val_parity`/`_scan_frontend_assets`/`_scan_ui_diff_registry`)→skins, `_computed_member_names`/`_bundle_iter`→page, `_qb_open_spy`/`_v4_opens`→traffic_qb, `_site_scan_env`/`_tracker_calls`/`_WEB_MGR_CFG`→backend_misc, `_epoch_tracker`→commands, `_free_port`/`_grab_web_logger`/`_noise_loop`/`_reset_noise_state`/`_pin_noop_sections`→views_reload, `_log_lines`→admin, `_mk_mgr_with_one_torrent`→seed_center, `_keys_headers`→keys; 常量 `_DT_REGISTRY_NODE_PROBE`/`_DT_FALLBACK_NODE_PROBE`/`_NODE_QB_TRAFFIC_PROBE`→panel, `_NODE_HRS_SORT_PROBE`/`_NODE_SYNTAX_CHECK`/`_CSS_CONTAINER_AT`/`_EP_MEMBERS_RE`/`_PAGE_HOOK_CLASSES`/`_PERF_BACKDROP_BANNED`→skins, `_GOLDEN_ROUTES`→route_manifest。

**内聚随节 13**: `_ListLogHandler`(L13760) + `module_log`(L13769) → test_web_longtail.py(外部零引用)。

### P-01/P-02 拍板结果(2026-10-08, 用户裁决)

| #     | 议题       | 计划原文                                                                     | S1 实测                                    | **拍板**                                                                                                       |
| ----- | -------- | ------------------------------------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| P-01a | 节 3 目标文件 | `test_web_traffic_qb.py`(55 fn)                                          | 55 fn 中仅 **18** 是流量                      | **拆两份**: 18 流量 → `test_web_traffic_qb.py`; 37 杂项 → `test_web_backend_misc.py`。文件数 15→**16**                  |
| P-01b | 节 2 对半命名 | `test_webui_static_dom_*.py ×2`                                          | 内容可分 panel/page                          | **按内容分**: `test_webui_static_dom_panel.py`(28 fn) + `test_webui_static_dom_page.py`(27 fn)                   |
| P-01c | 节 1 切分   | auth + api_core(共 21)                                                    | 14 + 7                                   | **维持 14/7**(`test_api_t_skip_check_gated_by_config` 归 api_core)                                              |
| P-02  | 共享件归宿    | web_env + \_make_web_manager + \_ensure_group_state → conftest(增量 ~40 行) | 17 跨文件辅助 + 3 常量; 非 fixture 不能只放 conftest | **fixture → conftest**(仅 `web_env`); **非 fixture 辅助 + 常量 → 新建 `tests/webui_helpers.py`**(16 辅助 + 3 常量), 显式导入 |

**可选未采纳项**: 节 3 杂项里的 6 个 HR 系测试(`test_api_hr_status_*` ×3 / `testhr_view_fields_*` ×2 / `test_build_group_view_hr_tags`)按「拆两份」留在 `test_web_backend_misc.py`(未并入 hr, 以保 `test_web_hr.py` = 51 与计划 §3.1 一致); 如需并入 hr, 说一声即可。

**收口口径**: 目标文件 **16** 个(计划 15); 校验① 面 = **329** 函数; 校验③ 条目守恒 = **312**。

> **S2 实测纠偏**: 本节的「16 辅助 + 3 常量」漏了**日志辅助类** —— `module_log` 被 3 个目标文件使用(commands / keys / longtail), `_ListLogHandler` 经其传递亦跨 3 文件 ⇒ 二者随共享件进 `tests/webui_helpers.py`。共享件实为 **21 项**(16 非 fixture 辅助 + 3 常量 + 2 类)。详见 §S2。

## S2 拆分工具与红验(2026-10-08)

**工具**: `scripts/split_test_web.py`(一次性)。机制: AST 顶层语句按「gap 归属」(上一语句 end+1 .. 本语句 end)切块 —— 每条源行恰属一块, 前置节标记注释随其后第一个函数走; 映射表(读本档 §目标文件映射)+「定义→使用」传递闭包定归属(跨多文件→`webui_helpers.py`; 恰一文件→随该文件; 跨文件 fixture→conftest); 每文件 import 头按 used-names 裁剪(保留原分组), docstring「## 测试计划」条目按函数名逐条重分布(**逐字取源行**)。批次模式 `--rewrite-source` 改写源文件(余量为空则删), `--emit-conftest` 上收 fixture, `--files` 选子集。

**校验 4 条(内建)+ 2 条加强**:

| # | 校验                                 | 钉住的失败形态             | 演练实测               |
| - | ---------------------------------- | ------------------- | ------------------ |
| 1 | 集合恒等(源测试函数名集合 == 输出并集)             | 漏迁 / 丢函数            | 329 == 329         |
| 2 | 计数各恰一次                             | 重迁(同名两处)            | 0 dup              |
| 3 | docstring 反幽灵 + 条目守恒(源侧计数钉 312)    | 幽灵条目 / 漏登           | 312 == 312         |
| 4 | 可编译 + `pytest --collect-only` 计数恒等 | import 裁剪错 / 常量落错文件 | 337 项 / 329 名 == 源 |
| + | 内容守恒(所有顶层块落到某输出文件)                 | 块被静默丢弃              | 0 lost             |
| + | 行守恒(输出块体逐行 == 源行多重集)               | 行被改写 / 丢失           | 14,180 行 == 源      |

**演练(不触生产)**: 输出到 `R:/Temp/auto-qb/split-drill-s2`(testpaths 之外, 防误收集) → 校验 1-4 + 内容/行守恒**全绿**; `pytest --collect-only` = **337 项 / 329 函数名**, 与源 `tests/test_web.py` 逐位持平。

**红验 3 条(§5.3, 先红后修)**: 全部在**临时副本**上注入(不触生产档案/源文件); 基线绿 → 注入必红 → 撤回复绿 = **6/6**。证据:

| 注入                    | 命中(实测)                                                              |
| --------------------- | ------------------------------------------------------------------- |
| 映射表划走 1 函数(漏迁)        | rc=1 `[校验1] 源被收集测试函数 328 != 应 329` + `源有测试函数但映射表未列(漏迁) 1 个`         |
| 映射表同函数指两文件(重迁)        | rc=2 `拆分中止: 映射表重复条目: test_api_requires_token`(载入期 fail-fast, 早于校验②) |
| docstring 条目名改不存在(幽灵) | rc=1 `[校验3] 源 docstring 幽灵条目(无对应函数)`                                |
| docstring 整行删掉(漏登)    | rc=1 `[校验3] 源 docstring 条目 311 != 应 312`                            |

**S2 实测对 §S1 的两处纠偏**:

- **日志辅助类跨文件, 非「内聚随节 13」**: 计划 §3.2 / §S1 说 `module_log` + `_ListLogHandler` 随节 13 进 `test_web_longtail.py`; 实测 `module_log` 被 3 个目标文件使用(commands L10691/10703/10721/10743 · keys L13416/13446 · longtail L13901+), `_ListLogHandler` 经 `module_log` 传递亦跨 3 文件 ⇒ 二者归 `tests/webui_helpers.py`(否则要跨测试模块 import)。共享件实为 **21 项**(16 + 3 + 2 类)。
- **节标记注释随行搬移**: 「gap 归属」把 15 处节标记(`# ---- qB 口径流量图 ... ----` 等)挂到其后第一个函数 —— 节标记随其域落进对应新文件, 不丢行(内容/行守恒校验钉住)。

**踩坑**: `ast.get_docstring` 返回**求值后**的字符串, 会把源里的 `\\p{L}` 吃成 `\p{L}`(内容被改写 + 触发 SyntaxWarning) ⇒ 逐行迁移必须**从源行切片**取 docstring。已入 [pitfalls/testing/ast-migration-fidelity.md](../pitfalls/testing/ast-migration-fidelity.md)。

## S3 批 1 试切(2026-10-08)

**命令**: `uv run python scripts/split_test_web.py --out-dir tests --rewrite-source --emit-conftest tests/conftest.py --files test_web_auth.py,test_web_api_core.py --collect`

**产出**(实测):

| 文件                           | 行      | fn  | 说明                                          |
| ---------------------------- | ------ | --- | ------------------------------------------- |
| `tests/test_web_auth.py`     | 409    | 14  | 本地件 1(`_auth_request`) + 共享件 2              |
| `tests/test_web_api_core.py` | 189    | 7   | 共享件 2                                       |
| `tests/webui_helpers.py`     | 437    | —   | 21 件(16 非 fixture 辅助 + 3 常量 + 2 类), 全量一次性写出 |
| `tests/test_web.py`(余量)      | 13,567 | 308 | 改写后剩 308 fn                                 |
| `tests/conftest.py`          | 219    | —   | +`web_env`(197→219)                         |

**校验**: 校验 1–4 + 内容/行守恒**全绿**; `--collect` collect-only **337 项 / 329 函数名 == 源**; 块体行 14,180 逐行搬移。

**验证**: `test.one` = 14 + 7 passed; `test.quick` = **2771 passed + 4 skipped**; `test.full` = **2771 passed + 4 skipped / TOTAL 16476/165/5694/149 / 99%**(与开工基线切片 26-10-08-0258 逐位持平 ⇒ 纯移动)。

**活注释**: 同步改 2 处 —— `tests/helpers.py`(点名 `test_web.py::test_add_torrent_receipt_and_optional_flags` → `test_web_admin.py::…`)、`tests/test_facade_modules.py`(`与 test_web 同款` → `与 webui_helpers 同款`)。

**批模式暴露并修复的 4 处工具缺陷**(S2 只在**全量演练模式**验证过, 批模式(`--rewrite-source`)的校验器/余量渲染**从未演练**; 本次全部先红后修, 属计划 S3「管线缺陷在本批暴露完毕」的预期产出):

| # | 缺陷                                                                          | 命中现象                                 | 修法                                                               |
| - | --------------------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------- |
| ① | 校验1 在批模式下把 expect 误算成「余量函数」                                                 | `[校验1] 多出(源中不存在) 21 个`(选中文件里的函数被当多余) | expect 恒比**全量**(选中 + 余量并集仍 = 329)                                |
| ② | 内容守恒 `written` 未含「未选中目标文件桶」                                                 | `[内容守恒] 354 个块未落任何输出文件`              | 批内 `written` 并入 `file_order`(未选中桶都汇进源文件余量)                       |
| ③ | 余量渲染把 `helpers`/`conftest` 块也留在源文件(与独立文件重复); 行守恒 exp 又含未进 bodies 的 conftest | `[行守恒] 多 441 行`                      | 余量 `moved` = 选中 + 共享模块 + (上收时的 conftest); 行守恒从比对面扣掉已上收的 conftest |
| ④ | collect-only 批模式下收集整个 `tests/` 目录                                           | `rc=4` / 口径错                         | 改**显式文件列表**(选中 + 共享模块 + 改写后源文件)                                  |

**演练**: 先在 gitignore 的 `tmp-analysis/split-rehearsal/`(整 `tests/` 副本, 保 `STATIC_ROOT`/`sidefx` 相对路径)跑批, 全绿后再落生产; 演练副本已清理。

**S3 对 S1/计划的纠偏**:

- **活引用远多于 S1 声称的 2 处**: 全仓 grep(`test_web` 后非 `_`)发现 ~18 处活注释/文档串散布 `src/auto_qb/webui/**`(auth.py/server/**init**.py/commands.py/views.py/fs.py 等)、`static/shared/*.js`、`e2e/*.mjs`、`scripts/ui_harness.py`, 以及 **kb 活文档** `memory-bank/modules/rules-and-deps.md`(列测试文件)、`modules/webui-static-contract.md`(点名守阵)、`conventions/code-style.md`。S1 的「仅 2 处」只扫了 `tests/`。按**范围守恒**本批只改计划点名的 2 处, 其余留 **S8 全仓验收 grep** 统一处置 —— 且这些引用**多数指向后续批才迁的函数/守阵**(如 `test_frontend_page_location_persisted` 归批 2 `test_webui_static_dom_page.py`), 现在改反而会指向尚不存在的文件。
- **不新建基线切片**: `test.full` 数字与开工基线逐位持平; 计划 §S8 才落「新基线切片」, 中间批新建同值切片是噪声(沿用 S2 口径)。

## 进度日志

- **2026-10-08 02:40** 会话开工: `commands run my-commit-flow.sync` → `已同步 34356f49`。读计划全文 + memory-bank README/skill + 忆坑四篇(bulk-rename / parallel-run / single-file-coverage-gate / tmpdir)。
- **2026-10-08 02:4x** S0: 核对基线 —— 计划基线 2757 已陈旧; 开分支 `feat/test-web-split`; `commands run test.full` 复测 **2771 passed + 4 skipped / 16476-165-5694-149 / 99% / 53.59s**, 与切片 26-10-08-0223 逐位持平 ⇒ 沿用该切片作开工基线。
- **2026-10-08 02:5x** S1: AST 扫描(脚本落 `tmp-analysis/`)—— 382 顶层函数 = 327 `test_*` + 2 `testhr_*` + 53 辅助; `pytest --collect-only` = **337 项 / 329 函数**; docstring 条目 312(0 幽灵, 17 缺口); 节结构 15 标记; 辅助/常量「定义→使用」传递闭包 → 16 辅助 + 3 常量上收 conftest。
- **2026-10-08 02:5x** S1 门: 映射表 329 fn 全覆盖零遗漏, 与 AST 逐名对账通过; 四处分歧(节 3 命名 / 节 2 对半 / conftest 增量 / 计数漂移)记入 §P-01, 待用户拍板。
- **2026-10-08 02:5x** **P-01/P-02 拍板(用户裁决)**: ①节 3 拆两份 —— 18 流量 → `test_web_traffic_qb.py`, 37 杂项 → `test_web_backend_misc.py`(HR 系 6 条未并入 hr); ②节 2 按内容分 `panel`(28)/`page`(27); ③节 1 维持 14/7; ④共享件 —— 仅 `web_env` fixture 进 conftest, 16 个非 fixture 跨文件辅助 + 3 常量进新建 `tests/webui_helpers.py` 显式导入。据此目标文件数 15→**16**; 映射表与归属表按拍板重算并回写本档。
- **2026-10-08 02:58** 收尾(用户「提交」): DoD —— 复测 `test.full` **2771 passed + 4 skipped / 16476-165-5694-149 / 99% / 56.3s**(与上基线逐位持平), 新建开工基线切片 [26-10-08-0258](../testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md); 本档补 `**Refs:**` 认领链(挂基线切片); 切片「最后活动」刷新; `kb.index` 重建。
- **2026-10-08 03:05** 推送落地(用户拍板): `ship.commit` 提交成功(`e9f82d66`)但推送失败 —— 新分支 `feat/test-web-split` 在 Gitee 不存在, `run_sync` 取不到远端 ref 即报「拿不到远端」(新分支无法自举)。用户拍板**改落 `develop`**: `develop` 快进到远端 tip `1a5f0262` → cherry-pick 本次提交(`136a42bf`)→ `ship.push`; 临时分支删除, S2–S7 亦在 develop 上做。
- **2026-10-08 03:17** S2 会话开工: `commands run my-commit-flow.sync` → `已同步 591797e5`。**发现工作区脏**: 本档有一笔提交后写入的**陈旧草稿**(mtime 03:12:59 晚于提交 03:12:11, 缺 02:58/03:05 两条日志与 `**Refs:**` 行)⇒ 按「提交态为准」`git checkout --` 复原, 未把回退内容带进本批。
- **2026-10-08 03:2x** S2: 写 `scripts/split_test_web.py`(AST 切块 + 映射表读取 + 归属闭包 + import 裁剪 + docstring 逐条重分布 + 校验 4 条 + 内容/行守恒)。开发中修掉两处保真缺陷: ①`ast.get_docstring` 求值转义吃掉 `\\p{L}` → 改**从源行切片**取 docstring; ②`webui_helpers.py` 自我 import(共享辅助互相引用) → 共享名扣掉本文件已定义者。导入分组按源分组号保留。
- **2026-10-08 03:2x** S2 演练(不触生产): `--out-dir R:/Temp/auto-qb/split-drill-s2 --report --collect` → 校验 1-4 + 内容/行守恒全绿; collect-only **337 项 / 329 函数名 == 源**; 块体行 14,180 逐行搬移。
- **2026-10-08 03:2x** S2 红验 3 条(临时副本注入): 6/6 通过(基线绿 / 4 注入必红 / 撤回复绿), 命中行见 §S2 表。
- **2026-10-08 03:2x** S2 纠偏落档: 日志辅助类跨 3 文件(非「内聚随节 13」)→ 共享件 21 项; 新坑入 [pitfalls/testing/ast-migration-fidelity.md](../pitfalls/testing/ast-migration-fidelity.md)。`commands run test.quick` = **2771 passed + 4 skipped**(与开工基线逐位持平, 未动 tests/ 与 src/ 任何一行)。
- **2026-10-08 03:32** S2 收尾 DoD: `commands run test.full` = **2771 passed + 4 skipped / TOTAL 16476/165/5694/149 / 99% / 53.65s** —— 与开工基线切片 [26-10-08-0258](../testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md) **逐位持平**(本批只动 `scripts/` 与 kb 文档, 不触 src/tests) ⇒ **不新建重复切片**(两片全同是噪声); `kb.index` 重建、`kb.check` 全绿(仅存量「切片数 93 > 70」债务, 不拦提交)。
- **2026-10-08 03:50** S3 会话开工: `commands run my-commit-flow.sync` → `已同步 b6a5a588`; 读计划全文 + 任务档案 + 忆坑(ast-migration-fidelity / bulk-rename / single-file-coverage-gate)。工作区净。
- **2026-10-08 03:5x** S3 演练(不触生产): 先在 `R:/Temp/aqb-split-s3` 副本跑批 → **暴露批模式 4 处校验器缺陷**(仅全量模式验证过): ①校验1 误比余量 → 「多出 21」; ②内容守恒未含未选中桶 → 「354 块未落」; ③余量重复 helpers/conftest + 行守恒含 conftest → 「多 441 行」; ④collect-only 收集整 tests/ → rc=4。逐条修复(见 §S3 表)。
- **2026-10-08 03:5x** S3 修复后演练(保真): 在 gitignore 的 `tmp-analysis/split-rehearsal/`(整 `tests/` 副本)跑批 → 校验 1–4 + 内容/行守恒**全绿**, collect-only **337 项 / 329 名 == 源**; 两新文件 `19 passed`(2 失败为副本路径致 `STATIC_ROOT` 失准的演练假象, 生产无此问题)。副本已清理。
- **2026-10-08 03:5x** S3 生产落批: `--out-dir tests --rewrite-source --emit-conftest tests/conftest.py --files test_web_auth.py,test_web_api_core.py --collect` → 全绿; 产出 409/189/437 行新文件 + 余量源 13,567 行 + conftest +`web_env`。
- **2026-10-08 03:5x** S3 活注释: 改 `tests/helpers.py`(指向 `test_web_admin.py::…`)与 `tests/test_facade_modules.py`(`与 webui_helpers 同款`); 全仓 grep 另见 ~18 处活引用(S1 只扫 tests/ 漏报), 按范围守恒留 S8。
- **2026-10-08 03:5x** S3 验证: `test.one` 两新文件 **14 + 7 passed**; `test.quick` = **2771 passed + 4 skipped**; `test.full` = **2771 passed + 4 skipped / TOTAL 16476/165/5694/149 / 99%**(与开工基线逐位持平) ⇒ 纯移动。**不新建基线切片**(同值噪声; 计划 §S8 落终版)。
