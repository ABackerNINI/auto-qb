# 26-10-04-test-ci-platform — 修 Linux CI 平台差异连红(覆盖率提升轮的 Windows-only 用例)

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04 05:53
**Summary:** 用户给 `R:\Download\test error.txt`(GitHub Actions `ubuntu-latest` 上 `10 failed, 2430 passed, 6 skipped`)要求修复。经 `gh api` 反查运行记录定位: 最后一次绿是 `41aa9f00`(2026-10-02 00:06), 其后**全红** —— 元凶是覆盖率提升轮(计划 `26-10-01-2157`, 提交 `f6c3f239`/`29f1841a`/`1c237504`/`21b8db24`), 那轮**只动 tests/ 且只在 Windows 侧验收**, 新增的 Windows 分支用例在 POSIX 上必红(该档案 Summary 自记的「Linux 侧待补」正是缺口)。四类根因: `ctypes.windll`/`WINFUNCTYPE` POSIX 不存在 / `winreg` Windows 专属 / `os.path` 是 posixpath(反斜杠不当分隔符) / 真值断言写死盘符。**生产代码一行未改**(按 pitfalls/testing/patching.md「排除环境之前不要动 src/」), 只把 4 个测试文件改成两平台同跑; 另把"手拼 docker 命令复现 Linux"收录为 **`commands run test.linux`**(脚本版, 避 cmd.exe 引号地狱)。两侧实测: **Linux 容器 2440 passed + 6 skipped / 覆盖率 98.69%**(修前 10 failed / 98.04%), **Windows `test.full` 2442 passed + 4 skipped / 99%**。

**Topics:** test-ci-platform

**Refs:** memory-bank/pitfalls/testing/patching.md, memory-bank/testing/baselines/26-10-04-0553-test-ci-platform.md, memory-bank/tasks/26-10-01-test-coverage-uplift.md

> 背景关联(不进机器认领链): 本任务是**覆盖率提升轮的后遗症清偿** —— 上游档案 `26-10-01-test-coverage-uplift.md`(已 Done)的 Summary 末句写着「基线切片 P0/P1/P2 各一份 (Linux 侧待补)」, 缺口没补, CI 便一直红着。

## 原始请求

用户 (2026-10-04): 「修复 GITHUB ACTION 报错: `R:\Download\test error.txt`」。文件内容为 CI 的 pytest 失败摘要 —— 10 条 FAILED 集中在 `test_utils`(5)、`test_tray`(3)、`test_ui`(1)、`test_expr_eval`(1), 末行 `10 failed, 2430 passed, 6 skipped in 56.69s`。

## 思考过程与决策

- **先反查"什么时候开始红的"而不是逐条猜**: `gh` 未装, 用 GitHub REST(`/actions/runs`)查到 100 条里 45 绿, 最后一次绿 = `41aa9f00`(2026-10-02 00:06), 其后全红; `git log 41aa9f00..HEAD -- tests/` 一眼锁定元凶是覆盖率提升轮。**先定位引入点再看单条失败**, 省掉对 10 条逐条归因。
- **决定性事实(实测, 不是推断)**: 在 Linux 容器里跑全量 —— 修前 **10 failed / 覆盖率 98.04%**(门槛 98%, 只余 0.04%)。⇒ **"跳过 Windows 用例"这条看似最省事的路走不通**: 跳过会让 Windows 专属行在 Linux 上彻底不覆盖, 覆盖率跌破 98%, CI 照样红。所以必须让用例**真的跑起来**, 而不是 skip。
- **只动 tests/, 一行 src/ 都不改**: 三条独立理由 —— ①pitfalls/testing/patching.md 明文「判据: 单跑通过 + 全量失败 ⇒ 先查环境能力, **排除环境之前不要动 `src/`**(生产代码都是对的)」; ②生产入口(`_win_user32`/`_win_shell_open`)靠 `is_windows()` 早退**本就是正确设计**, 是被测对象不是缺陷; ③AGENTS.md 黄金法则 6「范围守恒」。
- **关键探测: `ctypes.wintypes` 在 Linux 上其实可导入**(容器实测), 只有 `windll`/`WINFUNCTYPE`/`winreg` 缺 ⇒ 补门面的成本比预想低得多, "让用例真跑"这条路才可行。
- **四类根因与各自修法**(按"最小且平台无关"排序):
  1. `ctypes.windll` / `ctypes.WINFUNCTYPE` POSIX 不存在 → 新增 `_shim_posix_ctypes(monkeypatch)`: 用 `hasattr` 判缺才装, **Windows 上不装**(走真门面, 行为与改动前逐字一致); `WINFUNCTYPE` 假实现 = `lambda *a: (lambda f: f)`(假 user32 下真实调用约定无意义)。
  2. `winreg` 是 Windows 专属模块 → `_winreg_or_stub(monkeypatch)`: 真模块取不到就 `setitem(sys.modules, "winreg", 替身)`(既有处置形态)。**踩到一处**: 替身必须给 `CreateKeyEx`/`OpenKey`/`DeleteValue` 留**占位实现** —— `monkeypatch.setattr` 默认要求属性已存在, 否则 AttributeError(首跑即红在这)。
  3. `os.path` 在 POSIX 是 `posixpath`, 反斜杠不当分隔符 → `_win_reuse_title_candidates` 的 `"R:\\"` 盘根断言必红。按 pitfalls/testing/patching.md ④「固定语义」把 **utils 模块内的 `os` 换成 `ntpath`**(纯字符串模块, 两平台同语义); 不碰全局 `os.path`(会误伤 pytest 收尾)。
  4. 真值断言写死 Windows 盘符(`exists("C:/")`) → 改用 `tmp_path` 这个**跨平台真实存在**的目录。
  - 另两条机械补丁: `test_tray._patch_windll` 的 `setattr` 加 `raising=False`(POSIX 无 windll 属性); `test_autostart_error_paths` 三段改 `monkeypatch.context()`(旧写法靠 `monkeypatch.undo()` 清场, 会把平台 patch 与 winreg 替身一并撤掉, 后续段落没法在 POSIX 上跑)。
