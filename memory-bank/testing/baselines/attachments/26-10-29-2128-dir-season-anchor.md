# 4071 passed + 2 skipped(根) —— 目录季标记锚定放宽为「季标记+发布后缀」后全量基线

> 摘要: 目录季标记锚定放宽为「季标记+发布后缀」(issue 26-10-29-1329) 后全量基线
> 基线时间: 2026-10-29 21:28
**Refs:** memory-bank/issues/26-10-29-1329-bug-b-r08e03-dir-season-anchor.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`; 2026-10-29 实测, 全量 151.36s, 建档 21:28):

```
  TOTAL                                                21070     99   7136    103    99%
  4071 passed, 2 skipped in 151.36s (0:02:31)
```

- 汇总行: **4071 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本轮新增 11 个用例项: test_tvshows::TestFiles 后缀目录参数化 7 例 + 多季合包负测 1 条 + 白名单外尾词负测 1 条 + refine 端到端 2 条(season_inferred 留痕 / 名称侧不置位); 另 1 条既有用例补 season_inferred 断言(不新增项)。
  - 「2 skipped(根)」为既有环境条件 skip, 与本轮无关。
  - 修前红验: 以第 02 节取证串复现(带后缀四形态返 (None, [5])、refine 落 season=1, 同一输入路径) —— 新用例未在旧实现上逐条重跑, 不作「修前全红」断言; 修后新守阵全绿。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/core/tvshows.py` | 目录段季标记(issue 26-10-29-1329): 新增 `_DIR_SEASON_SUFFIX_RE`(发布后缀白名单: 画质/来源/Complete/字幕词)与 `_dir_season`(词形复用 `_SEASON_PATTERNS`, 锚定放宽为「季标记 + 可选发布后缀」, `_MULTI_SEASON_RE` 命中判未知); `parse_files` 三形态内联正则退役改调 `_dir_season`; `ParsedRelease` 增 `season_inferred: bool = False`; `refine_with_files` 名称侧无季标记时置 season_inferred=True(文件推断与兑底 1 两路都留痕), 名称侧已有季号的分支不再重复 replace season |
| `src/auto_qb/webui/views.py` / `runtime.py` | 「replace 字段集仅 kind/season/ep」三处互指注释补 season_inferred 留痕位(不改剧键结论不变) |
| `tests/test_tvshows.py` | TestFiles 后缀目录参数化 7 例(Season 2 (1080p)/S02 Complete/第2季(1080p)/Season 02 [1080p]/2nd Season 1080p/Show S02 Complete/Show.S02.Complete) + 多季合包(S01-S04/第1-4季)与白名单外尾词(Season 2 of Show)两条负测 + refine 端到端 2 条 + 既有 unknown 抢救用例补 season_inferred 断言; 头部「## 测试计划」补 2 行 + 用例名录补 5 行 |
| `memory-bank/issues/26-10-29-1329-bug-b-r08e03-dir-season-anchor.html` | 认领链 + 状态流转 Open → Done(复验/实际修法/验证方式回填) |

**未改**: 标题侧 `_SEASON_PATTERNS` 词形与优先级(目录段只复用词形, 锚定差异收进 `_dir_season`/`_DIR_SEASON_SUFFIX_RE`); `refine_with_files` 无季信息时「按第 1 季」的既有口径(parse_release 同款, 仅加留痕); episodes 侧解析与视图聚合逻辑。
