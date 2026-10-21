# 26-10-11-webui-dup-code-fixes — webui 重复代码修复轮(报告 26-10-11-0033 §18/§19)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-21
**Topics:** dup-code-audit
**Summary:** 用户「修复 webui 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」; 追问拍板**新建本修复轮档案作认领方 + 先做低风险 7 条**。报告 §18(R15 路由层)/§19(R16 表现层)共入池 webui 10 条 refactor issue —— 本轮认领并修完 7 条(virtual-tracker-prefix / status-payload / sidecar-dir / hr-route-guard / cmd-pair-handlers / bulk-receipt / seed-view-restate), 3 条按拍板留 `Open`(partial-publish-merge 热路径抽 `_merge_rows` / cross-layer-constant 跨层常量 / route-cmd-boilerplate 表驱动)。全程**行为逐字不变**: 日志文案、HTTP 状态码与文案、响应字段集一字未改, 只收骨架; 5 条新守阵(静态 ast/源码 + 动态等值)全部过红验。test.full 实测见基线切片 `26-10-11-1610`(+5 = 新增守阵, 无回归信号)。 **2026-10-15 续轮(R2)**: 用户「认领并修复 memory-bank/issues/26-10-11-0310-refactor-webui-cross-layer-constant-convention-dup.html」—— 当期三条延后项之一的跨层常量批次落地, 走 issue 建议第一支「保持守阵 + 补全机械比对」(未触前端构建面): 四组常量对中 ② REANNOUNCE 已有逐项守阵不动; ① 补 STATE_RANK_LAST↔_SHOW_STATE_RANK_LAST 比对(views.py 表外兜底秩 9 提为命名常量); ③ 新增 ETA 哨兵全静态树扫描(`_ETA_SENTINEL` ↔ format.js + 3 处 tpl 比较点, 零命中即红); ④ 新增键位正则跨层逐字比对(`_KEYS_SERIAL_RE` ↔ `KB_DEF_RE`)并消 test_web_shortcuts.py 第三份手抄(改导入后端单点)。三条新守阵全部过红验(值漂移/声明缺失/零命中三类突变)+ 3 个活性探针; test.full 实测见基线切片 `26-10-15-0450`(仍零行为变化, 纯守阵增量 + 常量命名化 + 注释)。 **2026-10-15 续轮(R3)**: 用户「认领并修复 memory-bank/issues/26-10-11-0309-refactor-webui-partial-publish-merge-dup.html」—— 当期三条延后项之二的热路径批次落地: `_publish_partial_locked` 四段(groups/singles/flat/shows)「重建脏行/保留未脏/追加」合并骨架抽 `_merge_rows` 静态单点(键名传字符串而非 key_of 可调用, 核心热路径逐行不多付函数调用), 引用稳定契约逐字不变; 既有 S5 镜子 + S6「局部重算 == 全量重跑」双保险全绿 + 新增 2 守阵(合并契约直测 + 静态零重复骨架, 均过红验); test.full 实测见基线切片 `26-10-15-0454`。 **2026-10-15 续轮(R4)**: 用户「认领并修复 memory-bank/issues/26-10-11-0309-refactor-webui-route-cmd-boilerplate-dup.html」—— 最后一条延后项落地, 走 issue 建议的「至少对成对抽 helper」支(表驱动注册器评估后不改道, 见档案思考段): 跳检 403 门控两处逐字同抽 `_require_skip_check(ctx)` 单点; 「路由→命令」透传 mechanics 收敛为 8 个形状 helper(torrent_cmds 四: hash/enable/单字符串字段/字符串列表字段; groups 一: 组 key; torrent_detail 三: 分类/标签/限速值), 21 个端点缩为「路径→命令」一行声明(差异项——命令名/字段名/空组 400 文案——作参数传入, 沿用 R1 口径); 行为逐字不变(既有表驱动用例逐端点钉 cmd/payload + 金清单守阵); 新增静态守阵 `test_route_cmd_passthrough_single_point`(AST: helper 各定义一次 + 端点体只剩 helper 调用 + 三种逐字形状零复发; 四类突变红验: 写回载荷构造/删 helper/抄双份 helper/新增端点照抄); build_router 头样板复评「已趋薄(只剩别名+构造+return), 无逻辑重复可再安全收敛」记于 issue 实际修法。test.full 实测见基线切片 `26-10-15-0532`。10 条 refactor 现状 **10 Done / 0 Open**。
**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md,memory-bank/testing/baselines/26-10-11-1610-webui-dup-code-fixes.md,memory-bank/activeContext/26-10-11-0314-dup-code-audit.md,memory-bank/issues/26-10-11-0310-refactor-webui-virtual-tracker-prefix-dup.html,memory-bank/issues/26-10-11-0309-refactor-webui-status-payload-dup.html,memory-bank/issues/26-10-11-0309-refactor-webui-sidecar-dir-convention-dup.html,memory-bank/issues/26-10-11-0309-refactor-webui-hr-route-guard-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-cmd-pair-handlers-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-bulk-receipt-boilerplate-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-seed-view-restate-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-cross-layer-constant-convention-dup.html,memory-bank/testing/baselines/26-10-15-0450-webui-cross-layer-constant-guard.md,memory-bank/activeContext/26-10-15-0450-webui-cross-layer-constant-guard.md,memory-bank/issues/26-10-11-0309-refactor-webui-partial-publish-merge-dup.html,memory-bank/testing/baselines/26-10-15-0454-webui-partial-publish-merge-dup.md,memory-bank/issues/26-10-11-0309-refactor-webui-route-cmd-boilerplate-dup.html,memory-bank/testing/baselines/26-10-15-0532-webui-route-cmd-boilerplate-dup.md

