# 5010 passed + 10 skipped —— 通知守卫按载荷形态改判全量基线

> 摘要: issue 26-11-03-2216 修复(通知守卫按 argv 载荷形态精确匹配, 不再按命令名拦 powershell)后的全量基线
> 基线时间: 2026-11-04 01:30
**Refs:** memory-bank/issues/26-11-03-2216-bug-test-notifier-guard.html

## 验收数字

`commands run test.full` 实测(develop, Windows 并行 + 覆盖率):

```text
[ok] test.full (140.1s)
  TOTAL                                                23325    185   7956    158    99%
  5010 passed, 10 skipped in 138.01s (0:02:18)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 140.1s; 覆盖率闸 Windows 99.0(`tests/conftest.py` 单点)。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests/conftest.py`: `_guard_run` 判据从「命令名 ∈ NOTIFIER_EXECUTABLES」改为「argv 命中通知载荷形态」(`_is_notifier_cmd`): `notify-send` 按名拦; `powershell`/`pwsh` 只拦 `-EncodedCommand`(toast 专用); `osascript` 按脚本短语 `display notification` 拦。非通知用途的 powershell `-Command`(端口探针)放行, 真实进 sidefx 台账按 POPEN 判越界 —— 此前在 Popen 构造前抛错致台账漏记(issue 26-11-03-2216)。
- `tests/test_notify.py`: `test_notify_real_send_blocked_under_pytest` 补 win32 toast send 失败分支; 新增 `test_notify_guard_payload_matching`(非通知 powershell 穿透到真实 run + 四形态通知载荷仍拦)。
- `memory-bank/testing/file-conventions.md`: 守卫口径段同步改判描述。
