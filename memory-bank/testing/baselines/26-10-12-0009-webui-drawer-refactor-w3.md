# 3130 —— WEBUI 抽屉重构 W3 流量页签与形态收敛(26-10-11-2106 计划)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-11-2259-webui-drawer-refactor-w2.md

> 摘要: 计划 `memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html`(专题 `webui-drawer-refactor`)的 **W3** —— seed 五页签(含流量)与 traffic 三挂点(全局 / 分组 / 单种)统一到新面板: 新增 `shared/drawer_head.js` + `tpl/drawer-head.html`(`<aq-drawer-head>` 唯一头部件壳 + `<aq-qb-ctl>` 多根控件组片段), `tpl/drawer.html` 的「两形态各一份头部」byte 级复写收成两行组件调用; 控件组两挂点(traffic 头部 / seed 流量页签 `.qb-statctl`)共用**同一份实现**; `drawer.kind` 形态判据收归 `drawerIsSeed`/`drawerIsTraffic` 两个 computed。**一处与计划文本的有意偏差**: 流量正文留在壳模板、不经组件包装 —— `_qbChartBuild` 经根实例 `$refs` 取挂载点, 子组件模板里的 ref 到不了根实例, 搬进组件图表会静默不画(计划 §05 W3「落地」条与 §11 已登记)。本轮拍板: 用户定「缺陷留到 W5」(`esc-attr-quote-dead-class` 随 W5 退役消失, 不回灌)。W3 的验收口径是**守阵**(计划未给 W3 派 e2e, e2e 归 W4), 故判据 = ① `test.full` = 基线 + 本轮新增守阵用例数, 零失败; ② 全量 e2e 与 W2 基线**逐位一致**(零用例增删, 无锚点漂移); ③ W3 的验收动词(三挂点控件齐全 / 形态判据单点 / `qbCurPending` 语义)各有守阵钉且**逐条红验非退化**。
> 基线时间: 2026-10-12 00:09

## test.full 实测

- 分支: `develop`(工作树含 W2+W3 两轮回写件时实测, 两轮均未提交)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3130 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial)
- **与上基线(`26-10-11-2259-…-w2`)对账**: 3129 → **3130** = 基线 + 本轮新增 1 条守阵用例(`test_webui_static_dom_panel.py::test_frontend_drawer_form_judge_single_point`), **零失败、零跳过变化、覆盖四项数字逐位相同**(语句 / 分母没动 —— W3 不删源码行, 只增守阵)。其余改动全部是既有用例的**同轮改版**(R8 口径不放宽): pin 从旧双 header 结构 / `drawer.kind` 字面量移到新组件与新谓词, 断言只收紧不放松。

## e2e 实测

- 命令: `commands run dev.e2e`(Windows; 桩 `scripts/ui_harness.py` 由 webServer 自动起)
- **实测 (Windows)**: **164 passed + 0 failed + 10 skipped**
- **与上基线对账**: **逐位一致**(W2 基线即 164/0/10) —— 本轮**未加 e2e 用例**(W3 验收按计划口径是守阵), 既有 164 项零失败说明组件化头部与形态判据换算**没有锚点漂移**: 面板开合 / 页签切换 / 流量页签 / 键盘跟随等真手势全部照旧。

## W3 验收动词 × 红验(「按下去到底行不行」的记录)

计划 §05 W3 验收的三件, 逐件钉守阵并做**注入回归红验**(改回错法 → 用例必须红, 注入前四文件备份在仓库内 `tmp-analysis/redcheck-w3/`, 验毕删除):

| 验收件 | 守阵 | 红验注入 | 结果 |
|---|---|---|---|
| 头部复写消除(两形态各一份头部 → 单壳) | `test_drawer_tpl_a11y_and_fetch_error_states`(关闭钮归 head_tpl)+ `test_frontend_qb_traffic_yaxis_and_annotation`(两分支正则)+ `test_web_shortcuts.py::test_drawer_narrow_fullscreen_w4` | **RC1**: 把 traffic 头部拆回内联 `<header class="drawer-head">`(复刻旧复写) | 3 条守阵 rc=1 (红 ✓) |
| `<aq-qb-ctl>` 多根(直接子选择器依赖) | 新增**结构级判根** `_tpl_top_level_tags`(HTML 解析 depth-0 根元素清单) | **RC2**: 给片段包一层 wrapper `<div>` | 结构判根 rc=1 (红 ✓); **同轮类名 count 钉全绿** —— 证明类名计数这类守阵对 wrapper 回潮**失明**, 只有结构判根看得见 |
| 形态判据单点(`drawerIsSeed`/`drawerIsTraffic`) | 新增 `test_frontend_drawer_form_judge_single_point`(钉两谓词**原文** + 各文件出现数 + drawer.html 三形态) | **RC3**: 把 `drawerIsSeed` 谓词的比较翻错 | rc=1 (红 ✓, dom_panel 与 shortcuts 两文件均接住) |
| `qbCurPending` 三合一语义不变 | `test_webui_static_dom_panel.py` 既有 pin | **RC4**: 回退成两段版(`qbCurLoading && !qbCurData`) | rc=1 (红 ✓) |

