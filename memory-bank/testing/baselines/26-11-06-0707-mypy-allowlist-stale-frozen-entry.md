# 5460 passed + 10 skipped —— issue 26-11-06-0624 修复: 冻结清单撤下 qbclient/override + 递减后回加红验

> 摘要: issue 26-11-06-0624 修复: 冻结清单撤下 qbclient/override + 递减后回加红验
> 基线时间: 2026-11-06 07:07

## 验收数字

- 汇总行: **5460 passed, 10 skipped, 1 warning in 203.59s**(0:03:23, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举); 命令整体 206.2s。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 74 miss / 8396 branch / 41 partial / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 本轮零产品代码改动、新增 1 条守阵红验用例; 数字为当前树实测(开工快进 1 笔后的远端合流面), 与历史切片的差值对比走 `commands run kb.baseline -n 2`。
- 静态类型面: `commands run dev.typecheck` 全库 `Success: no issues found in 195 source files`(退出码 0), 独立于 pytest 闸门(D3)。
- mypy 豁免面实测: pyproject 的 `disable_error_code` 展开 **153 对**、`ignore_errors` 2 模式; 守阵冻结清单同为 **153 对** / 2 模式, 双向差集均为空 —— 冻结清单已与现行配置完全对齐(修复前多留 ⑤ `qbclient/override` 一对, 即回加后门); 收紧面 8 模式未动。

## 本改动面

- `tests/test_mypy_allowlist_guard.py`: `_FROZEN_DISABLE_GROUPS` 撤下 ⑤ `(["auto_qb.core.qbclient"], ["override"])`, 原位留编号占位注释; 新增合成样本 `TOML_RE_ADD_REDUCED` 与红验 `test_frozen_rejects_re_add_of_reduced_exemption`(用真仓冻结清单对账, 回加该对应指名判红); 模块 docstring 设计不变量段补「递减须同步撤下、回加即红、递减不可逆」, 冻结清单标题由「S4 基线」改「现行豁免白名单」, 并同步「## 测试计划」清单。
- 红绿双验: 冻结清单未动时单跑新用例 `1 failed`(findings 为空, 现象复现); 修复后守阵单文件 `11 passed`; 一次性对账实证回加 findings 指名 `auto_qb.core.qbclient[override]`、真仓三清单对账 `[]`。
- `pyproject.toml`、产品代码零改动; `commands run dev.fmt` 通过。
- 收尾件: issue 报告两处状态 Open→In Progress→Done + 复验/口径拍板/实际修法/验证留痕; 生成物索引由 `kb.index` 重建; activeContext 切片走 `kb.wrap`。
- 真机自检不命中: 纯静态守阵改动, 不落入真机轨两类准入(qB 真执行 / 真文件系统·进程·注册表); 桩可验。
- 收口评审不触发(立档阈值不命中: 单会话、1 轮指令、1 个源文件); 未立任务档案; 本轮无提交动作。
