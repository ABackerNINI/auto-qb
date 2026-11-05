# activeContext 切片蒸馏归档（2026-11-05）

> 摘要: 2026-11-05 蒸馏轮的落点件 —— 97 条已完结切片逐字外迁到 5 份 attachments, 本篇按域给结论、指针与未决项; 保留 58 条(最后活动 2026-11-04/05)原样。
> 触发: 已归档切片, 切片蒸馏, activeContext 清理, 历史决议

**Refs:** memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html,memory-bank/plans/26-10-16-1509-plan-agg-hour-totals-attribution.html,memory-bank/plans/26-10-19-2007-plan-webui-site-alerts.html,memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html,memory-bank/reports/26-10-09-1529-report-transport-encryption-feasibility.html,memory-bank/reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html,memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-platform-detect-bypass-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-url-decompose-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-utils-small-helper-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-win-dll-lazy-bind-dup.html,memory-bank/issues/26-10-11-0352-refactor-notify-tray-icon-path-dup.html,memory-bank/issues/26-10-11-0352-refactor-torrents-snapshot-view-field-dup.html,memory-bank/issues/26-10-12-2338-test-traffic-limits-guard-midnight-flaky.html,memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html,memory-bank/issues/26-10-31-1539-bug-mutation-tooling-deselect-guards.html,memory-bank/issues/26-10-31-1539-bug-mutation-tooling-verify-channel.html,memory-bank/issues/26-11-01-0050-bug-traffic-sample-livetail-stale-interval.html,memory-bank/issues/26-11-03-0104-bug-full-checking-selfheal-state-save.html,memory-bank/issues/26-11-03-0802-bug-drawer-rowafter-dead-hook.html,memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md,memory-bank/tasks/26-10-09-backend-transport-encryption.md,memory-bank/tasks/26-10-12-webui-traffic-limit-history.md,memory-bank/tasks/26-10-13-backend-seed-state-writeback.md,memory-bank/tasks/26-10-14-webui-qb-traffic-agg-live-tail.md,memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md,memory-bank/tasks/26-10-16-ship-commit-omitted-note.md,memory-bank/tasks/26-10-31-memory-bank-recurrence-tooling.md,memory-bank/tasks/26-11-02-webui-flux-overlay-opacity.md

## 本篇只回答

本轮蒸发了哪些 activeContext 切片、结论落在哪、还有哪些未决项 —— 不复制切片原文。

## 保留与归档口径

- 保留判据: 切片 `> 最后活动:` ≥ 2026-11-04 的 58 条原样保留(含 2026-11-03 创建、11-04/05 仍在推进的 2 条)。
- 归档判据: 其余 97 条(最后活动 2026-09-30~11-03)逐条核对内容 —— 均为任务 Done / 结论已被后续提交取代 / 报告与计划已另存; 原文逐字外迁, 不做摘要改写。
- 归档位置(attachments 不计 cap): [traffic](attachments/activecontext-archive-traffic-2026-11-05.md) 13 条 / [webui](attachments/activecontext-archive-webui-2026-11-05.md) 25 条 / [backend](attachments/activecontext-archive-backend-2026-11-05.md) 12 条 / [testing](attachments/activecontext-archive-testing-2026-11-05.md) 16 条 / [tooling](attachments/activecontext-archive-tooling-2026-11-05.md) 31 条。

## 流量图与全局流量监视器（13 条）

- **视图形态**: 流量图由弹出窗并入详情同款停靠布局(高度跟随详情); 时间窗口 13 档记 localStorage; 头部控件三轮收敛(控件消失 → 头部落点被否决 → 移回图内)。权威口径 [conventions/webui.md](../conventions/webui.md)。
- **数据面**: 限速历史 W1-W3 完成, CI 哨兵 `0.0`→`None`; 3d+ 真空根因=agg.dat 只含封口行, 修法 `LiveTail.pending_agg` + `v4_agg_obs_live` 合流; 3d+ 空闲零值区补开放游程; 重启尖峰根因=qB alltime 在 payload=0 时仍增长、采样器开 z 游程冻结后把陈旧差打进单桶 —— P0-P6 全收口, 唯一未兑现 = E2E5 真机人工验收。
- **GTM**: 计划 Open; S0-S9 已落地, 旧 S10 已并入 0339 S19 并随其 2026-10-31 验收完成收口 Done(见文末「已关闭」); T-01~T-03 三缺陷与日总量虚高修复已 Done(评审 3 条次要发现当轮修)。Open 项见 [roadmap.md](roadmap.md)。

## WEB UI 界面与交互（25 条）

- **单点化批次**: 经典详情渲染彻底删除(内容页变体独档/流量页经典独档, 三皮肤死 CSS ~144 条清); 三皮肤逐字节相同的 35 条 CSS 规则收敛 `shared/console_hub.css`(−324 行); busy 骨架 19 处→3 单点; 三段式对话框外壳单点; 站点告警改 chip(两槽方案作废); 吸左首格选中态同色合成。
- **flux 视觉批次**: 新增 `--bg-pop` 不透明浮层底(12+7 处); 消息弹窗统一 glass 语言并补 warn 档; 移除 hover 行左条与 `fx-row-flash`; 做种时间格 padding→线偏移; 状态色 `--st/--st-soft` 7 kind; 右键目标行改 outline。口径 [conventions/webui.md](../conventions/webui.md)。
- **交互与同步**: 快捷键 6 条改开/关双态(另 4 有条件 + 49 不适合待定); 选中/触发一致性收敛 descriptor 单点 `_scopeResolve`; 乐观 UI(rename 补丁+速度预翻转) Done, 真机复测曾因测试实例不可达阻塞; rename 回滚双出口; add torrents 延迟根因=四跳异步管线, store 有界追平后零 1.5s 簇。
- **e2e 既有红**: 右键菜单三条过时 spec、窗口引擎三处接线、`dtRowAfter` tab 契约、`filteredGroups` 双闸 —— 产品零改动或定点修复, 全绿。
- **大文件列表性能**: 调研报告 26-11-02-0339 已落盘; W1-W5 与 W6a 已实施验收, W6b 已拍板 Dropped; D1/D2/D3 待拍板。

