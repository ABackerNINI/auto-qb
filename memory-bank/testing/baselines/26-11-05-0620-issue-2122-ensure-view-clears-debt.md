# 5341 passed + 10 skipped —— issue 26-09-19-2122 清偿(ensure_view 消费即清 + 门控 SSE 口径)后全量基线

> 摘要: issue 26-09-19-2122 认领清偿(ensure_view 消费即清/flush_views 门控注释与 pending_ver 声明补 SSE 口径)后全量基线
> 基线时间: 2026-11-05 06:20
**Refs:** memory-bank/issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html, memory-bank/tasks/26-10-08-webui-perf-issues-closing.md

## 验收数字

`commands run test.full` 实测(2026-11-05 06:20, Windows, 本机):

- 汇总行: `5341 passed, 10 skipped, 1 warning in 136.39s (0:02:16)` —— 0 failed
- 覆盖率 TOTAL 表末行: `TOTAL 24464 69 8390 38 99%`(语句 24464 / 缺 69 / 分支 8390 / 部分覆盖 38); 闸门判定通过(退出码 0)
- 口径注记: 副作用台账越界 0。相对上基线 26-11-05-0540: 测试数 +1(新用例 test_ensure_view_clears_pending_ver), 语句 +1, 缺口净额 ±0(miss+partial 69+38 逐位一致)。

## 本改动面

- `src/auto_qb/webui/runtime_views.py`: `ensure_view` 补「消费即清」——持锁内无条件 `pending_ver = None`, 与 `ensure_state` 同构(issue 26-09-19-2122 顺带小修: 只取 /api/groups 的外部脚本此前不清账, 欠账恒挂, 门控把主循环侧重建全推给请求路径); `flush_views` 门控注释补 SSE 消费动态口径(主路径等效失效/保护对象只剩轮询兜底/「省 50%」系主循环单列口径)。
- `src/auto_qb/webui/runtime.py`: `pending_ver` 字段声明补 SSE 消费动态与清账入口清单(方案 B 口径修正)。
- `tests/test_qbmanager_query.py`: 新用例 `test_ensure_view_clears_pending_ver`(发布登记欠账 → /api/groups 消费清账且不顺带重建 → 脏时 ensure_view 自身触发发布同临界区先置后清 → 门控重开可重建; 含收口评审 nit 补强分支); 头部 docstring 测试计划同步。
- `memory-bank/`: issue 26-09-19-2122 翻 Done(状态日志 + 修复后补充留痕), 归属档案 26-10-08-webui-perf-issues-closing 补 Refs/Summary, 索引重建。
