# 26-10-10-backend-dup-code-audit — 全仓重复代码审查(分步执行计划)

**Status:** In Progress
**Added:** 2026-10-10
**Updated:** 2026-10-11
**Topics:** dup-code-audit
**Summary:** 用户要求「做一轮重复代码审查, 主要用于后续的重构, 增强一致性与减少维护点; 先写一个分步执行方案(先分析后端哪一部分 config? core?), 避免单轮任务过长」, 追问下选定**正式 HTML 计划 + 全仓范围(含前端三皮肤)+ 步骤拆细**。本轮**只产出计划制品, 零代码改动**: 计划 `plans/26-10-10-2333-plan-dup-code-audit.html`(专题 `dup-code-audit`, 状态 `Open` 待拍板)。计划含四类判定口径(A 真重复 / B 分歧重复只登记 / C 同一事实多表示 / D 表面相似不动) + 两段式方法(机器提名 pylint R0801 / jscpd → 人工定性) + **27 轮分步清单**(准备 → 后端 19 → 前端 4 → 测试与横切 2 → 汇总, 一轮一面独立会话) + 每轮六步微步骤 S1–S6 + 硬停手点(只审查不改码 · 单轮 ≤4000 行 · B 类只登记)。〔26-10-11 执行轮〕用户「做 Phase 0/1」→ 已完成 **Phase 0 + 轮 01–04(config 全包)**; 用户「做 Phase 1 core部分」→ 已完成 **轮 05–10(core 全包)**; 用户「做 Phase 1 hr 部分」→ 已完成 **轮 11–14(hr 全包)**; 用户「做 Phase 1 webui 部分」→ 已完成 **轮 15–16(webui 全包)**; 用户「做 Phase 1, 17-19部分」→ 已完成 **轮 17–19(rules / infra / torrents+tray+entry)**, 三包 34 项发现(A11/B5/C9/D9), 全局累计 156 项(A58/B15/C40/D43)。**Phase 1 后端(config+core+hr+webui+rules+infra+torrents)全部走完**。全程纯审查轮, 零源码改动。
**Refs:** memory-bank/activeContext/26-10-10-2356-dup-code-audit.md,memory-bank/activeContext/26-10-11-0207-dup-code-audit.md,memory-bank/activeContext/26-10-11-0240-dup-code-audit.md,memory-bank/activeContext/26-10-11-0314-dup-code-audit.md,memory-bank/activeContext/26-10-11-0352-dup-code-audit.md,memory-bank/testing/baselines/26-10-10-2356-dup-code-audit-plan.md,memory-bank/testing/baselines/26-10-11-0033-dup-code-audit-config.md,memory-bank/testing/baselines/26-10-11-0207-dup-code-audit-core.md,memory-bank/testing/baselines/26-10-11-0240-dup-code-audit-hr.md,memory-bank/testing/baselines/26-10-11-0314-dup-code-audit-webui.md,memory-bank/testing/baselines/26-10-11-0352-dup-code-audit-rules-infra-torrents.md,memory-bank/reports/26-10-11-0033-report-dup-code-audit.html,memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

## 原始请求

> 用户(2026-10-10): 「重复代码审查: 做一轮重复代码审查, 主要用于后续的重构, 增强一致性与减少维护点. 先写一个分步执行方案, 比如先分析后端哪一部分(config?core?), 再分析哪一部分, 避免单轮任务过长」

> 追问下的三处选择(AskUserQuestion): 产出形式 = **正式 HTML 计划文档**(memory-bank/plans/); 审查范围 = **全仓(含前端三皮肤)**; 追加要求 = **「步骤拆细一点」**。

## 思考过程与决策

