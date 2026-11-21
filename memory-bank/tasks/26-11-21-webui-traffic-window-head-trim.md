# 26-11-21-webui-traffic-window-head-trim — 流量图 SSE 步进列名义窗头部修剪(左移压缩根治)

**Status:** Done
**Added:** 2026-11-21
**Updated:** 2026-11-21
**Summary:** 修 SSE 主路径下流量图左移时整列 x 向压缩、左端不出窗: 显示列两笔对账 GET 之间只增尾不剪头, auto x range 跨度随尾点变宽且 L0 min 恒驻(dx0=0)。修法 = 后端 meta 增 span_s(WINDOW_SPECS 经栅格单点下发)+ 前端 _qbTrimStaleHead 在 _qbStreamFrame 数据入口面按 尾t − span_s 修剪 store 列头部(门 = schema=2 且 span_s>0 且页面可见), 修剪点经 F5 补点通道出窗; 评审 3 轮(检 3/3 修 3)修掉显示面修剪悬停错位(major)与 hidden 期修剪脱拍(minor); 附带 13 处 node 探针 stdin 化(WinError 206 命令行上限)。
**Topics:** webui-traffic-window-head-trim
**Refs:** memory-bank/plans/26-11-18-0037-plan-traffic-stepwise-display.html, memory-bank/testing/baselines/26-11-21-1704-webui-traffic-window-head-trim.md

## 本篇只回答

「SSE 主路径下流量图左移时为何整列 x 向压缩、左端不出窗, 以及如何根治」—— 根因定位、修法取舍(显示面 vs 数据入口面)、评审轮次发现与处置。方案细节(名义窗修剪公式/门条件)单点在 `qb_traffic_chart.js` 的 `_qbTrimStaleHead` 节注。

## 原始请求

1. 「流量图左移时左边的曲线不出窗口而是曲线整体在x方向上压缩，这是错误的行为，分析原因」
2. 「修」(按分析的根治方向授权实施)

## 思考过程与决策

- **根因取证**(只读轮): SSE 阶段 3(计划 26-11-15-1104 → 26-11-18-0037 T4a)起显示列 = GET 组点列 + 事件尾点(`_qbStreamAppend` 只增尾不剪头, 头部只在 30s 对账 GET 整列替换时前进); 两笔对账之间每事件拍尾点 +si 而首点不动 → uPlot auto range `[xs[0], xs[n-1]]` 跨度单调变宽 = 整列压缩; 且该拍 `_qbRollJudge` dx0=0 → L0 摆回 min 恒驻(`dxMin0=dx0=0`), 左端从构造上不可能滚出窗。幅度 ≈ 对账周期/窗宽(1m 窗最坏 +50%/30s, 24h 窗不可见)。旧 GET 轮询时代每拍换列(dx0≈si≈dxN)无此问题 —— SSE 主路径引入的回归面。
- **D1 窗长来源**: 前端不复制 WINDOW_SPECS 窗名→秒映射(漂移面), 后端 `_meta` 增响应键 `span_s` = grid.t1−t0(整值归一), 沿 P4/F6「只增键」先例(旧前端忽略未知键)。经栅格单点而非限速事件合成首事件推 t0(后者无 ≤t0 事件时不合成, 有歧义)。
- **D2 修剪线锚尾点 t 而非墙钟**: 主循环停顿期尾点冻结 → 修剪线冻结 → 视图诚实冻结(与「滞后 Ns」徽标语义一致); 挂钟锚会在停顿期把左缘滑走。
- **D3 门 = meta.schema===2 且 span_s>0**: raw 段窗(1m-24h)是唯一点列每点带 t 的契约; agg 段窗(3d+)跨度增长 ≤对账周期/窗宽不可见; month(all)是数据面跨度, 本就该随尾点增长 —— schema 门天然排除, 无需窗名豁免。
- **D4 修剪落地面(评审轮1 major 改判)**: 初版在建图快路显示面修剪 —— 评审指出 `_qbHoverOf` 按显示列索引读 store 列 `d.points[i]` 会错位 cut 个点。改判: 修剪下沉到 `_qbStreamFrame` **数据入口面**, store 列 = 名义窗 + 事件尾点, 与显示列逐点恒对齐, 悬停/缺口区段索引零记账面; 附带恢复 SSE 前「摘要桶数 = 窗内桶数」语义。降级 GET 轮询/对账落袋整列替换恒新鲜不经修剪面。
- **D5 隐藏期门(评审轮2 minor)**: 修剪门与渲染门合流单点 `const live = !document.hidden`(同拍不齐会让 store 与冻结显示列失恒等, 回场悬停错位一拍; 追加不动既有索引, 隐藏期恒对齐; 长度界有 cap 兜底)。
- **D6 测试基建附带修复(计划内)**: 节拍电池 node 探针 `-e` 内联巨串在 Windows 触顶 CreateProcess 32k 命令行上限(WinError 206), S21 追加时实爆 → 13 处调用点改 stdin 形态(固定小包装器 `-e` + `input=探针`), argv 形状不变(图表路径仍 argv[1]), 见坑档 pitfalls/testing/node-e-cmdline-limit.md。

