# 26-10-12-webui-drawer-table-rework — WEBUI 抽屉表格统一重写（U0–U5）

**Status:** In Progress
**Added:** 2026-10-12
**Updated:** 2026-10-12
**Summary:** 依据双计划联合审计（26-10-12-0455）修正计划的执行档案：U0 冻结 + 1722 P6 契约交付；U1 引擎 spike（列子集声明 / 排序 per-table-id 泛化 / Teleport 锚桥，stub 四路径 e2e 闸门通过）；U2 用户表三变体（07/08/09）表格体重写接引擎（锚保活/对账/触碰三件套 + 分段桥 + omitEmpty 渐进列，e2e 手势红绿双验）。U3（tracker 04/05/06）待开工。
**Topics:** webui-drawer-table-rework
**Refs:** memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/reports/26-10-12-0455-report-webui-drawer-table-unification-audit.html,memory-bank/issues/26-10-12-0800-bug-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-12-0806-webui-drawer-table-rework-u2.md

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
| U3 tracker 04/05/06 表格体重写 | Open | 下波；reannounce 闸门等专属守阵逐条对账 |
| U4 内容树 10/11 表格体重写 | Open | D4 树缩进格单份渲染器 |
| U5 收口：Q1–Q5 终态 + 守阵定型 + 债务入账 | Open | 18/18 对账 + 红验两条 |

## 进度日志

- **2026-10-12 0746 前（U2 实施 + 守阵 + e2e）**：引擎侧 drawer_templates.js（dtSyncAnchors 单点对账 / anchFill 保活 / anchTouch 触碰 / register 收 rowsFn / 桥方法六件扩 Segs/RowCls/dtTplRows）、xtpl.html 分段桥模板、columns.js（omitEmpty 单点 + 三变体六 computed）、app.js（三列集 D2 裁剪 / DRAWER_TABLE_DEFS 三行 / 三组件注册）、table.js 三渲染器、xtpl-cells.html 三分片（压至 399 行守单分片上限）、三变体全量重写。守阵 `test_drawer_table_bridge_wiring` 扩 U2 十二段；修掉三个自检发现项（blk 提取在内层 `},` 截断、08 注释 data-sort 字面自撞、09 漏 `const R`）。a11y 守阵 `test_drawer_tpl_a11y_and_fetch_error_states` 随 D3 改版：07/08/09 手搓排序表头 aria-sort pin 退役（排序归引擎），07/09 chips 原生 button 口径、08 折叠组 P3-4 件套保留；引擎表头 role/aria-sort 缺口属引擎全域议题，入 issue 池。
- **2026-10-12 0750（e2e）**：`drawer-peers-columns.spec` / `drawer-peers-sticky-flush.spec` 探针改引擎口径（`.group-head[data-table=drawerPeerV0X]` / `.group-row` / 分段锚），双皮肤全过；新增 `drawer-peers-variant-tables.spec`（07 手势三件套 + 默认序/引擎排序、07/09 chips、08 分段/折叠/只看在传/组内 dyn 排序），双皮肤全过。**红验闭环**：anchTouch 注入空操作 → chips 测试假绿（行靠 5s 轮询 tick 延迟刷新兜底）→ 手法修正为「初始落袋后 peers 端点挂起冻结」→ 07/09 × 双皮肤注入即红，还原即绿。全量 e2e 首轮失败全部为桩服务中途 CONNECTION_REFUSED（零断言失败，环境事故），清 8137 残留重跑通过。数字见基线切片（`commands run kb.baseline`）。
- **2026-10-12 0800（收口）**：计划 §09 U2 变更行 + 本档案 + activeContext 切片 + 基线切片；引擎表头 a11y 缺口入 issue 池（计划外，不属本波修码面）。
