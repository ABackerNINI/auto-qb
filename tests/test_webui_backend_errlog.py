"""WEBUI 错误历史后端(S2): auto_qb logger 的 WARNING+ 内存错误环 + /api/errlog 只读增量端点

环本体与 seq 计数器是 WebUIRuntime 字段(tray/app.py UiLogHandler 同款范式: handler 持
引用写, emit 全程静默); 端点在 system.py 只读增量。环纯内存零磁盘触点, seq 进程内计数
(重启回零, 重启判定在客户端)。

## 测试计划
- test_levels_gate: DEBUG/INFO 不入环; WARNING/ERROR 入环
- test_ring_cap_evicts_oldest: 第 201 条挤掉最旧(cap 200 环形语义)
- test_after_increment_and_last: after 增量与 last 字段正确(含 after > last 回空)
- test_msg_truncate_and_multiline: msg 超长截断 500 字符 + 多行合一
- test_errlog_requires_token: 无 token 请求 /api/errlog 返回 401
- test_pure_memory_no_disk: 纯内存守阵 —— 错误环实现零磁盘触点(静态断言)
- test_attach_idempotent: handler 挂接幂等 —— start_server 重复调用不重复挂(抽出的
  attach_err_log_handler 可独立调用, 用 logger.handlers 计数断言; 兼验真实 logger 链路)
"""
import inspect
import logging
import re
from types import SimpleNamespace

import pytest

from auto_qb.webui.runtime import WEB_ERR_MSG_MAX, WEB_ERR_RING_MAX, WebErrLogHandler, WebUIRuntime


def _runtime() -> WebUIRuntime:
    """最小 host 替身的门面(错误环不触 host)"""
    return WebUIRuntime(SimpleNamespace())


def _record(levelno: int, msg, args=()) -> logging.LogRecord:
    """构造直达 handler.emit 的日志记录(绕开全局 logger, 不污染其它用例)"""
    return logging.LogRecord(
        name="auto_qb.test", level=levelno, pathname=__file__, lineno=1, msg=msg, args=args, exc_info=None
    )


def _emit(rt: WebUIRuntime, levelno: int, msg, args=()) -> None:
    WebErrLogHandler(rt).emit(_record(levelno, msg, args))


def test_levels_gate():
    """DEBUG/INFO 不入环; WARNING/ERROR/CRITICAL 入环且形状 {seq, ts, level, msg}"""
    import time as _time

    rt = _runtime()
    _emit(rt, logging.DEBUG, "debug 不入环")
    _emit(rt, logging.INFO, "info 不入环")
    assert rt.err_log_ring.maxlen == WEB_ERR_RING_MAX == 200
    assert len(rt.err_log_ring) == 0 and rt.err_log_seq == 0

    before = _time.time()
    _emit(rt, logging.WARNING, "warn 入环")
    _emit(rt, logging.ERROR, "error 入环")
    _emit(rt, logging.CRITICAL, "critical 入环")
    assert rt.err_log_seq == 3 and len(rt.err_log_ring) == 3
    for i, e in enumerate(rt.err_log_ring, start=1):
        assert set(e) == {"seq", "ts", "level", "msg"}
        assert e["seq"] == i and before - 1 <= e["ts"]
    assert [e["level"] for e in rt.err_log_ring] == ["WARNING", "ERROR", "CRITICAL"]


def test_ring_cap_evicts_oldest():
    """第 201 条挤掉最旧: 环保持 200 条, seq 继续单调递增"""
    rt = _runtime()
    for i in range(1, WEB_ERR_RING_MAX + 2):  # 201 条
        _emit(rt, logging.WARNING, f"第 {i} 条")
    assert len(rt.err_log_ring) == WEB_ERR_RING_MAX == 200
    assert rt.err_log_seq == 201
    assert rt.err_log_ring[0]["seq"] == 2, "seq=1 的最旧条目必须被挤掉"
    assert rt.err_log_ring[-1]["seq"] == 201


def test_after_increment_and_last():
    """after 增量: 只回 seq > after; last 恒为当前最大 seq; after > last 回空"""
    rt = _runtime()
    for i in range(1, 4):
        _emit(rt, logging.WARNING, f"e{i}")

    items, last = rt.err_log_since(0)
    assert [e["seq"] for e in items] == [1, 2, 3] and last == 3
    items, last = rt.err_log_since(2)
    assert [e["seq"] for e in items] == [3] and last == 3
    items, last = rt.err_log_since(3)
    assert items == [] and last == 3
    # after 大于当前 last(后端重启回零后客户端持旧游标的形态): 如实回空
    items, last = rt.err_log_since(99)
    assert items == [] and last == 3
    # 增量读取是纯读: 环与 seq 不被消费性改变
    assert rt.err_log_seq == 3 and len(rt.err_log_ring) == 3


