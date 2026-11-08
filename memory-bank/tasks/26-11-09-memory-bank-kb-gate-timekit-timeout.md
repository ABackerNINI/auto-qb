# 26-11-09-memory-bank-kb-gate-timekit-timeout — 提交闸门 kb 链 timekit 超时 60s 根因分析

**Status:** In Progress
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** 认领 issue 26-11-09-0441，复验并定位 ship.commit 的 kb 闸门 timekit --check 60s 超时：固定超时 × 全库扫描 × 并发放大 × 满载机
**Topics:** memory-bank-kb-gate-timekit-timeout
**Refs:** memory-bank/issues/26-11-09-0441-bug-kb-gate-timekit-timeout-flaky.html, memory-bank/plans/26-11-09-0559-plan-memory-bank-kb-gate-timekit-timeout.html

## 本篇只回答

只回答「ship.commit 的 kb 闸门为何在满载机上把 timekit --check 判成 60s 超时」；修法唯一权威在 plan `26-11-09-0559-plan-memory-bank-kb-gate-timekit-timeout.html`（2026-11-09 grilling 四问按推荐拍板，D1–D4）。本篇只引用不重写方案，滚动记录执行与验证进度。

## 原始请求

1. 先同步，然后分析：当前的提交闸门检查顺序是什么，多线程模型是什么样，用图表述一下（只读分析轮）。
2. 认领 issue，深入分析原因（认领 26-11-09-0441 + 根因取证；未授权修复、未授权提交）。
3. 评估「timekit --check 是否适合改为仅扫描改动文件、其它几条是否也适合」，把其它方案一并纳入 grilling，出修改方案（只读取证 + 拷问轮；用户按推荐拍板，方案已定稿）。

## 思考过程与决策

- 认领按 create-issue skill：先复验再 `kb.status` 翻 In Progress；建 tasks 档案并经 `--refs` 自动双向补链（`gen_doc_map --check` 校验）。
- 结论分三层写：可直接验证的事实 / 高置信根因 / 仍待证的推断；不把猜测写死（防过期原则第 1 条）。
- 冲突裁决以代码为准：`commit.py` 的 `__main__` 只让快照副本层跑 `main`，原包父层阻塞在 `subprocess.call` ⇒ 档案里「双层 commit.py 各起一套 gate」与代码不符，不沿用；「两个 timekit 并存」改从「超时杀树残留 + 连续重跑」解释。
- 复验口径：60s 判死本轮未复现（机器负载低于 04:41），但并发放大机制已 A/B/A 复现 ⇒ 写「部分复现」，既不写「已消失」也不写「仍复现」。
- 本轮零代码改动：不跑 `test.full`、不建基线切片；只跑 `kb.check` 机检文档面。
- 方案轮按 grilling 协议：事实由 agent 取证、决策由用户拍板；Q1–Q4 全部「按推荐」后设计树收敛，只落 plan 定稿，不实施 P0（D4）；方案与 issue / 本档案经 `--refs` 双向补链。

## 实现计划

分析任务不是修复；下列 1-5 已完成，6 需满载机现场，7 已拍板定稿，8 待实施。

1. 复核闸门顺序与并发模型：12 条 gates 配置序 → 串行展开 → `ThreadPoolExecutor(4)` 并发 → 失败按提交序收集、取 `failures[0]`。
2. 复验现场：Win32_Process 采样、单跑/并发计时、快照环境变量对照。
3. 排除确定性候选：扫描路径变化、锁/stdin、timekit 自身慢、WindowsApps python 存根。
4. 量化并发放大：A/B/A 对照（单跑 → 4 路并发 → 单跑）。
5. 把结论与证据落进 issue §02/§04/§05/§06/§07。
6. 待办（需满载机现场）：超时杀树后残留冻结进程的进程树快照、两轮闸门是否同时触发的日志取证。
7. 已定（2026-11-09）：修法选型落 `memory-bank/plans/26-11-09-0559-plan-memory-bank-kb-gate-timekit-timeout.html` —— 按改动收窄 `timekit` / `check_html` + 复跑清单扩面 + 展开长度守卫；分档 timeout 与独占池仅 P2 备选；本轮零代码改动。
8. 待办（实施另起指令）：按 plan §04 的 S1–S5 执行与验收，P0 与 P1 同批，不拆开发布。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 闸门顺序与并发模型复核 | Done(2026-11-09) |
| 2 | 现场进程 + 单跑/并发耗时复验 | Done(2026-11-09) |
| 3 | 确定性候选排除 | Done(2026-11-09) |
| 4 | A/B/A 并发放大对照 | Done(2026-11-09) |
| 5 | 根因结论与修法方向落 issue | Done(2026-11-09) |
| 6 | 满载机残留冻结进程取证 | Open |
| 7 | 修法拍板（plan 定稿 D1–D4） | Done(2026-11-09) |
| 8 | 按 plan §04 S1–S5 实施与验收 | Open |

## 进度日志

### R0 · 立档 (2026-11-09)

认领 issue 26-11-09-0441 并翻 In Progress；完成复验与根因分析（证据与结论落在 issue §02/§05，修法方向在 §06，复验口径在 §07）。本轮零代码改动，随本专题入库。

- 2026-11-09 05:35 认领 issue 26-11-09-0441 并翻 In Progress; A/B/A 复验确认 4 路并发把全库扫描放大 3.3 倍, 根因收敛为固定 60s 超时 × 并发放大 × 满载机; 结论落 issue 05 段, 修法方向 06 段; 零代码改动, 随本专题入库

- 2026-11-09 06:02 grilling 四问按推荐拍板, 新建 plan 26-11-09-0559 定稿(D1-D4): 按改动收窄 timekit/check_html + 复跑清单扩面 + 展开长度守卫, P2 仅备选; 任务档案判断面与 issue 06 段同步指向; 零代码改动, 随本专题入库
- review: 全能档 1 个只读 reviewer, 修复循环 3 轮 —— 首轮 5 条发现(major 1 / minor 3 / nit 1)引文校验 5/5 通过、裁定全相关、blocker 0、修 5、入池 0; R2/R3 零发现, 6 处修订逐项核验未回退; 评审期间远端推进 1 笔带 Review: 提交, 重新 sync 后按新锚点重取末轮基哈希, 发现不作废。
