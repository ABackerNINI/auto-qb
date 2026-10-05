# 全项目全面 Code Review 分步实施计划 (full-code-review-plan)

> 摘要: 用户动议对项目做一次全面 code review, 本轮出分步实施计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html)(Open 待拍板)。定性**只读取证**: 评审轮不改码不改文档, 修复另走认领。方案 = 先建「已知问题底册」(issues 38 条 Open + 坑档 7 类 + 在途件 + guards.md 蒸馏, 防重复报告) → 8 批包结构(A 主循环与任务模块 / B1+B2 HR 域 / C 流量采集存储 / D 配置链 / E WebUI 后端 / F1+F2 前端 static / G 规则引擎与种子数据 / H infra+tray+脚本+扩展) 每批一轮走五步序列(读档→坑档对照→逐文件读码→ruff+bandit 提示源→登记去重) → S5 汇总分级二次论证 → S6 报告定稿 + P0/P1 入池。十项维度 R1-R10 从黄金法则与近期事故导出(幂等窗口/保守默认与双入口闸门/单一写线程/fail-fast/时间语义含 epoch 与挂钟上界/错误退避/IO 原子写/安全含 XSS 路径穿越凭据/并发竞态/测试与文档漂移)。发现登记强制三锚(文件+函数+行号)与可达性证据, 不可达不登记为 bug。拍板点 D1-D5: D1 前端 JS 全量拆 F1/F2 两轮、CSS/HTML 仅机制面; D2 extensions+scripts+docker 纳入批 H; D3 引 ruff+bandit 作只读提示源、不引 mypy; D4 P0 也不当场修(保持只读); D5 每批开工 sync + 各批记 HEAD。起点基线 [26-10-05-1002](../testing/baselines/26-10-05-1002-full-code-review-plan.md)(2603+4 / 34.39s / 99%, +14 来自 HR 稳态降频守阵合并非本轮)。在途交叉: reannounce 计划(Open)与 v3 存储报告(待评审)覆盖文件只登记计划未覆盖增量; 评审期间每轮 test.full 数字应持平, 漂移即环境/代码变化信号。
> 最后活动: 2026-10-05 10:02

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html

## 已完成
- 计划产出: 范围底数表(src 33.6k / static 20.5k / issues 38 Open 蒸馏口径) + 十项维度 R1-R10(附判据与事故出处) + 五步评审序列与发现登记格式(ID/维度/P0-P3/三锚/可达性证据/撞车/处置) + S0-S6 门控步骤表(每步有完成判据) + 批次重点矩阵骨架(S1 脚本核对 0 漏 0 重) + 风险对冲 + 非目标(不改码/不评审 memory-bank 与 .commands/不做 UI 审美/不重开 feat-question)。
- 收尾: kb.index 重建(20 生成物, plans 索引已收录) + 基线切片 + 本切片; 拍板点 D1-D5 全部附推荐待用户确认。

## 正在进行
- 待拍板 D1-D5 → 拍板后 S0 开工(建底册 + 报告草稿骨架, 计划转 In Progress)。
