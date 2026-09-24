"""test_logging: setup_logging 控制台/文件 handler 配置

计划覆盖:
- test_setup_logging_console_only: file 为空 -> 仅 console handler, 不建文件
- test_setup_logging_file_handler: file 给定 -> 自动 makedirs 子目录 + RotatingFileHandler, 启动日志写入文件
- test_setup_logging_file_no_dir: file 无目录部分 -> 跳过 makedirs 直接建文件
- test_setup_logging_level_and_format: root level 与 format 按参数生效
- test_setup_logging_file_always_debug: 文件 handler 跟随 level, auto_qb 放开/qbittorrentapi 封顶 INFO
- test_filter_log_lines_follows_format_shape: 按格式串定位等级名(默认方括号 / 生产的破折号 / 带宽度字段名), 大小写不敏感, 空 level 全返
- test_filter_log_lines_keeps_multiline_record: 多行记录(整段 traceback)的续行跟随其记录的取舍
- test_filter_log_lines_unfilterable_returns_note: 格式无等级字段 / 已存行与格式不符 -> 回全部行 + note, 不静默给空
- test_filter_log_lines_custom_field_specs: 字段宽度/数字/字面量 %% 等格式变体不影响等级定位

注意: setup_logging 操作 root logger(清空并重建 handlers), 每个测试尾部必须恢复
root level(WARNING)并清空 handlers, 避免污染同批其它测试的日志行为。
"""
import logging
import os
import tempfile
from logging.handlers import RotatingFileHandler

from auto_qb.config.models import LoggingConfig
from auto_qb.infra.logging import NOTE_FORMAT_MISMATCH, NOTE_NO_LEVEL_FIELD, filter_log_lines, setup_logging

_WARNING = logging.WARNING  # 30

_DEFAULT_FMT = LoggingConfig().format  # 未配置 log.format 时的默认(等级带方括号)
_DASH_FMT = "%(asctime)s - %(levelname)s - %(message)s"  # 生产 config.yml 同形(无方括号)


def _lines(fmt, recs):
    """按 fmt 渲染真实日志行(等级过滤的输入一律是格式化后的文本)"""
    fmtr = logging.Formatter(fmt)
    return [fmtr.format(logging.LogRecord(n, lv, "f.py", 1, msg, None, None)) for n, lv, msg in recs]


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


def test_filter_log_lines_follows_format_shape():
    """等级名在行里的形状由 format 决定 —— 必须按格式串定位, 不能按 `[WARNING` 这类字面量捞"""
    recs = [
        ("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试"),
        ("auto_qb.core.z", logging.ERROR, "校验失败")
    ]
    for fmt in (_DEFAULT_FMT, _DASH_FMT, "%(levelname)s|%(asctime)s|%(message)s"):
        lines = _lines(fmt, recs)
        assert filter_log_lines(fmt, lines, "") == (lines, ""), fmt  # 空 level = 不过滤
        for lv, want in (("INFO", lines[0]), ("WARNING", lines[1]), ("ERROR", lines[2])):
            assert filter_log_lines(fmt, lines, lv) == ([want], ""), (fmt, lv)
            assert filter_log_lines(fmt, lines, lv.lower()) == ([want], ""), (fmt, lv)  # 大小写不敏感
        assert filter_log_lines(fmt, lines, "DEBUG") == ([], ""), fmt  # 没有 DEBUG 行 -> 空且不带 note


def test_filter_log_lines_keeps_multiline_record():
    """多行记录: 解析不出的行按上一记录的续行处理(traceback 每行都带不上等级标记)"""
    header = _lines(_DEFAULT_FMT, [("auto_qb.core", logging.ERROR, "主循环异常: boom")])[0]
    tail_lines = ["Traceback (most recent call last):", '  File "x.py", line 1', "RuntimeError: boom"]
    nxt = _lines(_DEFAULT_FMT, [("auto_qb.core", logging.INFO, "下一轮")])[0]
    lines = [header] + tail_lines + [nxt]

    assert filter_log_lines(_DEFAULT_FMT, lines, "ERROR") == ([header] + tail_lines, "")
    assert filter_log_lines(_DEFAULT_FMT, lines, "INFO") == ([nxt], ""), "续行不得被当成独立记录带走"
    # 首行不可解析(文件从中间被 tail 截断): 等级未知, 归哪一条都不对 -> 丢掉
    assert filter_log_lines(_DEFAULT_FMT, tail_lines + lines, "ERROR") == ([header] + tail_lines, "")


def test_filter_log_lines_unfilterable_returns_note():
    """两种"筛不了"必须回全部行 + note: 空结果与筛选失效在界面上不能长得一样"""
    lines = _lines(
        _DEFAULT_FMT, [("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试")]
    )
    # ①格式里没有等级字段 -> 等级无从判定
    assert filter_log_lines("%(asctime)s %(message)s", lines, "WARNING") == (lines, NOTE_NO_LEVEL_FIELD)
    # ②格式有等级字段, 但行是另一种格式(改了 format, 旧行还在)
    assert filter_log_lines("%(levelname)s %(message)s", lines, "WARNING") == (lines, NOTE_FORMAT_MISMATCH)
    # 空文件不报"筛不了"(确实没有内容, 不是筛不了)
    assert filter_log_lines(_DEFAULT_FMT, [], "WARNING") == ([], "")


def test_filter_log_lines_custom_field_specs():
    """字段宽度/数字类型/字面量 %% 等格式变体不得影响等级定位"""
    for fmt in (
        "%(asctime)s | %(name)-20s | %(levelname)-8s | %(lineno)d | %(message)s", "%(levelname)s%% %(message)s",
        "%(asctime)s %(levelname)s %(message)s"
    ):
        hit = _lines(fmt, [("auto_qb.core.mixins", logging.WARNING, "连接重试")])[0]
        miss = _lines(fmt, [("auto_qb.core.mixins", logging.INFO, "启动完成")])[0]
        assert filter_log_lines(fmt, [miss, hit], "WARNING") == ([hit], ""), fmt
        assert filter_log_lines(fmt, [miss, hit], "INFO") == ([miss], ""), fmt
