# 26-10-12-webui-drawer-table-rework — WEBUI 抽屉表格统一重写（U0–U5）

**Status:** Done
**Added:** 2026-10-12
**Updated:** 2026-10-12 18:00
**Summary:** 依据双计划联合审计（26-10-12-0455）修正计划的执行档案：U0 冻结 + 1722 P6 契约交付；U1 引擎 spike（列子集声明 / 排序 per-table-id 泛化 / Teleport 锚桥，stub 四路径 e2e 闸门通过）；U2 用户表三变体（07/08/09）表格体重写接引擎（锚保活/对账/触碰三件套 + 分段桥 + omitEmpty 渐进列，e2e 手势红绿双验）；U3 tracker 三变体（04/05/06）表格体重写接引擎（04 分段钮 dtSortSet 直设并引擎、05 异构分组单列满宽行桥、06 八列引擎表头，reannounce 闸门等专属守阵逐条对账改锚，e2e 红绿双验）；U4 内容树两变体（10/11）表格体重写接引擎（D4=A 树缩进格进渲染器 + 桥模板行级键盘扩展 data-dt-key/rowTab/rowAfter，e2e 红绿双验）；U5 收口（交互单点守阵定型「声明即受检」+ 红验两条 + 债务「已清偿」入账 + 1722 P6 闭环 + 2106 回引 + Q1–Q5 终态 18/18 定格）。**U0–U5 全部完结**（计划 Status → Done），终态 = 新增变体表格表面 = 外壳一个锚 + 描述符一行 + 一个行渲染器，表壳/交互/持久化/对齐零改动。
**Topics:** webui-drawer-table-rework
**Refs:** memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/reports/26-10-12-0455-report-webui-drawer-table-unification-audit.html,memory-bank/issues/26-10-12-0800-bug-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-12-0806-webui-drawer-table-rework-u2.md,memory-bank/testing/baselines/26-10-12-0913-webui-drawer-table-rework-u3.md,memory-bank/testing/baselines/26-10-12-1036-webui-drawer-table-rework-u4.md,memory-bank/testing/baselines/26-10-12-1800-webui-drawer-table-rework-u5.md

## 原始请求

用户裁定（26-10-12-0455 审计 + 0533 拍板）：「不考虑兼容 = 旧表格全部重写」——抽屉内 18 个手搓表格表面按 U0–U5 六波统一到引擎（aq-table 表壳 + 列选择器 + 排序 + 拖宽 + 右键隐藏 + 偏好持久化），每变体独立 table-id；拍板 D1 = Teleport 锚桥、D2 = 保留变体列个性、D3 = 排序全并引擎、D4 = 树缩进格进渲染器、D5 = 观感保持变体个性、D6 = 列偏好键每变体独立。指令「提交后继续」授权 U1 闸门后连续推进 U2。

## 思考过程与决策

- **真实变体与 stub 的关键差异**：stub 外壳 sig 恒定不重建；真实变体外壳随 5s 数据轮询整帧重建 —— U1「锚只建一次」不变量直接冲突。解法 = 锚保活三件套：`H.anchFill`（外壳重建后把宿主记账的锚元素替换进 `<div data-dt-anchor-slot>` 位，锚元素身份跨帧稳定）、`dtSyncAnchors`（挂载拍/数据通知/回落清宿主三路收口到 `_dtRender` 尾部单点的锚对账，按 tid **元素集合**比对——逐个比对会让 08 第二个锚误判换代）、`H.anchTouch`（变体 UI 态翻动后对在场 tid 强制自增一代，桥重挂重读 rowsFn）。
- **行来源含非响应式 UI 态**（07/09 筛选 chips、08 只看在传）：引擎对变体闭包态无感知 → rowsFn 由桥重挂时重读，而非响应式追踪。
- **08 五分组**：描述符 `segs: true` → rowsFn 返回 `[{key, rows}]`，桥逐段 teleport 到 `[data-dt-table-anchor][data-dt-seg]`；分组头留外壳（分组是版式，行是引擎表体）——与计划口径吻合。
- **渲染器判据零复制**：Vue 模板无法调用变体文件函数 → 行装配在变体 rowsFn 预计算（显示值/`_raw` 排序原值/徽章数组/微条宽度/`_cls` 行修饰类），x-template 分片只做声明式呈现；行级个性经描述符 rowCls 绑引擎行容器 `.group-row`（D5）。
- **吸顶个性**：皮肤 `.drawer-body .group-head { position: static }` 会吞引擎表头吸顶 → 变体 CSS 以 `.dtNN-list .group-head { position: sticky; top: -14px }`（特异性 0,3,0）反压制恢复（sticky-scrollpad-inset 口径不变）。
- **渐进 files 列**：qB 不回 peers.files 时整列错位 bug 类 → 列定义 `omitEmpty: true` 通用机制（`_colsOmitEmpty` 在 `_visibleCols` 尾部单点，表头/行/grid/对齐同走一条路），非变体特判。
- **07 四卡仪表的卡片 grid**：Q4 判据本体是「表格容器零列宽 grid」——卡片/图例版式 grid 是 D5 保留面，守阵收窄到表格类选择器判红。

