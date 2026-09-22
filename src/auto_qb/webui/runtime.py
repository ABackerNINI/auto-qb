"""WebUIRuntime: WEB UI 表现层运行时(**门面**)

把 WEB UI 的全部状态与节拍判据从 QbManager 里收出来, 使主循环不再持有、也不再判断任何
表现层细节 —— 主循环只见本对象暴露的少数语义方法(见下方「主循环接口」)。

为什么是门面而不是别的
----------------------
耦合的性质是「状态与门控」耦合: Web 侧从不通写路径, 只投递命令 + 只读快照, 边界对象早
就存在(命令队列 + 视图快照), 只是边界两侧的字段被平铺在同一个 self 上。故正解是把状态
与判据一起收走, 而不是引入事件总线(同步回调等价于直接调用, 只增加间接层)或 MVP 全套
(视图是 JSON 快照而非控件树, Presenter 的"更新控件"语义落空)。

依赖方向
--------
- **核心域 → 表现层**: 单向。主循环调本对象的门面方法; 核心域状态变化经 `mark_dirty()`
  / `mark_search_index_dirty()` 单向通知, 而不是直接写表现层的字段。
- **表现层 → 核心域**: 只有一条 —— 本对象通过 `self._host` 回调 QbManager 的写能力与
  视图**构建器**(`_cmd_*` 命令处理器 / `_build_*_view` / `store` / `api`)。构建器是纯读
  (读 store + config 产出 dict), 快照的装配、版本号与锁全部留在本对象。

线程契约(与拆分前**逐字一致**, 不得在后续改动中放松)
--------------------------------------------------
- 命令队列: Web 线程投递, 主循环线程消费 —— 写操作只在主循环线程(单一写者)。
- 视图快照: 主循环线程**发布**(持 `view_lock` 一次性替换四份视图 + 版本号),
  Web 线程**只读**;`ensure_*` 的「判脏 → 重建 → 取值」全程持锁, 保证四份视图同轮。
- `wake()` / 唤醒事件**不在这里**: 它是主循环的等待原语(托盘 UI 停止时也要用), 归核心域。

❗「四视图同轮发布」是硬约束: 四份视图共用 `group_view_ver` 一个版本号回传, 任何一份漏建
或跨轮混拼, 前端都会把陈旧数组当成新数据换上去(2026-09-18 实测事故)。新增视图只挂
`_publish_locked`, 不要在调用点各建一部分。
"""
import logging
import queue
import secrets
import threading
import time
from typing import List, Optional

from ..mixins.web_commands import (
    CMD_SLOW_MS,
    DEFERRED_RECEIPT_COMMANDS,
    REANNOUNCE_CONFIRM_TIMEOUT,
    TRUTH_PUSH_CAP_MS,
    RESYNC_COMMANDS,
    SELF_POSTED_COMMANDS,
    _timing,
)

logger = logging.getLogger(__name__)

# Web 客户端活跃窗口: 超时无请求则主循环跳过视图组装(惰性), 关闭网页后 CPU 回落
WEB_VIEW_TTL = 10.0
# 回执保留窗口与容量上限: 前端轮询完即弃, 兜底防无界增长
WEB_RESULT_TTL = 120.0
WEB_RESULT_MAX = 64

# 真值直查(torrents/info)的分批大小: hashes 是拼在 URL 里的,
# 448 个 40 位 hash ≈ 18KB, 超多数服务端/代理的 URL 长度限制(被截断或 414) ⇒ 分批查。
TRUTH_QUERY_CHUNK = 50

# 单个 SSE 订阅者的事件队列上限: 超过就丢(慢消费者靠轮询补), 防无界增长
EVENT_QUEUE_MAX = 200
# SSE 空闲心跳间隔(秒): 必须 **< WEB_VIEW_TTL**, 否则连着的客户端会被判成不活跃
# ⇒ 主循环停止组装视图 ⇒ 推送自己也没内容可发(自锁)。
SSE_KEEPALIVE_S = 5.0


