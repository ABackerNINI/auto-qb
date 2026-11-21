# webui-traffic-root-revamp

> 摘要: grilling 三轮七问拍板 D1-D7 全按推荐 + 三轮取证(仿真/基准/vendor)闭环四症状与两根缺陷(双几何/速率双轨) + 计划 26-11-15-1104 入库(Open, F1-F8/A1-A8/S1-S5 待显式开工) + 档案立档; 零代码改动
> 最后活动: 2026-11-21 16:53

**R0(2026-11-15 11:09):** grilling 三轮七问拍板 D1-D7 全按推荐 + 三轮取证(仿真/基准/vendor)闭环四症状与两根缺陷(双几何/速率双轨) + 计划 26-11-15-1104 入库(Open, F1-F8/A1-A8/S1-S5 待显式开工) + 档案立档; 零代码改动

**R1(2026-11-17 07:59):** S5 回写收口: webui-traffic-beat.md 读侧根修收口节+旧口径四处作废修正; 前序两计划指链 R13/R1 落行(双向); 本计划 §10 R3+doc-status Done; 任务档案收口(状态表全 Done+收口结论/指链核对节); 新坑档立档(pitfalls/testing 基准电池标定环境与并行负载因子余量); 计划外漂移列清单交主会话(baseline.md -n 4 漂移等 7 条入池候选)

**R2(2026-11-21 16:53):** 修 SSE 主路径流量图左移整列压缩: meta 增 span_s(WINDOW_SPECS 经栅格单点下发)+ _qbTrimStaleHead 数据入口面按 尾t-span_s 修剪(门 schema=2 且 span_s>0 且页面可见, 修剪点经 F5 补点通道出窗, 对账落袋 dx0≈0 零变化拍); 评审 3 轮(检 3/3 修 3)修掉显示面修剪悬停错位 major 与 hidden 期修剪脱拍 minor; 附带 13 处 node 探针 stdin 化(WinError 206 命令行上限实爆); 档案 26-11-21-webui-traffic-window-head-trim
