# 26-11-02-webui-large-filelist-perf — WEBUI 单种子千级文件列表性能统一优化 (W1-W5 落地, W6 待拍板)

**Status:** In Progress
**Added:** 2026-11-02
**Updated:** 2026-11-02
**Summary:** WEBUI 千级文件列表卡顿统一优化: 调研报告取证根因 R1-R6 → 计划 26-11-02-0351 拆 W1-W6 → 串行子智能体实施 W1(记忆化/廉价sig/content-visibility)+W2(kind 描述符参数化)+W3(抽屉挂窗)+W4(千级验收矩阵 8/8)+W5(主表 3000 种子复测全绿), 千级常驻 DOM 1001→45-48 行、交互 longtask 归零; 全量 4824 过/覆盖率 99.00% (基线 26-11-02-0707); W6(P3 可选)与真机轨待用户拍板/token
**Topics:** webui-large-filelist-perf
**Refs:** memory-bank/reports/26-11-02-0339-report-webui-large-filelist-perf.html, memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html, memory-bank/testing/baselines/26-11-02-0707-webui-large-filelist-perf.md

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
| S9 | W6a 乐观优先级对称补丁(依赖 D3 拍板+R5 占比实测) | Open |
| S10 | W6b payload 四步量法实测后裁剪(依赖 D1 拍板) | Open |
| S11 | 真机轨 rm08 千文件/千级种子条目(依赖用户注入 QBT_TEST_ token) | Open |

## 进度日志

### R0 · 立档 (2026-11-02)

- 全流程一轮完成: 报告→计划→W1-W5 串行实施→终态全量。千级实测: 常驻 DOM 行数 抽屉 1001→45-48(主表 3000 种子 24-34), rowsFn 千行热态 dt10 1.9-2.2ms/dt11 6.4-7.4ms, 勾选单行/数据回路/折叠三交互 longtask 全 0, 同屏主表窗口逐字段恒等(源族分家无串扰)。
- 全量与覆盖率数字见基线切片 26-11-02-0707(当时唯一红=认领链机检, 随本专题入库自愈)。
- 遗留: W6(D1/D3 待拍板)、真机轨(待 token)、计划外缺陷 5 条只记未改(dt12:323 残留 stringify sig、columns.js _rowWindow 死参、_ensureWinCtnBind unmount 不摘监听、_ensureWinTop 不含表头高度因子、perf.spec P1-3 预算余量薄 flaky 建议入池)。
- 工作区未提交(用户未授权)。

- 2026-11-02 07:08 报告 26-11-02-0339 + 计划 26-11-02-0351 + W1-W5 串行实施(千级 DOM 1001→45-48, longtask 归零, 主表 3000 种子复测全绿) + 基线 26-11-02-0707(4824 过/99.00%); 遗留: W6/D1/D3 待拍板、真机轨待 token; 工作区未提交(用户未授权)

- 2026-11-02 08:29 用户验收轮(3000 种子桩): 切标签页/关抽屉后卡死数秒且能滚不能点 —— 根因=columns.js _measureRowH 行高签名混入 viewMode(切页全表作废退全量量齐)+_winCtnSync 抽屉离场过渡期宽度假 bump(作废主表行高); 两守卫修复后 8.4s/5.6s longtask→0(主线程饿死假象, 非遮罩); 新守阵 e2e/window-invalidation 6 条+静态 1 条, 三皮肤千级 e2e 28/28
