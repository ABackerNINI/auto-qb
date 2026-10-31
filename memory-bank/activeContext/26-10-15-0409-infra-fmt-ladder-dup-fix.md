# infra fmt 阶梯单点 · dup-code-audit issue 认领与修复

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html」→ dup-code-audit 专题 infra 轮(R18)第 4 条 refactor issue 认领并修复。口径沿用前修复轮(hr/webui/rules/core/infra R9): A 类抽单点收敛 + 保守口径(行为逐字不变)。复验定案: `infra/utils.py` 的 `fmt_speed` / `fmt_size` 阶梯循环仍逐字同(判据与格式化行各写一遍, 只差单位表 `/s` 后缀)。
> 最后活动: 2026-10-15 04:14

**Refs:** memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html

## 已完成(2026-10-15 单会话收口)

- issue 复验(锚点均在, `utils.py` 679/687 按取证 26-10-15 04:09)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志留实际修法/验证方式/测试数字痕。
- 改动面: `src/auto_qb/infra/utils.py`(`_SIZE_UNITS` 单位表 + `_fmt_ladder(value, units, suffix)` 阶梯骨架单点, `fmt_speed` / `fmt_size` 降为委托 —— `fmt_size` 的 int 强转与 `"-"` 兜底保持在外) + `tests/test_utils.py`(行为用例 + 静态单点守阵, 头部「测试计划」清单同步两条); 全部过 `dev.fmt`。零跨包改动, `config.yml` / `auto-qb-data/` 未触碰。
- 验证: 定向 `test.one tests/test_utils.py` 全绿; 红验双验闭环 —— ①自抄阶梯回(fmt_speed 内内原循环)即静态守阵红(count 2), ②精度变异(`.2f`→`.1f`)即行为用例红(钉输出判), 还原即绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/attachments/26-10-15-0414-infra-fmt-ladder-dup-fix.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 主档案 `26-10-10-backend-dup-code-audit.md` 进度记 R10 一行; infra 余 1 条(`infra-platform-detect-bypass-dup`)仍 `Open`。
