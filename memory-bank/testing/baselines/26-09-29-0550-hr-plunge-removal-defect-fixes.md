# 1739 passed / 3 skipped —— 骤降保护移除 + HR 复审缺陷 H1/M1/M2 修复

> 摘要: 按复审报告 [reports/26-09-29-0404](../../reports/26-09-29-0404-report-hr-verify-v3-audit.html)
> §13 的用户裁决与缺陷清单实施: ①**骤降保护移除**(§13.3 裁决 —— 流转守恒是骤降的升级版, A 只流向
> B/C/D, 总量变化不构成漏 HR 面; 基线高水位永不回落会在站点合法清账后永久冻结批量签发):
> service(`PLUNGE_RATIO`/`plunge_suspect`/`releases_enabled` 条件/告警) + model(`HrWaveMeta.plunge/
> baseline_rows` 删除, hr_site 迁移不再产出 —— 读侧对旧文件键容忍, 非破坏性变更不 bump schema) +
> status/events/report/WebUI 模板/configuration.md 全链清理, 防伪收敛为「守恒 + 零行戳」两道;
> ②**H1** Retry-After 落盘(`_do_wave` 分支 commit + mark; 下载路径带 retry_after 上抛波级不计种子
> 失败); ③**M1** 登录失效路径 `budget.mark()` 前进间隔基准; ④**M2** 站点文件 schema 比程序新
> (`HrLockSession.version_mismatch`)跳过取数与写盘。测试: FakeFetcher 扩展 login_at/retry_after_at/
> retry_bytes_at; 骤降用例删除; light-wave 用例重写钉裁决行为(旧用例名不符实); 新增 4 回归。
> 基线时间: 2026-09-29 (develop @ 55a6b660, 已合流远端 WEBUI 搜索层改造)
> 档案: tasks/26-09-22-backend-partial-hr-verify.md · 报告 §13.5 实施记录

- test.full: **1739 passed / 3 skipped**, TOTAL **90%**(12,299 语句 / 1,005 未覆盖 / 4,168 分支 /
  408 partial), 耗时 ~21s。较上一基线(26-09-29-0301, 1735/3): +4 passed —— 骤降用例 −1,
  新增回归 +5(Retry-After 跨波 / 下载上抛 / 登录 mark / schema 跳过; light-wave 重写改名);
  语句 12,422→12,299(骤降机制删码)。
- 中途红验: version_mismatch 早退曾漏写 `return result`(返回 None 被测试当场抓住) —— 修复后全绿;
  M1/M2 测试自身的缺 import/缺 mkdir 两处亦由全量红验暴露后修复。
- 未提交(等用户显式指令); 真机走查开放(修 H1 后顺带验证 Retry-After 行为)。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
