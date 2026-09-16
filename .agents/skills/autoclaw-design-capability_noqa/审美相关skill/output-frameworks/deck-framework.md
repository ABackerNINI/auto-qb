# Deck Framework · 演示稿 / Slide 输出框架

> 🎯 **何时读**：当任务路由后选中的 skill 的 `od.mode == deck`（如 `pitch-deck` / `keynote-slide` / `report-pdf` 类 skill）。
> 其它 mode（`prototype` / `template` / `image` 等）**不读本文件**。

> 移植自 open-codesign [`apps/desktop/resources/templates/design-skills/slide-deck.jsx`](https://github.com/) 的设计骨架 + 我们的 Phase 框架。
> 用 markdown 描述视觉规约，让 agent 在生成 deck 时按本骨架展开——**不抄 JSX 代码**，只抄"是什么样、为什么这样"。

---

## 一、Canvas 规约（硬约束）

| 维度 | 规格 |
|---|---|
| **宽高比** | 16:9（默认）/ 4:3（per skill spec） |
| **画布尺寸** | 1920×1080（默认 16:9）/ 1024×768（4:3） |
| **页边距** | 上下 56px / 左右 72px（约 5%/4%）——不要逼边 |
| **页脚** | 距底 28px，左右各 72px 对齐内容栏 |
| **导出适配** | 必须含 `@page { size: 1920px 1080px landscape; margin: 0; }` print 样式 |

### scale-to-fit JS（嵌入 HTML）

deck 类需要在用户屏幕大小变化时自动等比缩放——不要让用户左右拖滚动条：

```html
<meta name="auto-designer-preview-device" content="slide">

<script>
  function fit() {
    const w = window.innerWidth, h = window.innerHeight;
    const scale = Math.min(w / 1920, h / 1080);
    document.documentElement.style.setProperty('--deck-scale', scale);
  }
  window.addEventListener('resize', fit);
  fit();
</script>

<style>
  body { transform: scale(var(--deck-scale, 1)); transform-origin: top left; }
</style>
```

> ⚠️ 这是给浏览器预览用的；**导出 PDF 时这段 JS 不执行**——但 `@page` 规约会让 PDF 直接是 1920×1080 横版。

### HTML 结构契约

每个 deck 必须是一个可独立打开的 `.html` 文件：

```html
<main class="deck" data-deck>
  <section class="slide is-active" data-slide="1" data-screen-label="Cover">
    ...
    <aside class="notes">这一页可以这样讲：……</aside>
  </section>
  <section class="slide" data-slide="2" data-screen-label="Agenda">
    ...
    <aside class="notes">讲到这里时，先承接上一页……然后把本页核心观点讲清楚……最后过渡到下一页。</aside>
  </section>
</main>
```

- `.slide` 是唯一页面单位；不要用纵向长网页模拟多页 PPT
- JS 负责 ← / → / Space 切页，并同步页码 / 进度
- 每个 `.slide` 都必须有 `<aside class="notes">`，默认不出现在观众视图，只用于端内 notes 面板、演讲者模式和 PPTX 导出；notes 内容必须是给演讲者直接口播的话术
- `data-screen-label` 用于端内文件预览 / 后续导出辅助识别页面

### Speaker Notes 书写规则（强制）

- **每页必写**：slide 数量 == notes 数量；不要只给封面或重点页写 notes
- **默认深度**：用户未指定时，每页写 80-160 字、2-4 句的简短口播稿，帮助演讲者直接开口讲，而不是只记录“这一页要怎么讲”
- **逐字稿模式**：用户选择逐字稿 / 分享稿 / 演讲稿时，每页写 150-300 字口语化讲稿
- **口吻要求**：notes 要像提词器话术，可以直接念给观众听；用“我们先看…”“这里的重点是…”“所以接下来…”这类自然口语
- **禁止写法**：不要写成“封面页：介绍……” / “数据页：展示……” / “本页说明……”这类页面一句话介绍
- **结构建议**：每页 notes 包含一句承接或开场、一到两句核心解释、一句与下一页的过渡；技术/数据页可补充关键解释口径

---

## 二、4 种 Slide 类型（每个 deck 必须用其中至少 3 种轮播）

deck **禁止**整页同一类型重复——观众会昏。强制 4 种轮换：

### 类型 1 · **标题页（SlideTitle）**

```
位置：开场第 1 页，可选闭幕第 N 页
节奏：左对齐 / 大标题占视觉中心 60-80%
组件：
  - 顶部 eyebrow（12px 大间距大写 + 24px accent 短横线）
  - 主标题：60-84px 衬线 + line-height 1.02 + 微负字距 (-1 ~ -2px)
  - 副标题（可选）：22px / 行高 1.4 / muted ink / max-width 640px
  - 演讲者条（可选）：底部头像 36px + 姓名 14px + 角色 12px muted
  - 页脚：页码 nn/total + 横线 + 项目期标识（如 "Q2 · 2026"）
字体：标题用 SERIF（如 Fraunces / DM Serif Display / Georgia），其它 SANS
```

### 类型 2 · **章节分隔页（SlideSection）**

```
节奏：左侧大数字 + 右侧章节标题
组件：
  - 左：MONO 字体 140px chapter 编号（如 "01"），accent 色
  - 右：12px label（"CHAPTER 01"）+ 56px 斜体衬线标题
布局：grid auto 1fr，gap 48px，align baseline
功能：明确告诉观众"我们要切话题了"
```

### 类型 3 · **双栏内容页（SlideTwoCol）**

```
节奏：1.1fr : 1fr 双栏，gap 56px
左栏：
  - 44px 衬线小标题（"The argument"）
  - 3-5 个 list 项，每项含 MONO 序号 + 16px sans body
  - 序号 0-padded 用 MONO + accent 色
右栏：
  - 4:3 aspectRatio 视觉块（图 / 图表 / 截图占位）
  - 渐变背景 = `accent×18% → accent×5%`
  - 边框 1px rule 色
用途：argument 论证、对比、过程图解
```

### 类型 4 · **一个大数字页（SlideStat）**

```
节奏：纯居中，单一焦点
组件：
  - 顶部 eyebrow "ONE NUMBER" + accent 短横线
  - 大数字：200px sans-bold + tabular-nums + -6px 负字距
  - 单位（可选）：36px accent 色，与数字 baseline 对齐
  - caption：24px 衬线斜体，max-width 620px，居中
  - source 行（可选）：11px 大间距大写，muted ink
用途：抓眼球的核心 metric / 论点定锤
```

---

## 三、统一组件（所有 slide 必含）

### 页码条（底部，所有 slide）

```
位置：底部 28px 高度区
左：MONO 字体 `NN / TT` 0-padded 页码（如 "03 / 12"）
中：1px 横线 rule 色，flex: 1
右：SANS 字体 12px 项目期标识（如 "Q2 · 2026" / "Internal Review"）
颜色：全部 muted ink（约 #6b6258 暖灰）
间距：左右与 padding 对齐（72px）
```

### Token（design-system 无明示时的 fallback default）

| Token | 默认值（暖编辑风） | 用途 |
|---|---|---|
| `--accent` | `#CC785C`（铜橙） | 强调 / 数字 / 序号 |
| `--bg` | `#faf8f3`（暖白） | slide 底色 |
| `--ink` | `#1a1a1a`（近黑暖） | 主文字 |
| `--muted` | `#6b6258`（暖灰） | 次文字 / 页脚 / source |
| `--rule` | `#e6dfd1`（暖底鸽灰） | 分割线 |

> ⚠️ **仅 fallback**——若 `used_design_system != null`，全部 token 来自该 brand 的 DESIGN.md，**不用本表默认值**。

### 字体栈（fallback）

| 角色 | fallback 默认 | 何时切换 |
|---|---|---|
| SERIF | `'Fraunces', 'DM Serif Display', Georgia, serif` | 标题 / caption |
| SANS | `'DM Sans', system-ui, sans-serif` | body / eyebrow / footer |
| MONO | `'JetBrains Mono', ui-monospace, monospace` | 页码 / 序号 / source |

> ⚠️ 若 `used_design_system` 明示用 Inter / Geist Mono 等，按 `OUTPUT_RULES §三·补·补` 仲裁规则，design-system 胜。

---

## 四、文案与内容规约

| 元素 | 字数硬限 |
|---|---|
| 标题页主标题 | ≤ 12 字（中）/ ≤ 8 词（英）——超字数换 `font-size: clamp(48px, 5vw, 84px)` |
| 章节标题 | ≤ 16 字 |
| 双栏 list 项 | ≤ 28 字 / 项；≤ 5 项 / 页 |
| 大数字页 caption | ≤ 32 字 |

**禁止**：

- ❌ 一页塞 ≥ 4 段 paragraph（slide 不是 doc）
- ❌ ≤ 24px 字号——观众根本看不清
- ❌ 满版图片占位（必须真图或 SVG，不要 "Image goes here" gray box）
- ❌ 项目符号（•）—— 我们用 MONO 序号 `01 / 02 / 03`
- ❌ lorem ipsum / "John Doe" / 编造 "10,000+ users"——必须**真实可信 mock**

---

## 五、Phase 1 deck 输出流程

```
0. 内部补齐 deck 参数：演示目标、受众、页数、叙事结构、视觉风格、speaker notes 深度、素材来源、交付形态
1. view skeleton example.html（如 pitch-deck/example.html）—— 强制 clone 起点
2. view design-system DESIGN.md —— 取 token
3. view 本文件（deck-framework.md）—— 取幻灯片预览 + 4 类型 + 页码条规约
4. view craft 数组里所有 .md
5. 思维四问（DESIGN.md §三）+ pre-flight 7 问（discovery-philosophy.md）
6. 选 4 类型中至少 3 种排页面顺序
7. 实施：clone example.html → 改 token / 字体 / 文案 / 页面排序 / 每页 speaker notes
8. MEDIA: 唤起预览
9. Phase 3 自检 9 项 + DESIGN §十二 8 项
```

第 0 步的默认值：

| 字段 | 默认策略 |
|---|---|
| 演示目标 | 按用户语义判断：汇报 / 融资 / 技术分享 / 教学 / 产品发布；不明确时按“内部汇报” |
| 受众 | 不明确时按“产品与业务团队” |
| 页数 | 内容少 5-6 页；普通 brief 8-10 页；资料充分 12-15 页 |
| 叙事结构 | 默认“问题 → 洞察 → 方案 → 证据 → 行动” |
| 视觉风格 | 优先沿用选中 skeleton；泛 deck 默认克制编辑风 |
| speaker notes | 默认每页 80-160 字简短口播稿 |
| 素材来源 | 优先使用用户上传/引用素材；没有素材时使用可信占位与结构化图形 |
| 交付形态 | 单文件可演示 HTML deck，兼顾打印基础 |

---

## 六、deck 特有 Phase 3 自检（在 OUTPUT_RULES §四 9 项之上加）

| 检查项 | 通过标准 |
|---|---|
| Canvas 是否 1920×1080（或 1024×768）？ | 用 devtools / 截图 check |
| scale-to-fit JS 是否嵌入？ | 调整浏览器窗口大小，slide 应等比缩放 |
| `@page` print 规约是否含？ | Ctrl+P 预览，应是横版 1920×1080 |
| 4 类型至少用了 3 种？ | 数页面类型分布 |
| 页码条 NN/TT 0-padded？ | 看每页底部 |
| 每页 Speaker Notes 是否齐全？ | slide 数量 == `<aside class="notes">` 数量；notes 不为空且不显示在观众视图 |
| 字号 ≥ 24px？ | body 文字最小 24px / 标题 60-120px / hero 大字 180-240px |
| 真实 mock 数据？ | 无 lorem / 无 "John Doe" |

任一项未过 → 回退 Phase 2 修订。

---

## 七、什么时候 *不* 用本框架

- skill `od.mode != deck`（如 `prototype` / `template` / `image`）→ 跳过本文件
- 用户明确说"做一个 PDF 报告"而非 slide → 走 `report-pdf` skill 的本文件 4:3 变体
- 用户要"infographic 海报"而非 slide → 走 `poster` skill，不读本文件

---

## 出处

视觉规约 + 4 类型设计模式移植自 open-codesign 的 `slide-deck.jsx`（MIT, [NOTICE.md](../NOTICE.md)）；我们只做了"JSX → markdown 规约"翻译 + 与本仓 Phase 框架 / 三轴架构对齐。
