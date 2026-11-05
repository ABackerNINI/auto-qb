# 4420 —— 规则引擎重设计 W5 单一 registry 收口

> 摘要: 规则引擎重设计 W5 单一 registry 收口
> 基线时间: 2026-11-01 07:52
**Refs:** memory-bank/plans/26-11-01-0106-plan-rule-engine-redesign.html

## 验收数字

`commands run test.full` (169.3s, 2026-11-01 实测):

```text
TOTAL                                                22394    200   7672    156    99%
4420 passed, 10 skipped in 166.72s (0:02:46)
```

- 口径见 [baseline.md](../baseline.md)。

W5 期基线(plan 26-11-01-0106): 单一 registry 收口(W1-W5 全序列终验)。skipped 与上条切片同环境口径(node/平台性跳过)。

## 本改动面

- `src/auto_qb/rules/registry.py`: W5 收口主体 —— 条件/动作/choose 编排块统一注册表, 条目 = 三元组(执行函数 + schema 声明 + 文档片段) + `validator`/`watchable_field`(G10)/`deleted_ok`(G11) 声明; 导入方向 R6(a): schema 声明留在 config.schema, 条目按名引用(schema_ref) + 延迟访问器(plugin/doc_text)躲 rules->config 导入环, 本模块顶层零项目内依赖; G13 拍板未用条目全部保留(内置 25 插件走按名引用, 声明零复制)。
- `src/auto_qb/config/validation/rules.py` / `config/schema/fields.py`: 深度校验器分发(`_plugin_spec_validators()` 按 registry 条目 validator 声明派生, 对照冻结手写基准 `_PLUGIN_SPEC_VALIDATORS_BASELINE`)、触发器 x 动作兼容表(`deleted_ok` 派生白名单 == `DELETED_ALLOWED_ACTIONS`)、watch_fields 取值域(`watchable_field` 派生 == `FIELD_WATCH_ALLOWED`)三处派生收口(G9 表述修正后的实际收口面)。
- 测试: `tests/test_registry_derived.py`(新, 9 例: 深度校验器分发双跑 / validator 声明可解析 / 兼容表与 watch_fields 双跑 / 派生序 / schema 引用解析 / choose 入册 / 文档片段一致性 / 演示测试 test_demo_new_action_one_place「新增哑动作只改 1 处」); 全序列终验 `commands run test.full` 4420 passed 10 skipped(见本片验收数字), W5 验收 5 条(演示测试/双跑 diff 清零/config_key_surface 守卫/文档片段一致/test_config 规则段)全部核对通过。
