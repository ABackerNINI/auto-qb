# 输出规则 - OUTPUT_RULES.md

> **所有 skill 输出时必须遵守的通用规则**
> Skill 自身的 SKILL.md workflow 是**局部规则**，本文件是**全局约束**。两者冲突时以**更严格**的为准。

---

## 一、Phase 状态机（全局）

```
Phase 1: 初始化与首次生成
    ↓ 用户提出修改意见
Phase 2: 敏捷迭代
    ↓ 用户确认满意
Phase 3: 交付定稿 + 归档
```

**状态转移规则**：

- **Phase 1 → Phase 2**：用户针对 Phase 1 输出提修改意见
- **Phase 2 → Phase 2**：循环迭代
- **Phase 2 → Phase 3**：用户明确表示满意 / "可以了" / "就这个"
- **回退约束**：
  - 进 Phase 2 后**不再回 Phase 1 做任务路由**（即不再换 skill / design-system）
  - Phase 3 验证不通过 → 回退 Phase 2 修订（但不重选 skill）

---

## 二、文件命名与版本管理

### 命名格式

```
App 类（双交付）：
  V{N} {项目名}-{画布后缀}.html
  V{N} {项目名}-{原型后缀}.html

Web 类 / Deck 类（单文件）：
  V{N} {项目名}.html
```

`{N}` 是版本号，从 1 起递增，无前导零、无小数位。

**文件名语言（强制）**：`{项目名}` 与类型后缀跟随用户最近一条真实消息的语言：

| 用户语言 | 画布后缀 | 原型后缀 |
|---|---|---|
| 中文 | `无限画布` | `可交互原型` |
| 英文 | `Infinite Canvas` | `Interactive Prototype` |
| 其它语言 | 对应语言中「无限画布」的惯用表达 | 对应语言中「可交互原型」的惯用表达 |

- 同一个项目内后缀保持一致，不得中途换语言（用户明确切换语言后，从新版本文件起跟随新语言）
- `V{N}` 版本前缀恒定，不翻译
- 文件名避免 Windows 非法字符（`\ / : * ? " < > |`）与结尾空格/句点

### 版本递增规则

任何会落到 HTML 文件的改动都触发一次 V +1（含微调 / 改色 / 改一个 padding / 改一行文案 / 修一个 bug）。
唯一例外：show-tweaks 用户连续点击"应用"且模型在同一轮 assistant 消息内一次性落地（合并升一次 V）；以及 preview-only 拖动旋钮未点"应用"（未写盘）。

| 触发条件 | 版本变化 |
|---|---|
| Phase 1 首次生成 HTML | V1 |
| 任何一次会落盘的改动 | V +1 |
| Phase 3 交付 | 沿用最后版本号 |

App 类双文件：每次 V +1 时**两文件一起进 archive/，两文件一起写新版**（即便本轮只改了一个，未改的那个也按当前内容复制为新版本号），保证按版本号一次能取回完整双交付。

### 归档目录

> 下面是**中文场景示例**；实际后缀按上方「文件名语言」规则跟随用户语言（英文如 `V3 {Project}-Infinite Canvas.html`）。

```
工作区目录/
├── V3 {项目名}-无限画布.html      ← 活跃版本（App 类示例）
├── V3 {项目名}-可交互原型.html
├── archive/                     ← 归档目录
│   ├── V1 {项目名}-无限画布.html   ← v2 诞生时，v1 移入归档
│   ├── V1 {项目名}-可交互原型.html
│   ├── V2 {项目名}-无限画布.html   ← v3 诞生时，v2 移入归档
│   └── V2 {项目名}-可交互原型.html
```

### 每次 Phase 2 迭代的操作顺序

**Web 类 / Deck 类（单文件）**：

```
收到修改指令
    ↓
1. cp "V{N} {项目名}.html" "archive/V{N} {项目名}.html"          ← 归档旧版
2. cp "archive/V{N} {项目名}.html" "V{N+1} {项目名}.html"        ← 复制新版
3. 在 V{N+1} {项目名}.html 上执行修改
4. 输出修改后的完整 HTML
```

