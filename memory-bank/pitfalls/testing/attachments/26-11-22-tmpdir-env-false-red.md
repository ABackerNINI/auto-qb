# tmpdir · 临时目录环境假红(PermissionError 污染 / 约定盘缺席回落)

> 摘要: 全量 pytest 报 pytest-current 是临时目录被污染、约定盘缺席时 TMPDIR 静默回落致隔离用例假红 —— 两则环境面假红的判别与处置。
> 触发: 跑全量, 查假红, pytest-current, PermissionError, 约定盘缺席, R 盘不可见, TMPDIR 回落, 快照守阵

### 全量 pytest 报 `PermissionError: … pytest-current` 是临时目录被污染, **不是测试红**

- **触发**: 全量 pytest 打完点号后报错(2026-09-21)。
- **判别**: 删除拦截层让 pytest 的 `garbage-*` 目录**删不掉、越堆越多**(实测 **283 个**); 下次运行
  `cleanup_dead_symlinks` 去 `resolve()` 已成死链的 `pytest-of-<user>/pytest-current` ⇒
  `PermissionError [WinError 5]`, **连汇总行都不打印**(极易误判成"测试全崩")。
- **处置**: **不要去删那些目录**(同样会被拦), 给 pytest 指一个全新临时根即可(现口径更简单:
  直接走 `commands run test.*`, `TMPDIR` 已内置)。

### 约定盘缺席/不可见 → `TMPDIR` 静默回落 `%TEMP%`, 依赖临时目录隔离的用例假红(2026-10-16 实测)

- **触发**: `set "TMPDIR=R:/Temp/auto-qb/tests" && pytest …` 照常执行, 但 R 盘在会话内**不存在/不可见**
  (`dir R:\` 报 "The system cannot find the drive specified", `Test-Path R:\` False) —— `set` 本身不报错,
  Python `tempfile` 校验候选目录失败后**静默回落** `%TEMP%`(`C:\Users\…\AppData\Local\Temp`)。
- **判别**: ①一查落点 `python -c "import tempfile; print(tempfile.gettempdir())"`, 一查盘 `dir R:\`;
  ②症状 = `test.pkg` 里 my-commit-flow 快照守阵数条红、报错路径落在 `%TEMP%` —— `_snapshot._find_repo_root`
  从临时目录上溯命中**家目录杂散 `.git`**(期望 `None` 实得家目录), 以及 `-n 8` 并行下 `_snap_dirs()`
  全局集合比较跨 worker 互见临时快照目录(串行只剩前者)。**先查临时目录再怀疑代码回归**。
- **处置**: 恢复 R 盘(TMPDIR 目标可建目录)即可消掉「家目录 .git」那条; 集合比较的跨 worker 竞态与盘无关,
  属测试设计面(识别与无关性证据见基线切片 [../../testing/baselines/26-10-16-1551-ship-commit-omitted-note.md](../../../testing/baselines/attachments/26-10-16-1551-ship-commit-omitted-note.md)「包内脚本测试」节)。
  沙箱拒写 R 盘的另一种「TMPDIR 等于没设」见 [sandbox-full-run.md](../sandbox-full-run.md)。
  （同日收口: ① 家目录空 `.git` 由机主移除; ② 竞态已按「用例私有临时根」修复 —— `.commands/my-commit-flow/scripts/test_snapshot.py::_private_tmp`(子进程 TMPDIR 一并隔离), 红绿双验通过。）
