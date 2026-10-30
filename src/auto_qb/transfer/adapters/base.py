"""DownloaderAdapter 协议 + 添加结果 + 注册表(计划 26-10-31-0306 §04 W2 / 拍板 D10)

协议三方法(键名复用 config.models.TRANSFER_FIELD_KEYS):
- capabilities() -> set[str]: 本适配器支持的字段键集合; add_torrent 对集合外的键降级忽略
- test_connection() -> str: 成功返回版本等描述信息; 失败抛 TransferAdapterError
  (文案面向用户可直接回显; 不返回错误字符串 —— 调用方不用再做成功/失败分流)
- add_torrent(data: bytes, fields: dict, skip_check: bool) -> AddResult: 业务失败一律
  返回失败态 AddResult 而非抛异常(调用方逐种子结算, 单种子失败不中断批次, D6);
  只有参数错用(如 data 非字节)等编程错误才抛。

fields 约定: 键 = TRANSFER_FIELD_KEYS 子集(值为该字段要下发的当前值); 额外允许键
"infohash" —— orchestrator 供给的源种子 hash, 仅作「目标已存在」探针, 不参与
capabilities 判定、不进 ignored_fields、不向目标下发。
"""
from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, Tuple

from ...infra.errors import AutoQbError

if TYPE_CHECKING:
    from ...config.models import TransferTargetConfig


class TransferAdapterError(AutoQbError):
    """适配器层故障(连接/登录/探测失败): AutoQbError 子类, 走 CLI 统一出口"""


class UnknownAdapterTypeError(TransferAdapterError):
    """注册表收到未知 target.type(配置校验本应拦住, 这里是防御兜底)"""


class AddStatus(str, Enum):
    """add_torrent 三态(计划 §03 失败分类的前置; W3 回执 {hash, 状态, 原因} 的状态源)"""
    ADDED = "added"  # 成功添加
    SKIPPED = "skipped"  # 目标已存在, 跳过(不是失败; 源按 orchestrator 规则保留)
    FAILED = "failed"  # 添加失败


@dataclass(frozen=True)
class AddResult:
    """add_torrent 结果: 三态 + 原因 + 目标 hash(可得时)+ 被降级忽略的字段键

    status: 三态(见 AddStatus)
    reason: 原因/详情一句话(成功时是回执详情, 如受理计数; 失败/跳过时是面向用户的解释)
    infohash: 目标侧 hash, 仅当目标回执可得(新 WebAPI added_torrent_ids / 探针命中)时非空
    ignored_fields: capabilities 不含而被忽略的字段键(降级注明, 计划 §03「目标不支持的字段
      由 adapter 降级并在结果注明」); 注意 save_path 锁死必开, 不在降级之列 —— 缺失即失败
    """

    status: AddStatus
    reason: str = ""
    infohash: str = ""
    ignored_fields: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """added/skipped 都算「这条种子处理完了」; 只有 failed 才是失败(D6 不中断批次)"""
        return self.status is not AddStatus.FAILED

    @classmethod
    def added(cls, reason: str = "", infohash: str = "", ignored_fields: Tuple[str, ...] = ()) -> "AddResult":
        return cls(AddStatus.ADDED, reason=reason, infohash=infohash, ignored_fields=ignored_fields)

    @classmethod
    def skipped(cls, reason: str = "", infohash: str = "", ignored_fields: Tuple[str, ...] = ()) -> "AddResult":
        return cls(AddStatus.SKIPPED, reason=reason, infohash=infohash, ignored_fields=ignored_fields)

    @classmethod
    def failed(cls, reason: str = "", infohash: str = "", ignored_fields: Tuple[str, ...] = ()) -> "AddResult":
        return cls(AddStatus.FAILED, reason=reason, infohash=infohash, ignored_fields=ignored_fields)


class DownloaderAdapter(ABC):
    """目标下载器适配器协议(D10): 每个实例绑定一个 TransferTargetConfig

    实现注意: add_torrent 内不得触碰源 qB(本层只有目标一个方向); 业务失败返回
    AddResult.failed, 不抛 —— 异常只留给编程错误。
    """
    def __init__(self, target: "TransferTargetConfig"):
        self.target = target

    @abstractmethod
    def capabilities(self) -> set:
        """本适配器支持的字段键集合(键名 = TRANSFER_FIELD_KEYS 子集); add_torrent 对
        集合外的键降级忽略并写进 AddResult.ignored_fields"""

    @abstractmethod
    def test_connection(self) -> str:
        """真实探测目标(登录 + 取版本): 成功返回描述信息(如 "qBittorrent v5.2.3"),
        失败抛 TransferAdapterError(文案可直接回显给用户)"""

    @abstractmethod
    def add_torrent(self, data: bytes, fields: Dict[str, object], skip_check: bool) -> AddResult:
        """向目标添加 .torrent(字节); fields 形状见模块 docstring; skip_check=True 时
        目标侧不做重校验(仅对已完成种子, 由 orchestrator 决策, 本层透传)"""


# 注册表: target.type -> (adapters 包内模块名, 类名)。类惰性导入 —— base 不反依赖各实现,
# 实现模块反向 import base 不构成环; 新类型在这里加一行 + config 校验枚举同步。
_ADAPTER_TYPES: Dict[str, Tuple[str, str]] = {
    "qb": ("qb", "QbDownloaderAdapter"),
    "tr": ("tr", "TrDownloaderStub"),
}


def create_adapter(target: "TransferTargetConfig") -> DownloaderAdapter:
    """按 target.type 实例化适配器(D10 注册表单点); 未知类型抛 UnknownAdapterTypeError"""
    entry = _ADAPTER_TYPES.get(target.type)
    if entry is None:
        raise UnknownAdapterTypeError(f"未知的目标下载器类型: {target.type!r}(已知: {', '.join(sorted(_ADAPTER_TYPES))})")
    module_name, class_name = entry
    module = importlib.import_module(f".{module_name}", __package__)
    adapter_cls = getattr(module, class_name)
    return adapter_cls(target)


def adapter_type_known(type_name: str) -> bool:
    """type 是否在注册表内(供调用方在不实例化的情况下预检; 校验层枚举另有单点)"""
    return type_name in _ADAPTER_TYPES
