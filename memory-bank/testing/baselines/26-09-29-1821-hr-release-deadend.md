# 1745 passed / 4 skipped —— HR 放行「签发即作废」+ 端点未监听(白等 180s)修复

> 摘要: 修复用户实报的三处同族缺陷(真机 traceback 引出): ①`hr/service.py::_freeze_terminal`
> 引用未导入的 `LANE_SATISFIED`(v3 重建起潜伏) ②冻结/观察期签发的放行记录漏带锚点快照,
> 判定侧把 `anchor_downloaded=0` 读成「downloaded 增长」⇒ 签发当刻作废(种子回落本地兜底)
> ③`HrRuntime.apply` L0 重建路径新建端点却不 `start()` ⇒ 端口从未绑定, 扩展连不上端点。
> 守阵侧同时揭穿既有 `test_terminal_vanish_writes_release` 常年**假绿灯**(夹具让目标分支不可达)。
> 追加轮: 端点未监听改**快速失败**(不再白等 180s) + 观测期出口守阵同样加固(只验「记录在」不验生效)。
> 基线时间: 2026-09-29 (develop @ 624547a, 本次改动未提交)
> 档案: tasks/26-09-29-backend-hr-release-deadend.md

- test.full: **1745 passed / 4 skipped**, TOTAL **91%**(12,425 语句 / 998 未覆盖 / 4,178 分支 /
  410 partial), 耗时 ~30s。
- 改动前同一工作树实测: **1740 passed / 4 skipped, TOTAL 90%**(12,409 / 1,004 / 4,170 / 407), ~28s。
  Δ = **+5 passed**(新增 5 例: C 档冻结来源 / 站点全关后重新启用 / 无快照不作废 /
  端点未监听快速失败 ×2), 另有 3 例既有守阵被**重塑加强**(观测期出口补「快照 + 判定生效」,
  冻结补 source 与快照断言 —— 只断言「记录在」的守阵对已注入的 bug 依旧是绿的)。
- 红验实测(仅 stash 源码修复, 保留测试改动): 第一轮(`hr/service.py` / `hr/runtime.py`) 4 条全红并
  **复现真机 NameError**(`波次异常: name 'LANE_SATISFIED' is not defined`); 第二轮
  (`hr/fetcher.py` / `hr/runtime.py` / `hr/service.py`) 3 条全红, 红因分别是「白等 5s 后才报
  等扩展超时」/「观测期记录 `anchor_*` 全零」/ 新增 API 缺失。恢复修复后全绿。
- 未提交(等用户显式指令)。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
