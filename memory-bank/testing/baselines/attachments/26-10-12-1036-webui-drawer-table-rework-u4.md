# 3144 —— WEBUI 抽屉表格统一重写 U4(26-10-12-0527 计划, 内容树两变体 10/11 接引擎, Q1–Q5 终态 18/18)

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/testing/baselines/26-10-12-0913-webui-drawer-table-rework-u3.md

> 摘要: U4 内容树两变体表格体重写接引擎(D4=A 树缩进格进渲染器)。判据: ① `test.full` **3144 passed + 4 skipped** / `TOTAL 16708 161 5688 140 99%`(U3 基线 3132 → +12 = 远端并入的流量图 W1–W3 波测试, 本波守阵改锚净零——roving/P3-6 两守阵同轮改锚 + skins ⑧⑨⑪ 扩八变体, 无新增 py 用例); ② 全量 e2e **196 passed + 0 failed + 10 skipped**(U3 190 → +6 = 新增 drawer-content-variant-tables 双皮肤三例), 实测 342s; ③ dt11-sticky 吸顶贴边 spec 探针改引擎口径全过(吸顶补偿 CSS 个性不变); ④ 红验两条闭环(anchTouch 空操作 → 10 折叠/11 勾选即红; dtRowAfter 空操作 → roving 锚点缺失即红, ×双皮肤, 还原即绿); ⑤ **Q1–Q5 终态对账(18/18)**。
> 基线时间: 2026-10-12 10:36

计划：memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html（§11 26-10-12-1036 条）
上一基线：memory-bank/testing/baselines/26-10-12-0913-webui-drawer-table-rework-u3.md

## 本波改动面

- **引擎侧**（shared/）: app.js（10 五列/11 七列列集——11 含 omitEmpty 可用性列与 locked 勾选/折叠列；两描述符 rowTab/rowAfter 声明位；两渲染器组件注册）；columns.js 四 computed；**桥模板 U4 扩展三件**（tpl/xtpl.html）：行容器 `data-dt-key` 身份锚（rowKey 值单点输出）+ rowTab 声明的行容器 tabindex=-1 + `.group-table @vue:mounted` → `dtRowAfter` → 变体 rowAfterFn（锚换代重挂恰好一次，roving 锚点/回焦在行进 DOM 后跑——行级键盘 a11y 面 issue 26-10-07-0846 在引擎行容器上的等价落地）；drawer_templates.js（register 收 rowAfterFn + dtBridgeRowTab/dtRowAfter 两根方法）；xtpl-cells-dt.html 追加 dt10/dt11 两分片（同文件 214 行 < 400 上限，零新增清单行）。
- **变体侧**（drawer_tpl/10|11）: 全量重写——10 左树 = 引擎表体（无表头设计 → 列头 CSS 隐藏，05 先例；拖宽/右键隐藏不适用记档），右详情/工具条/统计条留外壳，行选中（selPath）联动右详情 + 行 _cls；11 七列引擎表头 + 拖宽/右键隐藏/偏好持久化落地（locked 列右键 = 必显提示不可执行），行内勾选框三态经分片 `:checked/:indeterminate` 声明式（原生 property，原 render 后补挂面收进分片），批量优先级条留外壳；树聚合/筛选/折叠/勾选判据全留变体 rowsFn（判据零复制）；排序不适用（树序 = 树语义，全列 sortable:false + dyn 空键，Q3 不增项）。
- **测试侧**: roving 守阵 10/11 段改锚（data-node 字面退役 → 桥 data-dt-key/rowTab/rowAfterFn 三件钉 + 12 树图块不变）；P3-6 折叠守阵 path_attr 改 `data-act="fold"`+data-path 形态（data-tgl 迁分片）；skins ⑧⑨⑪ 扩八描述符/八分片/八变体（dt11 逐列 key 配对 + 勾选三态声明式钉 + 空态合成行分支钉）；e2e drawer-content-dt11-sticky 探针改引擎口径；新增 e2e/drawer-content-variant-tables.spec.mjs（10 折叠/筛选/选中联动右详情/行级键盘真机红验（ArrowDown 移焦 + Enter 激活）；11 勾选/子树三态 indeterminate/批量条/徽章循环真提交（POST 载荷断言）/拖宽落盘/locked 右键/刷新回放；omitEmpty 整列省略）× 双皮肤。

## 验收数字

- `test.full`: **3144 passed + 4 skipped** / 覆盖率 `TOTAL 16708 161 5688 140 99%`（对 U3 基线 +12 全部来自远端并入的流量图 W1–W3 波测试；本波守阵改锚净零）。
- 全量 e2e（dev.e2e，206 用例）: **196 passed + 0 failed + 10 skipped**，实测 342s（600s 预算内；U3 190 → +6，全部来自新增 drawer-content-variant-tables 双皮肤三例）。本轮无桩服务环境事故。
- 红验两条: ① `H.anchTouch` 注入空操作 → dt10 折叠不收拢 / dt11 勾选不亮即红（×双皮肤，omitEmpty 对照例仍绿 = 红得靶向）；② `dtRowAfter` 注入空操作 → roving 锚点缺失（首行 tabindex≠0）即红（×双皮肤）；还原即绿。
- Q1–Q5 终态对账（**18/18**）: Q1 引擎消费面 +2（10/11）= 18/18 收口；Q3 终态 = 引擎 1 份比较器（dtSortSet 直设特例 + 10/11 无排序记档）；Q4 全部表面零手搓列宽 grid。

## 已知偏差

- 10 无表头设计 → 拖宽/右键隐藏/列偏好不适用（Q3 记档：非缺能力，无列可拖；05 先例同口径）。
- 11 的可用性列 omitEmpty 判据字段为行 av 串（有 availability 才非空）——与原 hasAv 口径逐值等价（av=0 视为有值）。
- e2e 自检修正两处：locked 必显文案子串撞「显示/隐藏列…」菜单项（改钉隐藏动作项不存在）；Esc 是全局关抽屉快捷键（收层改点空白）。
- U5 停手点成立：12/13/14/15 等非表变体一行未动；树数据契约零改动（rowsFn 只读 ctx.drawerFileRows()/drawer.files）。
