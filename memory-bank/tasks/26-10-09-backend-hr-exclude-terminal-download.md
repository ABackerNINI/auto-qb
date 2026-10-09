# 26-10-09-backend-hr-exclude-terminal-download — HR 排除种子终态行仍下载 .torrent (无谓请求)

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 11:24
**Topics:** hr-steady-throttle
**Summary:** 认领并修复 issue 26-10-08-1304(计划 26-10-09-1057)。B/C/D 终态行(无 infohash)按名称粗配**只**命中「已被 HR 排除」的本地种子时, 原实现仍会取一次 `.torrent` —— 而排除种子无对账义务、判定侧已短路, 该身份**无任何消费方**。修法 = 把身份下载触发器的**名称候选面**从「全量本地种子名」收窄为「受管(未排除)种子名」(`_WaveContext.local_names` → `local_names_managed`), `_row_looks_local` 换数据源。命中面 `local_hashes` 与 A 档「考察中无条件下载」硬规则**逐字不动**。改动 1 源文件 2 处 + 守阵 4 条(3 条红验)。
**Refs:** memory-bank/plans/26-10-09-1057-plan-hr-exclude-terminal-download.html,memory-bank/testing/baselines/26-10-09-1124-hr-exclude-terminal-download.md,memory-bank/activeContext/26-10-09-1124-hr-exclude-terminal-download.md

## 原始请求

> 用户(2026-10-09): 「认领 issue 26-10-08-1304, 先写一个实施计划」→ 计划入库并拍板后「实施计划」(落地)。

## 思考过程与决策

- **本轮 = 执行任务**(产出计划 → 落码 → 守阵 → 收尾), 命中立档阈值 #4(产出计划文档)⇒ 立档 + 收尾 DoD; 未 commit(需用户「提交」)。
- **动「名称候选面」而非「命中面」**: 名称面唯一用途 = 终态行的身份下载触发器(启发式), 从不参与定论(定论一律 infohash 精配)。排除种子不值得花一次请求查身份 ⇒ 从候选面移除零判定损失; 而 `local_hashes` 是「排除 ≠ 不认识」的实质载体, 必须保持全量。
- **实现形态是约束不是分叉**(评审纠正, 曾误设为拍板点 D2): 粗配宽松(`FUZZY_NAME_K=12`, 标题重合 ≥12 字符即命中)⇒ 同一行可**同时**命中排除与受管种子(同剧不同集/季, 实测确认)。故只能**收窄候选集**(命中任一受管名即下载), **不能**写成「命中排除名即 return False」(会漏下受管种子身份; 漏管束 > 多一次请求)。已从「拍板点」降为设计注记。
- **D1 采纳推荐**: 收窄/改名(`local_names` → `local_names_managed`)而非新增并存 —— 全量名改后全域零消费方, 保留即死代码。

## 实现计划

- **S1** 判据收窄(`hr/service.py`: `_WaveContext` 名称面派生 + `_row_looks_local` 数据源)。
- **S2** 守阵(`tests/test_hr_service.py` 4 条 + 调整既有 S3-2 断言 1 处 + 头部测试计划清单)。
- **S3** 文档回写(`resolve.py` 注释 / `service.py` docstring / `modules/overview.md` / 上游计划偏差指针)。
- **S4** 收尾(基线切片 + issue/计划状态 + `kb.index`)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 名称候选面收窄为受管集 | Done |
| S2 | 守阵 4 条 + 调整 S3-2(3 条红验确认) | Done |
| S3 | 文档回写(resolve / service / overview / 上游计划指针) | Done |
| S4 | 收尾(基线 + 索引 + issue/计划状态) | Done |
| — | 真机复核(可选, 用户侧: 观察日志不再为排除种子终态行取 .torrent) | Open |

## 进度日志

- **2026-10-09 11:24** 实施轮落地: **S1** `hr/service.py` `_WaveContext` 名称面由 `local_names`(全量)改为 `local_names_managed`(`not a.excluded`) + `_row_looks_local` 换数据源(+ docstring 写清「收窄候选集 ≠ 提前返回」的形态约束与 A 档边界); **S2** `tests/test_hr_service.py` 新增 4 条 + 调整 `test_excluded_anchor_still_counts_as_local_hit` 的名称断言, 头部「测试计划」登记; **红验** = 临时去掉 `and not a.excluded` → 3 条转红(核心钉/派生/S3-2 名称断言), 还原复绿; **S3** 回写 `resolve.py:53` 注释、`service._build_objects` docstring、`memory-bank/modules/overview.md` 的 HR 行(「仍留命中集 local_hashes/local_names」→「仍留命中面 local_hashes; 名称候选面已收窄」), 并在计划 26-10-08-1249 §08 追一行偏差指针(其 §7.2「local_names 全量」被本项有意修正); **S4** 基线切片 + `kb.index`。`test.full` 与 `kb.check` 全绿(数字见 `commands run kb.baseline`)。
- **2026-10-09 11:13** 评审修正: 用户质询 D2 —— 取消该拍板点(「同一行同时命中」不是分叉而是形态约束), 实证该情形确可发生(粗配宽松), 计划 §05 只留 D1、§03.3 补实证注记。
- **2026-10-09 10:57** 认领 issue 26-10-08-1304(`Open → In Progress`, 认领方 = 计划 26-10-09-1057); 运行时复验现象仍复现; 计划入库。
