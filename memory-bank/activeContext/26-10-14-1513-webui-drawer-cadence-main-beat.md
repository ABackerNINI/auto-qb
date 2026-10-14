# webui-drawer-cadence-main-beat — 抽屉页签轮询节拍: 5s 固定改主节拍(专题 Done)

> 摘要: 专题 webui-drawer-cadence-main-beat.
> 最后活动: 2026-10-14 15:13

## 正在进行

- Done: `_startDrawerPoll` setInterval 尾部 5000 改 `this.currentPollMs()`(种子页刷新间隔单点, 分档 1.5/2/3s + 失败退背)—— 抽屉实时速度与行数据同频观, 用户口径「与主节拍一致」字取.
- 服务端不动: peers 短缓存 1s 窗口仍窗口外(主节拍下界 1.5s), trackers 默认 2s 缓存把 1.5s 档白拉吸收.
- 守阵两处(dom_panel/shortcuts)里钉 setInterval 尾部正则改钉新形态同轮 + 五处代码注释「5s 轮询」引用改写 + 契约附件两处改.
- 验证: test.full 与 e2e 全量全绿(e2e 首轮一条 flaky 红属 delta-sync 时序竞态与本轮面 disjoint, 重跑绿), 数字见 kb.baseline(切片 26-10-14-1513).

## 下一步

- 无 —— 专题 Done, 已沉淀到档案 tasks/26-10-14-webui-drawer-cadence-main-beat.md.
- 移交观察(若用户再报滞后): setInterval 求值一次起轮, 跨分档稳态不重求值 —— 档案「已知偏差」写口径, 改 setTimeout 链与主轮同口径才是现求值.
