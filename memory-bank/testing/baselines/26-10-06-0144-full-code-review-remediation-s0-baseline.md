# 2622 —— Code Review 修复实施计划 S0 基线 (六批 S1–S6 修复的对照点)

> 摘要: 计划 [26-10-06-0103-plan-full-code-review-remediation.html](../../plans/26-10-06-0103-plan-full-code-review-remediation.html)
> 第 0 步 (S0): 落一条修复开工前的全量测试基线, 作为后续 S1–S6 六批修复逐批对比的对照点。
> 本轮 src / tests 零改动, 基线用途 = 记录修复开工前 test.full 真值。
> 基线时间: 2026-10-06 01:44

**Refs:** memory-bank/plans/26-10-06-0103-plan-full-code-review-remediation.html

- 分支: develop @ fb461fea(会话开工 `my-commit-flow.sync` 所得, 已同步)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2622 passed + 4 skipped, 47.24s, 覆盖率 TOTAL 99%**
  (15624 语句 / 166 未覆盖 / 5400 分支 / 139 partial; 门槛 98% 达标)
- 相对上一条基线 [26-10-05-2058](26-10-05-2058-webui-toast-error-history-plan.md)
  (2622 passed + 4 skipped @ 2130450c, 15815/166/5400/139): passed / skipped / 未覆盖 / 分支 / partial
  五项逐字相同, 仅语句总数 15815 → **15624**(-191); `git diff 2130450c..HEAD` 确认两个 commit 之间
  **除 memory-bank 文档外零文件改动**, src / tests 完全一致, 用例数也一致 —— 该差异非代码变化所致,
  按本次实测 15624 为 S0 对照真值。
- 本切片作为六批修复 (S1–S6) 的对照点: 每批修完对比 passed / skipped / 覆盖率五项, 预期修复只应
  让 passed 不降、未覆盖 / partial 不升; 若出现回退先查该批改动。
