"""GroupingModule: 种子分组管理(辅种管理)的模块化封装(plan kernel-module-refactor P4)

GroupingMixin(387 行)整体迁入, 经四个刷新相位被内核广播(plan §4.2 相位表, 次序 =
原 _refresh_torrents 调用顺序的忠实编码):
- transitions:    任何自有动作之前(上传转暂停/进入 errored 用上一轮快照观测, §4.2);
- torrents_added: 逐新增种子的归组一步(P5 收口前相位里只有本模块认领, 其余各家 P5 随
                  逐种子管线一起迁入);
- removed_scan:   删除后组内缺文件扫描;
- post:           保存路径重归组 + 跨组文件交叉检测 + 下载冲突检查(每轮收尾)。
`grouping.enabled` 的启用开关由模块**自判**(plan §3.1: 启用开关属模块), 内核只广播相位。

缺文件扫描的轮内去重集合(_missing_scanned_keys)收进模块实例: 原内核 _refresh_torrents
每轮开头的无条件 clear 移到 transitions 处理器入口(分组各相位中每轮最早者, 在 enabled
判定之前清) —— 时序与原实现逐字节等价。

!client 经 ctx.api.client **现取**(不缓存): 重连换客户端时 QbApi.bind 同步更新
  (manager.client setter 的同步链), 模块侧永远拿到当前客户端。
!打标经 ctx.maintenance.add_tags(模块句柄经 ctx 取, 不 import 兄弟模块): MISSING 标签
  的添加/去重/日志语义单点在 maintenance 模块。

group_key_of 纯函数随迁(scripts/qb_capture.py 语料抓取器 import 同一份公式, 单一事实源)。
"""
import logging
import os
from collections.abc import Mapping
from typing import Any, Dict

from ...infra import file_access, utils
from ...torrents import TorrentRecord
from ..module import AppContext, BaseModule

logger = logging.getLogger(__name__)

# 「原名缺失但 .!qB 孪生存在」过渡态的连续容忍上限(issue 26-09-21-0219 / plan 26-09-22-2038):
# 三个触发源(删除事件 / save_path 变化 / 状态转移)在移动场景常同轮命中同一组, 轮内去重后
# 只扫一次 —— 连续 3 次独立事件都撞上改名窗口, 大概率是 qB 残留而非窗口, 兜底按真实缺失处理。
# 常量不进配置: 触发条件本身已足够窄(原名缺失 且 孪生存在), 默认开启符合最小惊讶。
TRANSITIONAL_SKIP_LIMIT = 3


def group_key_of(save_path: str, file_map: Mapping[str, int]):
    """归组 key 的单一事实源: (规范化 save_path, 排序后的文件相对路径元组)

    与 _assign_to_group 共用。抽成模块级纯函数是为了让 scripts/ 侧的语料抓取器
    (真值分组 / 等价类守恒校验) import 同一份公式, 避免复制副本与 :150 悄悄分叉 ——
    否则 CORPUS.group_exact 会拿"错误的期望"判"正确的实现"(稳定假红或假绿)。
    纯函数, 无状态, 不读 self; 行为与抽取前完全一致。
    """
    return (utils.path_normalize(save_path), tuple(sorted(file_map.keys())))


def _cross_physical_key(dir_resolved: str, rel_path: str) -> str:
    """跨组交叉检测专用的物理路径键: 目录解析结果 + 相对路径做 normcase+normpath 词法归一

    与 group_key_of 的 path_normalize 分层: 归组键保持词法形态(大小写/别名不折叠, 分组键
    单一事实源, 严禁改 path_normalize), 物理键在此叠加大小写折叠(仅 normcase 生效的平台
    (Windows)折叠, POSIX 恒等即不误报)与调用方预先完成的目录级别名解析(realpath_lexical)。
    纯函数, 只做字符串运算不触盘。
    """
    return os.path.normcase(os.path.normpath(os.path.join(dir_resolved, rel_path)))


