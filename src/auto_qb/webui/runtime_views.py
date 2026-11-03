"""WebUIRuntime 拆分: 视图发布 / 增量归约 / 搜索索引与错误原因推进。

move-only 自 runtime.py 切出(计划 26-11-02-2342 §07 R5), 未改语义; 由根 runtime.py 组合进 WebUIRuntime。
"""
from typing import List, Optional

from .runtime_common import _DELTA_VIEWS, _cancel_delta_buckets, _new_delta_buckets


class ViewsMixin:
    def _drain_delta_locked(self, store) -> None:
        """把 store 本轮增量推导成脏行键并入 _delta_pending(**持 view_lock**, 主循环线程)

        映射口径(plan S2/S9b): flat/singles 行键 = hash 直用 -> torrent 桶; 组行键 =
        store.member_to_key -> group 桶(成员字段变化会改组行聚合值); 剧行键 =
        _show_member_keys(S8 剧键映射)-> show 桶。数据源 = S1 属性快照
        (last_added/last_removed) + delta_fields(变化字段集, added 不在其中) +
        group_key_migrations(组键迁移待办: 旧键不在 groups -> removed, 在 -> upsert)。

        组行 removed 键推导: 先查 member_to_key 后消费 removed 清单 —— 查得到: 组仍在 ->
        组行内容变了(upsert), 组已解散 -> 组行消失(removed); 查不到(组键已随
        _leave_group/解散清除, 且与「从未归组」不可区分) -> 该组行键不可归约 -> 本代
        full(R11 保守正确优先)。

        show 桶推导(plan S9b): 成员离开/成员字段变化都会改剧行聚合值(频次/季级 gaps/
        状态归并全是剧内聚合) -> 该剧键整行重建。removed 成员的**旧**剧键须在映射清理
        **前**捕获(S8 清理在后); added/delta_fields 涉及 hash 的**新**剧键在 S8 映射更新
        **后**现算 —— 两个方向都进 upsert(重建候选), 全删剧转 removed 由局部重聚合
        _build_show_row 回 None 定行止(S8 口径「候选允许过宽, 重聚合按当前库态定行止」)。
        名称解析不出剧键的 hash 不在映射 -> 无剧行, 不推导。

        同一临界区顺带更新剧键等价映射(plan S8): S1 added/delta_fields 涉及的 hash 现算
        新剧键, 键变化记迁移候选 —— 详见 _update_show_member_keys_locked。
        """
        added = store.last_added
        removed = store.last_removed
        delta_fields = store.delta_fields
        # 组键迁移待办(P7): _leave_group/_assign_to_group 登记的旧/新键 —— 组键**更换**
        # (save_path 变化或武装重归组)无法用行级 delta 精确表达: 旧键行该消失、新键行该
        # 建出, 但 upsert/removed 桶的跨代抵消(R5)会把「先 upsert 后 removed」的同键两清,
        # 让旧行滞留成孤儿。迁移是低频事件(仅搬迁/重载), 直接本代 full(保守正确优先,
        # 与 row_key_unresolvable 同口径) —— 全量重建从 store.groups 现算, 恒无孤儿/缺行。
        if store.group_key_migrations:
            self._pending_full_reasons.add("group_key_migration")
            store.group_key_migrations = set()
        if not added and not removed and not delta_fields:
            return
        upsert = self._delta_pending["upsert"]
        rem = self._delta_pending["removed"]
        t_up, g_up = upsert["torrent"], upsert["group"]
        t_rm, g_rm = rem["torrent"], rem["group"]
        s_up = upsert["show"]
        member_to_key = store.member_to_key
        groups = store.groups
        show_keys = self._show_member_keys
        unresolvable = False
        for h in added:
            t_up.add(h)
            key = member_to_key.get(h)
            if key is not None:
                g_up.add(key)
        for h in delta_fields:
            t_up.add(h)
            key = member_to_key.get(h)
            if key is not None:
                g_up.add(key)
        for h in removed:
            t_rm.add(h)
            key = member_to_key.get(h)
            if key is not None:
                # 组仍在 -> 行内容变了(upsert); 组已解散 -> 行已消失(removed)
                (g_up if key in groups else g_rm).add(key)
            else:
                unresolvable = True
            # 旧剧键在映射清理前捕获: 成员离开 -> 该剧行内容必然变化(重建候选)
            sk = show_keys.get(h)
            if sk is not None:
                s_up.add(sk)
        if unresolvable:
            self._pending_full_reasons.add("row_key_unresolvable")
        self._update_show_member_keys_locked(store, added, delta_fields, removed)
        # 新剧键现算(S8 映射更新后): added/delta_fields 涉及 hash 的落点剧键
        for h in added:
            sk = show_keys.get(h)
            if sk is not None:
                s_up.add(sk)
        for h in delta_fields:
            sk = show_keys.get(h)
            if sk is not None:
                s_up.add(sk)

    def _update_show_member_keys_locked(self, store, added, delta_fields, removed) -> None:
        """剧键等价映射更新(plan S8, **持 view_lock**): S1 added/delta_fields 涉及的 hash
        现算新剧键并登记; 旧键存在且不同 -> 记「旧剧行 removed + 新剧行 upsert」迁移候选
        (S9 消费的暂存, 本步不进时间线 show 桶); removed 清理映射条目 —— 映射与 store
        状态同步。

        剧键口径 = tvshows.parse_release(rec.name).key, 出处 views._build_shows_view 现算
        点(views.py, 「parsed = tvshows.parse_release(rec.name)」行)—— 口径以现码为准;
        refine_with_files 不改 key(tvshows.py replace 字段集仅 kind/season/ep,
        后增 season_inferred 留痕位), 故文件兑底不影响剧键, 无需复刻索引兑底。局部导入同 views 同款(核心域入口按需取)。

        解析不出剧键的 hash 不登记; 已登记 hash 改名进未识别区 -> 清条目, 候选只记旧键
        一侧(新剧行不存在)。暂存只供 S9 推导脏剧键: 候选允许「过宽」—— 名称可解析但暂居
        未识别区(如季包待文件兑底)的 hash 也按 parse 键登记, 其迁移候选的旧键行可能实际
        未含该成员, S9 重聚合按当前库态定行止; 决不允许「过窄」—— 凡剧键变化的成员迁移必
        产出旧+新两侧候选。同拍增删同 hash 以删除为准(登记在先、清理在后, 与 store.by_hash
        终态一致)。
        """
        from ..core import tvshows  # 局部导入同 views._build_shows_view 同款

        mapping = self._show_member_keys
        staged = self._pending_show_migrations
        by_hash = store.by_hash

        def _register(h: str) -> None:
            rec = by_hash.get(h)  # 已删 hash(同拍增删/删除残值)现算不出键: 走清除分支
            new_key = tvshows.parse_release(rec.name).key if rec is not None else ""
            old_key = mapping.get(h)
            if old_key is not None and new_key != old_key:
                # 成员迁移(正确性边界 1): 旧剧行失去该成员 -> 旧键 removed 候选; 新名解析
                # 出剧键 -> 新剧行获得该成员 -> 新键 upsert 候选
                staged["removed"].add(old_key)
                if new_key:
                    staged["upsert"].add(new_key)
            if new_key:
                mapping[h] = new_key
            else:
                mapping.pop(h, None)

        for h in added:
            _register(h)
        for h in delta_fields:
            _register(h)
        for h in removed:
            mapping.pop(h, None)

    def _backfill_show_member_keys_locked(self, store) -> None:
        """剧键映射重启回填(plan S8, **持 view_lock**): 映射为空时全库现算登记, 全量路径
        调用(「首拍全量时回填」)。

        重启后映射空且客户端本就窗外 full(R10) —— 回填无旧键可比, 纯登记不产生迁移候选。
        非空即跳过: 运行期映射由排空段增量维护, 全库扫描只在重启后首代发生一次(全量路径
        可能因降级源反复走, 幂等)。by_hash 快照迭代同 _build_shows_view 读侧口径(发布可能
        经 Web 线程 ensure_state 触发, 主循环侧 apply 并发改库的窗口内不裸迭代)。
        """
        if self._show_member_keys:
            return
        from ..core import tvshows

        parse = tvshows.parse_release
        for h, rec in tuple(store.by_hash.items()):
            key = parse(rec.name).key
            if key:
                self._show_member_keys[h] = key

    def _merge_pending_error_hashes_locked(self) -> None:
        """错误原因预取的行级脏并入累积器(**持 view_lock**, plan S2 补)

        refresh_tracker_health 改写 tracker_error_msg / tracker_health_msg 的受影响 hash 进
        torrent 桶; 组行 members 的 error_reason / site_alert 随成员变化 -> 组键经
        member_to_key 一并进 group 桶(与
        store 增量推导同口径)。S6 起调用点在 _publish_locked 的分叉判定前(键集须在
        构建**前**定型) —— 分叉判定需要完整键集, fold 落代段不再重跑。
        """
        error_hashes = self._pending_error_hashes
        if not error_hashes:
            return
        member_to_key = self._host.store.member_to_key
        error_upsert = self._delta_pending["upsert"]
        for h in error_hashes:
            error_upsert["torrent"].add(h)
            key = member_to_key.get(h)
            if key is not None:
                error_upsert["group"].add(key)
        error_hashes.clear()

    def _merge_pending_show_migrations_locked(self) -> None:
        """剧键迁移候选并入累积器(plan S8/S9b, **持 view_lock**)

        S8 暂存的迁移候选在键集定型段并入 show 桶(与 _merge_pending_error_hashes_locked
        同款生命周期: 并入后清空, 调用点在 _publish_locked 的分叉判定前 —— 分叉判定需要
        完整键集)。并入目标两侧统一为 **upsert**(重建候选): 暂存口径「候选允许过宽,
        重聚合按当前库态定行止」—— 旧剧键行可能仍有其余成员(须重建为减员后的内容),
        全删剧由局部重聚合 _build_show_row 回 None 转 removed; 由此「决不允许过窄」
        (凡剧键变化的成员迁移必被重算)由两侧候选都参与重建保证。
        """
        staged = self._pending_show_migrations
        if not staged["upsert"] and not staged["removed"]:
            return
        show_up = self._delta_pending["upsert"]["show"]
        show_up |= staged["upsert"]
        show_up |= staged["removed"]
        staged["upsert"].clear()
        staged["removed"].clear()

    def _fold_delta_pending_locked(self) -> None:
        """把跨拍累积的脏行键折叠成本代时间线条目并清空累积器(**持 view_lock**)

        - 每次发布恰追加一条目(maxlen 截断兜底窗口滑出; 时间线全局一份, R2)。
        - 交叉抵消(R5): 落代前分视图 upsert -= removed; removed -= upsert —— 同拍增删
          同一行净变化为零, 不给客户端又删又发同一行。
        - full 代判定(R11): 本代任一降级源活跃 -> full=true 且键集清空, 累积器与理由
          一并清空(full 响应覆盖到当前 ver, 累积键已无意义)。
        - 错误原因预取暂存已前移到 _publish_locked 的 S6 分叉判定段(构建前定型本代键集);
          交叉键集基线检查在此保留(与分叉判定段同条件幂等, 兜构建期键集竞态)。
        """
        ver = self.group_view_ver
        reasons = self._pending_full_reasons
        # 跨组交叉标记增删: 本代构建期发现的键集与上一已发布代不同 -> 本代 full
        # (首代只立基线: 时间线此前为空, 任何客户端本就窗外)
        if self._cross_keys_prev is not None and self._cross_keys_seen != self._cross_keys_prev:
            reasons.add("cross_group")
        self._cross_keys_prev = self._cross_keys_seen
        if reasons:
            entry = {"ver": ver, "full": True, **_new_delta_buckets()}
            reasons.clear()
            self._delta_pending = _new_delta_buckets()
        else:
            _cancel_delta_buckets(self._delta_pending)
            upsert = self._delta_pending["upsert"]
            removed = self._delta_pending["removed"]
            entry = {"ver": ver, "full": False, "upsert": upsert, "removed": removed}
            self._delta_pending = _new_delta_buckets()
        self._delta_timeline.append(entry)

    def flush_views(self, force: bool = False) -> None:
        """消费视图脏标记并在 Web 活跃时惰性重建(同步线 / 任务线各自调用一次)

        每拍次序(plan 26-10-07-0414 S2): ①先排空 store 增量为脏行键并入 `_delta_pending`
        —— **先于**"已取走"门控, 门控跳拍的键集累积进下一代不丢(R4); ②消费 view_changed
        置脏(keyed 判定须联合 `rounds_applied` 前进, 防「最近一轮」快照残值误判, 见下);
        ③HR 判定新鲜度波次置脏; ④门控通过才 `rebuild_views()`。落代在 `_publish_locked`:
        跨拍累积折叠进 `_delta_timeline` —— **只存键不存值**, 行内容回放时从当前已发布视图
        现取(R1); 四视图 + 版本号在同一 `view_lock` 临界区内发布(「四视图同轮发布」硬约束,
        模块 docstring), 主循环与 Web 线程的 ensure_* 兜底都只经这一条发布路径 —— 单一写
        线程假设不破, 也不引入第二把锁(R12)。

        `force=True` 表示"本轮有命令改了种子状态", 必须**绕过**下面的"已取走"门控 ——
        用户操作后真值要在几十毫秒内进快照, 不能因为上一版还没被取走就跳过。
        """
        host = self._host
        # 增量排空(plan S2): 每拍(无论门控是否放行)先把 store 本轮增量推导成脏行键并入
        # _delta_pending —— 门控跳拍的键集累积进下一代不丢(R4)。排空段持 view_lock: 落代
        # 折叠在 _publish_locked(可能经 Web 线程 ensure_state 触发)的同一临界区, 同锁才无
        # 并发折叠/累积竞态(R12, 不引入新锁)。last_added/last_removed 只读不排空(下轮
        # _apply 覆盖, S1「最近一轮」语义), 同拍两次 flush 重复并入同键集 —— 集合语义幂等。
        rounds_now = host.store.rounds_applied
        with self.view_lock:
            self._drain_delta_locked(host.store)
        # 本拍 store 是否提供行级键: last_added/last_removed/delta_fields 是「最近一轮」快照
        # (不排空、下轮 _apply 覆盖), 无新应用轮时是残值, 不得当作本拍键源 —— 故须同时要求
        # 本拍确有新的 _apply 轮(rounds_applied 前进)。命令自写(update_torrent_fields)/
        # reset_runtime/标签定义删除这类纯命令源不跑 _apply, 只置 view_changed。
        keyed = rounds_now != self._drained_sync_rounds and bool(
            host.store.last_added or host.store.last_removed or host.store.delta_fields
        )
        self._drained_sync_rounds = rounds_now
        # store 的视图变化标记是 consume 语义(读后复位), 两条线各取一次即可完整覆盖。
        # 组键迁移待办(P7): 排空段已把它转成 full 理由(见 _drain_delta_locked), 但纯重键轮
        # 可能不伴随 view_changed(无视图字段变化) —— 理由在就必须触发一次重建, 否则孤儿行
        # 要等到下一次任意变更轮才被 full 清掉(静库下可无限期滞留)。
        if host.store.consume_view_changed() or self._pending_full_reasons:
            if keyed:
                self.mark_dirty()
            else:
                # R11: 视图须重建但行键不可推导的纯命令源 -> 本代标 full(保守正确优先)。
                # 否则落代为「空键集且 full=False」, 增量归约回空 delta, delta 客户端漏变更
                # (S3 观察缺口; S5 镜子 test_unkeyed_command_source_yields_full 钉住)。
                # store 驱动的常规轮不受影响: _apply 置 view_changed 必伴随三者之一的键。
                self.mark_dirty(full=True, reason="unkeyed_command_source")
        # HR 判定新鲜度: revision 与重建基线不等即置脏(基线在 _publish_locked 随重建前移,
        # 故只在 revision 真变的那一拍置一次, 无循环置脏 —— 收口靠基线前移, 发布侧**没有**
        # 内容指纹去重, 每次重建必增版本号必推 ver; 旧注释「按内容指纹去重」系与
        # hr/worker.py 的事件推送去重张冠李戴, 报告 26-10-07-0054 §06 指出, S10 修正)。
        # HR 派生字段无法归约为行级脏 -> 兼登记 full 降级理由(R11)。
        hr = getattr(host, "hr", None)
        if hr is not None and self._hr_rev_at_build != hr.revision:
            self.mark_dirty(full=True, reason="hr_revision")
        web_active = self.is_active()
        # 「上一版有没有人取走」门控(P-03 S10 裁决: 保留, 全口径见 pending_ver 字段声明):
        # 服务端节拍与客户端节拍各自独立定档, 大库下服务端生产的中间版本可能无人消费。
        # 让"生产"等一等"消费" —— 增量下跳拍的成本已降为一次键集追加(R4), 保留无害。
        unconsumed = self.pending_ver is not None
        if self.group_view_dirty and web_active and (force or not unconsumed):
            self.rebuild_views()

    def advance_error_reasons(self) -> None:
        """任务线: tracker 健康取数(错误原因 + 站点健康, 仅 Web 活跃时发 tracker 请求)"""
        if self.is_active():
            self._host.refresh_tracker_health()

    def advance_search_index(self) -> None:
        """任务线末尾: 搜索索引限流推进(仅 Web 活跃时), 关闭网页后不发多余的文件 API"""
        if self.search_index_dirty and self.is_active():
            self._host.build_search_index()

    # ------------------------------------------------------------------ 视图发布 / 读取

    def rebuild_views(self) -> None:
        """重建全部视图快照并自增版本号 —— **唯一**的重建入口(主循环侧)"""
        with self.view_lock:
            self._publish_locked()

    def _publish_locked(self) -> None:
        """重建四视图并发布 —— **调用方必须持有 view_lock**

        与 rebuild_views 分离, 使"判脏 → 重建 → 读取"能在**同一个临界区**内一次完成
        (见 ensure_view); 若拆成"加锁重建 / 释放 / 再加锁读", 中间仍可能被另一线程插入
        一次重建, 读到的四份视图依旧不属于同一轮。

        S6/S9b 分叉(plan 26-10-07-0414): 本代无 full 降级理由且有净键可归约 -> 局部重聚合
        (_publish_partial_locked, 未脏行对象引用原样保留; S9b 起 show 视图按脏剧键整行
        重建); full 理由/HR 波次/无键 -> 走原全量路径(四视图整体重建, 行为与 S6 之前逐字段
        一致)。应急回退(不 revert): 分叉判定恒为假(把下面的 if 条件整个换成 False)即回
        纯全量 —— 单行改动。

        发布口径(S10 回写, 与实现一致): 时间线只在本方法末尾落代(_fold_delta_pending_locked)
        —— 条目**只存脏行键不存值**(R1), 归约回放时行内容从当前已发布视图现取; 局部重聚合
        分支同样在本临界区内把四份数组**整体一次性替换**(「四视图同轮发布」硬约束不破,
        模块 docstring), 发布唯一入口就是本方法(主循环 / Web 线程 ensure_* 兜底共用同一把
        view_lock) —— 单一写线程假设不破, 无第二把锁(R12)。
        """
        host = self._host
        # ---- 本代键集定型(原属 _fold_delta_pending_locked 的前置段前移到构建前, S6) ----
        # 错误原因暂存并入: 分叉判定需要完整键集, 该源比 store 增量键集(排空在 flush_views
        # 开头)更及时, 并入点仍在 view_lock 临界区内(R12 不变)。
        self._merge_pending_error_hashes_locked()
        # 剧键迁移候选并入(plan S9b): S8 暂存的旧/新剧键统一作重建候选, 生命周期同上
        self._merge_pending_show_migrations_locked()
        # 交叉键集基线检查前移: 直接从 store 现算(与构建期 note_cross_keys 同源同值),
        # 增删即本代 full(R11) —— 局部重聚合无法修正未脏组行的 cross 标记, 必须先判定。
        cross_keys = host._cross_keys_snapshot()
        if self._cross_keys_prev is not None and cross_keys != self._cross_keys_prev:
            self._pending_full_reasons.add("cross_group")
        self.note_cross_keys(cross_keys)  # 局部路径不经 _build_group_view, 基线在此统一前移
        # R5 交叉抵消前移: 分叉判据是抵消后的净键集(fold 落代段重跑一遍, 幂等)
        _cancel_delta_buckets(self._delta_pending)
        upsert = self._delta_pending["upsert"]
        removed = self._delta_pending["removed"]
        # 未识别折叠面变化检测(plan S9b, R11): 增量协议没有未识别桶(S4 前端 delta 轮对
        # unrecognized「不动」, 只在 full 轮整表替换) -> 折叠成员增删不可归约为行级脏,
        # 本代标 full(保守正确优先)。判定用全量分类同款口径(_parse_show_member 解析+
        # 兑底): 「现分类未识别」≠「原居折叠区」即折叠面变化 —— 精确不放大, 静止未识别
        # 种子(如下载中的电影)速度抖动不触发。parse_release 按 name lru 缓存, 排空段已
        # 现算过同一批名字 -> 此处缓存命中, 增量成本可忽略(远廉于 S9b 前每拍全量重扫)。
        if upsert["torrent"] or removed["torrent"]:
            from ..core import tvshows as _tvshows

            _store = host.store
            index = self.search_index or {}
            old_unrec = set(self.shows_view["unrecognized"])
            unrec_changed = False
            for h in upsert["torrent"]:
                rec = _store.by_hash.get(h)
                if rec is None:
                    continue  # 已删 hash: 折叠面归 removed 分支判定
                _, parsed, _ = host._parse_show_member(rec, (index.get(h) or {}).get("files"))
                if (parsed.kind == _tvshows.KIND_UNKNOWN or not parsed.key) != (h in old_unrec):
                    unrec_changed = True  # 新进/离开折叠区(含改名与兑底归位两侧)
                    break
            if not unrec_changed:
                unrec_changed = any(h in old_unrec for h in removed["torrent"])
            if unrec_changed:
                self._pending_full_reasons.add("show_unrecognized")
        # HR 波次判定(flush_views 同款): ensure_state 触发的发布不经 flush 的判定点,
        # 局部重聚合只刷新脏行的 HR 派生字段, 波次未捕获会让未脏行的 HR 字段永久陈旧
        hr = getattr(host, "hr", None)
        hr_wave = hr is not None and hr.revision != self._hr_rev_at_build
        has_keys = bool(
            upsert["torrent"] or upsert["group"] or upsert["show"] or removed["torrent"] or removed["group"] or
            removed["show"]
        )
        partial = not self._pending_full_reasons and not hr_wave and has_keys
        if partial:
            self._publish_partial_locked(upsert, removed, cross_keys)
        else:
            old_show_keys = {r["key"] for r in self.shows_view["list"]}
            self.group_view = host._build_group_view()
            self.singles_view = host._build_singles_view()
            self.shows_view = host._build_shows_view()
            self.flat_view = host._build_flat_view()
            # 速度合计与四视图同一快照、同一临界区发布(状态栏据此与行数据同源同轮)
            self.speed_totals = host._build_speed_totals()
            # 剧键映射回填(plan S8): 重启后首个全量代全库登记(映射非空即跳过, 幂等)
            self._backfill_show_member_keys_locked(host.store)
            # show 桶时间线按现视图行止校准(plan S9b): 重建候选中已无剧行的键(迁移旧键
            # 成员迁空等)—— 原居旧视图的转 removed(客户端按它删行), 从未有过行的纯未识别
            # 键只撤候选不产生 removed 噪音; 免得后续归约对缺失行防御性 full
            gone = upsert["show"] - {r["key"] for r in self.shows_view["list"]}
            if gone:
                upsert["show"] -= gone
                removed["show"] |= gone & old_show_keys
        self.group_view_ver += 1
        self.group_view_dirty = False
        # 记下"这一版还没被任何 /api/state 请求取走" —— 主循环据此不再生产下一版(节拍对齐;
        # P-03 S10 裁决: 门控保留, 全口径见 pending_ver 字段声明处)
        self.pending_ver = self.group_view_ver
        # 增量时间线落代(plan S2): 跨拍累积的 _delta_pending 与本代 full 理由折叠成条目
        # 追加进时间线 —— 每次发布恰一条(R4 累积/R5 抵消/R11 降级/R12 临界区)
        self._fold_delta_pending_locked()
        # 事件驱动(P2): 新版本**主动推**信号(只推版本号, 绝不推数据 —— 3000 种子一轮
        # 全量要 63ms 序列化+网络+解析, 频繁推会把主线程打满)。前端据此触发一次 refresh。
        self.notify("ver", {"ver": self.group_view_ver})
        # 重建完成记 HR 判定新鲜度基线: 经 manager 现取 + 判空 —— 无 HR 运行时(测试桩/
        # 未装配)记 None, 比对端同样跳过, 不得在重建路径抛 AttributeError。
        # 全量路径基线恒前移(revision 已随全量重建落地, 不前移会让 flush 的波次判定
        # 每拍置脏 -> 无限 full 循环); 局部重聚合路径基线**只在 revision 仍等于旧基线时**
        # 前移(值不变即无操作): 若构建期间波次又动了(跨线程登记竞态), 保留旧基线让下一拍
        # flush 的波次判定补一次 full —— 否则基线前移会吞掉波次, 未脏行的 HR 字段永久陈旧。
        if hr is None:
            self._hr_rev_at_build = None
        elif not partial or hr.revision == self._hr_rev_at_build:
            self._hr_rev_at_build = hr.revision

    @staticmethod
    def _merge_rows(old_view: List[dict], key_field: str, rebuilt: dict, removed: set) -> List[dict]:
        """行合并骨架单点(issue 26-10-11-0309 认领修): _publish_partial_locked 四段
        (groups/singles/flat/shows)共用的「重建脏行/保留未脏/追加」骨架 —— 调用方只产
        rebuilt(键 -> 新行 dict)与 removed(键集), 归并口径只此一份, 改合并语义不再四处同步。

        契约(与四段各自内联时逐字一致):
        - removed 键的行直接从视图剔除(与全量构建不产已删行/空组行/已删剧行对齐);
        - rebuilt 命中的行换新对象(pop 顺带把替换过的键清出, 残余即新增行);
        - 未命中 rebuilt 的行**原样复用同一 dict** —— 引用稳定是前端 S7 按行对象身份
          WeakMap 记忆化的契约(脏行必然新对象, 未脏行一个字节都不动);
        - rebuilt 残余(新增行)追加在尾部(前端排序不依赖数组顺序)。

        key_field 与 rebuilt/removed 必须同一键空间(组段行键 = encode_group_key 后的字符串,
        调用方传 enc_rm 而非原始组键)。**核心热路径**: 逐行只做一次 dict 取键 + 集合成员判定,
        键名传字符串而非 key_of 可调用即为此——不为逐行多付一次函数调用。
        """
        out: List[dict] = []
        for old in old_view:
            k = old[key_field]
            if k in removed:
                continue
            out.append(rebuilt.pop(k) if k in rebuilt else old)
        out.extend(rebuilt.values())  # 新增行追加在尾部(前端排序不依赖数组顺序)
        return out

    def _publish_partial_locked(self, upsert: dict, removed: dict, cross_keys: set) -> None:
        """局部重聚合(plan S6/S9b): 仅对本代 upsert/removed 行键重跑构建 —— **调用方必须持有 view_lock**

        不变量(plan S6/S9b 核心):
        - 未脏行**对象引用原样保留**(同一 dict), 脏行必然新对象 —— 引用稳定只对未脏行承诺,
          前端 S7 按行对象身份的 WeakMap 记忆化依赖这一点;
        - 「四视图同轮发布」硬约束(模块 docstring)不破: 数组仍整体一次性替换, 行对象按
          未脏/脏区别复用/新建, 不在调用点分批建;
        - 四段(groups/singles/flat/shows)的合并骨架同一单点 `_merge_rows` —— 行对象复用/
          替换/剔除/追加的口径只此一份, 改合并语义(如 removed 处理)不再四处同步;
        - 组行内嵌 members 数组随组行整行走(P-02 一期口径); singles/flat 脏行按 hash 逐行
          重建(便宜); removed 键直接从视图剔除(与全量构建不产已删行/空组行对齐); 组行
          重建为空且旧行在视图 -> 组键转 removed 剔除(S6 补, 与 show 分支同口径), 旧行本
          不在视图则仅撤候选不产噪音;
        - show 行(S9b): 脏剧键经 _show_member_keys 反查成员集 -> 逐成员 _parse_show_member
          重解析 -> _build_show_row 重调出**整行** upsert(R8; 剧名频次/季级 gaps/集行状态
          归并全随整行重算, 正确性边界 2-4 落位); 重算成员为空(全删/迁移旧键清空)-> 行
          消失转 removed(对齐 _build_group_row 空组口径);
        - 脏行重算必须与全量重跑该行逐字段一致(S6/S9b 单测钉住; S5 镜子兜整体等价)。
        """
        host = self._host
        store = host.store
        from ..infra import utils as _utils

        # ---- groups: 脏组键整行重建(members 随行), 未脏组行复用, removed 组键剔除 ----
        rebuilt: dict = {}
        old_group_keys = {r["key"] for r in self.group_view}
        for k in list(upsert["group"]):  # 快照迭代: 重建为空的行止转换写回原集合(fold 读同一对象)
            members = store.groups.get(k) or ()
            recs = [store.by_hash[h] for h in members if h in store.by_hash]
            row = host._build_group_row(k, recs, cross_keys)
            enc = _utils.encode_group_key(k)
            if row is not None:
                rebuilt[enc] = row
            elif enc in old_group_keys:
                # 重建为空且旧行在视图(组条目未清理且成员全灭的桩态等)-> 旧行消失: 键转
                # removed 剔除, 与全量构建「不产空组行」产物对齐(show 分支同款口径, S6 补)。
                # !R5 抵消发生在 _publish_locked 键集定型段(本函数之前), fold 落代段对不
                # 交集幂等重跑 —— 此处 upsert -> removed 的挪动不会被回抵消。
                upsert["group"].discard(k)
                removed["group"].add(k)
            # else: 旧行本不在视图 -> 键**原样保留**在 upsert(S2 排空契约: 组键推导结果
            # 逐字进时间线, 桩态下首代即此形态); 行不存在由归约的缺行防御性 full 兜住,
            # 客户端不可能持有该行(行退出视图必有 removed 记录), 无残留面。
        enc_rm = {_utils.encode_group_key(k) for k in removed["group"]}  # 含上面转入的键
        # 合并骨架走四段共用单点(见 _merge_rows): 未脏组行同一 dict 原样保留
        group_view = self._merge_rows(self.group_view, "key", rebuilt, enc_rm)

        # ---- singles: torrent 桶脏行中未归组的按 hash 逐行重建(_member_view 口径) ----
        # 归组判定与 _build_singles_view 同款(groups 值并集, 不用 member_to_key —— 与
        # 全量构建的分类口径严格一致)
        grouped = set()
        for members in tuple(store.groups.values()):
            grouped.update(members)
        new_singles: dict = {}
        for h in upsert["torrent"]:
            if h not in grouped:
                rec = store.by_hash.get(h)
                if rec is not None:
                    new_singles[h] = host._member_view(rec)
        # 合并骨架走四段共用单点(见 _merge_rows): 新落地 singles(如成员脱离组)追加在尾部
        singles_view = self._merge_rows(self.singles_view, "hash", new_singles, removed["torrent"])

        # ---- flat: torrent 桶脏行按 hash 逐行重建(_seed_view 口径) ----
        new_flat: dict = {}
        for h in upsert["torrent"]:
            rec = store.by_hash.get(h)
            if rec is not None:
                new_flat[h] = host._seed_view(rec)
        # 合并骨架走四段共用单点(见 _merge_rows): 新增种子行追加在尾部(全量构建同按入库序在尾)
        flat_view = self._merge_rows(self.flat_view, "hash", new_flat, removed["torrent"])

        # ---- shows: 脏剧键整行重建(plan S9b), 未脏剧行复用, 全删剧转 removed 剔除 ----
        show_up = upsert["show"]
        show_rm = removed["show"]
        new_shows: dict = {}
        old_show_keys = {r["key"] for r in self.shows_view["list"]}
        if show_up:
            from ..core import tvshows

            index = self.search_index or {}
            by_hash = store.by_hash
            # 成员集反查(plan S9: 脏剧键经 _show_member_keys 取该剧成员 hash 集): 单次扫描
            # 只收脏剧键的成员 —— 映射规模 = 名称可解析的种子数, dict 扫描远廉于全库
            # parse_release(S9 的收益点)。映射口径比全量分类「宽一档」(S8: 名称可解析但
            # 暂居未识别区/待兑底的 hash 也登记) -> 成员逐个过 _parse_show_member 重分类,
            # 现分类未识别的(KIND_UNKNOWN, 如电影)剔除出剧行 —— 与全量分类产物对齐。
            want = set(show_up)
            members_by_key: dict = {}
            for h, k in self._show_member_keys.items():
                if k in want and h in by_hash:
                    members_by_key.setdefault(k, []).append(h)
            parse_member = host._parse_show_member
            build_row = host._build_show_row
            pending: List[str] = []
            for k in list(show_up):  # 快照迭代: 行止转换要写回原集合(fold 读同一对象)
                members = []
                for h in members_by_key.get(k) or ():
                    rec = by_hash.get(h)
                    if rec is None:  # 映射残值防御(理论不可达: 映射随删除清理)
                        continue
                    rec, parsed, is_pending = parse_member(rec, (index.get(h) or {}).get("files"))
                    if is_pending:
                        pending.append(h)  # 可兑底而索引未覆盖(全量同款: 未识别形态也计)
                    if parsed.kind == tvshows.KIND_UNKNOWN or not parsed.key:
                        continue  # 未识别折叠区不进剧行(全量分类同口径, 折叠面由检测器兜)
                    members.append((rec, parsed))
                row = build_row(k, members)
                if row is not None:
                    new_shows[k] = row
                elif k in old_show_keys:
                    # 剧已无(可分类)成员(全删/迁移旧键清空): 行消失 -> 转 removed
                    # (对齐 _build_group_row 空组口径; 改动进本代时间线条目)
                    show_up.discard(k)
                    show_rm.add(k)
                else:
                    # 从未有过剧行(纯未识别键等): 仅撤重建候选, 不产生 removed 噪音。
                    # !与 group 分支的「键保留 upsert」不同(S2 排空契约钉住): 剧键推导
                    # 源自 S8 过宽映射, 幻影键是常态形态(未识别种子每次抖动都推导出键),
                    # 留在 upsert 会令 show 视图归约频繁缺行防御 full —— 撤下才保增量率。
                    show_up.discard(k)
            # 文件兑底接线(与 _build_shows_view 同款): 脏成员中可被兑底而索引未覆盖 -> 登记
            # pending 并按需投递构建命令。False 归位转换刻意不在局部路径判定: 非脏成员的
            # pending 状态此处不可见, 误归位会丢「索引建成 -> 整季重解析」的重建触发
            # (归位拍由索引推进的 _trigger_shows_rebuild_if_pending 或下一个全量代兜住)
            pending = [h for h in pending if h not in index]
            if pending:
                self.mark_shows_pending(True)
                if self.search_index_dirty or self.search_index is None:
                    self.post_command("build_search_index")
        # 合并骨架走四段共用单点(见 _merge_rows): 新剧行追加在尾部(前端排序不依赖数组顺序)
        shows_list = self._merge_rows(self.shows_view["list"], "key", new_shows, show_rm)
        # 未识别折叠面原样保留: 折叠面变化已被 _publish_locked 的 show_unrecognized 检测
        # 拦为 full 代(R11, 协议无未识别桶), 走到这里的局部代折叠成员必与上一代一致
        shows_view = {"list": shows_list, "unrecognized": self.shows_view["unrecognized"]}

        # ---- 发布: 数组整体一次性替换(硬约束); speed_totals 无行键可归约, 仍现算 ----
        self.group_view = group_view
        self.singles_view = singles_view
        self.flat_view = flat_view
        self.shows_view = shows_view
        self.speed_totals = host._build_speed_totals()

    def ensure_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则返回当前引用

        与主循环惰性组装配合; 全程持锁保证"判脏 → 重建 → 读取"不被另一线程的重建插入。
        """
        with self.view_lock:
            if self.group_view_dirty:
                self._publish_locked()
            return self.group_view

    def ensure_state(self, rid: Optional[int], view: Optional[str] = None, delta: bool = False) -> dict:
        """WEB 线程调用: 带版本号的合并状态(前端按 rid 跳过整表替换与重渲染)

        rid 与服务端视图版本一致时**不回传任何数组**(响应体趋近于零)。status 体积极小,
        无关版本恒回传, 以保证连接状态 / 暂停状态 / 种子数变化能即时反映。

        **按视图回传**: view 指定当前视图时只回传该视图需要的数组(见 VIEW_ARRAYS), 响应体
        降到约 1/4。四视图仍共享同一版本号 —— 切视图时前端把 lastRid 置空强制取一次全量。

        **增量归约**(plan 26-10-07-0414 S3/S9b): 双重门控后才走归约分支 ——
        ①协商: 请求带 delta=1(路由层解析)才允许归约, 未带协商参数的请求**不进归约**,
        响应与历史版本逐字节等价(无 full 键)—— S3 与 S4 各自独立提交/回滚的兼容闸
        (P-01 定案: 未升级前端把增量载荷当全量吃会四数组 undefined 白屏);
        ②启用矩阵: view ∈ _DELTA_VIEWS(group/torrent/show); 缺省与未知值一律 full(无视图
        上下文可裁剪)。归约判定详见 _reduce_delta; 窗外/窗内含 full 代/防御检查不过时
        (R10)回落全量并标 full: true。
        """
        from .views import VIEW_ARRAYS

        with self.view_lock:
            if self.group_view_dirty:
                self._publish_locked()
            ver = self.group_view_ver
            # 本请求观察到了 ver ⇒ 这一版已被消费, 允许主循环生产下一版(节拍对齐的另一半)
            self.pending_ver = None
            updated = rid != ver
            state: dict = {"rid": ver, "updated": updated}
            if not updated:
                # 「零回传」: 版本一致只回 rid, 增量协商也不改变本分支(plan S3 保留 :828 语义)
                return state
            if delta and view in _DELTA_VIEWS:
                reduced = self._reduce_delta(rid, view)
                if not reduced.get("full"):
                    # 归约命中: rid(== ver)/full=False/delta/removed 四键并入(键名对齐 qB 命名法)
                    state.update(reduced)
                    return state
            # 全量分支(原路径): 协商客户端按协议标 full=true(不含 delta/removed 键, R10);
            # 未协商客户端**不加** full 键 —— 与 S3 之前的历史响应逐字节等价(独立提交安全)
            if delta:
                state["full"] = True
            arrays = {
                "groups": self.group_view,
                "singles": self.singles_view,
                "shows": self.shows_view,
                "torrents": self.flat_view,
            }
            keys = VIEW_ARRAYS.get(view) if view else None
            for k in keys or arrays:
                state[k] = arrays[k]
        return state

    def _reduce_delta(self, rid: int, view: str) -> dict:
        """把 (rid, ver] 窗口内的时间线归约为该视图的增量载荷(**调用方必须持有 view_lock**)

        判定顺序(plan 26-10-07-0414 S3, R3/R10; 协商与启用矩阵已在 ensure_state 门控):
          1. rid 缺省/0 / rid > ver(时钟倒挂) / rid < 时间线最旧代次(窗口滑出或尚未落代)
             -> 全量(R3: 数值区间比较, 不做 qB 式等值 ack/回绕);
          2. 窗口内任一代 full -> 全量(R11: full 代键集已清空, 键集链断裂);
          3. rid == ver(「零回传」)不进本函数(ensure_state 先行短路);
          4. 否则归约: upsert = 窗口内各代该视图 upsert 并集; removed = removed 并集 -
             最终 upsert(R5 跨代版: 后又改回的行让位, 回 upsert 不回 removed); 行内容现取
             自当前已发布视图(R1 时间线只存键不存值)。upsert 行必须存在于当前视图 ——
             不存在(跨代先增后删被 R5 抵消后的残留 upsert 等)即防御性转全量。

        返回 {"full": True} 或 {"rid": ver, "full": False, "delta": {...}, "removed": {...}}。
        delta/removed 的内层桶按该视图实际数组构成裁剪(与全量分支同款 VIEW_ARRAYS 裁剪),
        恒在、可为空。应急语义回退(不 revert): 本方法首行加 `return {"full": True}` 即回
        今天的行为(full 语义常驻)。
        """
        ver = self.group_view_ver
        # R3: rid 数值区间比较。缺省/0 与 >ver 都不可归约(后者含进程重启后旧客户端持未来 rid)
        if not rid or rid > ver:
            return {"full": True}
        timeline = self._delta_timeline
        # 时间线为空(尚未落代/重启归零)或最旧代次已越过 rid(环满滑出) -> 窗外全量(R10)
        if not timeline or rid < timeline[0]["ver"]:
            return {"full": True}
        window = [e for e in timeline if e["ver"] > rid]
        if any(e["full"] for e in window):
            return {"full": True}  # 窗内任一代 full: 键集链断裂, 只能全量(R10/R11)
        up_t: set = set()
        up_g: set = set()
        up_s: set = set()
        rm_t: set = set()
        rm_g: set = set()
        rm_s: set = set()
        for e in window:
            up_t |= e["upsert"]["torrent"]
            up_g |= e["upsert"]["group"]
            up_s |= e["upsert"]["show"]
            rm_t |= e["removed"]["torrent"]
            rm_g |= e["removed"]["group"]
            rm_s |= e["removed"]["show"]
        # R5 跨代版: removed 让位于后续 upsert(同键先删后改 = 行还在, 回 upsert)
        rm_t -= up_t
        rm_g -= up_g
        rm_s -= up_s
        from ..infra import utils as _utils
        from .views import VIEW_ARRAYS

        # 行内容现取自当前已发布视图(R1); upsert 行必须存在, 缺行即防御性转全量(见 docstring)。
        # 平铺视图含 store 全量 -> torrent 桶 upsert 的每一行都必须在 flat_view 里(三个视图通用)
        flat_rows = [r for r in self.flat_view if r["hash"] in up_t]
        if len(flat_rows) != len(up_t):
            return {"full": True}
        group_rows: list = []
        if up_g:
            enc_up = {_utils.encode_group_key(k) for k in up_g}
            group_rows = [r for r in self.group_view if r["key"] in enc_up]
            if len(group_rows) != len(up_g):
                return {"full": True}  # 组行已不在当前视图(跨代先改后解散的残留 upsert)
        show_rows: list = []
        if up_s:
            show_rows = [r for r in self.shows_view["list"] if r["key"] in up_s]
            if len(show_rows) != len(up_s):
                return {"full": True}  # 剧行已不在当前视图(全删转 removed 的跨代残留 upsert)
        # delta/removed 内层桶按该视图实际数组构成裁剪(与全量分支同款 VIEW_ARRAYS;
        # S9b 起 view=show 启用, delta.shows 回剧行/removed.shows 回剧键)
        keys = VIEW_ARRAYS.get(view) or ()
        delta: dict = {}
        removed: dict = {}
        if "torrents" in keys:
            delta["torrents"] = flat_rows
            removed["torrents"] = sorted(rm_t)
        if "groups" in keys:
            delta["groups"] = group_rows
            # 组行键回 encode 后的字符串(与视图行 r["key"] 同标识, 前端按它删行)
            removed["groups"] = sorted(_utils.encode_group_key(k) for k in rm_g)
        if "singles" in keys:
            # singles 行 = torrent 桶 upsert 中未归组的行(归组行的变更只落在 groups 桶);
            # 未归组行必须存在于当前 singles 视图, 缺行即防御性转全量
            member_to_key = self._host.store.member_to_key
            ungrouped = {h for h in up_t if h not in member_to_key}
            if ungrouped:
                singles_hashes = {r["hash"] for r in self.singles_view}
                if not ungrouped <= singles_hashes:
                    return {"full": True}
            delta["singles"] = [r for r in self.singles_view if r["hash"] in up_t]
            # removed.singles 回全部已删 hash(保守多删: 客户端删不存在的行是幂等 no-op,
            # 漏删才会留幽灵行 —— 已删行归没归过组在删除点之后已不可靠)
            removed["singles"] = sorted(rm_t)
        if "shows" in keys:
            delta["shows"] = show_rows
            # 剧行键 = parse_release 派生的剧键字符串(与视图行 r["key"] 同标识, 前端按它删行)
            removed["shows"] = sorted(rm_s)
        return {"rid": ver, "full": False, "delta": delta, "removed": removed}

    def mark_shows_pending(self, pending: bool) -> None:
        """追剧视图文件兑底标记: 索引推进后由构建器据此置脏重建

        True->False 归位拍登记 full 降级理由(plan S2 R11): 集行此前按名称解析展示,
        文件兑底后剧/季/集结构可能整体重组, 无法归约为行级脏 -> 本代 full。
        """
        was = self.shows_pending
        self.shows_pending = pending
        if was and not pending:
            self._pending_full_reasons.add("shows_pending")
