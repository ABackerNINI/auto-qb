# 7036 passed + 6 skipped, TOTAL 31424/108/11198/94 99% —— 流量图辉光 save/restore 配平修复全量基线

> 摘要: 流量图辉光 save/restore 配平修复全量基线
> 基线时间: 2026-11-26 06:06

## 验收数字

`commands run test.full` 实测(2026-11-26 06:04, Windows, rc=0, 132.60s, 工作树批态 = 辉光配平修复(qb_traffic_chart.js) + G17 守阵(canvas-ctx-transform-leak 坑档)未提交改动):

```
TOTAL                                                31424    108  11198     94    99%
7036 passed, 6 skipped, 1 warning in 132.60s (0:02:12)
```

与上基线(26-11-26-0502, 7036P/6S, TOTAL 31424/108/11198/94)对账: 通过/跳过/语句/分支/覆盖完全一致; 本批新增守阵 G17 落在既有电池内(不入新用例数), 坑档新档不改用例面 —— 用例数与覆盖零变化。

## 本改动面

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: `_qbDrawFxCurveGlow` 补第二笔 `ctx.restore()` 配平(保真修补 S1 重构压两笔 save —— `_qbCanvasScale` 内部 save+scale 与自身 clip save —— 只还了一笔); 函数注释补 transform 配平纪律段(uPlot 1.6.x 渲染无顶层 save 兕底, pxRatio>1 泄漏跨帧累积 = 真机全图逐帧放大错位)。
- `tests/test_webui_static_dom_panel_traffic.py`: 视觉引擎电池记账 ctx 增 saveCnt/restoreCnt 计数 + G17 配平断言(drawGlow 返回后 save==restore; 红绿双验: 修复前 39/40 唯一红); 电池 docstring 同步。
- `memory-bank/pitfalls/web-ui/canvas-ctx-transform-leak.md`: 新坑档(save/restore 失衡在 pxRatio=1 桩/CI 全绿、真机 125%/150% 缩放才爆发的掩蔽效应 + 判别/处置/守阵)。
- 真机形态回归: deviceScaleFactor=1.5 真浏览器探针连跑 12s 节拍动画, 逐帧采样 ctx.getTransform 恒 identity(20/20), 截图渲染正常 —— 修复前该形态必累积放大。
