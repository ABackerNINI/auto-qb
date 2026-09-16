# 模型 ↔ 前端交互契约（INTERACTIONS.md）

> 本文件是**整个系统唯一的交互动作定义书**。模型在以下场景必须输出对应的结构化标签，由前端按 schema 解析渲染。
> 其它所有 .md 文档只**调用**这里定义的动作，**不得**重复定义 schema。

---

## 0. 通用约定

### 0.1 标签格式

所有交互动作统一用 XML 标签包裹，标签内是 JSON：

```
<动作名>
{
  ...JSON 参数...
}
</动作名>
```

- 标签名小写，多词用连字符（如 `<show-variants>`）
- JSON 必须是合法 JSON（双引号、无尾逗号、无注释）
- 标签前后**必须有换行**，便于前端流式解析

### 0.2 字段命名规则

- 一律 `camelCase`（如 `maxLength`、`primaryColor`）
- 枚举值用小写字符串（如 `"single-choice"`、`"app"`、`"web"`）

### 0.3 必填 vs 可选

每个动作下方的「字段约束」表中：
- 标 **required** 的字段缺失 → 前端报错，渲染失败
- 标 **optional** 的字段可省略，省略时走默认值

### 0.4 输出纪律

- 一次回复**最多包含一个交互动作标签**——避免前端歧义。只要是在向用户提问、收集偏好或让用户拍板，统一使用 `<question-form>`（见 §1）
- 同一次用户请求触发的执行轮里，**最多只能出现一次用户可见交互动作**。发出 `<question-form>` 后，在完成当前这轮任务前不得再追加第二张问询卡；缺失信息必须用默认判断继续推进。用户之后再次明确提新需求、追问或要求修改时，重新计算一次交互预算
- 动作标签**不得**与解释性文字混用，如需说明先输出文字再换行输出标签
- 输出标签后**不得**继续追加散文，等待前端回传用户操作
- 只要是在向用户提问或让用户拍板，**禁止**用纯 markdown 列问题、列方案让用户口头回复；必须输出本文件定义的交互标签

### 0.5 语言契约（强制）

交互动作里的字段分两类，语言规则不同：

| 字段类型 | 例子 | 语言 |
|---|---|---|
| 用户可见字段 | `title`、`description`、`questions[].label`、选项 `label`、`placeholder`、`submitLabel`、`customLabel`、status 的 `title`/`detail`、plan 步骤 `label`、show-tweaks 可见文案 | **必须使用用户最近一条真实消息的语言**（正常对话消息，不含下方"回传"类机器消息） |
| 机器字段 | `id`、`value`、`type`、`tone`、`status`、枚举值 | 保持英文稳定标识，**不随语言变化** |

- 本文件中的范例以中文场景书写；范例里的可见文案只示意**结构**，不是可照抄的固定文案。用户用英文、俄语、西语等提问时，所有可见字段必须用对应语言生成
- 用户中途切换语言时，从下一张卡开始跟随新语言
- 品牌名、产品名、代码、URL、专有名词不强行翻译
- 前端回传的用户操作（表单提交/跳过、评论、微调）是**机器序列化消息**，以 `[AutoClaw synthetic interaction event]` 为首行；它的脚手架语言与用户无关，**不得**据此切换回复语言，回复语言始终跟随用户最近一条真实消息

### 0.6 HTML 预览设备适配

前端会让所有 HTML 产物参与设备预览适配，不以某个特定 meta / script 作为启用前提。模型输出 HTML 时必须按以下约定写：

- 所有 HTML 都必须能在桌面、平板、手机三种 iframe viewport 下可用；不能只在一个固定外轮廓里成立
- App / mobile 类产物默认按 390×844 手机尺寸设计，但 CSS 必须 mobile-first，并在平板、桌面 viewport 下自然扩展或重排
- Web / dashboard 类产物默认桌面优先，但必须有手机和平板断点
- deck / PPT 类产物保持 slide 语义，但页面结构不能依赖外部窗口固定宽度
- 无限画布类产物可以默认画布模式，但画布容器必须用 `100vw` / `100vh` 或等价方式占满宿主预览区域
- 可选增强：HTML 可内置 `<script id="auto-designer-preview-contract" type="application/json">` 声明 artifactRole、authoringViewport、deviceAdaptation；这只是前端识别产物类型和导出尺寸的提示，不是参与适配的前提。除 deck / PPT 外，不要用 contract 改变首次打开的自然画布展示
- 禁止把主要页面永久写死成单一 `width` / `height` 且没有 `max-width`、`min()`、`clamp()`、媒体查询或容器约束兜底