**App 类（双文件）**：

```
收到修改指令
    ↓
1. 判断修改性质：
   - 页面细节（视觉 token、模块、状态、文案、布局、交互组件）→ 两文件都改
   - 仅无限画布独有内容（Row 1 项目介绍、Row 2 设计系统说明、Row 3 跳转引导线、画布层级布局）→ 只改无限画布
   - 仅可交互原型独有内容（首屏微交互细节、原型独有的过渡 / 反馈）→ 只改可交互原型
   ↓
2. 不论改一个还是两个，两文件版本号同步升 V{N+1}：
   a. cp 两个旧版各自进 archive/
   b. cp archive/ 里的旧版各自复制为 V{N+1}
   c. 按第 1 步的范围在对应文件上落改动；不在范围内的文件保持内容不变，仅版本号升级
3. 输出两个 V{N+1} HTML，并对两个文件分别 MEDIA: 唤起预览
```

- 活跃版本（最新一版）始终留在工作区根目录
- `archive/` 下的文件**严禁修改**，保持历史快照
- 版本号递增不带前导零、不带小数位（V1 / V2 / V3，不是 V1.0 / V01）

---

## 二·项目交付物

App 和 Web 是两种交付节奏，别搞混。

**App 类**（手机 / 平板 / PC 桌面 / 穿戴）——交付两个文件：无限画布 + 可交互原型。
**Web 类**（落地页 / SaaS / Web App）——只出主 HTML，你自己判断要不要补别的。
**其它 mode**（deck / template / image / video / audio）——走各自规则，不管这节。

判定依据很简单：看 `used_skill` 的平台字段、场景关键词、名称前缀，哪个先命中就停。拿不准的默认 Web。

---

### App 交付物

两个文件，版本号同步。

```
V1 {项目名}-无限画布.html          ← ① 无限画布（三层架构，完整设计交付全景）
V1 {项目名}-可交互原型.html        ← ② 可交互原型（用户实际"摸"到的演示）
```

#### ① 无限画布 — 完整设计交付

采用 `infinite-canvas-output` 三层架构，一个文件承载全部设计产出：

**Row 1 项目介绍**——agent 在生成前先梳理项目背景，把结论输入到画布。三个问题必须回答清楚：是什么、给谁用、解决什么问题。信息架构、竞品差异、设计决策原因等维度根据项目复杂度自己决定要不要放。

**Row 2 设计系统**——agent 在生成前先定义视觉规范，把 token 输入到画布。三个维度必须展示：调性概述、色板（token + hex，必须跟 `used_design_system` 对得上）、字体排版。间距、组件、交互状态、动效等维度项目用到了就展示，没用到别凑数。

**Row 3 设计稿**——按交互链路从左到右排列所有页面，页面间用引导线标注跳转关系。这是核心交付物。

项目介绍和设计系统是 agent 的内部准备工作，不需要单独输出 .md 文件给用户——它们最终呈现在画布的 Row 1 和 Row 2 里。

#### ② 可交互原型 — 用户实际交互的演示

单独的首页 / 主屏，硬性要求：
- **设备适配**：默认按手机正常尺寸呈现，但必须能随前端设备切换适配桌面（≥1024px）、平板（768-1023px）、手机（<768px）三种 iframe viewport
- **不要写死外轮廓**：可以有 390×844 的手机 authoring viewport，但主容器必须有 `max-width` / `min()` / `clamp()` / media query 等响应式兜底，不能只靠固定 `width:390px;height:844px`
- 至少两个可点击元素（含悬停 / 按下 / 禁用反馈）
- 至少一个状态切换（toggle / tab / 验证态）
- MEDIA: 唤起预览时能直接交互

这是用户拿来"摸"的东西，不是示意图。

### 版本与归档

