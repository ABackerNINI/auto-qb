# 注解惰性求值让「typing 名字没导入」在导入期隐身

> 摘要: Python 3.14 起 PEP 649 让注解默认惰性求值 —— 模块级注解引用未导入的 typing 名字(如 Dict)在导入期**不报错**, 只在 ≤3.13 的解释器上炸; import-all 守卫必须显式 `inspect.get_annotations(obj, eval_str=True)` 强制求值才能跨版本抓住, 且守卫对已注入的 bug 还可能**假绿灯**(守卫写完必须红验)。
> 触发: Dict, typing, 注解, NameError, import 报错, 3.14, PEP 649, 惰性求值, import-all, 守卫, 假绿灯, 红验, TYPE_CHECKING, 前向引用, 引号, 字符串注解, 循环导入, mypy, 补注解

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

### 形态二: 项目内前向引用类名未加引号, 急切求值解释器上 def 期 NameError (2026-11-06)

- **触发**: 给模块补签名注解时, 被注解的类与当前模块存在**循环导入** —— 只能 `if TYPE_CHECKING:`
  导入(运行期不导入), 此时注解里直接写类名(不带引号): `def apply(self, old: Config, ...)`.
  本仓实撞(2026-11-06, mypy 接入计划 S3 core 批次): `core/modules/tracker_mod.py` 与
  `speed_curve_mod.py` 各 1 处, 注解 `Config` 只在 TYPE_CHECKING 块内导入, def 期急切求值
  → `NameError: name 'Config' is not defined`。注意 venv 是 3.13(≤3.13 急切求值), 不是 3.14。
- **判别**: 导入该模块即 NameError, 名字指向**项目内自己的类**(不是 typing 名); 该名字在
  `if TYPE_CHECKING:` 块里或本该在那儿(运行期导入会循环)。与形态一的区别: 形态一是
  「typing 模块名忘了导入」(导入即可修), 本形态是「名字**故意**不在运行期命名空间」
  (导入会循环) —— 修法不是补导入, 是**注解加引号**。
- **处置**: 注解写成字符串前向引用 `def apply(self, old: "Config", new: "Config") -> ApplyResult:`,
  类引用保留在 `if TYPE_CHECKING:` 块; mypy 静态检查与运行期求值两不误。批量补注解时,
  每引入一个 TYPE_CHECKING 导入就同步把引用它的注解全部加引号, 别只加导入不加引号。
- **复发**: 1(2026-11-06 首记)。**为什么没命中**: 读了原坑档, 但它的主形态是「typing 名字
  没导入」(3.14 惰性求值隐身), 触发词与判别都不覆盖「项目类前向引用未引号」这个新形态
  —— 原文只说「引用未导入的 typing 名」, 被误读为"只要不是 typing 名就不沾"; 实则同一
  求值机制管所有注解。
