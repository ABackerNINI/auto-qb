# 26-09-28-webui-group-columns — 辅种页扩列: 组级聚合 + 明细差异列 + hide 默认隐藏

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28 03:30
**Summary:** 辅种页扩列(2026-09-28 拍板): 分组列默认加 进度(max)/剩余时间(最小有效 eta)/已下载(Σ)/最近活动(max), 可选列(hide 默认收起)加 剩余量(min)/做种时长(平均)/可用性(max)/分享率(Σ上传÷单份大小); 明细列默认加 剩余时间, hide 加 限速上下行/Tracker/Hash/Hash v2/做种(总)/用户(总)/已下载/完成于/最近活动/活跃时间/可用性/见到完整副本; 列模型新增 `hide` 标志(loadColState 播种, 空存储路径必须覆盖); 新守阵 _scan_column_cells_paired; 双皮肤 Playwright 冒烟全绿。
**Topics:** webui-group-columns

## 原始请求

WEBUI 辅种界面添加所有适合的字段: 分组列展示组的共同/汇总信息, 明细列展示成员差异信息。经 5 轮口径对齐拍板:
1. 进度取组内最高(用户点名)。
2. ❗组内成员指向**同一份文件**(组 key 首元即规范化 save_path, 磁盘只占一份)—— 字节量类组级口径必须取"单份"视角: 剩余量取 min(不能 Σ)、分享率分母用单份大小(不能 total_size, N 份稀释 N 倍); 只有逐成员真实发生的网络流量(速度/总上传/已下载)才可求和。
3. **总大小(Σ)保留** —— 它是保种价值口径(N 站点各自计入的保种贡献), 不是磁盘占用。
4. **eta 取最小有效值**: 下载冲突检查(`grouping.py::_check_download_conflicts`)保证同组至多一个成员在下载(多下载/下载中与已完成并存都会被暂停), 它下完其余成员 recheck 即齐。
5. **已下载取 Σ**: 多站切换下载的流量总消耗(recheck 承接的字节不计入 downloaded, 恰为真实网络成本); 边界: 移除成员后其历史流量脱账。
6. 做种时长取**平均**(max 偏最老、min 偏刚补, 都不代表整组); 可用性取**最高**(内容获取由最好的 swarm 决定)。
7. 明细表加 tracker url / hash / hashv2(hash 已有, 补 tracker/infohash_v2); 表头名称与种子页同名列对齐; 可选字段默认隐藏; 限速上下行/tracker/hash/hashv2 也默认隐藏。
8. 除 ✗ 不建议的字段全部加上(含明细 seen_complete / num_complete / num_incomplete / time_active / completion_on / last_activity / availability)。

## 思考过程与决策

- **聚合口径单点**: 组级聚合一律后端 `_build_group_view` 算好("派生值后端算"约定), 前端只渲染; 成员字段先补进 `_member_view`(组视图 members / singles / 追剧集成员三方共用投影), `_seed_view` 契约不动。
- **哨兵语义**: eta 有效值 = `0 < eta < 8640000`(与 format.js::fmtEta 口径一致); 时间点 -1/0 = 从未(fmtTs 空白); 全组无效时 eta/last_activity 回 0、availability 回 None —— 前端空白而非假数值。
- **置脏安全**: 秒级递增字段(eta/time_active/last_activity/seeding_time)经 `view_field_value` 分钟量化; 组级 seeding_time 对已量化成员值求平均后再取整, 组级值不以秒粒度抖动。全部新字段已在 `_VIEW_FIELDS`(view.py), 无需扩置脏字段集。
- **hide 标志设计**: 列定义加 `hide: true`; `loadColState` 在**读完存储后**对"该页 hidden/order/w 全缺"的页注入默认隐藏集(内存意图态, 随首次 persistPage 落盘)。有任何已存偏好(哪怕空 hidden)不播 —— 防"刻意全开"被反复覆盖(列偏好被重置的同形陷阱, pitfalls columns-persist)。
- **冒烟抓到真 bug**: 首版把播种块放在 loadColState 的 per-page 循环内, 而函数对**空存储提前 return** ⇒ 全新浏览器 hide 全部失灵(所有可选列默认可见)。修法: 播种移到函数尾部, 空存储/坏 JSON 路径同样走完整流程。
- **模板成对**: 明细单元格分支在 groups.html(辅种展开)与 shows.html(追剧集成员)各一份, 共用同一列模型 —— 新列必须两处成对加分支; 为此新增静态守阵机械钉住(见下)。
- **CSS 零新增**: 组级进度条复用 `.m-progress`(组行配色规则已存在)、tracker 单元格复用 `.g-save-path`(member-row 上下文已覆盖)、数值格复用 `.g-stat/.m-stat` —— 对齐仍由 colAlignCss 按列模型生成。
- **排序/搜索不受扰**: 新列 sortable 走既有 sort.js 数值/字符串比较; search_torrents 的 `_view` 字段集未动(搜索命中行不消费新列)。

