"""test_import_all 测试计划: import-all + 注解强制求值守卫

## 测试计划(每个测试函数一条)
- test_all_modules_import: pkgutil 枚举 auto_qb 全部子模块逐一 import, 任何导入期错误都 fail,
  消息带模块名 + 原始异常(兜住 ≤3.13 上注解在 def 期即求值的 NameError)。
- test_all_annotations_resolve: 递归遍历每个模块的函数/类(含类内方法与嵌套类),
  用 inspect.get_annotations(eval_str=True) 强制求值全部注解 —— Python 3.14 起 PEP 649
  让注解默认惰性求值, 「注解引用了未导入的 typing 名字」(如 Dict)在导入期不再报错,
  只有显式求值才能跨解释器版本抓住该类 bug。背景: 该错误已复发两次。
  豁免: 名字在所在模块 `if TYPE_CHECKING:` 块内导入的(仅类型标注, 运行期不存在), 不算失败。
- test_no_undeclared_global_names: 静态检查每个模块的函数体里引用的名字能否解析到
  (自有绑定 / 外层作用域 / 模块全局 / 内建) —— 关掉「**未导入的名字只在真机走到那一行才炸**」
  这一类。背景: 该错误已复发三次(`LANE_SATISFIED` 崩整波、`CHANNEL_OK` 卡死视图发布、
  `List` 潜伏在写命令路由), import-all 与注解求值两道守卫都拦不住 —— 函数体只有在**被调用**时才求值。
"""
import ast
import builtins
import importlib
import inspect
import pkgutil
import re

import auto_qb

_NAME_RE = re.compile(r"name '(\w+)'")
_BUILTINS = set(dir(builtins))


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


# ---------- 函数体里的名字解析(2026-09-29: 同一类缺陷第三次复发后补) ----------


def _take_target(target, names: set) -> None:
    """赋值目标名(含解包/星号形态)"""
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            _take_target(element, names)
    elif isinstance(target, ast.Starred):
        _take_target(target.value, names)


def _arg_names(args: ast.arguments) -> set:
    names = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    return names


def _bound_names(body) -> set:
    """一段语句体内的绑定名(含嵌套块的导入/赋值/def/class/for/with/except/推导式/walrus)

    刻意**过宽**: 嵌套函数体内的局部名也算外层已绑定 —— 宁可少报也不假报(守卫的职责是
    抳「模块常量名漏导入」这类硬崩, 不是抠作用域细节)。
    """
    names: set = set()
    for stmt in body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for alias in stmt.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(stmt.name)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                _take_target(target, names)
        elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            _take_target(stmt.target, names)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            _take_target(stmt.target, names)
            names |= _bound_names(stmt.body) | _bound_names(stmt.orelse)
        elif isinstance(stmt, ast.While):
            names |= _bound_names(stmt.body) | _bound_names(stmt.orelse)
        elif isinstance(stmt, ast.If):
            names |= _bound_names(stmt.body) | _bound_names(stmt.orelse)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars is not None:
                    _take_target(item.optional_vars, names)
            names |= _bound_names(stmt.body)
        elif isinstance(stmt, ast.Try):
            names |= _bound_names(stmt.body) | _bound_names(stmt.orelse) | _bound_names(stmt.finalbody)
            for handler in stmt.handlers:
                if handler.name:
                    names.add(handler.name)
                names |= _bound_names(handler.body)
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                names |= _bound_names(case.body)
    for node in ast.walk(ast.Module(body=list(body), type_ignores=[])):
        if isinstance(node, ast.comprehension):
            _take_target(node.target, names)
        elif isinstance(node, ast.NamedExpr):
            _take_target(node.target, names)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
    return names


class _NameResolver(ast.NodeVisitor):
    """逐作用域检查函数体里的**名字引用**: 解析不到即记一条(名字 + 行号 + 归属)"""
    def __init__(self, module_names: set) -> None:
        self.module_names = module_names
        self.scopes = [set()]
        self.owner: list = []
        self.problems: list = []

    # ---------- 作用域 ----------
    def _visit_function(self, node) -> None:
        # 装饰器与默认值在外层作用域求值 —— 先在当前栈上走一遍
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in [*node.args.defaults, *[d for d in node.args.kw_defaults if d is not None]]:
            self.visit(default)
        self.scopes.append(_arg_names(node.args) | _bound_names(node.body))
        self.owner.append(node.name)
        for stmt in node.body:
            self.visit(stmt)
        self.owner.pop()
        self.scopes.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Lambda(self, node) -> None:
        for default in [*node.args.defaults, *[d for d in node.args.kw_defaults if d is not None]]:
            self.visit(default)
        self.scopes.append(_arg_names(node.args) | _bound_names([ast.Expr(node.body)]))
        self.owner.append("<lambda>")
        self.visit(node.body)
        self.owner.pop()
        self.scopes.pop()

    def visit_ClassDef(self, node) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in [*node.bases, *[k.value for k in node.keywords]]:
            self.visit(base)
        self.scopes.append(_bound_names(node.body))
        self.owner.append(node.name)
        for stmt in node.body:
            self.visit(stmt)
        self.owner.pop()
        self.scopes.pop()

    # ---------- 引用 ----------
    def visit_Name(self, node) -> None:
        if not isinstance(node.ctx, ast.Load):
            return
        if any(node.id in scope for scope in reversed(self.scopes)):
            return
        if node.id in self.module_names or node.id in _BUILTINS:
            return
        self.problems.append(f"{'.'.join(self.owner) or '<module>'} 第 {node.lineno} 行: {node.id}")


def _undeclared_names(module) -> list:
    """模块内函数体引用了、但**既非局部也非模块全局也非内建**的名字"""
    try:
        tree = ast.parse(inspect.getsource(module))
    except (OSError, TypeError):
        return []
    module_names = set(vars(module)) | _bound_names(tree.body)
    resolver = _NameResolver(module_names)
    for stmt in tree.body:
        resolver.visit(stmt)
    return resolver.problems


def test_no_undeclared_global_names():
    mods = _walk_module_names()
    failures = []
    for name in mods:
        module = importlib.import_module(name)
        for problem in _undeclared_names(module):
            failures.append(f"{name}: {problem}")
    assert not failures, f"{len(failures)} 处名字解析不到(漏导入 / 拼错):\n" + "\n".join(failures)
