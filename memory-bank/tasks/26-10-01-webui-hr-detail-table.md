# 26-10-01-webui-hr-detail-table — WEBUI HR 在线核实详情表

**Status:** In Progress
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** issue 26-10-01-2137 的计划轮: 只读调研(表①种子维度字段后端基本已有未导出, 表②按 --hr-status 表格化读法数据全有)后出计划 plans/26-10-01-2216(12 节, 含表①/表②字段清单、展示设计 mockup、四阶段实施、§9 六个待拍板决策点), 提交 6093a6b9 已推 Gitee。**停在 §9 拍板, 拍板前不动工**。

**Topics:** webui-hr-detail-table

## 原始请求

用户在 issue [26-10-01-2137-feat-webui-hr-detail-table](../issues/26-10-01-2137-feat-webui-hr-detail-table.html) 提出 WEBUI HR 在线核实详情表需求(表①种子维度 / 表②按 --hr-status 表格化), 要求先调研数据可用性再出计划; 本轮按「阶段1 只读调研 → 阶段2 出计划 → 阶段3 收尾回写」推进。issue 保持 Open, 认领待拍板后。

## 思考过程与决策

- 方案与取舍冻结在计划文档, 本档案只记执行与验证(计划 §7 四阶段 / §9 决策点 / §10 拍板记录区)。
- 调研结论: 表①数据可用性瓶颈在后端导出面(字段已存在未导出), 非采集缺失; 表②读法数据全有, 表格化偏前端; 另有 6 个待拍板决策点横在实施前。
- 制品链: issue(Open) ↔ 计划(Open) 已 doc-refs 双向互链; 本档案与 issue/计划仅正文互指、不进 doc-refs 协议链 —— 计划/issue 冻结不补反向声明, 声明即义务(认领 issue 时再建档案↔issue 双向对)。

## 实现计划

四阶段路线、表①/表②字段清单、展示设计与 mockup 见 [plans/26-10-01-2216](../plans/26-10-01-2216-plan-webui-hr-detail-table.html); 本档案不复制。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| 计划轮 | 调研 + 计划 26-10-01-2216(§9 决策点①-⑥ 待拍板) | 完成(26-10-01) |
| 实施 | 计划 §7 四阶段, 依赖 §9 拍板, 从阶段 1 起步 | 未开工 |

## 进度日志

- **2026-10-01 计划轮完成并入库**(提交 6093a6b9, 已推 Gitee): 调研 + 计划 26-10-01-2216(12 节) + plans/_index.md 重建登记 + issue 头部补 doc-refs 互链(状态保持 Open); 机检 test_docs_forms.py 10 passed。流程事件: ship.commit 首跑失败(远端被并行 clone 推进 f0ddd486, 重叠文件为生成物 plans/_index.md), 按失败行指引 sync 合流重跑成功(复发记账: pitfalls/git/sync-pull.md)。
- **2026-10-01 立档与收尾回写**: 按 skill 立档阈值 #3(「阶段 N」长周期表述)与 #4(已产出 plans/ HTML 制品)立档 —— 纯文档产出但阈值 #4 明文命中, 不得跳过; test.full 闸门过(纯知识库轮零代码变更), 基线切片见 testing/baselines/ 最新一条。
