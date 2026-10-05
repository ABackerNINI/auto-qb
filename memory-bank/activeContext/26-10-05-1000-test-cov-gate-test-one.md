# test.one 内置 --no-cov 修覆盖率闸假红 — issue 26-10-05-0922 认领完成 (Done)

> 摘要: 认领 issue 26-10-05-0922 (chore 便签档) —— `pytest.ini` addopts 的 `--cov-fail-under=98` 是对**全量收集面**设的闸, 单文件/筛选跑 (`test.one`) 收集面小 ⇒ 用例全绿仍以覆盖率 FAIL 退出 (假红, 实测 `11 passed` 同屏 `Total coverage: 18.52%`), 排障须手工 `--no-cov`。所有者指派「认领并修复」, 拍板方向①: `.commands/test/config.toml` 的 test.one run 串尾部加 `--no-cov` —— 与既有 test.quick/test.pkg 同款, `pytest.ini` 的闸门原样保留给 test.full 与 CI 全量跑 (零回归面, 改动只 1 处 task 定义)。修复后同命令 `11 passed in 1.50s` 无 FAIL (免覆盖率插桩, 4.42s→1.50s)。不满足立档阈值 (单会话、1 处 config 改动, 无任务档案)。test.full **2603 passed + 4 skipped / 99% / 50.03s**(基线切片 26-10-05-1000)。
> 最后活动: 2026-10-05 10:00

**Refs:** memory-bank/issues/26-10-05-0922-chore-pytest-cov-gate-test-one.html

## 现状

- **修复完成, 待提交**。改动面: `.commands/test/config.toml`(test.one run 串 + when/note) · 事实回写 `memory-bank/testing/run.md`(命令段补「覆盖率闸只归全量」) 与 `memory-bank/pitfalls/testing/single-file-coverage-gate.md`(处置段记 test.one 已内置 + 复发 1→2) · issue 状态回填 (Open → In Progress → Done + §05 实际修法/验证) · 本切片 · 基线切片 · `kb.index` 重建生成物。
- 验证: 修复前复验 `commands run test.one -- tests/test_docs_forms.py` → `11 passed in 4.42s` 同屏 `FAIL Required test coverage of 98% not reached. Total coverage: 18.52%`(现象仍在, 防过期原则第 5 条); 修复后 → `11 passed in 1.50s`, 无覆盖率 FAIL。全量 `test.full` 2603 passed + 4 skipped / 99% / 50.03s。
- 未验证面 / 残留风险: 裸跑 `uv run pytest tests/x.py -q` 不经 task, 仍会撞该假红(手工 `--no-cov`) —— 坑档保留此半边判据。
- 判据沉淀: 「覆盖率闸只归全量收集面, 部分运行不背全库闸」写进 run.md 命令段 + task note; 坑档 single-file-coverage-gate 处置段更新为「用 test.one 即免」。
