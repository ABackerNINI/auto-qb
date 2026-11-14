# CSS zoom 坐标空间错配: gBR/scrollY 一族是视觉空间, style.height 是布局空间

> 摘要: html{zoom!=1}(分数布局)下窗口化几何输入 window.scrollY / scrollHeight / getBoundingClientRect 全按**视觉空间**(缩放后)报数, 而占位件 style.height / getComputedStyle().height / computed rowGap 是**布局空间**(缩放前) —— 前缀和(视觉)直接写进 style 会再被 zoom 缩一遍, pad 恒短 (1-z) 倍, 贴文档底后 padTop 差约 (1-z)×视觉总高(flux 实测 ~1900px), 渲染行整体落在视口上方全不可见。窗口选行与前缀和在视觉空间内自洽, pad 是唯一不闭环出口, 所以错位只在文档底附近爆发、scrollBy ±1 跟随但不自愈。
> 触发: zoom 0.9, 分数布局, DPR 1.25, 窗口化错位, 行全在视口上方, 贴文档底, pad 短一截, getBoundingClientRect 视觉空间, offsetHeight 取整, computed zoom 不继承, style.height 布局空间, rowGap 布局

**Refs:** memory-bank/issues/26-11-14-0844-bug-webui-zoom-window-misalign.html, memory-bank/tasks/26-11-14-webui-row-window-zoom.md

### 实测坐标空间模型(Chrome, 2026-11-14, html{zoom:0.9} 探针)

- **触发**: `documentElement.style.zoom != 1`(T8 用例、用户样式表、缩放扩展; 浏览器 Ctrl 缩放/系统 DPR **不走 CSS zoom**, CSS px 全程同一空间, 不触发) + 行窗口化 pad 写入(`style.height`)与视觉空间前缀和同链路 —— 贴文档底后 padTop 差约 (1-z)×视觉总高, 错位随滚动深度线性增长, 文档底附近爆发。
- **判别**: zoom=1 下同路径逐位正常、zoom!=1 才错 = 坐标空间错配而非取整噪声(取整是像素级, 本坑是千像素级且方向系统性朝视口上方); scrollBy ±1 后窗口跟随但不自愈。用探针页实测三问定空间归属: 同一元素 `gBR.height` vs `getComputedStyle().height`(前者视觉后者布局, 实测 39.325 vs 43.7)、`scrollY == scrollHeight - innerHeight` 是否随 zoom 缩、`getComputedStyle(子孙).zoom` 是否报继承(Chrome 恒报自身指定值)。
- **处置**: 有效缩放单点实测 `_winZoomOf` = `gBR.height / parseFloat(getComputedStyle(el).height)`(computed used 高无取整; 分母**不能用 offsetHeight** —— ±0.5px 取整按比例放大, ~1450px 容器宽上 0.034% → ~19000px 的 padTop 上 ~6px, 实测撞红 flux 像素带判据); `_rowWindow` 两个 pad 出口按 `pre[start]/z - gap` 换算(gap 本就是布局空间, 放除法之后); `_winSigExtra` 加根缩放令牌(zoom 切换后 `_winTop` 重量)。zoom=1 时 z 恒 1, 逐位零差异。新窗口化产物写 `style` 前先问空间归属。

- **视觉空间**(缩放后): `getBoundingClientRect`(行高 43.7 布局 → gBR 39.325)、`window.scrollY`(= scrollHeight - innerHeight, 随内容缩放)、`innerHeight`(不随 zoom 变)。
- **布局空间**(缩放前): `style.height` 写入值、`getComputedStyle().height/width`(used 值, **分数精度**, 实测 row 43.7 → "43.6944px")、computed `rowGap`、`offsetHeight/offsetWidth`(布局但**取整**)。
- **`getComputedStyle().zoom` 不可用于取有效缩放**: Chrome 不把 zoom 报成继承, html 设 0.9 时 body/子孙 computed 恒 "1", 读出来恒 1 会把换算整个关掉。
- 浏览器 Ctrl 缩放(系统 DPR)不触发本坑; 触发面是 `documentElement.style.zoom`(T8 用例、用户样式表、缩放扩展)。

**修法契约(已修, 2026-11-14)**

`columns_grid.js`: `_winZoomOf(kind, refName)` 单点实测有效缩放; `_rowWindow` 两个 pad 出口按 `pre[start]/z - gap` 换算(gap 本就是布局空间, 放在除法之后同单位相减); `_winSigExtra` 加根缩放令牌(zoom 切换后 `_winTop` 重量, 否则 rel 偏 (1-z)×表顶、窗口选行错约一行)。zoom=1 时 z 数值等价 1(至多浮点重结合 1ulp 差), 逐位零差异。验证: e2e/row-window-zoom.spec.mjs(三皮肤贴底可见行) + node 语义电池 23/23。

**已知权衡(勿"补全")**: `_measureRowH` 的行高签名(`_winResize|列集合`)**有意不含根缩放** —— `_rowHs` 是视觉空间(gBR 实测)值, zoom 切换后整表陈旧且不失效, 只能靠 updated() 对已渲染行的逐行重探收敛自愈(收敛前 padBottom/文档总高偏大约 (1-z)×未重探尾部高, 键盘跨窗按 `_rowPre` 换算取旧值)。**别直觉地把 zoom 令牌加进 `_measureRowH` 签名** —— 那会踩回 viewMode 曾踩过的「每次切页作废三 kind 行高全表 + 3000 行 5.8s 全量重渲长任务」坑(见 `test_frontend_row_window_sig_and_ctn_sync_guard` 守阵)。
