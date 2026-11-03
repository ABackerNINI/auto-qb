# 26-11-03-memory-bank-code-review-3-s6 — 第三次评审 S6 跨批契约交叉验证 + 汇总分级

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** S6：6 对跨批契约（5 一致 / 1 不一致）+ S2–S5 全 18 条分级终表（P0 0 / P1 2 / P2 8 / P3 8）+ HEAD fbfc2825 可达性复验 + 18↔18 去重闭环（Open 75 = 底册 50 + 本轮 25）+ test.gtm 当期绿
**Topics:** memory-bank-code-review-3-s6
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s7.md

## 原始请求

1. 执行第三次 code review 计划的 **S6 步骤**（跨批契约交叉验证 + 汇总分级）；必读计划 `memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html`（S6 段与总验收判据）+ S2/S3/S4/S5 四份 task 文档 + S0 排重基线。
2. 工作方式：遇到问题一律**当场入池后继续**，不停下等指示；只做评审与验证，**零代码改动**。
3. 开工先 `commands run my-commit-flow.sync`，贴「已同步 <hash>」；只在 clone1 操作。
4. 跨批契约交叉验证至少覆盖 6 对：config `web.transfer` ↔ `schema.py`/`validate_config`；`config_rules.js` ↔ `compat.py`/`Rule` 构造；transfer API ↔ 前端调用与 `TransferStatus` 映射；gtm/capture ↔ 后端 `sync-stream` 契约；webui 路由 ↔ 前端 fetch 端点；HR/infra ↔ 作业队列状态机。
5. 汇总 S2–S5 全部发现（P0/P1/P2/P3 分级），做终表：每条含批号、类型、三锚、可达性、与 issue 池对应关系；**去重闭环**（与全部 Open issue 比对，含 S0 3 条、S1 3 条、S2 3 条、S3 5 条、S4 4 条、S5 6 条）。
6. 逐条在**当期 HEAD** 复验可达性（P0/P1 必须实证可触发；不可达的降级并写理由）；检查无断号、无重复条目、无「观察」混入发现表。
7. 复验 S4 的 `test.gtm` 失败与 S5 提到的 `test.gtm` 受影响项，给出当前 HEAD 实际状态。
8. 发现的任何新问题当场入池（含去重冲突、分级不一致、可达性证伪）。
9. 过程与终表写进本步单独 task 文档（`commands run kb.new task`）；计划只推进 S6 状态，不写流水；收尾 `kb.wrap`/`kb.index`/`kb.check` 后单独提交推送。
10. 回复：同步结果、契约结论（逐对）、分级计数、可达性复验、新增 issue、task 路径、提交 hash 与推送核验、交 S7 的输入清单。

## 思考过程与决策

- **请求边界**：本轮是「执行任务」但**零代码改动**——只做只读评审与验证；`kb.new`/`kb.wrap`/`kb.index`/`kb.check`/commit/push 由请求第 9 条显式授权。用户第 8 条显式授权「新问题当场入池」，覆盖计划 D7「P0/P1 不入池、待 S7 用户确认」的默认口径。
- **契约核对取三层证据**：①代码两侧真值对读（键名/枚举/状态映射）；②机器比对（后端 81 条 `@router` 路由 vs 前端 118 条 `/api/*` 字面量，归一化动态段后反查）；③探针/测试实证（可运行的最小复现）。
- **P 级口径**（计划 §03）：P0 数据破坏/安全红线；P1 功能错误或门禁失效；P2 健壮性/可观测性、真实可达但非破坏；P3 可维护性/文档漂移/测试缺口。既有 issue 已带 P 级的沿用其值（0824 P2、1035-bug P1、1035-test P2、1120-rules P2、1120-flux P3、1144-fs P1、1144-gtm P2、1145×2 P3）；便签档未写 P 级的 10 条按 S2–S5 task 文档口径与症状定级（0901×2 P3、1120-parity P3、1208×3 P2、1209-check P2、1209-feeder P3、1209-env2 P3）。
- **P1 复验用实证而非推理**：group 窗口化用现成语义电池（其断言 `SRC.group !== DOC` 本身即证明走容器分支）；fs_delta 用 `sanitize_all` 分支清单与回放端 `_apply_fs_delta` 取键真值。
- **既有条目修正不新开 issue**：`26-11-03-1144-fs-delta` 的「回放端静默丢增量」表述偏重——实际是按伪 hash 查 `save_path` 落空后把增量叠到**错误完整路径**（仍写入 `_disk_override`，非丢弃）。属同一 issue 的证据措辞精修，交 S7 一并处理，避免重复入池。
- **同类不并入**：`username/password/api_key` 只做 `str()` 不校验标量，与 0901-pathmap 同形但不并池——凭据接受数字/宽松转换是合法用法，而 `path_map.from/to` 参与前缀替换语义，非标量会静默失效，二者后果不可比。
- **零改码**：全程未改 `src/`、`scripts/`、`tests/`、`config.yml`；仅新建本 task 文档并回填计划 S6 状态一行。

