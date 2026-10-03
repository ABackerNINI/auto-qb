# 基线 · 2415 passed + 3 skipped / 99% —— 修 `-n 0` 串行挂死(Windows 子进程看门狗)

> 摘要: 清偿上一会话([26-10-03-2116](26-10-03-2116-commands-argv-flag-swallowed.md))的遗留观察 ——
> `test.pkg` / `test_sync` 的 `-n 0` 串行在第 15 个用例后**无限挂住**, 拖垮 `ship.commit` 闸门。
> **根因不是仓库逻辑**: Windows 上 `subprocess.run(capture_output=True)` 在**高负载 + 大量 spawn**
> 时无限挂死 —— `faulthandler` 抓栈到两种等价入口: ①`_winapi.CreateProcess`(`Popen.__init__`)不返回;
> ②`communicate()` join 读线程等不到 EOF(git 的**孙进程**继承了管道写端不退)。此时 `subprocess.run(timeout=…)`
> 也救不了。**修法**: `_pipeline.py` 新增 `run_capture()` 看门狗(硬截止 + `taskkill /F /T` 杀整棵树);
> `git` / `git_rc` / `git_run` / 闸门 `run_gates` / `_safe_files` 探针全改走它。`-n 0` 三个包脚本用例
> **79 passed / 275s 不再挂**; `-n 4` **79 passed / 100s**。
> 坑档 `pitfalls/testing/parallel-run.md` 从「根因未定位, 留给 issue」改写为真根因 + 修法。
> 基线时间: 2026-10-03 23:16, develop @ fa5cc5ed + 工作区(本轮回写件未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

**Refs:** memory-bank/activeContext/26-10-03-2316-subprocess-hang-n0.md

TOTAL **2415 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
`test.full` 49.04s, rc=0)。
相对上一切片(26-10-03-2116: 2415 passed + 3 skipped / 99%, 14,395 语句 / 131 未覆盖 / 4,810 分支,
@ fa5cc5ed)**passed / 语句 / 分支全部持平** —— 本单**净零用例变化**: 只是把已有 spawn 调用改走
`run_capture`, 未新增/删除测试; 守阵用例(`test_pipeline` / `test_sync` / `test_commit`)在 `tests/` 之外,
本 TOTAL 收不到, 其数字见下。

## 包内脚本测试(`tests/` 之外, 走 `test.pkg` / `test.one`)

| 跑法 | 结果 |
|---|---|
| `-n 0` 三个包脚本用例(test_pipeline + test_sync + test_commit) | **79 passed / 274.76s**(修复前: 第 15 个后无限挂) |
| `-n 4` 同三文件 | **79 passed / 100.03s** |
| `-n 4` `.agents/skills/commands`(引擎测试) | **17 passed / 6.41s** |

⚠ 注意: `test.pkg` 保持 `-n 4`(闸门要快 + 能收口), 不因修复而改回 `-n 0` —— 修复解决的是"挂死",
不是"串行更好"。

## 连带的两个「改错会静默/红」的坑(已抓出并写进注释)

1. **超时收成 `rc=-1` 不抛** ⇒ 原 `_safe_files` 靠 `except subprocess.SubprocessError` 接超时,
   改走 `run_capture` 后必须**显式判 `rc != 0`**, 否则探针超时被当"安全"⇒ **静默放行真动作脚本**
   (被 `test_safety_filter_drops_parameterless_action_scripts` 抓出)。
2. **裸 `Popen` 在 `TimeoutExpired` 分支要自己收尸** —— 只记 pid 不杀, 子进程活着占 cwd,
   调用方 `tearDown` 立刻 `rmtree` 临时目录 → `WinError 32`
   (被 `test_timeout_is_failure` / 冒烟用例抓出)。
