"""test_import_all 测试计划: import-all + 注解强制求值守卫

## 测试计划(每个测试函数一条)
- test_all_modules_import: pkgutil 枚举 auto_qb 全部子模块逐一 import, 任何导入期错误都 fail,
  消息带模块名 + 原始异常(兜住 ≤3.13 上注解在 def 期即求值的 NameError)。
- test_all_annotations_resolve: 递归遍历每个模块的函数/类(含类内方法与嵌套类),
  用 inspect.get_annotations(eval_str=True) 强制求值全部注解 —— Python 3.14 起 PEP 649
  让注解默认惰性求值, 「注解引用了未导入的 typing 名字」(如 Dict)在导入期不再报错,
  只有显式求值才能跨解释器版本抓住该类 bug。背景: 该错误已复发两次。
  豁免: 名字在所在模块 `if TYPE_CHECKING:` 块内导入的(仅类型标注, 运行期不存在), 不算失败。
"""
import ast
import importlib
import inspect
import pkgutil
import re

import auto_qb

_NAME_RE = re.compile(r"name '(\w+)'")


def _type_checking_names(module) -> set:
    """用 ast 从模块源码收集 `if TYPE_CHECKING:` 块内导入的名字(仅类型标注用途)。"""
    try:
        tree = ast.parse(inspect.getsource(module))
    except (OSError, TypeError):
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            for stmt in node.body:
                for alias in getattr(stmt, "names", []):
                    names.add(alias.asname or alias.name.split(".")[0])
    return names


def _iter_annotated(module, seen):
    """深度优先产出 (可求值注解的对象, 归属路径): 模块自身 + 模块级/类级函数与类。"""
    yield module, module.__name__
    seen.add(id(module))
    stack = [(v, f"{module.__name__}.{getattr(v, '__qualname__', '?')}") for v in vars(module).values()]
    while stack:
        obj, owner = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        is_func = inspect.isfunction(obj)
        is_class = isinstance(obj, type)
        if not (is_func or is_class):
            continue
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        yield obj, owner
        if is_class:
            stack.extend((v, f"{owner}.{getattr(v, '__qualname__', '?')}") for v in vars(obj).values())


def _eval_failures(obj, owner, tc_names):
    try:
        inspect.get_annotations(obj, eval_str=True)
    except NameError as e:
        missing = _NAME_RE.search(str(e))
        if not (missing and missing.group(1) in tc_names):
            return [f"{owner}: NameError: {e}"]
    except Exception as e:  # noqa: BLE001 —— 求值期其它异常同样意味着注解在运行期解析会炸
        return [f"{owner}: {type(e).__name__}: {e}"]
    return []


def _walk_module_names():
    mods = [m.name for m in pkgutil.walk_packages(auto_qb.__path__, prefix="auto_qb.") if not m.ispkg]
    assert mods, "walk_packages 未枚举到任何子模块, 守卫失效"
    return mods


def test_all_modules_import():
    mods = _walk_module_names()
    failures = []
    for name in mods:
        try:
            importlib.import_module(name)
        except Exception as e:  # noqa: BLE001 —— 守卫的职责就是兜住一切导入期异常再聚合报告
            failures.append(f"{name}: {type(e).__name__}: {e}")
    assert not failures, f"{len(failures)}/{len(mods)} 个模块导入失败:\n" + "\n".join(failures)


def test_all_annotations_resolve():
    mods = _walk_module_names()
    failures = []
    for name in mods:
        module = importlib.import_module(name)
        tc_names = _type_checking_names(module)
        for obj, owner in _iter_annotated(module, set()):
            failures.extend(_eval_failures(obj, owner, tc_names))
    assert not failures, f"{len(failures)} 处注解无法解析:\n" + "\n".join(failures)
