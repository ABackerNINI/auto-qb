# 26-10-17-webui-traffic-source-fixes — 全局流量来源联动缺陷修复 (Phase 1)

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-18
**Summary:** 修掉「全局流量来源」联动上线后暴露的 9 个缺陷；新增顶层 `traffic_source.enabled` 总开关（关闭＝停取数/停订阅/停自动拉起，修订 0339-D1）；工具参数单位改下拉＋`?` 并统一为 `30S`/`10MiB` 复合串；快照解耦与设置页合并卡另立 Phase 2。Phase 1 的 S1–S3（总开关契约 / 取数闸门＋off 快照＋expr 文案＋前端灰显 / 工具侧 POST /shutdown＋auto-qb 代理）、S4–S5（「关闭工具」按钮＋确认框＋affects 依赖元数据 / 去黑框）与 S6–S7（设置页四修 / 工具参数单位下拉＋`?`＋复合串契约＋旧值迁移）已实施完成并通过全域回归；S8 待续。
**Topics:** webui-traffic-source-fixes

## 原始请求

用户逐条列出 9 个问题（原话）：

1. 拉起后有黑框，需要改为后台运行。
2. webui 需添加关闭工具按钮。
3. 数据来源选择 Traffic Monitor 文件时，下方仍显示工具状态与工具参数。
4. 工具状态页面的"已就绪"是灰色。
5. 工具状态页面标题与内容文字未对齐。
6. 工具状态页面"打开工具设置"显示 `{"error": "invalid token"}`。
7. 选择"整机流量监视器"保存后，历史流量图仍显示 Traffic Monitor 的数据，一段时间后恢复，猜测可能与 10 分钟刷新有关。
8. 选择"整机流量监视器"保存后再换回"Traffic Monitor 文件"保存后，流量历史图不显示。
9. 工具参数设置中需按惯例把文件大小/时间单位改为下拉框，同时加 `?` 解释。

相关文档：`26-10-17-0339-plan-global-traffic-source-integration.html`。要求：**先 grilling，再写分步修复计划**。

## 思考过程与决策

- **计划**：`memory-bank/plans/26-10-17-1737-plan-global-traffic-source-integration-fixes.html`（Phase 1），拍板 D1–D15；Phase 2（快照解耦＋合并卡）方向 P1–P3 亦记录在同计划 §06。
- **总开关改判（D1，修订 0339-D1）**：用户把"关闭工具"从"切回 `provider=traffic_monitor`"改判为**新增顶层 `traffic_source.enabled` 总开关** —— 关闭＝停取数/停订阅/停自动拉起，`provider` 不变。一处字段同时满足"关工具"与"关数据来源功能"，并根除"停完又被订阅线程拉回"。
- **依赖处置（D2/D5/D6）**：闸门落在取数单点 `paths.dat_path/unavailable_reason` + `tool_client._desired` + `agent.ensure_running`；曲线走**运行期闸门**（发 `off` 快照），**不写盘**改 `global_speed_limit_curve.enabled`；expr 取不到**明确报错**（不静默当 0）。
- **关闭必提醒（D3/D4）**：确认框列出受影响功能，清单来自 schema 字段依赖元数据；次序＝先保存 `enabled=false` → 再 `POST /shutdown`。
- **单位惯例（D12/D13）**：工具参数改用项目既有 `hub-field` 的 `time`/`size`（数值＋单位下拉＋`?`），格式**统一为复合串**（`30S`/`10MiB`），工具侧新增同文法解析单点、读侧兼容旧数值一次性迁移。
- **关键澄清事实**：流量快照的**唯一发布者就是「限速曲线」模块**（`_publish_traffic → ctx.web.set_traffic_view`）——这既解释了 #7/#8 的"≈10 分钟"节拍，也决定了依赖提示要"两侧互指"。
- **分期（D15）**：9 项修复与重构解耦，Phase 1 先行可独立验收；Phase 2 另立计划。

## 实现计划

分 8 步（每步独立可验，落点与验收判据见计划 §04）：

