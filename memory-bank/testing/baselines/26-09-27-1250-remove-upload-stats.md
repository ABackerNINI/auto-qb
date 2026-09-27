# 1691 passed + 1 skipped / 0 failed —— upload_size 统计底座移除后新基线(合并远端 56c04e0 重测)

> 摘要: 计划 26-09-27-1232 执行完毕 —— 移除 upload_size/today/week/month 四条件 +
> tor.upload_today/week/month 表达式名 + begin_round/upload_delta 底座 +
> state["upload_snapshots"](state schema v1→v2 迁移清键)。
> 提交前 ff 合并远端 `56c04e0`(hr carpt 适配器 + webui 模板聚合化)后于新基线重测:
> 本改动树上 test.quick 与 test.full 双全绿。测试数 1688→1691(本改动删 3 用例 + 删 1 断言行 +
> 新增生产迁移测试 1; 远端净增 5)。
> 基线时间: 2026-09-27 13:00 (首测 12:50 在旧基线 835b62c: 1686 passed)
> 档案: 26-09-27-1232-plan-remove-upload-stats

TOTAL 91%(11195 语句 / 816 未覆盖 / 3724 分支 / 331 partial; test.full 18.1s;
覆盖率口径见 [../baseline.md](../baseline.md))。