## 原始请求

> 用户(2026-10-11): 「修复webui部分问题:26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」

> 追问下的两处选择(AskUserQuestion): 认领载体 = **新建修复轮任务档案**(与审查档案 `26-10-10-backend-dup-code-audit` 互引, 同 26-10-07 详情面板修复轮的做法); 修复范围 = **先做低风险 7 条**(热路径 merge / 跨层常量 / 路由表驱动三条只登记不动)。

## 思考过程与决策

- **请求边界**: 用户点名「修复 + 认领」= 执行任务(认领已显式授权, 不属越界); 报告本体是「出厂即冻结」的证据快照, **不随修复回写**(同 26-10-07 详情面板修复轮口径) —— 修复记录落本档案 + 各 issue 的「实际修法」段; **与报告不建正式认领链**(报告 `doc-refs` 只指专题前史档案), 正文以链接引用(故本件 `Refs` 不含报告)。
- **风险分层(拍板「低风险 7 条」的落法)**: 三条延后各有硬理由 —— ①`partial-publish-merge` 是核心热路径(前端按行对象身份做 WeakMap 记忆化, 引用稳定性是契约), 抽 `_merge_rows` 必须配「局部重算 == 全量重跑」镜子守阵, 属独立批次; ②`cross-layer-constant`(STATE_RANK / REANNOUNCE_BLOCKED / ETA 哨兵 / 键位正则)触及前端构建面, 现状已由静态守阵钉住, 收益中/风险中; ③`route-cmd-boilerplate` 的表驱动改造须保金清单守阵 `test_web_route_manifest_frozen`, 是声明式改造而非收骨架。三条保持 `Open`, 等各自批次。
- **「行为逐字不变」是本轮的硬约束**: 这批 issue 全是 C/A 类「同一事实多表示」, 抽单点的收益是消除漂移点, **不是**顺手改文案/口径。落地时逐条核对: 分类 create/edit 的日志尾部文案形状不同(`(保存路径 X)` vs ` -> 保存路径 X`), 于是把**尾部**当参数传入而不是统一格式; 批量 recheck 说「提交」、跳检说「成功」, 于是 ok/fail 两行日志文案由调用方给, 只收「有文案回 error 否则 ok」的形状; hr refresh 端点「线程未启动 409 先于未启用 400」的顺序也原样保留。
- **守阵策略**: 静态(ast/源码串)+ 动态(等值/行为)双半 —— 单靠动态抓不到「又抄了一份」(值本来相等), 单靠静态抓不到「改单点却没生效」; 五条守阵均做了红验(写回重述键 / 摘字段 / 自写 dirname / 写回字面量 / 复制派生式)。
- **R4 表驱动 vs 抽 helper 的裁决(2026-10-15)**: issue 建议的「声明成表 + 单一注册器」评估后不走 —— 收敛后端点只剩声明行, 残留重复是 builder 契约本身(别名 / `APIRouter()` / `return`)而无逻辑重复; 动态注册还会丢 handler 名(路由表可读性)并跨 3 文件改注册机制, 与 R1 commands 层「参数化单点」先例和「显式端点」文化不合。落「至少对成对抽 helper」支, 差异项(命令名 / 字段名 / 空组文案)作参数传入。
- **静态守阵撞车的一条**: `test_web_shortcuts.py` 原钉 `assert "manager.state_file" in keys_py`(意图 = 「存储路径必须与 web.token 同寻址」), keys.py 改走 `state_dir` 单点后字面量消失 —— 断言改写为 `assert "state_dir(manager)" in keys_py`, 意图不变。
- **行尾事故(本轮踩到)**: 用 `python open(...,'w')` 写源码会把 LF 翻成 CRLF(仓库 `.gitattributes` 是 `* text=auto eol=lf`) —— 9 个文件被翻, 已一次性归一回 LF 并经 `git ls-files --eol` 复核(以后写码一律带 `newline='\n'`)。

