# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1639 collected: 1638 passed + 1 skipped / Windows** —— 2026-09-26 **webui 种子级标签/分类编辑**
(档案 `26-09-26-webui-torrent-meta-edit`)。
**+3 条**(test_web.py): `test_api_t_bulk_tags_category_enqueue` bulk 标签/分类动作入队(tags 过滤空段非空才透传 /
category 按键存在性透传, 空串=清除分类要保留 / 未提供时载荷不带键历史形态不变) /
`test_drain_web_commands_bulk_torrents_tags_category` 标签/分类命令执行(单次调用带全部在册 hash /
缺 tags 或缺 category 键 error 回执 / 空串分类合法) /
`test_frontend_meta_dialog_paired` 标签/分类对话框守阵(双 UI 成对: metaOpen 对话框 + 浮条/批量菜单/单种子菜单三处入口;
shared 接线 openMetaDialog 锁定目标 + metaToggleTag 走 bulk 链路; .meta-dialog/.opt-pill 两套 CSS 成对)。
落地面: `/api/torrents/bulk` 动作表扩 add_tags/remove_tags/set_category(载荷加 tags/category 键) +
前端即时编辑对话框(shared/dialogs.js, .opt-pill 切换胶囊, atlas 首次引入该组件)。
TOTAL **92%**(11008 语句 / 787 未覆盖 / 3654 分支 / 330 partial)。

**上一态: 1636 collected: 1635 passed + 1 skipped / Windows** —— 2026-09-26 **webui 一键导入缺失站点**
(档案 `26-09-26-webui-sites-import`; 数字为**再合流远端 9 笔[HR 未达标红档/扩展选项页终态/webui 修复/docker 验收]后的合并树重测**)。
**+7 条**: test_web.py +6(后端 5:
`test_sites_missing_scans_and_builds_defaults` 缺失域名生成默认条目且已配置域名不重复 /
`test_sites_missing_name_conflict_suffix` 站点名冲突 `_N` 后缀 / `test_sites_missing_all_covered_returns_empty`
全覆盖空返回 / `test_sites_missing_requires_connected_client` 断连 503 / `test_sites_missing_api_failure_maps_502`
扫描失败 502 带原因; 前端接线 1: `test_frontend_sites_import_wiring`); test_exporter.py +1
(`test_gen_tracker_name` 新提取的站点名生成单测); 金清单 `_GOLDEN_ROUTES` +1
(`GET /api/sites/missing`, 合并树 62 条)。落地面: `core/exporter.py` 提取 `gen_tracker_name`
(export_yaml_template 改调, 行为不变) + 新路由模块 `webui/server/routes/sites.py` + 前端
`config_hub.js::hubImportSites()` 与两套 UI「⤓ 导入缺失站点」按钮。
TOTAL **92%**(10993 语句 / 787 未覆盖 / 3642 分支 / 328 partial)。

**上一态: 1629 collected: 1628 passed + 1 skipped / Windows** —— 2026-09-26 **两线合流: HR 未达标红档语义修正轮 × 扩展选项页终态**
(档案 `26-09-25-webui-hr-safety-display` 修正1–3 + `26-09-22-backend-partial-hr-verify` v3.3; 两轮并行开发, 本条为**合流树重测**)。

- **HR 红档轮 +0 条, 改 4 处断言/守阵**: test_hr_resolve C 档断言改 `SAFETY_FAILED`(「考核未通过」终态独立红档);
  test_web 接线守阵安全档位键集扩四档(danger/failed/safe/unknown)、CSS 成对清单加 `.m-pair.hr-fail`、
  考察中短语断言去「义务未了」。⚠ 合流时修入树缺陷: 远端 `hr/server.py` 的 `sites_fn` 注解用了 `List`
  但 typing 导入行没有 → 全库 import 级 NameError(89 errors), 合并解决里补 `List` 修复。