## 实现计划

1. 开工同步并记录当期 HEAD。
2. 读计划 S6 段与总验收判据、S2–S5 四份 task 与 S0/S1 底册。
3. 六对契约逐对核对（对读 + 机器比对 + 探针）。
4. 汇总 18 条发现，按 P0–P3 定级，登记批号/类型/三锚/可达性/issue 对应。
5. P0/P1 实证复验，其余静态复验；判定是否需要降级/升级。
6. 与全部 Open issue 做去重闭环并核对条数算术。
7. 复跑 `test.gtm`，记录当前 HEAD 实际状态。
8. 落盘本 task、推进计划 S6 状态、收尾 `kb.wrap`/`kb.index`/`kb.check`，然后提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S6-1 | 同步 + 记录当期 HEAD | Done(2026-11-03) |
| S6-2 | 读计划 S6/验收判据 + S2–S5 + 底册 | Done(2026-11-03) |
| S6-3 | 六对跨批契约核对 | Done(2026-11-03) |
| S6-4 | 18 条发现分级终表 | Done(2026-11-03) |
| S6-5 | 可达性复验（P0/P1 实证） | Done(2026-11-03) |
| S6-6 | 去重闭环 + 编号完整性 | Done(2026-11-03) |
| S6-7 | `test.gtm` 复跑 | Done(2026-11-03) |
| S6-8 | 落盘 + 计划状态 + 收尾 + 提交推送 | Done(2026-11-03) |

## 进度日志

### R0 · S6 执行 (2026-11-03)

**0. 同步与基线**
- `commands run my-commit-flow.sync` → **已同步 fbfc2825**。
- 当期 HEAD = `fbfc2825253ba5593af9fd4a8438860361eaa5ae`，`refs/heads/develop` 同值（三处一致）。行号锚均取证于该 HEAD。

**1. 跨批契约矩阵（6 对）**

