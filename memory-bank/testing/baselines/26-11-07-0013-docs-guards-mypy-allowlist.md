# 5471 passed + 10 skipped —— issue 26-11-06-0744 修复: guards.md 补登记 mypy allowlist 守阵

> 摘要: issue 26-11-06-0744 修复: guards.md 补登记 mypy allowlist 守阵
> 基线时间: 2026-11-07 00:13
**Refs:** memory-bank/issues/26-11-06-0744-docs-guards-mypy-allowlist-unregistered.html

## 验收数字

- 汇总行: **5471 passed, 10 skipped, 1 warning in 137.13s**(0:02:17, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举); 命令整体 139.2s。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 74 miss / 8396 branch / 41 partial / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 本轮**纯文档改动**(仅 `memory-bank/testing/guards.md`), 产品代码与测试代码零改动; 数字为当前树实测 —— 开工快进 11 笔后的远端合流面(上基线 5460 passed 是快进前), 用例增量来自远端提交而非本轮, 与历史切片的差值对比走 `commands run kb.baseline -n 2`。
- mypy 豁免面: 本轮零改动, 守阵 `tests/test_mypy_allowlist_guard.py` 单文件 **11 passed**; 真仓对账(zero finding)由全量覆盖。

## 本改动面

- `memory-bank/testing/guards.md`: 新增一节「类型注解 / mypy allowlist」, 表内一行登记 `test_mypy_allowlist_guard.py`(真仓对账面 = `test_repo_allowlist_matches_frozen`) —— 钉住 `[tool.mypy]` 三张清单对账(ignore_errors 整模块豁免面 / disable_error_code 的 (模块, 码) 豁免对 / 收紧面 disallow_untyped_defs)与五条判定(新增豁免红 · 递减不红 · 递减后回加红 · 顶层全局豁免红 · 收紧面回撤红); 节下补「只做静态扫描、不在 pytest 内跑 mypy, 类型正确性由 dev.typecheck 验收」与登记来源。
- 登记规则核对: ①本表加一行(本轮) ②守阵头部「## 测试计划」清单已有 11 条对应条目(无需改) ③红验已做(见下)。
- 红绿双验: 临时向真仓 `pyproject.toml` 注入冻结外豁免(合成模块 `auto_qb.core.redprobe_tmp[union-attr]`) ⇒ `test_repo_allowlist_matches_frozen` `1 failed`, finding 指名新增豁免对; `git checkout -- pyproject.toml` 撤注入(复扫零残留)后守阵 `11 passed`。
- `pyproject.toml`、产品代码、守阵代码零改动。
- 收尾件: issue 报告状态 Open→In Progress→Done + 复验/实际修法/红验留痕; 本基线切片; activeContext 切片走 `kb.wrap`; 索引由 `kb.index` 重建。
- 真机自检不命中: 纯文档改动, 不落入真机轨两类准入(qB 真执行 / 真文件系统·进程·注册表); 桩可验。
- 收口评审不触发(改动 <50 行、不触安全面/红线); 立档阈值不命中(单文件文档、1 轮指令), 未立任务档案。
