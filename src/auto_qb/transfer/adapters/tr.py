"""tr(Transmission)目标 stub(D10): 只留接口, 不做假接口

test_connection 返回「暂未实现」前缀文案(而非抛异常) —— D10 口径「test 即暂未实现」;
add_torrent 抛 NotImplementedError(orchestrator 未接该类型, 到这一层即编程错误);
capabilities 空集。真实现进来时替换本文件并同步注册表与校验枚举。
"""
from __future__ import annotations

from typing import Dict

from .base import AddResult, DownloaderAdapter

_NOT_IMPLEMENTED_TEXT = "暂未实现: Transmission 目标暂不支持转移(当前版本仅支持 qBittorrent 目标)"


class TrDownloaderStub(DownloaderAdapter):
    """Transmission 目标占位(D10): 拒绝一切执行动作, 零网络行为"""
    def capabilities(self) -> set:
        """空集 = 不支持任何字段(不做假接口)"""
        return set()

    def test_connection(self) -> str:
        """恒返回「暂未实现」前缀文案(不联网; 调用方按不可用处理)"""
        return _NOT_IMPLEMENTED_TEXT

    def add_torrent(self, data: bytes, fields: Dict[str, object], skip_check: bool) -> AddResult:
        raise NotImplementedError(_NOT_IMPLEMENTED_TEXT)