Phase 2 迭代时两文件版本号同步升级，无论本轮只动一个还是两个都动。具体范围按 §二 Phase 2 操作顺序的"判断修改性质"决定：页面细节（视觉 token / 模块 / 状态 / 文案 / 布局 / 交互组件）两边同步落地；只属于单一文件的内容（无限画布 Row 1/2/3 独有的；可交互原型独有的微交互）只在对应文件落。旧版进 `archive/`，严禁修改快照。

### App 交付自检

交付前跑这几项，任一未过就回 Phase 2 修：
- 两个文件都在，版本号一致
- 画布 Row 1 回答了三个核心问题
- 画布 Row 2 的 token 跟 `used_design_system` 对得上（抽查 3 个 hex）
- 可交互原型有可点击元素 + 状态切换
- 用户提的"页面细节"类修改两边都落了（视觉 token / 模块 / 状态 / 文案 / 布局 / 交互组件抽查 1-2 处对照）

### Web 类

不强制双文件。简单 landing 一个 HTML 就行；复杂 Web App 你自己判断要不要补。Web 项目形态太多变，不设硬约束。

---

## 二·补·补 · Deck 类项目交付规则（HTML 演示稿）

当 `used_mode == deck` 时，主产物是 **HTML deck**，不是 PPTX 导出任务，也不走 App 两件套。

### Deck 交付清单

```
工作区目录/
├── V1 {项目名}.html              ← 单文件 HTML deck，内部包含多页 slide
└── archive/                    ← Phase 2 迭代时旧版进这里
```

允许根据内容复杂度额外写 `README.md` / 资料整理 md，但不得把它们作为 deck 的主交付要求。

### HTML deck 必备能力

- **单一 HTML 源**：一个 `.html` 文件内完成 slide 结构、视觉样式、切页交互、speaker notes
- **固定演示画布**：默认 1920×1080（16:9）；若 skill 明确 4:3，使用 1024×768
- **多页结构**：每页是独立 slide section，包含页码 / 总页数 / 章节或进度提示
- **键盘可演示**：支持 ← / → 或 Space 切页；不得只能靠滚动阅读
- **端内预览优先幻灯片模式**：在 `<head>` 写入 `<meta name="auto-designer-preview-device" content="slide">`，让端内按 16:9 单页翻页 + speaker notes 展示
- **可打印基础**：包含 `@page` / `@media print` 横版样式，为后续 PDF 导出留接口
- **Speaker Notes 必备**：每页必须包含 `<aside class="notes">...</aside>` 或等价结构，用于端内 notes 面板与 PPTX 导出；notes 必须是演讲者可直接照着讲的口语讲稿，不是页面摘要、设计说明或“本页展示了什么”的一句话介绍；用户未指定时默认每页写 80-160 字、2-4 句的简短口播稿，用户要求逐字稿时写 150-300 字完整口语稿

### Deck 禁止事项

- ❌ 不要生成 `.pptx` 作为 Phase 1 主交付；PPTX 属于后续导出/转换链路
- ❌ 不要把多页 slide 做成纵向长网页，让用户一路滚动
- ❌ 不要套手机壳、平板壳或 App 两件套
- ❌ 不要把讲稿正文塞进可见 slide 主画面导致信息过密
- ❌ 不要省略 Speaker Notes，也不要只在少数页面写 notes
- ❌ 不要把 notes 写成“封面页：介绍……” / “核心论证页：展示……”这类页面说明；notes 要像主持人提词器里的话，能直接念给观众听

---

## 三、HTML 落盘与预览（强制）

任何输出 HTML 的 skill 必须遵守：

1. **写盘前必先升版本归档**：工作区已有活跃 V{N} HTML 时，先把 V{N} 复制进 `archive/`，再以 V{N+1} 写新版。**禁止**直接 `Write` 覆盖现有 HTML——会导致历史版本永久丢失，用户无法回退。
2. **真实写入 `.html` 文件到当前工作区目录**
3. **禁止仅在对话里展示本地路径字符串**——路径只是引用，不是交付物
4. 写入完成后**主动通过 `MEDIA:` 指令唤起端内预览**
5. **App 类双文件交付时，两个文件都必须 `MEDIA:` 唤起**——不论本轮只改了一个还是两个都改了，用户都要在端内同时看到无限画布与可交互原型的当前版本
6. 注：`MEDIA:` 是 autoclaw 平台原生指令（非 INTERACTIONS schema 的 question-form / status / plan / show-tweaks 等动作），由平台直接处理

