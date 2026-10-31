# 3552 passed + 4 skipped(根) —— 修掉 test_memory_bank 的跨零点时间炸弹(断言与实现同源取时)

> 摘要: `test_memory_bank` 两例把运行当天写死进断言(换日必红) → 改为与 `timekit.now()` 同源取时；全域回归转全绿
> 基线时间: 2026-10-18 06:26
**Refs:** memory-bank/issues/26-10-18-0608-test-memory-bank-test-hardcoded-today.html

## 验收数字

`commands run test.full` 实测(2026-10-18 06:26, 本机 Windows 单侧):

- 汇总行: **3552 passed, 4 skipped**(36.94s) —— 无 failed
- TOTAL 覆盖率: 18030 statements / 264 missed / 6120 branches / 191 partial / **98%**(98.10%, 闸门要求 98%, 达标)

## 本改动面

- `tests/test_memory_bank.py`(仅测试, 零实现改动): 新增 `_kb_clock()`(延迟 import `timekit`, 与同文件 `_flip_status()`/`_bump_doc()` 同一条 `sys.path` 注入路子); `test_flip_status_flips_bumps_and_fails_fast` 与 `test_bump_doc_appends_changelog_and_fails_fast` 里的三处硬编码日期断言(`**Updated:**` ×2、`最后活动` ×1)改成对 `_kb_clock().strftime(...)` 的 f-string 比对。
- 夹具里的 `**Added:** 2026-10-17` / `最后活动: 2026-10-17 09:00` 是**受测输入**(验证「抬戳」这个动作), 保持字面量不动。

## 守阵与坑

- **时间类断言只准同源取时**: 期望值必须来自实现用的那同一个时间单点(`timekit.now()`), 否则用例的生命周期就等于写它的那一天。前一基线切片 `26-10-18-0615` 记的两例红即此坑。
- 不放宽成「含 `**Updated:**` 即可」—— 那会把「确实抬到今天」这条唯一守阵能力丢掉; 也不给 `timekit` 加可注入 clock(能测得更彻底, 但要动实现单点, 收益不抵)。
