# 4366 passed + 2 skipped(根) —— 1,726 变异 / 复跑杀死率 91.94% —— core/traffic_store W4 变异审计: 首轮与补测后复跑(同目标同池)

> 摘要: core/ 包 W4(R28, 计划 26-10-31-0128): 目标 `**/core/traffic_store.py` 单文件 **1,726 变异** · 池 5 文件定向 → 首轮 **杀 1,544 / 存活 180 / no tests 0 / 超时 2**(杀死率 **89.45%**; 过程环境事件: WSL 会话被杀 6 次、分块续跑) → S5 补测 14 守阵进池(test_traffic_store +286 行, 红验 37/37 全红) → **同目标同池复跑: 杀 1,587 / 存活 139 / no tests 0 / 超时 0**(杀死率 **91.94%**, 存活 −41·超时 −2, **新增存活 0**)。三分类(W4 池口径): 确认真洞 **73** 处置闭环 = **中 12 + 低 25 共 37 条 S5 定向补测销账**(复跑实测新杀 39, 含 wtp_42/43 由 wtp_49 守阵连带转杀)+ **低/极低 36 批量入池 2 issue(H 簇观测面 19 + 极低危余量 17)**; **timeout 2(wtp_42/43)S4 形态级实跑裁定死循环**(DoS 形态, 复跑已转被杀); 等价 107(复跑后存活面 106: z_row_39 因新守阵断言消息文案转被杀, 连带销账); 假存活 0(S4 26 条全 SURVIVED 佐证)。**零 `src/` 改动**(纯补测 + 批量入池 + 文档 + 工具 deselect 一条)。
> 基线时间: 2026-10-31 16:12
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4366 passed + 2 skipped**(C3 阶段实测誊写, commit 0da14ca9 = 本轮开工 rebase 后树; S5 阶段实测 4251 + 2 为 rebase 前树, 开发线合入新增用例后重采, 本切片以此为准)。

### 首轮与复跑对照(每轮一行)

| 目标 / 轮次 | 变异 | 杀 | 存活 | no tests | 超时 | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| traffic_store.py 首轮(2026-10-31 13:49 dump) | 1,726 | 1,544 | 180 | 0 | 2 | 未整录(WSL 会话被杀 6 次、分块续跑) | 89.45% |
| **traffic_store.py 复跑(S6, 15:57)** | **1,726** | **1,587** | **139** | **0** | **0** | **288.4s**(wrapper 实测) | **91.94%** |

- **目标(glob)**: `**/core/traffic_store.py`(单文件, target 只收单 glob)
- **选择池(逐个文件, 5 个; 两轮一致)**:
  `tests/test_traffic_store.py` · `tests/test_traffic_grid.py` · `tests/test_traffic_sample.py` · `tests/test_traffic_limits.py` · `tests/test_web_traffic_qb.py`
  - 池内 1 文件含 S5 新守阵: test_traffic_store.py(+286 行, commit 6b435638); 其余 4 文件两轮无改动(md5 与首轮一致已核)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**(成因: W4-A 疑似并行会话共用默认镜像冲毁, 按计划 D3 备选切换, 硬约束 14)
- **镜像口径**: 镜像 fetch 自本地分支 mut-core-audit, head `a83e27b9`(W3 收口提交, 本地分支线)——**两轮同 head, 数字可比**; ⚠ head 非 origin/develop HEAD(本轮开工 rebase 后本地 HEAD `0da14ca9`, 镜像未刷新): 目标文件与池 5 文件 md5 与本地逐位一致已逐一核验, 复跑口径不受影响
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— S5 守阵 commit(6b435638)未在镜像 head 线内, `--no-refresh` + 手工 cp test_traffic_store.py 进镜像 `tests/`(md5 `f28c0f0e` 核对一致)
- **deselect 口径**: `set_conf.py` DEFAULT_DESELECT 本轮 **2→3 条**(新增 `tests/test_traffic_store.py::test_v4_parse_skeleton_single_point` —— S5 新骨架静态守阵读源码文本断言, mutmut 变异树里恒红; 按 issue 26-10-31-1539-bug-mutation-tooling-deselect-guards 建议修法补, 未提交)。S6 首启该守阵击穿 stats 收集一次(mutmut「failed to collect stats. runner returned 1」), 补 deselect 后过 —— 缺口本体与守阵提醒机制缺失已在该 issue 入池
- **新增存活 0**(逐 id 对差: 首轮 182 条存活+超时集合 vs 复跑 139 条存活集合, 只有移出无移入)
- **存活 −41·超时 −2 的构成**(新杀 43, 逐 id 对差):
  - **守阵 A–G 簇 39**: A 裁剪原子重写 trim_34 + wtp_1/9/12/49(5)· wtp_42/43 盲区转被杀(2, wtp_49 守阵连带 —— 变异体重试计数坏 → 永不返回 → 用例超时判杀, 预期兑现)· B 淘汰轮 evict_17/22(2)· C 文件头空行 _ensure_15/17/18/22(4)· D 解析幽灵块 day_2(1)· E errors 严格化 _read_parse_10/14/19/20 + trim_15/19/24/25(8)· F CRLF 族 app_rec_58/62 · app_agg_23/27 · wtp_23/27(6)· G 写侧 fail-fast/格式 width_5/6 + z_row_33/34/36 + slots_45 + app_rec_22 + live_tail_104/136/137/150(11)
  - **连带销账 2**: width_7(真洞极低, 「day 宽 86400→86401」被 cov 封顶守阵的精确断言 `cov_s == 86_400` 连带杀)· z_row_39(原判等价(消息面), 新守阵 `pytest.raises(match="负 delta")` 断言消息文案后转可观测 —— 判读保守非假阴性, 同 W3 kib_1 形态)
  - **疑似 flaky 击杀 2**: cache_agg_36/37(V4DayCache.read_agg 空默认 bad_lines/data_lines 0→1, 真洞极低, 本在极低危余量 issue)—— mutmut 判杀, 但定向复验两轮(全套件池 / 函数映射子集)均全绿**不可复现**, 同 R26 limits flaky 击杀前科(时序敏感子进程资源竞争型), 下轮对账
