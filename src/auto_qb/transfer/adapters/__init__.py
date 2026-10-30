"""transfer.adapters: 目标下载器适配器(D10)—— 协议 + 注册表 + qb 实现 + tr stub

调用方单点导入: `from auto_qb.transfer.adapters import create_adapter, AddResult, AddStatus`
"""
from .base import (
    AddResult,
    AddStatus,
    DownloaderAdapter,
    TransferAdapterError,
    UnknownAdapterTypeError,
    adapter_type_known,
    create_adapter,
)
from .qb import QbDownloaderAdapter
from .tr import TrDownloaderStub

__all__ = [
    "AddResult",
    "AddStatus",
    "DownloaderAdapter",
    "TransferAdapterError",
    "UnknownAdapterTypeError",
    "adapter_type_known",
    "create_adapter",
    "QbDownloaderAdapter",
    "TrDownloaderStub",
]
