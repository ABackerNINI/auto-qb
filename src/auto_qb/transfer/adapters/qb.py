"""qb 目标适配器(D10): 基于 qbittorrent-api 按目标凭据新建独立 Client

不复用主 qB 的连接/QbApi/store —— 转移目标是另一台(同机)qB 实例, 凭据来自
TransferTargetConfig; 客户端构造参数形态参考 core/qbclient.py(超时单点复用)。

per-target 字段键 -> 目标参数映射(capabilities 单点, 键名单点 config.models.TRANSFER_FIELD_KEYS):

  save_path           -> torrents/add save_path(锁死必带, 同机硬约束; 缺失即失败)
  category            -> torrents/add category
  tags                -> torrents/add tags(list 归一)
  share_ratio_limit   -> torrents/add ratio_limit
  seeding_time_limit  -> torrents/add seeding_time_limit
  up_limit            -> torrents/add upload_limit
  down_limit          -> torrents/add download_limit
  super_seeding       -> 添加成功且 hash 可得时 torrents/setSuperSeeding 补一发
                         (torrents/add 无此参数; 不可得/失败只在 reason 注明, 不翻状态)

已存在判定(计划 §03「目标已存在 -> 跳过」): 两条路 ——
  1) 响应文本含已存在类文案(跨版本子串匹配, qB 文案随版本/语言漂移, 尽力而为);
  2) 响应为"全部被拒"且 fields["infohash"] 探针可得时, 到目标查一次同 hash 是否已在
     (单次 torrents_info)。添加被**受理**(Ok./success_count>0)时不再查重 —— 此时
     hash 已在可能是本次添加本身; 精确的添加前查重是 orchestrator(T3) 的预检职责。
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import replace
from typing import Dict, List, Optional

from qbittorrentapi import (
    APIConnectionError,
    Client,
    Conflict409Error,
    LoginFailed,
)

from ...config.models import TRANSFER_FIELD_KEYS
from ...core.qbclient import REQUESTS_TIMEOUT
from .base import AddResult, AddStatus, DownloaderAdapter, TransferAdapterError

logger = logging.getLogger(__name__)


class QbDownloaderAdapter(DownloaderAdapter):
    """qbittorrent 目标: test_connection 真探测(登录+版本), add_torrent 走 torrents/add"""
    def __init__(self, target):
        super().__init__(target)
        self._client_instance: Optional[Client] = None  # 惰性缓存(见 _client); None = 未建

    # ---------- 协议实现 ----------

    def capabilities(self) -> set:
        """qb 支持全部 per-target 字段键(qbittorrent-api 原语齐备, 见模块 docstring 映射表)"""
        return set(TRANSFER_FIELD_KEYS)

    def test_connection(self) -> str:
        """登录 + 取版本; 失败抛 TransferAdapterError(文案可直接回显, 见 base 协议 docstring)"""
        try:
            version = str(self._client().app_version())
        except LoginFailed as exc:
            raise TransferAdapterError(f"目标 {self.target.name}: 登录失败(检查用户名/密码)") from exc
        except APIConnectionError as exc:
            # LoginFailed 在本库版本里是 APIConnectionError 的子类, 必须先捕它
            raise TransferAdapterError(f"目标 {self.target.name}: 无法连接 {self.target.base_url}({exc})") from exc
        except Exception as exc:
            raise TransferAdapterError(f"目标 {self.target.name}: 探测失败({exc})") from exc
        return f"qBittorrent {version}"

    def add_torrent(self, data: bytes, fields: Dict[str, object], skip_check: bool) -> AddResult:
        """torrents/add(multipart 文件上传 .torrent bytes); 三态判定见模块 docstring"""
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise TypeError("add_torrent 需要 .torrent 字节(orchestrator 传参错误)")
        fields = dict(fields or {})
        # 探针 hash: 协议级额外键(见 base 模块 docstring), 不参与 capabilities 判定
        probe_hash = str(fields.pop("infohash", "") or "")
        caps = self.capabilities()
        ignored = tuple(sorted(str(k) for k in fields if k not in caps))

        # save_path 锁死必开(配置校验保证); 适配器再防御一道: 缺失 = 数据不可达, 直接失败
        save_path = str(fields.get("save_path") or "").strip()
        if not save_path:
            return AddResult.failed("保存路径缺失(转移要求必带, 关掉 = 目标侧数据不可达)", ignored_fields=ignored)

        kwargs: Dict[str, object] = {"save_path": save_path, "is_skip_checking": bool(skip_check)}
        for key, arg in _FIELD_TO_ADD_ARG.items():
            value = fields.get(key)
            if value is None or value == "":
                continue
            kwargs[arg] = value
        tags = fields.get("tags")
        if tags:
            normalized_tags = _normalize_tags(tags)
            if normalized_tags:
                kwargs["tags"] = normalized_tags
        want_super_seeding = bool(fields.get("super_seeding"))

        try:
            client = self._client()
            result = client.torrents_add(torrent_files=bytes(data), **kwargs)
        except Exception as exc:
            return self._result_from_exception(exc, probe_hash=probe_hash, ignored=ignored)

        outcome = self._interpret_result(result, probe_hash=probe_hash, ignored=ignored)
        if outcome.status is AddStatus.ADDED and want_super_seeding:
            return self._apply_super_seeding(outcome)
        return outcome

    # ---------- 内部件 ----------

    def _client(self) -> Client:
        """目标客户端(惰性缓存; 测试通过替换单点 _build_client 注入替身)"""
        if self._client_instance is None:
            self._client_instance = self._build_client()
        return self._client_instance

    def _build_client(self) -> Client:
        """按目标凭据新建独立 Client(不复用主 qB 连接; 超时与主链路同一单点)"""
        return Client(
            host=self.target.base_url,
            username=self.target.username or None,
            password=self.target.password or None,
            REQUESTS_ARGS={"timeout": REQUESTS_TIMEOUT},
        )

    def _interpret_result(self, result: object, probe_hash: str, ignored: tuple) -> AddResult:
        """判定 torrents_add 响应 -> AddResult; 两形态都认(qb-api 坑档: 2026-09-24 实证)"""
        if isinstance(result, Mapping):
            success = int(result.get("success_count") or 0)
            failure = int(result.get("failure_count") or 0)
            pending = int(result.get("pending_count") or 0)
            detail = f"成功 {success} / 失败 {failure} / 待定 {pending}"
            ids = list(result.get("added_torrent_ids") or [])
            infohash = str(ids[0]) if ids else ""
            if failure > 0 and (success + pending) == 0:
                # 全部被拒且响应不带原因: 有探针 hash 就到目标查一次同 hash
                if probe_hash and self._hash_exists(probe_hash):
                    return AddResult.skipped("目标已存在(添加被拒且目标查得同 hash)", infohash=probe_hash, ignored_fields=ignored)
                return AddResult.failed(f"目标拒绝添加({detail})", infohash=infohash, ignored_fields=ignored)
            if (success + pending) > 0:
                return AddResult.added(f"目标已受理({detail})", infohash=infohash, ignored_fields=ignored)
            return AddResult.failed(f"目标拒绝添加({detail})", infohash=infohash, ignored_fields=ignored)
        text = str(result)
        if "Ok." in text:
            return AddResult.added("目标已受理", ignored_fields=ignored)
        if _looks_like_duplicate(text):
            return AddResult.skipped(f"目标已存在(响应: {text.strip() or '空响应'})", ignored_fields=ignored)
        return AddResult.failed(f"目标拒绝添加(响应: {text.strip() or '空响应'})", ignored_fields=ignored)

    def _result_from_exception(self, exc: Exception, probe_hash: str, ignored: tuple) -> AddResult:
        """调用异常 -> 三态: 409 里夹带已存在文案 = 跳过; 其余一律失败(原因带异常原文)"""
        if isinstance(exc, Conflict409Error) and _looks_like_duplicate(str(exc)):
            return AddResult.skipped(f"目标已存在({exc})", infohash=probe_hash, ignored_fields=ignored)
        if isinstance(exc, LoginFailed):
            return AddResult.failed("目标登录失败(检查用户名/密码)", infohash=probe_hash, ignored_fields=ignored)
        return AddResult.failed(f"目标添加请求失败({exc})", infohash=probe_hash, ignored_fields=ignored)

    def _hash_exists(self, infohash: str) -> bool:
        """目标是否已有同 hash 种子(单次 torrents_info; 查询失败按不存在处理 ——
        宁可走 failed 保留源, 不把网络噪声升级成误判已存在)"""
        try:
            found = self._client().torrents_info(torrent_hashes=infohash)
        except Exception as exc:  # noqa: BLE001 —— 任何查询故障都按"查不到"处理
            logger.warning("transfer: 目标查重失败(%s), 按不存在处理", exc)
            return False
        return bool(found)

    def _apply_super_seeding(self, outcome: AddResult) -> AddResult:
        """超级做种补一发(torrents/add 无此参数); hash 不可得/调用失败只注明不翻状态"""
        if not outcome.infohash:
            return replace(outcome, reason=_append_note(outcome.reason, "超级做种未应用(目标未回执 hash)"))
        try:
            self._client().torrents_set_super_seeding(enable=True, torrent_hashes=outcome.infohash)
        except Exception as exc:  # noqa: BLE001 —— 添加本身已成功, 超级做种失败不翻状态
            return replace(outcome, reason=_append_note(outcome.reason, f"超级做种应用失败({exc})"))
        return replace(outcome, reason=_append_note(outcome.reason, "已置超级做种"))


# ---------- 模块级纯函数/常量(不依赖实例状态) ----------

# per-target 字段键 -> torrents/add 参数(直接映射部分; save_path/tags/super_seeding 特殊处理)
_FIELD_TO_ADD_ARG = {
    "category": "category",
    "share_ratio_limit": "ratio_limit",
    "seeding_time_limit": "seeding_time_limit",
    "up_limit": "upload_limit",
    "down_limit": "download_limit",
}

# 已存在类响应文案 needle(小写匹配; qB 文案随版本/界面语言漂移, 尽力而为不猜全)
_DUPLICATE_NEEDLES = (
    "already exist",
    "already in use",
    "already added",
    "already in the download",
    "duplicate",
    "已存在",
    "已在下载列表",
)


def _looks_like_duplicate(text: str) -> bool:
    """响应/异常文本是否为「目标已存在」类(needle 子串, 大小写不敏感)"""
    lowered = text.lower()
    return any(needle in lowered for needle in _DUPLICATE_NEEDLES)


def _normalize_tags(tags: object) -> List[str]:
    """tags 归一为非空字符串列表(接受 str 逗号串 / 可迭代; qbittorrent-api 两种都收, 统一 list)"""
    if isinstance(tags, str):
        parts = tags.split(",")
    elif isinstance(tags, (list, tuple, set, frozenset)):
        parts = list(tags)
    else:
        parts = [tags]
    return [str(p).strip() for p in parts if str(p).strip()]


def _append_note(reason: str, note: str) -> str:
    """在回执详情尾追加注记(超级做种降级注明用)"""
    return f"{reason}; {note}" if reason else note
