# Structure and Style — Native HTML 的四根轴

> 通用原理,不绑定形态。被 `native-html.md` / `magazine.md` 引用。
> Stage 形态(`position:fixed` 视口锁定)已由 `SKILL.md` 第一步路由到 `references/huashu-design/`,本文档**只管 Scroll 半边**。
> 来源标注:🟢 排版学/Web 共识 · 🔵 实证观察(open-design 等) · 🟡 本文档合成 · 🟠 经验拍脑袋

Native HTML 的设计空间沿四根独立可变的轴铺开。决定 native 文档「长什么样」就是在这四根轴上各选一档:

| 轴 | 取值 | 在哪决策 |
|---|---|---|
| **Viewport** | Scroll / ~~Stage~~ | Stage 已路由 huashu,本文档只管 Scroll |
| **Navigation** | Linear / Branching | 下面 §Navigation 决策树 |
| **Content** | Prose / Data / Visual | 下面 §Content:reading measure vs canvas width |
| **Style** | 暖人文 / 冷技术 / Swiss editorial / 印刷期刊 / …… | 下面 §Style,不强枚举 |

> 🟢 「四轴正交」依据:Explore subagent 跨 200+ HTML 样本(open-design / html-effectiveness / huashu-design)归纳。Viewport × Navigation × Content 三轴严格独立(每根选定后另两根仍可任选)。Style 是第四维但软约束 —— 不当格子来填,当"调色盘"来挑。

---

## Navigation 决策树:Linear or Branching

触发**任一条件**就走 Branching(sticky left TOC + main):

- 章节 ≥ 4(用户能数得过来 = 不需要 nav;数不过来 = 需要)
- 用户提到「目录 / TOC / 章节导航 / 索引」
- 内容是技术文档 / API 文档 / 多层级手册 / 长 explainer
- 同一文档会被反复访问(reference doc),不是一次性读完

否则走 Linear(单列顺读)。

参考范型:
- Scroll × Branching × Prose:`references/native-examples/docs-page.html`(utility tech)、`proposal-swiss-editorial.html`(Swiss editorial,同结构不同风)
- 反例(不走 Branching):`eng-runbook.html` —— 技术内容但章节 ≤ 3,顺读即可,加 nav = overkill
- **变体 · Linear + 右栏 marginalia**:`research-concept-explainer.html` —— 主流是顺读,但右栏放术语 glossary / 定义引用(不是 nav),适合术语密集的研究 explainer。`grid-template-columns: 1fr 240px`,右栏 `position: sticky`

CSS 约定(可直接套或按场景另命名):

```css
:root {
  --nav-width:  clamp(200px, 18vw, 260px);
  --main-width: minmax(0, 1fr);
  --rail-width: clamp(180px, 16vw, 220px);  /* 可选第三栏 mini-TOC */
}

.layout-branching {
  display: grid;
  grid-template-columns: var(--nav-width) var(--main-width);
  min-height: 100vh;
}
.layout-branching.with-rail {
  grid-template-columns: var(--nav-width) var(--main-width) var(--rail-width);
}
.layout-branching > .sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow-y: auto;
  border-right: 1px solid var(--rule-soft);
}

/* 窄屏塌成单列,藏侧栏 */
@media (max-width: 980px) {
  .layout-branching,
  .layout-branching.with-rail { grid-template-columns: 1fr; }
  .layout-branching > .sidebar { display: none; }
}
```

> 🔵 240/1fr/220 三栏比例 = open-design `docs-page/example.html:17`;240 nav + 1fr 主 = 本仓库 `proposal-swiss-editorial.html` 实测可用区间。
> 🟡 `clamp(200px, 18vw, 260px)` 三个数字是经验区间,可调。

侧栏 nav 的硬约束:**只放导航树,不放 metric / status / KPI 卡** —— 一放就倒退成 dashboard,违反 `SKILL.md` 第三步硬约束。

---

## Content 轴:Reading measure vs Canvas width

排版里的"宽度"不是一个数,是**两个不同维度的数**搅在一起。把它们分开是这一节的核心。

### The core distinction

