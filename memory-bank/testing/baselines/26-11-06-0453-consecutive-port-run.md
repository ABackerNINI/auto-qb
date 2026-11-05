# 5466 passed + 2 skipped in 152.53s(TOTAL 24538 stmts / 57 miss / 99% cover) —— 连号候选端口整段自验修复后全量基线(issue 26-11-06-0330)

> 摘要: 连号候选端口整段自验修复后全量基线(issue 26-11-06-0330)
> 基线时间: 2026-11-06 04:53
**Refs:** memory-bank/issues/26-11-06-0330-test-hr-discovery-busy-retry-flake.html, memory-bank/activeContext/26-11-06-0453-consecutive-port-run.md

## 验收数字

- 汇总行: **5466 passed + 2 skipped** in 152.53s(0:02:32, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 57 miss / 36 partial / 99%**(Windows 侧覆盖闸 99.5, PASS)。
- 副作用台账: 越界 0。
- 差值对比: 相对上基线(26-11-06-0427, 5462)+4 —— 本轮守阵 +2(`test_hold_run_returns_bindable_run` /
  `test_hold_run_discards_run_whose_offset_is_refused`), 另 +2 来自开工同步并入的远端用例(55 笔)。

## 本改动面

- `tests/_test_ports.py`: 新增 `hold_run(count=3)` —— 连号候选段**整段真绑并持有**, 任一位失败
  (Windows 排除段 10013 / 独占 10048)整段丢弃换基址, 连抢 `RETRIES` 次才 `RuntimeError`; 返回 `(base, socks)`。
- `tests/test_hr_discovery.py`: `test_start_all_busy_returns_false_and_retries` 改用 `_hold_run(3)`
  (原 `_free_port()` + 自建 `_hold_ports` 只验基址, 是 issue 26-11-06-0330 的假红源)。
- `tests/test_free_port.py`: 守阵 +2(连号+持有契约 / 注入 10013 ⇒ 整段丢弃换基址)。
- 同形三处一并修(当日后续轮, issue 26-11-06-0330 的另一件):
  `test_start_binds_first_free_candidate`(`hold_run(3)` 自验后放回后两位, 断言改「候选表非首位」)、
  `test_runtime_builds_and_starts_discovery`(`hold_run(3)` 自验后全放回, 断言改「落在候选表」)、
  `test_runtime_discovery_bind_failure_keeps_data_endpoint`(占位改 `hold_run(3)`);
  本地 `_hold_ports` 复制实现删除, 端口占位单点收敛到 `tests/_test_ports.py`。
- 知识库: issue 26-11-06-0330 翻 Done(复验+修复后补充) · flaky 台账该行翻 Done · 新坑档
  `pitfalls/testing/consecutive-port-run.md` · `pitfalls/ops/venv-trampoline-clone-copy.md` 复发 +1。
