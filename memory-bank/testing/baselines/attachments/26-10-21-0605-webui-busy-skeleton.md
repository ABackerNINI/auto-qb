# 3971 passed + 10 skipped —— 前端 busy 骨架收敛为三单点(issue 26-10-20-2231)

> 摘要: 认领修复 issue 26-10-20-2231(fe-dialogs-js-boilerplate-dup) —— dialogs/config_hub 手抄 19 处的「busy → try → 失败反馈 → finally 复位」骨架收敛为 dialogs.js 三单点(_mgrRun / _panelLoad / _postWaitCmd), 行为零变化
> 基线时间: 2026-10-21 06:05
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-dialogs-js-boilerplate-dup.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 改动落盘后实测输出:

```text
TOTAL                                                20471     91   7012     94    99%
3971 passed, 10 skipped in 205.15s (0:03:25)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 动手前在同一棵树上(95baf46b)先跑了一遍全量取基线, 同样全绿 —— 本次 passed +1 即新增守阵 `test_frontend_busy_skeleton_single_point`, 其余逐位持平。
- 真浏览器侧: `commands run dev.e2e` 全量集 336 passed / 10 skipped(11.0m) —— 双皮肤 views(渲染健康/设置页/流量与限速合并卡/工具参数单位控件)与本轮改动面(tt 面板加载族 / tm 面板 / 一键导入)全绿。
- 定向: `commands run test.one -- tests/test_webui_trigger_registry.py tests/test_webui_static_dom_panel.py` 56 passed。
- 红验两支均判红后还原: ①拆 `_panelLoad` finally 复位 → 守阵红; ②回潮一处裸 busy 置位(`this.statsLoading = true`)→ 反向断言红。
- 过程性一红(非既有失败): POST 调用点收敛进 `_postWaitCmd` 后, `test_trigger_registry_call_sites_exact` 判「表外项」—— 按登记表口径把 triggers.js `calls` 表四处旧登记(_metaBulk / submitSpeedOverride / toggleAltSpeed / submitAltLimits)并为统一出口一行(scope = 调用方并集 sel|anchor|none)后复绿。
- 耗时区间: 全量两遍 203.7s / 207.2s(单次采样无意义, 记区间); e2e 一遍 660.7s(11.0m)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/dialogs.js` | 新增 `_mgrRun` / `_panelLoad` / `_postWaitCmd` 三个骨架单点(节首注释含分族依据); 14 处调用点改写: mgr CRUD 5(loadStats 侧栏见下) + 面板加载 5(loadStats/loadMgr/loadLogs/loadSpeedMode/loadHistory) + POST+waitCmd 4(_metaBulk/submitSpeedOverride/toggleAltSpeed/submitAltLimits); 文件头注明单点承载 |
| `src/auto_qb/webui/static/shared/config_hub.js` | tm 族 5 处改接 `_panelLoad`: tmLoad(authGated:false + keepErr + onErr 失败装配 + onFinally loaded 置位) / tmSave / tmAutostart(onErr 回滚勾选态) / tmPickLoad(onErr 清 dirs) / hubImportSites(errToast toast 通道); 文件头注明单点在 dialogs.js |
| `src/auto_qb/webui/static/shared/triggers.js` | TRIGGER_DEFS.calls: 四处 POST 旧登记并为 `_postWaitCmd` 一行(ep/scope/why 写明统一出口与调用方分派) |
| `tests/test_webui_static_dom_panel.py` | 新增 `test_frontend_busy_skeleton_single_point`(三单点在册 + 19 处接线数对账 + finally 保底 + 裸 busy 置位反向断言); 文件头测试计划同步登记 |
| `memory-bank/conventions/webui.md` | 新增「WEB UI busy 骨架单点」节(与同 issue 的 CSS 共用规则族节并列) |