- **S1** `traffic_source.enabled` 字段契约（models / schema / schema.py / validate_config / loaders）。
- **S2** 取数闸门 + `off` 快照态 + expr 文案（paths / tool_client / agent / speed_curve_mod / expr env / 前端灰显）。
- **S3** 工具侧 `POST /shutdown` + auto-qb 代理端点。
- **S4** 「关闭工具」按钮 + 确认框 + 依赖元数据。
- **S5** 去黑框（`CREATE_NO_WINDOW` + 启动器优先 `pythonw.exe`）。
- **S6** 设置页四修（整块隐藏 / `on→ok` / 行对齐 / 删「打开工具设置」）。
- **S7** 工具参数改 `hub-field` + 工具侧 units 解析 + 统一复合串 + 迁移。
- **S8** 切源即刷新（#7/#8）+ #8 真机复现取证。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | `traffic_source.enabled` 字段契约 | Done |
| S2 | 取数闸门 + `off` 快照态 + expr 文案 | Done |
| S3 | 工具侧 `POST /shutdown` + auto-qb 代理 | Done |
| S4 | 「关闭工具」按钮 + 确认框 + 依赖元数据 | Done |
| S5 | 去黑框 | Done |
| S6 | 设置页四修 | Done |
| S7 | 工具参数 `hub-field` + 工具侧 units + 统一格式 | Done |
| S8 | 切源即刷新（#7/#8）+ #8 真机复现 | Open |

## 进度日志

### R0 · 立档 (2026-10-17)

grilling 六轮收敛（用户逐条订正，含两次纠正字段落点），落盘 Phase 1 修复计划；据此在 0339 计划就地记 R3 变更行（D1 修订 + §05 盘上格式改复合串）；立本档（命中阈值 4：已产出计划文档）。本轮仅产出文档、未改代码。

- 2026-10-17 17:42 grilling 六轮收敛并落盘 Phase 1 修复计划；新增顶层 traffic_source.enabled 总开关(修订 0339-D1)；0339 记 R3

### R1 · S1 实施完成 (2026-10-17)

顶层 `traffic_source.enabled` 总开关四层契约(models/schema/validation/loaders)贯通；**恒等判据** `is not False`——只有显式 false 算关闭，MagicMock 属性不触发(pitfalls `hot-reload-mock-sections` 同族，全程规避未踩到)；键面守阵 loader 探针 + 基线重生成(v5 168→169 键) + `keys.md` 回写(总开关行 + dat_path 行补「来源启用时」限定)。计划未明说的**两处必需放宽**：①关源免检 `traffic_monitor.dat_path` 必填——关来源本就是「没配好数据源」时的出路，否则保存必败且 UI 里找不到能改的地方；②`_expr_gate` 不因关源禁用流量名字——同理否则保存必败。专用守阵 `test_validate_traffic_source_enabled_key`(缺省/false/true/非法/免检/非 false 不当成关闭/流量规则不被门控禁 + 对照组)。

### R2 · S2 实施完成 (2026-10-17)

取数闸门落在唯一入口 `paths.dat_path`(关源返回 `""`)，`unavailable_reason` 与 dat_path 同源分支(verdict-scope-parity，关源文案优先于 provider 分支)；`tool_client._desired()` 首行闸(停订阅) + `_pass` 传 enabled 到 `agent.ensure_running` 作纵深防御(拉起闸，`status()` 不设闸——停的瞬间 UI 仍要能看到状态)；曲线模块**运行期闸门**：handle 与 refresh 双路发 `off` 快照(判定优先于 `disabled`，**不写盘**改 `global_speed_limit_curve.enabled`)；expr `_traffic` 关源明确报错(不静默当 0)；notify 端点 disabled 条件扩到来源关闭；前端总开关 hub-field 行 + D14 灰显(`.hb-grey` opacity，不隐藏) + `trafficOn()` 排除 off + 历史弹层 off 态专属文案。settings.html 因新增内容触 400 行单分片上限，注释块 6→3 行 + 提示 span 并入按钮行压回(`test_frontend_template_split_wiring` 复跑通过)。

### R3 · S3 实施完成 (2026-10-17)

