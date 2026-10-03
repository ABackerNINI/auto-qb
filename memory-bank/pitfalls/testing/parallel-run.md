# 并行跑测试 (pytest-xdist)

> 摘要: **已设为默认**(`pytest.ini` 的 `addopts = -n 4`) —— 全量 21s → **7.6s**(带覆盖率); sidefx 台账已用 `workeroutput` 回传汇总, 「越界 0 条」不再消失。⚠ `-n 0` 曾对**包脚本那批真实临时仓库用例**挂住 —— 根因是 **Windows `subprocess` 无限挂死**(非仓库逻辑), 2026-10-03 用 `_pipeline.run_capture` 看门狗修复(见下节); 覆盖率分支 partial 与串行差 1。
> 触发: 并行, 并发跑测试, xdist, -n, 加速, 多进程, 跑得慢, 闸门, 端口冲突, 台账不打印, 串行挂住, 提交卡死, test.pkg, -n 0, subprocess 挂死, CreateProcess

### ⚠ `-n 0` 曾对 my-commit-flow 的真实仓库用例**挂住**(2026-10-03, 根因已定位并修复)

- **触发**: 跑 `test.pkg` / `test_sync.py`(`.commands/my-commit-flow/scripts/`), 尤其**提交时** ——
  症状是 `ship.commit` **无任何输出即中止**, 看着像闸门静默失败。
- **判别**: `.commands/test/config.toml` 的 `test.pkg` 原写 `-n 0`; 串行跑到 `test_sync.py` 第 **15** 个
  用例后**不再推进**(不报错、不超时退出, 直接挂死; 闸门的 `timeout=300` 把整条提交拖垮)。
  **是否存量**: 取 `git show HEAD:.../test_sync.py` 原版单跑**同样挂** ⇒ 与当次改动无关。
- **根因(2026-10-03 定位)**: **不是**仓库逻辑, 是 Windows 上 `subprocess.run(capture_output=True)`
  在**高负载 + 大量 spawn** 时会**无限挂住** —— 本机 4 个 clone 同时跑 git / 测试时, 从约第 800 次
  spawn 起概率性触发, 两种入口都实测到过(`faulthandler.dump_traceback(all_threads=True)` 抓栈):
  1. **`_winapi.CreateProcess`(即 `Popen.__init__`)不返回** —— 主线程停在
     `subprocess.py:1554 _execute_child`, 连子进程都没起来。
  2. **`communicate()` join 读线程等不到 EOF** —— 主线程停在 `subprocess.py:1663 _communicate → join`,
     两个 `subprocess._readerthread` 阻塞: git 的**孙进程**(`git push` → `sh.exe` →
     `git-receive-pack.exe` → `git.exe`)继承了管道写端且不退出。此时**连 `subprocess.run(timeout=…)`
     也救不了** —— timeout 只杀直接子进程, `communicate()` 仍阻塞在 join。
- **处置(已落地, 在 `.commands/my-commit-flow/scripts/_pipeline.py`)**: 新增 `run_capture()`
  统一入口 —— 真正的 `Popen + communicate` 放在**看门狗线程**里, 主线程只等到 deadline;
  到点用 `taskkill /F /T` 杀**整棵进程树** + 关掉本端管道(不 join), 返回 `rc=-1`。
  把"提交无声冻死"变成**快速可判定的失败**。`git` / `git_rc` / `git_run` / 闸门 `run_gates` /
  `_safe_files` 探针**全部**改走它; `test_sync.py` / `test_commit.py` 的 `_git` 也改走它。
  - ⚠ **超时/非 0 的中间态要显式判**: `run_capture` 把超时收成 `rc=-1`(**不抛**), 而原实现
    靠 `except subprocess.SubprocessError` / `TimeoutExpired` 接超时 —— 例如 `_safe_files` 探针
    必须显式看 `rc != 0` 才摘脚本, 漏判会**静默放行**真动作脚本
    (改的时候被 `test_safety_filter_drops_parameterless_action_scripts` 抓出)。
  - ⚠ **超时必须真的收尸**: 裸 `Popen` 在 `TimeoutExpired` 分支得自己 `taskkill` + `wait()`,
    否则子进程活着占 cwd, 调用方 `tearDown` 立刻 `rmtree` 临时目录 → `WinError 32`
    (改的时候被 `test_timeout_is_failure` / 冒烟用例抓出)。
