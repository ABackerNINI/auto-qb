# qb-traffic-rate-basis — 流量图速率口径调研

> 摘要: 用户反馈「流量图太陡」, 命题调研 qB 与业界方案裁决口径 —— 结论: 数据口径采用**区间平均速度**(计数器差分 Δbytes/Δt), 否决移动平均(平滑归展示层, 按观感再议); 瞬时速度继续落盘(r 行)供 agg 峰值与原始信号留存, 仅不再上图。调研全程 5 子代理串行, 全部一次成功; 报告 [26-10-07-2031](../reports/26-10-07-2031-report-qb-traffic-rate-basis.html)。
> 最后活动: 2026-10-07 20:46

**Refs:** memory-bank/tasks/26-10-07-webui-qb-traffic-rate-basis.md

- 陡因(代码事实): 1m~24h 窗走 raw 段, 1 桶=1 个 30s 采样, 采样器直采 qB 瞬时字段(libtorrent 1Hz×5s EWMA 快照), 前端零平滑; 3d+ 窗消费 dt 加权 hour 聚合, 天然平缓。
- 落地面(未决项, 实施与否由用户拍板): 纯读侧 —— r 行累计字节早已逐采样落盘, `v4_totals_points` 差分边界全套现成, 仅 `traffic_grid.py` 加桶点变换 + `traffic_qb.py` 三端点接线; 采样器/存储/state_file/前端/配置零改动, 旧数据即刻按新口径出图。
- 调研资产(仓库外, 长期留用): `D:\Projects\Else\qBittorrent`(master@8182ae071) 与 `D:\Projects\Else\libtorrent`(RC_2_1@53acefea9) 完整克隆; `D:\Projects\Else\auto-qb-speed-research\` 四份阶段笔记(01 现状 / 02 上游 / 03 业界 / 04 对比)。
- 任务档案: [26-10-07-webui-qb-traffic-rate-basis](../tasks/26-10-07-webui-qb-traffic-rate-basis.md)。
