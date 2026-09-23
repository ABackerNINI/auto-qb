# config 取值范围收紧
> 摘要: 已随合并入库；剩「缺省 0S = 每 tick」是否收紧待拍板（属行为变更）
> 触发: config 取值范围, 校验收紧, nan/inf, 行为变更
> 最后活动: 2026-09-22 19:37

## 状态

issue [26-09-22-1937-bug-config-value-range-validation](../issues/26-09-22-1937-bug-config-value-range-validation.html) 已置 Fixed。

收紧清单：`interval` 1s-1D / `main_tick` 0.5s-1H / `sync_interval` 1s-10M /
`max_tasks_per_tick` 1-500 / `log.max_bytes` 1MiB-1GiB（0 = RotatingFileHandler 从不轮转）/
站点 hr `required_share_ratio` [0,100] 拦 nan/inf /
`hr.condition` 百分比 (0,100] 与下载量 >0（`utils.parse_hr_condition` 解析单点拦）/
`notify.max_per_hour` ≤100 / `dedup_window` ≤24H（0 = 不去重仍合法）/ 规则 `interval` 显式 0 拦。

**待拍板**：缺省 `0S` = 每 tick 级别是既有行为未动，是否收紧属行为变更。

机制文档已回写 [config-reference/loading-and-write.md](../config-reference/loading-and-write.md)「校验范围 · 取值范围」条。
