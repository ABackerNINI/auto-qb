# 6656 passed, 6 skipped —— relocate RM11 真机复验轮收尾全量基线

> 摘要: relocate RM11 真机复验轮收尾全量基线(RM04-35/36/37 三项真机 PASS 收口, 见 kb.baseline 前后链; 本轮代码面 = tests-real 测试侧 + 文档, 产品代码零改动)
> 基线时间: 2026-11-21 06:58
**Refs:** memory-bank/tasks/26-11-15-backend-relocate-refactor.md

## 验收数字

`commands run test.full` 实测(2026-11-21 06:53, Windows, HEAD 73e8f422, 收尾回写随工作树在场):

```text
TOTAL                                                30030     74  10658     77    99%
6656 passed, 6 skipped, 8 warnings in 139.08s (0:02:19)
```

- 汇总: 6656 passed / 6 skipped / 0 failed; **覆盖率闸门达标** —— 99.63% ≥ Windows 阈 99.5(tests/conftest.py `COVERAGE_FLOOR_WIN`; 精确值由本轮 cov 数据文件 `coverage report --precision 2` 现算, 数据文件时刻与本轮完成时刻一致), 耗时单次采样 139.08s(并行 -n 8; 单次采样无区间意义, 区间口径见 testing/baseline.md)。
- 缺口净额(M8): 本片 151 单位(miss 74 + partial 77) 减上片 26-11-21-0016 的 100 单位(miss 42 + partial 58) = **+51**; 分母由语句 29262 / 分支 10402 变为 30030 / 10658。**点名与口径注记**: 本片树与 0016 树非同源 —— 0016 落自 develop 线(traffic-stepwise 收尾轮, 不含 S6 面), 本片树 = relocate S6/RM11 线 rebase 到 origin/develop=d5e5e0c2(远端推进面 = WEBUI 列风格切换整批 + hold_run flake 根治); 与本线最近同源基线 26-11-20-2348(S6, 120 单位, 99.70%)相比净额 +31, 增量全部来自 rebase 带入的远端推进面; **本轮代码面 = tests-real 测试侧 + 文档, 产品代码零改动, 缺口增量与本轮零关联**。本轮实测 miss 头部点名(均属远端推进面/既有缺口, 非本轮触碰面): `webui/runtime_transfer.py` 24 单位 / `core/traffic_grid.py` 12 / `core/fastresume.py` 11 / `infra/bt_backup_probe.py` 8。
- 同轮首跑红记账: 收尾回写中途 `test_claim_chain_is_bidirectional` 1 红 —— 档案 Refs 增补 RM11 计划后单向链未闭环(回写编辑顺序问题, 非产品回归), `kb.ref` 双向补链 + `kb.docmap` 闸门自证通过后全量复跑即本切片数字; 判据面零放宽。

## 本改动面

本轮(RM11 真机复验轮收尾)改动面, 逐文件:

- `tests-real/rm04_relocate/test_rm04_relocate_probe_async.py`: RM04-36 A5 段 mover 动态识别修(先到 dst 的唯一成员即 mover, 助推非 mover 成员; 断言阈值零放宽)—— 73e8f422 已入库。
- `memory-bank/issues/26-11-10-0638-bug-legacy-review4-relocate-probe-blocking.html`: 状态翻 Done(状态日志 26-11-21 条目 + 修复后补充三段)。
- `memory-bank/plans/26-11-15-2340-plan-relocate-refactor.html`: §03.6 0638 行翻灯已关 / §04-S6 真机复验达成注记 / §10 R8 / doc-status Open → Done(§01 三目标核验后翻)。
- `memory-bank/plans/26-11-21-0223-plan-real-rm11-s6-probe-verify.html`: §10 R3 执行轮记录 / §3.2「210 个真实种子」误标勘误 / doc-status 翻 Done / doc-refs 补档案反向声明(kb.ref)。
- `memory-bank/tasks/26-11-15-backend-relocate-refactor.md`: R4 段(RM11 轮) + Refs/Summary/S6 行同步。
- `memory-bank/pitfalls/ops/seed-clean-vs-evidence.md`: 复发+1(2026-11-21 收尾 seed.clean 裸跑误删取证)。
- 新入池 4 份 issue(Open): 26-11-21-0638(seed.clean 保护闸 rmNN 内层盲区) / 26-11-21-0639(guard 种子计数把 real-fake 计入) / 26-11-21-0639(review 记账排除面缺 real-baselines) / 26-11-21-0639(kb.wrap topic 大写拒绝 + guard vv5.2.3 拼印, cosmetic 合并)。
- 本切片(基线快照)。以上均不触 src/ 运行时代码; tests-real 用例改动只入测试侧执行轨。
