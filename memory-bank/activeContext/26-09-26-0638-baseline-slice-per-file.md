# 测试基线切片化(baseline 单文件 → 每条一档)

> 摘要: 实施 plan 26-09-26-0529: baselines/ 存量 37 条迁移 + gen_baseline_recent.py + kb.baseline 任务 + baseline.md 长青化 + 引用回写 13 处; 合流 e7b9299(schema 版本链)后合并树重测 1664+1 持平, 守卫全绿。已提交推送。
> 触发: baseline, 切片化, gen_baseline_recent, kb.baseline, testing/baselines, 基线窗口
> 最后活动: 2026-09-26 07:03

## 状态

- **已完成(全部落地)**: 机制四触点(`_common.py` role+cap / `gen_baseline_recent.py` 新脚本 / `kb.baseline` 任务 + `kb.check` 集合 / 守卫测试 5→6 + SKILL cap 表) · 存量迁移 37 条(09-26×9 / 09-25×22 / 09-24×6, 链接加深一层, 时分回填+当日序位) · `baseline.md` 转口径长青入口 · `baseline-history.md` 删除 · 引用回写(AGENTS / README / SKILL DoD / testing 存根 / techContext / file-conventions / run.md / pitfalls×3 / 冷库回指针×2 / 任务档案坏链×1) · 档案 `26-09-26-memory-bank-baseline-slice-per-file` 立档 + 计划 doc-refs 双向认领链 + doc-status→Done。
- **关键考据(对计划的一处修正)**: 计划给合流重测 / 1639 的文件名前缀「1700」保留, 但切片头「基线时间」字段取 git 考据值(04:38 = c8f98f4 / 03:54 = d0c39bf) —— 该切片时钟偏移; 若照抄 17:00, kb.baseline 最新就不是 1641 定稿, 违反计划 §06 验收「最新为 1641 定稿」。
- **既有缺陷顺手修复(用户指令)**: `commands run kb.active --check` 原被引擎拒参(run 无 `<args>`) —— 已补 `<args>`(与 kb.baseline 同法), 实测可达且绿。
- **验证**: test.full **1640 passed + 1 skipped / TOTAL 92%**(11013 / 787 / 3656 / 330)与基线持平 · kb.check 六项全绿 · kb.baseline 列 3 条、最新 = 1641 定稿 · doc.caps PASS。
- **下一步**: 「提交」已触发并走完 my-commit-flow: `.git` 备份 → e7b9299 ff 合流(唯一冲突 baseline.md 保长青版; 对方条目转切片 `0633-schema-version-chain`; 对方 progress 超 cap 10,064 已最小压缩回线 9,995, ⚠ 贴顶) → 合并树重测 1664+1 持平(切片 `0703`) → ship.commit / ship.push。
