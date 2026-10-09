# WEB UI 命令层捕获 qB 业务拒绝(4xx) · 已闭环

> 摘要: 用户报「webui 操作队列时报错」—— 队列命令被 qB 以 HTTP 409 拒绝(「必须启用 torrent 队列」, 库抛 `Conflict409Error`), 异常冒泡到 `WebUIRuntime.consume_commands` 兜底 `except`, 记 ERROR + 堆栈, 回执只有库原文。按用户拍板(**所有 WEB UI 命令** / **友好提示 + 日志降噪**)实施: 判据与文案单点 `webui/commands.py::qb_reject_text`(qB HTTP 4xx 且非 401 -> 可读文案 + 已知场景行动建议), 分发层只分流 —— 命中走 WARNING 无堆栈, 其余仍 ERROR + `exc_info=True`。**401 必须显式排除**(鉴权失败是凭据/环境故障, 与"业务拒绝"不同质, 二者同为 `HTTP4XXError` 子类)。
>
> 最后活动: 2026-10-09 13:07

**Refs:** memory-bank/tasks/26-10-09-webui-qb-command-reject.md,memory-bank/pitfalls/backend/qb-api.md,memory-bank/testing/baselines/26-10-09-1307-webui-qb-command-reject.md

## 本轮完成

- **`webui/commands.py`**: 新增 `QB_REJECT_HINTS`(按 qB 文案子串给行动建议, 中文 + 英文各一条)与 `qb_reject_text(exc)` —— `HTTP4XXError` 且非 `HTTP401Error` 时返回「qB 拒绝执行: <原文>(<建议>)」, 否则 `None`。文案只在这一处拼。
- **`webui/runtime.py::consume_commands`**: 兜底 `except` 改用 `qb_reject_text` 分流 —— 命中业务拒绝 `logger.warning`(无堆栈), 未命中 `logger.error(..., exc_info=True)`; 回执文案统一用分流后的 `reason`。
- **守阵**: `tests/test_web_commands.py` 新增 `test_qb_reject_text_classification`(分流矩阵)与 `test_queue_torrent_qb_reject_receipt_and_log`(409 端到端: 回执 + WARNING 分支); docstring「测试计划」同步。
- **回写**: 坑档 `pitfalls/backend/qb-api.md` 追加一条(4xx 分流 + 401 排除 + 单点位置); 档案 + 本切片 + 基线切片。实测数字见 `commands run kb.baseline`。

## 待办 / 移交

- **其它 4xx 文案暂无专门建议**: 目前只覆盖「未启用 torrent 队列」; 若遇到其它高频 qB 拒绝(如"名字已存在"), 在 `QB_REJECT_HINTS` 补一条 needle 即可(单点)。
- **真机未启用队列场景未实跑**: 用 FakeClient 抛异常复现; 若日后要前端主动禁用队列按钮(前置检查 `app.preferences.queueing_enabled`), 属另一专题。
- 无代码遗留。
