# 基线 · 2000 passed + 3 skipped / 93% —— HR 在线核实详情表计划(26-10-01-2216)四阶段收官

> 摘要: 计划 26-10-01-2216(issue 26-10-01-2137)阶段4 收官基线 —— 契约守阵通电 + 全量回归, 四阶段实施全部完成(doc-status → Done)。
> 档案: [plans/26-10-01-2216-plan-webui-hr-detail-table.html](../../plans/26-10-01-2216-plan-webui-hr-detail-table.html)。
> 基线时间: 2026-10-02 01:40, develop @ b2b1e96d(工作树含阶段4 契约守阵与收尾回写, 未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告 —— 两侧都重测前不当作两侧事实源)。

TOTAL **2000 passed + 3 skipped / 93%**(13,279 语句 / 774 未覆盖 / 4,444 分支 / 330 partial,
test.full 27.27 / 26.30s 两采样, rc=0)。**精确综合口径**(coverage json 导出, 行 + 分支出口合计):
**16,517 / 17,723 = 93.20%**(语句 12,505/13,279 = 94.17%, 分支 4,012/4,444 = 90.28%)。
相对 P0 基线(26-10-02-0025 @ 41aa9f00: 1997 passed + 3 skipped)**+3 用例**: 表① 接线守阵
(d3d4d987)/ 表② 接线守阵(b2b1e96d)/ 两表消费键契约守阵(本笔); 语句面 13,377 → 13,279(-98,
上一切片在并行合流现场实测, src/*.py 两树间无提交差异, 语句面以本切片为当前事实源)。

## 本笔改动面 (阶段4)

- 契约守阵 `test_frontend_hr_contract_keys_match_backend`(tests/test_web.py, 计划 §11 字段级对照
  收拢): 从前端源码双向提取消费键断言 ⊆ 后端 to_dict 键集 —— 表① `e.*`(模板 aqb:hr-detail-table
  锚段 + hr_status.js 行辅助三函数)对照 `EntryDetail`; 表② `s.*`/`ls.*`(hr_status.js 全文件 +
  aqb:hr-diag 锚段)对照 `SiteStatus`/`LaneStatus`; 每组带核心键在场断言防提取器失效变恒真。
  后端侧字段面闭集已由 test_entry_details_field_surface 钉死(阶段1), 本守阵补的是前端消费侧。
- **守阵通电即抓出存量幻键** `ls.lane_text`: `LaneStatus` 无此字段(to_dict 不含, 路由不补)⇒ 表②
  波次表档位徽章人话渲染为空(阶段3 交付缺陷; 复发记账 pitfalls/web-ui/contract-api.md)。修复属
  src/ 改动不在阶段4 范围, 守阵以「已知幻键白名单恰为一条」钉住, 修后收空(反向变红提醒收口)。
- 收尾回写(纯知识库): 计划 §12 v3 / issue 26-10-01-2137→Done / 任务档案置 Done / activeContext
  切片完成态 + progress 迁出 / modules/overview.md HR 行 + 根 README「HR 在线核实」段跟进新端点
  与两张表 / pitfalls 三处(sync-pull 复发+2 · contract-api 复发+1 · 新坑 subagent-mixed-workspace)。
- TODO.md: 计划点名的 L15+L196 两条核实为**已在开工前清账提交 c1b6d53f(移除已入池项)先行移除**,
  原文核实确为本诉求两条, 本阶段无可再动。

## 与拍板的对应

六项全按推荐(①a ②b ③a ④b ⑤a ⑥a)+ 默认项(表① 含失踪行)维持; remain_seconds 不导出
(test_entry_details_field_surface 钉死); 四笔实施提交 f5ce07bd / 964a55ba / d3d4d987 / b2b1e96d +
阶段4 收尾本笔。
