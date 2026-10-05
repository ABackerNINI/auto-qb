# 强制汇报确认机制调研 (backend-reannounce-confirm)

> 摘要: 用户报「强制汇报检测经常无法识别」(投递后 qB 显示 下一个announce 8分钟→0(约半秒)→回 8分钟), 调研 qB/qbittorrent-api 可用的汇报确认接口并出报告。结论: WebAPI 2.13.0(qB 5.2, 用户实测 5.2.3) 起 torrents/trackers 直出 next_announce/min_announce(**epoch 秒**)/endpoints/updating, 是持久可轮询的正向信号; 现判定 `na < b_na-60` 把 epoch 当倒计时用、成功路径方向相反恒不触发 → 恒 30s 超时误报失败。libtorrent 源码级机制(推迟路径/0抖动=announce 在途/停止种子静默 no-op)与候选判定设计(next_e 前跳+TOL 3~5s、stopped 直判、未确认单列、旧版回退证据门控)见报告 §5/§7, 待拍板后另开计划。
> 最后活动: 2026-10-05 09:02

**Refs:** memory-bank/tasks/26-10-05-backend-reannounce-confirm.md, memory-bank/reports/26-10-05-0854-report-reannounce-confirm-api.html

## 已完成
- 现状取证: `webui/commands.py` 四判据 + `runtime.py::check_pending` 逐条对机制分析, 失效根因定位(epoch/倒计时语义错位)。
- 外部取证: qB release-5.2.3 与 libtorrent RC_2_0 关键源码段(WebSearch 摘录 + 内置浏览器页面上下文 fetch 切片, 本环境 raw/blob/fossies 不可达); WebAPI 2.13.0(PR #23045, milestone 5.2)与 qB 5.2 sync announce stats(e309b17) 落点确认。
- 本地验证: qbittorrent-api 2026.8.1 Tracker=ListEntry→Dictionary→AttrDict(dict 透传, 新字段零成本), `app_web_api_version()` 可作版本闸门; 项目当前无 qB 版本探测。
- 产出: 报告 reports/26-10-05-0854-report-reannounce-confirm-api.html + 档案 tasks/26-10-05-backend-reannounce-confirm.md。

## 正在进行
- 无(调研轮收尾中; 报告 §8 三个待真机确认点与只读探针留待落地前验证)。
