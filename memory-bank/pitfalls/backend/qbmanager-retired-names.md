# qbmanager 命名与别名冻结

> 摘要: QbManager 上抽新方法/加新属性时, 命名会撞**别名冻结守阵**(`tests/test_qbmanager_alias_freeze.py`)——退役旧名(分诊清单 `26-10-01-0350-plan-web-state-alias-disposal.triage.json` 里 category=forward 的成员与 alias_layer.fields)禁止在 QbManager 上复活, 守阵红验报「退役旧名在 QbManager 上复活」。这**不是守阵误报**, 是命名撞车: 换一个名字即可, 不要去改分诊清单或删守阵。
> 等级: L0
> 触发: qbmanager, 抽方法, 抽私有方法, 重构命名, _load_state, 退役名, alias_freeze, 复活, 分诊清单, QbManager 新方法

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md,memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json

### 抽方法撞退役名: `_load_state` 实例(2026-10-11, R8 实施轮)

按 issue `26-10-11-0207-refactor-core-conn-state-boilerplate-dup` 给 QbManager 抽
「state 加载 + bind_field_snapshots」私有方法, issue 建议名就叫 `_load_state` ——
但这个名字**曾**是别名层 W2 时代的转发成员(`_load_state -> ctx.state.load()`, 分诊
清单 category=forward), W3 删除别名层后守阵钉死「退役名禁复活」, `test.quick` 红验:

```
AssertionError: 退役旧名在 QbManager 上复活: ['_load_state'] —— 兼容层已随 W3 删除…
```

**触发**: 给 QbManager 抽新方法/新增成员命名(重构/收敛样板时最常见)。

**判别**: `test.quick` 红验 `test_retired_names_stay_gone`, 报「退役旧名在 QbManager 上
复活: [...]」即命中 —— 守阵扫 QbManager 的方法/属性定义名集合(`_scan_qbmanager`)与
退役名单(分诊清单 `members[category==forward]` ∪ `alias_layer.fields`)求交。名单里
还有一批 `_web_*` / `_*_view` 形态的退役字段名, 新增成员前先查清单或跑一次该守阵,
别等红验。

**处置**: **换名**即可(`_load_state` → `_reload_state`), 并同步受影响的**接线守阵**
(`test_rule_engine.py::test_state_migration_materialize_is_wired_in_run` 原找字面
`self.ctx.state.load()`, 改找 `self._reload_state()` —— 意图「物化在加载后」不变)。
错误处置 = 改分诊清单/删守阵/改名后绕过: 分诊清单是退役契约的事实源(守阵 docstring
明言「退役名单以清单为基准, 缺了先补清单」), 为新方法腾名字不在其职。
