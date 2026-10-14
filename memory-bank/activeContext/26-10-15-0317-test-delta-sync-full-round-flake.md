# 修复 e2e delta-sync「置空 lastRid 走全量」全量轮偶发红 flake(issue 26-10-11-1825)

> 摘要: 用户指令「认领并修复: memory-bank/issues/26-10-11-1825-test-delta-sync-full-round-flake.html」。根因定案 = 断言读探针「最后一轮」对轮次到达顺序敏感: 轮询链在飞的旧 rid 请求被共享长驻桩的命令泵/回弹抬 ver 后回增量轮(full=false), 晚于踢出的全量轮落袋即假红(隔离恒绿、全量顺序偶发红)。修法 = 存在性判据(快照踢出前轮数, 等「踢出之后落过一次 full=true」), 时序无关。确定性竞态探针实证(newRounds=2 lastFull=false someFull=true)后删除。改动 1 个源文件(e2e/delta-sync.spec.mjs 断言 + 注释), 零生产代码。修复后隔离两轮 8/8 绿 + 全量 e2e 240 passed/10 skipped/0 failed。坑档 testing/poll-last-round-race.md 新立。测试数字见 `commands run kb.baseline`(本专题基线切片 26-10-15-0321)。

> 最后活动: 2026-10-15 03:17

## 状态

- issue 26-10-11-1825-test-delta-sync-full-round-flake.html: Done(修法/验证见报告「修复后补充」段)
- 代码: e2e/delta-sync.spec.mjs 收尾断言改存在性判据(第 2 条用例); S7 收尾判据(单调否定式)非同型, 未动

## 关键决策

- 方案 2 字面形式「等 rounds 长度自增再读最后一轮」仍对顺序敏感(第一个新轮可能恰是迟到增量轮) ⇒ 采纳其强化版存在性判据; 抬超时窗口(方案 3)不采纳(掩盖真问题)
- 不立 task 档案: 单文件小修, 低于立档阈值(见 memory-bank skill 阈值表)
- 复验不重跑全量轮(红率低、成本 8min): 以确定性探针替代, 机理四环均在代码层闭环(polling.js refresh/scheduleNext · runtime.py _reduce_delta · ui_harness 命令泵/回弹 · 断言读末值)
