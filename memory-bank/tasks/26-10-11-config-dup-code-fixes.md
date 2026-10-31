# 26-10-11-config-dup-code-fixes — config 包重复代码修复(dup-code-audit 7 issue)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-29
**Topics:** dup-code-audit
**Summary:** 用户指派修复报告 26-10-11-0033(config 部分)并认领相关 issue —— 7 条 refactor(0031 枚举双份 / 0032 默认多源 · 键面文档漂移 · loaders 绕过 _get · 站点页面事实双份 · 小校验三写两套 · writer 备份复制块)。修复口径: 枚举族收敛 schema/fields 单点 + validation/rules・sections・rules/expr/env 引用派生; loaders 两处统一走 _get; models.SiteHrCheckConfig 派生五键默认改空(真值只在 SITE_PRESETS); sections 抽 _try_port/_try_time_window; writer 抽 _atomic_copy; docs 漂移修正(log.format / hr_check 键数 / 档案 adapter 列 / schema_version 默认派生 CURRENT_VERSIONS) + docs↔代码守卫与枚举单源守卫入 test_config_schema。
**Refs:** memory-bank/issues/26-10-11-0031-refactor-config-schema-validation-enum-dup.html, memory-bank/issues/26-10-11-0032-refactor-config-default-multi-source.html, memory-bank/issues/26-10-11-0032-refactor-config-key-surface-doc-drift.html, memory-bank/issues/26-10-11-0032-refactor-config-loaders-get-inconsistency.html, memory-bank/issues/26-10-11-0032-refactor-config-site-preset-page-facts-dup.html, memory-bank/issues/26-10-11-0032-refactor-config-validation-smallchecks-dup.html, memory-bank/issues/26-10-11-0032-refactor-config-writer-backup-copy-dup.html, memory-bank/testing/baselines/26-10-11-1611-config-dup-code-fixes.md
## 原始请求

> 用户(2026-10-11): 「修复config部分问题:26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」

即: 按滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 的 config 部分(轮 01–04 发现, 已入池 7 条 refactor issue)执行修复, 并把 7 条 issue 置 In Progress / Done(认领人 = 用户指派, create-issue skill「修一条 issue 时」第 1 步满足)。

## 思考过程与决策

