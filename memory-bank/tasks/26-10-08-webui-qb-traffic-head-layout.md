# 26-10-08-webui-qb-traffic-head-layout — 流量图版式改(控件上提头部 + 图例并入统计栏)

**Status:** Done
**Added:** 2026-10-08
**Updated:** 2026-10-08 07:13
**Topics:** webui-qb-traffic-charts
**Summary:** 用户报「流量图被其它元素占用了高度, 主要信息(图本身)被压缩」。四条版式改(逐项拍板): ①**时间档位(13 档)+ 纵轴设置**自正文工具条**上提到「qB流量图」头部标题栏**; ②正文两处注释(工具条「qB 口径 · 程序运行期间(缺口 = 无采样, 停机/断连)」与图下行「…· 悬停查看详情」)**全部移除**; ③**上行/下行图例并入统计栏**(`.hs-leg`, 排在「窗口 N 桶」之前); ④**统计栏与状态栏间距减小**(`margin/padding-top` 10→6px)。标题由「qB 口径流量图」缩短为「qB流量图」(腾横向空间给档位)。**只改经典 UI**, `shared/drawer_tpl/` 15 个变体文件零改动。落地 = `drawer.html`(头部插 `.qb-tabs`/`.qb-tools`, 正文删工具条与独立图例, 统计栏加 `.hs-leg`)+ `qb_traffic_chart.js`(`qbTrafficTitle` 全局标题缩短)+ 三皮肤 `views.css`(`.hs-leg` 样式 / 头部 `:has(> .qb-tabs)` 换行不收缩 / 统计栏间距)。测试侧只**改写**两条既有守阵口径(未新增测试函数)。test.full **2772 passed + 4 skipped / 0 failed / 34.76s / TOTAL 99%**(基线 26-10-08-0713); 旁证真浏览器三皮肤目检头部仍 44px(未新增行)、图 266px 吃满余量、统计栏贴面板底缘、零 pageerror。
**Refs:** memory-bank/testing/baselines/26-10-08-0713-webui-qb-traffic-head-layout.md

## 原始请求

用户原文(附截图): 「流量图目前的问题: 流量图被其它元素占用了高度, 导致主要的信息(图本身)被压缩. 将时间档位/纵轴设置放到"qB 口径流量图"栏, 移除注释"qB 口径 · 程序运行期间(缺口 = 无采样, 停机/断连)", 将上行/下行图例放到统计栏(窗口 900桶后), 移除注释"qB 口径 · 程序运行期间(缺口 = 无采样, 停机/断连) · 悬停查看详情", 下方的"窗口 900桶"与状态栏间距减小. "qB 口径流量图"改为"qB流量图", 截图是qb全局流量图, 种子和辅种流量图类似修改, 只改"经典"UI图」

三问澄清后的拍板:
1. **「栏」指哪处**: **抽屉头部标题栏**(即「qB口径流量图 + 模板切换 + 收起/关闭」的 44px 头部行), 13 档窗口按钮与纵轴控件一起并进去; 正文只剩图 + 统计栏, 图高最大化。
2. **两处注释**: **全部移除**(上方图例注释与底部统计栏注释都删, 信息只在悬停 tooltip 里给)。
3. **原标题**: **缩短为「qB流量图」**(全局形态), 分组/种子仍显示各自名称。

## 思考过程与决策

- **「只改经典」的落点**: 详情面板现行「经典 / 变体」双轨(计划 26-10-06-0838)—— `shared/tpl/drawer.html` 的经典链与 `shared/drawer_tpl/15-*.js` 变体双轨。用户说「只改经典」⇒ 只动 `drawer.html` 的路由分支(流量形态头部 + 经典正文链), **不碰** `drawer_tpl/` 下 15 个变体文件。traffic 变体(13/14/15)消费的是 `qbCurData`/`qbCurSummary` 等数据域, 与本版式解耦 ⇒ 零改动可行。
- **控件为何能上提**: `.qb-tabs`/`.qb-tools` 的绑定(`qbWindowNames`/`qbCurWindow`/`qbSetWindow`/`qbYAxisMode`/`qbSetYAxisMode`/`qbYAxisCapText`)全在根实例 mixin 上, 头部与正文同处 `.drawer` 作用域内的 Vue 模板 ⇒ 搬到头部**只改 DOM 位置, 零 JS 逻辑改动**(唯一 JS 改动是标题文案)。
- **头部不新增行的判据**: 头部原为单行 44px(min-height 撑满), 13 档 + 纵轴并进来后总宽可能超出。定稿: 头部加 `:has(> .qb-tabs){flex-wrap: wrap}` 允许窄视口换行; 宽视口下标题(`flex:1 1 auto` + `min-width:0`)**优先让位**、档位/纵轴区 `flex: 0 0 auto` 不收缩 ⇒ 实测 1440x900 仍 44px、零换行。档位按钮紧凑档(`padding: 2px 8px`)回收横向空间。
- **`:has()` 选择器**: 只作用于「含 `.qb-tabs` 的头部」= 仅流量形态头部; 种子详情头部(含 `.drawer-tabs` 导航)不受影响 —— 避免用 `.drawer-head` 通用选择器误伤另一个头部。
- **图例并入统计栏**: 原独立 `.hist-legend` 行(图例 + 注释)整体删除; 图例色块改挂 `.hs-leg`(自带 `sw up/down`, 复用既有色义令牌 `--today-up/--today-down`), 插到 `.hist-summary` 首部。`popovers.html` 的历史流量弹层仍用 `.hist-legend`(那处注释「悬停查看详情」保留, 用户本次只针对流量图抽屉) —— 故 `.hist-legend` 类本身不删, 只在 drawer.html 里退场。
- **间距减小**: 该行既是「统计栏上边距」也是「统计栏与图的下边距」; 用户要的是「与状态栏间距减小」⇒ 把 `.hist-summary` 的 `margin-top`/`padding-top` 由 10px 收到 6px(面板高度靠抽屉高度锁, 省下的 8px 自然回给图)。
- **范围守恒**: 未动 `_QB_SCOPES` / 取数 / 轮询 / 窗口持久化 / 纵轴逻辑; 未动三挂点的数据域与变体文件; 未改面板默认高度语义(42vh 仍是另一件事)。

