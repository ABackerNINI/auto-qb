# 任务路由 - TASK_ROUTER.md

> 🔴 **职责：先做 Redesign 前置分流；未命中时再做任务分析 → 三轴拼接 → 调用对应 skill**。
> 平台（App / Web / PPT / PDF / ...）是 skill 选择的辅助维度，不是顶层路由。

---

## 0. Redesign 前置分流（最高优先级）

本步骤必须在读取 `INDEX.md`、选择 skeleton / skill、挂 design-system 或读取 craft 之前完成。

### 0.1 命中条件

当任务需要继承已有界面、项目代码或视觉参考作为实现基线时命中 Redesign。判断依据是任务是否依赖已有基线，而不是最终页面是否为全新页面。

以下情况命中：

- 修改、改版、重构或视觉升级已有页面、组件、交互流程或视觉体系
- 基于可访问的现有项目 / 代码，调整已有界面，或新增全新页面、组件、功能和交互
- 用户提供当前界面截图、Figma、线上页面或已有设计稿，并明确要求修改该现有对象
- 用户要求按照截图、参考图、Figma 或已有设计稿实现一个全新页面

以下情况不命中：

- 从零设计新项目、新页面或新视觉产物，且没有可继承的项目代码、现有界面或视觉参考
- 只分析、解释或评审现有实现，不要求生成改版产物
- 继续修改 Auto Designer 本轮已经生成的稿件；此时直接进入 `OUTPUT_RULES.md` 的 Phase 2
- 普通代码问答或与设计无关的任务

存在可访问的已有代码或项目时，“已有代码 + 新增全新页面”命中 Redesign。用户要求按照截图或其他已有视觉材料实现新页面时，“按截图实现一个新页面”也命中 Redesign。

### 0.2 分流结果

- **命中 Redesign**：读取 `REDESIGN.md`，由它独立完成保留边界、改造强度、方案方向、实现和 UI 检查；不得读取 `INDEX.md`，不得执行 §1 至 §3 的三轴路由。完成后读取 `OUTPUT_RULES.md`，执行用户意图匹配校验和交付规则。
- **未命中 Redesign**：继续执行下方 §0.3、§0.4 与 §1 至 §3 的原有流程。
- **无法判断是否需要继承已有项目、界面或视觉参考时**：存在可访问项目、现有界面或明确视觉参考就按 Redesign；否则按标准新设计任务继续。视觉方向模糊时交给 `REDESIGN.md` 或后续缺省决策，不做前置追问。

### 0.3 非 Redesign 输出契约

非 Redesign 任务完成三轴路由后必须产生以下结果：

1. **决定调用的 skill 名**（来自 `审美相关skill/skills/` 或 `审美相关skill/design-skeletons/`）
2. **决定挂的 design-system**（来自 `审美相关skill/design-systems/<brand>/`）
3. **决定拉的 craft 列表**（来自 `审美相关skill/craft/<*.md>`）

然后**控制权交给选中的 skill**，由它自己的 SKILL.md workflow 接管后续流程。

### 0.4 Phase 1 直接执行闸门（强制）

先完成 §0 Redesign 前置分流，再检查 §0.5 PRD / QA 文档分支。命中 Redesign 时直接交给 `REDESIGN.md`；命中文档分支时先完成文档摄取与拆解，再继续后续流程。

若本轮是新设计任务 / 新项目 Phase 1，完成任务分析后直接进入三轴拼接、资源 view 与产物生成。用户 brief 不完整时，由 agent 根据任务类型、附件、行业、平台、骨架默认值与设计系统匹配度自行补齐关键偏好。

- 第一条用户可见动作可以是简短状态或计划，也可以直接是生成进度；不要把偏好收集作为独立阶段
- 缺失项按“你来判断”处理，并在内部设计假设、HTML 注释、项目记录或最终说明中留痕
- Phase 2 修改当前稿、继续上一轮任务、或纯评审/解释类不产出新设计稿的请求，沿用已有项目上下文与当前版本，不重新路由

### 0.5 PRD / QA 文档分支（强制）

