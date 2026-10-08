# 26-10-08-backend-hr-exclude-steady — HR 排除在取数侧未生效 (稳态降频失效)

**Status:** In Progress
**Added:** 2026-10-08
**Updated:** 2026-10-08 13:05
**Topics:** hr-steady-throttle
**Summary:** 用户报「按标签/分类排除 HR 管理的种子似乎打破稳态触发拉取 (稳态设为 24H)」。取证结论: HR 排除的判据单点 `TorrentRecord.hr_excluded()` 只被判定侧 (hr_judgement / check_hr_condition / hr_managed) 与 WebUI 展示侧消费, **取数/对账侧从不读它** —— `HrRuntime._anchors` (runtime.py:358-383) 按站点接入无差别采集本地种子, `_build_objects` (service.py:1375-1413) 的排除链只有 终态/放行/超额 三档。后果: 被排除种子仍进对账对象集 ⇒ 稳态条件 (对象集为空) 恒不成立 ⇒ 间隔闸永远取 refresh_interval (5H), idle_refresh_interval (24H) 永不生效。日志侧证: 相邻两波间隔 16h55m < 24H。报告见 reports/26-10-08-1235; 修复方向 (A 锚点剔除 / B 锚点带排除位 / C 站点开关, 倾向 B) 待拍板, **本轮只出报告, 零代码改动**。
**Refs:** memory-bank/reports/26-10-08-1235-report-hr-exclude-steady.html,memory-bank/plans/26-10-08-1249-plan-hr-exclude-steady.html

## 原始请求

> 用户报: 「通过标签/分类排除 HR 管理的种子似乎会打破稳态触发拉取。设置稳态拉取时间 24H。」
> 附日志 (站点 carpt.net 的 HR 页请求, 每 3 行一簇、两簇间隔约 17h)。
> 「在 10-07 到 08 只添加了『IYUU自动辅种』种子, 设置中将其排除了 HR。」
> 「先写一个分析报告」—— 本轮范围为：取证 + 出报告, 不含修复。

## 思考过程与决策

- **先按请求边界定性**: 本轮 = 执行任务 (产出报告制品), 命中立档阈值 #4 (产出报告) ⇒ 立档 + 收尾 DoD; 但**不入池 issue、不改代码、不 commit** (用户未授权这三项)。
- **根因是「判据只落到一个消费侧」**: 「HR 排除」有唯一定义 (record.py `hr_excluded`), 但取数/对账链路是**另一套**对象语义 (`_build_objects`), 它复刻了「该不该管」的判断却漏了排除这一档。判据在两个消费侧各写一遍 ⇒ 漂移 (本项目既有纪律: 判据单点不两处各写)。
- **纠正用户的归因**: 「排除动作打破稳态」不成立 —— 排除在取数侧是**空操作**, 它既没打破也没修复。真正破稳态的是**新增 IYUU 种子** (新种子进对象集, 属设计本意「新下载自动破稳态」), 排除没救回来才是缺陷。
- **日志只作辅证**: 只能证「稳态未生效」(两波间隔 < 24H), 不能反推引擎用的是哪个 interval —— 取数通道 (浏览器扩展) 必须在线才发请求, 落时刻被「在线时刻」过滤。真值是站点文件 `wave.idle_mode` / 日志里是否有「稳态降频」字样。
- **自愈窗口量化**: 无 HR 规则的站点 `required_seeding_time=0` ⇒ 超额线整条失效 ⇒ 排除种子**永远**出不了对象集; 有规则的站点 (CarPT 36H×3=108H) 单颗 4.5 天自愈, 但 IYUU 持续新增 ⇒ 长期仍打不上稳态。
- **影响面定性**: 方向安全 (跑得更勤, 不是漏 HR), 但请求量/站点访问/日额被持续多耗, 且界面「已排除」与引擎「仍在翻页」口径相反。

## 实现计划

