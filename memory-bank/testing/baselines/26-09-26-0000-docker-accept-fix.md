# 1619 collected: 1618 passed + 1 skipped —— Docker 真机验收修复轮

> 摘要: 首连失败退出码契约(+2 条)与生命周期日志级别(改 2 条); 时分不可考; 当日序位第 1
> 基线时间: 2026-09-26 00:00
> 档案: 26-09-25-deps-docker-deploy

(档案 `26-09-25-deps-docker-deploy`)。**+2 条, 改 2 条**: 首连失败退出码契约(test_cli/test_qbmanager/test_ui)
+ 「WEB UI 已启动 / 配置热重载完成」按 INFO 记的日志断言(⚠ 抓日志挂目标 logger, caplog 挂 root 会被
setup_logging 清空)。
