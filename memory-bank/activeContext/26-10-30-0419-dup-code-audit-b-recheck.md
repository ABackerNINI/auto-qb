# dup-code-audit-b-recheck

> 摘要: B 类重复代码复核(R15 入池 22 条)中 14 条 open refactor issue 一次批次全部收口 —— 每单子会话独立实施并提交(14 commits), issue 翻 Done 留修法/提交/定向验证日志; 全量 test.full 与覆盖率见基线切片 26-10-30-0418-refactor-b-recheck-batch-baseline(commands run kb.baseline); 批次内唯一行为变更 = issue 1310 豁免线 3×req → 3×(req+extra)(用户拍板)
> 最后活动: 2026-10-30 04:19

**R0(2026-10-30 04:19):** B 类复核批次 14 条 open refactor issue 全部收口: 每单由子会话独立实施并提交(8fd15867/409f36fc/6441a707/bfd19fda/0075d3ce/79dc6b52/6dc63e5b/3c9de728/b3949cf0/541ede4b/a1ccda70/58f3d798/cf7357cb/2bd0e234), issue 状态翻 Done 并留修法/提交/定向验证日志; 全量 test.full 与覆盖率见基线切片 26-10-30-0418-refactor-b-recheck-batch-baseline

## 已完成(单会话收口, 14/14 —— 详情单点在各 issue 状态变更日志, 此处只留专题索引)

- tests 单点收口 5 单: 1403 wait_until(8fd15867) · 1406 write_endpoint_pointer(409f36fc) · 1405 relocate_env(6441a707) · 1404 make_service 落 hr_helpers(bfd19fda) · 1321 _cancel_delta_buckets(0075d3ce)
- 死代码删除 1 单: 1334 config_rules.js 八个 spec 死助手(79dc6b52, 用户拍板方案 A)
- webui 收敛 5 单: 1354 宿主/桥 v-for(6dc63e5b) · 1355 图标 sprite 化(3c9de728) · 1340 PRIO_TEXT 单点(b3949cf0) · 1343-C07 tracker 五桶表单源(541ede4b) · 1343-C06 content 目录树单点(a1ccda70)
- 规则/HR 语义 3 单: 1328 不合并只补守阵(58f3d798) · 1327 摘要部件单点(cf7357cb, 拍板全深度+透传 status) · 1310 豁免线派生属性单点(2bd0e234, 拍板 req+extra, 行为变更 9D → 10.5D)
- 专题余量核销: R15 入池 22 条(16 refactor + 6 bug)至此**全部 Done** —— 16 条 refactor 中 1304(v4-parse-skeleton)/1259(hr-absent-default) 由前序单会话收口, 本批收口其余 14 条; 6 条 bug(1320/1329/1335/1341/1348/1252)均前序各自收口(见各自基线切片)。认领链: 各 issue ↔ 基线切片 26-10-30-0418 双向 doc-refs
