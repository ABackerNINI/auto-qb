# plans/reports 实施状态清点与漂移审计
> 摘要: 用户令「分析还有哪些 plans/reports 没实施, 列详细表写入报告, 注意文档漂移」。开工快进同步至 b19eb4a 后交叉核对 61 计划 + 13 报告(meta × git log × 代码 grep × task 档案 × 切片)。结论: 计划真实未完成 7(3 完全未开工: tracker-url 脱敏 / .!qB 容忍 / 键盘快捷键; 版本管理拍板后全未动; HR 在线核实只差真机走查; Docker 剩可选 P4; activeContext 冲突治理剩可选 rerere); **已实施但状态漂移 6**(remove-upload-stats fbbd74d / hr-ext-options-style v3.3 / HR 弹窗 T3 08b2a63 + T1/T2 未随定稿翻 Superseded / commands W1–W7 全量); 报告侧 2 份有遗留(iyuu 闭环动作未立项 / hr 审查真机走查)。次级: 7 份 task 档案陈旧 + commands 专题 doc-topic 键分裂 + 版本管理前提过时(0 tag→已有 v0.1.0/v0.2.0)。报告入库 reports/26-09-27-1547-report-docs-implementation-audit.html; **漂移 meta 未代改、issue 未入池**(均待授权)。
> 触发: 实施状态, 漂移, 文档审计, doc-status, 索引, 计划清点, 报告清点
> 最后活动: 2026-09-27 15:47

## 状态

**Done**(审计 + 报告落盘; 无代码改动)。产物: [../reports/26-09-27-1547-report-docs-implementation-audit.html](../reports/26-09-27-1547-report-docs-implementation-audit.html)。
索引已重跑(`commands run kb.index`, 16 个索引); 守卫 + 全量实测 **1700 passed + 1 skipped(TOTAL 91%)** 无回归。

## 待办(下一步从这里接)

1. **漂移修正待授权**(报告 §3/§5 清单): 表 B 六份 meta 翻状态(B1/B2/B3/B6 → Done, B4/B5 → Superseded) + 7 份 task 档案收口 + commands topic 键统一 + remove-upload-stats 切片蒸馏 —— 用户点头后一次做完 + 重跑 kb.index。
2. 报告 §2 表 A 的 7 项真实待办优先级与排期归用户/issue 侧决定(本报告只留证未入池)。

## 取证锚点(复核用)

- 基线 gitee/develop @ b19eb4a; 提交: fbbd74d(remove-upload-stats) · 08b2a63(HR 弹窗 T3) · a06732b(快捷键计划) · 443a785/162c04b/5fe4530(docker 三笔) · 56c04e0(CarPT) · 0f98e7a(commands v2)。
- 代码判据: `src` grep `!qB` 零命中(A3); `webui/static` 无快捷键系统(A1); 无根 CHANGELOG.md / cli 无 --version / pyproject 0.1.0 vs `__init__` 0.2.0(A4); preflight.py 含 merge-tree 而 rerere 未启用(A7)。
