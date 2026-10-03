# 26-10-03-webui-qb-traffic-charts — WebUI qB 口径流量图可行性分析

**Status:** Open
**Added:** 2026-10-03
**Updated:** 2026-10-03
**Summary:** 为 WebUI 新增 3 种仅展示的 qB 口径流量图 (全局实时/单种子/辅种分组) 调研成熟方案并出可行性报告 26-10-03-0757 (13 节 dark 单文件, 主 issue 26-09-27-1248 本轮范围收窄为纯展示、不恢复 condition): 可行性高 —— 三图实时值已随主循环 1.5s 增量同步在内存 (种子级 uploaded/downloaded + server_state + _build_group_view 组级聚合), 零新增 qB 请求; 推荐方案A (internal 全局任务 30-60s 采样 + 内存环 24h@30s + 小时 rollup 30 天落 state.json, v3→v4 纯加法) + uPlot vendor 单文件; 单种 uploaded/downloaded 为 all-time 口径随 fastresume 跨 qB 重启持久 (源码级证据, 报告留 5 条待真机验证清单); 方案 B (纯前端不落盘) 判不满足需求, 方案 C (每组 dat 文件) 与 state_file 黄金法则有张力。主会话只委派, 4 个子智能体串行 (代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写) 全部一次成功 0 异常失败。**用户拍板 (2026-10-03): 先不实施 (P1-P5 五阶段方案保留待启动); 前端定 uPlot; 采样间隔/保留窗口做成可配置项 (新键须进 validate_config + config/schema.py); 停机空洞表达与分组换 key 旧历史策略之后决定。拍板记录已回写报告 §08。**

**Topics:** torrent-traffic-stats

## 原始请求

用户指令: 为 WebUI 新增 3 种仅展示的 qB 口径流量图 —— 全局实时 / 单种子 / 辅种分组 —— 调研成熟方案并出可行性报告。主 issue `26-09-27-1248-feat-stats-redesign-torrent-traffic` (Open, 单种统计重设计), 本轮范围收窄为**纯展示、不恢复 condition**; 相关 issue `26-10-01-2138-question-webui-traffic-history-chart` (Dropped, 混淆了 Traffic Monitor 全局与 qB 流量)。工作方式: 主会话只委派不实施, 子智能体分阶段串行; 收尾按 memory-bank DoD 回写 (禁止 git 写操作)。

## 思考过程与决策

