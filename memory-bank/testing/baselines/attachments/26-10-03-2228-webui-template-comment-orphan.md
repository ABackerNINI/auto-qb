# 基线 · 2416 passed + 3 skipped / 99% —— WEBUI 分片注释孤儿修复轮

> 摘要: 用户报 WEBUI 设置页冒出中文注释文字 —— W1 模板分片(commit `6fd133147`)切割时把「统计面板
> (FE-2C)」注释的**开头一行**丢了, 聚合(清单里 `into:"app"` 的分片拼成一个字符串再注入)里只剩孤儿
> `-->`, 被渲染成文字节点, 任何视图都可见。补回 shared/tpl/dialogs.html 第 1 行注释开头即修
> (`dialogs-mgr.html:1` 的 `-->` 由 dialogs.html 尾部闭合, 非孤儿, 未动)。
> 基线时间: 2026-10-03 22:28, develop @ 05b89769(工作区含本轮修复, 未提交)。

TOTAL **2416 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial, test.full 42.9s, rc=0)。
相对上一切片(26-10-03-2130: 2416 passed + 3 skipped / 99%, @ 03b5e211)**持平** —— 纯注释修复, 无代码路径变化。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。