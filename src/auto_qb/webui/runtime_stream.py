"""WebUIRuntime 拆分: SSE 订阅 / 事件票据 / 错误历史环 / 活跃门控 / 服务器生命周期。

move-only 自 runtime.py 切出(计划 26-11-02-2342 §07 R5), 未改语义; 由根 runtime.py 组合进 WebUIRuntime。
"""
import logging
import queue
import secrets
from typing import TYPE_CHECKING, List, Optional, Tuple

from .runtime_common import (
    EVENT_QUEUE_MAX,
    EVENT_TICKET_MAX,
    EVENT_TICKET_TTL_S,
    WEB_VIEW_TTL,
    WebErrLogHandler,
    logger,
)

if TYPE_CHECKING:
    from .server.lifecycle import WebServerHandle


class StreamMixin:
    # ------------------------------------------------------------------ 事件推送

    def subscribe(self):
        """登记一个 SSE 订阅者, 返回它的事件队列(Web 线程调用)"""
        q = queue.Queue(maxsize=EVENT_QUEUE_MAX)
        with self._sub_lock:
            self._subscribers.append(q)
        # 订阅/退订都记一条 INFO: 排查"SSE 没连上 / 句柄堆叠"的第一手依据(重连时会成对出现)
        # DEBUG: 连接级事件, 重连时会成对刷屏。排查"没连上 / 句柄堆叠"时把日志级别调到 DEBUG 即可。
        logger.debug(f"WEB SSE 订阅 +1(当前 {len(self._subscribers)})")
        return q

    def unsubscribe(self, q) -> None:
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)
                logger.debug(f"WEB SSE 退订 -1(当前 {len(self._subscribers)})")

    def subscriber_count(self) -> int:
        with self._sub_lock:
            return len(self._subscribers)

    # ------------------------------------------------------------------ SSE 换票

    def issue_event_ticket(self) -> str:
        """签发一条 SSE 一次性票据(短 TTL); 未消费满额时回 ""(端点转 503, 前端轮询兜底)

        EventSource 发不出 Authorization 头, 前端以带鉴权的 POST /api/events/ticket 换票,
        再把票据放查询串开流 —— 查询串会进反代访问日志, 所以只放**单次消费的短命票据**,
        不再放长期访问密钥(26-10-02 加固, 取代旧 ?token= 兜底)。
        """
        now = self._clock.now()
        with self._event_tickets_lock:
            if len(self._event_tickets) >= EVENT_TICKET_MAX:
                # 先清过期再判满额; 仍满则拒签(都是没被消费的活票, 退避比挤掉别人合理)
                expired = [t for t, ts in self._event_tickets.items() if now - ts > EVENT_TICKET_TTL_S]
                for t in expired:
                    del self._event_tickets[t]
                if len(self._event_tickets) >= EVENT_TICKET_MAX:
                    return ""
            ticket = secrets.token_urlsafe(24)
            self._event_tickets[ticket] = now
            return ticket

    def consume_event_ticket(self, ticket: str) -> bool:
        """消费票据: **取即删**(单次有效), TTL 外按无效; 重放/过期/未知一律 False"""
        with self._event_tickets_lock:
            issued_at = self._event_tickets.pop(ticket, None)
        return issued_at is not None and (self._clock.now() - issued_at) <= EVENT_TICKET_TTL_S

    # ------------------------------------------------------------------ 错误历史(/api/errlog)

    def append_err(self, msg: str, level: str) -> None:
        """入环一条 WARNING+ 记录(日志线程经 WebErrLogHandler 调用): seq 自增, 环满挤最旧

        出锁后 notify("errlog", {seq, level, msg}) 只推小真值(计划 26-11-27-0530 S1-a/D3):
        发布点在日志线程是明示例外, 靠 notify 的 _sub_lock 复制订阅者 + put_nowait 非阻塞
        保证安全 —— 不引入线程交接队列, 不改 seq 重启归零语义, 不推全量环。
        """
        with self.err_log_lock:
            self.err_log_seq += 1
            seq = self.err_log_seq
            self.err_log_ring.append({"seq": seq, "ts": self._clock.now(), "level": level, "msg": msg})
        # 出锁再广播: 不在 err_log_lock 临界区内持锁调 notify(避免锁嵌套); 队列满/异常
        # 由 notify 既有 notify_dropped 计数承载, 慢消费者靠 60s GET 对账补, 不加静默计时器。
        self.notify("errlog", {"seq": seq, "level": level, "msg": msg})

    def err_log_since(self, after: int) -> Tuple[List[dict], int]:
        """只读增量(Web 线程): 回 (seq > after 的条目, 环当前最大 seq)

        after >= 当前 last 时回空列表 —— 含后端重启后客户端持旧游标的场景(seq 回零),
        重启判定在客户端(last < 游标即重启), 服务端只如实返回。
        """
        with self.err_log_lock:
            items = [e for e in self.err_log_ring if e["seq"] > after]
            return items, self.err_log_seq

    def attach_err_log_handler(self) -> None:
        """把 WebErrLogHandler 挂到 auto_qb logger(幂等: 已挂不重挂, 黄金法则 1)

        在 start_server() 里调用; 热重载重启服务器会再进 start_server, 而环与 handler
        都是进程级(不随服务器重启), 故以 _err_log_handler 引用闸防重复挂载。
        """
        if self._err_log_handler is not None:
            return
        self._err_log_handler = WebErrLogHandler(self)
        logging.getLogger("auto_qb").addHandler(self._err_log_handler)

    def notify(self, etype: str, payload: dict) -> int:
        """广播一条事件; 返回送达的订阅者数

        !必须**非阻塞**: 调用点可能在主循环线程(且 `_publish_locked` 还持有 view_lock)。
        这里只做 put_nowait, 慢消费者丢事件(它下一轮轮询会补上)。
        """
        ev = {"type": etype, "payload": payload, "ts": self._clock.now()}
        hit = 0
        with self._sub_lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(ev)
                hit += 1
            except queue.Full:
                self.notify_dropped += 1
            except Exception:
                self.notify_dropped += 1
        return hit

    # ---------------------------------------------------------- 流量步进事件(26-11-18-0037 阶段 2)

    def subscribe_traffic_stream(self, scope: str, group_key=None):
        """登记一个 per-scope 流量步进事件订阅者(Web 线程调用), 返回它的事件队列

        scope = "global" | "torrent:<hash>" | "group:<key>"(与 /api/traffic/qb 三 GET
        端点的作用域语法一致; torrent: 前缀与存储系列键前缀同构, batch 直取)。组 scope
        的成员集**不随订阅定死**: 解码键(group_key, store.groups 的 tuple 键)随订阅缓存,
        成员查表每帧现取 —— 与 GET 读侧「成员集 = 查询时刻 store.groups[指纹键]」同口径
        (组解散/重组后帧面自动跟随)。队列上限/心跳/退订纪律承袭 /api/events 订阅面。
        """
        q = queue.Queue(maxsize=EVENT_QUEUE_MAX)
        with self._traffic_sub_lock:
            self._traffic_subs.setdefault(scope, []).append(q)
            if group_key is not None:
                self._traffic_group_keys[scope] = group_key
        # DEBUG: 连接级事件(同 /api/events 订阅日志口径; 排查"没连上/句柄堆叠"调 DEBUG 看)
        logger.debug(f"WEB 流量步进订阅 +1 scope={scope}(当前 {self.traffic_stream_subscriber_count()})")
        return q

    def unsubscribe_traffic_stream(self, scope: str, q) -> None:
        """退订 per-scope 流量步进订阅(Web 线程调用): 队列摘除, 空 scope 连同其组键缓存
        一并清理(订阅表无死键 —— torrent scope 随浏览面无界增长的内存卫生)。"""
        with self._traffic_sub_lock:
            lst = self._traffic_subs.get(scope)
            if lst is not None and q in lst:
                lst.remove(q)
                if not lst:
                    self._traffic_subs.pop(scope, None)
                    self._traffic_group_keys.pop(scope, None)
                    # seq 死键随 scope 一并清理(评审 #4: torrent scope 随浏览面无界残留的
                    # 内存卫生)。seq 是每连接游标 —— 清零后新连接首帧 seq=1, 语义一致
                    #(消费端以首帧为基线, 断档检测在基线之后)。
                    self._traffic_seq.pop(scope, None)
                    logger.debug(f"WEB 流量步进订阅归零 scope={scope}")

    def traffic_stream_subscriber_count(self) -> int:
        """当前流量步进订阅队列总数(诊断面)"""
        with self._traffic_sub_lock:
            return sum(len(queues) for queues in self._traffic_subs.values())

    def traffic_stream_active(self) -> bool:
        """是否有任何流量步进订阅者(主循环线程调用): 采样模块据此把「差分点计算 + 派发」
        整段短路 —— 无人订阅时事件源零计算零派发(链游标照常推进, 订阅者中途加入首帧
        即真值, 见 traffic_sample_events._publish_traffic_events)。"""
        with self._traffic_sub_lock:
            return bool(self._traffic_subs)

    def publish_traffic_batch(self, batch: dict) -> int:
        """流量步进事件 per-scope 派发(主循环线程, 采样 handler 收尾调用); 返回送达队列数

        batch = {系列键: 差分点 {t, dl, up}}(采样模块本 tick 的新观测; 系列键与 torrent
        scope 语法同构)。扇出: global / torrent:<hash> 直取 batch(本 tick 无观测的 scope
        不派帧 —— 静默是停流信号, seq 不虚增); group:<key> 按 _group_merge_points 口径
        Σ 现查成员(成员此 tick 无点按 0 计不设观测, 全员无观测不派帧 —— R3: 载荷 =
        scope 聚合显示点, 每 tick 每 scope 恰 1 帧, 绝不 per-torrent 逐成员推)。

        seq 每 scope 单调递增: **派发即占号**(含队列满丢弃)—— 消费端按 seq 断档检测
        兜底重拉(计划 D9), 丢弃必须留下断档痕迹; 丢弃计数 traffic_notify_dropped 可观测
        (notify_dropped 同款)。非阻塞(put_nowait), 慢消费者丢事件不 backpressure 主循环
        (黄金法则 5)。帧对象逐队列新建(隔离面: 各订阅者各得一份拷贝, 点 dict 只读共享)。
        """
        hit = 0
        with self._traffic_sub_lock:
            if not self._traffic_subs:
                return 0
            groups = self._traffic_group_keys
            for scope, queues in self._traffic_subs.items():
                pts = self._traffic_scope_points(scope, batch, groups.get(scope))
                if pts is None:
                    continue  # 本 tick 该 scope 无真值点: 不派帧不占号(静默 = 停流信号)
                seq = self._traffic_seq.get(scope, 0) + 1
                self._traffic_seq[scope] = seq
                for q in queues:
                    try:
                        q.put_nowait({"seq": seq, "scope": scope, "points": list(pts)})
                        hit += 1
                    except queue.Full:
                        self.traffic_notify_dropped += 1
                    except Exception:
                        self.traffic_notify_dropped += 1
        return hit

    def _traffic_scope_points(self, scope: str, batch: dict, group_key) -> Optional[list]:
        """scope -> 本 tick 该 scope 的显示点列(无真值点回 None); group Σ 口径 =
        traffic_qb._group_merge_points 的单 tick 形态(成员此 t 无点按 0 计不设观测 /
        已知向求和未知向按 0 计 / 有观测而全成员该向皆未知 -> 该向 None / 全 None 真值点
        不设观测)。主循环线程调用(成员查表现取 store.groups, 与 GET 读侧同口径)。"""
        if scope == "global":
            p = batch.get("global")
            return None if p is None else [p]
        if scope.startswith("torrent:"):
            p = batch.get(scope)
            return None if p is None else [p]
        if scope.startswith("group:") and group_key is not None:
            members = getattr(getattr(self._host, "store", None), "groups", {}).get(group_key)
            if not members:
                return None  # 组解散/清空: 不派帧(静默 -> 前端 GET 重拉得空态, 同 §08)
            dl = up = 0
            dl_known = up_known = False
            has_obs = False
            t = None
            for h in tuple(members):
                p = batch.get("torrent:" + h)
                if p is None:
                    continue  # 该成员此 t 无点: 按 0 计, 不设观测(_group_merge_points 同判)
                if t is None:
                    t = p["t"]  # 同 tick 采样成员 t 恒同(单点 now), 取首个成员的真值 t
                if p["dl"] is None and p["up"] is None:
                    # 全 None 真值点不设观测 —— 事件 batch 无 totals 面(读侧
                    # _group_merge_points 的同位剔除判据含 totals 面): 单点语义同向
                    #(无观测), 已知差异由 GET 重拉承载
                    continue
                has_obs = True
                if p["dl"] is not None:
                    dl += p["dl"]
                    dl_known = True
                if p["up"] is not None:
                    up += p["up"]
                    up_known = True
            if not has_obs:
                return None
            return [{"t": t, "dl": dl if dl_known else None, "up": up if up_known else None}]
        return None  # 未知 scope 形态(端点已校验, 防御面): 不派帧

    # ------------------------------------------------------------------ 活跃门控

    def is_active(self) -> bool:
        """Web 客户端是否活跃(最近一次请求距今 < WEB_VIEW_TTL)

        「Web 未启用 / 网页已关闭」在本方法里自然恒为 False —— 主循环因此不需要任何
        `if web_enabled` 分支(空对象语义): 这与拆分前 `_web_last_seen = 0` 的判据逐字等价。
        """
        return (self._clock.now() - self.last_seen) < WEB_VIEW_TTL

    def touch(self) -> None:
        """WEB 请求心跳: 刷新 last_seen, 让主循环在活跃窗口内持续组装视图"""
        self.last_seen = self._clock.now()

    def mark_dirty(self, full: bool = False, reason: str = "") -> None:
        """核心域 → 表现层: 视图内容已变, 下次组装前必须重建

        覆盖四份视图(groups/singles/shows/flat): 它们共享同一个版本号, 置脏必须一致 ——
        曾因只在"分组启用"分支内置脏, 导致分组关闭时另三份视图被饿死(2026-09-18 事故)。

        full=True(plan S2 R11 降级源): 本次置脏**无法归约为行级脏**(如配置热重载改写的
        配置派生展示值) —— reason 登记进 _pending_full_reasons, 落代时该代标 full 且
        累积键集清空。缺省 False: store 增量等可归约源照常推导行键。
        """
        self.group_view_dirty = True
        if full:
            self._pending_full_reasons.add(reason or "unspecified")

    def mark_search_index_dirty(self) -> None:
        """核心域 → 表现层: 种子集变化, 搜索索引需重建"""
        self.search_index_dirty = True

    def note_search_data_changed(self) -> None:
        """核心域 → 搜索: 搜索相关数据已变(plan 26-11-03-0120 S1)

        只自增版本号, 供前端在下一轮 /api/state 发现结果过期后静默重查; 幂等语义由
        前端整集替换保证(重复自增最多多一次无变化的刷新)。只由主循环线程调用。
        """
        self.search_rev += 1

    def note_cross_keys(self, keys) -> None:
        """视图构建期回传跨组交叉键集(plan S2; _build_group_view 在 view_lock 临界区内调用)

        落代时与上一已发布代的键集比较, 增删即本代 full(R11): cross_group_conflict 标记
        派生自去重集合, 旧组键不归约。
        """
        self._cross_keys_seen = frozenset(keys)

    def note_error_reason_hashes(self, hashes) -> None:
        """行级展示派生字段变更的行级脏登记(plan S2 补, 源标签 "tracker_error_refresh")

        refresh_tracker_health 改写 tracker_error_msg / tracker_health_msg 的受影响行键在
        改写点可得 -> 按**行级归约**(R11 不降级): _publish_locked 落代前并入 torrent/group
        桶 upsert, delta 客户端本代即拿到这些行的新内容(error_reason 与 site_alert 两个
        消费方共用同一登记口 —— 函数名沿用历史名, 语义已扩为「行级展示派生字段变更」)。
        主循环线程调用(任务线预取先于视图发布)。
        """
        self._pending_error_hashes.update(hashes)

    def set_traffic_view(self, view: dict) -> None:
        """限速/流量只读快照发布口(plan kernel-module-refactor P3)

        **唯一写入方是 traffic_snapshot 模块**(计划 26-10-18-0813 A2/D10: 段级写全收在它的
        publish_source / publish_limit / publish_off 里, 别的模块一律不得直改快照)。
        主循环线程**整体替换**引用, Web 线程只读该引用 —— 无锁即可保证读到自洽的一份。
        """
        self.traffic_view = view

    # ------------------------------------------------------------------ 服务器生命周期(plan P2 门面转正)

    def ensure_token(self) -> str:
        """确定访问密钥(显式配置优先, 否则随机生成并持久化到 data_dir/web.token)并落 self.token

        自 P2 起令牌生命周期内聚本门面: start_web_server 不再直写令牌字段(plan
        §05「外围绕过边界直写内核私有面」清零)。!密钥内容不进日志(server/common 契约)。
        """
        from .server.common import ensure_web_token

        self.token = ensure_web_token(self._host)
        return self.token

    def start_server(self) -> None:
        """启动 WEB 服务器(独立线程): 先确定密钥再拉起 —— 启用时的启动与热重载重启共用

        WebUIModule 是宿主侧唯一调用方(run() 的 web 启动块已退役, plan P2)。
        错误历史 handler 挂接在启动前完成(幂等, 重启不重挂)。
        """
        from . import start_web_server

        self.ensure_token()
        self.attach_err_log_handler()
        # 显式 Optional 注解: WebUIRuntime.__init__ 侧初值 None, 两侧类型须一致(单一声明点)
        self.handle: "WebServerHandle | None" = start_web_server(self._host)

    def stop_server(self) -> None:
        """请求服务器退出(进程关停路径): 只置退出位**不等**线程

        uvicorn 每 0.1s 才读一次 should_exit, 服务线程是 daemon 随进程终灭 —— 与原 run()
        finally 的 `handle.stop()` 口径逐字一致; 只有热重载重启才需要 stop_web_server
        的"停旧并等线程退出"(见 server/lifecycle 的 10048 回归说明)。
        """
        if self.handle is not None:
            self.handle.stop()
