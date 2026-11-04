# 5340 passed + 10 skipped —— store 增量 removed 同轮防御修 + M4 钉子改道后全量基线

> 摘要: store 增量 removed 同轮防御修(changes 构造单点过滤) + M4 镜像钉子改道(patch 赢)后全量基线
> 基线时间: 2026-11-05 05:40
**Refs:** memory-bank/issues/26-10-11-2045-bug-torrents-store-removed-pop-readd.html

## 验收数字

`commands run test.full` 实测(2026-11-05 05:40, Windows, 本机):

- 汇总行: `5340 passed, 10 skipped, 1 warning in 137.41s (0:02:17)` —— 0 failed
- 覆盖率 TOTAL 表末行: `TOTAL 24463 69 8390 38 99%`(语句 24463 / 缺 69 / 分支 8390 / 部分覆盖 38); 闸门判定 `Required test coverage of 99.5% reached. Total coverage: 99.66%`
- 口径注记: 全量阈值判定通过(退出码 0); 副作用台账越界 0。缺口净额 ±0(miss+partial 69+38 与上基线 26-11-05-0439 逐位一致; 测试数 +1 = 新用例 test_store_apply_removed_yields_to_same_round_patch)。

## 本改动面

- `src/auto_qb/torrents/store.py`: `_apply` 的 `changes` 构造(429-432)补防御过滤 —— 增量/全量轮 `removed` 中「本轮 patches 已含的 hash」不再计入删除(26-10-11-2045: 先写 patches 后 pop 的顺序竞争兜底; 真机 qB 5.2.3 实测两通道从不同轮命中同 hash)。
- `tests/test_torrents_store.py`: 新用例 `test_store_apply_removed_yields_to_same_round_patch`(红绿双验: 修复前同轮双通道把刚写的行 pop 掉且 removed 含该 hash; 修复后 patch 赢、纯 removed 照常 pop); 头部 docstring 测试计划同步。
- `tests/test_webui_delta_mirror.py`: M4-b 钉子改道 —— 原断言「同拍一增一删经 R5 交叉抵消, 响应不含该 hash」按新语义改为 patch 赢(store 行保留 + 镜像按 upsert 下发 + removed 不报); 头部 docstring 同步。
- `memory-bank/`: issue 26-10-11-2045 翻 Done(复验/修复后补充留痕), 任务档案 26-11-05-webui-delta-sync 立档, 坑档 pitfalls/testing/real-probe-rid-window 新增。
