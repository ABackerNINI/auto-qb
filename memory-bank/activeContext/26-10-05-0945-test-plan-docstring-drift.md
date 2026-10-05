# 测试文件头部「## 测试计划」清单与实际函数漂移清理

> 摘要: 认领 issue 26-10-05-0922(docs 便签档)并按用户拍板把范围扩到全 tests/。79 份带「## 测试计划」的测试文件里 11 份共 21 条清单条目指向全仓不存在的函数(幽灵条目)—— 清单只进不出、守阵退役/改名/搬迁后条目无人跟删。逐条裁决「有明确后继则改名, 无后继则删除」: 改名或合并 15 条 · 删除 5 条 · 跨文件指针修正 1 条(`test_state_matrix` 指向的 `test_conditions.py(...)` 已不存在, 实为 `test_config.py::test_validate_state_condition_spec`), 另补登 2 条漏登。**只改 docstring, 不动测试代码**。复扫 79 份文件幽灵 0 条; test.full **2603 passed + 4 skipped / 99%**(40.15s)。
> 最后活动: 2026-10-05 09:45

**Refs:** memory-bank/tasks/26-10-05-test-plan-docstring-drift.md

## 现状

- **修复完成, 待提交**。改动面: 11 份 `tests/*.py` 头部 docstring · issue 状态回填(Open → In Progress → Done, 含修法/验证/数字) · 本切片 · 基线切片 · 任务档案(立档阈值②: 改动 ≥3 个源文件) · `kb.index` 重建的生成物。
- 验证: 幽灵扫描脚本(清单条目 vs AST `def test_*`)改前 21 条 → 改后 **0 条**; `test_config_schema.py` 双向核对幽灵 0 / 漏登 0; `commands run test.full` **2603 passed + 4 skipped / 99% / 40.15s**。
- 未验证面 / 残留风险: 「文件内有、清单无」的漏登只对 `test_config_schema.py` 做了全量核对 —— 多数文件清单本就不穷举(test_web.py 280 个用例只列 ~90 条), 全量补登会是另一件事(已记入档案遗留段)。
- 判据沉淀: 幽灵条目的两种正确处置(改名 / 删除)与两类误报甄别(清单里引用的**文件名**、跨文件引用的用例名)写进了本轮档案的「思考过程与决策」; 扫描器为一次性脚本(临时目录, 已删), 未入库。
