# 26-09-25-webui-hr-safety-display — HR 在线核实的 WEB UI 呈现（删除安全档位 × 来源档位）

**Status:** In Progress
**Added:** 2026-09-25
**Updated:** 2026-09-25
**Summary:** WEB UI 一眼分清「哪些种子可以安全删除」。后端 `hr/resolve.py::safety_display` 派生**删除安全档位**(danger/safe/unknown/none) × **来源档位**(在线·考察中/已达标/未达标/已核实、策略、本地兜底、本地超龄豁免、未核实 —— 对齐 v3.0 优先级链), `views.py::_hr_view_fields` 透出 `hr_safety`/`hr_safety_text`/`hr_safety_src`(退役二值 `hr_satisfied_src`); 前端做种时长列(两套 UI 各 3 处)按档位着色(站点结论优先于本地) + 来源 2 字徽标 + 悬停全文, 删除确认框点名 HR 风险, H&R 筛选两档→四档 + 来源副筛选, 批量条「含 N 个不能删」。+4 测试, 全量 **1606 passed + 1 skipped**, 双 UI 冒烟 94 项全过。**未提交**。
**Topics:** webui-hr-safety-display
**Refs:** memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html, memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, memory-bank/tasks/26-09-22-backend-partial-hr-verify.md

## 原始请求

> HR在线核实在WEBUI界面上应该有体现, 让人一眼分清哪些种子可以安全删除, 哪些不能, 等等, 注意要考虑优先级, 先列个方案

随后两轮修正: ①「种子页与明细表有"做种时长"列担任HR职责」→ 不新增列, 复用该单元格; ②「需要明确展示当前状态来自于哪个优先级」→ 结论必须带来源档位。最后「立档后开工」。

## 思考过程与决策

- **数据已备, 缺口全在呈现**: `_hr_view_fields` 早已透出 `hr_state`/`hr_state_text`/`hr_reason`/`hr_site_*` 且种子页/明细/搜索每行都带; 三态只在详情抽屉可见, 主表只有本地口径的 pending/reached 配色。
- **D1 复用做种时长列不新增列**(用户纠正): 该列已挂 `hrTimeClass` 本地配色与「已做种 / 要求」后缀, 新增列是重复信息且挤行宽; 列显隐偏好不动。
- **D2 结论带来源档位**(用户指令): v3.0「档位即结论」后, 界面上每个结论都要能看出来自优先级链哪一档; 原二值「站点/本地兜底」粒度不够, 且来源判定必须在后端单点(前端各说一遍必然漂移)。
- **D3 颜色只编码「能不能删」, 来源用文字徽标**: 避免 4×8 色语义组合; 色弱兜底靠文字。
- **D4 不新造色族**: danger 复用 `pending` 橙、safe 复用 `reached` 青、unknown 用中性 `--paused`、不适用默认 teal; 零新色令牌。
- **D5 种子页做种时长列默认隐藏现状不动**: 列偏好存浏览器, 用户已按需开启。
- **派生不新造判定**: `safety_display(judged, triggered=, satisfied=)` 全部转译 `check_hr_condition`/`check_hr_satisfied`/`hr_judgement()` 的既有结论 —— 与打标流程同源, 徽章与标签芯片不可能互相矛盾; judged=None(未接入/无键)回落本地并记「本地·兜底」; mode=all 未命中(恒受管束无 facts)与新鲜度闸门归「策略」桶。
- **P4 统计口径**: 从删除链同一目标集合派生(`_deleteMembers` 提为共享收集点), 不按视图阵列另算(contract-api「跨视图聚合已第三次」的坑)。

## 实现计划

