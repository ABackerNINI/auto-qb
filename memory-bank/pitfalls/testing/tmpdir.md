# 临时目录与跑全量

> 摘要: 临时目录必须在 `tempfile.gettempdir()` 之下、覆盖率文件不能留仓库根、`TMPDIR` 不设收尾会崩, 别手工加前缀。
> 触发: 跑全量, basetemp, TMPDIR, 临时目录, 覆盖率文件, pytest-current, 耗时, 手工跑子集, R 盘缺席, 回落 TEMP, 快照守阵, 自举, auto-qb-tests, 外部 TMPDIR 拒收, rc=4, rc=3, 测试互斥锁, coverage 落点, Z 盘共享, 宿主机内存盘

**Refs:** memory-bank/plans/26-11-02-0657-plan-testing-tmpdir-bootstrap.html

### 测试 TMPDIR 已由 `tests/unit/_tmp_bootstrap.py` 自举接管(2026-11-02); 外部 TMPDIR 一律拒收 rc=4

- **触发**: 跑 tests/ 树的任何 pytest; 或想在 shell / run config / config.toml 里手工设 `TMPDIR`。
- **判别**:
  · 探测 R: → H: → 系统 `%TEMP%`(单一配置点 `TMP_ROOT_CANDIDATES`; 本机无 R/H ⇒ 常态走 `%TEMP%`);
    实例根 `<根>/auto-qb-tests/<repo hash8>-<pid>-<rand6>` —— 连跑两次根互异, xdist worker 同根;
    各 clone 按 repo 路径 hash 分根, 互不共享。
  · **映射盘共享不可作测试实例根**(26-11-28 实测撤回): Z:\R(宿主机内存盘经 VMware HGFS 共享)
    曾试入候选, 全量 187 failed —— 映射盘被 realpath 解析成 `\\vmware-host\...` UNC ⇒ 产品卷
    语义/搬迁闸门把 src 判远程卷成片假红, 且 junction 在共享挂载不可建(需本地 NTFS 卷, 另证)。
    已从候选撤回并留守卫(顺序用例断言 Z: 永不入列); 内存盘共享只喂纯写面 —— real.seed 大种子
    (`tests/real/seed.py::RAM_ROOT_CANDIDATES` 探针)与 sim root(`AUTOQB_SIM_ROOT`), 真机搬迁
    数据走 rm04 的 junction 试建探针(共享盘探不过自动退 .work)。
  · 外部 `TMPDIR`(值不含 `auto-qb-tests` 标记)→ 进程响亮退出 **rc=4** 并给清理指引;
    旧 `set "TMPDIR=R:/Temp/auto-qb/tests"` 前缀**已废止**(R: 在本机不存在, 该写法自 2026-09-23 引入起
    从未生效, 全靠 gettempdir 静默回落掩盖 —— git 考证见计划 `plans/26-11-02-0657`)。
  · 同口径已下沉到包测试(2026-11-14): `.commands/conftest.py` 对全体包测试拒收「gettempdir 落在仓库根
    之内」(rc=4 + FATAL, 判据 .git 含 HEAD / worktree 文件形态与 `_snapshot._find_repo_root` 同源;
    回归阵 `.commands/test_conftest_guard.py`) —— 背景(沙箱 /tmp 不可写 ⇒ tempfile 候选末位静默回落
    CWD=仓库根)与事故链单点在 `issues/26-11-14-0857-…snapshot-anchor.html`。
  · 本文件 2026-09 诸条目里「手工把 TMPDIR 指到某盘」的处置均为**前自举时代**写法;
    症状机制(basetemp 须在 `gettempdir()` 之下 / 收尾 `pytest-current` 崩溃)仍有效, 处置以本条为准。
  · coverage 落点: pytest-cov 在 `pytest_load_initial_conftests`(tryfirst) 就把 data_file 绑成
    CWD 的 `.coverage`(早于一切 conftest), env `COVERAGE_FILE` 对主进程**无效**;
    conftest `pytest_configure` 调 `_tmp_bootstrap.retarget_cov_data_file()` 改写 `_data._filename`
    重定向(xdist worker 启动晚, env 天然有效)。**若升级 pytest-cov/coverage 后仓库根又见 `.coverage.*`,
    先查这个私有面**(钉版于 uv.lock, 回归阵 `tests/unit/test_tmp_bootstrap.py`)。
  · 同 clone 写重型全量互斥锁 `<系统temp>/auto-qb-locks/<repo hash8>`: 撞锁 **rc=3** + 打印持锁者,
    强杀后下一位自愈; 残留实例根按「mtime 超 12h 且内嵌 pid 已死」双条件清扫(阈值暂定可调)。