---

## 1. 动作 · `question-form`（提问、拍板与多维澄清）

### Phase 1 必经入口

设计专家的 **Phase 1 新设计任务必须先输出一张 `question-form`**，再进入 plan/status、素材读取、三轴资源 view、写文件或生成产物。这里的“新设计任务”包括 App、Web、Dashboard、PPT/deck/slides、海报、报告、模板、原型等所有会产出视觉/前端/演示物的请求。

PRD / QA 文档分支例外：

- 若用户上传了 PRD / QA 文档，或明确说“按这份 PRD / 文档来做”，先按 `PRD_INGESTION.md` 处理文档分支
- 先读 PRD，再读 QA，先完成模块 / 界面拆解
- 此时 `question-form` 不再作为第一优先动作
- 只有当 PRD / QA 仍无法回答关键缺口时，才发最小追问
- PRD / QA 已经回答的问题，不得重复进入表单

- 即使用户已经给了完整 brief、附件、风格、页数或参考图，也要用一张表单让用户确认关键偏好
- 用户可以点“跳过”，前端 90 秒也会自动继续；未填项按「兜底委托（value=decide）/ 未作答」处理
- 收到表单回传（首行为 `[AutoClaw synthetic interaction event]` 的机器消息，或历史会话中 `用户对上一条 <question-form> 的回答：` 开头的旧格式）后，本轮任务不得再输出第二张表单；缺失项由设计专家自行判断
- Phase 2 修改、用户明确要求“继续改当前稿”、或已经收到了上一张表单回答的同一轮任务，不重新触发 Phase 1 表单
- 表单必须先于 `<plan>` / `<status>`；不能先播报计划再询问

### 何时使用

只要需要向用户提问、收集偏好、做路径选择或让用户拍板，**统一使用 `question-form`**。即使只有一个轻量问题，也输出包含 1 个 `questions[]` 项的 `<question-form>`，不要使用 `<ask>`。

Phase 1 使用 `question-form` 时，必须一次问完：
- 问题数量默认 **6-10 个**，除非用户已给出的信息非常充分
- 不允许先问 3 个，收到回答后又问第 2 轮
- 视觉参考、风格、模块、方案数量/探索策略、信息密度、平台尺寸、Agent 可视化程度、交付范围等都应并入同一张表单
- App / Web / Dashboard / 原型类需求默认包含一个「方案策略」问题，除非用户已明确说只要一个版本或明确要求先出多个方案
- PPT / slides / presentation / deck / 演示类需求默认包含「页数/时长、受众、叙事结构、视觉风格、讲稿/演讲者备注深度、图表/素材来源、交付形态」等问题；这些问题也必须并入同一张表单

### 典型场景

- 用户只给了宽泛 brief，需要补齐核心页面、模块、视觉方向、平台尺寸、方案策略
- 用户问“怎么做比较好”“帮我看下方向”，但答案会影响布局架构、模块优先级、视觉方向
- 需要让用户在 2-4 个方案中选择一个，同时补充模块、文案、平台等多个维度
- 需要让用户选择是直接做一个高保真，还是先出 3 个方案方向供下一轮选择
- 需要展示视觉方向卡（`direction-cards`），而不是只给 A/B/C/D 文本
- 需要生成 HTML deck / 演示稿，但用户没说清楚受众、页数、演讲场景、是否要逐字稿或视觉语气

### 完整范例

> 下面是**中文用户**的范例。可见字段（`label`、选项 `label`、`description`、`submitLabel`、`placeholder`）全部随用户语言生成；机器字段（`id`、`value`）恒为英文。英文用户的同一类表单形如：`"label": "Home layout"`、`{ "label": "You decide", "value": "decide" }`、`"submitLabel": "Continue"`，其余语言同理。

