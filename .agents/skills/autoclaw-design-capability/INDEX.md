# 资源索引 - INDEX.md

> 🔴 **三轴拼接前必读**——Agent 接到设计任务时，先来这里找候选资源，再交给 `TASK_ROUTER.md` 做拼接决策。
> **禁止 ls 整个 `审美相关skill/` 文件夹**——它有 500+ 个子目录，会瞬间撑爆 context。按本索引导航即可。

---

## 一、三轴架构速览

```
┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐
│ design-skeletons│  │ design-systems/  │  │  craft/        │
│ 84 个 HTML 骨架  │  │ 「穿什么皮」       │  │ 「基本功」       │
│ ⭐ 路由优先       │  │ 149 个品牌库      │  │ 11 条工艺规则    │
└─────────────────┘  └──────────────────┘  └────────────────┘
        +
┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐
│  skills/        │  │ prompt-templates │  │  frames/       │
│  「做什么」      │  │ 102 个 AI 生成    │  │ 5 个设备壳      │
│  106 个 skill   │  └──────────────────┘  └────────────────┘
│  skeleton 无法   │
│  满足时 fallback │
└─────────────────┘
        +
┌──────────────────────────────────────────────────────────┐
│  output-frameworks/  「输出形态」mode-driven 装配层         │
│  5 个 markdown · 复刻 open-codesign composeFull()         │
└──────────────────────────────────────────────────────────┘

调用流程：TASK_ROUTER → 按本 INDEX 找资源 → 拼三轴 →
         §2.6 按 mode 装配 output-frameworks → 按 skill workflow 执行
```

---

## 二、Design Skeletons · 现成骨架（82 个） 路由优先

> 路径：`审美相关skill/design-skeletons/<name>/{SKILL.md, example.html}`
> Skill workflow 强制要求**先 clone 骨架再改**，禁止从空白写。
> 🔴 **路由优先级：skeleton > skill**——同一关键词同时命中 skeleton 和 skill 时，skeleton 优先。详见 `TASK_ROUTER.md Step A`。

### 2.1 PPT / 幻灯片 / 演示 / Deck（42 个）

> 🔴 **PPT 路由详见 `TASK_ROUTER.md Step A-2`**——专项 PPT 按关键词一对一命中，zhangzara 风格族按氛围词二级路由。

**优先推荐**

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `html-ppt-zhangzara-broadside` | 编辑 / 文艺 | 项目BP / 品牌宣言 / 观点演讲 / 泛 PPT 默认兜底 |
| `html-ppt-pitch-deck` | 克制 / 理性 | 商业pitch / 融资 / 路演 / 投资人汇报 |
| `html-ppt-hermes-cyber-terminal` | 赛博 / 未来 / 氛围 | CLI、Agent / 开发工具 / 技术报告 |
| `html-ppt-taste-brutalist` | 粗野 / 科科技 | 技术复盘 / 实验演示 / 游戏相关 / 强观点表达 |
| `html-ppt-zhangzara-bold-poster` | 大胆 / 张力 | 品牌宣言 / 产品发布 / 创意提案 |
| `html-ppt-zhangzara-cartesian` | 克制 / 理性 | 投资观点 / 白皮书 / 理性汇报 |
| `html-ppt-zhangzara-coral` | 大胆 / 张力 | 品牌宣言 / 发布 / 观点演讲 |
| `html-ppt-zhangzara-editorial-tri-tone` | 时尚 / 编辑 | 时尚 / 文化 / 品牌内容 |
| `html-ppt-zhangzara-neo-grid-bold` | 粗野网格 / 大胆 / 张力 | 方案提案 / 品牌 workshop / 产品宣发 |
| `html-ppt-zhangzara-peoples-platform` | 大胆 / 张力 | 文化项目 / 品牌 / 创意产品 / 公共议题 |
| `html-ppt-zhangzara-pin-and-paper` | 手工 / 质感 | 用户研究 / 手工感项目 / 质性研究 |
| `html-ppt-zhangzara-soft-editorial` | 柔和 / 编辑 / 文艺 | 品牌故事 / 编辑内容 / 长文转演示 / 档案 |
| `html-ppt-zhangzara-stencil-tablet` | 手工 / 质感 | 品牌故事 / 档案叙事 / 强视觉表达 |
| `html-ppt-zhangzara-retro-windows` | 复古 / 怀旧 | 复古科技 / 游戏 / Y2K 主题 |
| `html-ppt-zhangzara-retro-zine` | 复古 / 怀旧 | 品牌 / 独立出版 / 社群 / 活动回顾 |
| `html-ppt-zhangzara-sakura-chroma` | 日系 / 复古 / 趣味 | 品牌 / 趋流 / 音乐 / 包装主题 |
| `html-ppt-zhangzara-pink-script` | 氛围 / 暗调 | 音乐 / 夜间活动 / 客华主题 |
| `html-ppt-zhangzara-8-bit-orbit` | 像素 / 趣味 / 活活泼 | 游戏 / 黑客松 / Web3 / 独立工具 |
| `html-ppt-zhangzara-creative-mode` | 大胆 / 色彩 / 张力 | 创意机构 / 设计发布 / 作品集 |
| `html-ppt-zhangzara-daisy-days` | 手绘 / 可爱 / 趣味 | 教育 / 儿童 / 社区 / 友好品牌 |

