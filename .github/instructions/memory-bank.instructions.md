---
description: 'Memory Bank pattern: persistent project documentation under a memory-bank/ folder so the AI can resume context across sessions.'
applyTo: 'memory-bank/**'
---

# Memory Bank — 编辑本目录时的规则

> 本文件是 `applyTo: memory-bank/**` 的**路由桩**(只在编辑 `memory-bank/` 时注入)。
> 口径唯二单点: 根 [AGENTS.md](../../AGENTS.md)(粗路由 + 硬约束) · [memory-bank/README.md](../../memory-bank/README.md)(库内细路由);
> 完整规程(会话两端 / 立档阈值 / cap 分级 / 三行头规格)在 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md)。
> 本文件只做路由与结构一览, 不复述任何细则。

## 检索纪律(三步, 2026-11-08 起)

1. `commands run kb.active` —— 最近会话滚动状态
2. [memory-bank/README.md](../../memory-bank/README.md) 细路由 —— 按任务选目录/文档
3. `grep -rn "<词>" memory-bank/` —— 兜底(不确定关键词时); **禁止整读**

❌「read ALL memory bank files at the start of every task」是旧版口径, **已废弃**(记录层四工位零索引, 检索只走上面三步)。
动代码前先扫 `pitfalls/_index.md` —— 全库唯一幸存的生成索引(改码前扫陷阱, grep 替代不了)。

## 当前结构(2026-11-08 重构后)

```
memory-bank/
  README.md                        # 库内细路由 (手写, 口径单点之一)
  active-context/                  # 会话切片 YY-MM-DD-HHMM-<slug>.md (kb.active 读)
  architecture/                    # 架构六包 (入口 overview.md)
  conventions/                     # 协议单点 (doc-forms / webui / code-style / collaboration…)
  pitfalls/                        # 坑档 <类>/<主题>.md; _index.md 是生成物 (kb.index 重建, 勿手改)
  projectbrief.md                  # 项目定位 / 范围 / 领域
  issues/ plans/ reports/ tasks/   # 记录层四工位 (历史件冻结; 检索 = grep + kb.nav(人))
  testing/                         # baseline.md · real-machine.md · baselines/ (冻结快照)
```

## 改完让机检全绿

`commands run kb.check`(切片 / 词表 / 认领链 / 日期守卫) 与 `commands run doc.links`(相对链接),
均已挂提交闸门; 会话协议与收尾 DoD 见 skill —— 本文件是路由桩, 不是第二套规范。
