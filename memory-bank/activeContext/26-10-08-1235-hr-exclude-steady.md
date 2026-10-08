# HR 排除未落到取数侧 · 稳态降频失效 (取证轮)

> 摘要: 用户报「按标签/分类排除 HR 管理的种子似乎打破稳态触发拉取 (稳态设 24H)」。取证结论: HR 排除的判据单点 <code>TorrentRecord.hr_excluded()</code> 只被判定侧 (hr_judgement / check_hr_condition / hr_managed) 与 WebUI 展示侧消费, <b>取数/对账侧从不读它</b> —— <code>HrRuntime._anchors</code>(runtime.py:358-383) 按站点接入无差别采集本地种子, <code>_build_objects</code>(service.py:1375-1413) 的排除链只有 终态/放行/超额 三档。⇒ 被排除种子仍进对账对象集 ⇒ <code>steady = anchors_known and not objects</code>(service.py:497) 恒假 ⇒ 间隔闸永远取 refresh_interval (用户 5H), idle 24H 永不生效。纠正归因: 排除在取数侧是空操作, 破稳态的真因是<b>新增 IYUU 种子</b>(新种子进对象集, 属设计本意)。日志侧证: 相邻两波间隔 16h55m &lt; 24H。修复方向 (A 锚点剔除 / B 锚点带排除位只出对象集 / C 站点开关) → 用户拍板 <b>方案 B</b>, <b>已落地</b>(计划 [26-10-08-1249](../plans/26-10-08-1249-plan-hr-exclude-steady.html), S1–S4; S5 真机复核待用户侧)。报告 [26-10-08-1235](../reports/26-10-08-1235-report-hr-exclude-steady.html)。
>
> 最后活动: 2026-10-08 13:05

**Refs:** memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md

## 正在进行

- <b>S5 真机复核待用户侧</b>(实施 S1–S4 已落地): 真机跑后看 <code>&lt;data_dir&gt;/hr/&lt;site&gt;.json</code> 的 <code>wave.idle_mode</code> 是否翻 <code>true</code>、日志是否出现「未到拉取时刻(拉取间隔·稳态降频…)」、稳态期请求量是否下降。计划 [26-10-08-1249](../plans/26-10-08-1249-plan-hr-exclude-steady.html)(In Progress)。档案 [26-10-08-backend-hr-exclude-steady](../tasks/26-10-08-backend-hr-exclude-steady.md)。

## 本轮完成 (实施轮)

- 方案 B 落码(源码 3 文件 3 处): <code>resolve.HrAnchor</code> 末尾加 <code>excluded: bool = False</code> → <code>record.hr_anchor()</code> 透传 <code>self.hr_excluded()</code> → <code>service._build_objects</code> 循环顶部第四档排除(<code>if anchor.excluded: continue</code>, 置于漂移回炉之前 ⇒ 撤销排除后可逆)。
- 守阵 4 条 + <b>红验 3/4</b>(临时关掉两处源码钩子后 <code>test_build_objects_skips_hr_excluded_anchor</code> / <code>test_hr_excluded_anchor_does_not_break_idle</code> / <code>test_record_hr_anchor_carries_excluded_flag</code> 转红, 还原复绿; 第 4 条 <code>test_excluded_anchor_still_counts_as_local_hit</code> 是「防做成方案 A」的设计锁, 不随本改动红)。
- 文档回写: <code>config-reference/keys.md</code>(<code>hr</code> 行补「取数/对账侧同源」)与 <code>modules/overview.md</code>(原「取数管道零感知」已过时)。
- <b>D1</b> 采纳建议(不清理既有 verified/index 行, 零代码); <b>D2</b> 入池 [26-10-08-1304-perf-hr-exclude-terminal-download](../issues/26-10-08-1304-perf-hr-exclude-terminal-download.html)(perf · Open)。

## 上一轮完成 (计划轮, 12:49)

- 实施计划入库 (方案 B): [plans/26-10-08-1249-plan-hr-exclude-steady](../plans/26-10-08-1249-plan-hr-exclude-steady.html)(S1–S6 + 拍板点 D1/D2 + 验收 V1–V5 + 风险 R1/R2/R3 + 不变项)。
- **实施前口径更正** <span class="num">(诚实性)</span>: 复核 <code>_process_rows</code> 后确认报告 §08「方案 A 会多触发一次 .torrent 下载」的说法不成立 ⇒ A/B 对「对象集是否为空」结果等价, 选 B 的理由修正为「<b>爆炸半径最小</b>」(只动对象集一个面, 匹配/身份/下载与现状逐字相同); 已回写报告 §11 后记 (doc-updated 抬 26-10-08-1249)。
- 认领链三向闭环: 计划 <code>doc-refs</code> ↔ 报告 <code>doc-refs</code> ↔ 档案 <code>**Refs:**</code>。

## 上一轮完成 (取证轮, 12:35)

- 取证报告入库: [reports/26-10-08-1235-report-hr-exclude-steady](../reports/26-10-08-1235-report-hr-exclude-steady.html)(根因两条代码证据 + 判定侧/取数侧对照表 + 日志对账 + 影响面 + 修复候选, doc-topic hr-steady-throttle)。
- 核实既有制品: 报告 [26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html) §13 与计划 [26-10-05-0555](../plans/26-10-05-0555-plan-hr-steady-throttle.html) §02 —— 两者枚举对象集排除链时都只列「终态/放行/超额」, <b>未含 HR 排除</b>, 佐证这是设计缺口而非实现漏行。
- 只读核对 config.yml: <code>exclude_categories=[IYUU自动辅种]</code>, 两站 <code>refresh_interval=5H</code>, <code>idle_refresh_interval</code> 未配走默认 24H, CarPT <code>required(1D)+extra(12H)=36H</code> ⇒ 超额线 108H。
- 坑档: `pitfalls/backend/verdict-scope-parity.md`(判据只落一个消费侧 ⇒ 配置看着生效实为不生效)。
