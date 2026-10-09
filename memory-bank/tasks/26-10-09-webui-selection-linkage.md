# 26-10-09-webui-selection-linkage — 组↔成员选中双向联动 + 成员行站点列去方框/选中视觉对齐

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 16:35
**Topics:** webui-selection
**Summary:** 用户命题三件套(辅种页 + 类推追剧页): ①成员行「站点」列去掉代表状态的小方框(只留站点名); ②成员行选中视觉与种子页选中种子同形(柔底 + 左色条); ③组↔成员选中**双向联动**且真改写选中数据 —— 组选中 ⇒ 成员全选(`_selAddGroup` 把组 key 与成员 hash 一起写入), 成员全选 ⇒ 组入选(`_selSyncGroups` 回扫), 撤到不全 ⇒ 组移出。连带修两个消费端口径: `selectedCount` 改走 `selHashSet.size` 去重(组 key 与其成员 hash 同时在集合里)、`_bulkTargets` 剔除已被选中组覆盖的成员 hash(否则同一目标既发组命令又发成员命令)。**补选/降级分治**: 补选只在组数据为当前视图权威的视图做(viewMode !== "torrents" —— 种子页不回 groups, `decoratedGroups` 是冻结快照), 降级(不再完整的组移出)所有视图都做。改动 12 个前端文件(模板 2 + 三皮肤 CSS 4 + shared js 5)+ 守阵 2 条 + e2e 全绿。
**Refs:** memory-bank/activeContext/26-10-09-1615-webui-selection-linkage.md,memory-bank/testing/baselines/26-10-09-1634-webui-selection-linkage.md

## 原始请求

> 用户(2026-10-09): 「将辅种页分组内种子"站点"列代表状态的方框移除, 选中种子改为种子页选中种子相同的视觉效果, 当一个组内的种子被全选时, 该组被选中, 同理一个组被选中时, 该组成员全部选中. 将其类推到追剧页中.」

澄清拍板(AskUserQuestion): ①"方框" = **成员行**站点列站点名前那个状态色小方块/圆点(不是组行站点列的胶囊 chip); ②移除后只留站点名文本; ③联动要**真改写选中数据**(非纯视觉)。

## 思考过程与决策

- **立项取景**: 先起桩(`scripts/ui_harness.py`)+ Playwright 截图/DOM dump 定位"方框"歧义(组行站点列的 `.site-chip` 状态色胶囊 vs 成员行 `.m-site` 的 7px 状态点), 再问用户拍板 —— 猜错要在 3 皮肤 × 模板 × 选择逻辑上返工。
- **联动口径取代 FX-11 互斥**: 旧口径"组/成员两类选择互斥, 同一时刻只有一侧非空"与"组选中 ⇔ 成员全选"直接冲突。取**超集模型**: `selGroups` = 完整入选的组 key, `selMembers` = 全部选中成员 hash(含组带来的), `selHashSet` 不变(本来就去重合并)。选超集而非"分区规范型"(组 key 与散 hash 互斥)的决定性理由: 分区型下用户 Ctrl+点选已选组的一个成员想撤选, 组 key 仍在 ⇒ 该成员依然显示选中 ⇒ **撤选失灵**; 超集型下撤一个 hash → 回扫把组移出, 交互自然。
- **写入单点三件套** `_groupHashes/_selAddGroup/_selDropGroup` + 回扫 `_selSyncGroups`: 五个成员侧变更点(toggleMemberSel/shiftMemberSel/shiftTorrentSel/_toggleUnit/_extendUnit)与两个组侧入口(toggleGroupSel/shiftGroupSel)全部收口, 不许再手写 `selGroups = []` 清另一侧(FX-11 残留会打断联动)。
- **追剧页无需新逻辑**: 集行的选中态(`epSelState`)本来就按成员完整度派生、`_toggleUnit` 本来就写成员 hash —— 两个方向早已成立; 本次只是同一套 CSS/模板改法覆盖它, 并让它随 `_selSyncGroups` 顺带联动辅种组。
- **❗踩坑(本会话实测抓到)**: `_selSyncGroups` 首版无条件按 `decoratedGroups` 回扫, e2e `menus.spec.mjs` W2 立刻红 —— 种子页按 `VIEW_ARRAYS` 不回 groups, 但**切视图后 `groups` 停在上次辅种页的冻结快照**(decorate.js 注释早已记过"或停在冻结的旧值"), 于是种子页点选 3 个种子(其中两个恰成一组)被补选成组 key, 批量限速载荷从"3 个 hash"漂成"1 组 key + 1 hash"。**判别**: 载荷 shape 变了但覆盖面没变 —— 不是命令丢了目标, 是目标形态被改写。**处置 = 补选/降级分治**(见 Summary); e2e 无需放宽断言。
- **`_bulkTargets` 去重是硬前提**: 超集模型下不剔除被组覆盖的 hash 会让同一目标既出现在 `keys` 又出现在 `hashes`(重复投递); 去重后 `keys`+`hashes` 的覆盖面与选中集合严格相等。

## 实现计划

- **S1** 模板/CSS: groups.html / shows.html 成员行站点格去 `<i class="dot">`; 三皮肤(atlas·prism·console)删 `.m-site .dot*` 死规则 + `.member-row.selected` 并入 `.group-row.selected` 同一条规则(底色 + 左色条)。
- **S2** 选择逻辑: selection.js 写入三件套 + 回扫 + `groupSelState` 派生兜底 + `selectedCount` 去重; commands.js `_bulkTargets` 去重; shortcuts.js 全选/反选三视图分支; polling.js 行级增删后回扫; state.js 注释。
- **S3** 守阵: `tests/test_web_shortcuts.py` 新增 `test_sel_group_member_linkage` + `test_sel_visual_parity_and_site_cell`(头部测试计划同步)。
- **S4** 收尾: 真浏览器核验(辅种/追剧/种子三视图 + 三皮肤)、KB 回写、基线、`kb.index`。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 模板去 dot + 三皮肤 CSS(去死规则 + 选中视觉成对) | Done |
| S2 | 选择联动(selection/commands/shortcuts/polling/state) | Done |
| S3 | 守阵 2 条(含头部测试计划) | Done |
| S4 | 真浏览器核验 + KB 回写 + 基线 + kb.index | Done |

## 进度日志

- **2026-10-09 16:35** 全部落地。S1/S2 见上; S2 途中 e2e 抓到冻结快照补选坑(见思考过程), 改为补选/降级分治后 `dev.e2e` 118 passed / 0 failed; S3 守阵 2 条绿(红验: 守阵先于实现写时曾按旧 CSS 结构误锚 `.group-row.selected` 首个出现位置 —— prism 的 `> :first-child` 规则在文件里更早, 改按选择器全名精确锚定); S4 回写 `memory-bank/modules/webui-static-contract.md`「选择模型」条(FX-11 互斥 → 双向联动 + 两个消费端口径), 基线切片入库, `kb.index` 重建。门禁: `test.full` 与 `dev.e2e` 全绿(数字见 `commands run kb.baseline`)。
- **2026-10-09 15:17** 开工: 同步(已同步 1d71a692)→ 取景(桩 + 截图 + DOM dump)→ 澄清拍板 → 实施。
