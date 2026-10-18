# 3590 passed + 4 skipped(根, TOTAL 18146/266/6146/193, 覆盖率 98%) —— 通知链路日志降 DEBUG 后全量基线

> 摘要: 通知链路日志降 DEBUG 后全量基线
> 基线时间: 2026-10-18 19:47

## 验收数字

`commands run test.full`(2026-10-18 19:44 / 19:46 连跑两次, 数字一致):

```
TOTAL   18146   266   6146   193   98%
3590 passed, 4 skipped in 33.95s / 35.90s
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 /
覆盖率(成功路径只印整数位)。计数与上一条基线(26-10-18-1058)逐位一致 —— 本次降级的三个
日志点原本就被既有用例覆盖, 无新增覆盖缺口; 用例数 3587 -> 3590 = 本轮新增 2 条守阵
(`test_notify_refresh_logs_at_debug` / `test_refresh_publish_logs_at_debug`)。

## 本改动面

用户诉求「log 被流量事件刷屏」: 全局流量监视器通知链路(gtm 阈值事件 -> 接收面 -> 主循环
刷新 -> 快照发布)每个放行事件固定产出 3 行 INFO, 大流量日(今日约 68GiB, 事件号至 #1200)
可达数百组。按用户拍板「改为 DEBUG 级」降级:

- `src/auto_qb/webui/server/routes/traffic_monitor.py`: 接收面放行日志(事件号/累计值 ->
  已投递刷新)INFO -> DEBUG; 与本就 DEBUG 的 skipped 分支口径一致(放行/拦下都只 DEBUG 可见);
  消息文本不变, DEBUG 下排障仍看得到事件号。
- `src/auto_qb/webui/commands.py`: `_cmd_refresh_traffic` 的 notify 触发分支 INFO ->
  DEBUG(docstring 同步); `config` 触发分支保持 INFO(用户保存动作, 一次一笔)。
- `src/auto_qb/core/modules/traffic_snapshot_mod.py`: `refresh()` 的「发布历史流量」一行
  INFO -> DEBUG(定时任务与通知链路共用该路径); 读盘失败/坏行两条 WARNING 不降。
- 测试守阵: `tests/test_web_traffic_monitor_notify.py::test_notify_refresh_logs_at_debug`
  (接收面放行日志恒 DEBUG 且不留 INFO 同题记录)与
  `tests/test_traffic_snapshot.py::test_refresh_publish_logs_at_debug`(发布行恒 DEBUG);
  捕获走 `helpers.capture_logs`(QbManager 构造链清 root handlers, caplog 恒空);
  两个文件的「## 测试计划」清单同步新增条目。
- 未动: 事件频率收敛参数(`traffic_source.global_traffic_monitor.notify_cooldown_s` 与工具侧
  `notify_threshold_bytes`)—— 本轮只降日志级, 收敛旋钮留待用户按需配置。
