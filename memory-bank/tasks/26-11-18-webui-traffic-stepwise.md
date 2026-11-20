# 26-11-18-webui-traffic-stepwise — 流量图采样步进+SSE改造立项(计划 26-11-18-0037)

**Status:** In Progress
**Added:** 2026-11-18
**Updated:** 2026-11-21
**Summary:** 流量图采样步进+SSE改造: 计划 26-11-18-0037 七批全部落地(样本分组点列契约/挂钟桶面退役/SSE 专用通道/前端契约适配与事件驱动/e2e 改写), 评审 7 批检 64/64 修 64 + 接缝终审 3 条处置全修, 全绿(见 kb.baseline); 改约两项待环境补验: Docker testbed e2e 与真机冒烟(qB 离线)
**Topics:** webui-traffic-stepwise
**Refs:** memory-bank/plans/26-11-18-0037-plan-traffic-stepwise-display.html, memory-bank/conventions/attachments/webui-traffic-beat.md, memory-bank/pitfalls/web-ui/wallclock-bucket-as-display-semantics.md, memory-bank/pitfalls/web-ui/tail-holding-clone-fake-data.md, memory-bank/pitfalls/web-ui/sse-payload-view-agnostic.md, memory-bank/testing/baselines/26-11-21-0016-webui-traffic-stepwise.md

## 本篇只回答

本轮(立项轮)只回答: 流量图尾端失真的根因是什么、彻底改造方案定成什么样。实施属于后续轮次, 按计划 26-11-18-0037 的分期表推进。

## 原始请求

1. 「流量图尾端一段数据偶尔不正常: 最后一段偶尔平直, 下一拍移动到倒数第二段后变为斜线, 说明尾端数据失真, 分析原因」(26-11-17)
2. 「不应该是拿到数据才更新流量图吗?」→ 追问「包括左滑」——确立「拿到数据才更新(含滚动)」的语义要求
3. 「grilling 然后出一个计划, 方向是彻底改造不做打补丁式修补」
4. 「我需要的是正常网络下抖动/延迟在毫秒级, 重新 grilling」——追加毫秒级管线硬指标
5. 「按推荐」(两轮) + 「确认」(共识表)——完成拍板

## 思考过程与决策

根因链: 尾桶在首样本落地前只有 holding 槽(`traffic_store_codec.py:339` → `traffic_grid.py:919-930` held=上一观测桶速率)→ 尾桶值≡倒数第二桶 → 严格平直; 真实样本落地改写 → 斜线。背后是三台时钟分裂(桶栅格锚挂钟/数据按采样节拍/前端按轮询), 持有面(F4/F3)只是糊缝。

grilling 五轮拍板(结论表见计划 §06): D1 全步进; D2 读侧契约深改(raw 桶面退役, 接受推翻 26-11-15-1104 沉没成本); D4 agg 段窗不动; D5 硬切无配置键; D6 契约破坏性重定义; D7 传输改 SSE(毫秒级硬指标否决轮询); D8 si=1.5s 保持; D9 序号+对账兜底; E1-E7 工程默认(专用通道/L0L1 保留/显式空值缺口/常量定值/测试面重写/组图同构/降级轮询)。

关键取舍: 「彻底」落点=契约层而非渲染层(把谎话藏起来≠不说谎); 存储面不动(v4 天文件本来就是样本槽, 桶化只是读侧表现层); 判定线=bbox 右缘语义不变, 全步进下 FX 锚零改动。

计划: `memory-bank/plans/26-11-18-0037-plan-traffic-stepwise-display.html`(§03 契约/传输/前端三层设计, §04 四阶段分期, §06 拍板记录)。

## 实现计划

按计划 §04 分期表执行, 每阶段独立可验:

1. 阶段 0 设计钉面: §03 契约表定稿, 常量定值(MAX_RAW_POINTS=500/对账 30s/静默 3×si)
2. 阶段 1 后端读侧: 样本分组装配纯函数 + traffic_qb.py 三端点替换 + meta 加 schema/stride + 电池改写
3. 阶段 2 传输面: handler 发布点 + StreamMixin per-scope 订阅 + /api/traffic/qb/stream 端点 + seq
4. 阶段 3 前端: 契约适配 + 订阅生命周期 + 事件驱动判定帧 + 窗口锚末样本 + 徽标 + 降级路径
5. 阶段 4 收尾: 评审/基线切片/pitfalls 回写/架构文档同步

部署纪律: 后端+前端同提交(硬切无兼容轨, 旧前端读不懂新契约)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 根因分析(持有克隆面/三台时钟) | Done(26-11-17) |
| 2 | grilling 五轮拍板 D1-D9/E1-E7 | Done(26-11-18) |
| 3 | 计划立档 26-11-18-0037(含事实探查: 消费方/判定线/测试钉面) | Done(26-11-18) |
| 4 | 阶段 0 设计钉面(§03 契约表定稿+常量表) | Done(26-11-18) |
| 5 | 阶段 1 后端读侧(T1a 装配纯函数/T1b 读侧切换+分组游标缓存/T1c-1/T1c-2 桶面退役) | Done(26-11-19) |
| 6 | 阶段 2 传输面(T2 SSE 专用通道) | Done(26-11-19) |
| 7 | 阶段 3 前端(T3 契约适配/T4a 事件驱动/T4b e2e 改写) | Done(26-11-20) |
| 8 | 阶段 4 收尾(终审/基线切片/pitfalls/架构文档/计划回写) | Done(26-11-21) |
| 9 | 改约: Docker testbed e2e(test.linux-env + test.linux-e2e, 本机无 docker) | Open |
| 10 | 改约: 真机冒烟(dev.run -- config.yml --dry-run, qB 离线拒连; 启动面日志已验正常) | Open |