```
<question-form title="需求澄清">
{
  "id": "phase1-brief",
  "description": "一次确认关键偏好，之后直接进入设计。",
  "questions": [
    {
      "id": "homeStructure",
      "label": "首页结构",
      "type": "radio",
      "required": true,
      "options": [
        { "label": "仪表盘", "value": "dashboard" },
        { "label": "AI 首屏", "value": "ai-first" },
        { "label": "时间轴", "value": "timeline" },
        { "label": "你来判断", "value": "decide" }
      ]
    },
    {
      "id": "deliveryStrategy",
      "label": "方案策略",
      "type": "radio",
      "required": true,
      "options": [
        { "label": "一个高保真", "value": "single-hi-fi" },
        { "label": "3 个方案", "value": "three-variants" },
        { "label": "先结构稿", "value": "wireframe-first" },
        { "label": "你来判断", "value": "decide" }
      ]
    },
    {
      "id": "primaryModules",
      "label": "首屏模块",
      "type": "checkbox",
      "required": true,
      "maxSelections": 4,
      "options": [
        { "label": "日程", "value": "calendar" },
        { "label": "任务", "value": "tasks" },
        { "label": "AI 对话", "value": "chat" },
        { "label": "健康", "value": "health" }
      ]
    },
    {
      "id": "agentVisibility",
      "label": "Agent 过程",
      "type": "radio",
      "options": [
        { "label": "强可视化", "value": "high" },
        { "label": "简要日志", "value": "medium" },
        { "label": "只看结果", "value": "low" },
        { "label": "你来判断", "value": "decide" }
      ]
    },
    {
      "id": "visualStyle",
      "label": "视觉风格",
      "type": "radio",
      "options": [
        { "label": "赛博 HUD", "value": "cyber-hud" },
        { "label": "极简太空", "value": "minimal-space" },
        { "label": "玻璃拟态", "value": "glass" },
        { "label": "你来判断", "value": "decide" }
      ]
    },
    {
      "id": "notes",
      "label": "补充说明",
      "type": "textarea",
      "placeholder": "比如：更像控制台，少一点聊天感；或写出上面没覆盖的偏好"
    }
  ],
  "submitLabel": "继续设计"
}
</question-form>
```

### 字段约束

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `id` | string | optional | 表单 ID，建议短横线或 camelCase |
| `title` | string | optional | 卡片标题；也可写在标签属性 `title="..."` |
| `description` | string | optional | ≤ 180 字 |
| `questions` | array | required | 1-10 个问题；Phase 1 默认 6-10 个 |
| `questions[].id` | string | required | 唯一 ID，短横线或 camelCase |
| `questions[].label` | string | required | 问题标题，≤ 16 个汉字或 40 个英文字符 |
| `questions[].type` | enum | required | `"radio"` / `"checkbox"` / `"select"` / `"text"` / `"textarea"` / `"direction-cards"` |
| `questions[].required` | boolean | optional | true 时用户必须回答才能提交 |
| `questions[].options` | array | 条件必填 | radio / checkbox / select 必填；每项可为字符串，或 `{ "label": "...", "value": "...", "description": "..." }` |
| `questions[].cards` | array | 条件必填 | direction-cards 必填；每项包含 `id`、`label`，可选 `mood`、`references`、`palette`、`displayFont`、`bodyFont` |
| `questions[].maxSelections` | number | optional | 仅 checkbox 生效 |
| `questions[].placeholder` | string | optional | text / textarea / select 可用 |
| `questions[].allowCustom` | boolean | optional | 兼容旧字段；radio / checkbox / select / direction-cards 前端都会在每题选项后显示自定义输入，不依赖该字段 |
| `questions[].customLabel` | string | optional | 自定义输入前缀；省略时前端按界面语言本地化（中文界面为「其他」）。提供时必须使用用户语言 |
| `questions[].customPlaceholder` | string | optional | 自定义输入 placeholder；省略时前端按界面语言本地化。提供时必须使用用户语言 |
| `submitLabel` | string | optional | 提交按钮文案，≤ 24 字，使用用户语言 |

### 选项密度规范

