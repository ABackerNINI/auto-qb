# 26-11-02-webui-large-filelist-perf — WEBUI 单种子千级文件列表性能统一优化 (W1-W5 + W6a 落地, W6b Dropped, 真机轨完成)

**Status:** Done
**Added:** 2026-11-02
**Updated:** 2026-11-03
**Summary:** WEBUI 千级文件列表卡顿统一优化: 调研报告取证根因 R1-R6 → 计划 26-11-02-0351 拆 W1-W6 → 串行实施 W1(记忆化/廉价sig/content-visibility)+W2(kind 描述符参数化)+W3(抽屉挂窗)+W4(千级验收矩阵 8/8)+W5(主表 3000 种子复测全绿), 千级常驻 DOM 1001→45-48 行、交互 longtask 归零; 首访量齐 issue 26-11-02-0902 已修并二轮调优。用户拍板后 W6 落地: W6a 抽屉专用乐观优先级补丁(失败/超时双出口回滚 + 重叠点击按 hash 序号收口, 最终态与整表重拉一致)已实施并由新单测 2 条 + 新 e2e 3 条 × 双皮肤验收, 千文件桩可见延迟 15-17ms vs 旧路径 171-174ms; W6b payload 裁剪按实测(127911B/可裁≈27%仅省≈1.3ms)拍板 Dropped(不等于已完成, 无代码/测试产出)。真机轨环境1(D盘 36595/36596)完成 RM08-09: 真 qB 1000 文件, 首帧 436-486ms / 常驻 DOM 47 行 / rowsFn 1002 行 max 7.6ms mean 5.28ms / longtask 0 / 乐观 9-14ms vs 旧路径 64-80ms / payload 156478B / 冷 30-44ms 热 16-18ms; 真实种子 8 枚全程非活跃。全量与基线数字见 kb.baseline。
**Topics:** webui-large-filelist-perf
**Refs:** memory-bank/reports/26-11-02-0339-report-webui-large-filelist-perf.html, memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html, memory-bank/testing/baselines/26-11-02-0707-webui-large-filelist-perf.md, memory-bank/issues/26-11-02-0902-perf-webui-first-visit-rowh-measure.html, memory-bank/pitfalls/web-ui/est-cold-start-vs-absolute-threshold.md, memory-bank/testing/baselines/26-11-02-1129-webui-large-filelist-perf.md, memory-bank/testing/baselines/26-11-02-1248-webui-large-filelist-perf.md, memory-bank/issues/26-11-02-0902-perf-webui-drawer-tab-switch-lag.html, memory-bank/testing/baselines/26-11-02-2246-webui-large-filelist-perf.md, memory-bank/testing/baselines/26-11-02-2353-webui-large-filelist-perf.md

## 原始请求

1. WEBUI 单种子千级文件列表操作卡顿, 需要优化性能。
2. 先调研成熟的解决方案, 写一个报告, 然后根据报告综合出一个计划。
3. 将列表性能问题统一解决, 也包括主表。
4. 执行方式: 主会话只委派与总结, 子智能体串行分阶段实施(大任务拆小防 token 爆炸与进度丢失), 完成后汇总交用户确认。

## 思考过程与决策

- 先报告后计划再实施(用户指定顺序); 报告取证根因 R1-R6(抽屉无窗口化/reactive tick 全量重派生/整列表交互粒度/JSON.stringify 全量比对/优先级提交整表重拉/后端全量无裁剪), 主表被判定已优化到位。
- 方案取舍: 自研窗口化推广进抽屉引擎(主修)+行对象记忆化(止血)+content-visibility(正交); 明确不做: 换框架/上构建步骤/引入第三方 grid(vue-virtual-scroller B-/TanStack B/AG Grid C)。
- 计划 `26-11-02-0351` 拆 W1-W6 串行工作包, 待拍板 D1(payload 裁剪先实测再定)/D2(主表残留池留池)/D3(W6a 乐观优先级待实测确认 R5 占比后做); 实施期按推荐默认推进 W1-W5, D1/D3 留待拍板。
- W1 三项偏差(记录于计划不改报告): sig 用全量数值滚动指纹而非抽样(防外壳停旧值); longtask 判据降为预算断言; 记忆化命中判据按渲染输入快照实现(观测等价)。
- W3 关键决策: 容器族滚动态与文档对分家(_winCtnState)——主表与抽屉同屏, 共用会让主表窗口跟抽屉滚动漂移。
- W4 A/B 口径定夺: longtask 断言下界收紧为 0(收窗后残留源消失, 实测双皮 4 格全 0); 真机轨 fail-closed 未跑(token 未注入), 零数字编造。

## 实现计划

