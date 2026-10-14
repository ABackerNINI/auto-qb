# 26-10-14-webui-content-ck-inline — 内容页「树表批量」勾选框收进 name 格(ck 独立列退役)

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-14
**Summary:** 用户二次复查(报告 26-10-14-0136 §02 续)——「种子详情内容页「树表批量」复选框仍然独立成列, 还能调整位置」。上一轮收编 tgl/prio 两轨道, 但 ck 勾选框仍独立成列(拖宽可调)。修法 = 勾选框收进 name 格首部随缩进(与节点同层, 不占轨道); ck 列删除(终态 V11 = name/size/prog/av 四列), 勾选框随 name 格走 ⇒ name 列 locked 续效(隐藏 name = 一并废掉勾选框/折叠钮/徽章三个交互件)。守阵新增「ck 不得回潮成独立列」判据 + 勾选框动作恰一次且 name 分支内; e2e 三份 spec 同轮改写(列数 5→4、hc-ck 右键删、终态不变量改挂 name 格内); test.full 与 e2e @fast 全绿, 数字见 Refs 基线。

**Refs:** memory-bank/reports/26-10-14-0136-report-webui-detail-table-rebuild-review.html,memory-bank/testing/baselines/26-10-14-0806-webui-content-ck-inline.md
**Topics:** webui-detail-panel-redesign, webui-drawer-templates

## 原始请求

> 种子详情内容页「树表批量」的复选框仍然独立成列的, 还能调整位置, 需要更改

## 思考过程与决策

- **同结构病, 第三面**: 上一轮(26-10-14-0633)收编 tgl(折叠钮)/prio(徽章)两轨道进 name 格, 但 ck(勾选框)仍独立成列 —— 用户再次点名「复选框仍然独立成列, 还能调整位置」. 勾选框是交互件(勾选批量优先级), 独立成列即拖宽可调即「按钮占列」呈现缺陷, 与 tgl/prio 同族.
- **收进 name 格首随缩进**: 勾选框与节点同层(随缩进 = 层级), 不占轨道. 勾选框三态(:checked/:indeterminate)声明式直持原样, 判据在变体 rowsFn 不改. 勾选集按 path 记账原样.
- **ck 列删除, name 列 locked 续效**: L4 铁律「交互件 locked」随交互件搬家 —— 隐藏 name = 一并废掉勾选框/折叠钮/徽章三个交互件. ck 列偏好陈旧键按 key 求交自然失效(坑档 columns-persist 既有纪律), 免迁移.
- **拖宽随 name 列**: ck 列独立拖轨道已删, 勾选框随 name 格走, 拖宽改挂 name 列(用户「还能调整位置」即独立拖轨道, 随 ck 列删即随轨道删).
- **范围守恒**: 只动内容页变体 11(树表批量)与它的列声明/渲染分片/CSS/守阵/e2e. 变体 10(树+详情)无勾选框(优先级走右详情面板), 不涉及. classic 链已整体退役(26-10-14-0204), 无第二实现. Tracker/用户两页签的 ops/act 列不在本请求范围(用户点名的是内容页「树表批量」).

## 实现计划

1. app.js: `DRAWER_CONTENT_V11_COLUMNS` 删 ck 列, name locked 续效 + 注释二次复查(终态 11 = name/size/prog/av 四列).
2. xtpl-cells-dt.html: dt11 分片重写 —— 勾选框收进 name 格首(随缩进), ck 分支删; 空态合成行与勾选三态声明式原样.
3. 变体 11 CSS: `.dt11-ck` 补 `flex:none`(在 name flex 格内不缩); 注释二次复查.
4. 守阵: test_webui_static_skins.py 桥接线守阵新增「ck 不得回潮成独立列」判列 + 勾选框动作恰一次且 name 分支内.
5. e2e: drawer-content-variant-tables(dt11 列数 5→4、hc-ck 右键删、name 列废掉三交互件、回放 3 列)、dt-table-layout-parity(V11 列数 5→4)、dt-live-update(#7 终态不变量改挂 `.dt11-n .dt11-ck`)三份同轮改写.
6. test.full + e2e @fast 全量验, 基线切片落 testing/baselines/, 知识库回写.

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 列声明改轨(V11 4 列, name locked 续效) | ✅ |
| dt11 渲染分片重写(勾选框收进 name 格首) | ✅ |
| 变体 11 CSS(ck flex:none, 注释) | ✅ |
| 守阵新增 ck 回潮判据 | ✅ |
| e2e 三份 spec 同轮改写 | ✅ |
| test.full 基线切片 + 知识库回写 | ✅ |

## 进度日志

- **26-10-14 07:3x**: 开工先 `my-commit-flow.sync` → 快进 `b59fd7be→fb58a9e4`(远端领先 1 笔, 与本专题无关的 traffic issue 清偿). 读上一轮档案 26-10-14-webui-content-table-controls-inline.md, 定位 ck 勾选框仍独立成列(拖宽可调)的第三面.
- **摸底**: 引擎侧 `dt_table.js`(几何单点)与桥零改动面 —— 几何是 `gridStyle` 按列集现算, 删列即删轨; 真改动只在列声明/渲染分片/CSS/守阵/e2e 五处.
- **改动**: 3 源文件(app.js / xtpl-cells-dt.html / 11-content-treegrid-batch-low.js)+ 4 测试文件(tests + 3 e2e spec)+ 2 新建 KB 文件(本档案 + 基线切片)+ 续效 activeContext 切片.
- **验证**: pytest 静态守阵全绿(test_webui_static_skins.py 15 passed); e2e @fast 全量 134 例绿(含本 spec 三份); test.full 3205 passed + 4 skipped, 99% coverage, 数字见 Refs 基线.
