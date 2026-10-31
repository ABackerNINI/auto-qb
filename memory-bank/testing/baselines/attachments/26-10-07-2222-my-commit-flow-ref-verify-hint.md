# 2757 —— my-commit-flow ref 核对停手指引按形态分流 (纯 .commands 轮, src/tests 零改动)

> 摘要: `verify_ref.py` 停手指引按形态分流 —— 「HEAD==loose 但 packed-refs 落后」不再误指向
> 「分支 ref 被回退」条目(其 `update-ref` 配方治不好 packed-refs), 改送「packed-refs 陈旧」条目
> (`git pack-refs --all`)。改动面全在 `.commands/my-commit-flow/scripts/`(verify_ref.py + test_commit.py)
> 与 `memory-bank/pitfalls/git/refs.md`; `src/`、`tests/`、配置零改动 ⇒ test.full 数字与上一基线持平,
> 增量在包内脚本测试(test.pkg)。
> 基线时间: 2026-10-07 22:22

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2757 passed + 4 skipped, 0 failed, 44.0s, 覆盖率 TOTAL 99%**
  (16457 语句 / 166 未覆盖 / 5686 分支 / 150 partial; 门槛 98% 达标)
- 相对上一基线 [26-10-07-2053](26-10-07-2053-webui-qb-traffic-rate-basis.md)
  (2757 passed + 4 skipped @ 29.50s, 16457 语句 / 166 未覆盖 / 5686 分支 / 150 partial):
  **全部指标逐位相同** —— 本轮 pytest 收集面零改动(`.commands/` 在 `testpaths(tests/)` 之外)。
  4 skipped 为 Windows 侧 POSIX 专属存量。

## 包内脚本测试 (test.pkg)

- 命令: `commands run test.pkg`(`uv run pytest .commands .agents/skills/commands -q --no-cov -n 4`)
- **实测: 148 passed**(117.6s, 0 failed)
- 本轮 `test_commit.py` 新增 3 条: `test_classify_form_pure` · `test_check_refs_packed_stale_routes_to_pack_refs` ·
  `test_check_refs_branch_rollback_routes_to_rollback_entry`(钉住两种形态的分流)。