## 后端核心 / 规则 / 迁移（12 条）

- **种子状态回写**: B/B′ 被 qB `RefreshInterval` 默认 1500ms 证伪(写后直查读到写前值), 计划置 Superseded; 定 A3(删合成回写 + deferral)并完成 S0-S2, 二次触发另入池。
- **迁移**: qb_temp 闸门按归属收窄(own 硬拦 / foreign+unowned 降 notes), 真机 RM04-10 通过; 此前 WEBUI 单种子移动的「已移动失败」误报随收窄消解; hot-reload 采纳方案 B 保留分组索引(环境2 R0-R6 PASS)。
- **运行时**: qbmanager 断连稳态重连; full_checking 自愈补 `state.save`; 启动期 fail-fast + 跨平台占用者诊断已合入 develop; taskqueue dry_run 守阵两变异形态红验通过(零 src)。
- **规则**: libtorrent 2.1.2 seed_mode 语义核查 —— fastresume 标记不可替代 zSkipChecked(报告 26-10-22-0234); rule-engine-redesign 两条 issue 核实已解决翻 Done; 自愈缺陷按正确主题另入池。
- **HR**: 扩展缺站点权限(MV3 可选权限重装丢失)取证到修复(预检/逐站授权/徽标第五态); 三处位置覆盖判据在 `cutoff_done<=0` 退化恒通过 → `_lane_covers_done` 单点。

## 测试基座 / 变异 / 真机（16 条）

- **变异测试**: 可行性报告落成 skill+命令包+常驻锚; config/hr/rules/core 四包收官, core W1-W9b 全完成(同池复跑 78.51%); 工具链修 deselect 表同步与 verify 四形态。
- **测试基座**: TMPDIR 自举+互斥锁五步; sidefx 临时根延迟求值; e2e/开发桩端口改 0 取号; CI 长尾用例钉钟; test_yamls 整目录移除; LiveTail `has_block` 守门; real-tag 多标签 `tag_set` 单点。
- **大文件拆分**: R1 完成 10→36 个测试文件 + 12 个支撑模块, 906 个测试函数名与 1170 个界定逐字不变; 12 个仍超千行的桶留 R2。
- **真机轨**: 双环境 `env_registry` 单点 + `real.env` + token 不落盘; RM08 官方 suite 7 passed/1 skipped; RM04 漂移计划 Done, L490 真机复验已跑通(六条断言, issue 26-11-02-1208 Done), 仅内存盘待用户卸载。

## 知识库 / 文档 / 依赖 / 重构（31 条）

- **知识库机制**: cap 债务三轮清理(10-19: 150→60 片); code-review 3 S0-S6 —— 479 文件打标, 18 条分级(P1 2/P2 8/P3 8), 去重闭环 75=50+25; 状态漂移机检四档、HTML 守卫 L1+L2、复发工具四件; kb.nav 搜索/置顶折叠/多选批量。
- **文档**: ActionResult 四态回写; 7 条漂移 issue 全部处置 + v.Nu 9 条清理; HTML 闭合标签笔误全库复扫零命中; 复合 Topics 拆键 question 待拍板。
- **提交链路**: `omitted_note` 按索引状态分组; sync 生成物白名单扩到新增路径; 11 条闸门盘点并出收窄计划(D1 test.quick 不动, D2-D4 待拍板)。
- **依赖/重构**: dup-code 4 条(infra 三 + torrents 一)收敛置 Done; qB 5.3 P1-P3 落地, P4/P5 待 stable。
- **全库二次评审**: 26 条发现 17 新池位 + 3 处回填, 26/26 对账无落空。
- **调研**: transport encryption 结论 —— 回环明文残余风险有限, 跨机唯一正确解是 TLS, 「token 加密载荷」在 LAN 非安全上下文失效, 落地随 hr-channel-remote; issue-clearance 路线图 v2; commands 中文乱码根因在解码侧 GBK(引擎侧修复有效)。

## 未决项（需人工）

- 快捷键 4 条「有条件」+ 49 条「不适合」维持待定。
- 复合 Topics 键拆分待拍板(存量数据未动)。
- 提交闸门 D2-D4 待拍板。
- qB 5.3 P4/P5 待 stable。
- RM04 L490 真机复验已完成(R6), 仅测试内存盘待用户卸载。
- 流量图 E2E5 真机人工验收未兑现。
- 大文件列表性能 D1/D2/D3 待拍板(W1-W5/W6a 已完成, W6b 已 Dropped)。

## 已关闭（2026-11-05 复核）

- **GTM S10 / 来源集成 S19 收口** —— 已关闭: 旧 GTM 计划 26-10-16-0541 的 S10 已并入计划 26-10-17-0339 的 S19 承接, S19 于 2026-10-31 05:40 真机验收完成、计划收口 Done(归档 tooling R2 复核, 零改动); 不再列未决项。
