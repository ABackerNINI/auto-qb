# 5876 passed + 2 skipped (99% 覆盖, 26152 stmts) —— issue 26-11-07-1216 修复批: 守卫扩面 scripts/ + 5 处钉码

> 摘要: issue 26-11-07-1216 修复批: 守卫扩面 scripts/ + 5 处钉码
> 基线时间: 2026-11-10 00:44

## 验收数字

`commands run test.full` 实测 (2026-11-10, head `f905b7b7` + 本批未提交改动):

- TOTAL 表: `26152 statements, 41 missed, 9102 branches, 53 partial, 99%`
- 汇总行: `5876 passed, 2 skipped in 162.30s (0:02:42)`
- 与上一基线 (26-11-09-2341, 5876 passed + 2 skipped) 差值: passed ±0 —— 本批只给 5 处
  `subprocess` 文本调用补 `encoding`/`errors` 关键字并扩 `test_repo_text_subprocess_calls_pin_utf8`
  扫描面 (tests/ → tests/ + scripts/), 无新增用例; 守卫扩面后 scripts/ 下无残余违例。

## 本改动面

- `scripts/port_kill.py`: `listening_pids` 的 powershell 调用与 `main` 的 taskkill 调用补
  `encoding="utf-8"` + `errors="replace"` (issue 本体两处, 多行化以守 120 列)。
- `scripts/e2e_selfcheck.py`: `_proc_info` powershell 调用同款钉码 (扩面守卫抓出的同病)。
- `scripts/hr_fetch_experiment.py`: `_kill_profile_browsers` powershell 调用同款钉码 (保留 `timeout=20`;
  其后 taskkill 字节模式调用不归守阵, 未动)。
- `scripts/sim_run.py`: 启动子进程的 `Popen` (stdout 重定向进 log) 钉码, 与 log 文件自身的
  utf-8+replace 口径对齐 (单行 grep 漏扫、扩面守卫亮红抓出)。
- `tests/test_platform_tolerance_guards.py`: `test_repo_text_subprocess_calls_pin_utf8` 扫描面
  `tests/` → `tests/ + scripts/` (新增 `SCRIPTS` 常量); 断言文案与文件头 docstring「测试计划」行同步。
- 记账: issue 26-11-07-1216 翻 Done (复验/修复后补充已填), pitfalls `ops/console-encoding.md`、
  `testing/tmpdir.md` 各补一条复发。