- **本轮 (S1)**: 取证 + 出报告 `reports/26-10-08-1235-report-hr-exclude-steady.html` (含根因/证据/日志对账/修复候选); 立档本档案; 切片; 坑档; 基线; kb.index。
- **后续 (待用户拍板, 未开工)**:
  - 拍板修复方案 (报告 §08: A 锚点剔除 / B 锚点带排除位只出对象集 / C 站点开关; 取证倾向 B)。
  - 定「中途被排除是否清理既有 verified / index 行」的口径 (取证倾向不清理)。
  - 落守阵: 排除种子不进对象集 (稳态可生效) + 排除种子仍参与命中识别 (防多下 .torrent) + 排除表为空时零静默变更。
  - 真机复核: `hr/<site>.json` 的 `wave.idle_mode` 与「未到拉取时刻」理由是否带「稳态降频」。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 取证分析报告 + 立档 + 切片 + 坑档 + 基线 | Done (本档案) |
| S2 | 修复方案拍板 | Done (方案 B, 2026-10-08 用户指令) |
| S3 | 出实施计划 (方案 B) | Done (plans/26-10-08-1249) |
| S4 | 实施 + 守阵 (计划 S1–S4) | Done (源码 3 文件 + 守阵 4 条, 3 条红验) |
| S5 | 真机复核稳态降频生效 | Open (用户侧真机跑) |
| S6 | D2 入池 issue | Done (26-10-08-1304 perf) |

## 进度日志

- **2026-10-08 13:05** 用户下达「D2 进 issue, D1 按建议, 开始实施」⇒ **实施轮 S1–S4 落地**(源码 3 文件 3 处改动): S1 `resolve.HrAnchor` 末尾加 `excluded: bool = False` + `record.hr_anchor()` 透传 `self.hr_excluded()`; S2 `service._build_objects` 循环顶部加第四档排除 + docstring 补档; S3 守阵 4 条(`test_build_objects_skips_hr_excluded_anchor` / `test_hr_excluded_anchor_does_not_break_idle` / `test_excluded_anchor_still_counts_as_local_hit` / `test_record_hr_anchor_carries_excluded_flag`)—— **红验**: 临时关掉两处源码钩子(`if False and ...` / `excluded=False`)后 3 条转红, 还原复绿(第 4 条是设计锁, 不随本改动红); S4 文档回写 `config-reference/keys.md` 的 `hr` 行与 `modules/overview.md` 的 HR 行(原「取数管道零感知」表述已过时, 改「取数/对账侧同源」)。**D1 采纳建议**: 不清理被排除种子既有 `verified` / `index` 行(零代码); **D2 入池** [26-10-08-1304-perf-hr-exclude-terminal-download](../issues/26-10-08-1304-perf-hr-exclude-terminal-download.html)(perf · Open · doc-refs 指向本计划)。计划 meta → In Progress。**S5 真机复核待用户侧**; 未提交。
- **2026-10-08 12:49** 用户拍板「按方案 B 出实施计划」⇒ 计划 [26-10-08-1249-plan-hr-exclude-steady](../plans/26-10-08-1249-plan-hr-exclude-steady.html) 入库 (状态 Open, S1–S6)。**实施前的口径更正**: 复核 `_process_rows` 后确认报告 §08 关于「方案 A 会多触发一次 .torrent 下载」的说法不成立 (缺 infohash 的 A 档行无论 A/B 都下载; 带 infohash 的行不下载) ⇒ A/B 对「对象集是否为空」结果等价, 选 B 的理由修正为「爆炸半径最小」; 已回写报告 §11 后记 (doc-updated 抬 26-10-08-1249)。认领链三向闭环 (计划 ↔ 报告 ↔ 本档案)。**仍未改任何源码**; 实施动作另行开轮。
- **2026-10-08 12:35** 取证轮完成, 报告 [26-10-08-1235-report-hr-exclude-steady](../reports/26-10-08-1235-report-hr-exclude-steady.html) 入库 (基线 develop @ fcc3cd69, 只读核对 config.yml)。定性: 排除判据缺取数/对账侧消费点 (`runtime._anchors` 358-383 / `service._build_objects` 1375-1413), 稳态 `steady = anchors_known and not objects` (service.py:497) 恒假 ⇒ 间隔恒取 refresh_interval。**零代码改动 / 未入池 / 未提交**; 修复方案与后续动作待拍板。
