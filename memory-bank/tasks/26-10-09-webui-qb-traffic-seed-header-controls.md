# 26-10-09-webui-qb-traffic-seed-header-controls — 修回归: 种子流量图的时间档位/纵轴控件消失

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 11:14
**Topics:** webui-qb-traffic-charts
**Summary:** 用户报「上次更改使种子流量图的时间视图选择按钮和纵轴模式选择按钮弄消失了」。根因 = **2026-10-08 版式改只接了一个形态宿主**: 时间档位(`.qb-tabs`, 13 档)与纵轴控件(`.qb-tools`)自正文上提到头部时, 只加进了**流量形态头部**(`v-if="drawer.kind === 'traffic'"`, 全局/分组两挂点); 而**种子流量图**走的是**种子形态头部**(`v-else`, `kind === "seed"` + `tab === "traffic"`, 见 `qbCurScope` 的 torrent 分支)—— 该头部没有这段控件 ⇒ 种子「流量」页签的档位/纵轴整组消失(提交信息「三挂点(全局/分组/单种)共用同一段头部」的前提不成立: 单种与另两挂点**不共用头部**)。修法 = 种子形态头部补同款控件组(`.qb-headctl` 包裹, 整体占满第二行, 门 = `qbCurScope === 'torrent'`), 三皮肤 `views.css` 补 `.qb-headctl` 版式。**零 JS 改动**(绑定/清单全在根实例 mixin); 守阵只**改写**既有断言口径未新增测试函数。test.full 全绿 / 0 failed / TOTAL 99%(精确数字见基线切片 [26-10-09-0740](../testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md)); 真浏览器三皮肤实测控件齐全且不越界、零 pageerror。**第 2 轮(同日, 用户更正落点)**: 用户判定控件放种子头部「太挤、小窗口下会变形」, 控件组改落**图下统计栏**(`.hist-summary` 内 `.qb-statctl`, 排在「下载累计」之后, 落点容器 `.qb-headctl` 随之退役), 统计栏本体渲染门放宽为 `qbCurSummary || qbCurScope === 'torrent'`(首载/错误态无汇总时控件仍可见); **全局/分组流量形态零改动**(控件仍在流量形态头部)。零 JS 改动; 守阵仍只改写断言口径未新增测试函数。
**Refs:** memory-bank/testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md,memory-bank/testing/baselines/26-10-09-1114-webui-qb-traffic-seed-statbar-controls.md,memory-bank/pitfalls/web-ui/drawer-multi-form-hosts.md

## 原始请求

用户原文: 「上次更改使种子流量图的时间视图选择按钮和纵轴模式选择按钮弄消失了, 修复」

## 思考过程与决策

- **定位(读码即定, 非推断)**: `qbCurScope`(`qb_traffic_chart.js:285`)对 `kind === "seed" && tab === "traffic"` 返回 `"torrent"` —— 即**种子流量图是种子形态**, 不是 `kind === "traffic"`。而 `drawer.html` 的两个头部是 `v-if="drawer.kind === 'traffic'"` / `v-else` 二选一, 2026-10-08 的控件只写进了前者。`qbTrafficTitle` 的 `"torrent"` 分支其实是**死代码**(`openDrawerTraffic` 只被 `global`/`group` 调用), 侧面印证当时的「三挂点共用头部」是误判。
- **为何守阵没拦住**: 既有守阵钉的是「控件落在**流量形态头部**内」—— 断言为真, 而种子头部缺控件**不在断言面内**。属「断言口径太窄」而非「没断言」。
- **修法(落点)**: 用户上一次的原始指令是「将时间档位/纵轴设置放到『qB 口径流量图』栏 … 种子和辅种流量图类似修改」—— 故修法取**回头部**(而非把工具条放回正文): 种子头部补同款控件组, 与全局/分组观感一致。**不动**流量形态头部(用户已拍板的单行 44px 布局)。
- **版式(种子头部为何两行)**: 种子头部已承载五页签导航 + 模板切换器, 13 档 + 纵轴再并进单行放不下。定稿: 控件组用 `.qb-headctl` 包成一组、置于头部末位、`flex: 1 1 100%` ⇒ **恒**换到第二行(与视口宽无关, 不依赖自然换行的巧合)。`.drawer-head` 既有的 `:has(> .qb-tabs)` 规则不命中本形态(控件非直接子级), 故新加 `:has(> .qb-headctl)` 一条。
- **防漂移**: 两处控件组内层标记必须逐字同源 ⇒ 新增守阵把两块内层(从 `<div class="qb-tabs">` 到 `qb-tools` 收口 `</div>`, 空白归一后)比对, 一处改了另一处不同步即红。
- **范围守恒**: 未动 `_QB_SCOPES` / 取数 / 轮询 / 纵轴逻辑 / 窗口持久化 / 15 个 `drawer_tpl/` 变体; 未动 `drawer_tpl` 与其它页签头部(非流量页签下 `.qb-headctl` 不渲染, 种子头部仍是单行 44px)。

