# 26-10-02-webui-multi-ctx-actions — WEBUI 多选右键菜单四项 + 跳检菜单开关

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-03
**Summary:** 计划 26-10-02-1955 五波六提交全部完成并推送: W1 配置键 web.skip_check_menu 全链路 + flags 端点/skip-check 403 fail-closed gate/前端菜单门控(b71e1291, dff534b6); W2 批量限速/移动(a4bfabbf); W3 批量跳检 ops 聚合(f5f62726); W4 多选导出——D1 拍板 A 前端循环逐个下载, 归档端点未建, 零后端改动(4c0c6f66); W5 冒烟走查汇总——harness 跳检开关两态参数化 + smoke 补四项齐/单选跳检项/确认后提交/限速与导出回执 toast/off 态精简轮, 双皮肤实跑(9f1e2a32)。拍板: D1=A(推翻计划推荐的后端 zip) / D2=是 fail-closed / D3=留空不改。基线 26-10-03-0542: 2309 passed + 3 skipped / 99%。
**Topics:** webui-multi-ctx-actions
**Refs:** memory-bank/plans/26-10-02-1955-plan-webui-multi-ctx-actions.html,memory-bank/issues/26-10-01-2119-feat-webui-batch-move-skipcheck.html

## 原始请求

用户指派出计划(26-10-02 19:55 切片): R1 多选右键补 限速…/移动…/跳检…/导出 .torrent 四项; R2 跳检项(单选+多选)加配置开关 `web.skip_check_menu` 默认关。计划文档 `memory-bank/plans/26-10-02-1955-plan-webui-multi-ctx-actions.html`, 五波(W1 开关全链路 → W2/W3/W4 批量动作 → W5 冒烟收尾), 三决策点 D1/D2/D3。

## 思考过程与决策

- **D1 批量导出形态 → A(前端循环逐个触发下载)**: 推翻了计划推荐的后端 zip 归档端点。实施取 D1=A —— 复用单 hash 导出端点, 前端 `exportMulti()` 按 `selHashSet` 全量展开串行逐个下载, **归档端点未建**(计划 W4 的 `POST /api/torrents/export-archive` 未实施), 路由金清单实际 +1(flags) 而非计划写的 +2。理由: 零后端改动、单选/多选同一套口径, 组选中展开由 selHashSet 权威派生。
- **D2 服务端同步封禁 → 是(fail-closed)**: skip-check 端点 403 gate 只放 web 入口, rule 源零改动; flags 端点与 gate 现读实时配置(热重载不持旧 Config)。
- **D3 批量限速留空 → 留空不改**: 双输入各自独立, 留空方向不进载荷(冒烟断言 `!("dl_limit" in posted)` 钉死该口径)。

## 实现计划

计划文档 §05 五波: W1 开关配置系统全链路(models/loaders/validate/GUI schema/minimal.yml/keys.md + `GET /api/webui/flags` + skip-check 端点 403 fail-closed + 前端 flags 显隐) / W2 bulk 扩 limits+location(qbapi 原生收 hash 列表单次调用) / W3 bulk skip_check 走 ops 逐 hash 串行聚合回执(样板 `_bulk_recheck_via_ops`) / W4 多选导出 / W5 冒烟走查+收尾。bulk 通道 RESYNC/DEFERRED 两表已含 bulk_torrents ⇒ 扩动作零表改。

## 子任务状态表

| 波次 | 内容 | 提交 | 状态 |
|---|---|---|---|
| W1a | `web.skip_check_menu` 配置系统全链路(models/loaders/validate/GUI schema/minimal.yml/keys.md/键面 fixture) | `b71e1291` | Done |
| W1b | `GET /api/webui/flags` 端点 + skip-check 端点 403 gate + 前端 flags 显隐门控 | `dff534b6` | Done |
| W2 | 多选右键批量限速/移动(bulk 扩 limits/location, 对话框前置, 留空方向不提交) | `a4bfabbf` | Done |
| W3 | 多选右键批量跳检(bulk 扩 skip_check 走 ops 逐 hash 串行聚合, danger 确认框) | `f5f62726` | Done |
| W4 | 多选右键「导出 .torrent」(D1=A: exportMulti 按 selHashSet 前端循环, 零后端改动) | `4c0c6f66` | Done |
| W5 | 冒烟走查汇总 + 收尾(ui_harness 两态 / ui_smoke 汇总断言 / 基线 / 归档) | `9f1e2a32` | Done |

## 进度日志

- **2026-10-02 19:55**: 计划已出, 三决策点待拍板(零代码)。
- **2026-10-02 22:00 → 2026-10-03 05:08**(并行会话实施): W1 拆两笔(b71e1291 配置键 / dff534b6 flags 端点+gate+门控), W2 a4bfabbf, W3 f5f62726, W4 4c0c6f66(D1 拍板=A)。
- **2026-10-03 05:45**(W5 收尾, 本轮): A 部分——`ui_harness.py` 跳检开关两态参数化(`--skip-check-menu on|off`, 默认 on; 起盘日志带旗标值); `ui_smoke.cjs` 补 `--skip-check` 参数 + 五处汇总断言(多选菜单四项齐 / 单选菜单含跳检项 / 确认后提交 bulk action=skip_check——danger 确认钮是 `.bt.danger-solid` 非 `.primary` / 限速+导出成功回执 toast / off 态精简轮: flags 取到布尔 false + 单选多选菜单都不渲染跳检项且其余项照常)。实测: on 态双皮肤新断言全 PASS, off 态双皮肤 10/10 全绿(含「无 console.error / pageerror」显式判定); test.quick 2309 passed + 3 skipped。既有 flaky「冒烟整体执行 click 超时」经 HEAD stash 对照定案为存量(stash 前后同位置失败), 与本任务无关——判别法已录 pitfalls/testing/smoke.md。B 部分——基线切片 26-10-03-0542(2309 passed + 3 skipped / 99%, 13,452 语句, test.full 32.13s @ 9f1e2a32); 本档案立档; 计划 doc-status → Done; 已完成条目迁出 progress/implemented-webui.md; smoke.md 端口占用条复发 +1。
