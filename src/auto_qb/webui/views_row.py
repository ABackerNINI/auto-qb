"""单种子/扁平/速度汇总视图域: RowMixin(从 views.py 拆出, 仅搬移)"""

from typing import List

from ..infra.utils import encode_group_key
from ..torrents import view_field_value


class RowMixin:
    def _member_view(self, r) -> dict:
        """单成员展示视图(分组视图 members 与 singles 未归组种子共用同一字段构建)"""
        # occ_key 的内容单元查表先行(组 key 单次 .get(); group_key 是 member_to_key 的
        # 非迭代读取, 与 Web 线程重建路径并发无 "dictionary changed size" 风险)
        gkey = self.store.group_key(r.hash)
        site_alert, site_alert_msg = self._site_alert(r)
        return {
            "hash": r.hash,
            "name": r.name,
            "site": r.tracker_name,
            "state": r.state,
            "kind": self.state_kind(r),
            # 错误状态的具体原因(文件丢失 / tracker 报错原文; 非错误状态为空串) ——
            # 前端状态列以它替代笼统的"错误", 见 _error_reason
            "error_reason": self._error_reason(r),
            # 站点 chip 左槽的持久健康告警(计划 26-10-19-2007 S2): "" / "no_site_conf" /
            # "tracker_error" + 展示文本(报错原文截断 / 固定文案)。判定单点在 _site_alert,
            # 前端只按 token 选图标与颜色, 不按 state 猜原因。
            "site_alert": site_alert,
            "site_alert_msg": site_alert_msg,
            "dlspeed": r.dlspeed,
            "upspeed": r.upspeed,
            "uploaded": r.uploaded,
            "size": r.size,
            # 组级"共同标签/分类"与保存路径筛选器的数据来源(交集/共同值由前端计算,
            # 后端只透出原始值, 避免每次重建做 O(成员数) 以上的集合运算)
            "save_path": r.save_path,
            # 迁移可见性(P0): 只读 job 快照标注(不改 save_path; 构建期零文件系统探测)
            "relocate": self._relocate_member(r.hash),
            "tags": sorted(r.tags_set),
            "category": r.category,
            "progress": round(r.progress, 4),
            # 取整到分钟(与 torrents.view_field_value 的重建判定同一步长): 该字段每秒递增,
            # 不取整会让做种中的种子每轮置脏, 惰性重建失效; 前端展示精度本就是分钟
            "seeding_time": view_field_value("seeding_time", r.seeding_time),
            "ratio": round(r.ratio, 3),
            # 添加时间(unix 秒): 组级默认排序取组内最大值(见下方组级 added_on)
            "added_on": r.added_on,
            # ---- 辅种扩列(2026-09-28)成员透传段: 明细表新列的数据源, 口径与种子页 SEED_ITEM 一致 ----
            # eta/time_active/last_activity 经 view_field_value 分钟量化(秒级递增字段, 同 seeding_time);
            # 哨兵原样带过(eta 8640000 / 时间点 -1 = 从未), 前端 format.js 的 fmtEta/fmtTs 按哨兵显示空白
            "eta": view_field_value("eta", r.eta),
            "downloaded": r.downloaded,
            "amount_left": r.amount_left,
            "last_activity": view_field_value("last_activity", r.last_activity),
            "time_active": view_field_value("time_active", r.time_active),
            "completion_on": r.completion_on,
            "availability": round(r.availability, 2),
            "dl_limit": r.dl_limit,
            "up_limit": r.up_limit,
            "tracker": r.tracker,
            "infohash_v1": r.infohash_v1,
            "infohash_v2": r.infohash_v2,
            "seen_complete": r.seen_complete,
            # HR 展示字段(标签语义色 + 要求/达成布尔): 判定与打标签流程同源, 见 hr_view_fields
            **self.hr_view_fields(r),
            # 连接数快照(TorrentRecord 已有): 成员/未归组种子直接透出, 供前端种子页与成员列展示
            "num_seeds": r.num_seeds,
            "num_leechs": r.num_leechs,
            "num_complete": r.num_complete,
            "num_incomplete": r.num_incomplete,
            # occ_key(2026-10-18, 计划 26-10-18-2013 D8): 内容单元标识 —— 归组种子带其辅种组
            # key(encode_group_key, 与组行 key 同键空间), 未归组为 null(前端按
            # m.occ_key || ("self:"+m.hash) 兜成自单元)。前端选中摘要
            # (selection.js::selSizeSummaryOf)按它把"同一份文件的多站点副本"并成一个占用
            # 单元(单元值取选中成员最大 size, Y≤X 恒成立)。只回键不回值: 单元值由前端从
            # 选中成员现算, 后端不对"选中子集"做假设(组行 size/total_size 双口径的选中版)。
            # 种子页平铺行经 _seed_view 的 {**_member_view(r), ...} 继承本字段(不重述,
            # 守阵 test_seed_view_no_member_view_restatement)。字段恒在/null = 不适用的
            # 契约与 availability 等同族(不搞"有条件缺键")。
            "occ_key": encode_group_key(gkey) if gkey is not None else None,
        }

    def _seed_view(self, r) -> dict:
        """种子中心视图条目(SEED_ITEM): 成员视图全字段 + 扩展 qB 数据字段

        WEB UI 替代 qB 界面的"种子页"数据源: 平铺列表/详情抽屉展示用。在 _member_view
        基础上补齐 TorrentRecord 的全部展示字段(字段集 = torrents/view._VIEW_FIELDS
        的平铺扩展段); eta/time_active/last_activity 按分钟量化(与重建判定同一步长)。

        !**不重述 `_member_view` 已给的字段**(issue webui-seed-view-restate-dup): 此前这里
        以 `{**_member_view(r), ...}` 起手后又重列了 eta/completion_on/availability/dl_limit/
        up_limit/tracker/num_*/downloaded 等 16 个同名字段(值逐字相同) —— 同一字段两处声明,
        `_member_view` 改口径(如量化步长)会被这里的重述静默盖住, 种子页与分组/单种子页展示
        漂移。现在只剩真正的平铺扩展段; 同名字段一律以 `_member_view` 为准(守阵:
        test_seed_view_no_member_view_restatement 钉两边同名字段等值)。
        """
        return {
            **self._member_view(r),
            "total_size": r.total_size,
            "max_ratio": r.max_ratio,
            "max_seeding_time": r.max_seeding_time,
            "max_inactive_seeding_time": r.max_inactive_seeding_time,
            "trackers_count": r.trackers_count,
            "seq_dl": r.seq_dl,
            "f_l_piece_prio": r.f_l_piece_prio,
            "auto_tmm": r.auto_tmm,
            "force_start": r.force_start,
            "super_seeding": r.super_seeding,
            "priority": r.priority,
            # magnet_uri 刻意不在轮询载荷(issue E-04, P-06 拍板): 契约口径 = 只在用户显式
            # 动作时才需要的字段不进每轮响应体(magnet 添加型库为 MB 级增量, 坑档
            # contract-api); "复制磁力"经 /api/torrents/{hash} 按需取一次详情(drawer.js
            # copyTorrentInfo), 该端点 to_dict() 全字段兜底。
            # infohash_v1 已并入 _member_view 透传段(2026-10-12, 与 infohash_v2 同源 —— 种子页
            # 不再单独重述, 守阵 issue webui-seed-view-restate-dup 钉两边同名字段等值)。
            "private": r.private,
            "comment": r.comment,
            "created_by": r.created_by,
            "creation_date": r.creation_date,
            "has_metadata": r.has_metadata,
            "piece_size": r.piece_size,
            "pieces_have": r.pieces_have,
            "pieces_num": r.pieces_num,
            "total_wasted": r.total_wasted,
            "connections_count": r.connections_count,
            "connections_limit": r.connections_limit,
            "reannounce": r.reannounce,
            "reannounce_in": r.reannounce_in,
            "has_tracker_error": r.has_tracker_error,
            "has_tracker_warning": r.has_tracker_warning,
            "has_other_announce_error": r.has_other_announce_error,
            "content_path": r.content_path,
            "download_path": r.download_path,
            "root_path": r.root_path,
            "popularity": r.popularity,
            "downloaded_session": r.downloaded_session,
            "uploaded_session": r.uploaded_session,
        }

    def _build_flat_view(self) -> List[dict]:
        """种子平铺视图(全部种子一列表): 与分组视图同一脏窗口同快照重建。

        WEB UI 替代 qB 界面的"种子页"数据源: 不依赖辅种分组是否启用, store.by_hash
        全量进视图(前端在平铺列表上自行筛选/排序/多选; 字段集 = SEED_ITEM 契约)。
        """
        return [self._seed_view(r) for r in tuple(self.store.by_hash.values())]  # 读侧快照(见 _build_group_view)

    def _build_speed_totals(self) -> dict:
        """全量种子的上传/下载速度合计(状态栏常显统计的数据源)

        !为什么必须由**服务端**算: 状态栏是跨视图的常驻显示, 而四个视图数组是**按视图回传**
        的(见 VIEW_ARRAYS) —— 种子页压根不回 groups。此前由前端对 groups 求和, 于是状态栏
        在种子页恒为 0(issue 26-09-20-1646); 且那份求和还漏掉未归组种子(singles, 实测少算
        88.7%)。改成服务端对 store 全量求和后前端只读一个标量, 与视图分片彻底解耦。

        求和范围 = store.by_hash 全量(组内成员 ∪ 未归组), 与种子页平铺视图同源。
        成本 O(n), 5000 种子约 1~2ms, 每轮视图重建一次。
        """
        dl = 0
        ul = 0
        for r in tuple(self.store.by_hash.values()):  # 读侧快照(见 _build_group_view): Web 重建路径可达
            dl += r.dlspeed
            ul += r.upspeed
        return {"dlspeed": dl, "upspeed": ul}

    def _build_singles_view(self) -> List[dict]:
        """未归组种子的单种子视图数据(分组未启用/文件列表不可读的种子不在任何组里,
        只能从这里进入单种子视图; 搜索兜底路径不含全量)。与分组视图在同一脏窗口重建,
        store.view_changed 对任意种子的视图字段变化置真, 故不会读到陈旧状态。"""
        grouped: set = set()
        for members in tuple(self.store.groups.values()):  # 读侧快照(见 _build_group_view)
            grouped.update(members)
        return [self._member_view(r) for h, r in tuple(self.store.by_hash.items()) if h not in grouped]
