# 3205 passed + 4 skipped / e2e 240 passed + 10 skipped —— 修复 e2e delta-sync 全量轮偶发红 flake(issue 26-10-11-1825)

> 摘要: 用户「认领并修复」issue 26-10-11-1825(e2e delta-sync「置空 lastRid 走全量」全量轮偶发红、隔离恒绿)。改动 1 个源文件: e2e/delta-sync.spec.mjs 第 2 条用例收尾断言由「读探针最后一轮的 full」改**存在性判据**(快照踢出前轮数, 等「踢出之后落过一次 full=true」), 零生产代码。根因 = 末值判据对轮次到达顺序敏感: 在飞旧 rid 请求被共享长驻桩命令泵/回弹抬 ver 后回增量轮(full=false), 晚于全量轮落袋即假红。验证 = 确定性竞态探针(newRounds=2 lastFull=false someFull=true, 探针跑完已删) + 隔离两轮 8/8 + 全量 e2e + test.full 全绿。
> 基线时间: 2026-10-15 03:21

## 验收数字

- test.full: 3205 passed + 4 skipped / TOTAL 16824 158 5724 140 99%(98.65%, 过 98% 闸门); 耗时 131.08s(单次采样, 口径见 baseline.md)。
- e2e 全量(commands run dev.e2e, 本机 8137 起桩串行 250 条): 240 passed + 10 skipped / 0 failed / 8.2m —— 修复前取证轮(2026-10-11)为 1 failed + 10 skipped + 157 passed, 唯一红即本 issue 的 delta-sync.spec.mjs:170。
- e2e 隔离(delta-sync.spec.mjs 单文件, 修复后 ×2): 均 8 passed / ~20s 与 ~18s。
- 包内脚本测试(commands run test.pkg): 本轮未触 .commands/ 与 .agents/skills/commands/, 闸门 match 不命中, 未跑。
- Linux(WSL)侧未重测 —— 改动为 e2e(JS)用例断言, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- 源(1 文件): e2e/delta-sync.spec.mjs —— 第 2 条用例收尾断言改存在性判据 + 注释记录竞态机理与 issue 编号; S7 收尾判据(单调否定式)非同型未动。
- 红验: 确定性竞态探针(一次性 spec) —— 等全量轮落袋后注入一次迟到增量轮: 旧末值读法得 false(假红复现), 新存在性判据得 true; 输出 newRounds=2 lastFull=false someFull=true。探针跑完即删, 不进提交。
- 文档: 本切片 · issue 报告 26-10-11-1825(Done, 复验/根因/修法/验证四段补齐) · 坑档 pitfalls/testing/poll-last-round-race.md(新立) · activeContext 切片 26-10-15-0317 · kb.index 重建。
