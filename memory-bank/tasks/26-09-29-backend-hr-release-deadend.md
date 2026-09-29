# 26-09-29-backend-hr-release-deadend — HR「放行签发即作废」与端点未监听(白等 180s)修复

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29
**Summary:** 用户实报 HR 站点接入热重载后种子仍显示「本地兜底已达标」+ 扩展连不上端点。真机 traceback 揪出三个同族缺陷: ①`service._freeze_terminal` 引用**未导入**的 `LANE_SATISFIED`(v3 重建起潜伏到真机才炸) ②冻结/观察期签发的放行记录**漏带锚点快照**, 判定侧把 `anchor_downloaded=0` 读成「downloaded 增长」⇒ 签发当刻作废 ③`HrRuntime.apply` L0 重建路径新建端点却**从不 `start()`**, 端口从未绑定。既有守阵 `test_terminal_vanish_writes_release` 从未走到目标分支(假绿灯) —— 已重塑并红验。**同会话追加一轮**: 端点未监听改为**快速失败**(不再白等 180s) + 观测期出口守阵同样加固。test.full 1745 passed / 4 skipped (91%)。
**Topics:** backend-partial-hr-verify

## 原始请求

用户实报(2026-09-29 18:00 前后日志): 「WEBUI 开启 HR 在线核实热重载后种子仍显示"本地兜底已达标", 实际在之前的版本已在线核实过, 且连接不上扩展, 扩展也连不上端点, 重启 qb 后才恢复连接, 重启后种子依然显示"本地", 还有报错」—— 附 traceback:
`hr/service.py::_freeze_terminal` → `NameError: name 'LANE_SATISFIED' is not defined`。

## 思考过程与决策

- **缺陷 1(未导入的名字)**: `LANE_SATISFIED` 自 v3 重建(`be83d61`)起只在 `service.py::_freeze_terminal` 被引用、**从未导入**(同处的 `LANE_EXEMPT` 导了、它漏了)。`get_errors`/import-all 守卫都抓不到 —— NameError 只在**真机走到那一行**时抛(教训: 未导入的名字潜伏在真机才走的分支里)。
- **缺陷 2(签发即作废, 用户症状的直接成因)**: 判据行 3「放行永续有效」靠 `verified` 记录里的锚点快照做「本机重下 ⇒ 提前作废」。三处签发点里 `_sign_releases` 带了快照, **`_freeze_terminal` / `_advance_observation` 没带**; `HrAnchor.drift_reason` 把 `anchor_downloaded=0` 读成「downloaded 增长」⇒ 那些记录**签发当刻**被判漂移 → 行 4 本地兜底 → WebUI 显示「本地兜底已达标」。计划 §7.2 明写 `verified` 记录「含锚点与 source」且旧记录「永续有效、迁移零过渡」, 故补: ①三处签发收敛到单点 `_release_record`(带快照) ②`HrVerified.has_anchor_snapshot` + `drift_reason` 早退 —— **无快照可比时不凭空判漂移**(治愈已落盘的旧记录)。
- **缺陷 3(端点从无到有)**: `HrRuntime.apply` L0 路径 `_build(keep_endpoint=True)`: `keep_endpoint` 只保证「已在监听的不重绑」, 而 `endpoint is None` 时新建的对象**没人 `start()`**(`HrWorker.start()` 不管端点)。上一轮同族修复只补了 worker ⇒ 热接入站点后线程在跑、端口从未绑定: 扩展连不上端点, 取数线程照样派发任务, 每页白等满 `request_timeout`(180s, 与日志中两次 180s 超时吻合)。
- **守阵假绿灯**: `test_terminal_vanish_writes_release` 的 B 行名称用 `"OTHER 21"`(粗配不上 ⇒ 不下载 ⇒ infohash 为空), 冻结的**内层「落放行记录」分支根本进不去**; 它断言的 `h21 in data.verified` 实际由第一波的「未列出」签发满足 —— 于是 `LANE_SATISFIED` 那行从未执行, 守阵一直是绿。判据: 把源码修复 stash 掉, 该守阵必须红(本轮实测: 修复前 4 条守阵全红且复现真机 NameError)。
- **决策**: 三处一次性修完(同一族缺陷, 用户症状一一对应); 不做范围外改造(如「端点未监听就不派发任务」的快速失败告警 —— 只是诊断增益, 未实施, 已记入报告)。`_freeze_terminal` 三元里 `SOURCE_EXEMPT` 分支实为死代码(`lane_states` 只含 A/B/C, D 档不翻页) —— 未动, 保持最小改动。

