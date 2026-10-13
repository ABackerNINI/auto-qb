# 26-10-14-webui-content-table-controls-inline — 内容页表格交互件收编: 操作按钮/展开钮退出独立列

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-14
**Summary:** 用户复查背景报告 26-10-14-0136 §02 的两项呈现缺陷——「种子详情内容页表格操作按钮独立成列」「展开按钮没有层级」。修法 = 内容树两变体(10 树+详情 / 11 树表批量)删除 tgl/prio 两条交互轨道: 折叠钮收编进 name 格首部(随 `p.indent` 缩进 = 树层级直接可视), 优先级徽章收编进 name 格尾部(`margin-left:auto` 右对齐, 不占轨道); name 列自此 locked(L4 续效: 隐藏 name = 一并废掉折叠钮与徽章两个交互件, ck 列同口径)。终态列集: V10 = name/size/prog(3 列), V11 = ck/name/size/prog/av(5 列)。用户已存列偏好按 key 求交, tgl/prio 陈旧键自然失效免迁移。守阵新增「tgl/prio 不得回潮成独立列」三条判据(列集键/name locked/交互件恰一次且在 name 分支), 三份 e2e spec 的列数/locked 流程/几何探针同轮改写; test.full 与 e2e @fast 全绿, 数字见 Refs 基线。

**Refs:** memory-bank/reports/26-10-14-0136-report-webui-detail-table-rebuild-review.html,memory-bank/testing/baselines/26-10-14-0639-webui-content-table-controls-inline.md
**Topics:** webui-detail-panel-redesign, webui-drawer-templates

## 原始请求

> 修复: 种子详情内容页表格操作按钮独立成列. 展开按钮没有层级
> 附录: 26-10-14-0136-report-webui-detail-table-rebuild-review.html

## 思考过程与决策

- **两项缺陷是同一个结构病的两个面**: tgl(折叠钮 18px)与 prio(优先级徽章 62px)曾是内容树两变体的两条独立网格轨道 —— 按钮被当成一列(用户报「操作按钮独立成列」), 展开钮全部钉在行首同一条竖线上、树层级只由 name 格的 paddingLeft 表达(用户报「展开按钮没有层级」)。上一轮(W5)对症状 7 的修法是给 prio 列打 `locked:true`——修的是「列不可隐藏」的能力, 没解决「按钮占一列」的呈现(报告 §3.1 判为命题偷换), 按钮至今仍各占一列, 用户复查再次点名。
- **修法 = 收编, 不是删功能**: 折叠钮迁进 name 格首部(与节点同层, 随缩进), 徽章迁进 name 格尾部(`margin-left:auto` 右对齐——不占轨道但保持各徽章仍对齐同一竖线, 观感上像一列、几何上不是一列)。两变体的行交互判据(打开优先级小菜单 / 循环优先级)原样保留, 事件委托的 `data-act` 属性一个不改, 只是 DOM 位置从行直接子格变成 name 格后代。
- **name 列必须 locked**: L4 铁律「交互件 locked」的语义随交互件搬家——隐藏 name 列 = 一并废掉折叠钮与徽章。10 无表头(列头 CSS 隐藏, 拖宽/右键隐藏本就不适用), locked 是纯声明; 11 有表头, locked 后右键出「为必显列」提示(headMenuHide 的 locked 分支只 toast 不隐藏)。
- **不搞列宽/列序迁移**: 列偏好 v5 按列 key 存, 删除 key 后旧存储里的 tgl/prio 条目不命中任何列, `loadColState` 求交自然忽略——无需迁移脚本、无需升版本(坑档 columns-persist 的既有纪律)。
- **探针与守阵判据同步换锚**: 原「按钮不占列」量具(dt-live-update #7)钉的是 prio 列 locked 必显; 新口径改钉 name 列 locked 必显; 几何守阵(dt-table-layout-parity)V10 规格从「5 格 5 轨」改「3 格 3 轨」+ 两个交互件在 name 格内。
- **范围守恒**: 只动内容树两变体(10/11)与它们的列声明/渲染分片/CSS/守阵/e2e。classic 链已整体退役(26-10-14-0204), 无第二条实现要同步; 变体 12(树图)无表格列, 不涉及; Tracker/用户两页签的 ops/act 列不在本请求范围(用户点名的是内容页)。

## 实现计划

1. app.js: `DRAWER_CONTENT_V10_COLUMNS`(tgl/prio 删, name locked)与 `DRAWER_CONTENT_V11_COLUMNS`(tgl/prio 删, name locked)改声明 + 注释重写(修法映射记录)。
2. xtpl-cells-dt.html: dt10/dt11 两分片重写 —— name 分支内收折叠钮(格首)/图标/名称/meta·miss chips/徽章(格尾), tgl/prio 分支删除; 空态合成行与勾选三态声明式原样。
3. 变体 CSS: dt10-tgl/dt11-tgl 补 `flex:none`; dt10-pbadge/dt11-pbadge 补 `flex:none; margin-left:auto`; 删 `.dt10-pnone`/`.dt11-pnone` 死规则; dt10 行左边补 4px 内边距顶替原 tgl 轨左缘; 文件头注释同步。
4. 守阵: test_webui_static_skins.py 桥接线守阵新增「tgl/prio 不得回潮」三条判据(列集无 tgl/prio 键 / name 列 locked / fold 与徽章动作在分片恰一次)。
5. e2e: drawer-content-variant-tables(dt10 交互件在 name 格断言; dt11 列数 7→5、name 列改 locked 必显、隐藏列换 size、回放 4 列)、dt-table-layout-parity(V11 列数 7→5; V10 树形态规格 5→3 轨/格 + tglInName/badgeInName 探针)、dt-live-update(#7 量具改钉 name 列 locked)三份同轮改写。
6. test.full + e2e @fast 全量验, 基线切片落 testing/baselines/, 知识库回写。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 列声明改轨(V10 3 列 / V11 5 列, name locked) | ✅ |
| dt10/dt11 渲染分片重写(交互件收编 name 格) | ✅ |
| 变体 CSS(徽章右对齐/删死规则/行左缘) | ✅ |
| 守阵新增回潮判据(三条) | ✅ |
| e2e 三份 spec 同轮改写 | ✅ |
| test.full 基线切片 + 知识库回写 | ✅ |

## 进度日志

- **2026-10-14 06:0x**: 开工先 `my-commit-flow.sync` → 快进 `20586350→d5221331`(远端领先 1 笔, 与本专题无关的 traffic issue 清偿)。读背景报告 26-10-14-0136, 定位两项缺陷的同一结构根因(tgl/prio 两轨道)。
- **摸底**: 引擎侧 `dt_table.js`(几何单点)与 `drawer_templates.js`(桥)零改动面——几何是 `gridStyle` 按列集现算, 删列即删轨; 真改动只在列声明/渲染分片/CSS/守阵/e2e 五处。跑真浏览器探针截图确认修前形态(按钮在最右独立列, 展开钮钉行首)。
- **改动**: 9 个修改文件(app.js / xtpl-cells-dt.html / 2 变体 js / tests + 3 e2e spec / 报告 doc-refs 反声明)+ 2 个新建 KB 文件(本档案 + activeContext 切片)+ 1 条基线切片, 命中立档阈值(≥3 源文件)。
- **验证**: pytest 静态守阵两文件全绿; e2e @fast 全量 70 例绿(含本 spec 三份); 修后截图确认折叠钮随缩进、徽章在 name 格尾右对齐、行 3/5 格 3/5 轨。test.full 3205 passed + 4 skipped, 数字见 Refs 基线。
