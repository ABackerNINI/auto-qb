# 3763 passed + 2 skipped(根) —— activeContext 条数债务清偿(删 90 留 60, 纯文档轮)

> 摘要: activeContext 条数债务清偿(删 90 留 60, 纯文档轮)
> 基线时间: 2026-10-19 23:09

## 验收数字

`commands run test.full` 实测:

```text
TOTAL                                                20575    372   6954    257    98%
3763 passed, 2 skipped in 127.68s (0:02:07)
```

口径注记:

- 覆盖率 98%(门限即 98%; **纯文档轮零代码改动**, 语句/分支计数与上基线的 ±个位数差异来自既有跳过条件的
  环境门控, 非本轮引入 —— 本轮改动面全部在 `memory-bank/` 文档与 `.openclaw` 之外的 scratch, 无一进入
  收集面)。
- 2 skipped 为既有条件跳过(与本轮无关)。
- 收口机检(先于 test.full 逐条全绿): `kb.check`(主键 733 / 认领链双向闭环 / 结构 / 回写措辞 / 新增面 /
  日期守卫) · `doc.links` · `doc.caps`(4 项既有字符债务原样) · `kb.active`(页脚 60 ≤ 70, 条数债务行消失)。

## 本改动面

- `memory-bank/activeContext/`: 删除 90 个滚动状态切片(150 → 60; 档案 Done/Dropped 且 ≥12h 的 41 片 +
  无档案且 ≥5 天的 49 片, 后者逐片语义 grep 复核全部已有坑档/同专题档案/报告/计划归宿, 免蒸馏)。
- `memory-bank/tasks/` ×29: 各档案 `**Refs:**` 行摘除指向已删切片的 token(docmap 声明方强校验目标存在),
  两个 token 的空行整删; `tasks/26-10-12-webui-column-picker.md` 另剥一条指向已删切片的内链留文本。
- `memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md`: 本轮状态条目 + 「债务判据速记」补
  2026-10-19 机检判据细化(声明方三分: 冻结 doc-refs/基线与流水真实链接保留 · tasks Refs/可编辑内链清链后删 ·
  纯文本提及容忍); 互链 2 处改指基线 `26-10-11-1745`。
- `memory-bank/tasks/26-09-30-memory-bank-cap-debt.md`: kb.wrap 进度日志行 + Summary 精编(10-19 轮一句)。
- `memory-bank/pitfalls/ops/console-encoding.md`: 新增「重定向变体: PowerShell 5.1 `>` 落盘 = UTF-16LE」
  条目(触发/判别/处置 + 头部触发词; 本轮实踩: PS 重定向落盘被 UTF-8 读方判 binary, `cmd /c` 转发绕开)。
- 生成物: `tasks/_index.md` 随 kb.wrap / kb.index 重建(21 生成物); 其余索引零变化。
- 零代码 / 零测试 / 零配置改动; 判据与逐类数字的权威记录 = 切片 `activeContext/26-09-30-2112`(R1 行 + 状态区 2026-10-19 条)。
