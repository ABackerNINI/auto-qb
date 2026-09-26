# 1673 passed + 1 skipped / 0 failed —— WebUI 长路径打开修复(代码 + 测试 + 知识库)

> 摘要: **代码轮**。新增 8 条用例(`test_utils` 6 / `test_web` 2)、改写 1 条, 净增 +8 collected(1666 → 1674);
> 全绿 0 红, 覆盖率 91%。改动面: `utils.open_path` 加 Windows Shell PIDL 分支(长路径)、`routes/fs.py` 全量前缀化、
> `tests/sidefx.py` 的 LAUNCH 守阵收录新入口。
> 基线时间: 2026-09-26 19:46
> 档案: 26-09-26-webui-long-path-open

- **新增 8 条**: `test_utils.py` 6 —— `test_open_path_windows_long_path_uses_shell_pidl`(长路径走 PIDL,
  绝不触达 `os.startfile`/`explorer`) / `test_open_path_windows_falls_back_to_string_route`(PIDL 失败退回字符串路线) /
  `test_open_path_non_windows_never_calls_shell_pidl`(POSIX 不触达 PIDL, 防守阵假阳性) /
  `test_win_shell_open_non_windows_returns_false` / `test_win_string_open_degrades_long_path_to_ancestor` /
  `test_exists_dir_file_apply_long_path_prefix`; `test_web.py` 2 —— `test_fs_endpoints_route_fs_calls_through_long_path_prefix`
  (三端点路由) / `test_fs_path_helpers_strip_long_path_prefix_before_compare`(前缀归一契约, 纯路径故任何平台都跑)。
- **改写 1 条**: `test_open_path_select_file_per_platform` —— Windows 段原钉 `os.startfile` 直调,
  改为"PIDL 不可用时的兜底"(并补 `_fake_windows` 中和前缀 helper, 理由写在用例 docstring)。
- **实施中被测试抓出真 bug**: `_fs_real` 不剥 `\\?\` 前缀 ⇒ `entry.path` 带前缀、允许根不带 ⇒ 白名单恒 False
  ⇒ 子目录全被过滤(目录树恒空)。修后该用例转绿 —— 本条即那次回归的守阵。
- **真机端到端**(不属 pytest 计数): `LongPathsEnabled=0` 下 `open_path(314 字符目录)` 与
  `open_path(长文件, select=True)` 均正确开窗并指向目标(窗口标题核对 + 截图, 探针已清理)。
- **闸门**: 本次 `test.full` 0 红; 提交 `db0993c` 的自动闸门 10 条全过, ref 三处一致, Gitee 主线已核对
  (`ls-remote` == 本地 HEAD)。

TOTAL 91%(11272 语句 / 816 未覆盖 / 3712 分支 / 332 partial; 本轮机跑 18.5–21.8s, 覆盖率口径见
[../baseline.md](../baseline.md); 语句数较上一条基线 +4, 为 `utils.py` / `fs.py` 本次改动所致)。
