# 全面 Code Review · 批 B1 完成 (hr/service.py + model.py + status.py)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 B1 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点同 commit。3 文件 / 2,930 行全部逐文件过目, 重点维度 R1 R3 R5 R8 逐文件勾选。发现 3 条 (均 P3): B1-01 store() 惰性建跨线程无锁 (良性, 契约脆弱点) · B1-02 status.py:40 F401 死导入 next_allowed_at · B1-03 _do_wave except HrFetchError 无 Retry-After 尾段不可达 (撞车池 bug 26-10-02-0441, 复核确认并补齐调用链证据)。复验不登记: _sign_releases verified 覆写全路径不可达结论成立 (池 26-10-02-0526)。底册状态漂移两项待 S6 核验: clock 注入 (0526-refactor) 与 _prune_index 双体 (0441-refactor) 疑似已修, finish-wave 告警去重 (0441-bug) 已修。工具源: bandit 0 条; ruff 152 条采纳 1 (F401)。test.full 2610+4 / 99% 与基线逐位持平。发现表落盘 [报告草稿批 B1 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 11:30

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · 前序切片 [批 A](26-10-05-1100-full-code-review-batch-a.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档稳态降频切片 + HR 计划链 → 坑档 backend 四主题 → LOC 降序逐文件读码 → ruff+bandit 逐条复核 → 登记去重)。
- 发现表 3 条回填报告草稿批 B1 章节 (含逐文件勾选结论 / 复验不登记项 / 工具提示源小结 / 基线对照)。
- test.full: 2610 passed + 4 skipped / 99% (15511/5342, 164/138) 与基线切片逐位持平, 无漂移。

## 遗留 / 待办

- 池内 3 条 HR 条目状态与代码现状漂移 (clock 注入 / prune_index 双体疑似已修, finish-wave 去重已修) —— 待 S6 汇总轮统一核验处置, 本轮未动池条目。
- 批 B2 (hr/ 其余 20 件 4,651 行, R6 R7 R8 R9) 待评审; worker 并发边界与站点凭据面在 B2 继续核对。
