# 26-10-05-backend-hr-steady-throttle — HR 稳态降频 (idle_refresh_interval) 实施

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05 09:25
**Topics:** backend-hr-steady-throttle
**Summary:** HR 在线核实稳态降频六阶段落地: 新站点键 idle_refresh_interval(默认 24H, 默认启用, 等效关闭 = 与 refresh_interval 相等) → 引擎拉取间隔闸按「对账对象集是否为空」动态取值 + 稳态旗标仅翻转落盘 + 锚点三态(None = 采集失败不降频) → 展示单点 site_conf_interval 跟随 + kv 行「(稳态降频)」注记(拍板 D1) → 守阵 6 条 → docs 机制段回写 → 全量基线与收尾。C3 淘汰预告未实施(拍板 D2: 不同批); 真机走查待做。
**Refs:** memory-bank/plans/26-10-05-0555-plan-hr-steady-throttle.html,memory-bank/reports/26-10-03-1505-report-hr-fetch-verify-forensics.html

## 原始请求

> 用户动议: 「本地无相关种子(零交集/全达标)时, HR 拉取频率降到 1 天一次」—— 取证报告
> [26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html) §13 后记判定可行并附机制分析与风险量化;
> 2026-10-05 05:30 所有者拍板 `idle_refresh_interval` 默认 24H 且默认启用; 计划工位出
> [26-10-05-0555](../plans/26-10-05-0555-plan-hr-steady-throttle.html) 分步实施(S1–S6); 用户下达实施指令。
> 执行形态: 分支 `feat/hr-steady-throttle`, 每阶段独立 commit, S6 收尾回写。

## 思考过程与决策

- **判据单点**: 两动议场景(本地零交集 / 全部终态)统一落「对账对象集为空」—— `_build_objects`(service.py) 波前纯内存现算, 未对账 ∪ 考察中经排除链(终态/已放行/超额 ≥3×)后为空。
- **动态取值 + 即时回退**: 间隔闸 `interval = idle_refresh_interval if steady else refresh_interval`; 破稳态无需触发器 —— 对象集翻非空 ⇒ 回常态间隔 ⇒ healthy+refresh_interval 早已过去 ⇒ 下一 poll(≤60s)立即开波。发现延迟 5H→≤60s, 比现状更快, N 波防抖省去(对象集为空是本波自证覆盖的结论)。
- **现算提级**: 对象集现算从 `_do_wave` 提到 `_refresh_locked` 顶部一次、传参进波 —— 杜绝双跑现算与双回炉; 漂移回炉从波时提前到 poll 时(语义不变, 正是「新下载自动破稳态」判据所需)。
- **锚点三态契约**(报告 R5 唯一实质风险的拦截): `None` = 采集失败/未知 ⇒ **不降频**; `{}` = 确认零锚点 ⇒ 可降频。worker 失败分支改返 None, refresh_site/refresh_all 去掉 `or {}` 吞并, None 直通 —— 不把「不知道」当「零种子」。
- **稳态旗标落盘纪律**: `HrWaveMeta.idle_mode` 仅**翻转时**经 `_persist_step` 写盘 —— 稳态期反复 poll 零写盘; 旗标只供展示链(视图四处全走落盘数据), 闸门永远用本实例现算值(多实例边界 R6)。不 bump hr_site 版本(versioning「补字段不造版本」, 旧 JSON 缺键回 False)。
- **拍板 D1 采纳实施**(4d88bf7e): kv 行「下次核对清单」稳态期加「(稳态降频)」注记, 常态期不出现 —— 与已修 B2 语义配套, 防「为什么是 24H」新误读。
- **拍板 D2 采纳推荐**(不同批): C3 30 天静默淘汰预告独立零耦合, **未实施**, 距首个真实触发(10-28 后)尚有余量; 方向 A(日志预告)留档计划 §04。
- **不变项逐条保持**(S4 守阵钉死): 复用窗 `min(reuse_window, refresh_interval)` 不跟随 idle / force 跳两道调度闸 / min_interval·日额·Retry-After·时间窗照常 / 对象集为空不跳波(省波次不省单波页数)。

## 实现计划

单点: [plans/26-10-05-0555](../plans/26-10-05-0555-plan-hr-steady-throttle.html)(§02 方案设计 / §03 分步实施 / §06 风险, 锚点行号 2026-10-05 实测重标 @ee52e57d)。

