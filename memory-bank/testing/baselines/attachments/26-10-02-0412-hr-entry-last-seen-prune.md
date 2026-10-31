# 基线 · 2219 passed + 3 skipped / 97.53% —— HrEntry.last_seen 写入点清偿(W1 2/3)

> 摘要: issue 26-10-01-2335 清偿(`_merge_seen` 刷新 last_seen + INDEX_RETENTION 清理复活 + `_prune_index` 合并单点, 测试净增 2 条)的收尾基线;
> 相对上一基线(26-10-02-0345: 2217+3 / 97.51% @ bc24631b)增量 = 测试用例 +2 / 语句 13,278→13,272(删类内重复 `_prune_index`) / 分支 4,444→4,438 / partial 88→86 / 覆盖率 97.51%→97.53%。
> 档案: [tasks/26-10-02-hr-entry-last-seen-prune.md](../../tasks/26-10-02-hr-entry-last-seen-prune.md)。
> 基线时间: 2026-10-02 04:12, develop @ bc24631b; 工作树含本轮改动(未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2219 passed + 3 skipped / 97.53%**(13,272 语句 / 298 未覆盖 / 4,438 分支 / 86 partial,
test.full 29.1s, rc=0; 阈值 94%)。

## 闸门过程记录

- 一次通过, 无 flaky 出现(已知 flaky test_budget_unit_wait_and_caps 本轮未触发, 未动)。
- 定向: 新增 test_merge_seen_refreshes_last_seen / test_index_retention_prune_revives(两波三波链),
  既有 prune 单元收敛到模块级单点并补「恒 0 存量不淘汰」断言; webui 契约守阵
  (test_frontend_hr_contract_keys_match_backend)随全量绿, EntryDetail 字段面零变更。
- 迭代记录: 首轮 test.quick 抓出两处 —— ①新测例回执断言算错行集(entries==2 应为 1, 本测例无第 22 条目),
  本轮自改; ②memory-bank 三守阵红(新档案未登记), `kb.index` 重建后绿。