- **现状**: 修复后 `-n 0` 跑三个包脚本用例 **79 passed / 274.76s**, 不再挂住。
  - 排障单文件**可以**用 `-n 0`; `test.pkg` 仍保持 `-n 4`(闸门能收口, 96 passed / ~105s)。
- **为什么值得单独记**: 它**卡在提交路径上**且**完全静默** —— 不是"跑得慢", 是"提交没有输出就结束了",
  最容易被误读成代码/闸门配置坏了。教训: **Windows 上把子进程 `timeout` 当成万无一失是错的** ——
  还得能**杀整棵树 + 不等读线程**。

### 现状: 默认并行 `-n 4`

- **触发**: 想加速全量 / 想知道并行怎么开(2026-09-23 落地)。
- **判别**(每条都 `1191 passed + 1 skipped`):
  | 方式 | 耗时 |
  |---|---|
  | 串行 `-n 0` | 21.15 / 21.56s |
  | **`-n 4`(默认)** | **7.61 / 7.79 / 8.87s**(带覆盖率) |
  | `-n 4 --no-cov` | 5.00 / 5.06 / 5.17s |
  | `-n 8 --no-cov` | 4.88s |
  | `-n 16 --no-cov` | 6.82s(**更差** —— worker 启动开销开始占主导) |
  ⇒ **`-n 4` 是甜点**。⚠ 别用 `-n 16`。
- **怎么开的**: ①`pyproject.toml` dev 组加 `pytest-xdist==3.8.0`; ②`pytest.ini` 的 `addopts` 加 `-n 4`。
  ⇒ **单文件跑会慢在 worker 启动上**, 排查时用 `-n 0`(如 `uv run pytest tests/test_web.py -q -n 0`)。
- **⚠ 结论曾经是反的**: 同日早些时候 `-n 4` 在 **15.94~209.77s** 之间乱跳(中位 ~31s, **尾部比串行最坏还差**),
  当时判定"闸门保持串行"。根因是**底层文件操作被拦截**(见 [perf-measurement.md](perf-measurement.md))——
  多进程只是把那份争用**放大**。系统层排除项修好后同一命令稳定在 ~5s, 波动几乎消失。
  ⇒ **"并行划不划算"取决于底层是否串行; 底层一改就要重测, 别把旧结论当定论。**

### sidefx 台账在并行下会消失 —— 已用 `workeroutput` 回传解决

- **触发**: 并行跑时收尾看不到「副作用台账 … 越界 0 条」那行(2026-09-23 实测)。
- **判别**: **拦截没丢, 丢的是可见性** —— 守卫是**会话级夹具**, xdist 下每个 worker 各跑一个会话、
  **各自会红**; 用仓库外插件 `R:/Temp/auto-qb/plugins/pa_violate.py` 注入一条越界删除验证:
  串行与 `-n 4` **都**报 `AssertionError: 测试期出现 1 条越界的真实系统副作用`。
  真正的问题是 `pytest_terminal_summary` **只在控制器上产出**, 而台账在 worker 上 ⇒ 静默消失。
- **处置(已落地, 在 `tests/conftest.py`)**: worker 侧把台账写进 `config.workeroutput`,
  控制器侧用 xdist 钩子 `pytest_testnodedown` 从 `node.workeroutput` 收, 在终端总结里**汇总成一行**:
  `副作用台账(4 个并行 worker 汇总): 共 2034 条, 越界 0 条`。
  **有越界时**额外把该 worker 的全文打出来 —— 比串行**更好**, 能看出是哪个 worker。
  串行跑时该钩子不被调用, 走原来的 `sidefx.LAST_REPORT` 路径。
  ⚠ 台账**条数**与串行不逐字相同(并行 2034 vs 串行 2036): 每个 worker 的会话起止各记一笔, 属正常。
- **覆盖率**: 并行 `7729 语句 / 623 未覆盖 / **219** 分支` vs 串行 `623 / **218**`, TOTAL 都是 91%
  ⇒ 并行下**分支 partial 多 1**(语句数一致), 换默认口径时留意。

### 项目文档里"并行不行"的那条理由是错的

- **触发**: 评估并行时会撞到既有说法 —— "本项目有绑定本地端口的 `FakeQbServer` 用例, 所以不能并行"。
- **判别**: **事实有误** —— `tests/helpers.py:388` 用的是 `ThreadingHTTPServer(("127.0.0.1", 0), ...)`,
  端口 **0 = 由内核分配**, 天然不撞。
- **处置**: 别拿这条当挡箭牌。
