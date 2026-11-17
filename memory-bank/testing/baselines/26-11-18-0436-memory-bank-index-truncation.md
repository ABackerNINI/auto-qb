# 6453 passed + 6 skipped —— kb.index 行内截断退役批基线

> 摘要: kb.index 行内截断退役批基线
> 基线时间: 2026-11-18 04:36

## 验收数字

`commands run test.full` 实测(2026-11-18 04:33, Windows, 2m18s):

```
TOTAL                                                28864     43  10304     60    99%
6453 passed, 6 skipped in 137.88s (0:02:17)
```

同轮 `commands run test.quick` 实测(修复增量两轮后复跑): `6457 passed, 2 skipped`(53s; +1 即本批新增守卫 `test_kb_index_triggers_fully_indexed`)。

## 本改动面

- `.agents/skills/memory-bank/scripts/gen_kb_index.py`(+14/-22 含注释): 退役行内截断 —— 删 `SUMMARY_MAX=140`/`TRIGGER_MAX=120`/`_clip()`(含第一版「截断+可见警告」实现一并撤销), 摘要/触发词全量进索引, 体积约束回归分卷 cap 单点 `INDEX_BUDGET`; 退役决策与实测代价写进注释(别条件反射加回截断)。修 issue 26-11-18-0326(全库 120/370 坑档触发行曾超限, 尾部关键词静默路由不到)。
- 生成物重生成: `commands run kb.index` 19→31 件(全库索引 ~109K→~156K 字符, backend 3→4 / ops 1→3 / testing 6→9 / web-ui 6→9 索引文件, kb 维持 2 卷页, 各卷仍 ≤8000)。
- 新增守卫: `tests/test_memory_bank_structure.py::test_kb_index_triggers_fully_indexed` —— 每个主题/类条目的触发词全文逐字在生成索引页里(主题行+类表两路渲染路径), 防行内截断回归; docstring「测试计划」同步。
- 附带: `memory-bank/pitfalls/testing/sandbox-venv-in-workspace.md` 触发行裸命令手抄改 task id `env.sync`(原被截断遮住、全量进索引后被命令漂移检查暴露; 正文未动)。
- 记账: doc-forms.md「索引与检索」明示触发行全量进索引; issue 26-11-18-0326 翻 Done 带修法与复验; 任务档案 `26-11-18-memory-bank-index-truncation` 立档; 本切片。
