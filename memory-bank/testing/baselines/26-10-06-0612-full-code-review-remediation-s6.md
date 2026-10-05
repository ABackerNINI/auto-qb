# 2676 —— Code Review 修复实施计划 S6 批 (P3 小修收尾 ×3)

> 摘要: 计划 [26-10-06-0103-plan-full-code-review-remediation.html](../../plans/26-10-06-0103-plan-full-code-review-remediation.html)
> §05 S6 批 (P3 小修收尾 ×3: bug ×2 + perf ×1 —— B2-04 parse_size 表外单位 / G-03 freespace OSError 拍板 P-07 改抛 ExprError / G-06 sys.torrent_count 全库拷贝)
> 实施完成后的全量测试基线。
> 基线时间: 2026-10-06 06:12

**Refs:** memory-bank/plans/26-10-06-0103-plan-full-code-review-remediation.html

- 分支: develop @ 2119931d(批实施起点, `my-commit-flow.sync` 所得; 本切片实测于修复后工作树)
- 命令: `commands run test.full`(Windows, 双次采样 40.0s / 41.6s —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 40.0~41.6s, 覆盖率 TOTAL 99%**
  (15823 语句 / 163 未覆盖 / 5472 分支 / 143 partial)
- 相对对照点 S5 后基线(批起点 2119931d 会话口径: 2674 passed + 4 skipped, 15820/163/5470/143, 99%):
  passed +2 恰为本批新增守阵 2 条(test_parse_size_unknown_unit_returns_none / test_torrent_count_no_full_copy;
  test_freespace_os_error 系改写非新增), skipped 持平; 未覆盖 163 / partial 143 **逐字持平**;
  语句 +3 / 分支 +2 均为本批新增且全覆盖的修复与守阵代码。
- 本批新增/改写守阵 3 条已登记 [../guards.md](../guards.md)「S6 P3 小修批次守阵」节, 均已做红验。
