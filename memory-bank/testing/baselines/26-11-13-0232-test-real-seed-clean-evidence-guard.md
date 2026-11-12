# 6084 passed + 2 skipped(根) —— real.seed.clean 证据保护闸批次

> 摘要: real.seed.clean 证据保护闸批次
> 基线时间: 2026-11-13 02:32
**Refs:** memory-bank/tasks/26-11-13-test-real-seed-clean-evidence-guard.md

## 验收数字

```text
TOTAL                                                27113     65   9480     69    99%
6084 passed, 2 skipped in 189.35s (0:03:09)
```

(实测时点: 修复循环轮2增量落(_allowed 严格包含 + 第 4 条守阵)后收尾 `commands run test.full` 2026-11-13; 2 skipped 为存量 skip; 较上一切片 26-11-13-0027 的 6063+2 增 21 = 本批守阵 4 条 + 远端并行入库用例; 本切片为本专题组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- **`tests-real/seed.py`**: `cmd_clean` 增证据保护闸 —— 默认整扫与 `--dir` 指 `.work` 本体时, 顶层凡不是 `seeds/`/`rmNN` 的内容 rc=1 拒跑(dry-run 同拒、删除零发生), 逃生门 = `--dir` 显式指名逐处清; 新增 `WORK_ROOT`/`CLEAN_KNOWN_WORK`/`_work_strays`; `_allowed` 裸前缀匹配改按路径分量严格包含(评审轮1发现, 兄弟目录 `.work-20261112` 不再误收); 模块 docstring 安全边界与 clean --help 同步。
- **`tests/test_real_machine_safety.py`**: 新增 seed clean 节守阵 4 条(未知顶层拒跑 / 认得的名字契约不变 / --dir 逃生门不波及证据 / 兄弟目录拒收), 隔离加载 seed.py 且落点全改指 tmp(真实 .work 本身是被保护对象); 头部「测试计划」清单同步。
- **口径回写四处**: `.commands/real/config.toml`(real.seed.clean when/note)、`memory-bank/pitfalls/ops/seed-clean-vs-evidence.md`(处置行: 闸已落地, rmNN 内与 --dir 指名面仍靠人工)、`memory-bank/testing/real-machine.md`(§2.5 收尾行)、`tests-real/tools/daemon_window_wrapper.py`(「clean 可清」过时措辞, 评审轮1)。
- **记账/issue 面**: issue 26-11-12-2345 翻 In Progress → Done(修复后补充落 §03 含评审轮2修正与最终验证数字); 任务档案 26-11-13-test-real-seed-clean-evidence-guard 立档; 事故档案 26-11-11-webui-group-hash-ref.md 回填面补闭环行。
