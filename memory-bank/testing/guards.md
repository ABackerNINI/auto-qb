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
| `test_kb_files_respect_caps` | 每个文件 ≤ 其角色 cap | 往某文件塞内容超 cap |
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
| `test_grouping.py::test_group_key_of_is_single_source_of_truth` | 归组 key 纯函数 == 真实 mixin 输出 | 内联公式分叉 |

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
| `CORPUS.fs_mock_coverage` | FS mock 的入口覆盖(把探测换成 pathlib 必须红) | 换 `pathlib` |
| `tests/test_sidefx.py`(10 项策略单测) | 记账 / 放行清单判定 + **临时目录判定必须剥 `\\?\` 前缀** | — |
| `test_notify_real_send_blocked_under_pytest` | 测试期不发真实系统通知 | 去掉会话夹具 |
| `test_config_schema.py`(20 项) | UI 元数据 vs 配置键 / 插件**一致** | 加配置键不改 `schema.py` |
| `test_impact.py` | 分级表直测(未列出默认 L2) | 加配置项不补表 |

## 通用纪律

- **红验优先用运行时 monkeypatch 还原旧实现**(不碰工作区), `lru_cache` 记得先 `cache_clear()`。
- **一条守阵只钉一个结论**; 想同时钉两侧(过严 / 过松)就写两条断言 —— 只钉一侧会被"更严格"或"更宽松"两头骗过。
- **静态扫描类守阵必须先剥注释**: `os.path.normcase` / `colManual` 这些串就写在 docstring 与注释里当反例,
  纯文本扫描会被注释骗过(冒烟的 `_scan_filter_facets` 同理, 见 `_strip_js_comments`)。
- 相关坑的完整判据见 [../pitfalls/testing/assertions.md](../pitfalls/testing/assertions.md) 与
  [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)。
