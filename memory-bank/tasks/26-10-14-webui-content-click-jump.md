# 26-10-14-webui-content-click-jump — 内容页树表点击跳动: 整帧换滚动位自保 + 动画重播(四复查定案)

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-18
**Summary:** 用户四复查「点击跳动, 持续 0.x 秒后回到原位」定案(四轮修复史): 一跳 = W5 反应式化 + _dtMergeRows(提交 48b82ca1); 二跳 = 10/11 补 withScroll(提交 cea6397a, 缺口收但未命中真机形态); 三跳 = 逐帧采样探针实锤根因 —— **anchFill 每帧摘插锚 = 元素移除再插入 = CSS 入场动画(page-in, translateY(4px)+淡入, .22s)在 atlas/console 每次点击重渲时重播**, 整表瞬跳 4px 后缓回, 完全匹配「0.x 秒后回位」(prism 无该动画规则故前三轮 prism 探针全干净). 修法 = 两皮肤 views.css 抽屉作用域 `.drawer .group-head, .drawer .group-table, .drawer .h-cell .arrow { animation: none; }`. 守阵 = dt-live-update #9 逐帧采样(rAF+4ms 双路, POST 走真实端点保 waitCmd 链, GET 翻转数据模拟真后端)双皮肤绿 + 红验通过. 验证数字见 Refs 基线切片 26-10-14-1401.

**Refs:** memory-bank/reports/26-10-14-0136-report-webui-detail-table-rebuild-review.html,memory-bank/testing/baselines/26-10-14-1401-webui-content-click-jump.md,memory-bank/pitfalls/web-ui/frame-swap-scroll-reset.md
**Topics:** webui-detail-table-rebuild

## 原始请求

> 修复: 种子详情内容页表格点击跳动的问题
> 附录: 26-10-14-0136-report-webui-detail-table-rebuild-review.html

## 思考过程与决策

- 报告 §02
- §02 问题面: 点击跳动(atlas 85px).
- §3.1 归因: 数据回路全帧重建.
- 行身份 ref-stable(_dtMergeRows).
- 缺口: 10/11 缺 withScroll(01-09 有).
- 修法: 整帧换收进 withScroll.
- 未复现: 探针 maxRowDev=0, scrollVals=[300].
- 结论: 缺口收, 真机形态分账未命中.

## 实现计划

1. 10/11 变体 js: replaceChildren + anchFill 收进 H.withScroll.
2. 既有守阵/e2e 不变(列集/几何/交互件不改).
3. test.full + e2e @fast 全量验, 基线切片, KB回写.

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 10/11 整帧换收进 withScroll | ✅ |
| 探针复前形态取证 | ✅ |
| test.full + e2e @fast 全绿 | ✅ |
| 基线切片 + KB回写 | ✅ |

## 进度日志

- 26-10-14 11:5x: sync 已同步 de83fbe8. 读报告 §02/§3.1, 定位缺口(10/11 缺 withScroll).
- 26-10-14 12:0x: 修两变体 js; 探针(40文件桩, 滚300, 屏内徽章, rAF)复前形态仍 maxRowDev=0 —— 85px 未复现, 缺口收为事实; test.full 3205+4 skip 99%, e2e @fast 134 绿; 基线切片落, KB回写随本专题入库.
- 26-10-14 13:xx(四复查, 根因翻案): sync 已同步 fb58a9e4→cea6397a. 用户关键线索「跳动持续 0.x 秒后回到原位」⇒ 前三轮探针全因**粗间隔/比对式量具**错过瞬态. 复探针(4ms 逐帧 + rAF 双路)在 atlas 抓到: 参考行 rect +4px ~62ms 回位, scrollTop 不变; 元素级归因(probe5)实锤换帧瞬间 `.group-table` 计算 transform=`matrix(1,0,0,1,0,4)` 后按 .22s ease-out 缓回 = **page-in 动画重播**(anchFill 摘插锚 = 元素移除再插入 = 动画重启); prism 无该规则故一直干净. 修法 = 两皮肤 views.css 抽屉作用域 animation:none; zz-verify 三皮肤(prism/atlas/console)× dt10/11 × 数据回路+选中全 dev=0, 红验(注回旧规则立刻 rt=4/rm=4)通过; 永久守阵 #9 落 dt-live-update(rAF+4ms 双路, POST 走真实端点保 waitCmd, GET 翻转数据), 双皮肤绿; test.full + e2e @fast 全量绿(数字见基线切片 26-10-14-1401, 不在此手抄); zz-* 探针已删; 坑档新增「动画重播同族」条目(含「瞬态缺陷必须逐帧采样」元教训), 三复查条目标 复发=1(修法未命中真机形态).
- 2026-10-18 10:1x: Topics 复合键回归单主键(issue 26-10-18-0858 拍板: 维持单主键口径): 原 "webui-detail-panel-redesign, webui-drawer-templates" 第一键写错——本档属 10-14 detail-table-rebuild 复查浪(计划 0811 + 报告 0136 + 档案 26-10-13 同键, 本档 Refs 已引 0136), 归 webui-detail-table-rebuild; 次要键无反声明目标, 从元数据消失, 关联由同键分组承载。
