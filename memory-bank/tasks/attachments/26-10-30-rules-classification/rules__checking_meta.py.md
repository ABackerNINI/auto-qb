# 分类: src/auto_qb/rules/checking_meta.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__checking_meta.py.txt`
- 机器实测: 11 条全部真存活(16 文件池全绿)
- 计数: 11 条 = 真洞 2 / 等价 9 / 假存活 0
- 口径说明: 分片实际 18 条 = `survived` 11 + `timeout` 7(机器未定性, 不在本表); 本表按 survived 11 条逐条分类

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `x_recheck_fail_count__mutmut_15` | recheck_fail_count | `rec.get("count", 0)`→默认 `None` | 等价 | count 只由 bump_recheck_fail 写入(它必写 "count"), rec 缺 count 键的形状本模块造不出 ⇒ 默认值无读点; 且 `date == today` 已由本函数前置过滤 |
| 2 | `x_recheck_fail_count__mutmut_17` | recheck_fail_count | `rec.get("count", )`(隐式 None) | 等价 | 同 mutmut_15, 默认值不可达 |
| 3 | `x_recheck_fail_count__mutmut_20` | recheck_fail_count | `rec.get("count", 1)` | 等价 | 同 mutmut_15; 即便缺键也只在 0/1 之间, 未越过 RECHECK_FAIL_LIMIT=3 的闸门 |
| 4 | `x_bump_recheck_fail__mutmut_13` | bump_recheck_fail | 新记录 `{"XXdateXX": "", "count": 0}` | 等价 | 键名错位只影响"首次建记录"的字典形状: `rec.get("date")` 取 None ≠ today ⇒ 仍走重置分支并补写 date=today, 返回值与后续行为一致 |
| 5 | `x_bump_recheck_fail__mutmut_14` | bump_recheck_fail | 新记录 `{"DATE": "", ...}` | 等价 | 同 mutmut_13 |
| 6 | `x_bump_recheck_fail__mutmut_15` | bump_recheck_fail | 新记录 `{"date": "XXXX", ...}` | 等价 | `"XXXX"` ≠ 今日 ISO 串 ⇒ 与初值 `""` 同走重置分支, 结果相同 |
| 7 | `x_bump_recheck_fail__mutmut_16` | bump_recheck_fail | 新记录 `{"date": "", "XXcountXX": 0}` | 等价 | 首次建记录必走重置分支, `rec["count"] = 0` 会被补写 ⇒ 缺 count 的窗口不可观测 |
| 8 | `x_bump_recheck_fail__mutmut_17` | bump_recheck_fail | 新记录 `{"date": "", "COUNT": 0}` | 等价 | 同 mutmut_16 |
| 9 | `x_bump_recheck_fail__mutmut_18` | bump_recheck_fail | 新记录 `{"date": "", "count": 1}` | 等价 | date="" ≠ today ⇒ 立刻被重置分支改写为 0 再 +1, 初值 1 被覆盖 |
| 10 | `x_bump_recheck_fail__mutmut_28` | bump_recheck_fail | 重置分支 `rec["XXcountXX"] = 0` | 真洞 | 跨自然日只重置 date 不重置 count ⇒ 昨日已 3 次的种子今天首次 bump 得 4, ops_mod:233 `>= RECHECK_FAIL_LIMIT` 立即闸死, 该种子当日再也无法 recheck(自然日重置语义失效, 损坏文件修复后仍卡死); 池内无跨日用例(都是新 state 首跑)。**建议守阵**: 预置 `{"date": "昨日", "count": 3}` 后 bump, 断言返回 1 |
| 11 | `x_bump_recheck_fail__mutmut_29` | bump_recheck_fail | 重置分支 `rec["COUNT"] = 0` | 真洞 | 同 mutmut_28: 跨日计数不清零, 次日首次即命中 3 次上限。**建议守阵**: 同上的跨日 count=3 用例 |
