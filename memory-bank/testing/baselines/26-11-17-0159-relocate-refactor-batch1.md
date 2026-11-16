# 6324 passed, 2 skipped —— relocate 重构第一批(S1-S4)收尾全量基线

> 摘要: relocate 重构第一批(S1-S4)收尾全量基线
> 基线时间: 2026-11-17 01:59
> 档案: memory-bank/tasks/26-11-15-backend-relocate-refactor.md

## 验收数字

`commands run test.full` 实测(2026-11-17 01:52, Windows 开发机, refactor/relocate-single-active @ cd786499):

```text
TOTAL                                                28371    129  10100    117    99%
FAIL Required test coverage of 99.5% not reached. Total coverage: 99.31%
6324 passed, 2 skipped in 175.45s (0:02:55)
```

- 汇总: 6324 passed / 2 skipped; **覆盖率闸门未过** —— 99.31% < Windows 阈 99.5(tests/conftest.py `COVERAGE_FLOOR_WIN`), test.full 退出码 1。用例面零失败, 红在覆盖率闸。
- 缺口净额(M8): 本片 246 单位(miss 129 + partial 117) 减上片 26-11-15-1546 的 152 单位(miss 73 + partial 79) = **+94**; 分母由语句 27855 / 分支 9822 变为 28371 / 10100(第一批 relocate 新增代码, 净 +516 语句 / +278 分支)。
- **点名(净额 +94 > +15)**: 新增缺口主体 = relocate 家族本批新增路径 —— `relocate_mod`(91%, miss 21 + partial 20)/`relocate_exec`(96%, 30+24)/`relocate_units`(96%, 19+12)/`relocate_lifecycle`(97%, 8+4)/`relocate_plan`(99%, 1+4)/`recycle_daemon`(98%, 8+7)/webui relocate 面(`commands_torrents` 6+4, `server/routes/relocate_chain` 4+0)。上片无逐模块台账, 名单按本批触碰面取现值; 补测属后续轮, 阈值未动。

## 本改动面

- 测量树 = 第一批 S1-S4 六笔提交链(f0004ef9 → 785ad5ae → dae75d34 → df15af5f → 3692616c → cd786499) + 收尾回写(计划 26-11-15-2340 R1 注记/任务档案 R1 段/issue 26-11-17-0156, 纯文档零代码)。
- 六笔提交的逐笔实测(test.quick 与评审轮次)见各提交信息与任务档案 R1 段; 本片只记录收尾时点全量。
- 覆盖率缺口补测未在本轮做: 第一批验收行「test.full 全绿」的覆盖率半边未达成, 已如实上报, 补测与阈值裁量由用户定。
