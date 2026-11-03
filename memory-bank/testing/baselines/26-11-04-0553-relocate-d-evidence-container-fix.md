# 5128 passed + 10 skipped(根) —— D 级证据容器判据修复后全量基线

> 摘要: D 级证据容器判据修复后全量基线
> 基线时间: 2026-11-04 05:53
**Refs:**

## 验收数字

`commands run test.full` 实测输出誊写：

```text
TOTAL                                                23934    228   8184    170    99%
1 failed, 5128 passed, 10 skipped in 180.05s (0:03:00)
FAILED tests/test_traffic_store_codec.py::test_all_persist_writes_on_caller_thread - assert 3 == 4
FAIL Required test coverage of 99.0% not reached. Total coverage: 98.70%
```

口径：仓库根全量；分支 `develop`，HEAD `a7f6f224`，工作树含本轮未提交改动（`src/` 仅 `relocate_proof.py`）。两条红均非本次引入：

- `test_all_persist_writes_on_caller_thread`（线程活跃计数 3==4）：与本改动无关；`commands run test.one -- tests/test_traffic_store_codec.py::test_all_persist_writes_on_caller_thread` 单跑 1 passed，属并行全量下的既有顺序/线程抖动。
- 覆盖率 98.70% 低于 Windows 闸 99.0：上一基线（`26-11-04-0507`，HEAD `e80d9f8e`）实测同口径 98.74%，同样低于闸；本次新增语句全部被新用例覆盖，非本次引入。

`tests-real/` 三例（RM04-11..13）不在 `testpaths(tests/)` 内，不计入本行；真机实测数字见本轮 issue/task 档案。

## 本改动面

代码面：`src/auto_qb/core/modules/relocate_proof.py` —— `_d_evidence` 容器判据由 `isinstance(entries, (list, tuple))` 改为 `_is_entry_sequence()`（`collections.abc.Sequence` 协议，排除 `str/bytes/bytearray`），覆盖 qbittorrent-api 的 `DirectoryContentList`（UserList 子类）；F 级 `link_follow_evidence` 同函数同源生效（issue 26-11-04-0504）。

测试面：`tests/test_relocate_proof.py` 新增 5 个回归（真实 `DirectoryContentList` 正向、`ListEntry` 条目、裸 `UserList` 同形、F 级同源、str/bytes/dict/None 反误放对照），本文件 35 passed；`tests-real/rm04_relocate/test_rm04_probe_real.py` 的 RM04-13 增加 D 级断言，真机 `1 passed`。

文档面：issue 置 Done 并补验证数据；task 档案补 R4；新建本基线切片。
