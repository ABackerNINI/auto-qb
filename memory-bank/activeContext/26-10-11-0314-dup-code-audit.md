# 全仓重复代码审查 · 轮 15–16(webui 全包)

> 摘要: 用户「做 Phase 1 webui 部分」→ 按计划 `26-10-10-2333` 执行 **Phase 1 后端 webui 包 = 轮 15–16**(轮 15 路由层 factory·context·auth·lifecycle·common·static_ui·traffic_qb + routes/*, ~2282 行 · 20 文件; 轮 16 表现层 runtime·views·commands·module, ~3851 行 · 4 文件)。**纯审查轮, 零源码改动**: 滚动报告 `26-10-11-0033` 追加 §18–§19 + 累计计数 §20 + issue 表 §21; webui 24 项发现(A9/B2/C7/D6), 全局累计 122 项(A47/B10/C31/D34); 入池 **webui 10 条 refactor issue**(专题 `dup-code-audit`, 均 Open 未认领)。S2 提名实测: pylint R0801(=6) 对 webui 0 命中、jscpd python 0 clone —— 与 config/core/hr 同结论。
> 最后活动: 2026-10-11 03:14

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## 正在进行

- **轮 15–16(webui 全包)已完成**(纯审查轮, 零源码改动)。滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 已追加 R15/R16(§18–§19)+ 累计计数/候选排序(§20)+ issue 表(§21); webui 计数 A9/B2/C7/D6, 全局累计 122(A47/B10/C31/D34)。
- **webui 10 条 refactor issue 已入池**(均 Open, 未认领): `webui-route-cmd-boilerplate-dup` / `webui-status-payload-dup` / `webui-hr-route-guard-dup` / `webui-sidecar-dir-convention-dup` / `webui-partial-publish-merge-dup` / `webui-cmd-pair-handlers-dup` / `webui-bulk-receipt-boilerplate-dup` / `webui-virtual-tracker-prefix-dup` / `webui-seed-view-restate-dup` / `webui-cross-layer-constant-convention-dup`。
- **下一轮候选**: Phase 1 后端轮 17(rules/); 或按用户偏好调整顺序。每轮开工另立会话, 按 S1–S6 走。

## 关键结论(供后续执行参考)

- **webui 字面重复同样极低**: pylint R0801(=6) 0 命中、jscpd python 0 clone。**webui 的重复以「路由/命令样板骨架」与「跨层常量多表示」为主**。
- **A 类重灾(可提取, 收益高/风险低)**: ① 路由命令透传 handler **成对逐字同**(pause/resume、create/edit category、tags、speed override/alt)+ 11 份 `build_router` 头样板(R15-A01); ② `runtime._publish_partial_locked` 四段同骨架「重建脏行→保留未脏→追加」(R16-A01, 核心热路径, 需 S5 镜子); ③ commands.py 成对 `_cmd_*`(R16-A02); ④ `_bulk_recheck_via_ops`↔`_bulk_skip_check_via_ops` 聚合回执骨架 + `check_pending`↔`_advance_reannounce_background` 判定骨架(R16-A03/A04); ⑤ status 子字典双份(R15-A02); ⑥ hr.py 前置守卫 5 处 + 站点派生 4 处(R15-A04)。
- **C 类(同一事实多表示, 优先)**: ① **虚拟 tracker 前缀字面量 3 处绕过 infra 单点** `VIRTUAL_TRACKER_PREFIXES`(R16-C01, 真实漂移点); ② **跨层常量**: `_SHOW_STATE_RANK`↔JS `STATE_RANK`、`REANNOUNCE_BLOCKED_STATES`↔JS、ETA 哨兵 `8640000`↔JS/tpl、键位正则 `_KEYS_SERIAL_RE`↔JS `KB_DEF_RE`(R16-C02/C03/C04); ③ 旁挂文件「与 state_file 同目录」寻址 webui 3 处 + 跨包 4 处(R15-C02); ④ token 口径 webui↔hr(R15-C01, 复核 R14-T01); ⑤ hr enabled-sites 派生(R15-C03 = R14-S01 的 webui 半)。
- **B 类(只登记, 不急合)**: search 行 `seeding_time` 未量化 ↔ `_member_view` 量化(R16-B01); 三桶 upsert/removed 集合处理三处用途分歧(R16-B02)。
- **D 类(明确不动)**: `manager.web.touch()` 心跳 / `if cmd_id:` 回执护栏(≤3 行惯用式); 单点已收敛件(`group_key_param`/`content_disposition`/`RoCache`/`_verdict_reannounce`/`_search_norm`/`VIEW_ARRAYS`); auth 跨站防护安全单点; 剧键口径调用点(已委托 `parse_release` 单函数)。
- **既有 issue 复核**: R14-T01(`hr-token-persist-convention-dup`)、R14-S01(`hr-site-derive-convention-dup`)在 webui 侧各找到对应「另一半」, 已引用不重复入池 —— 说明这两条跨包问题确为真。

## 后续候选(未开工)

- 轮 17–19(rules / infra / torrents+tray)、Phase 2 前端(20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(26)。
- 轮 26 汇总: 重构候选排序表(报告 §20 已有雏形)+ 跨层「同一事实」总账 + 未入池候选(R16-B01/B02 暂缓、各 D 类、及 config/core/hr 遗留项)按清偿顺序决定。