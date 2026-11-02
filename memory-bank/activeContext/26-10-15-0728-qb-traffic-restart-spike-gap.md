# qb-traffic-restart-spike-gap — WEBUI 流量图重启尖峰/无采样区取证

> 摘要: 用户报「WEBUI 流量图 10-15 06:36 重启后异常峰值 + 超出重启时间的无采样区」。取证结论: ①尖峰 = qB alltime 在 payload 速率恒 0 时持续增长(seed↔seed 短命连接握手字节, ~500 B/s 双向, 不落种子 payload), 采样器按 (0,0) 开 z 游程, z 快照冻结 6.6h(+15.3MB dl/+16.5MB up)且磁盘零痕迹; 重启后首样读入新鲜 totals, 读侧 delta/w 把整段陈旧差打进 06:36:08 单桶(2s 桶 6.9MB/s, 约 11,000×)。②无采样区 = 重启缝 ~10s(2s 视图 3 个 null 桶)+ 投递黑障(旧 WEBUI 06:36:01.5 死→新服务 06:36:08.1 起→~06:36:10 首活尾响应), null 区视觉延伸到观察时刻。细流来源与排除项见报告 §04.5; 分步实施 P0–P6 与验收 E2E1–E5 在计划 0829, agg 归属形态 D 在计划 1509。实施面已全部收口, 唯一未兑现 = E2E5 真机人工验收; 本切片只留结论、证据坐标与轮次索引, 明细在档案/计划/报告。
> 最后活动: 2026-10-17 04:44

**Refs:** memory-bank/reports/26-10-15-0728-report-qb-traffic-restart-spike-gap.html, memory-bank/reports/26-10-07-2031-report-qb-traffic-rate-basis.html, memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html, memory-bank/testing/baselines/attachments/26-10-15-0845-qb-traffic-restart-spike-gap-plan.md, memory-bank/testing/baselines/attachments/26-10-15-1135-qb-traffic-restart-spike-gap-p2.md, memory-bank/testing/baselines/attachments/26-10-15-1247-qb-traffic-restart-spike-gap-p3.md, memory-bank/testing/baselines/attachments/26-10-15-1418-qb-traffic-restart-spike-gap-p4.md, memory-bank/testing/baselines/attachments/26-10-16-0454-qb-traffic-restart-spike-gap-p3-rev.md, memory-bank/testing/baselines/attachments/26-10-16-1057-qb-traffic-seam-fixes.md, memory-bank/testing/baselines/attachments/26-10-16-1126-qb-traffic-seam-fixes-r2.md, memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md, memory-bank/issues/26-10-16-0020-bug-agg-hour-totals-frozen-run.html, memory-bank/issues/26-10-16-0020-question-agg-rate-lane-invisible-bytes.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-short-gap-spike.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-hint-missed-after-first-sample.html, memory-bank/testing/baselines/attachments/26-10-16-1204-qb-traffic-restart-spike-gap-p4-rev.md, memory-bank/plans/26-10-16-1509-plan-agg-hour-totals-attribution.html, memory-bank/testing/baselines/attachments/26-10-16-1628-qb-traffic-restart-spike-gap-agg-attribution-d.md, memory-bank/pitfalls/backend/traffic-row-format-extension.md

