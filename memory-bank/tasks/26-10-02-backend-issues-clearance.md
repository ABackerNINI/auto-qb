# 26-10-02-backend-issues-clearance — 用户指派批 7 条 issue 分阶段清偿(委派模式)

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02
**Summary:** 主会话只委派不实施: 7 条计划外 issue(覆盖提升 P1/P2 遗留发现)按模块强关联分 4 阶段, 逐个派子智能体实施并各自单独提交(2359a3d1 / 4a883385 / f89ceada / 49d933b5); 3 项待拍板修法先问用户, 2 项主会话按仓库惯例定夺; 7 条全部收口(5 Done + 1 Dropped 复验推翻 + 1 已消失关单); 子智能体 0 次异常失败, 3 次熔断条款未触发。

**Topics:** backend-issues-clearance
**Refs:** memory-bank/tasks/26-10-02-memory-bank-issue-clearance-roadmap.md

## 原始请求

用户(2026-10-02): 派子智能体分阶段依次实施 7 条 issue(26-10-02-0306-test-hr-budget-wait-flaky · hr-finish-wave-warn-dedupe-reset · hr-do-wave-hrfetcherror-dead-tail · tray-appid-readback-dead-branch · mainloop-stopiteration-swallowed · hr-prune-index-duplicate · qbmanager-web-arc-unreached); 强关联可合并、特大拆小防 O(n²) token 与出错进度全丢; 不并列执行防超并发; 待拍板的先询问; 主会话只委派总结不实施; 每阶段完成后由子智能体单独提交; 子智能体非正常失败 3 次后停止等人工。

## 思考过程与决策

- **分 4 阶段、严格串行**: ① hr/service.py 三项(同文件强关联: finish-wave 去重 + do-wave 死尾段 + prune 单点化) ② flaky 用例(同测试文件, 独立验收口径 = test.full 连续 10 跑) ③ core/qbmanager.py 两项(StopIteration + web 弧归档, 同文件) ④ tray/app.py(AUMID 读回)。每阶段一笔提交, 单阶段失败不牵连其它阶段。
- **归档位置**: 本批为用户指派批, 不入滚动路线图九波表, 故独立立档而非追加其波次表。
- **拍板三项问用户**(AskUserQuestion 一次三问): finish-wave 修法二选一 → 答案「恢复每站只报一次」; mainloop StopIteration 方向三选一 → 答案「接住 + 调用链根修」(方案③熔断不实施); do-wave 死尾段处置 → 答案「复验后删除」。
- **主会话定夺两项**(有仓库级事实支撑): tray 读回校验**删除** —— 该函数使用场景就是非打包进程, 而非打包进程 `GetApplicationUserModelId` 恒返回 15703(APPMODEL_ERROR_NO_PACKAGE 族), 判据在所有真实场景下无意义; web 弧按仓库 `# pragma: no cover` 既有惯例(6 处先例)标注归档 + 关单。flaky 修法按 issue 原文授权留给实施子智能体复验后自选(实际走了第三候选: 时钟起点对齐)。
- **停手协议生效一次**: do-wave「死尾段」复验被推翻 —— 挑战页 raise 能让 retry_after=0 的 HrFetchError 落入尾段(尾段实际可达且已有测试钉住), 子智能体按约停手未改码, issue 标 Dropped; 未向用户重开拍板(无可修对象, 若要改挑战页语义才需重新拍板)。
- **prune 单点化复验已消失**: 静态版 `_prune_index` 已被先行提交 54db09f2(26-10-01-2335 的工作, 早于本 issue 入池)合并为模块级单点, 零改动关单。

## 实现计划

4 阶段串行。每阶段固定流程: 子智能体 `my-commit-flow.sync` → 读 AGENTS.md + pitfalls 索引 → 认领复验(grep 锚点 + HTML 补复验行) → 实施(含红→绿守阵) → `test.full` 全绿 → issue HTML 状态推进(按 create-issue skill) → `ship.commit` 单独一笔。子智能体不写 activeContext / 不建基线切片(主会话统一收尾), 计划外缺陷不改不入池只转报。

## 子任务状态表

