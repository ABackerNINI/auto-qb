# 26-09-29-backend-hr-release-deadend — HR「放行签发即作废」与端点未监听(白等 180s)修复

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29
**Summary:** 用户实报 HR 站点接入热重载后种子仍显示「本地兜底已达标」+ 扩展连不上端点。真机 traceback 揪出三个同族缺陷: ①`service._freeze_terminal` 引用**未导入**的 `LANE_SATISFIED`(v3 重建起潜伏到真机才炸) ②冻结/观察期签发的放行记录**漏带锚点快照**, 判定侧把 `anchor_downloaded=0` 读成「downloaded 增长」⇒ 签发当刻作废 ③`HrRuntime.apply` L0 重建路径新建端点却**从不 `start()`**, 端口从未绑定。既有守阵 `test_terminal_vanish_writes_release` 从未走到目标分支(假绿灯) —— 已重塑并红验。**同会话追加一轮**: 端点未监听改为**快速失败**(不再白等 180s) + 观测期出口守阵同样加固。**第三轮**(只读核对用户运行数据): 定位「冷启动判定真空期」并修复 —— 发布原排在所有波次返回之后, 首波可跑数小时 ⇒ 重启后视图为空、判定全回落本地。**第四轮**(同一批数据里挖出真凶): `service.py::channel_state` 的 `CHANNEL_OK` 未导入 —— 健康波一到就 NameError ⇒ 视图发布崩(`view_revision` 恒 0)、`/api/hr/status` 500; 同族 `List`(torrent_cmds)一并修, 并把「名字解析不到」做成**静态守卫**(第三道, 关掉这一类)。test.full 1747 passed / 4 skipped (91%)。
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
| 冷启动判定真空期(第三轮) | Done | `_loop` 首轮取数**前**发布磁盘既有结论; 守阵用「卡住的通道」钉住首轮 |
| 真凶 `CHANNEL_OK` 未导入(第四轮) | Done | 健康波一到就 NameError ⇒ 视图发布崩 + 状态接口 500; 同族 `List` 一并修 |
| 静态名字解析守卫(第四轮收口) | Done | `test_import_all.py::test_no_undeclared_global_names`(第三道; 零误报 + 回退即红) |
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

## 第三轮(用户复验「仍显示本地」: 只读核对运行数据)

- **新证据**(用户授权的只读核对: `auto-qb-data/hr/BTSchool.json` + 运行实例的 `/api/hr/status`、`/api/state`):
  站点文件 schema v2、194 条**全在 B 档**(114 条有 infohash)、`verified` 4 条(锚点全零 —— 旧代码写的,
  现已被 `has_anchor_snapshot` 放行); 而 `view_revision = 0`、108 个种子 `hr_state` **全为空串**。
- **新缺陷(冷启动判定真空期)**: `HrWorker.run_once()` 的发布排在**所有站点波次返回之后**, 而一波受
  站点最小间隔(90s/请求) + 待回填 .torrent 约束可跑数小时 ⇒ `HrRuntime.judge()` 在视图为空时返回
  None ⇒ 四个消费点全部回落本地 ⇒ 界面全是「本地」。(补: `wave_ts` 与 `fetched_at` 差 12h,
  直接说明「那一波没跑完」—— 两者都只由 `_finish_wave` 写。)
- **修复**: `HrWorker._loop` 在首轮取数**之前**先 `publish(self._build_views([]))`(读盘既有结论),
  在 try/except 内只记 ERROR —— 读盘失败不打死取数线程。
- **量化复验**(站点文件 × /api/state 只读比对): 108 个本地种子中按 infohash 命中站点行的只有 **2 个**
  (Cat&Dragon S01E11/E12); 其余 106 = **77 个站点清单里根本没有对应行** + **29 个只有粗配命中他人的行**
  (例: 本地「每月三万…1080p…HHWEB」粗配了行「Yiran's Silver Linings 2026 …2160p…UBWEB」—— 靠质量
  标签构成重合段) ⇒ 行 4 本地兜底, 设计如此。视图发布后前者立刻转「已核实·放行」。
- **旁证(2026-09-29 第五轮按用户指令实施, 见下「第五轮」)**: `FUZZY_NAME_K = 12`(计划建议 12~15,
  取下限)使质量标签构成假重合段 —— 114 次 .torrent 下载里只有 2 次真命中, 白烧站点配额
  (90s/请求、240/日)。修法 = 剔技术噪声整词, **不动 K**(提高 K 治不了 20 字符的噪声段)。落迺�发布组段)由用户定。

## 第四轮(同一批数据里的真凶: `CHANNEL_OK` 未导入)

- **证据链**(全部只读取证, 未改动用户任何文件): 运行实例日志 `auto-qb-data/logs/auto-qb.log` 尾部 ——
  `File "hr/service.py", line 1179, in channel_state / return CHANNEL_OK` →
  `NameError: name 'CHANNEL_OK' is not defined`。崩点链:
  `worker._loop → run_once → publisher.publish(_build_views(...)) → service.build_views →
  build_view_for → channel_state → return CHANNEL_OK` ⇒ **视图永不发布**(被 `_loop` 的「单轮异常不打死
  线程」兜住, 只留一条 ERROR), `view_revision` 恒 0 ⇒ 判定全回落本地; 同一行也让 `/api/hr/status`
  500(`build_site_statuses → build_view_for`)。