- **处置**: 一律 `commands run test.*` 或裸 `uv run pytest tests ...`, **任何层都别预设 TMPDIR**。
- **复发**: 1(2026-11-04)—— AI shell 环境自带外部 `TMPDIR=C:\Users\…\AppData\Local\Temp`,
  裸 `uv run pytest` 与 `commands run test.full`(后台 shell 同 env)双双 rc=4, `env -u TMPDIR` 前缀后正常
  (为什么没命中: AGENTS.md 有该硬约束提示但开工只读了 pitfalls 总索引没进 testing 类索引;
  收尾跑全量换后台 shell 时又忘了 env 随 shell 走)。
- **复发**: 2(2026-11-04)—— 同日不同 clone 再踩同形: `commands run test.quick` 直跑 rc=4,
  `unset TMPDIR` 后过。为什么没命中: 跑测试前没进 testing 类索引(路由没到);
  失败行自带清理配方, 照做即过, 零排查成本。
- **复发**: 3(2026-11-06)—— issue 26-11-06-0330 收尾跑全量: 本 shell 自带 `TMPDIR=H:\Temp`,
  `commands run test.full` 1.3s 内 rc=4(拒收), 前缀 `TMPDIR= commands run test.full` 即过。
  为什么没命中: 又是在收尾"顺手跑个全量"时忘了 env 随 shell 走 —— 与上两轮同款,
  开工/收尾两次跑测试前都应先过一次 testing 类索引。
- **复发**: 4(2026-11-06)—— issue 26-11-06-0247 收尾: 自己的 `test.full` / `test.one` 都加了
  `env -u TMPDIR`, 但 `commands run ship.commit` **内部的闸门** `test.quick` 是同 env 子进程,
  于是提交被闸门拦下(rc=4)。为什么没命中: 把「跑测试要清 TMPDIR」记成了「我的 test.* 调用要清」,
  漏了闸门/流水线里的间接调用 —— 处置: **提交也走 `env -u TMPDIR commands run ship.commit`**。
- **复发**: 5(2026-11-08)—— issue 26-11-08-0703 修复轮首次 `commands run test.one` 直跑 rc=4
  (本 shell 自带 `TMPDIR=H:\Temp`), 加 `env -u TMPDIR` 前缀后全绿; 其后 `test.full` 从第一次就带前缀。
  为什么没命中: 开工只读了 pitfalls 总索引与 conventions 总索引, 没进 testing 类索引(路由没到);
  且把 AGENTS.md「别手工加前缀」读成了不必清 env —— 应把「跑任何 pytest 前先 `env -u TMPDIR`」当固定动作。
- **复发**: 6(2026-11-08)—— 修 Linux CI `test_r4_shortcuts_engine_table_and_keydown` 偶发红时,
  首次 `commands run test.one` 又直跑 rc=4(本 shell 仍自带 `TMPDIR=H:\Temp`), `env -u TMPDIR` 后过;
  本轮其后所有 pytest 均带前缀。为什么没命中: 开工按「先索引后 grep」读了总索引/README, 但定位焦点在
  前端 node 电池, 没顺着 testing 类索引点开本文件 —— 跨专题时最容易漏的固定动作。