## 实现计划

按「低风险优先」串行 7 步, 每步改完跑 `test.one` 定向用例, 收口 `test.full`。改动面: `webui/commands.py` / `webui/views.py` / `webui/runtime.py` / `webui/server/common.py` / `webui/server/lifecycle.py` / `webui/server/routes/{state,hr,keys}.py` + 4 个测试文件的守阵与计划清单。

## 后续批次: partial-publish-merge 热路径(2026-10-15 认领修)

用户显式指派「认领并修复 `26-10-11-0309-refactor-webui-partial-publish-merge-dup.html`」—— 上轮留 Open 的三条中第一条到手(余 2 条仍 Open, 见「未做项」)。单步执行, 无新子任务拆分: `runtime._publish_partial_locked` 四段(groups/singles/flat/shows)「重建脏行/保留未脏/追加」合并骨架抽 `_merge_rows(old_view, key_field, rebuilt, removed)` 静态单点。**行为逐字不变**口径不变: 合并顺序/pop 语义/尾部追加与四段各自内联时逐字一致, 引用稳定契约(未脏行同一 dict 原样保留)不动 —— 前端 S7 WeakMap 记忆化不受影响。热路径取舍: 键名传字符串而非 key_of 可调用, 逐行不多付一次函数调用(issue 建议的 `key_of` 形态的保性能变体)。守阵双保险: 既有 S5 镜子 + S6「局部重算 == 全量重跑」单测全绿; 新增两条(合并契约直测 + 静态零重复骨架, 红验 = 抄回一份内联骨架即判红)。

## 子任务状态表