## 实现计划

1. 后端 `webui/views.py`: 模块级 `_min_valid_eta`/`_max_valid_ts` 哨兵感知聚合助手; `_member_view` 补 12 个透传字段; `_build_group_view` 补 8 个组级聚合字段(progress/eta/downloaded/last_activity/amount_left/ratio/seeding_time/availability)。
2. 前端 `app.js`: GROUP_COLUMNS +4 默认列 +4 hide 列, DETAIL_COLUMNS +1 默认列(eta) +12 hide 列(hash 从默认可见转 hide); 列定义新增 `hide` 标志; `loadColState` 重构(早退 return 消除 + 尾部播种)。
3. 模板 `groups.html`/`shows.html`: 分组行 4+4 个新分支、明细行 13 个新分支(两份成对)。
4. 测试 `tests/test_web.py`: `test_build_group_view_group_aggregates`(双组: 有效聚合 + 全无效回 0/None)、`test_member_view_extended_fields`(量化/哨兵/透传); 静态守阵 `_scan_column_cells_paired`(列 key ↔ 模板分支配对 + hide 接线)挂进 `_scan_frontend_assets` 第 14 项。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 组级聚合口径定案(5 轮对齐: 单份文件/保种价值/单下载者/平均/最高) | ✅ |
| 后端 _member_view 透传 + _build_group_view 聚合 + 哨兵助手 | ✅ |
| 前端列模型加列 + hide 标志 + loadColState 播种(含空存储路径修复) | ✅ |
| groups.html/shows.html 单元格分支成对落地 | ✅ |
| 测试: 聚合用例 ×2 + 列单元格配对守阵 + 测试计划 docstring 同步 | ✅ |
| 双皮肤 Playwright 冒烟(atlas/prism: 新列头/默认隐藏/勾选开启/意图落盘/零 JS 错误) | ✅ |
| test.full 全绿 + 基线切片 | ✅ |

## 进度日志

- 2026-09-28 00:xx-03:30: 5 轮分析口径对齐(每轮修正上一轮聚合口径错误) → 用户确认"开始实施"。实施全程: 后端聚合 → 前端列模型 → 模板 → 测试 → 冒烟。
- 2026-09-28 03:xx: **冒烟发现 hide 播种被空存储提前 return 绕过**(全新浏览器所有可选列默认可见)—— 重构 loadColState 把播种移到函数尾部; 复跑冒烟全绿。已按新坑回写 pitfalls/web-ui/columns-persist.md。
- 2026-09-28 03:30: test.full 1818 passed / 3 skipped(TOTAL 91%, views.py 98%), 基线切片 26-09-28-0330; dev.harness 8099/8123 被一周旧孤儿进程占住 → `--port 8921` 绕开(未杀进程, 非本 clone 归属不明)。
- 遗留(范围外): `kb.check` 报两条 2026-09-27 旧基线文件名不合 `YY-MM-DD-HHMM-<slug>` 约定(console-skin / ui-switch-dropdown)—— 既有问题, 未夹带修复, 待拍板是否入池。
