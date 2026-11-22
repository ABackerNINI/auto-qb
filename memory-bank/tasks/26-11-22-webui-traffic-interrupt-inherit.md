# 26-11-22-webui-traffic-interrupt-inherit — 流量图打断拍视口继承(方向B): 摆回拍被对账GET打断零变化拍致补点滞留整列压缩

**Status:** Done
**Added:** 2026-11-22
**Updated:** 2026-11-22
**Summary:** 流量图打断拍视口继承(方向B): 摆回拍被对账GET打断零变化拍致补点滞留整列压缩 —— 修 26-11-21-1704(名义窗头部修剪)之后的残留压缩面: 视口/补点层
**Topics:** webui-traffic-interrupt-inherit
**Refs:** memory-bank/tasks/26-11-22-webui-traffic-anchor-viewport.md

## 本篇只回答

「26-11-21-1704 修完数据入口面修剪后, 为什么还偶尔整列 x 向压缩(特别是切换视图后), 以及方向B(打断拍视口继承)如何根治」—— 残余根因定位(F5 补点携带 × 摆回拍被打断 × 零变化判定不纠偏)与修法落点。数据面修剪几何见 26-11-21-webui-traffic-window-head-trim; 拍内核公式见计划 26-11-18-0037。

## 原始请求

1. 「这个问题没有彻底解决：流量图左移时左边的曲线不出窗口而是曲线整体在x方向上压缩，这是错误的行为。目前还是偶尔有x方向上的压缩，特别是切换视图后，分析原因」(只读分析轮)
2. 「按方向B修，补电池」(授权实施: 打断重建时继承被打断拍视口 + 补电池)

## 思考过程与决策

- **残余根因**(上一笔只修了数据面: store 列跨度 ≤ 名义窗; 本笔在显示/视口层):
  1. 建图快路每拍都调 `_qbPadTailColumns`, 携带门 `carry = (willShift || k === 0) && pIdx > 0` —— 上一拍留过补点时, **零变化拍也把补点 setData 进显示列**; `setData` 把 x 视口重置成**含补点全宽 auto range**。
  2. 把视口从全宽摆回真窗的 `setScale` 只挂在 `needsShift` 分支; 三条不纠偏路: 零变化拍早退(dx0=0 且 dxN=0)/纯数值收敛拍(needsTail-only)/reduce 拍。
  3. **触发链**: SSE 拍滚出一点(k=1)→ 补点进列 → L0 摆回拍开跑(shiftMs = 0.6×beat600 ≈ 360ms)→ **30s 对账 GET(或静默重拉/回场补拉/换窗 GET)恰在此窗落袋** → 判定 dx0=0/dxN=0(采样间隔内大概率无新样本)→ 零变化拍 → 补点滞留 + 视口定格全宽 = 整列压缩 + 左缘显示已滚出旧曲线; 收敛帧 `dropPad = needsShift && pad>0` 对非摆回拍**故意不摘** → 滞留到下一笔真样本拍(最长一个采样周期, 生产 si=1.5s)才自愈。触发概率 ≈ 摆回窗 360ms / 拍周期 1.5s ≈ 每笔对账 GET 24%(评审轮3 改判: 生产 si = main_tick 1.5 × multiplier 1 = 1.5s, 非 30s) = 「偶尔」; 切窗/回场 GET 密度升高 → 「特别是切换视图后」。
  4. 幅度: 跳宽 ≤ 补点跨度(≤2 组距); 1m 窗(60s 窗/组距 k×si=1.5s)最坏 ≈ +5% 宽度(评审轮3 改判, 原「+50% 与原报障同谱」把 head-trim 的对账周期漂移量错安到本残留 bug), 30m+ 窗不可见。
- **D1 方向B语义**(用户拍板): 打断重建时**继承被打断拍的当前视口**(读 cancel 前 anim 按拍内公式重建), 任何打断都不回跳。判定帧 setScale/帧循环/收敛/装饰 tip 四处公式**全部不动**(锚恒真窗口), 只把 anim 位移字段(dx0/dxN/dxMin0)换算到继承起点(剩余位移) —— t=0 视口 = 用户正看到的画面, 滑完剩余位移后收敛摘补点归位。
- **D2 重建而非读 scales**: `_qbInheritedViewport` 按拍内公式(rem = 1 - easeOut(clock/shiftMs), 含末帧 ulp 吸附钳)重建视口, 不读 uPlot scales 内部态 —— setScale 攒 pending 下次提交才消费, 判定帧同块 setScale 未提交时 scales.x 滞后一帧; 公式重建与帧循环逐位同源。rem 计算抽单点 `_qbBeatVpRem` 帧循环/重建两处共用(漂移即打断回跳, 静态钉 + 计数钉双封)。
- **D3 继承门**: rewin(换窗)拍不继承 —— 几何不连续本就瞬时落地, 补点随整列替换丢弃。继承拍强制进摆回判定(零变化打断拍 roll 伪真)后走**同一 `_qbFxShiftGate` 单点**现判可见性/instant 档 —— gate 拒绝(instant/亚可见)时走原生早退(instant 档既有语义不变)。
- **D4 范围裁定**: reduce/instant 档的**恒定**压缩变体(补点永不摘 = 恒 +k·step 宽度)是方向A(不摆回的拍不消费补点)的地盘, 本笔不动 —— 范围守恒; 档案留痕待拍板。
- **D5 捕获时机**: 快路 `_qbChartBuild` 在 `setData` **之前**捕获, 用 `prev.data[0]`(拍 A 显示列, 补点在内)与 `prev._qbBeat.anim` 重建。真实约束是**列亲和**(评审轮1 minor 改判): setData 落袋后 `prev.data[0]` 已是新列而 `anim.pad/n/dxMin0/dxN` 记账属拍 A 旧列 —— 晚捕获 = 新列 x 旧记账错位: 零变化打断两列同形无差(变异实证电池拦不住), 破坏面在真滚动打断(max 锚按新列末样本右移一个尾差, t=0 跳变), 该面靠静态钉逐字序在守。视口重建走公式而非读 scales(setScale 攒 pending 滞后一帧)是独立决策(D2); 静态钉封捕获先于 setData 的逐字序。
- **D6 测试面**: 调度器电池 S21(零变化打断继承全链)/S24(真滚动打断继承 —— max 侧从打断位续滑)/S25(rewin 打断不继承); 纯函数电池 _qbInheritedViewport/_qbBeatVpRem; 静态钉更新(快路逐字序/帧循环 rem 单点化/easeOut 计数钉/签名正则)。

