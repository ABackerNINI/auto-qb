# 1685 passed + 1 skipped / 0 failed —— 正词逐词跨行 AND 定案(每个正词命中任一候选行即可)

> 摘要: 正词口径两日三轮演进定案(26-09-26 行级「多词须同行」→ 26-09-27 分轨(全称行跨行/文件行
> 整行,中间态)→ 26-09-27 逐词跨行): 每个正词/短语命中**任一候选行**(名字/站点/分类/保存路径/
> 标签/文件行)即可、行可不同 —— 治「minions mteam」(名字×标签)与「delta 03」(包名 Gamma.Delta
> 在名字行、集号只在集文件行)两轮跨字段漏配; 26-09-26「文件行不参与跨行」边界随用户实测推翻
> (召回优先, 季包吸词代价知情接受), 守阵 `row_level_and` 改名 `cross_row_and` 并翻转断言。
> 负词种子级否决不变(26-09-27-0045)。基线时间: 2026-09-27 01:38
> 档案: 26-09-26-webui-search-query-syntax(延续)

- **测试增量**: 总数不变(1685): `test_search_torrents_row_level_and` →
  `test_search_torrents_cross_row_and` 重写(新增报障原型夹具 Gamma.Delta + Gamma.E01-E03,
  5 条「跨行不命中」断言翻转为命中 + 「AND 不退化 OR」守卫); views.py 删无引用 `_row_passes`;
  模块头「## 测试计划」与 6 处口径措辞同步; 前端 3 处注释同步(纯注释)。

TOTAL 91%(11305 语句 / 815 未覆盖 / 3720 分支 / 331 partial; views.py 97%;
test.full 19.7s(1 采样, 上轮 20.1~20.2s); 覆盖率口径见 [../baseline.md](../baseline.md))。