## 实现计划

单会话单步闭环: ① 读码定位(两个头部的 v-if/v-else 与 `qbCurScope` 派生)→ ② `drawer.html` 种子头部补控件组 → ③ 三皮肤 `views.css` 补 `.qb-headctl` → ④ 守阵改写(两头部齐全 + 逐字同源 + CSS 成对)→ ⑤ `test.one` 定向 → ⑥ 真浏览器三皮肤验证 → ⑦ `test.full` → ⑧ 回写(档案 / 基线切片 / activeContext / progress / 坑档)+ `kb.index`。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| S0 | 定位根因 | ✅ | 种子流量图走**种子形态头部**(`qbCurScope === 'torrent'`), 版式改只接了流量形态头部 |
| S1 | `drawer.html` 种子头部补控件组 | ✅ | `.qb-headctl`(门 `qbCurScope === 'torrent'`, 置于头部末位), 内层与流量形态头部逐字同源 |
| S2 | 三皮肤 CSS | ✅ | `:has(> .qb-headctl)` 换行 + `.qb-headctl { flex: 1 1 100%; display:flex }` + 内层不收缩/紧凑档(atlas/console/prism) |
| S3 | 守阵改写 | ✅ | 两头部控件组齐全 + `qbCurScope === 'torrent'` 门 + 内层逐字同源 + `qbSetYAxisMode(` 计数 3→6 + CSS 三皮肤成对; 零新增测试函数 |
| S4 | 定向 + 全量测试 | ✅ | `test.one` 29 passed; `test.full` 全绿 / 0 failed / TOTAL 99%(精确数字见基线 26-10-09-0740) |
| S5 | 真浏览器三皮肤验证 | ✅ | 种子「流量」页签: `.qb-headctl` 可见 / 档位 13 / 纵轴 3 / 控件框 `x=29 w=1388` 不越界 / 头部 65px(两行) / 图或空态可见 / 零 pageerror |
| S6 | 收尾回写 + 索引重建 | ✅ | 本档案 / 基线切片 / activeContext 切片 / progress / 坑档; `kb.index` |

## 进度日志

- **2026-10-09 07:33** 会话开工: 同步 `同步成功 289d947e`(4ce4a19f→289d947e); 读 `kb.active` 最近切片(命中 `26-10-08-0713-webui-qb-traffic-head-layout`)→ 读该档案与 `0e8d5432` 提交 diff → 定根因。
- **2026-10-09 07:3x** 落码 S1–S2: `drawer.html` 种子头部加 `.qb-headctl`; 三皮肤 `views.css` 各加 5 行 `.qb-headctl` 规则。复核: 两处控件组内层 826 字符逐字相等、`qbSetYAxisMode(` 计数 6、`dt-select`/`drawer-fold`/`drawer-close` 计数仍各 2。
- **2026-10-09 07:3x** 守阵改写 S3(只改断言口径, 零新增测试函数); `commands run test.one -- tests/test_webui_static_dom_panel.py` **29 passed**。
- **2026-10-09 07:3x** 真浏览器验证 S5: 临时桩(`tmp-analysis/`, 已 gitignore)复用 `scripts/ui_harness.py` 的合成种子设施 + 打开 `qb_traffic` 旗标; Playwright 三皮肤 1440x900 走真实手势(双击种子行 → 点「流量」页签): 三皮肤全 PASS(档位 13 / 纵轴 3 / 控件框 29,523 1388x26 / 头部 65px / 零 pageerror), 截图目检确认为「标题+五页签」第一行、控件组第二行的两行头部。临时桩与截图已删。
- **2026-10-09 07:40** `commands run test.full` **2817 passed + 4 skipped / 0 failed / 36.35s / TOTAL 99%**(16479/162/5696/146); 新建基线切片 [26-10-09-0740](../testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md); 新坑写进坑档 [drawer-multi-form-hosts](../pitfalls/web-ui/drawer-multi-form-hosts.md); 本档案 + activeContext 切片 + `progress/implemented-webui-history.md` 回写; `kb.index` 重建。

## 第 2 轮(同日 11:14): 落点更正 —— 控件改落图下统计栏

**原始请求(用户原文)**: 「提交83bf296f 把种子流量图的时间视图选择按钮和纵轴模式选择按钮放错了未知, 按qb全局流量图放置」
(「未知」是「位置」的输入法误打; 「提交 83bf296f」= 指代上一轮那笔提交, 即对本轮落点提出更正)。

**澄清轮(AskUserQuestion)**: 就「控件组落在种子头部哪个位置」给了两个选项(标题后紧跟 / 五页签导航之后) ——
两选项都属「放头部」; 用户答: 「放在上方适合太过拥挤, 小窗口下会变形, 先放流量图下方统计栏, 即『下载累计』后看看效果」。

**结论与决策**:

