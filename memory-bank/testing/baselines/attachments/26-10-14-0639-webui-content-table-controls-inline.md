# 3205 —— 内容页表格交互件收编: 操作按钮/展开钮退出独立列(按钮不占列 + 展开钮有层级)

**Refs:** memory-bank/tasks/26-10-14-webui-content-table-controls-inline.md

> 摘要: 失修 26-10-14 用户复查两项呈现缺陷(报告 26-10-14-0136 §02)——「种子详情内容页表格操作按钮独立成列」「展开按钮没有层级」。修法 = 内容树两变体(10 树+详情 / 11 树表批量)删除 tgl/prio 两条交互轨道: 折叠钮收编进 name 格首部(随缩进 = 树层级可视), 优先级徽章收编进 name 格尾部(margin-left:auto 右对齐); name 列 locked(L4 续效)。终态 V10 = 3 列 / V11 = 5 列。验证 = pytest 全量 + e2e @fast 全量(70 例)+ 修前/修后真浏览器截图对比(tmp-analysis/before|after-v10|v11.png)。
> 基线时间: 2026-10-14 06:39
> 档案: memory-bank/tasks/26-10-14-webui-content-table-controls-inline.md

## 验收数字

- `test.full`: **3205 passed + 4 skipped** / `TOTAL 16824 158 5724 140 99%`(98.65%, 过 98% 闸门)。
- 耗时: **111.23s**(单次采样, 口径见 baseline.md)。
- e2e @fast 全量(本机 8137 起桩串行): **70 passed**(含本专题三份 spec: drawer-content-variant-tables / dt-table-layout-parity / dt-live-update; 未跑全量矩阵轮, 口径同前基线)。
- 包内脚本测试(`commands run test.pkg`): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 闸门 match 不命中, 未跑。
- Linux(WSL)侧未重测 —— 改动为纯前端(静态 JS/CSS/列声明)+ 测试, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- **源(4 文件)**: `app.js`(`DRAWER_CONTENT_V10/V11_COLUMNS` 删 tgl/prio, name locked) · `tpl/xtpl-cells-dt.html`(dt10/dt11 分片重写: 交互件收编 name 格) · `drawer_tpl/10-content-tree-detail-tall.js`(徽章 flex:none+margin-left:auto, 删 pnone 死规则, 行左缘 4px, 注释) · `drawer_tpl/11-content-treegrid-batch-low.js`(同套 CSS + 注释)。
- **测试(4 文件)**: `tests/test_webui_static_skins.py`(桥接线守阵新增「tgl/prio 不得回潮」三条判据) · `e2e/drawer-content-variant-tables.spec.mjs`(dt10 交互件在 name 格断言; dt11 列数 7→5、name 列 locked 必显、隐藏列换 size、回放 4 列) · `e2e/dt-table-layout-parity.spec.mjs`(V11 列数 7→5; V10 树形态规格 5→3 轨/格 + tglInName/badgeInName 探针) · `e2e/dt-live-update.spec.mjs`(#7 量具改钉 name 列 locked)。
- **文档**: 本切片 · 任务档案 `tasks/26-10-14-webui-content-table-controls-inline.md` · activeContext 切片 `26-10-14-0633-webui-content-table-controls-inline.md` · 报告 26-10-14-0136 doc-refs 追加本档案反声明 · `kb.index` 生成物重建。

## 已知偏差 / 移交

- **徽章对齐口径可选**: 当前徽章 `margin-left:auto` 右对齐在 name 格尾(各徽章同一竖线, 观感近原独立列但零轨道); 若要改为「紧贴名称右侧」, 摘掉两处 `margin-left:auto` 即可, 单 point。
- **报告 §02 其余问题面未动**: 点击乱选 / 点击跳动 / 无点击排序 / 合并态切换内容消失等仍开放(普通签/用户签/Tracker 签的同类「按钮占列」形态也未动——用户本轮点名的是内容页)。
- **变体 10 目录行不再显示「—」占位**: 原 prio 列目录行出 `dt10-pnone`「—」; 收编后目录行无徽章(优先级是文件动作, 目录批量在右详情面板/11 的吸底条), 该死规则已删。
