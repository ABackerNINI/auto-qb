# 4180 passed + 2 skipped(根) —— 行语言 flat 行板表示统一后全量

> 摘要: issue 26-10-30-0818 修复后全量基线 —— row_lang.css flat 段行板基础底/hover/选中三处改与首格逐字同一表达式(消除「tint 叠页底 ↔ color-mix」视觉恒等但计算值分家), 视觉零变化; e2e 全量默认轮同轮实测 366 passed / 0 failed / 10 skipped(12.5m)
> 基线时间: 2026-10-31 00:13

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 119.96s, 建档 00:13):

```
  TOTAL                                                21135     96   7152    100    99%
  4180 passed, 2 skipped in 119.96s (0:01:59)
```

- 汇总行: **4180 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 相对上基线(`26-10-30-0419-webui-rowlang`, 4086 passed + 2 skipped)的 +94 passed 来自两者之间
    的其它轮次与本轮; 本轮改动仅 row_lang.css flat 段 3 处声明与注释, 未新增/删除任何测试,
    test_webui_static_skins 23 项全绿(其 row_lang.css 段只查 transition 纪律, 不钉行板表达式)。
  - 首跑 test.quick 曾 1 红(`test_memory_bank.py::test_gen_all_check_is_green`): issue 状态翻转后
    未重建 issues/_index.md —— `commands run kb.index` 重建后全绿, 非代码问题。

## 本改动面

- `src/auto_qb/webui/static/shared/row_lang.css`: flat 段 3 处声明改与首格逐字同一表达式 ——
  行板基础底 `transparent`→`var(--bg, #0d1724)`、行板 hover→`var(--rl-hover-solid, color-mix(白12%, --bg))`、
  行板 selected/partial→`var(--rl-sel-solid, color-mix(accent10%, --bg))`; `--rl-hover-tint` 令牌消亡
  (文档头摘除), `--rl-sel-tint` 保留(仍被 wave 段消费); 注释同步(恒等推导降级为历史备注)。
- e2e spec 零改动: `e2e/main-table-pinned-hover.spec.mjs` / `main-table-pinned-selected.spec.mjs`
  继续按计算值逐帧/逐字守原缺陷(悬停竖带), 两 spec 16 例(prism+atlas)全绿。
- 知识库: issue 26-10-30-0818 置 Done; 坑档 testing/headless-prefers-light-theme-gate 复发 +1
  (prism 例无头落 frost, 行语言规则整体关闭, e2e 盲区); pitfalls/web-ui/frozen-column.md ⑩ 追加
  同族拓展(「数学上恒等」的另一种写法不算同一表达式)。
