# 杂志风

> **适用前提**：内容是散文主导的长文阅读。如果内容是数据矩阵 / 多表格 / KPI 网格 / 财务报告，**改走 Native HTML 的 canvas 画布**（见 `references/native-html.md` 第二步半 + `craft/structure-and-style.md`），不要硬塞进杂志风的 65ch / 720px。

竖向滚动的 editorial 长文 —— 写得像一本被排过版的杂志内页：serif 大标题、单栏窄正文、图文混排、有叙事弧。蓝本：open-design / article-magazine（受 huashu-md-html 启发）。

**视觉骨架**：`assets/magazine-template.html`。`<style>` 是焊死的设计系统（配色 / 字体 / class），body 里是版式积木（信息卡 / kicker / hero / 导语 / 署名行 / 章节 / 引用块 / ornament / 收尾卡）。copy 骨架 → 按下面的版式说明，用积木自由取舍、增删、重组 → 不碰 `<style>`。

## 视觉签名（不许改）

- **画布**：暖白纸 `#fafaf7`（永不用纯白 `#fff`）；卡片次级背景 `#ffffff` 半透明。
- **墨色**：标题 `#1a1a1a`；正文 `#262421`（近黑暖灰）；次文字 `#6b6760`。
- **唯一 accent**：陶土红 `#b8553a` —— 链接 / 引用左边线 / kicker 小字 / drop cap / 自定义 bullet 只能用这一个色。`--twitter` 蓝仅服务信息卡图标，不当第二 accent 用。
- **字体**：标题 serif `Noto Serif SC`（500/700/900）；正文 sans `Inter` + `Noto Sans SC`（300/400/500/600）。serif 标题 vs sans 正文的对比是杂志风的核心签名，不许全篇统一成一种。
- **正文度量**：字号 `1.0625rem`、行高 `1.8`、限宽 `65ch`；单栏居中，文章容器 `max-width 720px`。**这是杂志风的视觉签名，不要破** —— 想破栏意味着选错形态了，见 `craft/structure-and-style.md`。
- **H2**：`1.875rem`、serif、700。
- **质感**：`.grain` 给页面铺一层极淡的 radial 颗粒纹（焊在 `<style>` 里，body 挂 `class="grain"` 即生效）。
- **圆角例外**：杂志风允许卡片 / 代码块用圆角（`rounded-2xl` / `rounded`）——这是本形态在 `<style>` 里明确开的口子，照用，不要改成直角。

## 版式说明（按内容判断，挑积木搭）

- **hero 区** — kicker 一行 + serif 大标题（关键处点一个 accent 词）+ 导语 + 署名行，底部 hairline 收口。每篇必有。
- **信息卡** — hero 之上的引用卡：引用外部出处 / 关联资料时用；纯原创文章删掉。
- **章节** — h2 + 若干正文段。第一章首段可做一次 drop cap（句首单字 serif 大字下沉），全文只用一次。
- **引用块 / 行内代码** — blockquote 自动套左侧 accent 边线 + 斜体；行内代码用 `code` 占位。
- **ornament** — 章节之间的居中小装饰，用来切换叙事节奏，不必每节都加。
- **收尾卡** — 文末行动号召 / 致谢卡，可删。

## 形态准则

- 当成一本杂志内页排，不是网页 —— 叙事有起承转合，靠 ornament 和章节切节奏。
- 层级靠 **serif/sans 对比 + 字号 + 留白**，accent 色只点睛，不铺面。
- drop cap、pull quote 是点缀，克制使用：一篇一个 drop cap，引用块不堆。
- 正文严守 `65ch` 限宽，宁窄勿宽，保证阅读节奏。
- 不用 emoji 当图标 / 装饰，需要图标自己写 inline SVG（见收尾卡）；正文引用的内容里本就带 emoji 不必强删。
- 中英混排加盘古之白（中英文之间留空格）。

通用禁律（去 AI 感 + 工程约束）见 `SKILL.md` 第三步，此处不重复。
