# 3117 —— config 重复代码修复(7 issue)全量基线

> 摘要: 档案 `26-10-11-config-dup-code-fixes` 执行轮(用户「修复config部分问题 + 相关issue一并认领」)。修复 7 条 refactor issue: 枚举族收敛 schema/fields 单点(validation/rules・sections・rules/expr/env 引用派生, 死件 MAINTENANCE_TAG_MODES 删除, 报错文案常量 join 派生) / loaders 两处统一 _get / models.SiteHrCheckConfig 派生五键默认改空 / validation 抽 _try_port+_try_time_window / writer 抽 _atomic_copy / docs 漂移修正(log.format・hr_check 键数・keys.md adapter 列)+ schema_version 默认派生 CURRENT_VERSIONS。新增守阵 4 条(test_config_schema)。改 `src/` 10 文件 + `scripts/ui_harness.py` + `tests/` 2 文件。
> 基线时间: 2026-10-11 16:11

**Refs:** memory-bank/tasks/26-10-11-config-dup-code-fixes.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 dacecf3d→c0038049; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3117 passed + 3 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16565 语句 / 155 未覆盖 / 5712 分支 / 143 partial; 门槛 98% 达标; 本轮 ~53s)
- 增量明细(相对上基线 `26-10-11-0354`, 本轮为修复轮 —— `src/`/`tests/` 真实改动):
  - `src/auto_qb/config/schema/fields.py`(枚举族单点声明 + 语义注释归并 + 死件删除) · `schema/groups.py`(schema_version 默认派生)
  - `src/auto_qb/config/validation/rules.py`(本地常量删除改引派生 + 报错文案派生) · `validation/__init__.py`(重导出挂规范名) · `validation/core.py`(_try_port/_try_time_window 单点) · `validation/sections.py`(常量引 schema + 端口/时间窗调用点归一)
  - `src/auto_qb/config/loaders.py`(_get 统一) · `models.py`(SiteHrCheckConfig 派生五键默认空) · `writer.py`(_atomic_copy)
  - `src/auto_qb/rules/expr/env.py`(STATE_ATTRS 引 schema 单点)
  - `scripts/ui_harness.py`(桩补 listing, 保真) · `tests/test_config.py`(quiet_hours 文案断言同步) · `tests/test_config_schema.py`(守阵 4 条 + 测试计划 docstring)
  - docs/KB: `docs/configuration.md`(log.format + 9 键) · `memory-bank/config-reference/keys.md`(9 键 + adapter 列) · issue ×7 状态流转 + 本切片 + 档案 + activeContext 切片 + 各 `_index.md`(`kb.index` 重建)
- 机检(本轮相关): `kb.index` 重建生成物; `kb.check` 主键纪律 / 认领链闭环 / 回写措辞 / 日期守卫; 新守阵含 docs↔代码漂移守卫(docs 侧首个)。
- 说明: 首跑 test.quick 曾红 1 条 —— 本档案初稿把「等提交指令」写进请求边界, 撞 `check_wording` 判据(回写措辞禁时点相对断言), 改时不变措辞「随本专题入库」后复验全绿; 本条即该坑的当轮实证。
