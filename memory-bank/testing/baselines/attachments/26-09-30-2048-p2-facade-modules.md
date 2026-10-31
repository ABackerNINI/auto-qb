# 基线 · 1860 passed + 3 skipped / 91% —— 内核化重构 P2 (门面转正: webui/hr 实现 Module 契约)

> 摘要: plan plans/26-09-30-1819 P2 全量实施 —— WebUIRuntime/HrRuntime 经 WebUIModule(webui/module.py)
> / HrModule(hr/module.py) 接入 Module 契约(sections 认领 + start/stop + apply + loop hooks), 装配清单
> 挂入四模块; run() 的 web 启动块/hr.start/finally 停止序列退役, 启停全走 host.start_all/stop_all;
> _apply_web_config 并入 webui.apply(有差异即置脏 + 仅监听身份变化才重启), hr.apply 每次热重载必过
> 的语义随 HrModule 保留; 主循环 self.web.* 语义调用改 loop hooks(flush_truths 次序语义留内核);
> store.hr_link 注入移进装配; start_web_server 不再写 manager._web_token(令牌生命周期内聚门面)。
> 守阵: tests/test_facade_modules.py 9 例; test_module_host 装配断言改四模块; test_web 两守阵改经
> WebUIModule.apply 驱动 + MagicMock 配置钉 web 段; web stop+wait 竞态 / hr 从无到有三件套 / 别名
> 代理层既有守阵全绿。
> 基线时间: 2026-09-30 20:48, develop @ 9c68cce9 + 本轮改动。

TOTAL **1860 passed + 3 skipped / 91%**(13125 语句 / 1051 未覆盖 / 4386 分支 / 427 partial,
test.full 20.86s, rc=0) —— 较上基线 26-09-30-1953(1851 passed + 3 skipped / 90%, 含 keymouse
方案 B 守阵)增 9: 本轮 +9(tests/test_facade_modules.py: webui start 语义 1 / stop 只请求退出 1 /
apply 有差异即置脏 1 / 仅监听身份变化才重启 1 / loop hooks 次序 1 / hr 模块契约 1 / run 接线
守阵 1 / 装配与判定桥 1 / start_server 先密钥后服务 1)。

## 本轮改动面

- 新建 webui/module.py(106 行, WebUIModule): start(dry-run/未启用无操作 + handle 幂等闸)/
  stop(只 handle.stop() 不等线程, 原 finally 口径)/apply(mark_dirty 有差异即置脏 + want/have
  监听身份对比: 相等则 ensure_token, 不等则 stop_web_server 先停旧等退出再启新或停净)/
  loop hooks(on_command_line = consume_commands+check_pending 返回 changed; on_sync_line =
  flush_views; on_task_line = advance_error_reasons -> flush_views -> advance_search_index)。
  门面对象经 manager.web 现取(测试整体替换 mgr.web/mgr.hr 时模块自动跟随)。
- 新建 hr/module.py(41 行, HrModule): start 的 dry-run 门/stop 透传/apply 透传 old.hr_check
  (短路/重建判据单点仍在 HrRuntime.apply, 每次热重载必过的语义由无条件广播承担); sections
  认领 ("hr_check", "trackers")(站点绑定派生自 trackers.X.hr_check, 只认 hr_check 会漏)。
- WebUIRuntime 604→637(+33): ensure_token(令牌确定并落 self.token, 内聚门面)/start_server
  (先密钥后 start_web_server, 启动与热重载重启共用)/stop_server(只置退出位不等线程)。
- server/lifecycle.py: start_web_server 删除 `manager._web_token = ensure_web_token(manager)`
  直写(plan §05「外围绕过边界直写内核私有面」清零; auth.py 经别名读 token 不变, D4 处置)。
- qbmanager.py 1060→1023: 装配清单挂入 WebUIModule/HrModule(webui→hr, store.hr_link = self.hr
  注入移进装配块); run() web 启动块/hr.start/finally 手工停止序列删除, 改 host.start_all(dry_run)
  /host.stop_all()(逆序 hr→webui→notify→logging); 主循环命令线改 host.run_command_line(),
  _sync_line 尾改 host.run_sync_line(force), _task_line 收尾改 host.run_task_line(force);
  apply_new_config 删 mark_dirty 手工行/old_web/old_hr_check 捕获/L1 分支 web 重启/hr.apply 手工调,
  L1 分支只剩 qb 重连; _apply_web_config 方法删除(669-692)。
- 测试: 新建 tests/test_facade_modules.py(9 例, 头部测试计划同步); test_module_host.py 装配断言
  (["logging","notify"] → ["logging","notify","webui","hr"]); test_web.py 四处 —— 两守阵改经
  mgr.host.get("webui").apply(old, new) 驱动并改名 test_webui_module_apply_*, 两处 MagicMock 配置
  补钉 new_cfg.web = mgr.config.web(防 Mock 监听身份被误判段变而真启服务器), 头部测试计划与
  test_apply_new_config_levels 文案同步 P2 口径。
- 无新配置键、无新线程、无 state_file schema 变更; 行为变化仅限计划内: ①advance_error_reasons
  自任务执行前移至任务线收尾 hook 内(预取变更经置脏同轮可见, 无顺序钉点); ②token 同步时机自
  「L1 且监听身份未变」扩展为「每次热重载且监听身份未变且在跑」(ensure_web_token 幂等, 无副作用);
  ③零差异保存不再置脏视图(原每次 apply_new_config 无条件 mark_dirty)。关停顺序 web 先于 hr 变为
  hr 先于 web(装配逆序, 资源独立无依赖)。

## 文档与制品

- tasks/26-09-30-backend-kernel-module-refactor.md: P2 → Done + 进度日志。
- plans/26-09-30-1819: 拍板记录更新(P0-P2 已实施)。
- activeContext/kernel-module-refactor 新切片(26-09-30-2048)。