仅在 §0 未命中 Redesign 时适用。若用户上传了 PRD / QA 文档，或明确说“按这份 PRD / 文档来做”，先读 `PRD_INGESTION.md`，然后改走文档分支：

1. 先读 PRD
2. 再读 QA
3. 先向用户输出功能模块与界面拆解
4. 再基于 `PRD + QA + 模块/界面拆解结果` 继续三轴拼接

此分支下，PRD / QA 已有信息优先于用户首句。若仍存在关键缺口，按最稳妥默认值继续，并在产物中标记为待确认假设。

---

## 1. 任务分析阶段（按顺序执行）

### 1.1 读用户首句

提取：
- **输出类型**关键词：「落地页 / dashboard / PPT / slides / presentation / deck / 演示 / 幻灯片 / 海报 / 原型 / 评审 / 报告 / 病历 / 行情图」等
- **平台**关键词：「App / iOS / Android / Web / 小程序 / PC 桌面 / 平板 / 穿戴」
- **风格 / 品牌**关键词：「Linear 风 / Stripe 风 / 类 Notion / 极简 / 极繁」
- **行业**关键词：「金融 / 量化 / SaaS / AI / 医疗 / 制造 / 政务 / 餐饮 / 体育 / 农业」

### 1.2 读 INDEX.md（仅非 Redesign）

按 1.1 的关键词查 `INDEX.md` 第九章「用户大盘场景速查」，得到候选资源清单。


### 1.3 PRD / QA 摄取分支

若命中 `PRD_INGESTION.md` 的适用时机：

- 先按 `PRD_INGESTION.md` 完成 PRD → QA 的阅读
- 先完成模块、界面、关键状态的需求拆解
- 再进入 §2 三轴拼接
- skeleton / skill / design-system / craft 的选择，必须以后一步拆解结果为准，而不是只看用户首句

---

## 2. 三轴拼接（仅非 Redesign）

### Step A · 选 Skill（做什么）

**优先级**：

```
0. 用户首句明确说 "PPT / slides / presentation / deck / 演示 / 幻灯片 / 分享稿"
   → 优先在 design-skeletons/ 选 od.mode=deck 的骨架（默认 html-ppt；Replit 风等明确风格按对应骨架）
   ↓ 没匹配
1. 用户首句明确说"做个 X" → 在 design-skeletons/ 找匹配 triggers 的骨架
   ↓ 没匹配
2. 用户首句是"评审 / 改进 / 提取 / 咨询 / 总监意见" → 在 skills/ 找能力 skill
   ↓ 没匹配
3. 模糊请求 → 用最稳默认骨架继续，优先选择覆盖面广、失败率低、可快速迭代的 skeleton
```

**匹配方法**：
- 扫描候选 skill 的 SKILL.md frontmatter `triggers` 字段
- 关键词命中率 ≥ 50% 即采纳。若冲突，按 skeleton 优先、用户显式输出类型优先、场景覆盖度优先、example.html 完整度优先的顺序裁决

**跨目录碰撞规则（skeleton vs skill 同时命中）**：

当同一关键词同时命中 `design-skeletons/` 和 `skills/` 的资源时：
1. **Skeleton 优先** — skeleton 有现成骨架（example.html 可 clone），优先于纯能力 skill
2. **Skill 降级为 fallback** — 仅当 skeleton 无法满足需求（如用户明确要评审/咨询而非产出新设计稿）时，才回退到 skill
3. 常见碰撞场景：
   - "slides / PPT / deck" → skeleton（guizang-ppt / simple-deck 等），**不选** skill:slides
   - "landing page / 落地页" → skeleton:saas-landing，**不选** skill:frontend-skill
   - "pitch deck" → skeleton:html-ppt-pitch-deck，**不选** skill:slides
   - "design review / 评审" → 这是咨询任务，无新设计产出 → **选 skill:design-review**（例外：不选 skeleton）

### Step A-2 · PPT 风格二级路由（PPT / slides / deck 类）

当一级路由命中 PPT 类（用户说"做 PPT / slides / deck / 演示 / 幻灯片"）时，按以下逻辑做二级风格匹配：

