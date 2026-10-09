# 2836 —— HR 故障归属分层拆分 (计划 26-10-09-0821)

> 摘要: 把「等扩展超时」补进异常家族, 并让「归属层」贯穿到日志出口。此前它抛裸 `HrFetchError` ⇒ 被当
> 「页面取数失败」: 套 `[HR 页面改版]` 标签(进前端错误历史)、写 `wave.notes`(环境噪音进持久证据链)、
> 推进 `fail_streak`(连关几晚升成「疑似改版」ERROR)。现归**通道层**(`action=no-channel`), 且通道层的
> **静默子类只进后端 log**(不进前端错误历史 / 不弹通知); 「WebUI 在线而扩展不在线」按可观测证据**可见告警**。
> 计划: memory-bank/plans/26-10-09-0821-plan-hr-fault-domain.html (Status: In Progress)
> 基线时间: 2026-10-09 09:31

**Refs:** memory-bank/plans/26-10-09-0821-plan-hr-fault-domain.html

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2836 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial)
- **耗时**: 30.36s(墙时 32.4s)
- **新增测试**: 12 个 —— worker 三档 ×3(`test_silence_is_quiet_when_nobody_watching` /
  `test_silence_is_visible_when_web_active` / `test_silence_names_rejected_root_cause`)· service ×5
  (通道归位 / 不升级疑似改版 / 边界回归 / 层表 / 独立标签)· errlog 静默 ×1 · server 被拒面 + 401 节流 ×2 · notify 静默 ×1

## 代码事实变更(需回写的口径)

- **异常家族补洞口**: `hr/fetcher.py` 新增 `HrChannelTimeout(HrChannelUnavailable)`; 超时改抛它 ⇒ 落进**既有的**
  `except HrChannelUnavailable`(`service.py:642`, 位置在 `except HrFetchError` 之前) ⇒ `ACTION_NO_CHANNEL`。
  **未新增 `except HrChannelTimeout` 分支** —— 继承链 + 现成的 except 顺序已让出口就位(计划 S2 因此免做)。
- **层单点**: `hr/events.py` 加 `EVENT_CHANNEL`「通道不可用」+ `DOMAINS`(事件→层) + `domain_of()`;
  `channel_silent(..., evidence=...)` 三档文案(`rejected` / `web_active` / `none`), 不再用一句问句让用户猜。
- **出口收放**: 新增 `hr/log.py`(生产点挂 `hr_domain` / `hr_silent`)+ `infra/logging.py` 的 `is_record_suppressed`
  读取器; `webui/runtime.py` 的 `WebErrLogHandler.emit` 与 `infra/notify.py` 的 `NotifyHandler.emit` 按档位跳过。
  **未打标 = 可见**(向后兼容; 漏打标的后果是"多报"而非"漏报")。
- **状态面**: `ChannelStatus` 增 `rejected_contacts` / `last_rejected_ts`(以及端点属性); 401/403 记「被拒接触」
  但**不污染** `last_contact_ts`; 401 日志由「每分钟一条 ERROR」改为「状态变化一次 + 6h 提醒」的 WARNING。
- **WebUI 活跃信号**: `HrWorker(web_active_fn=...)` ← `HrRuntime._web_active()`(现读 `manager.web.is_active()`);
  `_check_channel_silence` 按 `rejected` / `web_active` / `none` 三分支决定可见性与文案。**不判断同机 / 同源**。
