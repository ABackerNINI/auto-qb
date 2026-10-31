# 3990 —— tests 共享小助手收口后全量基线

> 摘要: tests 共享小助手收口后全量基线
> 基线时间: 2026-10-22 12:45

## 验收数字

`commands run test.full` 实测输出（基线 ad17518a，改动后同基线）：

- 汇总行: **3990 passed, 10 skipped in 77.27s (0:01:17)**
- TOTAL 表: `20728  116   7088   106    99%`（语句 / missed / 分支 / partial / 覆盖率）
- 覆盖率门槛 99% 达标，无 FAIL 行；零失败零回归

口径注记：passed/skipped/覆盖率数字由 agent 从本次实测输出誊写；相对上基线的逐位对比不写（看差值 `commands run kb.baseline -n 2`）。

合流后复测（rebase 到 `c3e7a71f`，含远端 4 笔 polling / aq-fold / web_env 提交）：**3992 passed, 10 skipped**，覆盖率 99%（TOTAL `20728  116   7088   105`）。与上表 +2 的差额即远端新增用例，非本轮改动引入。

## 本改动面

认领并修复 issue `26-10-21-0502-refactor-test-shared-micro-helper-dup`：8 族同名小助手逐字拷贝（24 处）全部收口到 tests 共享层单点，调用点直引单点、不留转发壳。

- `tests/helpers.py`：新增共享单点 8 个 —— `dat_text` / `write_dat` / `write_dat_lines` / `server_state` / `active_torrent` / `write_credential_file` / `pin_disk_usage` / `pin_atomic_write_crash` + 常量 `DAT_HEADER_LINE` / `LEGACY_V1`
- `tests/webui_helpers.py`：新增 `make_store(*hashes, state)`（⑥族落点，WEB UI 领域）
- 删除副本的 14 个测试文件：test_episodes / test_grouping / test_modules_p4（①）；test_grouping_relocate / test_relocate_exec / test_relocate_paths / test_web_relocate（②）；test_speed_curve / test_traffic_snapshot / test_traffic_monitor_client / test_traffic_store（③④）；test_traffic_sample（④）；test_traffic_source_agent（⑤）；test_webui_delta / test_webui_delta_mirror（⑥）；test_hr_channel / test_web_backend_misc（⑦）；test_config_writer / test_qbmanager（⑧）
- `src/` 零改动（纯 tests 侧合流）；仓库根 README/AGENTS.md 无受影响条目