- **S1** 配置键 idle_refresh_interval: models / loaders / validation(交叉校验拦 idle<refresh, 60s 下限 30d 上限) / schema 四点同步 + 键面守阵自动复核。
- **S2** 引擎闸: 间隔闸动态取值 + 旗标翻转落盘 + 锚点三态(service / worker / model)。
- **S3** 展示同步: status.py `site_conf_interval` 单点换算 + kv 行注记(D1)。
- **S4** 测试守阵: idle 闸 5 条 + 复用窗不跟随回归 1 条(tests/test_hr_service.py 三参数解耦区)。
- **S5** 文档回写: docs 机制段 + service docstring 对齐现算提级。
- **S6** 全量基线 + 计划状态回写 + docs 漂移补齐 + 立档 + kb.index + 真机 dry-run 冒烟。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| 拍板 | 核心机制(05:30 所有者) + D1/D2(实施轮) | Closed(D1 采纳实施; D2 采纳推荐不同批) |
| S1 | 配置键四点同步 + 键面守阵 | Done (10984535) |
| S2 | 引擎闸动态取值 + 旗标落盘 + 锚点三态 | Done (eeb9290e) |
| S3 | 展示单点 + kv 行注记(D1) | Done (4d88bf7e) |
| S4 | 测试守阵 6 条 | Done (a270aabb) |
| S5 | docs + docstring 回写 | Done (943ff662) |
| S6 | 全量基线 + 收尾回写 | Done (本档案) |

## 进度日志

- **2026-10-05 05:55** 计划入库(plans/26-10-05-0555, 状态 Open), 实施待指令; 切片 [计划 26-10-05-0555](../plans/26-10-05-0555-plan-hr-steady-throttle.html)。
- **2026-10-05 05:55–08:32** 实施六阶段, 每阶段独立 commit 全绿(各步 test.quick 依次 2572 / 2572 / 2575 / 2581 passed + 4 skipped; S4 结论「未发现前序阶段实现缺陷」): `10984535`(S1 配置键) → `eeb9290e`(S2 引擎闸; 既有用例计划内最小调整 12 处) → `4d88bf7e`(S3 展示 + D1 注记) → `a270aabb`(S4 守阵 6 条) → `943ff662`(S5 docs 机制段 + service docstring 对齐)。
- **2026-10-05 09:03** S6 收尾回写完成: ①全量基线已记(数字单点见 `testing/baselines/` 最新切片, `commands run kb.baseline`; 相对上基线 26-10-05-0630 的 2567+4 净增 14 用例 = S1 5 + S3 3 + S4 6, 全计划内); ②计划 meta doc-status Open → Done + §05 D1/D2「结果」列 + §07 验收判据逐条标注 + footer 变更记录追加实施完成轮; ③docs 漂移补齐两处 —— configuration.md 站点接入键清单(3 键→4 键)与配置样例补 `idle_refresh_interval`、hr-online-verify-docs.md 主线时间总表补 26-10-03-1505 报告与 26-10-05-0555 计划两行; ④本档案立档(Refs 双向: 计划 + 报告); ⑤kb.index 重建索引。
- **2026-10-05 09:02** 真机 dry-run 冒烟(`commands run dev.run -- config.yml --dry-run`, 只读): 配置加载 / schema 迁移 v3→v4(仅内存不落盘) / 全局任务创建均正常, 走到连接 qB(127.0.0.1:16585)一步因 qB 未运行失败(WinError 10061 连接被拒) —— 环境性失败, 按口径记录不重试不修复; 配置面与 HR 模块装载路径无异常。
- **2026-10-05 09:22–09:25** 所有者指派「遗留入池, C3 入池」: 4 条 issue 建档 (docs / chore / refactor 便签档 + feat 标准档, 专题 hr-steady-throttle), 遗留段③与②补 issue 链接, issues/_index.md 由生成器重建。
- **遗留**: ①**真机走查未做**(两站稳态期「下次核对清单」显示 24H / 手动加种子 ≤60s 回常态开波 / 稳态期请求量 14→6 每天核对 —— 计划 §07 标「待真机验收」); ②**C3 淘汰预告未实施**(拍板 D2 不同批, 首个真实触发 10-28 后) —— 已入池 [26-10-05-0922-feat-hr-prune-notice](../issues/26-10-05-0922-feat-hr-prune-notice.html)(方向 A 日志预告留档); ③**三个只报告未修项**(2026-10-05 09:22 所有者指派入池): (a) test_config_schema.py 头部测试计划清单漂移 → [docs-config-schema-docstring-drift](../issues/26-10-05-0922-docs-config-schema-docstring-drift.html); (b) pytest.ini 覆盖率闸使 test.one 部分运行绿测试仍 FAIL → [chore-pytest-cov-gate-test-one](../issues/26-10-05-0922-chore-pytest-cov-gate-test-one.html); (c) SiteHrCheckConfig.fetchable 零消费方(潜在缺口) → [refactor-hr-fetchable-dead-config](../issues/26-10-05-0922-refactor-hr-fetchable-dead-config.html)。