| # | 契约对 | 结论 | 真值锚 / 证据 |
|---|---|---|---|
| C1 | config `web.transfer` ↔ `schema.py` / `validate_config` | **一致** | 键面闭合：`KNOWN_TRANSFER_KEYS={"targets"}`、`KNOWN_TRANSFER_TARGET_KEYS` 11 键 = `TransferTargetConfig`(models.py:284) 字段集；`fields` 白名单 = `TRANSFER_FIELD_KEYS`(models.py:255，8 键，与前端 `TT_FIELDS` 逐键同名)；`path_map` 条目键 = `KNOWN_PATH_MAP_ENTRY_KEYS={from,to}`(sections.py:42)；`after_state` 取值受 `TRANSFER_AFTER_STATES` 约束(sections.py:958)；schema 侧 `groups.py` 有 `transfer` 隐藏对象项。校验缺口即 0901×2（已入池，非契约漂移）。 |
| C2 | 规则引擎 `config_rules.js` ↔ `compat.py` / `Rule` 构造 | **一致**（含 1 处已入池的检测盲区） | 归一化口径同源：`cfgRuleRetiredKeys`(config_rules.js:49)/`cfgIsRetiredAction`(:61) ↔ `retired_control_keys_in`(rules_mod.py:53) + `_warn_retired_rule`(:87)；Rule 侧 `_build_action_steps`(rules/base.py:311) 对未知动作 `registry.create_action` 抛 `ConfigError`(:323-326)。盲区：两侧都只扫顶层 `actions`，`choose.then/default` 内嵌退役伪动作漏检（= 1120-rules，P2）。 |
| C3 | transfer API ↔ 前端调用 & `TransferStatus` 映射 | **一致** | 请求体 `{target_id, hashes[], keep_source?}`：前端 `transfer_flow.js` 与 `api_transfer_run`(transfer.py:44) 同键；响应 `{results:{hash,状态,原因}, summary, target}` 由 orchestrator `to_receipt` 生成，前端按 `状态` 渲染成功/跳过/失败；`skip` 的 `reason` 字段与 UI 映射同义。 |
| C4 | gtm/capture ↔ 后端 `sync-stream` 契约 | **不一致（已入池）** | 主体一致：gtm `/subscribe` 回 `id+lease_ttl_s+heartbeat_interval_s`(server.py:354-378) ↔ `tool_client` 消费三键；notify 六键 `event_id/day/up_bytes/down_bytes/total_bytes/ts`(notifier.py:137-144) ↔ 接收端逐键校验(traffic_monitor.py:186-197)。**不一致点在 capture 侧**：`sanitize_all`(qb_capture.py:376) 的流帧分支只覆盖 torrents/torrents_removed/tags/categories(:414-427)，无 `fs_delta`；而 `probe_fs_delta`(:883) 把真 hash + 真相对路径写进 `stream[-1]["fs_delta"]`(:904)，回放端 `_apply_fs_delta`(sim_qb_model.py:163-172) 按（已伪名化的）torrents 取 `save_path` → 真实 hash 必查不到。= 1144-fs，P1。 |
| C5 | webui 路由 ↔ 前端 fetch 端点 | **一致** | 后端 81 条路由 vs 前端 118 条 `/api/*` 字面量机器比对：4 条「未匹配」全为构造式误报（`/api/groups/${key}/${action}` 的 action 变量展开为 pause/resume/reannounce/delete(groups.py:40-52)；`/api/traffic/qb/{torrent|group}/` 尾斜杠拼接(torrent_detail.py:84 / groups.py:27)），另 2 条为注释文本（triggers.js:276/280）。零真失配、零孤儿调用。 |
| C6 | HR/infra ↔ 作业队列状态机 | **一致** | 展示面与队列真值单源：`/api/hr/status` → `runtime.status()`(hr/runtime.py:515) → `ChannelStatus.pending=self.queue.pending()`(hr/server.py:350) → `HrTaskQueue.pending()`(hr/queue.py:160，先 `_expire_locked` 后计数)、`worker_running=worker.started`(runtime.py:531)；`/api/hr/refresh` 只走 `request_refresh`(runtime.py:368)，webui 层不直写队列/共享状态，无绕道写者。 |

**2. 分级终表（S2–S5 全 18 条）**

> 每条 = 批号 / 类型 / 三锚（文件:行 · 函数或符号）/ 可达性复验（HEAD fbfc2825）/ 级 / issue 池。所有条目均已入池且状态 Open，故「撞车」列为对应池条目本身（无双记）。

