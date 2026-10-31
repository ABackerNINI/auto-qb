# 3677 passed + 10 skipped(根) —— 跨零点时间炸弹清偿(expr 冻钟 + traffic 正午锚点)后全量基线

> 摘要: 跨零点时间炸弹清偿(expr 冻钟 + traffic 正午锚点)后全量基线
> 基线时间: 2026-10-19 07:39

## 验收数字

```text
TOTAL                                                19218    311   6534    219    98%
3677 passed, 10 skipped in 41.02s
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛 98%); 相对上基线的逐位对比不写 —— 看差值 `commands run kb.baseline -n 2`。
- 本轮只改测试(2 个文件), **未新增用例**: 通过数与上一条基线的差来自基线之后同步进来的提交, 与本次清偿无关。
- 跨零点免疫性另做定向取证(不进本表): 同一批 traffic 用例在「假墙钟 23:59:50」下 13 passed / 0 failed, 而改前 HEAD 版同工况 3 failed(正是 issue 报告里那三条); expr 侧冻钟后不再采样墙钟。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `tests/test_traffic_limits.py`: 新增 `_anchored_ts()`(本地当日正午锚点), 替换 9 处裸 `int(time.time())`; 端点 24h 窗口用例保留真钟并注明例外。
- `tests/test_expr_eval.py`: 新增 `_FrozenDatetime` + `_freeze_clock()`, 冻住 `rules.conditions` / `rules.expr.env` 的 `datetime`; 覆盖 `test_legacy_condition_equivalence` 与 `test_sys_time_and_counts`。
- 生产代码零改动(expr 侧「旧条件秒精度 vs 表达式分钟精度」的 59s/天 分叉仅记录, 未动 `utils.time_in_range`)。
- issue `26-10-19-0013` 置 Done。

> 后续(当日 08:10): 用户拍板「直接改」, 生产侧 `utils.time_in_range` 已改分钟粒度 —— 本切片只代表 07:39 那一刻(纯测试侧), 最新事实源见 [26-10-19-0810-test-midnight-bombs-granularity](26-10-19-0810-test-midnight-bombs-granularity.md)。