- **请求边界判定**: 这是**执行任务**(产出计划制品), 不是纯问答; 但本轮边界恰是「只定轮次、不改任何代码」——计划的执行放到后续独立会话与轮次。
- **形态走 `plans/`(不是 `reports/`)**: 本件回答「怎么审、按什么顺序审」= 方案与取舍, 属工位 `plan`(doc-forms 决策树); 审查产生的**现场证据**留待执行期进 `reports/`(滚动报告), 可动项进 `issues/`(type `refactor`)。
- **四类口径的取舍**: 关键是把「B 分歧重复」与「D 表面相似」单列 —— 前者直接合并会改行为(必须先钉差异点 + 回归保护), 后者是防**过度抽象**的刹车(形状像但语义无关, 一律不动)。没有这两类, 审查会退化成「见重复就抽公共函数」。
- **先 config 的顺序依据**: 一个配置键在 schema / loaders / validation / writer / docs/configuration.md / memory-bank config-reference / 设置页元数据 **至少七处**出现, 是全仓「同一事实多表示」(C 类)最密的包, 收益最大且相对自包含; 更详细的排序依据(重复密度 × 读取代价)写在计划 §04。
- **工具走临时环境**: pylint / jscpd 用 `uv run --with` / `npx` 临时拉起, **不写进 pyproject**(同变异测试审计对主仓依赖面的纪律); 工具只做**提名**, 结论一律人工定性(工具不懂哪些是刻意重复)。
- **一轮一面 + 六步固定**: 为满足「避免单轮过长」, 每轮限定一个面(包 / 子包 / 一类横切), 上限单轮 ≤4000 行源码 / 提名组 ≤30; 六步 S1–S6 保证可重复、可中断、可交接。
- **不越界立项**: `tests/` 与前端三皮肤虽在范围内, 但按阶段后置(Phase 2/3), 不并进首轮; 本轮不预设任何具体重复结论(那属执行期)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 范围与口径确定(全仓 · 四类判定词 · 一轮一面) | Done |
| S1 | 规模实测与轮次切分(各包/子面行数 + 文件数) | Done |
| S2 | 产出计划 HTML(`plans/26-10-10-2333-plan-dup-code-audit.html`) | Done |
| S3 | 收尾回写(本档案 + activeContext 切片 + 基线切片 + `kb.index` + `kb.check`) | Done |
| S4 | 计划拍板(报告形态 / 起步轮)—— 用户拍板: **范围 = Phase 0 + 轮 01–04(config 全包)**; 报告形态取默认**滚动报告** | Done |
| S5+ | 逐轮执行 Phase 0 → Phase 4(轮 00–26, 每轮独立会话)—— 已完成 Phase 0 + 轮 01–04(config) + 轮 05–10(core) + 轮 11–14(hr) + 轮 15–16(webui) + 轮 17–19(rules / infra / torrents+tray+entry) | In Progress |
| S6 | 轮 26 汇总: 重构候选排序表 + 跨层「同一事实」总账 + 可动项入池 | Open |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| 计划落盘 | Done | `plans/26-10-10-2333-plan-dup-code-audit.html`(dark · `doc-topic=dup-code-audit` · `Open`) |
| Phase 0 准备(轮 00 工具与口径) | Done | 工具冒烟 + 口径固化 + 建档 + 基线 `0d27b69e`; 见报告 §03 |
| Phase 1 后端(config 轮 01–04) | Done | 报告 §04–§07; 入池 7 issue(refactor) |
| Phase 1 后端(core 轮 05–10) | Done | 报告 §08–§13; 入池 core 9 issue; 46 项发现(A21/B6/C9/D10) |
| Phase 1 后端(hr 轮 11–14) | Done | 报告 §14–§17; 入池 hr 9 issue; 29 项发现(A12/B1/C7/D9) |
| Phase 1 后端(轮 15–16: webui 全包) | Done | 报告 §18–§19; 入池 webui 10 issue(refactor); 24 项发现(A9/B2/C7/D6) |
| Phase 1 后端(轮 17–19: rules / infra / torrents+tray) | Done | 报告 §20–§22; 入池 rules 3 / infra 5 / torrents+tray 3 = 11 issue; 34 项发现(A11/B5/C9/D9); **Phase 1 后端全包完成** |
| Phase 2 前端(轮 20–23: shared JS / 抽屉模板族 / 三皮肤 CSS / 模板) | Open | 总量最大两块之一 |
| Phase 3 测试与横切(轮 24–25: tests/ + 跨层同一事实总账) | Open | 轮 25 是重构收益最大的一张表 |
| Phase 4 汇总(轮 26) | Open | 重构候选排序 + issue 入池 |

## 进度日志

### 2026-10-10 R0 — 立项(计划落盘)