---

## 三·补 · 输出前必读三件套（强制·零容忍）

 **任何 skill 在开始生成产物前，必须显式执行以下 `view` 操作**——禁止凭记忆 / 凭直觉 / 凭手感写。三件套缺一不可：

```
1. view 审美相关skill/design-skeletons/<used_skill>/example.html
   ↑ 强制 clone 起点，禁止从空白写
   ↑ 完整读取该 example.html 的 token (--bg / --accent / 字体 / 圆角等)
   
2. view 审美相关skill/design-systems/<used_design_system>/DESIGN.md
   ↑ 真读 token，禁止凭记忆写品牌色
   ↑ 重点关注 色板 / 字体排版 / 组件样式 / Agent Prompt Guide 段
   
3. view 审美相关skill/craft/<each-required>.md (按 SKILL.md od.craft.requires 数组)
   ↑ 真读 craft，禁止凭直觉判断字距 / 阴影 / 状态枚举
   ↑ 默认 4 件套：typography / color / anti-ai-slop / accessibility-baseline
```

### 何时触发

- Phase 1 子步骤 5「输出 HTML 交付物」**之前**——三件套必须在写第一行代码前 view 完
- Phase 2 迭代时**通常不需要**重 view（已读过）——除非用户提出涉及不同 craft / design-system 的修改
- Phase 3 自检前**可选**——若自检不过且涉及"我以为 token 是 X 但实际不是"，必须回头补 view

### 违反的检测

Agent 自检时按 OUTPUT_RULES §四 检查项扩展：

| 第 6 项 · view 验证 | 通过标准 |
|---|---|
| view 了 used_skill 的 example.html？ | 工具调用历史含 view 该路径的记录 |
| view 了 used_design_system 的 DESIGN.md？ | 工具调用历史含 view 该路径的记录 |
| view 了 craft 数组里所有 .md？ | 工具调用历史含 view 全部记录 |

**任一未 view → 视为"凭记忆走捷径" → 必须中止当前生成，重新走 view 流程后继续**。

### 例外

仅在以下场景**允许跳过 view**（agent 必须显式声明跳过原因）：

| 例外场景 | 允许跳过哪一件 |
|---|---|
| skill 是纯能力 skill（如 `design-review` / `creative-director`），不输出 HTML | 跳过 example.html 的 view |
| used_design_system 为 `null`（用 _schema/defaults.css 兜底）| 跳过 design-system DESIGN.md 的 view |
| craft 数组为空（罕见）| 跳过 craft 的 view |

>  **声明跳过的方式**：在输出前的内部梳理里写"按 OUTPUT_RULES §三·补 例外，跳过 view {item}，原因：{...}"——这是审计痕迹。

---

## 三·补·补 · 仲裁规则（design-system 明示与 craft 黑名单冲突时）

 **重要冲突**：craft 文件含"反 AI slop 黑名单"（如 anti-ai-slop.md 禁 Inter / Roboto），但某些 design-system 的 DESIGN.md **明示**使用这些字体或色（如 raycast 明示用 Inter，linear-app 明示用 Inter Tight）。两者打架时**仲裁规则如下**：

### 优先级（高到低）

```
1. used_design_system DESIGN.md 明示规范        ← 最高优先级
2. SKILL.md frontmatter 内的品牌规范
3. craft 黑名单 / 通用规则                       ← 仅作兜底
```

### 具体到 Inter / Roboto / Space Grotesk 字体冲突

