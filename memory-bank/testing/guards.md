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

> **批次守阵外迁存档**: 主循环/WEB解耦 · 后端高风险动作 · S2-S6 四批次 · 仿真/语料/平台语义 · src 结构卫生 · 规则表达式内核 · 配置键面 · 提提交水线包 —— 原文 → [attachments/guards-batches-archive.md](attachments/guards-batches-archive.md) (节标题同名, 检索按守阵名)。

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
| `test_frontend_ctx_menu_refit_by_measured_size` | 浮层菜单开层**实测**钳位接线(issue 26-10-06-1717): `_menuFit` 按 `offsetWidth/offsetHeight` 算(常量估算回潮即红)且以视口为界 + 先复位兜底限高; 三个菜单容器 ref(`ctxMenu`/`headMenuEl`/`filePrioEl`)与三个开层 watcher 的 `(stateKey, refName)` 一一对上且都在 `$nextTick` 里量; `_menuFitRefit` 现读 `this[stateKey]`/`this.$refs[refName]` 并守 `visible` | 摘 `ref="ctxMenu"`(实测红在「ctx-menus.html 缺 ref」) |
| `test_api_state_skips_jsonable_encoder` | 热路径不得走 `jsonable_encoder`(计数替身; 清单排除 `/api/config/schema`) | `return payload` |
| `test_api_state_view_scoped_payload` | 按视图回传 + 未知 `view` 全回(保守默认) | 改 `VIEW_ARRAYS` |
| `test_ensure_group_state_show_view_carries_member_index` | 追剧页回传必须**连带成员索引**(groups+singles, 不回 torrents) | 只回 shows |
| `test_api_readonly_endpoints_short_cache` | 短缓存四边界: 窗口内合并 / **写命令后立即失效** / 断连仍 503 | 去掉失效接线 |
| `test_view_rebuild_waits_for_client_consume` | 上一版没被取走就不产下一版; **脏标记必须保留** + **`force=True` 必须绕过** | 去掉门控 |
| `test_api_fs_dirs_case_sibling_is_outside_whitelist` | 大小写兄弟目录判越界(**仅 Linux 真跑**, win32 skip) | 让 `_fs_real` 做 NTFS 折叠 |

## 流量聚合封口批次守阵 (26-10-13, 红验 26-10-13 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_traffic_store.py::test_v4_hour_agg_subsecond_coverage_floors_cov_to_one` | 小时行 cov_s 下限 1(行存在即有覆盖): `(0, 0.5]` 亚秒桶不再折 0 —— day/month 封口的 v4_rollup_agg 恒有 Σcov_s > 0 可上卷; 零覆盖仍 fail-fast; avg 仍按 float cov 加权 | 还原 `cov_s=int(round(cov))`(实测红在 `assert 0 == 1`) |
| `test_traffic_sample.py::test_agg_flush_subsecond_hour_rolls_up_without_raise` | 亚秒残余小时桶跨本地日封口时 hour + day 两行照常落盘(cov_s = 1) | 同上(实测红在 `ValueError: 逐级聚合无有效覆盖` —— 即真机报错原文) |
| `test_traffic_store.py::test_v4_merge_agg_same_epoch_reseal_keeps_coverage` | 同 epoch 重封合流: cov = 两段之和(非取残余) / avg 按 cov 加权 / totals 取后封行 / 桶宽截断 / 异 kind-epoch fail-fast | 让 `v4_merge_agg` 直接 `return row`(实测红在 `assert 1762 == 1838 + 1762`) |
| `test_traffic_sample.py::test_agg_reseal_merges_late_credit_keeps_full_coverage` | 已封小时被迟到补记重建再封时, 落批末行 = 合流行(cov 回到整小时), day 累计器同持合流行 —— 替换语义会让读侧末行只留残余 | 同上 + `_agg_merge_prev` 改 `return row`(实测红在 `assert 1762 == 3600`) |
| `test_traffic_sample.py::test_agg_flush_all_isolates_series_error_and_resets` | 逐系列隔离: 单系列封口抛错只告警该系列(节流一次)+ 重置其累计器, 其余系列照常落盘 | 去掉 `_agg_flush_all` 的 try/except(实测红在注入的 `ValueError` 直接上抛) |

