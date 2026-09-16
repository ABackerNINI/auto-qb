# Output Frameworks · 输出框架层

> 🎯 **存在意义**：复刻 open-codesign 的 `composeSystemPrompt`（[源 packages/core/src/prompts/compose-full.ts](https://github.com/the-actual-source) 的 11-section 装配能力）到 markdown 协议层。
> 让 agent 在 Phase 1 输出前按 `od.mode` 装配正确的"输出框架"——单页原型 vs deck vs 文档 vs 多页交付走不同骨架。

---

## 这一层补的是什么空白

旧架构 `infinite-canvas-output/` 是山寨的、跟 open-codesign 真源对不上。删掉后我们暂时丢失了**三件套交付（项目介绍 + 设计规范 + 页面设计）** 的能力——OSS 那边的实现是：

1. **系统 prompt** 11 个 section 按模式装配（`compose-full.ts`）
2. **`scaffold()` 工具** 提供 `slide-deck.jsx` / `landing-page.jsx` 等 starter 让 agent clone 起手
3. **多屏 baton** `DESIGN.md` 跨屏一致性

我们用 markdown 协议复刻这套：

| OSS 那边 | 我们这边 |
|---|---|
| `composeFull(mode)` 函数 | `prompt-composition-order.md` 装配规则 + TASK_ROUTER §2.6 让 agent 按序读 |
| `identity.md` section | `designer-prompt.md`（中文化 + autoclaw 平台适配） |
| `pre-flight.md` section | `discovery-philosophy.md`（与 DESIGN.md §三 思维四问互补） |
| `slide-deck.jsx` scaffold | `deck-framework.md` （`od.mode==deck` 时强制 view 的 16:9 骨架规约） |
| `output-rules.md` section | 已有 [OUTPUT_RULES.md](../../OUTPUT_RULES.md) |
| `design-methodology.md` section | 已有 [DESIGN.md §三](../../DESIGN.md) |
| `anti-slop-digest.md` section | 已有 [craft/anti-ai-slop.md](../craft/anti-ai-slop.md) |
| `brand-acquisition.md` section | 已有 OUTPUT_RULES §三·补 输出前必读三件套 |
| `safety.md` section | 已有 [AGENTS.md](../../AGENTS.md) §🚨 §🛡️ |
| `editmode-protocol.md` / `tweaks-protocol.md` | 跳过（autoclaw 平台无 EDITMODE 工具，不需要 inline tweak 协议） |
| `multi-screen-baton.md` | 已隐含在 OUTPUT_RULES 二·版本管理 + DESIGN.md 跨屏一致性 |
| `workflow.md` | 已被 AGENTS §0 启动协议 + TASK_ROUTER + 各 skill 自己的 SKILL.md 取代 |

> ⚠️ **不要在本文件夹复制已有规则**——只填空白。OUTPUT_RULES / DESIGN.md / craft 才是事实唯一源。

---

## 文件清单

| 文件 | 内容 | 何时读 |
|---|---|---|
| [designer-prompt.md](./designer-prompt.md) | Agent 人格 + 工作姿态（identity 中文化） | Phase 1 起手，每个新项目读一次 |
| [discovery-philosophy.md](./discovery-philosophy.md) | 写第一行代码前内部 pre-flight（DESIGN.md §三 四问的扩展） | Phase 1 写代码前 |
| [deck-framework.md](./deck-framework.md) | **`od.mode==deck` 才读**——16:9 slide 骨架 + 1920×1080 canvas + 4 段式 slide 类型 + print 样式 | 当 skill frontmatter `od.mode: deck` 时 |
| [prompt-composition-order.md](./prompt-composition-order.md) | **装配规则**——按 `od.mode` 决定本目录 + OUTPUT_RULES + DESIGN.md + craft 的读取顺序 | Phase 1 任务路由完成后 |

---

## 维护规则

- 本目录文件**总长目标 ≤ 800 行**——过长就回收到已有 lock 文件（DESIGN.md / OUTPUT_RULES.md）
- 跟 OSS 源同步：若 open-codesign 更新 `compose-full.ts`，对照检查本目录是否需要回填
- **绝不在本目录写"具体禁令清单"**（如禁 Inter / 禁 lorem）——那些归 craft；本目录只写"装配 / 流程 / 骨架结构"
- 本目录与 OUTPUT_RULES / DESIGN.md / INTERACTIONS.md 冲突时——**优先 lock 文件**，本目录适配修改

---

## 出处与归属

本目录的设计思想来自 open-codesign（MIT），具体见 [../NOTICE.md](../NOTICE.md)。我们只做了"markdown 协议层移植 + 中文化 + autoclaw 平台适配"，未抄袭原代码。