- **触发**: 用户「做一轮重复代码审查…先写一个分步执行方案…步骤拆细」。
- **摸底(只读)**: 走 `memory-bank/README.md` 细路由建立心智模型; 实测各包/子面行数与文件数(后端 8 包、前端静态、tests)作为轮次切分依据; 核对既有制品避免重复 —— 已有全项目 Code Review(`26-10-05-0951`)与变异审计(专题 `mutation-audit`)覆盖缺陷/测试硬度, 但**无一次系统性重复代码审查**(仅零散 refactor issue)。
- **产物**: `plans/26-10-10-2333-plan-dup-code-audit.html` —— §01 背景与目标(含与既有审查的不重叠声明) · §02 四类口径 + 记录七字段 · §03 两段式方法与工具 · §04 27 轮分步清单(Phase 0→4) · §05 每轮六步微步骤 · §06 产出与归档 · §07 停手点与风险 · §08 验收 · §09 变更记录。
- **待拍板**: ①报告形态(默认滚动报告; 备选每阶段冻结 3 份); ②起步轮(默认轮 01 `config/schema/`; 备选先跑轮 00 工具冒烟)。
- **收尾实测**: `commands run test.full` → 数字见基线切片 [26-10-10-2356](../testing/baselines/26-10-10-2356-dup-code-audit-plan.md)(本轮零 `src/`、零 `tests/` 改动, 与上基线持平); `test_docs_forms.py` 11 passed(计划 meta / 命名 / dark 主题 / 索引自洽); `kb.check` 主键纪律 / 认领链 / 回写措辞 / 日期守卫全过; `kb.index` 重建生成物(计划已进 `plans/_index.md`)。
- **未做 / 遗留**: 未执行任何轮次(计划边界: 只定轮次不改码); 未做轮 00 的工具冒烟(pylint / jscpd 噪声阈值) —— 待起步轮确定后执行。

### 2026-10-11 R1 — Phase 0 + 轮 01–04(config 全包)

- **触发**: 用户「做 Phase 0/1: 26-10-10-2333-plan-dup-code-audit.html」; 追问下拍板范围 = **Phase 0 + 轮 01–04(config 全包)**(报告形态取计划默认: 一份滚动报告)。
- **Phase 0**: 工具冒烟通过(`uv run --with pylint` 4.1.2 / `npx jscpd`); 噪声阈值实测 —— pylint 全 src 仅 2 组(R0801, 均在 torrents)、config 包 0; jscpd 全 src python 0 clone、config 1 clone(writer.py)。**结论: config 字面重复极低, 印证计划预判(C 类为主, 工具仅提名)**。基线 hash `0d27b69e`。
- **轮 01 config/schema**(1478 行·6 文件): 提名主靠 grep; 发现 C2 / D3(R01-S01 枚举双份, R01-S02 `MAINTENANCE_TAG_MODES` 死件+内联+活件三份)。
- **轮 02 config/validation**(1358 行·5 文件): A2 / C3 / D4(R02-V02 端口校验三处逐字重复; R02-V03 时间窗两套; R02-V01 KNOWN_KEYS 15 组; R02-V05 STATE_ATTRS 报错硬编码串)。
- **轮 03 config 其余**(~1546 行): A3 / B1 / C3 / D2(R03-M01 默认值多源且 log.format 已漂移; R03-W01 writer 备份复制块 jscpd 命中; R03-L01 `_get` 被绕过; R03-P01 页面事实字面量; R03-I01/K01 段认领/R 级事实多处)。
- **轮 04 键面横切总账**: 一个键面 8 处表示(§07); **已实证漂移**: hr_check 键数 7/8/9、schema_version 4 vs "1"、log.format、UNLIMITED_SPEED 三态。
- **产物**: 滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html)(§01–§10); **7 条 refactor issue 入池**(专题 `dup-code-audit`): `config-schema-validation-enum-dup` / `config-default-multi-source` / `config-key-surface-doc-drift` / `config-writer-backup-copy-dup` / `config-validation-smallchecks-dup` / `config-loaders-get-inconsistency` / `config-site-preset-page-facts-dup`。另 3 条候选(点路径工具/段认领/B 类)登记报告 §08 未入池。
- **零改动确认**: 全程 `src/`、`tests/` 无变更; 仅新增报告与 issue 制品。
- **待办下一轮**: Phase 1 后端轮 05(core 调度内核 qbmanager·taskqueue·state·module); 或按用户偏好调整顺序。

### 2026-10-11 R2 — 轮 05–10(core 全包)

