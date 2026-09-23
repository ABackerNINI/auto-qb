# 26-09-21-webui-filter-data-and-color-flicker — 种子页筛选器无数据 + 辅种组暂停后状态色闪烁

**Status:** Done
**Started:** 2026-09-21
**Updated:** 2026-09-21
**Owner:** 主线 (auto-qb-clone2)
**Summary:** 用户报两个 WEB UI 缺陷。**① 种子页筛选器无数据**: 筛选弹层的选项(标签/分类/站点/路径)一律遍历 `groups` 计算, 而种子页按视图分片**不回 `groups`**(`VIEW_ARRAYS["torrent"] = ("torrents",)`) ⇒ 四个弹层恒空、只剩"暂无数据"(H&R 是固定两档, 表现为 0/0 —— 更隐蔽); 与 issue 26-09-20-1646(状态栏速度)、BUG-8(追剧页成员索引)**同一类成因的第三次**, 故改法用"取数面单点"(`facetRows` + `_facetOptions`)并按视图定计数口径(组视图=组数, 种子页=种子数)。**② 辅种组暂停整组后颜色 灰→绿→灰**: 真值走 `torrents/info` **直查**, 比我们自己的 `/sync/maindata` **快照**新 ≤ `sync_interval`(1.5s); `onTruthEvent` 一到就 `delete pendingOps[h]`(撤掉值覆盖), 这 1.5s 内任何一次**视图发布**都会带着"命令前"的 kind 覆盖行对象 ⇒ 行被打回命令前的做种绿, 快照追上再变灰。修法 = 真值事件**只改覆盖的值(patch/prev)、不结束覆盖**, 收尾判据保持"服务端快照同意"(`_optimisticSettled`)。单测 **1142 passed**(基线不变, 只加守阵断言); 冒烟 ok **68 项 / 2 失败**(两条均为**既有**失败, 见下)、error **68 项 / 0 失败**、hang **8 项 / 0 失败**; 新增断言与静态守阵**均经红验**。
**Topics:** webui-filter-data-and-color-flicker

## 原始请求

> 修复BUG:
> * WEBUI
>     * 种子页筛选器无数据
>     * 辅种组暂定整组后颜色变灰,变绿,再变灰

## 思考过程与决策

- **决策 1(两条都先复现, 不靠静态阅读)**: 起 `scripts/ui_harness.py`(真 `create_app` + 合成种子) + Playwright 脚本(`.workbuddy-ai/tmp/` 下的一次性脚本, 未入库)。① 种子页 `groups=0` / `tagOptions=0 条` / 弹层 `暂无数据`, 且**先加载过辅种页再切过来时不是 0**(冻结的组数)—— 与 issue 26-09-20-1646 的"冻结旧值"形态完全同族。② 组行暂停用"逐步喂时序"的方式复现: 直调 `applyOptimistic → resolveOptimistic → onTruthEvent`, 再用 `page.route` 注入一次**陈旧快照**(成员 kind 改回命令前 + rid 前进)喂给 `refresh()` —— 行立刻从 `s-paused` 打回 `s-seeding`, **当场复现用户描述的"变绿"**。
- **决策 2(筛选器不把 `groups` 加回种子页)**: 与状态栏速度同一取舍 —— 加回去就会废掉 P1-1 的按视图回传(种子页响应体最大), 且现有守阵 `test_api_state_view_scoped_payload` 明确断言过种子页不带 `groups`。故改前端: 新增**取数面单点** `facetRows`(种子页=`torrents`, 其余=`decoratedGroups`), 四个选项 computed 与 `hrOptions` 一律走它。
- **决策 3(计数口径按视图定, 并把旧口径收进单点)**: 组视图的语义是"含该值的**组**数", 种子页是"含该值的**种子**数" —— 与各自页面真正在筛的行一致。旧实现有两份遍历(`_memberValueOptions` 按组 + `pathOptions` 自己一份), 正是"两处口径各写一遍"的老毛病, 一并收进 `_facetOptions(kind)`, 并把 `_memberValueOptions` 作为**反向守阵**钉住"不许复活"。
- **决策 4(真值事件不再"到此收工")**: D2 把一次命令拆成两个时刻(回执=结束压暗 / 真值=结束值覆盖), 但**真值的来源(直查)比它的落地处(同步快照)新** —— 在真值事件里删掉覆盖, 等于把"覆盖"这个补丁的寿命交给了一个比快照快的数据源。改法: 真值事件**只改 `op.patch`/`op.prev` 的值**(patch=已落地的真值 ⇒ resume 的"落地态 6 种 vs 预测 2 种"也顺带收敛, 不再依赖"预测 == 真值"的严格相等), 覆盖继续挂到 `_optimisticSettled`(快照同意)或 8s 兜底。`prev` 也一起改成"最后已知真值": 兜底回滚要回这里, 回命令前的旧值等于把已暂停的种子显示成做种中。
- **决策 5(守阵分两层, 且都必须红验)**: ①浏览器冒烟新增两条断言(种子页筛选器计数=种子数 / 真值事件后不被陈旧快照打回), **红验**把 `commands.js` 的修复临时撤掉重跑 ⇒ 断言按预期变红(`陈旧快照 seeding`、`覆盖保持=0 条`), 断言不是摆设; ②pytest 侧加静态守阵 `_scan_filter_facets`(选项必须走单点、旧实现不得复活), 用 5 种注入违例(含"把调用注释掉")红验。
- **决策 6(既有失败不顺手改)**: ok 模式剩 2 条失败(`P0-3 乐观态及时落回真值(80~1000ms)`, 双 UI 各一), 经"把修复撤掉重跑"证实**与本次改动无关**(撤与不撤失败完全相同, 且 testing.md 已记过同一现象)。本次给出**定论**: 该下界是 D2 之前的语义(那时"撤下"要等真值 ⇒ ≥120ms), D2 之后**压暗由回执结束**(实测 17~20ms, 设计使然), "等真值"那一段现在由**值覆盖(pendingOps)**承担 ⇒ 断言量错了对象。**按范围守恒未改**(改闸门阈值属计划外), 结论与建议写入 testing.md 待定夺。

