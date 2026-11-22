# 状态色 (0,4,0) 压掉后置 tone (0,3,0): 源顺序只在同特异度才生效

> 摘要: 数值档位色(`.tone-low`/`.tone-high`)写在状态色规则**之后**并不自动胜出 —— 状态色 `.group-row.s-* .g-stat:not(.zero)` 是 (0,4,0), 裸 tone `.group-row .g-stat.tone-*` 只有 (0,3,0), 低特异度者无论源顺序多靠后都被压住。issue 26-11-20-0404 根因即「注释误判为写后即覆盖」, 种子/组行状态行上 numTone 两档恒不生效; 修法是用单条 `:is()` 举齐状态把 tone 提到 (0,4,0), 保留裸选择器兜无状态行, 写在状态规则之后靠源序胜出(显式档位 (0,4,1) 仍压 tone)。
> 触发: CSS 级联, 特异度, 源顺序, tone 色阶, numTone, 状态文字色, group-row, 计算色, :is(), 静态守阵
> 收口: 2026-11-22, issue 26-11-20-0404 四皮肤原位提特异度 + 静态守阵 + e2e 计算色; issue Done
**Refs:** memory-bank/tasks/26-11-20-webui-column-style.md

## 条目

- **触发**: 细粒度修饰类(数值档位/徽标色等)加在带状态类的行内元素上, 靠「写在后面」指望覆盖状态类规则; 两条选择器 class 数不等。
- **判别**: 真浏览器 `getComputedStyle` 看到状态行上拿到的是状态文字色而不是档位色; 静态判别按 class 计数比对 —— 状态色 `.group-row.s-* .g-stat:not(.zero)` = (0,4,0), 裸 tone `.group-row .g-stat.tone-*` = (0,3,0), 后者源序再后也不可能胜出。别信旧注释「写在状态色之后(源顺序胜出)」。
- **处置**: 修饰类选择器补到同等特异度 —— 单条 `:is()` 列齐全部状态(每个 `:is()` 只算一个类)即可等效枚举多条全写选择器; 保留裸兜底选择器覆盖无状态行, 且置于状态规则之后。已有更高特异度的用户显式规则(如 `console_hub.css` 的 csp/cst (0,4,1))不需要动, 继续压修饰类, 保证显式选择优先。
- **守阵**: `tests/test_webui_static_skins_skin.py::test_frontend_tone_cascade_beats_state_color` 校验七状态全集 / `var(--token)` 全名精确比 / 后置且 class 特异度 ≥ 状态规则; `e2e/colstyle.spec.mjs` tone 用例在四皮肤真浏览器验 computed color。
- **复发**: 0(2026-11-20 首次入池, 2026-11-22 修复; 路由到级联特异度判据后才定位)
