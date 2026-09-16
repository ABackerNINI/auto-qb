# native-examples · 来源与许可

本目录共 6 份范型,沿 Viewport × Navigation × Content × Style 四轴 + 附加能力(嵌 widget / marginalia)铺开。LLM 看完一遍即理解 Native HTML 的设计空间与可选能力,**读、不抄**。

## 范型清单

| 文件 | 结构(V × N × C) | Style | 附加能力 | 上游 | 许可 |
|---|---|---|---|---|---|
| `doc-kami-parchment.html` | Scroll × Linear × Prose | 暖人文 · serif + parchment | —— | `nexu-io/open-design` · `skills/doc-kami-parchment/example.html` | Apache-2.0 |
| `eng-runbook.html` | Scroll × Linear × Prose | 冷技术 · dark + mono | —— | `nexu-io/open-design` · `plugins/_official/examples/eng-runbook/example.html` | Apache-2.0 |
| `docs-page.html` | Scroll × Branching × Prose | utility tech · sans + pill | —— | `nexu-io/open-design` · `design-templates/docs-page/example.html` | Apache-2.0 |
| `clinical-case-report.html` | Scroll × Linear × Data | 印刷期刊 · Georgia + hairline | —— | `nexu-io/open-design` · `design-templates/clinical-case-report/example.html` | Apache-2.0 |
| `proposal-swiss-editorial.html` | Scroll × Branching × Prose | Swiss editorial · IKB + 暖纸 | —— | 本 skill 自产(原 native-archetype-expansion 提案) | 本仓库许可 |
| `research-concept-explainer.html` | Scroll × Linear × Prose | research explainer · serif + clay + 浅 hairline | **嵌入 widget** + 右栏 glossary marginalia | `thariqs/html-effectiveness` · `15-research-concept-explainer.html` | Apache-2.0 |

> docs-page 与 proposal-swiss-editorial **结构同格、调性不同** —— 同骨架可承载不同 style。
> kami / runbook / research-explainer **结构同格(Scroll×Linear×Prose)、调性 + 能力各异** —— 同结构里能装暖人文叙事、冷技术运维、研究 explainer + 嵌 widget,证明同一格子内的差异空间。

## 上游同步

`open-design` 拉取信息:

- 仓库:https://github.com/nexu-io/open-design
- 同步 commit:`69469c639e2411f1b61bf0f0cf951b73f91cce5d`(2026-05-20)
- 拉取日期:2026-05-22(kami / runbook)· 2026-05-25(docs-page / clinical-case-report)
- 改动:**无** —— 4 份均原样收录。

`thariqs/html-effectiveness` 拉取信息(同 Apache-2.0,共用本目录 `LICENSE`):

- 仓库:https://github.com/thariqs/html-effectiveness
- 上游文件:`15-research-concept-explainer.html`
- 拉取日期:2026-05-25
- 改动:**仅文件改名**(`15-research-concept-explainer.html` → `research-concept-explainer.html`,去前缀编号)。

重新同步:从上述上游路径覆盖对应文件,并更新本文件 commit 与日期。

## 各范型的「不要照抄」注意点

LLM 看范型学整体调性 + 结构,但范型里的某些局部模式跟本 skill 硬约束冲突,不要原样搬:

- **`docs-page.html`** — 文中 `.callout` 用了「圆角卡片 + 左侧 accent border」(L36),这是 SKILL.md 第三步明禁的 AI 仪表盘块。**学它的三栏 layout 与 sidebar nav 结构,不学 callout 卡**。需要标注 / 提示时改用 hairline 上下 rule 或 blockquote。
- **`clinical-case-report.html`** — alert 区块用红色左 border(医疗 data-semantic 语境),**只在真的有"告警"语义时用**;普通文档别套这个样式做装饰。
- **`proposal-swiss-editorial.html`** — ⚠ 这份是 Native 四轴架构提案的 **v1 历史快照**,其内容里**多处方案已被推翻**(如「PDF 作为第一步介质例外」、「Stage 路由到外部 skill」、craft 文档命名为 `measure-and-canvas` 等)—— 当前生效的架构以本 `SKILL.md` + `craft/structure-and-style.md` 为准。**只学它的 Swiss editorial 视觉系统**(暖纸 + IKB accent + serif display + mono metadata + chip 来源标注 + sticky TOC + 右 rail),**不学它的内容结构与方案细节**(那是给一份具体提案文档用的,且部分内容已过时,不可作为当前架构的指引)。
- **`research-concept-explainer.html`** — 这份是「Native 文章 + 段间嵌 widget + 右栏 glossary marginalia」的复合范型。**调性比其他几份 softer**(serif body + clay/terracotta accent + 浅 hairline + 4-14px 微圆角),这是「research explainer」的合理松动,不算违反硬约束 —— 当你写「概念解释」「研究笔记」类文档时跟着 soft 一档完全 OK。但 **widget 里的 `border-radius` (6/14px) 不要照搬到 Swiss editorial / 印刷期刊 / 冷技术等 sharper 调性的文档里** —— 调性要内部一致,不能 widget 跟正文打架。也别学它**直接命名 class 为 `.demo`**(语义弱),自己写时按 widget 实际功能命名。

## 收 / 不收的门槛(给后续扩库者用)

新范型要进本目录,必须**全部**满足:

1. 覆盖一个尚未占的「结构格」(Viewport × Navigation × Content)**或**展示一个尚未有的「调性」
2. 许可 Apache 或 MIT,且与现 LICENSE 兼容(同源最佳,跨源需要新 LICENSE 文件 = 文件膨胀)
3. **单文件自包含** —— 无 Tailwind / 无构建步骤 / 无 CDN(字体 fallback 可内联)
4. 不违反 `SKILL.md` 第三步硬约束
5. 视觉质量本身能当 quality bar(LLM 看了就该知道"做到这个程度才叫成品")

排除的过往候选(决策可追溯,别重新提议):

| 候选 | 排除理由 |
|---|---|
| `resume-modern`(open-design) | Tailwind 依赖 → 违反 #3 |
| `dashboard` / `live-dashboard` / `trading-analysis-dashboard`(open-design) | 堆 KPI 卡墙 → 违反 #4 |
| `finance-report`(open-design) | KPI 卡 + box-shadow → 违反 #4 |
| `invoice`(open-design) | shadow + 圆角 → 违反 #4 |
| `pricing-page`(open-design) | 调性偏营销落地页,与 native 文档语义不贴 → 违反 #5 |
| huashu c1 / c5 等 Stage 形态 | `position:fixed` 视口锁定属于 Stage 形态,已通过 `SKILL.md` 第一步路由到内置 `references/huashu-design/`,不进 Native 库(避免 LLM 学到「写 Native 文档也能 fixed 全屏」) |

新加范型时,在本文件「范型清单」表格 + 上游同步信息处同步登记,如有局部反模式也在「不要照抄」一节加一段。