## 实现计划

单会话单步闭环: ① 三问拍板 → ② `drawer.html` 头部插控件 / 正文删工具条与图例 / 统计栏加 `.hs-leg` → ③ `qb_traffic_chart.js` 标题缩短 + 一处注释回写 → ④ 三皮肤 `views.css`(`.hs-leg` + 头部版式 + 间距) → ⑤ 守阵改写两条断言口径 + docstring → ⑥ `test.one` 定向 → ⑦ 真浏览器三皮肤目检(量头部/图/统计栏几何) → ⑧ `test.full` → ⑨ 回写(本档案 / 基线切片 / activeContext / progress)+ `kb.index`。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| S0 | 三问澄清与拍板 | ✅ | 头部标题栏 / 两处注释全删 / 标题缩短为「qB流量图」 |
| S1 | `drawer.html` 版式改 | ✅ | 头部插 `.qb-tabs` + `.qb-tools`; 正文删 `.drawer-toolbar` 与 `.qb-tools` 与独立 `.hist-legend`; 统计栏首部加两个 `.hs-leg` |
| S2 | 标题缩短 + 注释回写 | ✅ | `qbTrafficTitle` 全局 → `"qB流量图"`; 图例渲染位置注释回写 |
| S3 | 三皮肤 CSS | ✅ | `.hs-leg`(atlas/console/prism); 头部 `:has(> .qb-tabs)` 换行 + 档位/纵轴不收缩 + 紧凑档; `.hist-summary` 间距 10→6px |
| S4 | 守阵改写 | ✅ | 旧「图例 hint 两处同步」退役 → 新三条口径(文字退场/图例在统计栏首位/独立图例行不存在); `.qb-tools` 落点断言改判头部 |
| S5 | 定向 + 全量测试 | ✅ | `test.one` 29 passed; `test.full` **2772+4 / 0 failed / 34.76s / TOTAL 99%**(基线 26-10-08-0713) |
| S6 | 真浏览器三皮肤目检 | ✅ | 头部 44px / 图 266px / 统计栏贴底 / `.hist-legend` 计数 0 而 `.hs-leg` 计数 2 / 零 pageerror |
| S7 | 收尾回写 + 索引重建 | ✅ | 本档案 / 基线切片 / activeContext 切片 / progress 回写; `kb.index` |

## 进度日志

- **2026-10-08 06:58** 会话开工: 同步 `已同步 126b8aa7`(dd12edc7→126b8aa7); 读 `pitfalls/_index.md` + `web-ui/_index.md`; 定位流量图实现单点(`shared/tpl/drawer.html` 头部与正文块、`shared/qb_traffic_chart.js` 的 `qbTrafficTitle`、三皮肤 `views.css` 的 `.qb-tabs`/`.qb-tools`/`.hist-*` 段)与「经典 / 变体」双轨模型(核心层 `drawer_templates.js` + 15 个变体文件)。
- **2026-10-08 07:0x** 三问澄清; 用户逐项拍板(头部标题栏 / 两处注释全删 / 标题缩短)。
- **2026-10-08 07:0x** 落码 S1–S3: 头部插 13 档与纵轴控件; 正文删工具条与独立图例行; 统计栏首部加 `.hs-leg`; `qbTrafficTitle` 全局标题缩短; 三皮肤 CSS 补齐。首轮编辑头部时漏带模板切换器/收起/关闭块(编辑区段切错), 当帧即发现并改回(校验 `class="qb-tabs"` 计数 1 / `hist-legend` 计数 0 / 各标签配平)。
- **2026-10-08 07:1x** 守阵改写: `test_frontend_qb_traffic_chart_wiring` 第 6 点旧「图例 hint 两处同步」断言退役(该文案已按用户要求移除)改钉三条新口径; `test_frontend_qb_traffic_yaxis_and_annotation` 第 9 点 `.qb-tools` 落点断言从正文改判头部; 两处 docstring 清单同步。`test.one` **29 passed**。
- **2026-10-08 07:1x** 真浏览器目检(临时桩打开 qb_traffic + 合成天文件 + TM 当日流量让入口走真实路径; Chromium 1440x900 三皮肤): 头部 **44px**(未新增行)/ 档位区 510px / 纵轴区 299px / 图 **266px**(body 332 - 统计栏 26 - 间隙)/ 统计栏 819~845 贴 dock 底 866、状态栏 866 起(间距已减小)/ `.hist-legend` 计数 0 而 `.hs-leg` 计数 2 / 标题「qB流量图」/ **零 pageerror**。三皮肤一致。临时桩与截图已删(不入库)。
- **2026-10-08 07:13** `test.full` **2772 passed + 4 skipped / 0 failed / 34.76s / TOTAL 99%**(16476/165/5694/149, 相对上基线 2772+4 passed ±0 —— 只改断言口径未新增测试函数)。收尾回写: 本档案 + 基线切片 [26-10-08-0713](../testing/baselines/26-10-08-0713-webui-qb-traffic-head-layout.md) + activeContext 切片 + `progress/implemented-webui-history.md` 版式改条目; `kb.index` 重建。