- **落点** = 图下统计栏 `.hist-summary`, 排在「下载累计」之后、口径 hint 之前。用户口径理由: 种子头部已承载五页签导航 + 模板切换器, 13 档 + 纵轴再并进去太挤, 窄视口下会变形。
- **范围** = 只改**种子**侧(`qbCurScope === 'torrent'`)。全局/分组流量形态**零改动** —— 用户首句把全局图当参照(「按qb全局流量图放置」), 且从未报全局头部有问题; 澄清轮的提问本身也只针对种子侧控件组。
- **容器换名**: `.qb-headctl`(头部里那组)→ `.qb-statctl`(统计栏里那组)。不沿用旧类名 —— 一个叫 `head` 的类活在统计栏里, 正是后续读者最容易误判的漂移点。
- **统计栏本体的门必须放宽**(本轮唯一非纯平移的改动): `.hist-summary` 原本门在 `qbCurSummary` 上, 而 `_qbSummaryOf` 在数据为 null 时返回 null(= 首载 / 错误态)⇒ 只写 `qbCurSummary` 会让控件在「取不到数」时整组消失, 用户连换档位重试都点不到。改门为 `qbCurSummary || qbCurScope === 'torrent'`, 汇总子项各自 `v-if="qbCurSummary"`(全局/分组侧渲染结果逐字不变)。
- **防漂移**: 两处控件组仍钉**逐字同源**(流量形态头部 vs 统计栏), 守阵的比对对象随落点平移。
- **已知代价**(留给后续评估): 统计栏由 26px 变 54~57px ⇒ 图少约 31px —— 2026-10-08 版式改「把高度还给图」的收益被吃掉一部分; 口径 hint 因 `margin-left:auto` 被顶到第二行。用户口径是「先放…看看效果」, 若嫌图矮, 下一步可考虑 hint 让位或控件组与汇总分行的合并。

**子任务状态表(第 2 轮)**:

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| R2-S1 | 模板落点平移 | ✅ | `drawer.html`: 删种子头部 `.qb-headctl` 控件组, 统计栏「下载累计」后插 `.qb-statctl`(门 `qbCurScope === 'torrent'`)+ 统计栏本体门放宽 |
| R2-S2 | 三皮肤 CSS | ✅ | 原 5 行 `.qb-headctl` 规则换成 4 行 `.hist-summary > .qb-statctl`(成组 / 内层不收缩 / 紧凑档; atlas·console·prism 成对) |
| R2-S3 | 守阵改写 | ✅ | 落点改判统计栏 + 种子头部「不得再有控件组」+ 统计栏次序下标单调 + 统计栏本体门 + CSS 钉点换类名; **零新增测试函数** |
| R2-S4 | 定向 + 全量测试 | ✅ | `test.one` 定向 31 passed; `test.full` 全绿 / 0 failed / TOTAL 99%(精确数字见基线切片 26-10-09-1114) |
| R2-S5 | 真浏览器验证 | ✅ | 三皮肤 1440x900 + 窄视口 1180/980/820 + 分组形态对照; 零 pageerror |
| R2-S6 | 收尾回写 + 索引重建 | ✅ | 本档案 / 基线切片 / activeContext 切片 / progress / 坑档; `kb.index` |

**进度日志(第 2 轮)**:

- **2026-10-09 10:5x** 会话开工: 同步 `同步成功 620ec75b`(1f5334e5→620ec75b); 读 `kb.active` + 本档案 + `83bf296f`/`0e8d5432` 两笔 diff + 坑档, 定「控件当前在种子头部末位、`flex:1 1 100%` 恒占第二行」。
- **2026-10-09 11:0x** 澄清轮: 就落点问用户(两个「放头部」选项), 用户改口「放图下统计栏, 即『下载累计』后」。
- **2026-10-09 11:0x** 落码 R2-S1/R2-S2 + 守阵改写 R2-S3; `commands run test.one -- tests/test_webui_static_dom_panel.py` 定向 31 passed。
- **2026-10-09 11:0x** 真浏览器验证 R2-S5(临时桩复用 `scripts/ui_harness.py` 合成种子 + 打开 `qb_traffic` 旗标 + 合成流量响应; Playwright 三皮肤 1440x900 真实手势 + 窄视口四档 + 分组右键「qB 口径流量图」对照): 全部通过、零 pageerror; 临时桩与截图已删。
- **2026-10-09 11:14** `commands run test.full` 全绿 / 0 failed / 45.9s / TOTAL 99%(精确数字见基线切片 [26-10-09-1114](../testing/baselines/26-10-09-1114-webui-qb-traffic-seed-statbar-controls.md)); 坑档 [drawer-multi-form-hosts](../pitfalls/web-ui/drawer-multi-form-hosts.md) 补第 2 轮口径; 本档案 + activeContext 切片 + `progress/implemented-webui-history.md` 回写; `kb.index` 重建。
