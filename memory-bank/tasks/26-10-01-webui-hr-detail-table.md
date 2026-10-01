# 26-10-01-webui-hr-detail-table — WEBUI HR 在线核实详情表

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-02
**Summary:** issue 26-10-01-2137 全程收官: 计划 26-10-01-2216 拍板(六项全按推荐 ①a②b③a④b⑤a⑥a + 默认项含失踪行)后四阶段全部实施 —— 阶段1 后端导出(f5ce07bd, 顺带入池 last_seen issue 26-10-01-2335 = 964a55ba) → 阶段2 表① 渲染(d3d4d987) → 阶段3 表② 排障视图(b2b1e96d) → 阶段4 契约守阵+全量基线+收尾(本笔); 阶段4 守阵通电抓出存量幻键 ls.lane_text(白名单钉住, 补修 7cff3adb 闭环); 真机走查留给用户。

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
| 拍板 | §9 六项 + 非阻塞默认项 | 完成(26-10-01, 六项全按推荐, 计划 §10 回填) |
| 阶段1 | 后端: 种子明细导出 API(`EntryDetail`/`entry_details` + `GET /api/hr/sites/{site}/entries`), 提交 f5ce07bd | 完成(26-10-01) |
| 阶段1 副产 | 入池 HrEntry.last_seen 无写入点 issue 26-10-01-2335, 提交 964a55ba | 完成(26-10-01) |
| 阶段2 | webui: 表① 全量详情表渲染 + 档位筛选, 提交 d3d4d987 | 完成(26-10-01) |
| 阶段3 | webui: 表② 排障视图(`<details>` 默认收起), 提交 b2b1e96d | 完成(26-10-01) |
| 阶段4 | 契约守阵 + test.full 基线 + TODO/收尾回写, 随本笔提交 | 完成(26-10-02) |
| 补修 | 阶段4 守阵抓出的幻键 ls.lane_text —— LaneStatus 补 lane_text 字段(_lane_statuses 填充, LANE_TEXTS 单点), 守阵白名单收空, 提交 7cff3adb | 完成(26-10-01) |
| 真机走查 | 计划 §11 手动走查(真实数据下游回归 / 三套 UI 目检 / 三态走查) | 留给用户(需真实 qB 与 HR 站点数据) |

## 进度日志

