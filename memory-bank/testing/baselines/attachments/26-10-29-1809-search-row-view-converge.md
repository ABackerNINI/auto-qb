# 4036 passed, 2 skipped —— 搜索结果行收敛 _member_view 后全量基线(issue b-r16b01-search-row-view-converge)

> 摘要: 搜索结果行收敛 _member_view 后全量基线(issue b-r16b01-search-row-view-converge)
> 基线时间: 2026-10-29 18:09
**Refs:** memory-bank/issues/26-10-29-1320-bug-b-r16b01-search-row-view-converge.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`, 2026-10-29 18:09 建档时实测, 本轮第二次全量 —— 首轮口径注记见下):

```
  TOTAL                                                21067     99   7132    103    99%
  Required test coverage of 99% reached. Total coverage: 99.27%
  4036 passed, 2 skipped in 149.09s (0:02:29)
```

- 汇总行: **4036 passed + 2 skipped(根)**; 覆盖率 99.27%(门槛 99)。
- 逐条口径注记:
  - 用例数相对上一基线(4007+2, 2026-10-29 04:12)的增长来自远端 37 笔提交合入的新用例 + 本轮新增
    守阵 `test_search_row_view_converged_on_member_view`(test_web_hr.py)各占一部分, 逐位差值看
    `commands run kb.baseline -n 2`。
  - 「2 skipped(根)」是既有的根级用例, 与本轮无关。
  - 本轮首次全量曾红在 `test_gen_all_check_is_green`(issues 索引未重建) —— 属收尾步骤未做而非代码
    缺陷, `commands run kb.index` 后复跑转绿; 为取干净数字重跑了本轮全量(上段即重跑实测)。
- 精准面: `commands run test.one -- tests/test_web_hr.py tests/test_web_seed_center.py -k "search or
  restatement or view_fields"` 21 passed; 红验(临时在 `_view` 重列 `"hash"` 键)守阵判红后还原。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/webui/views.py` | `search_torrents` 内嵌 `_view` 收敛为 `{**self._member_view(rec), "by": by}`(issue b-r16b01-search-row-view-converge: 消除与 `_member_view` 的同族重述 —— seeding_time 补分钟量化, 补齐 eta/num_*/downloaded 等 19 键, 搜索虚拟行展开明细列不再空白); docstring 的手抄字段清单改为指向 `_member_view` |
| `tests/test_web_hr.py` | 新增守阵 `test_search_row_view_converged_on_member_view`(ast 静态: `_view` 返回字典只有 `**` 展开 + by; 动态: 键集 = 成员行键集 + {by}, 同名字段等值, 量化与明细列有值) + 头部「## 测试计划」补一行 |
| `memory-bank/issues/26-10-29-1320-...html` | 状态 Open → In Progress → Done, 复验/实际修法/验证留痕; `doc-refs` 反向声明基线切片 |
