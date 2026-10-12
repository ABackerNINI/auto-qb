# 3164 —— 引擎表头 a11y 补课(可排序表头语义与键盘可达, 方案 C)

**Refs:** memory-bank/tasks/26-10-12-webui-table-head-a11y.md

> 摘要: issue 26-10-12-0800。「D3 排序并引擎」后旧手搓表头的 P3-4 件套随载体退役, 而引擎 `aq-table` 表头**从未具备** —— 全域(主视图 5 · 抽屉经典 3 · 桥变体 8 · HR thead 1 = 17 个表头实例)键盘不可达、读屏不知排序态。方案 C: 语义载体用 `role="columnheader"`(**不是** button —— `aria-sort` 只对该 role 生效, 挂 button 上读屏忽略, 那正是 issue 里"读屏不知排序态"半个 bug 的修法); 件套收进 `shared/table.js` 的 `AQ_TABLE_COMPONENT.headAriaSort`/`headActivate` 两方法单点; grid / thead 两模式同轮; 点击与 Enter/Space 同走 `headActivate`。
> 基线时间: 2026-10-13 00:09

上一基线: memory-bank/testing/baselines/26-10-12-2236-webui-drawer-tpl-flicker-fix3.md

## 本波改动面

- `src/auto_qb/webui/static/shared/table.js`: `AQ_TABLE_COMPONENT` 新增 `methods.headAriaSort(col)`(命中列 `sortKey === col.key` 出 `ascending`/`descending`, 与箭头 `v-if` 判据同源)与 `methods.headActivate(col)`(grid → `$root.setSort(col.key, this.tableId)`; thead → `$emit("sort", col.key)`)。
- `src/auto_qb/webui/static/shared/tpl/xtpl.html`(`#tpl-aq-table`): grid 分支 `.h-cell` 加 `role="columnheader"` + `:aria-sort` + `:tabindex="col.sortable ? 0 : null"`, `@click` 由内联 `$root.setSort` 改走 `headActivate` 并加 `@keydown.enter/space.prevent`; `.group-head` 加 `role="row"`、`.col-drop-line` 加 `role="presentation"`; thead 分支 `<th>` 加 `:aria-sort` / `:tabindex` / `@keydown` 与 `@click` → `headActivate`。
- 三皮肤焦点可见(`.h-cell.sortable:focus-visible`, `outline-offset: -2px`): `console/css/components.css`、`prism/css/views.css`、`atlas/css/views.css`(**atlas 落 views.css 而非 components.css —— 后者改动前恰在 700 行单文件 cap**, views.css 首注即此约定)。
- `tests/test_webui_static_skins.py`: 新增 `test_frontend_table_head_a11y`(静态守阵, 钉件套单点 + 两模式 markup + 三皮肤焦点样式); `test_frontend_table_registry_single_point` 的 `setSort` pin 由「模板含字面串」改为「模板走 `headActivate` + 组件内 `setSort(col.key, this.tableId)`」; 文件头「## 测试计划」补 1 行。
- `tests/test_webui_static_dom_panel.py`: `test_drawer_tpl_a11y_and_fetch_error_states` 头注「引擎级表头 a11y 补课…已入 issue 池另议」→「已补, 件套在表壳」。
- `e2e/table-head-a11y.spec.mjs`: 新增 4 用例(×2 皮肤) —— 主视图与抽屉经典表: 列头 `columnheader`、可排序列才进 Tab 序、Enter → `aria-sort=descending` 且箭头点亮、Space → `ascending`。
- `e2e/harness.mjs`: `PORT` 由常量 `8137` 改为 `Number(process.env.E2E_PORT || 8137)`(排障口子, 默认不变; 因 8137 残留致全量轮飘忽, 需换干净端口复跑)。
- 知识库: `modules/webui-static-contract.md` 补「引擎表头 a11y 件套」条; issue 26-10-12-0800 置 `Done`; 计划 26-10-12-2330 置 `Done` + 变更记录; 本切片; 任务档案。

## 验收数字

- `test.full`: **3164 passed + 4 skipped**(+1 = 新增静态守阵; 改动前 3163) / 56.27s / 覆盖率 `TOTAL 16718 165 5688 141 99%`(与改动前逐位相同 —— 改动面为 JS/CSS/HTML, 不进 Python 覆盖率)。
  - **2 failed 与本改动无关**: `tests/test_traffic_limits.py::test_recorder_patological_flip_guard` / `test_recorder_warn_first_fire_on_fresh_boot` —— 根因是**跨零点 flaky**(用例循环 `ts + i` 跨本地零点, `SpeedLimitRecorder._guard_count` 见日期变化把 `_day_events` 清零, 2000 阈值永不达), 改动前(W0 23:35)与改动后(23:50)同样红, 单文件跑亦复现。按范围守恒**一行未改**, 已入池 `26-10-12-2338-test-traffic-limits-guard-midnight-flaky`。
  - **证实**: 过零点后 `commands run test.quick`(00:1x, 同一份工作区)**3166 passed + 4 skipped + 0 failed** —— 上述 2 条自然转绿, 且 3166 = 3164 + 那 2 条, 与该 flaky 诊断逐位吻合。
- 真浏览器 e2e(**全量轮**, 换干净端口复跑): `E2E_PORT=8337 commands run dev.e2e` → **200 passed + 0 failed + 10 skipped**(5.3m, `EXIT=0`) —— 含 4 条新用例(prism/atlas × 主视图/抽屉)全绿; 桩全程单实例存活, 收尾后 8337 无 LISTENING 残留。skipped 10 = 非默认模式门控项(`W5 off` 6 / `P0-3 hang` 2 / 行窗口化 2), 与改动前一致。
  - **8137 根因坐实(环境, 非本改动)**: 此前三次全量轮 81–98 failed, 失败**全部**为 `ERR_CONNECTION_REFUSED`/读到陈旧桩(桩服务 8137 中途死亡或残留竞争); 换一个干净端口即 **0 failed**, 直接证明与本改动无关。
  - **排障口子(本波新增)**: `e2e/harness.mjs` 的 `PORT` 改为 `Number(process.env.E2E_PORT || 8137)` —— 默认**恒 8137**(端口纪律不变: 撞残留宁可失败), 仅排障时用 `E2E_PORT=<n>` 换干净端口复跑; `global-teardown` 读同一个 `PORT`, 收尾兜底自动跟随。无守阵 pin 端口字面(仅注释提及), 改动面安全。
- 真浏览器 e2e(**受影响面子集**, `commands run dev.e2e -- e2e/table-head-a11y.spec.mjs e2e/drawer-tables.spec.mjs e2e/drawer-bridge-stub.spec.mjs e2e/column-prefs.spec.mjs e2e/views.spec.mjs`): **50 passed + 0 failed**(1.7m) —— 含 4 条新用例 + 表壳(抽屉三表)/桥变体/列偏好/主视图几何守阵(右对齐列表头 ±1px)全绿。
- 注: 测试增删 = 静态 +1(`test_frontend_table_head_a11y`) / e2e +4(`table-head-a11y.spec.mjs`); 全量 e2e 用例数 206 → 210。
- 注: W0(改动前)冻结数字: `test.full` **3163 passed + 4 skipped**(2 failed 同为上述 flaky); W0 全量 e2e 同因 8137 残留失败(未取到有效基线)。真实差异 = +1 passed(新守阵)。