## 实现计划

| ID | 改动 | 文件 | 状态 |
|---|---|---|---|
| F1 | 新增 `facetRows`(取数面单点) + `_facetPick`/`_facetOptions`; 标签/分类/站点/路径四个选项 computed 改走单点 | `src/auto_qb/web_ui/static/shared/filters.js` | ✅ 完成 |
| F2 | `hrOptions` 改走 `facetRows`, 组/种子两种行形态分别用 `_hrBucket` / `_hrBucketMember` | `src/auto_qb/web_ui/static/shared/hr.js` | ✅ 完成 |
| F3 | `onTruthEvent`: 真值只改 patch/prev + 重置兜底计时, **不再 `delete pendingOps[h]`** | `src/auto_qb/web_ui/static/shared/commands.js` | ✅ 完成 |
| F4 | 冒烟新增两条断言(筛选器有数据且计数=种子数 / 真值事件后不被陈旧快照打回) | `scripts/ui_smoke.cjs` | ✅ 完成 |
| F5 | 静态守阵 `_scan_filter_facets` + `_computed_body`/`_strip_js_comments` 两个小工具 | `tests/test_web.py` | ✅ 完成 |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 复现两个缺陷(桩服务 + Playwright, 含"陈旧快照"注入) | ✅ 完成 |
| F1/F2 筛选器取数面单点 | ✅ 完成 |
| F3 真值事件后的覆盖保持 | ✅ 完成 |
| F4 冒烟断言 + 红验(撤掉修复必须变红) | ✅ 完成 |
| F5 静态守阵 + 红验(5 种注入违例) | ✅ 完成 |
| 全量验证(单测 + 冒烟 ok/error/hang × 双 UI) | ✅ 完成 |
| 知识库回写(pitfalls / testing / progress / activeContext) | ✅ 完成 |

## 进度日志

- 2026-09-21: 开工; 按会话协议拉 Gitee `develop`(`9f1ba5d → e5c31d1`)。
- 2026-09-21: 定位 BUG-1(种子页 `groups=0` ⇒ 四个弹层空)与 BUG-2(陈旧快照打回命令前 kind), 各自做了最小复现脚本。
- 2026-09-21: 落地 F1/F2/F3; 复现脚本前后对照: BUG-1 选项 0 → 3/3/1/1(计数与真值一致), BUG-2 第⑤步 `seeding` → `paused` 且覆盖保留、快照同意后正常释放(pend 2 → 0)。
- 2026-09-21: F4/F5 落地并红验; 冒烟 ok 68/2(两条既有)、error 68/0、hang 8/0; 单测 1142 passed 无退化。
- 2026-09-21: 知识库回写; 既有失败(`80~1000ms` 下界)定性并留待用户定夺(未改)。