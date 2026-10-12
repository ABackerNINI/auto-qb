# 抽屉表格统一重写 · U2 用户表三变体落地（07/08/09 接引擎）

> 摘要: 计划 26-10-12-0527 U2 完成：07/08/09 三变体表格体重写接引擎——引擎侧锚保活三件套（dtSyncAnchors 单点对账 / H.anchFill 外壳重建保锚 / H.anchTouch 态翻动强制换代）+ segs 分段桥（08 五分组）+ columns.js 通用 omitEmpty 渐进列；变体外壳只留版式，行装配收进 rowsFn、渲染器分片零判据复制、行级个性经 rowCls 绑引擎行容器（D5）。守阵 bridge_wiring 扩 U2 十二段全绿；a11y 守阵随 D3 改版（引擎表头 role/aria-sort 缺口入 issue 池）；e2e 两 spec 探针改引擎口径 + 新增 drawer-peers-variant-tables（手势三件套/排序/chips/分段/折叠/只看在传）；anchTouch 红验闭环（空操作注入 + 轮询冻结 → 注入即红，还原即绿——红验设计要点：必须冻结 5s 轮询 tick，否则行靠 tick 重读假绿）。test.full 与 dev.e2e 全量通过（数字见基线切片）；Q1–Q5 对账第一步（13/18）。停手点成立：04/05/06/10/11 未动，**下一步 U3（tracker 04/05/06）**。dev.e2e 引擎超时随套件涨到 194 用例放宽 360s→600s。

> 最后活动: 2026-10-12 08:02

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/issues/26-10-12-0800-bug-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-12-0806-webui-drawer-table-rework-u2.md

## 遗留债务(需另开会话)

- **cap 债务**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W7 各一条)；清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**: `kb.check` 报「切片数 > 70」(每波新增切片加深)。
- 引擎表头 a11y 缺口(26-10-12-0800 issue, Open)：属计划外，未认领不修。