gtm 控制面 `ControlServer.__init__` 收 `stop_event`；新增 token 保护 `POST /shutdown`——**先回 200 再置位**(wfile 直写 socket 无缓冲，响应先上 wire)，未绑定 stop_event 时回 200 + WARNING(不炸旧构造)；`cmd_run` 把 `stop_event` 交给 ControlServer(原 L190 迟定义上移)，退出仍走既有 finally(最终落盘/释放锁/停控制面/删指针)，`_run_loop` 即时醒保证「有限时间内优雅退出」；auto-qb `routes/traffic_monitor.py` 增 `POST /api/traffic/monitor/shutdown` 代理(200 透传 / 不可达或非 200 → 502 附 state)，路由金清单同步补条目。验收对照：401 守阵(工具侧 `test_auth_required_on_all_write_endpoints` 含 /shutdown + auto-qb `test_shutdown_requires_auth`) ✓；带 token 200 + 置位 + 即时醒(`test_shutdown_returns_200_then_sets_stop_event` / `test_shutdown_wakes_run_loop`) ✓；代理码透传(`test_shutdown_forward_and_return` / `test_shutdown_unreachable_502`) ✓。**范围边界**：S3 仅后端——「关闭工具」按钮 + 确认框 + affects 元数据属 S4，本轮按用户指令不做。

- 2026-10-17 21:17 S1-S3 实施完成: traffic_source.enabled 总开关四层契约 + 取数闸门/off 快照/expr 文案/前端灰显 + gtm POST /shutdown 与 auto-qb 代理; 全域回归全绿(数字见基线切片 26-10-17-2114); S4-S8 按用户指令不在本轮范围

### R4 · S4 + S5 实施完成 (2026-10-18)

**S4「关闭工具」**：三件套落 `state.js`(`tm.shutting/shutdownMsg/shutdownErr`)、`config_hub.js`(`tmAffectLabels()` 从 `tmSourceRoot()` 取 `enabled` 字段的 `affects` → `TM_AFFECT_LABELS` 补人话, 漏 id 原样退回; `tmShutdownTool()`：确认框 → `cfgSave(enabled=false)` → `POST /api/traffic/monitor/shutdown` → `tmPollShutdown` 有界收敛)、`settings.html`(按钮可见三条件：`tmProvider()==='global_traffic_monitor' && !tmSourceOff() && tm.reachable`, 反馈 span 并入按钮行)。**次序是硬约束**：先落盘 enabled=false 并热重载, 再停进程 —— 反序会被订阅线程在停的瞬间抢拉。两处反悔护栏：保存失败把内存开关回滚成 true(否则下次普通保存把「关闭」静默写进盘); 停工具失败明说「来源已关闭并保存」+ 原因(不谎报成功)。`tmPollShutdown` 与 `tmPollSettle` 共用 `pollGen` 代际, 两条轮询链不叠加。`settings.html` 触 400 行单分片上限 → 注释块 6→2 行压回。**漏网一处**：`tmShutdownTool` 的 POST 没登记 `triggers.js`, 全量回归被守阵 T1 抓到 → 补 `calls` 行(`scope: none` + why)。

**S5 去黑框**：`agent.launch_tool` 的 `DETACHED_PROCESS` → `CREATE_NO_WINDOW`(前者让 console 子进程自建**可见**控制台, 正是黑框根因; 后者给无窗口控制台且不共享 auto-qb 控制台, 关 auto-qb 仍不带走工具; 两者互斥不能叠加), docstring/注释写明「别换回去」的理由; `launch.cmd` 改为 `pythonw.exe` → `python.exe` → `uv` 三级回退(pythonw 属 GUI 子系统, 覆盖「双击启动器 / 开机自启」这两条不经 auto-qb 的路径; 本机 venv 实测两件都在)。代价如实记：pythonw 的 `sys.stderr` 是 `None`, 输出全丢 —— 与被拉起时本就 `DEVNULL` 的行为一致, 不算回归; 启动器注释里给了「排障时临时换回 python.exe」的路子。

**守阵**：`test_frontend_shutdown_tool_wiring`(按钮三条件 + 方法在册 + 保存先于停工具的相对次序 + 回滚 + 不谎报 + 清单覆盖 schema `affects` 全部 id)、`test_launcher_prefers_pythonw`(三级回退次序 + 两类回退跑同一条命令)。文档回写 `docs/configuration.md`：YAML 样例补 `enabled`、「启用」与「关闭工具」两件事的分野、确认框清单来源。

**计划外发现(不改码, 已入池)**：`tests/test_memory_bank.py` 两例把 `2026-10-17` 写死进断言(跨零点必红, 与业务无关) → `issues/26-10-18-0608-test-memory-bank-test-hardcoded-today.html`。另记一条**未入池的范围外观察**：gtm 自启注册用的是 `sys.executable`(`python.exe`, console 子系统), 开机登录时理论上仍会闪一次窗; 本次 S5 的范围只到「立即拉起 + 启动器」, 未动 installer —— 若用户要求, 可另立条目把自启也切 `pythonw`。

