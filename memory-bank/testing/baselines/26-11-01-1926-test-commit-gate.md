# 4453 passed + 10 skipped —— test.full 基线快照: 四包闸门自测落地

> 摘要: test.full 基线快照: 四包闸门自测落地
> 基线时间: 2026-11-01 19:26
**Refs:** memory-bank/tasks/26-11-01-test-commit-gate.md

## 验收数字

- `commands run test.full` 实测(2026-11-01 19:26, Windows 本机):
  - 汇总行: `4453 passed, 10 skipped in 175.49s (0:02:55)`
  - TOTAL 表: `TOTAL  22482  197  7708  156  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- 口径注记: pytest.ini addopts `-n 8 --cov=src`; 测量树 = 本 clone 工作树, 含下方「本改动面」全部文件(未提交状态, 解释与历史基线数字差异用)

## 本改动面

- 新增 `.commands/{dev,doc,env,kb}/scripts/test_<包>_pkg.py` 四包最小自测(各 3 例: config 可解析+[pack].name+必备键(run/timeout/when) / run 命令 .py 引用存在+抽取非空; env 第三例改守 env.version 版本单源)
- 修改 `.commands/dev/config.toml`: `dev.port-kill` 补 `timeout = 60`(新守阵逮到的真缺口)
- 不动 src/ 与 tests/: test.pkg 口径(.commands + 引擎)用例 +12, tests/ 用例面不变