- **2026-10-01 计划轮完成并入库**(提交 6093a6b9, 已推 Gitee): 调研 + 计划 26-10-01-2216(12 节) + plans/_index.md 重建登记 + issue 头部补 doc-refs 互链(状态保持 Open); 机检 test_docs_forms.py 10 passed。流程事件: ship.commit 首跑失败(远端被并行 clone 推进 f0ddd486, 重叠文件为生成物 plans/_index.md), 按失败行指引 sync 合流重跑成功(复发记账: pitfalls/git/sync-pull.md)。
- **2026-10-01 立档与收尾回写**: 按 skill 立档阈值 #3(「阶段 N」长周期表述)与 #4(已产出 plans/ HTML 制品)立档 —— 纯文档产出但阈值 #4 明文命中, 不得跳过; test.full 闸门过(纯知识库轮零代码变更), 基线切片见 testing/baselines/ 最新一条。
- **2026-10-01 拍板并开工**: 用户对 §9 六个决策点逐条拍板, **六项全按推荐项**(①a ②b ③a ④b ⑤a ⑥a, 计划 §10 已回填); 非阻塞默认项(表① 行集含失踪行)维持默认。
- **2026-10-01 阶段1 完成并入库**(提交 f5ce07bd): `hr/status.py` 新增 `EntryDetail`/`entry_details()`(§3 P0+P1 全集, 档位·下载量排序含失踪行, `need_seed_text` 上收为口径单点, CLI 行为不变)+ `SOURCE_TEXTS`; `routes/hr.py` 新增 `GET /api/hr/sites/{site}/entries`(未启用 400 / 未接入 404 / 线程未启动 409); tests/test_hr_status.py(6 例)+ test_web.py 端点 5 例 + 路由金清单 67 条。顺带调研发现 `HrEntry.last_seen` 无写入点(INDEX_RETENTION 清理死分支), 入池 issue 26-10-01-2335 并提交(964a55ba)。ship.commit 内部同步撞「远端前移+树脏」, 按 backup→stash→sync→pop 预案化解。
- **2026-10-01 阶段2 完成并入库**(提交 d3d4d987): 表① 全量详情表渲染 —— settings-detail.html 站点卡片三层结构 + 档位筛选 chips(本地过滤) + 「数据截至」时间戳(拍板⑥) + 「上次核实(放行判定)」独立列名(拍板④); hr_status.js `loadHrSiteEntries` 按站点按需拉一次(不轮询, 失败置错误态不阻塞分区); `.hr-detail-table` 样式三套 UI 成对(prism 拆 components/views 两件)。ship.commit 内部同步再撞「远端前移+树脏」, 同预案化解。流程事件: 前一子智能体中途夭折(配额耗尽)遗留混合工作区(计划外模板抽离与计划内改动同文件交织), 按 backup diff → 精确回退越界段落 → 续派显式核对 git status 白名单处置(新坑: pitfalls/git/subagent-mixed-workspace.md)。
- **2026-10-01 阶段3 完成并入库**(提交 b2b1e96d): 表② 排障视图 —— 站点级 kv 行(`hrsKvRows` 拼行单点) + 各档波次明细表(`lanes[].detail` 首获展示位), 收进原生 `<details>` 默认收起(拍板①a); 数据全来自 /api/hr/status 现有载荷, 零新请求零定时器, 展开态不持久化; `.hrs-diag`/`.hr-diag-kv`/`.hr-wave-table` 三套 UI 成对。
- **2026-10-02 阶段4 完成并随本笔入库**: ①契约守阵 `test_frontend_hr_contract_keys_match_backend`(计划 §11 字段级对照收拢)—— 从前端源码双向提取消费键, 断言表① `e.*` ⊆ `EntryDetail.to_dict`、表② `s.*`/`ls.*` ⊆ `SiteStatus`/`LaneStatus.to_dict`(后端侧闭集钉法 test_entry_details_field_surface 挡不住「上游改键+同步改 expected」的静默落空, 阶段1 已钉后端面故不重复); **守阵首次通电即抓出存量缺陷**: 波次表消费 `ls.lane_text` 但 `LaneStatus` 无此字段 ⇒ 档位徽章人话渲染为空(阶段3 交付, 复发记账 pitfalls/web-ui/contract-api.md; 修复属 src/ 改动不在阶段4 范围, 守阵以「已知幻键白名单恰为一条」钉住, 已汇报待拍板)。②TODO.md 核实: 计划点名的 L15/L196 两条**已在开工前清账提交 c1b6d53f(移除已入池项)中先行移除**, 原文核实确为本诉求两条, 本阶段无可再动 —— 偏差汇报。③全量基线切片(testing/baselines/ 最新一条, 数字见 kb.baseline)。④收尾回写: 计划 doc-status→Done + §12 v3 / issue 26-10-01-2137→Done(阶段1-3 实施期间状态未及翻 In Progress, 流程缺口随 Done 行补记) / 本档案 / activeContext 切片(实施完成态, 实施摘要迁出 progress/implemented-webui.md) / modules/overview.md HR 行 + 根 README「HR 在线核实」段跟进新端点与两张表 / pitfalls 三处(复发+2、复发+1、新坑)。
- **2026-10-01 补修幻键 ls.lane_text**(提交 7cff3adb, 已推 Gitee): 阶段4 守阵白名单钉住的待修项按拍板执行 —— `LaneStatus` 新增 `lane_text` 字段由 `_lane_statuses` 填充(复用 LANE_TEXTS 单点); 守阵幻键白名单收空恢复严格闭集, 另加 lane_text 逐档值断言(A 考察中/B 已达标/C 未达标, 且钉「取自 LANE_TEXTS 单点」)。实测 test.quick 2000 passed, 3 skipped; EntryDetail(表①)字段面闭集与 CLI `--hr-status` 既有用例不受影响(纯新增字段)。
- **遗留(给用户)**: 计划 §11「手动走查」需真实 qB 与真实 HR 站点数据(生产红线, 未跑 dev.run): 真实数据下游回归(空变有值点亮此前不可达分支, pitfalls/web-ui/contract-api.md)、三套 UI 真机目检、空态/加载态/错误态三态走查、`--hr-status` 输出与表② 字段级对照; ls.lane_text 幻键修复已补修闭环(提交 7cff3adb, 见上), 不再遗留。
