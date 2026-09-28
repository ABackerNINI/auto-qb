# 1735 passed / 3 skipped —— HR 在线核实 v3 波次模型重建落地 (M1–M5)

> 摘要: 按计划 [plans/26-09-28-1932](../../plans/26-09-28-1932-plan-hr-verify-rebuild.html) 把 HR 在线
> 核实整体推翻重写 —— M1 四行判定表(`hr/resolve.py`, HrIdentity 三态: HR/RELEASED/NO_EVIDENCE,
> 行 4 本地兜底由 `record.check_hr_condition` 合成; 12 格矩阵逐格参数化) + M2 波次引擎(`hr/service.py`:
> 单波型全量对账 + A/B/C 轮流翻页 + 三停翻条件(①完成时间覆盖/②remain==0×5 到期段/③本地全集覆盖)
> + 档位级截断式数据有效性 + 失踪观察期 + 流转守恒/骤降/零行戳三道防伪 + 身份登记一次下载规则)
> + M3 单频控(`hr/ratelimit.py` 三键, 熔断/停用/退避删除, Retry-After 单存) + M4 配置 40→14 键
> (config v2→v3 与 hr_site v1→v2 迁移, 档案 `listing` 字段, `required_seeding_time` 派生) + M5
> 波次视图(`--hr-status` 各档明细/守恒/骤降/确认戳, `--hr-confirm-empty` 新增(含
> `POST /api/hr/confirm-empty`), `--hr-resume` 删除, WebUI 状态块重写)。实施中修掉两个真缺陷:
> 轮转循环「末页/停翻 break」吞掉同轮其它档位取数机会; 无版本章新配置在 v2→v3 迁移被清空 enabled。
> HR 测试按新模型重写九个文件(resolve 35 / service 29 / ratelimit 8 / config 29 / report 18 /
> store 17 / runtime 28 / worker 21 / multisite 5); keys.md 回写 + 键面基线
> `commands run test.keys-update` 重生成; doc-map 第五次收口(单件折行 400→800 + 头部压缩)。
> 基线时间: 2026-09-29 (develop @ da09e201, 已合流远端 3 提交: WEBUI 列对齐 / 设置页文案核对 / TODO)
> 档案: tasks/26-09-22-backend-partial-hr-verify.md · plans/26-09-28-1932 (doc-status Done)

- test.full: **1735 passed / 3 skipped**, TOTAL **90%**(12,422 语句 / 1,034 未覆盖 / 4,172 分支 /
  411 partial), 耗时 ~21s。较上一基线(26-09-28-2324, 1830/4)**−95 passed / −1 skipped / −1%**:
  HR 测试按 v3 模型重写(旧 v2 守阵如配额双桶/熔断/P 反算/覆盖证明整波语义随模型删除),
  配置键面收缩使 config 相关用例减少; 业务代码覆盖 TOTAL 90%(v2 基线 91%, hr 包删码 > 删测)。
- 键面: hr_check 段 31 个 v2 键消失、4 个新键(min_interval/max_requests_per_day/max_pages_per_wave/
  sites.*.enabled), 基线已重生成; keys.md 三处(hr_check 全局行 / trackers.hr_check 旧键行 /
  hr_check.sites 节)按 v3 口径回写。
- 中途红验: 迁移保留 `enabled` 键前后各验一次(误杀场景由 test_sites_entry_parsed 钉死);
  轮转 break→continue 由 test_run_hr_status_shows_incomplete_reason_and_pending(三档各得 1 页)钉死。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