| 阶段 | issue | 结果 | 提交 |
|------|-------|------|------|
| 1 | hr-finish-wave-warn-dedupe-reset | Done: 删 `_finish_wave` 末尾 3 行无条件 discard; 新增 `_reset_warned_on_recovery(site)`(service.py:1288), 调用点 `_run_pages` 页级登录/挑战检查通过后(:647)即恢复点; 测试改按新行为断言并钉「恢复后再失效重新告警」 | 2359a3d1 |
| 1 | hr-do-wave-hrfetcherror-dead-tail | Dropped: 复验推翻「不可达」—— 挑战页 raise(be83d611 起)在页级 try/except 之外, HrFetchError 默认 retry_after=0 直落尾段; 574-581 在 term-missing 而 582-585 不在(被 test_challenge_page_truncates_wave 执行) | (无, 按约停手) |
| 1 | hr-prune-index-duplicate | Done(已消失): 54db09f2 已先行按便签建议单点化, 测试已单口径, 零改动关单 | (随 2359a3d1 关单) |
| 2 | test-hr-budget-wait-flaky | Done: `Clock(start=1005)`→`1000` 对齐 `last_fetch_ts`(第三候选; ①容差丢语义、②sleeper 注入对本用例结构性不可行——不调 mark() 推钟会击穿 caps 断言); 机制=初始条件错位非定时器精度, 且与 xdist 无关(入池归因已修正); 修后直跑 0/60 红 + test.full 连续 10/10 绿 | 4a883385 |
| 3 | mainloop-stopiteration-swallowed | Done: 主循环 `except Exception` 前新增 `except StopIteration`(:559)—— ERROR 带堆栈日志后原样重抛, 绝不续拍; 两层调用链盘点无裸 next()/生成器(生产触发面仅测试 mock); 守阵 test_run_stopiteration_from_tick_not_swallowed 修复前红(吞掉续拍)后绿(穿透 run()) | f89ceada |
| 3 | qbmanager-web-arc-unreached | Done: qbmanager.py:528/:538 加 `# pragma: no cover` + 一行中文原因注释(指向本 issue), 格式对齐仓库先例; 未上重型 mock; qbmanager.py 覆盖率达 100% | f89ceada |
| 4 | tray-appid-readback-dead-branch | Done: 整段删读回块(kernel32 绑定/读值/一致性判定), 保 `SetCurrentProcessExplicitAppUserModelID` 设置调用与 hr!=0 warning; 成功路径补「已设置」debug; 测试 4→3(删 mismatch 用例, success 改钉 no_readback) | 49d933b5 |

## 进度日志

- 2026-10-02 05:57 — 阶段 1 完成: 2359a3d1, test.full 2288 passed + 3 skipped / 99.02%(34.80s); 期间远端前移(300f8aa5), stash→sync→pop 合流(仅生成物 issues/_index.md 冲突, 重跑 kb.index 解决)。
- 2026-10-02 06:15 — 阶段 2 完成: 4a883385, 直跑 60 次 0 红 + test.full 连续 10/10 全绿; 机制定位推翻入池归因(xdist 与失败机制无关)。
- 2026-10-02 06:44 — 阶段 3 完成: f89ceada, test.full 2290 passed + 3 skipped / 99%(35.6s); qbmanager.py 覆盖率 100%。
- 2026-10-02 07:01 — 阶段 4 完成: 49d933b5, test.full 2289 passed + 3 skipped / 99%(35.06s)。
- 2026-10-02 07:07 — 收尾: 本档案 + activeContext 切片 + 基线切片(baselines/26-10-02-0707-*) + ghost-pkg 坑复发 +1; 计划外发现四项转报用户(见下)。

## 计划外发现(均未处置, 转报用户)

1. **`_set_windows_appid` 本身是死函数**: 自 9891c030 引入起生产代码零调用点(tray/__init__.py 未导出, 仅测试驱动) —— 生产进程从未设置显式 AUMID, issue 26-10-01-2203(任务栏 python 图标)的「已设 AUMID」前提可能不成立; 需人工决断(补调用点 / 删函数 / 另案)。
2. **首轮 tick 任意异常无退避快速重试**: wait_for=0 机理下首轮 tick 抛**任何**异常(不止 StopIteration)在 next_*_at 未推进时都会形成无退避快速重试循环 —— 有 ERROR 日志不静默, 是否要退避待决。
3. tray/app.py docstring「对应开始菜单 AutoQB.UI.lnk」疑似漂移(9891c030 已改注册表键机制并清理 lnk); core-domain.md:27「进程须先设显式 AppUserModelID」表述与代码事实(无调用点)不符 —— 均为先在漂移, 未改。
4. **kb 债务**: activeContext 切片数 87 > 70、cap 债务 1 —— 按 DoD 口径需另开会话清理。
