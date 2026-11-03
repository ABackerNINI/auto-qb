# 5038 passed + 2 skipped(根) —— HR feeder wake 转发断言修复后全量基线(issue 26-11-03-1209 认领修复后)

> 摘要: HR feeder wake 转发断言修复后全量基线(issue 26-11-03-1209 认领修复后)
> 基线时间: 2026-11-04 01:48
**Refs:** memory-bank/issues/26-11-03-1209-test-test-hr-runtime-feeder-wake-forward-unasserted.html

## 验收数字

`commands run test.full` 实测(develop, Windows 并行 + 覆盖率):

```text
[ok] test.full (156.5s)
  TOTAL                                                23325    167   7956    152    99%
  5038 passed, 2 skipped in 153.97s (0:02:33)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 156.5s; 覆盖率闸 Windows 99.0(`tests/conftest.py` 单点)。与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。上基线(deps-upgrade, 26-11-04 01:33)TOTAL 表逐位相同 —— 本轮纯测试内改动, 源码零变化。

定向旁证: `commands run test.one -- tests/test_hr_runtime_feeder.py` 全文件 26 passed; 红验时掐掉 `runtime.wake` 转发后新断言在 `tests/test_hr_runtime_feeder.py:286` 必红, 还原实现后复绿(实现零残留, git diff 只含测试与 KB 件)。

## 本改动面

- `tests/test_hr_runtime_feeder.py::test_wake_is_safe_and_forwards_to_worker`: 弱断言修复 —— 原体只调用 `runtime.wake()` 不断言转发; 现在 `monkeypatch.setattr(runtime.worker, "wake", …)` 注入替身记录调用, 断言 `forwarded == [True]`(未启动空转分支保留)。文件头「测试计划」清单条目同步。
- 红验: 临时把 `src/auto_qb/hr/runtime.py` 的 `wake` 改为不转发 → 新断言必红; 还原后复绿, `src/` 零残留。
- `memory-bank/issues/26-11-03-1209-test-test-hr-runtime-feeder-wake-forward-unasserted.html`: 状态 Open→Done, 补认领/复验/实际修法/验证数字状态日志(索引已重建)。
