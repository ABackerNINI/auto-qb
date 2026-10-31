# 基线切片 26-10-05-0945 — 测试文件头部「## 测试计划」清单幽灵条目清理(纯文档轮)

> 摘要: 认领 issue 26-10-05-0922 并扩面到全 tests/ —— 79 份带「## 测试计划」的测试文件里 11 份共 21 条清单条目指向全仓不存在的函数。
> 逐条裁决后改名/合并 15 条 · 删除 5 条 · 跨文件指针修正 1 条, 另补登 2 条漏登。**只改 docstring, `src/` 与用例体零改动**, 故用例数与本笔无关地只受既有分支影响。
> 基线时间: 2026-10-05 09:45

**Refs:** memory-bank/tasks/26-10-05-test-plan-docstring-drift.md, memory-bank/activeContext/26-10-05-0945-test-plan-docstring-drift.md

- 分支: develop @ ef93db56(工作树含本轮改动: 11 份 tests/*.py 头部 docstring + issue 状态回填 + 切片/档案)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2603 passed + 4 skipped, 40.15s / 45.13s(两次采样), 覆盖率 TOTAL 99%**
  (15605 语句 / 163 未覆盖 / 5308 分支 / 138 partial; 门槛 98% 达标; 第二次采样为收尾闸门复跑, 中途修掉一处自引入的相对链接坏链)
- 相对上一条基线 (26-10-05-0947: 2589 passed + 4 skipped / 36.73s / 99%): passed **+14** /
  语句 +29 / 分支 +12 / partial +1。**+14 与本笔无关** —— 上基线记于 `86441e54`, 该提交之后
  并入的分支新增 `def test_*` **14 条 / 删除 0 条**(实测 `git diff 86441e54..HEAD -- tests/`),
  即 HR 稳态降频分支的 S1 5 + S3 3 + S4 6(档案 [26-10-05-backend-hr-steady-throttle](../../tasks/26-10-05-backend-hr-steady-throttle.md))。
  **本笔只改 11 份测试文件头部 docstring, 零用例增删, 故 passed / skip / 语句 三组对本笔零增量。**
- 耗时 40.2~45.1s 落在近几条切片 36.7~51.8s 的噪声带内, 非回归。
- 靶向验证(非计时): 幽灵扫描脚本比对 79 份带清单文件的「清单条目 vs AST `def test_*`」——
  改前 21 条幽灵, 改后 **0 条**; `test_config_schema.py` 另做双向核对(幽灵 0 / 漏登 0)。
- 改动面: 11 份 `tests/*.py` 的模块 docstring(`test_config_schema` / `test_checking` / `test_config_writer` /
  `test_hr_config` / `test_hr_report` / `test_hr_runtime` / `test_hr_service` / `test_hr_worker` /
  `test_state_matrix` / `test_torrents` / `test_tracker`) —— 测试函数体与 `src/` **零改动**。
- 未验证面: 「文件内有、清单无」的漏登只对 `test_config_schema.py` 做了全量核对; 其余文件的清单
  本就不穷举(如 test_web.py 280 个用例只列 ~90 条), 未做漏登排查(范围守恒, 记在本轮档案遗留段)。
