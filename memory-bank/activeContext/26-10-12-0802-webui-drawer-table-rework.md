# 抽屉表格统一重写 · U4 内容树两变体落地（10/11 接引擎，Q1–Q5 终态 18/18）

> 摘要: 计划 26-10-12-0527 U4 完成：10/11 两变体表格体重写接引擎——D4=A 树缩进格进渲染器（折叠钮/勾选框/缩进/图标/名称在格内，判据全留变体 rowsFn）；桥模板 U4 扩展三件 = 行容器 data-dt-key 身份锚（rowKey 值单点输出）+ rowTab 声明的行容器 tabindex=-1 + .group-table @vue:mounted → rowAfter → 变体 rowAfterFn（锚换代重挂恰好一次跑 roving 锚点/回焦）——行级键盘 a11y 面（issue 26-10-07-0846）在引擎行容器上的等价落地；10 无表头设计列头 CSS 隐藏（拖宽/右键不适用记档），右详情/工具条/统计条留外壳、行选中联动右详情；11 七列引擎表头 + 拖宽/右键隐藏/偏好持久化落地（locked 勾选/折叠列 = 必显提示不可执行）、行内勾选框三态经分片 :checked/:indeterminate 声明式、批量条留外壳、可用性列 omitEmpty（原 hasav/noav 双 grid 手搓退役）；排序不适用（树序 = 树语义，Q3 不增项）。守阵两处同轮改锚（roving 守阵 10/11 段改钉/P3-6 折叠 path_attr 改形态）；skins ⑧⑨⑪ 扩至八描述符/八分片/八变体；e2e dt11-sticky 探针改引擎口径（吸顶补偿 CSS 个性不变）+ 新增 content 变体 spec（行级键盘真机红验/勾选子树三态/徽章循环 POST 载荷断言/locked 右键/omitEmpty）；红验两条闭环（anchTouch / dtRowAfter 空操作注入即红，还原即绿）。test.full 与 dev.e2e 全量通过（数字见基线切片；总量 +12 为远端并入的流量图波）。**Q1–Q5 终态对账（18/18）**：Q1 引擎消费面 +2 = 18/18 收口，Q3 终态引擎 1 份比较器，Q4 全部表面零手搓列宽 grid。停手点成立：12/13/14/15 等非表变体一行未动、树数据契约零改动，**下一步 U5（收口：守阵定型 + 债务入账 + 终态对账并入基线切片）**。

> 最后活动: 2026-10-12 10:36

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/issues/26-10-12-0800-bug-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-12-1036-webui-drawer-table-rework-u4.md

## 遗留债务(需另开会话)

- **cap 债务**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W7 各一条)；清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**: `kb.check` 报「切片数 > 70」(每波新增切片加深)。
- 引擎表头 a11y 缺口(26-10-12-0800 issue, Open)：属计划外，未认领不修。
