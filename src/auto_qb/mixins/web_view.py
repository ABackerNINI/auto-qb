"""WebviewMixin: WEB UI 视图组装(分组视图/单种子视图/追剧视图/搜索索引/状态回传)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一): 视图组装只读 store 快照与宿主状态,
与核心循环解耦; 组合进 QbManager 后经 self 访问宿主属性。

依赖的宿主属性(由 QbManager.__init__ 初始化):
- self.store                种子数据层 TorrentStore(分组索引/by_hash/视图脏标记)
- self.client               qB 原始客户端(搜索索引拉取文件列表用)
- self.web_commands         WEB 控制命令队列(搜索 building 时投递构建命令)
- self._group_view / self._singles_view / self._shows_view / self._flat_view / self._group_view_ver
- self._group_view_dirty / self._shows_pending / self._web_last_seen
- self._search_index / self._search_index_dirty
"""
import logging
import time
from typing import Dict, List, Optional

from ..torrents import TorrentRecord, view_field_value

logger = logging.getLogger(__name__)

SEARCH_INDEX_BUILD_BUDGET = 500  # 搜索索引单次构建最多拉取的文件列表数(限流, 避免首轮 N 次 qB API 阻塞主循环)

# 集节点聚合状态优先级: 错误 > 下载 > 校验 > 暂停 > 做种 > 其它(前端按 state 着色)
_SHOW_STATE_RANK = {"error": 0, "downloading": 1, "checking": 2, "paused": 3, "seeding": 4, "other": 5}


def _ep_sort_key(nkey: tuple):
    """集节点排序键: 整季包(覆盖全季)最先, 其余按集号起点/终点; 日期桶内按日期字符串"""
    if nkey[0] == "pack":
        return (0, 0, "")
    if nkey[0] == "ep":
        return (0, nkey[1], "")
    if nkey[0] == "range":
        return (0, nkey[1], "")
    return (1, 0, nkey[1])  # date


