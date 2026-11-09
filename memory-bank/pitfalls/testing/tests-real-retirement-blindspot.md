# tests-real 不在 testpaths: 产品组件退役时 tests-real 侧用例必漏

> 摘要: tests-real 不在 pytest testpaths, 全量全绿不等于 tests-real 可收集; 退役/改签名产品组件时 grep 面必须含 tests-real/, 否则同组件的 tests-real 用例 import 即炸且全量发现不了。
> 触发: 退役, 组件退役, 改签名, 删模块, tests-real, testpaths, 全量全绿, 收集不到, import 失败, finalize_watch, acquire_pid, collect-only, 真机片, 同步退役

**Refs:** memory-bank/tasks/26-11-09-test-rm10-guardian-tests-retire.md

## 坑

`tests-real/` 不在 pytest `testpaths`, `test.full`/`test.quick` 都收集不到它 —— 全量全绿 **≠** tests-real 用例可收集。退役/重构产品组件时, 只按 pytest 收集面清偿测试(如 S4a 66418c7e 同步退役了 `tests/test_finalize_watch.py`)会**漏掉 tests-real 侧引用同一组件的用例**: `tests-real/rm10_notify/test_rm10_notify.py` 模块级 `from auto_qb.infra.relocate_journal import acquire_pid` + 三条 guardian 用例调 `finalize_watch.run`, import 即炸、整文件(含 5 条仍活的通知用例)无法收集, 潜伏至 B09 全仓复扫才被偶然发现(issue 26-11-09-2128, 2026-11-09 清偿)。

## 动作

- **退役/改签名产品组件时, grep 面必须含 `tests-real/`**(不是只看 `tests/`): `grep -rn "<退役符号>" tests-real/ --include="*.py"`, 命中即同批清偿, 不留「下轮再说」。
- **收尾自查用 collect 而非记忆**: `uv run python -m pytest tests-real/<片>/... --collect-only` 能跑通 import 才算清偿完(全量测试不覆盖这条路)。
- 结构性盲区本身仍在(testpaths 未纳 tests-real 是有意为之, 真机片有环境门禁不能进全量), 别「顺手」把 tests-real 加进 testpaths —— 那会把需要真实 qB 的片混进 CI。

## 复发

- (0)