- **复发**: 7(2026-11-10)—— issue 26-11-07-1216 修复轮首次 `commands run test.quick` 直跑 rc=4
  (本 clone 的 shell 自带 `TMPDIR=C:\Users\…\AppData\Local\Temp`), `TMPDIR=` 清空后过, 其后全带前缀。
  为什么没命中: AGENTS.md 测试节与失败行都写了判据, 但开工没把「跑任何 pytest 前先清 TMPDIR」
  当固定动作 —— 又一次证明该动作要放在跑测试的第一条命令里, 不是踩到 rc=4 再补。
- **复发**: 8(2026-11-10)—— 修复 GitHub CI 四组 e2e 既有红收尾, `commands run test.full` 直跑 1.0s
  rc=4(本 shell 自带 `TMPDIR=H:\Temp`), `env -u TMPDIR -u TEMP -u TMP` 后全绿; 其后所有
  pytest / test.full 均带前缀。为什么没命中: 开工按协议同步 + 读 kb.active 切片, 但没进
  testing 类索引, 直到失败行打出自检配方才想起 —— 与复发 3/5/6/7 同款「收尾顺手跑全量」形态;
  本轮还额外确认 `ship.commit` 内部闸门同 env, 提交也要带前缀(复发 4)。
- **复发**: 9(2026-11-11)—— webui 双排 title 退役批: 首次 `test.quick` rc=4 后补 `unset TMPDIR` 过,
  但**评审前置链 `sync && ship.gate` 组合命令漏带前缀**, `ship.gate` 内部 `test.quick` 再 rc=4 一次。
  为什么没命中: 已把前缀记成「跑测试的命令要带」, 漏了**组合命令里间接跑 pytest 的非 test.* 环节**
  (ship.gate 预跑闸门) —— 同复发 4 的「闸门同 env」教训换了个入口(ship.gate 而非 ship.commit)再犯;
  前缀应挂在**整条组合命令**开头, 不是只挂 test.* 调用。
- **复发**: 10(2026-11-18)—— 两则 e2e 恒红修复收尾, 首次 `commands run test.full` 直跑 1.0s rc=4
  (本 shell 自带 `TMPDIR=H:\Temp`), `unset TMPDIR` 后干净重跑。为什么没命中: 评审、包生成、文档
  回填每一步都盯住了, 唯独把「跑 pytest 前先清 TMPDIR」留成失败后的补救动作 —— 与复发 3/5/6/7/8
  完全同款; 前缀必须挂在 `test.full` 命令本身, 不等失败行提示。
- **复发**: 11(2026-11-19)—— 置前焦点修复轮: ①首次聚焦 pytest(`uv run pytest tests/unit/test_utils_windows.py`)
  直跑 rc=4(本 shell 自带 `TMPDIR=C:\Users\…\AppData\Local\Temp`); ②加了前缀跑测试后, **评审前置链
  `commands run ship.gate` 又裸跑**, 闸门内部 test.quick 同 env 再 rc=4 一次(同复发 4/9 的间接调用教训)。
  为什么没命中: AGENTS.md 顶部警告读过, 但没把「跑任何 pytest 前先 `env -u TMPDIR`」和「前缀挂整条
  组合命令开头」当固定动作, 两次都是失败行提示后补的 —— 该动作必须在开工读 AGENTS.md 时就挂上。
- **复发**: 12(2026-11-22)—— 多子代理委派实施轮: 开工后台基线 `commands run test.full` 直跑 rc=4
  (失败行提示后全程改挂 `env -u TMPDIR`, 与复发 11 同款「读档后仍以失败行为触发器」); 复评轮
  `commands run ship.gate` 又一次裸跑 rc=4(与复发 11-② 同点: 闸门内部 test.quick 同 env)。
  为什么没命中: AGENTS.md 与坑档的「闸门/提交同 env」教训已在档, 但开工第一跑仍默认直跑 task id ——
  动作化程度不够, 应把「本 shell 每条含 pytest 的命令(含 ship.gate/ship.commit/test.*)一律带
  `env -u TMPDIR` 前缀」当作开工同步后立即落进会话工作约定的第一步。

### `--basetemp` 换了目录会让 4 条 sidefx 用例**假红**

