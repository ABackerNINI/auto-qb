# 3208 passed + 4 skipped —— 修复 infra fmt_speed/fmt_size 阶梯逐字同(issue 26-10-11-0352 infra-fmt-ladder-dup)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html」→ dup-code-audit infra 轮(R18)第 4 条 refactor issue。改动 2 文件: `src/auto_qb/infra/utils.py` 抽 `_SIZE_UNITS` 单位表 + `_fmt_ladder(value, units, suffix)` 阶梯骨架单点, `fmt_speed` / `fmt_size` 降为委托(int 强转与 `"-"` 兜底保持在外, 行为逐字不变); `tests/test_utils.py` 新增行为用例(整数输入 `fmt_speed(v) == fmt_size(v) + "/s"` 跨 rung + 逐 rung 钉输出)与静态单点守阵(`if value >= div:` 计数 == 1), 头部「测试计划」清单同步。红验双验闭环: 自抄阶梯回即守阵红(count 2), 精度变异 `.2f`→`.1f` 即行为用例红, 还原即绿。
> 基线时间: 2026-10-15 04:14

**Refs:** memory-bank/activeContext/26-10-15-0409-infra-fmt-ladder-dup-fix.md,memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html

## 验收数字

- test.full: 3208 passed + 4 skipped / TOTAL 16840 159 5724 142 99%(98.64%, 过 98% 闸门); 耗时 145.74s(单次采样, 口径见 baseline.md)。与上基线 3206 passed 的 +2 = 本轮新增两用例, 零红。
- 定向 test.one(tests/test_utils.py, 修复后): 93 passed / 1.37s —— 含新增 `test_fmt_speed_size_ladder_equivalence` / `test_fmt_ladder_single_point`。
- 红验双验(一次性工作树变异, 还原即绿, 不进提交): ①`fmt_speed` 内内原阶梯自抄 → `test_fmt_ladder_single_point` 红(`AssertionError: 阶梯判单点`, count 2), 行为用例绿(行为不变, 守阵拦结构自抄); ②`_fmt_ladder` 精度 `.2f`→`.1f` → `test_fmt_speed_size_ladder_equivalence` 红(`'1.0 GiB' == '1.00 GiB'`), 静态守阵绿(形态未变) —— 两判据互补拦面实证。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 闸门 match 不命中, 未跑。
- Linux(WSL)侧未重测 —— 改动纯格式化函数与用例, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- 源(1 文件): src/auto_qb/infra/utils.py —— `_SIZE_UNITS` 共享单位表 + `_fmt_ladder` 阶梯骨架单点(判据与格式化行各写一遍, suffix 参数承载 `/s`), `fmt_speed` / `fmt_size` 降为委托; 过 dev.fmt。
- 测试(1 文件): tests/test_utils.py —— 行为用例 + 静态单点守阵(同 `test_hr_entry_guard_single_point` 体例), 头部「测试计划」清单 +2 行; 过 dev.fmt。
- 文档: 本切片 · issue 报告 26-10-11-0352-refactor-infra-fmt-ladder-dup.html(Done, 复验/实际修法/验证方式/测试数字留痕, doc-refs ↔ 切片 Refs 双向) · activeContext 切片 26-10-15-0409 · 主档案 26-10-10-backend-dup-code-audit.md 进度记 R10 · kb.index 重建。
