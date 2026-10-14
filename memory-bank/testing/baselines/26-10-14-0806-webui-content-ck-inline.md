# 3205 —— 内容页「树表批量」勾选框收进 name 格(ck 独立列退役)

**Refs:** memory-bank/tasks/26-10-14-webui-content-ck-inline.md

> 摘要: 失修 26-10-14 用户二次复查(报告 26-10-14-0136 §02 续)——「种子详情内容页「树表批量」复选框仍然独立成列, 还能调整位置」。上一轮收编 tgl/prio 两轨道, 但 ck 勾选框仍独立成列(拖宽可调)。修法 = 勾选框收进 name 格首部随缩进(与节点同层, 不占轨道); ck 列删除(终态 V11 = name/size/prog/av 四列), 勾选框随 name 格走 ⇒ name 列 locked 续效(隐藏 name = 一并废掉勾选框/折叠钮/徽章三个交互件)。验证 = pytest 全量 + e2e @fast 全量(134 例)。
> 基线时间: 2026-10-14 08:06
> 档案: memory-bank/tasks/26-10-14-webui-content-ck-inline.md

## 验收数字

- `test.full`: **3205 passed + 4 skipped** / `TOTAL 16824 158 5724 140 99%`(99%, 过 98% 闸门)。
- 耗时: **109.5s**(单次采样, 口径见 baseline.md)。
- e2e @fast 全量(本机 8137 起桩串行): **134 passed**(含本专题三份 spec: drawer-content-variant-tables / dt-table-layout-parity / dt-live-update; 未跑全量矩阵轮, 口径同前基线)。
- 包内脚本测试(`commands run test.pkg`): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 闸门 match 不命中, 未跑。
- Linux(WSL)侧未重测 —— 改动为纯前端(静态 JS/CSS/列声明)+ 测试, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- **源(3 文件)**: `app.js`(`DRAWER_CONTENT_V11_COLUMNS` 删 ck 列, name locked 续效 + 注释二次复查) · `tpl/xtpl-cells-dt.html`(dt11 分片: 勾选框收进 name 格首, ck 分支删) · `drawer_tpl/11-content-treegrid-batch-low.js`(`.dt11-ck` 补 `flex:none`, 注释二次复查).
- **测试(4 文件)**: `tests/test_webui_static_skins.py`(桥接线守阵新增「ck 不得回潮成独立列」判据 + 勾选框动作恰一次且 name 分支内) · `e2e/drawer-content-variant-tables.spec.mjs`(dt11 列数 5→4、hc-ck 右键删、name 列废掉三交互件、回放 3 列) · `e2e/dt-table-layout-parity.spec.mjs`(V11 列数 5→4) · `e2e/dt-live-update.spec.mjs`(#7 终态不变量改挂 `.dt11-n .dt11-ck`).
- **文档**: 本切片 · 任务档案 `tasks/26-10-14-webui-content-ck-inline.md` · activeContext 切片 `26-10-14-0633-webui-content-table-controls-inline.md`(续效 ck) · 报告 26-10-14-0136 doc-refs 追加本档案反声明 · `kb.index` 生成物重建.

## 已知偏差 / 移交

- **ck 列偏好陈旧键免迁移**: 用户已存列偏好按 key 求交, ck 陈旧键自然失效(坑档 columns-persist 既有纪律), 无需升版本.
- **报告 §02 其余问题面未动**: 点击乱选 / 点击跳动 / 无点击排序 / 合并态切换内容消失等仍开放(普通签/用户签/Tracker 签的同类「按钮占列」形态也未动——用户本轮点名的是内容页「树表批量」).
