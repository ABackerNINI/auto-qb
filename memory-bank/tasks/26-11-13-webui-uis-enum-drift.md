# 26-11-13-webui-uis-enum-drift — web_shortcuts UIS 三皮肤旧枚举收编 webui_helpers._UI_ALL 单点(issue 26-11-13-0443)

**Status:** In Progress
**Added:** 2026-11-13
**Updated:** 2026-11-13
**Summary:** web_shortcuts UIS 三皮肤旧枚举收编 webui_helpers._UI_ALL 单点(issue 26-11-13-0443)
**Topics:** webui-uis-enum-drift
**Refs:** memory-bank/issues/26-11-13-0443-test-webui-uis-enum-drift.html, memory-bank/tasks/26-11-12-webui-kbd-hints.md

## 本篇只回答

issue 26-11-13-0443(UIS 三皮肤旧枚举 vs `_UI_ALL` 四皮肤现口径漂移)是怎么修的、修到什么程度:修法取舍、消费面取证修正、评审循环与验证数字。

## 原始请求

1. 用户指派:`fix memory-bank/issues/26-11-13-0443-test-webui-uis-enum-drift.html`(单轮,无计划文档;认领 = 用户指派,合法)。

## 思考过程与决策

- **修法取舍**:issue §03 三选项(引用对齐 / 原地补 flux / 原地补+注记)中取「彻底去名」—— 删除 `web_shortcuts_support.py` 的 `UIS` 枚举,三个消费方改 `from webui_helpers import _UI_ALL` 直连单点。理由:仓库既有惯例是消费方直连 `webui_helpers._UI_ALL`(webui_dom_panel_support 同型),保留 `UIS = _UI_ALL` 别名会留下第二种词汇,与「口径单点」文化相悖。
- **消费面取证修正**:issue §02 称 cursor/drawer「不受本次枚举影响面」不实 —— `for ui in UIS` 循环共三处(registry:141 / cursor:481 / drawer:857,取证 2026-11-13),cursor/drawer 一并扩面。扩面前逐条预核 flux 静态面成立:tpl-manifest 挂 shortcuts.js(idx 75)先于 app.js(idx 79);views.css 含 `--sel-bg` 令牌族 / 左色条并列规则 / `.member-row position: relative`;dialogs.css 含 dock 动画裁剪与退场 absolute 底缘锚定 —— 纯扩面,无真实差异(issue §03 预判成立,未另立缺陷)。
- **连带如实更新**:测试 `test_mount_pairing_three_shells` → `test_mount_pairing_all_shells`(头部测试计划条目同步);三处循环周边「三皮肤」文案 → 「四皮肤」。
- **范围守恒**:drawer 另三处内联硬编码 `("atlas", "console", "prism")` 循环(lines 280/374/701,实测)是同类漂移的相邻面,超出本 issue 范围未动,已在 issue 正文留痕;是否入池等用户拍板。
- **环境坑复发**:收尾闸门预跑踩坑档 `pitfalls/testing/env3-test-run-prereqs.md`(node PATH 只做了会话级前插),r4 电池 69 条「无 node」环境态假红;带 `PATH="$HOME/.local/node/bin:$PATH"` 前置复跑全绿,复发 +1 已回写坑档。

## 实现计划

总体思路(单轮小修,无计划文档):①支撑模块删枚举留注记 → ②三消费方接线改名 → ③周边文案如实更新 → ④定向测试验证 → ⑤issue 翻 Done + 正文补实际修法 → ⑥评审循环 → ⑦收尾 DoD(坑档/立档/基线/切片)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | web_shortcuts_support.py 删 UIS 枚举留单点注记 | Done(2026-11-13) |
| 2 | registry/cursor/drawer 三消费方 `from webui_helpers import _UI_ALL` 接线 | Done(2026-11-13) |
| 3 | test_mount_pairing_all_shells 改名 + 「三皮肤→四皮肤」文案如实更新 | Done(2026-11-13) |
| 4 | 定向验证:test.one 四件 36 passed(flux 支全绿) | Done(2026-11-13) |
| 5 | issue 翻 Done(kb.status)+ 正文补实际修法/验证 | Done(2026-11-13) |
| 6 | 评审循环 R1(4 发现全修)→ R2(零发现)→ R3 坑档增量复评(零发现) | Done(2026-11-13) |
| 7 | 收尾 DoD:坑档复发+1 / 立档 / test.full+基线切片 / kb.wrap | Done(2026-11-13) |

## 进度日志

### R0 · 立档 (2026-11-13)

用户指派修复 issue 26-11-13-0443(单轮)。修复 + 验证 + issue 翻 Done 完成;评审三轮:R1 全能档单代理 4 发现(minor ×4,`review.check` 4/4 过检)全修,R2 复评零发现 4/4 落实,R3 坑档增量复评零发现(基哈希 d01d64368b74);收尾 DoD 完成:坑档 `env3-test-run-prereqs` 复发+1 + `kb.index` 再生、本档案立档(阈值第 2 条:改动 ≥3 源文件)、test.full 实测 6084 passed + 19 skipped 覆盖 99%(基线切片 26-11-13-0715,较 0629 +3: +1 TZ 批守阵用例、+2 跨 clone 环境差异带,零新增用例零回归)、会话切片 26-11-13-0716。**待用户「提交」指令**;入池候选两组待拍板(drawer 三处内联硬编码三皮肤循环 lines 280/374/701 / engine 头部同款旧导语,均为相邻面非本件范围)。
