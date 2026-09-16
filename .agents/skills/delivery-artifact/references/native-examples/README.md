# native-examples · 范型,不是模板

这里的 `.html` 是**范型(archetype)** —— 给你看「一份排过版的好东西」长什么样、版式怎么呼吸、品质标准在哪里。

**读它们,不要 copy 它们。** 读完为手上的产物**从零设计、从零生成**(方法见 `../native-html.md`)。

6 份范型沿 Viewport × Navigation × Content × Style **四轴**铺,外加可选**附加能力**(嵌 widget / marginalia)。LLM 看见 Native 的设计空间不止一根轴:

| 文件 | 结构(V × N × C) | Style | 能力 |
|---|---|---|---|
| `doc-kami-parchment.html` | Scroll × Linear × Prose | 暖人文 · serif + parchment | —— |
| `eng-runbook.html` | Scroll × Linear × Prose | 冷技术 · dark + mono | —— |
| `docs-page.html` | Scroll × Branching × Prose | utility tech · sans + pill | —— |
| `clinical-case-report.html` | Scroll × Linear × Data | 印刷期刊 · Georgia + hairline | —— |
| `proposal-swiss-editorial.html` | Scroll × Branching × Prose | Swiss editorial · IKB + 暖纸 | —— |
| `research-concept-explainer.html` | Scroll × Linear × Prose | research explainer · serif + clay + 微圆角 | **嵌 widget** + 右栏 marginalia |

观察:
- `docs-page` 与 `proposal-swiss-editorial` **结构同格、调性不同** —— 同骨架可承载不同 style。
- `kami` / `runbook` / `research-explainer` **结构同格、调性 + 能力各异** —— 同结构里能装暖人文叙事、冷技术运维、研究 explainer + 嵌 widget,证明同一格子内的差异空间。

它们守同一套普适工艺(排版 / 配色 / 构图 / 质感、反 AI slop),却长得毫无共同点 —— 这就是 Native 的关键:**没有唯一的「Native 样子」,按产物认定方向 + 选对结构骨架 + 看是否需要嵌 widget。**

照抄任意一份 = 回到「太模板化」,P0 自检会打回。

来源、各份的「不要照抄」局部反模式、收 / 不收的门槛,见 `SOURCE.md`。
