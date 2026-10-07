# 两计划状态收口: qb-traffic-v3 + cap 债务制翻 Done (Done)

> 摘要: 用户确认两计划已完成, 要求简单验证后更新状态。验证: ①qb-traffic-storage-v3 任务档案本就 Done(⓪~⑨ 全闭合), v3 关键代码(TrafficV3Store/WINDOW_SPECS/LiveTail)在位; ②cap-debt 唯一遗留子任务 7(AGENTS.md 削薄)已由后续清理轮(fa918a67/376dda34/cba7c4f6/295bb226 等)落地, 实测 **6,608/8,000**(余量 1,392); ③`doc.caps` 无阻塞项、cap 债务 0 项; ④test.quick **2705 passed + 4 skipped** 全绿(状态改动后复跑仍绿)。状态: 两计划 `doc-status` Open→Done(doc-updated 26-10-07-0755); cap-debt 档案 Status→Done + 子任务 7 置 ✅ + Summary 旧口径清除; kb.index 重建(20 生成物)归入 Done 分区。
> 最后活动: 2026-10-07 07:55

**Refs:** memory-bank/plans/26-10-04-1957-plan-qb-traffic-storage-v3.html · memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html · memory-bank/tasks/26-09-30-memory-bank-cap-debt.md

## 现状

- 纯状态收口轮, 无代码改动 —— 未跑 test.full / 未建基线切片(上一基线 26-10-07-0434 仍有效), 收尾验证用 test.quick。
- 附带入库: tasks/26-10-06-memory-bank-dangling-hash-refs.md 上一轮遗留的进度日志补记(ship.commit 同步撞闸门迁移窗口一事)随本提交走。
- 债务转告(非本轮): activeContext 切片数 86 > 70 —— **不拦提交**, 需另开会话蒸馏 14 天未动切片(`commands run doc.caps` 现算)。
