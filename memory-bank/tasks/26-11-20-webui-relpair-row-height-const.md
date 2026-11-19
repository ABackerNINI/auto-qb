# 26-11-20-webui-relpair-row-height-const — WEBUI 双排A→B行高恒等修正(负margin吃padding锁行高)

**Status:** Done
**Added:** 2026-11-20
**Updated:** 2026-11-20
**Summary:** WEBUI 双排A→B行高恒等修正: 整组迁移双排路径使行高变化(+8.9px), 违反最初设计判据「双排不得使行高变化」; 用户拍板负 margin 修法(row_lang.css has-relpair margin:-5px 0), e2e 四皮肤逐行差分守阵 + 静态钉 + 约定回写三层钉住, 评审 3 轮检 6/6 修 6, test.full 6472P/23S 99% 全绿(见 kb.baseline)
**Topics:** webui-relpair-row-height-const

## 本篇只回答

双排 A→B 路径为什么会改变主表行高、按最初设计判据(双排不得使行高变化)是怎么修的、守阵怎么钉。领域口径单点在 conventions/webui.md「行高恒等」条, 本篇是取证与决策档案。

## 原始请求

1. 用户报(2026-11-19): 「WEBUI整组移动双排路径导致行高变化, 按最初的设计, 双排路径不能使行高变化」—— 桩上复现 + 四皮肤实测后给三方案带实测数字让用户拍板。
2. 用户拍板(2026-11-19): 选「负 margin 吃 padding (Recommended)」。

## 思考过程与决策

- **取证**(桩 + Playwright 路由改写 /api/state 造 pair 行): pair 块 30.59px = 2×14.3px(11px/1.3) + 2px gap; 主表行内容盒 21.69px(组行, 14px/21.7 行盒驱动, 基线 42.69px)/ 22.05px(种子行, 基线 43.05px)→ 双排行 51.59px, +8.9px; 行高决定格 = g-name/g-stat 行盒, path 单排格(18.59px)不是驱动格。逐行 A/B 差分(两次加载按 key 对齐)证实增量分布 {组行 8.9, 种子行 8.54}。
- **设计判据溯源**: 最初计划 26-11-07-2344 S4 验收「行高不因两排溢出」+ 风险行「行高按需增长仅限两排行」两处表述打架, 实现取了放行侧; RM04-15 真机用例原有「行高等值断言」随 v1 徽标退役而退役(issue 26-11-11-0553 复验节留痕 pair 53 vs 44)。用户判据 = 恢复该恒等。
- **方案对比**: A 负 margin 吃 padding(margin-box 20.59 ≤ 内容盒, 字号 11px 不缩, 行高逐像素相等; 代价: 双排文字距行缘 10px→5.5px)—— 用户拍板; B 缩字号 9.5~10px/1.1 装内容盒(可读性差); C 全表统一抬高(改基线密度)。
- **e2e 钉法取舍**: route 改写翻腿(plain 腿)在增量轮询下死路 —— 版本未变时桩不回传行(polling.js 响应体趋零), app 永远吃不到去标注的全量行(实测 15s 不清零, 坑档 testing/route-leg-flip-incremental-polling); 改 vm 注入(delta 不冲注入, 实测跨 3+ 轮询周期存活), 同页 A/B 两腿逐行差分。
- **A 腿前提改判**(评审 r1→r2): 「A 腿零 pair」强前提恒红 —— 组级聚合 group_relocate 按 _PRIORITY 取最高态且单 job_id 不出 mixed, 桩 5 job 使组页本就有 2 个真 pair 组({t0 moving,t1 armed}→moving / {t2 failed,t3 done}→failed); 改按行状态分类只判「A 单排→B 双排」行, A 即 pair 行显式排除 + 排除数留痕 + 判定行数>0 守卫。

## 实现计划

总体思路: 一行 CSS 修法 + 三层守阵(几何 e2e / 静态钉 / 约定回写), 全程桩上取证与红绿双验, 免真机轨(纯 CSS 渲染面, relocate-key-change-pad 先例)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 取证: 桩上路由改写造 pair 行, 单/双排行高与几何构成实测(四皮肤) | Done(2026-11-19) |
| 2 | 三方案对比带实测数字, 用户拍板负 margin | Done(2026-11-19) |
| 3 | row_lang.css has-relpair margin:-5px 0 + 注释行高恒等口径改写 | Done(2026-11-19) |
| 4 | e2e relocate-pair-row-height.spec 四皮肤 vm 注入 A/B 逐行差分, 红绿双验(摘修正四皮肤全红) | Done(2026-11-20) |
| 5 | 静态钉 test_p1_pair_cell_margin_keeps_row_height_constant + docstring 测试计划同步 | Done(2026-11-19) |
| 6 | conventions/webui.md「行高恒等」条回写 | Done(2026-11-19) |
| 7 | 评审 3 轮(分面派遣 2, 检 6/6 修 6, r3 零发现收口) | Done(2026-11-20) |
| 8 | 全量 test.full 6472P/23S 99% 全绿(见 kb.baseline) + 基线切片 | Done(2026-11-20) |

## 进度日志

### R0 · 立档 (2026-11-20)

取证→拍板→修法→守阵→评审(3 轮检 6/6 修 6, blocker 0)→全量绿, 全链收口; 详情见切片 webui-relpair-row-height-const 与坑档 testing/route-leg-flip-incremental-polling。改动随本专题入库(触发词「提交」走 ship.commit)。
