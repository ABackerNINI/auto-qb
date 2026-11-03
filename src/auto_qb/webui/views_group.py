"""辅种分组视图域: GroupMixin(从 views.py 拆出, 仅搬移)"""

from typing import List, Optional

from ..torrents import TorrentRecord

from .views_common import _max_valid_ts, _min_valid_eta


class GroupMixin:
    def _cross_keys_snapshot(self) -> set:
        """跨组文件交叉标记的组 key 全集(读侧快照): 去重集合(plan 26-10-04-0107, 软信号纯内存)
        展平一次, 组装循环里只做 O(1) 成员判定; 空集合时零开销(开关关/无交叉的常态)。

        读侧快照(issue 26-10-06-0028 E-01): _build_* 系会在 Web 请求触发的重建路径
        (runtime.ensure_view/ensure_state)上由 Web 线程执行, 与主循环线程 remove_torrent /
        restore_torrent / reset_runtime / grouping_mod._leave_group 的原地增删并发, 直接迭代
        会抛 "dictionary changed size during iteration"(请求 500)。口径同 build_search_index
        的原子交换契约: 一律取快照引用(tuple/list)后再遍历, 单写线程的写路径一行不动。
        runtime._publish_locked 的 S6 分叉判定也经本方法现取同一键集(与构建期同源同值)。
        """
        return {k for pair in tuple(self.store.cross_group_conflict_warned) for k in pair}

    def _build_group_row(self, key, recs: List[TorrentRecord], cross_keys: set) -> Optional[dict]:
        """单组行构建(plan 26-10-07-0414 S6 拆出的「单组可调用」): 输入组键 + 成员记录集,
        输出组行 dict —— 全量路径(_build_group_view)逐组调用; 局部重聚合
        (runtime._publish_partial_locked)对脏组键单独调用。

        行内字段口径与 _member_view/_seed_view 既有约定逐一保持(纯重构段, S5 镜子守阵 +
        S6 单测「局部重算 == 全量重跑」双保险)。组行内嵌 members 数组随组行整行走
        (P-02 一期口径, R8 不做字段级 patch)。recs 为空(组已空/已解散)返回 None ——
        与全量构建跳过空组的产物对齐, 局部路径据此把该组行从视图剔除。
        """
        from ..infra import utils as _utils

        if not recs:
            return None
        members_view = [self._member_view(r) for r in recs]
        # 可用性组级值先算一次(dict 字面量里对生成器求两次 max 既难读又白费): 全组未知(负)回 None
        avail_max = max(m["availability"] for m in members_view)
        # 字段与拆分前逐字段一致(字段顺序也保持, 便于 diff 审阅)
        return {
            "key":
                _utils.encode_group_key(key),
            "name":
                recs[0].name,
            "count":
                len(recs),
            "dlspeed":
                sum(m["dlspeed"] for m in members_view),
            "upspeed":
                sum(m["upspeed"] for m in members_view),
            "uploaded":
                sum(m["uploaded"] for m in members_view),
            # size = **单种子**大小(同组文件列表相同, 取代表成员); total_size = 全组求和。
            # 两者不等即说明组内大小不一致(前端据此提示风险), 而非显示重复信息
            "size":
                members_view[0]["size"],
            "total_size":
                sum(m["size"] for m in members_view),
            # 组级默认排序键 = 组内**最近添加**时间(前端 sortKey=added_on 降序);
            # 用 max 而非 min: "刚补进来的那个辅种"才是用户最关心的新条目
            "added_on":
                max(m["added_on"] for m in members_view),
            # HR 栏: 分子 = 已触发但未达标(需关注), 分母 = 已触发 HR 的成员数;
            # 在**后端**算好计数, 前端只负责显示(与 memory-bank/pitfalls.md 的"派生值后端算"约定一致)
            "hr_triggered":
                sum(1 for m in members_view if m["hr_triggered"]),
            "hr_pending":
                sum(1 for m in members_view if m["hr_triggered"] and not m["hr_satisfied"]),
            # ---- 辅种扩列(2026-09-28)组级聚合段: 前端只渲染不计算(派生值后端算约定) ----
            # 聚合口径的总原则: 组内成员指向**同一份文件**(组 key 首元即规范化 save_path),
            # 磁盘只占一份 —— 字节量类取"单份"视角(min/单份分母), 只有逐成员真实发生的
            # 网络流量(速度/总上传/已下载)才可求和。
            # 进度 = 组内最高(最完整副本): "内容是否已完整到手"的信号, 与状态徽标互补
            # (徽标说"在下载", 进度说"内容其实已有")
            "progress":
                max(m["progress"] for m in members_view),
            # 剩余时间 = 组内最小有效 eta(依据见 _min_valid_eta: 同组至多一个成员在下载)
            "eta":
                _min_valid_eta(m["eta"] for m in members_view),
            # 已下载 = 全组求和: 多站切换下载的流量总消耗; recheck 从本地承接的字节不计入,
            # 恰好等于这份内容的真实网络成本(边界: 移除成员后其历史流量脱账)
            "downloaded":
                sum(m["downloaded"] for m in members_view),
            # 最近活动 = 组内最新(-1/0 = 从未 哨兵不参与)
            "last_activity":
                _max_valid_ts(m["last_activity"] for m in members_view),
            # 剩余量 = 组内最小: 补齐一份即可 —— 最完整成员还差的字节, 其余成员 recheck 即齐
            "amount_left":
                min(m["amount_left"] for m in members_view),
            # 组分享率 = 总上传 ÷ 单份大小。分母不能是 total_size(N 份会把比率稀释 N 倍);
            # 语义 = "这内容赚回几倍于一份自己的体量"。
            # 代表成员 progress 为 0 时按 0 处理(前端 cellRatio 对 0 进度不显示, 口径一致)
            "ratio":
                round(sum(m["uploaded"]
                          for m in members_view) / members_view[0]["size"], 3) if members_view[0]["size"] else 0.0,
            # 做种时长 = 组内平均(最老/最新成员都不代表整组): 成员值已量化到分钟,
            # 平均后再取整到分钟, 避免组级值以秒粒度抖动
            "seeding_time":
                sum(m["seeding_time"] for m in members_view) // len(members_view) // 60 * 60,
            # 可用性 = 组内最高(内容获取由最好的 swarm 决定, 差站点不妨碍到手);
            # 全组未知(qB 负值)回 None —— 前端显示空白而非 -1.00
            "availability":
                avail_max if avail_max >= 0 else None,
            # 跨组文件交叉标记(bool): 本组与某他组有文件指向同一磁盘物理文件(26-10-04-0107 D4),
            # 前端组名旁渲染警告标记 —— 布尔在后端查好, 前端只渲染不计算(派生值后端算约定);
            # 去重集合的增删由 grouping_mod 显式置 view_changed, 本视图重建后标记自然出现/消失
            "cross_group_conflict":
                key in cross_keys,
            "members":
                members_view,
        }

    def _build_group_view(self) -> List[dict]:
        """从 store 分组索引组装分组视图快照(主循环每 tick 重建, Web 线程只读引用)

        S6 后 = 逐组调用「单组可调用」_build_group_row 的全量循环; 局部重聚合路径
        (runtime._publish_partial_locked)不经本方法, 只对脏组键调 _build_group_row。
        """
        view = []
        cross_keys = self._cross_keys_snapshot()
        # 跨组交叉标记增删的构建期发现(plan 26-10-07-0414 S2): 键集回传门面, _publish_locked
        # 落代时与上一已发布代比较, 增删即本代 full(R11 —— 标记派生自去重集合, 旧组键不归约)
        self.web.note_cross_keys(cross_keys)
        for key, members in tuple(self.store.groups.items()):
            recs = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
            row = self._build_group_row(key, recs, cross_keys)
            if row is not None:
                view.append(row)
        return view
