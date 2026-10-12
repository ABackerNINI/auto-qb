# 3147 — dup-code-audit infra 修复轮 3 条 refactor issue 实施基线

> 摘要: 用户「认领并修复」infra 轮(R18)入池的 3 条 refactor issue(`26-10-11-0352-refactor-infra-*`)—— A/C 类抽单点收敛, 保守口径(行为逐字不变, 既有守阵回归): ①`infra-url-decompose-dup` 抽 `utils._split_url(url) -> (scheme, netloc, path, query)` 单点(去 userinfo / 缺 scheme path 首段兜底且首段消费后不回填 / 失败 None), `sanitize_tracker_url` 与 `mask_tracker_url` 共用; ②`infra-utils-small-helper-dup` 抽 `utils._hosts_of(urls)`(`extract_tracker_hostnames` 与 `match_tracker_confs` 的 host 收集内联循环归一, 入参形态差异由调用方适配) + `file_access` 基类 `FileAccess._probe(os_fn, path)`/`_probe_path` 收编 exists/isdir/isfile 三连(Local 传 `self._pref`、Mapped 传 `map_to_container` 的 syscall 路径, miss => UNDETERMINED); ③`infra-win-dll-lazy-bind-dup` 抽 `utils._win_dll(name, sigs)` 参数化惰性绑定骨架, `_win_user32`/`_win_kernel32` 保留 `_bound_*` 全局缓存与 monkeypatch 注入点, `is_windows()` 早退保持在缓存判定**之前**(守阵 `test_win_user32_kernel32_non_windows_none` 不重置缓存, 靠该顺序)。修法二: `_WIN_KERNEL32_SIGNATURES()` 与 user32 版同口径。**同步更新静态守阵**: 三态探针收编后 `os.path.exists` 由调用变基类属性引用(`_probe(os.path.exists, ...)`), mock 按模块属性打桩覆盖不变 ⇒ `tests/test_sim_corpus.py` 的 `_EXPECTED_PROBES` 去掉 exists 钉计数(注释说明), `scripts/sim_fsmock.py` 的 `MockCoverage` 覆盖说明同步。
> 基线时间: 2026-10-12 21:25(3 条 issue 全部实施后收口)

**Refs:** memory-bank/activeContext/26-10-12-2110-infra-dup-code-fixes.md,memory-bank/issues/26-10-11-0352-refactor-infra-url-decompose-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-utils-small-helper-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-win-dll-lazy-bind-dup.html

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 dea14b62; 工作树含本批次全部改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3147 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16689 语句 / 159 未覆盖 / 5682 分支 / 140 partial; 门槛 98% 达标; 本轮 48.39s)
- 前置机检: 定向 `tests/test_utils.py` + `tests/test_file_access.py` 全绿(119 passed + 2 skipped); 首轮 test.full 曾红 `test_fs_mock_coverage_static_guard`(探针写法从调用变属性引用, 期望表未同步) —— 按守阵自身规矩更新 `_EXPECTED_PROBES`/`MockCoverage` 后复绿; 改动文件 `dev.fmt` 全量格式化通过。
- 改动面(摘要): `src/auto_qb/infra/utils.py`(_split_url / _hosts_of / _win_dll + _WIN_KERNEL32_SIGNATURES) + `src/auto_qb/infra/file_access.py`(_probe/_probe_path) + `tests/test_sim_corpus.py`(静态守阵期望表) + `scripts/sim_fsmock.py`(MockCoverage 覆盖说明) + `memory-bank/issues/` 3 条状态流转。见 kb.baseline。
