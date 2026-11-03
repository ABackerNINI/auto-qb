# webui-search-uncovered-dedup

> 摘要: 修复 issue 26-11-03-0254: filteredGroups 渲染期用未过滤 this.groups 现算 groupedNow + 「不在命中集 / 已归组」两道闸(排 facet/push 之前); 静态守阵按语义位置 + 三皮肤 4 场景 e2e; 全量见 kb.baseline; issue 置 Done
> 最后活动: 2026-11-03 11:42
**Refs:**

**R0(2026-11-03 04:54):** 修复 issue 26-11-03-0254: filteredGroups 渲染期用未过滤 this.groups 现算 groupedNow + 「不在命中集 / 已归组」两道闸(排 facet/push 之前); 静态守阵按语义位置 + 三皮肤 4 场景 e2e; 全量见 kb.baseline; issue 置 Done

**R1(2026-11-03 10:54):** 补住 CI 收集期 BASE_URL 导出缺失: spec 改 baseUrl() + 新增 e2e 回潮守阵; test.full 4936 passed/2 skipped, e2e 定向 18/18

**R2(2026-11-03 11:42):** 同轮抬 e2e 预算(dev.e2e 2700s / playwright job 40m)并补坑档; site-alerts 全量顺序污染入池 test/standard Open