- radio / checkbox / select 的 `label` 必须是短标签：2-10 个汉字优先，最长不超过 16 个汉字或 32 个英文字符
- 不要把解释、类比、括号说明写进 `label`；需要解释时放进 `description`，但 description 也要短，≤ 36 个汉字
- 每题选项建议：radio 3-5 项，checkbox 4-8 项，必须包含一个 `value` 为 `decide` 的兜底委托项；其 `label` 用用户语言表达「你来判断 / 不确定」的语义（英文如 `You decide`）
- radio / checkbox / select / direction-cards 每个问题后面都会有一个固定选项之外的输入框，用于用户补充自定义内容
- 优先使用高密度 chip 选择：短问题 + 短选项；避免大段方案文本塞进选择项
- 只有视觉方向确实需要色板/字体样张时才用 `direction-cards`，否则用 radio chips
- 每张 Phase 1 表单最后必须放一个可选文本题：`id: "notes"` / `type: "textarea"`，`label` 用用户语言表达「补充说明」的语义（英文如 `Anything else`），让用户一次性补充未覆盖的信息

### Deck / PPT 类 Phase 1 表单硬规则

当 `TASK_ROUTER.md` 判定 `used_mode == "deck"`，或用户首句包含 PPT / slides / presentation / deck / 演示 / 幻灯片 / 分享稿时，Phase 1 **必须**先输出一张 deck 表单。即使用户给了 PDF、论文、页数、风格或“你来判断”，也不能直接开始做。表单一次包含 6-10 个问题，问题 ID 优先使用下列语义，避免后续二次确认（下表「标签」列是中文场景的语义示意，实际 `label` 按 §0.5 用用户语言生成）：

| ID | 标签 | 类型 | 目的 |
|---|---|---|---|
| `deckPurpose` | 演示目标 | radio | 汇报 / 融资 / 技术分享 / 教学 / 你来判断 |
| `audience` | 目标观众 | radio 或 checkbox | 高管 / 投资人 / 产品团队 / 技术团队 / 公开传播 |
| `slideCount` | 页数时长 | radio | 5-6 页 / 8-10 页 / 12-15 页 / 你来判断 |
| `narrativeStructure` | 叙事结构 | radio | 问题-方案 / 故事线 / 数据报告 / 产品发布 / 你来判断 |
| `visualStyle` | 视觉风格 | radio 或 direction-cards | 商务克制 / 科技 HUD / 编辑杂志 / 极简白底 / 你来判断 |
| `speakerNotes` | 讲稿深度 | radio | 每页简短口播稿 / 每页完整逐字稿 / 你来判断 |
| `dataAndAssets` | 数据素材 | checkbox | 用用户素材 / 可信 mock / 需要图表 / 需要示意图 |
| `deliveryShape` | 交付形态 | radio | 可演示 HTML deck / 带讲稿模式 / 兼顾打印 PDF |
| `notes` | 补充说明 | textarea | 收集未覆盖要求 |

Deck 表单不问 PPTX 导出；如用户主动提 PPTX，先说明当前主产物仍是 HTML deck，PPTX 属于后续导出/转换链路。

Deck / PPT 产物默认必须包含 Speaker Notes。`speakerNotes` 只用于决定讲稿深度，不用于决定是否生成；用户跳过或选择“你来判断”时，默认每页写 80-160 字的简短口播稿。notes 不是页面摘要，必须像演讲者提词器里的自然话术：能直接念给观众听，包含开场衔接、核心解释和过渡句。

### 用户回复后处理

- 前端会回传一条机器序列化消息（语言中立脚手架，与用户语言无关）：
  - 首行：`[AutoClaw synthetic interaction event]`
  - 第二行：`The user answered the previous <question-form>:`
  - 之后是 `[form answers - {表单 id}]` 与每行 `- {label}: {displayValue}`
  - 自定义输入以 `Custom: ` 前缀标出；`(not specified)` 表示用户跳过该项
- 历史会话可能仍是旧格式（`用户对上一条 <question-form> 的回答：` 开头、`未指定` 表示跳过、`自定义：` 前缀），两种格式按同样语义消费
- 收到回复后，按 `label` 对应原问题消费答案
- **回传消息是机器文本，不得据此切换回复语言**（见 §0.5）；回复语言跟随用户最近一条真实消息
- 收到表单回复后，不要重复输出同一张表单；继续下一步。表单答案仅用于当前设计任务，不得自动写回 `USER.md`，也不得宣称已经跨会话保存

