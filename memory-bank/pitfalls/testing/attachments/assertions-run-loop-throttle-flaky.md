# 断言有效性 · 主循环节流用例偶发翻红原文(外迁)

> 摘要: `pitfalls/testing/assertions.md`「`test_run_loop_throttles_without_stop_event` 偶发翻红」条原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: test_run_loop_throttles_without_stop_event, 全量 1 条红, 墙钟时序, 覆盖率, 偶发超时, 全新临时根

## `test_run_loop_throttles_without_stop_event` 偶发翻红

- **触发**: 全量跑出 1 条红。
- **判别**: 同一份代码全量跑两次: 一次 `1097 passed + 1 failed`, 一次 `1098 passed` ——
  它是**墙钟时序**断言(主循环节流间隔), 在覆盖率开启 + 全量负载下偶发超时;
  单跑 `tests/test_qbmanager_*.py` **43 passed 恒绿**。
- **处置**: 全量跑出 1 条红时**先换全新临时根重跑一次再判回归**, 别急着改代码 ——
  **真回归会稳定复现**。
