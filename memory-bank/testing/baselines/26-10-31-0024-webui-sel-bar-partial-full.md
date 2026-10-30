# 4175 passed, 10 skipped, 68.21s, cov 99.18% —— 全量基线: 模板C 半选比例条实施后

> 摘要: 全量基线: 模板C 半选比例条实施后
> 基线时间: 2026-10-31 00:24

## 验收数字

`commands run test.full` 实测(2026-10-31 00:23, 计划 26-10-30-2359 模板C 实施后):

- 汇总行: `4175 passed, 10 skipped in 68.21s (0:01:08)`
- 覆盖率: `Required test coverage of 99.0% reached. Total coverage: 99.18%`
- TOTAL: `20891 stmts, 114 miss, 7160 branch, 105 bmiss, 99%`(静态文件/前端 JS 无 py 覆盖, 全量口径与上基线一致)
- 首跑曾挂 `test_sel_group_member_linkage`: 守阵 needle 钉住 `groupSelState` 旧实现字符串
  `return { selected: st.selected, partial: st.partial };`, 本次重构直通 `_selState`(口径不变,
  多带 ratio)—— needle 随迁移更新后全量通过。

## 本改动面

- `src/auto_qb/webui/static/shared/selection.js`: `_selState` 返回值追加 `ratio`(hit/total);
  `groupSelState` 直通 `_selState`(全选分支补 `ratio: 1`); 新增 `groupSelStyle(g)` —— 半选时
  返回 `{ "--sel-ratio": ratio }` 供行内 style, 非半选空对象(CSS fallback=1 保守默认)。
- `src/auto_qb/webui/static/shared/tpl/groups.html`: 组行 `:style` 改数组合并
  `[gridStyle('group'), groupSelStyle(g)]`。
- `src/auto_qb/webui/static/shared/row_lang.css`: 四组 selected/partial 合写规则拆开 —— partial
  改下锚比例短条(`top:auto; height:max(8px, calc((100% - 28%) * var(--sel-ratio, 1)))`),
  flat/wave × 沟槽条/横滚吸左窄条各一处; 头部定案注释同步。
- `tests/test_web_shortcuts.py`: `test_sel_group_member_linkage` ④ 消费端 needle 随
  `groupSelState` 重构迁移 + 头部「测试计划」清单同步。
- 纯前端静态文件 + 守阵 needle, 无 Python 行为变更。
