# 2662 —— Playwright 整合提交后的合并态复验 (e6db1fab)

> 摘要: 上一条基线记的是 `37c427fe` + 未提交改动时的 2647, 而提交走的是**提交先行 → 提交后 rebase**
> ⇒ 提交 e6db1fab 落在 9 个远端提交**之后**, 合并态的数字没被任何基线覆盖("最新一条 = 单点事实源"
> 的语义下会误导)。本切片补上这个空档: 合并态实测 **2662 passed + 4 skipped / 99%**,
> 多出的 +15 全部来自合并进来的远端提交, 与本次 Playwright 改动无关。
> 基线时间: 2026-10-06 05:47

**Refs:** memory-bank/activeContext/26-10-06-0508-playwright-e2e.md

- 分支: develop @ **e6db1fab**(工作树仅 `M TODO.md` 未提交 —— 用户明确要求不提交它)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2662 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 两次采样: **64.45s / 72.45s**(引擎 66.1s / 74.2s) ⇒ 耗时区间约 **64~74s**。
  - 语句 15952 / 分支 5444 **两次一致**; 未覆盖 **163~166**、partial **143~144**
    —— 并行执行下有 ±3 抖动, **不是回归**(passed 两次恒为 2662)。
- 相对上一条基线 [26-10-06-0508](26-10-06-0508-test-playwright-e2e.md)
  (2647 passed + 4 skipped @ 37c427fe + 未提交, 15921/170/5444/144):
  passed **+15**, 语句 15921 → 15952(+31), 未覆盖 170 → 163~166, 分支 5444 → 5444(±0),
  partial 144 → 143~144。
- ⚠ **这 +15 全部来自合并进来的 9 个远端提交**, 不是本次 Playwright 改动 ——
  `2cb72adb` 与 `0b69cd49` 的提交信息自报 `(test.full 2648+4)` / `(test.full 2662+4)`, 与实测吻合;
  本次 Playwright 改动(CI 配置 / e2e / 文档 / `.commands/` 包)**未增删任何 Python 用例**。
- 旁证(同批核过): 闸门(`test.quick` + preflight)是在 **rebase 之前**跑的, 合并态未经闸门 ⇒
  本条即对该态的全量复验; `kb.check` 全绿(主键纪律 + 认领链双向闭环); `doc.drift` 0 处;
  远端 ref 经 `git ls-remote` 核实 == 本地 HEAD。