## 进度日志

### R0 · 立档 (2026-11-18)

立项轮: 根因分析 → grilling(9 拍板 + 7 工程默认) → 计划 26-11-18-0037 立档(plans/ HTML, 四阶段分期)。产出: 计划 + 本档案。实施未开工, 等用户显式触发(开工先跑 my-commit-flow.sync)。

- 2026-11-18 00:57 立项轮: 尾端持有失真根因闭环(traffic_grid.py:919-930 held=上一观测桶速率克隆); grilling 五轮拍板 D1-D9/E1-E7; 计划 26-11-18-0037 立档(样本分组点列/SSE 专用通道/事件驱动判定帧, 四阶段); task 26-11-18-webui-traffic-stepwise 立档; 实施未开工

### R1 · 实施收口 (2026-11-21)

计划 26-11-18-0037 七批全部落地(分支 feat-traffic-stepwise-sse, 随本专题入库):

- T1a 2d000f5e 样本分组装配纯函数: traffic_group_assembly.py(assemble_group_points / _seam_spread_delta 提取件 / group_null_lo 单点 / MAX_RAW_POINTS=500)+ 装配电池 24 用例
- T1b+T1c-1 2328b7a8 读侧切换+分组游标缓存: traffic_qb raw 切点列契约(meta schema=2/stride); V4SeriesGroupCache 前缀和增量与冷算逐位等价; A4 重标定(250ms 线)
- T1c-2 15fdea15 挂钟桶面退役: 21 文件, fold/桶缓存/归桶/持有/封口/回填删除; agg 段零改动; 电池改写新语义守阵; A4 温态断言 best-of-3 去抖
- T2 8b3a7923 SSE 传输面: traffic_sample_events.py 主循环派发 + /api/traffic/qb/stream + StreamMixin per-scope + auth 票据路径集合
- T3 fe715cc5 前端契约适配: _qbPointsToData 点列直读/agg 兼容支/显式空值点缺口面/stepNom roll/pad 真值现数; node 电池改写
- T4a 5e195ee4 前端事件驱动: SSE 状态机 connecting→live→retry→degraded→stopped(会话代际)/数据合并 GET 列+事件尾点/徽标两态(滞后 Ns·已断连)/降级 3 轮→GET 轮询 60s 重试
- T4b a26ea6b4 e2e 改写: 5 spec 改写+新 traffic-stream.spec 3 用例+泵桩走真发布点(lib/traffic-stream.mjs + ui_harness.py); Windows 全量 @fast 全绿

评审(每批只读子代理, 检/修/轮取自提交 trailer): T1a 11/11 轮3 · T1b 14/14 轮4 · T1c-2 10/10 轮2 · T2 11/11 轮3 · T3 3/3 轮2 · T4a 8/8 轮2 · T4b 7/7 轮2 —— 七批累计检 64/64 修 64, 零 blocker 零入池; 接缝终审 3 条本批处置(2 minor: traffic_sample_events.py / traffic_stream.py docstring「前端按 stride 现算」失实修正 —— per-tick 样本粒度系对计划 §03② k>1 措辞的有意偏离, 前端不消费 meta.stride; 1 major: 架构文档 webui-traffic-beat.md「读侧根修收口」节仍是退役挂钟桶面语义 —— 整节保留为历史, 新增「读侧契约换代收口(26-11-18-0037)」节为现行权威)。收尾批末轮评审 7 条(5 minor + 2 nit)全修, 备忘: 15fdea15 提交消息的退役规模数字(+1393/-4129)同失实(git 实测 21 files, +1529/-4189)—— 已提交不可改, 以 webui-traffic-beat.md 退役清单条与本行为准)。

终态: 全量/e2e 全绿(数字权威 = testing/baselines/ 最新切片, 引用走 kb.baseline)。

改约两项(环境不可达, 如实报告未伪造): ①Docker testbed e2e(test.linux-env + test.linux-e2e)—— 本机无 docker, 需在有 testbed 的机器跑; ②真机冒烟(dev.run -- config.yml --dry-run)—— qB 离线(127.0.0.1:16585 拒连), 需 qB 在线后跑; 启动面日志已验正常(流量模块初始化/无异常栈/干净退出)。

回写面: conventions/attachments/webui-traffic-beat.md 换代收口节 + 坑档三件(pitfalls/web-ui/: wallclock-bucket-as-display-semantics / tail-holding-clone-fake-data / sse-payload-view-agnostic)+ 根 README 核对(无 API 面/数据契约描述流量图, 不动)。

- 2026-11-21 00:17 七批全部落地收口: T1a 2d000f5e/T1b+T1c-1 2328b7a8/T1c-2 15fdea15/T2 8b3a7923/T3 fe715cc5/T4a 5e195ee4/T4b a26ea6b4 计划 26-11-18-0037 全链(装配纯函数/读侧切换+分组缓存/挂钟桶面退役/SSE 专用通道/前端契约适配/事件驱动/e2e 改写); 评审 7 批检 64/64 修 64 零 blocker + 接缝终审 3 条处置(2 minor docstring 失实修正/1 major webui-traffic-beat.md 换代收口节现行权威); 全绿(见 kb.baseline 26-11-21-0016); 改约两项待环境补验: Docker testbed e2e + 真机冒烟(qB 离线); 回写面: 坑档三件(wallclock-bucket-as-display-semantics/tail-holding-clone-fake-data/sse-payload-view-agnostic)+档案+计划 R1