- **超时盲区 2 条复跑转被杀**(wtp_42/43): 预期兑现 —— S4 已实跑裁定死循环 DoS 形态(227k 次 os.replace/sleep·5s 不返), 处置=随 A 簇 issue 记 bug 备注, 修复取代码侧非补测; 复跑由 wtp_49 守阵连带确定性转杀, 盲区清零

### 三分类与处置(W4 池口径, 详见任务档案 R28 与 tmp-analysis/mut-core-w4-classify.md)

- 确认真洞 **73**(中 12 / 低 38 / 极低 23)处置**全部闭环(37 + 19 + 17 = 73)**: **中 12 + 低 25 共 37 条由 S5 定向补测销账**(14 守阵体进 test_traffic_store, 红验 37/37 全红; 复跑实测新杀 39 = 37 条对应 + wtp_42/43 连带)+ **H 簇观测面 19 条(低 11 + 极低 8)批量入池 issue**(整体降级: 仅日志零行为, 如补则 caplog 两向断言)+ **余量 17 条(低 2: evict_37 · cache_day_33 + 极低 15)批量入池 issue**(其中 width_7 · cache_agg_36/37 复跑实测转被杀, 提前销账, issue 本体待核对; 其余维持 classify 逐条「不追」)。
- **等价 107**(消息面 47 · 域内/哨兵/不可达 60, 逐条理由见 classify)—— 复跑后存活面 **106**(z_row_39 转被杀, 连带销账)。
- **假存活 0**: 块 A/B 池外核查均零可杀(test_web_longtail 无字节级断言); S4 抽验 26 条全 SURVIVED 佐证。
- **timeout 2**(wtp_42/43): S4 形态级手搓实跑裁定死循环(DoS 形态, 危害 = PermissionError 持续时 flush 线程挂死 + tmp churn), 复跑转被杀, 盲区闭合。
- **S4 覆盖 26 条**(硬约束 10 收窄: 中 12 全验 + 低危 6 簇抽代表 8 + 极低 2 + 存疑 4): verify 实测 **26 SURVIVED / 0 KILLED**(判据 = 全套件差集, 基线 4227 passed + 12 skipped 0 失败; 5 条首轮遇 hr_discovery 绑定类 flaky 记 FLAKY, 复验落定, 未误判)—— 0 条判读被推翻; **存疑 4 条裁定**: ramp_25 = 等价(域内)· rdk_9 = 等价(域内)· _wbl_21 = 真洞(极低)· app_rec_22 = 真洞(低), 均按 SURVIVED 维持静态判读。
- **红验 37/37 全红**(S5 手搓同构变异形态复验 + 2 死循环盲区坐实; 手搓数字不进任何计数, 量化以本切片复跑为准)。
- **4 条 issue**(26-10-31-1539 系列, doc-refs 反向声明任务档案): `memory-bank/issues/26-10-31-1539-test-core-w4-mutation-observability-logs.html`(H 簇观测面 19 条目)· `26-10-31-1539-test-core-w4-mutation-extreme-low-residue.html`(极低危余量 17 条目)· `26-10-31-1539-bug-mutation-tooling-deselect-guards.html`(工具坑: DEFAULT_DESELECT 缺新文本层守阵 + 提醒机制缺失)· `26-10-31-1539-bug-mutation-tooling-verify-channel.html`(工具坑: verify 通道)。
- **dump / results 指针**(R:\Temp\auto-qb\mutants\): 三分类输入 = 首轮 dump `26-10-31-1349-core-traffic-store-py-mutants-dump.txt`(182 条 = 180 survived + 2 timeout); S4 verify = `s4-verify-w4-s4-ids.txt`(26 条终态); 复跑 = `26-10-31-1557-core-traffic-store-py-results.txt`(139 survived)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_traffic_store.py` | S5 阶段 14 守阵(+286 行, 红验 37/37 全红 + 2 死循环盲区坐实), commit 6b435638(先于本轮 C3) |
| `memory-bank/issues/26-10-31-1539-test-core-w4-mutation-observability-logs.html` · `26-10-31-1539-test-core-w4-mutation-extreme-low-residue.html` · `26-10-31-1539-bug-mutation-tooling-deselect-guards.html` · `26-10-31-1539-bug-mutation-tooling-verify-channel.html` | 批量入池 19+17 条目 + 工具坑 2 件, commit 08ce7f62(先于本轮 C3) |
| `.commands/mutants/scripts/set_conf.py` | DEFAULT_DESELECT 2→3 条(新增骨架静态守阵 deselect; 按 deselect-guards issue 建议修法; **本轮未提交**) |
| `memory-bank/testing/baselines/26-10-31-1612-mutants-core-traffic-store.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R28 轮次完成条目追加 |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W4 口径) |

**未改**: `src/` 零改动(纯补测 + 批量入池 + 文档 + 工具 deselect 一条); 选择池未扩(H 簇 caplog 守阵与极低危余量按 classify 建议记录不补, 留后续轮)。