**R1(2026-10-15 07:28):** 用户报故障, 要求只读取证并出报告 → `reports/26-10-15-0728-report-qb-traffic-restart-spike-gap.html`(Done)。
**R2(2026-10-15 08:08):** 用户要求定位细流 qB 侧来源并更新报告 → 就地增补 §04.5(计数器级定位, 未新建文件)。
**R3(2026-10-15 08:29):** 报告转分步计划 → `plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html`(P0–P6, E2E1–E5)。
**R4(2026-10-15 09:45):** 实施 P0 → 尖峰走活尾合流分支(`core/traffic_grid.py:412-415` 显式跳过真空判定), 非链断点; 生产仍处开放 z 游程(天文件 mtime 06:36:01、速率恒 0)。P1 降级可选, P2 升级唯一必要环。
**R5(2026-10-15 11:35):** 实施 P2(读侧接缝摊配 + 观测缝 > 60s 洞判 + 24h 回看) → E2E1 三窗 PASS, 接缝桶 (1068, 1526) B/s 逐位一致; 基线 26-10-15-1135。
**R6(2026-10-15 12:47):** 实施 P3(同步层速率键新鲜度告警, 范围拍板只做①缺席告警) → 基线 26-10-15-1247。
**R7(2026-10-15 14:22):** 实施 P4(meta `server_started_at` + `_qbSeamHint` + drawer「数据接缝中」提示) → 触 5 源文件立档; 基线 26-10-15-1418。
**R8(2026-10-15 15:02):** P5/P6 收口(零改码): 口径入 progress 单点; 端口建议 qB 侧手工归 0/给足余量(低优先级)。
**R9(2026-10-16 00:20):** 评估 P1 收益 → 四形态全不实施(1A 否决/1B 不可行/z 封口被用户否决); 派生两条 agg issue 入池。
**R10(2026-10-16 04:54):** P3 判据修订(per-key 语义, 修纯做种启动误报) → 基线 26-10-16-0454(当前事实源)。
**R11(2026-10-16 10:57):** 修复两条 26-10-16-0954 issue(短缝尖峰/断链首桶孤点) → 基线 26-10-16-1057。
**R12(2026-10-16 11:26):** 残余边界收口(活尾与磁盘同判块间真空) → 基线 26-10-16-1126。
**R13(2026-10-16 12:04):** 修 P4 接缝提示漏判(左端放宽一桶宽) → 基线 26-10-16-1204。
**R14(2026-10-16 15:09):** 认领 agg totals 归属错位(复验仍复现)并出三形态对照件 → `plans/26-10-16-1509-plan-agg-hour-totals-attribution.html`。
**R15(2026-10-16 16:28):** 用户拍板形态 D 落地(z 行扩末端快照对 + 两路共用摊配, raw 面零触碰) → issue Done; 基线 26-10-16-1628。
**R16(2026-10-17 04:44):** 文档收口: 计划 0829 → Done, §07 五项拍板全闭, 档案 Status → Done; 唯一未兑现 E2E5。

## 正在进行

- 计划与档案均 Done(R16); 唯一未兑现 = E2E5 真机人工验收(判据链 + 实测帧回归守阵已就位, 待真实重启补记)。
- 未决: `issues/26-10-16-0020-question-agg-rate-lane-invisible-bytes`(agg rate lane 口径)= Open / 未认领, 待拍板; 不影响 raw 面。
- 观测面: 细流仍在累积, 下次重启同型尖峰属设计口径; P2 后为夜均平线 + 观测缝 null, P4 后另有「数据接缝中」提示。

## 本专题关键坐标

- 交付物: 报告 0728(doc-status Done) / 计划 0829(Done) / 派生计划 1509(Done) / 档案 `tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md`(Done)。
- 细流实体: `alltime_dl = net.recv_bytes + net.recv_ip_overhead_bytes`(qB `sessionimpl.cpp:6571/6625`); WebUI 只暴露 payload 速率(`synccontroller.cpp:164-167`); IP 开销量化双向各记(`libtorrent session_impl.cpp:3466-3483`); seed↔seed 断开(`bt_peer_connection.cpp:2123-2129` / `peer_connection.cpp:2344-2350`)。DHT/PeX、uTP 报文开销、tracker 字节均已排除。
- 本仓读侧: `core/traffic_grid.py:412-415`(活尾合流/真空判定) / `traffic_sample_mod.py:602-605`(z/r 判据=速率字段) / `traffic_store.py:19-20`(z 行快照语义) / `torrents/store.py:184-186`(server_state 合并 + 新鲜度挂载) / `traffic_qb.py`(活尾装配, `server_started_at`) / `qb_traffic_chart.js`(轮询节拍 + `_qbSeamHint`)。
- 运行实例快照(2026-10-15 07:47–08:05, 只读): qB v5.2.3 / BT 监听 61323 / WebUI 16585; `dht=pex=lsd=False`、`bittorrent_protocol=0`、`encryption=1`、`outgoing_ports 61234–65000`、`connection_speed=30`; 180 种子 = 120 stalledUP / 36 stoppedDL / 24 missingFiles。
- 坑档: `pitfalls/ops/console-encoding.md`(中文表头探针静默读 0) / `pitfalls/backend/traffic-row-format-extension.md`(z 行扩列位次与回滚) / `pitfalls/web-ui/bucket-granularity-boundary.md`(桶粒度边界) / `pitfalls/testing/credential-shape-write-guard.md`(不可写文件收敛) / `pitfalls/testing/no-uv-fallback.md`。
- 复跑探针(scratch 未入库): `.openclaw/tmp/probe_p0_seam_path.py` / `e2e1_replay_p2.py` / `redverify_p2.py` / `probe_tail_vacuum.py` / `probe1.js`; 报告 §08 另有五条只读复跑清单。
