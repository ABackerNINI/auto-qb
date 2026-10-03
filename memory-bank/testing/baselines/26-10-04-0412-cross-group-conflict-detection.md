# 基线切片 26-10-04-0412 — 跨组文件交叉检测与紧急处置 S0-S5 全段完成

> 摘要: 计划 [plans/26-10-04-0107](../../plans/26-10-04-0107-plan-cross-group-file-conflict.html)
> 五步全部落地 (issue 26-09-22-2221 → Done): S1 配置键 `grouping.cross_group_conflict_check`
> (默认关) 全链贯通 / S2 检测核心 (物理路径全量展开 + 组对聚合警告, 纯内存零触盘) / S3 处置
> (暂停涉事下载方 + 组对去重 + 冲突消除清记录) / S4 Web 组视图 cross_group_conflict 标记 /
> S5 集成回写 (本切片)。新增用例 19 条: test_config_schema 3 + test_grouping 15 (S2 检测 8 +
> S3 处置 7) + test_web 1; 其中 1 条 POSIX 专用 (大小写不误报断言) 在 Windows 按设计 skip。

- 时间: 2026-10-04 04:12 (GMT+8); 分支 feat/cross-group-file-conflict (rebase 到 develop 2ab1f6a3 之上, 线性)
- 五笔实现提交: S0 认领 e5a43f75 / S1 配置键 90a250cf / S2 检测核心 e07f48c2 / S3 处置 9234dbfd / S4 Web 提示 efab3b7e
- 命令: `commands run test.full`
- 实测: **2441 passed + 4 skipped, 36.16s, 覆盖率 TOTAL 99%**(14361 语句 / 135 未覆盖 / 4864 分支 / 106 partial)
- 相对上基线(26-10-04-0353: 2423 passed + 3 skipped)净增 19 用例: 2445 总数 - 2426 = 19; passed +18,
  skipped 3→4 (+1 = `test_cross_group_case_only_posix_no_false_positive` 在 Windows skipif, 与 19 条
  新增中 18 过 1 skip 严格吻合); 全绿零回归
- 未验证面: 真机走查 (dev.run --dry-run 验警告路径) 本轮明确跳过 (计划里属可选项), 留待用户;
  真实 junction 别名场景仅测试内 `_winapi.CreateJunction` 覆盖