## 实现计划

1. 模块级纯函数 `_qbBeatVpRem`(rem 计算单点: easeOut + ulp 吸附钳)+ `_qbInheritedViewport`(在途摆回拍取消瞬间视口重建; 预览拍/非摆回拍/null 安全/isFinite 防御)—— node 电池真跑。✅
2. 帧循环 rem 行改消费 `_qbBeatVpRem(a)`(单点化, 行为逐位不变)。✅
3. 快路捕获(`_qbInheritedViewport(prev._qbBeat && prev._qbBeat.anim, prev.data && prev.data[0])` 先于 setData)+ `_qbBeatStart(scope, prev, inh)` 第三参。✅
4. `_qbBeatStart` 继承逻辑: 签名加 `inherited`; 非继承拍位移字段逐位不变; 继承拍 dxMin0/dxN 换算剩余位移 + anim.dx0 取 dxMin0(零 dxN 剩余的纯 min 侧继承拍也要逐帧提交)+ roll 伪真进摆回门。✅
5. 注释面回写(文件头 SSE 节/_qbBeatStart 节注/快路捕获注)。✅
6. 测试: 静态钉六处更新 + 调度器三场景 + 纯函数电池 + 两文件 docstring/测试计划同步。✅
7. 分批评审到零 actionable。✅

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 只读分析(残余根因定位, 方向A/B 拍板) | Done(2026-11-21) |
| 2 | 纯函数两件 + 帧循环单点化 | Done(2026-11-22) |
| 3 | 快路捕获 + 判定帧继承逻辑 | Done(2026-11-22) |
| 4 | 注释面回写 | Done(2026-11-22) |
| 5 | 测试电池 + 静态钉更新 + docstring | Done(2026-11-22) |
| 6 | 分批评评零 actionable | Done(2026-11-22, 轮1 检 2/2 修 2 / 轮2 零发现, 共 2 轮) |
| 7 | 真机观感验收 | Open(dev.sim + dev.webui 浏览器自动化开 1m 窗, 复现触发链难度高 —— 几何面电池已钉, 同 26-11-21-1704 R1 豁免口径) |

## 进度日志

### R0 · 立档 (2026-11-22)

用户报障(只读分析轮)→ 残余根因定位(F5 补点携带 × 摆回拍被打断 × 零变化判定不纠偏; 与 26-11-21-1704 修的数据面互补)→ 用户拍板方向B并授权实施(「按方向B修，补电池」)→ 实施中。

### R1 · 实施+评审收口 (2026-11-22)

- 实施全量落地: 纯函数两件(`_qbBeatVpRem` rem 单点 + `_qbInheritedViewport` 视口重建)+ 帧循环 rem 单点化(行为逐位不变)+ 快路捕获(先于 setData, 列亲和约束)+ 判定帧第三参继承(摆回锚换算剩余位移, 四处公式不动; 继承拍 roll 伪真进同一 `_qbFxShiftGate`)+ 注释面三处回写; 测试: 纯函数电池 L1-L8 + 调度器 S21/S24/S25(后补 S26)+ 静态钉六处更新 + docstring/测试计划同步。
- 评审 4 轮到零 actionable: 轮1 全能档 1 派发, 检 2/2(1 minor 快路捕获注释因果错 —— 「setData 重置视口」错误因果改判「列亲和: setData 后 prev.data[0] 已是新列而 anim 记账属拍 A 旧列, 破坏面在真滚动打断 max 锚右移尾差」+ 1 nit 纯 min 侧无行为化场景 → 补 S26); 轮2 修复增量复评零发现; 轮3 附件回写复评(远端推进两次 rebase 重钉)检 1/1(1 minor 条目算术前提: 生产 si 实值 1.5s 非 30s, 触发概率重算 ≈24%/笔 GET、1m 窗最坏 ≈+5% —— 附件与档案同源数字一并更正); 轮4 数字修正复评零发现, 轮1-3 发现校验未回退。Review: webui 流量图 · 381 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 轮 4 · 基 027e8ea94f4a · 派发 1 · 齐平 41000b0c。
- 评审期间远端推进 6 笔(relocate 专题)→ sync 快进 8aea3d16→7fb43e91, 零碰本批改动面。
- test.quick 6793 passed + 2 skipped(含远端并合的新测试)。test.full 基线切片待 R2。

### R2 · 收尾 (2026-11-22)

- Status 翻 Done(真机轨留 Open: 观感面走 26-11-21-1704 R1 同款豁免口径 —— 几何事实电池钉死, 触发链复现成本高)。
- test.full 6789 passed + 6 skipped(基线切片 26-11-22-0628: TOTAL 30681/85/10942/87 99% 档); 权威附件 webui-traffic-beat.md「打断继承视口」条目入库; kb.wrap 切片 26-11-22-0626。

- 2026-11-22 06:26 修复轮: minor注释因果改判+nit补S26+档案D5同步; 复评轮2零actionable; 权威附件回写打断继承条目
