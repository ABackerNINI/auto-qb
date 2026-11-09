# 5876 passed, 2 skipped —— tests-real RM10 guardian 三用例退役批全量复测 (issue 26-11-09-2128)

> 摘要: tests-real RM10 guardian 三用例退役批全量复测 (issue 26-11-09-2128)
> 基线时间: 2026-11-09 23:41

## 验收数字

- HEAD: 77b649fc(快进并入远端 1 笔纯 docstring 措辞修后复测)
- `commands run test.full` 2026-11-09 23:41 实测: **5876 passed, 2 skipped, 0 failed**(127.02s)
- TOTAL 行: 26153 stmts / 41 miss · 9102 branches / 53 partial → 覆盖率 99.73%(阈值 99.5% 达标)

## 本改动面

- `tests-real/rm10_notify/test_rm10_notify.py`: 退役 RM10-05/06/07 三条 guardian 用例(测已随 S4a 66418c7e 整文件退役的 finalize_watch)+ 独占 helper(`_StepClock`/`_journal_watch`/`_accept_loop`/`build_guardian_scene`/`GUARDIAN_JOB`/`dead_port`)+ 过期导入(relocate_journal 全部符号/alias_fs/guard/json/socket), docstring 八条→五条; 10 增/325 删
- `tests-real/rm10_notify/conftest.py` + `test_rm10_export_merge.py`: 评审发现的 docstring 数字/口径随改(4 增/4 删、1 增/1 删)
- `memory-bank/issues/26-11-09-2128-*.html` 收口 Open→Done + 实际修法小节; 新档案 `tasks/26-11-09-test-rm10-guardian-tests-retire.md`
- 验证: `uv run pytest tests-real/rm10_notify/test_rm10_notify.py --collect-only` 收集 5 条 import 不再失败(修复前整文件无法收集)
