"""qBittorrent API 统一Facade(QbApi)

所有业务代码对 qB 的调用统一经由此Facade: 写操作调用客户端后同步更新
TorrentStore 快照字段与缓存(快照一致性, 修复同 tick 内读到过期数据, 如
无种子标签清理读到旧使用数), 读操作尽量走 store 惰性缓存。方法名与
qbittorrentapi 保持一致(duck-type 兼容, 调用写法与测试断言不变);
dry_run 判定仍由调用点负责(facade 不感知); 属性 client 暴露原始客户端
(仅供数据层内部惰性缓存与测试使用)。

store 为必传参数(QbManager 恒持有数据层): "无 store 则透明透传"的可选
形态已移除, 不为测试留专用通道。

设计:
- 写方法: 调用 raw client 后同步 store(tags/category/state/限速/save_path/删除)
- 读方法: 快照内 hash 的 trackers/files 走 store 惰性缓存; 标签/分类列表走 store 缓存
- 透传: 无快照影响的调用(torrents_add/recheck/reannounce/info/piece_hashes/export/login;
  WEB UI 二轮新增的种子写操作 super_seeding/force_start/share_limits/rename/队列/auto_tmm/
  文件优先级/重命名文件(夹)均透传, 由下轮 refresh 校准; tracker 写操作额外失效记录级惰性缓存)
"""
import logging
from typing import Any, List, Optional, Union

from qbittorrentapi import Client

from ..infra.utils import mask_tracker_entry
from ..torrents import TorrentStore
from . import curves

logger = logging.getLogger(__name__)

HashType = Union[str, List[str]]


