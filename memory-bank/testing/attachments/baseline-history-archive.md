# 测试基线 · 变更流水 (归档: 较老一段)

> 摘要: `baseline-history.md` 触顶后外迁的**较老一段**流水(append-only, 内容逐字未改); 新条目仍追加到主文件。
> 触发: 基线历史增量, 这个数字是怎么来的, 老流水归档

> 主文件: [../baseline-history.md](../baseline-history.md)(只保留最近 ≤ 16,000 字符)
> 本文件 = **较新那一段**归档; 更老的见 [baseline-history-old.md](baseline-history-old.md)。
> ❗链接已在切切时重写过一遍(`attachments/` 前缀已去掉) —— 否则在当前目录就是坏链。

- ↑ 收集数 **1232 → 1233**(+1; 2026-09-24 **WEB UI 添加种子回执与 optional 选项**):
  用户报"添加种子显示失败 + 桌面弹 WARNING 但实际添加成功, 且「添加后开始」不生效"。三条根因:
  ① 回执只认 `"Ok." in str(result)`, 而 qB 5.2+(Web API 2.14.0)的 `/torrents/add` 已改回 JSON 元数据
  (`TorrentsAddedMetadata`, dict 子类)⇒ 判定恒假; ② 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到
  **会话级**默认 `isAddTorrentStopped()`, 勾了也按停止添加; 另 qbittorrent-api 的
  `is_paused or is_stopped` 会把 `is_paused=False` 折成 `None`(实测请求体空串)⇒ 只能用 `is_stopped=`;
  ③ 成功路径记 WARNING, 而 NotifyHandler 挂在 `auto_qb` logger 上 ⇒ 每次成功都推桌面弹窗。
  同轮按用户"修复同类隐患"把 `use_auto_torrent_management` 一并改成恒显式(它同为 `std::optional`,
  未勾 + 未填保存路径时会吃 qB 全局管理模式); 判据升级为"看 `addtorrentparams.h` 的字段类型 ——
  optional 的必须显式, 普通 bool 省略安全"。
  修法: 新增 `webui/commands.py::_add_outcome` 双形态判定 + 恒显式下发 `is_stopped` /
  `use_auto_torrent_management` + 成功 INFO / 未受理才 WARNING。替身同步补 `is_stopped` 与
  `is_stopped_raw`(保真度)。用例名 `test_add_torrent_receipt_and_optional_flags`(四条断言全红验)。
  两条新坑写进 [pitfalls/backend/qb-api.md](../../pitfalls/backend/qb-api.md) 与
  [pitfalls/testing/stubs-sim.md](../../pitfalls/testing/stubs-sim.md)(含 `make_manager` 清 root handlers
  ⇒ 用例体内建 manager 时 caplog 恒空)。⚠ 本轮开工时与主线齐平, 提交前发现主线已前进 2 个提交
  (`9d7a3eb` / `2e2e2b5`)⇒ 按"移出改动 → `merge --ff-only` → 施回改动"同步(重叠仅 3 个文件:
  两个基线文档 + 生成物 `tasks/_index.md`), 故本条收集数在**合流后**的 1232 基础上 +1。
  全量 **1232 passed + 1 skipped** / TOTAL 91%(7782 语句 / 622 未覆盖 / 2648 分支) / sidefx 2067 / 越界 0。
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

