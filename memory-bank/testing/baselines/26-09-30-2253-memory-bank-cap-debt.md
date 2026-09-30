# 基线 · 1881 passed + 4 skipped / 91% —— cap 守卫改债务制轮 (守卫降级 + 4 条可发现性守阵)

> 摘要: 尺寸 cap 从「提交前置条件」降级为**债务** —— 除 AGENTS.md 外超限只报告不拦提交, 债务由
> `doc.caps` 在提交时派生现算并转告用户, 清理由用户另开会话。改动面: `scripts/check_context_caps.py`
> (重写为硬规定/债务三档 + `--strict` 收口语义)、skill 侧 `check_kb_structure`(`HARD_CAP_ROLES` +
> `DEBT_MARK`) 与 `_common` / 两个切片脚本(`collect()` 改三元组)、`tests/test_memory_bank.py`
> (删 live 尺寸断言, 新增 4 条可发现性守阵)、`doc.caps` 补 `<args>` + 闸门 note/match、SKILL.md 协议回写。
> 基线时间: 2026-09-30 23:04 (develop @ 8ef82f48, sync 后重测)
> 档案: tasks/26-09-30-memory-bank-cap-debt.md

TOTAL **1881 passed + 4 skipped / 91%**(13279 语句 / 1055 未覆盖 / 4390 分支 / 428 partial, test.full 36.28s, rc=0)
—— 本轮用例净 **+3**: 删 `test_kb_task_archives_within_cap`(live 尺寸断言, −1) 与切片条数判红断言,
新增 `test_kb_cap_debt_is_discoverable_not_blocking` / `test_agents_md_cap_is_hard_not_debt` /
`test_kb_slice_cap_and_count_are_debt_not_blocking` / `test_context_caps_hard_and_debt_split`(+4);
**sync 到 8ef82f48(P4 内核查重构) 后别人新增 +7 测试, 故较上基线 26-09-30-2212(1871) 总 +10**。**删了
断言的地方都补了「可发现性」断言** —— 否则降级之后没有任何用例会因为「严重度改错」而红(新坑档 `pitfalls/kb/cap-debt.md` 第三条)。

分路机检: test.pkg **74 passed**; `doc.caps -- --strict` / `kb.check` / `doc.links` / `doc.drift` 全绿;
**cap 债务 0 项**; AGENTS.md **7,975/8,000**(余量 25 —— 它是硬规定不是债务, 削薄为独立清理项)。
AC 逐条验过 (tmp 仓库): AGENTS.md 未改动 + KB 超限 → rc=0; AGENTS.md 8,001 且改动命中 → rc=1;
仅债务非空 + `--strict` → rc=1 而默认模式 → rc=0。
