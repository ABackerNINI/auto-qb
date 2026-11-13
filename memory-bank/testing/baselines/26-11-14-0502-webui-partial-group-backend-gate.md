# 6106 —— rename-fs 部分组闸基线

> 摘要: rename-fs 端点部分组闸门(issue 26-11-12-0807): test.full 6104+2 覆盖 99%
> 基线时间: 2026-11-14 05:02

## 验收数字

`commands run test.full` 实测(Windows 宿主, issue 26-11-12-0807 修复收尾, 基线时间即建件时点):

- 汇总行: `6104 passed, 2 skipped in 207.68s (0:03:27)`(文案 nit 修复后复跑, 与首轮 174.57s 同数)
- TOTAL 表: `27119 stmts / 65 miss / 9482 branch / 69 miss / 99%`
- 对照同宿主上一切片(26-11-14-0348, 6102+2): +2 passed —— 干净可归属 +1(本批新增守阵
  test_rename_fs_partial_group_hard_rejected); 余 +1 未逐笔归因(0348 基线树到本次快进后
  tip 隔 11 笔远端提交, `git diff` 显示测试函数零新增、仅收编改道, 归因存疑如实记不硬凑);
  skipped 组 2 与同宿主一致; dispatch/longtail 两既有用例是收编改道不加数
- 闸门判定面纯 store 快照逻辑(拦截在 qB 调用之前), 桩可验, 未走真机轨

## 本改动面

- `src/auto_qb/webui/commands_torrents.py` — `_cmd_rename_fs` 加部分组闸: 谓词复用 0823 的
  `_partial_groups_of([hash], [])`, 命中多成员在册组 raise ValueError fail-closed 硬拒
  (回执经 consume_commands error 分支带出); 单成员组/未归组放行。
- `tests/test_web_commands_bulk.py` — 新增 `test_rename_fs_partial_group_hard_rejected`
  (两形态硬拒 + 放行面三例) + docstring 测试计划行。
- `tests/test_web_commands_dispatch.py` — `test_drain_web_commands_torrent_write_actions`
  收编: `store.remove_torrent("HB")` 缩组进放行面(rename_fs c12 参数透传守阵不变)。
- `tests/test_web_longtail_commands.py` — `test_web_commands_rename_fs_folder_branch`
  同款收编 + 计划行更新。
- 回写件: issue 26-11-12-0807 翻 Done + 复验行/修复后补充; 档案 26-11-12-webui-partial-group-backend-gate.md
  追加 S7 行 + Refs + Summary; architecture/webui.md 部分组段补 rename-fs 端点闸条目。