| 场景 | 仲裁结果 |
|---|---|
| `used_design_system != null` 且 DESIGN.md 明示用 Inter（或 Roboto / Space Grotesk）| **用 Inter**，无视 craft 黑名单。但必须用 `var(--font-display)` 等 token 引用，不得硬编码 |
| `used_design_system != null` 但 DESIGN.md 没明示字体 | 按 craft 黑名单 → 优先 design-system 推荐的兜底字体 / 用 Geist / Newsreader / Instrument Serif 等替代 |
| `used_design_system = null`（兜底到 _schema/defaults.css）| 严格执行 craft 黑名单，禁用 Inter / Roboto / Space Grotesk |

### 具体到色板 / 阴影 / 布局其它冲突

同样原则——design-system 明示 > craft 黑名单 > 兜底默认值。

### 为什么 craft 黑名单仍然有用

不是说 craft 没用。Craft 是**默认护城河**：
- 没指定 design-system 时（小项目 / 内部工具 / 用户没给品牌参考）→ 严格执行黑名单防 AI slop
- 指定了 design-system 时 → 该品牌的视觉血统决定，craft 退为兜底

### 写在 HTML 输出里的痕迹

当因 design-system 明示而使用了"通常被 craft 禁止"的资源时（如 Inter），在输出 HTML 的 `<head>` 或注释里留一行审计痕迹：

```html
<!-- font-stack: Inter (依据 raycast/DESIGN.md L68) -->
```

让人审 / agent 自查时能立刻看到"这不是凭手感写的，是 design-system 明示的"。

---

## 四、Phase 3 交付前自检（必跑，9 项）

| # | 检查项 | 通过标准 |
|---|---|---|
| 1 | HTML 文件已落盘 | 文件存在于工作区目录，可被 stat 验证 |
| 2 | MEDIA: 预览已唤起 | 用户可直接在端内看到渲染效果 |
| 3 | DESIGN.md §十二 验证清单全过 | 见下方 §五，逐项打勾 |
| 4 | 无 AI slop 痕迹 | 对照 `craft/anti-ai-slop.md` P0 黑名单 |
| 5 | 设计系统一致 | 颜色 / 字体 / 间距来自所挂的 `design-systems/<brand>/DESIGN.md` |
| 6 | **输出前三件套已 view** | 对话上下文中的工具调用历史含 view skeleton / design-system / craft 文件的记录（或显式标记 `exempt: <原因>`），且 view 时间早于 Phase 1 输出。详见 `§三·补`。|
| **7** | **App 交付物齐全 + 同步落地** | `used_project_type == app` 时——`ls` 工作区，无限画布 + 可交互原型两个文件版本号一致且都存在；并跑 §二 App 交付自检全过；且历次 Phase 2 提到的"页面细节"类修改在两文件上均已落地（视觉 token / 模块 / 状态 / 文案 / 布局 / 交互组件抽查 1-2 处对照一致）。`used_project_type != app` 时本项自动通过（Web / deck / template 等不强制 App 双交付）。|
| **8** | **历史版本可回退** | `archive/` 含 V1...V{N-1} 全部历史版本（App 类则每个版本号下两文件都在），活跃 V{N} 在工作区根目录；任意中间版本缺失视为失败，回退 Phase 2 补归档。|
| **9** | **用户意图匹配** | 对照用户最近一次明确要求、已确认的交互选择、可用的 PRD / QA、代码摄取形成的当前实现基线，以及 Redesign 的保留边界逐项检查；所有要求均已落实，或已明确标记为超出范围 / 仍待确认。Redesign 必须在 `UI-check.md` 完成后执行本项。|

### 用户可见回复脱敏（并入第 9 项检查）

- 用户可见回复只说明用户能够观察到的进展、结果、影响和下一步，不得泄漏内部控制文件名或路径、内部章节号或检查项、Skill / Design System / workflow 名称、工具名、字段名或内部 ID。
- 本规则只屏蔽 AutoDesign 自身的内部控制信息，不得误伤用户主动提供的文件名或路径、公开技术术语，以及需要交付给用户的产物文件名。
- 需要表达内部步骤已完成时，只转换为用户可观察的结果，不复述内部规则原文，也不输出固定的自然语言口播示例。

