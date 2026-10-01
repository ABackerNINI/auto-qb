# 基线 · 1909 passed + 3 skipped / 91% —— 审计 L1-L3 清扫(死 shim 删除 + 私有名公开化)

> 摘要: 内核化重构审计报告(reports/26-10-01-0918)§09 建议 4 的三项机械清扫落地, **零行为变更,
> 纯命名面**:
> **L1** `RulesModule._load_rules` → 公开方法 `load_rules`(内核 `run()` 调用点 qbmanager.py
> 不再触模块私有面; rules_mod 定义与 rebuild_runtime 内部调用 / store.py docstring /
> conventions/modules.md W3 记述 / tests 8 文件 11 处调用同步改名)。
> **L2** 删 `core/mixins/__init__.py`(15 行过渡 shim, 全库无人 import —— qbmanager 自 P2 起
> 直接 import `webui.views`/`webui.commands`)+ `src/auto_qb/mixins/` 空目录残留(仅 __pycache__,
> 未跟踪); 包 docstring 三处回写(auto_qb/__init__ core 行 / core/__init__ 删 mixins 条目 /
> qbmanager 类头「mixins 包」→「表现层 mixin」)。
> **L3** webui 私有名经宿主回环公开化: `WebviewMixin._state_kind` → `state_kind` /
> `_build_search_index` → `build_search_index`(views.py 定义 + 4 内部调用点; commands.py
> `_cmd_build_search_index` 处理器体内的调用; runtime.py:326/:488 两处 `self._host.*` 回环;
> atlas·console 两皮肤 components.css 注释; tests/test_web.py 全部调用与 docstring)。
> 命令处理器 `_cmd_build_search_index` 与测试函数名(test_build_search_index_* 等)按审计
> 口径保留不动。
> 基线时间: 2026-10-01 18:35, develop @ a03c3a8d(未提交工作树, 含 L1-L3 清扫改动)。

TOTAL **1909 passed + 3 skipped / 91%**(13278 语句 / 1048 未覆盖 / 4408 分支 / 434 partial,
test.full 23.64s, rc=0)—— 通过数与 M3 基线 26-10-01-1813 **持平**(纯改名零新例零删例);
语句 13281 → 13278(-3, 死 shim 退役)。改前 test.quick 预跑 1909+3 / 21.43s 同绿。
合流 0b422396(1728 文档修复 S1+S2, 纯 memory-bank 文档, stash→sync→pop, overview.md
双方不同段共存)后复核 test.full 1909+3 / 91% / 27.32s 同绿, 数字不变。

## 本段改动面

- 改名(L1): core/modules/rules_mod.py / core/qbmanager.py / torrents/store.py(docstring)/
  conventions/modules.md; tests: helpers / test_modules_p5 / test_checking / test_trigger_events /
  test_rule_engine / test_ops / test_rules_core。
- 删除(L2): src/auto_qb/core/mixins/(git rm __init__.py + 清 __pycache__)/ src/auto_qb/mixins/
  (未跟踪残留); 回写 auto_qb/__init__.py / core/__init__.py / qbmanager.py 类头 docstring。
- 改名(L3): webui/views.py / webui/commands.py / webui/runtime.py / static/atlas 与 console
  两 components.css(注释)/ tests/test_web.py。
- 文档: memory-bank/modules/overview.md 迁移映射表 mixins 行改为「过渡包已删」记实。
- 未动(范围外, 已知漂移顺带观察到): qbmanager.py:398 注释仍指旧路径 `mixins/web_commands.py`
  (P2 迁走前旧物)/ rules/actions 两 docstring 指 `core/mixins/ops.py`(P4 迁走前旧物)/
  memory-bank/modules/mixins.md 整篇描述已退役的 mixins 文件 —— 均属 26-10-01-1728 文档漂移
  修复计划辖区, 未顺手改。

**Refs:** memory-bank/reports/26-10-01-0918-report-kernel-module-refactor-audit.html
