# 26-10-07-webui-qb-traffic-rate-basis — 流量图速率口径调研(瞬时 · 区间平均 · 移动平均)

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07
**Summary:** 流量图「太陡」口径调研完成: 陡因=raw 窗 1 桶 1 瞬时样本+前端零平滑; 裁决数据口径采用区间平均(计数器差分 Δbytes/Δt)、否决移动平均(平滑归展示层); 落地为纯读侧接线(traffic_grid.py 桶点变换 + traffic_qb.py 端点), 零存储/state_file/配置改动; 报告 26-10-07-2031。
**Topics:** qb-traffic-rate-basis

**Refs:** memory-bank/reports/26-10-07-2031-report-qb-traffic-rate-basis.html,memory-bank/activeContext/26-10-07-2046-qb-traffic-rate-basis.md,memory-bank/testing/baselines/26-10-07-2053-webui-qb-traffic-rate-basis.md

## 原始请求

用户命题: 「流量图太陡, 调研 qb 和成熟的解决方案, 是采用移动平均还是平均上传/下载数据而不是实时速度? 比如 t0→t1 上传了 10MiB, 那么这段时间的平均上传速度是可以算出来的, 就不需要保存瞬时速度了, 写一份调查报告。过程中将 qb 或其它 git 仓库 clone 到 D:\Projects\Else 中以后就不用再找了。」执行方式由用户指定: 先拆解任务, 派子代理分阶段串行实施(防长任务 O(n²) token 与出错丢进度), 主会话只委派与总结; 完成后等提交指令。 <!-- wording:allow --> (引述用户原话)

## 思考过程与决策

- **拆解**: 研究型任务(不改业务代码), 按数据链路切五阶段串行子代理: P1 本项目现状 → P2 上游机制(克隆 qB/libtorrent) → P3 业界实践 → P4 方案对比 → P5 报告撰写; 每阶段详细笔记落盘仓库外 `D:\Projects\Else\auto-qb-speed-research\NN-*.md` 防进度丢失, 阶段间只传摘要防上下文膨胀。5 个子代理全部一次成功, 零重试。
- **关键事实**(详见报告 §2-§4):
  1. 陡因 = raw 段 1 桶=1 个 30s 瞬时样本(采样器直采 qB 字段, 即 libtorrent 1Hz 5 秒 EWMA 的快照)且前端零平滑; hour/day/month 聚合层本就是 dt 加权真均值, 陡只在 raw 窗。
  2. qB/libtorrent: 速度字段无 qB 侧二次平滑; qB GUI 速度图自带 Averager 分桶(1s~144s); 字节差分先例现成(calcRate / dl_speed_avg)。
  3. 业界: counter 差分是标准口径(MRTG/RRDtool/Prometheus/vnstat/Windows 性能计数器); 平滑归展示层时间桶 SMA; counter 重置丢点或 clamp 0。
- **决策**: 四方案(A 瞬时 / B 区间平均 / C 移动平均 / D 混合)对比后**推荐 B, 纯读侧实现**——r 行累计字节早已逐采样落盘、读侧差分 `v4_totals_points` 含重启/断链/z 游程边界全套现成, B 只是「把已存在的差分通道接到速率通道」; 写侧改 rate 列会新旧口径混窗+真峰值丢失+需按黄金法则 3 持久化基线。D 的展示层平滑留待 B 落地后按观感再议。瞬时速度继续落盘供 agg dl_max 与原始信号分析, 仅不再上图。
- **落地要点**(文件级, 未实施): `traffic_grid.py` 新增桶点级「totals 差分÷覆盖宽」变换接在 `v4_grid_obs` 前(窗口左界外扩一桶补窗首) + `traffic_qb.py` 三端点接线; 不需要新配置键(日后若做平滑开关, 须同步 models.py / validation/sections.py / schema/groups.py 三处)。

## 实现计划

P0 会话同步+规范阅读 → P1 现状梳理 → P2 克隆+上游调研 → P3 业界调研 → P4 对比推荐 → P5 报告撰写 → P6 验收+收尾立档。全程串行、本仓库只读(除 P5 报告与收尾回写)。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| P0 | 会话同步+规范阅读 | ✅ | 同步 003c7ce7; doc-forms/webui 口径确认 |
| P1 | 本项目现状梳理 | ✅ | 笔记 01-local-status.md(陡因定位) |
| P2 | 克隆+上游口径调研 | ✅ | `D:\Projects\Else\qBittorrent`(master@8182ae071) + `libtorrent`(RC_2_1@53acefea9) + 笔记 02 |
| P3 | 业界实践调研 | ✅ | 笔记 03-industry-practices.md(每条带来源链接) |
| P4 | 方案对比与推荐 | ✅ | 笔记 04-options-comparison.md; 推荐 B 区间平均 |
| P5 | HTML 调查报告 | ✅ | reports/26-10-07-2031-report-qb-traffic-rate-basis.html(7 章 52KB) |
| P6 | 验收+收尾立档 | ✅ | 本档案 + 基线切片(数字见切片) |

## 进度日志

- **2026-10-07 20:31** 报告落盘: 单文件 dark 主题 7 章 52KB, 5 个 doc-* meta 齐全, 无外部资源依赖; kb.index 登记入 reports/_index。
- **2026-10-07 20:46** 收尾: 立档(阈值命中第 4 条: 产出 reports/ HTML 制品), 报告 doc-refs 补本档案反向引用; test.full 实测数字与基线切片见 `testing/baselines/`(不在此手抄)。
- **2026-10-07 20:57** ship.commit 核 ref 假红(packed-refs 陈旧, 坑档 `pitfalls/git/refs.md` 该条复发 +1): 备份 .git 后 `git pack-refs --all` 处置; 提交 c1bacf2c 本身落稳, 处置后补 ship.push。
