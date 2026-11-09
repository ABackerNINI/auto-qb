# effect-confirmation-stale-pointers

> 摘要: 修复 issue 26-11-08-0043: effect-confirmation.md 两处陈旧指针改指 commands_torrents.py:30 / runtime_commands.py:370(建议路径 server/routes/ 那条已失效, 按当前代码树改道); issue 翻 Done 补复验行与修复后补充; kb.check 与 test.full 全绿(见 kb.baseline), 基线切片 26-11-10-0327; 计划外点名 announce-epoch-semantics.md:12 同类指针未修未入池
> 最后活动: 2026-11-10 04:53

**R0(2026-11-10 03:29):** 修复 issue 26-11-08-0043: effect-confirmation.md 两处陈旧指针改指 commands_torrents.py:30 / runtime_commands.py:370(建议路径 server/routes/ 那条已失效, 按当前代码树改道); issue 翻 Done 补复验行与修复后补充; kb.check 与 test.full 全绿(见 kb.baseline), 基线切片 26-11-10-0327; 计划外点名 announce-epoch-semantics.md:12 同类指针未修未入池

**R1(2026-11-10 03:41):** 收口: 分批评审(全能档只读子代理)与接缝终审均零发现, review.check 0 条 / 通过 0 / 弃 0; 基线数字按齐平后组合树重跑誊写(全绿, 见 kb.baseline); 真机不适用(纯静态可验); 计划外 announce-epoch-semantics.md:12 同类指针仅点名未修未入池; 改动随本专题入库

**R2(2026-11-10 04:39):** 用户显式授权「一起修，然后提交」: scope-guard 例外 3(当场扩范围)生效, 原 R0/R1 记的 announce-epoch-semantics.md:12「未修未入池」状态由本轮取代 —— 该坑档第 12 行判定单点改指 commands_torrents.py:30 并标取证时间与 move-only 出处(计划 26-11-02-2342 §07 R5); issue §03 范围守恒段与基线切片「本改动面」同步留痕, 已修完不另建 Open issue。本轮开工同步快进 2 笔(391f133a→eee97f5b, 远端新增 tests/test_qbmanager_loop.py 守卫用例), 提交前在最终组合树重跑 test.full 全绿(5886 passed + 2 skipped, 见 kb.baseline), 数字按实测同步进基线切片与 issue 报告; kb.check 与 HTML 标签平衡机检全绿。评审包按最终 diff 重取(52 行 / 全能档 / 基哈希 4aac6ab2bce7), 复评轮与收口接缝终审由只读子代理执行

**R3(2026-11-10 04:53):** 收口: 修复循环第 2 轮复评与提交前接缝终审均零发现(全轮 review.check 累计 0 条 / 通过 0 / 弃 0); 闸门口径实算 21 行可评内容(记账类不计), 基哈希 4aac6ab2bce7 未漂移; 提交前 kb.check / HTML 标签平衡 / test.full(见 kb.baseline) 全绿; 真机不适用(纯静态可验); 按用户显式「提交」指令走 ship.commit 完成 commit+push
