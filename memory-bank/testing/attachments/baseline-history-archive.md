# 测试基线 · 变更流水 (归档: 较老一段)

> 摘要: `baseline-history.md` 触顶后外迁的**较老一段**流水(append-only, 内容逐字未改); 新条目仍追加到主文件。
> 触发: 基线历史增量, 这个数字是怎么来的, 老流水归档

> 主文件: [../baseline-history.md](../baseline-history.md)(只保留最近 ≤ 16,000 字符)
> 本文件 = **较新那一段**归档; 更老的见 [baseline-history-old.md](baseline-history-old.md)。
> ❗链接已在切切时重写过一遍(`attachments/` 前缀已去掉) —— 否则在当前目录就是坏链。

- ↑ 1160 → 1169(**+9**; 2026-09-22 任务 26-09-22-memory-bank-dir-refactor **W1 基础设施**:
  知识库目录化守卫 9 条, 检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 守卫**进程内 import**
  (本项目测试禁止起子进程): `test_kb_index_is_regenerated` / `test_kb_index_and_files_are_bijective`
  (索引 == 生成结果; 索引 ↔ 目录双向一致)、`test_kb_topic_files_have_metadata` /
  `test_kb_files_respect_caps` / `test_kb_class_names_and_topic_filenames` (三行头元数据 / cap 分级 /
  类名与文件名)、`test_kb_no_orphan_index_dirs` / `test_kb_stubs_are_valid` (顶层索引都被 README 引用 /
  被拆文档留合法存根)、`test_kb_pitfall_entries_have_required_fields`、`test_kb_scripts_import_cleanly`。
  ⚠ 这 9 条是**结构性**的: 目录还没建时**空转通过**, 某个 `<文档>/` 一落地就自动生效 —— 故 W1 只增不减、
  既有用例零改动。两个例外按波次启用: `activeContext.md` 的 12 KB 硬顶(W4)与 `tasks/*.md` 的 24 KB(W7)
  仍在 `check_caps` 默认角色集之外 ⇒ 实测 `check_kb_structure.py --all` 现在**正好只报这两条**。
  另 `scripts/gen_tasks_index.py` 迁入 skill 的 `scripts/`(仓根该文件已删), 守卫改在进程内 import 它。
- ↑ 1152 → 1160(**+8**, 两批; 2026-09-22 issue 26-09-21-1347「state.json 损坏静默清空」守阵:
  `test_load_state_corrupt_falls_back_to_bak`(主文件损坏 -> 回退 .bak **并自愈写回主文件**;
  ❗自愈那条必须钉: 不写回的话下次 save_state 的 keep_backup 会把损坏内容复制成新的 .bak,
  唯一一份好备份被盖掉, 恢复等于白做 —— 红验(打回旧实现)下本用例必红) /
  `test_load_state_corrupt_without_backup_warns`(备份也不可用 -> 仍空状态但留两条 WARNING) /
  `test_load_state_missing_file_is_silent`(首启不得告警 —— 反向钉住"损坏 vs 首启"分开处置) /
  `test_load_state_recovered_writeback_failure_is_nonfatal`(自愈写回失败只告警、不抛 ——
  钉 `_write_back_recovered` 的异常分支: 它若把异常放出去, "有备份可恢复"反而比"没备份"更糟)。
  第二批 = 附带发现「孤儿 <state_file>.*.tmp 启动清理」(`_cleanup_orphan_tmp`, 持锁后才清):
  `test_cleanup_orphan_tmp_removes_only_state_leftovers`(只删 `<state_file>.<随机>.tmp`;
  **`.bak` 是关键反例** —— 清理一旦放宽成"同目录所有 .tmp", 就把唯一的恢复凭据删了; 并断言二次调用幂等) /
  `test_cleanup_orphan_tmp_missing_dir_is_nonfatal`(目录列不出只告警; 用打桩模拟, Windows 上 chmod 造不出) /
  `test_cleanup_orphan_tmp_delete_failure_is_nonfatal`(一个删不掉不得挡住其余) /
  `test_cleanup_orphan_tmp_is_wired_after_lock`(**接线守阵**: 源码里必须挂在 `self._lock.acquire()`
  之后且落在 `if not no_lock` 分支内 —— 防后来者把它挪到持锁之前)。
  另 `test_utils.py::test_atomic_write_keep_backup` 的备份路径断言改按 `path + utils.BACKUP_SUFFIX`(不写字面量)。
- ↑ 1149 → 1152(**+3**; 2026-09-22 issue 26-09-21-1347「跳检备份先于删除」守阵:
  `test_checking_skip_backup_precedes_delete_and_cleared_on_success`(在客户端的 torrents_delete
  里快照备份文件是否存在 —— 只查最终结果无法区分"之前写的"还是"之后补的")、
  `test_checking_skip_delete_unconfirmed_clears_backup`(删除未生效 -> 清备份, 不留孤儿)、
  `test_checking_skip_backup_failure_aborts_before_delete`(备份写不进 -> 不删除)。
  ⚠ 顺带把 `test_checking.py::make_mgr` 改成**未指定 state_file 时自动发一份临时 state 文件**:
  跳检现在每次都真实落盘/删除备份, 留空会写到 CWD=仓库根(污染仓库 + 被 tests/sidefx.py 判越界删除)。
- ↑ 1147 → 1149(**+2**; 2026-09-22 其四: B3 / D4 两段也从 `--self-test` 下沉 ——
  `test_safe_delete_rejects_bulk_over_declared`(B3 数量上限, **钉两侧**: 超 declared*2 要拒、
  恰好 2 倍不拒 —— 只钉一侧会被"更严格"或"更宽松"两头骗过) /
  `test_delete_group_files_removes_them_from_disk`(D4 删组文件, ❗必须走**合成档**:
  语料档是 `fs-mode=mock`, 磁盘上没文件 ⇒ `_walk()` 前后都是 0 ⇒ 判据**恒假**;
  故用例显式断言 `before > 0`, 把"没物化"变成红而不是绿)。
  红验各一次: B3 阈值改成 *99 ⇒ `DID NOT RAISE`; D4 改成"假装删了" ⇒ `assert 0 > 0`。
- ↑ 1146 → 1147(**+1**; 2026-09-22 其三: B2 段从 `sim_qb.py --self-test` **下沉**进
  `tests/test_sim_corpus.py::test_safe_delete_rejects_path_outside_fs_root` —— 原自检要真起 HTTP
  **且**真装 qbittorrentapi(没装就整段 return 0), **CI 从不执行** ⇒ 下沉后进两平台 CI。
  比原自检多钉两条: 拒绝时**文件没被真删** + **记进 violations**(否则"拒了但没记账"看不出来)。
  红验: 把 `is_within` 改成恒 True ⇒ 该用例 `DID NOT RAISE BoundaryViolation` 立刻红(4 failed)。
- ↑ 1143 → 1146(**+3 跑 +1 跳**; 2026-09-22 其二: 平台语义守阵补齐 ——
  ① `tests/test_sim_corpus.py` +3: `test_sim_is_within_host_semantics`(B2 逃逸判定在**宿主语义**下
  成立, 用 tmp_path ⇒ win32 与 linux **两边各真跑一次**) / `test_sim_is_within_linux_equivalent`
  (把 `os` 换成 `posixpath`+`sep='/'` ⇒ 本机复现 Linux 语义) / `test_sim_is_within_red_on_fold_without_sep`
  (**红验**: 只把 `_norm` 换成 `ntpath.normcase`、分隔符不动 ⇒ 真子路径被误拒 ⇒ 上一条立刻红,
  实测 1 failed)。钉死的是「sim_qb 的 fs_root 是 `os.makedirs` 出来的**宿主真实目录**,
  save_path 由它拼出 ⇒ 判定必须跟随宿主 FS, **不能统一到 ntpath**」这条结论。
  ② `tests/test_web.py` +1(**仅 Linux 跑**, win32 上 skip): `test_api_fs_dirs_case_sibling_is_outside_whitelist`
  —— 大小写兄弟目录(`/x/Media` vs `/x/media`)必须判为越界; 若 `_fs_real` 做 NTFS 式折叠则
  **越界放行**(fail-open)。⚠ NTFS 上建不出"仅大小写不同"的两个目录 ⇒ 本机(Windows)只能 skip, 由 CI 验。
- ↑ 1142 → 1143(**+1**; 2026-09-22 GitHub CI 红了 `test_fsmock_long_path_prefix_and_case`
  —— `scripts/sim_fsmock.py::_key` 用 `os.path.normcase` 做大小写折叠, 而它在 Linux 是
  **`posixpath.normcase`(恒等函数)** ⇒ 折叠静默失效 ⇒ 把存在的文件报成缺失 ⇒ D4 判据全假。
  该 mock 模拟的是 **NTFS 语义**(语料抓自 Windows 真机) ⇒ 归一必须**固定**, 改显式 `ntpath.normcase`。
  新增防回潮守阵 `test_fsmock_case_folding_does_not_follow_platform`(+1): **运行时**把模块里的
  `os` 换成 `path=posixpath` 再判结果 —— 这一换精确等价于"旧代码跑在 Linux", 于是**本机就能**
  抓住只在 CI 现形的失败。❗刻意**不用文本扫描**: `os.path.normcase` 这串字就写在 `_key` 的
  docstring 里当反例, 扫描会被注释骗过(与冒烟 `_scan_filter_facets` 先剥注释同一个坑)。
  红绿双验: 还原成 `os.path.normcase` ⇒ 本机(Windows)上该守阵**立刻红**, 而既有的
  `test_fsmock_long_path_prefix_and_case` 仍然绿 —— 后者正是"只在 Linux 现形"的原因)。
- ↑ 1142 → 1142(**不变**; 2026-09-21 二次: 种子页筛选器取数面 + 真值覆盖时序修复只**加断言**,
  未新增用例 —— `test_frontend_static_bundle_health` 内新增扫描器 `_scan_filter_facets`
  (筛选器选项必须走 `facetRows`/`_facetOptions` 单点; 旧按组实现 `_memberValueOptions` 复活即红),
  经 **5 种注入违例红验**(含"把调用注释掉"——所以该扫描器先剥 JS 注释再判存在性, 见 `_strip_js_comments`)。
  同批的浏览器冒烟断言见本节末「浏览器冒烟」)。
- ↑ 1138 → 1139(列偏好第二次修复 +1: `tests/test_web.py::test_frontend_save_col_state_skips_widths_for_auto_pages`
  钉死"未手动调过宽的页不得把自适应 px 落盘"; 与 `app.js::loadColState` 的"非手动页不读 px"成对,
  防列宽被**别的窗口**算出的值整段覆盖(issue 26-09-20-1800 第二次修复)。
  该 bug 前后四轮修复都没逮到 —— 单测全绿、冒烟全绿、**只在真机多窗口下现形**, 故必须静态钉; 守阵经**红验**。
  ⚠ 守阵只能判**非注释代码行**是否含 colManual —— 只查字符串存在性会被注释骗过
  (注释里正写着 colManual), 实测第一版守阵就是这么漏掉的(整行注释掉仍 passed)。
  ⚠ 跑全量**别用 `--basetemp` 指到项目内或 `AppData\Local\Temp`**: `tests/sidefx.py` 的
  `is_temp_path` 判定失效 ⇒ 冒出 4~5 条**假失败**(全是"临时目录内删除被判越界"), 与代码无关;
  另 `H:\Temp\pytest-of-11059\pytest-current` 残留符号链接会 PermissionError。
  ⇒ 本项目跑全量统一用 `--basetemp="H:/Temp/<新目录>"`, 实测干净。
- ↑ 1137 → 1138(tracker / tag 脱敏映射 +1: `tests/test_sim_corpus.py` ——
  auto-qb 自有标签字面量 MISSING / zSkipChecked 被伪名化后, 必须能反查回原文才能记进 meta 的
  `sanitize_map.known_tags`。❗踩过的坑: 标签集合里存的是**已脱敏**的伪名, 拿原始字面量去 `in`
  判断**永远为假** ⇒ 映射恒空 ⇒ 回放 config 仍写真字面量 ⇒ 跳检/缺文件行为与真机不一致。)
  ⚠ 该批次还修掉一个**会让头号判据假绿**的坑: 只信"权威"的 tracker→tag 映射会漏掉语料里最大的
  站点(35 个种子) ⇒ 那些种子被"未匹配 tracker 配置"跳过、**连带不参与归组** ⇒ group_exact 0 → 34。
  改成"权威优先 + 统计兜底 + 只输出语料里真出现过的域名"后才回到 0(详见 pitfalls)。
- ↑ 1133 → 1137(语料判据批次 W5 +4: `tests/test_sim_corpus.py` 续 —— 头号判据 `CORPUS.group_exact`
  的比对内核 `group_exact_diff` 及三道红验: **成员串组(组数仍相同)、一组被拆成两组、真值组没被分出**
  —— 只比"组数"会放过串组, 那正是"增量应用出错"的样子)。
  另有 2 条运行期判据落地: `CORPUS.group_exact`(需 --web-port, 走 auto-qb `GET /api/state?view=group`
  取**它自己**分的组, 不在 sim 侧重算 —— 重算会变"自己算的期望 vs 自己算的实际", 判据空转)
  + `CORPUS.maindata_lag_modeled`(issue 26-09-20-2145 的验收凭据)。
  ⚠ 阈值**两套不混用**(计划 §09): `plans/…baseline.json` 里 `corpus.*` 是语料档阈值、裸 id 是合成档;
  `sim_run` 在语料档只查 `corpus.` 前缀、**不回落裸 id**。首次固化时合成档基线另存 `…synthetic.json`。
  实测两套差得很远(corpus.P1.first_round_s 2.91 vs 22.68), 混用必然假红/假绿。
- ↑ 1128 → 1133(语料时间轴回放批次 W4 +5: `tests/test_sim_corpus.py` 续 —— 末帧 closure 必须排除出可回放集合、
  游标推进与窗口合并(后写覆盖 / server_state merge / 新增种子进状态)、fs_delta 按 t_seq 叠到磁盘状态、
  `--latency-mode` 的 recorded 与 const 两条分支)。
  另有 4 条 **CORPUS.*** 运行期判据落地在 `scripts/sim_run.py`(语料档专属, 合成档不出现):
  replay_stream_consumed / replay_timeline_aligned(阈值按「轮询间隔 × 倍速 × 2 裕度」算, 不拍常数)/
  fs_state_match / endpoints_covered —— 端到端 4 条全 PASS。
  ⚠ 该批改 `scripts/` 三个文件 + `tests/` 一个文件, src/ 零改动; 既有 1128 条全部原样通过。
- ↑ 1111 → 1128(语料回放批次 W3 +17: `tests/test_sim_corpus.py` —— FS mock 的拦截/作用域/长路径前缀与大小写/
  未知路径计数/disk_usage 用录制值; **静态守阵 CORPUS.fs_mock_coverage + 红验**(把探测换成 pathlib 必须红);
  窗口合并净额(先增后删 / 先删后加 / server_state merge / tags 按序末事件); piece hash 按内容集合派生
  (同组共享 ⇒ 严格模式判据不恒假); 两层状态模型(**info 先可见 / maindata 后可见 + 无滞后时的红验**);
  <FSROOT> 占位符解析; aborted 语料必须拒绝回放; 站点标签取"最专有"者)。
  ⚠ 该批改 `scripts/` 四个文件 + `src/` **零改动**(归组纯函数那处已在上一批入库), 既有 1111 条全部原样通过。
- ↑ 1098 → 1111(语料抓取批次 +13: `tests/test_qb_capture.py` +12 —— 脱敏等长/保形/保扩展名/
  单射与确定性/短标签碰撞重派生/真实标签集零碰撞/路径三条等价类边界/v1v2 infohash 形状/
  分组守恒绿 + **两道红验**(大小写被归一必须红、多成员组改一个成员路径必须红)/流累积器语义
  (server_state merge、torrents 后写覆盖、*_removed 净额)/抖动与结构字段的判定口径;
  `tests/test_grouping.py` +1 —— `test_group_key_of_is_single_source_of_truth` 钉死
  "归组 key 纯函数 == 真实 mixin 输出"(防内联公式与纯函数分叉)。
  范围: 语料计划 `memory-bank/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html` 的 W1/W2。
  ⚠ 该批**新增一个 scripts/ 文件** (`scripts/qb_capture.py`), 不覆盖 src/ —— 除 §04 那一处纯函数抽取外
  src/ 一行未改, 故既有 1098 条全部原样通过(无退化)。
  ⚠ **Linux 侧未同步重测**(本批只在 Windows 跑), 按本节上方纪律, 下次动基线时两侧一起补。
- ↑ 1094 → 1098(本批 +4: `tests/test_web.py` 新增两道前端静态守阵 —— `test_frontend_member_window_functions_live_in_methods`
  钉死"成员行窗口带参函数必须 methods 不得 computed"(防 Vue 3 getter 当属性调用导致整表白屏);
  `test_frontend_dist_segments_aggregates_per_view` 钉死"状态分布按 viewMode 分支取数"
  (防种子页 / 追剧页次导航统计全空)。两条都因 2026-09-21 一次两连 bug 落地 —— 修法均改两处前端 mixin,
  单测看不见, 必须静态钉)。
  实际: 1094 是当日已写好的 W3 收尾数字; 本批 +2(1096)→1098, 上一批 +2(1094→1096) 是领先
  origin/develop 的两个 commit 已加但 testing.md 未及时更新的测试(本批一并补齐基线)。
  (防种子页 / 追剧页次导航统计全空)。两条都因 2026-09-21 一次两连 bug 落地 —— 修法均改两处前端 mixin,
  单测看不见, 必须静态钉。
  ⚠ **Linux 侧未同步重测**(本批只在 Windows 跑), 按本节上方纪律, 下次动基线时两侧一起补。
- 更早的流水已外迁(2026-09-23, `log` cap 24,000 触发轮转: 切掉最老约 1/3) → [baseline-history-old.md](baseline-history-old.md)
