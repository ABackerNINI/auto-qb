# 4916 passed + 10 skipped(根) —— state 读侧 encoding 守阵(issue 26-10-31-0458)结清后全量

> 摘要: state 读侧 encoding 守阵(issue 26-10-31-0458)结清后全量
> 基线时间: 2026-11-03 04:27
**Refs:** memory-bank/issues/26-10-31-0458-bug-state-read-encoding-guard.html, memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮 encoding 守阵与知识库回写的工作树。
- `commands run test.full` 实测(wrapper 墙时 191.6s, 2026-11-03 采样, Windows 本机):
  - 汇总行: `4916 passed, 10 skipped, 3 warnings in 188.74s (0:03:08)`
  - TOTAL 表: `TOTAL  22543  152  7736  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- **定向**: `commands run test.one -- tests/test_rule_engine.py` 单文件全绿(含新增守阵); 新增用例单独跑绿。
- **红验(区分力实证)**: 读侧 `encoding="utf-8"` 改成 `None`、以及整体删掉该形参, 两种形态下新增用例均红; 复原后 `git diff -- src/` 为空(本轮零 src 改动)。
- **环境注记**: 本机同期有其它 clone 的 pytest 进程在跑(多 clone 并行), 本轮零失败、零偶发红。

## 本改动面

- 生产代码: 零改动 —— issue 的「修」是把守阵立起来(`core/state.py` 读侧本就显式 utf-8)。
- 守阵: `tests/test_rule_engine.py` 新增 `test_read_state_file_pins_utf8_encoding` —— `builtins.open` 探针把读侧 `encoding` 实参钉成 `"utf-8"`, 覆盖主文件与 `.bak` 两条读取; 中文内容往返与原样返回作正向对照。文件头部「## 测试计划」同步追加条目。
- 选型: 未走 issue 建议的源码文本守阵(那需要在 mutants 侧挂 `--deselect`); 探针式行为守阵全平台可观测且无需 deselect, 与 `tests/test_exporter.py` 既有 encoding 守阵同法。
- 知识库回写: 本基线切片 + issue(状态 Done + 状态日志 + 修复后补充 + doc-refs 反向链) + 任务档案 `26-10-08-test-mutation-audit.md` 进度行。
- `config.yml` / `auto-qb-data/` 红线未触碰; 未跨仓库; 未扩池。
