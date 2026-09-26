# 1685 passed + 1 skipped / 0 failed —— 负词名字行整种子否决(治「cat and -11」facet 行捞回)

> 摘要: 单点化把候选行扩到 站点/分类/保存路径/标签(同日 2332 切片)后, 行级负词出现泄漏面 ——
> E11 单文件的种子名行含 "11" 已按行作废, 却被不含 "11" 的保存路径行整颗捞回(2026-09-26 报障
> 「cat and -11」命中 "The.Cat.and.the.Dragon.S01E11.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv",
> 复现 `by="path"`)。修法: 名字行负词升级为**整种子否决**(`search_torrents::_name_vetoed`,
> 即时轮与文件轮同受约束), facet 行不得越过名字行负词捞回; 文件行/facet 行维持行级作废
> (合集包非负词行仍可命中, 调研报告 26-09-26-1918 §5.2 拍板不变)。
> 基线时间: 2026-09-26 23:55
> 档案: 26-09-26-webui-search-query-syntax(延续)

- **测试增量**: +1(`test_web.py::test_search_torrents_negative_name_veto`: 名字含负词的种子
  路径行不得捞回 / 无负词时名字行照常命中 / 文件轮同受名字否决 / 去负词后文件行命中对照);
  模块头「## 测试计划」docstring 同步。
- **收尾踩坑 1 次(已回写)**: 为拿引擎截掉的覆盖率表, `cmd //c` 复刻 test.full 的 `set "TMPDIR=…"`
  写法 ⇒ Git Bash 引号转义使 `set` 失效回落 `H:\Temp`, 收尾删 `pytest-of-*` 撞删除拦截层
  (rc=1, 点号全过 —— tmpdir.md「不是测试红」条, 复发 +1); 兜底改 bash 前缀
  `TMPDIR='R:/Temp/auto-qb/tests'` 实测 rc=0。
- **另采样到零点竞态假红 1 次(非本改动面, 未修)**: 23:59 跨零点跑全量时
  `test_expr_eval.py::test_legacy_condition_equivalence` 红 —— 表达式侧用 setup 期缓存
  (23:59·周五)判 True, legacy `DateTimeCondition.match` 重读实时钟(已翻 00:00·周日, dow=0
  不在 [1,7])判 False。跨零点跑必然偶发, 是否入池待用户定夺。

TOTAL 92%(11320 语句 / 815 未覆盖 / 3734 分支 / 330 partial; views.py 98%;
test.full 19.4~20.1s(3 采样); 覆盖率口径见 [../baseline.md](../baseline.md))。
