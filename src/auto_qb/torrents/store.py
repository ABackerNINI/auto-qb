"""TorrentStore: 主索引 + 增量同步态 + 分组索引 + 全局标签/分类缓存 + 写后同步"""
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union

import logging

from qbittorrentapi import NotFound404Error, TorrentDictionary

from .record import TorrentRecord
from .view import _VIEW_FIELD_SET

if TYPE_CHECKING:  # 仅用于类型标注, 避免与 qbapi 形成运行期循环导入
    from ..core.qbapi import QbApi

logger = logging.getLogger(__name__)

# qB 不支持 sync/maindata(旧版本 / 测试替身缺方法)时的降级信号; 其它异常(网络等)照常上抛
_SYNC_UNAVAILABLE = (AttributeError, NotFound404Error)


class TorrentStore:
    """种子信息数据层: 主索引 + 增量同步 + 惰性缓存 + 分组索引 + 全局标签/分类缓存

    增量同步态(qB /api/v2/sync/maindata rid 语义, 见 apply_sync):
      - rid: 上次响应 ID(0 = 下轮需全量); need_validate: 本轮是否全量(校验闸门);
      - using_fallback: 已降级全量(旧版 qB, 告警去重); validate_sample: 全量轮校验样本。
    分组相关结构(供 GroupingModule 直接读写, 保持增量语义):
      - groups:        key=(save_path, 排序文件路径元组) -> [hash...]
      - group_sizes:   key -> {hash: {规范化相对路径: 大小}}
      - member_to_key: hash -> 组 key(O(1) 定位)
      - state_snapshot: hash -> 上一轮 state_enum(上传转暂停检测)
      - download_conflict_warned: (组key, 冲突类型) 去重集合
      - transitional_missing_skips: 组key -> 连续「.!qB 过渡态」命中次数(仅内存, 见 __init__)
    本轮变化集(供主循环把 O(N) 扫描降为 O(变化数)):
      - delta_fields:  {hash: 变化字段名集合} 本轮发生变化的种子
      - state_changed: [(hash, fetch 时 state_enum)] state 字段变化的种子
      - dirty_groups:  需重算下载冲突的组 key(字段变化/成员增删/归组变化时登记)
    参考种子集合(仅内存): verified_references
    全局缓存: all_tags() / all_categories()(写操作后 invalidate)
    """
    def __init__(self, client: Any = None):
        self.client: Any = client
        # HR 判定桥(QbManager 注入 `HrRuntime` 门面): 新记录构建/变更时挂到 record 上,
        # 供 HR 四个消费点现算三态(计划 §9)。门面对象**稳定**(热重载不换), 故已挂过的
        # 记录不必重挂 —— 未变化的记录也不会被本类碰到。None ⇒ 全部走本地字段逻辑。
        self.hr_link: Any = None
        # 主索引: hash -> TorrentRecord(每轮原子替换引用, 记录对象跨 tick 保留)
        self.by_hash: Dict[str, TorrentRecord] = {}
        # 本程序自身发起删除、待下轮上报的 hash(remove_torrent 登记 / restore_torrent 撤销)
        self._pending_removed: Set[str] = set()
        # 增量同步态
        self.rid: int = 0
        self.need_validate: bool = True
        self.using_fallback: bool = False
        self.validate_sample: Optional[Any] = None
        # qB 全局状态(sync/maindata 响应的 server_state: 会话/累计流量/DHT 节点等)
        # 每轮合并为新 dict 后原子替换引用(增量轮部分键不丢旧值), 供 Web /api/stats 透出;
        # 降级全量路径置 None(前端空态)
        self.server_state: Optional[dict] = None
        # 本轮变化集
        self.delta_fields: Dict[str, FrozenSet[str]] = {}
        self.state_changed: List[Tuple[str, Any]] = []
        # 字段变化检测(计划 26-09-27-1438):
        # watch_fields:   监听字段并集(规则 watch_fields ∪ maintenance on_change 的 tags), 空 = 检测关闭
        # field_snapshots: 跨轮基线 {hash: {字段: 值}}, 持久化于 state.field_snapshots ——
        #                  update_field_snapshots **原地更新**(与 state 是同一对象, 原地改即落盘内容);
        #                  绑定点在 RuleEngineMixin._bind_field_snapshots
        # field_changed:  本轮净变化 [(hash, 变化字段集)](qB 增量 ∩ 监听字段后与基线对比确认;
        #                  首见/无基线/自写抑制的不进), 事件分派(_dispatch_events)按轮消费
        # external_tag_changes: tags 外部变化待重检登记(maintenance on_change 模式消费)
        # self_caused_fields: 本程序自身写后的待确认登记 {hash: {field: 期望值(归一化)}} ——
        # qB 增量报告该字段且**上报值与期望一致**时按自写处理(不触发/不打重检标记)并消费登记,
        # 防自喂环; 上报值不一致 = 写入后被外部覆盖, 按外部变化放行(计划 §04 细则 5 的保守口径
        # 仅用于"值无法区分"的场景, 值可比对时以值为准, 避免吞掉同字段的后续外部变化)
        self.watch_fields: FrozenSet[str] = frozenset()
        self.field_snapshots: Dict[str, Dict[str, Any]] = {}
        self.field_changed: List[Tuple[str, FrozenSet[str]]] = []
        self.external_tag_changes: Set[str] = set()
        self.self_caused_fields: Dict[str, Dict[str, Any]] = {}
        # 需重算下载冲突的组 key: 变化字段/成员增删/归组/自有停种打标时登记,
        # 由 GroupingModule._check_download_conflicts 取出并复位(跨轮累积, 不随 _apply 清空)
        self.dirty_groups: Set[Any] = set()
        # 轮次基线: >0 表示快照由主循环轮次驱动(变化集可用), 冲突检查走增量;
        # 直接驱动(_apply 未跑过, 如白盒测试)时为 0, 冲突检查退回全量扫描以保证正确
        self.rounds_applied: int = 0
        # 分组结构
        self.groups: Dict[Any, List[str]] = {}
        self.group_sizes: Dict[Any, Dict[str, Dict[str, int]]] = {}
        self.member_to_key: Dict[str, Any] = {}
        self.state_snapshot: Dict[str, Any] = {}
        self.download_conflict_warned: Set[Tuple[Any, str]] = set()
        # 跨组文件交叉检测的去重集合(plan 26-10-04-0107 S3): (组key_a, 组key_b) 规范序组对 ——
        # 软信号不落盘(纯内存, 重启即失忆, 方向是「更早恢复检测」, 保守); 热重载不清,
        # 理由见 reset_runtime 注释。
        self.cross_group_conflict_warned: Set[Tuple[Any, Any]] = set()
        # 缺文件扫描的过渡态容忍计数(仅内存, 重启归零): 组key -> 连续「原名缺失但 .!qB 孪生
        # 存在」命中次数(issue 26-09-21-0219 / plan 26-09-22-2038)。软信号不落盘 —— 丢失方向
        # 是"更早恢复判定"(保守, 沿用 verified_references 仅内存先例); 跨轮存活, 不随每轮
        # 变化集清空(与 _missing_scanned_keys 的轮清不同); 热重载 reset_runtime 随分组索引清空。
        self.transitional_missing_skips: Dict[Any, int] = {}
        # 内存参考种子集合(仅内存, 重启后重新积累): full-checking 校验通过的种子, 可作为同组参考
        self.verified_references: Set[str] = set()
        # 全局标签/分类缓存
        self._all_tags_cache: Optional[set] = None
        self._all_categories_cache: Optional[dict] = None
        # Web 分组视图需重建标记: 视图相关字段(_VIEW_FIELDS)或组成员变化时置真,
        # 主循环每 tick 消费(consume_view_changed), 无变化则不重建(惰性真正生效)
        self.view_changed: bool = True

    # ---------- 快照(增量同步) ----------

    def apply_sync(self, api: "QbApi") -> Tuple[List[str], List[str]]:
        """主循环入口: 从 qB 增量同步一轮并应用, 返回 (added, removed)

        /api/v2/sync/maindata 语义(见 src/webui/api/synccontroller.cpp):
          - full_update=true(首轮 / rid 失效) -> 响应含**全部种子全量字段**;
          - rid 一致 -> 只含**变化种子**的**变化字段**(未变化种子不出现),
            删除的种子列在 torrents_removed。
        端点不可用(旧版 qB / 测试替身缺方法)时降级为全量 torrents_info(一次性告警);
        其它异常 rid 归零后原样上抛(由调用方兜底, 不掩盖断连/鉴权问题)。
        """
        try:
            md = api.sync_maindata(rid=self.rid)
        except _SYNC_UNAVAILABLE as e:
            if not self.using_fallback:
                logger.warning(f"qB 不支持 sync/maindata, 降级为全量 torrents_info: {e}")
                self.using_fallback = True
            self.rid = 0
            self.need_validate = True
            tors = api.torrents_info()
            # 样本保持旧时序语义: 首个非 dict 的真实种子对象(测试注入的 plain dict 不作样本)
            self.validate_sample = next((t for t in tors if not isinstance(t, dict)), None)
            self.server_state = None  # 降级路径无 server_state 可言(下轮 sync 恢复后重取)
            return self.refresh(tors)
        except Exception:
            self.rid = 0  # 未知异常: 下轮强制全量
            raise
        self.using_fallback = False
        self.rid = int(md.get("rid", 0) or 0)
        full = bool(md.get("full_update"))
        self.need_validate = full
        # 全局状态捕获: qB 每轮 sync 响应都带 server_state(全量/增量皆然);
        # 响应缺失时保留上次已知值(不误清)。合并语义(FIX-04a): 增量轮(rid>0)qB 可能只带
        # 部分键(真机观察: 统计窗口仅累计流量正确、其余字段空值), 与上一轮旧值合并避免丢
        # 字段; 全量轮键集完整, 合并结果与整包替换一致(server_state 键集在 qB 侧稳定、
        # 无"键被移除"语义, 不引入陈旧键)。每轮生成新 dict 原子替换引用, Web 线程只读。
        if "server_state" in md:
            ss = md["server_state"]
            self.server_state = {**(self.server_state or {}), **dict(ss)} if isinstance(ss, Mapping) else ss
        patches = md.get("torrents") or {}
        # 校验样本: 仅全量轮提供。注意 qB sync 响应的 **hash 是 torrents 字典的键**, 值内不含
        # hash(与 torrents/info 的数组元素不同) -> 校验前需补齐, 否则必报缺 'hash' 字段
        if full and patches:
            h0, p0 = next(iter(patches.items()))
            self.validate_sample = {**p0, "hash": h0} if isinstance(p0, Mapping) else p0
        else:
            self.validate_sample = None
        return self._apply(patches, list(md.get("torrents_removed") or []), full=full)

    def refresh(self, tors: List[TorrentDictionary]) -> Tuple[List[str], List[str]]:
        """全量刷新入口(测试/降级路径): 以给定种子列表为全集, 返回 (added, removed)

        已存在记录对象原地更新(惰性缓存跨 tick 存活), 首轮全部视为新增。
        """
        patches: Dict[str, Any] = {}
        for t in tors:
            h = t.get("hash") if isinstance(t, Mapping) else getattr(t, "hash", None)
            if h:
                patches[h] = t
        return self._apply(patches, [], full=True)

    def reset_sync(self) -> None:
        """重置增量同步态(重连 / 热重载后旧 rid 失效, 下轮强制全量重建)"""
        self.rid = 0
        self.need_validate = True
        self.using_fallback = False
        self.validate_sample = None
        self.delta_fields = {}
        self.state_changed = []
        self.dirty_groups = set()

    # 影响下载冲突判定的字段(分组 n_dl/n_done 的判定依据)
    _CONFLICT_FIELDS = frozenset(("state", "amount_left", "tags"))

    def _apply(self, patches: Dict[str, Any], removed: List[str], *, full: bool) -> Tuple[List[str], List[str]]:
        """核心: 把 patches 应用到快照(原子替换 by_hash, Web 线程只读安全), 返回 (added, removed)

        full=True: patches 为全集, 未出现者视为删除;
        full=False(增量): patches 只含变化种子, 其余记录原样保留, 删除以 removed(torrents_removed)为准。
        本轮无任何变化且无待报删除时提前返回 —— 静止种子库的每 tick 成本趋近于 0。
        """
        pending = self._pending_removed
        self.rounds_applied += 1
        # 增量轮无变化且无待报删除 -> 零成本早退; 全量轮即使 patches 为空也必须走完(需检测删除)
        if not full and not patches and not removed and not pending:
            self.delta_fields = {}
            self.state_changed = []
            self.field_changed = []
            return [], []
        prev = self.by_hash
        by_hash = {} if full else dict(prev)  # 全量重建 / 增量: C 级浅拷贝, 未变化记录原样保留
        added: List[str] = []
        changes = list(removed)
        view_changed = False
        delta_fields: Dict[str, FrozenSet[str]] = {}
        state_changed: List[Tuple[str, Any]] = []
        field_changed: List[Tuple[str, FrozenSet[str]]] = []
        member_to_key = self.member_to_key
        hr_link = self.hr_link
        for h, src in patches.items():
            rec = prev.get(h)
            if rec is None:
                rec = TorrentRecord.from_torrent(src, hash=h)
                added.append(h)
                # 新增种子也过登记点: 有持久化基线(重启场景)时与基线对比 -> 停机期的外部变化
                # 在重启后首轮补捕(计划 §04 细则 4); 无基线(真首见/升级首启)只落基线不触发。
                # changed 传监听字段全集 ∪ tags: 与基线的差集才是真实变化, 不是"全变"。
                net = self._register_field_changes(h, rec, self.watch_fields | {"tags"})
                if net:
                    field_changed.append((h, net))
            else:
                changed = rec.apply_delta(src)
                if changed:
                    delta_fields[h] = changed
                    if not _VIEW_FIELD_SET.isdisjoint(changed):
                        view_changed = True
                    if "state" in changed:
                        state_changed.append((h, rec.state_enum))
                    if not self._CONFLICT_FIELDS.isdisjoint(changed):
                        key = member_to_key.get(h)
                        if key is not None:
                            self.dirty_groups.add(key)
                    net = self._register_field_changes(h, rec, changed)
                    if net:
                        field_changed.append((h, net))
            if hr_link is not None and rec.hr_link is not hr_link:
                rec.hr_link = hr_link  # 只在需要时赋值: 反复过磅的静止种子不做无谓写
            by_hash[h] = rec
        if full:
            # 全量: by_hash 由本轮响应重建, 旧快照中未出现者即已删除
            changes.extend(h for h in prev if h not in patches)
        else:
            for h in changes:
                by_hash.pop(h, None)
        # 本程序自身发起的删除(remove_torrent): qB 增量响应不一定会再列出, 由待报集合补齐
        changes.extend(h for h in pending if h not in by_hash)
        pending.clear()
        if changes:
            changes = list(dict.fromkeys(changes))
        # 被删除成员的原组需重算冲突(member_to_key 在下游取消归组前仍可定位)
        for h in changes:
            key = member_to_key.get(h)
            if key is not None:
                self.dirty_groups.add(key)
            # 已删种子的字段变化残留登记一并清掉(重加的同 hash 由后续轮重新检测)
            self.external_tag_changes.discard(h)
            self.self_caused_fields.pop(h, None)
        self.by_hash = by_hash
        self.delta_fields = delta_fields
        self.state_changed = state_changed
        self.field_changed = field_changed
        if view_changed or added or changes:
            self.view_changed = True
        return added, changes

    def consume_view_changed(self) -> bool:
        """读取并复位"分组视图需重建"标记(主循环每 tick 消费一次)"""
        changed = self.view_changed
        self.view_changed = False
        return changed

    def get(self, hash: str) -> Optional[TorrentRecord]:
        return self.by_hash.get(hash)

    def __contains__(self, hash: str) -> bool:
        return hash in self.by_hash

    def __len__(self) -> int:
        return len(self.by_hash)

    def all(self) -> List[TorrentRecord]:
        return list(self.by_hash.values())

    def hashes(self) -> List[str]:
        return list(self.by_hash)

    def update_state_snapshot(self) -> None:
        """本轮结束前更新状态快照(hash -> state_enum)

        直接取本轮 by_hash 的状态(record.state_enum 有缓存, 与 qB 版本无关): 自有动作
        经 QbApi 同步过的状态同样计入, 故下轮不会被误判为外部状态变化。
        """
        self.state_snapshot = {h: r.state_enum for h, r in self.by_hash.items()}

    def update_field_snapshots(self) -> None:
        """轮末刷新字段变化基线(与 update_state_snapshot 并列, 仅主循环线程调用)

        只存监听字段的当前值: 监听集合为空时清空基线(无规则监听 -> 零持久化开销);
        已删种子的基线一并清掉。!原地更新 —— field_snapshots 与 state["field_snapshots"]
        是同一对象(见 _bind_field_snapshots), 原地改即等于改落盘内容; 不得整体换引用。
        """
        watch = self.watch_fields
        if not watch:
            if self.field_snapshots:
                self.field_snapshots.clear()
            return
        snap = self.field_snapshots
        for h in [h for h in snap if h not in self.by_hash]:
            del snap[h]
        for h, rec in self.by_hash.items():
            snap[h] = {f: self._watch_value(rec, f) for f in watch}

    # ---------- 字段变化检测(计划 26-09-27-1438) ----------

    @staticmethod
    def _watch_value(rec: Any, field: str) -> Any:
        """监听字段的归一化当前值(基线与实时对比共用同一口径)

        tags 排序后比较(qB API 返回顺序不保证, 顺序噪声不触发); category 原样(空即 "")。
        """
        if field == "tags":
            return sorted(rec.tags_set)
        return rec.category or ""

    def set_watch_fields(self, fields) -> None:
        """注入监听字段并集(由 load_rules 从规则 watch_fields ∪ maintenance on_change 推导)

        空 = 检测关闭: 不建基线、零对比开销(黄金法则: 无消费不付费)。
        """
        self.watch_fields = frozenset(f for f in fields if f)

    def _register_field_changes(self, h: str, rec: Any, changed: FrozenSet[str]) -> FrozenSet[str]:
        """qB 增量报告字段变化后的登记点(新增种子也走这里: 有持久化基线时补捕停机期变化)

        返回与持久化基线对比后的**净变化**监听字段集(空 = 无事件候选); 入队 field_changed
        由 _apply 统一完成。
        1. 自写确认消费: 报告字段若在本程序自身写后登记过(self_caused_fields)且**上报值与
           登记的期望值一致** -> 按自写处理(不打外部重检标记、不进事件候选)并消费登记;
           上报值不一致 = 写入后被外部覆盖 -> 按外部变化放行。登记一律在报告时消费, 不残留。
           (计划 §04 细则 5 的"同轮叠加保守按自写"仅适用于值无法区分的场景; 值可比对时以
           值为准, 避免吞掉同字段的后续外部变化。)
        2. tags 外部变化 -> external_tag_changes 登记(maintenance on_change 重检依据)。
        3. 监听字段 ∩ 变化 -> 与持久化基线对比出**净变化**
          (全量 refresh 降级路径同此判据: 与快照对比, 禁止按"全变"处理 —— 计划 §05)。
        """
        caused = self.self_caused_fields.get(h)
        confirmed: Set[str] = set()
        if caused:
            for f in changed:
                if f not in caused:
                    continue
                if self._watch_value(rec, f) == caused[f]:
                    confirmed.add(f)  # 上报值与自写期望一致: 按自写处理
                del caused[f]  # 登记已被报告消费(无论结论)
            if not caused:
                del self.self_caused_fields[h]
        if "tags" in changed and "tags" not in confirmed:
            # 仅当基线已存在才登记(真首见走添加路径强制维护, 无需标记; 重启全量轮基线在,
            # 停机期/未知状态统一按待重检处理 -> 首轮全量收敛)
            if self.field_snapshots.get(h) is not None:
                self.external_tag_changes.add(h)
        watch = self.watch_fields & changed
        if not watch:
            return frozenset()
        snap = self.field_snapshots.get(h)
        if snap is None:
            return frozenset()  # 首见/无基线: 只待 update_field_snapshots 落基线, 不触发(对齐 state 先例)
        net = {
            f
            for f in watch if f in snap and self._watch_value(rec, f) != snap[f]  # f 不在 snap = 新增监听字段, 无基线不触发
        }
        net -= confirmed
        return frozenset(net)

    # ---------- 分组查询接口 ----------

    def group_members(self, hash: str) -> List[str]:
        """种子所属组全部成员 hash; 未归组 -> [自身] 单种子"""
        key = self.member_to_key.get(hash)
        if key is None:
            return [hash]
        return list(self.groups.get(key, [hash]))

    def group_key(self, hash: str) -> Optional[Any]:
        """种子所属组 key; 未归组 -> None"""
        return self.member_to_key.get(hash)

    # ---------- 全局标签/分类缓存 ----------

    def all_tags(self) -> set:
        """客户端全部标签定义(惰性缓存; 异常向上传播, 调用方处理)"""
        if self._all_tags_cache is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._all_tags_cache = set(self.client.torrents_tags() or [])
        return set(self._all_tags_cache)

    def all_categories(self) -> dict:
        """客户端全部分类定义(惰性缓存; 异常向上传播, 调用方处理)"""
        if self._all_categories_cache is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._all_categories_cache = dict(self.client.torrents_categories() or {})
        return self._all_categories_cache

    def invalidate_tags(self) -> None:
        """标签写操作后调用, 使全局标签缓存失效"""
        self._all_tags_cache = None

    def invalidate_categories(self) -> None:
        """分类写操作后调用, 使全局分类缓存失效"""
        self._all_categories_cache = None

    def tag_usage(self) -> Dict[str, int]:
        """从快照聚合标签使用情况 {tag: 使用该标签的种子数}

        替代 _handle_delete_tags_if_has_no_torrents 的 torrents.info(tag=) 逐个查询。
        """
        usage: Dict[str, int] = {}
        for rec in self.by_hash.values():
            for tag in rec.tags_set:
                usage[tag] = usage.get(tag, 0) + 1
        return usage

    # ---------- 写操作同步(供 QbApi Facade调用) ----------

    def reset_runtime(self) -> None:
        """热重载配置后的运行态重置: 清分组索引/缓存/状态快照/校验记录;
        种子记录保留(tracker_conf 置空, 由下一轮全量 refresh 重匹配)"""
        self.groups.clear()
        self.group_sizes.clear()
        self.member_to_key.clear()
        self.state_snapshot.clear()
        self.verified_references.clear()
        self.transitional_missing_skips.clear()  # 组 key 随分组索引重建, 过渡态计数一并清零
        # download_conflict_warned / cross_group_conflict_warned 有意不清(决策钉死, 防"顺手补 clear"):
        # 两个去重集合的组 key 均为纯函数派生(grouping_mod.group_key_of 单一事实源), 热重载重建
        # 分组索引后同数据派生同 key, 旧条目语义仍成立; 过期条目由每轮扫描的消除循环兜底丢弃。
        self.invalidate_tags()
        self.invalidate_categories()
        self.view_changed = True  # 分组索引已清空, 视图必须重建
        # 热重载全量重建: tracker 配置可能已变 -> 全部种子登记 tags 待重检
        # (maintenance on_change 模式据此实现"首轮全量收敛", 两个模式行为一致 —— 计划 §07)
        self.external_tag_changes |= set(self.by_hash)
        for rec in self.by_hash.values():
            rec.tracker_conf = None

    def update_torrent_fields(
        self,
        torrent_hashes: Union[str, List[str]],
        *,
        tags_add: Optional[List[str]] = None,
        tags_remove: Optional[List[str]] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        up_limit: Optional[int] = None,
        dl_limit: Optional[int] = None,
        save_path: Optional[str] = None,
    ) -> None:
        """写操作后同步快照字段(单 hash 或 hash 列表)

        由 QbApi Facade调用: 调用客户端 API 后立即更新内存快照, 保证同 tick 内
        后续读取(如 tag_usage / 分类判断 / 限速幂等)读到最新值; 下轮 refresh 校准。
        tags_add/tags_remove 合并式更新并失效 _tags_set, state 变化失效 _state_enum。
        tags/category 的**实际变化**同步登记 self_caused_fields(计划 26-09-27-1438):
        下轮 qB 增量报告同字段变化时保守按自写处理 —— 事件不自触发、maintenance on_change
        不打重检标记(防自喂环, 单点收口在本方法)。
        """
        hashes = [torrent_hashes] if isinstance(torrent_hashes, str) else list(torrent_hashes or [])
        tags_changed = tags_add is not None or tags_remove is not None
        state_changed = state is not None
        # state/save_path/tags/category 均为视图展示字段(组级共同标签/分类列): 写操作后视图需重建;
        # 限速(up_limit/dl_limit)不参与视图, 不置脏
        if state_changed or save_path is not None or tags_changed or category is not None:
            self.view_changed = True
        for h in hashes:
            torrent = self.by_hash.get(h)
            if torrent is None:
                continue
            if state_changed or tags_changed:
                # 自有停种/打标会改变组内冲突判定, 登记组级脏标记(下轮 qB 增量不会重报同样值)
                key = self.member_to_key.get(h)
                if key is not None:
                    self.dirty_groups.add(key)
            if tags_add is not None:
                current = set(torrent.tags_set)
                merged = current | set(tags_add)
                if merged != current:  # 幂等写不加标签: 不登记自写(qB 也不会报告变化, 登记必成残留)
                    torrent.tags = ",".join(sorted(merged))
                    torrent._tags_set = None
                    self.self_caused_fields.setdefault(h, {})["tags"] = sorted(torrent.tags_set)
            if tags_remove is not None:
                current = set(torrent.tags_set)
                remain = current - set(tags_remove)
                if remain != current:
                    torrent.tags = ",".join(sorted(remain))
                    torrent._tags_set = None
                    self.self_caused_fields.setdefault(h, {})["tags"] = sorted(torrent.tags_set)
            if category is not None:
                if torrent.category != category:  # 同值写不登记(同上)
                    torrent.category = category
                    self.self_caused_fields.setdefault(h, {})["category"] = category
            if state is not None:
                torrent.state = state
            if up_limit is not None:
                torrent.up_limit = up_limit
            if dl_limit is not None:
                torrent.dl_limit = dl_limit
            if save_path is not None:
                torrent.save_path = save_path
            if state_changed:
                torrent._state_enum = None

    def apply_tag_removal(self, tags: List[str]) -> None:
        """torrents_delete_tags 后从所有记录移除已删除标签(定义删除 = 所有种子移除)"""
        tags = set(tags or [])
        if not tags:
            return
        for torrent in self.by_hash.values():
            cur = torrent.tags_set
            removed = cur & tags
            if removed:
                torrent.tags = ",".join(sorted(cur - removed))
                torrent._tags_set = None
                self.view_changed = True  # 组级共同标签列随标签定义删除而变化
                key = self.member_to_key.get(torrent.hash)
                if key is not None:
                    self.dirty_groups.add(key)

    def remove_torrent(self, hash: str) -> None:
        """种子删除后立即从快照移除, 并登记待报 removed(供下轮 added/removed 语义)"""
        if self.by_hash.pop(hash, None) is not None:
            self._pending_removed.add(hash)

    def restore_torrent(self, record: TorrentRecord) -> None:
        """跳检重加后恢复删除前记录(tracker_conf/惰性缓存保留); 幂等

        remove_torrent 会登记待报 removed; 此处撤销登记 —— 否则重加的同 hash 种子下轮
        被误判为"已删除"(多余的组内缺文件扫描与 on_torrent_deleted 事件)。
        """
        self.by_hash[record.hash] = record
        self._pending_removed.discard(record.hash)
