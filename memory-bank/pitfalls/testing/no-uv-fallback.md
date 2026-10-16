# 本 clone 工具 shell 无 uv / 无 R 盘时跑测试的兜底

> 摘要: 包内 `test.*` 任务单点写着 `uv run pytest`, 而**本 clone 的工具 shell 的 PATH 里没有 `uv`**(实测 uv 本体已装在 `C:\Users\<用户>\.local\bin\uv.exe`, 只是不在 PATH) ⇒ 每个测试任务在第一行就失败(`'uv' is not recognized`), 闸门同理; `.commands/test/config.toml` 的 `TMPDIR=R:/Temp/auto-qb/tests` 指向的 **R: 盘本机也不存在**。首选处置 = **本次调用前把该目录前置进 PATH**(包内 task/闸门全线恢复, 实测), 次选 = 用仓库 venv 的 python 直跑 pytest + `TMPDIR` 指到 C 盘临时区。
> 触发: 跑测试, 提交, 闸门, uv, command not found, .local\bin, PATH, R:/Temp, 驱动器不存在, DriveNotFoundException, 全量, TMPDIR, COVERAGE_FILE, basetemp

**Refs:** memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md, memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

### 包内测试任务在本机跑不起来: uv 不在 PATH + R 盘不存在

- **触发**: 本 clone(Windows 工具 shell)里敲 `commands run test.full` / `test.one` / `test.quick`, 或任何以 `uv run …` 为 run 体的 task。
- **判别**: 两层叠加 ——
  · **uv 缺席**: `Get-Command uv` 无输出; `commands.cmd` 因此回退 `python run.py`(它能定位引擎并把 task 跑起来), 但 **task 体自身写死 `uv run pytest`** ⇒ 输出 `[FAIL] test.one (0.0s)` + `'uv' is not recognized as an internal or external command`。
  · **R 盘缺席**: `New-Item R:/Temp/...` 报 `DriveNotFoundException`(名为"R"的驱动器不存在) ⇒ 即便有 uv, 照抄 task 体的 `TMPDIR=R:/Temp/auto-qb/tests` 也落在不存在的盘上。这是**机器差异**不是仓库缺陷 —— 坑档 `testing/tmpdir.md` 同时列了 `C:/Users/<用户>/AppData/Local/Temp` 作为认可替代。
- **处置**: ①**首选: 本次调用前把 uv 所在目录前置进 PATH**(实测一次修复全线 —— dev.fmt 1.1s 过 / test.quick 过 / 整个 ship.commit 329.5s 成功推送; uv 未触碰 uv.lock / pyproject):

  ```powershell
  $env:PATH = "C:\Users\<用户>\.local\bin;$env:PATH"   # uv.exe 常在这(uv 自身安装器的默认落点), 只是没进工具 shell 的 PATH
  uv --version   # 实测 0.12.18, 项目 requires-python >=3.12, 直接复用仓库 .venv, 不重建
  ```

  ②**兜底(不前置 uv 时)**: ❌ 不要改 `.commands/*/config.toml`(全体 clone 共享的单点, 改它 = 把本机差异写进仓库); ❌ 也不要裸跑 pytest 而不设 `TMPDIR`(工具 shell 默认 `H:\Temp` 的重解析点会让收尾崩, 点号全过也判红)。用仓库 venv + C 盘临时区复刻 task 体的其余部分:

  ```powershell
  cd <仓库根>
  $env:TMPDIR='C:/Users/<用户>/AppData/Local/Temp'      # 不存在则先 New-Item -ItemType Directory
  $env:COVERAGE_FILE="$env:TMPDIR/aqb.coverage"          # 覆盖率文件不能落仓库根(tmpdir.md)
  $bt = "$env:TMPDIR/aqb-bt-" + [guid]::NewGuid().ToString('N').Substring(0,8)  # basetemp 必须"全新"
  .venv/Scripts/python.exe -m pytest tests -q --basetemp=$bt   # -n 8 等由 pytest.ini addopts 供
  ```

  单文件 / 筛选用例: 把 `tests` 换成目标文件并补 `-n 0 --no-cov`(与 `test.one` 口径一致; 单文件跑并行反而慢在 worker 启动, 覆盖率门槛只对全量收集面有意义, 见 `single-file-coverage-gate.md`)。全量判据看**末行**: `N passed, M skipped in …` + `Required test coverage of 98% reached`(exit=0)。
  ⚠ 另一条易踩: `| Select-Object -Last N` 接 pytest 会缓冲到结束才出输出(看着像卡死) —— 重定向到文件再读尾部(`> <log> 2>&1`), 或耐心等汇总行。
  ⚠ 兜底路径下的闸门替代: 包内闸门里 `TMPDIR=R:/Temp/...`(R 盘不存在)会自然回落到 `TEMP`/`TMP` —— 调用前把这两个也指向 C 盘临时区, 否则回落 `H:\Temp` 撞同一条收尾崩。
