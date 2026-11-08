# mypy 对重复调用 d.get(k) 的 isinstance 收窄失效: 类型残留 None

> 摘要: mypy 对重复调用 d.get(k) 的 isinstance 收窄失效: 类型残留 None
> 触发: mypy, typecheck, union-attr, arg-type, isinstance, 收窄, 重复调用, dict.get

## 本篇只回答

本篇只回答: 写「容器形状守卫」时, 为什么 `x = d.get(k) if isinstance(d.get(k), dict) else {}` 会让 mypy 报 union-attr / arg-type, 以及怎么零行为变化地修。allowlist 配置自身的坑见 mypy-config-cwd.md。

### 同一个 d.get(k) 在条件与取值分支各写一次, isinstance 收窄只作用于条件那一次

- **触发**: 从 JSON / 裸 dict 读嵌套容器并要求坏形状回空时, 顺手写 `x = d.get(k) if isinstance(d.get(k), dict) else {}`(常见于 from_json 形状守卫、journal.rewrites 读取)。这些模块若不在 [tool.mypy] per-module 豁免清单里, 跑 `commands run dev.typecheck` 就会报出来; 已被豁免的模块则静默藏着, 只在豁免收紧后集中暴露。
- **判别**: 报错形如 `Item "None" of "Any | dict[Any, Any] | None" has no attribute "items"` / `"get"`(union-attr), 或把该变量传给 `Dict[str, dict]` 形参时报 `Argument 2 ... has incompatible type "Any | dict[Any, Any] | None"; expected "dict[str, dict[Any, Any]]"`(arg-type)。关键信号 = 报错类型里同时有 `dict` 和 `None`, 而源码明明写了 isinstance 守卫 —— mypy 只收窄 `isinstance` 里那一次调用的表达式, 三元取值分支是**第二次独立调用**, 收窄不传导。
- **处置**: 先取一次到局部变量再收窄 —— `raw = d.get(k)` → `x = raw if isinstance(raw, dict) else {}`。运行时语义逐字等价(少一次纯函数 get), 容器坏形状回空 dict 的契约不变, mypy 把 x 收窄成 dict。别用 `cast` 掩盖, 也别为此往 pyproject 加 disable_error_code —— 守阵 tests/test_mypy_allowlist_guard.py 冻结豁免只减不增, 新增豁免当场判红, 且递减才是主轴。同族债: 字典字面量被推断成 `dict[str, float]` 后又要写 str 值, 用显式 `Dict[str, object]` 注解解。
