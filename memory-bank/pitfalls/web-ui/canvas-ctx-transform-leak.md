# canvas ctx transform 泄漏: 钩子内 save/restore 失衡在 pxRatio>1 真机才显形, 桩与守阵全绿

> 摘要: 自绘 canvas 钩子若压多笔 save(工具函数内部的 + 自身 clip 的)而 restore 少一笔, 泄漏的不是「状态」而是 transform —— 渲染引擎无顶层 save 兜底时按帧累积, pxRatio=1 的开发/桩/CI 环境 scale(1,1) 无害全绿, pxRatio>1(Windows 125%/150% 显示缩放)真机上全图逐帧放大错位
> 触发: canvas, ctx, save, restore, transform, pxRatio, devicePixelRatio, deviceScaleFactor, 显示缩放, 辉光, clip, 泄漏, 逐帧放大, clearRect

## 本篇只回答

「桩/e2e/全量守阵全绿、真机上图表彻底乱掉(曲线/网格/图例错位叠影乱跳)」这一类问题的根因形态与修法 —— 2026-11-26 流量图保真修补 S1 抽出的 `_qbDrawFxCurveGlow` 实证。

### 钩子 save/restore 失衡泄漏 scale(pxRatio), 渲染库无顶层兜底时跨帧累积

- **触发**: 绘制钩子经工具方法拿画布坐标系, 该方法内部 `ctx.save()+ctx.scale(pxRatio)` 且约定「调用方自还」(本项目 `_qbCanvasScale` 同款); 钩子体内为 clip 再压自己的 `save()` —— save 笔数 2、restore 笔数 1 即失衡。渲染库主循环**无顶层 save/restore 兜底**(uPlot 1.6.x 实证: `clearRect -> drawClear -> axes/series -> draw` 裸跑, 全文件无 setTransform), 泄漏的 scale 持续到下一帧并被下帧再乘。**pxRatio 掩蔽效应**: pxRatio=1 时 `scale(1,1)` 数值恒等 —— 无头浏览器(默认 deviceScaleFactor=1)、100% 显示缩放、CI、node 记账 ctx 全部不显形; 只有真机 Windows 显示缩放 125%/150%(或高 DPI 屏)才爆发。泄漏路径通常是「视觉增强层」(辉光/装饰), 关掉特效即消失, 更像特效 bug 而非坐标 bug。
- **判别**: 真机症状 = 逐帧恶化的全图放大错位(越画越大/整体外飞) —— clearRect 的设备像素实参在泄漏 scale 下映射为更大的设备矩形 = **过清**整幅, 不产生残影, 见不到残影不能据此排除本根因; 同一代码在 pxRatio=1 环境完全正常。机械判别(不依赖真机): 给记账 ctx 加 save/restore 计数, 每个绘制函数真跑一遍断言「返回后 saveCnt == restoreCnt」; 或真浏览器跑一轮动画后读 `ctx.getTransform()`, 断言恒 identity —— 只看像素/只跑 pxRatio=1 的 e2e 判不出。代码面扫法: 找「函数内调用返回 px 的坐标系工具(内部 save)且函数自身另有 save」的绘制函数, 数 restore 笔数。
- **处置**: 补齐配平 —— 结尾按压入逆序 restore 到平衡(本项目惯例 = 函数末 restore 数 = `_qbCanvasScale` 的 save + 自身 clip 的 save)。守阵前置: 记账 ctx 的 save/restore 计数配平断言是唯一能在 pxRatio=1 环境抓住它的机械面, 新增自绘 canvas 绘制函数时随电池补一条; pxRatio>1 真浏览器探针(getTransform 恒 identity)做真机形态回归; e2e/截图桩建议至少一轮 deviceScaleFactor>1 形态(Playwright `browser.newContext({ deviceScaleFactor: 1.5 })`), 否则这类缺陷整层测试盲区。
- **守阵**: `tests/test_webui_static_dom_panel_traffic.py` 视觉引擎电池 G17(drawGlow 返回后 ctx save==restore 计数相等, 红绿双验: 修复前唯一红)。
- **复发**: 0
