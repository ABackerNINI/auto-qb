# 3996 passed + 2 skipped —— 前端单点已存在但被绕过 7 族收敛(全部改调既有单点)后全量基线

> 摘要: 前端单点已存在但被绕过 7 族收敛(全部改调既有单点)后全量基线
> 基线时间: 2026-10-22 03:24

**Refs:** memory-bank/tasks/26-10-22-webui-single-point-bypass-dup.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3996 passed, 2 skipped in 116.11s**
- 覆盖率: TOTAL **99%**(过闸)

逐条口径注记:

- 开工首跑曾 1 failed(`test_gen_all_check_is_green`) —— 纯索引漂移: 认领时把 issue 置 In Progress 后未重建 `issues/_index.md`; `commands run kb.index` 后复跑转绿, 非代码问题
- 本轮改动面守阵在 test.full 内全绿: `test_webui_static_dom_page.py`(含 cfg 默认值梯 node 语义电池 —— config_editor.js + config_rules.js 合并求值, 本轮两文件均改) + `test_webui_static_dom_panel.py`(含 `_NODE_API_TIMEOUT_PROBE` —— auth.js 单文件 eval + 合成实例跑 `_request` 六型, Bearer 单点改为同文件顶层函数不破该探针) + `test_webui_static_skins.py` + `test_web_traffic_limit_card.py` + `test_web_traffic_monitor.py` + `test_web_backend_misc.py`
- 真浏览器复验(`commands run dev.e2e -- e2e/views.spec.mjs e2e/multiselect-shows.spec.mjs e2e/hr-history.spec.mjs`): **52 passed**(三皮肤; 设置页刷新保持位置 / 密码框不造脏 / 设置-HR 在线核实 / 工具参数单位控件(S7)保存回传复合串 / 流量与限速合并卡 / 追剧集行三视图)
- 本轮**未新增测试函数**(机械收敛, 既有守阵比对面未变); passed 数与上一基线(3995)的差 = 首跑 1 failed 转绿

## 本改动面

- `src/auto_qb/webui/static/shared/config_editor.js` —— 新增 `cfgTruthy(v)` 真值单点(`cfgBool` 转调); `cfgCurvePointAdd` 内联三元改调 `cfgCurveDirectionKey`; `cfgPathKey`(第二份 path→key 单点)转调 `hubKey`; `_fmtBytes/_fmtSpeed` 改调 `this._fmtLadder`; `cfgUnitOptions` 补禁抄阶梯注释
- `src/auto_qb/webui/static/shared/config_rules.js` —— `cfgSpecBool` 改调 `this.cfgTruthy`; `cfgRuleMetaOpen/Toggle` 两处内联 `join(".")` 改调 `this.hubKey`
- `src/auto_qb/webui/static/shared/config_hub.js` —— `hrSiteEnabled` 与 `hubReadout` hr_check 分支改调 `this.cfgTruthy`; `hubKey` 补禁内联注释
- `src/auto_qb/webui/static/shared/auth.js` —— 新增顶层函数 `aqbAuthHeaders(token)`(Authorization 头单点); `_request` 改调
- `src/auto_qb/webui/static/shared/shortcuts.js` —— 密钥面板 reload/save 两处手拼头改调 `aqbAuthHeaders`
- `src/auto_qb/webui/static/shared/commands.js` —— 导出下载手拼头改调 `aqbAuthHeaders(this.token)`
- `src/auto_qb/webui/static/shared/format.js` —— 新增 `AQB_UNIT_LADDER` 单位梯数据单点 + `_fmtLadder` 参数化消费单点(`fmtSpeed`/`fmtSize` 改调); 新增 `kibToBytes`/`bytesToKib` 换算单点(`fmtLimit` 改调)
- `src/auto_qb/webui/static/shared/drawer.js` —— 限速对话框三处内联乘除 1024 改调 `kibToBytes`/`bytesToKib`
- `src/auto_qb/webui/static/shared/hr.js` —— 新增 `hrEpTitle(e)`(ep 行 HR 徽标 title 单点, 保留既有短文案)
- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html` —— ep 行 HR title 四层三元改调 `$root.hrEpTitle(e)`
- 未授权不做: commit/push