**任一项未通过 → 立即补做或回退 Phase 2 修订，不允许直接交付。**

用户意图匹配失败时，只修正不匹配的局部内容，并重新检查受影响区域；不得重新执行代码摄取、任务路由或整个生成链路。当前代码只定义实现现状，不自动覆盖用户目标；只有差异会实质改变设计范围且现有材料无法判断时，才通过 `question-form` 做最小追问。

---

## 五、验证清单（链接 DESIGN.md §十二）

Phase 3 交付前必须跑 `DESIGN.md §十二` 验证检查清单（8 项基础检查）。

**完整 8 项定义见 `DESIGN.md §十二`，本文件不重复**——避免 DESIGN.md 更新时本文件产生偏移。

> 任一项未通过 → 立即补做或回退 Phase 2 修订，不允许直接交付。

---

## 六、归档项目（Phase 3 完成时）

交付完成后必须执行：

1. 在交付文件名 / 标题里加 `[DONE]` 标记，把 Phase 部分改为「已交付」（如 `## [DONE] {项目名} · {skill} · 已交付 · V3`）
2. 工作区内的历史版本（含 archive/）**全部保留**作为历史检索资料（不删除）
3. 完成后下一次新需求来时，会被识别为"无活动项目"，从 Phase 1 起算

---

## 七、设计思维四问（强制前置）

任何 skill 在写代码前必须先走 **`DESIGN.md §三`** 的设计思维四问（Purpose / Tone / Constraints / Differentiation）。

**完整四问定义见 `DESIGN.md §三`，本文件不重复**——避免 DESIGN.md 更新时本文件产生偏移。

> 不是问用户，是 agent 自己在内部梳理——梳理结果可在最终输出的 HTML 注释里留痕。

---

## 七·补 · 文案准则（语言匹配，强制）

**所有输出的可见文字（标题 / 副文案 / 按钮 / 卡片标签 / 模拟数据 / placeholder / footer 等）必须严格遵循 `DESIGN.md §七` 文案准则**——核心是：

> **用用户的语言写作（匹配输入语言）**

具体规则：

| 用户首句语言 | 输出 HTML 文案语言 |
|---|---|
| 中文 query | **必须中文**——包括模拟数据（人名 / 城市 / 卡片标题）、按钮、placeholder、footer 微文案 |
| 英文 query | 英文 |
| 中英混合 | 主体匹配中文（中文为主语），术语保留英文（如 SaaS / API / Token） |
| 其它语言 | 匹配用户语言 |

**禁止**：
- 禁止借鉴英文产品的 design-system 时，把英文模拟文案一起搬来（如借 Raycast 时使用 "Today's focus" / "Alice Chen"）
- 禁止凭"国际化产品默认英文"的惯性写英文
- 禁止中文 query 出现英文专有人名、英文卡片标签、英文 footer 等

**正确做法**：design-system 借的是**视觉 token**（颜色 / 字体 / 间距 / 圆角 / 组件结构），不是文案。文案永远跟用户语言走。

---

## 八、提问形式（强制）

任何 skill 在执行过程中需要问用户：

- **必须**通过 `INTERACTIONS.md §1` 的 `question-form` 动作
- **遵守** `DESIGN.md §十一` 提问形式硬规则
- **禁止**用 markdown 散文 / 自由文本提问

Phase 1 新设计任务必须先经过一次 `question-form`，再生成任何产物。用户提供完整 brief、附件、风格、页数或说“你来判断”，都不是跳过表单的理由；这些信息应预填/体现在选项里，等待用户提交、跳过或自动超时后继续。

PRD / QA 文档分支例外：若用户上传了 PRD / QA 文档，或明确说“按这份 PRD / 文档来做”，先按 `PRD_INGESTION.md` 完成 PRD → QA 阅读、模块 / 界面拆解，再继续三轴拼接与产物生成；只有 PRD / QA 仍无法回答关键缺口时，才通过 `question-form` 做最小追问。

