# 26-11-03-backend-gtm-day-total-inflation — GTM 当日总量虚高（断连恢复把网卡生命周期累计计入当日）修复

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** GTM 当日总量虚高（断连恢复把网卡生命周期累计计入当日）修复：sampler 改逐网卡基线；新增 C-prime 单轮速率告警（只告警不改入账）；配置新键走 config.v2.yml overlay；告警主告知为 auto-qb 状态栏常驻横幅。实施后整批 code review（报告 26-11-03-2346）：通过，3 条次要发现修复（取数专用短超时 / interval_hint 入口守卫 / overlay 保存幂等），1 条评审误判撤回。计划 26-11-03-1102，issue 26-11-03-1039。
**Topics:** backend-gtm-day-total-inflation
**Refs:** memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html, memory-bank/issues/26-11-03-1039-bug-gtm-day-total-inflation.html, memory-bank/pitfalls/backend/gtm-total-baseline.md, memory-bank/pitfalls/testing/uv-build-file-lock.md, memory-bank/testing/baselines/26-11-03-2148-gtm-day-total-inflation.md, memory-bank/testing/baselines/26-11-03-2352-gtm-day-total-inflation.md, memory-bank/reports/26-11-03-2346-report-gtm-day-total-inflation-review.html

## 原始请求

1. （2026-11-03）用户报告：网络断开后自动恢复，WebUI 顶栏「今日流量」pill 的当日累计跳变——断网前上传 60 多 G / 下载不到 10 G，恢复后涨到上传 300G 量级 / 下载 500G 量级；要求先只读分析与入池。
2. （2026-11-03）用户拍板修法：**A 逐网卡基线 + C-prime 单轮速率告警**（只告警、不记 0、不改当日累计）；新键不得写进生产 `config.yml`。
3. （2026-11-03）用户否决「告警只在设置页」：告警主告知必须是打开 WebUI 就能看到的常驻面；设置页与 GTM `/status` 降为次级。
4. （2026-11-03）流水线收尾（S9）：文档回写、全量验证、基线、原生 git commit；不合回 develop、不 push。

## 思考过程与决策

- 主修法（D1）：`_nic_base {网卡名: (last_up, last_down)}` 逐卡做差后求和；新卡只立基线，消失卡保留记忆并按 7 天 TTL 清理（D3）。
- 旧载荷（D2）：state `version:1` 保留 day/当日累计、逐卡基线置空，首轮 delta 0（少报 ≤1 个采样间隔，优于虚高）。
- 观测（D4/C-prime）：`rate = delta / eff_dt`，单卡单方向判定，默认 1 GiB/s；超阈值只 WARNING + `last_spike`，不记 0/不丢账/不改 day。
- 告警可见面（D5，v3）：主告知 = auto-qb 顶栏常驻横幅（快照追加可选 `gtm_anomaly`，来源 GTM `/status.last_spike`，只增不改）；设置页行与 GTM `/status` 为次级，日志只作取证。
- 配置升级（D6）：新键只写 `<data_dir>/config.v2.yml` overlay，程序启动时幂等补齐；主 `config.yml` 零改写，旧版本可零操作回滚。
- 契约（D7）：`history_traffic.dat`、auto-qb 读取/聚合/限速零改动；`/status` 与流量快照只追加可选字段。
- 计划路径：`memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html`（v3）。

## 实现计划

S0 先落红测试 → S1 sampler 逐网卡基线 → S2 storage 恢复兜底 → S3 测试补齐与覆盖率 → S5 C-prime 速率告警 → S8 日志落盘 → S7 次级可见面 → S6 配置 overlay → S7b 主告知数据链路 → S7c 状态栏横幅 → S9 文档回写与全量基线。每步独立可 revert；S5/S6/S7/S7b/S7c 不改变 dat 契约。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 红测试：改写 2 条旧语义用例 + 新增 T1/T2/T4/T8 | Done (2026-11-03, f71517c4) |
| S1 | sampler 逐网卡基线 + state v2 + v1 降级 | Done (2026-11-03, b427f33a) |
| S2 | storage.recover 兜底改用 state_restored/day | Done (2026-11-03, 29bde200) |
| S3 | T3/T5/T6/T9/T13 与覆盖率缺口 | Done (2026-11-03, c26d8cfa) |
| S4 | 真机断连复验 | 未执行（需真实断网/禁用网卡，本流水线不覆盖，代码验收不依赖） |
| S5 | C-prime 单轮速率告警（只告警不改入账） | Done (2026-11-03, 3bce4a06) |
| S6 | 配置升级 overlay（config.v2.yml） | Done (2026-11-03, 1a687e50) |
| S7 | 次级可见面：/status.last_spike + 设置页「最近异常」 | Done (2026-11-03, 88baad0f) |
| S7b | 主告知数据链路：快照 gtm_anomaly + fetch_last_spike | Done (2026-11-03, eb6d6735) |
| S7c | 主告知渲染：状态栏常驻横幅与本机消警 | Done (2026-11-03, c040cce7) |
| S8 | 日志落盘 gtm.log（提交记为 S6 日志） | Done (2026-11-03, 75cc0f77) |
| S9 | 文档回写 + 全量验证 + 基线 | Done (2026-11-03，随本专题入库) |

## 进度日志

### R0 · 立档 (2026-11-03)

S0–S3/S5–S8 与 S7b/S7c 已在分支 `feat/gtm-day-total-inflation` 按计划落地（提交见子任务状态表）；S9 完成文档回写（sampler 文档串补 C-prime、`docs/configuration.md` 口径/新键/overlay/告警可见面、本档案、坑档、计划状态与 issue）、全量实测基线切片（数字只写 `testing/baselines/`，见 `commands run kb.baseline`）与 `kb.check` 自检。S4 真机断连复验保留 Open（需物理断网，不阻塞代码验收）。issue 26-11-03-1039 状态置 Done 并补修复证据；存量虚高 dat 行未回写（见 issue「旧虚高存量」节）。

第一次会话: 用户报告与两次只读取证（10:35/10:47）→ 根因「过滤集收缩污染合计基线」→ 方案 v3 定稿入库 `c33a7e46`。

- 2026-11-03 21:51 S9 收尾：修正 issue 斜杠日期与 fetch_last_spike 失败矩阵前置；sampler/docs 文档回写；plan/issue 置 Done；全量实测基线入切片；kb.check 全绿（未合 develop、未 push）

- 2026-11-03 23:54 code review 整批 GTM 虚高修复(通过, 无阻塞缺陷): 3 条次要发现当轮修复(取数专用 3s 超时/interval_hint 入口守卫/overlay 保存幂等), 1 条评审误判撤回; 补 4 条守阵测试; 评审报告 26-11-03-2346 与新基线切片入库
