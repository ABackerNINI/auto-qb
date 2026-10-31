# 3274 —— hr/service.py 波次引擎余量函数变异守阵(issue 26-10-10-1108-service-engine)基线

> 摘要: 续 R16(第一批三函数, 604→502)认领 `issues/26-10-10-1108-test-hr-mutation-service-engine.html` 的**余量**: 本轮(**R22**)对 service.py 其余 12+ 函数(开工前态 **491 条存活**)逐条读带 diff 清单三分类, 补 **29 个新守阵**(`tests/test_hr_service.py` R22 节, 169→184 用例); 红验 **38/62 KILLED**(余 24 条逐条判等价, 清单见 `tmp-analysis/r20_equiv_reasons.md`), 主仓 `src/` 零残留。S6 复跑(目标 `**/hr/service.py` · 池 = R14 同一份 15 文件 · `--no-refresh`): **2102 变异 / 杀 1794 / 存活 308 / 0 超时 / 0 no tests**(杀死率 **85.35%**); 对开工前态 **逐 id 对差 491 → 308**(净 **−183** = 新杀 187 / 新增存活 4)。**零 `src/` 改动**(纯补测 + 文档)。**issue 置 `Done`**(service.py 余量函数全覆盖; 余 308 条存活按函数分布见下, 属等价面 + 4 条编号漂移新面)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-15 09:22

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-service-engine.html

## 变异面实测(S6 复跑)

- **目标(glob)**: `**/hr/service.py`
- **选择池(逐文件, 与 R14 完全一致)**: 15 文件(清单见 R16 切片 [26-10-10-1408](26-10-10-1408-mutants-hr-service.md))
- **工具 / 参数**: mutmut **3.8.0** · `process_isolation=forkserver` · `-n 0 --no-cov` · `--children 3` · 机器 = WSL2 `Ubuntu-26.04`
- **专用镜像** `~/auto-qb-mut-hr-svc`(与并行会话的 `~/auto-qb-mut-hr` 分离, 硬约束 14) · 复跑带 **`--no-refresh`**(硬约束 11), 且**先 `cp` 新 `tests/test_hr_service.py` 进镜像** —— cp 必须走 `wsl -e bash -lc "cp /mnt/d/..."`(裸 `wsl cp /mnt/d/...` 会被 Git Bash 改写成 `D:/Program Files/Git/mnt/d/...` 而失败)

| 轮次 | 目标 | 变异总数 | 杀 | 存活 | `no tests` | 超时 | 杀死率 | 墙时 |
|---|---|---|---|---|---|---|---|---|
| R16(26-10-10-1408, 第一批三函数) | `**/hr/service.py` | 2098 | 1596 | **502** | 0 | 0 | 76.07% | 26m08s |
| **本轮(26-10-15-0922, 余量函数)** | `**/hr/service.py` | **2102** | **1794** | **308** | **0** | **0** | **85.35%** | **27m12s** |

- **逐 id 对差(开工前态 491 vs 本轮)**: **新杀 187 · 新增存活 4**(净 **−183**)。
  - 新杀按函数: `_refresh_locked` **28** · `_lanes_summary_from` **22** · `_run_pages` **19** · `_append_history` **17** · `_do_wave` **14** · `_finish_wave` **14** · `_freeze_terminal` **13** · `_build_objects` **11** · `refresh_all` **7** · `__init__` 6 · `_sign_releases` 6 · `store` 5 · `_absence_proven_all` 5 · `_advance_observation` 5 · `build_view_for` 5 · `refresh_site` 4 · `_release_record` 3 · `_position_covered`/`_mark_fetch_failed_lane`/`_Budget.take` 各 1。
  - **新增存活 4 条**: `refresh_site` m24(`build_adapter(site, …) → (None, …)`) · `_do_wave` m151(删 `trigger=trigger`, 回落默认 `"auto"`) · `_run_pages` m3(`while active and … → or …`) · `_run_pages` m64(`events.fetch_failed(site, 1, 1, …) → (site, 2, 1, …)` 页号)。**4 条已用全套件手工同构复验: 均 `SURVIVED`(3274 passed), 是真存活不是假存活**(脚本 `tmp-analysis/r20_verify4.py`)。与本轮 S6 前态 KILLED 的差异**疑为 mutmut 编号漂移** —— 本轮 S6 前有一次被中断的跑批(cp 路径失败被 `TaskStop`), 镜像 `mutants/` 留下半轮缓存, 重跑时编号↔变异体映射错位(与 R16 记录的 `limits_for m5` 同源现象)。**结论: 以手工复验为准, 记为「4 条新面存活」**(`_run_pages` 的 `and→or` 由 `if not progressed: break` 兜底, 判等价; 另 3 条属未覆盖新面)。
  - 开工前态 491 = R16 后 502 经 R17–R19 三轮(池内其它测试文件增补)的自然漂移, 非本轮改动。
