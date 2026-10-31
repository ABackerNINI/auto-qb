# 4051 passed + 10 skipped(根) —— parse_speed 单位白名单兜底(方案 B 三解析器收敛)后全量基线

> 摘要: parse_speed 单位白名单兜底(方案 B 三解析器收敛)后全量基线
> 基线时间: 2026-10-29 18:35
**Refs:** memory-bank/issues/26-10-29-1252-bug-b-r18b01-parse-unit-ladder.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`; 2026-10-29 实测, 全量 155.71s, 建档 18:35):

```
  TOTAL                                                20804    117   7126    108    99%
  4051 passed, 10 skipped in 155.71s (0:02:35)
```

- 汇总行: **4051 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本轮新增 24 个用例项: test_utils 表驱动三件(合法/空串 8 + 非法矩阵 12 + 白名单文案 3)+ test_speed_curve 配置层守阵 1 条。
  - 「10 skipped(根)」为既有环境条件 skip, 与本轮无关。
  - 红验(修复前): `test.one -- tests/test_utils.py -k parse_quantity` **4 failed / 19 passed**(红恰为 speed 白名单 4 例: 旧实现 KeyError 对不上 `pytest.raises(ValueError)`); 配置层守阵 **1 failed**(KeyError 裸穿 load_config, 与 issue 证据 ② 同形态)。修复后两文件 176 passed 全绿。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/infra/utils.py` | 方案 B(issue 26-10-29-1252): 抽 `_parse_quantity` 骨架(正则 → 单位白名单兜底 → 乘数), parse_time/parse_fsize/parse_speed 各留薄包装并各自保留单位表/正则/报错文案/返回类型/空串语义; 白名单兜底进必经路径, `1iB/s`、`10KB/s` 等命中正则但不在表里的单位一律 ValueError(旧 KeyError), fsize 两条旧文案逐字保留 |
| `tests/test_utils.py` | 表驱动三件 `test_parse_quantity_ladder_valid_and_empty`(8) / `test_parse_quantity_ladder_invalid_valueerror`(12, 断言异常类恰为 ValueError) / `test_parse_quantity_ladder_unit_whitelist_message`(3) + 头部「## 测试计划」补 3 行 |
| `tests/test_speed_curve.py` | 新增 `test_speed_unit_prefixless_ib_aggregates_config_error`(load_config 聚合 ConfigError 且消息含键名, 钉「统一 ConfigError」契约) + 头部「## 测试计划」补 1 行 |
| `memory-bank/issues/26-10-29-1252-bug-b-r18b01-parse-unit-ladder.html` | 认领链 + 状态流转 Open → In Progress → Done(复验/实际修法/验证方式回填) |

**未改**: 校验层 `_try`(只接 ValueError 是设计选择, issue §05 已排除)、config-reference 主题文档(修后表述仍准确: 速度单位有效集 B/s ~ GiB/s 不变, 变的只是非法单位的异常类)。
