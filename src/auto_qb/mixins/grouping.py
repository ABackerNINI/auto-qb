"""种子分组管理(辅种管理) mixin: 将指向相同文件列表的种子归为一组, 统一检查处理

分组键: (规范化 save_path, 排序后的文件相对路径元组) — 文件列表相同 = 路径集合相同(不含大小,
以便把大小不一致的种子也归入同组做二次判定)。

分组维护(增量, 无初始化全量分组):
  - _refresh_torrents 检测到新增种子时增量归组(_assign_new_torrent), 程序启动首轮的
    现有种子同样作为新增逐个归组; 删除种子时从组中移除(_remove_from_groups)
  - 每轮分组检查仅拉一次全量 torrents_info, 组内文件大小映射复用缓存的 _group_sizes,
    不再逐种子拉取文件列表(大库性能)

组内处理(每轮全局任务):
  1. 文件大小一致性: 组内种子的 {路径: 大小} 映射不一致 -> 警告 + 整组暂停(不添加标签)
  2. 状态变化触发缺文件检查: 组内任一种子状态与上一轮快照不同 -> 触发一次磁盘扫描(同组共享)
     文件丢失 -> 整组暂停 + 添加 MISSING 标签(需求: 同组所有种子全部触发丢失动作)

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/_add_tags/_snapshot,
以及 qbmanager 初始化的 _groups/_group_sizes/_group_state_snapshot。
"""
import logging
import os
from typing import Any, Dict, List

from ..utils import _path_normalize, add_long_path_prefix_for_win

logger = logging.getLogger("auto-qb")


class GroupingMixin:
    """种子分组管理(辅种管理): 分组 + 组内大小一致性 + 状态变化触发的缺文件联动"""

    client: Any
    logger: Any
    config: Any

    def _handle_grouping(self, task, dry_run: bool) -> bool:
        """全局任务: 分组检查(增量维护分组, 替代逐种子 missing_files 任务)

        每轮: 一次全量 torrents_info(取状态/保存路径) + 复用缓存的组内文件大小映射,
        不再拉取任何文件列表; 分组由 _refresh_torrents 在增删种子时增量维护
        (全部经 _assign_new_torrent 归组, 无初始化全量分组)。
        """
        try:
            torrents = self.client.torrents_info()
        except Exception as e:
            self.logger.error(f"分组检查获取种子列表失败: {e}")
            return True

        # 同步分组: 清理已删种子, 处理保存路径变化(文件列表变化需重加种子, 罕见不处理)
        by_hash = {t.hash: t for t in torrents}
        self._sync_groups(by_hash)

        # 逐组检查(复用缓存的大小映射, 不逐种子拉文件列表)
        for key, members in list(self._groups.items()):
            tos = [by_hash[h] for h in members if h in by_hash]
            if tos:
                self._process_group(tos, self._group_sizes.get(key, {}), dry_run)

        # 更新状态快照(仅保存本轮可见种子的状态; 新种子下次视为"状态变化"触发检查)
        self._group_state_snapshot = {t.hash: t.state for t in torrents}
        return True

    def _assign_new_torrent(self, torrent_hash: str):
        """新增种子增量归组: 仅拉取该种子的文件列表并入组(每次一个种子, 不做全量遍历)"""
        tor = next((t for t in self._snapshot if t.hash == torrent_hash), None)
        if tor is None:
            return
        try:
            files = self.client.torrents_files(torrent_hash)
        except Exception as e:
            self.logger.debug(f"分组归组获取文件列表失败({torrent_hash}): {e}")
            return
        self._assign_to_group(tor, {_path_normalize(f.name): f.size for f in files})

    def _assign_to_group(self, tor, file_map: Dict[str, int]):
        """将种子按文件列表归入分组(幂等): 先移出旧组再加入新组"""
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

    def _remove_from_groups(self, torrent_hash: str):
        """种子被删除时从分组中移除"""
        for key, members in list(self._groups.items()):
            if torrent_hash in members:
                members.remove(torrent_hash)
                self._group_sizes[key].pop(torrent_hash, None)
                if not members:
                    del self._groups[key]
                    self._group_sizes.pop(key, None)
                return

    def _sync_groups(self, by_hash: Dict[str, Any]):
        """同步分组: 清理已删种子, 处理保存路径变化的种子(按新路径重归组)

        文件列表变化(路径增删)在 qB 中需重加种子, 会走 _assign_new_torrent 重新归组, 这里不处理。
        """
        for key, members in list(self._groups.items()):
            kept = []
            for h in members:
                tor = by_hash.get(h)
                if tor is None:
                    self._group_sizes[key].pop(h, None)  # 已删种子(双保险, 正常由 _remove_from_groups 处理)
                    continue
                if _path_normalize(tor.save_path) != key[0]:
                    old_map = self._group_sizes[key].pop(h, None)
                    if old_map:
                        self._assign_to_group(tor, old_map)  # 新 save_path + 原文件列表重归组
                    continue
                kept.append(h)
            if len(kept) != len(members):
                members[:] = kept
                if not members:
                    del self._groups[key]
                    self._group_sizes.pop(key, None)

    def _process_group(self, members: list, sizes: Dict[str, Dict[str, int]], dry_run: bool):
        """处理一组种子: 大小一致性检查 + 状态变化触发的缺文件联动

        sizes: 组内缓存的文件大小映射 {hash: {规范化相对路径: 大小}}(增量归组时拉取, 每轮复用)
        """
        # 1. 组内文件大小一致性: 各种子 {路径: 大小} 映射不一致 -> 警告 + 整组暂停
        size_sets = {tuple(sorted(fmap.items())) for fmap in (sizes.get(t.hash, {}) for t in members)}
        if len(size_sets) > 1:
            desc = ", ".join(f"{t.name}[{t.hash[:8]}]" for t in members)
            self.logger.warning(f"辅种组文件大小不一致({len(members)}个种子), 暂停整组: {desc}")
            if not dry_run:
                self.client.torrents_stop(torrent_hashes=[t.hash for t in members])
            return

        # 2. 状态变化触发检查(需求): 组内任一种子状态与上一轮快照不同才触发磁盘扫描
        if not any(t.state != self._group_state_snapshot.get(t.hash) for t in members):
            return

        # 3. 缺文件磁盘扫描(同组共享一次): 组内取一个已完成且正在做种的种子作为代表
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
        return (tor.state or "").lower() in ("uploading", "stalledup", "forcedup", "checkingup")
