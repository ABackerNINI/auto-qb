# 3625 passed + 2 skipped(根, 覆盖率 98%) —— 免重启整组迁移 P0 能力探测后全量基线

> 摘要: 免重启整组迁移 P0 能力探测后全量基线
> 基线时间: 2026-10-18 19:40
**Refs:** memory-bank/tasks/26-10-18-backend-group-relocate-restart-free.md

## 验收数字

`commands run test.full` 实测输出誊写(Windows 本机, 8 worker):

```text
TOTAL                                                18832    284   6302    200    98%
3625 passed, 2 skipped in 128.47s (0:02:08)
```

列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 / 覆盖率(覆盖率列按 coverage 输出取整)。

口径注记:

- 本轮新增 `src/auto_qb/infra/alias_fs.py`(486 语句 / 156 分支)与 `tests/test_alias_fs.py`(35 条),
  覆盖率持平量级 —— 新模块未覆盖行集中在**另一个平台的分支**(POSIX 专有 / Windows 专有),
  单平台跑必然留一侧, 两平台合并才齐。
- 2 skipped 是本机平台不满足的既有用例, 与本轮无关。

## 本改动面

- 新增 `src/auto_qb/infra/alias_fs.py`: 链接能力探测(真建真删) + 链接原语 + §3.3 能力矩阵纯函数。
- 新增 `tests/test_alias_fs.py`: 35 条守阵(探测四步、1314 二义性、形态阶梯、七行矩阵、
  WSL-on-NTFS 反例、挂载表解析、链接原语非递归删除、缓存与降级)。
- 未改任何既有源文件(`utils.is_*` 平台单点照用; 平台判定静态守阵仍绿)。
- 证据(不入库): `tmp-analysis/relocate-e2e/p0-windows.json`(Windows 两块盘)、
  `p0-wsl.txt`(WSL POSIX 分支 + `/mnt/d` 反例)。
