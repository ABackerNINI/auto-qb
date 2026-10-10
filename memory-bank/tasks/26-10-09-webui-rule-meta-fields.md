# 26-10-09-webui-rule-meta-fields — WEBUI 规则卡「触发与节奏」段(规则级字段图形化)

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Topics:** webui-rule-meta-fields
**Summary:** 用户报「WEBUI 规则设置只能设置条件与动作, 无法设置 interval/cooldown 等其它」—— 规则卡新增「触发与节奏」折叠段, schema.rule_fields 六字段(trigger/interval/execute_once/cooldown/stop_following_rules_if/watch_fields)经 cfgFlatten + hub-field 全量图形化; interval/watch_fields 挂 grey_if(事件触发下灰显仍可清); 桩物化版本章配置打通保存流冒烟(PUT 200 + 落盘形状正确 + 刷新回读)。测试面见 `commands run kb.baseline`。

**Refs:** memory-bank/pitfalls/web-ui/show-if-residual-key.md,memory-bank/pitfalls/testing/harness-save-flow.md,memory-bank/testing/baselines/26-10-09-2219-webui-rule-meta-fields.md

## 原始请求

- 「WEBUI规则设置只能设置条件与动作, 无法设置interval/cooldown等其它」(问题陈述, 按缺陷修复处理)
- 「继续」(推进修复)
- 「按下一步1/2/3/4执行」—— ①桩补版本章打通保存流冒烟 ②test.quick/e2e:fast/test.full ③清端口残留桩 ④按「提交」口径走 ship 流程

## 思考过程与决策

- **取证**: 后端规则级字段 6 个早已存在且 `/api/config/schema` 载荷已含 `rule_fields`(schema_payload), 前端规则卡只渲染了 enabled 开关 + conditions/actions —— 纯前端渲染缺口。
- **渲染方案**: 不新写控件 —— `cfgRuleMetaItems` 取 schema.rule_fields(滤掉 enabled, 卡头已有开关)走既有 `cfgFlatten` + `hub-field` 通用链, 控件/帮助/「?」/条件显隐零特判复用; enum 字段(trigger/execute_once/stop_following_rules_if)克隆标 `required: true` 摘掉「(未配置)」空选项(写出空串后端必拒), 未动过的键不落树保 YAML 简洁。
- **show_if → grey_if(本轮最重要的语义决策)**: watch_fields 原 show_if 在触发时机切走后整行消失但键残留, 保存必败且 UI 无从自救(冒烟第一轮 400 实证); interval 同理需要"非周期触发下不生效"的视觉提示。两者统一改 grey_if —— 灰显仍可清, 清空自动删键。判据入坑档(show-if-residual-key)。
- **桩物化**: 保存流冒烟被 PUT 版本闸门挡住(GET 树缺 schema_version); 桩的运行期配置是内存 FakeConfig、磁盘无文件, 与真机「启动物化必盖章」形态不符。决策 = 桩 boot 期物化带版本章的最小合法配置 + load_config 自校验(模板漂移显式起不来), 而不是在测试里手补版本章(那测不到真闸门); reload_config 在桩上只回执不应用(_apply_truth 只认 pause/resume), FakeConfig 不会被顶掉。判据入坑档(harness-save-flow)。
- **定位**: 刷新回读首版等 `.group-row` 超时 —— 位置持久化会把页面恢复到设置页规则分区, 种子页行根本不渲染; 改等规则卡本体 + 兜底点击导航。

## 实现计划

1. `config_rules.js`: cfgTriggerLabel(中文触发标签单点) / cfgRuleMetaItems / cfgRuleMetaOpen·Toggle / cfgRuleMetaSummary(折叠摘要常显) + cfgRuleSummary 中文化
2. `config_editor.js`: cfg.openRuleMeta 折叠态 + 登出清空
3. `settings.html`: 规则卡头部与「条件/动作」流程之间插入折叠段(复用 hb-blk-hd 条状头)
4. `console_hub.css`: `.hb-rule-meta` 三条规则(摘 hb-blk-hd 底边、段底 hairline 收口、头部 hover)
5. `schema/rules.py`: interval 加 grey_if=("trigger","interval"); watch_fields show_if→grey_if
6. `scripts/ui_harness.py`: _materialize_config + config_path/data_dir 钉到临时目录
7. 验证: 浏览器冒烟全链 → test.quick → e2e:fast → test.full

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 规则级字段图形化(前端 5 文件) | Done |
| schema grey_if 两处(interval/watch_fields) | Done |
| 桩物化版本章 + 保存流冒烟打通 | Done |
| 冒烟脚本(一次性, .openclaw/tmp, 不入库) | Done |
| test.quick / e2e:fast / test.full | Done |
| 知识库回写(档案/切片/基线/坑档×2/web-config-editor) | Done |
| commands 收录 dev.port-kill | Done |

## 进度日志

- **2026-10-09 21:05-21:35**: 取证 + 前端实现(6 文件中 5 个) + test.quick 全绿; 浏览器冒烟第一轮暴露 watch_fields 残留键保存必败 → show_if 改 grey_if; 第二轮暴露桩 PUT 版本闸门 400(恢复轮中断)。
- **2026-10-09 21:58-22:19**: 用户授权四步收口 —— 桩物化版本章 → 冒烟全绿(落盘 spec 正确、刷新回读一致、零 pageerror; 冒烟顺带实证「位置持久化恢复到设置页」与「杀 uv 不死 python 子进程」两个坑) → test.quick / e2e:fast / test.full 全绿 → 知识库回写与收录, 随本专题入库。
