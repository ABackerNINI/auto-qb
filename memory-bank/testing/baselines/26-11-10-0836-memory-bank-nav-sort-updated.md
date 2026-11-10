# 5911 passed + 2 skipped —— kb.nav 排序新增更新时间默认档

> 摘要: kb.nav 台账排序新增「更新时间」档并改为默认, 全量绿
> 基线时间: 2026-11-10 08:36

## 验收数字

```text
TOTAL                                                26254     48   9150     58    99%
5911 passed, 2 skipped in 130.42s (0:02:10)
```

(实测时点: HEAD 07085eab + 本轮工作树改动, `commands run test.full` 2026-11-10 08:36; 全绿, 覆盖率 99%)

## 本改动面

- **`.agents/skills/memory-bank/scripts/nav_page.html`** (+14/-4): 排序下拉新增 `updated`(更新时间 新-旧)档并置顶为出厂默认, 原 `stamp` 档改名「创建时间 新-旧」(键名不动, 旧 localStorage 存档兼容); `SORT_KEYS` 加 `updated`; `aFiltered()` cmp 表加 updated 比较器 (doc-updated 新-旧, 同戳按创建戳, 兜底形态序); `ledgerCells()` 时间戳列在更新时间序下改显 doc-updated (缺回落 stamp, 创建戳进 title)。
- **`tests/test_kb_nav_shell.py`** (+23): 新守阵 `test_ledger_sort_has_updated_default` 钉五面 (updated option 置顶 / `sort: "updated"` 出厂默认 / SORT_KEYS 含 updated+stamp 双值 / cmp 含 updated 比较器 / ledgerCells cellStamp 跟随排序档); 文件头「## 测试计划」清单同步。
- **评审**: 3 轮 (轮1 minor 排序守阵缺口 + 轮2 nit cellStamp 漏钉, 全修; 轮3 零 actionable), 引文过检 2/2; 另以 node 实测比较器同戳回落行为 (同更新戳按创建戳、缺失回落 stamp)。
- **真机**: 不适用 (纯前端排序逻辑, 数据字段 doc-updated 由 nav_data enrich 单测覆盖, 桩面无失真)。
