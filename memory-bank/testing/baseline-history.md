# 测试基线 · 变更流水

> 摘要: 测试基线的**逐次增量流水**(最近在上), 每次增删用例都记一条 —— 用来回答"这个数字是怎么来的"。
> 触发: 基线为什么是这个数, 某条用例何时加的, 覆盖率变化, 历史增量

> 迁移说明(2026-09-22 W3): 本节原在 `testing.md` 顶部的 ```bash 围栏里当注释, 现原样外迁 ——
> **只把 bash 注释标记转成 markdown 列表缩进**(内容逐字未改)。**当前数字**见 [baseline.md](baseline.md)。

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
  `checking` 高风险动作按计划**单独成篇**并与 [../pitfalls/backend/high-risk-ops.md](../pitfalls/backend/high-risk-ops.md) 互指。
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
  迁到 [baseline.md](baseline.md)**, 变更流水原样外迁到本文件; `techContext.md` 的浏览器自动化两条轨道
  迁入 [browser-env.md](browser-env.md)(techContext 6,706 → 3,542 字符)。全量 1169 passed + 1 skipped, sidefx 越界 0)。
: 只动文档与 skill 脚本, 未增删用例 ——
  但 9 条知识库守卫从「目录未建时空转」变成**真跑**(索引 == 生成结果 / 索引↔目录双向一致 / 三行头元数据 /
  cap 策略 / 类名与文件名 / 无孤儿索引 / 存根合法 / pitfalls 条目三字段 / 4 脚本可 import)。
  全量 1169 passed + 1 skipped, sidefx 越界 0)。
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
  范围: 语料计划 `docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html` 的 W1/W2。
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
