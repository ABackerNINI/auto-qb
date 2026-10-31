# 1693 passed + 1 skipped / 0 failed —— CarPT HR adapter 接入后新基线

> 摘要: HR 在线核实新增 CarPT 变体 adapter(`?status=N` 状态参数 + `H&R ID` 十列表头)落地后全量:
> NexusPhpMyhrAdapter 参数化(scope 参数/表头/列名可注入), fetcher/report 的 `_scope_of` 兼容 `status=`;
> 测试 +5(CarPT URL 映射 / 解析 / 空表 / 改版 / 登录识别), 语句 11206→11227。基线时间: 2026-09-27 12:35
> 档案: 26-09-22-backend-partial-hr-verify

TOTAL 91%(11227 语句 / 815 未覆盖 / 3720 分支 / 330 partial; test.full 18.1s;
覆盖率口径见 [../baseline.md](../baseline.md))。
