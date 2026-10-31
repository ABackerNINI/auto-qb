# 2813 —— HR 排除方案 B 实施计划入库 (计划 26-10-08-1249)

> 摘要: 「HR 排除落到取数侧 (方案 B)」实施计划入库轮收尾基线。本轮**零代码改动** —— 新增计划 HTML + 报告 §11 后记 + 认领链三向闭环 (计划 ↔ 报告 ↔ 档案), 全量套件与文档守卫复跑全绿。数字与上一条同 (未动 `src/`/`tests/`)。
> 档案: memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md
> 基线时间: 2026-10-08 12:53

**Refs:** memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2813 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial; 门槛 98% 达标)
- **耗时**: 42.85s(墙时 45.2s)
- **本轮闸门插曲**: 首跑 1 条失败 —— `test_memory_bank.py::test_wording_guard_is_green_on_current_kb` 命中新切片正文「等…指令」时点相对措辞; 改时不变措辞后复跑全绿 (四处闸无误报)。

## 说明

- **相对上基线的参考**: 与 [26-10-08-1235](26-10-08-1235-hr-exclude-steady.md) 同数字 (本轮无代码/测试改动); 要看差值跑 `commands run kb.baseline -n 2`。
- **代码事实变更**: 无 (本轮未改 `src/` 一行)。
