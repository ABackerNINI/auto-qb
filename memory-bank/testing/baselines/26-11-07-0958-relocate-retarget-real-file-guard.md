# 5626 passed + 2 skipped(根) —— retarget_alias 真文件占位保护(issue 26-11-07-0748)收尾基线

> 摘要: retarget_alias 真文件占位保护(收窄式放行 + 评审 minor 修)收尾基线
> 基线时间: 2026-11-07 09:58

## 验收数字

`commands run test.full` 实测 (2026-11-07, 命令整体 130.5s):

```text
TOTAL                                                25505      5   8800     27    99%
5626 passed, 2 skipped, 1 warning in 129.00s (0:02:08)
```

- 差值看上片: `commands run kb.baseline -n 2`。本批新增 4 用例(真文件拒绝三路 + 云占位符标签 + 孪生残名放行两分支);
  另有开工同步自远端带入 1 笔新增测试, 本片数字录于其合流之后。
- POSIX 侧(Linux CI)未本地重测, 随推送由 GitHub CI 验证; 本批改动对 POSIX 的行为差: 重解析标签豁免在
  无 `st_reparse_tag` 平台按 0 处理, 真文件/真目录保护判定与改前一致(0 不属 MOUNT_POINT/SYMLINK)。

## 本改动面

- `src/auto_qb/infra/alias_fs.py`: `retarget_alias` 删旧链接段补真文件占位保护 —— `existing is None` 且
  lstat 非链接(标签豁免只认 MOUNT_POINT/SYMLINK)时, `S_ISREG` 仅当 plan 声明 hardlink 且与新目标同尺寸
  (孪生残名必要特征)才放行删除, 其余一律 RuntimeError 留现场(D20); `S_ISDIR` 沿用原目录支口径。
- `tests/test_alias_fs.py`: +4 用例(拒绝三路 / 云占位符 lstat 桩 / 孪生残名同卷 / 孪生残名跨卷回落),
  文件头测试计划同步 4 条。
- issue `26-11-07-0748` 翻 Done(复验仍复现 + 实际修法与建议①改道说明入正文); 评审 1 条 minor 当场修,
  `review.check` 过检 1/1。
