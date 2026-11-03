# 26-11-04-webui-fx-glow — fx 辉光荧光化四轮修(雾/圆角/无辐射/角缺光)

**Status:** Done
**Added:** 2026-11-04
**Updated:** 2026-11-04
**Summary:** fx 按钮辉光四轮修: 根因双叠(glass 辉光色源 --accent-ink 在 flux 未定义→落 currentColor 灰白/暗雾 + 单层 12px blur 无芯无负spread)与三层物理约束(blur 圆角/负spread环角缺光), 终版=硬芯0blur + 正spread扩方四层; 配色公式落 fx.css * 通用层逐元素现算 ink(danger 重挂 error), 供给面改标量
**Topics:** webui-fx-glow
**Refs:** memory-bank/pitfalls/web-ui/css-var-substitution-level.md

## 原始请求

1. 「WEBUI弹窗中的按钮大辉光动效效果需要调整(如添加/删除种子弹窗的"取消"按钮), 该动效应统一写在一处, 改动需覆盖所有有问题的元素, 如果不是及时报告; 辉光没有做到荧光发亮的感觉反而是雾蒙蒙的, 聚到一起。改完后起桩让我验收」
2. 「还有个问题, 荧光是弧形, 按钮看起来像圆角, 不符合皮肤的风格(方角), 需要调整」
3. 「没有散发荧光了, 目前仅一个荧光色方框」(二修过紧)
4. 「又回到圆角的问题了, 只是弱了; 四个角没有荧光或很弱, 边上的荧光整体呈弧形」
5. 「提交」

## 思考过程与决策

- **根因双叠**(一轮定位): ①glass 辉光色源 `var(--accent-ink, currentColor)` 的 `--accent-ink` 只有 showcase 演示页定义, flux 从未定义 → 全落 currentColor: ghost 钮(浅灰白字)发灰白雾、danger-solid(深字 --on-error)发暗雾; ②单层 `0 0 12px` 半透明阴影无亮芯、无负 spread, 衰减均匀 = 雾。
- **单点架构**: 配色公式一个落点(`fx.css` `*` 通用层), 消费方(fx.css glow 原语 / fx-mount.css .bt 与 chip / showcase 镜像与 ctl.on/hsp-glow/pc-sig-bar)一律取 `var(--fx-glow-stack)` 整体, 不得拆层重拼; preset 只供标量(半径/ink/两层 alpha), 不再供算好的颜色。
- **D1(关键架构修)**: 自定义属性 var() 代入发生在**声明元素**上 —— 颜色槽(:root/preset 算死)挡住组件层按变体换色(danger 要红)。实测撞坑后把公式从 :root 挪到 `*` 通用层逐元素现算, ink 重挂即时生效(详见 pitfalls/web-ui/css-var-substitution-level.md)。
- **D2 色源**: ink 缺省 `--accent-hi`(四皮肤对等令牌); danger/danger-solid 在 flux 挂载层重挂 `--fx-glow-ink: var(--error)`。
- **D3-D5 形状三轮**: blur 圆角物理(box-shadow blur 是环形光源扩散, 角部对角线距离远天然缺光): ①芯层 0 blur 硬边锚方角; ②纯负 spread 环辐射感归零; ③终版 = 硬芯 + 正 spread 扩方三层(角半径=spread 仅 1-3px, 角部被填充照亮, 沿周边亮度均匀)。层尺寸全部从供给半径派生(g/4、g/2、g、g/12), 关档(g=0)时 blur+spread 双 0 不落笔。
- **覆盖面核过**: .bt 六变体 / chip 三类 / showcase 镜像全走 stack; 进度条微辉光(本就负 spread 紧配方)、danger 弹窗一次性脉冲(400ms 瞬态)、showcase 页自身 neon 氛围装饰(仅演示页)评估后不属于问题元素, 未动。
- **弹窗确认钮青圈**: 脚本自动聚焦触发全局 `:focus-visible` accent 外环, 存量既有行为与辉光无关, 未动(已报告用户)。

## 实现计划

1. fx.css: 供给面标量化(--fx-glow/--fx-glow-ink/--fx-glow-a/--fx-glow-a-hi) + `*` 通用层配色公式 + glow 原语改消费 stack
2. fx-presets.css: neon/glass/crisp/兜底四块改标量供给; glass ink=--accent-hi
3. fx-mount.css: .bt 悬停合成 `var(--glow-soft/-glow), var(--fx-glow-stack)`; danger 变体 ink 重挂; chip 改 stack
4. showcase.html: 补 --accent-hi、force-glow 改标量、镜像/ctl.on/hsp-glow/pc-sig-bar 对齐
5. Playwright 真浏览器 hover 三变体截图验证(ghost/primary/danger-solid) + test.quick + test.full 基线

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 根因定位(色源断+单层配方)与覆盖面盘点 | Done(2026-11-04) |
| 2 | fx.css/fx-presets.css/fx-mount.css/showcase.html 四件改单点配方 | Done(2026-11-04) |
| 3 | 真浏览器三变体渲染验证(四轮迭代) | Done(2026-11-04) |
| 4 | test.full 基线切片 + 坑档入库 + 提交 | Done(2026-11-04) |

## 进度日志

### R0 · 立档 (2026-11-04)

- 一轮: 根因双叠定位, 单层改三层荧光(芯/晕/泛光) + 色源挂 --fx-glow-ink 钩子; 真浏览器验证 ghost/danger 渲染, 发现 danger 重挂不生效 → 定位 var() 代入层级问题, 公式挪 `*` 通用层; test.quick 全绿。
- 二轮(用户报「辉光弧形像圆角」): 芯层 1px blur → 0 blur 硬边; 柔光负 spread 收紧; 辐射感损失(用户报「只剩荧光方框」)。
- 三轮: 回补多层小步衰减(3px blur 紧贴层), 辐射回来但角仍缺光。
- 四轮(用户报「四角无荧光、边上呈弧形」): 柔光改正 spread 扩方, 角部填充照亮; 修层尺寸派生(关档双 0 不落笔); test.quick 全绿(5005 passed, 见 kb.baseline), 用户验收通过, 提交。

- 2026-11-04 01:52 fx 辉光四轮修入库: 单层雾配方→四层方角霓虹(硬芯0blur+正spread扩方), 色源挂 ink 钩子(glass=accent-hi/danger重挂error), 配色公式落 * 通用层修 var 代入层级; 全量基线 26-11-04-0151
