# 基线切片 26-10-05-1000 — test.one 内置 --no-cov 修覆盖率闸假红 (issue 26-10-05-0922 认领)

> 摘要: 认领 issue 26-10-05-0922 (chore 便签档) —— `pytest.ini` addopts 的 `--cov-fail-under=98` 是对**全量收集面**设的闸, 单文件/筛选跑 (`test.one`) 收集面小 ⇒ 用例全绿仍以覆盖率 FAIL 退出 (假红)。
> 拍板方向①: `.commands/test/config.toml` 的 test.one run 串尾部加 `--no-cov`; pytest.ini 闸门原样保留给 test.full 与 CI 全量跑。
> 本笔零用例增删 (只改 task 定义 + 文档, `src/` 与 `tests/` 零改动)。
> 基线时间: 2026-10-05 10:00

**Refs:** memory-bank/issues/26-10-05-0922-chore-pytest-cov-gate-test-one.html, memory-bank/activeContext/26-10-05-1000-test-cov-gate-test-one.md

- 分支: develop @ 8dd38afe(会话开工同步; 工作树含本轮改动: `.commands/test/config.toml` + issue 状态回填 + `testing/run.md` + 坑档 + 切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2603 passed + 4 skipped, 50.03s, 覆盖率 TOTAL 99%**
  (15605 语句 / 163 未覆盖 / 5308 分支 / 138 partial; 门槛 98% 达标, `Required test coverage of 98% reached. Total coverage: 98.51%`)
- 相对上一条含同代码面的基线 (26-10-05-0945 test-plan-docstring-drift: 2603 passed + 4 skipped / 40.15s~45.13s / 99%):
  passed / skip / 语句 / 分支 / partial **全指标一致** —— 本笔只改 `.commands/test/config.toml` 的 task 定义与文档,
  `src/` 与 `tests/` 零改动, 故对用例数零增量。(列表里更晚的 26-10-05-0947 切片记的是 HR 分支并入前的工作树, 2589 + 4, 非本笔可比基线。)
- 耗时 50.03s 落在近几条切片 36.7~51.8s 的噪声带内, 非回归。
- 靶向验证(非计时): `commands run test.one -- tests/test_docs_forms.py` —— 修复前 `11 passed in 4.42s` 同屏
  `FAIL Required test coverage of 98% not reached. Total coverage: 18.52%`(假红复现); 修复后 `11 passed in 1.50s`,
  无覆盖率 FAIL(免覆盖率插桩故更快)。
- 改动面: `.commands/test/config.toml`(test.one run 串 `--no-cov` + when/note) ·
  `memory-bank/testing/run.md`(命令段补「覆盖率闸只归全量」) ·
  `memory-bank/pitfalls/testing/single-file-coverage-gate.md`(处置段更新 + 复发 1→2) ·
  issue HTML 状态回填(Open → In Progress → Done + §05) · 本切片 + activeContext 切片 · `kb.index` 生成物。
- 未验证面: 裸跑 `uv run pytest tests/x.py -q` 不经 task, 仍会撞该假红(手工 `--no-cov`) —— 坑档保留此半边判据。
