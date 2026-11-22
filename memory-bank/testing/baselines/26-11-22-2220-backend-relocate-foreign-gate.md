# 7009 passed, 6 skipped —— relocate foreign 面既有漂移行清偿与覆盖缓冲加厚全量基线

> 摘要: relocate foreign 面既有漂移行清偿与覆盖缓冲加厚全量基线
> 基线时间: 2026-11-22 22:20
**Refs:** memory-bank/tasks/26-11-22-backend-relocate-foreign-gate.md

## 验收数字

`commands run test.full` 实测(2026-11-22, Windows, rc=0, 146.0s, 树 = e0802699 + 本轮未提交件, 分支 develop):

```
TOTAL                                                31412    108  11190     93    99%
7009 passed, 0 failed, 6 skipped
Required test coverage of 99.5% reached. Total coverage: 99.50%
```

全绿 rc=0(测试 7009P/0F/6S, 覆盖率过 Windows 线 99.5, tests/conftest.py `COVERAGE_FLOOR_WIN = 99.5`)。精确覆盖率(coverage JSON; 改善后两次独立实测恒同) = (31304 行 + 11089 弧) / (31412 + 11190) = **99.50941%**(缺失 108 行 + 101 弧 = 209 单元; 对 99.5 闸余量 4 缺失单元, 约 2 行当量)。与上基线(26-11-22-2035, 7000P/6S, miss 109/BrPart 94, 精确 99.50007%)相比: passed 7000→7009(池序抖动修复批 +8 已随 e0802699 入库, 本轮漂移行清偿 +1); 本轮净清偿 = 1 行(relocate_foreign.py:818)+ 1 弧(817->818) —— 同测试集(减本轮新测试)仲裁实测 miss 109/缺失弧 102 = 99.50472%, 缓冲余量 2→4 缺失单元加厚。口径注: 昨夜收尾轮对 7008P 态实测 99.50007%(缺失弧 104), 与本轮同态仲裁(102)差 2 缺失弧 = 套件既存轮间抖动面(±2 单元, 约 0.005pp; 本轮改善后侧两次实测恒同未见抖动), 非本改动引入。

## 本改动面

本轮 = relocate_foreign 面全量 missing 的既有漂移行清偿(只动 tests/, 零 src 改动):

- tests/test_relocate_foreign.py 新增 test_foreign_restore_location_guard_arms_no_overwrite: 空位回填守卫面钉测(relocate_foreign.py:818 守卫臂三支)—— 回填只补空: 条目已有位置不被外来 hit 覆盖/场景 A hit 不回填/hit 无位置静默; 文件头部「测试计划」docstring 同步; test_foreign_pending_vanish_skipped 内注释漂移顺带修(「池余 5(V10..V14)」改序无关如实表述, 断言零改动)。
- 全量 missing 明细(pre = 勘察/实测 257, 326, 403, 818; post = 257, 326, 403): 818 已清偿; 257/326(`_norm` 守卫, `normpath` 对任意 str 输入恒非空, 最小返回 ".")与 403(池溢出循环前提 `len>=1001` 下 `next(iter(...))` 不可能 None)为不可达防御行, 判定不硬凑不删改 —— relocate_foreign 面全量可达 missing 清零。
- 记账文档旧 hash 引用校正(rebase 改写提交链): tasks/26-11-22-backend-relocate-foreign-gate.md、baselines/26-11-22-2035-backend-relocate-foreign-gate.md、active-context/26-11-22-0536-backend-relocate-foreign-gate.md 三件按映射更新(c03f09e0→153d7c3e/7e56f8c4→4a51f60a/f1cd83bb→0a88e51a; 213fbc9d 引用按事实改述「原独立小提交, 后经 rebase 撤销 —— 同一修复已由远端 8763ca51 顺带落地」), grep 残留零。
- passed/skipped/覆盖率数字自本切片起以本切片为权威。
