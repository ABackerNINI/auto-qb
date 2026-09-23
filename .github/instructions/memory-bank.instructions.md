---
description: 'Memory Bank pattern: persistent project documentation under a memory-bank/ folder so the AI can resume context across sessions.'
applyTo: 'memory-bank/**'
---

# Memory Bank — 编辑本目录时的规则

> 本文件是 `applyTo: memory-bank/**` 的**规则载体**: 只在编辑 `memory-bank/` 时注入, 所以它必须**自足且短**。
> **单点在别处, 本文件不复述** —— 完整规程(会话开始 / 收尾 DoD 5 步 / 立档阈值 / 档案模板 / cap 分级 /
> 三行头与 pitfalls 字段规格)全在 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md);
> cap 的**机器单点**是该 skill 的 `scripts/_common.py`(`CAP_POLICY`, 守卫 import 它, 别在这里抄一张表);
> 硬约束(黄金法则 / 红线 / 提交口径)在根 [AGENTS.md](../../AGENTS.md); 库内细路由在
> [memory-bank/README.md](../../memory-bank/README.md); 闸门清单在 `.commit-flow.toml`。

## 三条铁律

1. **先索引、后 grep、禁止整读。**
   ❌ 「read ALL memory bank files at the start of every task」是**旧版反模式, 已废弃** ——
   它正是本库一度涨到 50 万字符、「必读」退化成「不读」、已记的坑被反复重踩的直接原因。
   ✅ 入口链: `AGENTS.md`(粗路由) → `memory-bank/README.md`(细路由) → `<目录>/_index.md` → 主题文件。
   关键词不明确时 `grep -rn "<词>" memory-bank/` 兜底 —— 每个主题文件头部都写了 `触发:` 动作词, 就是给 grep 用的。
2. **生成物一律不要手改。** `_index.md` 冲突只需**重跑生成器**, 不要人工合并两版文本 ——
   同理 `tasks/_index.md` / `issues/_index.md`; `activeContext.md` 是 ≤1 KB 存根(滚动状态在 `activeContext/`)。
3. **改完让机检全绿** —— 见末节「收尾」。红了先读判据说的是哪一条, 不要绕过。

## 这个目录怎么长

```
memory-bank/
  README.md              # 库内细路由 (手写)
  activeContext.md       # ≤1 KB 存根; 滚动状态在下面那个目录里 (勿往存根写状态)
  activeContext/         # 会话切片 YY-MM-DD-HHMM-<slug>.md; 有独立阅读器, 不生成 _index.md
  <专题>/                # _about.md(手写) + _index.md(生成物) + <主题>.md(三行头)
  tasks/                 # 档案 YY-MM-DD-<slug>.md + attachments/ (有独立生成器)
  issues/  checklists/
```

- 新增**目录** = 建目录 + 写 `_about.md` + 主题文件(三行头) + **重跑生成器** + 在
  [memory-bank/README.md](../../memory-bank/README.md) 细路由**登记一行** —— 少一处结构守卫就红。
- 新增**主题文件** = 写文件(三行头) + 重跑生成器。
- **存根**: 被拆掉的原路径保留 ≤1 KB 存根, 只为兜住历史计划 HTML / issue 报告里的既有引用。
  ❗**活文档应指向目标文件, 不指向存根** —— 链接存在性由 `scripts/check_doc_links.py` 验,
  但"指向存根"**不会报错**, 只能靠人守。

## 收尾 (改完 `memory-bank/` 必跑)

```bash
python .agents/skills/memory-bank/scripts/gen_tasks_index.py            # 改了档案 Status / Summary
python .agents/skills/memory-bank/scripts/gen_kb_index.py               # 改了任何主题文件的三行头
python .agents/skills/memory-bank/scripts/gen_active_recent.py --check  # 改了会话切片
python .agents/skills/memory-bank/scripts/check_kb_structure.py         # 结构 / cap / 双向一致 / 存根 / 条目字段
python scripts/check_doc_links.py                                       # 相对链接存在性
```

五条都已挂 `.commit-flow.toml` 的 `[[gates]]`, 提交时会自动跑; 会话级 5 步 DoD 见 skill。
