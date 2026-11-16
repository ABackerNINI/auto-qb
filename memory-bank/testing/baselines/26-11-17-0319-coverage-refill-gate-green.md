# 6368 passed, 2 skipped —— 覆盖率补测到闸门绿(用户拍板「补测轮到闸门绿」)全量基线

> 摘要: relocate 家族覆盖率补测收口, 覆盖率闸门转绿(99.76% >= 99.5)
> 基线时间: 2026-11-17 03:36
> 档案: memory-bank/tasks/26-11-15-backend-relocate-refactor.md

## 验收数字

`commands run test.full` 实测(2026-11-17 03:33-03:36, Windows 开发机, refactor/relocate-single-active @ 11fc721d + 未提交补测工作树):

```text
TOTAL                                                28371     37  10100     54    99%
Required test coverage of 99.5% reached. Total coverage: 99.76%
6368 passed, 2 skipped in 163.75s (0:02:43)
```

- 汇总: 6368 passed / 2 skipped; **覆盖率闸门已过** —— 99.76% >= Windows 阈 99.5(tests/conftest.py `COVERAGE_FLOOR_WIN`), test.full 退出码 0。阈值未动。
- 缺口净额(M8): 本片 91 单位(miss 37 + partial 54) 减上片 26-11-17-0159 的 246 单位(miss 129 + partial 117) = **-155**; 分母 28371 / 10100 与上片持平(本轮零 src 改动, 纯补测 +44 用例)。
- 补测面(上片点名清单逐项清偿): `relocate_mod`(21+20 -> 0 miss, 剩 2 条不可达防御弧: 旧账 `superseded_from` 恒非空使 `old_dst` 假支不可达 / `arm_members_of` 对非空 hash 恒产一条 member 使空迭代弧不可达)/`relocate_exec`/`relocate_units`/`relocate_lifecycle`/`recycle_daemon`(100%)/`webui relocate 面`(commands_torrents / server/routes/relocate_chain 100%)全部按行为有意义分支补齐; 剩余缺口散布在非本批触碰面(与上片同源存量), relocate 家族余量全部为防御弧(relocate_mod 385->387/461->460, relocate_units 1004->1006, relocate_exec 650/1286 等现实不可达形态)。
- 新增用例 44 条分布于 11 个既有测试文件(每文件头部「## 测试计划」已同步, docstring 守卫绿); dev.fmt 已过。
