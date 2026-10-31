# 2678 —— 详情面板模板重构 S7 收口基线(15 变体 + classic 全量实施完成)

> 摘要: 实施计划 [26-10-06-0838](../../plans/26-10-06-0838-plan-webui-detail-panel-redesign.html)
> S7 收尾基线。S1-S6 新增 2 条守阵(test_drawer_tpl_registry_wiring / test_drawer_tpl_classic_default)
> 与 S7 收口的坑档两篇(pitfalls/web-ui/)、档案回写后实测; passed 相对上一条
> [26-10-06-0731](26-10-06-0731-plan-playwright-e2e.md) 的 2676 + 4 **+2**(S1 两条新守阵)。
> 基线时间: 2026-10-06 16:20

**Refs:** memory-bank/tasks/26-10-06-webui-detail-panel.md, memory-bank/plans/26-10-06-0838-plan-webui-detail-panel-redesign.html

- 分支: feature/webui-drawer-templates @ S1-S7 七笔提交(S6 后 `b2a85edb`, 工作树含 S7 文档改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2678 passed + 4 skipped, 覆盖率 TOTAL 99%**, 单次采样 **45.37s**(wrapper 46.0s)
  - 语句 16021 / 未覆盖 166 / 分支 5472 / partial 144。
- 相对上一条基线 [26-10-06-0731](26-10-06-0731-plan-playwright-e2e.md)
  (2676 + 4 / 15823 / 163 / 5472 / 143): passed **+2**(S1 详情面板模板守阵两条), 分支 ±0;
  语句/未覆盖/partial 的分布差异(+198/+3/+1)含 0731 基线(远端 develop @ `0e278f12`)与本分支
  (fork 自 `63a1d7a7`)各自未互合的并行提交, 不逐一归因 —— 本分支侧的增量为 S1 两条守阵与
  S7 文档改动(零 Python 产品代码)。
- ⚠ 基线口径: 本基线在 feature/webui-drawer-templates 上实测; 与 develop 侧基线合流后按惯例
  以最新一条为准。
- 配套实测(同轮 S7, 详见任务档案 2026-10-06 16:3x 条目): 全矩阵 Playwright 巡检
  **283 断言全过 / 零 pageerror**(prism 全矩阵 16 选择 × 5 页签 × 3 档 + 两皮肤抽查 +
  刷新恢复 + 脏 id 回落 + 监听不叠加); 删变体演示(守阵红 → 页面回落 classic → 恢复转绿)全过。
