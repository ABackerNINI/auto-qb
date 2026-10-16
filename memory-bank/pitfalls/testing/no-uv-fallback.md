# 本 clone 工具 shell 无 uv / 无 R 盘时跑测试的兜底

> 摘要: 包内 `test.*` 任务单点写着 `uv run pytest`, 但**本 clone 的工具 shell 里 `uv` 不可用**(PATH 无 uv), 且 `.commands/test/config.toml` 的 `TMPDIR=R:/Temp/auto-qb/tests` 指向的 **R: 盘本机不存在** ⇒ 每个测试任务在第一行就失败(`'uv' is not recognized`)。兜底 = 用仓库 venv 的 python 直跑 pytest, 并把 `TMPDIR` 指到坑档已认可的 C 盘临时区。
> 触发: 跑测试, uv, command not found, R:/Temp, 驱动器不存在, DriveNotFoundException, 全量, TMPDIR, COVERAGE_FILE, basetemp

**Refs:** memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md

### 包内测试任务在本机跑不起来: uv 不在 PATH + R 盘不存在

- **触发**: 本 clone(Windows 工具 shell)里敲 `commands run test.full` / `test.one` / `test.quick`, 或任何以 `uv run …` 为 run 体的 task。
- **判别**: 两层叠加 ——
  · **uv 缺席**: `Get-Command uv` 无输出; `commands.cmd` 因此回退 `python run.py`(它能定位引擎并把 task 跑起来), 但 **task 体自身写死 `uv run pytest`** ⇒ 输出 `[FAIL] test.one (0.0s)` + `'uv' is not recognized as an internal or external command`。
  · **R 盘缺席**: `New-Item R:/Temp/...` 报 `DriveNotFoundException`(名为"R"的驱动器不存在) ⇒ 即便有 uv, 照抄 task 体的 `TMPDIR=R:/Temp/auto-qb/tests` 也落在不存在的盘上。这是**机器差异**不是仓库缺陷 —— 坑档 `testing/tmpdir.md` 同时列了 `C:/Users/<用户>/AppData/Local/Temp` 作为认可替代。
- **处置**: ❌ 不要改 `.commands/*/config.toml`(全体 clone 共享的单点, 改它 = 把本机差异写进仓库); ❌ 也不要裸跑 pytest 而不设 `TMPDIR`(工具 shell 默认 `H:\Temp` 的重解析点会让收尾崩, 点号全过也判红)。**用仓库 venv + C 盘临时区复刻 task 体的其余部分**(实测跑通全量含覆盖率闸门):

  ```powershell
  cd <仓库根>
  $env:TMPDIR='C:/Users/<用户>/AppData/Local/Temp'      # 不存在则先 New-Item -ItemType Directory
  $env:COVERAGE_FILE="$env:TMPDIR/aqb.coverage"          # 覆盖率文件不能落仓库根(tmpdir.md)
  $bt = "$env:TMPDIR/aqb-bt-" + [guid]::NewGuid().ToString('N').Substring(0,8)  # basetemp 必须"全新"
  .venv/Scripts/python.exe -m pytest tests -q --basetemp=$bt   # -n 8 等由 pytest.ini addopts 供
  ```

  单文件 / 筛选用例: 把 `tests` 换成目标文件并补 `-n 0 --no-cov`(与 `test.one` 口径一致; 单文件跑并行反而慢在 worker 启动, 覆盖率门槛只对全量收集面有意义, 见 `single-file-coverage-gate.md`)。全量判据看**末行**: `N passed, M skipped in …` + `Required test coverage of 98% reached`(exit=0)。
  ⚠ 另一条易踩: `| Select-Object -Last N` 接 pytest 会缓冲到结束才出输出(看着像卡死) —— 重定向到文件再读尾部(`> <log> 2>&1`), 或耐心等汇总行。
- **与既有坑档的关系**: `tmpdir.md`(TMPDIR / 临时目录 / 收尾崩)只覆盖临时目录面, 本条补的是「包内 task 依赖 uv, 而本机无 uv」这一层入口差异; `sandbox-full-run.md`(沙箱拒写 R:\Temp ⇒ 回落 H:\Temp 收尾崩)同属环境面假红。
