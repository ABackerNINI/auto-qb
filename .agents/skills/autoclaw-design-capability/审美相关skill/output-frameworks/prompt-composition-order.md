# Prompt Composition Order · 模式驱动的资源装配规则

> 🎯 **存在意义**：复刻 open-codesign [`packages/core/src/prompts/compose-full.ts`](https://github.com/) `composeFull(mode)` 函数到 markdown 协议层。
> 让 agent 在 Phase 1 任务路由完成后，按 `used_skill` 的 `od.mode` **决定该读哪些资源、什么顺序**。

> 由 [TASK_ROUTER.md §2.6](../../TASK_ROUTER.md) 引用，agent 实际执行入口在 TASK_ROUTER，本文件是"规约 spec"。

---

## 一、为什么需要这一层

不同 mode 的输出形态完全不同——硬塞同一套指令既冗余又会让 agent 走偏：

| mode | 主交付 | 关键约束 |
|---|---|---|
| `prototype` | 可预览 HTML 原型（单页或多页） | 触控目标 / 状态枚举 / 真实 mock |
| `deck` | 16:9 slide deck（HTML 内含 scale-to-fit） | Canvas 1920×1080 / 4 类型轮换 / 字号 ≥ 24px |
| `template` | 设计系统 handoff（DESIGN.md + 示例页） | Token 体系完整 / 跨屏复用 |
| `image` | 静态图（海报 / 封面 / banner） | 不需要 interaction / 强视觉冲击 |
| `video` | 短视频脚本 / 分镜（md） | 时序 / 镜头语言 |
| `audio` | 音频脚本 / 提示词（md） | 节奏 / 时长 |

我们目前**只实施 `prototype` + `deck`**——其它 mode 框架未来按需扩展。

---

## 二、装配顺序（mode = `prototype`）

```
Phase 1 任务路由完成后，按下面顺序 view（**严禁跳读**）：

[1] 锁定文件（已有，跨 mode 通用）
    ├─ AGENTS.md §0 §2  ← agent 自我定位 + 启动协议（启动时已读，此处不重读）
    ├─ OUTPUT_RULES.md  ← 全局输出规则 + §三·补 输出前必读三件套
    ├─ DESIGN.md §三 §十二 ← 思维四问 + 验证清单
    └─ INTERACTIONS.md §1 ← 提问 schema（若需 question-form）

[2] 输出框架层（本目录）
    ├─ designer-prompt.md         ← 工作姿态（每个新项目读一次，迭代不重读）
    └─ discovery-philosophy.md    ← pre-flight 7 问（写代码前必跑）

[3] 三轴资源（TASK_ROUTER 已选定）
    ├─ skills/<used_skill>/SKILL.md  或
    │  design-skeletons/<used_skill>/SKILL.md + example.html  ← clone 起点
    ├─ design-systems/<used_design_system>/DESIGN.md  ← token 来源
    └─ craft/<each-required>.md  ← 按 SKILL.md od.craft.requires 数组

→ 开始写第一行代码 → MEDIA: 预览 → 自检 → 归档
```

---

## 三、装配顺序（mode = `deck`）

```
[1] 同 prototype，加 ↓

[2.5] **deck 专用**
    └─ output-frameworks/deck-framework.md  ← 16:9 幻灯片预览 + 4 类型 + 页码条 + scale-to-fit

[3] 三轴资源 + deck 类 skill 的 example.html

[4] Phase 1 必经交互
    └─ 在写 slides / 读素材 / 发 plan/status 前，先输出 INTERACTIONS.md §1 的 deck question-form，
       一次问清受众 / 页数 / 叙事 / 风格 / notes / 素材 / 交付形态。
       用户跳过或超时后再自行判断，不能因为 brief 看起来完整而跳过。

→ 实施时按 deck-framework §五 流程
→ Phase 3 自检在 OUTPUT_RULES §四 9 项之上加 deck-framework §六 的 7 项
```

---

## 四、装配顺序（mode = `template`）

```
[1] 同 prototype

[2.5] **template 专用 · TODO**（待补 `template-framework.md`）
    └─ 目前 fallback：参考 design-systems/*/DESIGN.md 自身结构 +
       OUTPUT_RULES §三 关于多文件 handoff 的部分

→ 输出：DESIGN.md（项目级） + 至少 2 个示例 HTML + token 一览
```

---

## 五、跨 mode 共通的"省略层"（已经在锁定文件覆盖，**不重复**）

下面这些 open-codesign 那边的 prompt section，我们**没有移植**，因为已被现有 lock 文件等价覆盖：

| OSS section | 我们的覆盖位 |
|---|---|
| `identity.md` | 已部分在 SOUL.md + 部分在 designer-prompt.md |
| `workflow.md` | AGENTS §0 + TASK_ROUTER §1-2 + skill 自己的 SKILL.md |
| `output-rules.md` | OUTPUT_RULES.md（更严更细） |
| `design-methodology.md` | DESIGN.md §三 + discovery-philosophy.md §设计方法论 |
| `pre-flight.md` | discovery-philosophy.md §写第一行代码前 |
| `editmode-protocol.md` + `tweaks-protocol.md` | **跳过**——autoclaw 平台无 EDITMODE 工具 |
| `anti-slop-digest.md` | craft/anti-ai-slop.md（更细） |
| `brand-acquisition.md` | OUTPUT_RULES §三·补 输出前必读三件套（更严） |
| `multi-screen-baton.md` | OUTPUT_RULES §二 版本管理 + DESIGN.md 跨屏 token 一致性 |
| `safety.md` | AGENTS.md §🚨 + §🛡️（更细） |

> 维护规则：若 open-codesign 更新 `compose-full.ts` 引入新 section，先评估是否已被我们 lock 文件覆盖——能覆盖就不在本目录写，无覆盖才补一个 `output-frameworks/<name>.md`。

---

## 六、Agent 怎么用本文件（实操指引）

**Phase 1 任务路由后**，TASK_ROUTER 的 §2.6 会引用本文件指示 agent：

1. 读本文件二、三、四节，根据 `used_skill` frontmatter 的 `od.mode` 字段决定走哪条装配路径
2. 按该路径 view 列出的资源（已 view 过的不重 view）
3. 然后才允许写第一行 HTML

**Phase 2 迭代**时：

- 已 view 过的资源不重 view，直接基于既有 HTML 改
- 但若用户提的修改涉及**新 craft / 新 design-system**（罕见，因 OUTPUT_RULES §一 禁止 Phase 2 重选 skill / design-system，但 craft 可能临时补一个），需 view 该新资源再改

---

## 七、自检（在 Phase 3 自检 §四 第 6 项之上）

**第 6 项已在 OUTPUT_RULES §四 定义**——通过对话上下文中的工具调用历史验证 view 完整性。

本文件**不额外加自检项**——装配顺序对了，view 痕迹自然在工具调用历史里能查到。

---

## 八、出处

本规约的"mode-driven assembly"思想来自 open-codesign `compose-full.ts`（MIT, [NOTICE.md](../NOTICE.md)）。我们只在 markdown 协议层重写了等价的装配规则，未抄袭原代码。
