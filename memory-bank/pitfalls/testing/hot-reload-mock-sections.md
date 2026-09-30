# 热重载守阵的 MagicMock 配置会让新模块把 Mock 段误判成「段变」而真启服务器/真重挂

> 摘要: apply_new_config 的守阵惯用 `mock.MagicMock()` 当新配置(替身区只钉住自己关心的段)。内核化
> 重构后每次热重载会对全部模块无条件广播 apply, 模块靠「新旧配置段整段相等」短路 —— Mock 段是新
> 取的属性对象, 永远不等于旧段, 于是新挂的模块会走「段变」分支: webui 会**真启 uvicorn 服务器**
> (host/port 是 Mock), logging/notify 会真重挂。P1(钉 logging/notify 段)与 P2(补钉 web 段)连续两
> 轮命中; P3-P5 每新增一个带段短路判据的模块都要复查现有 MagicMock 配置测试是否补钉。
> 触发: 改 apply_new_config / 新增模块 apply / 热重载守阵, 见到 MagicMock 配置 + 新模块段短路判据

- **触发**: 给 apply_new_config 写或改守阵时用 `MagicMock()` 当新配置; 或内核化重构 P3-P5 每段往
  host.apply_all 挂入新模块(带 sections 认领 + 段相等短路)时。
- **判别**: 测试红在「服务器真启动 / setup 被多调」而不是断言失败文本本身; 或全量跑挂起(uvicorn
  真绑定端口)。反向核对: 该测试的替身区是否只钉了**旧**模块关心的段(logging/notify), 而本轮新挂
  模块关心的段(web/hr_check/trackers...)没钉。
- **处置**: 替身区把新模块消费的段**钉成现行配置的同一段对象**(`new_cfg.web = mgr.config.web`),
  并在注释里写明「防 Mock 段被误判段变」。判据用段对象同一性最稳 —— 不要试图让 MagicMock 支持
  相等比较。守阵本体的模块侧段短路/身份对比判据另有单测(test_core_modules / test_facade_modules),
  热重载守阵只钉"分级分支"语义, 两层不要混。
- **守阵**: test_web.test_apply_new_config_levels / test_apply_new_config_l2_preserves_runtime_state
  的替身区钉段注释; tests/test_facade_modules.py 头部说明。
- **复发**: 2(2026-09-30 P1 logging/notify、P2 web/hr 各一次; P1 未立档是本条漏记主因 —— 当时只
  在档案与测试注释里记了, 没进 pitfalls)。
