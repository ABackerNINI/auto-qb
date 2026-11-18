# 6466 passed + 6 skipped(根) —— sigterm-stall 复验判别观测面落地与 20 轮采样收尾基线

> 摘要: sigterm-stall 复验判别观测面落地与 20 轮采样收尾基线(webui-boot-first-data 计划全步落地后的 sigterm-stall S0/S1 观测面轮)
> 基线时间: 2026-11-19 03:20

## 验收数字

```
6466 passed, 6 skipped in 161.79s (0:02:41)
TOTAL  28870     43  10306     60    99%
```

- 对上一切片(26-11-18-1633 e2e-ci-perf-backup-harness-fix): passed +6(6460→6466)/ skipped 持平 6 / 语句 28864→28870(+6)/ miss 持平 43 / 分支 10304→10306(+2)/ partial 持平 60, TOTAL 99% 持平 —— 增量来自 S2 守阵新用例面; 基线 commit = 9a28eebe(plan-26-11-19-0054-sigterm-stall)。

## 本改动面

- src/auto_qb/core/qbmanager.py: 启动首轮提前发布(07306fd3 S1, apply_sync 落库后即发基础视图)+ S2 守阵补钉(8c420060)。
- tests/test_webui_boot_first_publish.py 新增(S2 守阵: 两代发布语义 / rid 序列 / delta 兼容)+ tests/test_qbmanager_tasks.py 扩面。
- e2e/boot-first-two-hop.spec.mjs 新增 + e2e/harness.mjs / e2e/lib/mode.mjs / playwright.config.mjs / scripts/ui_harness.py 修整(冷启动两跳 spec 与 harness 面; 不在 pytest 数字内)。
- tests-real/tools/run_s0_boot.py(+171/-9, 9a28eebe S0/S1 停机观测面: stop.polls + faulthandler 看门狗)+ measure_boot_first_data.py / seed_bulk_boot.py 新工具(真机轨, 不在 pytest 收集面)。
- memory-bank 文档面: webui-boot-first-data 计划档案/基线/证据档收尾 + graceful-stop-sigterm-stall issue 26-11-18-2350 / 计划 26-11-19-0054 / 2 则新 issue 入池 / 2 则坑档(不占测试数字)。