- **仍存活 308 条按函数分布**: `_run_pages` 47 · `_finish_wave` 36 · `_do_wave` 35 · `_process_rows` 15 · `_append_history` 13 · `refresh_site` 11 · `_stop_condition` 10 · `_run_downloads` 10 · `__init__` 9 · `_refresh_locked` 9 · `_warn_no_channel` 8 · `_sign_releases` 8 · `_build_objects`/`_lanes_summary_from`/`_Budget.take` 各 6 · `_warn_parse`/`_absence_proven_all`/`_maybe_alert_lane_fail`/`_update_cutoff`/`_order_violation`/`_warn_once` 各 5 · `_merge_seen`/`_release_record`/`fuzzy_name_match`/`channel_state` 各 4 · `_warn_ext_quota`/`limits_for`/`_warn_login`/`_advance_observation`/`_prune_index` 各 3 · 余为 1–2 条的小面。等价面(错误/告警文案、日志级别、增量落盘被摘、形参默认值、`getattr` 缺省、判据边界在真实取值域不可分等)为主。
- 结果清单: `R:/Temp/auto-qb/mutants/26-10-15-0922-hr-service-py-results.txt`(308 行); 带 diff 清单 `R:/Temp/auto-qb/mutants/26-10-15-0923-hr-service-py-mutants-dump.txt`(308 条)。

## S3 三分类 + 本轮守阵面

按「判据密度 × 出错代价」覆盖余量函数(开工前态存活数):

| 函数 | 前态存活 | 本轮新杀 | 守阵(新) | 说明 |
|---|---|---|---|---|
| `_run_pages` 翻页轮转 | 64 | 19 | 12 | 页上限下限 1、预算挡下只截断自己(continue)、亚秒 Retry-After、排序违反只停该档、计数上交实参、行数跨页累加、merge_seen 时刻、heartbeat、JS 翻页标记双证据、末页只结束该档、未轮档失败累加 |
| `_finish_wave` 收尾 | 50 | 14 | 8 | 干净波清零、确认戳清 0、notes 分号连接、零行文案单点、健康波无留存 note、persist=false/只读退化 reason 追加 |
| `_do_wave` 波内预算与分支 | 48 | 14 | 7 | 单次/本波累计等待上限、叫停不记历史、扩展额度让位记历史、登录失效、Retry-After 24h 封顶、页面失败降 PARTIAL |
| `_refresh_locked` 调度闸 | 37 | 28 | 5 | 复用窗边界到期即取、复用路径回填字段、拉取间隔精确秒数、dry-run force defer 历史、min_interval force defer 精确秒数 |
| `_append_history` + `_lanes_summary_from` | 58 | 39 | 4 | 档位摘要排版三态、波事件逐字段搬运、reason_kind=budget、defer 事件默认 0 |
| `_build_objects`/`_process_rows`/`_freeze_terminal`/`_sign_releases`/`_advance_observation` | 64 | 37 | 7 | 对象集排除面(纯内存)、重例行继承身份、多条目退役位置规则 + 失效档条目只跳过自己、命中跳过不拦后续签发 + 登记 tid、观察期逐条目出口 + A 档出口 streak 清零 |
| `refresh_site` / 版本回退 / 读坏 | 14 | 4 | 2 | 版本回退 reason 精确文案、读坏恢复按空数据保守跑 |
| `refresh_all`/`store`/`build_view_for`/`_WaveContext.__init__`/`_absence_proven_all` | 38 | 23 | 5 | 三态直通(None→None / 缺站键→{})、惰性分支构造参数、视图透传三字段、波上下文初值不变量、缺席证明四边界 |

