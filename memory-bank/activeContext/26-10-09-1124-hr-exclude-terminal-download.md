# HR 排除种子终态行身份下载短路 · 已闭环

> 摘要: 用户指派「认领 issue 26-10-08-1304, 先写实施计划」后下令实施。被排除 HR 的本地种子在 B/C/D 终态行按名称粗配命中时, 原实现仍会取一次 `.torrent`(浪费站点日额/频控), 而该身份对排除种子**无任何消费方**(判定侧已短路)。修法 = 身份下载触发器的**名称候选面**从「全量本地名」收窄为「受管(未排除)名」(`_WaveContext.local_names` → `local_names_managed`, `_row_looks_local` 换数据源); `local_hashes` 命中面与 A 档「考察中无条件下载」硬规则**逐字不动**。评审中把「同一行同时命中排除与受管种子」从拍板点降为**形态约束**(粗配宽松 K=12, 同剧不同集/季会互相命中 ⇒ 只能收窄候选集, 不能「命中排除名即 return False」)。
>
> 最后活动: 2026-10-09 11:24

**Refs:** memory-bank/tasks/26-10-09-backend-hr-exclude-terminal-download.md,memory-bank/testing/baselines/26-10-09-1124-hr-exclude-terminal-download.md

## 本轮完成

- **复验先行**: 运行时直取 `_WaveContext` + `_process_rows` 确认现象仍复现(排除种子仍在名称面 ⇒ 终态行入 `pending_downloads`)。
- **源码**: `src/auto_qb/hr/service.py` —— `_WaveContext` 名称面派生 `local_names` → `local_names_managed`(`not a.excluded`); `_row_looks_local` 换数据源 + docstring 写清形态约束与 A 档边界。1 源文件 2 处, 净增约 2 行。
- **守阵**: `tests/test_hr_service.py` 新增 4 条(派生 / 只命中排除种子零下载 / 同时命中排除+受管仍下载 / A 档仍无条件下载) + 调整既有 S3-2 名称断言 1 处; **红验** 3 条转红。
- **文档回写**: `hr/resolve.py` 注释、`service._build_objects` docstring、`memory-bank/modules/overview.md` HR 行、上游计划 26-10-08-1249 §08 偏差指针。
- 实测数字见 `commands run kb.baseline`。

## 待办 / 移交

- **真机复核(可选, 用户侧)**: 观察站点日志不再为「命中排除表的本地种子终态行」取 `.torrent`(收益 = 省站点日额/频控)。