| # | issue | 改动 | 守阵 | 状态 |
|---|-------|------|------|------|
| 1 | `webui-virtual-tracker-prefix-dup` | `commands.py` 3 处字面量 `("**","[DHT]","[PeX]","[LSD]")` → import `infra.utils.VIRTUAL_TRACKER_PREFIXES`(前端 drawer.js 第 4 份归 Phase 2) | `test_virtual_tracker_prefix_single_point`(源码零字面量 + 猴补单点为空元组后 DHT 行进基线) | Done |
| 2 | `webui-status-payload-dup` | `routes/state.py` 抽 `_status_payload(manager, snap)`, `/api/status` 与 `/api/state` 共用前 6 字段(后者只叠 server/totals); `/api/state` 的 `snap` 仍**先**取好再进函数(求值顺序口径不动) | `test_api_status_and_state_share_status_payload`(6 字段两端点等值 + `/api/state` 只多 server/totals) | Done |
| 3 | `webui-sidecar-dir-convention-dup` | `server/common.py` 新增 `state_dir(manager)` 单点(含裸文件名回 `.` 兜底), `common.ensure_web_token` / `lifecycle` 启动日志 / `routes/keys.keys_file_path` 三处改走它; 跨包 4 处(tray/ops/qbmanager/cli)归后续总账轮 | `test_web_sidecar_dir_single_point`(两处调用点源码零自写 dirname + common 内只一份 + 裸文件名回 `.`) | Done |
| 4 | `webui-hr-route-guard-dup` | `routes/hr.py` 抽 `_hr_conf`(读取) / `_require_hr_enabled`(400) / `_require_hr_runtime`(409) / `_require_hr_service`(409) / `_hr_enabled_sites`(站点集派生) 五个单点, 5 处守卫 + 4 处派生式收敛; 校验码与文案、refresh 的 409→400 顺序逐字不变 | `test_hr_route_guard_single_point`(派生式与 hr_check 读取各只一份 + 400/404/409 三档行为) | Done |
| 5 | `webui-cmd-pair-handlers-dup` | `commands.py` 抽 `_group_action` / `_torrent_action` / `_category_action` / `_tags_action` / `_speed_action` 五个 (method, verb) 参数化单点, 六对 `_cmd_*`(pause/resume 组、pause/resume 单种子、super_seeding/force_start、category create/edit、tags create/delete、speed override/alt)各缩成一行 | 既有命令用例全覆盖(调用形状/日志文案逐字不变); 分类尾部文案按形状差异作参数传入 | Done |
| 6 | `webui-bulk-receipt-boilerplate-dup` | `commands.py` 抽 `_bulk_missing_msgs` + `_bulk_receipt`(有文案回 error 否则 ok 的收口形状), 两处调用点保留各自的分桶计数(recheck 计数 / 跳检按原因分桶)与日志文案; `runtime.py` 抽 `_judge_reannounce`(读 trackers → `_verdict_reannounce` 的判定处置单点), `check_pending` 与 `_advance_reannounce_background` 共用, 异常面仍各自处理 | 既有批量用例(日志串「批量跳检(成功 1, 跳过 1, 失败 2)」等)逐字断言 + 汇报确认用例 | Done |
| 7 | `webui-seed-view-restate-dup` | `views._seed_view` 删 16 个与 `_member_view` 逐字同值的重述键(eta/completion_on/time_active/last_activity/availability/dl_limit/up_limit/tracker/num_*/downloaded/amount_left/seen_complete/infohash_v2), 只留平铺扩展段 | `test_seed_view_no_member_view_restatement`(ast 静态零交集 + 同名字段值等值) | Done |
| 8 | `webui-cross-layer-constant-convention-dup`(R2 续轮) | `views.py` 表外兜底秩提命名常量 `_SHOW_STATE_RANK_LAST`; `test_webui_static_skins.py` 补 3 条跨层守阵(STATE_RANK_LAST 比对 / ETA 哨兵全树扫描 / 键位正则逐字)并注册 + 文档字符串同步; `test_web_shortcuts.py` 消第三份手抄正则(改导入后端单点); keys.py/shortcuts.js 注释补守阵指针 | `_scan_state_rank` 扩展 + `_scan_eta_sentinel` + `_scan_keys_serial_re`(值漂移/声明缺失/零命中三类突变红验 + 3 活性探针) | Done |
| 9 | `webui-partial-publish-merge-dup`(R3 续轮, 2026-10-15 用户显式指派认领修) | `runtime._publish_partial_locked` 四段(groups/singles/flat/shows)合并骨架抽 `_merge_rows(old_view, key_field, rebuilt, removed)` 静态单点; 键名传字符串而非 key_of 可调用(核心热路径, 逐行不多付函数调用); 组段传 encode 后 enc_rm 键空间 | 既有 S5 镜子 + S6「局部==全量」单测全绿 + 新增 `test_merge_rows_single_point_semantics`(契约直测)/ `test_publish_partial_merge_skeleton_single_point`(静态零重复, 红验 = 抄回内联骨架即判红) | Done |
| 10 | `webui-route-cmd-boilerplate-dup`(R4 续轮, 2026-10-15 用户显式指派认领修) | `torrent_cmds.py` 抽 `_require_skip_check(ctx)` 门控单点(403 两处逐字同 → 1 处)+ build_router 内四形状 helper(`_cmd_hash`/`_cmd_enable`/`_cmd_field`/`_cmd_str_list`), 12 端点缩为一行声明; `groups.py` 抽 `_cmd_key` 收敛 3 端点; `torrent_detail.py` 抽 `_cmd_category`/`_cmd_tags`(空组文案参数化)/`_cmd_speed_limits` 收敛三对 | 既有表驱动用例逐端点钉 (cmd, payload)(test_web_commands 15 端点 + test_web_longtail pause/resume/delete/skip-check + test_web_admin 分类/标签/限速)全绿 + 金清单守阵全绿 + 新增 `test_route_cmd_passthrough_single_point`(AST 静态, 四类突变红验) | Done |

