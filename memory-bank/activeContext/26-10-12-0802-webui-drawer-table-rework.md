# 抽屉表格统一重写 · U3 Tracker 三变体落地（04/05/06 接引擎）

> 摘要: 计划 26-10-12-0527 U3 完成：04/05/06 三变体表格体重写接引擎——04 状态卡（单列满宽行 + 引擎行容器覆盖双列 grid、虚拟合并卡 = rowsFn 合成行、手搓分段排序退役并经 `dtSortSet` 直设口并引擎——「模式选择」语义与 h-cell 三态循环冲突的引擎特例，Q3 记档）；05 健康度分组（分组头留外壳 + 单列满宽行分段桥，行三形态，折叠/msg 展开只翻 class 不触碰锚）；06 增强表格（八列引擎表头，「下次重新汇报」不可排——三态混合口径无单一原值；onlyBad 外壳容器类切换行不重装配）。渲染分片另立 xtpl-cells-dt.html（xtpl-cells.html 顶死 400 行单分片上限）+ 三清单挂载。守阵四处计数锚同轮改锚不放宽（reannounce 闸门④ 判据留变体/呈现锚迁分片——reannounce spec 探针零改版全过）；e2e 新增 tracker 变体 spec × 双皮肤，红验两条闭环（dtSortSet / anchTouch 空操作注入即红，还原即绿）。test.full 与 dev.e2e 全量通过（数字见基线切片）；Q1–Q5 对账第二步（16/18），Q3 手搓清零记档三条。停手点成立：10/11 未动、树数据契约零改动，**下一步 U4（内容树 10/11）**。

> 最后活动: 2026-10-12 09:13

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/issues/26-10-12-0800-bug-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-12-0913-webui-drawer-table-rework-u3.md

## 遗留债务(需另开会话)

- **cap 债务**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W7 各一条)；清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**: `kb.check` 报「切片数 > 70」(每波新增切片加深)。
- 引擎表头 a11y 缺口(26-10-12-0800 issue, Open)：属计划外，未认领不修。