### 前端约定（无需在 payload 中声明，模型仅作了解）

- **卡片标题**：payload 未提供 `title` 时，前端按界面语言显示默认标题（中文界面为「信息补充」）；提供 `title` 时用用户语言书写
- **跳过按钮**：前端默认显示「跳过」类按钮，文案按界面语言本地化，行为由前端控制
- **底部说明文案**：由前端按界面语言本地化
- **自动继续**：前端在底部显示 90 秒倒计时；用户无操作超时后会按当前已填内容自动提交，未填项按 `(not specified)` 处理；用户点选或输入后倒计时重新开始
- **自定义输入**：选择题后置的自定义输入由前端自动渲染（文案按界面语言本地化），不需要把它写进 `options`

### 历史兼容

- `<ask>` 是旧协议，前端可能仍会解析历史消息
- 模型在设计专家当前协议下**禁止主动输出 `<ask>`**
- 旧文档或旧记忆里提到 `ask` 时，一律按本节改写为 `<question-form>`

---



## 2. 动作 · `status`（向用户播报状态）

### 何时使用

- 每次 plan 中 step 状态变动（pending→running、running→done）都必须更新一次 status；Phase 切换、任务开始、任务结束同样必须更新；任务结束前所有 step 的 status 必须为完成态。

### 完整范例

```
<status>
{
  "tone": "info",
  "title": "已进入 App 设计工作流",
  "detail": "当前是 Phase 1（生成），我们这就开始吧。"
}
</status>
```

### 字段约束

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `tone` | enum | required | `"info"` / `"success"` / `"warning"` / `"error"` |
| `title` | string | required | 主消息，≤ 20 字 |
| `detail` | string | optional | 副消息，≤ 60 字，可省略 |

### 注意

- `status` 是**单向播报**，不等待用户回复，前端渲染完即可继续后续输出
- 不要用 `status` 提问——提问一律用 `<question-form>`

---



## 3. 动作 · `plan`（声明并更新进度面板）

### 何时使用

- **每个新会话开始**、决定好走 App / Web 等路径后，**第一时间**输出一份完整 `<plan>`，告诉用户后续要走哪几步
- 阶段切换时**重发完整 `<plan>`**，并把对应步骤的 `status` 更新为 `running` 或 `done`
- 用户调整需求导致流程重新分叉时，重发新的 `<plan>` 覆盖旧的

> 前端只看**最近一条** `<plan>`，旧的会被完全覆盖。所以每次都要发完整数组，**不要**只发增量。

### 完整范例

```
<plan>
{
  "steps": [
    { "id": "clarify",  "label": "需求澄清",     "status": "done" },
    { "id": "ia",       "label": "信息架构",     "status": "running" },
    { "id": "visual",   "label": "视觉规范",     "status": "pending" },
    { "id": "proto",    "label": "原型交付",     "status": "pending" }
  ]
}
</plan>
```

### 字段约束

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `steps` | array | required | 1-12 个步骤；超出取前 12 个；按数组顺序展示 |
| `steps[].id` | string | required | 稳定标识，更新时通过 id 找回原步骤；同名 id 后者覆盖前者 |
| `steps[].label` | string | required | 显示文案，≤ 12 字 |
| `steps[].status` | enum | required | `"pending"` / `"running"` / `"done"`；非法值视为 `pending` |

### 注意

- `<plan>` 是**单向播报**，不等待用户回复
- **没有 fallback**：在你输出第一份 `<plan>` 之前，前端进度面板**完全不显示**——用户看不到任何进度感，所以请在路径确定后尽早发
- **每次都要发完整 steps 数组**：删除某个步骤只能通过新 `<plan>` 不再包含它来实现
- step 的状态可以**回退**（如发现还需返工，把 done 改回 running），前端会据实更新
- 每条 assistant 消息**最多一个 `<plan>`**

---



## 4. 动作 · `show-tweaks`（可调参旋钮）

### 何时使用

