# 26-10-07-webui-qb-traffic-rate-basis — 流量图速率口径调研(瞬时 · 区间平均 · 移动平均)

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-08
**Summary:** 流量图「太陡」口径调研完成: 陡因=raw 窗 1 桶 1 瞬时样本+前端零平滑; 裁决数据口径采用区间平均(计数器差分 Δbytes/Δt)、否决移动平均(平滑归展示层); 落地为纯读侧接线(traffic_grid.py 桶点变换 + traffic_qb.py 端点), 零存储/state_file/配置改动; 报告 26-10-07-2031; 实施计划 26-10-07-2127 的 S1-S4 已全部实施(读侧区间平均 + 三端点接线 + raw 桶数上限 MAX_RAW_BUCKETS=2880; 万桶级治理入实施, 采样间隔演进 D6 仅入计划留后续切片)。
**Topics:** qb-traffic-rate-basis

**Refs:** memory-bank/reports/26-10-07-2031-report-qb-traffic-rate-basis.html,memory-bank/activeContext/26-10-07-2046-qb-traffic-rate-basis.md,memory-bank/testing/baselines/26-10-07-2053-webui-qb-traffic-rate-basis.md,memory-bank/testing/baselines/26-10-08-0142-webui-qb-traffic-rate-basis-impl.md,memory-bank/plans/26-10-07-2127-plan-qb-traffic-rate-basis.html

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

第二阶段(实施, 计划 26-10-07-2127): S1 读侧差分变换核心 → S2 三端点接线+窗首种子 → S3 raw 桶数上限 → S4 收口。串行执行, 每步 test.quick 全绿再进下一步; 纯读侧, 无数据迁移(回滚 = revert 读侧提交)。

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
| S1 | 读侧差分变换 `v4_rate_from_totals` + `v4_grid_obs` D4 豁免 | ✅ | core/traffic_grid.py; test_traffic_grid.py +6(先红后绿) |
| S2 | 三端点接线 + 窗首种子(D3) | ✅ | webui/server/traffic_qb.py 两处; test_web.py 既有 6 改形 + 新增 3 |
| S3 | raw 桶数上限 `MAX_RAW_BUCKETS=2880` | ✅ | core/traffic_grid.py 常量 + build_grid 一式; test_traffic_grid.py +3 + 既有 1 改形 |
| S4 | 收口: 全量测试 + 基线 + 立档 + 回写 | ✅ | test.full **2769+4 / 99%**; 基线 26-10-08-0142; 档案/切片/roadmap/keys.md 回写 |

## 进度日志

- **2026-10-07 20:31** 报告落盘: 单文件 dark 主题 7 章 52KB, 5 个 doc-* meta 齐全, 无外部资源依赖; kb.index 登记入 reports/_index。
- **2026-10-07 20:46** 收尾: 立档(阈值命中第 4 条: 产出 reports/ HTML 制品), 报告 doc-refs 补本档案反向引用; test.full 实测数字与基线切片见 `testing/baselines/`(不在此手抄)。
- **2026-10-07 20:57** ship.commit 核 ref 假红(packed-refs 陈旧, 坑档 `pitfalls/git/refs.md` 该条复发 +1): 备份 .git 后 `git pack-refs --all` 处置; 提交 c1bacf2c 本身落稳, 处置后补 ship.push。
- **2026-10-07 21:51** 报告转化实施计划 [26-10-07-2127](../plans/26-10-07-2127-plan-qb-traffic-rate-basis.html)(21:27 建, 21:39 按用户澄清修订): 实施步骤 S1 读侧差分变换核心 → S2 三端点接线+窗首种子 → S3 raw 窗桶数上限 MAX_RAW_BUCKETS=2880 → S4 收口; 万桶级根因=生产 config 1.5S 采样(24h 窗 57600 桶), 成熟方案对比采用时间桶加宽(RRDtool AVERAGE/qB Averager 同型); 采样间隔两项(默认 1× main_tick、仅能按倍数设置)按用户拍板**仅写入计划**(D6 留后续切片, 实施前依赖桶数上限先行)。本轮仅交付计划文档, 零代码更改; 拆解失误(括注适用范围漏读)入坑档 `pitfalls/kb/scope-qualifier-parenthetical.md`。
- **2026-10-07 22:00** 计划提交 `ed4831ce` 落稳但 ship.commit 核 ref 假红(packed-refs 陈旧, `pitfalls/git/refs.md` 该条复发 +1 至 4): format-patch 留底 + `git pack-refs --all` + verify-ref 一致后 ship.push 推送成功; 复发实录随补笔提交入库。
- **2026-10-07 22:5x** S1 实施(用户指令「实施计划S1」): `core/traffic_grid.py` 新增纯函数 `v4_rate_from_totals`(桶点级逐点重写 rate = delta/w, 差分边界全套复用 `v4_totals_points`; totals/w 原样保留; null 点透传; totals 链推进独立于 rate 可派) + `v4_grid_obs` D4 豁免(rate=None 但 totals 有效的点只更新覆盖末端与快照链, rate 权重逐向记 0); 测试 +6(先红后绿); 接线点未动, 调用面行为零变化。test.quick 2763+4。提交 `4ab844a6`。
- **2026-10-07 23:45** S2 实施(用户指令「实施计划S2」): `webui/server/traffic_qb.py` 两处 raw 段接线(`read_window`/`v4_series_points` 的 t0 外扩 `seed_t0 = grid.t0 - grid.interval` → `v4_rate_from_totals` → `v4_grid_obs`); test_web.py 既有 6 用例按新口径改形 + 新增 3。test.quick 2766+4。提交 `b49b645e`。**发现 D3 边界缺口**: 停机落在 `(seed_t0-1, seed_t0)` 带且恢复在窗内时真空 null 点被 t0 过滤丢弃, 离线字节误归恢复首桶(常见几何安全, 仅 1s/窗 边界带)。
- **2026-10-08 01:34** S3 实施(用户指令「实施计划S3」): `core/traffic_grid.py` 新增模块常量 `MAX_RAW_BUCKETS = 2880` + `build_grid` raw 桶宽改 `max(1, ceil(sample_interval), ceil(span/MAX_RAW_BUCKETS))`(30s 默认采样数学恒等零回归); test_traffic_grid.py +3(高频上限数学 / 30s 零回归 / S3×S2 种子外扩联动)+ 既有 `test_build_grid_fractional_interval_ceils_bucket_width` 由 24h 改 1m 窗。先红后绿(红验 2 红)。test.quick 2769+4。
- **2026-10-08 01:42** S4 收口(用户指令「继续S4, D3入池」): D3 缺口入池 [issues/26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html](../issues/26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html)(bug / standard, 状态 Open, 未认领); `commands run test.full` **2769 passed + 4 skipped / 99%**(16474 语句 / 165 未覆盖 / 5694 分支 / 149 partial), 新建基线切片 [26-10-08-0142](../testing/baselines/26-10-08-0142-webui-qb-traffic-rate-basis-impl.md); 计划 [26-10-07-2127](../plans/26-10-07-2127-plan-qb-traffic-rate-basis.html) doc-status Open→Done; 回写 config-reference/keys.md(`sample_interval` 行补 raw 桶宽上限代码事实)+ roadmap.md(D6 采样间隔演进 + D3 issue 两条未决项迁入)+ activeContext 切片蒸馏; `kb.index` 重建。S1-S4 源码面零回归, 全绿。