- **请求边界**: 执行任务(修复 + 认领均显式指派); 工作树改动随本专题入库。
- **立档依据**: 改动 ≥3 源文件(memory-bank skill 立档阈值 2)—— 实际涉及 config 包 8 文件 + rules/expr/env.py + docs ×2 + tests + ui_harness。
- **枚举族单点选 schema/fields**: 它是纯声明模块(fields.py「无项目内依赖, 其余 schema 子模块全部由它派生」), validation/core 已有 `from ..schema.trackers import` 同向先例; rules/expr/env 顶层引 config 已有先例(rules/base.py 顶层 `from ..config import`), env 引 `config.schema.fields` 不引入新的环(config 包无模块级 rules 导入, 已 grep 复验)。
- **MAINTENANCE_TAG_MODES 不搬**: schema 侧是死件(全仓无引用、schema/__init__ 未导出), 按 issue 建议直接删除, 活件留在 validation/core(本包单点)。
- **validation/__init__ 重导出面**: 旧别名(`EXECUTE_ONCE_VALUES` 等)全仓只有 validation 自身与 1 处测试引用 —— 重导出改挂规范名, 测试同步改, 不留双名。
- **loaders._get 统一**: parse_time/parse_bool 内部已自 str 化(infra/utils 复验), 原 `str(spec[k])` 包裹可安全去掉; GlobalSpeedLimitCurve 必填 dat_path/curves 无法缺省构造, 字段默认经类属性读取(dataclass 有默认值的字段即类属性, 单源仍是 models)。
- **SiteHrCheckConfig 派生五键默认改空**: fetchable 属性全仓无消费点(已 grep); 测试侧 hr_helpers 全显式传参; ui_harness 三处桩构造补 `listing="list"` 保桩显示不失真(stub-bypass-apply 教训: 桩要跟生产同构); hr/adapters 工厂本就有 `conf.adapter or DEFAULT_ADAPTER` 兜底, 空串不会炸。
- **docs 漂移修正版图**(0032 default-multi-source 改道说明): 「schema.Field.default 全键由 models 派生」需要 YAML↔解析空间逐键换算, 收益/成本不匹配且已有 unit_default/可解析守卫兜底 —— 改道为: ①实漂移逐处修正(log.format / hr_check 键数 7·8·9 / keys.md 档案 adapter 列 / schema_version 默认 "1"→派生 CURRENT_VERSIONS); ②补 docs↔代码守卫(log.format 字面 + 键数 token)防回潮。完整派生留待后续如需再做。
- **小校验收敛口径**: `_try_port` 保留逐字原文案(三处本就同款); 时间窗统一走 parse_hm 单点, quiet_hours 无横线分支并入(报错文案统一为「须为 'HH:MM-HH:MM'(可跨午夜)」) —— test_config 两处断言同步。
- **writer._atomic_copy**: 只抽「读源文件 + atomic_write 写出 + 父目录创建」; backup_versioned 的版本号命名与 _backup 的存在性检查各留调用方(与 issue 建议一致)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 立档 + 7 issue 认领(In Progress + doc-refs 双向链) + kb.index | Done |
| S2 | 0031: 枚举族收敛 schema 单点(validation/rules・__init__・sections・rules/expr/env) + 删死件 + 报错文案派生 | In Progress |
| S3 | 0032 smallchecks: _try_port + _try_time_window 单点 | In Progress |
| S4 | 0032 loaders: 两处统一 _get | In Progress |
| S5 | 0032 site-preset: models 派生五键默认改空 + ui_harness 桩补参 | In Progress |
| S6 | 0032 writer: _atomic_copy 单点 | In Progress |
| S7 | 0032 default/key-surface: docs 漂移修正 + schema_version 默认派生 + 守卫测试(枚举单源/docs↔代码/页面事实/版本默认) | In Progress |
| S8 | 定向测试 → fmt → test.full + 基线切片 | Open |
| S9 | issue 置 Done(实际修法/验证/数字) + 收尾回写(档案/切片/kb.index/kb.check) | Open |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| 26-10-11-0031 枚举/常量双份收敛 | Done | schema 单点 + 三方引用派生; MAINTENANCE_TAG_MODES 死件删除; 报错文案常量 join |
| 26-10-11-0032 默认值多源 | Done | 改道: 实漂移修正 + schema_version 派生 + docs 守卫(理由见决策) |
| 26-10-11-0032 键面文档漂移 | Done | hr_check 键数统一 9(=KNOWN_HR_CHECK_KEYS) + keys.md adapter 列修正 + docs↔代码守卫 |
| 26-10-11-0032 loaders 绕过 _get | Done | load_qb_traffic ×5 + load_global_speed_limit_curve ×2 统一 _get |
| 26-10-11-0032 站点页面事实双份 | Done | models 派生五键默认改空, 真值只留 SITE_PRESETS; ui_harness 桩补参 |
| 26-10-11-0032 validation 小校验重复 | Done | _try_port 三处 + 时间窗 parse_hm 单点(quiet_hours 文案统一) |
| 26-10-11-0032 writer 备份复制块 | Done | _atomic_copy 单点, backup_versioned/_backup 复用 |

## 进度日志

### 2026-10-11 R0 — 认领与开工

- 同步: `commands run my-commit-flow.sync` 快进 dacecf3d→c0038049。
- 复验(issue 锚点逐条核对源码, 2026-10-11): 0031 枚举双份 9 族 + MAINTENANCE_TAG_MODES 死件(schema/fields.py:178 无引用) + env._STATE_ATTRS 第三份 + rules.py 报错硬编码串 —— 全部仍在; 0032 loaders 两处三元绕过 _get / writer 两处备份块逐字同 / sections 端口三写+时间窗两套 / models 五键具体站点值(且 keys.md btschool adapter 列与 SITE_PRESETS 漂移: 文档写 nexusphp, 代码是 btschool) —— 全部仍在。
- 7 issue 置 In Progress, doc-refs 指向本档案(双向认领链), kb.index 重建。

### 2026-10-11 R1 — 修复落地与验证

