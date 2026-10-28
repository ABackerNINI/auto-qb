# 26-10-29-backend-hr-ext-site-permission — HR 扩展缺站点权限的可见化与失败分类修正

**Status:** In Progress
**Added:** 2026-10-29
**Updated:** 2026-10-29
**Summary:** 生产故障(BTSchool/CarPT 三档全失败 12h+, 日志只写「页面改版」)取证到扩展重装后 MV3 可选站点权限被清空; 两侧可见化 + 失败分类归位 + 零行判据修正, M1–M5 全量落地
**Topics:** backend-hr-ext-site-permission
**Refs:** memory-bank/plans/26-10-29-0147-plan-hr-ext-site-permission.html

## 原始请求

1. 结合设计文档只读分析 `D:\Projects\auto-qb\` 的日志报错原因(用户假设:「猜测是 A 页 0 行导致的, 但 B 页不是 0 行」)。
2. `grilling` 一个修复计划, **缺权限的站点必须在 auto-qb 与扩展侧明确展示**, 且诊断中发现的三处设计缺口一并纳入计划。
3. 两轮 grilling 逐条拍板(第一轮 Q1–Q5「全按推荐」, 第二轮 Q6–Q9「按推荐」)。
4. **全量实施**(M1–M5)。
5. **提交**。

## 思考过程与决策

**根因(证据链, 非推断)**: 用户假设(A 页 0 行导致)被证伪 —— 三档 `pages` 全为 0, 说明**一页都没取到**, 不是「取到了但是空的」。
决定性证据是 Edge `Secure Preferences`: 该扩展 `first_install_time == last_update_time == 2026-10-28 12:47:36`,
`granted_permissions.explicit_host` 只剩三个回环 origin ⇒ 扩展被重装, MV3 的**可选站点权限被清空**,
`fetch(url, {credentials:'include'})` 被 CORS 拒, 浏览器只给一句 `TypeError: Failed to fetch`(与「端点没起」同一句话、完全不同病因)。

**三处既有设计缺口(用户要求一并纳入)**:

- G1 `events.fetch_failed` 用 `EVENT_PARSE` 发事件 ⇒ 网络层失败被贴上 `[HR 页面改版]`(把排查引向站点改版)。
- G2 `_maybe_alert_lane_fail` 只接在 `_LaneAbort`(结构失效)路径 ⇒ 取数失败路径永不升级, `fail_streak` 涨到 58 也没有一句「疑似改版」。
- G3 `zero_rows = 总量为 0` ⇒ 「一页都没取到」被写成「结构完好但清单为 0」, 把用户引向 `--hr-confirm-empty` 人工对账。

**拍板结论(计划 §06 D1–D9)**: D1 预检 + 失败归因两者都要 / D2 后端只经 `POST /api/hr/result` 的 `kind` 感知, 不做 capability 上报 /
D3 两个 kind 归**通道层**且**两个独立异常类**(继承即语义) / D4 `zero_rows = 总量为 0 ∧ 全档 ok` / D5 选项页逐站授权态 + 徽标第五态 /
D6 `channel_state` 新态**与** `blocking_reason` 都接, 且病因排判定链最前 / D7 缺权限 ERROR + 主动通知, 网络层 WARNING + 静默 /
D8 升级告警只接页面层 / D9 退避 / capability / schema 抬版三项明确不做。

**关键取舍**: 不抬 `hr_site` schema_version —— 新字段缺键即默认(零迁移); WebUI **零改动**(它只读 `channel_text`, 文案单点在 `status.py`);
`permissions.contains` 判多 origin 被否(只在全部授予时为真), 改 `getAll()` + 纯函数匹配, 两份实现由跨层真值表钉死。

## 实现计划

按 W1–W5 五个工作面 / M1–M5 五个可独立验收的期推进(详见计划 §04):

1. **M1** 扩展侧: `originGranted`/`siteGranted` 预检 + 未授权**拒发** + 选项页逐站授权态与一键补授权 + 徽标第五态(排在 `ok` 之前)。
2. **M2** 后端分类: 两个 `kind` → 两个通道层异常 → 落盘 `channel_last_error`; 未知 kind 仍回落 `HrFetchError`(旧扩展兼容)。
3. **M3** 两侧展示: `channel_state` 两新态 + `CHANNEL_TEXTS` 带动作文案; `blocking_reason` 病因优先; `--hr-status` / WebUI 自动跟随。
4. **M4** 判据与告警: `zero_rows` 改「全档 ok」口径 + note 守卫; 页面层取数失败补接升级告警(`_WaveContext.alerted` 承接登录分支)。
5. **M5** 文档 / 坑档 / 守阵 / 基线: 扩展 README(授权独立成步 + 重装警告 + 排障表拆行) / `docs/configuration.md` / 两份坑档 / 18 条新用例 / 新基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| M1 | 扩展侧预检、拒发、逐站展示、徽标第五态 | Done(2026-10-29) |
| M2 | 后端两个 kind → 通道层异常 → 落盘通道痕 | Done(2026-10-29) |
| M3 | `channel_state` 两新态 + `blocking_reason` 病因优先 | Done(2026-10-29) |
| M4 | `zero_rows` 全档有效口径 + 页面层升级告警补接 | Done(2026-10-29) |
| M5 | 文档 / 坑档 / 守阵 18 例 / 基线切片 / 计划翻 Done | Done(2026-10-29) |
| M6 | 真机走查(重载扩展 → 选项页授权态 → 徽标回绿) | Open |

## 进度日志

### R0 · 立档 (2026-10-29)

本轮进展:

- 取证定因: 日志(347 次 `Failed to fetch`, 首现 2026-10-28 12:49:07) + 两站站点文件(三档 `pages=0/rows=0/fail_streak=55~58`) + Edge `Secure Preferences`(`explicit_host` 仅回环, 安装时间 == 更新时间) ⇒ 扩展重装导致可选站点权限丢失, 用户「A 页 0 行」的假设被证伪。
- 计划 `26-10-29-0147` 两轮 grilling 后成文并全量实施(M1–M5), 状态翻 Done。
- 新增 18 条守阵(扩展 3 / 服务 7 / 状态 3 / 事件 2 / 取数通道 3), 全量 `test.full` 绿(数字见 `commands run kb.baseline` 最新一条)。
- 坑档: `pitfalls/web-ui/extension-bridge.md` 新增「重装后未授权 → `Failed to fetch`」行 + `复发: 3`; `pitfalls/backend/fault-domain-classification.md` 记 `复发 +1`(同一坑第二次实报)。
- 遗留: M6 真机走查需用户在真实浏览器里点一次(代码与守阵保证不了浏览器行为)。

- 2026-10-29 02:16 HR 扩展缺站点权限(MV3 可选权限重装后丢失)取证到修复: 扩展侧预检+拒发+逐站授权态+徽标第五态, 后端两 kind 归通道层并落盘通道痕, 通道态与病因文案两侧可见, zero_rows 改全档有效口径并补接页面层升级告警, 文档/坑档/18 例守阵/基线齐