- **验收口径: 两侧都测**(baseline.md 常驻警告「只测一侧就更新会立刻产生漂移」)。Linux 侧本机 WSL 被安全策略拦(patching.md 已记), 改用 **Docker** 起 Linux 容器跑全量。

## 实现计划

- 探测: Docker 容器内确认 `ctypes.wintypes` 可导入、`windll`/`WINFUNCTYPE`/`winreg` 缺失。
- 修 `tests/test_utils.py`: `_shim_posix_ctypes` + 4 处用例补平台/门面 + `_win_reuse_title_candidates` 用例固定 `ntpath` + 头部「测试计划」清单同步。
- 修 `tests/test_tray.py`: `_patch_windll` 加 `raising=False` + docstring 说明。
- 修 `tests/test_ui.py`: `_winreg_or_stub` + `test_autostart_error_paths` 三段 `monkeypatch.context()`。
- 修 `tests/test_expr_eval.py`: `exists` 真值改 `tmp_path`。
- 验证: Linux 容器跑全量(目标 0 failed + 覆盖率 ≥98%) + Windows `commands run test.full`。
- 收尾: `pitfalls/testing/patching.md` 记「复发 +1」+ Docker 复现配方; `test_memory_bank.py` 守卫; 基线切片 + 本档案 + activeContext 切片。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 反查引入点(何时开始红) | ✅ 完成 | `gh api` 定位最后绿 `41aa9f00`; `git log` 锁定覆盖率提升轮 |
| Linux 容器复现 + 量出覆盖率余量 | ✅ 完成 | 修前 10 failed / **98.04%**(门槛 98%) ⇒ 排除"跳过"方案 |
| `test_utils.py` 平台门面 + ntpath | ✅ 完成 | `_shim_posix_ctypes` + 4 用例 + `import ntpath` + 清单同步 |
| `test_tray.py` `raising=False` | ✅ 完成 | `_patch_windll` |
| `test_ui.py` winreg 替身 + `context()` | ✅ 完成 | `_winreg_or_stub`(含占位实现) + 三段重排 |
| `test_expr_eval.py` `exists` 真值 | ✅ 完成 | 改用 `tmp_path` |
| Linux 侧全量验证 | ✅ 完成 | **2440 passed + 6 skipped / 98.69%** |
| Windows 侧全量验证 | ✅ 完成 | `commands run test.full` **2442 passed + 4 skipped / 99%** |
| 坑档回写(复发 +1 + Docker 配方) | ✅ 完成 | `pitfalls/testing/patching.md` |
| memory-bank 守卫 | ✅ 完成 | `test_memory_bank.py` 31 passed(三行头未变, 无需重跑 kb.index) |
| 基线切片 + activeContext 切片 + 本档案 | ✅ 完成 | 见 Refs |
| 收录 `test.linux` task | ✅ 完成 | 手拼 docker 命令跑了 7 次且踩坑 2 次 ⇒ 按 commands skill 收录协议进 `test` 包(`scripts/linux_ci.py`, 脚本版避 cmd.exe 引号地狱); 实测 `commands run test.linux` = 2440 passed + 6 skipped / 98.69% |
| 提交 | ⬜ 待用户指令 | 用户未说「提交」, 按请求边界不自行 commit/push |

## 进度日志

