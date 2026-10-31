# 4073 passed + 2 skipped(根) —— env._hr 未配hr 判定收敛到 record._hr_guard(建议A)后全量基线

> 摘要: env._hr 未配hr 判定收敛到 record._hr_guard(建议A)后全量基线
> 基线时间: 2026-10-30 01:39
**Refs:** memory-bank/issues/26-10-29-1259-refactor-b-r17b01-hr-absent-default.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`(pytest.ini addopts, TMPDIR 由 task 内置); 2026-10-30 实测, 全量 158.96s, 建档 01:39):

```
  TOTAL                                                21070     99   7136    103    99%
  4073 passed, 2 skipped in 158.96s (0:02:38)
```

- 汇总行: **4073 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本轮零新增用例: 等价性由既有守阵背书 —— 修前定向守阵(`tests/test_expr_eval.py tests/test_conditions.py tests/test_hr.py`, test.one)78 passed; `-k "derived_values or legacy_condition_equivalence or hr"` 18 passed。全量与定向均修后跑, 无修前红验(等价重构, issue 04 节明示无需新写行为断言)。
  - 「2 skipped(根)」为既有环境条件 skip, 与本轮无关(`26-10-29-1835-parse-unit-ladder` 等切片同为 2; `26-10-30-0025-hr-thead` 切片记 10, 环境差异见各片)。
  - 既有静态守阵 `test_hr_entry_guard_single_point`(record.py 里 `not self.tracker_conf.hr` 只许出现一次)照常通过 —— 本轮把表达式侧的重复判定删掉, 正是该守阵精神的反向延伸(env 侧不再有第二份)。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/rules/expr/env.py` | `_hr` 删 `or not tor.tracker_conf.hr` 半句, 只留「无 tracker_conf 兜底 + 委托记录方法」(建议 A, 行为逐字等价); docstring 补「未配 hr 口径单点在 record._hr_guard」与 ② 分歧互指(表达式侧 hr_satisfied=false 是达标语义, 勿单边改齐) |
| `src/auto_qb/rules/conditions.py` | `HrCondition.match` 的 `conf.hr is None` 分支补 ② 分歧互指注释(本处 true 是义务语义「没有要求=视为已满足」), 零行为变化 |
| `src/auto_qb/torrents/record.py` | `_hr_guard` docstring 补一句「表达式取值面 _hr 亦委托到本口径」; 判定语句本身零改动 |
| `memory-bank/issues/26-10-29-1259-refactor-b-r17b01-hr-absent-default.html` | 状态 Open → In Progress → Done(复验/实际修法/验证方式回填); doc-refs 反向声明本切片 |

**未改**: 建议B(把 `tracker_conf is None` 并进 `_hr_guard`、`_hr` 纯委托)未采纳 —— webui/views 对 record 方法调用前已自防 conf=None 且明文「不做 None 防御(早暴露配置匹配错误)」, B 会给 record 方法新增 conf=None 容忍, 与该口径相悖; 条件侧 HrCondition 语义一字未动(issue ② 判定: 业务正解不该合)。