**Reading measure(读宽度)** 和 **Canvas width(画布宽度)** 是两件事:

| 概念 | 单位 | 典型值 | 服务对象 |
|---|---|---|---|
| Reading measure | `ch`(字符宽) | 50–75ch ≈ 600–720px | **人眼**:回行时不丢失位置 |
| Canvas width | `px` | 1080–1280px | **屏幕**:让表格/网格/图表能呼吸 |

把两个搅在一起 = 要么散文不好读(全屏 130 字/行),要么数据被压扁(表格塞进 720px 多行换行)。

> 🟢 Reading measure 与 50–75 字/行的依据:Bringhurst《The Elements of Typographic Style》§3.2.7,排版学经典准则,被现代 web typography 全盘继承。
> 🟡 Canvas 这个术语是本文档为对照 measure 引入的命名,借自 Figma / Sketch 的"画布"语义。排版学经典里没有直接对应词。

### When to apply which

按**主导内容类型**选画布;**散文段落**始终独立锁 measure(只是有时候段落 = 整个画布,有时候只是画布里的一个块)。

| 内容类型 | 画布宽 | 段落用 measure? | 典型产物 |
|---|---|---|---|
| 散文主导(Prose) | = measure(≈ 720px) | 是 | Letter / 长文 / 信函 / 杂志风 |
| 数据主导(Data) | ≈ 1180px(canvas) | 否 —— 段落随表格走 | 财报 / 矩阵 / benchmark |
| 混合 | ≈ 1180px(canvas) | **是**,但表格用 `.bleed` 突破 | 投研 / White paper |

判定 3 问(LLM 自查):

1. 内容里有 ≥ 5 列表格 / 多图表 / KPI 网格吗?→ 数据画布
2. 内容是 80%+ 连贯段落吗?→ 散文画布
3. 都有?→ 混合(画布宽 + 段落锁 measure + 表格 `.bleed`)

> 🔵 数值来源:1180px ≈ Tailwind `max-w-6xl`(open-design `skills/data-report/example.html:24` 实际用值);720px ≈ open-design `skills/article-magazine/example.html:25` 实际用值(`max-w-[720px]`);65ch 来自 Bringhurst。
> 🟡 3 问决策树是本文档原创合成 —— open-design 通过"拆 skill"解决同样问题(article-magazine 与 data-report 是两个独立 skill,各有自己宽度规则,不需要决策树)。我们走单 skill 路线,所以在 skill 内分支。
> 🟠 "80% 连贯段落"的 80% 阈值是经验估计,可调。

### CSS 约定(escape hatch)

不强制 class 名 —— Native HTML 是 prototype-skill,LLM 可以另起命名。下面是**推荐约定**,因为它把上面三档跟 CSS 一一对上:

```css
:root {
  --measure: 65ch;
  --canvas:  clamp(960px, 92vw, 1180px);
  --gutter:  clamp(16px, 4vw, 48px);
}

/* 主容器三选一 */
.layout-prose {
  max-width: var(--measure);
  margin-inline: auto;
  padding-inline: var(--gutter);
}
.layout-canvas {
  max-width: var(--canvas);
  margin-inline: auto;
  padding-inline: var(--gutter);
}

/* 混合型:外层 canvas,内嵌散文块另套 measure */
.layout-canvas > .prose-block {
  max-width: var(--measure);
  margin-inline: auto;
}

/* escape hatch:套在 prose 容器内部,让单个元素全宽突破 */
.layout-prose .bleed,
.prose-block  .bleed {
  max-width: none;
  margin-inline: calc(-1 * var(--gutter));
}
```

用法示例(混合型):

```html
<main class="layout-canvas">
  <article class="prose-block">
    <p>这段散文锁 65ch,读起来舒服。</p>
    <figure class="bleed">
      <table>...一张 8 列的财务表,突破 65ch...</table>
    </figure>
    <p>表格之后回到 65ch 散文。</p>
  </article>
</main>
```

`.bleed` 用在 **figure / div 包表格或图表**,不要用在段落本身 —— 段落突破 65ch 就是反例(回行困难)。

