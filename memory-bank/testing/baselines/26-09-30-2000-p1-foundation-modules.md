# 基线 · 1850 passed + 3 skipped / 91% —— 内核化重构 P1 (基建模块化: logging/notify + 托盘改口)

> 摘要: plan plans/26-09-30-1819 P1 全量实施 —— LoggingModule/NotifyModule 立契约样板(sections 认领
> + apply 整段短路), 新建 core/modules 包(3 文件 140 行); qbmanager 装配清单挂入基建两模块, run()
> 启动接线改 host.start_all, 热重载 L1 的手工重挂两段(logging/notify)改 host.apply 无条件广播
> (hot-reload W1+W2 子集, 影子并行: L1 分支暂留 qb 重连+web 重启待 P2 迁出); 托盘 4 处
> manager._notify_handler 直写改 ctx.notify 公开方法(app.py:405/426/456/460), 私有字段访问清零。
> 守阵: tests/test_core_modules.py 7 例(段变才重挂/无关保存零动作 P1 指定守阵在内); test_module_host
> 装配断言改 ["logging","notify"]; test_web 热重载两守阵改写(L1 断言重连+web 重启, 模块段相等零动作)。
> 基线时间: 2026-09-30 20:00, develop @ 01e47169 + 本轮改动。

TOTAL **1850 passed + 3 skipped / 91%**(13076 语句 / 1052 未覆盖 / 4382 分支 / 430 partial,
test.full 26.44s, rc=0) —— 较上基线 26-09-30-1912(1843 passed + 3 skipped / 91%)增 7:
本轮 +7(tests/test_core_modules.py: logging start 幂等 1 / logging apply 短路+重挂 1 / notify
start 语义 1 / notify apply 重挂 1 / 托盘 API 契约 1 / apply_new_config 改 notify 段才重挂+无关
保存零动作 1 / 托盘与内核源码私有面清零 1)。

## 本轮改动面

- 新建 core/modules 包(3 文件 140 行): `__init__.py`(13, 包 docstring + 导出)、logging_mod.py(48
  —— LoggingModule: start 幂等闸(构造期接线与 run 的 start_all 双入口合流)/apply 段相等短路/段变
  重挂)、notify_mod.py(79 —— NotifyModule: ctx 构造期注入(托盘会话开关早于 run 的 start)/start
  dry-run 判定/apply 先摘旧再 force=True 重挂(原 L1 语义)/托盘公开口 enabled_state/is_enabled/
  set_enabled)。
- module.py 288→291: AppContext 挂 notify 模块句柄(托盘等外围经 ctx 调模块公开方法, plan §3.2);
  P0「零模块」表述随事实更新。
- qbmanager.py 1058→1060: 构造期装配清单(plan §3.3 顺序前缀 logging→notify, P2+ 清单注释入档);
  _setup_logging 方法删除(改经 host.get("logging").start); _notify_handler 私有字段删除;
  run() 的 setup_notify 行改 host.start_all(dry_run); apply_new_config 捕获整份旧配置传
  host.apply_all(old, config) 无条件广播, L1 分支只剩重连+web 重启。
- tray/app.py 4 处直写改公开口: _refresh_status 状态同步读 enabled_state()/ _notify_on 读
  is_enabled 语义 / _toggle_notify 会话挂载与翻转走 set_enabled; setup_notify import 随之移除。
- 测试: 新建 tests/test_core_modules.py(7 例, 头部测试计划同步); test_module_host.py 装配断言
  (零模块 → ["logging","notify"] + ctx.notify is host.get("notify")); test_web.py 两守阵改写
  (test_apply_new_config_levels: L1 断言改重连+web 重启+模块零动作, 替身区钉 logging/notify 段
  对象; test_apply_new_config_l2_preserves_runtime_state: 同款钉段避免 Mock 段被误判段变)。
- 无新配置键、无新线程、无 state_file schema 变更; 行为变化仅限计划内: 无关保存不再重挂
  logging/notify(过度重启族在 notify/logging 域的消除), 其余语义原样。

## 文档与制品

- tasks/26-09-30-backend-kernel-module-refactor.md: P1 → Done + 进度日志。
- plans/26-09-30-1819: 拍板记录与 colophon 更新(P0-P1 已实施)。
- activeContext/kernel-module-refactor 切片滚动更新。