- **扩展选项页轮 +1 条**: `test_extension_proxy.py::test_background_events_ring_dual_write`(后台/日志同源
  双写事件环契约) + 三档接线守阵改写 `test_options_swiss_wiring`; 落地面 background.js 事件环 +
  选项页按样张 A 重写, 新增制品 [plans/26-09-26-0031-plan-hr-ext-options-style.html](../plans/26-09-26-0031-plan-hr-ext-options-style.html)。
- **mockup 轮踩坑**: 新建 plans/ 制品缺五元 meta + 父计划未反链 → 文档守阵红(补齐即绿; 认领链同因)。

TOTAL **92%**(11064 语句 / 787 未覆盖 / 3640 分支 / 329 partial); dev.fmt 已跑。

**上一态: 1629 collected: 1628 passed + 1 skipped / Windows** —— 2026-09-26 **HR 扩展选项页终态实施: 风格 A 瑞士网格 + 两表 + 日志收起**
(档案 `26-09-22-backend-partial-hr-verify` v3.3; 数字为**合流远端 `700a11b` 五笔[webui 修复/docker 验收]后重测**)。
本轮 **+1 条**: `test_extension_proxy.py::test_background_events_ring_dual_write` —— 真跑 background.js 六类场景
(页面成功×2 / HTTP 失败 / .torrent 成功 / 登录页 / 配额让位), 钉死后台与日志**同源双写**的结构化事件环契约
(tag 分类 ok/quota/login/error + host/kind/ms/bytes); 另把三档接线守阵改写为 `test_options_swiss_wiring`
(单一风格定案 + 三档共存机制不得回潮)。落地面: `background.js` 事件环(EVENT_CAP=50, 防抖整份写回,
五个事件点) + 选项页按样张 A 重写(①连接 ②站点权限 ③站点现状表 ④取数明细表 + 折叠区[日志/硬上限/高级 JSON]);
表内阈值从 `SITE_CAPS` 取不写死。**新增制品** [plans/26-09-26-0031-plan-hr-ext-options-style.html](../plans/26-09-26-0031-plan-hr-ext-options-style.html)
(三套风格选型, 用户选定 A)。

**上一态: 1621 collected: 1620 passed + 1 skipped / Windows** —— 2026-09-26 **合流轮: 设置页 `[object Object]` 修复 + WEB UI 地址改展示 localhost**
(远端 docker 部署 / full-checking 首样本竞态两批先合入, 再以 `git rebase` 施回本轮两笔; 基线为**合流后重测**数字)。**+2 条**:
hub 字段覆盖守阵(`tpl-hub-field` 逐个覆盖 `cfgFlatten` 全部非叶子项类型) + `display_host` 三条口径
(回环折 `localhost` / 含 `0.0.0.0` 原样返回 / 非字符串不炸)。合流冲突 3 处(baseline / pitfalls/docs/_index / lifecycle 手工合并)。

**上一态: 1619 collected: 1618 passed + 1 skipped / Windows** —— 2026-09-26 **Docker 真机验收修复轮**
(档案 `26-09-25-deps-docker-deploy`)。**+2 条, 改 2 条**: 首连失败退出码契约(test_cli/test_qbmanager/test_ui)
+ 「WEB UI 已启动 / 配置热重载完成」按 INFO 记的日志断言(⚠ 抓日志挂目标 logger, caplog 挂 root 会被
setup_logging 清空)。

> **2026-09-25 及更早的逐轮状态**(示例配置守阵 / HR 扩展配置简化 / full-checking 首样本竞态 /
> 展开态跨视图记忆 / HR 删除安全档位落地 / HR v3.0 档位即结论 / 两线合一 + DND 拖拽·右键次级菜单·
> UI 位置持久化)已迁出 → [baseline-history.md](baseline-history.md)。

⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-26 一键导入合流树)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **18.3 / 56.0s**(2 次采样, 全部 test.full; 56.0s 为同机其它 clone 并行工作时的负载离群, 18.3 为常态)

