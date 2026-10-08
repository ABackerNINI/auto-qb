# webui-qb-traffic-gap-hatch — 流量图缺口斜纹配色 + 几何修复

> 摘要: 用户报「WEBUI 流量图断线区域标注未落到正确的区域, 且其颜色几乎不可分辨」(附截图)。**第一轮**诊断结论: 两症状同源 —— 斜纹色误用装饰性发丝线令牌 `--hairline`(alpha 仅 0.05~0.08)再叠 `globalAlpha=0.5`, 有效不透明度约 3%, 深/亮底上**都**等于没画。修法 = 单列专用高对比令牌 `--qb-gap-hatch`(三皮肤 + prism 五主题成对, 亮主题用深墨色非白色)+ 去掉多余的 `globalAlpha` 折半。**第二轮(用户复报「第一次修复未成功」)**: 真几何缺陷 —— `_qbDrawGaps` 用 45 度线段铺缺口时只把外层 clip 收到**整个绘图区**, 涂出的并集是"宽 = 图高 H 的**斜向平行四边形**"(左右边界皆斜边), 缺口右段下半留白、左段上半越界到缺口左侧; 第一轮把此缺陷**误判为"颜色不可见导致无法判读落点"**, 并写下"几何经代数证明恒等、无缺陷"的**错误结论**(代数只证两式互等, 未证形状正确, 两式同错)。修法 = **逐 run 追加一次 clip 到缺口矩形** `ctx.rect(xa, T, xb-xa, H)` + `xa<xb` 退化守卫。两轮均闭环。
> 最后活动: 2026-10-08 11:44

**Refs:** memory-bank/pitfalls/web-ui/canvas-hatch-token.md,memory-bank/testing/baselines/26-10-08-1130-webui-qb-traffic-gap-hatch.md,memory-bank/testing/baselines/26-10-08-1144-webui-qb-traffic-gap-geometry.md

- 坑档: [canvas-hatch-token](../pitfalls/web-ui/canvas-hatch-token.md) —— 「45 度线铺竖矩形底纹必须逐 run 裁到目标矩形, 只裁绘图区不够」+「症状『没落到正确区域』先分几何/配色两问」+「等价 ≠ 正确; 已证结论被推翻必须回改坑档」三条方法论, 含**证伪诊断不得留成守阵锚**的教训。
- 落地(**两轮**, 纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/qb_traffic_chart.js` —— ①第一轮: `_qbChartTokens()` 新增 `gap` 令牌(回退链 `--qb-gap-hatch` → `--border-strong` → `--fg-muted`, 绝不落回 `grid`); `_qbDrawGaps` 改 `ctx.strokeStyle = tk.gap || tk.grid;` + `ctx.globalAlpha = 1`(去掉折半); ②第二轮: `_qbDrawGaps` 每 run 追加 `ctx.save()/rect(xa,T,xb-xa,H)/clip()` 把斜带裁成竖矩形 + `if (!(xb > xa)) continue;` 退化守卫; 函数头补「几何硬约束, 别改坏」注释。
- 令牌面(5 文件, 第一轮): `prism/css/themes/{ocean,galaxy,orbit}.css` 深色 `rgba(255,255,255,.22)`; `frost.css` 深墨 `rgba(27,42,58,.22)`; `golden.css` 暖墨 `rgba(60,51,39,.22)`; `atlas/style.css` + `console/style.css` `rgba(255,255,255,.22)`。
- 关键判据(易被后人改坏): ①**面积底纹 / 高对比标注一律单列专用令牌**, 不复用发丝线(`--hairline`)与网格线令牌; 亮主题禁白色。②**45 度线铺"竖矩形"底纹必须逐 run 裁到目标矩形** —— 只裁绘图区会成斜向平行四边形。③`ctx.clip()` 不改写记账式假 ctx 的端点, 守阵不能断言"原始端点落在区间内"。
- 守阵: `test_frontend_qb_traffic_yaxis_and_annotation` §5b(第一轮: 令牌成对 + 亮主题禁白; 第二轮: `ctx.rect(xa, T, xb-xa, H)` + `if (!(xb > xa)) continue;` 静态锚)+ node **电池**(记账式假 ctx 调真实 `_qbDrawGaps`, 断言走专用令牌 / 不折半 / **令牌 alpha 量级下界 >= 0.15** / **per-run clip == 缺口矩形** / 扫线覆盖缺口两边界 / 线段跨度恒 = H)。**红验六路**均按预期变红, 还原复绿: ①还原 `tk.grid` ②还原 `globalAlpha=0.5` ③摘 frost 令牌 ④frost 误用白色 ⑤摘 atlas 令牌 ⑥**删 per-run 缺口矩形 clip(几何锚变红)**。
- 实测: `commands run test.full` **2791 passed + 4 skipped / 0 failed / 32.8s / TOTAL 99%**(16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial)。基线切片 [26-10-08-1144](../testing/baselines/26-10-08-1144-webui-qb-traffic-gap-geometry.md)(第二轮); 与第一轮基线 26-10-08-1130 相比 passed **±0**(两轮均改同一函数内部, 未新增测试函数)。
- 真机/真浏览器验证: 栅格化模拟 + 真浏览器 canvas 渲染截图(临时脚手架 `tmp-analysis/`, 已清理)确认第二轮修复后斜纹呈**竖矩形**, 恰好铺满缺口区间 `[xa, xb]` 全高, 左右边界为竖直边, 无斜边越界; 对比第一轮产物为斜向平行四边形(与用户截图一致)。
- **教训**: 第一轮"几何无缺陷"结论已回改坑档 —— 症状「位置错 + 看不清」不应因"同时说颜色看不清"就跳过几何验证, 且几何验证要验"画出的形状是否等于目标形状", 而非"两段代码是否等价"(等价可能一起错)。
