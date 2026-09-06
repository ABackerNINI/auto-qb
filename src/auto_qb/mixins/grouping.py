"""种子分组管理(辅种管理) mixin: 将指向相同文件列表的种子归为一组, 统一检查处理

分组键: (规范化 save_path, 排序后的文件相对路径元组) — 文件列表相同 = 路径集合相同(不含大小,
以便把大小不一致的种子也归入同组做二次判定)。

分组维护(增量, 事件驱动, 无周期轮询任务):
  - 维护成员索引 store.member_to_key(hash -> 组 key): 删除/状态变化/save_path 同步时
    O(1) 定位种子所属组, 不做全量遍历; 与 store.groups/store.group_sizes 在归组/移组时同步更新
  - _refresh_torrents 每轮拉全量种子列表, 检测增删与状态变化并立即处理:
    * 新增种子 -> _assign_new_torrent 增量归组(程序启动首轮的现有种子同样逐个归组);
      归组时检查文件大小一致性(文件列表轻易不变, 仅新增时检查, 不每轮检查):
      组内 {路径: 大小} 映射不一致 -> 警告 + 整组暂停(不添加标签)
    * 删除种子 -> _handle_removed_torrents: 移出组; 组内仍有剩余种子 -> 立即触发缺文件磁盘扫描
    * 种子由上传(做种)状态转为暂停状态 -> _handle_state_transitions 立即触发缺文件磁盘扫描(不等下一轮)
    * 保存路径变化 -> _handle_save_path_changes 按新路径重归组; 原组剩余成员与新组已有成员均触发缺文件磁盘扫描
    * 下载冲突(每轮, 分组 enabled 时) -> _check_download_conflicts: 同组两个及以上种子同时下载,
      或已完成与下载中并存 -> 警告 + 整组暂停(内存 set 去重, 冲突消除后清除)
  - 缺文件磁盘扫描: 组内取一个已完成且做种的种子作代表扫描磁盘(同组共享一次);
    文件丢失 -> 整组暂停 + 添加 MISSING 标签(同组所有种子全部触发丢失动作)
  - checking 动作辅助(供 rules/actions.py 调用): _group_members(成员 hash 列表)/
    _group_has_downloading(组内活跃下载判定)/_group_reference_candidates(已完成且未校验参考候选)

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/_add_tags,
以及 self.store(TorrentStore) 内聚的 _groups/_group_sizes/_member_to_key/state_snapshot/by_hash。
"""
import logging
import os
from typing import Any, Dict, Optional
from qbittorrentapi import Client, TorrentState

from ..config import Config
from .. import utils
from ..torrents import TorrentStore, TorrentRecord

logger = logging.getLogger(__name__)


