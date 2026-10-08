# 方案 C: 手抄测试数字上守卫(判据族 B) + 存量冻结

> 摘要: 用户报「基线维护成本高, 每轮要改切片/档案/切片正文/commit 至少 4 处」→ 分析可行性(方案 A/B/C),
> 拍板 C: 数字只留 `testing/baselines/` 切片一处, 其余一律引用不手抄; 给 `check_wording.py` 加判据族 B
> (裸测试数字), 存量冻结(只拦新增)。口径单点: `baseline.md` / `SKILL.md` / `AGENTS.md`。
> 最后活动: 2026-10-08 08:42

## 正在进行

- 收尾回写: 档案二轮 / 本切片 / 基线切片 / `kb.index` 重建 → 提交。
- 待办: 无(方案 C 完整落地)。

## 已完成

- 可行性分析(问答轮): 四处写入点 + 方案 A(交 test 脚本) / B(只写 commit msg) / C(折中) 优劣对比。
- 守卫判据族 B: `scan_text_numbers` / `list_test_numbers` / `count_test_numbers` + `FROZEN_TEST_NUM_COUNT`
  存量冻结; CLI `--count-numbers` / `--list-numbers`; 红验通过。
- 口径单点: `baseline.md` 口径段 / `SKILL.md` 新节 + DoD / `AGENTS.md` 产出口径; 守阵 2 条。
- 闸门: `kb.check` 全绿; `test.full` 通过(见 kb.baseline 最新切片)。

## 关键判断

- 真成本是同一数字的**四个副本**(切片正文的「逐位对比」最重), 不是切片本身 —— 切片保事实源, 其余改引用。
- 存量 394 处非日期裸数字**冻结为债务**(多数是不可变历史记录, 改写=篡改历史; 与 cap 债务制同构)。
