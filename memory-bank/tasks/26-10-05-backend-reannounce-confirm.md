# 26-10-05-backend-reannounce-confirm — 强制汇报确认机制调研

**Status:** Done
**Added:** 26-10-05
**Updated:** 26-10-05
**Summary:** 调研 qB/qbittorrent-api 汇报状态接口并解码用户观察的 0 抖动场景: WebAPI 2.13.0(qB 5.2) 起 torrents/trackers 直出 next_announce/min_announce(epoch 秒)/endpoints/updating; 现判定 `na < b_na-60` 把 epoch 当倒计时、方向反了故恒不触发, 30s 超时误报失败; 候选判定(next_e 前跳+TOL 3~5s / updating / status4+msg / stopped 直判 / 未确认单列)已写入报告待拍板。
**Topics:** backend-reannounce-confirm

**Refs:** memory-bank/reports/26-10-05-0854-report-reannounce-confirm-api.html, memory-bank/testing/baselines/26-10-05-0907-reannounce-confirm-research.md, memory-bank/plans/26-10-05-0923-plan-reannounce-confirm-rework.html

## 原始请求

用户(2026-10-05): 现在的强制汇报检测不准, 经常无法识别。观察: 投递前 qB 显示「下一个announce 8分钟, 最小announce 8分钟」, 投递后显示「0分钟, 0分钟」约半秒, 换回「8分钟, 8分钟」。调研 qb / qbittorrent-api 是否有相关接口可以直接/间接准确确认汇报情况, 写一份报告。

## 思考过程与决策

- **现状取证**: 确认链路 = `webui/commands.py::_trackers_baseline`(记 status+next_announce 基线) → `runtime.py::check_pending` 每 tick(2s) 轮询 `torrents/trackers` → `commands.py::_confirm_reannounce_result` 四判据 → 30s(`REANNOUNCE_CONFIRM_TIMEOUT`)超时判失败。
- **外部取证路径**: raw.githubusercontent / github blob / fossies 在本环境被墙或反爬, 最终用「WebSearch 摘录 + 内置浏览器在页面上下文 fetch raw 文件后切片回传」拿到 qB release-5.2.3 与 libtorrent RC_2_0 的关键源码段(只回传切片, 不整读)。
- **机制解码**(源码级, 证据链见报告 §2/§5):
  - qB `forceReannounce` 不带 `ignore_min_interval` → libtorrent 尊重 min_interval: `next_announce = max(now, min_announce)+1s` 且 `min_announce := next_announce`; 未过期时强制汇报被**推迟**, HTTP 200 照常返回。
  - 发送瞬间 `updating=true; next_announce=min_announce=now` → 用户看到的 0/0 半秒抖动 = announce 在途(说明当时 min_interval 已过期, 走立即路径)。
  - 响应后 `next=now+interval; min=now+min_interval; fails=0; msg 清空` → 回到 8/8。
  - `is_paused()` 直接 return → 停止种子强制汇报是静默 no-op。
- **失效根因**: `next_announce`/`min_announce` 是 **epoch 秒**(PR #23045 提交 "seconds since epoch"; qB `toSecondsSinceEpoch`), 现判据 `na < b_na - 60` 按倒计时设计 → 成功时 na 前跳, 判据方向反了恒不触发; `status==3` 0.5s 窗口 ≪ 2s tick 命中率 ~25%; `2→2`+msg 不变无差异 → 恒 30s 超时误报失败。
- **接口盘点结论**: 主判据 = next_announce epoch 前跳(持久, 2s 粒度可检); 辅助 = min_announce 前跳 / updating / status3; 否定 = status4+msg(现实现已对); 另有 sync 通道 `has_*_announce_error` 健康位(qB 5.2, `record.py:106` 已接 `has_other_announce_error`, qB 会对汇报状态刚变的种子下一 tick 主动重推); 种子级 `reannounce` 倒计时全版本可用但有"剩余≈interval 不可区分"盲区; log/main 无正向信号。
- **决策**: 只出调研报告(阈值 #4 立档), 不动代码; 候选判定设计(next_e 前跳 + TOL 3~5s + 推迟窗口 + 未确认单列 + 旧版回退证据门控)写进报告 §7 待用户拍板后另开计划。

## 实现计划

1. 会话开工同步 + 路由阅读(README 细路由 / doc-forms / webui dark 规范 / qb-api 坑档)。
2. 现状取证: 现有确认链路与四判据逐条分析。
3. 外部调研: WebAPI changelog/PR/源码 → libtorrent 源码 → qbittorrent-api 本地验证(透传 + `app_web_api_version`)。
4. 产出报告 `reports/26-10-05-0854-report-reannounce-confirm-api.html`(dark, doc-forms 协议)。
5. 收尾: activeContext 切片 + kb.index + test.full 基线切片。

## 子任务状态表

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| S1 | 现状取证(四判据 vs 机制) | 已完成 | 报告 §3 |
| S2 | qB 5.2.3 源码取证(序列化/reannounce 行为) | 已完成 | 报告 §4/§5 |
| S3 | libtorrent RC_2_0 机制取证 | 已完成 | 报告 §5(推迟路径/0抖动/停止种子 no-op) |
| S4 | qbittorrent-api 2026.8.1 适配验证 | 已完成 | Tracker dict 透传, 无需升级 |
| S5 | 报告产出 + 档案 + 收尾 | 已完成 | 报告 §7 = 候选设计待拍板 |

## 进度日志

- 2026-10-05: 开工同步 911af7ef; 完成全部调研与报告; 结论单点见报告 §1 —— qB 5.2+ 的 `torrents/trackers` 已有可用的持久正向信号, 现判定失效根因是 epoch/倒计时语义错位。三个待真机确认点(未联系行的 epoch 值 / 立即路径跳幅 / 推迟路径同值移动)与只读探针列在报告 §8。
- 2026-10-05 收尾: `commands run kb.index` 重建(20 生成物); `commands run test.full` 2589 passed + 4 skipped / 99% / 36.78s(纯文档轮零代码改动, 增量 +13 来自并行会话已入库 develop 的用例; 基线 [26-10-05-0907](../testing/baselines/26-10-05-0907-reannounce-confirm-research.md))。待用户「提交」指令后走 `ship.commit`。
