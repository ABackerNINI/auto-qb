# 26-10-15-backend-store-recover-lock-dedup — hr 恢复链与文件锁跨包收口(issue hr-store-recover-lock-family-dup 认领与修复)

**Status:** Done
**Added:** 2026-10-15
**Updated:** 2026-10-22
**Summary:** 用户指令「认领并修复 memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html」—— dup-code-audit infra 轮(R18)对 R6/R2/R3 三轮暂缓跨包件的合并考量收口。口径沿用前修复轮保守纪律(行为逐位不变, 仅编排/构造收口): ① `infra/store_recovery.py` 新增「读坏→(挪走)留证→读 `.bak`」编排单点 `recover_corrupt_file`(回调式 read_backup + 可选 quarantine, 不传 = 原地保留)与 `quarantine_bad_file` 时间戳留证单点, hr `HrLockSession._recover` 与 state `StateService.load()` 损坏分支两处调用 —— 语义差异(hr 挪走留证/schema 迁移/read_error 消息 vs state 原地保留/_CORRUPT 三态/分级日志/立即自愈写回)全部保留在调用方; ② `infra/locking.py` 新增 `open_file_lock`/`release_file_lock` 构造/释放单点, hr 站点锁与 SingleInstanceLock 同族收口(hr/store 不再裸 import filelock); ③ 新守阵 tests/test_store_recovery.py 十条(静态两判据均过红验)。测试数字唯一权威在基线切片(见 **Refs:**)。
**Topics:** dup-code-audit

**Refs:** memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html, memory-bank/testing/baselines/26-10-15-0540-backend-store-recover-lock-dedup.md
## 原始请求

> 用户(2026-10-15): 「认领并修复 memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html」

## 思考过程与决策

- **请求边界判定**: 执行任务(改代码 + 认领 issue)。用户显式「认领并修复」= 指派 + 修复双授权(create-issue skill「Agent 不得自行认领」以用户指派为前提, 本条满足); 未含 commit/push 授权, 收尾不做提交。
- **复验(防过期原则 5)**: 锚点仍在 —— hr/store.py 裸 `FileLock`(import + 构造各一处)、恢复链两套同族(`_recover` ↔ `load()` 损坏分支); 相对入池取证的 2026-10-11 02:39 行号有漂移(轮次间文件长短变化), 按符号 + grep 重定位。
- **回调式单点 vs 内置编排(改道点)**: 首版把「先留证」做进 infra 内部(按 path 直接挪), hr 两条例行 seam(`store.quarantine = lambda: ""` 模拟挪不动)被绕过, 首跑 test.one 双红 —— 说明**处置动作必须经调用方回调**: 单点只保留编排顺序纪律与兜底实现(`quarantine_bad_file`), hr 的 `store.quarantine` 方法保留为公开面 + seam。改道后双红即绿。
- **语义差异保留判据**(issue 建议点名的两处 + 实测第三处): hr 有 schema 迁移/版本回退即拒(recoverable=False 不挪也不从备份猜)、坏文件挪走留证、结论拼 `read_error`; state 有 `_CORRUPT` 三态、future 版本 fail-fast(不算损坏)、原地保留、立即自愈写回且失败不阻断启动。单点只收「顺序纪律 + 挪文件 + (数据, 原因) 契约」, 消息/日志/迁移/写回全部留调用方。
- **不合并的第三处差异**: state 的 `_write_back_recovered`(立即自愈写回, OSError 只告警)与 hr 的 commit 期 `keep_backup=not recovered_from_backup` —— 时机/载荷/异常口径都不同; 且 `test_load_state_recovered_writeback_failure_is_nonfatal` 按 `qb_state.utils.atomic_write` 打补丁(模块属性), 抽走会把补丁面打穿。只各保留 + 在 infra/store_recovery docstring 以第 3 条纪律互指。
- **锁收口的粒度**: 不做「锁类统一」—— SingleInstanceLock 有 meta 伴生/固定超时 0/CLI 错误通道, hr 有 per-site 路径/可配超时/HrLockBusy 领域异常, 强并类会改错误语义; 只收 filelock 依赖与构造/释放纪律(`open_file_lock` / `release_file_lock`), Timeout→领域异常的翻译留各自调用方。
- **filelock 版本事实**: 本仓锁定 3.32.6, `BaseFileLock` 已无 `_lock_file` 属性(句柄由库内 fd 生命周期自理), 旧 `_lock_file.close()` 仅作旧版兜底(AttributeError 静默跳过) —— `release_file_lock` 内保留兜底并注明, 行为与改前等价(改前该方法同样静默跳过)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步 + issue 复验 + 置 `In Progress` + kb.index | Done |
| S2 | `infra/store_recovery.py` 编排单点(回调式) + `quarantine_bad_file` | Done |
| S3 | `infra/locking.py` 构造/释放单点 + SingleInstanceLock 委托 | Done |
| S4 | `hr/store.py`: 锁走单点 / quarantine 委托 / `_recover` 走编排 | Done |
| S5 | `core/state.py`: `load()` 损坏分支走编排 + `_read_backup_dict` | Done |
| S6 | 守阵 `tests/test_store_recovery.py`(静态 2 + 行为 8) + 红验 | Done |
| S7 | test.full 全量 + 基线切片 | Done |
| S8 | 收尾: issue 置 `Done`(doc-refs) / 档案 / 切片 / kb.index / kb.check | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| 恢复链编排单点 | Done | `recover_corrupt_file`(回调式) + `quarantine_bad_file`; hr/state 两处调用 |
| 语义差异保留 | Done | hr 迁移/read_error/挪走留证 vs state 三态/分级日志/原地保留/立即自愈 |
| 文件锁单点 | Done | `open_file_lock` / `release_file_lock`; hr 站点锁与 SingleInstanceLock 共用 |
| 守阵与红验 | Done | 静态两判据(`.bad-` 字面量分布 / `from filelock import` 分布)均红验; 行为用例 8 条 |
| 认领链 | Done | issue `doc-refs` ↔ 本档案 `**Refs:**` 双向; 会话切片反向声明 |
| 收尾(测试/索引/基线) | Done | 基线切片 `26-10-15-0540-backend-store-recover-lock-dedup`; kb.index / kb.check |

