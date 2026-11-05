# 5392 passed + 2 skipped in 140.72s (TOTAL 24483 stmts, 99% cover, 57 miss; 评审修复轮 c9a190d2 后) —— 版本管理机械化评审修复轮全量基线

> 摘要: 版本管理机械化评审修复轮全量基线
> 基线时间: 2026-11-06 02:36
**Refs:**

## 验收数字

- 汇总行: **5392 passed + 2 skipped** in 140.72s(0:02:20, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 24483 stmts / 57 miss / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 上轮基线(2026-11-05 会话)5381 passed; 本轮 +11 = 决策器守阵 25→34(+9: 空区间/错误路径/无 tag 指引/草稿透出/JSON 合流/捕获组校验等评审修复用例) + 版本守阵 5→7(+2: bumpversion 接线守阵/元数据兜底)。全绿无 fail, 副作用越界 0(test.quick 复核 39.6s 同数)。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- 评审修复轮(基线 commit c9a190d2, 计划 26-09-22-2318 v2 阶段 1 S0-S5 收口评审, 分面档 14 发现全修):
  - `.agents/skills/release/scripts/suggest_bump.py`: breaking 判定严格大写化(R1-F1)/无 tag 停手指引可达(F2)/--json 含 changelog 草稿字段(F3)/except 收口 re.error+OSError(F5)/捕获组个数强制(F6)/stdout 锁 UTF-8(F7)/Breaking 标题去 ⚠️(F8)。
  - `pyproject.toml`: 零改动(评审仅加守阵)。
  - `src/auto_qb/cli.py`: 零改动(评审仅加守阵)。
  - `tests/test_release_suggest_bump.py`: 25→34 条(新增 main 错误路径契约/空区间重入/JSON 合流/捕获组/前导空格等)。
  - `tests/test_version_guard.py`: 5→7 条(+bumpversion 接线守阵 commit/tag=False+current_version 同步+占位符在位; +元数据缺失兜底)。
  - `memory-bank/plans/26-09-22-2318-version-management-plan.html`: §6.2 步骤③补「bump 后即刷打包元数据(用 `commands run env.sync`)」(R1-F4)。
