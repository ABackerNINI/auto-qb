# 4067 passed + 10 skipped(根) —— v4 解析纪律骨架收敛单点后全量基线

> 摘要: 4067 passed + 10 skipped(根) —— v4 解析纪律骨架收敛单点后全量基线
> 基线时间: 2026-10-30 02:09
**Refs:** memory-bank/issues/26-10-29-1304-refactor-b-r07t06-v4-parse-skeleton.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`(pytest.ini addopts, TMPDIR 由 task 内置); 2026-10-30 实测, 全量 117.70s(pytest 自报; 命令墙钟 119.4s), 建档 02:09):

```
  TOTAL                                                20802    117   7128    108    99%
  4067 passed, 10 skipped in 117.70s (0:01:57)
```

- 汇总行: **4067 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 「10 skipped(根)」为既有环境条件 skip, 与本轮无关(上一切片 26-10-30-0025 同为 10 skipped)。
  - 本轮用例净 +2(`tests/test_traffic_store.py` 测试函数 56 -> 58: 两条新守阵); passed 对照上一可用基线 26-10-30-0025(4064)的 +3 中余 1 条差额产生于两轮之间, 不在本轮改动面(本轮 diff 仅 src/tests 各 1 文件, 两笔远端 docs 提交不含测试)。
  - 红验两向(精确 edit 突变 -> 精确反向还原, 未用 git checkout —— 工作区含未提交实现): ① `parse_v4_agg_text` 内注入永不调用的骨架逐字副本 -> 静态守阵 `test_v4_parse_skeleton_single_point` 红(骨架行计数 2==1), 行为守阵同轮绿; ② 驱动器删撕裂尾豁免两行 -> 行为守阵 `test_v4_parse_discipline_dual_parser_same_verdict` 红(撕裂尾夹具 `torn_tail False != True`), 静态守阵同轮绿; 还原后文件字节数与改前一致, 选段 4 条复跑全绿。
  - 定向跑: `test.one tests/test_traffic_store.py` 58 passed / `test.one tests/test_traffic_sample.py` 113 passed(agg 侧撕裂行纪律既有用例含内)。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/core/traffic_store.py` | 抽公共行循环驱动器 `_parse_v4_text(text, on_line) -> (key, bad, data, torn_tail)` 单点(splitlines / torn 判定 / 头行门闩整文件坏含头行本身 / key 首个消费 / 空行注释跳 / data 逐行分母 / `except (ValueError, IndexError)` 统一转 `bad += 1` / 撕裂尾末行豁免); `parse_v4_agg_text` 只留 9+8 列行型回调 `on_agg_line`, `parse_v4_day_text` 只留 B/r/z/n 块状态机回调 `on_day_line`(块头前数据行/无基线块 r/z 两守卫以 ValueError 走同一吞异常路径); 两处互指注释退役改单点声明(issue 26-10-29-1304 R07-T06) |
| `tests/test_traffic_store.py` | 新守阵 2 条: `test_v4_parse_discipline_dual_parser_same_verdict`(同夹具双 parser 纪律面逐项同判: 空文本/头行缺失与旧头行/坏行族+空行注释跳/撕裂尾/完整末行无换行 五组, 行型中立夹具) + `test_v4_parse_skeleton_single_point`(静态: 骨架行/行循环/`def _parse_v4_text` 各恰 1 + 两解析器接线行闭集; 口径只扫 traffic_store.py —— `traffic_limits.parse_limits_day_text` 同形行属另一族不在本条范围); 头部「## 测试计划」同步 + `import inspect/re` |
| `memory-bank/issues/26-10-29-1304-refactor-b-r07t06-v4-parse-skeleton.html` | 状态 Open -> In Progress -> Done(复验/实际修法/验证方式回填); doc-refs 反向声明本切片(D4 补链) |

**未改**: `traffic_limits.parse_limits_day_text`(另一族解析器, 无头行门闩/撕裂尾直接丢弃, R07 相邻项已判不在范围); 行型语义/写侧序列化 `format_*` 全族零触碰(行为等价由既有 roundtrip/坏行族/撕裂尾守阵钉住); 读侧缓存与告警(`_warn_bad_lines`)零改动。
