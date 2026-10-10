# 26-10-10-backend-dup-code-audit — 全仓重复代码审查(分步执行计划)

**Status:** In Progress
**Added:** 2026-10-10
**Updated:** 2026-10-11
**Topics:** dup-code-audit
**Summary:** 用户要求「做一轮重复代码审查, 主要用于后续的重构, 增强一致性与减少维护点; 先写一个分步执行方案(先分析后端哪一部分 config? core?), 避免单轮任务过长」, 追问下选定**正式 HTML 计划 + 全仓范围(含前端三皮肤)+ 步骤拆细**。本轮**只产出计划制品, 零代码改动**: 计划 `plans/26-10-10-2333-plan-dup-code-audit.html`(专题 `dup-code-audit`, 状态 `Open` 待拍板)。计划含四类判定口径(A 真重复 / B 分歧重复只登记 / C 同一事实多表示 / D 表面相似不动) + 两段式方法(机器提名 pylint R0801 / jscpd → 人工定性) + **27 轮分步清单**(准备 → 后端 19 → 前端 4 → 测试与横切 2 → 汇总, 一轮一面独立会话) + 每轮六步微步骤 S1–S6 + 硬停手点(只审查不改码 · 单轮 ≤4000 行 · B 类只登记)。〔26-10-11 执行轮〕用户「做 Phase 0/1」→ 已完成 **Phase 0 + 轮 01–04(config 全包)**; 用户「做 Phase 1 core部分」→ 已完成 **轮 05–10(core 全包: 内核 / 数据接入 / 流量 / 领域 / 模块契约样板 / 模块业务)**, 累计 46 项发现(A21/B6/C9/D10), 入池 core 9 issue。全程纯审查轮, 零源码改动。
**Refs:** memory-bank/activeContext/26-10-10-2356-dup-code-audit.md,memory-bank/activeContext/26-10-11-0207-dup-code-audit.md,memory-bank/testing/baselines/26-10-10-2356-dup-code-audit-plan.md,memory-bank/testing/baselines/26-10-11-0033-dup-code-audit-config.md,memory-bank/testing/baselines/26-10-11-0207-dup-code-audit-core.md,memory-bank/reports/26-10-11-0033-report-dup-code-audit.html

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
| S5+ | 逐轮执行 Phase 0 → Phase 4(轮 00–26, 每轮独立会话)—— 已完成 Phase 0 + 轮 01–04(config 全包) + 轮 05–10(core 全包) | In Progress |
| S6 | 轮 26 汇总: 重构候选排序表 + 跨层「同一事实」总账 + 可动项入池 | Open |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| 计划落盘 | Done | `plans/26-10-10-2333-plan-dup-code-audit.html`(dark · `doc-topic=dup-code-audit` · `Open`) |
| Phase 0 准备(轮 00 工具与口径) | Done | 工具冒烟 + 口径固化 + 建档 + 基线 `0d27b69e`; 见报告 §03 |
| Phase 1 后端(config 轮 01–04) | Done | 报告 §04–§07; 入池 7 issue(refactor) |
| Phase 1 后端(core 轮 05–10) | Done | 报告 §08–§13; 入池 core 9 issue; 46 项发现(A21/B6/C9/D10) |
| Phase 1 后端(轮 11–19: hr / webui / rules / infra / torrents+tray) | Open | 未开工 |
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