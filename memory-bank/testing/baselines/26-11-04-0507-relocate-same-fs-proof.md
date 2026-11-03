# 5119 —— P6 真机验收后全量基线

> 摘要: P6 真机验收后全量基线(5119 passed + 10 skipped, 根)
> 基线时间: 2026-11-04 05:07
**Refs:**

## 验收数字

`commands run test.full` 实测输出誊写：

```text
TOTAL                                                23893    230   8158    173    99%
5119 passed, 10 skipped in 193.99s (0:03:13)
```

口径：仓库根全量；上一行为 test.full 的覆盖率 TOTAL 表原样誊写，下一行为 pytest 汇总行。分支 `develop`，HEAD `e80d9f8e`，工作树含本轮未提交的真机用例与文档改动（`src/` 未触碰）。
`tests-real/` 三例（RM04-11..13）不在 `testpaths(tests/)` 内，不计入本行；真机实测数字另见本轮 task 档案。

## 本改动面

代码面：与上一基线（`26-11-04-0241`）相同的 P1-P5 产品代码，`src/` 本轮零改动；新增真机用例 `tests-real/rm04_relocate/test_rm04_probe_real.py`（RM04-11/12/13，仓库外轨，不参与本基线计数）。
文档面：新建本基线切片；真机验收记录回写 task 档案、计划 P6、报告 §7.4；计划外缺陷入池 `memory-bank/issues/26-11-04-0504-bug-relocate-d-evidence-container-type.html`。
