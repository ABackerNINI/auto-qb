# 5140 passed + 10 skipped(根) —— Web UI 整组迁移 confirm 回路真机验收(RM04-14)

> 摘要: Web UI 整组迁移 confirm 回路真机验收(RM04-14)
> 基线时间: 2026-11-04 08:37
**Refs:** memory-bank/tasks/26-10-18-backend-group-relocate-restart-free.md

## 验收数字

`commands run test.full`(Windows, 并行 `-n 4`, 185.2s / 0:03:05):

| 指标 | 实测 |
| --- | --- |
| 汇总 | 5140 passed, 10 skipped |
| TOTAL | 23946 语句 / 226 未覆盖 / 8188 分支 / 168 partial |
| 覆盖率 | 99% |

口径注记: 单次采样快照(耗时区间/中位口径见 [baseline.md](../baseline.md))。

口径注记(范围外抖动, 本轮不修): 三次全量中的第二次出现 1 条既有假红
`tests/test_qb_capture.py::test_sanitize_all_rewrites_fs_delta_with_same_derivation` —— 夹具用非 hex
假 hash `H1`,`Sanitizer.infohash` 在约 1/16 的随机盐下把 `H1` 映射回自身, 令末行 `"H1" not in stream`
偶发失败; 单文件单跑 5/5 绿、重跑全量绿。与 confirm 回路改动无关(该文件本轮零改动)。

## 本改动面

- `tests-real/rm04_relocate/test_rm04_relocate.py`: 新增 `test_rm04_11_webui_confirm_loop_ui`(真实 Web UI
  点完取消/确认两条路径; 断言首投无「已执行」、确认框 7 要素、`confirm=true` 重发、dst 落地(9 文件
  size+sha1)、src 内容根 junction、日志「迁移发起」「已武装收尾」、job/journal phase=done、B 组零副作用)。
- `tests-real/lib/relocate_confirm_ui.mjs`: 新增 Node/Playwright UI 断言与取证脚本(右键组行 -> 设定位置
  -> 确认框 -> 取消/确认; POST 响应取 cmd_id, 结束前在页面上下文取 `/api/cmd/<id>` 终态, 避开 SSE 时序)。
- `memory-bank/`: issue 26-11-04-0734 补真机复验证据; task 档案 P5 回写真机验收结果。