- ↑ 收集数 **1225 → 1232**(+7; 2026-09-24 **commands 引擎子进程编码**):
  用户报「跑 `commands run kb.index` 输出乱码」。取证: 引擎自己的 stdout 是 UTF-8(`uv run` 给的),
  但它 `shell=True` 起的**孙进程**(`kb.index` 的第二条包脚本)的 stdout 被管道接住时按**本地码页 cp936**
  输出 ⇒ 引擎按 UTF-8 硬解 ⇒ 「已生成 16 个索引」变 `������ 16 ������`。拓原始字节确认是 GBK
  (`b'\xd2\xd1\xc9\xfa\xb3\xc9 16 \xb8\xf6\xcb\xf7\xd2\xfd'`), **退出码照旧 0** —— 静默的坏, 只影响人读。
  修法(引擎单点, 不动任何包脚本): ① 子进程环境注入 `PYTHONIOENCODING=utf-8`(只影响 stdio, 不像
  `PYTHONUTF8=1` 连 `open()` 默认编码一起改; 放在 pack env 之前, 包仍可覆盖) ② `_shell` 改**按字节收** +
  `_decode` 兜底解(UTF-8 → 本地码页 → `errors="replace"`) —— 非 Python 子进程仍可能给 GBK, 这一层兜住。
  新增 7 条守阵(全在 `tests/test_commands_engine.py`), **红验**用 A/B 对照(修前解出 `������ 16 ������`,
  守阵对差异敏感)。❗测试里**不真起子进程** —— `tests/sidefx.py` 的 POPEN 记账会判越界,
  所以用假 `subprocess.run` 直接给字节。坑与判据写进
  [pitfalls/ops/console-encoding.md](../../pitfalls/ops/console-encoding.md), 引擎约定写进
  [`.agents/skills/commands/references/howto-add-command.md`](../../../.agents/skills/commands/references/howto-add-command.md)。
  全量 **1231 passed + 1 skipped** / TOTAL 91%(7768 语句 / 623 未覆盖) / sidefx 台账 2049 / 越界 0。
- ↑ 收集数 **1216 → 1225**(+9; 2026-09-24 **commands W7: wrapper 入口**):
  用户要求「真正实现 `commands run <task.id>`」。先实测三个 shell 对 cwd 的搜索规则(Git Bash 与 PowerShell
  **都不搜**, 只有 cmd.exe 搜)⇒ 只落仓库根达不到目标, 与用户确认后落 **cwd + PATH 目录**两处: 新增生成器
  `install_wrapper.py`(幂等 / 只认自己的标记行 / 生成物 gitignore / 装完自证), 解释器优先 `uv run python`
  (包脚本以引擎的 `sys.executable` 执行, 这决定它们跑在系统 python 还是项目 venv)。
  实测撞到 6 个坑, 全部写进 [pitfalls/backend/platform-fs.md](../../pitfalls/backend/platform-fs.md):
  批处理 `rem` 含引号/括号/反引号 → 静默退出 2 且无输出 · `.cmd` 必须 CRLF · 消息必须 ASCII ·
  CreateProcess 不认 shebang(WinError 193) · Git Bash 的 PATH 条目是 MSYS 形态(直接比永远不相等) ·
  `os.access(W_OK)` 在 Windows 目录上给假否定。同轮把「低噪音包」八条判据写进 `howto-add-command.md`。
  新增 9 条守阵(含端到端真跑 wrapper), 全量 **1224 passed + 1 skipped** / TOTAL 91%(7768 语句 / 623 未覆盖)
  / sidefx 2051 / 越界 0(sidefx 放行面收窄到「临时目录里的 `commands` / `commands.cmd`」)。
- ↑ 收集数 **1208 → 1216**(+8; 2026-09-24 **commands 引擎的会话噪音治理**):
  用户走查上一轮提交流程后指出"噪音多、没达到设计初衷"。逐条取证后改: 引擎 `run` 的摘要从
  "只取末 3 行"改成**末几行结论 + 异常行**(只取末行会让检查表里 "2 项 WARN" 的**内容**消失,
  实测逼出一次预检重跑 21s×2)、task id 认包路径限定写法(`包/子包.<task>`)、闸门 PASS 行从
  ≈1.5 KB 命令全文收成一行、开工自检给出**可执行的同步配方**(含文件重叠判定)、
  包/引擎的 47 条脚本测试首次挂上闸门。新增 `tests/test_commands_engine.py` **8 条**(均已在还原版上红验);
  包内测试 34 → **47 条**(+13: `sync_recipe` 判定矩阵 / `summarize_gates` / `_short`)。
  全量 **1215 passed + 1 skipped** / TOTAL 91%(7768 语句 / 623 未覆盖 / 2646 分支) / sidefx 2036 / 越界 0。
  细节见 [pitfalls/kb/scripts.md](../../pitfalls/kb/scripts.md)(摘要要按异常行挑)与
  [tasks/26-09-23-commands-unified-surface.md](../../tasks/26-09-23-commands-unified-surface.md) 的 W6。