class QbApi:
    """qB API Facade: 封装客户端调用 + store 快照同步"""
    def __init__(self, client: Optional[Client], store: TorrentStore):
        self._client: Optional[Client] = client
        self.store: TorrentStore = store

    @property
    def client(self) -> Optional[Client]:
        """原始 qbittorrentapi 客户端(数据层内部惰性缓存/测试使用)"""
        return self._client

    def bind(self, client: Optional[Client], store: TorrentStore) -> None:
        """重新绑定客户端/数据层(QbManager.client setter 调用)"""
        self._client = client
        self.store = store

    @staticmethod
    def _to_list(value: Optional[Union[str, List[str]]]) -> List[str]:
        """单个字符串 -> [str], 其余原样转 list(与 qbittorrentapi 接受单值/列表一致)"""
        if value is None:
            return []
        return [value] if isinstance(value, str) else list(value)

    # ---------- 写操作: 调用 raw 后同步 store ----------

    def torrents_add_tags(
        self,
        tags: Optional[Union[str, List[str]]] = None,
        torrent_hashes: Optional[HashType] = None,
        **kwargs: Any,
    ):
        self._client.torrents_add_tags(tags=tags, torrent_hashes=torrent_hashes, **kwargs)
        self.store.update_torrent_fields(torrent_hashes, tags_add=self._to_list(tags))
        self.store.invalidate_tags()  # 新增标签定义可能未存在(全局标签列表缓存失效)

    def torrents_remove_tags(
        self,
        tags: Optional[Union[str, List[str]]] = None,
        torrent_hashes: Optional[HashType] = None,
        **kwargs: Any,
    ):
        self._client.torrents_remove_tags(tags=tags, torrent_hashes=torrent_hashes, **kwargs)
        self.store.update_torrent_fields(torrent_hashes, tags_remove=self._to_list(tags))

    def torrents_delete_tags(self, tags: Optional[Union[str, List[str]]] = None, **kwargs: Any):
        self._client.torrents_delete_tags(tags=tags, **kwargs)
        self.store.apply_tag_removal(self._to_list(tags))
        self.store.invalidate_tags()

    def torrents_create_category(self, name: Optional[str] = None, **kwargs: Any):
        self._client.torrents_create_category(name=name, **kwargs)
        self.store.invalidate_categories()

    def torrents_set_category(
        self,
        category: Optional[str] = None,
        torrent_hashes: Optional[HashType] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_category(category=category, torrent_hashes=torrent_hashes, **kwargs)
        self.store.update_torrent_fields(torrent_hashes, category=category)

    def torrents_start(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        self._client.torrents_start(torrent_hashes=torrent_hashes, **kwargs)
        self.store.note_own_write(torrent_hashes)

    def torrents_stop(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        self._client.torrents_stop(torrent_hashes=torrent_hashes, **kwargs)
        self.store.note_own_write(torrent_hashes)

    def torrents_pause(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        """暂停(与 torrents_stop 同为暂停轴写操作, 纯透传)

        !不回写快照(A 系 26-10-13-0540 S1: 删除原 _sync_paused_state 合成回写)。state 是
        **唯一**由 qB 同步权威驱动的字段 —— 快照语义收敛为「严格 = 最近一次同步的应用结果」；
        自有停/起与外部变更因此**源无关**: 状态变化只经下一轮真实 delta 被转移检测与状态事件
        看见(不再是「自家动作当场改写、外部变更等同步」的不对称)。

        代价(刻意): 同 tick 内 is_paused 仍为旧值 ⇒ 第二个同类动作可能重发一次请求(qB 侧
        幂等, 无功能错误, 只是重复 HTTP 与日志噪声); 需补回时见计划 §4.4 的可选件 pending_writes。

        登记 own_writes(A 系 26-10-13-0540 S2): 停/起的**意图**要登记, 供 deferral 判据 ——
        校验类决策(跳检闸门/决策链)在快照尚未回流时延迟到下一 tick, 收回 G4/G6 陈旧-放行窗口。
        """
        self._client.torrents_pause(torrent_hashes=torrent_hashes, **kwargs)
        self.store.note_own_write(torrent_hashes)

    def torrents_resume(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        """恢复(与 torrents_pause 对称, 纯透传; 见 torrents_pause 注)"""
        self._client.torrents_resume(torrent_hashes=torrent_hashes, **kwargs)
        self.store.note_own_write(torrent_hashes)

    def torrents_set_upload_limit(
        self,
        torrent_hashes: Optional[HashType] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_upload_limit(torrent_hashes=torrent_hashes, limit=limit, **kwargs)
        self.store.update_torrent_fields(torrent_hashes, up_limit=limit)

    def torrents_set_download_limit(
        self,
        torrent_hashes: Optional[HashType] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_download_limit(torrent_hashes=torrent_hashes, limit=limit, **kwargs)
        self.store.update_torrent_fields(torrent_hashes, dl_limit=limit)

    def torrents_set_location(
        self,
        torrent_hashes: Optional[HashType] = None,
        location: Optional[str] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_location(torrent_hashes=torrent_hashes, location=location, **kwargs)
        self.store.update_torrent_fields(torrent_hashes, save_path=location)

    def torrents_delete(self, torrent_hashes: Optional[HashType] = None, delete_files: bool = False, **kwargs: Any):
        self._client.torrents_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kwargs)
        for h in self._to_list(torrent_hashes):
            self.store.remove_torrent(h)

    # ---------- 写操作: 无快照变化(下轮 refresh 校准) ----------

    def torrents_add(self, *args: Any, **kwargs: Any):
        return self._client.torrents_add(*args, **kwargs)

    def torrents_recheck(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_recheck(torrent_hashes=torrent_hashes, **kwargs)

    def torrents_reannounce(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_reannounce(torrent_hashes=torrent_hashes, **kwargs)

    def torrents_set_super_seeding(
        self, enable: bool = False, torrent_hashes: Optional[HashType] = None, **kwargs: Any
    ):
        return self._client.torrents_set_super_seeding(enable=enable, torrent_hashes=torrent_hashes, **kwargs)

    def torrents_set_force_start(self, enable: bool = False, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_set_force_start(enable=enable, torrent_hashes=torrent_hashes, **kwargs)

    def torrents_set_share_limits(
        self,
        ratio_limit: Optional[float] = None,
        seeding_time_limit: Optional[int] = None,
        inactive_seeding_time_limit: Optional[int] = None,
        torrent_hashes: Optional[HashType] = None,
        **kwargs: Any,
    ):
        """设置分享限制(qB torrents/setShareLimits 端点, 库内同名方法透传)

        哨兵语义(与 qbittorrent-api 文档一致, 种子快照 ratio_limit 等字段同义):
        - -2 = 使用全局分享限制默认值
        - -1 = 不限制
        - 其余正数 = 限制值(ratio_limit 为比例; seeding_time_limit/inactive_seeding_time_limit 为分钟)
        调用方须保证三个维度均为具体数值(缺失按 -2 补齐), 库不会过滤 None,
        直传 None 会以字面量 "None" 发送给 qB 导致参数无效。
        """
        return self._client.torrents_set_share_limits(
            ratio_limit=ratio_limit,
            seeding_time_limit=seeding_time_limit,
            inactive_seeding_time_limit=inactive_seeding_time_limit,
            torrent_hashes=torrent_hashes,
            **kwargs,
        )

    def torrents_rename(
        self, torrent_hash: Optional[str] = None, new_torrent_name: Optional[str] = None, **kwargs: Any
    ):
        """重命名种子(仅改 qB 显示名, 不动磁盘文件名); 快照 name 由下轮 sync 自然更新"""
        return self._client.torrents_rename(torrent_hash=torrent_hash, new_torrent_name=new_torrent_name, **kwargs)

    def torrents_set_auto_management(
        self, enable: bool = False, torrent_hashes: Optional[HashType] = None, **kwargs: Any
    ):
        return self._client.torrents_set_auto_management(enable=enable, torrent_hashes=torrent_hashes, **kwargs)

    # ---------- 队列调整(单种/批量同形; torrent_hashes 列表即批量) ----------

    def torrents_top_priority(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_top_priority(torrent_hashes=torrent_hashes, **kwargs)

    def torrents_increase_priority(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_increase_priority(torrent_hashes=torrent_hashes, **kwargs)

    def torrents_decrease_priority(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_decrease_priority(torrent_hashes=torrent_hashes, **kwargs)

    def torrents_bottom_priority(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_bottom_priority(torrent_hashes=torrent_hashes, **kwargs)

    # ---------- tracker/文件内容写操作 ----------

    def _invalidate_torrent_trackers(self, torrent_hash: Optional[str]) -> None:
        """tracker 写操作后失效该种子的 tracker 惰性缓存(同 tick 内后续读取拿到新值); 未知 hash 静默"""
        rec = self.store.get(torrent_hash) if torrent_hash else None
        if rec is not None:
            rec.invalidate_trackers()

    def torrents_add_trackers(self, torrent_hash: Optional[str] = None, urls=None, **kwargs: Any):
        self._client.torrents_add_trackers(torrent_hash=torrent_hash, urls=urls, **kwargs)
        self._invalidate_torrent_trackers(torrent_hash)

    def torrents_remove_trackers(self, torrent_hash: Optional[str] = None, urls=None, **kwargs: Any):
        self._client.torrents_remove_trackers(torrent_hash=torrent_hash, urls=urls, **kwargs)
        self._invalidate_torrent_trackers(torrent_hash)

    def torrents_file_priority(
        self, torrent_hash: Optional[str] = None, file_ids=None, priority: Optional[int] = None, **kwargs: Any
    ):
        return self._client.torrents_file_priority(
            torrent_hash=torrent_hash, file_ids=file_ids, priority=priority, **kwargs
        )

    def torrents_rename_file(
        self,
        torrent_hash: Optional[str] = None,
        old_path: Optional[str] = None,
        new_path: Optional[str] = None,
        **kwargs: Any
    ):
        """重命名单文件(old_path/new_path 为 Web API v2.7+ 参数形态; qB 4.3.3+ 均支持)"""
        return self._client.torrents_rename_file(
            torrent_hash=torrent_hash, old_path=old_path, new_path=new_path, **kwargs
        )

    def torrents_rename_folder(
        self,
        torrent_hash: Optional[str] = None,
        old_path: Optional[str] = None,
        new_path: Optional[str] = None,
        **kwargs: Any
    ):
        return self._client.torrents_rename_folder(
            torrent_hash=torrent_hash, old_path=old_path, new_path=new_path, **kwargs
        )

    def torrents_edit_category(self, name: Optional[str] = None, save_path: Optional[str] = None, **kwargs: Any):
        self._client.torrents_edit_category(name=name, save_path=save_path, **kwargs)
        self.store.invalidate_categories()

    def torrents_remove_categories(self, categories=None, **kwargs: Any):
        self._client.torrents_remove_categories(categories=categories, **kwargs)
        self.store.invalidate_categories()

    def torrents_create_tags(self, tags=None, **kwargs: Any):
        self._client.torrents_create_tags(tags=tags, **kwargs)
        self.store.invalidate_tags()

    # ---------- 读操作: 优先 store 惰性缓存 ----------

    def torrents_info(self, *args: Any, **kwargs: Any):
        return self._client.torrents_info(*args, **kwargs)

    def sync_maindata(self, rid: int = 0, **kwargs: Any):
        """增量同步端点 /api/v2/sync/maindata: rid=0 取全量快照, 否则只回自该 rid 起的变化

        透传(无快照副作用): 快照更新由 TorrentSync 合并 + store.refresh 完成。
        """
        return self._client.sync_maindata(rid=rid, **kwargs)

    def torrents_piece_hashes(self, torrent_hash: str, **kwargs: Any):
        return self._client.torrents_piece_hashes(torrent_hash, **kwargs)

    def torrents_export(self, torrent_hash: str, **kwargs: Any):
        return self._client.torrents_export(torrent_hash, **kwargs)

    def torrents_trackers(self, torrent_hash, **kwargs):
        torrent = self.store.get(torrent_hash)
        if torrent is not None:
            return torrent.trackers_info(self._client)
        # store 未命中直连同样过 mask(计划 26-10-07-0055 S1): 两条读路径口径一致, 原文不出 Facade
        return [mask_tracker_entry(t) for t in (self._client.torrents_trackers(torrent_hash, **kwargs) or [])]

    def torrents_files(self, torrent_hash, **kwargs):
        torrent = self.store.get(torrent_hash)
        if torrent is not None:
            return torrent.files(self._client)
        return self._client.torrents_files(torrent_hash, **kwargs)

    def torrents_tags(self) -> List[str]:
        """全局标签列表(读 store 缓存, 写操作时已失效重建)"""
        return list(self.store.all_tags())

    def torrents_categories(self) -> dict:
        """全部分类(读 store 缓存, 写操作时已失效重建)"""
        return dict(self.store.all_categories())

    def auth_log_in(self, **kwargs: Any):
        return self._client.auth_log_in(**kwargs)

    # ---------- 全局速度限制(qB 5.0 transfer 端点; 单位 bytes/s, 0 = 不限速) ----------

    def get_global_speed_limits(self) -> dict:
        """读取 qB 全局上传/下载速度限制; 对外以 KiB/s 返回(<=0 归一为 0 = 不限速)

        qB 5.0(Web API v2.9+ / qbittorrent-api 2026.8.x)中 app/preferences 的旧键
        upload_limit/download_limit 已失效(静默无效), 全局限速走 transfer 端点且单位
        为 bytes/s。读取 bytes/s 经 bytes_to_kib_floor(整除向下)换算为 KiB/s —— 取整
        方向单点见 curves「速度单位换算单点」段。
        """
        return {
            "upload_limit": curves.bytes_to_kib_floor(int(self._client.transfer_upload_limit())),
            "download_limit": curves.bytes_to_kib_floor(int(self._client.transfer_download_limit())),
        }

    def set_global_speed_limits(self, upload_kib: int = None, download_kib: int = None):
        """设置 qB 全局上传/下载速度限制(KiB/s); 0 = 不限速

        走 qB 5.0 transfer 端点(transfer_set_upload_limit/download_limit), 单位换算
        经 curves.kib_to_bytes(bytes/s, 0 即不限速; 旧版 app.preferences 的 -1 标记
        不再使用)。仅传非 None 的方向; 调用方先比较当前值, 有变化才调用。
        """
        if upload_kib is not None:
            self._client.transfer_set_upload_limit(limit=curves.kib_to_bytes(upload_kib))
        if download_kib is not None:
            self._client.transfer_set_download_limit(limit=curves.kib_to_bytes(download_kib))

    # ---------- 备用(替代)速度限制与模式切换(qB"乌龟"; ALT-01) ----------

    def get_alt_speed_limits(self) -> dict:
        """读取 qB 备用全局速度限制; 对外以 KiB/s 返回(<=0 归一为 0 = 不限)

        qB 5.0 的端点迁移只动了**主速度**两个键(upload/download_limit -> transfer 端点),
        备用速度 alt_dl_limit/alt_up_limit 仍在 app/preferences, 单位 bytes/s
        (换算同主速度: curves.bytes_to_kib_floor 单点)。
        """
        prefs = self._client.app_preferences() or {}

        return {
            "upload_limit": curves.bytes_to_kib_floor(prefs.get("alt_up_limit")),
            "download_limit": curves.bytes_to_kib_floor(prefs.get("alt_dl_limit")),
        }

    def set_alt_speed_limits(self, upload_kib: int = None, download_kib: int = None):
        """设置 qB 备用全局速度限制(KiB/s); 0 = 不限速

        app/setPreferences 是增量语义: 只传需要改的 alt_* 键, 其余偏好不动。
        仅传非 None 的方向; 单位换算与主速度一致(curves.kib_to_bytes 单点)。
        """
        prefs: dict = {}
        if upload_kib is not None:
            prefs["alt_up_limit"] = curves.kib_to_bytes(upload_kib)
        if download_kib is not None:
            prefs["alt_dl_limit"] = curves.kib_to_bytes(download_kib)
        if prefs:
            self._client.app_set_preferences(json=prefs)

    def get_speed_limits_mode(self) -> int:
        """当前速度模式: 0 = 主速度 / 1 = 备用速度(transfer/speedLimitsMode)"""
        return int(self._client.transfer_speed_limits_mode())

    def toggle_speed_limits_mode(self):
        """在主/备速度模式间切换(transfer/toggleSpeedLimitsMode; 切换后状态随主轮询回读)"""
        self._client.transfer_toggle_speed_limits_mode()
