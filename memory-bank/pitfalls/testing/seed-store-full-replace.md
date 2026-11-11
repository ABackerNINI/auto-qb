# seed_store 传子列表 = 整体替换 by_hash, 不是增量追加

> 摘要: `tests/helpers.py::seed_store(mgr, torrents)` 的形参像「灌入这些种子」(增量), 实际语义是
> **整体替换** `store.by_hash`(与 store.refresh 全量轮同构: 新 dict 换引用, 旧条目即淘汰) —— 测试中途
> 想追加几个种子时把子列表传进去, 会把既有种子全部挤出快照, 症状是「刚还好好的用例突然 1/2 个种子
> 不存在」「部分组判定静默漏组」且无报错。追加口径 = 不传列表(取 `client.torrents` 全量)。
> 触发: seed_store, 全量替换, 整体替换, by_hash, 增量追加, 部分灌入, 挤出快照, 种子不存在, webui_helpers,
> _make_grouped_manager, 组员索引, 快照缺失

### 部分组闸门电池首轮全红: _seed_group 把 HA/HB 挤出快照 (2026-11-12)

- **触发**: `test_web_commands_bulk.py` 写闸门电池时抽了 `_seed_group/_seed_ungrouped` 助手再灌种子,
  顺手写成 `seed_store(mgr, tors)`(只传新种子) —— `_make_grouped_manager` 当初是**全量同灌**所以没踩,
  增量助手一传子列表, HA/HB 直接从 `store.by_hash` 消失: 已知种变缺失("1/2 个种子不存在"),
  部分组谓词对消失的成员静默漏判(known 过滤后组 A 不进判定)。
- **判别**: 症状 = 「新灌的种子在、既有种子消失」且 store 侧无异常; 断言 `store.get("HA") is None` /
  缺失计数文案异常即可坐实。看 helpers.py 源码: `new_by_hash` 只装传入列表, `store.by_hash = new_by_hash`
  整体换引用 —— 形参是 None 才走 `client.torrents.values()` 全量。
- **处置**: 追加种子一律 `seed_store(mgr)`(不传列表); helper docstring 显式注明「传子列表会整体替换,
  把既有种子挤出快照」—— 语义与形参名直觉相反, 属看了签名猜不出来的那一类。
