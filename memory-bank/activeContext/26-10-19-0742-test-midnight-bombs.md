# test-midnight-bombs

> 摘要: 认领并修复 issue 26-10-19-0013 两轮 —— ①测试侧: expr 冻钟 + traffic 正午锚点(假墙钟 23:59:50 对照取证, 改前 3 红/改后 13 绿); ②生产侧(用户拍板「直接改」): `utils.time_in_range` 改分钟粒度, 三消费方收口, 补分钟粒度单测 + 等价性 edge-minute 守阵位, 红验通过; 数字见 kb.baseline 最新切片
> 最后活动: 2026-10-19 07:42

**R0(2026-10-19 07:42):** 认领并修复 issue 26-10-19-0013: expr 侧冻钟 + traffic 侧正午锚点, 生产代码零改动; 假墙钟 23:59:50 对照取证(改前 3 红 / 改后 13 绿), 定向 44 例与全量均绿, 数字见 kb.baseline 最新切片

**R1(2026-10-19 08:11):** 用户拍板「直接改」→ 生产侧 `utils.time_in_range` 改分钟粒度(比较前截秒/微秒), 三消费方(`date_time` 条件 / `quiet_hours` / `allow_window`)同步收口, `00:00-23:59` 从此真覆盖全天; 补两道守阵(`test_time_in_range_minute_granularity` + 等价性 `edge-minute` 参数位 23:59:30), 红验: 去掉截断则两处同时红; `docs/configuration.md` 的 `date_time` 行回写语义。数字见 `kb.baseline` 最新切片(同专题 `-granularity` 那条)。

**已决(原「待决」项已拍板):** 旧 `date_time` 条件(秒精度)与表达式 `sys.time_of_day`(分钟精度)的 59 秒/天 分叉 —— 未入池、未开新 issue, 按用户「直接改」在原单内收口。
