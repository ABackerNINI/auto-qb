# 5649 passed + 2 skipped(根) —— R4 scripts 修复批收尾基线: 五批委派实施 + 评审收口 + issue 收编

> 摘要: R4 scripts 修复批收尾基线: 五批委派实施 + 评审收口 + issue 收编
> 基线时间: 2026-11-07 12:48

## 验收数字

`commands run test.full` 实测 (121.0s):

```text
TOTAL                                                25511      5   8802     27    99%
5649 passed, 2 skipped, 1 warning in 121.04s (0:02:01)
```

覆盖率门槛 99.5 过(实测输出 `Total coverage: 99.91%`)。相对上片差值看 `commands run kb.baseline -n 2`;
本批新增 19 例(test_legacy_review4_scripts 15 + test_sim_corpus 4), 既有用例 0 改写; 2 skipped 为
既有设计性跳过(见上片 -rs 实核)。POSIX 侧未本地重测, 随推送由 GitHub CI 验证; 本批改动全在
scripts/ 测试与守卫工具 + 测试文件, 生产码零改动, 对 POSIX 的行为差预期为零。

**flake 备注**: 本轮首跑一次红(5648+1 failed)——红在 `test_legacy_review4_scripts.py::test_qb_capture_dry_true_zero_requests`
的**对照组**真流量段(`ConnectionAbortedError(10053)`, --dry 零请求主断言已过), 单跑绿、复跑全量即本片绿
数字, 定性并行负载 flake; 指纹与处置见 `pitfalls/testing/inproc-server-conn-abort.md`。

包内脚本测试 `commands run test.pkg`: 本批动过 `.commands/dev/config.toml`(dev.port-kill note), 实测
371 passed + 15 subtests passed in 74.70s 全绿。

## 本改动面

- scripts/ 17 工具修复(五批委派, 逐条明细见 issue 26-11-07-0536 与档案 tasks/26-11-07-test-legacy-review4-scripts-fix.md):
  sim_qb_server / sim_fsmock / sim_baseline / sim_run / sim_qb / sim_qb_cli / sim_qb_core / sim_qb_model /
  ui_harness / e2e_selfcheck / qb_capture / port_kill / hr_ext_stub / hr_fetch_experiment / dev_webui /
  check_command_drift / check_context_caps; 重点改道: qb_capture --dry 提前到 main() Capture 构造前判定
  (真零请求), port_kill 新增杀前进程核验 kill_decision + --yes 门。
- tests/ 新增 2 文件: test_legacy_review4_scripts.py(15 例) + test_sim_corpus.py(4 例), 文件头测试计划同步。
- `.commands/dev/config.toml`: dev.port-kill note 更新(--yes 门口径)。
- AGENTS.md: 「🔴进程安全:禁止一切taskkill」条目新增 2 行豁免(port_kill.py + hr_fetch_experiment.py
  脚本内定点杀, 用户拍板 2026-11-07)。
- memory-bank/ 侧: issue 26-11-07-0536 收编 Done; 坑档 console-encoding.md 复发 +1 + 新立
  inproc-server-conn-abort.md; 切片与索引为 kb.wrap / kb.index 生成物。
