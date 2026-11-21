# 6665 —— 6665 passed, 6 skipped —— guard 豁免单点与 clean B-严格闸收尾全量基线

> 摘要: 6665 passed, 6 skipped —— guard 豁免单点与 clean B-严格闸收尾全量基线
> 基线时间: 2026-11-21 10:13
**Refs:** memory-bank/tasks/26-11-21-test-real-guard-skip-tags-clean-rmnn-gate.md

## 验收数字

`commands run test.full` 实测(2026-11-21 10:05, Windows, HEAD 392ce63d, 收尾回写随工作树在场):

```text
TOTAL                                                30044     74  10662     77    99%
6665 passed, 6 skipped, 8 warnings in 173.85s (0:02:54)
```

- 汇总: 6665 passed / 6 skipped / 0 failed; 覆盖率闸门达标(99% ≥ Windows 阈, 见 testing/baseline.md), 耗时单次采样 173.85s(并行 -n 8)。
- 缺口净额: 本片 151 单位(miss 74 + partial 77) 与上片 26-11-21-0829 的 151 单位(miss 74 + partial 77) **持平净额 0**; 分母由语句 30030 / 分支 10658 变为 30044 / 10662(+14/+4 = 本轮新增生产代码与用例)。本轮代码面 = 真机轨守卫/闸 5 文件, 新增面全覆盖(净额 0 = 新增缺口为零)。

## 本改动面

本轮(修 issue 26-11-21-0639 + 26-11-21-0638)改动面, 逐文件:

- `tests-real/lib/guard.py`: 新增 `REAL_FAKE_TAG` 标签单点与 `fakes(qb)` 认领单点; snapshot docstring 钉「调用方必须显式传 skip_tags」。
- `tests-real/runner.py`: cmd_guard/cmd_pause_all 显式传 `skip_tags=(guard.REAL_FAKE_TAG, )`, 输出改双口径(真实 N 已暂停 / 自造 M 不计入·未动); pause-all help 同步行为。
- `tests-real/conftest.py`: env fixture 的保护面收窄到真实种子(自造种子不由守卫暂停、不进看门狗保护面)。
- `tests-real/seed.py`: TAG 收敛为 guard.REAL_FAKE_TAG 短别名、_fakes 委托 guard.fakes; clean 整扫新增第二层闸(CASE_DIR_RE + _dirty_case_dirs): rmNN 内层有文件即整单拒跑(rc=1, 拒跑信息逐 rmNN 列内层文件数与前 5 路径), 零文件空壳照旧收壳, --dir 指名子树仍是显式豁免口。
- `tests/test_real_machine_safety.py`: 守阵 6 条 —— 静态守阵 test_real_guard_snapshot_callers_pass_skip_tags(全 tests-real 扫描 snapshot 裸调, 带已知违规活性探针)、test_guard_snapshot_skips_tagged_seeds(豁免语义双端钉)、test_cmd_guard_reports_real_and_fake_counts / test_cmd_pause_all_skips_fakes(双口径+传参)、test_seed_clean_refuses_rmnn_case_dirs_with_files(rmNN 有文件整单拒跑 + --dir 豁免口 + 不波及 seeds)、test_seed_clean_sweeps_seeds_and_ram_when_no_case_files(空壳照收 + seeds/R: 原契约不变, 重写自原 known_namespaces 用例); 头部 docstring 测试计划同步。
- 回写面: 两 issue HTML 翻 Done + 复验 + 修复后补充(0638 含改道说明)、坑档 pitfalls/ops/seed-clean-vs-evidence.md 处置行升级(「clean 前先 ls 盘点」+ rmNN 闸强制)、testing/real-machine.md §2.4 口径、.commands/real/config.toml 的 real.seed.clean 文案。
