# 挂钟严格推进断言的本机粒度坍缩: 背靠背 time.time() 同值

> 摘要: 挂钟严格推进断言的本机粒度坍缩: 背靠背 time.time() 同值(判别须追基线值来源 —— 活钟读数才中招, 夹具常量天然稳, 2026-10-22 实证误报一例)
> 等级: L0
> 触发: ts 推进, time.time 同值, 背靠背, 粒度坍缩, 严格大于断言, 递增假钟, monkeypatch time, flaky, traffic_view, _publish
**Refs:** memory-bank/testing/baselines/26-10-22-0121-time-tick-collapse-strict-advance.md

### `assert view["ts"] > before_ts` 类「严格推进」断言在本机背靠背 time.time() 同值下必 flaky

- **触发**: 用例拿 `before = X["ts"]`(由前一次 `_publish` 写下的 `time.time()`), 再触发一次发布, 断言 `X["ts"] > before`。本机(Windows)背靠背两次 `time.time()` 常返回**同一值**(亚 µs 粒度坍缩), 只要两次发布之间没跨过一个时钟刻度, 断言就红。与午夜窗口无关, 任何时段随机现形。
- **判别**: 失败信息是 `assert 1792602646.627729 > 1792602646.627729` —— 两个值**完全相同**而非相差几毫秒(那是 timing-tolerance 的 OS 刻度余量形态, 不同根); 单跑偶发、全量/提交闸门负载下必现; 干净树无插件也红。
  **锚点(防误报, 2026-10-22 实证)**: 只 pattern-match 断言形状 `X["ts"] > before` **会误报** —— 必须先追基线值的**来源**: `tests/test_traffic_monitor_client.py:641` 形状完全相同, 但 `ts_before` 取自 `_refresh_env` 种进视图的**字面量 1.0**(探针实测), 断言实为 `新发布 ts > 1.0`, 天然稳, 无需修。判别法: 看 before 值是上一次 `_publish` 写的活钟读数(中招), 还是夹具种下的常量(安全)。
- **处置**: 钉一个**每次调用 +1.0s 的严格递增假钟**(`monkeypatch.setattr(time, "time", ...)`, 起始值取一次真钟), 覆盖该用例全部发布路径 —— 发布不少 1 次就严格推进; 一次都不发布(补丁失效)则 ts 一字不动, 断言仍拦得住, 判别力不损失。**不要**改 `>=`(会把「ts 没刷新」这个真缺陷放行)也不要 `before - 1`(同理失去判别力)。红验: 假钟临时改回常量, 断言必须精确复现原 flake 形状。
- **守阵**: `tests/test_traffic_snapshot.py::test_publish_event_patches_day_row_without_reading`(2026-10-22 修复: 提交闸门里现形, 挡下一笔提交; 修后连跑 20 遍全绿, 常量钟红验通过)。
- **复发**: 0