**上一态(2026-09-26 HR v3.3 扩展终态)**: 并行 17.1 / 18.1s(2 次采样, 全部 test.full)。

**上一态(2026-09-25 HR v3.0 达标来源优先级)**: 并行 18.6 / 18.1s(2 次采样, 全部 test.full)。

**更早(2026-09-25 两线合一)**: 并行 20.5 / 18.8s(2 次采样, 全部 test.full, 合并态)。

**更早(2026-09-25 HR 超龄豁免)**: 并行 19.9 / 36.8s(2 次采样; 后者为同机其它 clone 并行工作时的负载离群, 前者为常态)。

**更早(2026-09-25 搜索分隔符归一)**: 并行 17.0 / 17.9s(热采 2 次; 另有首跑冷缓存 37.6s 不计入, 全部 test.full)。

**更早(2026-09-25 GBK 回退修复)**: 并行 14.3 / 20.9 / 21.2s(3 次采样, 全部 test.full)。

**更早(2026-09-25 扩展运行日志)**: 并行 17.6 / 19.8 / 19.9 / 20.5s(test.quick ×1 + test.full ×3)。

**更早(2026-09-25 禁令解除回写 → 2026-09-24 告警分档各轮)**: 并行 14.3–21.7s 区间多次采样; 扩展守阵真跑 node 比 M1 末态高约 5s(预期环境成本); M2 关停白等扩展回传的 10s 级浪费为**真缺陷**已修(「先叫停队列再 join」+ 守阵 `test_stop_is_prompt_while_waiting_for_extension`)。逐次采样数字见 [baseline-history.md](baseline-history.md)「耗时采样归档」条。

> **本文件是这组数字的唯一枚举处** —— 其它文档只写量级与"见 baseline.md", 别再抄一遍(抄一份多一处漂移)。
> 上面的列表是**采样快照**, 不必随每次跑更新; 要更新的只是"范围 / 中位"这层结论。

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
- **覆盖率口径**: **当前**并行 `10853 语句 / 789 未覆盖 / 3598 分支 / 326 partial`, TOTAL **91%**(HR 包 93%)。
  下面这组"并行 vs 串行"的对照取自 2026-09-23 采样(结论不变, 数字不再逐轮重采):
  并行 `7729 语句 / 623 未覆盖 / **219** 分支` vs 串行 `623 / **218**`, TOTAL 都是 **91%**
  ⇒ 换默认并行后**分支 partial 多 1**(语句数一致)。
- **成因(单点: [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md))**: 本机每次文件操作
  曾收一笔**固定开销**(初始 写 20ms / 删 43ms, 三盘一致、与数据量无关; 一次全量建 577 个临时目录 ⇒ 约 26s)。
  **已由系统层排除项治好** —— 现 `mkdir` 0.13ms / 写 0.21ms / `remove` 0.16ms / `rmdir` 0.14ms(全部 <1ms)。
  ⇒ 这 3.8× 来自**环境**, 不是代码优化。
- **并行**: 已是**默认**(`pytest.ini` 的 `addopts = -n 4`, dev 依赖 `pytest-xdist==3.8.0`);
  单文件排查用 `-n 0`。台账回传与覆盖率差异见
  [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。

⚠ throttle 守阵(`test_run_loop_throttles_without_stop_event`)文件级/全量跑偶发假红(Windows sleep(50ms) 精度 46ms < 0.05 下限, 容差无余量), 单跑恒绿 —— 已入池 [issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html](../issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html), 稳态数字取自 deselect 该用例的全量。

> ⚠ **只测一侧就更新会立刻产生漂移** —— 改了基线就把 Windows 与 Linux 两侧**都重测**再落数字。
> 两侧**收集数相同**但 passed 可能不同(Windows 专属用例在 Linux 上 skip), 比较时别拿 passed 直接比。

## 变更流水

逐次增量的完整流水(最近在上)已外迁 → [baseline-history.md](baseline-history.md)。