| # | 批号 | 类型 | 级 | 三锚 | 可达性复验（当期 HEAD） | issue 池 |
|---|---|---|---|---|---|---|
| 1 | S2-B1-1 | bug | P2 | `transfer/orchestrator.py:370` · `_transfer_one` → `_delete_source`(:443) | 可达：目标加种+校验成功后删源抛异常 → 整条结算为失败（实测路径有 `except` 仅包 adapter 段，删源段无保护） | 26-11-03-0824-…source-delete-misreport |
| 2 | S2-B1-2 | bug | P3 | `webui/server/routes/transfer.py:58` · `api_transfer_run` | 可达：直调（需 web token）传字符串 → 逐字符拆成伪 hash；前端恒传数组 | 26-11-03-0901-…hashes-input-type |
| 3 | S2-B2-1 | bug | P3 | `config/validation/sections.py:893` · `_validate_transfer_path_map` | 可达：手写 YAML 的 from/to 为 dict/列表 → `str()` 判空放行 → 前缀替换静默失效 | 26-11-03-0901-…pathmap-nonscalar |
| 4 | S3-P1-01 | bug | **P1** | `shared/columns.js:72-75` · `WIN_SOURCES.group` + `shared/columns_grid.js:461` · `_rowWindow` | **实证**：`test_frontend_window_source_kind_descriptor_parameterized` 绿（1 passed）——该测试电池第 483-484 行断言 `SRC.group !== DOC`，即 group 走容器分支；抽屉关 `_winCtnState().h=0` → `vh<=0` 全量渲染；抽屉开用抽屉坐标系切主表 | 26-11-03-1035-…group-window-source-mismatch |
| 5 | S3-B5 | test | P2 | `e2e/search-uncovered-no-duplicate.spec.mjs:32` · 具名导入 `BASE_URL` ↔ `e2e/harness.mjs:44` · 仅导出 `baseUrl` | 可达：ESM 具名导入不存在绑定 → 集合期 SyntaxError，`dev.e2e` 全量起不来（静态闭合：harness 10 个导出无 `BASE_URL`） | 26-11-03-1035-…e2e-harness-baseurl-import |
| 6 | S3-B5 | bug | P2 | `core/modules/rules_mod.py:53` · `retired_control_keys_in` + `config/validation/rules.py:404` + `rules/base.py:323` · `registry.create_action` | 可达（低门槛）：手写 YAML 在 `choose.then/default` 内嵌 `ignore_next_action_error` → 校验放行（伪动作分支先返回）→ 启动 `Rule()` 抛 `ConfigError` 硬失败 | 26-11-03-1120-…rules-choose-nested-retired-control |
| 7 | S3-B5 | bug | P3 | `flux/css/views.css:133` · 移动端 `.ce-page` ↔ `flux/css/dialogs.css:482` 同特异性后置 | 可达：移动端宽 + flux 皮肤下设置页内边距 4px 偏差（层叠顺序由 `_ui_css_aggregate` 固定） | 26-11-03-1120-…flux-ce-page-media-cascade |
| 8 | S3-B5 | test | P3 | `shared/config_rules.js:49/:61` ↔ `config/compat.py` 规范化 | 可达：改任一侧漏对拍即静默，现无自动化守卫 | 26-11-03-1120-…config-normalize-parity-gap |
| 9 | S4-B7 | bug | **P1** | `scripts/qb_capture.py:376` · `sanitize_all`（流帧分支 :414-427 无 `fs_delta`）+ `:883` · `probe_fs_delta` + `:904` | **实证**：脱敏分支清单证明 `fs_delta` 未遍历（真 hash/真文件名落盘 = 安全红线）；回放端 `sim_qb_model.py:163-172` 按伪名化 torrents 取 `save_path` → 真 hash 必落空 | 26-11-03-1144-…fs-delta-sanitize |
| 10 | S4-B7 | bug | P2 | `tools/global-traffic-monitor/src/gtm/server.py:273-279` · `handle`（401 短路） | 可达：无/错 token 的 POST 带体请求未读体即回 401 → Windows keep-alive 收连接重置；间歇型（见 §4） | 26-11-03-1144-…gtm-auth-body-drain |
| 11 | S4-B8 | bug | P3 | `scripts/sim_qb_core.py:236-240` · `minimal_bencode` | 可达：announce 长度标 26、实际 25 → 非法 bencode；仅测试替身保真度 | 26-11-03-1145-…sim-qb-export-bencode |
| 12 | S4-B8 | refactor | P3 | `scripts/qb_capture_cli.py:60` · `main`（:78 引用未定义 `Capture`；无 `__main__`） | 可达：执行/导入该 CLI 即 `NameError`；拆分后死入口 | 26-11-03-1145-…qb-capture-cli-dead-main |
| 13 | S5-B10 | docs | P2 | `docs/configuration.md`（全文无 `web.transfer`）↔ `config/models.py:313` · `TransferConfig` | 可达：按文档配转移必漏键（键面真值见 C1） | 26-11-03-1208-…configuration-transfer-missing |
| 14 | S5-B10 | docs | P2 | `docs/context7/README.md:4/:11/:12` ↔ `uv.lock` 真值 | 可达：5/10 版本不符 + 2 条模块路径已迁（`core/qbclient.py`、`webui/server/`） | 26-11-03-1208-…context7-version-path-drift |
| 15 | S5-B10 | docs | P2 | `README.md:247` · 用例规模段 | 可达：停留 2026-10-03「2300+/2312」，与现行收集数不符 | 26-11-03-1208-…readme-test-scale-drift |
| 16 | S5-B9 | test | P2 | `.agents/skills/deps-upgrade/scripts/check_updates.py`（版本切分/增量分类） | 可达：该脚本无任何 `tests/` 覆盖，改动无守阵 | 26-11-03-1209-…check-updates-uncovered |
| 17 | S5-B9 | test | P3 | `tests/test_hr_runtime_feeder.py` · wake 转发用例 | 可达：用例名声称转发，未断言转发目标 → 实现回退仍绿 | 26-11-03-1209-…feeder-wake-forward-unasserted |
| 18 | S5-B10 | docs | P3 | `tests-real/lib/env_registry.py:5` ↔ `:28` | 可达：环境2 端口/exe 已定（56589/56590）与「尚未实测留空」注释自相矛盾 | 26-11-03-1209-…tests-real-env2-comment-drift |