**普通推荐**

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `html-ppt-course-module` | 克制 / 文艺 | 课程 / 培训 / 工作坊 |
| `html-ppt-zhangzara-biennale-yellow` | 简洁 / 文艺 | 展览 / 计划 / 文化机构 / 简单报告 |
| `html-ppt-zhangzara-block-frame` | 大胆 / 张力 | 独立产品 / 年轻品牌 / 创意pitch |
| `html-ppt-zhangzara-capsule` | 卡通 / 趣味 / 活泼 | 创作者 / 生活方式 / 模块化产品 |
| `html-ppt-zhangzara-grove` | 克制 / 理性 | 汇报 / 观点演讲 / 品牌策划 / 可可持续主题 |
| `html-ppt-zhangzara-mat` | 中世纪 / 温暖 / 亲近 | 社区 / 文化机构宣传 / 生活方式 / 品牌策划 |
| `html-ppt-zhangzara-monochrome` | 克制 / 理性 | 用户研究 / 复盘 / 文本密集材料 |
| `html-ppt-zhangzara-playful` | 趣味 / 洴泼 | 创作者 / 教育 / 年轻品牌 |
| `html-ppt-zhangzara-raw-grid` | 粗野 / 大胆 / 张力 | 创业pitch / 设计型汇报 |
| `html-ppt-zhangzara-signal` | 克制 / 理性 | 用户研究 / 复盘 / 文本密集材料 |
| `html-ppt-zhangzara-studio` | 高能 / 大胆 / 张力 | 创意工作室 / 社区、文化宣传 / 发布会 |
| `html-ppt-zhangzara-vellum` | 克制 / 理性 | 汇报 / 观点演讲 / 品牌策划 |
| `kami-deck` | 理性 / 克制 / 极简 | 内容型演示 / 知识型分享 / 文档型deck |
| `open-design-landing-deck` | 文艺 / 克制 | Keynote / 产品发布 / 编辑式演示 |

**不建议默认使用**

> 仅当前两类里找不到合适风格或使用场景明显不匹配时，再考虑这些模板。

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `guizang-ppt` | 简洁 / 克制 | 独立产品 / 年轻品牌 / 个人pitch |
| `html-ppt-presenter-mode-reveal` | 深色 / 繁杂 | 公开演讲 / 课程讲解 / 技术分享 |
| `html-ppt-testing-safety-alert` | 繁杂 | 说明类deck / 评估式PPT / 安全复盘 |
| `html-ppt-taste-editorial` | 极简 | 研究分享 / 观点演示 / 编辑式deck |
| `html-ppt-zhangzara-cobalt-grid` | 编辑 / 文艺 | 技术创意 / 快速节奏发布 / 研究展示 |
| `html-ppt-zhangzara-long-table` | 温暖 / 亲近 | 社区、文化宣传 / 品牌策划 |
| `html-ppt-zhangzara-scatterbrain` | 活泼 / 趣味 / 卡通 | Brainstorm / 工作坊 / 创意过程 |

### 2.2 Dashboard / 后台（3 个）

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `dashboard` | 理性 / 克制 | B 端后台 / 运营面板 / 数据看板 |
| `live-dashboard` | 简洁 / 直接 | 实时看板 / 团队状态 / 运营监控 |
| `trading-analysis-dashboard-template` | 未来 / 科技 | 行情 / 交易 / 金融分析 |

### 2.3 营销 / 落地页（3 个）

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `pricing-page` | 简洁 / 理性 | 定价页 / 套餐页 / 订阅转化 |
| `saas-landing` | 文艺 / 编辑 | AI / 产品 / 开发者工具 |
| `kami-landing` | 文艺 / 编辑 | 内容演示/产品 |

