# 基线 · 1909 passed + 3 skipped / 91% —— issue 清偿路线图 W1 收尾

> 摘要: 清偿路线图(plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1「流程与闸门卡点」
> 5/5 全清后的收尾基线。五笔清偿提交对 pytest 面**零增量**(唯一新增守阵 test_unstaged_delete_uses_rm_cached
> 在 `.commands/my-commit-flow/` 包内, 走 test.pkg 不入 test.full 口径;ui_smoke.cjs 是冒烟 harness 非 pytest)
> —— 通过数与上一基线 26-10-01-1930 持平为预期。
> 基线时间: 2026-10-01 20:03, develop @ 59725443(五笔已入库;工作树含本次收尾回写文档改动未提交)。

TOTAL **1909 passed + 3 skipped / 91%**(13278 语句 / 1047 未覆盖 / 4408 分支 / 433 partial,
test.full 24.3s, rc=0)—— 与 26-10-01-1930 基线**同数持平**(未覆盖/partial ±4/±2 为逐轮采样浮动,
结论不变); 耗时在近期全量采样区间(21-31s)内。包内脚本测试另计: **test.pkg 75 passed**
(含本波新增的未暂存删除守阵); 双 UI 冒烟 **96 项 0 失败**(随 0602 清偿实测)。

## W1 五笔提交要点(每条单独提交, 明细在各自档案)

1. **931e231d** · issue 26-09-28-0128(ship.commit 撞已暂存删除): 根修已随 my-commit-flow v3(4ba6cb7f)
   落库(commit.py 按文件存在性三分流), 本轮补未暂存删除分支守阵 + 清偿链。
2. **2fc34fc2** · issue 26-09-20-2212(同名测试遮蔽): 根修已随 0c18fcda 落库(两条同名守阵合并为
   test_truth_hold_matches_truth_push_cap, 零断言弃置), 本轮只补复验 + 清偿链。
3. **9486a7cd** · issue 26-09-22-2311(FakeConfig 类级共享可变属性): 根修已随 54c83ac3 落库
   (__init__ deepcopy 成实例属性, 整类污染面根除), 原必红顺序复测两绿, 零代码改动。
4. **9aeb4400** · issue 26-09-30-0602 colwidth: 产品无缺陷, harness 守阵选键错(默认隐藏列从未固化
   过意图宽度)—— 修为隐藏前直取 `_visibleCols[2].key`, 断言语义升级回守阵目标。
5. **59725443** · issue 26-09-30-0602 ctx03: 两个入池假设(ElementHandle 脱挂竞态/真实 UI 缺陷)均被
   仪器化探针排除 —— 真因是行几何中心被 `.site-chip`(@click.stop)占据吞掉修饰键点击, Ctrl+click
   落点改行左缘 (8,8); 新坑已入 pitfalls/testing/smoke.md。

机检同轮: kb.index 16 索引重生成; gen_issues_index.py 重跑零漂移(issues/_index.md 中 W1 五条已在
Done 分区); kb.check 主键纪律 OK(259 文档 / 160 专题无缺主键; 切片数 81>70 与 cap 债务 1 项为既有
债务, 不拦提交)。

**Refs:** tasks/26-10-01-commands-shipflow-staged-delete-fix.md ·
tasks/26-10-01-test-truth-hold-shadowed-guard.md ·
tasks/26-10-01-test-fakeconfig-shared-state-isolation.md ·
tasks/26-10-01-test-ui-smoke-clearance.md(Refs 覆盖两条 0602)