**分级计数**：P0 **0** · P1 **2**（#4、#9）· P2 **8**（#1、#5、#6、#10、#13、#14、#15、#16）· P3 **8**（#2、#3、#7、#8、#11、#12、#17、#18）。合计 18。

**3. 可达性复验结论**

- P0/P1（3 条要求实证，实有 2 条）：
  - #4 group 窗口化：实证（现成语义电池通过，且电池断言正是「group 非文档型」；结合 `_winCtnState` 零视口回退 → 抽屉关全量 / 抽屉开错坐标系）。**维持 P1，不降级**。
  - #9 fs_delta：实证（脱敏分支清单 + 回放端取键真值）。**维持 P1**；仅把「静默丢增量」精修为「叠到错误完整路径」（见决策段，交 S7 修 issue 措辞）。
- 其余 16 条静态复验均判定**可达**，无降级、无升级；两条「可达性门槛」说明：#6 需手写 YAML 才能构造（webui 无法创建该形态），但仍为启动期硬失败，维持 P2；#2/#3 仅直调 API/手写 YAML 可达，维持 P3。
- **无「观察」混入**：S3/S5 文档中未确认的候选（flux 全量 CSS、`shared/config_rules.js` 深读、`runner.py` CLI 门禁）留在各自 task 的「残余风险」，未进本表；本表 18 条均为带锚可复核条目。

**4. `test.gtm` 现状（复验 S4 失败项与 S5 受影响项）**

