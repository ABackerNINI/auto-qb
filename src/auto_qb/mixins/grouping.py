"""种子分组管理(辅种管理) mixin: 将指向相同文件列表的种子归为一组, 统一检查处理

分组键: (规范化 save_path, 排序后的文件相对路径元组) — 文件列表相同 = 路径集合相同(不含大小,
以便把大小不一致的种子也归入同组做二次判定)。

分组维护(增量, 事件驱动, 无周期轮询任务):
  - 维护成员索引 _group_member_to_key(hash -> 组 key): 删除/状态变化/save_path 同步时
    O(1) 定位种子所属组, 不做全量遍历; 与 _groups/_group_sizes 在归组/移组时同步更新
  - _refresh_torrents 每轮拉全量种子列表, 检测增删与状态变化并立即处理:
    * 新增种子 -> _assign_new_torrent 增量归组(程序启动首轮的现有种子同样逐个归组);
      归组时检查文件大小一致性(文件列表轻易不变, 仅新增时检查, 不每轮检查):
      组内 {路径: 大小} 映射不一致 -> 警告 + 整组暂停(不添加标签)
    * 删除种子 -> _handle_removed_torrents: 移出组; 组内仍有剩余种子 -> 立即触发缺文件磁盘扫描
    * 种子由上传(做种)状态转为暂停状态 -> _handle_state_transitions 立即触发缺文件磁盘扫描(不等下一轮)
    * 保存路径变化 -> _handle_save_path_changes 按新路径重归组; 原组剩余成员与新组已有成员均触发缺文件磁盘扫描
  - 缺文件磁盘扫描: 组内取一个已完成且做种的种子作代表扫描磁盘(同组共享一次);
    文件丢失 -> 整组暂停 + 添加 MISSING 标签(同组所有种子全部触发丢失动作)

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/_add_tags,
以及 qbmanager 初始化的 _groups/_group_sizes/_group_member_to_key/_group_state_snapshot。
"""
import logging
import os
from typing import Any, Dict, Optional
from qbittorrentapi import Client

from ..config import Config
from .. import utils

logger = logging.getLogger(__name__)