class WebUIRuntime:
    """WEB UI 表现层状态 + 节拍判据 + 命令编排(主循环经门面方法调用, Web 线程经只读方法调用)"""
    def __init__(self, host):
        # host = QbManager。逆向引用只用于回调写能力与视图构建器, 不读它的表现层字段
        self._host = host
        # 控制命令队列: Web 线程投递, 主循环线程消费(写操作只在主循环线程)
        self.commands: "queue.Queue" = queue.Queue()
        # 写命令序号: 任何一条非自投递命令执行成功即自增 —— Web 线程的只读端点短缓存据此失效,
        # 避免改完立刻重取还拿到缓存里的旧值
        self.write_seq: int = 0
        # 命令执行结果回执(cmd_id -> {status, error, ts, wait_ms, exec_ms, truth})。
        # 主循环线程唯一写者, Web 线程经 /api/cmd/{id} 只读
        self.results: dict = {}
        # 强制汇报确认跟踪(cmd_id -> {deadline, items: {hash: {done, ok, err, baseline}}})
        self.reannounce_pending: dict = {}
        # 待推真值(cmd_id -> {cmd, args, ts}); 回执已即时发出, 这里只等真值落地再推事件
        self.truth_pending: dict = {}
        # ---- 视图快照(Web 线程只读, 发布时整体替换) ----
        self.group_view: List[dict] = []
        self.singles_view: List[dict] = []  # 未归组单种子视图
        self.flat_view: List[dict] = []  # 种子平铺视图(种子页数据源)
        self.shows_view: dict = {"list": [], "unrecognized": []}  # 追剧视图(剧→季→集)
        # 追剧视图文件兑底待解析标记: 名称无标记的种子需等搜索索引提供文件列表
        self.shows_pending: bool = False
        # 视图版本号(等价 qB 的 rid): 每次发布自增, Web 端按版本跳过整表替换。
        # 以进程启动时间播种 —— 进程重启后版本号不会回落到旧客户端已持有的值
        self.group_view_ver: int = int(time.time())
        # 快照是否过期(全部 Web 视图共享: 主循环据此惰性重建)
        self.group_view_dirty: bool = True
        # 最近一次 Web 请求时间(活跃门控的心跳)
        self.last_seen: float = 0.0
        # 已发布但**还没被任何 /api/state 请求取走**的版本号(None = 没有"欠着"的版本)。
        # 用于把"服务端重建节拍"对齐到"客户端实际取数据的节拍": 上一版没人看就不生产下一版
        self.pending_ver: Optional[int] = None
        # 发布锁: 四份视图 + 版本号必须**同一临界区内**发布
        self.view_lock = threading.Lock()
        # 搜索索引(hash -> {name, files[文件名]}): 主循环按需构建并原子替换, Web 线程只读
        self.search_index: Optional[dict] = None
        self.search_index_dirty: bool = True
        # 访问密钥 / 服务器句柄(启用时确定)
        self.token: str = ""
        self.handle = None
        # 限速/流量只读快照(限速曲线任务整体替换, Web 线程只读); 未启用曲线时 state="disabled"
        self.traffic_view: dict = {"state": "disabled", "periods": [], "limit": {}}
        # 全量种子上传/下载速度合计(状态栏常显统计): 与四视图**同一临界区**发布, 随 /api/state
        # 的 status 恒回传 —— 不参与 VIEW_ARRAYS 视图分片、不受 rid 门控(状态栏是跨视图的常驻
        # 显示, 不能依赖任何一个"可能被裁掉"的数组, 见 issue 26-09-20-1646)
        self.speed_totals: dict = {"dlspeed": 0, "upspeed": 0}
        # ---- 事件推送(SSE /api/events) ----
        # 每个订阅者一个**有界**队列: 主循环侧只 put_nowait, 队列满就丢(推送是加速手段,
        # 丢了只是退化成轮询, 不是错误)。❗主循环**绝不直接写 socket** —— 本项目头号教训:
        # 搜索索引单次 500 条文件 API 曾占满主循环, 导致命令排队数秒。
        self._subscribers: list = []
        self._sub_lock = threading.Lock()
        self.notify_dropped: int = 0

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

    def notify(self, etype: str, payload: dict) -> int:
        """广播一条事件; 返回送达的订阅者数

        ❗必须**非阻塞**: 调用点可能在主循环线程(且 `_publish_locked` 还持有 view_lock)。
        这里只做 put_nowait, 慢消费者丢事件(它下一轮轮询会补上)。
        """
        ev = {"type": etype, "payload": payload, "ts": time.time()}
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

    # ------------------------------------------------------------------ 活跃门控

    def is_active(self) -> bool:
        """Web 客户端是否活跃(最近一次请求距今 < WEB_VIEW_TTL)

        「Web 未启用 / 网页已关闭」在本方法里自然恒为 False —— 主循环因此不需要任何
        `if web_enabled` 分支(空对象语义): 这与拆分前 `_web_last_seen = 0` 的判据逐字等价。
        """
        return (time.time() - self.last_seen) < WEB_VIEW_TTL

    def touch(self) -> None:
        """WEB 请求心跳: 刷新 last_seen, 让主循环在活跃窗口内持续组装视图"""
        self.last_seen = time.time()

    def mark_dirty(self) -> None:
        """核心域 → 表现层: 视图内容已变, 下次组装前必须重建

        覆盖四份视图(groups/singles/shows/flat): 它们共享同一个版本号, 置脏必须一致 ——
        曾因只在"分组启用"分支内置脏, 导致分组关闭时另三份视图被饿死(2026-09-18 事故)。
        """
        self.group_view_dirty = True

    def mark_search_index_dirty(self) -> None:
        """核心域 → 表现层: 种子集变化, 搜索索引需重建"""
        self.search_index_dirty = True

    # ------------------------------------------------------------------ 主循环接口

    def consume_commands(self) -> bool:
        """消费 WEB UI 控制命令; 返回本批是否含"改了 qB 种子状态"的命令(主循环据此补刷新)

        命令带 cmd_id: 执行完立即写回执(见 results), 供前端 /api/cmd/{id} 轮询。
        例外: reannounce 只发指令并登记确认跟踪(reannounce_pending), 回执由 check_pending()
        在 tracker 确认后写入 —— "已发送"不等于"汇报成功"; bulk/add 的回执由 handler 聚合写。

        ❗写序号必须在写回执**之前**自增: 前端拿到回执会立刻重取只读端点(如改完分类重取
        /api/categories), 顺序反过来会让那一瞬的读命中旧写序号对应的缓存键。
        """
        host = self._host
        handlers = host._web_command_handlers()
        changed = False
        try:
            while True:
                cmd, payload = self.commands.get_nowait()
                cmd_id = str(payload.get("cmd_id") or "")
                # 下划线前缀的键是埋点/元数据, 不传给 handler(否则被当命令参数报 TypeError)
                args = {k: v for k, v in payload.items() if k != "cmd_id" and not k.startswith("_")}
                queued_ts = payload.get("_queued_ts")
                start_ts = time.time()  # 出队即开始, 用于拆 wait_ms / exec_ms
                try:
                    deferred = cmd in DEFERRED_RECEIPT_COMMANDS
                    if cmd_id and deferred:
                        handlers[cmd](cmd_id=cmd_id, **args)
                    else:
                        handlers[cmd](**args)
                    # 自投递命令不计数: 它只是内部索引推进, 且频次高, 计进去会让缓存在
                    # 建索引期间完全失效
                    if cmd not in SELF_POSTED_COMMANDS:
                        self.write_seq += 1
                    timing = _timing(queued_ts, start_ts)
                    if cmd_id and not deferred:
                        if cmd in RESYNC_COMMANDS:
                            # 改种子状态的命令: 回执**推迟到补刷新之后**再写(见 flush_receipts)。
                            # 原写法在这里就写 ok, 而补刷新还在后面才跑 ⇒ 前端"拿到回执就立刻
                            # refresh"取到的必然是补刷新之前的旧快照(rid 未变), 第一次拉取 100%
                            # 扑空。推迟后第一次拉取即可命中。
                            self.defer_receipt(cmd_id, cmd, args, timing)
                        else:
                            self.set_result(cmd_id, "ok", timing=timing)
                    if cmd_id:
                        self._log_cmd_timing(cmd, timing)
                    if cmd in RESYNC_COMMANDS:
                        changed = True
                except KeyError as e:
                    logger.warning(f"WEB UI 未知命令: {e}")
                    if cmd_id:
                        self.set_result(cmd_id, "error", f"未知命令: {e}", _timing(queued_ts, start_ts))
                except Exception as e:
                    logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
                    if cmd_id:
                        self.set_result(cmd_id, "error", str(e), _timing(queued_ts, start_ts))
        except queue.Empty:
            pass
        return changed

    def check_pending(self) -> None:
        """每 tick 检查在途的强制汇报确认; 某 cmd_id 全部种子出结论后聚合写回执"""
        host = self._host
        if not self.reannounce_pending:
            return
        now = time.time()
        finished = []
        for cmd_id, entry in self.reannounce_pending.items():
            for h, it in entry["items"].items():
                if it["done"]:
                    continue
                if now >= entry["deadline"]:
                    it["done"], it["ok"] = True, False
                    it["err"] = f"汇报确认超时({REANNOUNCE_CONFIRM_TIMEOUT:.0f}s 内未确认到 tracker 响应)"
                    continue
                if host.client is None:
                    continue  # qB 断连: 等恢复继续确认, 或按超时判失败
                try:
                    trackers = host.client.torrents_trackers(h) or []
                    r = host._confirm_reannounce_result(trackers, it["baseline"])
                except Exception as e:
                    it["done"], it["ok"], it["err"] = True, False, f"读取 tracker 状态失败: {e}"
                    continue
                if r is True:
                    it["done"], it["ok"] = True, True
                elif r is False:
                    it["done"], it["ok"], it["err"] = True, False, "tracker 未接受汇报(not working)"
            if all(it["done"] for it in entry["items"].values()):
                finished.append(cmd_id)
        for cmd_id in finished:
            entry = self.reannounce_pending.pop(cmd_id)
            items = list(entry["items"].values())
            fails = [it for it in items if not it["ok"]]
            if not fails:
                self.set_result(cmd_id, "ok")
                logger.info(f"WEB UI | 强制汇报确认成功({len(items)}个种子)")
            else:
                msg = f"{len(fails)}/{len(items)} 个种子汇报确认失败: " + "; ".join(it["err"] for it in fails[:3])
                self.set_result(cmd_id, "error", msg)
                logger.warning(f"WEB UI | {msg}")

    def flush_views(self, force: bool = False) -> None:
        """消费视图脏标记并在 Web 活跃时惰性重建(同步线 / 任务线各自调用一次)

        `force=True` 表示"本轮有命令改了种子状态", 必须**绕过**下面的"已取走"门控 ——
        用户操作后真值要在几十毫秒内进快照, 不能因为上一版还没被取走就跳过。
        """
        host = self._host
        # store 的视图变化标记是 consume 语义(读后复位), 两条线各取一次即可完整覆盖
        if host.store.consume_view_changed():
            self.mark_dirty()
        web_active = self.is_active()
        # 「上一版有没有人取走」门控: 服务端节拍与客户端节拍各自独立定档, 大库下服务端
        # 生产的中间版本可能无人消费。让"生产"等一等"消费"。
        unconsumed = self.pending_ver is not None
        if self.group_view_dirty and web_active and (force or not unconsumed):
            self.rebuild_views()

    def advance_error_reasons(self) -> None:
        """任务线: 错误状态种子的具体原因预取(仅 Web 活跃时发 tracker 请求)"""
        if self.is_active():
            self._host.refresh_error_reasons()

    def advance_search_index(self) -> None:
        """任务线末尾: 搜索索引限流推进(仅 Web 活跃时), 关闭网页后不发多余的文件 API"""
        if self.search_index_dirty and self.is_active():
            self._host._build_search_index()

    def flush_truths(self) -> None:
        """直查真值, 落地了就推 `truth` 事件; 未落地继续等(上限 TRUTH_PUSH_CAP_MS)

        ❗**必须无条件调用**(哪怕本轮没跑补刷新): 漏调会让前端一直挂着乐观值。
        ❗超时**不推**: 推一个未落地的真值 = 让前端采纳命令前的旧值 ⇒ 弹回。
          那种情况交给前端超时回滚, 且必须有明确 toast(不能静默)。
        """
        if not self.truth_pending:
            return
        pending, self.truth_pending = self.truth_pending, {}
        now = time.time()
        n_push = 0
        n_wait = 0
        for cmd_id, item in pending.items():
            truth = self._affected_truth(item["cmd"], item["args"])
            landed = self._truth_landed(item["cmd"], item["args"], truth)
            if not landed and (now - item.get("ts", now)) * 1000.0 < TRUTH_PUSH_CAP_MS:
                self.truth_pending[cmd_id] = item
                n_wait += 1
                continue
            if not landed:
                logger.warning(f"[cmd] 真值超时(>{TRUTH_PUSH_CAP_MS:.0f}ms)未落地, 放弃推送: {cmd_id}")
                continue
            self.notify("truth", {"cmd_id": cmd_id, "hashes": sorted(truth or {}), "truth": truth})
            n_push += 1
        if n_push:
            # DEBUG: 一次命令一条, 常态下不必占 INFO —— 真值是否到达可从前端
            # [perf] 的 `via=push` 看出, 排查埋点归前端一处, 后端不重复刷。
            logger.debug(f"[cmd] 真值已推 {n_push} 条")
        elif n_wait:
            # 等待轮次只打 DEBUG: 真机实测一次命令要等 7~8 轮(每轮 ~200ms), 全打 INFO 会把日志
            # 刷满 —— 而这段等待现在**完全不影响观感**(压暗早已结束), 不值得占 INFO。
            logger.debug(f"[cmd] 真值未落地, 继续等 {n_wait} 条(上限 {TRUTH_PUSH_CAP_MS:.0f}ms)")

    def resync_elapsed_ms(self, t0: float) -> None:
        """命令后补刷新耗时落日志(计时口径见 qbmanager.run 的"命令驱动那一轮")

        与 set_result 里的 wait_ms / exec_ms 合起来是"点下去到真值进快照"的三段归因。
        """
        ms = round((time.time() - t0) * 1000, 1)
        # ❗正常耗时只打 DEBUG: 每条命令都会跑一次补刷新, 全打 INFO 会把日志刷满 ——
        #   而现在真值走直查、撤下也不再等它, 它已经不在用户可见的延迟链路上。
        #   只有**异常慢**才升到 WARNING(那时它确实会拖慢下一次视图数据的新鲜度)。
        if ms > CMD_SLOW_MS:
            logger.warning(f"[cmd] 命令后补刷新 {ms}ms —— 真值要这一轮跑完才进快照,"
                           " 前端的乐观撤下再快也得等它(大库 /sync/maindata 往返 + 四视图重建)")
        else:
            logger.debug(f"[cmd] 命令后补刷新 {ms}ms")

    # ------------------------------------------------------------------ 回执

    def set_result(
        self,
        cmd_id: str,
        status: str,
        error: str = "",
        timing: Optional[dict] = None,
        truth: Optional[dict] = None,
    ) -> None:
        """写入命令执行结果回执(主循环线程唯一写者); 顺手清理过期回执防无限增长

        timing: 埋点(wait_ms 排队等主循环 / exec_ms 执行耗时), 由 /api/cmd/{id} 一并返回。
        truth: 受影响种子的当前真值, 前端拿到即可撤下乐观态, 省掉一次全量 refresh。
        """
        now = time.time()
        if len(self.results) > WEB_RESULT_MAX:
            self.results = {k: v for k, v in self.results.items() if now - v.get("ts", 0) < WEB_RESULT_TTL}
        rec = {"status": status, "error": error, "ts": now}
        if timing:
            rec.update(timing)
        if truth:
            rec["truth"] = truth
        self.results[cmd_id] = rec
        # 事件驱动(P2): 回执**主动推**给前端, 前端不必再轮询 /api/cmd/{id}。
        # 轮询退避 0→150→300→500ms 的粒度是撤下延迟的一部分, 推送把它压到 ~1ms。
        # ❗必须带上 cmd_id —— 前端按它匹配自己那条命令(多个命令可能同时在途)。
        self.notify("cmd", {**rec, "cmd_id": cmd_id})

    def defer_receipt(self, cmd_id: str, cmd: str, args: dict, timing: dict) -> None:
        """回执**立即**写 + 真值登记为"稍后推"(2026-09-20 D2 定案)

        ❗为什么不再"扣住回执等真值": 真机实测 qB 把状态翻过来要 **1258ms**, 而命令执行
          只要 2.7ms —— 扣着回执等, 撤下就被 qB 钉死在 1.25s+(实测撤下 2947ms)。
          拆成两步:
            ① 回执立刻发(只表示"命令已执行"), 前端据此**结束压暗** ⇒ 撤下降到 10~20ms;
            ② 真值继续直查, 落地了再推 `truth` 事件, 前端据此结束"值覆盖"。
        ❗回执**不带 truth**: 带上未落地的真值 = 让前端采纳命令**前**的旧值 ⇒ 弹回
          (4df80dc 那条红线)。真值只走 `truth` 事件, 且只有落地了才推。
        """
        self.set_result(cmd_id, "ok", timing=timing)
        self.truth_pending[cmd_id] = {
            "cmd": cmd,
            "args": dict(args or {}),
            "ts": time.time(),
        }

    @staticmethod
    def _truth_landed(cmd: str, args: dict, truth: Optional[dict]) -> bool:
        """真值是否已**落地**(命令的效果是否已经在种子状态上体现)

        ❗与"命令执行成功"是两回事: `torrents/resume` 返回 200 时 qB 可能还没翻状态,
        补刷新读到的还是命令**前**的 paused。此时若把回执发出去, 回执里的真值就是旧值 ——
        前端一旦采纳就会把行改回「已暂停」, 用户看到"乐观做种 → 弹回暂停 → 2 秒后变做种"
        (2026-09-20 真机回归)。故这里在服务端**等真值落地**再发回执, 前端拿到的必然是自洽的。
        """
        if not truth:
            return True  # 取不到真值就不等(退回前端拉一次的老路径)
        act = args.get("action") if cmd == "bulk_torrents" else cmd.split("_", 1)[0]
        for v in truth.values():
            kind = (v or {}).get("kind")
            if act == "pause" and kind != "paused":
                return False
            if act == "resume" and kind == "paused":
                return False
        return True

    def _affected_hashes(self, cmd: str, args: dict) -> List[str]:
        """命令影响了哪些种子(用于回执带真值); 取不到就返回空 —— 只影响能否省一次 refresh"""
        host = self._host
        try:
            if cmd.endswith("_torrent"):
                h = (args or {}).get("hash")
                return [h] if h else []
            if cmd.endswith("_group"):
                return list(host.store.groups.get((args or {}).get("key") or (), []) or [])
            if cmd == "bulk_torrents":
                out = list((args or {}).get("hashes") or [])
                for k in (args or {}).get("keys") or []:
                    out.extend(host.store.groups.get(k, []) or [])
                return list(dict.fromkeys(out))
        except Exception:  # 桩/异常配置下取不到就退化为"不写真值", 前端照旧拉一次
            return []
        return []

    def _affected_truth(self, cmd: str, args: dict) -> Optional[dict]:
        """受影响种子的**当前真值**({hash: {"kind": ...}}) —— **直查 qB, 不读同步快照**

        ❗为什么必须直查(2026-09-20 定案):
          `store.by_hash` 来自 `/sync/maindata` **同步快照**, 按 qB 的节奏刷新 —— 真机实测命令后
          要等 6 轮 / **1362ms** 才在上面看到新状态(而命令本身只要 8.4ms), 这个数与
          `sync_interval = 1.5 # 与 qB 自带 WebUI(1500ms)同量级` 几乎重合 ⇒ 滞后来自快照刷新节奏。
          拿快照当"命令后的真值"就会读到命令**前**的旧值 —— 这正是"撤下要等 3s"的根源。
          改走 `torrents/info` 直查, 拿到的是 qB 的**实时**状态。

        ❗取不到就返回 **None（不回落快照）**: 回落会把"读不到"伪装成"读到了旧值",
          而旧值正是要消灭的东西。没有真值时前端保持乐观/等待, 语义更干净。
        """
        hashes = self._affected_hashes(cmd, args)
        if not hashes:
            return None
        want = set(hashes)
        truth: dict = {}
        try:
            # 分批: hashes 拼在 URL 里, 448 个 hash ≈ 18KB 会超长度限制(被截断/414)
            for i in range(0, len(hashes), TRUTH_QUERY_CHUNK):
                chunk = hashes[i:i + TRUTH_QUERY_CHUNK]
                for t in self._host.api.torrents_info(torrent_hashes=chunk) or []:
                    # 真机是 TorrentDictionary(有 .get/.hash); 测试桩 FakeTorrent 只有属性
                    h = getattr(t, "hash", None) or (t.get("hash") if hasattr(t, "get") else None)
                    if h in want:
                        truth[h] = {"kind": self._host._state_kind(t)}
        except Exception as e:
            logger.warning(f"[cmd] 真值直查失败(不回落同步快照): {e}")
            return None
        return truth or None

    def _log_cmd_timing(self, cmd: str, timing: Optional[dict]) -> None:
        """命令耗时落日志 —— 排查"点了要等几秒"的**主出口**(不依赖浏览器控制台)

        三段的读法(配合 resync_elapsed_ms 的补刷新那段):
          排队 wait_ms 大 = 主循环正被长任务占住(搜索索引 500 条文件 API / 任务批 / tracker 预取);
          执行 exec_ms 大 = qB API 本身慢(库大 / qB 忙 / 网络);
          补刷新大       = 命令后的强制同步慢(大库 /sync/maindata 往返)。
        """
        if not timing:
            return
        w = timing.get("wait_ms")
        e = timing.get("exec_ms")
        msg = f"[cmd] {cmd}: 排队 {w}ms / 执行 {e}ms"
        if cmd in SELF_POSTED_COMMANDS:
            logger.debug(msg + "(自投递, 不唤醒主循环)")  # 自投递频次高, 不进常规日志
            return
        if (w or 0) > CMD_SLOW_MS or (e or 0) > CMD_SLOW_MS:
            logger.warning(
                msg + f" —— 超过 {CMD_SLOW_MS:.0f}ms:"
                " 排队大=主循环被长任务占住(搜索索引/任务批/tracker 预取),"
                " 执行大=qB API 慢; 前端再快也盖不住这一段(乐观 UI 只遮住回执之前的一半)"
            )
        else:
            # ❗正常耗时只打 DEBUG: 每条命令都打, 全进 INFO 会把日志刷满 ——
            #   常态下的耗时看前端 `[perf]` 那一行即可(五段更全), 异常慢才由上面升 WARNING。
            logger.debug(msg)

    # ------------------------------------------------------------------ 命令投递(Web 线程)

    def post_command(self, cmd: str, payload: Optional[dict] = None) -> dict:
        """投递控制命令并生成回执 ID: 前端据 cmd_id 轮询 /api/cmd/{id} 获取执行结果

        自投递命令(SELF_POSTED_COMMANDS)**不唤醒主循环**且不带 cmd_id —— 否则会形成
        「唤醒 → drain → 索引仍脏 → 再投递」的自激循环, 打满 CPU 并冲垮 qB。
        """
        body = dict(payload or {})
        if cmd in SELF_POSTED_COMMANDS:
            # 自投递: 不入回执(没有 cmd_id), 也不带埋点 —— 它根本没有回执消费者
            self.commands.put((cmd, body))
            return {"queued": True, "cmd_id": ""}
        body["_queued_ts"] = time.time()  # 埋点: 投递时刻, 回执据此拆出排队耗时
        cmd_id = secrets.token_hex(8)
        body["cmd_id"] = cmd_id
        self.commands.put((cmd, body))
        self._host.wake()  # 唤醒主循环立即消费(命令延迟从 0~main_tick 降到近乎 0)
        return {"queued": True, "cmd_id": cmd_id}

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
        """
        host = self._host
        self.group_view = host._build_group_view()
        self.singles_view = host._build_singles_view()
        self.shows_view = host._build_shows_view()
        self.flat_view = host._build_flat_view()
        # 速度合计与四视图同一快照、同一临界区发布(状态栏据此与行数据同源同轮)
        self.speed_totals = host._build_speed_totals()
        self.group_view_ver += 1
        self.group_view_dirty = False
        # 记下"这一版还没被任何 /api/state 请求取走" —— 主循环据此不再生产下一版(节拍对齐)
        self.pending_ver = self.group_view_ver
        # 事件驱动(P2): 新版本**主动推**信号(只推版本号, 绝不推数据 —— 3000 种子一轮
        # 全量要 63ms 序列化+网络+解析, 频繁推会把主线程打满)。前端据此触发一次 refresh。
        self.notify("ver", {"ver": self.group_view_ver})

    def ensure_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则返回当前引用

        与主循环惰性组装配合; 全程持锁保证"判脏 → 重建 → 读取"不被另一线程的重建插入。
        """
        with self.view_lock:
            if self.group_view_dirty:
                self._publish_locked()
            return self.group_view

    def ensure_state(self, rid: Optional[int], view: Optional[str] = None) -> dict:
        """WEB 线程调用: 带版本号的合并状态(前端按 rid 跳过整表替换与重渲染)

        rid 与服务端视图版本一致时**不回传任何数组**(响应体趋近于零)。status 体积极小,
        无关版本恒回传, 以保证连接状态 / 暂停状态 / 种子数变化能即时反映。

        **按视图回传**: view 指定当前视图时只回传该视图需要的数组(见 VIEW_ARRAYS), 响应体
        降到约 1/4。四视图仍共享同一版本号 —— 切视图时前端把 lastRid 置空强制取一次全量。
        """
        from ..mixins.web_view import VIEW_ARRAYS

        with self.view_lock:
            if self.group_view_dirty:
                self._publish_locked()
            ver = self.group_view_ver
            # 本请求观察到了 ver ⇒ 这一版已被消费, 允许主循环生产下一版(节拍对齐的另一半)
            self.pending_ver = None
            updated = rid != ver
            state: dict = {"rid": ver, "updated": updated}
            if updated:
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

    def mark_shows_pending(self, pending: bool) -> None:
        """追剧视图文件兑底标记: 索引推进后由构建器据此置脏重建"""
        self.shows_pending = pending
