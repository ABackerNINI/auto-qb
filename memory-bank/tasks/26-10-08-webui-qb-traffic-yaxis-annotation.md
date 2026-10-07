# 26-10-08-webui-qb-traffic-yaxis-annotation — 流量图纵轴固定模式 + 画布注解层

**Status:** Done
**Added:** 2026-10-08
**Updated:** 2026-10-08 05:59
**Topics:** webui-qb-traffic-yaxis-annotation
**Summary:** 用户命题「WEBUI 流量图添加纵轴最大值固定模式(可切换; 限速+20% 或手动输入值; 峰值超出最大值需按峰值显示; 覆盖全局流量 / 种子 / 辅种分组三挂点)」, 并一并认领 issue 26-10-07-0149(13 变体限速虚线/缺口斜纹注解层)。四问拍板: ①限速一律取 **qB 全局限速**(三作用域同源) ②方向取**上下行较大者** ③手动值单位 **MiB/s** ④偏好**三作用域各自独立**持久化; 注解层范围拍板「**共享图面**(三挂点全生效)」, 自动模式下**峰值超过限速才画**限速线。落地 = `qb_traffic_chart.js` 纵轴三态(auto/limit/manual)+ 值域纯函数 `_qbYRange`(上限只保底, 峰值超上限按峰值)+ 画布注解层(`drawClear` 缺口斜纹 / `draw` 限速虚线, uPlot ctx 无 transform = 设备像素按 `pxRatio` 换算)+ `state.js` 三字段 + `drawer.html` 控件 + 三皮肤 CSS; 新增守阵 1 个测试函数(2 组 node 电池, 红验三次均按预期变红)。纯前端静态层 + 测试侧, Python 产品代码零改动。test.full **2772 passed + 4 skipped / 0 failed / 48.44s / TOTAL 99%**(基线 26-10-08-0559); 旁证 `npm run test:e2e:fast` 8 passed、真浏览器注解钩子自检零 pageerror(带钩子比不带多 9,870 已绘制像素)。
**Refs:** memory-bank/issues/26-10-07-0149-feat-webui-traffic-chart-annotation-layer.html,memory-bank/testing/baselines/26-10-08-0559-webui-qb-traffic-yaxis-annotation.md

## 原始请求

用户原文: 「WEBUI流量图添加纵轴最大值固定模式, 可切换. 纵轴最大值可以选择[限速+20%]或者手动输入值. 注意峰值如果超出最大值需按峰值显示. 包括全局流量/种子与辅种分组流量」。

四问澄清后的拍板:
1. **限速来源**: 三张图**都只用全局限速**(不取种子自身限速 / 不取组内成员限速之和); 同时用户补充「补充文档 `26-10-07-0149-feat-webui-traffic-chart-annotation-layer.html`, **认领一并做**」。
2. **方向口径**: 纵轴上下行共用一条 ⇒ 取**上下行限速的较大者**。
3. **手动值单位**: **MiB/s 数值**。
4. **持久化粒度**: **三个作用域各自独立一份**。

注解层两问: ①画在**共享图面**(三挂点全部生效, 非仅 13 变体); ②自动模式下**最大值超过限速才画**限速虚线。

## 思考过程与决策