- **触发**: 用户「做 Phase 1 core部分」。
- **范围(拍板推定)**: Phase 1 后端 core 包 = 轮 05 调度内核(qbmanager·taskqueue·state·module) / 06 数据接入(qbapi·qbclient) / 07 流量(traffic_store·traffic_grid·curves) / 08 领域(episodes·tvshows·exporter) / 09 模块契约样板(跨 9 模块 + webui/hr module) / 10 模块业务(9 模块)。合计 ~8.1k 行 / 32 文件(+ 契约层样板)。
- **S2 提名实测**: pylint R0801(<code>=8</code>)对 core 0 命中(下探 <code>=5</code> 仅 1 组 modules/__init__); jscpd python <b>0 clone</b> —— 与 config 同结论(config/core 字面重复极低, 主战场是结构线索 + 精读)。
- **轮 05 内核**: A4(R05-M01 连接失败节流 3 份 / M02 重连成功 2 份 / M03 state 加载 2 份 / M04 ModuleHost hook 分发 2 份逐字同) + C1(state 原子写调用 2 份) + D3(服务委托属性对 / _throttle↔_wait_next / BaseModule 样板)。
- **轮 06 数据接入**: A1(R06-A01 `_kib` 2 份) + C1(R06-A02 KiB↔bytes+0=不限速 4+处, 且与 curves 取整方向分歧) + D1(透传 facade ~20 方法刻意显式)。
- **轮 07 流量**: A3(T01 读解析 4 处两两同构 / T02 追加建头 2 处 / T03 build_grid 分支 2 处) + B3(T04 差分两实现 / T06 解析骨架两套 / T07 加权聚合两实现) + C3(T05 原子写自实现 / C01 单位口径跨文件 / C02 v3 遗留 8 列兜底) + D1。
- **轮 08 领域**: C1(E01 分辨率/年份排除集同值两份) + B2(E02 集数正则族两份已演化 / E03 季标记两处) + D2(双入口包装 / 跨模块复用)。
- **轮 09 契约样板**: A2(C01 apply 段相等短路样板 4 模块 / C02 全局任务自注册样板 2 模块) + C1(C03 相位认领骨架) + D3。
- **轮 10 模块业务**: A11(G01 缺文件扫描触发 3 处 / G02 活跃下载谓词 2 处 / O01 实时复核 2 处 / O02 关块重开 3 处 / D01 两 delete-tags handler / D02 打标删标 3 处 / R01 事件分派 3 块 / R02 RuleContext 构造 3 份 / T01 块复位 8 行 2 份 / T02 agg 入账 / T03 catch-up) + C2(X01 <b>state 日键淘汰三处形态各异</b> / X02 计数器重置判据分层) + B1(X03 站点优先回落判定)。
- **产物**: 滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 追加 §08–§13(覆盖表 + 累计计数 §14 + core 候选排序); **9 条 refactor issue 入池**(专题 `dup-code-audit`)。
- **零改动确认**: 全程 `src/`、`tests/` 无变更; 仅新增报告与 issue 制品。
- **待办下一轮**: Phase 1 后端轮 11(hr 解析面 adapters·parse·bencode·fetcher); 或按用户偏好调整顺序。

### 2026-10-11 R3 — 轮 11–14(hr 全包)

