# uPlot 轴刻位: `.splits` 是生成器函数, 真值在 `._splits`

> 摘要: 读 uPlot x 轴刻位(tick 位置)时 `u.axes[0].splits` **不是数组**, 是生成刻位的函数(vendor 1.6.32: 绘制时 `t._splits = t.splits(...)` 回填); 拿它当数组用得到的是函数对象本身(长度/下标全错或 typeof 直接炸), 真·刻位数组在 `u.axes[0]._splits`(每次绘制回填的网格/轴标同源真值)。读 `._splits` 只读运行态回填值, 不碰生产内部, e2e 可用。
> 触发: uPlot axes, splits, _splits, 刻位真值, tick 位置, split 集, 网格刻度, 生成器函数, vendor 1.6.32, 轴标断言, split 数恒定

**Refs:** memory-bank/plans/26-11-14-1313-plan-webui-traffic-beat-fidelity.html, memory-bank/tasks/26-11-15-webui-traffic-beat-fidelity.md

### 「split 数/首刻位」断言读 `._splits`, 别读 `.splits`

- **触发**: `e2e/traffic-grid-stability.spec.mjs` 的 A4 用例(F3 栅格 floor+1 后「split 集稳定」判据: 逐帧 split 数恒定 + 首刻位不回跳)首写时(2026-11-14)直接读 `u.axes[0].splits`。
- **判别**: vendor uPlot 1.6.32 源里 x 轴刻位流向是 `t._splits = t.splits(...)`(绘制时调用配置的 splits **函数**生成数组回填到 `_splits`), 所以 `u.axes[0].splits` 是函数、`u.axes[0]._splits` 才是上次绘制回填的真值数组。踩到的形态: `splits.length` 拿到的是函数形参个数(不是刻位数)、`splits[0]` 是 undefined 或函数体 —— 不报错但数字荒谬, 容易被误读成「uPlot 行为怪」; 首跑前的空态 `_splits` 可能是 undefined(图未绘制过), 采样器要判空。
- **处置**: 断言一律 `u.axes[0]._splits`(判空后取 length/[0]); 这是只读运行态回填值, 与 vm 内部时序探针同类, 不算碰生产内部。刻位稳定性判据(逐帧长度恒定 + 首刻位单调)配合栅格桩压缩轮询使用, 见 grid-stability spec 的 rAF 采样器。
- **关联**: 悬停/落点类断言的 uPlot 交互面(参考盒取 `.u-over`)单点在 [uplot-hover-hit-area.md](uplot-hover-hit-area.md) —— 同族不同面: 那条管「鼠标往哪点」, 这条管「刻位从哪读」。
