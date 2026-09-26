"""WebviewMixin: WEB UI 视图**构建器**(分组/单种子/追剧/平铺视图 + 搜索索引)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一)。2026-09-20 二次拆分后本模块只留
**构建**: 每个 `_build_*` 都是纯读(读 store / config 产出 dict), 不碰快照、版本号与锁 ——
那些归 `web_runtime.WebUIRuntime`(门面), 由它调本模块的构建器并在同一临界区内发布。

❗新增视图必须挂进 `WebUIRuntime._publish_locked`, 不要在调用点各建一份: 四份视图共用
一个版本号回传, 漏建一份会让前端把陈旧数组当成新数据换上去(2026-09-18 实测事故)。

依赖的宿主属性:
- self.store                种子数据层 TorrentStore(分组索引/by_hash/视图脏标记)
- self.client               qB 原始客户端(搜索索引拉取文件列表用)
- self.web                  WebUIRuntime(快照 / 脏标记 / 搜索索引 / 命令投递)
"""
import logging
import re
import time
from typing import Dict, List, Tuple

from qbittorrentapi import TorrentState, TrackerStatus

from ..hr.resolve import safety_display
from ..torrents import TorrentRecord, view_field_value

logger = logging.getLogger(__name__)

SEARCH_INDEX_BUILD_BUDGET = 500  # 搜索索引单次构建最多拉取的文件列表数(限流, 避免首轮 N 次 qB API 阻塞主循环)

# 搜索匹配口径: 种子名/文件名是 scene 命名(点/下划线/连字符等作分隔), 查询词却以空格分词 ——
# 裸子串匹配时 "cat and" 对不上 "The.Cat.and…"。两侧统一把非文字字符折叠为单空格再匹配;
# 下划线属 \w 须显式并入折叠集, \w 保留 Unicode 文字(CJK 名称可搜)。
_SEARCH_SEP_RE = re.compile(r"[\W_]+")


def _search_norm(s: str) -> str:
    """搜索匹配归一: 分隔符折叠为单空格 + 小写 + 去首尾空 —— 查询词与种子名/文件名配对使用"""
    return _SEARCH_SEP_RE.sub(" ", s).lower().strip()


def _parse_query(q: str) -> Tuple[List[str], List[str]]:
    """搜索查询解析(宽容, 永不报错): 返回 (正词, 负词), 词均为 _search_norm 归一后的子串口径。

    语法(websearch 惯例, 调研报告 26-09-26-1918 §5): 空格分词隐式 AND; 词首单个 `-`(后随非空白)
    为排除; `"…"` 短语整段归一为**连续**子串(可含空格), `-"…"` 排除短语; 其余宽容 —— 孤立 `-`
    忽略, 未闭合引号收至行尾, 词中引号无特殊含义(随归一折叠), 纯标点 token 丢弃。
    词法判定在**原始查询**上进行, 与归一化互不干扰: `-DV` 切词阶段即识别为负词; `web-dl` 不以
    `-` 开头是正词(scene 命名里的连字符经归一折叠为空格, 不会被误判成排除符)。
    """
    pos: List[str] = []
    neg: List[str] = []
    i, n = 0, len(q)
    while i < n:
        if q[i].isspace():
            i += 1
            continue
        negative = q[i] == "-" and i + 1 < n and not q[i + 1].isspace()
        if negative:
            i += 1
        if i < n and q[i] == '"':
            j = q.find('"', i + 1)
            raw = q[i + 1:(n if j == -1 else j)]
            i = n if j == -1 else j + 1
        else:
            j = i
            while j < n and not q[j].isspace():
                j += 1
            raw = q[i:j]
            i = j
        term = _search_norm(raw)
        if term:
            (neg if negative else pos).append(term)
    return pos, neg


# 错误原因(状态列"错误"背后的具体原因)刷新: qB torrents/info **不含**错误文本, 原因只能从
# torrents/trackers 的 msg 取 —— 故只对错误状态种子按 TTL 限额预取, 视图组装只读缓存。
ERROR_REASON_TTL = 300.0  # 单条原因的重取间隔(秒): tracker msg 随站点状态变化, 过期重取
ERROR_REASON_BUDGET = 5  # 单轮最多拉取的 tracker 请求数(限流, 错误种子成片时不阻塞主循环)
# "tracker 报错"状态集合(qB TrackerStatus): 4=not working / 5=tracker error / 6=unreachable
_TRACKER_ERROR_STATUSES = frozenset(
    int(s) for s in (TrackerStatus.NOT_WORKING, TrackerStatus.TRACKER_ERROR, TrackerStatus.UNREACHABLE)
)
# 虚拟 tracker 条目(DHT/PeX/LSD, 非真实站点): 与强制汇报确认同一口径, 不参与报错文本提取
_VIRTUAL_TRACKER_PREFIXES = ("**", "[DHT]", "[PeX]", "[LSD]")