- **复验(issue 26-10-07-0149)**: 按防过期原则先重跑锚点 —— ①`drawer_tpl/13-traffic-chart-led-tall.js` 头注释仍写「P-03 拍板: v1 省略图上虚线/斜纹注解层」、`limitCell()` 仍以 KPI 文字格展示限速值(锚点与报告一致); ②`qb_traffic_chart.js` 建图管线此前只有 `setCursor` 一个钩子, 无注解层挂点; ③守阵 `test_frontend_qb_traffic_chart_wiring` 在位(文件已由 test-web-split 迁入 `test_webui_static_dom_panel.py`)。结论: **仍复现**。
- **改道说明(与 issue「建议修法」的出入)**: issue 建议「暴露 uPlot 实例给 13 变体、插件整体放变体文件」的窄口径; 用户拍板改为**共享图面** ⇒ 直接把注解画进建图管线(两钩子), 不再需要对外暴露实例, 三挂点 + 经典/所有变体一次全生效。代价: 动现管线(守阵回归项全过), 但**净改动面反而更小**(无新对外接口)。
- **画布坐标口径(读 vendor 源码确认, 非猜测)**: uPlot 1.6.32 的 `ctx` **不设 transform**, `_draw` 里 `clearRect(0,0,can.width,can.height)`(can.width = CSS 宽 × `pxRatio`), 自身绘制处处 `*pxRatio`; `u.bbox` 是**设备像素**, 而 `valToPos(v, scale)`(第三参缺省)**回 CSS 像素且相对绘图区**(`getHPos(val, scale, plotWidCss, 0)`)。⇒ 统一 `ctx.save(); ctx.scale(pxRatio);`, 绝对坐标 = `bbox/pxRatio + valToPos(相对值)`, 线宽/虚线/间距用 CSS 值。**不猜**, 写成 `_qbCanvasScale` 单点 + 注。
- **值域语义**: `_qbYRange(dmax, cap)` = 自动 `[0, peak*1.05]`(无数据回落 1); `cap>0` 时 `max(cap, peak*1.05)` —— 上限只保底、**绝不裁剪数据**(用户原话「峰值如果超出最大值需按峰值显示」)。抽成模块级纯函数以便 node 单测。
- **限速线可见性判据**: 只画 `0 < 限速 < yMax` 的线 —— 自动模式下峰值未超限速时线在顶沿之上不可见, 自然不画(与用户拍板「自动模式最大值超过限速才画」同构); 固定模式下 `yMax ≥ 限速×1.2 > 限速`, 恒画。0(不限速)/null(未知)一律不画。**一条判据覆盖两模式**, 不写模式分支。
- **缺口判据**: 上下行**皆** null 才算缺口(后端整桶 null 时两列同 null; 单列 null 防御性不误判成缺口)。斜纹画在**系列之下**(`drawClear` 钩子, 在 `clearRect` 之后、`drawOrder` 之前), 不遮曲线。
- **持久化粒度**: 与窗口档位刻意不同(用户拍板)—— 窗口是「全局单独 / 组种共用」, 纵轴是「三作用域各自独立」; 键 `autoqb.ui.qbYAxis{Global,Torrent,Group}`, 值 JSON `{mode, manual}`。
- **重排而非重取**: 切档/改值只改 scale ⇒ 走 `_qbChartRescale`(`setData` 默认 `resetScales=true` 重跑 range 与全部 draw 钩子), 不销毁重建、不重拉数据(重取数等于白拉一发)。限速值可能在建图后才到手(qB 重连 / 长窗轮询夹到 600s)⇒ `mounted` 注册 `$watch` 按值变化重排; 注册方式沿用 `drawer_templates.js` 先例(全局 mixin 会注入 `<transition>` 的 BaseTransition 假实例, 写成 watch 选项会在其上求值即抛)⇒ `mounted` 里先按 `this.drawer` 守卫。
- **范围守恒**: 只动流量图纵轴/注解与其控件; 未触碰 13/14/15 变体文件(其 KPI 限速文字格保留, 与本次「全局限速」口径不同属两件事)、未动后端、未动取数/窗口/轮询逻辑。

## 实现计划

