# 3131 —— 守阵保留前缀指令分支死支修复 + 恒久活性探针

> 摘要: issue 26-10-11-2030 认领修复轮。守阵 `test_frontend_template_no_reserved_prefix_identifiers` 的指令表达式分支取错捕获组(组 1 = 引号, 表达式在组 2), 检出能力恒为 0。修 = 消费处改 `group(2)` + 扫描抽单点 `_reserved_prefix_problems` + 守阵尾部恒久活性探针(两条形态已知违规必须命中 / 白名单内建必须放行); 真注入红验(往 ctx-menus.html 尾写 `@click="_probeRed()"` 精准报红, 还原复绿); 修前存量预览 19 份扫描源 0 违规。坑档 `pitfalls/testing/guard-dead-branch.md`。
> 基线时间: 2026-10-12 02:33

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 9b0d6f41→acd0e26f; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3131 passed + 3 skipped, 0 failed, 覆盖率 TOTAL 99%**(语句 16517 / 未覆盖 151 / 分支 5626 / partial 134)
- skip 构成(本轮 3 条): `test_commands_engine.py::test_local_codepage_ignores_utf8_mode`(仅 win32+UTF-8 模式有判据, 本轮非 UTF-8 模式跳过) / `test_grouping.py:1635`(normcase 断言仅 POSIX 成立) / `test_web_hr.py:1491`(大小写敏感 FS 断言仅 ext4 成立)
