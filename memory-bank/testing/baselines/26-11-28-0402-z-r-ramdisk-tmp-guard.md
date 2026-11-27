# 7064 —— Z:\R 内存盘共享接入与 TMPDIR 候选守卫(26-11-28)

> 摘要: Z:\R 内存盘共享接入与 TMPDIR 候选守卫(26-11-28)
> 基线时间: 2026-11-28 04:02

## 验收数字

终版(评审修复后)实测: `commands run test.full` [ok] 409.0s = **7073 passed, 6 skipped, 1 warning in 407.05s**(含远端 26-11-28 同步进的 Web 鉴权守阵 +15 条); 等价收集面 `pytest tests/unit` = **99.51%(闸过, 421.35s, 7073 passed/6 skipped)**。
本机 arg=tests 形态的覆盖率报表恒 0% 且闸静默放行 —— 环境问题非回归(本批 coverage 相关代码与改前逐字节等价), 覆盖率背书一律引用 unit 形态实测; 判别与绕行单点见 [pitfalls/testing/coverage-xdist-zero.md](../../pitfalls/testing/coverage-xdist-zero.md)。
真机面(rm04/seed 的内存盘落点与负向对照)本环境无真实 qB, 仅静态/导入级验证: rm04 导入探针实测 RAM 回退 `.work`(共享盘 junction 探不过, 候选目录已回收)、`_absent_drive()`=Q:; seed 探针实测 RAM_ROOT=Z:\R\qbt-fake、64M 落内存盘/256K 落 .work。真机回归待有 qB 环境跑(任务档案子任务 9 Open)。

## 本改动面

- `tests/unit/_tmp_bootstrap.py`: 候选不加 Z:\R(映射盘共享, 26-11-28 实测撤回并留元组尾注守卫文案); FATAL/rc=4 文案链与 docstring 路径漂移同修(`tests/_tmp_bootstrap.py`→`tests/unit/_tmp_bootstrap.py` 等); docstring 改 raw。
- `tests/unit/test_tmp_bootstrap.py`: 顺序用例增「Z: 永不入候选」断言(映射盘 UNC 假红守卫); 测试计划条目同步。
- `tests/real/seed.py`: RAM_ROOT 单常量 → 候选探测(`R:/qbt-fake` → `Z:/R/qbt-fake`, mkdir+写探针), None 兼容(ALLOWED_ROOTS/list/clean 分支); 理由串与 docstring 中性化(「内存盘」不再钉 R:)。
- `tests/real/rm04_relocate/test_rm04_relocate.py`: `_ram_root` 候选同上 + `_junction_ok` 试建探针(共享盘 junction 不可建 → 退 `.work`); 新增 `_absent_drive()` 动态选不存在盘替代钉死的 `Z:/rm04_05_neg_ctl/dst`(Z: 于 26-11-28 起为内存盘共享, 负向对照前提翻转); docstring/注释同步。
- `tests/unit/sidefx.py`: `RAM_SCRATCH_ROOTS`(`R:\qbt-fake`/`Z:\R\qbt-fake`)登记为 FSDEL/SYMLINK 放行面(内存盘探针的删除/建链是刻意行为), UNC 归一比对。
- 叙述链同步: `.commands/test/config.toml`、`.commands/test/scripts/pkg_scoped.py`、`tests/real/conftest.py`、`tests/unit/sidefx.py` 示例、`.commands/real/config.toml`(real.seed 落点)。
- 口径文档: `memory-bank/pitfalls/testing/tmpdir.md`(候选链 + Z:\R 撤回实证段 + 触发词)、`memory-bank/projectbrief.md`(临时产物两环境口径 + junction 不可建实证)、`memory-bank/testing/real-machine.md`(≥32M 落点)、`memory-bank/testing/sim-5000.md`(AUTOQB_SIM_ROOT 口径); 新坑档 `memory-bank/pitfalls/testing/coverage-xdist-zero.md`(本机 pytest tests 覆盖率 0% + 闸静默)。