class GroupingMixin:
    """种子分组管理(辅种管理): 分组 + 组内大小一致性 + 状态变化触发的缺文件联动"""

    client: Optional[Client]
    store: TorrentStore
    config: Config

    def _handle_removed_torrents(self, removed_hashes: list[str], dry_run: bool):
        """删除事件处理: 组内种子被删除 -> 移出分组; 组内仍有剩余种子 -> 立即触发缺文件扫描(可能文件丢失) """
        if not self.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 缺文件检查
        affected = set()
        for h in removed_hashes:
            key = self._leave_group(h)
            if key is not None:
                affected.add(key)
        for key in affected:
            members = self.store.groups.get(key, [])
            torrents = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
            if torrents:
                self._check_missing_files(torrents, self.store.group_sizes.get(key, {}), dry_run)

    def _handle_save_path_changes(self, dry_run: bool):
        """保存路径变化处理: 种子 save_path 变化 -> 移出原组按新路径重归组; 原组与新组触发缺文件扫描

        触发扫描(事件驱动, 同组只扫一次, 循环后统一处理):
          - 原组: 种子离开后组内仍有剩余成员 -> 立即扫描(文件可能随路径变化而丢失)
          - 新组: 已有其它成员(非仅本种子) -> 归组后也扫描一次(新种子可能补齐或缺失文件)
        文件列表变化(路径增删)在 qB 中需重加种子, 会走 _assign_new_torrent 重新归组, 这里不处理;
        已删种子由删除事件(_handle_removed_torrents)处理, 这里不重复清理。
        """
        triggered = set()
        for h, torrent in self.store.by_hash.items():
            key = self.store.member_to_key.get(h)
            if key is None or utils.path_normalize(torrent.save_path) == key[0]:
                continue
            old_map = self.store.group_sizes.get(key, {}).get(h)
            if not old_map:
                continue  # 无缓存文件映射, 无从重归组与扫描(维持原行为)
            remain_key = self._leave_group(h)  # 移出原组(成员索引 O(1)); 组空则返回 None
            if remain_key is not None:
                triggered.add(remain_key)  # 原组: 剩余成员触发缺文件扫描
            self._assign_to_group(torrent, old_map, dry_run)  # 新 save_path + 原文件列表重归组
            new_key = self.store.member_to_key.get(h)
            if new_key is not None and len(self.store.groups[new_key]) > 1:
                triggered.add(new_key)  # 新组: 已有其它成员, 归组后触发一次扫描

        if not self.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 缺文件检查
        for key in triggered:
            members = [self.store.by_hash[m] for m in self.store.groups.get(key, []) if m in self.store.by_hash]
            if members:
                self._check_missing_files(members, self.store.group_sizes.get(key, {}), dry_run)

    def _handle_state_transitions(self, dry_run: bool):
        """
        状态变化处理: 种子由上传(做种)转为暂停状态 -> 所属组立即触发缺文件扫描(同组只扫一次)

        状态快照(store.state_snapshot)存上一轮各种子的 state_enum 枚举对象,
        与 qB 版本无关(老版 pausedUP / 新版 stoppedUP 归为同一 is_paused 类别):
        遍历本轮种子先过滤暂停状态, 再对比上一轮快照为上传(做种)类别即触发;
        状态变化在检测到的同一轮立即处理, 不等下一轮。
        """
        if not self.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 缺文件检查
        triggered = set()
        for h, torrent in self.store.by_hash.items():
            # 跳过未完成或非暂停种子
            if not torrent.state_enum.is_complete or not torrent.state_enum.is_stopped:
                continue
            prev = self.store.state_snapshot.get(h)  # 上一轮 state_enum 枚举
            if prev is not None and getattr(prev, "is_uploading", False):
                key = self.store.member_to_key.get(h)
                if key is not None:
                    triggered.add(key)
        for key in triggered:
            members = self.store.groups[key]
            torrent = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
            if torrent:
                self._check_missing_files(torrent, self.store.group_sizes.get(key, {}), dry_run)

    def _assign_new_torrent(self, hash: str, dry_run: bool = False):
        """新增种子增量归组: 仅拉取该种子的文件列表并入组(store O(1) 定位, 不做全量遍历) """
        torrent = self.store.get(hash)
        files = torrent.files(self.client)
        self._assign_to_group(torrent, {utils.path_normalize(f.name): f.size for f in files}, dry_run)

    def _assign_to_group(self, torrent: TorrentRecord, file_map: Dict[str, int], dry_run: bool = False):
        """将种子按文件列表归入分组(幂等): 先移出旧组再加入新组; 维护成员索引; 归组后检查大小一致性"""
        if not file_map:
            return
        key = (utils.path_normalize(torrent.save_path), tuple(sorted(file_map.keys())))
        self._leave_group(torrent.hash)  # 幂等: 移出旧组(可能因 save_path 变化被重归组), 不触发扫描
        self.store.groups.setdefault(key, []).append(torrent.hash)
        self.store.group_sizes.setdefault(key, {})[torrent.hash] = file_map
        self.store.member_to_key[torrent.hash] = key
        # 文件大小一致性: 仅新增/重归组时检查(文件列表轻易不变, 无需每轮检查)
        self._check_size_consistency(key, dry_run)

    def _check_size_consistency(self, key: str, dry_run: bool):
        """新增种子归组时检查组内文件大小一致性: 组内 {路径: 大小} 不一致 -> 警告 + 整组暂停(不加标签) """
        members = self.store.groups[key]
        if len(members) <= 1:
            return
        torrents = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
        if not self._size_mismatch(torrents, self.store.group_sizes[key]):
            return
        desc = ", ".join(t.log_repr for t in torrents)
        logger.warning(f"辅种组({len(torrents)}个) | 文件大小不一致, 暂停整组: {desc}")
        if not dry_run:
            self.api.torrents_stop(torrent_hashes=[t.hash for t in torrents])

    def _leave_group(self, hash: str):
        """将种子移出所在分组(成员索引 O(1) 定位, 不做全量遍历); 组空则删除整组

        返回移除后组内仍有剩余成员的组 key(无则 None); 不触发缺文件扫描,
        重归组(_assign_to_group)与删除(_handle_removed_torrents)共用, 是否扫描由调用方决定。
        """
        key = self.store.member_to_key.pop(hash, None)
        if key is None:
            return None
        members = self.store.groups.get(key, [])
        if hash in members:
            members.remove(hash)
        self.store.group_sizes.get(key, {}).pop(hash, None)
        if not members:
            del self.store.groups[key]
            self.store.group_sizes.pop(key, None)
            return None
        return key

    @staticmethod
    def _size_mismatch(members: list[TorrentRecord], sizes: Dict[str, Dict[str, int]]) -> bool:
        """组内文件大小一致性: 各种子 {路径: 大小} 映射不一致返回 True(仅新增归组时检查) """
        size_sets = {tuple(sorted(fmap.items())) for fmap in (sizes.get(t.hash, {}) for t in members)}
        return len(size_sets) > 1

    @staticmethod
    def _valid_for_representative(torrent: TorrentRecord) -> bool:
        """候选项有效: 已完成且正在做种的种子可作为组内缺文件扫描的代表种"""
        state_enum = torrent.state_enum
        return (
            torrent.amount_left <= 0 and state_enum.is_complete and state_enum.is_uploading and
            not state_enum.is_checking and not state_enum.is_errored and not state_enum == TorrentState.MOVING
        )

    def _check_missing_files(self, members: list[TorrentRecord], sizes: Dict[str, Dict[str, int]], dry_run: bool):
        """
        缺文件磁盘扫描(同组共享一次): 文件丢失 -> 整组暂停 + MISSING 标签

        由删除事件(_handle_removed_torrents)或状态变化检测(_handle_state_transitions)或种子保存路径变化(_handle_save_path_changes)
        在满足触发条件(组内 种子被删除 / 种子由上传转暂停 / 种子保存路径变化)时立即调用。
        sizes: 组内缓存的文件大小映射 {hash: {规范化相对路径: 大小}}(增量归组时拉取, 复用)
        """
        if not self.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 组内取一个已完成且正在做种的种子作为代表
        rep = next((t for t in members if self._valid_for_representative(t)), None)
        if rep is None:
            return  # 组内无已完成做种种子(均在下载/暂停/移动), 不检查

        logger.debug(f"辅种组({len(members)}个) | 检查文件丢失(代表种: {rep.log_repr})")
        missing = False
        for fname, fsize in sizes.get(rep.hash, {}).items():
            full_path = utils.add_long_path_prefix_for_win(os.path.normpath(os.path.join(rep.save_path, fname)))
            if not os.path.exists(full_path):
                logger.warning(f"辅种组 | 文件缺失: '{full_path}'")
                missing = True
                break
            try:
                if os.path.getsize(full_path) != fsize:
                    logger.warning(f"辅种组 | 文件大小不一致: '{full_path}', 期望 {fsize}")
                    missing = True
                    break
            except OSError:
                logger.warning(f"辅种组 | 文件无法读取: '{full_path}'")
                missing = True
                break

        if missing:
            # 文件丢失: 同组所有种子全部触发丢失动作(暂停 + MISSING 标签)
            tag = self.config.grouping.missing_tag
            # 成员紧凑格式 hash8[站点]: 同名录种共享名称, 逐个 log_repr 会重复大段名称
            desc = ", ".join(f"{t.hash[:8]}[{t.tracker_name}]" for t in members)
            logger.warning(f"辅种组({len(members)}个) | 文件丢失, 暂停整组并添加标签 '{tag}': {desc}")
            if not dry_run:
                self.api.torrents_stop(torrent_hashes=[t.hash for t in members])
            for t in members:
                self._add_tags(t, [tag], dry_run, log_level=logging.DEBUG)

    # ---------- 下载冲突检查(每轮, 分组 enabled 时) ----------

    def _check_download_conflicts(self, dry_run: bool):
        """下载冲突检查: 同组两个及以上种子同时下载 / 已完成与下载中并存 -> 警告 + 整组暂停

        设计(想法.md):
          - 同组中两个及以上的种子同时下载 -> 暂停并发出警告
          - 同组中有已完成的种子和正在下载的种子 -> 暂停并发出警告
        去重: store.download_conflict_warned 记录 (组key, 冲突类型), 冲突持续不重复暂停
        (暂停幂等), 冲突消除后清除; 触发: _refresh_torrents 每轮调用(分组 enabled 时),
        状态快照在调用前已更新。
        """
        warned = self.store.download_conflict_warned
        # 1. 扫描各组统计下载中/已完成成员
        active = set()
        for key, members in self.store.groups.items():
            torrents = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
            n_dl = sum(
                1 for t in torrents if t.state_enum.is_downloading and not t.state_enum.is_stopped and
                not t.state_enum.is_checking and t.amount_left > 0
            )
            n_done = sum(1 for t in torrents if t.state_enum.is_complete and t.amount_left <= 0)
            if n_dl >= 2:
                active.add((key, "multi-dl"))
            elif n_dl == 1 and n_done >= 1:
                active.add((key, "mixed"))
        # 2. 冲突消除: 清除去重记录(下次重现时再次警告+暂停)
        for tag in list(warned):
            if tag not in active:
                warned.discard(tag)
        # 3. 新冲突: 警告 + 整组暂停(dry-run 只报告, 不记录去重, 下次真实执行仍会暂停)
        for key, kind in active:
            if (key, kind) in warned:
                continue
            torrents = [self.store.by_hash[h] for h in self.store.groups[key] if h in self.store.by_hash]
            desc = ", ".join(t.log_repr for t in torrents)
            if kind == "multi-dl":
                logger.warning(f"辅种组({len(torrents)}个) | 多个种子同时下载, 暂停整组: {desc}")
            else:
                logger.warning(f"辅种组({len(torrents)}个) | 已完成与下载中并存, 暂停整组: {desc}")
            if dry_run:
                continue
            warned.add((key, kind))
            self.api.torrents_stop(torrent_hashes=[t.hash for t in torrents])

    # ---------- 校验动作(checking)辅助: 组上下文 ----------

    def _group_members(self, hash: str) -> list:
        """种子所属组全部成员 hash 列表; 未归组/分组未启用 -> [自身] 单种子(无参考)"""
        return self.store.group_members(hash)

    def _group_by_hash(self) -> Dict[str, TorrentRecord]:
        """最近一轮种子快照的 hash -> 种子 映射(checking 动作用, 无需额外拉取) """
        return self.store.by_hash

    def _group_has_downloading(self, members: list[str]) -> bool:
        """组内是否存在活跃下载种子: 存在 -> 整组未完成, 不进行任何校验(包括跳检) """
        by_hash = self.store.by_hash
        for h in members:
            if h not in by_hash:
                continue
            state_enum = by_hash[h].state_enum
            if state_enum.is_downloading and not state_enum.is_stopped and not state_enum.is_checking:
                return True
        return False

    def _group_reference_candidates(self, members: list[str]) -> list:
        """组内已完成且未在校验的成员列表, 作为参考种子候选(想法2: filelist 参考定义)

        is_complete 而非 is_uploading: 暂停/停止做种的完成成员亦是有效参考
        (参考用的是元数据 filelist/piece hashes, 与暂停状态无关), 否则整组
        停种后无参考。排除 checking: 参考自身完整性正被重校验质疑, 不得作为
        跳检依据。
        """
        by_hash = self.store.by_hash
        return [
            by_hash[h] for h in members
            if h in by_hash and by_hash[h].state_enum.is_complete and not by_hash[h].state_enum.is_checking
        ]
