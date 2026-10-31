# 基线 · 1894 passed + 3 skipped / 91% —— 别名层处置 W1(路由与 src 侧改新名)

> 摘要: plan plans/26-10-01-0350 **W1 全量实施(只改名/删转发调用, 零行为变更)**。分诊清单
> 标 W1 的 15 个名字的 src 消费方全部改新名口:
> ①**webui 路由域**: auth.py 2 处 `manager._web_token` → `manager.web.token`; context.py
> getattr 字符串暗消费方 `getattr(mgr, "_web_write_seq", 0)` → `manager.web.write_seq`(直取,
> 替身与真身都有该属性, 不再需要 getattr 兜底); system.py `_web_results` → `web.results`;
> state.py/torrent_detail.py `_group_view`/`_traffic_view` → `web.group_view`/`web.traffic_view`
> (5 处); `ensure_group_state`/`ensure_group_view` → `web.ensure_state`/`web.ensure_view`;
> `touch_web_client` → `web.touch` ×26(events/fs/hr/sites/state/system/torrent_detail 七文件)。
> ②**_hr_view_fields 公开化**(范围外注记的处置): WebviewMixin 静态方法 `_hr_view_fields`
> 改名 `hr_view_fields`(路由直调它, 私有下划线名不成立), views.py 内部 4 处 + record.py
> 注释 2 处 + test_web.py 15 处同步; 不搬 hr 口 —— 搬移是行为面重排, 超出 W1 只改名边界。
> ③**rules 动作三域**: checking.py 组上下文 4 处(manager._group_*) → `host.get("grouping")._*`
> (W2 施工图口径); base.py record_execution/get_exec_record → `manager.ctx.state.*`;
> checking_meta.py 冷却 helper 宿主参数由鸭子类型(manager/OpsModule 双形态)收敛为
> **StateService**(`.data` 读写 + `.save()` 落盘) —— ops_mod.py 3 处传 `self._ctx.state`,
> full_checking.py 1 处传 `manager.ctx.state`, 测试 3 处直传 `mgr.ctx.state`。
> ④**注释与静态文件旧名字样清零**(grep 验收面): webui/module.py、runtime.py、lifecycle.py、
> context.py 注释与 static 四文件(app.js/decorate.js/hr.js/components.css)的 `qbmanager._*`
> 提法改指 WebviewMixin/新名口。⑤**test_web 假替身接线**(SimpleNamespace 无别名层, 必须
> 同波): `_make_web_manager` 数据接线到 `mgr.web.*`(group_view/traffic_view/ensure_view/
> ensure_state 覆盖 + hr_view_fields), web_env 双写 token(`web.token` 是 routes 读点, 旧名
> 留 W2 测试面迁移); 替身测试体 3 处预置/失效模拟改 `web.results`/`web.traffic_view`/
> `web.write_seq`。真 manager 测试经别名层转发零改动(W2 范围)。
> 基线时间: 2026-10-01 05:45, develop @ f7c79058 + 本轮 W1 改动。

TOTAL **1894 passed + 3 skipped / 91%**(13316 语句 / 1058 未覆盖 / 4412 分支 / 437 partial,
test.full 35.6s, rc=0)—— 与上基线 26-10-01-0443-W0(1894+3 / 91%)持平: 本波只改调用方名字,
零新增测试; 语句 +2(checking.py 两处 grouping 局部变量)、未覆盖 +1, 覆盖率不变。
验收: `grep -rn "manager\._" src/auto_qb/webui/` 为空; 冻结守阵 test_qbmanager_alias_freeze
4 例绿(qbmanager.py 本体未动, 兼容层随 W3 才删)。

## 本波改动面(26 文件, +116/-122)

- src 路由域: webui/server/auth.py、context.py、routes/{state,system,torrent_detail,events,fs,hr,sites}.py。
- src 其他域: webui/{module,runtime,views}.py、webui/server/lifecycle.py、torrents/record.py(注释)、
  rules/{base,checking_meta}.py、rules/actions/{checking,full_checking}.py、core/modules/ops_mod.py。
- static 注释: shared/{app,decorate,hr}.js、atlas/css/components.css。
- 测试: test_web.py(替身接线 + hr_view_fields 同步)、test_checking.py、test_ops.py(冷却 helper 宿主)。
- 文档: 基线切片(本文件)/ 任务档案 W1 收档 / 计划状态行 / activeContext 切片 / conventions/modules.md 注记。

## W2/W3 边界注记

- webui/server/__init__.py:5 docstring 仍提 `manager.web_commands`(W2 名单 web_commands 的
  docstring 提及, 非调用点, 留 W2); core 注释里 2 处历史提法(manager._suppress_events /
  _notify_handler)非别名层成员, 不属本计划。
- 替身与测试体遗留的旧名属性(mgr._web_token 双写镜像等)按 D2 留 W2 测试面迁移批次。
