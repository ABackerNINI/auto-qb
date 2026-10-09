# 2824 —— memory-bank 三项 cap 债务清理轮 (档案外迁 · tasks/issues 索引压截断)

> 摘要: 用户开清理会话「整理文档doc.caps」—— `doc.caps` 报 3 项 cap 债务一次收口: ①`tasks/26-10-08-backend-test-web-split.md` 62,661 → 6,382(实施记录整段外迁 `tasks/attachments/`) ②`tasks/_index.md` 26,162 → 22,869(`gen_tasks_index.SUMMARY_MAX` 80 → 60) ③`issues/_index.md` 26,576 → 24,298(`gen_issues_index.SUMMARY_MAX` 24 → 12)。两项索引均判「摘要顶爆」(无摘要口径 < cap)故走渲染口径、不外迁条目。`doc.caps -- --strict` 债务清零。
> 专题: memory-bank-cap-debt
> 基线时间: 2026-10-09 08:32

**Refs:** memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2824 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16479 语句 / 161 未覆盖 / 5696 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 两次采样 31.10s / 42.72s(墙时 33.1s / 44.6s) ⇒ 区间约 **31~43s**
- **本轮零 `src/` 零 `tests/` 改动** —— 改动面全在知识库与 skill 常量, 不进 `--cov=src` 统计, 也不在 `testpaths(tests/)` 里。

## 改动面(全部为知识库维护)

- `memory-bank/tasks/26-10-08-backend-test-web-split.md` —— 62,661 → 6,382: S1 勘察结论(329 fn 映射表 22,712)+ S2–S8 逐批实施记录 + 进度日志(10,746)原文外迁; 3,713 字流水型 `**Summary:**` 压成 543 字。
- `memory-bank/tasks/attachments/26-10-08-backend-test-web-split-history.md` —— **新建**(53,791), 原文逐字保留; 随迁的 9 条 `../` 相对链接整体上移一层。
- `.agents/skills/memory-bank/scripts/gen_tasks_index.py` —— `SUMMARY_MAX` 80 → 60 + 判据注释。
- `.agents/skills/create-issue/scripts/gen_issues_index.py` —— `SUMMARY_MAX` 24 → 12 + 判据注释。
- `memory-bank/pitfalls/kb/cap-counting.md` —— 新条目「外迁到 `attachments/` 时相对链接要整体上移一层」(复发 2)+「生成式索引撞 cap」补第三次复撞(无摘要口径已占 cap 85%); 头部摘要/触发词同步。
- `memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md` —— 本清理轮记录 + 最后活动。
- 生成物 `_index.md` 族(20 个重建)。

## 守卫

- `commands run doc.caps -- --strict` **债务 0 项** / `kb.check` 绿(主键纪律 527 文档 · 275 专题, 认领链闭环; 日期守卫 / 回写守卫无违规) / `doc.links` 绿 / `doc.drift` 绿(0 处手抄)。
- **范围外(未动, 转告用户)**: 切片数 104 > 70 的**条数债务**仍在(不在 `doc.caps` 口径内, 属 `kb.active` 侧), 需另开清理会话。