## 实测汇总

- 收口 `test.full`: **3118 passed + 4 skipped / 覆盖率 TOTAL 99%(16586 语句 / 153 未覆盖 / 5696 分支 / 137 partial)/ 29.15s** —— 基线切片 `26-10-11-1610`(相对上基线 `26-10-11-0354`: passed +5 = 新增守阵, 无回归信号)。
- 后续批次(2026-10-15 partial-publish-merge 认领修): 收口 `test.full` 全绿, 覆盖率 TOTAL 持平(语句面变大因两文件新增守阵; 数字见 `commands run kb.baseline` 最新切片 `26-10-15-0454`, 不手抄); 新增守阵两条(合并契约直测 + 静态零重复), 均过红验; 改动文件过 `dev.fmt`(yapf facebook / 列宽 120), 行尾归一 LF 后经 `git ls-files --eol` 复核 `w/lf`。
- 新增守阵 5 个测试函数, **五条均过红验**(写回重述键 / 摘掉 status 字段 / keys.py 自写 dirname / 写回前缀字面量 / 复制一份站点派生式 —— 各半静态或动态判红, 还原即绿)。
- 各改动文件过 `commands run dev.fmt`(yapf facebook / 列宽 120), 行尾归一 LF 后 `git ls-files --eol` 复核全部 `w/lf`。

## 未做项(保持 `Open`, 等各自批次)

