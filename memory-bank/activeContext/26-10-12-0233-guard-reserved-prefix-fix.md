# 26-10-12-0233-guard-reserved-prefix-fix — 守阵保留前缀指令分支死支修复(issue 26-10-11-2030)

> 摘要: 用户「认领并修复」issue 26-10-11-2030 —— 守阵 `test_frontend_template_no_reserved_prefix_identifiers` 的指令表达式分支取错捕获组(组 1 = 引号, 表达式在组 2), 指令形态检出能力恒为 0 且全绿无征兆(26-10-03-1412 的复发形态按设计该由它拦)。复验仍复现; 修 = 消费处改 `group(2)` + 扫描抽单点 `_reserved_prefix_problems` + 恒久活性探针(两条形态已知违规必须命中 / 白名单内建必须放行); 真注入红验过(还原复绿); 修前存量预览零违规。issue 置 Done; 坑档 `pitfalls/testing/guard-dead-branch.md`(扫描型守阵死支/活性探针/红验纪律); 全量数字见 `commands run kb.baseline`。
> 最后活动: 2026-10-12 02:33
> 状态: Done(本专题本轮完结)

## 现在做到哪

- 修复已落地 `tests/test_webui_static_dom_page.py`(单文件, 立档阈值未命中 → 不立档): 模块级 `_RESERVED_PREFIX_SPAN_PATS`(每形态标注表达式组号) + `_RESERVED_PREFIX_WHITELIST` + `_reserved_prefix_problems()` 扫描单点; 守阵尾部双探针(活性 + 白名单)。
- 红绿双验: 修前白名单回退复刻假绿(死支实证) → 修后绿 → 真注入红(`ctx-menus.html:281` 的 `_probeRed` 被精准报出) → 还原绿。
- P5 切片(26-10-11-2015)「顺带发现(待认领)」指针已更新为已修。

## 产物

- 代码: `tests/test_webui_static_dom_page.py`(守阵重构 + 恒久活性探针)
- issue: `memory-bank/issues/26-10-11-2030-test-guard-reserved-prefix-directive-dead.html`(Open → In Progress → Done)
- 坑档: `memory-bank/pitfalls/testing/guard-dead-branch.md`(新)
- 基线: `memory-bank/testing/baselines/26-10-12-0233-guard-reserved-prefix-fix.md`

## 下一步 / 遗留

- 无遗留。同类扫描型守阵再扩覆盖形态时, 照坑档口径给每条宣称形态配「合成样例必须命中」断言。
