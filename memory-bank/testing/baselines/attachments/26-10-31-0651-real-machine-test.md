# 4196 passed + 2 skipped —— 真机实测轨建立: 规程 + 常驻排期锚(11 片)

> 摘要: 真机实测轨建立: 规程 + 常驻排期锚(11 片)
> 基线时间: 2026-10-31 06:51

## 验收数字

`commands run test.full`(2026-10-31 06:51, Windows, 默认并行):

```text
TOTAL                                               21148     96   7164    100    99%
4196 passed, 2 skipped in 125.25s (0:02:05)
```

覆盖率闸(Windows 99.0)通过; 与上一条基线同值 —— 本轮**零代码改动**(纯文档), 数字本就不该动。

## 本改动面

- **新增** `memory-bank/testing/real-machine.md` —— 真机实测轨的规程(硬约束 5 条 / 环境守卫三层 / 种子层 L0-L2 / 切片更新规则 9 条 / 一轮标准动作 / 漂移判定 / 成熟度 L0-L3 / 用例写法)。
- **新增** `memory-bank/issues/26-10-31-0641-test-real-machine-test-standing.html` —— 常驻排期锚(§03 片表 11 片含路径 glob、§07 覆盖进度总表、§08 变更日志)。
- **新增** `memory-bank/testing/real-baselines/` —— 真机实测数字的落点(与 `baselines/` 分开: 采集面不同, 混在一起无法纵向比)。
- **改** `memory-bank/README.md` —— 细路由加一行(真机实测 → 规程 + 排期锚)。
- 生成物随 `commands run kb.index` 重建: `issues/_index.md` · `issues/attachments/_archive.md` · `testing/_index.md`。
- `src/` 与 `tests/` **零改动**; `tests-real/` 与 `.commands/real/` 由 RM00 建立(本轮只出规程与片表)。
