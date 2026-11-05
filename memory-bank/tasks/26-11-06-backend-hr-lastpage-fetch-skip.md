# 26-11-06-backend-hr-lastpage-fetch-skip — issue 26-09-30-0052 末页追翻省略复验与拍板

**Status:** In Progress
**Added:** 2026-11-06
**Updated:** 2026-11-06
**Summary:** HR 计数末页追翻省略(P3 缓做项)issue 复验仍复现(service.py 拆分后锚点重新定位)+ 收益风险对照 + 用户拍板 Dropped;零代码,纯知识库落盘
**Topics:** backend-hr-lastpage-fetch-skip
**Refs:** memory-bank/issues/26-09-30-0052-perf-hr-lastpage-fetch-skip.html

## 原始请求

1. 「认领复验26-09-30-0052-perf-hr-lastpage-fetch-skip.html」—— 用户指派认领,按 issue §7 复验口径重跑锚点、确认现象仍在、补复验行;
2. 「出个收益与风险对照」—— 为拍板提供依据(回复内交付,未建报告件);
3. 「什么情况下会出现「rows 已达 claim 但下一页标记未消失」?」—— 收益场景的机制追问;
4. 「情形3在正常情况下似乎不会出现,收益不足以支撑风险,改dropped」—— 拍板 Dropped;
5. 「提交」—— commit + push。

## 思考过程与决策

- 复验(2026-11-05 23:49,HEAD e470ccca):`service.py` 已拆分(service_wave/service_common/service_status),`full_depth` 两赋值点漂移至 `service_wave.py:316/:326`,`has_next` 仍在 `base.py:28`,§2.2 四消费点全部重新定位且语义未变;现象本体仍复现(循环终点仍只有停翻条件①②③与「下一页标记消失」,`counter_claims` 不参与停翻决策)。
- 收益风险对照的关键结构:**收益窗口 = 风险窗口** —— 「rows==claim 但标记未消失」只在站点计数与表格实况出现偏差时张开;计数精确且波内无增删时 rows 恰在真末页达成 claim(该页自身 has_next 已 False),无可省。能开窗三情形:①计数滞后 ②行重现型 churn(均为异常,恰是现行超翻锻造 `count_match=False` 冻结证据的时刻)③空末页伪影(唯一纯收益,正常形态不出现)。
- 追问③后用户拍板:**Dropped**(收益不足以支撑风险;早停把计数偏小变成自我确认,削弱计数对账证据链,直击报告 §4.3「不误放行」核心安全性质;与报告 §5.1 否决「观察期 2 波→1 波」同判据)。重启前置保留:D4 口径实证 + 修法改走页码标记佐证(`cur_mark == max_mark`)而非计数对平。

## 实现计划

总体思路(无分步):重跑锚点复验 → 复验结论落盘 issue(状态暂保持 Open)→ 回复内对照分析 → 用户拍板后按 create-issue 五词表流程落盘(两处状态 + 日志末条 + 索引重建)→ 立档收尾提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 开工同步(048850fd→e470ccca 快进 11 笔)+ 锚点重跑复验 | Done(2026-11-06) |
| 2 | issue §7 复验小节 + 状态日志落盘(状态保持 Open) | Done(2026-11-06) |
| 3 | 收益与风险对照(回复内交付)+ 情形③机制追问 | Done(2026-11-06) |
| 4 | 拍板 Dropped 六处落盘(meta/徽标/lede/摘要/日志末条/§06 收口)+ kb.index | Done(2026-11-06) |
| 5 | 立档 + 收尾提交(非涉码轮免 test.full,按 kb.wrap 条件) | Done(2026-11-06) |

## 进度日志

### R0 · 立档 (2026-11-06)

认领复验(仍复现,锚点随 service.py 拆分重新定位)→ 回复内收益风险对照 → 用户拍板 Dropped 落盘(六处 + 索引重建,kb.check 全绿)→ 本档立档。零代码改动,非涉码轮按 kb.wrap 条件免 test.full,基线事实源仍为 26-11-05-0952 切片(见 kb.baseline)。

- 2026-11-06 01:04 认领复验 26-09-30-0052(仍复现,锚点随 service.py 拆分重定位)+ 收益风险对照 + 拍板 Dropped 落盘