- **触发**: 用户「做 Phase 1 hr 部分: 26-10-10-2333-plan-dup-code-audit.html」。
- **范围(拍板推定)**: Phase 1 后端 hr 包 = 轮 11 解析面(adapters·parse·bencode·fetcher) / 12 判定与序列化(resolve·status·model) / 13 运行面 A(service) / 14 运行面 B(runtime·worker·store·queue·channel·server·events·report·ratelimit·module·log)。合计 ~6.8k 行 / 23 文件。
- **S2 提名实测**: pylint R0801(<code>=6</code>)对 hr 收 2 组(ACTION_* 重导出 = 非重复; model↔status 展示字段镜像 = R12-D01); jscpd python <b>0 clone</b> —— 与 config/core 同结论(字面重复极低, 主战场是结构线索 + 精读)。
- **轮 11 解析面**: A3(parse_counters 逐字同 carpt↔btschool / ADAPTERS 工厂 lambda / fetcher URL 参数小助手) + C1(单位表 ↔ 跨包) + D2。
- **轮 12 判定与序列化**: A2(<b>model 9 个 dataclass 的 to_json/from_json 字段样板</b> / `_as_int/_as_float` model↔channel 逐字同) + C1(档位谓词) + D2(展示 DTO 镜像层 / SCHEMA_VERSION 别名)。
- **轮 13 运行面 A(service)**: A3(档位截断/失效骨架 3 处 / 告警去重一次骨架 3 方法 / 波级异常收尾样板 3 分支) + B1(各档摘要串两套, `(全深度)` vs `(全)`) + D2(`_release_record` 单点; **复核 issue `26-10-02-0441`(`_prune_index` 同体重复)已消除**)。
- **轮 14 运行面 B**: A4(`_scope_of` report↔fetcher 逐字同 / run_hr_* 三入口样板 / `stamp_text_ts` 死件 / 线程生命周期骨架) + C5(<b>站点派生多处</b> runtime↔report 逐字同 + webui routes/hr 四处 / <b>token 口径</b> hr↔webui 逐字同 / <b>读坏恢复链两套</b> hr/store↔core/state + infra/locking 单点未被用 / 告警节流窗口口径分散 4 处 / URL 分解口径) + D3(CLI 表格对齐单点 —— 计划预判「与 infra 表格工具重复」<b>不成立</b>; HTTP 头解析单点; 队列单点)。
- **产物**: 滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 追加 §14–§17(覆盖表 + 累计计数 §18 + hr 候选排序); **9 条 refactor issue 入池**(专题 `dup-code-audit`): `hr-adapter-parse-boilerplate-dup` / `hr-model-serialize-helper-dup` / `hr-lane-transition-boilerplate-dup` / `hr-warn-dedup-throttle-dup` / `hr-report-cli-boilerplate-dup` / `hr-store-recover-lock-family-dup` / `hr-token-persist-convention-dup` / `hr-site-derive-convention-dup` / `hr-thread-lifecycle-boilerplate-dup`。另 3 条候选(单位口径 / URL 分解 / 档位谓词)登记报告 §18 未入池。
- **零改动确认**: 全程 `src/`、`tests/` 无变更; 仅新增报告/issue 制品。
- **待办下一轮**: Phase 1 后端轮 15(webui/server: factory·context·auth·lifecycle·common·static_ui·traffic_qb + routes/*); 或按用户偏好调整顺序。

### 2026-10-11 R4 — 轮 15–16(webui 全包)

- **触发**: 用户「做 Phase 1 webui 部分: 26-10-10-2333-plan-dup-code-audit.html」。
- **范围(拍板推定)**: Phase 1 后端 webui 包 = 轮 15 路由层(factory·context·auth·lifecycle·common·static_ui·traffic_qb + routes/*, ~2282 行 · 20 文件) / 轮 16 表现层(runtime·views·commands·module, ~3851 行 · 4 文件)。合计 ~6.1k 行 / 24 文件。
- **S2 提名实测**: pylint R0801(`--min-similarity-lines=6`)对 webui <b>0 命中</b>(rate 10.00/10); jscpd python `10/70` <b>0 clone</b> —— 与 config/core/hr 同结论(字面重复极低, 主战场是结构线索 + 精读)。
- **轮 15 路由层**: A4(路由命令透传 handler 成对逐字同 + 11 份 build_router 头样板 / status 子字典双份 / 跳检 403 门控两处 / hr.py 前置守卫 5 处) + C3(token 口径复核 R14-T01 / state_file 同目录寻址 webui 3 处 / hr enabled-sites 派生 4 处 = R14-S01 webui 半) + D3(touch 心跳惯用式 / 单点已收敛件 / auth 安全单点)。
- **轮 16 表现层**: A5(runtime `_publish_partial_locked` 四段同骨架 / commands 成对 `_cmd_*` / `_bulk_*_via_ops` 聚合骨架 / reannounce 判定处置两处 / `_seed_view` 重述 `_member_view` 字段) + B2(search 行精度分歧 / 三桶集合处理三处) + C4(虚拟 tracker 前缀字面量 3 处绕过 infra 单点 / `_SHOW_STATE_RANK`↔JS STATE_RANK / `REANNOUNCE_BLOCKED_STATES`↔JS / ETA 哨兵 8640000↔JS) + D3(惯用式 / 剧键口径调用点 / 单点已收敛件)。
- **产物**: 滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 追加 §18–§19(发现清单)+ §20 累计计数/候选排序 + §21 issue 表; **10 条 refactor issue 入池**(专题 `dup-code-audit`): `webui-route-cmd-boilerplate-dup` / `webui-status-payload-dup` / `webui-hr-route-guard-dup` / `webui-sidecar-dir-convention-dup` / `webui-partial-publish-merge-dup` / `webui-cmd-pair-handlers-dup` / `webui-bulk-receipt-boilerplate-dup` / `webui-virtual-tracker-prefix-dup` / `webui-seed-view-restate-dup` / `webui-cross-layer-constant-convention-dup`。
- **零改动确认**: 全程 `src/`、`tests/` 无变更; 仅新增报告/issue 制品。
- **待办下一轮**: Phase 1 后端轮 17(rules/); 或按用户偏好调整顺序。

### 2026-10-11 R5 — 轮 17–19(rules / infra / torrents+tray+entry 全包)

- **触发**: 用户「做 Phase 1, 17-19部分: 26-10-10-2333-plan-dup-code-audit.html」。
- **范围(拍板推定)**: Phase 1 后端余下三包 = 轮 17 **rules/**(base·conditions·registry·checking_meta·actions/{basic,transfer,checking,full_checking,skip_checking}·expr/{lexer,parser,env,eval,types,errors}, 2187 行 · 18 文件) / 轮 18 **infra/**(utils·file_access·notify·logging·locking·versioning·autostart·errors, 2013 行 · 9 文件) / 轮 19 **torrents/ + tray/ + entry**(torrents 5 + tray 2 + cli/__main__, 1877 行 · 9 文件)。合计 ~6.1k 行 / 36 文件。
- **S2 提名实测**: pylint R0801(`--min-similarity-lines=6`) 对三面对收 **2 组**, 均在 `torrents/compat`↔`torrents/view` 字段列表(= R19-C01) —— 亦是全批唯一工具命中; rules / infra **0 命中**。jscpd python(`10/70`)对三面 **0 clone**(33 文件) —— 与 config/core/hr/webui 同结论(字面重复极低, 主战场是结构线索 + 精读)。
- **轮 17 rules**: A3(R17-A01 盘用量取数四处逐字同 / A02 数值谓词三处 / A03 动作 init 样板) + B2(no-HR 缺省语义两处 / AST 双类型检查) + C2(STATE_ATTRS 第三份=归 config issue / parser 死件运算符常量) + D3。
- **轮 18 infra**: A4(A01 fmt_speed↔fmt_size 阶梯 / A02 _win_user32↔_win_kernel32 惰性绑定 / A03 host 收集↔extract_tracker_hostnames / A04 文件三态探针两实现) + B1(parse_* 三族) + C4(C01 平台判定旁路单点[autostart 6 处 + tray·notify] / C02 sanitize↔mask URL 分解 / C03 数值强转=归 R12-M02 / C04 告警节流窗口=归 R14-T03) + D3。
- **轮 19 torrents+tray+entry**: A4(A01 notify↔tray icon 路径逐字同 / A02 cli 连接守卫 / A03 store 惰性缓存对 / A04 HR 判定入口守卫三处) + B2(view 量化↔webui / 两处基线刷新) + C3(C01 快照字段表↔视图字段表双份 / C02 平台旁路=归 R18-C01 / C03 ETA 哨兵=归 R16-C04) + D3。
- **产物**: 滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 追加 §20–§22(发现清单)+ §23 累计计数/候选排序 + §24 issue 表 + §25 变更记录; **11 条 refactor issue 入池**(专题 `dup-code-audit`): `rules-expr-disk-helper-dup` / `rules-expr-numeric-predicate-dup` / `rules-parser-dead-op-constants-dup` / `infra-fmt-ladder-dup` / `infra-win-dll-lazy-bind-dup` / `infra-utils-small-helper-dup` / `infra-platform-detect-bypass-dup` / `infra-url-decompose-dup` / `torrents-snapshot-view-field-dup` / `torrents-hr-entry-guard-dup` / `notify-tray-icon-path-dup`。三包 34 项发现(A11/B5/C9/D9), 全局累计 156(A58/B15/C40/D43)。
- **零改动确认**: 全程 `src/`、`tests/` 无变更; 仅新增报告/issue 制品。
- **待办下一轮**: Phase 2 前端轮 20(shared/*.js 非抽屉)。**Phase 1 后端(轮 01–19)至此全部走完**。

### 2026-10-11 R6 — 修复轮(hr 低风险子集, 5 条 issue 认领与修复)

- **触发**: 用户「修复 hr 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」→ 拍板**只做低风险高收益子集(5 条)+ 保守口径(无行为变化的收口)**。
- **产物**: 修 5 条 hr refactor issue 并置 `Done`(`hr-adapter-parse-boilerplate-dup` / `hr-report-cli-boilerplate-dup` / `hr-lane-transition-boilerplate-dup` / `hr-warn-dedup-throttle-dup` / `hr-model-serialize-helper-dup` 的强转助手部分); 余 4 条跨包/低收益件暂缓留 `Open`。档案 [26-10-11-backend-hr-dup-code-fix](26-10-11-backend-hr-dup-code-fix.md)。
- **执行注意(供后续修复轮复用)**: ① **报告的分类描述要复核, 不能照抽** —— 报告把档位处置三处判为 A 类「仅 detail 文案不同」, 实读发现 `fail_streak` 推进与升级告警三处各不相同, 照建议的 `_fail_or_truncate(st, detail)` 抽会**静默改行为**(给预算截断也计连续失效); 后续轮次对每个 A 类项都要**逐处比对行为**, 差异用显式参数承载。② **「口径收敛」先查值是否真相同** —— 报告建议把「6h 节流」收敛成单点, 但 4 处窗口值不同(且 worker 侧有 16 条单测按模块常量打补丁)⇒ 只抽算法、阈值留各模块常量。③ **删死件前先查测试引用** —— `stamp_text_ts` 生产侧零调用但有自己的单测, 删件须连带删测试与「测试计划」清单行。
- **零改动确认**: 改动面仅 hr 包内 9 源文件 + 1 测试文件; 跨包(webui/core/infra)零改动; `config.yml` / `auto-qb-data/` 未触碰。
- **待办下一轮**: hr 余 4 条暂缓件按各自轮次处理; 重复代码审查主线(Phase 2 前端 20–23 / Phase 3 测试横切 24–25 / Phase 4 汇总 26)仍未开工。

### 2026-10-11 — webui 修复轮(认领 7 条 issue)

- **触发**: 用户「修复 webui 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」(追问拍板: 新建修复轮档案作认领方 + 先做低风险 7 条)。
- **认领与结果**: 见修复轮档案 [26-10-11-webui-dup-code-fixes](26-10-11-webui-dup-code-fixes.md) —— 7 条置 `Done`(行为逐字不变 + 5 条新守阵过红验), 3 条留 `Open`(热路径 merge / 跨层常量 / 路由表驱动)。

### 2026-10-11 R7 — 修复轮(rules 全包, 3 条 issue 认领与修复)

- **触发**: 用户「修复 rules 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」。
- **范围**: 报告 §20(轮 17 rules)入池 3 条 refactor issue —— 全部在包内、报告均标「风险低」, 故**全做**(无跨包暂缓件, 与 R6 的 hr 子集不同)。
- **产物**: 修 3 条并置 `Done`(`rules-expr-disk-helper-dup` 收 `env.disk_usage_value` / `rules-expr-numeric-predicate-dup` 收 `types.require_number` / `rules-parser-dead-op-constants-dup` 删死件), 新增 3 个守阵测试。档案 [26-10-11-backend-rules-dup-code-fix](26-10-11-backend-rules-dup-code-fix.md)。
- **执行注意(供后续修复轮复用)**: ① 报告口径仍需逐处复核 —— R17-A01 条件侧原只捕 `OSError`、env 侧捕 `(OSError, ValueError)`, 取超集后对条件侧是不可达路径的防御性放宽(实测两实现不抛 `ValueError`), 行为等价; ② 「文案逐字不变」是保守口径的关键 —— 三处数值校验文案不同, helper 用 `what` 参数承载主体短语而非硬编一种; ③ 收口后**清未用导入**(conditions 的 `file_access`)。
- **零改动确认**: 改动面仅 rules 包内 5 源文件 + 1 测试文件; 跨包零改动; `config.yml` / `auto-qb-data/` 未触碰。
- **待办下一轮**: infra 轮 18 的 5 条 issue 仍在 `Open`, 属后续修复轮候选; 重复代码审查主线(Phase 2 前端 20–23 / Phase 3 测试横切 24–25 / Phase 4 汇总 26)仍未开工。
### 2026-10-11 R8 — core 批次 9 条 issue 实施(用户「修复core部分问题…相关issue一并认领」)

- **触发**: 用户指名按报告 `26-10-11-0033` 修复 core 部分, 相关 issue 一并认领。9 条 `26-10-11-0207-refactor-core-*` 全部 Open → In Progress → **Fixed**(状态变更日志逐条留痕)。
- **实施口径**: A/C 类抽单点收敛; B 类按计划「只登记」口径加互指注释不合并。逐条:
  - **R05 qbmanager**: 抽 `_note_conn_failed/_note_conn_ok/_reload_state` 三私有方法, connect()/run()/__init__ 七个调用点归一。⚠初版命名 `_load_state` 撞**别名冻结守阵**(`test_qbmanager_alias_freeze`: 退役 forward 成员名禁复活)红验, 改名 `_reload_state`; 接线守阵 `test_state_migration_materialize_is_wired_in_run` 同步改锚 `_reload_state()`(意图不变: 物化在加载后)。
  - **R10 日键淘汰**: `state.prune_day_keys(d, today, keep_days, date_of)` 单点 —— 三形态(键即日期 / 值字段 date / 值即日期)由 `date_of(key, value)` 声明; ops skip_check_day 的「只留当日」= keep_days=0 特例(理论行为差: 未来日期不再被删, 实际写入只产当日)。
  - **R08 集数标记**: 排除集单点 `episodes.RESOLUTION_EXCLUDE`(tvshows `_BARE_EXCLUDE` 引用之, tvshows 顶部补 `from . import episodes`, 无环); 集数/季标记正则族 B 类互指注释(episodes 是 tvshows 超集的子集, 评估复用后再定)。⚠注释初稿函数名 `_derive_from_directory` 系臆测, 已按实改 `parse_files`。
  - **R05/R09 模块契约**: ModuleHost 抽 `_iter_hooks`(「有则调用, 无则跳过」getattr 单点; run_command_line 保留全量循环**不短路** —— any() 会跳过后续模块命令消费); BaseModule 增 `apply_section`(段相等短路 + 回执骨架; logging/notify 接入, tracker(双短路原因)/rules(复合谓词)保持显式并注明缘由)与 `register_global_tasks`(自注册骨架; speed_curve/maintenance/traffic_sample 三处接入, 「创建全局任务 N 个」日志格式三处原已一致由单点承载); module.py 新增 `from .taskqueue import Task` 运行时导入(taskqueue 无反向依赖, 无环)。
  - **R10 ops/grouping**: grouping `_scan_triggered_groups`(缺文件扫描触发骨架 ×3)+ `_is_active_download`(谓词 ×2); ops `_live_recheck`(R1/R2 实时复核样板, 日志行逐字节保持, 调用方 isinstance 分流 ActionResult); traffic_sample `_close_block_and_reopen`(关块重开 ×3, reset_log 参数化计数器重置审计行 —— ⚠issue 位置笔误标成 ops_mod, 实际全在 traffic_sample_mod, 按 grep 事实落点)。
  - **R10 maintenance/rules/sample**: maintenance `_apply_tag_changes`(标签动作 ×3)+ `_purge_matched_tags`(两 handler, select 回调声明命中判据, tag_usage 调用时序保持); rules `_make_ctx`/`_run_rule`(RuleContext+process+except ×3, 日志前缀参数化)+ `_dispatch_trigger_rules`(分派内层 ×4, deleted 路径 snapshot 透传); traffic_sample `_reset_block`(复位 8 字段 ×2)+ `_ingest_acc`(hour/day 累计器并入骨架, cascade 闭包承载翻桶差异 —— **落批 append(row) 时序保持原序**, 防文件行序漂移)+ `_catch_up_level`(day/month catch-up 同构, 三元组返回避 setattr)。
  - **R06/R07 速度单位**: curves 增「速度单位换算单点」段 —— `kib_to_bytes`(0=不限速)与 `bytes_to_kib`(曲线目标, 半值向上)/`bytes_to_kib_floor`(读回现值, 整除向下)显式双函数钉死取整方向; qbapi 6 处消费, 局部 `_kib` ×2 退役。
  - **R07 traffic_store/grid**: 模块级 `_read_parse(path, parser, empty)`(读解析告警纪律单点, 缓存层两个静态壳退役直调)+ `_ensure_file_prefix`(建头/撕裂尾查补单点); traffic_grid `_floor_buckets`(raw/hour 桶序列单点)。
  - **R07/R10 traffic 解析差分层(B/C)**: 按建议只登记 —— parse day↔agg 骨架互指、series_totals_points↔v4_totals_points 互指、v4_hour_agg↔v4_rollup_agg 互指、「cur < last 判重置」三层(采样器/视图/解析)互指注释。
- **测试**: 每项任务后 `test.quick` 全绿; 收口 `test.full` **3113 passed + 4 skipped / TOTAL 99%**(基线切片 `26-10-11-1630-core-dup-code-fixes`); 全部改动文件过 `dev.fmt`。
- **待办**: Phase 2 前端轮 20(shared/*.js 非抽屉); webui/hr/rules/infra/torrents/config 各批 issue 实施另开会话。