---

## 九、平台特定约束

各平台的硬约束：

### App 类 skill（手机 / 平板 / PC / 穿戴）

- **触控目标 ≥ 44×44pt**（iOS）/ 48×48dp（Android）
- **不依赖 hover**——触控设备没有 hover 态
- **状态枚举完备**：所有按钮 / 输入框含 `默认 / 按下 / 禁用` 三态
- **响应式**：默认手机 390×844，但必须能适配 iPad 1024×1366 / PC 1280×800 等更大 viewport；不能把整页永久锁死在单一手机外轮廓
- **核心组件多状态**：本次涉及的组件必须展示所有交互状态（加载中 / 空态 / 错误 / 成功）

### Web 类 skill（落地页 / 多页站点 / SaaS 后台）

- **响应式**：每个核心页面至少出**桌面 + 移动**两态稿
- **三断点**：若是"双端响应式"项目，给出 640 / 1024 / 1440 三断点对照
- **交互态完备**：所有可点击元素显式画出 `默认 / 悬停 / 聚焦 / 禁用` 四态
- **链接对比度**：链接色与正文色对比度 ≥ 3:1（防灰底蓝链看不清）
- **footer + nav**：除单页 landing 外，多页站点必须有持久导航栏和页脚

### PPT / Deck 类 skill

- **尺寸**：默认 1920×1080（16:9）/ 1024×768（4:3）二选一，按 skill 规范确定
- **字号底线**：正文 ≥ 24px / 标题 60-120px / 主视觉大字 180-240px
- **不要 ≤ 24px 字放幻灯片**
- **主产物**：单文件 HTML deck，内含多页 slide / 键盘切页 / 页码 / 每页 speaker notes
- **预览标记**：`<meta name="auto-designer-preview-device" content="slide">`

### 报告 / PDF 类 skill

- **正文**：最小 10pt（≈13.3px），理想 11-12pt
- **300 DPI** 印刷场景适用

---

## 十、硬性禁令汇总

- 不得跳过 Phase 3 交付前自检直接交付
- 不得只展示路径不写文件
- 不得跳过 MEDIA: 指令
- 不得用散文向用户提问
- 不得在 Phase 3 完成后忘记按 §六 归档（加 `[DONE]` / 改"已交付"）
- 不得在 Phase 2 重选 skill / design-system
- 不得跳过 DESIGN.md §三设计思维四问 直接写 HTML
- 不得在交付时漏掉版本号
- **不得覆盖已有 HTML**——任何写盘（含微调 / tweaks 应用 / bug 修）都必须先把活跃版本进 archive/ 再以 V +1 写新版
- **不得删除或改动 `archive/` 下的历史版本**——它是用户回退的唯一依据
- **App 类项目交付时漏掉交付文件**（违反 §二）——无限画布 + 可交互原型必须全到
- **App 类 Phase 2 页面细节修改只改了一个文件**（违反 §二）——视觉 token / 模块 / 状态 / 文案 / 布局 / 交互组件类改动必须两文件同步落地
- **App 类 Phase 2 输出时漏发任一文件**（违反 §三 第 4 条）——两个文件必须都 `MEDIA:` 唤起给用户
- **不得在 HTML 产物中使用 emoji 作为设计元素**——包括但不限于图标、头像占位、产品图占位、导航图标、装饰元素。用 SVG 线性图标（1.6–1.8px stroke、currentColor）或 CSS 图形替代。画布 Row 1 / Row 2 的说明性标签允许少量 emoji，但 Row 3 设计稿页面内严禁

---

## 十一、维护规则

- 本文件目标长度 **≤ 250 行**
- 新增跨 skill 通用规则时加在本文件
- skill 特定规则（如 saas-landing 必须含 6 段式）写在该 skill 的 SKILL.md，不写本文件
- 本文件与 `DESIGN.md` / `INTERACTIONS.md` 冲突时——**优先锁定文件**（DESIGN / INTERACTIONS），本文件适配修改