- 无 —— webui 10 条 refactor issue 已于 2026-10-15 R4 全部 `Done`(最后一条 `route-cmd-boilerplate` 认领修, 见子任务表 #10); 前端 drawer.js 第 4 份虚拟 tracker 字面量归 Phase 2(非本轮范围)。

## 进度日志

- 2026-10-11 15:40-16:10: 会话开工同步(快进 `727b72e2`→`c0038049`) → 读报告 §18/§19 与 10 条 issue → 追问拍板(认领载体 / 范围) → 7 条逐条改码 + 5 守阵(含红验) → `dev.fmt` + 行尾归一 → `test.full` 实测 → 立本档案 + 基线切片 + 7 条 issue 置 `Done`(补实际修法/验证/数字 + `doc-refs`) → `kb.index` 重建。

### 2026-10-15 R2 — 跨层常量守阵补齐(用户指名延后项之一)

- 开工同步(远端领先 1 笔, 快进 `22f34e13→a369c99a`) → 复验四组常量对均在(ETA 哨兵 tpl 处数 4→3 系 26-10-11-1722 计划单元格收敛, 非漂移) → 定案走 issue 建议第一支「保持守阵 + 补全机械比对」(第二支构建期注入触前端构建面, 留痕改道原因)。
- 落地: views.py `_SHOW_STATE_RANK_LAST` 命名常量; test_webui_static_skins.py 三支跨层守阵(STATE_RANK_LAST / ETA 哨兵全树 / 键位正则)注册 + 两处文档字符串同步; test_web_shortcuts.py 消第三份手抄; 三处注释指针。
- 验证: 三类突变红验(format.js 哨兵值 / shortcuts.js 正则 / app.js 兜底秩)+ 3 活性探针(零命中/声明缺失)全过 → `test.one` 两文件 50 passed → `test.full` 3209 passed + 4 skipped(基线切片 `26-10-15-0450`)。
- kb 回写: 本档案 R2 段(Summary/子任务表第 8 行/未做项出账/Refs/进度日志) + issue 置 `Done`(doc-refs 认领链) + activeContext 切片新建 + 基线切片 + `kb.index` 重建。

### 2026-10-15 R3 — partial-publish-merge 热路径合并骨架抽单点(用户指名延后项之二)

- 2026-10-15 04:36-04:54: 会话开工同步(已同步 a369c99a) → 用户显式指派「认领并修复」partial-publish-merge(上轮拍板留 Open 的热路径项, 即「各自批次」到手) → 读 issue + 坑档(web-ui/perf-cadence 热路径口径) + 上轮档案 → 抽 `_merge_rows` 静态单点(键名传字符串, 热路径不加 per-row 可调用) → 四段调用点改造 + 新增 2 守阵(契约直测 + 静态零重复, 均红验) → `test.one` 定向 + `test.full` 收口全绿 → 基线切片 `26-10-15-0454` + issue 置 `Done` + 本档案追加 → `kb.index` 重建。
- 2026-10-15 05:06 提交合流: 推送遇远端 `6adf6282`(R2 续轮)前进, rebase 三冲突(两个生成物索引取侧重跑 + 本档案手写段双方追加)按「双方记录都留」合流: Summary 并 R2/R3 两段 + Refs 并集, 子任务表 R2 行保持 #8、本项顺延 #9, 未做项仅剩 route-cmd-boilerplate, 进度日志 R2/R3 两节并列; 合并树复跑 `test.full` 确认两侧改动共存无回归。

### 2026-10-15 R4 — 路由命令透传样板收敛(用户指名延后项之三, 本轮修)

- 开工同步(远端领先 1 笔, 快进 `6adf6282→5f5689c5`) → 用户显式指派「认领并修复」route-cmd-boilerplate(上轮拍板留 Open 的最后一条) → 复验三处重复均在 → 读金清单守阵 `test_web_route_manifest_frozen`(只钉 (method, path) 集合, 不钉 handler 名 → 收敛不改注册形态) → 定案走 issue 建议的「至少对成对抽 helper」支: 表驱动注册器(单一 registrar + add_api_route 循环)评估后不改道 —— ① 收益边际小: 收敛后端点只剩声明行, 残留的是 builder 契约本身(别名/构造/return), 无逻辑重复; ② 风险不对称: 动态注册丢 handler 名(路由表可读性)+ 跨 3 文件改注册机制, 而本仓库既有口径(R1 commands 层五单点)正是参数化 helper 而非表; ③ 金清单文化偏好显式端点(create_app 瘦壳守阵同旨)。
- 落地: torrent_cmds.py `_require_skip_check(ctx)` 门控单点(两处 403 逐字同 → 1 处)+ 四形状 helper(`_cmd_hash`/`_cmd_enable`/`_cmd_field`/`_cmd_str_list`), 12 端点缩为一行声明; groups.py `_cmd_key` 收敛 pause/resume/reannounce; torrent_detail.py `_cmd_category`/`_cmd_tags`(空组 400 文案参数化, 沿用 R1「文案由调用方给」口径)/`_cmd_speed_limits` 收敛三对。差异项(命令名/字段名/文案)一律作参数传入, 行为逐字不变。
- 验证: 既有表驱动用例逐端点钉 (cmd, payload) 全绿(test_web_commands 15 端点 + test_web_longtail pause/resume/delete/skip-check + test_web_admin 分类/标签/限速 + skip_check/api_core 门控) + 金清单守阵全绿; 新增 `test_route_cmd_passthrough_single_point`(AST 静态)四类突变红验(写回载荷构造/删 helper/抄双份 helper/新增端点照抄形状)全过; `test.full` 收口全绿(基线切片 `26-10-15-0532`)。
- kb 回写: 本档案 R4 段(Summary/子任务表 #10/未做项出账/Refs/进度日志) + issue 置 `Done`(doc-refs 认领链双向闭合) + activeContext 切片新建 + 基线切片 + `kb.index` 重建。

- 2026-10-21 02:26 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)

- 2026-10-21 03:11 认领并修复 issue 26-10-20-2231(refactor-fe-config-entity-crud-dup): config_editor.js 抽 cfgEntityAdd/Rename/Remove 三骨架 + cfgTrackerDef/RuleGroupDef/RuleDef 三份差异清单, config_hub.js 三处 promptDialog 包装合并为 hubAddEntity(def), 九处入口收敛; 连带删中间态 newXName×3/addOpen/cfgAddCancel/cfgTracker(name); 50 项等价性 harness 对 HEAD 版与改后各跑一遍均全绿(开发中抓出 _rules 后缀回归并修), issue 置 Done
- 2026-10-21 02:56 认领并修复 issue 26-10-20-2230(前端 combobox 族重复): 模板骨架 5 处收敛为独立分片 tpl/combo-input.html 的 #tpl-combo-input + 五处一行 aq-combo-input 调用(差异全参数化), 键盘导航 _comboKeydown 提为 comboKeydown(ctx, ev) 单点并补 IME 守卫, 40ms 合帧收层收敛为 _popBlurArm/_popBlurCancel(删两份拷贝), 四个守阵同步; 全量 pytest 3959 passed + 10 skipped(99.29%), 新坑档 component-ref-ownership
- 2026-10-21 03:25 认领并修复 issue 26-10-20-2231(refactor-fe-config-default-ladder-dup): schema→默认值梯三处收敛为 cfgDefaultScalar/cfgDefaultForFields 单点 + 插件侧 cfgDefaultForPlugin 分派, 行为等价性实证(真实 schema 25 插件 + 18 段 diff 为空), 新增守阵 test_frontend_config_default_ladder_single_point(形态六查 + node 语义电池 11 项), 红验三类突变后精确还原, test.full 3967 passed + 10 skipped / TOTAL 99%

- 2026-10-21 04:46 认领并修复 issue 26-10-20-2231(refactor-fe-tpl-list-row-empty-dup, 台账 R23-A-05 + R23-B-06): 模板层两件套各收敛一份 —— 新增分片 tpl/list-shell.html 的 tpl-aq-row-pad / tpl-aq-empty + table.js 两组件 + app.js 注册 + 三 shell 清单挂载(aq-row-pad 落地为同组件挂两次, 占位须夹住 v-for 行; 行本身仍内联, 不碰逐行组件实例纪律), 四处三明治 8 个占位实例与十二处空态全部改挂(无图标的 4 处按语义补 hourglass/warn/inbox 且口径写进组件头注), 空态四层嵌套三元收敛为 filters.js::listEmptyText 单点 + 三视图 computed 薄壳并补回种子页缺失的索引构建分支; 新增守阵 test_frontend_list_row_pad_and_empty_single_point(形态查 + 活性探针 + node 语义电池 15 项), 红验 4/4 判红并修正活性探针被头注字样撑满的失效(计数前剥 HTML 注释); test.full 3968 passed + 10 skipped / TOTAL 99%

- 2026-10-21 05:05 Phase 3 收口(轮 24-25): R24 tests/ 审查 25 项(A11/B5/C6/D3, 拆 A-D 四子轮, jscpd 112 克隆/1.30% + ast docstring 比对 56 文件漂移) + R25 跨层六主题面总账(全局累计 347 项); 入池 6 条(5 refactor+1 test); 零源码改动, 基线 cecbe4a9

- 2026-10-21 05:35 认领并修复 issue 26-10-20-2231(refactor-fe-css-skin-token-layer-dup): atlas :root 补 --font-ui/--font-display/--font-mono 三令牌(86→89, 与另两皮肤相等, 顺带修掉自己 4 处 var(--font-mono) 裸引用的静默失效); prism 新建 css/dialogs.css 把弹窗族从 components(313 行)/views(264 行) 按原全局序迁入, link 落 views 之后, 拆后 381/818/603 行; 守阵同轮对齐(单文件路径 5 处改聚合、inset:0 判据收窄、shell cap 214)+ 新增令牌名集相等与 prism 链接序两条守阵(均红验); 等价性静态赢家表 3526 条零变化 + 真浏览器 5 态像素 prism 全 0 差异 + test.full 3971 passed

- 2026-10-21 05:47 认领并修复 issue 26-10-20-2231(refactor-fe-drawer-fetcher-boilerplate-dup, 台账 R21-A-01): drawer_store 四份 fetcher 收敛为唯一骨架 _fetchDrawerSource + 顶层差异表 _DT_FETCH(端点/归一/目标状态键/空值形状 + loading 门/失败标记/通知时机), 四入口退化为单行薄壳, stale 判点 13→4; 等价性实证(37 项 node 电池对收敛前实现同绿) + 红验七类突变全红 + 抽屉域 11 份 e2e 64 绿; 新增守阵 test_drawer_fetcher_skeleton_single_point, 四处既有守阵同步到骨架/表; 数字见 kb.baseline
