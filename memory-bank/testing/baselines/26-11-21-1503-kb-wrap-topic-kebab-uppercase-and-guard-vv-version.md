# 6757 —— 6757 passed, 6 skipped —— issue 0639 双 cosmetic 修复批全量基线: guard 双 v 去除 + 切片命名小写定案

> 摘要: 6757 passed, 6 skipped —— issue 0639 双 cosmetic 修复批全量基线: guard 双 v 去除 + 切片命名小写定案
> 基线时间: 2026-11-21 15:03

## 验收数字

`commands run test.full` 实测(2026-11-21 15:00, Windows, HEAD 914bd462, 收尾回写随工作树在场):

```text
TOTAL                                                30547     82  10880     81    99%
6757 passed, 6 skipped, 8 warnings in 145.49s (0:02:25)
```

- 汇总: 6757 passed / 6 skipped / 0 failed; 覆盖率闸门达标(99% ≥ Windows 阈, 见 testing/baseline.md), 耗时单次采样 145.49s(并行 -n 8)。
- 缺口净额: 本片 163 单位(miss 82 + partial 81) 与上片 26-11-21-1013 的 151 单位(miss 74 + partial 77) 相比 **+12**; 分母由语句 30044 / 分支 10662 变为 30547 / 10880(+503/+218)。增长主体非本批 —— 两片之间落库了守阵批 1b18a05b 与「外部旧路径种子处置」T1-S6 六笔(3b340d44..914bd462); 本批仅 6 行(生产代码零新增, 1 行测试断言 + 1 行注释 + 文档/记账面), 不引入新缺口面。

## 本改动面

本轮(修 issue 26-11-21-0639 双 cosmetic 合并件)改动面, 逐文件:

- `tests-real/runner.py`: cmd_guard 输出 `v{version}` 改裸 `{version}` 原样打印(qb.version() 原样返回 /app/version 自带 v 前缀, 「vv5.2.3」双 v 根除), 行上加注释留痕防拼回。
- `tests/test_real_machine_safety.py`: `test_cmd_guard_reports_real_and_fake_counts` 增断言 `"v5.0.0" in out and "vv" not in out`(双向钉: 拼回 v 前缀→vv 命中红; 剥掉 API 自带前缀→v5.0.0 缺失红)。
- `memory-bank/testing/real-machine.md`: §06 定期排期触发第 6 步记录行补「片名一律小写 kebab(real-rm04-slice-a 式, 禁 sliceA 大写段: kb.wrap --topic 过 kebab 校验必拒; 26-11-21 改定, 存量大写文件名不改)」—— 命名冲突按 issue 定案落在惯例一侧, wrap 校验不动。
- 记账面: issue 0639 翻 Done + 正文补实际修法/验证方式; 本基线切片; active-context 切片 26-11-21-1503。
- 真机轨: 纯桩可验(输出格式化面, 守阵桩已钉), 免真机轨; 下轮 real.guard 真跑显示串自然复核。
