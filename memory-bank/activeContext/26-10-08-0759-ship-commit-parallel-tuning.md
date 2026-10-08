# ship-commit-parallel-tuning — ship.commit 提速: 闸门并行度 -n 4 → -n 8

> 摘要: 用户报 `commands run ship.commit` 跑 161s「大概率出 BUG」。逐条复刻 `run_gates` 展开实测, 归因 **不是逻辑 BUG**: 161s 里 **118s(69%) 是 `test.pkg`**(`.commands` 全包 134 个真实 git 场景用例), 43s(25%) 是 `test.quick`。根因是 `-n 4` 这个并行度是 2026-10-03 为「修 `-n 0` 挂死」随手定的、**从没按速度调过**, 而两类用例体量已从 96/1191 涨到 154/2772。修法 = 两处并行度上调 `-n 8`(`.commands/test/config.toml` 的 `test.pkg`/`test.quick` + `pytest.ini` 的 addopts), 实测 `test.pkg` 112s→85s、`test.quick` 31s→20s、同一改动集闸门合计 169s→~89s。坑档 `pitfalls/testing/parallel-run.md` 已重写「甜点」节(甜点随笔例体量与负载形态漂移; `-n auto` 会 2 failed + 16 errors, 必须避免)。
> 最后活动: 2026-10-08 07:59

## 已完成(详情见坑档与配置注释, 不在此复述)

- 诊断: 逐条闸门耗时排序(`_pipeline.run_gates` 复刻) —— `test.pkg` 117.7s / `test.quick` 42.8s / 其余 10 条共 ~11s。
- 并行度扫描实测(全绿): `test.pkg` 类 -n 4=117s / 6=90s / **8=73s** / 12=92s / auto=✗失败; `tests/` 类 -n 4=29s / **8=19s** / 16=20s。
- 改动: `.commands/test/config.toml`(`test.pkg`/`test.quick` 显式 `-n 8` + note 写实测数字与「别用 auto」) / `pytest.ini`(addopts `-n 8` + 注释说明甜点随体量漂移)。
- 回写: `pitfalls/testing/parallel-run.md` —— 摘要行、`-n 0` 节现状行、`### 现状: 默认并行` 节全节重写(含 A/B 两张判别表 + 两条「结论曾被推翻」教训 + 重测配方)。

## 正在进行

- 待用户说「提交」后 `commands run ship.commit`(本轮改动 3 文件: config.toml / pytest.ini / parallel-run.md)。

## 未决项

- **闸门耗时未换基线切片**: 本次改的是闸门配置而非 `src/`/`tests/` 代码, 未跑 `test.full` 出基线切片 —— 若收尾要求补一份「闸门耗时基线」, 需另立 `testing/baselines/` 切片。
- **cap 债务 3 项**(`check_context_caps.py` 报, 与本次无关): `memory-bank/tasks/_index.md` 等超标, 不拦提交, 需**另开新会话**清理(本会话不修, 遵循范围守恒)。
- 未回写 `memory-bank/pitfalls/kb/` 或 progress 其它处 —— 本次无新增代码事实越界。