## 增量明细(本轮真正新增/改动)

- **源(新)** —— `webui/static/shared/drawer_head.js`(`AQ_DRAWER_HEAD_COMPONENT`: props tone/icon/text/textTitle/statusTitle, 后两者缺省 `null` 避免流量形态长出多余 title 属性被 ui_feedback 迁成 data-aq-tip; `AQ_QB_CTL_COMPONENT` 无 props, 全走 `$root`)+ `webui/static/shared/tpl/drawer-head.html`(两个 x-template, 61 行)。
- **源(改)** —— `tpl/drawer.html`(两段 header 复写 → `aq-drawer-head` 两行调用; `.qb-statctl` 挂点接 `<aq-qb-ctl>`; `<aside>` 态类/aria 走 `drawerIsTraffic`; 留壳偏差的说明性注释)、`drawer.js`(四个新 computed + 两调用点)、`drawer_templates.js`(`dtMenuMergeOn`)、`menu.js`、`shortcuts.js`(三键盘入口)、`app.js`(两个 `app.component` 注册)、三皮肤 `index.html`(parts 尾行 + scripts 各一行, prism/console 压相邻 parts 项腾行 → **208/204/208 行**, cap 210 内)。
- **测试** —— `test_webui_static_dom_panel.py`: 六条用例同轮改版 + 新增 `test_frontend_drawer_form_judge_single_point` + 新增结构判根助手 `_tpl_body`/`_tpl_top_level_tags`; `test_web_shortcuts.py`: 七处 pin 同轮换。
- **零改动面(计划停手点)** —— `qb_traffic_chart.js`(仅 `active/stale` 谓词的 `drawer.kind` 字面量按停手点**冻结保留**, 守阵注豁免)、uPlot、三皮肤 CSS(`.drawer-body.is-traffic` 布局类原样)。

## 风险 / 观察

- **`$refs` 作用域是「组件化」的高频暗礁(W2+W3 连续两轮同病灶族)**: 根实例 `$refs` 只收**自己模板**里声明的 ref —— W2 的抽屉表头(拖宽没反应)与 W3 的图表挂载点(搬进组件图表静默不画)都是它。判别口诀: 凡根实例方法经 `this.$refs[x]` 找 DOM 的, 目标节点要么留在壳模板, 要么给该方法补 DOM 兜底。
- **类名 count 守阵对「包 wrapper」失明**: RC2 红验实证 —— wrapper 加进来后 `class="qb-tabs"` 等计数一个不变, 全绿, 但三皮肤四组直接子选择器已全部静默失效。多根片段的「根形态」必须结构级判根(HTML 解析 depth-0), 不能靠字符串计数。
- **形态判据收口是红可验的**: 谓词原文 + 各文件出现数都被钉住, 任何调用点回退成 `drawer.kind` 字面量、或谓词比较被翻错, 都会落在具名断言上; `qb_traffic_chart.js` 的豁免有注释与守阵双向登记(W5/W6 收口时摘)。
- **W3 没有新增 e2e 是口径内决策而非偷懒**: 计划 §05 W3 验收只列守阵动词(e2e 归 W4 的合并/右键四条), 且既有 164 项对头部组件化形成真手势回归网。
- **债务(承接, 不拦提交)**: `modules/webui-static-contract.md` 超 evergreen cap(W2/W3 各加一条, 债务加深); `kb.check` 切片数 > 70(每轮新增切片后加深)。两项均需另开新会话收口。
- W4–W6 待起(W4 = 合并双列 + 右键模板选择; W5 = 15 变体 → 声明式密度变体 + `esc-attr-quote-dead-class` 随之消失; W6 = 退役第二套渲染技术, 顺势摘 `qb_traffic_chart.js` 谓词的冻结豁免)。
