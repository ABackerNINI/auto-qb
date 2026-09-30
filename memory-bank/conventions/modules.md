# 功能模块契约与扩展约定(plan kernel-module-refactor)

> 摘要: core/modules 十功能模块的统一契约(name/sections/start/stop/apply/subscribe)、装配清单、热重载语义(整段短路 + 未认领段兜底)、刷新相位表、ctx 服务面与模块协作纪律 —— 新增/修改功能模块前先读这份单点。
> 触发: 模块契约, 新增模块, sections 认领, 段认领, 热重载, 相位, 刷新管线, EventBus, ModuleHost, 微内核, 插件, AppContext, ctx 服务, loop hooks

## 三层结构(谁是内核、谁是服务、谁是模块)

| 层 | 载体 | 判据 |
|---|---|---|
| 内核 | `core/qbmanager.py` | 只知「何时」(节拍/相位/生命周期): 主循环三时间线、连接管理、落盘计时、ModuleHost 编排。**零业务 import**(AST 守阵) |
| 能力服务 | `ctx.store / api / state` 等 | 无启用开关、无线程、无热重载语义、被多方消费的纯能力; 内核与模块共同消费 |
| 功能模块 | `core/modules/` 十模块 | 有启用开关、可能持线程/服务器/队列任务、有配置认领与热重载语义的自治单元 |

模块清单与装配序: logging → notify → webui → hr → tracker → speed_curve → maintenance → grouping → ops → **rules 最后**(它消费前面所有人的服务)。

## Module 契约(单点: `core/module.py`)

- `name` + 五动词: `sections()` / `start(ctx, dry_run)` / `stop()` / `apply(old, new)` / `subscribe(phases)`。
- **start/stop 必须幂等**(黄金法则 1); stop 先叫停后 join(pitfalls/backend/concurrency.md 第 1 条)。
- **apply 每次热重载无条件被调**, 相关配置段整段相等才短路返回 —— 「统一挂载口」语义; 级别分派表已退役, 段变动作是模块自判知识, 不许再建中央表。
- 可选 loop hooks: `on_command_line() -> bool` / `on_sync_line(force)` / `on_task_line(force)` —— 基类刻意不定义; 用 getattr 探测, 有则被宿主按装配序调用, 无则跳过。
- dry_run 全量透传给 `start`; 模块自判「只观察不落盘」口径。

## 配置段认领(P6 守阵, 红线级约定)

- **新增配置顶层段必须落到三者之一**: 某模块 `sections()` 认领 / `impact.KERNEL_SECTIONS`(内核现读: main_tick/sync_interval/max_tasks_per_tick/state_save_interval/qbittorrent) / `impact.RESTART_SECTIONS`(R 级重启闸)。漏登 ⇒ `tests/test_modules_p6.py` 守阵红表。
- **未认领段变更**: 运行期落 WARN + `rebuild_runtime` 相位全量重建兜底(保守性可解释, hot-reload-simplify 拍板决策 3)—— 兜底只防认领面漂移, 不是漏登的借口。
- 认领语义 = 「我消费这个段」, 不等于「段变我要重挂什么」; 载入期合并进 tracker 的段(hr/remove_similar_tags)认领后仍可无重挂动作。
- 宿主并集口: `ModuleHost.claimed_sections()`(schema 端点与内核兜底都从它派生, 段认领单一真相在模块, 不落表)。

## 刷新相位表(plan §4.2, 顺序守阵锁定)

内核 `_refresh_torrents` = 同步 + 相位广播, 顺序是历史调用次序的忠实编码: `full_round → transitions → events_removed → events_added → torrents_added(逐种子) → removed_scan → post`; 非刷新类相位: `queue_rebuilt`(L2 队列重建后全局任务重入队)/ `rebuild_runtime`(未认领段兜底重建)。同相位内消费序 = 装配序; **改相位顺序必须是有意行为**(守阵会红, 意图变更要同步 plan/守阵)。

## 模块协作纪律

- **模块之间不互相 import**。需要别人的能力: ①对方是服务 → 经 ctx 现取; ②对方是模块 → 把它需要的公开方法经 ctx 句柄暴露(既有先例: `ctx.notify` 托盘口 / `ctx.trackers.match` / `ctx.maintenance.add_tags` / `ctx.ops.recheck`)。
- client 永远**现取** `ctx.api.client`(重连换客户端随 QbApi.bind 同步链), 不缓存引用。
- 门面模块(webui/hr)经 manager 现取门面对象, 不缓存(测试整对象替换 mgr.web/mgr.hr 时模块自动跟随)。
- Rule/RuleContext 的宿主面仍是 QbManager(rules 动作消费 manager.store/state/ctx.ops); 换宿主面是 rules 动作层的独立改动面。

## 守阵地图

| 文件 | 锁什么 |
|---|---|
| `tests/test_module_host.py` | 契约编排: 注册序/fail-fast/生命周期序/loop hooks/ctx 同对象 |
| `tests/test_core_modules.py` / `test_facade_modules.py` | logging/notify 与 webui/hr 的段变才动 + 段不变短路 |
| `tests/test_modules_p3.py` ~ `p5.py` | 各模块装配本体、相位订阅面、刷新相位顺序、L2 短路/重建 |
| `tests/test_modules_p6.py` | **段认领完备**(配置全段有主 + 认领面无幽灵段)与未认领兜底 WARN/重建 |

## 兼容层现状(决策点 D4, 处置另立计划)

manager 上的旧名单行委托(§7.2)与 `_WEB_STATE_ALIAS`(19 字段 + `__getattr__`/`__setattr__` 转发)是迁移过渡层: 被测试/路由点名的旧名在实现迁模块后留单行转发。**新代码一律用新名**(模块方法 / `self.web.*` / ctx 服务), 不要再往委托层加东西; 处置计划见 memory-bank/plans/(别名层清理, 2026-10-01 立计划)。
