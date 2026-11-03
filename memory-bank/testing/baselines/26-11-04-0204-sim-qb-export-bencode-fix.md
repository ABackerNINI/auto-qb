# 5033 —— sim_qb export bencode 长度前缀修复(issue 26-11-03-1145)全量基线

> 摘要: sim_qb export bencode 长度前缀修复(issue 26-11-03-1145)全量基线
> 基线时间: 2026-11-04 02:04
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-04, `uv run pytest` 全量含覆盖率):

- 汇总行: `5033 passed, 10 skipped in 130.55s (0:02:10)`
- 覆盖率 TOTAL 表: `TOTAL 23325 185 7956 158 99%`(语句 23325 · 未覆盖 185 · 分支 7956 · 分支未覆盖 158 · 总覆盖 99%)
- 口径注记: 修复前同套件已全绿(5033 passed)—— 新守阵 `test_minimal_bencode_roundtrip_parse` 是**净增 1 条**(旧 5032 passed 一轮里已含它红过一次的中间态, 最终全量两轮均 5033); skipped 10 条为存量平台条件跳过, 与本轮无关。

## 本改动面

- `scripts/sim_qb_core.py` · `minimal_bencode`: announce 与 name 的 bencode 长度前缀改为按字节数动态拼(announce 曾写死 26 实 25; `len(name)` 是字符数, 非 ASCII 名漂移), issue 26-11-03-1145。
- `tests/test_sim_corpus.py` · 新增 `test_minimal_bencode_roundtrip_parse`: 极简 bencode 解析器回读导出物, 断言 announce/info/length/piece length + 尾部无残留; ASCII/非 ASCII 名 × 0/大 size 三档; 同步文件头部「测试计划」清单。
- `memory-bank/issues/26-11-03-1145-bug-sim-qb-export-bencode.html`: Open → Done, 补复验/修法/验证记录。
