# 4444 passed + 10 skipped(根) —— HTML 检测闸门扩面: 全仓改动 HTML 进 v.Nu 增量面

> 摘要: HTML 检测闸门扩面: 全仓改动 HTML 进 v.Nu 增量面
> 基线时间: 2026-11-01 09:38
**Refs:** memory-bank/tasks/26-11-01-memory-bank-html-syntax-guard.md

## 验收数字

`commands run test.full` (201.8s, 2026-11-01 实测):

```text
TOTAL                                                22420    197   7688    156    99%
4444 passed, 10 skipped in 197.91s (0:03:17)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。
注记: 首跑全量撞上「跑动期间回写 KB」竞态(2 条回写守卫读到中间态判红, 覆盖率 FAIL 在稳定树复跑未复现), 本条数字取稳定树复跑; 真机按新闸门命令形态对 skill 骨架样例跑 `--vnu --strict` 命中存量 error(空 `<title>`), 扩面行为实证。

## 本改动面

- `.commands/my-commit-flow/.my-commit-flow.toml`: v.Nu 增量闸门扩面 —— `match` `["memory-bank/"]` → `[".html"]`(子串命中, 真有 HTML 改动才触发, 纯 md/py 提交不空跑), `<changed:memory-bank/**/*.html>` → `<changed:**/*.html>`(全仓改动 HTML 都过 W3C v.Nu, 不限 memory-bank); L1+L2 常驻行与 `kb.html-audit` 巡检面口径未动。
- `tests/test_memory_bank.py`: `test_html_guard_wired_into_kb_check_and_gate` 断言钉住新触发面(`match = [".html"]` + `<changed:**/*.html>`)。
- `.agents/skills/memory-bank/scripts/check_html.py` / `memory-bank/pitfalls/ops/vnu-gate-bootstrap.md`: docstring 与坑档触发描述同步扩面口径(认领链双向补齐)。
