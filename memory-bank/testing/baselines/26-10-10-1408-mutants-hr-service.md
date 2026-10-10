# 2916 —— hr/service.py 波次引擎变异守阵(issue 26-10-10-1108-service-engine)基线

> 摘要: 认领 `issues/26-10-10-1108-test-hr-mutation-service-engine.html`(hr 首轮变异审计里 service.py 的 604 条存活, 首轮建议「按函数分批, 先 `_stop_condition` / `_run_downloads` / `_finish_wave`」)。本轮实施**第一批(这三个函数)**: 逐条读带 diff 的存活清单三分类, 补 **30 个新守阵** + **4 处既有用例补断言**; 红验 **85/85 KILLED**(dump 驱动的同构变异逐条 apply → 定向守阵变红 → 原字节还原, 主仓 `src/` 零残留)。S6 复跑(目标 `**/hr/service.py` · 池 = R14 同一份 15 文件 · `--no-refresh`): **2098 变异 / 杀 1596 / 存活 502**(杀死率 **76.07%**); 对 R14 的 service.py 存活清单**逐 id 对差: 604 → 502(净 −102 = 新杀 103 / 新增存活 1)**, 其中 **93 条落在三个目标函数**(`_run_downloads` 43 · `_finish_wave` 38 · `_stop_condition` 12), 另 10 条为守阵触达旁支路径的连带新杀。**零 `src/` 改动**(纯补测 + 文档)。**issue 留 `In Progress`**(604 条中其余 12+ 函数尚未覆盖, 余量清单见下)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 14:08

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-service-engine.html

## 变异面实测(S6 复跑)

- **目标(glob)**: `**/hr/service.py`(本轮把目标从 R14 的整包 `**/hr/*.py` 收窄到单模块 —— 见下「为什么可比」)
- **选择池(逐文件, 与 R14 完全一致 —— 换池数字不可比)**: `tests/test_hr_service.py` · `tests/test_hr_parse.py` · `tests/test_hr_runtime.py` · `tests/test_hr_resolve.py` · `tests/test_hr_server.py` · `tests/test_hr_worker.py` · `tests/test_hr_store.py` · `tests/test_hr_report.py` · `tests/test_hr_status.py` · `tests/test_hr_channel.py` · `tests/test_hr_fetcher_channel.py` · `tests/test_hr_bencode.py` · `tests/test_hr_queue.py` · `tests/test_hr_ratelimit.py` · `tests/test_hr_multisite.py`
- **工具 / 参数**: mutmut **3.8.0** · `process_isolation=forkserver` · `-n 0 --no-cov` · `--max-children 4`(默认) · 机器 = WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限)
- **专用镜像** `~/auto-qb-mut-hr`(`--mirror`; 多 clone 并行不共用默认镜像, 硬约束 14) · 复跑带 **`--no-refresh`**(硬约束 11), 且**先 `cp` 新 `tests/test_hr_service.py` 进镜像**

| 轮次 | 目标 | 变异总数 | 杀 | 存活 | `no tests` | 超时 | 杀死率 | 墙时 |
|---|---|---|---|---|---|---|---|---|
| R14(26-10-10-1108, 整包) service.py 面 | `**/hr/*.py` | (整包 8027) | — | **604** | — | — | — | — |
| **本轮(26-10-10-1408, 单模块)** | `**/hr/service.py` | **2098** | **1596** | **502** | **0** | **0** | **76.07%** | **26m08s**(1.41 变异/s) |

- **逐 id 对差(R14 service.py 存活 vs 本轮)**: **新杀 103 · 新增存活 1**(净 **−102**)。
  - 新杀按函数: `_run_downloads` **43** · `_finish_wave` **38** · `_stop_condition` **12**(三目标函数合计 **93**)· 旁支 `_do_wave` 2 · `_run_pages` 2 · `_retention_check` 2 · `__init__` 1 · `_refresh_locked` 1 · `_mark_fetch_failed_lane` 1 · `refresh_site` 1(合计 10 —— 新守阵顺带走到这些路径)。
  - **新增存活 1 条**: `limits_for__mutmut_5`(`self.site_confs.get(site)` → `get(None)`)。**经全套件(15 文件)手工复验确认为真存活, 不是退化** —— 疑为 R14「共享镜像崩溃 + 续跑」留下的编号/归类漂移(R14 dump 里 `limits_for` 只有 m2/m4)。已作为余量记入本切片, 不在本轮守阵面(属 `limits_for`, 非三个目标函数)。
- **为什么目标收窄仍可比**: mutmut 的变异**逐文件**生成, 单条变异体「是否被池杀死」只取决于该变异 + 池。R14 的 service.py 存活数(604)来自整包目标的同一份 15 文件池; 本轮把 `only_mutate` 收到单文件不改变 service.py 的变异体集合与池行为 ⇒ 两者的 service.py 存活集合可直接对差。收窄的收益是墙时从整包 ≈96 min 降到 26 min。
- 结果清单: `R:/Temp/auto-qb/mutants/26-10-10-1408-hr-service-py-results.txt`(502 行); 带 diff 清单 `R:/Temp/auto-qb/mutants/26-10-10-1409-hr-service-py-mutants-dump.txt`(502 条)。

## S3 三分类 + 本轮守阵面

