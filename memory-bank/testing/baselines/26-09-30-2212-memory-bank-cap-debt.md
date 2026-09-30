# 基线 · 1871 passed + 3 skipped / 91% —— cap 守卫改债务制计划入档 (纯文档轮, 落在 P3 合并后)

> 摘要: plan plans/26-09-30-2112-plan-memory-bank-cap-debt (cap 守卫改债务制: **提交时 WARN** +
> 警告文案自带「提醒用户另开新会话清理」+ 用户自行开清理会话; AGENTS.md = 硬规定, 不入债务体系)
> 定稿入档, 随附 tasks/26-09-30-memory-bank-cap-debt.md 档案与 activeContext/26-09-30-2112 切片;
> 前序波次切片 26-09-30-0018 (token-budget, 已完结) 按切片计数守卫的处置口径蒸馏删除 (内容全在其
> 档案内); 切片 26-09-27-1812 待办①「AGENTS.md 削薄」移交本专题。**纯文档轮 +0 用例** —— 无代码 /
> 脚本 / 测试 / 配置改动。数字在**合并远端 P3 (ed514e30) 之后**实测(先合并远端, 再收尾)。
> 基线时间: 2026-09-30 22:12 (develop @ ed514e30 + 本轮未提交改动) 制品: plans/26-09-30-2112 状态 Open。

TOTAL **1871 passed + 3 skipped / 91%**(13214 语句 / 1053 未覆盖 / 4390 分支 / 429 partial,
test.full 22.27s, rc=0) —— 与上基线 26-09-30-2142(内核化 P3, 1871 passed + 3 skipped / 91%)用例数
持平、本轮增删为零; 语句 / 分支绝对值随 P3 合并而变动(本轮零代码改动, 不引入新语句)。

## 本轮改动面

- 新建 3 文件: memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html(计划, doc-status Open,
  doc-updated 26-09-30-2159)、memory-bank/tasks/26-09-30-memory-bank-cap-debt.md(档案, Status Open)、
  memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md(切片); `kb.index` 重建索引。
- 删除 1 文件: memory-bank/activeContext/26-09-30-0018-memory-bank-token-budget.md
  (已完结波次的切片, 内容全在其档案 tasks/26-09-30-memory-bank-token-budget.md 内)。
- 更新 1 文件: memory-bank/activeContext/26-09-27-1812-commit-msg-consume-delete.md 待办① ——
  「AGENTS.md 削薄」移交专题 memory-bank-cap-debt(「下次收尾时顺手做」被证伪: 收尾是最贵时刻)。
- 坑档: pitfalls/kb/cap-counting.md 新增「切片计数触顶时, 可蒸馏的是已完结波次切片」条目 +
  行尾坑(量 cap 用 char_count / 新建文件须 CRLF)**复发 5**(本轮新建四件 Write 全落 LF, 收口断言一次捕获)。
- 无代码 / 脚本 / 测试 / 配置改动, 无新配置键, 无线程与 state_file 变更。

## 首跑红与判定依据 (本计划主题的现场实例)

- test.full 首跑唯一红: test_kb_active_context_slices_are_valid —— 切片数 **71 > SLICE_COUNT_LIMIT 70**
  (本会话新增 1 片恰好触顶; 当日多 clone 节奏实测 15 片, 而上限按 ~5 片/日校准)。这正是本计划所治的
  「增长型 cap 在收尾最贵时刻索要返工」的现场实例, 也是计划 D2(计数阈值归债务通道)的依据。
- 处置: 按守卫消息自身的口径(「蒸馏进任务档案后删除」)蒸馏已完结切片 26-09-30-0018 —— 未抬守卫
  数字、未动他人活跃切片(4 片 kernel-module-refactor 属在办专题, 一行未碰)、未违规归档(删除对象
  不是 <14 天未动的活跃切片, 而是内容已被档案全量覆盖的完结波次)。
- 拍板两轮(用户): D1/D3 —— AGENTS.md = 硬规定(不能超 / 不套 50% 收缩 / 不入债务体系), 取消 1.25×
  止损线; 触发点二次修正 —— 债务可见性从「会话开始」改「提交时」(agent 开不了新会话), agent 转告
  用户、用户自行开清理会话; 会话开始协议与 AGENTS.md 均不动, AGENTS.md 削薄降为独立清理项。
- 合并与复测: 提交前同步合入远端 P3 ed514e30(内核化三模块 + 11 用例 + 其基线切片 2142), 本轮按其后的
  新基线复测并记本切片; 复跑全绿: test.full 1871 passed + 3 skipped; `kb.index` / `kb.check` /
  `doc.caps` / `doc.links` / `doc.drift` 全绿; AGENTS.md 实测 7,975/8,000(余量 25 —— 计划 §1.1 的立项证据)。