```
用户首句含风格词？
  ├─ 是 → 按 INDEX.md §2.1「风格→骨架映射表」精确匹配单个 PPT 骨架变体
  ├─ 含专项关键词（pitch / 课程 / 复盘 / 演讲稿）→ 按下方「专项关键词映射」走对应骨架
  └─ 否（泛 "做个 PPT"）→ 默认 html-ppt-zhangzara-broadside；若内容偏杂志演讲则选 guizang-ppt，偏融资则选 html-ppt-pitch-deck，偏课程则选 html-ppt-course-module
```

**专项关键词→骨架映射**（一对一命中，不需要二级风格路由）：

| 关键词 | 骨架 |
|---|---|
| pitch / fundraising / investor / 融资 | `html-ppt-pitch-deck` |
| course / workshop / training / 课程 / 培训 | `html-ppt-course-module` |
| 演讲者模式 / speaker notes / 提词器 | `html-ppt-presenter-mode-reveal` |
| incident / safety / red team / 事故复盘 | `html-ppt-testing-safety-alert` |
| terminal / CLI / dev tool review | `html-ppt-hermes-cyber-terminal` |
| replit / helix | `replit-deck` |
| kami / 紙 / paper deck | `kami-deck` |
| keynote / 演示文稿 / editorial slides | `open-design-landing-deck` |


**同一风格族内多选一**：若氛围词命中整个族（如"editorial"命中 6 个），优先选族内排第一个（最典型）；若用户语义指向更明确的行业、媒介或情绪，则选对应变体。

**严禁**：
- 从空白写而不挂任何 skill
- 同时挂两个互斥的 design-skeletons（如 saas-landing + dashboard）
- 把明确的 PPT / slides / presentation / deck 需求误路由到 App/Web prototype；这类需求的主产物是 **HTML deck**，不是移动端 App 原型，也不是 PPTX 导出任务

### Step B · 选 Design System（穿什么皮）

```
                  用户给了视觉参考？
                /                  \
               是                    否
              /                       \
       明确指定品牌？               有项目上下文？
      /         \                    /         \
     是          否                  是          否
     ↓           ↓                  ↓           ↓
  用对应品牌    截图 / Figma     调 taste-skill  default
  DESIGN.md    → taste-skill     推荐 2-3 个      ↓
               自动选最贴近的 taste 方向   _schema/defaults.css
                                                 + taste-skill 调参
```

**骨架自带风格 vs design-system 冲突规则**：

1. **骨架目录含 `example.html` 且用户未指定品牌风格** → Step B **跳过 design-system 挂载**，直接用骨架自带风格，`used_design_system` 写 `null`（骨架即皮肤）
2. **骨架目录不含 `example.html`** → 正常走 Step B 挂 design-system

### Step C · 拉 Craft（基本功）

**默认必拉 4 件套**（无论什么 skill）：
- `typography.md`
- `color.md`
- `anti-ai-slop.md`
- `accessibility-baseline.md`

**按场景扩展拉取**：

| 场景特征 | 额外拉 |
|---|---|
| 含表单 / 输入 | `form-validation.md` |
| 强交互（按钮、下拉、tab） | `laws-of-ux.md` |
| 含动画 / 微交互 | `animation-discipline.md` |
| App / Dashboard / 工具类 | `state-coverage.md` |
| 文字密集（落地页 / 文档） | `typography-hierarchy.md` |
| 编辑式风格（杂志 / blog） | `typography-hierarchy-editorial.md` |
| 中东 / 阿拉伯文场景 | `rtl-and-bidi.md` |

**优先级**：以 skill 的 SKILL.md frontmatter `od.craft.requires` 数组为准。本节是兜底默认。

---

## 2.5 输出前必读三件套（强制）

三轴拼接完成后、控制权交给 skill 之前，必须 view skeleton + design-system + craft。

**完整规则（含例外条款、跳过声明、自检检测）统一定义在 `OUTPUT_RULES §三·补`，此处不重复。**

未 view 即开始生成 → 视为"凭记忆走捷径" → 必须中止生成、重新走 view 流程。

---

## 2.6 Prompt Composition · 按 `od.mode` 装配输出框架（强制）

