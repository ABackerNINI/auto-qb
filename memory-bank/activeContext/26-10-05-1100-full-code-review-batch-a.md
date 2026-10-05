# 切片 26-10-05-1100 — 全面 Code Review 批 A 评审完成

> 摘要: 计划 26-10-05-0951 S2 的批 A(core 根 + core/modules 除 traffic_sample_mod)评审轮完成;
> 只读取证, 零改码, 发现登记进报告草稿批 A 章节。

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html, memory-bank/reports/26-10-05-1036-report-full-code-review.html

- 评审时 HEAD: `a4d14a8d`(my-commit-flow.sync 成功; 树含评审文档未提交件属正常)
- 范围: 批 A 20 文件 / 5,977 行, **20/20 全部逐文件过目**(LOC 降序, 重点维度 R1 R2 R3 R6 R9)
- 五步执行: 读档(main-loop/taskqueue/core-runtime/core-domain)→ 坑档对照(backend 5 主题)→ 逐文件读码 → ruff+bandit 逐条人工复核 → 登记去重
- **发现 8 条**(P2×1 + P3×7, 全部登记报告草稿批 A 章节):
  - **A-01(P2/R6)** suppress live 旗标异常路径泄漏 — qbmanager `_refresh_torrents` 窗口 arm(:801)到 close(:835)无异常保护, 订阅者异常/added 循环 match 网络异常上抛后, 下一成功轮的 full_round/transitions/两事件相位被整轮吞掉(边沿事件不可重放)
  - A-02(P3)export_torrents_info 裸 open("w") 无编码(cp936 崩溃面, CLI 调试入口可达)
  - A-03(P3/R3)state 两处键无界增长(exec_history 无清理面 / speed_limit_curve 日键)
  - A-04(P3)qbapi pause/resume 与 stop/start 快照同步不对称(当前 WEB 调用面有 P0-5 兜底, 潜伏陷阱)
  - A-05(P3/R7)ops_mod _backup_torrent "wb" 直写(O_TRUNC 守阵 token 面外, 风险低)
  - A-06(P3)rules_mod._handle_rule `handled` 未消费(ruff RUF059 采纳)
  - A-07(P3/R6)托管模式首连循环非 APIConnectionError 异常无节流逐 tick 刷 ERROR
  - A-08(P3/R10)core/__init__.py docstring「旧名单行委托」已随 W3 退役过时
- 工具源: ruff 310 条采纳 1; bandit 3 条全排除(B506 系 BaseLoader 误报); F401(V3Block unused)在 traffic_grid.py:40 **属批 C 范围, 留批 C 核对**
- 底册撞车: A-01 与坑档 suppress-request-vs-live-flag 同族(该坑只覆盖请求位侧); 其余撞车「无」; 无与 37 条 Open issue 撞车的新发现
- **基线哨兵**: 收尾 test.full 首跑 98%(166/139)→ 复跑 99%(164/138)与基线逐位持平; 语句/分支总数两跑均 15511/5342(无代码变更), 首跑差异判定为运行间覆盖抖动, 已记报告批 A 章节
- 待办移交: P0/P1 本批为零; 批 A 无入池急件(A-01 P2 入池建议留给 S5 汇总分流的拍板), 发现表处置建议均已写明
- 状态: 批 A 完成, 下一批 B1(hr/service + model + status)