## 进度日志

### 2026-10-15 — 单会话收口(R12)

- **开工同步**: `commands run my-commit-flow.sync` → 已同步 `5f5689c5`。
- **复验**: 锚点均在(hr/store.py 裸 FileLock; `_recover` 与 `load()` 损坏分支同族); 置 `In Progress` + `kb.index`。
- **改道记录(首跑双红 → 回调式改道)**: 首版 infra 内置按 path 挪文件, 绕过 hr 例行的 `store.quarantine` seam(`test_repeated_read_failure_does_not_rewarn` / `test_store_recover_unmovable_keeps_backup` 双红) → 处置改回调注入, 单点只留编排纪律。教训: 单点化时所有「调用方可能打桩的既有方法」都是 seam, 要么保留在调用链上, 要么显式接受并同步改测试。
- **改动**: 如子任务表; 全部过 `dev.fmt`(yapf 顺带规范化 locking.py 两处既有未格式化行, fmt 闸门对 `src/` 生效, 保留其结果)。
- **行为等价审计**: `read_error` 四段消息逐字重组(坏文件已挪走 / 未能挪走 / 已从备份恢复 / 备份不可用); state 的 WARNING/INFO/ERROR 三条日志与自愈写回路径不变; hr 锁的 acquire / Timeout→HrLockBusy / release 纪律不变(唯一微差: 释放失败 debug 文案「释放站点锁失败: {path}」→「释放站点锁 {path} 失败: ...」, 无守阵钉该文案)。
- **验证**: 定向 6 文件全绿(hr_store / locking / rule_engine / hr_status / hr_service / store_recovery); test.full 全绿, 数字唯一权威在基线切片(见 **Refs:**), 此处不手抄。
- **零改动确认**: 未触碰 `config.yml` / `auto-qb-data/`; webui/torrents 零改动; 既有测试文件零修改(仅新增 `tests/test_store_recovery.py`)。

- 2026-10-21 02:26 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)

