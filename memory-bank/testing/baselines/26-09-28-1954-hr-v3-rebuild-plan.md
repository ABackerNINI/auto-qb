# 1828 passed / 3 skipped —— HR 在线核实 v3 模型重建计划立档(纯文档轮, 代码零改动)

> 摘要: 用户定调推翻 v2 模型(每轮全量翻页违背「首波全量/后续增量」口径 / legacy+split 双频控混杂 /
> 熔断停用回落本地是漏 HR 隐形炸弹 / 40 键配置面失控) ⇒ v3 重建计划
> [plans/26-09-28-1932](../../plans/26-09-28-1932-plan-hr-verify-rebuild.html) 立档(doc-status Open, 待批准实施):
> 四行判定表(未核实恒受管束硬编码, 本地做种达标=satisfied 只作展示不产生放行) + 波次引擎(全量/增量/续翻三波型 +
> 收波判据①整页已见②放行方向段封闭, 反算考核期 P 机制删除) + 单频控三键(min_interval/max_requests_per_day/
> max_pages_per_wave) + 熔断删除改指数退避(1H→24H) + 空清单人工对账戳(--hr-confirm-empty);
> 配置 40→14 键。收尾回写: activeContext 切片 / 任务档案滚动区与 Refs / docs/hr-online-verify-docs.md 清单 /
> v2 审计报告与 1815 计划 doc-refs 双向认领链补声明。
> 基线时间: 2026-09-28 19:54 (develop @ 5bc43784, 与 Gitee 主线齐平)
> 档案: plans/26-09-28-1932-plan-hr-verify-rebuild.html (doc-status Open)

- test.full: **1828 passed / 3 skipped**, TOTAL **91%**(12576 语句 / 917 未覆盖 / 4246 分支 / 390 partial),
  耗时 21.64s —— 与前基线(26-09-28-1840)逐位一致, 纯文档轮零漂移。
- 中途: 新计划 HTML 首次全量跑红 4 条(test_docs_forms: 缺 doc-* meta + 两索引未再生), 补 meta +
  `commands run kb.index` 再生成后绿; 期间一次 Python 脚本替换把两份审计报告 doc-refs meta 闭合引号截断
  (守阵即红暴露), `git checkout --` 恢复后改用精确锚点重插, 守阵 10 项全绿 —— 认领链守阵对 meta 损坏的敏感度得到实证。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
