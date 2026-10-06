# WebUI 增量同步(qB rid 式): 可行性 → 实施计划

> 摘要: 专题两轮。①可行性轮(02:04): 判定**可行且地基厚** —— /api/state 已是 qB rid 的
> 「跳过」半套(rid 命中零回传), 缺「变化回增量」半套; 摄入侧 store.apply_sync 今天就在跑
> 同款协议客户端, 而 delta_fields 每拍算出后在视图层门口被塌缩成布尔丢弃, 方案落点是把
> 这份信息接住。报告
> [26-10-07-0204](../reports/26-10-07-0204-report-webui-delta-sync-feasibility.html)。
> ②计划轮(04:38): 先源码级调研 qB rid 实现 —— **双指针 ack 协议**(lastSentID/acceptedID +
> 快照与待确认值缓冲)、变化种子只发改动字段、`*_removed` 累积到确认为止、客户端从不清
> rid 全靠服务端 full_update 兜底, 提炼避坑 5 条; 发现**报告 4 处与 qB 源码出入**(deque
> 窗口只存键系自创改进而非「qB 同款」等)。盘点报告方案到仓库触点: 服务端 4 件全收
> WebUIRuntime / 前端 3 件 / 拍板点 5 个, 另新发现两缺口(store 不持久化 added/removed、
> 剧侧无 member_to_key 等价映射)。实施计划
> [26-10-07-0414](../plans/26-10-07-0414-plan-webui-delta-sync.html) 已出(doc-status **Open
> 待拍板**): S0-S10 四里程碑(地基与协议→前端与守阵→增量重聚合→收尾), 拍板点 P-01..P-05
> 全带推荐案, 设计规则 R1-R12, 每步独立提交/回滚。认领链双向闭环, kb.check 全绿。
> ③排版修复轮(10-07): 计划 HTML 的 `.sheet` 两列 grid 把 nav/header/7 个 section 逐个
> 自动填进格子, 正文各节轮流掉进 216px 窄目录列(表格挤乱、sticky 目录叠正文)—— 正文包进
> `.main` 容器让 grid 只剩两子元素, `code` 加 `overflow-wrap:anywhere` 断长路径; 无头
> 浏览器四点截图(顶部/S0 表格/S2/页尾)复验通过。
> 最后活动: 2026-10-07 04:56

**Refs:** memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md, memory-bank/reports/26-10-07-0204-report-webui-delta-sync-feasibility.html, memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html, memory-bank/testing/baselines/26-10-07-0204-webui-delta-sync-feasibility.md, memory-bank/testing/baselines/26-10-07-0438-webui-delta-sync-plan.md

## 未闭环

- 计划 Open 待拍板: P-01..P-05 待用户逐项拍板后按 S0-S10 分步派工实施(每步一个独立工作单元, 独立提交/回滚)。
- 实施开工 S0 重立 test.full 基线(计划 26-10-07-0414 实施纪律段); 中间调研笔记在仓库外 `_planwork-webui-delta/`(01 调研 / 02 对表 / 03 内容稿), 供各步实施子智能体取用。
