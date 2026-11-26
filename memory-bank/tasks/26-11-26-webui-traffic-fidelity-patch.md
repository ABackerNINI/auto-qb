# 26-11-26-webui-traffic-fidelity-patch — WEBUI 流量图保真二轮缺陷修补(辉光常驻+视口裁剪+粒子三因子+勾选六项)

**Status:** Done
**Added:** 2026-11-26
**Updated:** 2026-11-26
**Summary:** WEBUI 流量图保真二轮缺陷修补(辉光常驻+视口裁剪+粒子三因子+勾选六项) + 逐拍菱形锚越界触发的详情横向滚动条修复
**Topics:** webui-traffic-fidelity-patch
**Refs:** memory-bank/plans/26-11-26-0227-plan-webui-traffic-fidelity-patch.html, memory-bank/testing/baselines/26-11-26-0502-webui-traffic-fidelity-patch.md

## 本篇只回答

流量图保真二轮缺陷修补(计划 26-11-26-0227)这一轮「怎么落的、落到哪」: S1-S4 八笔提交的执行状态、五缺陷+六勾选共 11 项修法与代码事实的对应、守阵与基线收口。逐项修法与取舍的单点在计划 §03, 动效现行口径单点在附件 `conventions/attachments/webui-traffic-beat.md`「缺陷修补」子节 —— 本档案只记执行与验证, 不复述方案。

## 原始请求

1. 真机复报两缺陷: 曲线辉光只在拍内闪现(拍间消失)、辉光溢出绘图区浮进左缘图例区; 附「其它特效不尽人意」。
2. 追问差异清单来源(读文档还是读代码)后逐项勾选 P1-P8: P1/P2/P4/P5/P6 修, P3/P7/P8 保留(落计划 §06 D3); 代码驱动补漏的三处粒子漂移(P9-P11)默认纳入。
3. 「1 分钟流量图每拍会使详情面板出现一次横向滚动条, 分析原因并修复」。

## 思考过程与决策

- 权威计划 = `plans/26-11-26-0227-plan-webui-traffic-fidelity-patch.html`; 关键拍板: D1 辉光改常驻(非加长窗) / D3 用户勾选六项 / R2 代码驱动比对补 P9-P11(文档零记录)。
- 缺陷一+二同根(都在二轮 S3 新增辉光段), 合并为一处重构: 抽独立 `_qbDrawFxCurveGlow`。
- 张力处置: P6 装饰 clip 放宽会进轴标签区(缺陷二教训), 默认放宽到画布边缘+真机核对不压轴标签; P1 右向不裁靠行程静态钳而非放宽裁剪。
- 横向滚动条根因 = P5 的 DOM 锚跟随新末点、L0 视口尚在滑向新锚, 锚短暂越过 `.u-wrap` 右缘; 原无裁剪把装饰越界传成抽屉 scrollable overflow。修复限定在共享图装饰层 `.u-wrap { overflow: clip }`, 不改抽屉滚动策略。

## 实现计划

按计划 §04 分四步, 每步守阵先红后绿、每勾选项独立提交:

- S1 缺陷一+二: 辉光常驻重构(去时间窗/严格 rect 视口裁剪/帧末清 blur)。
- S2 缺陷三四五: 粒子纵压 0.7 / 寿命 ×life / 边数 i%3。
- S3 勾选六项: P1(360°+dist 右余量静态钳) / P2(lw3+0.55×q×impact) / P4(判定线小菱形) / P5(DOM 锚随末点滑) / P6(去钳制镜像+上下缘放宽)。
- S4 守阵总收口: 静态钉/e2e 全改判 + test.full + 新基线切片 + 文档回写收尾。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 辉光常驻+严格视口裁剪, 抽 `_qbDrawFxCurveGlow`(348002a3) | Done(2026-11-26) |
| S2 | 粒子三因子: 纵压 0.7/寿命 ×life/边数 i%3(b8d1f2f2) | Done(2026-11-26) |
| S3-P2 | 判定线短亮段 lw3+0.55×q×impact(523fa0b0) | Done(2026-11-26) |
| S3-P4 | 判定线小菱形, 双锚形态(f737bcf6) | Done(2026-11-26) |
| S3-P1 | 喷射角 360°+dist 按右余量静态钳(9cfe6a24) | Done(2026-11-26) |
| S3-P5 | DOM 锚动画期随 tipX 滑, 静止回落 L+W, 零新 rAF(f00b99fa) | Done(2026-11-26) |
| S3-P6 | 去 ringY 钳制与底缘镜像, 装饰 clip 上下缘放宽到画布缘(6fe8ad28) | Done(2026-11-26) |
| S4 | 守阵总收口: 静态钉/e2e 全改判 + 基线切片 26-11-26-0502(a33aa41b) | Done(2026-11-26) |
| S4 文档面 | 附件「缺陷修补」子节 + 计划翻 Done + 本档案立档 + wrap 切片 | Done(2026-11-26) |

## 进度日志

### R0 · 立档 (2026-11-26)

立档于 S4 文档收尾轮: S1-S4 八笔提交均已落地(348002a3/b8d1f2f2/523fa0b0/f737bcf6/9cfe6a24/f00b99fa/6fe8ad28/a33aa41b), 全量基线切片 `26-11-26-0502-webui-traffic-fidelity-patch` 已入库; 附件 `webui-traffic-beat.md` 已增「缺陷修补(2026-11-26)」子节(与代码实况逐项核对), 计划 doc-status 翻 Done。P3/P7/P8 保留未动。

- 2026-11-26 05:09 S4 文档面收尾: 附件 webui-traffic-beat.md 增「缺陷修补(2026-11-26)」子节(辉光常驻/粒子三因子/P1-P6 新口径, 与代码实况核对) + 计划 26-11-26-0227 翻 Done 补 R2/R3 + 立档 tasks/26-11-26-webui-traffic-fidelity-patch.md

- 2026-11-26 06:01 真机乱跳根因修复: 保真修补 S1 常驻辉光 _qbDrawFxCurveGlow save/restore 失衡泄漏 ctx.scale(pxRatio), uPlot 1.6.x 渲染无顶层 save 兜底跨帧累积, pxRatio=1(桩/CI)无害全绿而真机 125%/150% 缩放全图逐帧放大错位 —— 补第二笔 restore 配平 + 记账 ctx save/restore 计数守阵 G17(红绿双验) + pxRatio1.5 真浏览器探针 transform 恒 identity 实测 + 坑档 canvas-ctx-transform-leak 新档

- 2026-11-26 06:22 评审闭环: 轮1 唯一发现(clearRect 欠清口径方向反了 —— 泄漏 scale 下实参映射更大设备矩形实为过清无残影)已修(坑档判别段+G17 注释两处), 引文过 review.check(快照态 1/1), 轮2 复评零 actionable 且核验轮1 两处落实未回退; test.full 复跑绿

- 2026-11-26 16:52 修复 1m 流量图逐拍横向滚动条: .u-wrap overflow:clip 裁装饰锚; 四皮肤 DPR1.5 红绿回归+静态守阵; 两轮只读评审零发现; test.full 全绿; @fast 唯一无关主表悬停偶发失败单跑复绿; 按请求边界未新建基线切片
