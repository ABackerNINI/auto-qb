# webui-perf-issues-closing — 三条 perf issue 定案 / 重归因

> 摘要: 用户命题「最近进行了重构, 分析这三个性能相关 issues 是否已经解决」→ 只读裁定 → 用户指令「按照建议执行 1/2/3」。落地: ①`26-10-01-2218-perf-webui-api-state-full-scan` **Done**（方向①②由增量同步计划 26-10-07-0414 兑现, 带实测数字; 方向③分页/按需字段未实施 → 转新件 `26-10-08-0411-perf-webui-api-state-pagination`）; ②`26-09-21-1408-perf-webui-shows-view-full-rebuild` **Done**（补跑全量 `dev.e2e` 94 passed / 10 skipped / 0 failed, S10 记录的 6 条存量失败清零, 三点现象复验均"已消失"）; ③`26-10-01-2218-perf-mainloop-max-tasks-adaptive` **重归因 + 复测, 状态仍 Open 待拍板**（P2 复测稳态 2.87→2.139 s、漂移 1.22→0.801 s 已进 1.0 s 门限; 原方案 `max_tasks_per_tick` 自适应经查非有效旋钮 —— 成本在同步线 `_refresh_torrents` 的逐种子内联请求, 不受任务线配额约束; 改道"灌入期每拍请求预算"并判断倾向不做 → 建议 Dropped）。  
> 最后活动: 2026-10-08 04:27

**Refs:** memory-bank/tasks/26-10-08-webui-perf-issues-closing.md, memory-bank/issues/26-10-01-2218-perf-webui-api-state-full-scan.html, memory-bank/issues/26-09-21-1408-perf-webui-shows-view-full-rebuild.html, memory-bank/issues/26-10-01-2218-perf-mainloop-max-tasks-adaptive.html, memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html

## 已完成(详情见档案, 不在此复述)

- 三条 issue 逐项重锚 + 裁定（锚点整体漂移: `runtime.py:775→1124`、`views.py:412→800`、`state.py:33→35`）。
- e2e 全量复跑 **94 passed / 10 skipped / 0 failed**（3.5m）—— 顺带发现本机缺 `@playwright/test`, `npm install` 后跑通。
- P2 仿真复测: verdict OK, avg_interval=2.139 s / drift_max=0.801 s（原 2.87 / 1.22）, tracebacks=0。
- 新件入池 `26-10-08-0411-perf-webui-api-state-pagination`（perf / standard / topic `webui-polling`）。
- test.full **2771 passed + 4 skipped / 99%**（42.68s）见基线 [26-10-08-0427](../testing/baselines/26-10-08-0427-webui-perf-issues-closing.md)（相对上基线逐位持平, 本轮 `src/`+`tests/` 零改动）。
- `kb.index` 20 个生成物 + `kb.check` 全绿（主键纪律 / 认领链双向闭环 / 回写措辞 / 日期守卫）。

## 正在进行

- 无 —— 三条建议的文档侧动作已全部落地。

## 未决项

- **mainloop 件是否走 Dropped**（待用户拍板）: 倾向不做（复测已进稳态门限 + 原方案无效 + 症状为一次性代价）; 若拍板做, 先做 §05「仍待查」的漂移构成拆分再动码。拍板后由 agent 改徽标 + meta + 追加日志 + `kb.index`。
- **api-state 残留件（分页）与 `26-10-07-1420` 组行 hash 引用式的先后** —— 两者都要动响应体形状, 建议一起排; 共同前置 = 全量轮成本构成实测拆分。
- `26-10-07-1420-refactor-webui-pending-ver-gate-redundancy`（pending_ver 门控冗余评估）与本次定案解耦, 按其原计划另拍板。
- 存量 cap 债务（切片数 93 > 70）—— 本会话不修, 另开会话清理。