def test_msg_truncate_and_multiline():
    """msg 超长截断 500 字符 + 多行合一(换行/空白折叠成空格, 收集时一次处理)"""
    rt = _runtime()
    _emit(rt, logging.WARNING, "a\nbb\r\nccc")
    assert rt.err_log_ring[-1]["msg"] == "a bb ccc"
    _emit(rt, logging.WARNING, "A" * (WEB_ERR_MSG_MAX + 100))
    assert len(rt.err_log_ring[-1]["msg"]) == WEB_ERR_MSG_MAX == 500
    # 多行 + 超长叠加: 先合一再截断, 结果恒单行且不超限
    _emit(rt, logging.ERROR, ("x" * 60 + "\n") * 12)
    e = rt.err_log_ring[-1]["msg"]
    assert len(e) == 500 and "\n" not in e and "\r" not in e
    # 带参数的消息照常插值
    _emit(rt, logging.WARNING, "失败 %s 个", (3, ))
    assert rt.err_log_ring[-1]["msg"] == "失败 3 个"


def test_errlog_requires_token():
    """无 token / 错 token 请求 /api/errlog 返回 401(鉴权走 factory 全局 dependencies 单点)"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = SimpleNamespace(
        config=SimpleNamespace(
            web=SimpleNamespace(enabled=True, host="127.0.0.1", port=8080, token="", skip_local_verify=False)
        )
    )
    mgr.web = WebUIRuntime(SimpleNamespace())
    mgr.web.token = "errlog-test-token"
    client = TestClient(create_app(mgr))
    assert client.get("/api/errlog").status_code == 401
    assert client.get("/api/errlog?after=0").status_code == 401
    assert client.get("/api/errlog", headers={"Authorization": "Bearer wrong"}).status_code == 401
    # 密钥正确: 200 + 端点形状(items / last)
    WebErrLogHandler(mgr.web).emit(_record(logging.WARNING, "走端点可见"))
    r = client.get("/api/errlog", headers={"Authorization": "Bearer errlog-test-token"})
    assert r.status_code == 200
    body = r.json()
    assert body["last"] == 1 and len(body["items"]) == 1 and body["items"][0]["msg"] == "走端点可见"


def test_pure_memory_no_disk():
    """纯内存守阵: 错误环全链路(handler/环/端点)源码零磁盘触点

    静态断言(WEBUI 错误历史 §06 口径): 取 emit / append_err / err_log_since /
    attach_err_log_handler / api_errlog 五段源码, 禁出现任何写盘或持久化路径。
    """
    from auto_qb.webui.server.routes import system

    forbidden = ("open(", "state_file", "FileHandler", "os.remove", "makedirs", "atomic_write", "shutil", "Path(")
    sources = {
        "emit": inspect.getsource(WebErrLogHandler.emit),
        "append_err": inspect.getsource(WebUIRuntime.append_err),
        "err_log_since": inspect.getsource(WebUIRuntime.err_log_since),
        "attach_err_log_handler": inspect.getsource(WebUIRuntime.attach_err_log_handler),
    }
    src = inspect.getsource(system)
    m = re.search(r'@router\.get\("/api/errlog"\).*?(?=\n    @router\.|\n    return router)', src, re.S)
    assert m, "system.py 里找不到 api_errlog(端点被挪走? 守阵同步更新)"
    sources["api_errlog"] = m.group(0)
    for name, text in sources.items():
        for token in forbidden:
            assert token not in text, f"错误环链路 {name} 出现磁盘触点 {token!r} —— 环必须保持纯内存"


def test_attach_idempotent():
    """挂接幂等: attach 重复调用不重挂(logger.handlers 计数); 兼验真实 logger 链路入环

    计数只认属于本 runtime 的 handler: 其它用例(如 facade 的 start_server 用例)在同一
    worker 进程也会经 start_server 挂自己的 handler, 那是各自的进程级环, 不属本断言面。
    """
    rt = _runtime()
    lg = logging.getLogger("auto_qb")

    def _mine():
        return [h for h in lg.handlers if isinstance(h, WebErrLogHandler) and getattr(h, "_runtime", None) is rt]

    try:
        rt.attach_err_log_handler()
        rt.attach_err_log_handler()
        rt.attach_err_log_handler()
        assert len(_mine()) == 1, "重复挂接必须被幂等闸挡住"
        assert rt._err_log_handler is _mine()[0]
        # 真实 logger 链路: attach 后 auto_qb 命名空间的 WARNING 经传播进本 runtime 的环
        logging.getLogger("auto_qb.err_probe").warning("挂接链路探针")
        logging.getLogger("auto_qb.err_probe").info("INFO 不该入环")
        assert [e["msg"] for e in rt.err_log_ring] == ["挂接链路探针"]
    finally:
        lg.removeHandler(rt._err_log_handler)
    assert _mine() == []


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