### 2.4 工具型 App（8 个）

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `ai-assistant-mobile-dashboard` | 理性 / 克制 / 暗调 | AI 助理 / 智能管家手机 Dashboard |
| `kanban-board` | 简洁 / 克制 | 项目管理 / 任务流转 / 协作工具 |
| `meeting-notes` | 简洁 / 理性 | 会议纪要 / 团队协作 / 知识沉淀 |
| `web-prototype` | 简洁 / 留白 | 通用 Web 原型 / 业务页面 |
| `web-prototype-taste-brutalist` | 简洁 / 留白 | 技术复盘 / 实验演示 |
| `web-prototype-taste-editorial` | 简洁 / 编辑 | 内容型 Web / 研究页 / 品牌页 |
| `web-prototype-taste-soft` | 简洁 / 留白 | App 官网 / 轻 SaaS / 消费产品 |
| `mobile-app` | 简洁 / 克制 | 通用移动端 |

### 2.5 内容 / 文档（3 个）

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `blog-post` | 文艺 / 编辑 | 博客 / 专栏 / 长文内容 |
| `docs-page` | 简洁 / 编辑 | API 文档 / 产品文档 / 使用指南 |
| `digital-eguide` | 文艺 / 编辑 / 时尚 | 白皮书 / 电子书 / 预览 |

### 2.6 报告 / 金融（5 个）

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `finance-report` | 简洁 / 理性 | 月报 / 季报 / 财务分析 |
| `dcf-valuation` | 极简 / 理性 | 研投 / 快速评估 / 简报 |
| `ib-pitch-book` | 文艺 / 编辑 | 投行 pitch / 战略选择 / 估值材料 |
| `clinical-case-report` | 极简 / 理性 | 医疗病例 / 临床汇报 |
| `eng-runbook` | 未来 / 科技 / 暗调 | 工程运维手册 / Runbook / SRE / 事故响应 |

### 2.7 工具特化（6 个）

| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `pm-spec` | 简洁 / 理性 | PRD / 产品说明 / 需求评审 |
| `hr-onboarding` | 理性 / 文艺 | 入职 / 员工培训 / 团队 onboarding |
| `weekly-update` | 暗调 / 高级 / 专业 | 周报 / 项目进展 / 团队同步 |
| `social-carousel` | 轻奢 / 新潮 | 社媒轮播 / 活动宣发 / 品牌内容 |
| `invoice` | 极简 / 克制 | 发票 / 账单 / 报价单 |
| `magazine-poster` | 理性 / 文艺 | 内容输出 / 杂志内页 / 观点海报 |

### 2.8 其他（13 个）
| 文件名 | 风格 | 具体场景 |
|---|---|---|
| `orbit-linear` | 简洁 / 清晰 | Linear 日报 / 项目摘要 |
| `wireframe-sketch` | 日系 / 趣味 / 活泼 | 线框稿 / 方案探索 / 低保真原型 / 风格艺术类产品汇报 |
| `hyperframes` | 未来 / 科技 | 数据 / 内容 / 研究报告 |
| `motion-frames` | 动态 / 编辑 | 动画 / 动态海报 / 视频前置视觉 |
| `sprite-animation` | 动态 / 趣味 / 像素 | 像素解释页 / 游戏化视觉 / 活动页 |
| `video-shortform` | 动态 / 影像 / 趣味 | 产品短视频 / 动效 teaser |
| `tweaks` | 简洁 / 克制 | 模板调参 / 方案对比 / 视觉微调 |
| `live-artifact` | 多风格 / 特效 / 动态 | 可刷新报告 / 同步视图 / 数据产物 |
| `critique` | 文艺 / 编辑 | 设计评审 / 视觉审计 / 质量检查 |
| `gamified-app` | 暗调 / 克制 | 习惯养成 / 教育产品 / 个人监督 App |
| `x-research` | / | 实验性 |
| `orbit-notion` | / | Notion 摘要 / 知识库简报 |

---

## 三、Skills · 做什么（106 个）

> 路径：`审美相关skill/skills/<name>/SKILL.md`
> 每个 skill 头部 YAML frontmatter 含 `triggers` 关键词——TASK_ROUTER 按用户首句关键词匹配选 skill。
> 🔴 **skeleton 无法满足时才 fallback 到 skill**——本节列出高频 skill（约 40 个），长尾 skill 靠搜索兜底（见 §十）。

