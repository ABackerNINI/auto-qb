# 6748 —— 6748 passed, 6 skipped —— backend-relocate-foreign-torrent(计划 26-11-20-0434)收尾基线

> 摘要: 6748 passed, 6 skipped —— backend-relocate-foreign-torrent(计划 26-11-20-0434)收尾基线
> 基线时间: 2026-11-21 13:41
**Refs:** memory-bank/tasks/26-11-20-backend-relocate-foreign-torrent.md

## 验收数字

`commands run test.full` 实测(2026-11-21 13:47, Windows, 2m25s):

```
TOTAL                                                30533     84  10876     82    99%
6748 passed, 6 skipped, 8 warnings in 145.69s (0:02:25)
```

覆盖率闸门通过(99.5% 线无 Required FAIL 行, rc=0)。收口批曾一红: 首跑 99.48% < 99.5%(relocate_foreign.py 新面 30 miss + relocate_exec.py 本批面 3 miss), 收口批补 20 测收敛到 99.60% 后本切片全绿; 3 条结构性不可达防御行(relocate_foreign.py:234/303/380)核实留档不凑测。

## 本改动面

本切片 = 计划 26-11-20-0434(S1-S6)五批 + 收口批的终态快照, 本轮改动:

- T1(S1+S2a, df63f10a): 配置键 relocate.foreign_torrent(schema/models/validation/loaders) + store.last_added_diff 每拍原始差集。
- T2(S2b, 7b3e1baa): relocate_foreign.py 侦测面(差集消费/四时机全量兜底/候选分类/清单比对/notified 账/有界 FIFO) + store.sync_epoch。
- T3(S3, d8082739): 场景 A 零破坏纳入(job.hashes + spec 双写/恢复账并入/pending_tag 增量) + 测试 data_dir 夹具修红线污染。
- T4(S4, 787eb46a): 收尾守卫(_rewrite_cover_of 分流/WAIT 支/孤儿告警) + 链式闭包解析器。
- T5(S5, b3c4c3b7): 场景 B 只通知(WARNING + WebUI relocate 面板 foreign 行标注/浮窗/抽屉/筛选档, e2e 双皮肤)。
- 收口批(本轮): 接缝终审修复(relocate_exec.py 词表单点) + 覆盖率收敛 20 新测(tests/test_relocate_foreign.py +17 / test_relocate_exec_verify.py +2 / test_relocate_exec_reconcile.py +1) + S6 文档回写(架构 hr-groups.md relocate 篇 foreign 小节/计划翻 Done/档案收口/坑档 test-data-dir-prod-fallback-write 新条 + 4 issue 入池 + 本切片)。
