# 3127 —— WEBUI 表格公共组件 P5(HR 表借壳 thead 模式 + HR 表注册表)

> 摘要: 计划 `26-10-11-1722-plan-webui-table-component` 的 **P5**(设置页 HR 表接入, 用户拍板「复用表壳 · th 模式」)—— `<aq-table>` 加 **thead 模式**(同一表壳的第二根 = 原生 `<table>` 表头行), HR 详情表(表①)表头借壳渲染; HR 三张表列定义单点进 `hr_status.js` 的 `HR_TABLE_DEFS`(hrDetail/hrWave/hrKv, 与 `TABLE_DEFS` 同形但独立 —— 不进 `TABLE_PAGES`, 否则列选择器多出分组); 波次表(表②)表头改由注册表 `v-for` 摆列; 排序仍走 `hrsSetSort` 三态(D3=B), 死件 `hrsArrowHref` 随箭头解析并入表壳退役。关键机制: 根模板是 in-DOM 的, 自定义元素直接放 `<thead>` 会被浏览器 foster-parent 移出表格 ⇒ 占位写成 `<tr is="vue:aq-table" mode="thead">`(`vue:` 前缀让编译器把 `<tr>` 当组件)。守阵同轮改版(shell 单点守阵增 ④thead 分支与占位形态 / HR 排序守阵表头接线改扫组件 + 注册表十列键 / diag 守阵增 `hrsWaveCols` / 保留前缀守阵白名单并入 `$emit`, 红绿双验过)。验收: 真浏览器 A/B 表头 DOM **逐字节等价**(表① `outerHTML` 与子节点骨架、表② `outerHTML` 与 HEAD 相同)+ e2e 与上片基线一致 + 覆盖率四项与上片逐位相同。
> 基线时间: 2026-10-11 20:15

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `1733803f`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3127 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16503 语句 / 148 未覆盖 / 5620 分支 / 133 partial; 门槛 98% 达标; 本轮 59.5s / 59.7s 两次采样)
- 四项覆盖率指标(语句/未覆盖/分支/partial)与上片记录**逐位相同** —— 本轮改的是前端静态资产 + 既有守阵, `src/` 零新增代码路径。
- **用例数核对**: 本轮零新增用例(只改 4 条既有守阵), 复核 HEAD(不含本轮改动)`--collect-only` 收集 3131 = 3127 passed + 4 skipped, 与本轮**完全一致** —— 上片切片记录的 3126 与本片的 3127 差 1 来自上片记录时点(其「会话开工 sync 到 `4734c001`」时点不含 `bab4b1de` 的用例面), 不是本轮引入; 以本片为最新事实源。
- 增量明细: `src/auto_qb/webui/static/shared/table.js`(mode prop + emits 声明) · `shared/tpl/xtpl.html`(`#tpl-aq-table` 增 thead 分支, grid 分支一字未动) · `shared/hr_status.js`(模块级 `HR_TABLE_DEFS` + `hrsWaveCols()` + 删 `hrsArrowHref`; 636→~700 行) · `shared/tpl/settings-detail.html`(表① 表头借壳 + 表② 表头注册表 v-for; 539→543 行, 硬顶 560) · `tests/test_webui_static_skins.py`(两条守阵改版) · `tests/test_webui_static_dom_page.py`(两条守阵改版)。文档面: 计划 §09 变更记录 + 任务档案 + 本切片 + activeContext 切片 + `modules/webui-static-contract.md`(表格公共组件条补 thead 模式 / 新增 HR 表接入条)。
- 机检: 受影响守阵面(`test_webui_static_skins.py` + `test_webui_static_dom_page.py` + `test_web_hr.py`)98 passed / 1 skipped; 全量见上。
- 真浏览器 A/B(一次性探针, 不入仓库): 读盘上**两侧真实** `settings-detail.html` 锚段里的 `<thead>`, 走真 in-DOM 路径(`page.setContent` → 浏览器解析 → `mount("#app")` 用 innerHTML 编译)+ 真 `table.js`/`hr_status.js` 渲染 —— 表① 表头 `outerHTML` 与子节点骨架、表② 表头 `outerHTML` 三项与 HEAD **逐字节相同**; 排序交互(首击降 → 箭头 on 只落命中列 → 第三击回默认)两侧行为一致。**已知偏差(记录在案)**: 表② 表头改 v-for 后, Vue v-for 片段会在 `<tr>` 里插 **18 个零长文本锚点**(每项 2 + 片段首尾 2)—— `outerHTML` 序列化不含、CSS 表格修正对 whitespace-only 文本不参与布局, 视觉/行为零影响; 属 v-for 实现不变量, 若要绝对零差异只能放弃注册表化。探针已删。

## e2e 实测

- `commands run dev.e2e` 全量: **158 passed / 0 failed / 10 skipped**(4.1m)—— 与上片基线**逐位一致**。
- 过程记录(保留作抖动佐证): 本轮首次全量轮曾出 **157 passed / 1 failed / 10 skipped**(4.0m), 失败 = `delta-sync.spec.mjs:170`(prism)「lastRid 置空后下一轮为全量」8s 轮询超时 —— **与既有 issue `26-10-11-1825-test-delta-sync-full-round-flake` 同签名**(该 issue 18:25 入池, 早于本轮; 其证据里同样是 157/1/10)。隔离重跑该 spec: B 侧 3 次 + A(HEAD)侧 3 次**均 8/8 绿** ⇒ 判定为该已知抖动复发, 非本轮引入(该 spec 与本轮改动面 HR 表头无交集); 复跑全量即 158/0/10。

## 风险 / 观察

- 表② 表头的 v-for 零长文本锚点是本轮唯一偏离「DOM 逐字节等价」硬闸的点 —— 已在计划 §09 与任务档案记录; 后续若有人按骨架比对表② 表头, 见本条不要误判为回归。
- 顺带发现(不在本轮修): `test_frontend_template_no_reserved_prefix_identifiers` 的**指令表达式分支是死的**(正则捕获组 1 是引号, 守阵却读它当表达式)—— `@click="_x()"` 这类指令形态实际从未被检出; 已写进任务档案, 待用户定夺是否入池/修复。