- **四子智能体串行委派** (主会话只委派): 代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写, 全部一次成功 0 异常失败。
- **可行性核心发现**: 三图实时值已随主循环 1.5s 增量同步在内存 —— 种子级 uploaded/downloaded + server_state + `_build_group_view` 组级聚合, **零新增 qB 请求**; 缺的只是历史序列的采样与存储。
- **方案裁决**: 方案 A (internal 全局任务 30-60s 采样 + 内存环 24h@30s + 小时 rollup 30 天落 state.json, v3→v4 纯加法) 推荐; 方案 B (纯前端不落盘) 判不满足需求; 方案 C (每组 dat 文件) 与 state_file 黄金法则 (状态统一进 state_file) 有张力。前端选型 uPlot (vendor 单文件, 与仓库单文件交付约束相容)。
- **口径发现**: 单种 uploaded/downloaded 为 **all-time 口径**、随 fastresume 跨 qB 重启持久 (源码级证据); 报告留 5 条待真机验证清单 (P5 前置)。
- **用户拍板 4 项** (2026-10-03, 已回写报告 §08): ① 先不实施 (P1-P5 五阶段方案保留待启动); ② 前端定 uPlot; ③ 采样间隔/保留窗口做成**可配置项** (新键须进 validate_config + 同步 config/schema.py, 黄金法则 #4); ④ 停机空洞表达 (null 断线 vs 补0) 与分组换 key 旧历史策略**之后决定**。
- **本档案不声明 `**Refs:**`**: 报告出厂冻结且本轮可改文件清单不含报告/issue 的 doc-refs meta, 单向声明会触发认领链守卫「目标未反向声明本件」; 三件制品 (issue ↔ 报告 ↔ 本档案) 由同键 `torrent-traffic-stats` 在 doc-map 专题视图归组, 正文链接不构成声明 (check_claim_chain 只扫声明方)。

## 实现计划

报告 P1-P5 五阶段 (各段独立可提交), 全部待启动:

- **P1 采样管线**: internal 全局任务 30-60s 采样, 间隔可配置 (新键进 validate_config + config/schema.py)。
- **P2 state v4**: 内存环 24h@30s + 小时 rollup 30 天落 state.json, schema v3→v4 纯加法迁移。
- **P3 API + 金清单**: 历史序列查询端点 + 黄金清单验证。
- **P4 前端三图**: uPlot vendor 单文件, 全局实时/单种子/辅种分组三图接线。
- **P5 真机收尾**: 报告 5 条待真机验证清单逐项核验。

前置 (**实施前补拍板**): ① 停机空洞表达 (null 断线 vs 补0); ② 分组换 key 旧历史策略。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| ① 代码盘点 | 三图数据源盘点 (内存已有实时值 / 主循环 1.5s 增量同步 / 组级聚合) | 完成(26-10-03) |
| ② 外部调研 | 成熟方案调研与三方案选型 (A/B/C) + 前端库选型 (uPlot) | 完成(26-10-03) |
| ③ 报告撰写 | reports/26-10-03-0757 (13 节 dark 单文件) + reports/_index.md 登记 | 完成(26-10-03) |
| ④ 拍板记录回写 | 用户拍板 4 项回写报告 §08 | 完成(26-10-03) |
| ⑤ 收尾回写 | 立档 + activeContext 切片 + 主 issue 补状态日志 + kb.index + test.full | 完成(26-10-03) |
| ⑥ P1 采样管线 | internal 全局任务 30-60s 采样 (间隔可配置) | pending |
| ⑦ P2 state v4 | 内存环 24h@30s + 小时 rollup 30 天落 state.json (v3→v4 纯加法) | pending |
| ⑧ P3 API+金清单 | 历史序列查询端点 + 黄金清单验证 | pending |
| ⑨ P4 前端三图 | uPlot vendor 单文件, 三图接线 | pending |
| ⑩ P5 真机收尾 | 报告 5 条待真机验证清单逐项核验 | pending |

> ⑥-⑩ 共同前置: 实施前补两个拍板 —— 停机空洞表达 (null 断线 vs 补0) / 分组换 key 旧历史策略; 采样间隔与保留窗口的可配置键设计须过 validate_config + config/schema.py。

## 进度日志

- **2026-10-03 可行性报告轮**: 主会话只委派, 4 个子智能体串行 (代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写) 全部一次成功 0 异常失败。取证基线 c91be940, 收尾前已同步至 dd180a11。产出 `memory-bank/reports/26-10-03-0757-report-qb-traffic-charts.html` (13 节 dark 单文件, 58.1KB) + `reports/_index.md` 登记行 (专题 torrent-traffic-stats)。核心结论: 可行性高 —— 零新增 qB 请求; 推荐方案A + uPlot; 方案 B 判不满足需求, 方案 C 与 state_file 黄金法则有张力。
- **2026-10-03 拍板与收尾**: 用户拍板 4 项 (先不实施 / uPlot / 采样间隔与保留窗口可配置 / 两项策略后定), 拍板记录回写报告 §08。立档 (阈值 #4 命中: 已产出 reports/ HTML 制品) + activeContext 切片 + 主 issue 26-09-27-1248 补状态变更日志行 (状态保持 Open) + `kb.index` 重建。**零代码改动, docs-only 豁免新建基线切片** (依据: 同型先例 26-10-03-webui-delete-tag-scope-confusion「无代码变更沿用最近基线」; test.full 数字记本段, 基线事实源仍走 `kb.baseline` 不手抄): test.full 实测 (2026-10-03 08:47 单次采样) **2325 passed / 3 skipped / 31.30s**, 覆盖率 TOTAL **99%** (13531 语句 / 88 未覆盖 / 4542 分支 / 89 partial); `kb.index` 幂等重跑 7 个再生索引字节一致。
