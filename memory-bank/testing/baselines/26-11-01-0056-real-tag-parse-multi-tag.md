# 4348 passed + 2 skipped —— tests-real 多标签解析修复(issue 26-10-31-1215)

> 摘要: tests-real 多标签解析修复(issue 26-10-31-1215): lib/guard.py::tag_set 单点, seed.py/guard.snapshot 同改
> 基线时间: 2026-11-01 00:56
**Refs:** memory-bank/issues/26-10-31-1215-bug-real-tag-parse-multi-tag.html

## 验收数字

`commands run test.full` 实测(2026-11-01 00:54, 随本专题入库):

```
TOTAL                                                21805    145   7394    122    99%
4348 passed, 2 skipped in 176.25s (0:02:56)
```

- 通过数较上一基线(26-11-01-0025, 4327) +21: 全部来自本轮开工同步进来的远端 7 笔提交, 与本改动无关 —— 本改动只动 `tests-real/`(不在 testpaths, 全量测试收不到), 用例面零增减。
- 首跑曾 3 failed(test_memory_bank 索引双向一致守卫): 原因是收尾新建坑档/切片后未及时重建索引, `kb.index` 后单文件复跑全绿; 本基线是重建后的干净复跑。
- skipped 仍为 tests-real 真机轨(不在 testpaths)与平台态 skip。

## 真机面(独立轨, 不进本数字)

36596 真机, 256K 假种子 + 经 qB API 手动加第二标签 `MISSING`(tags=`MISSING, real-fake`):

- 修复前: `real.seed.list` 报「共 1 个种子, 其中自造 0 个」—— 失明复现。
- 修复后: `real.seed.list` 自造 1 个可见; `guard.snapshot(skip_tags=('real-fake',))` 保护面为空、假种子未被暂停(state 保持 stalledUP); `real.seed.rm --all --yes` 命中 1 个连数据删除, 复查归 0。

## 本改动面

- `tests-real/lib/guard.py`: 新增 `tag_set()` —— qB tags 字段 strip 版集合解析单点(docstring 写明禁令); `snapshot` 的 `ours()` 改走它。
- `tests-real/seed.py`: `_fakes` 改走 `guard.tag_set`, 不再自带裸 `split(",")`。
- 主仓代码与 `tests/` 未动。
