# 7058 passed, 6 skipped, 1 warning in 140.67s (0:02:20) —— S2 transfer D5b 两段回执全量测试基线

> 摘要: S2 transfer D5b 两段回执全量测试基线
> 基线时间: 2026-11-27 13:24
**Refs:** memory-bank/tasks/26-11-27-webui-sse.md

## 验收数字

TOTAL                                                31453  31453     0%
7058 passed, 6 skipped, 1 warning in 140.67s (0:02:20)

`commands run test.full` 实测(2026-11-27)。覆盖率行照实测输出逐字誊写; 本轮全绿。

## 本改动面

- `transfer_flow.js`: `_transferExec` 受理段从 POST 之前挪到 POST 成功返回 `cmd_id` 之后本地渲染(pending 图标 +「后台验证中」), 失败路径不误挂 pending; 新增 `_transferRenderAccepted` / `_transferSettleIcon` 成对共用本批局部 `settled` 集合, 终态先到先记账, 后到的受理段渲染不降级已结算行; 终态仍走既有 `receipt_port -> set_result -> notify("cmd")` 覆盖同 cmd_id, `waitCmd` 保留兜底。后端零改动。
- 测试: `test_transfer_flow_confirm.py` node 电池扩两段可见(受理段 pending→终态 ok)与双跳竞态(迟到受理段不降级/两段共用同一 settled), 静态 +6 守阵; 新增 `test_tf_backend_no_accept_signal_guard`(零 notify 推送点/唯一 set_result notify(cmd)/事件面五项/waitCmd 三态/单写线程); `test_webui_static_r4_poll_auth_lifecycle.py` SSE 电池 +1 事件面清单断言。定向 5 passed + SSE 1 passed。
- e2e: 新增 `tests/e2e/transfer-two-hop.spec.mjs` 双皮肤(prism/atlas)覆盖受理段可见→终态结算→已结算不降级; 2 passed(4.5s)。
- 真机 S2-c: `real.guard` FAIL(端口 56589/56590 均无监听进程), 按计划 D11 记 BLOCKED, 不阻断入库; 未手工杀进程/未拉共享实例。
- 计划 26-11-27-0530 整体仍 Open(S3 未做), issue 26-11-20-0408 状态未动。