计划单点: `memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html` (doc-status In Progress)。调研证据单点: `memory-bank/reports/26-11-02-0339-report-webui-large-filelist-perf.html`。执行方式 = 串行子智能体逐包推进(每包后 test.quick, 终态 test.full+基线), 主会话只委派与总结。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 调研报告(现状取证+成熟方案对比+推荐路线) | Done(2026-11-02) |
| S2 | 综合计划拆 W1-W6 工作包 | Done(2026-11-02) |
| S3 | W1 P1止血: 变体10/11 行记忆化+廉价sig+content-visibility+O(D×F)消除 | Done(2026-11-02) |
| S4 | W2 P2前置: 引擎窗口化 kind 描述符参数化, 主表零回归(e2e 36/36) | Done(2026-11-02) |
| S5 | W3 P2抽屉接线: drawerContent kind+桥切片+跨窗回焦, 千级 DOM 1001→47 | Done(2026-11-02) |
| S6 | W4 千级验收: drawer-content-perf spec 8/8 全矩阵+A/B 口径收紧 | Done(2026-11-02) |
| S7 | W5 主表千级复测: 五 spec 44/44+同屏交叉 2 条, 主表零回归 | Done(2026-11-02) |
| S8 | 终态 test.full+基线切片 26-11-02-0707(4824 过/99.00%) | Done(2026-11-02) |
| S9 | W6a 乐观优先级补丁(用户拍板实施) | Done(2026-11-02) — `drawer.js` 新增 `_drawerFilePriority`/`_drawerFileRollback`: prev 快照→当帧写 priority→POST→waitCmd(10s); 失败/超时回 prev 后静默重拉 files(最终态==整表重拉), 重叠点击按 hash 序号只让最新一次收口; 单测 2 条(静态顺序/双出口 + node 五态) + e2e 3 条×双皮肤; 桩可见延迟 15-17ms vs 旧 171-174ms, 失败回滚 350-352ms, 超时回滚 10027-10036ms |
| S10 | W6b payload 四步量法实测后裁剪(依赖 D1 拍板) | Dropped(2026-11-02, 用户拍板) — 实测 127911B/可裁≈27%仅省≈1.3ms; **Dropped 不等于已完成**: 未产出代码/测试, 不得记 Done |
| S11 | 真机轨 rm08 千文件 content 条目(用户提供测试环境) | Done(2026-11-02) — 环境1(D盘 36595/36596; C盘不存在), 三方核对通过; 新增 RM08-09(真 qB 1000 文件假种子): 首帧 436-486ms/常驻 DOM 47 行(折叠1/展开47)/rowsFn 1002 行 max 7.6ms mean 5.28ms/longtask 0/乐观 9-14ms vs 旧 64-80ms/payload 156478B/冷 30-44ms 热 16-18ms/detail 12-28ms/命令回执 423-440ms; 真实种子全程非活跃 |

## 进度日志

### R0 · 立档 (2026-11-02)

- 全流程一轮完成: 报告→计划→W1-W5 串行实施→终态全量。千级实测: 常驻 DOM 行数 抽屉 1001→45-48(主表 3000 种子 24-34), rowsFn 千行热态 dt10 1.9-2.2ms/dt11 6.4-7.4ms, 勾选单行/数据回路/折叠三交互 longtask 全 0, 同屏主表窗口逐字段恒等(源族分家无串扰)。
- 全量与覆盖率数字见基线切片 26-11-02-0707(当时唯一红=认领链机检, 随本专题入库自愈)。
- 遗留: W6(D1/D3 待拍板)、真机轨(待 token)、计划外缺陷 5 条只记未改(dt12:323 残留 stringify sig、columns.js _rowWindow 死参、_ensureWinCtnBind unmount 不摘监听、_ensureWinTop 不含表头高度因子、perf.spec P1-3 预算余量薄 flaky 建议入池)。
- 工作区未提交(用户未授权)。

- 2026-11-02 07:08 报告 26-11-02-0339 + 计划 26-11-02-0351 + W1-W5 串行实施(千级 DOM 1001→45-48, longtask 归零, 主表 3000 种子复测全绿) + 基线 26-11-02-0707(4824 过/99.00%); 遗留: W6/D1/D3 待拍板、真机轨待 token; 工作区未提交(用户未授权)

- 2026-11-02 08:29 用户验收轮(3000 种子桩): 切标签页/关抽屉后卡死数秒且能滚不能点 —— 根因=columns.js _measureRowH 行高签名混入 viewMode(切页全表作废退全量量齐)+_winCtnSync 抽屉离场过渡期宽度假 bump(作废主表行高); 两守卫修复后 8.4s/5.6s longtask→0(主线程饿死假象, 非遮罩); 新守阵 e2e/window-invalidation 6 条+静态 1 条, 三皮肤千级 e2e 28/28

- 2026-11-02 11:25 认领并修复 issue 26-11-02-0902: 千级首访估算开窗+渐进量齐(ROW_WIN_EST_MIN 1000 / _rowHAvgOf 全局均值), 3000 行首访 longtask 8432ms→97ms、gBR 3310→55 次; perf.spec 千级档判据分档(粗界/不塌陷), 3000 档 10 passed; 新增坑档 est-cold-start-vs-absolute-threshold; 工作区未入库(用户未授权)

