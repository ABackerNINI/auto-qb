# 26-10-11-config-dup-code-fixes — config 包重复代码修复(dup-code-audit 7 issue)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-21
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
- **验证**: 定向先跑 test.quick(除自引发措辞 1 红外全绿, 已改时不变措辞复验); `commands run test.full` 全绿, 数字见基线切片 [26-10-11-1611](../testing/baselines/26-10-11-1611-config-dup-code-fixes.md); dev.fmt 覆盖 13 个改过的 .py; 7 issue 置 Done(实际修法/验证/数字进 issue changelog)。
- **改道说明**: 0032 default-multi-source 的「schema.Field.default 全键由 models 派生」不做(YAML↔解析空间逐键换算成本高, 现有 unit_default/可解析守卫 + 新 docs 守卫兜主要漂移面), 其余按建议落地。

- 2026-10-21 02:26 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)

- 2026-10-21 03:11 认领并修复 issue 26-10-20-2231(refactor-fe-config-entity-crud-dup): config_editor.js 抽 cfgEntityAdd/Rename/Remove 三骨架 + cfgTrackerDef/RuleGroupDef/RuleDef 三份差异清单, config_hub.js 三处 promptDialog 包装合并为 hubAddEntity(def), 九处入口收敛; 连带删中间态 newXName×3/addOpen/cfgAddCancel/cfgTracker(name); 50 项等价性 harness 对 HEAD 版与改后各跑一遍均全绿(开发中抓出 _rules 后缀回归并修), issue 置 Done
