"""WebviewMixin: WEB UI 视图组装(分组视图/单种子视图/搜索索引/状态回传)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一): 视图组装只读 store 快照与宿主状态,
与核心循环解耦; 组合进 QbManager 后经 self 访问宿主属性。

依赖的宿主属性(由 QbManager.__init__ 初始化):
- self.store                种子数据层 TorrentStore(分组索引/by_hash/视图脏标记)
- self.client               qB 原始客户端(搜索索引拉取文件列表用)
- self.web_commands         WEB 控制命令队列(搜索 building 时投递构建命令)
- self._group_view / self._singles_view / self._group_view_ver
- self._group_view_dirty / self._web_last_seen
- self._search_index / self._search_index_dirty
"""
import logging
import time
from typing import List, Optional

from ..torrents import TorrentRecord, view_field_value

logger = logging.getLogger(__name__)

SEARCH_INDEX_BUILD_BUDGET = 500  # 搜索索引单次构建最多拉取的文件列表数(限流, 避免首轮 N 次 qB API 阻塞主循环)


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

    def _build_singles_view(self) -> List[dict]:
        """未归组种子的单种子视图数据(分组未启用/文件列表不可读的种子不在任何组里,
        只能从这里进入单种子视图; 搜索兜底路径不含全量)。与分组视图在同一脏窗口重建,
        store.view_changed 对任意种子的视图字段变化置真, 故不会读到陈旧状态。"""
        grouped: set = set()
        for members in self.store.groups.values():
            grouped.update(members)
        return [self._member_view(r) for h, r in self.store.by_hash.items() if h not in grouped]

    def ensure_group_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则直接返回当前引用。
        与主循环惰性组装配合: 主循环只在 Web 活跃且视图有变化时重建, 这里兜底保证每次请求都拿到最新。
        singles(未归组种子)与分组视图在同一脏窗口同快照重建 —— 保证两组数据互相一致。"""
        if self._group_view_dirty:
            self._group_view = self._build_group_view()
            self._singles_view = self._build_singles_view()
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
        for h, rec in self.store.by_hash.items():
            entry = prev.get(h)
            if entry is not None:
                entry["name"] = rec.name
            elif budget > 0:
                budget -= 1
                try:
                    files = [f.name for f in rec.files(self.client)]
                except Exception:
                    files = []
                entry = {"name": rec.name, "files": files}
            else:
                # 预算用尽: 剩余种子本轮不进新字典(下次调用续建), 保持脏
                self._search_index = idx
                self._search_index_dirty = True
                return
            idx[h] = entry
        self._search_index = idx
        self._search_index_dirty = False

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
