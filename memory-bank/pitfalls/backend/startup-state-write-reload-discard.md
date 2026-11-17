# 启动期 state 写点被 reload 整体替换丢弃

> 摘要: `QbManager.run()` 的启动序列里, `_reload_state()` 把 `ctx.state.data` 从磁盘**整体替换**(非合并)。模块启动期(`host.start_all` 阶段)写 state 的突变 —— 迁移器盖章/启动对账回写/prune 滚出这类「接管面」—— 若发生在 reload 之前会被那次替换静默丢弃, 周期刷盘随后把磁盘旧版原样写回; 症状是「启动期写入看似已持久, 盘面却停在旧账, 直到首个运行期写点才收敛」。修法 = 加载/物化/落盘起点整体挪到 `start_all` **之前**(issue 26-11-17-0214); reload 只依赖磁盘与 `ctx.store`(构造期已有), 与 qB 连接无关, 「必须在 connect 之后」从来不是真约束。
> 触发: 启动期, start_all, 模块 start, 写 state, reload, _reload_state, 整体替换, 丢弃, 落盘, model_version, 盖章, 对账, prune, 启动序列, 摆位

**Refs:** memory-bank/issues/26-11-17-0214-question-qbmanager-startup-reload-state-discard.html,memory-bank/tasks/26-11-15-backend-relocate-refactor.md,memory-bank/tasks/26-11-18-backend-qbmanager-startup-reload-discard.md

### 启动期写点被 reload 整体替换丢弃(2026-11-17 真机实证, 2026-11-18 内核修复)

**触发**: 模块在 `start()`/接管路径写 `ctx.state.data`(迁移章/对账/清理类尤甚), 或排查
「启动期写入看似已持久、盘面却停在旧账, 运行期再写一次才收敛」。

**判别**: 重启后盘面没有启动期写的键, 但运行期再写一次就有了 -> 启动期写点被 reload
丢弃。排除面: 周期刷盘缺漏(刷盘正常工作, 写的是被替换后的旧版)、字段绑定失联(bind
由 `_reload_state` 重挂, 不是这条)、并发/丢锁(全程持锁、单一写线程)。病理摆位史: 模块化
前的平铺版 `run()` 里 state 加载紧贴主循环开跑前(connect 之后), 当时两者之间无写点,
摆位无害; 模块化把 `host.start_all` 插到连接循环**之前**后, 「启动期写点 -> reload 整体
替换」的丢弃窗口悄悄形成 —— 真机实证(relocate, 写穿规避前): prune 滚出后三次周期刷盘
仍写滚出前旧账 27 条、`relocate.model_version` 永不落盘。

**处置**: 已落地(issue 26-11-17-0214, 2026-11-18 用户拍板方向 A)。内核面: `run()` 内
`self._reload_state()` + `ctx.state.materialize_migration(dry_run)` + `next_flush_at`
起点整体挪到 `self.host.start_all(dry_run)` 之前(try 内; 物化紧随加载判据不变;
`start_all` 失败路径不回滚物化 —— 迁移/恢复写回幂等, 下次启动重放同链)。守阵:
`tests/test_qbmanager_w6.py` 两条 —— `test_w6_reload_precedes_start_all_wiring`(顺序
接线) + `test_w6_startup_state_write_survives_run`(行为: 桩 start_all 写 state, run()
优雅退出后盘面必须带该写点; 红验在回归摆位下两条全红)。过渡形态留档: relocate 接管面
写穿(`relocate_mod.py` `_load_jobs` 尾部 `ctx.state.save()`)曾是规避手段, 内核修复后
**保留**为「接管即持久」语义面(启动期突变丢失窗口压到零, 不依赖周期刷盘) —— 注释已改口,
别再把它当 bug 规避读。

### 新模块接入: 启动期写 state 的动作面(2026-11-18 沉淀)

**触发**: 新模块的 `start()`/接管路径需要写 `ctx.state.data` 并依赖落盘(修复后加载已在
start_all 之前, 写点合法, 但有两件事容易做错)。

**判别**: 两种错误形态: (1) 派生容器(field_snapshots 类)自己 `setdefault` 后另存引用 ——
整体替换语义下旧引用即孤儿(「换对象不等于下游自动跟进」, `hot-reload-stale-bindings-derived-views`
同族); (2) 启动期突变按「丢失可接受」处理, 实际是迁移章/对账这类丢失不可接受面。

**处置**: (1) 需要 bind 的派生容器必须经 `StateService.bind_*` 单点(与 `_reload_state`
的重挂口径一致); (2) 启动期突变若属「丢失不可接受」面, 参照 relocate 先例在收敛完成后
显式 `ctx.state.save()` 一次(接管即持久); 一般突变交给周期刷盘即可(黄金法则 3 的窗口
语义)。