- **为何前两轮没看见**: `channel_state` 只在「健康波新鲜」时返回 `CHANNEL_OK`; 重启时 `healthy_ts` 还是
  24h 前的(返回 `CHANNEL_SILENT`, 那行不执行)。18:50:08 波次跑成功(`终态冻结 124 条`)后 `healthy_ts`
  变新鲜 ⇒ 第一次走到 `CHANNEL_OK` ⇒ 崩 —— 即**前两轮修复让波次跑通了, 才把这个更深一层的未导入名顶出来**。
- **同类第三例**: `_freeze_terminal` 的 `LANE_SATISFIED`(第一轮)、`channel_state` 的 `CHANNEL_OK`(本轮)、
  `webui/routes/torrent_cmds.py::api_torrents_add` 的 `List`(局部注解不参与运行期求值, 一直潜伏)。
- **收口(关掉这一类)**: `test_import_all.py` 增第三道静态守卫 `test_no_undeclared_global_names` ——
  逐作用域解析函数体里的名字(自有绑定 / 外层作用域 / 模块全局 / 内建), 解析不到即 red。
  **实测: 现有代码库零误报; 回退本轮两处修复即红**(红/绿双向验证)。前两道拦不住: import-all 只管
  导入期求值, `inspect.get_annotations` 只管注解 —— 函数体里的名字只在**被调用**时才解析。

## 第五轮(用户指令: 修 `FUZZY_NAME_K = 12` 的假重合)

- **只读取证**(用户真实数据 50 条活跃无 infohash 行 × 108 本地名, 未改动任何文件): 旧判据 **159 对**命中
  里 128 对是**纯技术噪声段**(`1080pwebdlh26` / `0pwebdlh265aac` / `1080pnfwebdl` / `2026s01complete1080p`),
  真命中只有 Futsutsuka 与 Cat&Dragon 两族。注意 `2026s01complete1080p` **长 20** —— 光提高 K 拦不住。
- **根因**: 判据 = 「归一化后存在 ≥12 字符连续重合段」, 而归一化把 `1080p WEB-DL H265 AAC` 这类
  每个发布都一样的词也留着 ⇒ 重合段常整段由质量标签构成。
- **修法**: K 仍 12, **变的是拿哪部分参与重合** —— 新增 `FUZZY_NOISE_TOKEN`(分辨率/来源/编码/音轨/
  发布类型/字幕的**整词**表) + `_fuzzy_signal()`(小写 → 按分隔符切词 → 剔噪声整词 → 拼回); 判据改在
  信号串上做 ≥K 重合, **信号串完全相等**不受 K 下限(短标题兜底通路)。按整词剔而非子串替换 ——
  免得把标题里的字符一起啃掉; `dl`(`WEB-DL` 拆出的 2 字符整词)必须收进去, 否则相等通路被它挡掉。
- **验证**: 同批数据 159 → 31 对(剔 128 / **新增 0**); 按行看 13 条 → **4 条**(Futsutsuka + Cat&Dragon
  三集)。另验「再剔发布组后缀(最后一个 `-` 后的短段)」零收益(4 → 4), 故**不做**。
- **残余(不修, 属行 4 本地兜底)**: 标题段短于 K 且两侧组标不同 ⇒ 不触发粗配, 不拿配额换假重合;
  已知报告 `reports/26-09-29-0404-report-hr-verify-v3-audit.html` 里的「粗配 K=12」指**收紧前**语义。
- **守阵**: `test_fuzzy_name_match_rejects_noise_only_overlap`(4 条真实假重合 + 2 族真命中必须保住)
  + `test_fuzzy_name_match_unit` 补 3 条; 红验 —— 仅回退 `service.py`(留测试)即 2 红。
- test.full **1748 passed / 4 skipped, TOTAL 91%**(12,432 / 999 / 4,178 / 409)。

## 进度日志

- **2026-09-29 (第五轮, 用户指令)**: 粗配判据收紧(剔技术噪声整词) —— 真实数据 159 → 31 对、按行
  13 → 4 条、新增 0; 红验仅回退 `service.py` 即 2 红; test.full **1748 passed / 4 skipped (91%)**。
  坑档新增 [pitfalls/backend/fuzzy-match-noise.md](../pitfalls/backend/fuzzy-match-noise.md)。
- **2026-09-29 (同会话追加)**: 端点未监听快速失败 + 守阵加固 —— 3 条守阵红验(白等 5s 后才报超时 /
  观测期记录快照全零 / API 缺失), 修复后 test.full **1745 passed / 4 skipped (91%)**。
- **2026-09-29**: 实报定位(含探针取证: 第一波后 `data.verified[h21]=not-listed`、`infohash_v1` 为空 ⇒ 解释守阵为何假绿灯) → 三缺陷修复 → 守阵重塑与红/绿双向验证 → test.full **1743 passed / 4 skipped, TOTAL 91%**(改动前 1740/4, 90%) → 收尾回写。**真机验证待用户**(端点监听 + 种子从「本地兜底」转「已核实·放行」)。
- **2026-09-29 (第三轮, 只读核对用户运行数据后)**: 定位「冷启动判定真空期」并修复(首轮取数前发布磁盘结论)
  —— 红验 `assert 0 >= 1` 精确复现实测(`view_revision == 0`); test.full **1746 passed / 4 skipped (91%)**。
  仍待用户确认: 106 个种子在站点清单里无对应行是否与预期一致。
- **2026-09-29 (第四轮, 日志取证)**: 挖出真凶 `CHANNEL_OK` 未导入(健康波一到就 NameError ⇒ 视图发布崩
  + `/api/hr/status` 500), 同族 `List` 一并修; 并给这类缺陷补上**静态守卫**(函数体名字解析)。
  全库扫描实测零误报, 回退修复即红; test.full **1747 passed / 4 skipped (91%)**。
