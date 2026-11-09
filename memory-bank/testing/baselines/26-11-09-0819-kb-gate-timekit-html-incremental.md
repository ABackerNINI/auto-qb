# 5,872 passed + 2 skipped —— kb 闸门 timekit/check_html 按改动增量 + 复跑清单扩面 + 展开分片

> 摘要: kb 闸门 timekit/check_html 按改动增量 + 复跑清单扩面 + 展开分片
> 基线时间: 2026-11-09 08:19

## 验收数字

`commands run test.full` 2026-11-09 08:16 复跑实测(本轮收尾时点): **5,872 passed, 2 skipped in 125.82s**; 覆盖率 99% (TOTAL 26,153 语句 / 42 未覆盖 / 9,100 分支 / 54 未覆盖分支; 总覆盖率 99.72%, 门槛 99.5%)。较基线 26-11-09-0619(5,869+2)净增 3 条用例, 来自 `tests/test_memory_bank_docs.py` 新增的三条守阵(无参=全量 / timekit 增量未来日期判红 / check_html 增量只扫给定件); S4 的 7 条引擎用例在 `.commands/my-commit-flow/scripts/test_pipeline.py` 与 `test_commit.py`, 属包测试(test.pkg 口径), 不进 test.full 收集面。

**flake 备注**: 本轮 `test.full` 首跑一次红(5,871 passed + 1 failed)—— 红在 `tests/test_legacy_review4_scripts.py::test_qb_capture_dry_true_zero_requests`, 属已立档偶发坑 `pitfalls/testing/inproc-server-conn-abort.md`(进程内假服已建连被中止族); 单跑该 nodeid 绿, 全量复跑即绿(取上面这组数字)。首跑仅留 tail 未捕到完整 traceback, 按坑档「单跑绿 + 全量复跑绿」判偶发, 不改测试不加无脑重试。

## 本改动面

- `timekit.py`: 新增 `--files`(nargs="*"), 文件名/元数据/正文三层收窄到传入文件; 无参仍全量; 两轮 `rglob` 合一、每文件只读一次、无数字行预筛。
- `check_html.py`: `--check` 接受显式 paths(无参仍全量 902 件); L1+L2 判据不变。
- `.commands/my-commit-flow/.my-commit-flow.toml`: kb 闸门第 7 条改 `timekit.py --check --files <changed:memory-bank/**>`、第 9 条改 `check_html.py --check <changed:**/*.html>`; `timekit.py --check` / `check_html.py --check` 字面串保留(守阵逐字匹配)。
- `_pipeline.py`: `changed_extra` 只并入 `<changed:>` 展开; 新增 8191 字符上限与分片, 分片仍超限 `ExpandError` → rc=-2 STOP。
- `commit.py`: 复跑阶段把 rebase 合入的 `memory-bank/**` 并入 `ctx["changed_extra"]`; `gates_for` 命中与暂存清单未动。
- `tests/test_memory_bank_docs.py`: +3 守阵; `.commands/my-commit-flow/scripts/`: +7 用例。
- memory-bank 回写: 计划 26-11-09-0559(§02 实施轮复测 / §04 / §05 / §10 R1, doc-status Done) + issue 26-11-09-0441(状态 Done + 修复后补充三段) + 任务档案(实施轮与子任务表) + 坑档三处复发 + `conventions/process.md` 闸门口径。
