# 26-10-09-1615-webui-selection-linkage

> 摘要: 用户命题(辅种页 + 类推追剧页)三件套: ①成员行「站点」列去掉代表状态的小方框(只留站点名); ②成员行选中视觉与种子页选中种子同形(柔底 + 左色条, 三皮肤); ③组↔成员选中**双向联动**且真改写选中数据 —— 组选中 ⇒ 成员全选(`_selAddGroup`), 成员全选 ⇒ 组入选(`_selSyncGroups` 回扫), 撤到不全 ⇒ 组移出; 连带 `selectedCount` 走 `selHashSet` 去重、`_bulkTargets` 剔除被选中组覆盖的成员 hash, 补选/降级分治(种子页不补选 —— 那里的 `groups` 是冻结快照)。已落地, 档案 Done。
> 最后活动: 2026-10-09 16:34

**Refs:** memory-bank/tasks/26-10-09-webui-selection-linkage.md

## 已完成

- 模板/CSS: groups.html + shows.html 成员行站点格去 `<i class="dot">`; atlas·prism·console 三皮肤删 `.m-site .dot*` 死规则; `.member-row.selected` 并入 `.group-row.selected` 同一条规则(底色 + 左色条)。
- 选择逻辑: selection.js 新增 `_groupHashes`/`_selAddGroup`/`_selDropGroup`/`_selSyncGroups`(写入单点), 五个成员侧变更点全部回扫, `groupSelState` 按成员完整度派生 selected(视觉兜底), `selectedCount` → `selHashSet.size`; commands.js `_bulkTargets` 去重; shortcuts.js 全选/反选三视图分支收口; polling.js 行级增删后回扫。
- 守阵: `test_web_shortcuts.py` 新增 2 条(联动写入口/变更点回扫/消费端去重 + 视觉成对/站点格无 dot)。
- 门禁: `test.full` 2852 passed / 0 failed(覆盖率 99%); `dev.e2e` 118 passed / 0 failed(首轮 2 failed 抓到「种子页 groups 冻结快照被回扫补选」坑, 补选/降级分治后复绿, 未放宽任何 e2e 断言)。
- 回写: `memory-bank/modules/webui-static-contract.md`「选择模型」条(FX-11 互斥 → 双向联动 + 两个消费端口径)、基线切片、`kb.index`。

## 本轮关键取舍(沉淀)

- **超集模型而非分区规范型**: 分区型(组 key 与散 hash 互斥)下撤选已选组的单个成员会失灵(组 key 还在 ⇒ 成员仍显示选中); 超集型撤一个 hash 即由回扫把组移出, 交互自然。
- **补选/降级分治**: 补选(新凑齐的组入选)只在 `viewMode !== "torrents"` 做 —— 种子页不回 groups, `decoratedGroups` 是上次辅种页的冻结快照, 拿它补选会把"我选了这些种子"在批量载荷里漂成"按组下发"; 降级(不再完整的组移出)所有视图都做, 否则种子页撤选组内一员后残留组 key 会把已撤选种子卷进批量命令。

## 下一步

- 无未竟事项。真机长库(3000+)下回扫耗时未实测(见基线切片「未验证面」); 若有点滞后再把 `_selSyncGroups` 收成增量回扫。