- **等价 / 不可观测(不追, 逐条理由见 `tmp-analysis/r20_equiv_reasons.md`)**: 形参默认值不可达 6 · 属性恒存在/形参未使用 5 · 被后续赋值/兜底覆盖 5 · 判据边界在真实取值域不可分 5 · 参数在给定路径下不参与计算 2 · 测试面不可观测 1(`_refresh_locked` m4: 池内站点 conf 未设异于 global 的限速面)。

## 补测(S5)与红验

- **新增 29 个测试函数**(全落 `tests/test_hr_service.py` R22 节; 已同步该文件 docstring 的「## 测试计划」R22 节): `_run_pages` 12 · `_finish_wave` 8 · `_do_wave` 7 · `_refresh_locked` 5 · `_append_history`/`_lanes_summary_from` 4 · 对象集/行处理/冻结/签发/观察期 7 · `refresh_site` 2 · `refresh_all`/`store`/`build_view_for`/`_WaveContext`/`_absence_proven_all` 5。助手: `_StoppedFetcher` · `_RecordingCounterAdapter` · `_marks_page` · `_real_adapter` · `_site_file_json`。
- **红验 38/62 KILLED**(脚本 `tmp-analysis/r20_redverify.py` —— dump 驱动同构变异逐条 apply → 定向守阵 → 原字节回写还原; MAP 62 条 = 12 大族各抽 2 条 + 5 个新函数面全量 + `_absence_proven_all` 10 条全量)。
  - **首轮红验 33/62 暴露 5 条真洞** ⇒ 当场补 3 个守阵(`test_sign_releases_hit_head_does_not_abort_rest` 命中首条 break 漏签 / `test_freeze_terminal_failed_lane_between_entries` 失效档条目 break 漏退役 / `test_advance_observation_scope_exit_resets_streak` 出口 streak 未断)并加强 `test_build_view_for_passes_listing_state_generated`(内存 data 与盘故意不同 → 杀 channel_state 回读盘)⇒ 复验 **5/5 KILLED**。
  - **调试实录(值得记)**: `_run_pages__mutmut_4`(`pages_left > 0 → >= 0`)红验判 SURVIVED, 初判为「缓存/apply 失效」—— 用 `faulthandler` + 逐圈打印实测, 真相是 while 体尾部 `if not progressed: break` 兜底(多出的空转圈零请求零副作用) ⇒ **等价**, 不是漏杀。**教训: 红验 SURVIVED 先查守卫兜底, 别先怀疑脚本**。
  - **红验脚本自身修三处 bug**: ①`parse_dump` 首版把所有条目写进同一个 `None` key(只活最后一条); ②模块级 mutmut id 前缀是 `x_`(剥 2 字符)不是 `x__`(剥 3); ③MAP key 的 func 段需归一化(类内保留前导下划线、模块级剥 `x_`)。

## test.full 实测

- 分支: `develop`(工作树含本轮补测 + 文档时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **3274 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16866 语句 / 158 未覆盖 / 5714 分支 / 142 partial)
- 相对 R16 切片 [26-10-10-1408](26-10-10-1408-mutants-hr-service.md): passed **+358**(含本轮 15 个新用例; 余数来自开工同步/并行轮次进来的用例, 非本轮)· 未覆盖 167 → 158 · partial 142 持平。
- `src/` **零改动**。Linux(WSL 沙箱)侧未重测 —— 本轮只加平台无关断言用例, 未改平台相关代码。