## 实现计划

1. 后端 `traffic_qb.py` `_meta` 增 `span_s` 键(+docstring)—— 单点装配全出口覆盖。✅
2. 前端 `qb_traffic_chart.js`: 模块级纯函数 `_qbTrimStaleHead`(修剪线含界保留/无 t 即停/列尾恒存活/非法 span 不剪)+ `_qbStreamFrame` 接线(live 门)+ 三处注释面回写(文件头 SSE 节/_qbStreamAppend 契约注/节注)。✅
3. 测试: 后端 meta 全量形状断言补 span_s + 未启用空态/30d 用例; 前端纯函数电池 8 断言(_NODE_QB_TRAFFIC_PROBE)+ SSE 电池 A7 帧面修剪真跑含门关对照; 两文件测试计划 docstring 同步。✅
4. 测试基建: 13 处 node 探针 stdin 化 + `_NODE_STDIN_WRAPPER` 常量。✅
5. 分批评审 3 轮到零 actionable(轮1 1 major → D4 改判修复; 轮2 1 minor 1 nit → D5+导语; 轮3 零发现)。✅

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 只读分析(根因定位+修法方向) | Done(2026-11-21) |
| 2 | 后端 span_s 键 | Done(2026-11-21) |
| 3 | 前端修剪函数+接线+注释面 | Done(2026-11-21) |
| 4 | 前后端测试电池+docstring | Done(2026-11-21) |
| 5 | 测试基建 stdin 化 | Done(2026-11-21) |
| 6 | 评审 3 轮零 actionable | Done(2026-11-21) |
| 7 | 真机观感验收 | Done(2026-11-21, 纯桩可验豁免 —— 理由见 R1) |

## 进度日志

### R0 · 立档 (2026-11-21)

用户报障(只读分析轮)→ 根因定位(SSE 步进列只增尾不剪头)→ 用户说「修」授权实施。实施 + 评审 3 轮(检 3/3, blocker/major/minor 全修)全绿(见 kb.baseline)。

### R1 · 收尾 (2026-11-21)

- 真机轨准入裁决: **纯桩可验豁免**(real-machine.md §00 反膨胀判据 —— 观感交互归 e2e 轨): 修法的行为面(修剪几何 dx0 随尾点推进/左端经补点通道出窗/对账拍 dx0≈0/悬停索引对齐)已在 node 电池数据几何层钉死(SSE 电池 A7 帧面修剪真跑含门关对照 + 纯函数电池 8 断言 + 既有 L0/S14-S20 拍几何电池), auto range→渲染映射是 uPlot vendor 行为(建图注已读源实证), 观感症状是几何事实的直接投影; SSE 接线面由 e2e traffic-stream.spec(驱动真发布点)覆盖, 不属本批改动面。若后续仍需观感直证: dev.sim + dev.webui + 浏览器自动化开 1m 窗观测左端随拍出窗。
- **Status 翻 Done。** 随本专题入库。

- 2026-11-21 16:53 修 SSE 主路径流量图左移整列压缩: meta 增 span_s(WINDOW_SPECS 经栅格单点下发)+ _qbTrimStaleHead 数据入口面按 尾t-span_s 修剪(门 schema=2 且 span_s>0 且页面可见, 修剪点经 F5 补点通道出窗, 对账落袋 dx0≈0 零变化拍); 评审 3 轮(检 3/3 修 3)修掉显示面修剪悬停错位 major 与 hidden 期修剪脱拍 minor; 附带 13 处 node 探针 stdin 化(WinError 206 命令行上限实爆); 档案 26-11-21-webui-traffic-window-head-trim
