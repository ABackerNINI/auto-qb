# CSS 自定义属性的 var() 代入发生在声明元素, 组件层重挂"原料令牌"追不回已算死的颜色

> 摘要: 把「配方颜色」当供给槽在 :root/preset 层算死(如 `--fx-glow-c: color-mix(... var(--accent-ink) ...)` 写在 html 的 preset 块), 再指望组件层重挂原料令牌(`.bt.danger { --fx-glow-ink: var(--error) }`)换色 —— **必然落空**: var() 的代入发生在**声明该属性的元素**上, --fx-glow-c 在 <html> 层就替换成了 accent 色, 后代元素继承的是**算好的计算值**, 自己重挂 --fx-glow-ink 改变不了任何已算死的下游令牌(2026-11-04 fx 辉光四轮修实测: danger-solid 悬停仍发 accent 青光, getComputedStyle 看 ink=红而 boxShadow=青)。定稿修法: 配色公式从 :root/preset 挪到 `*` 通用层 —— 每个元素用自己的原料令牌现算, preset 只供标量(半径/ink/alpha), 组件层按变体重挂 ink 即时生效。
> 触发: 主题换色, 按变体换色, danger 换红, 皮肤令牌, preset 配方, 重挂令牌, ink 钩子, getComputedStyle 不一致, 计算值不更新, color-mix 变量, --fx-glow, fx-presets, 组件配方换色
> 收口: 2026-11-04, fx.css 辉光配色公式落 `*` 通用层(fx-glow-stack 三层荧光配方单点), 供给面标量化
**Refs:** memory-bank/tasks/26-11-04-webui-fx-glow.md

## 条目

- **触发**: 任何「preset/:root 层定义派生颜色令牌(值里引用别的令牌) + 后代组件想按自己的变体/状态重定义原料令牌来换色」的组合。典型: 皮肤层配方(hover 辉光/focus 环/语义染色)想按按钮变体(primary 青/danger 红)取不同墨色。
- **判别**: 症状 = 元素上 `getComputedStyle(el).getPropertyValue(<原料令牌>)` 已是新值, 但消费它的属性(box-shadow/color/...)仍是旧值; 或 `getPropertyValue(<派生颜色令牌>)` 在该元素上返回的仍是 html 层算死的值。盘查口诀: **var() 在哪声明就在哪代入** —— 派生令牌声明在 :root/preset 块(都落在 <html>), 后代只能继承计算结果。
- **处置**: 配色公式下放到 `*` 通用层(fx.css 辉光段体例: 派生令牌声明在 `*`, 每元素用继承来的原料标量现算), 原料(ink/alpha/半径)全部标量化供 preset 声明; 组件层重挂原料即生效。注意配套两点: ①关档判据别依赖颜色(transparent)以外的尺寸 —— 层尺寸须从标量派生使关档时 blur+spread 双 0 不落笔; ②`*` 声明的派生令牌会被更高特异性的同名声明覆盖, preset 块里**不得**再声明派生颜色(半套替换 = 代入层级回退)。
- **守阵**: 无静态守阵(浏览器计算值行为, pytest 摸不到); 判别靠真浏览器 getComputedStyle(managed 桩 + Playwright evaluate)。
- **复发**: 1(2026-11-04 首撞: 一轮把 stack 公式放 :root, danger 重挂 ink 落空, 二轮才发现 —— 路由没到, 坑当时不存在; 记档防再踩)
