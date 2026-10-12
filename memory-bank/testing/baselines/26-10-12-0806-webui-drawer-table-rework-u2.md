# 3132 —— WEBUI 抽屉表格统一重写 U2(26-10-12-0527 计划, 用户表三变体 07/08/09 接引擎)

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/testing/baselines/26-10-12-0641-webui-drawer-table-rework-u1.md

> 摘要: U2 用户表三变体表格体重写接引擎。判据: ① `test.full` **3132 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`(U1 3132 → 持平: 守阵改版净零——bridge_wiring 扩 U2 十二段 / a11y 守阵随 D3 改版重排, 用例总数不变); ② 全量 e2e **184 passed + 0 failed + 10 skipped**(U1 176 → +8 = 新增 drawer-peers-variant-tables 双皮肤); ③ anchTouch 红验闭环(空操作注入 + peers 端点挂起冻结 → 07/09 × 双皮肤注入即红, 还原即绿)。
> 基线时间: 2026-10-12 08:06

计划：memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html（§09 26-10-12-0802 条）
上一基线：memory-bank/testing/baselines/26-10-12-0641-webui-drawer-table-rework-u1.md

## 本波改动面

- **引擎侧**（shared/）: drawer_templates.js（dtSyncAnchors 锚对账单点收口 _dtRender 尾部 / H.anchFill 锚保活 / H.anchTouch 触碰 / register 收 rowsFn / 桥方法扩 dtBridgeSegs·dtBridgeRowCls·dtTplRows）；xtpl.html 桥模板分段化（segs 逐段 teleport）；columns.js（通用 omitEmpty 单点 _colsOmitEmpty + 三变体六 computed）；app.js（DRAWER_PEER_V07/08/09 列集 D2 裁剪 / DRAWER_TABLE_DEFS 三行 / 三渲染器组件注册）；table.js 三渲染器定义；xtpl-cells.html 三分片（压至 399 行守单分片上限）。
- **变体侧**（drawer_tpl/07|08|09）: 全量重写——外壳只留版式（卡片/分组头/chips/折叠），删三套手搓排序状态机与列宽 grid；rowsFn 行装配（显示值 + _raw + _cls）；吸顶个性 .dtNN-list .group-head sticky -14px 反压制皮肤 static。
- **测试侧**: 守阵 test_drawer_table_bridge_wiring 扩 U2 十二段；a11y 守阵随 D3 改版（手搓表头 aria-sort pin 退役，07/09 chips 原生 button 口径）；e2e drawer-peers-columns / drawer-peers-sticky-flush 探针改引擎口径；新增 e2e/drawer-peers-variant-tables.spec.mjs（07 手势三件套 + 默认序/引擎排序、07/09 chips 轮询冻结口径、08 分段/折叠/只看在传/组内 dyn 排序）。
- **命令配置**: .commands/dev/config.toml dev.e2e timeout 360→600（套件 176→194 用例后默认轮实测 ~356s 顶满旧预算被引擎强杀）。
- **计划外入池**: 引擎 aq-table 表头 role/aria-sort/键盘可达缺口（issues/26-10-12-0800-bug-webui-table-head-a11y.html，Open 未认领）。

## 验收数字

- `test.full`: **3132 passed + 4 skipped** / 覆盖率 `TOTAL 16517 151 5626 134 99%`（与 U1 基线持平——守阵改版为同轮重排净零，无新增 py 用例）。
- 全量 e2e（dev.e2e，194 用例）: **184 passed + 0 failed + 10 skipped**，实测 339s（600s 预算内；U1 基线 176 → +8，全部来自新增 drawer-peers-variant-tables 双皮肤八例）。运行注记：首轮曾遇桩服务中途 CONNECTION_REFUSED 的环境事故（失败全部为连接拒绝、零断言失败），清 8137 残留重跑即全绿。
- 红验一条（anchTouch）：`H.anchTouch` 注入空操作 → chips 用例假绿（行靠 5s 轮询 tick 重读兜底）→ 手法修正为「初始落袋后 peers 端点挂起冻结」→ 07/09 × 双皮肤注入即红 → 还原即绿。
- Q1–Q5 对账第一步（13/18）：抽屉 18 个手搓表格表面中 stub + 07/08/09 已统一到引擎，余 04/05/06（U3）、10/11（U4）待收。

## 已知偏差

- 引擎表头 a11y（role/tabindex/aria-sort）全域缺口未修，属计划外，已入 issue 池待拍板（见上）。
- dev.e2e 全量 5.6 分钟超出旧 360s 引擎预算的根因已记进任务配置 note（套件扩容，非回归变慢）。
