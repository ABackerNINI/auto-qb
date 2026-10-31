# 3559 passed + 4 skipped —— docmap 名录折行修复后全量基线

> 摘要: docmap 名录折行修复后全量基线
> 基线时间: 2026-10-18 08:47

## 验收数字

`commands run test.full` 实测(2026-10-18 08:45):

```
[ok] test.full (123.7s)
  TOTAL                                                18230    264   6120    191    98%
  3559 passed, 4 skipped in 121.17s (0:02:01)
```

口径注记: 3559 passed / 4 skipped / 总覆盖 98%(行覆盖 18230 语句, 264 未覆盖, 6120 部分覆盖); 4 个 skipped 为既有条件跳过, 非本轮引入。

## 本改动面

本轮(报告迁入 memory-bank + 守卫修复)改动的文件:

- `.agents/skills/memory-bank/scripts/gen_doc_map.py` —— `_name_list` 折行改以专题名为原子单位(旧按字节位 rfind 折行会把含空格的复合专题键从边界撕断); 同步修正 NAME_WRAP 注释里"零信息损失"的声明。
- `tests/test_docs_forms.py` —— 新增 `test_doc_map_name_list_never_splits_keys` 回归测试(折行落在复合键上时键不被拆断 + 确实发生了折行), 测试计划 docstring 同步登记。
- `memory-bank/reports/26-10-18-0826-report-missing-files-setlocation-recovery.html` —— 新建(由错放于 docs/ 的 markdown 可行性报告迁入并转换为规范 HTML 报告件)。
- `memory-bank/reports/26-10-18-0818-report-group-relocate-restart-free.html` —— 修正两处 stale 路径引用, 补 doc-refs 双向认领链, kb.bump 落 R1。
