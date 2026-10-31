# 4353 passed, 2 skipped (coverage 99%: 21823 stmts, 145 miss, 7398 br, 122 pb) —— qB 断连稳态守卫落地(issue 26-10-31-1029)

> 摘要: 主循环断连稳态守卫 —— client=None+_last_conn_ok=False 时跳过请求线走 _reconnect_due 重连 + 恢复检测改 _ran_line 门; 新用例红绿双验
> 基线时间: 2026-11-01 02:28

## 验收数字

`commands run test.full` (229.5s, 2026-11-01 实测):

```text
TOTAL                                                21823    145   7398    122    99%
4353 passed, 2 skipped in 226.43s (0:03:46)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。
skipped 与上条切片同环境口径(node/平台性跳过, 本轮 2 条)。

## 本改动面

- `src/auto_qb/core/qbmanager.py`: 主循环加断连稳态守卫 —— 分派线之前判 `client is None and self._last_conn_ok is False`(二元组判据: `_last_conn_ok=False` 只由断连转换单点 `_note_conn_failed` 置位, 单看 client=None 会误伤启动/热重载窗口), 命中即跳过全部请求线, 直接 `_reconnect_due` → `connect()`(成功后本轮立即补一次同步), 两条时间线照常推进(防空转, 26-10-02-0728 同款判据); 「连接恢复检测」的门从 `sync_due/tick_due` 改为新增局部旗标 `_ran_line`(本轮真有线跑成功) —— 守卫轮两条 due 都可为真却没线跑, 照旧翻转会把守卫下一轮绕开。
- `tests/test_qbmanager.py`: 新增 `test_run_client_none_reconnects_without_error_spam`(断连稳态跳线/重连/补同步/「已重新连接」INFO/无「主循环异常」刷屏五断言; 红验兜底 60 拍置停止信号防修复前挂死); `test_connect_throttle_repeated_failures` 的 connect 替身补「成功即落非 None client」语义(与真实现同构, 否则守卫把 None client 拦在请求线之外, 三次线级失败序列走不到); 头部测试计划同步。
- 红验: 守卫条件临时短路(False and …)后新用例判红 —— `_tick` 逐拍 60 次(AttributeError 路径无出口、connect 不再被调), 与 issue 现场一致; 还原后绿。
- 真机 RM02-07 回归(断 75s+恢复)未跑(需真实 qB + 本地 TCP 代理环境), 单测面已覆盖等价时序。
