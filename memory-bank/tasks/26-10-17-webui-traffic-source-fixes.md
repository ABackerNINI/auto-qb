# 26-10-17-webui-traffic-source-fixes — 全局流量来源联动缺陷修复 (Phase 1)

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-17
**Summary:** 修掉「全局流量来源」联动上线后暴露的 9 个缺陷；新增顶层 `traffic_source.enabled` 总开关（关闭＝停取数/停订阅/停自动拉起，修订 0339-D1）；工具参数单位改下拉＋`?` 并统一为 `30S`/`10MiB` 复合串；快照解耦与设置页合并卡另立 Phase 2。
**Topics:** webui-traffic-source-fixes

## 原始请求

用户逐条列出 9 个问题（原话）：

1. 拉起后有黑框，需要改为后台运行。
2. webui 需添加关闭工具按钮。
3. 数据来源选择 Traffic Monitor 文件时，下方仍显示工具状态与工具参数。
4. 工具状态页面的"已就绪"是灰色。
5. 工具状态页面标题与内容文字未对齐。
6. 工具状态页面"打开工具设置"显示 `{"error": "invalid token"}`。
7. 选择"整机流量监视器"保存后，历史流量图仍显示 Traffic Monitor 的数据，一段时间后恢复，猜测可能与 10 分钟刷新有关。
8. 选择"整机流量监视器"保存后再换回"Traffic Monitor 文件"保存后，流量历史图不显示。
9. 工具参数设置中需按惯例把文件大小/时间单位改为下拉框，同时加 `?` 解释。

相关文档：`26-10-17-0339-plan-global-traffic-source-integration.html`。要求：**先 grilling，再写分步修复计划**。

## 思考过程与决策

- **计划**：`memory-bank/plans/26-10-17-1737-plan-global-traffic-source-integration-fixes.html`（Phase 1），拍板 D1–D15；Phase 2（快照解耦＋合并卡）方向 P1–P3 亦记录在同计划 §06。
- **总开关改判（D1，修订 0339-D1）**：用户把"关闭工具"从"切回 `provider=traffic_monitor`"改判为**新增顶层 `traffic_source.enabled` 总开关** —— 关闭＝停取数/停订阅/停自动拉起，`provider` 不变。一处字段同时满足"关工具"与"关数据来源功能"，并根除"停完又被订阅线程拉回"。
- **依赖处置（D2/D5/D6）**：闸门落在取数单点 `paths.dat_path/unavailable_reason` + `tool_client._desired` + `agent.ensure_running`；曲线走**运行期闸门**（发 `off` 快照），**不写盘**改 `global_speed_limit_curve.enabled`；expr 取不到**明确报错**（不静默当 0）。
- **关闭必提醒（D3/D4）**：确认框列出受影响功能，清单来自 schema 字段依赖元数据；次序＝先保存 `enabled=false` → 再 `POST /shutdown`。
- **单位惯例（D12/D13）**：工具参数改用项目既有 `hub-field` 的 `time`/`size`（数值＋单位下拉＋`?`），格式**统一为复合串**（`30S`/`10MiB`），工具侧新增同文法解析单点、读侧兼容旧数值一次性迁移。
- **关键澄清事实**：流量快照的**唯一发布者就是「限速曲线」模块**（`_publish_traffic → ctx.web.set_traffic_view`）——这既解释了 #7/#8 的"≈10 分钟"节拍，也决定了依赖提示要"两侧互指"。
- **分期（D15）**：9 项修复与重构解耦，Phase 1 先行可独立验收；Phase 2 另立计划。

## 实现计划

分 8 步（每步独立可验，落点与验收判据见计划 §04）：

- **S1** `traffic_source.enabled` 字段契约（models / schema / schema.py / validate_config / loaders）。
- **S2** 取数闸门 + `off` 快照态 + expr 文案（paths / tool_client / agent / speed_curve_mod / expr env / 前端灰显）。
- **S3** 工具侧 `POST /shutdown` + auto-qb 代理端点。
- **S4** 「关闭工具」按钮 + 确认框 + 依赖元数据。
- **S5** 去黑框（`CREATE_NO_WINDOW` + 启动器优先 `pythonw.exe`）。
- **S6** 设置页四修（整块隐藏 / `on→ok` / 行对齐 / 删「打开工具设置」）。
- **S7** 工具参数改 `hub-field` + 工具侧 units 解析 + 统一复合串 + 迁移。
- **S8** 切源即刷新（#7/#8）+ #8 真机复现取证。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | `traffic_source.enabled` 字段契约 | Open |
| S2 | 取数闸门 + `off` 快照态 + expr 文案 | Open |
| S3 | 工具侧 `POST /shutdown` + auto-qb 代理 | Open |
| S4 | 「关闭工具」按钮 + 确认框 + 依赖元数据 | Open |
| S5 | 去黑框 | Open |
| S6 | 设置页四修 | Open |
| S7 | 工具参数 `hub-field` + 工具侧 units + 统一格式 | Open |
| S8 | 切源即刷新（#7/#8）+ #8 真机复现 | Open |

## 进度日志

### R0 · 立档 (2026-10-17)

grilling 六轮收敛（用户逐条订正，含两次纠正字段落点），落盘 Phase 1 修复计划；据此在 0339 计划就地记 R3 变更行（D1 修订 + §05 盘上格式改复合串）；立本档（命中阈值 4：已产出计划文档）。本轮仅产出文档、未改代码。

- 2026-10-17 17:42 grilling 六轮收敛并落盘 Phase 1 修复计划；新增顶层 traffic_source.enabled 总开关(修订 0339-D1)；0339 记 R3
