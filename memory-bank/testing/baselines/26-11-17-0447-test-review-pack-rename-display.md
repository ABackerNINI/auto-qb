# 6268 —— pack 展示面 rename 对齐批全量基线

> 摘要: pack 展示面 rename 对齐批全量基线
> 基线时间: 2026-11-17 04:47

## 验收数字

`commands run test.full` 实测(2026-11-17 04:52, Windows; 3m20s):

```
TOTAL                                                27855     73   9822     78    99%
Required test coverage of 99.5% reached. Total coverage: 99.59%
6268 passed, 2 skipped in 198.22s (0:03:18)
```

包内守阵: `commands run test.pkg` **520 passed + 15 subtests**;`ship.gate` 预跑全绿(命中 5 条)。

## 本改动面

- `.commands/review/scripts/review_pack.py`: cmd_pack 文件清单 name-status 钉 `--no-renames`(rename 拆 D 旧路径 + A 新路径,与实算口径对齐)+ 新增「改名对」提示行(第二次 `diff --name-status -M`,两侧任一可评才显示,仅提示不进计行/清单/敏感面)+ 模块 docstring 同步。
- `.commands/review/scripts/test_review_pkg.py`: 翻转 `test_lists_changed_renamed_deleted_untracked`(旧路径 `[已删除]` 进清单 + 「删除文件」专用行断言)、新增 `test_rename_pair_hint_lists_both_sides`、测试计划 docstring 同步。
- `.commands/review/config.toml`: review.pack note 同步(顺带清掉遗留「diff 统计」旧措辞)。
- `.agents/skills/code-review/SKILL.md`: ③ 机械五件描述同步 rename 拆分与改名对提示。
- `tests/test_docs_forms.py`(计划外修复, scope-guard 例外 1, 用户拍板白名单): `test_plans_reports_have_no_md` 加逐件点名 `ARCHIVE_MD_EXCEPTIONS` 收编 `reports/` 存档特例 .md(a54213b9 撞红 develop tip),特例文件不在场即红防死条目;测试计划 docstring 同步。
- 回写件: tasks 档案 / active-context 切片 / pitfalls/kb/review-pack-rename-double-count.md + `kb.index` 重建(不计行面)。
