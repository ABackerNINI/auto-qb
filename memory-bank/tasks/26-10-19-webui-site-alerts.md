# 26-10-19-webui-site-alerts — WEBUI 站点列状态提醒与逐目标汇报回执

**Status:** Done
**Added:** 2026-10-19
**Updated:** 2026-10-19
**Summary:** 站点 chip 内开两个图标槽(左 = 持久健康: 缺站点配置 / tracker 报错; 右 = 临时命令结果: 进行中 / 成功 / 推迟·未确认 / 失败); 判定与取数全在后端单点(统一 tracker 健康取数器 + 墙钟去抖), 汇报回执带出逐 hash 结果
**Topics:** webui-site-alerts
**Refs:** memory-bank/plans/26-10-19-2007-plan-webui-site-alerts.html

## 原始请求

1. 实施 P0: `memory-bank/plans/26-10-19-2007-plan-webui-site-alerts.html`。
2. 相关配置在 `D:\Projects\auto-qb\config.yml`(生产实例), **只读验证** —— 只借它的 qB 连接参数做 S0 真机标定, 不改该 clone 的任何文件。

## 思考过程与决策

计划 §06 的 11 项拍板(D1-D11)全部沿用, 实施中未出现需要就地决定的新取舍。落地时补齐的三处判断:

- **去抖窗口独立成常量** `TRACKER_DEBOUNCE_WINDOW = 30s`: `TRACKER_SUSPECT_TTL` 管"多久复查一次"(调度), 窗口管"满多久才认"(判据)。混成一个常量会让"复查间隔"与"确认窗口"永远绑死, 调其中一个必然误伤另一个。
- **取数函数返回三态** `None / "" / 文本`: 计划 S1 要求"取数失败不动现值", 而原 `_fetch_tracker_error` 用空串同时表示"无报错"和"取不到" —— 直接复用会把 qB 抖动翻译成"站点已恢复"(图标灭掉)。这是计划没写、但不改就违背其验收口径的一处。
- **暂停/其它态保留健康态**: 计划只说"跳过不扫描"。跳过取数 ≠ 清空结论 —— 没有新观测时不拿"没看"当成"好了"; 展示原因(`tracker_error_msg`)仍照旧在离开 error 态时清空(那是"这个种子的错误", 状态一变即失效)。

S0 标定结论: 生产 qB 5.2.3 / 151 种子库, 裸 keep-alive 连发 50 次 `/torrents/trackers` —— 均值 0.38ms / P95 0.53ms; 20 条/轮 ≈ 7.5ms = 1.5s tick 的 0.5%, 远低于 R2 的 5% 触发线 ⇒ 预算与 TTL 按计划原值定死。

## 实现计划

计划 §04 的 S0-S7 七步, 每步一个可验单元:

- S0 锚点复验 + 真机标定(不改代码)
- S1 数据层: 记录字段 + 统一取数器 `refresh_tracker_health`
- S2 视图字段 `site_alert` / `site_alert_msg` + 行级脏接线
- S3 站点 chip 左槽图标(三视图 + 三皮肤 + 装饰指纹)
- S4 状态列错误图标呼吸动画
- S5 回执契约 `truth.results`
- S6 右槽命令结果图标
- S7 收口(全量测试 / 基线 / 文档回写)

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 锚点复验 + 真机标定(均值 0.38ms / P95 0.53ms; 预算 20 与 TTL 600 定死, 不触发 R2) | Done(2026-10-19) |
| S1 | `record.py` 三个健康字段; `views.py` 统一取数器(扫描范围 / 四档 TTL / 预算分桶 / 墙钟去抖); `ERROR_REASON_BUDGET` 退役 | Done(2026-10-19) |
| S2 | `_member_view` / 搜索 `_view` 加 `site_alert` + `site_alert_msg`; 复用 `note_error_reason_hashes` 行级登记 | Done(2026-10-19) |
| S3 | `xtpl-cells.html` 三处站点 cell 双槽; 三皮肤 `.sa`/`.sx` 规则; `decorate.js` 指纹纳入新字段 | Done(2026-10-19) |
| S4 | `.g-status.k-error .ico` 复用 `dot-pulse` 呼吸 + `prefers-reduced-motion` 降级 | Done(2026-10-19) |
| S5 | `runtime.check_pending` 聚合带出 `truth.results`(文案逐字不变) | Done(2026-10-19) |
| S6 | `state.js::alertIcons` + `commands.js::setRowIcon`; `_actCore` job 带目标标识、按 `truth.results` 逐 hash 落终态、truth 缺失统一落 warn | Done(2026-10-19) |
| S7 | 全量测试 / 基线切片 / 文档回写(modules + systemPatterns + static-contract) / 计划转 Done | Done(2026-10-19) |

## 进度日志

### R0 · 立档 (2026-10-19)

第一阶段(S0-S7)一次做完并收口。新增单测 6 条 + delta 行级归约 1 条 + 回执契约 1 条 + 静态守阵 1 条 + e2e `e2e/site-alerts.spec.mjs`(两皮肤 × 左槽/右槽, 含"3 目标 1 被拒"部分失败场景); 全量测试与覆盖率见 `kb.baseline`。

桩侧配套: `scripts/ui_harness.py` 新增 `--site-alert`(默认 on)注入两态, 命令泵对 reannounce 回执带 `truth.results`(与后端同形), 使"部分失败可定位"在 e2e 可复现。

- 2026-10-19 21:24 S0-S7 实施完成: 统一 tracker 健康取数器 + 站点 chip 两槽图标 + 逐目标回执; 计划转 Done, 已立档
