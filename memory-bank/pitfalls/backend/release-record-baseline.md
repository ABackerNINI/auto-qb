# 「永久生效」的凭据必须连比对基准一起落盘 —— 缺了它, 签发当刻就被消费侧作废

> 摘要: 一份凭据(放行/授权/豁免记录)若靠「与签发时的状态快照比对」来判断是否失效, 快照就是
> 凭据的一部分 —— 漏带快照 ⇒ 消费侧把「快照全零」读成「状态已变」, 凭据**签发当刻即作废**,
> 且**不报错**: 表现是「功能像是没生效」(HR: 种子显示本地兜底), 而写入方日志一切正常。
> 触发: 放行记录, verified, 签发, 锚点, 快照, 漂移, drift, 永续有效, 永久记录, 凭据, 三处写入点, 签发即作废

### 判别与处置

- **触发**: 写「一次签发、长期有效」的记录时, 消费侧用记录里的字段与**当下状态**比对来决定
  是否作废/失效(本仓: `HrVerified.anchor_*` 与本地锚点比 `drift_reason`)。
- **判别**: 数清这条记录**有几个写入点**; 只要有两个以上, 快照字段就必然被漏一处。
  本仓实例(2026-09-29 实报): 三处签发里 `_sign_releases` 带了快照, `_freeze_terminal` /
  `_advance_observation` 没带 ⇒ 后两者签发的放行记录, 在 `resolve_identity` 行 3 立刻被判
  「锚点漂移(本机重下): downloaded 增长」(`anchor_downloaded=0` vs 本地 `downloaded>0`)⇒ 落行 4
  本地兜底。用户看到的是「明明在线核实过, 却显示本地兜底已达标」,**全程零报错**。
- **处置**: ①把记录的构造收敛成**单点工厂**(本仓 `hr/service.py::_release_record`), 快照在里面
  一次写全 —— 多写入点 + 每个点自己拼 kwargs 就是漏字段的温床; ②消费侧的比对, **基准缺失时
  一律不作废**(本仓 `HrVerified.has_anchor_snapshot` + `drift_reason` 早退): 「无数据可比」
  ≠ 「状态已变」 —— 前者只能保守放行, 硬判漂移会把所有旧记录(早于该字段落盘的)一并作废,
  与「迁移零过渡」的承诺直接冲突; ③守卫要断言**字段真的落盘**(本仓钉 `verified[h].source`
  与 `.has_anchor_snapshot`), 只断言「记录在」等于没测。
- **守阵**: `tests/test_hr_service.py::test_terminal_vanish_writes_release`(断言
  `data.verified[h21].has_anchor_snapshot` 且 `anchor_downloaded == anchors[h21].downloaded`)、
  `tests/test_hr_resolve.py::test_row3_record_without_anchor_snapshot_is_not_drift`。
- **相关**: [hot-reload-held-config.md](hot-reload-held-config.md)(同一轮实报的另一条)、
  `reports/26-09-29-0404-report-hr-verify-v3-audit.html`(v3 审计)。
