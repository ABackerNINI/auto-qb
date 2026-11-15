# 6179 —— test.linux-clean 落地批全量基线

> 摘要: test.linux-clean 落地批全量基线
> 基线时间: 2026-11-15 07:59

## 验收数字

`commands run test.full` 实测(2026-11-15 07:59, Windows 开发机):

```text
TOTAL                                                27436     72   9646     77    99%
6179 passed, 2 skipped in 165.34s (0:02:45)
```

- 汇总: 6179 passed / 2 skipped, 覆盖率 99%(Windows 闸 99.5 差异面见 conftest COVERAGE_FLOOR 单点; 实测表尾 99% 由 pytest-cov 出)。
- 与上一切片的差值口径见 `memory-bank/testing/baseline.md`, 本切片不重复。

## 本改动面

- 新增 `.commands/test/scripts/linux_clean.py`(test.linux-clean 三层清扫自动化主体, 演练/--yes 两态 + 白名单点名式 + PT ban 终闸 + 面杀命令/容器删除 absence 纪律)。
- 新增 `.commands/test/scripts/test_linux_clean.py`(守阵 18 条: 纯函数/脚本文本/CLI 两态/absence/config 钉面)。
- `.commands/test/config.toml`: 新增 `test.linux-clean` task 条目。
- 文档面: 计划 26-11-12-0152(§03 行落地注记 + §10 R9)、issue 26-11-13-0212 翻 Done + 修复后补充段、坑档 `pitfalls/testing/docker-id-truncation.md`、任务档案 `tasks/26-11-15-test-linux-clean.md`、AGENTS.md linux 测试注记一行(余量 350/8000)。
- 产品代码(`src/`)与 `tests/` **零改动** —— 基线数字相对前切片预期不变; 本切片作为本批收尾锚。