## 种子状态 A 系批次守阵 (26-10-13-0540 S1 值层 / S2 deferral / S3 收尾, 红验 26-10-13 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_sync.py::test_own_writes_evicted_on_state_sync` | 自有写登记在「同步应用到该 hash 新 state」时逐出; 状态未变**不**逐出(保守) | 去掉 `_apply` 的 `if "state" in changed` 分支里的 `own_writes.pop` ⇒ 断言红 |
| `test_sync.py::test_own_writes_ttl_bounded` (D2) | 下限保证: `own_writes` 永不逐出时由 TTL 兜底丢弃(判据恢复 False) —— 不依赖「qB 缓存一定会前进」 | 去掉 `own_write_pending` 里的 `_evict_expired_own_writes()` ⇒ 超期判据恒真即红 |
| `test_sync.py::test_own_writes_group_judgement` | deferral 判据含**组维度**: 同组任一成员在 `own_writes` 即让位(组级闸门 G6/决策链 1 读组状态) | 去掉 `own_write_pending` 的组分支 ⇒ `HC` 断言红 |
| `test_sync.py::test_own_writes_not_persisted` (S2 静态) | `own_writes` 纯内存、不落盘(state.json 顶层无相关键) | 把 `own_writes` 绑进 `state.data` ⇒ 断言红 |
| `test_taskqueue.py::test_run_due_defer_gate_defers_then_resumes` (D-1 机制) | `run_due(defer_gate=...)` 命中者本轮不执行、以 `next_run=now` 重入堆下一轮再判; 放行后执行(有界) | 去掉 `run_due` 的 defer_gate 分支 ⇒ 首次即执行, 断言红 |
| `test_qbmanager.py::test_own_write_defer_gate_targets_group_members` (D-1 判据) | 队列级闸门: 目标 hash 或其组任一成员 ∈ `own_writes` 才让位; 无 hash 全局任务不拦 | 去掉组维度 ⇒ `HC` 断言红 |
| `test_ops.py::test_skip_check_deferred_on_own_write` (D-2) | 跳检执行路径: 目标或其组刚被自有停/起(快照未回流) ⇒ 让位, 零副作用(WEB 路径不经 task 线, 靠此拦) | 去掉 `skip_check` 入口的 `own_write_pending` 闸门 ⇒ 走完四阶段, `calls == []` 红 |
| `test_checking.py::test_checking_action_deferred_on_own_write` (D-3) | 决策链入口让位: 目标或其组刚被自有停/起 ⇒ 本轮不出决策(用 skip 非 pending, 避免丢任务) | 去掉 `CheckAction.execute` 入口的 `own_write_pending` 闸门 ⇒ 直接提交 recheck 红 |
| `test_sync.py::test_no_synthetic_state_write_site` (S1 静态) | 全库无合成 state 写点: 剥注释扫描 `qbapi.py`/`store.py` —— ① `update_torrent_fields` 调用块内无 `state=` ② 无 `.state=` 直接赋值 ③ 无 `setattr(..., "state", ...)` | 还原任一一处合成回写 ⇒ ①或②红 |
| `test_sync.py::test_value_layer_truth_only_via_sync` (V1 值层) | 停/起动作后快照 state **逐字不变**; 下一轮同步后 == 替身真值(含 `checkingUP` 等非四值枚举) | 残留合成写回 ⇒ 「逐字不变」红 |
| `test_sync.py::test_state_domain_not_flattened` (V2 值域) | 值域未被压平: 快照可持有 `queued*/forced*/checking*/moving/missingFiles` 且 state_enum 可解析(非 UNKNOWN) | 注入四值压平逻辑 ⇒ 断言红 |
| `test_grouping.py::test_own_stop_triggers_scan_on_next_sync` (E1 发射) | 自有停种经**下一轮同步回流**触发转移扫描(源无关, 与外暂停对称), 且不重复触发 | 屏蔽发射(谓词加「非自有」过滤) ⇒ 触发轮无 stop 即红 |
| `test_grouping.py::test_pause_via_qb_webui_and_autoqb_webui_agree` (E2 一致性) | qB 自身 WebUI 暂停 与 auto-qb WebUI 暂停 行为**逐字一致**(都触发缺文件扫描) | 两条路径结果不同 ⇒ 断言红 |
| `test_ops.py::test_g6_stale_snapshot_window_recovered_by_deferral` (D1 G6 端到端) | 三段式: ①陈旧快照下 G6 放行(**窗口存在**) ②`own_writes` 登记 ⇒ 跳检让位、零副作用 ③回流后 G6 恢复拦截(证明 deferral 是「推迟到新鲜时」而非「放弃保护」) | 去掉 `skip_check` 入口 deferral 闸门 ⇒ ②不再让位(且 G6 因陈旧放行) 红 |
| `test_actions.py::test_start_stop_idempotent_within_same_tick` (I1 幂等, A2) | 同 tick 二次 stop/start 被 `own_writes` **意图标记**拦下, 且**不写任何假 state 值**(快照逐字不变) | 用假值实现幂等(如回写 `pausedUP`) ⇒ 「逐字不变」红; 去掉幂等门 ⇒ 第二次不 skip 红 |

> A 系两批的语义主线见 [../plans/26-10-13-0540-plan-seed-state-writeback-removal-local-deferral.html](../plans/26-10-13-0540-plan-seed-state-writeback-removal-local-deferral.html);
> 口径漂移(「qB 自带 WebUI 1500ms」→ 服务端 `RefreshInterval` 节流)见 [../systemPatterns/main-loop.md](../systemPatterns/main-loop.md)。
> deferral 纪律(校验类不得对自写 hash 出决策 + 有界性双依据)见 [../pitfalls/backend/concurrency.md](../pitfalls/backend/concurrency.md)。

## 通用纪律

- **红验优先用运行时 monkeypatch 还原旧实现**(不碰工作区), `lru_cache` 记得先 `cache_clear()`。
- **一条守阵只钉一个结论**; 想同时钉两侧(过严 / 过松)就写两条断言 —— 只钉一侧会被"更严格"或"更宽松"两头骗过。
- **静态扫描类守阵必须先剥注释**: `os.path.normcase` / `colManual` 这些串就写在 docstring 与注释里当反例,
  纯文本扫描会被注释骗过(冒烟的 `_scan_filter_facets` 同理, 见 `_strip_js_comments`)。
- 相关坑的完整判据见 [../pitfalls/testing/assertions.md](../pitfalls/testing/assertions.md) 与
  [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)。