### 3.1 设计评审 / 咨询
- `creative-director` —— 创意总监视角整体把控（20+ 方法论）
- `design-review` —— 视觉审计 + 原子提交修复
- `plan-design-review` —— 高级设计师维度打分评审
- `design-consultation` —— 从零构建完整设计系统
- `taste-skill` —— 视觉调参（density / motion / variance），反 AI slop
- `color-expert` —— 配色科学专家（286K 词参考材料）
- `apple-hig` —— Apple HIG 14 模块顾问
- `ui-ux-pro-max` —— UI/UX 模式库 + 启发式检查

### 3.2 前端 / 网页 / 原型
- `frontend-design` —— 生产级前端 UI/UX
- `frontend-dev` —— 全栈前端 + 电影感动画
- `frontend-skill` —— 落地页 / 网站 / App UI
- `artifacts-builder` —— claude.ai 多组件 HTML artifact
- `web-artifacts-builder` —— claude.ai React+Tailwind artifact
- `canvas-design` —— PNG/PDF 视觉设计
- `login-flow` —— 登录流程原型
- `paywall-upgrade-cro` —— 付费墙 / 升级弹窗设计

### 3.3 PPT / 演示
- `frontend-slides` —— 动画丰富的 HTML 演示
- `slides` —— PptxGenJS 做 .pptx
- `pptx` —— 读取 / 生成 / 调整 PowerPoint
- `pptx-generator` —— MiniMax PptxGenJS 管线
- `nanobanana-ppt` —— AI 风格化 PPT + 文档分析
- `pptx-html-fidelity-audit` —— HTML→PPTX 保真验证

### 3.4 品牌 / 视觉提取
- `brand-guidelines` —— 品牌规范提取
- `competitive-ads-extractor` —— 竞品广告抽取分析

### 3.5 创意 / 内容 / 文案
- `brainstorming` —— 结构化头脑风暴
- `ad-creative` —— 广告创意文案 + 视觉
- `copywriting` —— 营销文案撰写 / 改写

### 3.6 数据可视化
- `d3-visualization` —— D3 图表 / 交互可视化
- `hand-drawn-diagrams` —— Excalidraw 手绘风格图
- `algorithmic-art` —— p5.js 生成艺术

### 3.7 Figma
- `figma-use` —— Figma Plugin API 脚本执行
- `figma-generate-design` —— 代码 / 描述 → Figma 页面
- `figma-generate-library` —— 代码 → Figma 设计系统库
- `figma-implement-design` —— Figma → 生产代码 1:1 还原
- `figma-create-new-file` —— 新建 Figma 文件
- `figma-create-design-system-rules` —— 生成 Figma→Code 设计系统规则
- `figma-code-connect-components` —— Figma 组件 ↔ 代码组件连接

### 3.8 长尾 skill（按类别，INDEX 不逐一列出，靠搜索命中）

| 类别 | 数量 | 代表 skill | 典型触发词 |
|---|---|---|---|
| AI 图片生成/编辑（fal 系） | 12 | `fal-generate` / `fal-image-edit` / `fal-3d` | "生成图片" / "AI 修图" / "3D 模型" |
| AI 图片生成/编辑（其他） | 5 | `imagegen` / `imagen` / `replicate` | "OpenAI 生图" / "Gemini 生图" |
| AI 媒体（Venice 系） | 5 | `venice-image-generate` / `venice-video` / `venice-audio-music` | "Venice 生图" / "AI 音乐" |
| 视频 | 4 | `sora` / `remotion` / `video-downloader` / `youtube-clipper` | "生成视频" / "下载视频" |
| 音频 | 2 | `ai-music-album` / `speech` | "AI 音乐专辑" / "文字转语音" |
| 文档生成 | 5 | `doc` / `docx` / `pdf` / `minimax-pdf` / `minimax-docx` | "生成 PDF" / "生成 Word" |
| GSAP 动画 | 4 | `gsap-core` / `gsap-react` / `gsap-scrolltrigger` / `gsap-timeline` | "GSAP" / "滚动动画" |
| 3D / Shader | 2 | `threejs` / `shader-dev` | "Three.js" / "GLSL shader" |
| 截图 / 浏览器工具 | 4 | `screenshot` / `full-page-screenshot` / `agent-browser` | "截图" / "全页截图" |
| 设计规范 / 体系 | 10 | `platform-design` / `web-design-guidelines` / `shadcn-ui` / `wpds` | "设计规范" / "shadcn" |
| Deck 风格模板 | 7 | `swiss-creative-mode-template` / `editorial-burgundy-principles-template` | 按风格关键词搜索 |
| 其他工具 | 6 | `domain-name-brainstormer` / `gif-sticker-maker` / `hatch-pet` | 按具体功能搜索 |

