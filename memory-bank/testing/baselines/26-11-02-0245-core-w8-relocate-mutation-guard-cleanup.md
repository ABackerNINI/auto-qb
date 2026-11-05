# 4804 passed + 1 failed + 2 skipped(根) —— W8 relocate 遗留两件结清(blindspot/low-residue 守阵, 零 src 改动)

> 摘要: W8 relocate 遗留两件结清(blindspot/low-residue 守阵, 零 src 改动)
> 基线时间: 2026-11-02 02:45
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-11-02-0313-gate-writeform-coverage-gap.md

## 验收数字

- **目标**: 全量 pytest(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮守阵的**未提交工作树**(HEAD `bd6c8a32` + `tests/test_relocate_exec.py`、两件 issue HTML、任务档案、本切片)
- `commands run test.full` 实测(wrapper 墙时 137.25s, 2026-11-02 02:45, Windows 本机):
  - 汇总行: `1 failed, 4804 passed, 2 skipped in 137.25s (0:02:17)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率显示值; 闸门内部口径 `98.97%`)
  - **覆盖率闸未过**: `Required test coverage of 99.0% not reached. Total coverage: 98.97%`
- 红验(本轮守阵): Issue A `tmp-analysis/w8fix/redverify_tag.py` **4/4 RED** + 还原 GREEN; Issue B `…/redverify_issueb.py` **8/8 RED** + 还原 GF/SJ 双 GREEN
- 变异池复跑(WSL 镜像 `~/auto-qb-mut-w8fix`, mutmut 3.8.1, `--no-refresh --no-sync`): relocate_mod.py **3006 变异 / 杀 2503 / 存活 503 / 超时 0 / no tests 0**; 存活集对差 518→503 = **新杀 15 / 新增存活 0**
- **环境 / 工具**: Windows 本机(win32)· Python 3.13 · pytest-xdist 8 workers · `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)
- **口径注记(两条红 gate 均为既有、与本轮无关, 范围外不修)**: ①`test_md_no_mixed_line_endings` 报 10 个 2026-09 旧 task `.md` 工作树内 `CRLF xN + LF x1` 混排(HEAD blob 为纯 LF、`git status` 不显, 非本轮文件); ②覆盖率 98.97% 差 99.0% 门槛 —— 本轮 `src/` 零改动, 且上一片 `26-11-02-0059` 在相同 TOTAL 曾判达标, 属测量/并行抖动。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests/test_relocate_exec.py`: ①`_stub_lstat` 增 `omit_tag`(可造 POSIX stat 无 `st_reparse_tag` 形态)+ `test_group_facts_gate_inputs_block_gates` 增非零 tag / 缺省 tag 两段; ②`_stub_cap` 增 `hardlink_ok` 并让 `file_alias_kind` 替身忠实回放同卷硬链接兜底 + `test_group_facts_platform_and_unc_faces` 增 same_volume/capability_ok/file_link_kind 断言; ③`test_start_job_pause_issue_args_and_crash_window` 增补发 setLocation 入参(只发 mover)与发起 rt 初值断言; ④文件头「## 测试计划」同步补注。
- `.commands/mutants/scripts/mutants.py`: `MUTMUT_VERSION = "3.8.1"` + `_ensure_tool` 核版本(修 mutmut 3.8.0 用 pytest 私有 `_nodeid` 与本仓 pytest 9.2 不兼容的 stats 崩溃)。
- `.commands/mutants/scripts/set_conf.py`: `DEFAULT_DESELECT` 追加 `tests/test_relocate_exec.py::test_spawn_args_pinned`(该守阵依赖 `CREATE_NO_WINDOW`, WSL 恒红; Windows 侧仍跑)。
- 知识库回写: 两件 issue HTML(状态 Done + 根因/修法/验证/遗留)、`tasks/26-10-08-test-mutation-audit.md` R37 段、本切片、`kb.index` 重建生成物。
- **零 `src/` 改动**; `config.yml` / `auto-qb-data/` 红线未触碰。
