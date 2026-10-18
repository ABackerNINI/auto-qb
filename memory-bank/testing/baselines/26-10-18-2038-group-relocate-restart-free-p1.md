# 3639 passed + 2 skipped(根), 98% 覆盖 —— 免重启整组迁移 P1 配置面落地后全量基线

> 摘要: 免重启整组迁移 P1 配置面落地后全量基线
> 基线时间: 2026-10-18 20:38
**Refs:** memory-bank/plans/26-10-18-1604-plan-group-relocate-restart-free.html

## 验收数字

`commands run test.full` 实测(2026-10-18 20:36, 启动前已 `my-commit-flow.sync` 同步到 d7fc97ae):

```
TOTAL    18902    287    6330    202    98%
3639 passed, 2 skipped in 118.99s (0:01:58)
```

逐条口径: 总数 3639(通过); 2 skipped(既有 skip, 与本改动无关); 覆盖率 98%(fail-under=98 达标)。上一条基线为 P0(26-10-18 19:40, slug group-relocate-restart-free-p0), 相对差值看 `commands run kb.baseline -n 2`, 本切片不手抄。

## 本改动面

P1 配置面(计划 26-10-18-1604 §04 P1)落地, 均为纯增键面(非破坏, 未抬 schema 版本):

- `src/auto_qb/config/models.py`: 新增 `RelocateConfig`(9 键, 默认全保守关) + `Config.relocate` 字段
- `src/auto_qb/config/loaders.py`: 新增 `load_relocate_config` 并在 `load_config` 接线
- `src/auto_qb/config/validation/sections.py`: 新增 `KNOWN_RELOCATE_KEYS`(9 键) 与 `_validate_relocate`; `validation/core.py` 顶层键登记 + 调用; `validation/__init__.py` 重导出
- `src/auto_qb/config/schema/fields.py`: `RELOCATE_VERIFY_MODES` 取值域单点; `schema/groups.py`「自动化」组新增 relocate 段(含管理员运行提示)
- `src/auto_qb/core/modules/relocate_mod.py`(新): `RelocateModule` 段认领桩(sections=("relocate",), apply 短路, P1 无引擎); `qbmanager.py` 装配清单末尾注册
- 测试: 新 `tests/test_relocate_config.py`(13 例); `test_config_schema.py` 参数面补 relocate; `test_config_key_surface.py` 探针表补 9 键; `test_module_host.py` 模块序守阵补 relocate; `test_web_views_reload.py` `_pin_noop_sections` 钉 relocate 段; `tests/helpers.py` `FakeConfig` 补 relocate
- 基线: `tests/fixtures/config_key_surface.txt` 重生成(170 -> 180 键, v5 不变)
- 文档: `docs/configuration.md` 新增「整组迁移(relocate)」节 + 完整示例; `memory-bank/config-reference/keys.md`  relocate 段
