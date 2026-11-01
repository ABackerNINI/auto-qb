# 4805 passed + 2 skipped; TOTAL 22482 stmts / miss 164 / branch 7708 / partial 134 / 99% —— 修复 mutants 工具链两 issue(deselect 守阵 + verify 通道)后全量测试基线

> 摘要: 修复 mutants 工具链两 issue(deselect 守阵 + verify 通道)后全量测试基线
> 基线时间: 2026-11-02 02:09
**Refs:** memory-bank/issues/26-10-31-1539-bug-mutation-tooling-deselect-guards.html, memory-bank/issues/26-10-31-1539-bug-mutation-tooling-verify-channel.html

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮修复的**未提交工作树**(HEAD `bd6c8a32` + 本轮改动: `.commands/mutants/scripts/{set_conf,mutants,test_mutants}.py`、`.commands/mutants/references/why.md`、`.agents/skills/mutation-testing/SKILL.md` 及两条 issue 回写件)
- `commands run test.full` 实测(wrapper 墙时 188.3s, 2026-11-02 02:11, Windows 本机):
  - 汇总行: `4805 passed, 2 skipped in 185.97s (0:03:05)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- 包内脚本测试: `commands run test.pkg` **235 passed, 14 subtests passed**(含本轮新增 `DeselectTableTest` / `DoneIdsTest` / `SuiteCmdDeselectTest` / `EnsureMirrorTest`)
- **环境 / 工具**: Windows 本机(win32)· Python 3.13 · pytest-xdist 8 workers · `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)
- **口径注记**: 首轮全量跑发生在 `kb.index` 重建前的中间态 —— `test_gen_all_check_is_green` 报 `issues/_index.md` / `attachments/_archive.md` 漂移, 且并行分布下覆盖率为 98.97% 差门槛; `kb.index` 重建后复跑即全绿(4805 passed / 99%)。属测量时序, 非代码面缺陷。

## 本改动面

- `.commands/mutants/scripts/set_conf.py`: ①`DEFAULT_DESELECT` 表前补「新增/改名文本层守阵必须同步改表」的首要纪律注释; ②新增 `FLAKY_DESELECT`(6 条已实证 node id: hr_discovery 3 · web_views_reload 2 · commands_engine 1); ③`--deselect` 默认改为 `DEFAULT_DESELECT + FLAKY_DESELECT`(显式传参仍可覆盖/清空); ④docstring 同步。
- `.commands/mutants/scripts/mutants.py`: ①`_ensure_mirror` 先探 WSL 可达性(不可达即 Fail 且不 clone), 再按「目录不存在 / 目录在但 `.git` 缺失 / 正常」三态处理; ②`cmd_run` 清理前警告注册表失效, 基线失败行点名 `DEFAULT_DESELECT`; ③`cmd_verify` 开跑前预检 `mutants/**/*.meta` 注册表; ④新增纯函数 `_done_ids`(APPLY_FAIL/TIMEOUT/FLAKY/UNKNOWN 不进 done)并用于续跑; ⑤收尾未判定提示补 APPLY_FAIL; ⑥`_suite_cmd` 自动从 `FLAKY_DESELECT` 派生 `--deselect`。
- `.commands/mutants/scripts/test_mutants.py`: 新增 `DeselectTableTest`(两张表条目对差守阵) / `DoneIdsTest` / `SuiteCmdDeselectTest` / `EnsureMirrorTest`(WSL 不可达 / `.git` 缺失绝不 clone), 文件头「## 测试计划」同步。
- `.commands/mutants/references/why.md`: 新增「S4 手工通道: dump diff → 整文件 post-image」小节 + 排障表两行(APPLY_FAIL 注册表失效 / 不再自动跳过)。
- `.agents/skills/mutation-testing/SKILL.md`: 硬约束 4 补同步核表与 flaky 表说明; 坑段加 S4 手工通道指针。
- 知识库回写: 两条 issue 各自 In Progress→Done + 复验/修复后补充 + 状态日志; 本切片与 `kb.index` 重建。
- 零 `src/` 改动; `config.yml` / `auto-qb-data/` 红线未触碰。