---

## 四、Design Systems · 穿什么皮（149 个品牌）

> 路径：`审美相关skill/design-systems/<brand>/DESIGN.md`
> 每个品牌一份 9 段式完整规范（含 Agent Prompt Guide 段）

### 4.1 科技 / SaaS（你的核心用户场景）
- `apple` / `linear-app` / `stripe` / `notion` / `vercel` / `figma` / `airbnb`
- `raycast` / `arc` / `airtable` / `bento` / `binance`
- `agentic` / `application`

### 4.2 设计工具
- `figma` / `arc` / `raycast` / `atelier-zero`

### 4.3 金融（用户大盘）
- `binance` —— 加密 / 数字资产
- 其它金融品牌需检查（建议未来补 stripe / robinhood / mercury 等）

### 4.4 抽象风格 / 哲学
- `bento` —— Bento grid 风格
- `artistic` —— 艺术派
- `bold` —— 大胆派
- `brutalism` / `glassmorphism` —— 设计流派

### 4.5 汽车 / 工业
- `bmw` / `bmw-m` / `bugatti`

### 4.6 元资源
- `_schema/` —— **保留勿删**，含 `tokens.schema.ts`（4 层 token schema） + `defaults.css`（默认 CSS）

> ⚠️ 本节仅列代表 22 个。完整 149 个品牌通过 `ls 审美相关skill/design-systems/` 取得。

### 4.7 兜底策略

| 场景 | 怎么选 |
|---|---|
| 用户明确指定品牌（"Linear 风"）| 直接用对应品牌的 DESIGN.md |
| 用户给截图但没说品牌 | 调用 `taste-skill` 推荐 + 用户在 2-3 个候选里选 |
| 用户什么都没给 | fallback 到 `_schema/defaults.css` + `taste-skill` 调参 |

---

## 五、Craft · 基本功（11 条工艺铁律）

> 路径：`审美相关skill/craft/<name>.md`
> 每个 SKILL.md 头部 `od.craft.requires` 数组按需声明拉哪些 craft 注入 system prompt。

| 文件 | 管什么 | 默认是否必拉 |
|---|---|---|
| `typography.md` | 字间距 / 行高 / 孤儿寡母 / tabular-nums | ✅ 默认拉 |
| `typography-hierarchy.md` | 字号层级 / display vs body 配对 | 🟡 文字密集场景拉 |
| `typography-hierarchy-editorial.md` | 编辑式排版 | 🟡 内容站 / 杂志风拉 |
| `color.md` | oklch 优先 / 不发明色 / 对比度 ≥4.5 | ✅ 默认拉 |
| `anti-ai-slop.md` | 反 AI 土味 P0/P1/P2 黑名单 | ✅ **默认必拉** |
| `animation-discipline.md` | 动画节奏 / easing / 不要散落微交互 | 🟡 含动画场景拉 |
| `accessibility-baseline.md` | 焦点态 / alt 文本 / ARIA / 对比度 | ✅ 默认拉 |
| `state-coverage.md` | loading / empty / error 三态完备 | ✅ App / Dashboard 必拉 |
| `form-validation.md` | 表单错误 / placeholder / 验证提示 | 🟡 含表单场景拉 |
| `laws-of-ux.md` | Fitts / Hick / Miller / 错误恢复 | 🟡 强交互场景拉 |
| `rtl-and-bidi.md` | 右到左 / 双向文本 | 🔴 仅阿拉伯语 / 希伯来语场景拉 |

**默认配置**：所有 skill 默认拉 `typography + color + anti-ai-slop + accessibility-baseline` 四件套。

---

## 六、Prompt Templates · AI 生成模板（102 个）


> 路径：`审美相关skill/prompt-templates/{image,video}/<name>.json`
> 含 model / aspect / prompt / source 元数据，prompt 内部用 `{argument name="x" default="y"}` 占位语法。

| 子目录 | 数量 | 用途 |
|---|---|---|
| `image/` | 45 | 生图模板（hero image / 海报 / 概念图） |
| `video/` | 57 | 视频模板（hero animation / 短视频） |

调用方式：skill 内通过 `prompt_template: <name>` 字段引用，agent 拼成最终 prompt 喂给 nano-banana / Veo / Midjourney 等模型。

---

