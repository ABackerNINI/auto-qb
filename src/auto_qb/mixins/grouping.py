"""种子分组管理(辅种管理) mixin: 将指向相同文件列表的种子归为一组, 统一检查处理

分组键: (规范化 save_path, 排序后的文件相对路径元组) — 文件列表相同 = 路径集合相同(不含大小,
以便把大小不一致的种子也归入同组做二次判定)。

分组维护(增量, 事件驱动, 无周期轮询任务):
  - _refresh_torrents 每轮拉全量种子列表, 检测增删与状态变化并立即处理:
    * 新增种子 -> _assign_new_torrent 增量归组(程序启动首轮的现有种子同样逐个归组);
      归组时检查文件大小一致性(文件列表轻易不变, 仅新增时检查, 不每轮检查):
      组内 {路径: 大小} 映射不一致 -> 警告 + 整组暂停(不添加标签)
    * 删除种子 -> _remove_from_groups 移出组; 组内仍有剩余种子 -> 立即触发缺文件磁盘扫描
    * 组内种子由上传(做种)状态转为暂停状态 -> 立即触发缺文件磁盘扫描(不等下一轮)
  - 缺文件磁盘扫描: 组内取一个已完成且做种的种子作代表扫描磁盘(同组共享一次);
    文件丢失 -> 整组暂停 + 添加 MISSING 标签(同组所有种子全部触发丢失动作)

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/_add_tags/_snapshot,
以及 qbmanager 初始化的 _groups/_group_sizes/_group_state_snapshot。
"""
import logging
import os
from typing import Any, Dict, List

from ..utils import _path_normalize, add_long_path_prefix_for_win

logger = logging.getLogger("auto-qb")

# 上传(做种)状态: 由这些状态转为暂停状态时触发缺文件扫描
_UPLOADING_STATES = frozenset({"uploading", "stalledup", "forcedup", "checkingup", "queuedup"})
# 暂停状态(qB 新老版本命名)
_PAUSED_STATES = frozenset({"pausedup", "stoppedup", "pauseddl", "stoppeddl"})


