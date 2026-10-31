# 2785 —— 常驻锚「覆盖进度总表」+ 约束进 skill / 相关文档 基线

> 摘要: 给变异测试常驻排期锚 issue 新增 **§07 覆盖进度总表**(列 = 包/模块 · 上次测试日期 · 变异数 · 杀死率 · 编号/轮次 · 状态 · 基线切片/计划/任务档案), 原 §07 轮次台账顺延为 §08、状态日志为 §09; 并把约束「**每次变异测试实施完成后必须同步更新该表**」写成指导 skill 的**硬约束 12** 与专节「覆盖进度总表(收尾必更)」, 同步进证据报告 §14/§15 与命令包深读 `why.md`。**纯文档改动: 零 `src/`、零 `tests/` 改动**。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 09:39

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(工作树含本专题全部改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2785 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16476 语句 / 164 未覆盖 / 5694 分支 / 148 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0920](26-10-08-0920-mutation-audit-tooling.md)(2785 passed + 4 skipped, 同 16476 / 164 / 5694 / 148): **逐位持平**(本轮零 `src/`、零 `tests/` 改动)。

## 文档守卫实测

- `commands run kb.index`: 重建 20 个生成物。
- `commands run kb.check`: 主键纪律(520 份文档 / 274 个专题)· 认领链(双向闭环)· 回写守卫(措辞 + 手抄测试数字, **无违规**)· 日期守卫全过; 存量 cap 债务 3 项未增/未减(不拦提交, 转告用户另开会话清理)。
- `commands run doc.links` 无坏链; `commands run doc.drift` 0 处手抄命令; `commands run doc.caps` 无**新增**债务。

## 对照判据(后续沿用)

- `test.full` 以本切片(2785 + 4 / 16476 / 164 / 5694 / 148)为对照点。
- **覆盖进度总表口径自查**: 表中每个「已做」行须有基线切片链接、日期与切片一致、变异数/杀死率与切片逐位一致, 且**不含 `N passed`**(那是切片的事, 手抄会被回写守卫判据族 B 判红)。
