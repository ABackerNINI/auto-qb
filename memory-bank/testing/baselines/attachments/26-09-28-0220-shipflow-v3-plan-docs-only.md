# 基线 · 1814 passed + 1 known-red —— shipflow-v3 计划轮(纯文档, 零代码改动)

> 摘要: 本轮只产出计划文档(26-09-28-0157)+任务档案+切片+issue(26-09-28-0219), 未改任何源码/测试。
> 跑 test.full 验证回写件与守阵自洽: 1814 passed / 3 skipped / **1 failed** —— 唯一红是
> `test_docs_forms.py::test_doc_map_is_regenerated_and_capped`(doc-map 容量触顶, 生成内容与
> 断言一致、仅超 cap, 已入池 issue 26-09-28-0219 待用户定调, 非本轮引入的缺陷而是本轮合规
> 回写触发的必然)。known-red 不影响本轮"绿"的判定口径: 除该 cap 项外全绿。
> 基线时间: 2026-09-28 02:20
> 档案: memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md

TOTAL 1814 passed + 3 skipped + 1 failed(doc-map cap, 见上) / 24.3s
覆盖率 91%(12504 语句 / 914 未覆盖 / 4204 分支 / 387 partial)
对比前基线(26-09-28-0041): 1813 passed + 3 skipped —— passed +1(远端 alt-speed 轮守阵并入), 零回归;
failed +1 = doc-map cap(issue 26-09-28-0219), 与代码无关。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