class GroupingMixin:
    """种子分组管理(辅种管理): 分组 + 组内大小一致性 + 状态变化触发的缺文件联动"""

    client: Any
    logger: Any
    config: Any

    def _on_group_removed(self, removed_hashes, by_hash: Dict[str, Any], dry_run: bool):
        """删除事件处理: 种子移出分组; 组内仍有剩余种子 -> 立即触发缺文件扫描(可能文件丢失) """
        affected = set()
        for h in removed_hashes:
            affected |= self._remove_from_groups(h)
        for key in affected:
            members = self._groups.get(key, [])
            tos = [by_hash[h] for h in members if h in by_hash]
            if tos:
                self._check_missing_files(tos, self._group_sizes.get(key, {}), dry_run)

    def _sync_groups(self, by_hash: Dict[str, Any], dry_run: bool):
        """同步分组: 保存路径变化的种子按新路径重归组

        文件列表变化(路径增删)在 qB 中需重加种子, 会走 _assign_new_torrent 重新归组, 这里不处理;
        已删种子由删除事件(_on_group_removed)处理, 这里不重复清理。
        """
        for key in list(self._groups.keys()):
            for h in list(self._groups[key]):
                tor = by_hash.get(h)
                if tor is None:
                    continue
                if _path_normalize(tor.save_path) != key[0]:
                    old_map = self._group_sizes.get(key, {}).pop(h, None)
                    if old_map:
                        self._assign_to_group(tor, old_map, dry_run)  # 新 save_path + 原文件列表重归组

    def _check_group_state_transitions(self, by_hash: Dict[str, Any], dry_run: bool):
        """状态变化检测: 组内种子由上传(做种)转为暂停状态 -> 立即触发缺文件扫描(同组只扫一次)

        用上一轮 _group_state_snapshot 对比: 上一轮为上传状态且本轮暂停 -> 触发;
        状态快照由 _refresh_torrents 每轮更新, 因此状态变化在检测到的同一轮立即处理, 不等下一轮。
        """
        for key, members in list(self._groups.items()):
            tos = [by_hash[h] for h in members if h in by_hash]
            if not tos:
                continue
            if any(self._uploading_to_paused(t) for t in tos):
                self._check_missing_files(tos, self._group_sizes.get(key, {}), dry_run)

    def _assign_new_torrent(self, torrent_hash: str, dry_run: bool = False):
        """新增种子增量归组: 仅拉取该种子的文件列表并入组(每次一个种子, 不做全量遍历)"""
        tor = next((t for t in self._snapshot if t.hash == torrent_hash), None)
        if tor is None:
            return
        try:
            files = self.client.torrents_files(torrent_hash)
        except Exception as e:
            self.logger.debug(f"分组归组获取文件列表失败({torrent_hash}): {e}")
            return
        self._assign_to_group(tor, {_path_normalize(f.name): f.size for f in files}, dry_run)

    def _assign_to_group(self, tor, file_map: Dict[str, int], dry_run: bool = False):
        """将种子按文件列表归入分组(幂等): 先移出旧组再加入新组; 归组后检查文件大小一致性"""
        if not file_map:
            return
        key = (_path_normalize(tor.save_path), tuple(sorted(file_map.keys())))
        # 移出旧组(幂等: 种子可能因 save_path 变化被重归组)
        for other_key, members in list(self._groups.items()):
            if tor.hash in members:
                members.remove(tor.hash)
                self._group_sizes[other_key].pop(tor.hash, None)
                if not members:
                    del self._groups[other_key]
                    self._group_sizes.pop(other_key, None)
        self._groups.setdefault(key, []).append(tor.hash)
        self._group_sizes.setdefault(key, {})[tor.hash] = file_map
        # 文件大小一致性: 仅新增/重归组时检查(文件列表轻易不变, 无需每轮检查)
        self._check_size_consistency(key, dry_run)

    def _check_size_consistency(self, key, dry_run: bool):
        """新增种子归组时检查组内文件大小一致性: 组内 {路径: 大小} 不一致 -> 警告 + 整组暂停(不加标签)"""
        members = self._groups[key]
        if len(members) <= 1:
            return
        snap = {t.hash: t for t in self._snapshot}
        tos = [snap[h] for h in members if h in snap]
        if not self._size_mismatch(tos, self._group_sizes[key]):
            return
        desc = ", ".join(f"{t.name}[{t.hash[:8]}]" for t in tos)
        self.logger.warning(f"辅种组文件大小不一致({len(tos)}个种子), 暂停整组: {desc}")
        if not dry_run:
            self.client.torrents_stop(torrent_hashes=[t.hash for t in tos])

    def _remove_from_groups(self, torrent_hash: str) -> set:
        """种子被删除时从分组中移除; 返回组内仍有剩余成员的组 key(调用方据此触发缺文件扫描)"""
        affected = set()
        for key, members in list(self._groups.items()):
            if torrent_hash in members:
                members.remove(torrent_hash)
                self._group_sizes[key].pop(torrent_hash, None)
                if not members:
                    del self._groups[key]
                    self._group_sizes.pop(key, None)
                else:
                    affected.add(key)
                break  # 一个种子只属于一个组(归组幂等保证)
        return affected

    @staticmethod
    def _size_mismatch(members: list, sizes: Dict[str, Dict[str, int]]) -> bool:
        """组内文件大小一致性: 各种子 {路径: 大小} 映射不一致返回 True(仅新增归组时检查) """
        size_sets = {tuple(sorted(fmap.items())) for fmap in (sizes.get(t.hash, {}) for t in members)}
        return len(size_sets) > 1

    def _check_missing_files(self, members: list, sizes: Dict[str, Dict[str, int]], dry_run: bool):
        """缺文件磁盘扫描(同组共享一次): 文件丢失 -> 整组暂停 + MISSING 标签

        由删除事件(_on_group_removed)或状态变化检测(_check_group_state_transitions)在
        满足触发条件(组内种子被删除 / 种子由上传转暂停)时立即调用。
        sizes: 组内缓存的文件大小映射 {hash: {规范化相对路径: 大小}}(增量归组时拉取, 复用)
        """
        # 组内取一个已完成且正在做种的种子作为代表
        rep = next((t for t in members if t.amount_left <= 0 and self._is_uploading(t)), None)
        if rep is None:
            return  # 组内无已完成做种种子(均在下载/暂停), 不检查

        missing = False
        for fname, fsize in sizes.get(rep.hash, {}).items():
            full_path = add_long_path_prefix_for_win(os.path.normpath(os.path.join(rep.save_path, fname)))
            if not os.path.exists(full_path):
                self.logger.warning(f"辅种组文件缺失: '{full_path}'")
                missing = True
                break
            try:
                if os.path.getsize(full_path) != fsize:
                    self.logger.warning(f"辅种组文件大小不一致: '{full_path}', 期望 {fsize}")
                    missing = True
                    break
            except OSError:
                self.logger.warning(f"辅种组文件无法读取: '{full_path}'")
                missing = True
                break

        if missing:
            # 文件丢失: 同组所有种子全部触发丢失动作(暂停 + MISSING 标签)
            tag = self.config.grouping.missing_tag
            desc = ", ".join(f"{t.name}[{t.hash[:8]}]" for t in members)
            self.logger.warning(f"辅种组文件丢失, 暂停整组并添加标签 '{tag}': {desc}")
            if not dry_run:
                self.client.torrents_stop(torrent_hashes=[t.hash for t in members])
            for t in members:
                self._add_tags(t, [tag], dry_run)

    @staticmethod
    def _is_uploading(tor) -> bool:
        """种子是否处于做种(上传)状态: 优先用 state_enum, 回退到 state 字符串判断"""
        enum = getattr(tor, "state_enum", None)
        if enum is not None:
            return bool(getattr(enum, "is_uploading", False))
        return (tor.state or "").lower() in _UPLOADING_STATES

    @staticmethod
    def _is_paused(tor) -> bool:
        """种子是否处于暂停状态: 优先用 state_enum, 回退到 state 字符串判断"""
        enum = getattr(tor, "state_enum", None)
        if enum is not None:
            return bool(getattr(enum, "is_paused", False))
        return (tor.state or "").lower() in _PAUSED_STATES

    def _uploading_to_paused(self, tor) -> bool:
        """种子由上传(做种)状态变为暂停状态 -> 触发缺文件扫描"""
        prev = self._group_state_snapshot.get(tor.hash)
        if prev is None:
            return False
        return prev.lower() in _UPLOADING_STATES and self._is_paused(tor)
