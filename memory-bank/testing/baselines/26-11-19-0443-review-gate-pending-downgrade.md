# 6477 —— 闸门待评审降级与 review.pack 自动锚点收尾基线(鸡生蛋收口批)

> 摘要: 闸门待评审降级与 review.pack 自动锚点收尾基线(鸡生蛋收口批)
> 基线时间: 2026-11-19 04:43

## 验收数字

```
6477 passed, 6 skipped, 7 warnings in 197.33s (0:03:17)
TOTAL  28896     44  10314     61    99%
```

- 对上一切片(sigterm-stall-observability-resampling, 2026-11-19 03:20): passed +11(6466→6477) / skipped 持平 6 / 语句 28870→28896(+26) / miss 43→44(+1) / 分支 10306→10314(+8) / partial 60→61(+1), TOTAL 99% 持平 —— 增量全部来自远端合流的 sigterm-stall S0/S1 观测面批次(8b16784c 等 3 笔), **本批未触 tests/**; 基线 commit = 1ccd69a6(测试跑在纯工作树 + 本批未提交改动之上, 本批不涉 tests/ 与 src/)。

## 本改动面

- .commands/my-commit-flow: gate.py 待评审降级(行首标记识别, 待办行不计失败)+ ship/config.toml note + .my-commit-flow.toml when_message 注释 + references/pipeline.md 同段重写。
- .commands/review: check_review_trace.py rc=3 待评审 + 行首标记 `评审留痕[待评审]:`(契约单点模块头新设「rc=3 待评审」节)/ review_pack.py --base 可选(自动现算锚点回显, 零提交仓库 rc=2)/ config.toml 两处 note。
- 测试扩面: test_gate.py 2 新用例 + 跨包字面量钉面; test_review_pkg.py 4 处 rc 钉面 1→3 + 3 新用例(敏感面待评审 / pack 裸跑自动锚点 / 零提交仓库 rc=2)。包测试两包整跑全绿(数字见 kb.baseline 口径, 不手抄)。
- 文档面: code-review SKILL.md 两处(③ pack 调用形态 / pack 前置预跑语义); 坑档 1 条 ops/commands-engine-rc-normalization(不占测试数字)。
- 真机自检: 纯工具链机械面(提交闸门/评审包), 不落真机轨两类准入(qB 真执行 / 真文件系统·进程·注册表均不涉)。

**Refs:** memory-bank/tasks/26-11-11-docs-ship-gate-prerun.md
