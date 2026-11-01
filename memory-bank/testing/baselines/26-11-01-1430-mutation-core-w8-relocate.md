# 4563 passed + 2 skipped(根) —— core W8 R32 变异审计: relocate 搬移面两文件 S6 同池复跑(4,185 变异, 杀死率 63.66% → 82.15%)

> 摘要: core 包 W8(R32, 计划 26-10-31-0128): 目标 2 文件 `**/core/modules/relocate_mod.py`(1,511 行)+ `**/core/modules/relocate_units.py`(932 行)· 池 6 文件 → 首轮(S2, 2 文件分跑 + 合并 glob 三跑补 meta) **4,185 变异 / 存活 1,521(mod 1,120 · 62.74% + units 401 · 65.99%, 零超时零 no tests)** → S3 三分类 **真洞 1,147(高 0 / 中 280 / 低 795 / 极低 72)/ 等价 372~374(块小结与表行直和 ±2 记账差, 同 R31 ±3 先例)** → S4-S5a 补 **50 守阵**(test_relocate_exec 37 + test_relocate_units 13, 红验 688/688 全红, commit af90d234 / bf7aaefe)+ 余量真洞 461 批量入池 2 件(26-11-01-1357, commit 64974759)→ **S6 同目标同池复跑(2 文件分跑): 杀 3,438 / 存活 747 / 超时 0 / no tests 0(82.15%)**, **新增存活 0**(逐 id 对差: 复跑 747 全部 ⊆ 首轮 1,521)。对差: 移出 774 = 红验清单兑现 673 + **连带杀 101(等价 46 + 真洞余量 54 + 记账差 1)**; 复跑存活构成闭合 = 红验covered存活 17(spawn 簇 14 因 Windows-only 守阵镜像 deselect + `_norm#16/17` 2 条 return 行 replace 变异 POSIX no-op 仅 Windows 可杀 + w5 等价改判 1)+ 余量存活 730。**零 `src/` 改动**(纯补测/入池[均先于本轮] + 文档)。
> 基线时间: 2026-11-01 14:30
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4563 passed + 2 skipped / 覆盖率 99%**(C3 收尾实测 117.5s, mut-core-audit 本地树; 档案 Refs 与 26-11-01-1357 两件 doc-refs 双向补链在 S5a 批量 commit 64974759 已就位, 一次全绿)。

### 首轮与复跑对照(全轮一行 + 逐文件两行)

| 轮次 | 变异 | 杀 | 存活 | 超时 | no tests | 杀死率 |
|---|---|---|---|---|---|---|
| 首轮(S2, 2026-11-01 上午, 2 文件分跑 + 合并 glob 三跑) | 4,185 | 2,664 | 1,521 | 0 | 0 | 63.66% |
| **复跑(S6, 2026-11-01 14:07–14:20, 2 文件分跑, 结果戳 1419/1420)** | 4,185 | **3,438** | **747** | **0** | **0** | **82.15%** |

| 目标文件 | 变异 | 存活(首轮) | 杀(复跑) | 存活(复跑) | 杀死率(首轮→复跑) | 复跑墙时 |
|---|---|---|---|---|---|---|
| modules/relocate_mod.py | 3,006 | 1,120 | 2,484 | 522 | 62.74% → 82.63% | 2m25.6s(25.61 mut/s) |
| modules/relocate_units.py | 1,179 | 401 | 954 | 225 | 65.99% → 80.92% | 1m1.8s(25.00 mut/s) |
| **合计** | **4,185** | **1,521** | **3,438** | **747** | **63.66% → 82.15%** | ≈14 min 含导出 |

