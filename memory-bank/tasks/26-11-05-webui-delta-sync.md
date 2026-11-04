# 26-11-05-webui-delta-sync — store 增量 removed 同轮 pop 隐患: 真机复测 + 防御修(issue 26-10-11-2045)

**Status:** Done
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** 真机探针证实 qB 5.2.3 增量响应从不同轮下发同 hash 的 patch+removed; 按方案 1 落防御修(changes 构造单点过滤), 红绿双验 + M4 钉子改道, 全量绿(见 kb.baseline)
**Topics:** webui-delta-sync
**Refs:** memory-bank/issues/26-10-11-2045-bug-torrents-store-removed-pop-readd.html

## 原始请求

1. 用户: 「认领 memory-bank/issues/26-10-11-2045-bug-torrents-store-removed-pop-readd.html, 使用测试qb复测」
2. 复测结论汇报后, 用户拍板(AskUserQuestion): 「方案1 防御性一行修 + 单测」→ issue 置 Done

## 思考过程与决策

- 复测形态: 纯 qB 行为探针(读侧), 直连测试 qB 走 `/sync/maindata`, 不需要产品主循环参与 —— 环境2 副实例 56590(qB 5.2.3)。
- 探针 v1 有方法论缺陷被自纠: trigger 后才从 rid=0 重拉全量, 窗口内积累的 removed 被全量响应冲掉 → 假阴性。v2 改为: 先取全量基线 rid, 轮询全程连续(50ms), 删/重加作为定时事件在轮询循环内触发; 另设「只删不重加」对照组验证 removed 通道本身工作。已入坑档(pitfalls/testing/real-probe-rid-window.md)。
- 真机结论: 5 组试验中两通道**从不同轮命中同 hash** —— 间隔≈3ms 时事件完全合并(无 removed 只有 patches); 间隔 0.3/1.5/5s 时 removed 先行一轮、patch 后续一轮。触发前置在 qB 5.2.3 不成立。
- 修复落点改道(与 issue 建议方案 1 同向但落点不同): 不在 pop 循环加判断, 而在 `changes` 构造单点过滤(store.py:429-432)把「本轮 patches 已含的 hash」与跳检窗 hash 一起剔除 —— pop 循环/全量轮/added-removed 上报三处同时自洽(只改 pop 会留下「行保留但 removed 上报仍含该 hash」的自相矛盾)。已按 create-issue 口径在 issue「修复后补充」说明改道原因。
- 全量跑出的失败钉子 `test_m4_same_tick_add_remove_and_pending_removed_overlap` b 段属**既有契约改道**: 老断言把「同拍一增一删经 R5 交叉抵消成响应不含该 hash」钉为正确, 但该契约自相矛盾(store 行被 pop 而镜像保持旧态, 两边分叉), 按新语义改为 patch 赢/行按 upsert 下发/store 与镜像一致。
- 处置决策由用户拍板: 真机不发生仍选防御性修复(一行级代价消解顺序竞争), 非「仅记档」。

## 实现计划

1. 认领: issue 置 In Progress + 状态日志 + kb.index。
2. 复验锚点: store.py 现状(pop 循环 480-481; skipping_hashes/restore_torrent 为立档后新防线, 证据 D 已过期)。
3. 真机探针: 5 组(对照 + 4 间隔), 记录每 rid 的 patches/removed。
4. 结论请用户拍板处置方向。
5. 修: store.py changes 过滤单点; 新用例先红后绿; M4-b 钉子改道。
6. 收尾: code-review(全能档, 1 只读子代理) → 发现 2 条行号漂移当场修 → 立档/基线/坑档/kb.wrap。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 认领 + 状态翻转 + 索引 | Done(2026-11-05) |
| 2 | 锚点复验(代码现状 + 过期证据辨认) | Done(2026-11-05) |
| 3 | 真机探针 5 组(56590, qB 5.2.3) | Done(2026-11-05) |
| 4 | 处置拍板(用户选方案 1) | Done(2026-11-05) |
| 5 | 防御修 + 新用例红绿 + M4 改道 | Done(2026-11-05) |
| 6 | 全量绿 + 收口评审 + 立档/基线/坑档 | Done(2026-11-05) |

## 进度日志

### R0 · 立档 (2026-11-05)

- 真机探针: 对照组 removed 通道正常单独下发; gap≈3ms 完全合并无 removed; gap 0.3/1.5/5s 均 removed 先行、patch 后续, **零同轮**。
- 修复: store.py:429-432(changes 过滤单点); 新用例 test_store_apply_removed_yields_to_same_round_patch(修复前红/修复后绿); M4-b 钉子改道(patch 赢)。
- 实测: 全量绿, 覆盖率过闸(数字见 kb.baseline, 切片 26-11-05-0540-store-removed-patch-wins)。
- review: blocker 清零, 修 2(minor 1 + nit 1, 均为 issue HTML 行号漂移, 引文过 review.check 后当场修), 入池 0; 评审档位 = 全能(diff 76 行, 1 只读子代理)。

- 2026-11-05 05:41 认领 issue 26-10-11-2045: 真机探针复测(qB 5.2.3 零同轮双通道) + 方案1 防御修(store.py changes 过滤单点) + M4 钉子改道 + 全量绿(见 kb.baseline) + review blocker 清零(修 2 入池 0)
