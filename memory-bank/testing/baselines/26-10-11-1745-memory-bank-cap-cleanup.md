# 3124 —— cap 债务清零轮(索引改渲染口径 + 两件手写文档外迁)

> 摘要: 用户令「清理 cap 债务」(开工 `doc.caps -- --strict` 报 **5 项**)。三类病根分别治: ①`issues/_index.md` 31,196 —— 无摘要口径 27,336 = cap **108%**, 条目数本身就是病根 ⇒ 走**视图归档**(生成器 `CLOSED_KEEP=60` 只渲染已关闭状态最近 60 条, 报告原地不动, 全量清单另落 `issues/attachments/_archive.md`), 31,196 → 16,960; ②`tasks/_index.md` 25,974 / `pitfalls/web-ui/_index.md` 25,940 —— 无摘要口径仍 < cap ⇒ 压渲染口径(`gen_tasks_index.SUMMARY_MAX` 60→30; `gen_kb_index` 新增摘要/触发词截断 140/120), → 20,190 / 15,986; ③两件手写文档按「触顶切最老一半到 `attachments/`」外迁 —— 档案 `26-10-08-test-mutation-audit.md` 56,960 → 23,480(进度日志 R0–R14 外迁), `progress/implemented-webui.md` 23,251 → 10,362(六条胖条目外迁 + 41 条同质指针行压成一行, 零信息损失)。新增非 `_index.md` 生成物使 `test_gen_all_declares_exactly_all_indexes` 红, 在 `EXTRA_GENERATED` 显式登记(未把断言放宽为恒真)。收口 `doc.caps -- --strict` **0 债务** / `doc.links` 绿 / `kb.check` 全绿。
> 基线时间: 2026-10-11 17:45

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 `8d76b3eb`→`cfe9a8d5`; 工作树含本轮全部改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3124 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16464 语句 / 148 未覆盖; 守阵修复前同批为 3123 passed + 1 failed —— 失败项即 `test_gen_all_declares_exactly_all_indexes`)
- 与上一基线差: **+1 passed**(新增登记常量后该守阵转绿; 本轮**未新增测试函数**, 未改源码)

## 债务清偿前后(守卫口径 `char_count`)

| 件 | 角色 cap | 清理前 | 清理后 |
|---|---|---|---|
| `issues/_index.md` | index-auto 25,200 | 31,196 | 16,960 |
| `tasks/_index.md` | index-auto 25,200 | 25,974 | 20,190 |
| `pitfalls/web-ui/_index.md` | index-auto 25,200 | 25,940 | 15,986 |
| `progress/implemented-webui.md` | evergreen 20,000 | 23,251 | 10,362 |
| `tasks/26-10-08-test-mutation-audit.md` | task 48,000 | 56,960 | 23,480 |

- 条数债务(切片数 64 / `SLICE_COUNT_LIMIT` 70)本轮**本就不超**, 未动。
- 全部外迁正文的相对链接已整体上移一层(`../` → `../../`), 机检 `doc.links` 绿。