class GroupingModule(BaseModule):
    """grouping 模块: 分组 + 组内大小一致性 + 状态变化触发的缺文件联动 + 下载冲突检查

    实现自 GroupingMixin 原样迁入(self.store/api/config 改经 ctx 现取); 相位认领见
    subscribe, 启用开关与去重集合的归属见模块 docstring。
    """

    name = "grouping"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        # 缺文件扫描轮内去重: 移动种子等场景同一轮会命中多个触发源(状态转移+路径变化),
        # 同组 key 同轮只扫一次; 每轮开始(transitions 相位入口)无条件清空
        self._missing_scanned_keys: set = set()

    def sections(self) -> tuple[str, ...]:
        return ("grouping", )

    # ---------- 相位订阅(plan §4.2: transitions / torrents_added / removed_scan / post) ----------

    def subscribe(self, phases) -> None:
        phases.on("transitions", self._on_transitions)
        phases.on("torrents_added", self._on_torrents_added)
        phases.on("removed_scan", self._on_removed_scan)
        phases.on("post", self._on_post)

    def _on_transitions(self, event) -> None:
        # 去重集合清零必须在 enabled 判定之前: 与原 _refresh_torrents 每轮开头无条件
        # clear 同口径, 否则 enabled 翻转后残留 key 会吞掉首轮合法扫描
        self._missing_scanned_keys.clear()
        if not self._ctx.config.grouping.enabled:
            return  # 启用开关模块自判(plan §3.1)
        self._handle_state_transitions(event.payload.get("dry_run", False))

    def _on_torrents_added(self, event) -> None:
        if not self._ctx.config.grouping.enabled:
            return
        self._assign_new_torrent(event.payload["hash"], event.payload.get("dry_run", False))

    def _on_removed_scan(self, event) -> None:
        if not self._ctx.config.grouping.enabled:
            return
        self._handle_removed_torrents(event.payload.get("hashes", []), event.payload.get("dry_run", False))

    def _on_post(self, event) -> None:
        if not self._ctx.config.grouping.enabled:
            return
        dry_run = event.payload.get("dry_run", False)
        self._handle_save_path_changes(dry_run)
        # 跨组检测挂在同组检查之前且对 dirty_groups 只读(单一消费点仍是 _check_download_conflicts,
        # 两套检查共用同一份变化登记, plan 26-10-04-0107 §04 插入位置 note)
        self._check_cross_group_file_conflicts(dry_run)
        self._check_download_conflicts(dry_run)

    # ---------- 删除事件 ----------

    def _handle_removed_torrents(self, removed_hashes: list[str], dry_run: bool):
        """删除事件处理: 组内种子被删除 -> 移出分组; 组内仍有剩余种子 -> 立即触发缺文件扫描(可能文件丢失) """
        if not self._ctx.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 缺文件检查
        affected = set()
        for h in removed_hashes:
            key = self._leave_group(h)
            if key is not None:
                affected.add(key)
        for key in affected:
            members = self._ctx.store.groups.get(key, [])
            torrents = [self._ctx.store.by_hash[h] for h in members if h in self._ctx.store.by_hash]
            if torrents:
                self._check_missing_files(torrents, self._ctx.store.group_sizes.get(key, {}), dry_run, key)

    def _handle_save_path_changes(self, dry_run: bool):
        """保存路径变化处理: 种子 save_path 变化 -> 移出原组按新路径重归组; 原组与新组触发缺文件扫描

        触发扫描(事件驱动, 同组只扫一次, 循环后统一处理):
          - 原组: 种子离开后组内仍有剩余成员 -> 立即扫描(文件可能随路径变化而丢失)
          - 新组: 已有其它成员(非仅本种子) -> 归组后也扫描一次(新种子可能补齐或缺失文件)
        文件列表变化(路径增删)在 qB 中需重加种子, 会走 _assign_new_torrent 重新归组, 这里不处理;
        已删种子由删除事件(_handle_removed_torrents)处理, 这里不重复清理。
        """
        store = self._ctx.store
        triggered = set()
        for h, fields in store.delta_fields.items():
            if "save_path" not in fields:
                continue  # 仅保存路径变化的种子可能需重归组(增量)
            torrent = store.by_hash.get(h)
            if torrent is None:
                continue
            key = store.member_to_key.get(h)
            if key is None or utils.path_normalize(torrent.save_path) == key[0]:
                continue
            old_map = store.group_sizes.get(key, {}).get(h)
            if not old_map:
                continue  # 无缓存文件映射, 无从重归组与扫描(维持原行为)
            remain_key = self._leave_group(h)  # 移出原组(成员索引 O(1)); 组空则返回 None
            if remain_key is not None:
                triggered.add(remain_key)  # 原组: 剩余成员触发缺文件扫描
            self._assign_to_group(torrent, old_map, dry_run)  # 新 save_path + 原文件列表重归组
            new_key = store.member_to_key.get(h)
            if new_key is not None and len(store.groups[new_key]) > 1:
                triggered.add(new_key)  # 新组: 已有其它成员, 归组后触发一次扫描

        if not self._ctx.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 缺文件检查
        for key in triggered:
            members = [store.by_hash[m] for m in store.groups.get(key, []) if m in store.by_hash]
            if members:
                self._check_missing_files(members, store.group_sizes.get(key, {}), dry_run, key)

    def _handle_state_transitions(self, dry_run: bool):
        """
        状态变化处理: 组内种子发生缺文件关联的状态转移 -> 所属组立即触发缺文件扫描(同组只扫一次)

        两条触发路径(状态快照 store.state_snapshot 存上一轮 state_enum 枚举对象, 与 qB 版本无关):
          1. 上传(做种)转为暂停完成: 做种中文件可能被外部删除, 转暂停后不再主动读盘, 需扫描确认
          2. 进入 errored(missingFiles/error): 重校验/恢复发现文件缺失是缺文件的第一现场,
             同组共享物理文件须整体确认(修复: 原仅检测"上传转暂停", 校验发现缺失不触发任何扫描,
             组继续"健康"做种, 用户重新下载又被 mixed 冲突拦截)
        状态变化在检测到的同一轮立即处理, 不等下一轮; 持续 errored 不重复触发(仅转换拍触发);
        触发点用 errored 布尔属性而非枚举具体状态名, 不依赖 checkingUP/checkingResumeData
        等中间状态的映射细节。
        """
        if not self._ctx.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 缺文件检查: 只有本轮 state 字段变化的种子才可能命中(增量应用时收集)
        store = self._ctx.store
        triggered = set()
        state_snapshot = store.state_snapshot
        member_to_key = store.member_to_key
        for h, cur in store.state_changed:
            prev = state_snapshot.get(h)  # 上一轮 state_enum 枚举
            if prev is None:
                continue  # 首轮无上一轮快照, 不视为状态变化(与上传转暂停路径一致)
            if not (
                (cur.is_complete and cur.is_stopped and prev.is_uploading) or (cur.is_errored and not prev.is_errored)
            ):
                continue
            key = member_to_key.get(h)
            if key is not None:
                triggered.add(key)
        for key in triggered:
            members = store.groups[key]
            torrent = [store.by_hash[h] for h in members if h in store.by_hash]
            if torrent:
                self._check_missing_files(torrent, store.group_sizes.get(key, {}), dry_run, key)

    # ---------- 归组 ----------

    def _assign_new_torrent(self, hash: str, dry_run: bool = False):
        """新增种子增量归组: 仅拉取该种子的文件列表并入组(store O(1) 定位, 不做全量遍历) """
        torrent = self._ctx.store.get(hash)
        files = torrent.files(self._ctx.api.client)
        self._assign_to_group(torrent, {utils.path_normalize(f.name): f.size for f in files}, dry_run)

    def _assign_to_group(self, torrent: TorrentRecord, file_map: Dict[str, int], dry_run: bool = False):
        """将种子按文件列表归入分组(幂等): 先移出旧组再加入新组; 维护成员索引; 归组后检查大小一致性"""
        if not file_map:
            return
        store = self._ctx.store
        key = group_key_of(torrent.save_path, file_map)
        self._leave_group(torrent.hash)  # 幂等: 移出旧组(可能因 save_path 变化被重归组), 不触发扫描
        store.groups.setdefault(key, []).append(torrent.hash)
        store.group_sizes.setdefault(key, {})[torrent.hash] = file_map
        store.member_to_key[torrent.hash] = key
        store.dirty_groups.add(key)  # 成员变化 -> 该组冲突集合需重算
        # 文件大小一致性: 仅新增/重归组时检查(文件列表轻易不变, 无需每轮检查)
        self._check_size_consistency(key, dry_run)

    def _check_size_consistency(self, key: str, dry_run: bool):
        """新增种子归组时检查组内文件大小一致性: 组内 {路径: 大小} 不一致 -> 警告 + 整组暂停(不加标签) """
        store = self._ctx.store
        members = store.groups[key]
        if len(members) <= 1:
            return
        torrents = [store.by_hash[h] for h in members if h in store.by_hash]
        if not self._size_mismatch(torrents, store.group_sizes[key]):
            return
        desc = ", ".join(t.log_repr for t in torrents)
        logger.warning(f"辅种组({len(torrents)}个) | 文件大小不一致, 暂停整组: {desc}")
        if not dry_run:
            self._ctx.api.torrents_stop(torrent_hashes=[t.hash for t in torrents])

    def _leave_group(self, hash: str):
        """将种子移出所在分组(成员索引 O(1) 定位, 不做全量遍历); 组空则删除整组

        返回移除后组内仍有剩余成员的组 key(无则 None); 不触发缺文件扫描,
        重归组(_assign_to_group)与删除(_handle_removed_torrents)共用, 是否扫描由调用方决定。
        """
        store = self._ctx.store
        key = store.member_to_key.pop(hash, None)
        if key is None:
            return None
        store.dirty_groups.add(key)  # 成员变化 -> 该组冲突集合需重算(含组已被解散的情形)
        members = store.groups.get(key, [])
        if hash in members:
            members.remove(hash)
        store.group_sizes.get(key, {}).pop(hash, None)
        if not members:
            del store.groups[key]
            store.group_sizes.pop(key, None)
            return None
        return key

    @staticmethod
    def _size_mismatch(members: list[TorrentRecord], sizes: Dict[str, Dict[str, int]]) -> bool:
        """组内文件大小一致性: 各种子 {路径: 大小} 映射不一致返回 True(仅新增归组时检查) """
        size_sets = {tuple(sorted(fmap.items())) for fmap in (sizes.get(t.hash, {}) for t in members)}
        return len(size_sets) > 1

    @staticmethod
    def _valid_for_representative(torrent: TorrentRecord) -> bool:
        """候选项有效: 已完成或 errored 且未在校验的种子可作为组内缺文件扫描的代表种

        代表种只决定扫描谁的保存路径(组内共享)与复用缓存的文件映射, 不要求种子健康:
        missingFiles/errored 成员的 save_path 与缓存映射同样有效, 且恰是缺文件事件第一现场
        ——排除它会导致全组同时 errored(如同轮重校验多个成员)时无代表可扫
        (2026-09-12 放宽, 原为仅 is_complete); checkingUP 校验中完整性存疑仍排除;
        MOVING 不在 is_complete/is_errored 集合内, 无需显式排除。

        !与跳检参考种判据(_group_reference_candidates, 仅 is_complete)是**两口径**:
        扫描代表种允许 errored 成员(缺文件第一现场), 参考种不允许 —— 分模块后仍各自单点。
        """
        state_enum = torrent.state_enum
        return (state_enum.is_complete or state_enum.is_errored) and not state_enum.is_checking

    def _check_missing_files(
        self, members: list[TorrentRecord], sizes: Dict[str, Dict[str, int]], dry_run: bool, key: str
    ):
        """
        缺文件磁盘扫描(同组共享一次): 文件丢失 -> 整组暂停 + MISSING 标签

        由删除事件(_handle_removed_torrents)或状态变化检测(_handle_state_transitions)或种子保存路径变化(_handle_save_path_changes)
        在满足触发条件(组内 种子被删除 / 种子由上传转暂停 / 种子进入 errored(校验发现文件缺失) / 种子保存路径变化)时立即调用。
        sizes: 组内缓存的文件大小映射 {hash: {规范化相对路径: 大小}}(增量归组时拉取, 复用)
        key: 组 key, 用于轮内去重 —— 移动种子等场景同一轮会同时命中多个触发源(如状态转移+路径变化),
        同组同轮只扫一次(跨轮不抑制, 各轮事件仍各自检测)

        过渡态容忍(plan 26-09-22-2038, issue 26-09-21-0219): qB 移动种子时偶发把磁盘文件临时
        改名为 原名.!qB(搬运未完成后缀, 完成后改回), 改名窗口内原路径不存在属过渡态 —— 命中
        (原名缺失 且 原名+.!qB 孪生存在, 后缀成因保持中立, 只看可观测状态)时**整轮放弃判定**
        (目录处于改名窗口, 部分文件在、部分带后缀, 任何部分结论都不可靠): 不暂停、不打标, 等
        下一个触发事件再判; 连续 TRANSITIONAL_SKIP_LIMIT 次未消除视为 qB 残留, 按真实缺失兜底。
        连续计数存 store.transitional_missing_skips(仅内存, 不落盘, 跨轮存活) —— 正常判定
        (含真实缺失/大小不符/文件齐全)即清零重计; 大小不一致 / OSError 分支与窗口无关(原名存在),
        保持原判定; UNDETERMINED 早退路径未发生判定, 计数不动。dry-run 下容忍分支同样只报告,
        外部动作由下方原有 dry_run 闸门拦截。
        """
        if not self._ctx.config.grouping.check_missing_files:
            return  # 配置禁用缺文件检查

        # 组内取一个已完成且未在校验的种子作为代表
        rep = next((t for t in members if self._valid_for_representative(t)), None)
        if rep is None:
            return  # 组内无已完成未校验种子(均在下载/校验/异常), 不检查
        # 去重登记在代表确认之后: 无代表的调用未发生扫描, 不占轮内去重名额
        if key in self._missing_scanned_keys:
            return  # 同轮已扫描(多触发源命中同组)
        self._missing_scanned_keys.add(key)

        logger.debug(f"辅种组({len(members)}个) | 检查文件丢失(代表种: {rep.log_repr})")
        fa = file_access.get_file_access()
        missing = False
        transitional = False
        for fname, fsize in sizes.get(rep.hash, {}).items():
            full_path = os.path.normpath(os.path.join(rep.save_path, fname))
            exists = fa.exists(full_path)
            if exists is file_access.UNDETERMINED:
                # 映射 miss: 存在性不可判定 —— 跳过该组, 不暂停不打标(报告 §05 红线:
                # 配错映射时宁可功能退化, 不能照常返回 False 重演误暂停事故)
                logger.warning(f"辅种组 | 路径不可判定: '{full_path}'(未命中 fs.path_map 映射), 跳过本组缺文件扫描")
                return
            if not exists:
                # 原名缺失时才探测孪生(健康路径零新增 stat); 存在性同样经文件访问层三态语义,
                # 非 True(含 UNDETERMINED)一律按无孪生处理, 维持原判定
                if fa.exists(utils.qb_incomplete_twin_path(full_path)) is True:
                    transitional = True  # 改名窗口: 整轮放弃, 单文件结论不可靠
                    break
                logger.warning(f"辅种组 | 文件缺失: '{full_path}'")
                missing = True
                break
            try:
                if fa.getsize(full_path) != fsize:
                    logger.warning(f"辅种组 | 文件大小不一致: '{full_path}', 期望 {fsize}")
                    missing = True
                    break
            except OSError:
                logger.warning(f"辅种组 | 文件无法读取: '{full_path}'")
                missing = True
                break

        skips = self._ctx.store.transitional_missing_skips
        if transitional:
            n = skips.get(key, 0) + 1
            skips[key] = n
            if n < TRANSITIONAL_SKIP_LIMIT:
                logger.warning(
                    f"辅种组 | 疑似 qB 搬运过渡态({utils.QB_INCOMPLETE_SUFFIX}), 本轮不判缺文件"
                    f"(第{n}次): 代表种 {rep.log_repr}"
                )
                return  # 不暂停、不打标; 下一个触发事件再判
            logger.warning(f"辅种组 | 过渡态({utils.QB_INCOMPLETE_SUFFIX})连续 {n} 次未消除, 按真实缺失处理")
            missing = True  # 落入下方原有整组暂停 + MISSING 分支(残留兜底)
        else:
            # 正常判定结束(含真实缺失/大小不符/文件齐全): 清零重计, 连续次数只在相邻过渡态间累积
            skips.pop(key, None)

        if missing:
            # 文件丢失: 同组所有种子全部触发丢失动作(暂停 + MISSING 标签)
            tag = self._ctx.config.grouping.missing_tag
            # 成员紧凑格式 hash8[站点]: 同名录种共享名称, 逐个 log_repr 会重复大段名称
            desc = ", ".join(f"{t.hash[:8]}[{t.tracker_name}]" for t in members)
            logger.warning(f"辅种组({len(members)}个) | 文件丢失, 暂停整组并添加标签 '{tag}': {desc}")
            if not dry_run:
                self._ctx.api.torrents_stop(torrent_hashes=[t.hash for t in members])
            for t in members:
                self._ctx.maintenance.add_tags(t, [tag], dry_run, log_level=logging.DEBUG)

    # ---------- 下载冲突检查(post 相位: 每轮收尾) ----------

    def _check_download_conflicts(self, dry_run: bool):
        """下载冲突检查: 同组两个及以上种子同时下载 / 已完成与下载中并存 -> 警告 + 整组暂停

        设计(想法.md):
          - 同组中两个及以上的种子同时下载 -> 暂停并发出警告
          - 同组中有已完成的种子和正在下载的种子 -> 暂停并发出警告
        带 MISSING 标签的已完成成员不计入"已完成": MISSING 组是已知缺文件、等待用户处理的状态,
        用户恢复/重加种子重新下载是合法补救, 不应被 mixed 冲突拦停(健康完成成员不受影响,
        仍正常触发); multi-dl(两个同时下载写同一物理文件)与缺文件无关, 继续拦截。
        去重: store.download_conflict_warned 记录 (组key, 冲突类型), 冲突持续不重复暂停
        (暂停幂等), 冲突消除后清除。

        **增量**: 轮次基线已建立(store.rounds_applied > 0)时只重算 `store.dirty_groups` 中的组
        (判定依据字段 state/amount_left/tags 变化、成员增删、归组变化、自有停种/打标时登记),
        其余组的冲突集合与上轮一致 —— 静止种子库零成本; 去重记录的清理同样只针对被重算的组。
        基线未建立(直接驱动该方法的白盒测试/外部调用无变化集)时退回全量扫描。
        """
        store = self._ctx.store
        dirty = store.dirty_groups
        incremental = store.rounds_applied > 0
        if incremental and not dirty:
            return  # 本轮无冲突相关变化: 冲突集合与上轮一致
        store.dirty_groups = set()  # 取出本轮登记并复位(_apply 不清空, 跨轮累积)
        warned = store.download_conflict_warned
        missing_tag = self._ctx.config.grouping.missing_tag
        groups = store.groups
        by_hash = store.by_hash
        keys = dirty if incremental else groups.keys()
        key_set = dirty if incremental else set(groups)
        # 1. 重算脏组(或全量)的下载中/已完成成员数
        active = set()
        for key in keys:
            members = groups.get(key)
            if not members:
                continue  # 组已解散
            n_dl = 0
            n_done = 0
            for h in members:
                t = by_hash.get(h)
                if t is None:
                    continue
                e = t.state_enum
                if e.is_downloading and not e.is_stopped and not e.is_checking and t.amount_left > 0:
                    n_dl += 1
                if e.is_complete and t.amount_left <= 0 and missing_tag not in t.tags_set:
                    n_done += 1
            if n_dl >= 2:
                active.add((key, "multi-dl"))
            elif n_dl == 1 and n_done >= 1:
                active.add((key, "mixed"))
        # 2. 冲突消除: 清除被重算组的过期去重记录(下次重现时再次警告+暂停)
        for tag in list(warned):
            if tag[0] in key_set and tag not in active:
                warned.discard(tag)
        # 3. 新冲突: 警告 + 整组暂停(dry-run 只报告, 不记录去重, 下次真实执行仍会暂停)
        for key, kind in active:
            if (key, kind) in warned:
                continue
            torrents = [by_hash[h] for h in groups[key] if h in by_hash]
            desc = ", ".join(t.log_repr for t in torrents)
            if kind == "multi-dl":
                logger.warning(f"辅种组({len(torrents)}个) | 多个种子同时下载, 暂停整组: {desc}")
            else:
                logger.warning(f"辅种组({len(torrents)}个) | 已完成与下载中并存, 暂停整组: {desc}")
            if dry_run:
                continue
            warned.add((key, kind))
            self._ctx.api.torrents_stop(torrent_hashes=[t.hash for t in torrents])

    # ---------- 跨组文件交叉检测(post 相位: 消除 + 去重门 + 暂停涉事下载方, plan 26-10-04-0107) ----------

    def _check_cross_group_file_conflicts(self, dry_run: bool):
        """跨组文件交叉检测: 组边界不等于磁盘上不交叉, 交叉在场且下载中即警告并暂停涉事下载方

        场景(plan 26-10-04-0107 §01): (1)同 save_path 文件列表部分重叠; (2)文件名仅大小写不同
        (Windows 不区分大小写); (3)不同 save_path 经 junction/symlink/盘符别名指向同一物理目录。
        新种子下载会静默覆盖另一组已下载/已完成数据, 不可逆 —— 同组下载冲突检查覆盖不到
        (其 docstring 明确只做组内比较)。

        四步判定(展开 -> 事件 -> 豁免 -> 激活警告):
          1. 物理路径全量展开: store.groups x store.group_sizes 的相对路径拼 save_path, 经
             _cross_physical_key 归一成物理路径键, 建反向索引 path -> [(组key, hash)];
             目录部分经 file_access.realpath_lexical 解析别名(每个不同 save_path 只解析一次,
             syscall 次数 O(组数); Mapped 部署自动退化为词法归一, 保守不误报), 解析异常回退词法。
          2. 交叉事件: 同一物理路径被 >=2 个不同组 key 引用(同组多成员共享路径是分组定义的
             固有属性, 归同组检查管)。
          3. MISSING 豁免(D3): 事件任一参与者带 missing_tag -> 豁免该事件(带标签侧是已知缺文件、
             等用户重下补救的状态, 对侧重新下载这些文件是合法补救)。
          4. 激活: 非豁免事件中存在下载中参与者(谓词与 _check_download_conflicts 同款)才激活,
             按组对聚合(组对规范序 tuple(sorted((ka, kb), key=str)), 路径展示截前 3 处 +
             「等 N 处」)。
          5. 消除 + 处置(结构对齐 _check_download_conflicts 的消除段与处置段): active 组对集
             算完后先清过期去重记录(store.cross_group_conflict_warned, 组对不再激活即 discard,
             下次重现可再次触发); 处置循环顺序严格对齐同组检查 —— 警告 -> dry_run 止步(不暂停、
             不记去重) -> 登记去重 -> 暂停涉事下载方(D2: 只停两侧组中满足下载中谓词的成员,
             绝不传整组; 暂停幂等, 组对持续不重复警告/暂停)。

        成本: 只消费 store.groups / store.group_sizes / store.by_hash 三份内存数据, 零新增
        qB 请求、检测零触盘(只有目录级 realpath_lexical); 开关关闭首行即返回零开销;
        增量轮(rounds_applied > 0)且 dirty_groups 为空时事件集合与上轮一致, 直接返回
        (dirty 只读不复位, 消费单点仍是 _check_download_conflicts; 全量基线未建立时必跑)。
        """
        cfg = self._ctx.config.grouping
        if not cfg.cross_group_conflict_check:
            return
        store = self._ctx.store
        if store.rounds_applied > 0 and not store.dirty_groups:
            return  # 增量轮零变化: 事件集合与上轮一致(全量基线未建立时必跑)
        fa = file_access.get_file_access()
        by_hash = store.by_hash
        missing_tag = cfg.missing_tag
        # 1. 物理路径全量展开: 目录解析缓存(每 save_path 一次 syscall) + 物理键反向索引
        dir_resolved: Dict[str, str] = {}  # 归一 save_path(组 key 首元) -> 别名解析结果
        loc: Dict[str, list] = {}  # 物理路径键 -> [(组key, hash)]
        for key, members in store.groups.items():
            save_path = key[0]
            resolved = dir_resolved.get(save_path)
            if resolved is None:
                try:
                    resolved = fa.realpath_lexical(save_path)
                except (OSError, ValueError):
                    # 畸形路径不打断主循环: 词法回退方向是「少检出」, 保守
                    resolved = os.path.normcase(os.path.normpath(save_path))
                dir_resolved[save_path] = resolved
            for h in members:
                for rel in store.group_sizes.get(key, {}).get(h, {}):
                    loc.setdefault(_cross_physical_key(resolved, rel), []).append((key, h))
        # 2-3. 参与者按组全量预分类(下载中 / MISSING), 供逐事件的豁免与激活判定
        group_dl: Dict[Any, list] = {}  # 组 key -> 下载中成员 hash(谓词与 _check_download_conflicts 同款)
        group_missing: Dict[Any, bool] = {}  # 组 key -> 任一成员带 missing_tag
        for key, members in store.groups.items():
            dl = []
            has_missing = False
            for h in members:
                t = by_hash.get(h)
                if t is None:
                    continue  # 幽灵成员(组表有快照无): 不参与豁免与激活判定
                if missing_tag in t.tags_set:
                    has_missing = True
                e = t.state_enum
                if e.is_downloading and not e.is_stopped and not e.is_checking and t.amount_left > 0:
                    dl.append(h)
            group_dl[key] = dl
            group_missing[key] = has_missing
        # 4. 事件 -> 豁免 -> 激活: 按组对聚合(keys 已按 str 排序, (ka, kb) 即规范序, 去重键同形)
        pair_paths: Dict[tuple, list] = {}  # 组对(规范序) -> 共享物理路径列表
        for phys, hits in loc.items():
            keys = sorted({k for k, _h in hits}, key=str)
            if len(keys) < 2:
                continue  # 同组多成员共享路径是分组固有属性, 归同组检查管
            for i, ka in enumerate(keys):
                for kb in keys[i + 1:]:
                    if group_missing.get(ka) or group_missing.get(kb):
                        continue  # D3: 任一侧带 missing_tag -> 豁免该事件
                    if not group_dl.get(ka) and not group_dl.get(kb):
                        continue  # 无下载中参与者: 静态共存不激活
                    pair_paths.setdefault((ka, kb), []).append(phys)
        # active 组对集: (ka, kb, 共享路径, 涉事下载方) —— dl_hashes 只含两侧组中满足下载中谓词的
        # 成员 hash(group_dl, 谓词与 _check_download_conflicts 同款; 通常恰 1 个, 双侧都在下载则都停),
        # 绝不传整组(D2)
        active = [(ka, kb, paths, group_dl[ka] + group_dl[kb]) for (ka, kb), paths in pair_paths.items()]
        # 5. 交叉消除: 不在 active 组对集的过期去重记录清除(下次重现时再次警告+暂停),
        #    对齐 _check_download_conflicts 的消除段; 下载方被暂停后组对失活, 下轮即在此清除。
        #    成员判定对 pair_paths 的键(即 active 组对集): active 是四元组列表, 不能直接 in
        warned = store.cross_group_conflict_warned
        for pair in list(warned):
            if pair not in pair_paths:
                warned.discard(pair)
        # 6. 处置: 警告 + 暂停涉事下载方(顺序严格对齐 _check_download_conflicts 处置段:
        #    警告 -> dry-run 止步(不暂停、不记去重) -> 登记去重 -> 暂停)
        for ka, kb, paths, dl_hashes in active:  # paths 供消息, dl_hashes = 涉事下载方
            if (ka, kb) in warned:
                continue  # 冲突持续不重复警告/暂停(暂停幂等)
            dl_set = set(dl_hashes)
            dl_desc = ", ".join(f"{h[:8]}[{by_hash[h].tracker_name}]" for h in dl_hashes)
            done_desc = ", ".join(
                f"{h[:8]}[{by_hash[h].tracker_name}]"
                for h in store.groups.get(ka, []) + store.groups.get(kb, []) if h not in dl_set and h in by_hash
            )
            shown = paths[:3]
            more = len(paths) - len(shown)
            paths_desc = ", ".join(f"'{p}'" for p in shown) + (f" 等 {more} 处" if more > 0 else "")
            logger.warning(
                f"跨组文件交叉(2组) | 共享物理文件 {len(paths)} 处: {paths_desc}, "
                f"下载方: {dl_desc}, 完成侧: {done_desc or '无'}"
            )
            if dry_run:
                continue  # dry-run 只报告: 不暂停、不记去重
            warned.add((ka, kb))
            self._ctx.api.torrents_stop(torrent_hashes=dl_hashes)

    # ---------- 校验动作(checking)辅助: 组上下文 ----------

    def _group_members(self, hash: str) -> list:
        """种子所属组全部成员 hash 列表; 未归组/分组未启用 -> [自身] 单种子(无参考)"""
        return self._ctx.store.group_members(hash)

    def _group_by_hash(self) -> Dict[str, TorrentRecord]:
        """最近一轮种子快照的 hash -> 种子 映射(checking 动作用, 无需额外拉取) """
        return self._ctx.store.by_hash

    def _group_has_downloading(self, members: list[str]) -> bool:
        """组内是否存在活跃下载种子: 存在 -> 整组未完成, 不进行任何校验(包括跳检) """
        by_hash = self._ctx.store.by_hash
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

        !与缺文件扫描代表种判据(_valid_for_representative, is_complete or is_errored)
        是**两口径**, 不得混用(见各自 docstring)。
        """
        by_hash = self._ctx.store.by_hash
        return [
            by_hash[h] for h in members
            if h in by_hash and by_hash[h].state_enum.is_complete and not by_hash[h].state_enum.is_checking
        ]
