# 7000 passed, 6 skipped —— relocate 收尾簇七件修复总收尾全量基线

> 摘要: relocate 收尾簇七件修复总收尾全量基线
> 基线时间: 2026-11-22 20:35
**Refs:** memory-bank/tasks/26-11-22-backend-relocate-foreign-gate.md

## 验收数字

`commands run test.full` 实测(2026-11-22, Windows, 终验 rc=0 两次复验 148.4s / 169.6s, 树 = 0a88e51a[重放后同一树内容], 分支 fix/relocate-gate-closeout, 工作树含覆盖小轮未提交件 tests/test_relocate_foreign.py + pytest.ini 与本轮文档件):

```
TOTAL                                                31412    109  11190     94    99%
7000 passed, 0 failed, 6 skipped
Required test coverage of 99.5% reached. Total coverage: 99.50%
```

全绿 rc=0(测试 7000P/0F/6S, 覆盖率 99.50% 过 Windows 线 99.5, tests/conftest.py `COVERAGE_FLOOR_WIN = 99.5`)。与上基线(26-11-22-1727, 树 = 9f158a3c, 6988P/6S)相比: 两树间 5 笔提交(839eb6e5 文档 / 独立小文档提交一笔[原独立小提交, 后经 rebase 撤销 —— 同一修复已由远端 8763ca51 顺带落地] / 153d7c3e·4a51f60a·0a88e51a 三批代码)带入新代码与新测试面(TOTAL Stmts 31384→31412 / Branch 11180→11190), passed 6988→7000(批1-3 新测试面 + 覆盖小轮定向测试), Miss 110→109 / BrPart 94→94 持平, skipped 6→6 持平。passed/skipped 数字自本切片起以本切片为权威。

### 覆盖率闸红旧记录的归因与处置(2026-11-22 补覆盖小轮, 用户拍板)

总收尾首轮 test.full 覆盖率闸红(6999P/0F/6S, miss 111/BrPart 95, 99.50% 未达)已处置, 根因不是批1-3 新代码失覆盖:

- **根因**: 缺口 relocate_foreign.py:434-436+434 True 臂(池内候选排队期从 store 消失→rec None 出队)是**既有行**, 覆盖确定性被批2 F2 改变 —— 旧「每拍重算不排空」下消失候选下拍必重入池覆盖恒定, F2 消费即排空后只在「消失候选恰好留池尾」执行, 池序 = frozenset 迭代序(hash 种子随机)每轮 ~57% 覆盖 / 43% 缺失抖动, 即 miss 净增 1 行 + 1 部分分支的来源(闸过 109/94 = 99.5000%, 闸红 111/95 = 99.4954%)。
- **修法**: tests/test_relocate_foreign.py 新增 test_foreign_drain_vanish_pop_pool_order_independent(_foreign_enqueue 直控池序, 断言池清空 + 消失不记账 + 零 qB API 调用), 4/4 轮 missing 435-436 恒覆盖; pytest.ini :19 注释对齐 conftest 单点(Windows 99.5 / 其余 99.0)。

## 本改动面

本轮 = 计划 26-11-22-1714 总收尾(纯文档 + 测试跑面, 代码树 = 0a88e51a[重放后同一树内容] 未动):

- 档案 memory-bank/tasks/26-11-22-backend-relocate-foreign-gate.md: Summary 精修(修复轮完成态)+ 进度日志追加 R3 修复轮节(三批落地/接缝终审/D3 对 0434 D12 修订留痕/计划外事项/真机 S4 待办)。
- 架构附件 memory-bank/architecture/attachments/relocate-foreign-torrent.md 侦测(D12)行改写现役口径: 字段 pending_added_diff、语义「累积游标 + take_added_diff 消费即排空」(F2 对 0434 D12「只读不排空」的修订); 历史件(计划 HTML/issue/档案历史轮次/基线快照)一律不改写。
- pitfalls: backend/save-path-equality-sibling-trap.md 复踩 +1(2026-11-22 第三踩: 2076c889 有意加回的等值面残留, F3 自锁; 触发条改三踩 + 处置/守阵行补 F1 per-file 精判)+ 新立 backend/duplicate-impl-absorb-tolerance-gap.md(F7 副本收编漏搬防御容忍教训); `kb.index` 重跑(33 生成物)。
- 会话切片 kb.wrap(R3 行 + 档案 Updated)。
- 覆盖率闸红旧记录已处置收口: 用户拍板补覆盖小轮(另一子代理落地, 根因批2 池序依赖 + 定向测试恢复恒覆盖 + pytest.ini 注释对齐), 本切片数字已更新为终验 rc=0 全绿(见上「验收数字」与其下归因小节)。
