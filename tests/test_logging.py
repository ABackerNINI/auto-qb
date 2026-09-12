"""test_logging: setup_logging 控制台/文件 handler 配置

计划覆盖:
- test_setup_logging_console_only: file 为空 -> 仅 console handler, 不建文件
- test_setup_logging_file_handler: file 给定 -> 自动 makedirs 子目录 + RotatingFileHandler, 启动日志写入文件
- test_setup_logging_file_no_dir: file 无目录部分 -> 跳过 makedirs 直接建文件
- test_setup_logging_level_and_format: root level 与 format 按参数生效
- test_setup_logging_file_always_debug: 文件 handler 跟随 level, auto_qb 放开/qbittorrentapi 封顶 INFO

注意: setup_logging 操作 root logger(清空并重建 handlers), 每个测试尾部必须恢复
root level(WARNING)并清空 handlers, 避免污染同批其它测试的日志行为。
"""
import logging
import os
import tempfile
from logging.handlers import RotatingFileHandler

from auto_qb.logging import setup_logging

_WARNING = logging.WARNING  # 30


def _reset_root():
    """关闭/清空 root handlers 并重置 level(WARNING)

    必须在 setup_logging 前紧贴调用: pytest logging 插件会在 fixture 阶段之后
    往 root 注入 handler, 使 basicConfig(level=...) 静默失效(handlers 非空时不
    重设 root level), 导致启动 INFO 被过滤。
    """
    root = logging.getLogger()
    for h in root.handlers:
        h.close()
    root.handlers.clear()
    root.setLevel(_WARNING)


def _restore_root():
    """关闭并移除 root 全部 handlers, 恢复 root level(WARNING)

    必须 close 释放文件句柄, 否则 Windows 下 TemporaryDirectory 清理会失败。
    """
    root = logging.getLogger()
    for h in root.handlers:
        h.close()
    root.handlers.clear()
    root.setLevel(_WARNING)


def test_setup_logging_console_only():
    """file 为空: 只加 console handler, 不创建文件"""
    try:
        _reset_root()
        setup_logging(file="", level=logging.INFO, max_bytes=1024, format="%(message)s")
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)
        assert root.level == logging.INFO
        # 第三方 logger 作用域: qbittorrentapi 封顶 INFO; urllib3 封顶 ERROR(排除断连 Retry 刷屏)
        assert logging.getLogger("qbittorrentapi").level == logging.INFO
        assert logging.getLogger("urllib3").level == logging.ERROR
    finally:
        _restore_root()


def test_setup_logging_file_handler():
    """file 给定: 自动建子目录 + RotatingFileHandler, 启动信息写入文件"""
    with tempfile.TemporaryDirectory() as td:
        log_file = os.path.join(td, "logs", "nested", "app.log")
        try:
            _reset_root()
            setup_logging(file=log_file, level=logging.DEBUG, max_bytes=2048, format="%(levelname)s %(message)s")
            root = logging.getLogger()
            handlers = root.handlers
            assert len(handlers) == 2, f"console + file 两个 handler: {handlers}"
            file_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
            assert len(file_handlers) == 1
            assert file_handlers[0].maxBytes == 2048
            assert file_handlers[0].backupCount == 5
            assert os.path.exists(log_file), "深层子目录应被 makedirs 自动创建"
            with open(log_file, encoding="utf-8") as f:
                assert "日志初始化完成" in f.read()
        finally:
            _restore_root()


def test_setup_logging_level_and_format():
    """root level 按参数设置; 低于 level 的日志被过滤"""
    try:
        _reset_root()
        setup_logging(file="", level=logging.WARNING, max_bytes=1024, format="%(message)s")
        root = logging.getLogger()
        assert root.level == logging.WARNING
        # WARNING 级过滤 INFO: 无 INFO 记录
        info_handler = root.handlers[0]
        assert info_handler.level == logging.WARNING
    finally:
        _restore_root()


def test_setup_logging_file_no_dir():
    """file 不含目录部分(纯文件名): 跳过 makedirs, 直接在 cwd 建文件"""
    old_cwd = os.getcwd()
    td_ctx = tempfile.TemporaryDirectory()
    td = td_ctx.__enter__()
    try:
        os.chdir(td)
        _reset_root()
        setup_logging(file="app.log", level=logging.DEBUG, max_bytes=1024, format="%(message)s")
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert os.path.exists(os.path.join(td, "app.log"))
    finally:
        _restore_root()
        os.chdir(old_cwd)  # 先切回, 避免清理期间 cwd 被占用
        td_ctx.__exit__(None, None, None)


def test_setup_logging_file_always_debug():
    """配置 level=INFO 时文件 handler 跟随 level(auto_qb 放开 DEBUG 穿透);
    auto_qb 放开 DEBUG, qbittorrentapi 封顶 INFO(排除请求/响应噪音)"""
    with tempfile.TemporaryDirectory() as td:
        log_file = os.path.join(td, "app.log")
        try:
            _reset_root()
            setup_logging(file=log_file, level=logging.INFO, max_bytes=1024, format="%(message)s")
            root = logging.getLogger()
            assert root.level == logging.INFO, "root 跟随配置(拦截第三方 DEBUG)"
            file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
            assert file_handlers and file_handlers[0].level == logging.INFO, "文件 handler 跟随 level"
            assert logging.getLogger("auto_qb").level == logging.DEBUG
            assert logging.getLogger("qbittorrentapi").level == logging.INFO, "qbt DEBUG 噪音排除"
            # 行为验证: auto_qb DEBUG 被文件 handler 过滤(level=INFO), 不写入
            logging.getLogger("auto_qb.test").debug("debug-probe")
            logging.getLogger("auto_qb.test").info("info-probe")
            with open(log_file, encoding="utf-8") as f:
                content = f.read()
                assert "info-probe" in content, "auto_qb INFO 应写入文件"
                assert "debug-probe" not in content, "auto_qb DEBUG 不应写入文件(level=INFO)"
        finally:
            # setup_logging 修改了两个子 logger 的 level, 测试尾部一并恢复(继承 root)
            logging.getLogger("auto_qb").setLevel(logging.NOTSET)
            logging.getLogger("qbittorrentapi").setLevel(logging.NOTSET)
            _restore_root()
