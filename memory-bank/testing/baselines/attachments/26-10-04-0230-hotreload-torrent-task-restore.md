# 基线切片 26-10-04-0230 — 热重载 L2 重建后种子级任务补建 (issue 26-10-01-2147 修复)

> 摘要: 认领修复 issue 26-10-01-2147(所有 L2 级热重载后存量种子种子级任务丢失, 不止新站点): TaskQueue.has_task 查重助手(has_named 委托归一) + RulesModule 订阅 full_round 补建(装配序在 tracker 重匹配后, conf 仍 None 留待下轮) + _create_torrent_tasks 幂等化 + immediate(补建任务立即到期, 下一 tick 兑现一次维护消费 external_tag_changes)。红验先行 3 用例(test_modules_p5.py)修复前红修复后绿; 既有测试随行为变化同步 3 处。

- 时间: 2026-10-04 02:35 (GMT+8)
- 分支: develop @ 4805f5f5 (会话起点 sync 后; 本轮回写件全部待用户提交指令, 未 commit)
- 命令: `commands run test.full`
- 实测: **2422 passed + 3 skipped, 29.07s, 覆盖率 99%** (14345 语句 / 132 未覆盖 / 4820 分支 / 105 partial; Required coverage of 98% reached)
  - `commands run test.quick`: 2422 passed + 3 skipped, 22.80s (同数字口径, 提交闸门用)
  - 前基线 (26-10-04-0115): 2418 passed + 3 skipped → 本轮 +4 = 新增回归测试 3 条 + test_modules_p3 订阅者断言改判定不变
- 改动面:
  - `src/auto_qb/core/taskqueue.py`: +`has_task(kind, name, hash)` 种子级任务幂等判据单点; `has_named` 改为其 hash="" 特例转发(语义不变)。
  - `src/auto_qb/core/modules/rules_mod.py`: subscribe +full_round; `_on_full_round` 补建(conf 非 None + 回执日志); `_create_torrent_tasks` 入口幂等(maintenance 任务在队即整面跳过) + `immediate` 参数(补建 next_run=now) + 返回 bool。模块 docstring 相位清单同步。
  - `tests/test_modules_p5.py`: 新增 test_full_round_restores_torrent_tasks_after_rebuild / test_full_round_skips_unmatched_records / test_startup_round_tasks_not_duplicated(红验过) + test_phase_subscription_map 补 full_round 断言(tracker→rules) + test_torrents_added_pipeline_order 断言更新(order 首元素 = full_round 补建) + 文件头测试计划同步。
  - `tests/test_modules_p3.py` / `tests/test_qbmanager.py`: 既有断言随行为变化更新(full_round 订阅者数 1→2 / _create_torrent_tasks 返回值 None→False)。
- 知识库回写: issue 26-10-01-2147 Done(§07 修复后补充) / systemPatterns/main-loop.md 相位表 / modules/core-runtime.md RulesModule 行 / rule-system/rules-and-triggers.md / progress/implemented-core.md / pitfalls/backend/hot-reload-stale-bindings-derived-views.md(第三段); 档案 [tasks/26-10-04-backend-hotreload-torrent-task-restore](../../tasks/26-10-04-backend-hotreload-torrent-task-restore.md)(Done)。
