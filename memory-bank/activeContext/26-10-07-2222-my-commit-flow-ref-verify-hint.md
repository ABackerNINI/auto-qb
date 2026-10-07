# my-commit-flow ref 核对停手指引按形态分流 (Done)

> 摘要: 另一会话报「`verify_ref.py` 的停手指引对『HEAD==loose 但 packed-refs 落后』形态仍指向『分支 ref 被回退』条目, 按其 `update-ref` 配方治不好」——坑档 `pitfalls/git/refs.md` 同日已记 4 笔复发, 该会话本轮实际撞 5 次。根治 = `verify_ref.py` 停手指引**按形态分流**: 新增 `classify_form()`, 判「三处本地真值(HEAD / refs/heads / loose)一致、仅 packed 落后」→ 送「packed-refs 陈旧」条目(`git pack-refs --all`, 明示**不要** update-ref); 只有分支指针真被回退/丢失才送「分支 ref 被回退」条目。输出契约 v3→v4, 加 3 条守阵钉住分流。test.pkg **148 passed**; test.full **2757 passed + 4 skipped / 99%**(基线切片 26-10-07-2222)。
> 最后活动: 2026-10-07 22:22

## 现状

- **改动完成**。改动面: `.commands/my-commit-flow/scripts/verify_ref.py`(`FIX_HINT` 拆 `BRANCH_ROLLBACK_HINT` / `PACKED_STALE_HINT` + 新增 `classify_form` + `check_refs` 按形态分流 + docstring v4) · `.commands/my-commit-flow/scripts/test_commit.py`(3 条守阵 + docstring「测试计划」同步) · `memory-bank/pitfalls/git/refs.md`(处置加分流注 + 复发 4→5)。
- 验证: `commands run test.pkg` **148 passed**(117.6s); `commands run test.full` **2757 passed + 4 skipped / 0 failed / 99% / 44.0s**(16457 语句 / 166 未覆盖 / 5686 分支 / 150 partial) —— 与上一条基线 26-10-07-2053 逐位相同, 本轮只动 `.commands/` 包脚本, 不进 testpaths, 项目面预期零增量。
- 判据沉淀: ①停手指引指错配方 = 坑档反复复发的直接原因(按被回退条目的 `update-ref` 治不好 packed-refs); 分流判据 = 三处本地真值是否一致, 单点落 `classify_form`。②守阵断言别用裸子串 `分支 ref 被回退` —— 新指引正文含对比句会误判, 改判「是否指向该条目」(`「分支 ref 被回退」条目` 或配方行 `建锚点防 GC`)。
- 未验证面 / 残留风险: packed_stale 分流靠临时仓库造形态验证(真仓复现需先 `pack-refs --all` 再提交), 未在真机撞到该形态; 该形态下提交确已落稳(坑档实证), 处置后补 `ship.push` 即可。
