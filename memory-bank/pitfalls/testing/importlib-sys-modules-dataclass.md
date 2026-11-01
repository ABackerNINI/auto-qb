# importlib 就地加载 future-annotations dataclass 模块, 不先注册 sys.modules 会在 3.13 上炸 NoneType

> 摘要: importlib 就地加载 future-annotations dataclass 模块, 不先注册 sys.modules 会在 3.13 上炸 NoneType
> 触发: importlib, spec_from_file_location, exec_module, sys.modules, dataclass, NoneType, 3.13, 就地加载, 守阵加载引擎, find_skill_dir
**Refs:** memory-bank/tasks/26-11-01-test-commit-gate.md

### 守阵用 importlib 就地加载引擎配置模块, 不先注册 sys.modules → 3.13 dataclass 注解求值期炸 NoneType

- **触发**: 想复用引擎单点(如 `.agents/skills/commands/scripts/_config.py` 的 `find_skill_dir`)时, 用 `importlib.util.spec_from_file_location` + `module_from_spec` 就地加载, 没把模块注册进 `sys.modules` 就直接 `exec_module`; 被加载模块带 `from __future__ import annotations` + `@dataclass`(cpython 3.13.15 实测)。
- **判别**: `exec_module` 期直接炸 `AttributeError: 'NoneType' object has no attribute '__dict__'`, 栈在 `dataclasses._is_type` 的 `sys.modules.get(cls.__module__).__dict__` —— 被加载模块本身没毛病, 是假名不在 `sys.modules` 导致 dataclass 解 KW_ONLY 哨兵注解时拿不到模块命名空间; 同份代码经正常 import 或注册后加载则完全正常。
- **处置**: `exec_module` 前先 `sys.modules[spec.name] = module` 再 exec(importlib 官方配方); 或改走正常 import, 但 `_config` 这类泛名进 `sys.path` 有撞名风险, 不推荐。实例: `.commands/doc/scripts/test_doc_pkg.py` / `.commands/kb/scripts/test_kb_pkg.py` 的 `_ENGINE` 加载块。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
