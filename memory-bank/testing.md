# Testing — 测试指南

> **单点事实源**: 全库的测试基线数字 (passed/skipped/覆盖率/耗时) 只在本文件维护 — README/AGENTS.md/progress.md 等一律引用此处, 更新基线时只改这里。

## 运行

```bash
# 依赖统一 uv 管理 (pyproject.toml + uv.lock, 2026-09-15 起); 首次/依赖变更后先 `uv sync`
# 基线: **1142 passed (Windows 本地, 0 skipped) / Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)** —— 2026-09-21 实测;
#   ↑ 1142 → 1142(**不变**; 2026-09-21 二次: 种子页筛选器取数面 + 真值覆盖时序修复只**加断言**,
#     未新增用例 —— `test_frontend_static_bundle_health` 内新增扫描器 `_scan_filter_facets`
#     (筛选器选项必须走 `facetRows`/`_facetOptions` 单点; 旧按组实现 `_memberValueOptions` 复活即红),
#     经 **5 种注入违例红验**(含"把调用注释掉"——所以该扫描器先剥 JS 注释再判存在性, 见 `_strip_js_comments`)。
#     同批的浏览器冒烟断言见本节末「浏览器冒烟」)。
#   ↑ 1138 → 1139(列偏好第二次修复 +1: `tests/test_web.py::test_frontend_save_col_state_skips_widths_for_auto_pages`
#     钉死"未手动调过宽的页不得把自适应 px 落盘"; 与 `app.js::loadColState` 的"非手动页不读 px"成对,
#     防列宽被**别的窗口**算出的值整段覆盖(issue 26-09-20-1800 第二次修复)。
#     该 bug 前后四轮修复都没逮到 —— 单测全绿、冒烟全绿、**只在真机多窗口下现形**, 故必须静态钉; 守阵经**红验**。
#     ⚠ 守阵只能判**非注释代码行**是否含 colManual —— 只查字符串存在性会被注释骗过
#     (注释里正写着 colManual), 实测第一版守阵就是这么漏掉的(整行注释掉仍 passed)。
#     ⚠ 跑全量**别用 `--basetemp` 指到项目内或 `AppData\Local\Temp`**: `tests/sidefx.py` 的
#     `is_temp_path` 判定失效 ⇒ 冒出 4~5 条**假失败**(全是"临时目录内删除被判越界"), 与代码无关;
#     另 `H:\Temp\pytest-of-11059\pytest-current` 残留符号链接会 PermissionError。
#     ⇒ 本项目跑全量统一用 `--basetemp="H:/Temp/<新目录>"`, 实测干净。
#   ↑ 1137 → 1138(tracker / tag 脱敏映射 +1: `tests/test_sim_corpus.py` ——
#     auto-qb 自有标签字面量 MISSING / zSkipChecked 被伪名化后, 必须能反查回原文才能记进 meta 的
#     `sanitize_map.known_tags`。❗踩过的坑: 标签集合里存的是**已脱敏**的伪名, 拿原始字面量去 `in`
#     判断**永远为假** ⇒ 映射恒空 ⇒ 回放 config 仍写真字面量 ⇒ 跳检/缺文件行为与真机不一致。)
#   ⚠ 该批次还修掉一个**会让头号判据假绿**的坑: 只信"权威"的 tracker→tag 映射会漏掉语料里最大的
#     站点(35 个种子) ⇒ 那些种子被"未匹配 tracker 配置"跳过、**连带不参与归组** ⇒ group_exact 0 → 34。
#     改成"权威优先 + 统计兜底 + 只输出语料里真出现过的域名"后才回到 0(详见 pitfalls)。
#   ↑ 1133 → 1137(语料判据批次 W5 +4: `tests/test_sim_corpus.py` 续 —— 头号判据 `CORPUS.group_exact`
#     的比对内核 `group_exact_diff` 及三道红验: **成员串组(组数仍相同)、一组被拆成两组、真值组没被分出**
#     —— 只比"组数"会放过串组, 那正是"增量应用出错"的样子)。
#     另有 2 条运行期判据落地: `CORPUS.group_exact`(需 --web-port, 走 auto-qb `GET /api/state?view=group`
#     取**它自己**分的组, 不在 sim 侧重算 —— 重算会变"自己算的期望 vs 自己算的实际", 判据空转)
#     + `CORPUS.maindata_lag_modeled`(issue 26-09-20-2145 的验收凭据)。
#   ⚠ 阈值**两套不混用**(计划 §09): `plans/…baseline.json` 里 `corpus.*` 是语料档阈值、裸 id 是合成档;
#     `sim_run` 在语料档只查 `corpus.` 前缀、**不回落裸 id**。首次固化时合成档基线另存 `…synthetic.json`。
#     实测两套差得很远(corpus.P1.first_round_s 2.91 vs 22.68), 混用必然假红/假绿。
#   ↑ 1128 → 1133(语料时间轴回放批次 W4 +5: `tests/test_sim_corpus.py` 续 —— 末帧 closure 必须排除出可回放集合、
#     游标推进与窗口合并(后写覆盖 / server_state merge / 新增种子进状态)、fs_delta 按 t_seq 叠到磁盘状态、
#     `--latency-mode` 的 recorded 与 const 两条分支)。
#     另有 4 条 **CORPUS.*** 运行期判据落地在 `scripts/sim_run.py`(语料档专属, 合成档不出现):
#     replay_stream_consumed / replay_timeline_aligned(阈值按「轮询间隔 × 倍速 × 2 裕度」算, 不拍常数)/
#     fs_state_match / endpoints_covered —— 端到端 4 条全 PASS。
#   ⚠ 该批改 `scripts/` 三个文件 + `tests/` 一个文件, src/ 零改动; 既有 1128 条全部原样通过。
#   ↑ 1111 → 1128(语料回放批次 W3 +17: `tests/test_sim_corpus.py` —— FS mock 的拦截/作用域/长路径前缀与大小写/
#     未知路径计数/disk_usage 用录制值; **静态守阵 CORPUS.fs_mock_coverage + 红验**(把探测换成 pathlib 必须红);
#     窗口合并净额(先增后删 / 先删后加 / server_state merge / tags 按序末事件); piece hash 按内容集合派生
#     (同组共享 ⇒ 严格模式判据不恒假); 两层状态模型(**info 先可见 / maindata 后可见 + 无滞后时的红验**);
#     <FSROOT> 占位符解析; aborted 语料必须拒绝回放; 站点标签取"最专有"者)。
#   ⚠ 该批改 `scripts/` 四个文件 + `src/` **零改动**(归组纯函数那处已在上一批入库), 既有 1111 条全部原样通过。
#   ↑ 1098 → 1111(语料抓取批次 +13: `tests/test_qb_capture.py` +12 —— 脱敏等长/保形/保扩展名/
#     单射与确定性/短标签碰撞重派生/真实标签集零碰撞/路径三条等价类边界/v1v2 infohash 形状/
#     分组守恒绿 + **两道红验**(大小写被归一必须红、多成员组改一个成员路径必须红)/流累积器语义
#     (server_state merge、torrents 后写覆盖、*_removed 净额)/抖动与结构字段的判定口径;
#     `tests/test_grouping.py` +1 —— `test_group_key_of_is_single_source_of_truth` 钉死
#     "归组 key 纯函数 == 真实 mixin 输出"(防内联公式与纯函数分叉)。
#     范围: 语料计划 `docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html` 的 W1/W2。
#     ⚠ 该批**新增一个 scripts/ 文件** (`scripts/qb_capture.py`), 不覆盖 src/ —— 除 §04 那一处纯函数抽取外
#     src/ 一行未改, 故既有 1098 条全部原样通过(无退化)。
#   ⚠ **Linux 侧未同步重测**(本批只在 Windows 跑), 按本节上方纪律, 下次动基线时两侧一起补。
#   ↑ 1094 → 1098(本批 +4: `tests/test_web.py` 新增两道前端静态守阵 —— `test_frontend_member_window_functions_live_in_methods`
#     钉死"成员行窗口带参函数必须 methods 不得 computed"(防 Vue 3 getter 当属性调用导致整表白屏);
#     `test_frontend_dist_segments_aggregates_per_view` 钉死"状态分布按 viewMode 分支取数"
#     (防种子页 / 追剧页次导航统计全空)。两条都因 2026-09-21 一次两连 bug 落地 —— 修法均改两处前端 mixin,
#     单测看不见, 必须静态钉)。
#     实际: 1094 是当日已写好的 W3 收尾数字; 本批 +2(1096)→1098, 上一批 +2(1094→1096) 是领先
#     origin/develop 的两个 commit 已加但 testing.md 未及时更新的测试(本批一并补齐基线)。
#     (防种子页 / 追剧页次导航统计全空)。两条都因 2026-09-21 一次两连 bug 落地 —— 修法均改两处前端 mixin,
#     单测看不见, 必须静态钉。
#   ⚠ **Linux 侧未同步重测**(本批只在 Windows 跑), 按本节上方纪律, 下次动基线时两侧一起补。
#   ↑ 1062 → 1077(W1 `tests/test_expr_parse.py` +15: 词法字面量/单位、一层一运算符红绿用例、前缀形态、
#     函数调用、列表字面量、字面量类型冲突、AST 形状)
#     → 1094(W2/W3 `tests/test_expr_eval.py` +17: 取值面/求值/短路与缓存/运行期类型错误/静态语义校验/
#     数据源不可用与**配置期门控**/全局流量取值/**旧 16 条件 + 2 条 = 18 条等价对拍**)。
#   ⚠ **Linux 侧未同步重测**(这两轮只在 Windows 跑), 按本节上方纪律, 下次动基线时两侧一起补。
#   ❗TOTAL 覆盖率 91%; `src/auto_qb/rules/expr/` 未覆盖行主要是错误分支与防御路径。
# ❗两侧**收集数相同**(那 2 条在 Windows 上跑、在 Linux 上跳), 比较时别拿 "passed" 直接比:
#   Windows 1057 passed == Linux 1055 passed + 2 skipped。跳的两条都是 Windows 专属 ——
#   `test_sidefx.py::…`(AUMID 守卫: 非 Windows 无 winreg) 与 `test_ui.py::…`(注册表专属键)。
#   改了基线就把**两侧都重测**, 只测一侧就更新会立刻产生漂移
#   (本次就是把还停在 1049 的 Linux 数字补回来的)。
#   ⚠ WSL 侧重测要 `cp -r` 一份**到 ~/ 下**(不要放 /tmp): 仓库副本落在临时目录里会让
#     `test_sidefx.py::test_sidefx_is_temp_path` / `::test_sidefx_policy_flags_unknown_effects`
#     两条**假红**(2026-09-20 实测: /tmp 副本 2 failed, 同代码挪到 ~/ 即 0 failed —— 不是回归)。
# = 1055 + **主循环 × WebUI 解耦(docs/plans/26-09-20-0234-webui-decoupling-plan.html)** 新增 2 项:
#   ① `test_qbmanager.py::test_qbmanager_source_has_no_web_state_fields` —— **静态防回潮守阵**:
#      扫 `qbmanager.py` 源码不得再出现 19 个表现层字段名(`self._group_view` 等)。必要性在于
#      兼容代理 `_WEB_STATE_ALIAS` 会把这类回潮**静默转发** ⇒ 代码照样能跑、diff 里看不出问题,
#      只有扫描能抓住。红绿双验过(注入 `self._group_view = []` ⇒ 报 `['_group_view']`)。
#   ② `test_qbmanager.py::test_web_state_alias_proxies_to_runtime` —— 代理**只转发不存值**守阵:
#      旧字段名与 `self.web.<新名>` 必须读同一对象、写双向可见。若退化成"赋值进实例字典"就出现
#      两份真相(主循环改 runtime 那份、Web 线程读 manager 那份 ⇒ 视图静默停在旧快照且不报错)。
#   本次另改 3 处既有守阵的**目标**(不是判据): `_drain_web_commands` → `web.consume_commands`、
#   回执 spy → `web.set_result`、`_log_cmd_timing` 的宿主 → `WebUIRuntime`; 自投递静态守卫的正则
#   扩到同时认 `web_commands.put(` 与 `web.post_command(` 两种写法(否则重构后守卫直接失效)。
# = 1053 + **节拍对齐门控(issues/26-09-19-1900-bug-webui-poll-cadence-mismatch, 方案 B)** 新增 1 项:
#   `test_qbmanager.py::test_view_rebuild_waits_for_client_consume`(上一版没被 /api/state 取走就不生产下一版:
#   >3000 种子时服务端 3s 产 2 版而客户端只取 1 版 ⇒ 实测 20 周期 40 次 → **20 次(省 50%)**;
#   同时钉住两个边界: **脏标记必须保留**(只是不生产, 不是丢弃变化) 与 **force=True 必须绕过** ——
#   本轮有命令改了种子状态时必须立刻重建, 否则与 P0-5「真值几十毫秒内进快照」相悖。红绿双验过)。
# = 1052 + **热路径跳过 FastAPI `jsonable_encoder`** 新增 1 项:
#   `test_web.py::test_api_state_skips_jsonable_encoder`(用**计数替身**包住
#   `fastapi.routing.jsonable_encoder`, 断言 8 条 URL(7 个端点)调用次数为 0: /api/state?view=torrent、/api/state、
#   /api/groups、/api/search、/api/torrents/{hash} 及 /trackers、/files、/peers;
#   **清单里明确排除 `/api/config/schema`** —— 它的载荷含 dataclass(Group/Field/Plugin), 必须保留
#   编码器做转换(直返会 `TypeError: Object of type Group is not JSON serializable` ⇒ 500, 实测)。**这是"优化被后人重构掉"的守阵, 不是功能断言** ——
#   返回裸 dict 时 FastAPI 会先递归遍历整个响应体做一次 jsonable_encoder(3000 种子实测
#   **161 ms**, 占端点总耗时 189 ms 的 85%, 全程占 GIL); 改成 `JSONResponse` 直返即被
#   `fastapi/routing.py` 的 `isinstance(raw_response, Response)` 短路。刻意用计数而非计时:
#   计时在 CI 上不可靠。红绿双验过(注入 `return payload` → 报"走了 jsonable_encoder(1 次)")。
# = 1052 + **复核第二波(组/集乐观 BUG-3 + 追剧页空白 BUG-8 + 复制磁力 BUG-9 + 状态优先级表 BUG-7)** 新增 1 项:
#   `test_web.py::test_ensure_group_state_show_view_carries_member_index`(BUG-8: 追剧页的按视图回传
#   必须**连带成员索引** groups+singles, 但不回 4.5MB 的 torrents —— 只回 shows 时前端 memberByHash
#   为空, 每个集的成员都被 filter(Boolean) 丢掉, 刷新后停在追剧页会得到**永久空白**且不会自愈)。
#   另改 2 项既有测试的口径: `test_api_state_view_scoped_payload`(view=show 的期望从"只回 shows"
#   改为"回 shows+groups+singles"), `test_frontend_static_bundle_health`(静态守阵新增第 8 项:
#   `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致 —— BUG-7 就是两张表漂移, 人眼发现不了)。
#   2026-09-21 第 8 项**再补一条顺序断言**: `seeding` 必须严格排在 `paused` 之前(混合态取做种色,
#   用户口径) —— 逐项一致只管"两页同色", 管不了"同成哪个色"; `04cbc8e` 正是两表一起翻成 paused
#   才让辅种页组行变灰。红绿双验过(注入旧顺序 ⇒ 报"把 paused 排在 seeding 之前或同级")。
#   基线数字**不变**(只加断言, 未新增测试函数)。
#   BUG-9(复制磁力)与 BUG-3(组行 is-pending / 集行 epState)是纯前端, 由冒烟覆盖;
#   `tests/helpers.py::FakeTorrent.to_dict` 是**桩保真度**修复(缺它则详情端点恒 500, 详情抽屉与
#   依赖详情的编辑对话框在冒烟里从未被跑过), 不影响单测基线。
# = 1051 + **复核缺陷修复批(1~4 + 8~9)** 新增 2 项(均为「接线」断言, 红绿双验):
#   `test_qbmanager.py::test_drain_web_commands_bumps_write_seq`(P1-4 失效接线: 写命令执行后
#   `_web_write_seq` 必须自增, **自投递命令不得自增** —— 此前全仓只测缓存机制、没测接线,
#   字段改名或把自增挪走都会让测试全绿而只读缓存静默永不失效);
#   `test_drain_bumps_write_seq_before_writing_receipt`(BUG-5 顺序: 用 spy 观察 `_set_web_result`
#   内部看到的序号 —— 回执必须先失效缓存再宣布成功; 旧顺序下实测报 "实际 0 vs 期望 1")。
#   其余修复项(P1-2 间距实测 / 冒烟读数时机 / 文档漂移 / harness 限回环 / cmdStats 出口)不改单测基线:
#   前两项由**浏览器冒烟**覆盖(`P1-2 占位总高 == 全量渲染`, 见本节末), 后者为注释/脚本改动。
# 此前 1049 —— 波次三(P1-2 行窗口化)为**纯前端**改动, 未新增/减少单测 —— 由静态守阵
#   `test_frontend_static_bundle_health` + **真浏览器冒烟**覆盖(见本节末「浏览器冒烟」)。
# = 1046 + **WEB UI 响应性波次二(P1-5 超时 / P1-1 按视图回传 / P1-4 只读端点短缓存)** 新增 3 项:
#   `test_qbmanager.py::test_new_client_sets_request_timeout`(P1-5 守卫: 客户端必须带请求超时,
#   否则 qB 假死时主循环被占住、连重连退避都跑不起来);
#   `test_web.py::test_api_state_view_scoped_payload`(P1-1: view=torrent/show 只回该视图数组;
#   未知 view 回全部作保守默认; 版本一致时增量门控优先于 view);
#   `test_web.py::test_api_readonly_endpoints_short_cache`(P1-4: 窗口内合并重复请求 /
#   **写命令后立即失效** / 断连仍 503 —— 后两条是硬要求, 缺一条就会出现"改了没生效"或"断连被藏住")。
#   P1-3(updated() 去布局抖动)纯前端, 由静态守阵 + 浏览器冒烟覆盖, 无新增单测。
#   另: `test_web.py` 的 `_make_web_manager` 替身需同步 `ensure_group_state(rid, view)` 与
#   `_web_write_seq` 字段 —— 真实 manager 加了参数/字段后, 替身不同步就会 TypeError。
# 此前 1046 = 1041 + **WEB UI 响应性波次一** 新增 5 项, 见下。
# = 1041 + **WEB UI 响应性波次一(分层节拍 + P0-1 命令唤醒 + P0-5 命令后补刷新 + P0-0 埋点)** 新增 5 项:
#   `test_qbmanager.py::test_run_loop_layered_cadence`(同步线按 sync_interval / 任务线按 main_tick, 两线次数不等)、
#   `test_wake_drains_commands_without_extra_ticks`(命令唤醒只走命令线, 命令风暴下 tick 次数不增加)、
#   `test_drain_web_commands_reports_resync_needed`(P0-5 门控: 只有改种子状态的命令置 changed)、
#   `test_command_batch_triggers_single_resync`(P0-5 一批命令后只补**一次**完整刷新)、
#   `test_web.py::test_api_enqueue_wakes_main_loop`(投递用户命令唤醒主循环 + 自投递命令须登记防自激)。
#   ⚠️ 同时**改写**了 3 条既有用例的判据(不是新增): `test_run_loop_throttles_without_stop_event` /
#   `test_run_loop_managed_never_sleeps` 的阻塞原语从 `time.sleep(main_tick)` 换成 `_wait_next`
#   (按"真实经过时间"判定, 仍是防空转的回归守卫); `test_local_qb_service.py::test_main_loop_throttled_by_main_tick`
#   需把 sync_interval 一并设成 0.2 —— 两线不同拍时 `_tick` 只在两线同时到期才走到, 原"每轮一次 sync"假设失效。
# 此前 1041 = 修复前实测 1039 + **Linux CI 三处失败修复** 新增 2 项(`test_sidefx.py::test_sidefx_rmtree_dir_fd_entries_not_flagged`、
# `test_utils.py::test_atomic_write_rejects_empty_path`)。注: 修复前实测 1039, 比本文件此前记的 1038 多 1 —— 以实测为准,
# 下面链条里的 1036/1022 等历史基数不再逐一追平。历史链条: 1036 = 1022 + **架构审查 Wave 3/4 第二批** 2 项(`test_actions.py::test_stop_preserves_completeness` 暂停/恢复不得翻转完成位、`test_qbmanager.py::test_reconnect_backoff_and_reset` 重连指数退避与归零); 此前 1036 = 1022 + **架构审查 Wave 0/1/3/4 固化缺陷** 14 项: `test_utils.py` 原子写 3 项(`test_atomic_write_creates_file` / `test_atomic_write_failure_keeps_old_content` / `test_atomic_write_keep_backup`)、`test_checking.py` 跳检未确认也备份 1 项(`test_checking_skip_readd_unconfirmed_backs_up`)、`test_web.py` 密钥不进日志 + 配置树掩码 2 项(`test_web_token_not_printed_in_logs` / `test_config_tree_masks_secrets`)、`test_config_writer.py` 掩码还原 2 项(`test_mask_tree_hides_sensitive_scalars` / `test_unmask_tree_restores_from_disk`)、`test_config.py` 任务数范围校验 1 项(`test_validate_max_tasks_per_tick_range`)、`test_web.py` 视图并发原子发布 1 项(`test_views_published_atomically_when_rebuilt_concurrently`)、`test_tvshows.py` bare 集数 0 拦截 1 项(`test_bare_zero_not_episode`)、`test_conditions.py` HR 无站点判定 1 项(`test_hr_condition_no_tracker_conf`)、`test_web.py` 畸形分组 key 转 400 1 项(`test_api_group_malformed_key_returns_400`)、`test_notify.py` 免打扰不吃配额 + 去重表淘汰 2 项(`test_notify_quiet_hours_does_not_consume_quota` / `test_notify_throttle_dedup_table_evicted`); 此前 1022 = 1021 + 任务档案改名与索引生成化新增 `test_memory_bank.py::test_index_is_regenerated` 1 项; 1021 = 1018 + WEB UI **视图重建范围收口** 3 项(`test_flat_view_refreshed_by_main_loop_tick` / `test_rebuild_views_single_entry_point` / `test_api_state_status_carries_server_state`); 此前 = 1007 + **副作用记账器固化**(`tests/sidefx.py` 记账与判定策略 + `tests/test_sidefx.py` 10 项策略单测) + `test_notify.py` 1 项 "启用且不 mock" 真实路径回归; 此前 1007 = 1006 + **测试期禁止真实系统通知**(`tests/conftest.py` 会话夹具)新增 1 项 `test_notify_real_send_blocked_under_pytest`; 此前 1006 = 1001 + WEB UI **错误种子显示具体原因**(TASK015)5 项新测试: `test_error_reason_from_tracker_msg` / `test_error_reason_missing_files_without_api` / `test_refresh_error_reasons_budget_and_ttl` / `test_refresh_error_reasons_clears_when_recovered` / `test_refresh_error_reasons_skips_when_disconnected`; 此前 1001 = 1000 + `test_memory_bank.py::test_task_ids_and_slugs_are_unique` 1 项, 清理并行工作区 (当时是 worktree) 造成的重复档案时新增的结构守卫; 此前 2026-09-17 实测 1000, uv 环境; 修复导出 .torrent 的 latin-1 头崩溃 + `test_content_disposition_encoding` 后 = 999 + 1; 此前 999 = 第十轮 996 + 3 项 fs 端点测试; WEB UI 第十轮 16 项修复后 = 996 + `test_open_path_select_file_per_platform` + `test_api_fs_dirs_endpoint` + `test_api_fs_mkdir_endpoint` 3 项; **第十一轮 7 项前端修复后复核同为 999**(无新增后端逻辑, 改动由静态守阵 + 双 UI 浏览器冒烟覆盖), 前端改动不影响单测, 双 UI 模板/CSS 由静态守阵 + 浏览器冒烟覆盖), 分支覆盖率 92%(ui.py 窗口/托盘本体不单测, 真机冒烟验证; WEB UI 端到端为后端单测 + 临时 Fake 服务浏览器冒烟; 真实 HTTP 栈的集成测试用 `helpers.FakeQbServer` 本地假服务, 不连真实 qBittorrent; 注意: test_ui.py::test_autostart_windows_registry 真写 HKCU 注册表, 沙箱化 shell 里会因写入受限失败, 常规终端应通过)
uv run pytest tests -q                 # pytest.ini 已带 --cov=src --cov-report=term-missing --cov-branch
uv run pytest tests/test_grouping.py -q
uv run pytest tests/test_checking.py -q -k "skip"   # 按关键词
```

- `pytest.ini`: `pythonpath = src` (uv sync 也会把项目 editable 装入 venv, 双保险), `testpaths = tests`, addopts 含覆盖率 → 每次 pytest 输出 coverage 表 (会稍慢, 调试单个测试可加 `--no-cov`)。
- 测试**基本全部使用 Fake, 不连真实 qBittorrent**(随时可全量运行)。唯一例外是 `test_local_qb_service.py` + `test_ui.py::test_connect_failure_throttles_logging`: 它们用 `helpers.FakeQbServer`(标准库 `http.server` 监听回环随机端口)承载**真实** `qbittorrent-api`/requests 栈, 因为"trust_env 是否真的生效"“库重建 Session 是否弄丢我们的设置”这类行为在进程内替身上根本无法暴露(历史教训)。
- 覆盖率现状 (2026-09-19 实测, 全量): 总 92%; 低洼: `ui.py`(GUI 本体真机冒烟不单测); 近乎全绿: `config/impact.py`/`config/schema.py`/`logging.py`/`registry.py`/`taskqueue.py`/`qbapi.py`/`speed_curve.py`/`tracker.py` 100%, `notify.py` 98%, `utils.py` 98%, `qbmanager.py` 96%, `tvshows.py` 94%, `web.py` 92%(较 2026-09-14 的 75% 提升: 架构审查 Wave 0 补了配置掩码/密钥日志/畸形 key 等分支), conditions 99%。补测试优先看 term-missing 输出。
- **耗时实测 (2026-09-19, 空载, 波次一后)**: `uv run pytest tests -q`(含 `--cov-branch`)≈ **40 秒**; 加 `--no-cov` ≈ **30 秒**;
  Linux(WSL 沙箱, ext4)≈ **12 秒** —— Windows 慢约 3 倍, 差值主要来自 drvfs 与进程/文件操作。
- ⚠ **WSL 里不能直接复用 Windows 建的 `.venv`** (2026-09-19): 项目在 `/mnt/d/...` 上、`.venv` 是 Windows 侧
  `uv sync` 建的(`Lib/` + `Scripts/`)时, WSL 的 uv 会判定环境不兼容并试图删掉重建 ⇒
  `error: failed to remove directory .venv/Lib: Input/output error (os error 5)`, 而且可能把 Windows 侧的
  venv 弄坏。解法: **给 WSL 单独指定环境目录**, 不要碰共享的 `.venv` ——
  `UV_PROJECT_ENVIRONMENT=/tmp/aqb-venv uv sync && UV_PROJECT_ENVIRONMENT=/tmp/aqb-venv uv run pytest tests -q`
  (首次 sync 约几十秒, 之后 `/tmp` 里的环境可复用)。
  波次一新增的 4 条主循环用例用**真实睡眠**(0.05~0.6s)观测节拍, 共约 2s, 是耗时上升的主因; 判据用真实时间而非
  mock 时钟 —— 若换成 mocked sleep, 时间不前进会导致"两条线都不到期"的死循环, 用例会挂死而非失败。此前文档写的"约 12 秒"已过时 —— 另注意**不要并发起多个 pytest**: 本项目有绑定本地端口的 `FakeQbServer` 用例, 且 sidefx 守卫按**会话**记账(任何进程删了越界文件都会算到当前会话头上), 并发跑会出现假的失败。

> **图形化配置编辑器测试**: `test_config_schema.py`(UI 元数据与配置键/插件的**一致性守卫**, 20 项: 顶层键 vs `KNOWN_CONFIG_KEYS`、各段子键 vs `KNOWN_*_KEYS`、插件表 vs `registry`、kind/optional/enum 形态自检) 与 `test_config_writer.py`(结构化写回: 读取语义/校验拒绝不碰磁盘/注释与标量风格保留/增删键/R 级回退/预览不落盘/有损数字串不被规范化)。**新增配置键或插件时必须同步 schema.py**, 否则守卫测试直接失败。

## 测试文件约定

1. **每个测试文件头部 docstring 维护 "## 测试计划" 清单** — 项目明文规定: 新增测试必须同步更新对应文件的清单 (README 也强调)。
2. 文件名与被测模块对应 (`test_actions.py` ↔ `rules/actions.py`); 一个模块可以有多个文件 (如 test_rules_core/test_rule_base/test_rule_engine 拆分)。
3. 测试粒度小而多 (**1062 条**, 2026-09-20 Windows 收集数; 基线 passed/skipped 见本文件顶部), 名字用中文/英文短语描述场景。
4. **平台相关测试必须以 `monkeypatch` 固定平台** — GitHub Actions 跑在 Linux, 而本项目以 Windows 为运行环境。**判据是"本地全量绿"不算数**: 2026-09-19 Linux CI 一次红了 3 条, 全是"Windows 全绿 / Linux 全红"型 —— ①`shutil.rmtree` 在 POSIX 走 fd 版实现(传纯文件名 + `dir_fd`), 副作用记账器记到裸名字被判越界(76 条假阳性); ②`PlatformChannel("win32")` 里 `import winreg` 在 Linux 抛 `ModuleNotFoundError`, 而调用方只 catch `OSError`; ③`connect()` 真实连 `127.0.0.1:16585`, 是否抛异常取决于机器环境。修法与判别法见 [pitfalls.md](pitfalls.md)。验证 Linux 行为本机可用 WSL(见 pitfalls 同条)。纯 Windows 行为 (如长路径 `\\?\` 前缀) 的测试若直接断言, 在 Linux CI 上必失败 (2026-09-10 实测 3 例): `test_utils.py` 的 `test_add_long_path_prefix_for_win/unc/already_prefixed` 用 `monkeypatch.setattr(sys, "platform", "win32")` 模拟 Windows。规则: 测试主体行为的是"平台逻辑"而非"当前真实平台", 一律显式 monkeypatch, 不要依赖运行环境。
5. **`test_web.py` 不只测 FastAPI 路由**: 除鉴权/API/命令入队/设置读写/`?rid=` 视图版本门控/**静态资源 no-cache 响应头**/**前端静态资源守阵**(`test_frontend_static_bundle_health`: 冲突标记残留、JS 注释孤儿续行、**装了 node 时跑 `node --check` 真语法校验**、CSS 规则块漏闭合、`<transition>` 吞弹窗、模板引用的静态资源是否存在 —— 这类问题会让整页只剩背景色或整块功能静默失效)外, 还覆盖 WEB 功能的 manager 侧 —— 搜索索引构建与搜索、`_drain_web_commands` 各命令执行(含未知命令/异常的容错)、`ensure_group_view`/`ensure_group_state` 脏重建与版本自增、`_state_kind` 状态分类、`build_group_view` 字段(含单种子大小/总大小/标签/分类/保存路径/**组级 added_on 取组内最大值/组级 hr_triggered 与 hr_pending 计数**)、**错误原因展示**(TASK015: `_error_reason` 的 missingFiles→"文件丢失" / error→tracker `msg` / 非错误→空串, `refresh_error_reasons` 的预算与 TTL 限额、虚拟 tracker 条目跳过、离开错误态清空缓存、qB 断连跳过且不清值)、**HR 展示字段**(`hr_tag`/`hr_tag_done` 文本 + `hr_triggered`/`hr_satisfied` 布尔 + `hr_req_time`/`hr_req_ratio` 阈值)、`apply_new_config` 分级应用。找 WEB 功能的测试先看这个文件。`test_speed_curve.py` 另覆盖 **`_traffic_view` 只读快照**的各分支(disabled/ok 含 periods 与 target+actual/dry_run 无 actual/manual 原因/stale 的两种原因码)。

> ⚠ **前端渲染逻辑无法靠 pytest 覆盖**: 模板表达式错误(computed 当函数调用等)会让页面整块空白而测试全绿 —— 改前端必须做浏览器冒烟(假 qB + 临时 data_dir, 完事清理), 详见 [pitfalls.md](pitfalls.md)。**半个例外**: "整包 JS 语法损坏"(合并冲突残留、注释孤儿续行)与"模板引用缺失静态资源"属纯静态可判定, 已由 `test_frontend_static_bundle_health` 守阵(2026-09-17 实测白屏故障的防回归); 模板/表达式层面的错误仍只能靠真机页面看。
>
> ✅ **2026-09-19 起浏览器冒烟已脚本化, 不再"只能人工点"** ——
> **两条轨道: 首选 `agent-browser`(1.3.0 起 Windows 可用, 2026-09-20 已实测), 它不可用才回退 Playwright
> —— 本节下面讲的是回退轨道 `ui_smoke.cjs`。环境装在哪 / 为什么必须带 `NODE_PATH` / 换机器怎么自检**见
> [techContext.md](techContext.md)「浏览器自动化环境(两条轨道)」:
> `scripts/ui_harness.py` 起一个**真 `create_app` + 真 `QbManager` + `FakeClient` + 合成种子**的桩服务
> (`--torrents N --groups N --port P --cmd-result ok|error|hang --state-revert-ms N`), `scripts/ui_smoke.cjs` 用 Playwright 跑(**回退轨道**)
> prism/atlas 双 UI 断言(当前 **68 项 / 失败 2 项**(ok 模式; 两条均为**既有失败**, 见下)/
> **68 项 0 失败**(`--expect-cmd error`, 回滚路径; 单 UI 各 34 项)/
> **8 项 0 失败**(`--expect-cmd hang`, 3s 兜底路径; 单 UI 各 4 项),
> 含"轮询间隔按种子量分档"、"滚动到底不塌陷"、
> **P1-2 占位总高 == 全量渲染**(同一帧序列里对照开关两侧 —— 2026-09-19 加, 见下方读数时机坑)、
> **P0-4 批量合单数请求**、**P0-3 整组/整集/整剧乐观**(组行 / 集行 / **剧行**各自的 `is-pending`
> 与状态色翻转 —— 剧行是 issues/26-09-19-1959 补的第三层: 剧行默认折叠、集行不渲染, 只有剧行能显示"在飞")、
> **P0-3 补丁先于 POST**(注入 800ms 命令延迟仍要求 <400ms 出 pending, 见下)、
> **P0-3 乐观态及时落回真值**(80~1000ms, **带下界**, 见下方"真值对齐"条目)、
> **种子页筛选器有数据(计数=种子数)**(2026-09-21 加, 各 UI +1: 选项非空 + 计数 == 用 `vm.torrents`
>   现数的真值 + 弹层 DOM 真有项 —— 见 pitfalls「跨视图的常驻消费者」)、
> **真值事件后不被陈旧快照打回(值覆盖保持到快照同意)**(2026-09-21 加, 各 UI +1: `page.route` 注入
>   陈旧 payload ⇒ 行色必须不变、覆盖必须还在; 再由"快照同意"那一版收工 —— 红验撤掉修复即变红)、
> **BUG-8 刷新后追剧页不空白**、**BUG-9 辅种页复制磁力可用**)
> ⚠ **2026-09-21 实测: 68 项 / 失败 2 项**(两 UI 各一条 `P0-3 乐观态及时落回真值(80~1000ms)` —— 实测
>   pending 只活 17~21ms, **低于断言下界 80ms**)。**与两轮改动均无关**(两次都做了 A/B: 把被测表/修复
>   临时撤掉重跑, 失败项**完全相同**)。**根因已定性**(2026-09-21): 该断言**量错了对象** —— 下界 80ms 出自
>   D2 之前的语义("撤下"要等真值落地 ⇒ ≥120ms), 而 D2(`0c18fcd`)之后**压暗由回执结束**(17~20ms 是
>   设计使然), "等真值"那一段改由**值覆盖(pendingOps)**承担 ⇒ 应改量 `pendingOps` 的释放时刻
>   (harness 里约 150~250ms, 仍落在 80~1000ms 区间), 而不是量 DOM 上的 `.is-pending`。
>   **未改**(改闸门阈值属计划外, 按范围守恒留待定夺)。
> 另: 桩服务**会真的改状态**(2026-09-19 起, 否则"真值对齐"类断言只会测到"走满 3s", 跟没测一样),
>   并靠 `--state-revert-ms`(默认 1500)自愈 —— 真值**被 `/api/state` 取走后**再等这么久还原成初始状态。
>   没它的话长驻桩服务会跨轮累积: 跑过一次"整剧暂停"(合成数据里一剧 = 全部种子)之后, 下一轮冒烟
>   **所有行都是 s-paused**, 4 条"挑一个未暂停的行"的断言集体假失败(与被测代码无关)。
>   ❗回弹不能写成"生效后 N ms"的盲定时 —— 实测定时 4s 回弹把一次整组撤下拖到 4149ms
>   (回弹跑到了前端观测之前, 把真值又改回去了)。
> **命令埋点已补齐两段**: `patchMs`(点击→补丁贴上)与 **`settleMs`(点击→补丁撤下、行恢复正常)**。
>   缺后者正是"同一现象连报三次"的原因 —— 前三次修复全只埋了"贴上", 日志全绿、只能靠用户肉眼报。
>   `[perf]` 阈值按目标数分档(单目标 800ms / >100 目标 2500ms); 无回执(hang)只记不报(走 3s 兜底属设计)。
> 并**内置 A/B 基准**(同进程内关/开窗口化各跑 3 轮对比 refresh 与长任务)。
> 顺带一提: 换 `--torrents N` 跑不同规模的库, 就能量出"单轮 refresh 耗时 × 种子数"曲线 ——
> 前端轮询档位就是这么定的(1000:143ms / 3000:353ms / 5000:~550ms)。
> 典型用法: 起桩服务 → 跑 `ui_smoke.cjs` → 关服务(**完整命令与 `NODE_PATH` 见 techContext 同节**, 此处不重复)。
> 它验的是单测永远够不着的东西: 乐观 UI 的 pending→回滚、视图切换后的 payload 收敛、
> 滚动总高与末行可达、主线程长任务、**批量动作是否真的合成一条请求**(靠 `page.on("request")`
> 数 `/api/torrents/bulk` 与逐目标端点的次数 —— 这类"发了几次请求"的断言单测根本写不出来)。
> 改前端任何一处渲染/交互逻辑后**应当跑它**。
> ⚠ 新增断言务必**红绿双验**: 把被测优化临时关掉(如把 `bulkAct` 的合单分支短路成
> `if (false && …)`), 确认断言真的变红(实测拿到 "bulk 0 次 / 逐目标 60 次"), 再改回跑绿。
> 否则很容易写出一条"永远为真"的摆设断言。
> ⚠ **延迟类缺陷必须人为造慢才测得出来**(2026-09-19, issue 26-09-19-1939): 桩服务回执与本地
>   POST 都是**瞬时**的, 而真机大库下命令 POST 可达秒级 ⇒ "补丁贴在 `await POST` 之后"这种
>   **顺序型**缺陷在本地恒测不出来(冒烟"点击后立即可见 pending"一路 PASS, 直到用户真机肉眼报
>   "点了 2-4s 才变")。解法: 用 `page.route(CMD_URL)` 给命令 POST **注入人为延迟**(800ms),
>   再断言"点击 → `.is-pending`"仍 < 400ms —— 判的是"补丁贴在第几行", 不是"网络快不快"。
>   ❗Playwright 新版的路由谓词收到的是 **URL 对象**不是字符串(直接 `u.includes` 会
>   `TypeError`), 先 `String(u)`。点击时刻取**菜单项的 click 事件**(捕获阶段), 不要用
>   Playwright 的 `h.click()` 时刻 —— 那含鼠标开销(实测虚高 ~250ms)。
> ⚠ 两条反例(2026-09-19 实测, 都是"摆设断言"的变体, 且都真的漏过了缺陷):
> ① **恒真断言** —— `add(ui, "切到追剧视图无异常", epRows >= 0)` 永远为真, 于是"追剧页 0 行"
>   这种整页空白照样 PASS(BUG-8 就是这么溜过去的)。判据一律写成 `> 0` / 等值比较;
> ② **某种模式下恒红** —— 批量乐观那条断言在 `--expect-cmd error` 下 `pendingOps` 恒 0
>   (回执瞬间返回, 乐观窗口在采样前就关了) ⇒ 该模式必红 ⇒ 没人跑 error 模式。按模式分流:
>  ok/hang 断言"覆盖全部目标", error 断言"回滚干净"。**"恒红"和"恒真"一样会让断言失去意义。**
> ⚠ **"真值对齐"类断言必须设下界, 且桩服务必须真的改状态**(2026-09-19, issue 26-09-19-2024):
> ① 桩服务原本只回 `ok` **不改数据** ⇒ 真值永远不到 ⇒ 任何"pending 何时消失"的断言都只测到
>   "走满 3s 兜底", 跟没测一样。已加 `ui_harness.py::_apply_truth`(pause/resume 真改 `tor.state`
>   并 `rebuild_views()`), 且**先回执、后改状态**(`_TRUTH_DELAY=0.12`)复刻真机补刷新的错位。
> ② 只设上界(<1000ms)会被"假对齐"骗过去: 判定若拿**行上的当前值**跟补丁比, 而那值正是自己上一轮
>   贴的补丁 ⇒ 首轮必匹配、pending 22ms 就清, 断言绿得发亮却什么都没测到 —— 连"落回的是真值
>   (s-paused)"那条都照样绿(补丁值还留在行上, 看着就像真值)。**必须设下界**: 桩服务真值 +120ms
>   才落 ⇒ `clear` 落在 80~1000ms 才算数。红绿双验过: 把判定改回"拿行上的值比" ⇒ 22ms 变红。
> ③ error 模式没有"等真值"这回事(失败立即回滚 ~21ms), 给它套下界会恒红 ⇒ 按模式把下界置 0。
> ⚠ **hang 模式(命令永不回执)是第三种模式, 独占一轮跑**: `--cmd-result hang` +
>   `--expect-cmd hang` ⇒ 只跑 `hangChecks()`(双 UI **8 项 0 失败**), 判据 = pending 立即出现 /
>   3s 兜底清除 / **最终状态色 == 点击前**。
>   ❗它判的是「失败/未知绝不留永久假状态」在无回执场景下还成不成立, ok / error 两轮**都碰不到**
>   —— [26-09-19-2141](issues/26-09-19-2141-bug-webui-pending-timeout-stale-patch.html)(超时后补丁值
>   永久留在行上)就是这么溜过三道关口的。hang 下前端 `waitCmd` 超时是 40s, 混进主轮会把一轮拖到
>   十分钟, 故做成独立模式而不是主轮的一段。
> ⚠ 跑测用仓外 `--basetemp` 时, **该目录必须不存在**: 已存在则 pytest 开跑前会删它, 而本机
>   沙箱的删除拦截层会拉起回收站助手进程, 被 `tests/sidefx.py` 记成越界 POPEN ⇒ 全绿也会在
>   某个用例的 teardown 报 ERROR(实测复用旧目录得 `1052 passed + 1 error`, 换全新路径即干净)。
>   `COVERAGE_FILE` 同理要指到仓外(仓内 `.coverage` 会让覆盖率在启动时删仓内文件而中止)。
> 写冒烟脚本的三条硬约束: ①**必须 CJS**(不能 ESM); ②Vue 根实例走 `#app._vnode.component.proxy`
> (`__vue_app__._instance` 恒空); ③`playwright-core` 版本须与本机 chromium 对齐 —— 环境侧细节见
> [techContext.md](techContext.md)「轨道二」, 取实例与读数时机的坑另见 [pitfalls.md](pitfalls.md)。
5.5 **`test_sync.py` 专测增量同步层**: `TorrentRecord.apply_delta`(只遍历 patch 字段/变化字段集/量化/双通道源/`_raw` 兜底/`state_enum` 缓存)、`TorrentStore.apply_sync`(首轮全量/增量只改变化记录/无变化零成本/增删/全量剪除/待报删除/降级/异常/`reset_sync`)、以及 QbManager 接线(增量轮不做 schema 校验、变化集与冲突脏组)。改 `torrents.py` 的同步层或 `_refresh_torrents` 时必须同步此文件。
6. **`test_impact.py` 直接测分级表而非被测端**: 用真实 `Config()`(字段默认即全默认实例) 构造新旧配置做 diff, 分级表外字段用 `SimpleNamespace` 替身(验证“未列出默认 L2”); 含 `_diff_flat`/`_diff_trackers`/`max_level`/`restart_required_paths` 直测。**改分级表或新增配置项时必须同步此文件**(新增配置项未补表 -> 默认 L2, 分级错误会让热重载静默不生效或误要求重启)。
7. **`test_memory_bank.py` 守知识库结构**(2026-09-17 新增, 不覆盖 src): `_index.md` 登记项 ↔ `tasks/TASK*.md` **双向一致** / 文件名 `TASKnnn-slug.md` / 五个必备章节齐全 / 档案 `**Status:**` 与索引分区一致 / 索引保留四个状态分区 / **档案 slug 唯一 + 索引同一 TASKID 只登记一次**(2026-09-18 补: 并行工作区各自立档会产出逐字节相同的重复档案与重复索引条目, 而 dict 式解析会静默覆盖, 双向一致与状态分区两个守卫都漏) / **`activeContext.md` 不得出现 `^- 2026-` 流水账纪要行** / skill 载体存在且 `AGENTS.md` 与 `copilot-instructions.md` 均声明立档阈值并指向 skill。改 `memory-bank/` 结构或会话协议时必须同步此文件 (红绿验证过: 幽灵任务与纪要回流两类违例都会失败)。
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

## 5000 种子仿真测试（手动工具，不进 CI）

> **使用手册（怎么跑 / 怎么判 / 怎么回溯 / AI 调用约定）在
> [docs/sim-client-test-howto.md](../../docs/sim-client-test-howto.md)** —— 本节只放基线与约定要点。

> 独立 HTTP 仿真服务端 + 驱动器，用于 **5000 种子规模的安全 / 性能测试**。
> 脚本：`scripts/sim_qb.py`（仿真服务端，可独立运行）/ `scripts/sim_run.py`（驱动器，编排 + 断言 + 两层日志）/
> `scripts/sim_autoqb.py`（auto-qb 子进程启动包装，装 SIGBREAK 处理器以便优雅停机）/
> `scripts/sim_baseline.py`（一键跑 P1–P7 并固化阈值）。
> 计划与全部实测：[docs/plans/26-09-19-1433-sim-client-5000-plan.html](../../docs/plans/26-09-19-1433-sim-client-5000-plan.html)。
> **不进 CI**（跑数分钟且依赖 R 盘），手动跑；产物全落 `--root`（默认 `R:\auto-qb-sim`，环境变量 `AUTOQB_SIM_ROOT` 覆盖）。

### 为什么不是进程内替身

单元测试用 `FakeQbServer` 承载**真实** `qbittorrent-api` 栈（见上文），但**规模行为测不到**：
全量 sync 端到端 205–240 ms / 8.77 MB，增量 3.3 ms / 107 KB（**差 62 倍**）；
仿真端自己的 diff 策略也要跟着对（朴素全量 diff 22.6 ms vs 脏集合 0.34 ms，**差 67 倍**）——
否则测的是仿真器自己。

### 固化基线（W4，2026-09-19 实测：Windows 本机 / R 盘 / 回环）

文件：`docs/plans/26-09-19-1433-sim-client-5000.baseline.json`。
`sim_run.py` 启动时自动读取填阈值；**文件不存在时相关项记 `BASELINE`（不算 FAIL）**，
固化后同一指标即成硬判据。重跑：`uv run python scripts/sim_baseline.py`（`--only P1,P3` 跑部分 /
`--merge` 只覆盖重跑的场景 / `--dry` 只打印命令）。

| 阈值 | 值 | 来源 |
|---|---|---|
| `P1.first_round_s` | ≤ 22.68 | 实测 max 15.1 s × 1.5 |
| `S3.write_rate_per_min` | ≤ 6210.49 | 实测 4777.3/min × 1.3 |
| `S7.p95_ms` | ≤ 1218.4 | `/api/state` p95 609 ms × 2 |
| `SYNC.drift_max_s` | ≤ 1.0 | **纯主循环**场景实测 max 0.32 + 0.5（下限 1.0） |

❗**阈值候选集是分级的**：`--ramp`（渐进灌入）、`--stress`（压力档）、带 `--web-poll` 的场景
**不进** `SYNC.drift_max_s` 的基线 —— 否则阈值被抬到 1.77，会放走真正的稳态回归。
它们的漂移另记 `P2.drift_max_s` 观测（不判红）。

### 关键实测数字（速查）

- **首轮灌入**：5000 种子 **14.4 s**（回环）≈ 15 754 次请求 ≈ 0.96 ms/次 —— 每新种子约 2 次内联请求
  （`torrents/trackers` + `torrents/files`），**在 `_refresh_torrents` 里逐个内联跑，不受 `max_tasks_per_tick` 约束**。
- **稳态**：tick 2.0 与 1.5 两档都跟得上（漂移 < 0.35 s）；删除风暴反而更轻（种子少了）。
- **任务吞吐**：**10.6 任务/s**（= `max_tasks_per_tick 20 ÷ tick 2 s`）。
  执行周期 ≈ `(1+规则数) × 种子数 ÷ 20 × tick`：5000 种子 R=1 → 8.3 min，R=2 → **16.7 min**。
- **写请求放大一倍**：`qbittorrent-api` 每次写前额外查一次 `app/webapiVersion`（库内无缓存），
  trace 里其命中数恒等于写请求数。
- 归因与改进建议见计划文档第 13 节（W5，只出结论未动代码）。

### 判据设计约定（踩过的坑，详见 pitfalls.md）

1. **外部删除必须经 `torrents_removed` 上报** —— 否则 auto-qb 快照里全是幽灵，判据全绿但什么都没测到。
2. **别只看写台账判"种子是否还在"** —— 打标签是一次性的（state 记过就不再写）。
   要直接问 auto-qb：开 `--web-port` 轮询 `/api/status` 的 `torrents`（= `len(store.by_hash)`）。
3. **别硬 kill auto-qb** —— Windows 上 `terminate()` = TerminateProcess，`finally` 不跑 ⇒ `state.json` 不落盘；
   原生 `CTRL_BREAK_EVENT` 也只得到 0xC000013A。必须经 `sim_autoqb.py` 启动（装了 SIGBREAK 处理器）。
4. **停机前先让观测/轮询收手**（`quiesce`）—— 否则半截请求让 uvicorn 抛 h11 异常栈，污染 `LOG.tracebacks`。
5. **断言"某保护生效"前先确认测试数据落在保护范围内** —— 例：项目约定**奇数 KiB/s** 才是
   "用户手动限速、程序不覆盖"（`utils.is_manual_speed_limit`），造偶数会被正常覆盖 ⇒ 假红。
