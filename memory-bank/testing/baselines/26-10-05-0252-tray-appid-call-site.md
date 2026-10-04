# 基线切片 26-10-05-0252 — tray AUMID 设置补生产调用点 (issue 26-10-02-0727 认领, 关联 2203)

> 摘要: 认领 issue 26-10-02-0727 (tray/_set_windows_appid 自 9891c030 引入起生产零调用点, 生产从未设
> 进程级 AUMID) 与关联 26-10-01-2203 (任务栏按钮恒 python 图标五轮未解)。考古闭环: 9891c030 引入时即
> 生而零调用(git show 9891c030:src/auto_qb/ui.py 仅定义 :135 无 caller); 五轮排查的「AUMID」均为注册表/lnk
> 的 toast 来源注册, 不改变进程 AUMID, 决定性变量从未生效 —— 与 core-domain.md 四轮对照诊断自洽。
> 修法①: TrayUi.__init__ 在 _build_window 前调 _set_windows_appid(), 时序钉死测试防调用点再丢失。
> 基线时间: 2026-10-05 02:52

**Refs:** memory-bank/issues/26-10-02-0727-bug-tray-appid-setter-no-call-site.html, memory-bank/issues/26-10-01-2203-bug-taskbar-python-icon.html, memory-bank/activeContext/26-10-05-0252-tray-appid-call-site.md

- 分支: develop @ 3505fda1 (+ 本轮未提交改动: src/auto_qb/tray/app.py / tests/test_tray.py / 两份 issue HTML / core-domain.md / issues/_index.md / 本切片)
- 命令: `commands run test.full`(Windows, 最终态一次采样)
- **实测 (Windows)**: **2541 passed + 4 skipped, 28.49s, 覆盖率 TOTAL 99%**
  (14871 语句 / 152 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向 (tests/test_tray.py): 59 passed。红验: 探针把 `_set_windows_appid()` 调用临时摘除,
  新时序测试 `test_trayui_init_sets_appid_before_first_window` 变红(order == ["window","tray"] 缺 appid),
  恢复后绿。过程插曲: 红验后用 `git checkout -- app.py` 恢复时把未提交修复一并回退(HEAD 即原始态),
  已重新落补丁并以本基线的最终态重跑为准 —— 数字取自恢复后重跑, 非探针前旧采样。
- 相对上基线 (26-10-05-0232: 2540 passed + 4 skipped / 99% / 36.39s+27.69s): passed +1
  (新增时序测试 1 条); 语句 14870→14871 = app.py 新增调用一行(注释不计语句)。
- 改动面: src/auto_qb/tray/app.py(调用点 +4 行) + tests/test_tray.py(新测试 + 测试计划同步) +
  两份 issue HTML(0727→Done / 2203→In Progress) + core-domain.md(:27 现状回写) + issues/_index.md(生成物) +
  基线切片 / activeContext 切片。
