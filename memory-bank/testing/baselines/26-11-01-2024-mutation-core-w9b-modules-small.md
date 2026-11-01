# 4653 passed + 2 skipped(根) —— core W9b R34 变异审计: rules+modules 小件 6 文件 S6 同池复跑(1,442 变异, 杀死率 67.79% -> 88.14%)

> 摘要: core 包 W9b(R34, 计划 26-10-31-0128): 目标 6 文件(modules/{rules,maintenance,speed_curve,tracker,notify,logging}_mod.py)· 池 8 文件 → 首轮(S2) **1,442 变异 / 存活 459 + no tests 17(67.79%)** → S3 三分类 真洞 367(高 18/中 237/低 112; 存活侧 351 + no-tests 侧 16)/等价 109 → S5a 补 **44 守阵**(新建 tests/test_modules_w9b_s5.py, 红验 285/285 全红, commit 986b9f2f) → **S6 同目标同池复跑(3 跑): 杀 1,271 / 存活 171 / 超时 0 / no tests 0(88.14%)**; 对差: 新增存活 0(逐 id), 移出 305 = covered 真洞 280(存活侧 265 + no-tests 侧 15)+ 翻案杀 5 + 连带杀等价 15 + 余量兑现 5; 余量 87 批量入池 1 件(26-11-01-2024); **core/ 整包审计收官(W1–W9b)**。**零 `src/` 改动**(纯补测[先于本轮] + 入池 + 文档)。
> 基线时间: 2026-11-01 20:24
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4653 passed + 2 skipped / 覆盖率 99.16%(语句覆盖 99%, 分支 7400)**(C3 收尾实测 124s 量级, mut-core-audit 本地树; 档案 Refs 与 26-11-01-2024 doc-refs 双向补链后全绿)。

### 首轮与复跑对照(全轮一行 + 逐文件)

| 轮次 | 变异 | 杀 | 存活 | 超时 | no tests | 杀死率 |
|---|---|---|---|---|---|---|
| 首轮(S2, 2026-11-01 午后) | 1,442 | 966 | 459 | 0 | 17 | 67.79%(no tests 计入分母 66.99%) |
| **复跑(S6, 2026-11-01 20:08–20:12, 3 跑)** | 1,442 | **1,271** | **171** | **0** | **0** | **88.14%** |

| 目标文件 | 变异 | 存活+no tests(首轮) | 杀(复跑) | 存活(复跑) | 杀死率(首轮→复跑) |
|---|---|---|---|---|---|
| modules/rules_mod.py | 517 | 250+17 no tests | 460 | 57 | 50.00% → 88.97% |
| modules/maintenance_mod.py | 394 | 130 | 331 | 63 | 67.01% → 84.01% |
| modules/speed_curve_mod.py | 341 | 43 | 303 | 38 | 87.39% → 88.86% |
| modules/tracker_mod.py | 112 | 23 | 102 | 10 | 79.46% → 91.07% |
| modules/notify_mod.py | 51 | 8 | 51 | 0 | 84.31% → 100% |
| modules/logging_mod.py | 27 | 5 | 24 | 3 | 81.48% → 88.89% |
| **合计** | **1,442** | **459+17** | **1,271** | **171** | **67.79% → 88.14%** |

