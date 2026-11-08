# 相位 handler 的 mock 失效 (EventBus 注册期绑定)

> 摘要: `mock.patch.object(模块实例, "_on_xxx")` 拦不住 EventBus 已注册的相位 handler —— 注册期捕获的是绑定方法对象, patch 换的是实例属性, 总线里的引用不变; 守相位接线用「订阅计数 + emit 返回值」, 守行为直调真 handler。
> 触发: EventBus, 相位, subscribe, mock.patch.object, handler 断言, assert_called_once, P5 守阵

### patch 实例属性后 emit 仍走旧 handler (kernel-module-refactor P4 踩到)

- **触发**: 想用 `with mock.patch.object(mgr.host.get("grouping"), "_on_transitions") as h: mgr.events.emit("transitions", ...)` 断言「相位广播恰好触达一次」—— emit 正常返回但 handler 0 次调用。
- **判别**: `ModuleHost.register` 在装配点回调 `module.subscribe(events)`, `phases.on(phase, handler)` 存进总线的是**当时的绑定方法对象**; `patch.object` 替换的是实例属性 `_on_transitions`, 二者是两个对象 —— 总线快照 `tuple(self._handlers[...])` 派发的永远是注册期那份。
- **处置**: 守**接线**(谁订阅了什么)用 `len(mgr.events._handlers[phase]) == 1` + `emit(...) == 1`(返回值即触达订阅者数); 守**行为**直接 emit 真数据断言副作用, 或 `patch.object` 总线里那个 handler 对象本身。见 tests/test_modules_p4.py::test_grouping_phases_wired 的两种写法。
- **守阵**: tests/test_modules_p4.py::test_grouping_phases_wired(订阅计数 + emit 返回值)。