按「判据密度 × 出错代价」先做三个函数(首轮建议的批次):

| 函数 | 存活(R14) | 本轮新杀 | 守阵(新) | 说明 |
|---|---|---|---|---|
| `_stop_condition` 停翻三条件 | 22 | 12 | 10 | 连击起点/清零、命中对象跳过、可信完成时间键、最老取小、余量边界、本地覆盖非全深度、兜底 full 标志 |
| `_run_downloads` 防伪下载 | 53 | 43 | 9 | 回填出队、continue 语义、冷却闸边界、失败计数累加、HrDownloaded 字段、命中侧取本地、dl_by_hash 登记、亚秒 Retry-After |
| `_finish_wave` 放行与释放 | 88 | 38 | 11 + 4 处补断言 | 波元数据(wave_ts/retention)、releases_signed 相加、depth_broken→parse、alerted 各单因、零行确认戳边界、健康波判据、计数对不平 ERROR 级别与逐参文案、截断差值边界 |

- **等价 / 不可观测(不追, 各记理由)**: 错误/告警**文案**变体(如 `raise ValueError(None)`、`logger.warning(None)`、`"XX..XX"` 包裹)、**日志级别**变体、**增量落盘**被摘(`_persist_step(None)`, 崩溃窗口不可观测 —— 波末仍会 commit)、`retry_after` 的 `getattr` 缺省变体(`HrFetchError.retry_after` 恒存在 ⇒ 缺省值不可达)、`anchor.completion_on > 0` 的 `>=0`/`>1`/`else 1.0` 变体(下游 `done > 0` 闸把负值/0 一并滤掉 ⇒ 全部输入等价)。
- **余量(未覆盖, 留后续轮)**: `service.py` 其余函数 —— `_run_pages` 68 · `_do_wave` 61 · `_refresh_locked` 38 · `_append_history` 30 · `_lanes_summary_from` 28 · `_build_objects` 17 · `refresh_site` 16 · `_process_rows` 15 · `_freeze_terminal` 15 · `_sign_releases` 14 · `_advance_observation` 8 · `_order_violation` 5 · `_update_cutoff` 5 · 模块级纯函数等(粗读已见大量真洞: `while` 边界、`marks_says_next` 判据、`st.rows += len(...)`、`continue→break`、`parse_problem` 旗标、事件参数替换)。

## 补测(S5)与红验

- **新增 30 个测试函数**(全落 `tests/test_hr_service.py`, 已同步该文件 docstring 的「## 测试计划」R16 节): `_stop_condition` 单元 10 个 + `_run_downloads` 单元/端到端 9 个 + `_finish_wave` 端到端 11 个。
- **既有用例补断言 4 处**(原先缺断言 ⇒ 对应变异存活): `test_retention_check_freezes_batch`(+`retention_ratio ≈ 1/3`、+`alerted is True`)· `test_zero_rows_no_release`(+`alerted is True`)· `test_counter_zero_claims_self_attest_empty`(+`alerted is False`)· `test_interval_empty_page_keeps_manual_stamp`(+`alerted is True`)。
- **红验 85/85 KILLED**: 脚本 `tmp-analysis/mut_svc_redverify.py` —— 从 R14 dump 取每条候选的**同构变异块**, 按「strip 后内容唯一命中」定位(处理 mutmut dump 的**去缩进 + 续行不归一**两种形态; 命中数 `!= 1` 报 `ANCHOR-MISS` 停手), 逐条 apply → 跑**定向守阵** → 原字节回写还原(主仓 `src/` 零残留, LF 未被改写)。
- **踩到的已记坑**: [redverify-anchor-lineendings](../../pitfalls/testing/redverify-anchor-lineendings.md) **复发 +1** —— 本轮出现**形态四**: 锚点来源从「手写文本」换成「从 mutmut dump 取行块」后, dump 行块相对源码整体**去缩进**、且**续行缩进不被归一**(同一 hunk 内既有 −4 也有 −0) ⇒ 精确块匹配恒失配(实测 9 条 ANCHOR-MISS)。处置: 改「strip 内容唯一匹配 + 按锚点行缩进位移复原 + 只重写有变化的行」。另有首版脚本用 `write_text` 在 Windows 把 LF 写成 CRLF(还原时污染工作树) ⇒ 改**字节层读写**。**为什么没命中**: 坑里记的是 CRLF / 缩进差 1 / 字节层类型 / 重复锚点四形态, 本轮是**「锚点来自 diff 产物的空白不可信」**这一新形态; 但「命中数 `!= 1` 就停手」的兜底生效了(报 ANCHOR-MISS 而非假绿)。已把形态四补进坑档。

## test.full 实测

- 分支: `develop`(工作树含本轮补测 + 文档时实测; 开工已同步远端)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2916 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16568 语句 / 167 未覆盖 / 5716 分支 / 142 partial)
- 相对 R14 切片 [26-10-10-1108](../baselines/26-10-10-1108-mutants-hr.md): passed **+30**(= 本轮新增用例; 余数来自开工同步进来的远端提交, 非本轮)· 未覆盖 167 持平 · partial 143 → 142。
- `src/` **零改动**。Linux(WSL 沙箱)侧未重测 —— 本轮只加平台无关的断言用例, 未改平台相关代码(口径见 baseline.md 常驻警告)。
