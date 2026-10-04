# 基线切片 26-10-05-0209 — HR 已放行记录不覆写守阵 (issue 26-10-02-0526 认领)

> 摘要: 认领 issue 26-10-02-0526 (`_sign_releases` 批量签发对已 verified 的 infohash 不查重,
> `data.verified[h] =` 直接整条覆写)。复验仍复现(代码层); 可达性核实为**当前代码全路径不可达**,
> 按 §06② 补两层守阵钉住「unmatched 不含已 verified infohash」前提, src/ 零改动。
> 基线时间: 2026-10-05 02:09

**Refs:** memory-bank/issues/26-10-02-0526-bug-hr-sign-releases-verified-overwrite.html, memory-bank/activeContext/26-10-05-0210-hr-verified-overwrite-guard.md

- 分支: develop @ b7db4472 (+ 本轮未提交改动: tests/test_hr_service.py / issue HTML / 本切片)
- 命令: `commands run test.full`(Windows, 两次采样)
- **实测 (Windows)**: **2540 passed + 4 skipped, 27.60s / 27.52s, 覆盖率 TOTAL 99%**
  (14871 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向 (tests/test_hr_service.py): `test_build_objects_unit_guards`(扩展: 已 verified 未漂移不回对象集)
  + `test_verified_record_not_overwritten_on_rewave`(新增: 已放行未漂移跨波记录逐字段原样 + 零二次签发),
  2 passed。红验: 探针摘除 `_build_objects` 的 `if ver is not None: continue` 排除分支,
  两条全红(单元断言红 + 波次级 `releases_signed == 1` 抓到二次签发); 恢复后整文件 84 passed。
- 相对上基线 (26-10-05-0143: 2538 passed + 4 skipped / 99% / 31.49s): passed **+2** =
  本轮新守阵 1 条(test_build_objects_unit_guards 扩展不加数) + **存量偏差 1 条**(HEAD 实测收集
  2543 = 2539 passed + 4 skipped, 上基线记录 2538; 该偏差早于本轮存在, 近五笔提交均无
  parametrize/隐藏用例扩展, 来源未逐笔追溯)。skip 集合不变 (Windows 侧 4 条 POSIX 专属)。
- 改动面: tests/test_hr_service.py(+1 新守阵 / 扩展 1 条 / docstring 测试计划同步 2 处),
  生产代码 src/ 零改动。
