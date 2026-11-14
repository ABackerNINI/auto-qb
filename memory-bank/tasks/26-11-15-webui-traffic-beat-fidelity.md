# 26-11-15-webui-traffic-beat-fidelity — traffic fx 复刻矫正(计划 26-11-14-1313)

**Status:** Done
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** traffic fx 复刻矫正(计划 26-11-14-1313)六批落地收口: F1-F6 全提交 + A1-A7 专项 e2e + 量法偏差降级记档 + S3b 回写收口
**Topics:** webui-traffic-beat-fidelity
**Refs:** memory-bank/plans/26-11-14-1313-plan-webui-traffic-beat-fidelity.html, memory-bank/conventions/attachments/webui-traffic-beat.md, memory-bank/testing/baselines/26-11-15-0432-webui-traffic-beat-fidelity.md, memory-bank/pitfalls/testing/headless-canvas-decor-ink.md, memory-bank/pitfalls/testing/uplot-axes-splits-generator.md

## 本篇只回答

traffic fx 复刻矫正(计划 26-11-14-1313)六批各落在哪、评审结论、量法偏差降级与遗留清单; F1-F6 的**产出口径权威**在 `conventions/attachments/webui-traffic-beat.md`(本档案不复制口径), 取证与拍板全录在计划。

## 原始请求

用户 26-11-14 两轮报障(复刻模板 26-11-12-1139 的动效 vs 生产): ①动效几乎不出现(稳态流全静默)/缺常驻旋转菱形/0 流量零动效/x 轴逐拍抖动; ②二次补充: 动效右·下被裁剪/曲线不总落判定线(尾桶间歇 null)/面板采样显示口径(配置 1.5s 显示 2.0s)。流程拍板 D5: 只建计划暂不动代码, 实施开工由后续会话推进。

## 思考过程与决策

三轮帧采样取证(生产同构桩 2400+6011+6011 帧)闭环七项根因(G1-G7), 修复方案 F1-F6 + 拍板 D1-D5, 单点在计划 `26-11-14-1313-plan-webui-traffic-beat-fidelity.html`(§01-§07)。关键拍板: D1 活跃轨(值>0)恒 ≥Lv.1; D2 CSS 合成器菱形(零 rAF/零重绘); D3 抖动主靶=x 轴栅格(F3)非 y 轴; D4 二次补充四项并入(F2/F4/F5/F6); P1 间隙上界 max(interval_s, 采样)×2 / P2 reduced-motion 隐藏 / P3 环心上抬钳制。前序计划 26-11-12-1139 的「Δ<0.5% 静默」「零流量零装饰」「菱形只在拍窗画」口径被本计划正式推翻(其 §11 R11/R12 已补指链)。

## 实现计划

计划 §04: S1a 栅格 floor+1 / S1b 活尾延伸 / S1c meta 增 sample_interval_s / S2a 等级门恒 ≥Lv.1 / S2b CSS 常驻菱形锚层 / S2c clip 修正+两值显示 / S3a 回归面+A1-A7 专项 e2e / S3b 回写收口(本批)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1a+S1c | 栅格桶数 ceil→floor+1 + meta 增 sample_interval_s(e36c663d) | Done(26-11-14) |
| S1b | 活尾链端延伸 holding 槽(a9f0f026) | Done(26-11-14) |
| S2a+S2c | 等级门恒 ≥Lv.1 + clip 右缘放宽/环钳制/粒子镜像 + 采样两值显示(503230e8) | Done(26-11-14) |
| S2b | CSS 常驻旋转菱形锚层, 拍间不停零 rAF(1a9a08f5) | Done(26-11-14) |
| S3a | 帧级探针复核 + A1-A7 专项 e2e + 页签定位红面修复(844bb2c1) | Done(26-11-14) |
| B6 收尾 | S3b 回写(webui-traffic-beat.md/前序计划 §11/计划 Done) + 基线切片 + 立档 + 坑档两条 | Done(26-11-15) |

## 进度日志

### R0 · 立档 (2026-11-15)

六批按计划 §04 全部提交(e36c663d/a9f0f026/503230e8/1a9a08f5/844bb2c1 + 本批收尾), 每批过只读评审(各提交 `Review:` trailer: B2-B5 均 blocker 0)。量法偏差两处如实降级记档: A1 像素强度量法在 headless 软件光栅不可落地(装饰墨读不到)→ 现落点=调度器在场+电池 spawn/clip 面(坑档 `pitfalls/testing/headless-canvas-decor-ink.md`); A6 像素探针降级为 clip 实参 ctx.rect 记账(与电池 G0 同契约); A4 量法踩 `u.axes[0].splits` 生成器坑, 真值在 `_splits`(坑档 `pitfalls/testing/uplot-axes-splits-generator.md`)。前序计划 §11 补 R12 收口指链; 本计划 doc-status 置 Done。**遗留**: Linux testbed 三面(pytest/e2e/变异)本机无 docker 留待补跑 —— 全量测试 Windows 侧全绿(见 kb.baseline), Linux 补跑结果随下次相关批次记录。

- 2026-11-15 04:36 S3b 收口: webui-traffic-beat.md 口径回写(F1-F6 全落地) + 前序计划 §11 R12 指链 + 计划 Done + 基线切片 + 坑档两条(decor-ink/splits)
