# 1684 passed + 1 skipped / 0 failed —— 搜索匹配收敛服务端单点(三页统一消费 searchHits)

> 摘要: 治"同一查询语法三份实现(服务端行级匹配 / 种子页 filters.js 客户端行过滤 / 追剧页剧名
> 整句 includes)修三遍" —— 匹配单点收敛 `views.py::search_torrents`, 候选行扩为 名字/站点/分类/
> 保存路径/每标签/每文件名(行级 AND + 负词按行作废口径不变; 站点/分类/路径/标签行即时读 store,
> 文件行仍走索引 building 渐进); 前端删净第二/第三实现(filters.js 四函数 / shows.js 剧名 includes /
> app.js searchHitsQ), 三页统一消费 searchHits, 守阵改反漂移(复活即红)。顺带治了"搜站点/标签
> 分组·追剧页搜不到"的跨页不一致。
> 基线时间: 2026-09-26 23:32
> 档案: 26-09-26-webui-search-query-syntax(延续)

- **测试增量**: +1(`test_web.py::test_search_torrents_facet_rows`: 站点/分类/标签/路径行命中,
  `by` 定位首个通过的行类别 + 行级负词不整种子误杀); 改写 `test_frontend_search_syntax_wiring`
  为反漂移(前端复活任何"函数名+括号"匹配实现即红; node vm 对账脚本随客户端解析器一起删除 ——
  没有对账对象了); `test_search_torrents_file_match` 补季包回归(HA 包名不含"12"、集文件
  S01E12 行命中, by="file"); 模块头「## 测试计划」docstring 同步。
- **中途回归抓真坑 1 次**: 坑档案条目重写时字段写成 `判别(史)`/`处置(2026-09-26 收敛)`,
  机械守阵 `test_kb_pitfall_entries_have_required_fields` 红了 test.full —— 字段名是字面匹配,
  装饰性后缀不行; 改回标准三字段即绿。

TOTAL 91%(11316 语句 / 816 未覆盖 / 3732 分支 / 332 partial; views.py 97%;
test.full 19.1s; 覆盖率口径见 [../baseline.md](../baseline.md))。
