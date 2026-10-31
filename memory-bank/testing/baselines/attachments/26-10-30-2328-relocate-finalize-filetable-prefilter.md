# 4182 passed, 2 skipped in 127.87s; TOTAL 21142/99/7156/101 99% —— relocate 收尾集合预过滤: files API 只发给覆盖分支候选(26-10-30-0616)

> 摘要: relocate 收尾集合预过滤: files API 只发给覆盖分支候选(26-10-30-0616)
> 基线时间: 2026-10-30 23:28
**Refs:** memory-bank/issues/26-10-30-0616-perf-finalize-members-filetable-filter.html

## 验收数字

`commands run test.full` 实测(2026-10-30 23:19, Windows, 修复落盘后):

```
TOTAL                                                21142     99   7156    101    99%
4182 passed, 2 skipped in 127.87s (0:02:07)
```

- **汇总行**: **4182 passed / 2 skipped**, 墙时 **127.87s** 区间口径见 testing/baseline.md「耗时与覆盖率口径」。
- **TOTAL 表**: 语句 **21142** / 未覆盖 **99** / 分支 **7156** / partial **101** / 覆盖率 **99%**。
- **新增守阵**: `test_finalize_scope_candidate_prefilter`(units —— 预过滤条件单点三态) +
  `test_finalize_members_prefilters_file_table`(exec —— 假 rec 计数 files 调用, 断言只有覆盖分支候选被取文件表、逐文件链接 job 全程零调用)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/core/modules/relocate_units.py` | 新增纯函数 `finalize_scope_candidate(job, save_path)` —— finalize_members 覆盖分支条件的前半段(目录别名且 save_path==src)抽成单点, finalize_members 与 _finalize_members 预过滤同源复用; finalize_members 循环改用它(语义逐字等价) |
| `src/auto_qb/core/modules/relocate_mod.py` | `_finalize_members` 取数顺序倒正(26-10-30-0616): mover/job.hashes 直通(root 占位, 判定短路免文件表), 新增候选先按 save_path==src 筛, 只对筛剩者发 files API 算内容根 —— 全库逐条先取文件表再过滤的路径消除 |
| `tests/test_relocate_units.py` | 新增 `test_finalize_scope_candidate_prefilter` + 头部测试计划同步 |
| `tests/test_relocate_exec.py` | 新增 `test_finalize_members_prefilters_file_table` + 头部测试计划同步 |
| `memory-bank/issues/26-10-30-0616-perf-finalize-members-filetable-filter.html` | 认领: Open → In Progress → Done, 复验行 + 修法/验证/测试数字日志 |
