# WebUI qB 口径流量图可行性分析 (全局/单种/分组三图) — 可行性完结, 停在先不实施

> 摘要: 委派模式 4 子智能体串行 (代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写) 全部一次成功 0 异常失败; 产出 [reports/26-10-03-0757](../reports/26-10-03-0757-report-qb-traffic-charts.html) (13 节 dark 单文件) + 档案 [tasks/26-10-03-webui-qb-traffic-charts](../tasks/26-10-03-webui-qb-traffic-charts.md) (专题 torrent-traffic-stats)。核心结论: 可行性高 —— 三图实时值已随主循环 1.5s 增量同步在内存, 零新增 qB 请求, 推荐方案A (internal 全局任务 30-60s 采样 + 内存环 24h@30s + 小时 rollup 30 天落 state.json v3→v4 纯加法) + uPlot vendor 单文件。拍板四项: ① 先不实施 (P1-P5 保留待启动) ② 前端定 uPlot ③ 采样间隔/保留窗口做成可配置项 (新键须进 validate_config + config/schema.py) ④ 停机空洞表达 (null 断线 vs 补0) 与分组换 key 旧历史策略之后决定; 拍板记录已回写报告 §08。主 issue 26-09-27-1248 保持 Open。

> 最后活动: 2026-10-03 08:46

**正在进行**: 无 —— 停在「先不实施」。

**待办**: 实施启动后按报告 P1-P5 逐段派发, 每段独立可提交; 实施前先补两个拍板: 停机空洞表达 (null 断线 vs 补0) / 分组换 key 旧历史策略。
