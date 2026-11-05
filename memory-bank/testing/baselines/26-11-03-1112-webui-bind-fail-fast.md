# 4971 passed + 2 skipped(根) —— WebUI bind fail-fast 全量基线

> 摘要: WebUI bind fail-fast 启动期 fail-fast 全量基线
> 基线时间: 2026-11-03 11:12
**Refs:** memory-bank/plans/26-11-03-0930-plan-webui-bind-fail-fast.html, memory-bank/testing/real-baselines/26-11-03-1045-real-rm01-webui-bind.md, memory-bank/tasks/26-11-03-webui-bind-fail-fast.md

## 验收数字

`commands run test.full` 实测(分支 `feat/webui-bind-fail-fast`, Windows 并行 + 覆盖率):

```text
TOTAL                                                22975    137   7792    129    99%
4971 passed, 2 skipped, 3 warnings in 197.29s (0:03:17)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 204.0s。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `src/auto_qb/infra/port_owner.py`(新增): 三平台端口占用者探针 `describe_port_owner`, 三态 found/absent/unavailable, 总预算 1.5s, 任何异常降级且不抛出。
- `src/auto_qb/webui/server/lifecycle.py`: 新增 `WebUIBindError(AutoQbError)` 与单行消息 `_bind_message`; 低层 `start_web_server` 保持「返回 handle」的原契约。
- `src/auto_qb/webui/module.py`: `WebUIModule.start` 在 `web.handle.started` 为假时先落 INFO 诊断块(原因/占用者/处置/退出)再抛 `WebUIBindError`; 探针结果只进日志。
- `src/auto_qb/core/qbmanager.py`: `host.start_all(dry_run)` 移入 `try`, 新增 `lifecycle_ready` 闸门(catch/finally 均走 `stop_all`, 失败启动不落空态 `state.json`, 锁在任何路径都释放)。
- 测试: `tests/test_port_owner.py`(新增, 三平台 mock/三态降级/预算)、`tests/test_web_admin.py`(模块级抛点与诊断块)、`tests/test_qbmanager_loop.py`(`start_all` 抛错时 stop_all/不落盘/释放锁)、`tests-real/rm01_startup/test_rm01_startup.py`(RM01-06 判据反转为启动期 fail-fast)。
