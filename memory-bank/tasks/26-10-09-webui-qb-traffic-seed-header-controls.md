# 26-10-09-webui-qb-traffic-seed-header-controls — 修回归: 种子流量图的时间档位/纵轴控件消失

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 07:40
**Topics:** webui-qb-traffic-charts
**Summary:** 用户报「上次更改使种子流量图的时间视图选择按钮和纵轴模式选择按钮弄消失了」。根因 = **2026-10-08 版式改只接了一个形态宿主**: 时间档位(`.qb-tabs`, 13 档)与纵轴控件(`.qb-tools`)自正文上提到头部时, 只加进了**流量形态头部**(`v-if="drawer.kind === 'traffic'"`, 全局/分组两挂点); 而**种子流量图**走的是**种子形态头部**(`v-else`, `kind === "seed"` + `tab === "traffic"`, 见 `qbCurScope` 的 torrent 分支)—— 该头部没有这段控件 ⇒ 种子「流量」页签的档位/纵轴整组消失(提交信息「三挂点(全局/分组/单种)共用同一段头部」的前提不成立: 单种与另两挂点**不共用头部**)。修法 = 种子形态头部补同款控件组(`.qb-headctl` 包裹, 整体占满第二行, 门 = `qbCurScope === 'torrent'`), 三皮肤 `views.css` 补 `.qb-headctl` 版式。**零 JS 改动**(绑定/清单全在根实例 mixin); 守阵只**改写**既有断言口径未新增测试函数。test.full 全绿 / 0 failed / TOTAL 99%(精确数字见基线切片 [26-10-09-0740](../testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md)); 真浏览器三皮肤实测控件齐全且不越界、零 pageerror。
**Refs:** memory-bank/testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md,memory-bank/pitfalls/web-ui/drawer-multi-form-hosts.md

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
