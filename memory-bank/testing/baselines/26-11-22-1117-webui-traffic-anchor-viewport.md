# 6789 passed, 6 skipped, TOTAL 30681/85/10942/87 99% —— 流量图尾锚显式视口重构收尾基线

> 摘要: 流量图尾锚显式视口重构收尾基线(计划 26-11-22-0858 S1-S2; 三不变量结构性消除压缩类问题)
> 基线时间: 2026-11-22 11:17

## 验收数字

`commands run test.full` 实测(test.quick 同树 6793 passed, 6 skipped):

```
TOTAL                                                30681     85  10942     87    99%
6789 passed, 6 skipped, 8 warnings in 163.91s
```

e2e(Windows 本机 playwright, dev.e2e 形态按 spec 单跑): traffic-stream 3P / traffic-fx-anchor 6P / traffic-grid-stability 6P / traffic-gap-zones 全绿 / traffic-fx-frames 8P / traffic-fx-panel+source-switch 32P —— 流量系 spec 零适配全绿(锚视口下左端连续/末点贴判定线/跨度恒定断言天然成立)。Docker testbed 侧(变异测试)待环境, 与 26-11-18-0037 R1 同款改约口径。

## 本改动面

- src/auto_qb/webui/static/shared/qb_traffic_chart.js: 尾锚显式视口三不变量(视口恒等式 [anchor−span_s, anchor] / 单列恒等 / _qbLoad 取数窗口分量); 判定帧/帧循环/收敛帧/快路/修剪余量线(span+2 组距)/历史保留合并/_qbAnchorJudge+_qbAnimAnchorAt+_qbRetainHistory 新纯函数三件/_qbRollJudge+_qbPadTailColumns+_qbInheritedViewport+_qbBeatVpRem+_qbPad 记账退役/fx spawn pxPerT 改名义窗长/悬停索引直通/摘要窗内桶数/建图初始视口播种/头注与节注换代。
- tests/test_webui_static_dom_panel_traffic.py: 节拍电池 J1-J10/L1-L9/S0-S20b 换代(锚不变量矩阵: 细相位打断/隐藏/断档/突发/竞态乱序/历史保留/左缘连续/S20b 余量列变异盲区封堵), 退役件零残留反向钉, _qbLoad 窗口分量钉; A7 余量线对照; FXPANEL 双探针 harness 换代; mkBeat 签名(anchor/step/span)全家化。
- memory-bank: 计划 26-11-22-0858/任务档案/pitfalls web-ui/traffic-implicit-viewport 新档/权威附件 webui-traffic-beat.md 尾锚显式视口换代收口节/本基线切片。
