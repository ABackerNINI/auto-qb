# 2817 —— HR 排除落到取数侧 (方案 B) 实施 S1–S4 (计划 26-10-08-1249)

> 摘要: 方案 B 落码 + 守阵 4 条 + 文档回写后的收尾基线。改动 3 个源文件(`hr/resolve.py` 加 `HrAnchor.excluded` / `torrents/record.py` `hr_anchor()` 透传 / `hr/service.py` `_build_objects` 第四档排除), 新增守阵 4 条(3 条红验确认)。全量套件与文档守卫全绿。
> 档案: memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md
> 基线时间: 2026-10-08 13:07

**Refs:** memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2817 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16479 语句 / 162 未覆盖 / 5696 分支 / 146 partial; 门槛 98% 达标)
- **耗时**: 46.63s(墙时 49.0s)
- **新增用例 4 条**: `tests/test_hr_service.py` 3 条(对象集跳过 / 稳态降频恢复 / 命中识别保留) + `tests/test_torrents.py` 1 条(锚点快照带排除位)。
- **红验**: 临时关掉两处源码钩子后 3 条转红(第 4 条是设计锁, 方向相反不随本改动红), 还原复绿 —— 证守卫非恒真。

## 说明

- **相对上基线的参考**: 与 [26-10-08-1253](26-10-08-1253-hr-exclude-steady-plan.md) 同池 +4 用例; 要看差值跑 `commands run kb.baseline -n 2`。
- **代码事实变更**: 有 —— `HrAnchor` 结构(冻结 dataclass)末尾加 `excluded: bool = False`; 不参与放行记录快照/漂移比对, 既有全量相等断言与关键字构造不受影响。