### R5 · 计划外收尾: 修时间炸弹用例 (2026-10-18)

用户指派「修失败用例」→ 认领并修掉 R4 记的那两例：`tests/test_memory_bank.py` 新增 `_kb_clock()`，三处硬编码日期断言（`**Updated:**` ×2、`最后活动` ×1）改为与实现同源取时（`timekit.now()`）。**只动测试，零实现改动**；issue `26-10-18-0608` 置 Done 并回填修法/验证。夹具里的 `**Added:**`/`最后活动:` 是受测输入，保持字面量。全域回归至此转全绿（数字见 `commands run kb.baseline` 最新切片）。

### R6 · S6 + S7 实施完成 (2026-10-18)

**S6 设置页四修**：① **#3 整块隐藏**——工具状态 / 工具参数（高级）/ 工具文件选择器三块都以 `tmProvider() === 'global_traffic_monitor'` 为渲染闸（D8）；守卫按「块头标题 → 定位其 `v-if`」取值，不做关键字全文匹配。② **#4 状态色**——`tmStateClass()` 的 `ready` 由 `"on"`（CSS 里根本没有 `.hb-led.on`，落到基态灰条）改 `"ok"`；守卫另外扫「映射值必须有对应 CSS 规则」，防下一个新态再掉灰。③ **#5 行对齐**——只读状态行挂专用类 `.hb-row.hb-ro`（`align-items: baseline` + `.hb-lb { padding-top: 0 }`），**不动**全局 `.hb-row`（控件行仍靠那 7px 与输入框顶端对齐）；e2e 几何守卫实测首行顶端差与级联结果。④ **#6 删按钮**——「打开工具设置」与 `tmOpenToolSettings()` 一并清除（工具控制面纯 JSON + 全路径 Bearer，点开必看 401）。

**S7 工具参数单位化**：工具侧新增 `gtm/units.py`（`parse_duration/parse_size/format_*`；文法逐字镜像 auto-qb `parse_time`/`parse_fsize` + `TIME_UNITS`/`SIZE_UNITS`，大小只认二进制阶梯）；`gtm/config.py` 的校验/回显/落盘全部改走它 —— 盘上与 `GET /status` 的 `config` 回显**只留复合串**，`Config` 内存里仍是秒/字节（采样循环不认识单位）。读侧兼容 D13 之前的裸数值（按秒/字节平移），并新增 `migrate_legacy_config`：启动时若盘上确有旧值就原子重写一次（无旧值一个字节都不碰，坏配置留给 fail-fast 报错，不"修好"成默认值）。前端 `tmParams()` 升级为元数据表（kind/unitDefault/help/def），时间与大小渲染成「数值框 + 单位下拉 + `?`」（复用设置页 `UNIT_OPTIONS` / `cfgUnitParts` / `hubAsk` 同一套），`tmBuildPayload` **不再 Number() 化**时间/大小（数值化会把单位吞掉）—— 单位没动过的键原样回传，旧版工具回显的裸值也能无损往返。

**守阵**：gtm 侧新增 `test_units.py`（全单位 parse/format 互逆 + 非法串 + bool 陷阱 + 整字节）与 `test_config.py` 的复合串/迁移/聚合用例（工具侧全量转绿, 数字见基线切片）。auto-qb 侧新增 6 条静态守阵（三块隐藏闸 / 状态色与 CSS 规则 / `.hb-ro` 与全局口径不变 / 删按钮无死引用 / 参数单位控件 + 载荷不 Number 化 / 单位表三处同源）、2 条 e2e（来源=文件时工具块确实不在 + 切到工具后回来；单位控件拆分 + `?` 浮窗 + 保存回传复合串）与 1 条只读行几何守卫（真浏览器量首行顶端差 + 级联结果）——三条新 e2e 都做过**变异验证**：去掉修复即红。

**额度**：`settings.html` 触 400 行单分片上限 → 额度提到 440 并在守阵里写明理由（该卡是二级页 `v-else-if` 链的一环，抽分片会断链；下次再长应先重构成独立组件）。

**回归**：`commands run test.full` 全绿（含覆盖率闸门）；gtm 工具侧全量亦全绿。数字只写基线切片 `26-10-18-0706-global-traffic-source-fixes-s6-s7`，此处不手抄。
