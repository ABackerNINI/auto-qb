# 3983 passed + 10 skipped —— 抽屉变体渲染层三族重复收敛: 三态空帧单点 + peers 判据共用 + dt 值格模板合一 (issue 26-10-20-2231)

> 摘要: 抽屉变体渲染层三族重复收敛(issue 26-10-20-2231 认领修复) —— 27 块三态空帧骨架收敛为 `H.emptyFrame` 单点(9 件桥变体各一处接线), 07/08/09 五件 peers 判据逐字副本收敛为 `reg.peers` 命名空间, dt07/08/09 三份 x-template 合一为 `tpl-aq-dt-peer-cells`(pfx/occ 两 prop, 类名渲染结果与旧逐字同), 行为零变化
> 基线时间: 2026-10-22 00:39
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-drawer-variant-renderer-dup.html, memory-bank/tasks/26-10-21-webui-drawer-variant-renderer-dup.md

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 改动落盘后实测输出:

```text
TOTAL                                                20739    115   7090    104    99%
3983 passed, 10 skipped in 87.11s (0:01:27)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 动手前在同一棵树上(同步重组后的 8f39b625)先跑了一遍全量取基线, 同样全绿(3982 passed) —— 本次 passed +1 即新增守阵 `test_drawer_variant_skeleton_single_point`, 其余逐位持平。
- 真浏览器侧: `commands run dev.e2e` 全量集 **336 passed / 10 skipped(11.6m)** —— 与上轮基线逐位持平(本族改动的验收口径即「类名渲染结果与旧逐字同」, e2e 数字不动恰是预期: 三皮肤 CSS 与 `_scan_ui_diff_registry` 零触碰)。
- 定向: `tests/test_webui_static_dom_panel.py` + `test_webui_static_dom_page.py` 86 passed、`test_webui_static_skins.py` 23 passed(守阵⑨ 并集口径改写后复绿); e2e 定向子集 94 passed(peers-columns / variant-tables / sticky-flush / dt-table-face-bg / layout-parity / bridge-stub / content-dt11-sticky / drawer-peers / switch-no-flash, 3.1m + 31s)。
- 红验三支全部命中即红, 还原后复绿: ①05 接线改名(`H.emptyFrame` → `H.emptyFrames`)→「接线数漂了」红; ②08 复活本地 `isBad` 定义→「判据本地副本」红; ③旧模板 id `tpl-aq-dt07-cells` 回潮→「旧分片残留」红。
- 耗时区间: test.full 一遍 87.1s(上一轮 88.8s); e2e 一遍 699s(11.6m)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/drawer_templates.js` | HELPERS 加 `emptyFrame(host, o)`(has 闸 + loading→err→empty 优先级 + 整帧换帧, 有数据返 false 调用方续跑, 否则渲槽返 true); TPL_REG 挂 `peers` 命名空间(`FLAG_META` 10 项徽章表 + `flagTokens`/`isBad` 吸血启发式 + `bucketOf` 五桶 + `isLanIp` 内网判定五件) |
| `src/auto_qb/webui/static/shared/drawer_tpl/04~12`(九件桥变体) | 27 个手抄三态块(各 4 处) → 各 1 处 `H.emptyFrame` 调用; 槽类名/文案逐件誊(tracker 族 04-06 / 用户族 07-09 / 文件族 10-12); general 三件(01-03)无三态刻意不收编 |
| `src/auto_qb/webui/static/shared/drawer_tpl/07-peers-dashboard-tall.js` / `08-peers-groups-low.js` / `09-peers-density-collapsed.js` | 删五件判据本地副本, 接 `const P = reg.peers;`; 07 私有 `flagHas` 保留但其体内改走 `P.flagTokens(p)`; BUCKETS/FILTERS/clientName/countsOf 为变体私有不动 |
| `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html` | 356→310 行: dt07/dt08/dt09 三份 x-template 合一为单一 `tpl-aq-dt-peer-cells`, 类名经 `pfx` prop 计算, dt09 三处特化(upspeed 占用条 / dlspeed 平铺无 `<b>` 包裹 / files 列)由 `occ` prop 表达; 头部注释记载合一决策 |
| `src/auto_qb/webui/static/shared/table.js` | DT07/DT08/DT09 三组件同名不变共享 `#tpl-aq-dt-peer-cells`, 默认 prop 各表自己: pfx(`dt07`/`dt08`/`dt09`) + occ(false/false/true) |
| `tests/test_webui_static_skins.py` | 守阵⑨改「单一模板覆盖三变体列键并集(10 键)」口径(原要求三份分片在册); 顺手删死变量 `app_keys` |
| `tests/test_webui_static_dom_panel.py` | 新增 `test_drawer_variant_skeleton_single_point`(emptyFrame 在册 + 9 件接线数/槽类名/空态文案逐件对账 + 「正在加载…」反向断言 + general 钉 0; reg.peers 五件 + TPL_REG 挂载 + 三件 `const P = reg.peers;` + 本地副本反向断言; 单一模板 + 旧 id 零残留 + 三组件 pfx/occ 默认值), 文件头测试计划同步 |
| `memory-bank/modules/webui-static-contract.md` | P6 条目后新增「抽屉变体渲染层三族重复收敛」契约条(三族单点口径 + pfx/occ + 守阵编号) |