- **2026-10-04 05:38** 开工。读 `R:\Download\test error.txt`(10 条 FAILED), 列 `.github/workflows/ci.yml`(`ubuntu-latest`, py3.12/3.13, `uv run pytest tests -q`, `--cov-fail-under=98` 在 pytest.ini)。用 GitHub REST 反查 100 条运行: 45 绿, 最后绿 = `41aa9f00`(2026-10-02 00:06); `git log 41aa9f00..HEAD -- tests/` → 元凶 = 覆盖率提升轮 4 笔提交。
- **2026-10-04 05:41** 会话开局 `commands run my-commit-flow.sync` → `同步成功 30b887e9`(远端一笔 `30b887e9` 流量页签修复, 不触 tests/)。
- **2026-10-04 05:42** Linux 容器复现(修前): `10 failed, 2430 passed, 6 skipped`, **覆盖率 98.04%**(14495 语句 / 240 未覆盖)⇒ 判定"跳过"方案会让覆盖率跌破 98%, 必须让用例真跑。容器实测: `ctypes.wintypes` **可导入**, `windll`/`WINFUNCTYPE`/`winreg` 缺失。
  - ⚠ 同轮踩坑: 首次复现时 `rm -rf /work/.git` 导致 `test_commands_engine` 多出 5 条**假红**(`_config.find_root()` 靠向上找 `.git`) —— 已写进坑档的 Docker 配方, 复现须保留 `.git`。
- **2026-10-04 05:45** 落地 4 个测试文件(见「实现计划」)。Windows 侧先跑受影响 4 文件: **183 passed**。
- **2026-10-04 05:48** Linux 容器复跑: 1 failed(`test_autostart_error_paths`, 替身缺占位属性撞 monkeypatch"属性必须已存在")→ 补 `CreateKeyEx`/`OpenKey`/`DeleteValue` 占位 → 4 文件 **181 passed + 2 skipped**。
- **2026-10-04 05:51** Linux 容器全量: **2440 passed + 6 skipped / 覆盖率 98.69%**(修前 10 failed / 98.04%)。
- **2026-10-04 05:52** Windows `commands run test.full`: **2442 passed + 4 skipped / 99%**(133 未覆盖, 40.63s)。`test_memory_bank.py` 31 passed。
- **2026-10-04 05:53** 收尾: `pitfalls/testing/patching.md` 加「复发 +1」(含"为什么没命中"与四类根因处置) + 「Docker 等价复现」配方; 基线切片 + activeContext 切片 + 本档案。未提交(等用户「提交」)。
- **2026-10-04 06:0x** 提交轮, 闸门拦下两处并顺带收了条命令:
  - `check_command_drift` 判红 —— 基线切片里**手抄**了 `uv run pytest tests -q` / `uv sync`(均已收录, 应写 task id)。
  - 处置不只是在文档里改字: 手拼 docker 命令本会话跑了 **7 次**且**踩坑 2 次**(删 `/work/.git` 多 5 条假红 / 没删宿主 `.venv`), 正合 commands skill「难拼 → 自己 add」的收录条件 ⇒ 收录为 **`commands run test.linux`**(`[pack].scripts_dir = "scripts"` + `.commands/test/scripts/linux_ci.py`)。**用脚本而非一行 `run`**: 命令里全是 `&&`/`;`/`|` 与多层引号, 引擎在 Windows 上走 cmd.exe, 引号地狱必踩; 脚本用 argv 列表调 docker, 零引号问题, 且 `<root>` 由 `Path(__file__).parents[3]` 现算(跨 clone 不写死)。实测 `commands run test.linux` = **2440 passed + 6 skipped / 98.69%**。
  - 同步: 基线切片改引 task id; 坑档的 Docker 段改以 task id 为单点、只留三个必踩点(命令本体不再抄)。
  - **踩到的机检两条**(记进 `.workbuddy-ai` 日志): ①新建档案后**必须先 `kb.index`** 否则 `test_memory_bank` 4 条 + `test_docs_forms` 1 条红; ②**认领链必须双向** —— 档案 `**Refs:**` 指向的每个件都要反向 `**Refs:**` 回来(坑档 / 基线切片各加一行, 上游档案 Refs 追加), 否则 `test_docs_forms::test_claim_chain_is_bidirectional` 红。
  - 另: `doc` 字段的相对路径是**相对包目录**解析的(不是仓库根)—— 写 `../../../` 会 STOP。
  - 另: **新脚本必须自认 `--safety` → `action-without-args`**(判据单点 `_pipeline._safe_files`)。首版漏了,
    闸门虽仍把它摘掉(探针 10s 超时 → 按不安全), 但**每次提交白等 10s 且白起一次 `docker run`** —— 补上后探针即时返回。
