# 3996 passed + 2 skipped —— HR 行键面收单点(测试侧常量)后全量基线

> 摘要: HR 行键面收单点(测试侧常量)后全量基线
> 基线时间: 2026-10-22 03:35

**Refs:** memory-bank/tasks/26-10-22-test-hr-row-key-surface-dup.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3996 passed, 2 skipped in 144.89s**
- 覆盖率: TOTAL **99%**(20981 stmts / 7088 branch, 99.28%)

逐条口径注记:

- 本轮只改测试侧(三常量 + 四处断言), `src/` 零改动 ⇒ 语句/分支分母与上一条基线同量级
- 守阵红验(探针): 临时给 `EntryDetail` 加 `probe_extra` 字段 → 两处闭集断言**同时变红**(2 failed), 还原后归绿 —— 证明收单点没有削弱守阵
- 基线测在「已含本次代码改动、尚未提交」的工作树上
- 耗时 144.89s 是**单次采样**(同时段另有 clone 在跑全量), 报耗时带区间见 `testing/baseline.md` 口径段

## 本改动面

- `tests/webui_helpers.py` —— HR 段新增三常量 `HISTORY_ROW_KEYS`(22 键) / `ENTRY_ROW_KEYS`(模型面 20 键) / `ENTRY_ROW_KEYS_API`(= 模型面 | `local_present`), 附「为何刻意不从 dataclass 派生」注释
- `tests/test_hr_status.py` —— `test_entry_details_field_surface` 与 `test_history_rows_field_surface` 改引常量, 删两处全量字面量
- `tests/test_web_hr.py` —— `test_api_hr_site_entries_full_fields` / `test_api_hr_history_rows_from_real_wave` 改引常量, import 补两名字
- 生产代码零改动; lane 子键面与 `SiteStatus` 键面属同类但不在本条 issue 范围, 未动