class GroupingMixin:
    """种子分组管理(辅种管理): 分组 + 组内大小一致性 + 状态变化触发的缺文件联动"""

    client: Optional[Client]
    logger: logging.Logger
    config: Config

    def _handle_removed_torrents(self, removed_hashes, by_hash: Dict[str, Any], dry_run: bool):
        """删除事件处理: 组内种子被删除 -> 移出分组; 组内仍有剩余种子 -> 立即触发缺文件扫描(可能文件丢失)"""
        affected = set()
        for h in removed_hashes:
            key = self._leave_group(h)
            if key is not None:
                affected.add(key)
        for key in affected:
            members = self._groups.get(key, [])
            tos = [by_hash[h] for h in members if h in by_hash]
            if tos:
                self._check_missing_files(tos, self._group_sizes.get(key, {}), dry_run)

    def _handle_save_path_changes(self, by_hash: Dict[str, Any], dry_run: bool):
        """保存路径变化处理: 种子 save_path 变化 -> 移出原组按新路径重归组; 原组与新组触发缺文件扫描

        触发扫描(事件驱动, 同组只扫一次, 循环后统一处理):
          - 原组: 种子离开后组内仍有剩余成员 -> 立即扫描(文件可能随路径变化而丢失)
          - 新组: 已有其它成员(非仅本种子) -> 归组后也扫描一次(新种子可能补齐或缺失文件)
        文件列表变化(路径增删)在 qB 中需重加种子, 会走 _assign_new_torrent 重新归组, 这里不处理;
        已删种子由删除事件(_handle_removed_torrents)处理, 这里不重复清理。
        """
        triggered = set()
        for h, tor in by_hash.items():
            key = self._group_member_to_key.get(h)
            if key is None or utils._path_normalize(tor.save_path) == key[0]:
                continue
            old_map = self._group_sizes.get(key, {}).get(h)
            if not old_map:
                continue  # 无缓存文件映射, 无从重归组与扫描(维持原行为)
            remain_key = self._leave_group(h)  # 移出原组(成员索引 O(1)); 组空则返回 None
            if remain_key is not None:
                triggered.add(remain_key)  # 原组: 剩余成员触发缺文件扫描
            self._assign_to_group(tor, old_map, by_hash, dry_run)  # 新 save_path + 原文件列表重归组
            new_key = self._group_member_to_key.get(h)
            if new_key is not None and len(self._groups[new_key]) > 1:
                triggered.add(new_key)  # 新组: 已有其它成员, 归组后触发一次扫描
        for key in triggered:
            members = [by_hash[m] for m in self._groups.get(key, []) if m in by_hash]
            if members:
                self._check_missing_files(members, self._group_sizes.get(key, {}), dry_run)

    def _handle_state_transitions(self, by_hash: Dict[str, Any], dry_run: bool):
        """状态变化处理: 种子由上传(做种)转为暂停状态 -> 所属组立即触发缺文件扫描(同组只扫一次)

        状态快照(_group_state_snapshot)存上一轮各种子的 state_enum 枚举对象,
        与 qB 版本无关(老版 pausedUP / 新版 stoppedUP 归为同一 is_paused 类别):
        遍历本轮种子先过滤暂停状态, 再对比上一轮快照为上传(做种)类别即触发;
        状态变化在检测到的同一轮立即处理, 不等下一轮。
        """
        triggered = set()
        for h, tor in by_hash.items():
            if not self._is_paused(tor):
                continue
            prev = self._group_state_snapshot.get(h)  # 上一轮 state_enum 枚举
            if prev is not None and getattr(prev, "is_uploading", False):
                key = self._group_member_to_key.get(h)
                if key is not None:
                    triggered.add(key)
        for key in triggered:
            members = self._groups[key]
            tos = [by_hash[h] for h in members if h in by_hash]
            if tos:
                self._check_missing_files(tos, self._group_sizes.get(key, {}), dry_run)

    def _assign_new_torrent(self, torrent_hash: str, by_hash: Dict[str, Any], dry_run: bool = False):
        """新增种子增量归组: 仅拉取该种子的文件列表并入组(by_hash O(1) 定位, 不做全量遍历)"""
        tor = by_hash.get(torrent_hash)
        if tor is None:
            return
        try:
            files = self.client.torrents_files(torrent_hash)
        except Exception as e:
            logger.debug(f"分组归组获取文件列表失败({torrent_hash}): {e}")
            return
        self._assign_to_group(tor, {utils._path_normalize(f.name): f.size for f in files}, by_hash, dry_run)

    def _assign_to_group(self, tor, file_map: Dict[str, int], by_hash: Dict[str, Any], dry_run: bool = False):
        """将种子按文件列表归入分组(幂等): 先移出旧组再加入新组; 维护成员索引; 归组后检查大小一致性"""
        if not file_map:
            return
        key = (utils._path_normalize(tor.save_path), tuple(sorted(file_map.keys())))
        self._leave_group(tor.hash)  # 幂等: 移出旧组(可能因 save_path 变化被重归组), 不触发扫描
        self._groups.setdefault(key, []).append(tor.hash)
        self._group_sizes.setdefault(key, {})[tor.hash] = file_map
        self._group_member_to_key[tor.hash] = key
        # 文件大小一致性: 仅新增/重归组时检查(文件列表轻易不变, 无需每轮检查)
        self._check_size_consistency(key, by_hash, dry_run)

    def _check_size_consistency(self, key, by_hash: Dict[str, Any], dry_run: bool):
        """新增种子归组时检查组内文件大小一致性: 组内 {路径: 大小} 不一致 -> 警告 + 整组暂停(不加标签)"""
        members = self._groups[key]
        if len(members) <= 1:
            return
        tos = [by_hash[h] for h in members if h in by_hash]
        if not self._size_mismatch(tos, self._group_sizes[key]):
            return
        desc = ", ".join(f"{t.name}[{t.hash[:8]}]" for t in tos)
        logger.warning(f"辅种组文件大小不一致({len(tos)}个种子), 暂停整组: {desc}")
        if not dry_run:
            self.client.torrents_stop(torrent_hashes=[t.hash for t in tos])

    def _leave_group(self, torrent_hash: str):
        """将种子移出所在分组(成员索引 O(1) 定位, 不做全量遍历); 组空则删除整组

        返回移除后组内仍有剩余成员的组 key(无则 None); 不触发缺文件扫描,
        重归组(_assign_to_group)与删除(_handle_removed_torrents)共用, 是否扫描由调用方决定。
        """
        key = self._group_member_to_key.pop(torrent_hash, None)
        if key is None:
            return None
        members = self._groups.get(key, [])
        if torrent_hash in members:
            members.remove(torrent_hash)
        self._group_sizes.get(key, {}).pop(torrent_hash, None)
        if not members:
            del self._groups[key]
            self._group_sizes.pop(key, None)
            return None
        return key

    @staticmethod
    def _size_mismatch(members: list, sizes: Dict[str, Dict[str, int]]) -> bool:
        """组内文件大小一致性: 各种子 {路径: 大小} 映射不一致返回 True(仅新增归组时检查) """
        size_sets = {tuple(sorted(fmap.items())) for fmap in (sizes.get(t.hash, {}) for t in members)}
        return len(size_sets) > 1

    def _check_missing_files(self, members: list, sizes: Dict[str, Dict[str, int]], dry_run: bool):
        """缺文件磁盘扫描(同组共享一次): 文件丢失 -> 整组暂停 + MISSING 标签

        由删除事件(_handle_removed_torrents)或状态变化检测(_handle_state_transitions)在
        满足触发条件(组内种子被删除 / 种子由上传转暂停)时立即调用。
        sizes: 组内缓存的文件大小映射 {hash: {规范化相对路径: 大小}}(增量归组时拉取, 复用)
        """
        # 组内取一个已完成且正在做种的种子作为代表
        rep = next((t for t in members if t.amount_left <= 0 and self._is_uploading(t)), None)
        if rep is None:
            return  # 组内无已完成做种种子(均在下载/暂停), 不检查

        logger.info(f"正在检查种子组的文件丢失: 辅种数: {len(members)}, 名称: {rep.name}")
        missing = False
        for fname, fsize in sizes.get(rep.hash, {}).items():
            full_path = utils.add_long_path_prefix_for_win(os.path.normpath(os.path.join(rep.save_path, fname)))
            if not os.path.exists(full_path):
                logger.warning(f"辅种组文件缺失: '{full_path}'")
                missing = True
                break
            try:
                if os.path.getsize(full_path) != fsize:
                    logger.warning(f"辅种组文件大小不一致: '{full_path}', 期望 {fsize}")
                    missing = True
                    break
            except OSError:
                logger.warning(f"辅种组文件无法读取: '{full_path}'")
                missing = True
                break

        if missing:
            # 文件丢失: 同组所有种子全部触发丢失动作(暂停 + MISSING 标签)
            tag = self.config.grouping.missing_tag
            desc = ", ".join(f"[{t.hash[:8]}]" for t in members)
            logger.warning(f"辅种组文件丢失, 暂停整组并添加标签 '{tag}', 受影响的种子哈希: {desc}")
            if not dry_run:
                self.client.torrents_stop(torrent_hashes=[t.hash for t in members])
            for t in members:
                self._add_tags(t, [tag], dry_run)

    @staticmethod
    def _is_uploading(tor) -> bool:
        """种子是否处于做种(上传)状态: 由 state_enum.is_uploading 判定(qB 版本无关, 不含暂停)"""
        enum = getattr(tor, "state_enum", None)
        return bool(enum is not None and enum.is_uploading)

    @staticmethod
    def _is_paused(tor) -> bool:
        """种子是否处于暂停状态: 由 state_enum.is_paused 判定(qB 版本无关, 覆盖老版 pausedUP/新版 stoppedUP)"""
        enum = getattr(tor, "state_enum", None)
        return bool(enum is not None and enum.is_paused)
