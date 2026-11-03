"""追剧(剧/季/集)视图域: EpisodesMixin(从 views.py 拆出, 仅搬移)"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from ..torrents import TorrentRecord

from .views_common import _SHOW_STATE_RANK, _SHOW_STATE_RANK_LAST, _ep_sort_key

if TYPE_CHECKING:
    from ..core.tvshows import ParsedRelease  # 仅类型标注(注解为字符串)


class EpisodesMixin:
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
        kind = self.state_kind(rec)
        hr = self.hr_view_fields(rec)
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

    @staticmethod
    def _parse_show_member(rec, files: Optional[List[str]]) -> Tuple[TorrentRecord, "ParsedRelease", bool]:
        """单成员解析 + 文件兑底(plan 26-10-07-0414 S9a 抽出的小函数): 单个种子归属哪部剧/
        哪季哪集的**分类**口径 —— 全量构建与 S9b 脏剧局部重算共用这一份, 不各自复刻。

        种子名 parse_release 后, 季包/无标记名称在文件列表就位时 refine_with_files 展开
        (名称标记优先, 已有明确集数/日期的结果不改)。返回 (rec, parsed, pending):
        pending=True 表示该 hash 可被文件兑底但搜索索引未覆盖(调用方登记待归位,
        _build_shows_view 接线 shows_pending); files=None 即索引未覆盖该 hash,
        索引已覆盖但文件列表为空同样按未覆盖处理(与拆分前逐分支一致)。
        注意 refine_with_files 不改剧键(S8 已核: replace 字段集仅 kind/season/ep,
        后增 season_inferred 留痕位), 故剧键归属在兑底前后稳定, 分类结果可放心喂给 _build_show_row 聚合。
        """
        from ..core import tvshows

        parsed = tvshows.parse_release(rec.name)
        pending = False
        if parsed.kind in (tvshows.KIND_SEASON_PACK, tvshows.KIND_UNKNOWN) and parsed.key:
            if files:
                parsed = tvshows.refine_with_files(parsed, files)
            else:
                pending = True  # 可被文件兑底但索引未覆盖: 待索引建成后归位
        return rec, parsed, pending

    def _build_show_row(self, key: str, members: List[Tuple[TorrentRecord, "ParsedRelease"]]) -> Optional[dict]:
        """单剧行构建(plan 26-10-07-0414 S9a 拆出的「单剧可调用」, 先例 _build_group_row):
        输入剧键 + 该剧成员集(每项 = (种子记录, 解析结果) —— 解析/文件兑底属分类步骤,
        由调用方经 _parse_show_member 完成后按剧键分桶传入, 全量路径与 S9b 局部重算都
        不重复 parse_release), 输出剧行 dict; members 为空(剧已无成员)返回 None ——
        与 _build_group_row 空组口径对齐, 局部重聚合据此把该剧行从视图剔除。

        拆分口径(plan §06 正确性边界 2-4 落位, 逐条现码重核, 全部**剧内局部**, 无跨剧
        共享输入需要显式入参):
        - 剧名频次(现码 :705-708)是剧内局部统计 —— titles 只从本剧成员的 parsed.title
          累加, 展示名 = 本剧成员标题的众数 —— 收进本函数; S9b 边界3「重扫该剧成员标题」
          = 对脏剧成员重解析后重调本函数, 天然局部, 无需全局重扫;
        - 季级 covered/gaps(现码 :741-752)按 (剧,季) 在剧内整季重算, 本就剧内局部;
        - 集行 state 按 _SHOW_STATE_RANK 取 min(现码 :725, 无跨行传播)、members 是数组
          整体(现码 :734, R8 行级 upsert 不做字段级 patch), 语义原样保留。
        """
        from ..core import tvshows

        if not members:
            return None
        titles: Dict[str, int] = {}
        seasons: Dict[Optional[int], dict] = {}
        for rec, parsed in members:
            if parsed.title:
                titles[parsed.title] = titles.get(parsed.title, 0) + 1
            # 日期型集键不挂编号季(综艺/日播无季概念): 归 None 季桶, 前端渲染为"日播/特别篇"
            skey = parsed.season if parsed.kind != tvshows.KIND_DATE else None
            nodes = seasons.setdefault(skey, {})
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

        # ---- 行组装(拆分前 _build_shows_view 的 per-show 循环体原样搬入, 逐字段一致) ----
        # 展示名 = 出现频次最高的原始剧名(并列取更长/字典序, 保证确定性)
        name = max(titles.items(), key=lambda kv: (kv[1], len(kv[0]), kv[0]))[0] if titles else key
        seasons_out = []
        latest = 0
        member_total = 0
        ep_total = 0
        # 编号季升序在前, None 季桶(日期型)殿后
        for skey in sorted(seasons, key=lambda s: (s is None, s if s is not None else 0)):
            nodes = seasons[skey]
            eps_out = []
            covered = set()
            has_pack = False
            for nkey in sorted(nodes, key=_ep_sort_key):
                node = nodes[nkey]
                eps_out.append(
                    {
                        "key": list(nkey),
                        "count": len(node["members"]),
                        "state": min(node["kinds"], key=lambda k: _SHOW_STATE_RANK.get(k, _SHOW_STATE_RANK_LAST)),
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
        return {
            "key": key,
            "name": name,
            "latest": latest,
            "member_count": member_total,
            "episode_count": ep_total,
            "seasons": seasons_out,
        }

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
        标记 web.shows_pending 并投递构建命令 —— 索引推进后由 build_search_index
        置脏触发重建归位(种子名无标记不会自动置脏, 这是唯一需要动重建时序的点)。

        S9a 起拆「单剧可调用」(plan 26-10-07-0414): 本方法只做全库**分类**(逐 hash 经
        _parse_show_member 解析/兑底, unrecognized/pending 出口径)→ 按剧键分桶 → 逐剧调
        _build_show_row 产行; S9b 局部重聚合不经本方法, 只对脏剧键重解析成员后重调
        _build_show_row(拆分口径见其 docstring)。

        返回 {"list": [剧…], "unrecognized": [hash…]}:
          剧: {key, name, latest, member_count, episode_count, seasons: [季…]}
          季: {season(编号或 None=日播/日期型), gaps(缺集列表), episodes: [集…]}
          集: {key: ["ep",n]|["range",a,b]|["pack"]|["date",iso], count, state,
               速度/上传/size(代表版本)/progress(最差版本)/HR 计数/sites/members(hash)/added_on}
        """
        from ..core import tvshows

        index = self.web.search_index or {}
        by_show: Dict[str, List[Tuple[TorrentRecord, "ParsedRelease"]]] = {}
        unrecognized: List[str] = []
        pending: List[str] = []
        for h, rec in tuple(self.store.by_hash.items()):  # 读侧快照(见 _build_group_view)
            rec, parsed, is_pending = self._parse_show_member(rec, (index.get(h) or {}).get("files"))
            if is_pending:
                pending.append(h)
            if parsed.kind == tvshows.KIND_UNKNOWN or not parsed.key:
                unrecognized.append(h)
                continue
            by_show.setdefault(parsed.key, []).append((rec, parsed))

        # S9a 后 = 逐剧调用「单剧可调用」_build_show_row 的全量循环; 局部重聚合(S9b)
        # 不经本方法, 只对脏剧键重解析成员后调 _build_show_row。by_show 保持首次出现序
        # (dict 插入序), 供下游稳定排序复现拆分前行序。
        out = []
        for key, members in by_show.items():
            row = self._build_show_row(key, members)
            if row is not None:
                out.append(row)
        # 默认排序: 剧内最近有动静的剧在前(与分组视图"新补的辅种最先看到"同哲学)
        out.sort(key=lambda s: (-s["latest"], s["name"]))

        # 文件兑底接线: 待解析种子且索引未覆盖 -> 标记 pending 并投递构建命令(幂等,
        # 拉取限流由索引侧 SEARCH_INDEX_BUILD_BUDGET 控制; 索引已覆盖但无文件的不再投递)
        pending = [h for h in pending if h not in index]
        if pending:
            self.web.mark_shows_pending(True)
            if self.web.search_index_dirty or self.web.search_index is None:
                self.web.post_command("build_search_index")
        else:
            self.web.mark_shows_pending(False)
        return {"list": out, "unrecognized": sorted(unrecognized)}

    def _trigger_shows_rebuild_if_pending(self, added: int) -> None:
        """追剧视图文件兑底触发: 种子名无标记不会进 _VIEW_FIELDS 置脏 —— 索引推进
        (新增条目)是文件列表就位的唯一信号, 此处置脏让下一轮重建用文件列表归位。
        本方法只在主循环线程调用(与 web.group_view_dirty 的既有跨线程语义一致: 竞争
        最坏结果是多重建一次, 无正确性风险)。"""
        if added and self.web.shows_pending:
            self.web.mark_shows_pending(False)
            self.web.mark_dirty()
