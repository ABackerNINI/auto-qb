# webui-traffic-fidelity-patch

> 摘要: S4 文档面收尾: 附件 webui-traffic-beat.md 增「缺陷修补(2026-11-26)」子节(辉光常驻/粒子三因子/P1-P6 新口径, 与代码实况核对) + 计划 26-11-26-0227 翻 Done 补 R2/R3 + 立档 tasks/26-11-26-webui-traffic-fidelity-patch.md
> 最后活动: 2026-11-26 06:22

**R0(2026-11-26 05:09):** S4 文档面收尾: 附件 webui-traffic-beat.md 增「缺陷修补(2026-11-26)」子节(辉光常驻/粒子三因子/P1-P6 新口径, 与代码实况核对) + 计划 26-11-26-0227 翻 Done 补 R2/R3 + 立档 tasks/26-11-26-webui-traffic-fidelity-patch.md

**R1(2026-11-26 06:01):** 真机乱跳根因修复: 保真修补 S1 常驻辉光 _qbDrawFxCurveGlow save/restore 失衡泄漏 ctx.scale(pxRatio), uPlot 1.6.x 渲染无顶层 save 兜底跨帧累积, pxRatio=1(桩/CI)无害全绿而真机 125%/150% 缩放全图逐帧放大错位 —— 补第二笔 restore 配平 + 记账 ctx save/restore 计数守阵 G17(红绿双验) + pxRatio1.5 真浏览器探针 transform 恒 identity 实测 + 坑档 canvas-ctx-transform-leak 新档

**R2(2026-11-26 06:22):** 评审闭环: 轮1 唯一发现(clearRect 欠清口径方向反了 —— 泄漏 scale 下实参映射更大设备矩形实为过清无残影)已修(坑档判别段+G17 注释两处), 引文过 review.check(快照态 1/1), 轮2 复评零 actionable 且核验轮1 两处落实未回退; test.full 复跑绿
