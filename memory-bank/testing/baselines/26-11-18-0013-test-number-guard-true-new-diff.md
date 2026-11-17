# 6415 —— check_wording 族 B 超线报真新增(HEAD 清单现算 diff)收口全量基线

> 摘要: check_wording 族 B 超线报真新增(HEAD 清单现算 diff)收口: test.full 全绿
> 基线时间: 2026-11-18 00:13

## 验收数字

`commands run test.full` 实测(2026-11-18 00:10, Windows 开发机, 基线 commit a124636b + 本批未提交增量):

```text
TOTAL                                                28858     43  10302     59    99%
6415 passed, 6 skipped in 185.22s (0:03:05)
```

- 汇总: 6415 passed / 6 skipped / 0 failed, 覆盖率 99%(TOTAL 行) —— 覆盖闸行未截存, test.full 退出码 0 = 闸通过。
- 受影响电池: `commands run test.one -- tests/test_memory_bank_docs.py -k number_guard` 7 passed(本批新增 4 用例全绿)。

## 本改动面

issue 26-11-17-0852 认领修复(check_wording 族 B 超线报「扫描序末 N 条」误导排查 → 报真新增), 逐文件:

- `.agents/skills/memory-bank/scripts/check_wording.py`: 族 B 超线改对 HEAD 同面清单现算 diff 报真新增行 —— 新增 `_scan_number_hits` / `_format_number_hit`(展示格式单点, `list_test_numbers` 收敛于此)/ `_head_hit_counter`(每扫描面一次 `git archive HEAD` 内存 tar 展开; 无 `.git` 先做无子进程短路; 只归档两个扫描面防 baselines 同文行污染)/ `_diff_new_number_hits`((路径, 分类, 行文) 多重集配对, 行号漂移不参与) 四 helper; `collect_violations` 超线块三分支: git 不可用退回末 N 条启发式(文案明写「样本非新增定位」)/ 有基线报真新增 / 溢出但 diff 无新增(指路 `--count-numbers` 下调冻结常数); 模块 docstring 增「报错定位」节。
- `tests/test_memory_bank_docs.py`(+4 用例, 头部测试计划清单同步): 真新增定位不取末 N 条 / 同文行多重集配对 / 无 git 无子进程短路 / `collect_violations` 接线必报真新增(monkeypatch 基线, 评审 minor 补)。
- `memory-bank/pitfalls/kb/wrap-did-test-numbers.md`: 「判红位置可能指向存量件」节根因句按扫描序实况改正(`SCAN_DIRS` tasks 段在前; 原句误记 activeContext 先于 tasks), 判别法标降级备用; 摘要行同步。
- `memory-bank/issues/26-11-17-0852-bug-kb-check-wording-tail-mislead.html`: 复验行 / 修复后补充(实际修法·验证数字) / 状态 Open → Done。

评审: code-review 全能档, 首轮 + 修复轮共 2 轮, 派发 2, 检 P1/T2(1 条 minor 当场修, 1 条 REFUTE 弃), 修复轮零发现收口。
