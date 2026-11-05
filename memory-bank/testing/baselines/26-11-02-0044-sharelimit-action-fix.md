# 4804 passed + 2 skipped / TOTAL 99%(22482 语句 / 164 未覆盖 / 7708 分支 / 135 partial) —— WebUI shareLimitAction 必填参修复后全量基线 (issue 26-11-01-2102)

> 摘要: WebUI shareLimitAction 必填参修复后全量基线 (issue 26-11-01-2102)
> 基线时间: 2026-11-02 00:44
**Refs:** memory-bank/issues/26-11-01-2102-bug-webui-set-share-limits-missing-sharelimitaction.html, memory-bank/tasks/26-11-02-backend-webui-seed-cmds.md

## 验收数字

- `commands run test.full` (2026-11-02 00:41, 本 clone 工作树, 改动未提交):
- TOTAL 表: `TOTAL  22482  164  7708  135  99%` (语句 / 未覆盖 / 分支 / partial / 覆盖率)
- 汇总行: `4804 passed, 2 skipped in 188.08s (0:03:08)`
- 前置: `commands run test.quick` 同树 `4804 passed, 2 skipped in 73.63s`(与全量同数, 无覆盖率报表)
- 口径注记: 全部通过, 无既有失败; `dev.fmt` 已跑(6 个改动 .py)。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `src/auto_qb/core/qbapi.py`: facade `torrents_set_share_limits` 补具名参 `share_limit_action: str = "Default"` 并透传; docstring 补 5.0+/WebAPI 2.10.4 必填语义(issue 26-11-01-2102)。
- `src/auto_qb/webui/commands.py`: `_cmd_set_share_limits` 调用点透传 `share_limit_action="Default"`; docstring 同步。
- `tests/helpers.py`: FakeClient `torrents_set_share_limits` 扩 `share_limit_action` 参, calls 记 5 元组。
- `tests/test_web_commands.py`: 2 处既有断言扩 5 元组 + 注释/文案同步。
- `tests/test_web_longtail.py`: 1 处既有断言扩 5 元组。
- `tests/test_qbapi_wire.py`: 新增 `test_facade_set_share_limits_wire_carries_share_limit_action`(经 QbApi facade 出口断言请求体含 shareLimitAction=Default + shareLimitsMode=Default)+ 头部「## 测试计划」同步。