> 🟢 `clamp()` / `margin-inline`(logical properties)是 W3C CSS 标准,浏览器支持 97%+(caniuse 2026)。
> 🔵 `.bleed` 命名借鉴 Andy Bell 的 "Every Layout" 与 Tailwind 社区惯用的 `full-bleed`;open-design `plugins/_official/examples/motion-frames/SKILL.md` 也使用过 "full-bleed" 一词,但未给出标准 class。
> 🟠 `clamp(960px, 92vw, 1180px)` 三个具体数字是经验值:下界 960px(避免小屏过窄)、上界 1180px(open-design data-report 的 6xl 略收紧)、92vw 是中间响应区间的拍脑袋值。都可调,LLM 也可按场景另选。

---

## Style 是真·第四维,但不强枚举

Style(调性 / 视觉签名)跟前三轴正交 —— 同一个 Scroll × Linear × Prose 格子里,可以是 kami 暖人文、可以是 runbook 冷技术、可以是 Swiss editorial、可以是 brutalist、可以是任何尚未发明的方向。**结构不决定风格**。

但 Style **不强枚举入决策树** —— 风格是无穷可能的设计选择,不是有限格子。原则:

1. 走 `native-html.md` 第一步「认定方向」与用户对齐 —— 这是 style 决策入口。
2. 看 `references/native-examples/SOURCE.md` 各范型的 Style 列,挑一种最贴合的当起点,**学其视觉系统而非复制其内容**。
3. 范型库没覆盖到的方向(比如 brutalist / Bauhaus / Art Deco / 北欧极简),按 `native-html.md` 第三步通用工艺(排版 / 配色 / 构图 / 质感)从零执行。
4. 后续若某个新风向反复出现,且能找到一份高质量样本满足 `native-examples/SOURCE.md` 的「收 / 不收的门槛」,就 vendor 进库。**慢慢扩,不预设穷举**。

> 🟡 Style 不进矩阵但显式入库 —— 这是 Explore subagent 报告里被我撤回的判断后做的修正:subagent 起初判 style 是「结构选定后派生」,这站不住(同结构可承载多种风格),但 style 也确实不是结构那种有限枚举,所以待遇是「真维度 + 软处理」。

---

## Anti-patterns

- **整篇 `max-width: 65ch`,里头硬塞 8 列表格** —— 表格被压成多行换行。
  正解:整体走 `.layout-canvas`,段落另套 `.prose-block`。
- **整篇 `max-width: 100%`,散文拉满 130 字/行** —— 眼睛会累。
  正解:走 `.layout-canvas`,但段落仍要 measure 包裹。
- **用 `.bleed` 包整段长文** —— 失去 measure 保护,等同上一条。
- **在杂志风里突破 65ch** —— 杂志风的视觉签名就是窄栏,破栏就破气质。混合型内容请直接走 Native HTML 而非杂志风。
- **Stage 模式混入 Scroll 文档** —— Native 文档绝不用 `position:fixed` + absolute 全屏定位。那是 Stage 形态(kiosk / 原型 / 海报),已路由到 `references/huashu-design/`,不在本文档管辖。
- **侧栏 nav 带数据 KPI 卡** —— Branching 形态的侧栏只放导航树,不放 metric / status / KPI。

---

## Lint(自检)

- [ ] Viewport 是 Scroll(没有 `position:fixed; inset:0` 的全屏舞台 root)
- [ ] Navigation 决策树命中条件成立时,走了 Branching(章节 ≥ 4 / 长技术文档 / 用户提目录 → 有 sticky TOC)
- [ ] 散文段落实际行长 50–75 字之间(中英文都算字)
- [ ] 表格 / 图表 / KPI 网格的水平利用率 ≥ 80%(没被框死多行换行)
- [ ] 1920px 屏幕上,主容器两侧总留白 ≤ 屏宽 35% 🟠 经验值
- [ ] `.bleed` 只用在 figure / div 上,没用在 `<p>` 上 (guidance)
- [ ] 侧栏只放导航,没放 KPI / metric 卡
- [ ] Style 跟 `native-examples/` 某份范型对齐(或明确按 native-html.md 第三步从零执行),不是混搭多种风格