- ↑ 收集数 **1203 → 1208**(+5; 2026-09-24 **WEB 事件循环断连噪音降级**):
  用户报障 `ERROR - Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)`
  (`ConnectionResetError [WinError 10054]`) —— 判定为**网络波动**(对端 RST 后 asyncio 仍调
  `sock.shutdown`), 非本项目 bug。修法: `webui/server/lifecycle.py` 新增
  `_web_loop_exception_handler`(波动型降级为一行 INFO + 60s 窗口节流, 其余异常照旧交给
  asyncio 默认处理器) + `_QuietLoopConfig.get_loop_factory()` 把处理器挂到服务循环上。
  新增 5 条守阵(降级 / 节流 / 真 bug 不吞 / 判定矩阵 / 处理器装载), **均已在还原版上红验**;
  真机复现: 原生 `uvicorn.Config` 打 ERROR + traceback, 换 `_QuietLoopConfig` 后同一异常只剩一行 INFO。
  `lifecycle.py` 覆盖率 **96%**; 全量 **1207 passed + 1 skipped** / TOTAL 91%
  (7768 语句 / 623 未覆盖 / 2646 分支) / sidefx 2034 条 / 越界 0。
  判别法与处置见 [pitfalls/backend/platform-fs.md](../../pitfalls/backend/platform-fs.md)。
- ↑ 收集数 **1202 → 1203**(+1; 2026-09-24 **浏览器站点级"关闭时清除站点数据"取证 + 空存储提示加固**):
  新增 `test_frontend_cols_empty_hint_names_browser_clear_cause` —— 钉住"空存储提示"必须同时点名
  ①origin 隔离(换地址/端口) ②浏览器站点级「关闭窗口时清除 Cookie 和站点数据」(Chromium cookie
  例外 `setting=4` = SESSION_ONLY, 会连 localStorage 一起清), 给出自查路径, 并要求用 sessionStorage
  做"同一次会话只弹一次"的兜底(清站点数据的环境下 localStorage 里的去重标记也会一起没)。
  全量 **1202 passed + 1 skipped** / TOTAL 91%(7729 语句 / 623 未覆盖 / 2636 分支; 串行实测) / 越界 0。
  取证原文与机理见 [pitfalls/web-ui/columns-persist.md](../../pitfalls/web-ui/columns-persist.md)。
- ↑ 收集数**不变**(**1192**; 2026-09-23 **全量测试耗时归因与优化**, 见 [tasks/26-09-23-test-suite-perf.md](../../tasks/26-09-23-test-suite-perf.md)):
  **未增删用例**, 只做三处实测优化 + 补一份坑档 —— ①`tests/sidefx.py` 的 `report()` 把 `violations`
  提到循环外(原写法每种 kind 重算一次 = 8 次 × 约 1600 条路径 × `os.path.realpath`)⇒ 收尾 teardown
  **4.71~8.97s → 1.04~1.20s**; ②`tests/test_web.py` 的前端 JS 语法守阵由"20 次 `node --check` 进程"
  改为**单进程批量**(`node -e` + `Module.wrap`; 裸 `vm.Script` 会把顶层 `return` 判错, 已对齐为
  与 `--check` **8/8 一致**)⇒ 7.375s → 0.378s, `test_frontend_static_bundle_health` 4.06s → 0.27s;
  ③修三处临时目录泄漏(`test_web` / `test_expr_eval` / **探针新查出** `test_trigger_events`)⇒
  探针实测"每次全量建 **577** 个临时目录, 收尾残留 **2 → 1**", 剩下的 1 个是
  `test_checking.py:155` 的模块级持有者, 进程退出即回收。全量 1191 passed + 1 skipped / TOTAL 91% / 越界 0。
  ⚠ **耗时数字改口径**: 旧记录写单值(139.07s), 本轮同一条命令多次实测为
  **62~114s**(中位约 75s, 极差 1.8 倍; 逐次枚举见 [baseline.md](../baseline.md))
  ⇒ 基线耗时**改为区间**, 理由与成因见 [baseline.md](../baseline.md) 与
  [pitfalls/testing/perf-measurement.md](../../pitfalls/testing/perf-measurement.md)。
  同日续: 用户把**三盘 Temp 目录**加入文件安全白名单后复测, **写 20.19 → 0.58ms(34×)**、
  串行中位 **75 → 61s**(54~81s); 但 `os.remove` 14.6ms / `os.rmdir` 52.7ms **仍被拦**
  (一次全量 577 个临时目录 ⇒ 删除类 ≈ 26s, 占 44%)。并行 `-n 4` 中位 ~31s 但尾部最坏 209.77s。
  同日再续: 用户继续调整设置后**删除也被治好** —— 四类操作全部 <1ms
  (`mkdir` 0.13 / 写 0.21 / `remove` 0.16 / `rmdir` 0.14ms)⇒ 串行 **19.37~20.16s**(中位 ~19.6s),
  并行 `-n 4` **5.00 / 5.06s**(波动消失)⇒ 相较最初的 75s 量级共 **3.8×**(并行 15×)。
  ⚠ 这 3.8× 全部来自**环境**, 不是代码优化; 并行条目已从"不建议"翻转为"建议 `-n 4`" ——
  见 [pitfalls/testing/parallel-run.md](../../pitfalls/testing/parallel-run.md)。
  另: 原候选"C 把 basetemp 钉进 TMPDIR 以省掉会话起始清理"实测**被推翻**(只把删除从收尾挪到起始 ——
  `_pytest/tmpdir.py` 对显式给定且已存在的 basetemp 会先 `rm_rf`, RUN H setup 段 19.85s), **未实施**。
