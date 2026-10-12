# 26-10-12-webui-table-head-a11y — 引擎表头 a11y 补课(可排序表头语义与键盘可达, 方案 C)

**Status:** Done
**Added:** 2026-10-12
**Updated:** 2026-10-13 00:09
**Topics:** webui-drawer-table-rework
**Summary:** 认领 issue 26-10-12-0800。「D3 排序并引擎」后旧手搓表头(07/08/09)的 `role="button" + tabindex + aria-sort` 件套随载体退役, 而引擎 `aq-table` 表头**从未具备** —— 抽屉三变体从「局部有」退化为「全域无」, 与主视图各表一起键盘不可达、读屏不知排序态(全域 17 个表头实例)。用户先令「先确定最彻底的方案」→ 定**方案 C**(非 issue 原建议 A/B): 语义载体用 `role="columnheader"`(**不是** button —— `aria-sort` 只对该 role 生效, 挂 button 上读屏直接忽略, 故 A/B 只解决了"键盘可达"一半); 件套收进 `shared/table.js` 的 `headAriaSort`/`headActivate` 两方法单点(grid/thead 共用, 点击与 Enter/Space 同路); grid/thead 两模式 + 三皮肤焦点可见同轮。用户「按推荐实施」= 拍板 P1②(只补表头侧、不做表体值格语义)/P2①(resizer 与列菜单键盘另立)/P3①(thead 同轮)/P4①(逐列 tabindex)。验收见基线切片。
**Refs:** memory-bank/plans/26-10-12-2330-plan-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-13-0009-webui-table-head-a11y.md

## 原始请求

> 用户(2026-10-12 19:25): 「认领 26-10-12-0800-bug-webui-table-head-a11y.html, 先确定最彻底的方案」
> 用户(2026-10-12 23:30): 「按C出计划」
> 用户(2026-10-12 23:33): 「按推荐实施」

## 思考过程与决策

- **为什么不是 issue 建议的 A/B**: 两者都以 `role="button"`(`.h-cell` 加件套)或 `<button>`(整格换载体)承载, 而 WAI-ARIA 规定 `aria-sort` 只对 `role="columnheader"`(或 rowheader)生效 —— 挂 button 上读屏忽略, issue 摘要里「读屏不知排序态」那半个 bug **加完 A 依然存在**; 且列头语义降级为"按钮"。B 另有代价: `.h-cell` 内嵌 `.resizer` + `@mousedown` 拖拽 + `@contextmenu` 右键, 改 button 会与三者冲突, 三皮肤 CSS 与多处 e2e 手势全要重核。→ 语义载体改用 `role="columnheader"`(thead 的 `<th>` 隐含该 role, 零补丁)。
- **件套单点**: grid 与 thead 是同一组件的两根, 若各自手写件套即两份实现(未来新模式再写第三份)。收进组件两方法: `headAriaSort(col)`(与箭头渲染同源, 保证属性与箭头任一时刻一致) + `headActivate(col)`(激活单点)。顺带消掉 grid 原本的内联 `@click="col.sortable && $root.setSort(...)"`。
- **边界(拍板 P1②)**: "彻底"的极限是给表体值格补 `role="row"/"gridcell"` 全套, 但值格散在行渲染器 v-if 链(group 49 / torrent 28 / show-ep / member 28 个分支), 全量加 role 触 100+ 处并破坏历来的"渲染 DOM 逐字节等价"验收口径 —— 收益(读屏报"表格 N 行 M 列")与代价不成比例。**诚实边界**: 缺祖先表格语义时部分读屏对 `aria-sort` 的播报可能不完整, 本轮接受, 另立议题。
- **atlas CSS 落点偏差**: 三皮肤焦点样式本拟各落 `.h-cell.sortable` 所在文件, 但 `atlas/css/components.css` 改动前恰在 700 行单文件 cap(该文件与 `views.css` 首注已写明"顶 cap 时新规则入 views.css"的约定) ⇒ atlas 落 `views.css`。

