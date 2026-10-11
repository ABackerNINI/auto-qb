# 26-10-11-webui-dup-code-fixes — webui 重复代码修复轮(报告 26-10-11-0033 §18/§19)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-11 16:10
**Topics:** dup-code-audit
**Summary:** 用户「修复 webui 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」; 追问拍板**新建本修复轮档案作认领方 + 先做低风险 7 条**。报告 §18(R15 路由层)/§19(R16 表现层)共入池 webui 10 条 refactor issue —— 本轮认领并修完 7 条(virtual-tracker-prefix / status-payload / sidecar-dir / hr-route-guard / cmd-pair-handlers / bulk-receipt / seed-view-restate), 3 条按拍板留 `Open`(partial-publish-merge 热路径抽 `_merge_rows` / cross-layer-constant 跨层常量 / route-cmd-boilerplate 表驱动)。全程**行为逐字不变**: 日志文案、HTTP 状态码与文案、响应字段集一字未改, 只收骨架; 5 条新守阵(静态 ast/源码 + 动态等值)全部过红验。test.full 实测见基线切片 `26-10-11-1610`(+5 = 新增守阵, 无回归信号)。
**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md,memory-bank/testing/baselines/26-10-11-1610-webui-dup-code-fixes.md,memory-bank/activeContext/26-10-11-0314-dup-code-audit.md,memory-bank/issues/26-10-11-0310-refactor-webui-virtual-tracker-prefix-dup.html,memory-bank/issues/26-10-11-0309-refactor-webui-status-payload-dup.html,memory-bank/issues/26-10-11-0309-refactor-webui-sidecar-dir-convention-dup.html,memory-bank/issues/26-10-11-0309-refactor-webui-hr-route-guard-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-cmd-pair-handlers-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-bulk-receipt-boilerplate-dup.html,memory-bank/issues/26-10-11-0310-refactor-webui-seed-view-restate-dup.html

## 原始请求

> 用户(2026-10-11): 「修复webui部分问题:26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」

> 追问下的两处选择(AskUserQuestion): 认领载体 = **新建修复轮任务档案**(与审查档案 `26-10-10-backend-dup-code-audit` 互引, 同 26-10-07 详情面板修复轮的做法); 修复范围 = **先做低风险 7 条**(热路径 merge / 跨层常量 / 路由表驱动三条只登记不动)。

## 思考过程与决策

- **请求边界**: 用户点名「修复 + 认领」= 执行任务(认领已显式授权, 不属越界); 报告本体是「出厂即冻结」的证据快照, **不随修复回写**(同 26-10-07 详情面板修复轮口径) —— 修复记录落本档案 + 各 issue 的「实际修法」段; **与报告不建正式认领链**(报告 `doc-refs` 只指专题前史档案), 正文以链接引用(故本件 `Refs` 不含报告)。
- **风险分层(拍板「低风险 7 条」的落法)**: 三条延后各有硬理由 —— ①`partial-publish-merge` 是核心热路径(前端按行对象身份做 WeakMap 记忆化, 引用稳定性是契约), 抽 `_merge_rows` 必须配「局部重算 == 全量重跑」镜子守阵, 属独立批次; ②`cross-layer-constant`(STATE_RANK / REANNOUNCE_BLOCKED / ETA 哨兵 / 键位正则)触及前端构建面, 现状已由静态守阵钉住, 收益中/风险中; ③`route-cmd-boilerplate` 的表驱动改造须保金清单守阵 `test_web_route_manifest_frozen`, 是声明式改造而非收骨架。三条保持 `Open`, 等各自批次。
- **「行为逐字不变」是本轮的硬约束**: 这批 issue 全是 C/A 类「同一事实多表示」, 抽单点的收益是消除漂移点, **不是**顺手改文案/口径。落地时逐条核对: 分类 create/edit 的日志尾部文案形状不同(`(保存路径 X)` vs ` -> 保存路径 X`), 于是把**尾部**当参数传入而不是统一格式; 批量 recheck 说「提交」、跳检说「成功」, 于是 ok/fail 两行日志文案由调用方给, 只收「有文案回 error 否则 ok」的形状; hr refresh 端点「线程未启动 409 先于未启用 400」的顺序也原样保留。
- **守阵策略**: 静态(ast/源码串)+ 动态(等值/行为)双半 —— 单靠动态抓不到「又抄了一份」(值本来相等), 单靠静态抓不到「改单点却没生效」; 五条守阵均做了红验(写回重述键 / 摘字段 / 自写 dirname / 写回字面量 / 复制派生式)。
- **静态守阵撞车的一条**: `test_web_shortcuts.py` 原钉 `assert "manager.state_file" in keys_py`(意图 = 「存储路径必须与 web.token 同寻址」), keys.py 改走 `state_dir` 单点后字面量消失 —— 断言改写为 `assert "state_dir(manager)" in keys_py`, 意图不变。
- **行尾事故(本轮踩到)**: 用 `python open(...,'w')` 写源码会把 LF 翻成 CRLF(仓库 `.gitattributes` 是 `* text=auto eol=lf`) —— 9 个文件被翻, 已一次性归一回 LF 并经 `git ls-files --eol` 复核(以后写码一律带 `newline='\n'`)。

## 实现计划

按「低风险优先」串行 7 步, 每步改完跑 `test.one` 定向用例, 收口 `test.full`。改动面: `webui/commands.py` / `webui/views.py` / `webui/runtime.py` / `webui/server/common.py` / `webui/server/lifecycle.py` / `webui/server/routes/{state,hr,keys}.py` + 4 个测试文件的守阵与计划清单。

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

## 实测汇总

- 收口 `test.full`: **3118 passed + 4 skipped / 覆盖率 TOTAL 99%(16586 语句 / 153 未覆盖 / 5696 分支 / 137 partial)/ 29.15s** —— 基线切片 `26-10-11-1610`(相对上基线 `26-10-11-0354`: passed +5 = 新增守阵, 无回归信号)。
- 新增守阵 5 个测试函数, **五条均过红验**(写回重述键 / 摘掉 status 字段 / keys.py 自写 dirname / 写回前缀字面量 / 复制一份站点派生式 —— 各半静态或动态判红, 还原即绿)。
- 各改动文件过 `commands run dev.fmt`(yapf facebook / 列宽 120), 行尾归一 LF 后 `git ls-files --eol` 复核全部 `w/lf`。

## 未做项(保持 `Open`, 等各自批次)

- `26-10-11-0309-refactor-webui-partial-publish-merge-dup` —— 热路径四段抽 `_merge_rows`, 需「局部重算 == 全量重跑」镜子守阵。
- `26-10-11-0310-refactor-webui-cross-layer-constant-convention-dup` —— 跨层常量(STATE_RANK / REANNOUNCE_BLOCKED / ETA 哨兵 / 键位正则)触前端构建面, 现状已有静态守阵钉住。
- `26-10-11-0309-refactor-webui-route-cmd-boilerplate-dup` —— 「路由→命令」表驱动改造, 须保金清单守阵 `test_web_route_manifest_frozen`。

## 进度日志

- 2026-10-11 15:40-16:10: 会话开工同步(快进 `727b72e2`→`c0038049`) → 读报告 §18/§19 与 10 条 issue → 追问拍板(认领载体 / 范围) → 7 条逐条改码 + 5 守阵(含红验) → `dev.fmt` + 行尾归一 → `test.full` 实测 → 立本档案 + 基线切片 + 7 条 issue 置 `Done`(补实际修法/验证/数字 + `doc-refs`) → `kb.index` 重建。