## 实现计划

U0 冻结 + 1722 P6 契约 → U1 引擎 spike（stub 闸门）→ **U2 用户表 07/08/09**（本轮）→ U3 tracker 04/05/06 → U4 内容树 10/11 → U5 收口（守阵定型 + Q1–Q5 终态 + 债务入账）。每波：计划 §09 变更行 + 本档案日志 + 基线切片。

## 子任务状态表

| 子任务 | 状态 | 备注 |
| --- | --- | --- |
| U0 冻结 + 1722 P6 契约交付 | Done | 26-10-12-0553 入库 |
| U1 引擎 spike：三件泛化 + Teleport 桥四路径闸门 | Done | e2e 抓两缺陷（行漏 sortedDrawer / gen 回落）修复入守阵 |
| U2 引擎侧：锚保活 + 分段桥 + 描述符三行 + 渲染器三份 | Done | dtSyncAnchors/anchFill/anchTouch + omitEmpty + 六 computed |
| U2 变体侧：07/08/09 三变体表格体重写 | Done | 外壳留版式，表格体全走引擎；零手搓排序/零列宽 grid |
| U2 守阵与扫描器改版 | Done | bridge_wiring 扩 U2 十二段；a11y 守阵随 D3 改版（引擎表头 a11y 缺口入 issue 池） |
| U2 e2e：两 spec 改版 + 变体手势新 spec + 红验 | Done | anchTouch 红验：空操作注入 + 轮询冻结 → 4 红，还原即绿 |
| U2 收口：文档回写 + 基线切片 | Done | 计划 §09 变更行 + 本档案 + activeContext + 基线切片 |
| U3 tracker 04/05/06 表格体重写 | Done | 04 分段钮 dtSortSet 直设 / 05 分段桥单列满宽行 / 06 八列引擎表头；专属守阵逐条对账改锚 |
| U4 内容树 10/11 表格体重写 | Done | D4=A 树缩进格进渲染器；桥模板行级键盘扩展（data-dt-key/rowTab/rowAfter）；Q1–Q5 终态 18/18 |
| U5 收口：Q1–Q5 终态 + 守阵定型 + 债务入账 | Done | 定型守阵「声明即受检」+ 红验两条 + 债务已清偿入账 + 1722 P6 闭环 + 2106 回引；Q1–Q5 终态 18/18 定格 |

## 进度日志