- **触发**: 想换临时目录跑全量(2026-09-22)。
- **判别**: 换 basetemp 时**必须仍在 `tempfile.gettempdir()`(本机 `H:\Temp`)之下** ——
  `test_sidefx_is_temp_path` 断言 `sidefx.is_temp_path(tmp_path)`,
  挪到 `C:\Users\...\AppData\Local\Temp` 会挂 4 条
  (`is_temp_path` / `policy_allows_known_effects` / `recorder_installed_and_records` /
  `rmtree_dir_fd_entries_not_flagged`)+ 1 条 ERROR, **看着像真失败, 实为临时目录搬家的假红**。
- **处置**: 正确姿势 `uv run pytest tests -q --no-cov --basetemp "H:/Temp/<新目录>"` → 与基线一致。
- **复发**: 2 —— `--basetemp` 落在 TMPDIR **之外**(如 `R:/Temp/auto-qb/pa_bt`)跑全量再次同形假红
  (为什么没命中: 路由到了 [../../testing/run.md](../../testing/run.md) 却没顺着点开本文件)。
  同日复核: basetemp 落在 `tempfile.gettempdir()` **之内**即不假红
  (`--basetemp=R:/Temp/auto-qb/tests/bt` 实测越界 0 条、守卫全绿)。

### 测试基线的临时目录与覆盖率文件必须落在仓库外, 且 basetemp 目录本身必须**不存在**

- **触发**: 跑带覆盖率的全量。
- **判别**: 四条机制 ——
  · `--basetemp` 指到**仓库内** ⇒ 仓内删除被判越界(**5 failed + 1 error**, 是环境口径差异不是回归)。
  · 默认 basetemp 下收尾批量删 `%TEMP%\pytest-of-*` 会撞删除拦截层 ⇒ **点号全过却打不出汇总行**
    (退出码 1, 像失败)。
  · `COVERAGE_FILE` 留在仓库根 ⇒ coverage 开跑时先擦它, 删除同样被拦 ⇒ **开跑 1 秒即退出**。
  · 复用**已存在**的 basetemp ⇒ pytest 开跑前 `rm_rf` 会拉起回收站助手进程, 被记成越界 `POPEN`。
- **处置**: 写法 `COVERAGE_FILE=H:/Temp/aqb.coverage uv run pytest tests -q --basetemp=H:/Temp/<全新目录>`
  (**须在 `tempfile.gettempdir()` 之下**)。

## 规程单点

- 「直接跑全量 / 不比挑子集」、`| tail -N` 禁用口径的单点在 [../../testing/run.md](../../testing/run.md)「环境纪律」; 并发假耗时见 [perf-measurement.md](perf-measurement.md)。

> 已外迁: 全量 pytest 报 pytest-current 假红(临时目录污染) → [attachments/26-11-22-tmpdir-env-false-red.md](attachments/26-11-22-tmpdir-env-false-red.md)(26-11-22 cap 清零)

> 「❗工具 shell 的 `TMPDIR` 指向 `H:\Temp`, pytest 会在**会话结束时**崩」条目(2026-09 自举前时代, 手工固定写法已废止)已外迁: [attachments/26-11-08-tmpdir-tool-shell-crash.md](attachments/26-11-08-tmpdir-tool-shell-crash.md)(26-11-08 cap 清零) —— 含「rename 临时根」治本解与复发 11/12。

**❗在工具沙箱内跑全量也会假红**(另案): 沙箱拒写 `R:\Temp` ⇒ `TMPDIR` 等于没设 ⇒ 回落 `H:\Temp` 收尾崩 ——
点号全过也判红, 关沙箱即消失。已拆至 [sandbox-full-run.md](sandbox-full-run.md)(2026-09-26, 本文件超 cap 拆分)。

> 已外迁: 约定盘缺席/不可见致 TMPDIR 回落、临时目录隔离用例假红 → [attachments/26-11-22-tmpdir-env-false-red.md](attachments/26-11-22-tmpdir-env-false-red.md)(26-11-22 cap 清零)
