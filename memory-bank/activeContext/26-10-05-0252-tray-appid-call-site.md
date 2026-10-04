# tray AUMID 生产调用点 — issue 26-10-02-0727 + 2203 认领 (0727 Done / 2203 待真机确认)

> 摘要: 认领两份高度关联 issue。0727: `_set_windows_appid` 自 9891c030 引入起生产零调用点, 生产从未设
> 进程级 AUMID; 2203: 任务栏按钮恒 python 图标五轮未解。考古闭环(2026-10-05): 引入提交当时即生而零调用
> (git show 9891c030:src/auto_qb/ui.py 仅定义无 caller), 非「后被移除」; 五轮排查的「AUMID」均为注册表/lnk
> 的 toast 来源身份注册(notify 的 AutoQB.UI), 不改变当前进程 AUMID —— 决定性变量从未被施加, 与 core-domain.md
> 四轮对照诊断(无 AUMID 恒 python.exe)完全自洽。实际修法(0727 建议修法①): TrayUi.__init__ 在 _build_window
> (首窗口)前调用 _set_windows_appid(); 新增时序钉死测试 test_trayui_init_sets_appid_before_first_window,
> 红验(摘调用点→红)通过。test.full 2541 passed + 4 skipped / 99% / 28.49s (基线
> [26-10-05-0252](../testing/baselines/26-10-05-0252-tray-appid-call-site.md))。不满足立档阈值, 无任务档案。
> 最后活动: 2026-10-05 02:52

**Refs:** memory-bank/issues/26-10-02-0727-bug-tray-appid-setter-no-call-site.html, memory-bank/issues/26-10-01-2203-bug-taskbar-python-icon.html, memory-bank/testing/baselines/26-10-05-0252-tray-appid-call-site.md

## 现状

- 0727 已 Done: 生产调用点已补(TrayUi.__init__ 首窗口前), core-domain.md:27 现状段已回写。
- 2203 In Progress: 代码链路已闭环, **任务栏按钮是否恢复 orbit 属真机视觉行为, 待作者下次 --tray 运行
  目视确认** —— 确认后转 Done; 若仍 python, 在 AUMID 已生效新前提下按 explorer 身份解析链重新取证
  (五轮排除项不需重查)。
- 改动未提交: src/auto_qb/tray/app.py / tests/test_tray.py / 两份 issue HTML / core-domain.md /
  issues/_index.md / 基线切片 / 本切片。