- **2026-10-12 0746 前（U2 实施 + 守阵 + e2e）**：引擎侧 drawer_templates.js（dtSyncAnchors 单点对账 / anchFill 保活 / anchTouch 触碰 / register 收 rowsFn / 桥方法六件扩 Segs/RowCls/dtTplRows）、xtpl.html 分段桥模板、columns.js（omitEmpty 单点 + 三变体六 computed）、app.js（三列集 D2 裁剪 / DRAWER_TABLE_DEFS 三行 / 三组件注册）、table.js 三渲染器、xtpl-cells.html 三分片（压至 399 行守单分片上限）、三变体全量重写。守阵 `test_drawer_table_bridge_wiring` 扩 U2 十二段；修掉三个自检发现项（blk 提取在内层 `},` 截断、08 注释 data-sort 字面自撞、09 漏 `const R`）。a11y 守阵 `test_drawer_tpl_a11y_and_fetch_error_states` 随 D3 改版：07/08/09 手搓排序表头 aria-sort pin 退役（排序归引擎），07/09 chips 原生 button 口径、08 折叠组 P3-4 件套保留；引擎表头 role/aria-sort 缺口属引擎全域议题，入 issue 池。
- **2026-10-12 0750（e2e）**：`drawer-peers-columns.spec` / `drawer-peers-sticky-flush.spec` 探针改引擎口径（`.group-head[data-table=drawerPeerV0X]` / `.group-row` / 分段锚），双皮肤全过；新增 `drawer-peers-variant-tables.spec`（07 手势三件套 + 默认序/引擎排序、07/09 chips、08 分段/折叠/只看在传/组内 dyn 排序），双皮肤全过。**红验闭环**：anchTouch 注入空操作 → chips 测试假绿（行靠 5s 轮询 tick 延迟刷新兜底）→ 手法修正为「初始落袋后 peers 端点挂起冻结」→ 07/09 × 双皮肤注入即红，还原即绿。全量 e2e 首轮失败全部为桩服务中途 CONNECTION_REFUSED（零断言失败，环境事故），清 8137 残留重跑通过。数字见基线切片（`commands run kb.baseline`）。
- **2026-10-12 0800（收口）**：计划 §09 U2 变更行 + 本档案 + activeContext 切片 + 基线切片；引擎表头 a11y 缺口入 issue 池（计划外，不属本波修码面）。
- **2026-10-12 0913 前（U3 实施 + 守阵 + e2e）**：引擎侧 app.js 三列集（04/05 单列满宽 card 列集 + 06 八列，next 列 sortable:false——行级/种子级/正在汇报三态混合口径无单一原值）+ DRAWER_TABLE_DEFS 三描述符（04 segs 模式排序 defKey sev、05 segs:true 空排序键保原序、06 sev 升序异常置顶）+ 三渲染器组件注册；sort.js 新增 dtSortSet 直设口（04 分段钮「模式选择」语义与引擎三态循环冲突的特例，Q3 记档，排序态仍归 dtSortState 单点）；columns.js 六 computed；xtpl-cells-dt.html 三分片新文件（xtpl-cells.html 已 399 行顶死单分片上限）+ 三份 index.html 清单挂载。变体侧 04/05/06 全量重写：04 卡片栅格覆盖引擎行容器为双列 grid、虚拟合并卡为 rowsFn 合成行、手搓分段排序退役；05 异构分组 = 分组头留外壳 + 单列满宽行桥，行三形态（fail 处置块 / row / chips 合成行），折叠与 msg 展开只翻 class 不触碰锚（行来源不变）；06 八列引擎表头 + onlyBad 外壳容器类切换（行不重装配原口径）。守阵四处计数锚红全部同轮改口径（R3 不放宽不删除）：reannounce 闸门④ 判据留变体、呈现锚迁分片；等高守阵改 grid+stretch 切片；per_tracker 探针（.dt06-next b / .dt06-gb）在分片中存活零改版全过；a11y msg 件套迁分片钉。e2e：reannounce spec 零改版全过 + 新增 tracker 变体 spec（三测试 × 双皮肤），红验两条闭环（dtSortSet 空操作注入 → 分段 active 失效即红；anchTouch 空操作注入 → 04 轮询冻结后行数失效即红，还原即绿）。
- **2026-10-12 0913（收口）**：计划 §11 U3 变更行（Q1–Q5 对账 16/18，Q3 手搓清零记档三条，U4 停手点成立：10/11 未动、树数据契约零改动）+ 本档案 + activeContext 切片 + 基线切片。
- **2026-10-12 1036 前（U4 实施 + 守阵 + e2e）**：引擎侧 app.js 两列集（10 五列 / 11 七列含 omitEmpty 可用性列与 locked 勾选/折叠列）+ 两描述符（rowTab/rowAfter 声明位）+ 两渲染器组件（drawerFileTree 树缩进格两段同构单份口径）；columns.js 四 computed；桥模板 U4 扩展三件——行容器 data-dt-key 身份锚（rowKey 值单点输出）、rowTab 声明的行容器 tabindex=-1、.group-table @vue:mounted → dtRowAfter → 变体 rowAfterFn（锚换代重挂恰好一次，roving 锚点/回焦在行进 DOM 后跑——行级键盘 a11y 面在引擎行容器上的等价落地）；drawer_templates.js register 收 rowAfterFn + 两根方法。变体侧 10/11 全量重写：10 左树 = 引擎表体（无表头设计列头隐藏）、右详情/工具条/统计条留外壳、行选中联动右详情；11 七列引擎表头 + 拖宽/右键隐藏/偏好持久化落地（locked 列右键 = 必显提示）、行内勾选框三态经分片 :checked/:indeterminate 声明式（原 render 后补挂面收进分片）、批量条留外壳；树聚合/筛选/折叠/勾选判据全留变体 rowsFn；排序不适用（树序 = 树语义，Q3 不增项）。守阵两处同轮改锚：roving 守阵 10/11 段改钉（data-node → 桥三件 + 12 不变）；P3-6 折叠守阵 path_attr 改 data-act="fold"+data-path；skins ⑧⑨⑪ 扩至八描述符/八分片/八变体。e2e：dt11-sticky 探针改引擎口径双皮肤全过（吸顶补偿 CSS 个性不变）；新增 content 变体 spec（10 折叠/筛选/选中联动/行级键盘真机红验、11 勾选/子树三态/批量条/徽章循环 POST 载荷断言/拖宽落盘/locked 右键/刷新回放/omitEmpty 整列省略）。红验两条闭环（anchTouch 空操作 → 10 折叠/11 勾选即红；dtRowAfter 空操作 → roving 锚点缺失即红；还原即绿）。途中两处自检修正：e2e 断言撞 locked 必显文案子串（改钉隐藏动作项不存在）与 Esc 全局关抽屉快捷键（收层改点空白）。
- **2026-10-12 1036（收口）**：计划 §11 U4 变更行（Q1–Q5 终态对账 18/18，U5 停手点成立：非表变体一行未动、树数据契约零改动）+ 本档案 + activeContext 切片 + 基线切片。
- **2026-10-12 1800 前（U5 收口实施 + 红验 + 全量三道闸）**：① 定型守阵 `test_drawer_tpl_variant_interaction_single_point`（skins 文件新增独立测试函数 + 头注测试计划同步）——声明即受检（全目录零 ui.sort；tableId+rowsFn 双声明桥变体零表格容器列宽 grid，⑪ 同口径选择器族），已知八变体清单兜底防判据缩水；红验两条闭环（07 注入 ui.sort → 红 / 11 注入 .dt11-r 列宽 grid → 红，git checkout 还原 → 绿，探针未进仓库）。② 债务入账：模块文档「变体表格 8 份手搓」→「已清偿 + 新判据」；1722 档案 P6 已交付 → Done 闭环（Status → Done，P0–P6 全阶段完成）；2106 档案回引本计划（目标函数修正由 0527 承接收口 + Refs 补链）。③ 全量三道闸：test.full 首轮 3 failed = 1722 档案 Status 改动引发的 _index.md 生成物漂移（kb.index 重建后转绿，非代码问题）；终值 **3145 passed + 4 skipped**（U4 3144 → +1 = 定型守阵）；dev.e2e **196 passed + 0 failed + 10 skipped**（206 用例 359s，与 U4 基线逐位一致 = 本波零代码改动面的直接证据）。
- **2026-10-12 1800（收口）**：计划 §11 U5 变更行 + 计划 Status → Done（U0–U5 全部完结）+ 本档案（Status → Done + Summary + 子任务表 + 本条目）+ activeContext 切片 + 基线切片 26-10-12-1800（Q1–Q5 终态表定格）。