- `commands run test.gtm` → **绿**：`463 passed, 2 skipped in 64.74s`；覆盖 `TOTAL 99%`（门禁 88%）。
- 与 S4 记录（`test.gtm` 1 failed = `26-11-03-1144-bug-gtm-auth-body-drain`）不冲突：该缺陷是**间歇型**（401 短路不读请求体 → Windows 连接重置），单轮绿不构成关闭依据；代码路径仍存（gtm/server.py:273-279 未改）。= 维持 P2，S7 不因本轮绿而降级。
- S5 提到的「`test.gtm` 受影响项」在当期 HEAD 未出现红；`check_updates` 覆盖缺口（#16）仍成立（与 gtm 测试无关，属 deps-upgrade 脚本）。

**5. 去重闭环与编号完整性**

- 终表 18 条 ↔ 18 个**互不相同**的 Open issue，一对一，无两条发现落同一 issue、无发现与池外既有 issue 重复。
- 池总量核对（`_index.md` 生成物口径）：Open **75** = feat20 / bug16 / docs13 / test8 / question6 / refactor5 / perf5 / chore2。
  - 本轮新增 **25** = S0 3（0630×3）+ 评审流程 1（0647 refchain）+ S1 3（0704×3）+ S2 3 + S3 5 + S4 4 + S5 6。
  - 其中**发现类 18** = 终表；**流程/计划类 7** = S0 3 + 0647 1 + S1 3，均非代码发现，不进分级终表。
  - 其余 **50** 为历史底册（含评审起始前已存的 26-11-03 早批 4 条：0316×2 / 0315 / 0115）。75 = 50 + 25 闭合。
- 编号完整性：S2 三条为 B1-1/B1-2/B2-1（B3/B4 无发现，属结论非断号）；S3/S4/S5 各批发现数 5/4/6 与入池数一一对上；终表序号 1–18 连续无空号。
- 近邻撞车（记录但不并池）：#4 与已 Done 的 `26-11-02-0902`（首访量齐行高）同属窗口化子系统但根因不同；#16 与 #8 同属测试缺口但模块不同；#9 与 #1 同为「静默失配」但层级不同（脱敏/回执）。

**6. 新增 issue**

- **0 条**。理由：18 条发现已全部在池（1:1）；本轮未发现新的代码缺陷。两类接近「新问题」的事项按去重纪律**不重复入池**：
  1. `1144-fs-delta` 的回放端措辞精修 → 并入既有条目，交 S7 改文；
  2. 「10 条便签档 issue 未写严重度」→ 属 create-issue 的便签/标准两档设计，非缺陷；P 级已在终表补齐，供 S7 沿用。

**7. 交 S7 的输入清单**

1. **18 条终表**（本文 §2，含级/三锚/可达性/池条目），按 P1→P3 排序推进处置。
2. **P1 两条**优先：`26-11-03-1035-…group-window-source-mismatch`、`26-11-03-1144-…fs-delta-sanitize`（后者含安全红线，建议先处置）。
3. **需在 S7 修的既有条目**：`1144-fs-delta` 的回放端描述（「静默丢增量」→「按伪 hash 查 save_path 落空，增量叠到错误完整路径」），并补一条自测断言建议（fs_delta 伪名化后回放可命中）。
4. **契约结论基线**：C1/C2/C3/C5/C6 一致（可作回归判据），C4 含唯一不一致点（= #9），修完后应重跑 C4 对读。
5. **门禁基线**：`test.gtm` 当期绿 463 passed / 2 skipped / 99%；`dev.e2e` 仍受 #5 阻塞（修 #5 后才能做全量前端回归）。
6. **底册算术**：Open 75 = 50 历史 + 25 本轮（发现 18 + 流程 7）；S7 收尾写报告时以此为准，勿沿用计划 §02 的旧数字（0630 已入池）。

- 2026-11-03 12:32 S6：六对跨批契约核对（5 一致/1 不一致）+ 18 条分级终表（P0 0/P1 2/P2 8/P3 8）+ HEAD fbfc2825 可达性复验（P1 实证）+ 去重闭环 75=50+25 + test.gtm 绿；零代码改动，新增 issue 0
