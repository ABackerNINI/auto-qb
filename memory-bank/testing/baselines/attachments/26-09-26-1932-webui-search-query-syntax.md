# 1669 passed + 1 skipped / 2 failed + 1 error(全部为并发会话在途改动) —— 搜索语法调研报告落盘 (纯文档轮)

> 摘要: 只新增报告/档案/切片三份制品 + kb.index 生成物 + roadmap 蒸馏 1 切片, 无代码/测试改动 ⇒ 自有增量 0 条;
> 套件级红全部归属**同 clone 并发会话**(19:27 起在途: `webui-long-path-open` 任务档案 + `infra/utils.py` fs 长路径改动), 与本轮制品无关
> 基线时间: 2026-09-26 19:32
> 档案: 26-09-26-webui-search-query-syntax

(制品 `memory-bank/reports/26-09-26-1918-report-webui-search-query-syntax.html`, doc-topic `webui-search-query-syntax`;
本轮为**纯调研轮**, 未改任何源码 / 配置 / 测试)。

- **新增**: 报告 1 份(六系查询语法对比 / F1–F5 公共性 / websearch 三件套 + 行级语义推荐设计),
  任务档案 1 份, activeContext 切片 1 份; 认领链双向声明(报告 doc-refs ↔ 档案 Refs, **仓库根相对路径** ——
  文件相对路径会被 `test_claim_chain_is_bidirectional` 判"目标不存在", 本轮实测踩中并修正)。
- **闸门红排障实录**(3 次全量 + 守卫定向复跑):
  ① 首跑 8 红 —— 新制品未登记索引, `kb.index` 后 6 绿;
  ② 剩 2 红 —— 我方 doc-refs 相对路径口径(改根相对后绿) + activeContext 切片 41>40 超 cap;
  ③ cap 处置: 最老切片 `26-09-19-0000-docs-plan-review-wrapup`(7 天, 仅剩低优先遗留项)蒸馏进
  `progress/roadmap.md`「其它功能」一行(遗留项本就被 Open issue 26-09-19-2122 追踪)后删除, 守卫绿;
  ④ 终态 2 failed + 1 error —— `test_claim_chain_is_bidirectional`(并发会话档案认领链单向 ×4)、
  `test_web.py::test_api_fs_dirs_endpoint` + `test_affected_truth_reads_qb_directly_not_sync_snapshot` teardown
  (并发会话 `utils.py` fs 路由改动在途)—— **全部非本轮制品**, 未代修(不碰他会在途工作)。
- **测试增量**: 0 条新增 / 0 条改写。

TOTAL 91%(11268 语句 / 827 未覆盖 / 3710 分支 / 339 partial; 本轮机跑 15.8–22.7s, 覆盖率口径见
[../baseline.md](../baseline.md); 语句数较上条基线 +57 为并发会话在途 `utils.py` 改动所致, 非本轮)。
