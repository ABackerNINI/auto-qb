# 5140 passed + 10 skipped(根) —— 整组迁移 confirm 回路补齐(前端二次确认+confirm=true 重发)

> 摘要: 整组迁移 confirm 回路补齐(前端二次确认+confirm=true 重发)
> 基线时间: 2026-11-04 07:57
**Refs:**

## 验收数字

`commands run test.full`(Windows, 并行 `-n 4`, 166.92s / 0:02:46):

| 指标 | 实测 |
| --- | --- |
| 汇总 | 5140 passed, 10 skipped |
| TOTAL | 23943 语句 / 226 未覆盖 / 8186 分支 / 168 partial |
| 覆盖率 | 99% |

口径注记: 单次采样快照(耗时区间/中位口径见 [baseline.md](../baseline.md))。

## 本改动面

- `src/auto_qb/webui/static/shared/drawer.js`: 新增 `_relocateConfirmCount` / `_relocateConfirmRows` /
  `_relocateConfirmGate` / `_relocateDoneText`; `_editPost` / `_bulkEditPost` 在 `r.ok` 且
  `truth.summary.confirm > 0` 时返回 `"confirm"` 且不弹成功; `submitMoveDialog` 先收设定位置框
  (两层全屏遮罩同 z-index) -> 二次确认框(形态/来源/目标/未来种子/原因/提示) -> 带 `confirm=true`
  重发; 成功 toast 改按真实回执计数(`已发起/跳过/拒绝/待确认`)。
- `tests/test_web_relocate.py`: +`test_relocate_confirm_loop_wired_in_move_dialog`(前端静态守阵) /
  `test_web_relocate_confirm_passthrough_routes`(路由 confirm 透传契约), 并同步文件头测试计划清单。
- `tests/test_webui_optimistic_rename_alt.py`: node 探针桩补 `_relocateDoneText`(`_editPost` 成功
  toast 新增的回执文案单点依赖)。
- `memory-bank/issues/26-11-04-0734-bug-webui-relocate-confirm-unwired.html`: 置 Done(附验证数据)。
