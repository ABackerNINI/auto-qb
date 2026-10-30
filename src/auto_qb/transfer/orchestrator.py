"""种子转移编排器(计划 26-10-31-0306 §03 单种子执行流水 / §04 W2 / 拍板 D1/D2/D5/D6/D8/D9)

单种子流水: 状态门 -> 源 export -> 字段采集 -> 路径映射 -> 跳检决策
-> adapter.add_torrent -> 验证轮询 -> (after_state=paused 暂停目标) -> 删源。

不变量(违反即错, 计划 §01):
- 数据文件永不移动、永不删除 —— 删源只删任务(torrents_delete delete_files=False 恒定);
- 任何不成功路径不碰源 —— 门拦/export 败/已存在/添加败/验证超时/目标 error 一律保留源;
- 未完成种子绝不以跳检形式添加 —— progress < 100% 时跳检逐条自动降级为校验添加(D8);
- 单一写线程假设: 本模块纯串行逐种子, 不引入线程/并发(D6)。

实现选型(验证轮询): 经 adapter 扩展点 —— QbDownloaderAdapter.find_torrent(本任务在
qb adapter 上新增的具体方法, 不进 ABC 协议); orchestrator 经 getattr 探测, 适配器没有
该方法即按「不支持验证」失败并保源(绝不无验证删源)。轮询时间可控: sleep 与超时均为
构造参数, 测试注入假 sleep/极短超时, 不真等。

结果结构(状态枚举单点, W3 回执直接用): TorrentTransferResult {hash, status, reason, code};
W3 回执 {hash, 状态: status.label(成功/跳过/失败), 原因: reason}。失败/跳过分类单点 =
TransferOutcomeCode。批次不中断(D6): 逐种子全兜底, 单种子未预期异常只结算本条。

状态语义(门拦 = 跳过而不是失败): 下载管线态/missingFiles/未知状态属「不可转移」的预期
拒绝, 与 W4 确认弹窗预检「将跳过及原因」同口径; 已存在同样归跳过; 其余(export 败/添加败/
认证败/验证超时/目标 error/未预期)才是失败。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..config.models import TRANSFER_FIELD_KEYS, TransferTargetConfig
from .adapters import AddStatus, create_adapter

if TYPE_CHECKING:
    from ..core.qbapi import QbApi
    from .adapters import DownloaderAdapter

logger = logging.getLogger(__name__)

# ---------- 结果结构(单点, W3 回执直接用) ----------


class TransferStatus(str, Enum):
    """逐种子结果三态(计划 §03/W3 回执口径: 成功/跳过/失败)"""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"

    @property
    def label(self) -> str:
        """中文展示名(回执/toast 直接用)"""
        return _STATUS_LABELS[self]


_STATUS_LABELS = {
    TransferStatus.SUCCESS: "成功",
    TransferStatus.SKIPPED: "跳过",
    TransferStatus.FAILED: "失败",
}


class TransferOutcomeCode(str, Enum):
    """逐种子结果分类单点(失败分类 + 跳过分类; 成功不进本枚举, code=None)

    - BLOCKED_STATE: 状态门拦截(下载管线态/未知状态, 保守拦截)
    - MISSING_FILES: 源 missingFiles(数据已丢, 不可转移)
    - SOURCE_READ_FAILED: 源 maindata 不可得(torrents_info 查无/故障)
    - EXPORT_FAILED: 源 torrents_export 失败
    - DUPLICATE: 目标已存在(状态为跳过, 非失败)
    - AUTH_FAILED: 目标认证失败(用户名/密码错)
    - ADD_FAILED: 目标拒绝添加(其它)
    - VERIFY_TIMEOUT: 验证超时(目标侧 10s 内未出现该 hash)
    - VERIFY_UNSUPPORTED: 适配器不支持验证查询(为保源不删源)
    - TARGET_ERROR: 目标侧 error/missingFiles 态
    - UNEXPECTED: 未预期异常(兜底, 日志带堆栈)
    """

    BLOCKED_STATE = "blocked_state"
    MISSING_FILES = "missing_files"
    SOURCE_READ_FAILED = "source_read_failed"
    EXPORT_FAILED = "export_failed"
    DUPLICATE = "duplicate"
    AUTH_FAILED = "auth_failed"
    ADD_FAILED = "add_failed"
    VERIFY_TIMEOUT = "verify_timeout"
    VERIFY_UNSUPPORTED = "verify_unsupported"
    TARGET_ERROR = "target_error"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True)
class TorrentTransferResult:
    """逐种子转移结果(W3 回执直接用: {hash, 状态: status.label, 原因: reason})

    code: 结果分类(TransferOutcomeCode); 成功时为 None。
    """

    hash: str
    status: TransferStatus
    reason: str = ""
    code: Optional[TransferOutcomeCode] = None

    def to_receipt(self) -> Dict[str, str]:
        """W3 回执形态 {hash, 状态, 原因}(中文三态)"""
        return {"hash": self.hash, "状态": self.status.label, "原因": self.reason}


# ---------- 状态门(计划 §03; 判据用 qB 状态名, 放行集白名单 + 未知保守拦截) ----------

# 下载管线态(计划 §03 拦截清单; forcedMetaDL 等清单外的下载侧状态由白名单兜底同拦)
_DOWNLOAD_PIPELINE_STATES = frozenset(
    {"metaDL", "downloading", "stalledDL", "queuedDL", "checkingDL", "allocating", "forcedDL"}
)
# 源数据已丢
_MISSING_FILES_STATE = "missingFiles"
# 放行白名单: UP 家族 + 暂停的未完成态(走非跳检通路) + error(按完成度走通用规则)
_ALLOWED_STATES = frozenset(
    {
        "uploading",
        "stalledUP",
        "pausedUP",
        "stoppedUP",
        "queuedUP",
        "forcedUP",
        "checkingUP",
        "pausedDL",
        "stoppedDL",
        "error",
    }
)

# 验证成功判定排除态(计划 §03/§07): hash 出现 且 state 不属于该集才算成功
_BAD_TARGET_STATES = frozenset({"error", "missingFiles"})

# 跳检判定容差: qB 上报 progress 恰为 1.0; 容差只吸收浮点序列化尾差(0.9999999 级),
# 不改变「未完成」的业务判定(0.99 的种子差得远)
_PROGRESS_TOLERANCE = 1e-9

# 字段键 -> 源 maindata 键(save_path 特殊: 终值单独取并做映射)
_FIELD_SOURCES = {
    "category": "category",
    "tags": "tags",
    "share_ratio_limit": "ratio_limit",
    "seeding_time_limit": "seeding_time_limit",
    "up_limit": "up_limit",
    "down_limit": "dl_limit",
    "super_seeding": "super_seeding",
}

# qb adapter 认证失败原因 needle(与 adapters/qb.py 的失败文案耦合; qB 文案漂移不涉及
# 本文案 —— 它是适配器自产文案, 单点在那边)。子串命中即分类 AUTH_FAILED, 未命中归 ADD_FAILED。
_AUTH_FAILURE_NEEDLE = "登录失败"


def _join_notes(*parts: str) -> str:
    """非空注记按序拼接("; " 分隔); 全空返回空串(回执原因不留悬空分隔符)"""
    return "; ".join(p for p in parts if p)


# ---------- 纯函数(单测直接覆盖) ----------


def _field_of(record: object, key: str, default: Any = None) -> Any:
    """从源/目标 maindata 记录取字段: 对象属性优先, 回落 Mapping 键(qbittorrent-api
    的 TorrentDictionary 两者都支持; store 的 TorrentRecord 走属性)"""
    try:
        value = getattr(record, key)
    except AttributeError:
        pass
    else:
        return default if value is None else value
    getter = getattr(record, "get", None)
    if callable(getter):
        return getter(key, default)
    return default


def map_save_path(save_path: str, rules: Sequence[Any]) -> str:
    """路径映射: 有序 from->to 前缀替换, 首条命中生效, 只作用于保存路径终值

    rules: TransferPathMapEntry 序列(src=from 前缀, dst=to 前缀); 空表 = 原样。
    """
    for rule in rules:
        src = str(getattr(rule, "src", "") or "")
        dst = str(getattr(rule, "dst", "") or "")
        if src and save_path.startswith(src):
            return dst + save_path[len(src):]
    return save_path


def decide_skip_check(progress: float, skip_check_enabled: bool) -> Tuple[bool, str]:
    """跳检决策(D2/D8): 不看状态名看完成度

    返回 (skip_check, 降级注明)。progress 达 100%(含容差) 且目标跳检开 -> True;
    其余一律 False —— 目标跳检开但种子未完成时注明「未完成, 已自动改为校验添加」。
    """
    if not skip_check_enabled:
        return False, ""
    if float(progress) >= 1.0 - _PROGRESS_TOLERANCE:
        return True, ""
    return False, "未完成, 已自动改为校验添加"


def gate_verdict(state: str) -> Optional[Tuple[TransferStatus, TransferOutcomeCode, str]]:
    """状态门判定: 拦截返回 (跳过, 分类, 原因); 放行返回 None

    拦截态归「跳过」(预期拒绝, 与 W4 预检「将跳过」同口径); 白名单外的未知状态
    一律保守拦截(黄金法则 2), 源不碰。
    """
    state = str(state or "")
    if state == _MISSING_FILES_STATE:
        return (TransferStatus.SKIPPED, TransferOutcomeCode.MISSING_FILES, "源数据文件已丢失(missingFiles), 不可转移")
    if state in _DOWNLOAD_PIPELINE_STATES:
        return (TransferStatus.SKIPPED, TransferOutcomeCode.BLOCKED_STATE, f"下载管线态({state}), 不可转移")
    if state not in _ALLOWED_STATES:
        return (TransferStatus.SKIPPED, TransferOutcomeCode.BLOCKED_STATE, f"未知状态({state or '空'}), 保守拦截")
    return None


# ---------- 编排器 ----------


@dataclass(frozen=True)
class _SeedPlan:
    """单种子的门后中间产物(状态门已过, 进入添加前的准备结果)"""

    data: bytes
    fields: Dict[str, object]
    skip_check: bool
    degraded_note: str
    source_hash: str


class TransferOrchestrator:
    """串行逐种子编排一个转移批次(D6: 批量无上限/不中断/不自动重试)

    qb_api: 主 qB 的 QbApi facade(只用来读源 maindata / export / 删源任务;
    删源恒 delete_files=False, 且只在验证成功后发生)。
    sleep/verify_timeout/poll_interval: 验证轮询可注入(测试不真等 10s)。
    """
    def __init__(
        self,
        qb_api: "QbApi",
        *,
        sleep: Callable[[float], None] = time.sleep,
        verify_timeout: float = 10.0,
        poll_interval: float = 0.5,
    ):
        self._qb_api = qb_api
        self._sleep = sleep
        self._verify_timeout = float(verify_timeout)
        self._poll_interval = float(poll_interval)

    # ---------- 批次入口 ----------

    def run_batch(
        self,
        target: TransferTargetConfig,
        hashes: Sequence[str],
        keep_source: bool = False,
    ) -> List[TorrentTransferResult]:
        """串行转移一个批次; 返回逐种子结果(顺序 = 入参顺序)

        keep_source: 「仅本次保留源种子」勾选(D1)—— 跳过删源, 其余流程不变。
        批量无上限、不自动重试; 单种子的任何异常只结算本条, 不中断批次(D6)。
        """
        hashes = [str(h) for h in (hashes or [])]
        if not hashes:
            return []
        adapter = create_adapter(target)
        results: List[TorrentTransferResult] = []
        for hash_ in hashes:
            try:
                results.append(self._transfer_one(adapter, target, hash_, keep_source))
            except Exception as exc:  # noqa: BLE001 —— D6: 单种子兜底, 批次继续
                logger.error("transfer: 种子 %s 未预期异常", hash_, exc_info=True)
                results.append(
                    TorrentTransferResult(
                        hash_, TransferStatus.FAILED, f"未预期异常({exc})", TransferOutcomeCode.UNEXPECTED
                    )
                )
        return results

    # ---------- 单种子流水 ----------

    def _transfer_one(
        self,
        adapter: "DownloaderAdapter",
        target: TransferTargetConfig,
        hash_: str,
        keep_source: bool,
    ) -> TorrentTransferResult:
        record = self._read_source(hash_)
        if record is None:
            return TorrentTransferResult(
                hash_, TransferStatus.FAILED, "源种子读取失败(qB 查无此 hash 或查询故障)", TransferOutcomeCode.SOURCE_READ_FAILED
            )
        source_hash = str(_field_of(record, "hash", hash_) or hash_)

        verdict = gate_verdict(str(_field_of(record, "state", "") or ""))
        if verdict is not None:
            status, code, reason = verdict
            return TorrentTransferResult(hash_, status, reason, code)

        data = self._export(source_hash)
        if data is None:
            return TorrentTransferResult(
                hash_, TransferStatus.FAILED, "源 .torrent 导出失败(torrents_export), 源已保留",
                TransferOutcomeCode.EXPORT_FAILED
            )

        plan = self._prepare(data, record, target, source_hash)

        try:
            add = adapter.add_torrent(plan.data, plan.fields, plan.skip_check)
        except Exception as exc:  # noqa: BLE001 —— 适配器编程错误也按 D6 结算本条, 带堆栈日志
            logger.error("transfer: 目标添加调用异常 %s", source_hash, exc_info=True)
            return TorrentTransferResult(
                hash_, TransferStatus.FAILED, f"目标添加调用异常({exc})", TransferOutcomeCode.UNEXPECTED
            )

        reason = _join_notes(add.reason, plan.degraded_note)
        if add.ignored_fields:
            reason = _join_notes(reason, f"目标不支持已忽略字段: {', '.join(add.ignored_fields)}")

        if add.status is AddStatus.SKIPPED:
            # 已存在 -> 跳过, 源保留(计划 §03 失败分类「已存在 -> 跳过」)
            return TorrentTransferResult(
                hash_, TransferStatus.SKIPPED, _join_notes(reason, "源已保留"), TransferOutcomeCode.DUPLICATE
            )
        if add.status is not AddStatus.ADDED:
            code = TransferOutcomeCode.AUTH_FAILED if _AUTH_FAILURE_NEEDLE in (
                add.reason or ""
            ) else TransferOutcomeCode.ADD_FAILED
            return TorrentTransferResult(hash_, TransferStatus.FAILED, _join_notes(reason, "源已保留"), code)

        failure = self._verify(adapter, source_hash)
        if failure is not None:
            return TorrentTransferResult(hash_, failure.status, _join_notes(failure.reason, "源已保留"), failure.code)

        note = ""
        if target.after_state == "paused":
            # D9: 统一暂停。顺序 = 验证成功后、删源前 —— 目标侧先落到承诺状态,
            # 删源这最后一步才发生; 暂停失败不回滚转移(验证已成功), 只在结果注明。
            pause = getattr(adapter, "pause_torrent", None)
            if pause is None or not pause(source_hash):
                note = "目标暂停失败(after_state=paused 未生效)"

        if keep_source:
            return TorrentTransferResult(hash_, TransferStatus.SUCCESS, _join_notes(reason, "按勾选保留源种子", note))

        self._delete_source(source_hash)
        return TorrentTransferResult(hash_, TransferStatus.SUCCESS, _join_notes(reason, note))

    # ---------- 各步实现 ----------

    def _read_source(self, hash_: str) -> Optional[object]:
        """源 maindata(torrents_info 单条); 查无/查询故障 = None(不碰源)"""
        try:
            found = self._qb_api.torrents_info(torrent_hashes=hash_)
        except Exception as exc:  # noqa: BLE001 —— 任何查询故障都按"读不到"处理
            logger.warning("transfer: 源种子读取失败 %s(%s)", hash_, exc)
            return None
        return found[0] if found else None

    def _export(self, source_hash: str) -> Optional[bytes]:
        """源 .torrent 字节; 失败/空 = None(源保留)"""
        try:
            data = self._qb_api.torrents_export(source_hash)
        except Exception as exc:  # noqa: BLE001
            logger.warning("transfer: 源导出失败 %s(%s)", source_hash, exc)
            return None
        return bytes(data) if data else None

    def _prepare(self, data: bytes, record: object, target: TransferTargetConfig, source_hash: str) -> _SeedPlan:
        """字段采集(按 per-target 字段集) + 路径映射 + 跳检决策"""
        fields: Dict[str, object] = {"infohash": source_hash}
        # save_path 锁死必开(计划 §03; 配置校验拒绝显式 false, 这里无视开关恒采集)
        save_path = str(_field_of(record, "save_path", "") or "")
        fields["save_path"] = map_save_path(save_path, target.path_map)
        for key in TRANSFER_FIELD_KEYS:
            if key == "save_path" or not target.fields.get(key):
                continue
            value = _field_of(record, _FIELD_SOURCES[key])
            if value is None:
                continue
            fields[key] = value
        skip_check, degraded = decide_skip_check(float(_field_of(record, "progress", 0.0) or 0.0), target.skip_check)
        return _SeedPlan(
            data=data, fields=fields, skip_check=skip_check, degraded_note=degraded, source_hash=source_hash
        )

    def _verify(self, adapter: "DownloaderAdapter", source_hash: str) -> Optional[TorrentTransferResult]:
        """验证轮询: hash 出现 且 state 不属于 {error, missingFiles} 即成功(None)

        超时/目标 error/missingFiles 返回失败结果(源保留, 由调用方拼源语义)。
        适配器无 find_torrent 扩展点 = 不支持验证 -> 失败(绝不无验证删源)。
        """
        finder = getattr(adapter, "find_torrent", None)
        if finder is None:
            return TorrentTransferResult(
                source_hash, TransferStatus.FAILED, "适配器不支持验证查询", TransferOutcomeCode.VERIFY_UNSUPPORTED
            )
        waited = 0.0
        while True:
            record = finder(source_hash)
            if record is not None:
                state = str(_field_of(record, "state", "") or "")
                if state in _BAD_TARGET_STATES:
                    return TorrentTransferResult(
                        source_hash, TransferStatus.FAILED, f"目标侧状态异常({state})", TransferOutcomeCode.TARGET_ERROR
                    )
                # hash 出现即接受(计划 §07: 超大种子 recheck 超时不误伤; 数据文件全程不删)
                return None
            if waited >= self._verify_timeout:
                return TorrentTransferResult(
                    source_hash,
                    TransferStatus.FAILED,
                    f"验证超时({self._verify_timeout:g}s 内目标未出现该种子)",
                    TransferOutcomeCode.VERIFY_TIMEOUT,
                )
            self._sleep(self._poll_interval)
            waited += self._poll_interval

    def _delete_source(self, source_hash: str) -> None:
        """删源: 仅删任务, delete_files=False 恒定(不变量 1: 数据文件永不删除)"""
        self._qb_api.torrents_delete(torrent_hashes=source_hash, delete_files=False)
