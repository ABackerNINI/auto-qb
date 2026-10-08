# webui-qb-traffic-gap-hatch-color — 流量图缺口斜纹配色修复

> 摘要: 用户报「WEBUI 流量图断线区域标注未落到正确的区域, 且其颜色几乎不可分辨」(附截图)。诊断结论: **两个症状同源** —— 斜纹色误用装饰性发丝线令牌 `--hairline`(alpha 仅 0.05~0.08)再叠 `globalAlpha=0.5`, 有效不透明度约 3%, 深/亮底上**都**等于没画; 颜色不可见导致无法判读落点, 故被感知成"没落到正确区域"。**几何经代数证明 + 数值枚举 6 组 + 真浏览器 A/B 渲染确认与原式逐条线段恒等, 无缺陷**(原"左移 H 像素"诊断被实测证伪)。修法 = 单列专用高对比令牌 `--qb-gap-hatch`(三皮肤 + prism 五主题成对, 亮主题用深墨色非白色)+ 去掉多余的 `globalAlpha` 折半。用户拍板「**现在修**」, 已闭环。
> 最后活动: 2026-10-08 11:30

**Refs:** memory-bank/pitfalls/web-ui/canvas-hatch-token.md,memory-bank/testing/baselines/26-10-08-1130-webui-qb-traffic-gap-hatch.md

- 坑档: [canvas-hatch-token](../pitfalls/web-ui/canvas-hatch-token.md) —— 「canvas 面积底纹不得复用发丝线令牌」+「症状『没落到正确区域』先分几何/配色两问」两条方法论, 含**证伪诊断不得留成守阵锚**的教训。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/qb_traffic_chart.js` —— `_qbChartTokens()` 新增 `gap` 令牌(回退链 `--qb-gap-hatch` → `--border-strong` → `--fg-muted`, 绝不落回 `grid`); `_qbDrawGaps` 改 `ctx.strokeStyle = tk.gap || tk.grid;` + `ctx.globalAlpha = 1`(去掉折半); 几何等价改写为 `x=xa; x<xb+H` 画 `(x-H,T+H)->(x,T)`(与原式恒等, 仅可读性)。
- 令牌面(5 文件): `prism/css/themes/{ocean,galaxy,orbit}.css` 深色 `rgba(255,255,255,.22)`; `frost.css` 深墨 `rgba(27,42,58,.22)`; `golden.css` 暖墨 `rgba(60,51,39,.22)`; `atlas/style.css` + `console/style.css` `rgba(255,255,255,.22)`。
- 关键判据(易被后人改坏): **面积底纹 / 高对比标注一律单列专用令牌**, 不复用发丝线(`--hairline`)与网格线令牌; 亮主题禁白色(`rgba(255,255,255,…)` 铺白底 = 不可见, 与深色主题的镜面缺陷)。
- 守阵: `test_frontend_qb_traffic_yaxis_and_annotation` 内 §5b(静态: 令牌成对 + 亮主题禁白)+ node **配色电池**(记账式假 ctx 调真实 `_qbDrawGaps`, 断言走专用令牌 / 不折半 / **令牌 alpha 量级下界 >= 0.15** 的数值判定)。**红验五路**均按预期变红, 还原复绿: ①还原 `tk.grid` ②还原 `globalAlpha=0.5` ③摘 frost 令牌 ④frost 误用白色 ⑤摘 atlas 令牌。
- 实测: `commands run test.full` **2791 passed + 4 skipped / 0 failed / 35.30s / TOTAL 99%**(16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial); 与上基线 26-10-08-1016(2790+4)相比 passed **+1**(§5b 未新增测试函数, 该 +1 来自其间其它专题并入的守阵 —— 本专题改的是同一函数内部)。
- 真机验证: `tmp-analysis/` 脚手架(已清理)含 `repro_gap.html` / `real_scene.html` / `ab.html` / `allskins.html` —— 五主题全皮肤渲染确认斜纹均清晰可见且落在缺口区(06:50–07:20 两桶)。
