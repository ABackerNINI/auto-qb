# 全仓重复代码审查 · 轮 11–14(hr 全包)

> 摘要: 用户「做 Phase 1 hr 部分」→ 按计划 `26-10-10-2333` 执行 **Phase 1 后端 hr 包 = 轮 11–14**(解析面 / 判定与序列化 / 运行面 A service / 运行面 B runtime·worker·store·channel·server·report 等, ~6.8k 行 / 23 文件)。**纯审查轮, 零源码改动**: 滚动报告 `26-10-11-0033` 追加 §14–§17 + 累计计数 §18; hr 29 项发现(A12/B1/C7/D9), 全局累计 98 项(A38/B8/C24/D28); 入池 **hr 9 条 refactor issue**(专题 `dup-code-audit`, 均 Open 未认领)。复核已知 issue `26-10-02-0441`(`_prune_index` 同体重复)已消除。S2 提名实测: pylint R0801 对 hr 收 2 组(1 组为误报型重导出、1 组即展示 DTO 镜像)、jscpd python 0 clone —— 与 config/core 同结论。
> 最后活动: 2026-10-11 02:40

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## 正在进行

- **轮 11–14(hr 全包)已完成**(纯审查轮, 零源码改动)。滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 已追加 R11–R14(§14–§17)+ 累计计数/候选排序(§18); hr 计数 A12/B1/C7/D9, 全局累计 98(A38/B8/C24/D28)。
- **hr 9 条 refactor issue 已入池**(均 Open, 未认领): `hr-adapter-parse-boilerplate-dup` / `hr-model-serialize-helper-dup` / `hr-lane-transition-boilerplate-dup` / `hr-warn-dedup-throttle-dup` / `hr-report-cli-boilerplate-dup` / `hr-store-recover-lock-family-dup` / `hr-token-persist-convention-dup` / `hr-site-derive-convention-dup` / `hr-thread-lifecycle-boilerplate-dup`。
- **下一轮候选**: Phase 1 后端轮 15(webui/server: factory·context·auth·lifecycle·common·static_ui·traffic_qb + routes/*); 或按用户偏好调整顺序。每轮开工另立会话, 按 S1–S6 走。

## 关键结论(供后续执行参考)

- **hr 字面重复同样极低**: pylint R0801(=6) 仅 2 组、jscpd python 0 clone。**hr 的重复以「样板骨架」为主** —— 档位状态机处置(3 处)、告警去重一次(3 方法)、波级异常收尾(3 分支)、CLI 入口(3 处)、model 序列化(9 dataclass)。
- **A 类重灾(可提取, 收益高/风险低)**: `parse_counters` 逐字同(R11-A01); model 的 to_json/from_json 字段样板(R12-M01, 注意 HrLaneState 判空 / HrSiteData writer 两特例); service 内三组骨架(R13-S02/S03/S04); report 三入口 + `_scope_of` 双份 + `stamp_text_ts` 死件(R14-RP01/02/03); 线程生命周期(R14-T05)。
- **C 类(同一事实多表示, 优先)**: ① **token 生成/持久化口径** hr/channel ↔ webui/server/common **逐字同**(R14-T01); ② **「接入 hr_check 的站点」派生** runtime ↔ report 逐字同 + webui routes/hr 四处同口径(R14-S01); ③ **读坏→.bak→quarantine→写回自愈恢复链两套** hr/store ↔ core/state, 且 infra/locking 单点未被 hr/store 使用(R14-T02, 归轮 18); ④ 告警节流窗口口径分散 4 处(R14-T03); ⑤ URL 分解口径(R14-T04); ⑥ hr 单位表 ↔ 跨包(R11-C01)。
- **B 类(只登记, 不急合)**: 各档摘要串两套 service ↔ status, 文案已分叉 `(全深度)` vs `(全)`(R13-S01)。
- **D 类(明确不动)**: model→status 展示 DTO 镜像层(刻意分层, 契约「前端只展示不重算」, R12-D01); CLI 表格对齐工具 `_dwidth/_pad/_ellipsis`(**全仓单点** —— 计划预判「与 infra 表格工具重复」不成立, R14-D01); HTTP 头解析 `_header`(单点); `HrTaskQueue`(单点)。
- **既有 issue 复核**: `26-10-02-0441`(`HrRefreshService._prune_index` 与模块级同名同体)**已消除** —— 现为模块级单点(R13-D02)。

## 后续候选(未开工)

- 轮 15–19(webui / rules / infra / torrents+tray)、Phase 2 前端(20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(26)。
- 轮 26 汇总: 重构候选排序表(报告 §18 已有雏形)+ 跨层「同一事实」总账 + 未入池候选(hr 单位口径 R11-C01 / URL 分解 R14-T04 / 档位谓词 R12-S01, 及 config/core 遗留项)按清偿顺序入池。