class WebviewMixin:
    @staticmethod
    def _state_kind(rec: TorrentRecord) -> str:
        """状态语义分类(前端着色): 错误红/校验蓝/下载蓝/做种绿/暂停灰

        注意 is_stopped 须先于 is_downloading/is_uploading 判定: 暂停的种子
        (stoppedDL/stoppedUP)同时命中下载/做种类别, 暂停态优先展示。
        """
        e = rec.state_enum
        if e.is_errored:
            return "error"
        if e.is_checking:
            return "checking"
        if e.is_stopped:
            return "paused"
        if e.is_downloading:
            return "downloading"
        if e.is_uploading:
            return "seeding"
        return "other"

    @staticmethod
    def _hr_view_fields(rec: TorrentRecord) -> dict:
        """该成员的 HR 展示字段(标签文本 + 要求/达成布尔), 供前端渲染 H&R 栏与对照列

        - hr_tag / hr_tag_done: 已触发未达标 / 已达标时应有的标签(供前端按文本着色)
        - hr_triggered / hr_satisfied: 是否触发 HR / 是否已达成要求
        - hr_req_time: 要求做种时长(秒) = required_seeding_time + extra_seeding_time
        - hr_req_ratio: 要求分享率(0 = 不要求)

        判定委托 TorrentRecord.check_hr_condition/check_hr_satisfied, 标签文本经
        utils.replace_vars 解析 ${required_seeding_time}, 与维护流程(打 HR 标签)完全同源 ——
        前端只做展示比较, 不得在 JS 里重算模板或阈值(否则自定义标签格式/阈值会立即失效)。
        未配置 HR 站点返回全空值(前端据此整列显示"—"), 不做 None 防御(早暴露配置匹配错误)。
        """
        from .. import utils as _utils

        conf = rec.tracker_conf
        hr = conf.hr if conf is not None else None
        if hr is None:
            return {
                "hr_tag": "",
                "hr_tag_done": "",
                "hr_triggered": False,
                "hr_satisfied": False,
                "hr_req_time": 0,
                "hr_req_ratio": 0.0,
            }
        triggered = rec.check_hr_condition()
        satisfied = triggered and rec.check_hr_satisfied()
        fields = {
            "hr_tag": "",
            "hr_tag_done": "",
            "hr_triggered": triggered,
            "hr_satisfied": satisfied,
            "hr_req_time": hr.required_seeding_time + hr.extra_seeding_time,
            "hr_req_ratio": hr.required_share_ratio,
        }
        if triggered:
            if satisfied:
                fields["hr_tag_done"] = _utils.replace_vars(hr.add_tag_for_satisfied, conf)
            else:
                fields["hr_tag"] = _utils.replace_vars(hr.add_tag, conf)
        return fields

    def _member_view(self, r) -> dict:
        """单成员展示视图(分组视图 members 与 singles 未归组种子共用同一字段构建)"""
        return {
            "hash": r.hash,
            "name": r.name,
            "site": r.tracker_name,
            "state": r.state,
            "kind": self._state_kind(r),
            "dlspeed": r.dlspeed,
            "upspeed": r.upspeed,
            "uploaded": r.uploaded,
            "size": r.size,
            # 组级"共同标签/分类"与保存路径筛选器的数据来源(交集/共同值由前端计算,
            # 后端只透出原始值, 避免每次重建做 O(成员数) 以上的集合运算)
            "save_path": r.save_path,
            "tags": sorted(r.tags_set),
            "category": r.category,
            "progress": round(r.progress, 4),
            # 取整到分钟(与 torrents.view_field_value 的重建判定同一步长): 该字段每秒递增,
            # 不取整会让做种中的种子每轮置脏, 惰性重建失效; 前端展示精度本就是分钟
            "seeding_time": view_field_value("seeding_time", r.seeding_time),
            "ratio": round(r.ratio, 3),
            # 添加时间(unix 秒): 组级默认排序取组内最大值(见下方组级 added_on)
            "added_on": r.added_on,
            # HR 展示字段(标签语义色 + 要求/达成布尔): 判定与打标签流程同源, 见 _hr_view_fields
            **self._hr_view_fields(r),
            # 连接数快照(TorrentRecord 已有): 成员/未归组种子直接透出, 供前端种子页与成员列展示
            "num_seeds": r.num_seeds,
            "num_leechs": r.num_leechs,
            "num_complete": r.num_complete,
            "num_incomplete": r.num_incomplete,
        }

    def _build_group_view(self) -> List[dict]:
        """从 store 分组索引组装分组视图快照(主循环每 tick 重建, Web 线程只读引用)"""
        from .. import utils as _utils

        view = []
        for key, members in self.store.groups.items():
            recs = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
            if not recs:
                continue
            members_view = [self._member_view(r) for r in recs]
            view.append(
                {
                    "key": _utils.encode_group_key(key),
                    "name": recs[0].name,
                    "count": len(recs),
                    "dlspeed": sum(m["dlspeed"] for m in members_view),
                    "upspeed": sum(m["upspeed"] for m in members_view),
                    "uploaded": sum(m["uploaded"] for m in members_view),
                    # size = **单种子**大小(同组文件列表相同, 取代表成员); total_size = 全组求和。
                    # 两者不等即说明组内大小不一致(前端据此提示风险), 而非显示重复信息
                    "size": members_view[0]["size"],
                    "total_size": sum(m["size"] for m in members_view),
                    # 组级默认排序键 = 组内**最近添加**时间(前端 sortKey=added_on 降序);
                    # 用 max 而非 min: "刚补进来的那个辅种"才是用户最关心的新条目
                    "added_on": max(m["added_on"] for m in members_view),
                    # HR 栏: 分子 = 已触发但未达标(需关注), 分母 = 已触发 HR 的成员数;
                    # 在**后端**算好计数, 前端只负责显示(与 memory-bank/pitfalls.md 的"派生值后端算"约定一致)
                    "hr_triggered": sum(1 for m in members_view if m["hr_triggered"]),
                    "hr_pending": sum(1 for m in members_view if m["hr_triggered"] and not m["hr_satisfied"]),
                    "members": members_view,
                }
            )
        return view

    def _seed_view(self, r) -> dict:
        """种子中心视图条目(SEED_ITEM): 成员视图全字段 + 扩展 qB 数据字段

        WEB UI 替代 qB 界面的"种子页"数据源: 平铺列表/详情抽屉展示用。在 _member_view
        基础上补齐 TorrentRecord 的全部展示字段(字段集 = torrents/view._VIEW_FIELDS
        的平铺扩展段); eta/time_active/last_activity 按分钟量化(与重建判定同一步长)。
        """
        return {
            **self._member_view(r),
            "downloaded": r.downloaded,
            "total_size": r.total_size,
            "eta": view_field_value("eta", r.eta),
            "max_ratio": r.max_ratio,
            "max_seeding_time": r.max_seeding_time,
            "max_inactive_seeding_time": r.max_inactive_seeding_time,
            "completion_on": r.completion_on,
            "time_active": view_field_value("time_active", r.time_active),
            "availability": round(r.availability, 2),
            "num_seeds": r.num_seeds,
            "num_leechs": r.num_leechs,
            "num_complete": r.num_complete,
            "num_incomplete": r.num_incomplete,
            "tracker": r.tracker,
            "trackers_count": r.trackers_count,
            "dl_limit": r.dl_limit,
            "up_limit": r.up_limit,
            "seq_dl": r.seq_dl,
            "f_l_piece_prio": r.f_l_piece_prio,
            "auto_tmm": r.auto_tmm,
            "force_start": r.force_start,
            "super_seeding": r.super_seeding,
            "priority": r.priority,
            "magnet_uri": r.magnet_uri,
            "infohash_v1": r.infohash_v1,
            "infohash_v2": r.infohash_v2,
            "private": r.private,
            "comment": r.comment,
            "created_by": r.created_by,
            "creation_date": r.creation_date,
            "has_metadata": r.has_metadata,
            "piece_size": r.piece_size,
            "pieces_have": r.pieces_have,
            "pieces_num": r.pieces_num,
            "last_activity": view_field_value("last_activity", r.last_activity),
            "total_wasted": r.total_wasted,
            "connections_count": r.connections_count,
            "connections_limit": r.connections_limit,
            "reannounce": r.reannounce,
            "reannounce_in": r.reannounce_in,
            "has_tracker_error": r.has_tracker_error,
            "has_tracker_warning": r.has_tracker_warning,
            "has_other_announce_error": r.has_other_announce_error,
            "amount_left": r.amount_left,
            "content_path": r.content_path,
            "download_path": r.download_path,
            "root_path": r.root_path,
            "popularity": r.popularity,
            "seen_complete": r.seen_complete,
            "downloaded_session": r.downloaded_session,
            "uploaded_session": r.uploaded_session,
        }

    def _build_flat_view(self) -> List[dict]:
        """种子平铺视图(全部种子一列表): 与分组视图同一脏窗口同快照重建。

        WEB UI 替代 qB 界面的"种子页"数据源: 不依赖辅种分组是否启用, store.by_hash
        全量进视图(前端在平铺列表上自行筛选/排序/多选; 字段集 = SEED_ITEM 契约)。
        """
        return [self._seed_view(r) for r in self.store.by_hash.values()]

    def _build_singles_view(self) -> List[dict]:
        """未归组种子的单种子视图数据(分组未启用/文件列表不可读的种子不在任何组里,
        只能从这里进入单种子视图; 搜索兜底路径不含全量)。与分组视图在同一脏窗口重建,
        store.view_changed 对任意种子的视图字段变化置真, 故不会读到陈旧状态。"""
        grouped: set = set()
        for members in self.store.groups.values():
            grouped.update(members)
        return [self._member_view(r) for h, r in self.store.by_hash.items() if h not in grouped]

    # ---------- 追剧视图(shows): 全量种子按 剧→季→集 聚合 ----------

    @staticmethod
    def _missing_in_range(covered: set) -> List[int]:
        """已覆盖集号集合内的缺口(缺集提示): [E1,E2,E4] -> [3]"""
        if not covered:
            return []
        lo, hi = min(covered), max(covered)
        return sorted(set(range(lo, hi + 1)) - covered)

    def _agg_show_node(self, node: dict, rec) -> None:
        """把一个成员累加进集节点(聚合规则):

        - 速度/上传量/HR 计数求和; 站点去重(保持出现序); added_on 取最新
        - 代表大小 = 最完整版本(进度最高, 并列取更大): 用户关心"这一集拿到的版本多大"
        - 集进度 = 最差版本(全部版本完成才算这一集完成)
        - 状态逐个记录, 出口处按优先级归并为节点状态
        """
        kind = self._state_kind(rec)
        hr = self._hr_view_fields(rec)
        node["members"].append(rec.hash)
        node["kinds"].append(kind)
        node["dlspeed"] += rec.dlspeed
        node["upspeed"] += rec.upspeed
        node["uploaded"] += rec.uploaded
        if rec.progress > node["size_progress"] or (rec.progress == node["size_progress"] and rec.size > node["size"]):
            node["size_progress"] = rec.progress
            node["size"] = rec.size
        node["progress"] = min(node["progress"], rec.progress)
        if hr["hr_triggered"]:
            node["hr_triggered"] += 1
            if not hr["hr_satisfied"]:
                node["hr_pending"] += 1
        if rec.tracker_name and rec.tracker_name not in node["sites"]:
            node["sites"].append(rec.tracker_name)
        node["added_on"] = max(node["added_on"], rec.added_on)

    def _build_shows_view(self) -> dict:
        """追剧视图: 全量种子按 (剧键, 季, 集键) 三层聚合(与分组视图同一脏窗口同快照重建)

        数据源是 store.by_hash **全量**(不依赖辅种分组是否启用): 追剧语义是
        "这部剧我有哪些集", 未归组种子同样进视图。同一辅种组内成员文件列表相同,
        解析结果必然同剧同季同集 —— 多站点辅种天然归并进同一集行, 无需显式关联;
        不同编码的独立种子也落在同一集行(集 = 展示单位, 成员 = 版本)。

        聚合层在后端算好(pitfalls 约定: 派生值后端算), members 只放 hash ——
        明细字段由前端从 groups/singles 的成员索引取(groups ∪ singles = 全量,
        避免响应体重复成员数据)。

        文件列表兑底: 季包/名称无标记的种子从搜索索引缓存解析集数
        (tvshows.refine_with_files); 索引尚未覆盖的种子暂按名称解析结果展示,
        标记 _shows_pending 并投递构建命令 —— 索引推进后由 _build_search_index
        置脏触发重建归位(种子名无标记不会自动置脏, 这是唯一需要动重建时序的点)。

        返回 {"list": [剧…], "unrecognized": [hash…]}:
          剧: {key, name, latest, member_count, episode_count, seasons: [季…]}
          季: {season(编号或 None=日播/日期型), gaps(缺集列表), episodes: [集…]}
          集: {key: ["ep",n]|["range",a,b]|["pack"]|["date",iso], count, state,
               速度/上传/size(代表版本)/progress(最差版本)/HR 计数/sites/members(hash)/added_on}
        """
        from .. import tvshows

        index = self._search_index or {}
        shows: Dict[str, dict] = {}
        unrecognized: List[str] = []
        pending: List[str] = []
        for h, rec in self.store.by_hash.items():
            parsed = tvshows.parse_release(rec.name)
            files = (index.get(h) or {}).get("files")
            if parsed.kind in (tvshows.KIND_SEASON_PACK, tvshows.KIND_UNKNOWN) and parsed.key:
                if files:
                    parsed = tvshows.refine_with_files(parsed, files)
                else:
                    pending.append(h)  # 可被文件兑底但索引未覆盖: 待索引建成后归位
            if parsed.kind == tvshows.KIND_UNKNOWN or not parsed.key:
                unrecognized.append(h)
                continue
            show = shows.get(parsed.key)
            if show is None:
                show = shows[parsed.key] = {"titles": {}, "seasons": {}}
            if parsed.title:
                titles = show["titles"]
                titles[parsed.title] = titles.get(parsed.title, 0) + 1
            # 日期型集键不挂编号季(综艺/日播无季概念): 归 None 季桶, 前端渲染为"日播/特别篇"
            skey = parsed.season if parsed.kind != tvshows.KIND_DATE else None
            nodes = show["seasons"].setdefault(skey, {})
            node = nodes.get(parsed.episode_key)
            if node is None:
                node = nodes[parsed.episode_key] = {
                    "members": [],
                    "kinds": [],
                    "sites": [],
                    "dlspeed": 0,
                    "upspeed": 0,
                    "uploaded": 0,
                    "size": 0,
                    "size_progress": -1.0,
                    "progress": 1.0,
                    "hr_triggered": 0,
                    "hr_pending": 0,
                    "added_on": 0,
                }
            self._agg_show_node(node, rec)

        out = []
        for key, show in shows.items():
            titles = show["titles"]
            # 展示名 = 出现频次最高的原始剧名(并列取更长/字典序, 保证确定性)
            name = max(titles.items(), key=lambda kv: (kv[1], len(kv[0]), kv[0]))[0] if titles else key
            seasons_out = []
            latest = 0
            member_total = 0
            ep_total = 0
            # 编号季升序在前, None 季桶(日期型)殿后
            for skey in sorted(show["seasons"], key=lambda s: (s is None, s if s is not None else 0)):
                nodes = show["seasons"][skey]
                eps_out = []
                covered = set()
                has_pack = False
                for nkey in sorted(nodes, key=_ep_sort_key):
                    node = nodes[nkey]
                    eps_out.append(
                        {
                            "key": list(nkey),
                            "count": len(node["members"]),
                            "state": min(node["kinds"], key=lambda k: _SHOW_STATE_RANK.get(k, 9)),
                            "dlspeed": node["dlspeed"],
                            "upspeed": node["upspeed"],
                            "uploaded": node["uploaded"],
                            "size": node["size"],
                            "progress": round(node["progress"], 4),
                            "hr_triggered": node["hr_triggered"],
                            "hr_pending": node["hr_pending"],
                            "sites": sorted(node["sites"]),
                            "members": sorted(node["members"]),
                            "added_on": node["added_on"],
                        }
                    )
                    member_total += len(node["members"])
                    ep_total += 1
                    latest = max(latest, node["added_on"])
                    if nkey[0] == "ep":
                        covered.add(nkey[1])
                    elif nkey[0] == "range":
                        covered.update(range(nkey[1], nkey[2] + 1))
                    elif nkey[0] == "pack":
                        has_pack = True  # 整包覆盖全季: 不提示缺集
                seasons_out.append(
                    {
                        "season": skey,
                        "gaps": [] if has_pack else self._missing_in_range(covered),
                        "episodes": eps_out,
                    }
                )
            out.append(
                {
                    "key": key,
                    "name": name,
                    "latest": latest,
                    "member_count": member_total,
                    "episode_count": ep_total,
                    "seasons": seasons_out,
                }
            )
        # 默认排序: 剧内最近有动静的剧在前(与分组视图"新补的辅种最先看到"同哲学)
        out.sort(key=lambda s: (-s["latest"], s["name"]))

        # 文件兑底接线: 待解析种子且索引未覆盖 -> 标记 pending 并投递构建命令(幂等,
        # 拉取限流由索引侧 SEARCH_INDEX_BUILD_BUDGET 控制; 索引已覆盖但无文件的不再投递)
        pending = [h for h in pending if h not in index]
        if pending:
            self._shows_pending = True
            if self._search_index_dirty or self._search_index is None:
                self.web_commands.put(("build_search_index", {}))
        else:
            self._shows_pending = False
        return {"list": out, "unrecognized": sorted(unrecognized)}

    def ensure_group_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则直接返回当前引用。
        与主循环惰性组装配合: 主循环只在 Web 活跃且视图有变化时重建, 这里兜底保证每次请求都拿到最新。
        singles(未归组种子)、shows(追剧视图)与 flat(种子平铺视图)与分组视图在同一脏窗口同快照重建
        —— 保证四组数据互相一致。"""
        if self._group_view_dirty:
            self._group_view = self._build_group_view()
            self._singles_view = self._build_singles_view()
            self._shows_view = self._build_shows_view()
            self._flat_view = self._build_flat_view()
            self._group_view_ver += 1
            self._group_view_dirty = False
        return self._group_view

    def ensure_group_state(self, rid: Optional[int]) -> dict:
        """WEB 线程调用: 带版本号的合并状态(前端按 rid 跳过整表替换与重渲染)

        rid 与服务端视图版本一致时**不回传 groups**(响应体趋近于零); 不一致时回传
        全量分组数据并带上新版本号。status 体积极小(4 个标量), 无关版本恒回传,
        以保证连接状态/暂停状态/种子数变化能即时反映。
        """
        self.ensure_group_view()
        ver = self._group_view_ver
        updated = rid != ver
        state: dict = {"rid": ver, "updated": updated}
        if updated:
            state["groups"] = self._group_view
            # singles 与 groups 同版本门控: 版本一致时不回传(前端保留原数组, 不触发重渲染)
            state["singles"] = self._singles_view
            # 追剧视图同门控同版本回传(结构与 groups 独立, 前端按 viewMode 取用)
            state["shows"] = self._shows_view
            # 种子平铺视图同门控同版本回传(种子页数据源; 字段集 = SEED_ITEM 契约)
            state["torrents"] = self._flat_view
        return state

    def _build_search_index(self) -> None:
        """主循环线程调用: 增量构建搜索索引(hash -> {name, files[文件名]}), 单次限流拉取。

        **原子交换契约**: 每轮在**新字典**上重组(消失的种子不进新字典即淘汰), 完成后整体替换
        `_search_index` 引用 —— 绝不就地增删旧字典, 否则 Web 线程正在迭代时会抛
        "dictionary changed size during iteration"。已建条目只刷新名称(值替换不改结构, 并发只读安全),
        新种子拉取文件列表(rec.files 惰性拉取 + 记录 _files 跨 tick 缓存, 只在主循环线程), 单条失败
        跳过(记空文件列表)不阻塞整体。
        限流: 单次最多拉取 SEARCH_INDEX_BUILD_BUDGET 条, 未拉完保持 _search_index_dirty=True,
        由后续调用(下一 tick 推进 / 前端据 building 重查投递)续建 —— 避免首轮 N 次 API 长时间阻塞主循环。
        """
        if self.client is None:
            # qB 断开中: 无文件 API 可用, 保持脏待连接恢复后重建(不能把空文件列表当成"已建完")
            self._search_index_dirty = True
            return
        prev = self._search_index if self._search_index is not None else {}
        idx: dict = {}
        budget = SEARCH_INDEX_BUILD_BUDGET
        added = 0  # 本轮新增条目数(追剧视图文件兑底的重建触发依据)
        for h, rec in self.store.by_hash.items():
            entry = prev.get(h)
            if entry is not None:
                entry["name"] = rec.name
            elif budget > 0:
                budget -= 1
                added += 1
                try:
                    files = [f.name for f in rec.files(self.client)]
                except Exception:
                    files = []
                entry = {"name": rec.name, "files": files}
            else:
                # 预算用尽: 剩余种子本轮不进新字典(下次调用续建), 保持脏
                self._search_index = idx
                self._search_index_dirty = True
                self._trigger_shows_rebuild_if_pending(added)
                return
            idx[h] = entry
        self._search_index = idx
        self._search_index_dirty = False
        self._trigger_shows_rebuild_if_pending(added)

    def _trigger_shows_rebuild_if_pending(self, added: int) -> None:
        """追剧视图文件兑底触发: 种子名无标记不会进 _VIEW_FIELDS 置脏 —— 索引推进
        (新增条目)是文件列表就位的唯一信号, 此处置脏让下一轮重建用文件列表归位。
        本方法只在主循环线程调用(与 _group_view_dirty 的既有跨线程语义一致: 竞争
        最坏结果是多重建一次, 无正确性风险)。"""
        if added and self._shows_pending:
            self._shows_pending = False
            self._group_view_dirty = True

    def search_torrents(self, q: str) -> dict:
        """WEB 线程调用: 按 q(种子名 + 文件列表)搜索种子。

        种子名匹配即时遍历 store.by_hash(无 qB API); 文件列表匹配依赖 _search_index 缓存。
        返回 {"results": [..], "building": bool}——building 为 True 表示文件索引已过期/缺失,
        已投递构建命令, 前端应稍后重查以获取完整文件匹配结果。
        结果项含完整明细字段(与分组成员视图对齐): hash/name/site/kind/dlspeed/upspeed/
        uploaded/size/progress/seeding_time/ratio/save_path/tags/category/by, 供前端完整展示命中种子信息。
        """
        def _view(rec, by):
            return {
                "hash": rec.hash,
                "name": rec.name,
                "site": rec.tracker_name,
                "kind": self._state_kind(rec),
                "dlspeed": rec.dlspeed,
                "upspeed": rec.upspeed,
                "uploaded": rec.uploaded,
                "size": rec.size,
                "save_path": rec.save_path,
                "tags": sorted(rec.tags_set),
                "category": rec.category,
                "progress": round(rec.progress, 4),
                "seeding_time": rec.seeding_time,
                "ratio": round(rec.ratio, 3),
                "added_on": rec.added_on,
                # 未归组命中种子以单种子虚拟行展示, 同样需要 HR 列所需字段
                **self._hr_view_fields(rec),
                "by": by,
            }

        q = (q or "").strip().lower()
        if not q:
            return {"results": [], "building": False}
        results = []
        seen = set()
        # 种子名匹配(即时)
        for h, rec in self.store.by_hash.items():
            if q in rec.name.lower():
                seen.add(h)
                results.append(_view(rec, "name"))
        # 文件列表匹配(依赖缓存索引)
        idx = self._search_index
        if idx is not None:
            for h, entry in idx.items():
                if h in seen:
                    continue
                if any(q in fn.lower() for fn in entry["files"]):
                    rec = self.store.by_hash.get(h)
                    if rec is None:
                        continue
                    results.append(_view(rec, "file"))
        building = self._search_index_dirty
        if building:
            self.web_commands.put(("build_search_index", {}))
        return {"results": results, "building": building}

    def touch_web_client(self) -> None:
        """WEB 请求心跳: 刷新 _web_last_seen, 让主循环在 Web 活跃窗口内持续重建分组视图。"""
        self._web_last_seen = time.time()

    def _group_hashes(self, key: tuple) -> List[str]:
        return [h for h in self.store.groups.get(key, []) if h in self.store.by_hash]