🔴 三件套 view 完后、写第一行代码之前，**必须**根据 `used_skill` SKILL.md frontmatter 的 `od.mode` 字段，额外 view 对应的"输出框架层"资源。

**完整装配规则**见 [`审美相关skill/output-frameworks/prompt-composition-order.md`](审美相关skill/output-frameworks/prompt-composition-order.md)，本节是简表速查。

### 装配矩阵

| `od.mode` | 主交付形态 | 额外必读（在 §2.5 三件套之上） | 交付物数量 |
|---|---|---|---|
| `prototype` + **App 类**（used_project_type=app） | 可预览 HTML 原型 | `output-frameworks/designer-prompt.md`（首次）+ `output-frameworks/discovery-philosophy.md` | **2 件**（无限画布 + 可交互原型）·详见 `OUTPUT_RULES §二` |
| `prototype` + **Web 类**（used_project_type=web） | 可预览 HTML 原型 | 同上 | 仅主 HTML |
| `deck` | 16:9 演示 deck（HTML 内含多页 slides） | 上面两个 + **`output-frameworks/deck-framework.md`**（幻灯片预览 / 4 类型 / scale-to-fit / 键盘切页） | 1 个 deck HTML |
| `template` | 设计系统 handoff（DESIGN.md + 示例） | 上面两个 + （未来补 `template-framework.md`，目前走 fallback） | DESIGN.md + ≥2 示例 |
| `image` / `video` / `audio` | 静态图 / 视频 / 音频 | 框架未实施——按 skill 自有 workflow 走 | 按 skill 规则 |

> 📌 **`od.mode` 字段读取**：从选中 skill 的 SKILL.md frontmatter 的 `od:` 段查 `mode:`。若 skill 没明示 `mode`，按其 `od.preview.type` / `outputs.primary` 反推（含 `.html` / `.jsx` → `prototype`；slides → `deck`；image → `image`）。

> 📌 **`used_project_type` 字段判定**：仅 `mode == prototype` 时需要判定，按 `OUTPUT_RULES §二` 的判定规则：① `od.platform` 字段 → ② `od.scenario` / `triggers` 关键词 → ③ skill 名前缀。

### Mode-Aware 自检（在 OUTPUT_RULES §四 9 项之上）

| mode | 额外自检 |
|---|---|
| `prototype` + App | 第 7 项已覆盖（OUTPUT_RULES §四 + §二 App 交付自检） |
| `prototype` + Web | 无额外（仅产主 HTML，OUTPUT_RULES §四 9 项足够） |
| `deck` | 跑 `deck-framework.md §六` 的 7 项 deck 专用自检 |
| `template` | 跑 design-system 自身 DESIGN.md 的验证项（如 token 全部定义、跨屏复用核对） |

---

## 3. 拼接示例

### 示例 1 · "做个 Linear 风的 SaaS 落地页"

```
分析：
- 输出类型 = 落地页 → design-skeletons/saas-landing
- 风格 = Linear → design-systems/linear-app
- 没含表单 / 动画特征 → 拉默认 4 件套 + skill 自身 od.craft.requires

拼接结果：
  used_skill          = saas-landing
  used_design_system  = linear-app
  used_craft          = [typography, color, anti-ai-slop, accessibility-baseline,
                         laws-of-ux]  ← skill 自带要求

调用 saas-landing/SKILL.md → 执行其内部 workflow
```

### 示例 2 · "做一个量化交易策略 dashboard"

```
分析：
- 输出类型 = dashboard → design-skeletons/trading-analysis-dashboard-template
- 行业 = 量化金融 → design-systems/binance（fallback：linear-app）
- 含数据 / 表格 → 必拉 state-coverage

拼接结果：
  used_skill          = trading-analysis-dashboard-template
  used_design_system  = binance
  used_craft          = [typography, color, anti-ai-slop, accessibility-baseline,
                         state-coverage, typography-hierarchy]

注意：金融行业红涨绿跌强制要求，需在 skill workflow 内单独强调
```

### 示例 3 · "帮我评审这个稿"