- 2026-11-02 12:51 阈值二轮调优 1000→200(拐点实测 250ms 线落 150~200 之间, 与 ROW_WIN_MIN 合并); 空档1 首访路径指纹用例+空档2 单测边界断言补齐并双负向验证; 滚到底估算档改按比例禁塌陷; e2e 199/200/300 三档+test.full 全绿, 基线 26-11-02-1248

- 2026-11-02 21:0x 复测 issue 26-11-02-0902(抽屉页签切换卡 1-2s, 等 5e351c4b 合入后按用户要求重测): 同步到 e8d6279c; 干净端口 8157 新起 3000 种子桩(不复用 8155); 真实鼠标开抽屉+12 次切页签, atlas/prism 双皮肤、headless/headed/CPU4x 五轮 —— 切页签首帧 31-77ms、Layout 1.1-18.2ms、Style 3.7-9.1ms、Script 2.6-5.8ms、切换期 0 longtask(4x 下 70-389ms 仍无 1-2s)。同桩 A/B(页内强制"量齐前全量渲染"): 3000 行单发 _measureRowH 2086.9ms / longtask [4639ms, 2028ms], 修复后首访 30 行/20.4ms/0 longtask —— 结论: 随 5e351c4b 解决, issue 置 Done(关联对方提交, 非本条独立修复); 证据边界=报告者 session 未逐次录样, 属关联证据

- 2026-11-02 21:28 复测 drawer-tab-switch-lag: 同步 e8d6279c, 对照对方 5e351c4b 首访估算开窗, 同桩同路径不复现(31-77ms/0 longtask), issue 置 Done

- 2026-11-02 22:45 W6 测量先行 + 残留清理: 删除 `tmp-analysis/s6_test_discovery.py`(gitignored 一次性生成器, 内嵌模板含 `def _free_port`, 是 `test_free_port_single_source` 唯一误报源; `tmp-analysis/` 其余 100+ 旧草稿非同源, 未动), `test.free_port` 复验通过, `test.full` 恢复全绿 4888 passed/2 skipped(覆盖率 99%, 22523 stmts/134 miss, 分支 7728/128 miss), 基线 26-11-02-2246。W6 千文件桩 3 轮(prism dt11/1000 files): W6a 现状 POST 43-56ms/GET 83-94ms/徽章可见 142-153ms/0 longtask/13 次 DOM 变更, 乐观写候选 16.5-19.6ms/5 次; W6b payload 127911B(name 20k/piece_range 8k/size 7k/availability 4110/is_seed 4k/progress 3k/priority 1k, 键名开销 85600B), 取数 4.3-4.8ms/parse 0.15-0.18ms/assign 0-0.1ms/rowsFn 6.0-6.3ms/到两帧 40.3-63.7ms, 同尺寸静态对照 drawer.js 98215B/5-6ms。建议 W6b Dropped、W6a 做, 均待用户拍板; 代码实况: `_forEachRow` 不覆盖 `drawer.files`, W6a 需抽屉专用乐观写+双出口回滚。真机轨仍待 QBT_TEST_* token, 清单已入计划 §06.1。计划/档案保持 In Progress, 未 commit/push。

- 2026-11-02 22:47 W6 测量先行: W6a 现状 142-153ms→乐观写 16.5-19.6ms(建议做), W6b payload 127911B/裁剪省≈1.3ms(建议 Dropped), D1/D2/D3 已回填计划 §06, 真机轨待 QBT_TEST_* token; 服务端/前端代码零改动, 计划与档案保持 In Progress

- 2026-11-02 23:59 用户拍板后落地: W6a 实施(`drawer.js` 抽屉专用乐观写: 先采 prev→当帧写 priority→POST→waitCmd(10s), 失败/超时回 prev + 静默重拉 files 与整表重拉对齐; 重叠点击按 hash 序号只让最新一次收口), 新单测 2 条(静态顺序/双出口 + node 五态: 成功/失败/超时/重叠/幂等)+新 e2e 3 条×双皮肤(千文件桩: 可见延迟乐观 15-17ms vs 旧 171-174ms, 失败回滚 350-352ms, 超时回滚 10027-10036ms); W6b 按拍板 Dropped(不等于已完成)。真机轨选环境1(D盘 36595/36596, C盘目录不存在), 端口+路径+进程三方核对+real.guard 通过, 主实例 8 枚真实种子全程非活跃; 新增 RM08-09 千文件假种子用例并实测: files 1000 行/payload 156478B/冷 30-44ms 热 16-18ms/detail 12-28ms/命令回执 423-440ms, 真产品首帧 436-486ms/常驻 DOM 47 行(折叠1/展开47)/rowsFn 1002 行 max 7.6ms mean 5.28ms/longtask 0/乐观 9-14ms vs 旧 64-80ms; 中途主实例被外部停掉, 按授权 real.up 只拉起环境1后复跑。计划与档案在实现、验收、真机数字齐备后翻 Done; 未 commit/push(用户未授权)

- 2026-11-02 23:54 W6a 实施+验收(单测2+e2e6); W6b 拍板 Dropped; 真机环境1 RM08-09 千文件; 全量 4896 passed
