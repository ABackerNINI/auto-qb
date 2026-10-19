# test-linux-ci-parity

> 摘要: 修 GitHub Actions(ubuntu-latest)三条红 —— relocate_mod 空文件表把 save_path(目录)当代表文件探测(POSIX 目录 nlink≥2 → IndexError, Windows nlink=1 走不到) + guardian 进程表分派用例按 Windows 写死; 补回归守阵 + 平台中立改写, Windows 侧全量除既有 traffic 墙钟相关失败外全绿
> 最后活动: 2026-10-20 00:03

**R0(2026-10-20 00:03):** 开工同步快进 `dd4bccb8→80bdf3c3`(44 笔)。用户贴 GitHub Actions 红(ubuntu-latest, 3 条 FAILED + 覆盖率门槛未达), 指令「修复 github 报错, 覆盖率问题先不用管」。三条失败全部**只在 Linux 显形**:

1. `test_exec_reject_and_pause_failure` / `test_relocate_module_branch_extras` —— `relocate_mod._group_facts` 在空文件表(读不到文件列表)时 `first_native = save_path`, 随后 `os.lstat` 得到**目录**的 stat, `st_nlink` 在 POSIX 上恒 ≥ 2(2 + 子目录数) ⇒ 进入硬链接分支落到 `names[0]` → `IndexError`。本机实测: Windows 目录 `st_nlink = 1`、普通文件 = 1 —— 同一条分支在 Windows **永远走不到**, 所以本机全绿、CI 全红。
2. `test_guardian_process_names_parsing` —— 用例只 mock `subprocess.run`, 就断言 `_qb_process_names()` 返回 tasklist 结果; 而该函数是**跨平台分派**(`nt` → tasklist / `/proc` → comm / 其它 POSIX → `ps`), 在 Linux 上走 `/proc` 拿到真机进程名。

**判据(定责):** `_qb_process_names` 的三支设计本身正确(`_names_from_proc`/`_names_from_ps` 早已存在), 错的是用例把平台写死; `_group_facts` 那段是**生产代码的语义缺口** —— 空文件表没有「代表文件」, 不该拿目录顶替。

**处置:**

- `src/auto_qb/core/modules/relocate_mod.py` —— 代表文件探测整段收进 `if names:`(空表不探测), 冲突/空间/同卷/能力探测零改动; 空表仍由 `evaluate_group` 按「文件列表为空, 无法判定内容布局」拒绝, **对外行为不变**。
- `tests/test_relocate_paths.py` —— 新增 `test_precheck_empty_file_table_skips_representative_probe`: 给 `os.lstat` 装探针记录调用路径, 断言空表时 `save_path` 一次都没被探测; **红绿双验**(撤掉源码修复该条即红, 复原即绿)。平台中立改写 `test_guardian_process_names_parsing`: 先验 tasklist 解析本体, 再验 `ps` 与 `/proc` 两支解析, 最后用三条来源替身验**分派**(按 `os.name` + `/proc` 现查判据)与异常吞噬。docstring「## 测试计划」清单同步两条。
- 未改任何测试断言去迁就实现, 未删/跳过任何用例。

**验证:**

- Windows: `test.one -- tests/test_relocate_paths.py` 该文件全绿(含新增条); 全量 `test.full` 仅 1 条**既有**失败 —— `test_api_traffic_qb_global_24h_reads_only_involved_day_files`(隔离单跑同样红; 同步的 44 笔未触碰 traffic 四文件; 上一基线切片同一份代码全绿 ⇒ 随本地墙钟翻转), 与本轮改动无涉。数字见 `commands run kb.baseline`。
- Linux 侧: 本机**无 Docker / 无 WSL**, `commands run test.linux` 跑不了 ⇒ 用脚本模拟 POSIX 分派(临时把 `os.name="posix"` + `isdir` 替身)实跑, 三支选路与「读不到 → 空」逐条通过; `IndexError` 那条由新增守阵的探针在 Windows 上覆盖(撤修复即红)。真值仍以 GitHub Actions 复跑为准。

**边界(未做):** traffic 24h 窗那条既有失败未修(不在用户给的 CI 日志里, 且墙钟相关) —— 是否另起一轮待用户定夺; 覆盖率门槛按用户指令不处理; 本轮止于代码与验证。
