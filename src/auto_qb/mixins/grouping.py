"""种子分组管理(辅种管理) mixin: 将指向相同文件列表的种子归为一组, 统一检查处理

分组键: (规范化 save_path, 排序后的文件相对路径元组) — 文件列表相同 = 路径集合相同(不含大小,
以便把大小不一致的种子也归入同组做二次判定)。

组内处理(每轮全局任务):
  1. 文件大小一致性: 组内种子的 {路径: 大小} 映射不一致 -> 警告 + 整组暂停(不添加标签)
  2. 状态变化触发缺文件检查: 组内任一种子状态与上一轮快照不同 -> 触发一次磁盘扫描(同组共享)
     文件丢失 -> 整组暂停 + 添加 MISSING 标签(需求: 同组所有种子全部触发丢失动作)

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/_add_tags。
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
        """全局任务: 全量种子分组检查(替代逐种子 missing_files 任务)

        每轮: 一次全量 torrents_info + 一次全量 torrents_files(满足大库性能:
        分组键计算与缺文件磁盘扫描共用同一次文件列表获取)。
        """
        try:
            torrents = self.client.torrents_info()
        except Exception as e:
            self.logger.error(f"分组检查获取种子列表失败: {e}")
            return True

        # 1. 一次全量文件列表获取: hash -> {规范化相对路径: 大小}
        file_maps: Dict[str, Dict[str, int]] = {}
        for tor in torrents:
            try:
                files = self.client.torrents_files(tor.hash)
            except Exception as e:
                self.logger.debug(f"分组检查获取文件列表失败({tor.hash}): {e}")
                continue
            file_maps[tor.hash] = {_path_normalize(f.name): f.size for f in files}

        # 2. 构建分组: key = (save_path, 排序后的文件路径元组)
        groups: Dict[tuple, List[Any]] = {}
        for tor in torrents:
            fmap = file_maps.get(tor.hash)
            if fmap is None:
                continue  # 文件列表获取失败, 本轮跳过该种子
            key = (_path_normalize(tor.save_path), tuple(sorted(fmap.keys())))
            groups.setdefault(key, []).append(tor)

        # 3. 逐组处理
        for members in groups.values():
            self._process_group(members, file_maps, dry_run)

        # 4. 更新状态快照(仅保存本轮可见种子的状态; 新种子下次视为"状态变化"触发检查)
        self._group_state_snapshot = {t.hash: t.state for t in torrents}
        return True

    def _process_group(self, members: list, file_maps: Dict[str, Dict[str, int]], dry_run: bool):
        """处理一组种子: 大小一致性检查 + 状态变化触发的缺文件联动"""
        # 1. 组内文件大小一致性: 各种子 {路径: 大小} 映射不一致 -> 警告 + 整组暂停
        size_sets = {tuple(sorted(fmap.items())) for fmap in (file_maps.get(t.hash, {}) for t in members)}
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
        for fname, fsize in file_maps.get(rep.hash, {}).items():
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