## 实现计划

1. `hr/service.py`: 补 `LANE_SATISFIED` 导入; 新增 `_release_record()` 单点(含锚点快照)并替换三处签发; `_WaveContext` 存 `anchors` 供冻结/观察期取快照。
2. `hr/model.py`: `HrVerified.has_anchor_snapshot`。
3. `hr/resolve.py`: `drift_reason` 对「无快照」早退(不凭空判漂移)。
4. `hr/runtime.py`: L0 重建路径补「端点从无到有则 `start()`」。
5. 测试: 重塑 `test_terminal_vanish_writes_release`(粗配同名 ⇒ 登记 infohash ⇒ 真走到落记录分支 + 断 source/快照)、新增 C 档同路径一例、`test_apply_starts_worker_when_never_started` 补端点断言、新增「站点全关后重新启用必须重新监听」、`test_hr_resolve` 补「无快照不作废」一例。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 定位三个缺陷(真机 traceback + 探针取证) | Done | 2026-09-29 本轮 |
| 修 service/model/resolve(缺陷 1+2) | Done | 签发单点 + 快照 + 无快照不作废 |
| 修 runtime 端点从无到有(缺陷 3) | Done | L0 路径补 `endpoint.start()` |
| 端点未监听快速失败(追加轮) | Done | `ChannelFetcher.listening_fn` + 门面接线; 下载路径让位元组补齐 |
| 守阵加固(追加轮) | Done | 观测期出口补「快照 + 判定生效」断言; 新增 2 条快速失败守阵并红验 |
| 守阵重塑 + 红验(4 条) | Done | 修复前全红且复现 NameError; 修复后全绿 |
| 收尾回写(归档/切片/坑档/基线) | Done | 基线 26-09-29-1821; 坑档 backend/release-record-baseline.md + testing/unreached-branch-guard.md; hot-reload-held-config.md 扩端点 |

## 第二轮(同会话追加): 端点未监听快速失败 + 守阵加固

- **诉求**(用户): 「修复白等 180s 才告警的问题; 测试问题没修的话也一同修」。
- **白等 180s**: 端点没绑端口时, 本机**自己就知道**等不到扩展回传, 而 `ChannelFetcher` 只会
  `queue.wait(request_timeout)` —— 白等 3 分钟(白占站点锁), 日志还只留「等扩展取数超时(浏览器是否
  在运行…)」这条**把人引向浏览器的假线索**。处置: `ChannelFetcher` 增 `listening_fn`(现读回调)
  + `_fetch` 进门即查 ⇒ 未监听立刻抛 `HrChannelUnavailable`(service 折成 `ACTION_NO_CHANNEL`
  + 每站一次 WARNING, 不计失败/不推熔断); 门面 `_build` 传
  `lambda: self.endpoint is not None and self.endpoint.started`(闭包现读: 热重载会整个换端点对象)。
  叫停语义优先(`cancel_reason` 先判 ⇒ 关停路径照旧 `HrChannelStopped`)。附带补齐: `_run_downloads`
  的让位元组漏了 `HrChannelUnavailable` —— 否则通道级故障会被记成「种子取 .torrent 失败」并进重试冷却。
- **守阵加固**: 观测期出口(`_advance_observation`)与冻结同病 —— `test_observing_seed_kept_managed_then_released`
  只断言「记录在」, 不验「放行生效」, 故记录漏带快照时它仍是绿的。已补 `has_anchor_snapshot` +
  `judge_record(...).identity is RELEASED`(红验实测: 未修复时记录 `anchor_*` 全零)。
- **未做**: 端点未监听时的前端展示/自检新字段 —— WebUI 状态块已有 `channel.listening`, 语义够用。

## 进度日志

- **2026-09-29 (同会话追加)**: 端点未监听快速失败 + 守阵加固 —— 3 条守阵红验(白等 5s 后才报超时 /
  观测期记录快照全零 / API 缺失), 修复后 test.full **1745 passed / 4 skipped (91%)**。
- **2026-09-29**: 实报定位(含探针取证: 第一波后 `data.verified[h21]=not-listed`、`infohash_v1` 为空 ⇒ 解释守阵为何假绿灯) → 三缺陷修复 → 守阵重塑与红/绿双向验证 → test.full **1743 passed / 4 skipped, TOTAL 91%**(改动前 1740/4, 90%) → 收尾回写。**真机验证待用户**(端点监听 + 种子从「本地兜底」转「已核实·放行」)。
