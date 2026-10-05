# 全面 Code Review · 批 C 完成 (流量采集与存储三件: traffic_store / traffic_sample_mod / traffic_grid)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 C 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点同 commit。3 文件 / 2,889 行 (1263+1096+530) 全部逐文件过目, 重点维度 R3 R5 R7 逐文件勾选; 先读 v3 存储报告 26-10-04-1730 全文对齐覆盖面, 发现逐条标注 v3 关系。发现 5 条 (P2 ×1 + P3 ×4): C-01 earliest_hour 只在启动恢复初始化 —— 运行期新建系列的 agg hour 行永不受 rollup_window 裁剪 (无界增长到重启, P2) · C-02 traffic_store `_parse_int_field` 逐字重复定义 (:106/:116, ruff F811 盲区) · C-03 traffic_grid F401 `V3Block` (批 A 移交线索核对属实) · C-04 v2 坏行隔离 (.corrupt) 在 v3 退役且 bad_lines 系计数全仓零消费方, 与 v3 报告 §5.7「沿用」表述漂移 · C-05 hour 桶 UTC 整小时对齐 vs day/month 本地日界 (半小时时区错位, 备查)。复验不登记 6 项 (live_tail interval_s 旧值微观漂移 / 零样本接 n 游程单槽丢失系明文设计 / evict 单系列 listdir 失败兜底 / trim 孤儿 .tmp 不入数据门 / torn_tail 索引坐标系恒等 / 活尾竞态去重镜像成立)。R4 顺带核验: flush_interval 已进 validate_config + schema 键面。工具源: ruff 87 条采纳 1 (F401); bandit 0 条。test.full 2610+4 / 99% 与基线逐位持平。发现表落盘 [报告草稿批 C 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 11:50

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · memory-bank/reports/26-10-04-1730-report-qb-traffic-storage-v3.html · 前序切片 [批 A](26-10-05-1100-full-code-review-batch-a.md) · [批 B1](26-10-05-1130-full-code-review-batch-b1.md) · [批 B2](26-10-05-1135-full-code-review-batch-b2.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档 v3 报告 + 包 docstring → 坑档 backend 五主题 → LOC 降序逐文件读码 → ruff+bandit 逐条复核 → 登记去重)。
- 发现表 5 条回填报告草稿批 C 章节 (含逐文件勾选结论 3/3 / 复验不登记项 / 工具源小结 / R4 顺带核验; 每条带 v3 关系标注)。
- test.full: 2610 passed + 4 skipped / 99% (15511/5342, 164/138) 与基线切片逐位持平, 无漂移。

## 遗留 / 待办

- C-01 (P2) 建议尽早入池: 全新安装 global 系列 / 运行期新增种子 / 热重载启用 qb_traffic 三个场景 hour 保留窗契约失效, 长驻进程下 agg 读放大无界涨 (~1 年触 ~1MB 快读口径)。
- C-04 的处置二选一 (补坏行计数消费方 vs 按代码现状收窄 docstring) 需拍板, 随入池时定; v3 报告出厂冻结, 漂移以代码为准。
- 剩余批次: D (config) / E (webui, 先读 reannounce 计划) / F1 / F2 / G / H。