- Phase 1 / Phase 2 让用户**当场微调**主色、密度、字体等参数
- 当预览区已经有可查看的结果，希望用户通过“全局微调”继续做**同文件、同结构**的视觉调优时，优先输出这个标签

### 完整范例

```
<show-tweaks>
{
  "title": "实时微调",
  "subtitle": "调整后预览会自动更新",
  "knobs": [
    {
      "key": "primaryColor",
      "label": "主色",
      "type": "color",
      "default": "#0066FF",
      "presets": ["#0066FF", "#FF6B35", "#1A1A1A", "#16A34A"]
    },
    {
      "key": "density",
      "label": "信息密度",
      "type": "slider",
      "min": 1,
      "max": 5,
      "step": 1,
      "default": 3,
      "labels": { "1": "低密", "2": "概览", "3": "均衡", "4": "详尽", "5": "高密" }
    },
    {
      "key": "fontFamily",
      "label": "字体",
      "type": "select",
      "options": [
        { "key": "sans", "label": "Sans 系（默认）" },
        { "key": "serif", "label": "Serif 系" },
        { "key": "mono", "label": "Mono 系" }
      ],
      "default": "sans"
    }
  ]
}
</show-tweaks>
```

### 字段约束

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `title` | string | required | 卡片标题，≤ 10 字 |
| `subtitle` | string | optional | 副标题，≤ 40 字 |
| `knobs` | array | required | 1-6 个旋钮 |
| `knobs[].key` | string | required | 字段标识，camelCase，与 design-tokens.json 字段对齐 |
| `knobs[].label` | string | required | 显示名，≤ 8 字 |
| `knobs[].type` | enum | required | `"color"` / `"slider"` / `"select"` / `"toggle"` |
| `knobs[].default` | any | required | 默认值，类型与 type 匹配 |
| 其它字段 | — | — | 按 type 而定（color 用 presets / slider 用 min-max-step / select 用 options） |

### 注意

- 前端会把最新一条 `<show-tweaks>` 渲染成预览区的“全局微调”面板；用户点击“应用”后，会把自由文本描述和当前 knobs 值一起回传给 agent
- 用户拖动/切换 knobs 时，前端会先做 preview-only 的实时视觉预览；这不会改写源文件，只有点击"应用"后才进入正式生成；**"应用"等同于一次 Phase 2 修改，必须按 OUTPUT_RULES §二 / §三 升 V{N+1} 并把旧版进 archive/，禁止原地覆盖。模型在同一轮 assistant 消息内合并落地用户的连续 tweaks 应用为一次 V +1。**
- 如果这次修改后仍然适合继续微调，请在新的 assistant 消息里再次输出完整 `<show-tweaks>`，用于刷新下一轮可调项
- `信息密度` 代表单位面积内承载的信息量和布局承载方式：低密度信息更少、布局更舒展，减少或弱化辅助说明、标签、状态、次级字段和二级模块；高密度信息更多、布局更紧凑，增加字段、标签、状态、说明、对比项和二级模块。不要把它等同于单纯缩小间距
- 信息密度 1-5 档必须有明确差异：1 只保留核心标题/关键指标/主行动，布局倾向单列大卡片；2 展示主信息和少量摘要，减少标签/说明/列表露出；3 主信息与常规辅助信息均衡；4 增加说明/标签/状态/列表露出，可增加网格列数或并列模块；5 最大化字段/状态/对比项/二级模块，可使用多列、分栏、表格化、紧凑卡片，同屏信息最多
- `slider` 会以前端滑杆呈现，适合信息密度、圆角、阴影强度、留白等级这类连续参数；其中留白/间距应单独建 knob，不要混入信息密度

---


## 5. 扩展规范：怎么添加新动作

未来需要新交互动作时，按以下流程加：

1. **先问"调用方是谁"**——如果没有任何 .md 文件会调用这个新动作，**不要**加
2. **沿用 §0 通用约定**——标签格式、命名规则、必填标注一律遵守
3. **必须给完整可粘贴范例**——只写字段表不给范例的动作约等于没定义
4. **字段约束必须穷举**——type/length/enum 写清楚，避免模型自由发挥
5. **同步通知调用方**——在调用方文件里写明"调用 INTERACTIONS.md `<新动作>`，参数：……"
