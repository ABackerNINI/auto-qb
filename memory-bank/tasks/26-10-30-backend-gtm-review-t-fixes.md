# 26-10-30-backend-gtm-review-t-fixes — gtm 批T 三缺陷收口: config 写锁 / http_host 回环 / day_rolled 方向

**Status:** In Progress
**Added:** 2026-10-30
**Updated:** 2026-10-30
**Summary:** gtm 批T 三缺陷(T-01/T-02/T-03, 第二次全项目 code review)收口: config 写路径加 `_config_write_lock` 串行化 / `http_host` 校验层回环约束 / `day_rolled` 方向检查(回跳不清零且钉原日界), 三 issue 翻 Done, 全量全绿(数字见 kb.baseline)
**Topics:** backend-gtm-review-t-fixes

## 原始请求

1. 用户指令「认领并修复」三份 issue: `26-10-30-0624-bug-gtm-config-write-lock.html`(T-01)、`26-10-30-0624-bug-gtm-http-host-loopback-contract.html`(T-02)、`26-10-30-0624-bug-gtm-day-rolled-direction-check.html`(T-03) —— 三条均为第二次全项目 code review 批T 的 P3, 用户显式指派 = 认领授权。

## 思考过程与决策

- **T-02 取「校验层兑现绑定承诺」一侧**(issue 建议二选一): 改 docstring 降级声明会让安全不变式消失, 加约束则两处声明面原样成立。放行面 = `ipaddress.is_loopback`(127.0.0.0/8 全段 + ::1) + 保留名 `localhost`(RFC 6761, 按定义只解析到回环, 不因严格而破坏合法存量配置); 非回环 fail-fast 聚合报错、不静默回落默认值(黄金法则 4)。约束落 `validate_payload` 单点, `load_config` 与 PUT /config 两入口共用。
- **T-03 复验发现比 issue 描述多一层**: `storage.record` 用 `result.day` 做 dat upsert 目标 —— 只按建议「不清零」修, 回跳采样仍会把累计 upsert 进历史日期行(写坏历史)。故除 `day > self._day` 才硬切、`day <` 记 WARNING 外, 还把采样日钉在原日界(`day = self._day`), 累计与 upsert 目标一致; 快照日界因此保持「晚于今天」形态, 重启后 restore 走既有「未来日期判损坏降级」—— 与恢复路径同一防线, 天然对称。
- **T-01 取「加锁串行化」一侧**(而非 /autostart 最小改写): 最小改写要新开「只翻一个键」的 YAML 改写路径, 复杂度高于一把锁; 锁与 `storage._state_lock` 同族(HTTP 线程写点串行化的既有先例), 锁内无网络无重活。`/autostart` 的**快照读取也放进锁内** —— 只锁 save 不锁 read, 丢更新窗口仍在。

## 实现计划

总体思路: 三 issue 各自独立修, 每条 = 源码最小修 + docstring 声明面对齐 + 守阵(含一条确定性复刻原缺陷的用例), 最后全量 test.full + 基线切片。

1. T-03 sampler: day_rolled 判据加方向 + 回跳钉日界 + 模块 docstring; test_sampler 两用例(回跳保持/回跳后再前进自愈)。
2. T-02 config: `_check_str` 之上加 `_check_http_host`, `_STR_FIELDS` 改 `_HOST_FIELDS`; server/storage docstring 取齐; test_config 放行/拒绝参数化面 + load_config 入口用例。
3. T-01 server: `ControlServer._config_write_lock`, `_put_config` 与 `_autostart` 临界区持锁; test_server 阻塞 save_config 替身复刻交叠 + PUT 非回环 400 端点用例。
4. 收尾: dev.fmt → test.full → 三 issue 翻 Done + 日志行 → kb.index → 立档/切片/基线。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | T-03 sampler day_rolled 方向检查 + 钉日界 + 守阵 | Done(2026-10-30) |
| 2 | T-02 config http_host 回环约束 + 声明面对齐 + 守阵 | Done(2026-10-30) |
| 3 | T-01 server config 写临界区加锁 + 守阵 | Done(2026-10-30) |
| 4 | 全量 test.full + 基线切片 + issue 翻 Done + 索引重建 | Done(2026-10-30) |

## 进度日志

### R0 · 立档 (2026-10-30)

- 2026-10-30 06:50 T-01/T-02/T-03 三缺陷收口: sampler day_rolled 方向检查+钉日界, config http_host 回环约束, server config 写临界区 _config_write_lock; 三 issue 翻 Done, 守阵 +9 条, 全量 test.full 全绿与覆盖率见 kb.baseline 最新切片(26-10-30-0649)
