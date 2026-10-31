# 4064 passed + 10 skipped(根) —— HR 详情表表头排序判据同源修复后全量基线

> 摘要: HR 详情表(thead 模式)表头排序整表静默失效修复(issue 26-10-29-1348)后全量基线
> 基线时间: 2026-10-30 00:25
**Refs:** memory-bank/issues/26-10-29-1348-bug-b-r23b10-aqtable-hr-sort-dead.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`(pytest.ini addopts, TMPDIR 由 task 内置); 2026-10-30 实测, 全量 126.09s, 建档 00:25):

```
  TOTAL                                                20817    117   7136    108    99%
  4064 passed, 10 skipped in 126.09s (0:02:06)
```

- 汇总行: **4064 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本轮零新增用例项: 三处既有守阵函数内扩断言(`test_frontend_table_shell_single_point` ④ / `test_frontend_hr_table_sort_filter_reorg_wiring` §2 各改版 1 条字面断言 + 补 3 条新断言), passed/skipped 与上一可用基线(`26-10-29-2113-pop-item`)同型。
  - 「10 skipped(根)」为既有环境条件 skip, 与本轮无关(`26-10-29-2113` 切片同为 10 skipped; 21:28 的 dir-season 切片记 2, 当轮环境差异见该片)。
  - 红验两轮(突变 → 还原): ①xtpl.html thead 恢复硬编码 `class="sortable"` + 箭头摘 v-if → **2 failed 恰落新断言**(其余 4062 全绿); ②hr_status.js 十列摘 `sortable: true` → **1 failed 红在「十列必须全部标 sortable: true…实得 0」**; 还原后全量绿。
  - 运行时等价性(issue 验证手段②): 真浏览器(atlas, dev.harness 桩; 站点明细端点在页面内以 fetch 桩灌 5 行合成数据, 其余走真链路)三连点「上传量」→ 降序(空值行恒末位)/ 升序(空值仍末位)/ 后端默认序, aria-sort 与箭头逐态同步; 键盘 focus + Enter → tid 降序(修前列头连焦点都进不去)。桩端点与行序断言均为本次会话现算, 未落仓库。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/webui/static/shared/hr_status.js` | `HR_TABLE_DEFS.hrDetail` 十列全补 `sortable: true`(判据 = HRS_SORT_VAL 十键全有访问器, 真能排的才标); 注册表头注补判据来源与漏标后果 |
| `src/auto_qb/webui/static/shared/tpl/xtpl.html` | 表壳 thead 分支可排序性判据同源 `col.sortable`: 硬编码 `class="sortable"` 改 `:class="{ sortable: col.sortable, num: col.num }"`, 箭头位补 `v-if="col.sortable"`; 分支头注补判据同源纪律(issue 26-10-29-1348) |
| `tests/test_webui_static_skins.py` | `test_frontend_table_shell_single_point` ④ 与 `test_frontend_hr_table_sort_filter_reorg_wiring` §2: `class="sortable"` 字面断言改读 thead 分支切片, 钉 sortable 类与箭头门控同源 `col.sortable`; 补 hrDetail 十列 `sortable: true` 计数 + HRS_SORT_VAL 访问器对账; 头部「## 测试计划」两行同步 |
| `memory-bank/issues/26-10-29-1348-bug-b-r23b10-aqtable-hr-sort-dead.html` | 状态 Open → In Progress → Done(复验/实际修法/验证方式回填); doc-refs 反向声明本切片与坑档 |
| `memory-bank/pitfalls/web-ui/sortable-gate-source-split.md` | 新坑档(能力判据源分裂) |
| `modules/attachments/webui-static-contract-details.md` | 表壳契约 thead 模式段补「可排序性判据同源 col.sortable」 |

**未改**: `shared/table.js` 的 `headActivate` 门控(issue 建议修法明确不推荐摘门控); grid 分支一字未动; `hrsSetSort` 三态机与 `hrsCompareRows` 比较器零触碰(语义由既有 node 电池钉住); 表② 波次表仍不接排序(计划 §3.4 口径)。
