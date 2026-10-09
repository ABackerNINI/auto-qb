# webui 规则卡「触发与节奏」段(规则级字段图形化)

> 摘要: 用户报「WEBUI 规则设置只能设置条件与动作, 无法设置 interval/cooldown 等其它」→ 规则卡新增折叠段, schema.rule_fields 六字段(trigger/interval/execute_once/cooldown/stop_following_rules_if/watch_fields)全量图形化, interval/watch_fields 挂 grey_if; 桩物化版本章配置打通保存流冒烟(PUT 落盘形状正确 + 刷新回读一致); 顺手修掉 show_if 残留键保存必败的陷阱(坑档单点)。全绿, 随本专题入库。
> 最后活动: 2026-10-09 22:19

**Refs:** memory-bank/tasks/26-10-09-webui-rule-meta-fields.md

- 已完成: 前端 5 文件(config_rules.js 方法族 / config_editor.js 折叠态 / settings.html 折叠段 / console_hub.css / schema rules.py grey_if×2) + 桩 _materialize_config; 冒烟/quick/e2e:fast/full 全绿(实测数字见 `commands run kb.baseline`)。
- 判据单点: 坑档 `pitfalls/web-ui/show-if-residual-key.md`(show_if 残留键陷阱) + `pitfalls/testing/harness-save-flow.md`(桩保存流/版本章/杀桩)。
- 正在进行: 无。
