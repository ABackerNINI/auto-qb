# port-kill-subprocess-encoding

> 摘要: 修复 issue 26-11-07-1216: port_kill.py 两处 subprocess 未钉 encoding (cp1252 同病) —— 实际扩成 5 处钉码 (port_kill x2 / e2e_selfcheck / hr_fetch_experiment / sim_run Popen), 守卫 test_repo_text_subprocess_calls_pin_utf8 扫描面 tests/ 扩到 tests/+scripts/, 扩面当场抓出 sim_run.py:813; test.full 全绿 (见 kb.baseline); 评审 3 轮 (0+3 minor 全修); issue 翻 Done, pitfalls 两条复发补记, 基线切片 26-11-10-0044
> 最后活动: 2026-11-10 00:45

**R0(2026-11-10 00:45):** 修复 issue 26-11-07-1216: port_kill.py 两处 subprocess 未钉 encoding (cp1252 同病) —— 实际扩成 5 处钉码 (port_kill x2 / e2e_selfcheck / hr_fetch_experiment / sim_run Popen), 守卫 test_repo_text_subprocess_calls_pin_utf8 扫描面 tests/ 扩到 tests/+scripts/, 扩面当场抓出 sim_run.py:813; test.full 全绿 (见 kb.baseline); 评审 3 轮 (0+3 minor 全修); issue 翻 Done, pitfalls 两条复发补记, 基线切片 26-11-10-0044
