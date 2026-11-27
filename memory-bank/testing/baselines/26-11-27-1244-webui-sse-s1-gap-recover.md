# 7057 passed, 6 skipped, 1 warning in 152.91s (0:02:32) —— S1 补充单游标回捞缺口修复全量测试基线

> 摘要: S1 补充单游标回捞缺口修复全量测试基线
> 基线时间: 2026-11-27 12:44
**Refs:** memory-bank/tasks/26-11-27-webui-sse.md

## 验收数字

TOTAL                                                31453  31453     0%
7057 passed, 6 skipped, 1 warning in 152.91s (0:02:32)

`commands run test.full` 实测(2026-11-27)。覆盖率行照实测输出逐字誊写; 本轮全绿。

## 本改动面

- `lifecycle.js`: created 初始化 `_errReconcileAfter`; `onErrlogEvent` 合并前间隙侦测记回退游标(`min(已有 ?? 当前游标, 到达seq-1)`); `_pullErrlog` 的 `after` 改用回退游标, 回捞走既有 merge 去重/排序/游标 max 且不计未读, 仅相等时清空, GET 失败保留, reseed 同步清空。不改后端/配置/事件类型/seq 语义。
- 测试: `test_webui_static_r4_poll_auth_lifecycle.py` 的 `_NODE_ERRLOG_EVENT_PROBE` 扩九组缺口回捞断言(回捞成功/降序落位/不去重计/游标不倒退/成功后清空/多缺口保最早/GET 期间新缺口不误清/失败保留/reseed 清); `test_webui_error_history.py` 静态接线 +6 断言。定向 21 passed。
- 计划 26-11-27-0530 §05/§06 D13/§10 R4 回填; 任务档案补 R2 进度日志; 整体仍 Open(S2/S3 未做), issue 状态未动。
