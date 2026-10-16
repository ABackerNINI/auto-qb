# 26-10-15-webui-qb-traffic-restart-spike-gap — qB 流量图重启缝幻影尖峰与无采样区

**Status:** In Progress
**Added:** 2026-10-15
**Updated:** 2026-10-16
**Summary:** 取证报告 26-10-15-0728 的实施专题立档(P4 轮触 5 源文件命中立档阈值 #2, 计划 §07.5 预授权路径)。分步实施按计划 26-10-15-0829 推进: P0 只读定位 / P2 读侧摊配 / P3 速率键新鲜度 / P4 呈现层接缝标记 / P5 口径文档化 / P6 出站端口评估已完成, P1 用户拍板暂缓; 26-10-16 追加计划外缺陷修复轮(两条 26-10-16-0954 issue: 短缝摊配与断链首桶 null 语义); P4 判据左端已按 issue 26-10-16-0954(seam-hint-missed)修订(左端放宽一桶宽, 修「重启后首采即链末桶」形态漏判, 见 R13)。
**Refs:** memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html, memory-bank/activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md, memory-bank/issues/26-10-16-0954-bug-traffic-seam-short-gap-spike.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-hint-missed-after-first-sample.html, memory-bank/testing/baselines/26-10-16-1204-qb-traffic-restart-spike-gap-p4-rev.md
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
| P4 呈现层接缝标记 | Done | 本档案进度日志 R7; 基线切片 26-10-15-1418; **判据左端修订 26-10-16**(issue 26-10-16-0954, 见 R13; 基线切片 26-10-16-1204); E2E5 待真机人工验收 |
| P5 口径文档化 | Done | 计划 §03 实施记录 P5; progress 单点「qB 口径流量图三图」口径段(引报告 §04.5) |
| P6 出站端口 churn 评估 | Done | 计划 §03 实施记录 P6; 结论 = 建议改·低优先级·qB 侧手工, qB prefs 与本仓均未动 |
| 计划外缺陷修复轮(26-10-16-0954 两件) | Done | 本档案进度日志 R11 + R12(残余边界补修) + 计划 §03「实施记录 · 计划外缺陷修复轮」; 基线切片 26-10-16-1057 / 26-10-16-1126 |

## 进度日志

- **R7(2026-10-15 14:18, 本轮)**: 用户「实施计划P4」→ P4 落地(呈现层接缝标记)。改动 5 文件: `traffic_qb.py`(meta 加 `server_started_at`, 模块级进程出生锚点) / `qb_traffic_chart.js`(`_qbSeamHint` 纯函数 + `qbCurSeamHint` computed) / `drawer.html`(「数据接缝中」提示行, 三挂点共用块一处) / `test_web_traffic_qb.py`(meta 契约断言折入既有用例 + 17 处 `_auth(mgr)` 收敛, 用户拍板①) / `test_webui_static_dom_panel.py`(node 电池 +12 用例 + 第 6 节静态守阵)。守阵红绿双验 5 类突变判红(后端键删除 2 红 / 尾区判据删除 / 链内误报面放开 / 新键判据删除 / 模板行删除各 1 红)后还原复绿 61 passed; 全量 3363 passed + 4 skipped(基线切片 `testing/baselines/26-10-15-1418-qb-traffic-restart-spike-gap-p4.md`, 与 P3 基线同数 —— 断言扩展无新测试函数)。触 5 源文件 ≥3 立档(本档案); 新坑档 1 条(`pitfalls/testing/credential-shape-write-guard.md`); 计划 doc P4 实施记录 + activeContext R7。E2E5(重启后人工观察不再误读)留真机兑现; 未入池 issue(无计划外缺陷); 随本专题入库。
- **R8(2026-10-15 15:02)**: 用户「实施计划P5 P6」→ **零改码轮**(未触源码/配置/运行数据/qB prefs): **P5** = 口径写入 progress 单点(implemented-webui-history.md「qB 口径流量图三图」条目) —— 流量 = alltime 差分 = net.recv_bytes(payload + BT 协议字节) + net.recv_ip_overhead_bytes(模型化 IP 开销, 双向各记); 不含 tracker 字节与 DHT 报文本体; 基线几百 B/s 是真实 socket 收发(seed↔seed 短命连接握手/协议字节)非噪声, 证据单点 = 报告 §04.5。**P6** = 出站端口评估结论入档: **建议改(低优先级)** —— 首选 qB 高级设置 outgoing_ports 两键归 0(OS 自选临时端口, Windows 默认池 49152-65535)或保留专用段则给足余量(现配 61234-65000 仅 3,767 端口, 0.23 新连接/s + 失败重试 + TIME_WAIT 叠加下不敷分配 ⇒ libtorrent 反复 too_few_outgoing_ports); 不动 connection_speed; 治 bind 失败与日志噪声, 治不了不可达对端的 connect 失败, 细流量级不变(或有边际上升)。改动面: 计划 HTML(P5/P6 实施记录 + 状态栏 + 变更记录, doc-updated=1502) + progress 单点 + 本档案 + activeContext 切片; 零改码无测试面变化(P4 基线仍为当前事实源, 未跑全量未新建切片); 无新坑; 未入池 issue; 随本专题入库。
- **R10(2026-10-16 04:54)**: 用户「按推荐修复警告的问题」→ **P3 判据修订(修纯做种启动误报)**。根因: P3 告警「两键同现才算新鲜」与 qB sync/maindata 增量轮**逐键 diff** 语义错配(仅值变化的键才进响应) —— 纯做种时 dl_info_speed 恒 0(值不变)⇒ 增量轮永远缺席 ⇒ 每进程启动后第 3 个增量轮必误报(运行实例 26-10-15 22:50 / 26-10-16 01:25 / 01:30 三次重启各一条, 只读取证实锤, 读数实际新鲜); 且同专题 R2 已实锤「速率恒 0 而 alltime 在涨」是 payload vs 计数器口径的设计使然非陈旧 —— 原判据想抓的事故签名根本抓不到。修复 = per-key 语义: 已收过的键增量轮缺席 = 值未变 = 合并旧值即当前值(不计); 仅「全量轮快照缺键」与「从未收到过」两类计无读数; 阈值/节流/复位语义不变, 合并语义零改动(FIX-04a 不动)。改动 2 源文件: `src/auto_qb/torrents/store.py`(`_track_rate_key_freshness(md, *, full)` 重写 + 模块常量 `_RATE_KEYS` + 告警文案区分两类根因 + 常量注释/类文档/apply_sync 文档同步 + 合并块注释修正「qB 每轮都带 server_state」的不准确表述) 与 `tests/test_sync.py`(rate 键用例 6 → 7 条: 重写 5 + 新增全量快照缺键 1, 含纯做种稳态与整包缺 server_state 两条误报回归; 头部 docstring 测试清单同步)。守阵红绿双验 3 类突变判红(丢全量判据 / 丢从未收到判据 / 退回旧行为各 2 红)还原复绿; 全量数字见基线切片 `testing/baselines/26-10-16-0454-qb-traffic-restart-spike-gap-p3-rev.md`(新当前事实源, 本档案不手抄)。滚动面: 计划 §03 P3 修订注记 + 变更记录(doc-updated 抬行) + activeContext 切片 R10; 未入池 issue(既定 P3 的判据修正, 非计划外缺陷); 运行实例在 `D:/Projects/auto-qb/`, 修复随本专题入库后需用户侧部署生效; 随本专题入库。
- **R11(2026-10-16 10:57, 本轮)**: 用户「认领并修复: 26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker, 26-10-16-0954-bug-traffic-seam-short-gap-spike」→ **计划外缺陷修复轮**(两件均属 P2 同一决策面的边界形态收口)。开工同步快进 `60d207d7→2f56cc4d`。根因双侧: ①短缝尖峰 = 摊配判据只有「变化点跨度 > max(2×桶宽, 60s)」一条, 而洞判定用观测覆盖缝, 两门槛方向相反而短缝两头落空 —— 活尾路径(无真空标记, `marked=False`)把整段接缝差按自身桶宽打入接收桶(证据行几何 2,496,825 B / 2s 桶 = 1,248,412 B/s, 8.5×), 磁盘路径(有标记、未触发摊配)则 delta=None 断链——同一桶刷盘前后取值不同; ②孤点 = 洞后首桶 `rate=None` 但 totals 有效 ⇒ D4 豁免出 0/0 非 null ⇒ 前端孤点标记 + 峰值 0 把值域塌到 [0,1] + 把无采样斜纹区一分为二。**改动 3 文件**: `core/traffic_grid.py`(摊配判据三形态: 本点前有 null 标记 / 未覆盖段 `span > cov` / 陈旧长跨度; 基准 `step_w = step × cov // span`(未覆盖秒不归因), 份额按累计比例取整不堆接收桶; `v4_grid_obs` 断链首桶该向出 None 而快照照记; `BucketObs` 速率放宽 Optional; `group_rate_points` 有观测而全成员该向皆未知出 null) + `tests/test_traffic_grid.py`(新增 2 守阵 + 6 条按新口径重钉) + `tests/test_web_traffic_qb.py`(端点面 4 条期望同步)。**验证**: 只读探针复现两件几何(短缝 8.5×→1.00×, 磁盘/活尾两路径同值; 洞后桶 `BucketObs(None, None, 快照)` + `rate_points` null + 次桶 delta 照旧; 次记录桶 up=122,818 与 issue 证据行「刷盘后变平线」吻合 —— 合成几何与运行实例同构); 红绿双验 4 类突变判红(断链桶回 0 / 摘新判据 / 基准不缩放 / 组未知判据回 0 → 1/3/6/1 红)还原复绿; 全量数字见基线切片 `testing/baselines/26-10-16-1057-qb-traffic-seam-fixes.md`(本档案不手抄)。滚动面: 两 issue 状态 → Done(复验 + 修复后补充已填) + 计划 §03 修复记录 + §07 #2 不变声明 + progress 口径单点补注 + 坑档 traffic-window-edge-floor 状态更新; 未入池新 issue(两件均本次修复); 真实运行实例的天文件在另一 clone, 未读(跨 clone 禁止), 复现走合成几何 + 证据行数值; 随本专题入库。新增坑档 `pitfalls/testing/no-uv-fallback.md`(本 clone 工具 shell 无 uv 且无 R: 盘 ⇒ 包内 `test.*` 第一行即失败; 兜底配方 = venv python + C 盘 TMPDIR + 仓库外 COVERAGE_FILE + 全新 --basetemp)。
- **R12(2026-10-16 11:26, 本轮)**: 用户「修复残余边界」→ R11 自报的残余形态收口。根因: `v4_series_points` 的活尾组不做块间真空判定(注释假设「磁盘链末槽与活尾首槽之间是一次标称采样间隔」—— 只对同块续链成立, `head_pending` 的活尾首槽是块首记录 `B.start`, 重启后可隔一整段停机) ⇒ 覆盖连续(`span == cov`)且带块界真空标记的缝在两条路径上取值不同: 磁盘走摊配回收(span <= 60s 时甚至走 `elif marked` 丢弃成 None), 活尾走接收桶单桶 `delta/w`。改动 1 源文件: `core/traffic_grid.py`(活尾组与磁盘块**同判块间真空**, 同一条判据; 模块头/函数 docstring 同步)+ `tests/test_traffic_grid.py`(新增 1 条守阵 `test_v4_seam_covered_span_mark_two_paths_agree` + 活尾相关 3 条改钉「同标记」口径 + 头部清单同步)。**验证**: 只读探针(scratch `.openclaw/tmp/probe_tail_vacuum.py`)实测残余几何两路径逐位一致(含同一位标记)、既有场景数值不变(仅多一个标记点); 红绿双验 1 类突变(摘除活尾真空判定)判 4 红还原复绿; 全量数字见基线切片 `testing/baselines/26-10-16-1126-qb-traffic-seam-fixes-r2.md`。滚动面: issue short-gap-spike 补记残余边界修(状态维持 Done) + 计划 §03 补修段 + 变更记录 + activeContext R12 + 坑档 traffic-window-edge-floor 再补一条(「稳态才成立」的假设不得当不变式入守阵); 同轮把 S6 的旧钉「活尾合流不产 null 标记」改钉为「同判同标记」(旧钉护住的是缺陷面); 未入池新 issue; 随本专题入库。
- **R13(2026-10-16 12:04, 本轮)**: 用户「认领并修复 memory-bank/issues/26-10-16-0954-bug-traffic-seam-hint-missed-after-first-sample.html」→ **P4 判据左端修订**(呈现层判据漏判形态修复, 未动读侧)。复验(11:44, 只读探针 `.openclaw/tmp/probe1.js`, 未入库): 实测帧重建(1m 窗 interval=2s, 全窗唯一非 null = 首采桶 04:45:02, 重启 04:45:01)代入旧判据恒 null(零提示, 现象复现); 锚点零漂移(`_qbSeamHint` 定义在 :288 / 消费点 `qbCurSeamHint` 在 :416-419)。修法(11:45): `_qbSeamHint` 左端从「链末桶覆盖端 `t+interval`」放宽到「**链末桶前一桶起点 `t-interval`**」(两端含) —— 原口径的隐含前提「链末桶晚于重启时刻 ⟹ 链已接续、无误读面」在「重启后首采已入账、随后立即进入开放零游程」形态下不成立(首采恒落在重启后 <= 一个 main_tick, 总归进链末桶, 但尾区仍在); 「链在重启处断」与「重启后首个观测桶即链末」在桶粒度上不可分, 故放宽恰好一桶宽; 反方向(链末桶起点晚于重启 + 1 桶宽以上)仍判「链确已接续」不提示。改动 3 文件: `qb_traffic_chart.js`(定义行 + 比较行 + docstring/computed 注释) / `drawer.html`(模板注释口径同步, 提示行本体零改动) / `test_webui_static_dom_panel.py`(电池 `_qbSeamHint` 11→17 条含实测帧回归 + 第 6 节左端整行活性锚 + 两处 docstring)。红绿双验(11:46): 退回旧左端 4 红 / 去掉左端 3 红, 还原复绿 50/50(突变只写副本, 真源码字节恒等自证); 全量数字见基线切片 `testing/baselines/26-10-16-1204-qb-traffic-restart-spike-gap-p4-rev.md`(新当前事实源, 本档案不手抄; 切片含「语句列 -199」口径注记 —— 已核 git 内容一致 + 工具链一致 + 三种跑法逐位一致, 差异不在改动面、未定位成因留档)。滚动面: 计划 §03 P4 判据修订注记 + 变更记录(doc-updated 抬行); 坑档新 `pitfalls/web-ui/bucket-granularity-boundary.md` + `pitfalls/testing/sandbox-tool-cache.md` 变体(uv 托管命令在 LOCALAPPDATA 空时把缓存落 CWD); issue Open→Done + 认领链双向。范围守恒: 「开放游程为何读侧不可见」按 issue 认定留独立件未动; 随本专题入库。
