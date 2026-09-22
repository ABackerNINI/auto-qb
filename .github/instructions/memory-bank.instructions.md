---
description: 'Memory Bank pattern: persistent project documentation under a memory-bank/ folder so the AI can resume context across sessions.'
applyTo: 'memory-bank/**'
---

# Memory Bank — 编辑本目录时的规则

> 本文件是 `applyTo: memory-bank/**` 的**规则载体**: 只在编辑 `memory-bank/` 时注入, 所以它必须**自足且短**。
> **单点在别处, 本文件不复述**: 完整规程(会话开始 / 收尾 DoD 5 步 / 立档阈值 / 档案模板)在
> [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md); 硬约束(黄金法则 / 红线 / 提交口径)在
> 根 [AGENTS.md](../../AGENTS.md); 库内细路由在 [memory-bank/README.md](../../memory-bank/README.md)。
> 本文件只讲**这个目录本身怎么长、怎么改**。

## 三条铁律

1. **先索引、后 grep、禁止整读。**
   ❌ 「read ALL memory bank files at the start of every task」是**旧版反模式, 已废弃** ——
   它正是本库一度涨到 50 万字符、「必读」退化成「不读」、已记的坑被反复重踩的直接原因。
   ✅ 入口链: `AGENTS.md`(粗路由) → `memory-bank/README.md`(细路由) → `<目录>/_index.md` → 主题文件。
   关键词不明确时 `grep -rn "<词>" memory-bank/` 兜底 —— 每个主题文件头部都写了 `触发:` 动作词, 就是给 grep 用的。
2. **`_index.md` 一律是生成物, 不要手改。** 冲突只需**重跑生成器**, 不要人工合并两版文本。
3. **改完让机检全绿** —— 见末节「收尾」。红了先读判据说的是哪一条, 不要绕过。

## 目录结构 (2026-09-22 目录化重构后)

```
memory-bank/
  README.md              # 库内细路由 (手写, ≤3 KB)
  activeContext.md       # 易变层: 当前焦点 / 下一步 (硬顶 12 KB)
  <专题>/                # pitfalls · testing · progress · systemPatterns · modules
                         #   · conventions · config-reference · rule-system
    _about.md            # 目录元数据: 标题 + 一句话 + 触发 (手写)
    _index.md            # 生成物
    <主题>.md            # 主题文件 (三行头 + 正文)
  tasks/                 # 任务档案 (有独立生成器)
    _index.md            # 生成物
    YY-MM-DD-<slug>.md   # 档案; slug 为英文小写连字符
    attachments/         # 纪要段 / 超长日志 (不递归扫, 不当档案)
  issues/                # 计划外问题池 (HTML, 有独立生成器)
  checklists/            # 人工走查清单
```

**存根**: 被拆掉的原路径(`pitfalls.md` / `testing.md` / `progress.md` / `systemPatterns.md` / `modules.md` /
`conventions.md` / `config-reference.md` / `rule-system.md`)保留 **≤1 KB 存根**, 只为兜住历史计划 HTML 与
issue 报告里的既有引用。
❗**活文档应指向目标文件, 不指向存根** —— 否则每次读多一跳。链接存在性由 `scripts/check_doc_links.py` 验,
但"指向存根"**不会报错**, 只能靠人守。

## 主题文件的三行头元数据 (手写; 索引由它生成)

```markdown
# <标题>

> 摘要: <一句话 —— 索引表里"一句话"列就是它>
> 触发: <逗号分隔的动作词 —— 索引表"触发词"列, 也是 grep 的命中面>

<正文>
```

- 新增一个**目录** = 建目录 + 写 `_about.md` + 写主题文件(三行头) + **重跑生成器** +
  在 [memory-bank/README.md](../../memory-bank/README.md) 的细路由表**登记一行** —— 少一处结构守卫就红。
- 新增一个**主题文件** = 写文件(三行头) + 重跑生成器。

## cap 分级 (超了就是"该拆文件或该外迁"的信号)

| 角色 | 谁 | 上限(字符) |
|---|---|---|
| index | `<目录>/_index.md`、`memory-bank/README.md` | 3,000 |
| index-auto | `tasks/_index.md`、`issues/_index.md`(自动生成, 行数随条目涨) | 12,000 |
| pitfall | `pitfalls/**/*.md` | 6,000 |
| evergreen | `testing/` `systemPatterns/` `modules/` `conventions/` `checklists/` | 10,000 |
| reference | `config-reference/` `rule-system/` | 12,000 |
| volatile | `activeContext.md`(**硬顶**) | 12,000 |
| log | `*-history.md`(append-only) | 24,000 |
| task | `tasks/*.md`(其中「历史会话纪要」段 ≤8,000) | 24,000 |

单条内容超 cap ⇒ **先外迁再登记**: `tasks/attachments/` 放档案纪要段与超长日志,
`progress/attachments/` 放超长叙事(原位留首行 + 指针)。

## pitfalls 条目格式

`### <一句话结论>` + `触发` / `判别` / `处置` **三必填**(`守阵` / `复发` 选填), 由守卫机械校验。
踩到**已记的坑**时把该条 `复发` +1, 并在任务档案里写一句**为什么没命中** —— 反复重踩于是变成可排序的数字。

## 任务档案格式 (`tasks/YY-MM-DD-<slug>.md`)

- `**Status:**` 只能取 **4 个英文单词**之一: `In Progress` / `Pending` / `Completed` / `Abandoned`
  (写成 `✅ 完成` 会让两条守阵同时红); 允许 `Completed (…中文说明…)`。
- **五个必备章节, 标题逐字照抄**(守卫按**行首标题**比对 —— 正文里提到不算):
  `## 原始请求` · `## 思考过程与决策` · `## 实现计划` · `## 子任务状态表` · `## 进度日志`
- 立档前先按 slug **查重**; 改完 `Status` 必须重跑 `gen_tasks_index.py`。

## 收尾 (改完 `memory-bank/` 必跑)

```bash
python .agents/skills/memory-bank/scripts/gen_tasks_index.py     # 改了档案 Status / Summary
python .agents/skills/memory-bank/scripts/gen_kb_index.py        # 改了任何主题文件的三行头
python .agents/skills/memory-bank/scripts/check_kb_structure.py  # 结构: 角色 / cap / 双向一致 / 存根 / 条目字段
python scripts/check_doc_links.py                                # 相对链接存在性
```

四条都已挂 `.commit-flow.toml` 的 `[[gates]]`, 提交时会自动跑; 会话级 5 步 DoD 见 skill。
