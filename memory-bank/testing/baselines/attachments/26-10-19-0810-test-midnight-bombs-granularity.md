# 3679 passed + 10 skipped(根) —— 时段判定改分钟粒度(time_in_range 单点)后全量基线

> 摘要: 时段判定改分钟粒度(time_in_range 单点)后全量基线
> 基线时间: 2026-10-19 08:10

## 验收数字

```text
TOTAL                                                19219    311   6534    219    98%
3679 passed, 10 skipped in 34.56s
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛 98%); 相对上基线的逐位对比不写 —— 看差值 `commands run kb.baseline -n 2`。
- 与同专题上一条切片(26-10-19 07:39, 仅测试侧)的差: 本轮多一条 `utils.time_in_range` 分钟粒度守阵 + 等价性用例参数化(正午 / 23:59:30 两时刻), 故通过数 +2。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/infra/utils.py::time_in_range`: 比较前先 `replace(second=0, microsecond=0)` —— 端点所在整分钟含在内。三个消费方(`date_time` 条件 / 通知 `quiet_hours` / HR 限速 `allow_window`)一起收口。
- `tests/test_utils.py`: 新增 `test_time_in_range_minute_granularity`(全时段 / 跨午夜两端点 / 非跨午夜两端点的分钟内与分钟外)。
- `tests/test_expr_eval.py`: `_freeze_clock(monkeypatch, when)` 参数化冻结时刻; `test_legacy_condition_equivalence` 加 `edge-minute`(23:59:30)守阵位。
- `docs/configuration.md`: `date_time` 条件行补「`time` 按分钟粒度判定, 端点整分钟含在内, `00:00-23:59` 即全天」。
- 测试侧同轮已有(见同专题上一条切片): traffic 正午锚点 `_anchored_ts()` + expr 冻钟。
- issue `26-10-19-0013` 置 Done。
