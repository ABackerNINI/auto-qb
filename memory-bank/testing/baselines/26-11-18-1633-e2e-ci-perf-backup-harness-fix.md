# 6460 passed + 6 skipped(根) —— e2e perf 计数窗口与 harness GTM 隔离修复批基线

> 摘要: e2e perf 计数窗口与 harness GTM 隔离修复批基线
> 基线时间: 2026-11-18 16:33

## 验收数字

```
6460 passed, 6 skipped in 227.03s (0:03:47)
TOTAL  28864  43  10304  60  99%
```

- 对上一切片(26-11-18-0721 backend-qbmanager-startup-reload-discard) passed / skipped / TOTAL 逐位不变 —— 本批改动只在 Playwright spec 与桩脚本(不在 pytest 收集面); 首次尝试因外部 TMPDIR 被自举探测拒收(rc=4), 清掉环境变量后干净重跑。

## 本改动面

- e2e/perf.spec.mjs: `benchRun` 每段起清零 `window.__gbr`, 修 P1-3 累计计数混入 A 段导致 atlas 越界的假红; 预算公式/阈值/rounds 未动。
- scripts/ui_harness.py: 新增 `_isolate_gtm_discovery(tmp)`, create_app 前把 `agent.pointer_dir()` 重定向到桩私有临时目录, 修 settings-backup 桩读到宿主用户级 GTM 指针的恒红; 产品代码/spec 断言零改动。
- memory-bank: 两 issue 回填根因/修法/验证数字并翻 Done; flaky 台账两行翻 Done; 本切片记录基线。
