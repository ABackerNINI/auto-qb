# 基线 · 2408 passed + 3 skipped / 99% —— HR 四现象故障取证轮(纯文档)

> 摘要: HR 在线核实四现象(仍拉取 x2 / 核实结论「未核实」/ 失踪 0 波·最近被见到 09-28 07:14)故障取证轮,
> 产出报告 reports/26-10-03-1505 + 档案 26-09-22-backend-partial-hr-verify 追加 + activeContext 切片,
> src/ 零改动。test.full 首跑红 1 条认领链守卫(档案→报告单向), 报告补 doc-refs 反向声明后全绿。
> 基线时间: 2026-10-03 15:37, develop @ 61c0ddc4(先同步合流远端 qB 流量图 P3/P4 + copytext 别名 + 抽屉
> FX-29 软切换等, stash→sync→pop 索引重生成零冲突; 工作区含本轮纯文档回写件)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2408 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 29.6s, rc=0)。
相对上一切片(26-10-03-1431: 2390 passed + 3 skipped / 99%, 13,996 语句 / 127 未覆盖 / 4,728 分支, @ da23e842)
**passed +18** —— 全部来自合流远端提交(qB 口径流量图 P4 端点与回归 + 抽屉切换闪烁修复 + copytext
守阵件), 语句/分支增长同源; 本轮纯文档, 守卫侧唯一增量是报告 doc-refs 反向声明让认领链闭环。