- **与既有坑档的关系**: `tmpdir.md`(TMPDIR / 临时目录 / 收尾崩)只覆盖临时目录面, 本条补的是「包内 task 依赖 uv, 而本机无 uv」这一层入口差异; `sandbox-full-run.md`(沙箱拒写 R:\Temp ⇒ 回落 H:\Temp 收尾崩)同属环境面假红。
- **复发 +1 (2026-10-16 15:09, 本 clone)**: 认领轮开工时又踩。会话首个动作按协议跑了开工同步(它走纯 python, 不触 uv), 随后**直接调 `uv run python .agents/skills/commands/scripts/install_wrapper.py`**(装 wrapper 的正规写法)而没先走 task id ⇒ 第一条即 `'uv' is not recognized`。
  - **为什么没命中(路由没到)**: `pitfalls/_index.md` 是在这条失败**之后**才读的, 而 `testing/` 类索引(本条所在类)直到跑测试前才轮到 —— 「先读 pitfalls 再动手」的次序被「协议硬步骤 + 直调 uv」这两步绕过了。走向 task id 的写法则会在 task 体里当场暴露同一句话, 这是本条的判别面没被用上的原因。
  - **处置(按本条首选)**: `$env:PATH = "C:\Users\<用户>\.local\bin;$env:PATH"` ⇒ 实测 uv 0.12.18 立即可用, `commands` 引擎随之自动走 `uv run` 分支, 包内 task 全线恢复(无需改 `.commands/*/config.toml`)。**R 盘仍不存在** ⇒ 跑 `test.*` 时 task 体的 `TMPDIR=R:/Temp/...` 会自然回落; 调用前把 `TEMP`/`TMP` 指向 C 盘临时区以固定回落目标。
- **复发 +2 (2026-10-16 17:5x, 本 clone, GitHub CI 修复轮)**: 又一次开工即踩 —— 会话首个动作 `commands run my-commit-flow.sync` 报「无法将"commands"识别为 cmdlet…」(wrapper 不在 PATH), 紧接着按正规写法直调 `uv run python .agents/skills/commands/scripts/install_wrapper.py` 又撞 `'uv' is not recognized`; 直到按本条首选前置 PATH 后 `\commands.cmd run …` 全线恢复(wrapper 本已存在, 无需重装)。
  - **为什么没命中(路由没到)**: 与 15:09 那次同因 —— 协议硬步骤(开工同步)先跑, 直调 uv 时本条尚未读到; `pitfalls/_index.md` / `testing/_index.md` 是排障途中才打开的。**根治方向**: 把「本 shell 无 uv ⇒ 先前置 PATH」挪到开工第一条的现现场(或让 sync 的失败行自带该提示), 否则每个新会话都要重踩一次。
- **复发 +3 (2026-10-16 18:2x, 本 clone · global-traffic-monitor S9 轮)**: 同一会话里第二次撞上, 形态比上一条更隐蔽 —— 不是直接敲 `uv`, 而是敲**包内 task**(经引擎展开为 `uv run python …run.py run test.full`): 引擎本体能跑(python 脚本), 失败的是 task **体**里的 `uv run pytest`, 输出只有 `[FAIL] test.full (0.0s)` + `'uv' is not recognized as an internal or external command` —— 看上去像 test.full 自己坏了。
  - **为什么没命中**: 本会话开工起就用 **uv 的绝对路径**(`& "$env:USERPROFILE\.local\bin\uv.exe" …`)跑同步与引擎, 于是「PATH 里没有 uv」这件事在前几轮从未暴露; 读到本条时把它归成了「敲 `commands` 失败」的入口差异, 没延伸到「引擎能跑 ≠ 它调起的 task 体能跑」。
  - **处置**: 照本条首选 —— 调用前 `$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"`, 并把 `TEMP`/`TMP` 指向 C 盘临时区(R 盘不存在, task 体的 `TMPDIR=R:/Temp/...` 会回落), 随后 `test.full` 正常跑完并给出覆盖率结论行。
