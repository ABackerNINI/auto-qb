# 1831 passed / 3 skipped —— 设置二级页返回优化: 吸顶返回条 + Esc 返回基线快照(档案 26-09-28-webui-settings-back-nav)

> 摘要: 方案一(面包屑升级吸顶返回条)+方案三(Esc 链尾返回首页, escBusy 守门)落地后的基线。纯静态前端改动(5 文件: tpl/settings.html / console_hub.css / config_hub.js / dialogs.js / lifecycle.js 注释), 无测试接触面、无新增用例。
> 基线时间: 2026-09-28 22:01
> 档案: tasks/26-09-28-webui-settings-back-nav.md(新建)

- test.full: **1831 passed / 3 skipped**, TOTAL **91%**(12462 语句 / 917 未覆盖 / 4246 分支 / 391 partial), 耗时 23.5s; 同数字复跑 test.quick 一致。
- 较前基线(26-09-28-1855)净增 8 条 passed: 来自本会话开头同步合入的远端区间 b68e9a0..debdf600(配置版本守卫 +3 / HR 排除 / throttle 计时余量 / 移除遮蔽重复用例), 与本批改动无关; 本批零回归。
