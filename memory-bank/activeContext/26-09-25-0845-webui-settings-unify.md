# 设置页合一: 移除经典设置页 + HR 站点状态并入「HR 在线核实」

> 摘要: 用户指令「将新版设置页的HR在线核实与HR站点状态合并, 移除旧版设置页」—— 经典页整块删除(含切换机制),
> HR 站点状态从独立卡片降为 hr_check 分区页尾只读块; 顺带清掉只被旧页引用的 JS/CSS 死代码; 机检锚点同步。
> 触发: 设置页, Console Hub, 经典设置页, HR 站点状态, HR 在线核实, hub.mode, hubSetMode, 死代码清理, 两套 UI 成对改
> 最后活动: 2026-09-25 08:45

## 状态

**Done**(2026-09-25, 已入库 `7fcdc9c`)。13 文件 +159/−1845。

## 改动面

- **模板(prism/atlas 成对)**: 删 `<main v-if="page==='settings' && !hub.mode" class="ce-page">` 整块(旧版图形化配置页,
  含其侧栏「运行日志 / HR 站点状态」章节与 YAML 预览); hub 主入口收成 `page==='settings'`; 删「新版界面/经典界面」
  切换按钮; 独立 `__hr` 分区模板删除, 状态块并入通用分区渲染尾部(`<template v-if="hub.view === 'hr_check'">`)。
- **config_hub.js**: 删 `HUB_MODE_KEY`/`hub.mode`/`hubSetMode`; `hubCards` 不再 push `__hr` 卡;
  `hubGo('hr_check')` 打开分区时拉一次 `/api/hr/status`; hr_check 的 desc/lede 改写说明页尾附站点现状。
- **hr_status.js**: 删 `openHrStatus`(唯一调用方在旧页); 头注释改单入口口径。
- **死代码(只删「本次改动致死」, 既有死代码按范围守恒不动)**: `dialogs.js openLogs`;
  `config_editor.js` 的 `cfgGroups`/`cfgActive`/`cfgTogglePreview`+preview 四状态/`cfgAddStart`/`cfgCurveOpen|Toggle`/
  `cfgCurvePeriodHint`/`activeGroup`/`openRules`/`openCurves`; `config_rules.js` 的 `cfgRuleItems`/`cfgRuleKey`/
  `cfgRuleCollapsed|Toggle`/`cfgPickerOpen|IsOpen`/`cfgPluginReplace`/`cfgIgnoreNextAdd`(后两个级联死亡补删)。
  甄别法: 工作区语料零引用 + HEAD 语料对照, 区分「本次致死 vs 本来已死」(`pollLabel`/`cfgSpec*`/`limitRows` 等既有死的不动)。
- **死 CSS(两主题)**: ce-grid/ce-side*/ce-master*/ce-head*/ce-card/ce-banner/ce-fields/ce-rule-*/ce-plugins*/
  ce-curve-*(旧曲线卡)/ce-preview*/ce-actions/ce-inline-*/ce-add-*/ce-picker*/ce-hint/ce-empty-hint/ce-pseudo/
  logs-embed 系(保留 `.logs-note`)/icog-*/ico-log/`.sh-r`; 媒体查询里的残留行一并删。
  ⚠ `icog-*` 在 HEAD 是 `'icog-' + key` 动态拼接, 字面检索会误判成「本来已死」—— 拼接点随旧页删掉后整族才算死。
  ⚠ 混合选择器(按下反馈/下拉外观/caret 过渡)只摘死分支, 不能整条删。
- **机检**: `test_frontend_hr_status_fields_match_backend` 锚点从四入口(两 UI × 经典 `__hr` 章节 + hub `__hr` 视图)
  改为两入口(`hub.view === 'hr_check'` 唯一性断言 + 闭合标签切块)。
- **知识库回写**: systemPatterns/web-config-editor.md(前端结构/模式/端点/两套并存条目)、modules/overview.md(HR 状态入口)、
  checklists/manual-walkthrough.md(切换入口)、progress/implemented-webui.md(沉淀首条)。

## 验证

- 全量 `commands run test.full`: **1597 passed + 1 skipped**(与 [testing/baseline.md](../testing/baseline.md) 一致;
  曾在本 shell 恒红的 2 条 GBK 假红已随远端 a760da0 修复, 现在 0 failed)。
- 双主题真浏览器冒烟: `create_app(假 manager)` 起本地服务(脚本一次性, 未留存) ——
  atlas(/) 与 prism(/prism/) 各验: 登录 → hub 首页 10 卡且只有一张 HR 卡 → HR 分区(说明/字段/页尾「站点状态」块) →
  拦截 `/api/hr/status` 注入站点数据后渲染正常(含熔断/过期/不放行异常态) → 运行日志视图 → 搜索直达;
  结构断言 `main.ce-page` 恰 1 个、全页无「经典」字样按钮。截图核验样式无缺损。
- 反向校验: 「html/js 引用类都有 CSS 定义」缺失集修剪前后不扩大; 死类集在 CSS 全库归零; 花括号配平。

## 遗留

- 立档阈值判断: 本次属结构性 UI 改动(非纯文案), 是否值得 `tasks/` 立档待用户定。
- 落 develop 方式: 远端 develop 在会话中前进(1516bd6 → 3e31c1f)且与本改动唯一交集 tests/test_web.py
  区域不重叠 —— 走「临时分支落盘 → 基于新 develop cherry-pick」落回, 未经 rebase/stash。