单点在 [计划文档](../plans/26-09-25-1823-plan-webui-hr-safety-display.html)(§3 两张映射表 / §5 分阶段): P1 单元格升级 → P2 删除链点名 → P3 筛选扩档 → P4 选中统计。本轮 P1–P4 一次全部落地。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 方案 v1→v3 收口 | Done | v1 新增 HR 列 → v2 用户纠正改复用做种时长列 → v3 结论带来源档位(8 token 映射表); 立档 `26-09-25-1823-plan-webui-hr-safety-display.html` |
| P1 后端派生单点 | Done | `hr/resolve.py` 新增 `safety_display` + `HrSafetyDisplay` + 4 `SAFETY_*` + 8 `SRC_*`; `views.py::_hr_view_fields` 透出三字段并退役 `hr_satisfied_src`(docstring 同步); 判定链四个消费点零改动 |
| P1 前端单元格 | Done | `hr.js` 新增 `hrDurClass`(站点结论优先, 未接入回落 `hrTimeClass`)/`hrSrcBadge`/`hrDurTitle`; 6 处模板换绑(atlas 476/584/764 与 prism 502/611/792, 组内成员·种子页·明细各 2)+ `:title` + 徽标节点; 两套 CSS 加 `.m-pair.hr-unk` 与 `.m-pair .hr-src` |
| P2 删除链点名 | Done | `delete_flow.js` 提取 `_deleteMembers` 共享收集 + `_hrRiskOf`; `_deleteFlow` 目标含 danger 时确认框追加「HR 风险」明细行(`#i-warn` 图标, 数量+来源短语+前 3 个名字); 四入口同构自动生效 |
| P3 筛选扩档 | Done | `hr.js` `_hrBucketMember` 改消费 `hr_safety`(旧服务端回落本地布尔)、组级改 `_hrBuckets` 集合、`hrOptions` 两档→四档 + 新 `hrSrcOptions`; `filters.js` filteredGroups/searchUncovered 两处 pass + `filterDefs` 加「HR 来源」+ clearFilters/filtersActive; `app.js` 加 `hrSrcFilter`; 模板筛选摘要行 +1 |
| P4 批量条统计 | Done | `bulkHrWarnText()` 从 `_bulkTargets` 派生 danger 计数, 批量条渲染「⚠ 含 N 个不能删」(两套模板 + 两套 CSS `.bulk-hr-warn`) |
| 测试与守阵 | Done | +4 条与扩展 1 条(见 baseline 顶部); `_scan_filter_facets` 同查 `hrSrcOptions`; 双 UI 浏览器冒烟 94 项全过 0 失败 |
| 真机走查 | Pending | 装扩展跑真实取数后确认: 命中行的档位徽标与 `--hr-status` 明细一致 / 删除确认框点名真实触发 / 筛选计数与行数对得上 |

## 进度日志

- **2026-09-25 19:14 (P1–P4 一次落地 + 三层验收全绿)** — 用户令「立档后开工」。
  ① **后端**: `safety_display` 纯函数落 `hr/resolve.py`(判定收口旁边, CLI 报告日后可共用), 档位结论只认站点档位与身份层, judged=None 时以 triggered/satisfied 为本地结论; `views.py` 三字段全链透出(种子页 `_seed_view`/明细 `_member_view`/搜索 `_view` 都走 `_hr_view_fields`, 零额外接线)。
  ② **前端**: 模板 6 处换绑 + 徽标 + title; `hrStateLine` 改读 `hr_safety_text`(含来源短语, 二值字段退役); token→文字映射表(`HR_SRC_BADGES`/`HR_SRC_BUCKETS`/`HR_SAFETY_CLASSES`/`HR_SAFETY_BUCKETS`)是前端唯一新增的"判定知识", 且被守阵钉死与后端常量逐字一致。
  ③ **测试**: 定向 44 项全绿; 全量 **1606 passed + 1 skipped**(TOTAL 91% / 10991 / 791 / 3612 / 327; resolve.py 98%); 冒烟 94 项 0 失败。红验说明: 派生函数为纯转译, 守阵把"档位→结论/来源"钉成预期值表(无旧实现可还原, 以映射表逐项断言代替红验)。
  ④ **回写**: baseline 顶部、本档案、切片、progress/implemented-webui、README HR 段一条; 计划文档状态 In Progress→Done。tmpdir 坑复发 +1(又手工加 TMPDIR 前缀直跑 pytest, 没先走 commands 引擎)。
  ⑤ 未提交 —— 等用户显式指令。
