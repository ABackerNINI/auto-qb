# 测试覆盖率提升 · 计划已出待执行

> 摘要: 用户要求提升 91% 覆盖率。实测缺口地图 (1,625 单位: 1,030 行 + 595 分支出口) 后出四阶段计划 **plans/26-10-01-2157-plan-test-coverage-uplift.html** (P0 快赢→93% / P1 服务层→95% / P2 tray→96%± / P3 防回沉阈值化), 档案 26-10-01-test-coverage-uplift。**执行未开工**, 首批 = P0 的 T0.1–T0.7。
> 最后活动: 2026-10-01 22:06

- **关键事实**: 分母 17,718 单位 (13,300 语句 + 4,418 分支出口), 每单位 ≈ +0.0056%; 最大单文件欠账 tray/app.py (31%, 277 单位) 单列 P2; A 类「整块功能空洞」(versioning 迁移函数 / events.py SSE 生成器 / routes/hr.py) 最优先。
- **机制抓手**: `--cov-fail-under` 随阶段抬 (92→94→95), 永低于实测 1 个点; `test.quick` `--no-cov` 有意豁免不动。
- **正在进行**: 无 (计划轮已收尾)。
- **下一步**: 用户认领后从 P0/T0.1 (versioning `_migrate_hr_site_1_2` 整函数补测, tests/test_versioning.py) 开始; 执行纪律见计划 §4 (pitfalls/testing 引用清单)。
