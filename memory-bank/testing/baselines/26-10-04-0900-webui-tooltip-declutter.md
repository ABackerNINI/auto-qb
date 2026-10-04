# 基线切片 26-10-04-0900 — webui 复述型 tooltip 全量移除(67 处)+ 不复活守卫

> 摘要: 按判定报告 [reports/26-10-04-0815](../../reports/26-10-04-0815-report-webui-tooltip-declutter.html) 移除 webui 全部 67 处复述型 tooltip
> (A-G 组 66 处散在 10 个共享模板 + H1 columns.js; dialogs.js A5 精简而非全删), 新增守卫
> test_removed_redundant_tooltips_stay_removed(tests/test_web.py)钉死已删文案。
> 基线时间: 2026-10-04 09:00
> 档案: [tasks/26-10-04-webui-tooltip-declutter](../../tasks/26-10-04-webui-tooltip-declutter.md)

- 时间: 2026-10-04 09:00 (GMT+8); 基线 = 分支 webui-tooltip-declutter @ `e8203a3c`(实施 6 提交全落地, 树净)
- 分支: webui-tooltip-declutter @ `e8203a3c`
- 命令: `commands run test.full`
- 实测: **2462 passed + 4 skipped, 28.54s(pytest 计时, 单次采样), 覆盖率 TOTAL 99%**(14650 语句 / 139 未覆盖 / 4894 分支 / 108 partial)
- 相对上基线(26-10-04-0752: 2460 passed + 4 skipped)净增 2, 两条均可归因: ①本分支守卫
  test_removed_redundant_tooltips_stay_removed(+1, 本分支对 tests/ 的唯一改动); ②判定报告
  reports/26-10-04-0815 HTML(`72a7d274`)落盘晚于上基线运行时点, test_docs_forms 按文件收集 +1
- 覆盖率四元组与上基线完全一致 —— 纯属性删除 + 守卫, 无新逻辑面, 符合预期
