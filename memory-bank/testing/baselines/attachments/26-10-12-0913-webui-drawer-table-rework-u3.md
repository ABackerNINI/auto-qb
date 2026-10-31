# 3132 —— WEBUI 抽屉表格统一重写 U3(26-10-12-0527 计划, Tracker 三变体 04/05/06 接引擎)

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/testing/baselines/26-10-12-0806-webui-drawer-table-rework-u2.md

> 摘要: U3 Tracker 三变体表格体重写接引擎。判据: ① `test.full` **3132 passed + 4 skipped**(U2 持平: dom_panel 四守阵改锚 + skins 扩容重排, py 用例总数不变); ② 全量 e2e **190 passed + 0 failed + 10 skipped**(U2 184 → +6 = 新增 drawer-trackers-variant-tables 双皮肤三例), 实测 322s; ③ reannounce spec 探针在分片中存活**零改版全过**(R4 不删只改锚的最优解); ④ 红验两条闭环(dtSortSet 空操作注入 → 分段 active 失效即红; anchTouch 空操作注入 + 04 轮询冻结 → 行数失效即红, 还原即绿); ⑤ Q1–Q5 对账第二步(16/18), Q3 手搓清零记档三条。
> 基线时间: 2026-10-12 09:13

计划：memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html（§11 26-10-12-0913 条）
上一基线：memory-bank/testing/baselines/26-10-12-0806-webui-drawer-table-rework-u2.md

## 本波改动面

- **引擎侧**（shared/）: app.js（04/05 单列满宽 card 列集 + 06 八列列集，next 列 sortable:false——行级 next_announce/种子级回退/正在汇报三态混合口径无单一原值；DRAWER_TABLE_DEFS 三描述符：04 排序 defKey sev / 05 segs:true 空排序键保原序 / 06 sev 升序异常置顶；三渲染器组件注册）；sort.js 新增 `dtSortSet(tableId, key, dir)` 直设口（04 分段钮「模式选择」语义与引擎 h-cell 三态循环冲突的引擎特例，Q3 记档，排序态仍归 dtSortState 单点）；columns.js 六 computed；table.js 三渲染器定义；**新建 tpl/xtpl-cells-dt.html 三分片**（xtpl-cells.html 已 399 行顶死单分片 400 行上限）+ 三份 index.html 清单挂载。
- **变体侧**（drawer_tpl/04|05|06）: 全量重写——04 卡片栅格覆盖引擎行容器为双列 grid（等高 stretch 守阵口径）、虚拟合并卡 = rowsFn 合成行、手搓分段排序退役并 dtSortSet；05 异构分组 = 分组头留外壳（分组是版式）+ 单列满宽行桥，行三形态（fail 处置块 / row / chips 合成行），折叠与 msg 展开只翻 class 不触碰锚（行来源不变 → 无 anchTouch 正当化）；06 八列引擎表头（tier/sev 可排、下次重新汇报不可排）+ onlyBad 外壳容器类切换（行不重装配原口径）。
- **测试侧**: dom_panel 四守阵同轮改锚不放宽（reannounce 闸门④ 判据留变体/呈现锚迁分片、等高 grid+stretch、per_tracker 分片切片、a11y msg 件套迁分片钉）；skins ⑧⑨⑪ 扩容（六描述符/六分片 dt06 逐列 key 配对/六变体参数化 anchTouch 标志）；新增 e2e/drawer-trackers-variant-tables.spec.mjs（04 分段排序并引擎 + pills + 虚拟卡、05 五组锚/tier 升序/折叠/msg、06 引擎排序三态/拖宽/右键隐藏落盘回放/仅看异常）× 双皮肤。

## 验收数字

- `test.full`: **3132 passed + 4 skipped**（与 U2 基线持平——守阵改版为同轮改锚净零，无新增 py 用例）。
- 全量 e2e（dev.e2e，200 用例）: **190 passed + 0 failed + 10 skipped**，实测 322s（600s 预算内；U2 184 → +6，全部来自新增 drawer-trackers-variant-tables 双皮肤三例）。本轮无桩服务环境事故。
- reannounce spec（drawer-trackers-reannounce）: 探针 `.dt06-next b` / `.dt06-gb` 在渲染分片中存活，**零改版**双皮肤全过。
- 红验两条: ① `dtSortSet` 注入空操作 → dt04 × 双皮肤分段钮 active 态断言即红；② `anchTouch` 注入空操作 → dt04 × 双皮肤（pills 冻结轮询口径）行数断言即红；还原即绿。

## 已知偏差

- Q3 记档三条（手搓清零记档）: 04 分段钮排序为引擎 `dtSortSet` 特例（模式选择非 h-cell 三态循环）；04/05 拖宽/右键隐藏不适用（非缺能力，无列可拖——单列满宽行）；06「下次重新汇报」列不可排（三态混合口径无单一原值）。
- Q1–Q5 对账第二步（16/18）: 18 个手搓表格表面中 stub + 07/08/09 + 04/05/06 已统一到引擎，余 10/11（U4）待收；U4 停手点成立：10/11 未动、树数据契约零改动。
