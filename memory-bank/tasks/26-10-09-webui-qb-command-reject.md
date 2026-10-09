# 26-10-09-webui-qb-command-reject — WEB UI 命令层捕获 qB 业务拒绝(4xx)

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Summary:** WEB UI 队列操作遇 qB「必须启用 torrent 队列」(HTTP 409 `Conflict409Error`) 时, 库异常冒泡到命令分发层兜底 `except`, 记 ERROR + 堆栈且回执只有库原文。本轮在命令层加判据/文案单点 `webui/commands.py::qb_reject_text`(qB HTTP 4xx 且非 401 -> 可读文案 + 已知场景行动建议), 分发层 `consume_commands` 据此分流: 命中走 WARNING(无堆栈), 其余仍 ERROR + 堆栈; 回执文案统一为「qB 拒绝执行: <qB 原文>(<建议>)」。范围按用户拍板 = **所有 WEB UI 命令**; 行为 = **友好提示 + 日志降噪**。
**Topics:** webui-qb-command-reject

**Refs:** memory-bank/pitfalls/backend/qb-api.md,memory-bank/testing/baselines/26-10-09-1307-webui-qb-command-reject.md

## 原始请求

webui 操作队列时报错, 需要捕获报错:

```
2026-10-09 10:48:46,324 - ERROR - WEB UI 命令执行失败: queue_torrent: 必须启用 torrent 队列
Traceback (most recent call last):
  File ".../webui/runtime.py", line 456, in consume_commands   # 分发处调用 handler
  File ".../webui/commands.py", line 604, in _cmd_queue_torrent # 调 qB 队列端点方法
  ...(qbapi -> qbittorrentapi.request)
qbittorrentapi.exceptions.Conflict409Error: 必须启用 torrent 队列
```

## 思考过程与决策

- **范围(用户拍板)**: 不是只修 `queue_torrent`, 而是在**命令分发层**统一捕获所有 WEB UI 命令的 qB 业务拒绝。
- **行为(用户拍板)**: 友好提示(可读文案 + 可行动建议) + 日志降噪(命中业务拒绝 -> WARNING 无堆栈)。
- **分类判据**: 捕获集 = qB 的 **HTTP 4xx 业务拒绝**(库共同基类 `HTTP4XXError`)。**401 显式排除** —— 鉴权失败是凭据/环境故障, 需人工介入(弹窗测试 -> ERROR), 与「业务拒绝」不同质; 5xx / 连接错误同样不降噪。
- **落点**: 判据与文案单点放 `webui/commands.py`(与 `_add_outcome` 同域, 二者都是"qB 交互语义"); 分发层 `runtime.consume_commands` **只分流**, 不重复拼文案。
- **行动建议尽力而为**: `QB_REJECT_HINTS` 按 qB 返回文案子串匹配(中文 + 英文各一条), 命中才附 —— qB 文案随其 WebUI 界面语言变化, 匹配不到只给通用前缀, 不猜。

## 实现计划

1. `webui/commands.py`: 加 `QB_REJECT_HINTS` 常量 + `qb_reject_text(exc)`(4xx 且非 401 -> 文案, 否则 None)。
2. `webui/runtime.py::consume_commands`: 兜底 `except` 改用 `qb_reject_text` 分流日志级别与回执文案。
3. 守阵: `test_qb_reject_text_classification`(分流矩阵) + `test_queue_torrent_qb_reject_receipt_and_log`(409 端到端)。
4. 回写: 坑档 `pitfalls/backend/qb-api.md` + 本档案 + activeContext 切片 + 测试基线。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 命令层判据/文案单点 `qb_reject_text` + `QB_REJECT_HINTS` | Done |
| 2 | 分发层日志级别与回执文案分流 | Done |
| 3 | 两条守阵 + `test_web_commands.py` docstring 测试计划同步 | Done |
| 4 | 坑档回写 + 本档案 + 切片 + 测试基线 | Done |

## 进度日志

- **2026-10-09 13:0x** 开工同步 `ff768df6`(工作区净)。读 `webui/runtime.py::consume_commands` / `webui/commands.py::_cmd_queue_torrent` / `core/qbapi.py` 队列四方法, 确认异常冒泡路径; 用 AskUserQuestion 定范围(所有命令)与行为(友好提示 + 日志降噪)。核对 `qbittorrentapi.exceptions` 继承结构(`HTTP4XXError` 是 4xx 共同基类, `Unauthorized401Error` 亦其子类, 必须排除)。实现 → `dev.fmt` → `commands run test.quick` 全绿 → `commands run test.full` 见基线切片。回写坑档/档案/切片/基线。