```
分析：
- 输出类型 = 评审 → skills/design-review（不是 skeleton）
- 没新 artifact 产出 → 不挂 design-system / 不出 HTML

拼接结果：
  used_skill          = design-review
  used_design_system  = null（评审不需要）
  used_craft          = [anti-ai-slop, color, typography]（评审依据）

调用 design-review/SKILL.md → 输出评审意见（非 HTML 产物）
```

### 示例 4 · "做一份 AutoClaw 介绍 PPT"

```
分析：
- 输出类型 = PPT / 演示 → design-skeletons/html-ppt（od.mode=deck）
- 如果用户指定 Replit / keynote / 小红书图文等风格 → 选对应 deck 骨架
- brief 不完整时，自动补齐受众、页数、叙事、风格、讲稿深度和交付形态；默认选择一个可演示、可继续迭代的 HTML deck 方向

拼接结果：
  used_skill          = html-ppt
  used_design_system  = _schema/defaults.css 或用户指定品牌
  used_craft          = [typography, color, anti-ai-slop, accessibility-baseline,
                         typography-hierarchy]
  used_mode           = deck
  used_project_type   = other

交付：1 个可预览 HTML deck（内含多页 slide / 键盘切页 / 页码 / 每页 speaker notes），不是 PPTX。
```

### 示例 5 · "做个医疗病例报告"

```
分析：
- 输出类型 = 报告 → design-skeletons/clinical-case-report
- 行业 = 医疗 → 无对应 design-system
- 含表单结构 → 拉 form-validation

拼接结果：
  used_skill          = clinical-case-report
  used_design_system  = _schema/defaults.css （fallback）+ taste-skill 调参
  used_craft          = [typography, color, anti-ai-slop, accessibility-baseline,
                         form-validation, typography-hierarchy-editorial]
```

---

## 4. 缺省决策协议

任务分析过程中缺少信息时，按以下规则直接补齐：

- 平台模糊：优先 Web；若出现手机、移动端、App、iOS、Android、小程序等词，按 App 类
- 风格模糊：优先选择与内容场景匹配的骨架自带风格；没有视觉源时按 `discovery-philosophy.md` 的三方向表选择一个方向
- 场景多义：优先选择能覆盖最多核心信息与状态的 skeleton；纯咨询/评审才回退到 skills/
- 产物范围模糊：先交付一个完整 V1，可在 Phase 2 继续迭代，不把偏好确认变成前置步骤

**典型场景**：
| 情景 | 默认裁决 |
|---|---|
| 平台模糊（既像 App 又像 Web） | 默认 Web；若任务强调移动使用，则 App |
| 风格模糊 + 没参考 | 按行业与内容密度选 Minimal / Editorial、Bold / Campaign 或 Dense / Professional |
| 场景多义（"做个表格"）| 默认 dashboard / 数据管理场景，并补齐空态、筛选、表格状态 |

> 缺省选择不是最终锁死。用户后续提出修改时进入 Phase 2，以 V+1 的方式迭代。

---

## 5. 硬性禁令

- ❌ **不得跳过本文件直接调用 skill**（先完成 §0 分流；非 Redesign 才做三轴拼接）
- ❌ **不得让 Redesign 继续读取 `INDEX.md` 或补走三轴路由**
- ❌ **不得因设计偏好缺失停在前置阶段**；按本文件缺省决策生成可迭代 V1
- ❌ **不得同时挂两个互斥的 design-skeletons**
- ❌ **不得选 INDEX 没列的 skill**（避免幻觉调用不存在的 skill）
- ❌ **不得在 design-system 缺失时凭记忆写品牌色**（fallback 到 _schema 或 taste-skill）
- ❌ **不得跳过「输出前必读三件套」直接生成产物**（违反 §2.5 + OUTPUT_RULES §三·补）

---

## 6. 维护规则

- 新增 skill / 新增品牌时，**INDEX.md 必须同步更新**——本文件不重复列具体 skill
- 新增大盘场景（如新行业）时，§2 Step B 的"特殊情况"和 §3「拼接示例」要补
- 本文件目标长度 **≤ 250 行**，超过说明拼接逻辑变复杂，需要拆分子文件
