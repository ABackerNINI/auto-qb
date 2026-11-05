# 主循环测试的 connect 替身: 返回 True 必须同时落非 None client

> 摘要: QbManager.run() 主循环用例里把 `connect` mock 成 `return True` 却不给 `mgr.client` 落值, 在断连稳态守卫(26-10-31-1029)生效后会让请求线被整段静默跳过 —— 用例不报错, 断言以「线没跑」的形态假红/假绿。
> 触发: 写或改 run() 主循环测试, mock/替换 connect; 或改断连守卫判据后跑主循环用例

### 条目

- **触发**: 主循环测试用 `mgr.connect = mock.Mock(return_value=True)`(或 `lambda: True`)让启动首连直通, 但没像真 `connect()` 一样留下非 None client —— manager 初始 client 就是 None。
- **判别**: 症状是「静默不跑」而非报错 —— 守卫轮两条件(`client is None and _last_conn_ok is False`)在断连转换后命中, 请求线整段被跳过, `_tick`/`_refresh_torrents` 的调用次数/序列与断言对不上; 尤其注意 connect 替身每次被调都该落 client(断连→重连成功后线要恢复)。
- **处置**: connect 替身与真实现同构 —— 成功路径给 `mgr.client` 落非 None 替身(见 `tests/test_qbmanager_connect.py::test_connect_throttle_repeated_failures` 的 `fake_connect`); 需要「重连仍失败」场景就让替身返回 False 且不落 client(对应真实现中 `new_client` 抛 APIConnectionError、client 保持 None)。
- **守阵**: `test_run_client_none_reconnects_without_error_spam` 锁守卫行为本身; 主循环既有用例的 connect 替身已逐一核对过落值。
