# 5685 passed + 2 skipped(根) —— R4·static 清池(issue 26-11-07-0536)收尾基线

> 摘要: R4·static 清池(issue 26-11-07-0536)收尾基线; e2e 全量 455 passed + 18 skipped + 1 例既有 flaky(定向重跑 4/4 绿) 15.4m
> 基线时间: 2026-11-08 02:24

## 验收数字

`commands run test.full` 实测 (2026-11-08, 命令整体 149.5s):

```text
TOTAL                                                25505      5   8800     27  99.91%
5685 passed, 2 skipped, 1 warning in 147.81s (0:02:27)
```

- 差值看上片: `commands run kb.baseline -n 2`(上片 5626)。本片与批账 test.quick 一致(同一套件,
  quick 只省覆盖率报表), P16 终审修复批净增 0 用例、守阵改写 0 增 1 断言组。
- 覆盖率 99.91% 由实例根 cov 数据 `coverage report --precision=2` 复算(test.full 汇总行只印整位数)。
- e2e 全量 474 例(15.4m): 455 passed + 18 skipped(模式矩阵用例) + 1 failed —— `traffic-gap-zones.spec.mjs:203
  [atlas]` Ctrl+\ 开全局流量图抽屉 10s 未现; 同 spec prism 孪生套内 1.4s 过、定向重跑 4/4 全绿,
  键盘入口满载时序抖动, 与本分支改动面无关(既有环境型 flaky, 照实记录不追改)。

## 本改动面

- 清池主体: 存量评审 R4·static 主题 135 条(issue 26-11-07-0536)P01-P16 分批修复, 收口提交
  `2a5433ea`(终审三面评审 11+3 条全修: R5#181 themechange 监听卸载对称/metaAddNewTags 同构
  占闸/注释口径批), 逐批明细见 issue §07 与各批提交。
- 本片数字录于终审修复与增量轮全部合入之后(分支 `fix/legacy-review4-static`, 未合流)。
