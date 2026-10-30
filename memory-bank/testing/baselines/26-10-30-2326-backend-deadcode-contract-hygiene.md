# 4180 passed, 2 skipped —— 第二次全项目评审 P3 合并池位收口: 死码批量清理与契约卫生

> 摘要: 第二次全项目评审 P3 合并池位收口: 死码批量清理与契约卫生
> 基线时间: 2026-10-30 23:26
**Refs:** memory-bank/tasks/26-10-30-backend-deadcode-contract-hygiene.md

## 验收数字

`commands run test.full` 实测(2026-10-30, Windows, 全部清理落盘后):

```
TOTAL                                                21134     96   7152    100    99%
4180 passed, 2 skipped in 117.33s (0:01:57)
```

- **汇总行**: **4180 passed / 2 skipped**, 墙时 **117.33s**, 区间口径见 testing/baseline.md「耗时与覆盖率口径」。
- **TOTAL 表**: 语句 **21134** / 未覆盖 **96** / 分支 **7152** / partial **100** / 覆盖率 **99%**。

工具侧(本轮动了 gtm 四文件, `commands run test.gtm` 实测, 独立 uv 项目自带套件):

```
TOTAL                   1962      8    468      6    99%
426 passed, 2 skipped, 1 warning in 62.01s (0:01:02)
```

- 红验说明: 本轮全部为行为零差纯卫生(删死码/对齐注释与文档), 无新守阵 —— 等价性由双侧全量绿 + 六个改动态 JS `node --check` 全过 + A-07 真 bool 等价论证(调用方只喂 `source_enabled()` 严格 bool)构成, 不设独立红验。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/core/modules/ops_mod.py` | A-08: `skip_submit` 未消费解包 `job`→`_`; `_skip_begin` 死变量 `prefix` 删除 |
| `src/auto_qb/hr/discovery.py` | B-02: 死导入 `is_loopback_host` / `_content_length` 删除 |
| `src/auto_qb/webui/static/shared/drawer_store.js` | F2-01: `_dtMergeRows` 只写不读的 `seen` Set 两行删除 |
| `src/auto_qb/webui/static/shared/drawer_tpl/05-trackers-health-groups-low.js` | F2-02: 无调用点 `rerender` 函数删除 |
| `src/auto_qb/webui/static/shared/drawer_tpl/06-trackers-table-collapsed.js` | F2-02: 无调用点 `rerender` 函数删除 |
| `src/auto_qb/webui/static/shared/drawer_tpl/09-peers-density-collapsed.js` | F2-02: 整帧重建分支死 `chips` 两行删除(barHtml 构建器是真单点) |
| `tools/global-traffic-monitor/src/gtm/server.py` | T-05: 死导入 `Config` 删除 |
| `tools/global-traffic-monitor/src/gtm/__main__.py` | T-05: F841 `uninstall` 赋值摘除(add_parser 副作用不变) |
| `tools/global-traffic-monitor/src/gtm/config.py` | T-05: `migrate_legacy_config` 未消费解包 `errors`→`_` |
| `extensions/hr-fetch-proxy/background.js` | GH-02: `poll-now` 死消息分支删除(全仓无发送方) |
| `src/auto_qb/webui/runtime.py` | 顺手: 死导入 `DEFERRED_RECEIPT_COMMANDS` 删除 |
| `src/auto_qb/rules/base.py` | 顺手: 死导入 `TorrentDictionary` 删除 |
| `src/auto_qb/webui/module.py` | 顺手: 注释「客户顿」→「客户端」 |
| `src/auto_qb/core/traffic_source/agent.py` | A-07: `ensure_running` 门侧判据 `enabled is not True`→`enabled is False`(与 `paths.source_enabled` 恒等判据同族, 真 bool 等价) |
| `src/auto_qb/webui/static/shared/app.js` | F1-02: 段头注「见 shared/drawer_tabs.js」改指各变体 `rowsFn`(该文件已删) |
| `tools/global-traffic-monitor/src/gtm/__init__.py` | T-04: 进度注追平 S0-S9(按计划档状态行) + 通知描述改零读盘直达口径 |
| `tools/global-traffic-monitor/README.md` | T-04: 开头段「重读历史文件」改零读盘直达口径(与「通知 (S4)」段及 notifier 头注取齐) |
| `memory-bank/issues/26-10-30-0620-chore-dead-code-batch-cleanup-2.html` | 认领: Open → In Progress → Done, 状态日志记复验与修法 |
| `memory-bank/issues/26-10-30-0620-chore-annotation-comment-contract-hygiene.html` | 认领: Open → In Progress → Done, 状态日志记复验与修法 |
| `memory-bank/tasks/26-10-30-backend-deadcode-contract-hygiene.md` | 认领档案(本池位收口立档) |
| `memory-bank/testing/baselines/26-10-30-2326-backend-deadcode-contract-hygiene.md` | 本切片 |
