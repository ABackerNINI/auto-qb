"""qBittorrent API 统一门面(QbApi)

所有业务代码对 qB 的调用统一经由此门面: 写操作调用客户端后同步更新
TorrentStore 快照字段与缓存(快照一致性, 修复同 tick 内读到过期数据, 如
无种子标签清理读到旧使用数), 读操作尽量走 store 惰性缓存。方法名与
qbittorrentapi 保持一致(duck-type 兼容, 调用写法与测试断言不变);
dry_run 判定仍由调用点负责(facade 不感知); 属性 client 暴露原始客户端
(仅供数据层内部惰性缓存与测试使用)。

设计:
- 写方法: 调用 raw client 后同步 store(tags/category/state/限速/save_path/删除)
- 读方法: 快照内 hash 的 trackers/files 走 store 惰性缓存; 标签/分类列表走 store 缓存
- 透传: 无快照影响的调用(torrents_add/recheck/reannounce/info/piece_hashes/export/login)
"""
import logging
from typing import Any, List, Optional, Union

from qbittorrentapi import Client

from .torrents import TorrentStore

logger = logging.getLogger(__name__)

HashType = Union[str, List[str]]


class QbApi:
    """qB API 门面: 封装客户端调用 + store 快照同步"""
    def __init__(self, client: Optional[Client] = None, store: Optional[TorrentStore] = None):
        self._client: Optional[Client] = client
        self.store: Optional[TorrentStore] = store

    @property
    def client(self) -> Optional[Client]:
        """原始 qbittorrentapi 客户端(数据层内部惰性缓存/测试使用)"""
        return self._client

    def bind(self, client: Optional[Client], store: Optional[TorrentStore] = None) -> None:
        """重新绑定客户端/数据层(QbManager.client setter 调用)"""
        self._client = client
        if store is not None:
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
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, tags_add=self._to_list(tags))
            self.store.invalidate_tags()  # 新增标签定义可能未存在(全局标签列表缓存失效)

    def torrents_remove_tags(
        self,
        tags: Optional[Union[str, List[str]]] = None,
        torrent_hashes: Optional[HashType] = None,
        **kwargs: Any,
    ):
        self._client.torrents_remove_tags(tags=tags, torrent_hashes=torrent_hashes, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, tags_remove=self._to_list(tags))

    def torrents_delete_tags(self, tags: Optional[Union[str, List[str]]] = None, **kwargs: Any):
        self._client.torrents_delete_tags(tags=tags, **kwargs)
        if self.store is not None:
            self.store.apply_tag_removal(self._to_list(tags))
            self.store.invalidate_tags()

    def torrents_create_category(self, name: Optional[str] = None, **kwargs: Any):
        self._client.torrents_create_category(name=name, **kwargs)
        if self.store is not None:
            self.store.invalidate_categories()

    def torrents_set_category(
        self,
        category: Optional[str] = None,
        torrent_hashes: Optional[HashType] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_category(category=category, torrent_hashes=torrent_hashes, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, category=category)

    def torrents_start(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        self._client.torrents_start(torrent_hashes=torrent_hashes, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, state="stalledUP")

    def torrents_stop(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        self._client.torrents_stop(torrent_hashes=torrent_hashes, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, state="pausedUP")

    def torrents_set_upload_limit(
        self,
        torrent_hashes: Optional[HashType] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_upload_limit(torrent_hashes=torrent_hashes, limit=limit, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, up_limit=limit)

    def torrents_set_download_limit(
        self,
        torrent_hashes: Optional[HashType] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_download_limit(torrent_hashes=torrent_hashes, limit=limit, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, dl_limit=limit)

    def torrents_set_location(
        self,
        torrent_hashes: Optional[HashType] = None,
        location: Optional[str] = None,
        **kwargs: Any,
    ):
        self._client.torrents_set_location(torrent_hashes=torrent_hashes, location=location, **kwargs)
        if self.store is not None:
            self.store.update_torrent_fields(torrent_hashes, save_path=location)

    def torrents_delete(self, torrent_hashes: Optional[HashType] = None, delete_files: bool = False, **kwargs: Any):
        self._client.torrents_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kwargs)
        if self.store is not None:
            for h in self._to_list(torrent_hashes):
                self.store.remove_torrent(h)

    # ---------- 写操作: 无快照变化(下轮 refresh 校准) ----------

    def torrents_add(self, *args: Any, **kwargs: Any):
        return self._client.torrents_add(*args, **kwargs)

    def torrents_recheck(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_recheck(torrent_hashes=torrent_hashes, **kwargs)

    def torrents_reannounce(self, torrent_hashes: Optional[HashType] = None, **kwargs: Any):
        return self._client.torrents_reannounce(torrent_hashes=torrent_hashes, **kwargs)

    # ---------- 读操作: 优先 store 惰性缓存 ----------

    def torrents_info(self, *args: Any, **kwargs: Any):
        return self._client.torrents_info(*args, **kwargs)

    def torrents_piece_hashes(self, torrent_hash: str, **kwargs: Any):
        return self._client.torrents_piece_hashes(torrent_hash, **kwargs)

    def torrents_export(self, torrent_hash: str, **kwargs: Any):
        return self._client.torrents_export(torrent_hash, **kwargs)

    def torrents_trackers(self, torrent_hash, **kwargs):
        if self.store is not None:
            torrent = self.store.get(torrent_hash)
            if torrent is not None:
                return torrent.trackers_info(self._client)
        return self._client.torrents_trackers(torrent_hash, **kwargs)

    def torrents_files(self, torrent_hash, **kwargs):
        if self.store is not None:
            torrent = self.store.get(torrent_hash)
            if torrent is not None:
                return torrent.files(self._client)
        return self._client.torrents_files(torrent_hash, **kwargs)

    def torrents_tags(self, **kwargs: Any):
        if self.store is not None:
            return list(self.store.all_tags())
        return self._client.torrents_tags(**kwargs)

    def torrents_categories(self, **kwargs: Any):
        if self.store is not None:
            return dict(self.store.all_categories())
        return self._client.torrents_categories(**kwargs)

    def auth_log_in(self, **kwargs: Any):
        return self._client.auth_log_in(**kwargs)