# 集节点聚合状态优先级: 错误 > 下载 > 校验 > 做种 > 暂停 > 其它(前端按 state 着色)
# ❗做种必须排在**暂停之前**: 组/集内"部分暂停部分做种中"是常态(整组只有个别站点被暂停),
#   取 paused 会让整个做种中的行变成灰的(2026-09-21 用户报"辅种页状态色错误")。
#   与前端 `shared/app.js::STATE_RANK` 逐项一致由 tests/test_web.py 静态守阵机械比对。
_SHOW_STATE_RANK = {"error": 0, "downloading": 1, "checking": 2, "seeding": 3, "paused": 4, "other": 5}

# P1-1 按视图回传: 每个视图实际要用的数组。四视图共享同一版本号(rid), 所以"只回一部分"
# 不会让别的视图停在旧数据上 —— 前端切视图时会把 lastRid 置空强制取一次全量。
# 键未列出 / view 为空 ⇒ 回传全部(保守默认)。
VIEW_ARRAYS = {
    # 辅种页: 分组表 + 未归组单种子(singles 是同页的兜底行, 必须一起回)
    "group": ("groups", "singles"),
    # 种子页: 全部种子一行一条的平铺数组
    "torrent": ("torrents", ),
    # 追剧页: 剧→季→集聚合 + **成员索引**。
    # ❗shows 里的 members 只是一串 hash(见前端 memberByHash 注释: 明细成员经索引取, 不随 shows
    #   重复回传), 而索引正是 groups + singles 拼出来的 ⇒ 只回 shows 时前端索引为空,
    #   decoratedShows 的成员解析全部落空: **刷新后停在追剧页会得到一张永久空表**
    #   (2026-09-19 实测: groups=0 / memberByHash=0 / 0 行; 且 rid 已记住 ⇒ 后续每轮都是
    #   "版本未变不回传", 自己不会恢复, 必须切一次视图)。故追剧页必须连带成员索引一起回。
    "show": ("shows", "groups", "singles"),
}


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
    def _error_reason(rec: TorrentRecord) -> str:
        """错误状态种子的**具体原因**(前端状态列据此替代笼统的"错误"; 非错误状态返回空串)

        - missingFiles: 状态本身即原因(文件丢失), 不依赖任何 API
        - error: 主循环预取的 tracker 报错文本(如 "torrent not registered with this
          tracker"); 取不到时(纯磁盘/IO 错误, 或预取尚未跑到)回退状态文本"错误"

        取数单点: 前端只展示这里的字符串, 不得在 JS 里按 state 猜原因(与 HR 标签同约定)。
        """
        e = rec.state_enum
        if e is TorrentState.MISSING_FILES:
            return "文件丢失"
        if e is TorrentState.ERROR:
            return rec.tracker_error_msg or "错误"
        return ""

    @staticmethod
    def _fetch_tracker_error(rec: TorrentRecord, client) -> str:
        """从 tracker 列表提取报错文本(取第一条非空错误 msg); 异常按"取不到"处理

        虚拟条目(DHT/PeX/LSD)跳过 —— 其 msg 与真实站点无关。单条拉取失败不阻塞整体,
        下个 TTL 周期自然重试。
        """
        try:
            entries = client.torrents_trackers(rec.hash) or []
        except Exception as e:
            logger.debug(f"读取 tracker 状态失败({rec.log_repr}): {e}")
            return ""
        for t in entries:
            if str(t.get("url") or "").startswith(_VIRTUAL_TRACKER_PREFIXES):
                continue
            if t.get("status") in _TRACKER_ERROR_STATUSES and (t.get("msg") or "").strip():
                return t["msg"].strip()
        return ""

    def refresh_error_reasons(self) -> None:
        """主循环调用: 刷新错误状态种子的具体原因(WebUI 状态列展示)

        只对 kind=="error" 且原因非状态自明(missingFiles = "文件丢失", 见 _error_reason)
        的种子按 TTL 限额拉取 tracker 状态(错误种子通常个位数; 单轮预算 ERROR_REASON_BUDGET
        条, 成片错误时按轮次摊开, 不阻塞主循环)。
        记录已离开错误状态时清空缓存 —— 否则恢复做种后仍挂着旧原因。

        原因不是快照字段, `store.view_changed` 覆盖不到它, 故变化时显式置
        `_group_view_dirty`(与"由配置派生的展示值"同一判别法: 种子数据一字未变时该值也会变)。
        """
        client = self.client
        if client is None:
            return  # qB 断开: 无 API 可用, 保持现值待连接恢复后刷新
        now = time.time()
        budget = ERROR_REASON_BUDGET
        changed = False
        for rec in self.store.by_hash.values():
            if self._state_kind(rec) != "error" or rec.state_enum is TorrentState.MISSING_FILES:
                if rec.tracker_error_msg:
                    rec.tracker_error_msg = ""
                    rec.tracker_error_ts = 0.0
                    changed = True
                continue
            if rec.tracker_error_ts and now - rec.tracker_error_ts < ERROR_REASON_TTL:
                continue  # 未过期: 直接复用现值
            if budget <= 0:
                continue  # 本轮预算用尽: 余下种子下一轮续取
            budget -= 1
            rec.tracker_error_ts = now  # 先记时间戳: 拉取失败也不在 TTL 内反复重试
            msg = self._fetch_tracker_error(rec, client)
            if msg != rec.tracker_error_msg:
                rec.tracker_error_msg = msg
                changed = True
        if changed:
            self.web.mark_dirty()

    @staticmethod
    def _hr_view_fields(rec: TorrentRecord) -> dict:
        """该成员的 HR 展示字段(标签文本 + 要求/达成布尔 + 三态与依据), 供前端渲染 H&R 栏与对照列

        - hr_tag / hr_tag_done: 已触发未达标 / 已达标时应有的标签(供前端按文本着色)
        - hr_triggered / hr_satisfied: 是否触发 HR / 是否已达成要求
        - hr_req_time: 要求做种时长(秒) = required_seeding_time + extra_seeding_time
        - hr_req_ratio: 要求分享率(0 = 不要求)
        - hr_state / hr_state_text / hr_reason: 站点侧判定(hr / verified_non_hr / unknown /
          exempt=超龄豁免) + 中文说法 + 依据; 接入站点才非空(未接入 = "", 前端据此不显示三态行)
        - hr_safety / hr_safety_text / hr_safety_src: 删除安全档位(danger/failed/safe/unknown/none,
          failed = 未达标终态红档, 2026-09-25 用户修正) +
          含来源的人话短语 + 来源档位 token —— 派生单点在 hr.resolve.safety_display(不新造判定,
          只转译既有结论); 站点未配 HR 全空串(前端整列不显示)
        - hr_site_lane / hr_site_need / hr_site_remain / hr_site_ratio / hr_site_dl: 命中行的
          **站点侧值**(档位 / 还需做种 / 剩余达标 / 分享率 / 下载量) —— 与本地实时值对照用:
          本地值实时但会被重加/转移清零, 站点值是账号级权威但滞后一个刷新周期(计划 §9)
          未命中/未接入一律空串 ""(未知与 0 必须可分: `hr_site_remain == 0` 是"已达标")

        判定委托 TorrentRecord.check_hr_condition/check_hr_satisfied, 标签文本经
        utils.replace_vars 解析 ${required_seeding_time}, 与维护流程(打 HR 标签)完全同源 ——
        前端只做展示比较, 不得在 JS 里重算模板或阈值(否则自定义标签格式/阈值会立即失效)。
        未配置 HR 站点返回全空值(前端据此整列显示"—"), 不做 None 防御(早暴露配置匹配错误)。
        """
        from ..infra import utils as _utils

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
                "hr_state": "",
                "hr_state_text": "",
                "hr_reason": "",
                "hr_safety": "",
                "hr_safety_text": "",
                "hr_safety_src": "",
                "hr_site_lane": "",
                "hr_site_need": "",
                "hr_site_remain": "",
                "hr_site_ratio": "",
                "hr_site_dl": "",
            }
        triggered = rec.check_hr_condition()
        satisfied = triggered and rec.check_hr_satisfied()
        judged = rec.hr_judgement()  # 站点未接入返回 None(下面四个字段留空)
        facts = judged.facts if judged is not None else None
        safety = safety_display(judged, triggered=triggered, satisfied=satisfied)
        fields = {
            "hr_tag":
                "",
            "hr_tag_done":
                "",
            "hr_triggered":
                triggered,
            "hr_satisfied":
                satisfied,
            "hr_req_time":
                hr.required_seeding_time + hr.extra_seeding_time,
            "hr_req_ratio":
                hr.required_share_ratio,
            "hr_state":
                judged.identity.value if judged is not None else "",
            "hr_state_text":
                judged.state_text if judged is not None else "",
            "hr_reason":
                judged.reason if judged is not None else "",
            "hr_safety":
                safety.safety,
            "hr_safety_text":
                safety.text,
            "hr_safety_src":
                safety.src,
            "hr_site_lane":
                facts.lane if facts is not None else "",
            "hr_site_need":
                facts.need_seed_seconds if facts is not None and facts.need_seed_seconds is not None else "",
            "hr_site_remain":
                facts.remain_seconds if facts is not None and facts.remain_seconds is not None else "",
            "hr_site_ratio":
                facts.ratio if facts is not None and facts.ratio is not None else "",
            "hr_site_dl":
                facts.downloaded_bytes if facts is not None and facts.downloaded_bytes is not None else "",
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
            # 错误状态的具体原因(文件丢失 / tracker 报错原文; 非错误状态为空串) ——
            # 前端状态列以它替代笼统的"错误", 见 _error_reason
            "error_reason": self._error_reason(r),
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
        from ..infra import utils as _utils

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

    def _build_speed_totals(self) -> dict:
        """全量种子的上传/下载速度合计(状态栏常显统计的数据源)

        ❗为什么必须由**服务端**算: 状态栏是跨视图的常驻显示, 而四个视图数组是**按视图回传**
        的(见 VIEW_ARRAYS) —— 种子页压根不回 groups。此前由前端对 groups 求和, 于是状态栏
        在种子页恒为 0(issue 26-09-20-1646); 且那份求和还漏掉未归组种子(singles, 实测少算
        88.7%)。改成服务端对 store 全量求和后前端只读一个标量, 与视图分片彻底解耦。

        求和范围 = store.by_hash 全量(组内成员 ∪ 未归组), 与种子页平铺视图同源。
        成本 O(n), 5000 种子约 1~2ms, 每轮视图重建一次。
        """
        dl = 0
        ul = 0
        for r in self.store.by_hash.values():
            dl += r.dlspeed
            ul += r.upspeed
        return {"dlspeed": dl, "upspeed": ul}

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
        from ..core import tvshows

        index = self.web.search_index or {}
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
            self.web.mark_shows_pending(True)
            if self.web.search_index_dirty or self.web.search_index is None:
                self.web.post_command("build_search_index")
        else:
            self.web.mark_shows_pending(False)
        return {"list": out, "unrecognized": sorted(unrecognized)}

    def _build_search_index(self) -> None:
        """主循环线程调用: 增量构建搜索索引(hash -> {name, files[文件名], files_q[归一文件名]}), 单次限流拉取。

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
            self.web.search_index_dirty = True
            return
        prev = self.web.search_index if self.web.search_index is not None else {}
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
                entry = {"name": rec.name, "files": files, "files_q": [_search_norm(f) for f in files]}
            else:
                # 预算用尽: 剩余种子本轮不进新字典(下次调用续建), 保持脏
                self.web.search_index = idx
                self.web.search_index_dirty = True
                self._trigger_shows_rebuild_if_pending(added)
                return
            idx[h] = entry
        self.web.search_index = idx
        self.web.search_index_dirty = False
        self._trigger_shows_rebuild_if_pending(added)

    def _trigger_shows_rebuild_if_pending(self, added: int) -> None:
        """追剧视图文件兑底触发: 种子名无标记不会进 _VIEW_FIELDS 置脏 —— 索引推进
        (新增条目)是文件列表就位的唯一信号, 此处置脏让下一轮重建用文件列表归位。
        本方法只在主循环线程调用(与 _group_view_dirty 的既有跨线程语义一致: 竞争
        最坏结果是多重建一次, 无正确性风险)。"""
        if added and self.web.shows_pending:
            self.web.mark_shows_pending(False)
            self.web.mark_dirty()

    def search_torrents(self, q: str) -> dict:
        """WEB 线程调用: 按 q 搜索种子 —— **全站唯一文本匹配点**(辅种/种子/追剧三页统一消费其结果)。

        匹配口径(**行级**, 拍板 2026-09-26, 调研报告 26-09-26-1918 §5): q 经 _parse_query 解析为
        正/负词(词已是归一后的子串口径); **候选行** = 种子名/站点/分类/保存路径/每个标签/每个
        文件名 各归一为一行, 行通过 ⇔ 含全部正词/短语且不含任何负词/负短语; 种子命中 ⇔ 任一
        候选行通过。负词按行作废(合集包里非 DV 行仍可命中), 多词 AND 约束在同一行内 —— 旧口径
        「整句连续子串」的「恶女 10」失配(两词不连续必不中)由此修复。

        候选行 26-09-26 起**收敛为服务端单点**并覆盖全部文本面: 此前种子页(名字/站点/分类/
        路径/标签的客户端过滤)与追剧页(剧名整句 includes)各持一份匹配实现, 同一语义(恶女 10 /
        季包"cat 12")前后端修了三遍; 现在前端三页一律消费本结果的 hash 集合(searchHits),
        不再持有任何文本匹配代码。站点/分类/路径/标签行只读 store(无 qB API, 与名字行同轮
        即时); 文件行依赖 _search_index 缓存。剧名不单设候选行 —— 追剧视图的展示名本就是
        成员种子名解析出的标题(tvshows.parse_release), 名字行命中天然覆盖。

        返回 {"results": [..], "building": bool, "negative_only": bool}——building 为 True 表示文件
        索引已过期/缺失(只影响**文件行**命中), 已投递构建命令, 前端应稍后重查以获取完整文件
        匹配结果; negative_only 为 True 表示查询只含排除词(无正判据, 「只说不要什么」无从起搜,
        与 Google 一致返回空, 前端据此前端提示)。结果项含完整明细字段(与分组成员视图对齐):
        hash/name/site/kind/error_reason/dlspeed/upspeed/uploaded/size/progress/seeding_time/
        ratio/save_path/tags/category/by, 供前端完整展示命中种子信息(by = 首个通过的行类别,
        供测试定位, 前端不消费)。
        """
        def _view(rec, by):
            return {
                "hash": rec.hash,
                "name": rec.name,
                "site": rec.tracker_name,
                "kind": self._state_kind(rec),
                "error_reason": self._error_reason(rec),
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

        pos, neg = _parse_query(q or "")
        if not pos:
            return {"results": [], "building": False, "negative_only": bool(neg)}

        def _row_passes(row: str) -> bool:
            return all(t in row for t in pos) and not any(t in row for t in neg)

        def _instant_by(rec):
            """即时候选轮(只读 store, 不依赖文件索引): 名字/站点/分类/保存路径/每个标签各归一为一行,
            返回首个通过的行类别, 全不通过返回 None。空值字段不构成候选行。"""
            for by, raw in (
                ("name", rec.name),
                ("site", rec.tracker_name),
                ("category", rec.category),
                ("path", rec.save_path),
                *(("tag", t) for t in rec.tags_set),
            ):
                if not raw:
                    continue
                if _row_passes(_search_norm(raw)):
                    return by
            return None

        results = []
        seen = set()
        # 即时轮: 名字/站点/分类/路径/标签行(归一口径: "cat and" 命中 "The.Cat.and…", 两词无需连续)
        for h, rec in self.store.by_hash.items():
            by = _instant_by(rec)
            if by is not None:
                seen.add(h)
                results.append(_view(rec, by))
        # 文件列表行匹配(依赖缓存索引, 行 = 构建期归一好的 files_q)
        idx = self.web.search_index
        if idx is not None:
            for h, entry in idx.items():
                if h in seen:
                    continue
                if any(_row_passes(fq) for fq in entry["files_q"]):
                    rec = self.store.by_hash.get(h)
                    if rec is None:
                        continue
                    results.append(_view(rec, "file"))
        building = self.web.search_index_dirty
        if building:
            self.web.post_command("build_search_index")
        return {"results": results, "building": building, "negative_only": False}

    def _group_hashes(self, key: tuple) -> List[str]:
        return [h for h in self.store.groups.get(key, []) if h in self.store.by_hash]
