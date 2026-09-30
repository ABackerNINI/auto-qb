# 基线 · 1844 passed + 3 skipped / 90% —— WEBUI 键鼠割裂方案 B(点击落光标 + 回落视口就近)

> 摘要: 报告 reports/26-09-30-1806 推荐方案 B 全量实施(用户直接拍板, 未另出计划 HTML):
> ①无光标回落极值行→视口就近行(shortcuts.js 新增 `_kbViewportRow`: group/torrent 窗口化走
> `_rowPre` 前缀和同源校验, 其余扫渲染行可见性, 解析失败退回旧口径; `_kbMove` cur<0 分支改走它,
> 修「鼠标在顶部按一下 ↑ 视口跳到底」) ②selection.js 五个点击入口按所在行回写 kbCursor
> (写在修饰键分支之前, Ctrl/Shift 点击同样落光标; 落光标≠选中) ③groups/shows 两处明细成员行
> 补 kb-cursor 绑定(报告「视觉双轨已就位」对成员行不成立, 已补齐) ④_kbHint 文案与注释同步
> ⑤守阵 test_web_shortcuts.py 16→17。纯前端(JS/模板), 无 Python src 改动、无配置键、无后端改动。
> 基线时间: 2026-09-30 19:53 初测(01e47169+本轮), 提交前合流远端内核 P1(2174a568)后复核 20:10;
> 树 = develop @ 2174a568(内核 P0+P1) + 本轮 6 文件改动(未提交)。

TOTAL **1851 passed + 3 skipped / 90%**(12965 语句 / 1054 未覆盖 / 4382 分支 / 430 partial,
pytest 26.98s, test.full 27.8s, rc=0, 合流后终树复核) —— 较最新基线 26-09-30-1912(内核 P0,
1843+3 / 91%): 本轮新守阵 +1(test_click_lands_cursor_and_viewport_fallback), 远端合流内核
P1 提交 2174a568(logging/notify 模块化 + 托盘 ctx.notify)带 +7; 其树当时未提交的内核改动
使语句数 13010 与本树 12965 的差异属跨 clone 工作树时点差, 非本轮所致 —— 本轮 src 改动全为
JS/模板, 不进 coverage 统计。

## 本轮改动面(6 文件)

- shortcuts.js: `_kbMove` 回落分支 + 新增 `_kbViewportRow`(~40 行) + `_kbHint` 文案 + 头注设计单点。
- selection.js: 五入口(onGroupClick/onMemberClick/onTorrentClick/onShowClick/onShowEpClick)各一行
  回写 + 头注「键鼠衔接」节。
- state.js: kbCursor 注释补方案 B 口径(纯注释)。
- tpl/groups.html + tpl/shows.html: 明细成员行 class 补 `'kb-cursor': isKbCursor('torrent', m.hash)`。
- test_web_shortcuts.py: +1 测试 + 模板断言 3→5 行 + docstring 测试计划同步。

## 口径与边界

- 成员行点击落 `{kind:"torrent"}` 不在组行线性链(决策② 成员行 vNext): 下一次 ↑↓ 经视口就近回落
  落到链行; 动作键目标解析(`_kbTargets`)立即按该 hash 生效。
- 滚动跟随仍只发生在键盘路径(`_kbApplyCursor`), 点击路径不滚动(点击行必在视口内, 最小滚动=no-op)。
- 方案 C(roving tabindex)缓议, B 的状态模型与 C 兼容。