## 七、Output Frameworks · 输出框架层（5 个）

> 路径：`审美相关skill/output-frameworks/<name>.md`
> 🎯 移植自 open-codesign `composeFull()` 的 mode-driven 装配能力。Phase 1 三轴定后、写代码前由 [TASK_ROUTER §2.6](TASK_ROUTER.md) 按 `od.mode` 装配读取。

| 文件 | 何时读 | 内容 |
|---|---|---|
| `README.md` | 维护时 | 本目录说明 + 与 OUTPUT_RULES / DESIGN.md 的边界 |
| `designer-prompt.md` | 每个新项目 Phase 1 起手 | Agent 工作姿态（identity 中文化） |
| `discovery-philosophy.md` | Phase 1 写代码前 | pre-flight 7 问 + 设计方法论（DESIGN.md §三 四问的扩展层）|
| `deck-framework.md` | `od.mode == deck` 时 | 16:9 canvas / 4 类型 slide / scale-to-fit / 页码条规约 |
| `prompt-composition-order.md` | TASK_ROUTER §2.6 引用 | mode 装配顺序规约（spec）|

> ⚠️ 本目录**不重复** OUTPUT_RULES / DESIGN.md / craft 已覆盖的规则——只补真正空白。详见 README.md。

---


## 八、你保留的本地 skill

| Skill | 路径 | 用途 |
|---|---|---|
| `ui-prototype-generator-1.0.0` | `审美相关skill/ui-prototype-generator-1.0.0/` | HTML / Figma 原型生成（open-design 无同类，保留） |

---

## 九、用户大盘场景 × 资源推荐速查

> 用户提到的 4 大业务场景，按优先级匹配资源。

### 🏦 金融 / 投资（量化 / 股票 / ETF / 外汇期权）
- design-skeletons：`finance-report` / `dcf-valuation` / `ib-pitch-book` / `trading-analysis-dashboard-template`
- design-systems：`binance`（其它金融品牌建议未来补）
- craft：默认四件套 + `state-coverage`（行情数据空/error 状态）

### 🏢 企业服务 / B 端 SaaS / 内部系统
- design-skeletons：`dashboard` / `kanban-board` / `meeting-notes` / `pm-spec` / `hr-onboarding` / `weekly-update` / `invoice`
- design-systems：`linear-app` / `notion` / `figma` / `airtable` / `vercel`
- skills：`design-review` / `pptx-generator`（B 端汇报）

### 🤖 AI 产品 / AI Agent 平台
- design-skeletons：**`ai-assistant-mobile-dashboard`** ⭐⭐⭐（AI 助理手机 Dashboard，2026-05-18 新建）/ `html-ppt-pitch-deck` / `html-ppt-knowledge-arch-blueprint`（架构图）/ `mobile-app`（通用兜底）
- design-systems：`agentic` / `arc` / `raycast` / `vercel`
- skills：`taste-skill` / `creative-director`
- **过去的缺口已部分填补**：`ai-assistant-mobile-dashboard` 解决"个人助理 / AI 秘书 / 智能管家"类手机 App 入口。其它如「Agent 工作台 / Prompt 编辑器 / 模型对比」仍待自建。

### 🏭 垂直行业系统（医疗 / 制造 / 政务 / 餐饮 / 体育 / 农业）
- design-skeletons：仅 `clinical-case-report`（医疗）能直接用
- **缺口**：制造 / 政务 / 餐饮等几乎全缺——建议未来按场景补建

---

## 十、检索流程（给 Agent 的硬规则）

```
任务来 → 读 TASK_ROUTER 拿决策框架 → 按方向检索本 INDEX → 拿候选回 TASK_ROUTER 拼三轴
```

### 高频 skill（§三 3.1-3.7）
- 直接在本 INDEX 命中，不需要额外搜索

### 长尾 skill（§三 3.8）
- 本 INDEX 只列类别和代表 skill
- 若 INDEX 没有精确命中 → 用 `grep -rl "关键词" 审美相关skill/skills/*/SKILL.md` 按 triggers 精准搜索
- **禁止 `ls` 整个 `审美相关skill/` 目录**（500+ 子目录会撑爆 context）
- **允许**按关键词 `grep` 搜索具体 skill 的 SKILL.md
- 搜到后可主动在本 INDEX §三 3.8 表格里补一行，避免下次再搜

---

**版本**：v1.0
**适用**：autoclaw 平台「设计专家 Agent · designagent0518」
**维护**：新增 / 删除 skill 后必须同步更新本文件对应章节