- **目标(glob)**: 2 个单文件 glob(同首轮逐文件跑; 首轮曾用合并 glob `**/core/modules/relocate_*.py` 三跑补 meta, 复跑后镜像 pyproject 已复原回该收官态)
- **选择池(6 个; 两轮一致)**: `tests/test_relocate_exec.py` · `tests/test_relocate_config.py` · `tests/test_relocate_paths.py` · `tests/test_relocate_units.py` · `tests/test_grouping_relocate.py` · `tests/test_web_relocate.py`(T15a/T15b 改过的 test_relocate_exec / test_relocate_units 已 cp 进镜像 + md5 核对一致, 另 4 池文件与 2 目标 src 本来就逐位一致)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**
- **镜像口径**: head **3275c1d4**(与首轮逐位一致); **未刷新/未重建/未 uv sync**(`--no-refresh --no-sync` 原样复用, venv pytest 钉 **9.1.1**); 跑前核镜像 pyproject `[tool.mutmut]` only_mutate 为本轮 glob
- **机器**: WSL2 · **8 核**
- **⚠ deselect 偏差声明(与首轮 8 条的差异, 本轮唯一配置偏离)**: S5a 新守阵 `test_spawn_args_pinned`(test_relocate_exec)断言 Windows-only 的 `subprocess.CREATE_NO_WINDOW`, 在 WSL 镜像**基线即红** → mutmut stats 收集中断(首次走 `mutants.run` wrapper 24.7s 失败退出, 基线红族同 R28 形态但成因是平台属因而非静态守阵)。处置 = 镜像内直调 `set_conf.py --deselect <8 条原样 + 本条>`(第 9 条**仅本轮镜像**, 未进包 `DEFAULT_DESELECT`, 本地 tests/ 零改动); 后果 = 该守阵目标簇(spawn 进程参数 14 条)在 WSL 复跑不可杀, 留存面见下。缺口本体(平台敏感守阵的 deselect 提醒机制)同族先例 issue 26-10-31-1539-deselect-guards, 后续轮处置建议已留报告
- **新增存活 0**(逐 id 对差做实): 复跑存活 747 全部 ⊆ 首轮 1,521, 只有移出无移入(mod 522 ⊆ 1,120 / units 225 ⊆ 401)
- **移出 774 构成**: 红验清单兑现 **673**(清单 690 = mod 528 + units 162; 存活 17 见下, 被杀 673 含翻案 j13/lo2 2 条)+ **连带杀 101** = 等价 46(`gf19/gf120/gf143 sm53/60/61/62/65/66/68/69/70/71/128/222 sj73/76/79/131/132 ar61/62/63/86/99/100 rv61/62/63 sg43 lj19/20/22/23/24 am21/22/28 sc23/24 j12 p112/197/198/200 sh9` —— 同 W4-W7「新守阵精确断言把等价转可观测」形态)+ 真洞余量 54(含未逐验销账 3: gf_24/25、sm_72; sg_1/29 kill 面同构兑现; 余为守阵簇映射/既有池测试连带)+ 行映射记账差 1
- **复跑存活构成闭合(747)**: 红验 covered 存活 **17**(spawn 簇 14: `sp8/9/13/14/15/16/19/20/24/26/32/33/34/35` —— 目标守阵被 deselect[见上]; `_norm#16/17`: return 行 replace 变异在 POSIX 恒 no-op、仅 Windows 可杀, W7「平台真洞 Windows 套件咬合」同族新形态; `_within#5`=w5: S5a 已改判等价死代码, 预期存活)+ 余量存活 **730**(真洞余量 ~404 = 461 − 连带杀 54 ± 行映射记账差 3; 等价 326 = 372 − 连带杀 46; 无行记账差 29)= **747** ✓
- **未逐条红验 10 条销账情况(S5a 遗留, 中危 18 = 未逐验 10 + 注记 8)**: 复跑被杀 **3**(gf_24/25、sm_72, 销账)+ 存活 **7**(gf_140/144/147、sm_41/43、sj_145 守阵同函数簇级覆盖对该变异形态无断言实锤 + sp_27 属 deselect 守阵簇)→ **中危余量 18 → 15**; 注记 8 中 st_reparse_tag 簇 4(WSL 不可构造)维持存活, sg_1/29 兑现被杀, 翻案 gf_142/am_25(改判等价)维持存活
- **三分类终态(S5a 收账)**: 真洞 **1,147**(高 0 / 中 280 / 低 795 / 极低 72)= 红验覆盖 686 + 余量 461(中 15 / 低 397 / 极低 46, 复跑后中危修订); 等价 **372**(连带杀 46 后存活面 326)
- **S4 对账**: 本轮宽池轮不另走全套件 verify(沿 R30 宽池口径直接读 diff); 红验 **688/688 全红**(mod 528 + units 160, 逐条 apply→跑守阵→还原; units 清单含 w5 GREEN 改判等价)
- **2 件 issue(余量入池, 有意不补测)**: [`26-11-01-1357-test-core-w8-relocate-mutation-low-residue`](../../issues/26-11-01-1357-test-core-w8-relocate-mutation-low-residue.html)(低 397/极低 46/中危 18=未逐验 10+注记 8)+ [`26-11-01-1357-test-core-w8-relocate-mutation-blindspot-equivalence`](../../issues/26-11-01-1357-test-core-w8-relocate-mutation-blindspot-equivalence.html)(平台盲区与翻案落账); 档案 Refs 已双向声明
- **dump / results 指针**: 首轮 = `tmp-analysis/w8-r32/26-11-01-10{32,37,43}-*-results.txt` + dump `26-11-01-104{4,5}-*`(原始落盘 `R:\Temp\auto-qb\mutants\`); 复跑 = `tmp-analysis/w8-r32/26-11-01-rerun-core-modules-relocate-{mod,units}-py-results.txt`; 对账产物 = `s6-reconcile.py` + `s6-reconcile-output.txt` + `s6-{covered,residue}-alive.txt`(covered/residue × alive/killed 全集划分); 三分类输入 = `classify-mod-a.md` / `classify-mod-b.md` / `classify-units.md`(含 S5a 覆盖账目节); 红验日志 `s5-redverify-*.log` + `s5-redverify{,-units}.py`

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_relocate_exec.py`(37 守阵)· `tests/test_relocate_units.py`(13 守阵) | S5/T15a-T15b 补测, commit bf7aaefe / af90d234(先于本轮 C3) |
| `memory-bank/issues/26-11-01-1357-*.html`(2 件) | 余量批量入池, commit 64974759(先于本轮 C3) |
| `memory-bank/testing/baselines/26-11-01-1430-mutation-core-w8-relocate.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R32 条目 + Summary/S 步表收口 W8 |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W8 口径)+ §03 core 行 W8 已做注记同步 |
