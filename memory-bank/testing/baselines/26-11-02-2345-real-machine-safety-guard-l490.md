# 4899 passed + 2 skipped(根) —— RM04-05 L490 真机前置改为显式入口与安全守卫(全量基线)

> 摘要: RM04-05 L490 真机前置改为显式入口与安全守卫(全量基线)
> 基线时间: 2026-11-02 23:45
**Refs:** memory-bank/issues/26-11-02-1208-bug-rm04-gate-space-crossvol-branch-missing.html

## 验收数字

命令: `commands run test.full`

汇总行: `4899 passed, 2 skipped, 3 warnings in 158.79s (0:02:38)`

TOTAL 表: `22523 134 7728 128 99%`(stmt / miss / branch / brpart / cover); `Required test coverage of 99.0% reached. Total coverage: 99.11%`

口径注记: 全量套件(根 `tests/` + 各子包), 8 并发 worker; 新增 `tests/test_real_machine_safety.py` 4 条已计入。上一轮同代码面(索引重建前)的失败轮为 `3 failed, 4896 passed`, 失败仅为 KB 文档日期/生成物漂移, 修正后本轮全绿。

## 本改动面

- `tests-real/lib/small_target.py`(新增): 显式入口 `QBT_REAL_SMALL_TARGET` + `assert_safe_target` / `require_small_target` 硬守卫(拒 UNC/卷 GUID、无盘符、非绝对、非已存在目录、系统卷、Recovery/System/EFI 类卷标、路径 hidden/system/reparse point、`st_dev` 跨卷); 前置缺失或剩余 ≥ needed 时显式断言失败并给准备指引。
- `tests-real/rm04_relocate/test_rm04_relocate.py`: 删除 `_volume_roots()` / `small_volume_junction()`(隐藏卷枚举与 junction 暴露); L490 段改走 `small_target.require_small_target()` 并移到主链之后(前置缺失只红该段)。
- `tests/test_real_machine_safety.py`(新增): 扫描 `tests-real/` 源码禁止 `FindFirstVolumeW/FindNextVolumeW`、卷 GUID 字面量、旧构造函数名; 守卫路径拒绝/缺 env 指引/卷标关键词 4 条。
- 文档: issue `26-11-02-1208`(§02/§05/§06/§07 改写为「曾用过、已废弃并移除」)、`memory-bank/testing/real-machine.md` §2.9(安全构造配方)、`memory-bank/testing/real-baselines/26-11-02-2243-real-RM04-05.md`(顶部废弃声明)。
- 产品代码 `src/` 零 diff。