- **0031 枚举收敛**: 单点 schema/fields(吸收 validation 侧语义注释); validation/rules.py 删 7 个本地常量改引派生(EXECUTE_ONCE/STOP_IF/TRIGGERS/FIELD_WATCH_ALLOWED/CHECKING_BASIC/CHECKING_MODES/DELETED_ALLOWED_ACTIONS/STATE_ATTRS), validation/__init__ 重导出改挂规范名(旧 *-VALUES 别名全仓仅测试 1 处引用, 同步改), sections 删 NOTIFY_CHANNELS/NOTIFY_LEVELS 本地副本改引 schema(附 LOG_LEVELS 报错文案派生), rules/expr/env 删 _STATE_ATTRS 第三份; schema 死件 MAINTENANCE_TAG_MODES 删除(活件留 core, 注释更新); rules.py 状态属性报错改 `"/".join(STATE_ATTRS)` 派生。防环复验: config 包无模块级 rules 导入(registry 懒加载), env 顶层引 config.schema.fields 与 rules/base.py 既有顶层引 config 同向。
- **0032 各项**: loaders 两处统一 _get(parse_time/parse_bool 内部自 str 化, 显式包裹去除; GlobalSpeedLimitCurve 默认经类属性读取); models 派生五键默认改空(fetchable 无消费点; ui_harness 三处桩补 listing); core 抽 _try_port/_try_time_window(端口三处文案逐字不变; quiet_hours 文案统一, test_config 断言同步); writer 抽 _atomic_copy(语义不变)。
- **0032 docs/守卫**: configuration.md log.format + 9 键、keys.md 9 键 + btschool adapter 列修正; schema_version Field.default 派生 CURRENT_VERSIONS; 新守阵 4 条(test_validation_enums_are_schema_derived / test_site_hr_page_facts_are_preset_only / test_schema_version_field_default_tracks_versioning / test_docs_config_facts_match_code), 测试计划 docstring 同步。
- **验证**: 定向先跑 test.quick(除自引发措辞 1 红外全绿, 已改时不变措辞复验); `commands run test.full` 全绿, 数字见基线切片 [26-10-11-1611](../testing/baselines/attachments/26-10-11-1611-config-dup-code-fixes.md); dev.fmt 覆盖 13 个改过的 .py; 7 issue 置 Done(实际修法/验证/数字进 issue changelog)。
- **改道说明**: 0032 default-multi-source 的「schema.Field.default 全键由 models 派生」不做(YAML↔解析空间逐键换算成本高, 现有 unit_default/可解析守卫 + 新 docs 守卫兜主要漂移面), 其余按建议落地。

- 2026-10-21 02:26 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)

- 2026-10-21 03:11 认领并修复 issue 26-10-20-2231(refactor-fe-config-entity-crud-dup): config_editor.js 抽 cfgEntityAdd/Rename/Remove 三骨架 + cfgTrackerDef/RuleGroupDef/RuleDef 三份差异清单, config_hub.js 三处 promptDialog 包装合并为 hubAddEntity(def), 九处入口收敛; 连带删中间态 newXName×3/addOpen/cfgAddCancel/cfgTracker(name); 50 项等价性 harness 对 HEAD 版与改后各跑一遍均全绿(开发中抓出 _rules 后缀回归并修), issue 置 Done
- 2026-10-21 02:56 认领并修复 issue 26-10-20-2230(前端 combobox 族重复): 模板骨架 5 处收敛为独立分片 tpl/combo-input.html 的 #tpl-combo-input + 五处一行 aq-combo-input 调用(差异全参数化), 键盘导航 _comboKeydown 提为 comboKeydown(ctx, ev) 单点并补 IME 守卫, 40ms 合帧收层收敛为 _popBlurArm/_popBlurCancel(删两份拷贝), 四个守阵同步; 全量 pytest 3959 passed + 10 skipped(99.29%), 新坑档 component-ref-ownership
- 2026-10-21 03:25 认领并修复 issue 26-10-20-2231(refactor-fe-config-default-ladder-dup): schema→默认值梯三处收敛为 cfgDefaultScalar/cfgDefaultForFields 单点 + 插件侧 cfgDefaultForPlugin 分派, 行为等价性实证(真实 schema 25 插件 + 18 段 diff 为空), 新增守阵 test_frontend_config_default_ladder_single_point(形态六查 + node 语义电池 11 项), 红验三类突变后精确还原, test.full 3967 passed + 10 skipped / TOTAL 99%

- 2026-10-21 04:46 认领并修复 issue 26-10-20-2231(refactor-fe-tpl-list-row-empty-dup, 台账 R23-A-05 + R23-B-06): 模板层两件套各收敛一份 —— 新增分片 tpl/list-shell.html 的 tpl-aq-row-pad / tpl-aq-empty + table.js 两组件 + app.js 注册 + 三 shell 清单挂载(aq-row-pad 落地为同组件挂两次, 占位须夹住 v-for 行; 行本身仍内联, 不碰逐行组件实例纪律), 四处三明治 8 个占位实例与十二处空态全部改挂(无图标的 4 处按语义补 hourglass/warn/inbox 且口径写进组件头注), 空态四层嵌套三元收敛为 filters.js::listEmptyText 单点 + 三视图 computed 薄壳并补回种子页缺失的索引构建分支; 新增守阵 test_frontend_list_row_pad_and_empty_single_point(形态查 + 活性探针 + node 语义电池 15 项), 红验 4/4 判红并修正活性探针被头注字样撑满的失效(计数前剥 HTML 注释); test.full 3968 passed + 10 skipped / TOTAL 99%

- 2026-10-21 05:05 Phase 3 收口(轮 24-25): R24 tests/ 审查 25 项(A11/B5/C6/D3, 拆 A-D 四子轮, jscpd 112 克隆/1.30% + ast docstring 比对 56 文件漂移) + R25 跨层六主题面总账(全局累计 347 项); 入池 6 条(5 refactor+1 test); 零源码改动, 基线 cecbe4a9

