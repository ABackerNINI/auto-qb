# 26-10-09-webui-per-tracker-reannounce — 06 变体逐行汇报倒计时真 per-tracker 口径

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 12:57
**Topics:** webui-detail-panel-templates
**Summary:** 认领并实施 issue 26-10-07-0149(计划 26-10-09-1243, 详情面板重构 26-10-06-0838 §06 拍板点 P-02 的备选案)。06「增强表格」变体的逐行「下次汇报」列原以种子级 `detail.reannounce_in` 全局值近似并对所有行标「全局」。取证发现 per-tracker 真值**已在既有 `/trackers` 透传里**(qB 5.2+/WebAPI 2.13.0 每条 tracker 返回 `next_announce`, epoch 秒; 后端 `mask_tracker_entry` 只改 url), 故按推荐案走**纯前端**。修法 = `06-trackers-table-collapsed.js::nextHtml` 改读行级 `next_announce` 减 `nowSec`, 去「全局」标、去微条(per-tracker interval 不可得, 不造假); qB < 5.2 无该字段时**回退**旧全局近似分支; `nowSec` 计入 sig(否则跳过重建把倒计时冻帧)。1 源文件 + 1 桩 + 1 守阵 + 1 e2e。
**Refs:** memory-bank/plans/26-10-09-1243-plan-webui-per-tracker-reannounce.html,memory-bank/testing/baselines/26-10-09-1300-webui-per-tracker-reannounce.md

## 原始请求

> 用户(2026-10-09): 「认领 issue: memory-bank/issues/26-10-07-0149-feat-webui-per-tracker-reannounce-endpoint.html 先写一个实施计划」→ 计划入库 → 「按推荐实施」(P-01…P-05 全取推荐案)。

## 思考过程与决策

- **本轮 = 执行任务**(认领 → 计划 → 落码 → 守阵 → 收尾), 命中立档阈值 #4(产出计划文档)⇒ 立档 + 收尾 DoD; 代码与文档改动随本专题入库(提交由用户显式「提交」指令触发)。
- **P-01 取纯前端(后端零改动)**: 取证确认 per-tracker `next_announce` 已在既有 `/trackers` 透传里 —— 后端 `torrent_detail.py:44-56` 对 `client.torrents_trackers(hash)` 逐条 `mask_tracker_entry` 后直接 `JSONResponse`(无 response_model / 白名单), 而 `mask_tracker_entry`(`infra/utils.py:398`)只改 `url`。故 issue 原假设「需后端加端点/字段」**部分过期**; 后端不动即天然满足「5s 轮询负载不得加频」。
- **P-02 取本机 epoch**: `next_announce` 是 qB 主机 epoch 绝对秒, 前端用 `Date.now()/1000` 相减(单机/局域网时钟通常已对齐)。**硬约束**: epoch 是绝对时间不是倒计时, 必须先减 `now` —— 与 `webui/commands.py::_verdict_reannounce` docstring 记的事故根因同一判据。
- **P-03 去微条**: qB 只给 `next_announce`/`min_announce`, **不给 per-tracker interval** ⇒ 「剩余/周期」无真分母; 沿用旧种子级 `detail.reannounce` 当分母只有活跃行近似正确 ⇒ 真口径行**不画微条**(不造假)。
- **P-04 沿用 5s 轮询**: 不加 1s ticker(零新增负载、无定时器); 倒计时刷新粒度 = 轮询粒度。**配套必做**: `nowSec` 计入 `render()` 的 sig —— 否则 trackers 数据未变时 `H.skipUnchanged` 跳过重建, 倒计时会**冻在上一帧**。
- **P-05 保留回退分支**: 行缺 `next_announce`(qB < 5.2)时保留旧全局近似 + 「全局」标 + 种子级微条 —— 即「现状代码」不退场, 只是不再是 qB 5.2+ 下的默认分支。版本探测**按行按键存在性判**(`num(t.next_announce) && t.next_announce > 0`), 不凭版本号。

## 实现计划

- **S0** 复验锚点(06 现状 / 后端透传无白名单 / qB 字段口径出处 reports/26-10-05-0854 §4.1)。
- **S1** 前端换真口径(`06-trackers-table-collapsed.js`: `nextHtml` 读行级 `next_announce` + 减 `nowSec`; `rowHtml`/`render` 传参; sig 计 `nowSec`; 工具条注与列 title 随口径更新)。
- **S2** 微条/刷新(按 P-03/P-04: 真口径不画微条; 沿用 5s 轮询)。
- **S3** 守阵 + 桩(`tests/test_webui_static_dom_panel.py` 新增 1 条静态守阵; `scripts/ui_harness.py` 新增 `_make_trackers_response` 并按种子灌 `trackers_map`; `e2e/drawer-trackers-reannounce.spec.mjs`)。
- **S4** 收尾(基线切片 + issue/计划状态 + 档案 + `kb.index`)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S0 | 复验锚点 | Done |
| S1 | 06 前端换真口径 | Done |
| S2 | 去微条 + 沿用 5s 轮询 | Done |
| S3 | 静态守阵 1 条 + harness 桩 + e2e 1 条 | Done |
| S4 | 收尾(基线 + 索引 + issue/计划状态 + 档案) | Done |
| — | 真机复核(可选, 用户侧: 多 tracker 种子各行倒计时与 qB GUI「下一个 announce」逐行一致) | Open |

## 进度日志

- **2026-10-09 12:57** 实施轮落地。**S0** 复验: 06 `nextHtml` 现状 + 后端透传无白名单 + qB 字段口径(reports/26-10-05-0854 §4.1)三条锚点均在位, 现象仍复现。**S1** `06-trackers-table-collapsed.js`: `nextHtml(ctx)` → `nextHtml(ctx, t, nowSec)` 读行级 `next_announce` 减 `nowSec`(真口径分支去「全局」标、不画微条); 缺字段回退旧全局近似; `rowHtml`/`render` 透传 `nowSec`; sig 追加 `nowSec`; 工具条注与表头 title 随口径更新。**S2** 同 S1(真口径不画微条; 5s 轮询不变)。**S3** 静态守阵 `test_drawer_tpl_trackers_per_tracker_reannounce`(6 断言, **红验** = 把 sig 的 `nowSec` 改坏 → 转红, 还原复绿) + `ui_harness._make_trackers_response`(3 条 real tracker, 前两条 status=2、第三条按奇偶给 4/3, `next_announce` 逐行 +30min, 保证每个种子恒有 2 行非「更新中」) + `e2e/drawer-trackers-reannounce.spec.mjs`(双皮肤 @fast: 逐行倒计时 ≥2 行且互不相同 + 无「全局」标; 实测 2 passed)。**S4** 基线切片 + 档案 + issue/计划状态 + `kb.index`; `test.full` 与 `kb.check` 全绿(数字见 `commands run kb.baseline`)。
- **2026-10-09 12:43** 用户「按推荐实施」(P-01…P-05 全取推荐案); 实施开工。
- **2026-10-09 12:43** 认领 issue 26-10-07-0149(`Open → In Progress`, 认领方 = 计划 26-10-09-1243); 计划入库(§06 P-02 备选案); 复验锚点。
