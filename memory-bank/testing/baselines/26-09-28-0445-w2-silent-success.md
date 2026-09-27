# 基线 · 1818 passed + 3 skipped · 0 warnings —— W2-4 成功静默(silent_success 旗标)落地

> 摘要: 用户追补: test.full 成功时连「略过 N 行」提示也不要。做成任务级显式旗标
> silent_success(test.full/test.quick 声明): 引擎成功路径只出结论行(_digest conclusions_only,
> 无结论形态退回末 N 行不变盲), 提示不打; 信息类命令(kb.active 等)不加旗标——有损摘要靠提示
> 兜底, 一刀切会静默吞内容。真机验收: test.full 可见 = [ok]+TOTAL+passed 三行(零提示), test.quick
> 两行; 引擎测试 15 项(+4: 旗标解析/提示抑制/无结论兜底/信息类保提示)。
> 基线时间: 2026-09-28 04:45
> 档案: memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md

TOTAL 1818 passed + 3 skipped / 0 failed / 19.8s(并行 4 worker) / warnings 0
覆盖率 91%(12512 语句 / 914 未覆盖 / 4204 分支 / 387 partial)
对比前基线(26-09-28-0432): passed 与覆盖率持平, 零回归; 差异 = 引擎摘要语义(成功静默)。
包测试 57 + 引擎 15 全绿。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