- ↑ 收集数不变(**1192**; 2026-09-23 **tasks 索引渲染口径改造**): 未增删用例, 只消红 ——
  `gen_tasks_index.SUMMARY_MAX = 80`(摘要截断成一行) 让 `tasks/_index.md` **12,299 → 5,710**,
  那条既有红 `test_kb_files_respect_caps` 随之消失, 全量 **1191 passed + 1 skipped** / 139.07s / TOTAL 91%。
  为什么不按"轮转老档案"化解(实测数据): 可动档案仅 16 个 `Completed`(另 16 个 In Progress 是活的),
  其中 **15 个有外部引用** —— 搬走会让 `check_doc_links.py` 变红; 且 33 条平均 350 字符/行, 全搬也只够一次。
  病根是「索引把 `Summary` 全文打进一行」, 见 [pitfalls/kb/cap-counting.md](../../pitfalls/kb/cap-counting.md) 第三节。
- ↑ 1190 → 1191(**+1**; 2026-09-23 **activeContext 切片化**(plan 26-09-22-2350 v1.1):
  新增守阵 `test_kb_active_context_slices_are_valid`(切片命名定宽前缀 / 三行头 / 每个 ≤6,000 / 总数 ≤40),
  并把 `test_kb_active_context_within_cap` 改判**存根合法性**(旧 12 KB「易变层硬顶」在切片化后失去对象)、
  `test_active_context_has_no_rolled_up_session_log` **语义重定义**(切片本身就是流水账, 原判据 `^- 2026-`
  在切片化后恒绿 = 等于没守; 改为只管 `activeContext.md` 本体 + 断言切片目录存在)。
  ⚠ 该轮全量实测 1189 passed + 1 skipped + 1 failed —— 那条 failed 是**既有红**
  (`test_kb_files_respect_caps`: `tasks/_index.md` 超 index-auto cap, 与本轮改动无关);
  **同日晚已由索引渲染截断解决, 见上一条**。TOTAL 91%, 143.77s。Linux 侧未重测。
- ↑ 1186 → 1188(**+2**; 2026-09-22 **web.py→web/ 包拆分 · issue 26-09-21-1408**(plan 26-09-22-1857):
  新增守阵 `test_web_route_manifest_frozen`(60 条 (method,path) 金清单集合比对; ❗本仓 FastAPI 的
  `include_router` 走 `_IncludedRouter` 懒解析, 清点须下钻 `original_router.routes` —— 首版因此假红)
  + `test_create_app_is_thin_assembly`(create_app ≤150 行且无内联 `@app.*`, 红=拆分前 926 行双红)。
  既有用例零改动(1 处管线性: open_path patch 目标 → `auto_qb.web.common.open_path`); 冒烟双 UI
  ok/error 两模式 70 项 0 失败。全量 1188 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1188 → 1190 collected(**净 +2 用例**; 2026-09-22 **两案合流(2d4720b) + web 拆分合入**两次 merge 先后入库:
  config 取值范围收紧(issue 26-09-22-1937, 本侧 +1 守阵)
  × 状态周期落盘 + 热重载修复(对侧), core.py 冲突块手工合流(双方意图全保留); 
  合并树实测 deselect throttle 全量 1188 passed + 1 skipped + 1 deselected(throttle 文件级/全量跑因
  sleep 精度容差偶发假红, 已入池 26-09-22-2052); TOTAL 91% 7600 语句)
- ↑ 1176 → 1177(**+1**; 2026-09-22 **config 取值范围收紧实施**(issue 26-09-22-1937, 合流前单树实测):
  新增 `test_validate_value_ranges`(聚合验证 interval/main_tick/sync_interval 上下界、max_tasks_per_tick 上界、
  log.max_bytes 轮转区间、required_share_ratio 拦 nan/inf/负数、hr.condition 百分比与下载量边界、
  notify 上界、规则 interval 正时间); test_parse_hr_condition 补 4 条边界断言。
  助手层: 新增 `_try_number`(isfinite 拦 nan/inf)、`_try_time` 增 min_s/max_s、`_try` 返回解析值。
  全量 1177 passed + 1 skipped, sidefx 越界 0。首次全量曾现 test_run_loop_throttles_without_stop_event
  假失败(时序抖动: 单跑与复跑均绿, 与本次改动无关))
- ↑ 1185 → 1186(**+1**; 2026-09-22 issue 26-09-21-1347 **热重载 L2 state 回滚修复**:
  新增守阵 `test_apply_new_config_l2_preserves_runtime_state`(L2 热重载不得重读磁盘 state
  回滚运行期内存态; 修前红验必红 —— 实测 mgr.state 被换成磁盘旧版 `{'stale_marker': True}` →
  1 failed; 删 qbmanager.py:503 一行后转绿)。合流前单树实测: 语句 7542→7541(删 1 条已覆盖语句),
  miss ±1 的逐次抖动判为 server 线程路径的度量噪声; 覆盖率口径以本次实测为准。
  全量 1186 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1176 → 1185(**+9**; 2026-09-22 **状态周期落盘 · issue 26-09-21-1347**:
  新键 `state_save_interval`(默认 120s / 配置端下限 30s 防误配置写放大 / 0=关闭) +
  主循环周期落盘钩子 + `skip_check_day`/`recheck_fails` 写点即时落盘。守阵 9 条:
  周期触发/关闭逃生口/脏退出验收阵与 interval=0 对照/跳检标记即时落盘/冷却计数即时落盘/
  配置校验/L0 分级/主循环接线。红验: 运行期把 `_maybe_flush_state` 与 `save_state` 打回 no-op,
  3 条行为守阵全红(KeyError/FileNotFoundError = 状态从未上盘); 还原全绿。
  全量 1185 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1175 → 1176(**+1**; 2026-09-22 同任务 **W8 收尾 · 重写 `memory-bank.instructions.md`**:
  新增 `test_memory_bank_instructions_match_current_structure`。
  为什么值得单独钉: 该文件 `applyTo: memory-bank/**`, **只在编辑 memory-bank 时注入** ——
  不重写的话, 目录化重构后的新结构在改库那一刻**根本不在上下文里**, 于是又会按旧的 8 文件结构去写。
  旧版(12,073 字符)还在教「read ALL memory bank files at the start of every task」——
  那正是本库涨到 50 万字符、「必读」退化成「不读」的直接原因。重写后 **4,830 字符**,
  改为「先索引、后 grep、禁止整读」+ 当前目录树 + 三行头 + cap 分级表 + 档案五必备章节(标注按行首标题比)。
  另把 `.github/` 纳入 `check_doc_links.py` 的扫描面(规则载体也有链接, 之前扫不到)。
  全量 1176 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1174 → 1175(**+1**; 2026-09-22 同任务 **W8 机检化 + 回归演练**:
  新增 `test_doc_links_are_not_broken`(全库相对链接存在性, 检查器 `scripts/check_doc_links.py`,
  **进程内 import**)。⚠ 它首跑就抓出 **73 处坏链**, 全是目录化搬家导致的**相对深度错位**
  (文件进了子目录、链接还按原深度写) —— 这正是"改名/搬家后的坏链不会让任何测试失败"那条坑,
  记了很久、一直只靠人工扫, 本波把它变成判据。修完 **192 个文件 0 处坏链**。
  全量 1175 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1173 → 1174(**+1**; 2026-09-22 同任务 **W7 `tasks/` 档案消肿** —— 与远端合流后实测):
  ⚠ 本波提交时远端已领先 6 个提交(另一个 clone 的 tracker URL 脱敏 + 两次基线更新), 推送被拒(non-fast-forward)。
  **按纪律没跑 rebase**(本 shell 里必炸), 走 `format-patch` → `reset --hard` → `apply --3way` 重放;
  唯一冲突是 `baseline.md`(远端 1173 vs 本地 1171), 取远端为底, **在最终树上重跑全量**得 1174。
  ⇒ 教训: **跨 clone 的基线数字必须以"最终树实测"为准**, 两边各自的 +N 不能直接相加(远端那 1173 已含它自己的 +2)。
- ↑ 1170 → 1171(**+1**; 2026-09-22 同任务 **W7 `tasks/` 档案消肿**(本 clone 侧):
  新增 `test_kb_task_archives_within_cap` —— 本波把 `task` 角色纳入 `check_kb_structure` 默认角色集
  ⇒ **`check_caps` 的全部角色至此都被默认检查**(W1 故意留在门外的 `volatile` 在 W4 纳入, `task` 在本波纳入),
  这是「守卫按波次激活」这条设计的收口。
  实测: 最大档案 26,871 → **21,881 字符**(cap 24,000); 另把 `26-09-15-webui-qb-replacement.md` 的
  9,413 字符纪要段(超 8,000 子上限)外迁。全量 1171 passed + 1 skipped, sidefx 越界 0)。
 + `config-reference/` + `rule-system/` 目录化**:
  只动文档, 未增删用例。三文件(15,283 / 11,779 / 15,964 字符)→ **4 + 2 + 3 个主题文件 + 存根**;
  `checking` 高风险动作按计划**单独成篇**并与 [../pitfalls/backend/high-risk-ops.md](../../pitfalls/backend/high-risk-ops.md) 互指。
  全量 1170 passed + 1 skipped, sidefx 越界 0)。
 + `modules/` 目录化**:
  只动文档, 未增删用例。`systemPatterns.md`(31,678 字符)→ **8 个主题文件**, `modules.md`(30,324 字符)→ **7 个**,
  两处源文件各留 ≤1 KB 存根。⚠ 顺带**纠正一处归属错误**: 原先「WEB UI 线程模型 / 前端渲染与响应性 /
  图形化配置编辑」三节(合计约 21 KB)挂在「任务队列」名下, 它们属于 **WEB UI 运行时**, 不属于队列。
  全量 1170 passed + 1 skipped, sidefx 越界 0)。
 + `progress/` 拆分**:
  `test_kb_active_context_within_cap` 是 W1 就写好但**按波次未启用**的那条 —— 本波把 `activeContext.md`
  压到 12 KB 硬顶之下(实测 **4,783** 字符), 才把它纳入 `check_kb_structure` 的默认角色集(`volatile`)。
  ⇒ **守阵按波次"激活"**是这套重构的一条设计: 检查器先写全, 目录/内容没到位时空转通过, 一落地就生效。
  全量 1170 passed + 1 skipped, sidefx 越界 0)。
: 只动文档与 skill 脚本, 未增删用例 ——
  `testing.md`(6,706 字符 / 489 行)拆成 **9 个主题文件 + 存根**; **基线数字的单点从 `testing.md` 顶部
  迁到 [baseline.md](../baseline.md)**, 变更流水原样外迁到本文件; `techContext.md` 的浏览器自动化两条轨道
  迁入 [browser-env.md](../browser-env.md)(techContext 6,706 → 3,542 字符)。全量 1169 passed + 1 skipped, sidefx 越界 0)。
: 只动文档与 skill 脚本, 未增删用例 ——
  但 9 条知识库守卫从「目录未建时空转」变成**真跑**(索引 == 生成结果 / 索引↔目录双向一致 / 三行头元数据 /
  cap 策略 / 类名与文件名 / 无孤儿索引 / 存根合法 / pitfalls 条目三字段 / 4 脚本可 import)。
  全量 1169 passed + 1 skipped, sidefx 越界 0)。

- 更早的流水已外迁(2026-09-23, `log` cap 24,000 触发轮转: 切掉最老约 1/3) → [baseline-history-old.md](baseline-history-old.md)