单会话单步闭环: ① 四问拍板 + 两问注解层范围 → ② `qb_traffic_chart.js`(常量/初值/纯函数/作用域表 `yaxis` 字段/computed/methods/两钩子/range/`mounted` 守卫) → ③ `state.js` 三字段 → ④ `drawer.html` 控件 → ⑤ 三皮肤 CSS → ⑥ 守阵(`test_webui_static_dom_panel.py` 新函数 + node 电池; `test_webui_error_history.py` 存储基线 1→2) + **红验** → ⑦ `test.quick` / `test.full` / `npm run test:e2e:fast` / 真浏览器注解钩子自检 → ⑧ 回写(issue Done + 认领链 / 本档案 / 基线切片 / activeContext / conventions/webui.md) + `kb.index`。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| S0 | 澄清与拍板(四问 + 注解层两问) + issue 复验 | ✅ | 全局限速 / 取大者 / MiB/s / 三作用域独立; 共享图面 + 超限速才画; 复验「仍复现」 |
| S1 | 纵轴三态 + 值域纯函数 + 上限派生单点 | ✅ | `QB_YAXIS_MODES` / `QB_YAXIS_LIMIT_FACTOR` / `QB_YAXIS_MIB` / `_qbYRange` / `_qbYCapOf` / `_qbGlobalLimit` |
| S2 | 持久化(三作用域独立)+ 切档落盘重排 + 限速变化重排 | ✅ | `qbYAxisStoreKey` / `qbInitialYAxis` / `persistQbYAxis` / `qbSetYAxisMode` / `qbSetYAxisManual` / `_qbChartRescale` / `mounted` `$watch` |
| S3 | 画布注解层(限速虚线 + 缺口斜纹) | ✅ | `_qbCanvasScale` / `_qbDrawGaps`(`drawClear`)/ `_qbDrawLimits`(`draw`)/ `_qbGapRuns` |
| S4 | 接线: `state.js` 三字段 + `drawer.html` 控件 + 三皮肤 CSS | ✅ | `qbHistYAxis`/`qbTorrentYAxis`/`qbGroupYAxis`; `.qb-tools`/`.qb-seg`/`.qb-yaxis-input`(atlas/console/prism) |
| S5 | 守阵 + 红验 + 基线 | ✅ | `test_frontend_qb_traffic_yaxis_and_annotation`(+2 node 电池); 红验 3 次; 存储基线 1→2; test.full **2772+4 / 99%**(基线 26-10-08-0559) |
| S6 | 真浏览器验证 | ✅ | `npm run test:e2e:fast` 8 passed; 注解钩子自检零 pageerror、带钩子多 9,870 已绘制像素 |
| S7 | 收尾回写 + 索引重建 | ✅ | issue 置 Done + 认领链双向; 本档案 / 基线切片 / activeContext 切片 / `conventions/webui.md` 取色面回写; `kb.index` + `gen_issues_index` |

## 进度日志

- **2026-10-08 05:33** 会话开工: 同步 `已同步 29fa6c8b`; 读 `pitfalls/_index.md` + `web-ui/_index.md`; 定位流量图实现单点(`shared/qb_traffic_chart.js` 建图管线 `_qbChartBuild`、`_QB_SCOPES` 三挂点表、`shared/tpl/drawer.html` 流量正文块、三皮肤 `views.css` 的 `.qb-tabs` 段)与限速数据源(`statsServer.up_rate_limit/dl_rate_limit` 随主轮询下发, `speedLimitBytes` 为既有取数单点)。
- **2026-10-08 05:40** 四问澄清 + 注解层两问; 用户补充「补充文档 26-10-07-0149 认领一并做」⇒ 读该 issue(Open/standard/feat)并复验锚点仍复现。
- **2026-10-08 05:45** 读 uPlot vendor 源码确认画布坐标口径(无 transform / 设备像素 / `bbox` 与 `valToPos` 单位差异 / `uPlot.pxRatio`), 定 `_qbCanvasScale` 单点。
- **2026-10-08 05:5x** 落码 S1–S4(8 个文件: 组件 / state / 模板 / 三皮肤 CSS / 两测试文件); `node --check` 通过; node 电池实测 `_qbYRange` 5 例 + `_qbGapRuns` 5 例全过。
- **2026-10-08 05:5x** 守阵落码 + **红验三次**(①去掉峰值保底 → 电池「峰值超固定上限按峰值显示」红; ②摘 `drawClear` 钩子 → 红; ③断 y range 接线 → 红), 每次还原复绿。
- **2026-10-08 05:5x** 验证: `test.quick` **2772 passed + 4 skipped**; `test.full` **2772 passed + 4 skipped / 0 failed / 48.44s / TOTAL 99%**(16476/165/5694/149); `npm run test:e2e:fast` **8 passed**(含渲染健康无运行时错误); 真浏览器加载 vendor + 组件跑注解钩子自检 —— 零 pageerror, 带钩子 27937 vs 不带 18067 已绘制像素。
- **2026-10-08 05:59** 收尾回写: issue 置 **Done** + `doc-refs` 回填(认领链双向闭合); 新建本档案 + 基线切片 [26-10-08-0559](../testing/baselines/26-10-08-0559-webui-qb-traffic-yaxis-annotation.md); `conventions/webui.md` 流量方向色族消费面补注画布注解层同源取色; activeContext 切片; `kb.index` + `gen_issues_index` 重建。
