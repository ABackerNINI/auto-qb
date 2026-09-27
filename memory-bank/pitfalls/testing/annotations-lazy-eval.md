# 注解惰性求值让「typing 名字没导入」在导入期隐身

> 摘要: Python 3.14 起 PEP 649 让注解默认惰性求值 —— 模块级注解引用未导入的 typing 名字(如 Dict)在导入期**不报错**, 只在 ≤3.13 的解释器上炸; import-all 守卫必须显式 `inspect.get_annotations(obj, eval_str=True)` 强制求值才能跨版本抓住, 且守卫对已注入的 bug 还可能**假绿灯**(守卫写完必须红验)。
> 触发: Dict, typing, 注解, NameError, import 报错, 3.14, PEP 649, 惰性求值, import-all, 守卫, 假绿灯, 红验

### 同一 bug 在不同 clone 上一边炸一边静默 (2026-09-27)

- **触发**: `config/loaders.py` 的 `_resolve_hr_site_bindings` 用了 `Dict[str, TrackerConfig]`
  但顶部只导入 `List, Optional` —— 该类缺陷已复发两次(都是改函数签名加注解时漏导入)。
- **判别**: 报错 clone (`D:\Projects\auto-qb`) 跑 ≤3.13, 注解在 def 期即求值 → 导入期
  `NameError: name 'Dict' is not defined`; 本 clone uv 环境是 **3.14**, PEP 649 惰性求值 →
  `import auto_qb` **照样 OK**, bug 完全隐身。同一份代码两个 clone 一边炸一边静默,
  只看本 clone 测试绿灯会得出「没问题」的错误结论。
- **处置**: `tests/test_import_all.py` 双守卫 —— ①import-all 兜导入期错误; ②递归遍历
  每个模块的函数/类/方法, `inspect.get_annotations(eval_str=True)` 强制求值全部注解;
  名字在所在模块 `if TYPE_CHECKING:` 块内导入的豁免(ast 解析收集, 现有 store.py /
  taskqueue.py 两处)。**守卫写完必须红验**: 首版只有 import-all, 把 bug 重新注入后守卫
  仍 1 passed(3.14 上导入不炸)—— 红验才暴露守卫自身无效, 补强制求值后同 bug 精确报出
  `loaders._resolve_hr_site_bindings: NameError`。
- **复发**: 1 —— 2026-09-27 首版守卫假绿灯: 只做 import-all 没强制求值注解, 注入 bug 后
  仍全绿。**为什么没命中: 不是踩已有坑, 是守卫自身的设计缺口被红验揪出** —— 教训
  归入 [assertions.md](assertions.md) 的「红验」纪律: 守卫类测试必须先证明它能红, 再信它的绿。