## 实现计划

- **W0** 冻结基线(零代码): `test.full` + `dev.e2e` 现状数字 + 表头 markup 快照。
- **W1** 语义载体 + 件套单点: `table.js` 两方法; `xtpl.html` grid/thead 两模式接线 + 容器语义; 新增静态守阵 + 同轮改版 `setSort` pin。
- **W2** 焦点可见: 三皮肤 `.h-cell.sortable:focus-visible`。
- **W3** 守阵改版 + 验收闭环: a11y 守阵头注翻向; e2e 键盘用例; `test.full` + e2e; 基线切片; 模块文档/issue/档案回写; `kb.index`。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| W0 | 冻结基线(test.full + e2e + 快照) | Done(test.full 已取; W0 全量 e2e 同因 8137 残留未取到, 后以换端口轮替代) |
| W1 | 两方法 + 两模式接线 + 静态守阵 + 改版 pin | Done |
| W2 | 三皮肤 focus-visible | Done(atlas 落 views.css) |
| W3 | 守阵头注 / e2e 用例 / 全量验证 / 切片 / 文档 / Done | Done |

## 进度日志

- **2026-10-12 19:28** 开工 sync 快进 `94e7ca62→d428d080`; 复验仍复现(grid `.h-cell` 无件套、thead `<th>` 同); issue 置 `In Progress` + 认领链回填(doc-refs ↔ 计划); 方案论证(三方案对比) → 用户裁「按 C 出计划」。
- **2026-10-12 23:30** 立计划 `26-10-12-2330-plan-webui-table-head-a11y.html`(单文件 HTML); 认领链双向闭合(`kb.check` 报「认领链 OK」)。用户「按推荐实施」。
- **2026-10-12 23:33** 开工 sync 快进 `d428d080→cd830692`(远端 9 笔)。W0 跑 `test.full` 见 **2 failed**(`test_traffic_limits.py` 两条), 单文件跑同复现 → 定位为**跨零点 flaky**(循环 `ts+i` 跨天 → `_guard_count` 清零计数), 与本改动无关 → 按范围守恒一行未改, **入池 `26-10-12-2338`**。
- **2026-10-12 23:43** W1/W2 落地: `table.js` 两方法 + `xtpl.html` 两模式接线 + 三皮肤 focus-visible。跑目标守阵先撞 `atlas/css/components.css` 703 行超 cap → 改落 `atlas/css/views.css`(按该文件既有约定) → 53 passed。
- **2026-10-12 23:52** W3: 新增 `e2e/table-head-a11y.spec.mjs`(定向跑 4 passed); `test.full` **3164 passed + 4 skipped**(+1 = 新守阵, 覆盖率持平); 回写模块文档 / 计划 / issue / 本档案。
- **2026-10-13 00:09** e2e: 全量轮(8137)三次尝试 81–98 failed, 失败**全为** `ERR_CONNECTION_REFUSED`/读到陈旧桩(桩服务中途死亡或残留竞争) → 先以**受影响面子集 50 passed / 0 failed** 为验收依据(含 4 条新用例 + 表壳/桥/列偏好/主视图几何守阵); 写基线切片 `26-10-13-0009-webui-table-head-a11y`; `kb.index` + `kb.check`。
- **2026-10-13 00:19** e2e 复跑(**换干净端口 8337**): `E2E_PORT=8337 commands run dev.e2e` = **200 passed + 0 failed + 10 skipped**(5.3m, `EXIT=0`; 含 4 条新用例全绿) —— **8137 根因坐实为端口残留环境问题**(换端口即 0 failed, 与本改动无关)。同轮给 `e2e/harness.mjs` 的 `PORT` 加排障口子 `Number(process.env.E2E_PORT \|\| 8137)`(**默认恒 8137, 端口纪律不变**), 切片 §验收数字已更正为全量轮数字。
