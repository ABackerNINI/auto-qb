# 26-10-07-webui-tracker-url-sanitize — tracker URL 源头脱敏（方案 B 实施）

**Status:** Open
**Added:** 2026-10-07
**Updated:** 2026-10-07 00:55
**Topics:** tracker-url-source-sanitize
**Summary:** 方案 B（单轨 + 瞬时原文 + mask 形态）已转成 S1–S4 分步实施计划（26-10-07-0055，基树 20bd2157 重取证），未开工；编排修正：详情 API 收口与删除改道必须同批（拆开会打断移除）。

**Refs:** memory-bank/plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html,memory-bank/plans/26-09-22-1801-tracker-url-source-sanitize-plan.html,memory-bank/activeContext/26-09-23-1915-tracker-url-source-sanitize.md

## 原始请求

用户：「将报告转化为分步实施计划，按方案B：26-09-22-1801-tracker-url-source-sanitize-plan.html」——把可行性报告里已拍板的方案 B（单轨 + 瞬时原文 + mask 形态）落成可开工的分步计划。

## 思考过程与决策

- **现状核验**：报告档 meta「已实施(2026-10-04 复核)」指的是前置日志脱敏（issue 26-09-21-1408，`infra/utils.py:294` 只留主地址形态）已落码；方案 B 四波次本体在 20bd2157 **均未落码**（Facade 纯透传 / 详情 API 透传原文 / 编辑全链路在 / 无 mask 函数）。
- **编排修正（本轮关键发现）**：报告 §07-4「先批 W1+W2」不可执行——W2 让详情 API 只回 mask 值后，前端移除提交的也是 mask 值，而旧 `_cmd_remove_tracker`（commands.py:634）直传 qB（按原文精确匹配），移除必断；编辑弹窗预填 mask 值同样废。⇒ 详情 API 收口 + 删除改道收敛为**原子批**（计划 S3），编辑下线独立先行（S2）。
- **转计划三裁定**：① 新增 `mask_tracker_url()`，日志路径 `sanitize_tracker_url()` 与其测试一行不动；② 批次重排 S1→S4；③ path 末段高熵（≥16 位 `[A-Za-z0-9_-]`）才整段 hash，`announce` 等端点名保留（调和报告示例与「path 末段可能藏凭据」两处表述）。
- **行号漂移**：汇报确认机制 D1–D5 重构（bf12a487）后 runtime 出现第二直读点（:474 后台核实）；计划全部行号按 20bd2157 重取，报告的 fda13cd 行号作废。

## 实现计划

单点 = 计划 HTML §04（S1 源头归一化 → S2 编辑下线 → S3 收口切换（原子）→ S4 守阵 + 红验 + 回写）；mask 规格单点 = 计划 §03 R1–R9；单轨边界（谁能碰原文）= 计划 §03 表。

## 子任务状态表

| # | 批次 | 状态 | 验证门 |
|---|------|------|--------|
| S1 | 源头归一化（mask fn + 槽/Facade 归一 + 单测） | 未开工 | test.quick |
| S2 | 编辑下线（前端 + 路由 + 命令表 + 处理器 + 测试） | 未开工 | test.quick |
| S3 | 收口切换（详情 API mask + 删除改道，原子批） | 未开工 | test.quick + 定向 |
| S4 | 守阵 5 组 + 红验 + conventions 回写 | 未开工 | test.full |

## 进度日志

- 2026-10-07 00:55: 立档。方案 B 分步实施计划产出（`26-10-07-0055-plan-tracker-url-sanitize-planb.html`）：现状取证（含报告行号漂移表与 D1–D5 重构影响）、mask 规格化（R1–R9）、四批文件级改动清单、守阵与红验设计。未开工改码。
