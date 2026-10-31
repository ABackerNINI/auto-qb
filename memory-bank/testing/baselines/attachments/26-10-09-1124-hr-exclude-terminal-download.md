# 2842 —— HR 排除种子终态行身份下载短路 (计划 26-10-09-1057 / issue 26-10-08-1304)

> 摘要: 名称候选面收窄为「受管集」后的收尾基线。改动 1 个源文件 2 处(`hr/service.py`: `_WaveContext` 名称面派生 `local_names` → `local_names_managed` + `_row_looks_local` 数据源), 新增守阵 4 条 + 调整既有 S3-2 断言 1 处(3 条红验确认)。命中面 `local_hashes` 逐字未动。全量套件与文档守卫全绿。
> 档案: memory-bank/tasks/26-10-09-backend-hr-exclude-terminal-download.md
> 基线时间: 2026-10-09 11:24

**Refs:** memory-bank/tasks/26-10-09-backend-hr-exclude-terminal-download.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2842 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 35.98s(命令墙时 38.0s)
- **新增用例 4 条**: `tests/test_hr_service.py`(名称候选面派生 / 终态行只命中排除种子零下载 / 同时命中排除+受管仍下载 / A 档命中排除种子仍无条件下载) + 调整既有 `test_excluded_anchor_still_counts_as_local_hit` 断言 1 处。
- **红验**: 临时去掉名称面的排除位过滤(`and not a.excluded`)后, 3 条转红(核心钉 + 派生 + S3-2 断言), 还原复绿 —— 证守卫非恒真。

## 说明

- **相对上基线的参考**: 要看差值跑 `commands run kb.baseline -n 2`。
- **代码事实变更**: 有 —— `_WaveContext.local_names`(全量名) → `local_names_managed`(受管名, `not a.excluded`); `_row_looks_local` 数据源随之。`local_hashes` 命中面与 A 档硬规则不变。
- **正确性依据**: 粗配宽松(`FUZZY_NAME_K=12`), 同一行可能同时命中排除与受管种子(同剧不同集/季); 用**收窄候选集**而非「命中排除名即 return False」(后者会漏下受管种子身份)。见计划 26-10-09-1057 §03.3。
