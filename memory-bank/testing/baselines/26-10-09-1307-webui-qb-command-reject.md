# 2846 —— WEB UI 命令层捕获 qB 业务拒绝(HTTP 4xx)

> 摘要: 「WEB UI 命令层捕获 qB 业务拒绝」专题收尾基线。改动: `webui/commands.py` 新增 `QB_REJECT_HINTS` + `qb_reject_text`(qB HTTP 4xx 且非 401 -> 可读回执文案 + 已知场景行动建议); `webui/runtime.py::consume_commands` 的兜底 `except` 据此分流 —— 命中业务拒绝走 WARNING 无堆栈, 未命中(网络/鉴权/代码 bug)仍 ERROR + `exc_info=True`。回执文案统一为「qB 拒绝执行: <qB 原文>(<建议>)」。
> 档案: memory-bank/tasks/26-10-09-webui-qb-command-reject.md
> 基线时间: 2026-10-09 13:07

**Refs:** memory-bank/tasks/26-10-09-webui-qb-command-reject.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2846 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial)
- **耗时**: 31.30s(命令墙时 33.3s)
- **新增用例**: 2 个测试函数 —— `tests/test_web_commands.py::test_qb_reject_text_classification`(分流矩阵: 已知 4xx 附建议 / 未知 4xx 只给通用前缀 / 401 / 5xx / 非 qB 异常均返回 None)与 `test_queue_torrent_qb_reject_receipt_and_log`(queue_torrent 遇 409 端到端: 回执带可读文案 + 行动建议, 走 WARNING 分支而非 ERROR)。

## 说明

- **代码事实变更**: 有 —— `webui/commands.py` 新增判据/文案单点; `webui/runtime.py` 兜底 except 分流日志级别与回执文案。无前端改动。
- **未验证面**: ①真机 qB 未启用队列场景未实跑(用 FakeClient 抛 `Conflict409Error` 复现冒泡路径); ②其它 4xx 文案(如"名字已存在")暂无专门行动建议, 走通用前缀; ③英文界面下建议文案未真机核对(按 `torrent queueing` 子串兜底)。
