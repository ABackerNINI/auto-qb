# 4830 passed + 10 skipped(根) —— TMPDIR 自举+互斥锁+coverage 落实例根后全量

> 摘要: TMPDIR 自举+互斥锁+coverage 落实例根后全量
> 基线时间: 2026-11-02 08:38
**Refs:**

## 验收数字

- **目标**: 全量 pytest(`tests/` 全量 + `src/` 覆盖率报表), 测于 TMPDIR 自举/互斥锁/coverage 落实例根五步全部落盘后的工作树(HEAD `9b77ad98` + 本轮未提交改动)
- `commands run test.full` 实测(wrapper 墙 225.2s, 2026-11-02 08:38, Windows 本机):
  - 汇总行: `4830 passed, 10 skipped, 4 warnings in 222.31s (0:03:42)`
  - TOTAL 表: `TOTAL  22521  152  7726  135  99.00%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: 通过(要求 99.0%, 实测 99.00%)
- **首跑一红及处置**: 全量首跑 `1 failed, 4829 passed, 10 skipped in 216.15s`, 红在
  `test_test_plan_docstring_guard.py::test_repo_plan_matches_defs` —— 本轮新建的
  `tests/test_tmp_bootstrap.py` 缺模块 docstring 的「## 测试计划」清单(AGENTS.md 硬规定);
  补 7 条用例清单后复跑全绿(上方数字), 非环境性、非行为回归。
- **环境 / 工具**: Windows 本机(win32)· Python 3.13 · pytest-xdist 8 workers ·
  `TMPDIR` 由 `tests/_tmp_bootstrap.py` 自举(R→H→%TEMP%), 不再由 config 写死盘符

## 本改动面

- `tests/_tmp_bootstrap.py`(新): 实例根探测自举(R→H→%TEMP% 单一配置点 `TMP_ROOT_CANDIDATES`)、外部 TMPDIR 拒收 rc=4、幂等口、12h+pid 死双条件清扫、写重型互斥锁(mkdir 原子抢占/rc=3/僵尸自愈/sessionfinish+atexit 双释放)、`retarget_cov_data_file`(coverage 落实例根)。
- `tests/test_tmp_bootstrap.py`(新): 7 条守阵(候选单点/顺序/标记判定/rc=4 拒收/幂等/僵尸判定/coverage 重定向)。
- `tests/conftest.py`: 模块级 `bootstrap()` + pytest_configure 调 `retarget_cov_data_file` + sessionfinish 锁释放。
- `.commands/test/config.toml`: 四处 `set "TMPDIR=R:/..."` 前缀摘除; `test.full` timeout 900→1800。
- `.commands/test/scripts/pkg_scoped.py` + `test_pkg_scoped.py`: 去掉写死 R:\ 常量与注入, 随系统 temp。
- `.commands/mutants/scripts/mutants.py`: DEFAULT_OUT 改 `tempfile.gettempdir()/auto-qb-mutants`, 子进程写死盘符摘除。
- `tests-real/conftest.py`: 注释同步新口径; `tests/test_relocate_exec.py`: 预算 5s→15s + 高机载口径 docstring。
- `AGENTS.md`: TMPDIR 过时措辞回写为自举/拒收 rc=4/换根改 `TMP_ROOT_CANDIDATES`。
- 知识库: 计划 `26-11-02-0657`(含变更记录 R0/R1)、坑档 `pitfalls/testing/tmpdir.md` 回填、切片 `26-11-02-0745`、本基线切片; `kb.index` 重建生成物。
- `.tmp_s3_t1.py`(删除): 历史 S3 一次性改写脚本, 提交信息自称「用完即删」却入库, 本轮 `git rm` 清除。
- **零 `src/` 改动**; `config.yml` / `auto-qb-data/` 红线未触碰。
