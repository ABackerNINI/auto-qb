# 评审 trailer 与批次锚点

> 摘要: Review trailer 范围自由文本里「数字+行」会被行数解析抓走; 批次锚点是最近一条带 `Review:` **或** `Review-Skip:` 的提交, 手猜基线会偏宽。
> 等级: L0
> 触发: 写 Review trailer, 算批次基哈希, ship.commit 评审留痕判红

### trailer 范围段「数字+行」被行数解析误抓

- **触发**: `Review:` trailer 的范围字段写成含「数字紧邻行」的自由文本, 如「闸门二进制0行批 · 116 行」(2026-11-09 实测)。
- **判别**: 闸门判红「`Review:` 声明 0 行 ≠ 实算 116 行」—— 解析从范围段抓走了「0行」当声明行数, 你写的 116 被无视。
- **处置**: 范围段避开「数字紧邻行/文件」的写法(改「闸门二进制绕过批」); 行数声明只认 `· N 行` 字段。判红后先看范围段有没有误导串再改数字。

### 批次锚点是最近一条 `Review:` **或** `Review-Skip:` 提交, 手猜会偏宽

- **触发**: 手工 `git log --grep '^Review:'` 找批次基线跑 review.pack(2026-11-09 实测, 漏了 `Review-Skip:`)。
- **判别**: ship.commit 判红「声明 N 行 ≠ 实算 M 行」且 M 远小于 pack 的 diff 统计 —— 锚点偏宽, 把已入库的入池/记账提交也滚进了批次。
- **处置**: 不手猜 —— review.pack 的基线取最近一条带 `Review:` **或** `Review-Skip:` 的提交(grep 模式写 `'Review-Skip:|^Review:'`), 或直接以闸门实算为准重跑 pack 换基哈希; 派遣评审时把滚入的已评提交在提示里声明清楚。

**Refs:** memory-bank/tasks/26-11-09-rule-issue-fix-batch.md
