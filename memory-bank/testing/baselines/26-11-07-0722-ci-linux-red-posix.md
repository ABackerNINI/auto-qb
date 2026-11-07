# 5609 —— GitHub Linux CI 三条红修复后基线

> 摘要: GitHub Linux CI 三条红修复后基线(alias_kind_of 真目录 + 两条桩形态)
> 基线时间: 2026-11-07 07:22

## 验收数字

`commands run test.full` 实测 (2026-11-07 08:12, 145.1s):

```text
TOTAL                                                25499     27   8796     34    99%
5609 passed, 13 skipped, 1 warning
```

覆盖率门槛 99.5 过(`commands run test.full` 退出码 0; 精确百分比以该命令输出为准, 此处不另抄)。
相对上一切片(+130 用例)的增量来自远端合流的多笔提交; 本批对 `tests/` 净 +1 例(守阵
`test_alias_kind_of_real_dir_is_none`), 另有 3 条既有用例补了 `_SYMLINK_REQUIRED` 准入 —— skipped
因此由 10 升到 13(见下段)。

**13 skipped 里本批新增的 3 条是宿主能力面**(Linux CI 侧无此面, 照常真跑): 三条最终都要真建符号链接
(来路各不相同 —— 显式 `KIND_SYMLINK` / 传 `KIND_HARDLINK` 由跨卷回落成 symlink / 不传 kind 靠目标类型
推断), 本机 Windows 缺 `SeCreateSymbolicLinkPrivilege`(未开开发者模式), `os.symlink` 抛
`WinError 1314` —— `test_retarget_alias_missing_link_rebuilds` /
`_hardlink_cross_volume_falls_back_to_symlink` / `_infers_kind_when_link_and_kind_absent`。改前这三条
是**红**的、并因此拦住提交闸门(`ship.commit` 的 test.quick 闸), 按仓库既有约定(file-conventions
「测试不得依赖宿主环境能力」, 与 `test_alias_fs` 里 `_SYMLINK_REQUIRED` 同族)改为 skip 而非 fail;
有建链能力的环境(管理员/开发者模式/Linux)照常真实执行, 覆盖不缩水。
另一面: 本批修的两条 relocate 预检用例改前在本机也是红的(红在别处 —— 桩连带打掉 `same_volume`,
形态闸按跨卷拒绝), 改后转绿。

包内脚本测试 `commands run test.pkg`: 360 passed, 15 subtests (2026-11-07 实测; 本批零改动)。

## 本改动面

- `src/auto_qb/infra/alias_fs.py`: `alias_kind_of` 在 `S_ISLNK` 之后、nlink 判据之前加 `S_ISDIR -> None`
  —— POSIX 目录 `st_nlink = 2 + 子目录数`(恒 > 1), 旧写法把真目录判成 `KIND_HARDLINK`, 使
  `retarget_alias`「链接位被非空真目录占据」的拒绝分支前置条件(`existing is None`)不成立, 拿目录去
  `os.unlink` 抛 `IsADirectoryError`。
- `tests/test_alias_fs.py`: ① `test_alias_points_to_hardlink_stat_failure_is_false` 夹具改到装 `os.stat`
  桩**之前**(POSIX 上 `posixpath.isdir` 走被桩的 stat, `exist_ok` 失效 -> 建夹具即 `FileExistsError`);
  ② 新增守阵 `test_alias_kind_of_real_dir_is_none` 与「测试计划」清单条目; ③ 三条需真建符号链接的重定向
  用例补 `_SYMLINK_REQUIRED`(解锁本机提交闸门, 清单同步标注)。
- `tests/test_web_relocate.py`: 新增测试侧助手 `_stub_bprime_unavailable`(桩打在
  `relocate_proof._bprime_evidence` 判定层, 不桩 `os.stat`)并替换
  `test_relocate_module_same_fs_p3_semantics` / `test_relocate_module_precheck_scandir_and_lstat_degraded`
  里的 `os.stat` 桩 —— POSIX 上 `os.path.exists` 走被桩的 stat, 会把声明文件判成「缺失」并以
  `source_missing` 抢拦, B′ 分支根本走不到(Windows 上 `os.path.exists` 是 C 内建, 桩对它无效, 故本地绿)。
- 坑档: `pitfalls/backend/platform-fs.md` 目录 nlink 条 `复发` +1(新入口 `alias_kind_of`);
  `pitfalls/testing/patching.md` 新增 ⑦「给 `os.stat` 打桩在 Windows 对 `os.path` 判定无效」,
  「本机绿不算绿」判别法补该面为第六类。
- 入池: `issues/26-11-07-0748-bug-relocate-retarget-real-file-unlink`(`retarget_alias` 对「链接位是
  真文件」无保护, 会 unlink 真数据; 本批不修)。
- `_index*.md` 为 `kb.index` 生成物。
