# 26-11-10-test-github-ci-e2e-red-fix — 修复 GitHub CI 四组 e2e 既有红 (issue 26-11-07-0326)

**Status:** In Progress
**Added:** 2026-11-10
**Updated:** 2026-11-10
**Summary:** 修复 GitHub CI 四组 e2e 既有红 (issue 26-11-07-0326)
**Topics:** test-github-ci-e2e-red-fix
**Refs:** memory-bank/issues/26-11-07-0326-test-ci-smoke-existing-red-backlog.html

## 本篇只回答

本轮如何把 GitHub CI 最近三次失败里的 4 组 e2e 红灯按根因真修(不掩盖), 以及顺带发现的两类「产品口径已变、e2e 断言未同步」回归。

## 原始请求

1. 用户原话: 「修复github CI报错, 使用gh查询最近3个失败历史」。
2. 给出诊断后, 用户在四个范围选项中拍板「认领并真修全部 4 组」——构成对既有红 issue 的显式认领指派, 覆盖台账原「只展示不修、等排期」的拍板。
3. 收尾时用户拍板「完整收尾并提交」, 授权新建文件与 commit/push。

## 思考过程与决策

- `gh run list --status failure --limit 3` 三次失败全部是 `Playwright (WEB UI 冒烟)`, 同期 `CI`(pytest) 全绿; 15:50 那次 daily 绿是**假绿** —— 提交只改 tests-real, 未命中 gate 白名单, 三个分片全 `skipped`, aggregate 按 `success|skipped` 判绿。失败从未被修, 只是没跑。
- 防过期复验: 本地隔离跑 `gtm-alert` 2 passed / `kbd-scroll-band` 2 passed / `perf W5` 2 passed(3 拍贴边); 按 CI 口径整片 `shard 2/3` = 102 passed 全绿 → **排除全量顺序污染**, 判定 Linux runner 与本地 Windows 的环境差异(字体行高 / `$nextTick` 与窗口化重渲时序 / CPU 抢占)。
- 台账 `26-11-07-0326` 原拍板「既有红只展示、不解决、不掩盖」; 本轮用户显式指派认领, 属 scope-guard 例外 3「用户当场扩范围」。全程**未采用** `skip` / `continue-on-error` / `--grep` 排除 / 放宽 retry / 按 CI 分档放宽。
- 修法取向一律「消掉错误假设」而非抬阈值: gtm 是等待窗口不足(默认 5s), perf 是把不定长交互窗当固定 4.4s, kbd 是落定执行时机早于 DOM 重渲, drawer/menus/optimistic 是产品口径变更后测试面没同步。
- 顺带发现两个**当前 HEAD 的确定性回归**: `76deeb7d` 复制 magnet 三处入口下线漏改 e2e 断言; 修完 magnet 后又被暴露的 `26-11-08-1621` wide 条件式与 `BASE_PATCH` 桩数据不同步。二者本地可稳定复现, 属本轮 CI 报错面。
- 评审两轮(code-review skill): 轮 1 提 2 条 major —— ① perf 上界硬编码 2000ms 与 `vm.basePollMs()` 在 600 档真实 1500ms 不符(会把假红重新引入)、② `!pre` 分支单次 rAF 仍可能在慢 runner 上扑空(等于旧码的静默放弃); 两条当场修完并复验。轮 2 零 actionable, 首轮发现确认未回退。
- 取舍: 不把 kbd 判成「runner flaky 所以放宽几何余量」—— spec 头注释记录的本就是真实用户报障(End 到末行只显示一半), 放宽余量会掩盖产品缺陷。

## 实现计划

1. 开工同步 + `gh` 取三次失败日志, 定位失败 job 与断言行号。
2. 复验(隔离 + 整片 shard), 区分顺序污染 / 环境差异 / 确定性回归。
3. 认领台账 `26-11-07-0326` 置 In Progress。
4. 分四组修根因 + 同步 magnet/wide 过期断言与桩数据。
5. 本地验证: 目标 spec 全绿 + `test.full` + 静态守阵 + `node --check`。
6. 收尾: 分批评审、坑档复发/新坑、任务档案、基线切片、issue 翻 Done、索引重建、提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | gh 查询三次失败历史 + 日志取证 | Done (2026-11-10) |
| 2 | 防过期复验(隔离 4 组 + 整片 shard 2/3 = 102 passed) | Done (2026-11-10) |
| 3 | 认领台账置 In Progress + 双向认领链 | Done (2026-11-10) |
| 4 | 四组根因修复 + magnet/wide 断言同步(7 文件) | Done (2026-11-10) |
| 5 | 本地验证: 全量数字见 kb.baseline, 各 e2e spec 全绿 | Done (2026-11-10) |
| 6 | 分批评审两轮(轮 1 修 2 major / 轮 2 零 actionable) | Done (2026-11-10) |
| 7 | 坑档 3 条复发 + 档案/基线/索引回写 + issue 翻 Done | Done (2026-11-10) |
| 8 | 提交并推送, 由下一轮 GitHub CI 验证 kbd 的 Linux 侧效果 | Open |

## 进度日志

### R0 · 立档 (2026-11-10)

- 三次失败历史取证完毕, 失败集合固定为 gtm-alert / kbd-scroll-band / perf W5 / drawer-general-variants 四组(另加 magnet 与 wide 两类过期断言)。
- 7 个文件改动已本地验证: 全量数字见 kb.baseline / 99% 覆盖; 目标 e2e 全绿; 两分片并行回归各有 1 条无关偶发红, 串行单跑均绿。
- 遗留事实: `kbd-scroll-band` 在 Windows 本地不复现, 产品侧「下一帧按真实 DOM 补正落点」的修复只能由 Linux CI 下一轮确认 —— 提交后须回看 `smoke (@fast) shard 2/3`。

- 2026-11-10 01:23 认领 26-11-07-0326 并真修 GitHub CI 四组 e2e 既有红 + magnet/wide 过期断言; 全量数字见 kb.baseline; 评审两轮(轮1 修 2 major, 轮2 零 actionable); 坑档 3 条复发; 随本专题入库, 下一轮 Linux CI shard 2/3 需回看
