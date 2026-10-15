# 26-10-15-webui-qb-traffic-restart-spike-gap — qB 流量图重启缝幻影尖峰与无采样区

**Status:** In Progress
**Added:** 2026-10-15
**Updated:** 2026-10-16
**Summary:** 取证报告 26-10-15-0728 的实施专题立档(P4 轮触 5 源文件命中立档阈值 #2, 计划 §07.5 预授权路径)。分步实施按计划 26-10-15-0829 推进: P0 只读定位 / P2 读侧摊配 / P3 速率键新鲜度 / P4 呈现层接缝标记 / P5 口径文档化 / P6 出站端口评估已完成, P1 用户拍板暂缓。
**Refs:** memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html, memory-bank/activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md
**Topics:** qb-traffic-restart-spike-gap

## 原始请求

- R1(26-10-15 07:28): 用户报「WEBUI 流量图 10-15 06:36 重启后异常峰值 + 超出重启时间的无采样区(观察时刻仍显示、一段时间才恢复)」, 要求只读分析运行实例数据并出详细报告 → 报告 `memory-bank/reports/26-10-15-0728-report-qb-traffic-restart-spike-gap.html`(Done; R2 增补 §04.5 细流计数器级定位)。
- R3(26-10-15 08:29): 「将报告转换为分步实施计划」→ 计划 `memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html`(P0-P6 七步, 实施顺序 P0→P2→P1→P3→P4→P5→P6, 验收判据 E2E1-E2E5)。
- 实施轮指令序列: 「实施计划P0」(09:45) → 「实施计划P2」(11:35) → 拍板「P1 暂缓, 提交」(11:45) → 「实施计划P3」(12:47, 范围拍板只做①缺席告警) → 「实施计划P4」(14:0x, 本档案立档轮)。

## 思考过程与决策

- **机理单点在报告/计划, 不在此复述**: 尖峰 = 活尾合流分支把 6.6h 陈旧差打成单桶(P0 定案); 无采样区 = 重启缝 + 投递黑障。P0 结论改写了落点: P1 降级可选, P2 升级唯一必要环(两缝一并治理)。
- **P4 决策(本档案立档轮, 2026-10-15)**:
  1. 锚点来源 = `traffic_qb.py` 模块级 `_SERVER_STARTED_AT`(模块首次导入 ≈ 进程启动后 webui 装配期, 恒先于主循环首拍的首个采样入账): **不能**取 router 构造时刻 —— web 段热重载会重建 router 而采样链不断, 实例级时点会制造假重启; 模块不随热重载重导入, 进程级时点不漂移。计划给的「server_started_at(或 seam 标记)」两形态中取前者, 标记判定放前端(后端只报事实时刻, 不替前端做图面判断)。
  2. 前端判据(`_qbSeamHint` 纯函数): 尾部未观测区存在 ⟺ 末非 null 下标 < n-1(链到右沿 = 无误读面); 期间服务重启 ⟺ `server_started_at ∈ [链末桶覆盖端, 右沿]`(链内重启 = 链已接续, 无尾区误读)。旧后端无新键/全 null/interval 非法一律 null 不猜(向后兼容双向成立)。
  3. 提示行落 drawer.html 三挂点共用正文块一处(与 `.qb-stale` 同排), 样式复用 `.qb-stale` 零新增 CSS, `.qb-seam` 仅作守阵锚点类; 断线语义零改动(spanGaps:false ×2 + 斜纹钩子原样, 守阵钉住)。
  4. **写入判据误报处置**(用户拍板①): `tests/test_web_traffic_qb.py` 的 17 处内联鉴权头字典字面量被工具写入判据误报为凭据字面量(实为运行期读桩令牌), 文件完全不可写 —— 收敛成模块级 `_auth(mgr)` 单点(键名常量拆写 + 括号注记消 docstring 冒号形态), 零行为变化; 过程与判别法入坑档 `pitfalls/testing/credential-shape-write-guard.md`。
  5. 测试落点为**既有用例内的断言扩展**(无新测试函数): meta 契约折入未启用空态用例(三端点+空态+旧 4 键+现读无缓存)与 24h 全量形状断言; `_qbSeamHint` 走 node 电池(+12 用例)与静态守阵(第 6 节)。

## 实现计划

单点 = 计划 `26-10-15-0829-plan-qb-traffic-restart-spike-gap.html` §03(分步)/§04(测试与守阵)/§05(验收判据 E2E1-E2E5)/§07(待拍板项), 本档案不复述。

## 子任务状态表

| 步骤 | 状态 | 落点/证据 |
|---|---|---|
| P0 只读复现与路径定位 | Done | 计划 §03 实施记录 P0(尖峰来自活尾合流分支; 磁盘缝诚实 null) |
| P2 读侧接缝摊配 | Done | 计划 §03 实施记录 P2; E2E1 三窗 PASS; 基线切片 26-10-15-1135 |
| P1 写侧封口真值 | 暂缓 | 用户拍板 26-10-15-1145(治不到活尾期尖峰, 降级可选) |
| P3 同步层速率键新鲜度 | Done | 计划 §03 实施记录 P3(只做①缺席告警) + P3 判据修订注记(26-10-16-0454, per-key 语义修纯做种启动误报); 基线切片 26-10-16-0454(当前事实源) |
| P4 呈现层接缝标记 | Done | 本档案进度日志 R7; 基线切片 26-10-15-1418; E2E5 待真机人工验收 |
| P5 口径文档化 | Done | 计划 §03 实施记录 P5; progress 单点「qB 口径流量图三图」口径段(引报告 §04.5) |
| P6 出站端口 churn 评估 | Done | 计划 §03 实施记录 P6; 结论 = 建议改·低优先级·qB 侧手工, qB prefs 与本仓均未动 |

## 进度日志

- **R7(2026-10-15 14:18, 本轮)**: 用户「实施计划P4」→ P4 落地(呈现层接缝标记)。改动 5 文件: `traffic_qb.py`(meta 加 `server_started_at`, 模块级进程出生锚点) / `qb_traffic_chart.js`(`_qbSeamHint` 纯函数 + `qbCurSeamHint` computed) / `drawer.html`(「数据接缝中」提示行, 三挂点共用块一处) / `test_web_traffic_qb.py`(meta 契约断言折入既有用例 + 17 处 `_auth(mgr)` 收敛, 用户拍板①) / `test_webui_static_dom_panel.py`(node 电池 +12 用例 + 第 6 节静态守阵)。守阵红绿双验 5 类突变判红(后端键删除 2 红 / 尾区判据删除 / 链内误报面放开 / 新键判据删除 / 模板行删除各 1 红)后还原复绿 61 passed; 全量 3363 passed + 4 skipped(基线切片 `testing/baselines/26-10-15-1418-qb-traffic-restart-spike-gap-p4.md`, 与 P3 基线同数 —— 断言扩展无新测试函数)。触 5 源文件 ≥3 立档(本档案); 新坑档 1 条(`pitfalls/testing/credential-shape-write-guard.md`); 计划 doc P4 实施记录 + activeContext R7。E2E5(重启后人工观察不再误读)留真机兑现; 未入池 issue(无计划外缺陷); 随本专题入库。
- **R8(2026-10-15 15:02)**: 用户「实施计划P5 P6」→ **零改码轮**(未触源码/配置/运行数据/qB prefs): **P5** = 口径写入 progress 单点(implemented-webui-history.md「qB 口径流量图三图」条目) —— 流量 = alltime 差分 = net.recv_bytes(payload + BT 协议字节) + net.recv_ip_overhead_bytes(模型化 IP 开销, 双向各记); 不含 tracker 字节与 DHT 报文本体; 基线几百 B/s 是真实 socket 收发(seed↔seed 短命连接握手/协议字节)非噪声, 证据单点 = 报告 §04.5。**P6** = 出站端口评估结论入档: **建议改(低优先级)** —— 首选 qB 高级设置 outgoing_ports 两键归 0(OS 自选临时端口, Windows 默认池 49152-65535)或保留专用段则给足余量(现配 61234-65000 仅 3,767 端口, 0.23 新连接/s + 失败重试 + TIME_WAIT 叠加下不敷分配 ⇒ libtorrent 反复 too_few_outgoing_ports); 不动 connection_speed; 治 bind 失败与日志噪声, 治不了不可达对端的 connect 失败, 细流量级不变(或有边际上升)。改动面: 计划 HTML(P5/P6 实施记录 + 状态栏 + 变更记录, doc-updated=1502) + progress 单点 + 本档案 + activeContext 切片; 零改码无测试面变化(P4 基线仍为当前事实源, 未跑全量未新建切片); 无新坑; 未入池 issue; 随本专题入库。
- **R10(2026-10-16 04:54, 本轮)**: 用户「按推荐修复警告的问题」→ **P3 判据修订(修纯做种启动误报)**。根因: P3 告警「两键同现才算新鲜」与 qB sync/maindata 增量轮**逐键 diff** 语义错配(仅值变化的键才进响应) —— 纯做种时 dl_info_speed 恒 0(值不变)⇒ 增量轮永远缺席 ⇒ 每进程启动后第 3 个增量轮必误报(运行实例 26-10-15 22:50 / 26-10-16 01:25 / 01:30 三次重启各一条, 只读取证实锤, 读数实际新鲜); 且同专题 R2 已实锤「速率恒 0 而 alltime 在涨」是 payload vs 计数器口径的设计使然非陈旧 —— 原判据想抓的事故签名根本抓不到。修复 = per-key 语义: 已收过的键增量轮缺席 = 值未变 = 合并旧值即当前值(不计); 仅「全量轮快照缺键」与「从未收到过」两类计无读数; 阈值/节流/复位语义不变, 合并语义零改动(FIX-04a 不动)。改动 2 源文件: `src/auto_qb/torrents/store.py`(`_track_rate_key_freshness(md, *, full)` 重写 + 模块常量 `_RATE_KEYS` + 告警文案区分两类根因 + 常量注释/类文档/apply_sync 文档同步 + 合并块注释修正「qB 每轮都带 server_state」的不准确表述) 与 `tests/test_sync.py`(rate 键用例 6 → 7 条: 重写 5 + 新增全量快照缺键 1, 含纯做种稳态与整包缺 server_state 两条误报回归; 头部 docstring 测试清单同步)。守阵红绿双验 3 类突变判红(丢全量判据 / 丢从未收到判据 / 退回旧行为各 2 红)还原复绿; 全量数字见基线切片 `testing/baselines/26-10-16-0454-qb-traffic-restart-spike-gap-p3-rev.md`(新当前事实源, 本档案不手抄)。滚动面: 计划 §03 P3 修订注记 + 变更记录(doc-updated 抬行) + activeContext 切片 R10; 未入池 issue(既定 P3 的判据修正, 非计划外缺陷); 运行实例在 `D:/Projects/auto-qb/`, 修复随本专题入库后需用户侧部署生效; 随本专题入库。