- 2026-10-21 03:11 认领并修复 issue 26-10-20-2231(refactor-fe-config-entity-crud-dup): config_editor.js 抽 cfgEntityAdd/Rename/Remove 三骨架 + cfgTrackerDef/RuleGroupDef/RuleDef 三份差异清单, config_hub.js 三处 promptDialog 包装合并为 hubAddEntity(def), 九处入口收敛; 连带删中间态 newXName×3/addOpen/cfgAddCancel/cfgTracker(name); 50 项等价性 harness 对 HEAD 版与改后各跑一遍均全绿(开发中抓出 _rules 后缀回归并修), issue 置 Done
- 2026-10-21 02:56 认领并修复 issue 26-10-20-2230(前端 combobox 族重复): 模板骨架 5 处收敛为独立分片 tpl/combo-input.html 的 #tpl-combo-input + 五处一行 aq-combo-input 调用(差异全参数化), 键盘导航 _comboKeydown 提为 comboKeydown(ctx, ev) 单点并补 IME 守卫, 40ms 合帧收层收敛为 _popBlurArm/_popBlurCancel(删两份拷贝), 四个守阵同步; 全量 pytest 3959 passed + 10 skipped(99.29%), 新坑档 component-ref-ownership
- 2026-10-21 03:25 认领并修复 issue 26-10-20-2231(refactor-fe-config-default-ladder-dup): schema→默认值梯三处收敛为 cfgDefaultScalar/cfgDefaultForFields 单点 + 插件侧 cfgDefaultForPlugin 分派, 行为等价性实证(真实 schema 25 插件 + 18 段 diff 为空), 新增守阵 test_frontend_config_default_ladder_single_point(形态六查 + node 语义电池 11 项), 红验三类突变后精确还原, test.full 3967 passed + 10 skipped / TOTAL 99%

- 2026-10-21 04:46 认领并修复 issue 26-10-20-2231(refactor-fe-tpl-list-row-empty-dup, 台账 R23-A-05 + R23-B-06): 模板层两件套各收敛一份 —— 新增分片 tpl/list-shell.html 的 tpl-aq-row-pad / tpl-aq-empty + table.js 两组件 + app.js 注册 + 三 shell 清单挂载(aq-row-pad 落地为同组件挂两次, 占位须夹住 v-for 行; 行本身仍内联, 不碰逐行组件实例纪律), 四处三明治 8 个占位实例与十二处空态全部改挂(无图标的 4 处按语义补 hourglass/warn/inbox 且口径写进组件头注), 空态四层嵌套三元收敛为 filters.js::listEmptyText 单点 + 三视图 computed 薄壳并补回种子页缺失的索引构建分支; 新增守阵 test_frontend_list_row_pad_and_empty_single_point(形态查 + 活性探针 + node 语义电池 15 项), 红验 4/4 判红并修正活性探针被头注字样撑满的失效(计数前剥 HTML 注释); test.full 3968 passed + 10 skipped / TOTAL 99%

- 2026-10-21 05:05 Phase 3 收口(轮 24-25): R24 tests/ 审查 25 项(A11/B5/C6/D3, 拆 A-D 四子轮, jscpd 112 克隆/1.30% + ast docstring 比对 56 文件漂移) + R25 跨层六主题面总账(全局累计 347 项); 入池 6 条(5 refactor+1 test); 零源码改动, 基线 cecbe4a9

- 2026-10-21 05:35 认领并修复 issue 26-10-20-2231(refactor-fe-css-skin-token-layer-dup): atlas :root 补 --font-ui/--font-display/--font-mono 三令牌(86→89, 与另两皮肤相等, 顺带修掉自己 4 处 var(--font-mono) 裸引用的静默失效); prism 新建 css/dialogs.css 把弹窗族从 components(313 行)/views(264 行) 按原全局序迁入, link 落 views 之后, 拆后 381/818/603 行; 守阵同轮对齐(单文件路径 5 处改聚合、inset:0 判据收窄、shell cap 214)+ 新增令牌名集相等与 prism 链接序两条守阵(均红验); 等价性静态赢家表 3526 条零变化 + 真浏览器 5 态像素 prism 全 0 差异 + test.full 3971 passed

- 2026-10-21 05:47 认领并修复 issue 26-10-20-2231(refactor-fe-drawer-fetcher-boilerplate-dup, 台账 R21-A-01): drawer_store 四份 fetcher 收敛为唯一骨架 _fetchDrawerSource + 顶层差异表 _DT_FETCH(端点/归一/目标状态键/空值形状 + loading 门/失败标记/通知时机), 四入口退化为单行薄壳, stale 判点 13→4; 等价性实证(37 项 node 电池对收敛前实现同绿) + 红验七类突变全红 + 抽屉域 11 份 e2e 64 绿; 新增守阵 test_drawer_fetcher_skeleton_single_point, 四处既有守阵同步到骨架/表; 数字见 kb.baseline

- 2026-10-22 01:49 issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup 认领并修复: ctx-menus.html 四支各一份 .ctx-item 骨架(5 份)合并为一条 ctxItems(ctxMenuKind()) v-for, 骨架 5 份→2 份; 三件守阵比对面搬到 ctxMenuKind() 单点; 全量 3994 passed/覆盖率 99.28%
