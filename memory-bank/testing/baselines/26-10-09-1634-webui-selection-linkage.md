# 2852 —— 组↔成员选中双向联动 + 成员行站点列去方框/选中视觉对齐

> 摘要: 用户命题(辅种页 + 类推追剧页)三件套落地 —— ①成员行「站点」列去掉代表状态的小方框(只留站点名); ②成员行选中视觉与种子页选中种子同形(柔底 + 左色条, 三皮肤成对); ③组↔成员选中**双向联动**且真改写选中数据(`_selAddGroup`/`_selDropGroup`/`_selSyncGroups` 单点, 取代 FX-11 互斥), 连带 `selectedCount` 走 `selHashSet` 去重、`_bulkTargets` 剔除被选中组覆盖的成员 hash, 补选/降级分治(种子页不补选)。档案 [26-10-09-webui-selection-linkage](../../tasks/26-10-09-webui-selection-linkage.md)。
> 档案: memory-bank/tasks/26-10-09-webui-selection-linkage.md
> 基线时间: 2026-10-09 16:34

**Refs:** memory-bank/tasks/26-10-09-webui-selection-linkage.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2852 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial)
- **耗时**: 单次 26.71s(命令墙时 28.6s)

## 说明

- **代码事实变更**: 前端 12 文件(模板 groups.html/shows.html + 三皮肤 CSS 4 份 + shared js 5 份: selection/commands/shortcuts/polling/state)+ 守阵新增 2 条(`test_web_shortcuts.py::test_sel_group_member_linkage` / `test_sel_visual_parity_and_site_cell`); 无 Python src / 配置键 / 后端改动。相对上基线的 +2 passed = 新增守阵 2 条。
- **e2e 门禁**: `commands run dev.e2e` **118 passed + 0 failed + 10 skipped**(2.7m, 双皮肤全量集)—— 首轮曾 2 failed(`menus.spec.mjs` W2 批量限速载荷形态), 归因 = 种子页上 `groups` 停在冻结快照导致回扫把点选种子补选成组 key, 改为补选/降级分治后复绿(未放宽任何 e2e 断言)。
- **真浏览器核验**(桩 60 种子/6 组, atlas·prism·console 三皮肤): 成员行站点格无残留 `.dot` / 组行·成员行·种子页种子行选中态 `::before` 逐项同形(3px 左色条同色) / 辅种页全选成员⇒组行 `selected`、选组⇒成员全 `selected`、撤一个成员⇒组转 `partial` / 追剧集行同款两方向成立。
- **环境**: HEAD `1d71a692`(会话开工 `my-commit-flow.sync` 已同步), 其上叠加本轮未提交的改动。
- **未验证面**: 真机 qB 上的长库(3000+)下 `_selSyncGroups` 每次成员点选的回扫耗时未实测(桩上无感; 复杂度 O(组数×组成员数), 全选走 `_selAddGroup` 逐组写入为 O(G²) 拷贝, 大库若有点滞后再收成增量回扫)。