- 2026-10-21 05:35 认领并修复 issue 26-10-20-2231(refactor-fe-css-skin-token-layer-dup): atlas :root 补 --font-ui/--font-display/--font-mono 三令牌(86→89, 与另两皮肤相等, 顺带修掉自己 4 处 var(--font-mono) 裸引用的静默失效); prism 新建 css/dialogs.css 把弹窗族从 components(313 行)/views(264 行) 按原全局序迁入, link 落 views 之后, 拆后 381/818/603 行; 守阵同轮对齐(单文件路径 5 处改聚合、inset:0 判据收窄、shell cap 214)+ 新增令牌名集相等与 prism 链接序两条守阵(均红验); 等价性静态赢家表 3526 条零变化 + 真浏览器 5 态像素 prism 全 0 差异 + test.full 3971 passed

- 2026-10-21 05:47 认领并修复 issue 26-10-20-2231(refactor-fe-drawer-fetcher-boilerplate-dup, 台账 R21-A-01): drawer_store 四份 fetcher 收敛为唯一骨架 _fetchDrawerSource + 顶层差异表 _DT_FETCH(端点/归一/目标状态键/空值形状 + loading 门/失败标记/通知时机), 四入口退化为单行薄壳, stale 判点 13→4; 等价性实证(37 项 node 电池对收敛前实现同绿) + 红验七类突变全红 + 抽屉域 11 份 e2e 64 绿; 新增守阵 test_drawer_fetcher_skeleton_single_point, 四处既有守阵同步到骨架/表; 数字见 kb.baseline

- 2026-10-22 01:49 issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup 认领并修复: ctx-menus.html 四支各一份 .ctx-item 骨架(5 份)合并为一条 ctxItems(ctxMenuKind()) v-for, 骨架 5 份→2 份; 三件守阵比对面搬到 ctxMenuKind() 单点; 全量 3994 passed/覆盖率 99.28%

- 2026-10-22 02:24 认领并修复 issue 26-10-20-2231(模板层单元格碎片): site-chip 3 份收敛为 #tpl-aq-site-chip 单点组件(三调用点, DOM 逐字同), torrent chip+torrents.html 行级补 search-hit(休眠绑定已取证), m-progress 四处抽 $root.progPct 单点, dur-body 注释跨文件互指; 全量 3995 passed/99%, e2e 三规格 64 passed

- 2026-10-22 03:26 认领并修复 issue 26-10-20-2231(fe-single-point-bypass-dup): 7 族单点绕过全部收敛 —— 提 cfgTruthy/aqbAuthHeaders/kibToBytes/bytesToKib/AQB_UNIT_LADDER/_fmtLadder/hrEpTitle 单点, 合并 cfgPathKey 第二份 path→key 单点, 11 处内联改调 + 单点处禁内联注释; 单位梯保留表格/图轴精度分歧(参数化), 阶梯核对无 KiB/KB 口径差; Bearer 取顶层函数护住 auth.js 单文件探针; test.full 与 e2e 三规格双绿(数字见基线切片 26-10-22-0324), 档案/契约/索引回写
- 2026-10-22 04:36 认领并修复 issue 26-10-20-2231(refactor-fe-polling-family-dup): 轮询生命周期收敛为 polling.js 骨架 startPoll/stopPoll/awaitPoll, 抽屉侧补悬挂兜底, document.hidden 守卫单点; 新守阵 + 6 处既有守阵换形态; 红验八类突变全红; e2e 340 passed; test.full 3989 passed / 99.17%

- 2026-10-22 12:44 认领并修复 26-10-21-0502-refactor-test-shared-micro-helper-dup: 8 族同名小助手逐字拷贝(24 处)全部收口共享层单点(helpers/webui_helpers), test.full 实测数字见 kb.baseline(切片 26-10-22-1245-dup-code-audit)

- 2026-10-29 04:33 Phase 4(轮 26)汇总收口: 滚动报告追加 §33 —— 全局 347 项(A140/B35/C94/D78)定稿 + 入池 69 条全部 Done(清偿率 100%) + 候选排序总表 21 行(收益/风险 × 现状) + 清偿顺序三批 + 六条方法论结论 + 计划 §08 验收五项逐条核销达成; 计划 26-10-10-2333 与报告 26-10-11-0033 同步置 Done; 纯审查零源码改动(取证基线 83461080)

- 2026-10-29 17:20 B 类重复代码复核收口: 35 项(后端15/前端15/tests5)逐项对当前代码复核定案, 入池 22 条(16 refactor light + 6 bug standard, 专题 dup-code-audit-b-recheck), 13 项判不值得/已消解并各写重开条件; 零源码改动, 守卫 79 passed
