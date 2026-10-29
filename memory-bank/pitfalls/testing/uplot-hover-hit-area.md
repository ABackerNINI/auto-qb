# uPlot 悬停类断言: 参考盒必须是 `.u-over`, 不是画布宿主

> 摘要: 给 uPlot 图写「悬停第 N 个桶」类 e2e 断言时, 拿宿主 `.qb-chart-host` 的盒子推像素会落到**交互面之外** —— uPlot 收不到 mousemove, hoverIdx 回落 -1, 且报错指向 tooltip 而非几何、看不出病因; 真正的交互面是宿主内那个 `.u-over`(实测宿主宽 1382px 时它从 x+84 起、宽 1273)。等距栅格下桶 index 与 px 严格线性, 两点标定即能解出任意桶的落点。
> 触发: 悬停断言, hoverIdx -1, 落点到图外, u-over, qb-chart-host, uPlot 交互面, 纵轴槽, 84px, 桶 index 转 px, 两点标定, e2e 点画布, tooltip 不出现
**Refs:** memory-bank/testing/baselines/26-10-30-0251-webui-traffic-gap-zone-tips.md

### 宿主盒 ≠ 画布的可悬停面: 纵轴槽与 x 轴槽都不接收 mousemove

- **触发**: `e2e/traffic-gap-zones.spec.mjs` 首跑(2026-10-30 缺口分区段文案守阵)—— 参考盒取
  `.qb-chart-host`, 右探头用 `box.x + box.width - 4`, 结果 `hoverIdx = -1`, 双皮肤四条例全红在
  同一条标定断言上。
- **判别**: uPlot 的鼠标监听挂在 `.u-over` 上, 而这个元素**不是**宿主满幅 —— 实测它自带内联样式
  `left: 84px; top: 17px; width: 1273px; height: 204px`(84 = y 轴槽宽, 来自 options 里写死的
  `size: 84`)。宿主宽 1382px, 于是左侧 84px 与右侧约 109px 都**不接受**悬停: 鼠标到那里 uPlot
  触发的是 mouseleave ⇒ `cursor.idx == null` ⇒ setCursor 钩子把 scope 化 hoverIdx 写回 -1。
  最坑的一步不是「取不到值」而是「悄无声息取到 -1」: 后续断言等到超时, 报错指向 tooltip 而不是
  几何 —— 在同一个 60 桶的图上, 落在 over 内还剩最后一像素时能拿到 idx 59, 越界一像素就 -1,
  这种"边缘效应"最容易被误判成 flaky。
- **处置**: 参考盒一律取 `.qb-chart-host .u-over`(一个抽屉挂点上本就一张图, uPlot 每图恒定生成
  一个 u-over, 定位器不会多命中); 标定探头在两端各留 2px, 不出 over。
- **守阵**: 上述 spec 的 `hoverBucket()` 自带两点标定 + 命中回读 —— 几何再变(换皮肤 / 换窗口 /
  加右侧轴)会先在「标定必不成立」这一步红, 且报错带左右探头的实际 px 与 idx; 不会退化成
  tooltip 超时那种看不出病因的红。

### 桶 index -> px 用两点标定, 不要按公式反推

- **触发**: 要把鼠标送到第 N 个桶上, 而 uPlot 的 x 尺取值域、轴槽宽、devicePixelRatio 三样都不
  打算让调用方去猜。
- **判别**: raw / hour 段窗的栅格是等距的 ⇒ (桶 index, px) 严格线性, 两点即定标。同一张图上实测:
  over 内 54px 落在 idx 3、1159px 落在 idx 54 —— 用这两点线性解出的落点, 回读 hoverIdx 与目标
  逐桶一致。
- **处置**: 左探头 -> idx_a、右探头 -> idx_b, 目标 `x = xa + (target - ia) * (xb - xa) / (ib - ia)`;
  **落点后必须回读 hoverIdx 并断言命中** —— 「我正点在哪一桶」在 DOM 上没有第二路证据, 光看
  tooltip 的时刻会被 fmtTime 粒度与桶宽遮住(相邻两桶可能打出同一个刻度)。
- **复发**: 1 次(2026-10-30 首跑四红, 换 over 盒后四绿)。
