# 6059 passed + 2 skipped(根) —— src/ 钉码与指路清零两批入库基线

> 摘要: src/ 钉码与指路清零两批入库基线
> 基线时间: 2026-11-12 01:35
**Refs:** memory-bank/tasks/26-11-12-backend-stale-ref-utf8-pin.md

## 验收数字

```text
TOTAL                                                27073     65   9460     68    99%
6059 passed, 2 skipped in 213.72s (0:03:33)
```

(实测时点: 两批评审零 actionable 后收尾 `commands run test.full` 2026-11-12; 2 skipped 为存量 skip; 本切片为本批组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- 批1(771f262d, 指路清零+注释口径, 7 文件): `scripts/update_config_key_surface.py`(docstring+print 指路改指 schema/validate_config 与键面快照)、`docs/configuration.md` x2 处、`docs/hr-online-verify-docs.md` x1 处、`src/auto_qb/webui/static/shared/state.js` 与 `config_editor_curve.js`(注释死链删链保留事实)、`src/auto_qb/infra/bt_backup_probe.py` 与 `src/auto_qb/core/modules/relocate_plan.py`(qB 5.x 存储类型注释补线值字符串枚举, 零行为改动)。
- 批2(807ad38d, src/ 文本子进程钉死 UTF-8 + 守卫扩面, 5 文件): `src/auto_qb/infra/port_owner.py`:108、`src/auto_qb/core/traffic_source/agent.py`(_run_foreground)、`src/auto_qb/tools/recycle_daemon.py`(tasklist/ps 两处)、`src/auto_qb/rules/actions/checking.py`:263(守卫扩面实扫出的第 5 处)—— 统一 `encoding="utf-8", errors="replace"`; `tests/test_platform_tolerance_guards.py`(守卫扫描面纳入 src/)。
- 零生产行为改动: 5 处钉码判定路径只用 rc 或恒 ASCII 匹配目标; 注释/docstring/文案级改动不涉运行语义。
