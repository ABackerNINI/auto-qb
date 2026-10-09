# 06 变体逐行汇报倒计时真 per-tracker 口径 · 已实施闭环

> 摘要: 用户指派「认领 issue 26-10-07-0149, 先写实施计划」→ 计划入库 → 「按推荐实施」(P-01…P-05 全取推荐案)。本件即详情面板重构计划 26-10-06-0838 §06 拍板点 **P-02** 的备选案。**开工取证的关键发现**: per-tracker 真值**已在既有 `/trackers` 透传里** —— qB 5.2+(WebAPI 2.13.0)的 `GET /api/v2/torrents/trackers` 每条返回 `next_announce`(epoch 秒), 后端 `torrent_detail.py:44-56` 只做 `mask_tracker_entry`(仅改 url)后原样透传。故 issue 里「后端需加端点」的前提**部分过期**, 改走**纯前端**: 06 变体逐行倒计时改读行级 `next_announce` 减 `nowSec`(去「全局」标、去微条), qB < 5.2 回退旧全局近似。1 源文件 + 1 桩 + 1 静态守阵 + 1 e2e。
>
> 最后活动: 2026-10-09 12:57

**Refs:** memory-bank/tasks/26-10-09-webui-per-tracker-reannounce.md,memory-bank/testing/baselines/26-10-09-1300-webui-per-tracker-reannounce.md

## 本轮完成

- **会话开工同步**: `my-commit-flow.sync` 快进 `7db68591 → ff768df6`。
- **认领 + 计划**: issue 26-10-07-0149 `Open → In Progress`(后转 Done); 计划 `memory-bank/plans/26-10-09-1243-plan-webui-per-tracker-reannounce.html`(S0-S4 + 拍板点 P-01…P-05); 认领链双向闭环。
- **实施(S1-S3)**: ①`src/auto_qb/webui/static/shared/drawer_tpl/06-trackers-table-collapsed.js` —— `nextHtml` 改读行级 `next_announce` 减 `nowSec`(真口径去「全局」标/去微条), 缺字段回退旧全局近似; `nowSec` 计入 sig(否则跳过重建冻帧); ②`scripts/ui_harness.py` —— 新增 `_make_trackers_response`(3 条 real tracker 含 `next_announce`, 恒有 2 行非「更新中」)并灌 `trackers_map`; ③`tests/test_webui_static_dom_panel.py` —— 新增静态守阵 `test_drawer_tpl_trackers_per_tracker_reannounce`(6 断言, **红验**确认); ④`e2e/drawer-trackers-reannounce.spec.mjs` —— 双皮肤 @fast(逐行倒计时 ≥2 行且互不相同 + 无「全局」标, 实测 2 passed)。
- **收尾(S4)**: 档案 `memory-bank/tasks/26-10-09-webui-per-tracker-reannounce.md`(Done) + 基线切片 + issue/计划状态 Done + `kb.index`; `test.full` 与 `kb.check` 全绿(数字见 `commands run kb.baseline`)。

## 待办 / 移交

- **真机复核(可选, 用户侧)**: 多 tracker 种子上, 06 变体各行倒计时与 qB GUI「下一个 announce」逐行一致(容差 = 5s 轮询粒度); 用户侧 qB 需 ≥ 5.2(否则走回退分支 + 「全局」标)。
- **cap 债务(另开会话)**: `kb.check` 报 1 项 cap 债务 + 切片数超 70 —— 不拦提交, 本会话不动手, 需另开清理会话。