- **选择池(8 个)**: `tests/test_modules_p3.py` · `test_modules_p5.py` · `test_mixins_tags.py` · `test_speed_curve.py` · `test_tracker.py` · `test_notify.py` · `test_core_modules.py` + **`test_modules_w9b_s5.py`(S5a 新建, 本轮 cp 进镜像 md5 核对一致; 池 7 既有文件 + helpers 逐位一致已核 md5 双侧相等)**
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**(head 3275c1d4 原样复用, venv pytest 钉 9.1.1 未动未重建; 跑前按坑档配方删 mutants/ 6 目标副本+.meta+.spans+stats, Run A 前全量 rm -rf mutants+cache)
- **deselect**: 9 条镜像口径原样(8 条 DEFAULT_DESELECT + `test_relocate_exec::test_spawn_args_pinned`; 本轮池不含 test_relocate_exec, 平台守阵免核 —— test_modules_w9b_s5.py grep CREATE_NO_WINDOW 零命中); 池基线预验 8 文件 **223 passed** 全绿(0.77s)
- **3 跑**(全 rc=0, 无 WSL VM 被杀): Run A rules 单目标 28s → Run B 其余 5 文件 43s(换目标前删 5 目标副本+meta+spans+stats)→ **Run C 收官合并 glob 5s**(stats 复验, R33 先例, 6 份 meta 共存)
- **对差(逐 id, s6-reconcile-report.txt)**: 首轮 476(459 survived + 17 no tests) → 复跑 171, **新增存活 0**(6 文件逐一做实, 复跑存活 ⊆ 首轮)。移出 305 = **covered 真洞 280**(存活侧 265 + no-tests 侧 15 —— 后者 = no tests 17 中 15 真洞被 `_handle_rule` 定向守阵转 killed, 余 2 条 = 等价 hr4 + 真洞 hr12·低 转 survived 记账)+ **翻案杀 5**(ae1/ae3/ae4/ae15/ae16)+ **连带杀等价 15**(rules 9: ad4/ae28/de18/de96/mk5/rm3/rm4/tr13/tr19 · maintenance 5: hm31/hm54/hr75/ta15/ta6 · tracker 1: ta8 —— 同 W4-W9a「新守阵精确断言把等价转可观测」形态)+ **余量兑现 5**(mk3/mk7/mk13/mk14/rf11, 簇级覆盖连带)
- **复跑存活构成闭合**: 等价 **89**(存活侧 88 + no-tests 等价 hr4)+ 余量真洞 **82**(存活侧 81 + no-tests 余量 hr12)= 171 ✓; 逐文件: rules 57(等价 31+余量 26)· maintenance 63(44+19)· speed_curve 38(8+30)· tracker 10(3+7)· notify 0 · logging 3(3)
- **三分类终态(S1 收账, 逐 id 对账 s6-ledger.py)**: 全轮真洞 **367**(高 18/中 237/低 112; 存活侧 351 + no-tests 侧 16), 处置闭环 = **280 守阵覆盖**(存活侧 265 + no-tests 侧 15)+ **余量 87 批量入池 1 issue**(rules 31 含 hr12 + maintenance 19 + speed_curve 30 + tracker 7, 中 4/低 83); 等价 **109**(含翻案 5 维持等价 —— ae1/ae3/ae4/ae15/ae16 在 classify 表内自始记等价, 收尾预案「351→346/108→113」改判量经逐 id 对账不成立, 终态维持 真洞 351/等价 108; 弃杀 4 rf9/rf11/he6/he10 留池, 复跑实测 rf11 被簇级连带杀)
- **1 件 issue(余量入池, 有意不补测)**: [`26-11-01-2024-test-core-w9b-mutation-low-residue`](../../issues/26-11-01-2024-test-core-w9b-mutation-low-residue.html)
- **dump / results / 对账产物指针**: 复跑 = `tmp-analysis/w9b-r34/26-11-01-2018-rerun-merged-dump.txt`(171 条带 diff)+ `s6-reconcile-report.txt`(对差全构成 + 账目闭合); 对账脚本 = `s6-ledger.py`(覆盖账目)+ `s6-survivor-diff.py`(逐 id 对差); 首轮 = `26-11-01-1811-dump-*.txt` 系列与 `26-11-01-1806-core-modules-w9b-merged-results.txt`; 三分类输入 = `classify-rules.md` / `classify-small.md`(各含「R34 收尾落账」节); 红验 = `s5-redverify-units.py`(285 条)

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_modules_w9b_s5.py`(44 守阵) | S5a 补测, commit 986b9f2f(先于本轮 C3) |
| `memory-bank/issues/26-11-01-2024-test-core-w9b-mutation-low-residue.html` | 余量批量入池(本轮) |
| `memory-bank/testing/baselines/26-11-01-2024-mutation-core-w9b-modules-small.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R34 条目 + Summary/S 步表收口 W9b(core/ 整包收官) |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W9b 口径, 变异数 15,585)+ §03 core 行改「已做(整包审计收官)」 |
| `tmp-analysis/w9b-r34/`(gitignore) | classify 收尾落账节 + s6-ledger.py / s6-survivor-diff.py / s6-reconcile-report.txt + 2018 复跑 dump |
