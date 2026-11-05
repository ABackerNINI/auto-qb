# 4398 —— 规则引擎重设计 W3 组合树+choose 收尾(choose 编排块 + webui 结构树编辑器)

> 摘要: 规则引擎重设计 W3 组合树+choose 收尾(choose 编排块 + webui 结构树编辑器)
> 基线时间: 2026-11-01 06:30
**Refs:** memory-bank/plans/26-11-01-0106-plan-rule-engine-redesign.html

## 验收数字

`commands run test.full` (168.2s, 2026-11-01 实测):

```text
TOTAL                                                22222    188   7622    149    99%
4398 passed, 10 skipped in 165.75s (0:02:45)
```

- 口径见 [baseline.md](../baseline.md)。

W3 期基线(plan 26-11-01-0106): 组合树(W3-A)收口 + choose 编排块(W3-B, D3 转正) + webui 条件组合树/choose 编辑器(D2/D8) + 生产 5 条规则快照零差异(金标准不回退)。skipped 与上条切片同环境口径(node/平台性跳过)。

## 本改动面

- `src/auto_qb/config/compat.py`: `CHOOSE_KNOWN_KEYS`/`CHOOSE_BRANCH_KEYS` 键面单点 + `normalize_choose_block`(choose 结构归一: when 过 normalize_conditions 建树、then/default 逐项过 normalize_action_entry 注入缺省 on_error、异形原样透传交校验器) + `normalize_action_list` + `normalize_action_entry` choose 分流(编排块键面保留, 不翻 {type, params} 形); 幂等保持。
- `src/auto_qb/config/validation/rules.py`: `_validate_choose_block`(块级/分支键面、缺 when/缺 then、choose 非列表、空分支列表、then/default 非 list、嵌套 choose 拒绝、when 条件树同款校验含 expr 门控, 坐标报 choose[i].when / choose[i].then[j]); `_validate_action_entry` 加 gate/allow_choose 参数(嵌套拦截); `_validate_trigger_action_compat` 扩 choose 块内 then/default 白名单(on_torrent_deleted)。
- `src/auto_qb/rules/base.py`: `ChooseBranch`/`ChooseBlock` 运行时形态 + `_build_action_steps`/`_build_choose_block`(构造期建执行步; choose 内嵌 choose 构造期兜底 ConfigError); `Rule.steps` 执行步列表(choose 与普通动作同占一步, 无 choose 的规则 steps 与 actions 1:1, 断点语义不变); `process` 重构 —— `_dispatch_result`(on_error 三档分派 + 日志单点, choose 内外共用) + `_pick_choose_branch`(首命中短路/无命中走 default/无命中无 default=no_op/when 求值异常按顶层条件异常同语义 error 收场); choose 内 retry 断点挂块首(整块重新求值重新分派)、pending 挂块后(块内不细粒度续跑); `record_execution` 判据 steps 化。
- `src/auto_qb/webui/static/shared/config_rules.js`: 草稿规范化单点 `cfgNormalizeRulesDraft`/`cfgNormalizeActionEntryDraft`(JS 镜像后端 normalize, 与后端幂等同构; W2-B 混合形写侧升级为全规范形写侧); 条件组合树方法族 cfgCond*(读侧/建树/组合键切换/删除向上收敛/排序/叶子计数/UI 深度软上限 8); choose 方法族 cfgChoose*/cfgActionEntry*At/cfgListEntryRemove/cfgThen*/cfgDefault*; on_error 路径版 cfgOnError*At(choose 块内动作项, 与顶层同口径); `cfgPluginAdd` 改写规范形; `cfgSpecItemsAt` 路径版本体(cfgSpecItems 转调); 组件定义 `AQ_COND_NODE_COMPONENT`(递归)/`AQ_CHOOSE_BLOCK_COMPONENT`。
- `src/auto_qb/webui/static/shared/config_editor.js`: `cfgSetTree` 挂草稿规范化(D2: 打开即归一形、保存即写新形态; 归一在基线快照前, 打开不误报脏)。
- `src/auto_qb/webui/static/shared/tpl/rule-tree.html`(新): `tpl-aq-cond-node` 递归模板 + `tpl-aq-choose-block`; `tpl/settings.html`: 条件区换组合树编辑器(旧扁平条件写入路径退役)、动作区 choose 分支卡 + 「添加分支(choose)」按钮; `app.js` 注册两组件; 三皮肤 index.html 清单挂 rule-tree.html; `console_hub.css` 补 .hb-cond-*/.hb-branch-*/.hb-add-row 版式(三皮肤共用层单点); `config_hub.js` hubPluginText 补 choose 行话(meta 判空之前)。
- 测试: `test_rule_compat.py` +10(choose 归一形态/校验认/fail-fast 矩阵/when 深度复用上限/引擎分支分派与短路/when 异常 error 收场/on_error 三档分派/嵌套构造拒绝/删除触发白名单; docstring 测试计划同步), `test_rule_base.py`(测试注动作步换 steps 口径), `test_actions.py`(同), `test_modules_p5.py`(换桩助手), `test_config_key_surface.py`(键面派生补 choose 键), `test_webui_static_dom_page.py` +1(规则树+choose 编辑器守阵: 单点/接线/三清单/17 项 node 语义电池; docstring 同步)。
- 样例与文档: `test_yamls/test_actions/test_choose.yml`(choose 样例, 载入链实测通过); `memory-bank/rule-system/conditions-and-actions.md` 新增「choose 编排块」节 + hr 条件行按现行为修正(无 HR 可判定显式分支, W3-A 报告计划外发现); `memory-bank/config-reference/keys.md` 规则集段补 choose 键面; `tests/fixtures/config_key_surface.txt` 重生成(+4: choose/default/when/then)。
- 键面核对: `commands run test.keys-update` 实跑(186 -> 190 键, 纯新增非破坏, config 版本不抬)。
