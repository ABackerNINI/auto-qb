# 26-10-01-backend-transmission-compat — 兼容 Transmission 可行性分析

**Status:** In Progress
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** 认领 issue 26-10-01-2212(question · 兼容 Transmission 可行性分析): 先查重确认无同类报告, 再做 qB 耦合面全量盘点并出可行性报告 26-10-01-2347(结论: 技术可行性中 / 业务可行性低 / 全量 38-58 人日 / 建议暂不做, 若做只做 8-12 人日的最小只读子集)。issue 改 In Progress 并建三方认领链(issue ↔ 报告 ↔ 本档案)。**停在拍板: 结论「暂不做(Dropped 候选)」待用户拍板后定 issue 终态。**

**Topics:** transmission-compat-feasibility

**Refs:** memory-bank/issues/26-10-01-2212-question-transmission-compat-feasibility.html,memory-bank/reports/26-10-01-2347-report-transmission-compat-feasibility.html

## 原始请求

用户指令「认领issue: 兼容 Transmission 可行性分析, 产出报告, 做之前查看是否已有此类分析报告」, 对应 issue [26-10-01-2212](../issues/26-10-01-2212-question-transmission-compat-feasibility.html)(来源 TODO.md L216 原文「(需要可行性分析) 兼容tr」)。三个动作: ①查重 ②认领 ③出可行性报告。

## 思考过程与决策

- **查重先行(用户显式要求)**: 全仓 grep `transmission` 仅 2 命中(issue 本体 + `_index.md` 登记行); `多后端 / 后端抽象 / tr 后端` 零命中; `reports/_index.md` 现役 21 份无同类主题; `doc-topic` 主键此前仅 issue 声明。**结论: 此前不存在同类分析报告, 本报告是该专题第一份制品** —— issue 里「qB client 抽象面: 待查」一栏由本报告填平。
- **结论落在报告, 不落在本档案**: 报告是快照(report 恒 Done, 出厂即冻结), 本档案只记执行过程与待拍板事项; 重开条件触发时应新建 plan 引用报告, 不回头改报告。
- **一个修正了直觉的发现**: 起手假设「tr 完全不支持跳检 → 能力缺失 → 不可行」。查 tr 官方 RPC spec 与 4.0/4.1 变更日志后修正为 —— tr 4.0+ 有 `torrent-added-verify-mode: fast`(默认) 可**条件跳过**完整校验, 跳过条件(文件存在/大小匹配/mtime 早于添加时刻/首片校验通过)与 auto-qb 自己的跳检前置 filelist 检查同向。故判定从「不可行」改为「可行但核心能力从确定性降级为启发式」, 这才是建议不做的真正理由。
- **认领链三方互链**: 报告 ↔ issue ↔ 本档案 双向 `doc-refs` / `**Refs:**`, 交由 `test_docs_forms.py::test_claim_chain_is_bidirectional` 机械校验(声明即义务)。

## 实现计划

无实施计划 —— 本轮是可行性分析, 零代码变更(范围守恒: 计划外不改码)。结论若为「做」应转计划文档, 不走 issue 实施。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| ① 查重 | 确认无同类分析报告 | 完成(26-10-01) |
| ② 耦合面盘点 | qB 耦合面全量盘点(端点/类型面/配置/前端/测试) | 完成(26-10-01) |
| ③ 出报告 | reports/26-10-01-2347(11 节 + 附录端点映射表) | 完成(26-10-01) |
| ④ 认领与收尾 | 立档 + issue 改 In Progress + 三方认领链 + 重建索引 + 闸门 | 完成(26-10-01, 2026-10-04 复核追认: 立档/认领链/索引/闸门均在当日进度日志内确已执行) |
| ⑤ 拍板 | 结论「暂不做(Dropped 候选)」待用户拍板 → 定 issue 终态 | 未开始 |

## 进度日志

- **2026-10-01 认领 + 报告轮**: 同步 826f25e6 后开工。查重确认无同类报告; 拉取 qB 耦合面盘点(src 123 .py / 28,401 LOC; qbapi.py 49 端点调用点 / 49 个不同方法; 46/123 文件带 qB 痕迹; TorrentRecord 70 个槽名逐字等于 qB 字段名且无翻译层; hash 主键符号横跨 35 文件; 前端 29 JS / 10,742 LOC 直吃 qB 字段名; 规则 DSL 暴露 70 个 `tor.*` + 7 个 `is_*` 属已发布对外契约; 测试 917/1697 函数依赖 qB 替身; `infra/file_access.py` 是唯一干净解耦项)。逐项核验关键论断: `ops_mod.py:415` `is_skip_checking=True`、`ops_mod.py:295` `torrents_export`、`record.py:7` import TorrentState、全仓 `downloader|client_type|backend_type` 零命中。出报告 26-10-01-2347, 结论: 技术可行性中 / 业务可行性低 / 全量 38-58 人日(最小只读子集 8-12 人日) / 建议暂不做, 三条重开条件已写明。
- **2026-10-01 立档与收尾回写**: 按立档阈值 #4(已产出 reports/ HTML 制品)立档, 阈值明文命中不得跳过; issue 状态 Open → In Progress 并补 doc-refs; 建三方认领链; 重跑 gen_issues_index.py 与 kb.index; test.full 闸门。
