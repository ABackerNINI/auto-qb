"""WebCommandsMixin: WEB UI 控制命令消费与回执(主循环线程侧执行体)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一)。Web 线程只向 self.web_commands
投递命令并只读 self._web_results 回执; 本 mixin 全部方法都在主循环线程执行
(_tick 经 _drain_web_commands 消费命令, _check_reannounce_pending 每 tick 推进汇报确认)。

依赖的宿主属性(由 QbManager.__init__ 初始化):
- self.web_commands / self._web_results / self._reannounce_pending
- self.api(QbApi) / self.store / self.client
- self.apply_new_config(配置热重载, 定义于 QbManager 核心)
"""
import logging
import queue
import time
from typing import List, Optional

from ..config import Config

logger = logging.getLogger(__name__)

# 强制汇报的 tracker 确认窗口: reannounce 后 qB 立即重发 announce, 私站响应通常 1~10s;
# 留足慢站点余量取 30s(主循环 main_tick=2s -> 约 15 轮确认机会), 超时仍未确认即判失败。
REANNOUNCE_CONFIRM_TIMEOUT = 30.0

# **自投递**命令: 由 Web 侧在自己处理过程中 put 回队列(不是用户操作), 投递后**不唤醒**主循环。
# 目前只有 build_search_index —— web_view 在搜索索引脏时自投递(web_view.py:513/:699)。
# ❗若允许它唤醒会形成自激循环: 唤醒 -> drain(单轮最多 SEARCH_INDEX_BUILD_BUDGET=500 条文件 API)
# -> 索引仍脏 -> 再投递 -> 立刻再唤醒 …… 中间没有 tick 兜底, 直接打满 CPU 并冲垮 qB。
# 新增自投递命令时必须同步加进这里(测试守卫: tests/test_web.py::test_api_enqueue_wakes_main_loop)。
SELF_POSTED_COMMANDS = frozenset({"build_search_index"})

# 执行后会**改变 qB 种子状态**的命令: 主循环在这批命令消费完后补一次完整刷新,
# 让真实状态立刻进快照, 而不必等下个节拍(P0-5)。按操作次数计费, 不是按时间计费。
# 用白名单而非黑名单: 配置/标签/分类类命令(reload_config/create_tags/edit_category …)
# 改的不是种子状态, 补刷新无收益; reannounce_* 的结果由 tracker 确认跟踪器单独推进。
RESYNC_COMMANDS = frozenset(
    {
        "pause_group",
        "resume_group",
        "delete_group",
        "pause_torrent",
        "resume_torrent",
        "delete_torrent",
        "recheck_torrent",
        "super_seeding",
        "force_start",
        "set_torrent_limits",
        "set_share_limits",
        "set_torrent_location",
        "rename_torrent",
        "queue_torrent",
        "set_auto_tmm",
        "add_trackers",
        "set_file_priority",
        "rename_fs",
        "bulk_torrents",
        "add_torrents",
    }
)

# **延迟回执**命令: handler 只发指令并登记确认跟踪, 真正的结果由后续 tick(tracker 确认)或
# handler 内部(依 qB 返回串写)写入 —— 它们不是"执行完即 ok", 所以 drain 侧**不**补写回执。
DEFERRED_RECEIPT_COMMANDS = frozenset({"reannounce_group", "reannounce_torrent", "bulk_torrents", "add_torrents"})


def _timing(queued_ts: Optional[float], start_ts: float) -> dict:
    """P0-0 埋点: 把一次命令拆成两段耗时(毫秒), 供 /api/cmd/{id} 回传

    wait_ms = 出队时刻 - 投递时刻(命令排队等主循环的空档, P0-1 唤醒后应趋近 0)
    exec_ms = 执行完时刻 - 出队时刻(真正干活: 多数是 1 次 qB API 往返)

    ❗这两段**只在回执里回传**, 要看就得开浏览器控制台 —— 真机上用户不一定开得了(嵌入式
    WebView / 手机 / 不愿开 F12)。故 drain 侧同时落一行日志(见 _log_cmd_timing),
    排查"点了要等几秒"时**不用控制台**。
    """
    if not queued_ts:
        return {}
    return {
        "wait_ms": round((start_ts - queued_ts) * 1000, 1),
        "exec_ms": round((time.time() - start_ts) * 1000, 1),
    }


# 慢命令告警阈值(ms): 超过就按 WARNING 落日志, 便于在日志里直接捞
CMD_SLOW_MS = 300.0


class WebCommandsMixin:
    def _drain_web_commands(self) -> bool:
        """消费 WEB UI 控制命令(Web 线程投递, 主循环线程执行写操作——单一写者约束保持)

        命令带 cmd_id: 执行完立即写回执(_web_results), 供前端 /api/cmd/{id} 轮询执行结果。
        例外: reannounce 只发指令并登记确认跟踪(_reannounce_pending), 回执由
        _check_reannounce_pending 在 tracker 确认后写入 —— "已发送"不等于"汇报成功";
        bulk_torrents 的回执由 handler 聚合写(部分失败需报缺失计数)。

        返回本批是否含"改了 qB 种子状态"的命令(RESYNC_COMMANDS)且执行成功 ——
        主循环据此补一次完整刷新(P0-5)。整批只补一次, 不是每条命令各补一次。
        """
        handlers = {
            "pause_group": self._cmd_pause_group,
            "resume_group": self._cmd_resume_group,
            "reannounce_group": self._cmd_reannounce_group,
            "delete_group": self._cmd_delete_group,
            "pause_torrent": self._cmd_pause_torrent,
            "resume_torrent": self._cmd_resume_torrent,
            "reannounce_torrent": self._cmd_reannounce_torrent,
            "delete_torrent": self._cmd_delete_torrent,
            "recheck_torrent": self._cmd_recheck_torrent,
            "super_seeding": self._cmd_super_seeding,
            "force_start": self._cmd_force_start,
            "set_torrent_limits": self._cmd_set_torrent_limits,
            "set_share_limits": self._cmd_set_share_limits,
            "set_torrent_location": self._cmd_set_torrent_location,
            "rename_torrent": self._cmd_rename_torrent,
            "queue_torrent": self._cmd_queue_torrent,
            "set_auto_tmm": self._cmd_set_auto_tmm,
            "add_trackers": self._cmd_add_trackers,
            "edit_tracker": self._cmd_edit_tracker,
            "remove_tracker": self._cmd_remove_tracker,
            "set_file_priority": self._cmd_set_file_priority,
            "rename_fs": self._cmd_rename_fs,
            "bulk_torrents": self._cmd_bulk_torrents,
            "create_category": self._cmd_create_category,
            "edit_category": self._cmd_edit_category,
            "remove_categories": self._cmd_remove_categories,
            "create_tags": self._cmd_create_tags,
            "delete_tags": self._cmd_delete_tags,
            "speed_override": self._cmd_speed_override,
            "add_torrents": self._cmd_add_torrents,
            "reload_config": self._cmd_reload_config,
            "build_search_index": self._cmd_build_search_index,
        }
        changed = False
        try:
            while True:
                cmd, payload = self.web_commands.get_nowait()
                cmd_id = str(payload.get("cmd_id") or "")
                # 下划线前缀的键是埋点/元数据, 不传给 handler(否则被当命令参数报 TypeError)
                args = {k: v for k, v in payload.items() if k != "cmd_id" and not k.startswith("_")}
                queued_ts = payload.get("_queued_ts")
                start_ts = time.time()  # P0-0: 出队即开始, 用于拆 wait_ms / exec_ms
                try:
                    deferred = cmd in DEFERRED_RECEIPT_COMMANDS
                    if cmd_id and deferred:
                        # handler 只发指令并登记确认跟踪(bulk: 聚合写回执; add: 依 qB 结果串写回执);
                        # 回执由后续 tick(汇报确认)或 handler 内部写入 —— 均不是简单的"执行完即 ok"
                        handlers[cmd](cmd_id=cmd_id, **args)
                    else:
                        handlers[cmd](**args)
                    # 写命令序号: Web 线程的只读端点短缓存据此失效(P1-4)。自投递命令不计数 ——
                    # 它只是内部索引推进, 且频次高, 计进去会让缓存在建索引期间完全失效。
                    # ❗必须在写回执**之前**自增: 前端拿到回执会立刻重取只读端点(如改完分类重取
                    # /api/categories), 若先写回执, 那一瞬的读会命中旧写序号对应的缓存键 ——
                    # 顺序反过来才是"先让缓存失效, 再宣布命令成功"。
                    if cmd not in SELF_POSTED_COMMANDS:
                        self._web_write_seq += 1
                    timing = _timing(queued_ts, start_ts)
                    if cmd_id and not deferred:
                        if cmd in RESYNC_COMMANDS:
                            # ❗改种子状态的命令: 回执**推迟到补刷新之后**再写(见 _flush_deferred_receipts)。
                            # 原写法在这里就写 ok, 而 P0-5 的补刷新还在**后面**才跑 ⇒ 前端"拿到回执就
                            # 立刻 refresh"取到的必然是补刷新**之前**的旧快照(rid 未变), 第一次拉取
                            # 100% 扑空, 要等 200ms 退避重试 —— 大库单轮 refresh 慢时, 这一次扑空就是
                            # 用户肉眼看到的"点了要 2 秒才恢复正常"(真机实测 排队 0 / 执行 8.4 /
                            # 补刷新 88.4ms, 而前端撤下 1998ms)。推迟后第一次拉取即可命中。
                            self._defer_receipt(cmd_id, cmd, args, timing)
                        else:
                            self._set_web_result(cmd_id, "ok", timing=timing)
                    if cmd_id:
                        self._log_cmd_timing(cmd, timing)
                    # handler 已同步改完 qB 状态(未抛异常即成功) -> 记一笔, 整批结束后补刷新
                    if cmd in RESYNC_COMMANDS:
                        changed = True
                except KeyError as e:
                    logger.warning(f"WEB UI 未知命令: {e}")
                    if cmd_id:
                        self._set_web_result(cmd_id, "error", f"未知命令: {e}", _timing(queued_ts, start_ts))
                except Exception as e:
                    logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
                    if cmd_id:
                        self._set_web_result(cmd_id, "error", str(e), _timing(queued_ts, start_ts))
        except queue.Empty:
            pass
        return changed

    def _set_web_result(
        self, cmd_id: str, status: str, error: str = "", timing: Optional[dict] = None, truth: Optional[dict] = None
    ) -> None:
        """写入命令执行结果回执(主循环线程唯一写者); 顺手清理 2 分钟前的旧回执防无限增长

        timing: P0-0 埋点(wait_ms 排队等主循环 / exec_ms 执行耗时), 由 /api/cmd/{id} 一并返回,
        前端据此把"点下去到看到结果"拆成可归因的几段, 而不是只有一个"感觉慢"。
        """
        now = time.time()
        if len(self._web_results) > 64:
            self._web_results = {k: v for k, v in self._web_results.items() if now - v.get("ts", 0) < 120}
        rec = {"status": status, "error": error, "ts": now}
        if timing:
            rec.update(timing)
        if truth:
            # 受影响种子的**当前真值**({hash: {"kind": ...}}): 前端拿到即可撤下乐观态,
            # 省掉"回执后再拉一次全量 /api/state"这一趟(大库单轮 refresh 可达数百毫秒)。
            rec["truth"] = truth
        self._web_results[cmd_id] = rec

    def _defer_receipt(self, cmd_id: str, cmd: str, args: dict, timing: dict) -> None:
        """登记"等补刷新跑完再写"的回执(主循环线程唯一写者)

        与 `_set_web_result` 的区别只是**时机**: 登记后由 `run()` 在补刷新之后调
        `_flush_deferred_receipts()` 落盘, 并顺带把受影响种子的**当前真值**写进回执
        ⇒ 前端拿到回执就能撤下乐观态, 不必再发一次全量 refresh。
        """
        d = getattr(self, "_deferred_receipts", None)
        if d is None:
            d = {}
            self._deferred_receipts = d
        d[cmd_id] = {"cmd": cmd, "args": dict(args or {}), "timing": timing}

    def _affected_hashes(self, cmd: str, args: dict) -> List[str]:
        """命令影响了哪些种子(用于回执带真值); 取不到就返回空 —— 只影响能否省一次 refresh, 不影响正确性"""
        try:
            if cmd.endswith("_torrent"):
                h = (args or {}).get("hash")
                return [h] if h else []
            if cmd.endswith("_group"):
                return list(self.store.groups.get((args or {}).get("key") or (), []) or [])
            if cmd == "bulk_torrents":
                out = list((args or {}).get("hashes") or [])
                for k in (args or {}).get("keys") or []:
                    out.extend(self.store.groups.get(k, []) or [])
                return list(dict.fromkeys(out))
        except Exception:  # 桩/异常配置下取不到就退化为"不写真值", 前端照旧拉一次
            return []
        return []

    def _flush_deferred_receipts(self) -> None:
        """补刷新跑完后落回执, 并附上受影响种子的当前真值(主循环线程调用)

        ❗**必须无条件调用**(哪怕本轮没跑补刷新 / dry_run): 漏调会让前端 waitCmd 干等 40s。
        真值取 `store.by_hash` 的当前 kind —— 补刷新之后它就是服务端认为的最新状态。
        """
        d = getattr(self, "_deferred_receipts", None)
        if not d:
            return
        self._deferred_receipts = {}
        n_truth = 0
        for cmd_id, item in d.items():
            truth = {}
            try:
                for h in self._affected_hashes(item["cmd"], item["args"]):
                    rec = self.store.by_hash.get(h)
                    if rec is None:
                        continue
                    truth[h] = {"kind": self._state_kind(rec)}
            except Exception:
                truth = {}
            n_truth += len(truth)
            self._set_web_result(cmd_id, "ok", timing=item["timing"], truth=truth or None)
        # 排查标记: 日志里**没有这一行** = 服务端还在跑旧代码(回执在补刷新之前就写了),
        # 前端只能走 via=pull 拉全量 —— 真机大库上就是"点了要 1.7~2s 才恢复正常"。
        logger.info(f"[cmd] 回执(补刷新后)已写 {len(d)} 条, 带真值 {n_truth} 个种子")

    def _log_cmd_timing(self, cmd: str, timing: Optional[dict]) -> None:
        """命令耗时落日志 —— 排查"点了要等几秒"的**主出口**(不依赖浏览器控制台)

        2026-09-20: 用户连续四次报"乐观 UI 生效但要 2-4s 才恢复正常", 四轮修复全在前端找,
        因为本地桩服务**没有主循环** ⇒ `wait_ms` 恒为 0 ⇒ "命令投递 → 回执"这一段从来没被测到。
        而真机上用户往往开不了/不愿开 F12, 埋点只回传在回执里等于没有。故这里直接落到日志。

        三段的读法(配合 qbmanager.run() 里补刷新那段日志):
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
            logger.info(msg)

    def _trackers_baseline(self, hashes: List[str]) -> dict:
        """读取汇报前各种子的 tracker 状态基线: {hash: {url: (status, next_announce)}}

        排除 DHT/PeX/LSD 虚拟 tracker(url 以 **/[DHT]/[PeX]/[LSD] 开头, 它们不走 announce)。
        qB 断连等读取失败时异常上抛, 由命令分发层写 error 回执。
        """
        baseline = {}
        for h in hashes:
            trackers = self.client.torrents_trackers(h) or []
            real = {}
            for t in trackers:
                url = str(t.get("url") or "")
                if url.startswith(("**", "[DHT]", "[PeX]", "[LSD]")):
                    continue
                real[url] = (t.get("status"), t.get("next_announce"))
            baseline[h] = real
        return baseline

    @staticmethod
    def _confirm_reannounce_result(trackers: list, baseline: dict) -> Optional[bool]:
        """判定单个种子汇报确认结果: True=已确认成功 / False=已确认失败 / None=仍在进行

        逐 tracker 检查, 任一命中即结论:
        - status == 3 (updating)                    -> qB 正在汇报, 视为成功
        - next_announce 比基线提前(>60 单位, 秒/毫秒通用) -> next_announce 被重置, 视为成功
        - status 从非 working 变为 2 (working)      -> 视为成功
        - status == 4 (not working) 且带错误消息    -> tracker 拒绝, 视为失败
        """
        for t in trackers:
            url = str(t.get("url") or "")
            if url.startswith(("**", "[DHT]", "[PeX]", "[LSD]")):
                continue
            b_status, b_na = baseline.get(url, (None, None))
            status = t.get("status")
            na = t.get("next_announce")
            if status == 3:
                return True
            if na is not None and b_na is not None and na < b_na - 60:
                return True
            if status == 2 and b_status is not None and b_status != 2:
                return True
            if status == 4 and (t.get("msg") or ""):
                return False
        return None

    def _check_reannounce_pending(self):
        """每 tick 检查在途的强制汇报确认; 某 cmd_id 全部种子出结论后聚合写回执"""
        if not self._reannounce_pending:
            return
        now = time.time()
        finished = []
        for cmd_id, entry in self._reannounce_pending.items():
            for h, it in entry["items"].items():
                if it["done"]:
                    continue
                if now >= entry["deadline"]:
                    it["done"], it["ok"] = True, False
                    it["err"] = f"汇报确认超时({REANNOUNCE_CONFIRM_TIMEOUT:.0f}s 内未确认到 tracker 响应)"
                    continue
                if self.client is None:
                    continue  # qB 断连: 等恢复继续确认, 或按超时判失败
                try:
                    trackers = self.client.torrents_trackers(h) or []
                    r = self._confirm_reannounce_result(trackers, it["baseline"])
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
            entry = self._reannounce_pending.pop(cmd_id)
            items = list(entry["items"].values())
            fails = [it for it in items if not it["ok"]]
            if not fails:
                self._set_web_result(cmd_id, "ok")
                logger.info(f"WEB UI | 强制汇报确认成功({len(items)}个种子)")
            else:
                msg = f"{len(fails)}/{len(items)} 个种子汇报确认失败: " + "; ".join(it["err"] for it in fails[:3])
                self._set_web_result(cmd_id, "error", msg)
                logger.warning(f"WEB UI | {msg}")

    def _cmd_build_search_index(self):
        """WEB UI 命令: 构建搜索索引(Web 线程检测到索引脏后投递, 主循环线程执行)。

        限流构建可能需多轮: 仅在全部拉取完成(不再脏)时记录完成日志, 避免分批刷屏。
        """
        self._build_search_index()
        if not self._search_index_dirty:
            logger.info(f"WEB UI | 搜索索引已构建: {len(self._search_index)} 个种子")

    def _cmd_pause_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_pause(torrent_hashes=hashes)
            logger.info(f"WEB UI | 暂停整组({len(hashes)}个种子)")

    def _cmd_resume_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_resume(torrent_hashes=hashes)
            logger.info(f"WEB UI | 开始整组({len(hashes)}个种子)")

    def _cmd_reannounce_group(self, key: tuple, cmd_id: str = ""):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_reannounce(torrent_hashes=hashes)
            # 发送仅是"已下发指令"; 成功回执由 tracker 确认跟踪器在后续 tick 写入
            baseline = self._trackers_baseline(hashes)
            self._register_reannounce_pending(cmd_id, hashes, baseline)
            logger.warning(f"WEB UI | 强制汇报整组({len(hashes)}个种子), 等待 tracker 确认")

    def _cmd_delete_group(self, key: tuple, delete_files: bool = False):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_delete(torrent_hashes=hashes, delete_files=delete_files)
            logger.warning(f"WEB UI | 删除整组({len(hashes)}个种子, delete_files={delete_files})")

    def _cmd_pause_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_pause(torrent_hashes=[hash])
            logger.info(f"WEB UI | 暂停种子 {hash[:8]}")

    def _cmd_resume_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_resume(torrent_hashes=[hash])
            logger.info(f"WEB UI | 开始种子 {hash[:8]}")

    def _cmd_reannounce_torrent(self, hash: str, cmd_id: str = ""):
        if self.store.get(hash) is None:
            # 种子已不存在: 无法汇报, 直接给失败回执(删除流程据此不删除)
            if cmd_id:
                self._set_web_result(cmd_id, "error", "种子不存在或已被删除")
            return
        self.api.torrents_reannounce(torrent_hashes=[hash])
        baseline = self._trackers_baseline([hash])
        self._register_reannounce_pending(cmd_id, [hash], baseline)
        logger.warning(f"WEB UI | 强制汇报种子 {hash[:8]}, 等待 tracker 确认")

    def _register_reannounce_pending(self, cmd_id: str, hashes: List[str], baseline: dict) -> None:
        """登记汇报确认跟踪: 全部种子出结论(成功/失败/超时)后聚合写该 cmd_id 的回执"""
        if not cmd_id:
            return  # 无回执需求的调用(直接构造 manager 的场景): 只发指令不跟踪
        self._reannounce_pending[cmd_id] = {
            "deadline": time.time() + REANNOUNCE_CONFIRM_TIMEOUT,
            "items": {
                h: {
                    "done": False,
                    "ok": False,
                    "err": "",
                    "baseline": baseline[h]
                }
                for h in hashes
            },
        }

    def _cmd_delete_torrent(self, hash: str, delete_files: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_delete(torrent_hashes=[hash], delete_files=delete_files)
            logger.warning(f"WEB UI | 删除种子 {hash[:8]}(delete_files={delete_files})")

    def _cmd_recheck_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_recheck(torrent_hashes=[hash])
            logger.info(f"WEB UI | 重新校验种子 {hash[:8]}")

    def _cmd_super_seeding(self, hash: str, enable: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_set_super_seeding(enable=enable, torrent_hashes=[hash])
            logger.info(f"WEB UI | 种子 {hash[:8]} 超级做种({'开' if enable else '关'})")

    def _cmd_force_start(self, hash: str, enable: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_set_force_start(enable=enable, torrent_hashes=[hash])
            logger.info(f"WEB UI | 种子 {hash[:8]} 强制开始({'开' if enable else '关'})")

    def _cmd_set_torrent_limits(self, hash: str, up_limit: Optional[int] = None, dl_limit: Optional[int] = None):
        """种子传输限速(bytes/s, 0 = 不限); 只下发非 None 的方向, 快照 up_limit/dl_limit 同步更新"""
        if self.store.get(hash) is None:
            return
        if up_limit is not None:
            self.api.torrents_set_upload_limit(torrent_hashes=[hash], limit=int(up_limit))
        if dl_limit is not None:
            self.api.torrents_set_download_limit(torrent_hashes=[hash], limit=int(dl_limit))
        logger.info(f"WEB UI | 种子 {hash[:8]} 限速更新(up={up_limit}, down={dl_limit} bytes/s, 0=不限; 仅设置提供的方向)")

    def _cmd_set_share_limits(
        self,
        hash: str,
        ratio_limit: Optional[float] = None,
        seeding_time_limit: Optional[int] = None,
        inactive_seeding_time_limit: Optional[int] = None,
    ):
        """种子分享限制; 缺失维度按 -2(使用全局默认)补齐 —— 库不过滤 None, 直传会发字面量 "None"

        哨兵语义(与 qbittorrent-api torrents_set_share_limits 文档一致):
        -2 = 使用全局分享限制默认值; -1 = 不限制; 正数 = 限制值(比例/分钟)。
        """
        if self.store.get(hash) is None:
            return
        self.api.torrents_set_share_limits(
            ratio_limit=-2.0 if ratio_limit is None else float(ratio_limit),
            seeding_time_limit=-2 if seeding_time_limit is None else int(seeding_time_limit),
            inactive_seeding_time_limit=-2 if inactive_seeding_time_limit is None else int(inactive_seeding_time_limit),
            torrent_hashes=[hash],
        )
        logger.info(
            f"WEB UI | 种子 {hash[:8]} 分享限制更新(ratio={ratio_limit}, seeding_time={seeding_time_limit}, "
            f"inactive={inactive_seeding_time_limit}; -1=不限制, -2=用全局)"
        )

    def _cmd_set_torrent_location(self, hash: str, location: str = ""):
        if self.store.get(hash) is None:
            return
        if not location:
            raise ValueError("location 不能为空")
        self.api.torrents_set_location(torrent_hashes=[hash], location=location)
        # 组键含 save_path: 移动后下轮同步会按新 save_path 重归组(旧组解散/新组建立), 属预期行为
        logger.warning(f"WEB UI | 种子 {hash[:8]} 移动保存路径 -> {location}(将按新路径重归组, 属预期)")

    def _cmd_rename_torrent(self, hash: str, name: str = ""):
        if self.store.get(hash) is None:
            return
        if not name:
            raise ValueError("重命名名称不能为空")
        self.api.torrents_rename(torrent_hash=hash, new_torrent_name=name)
        # 只改 qB 显示名: 快照 name 不手工改, 下轮 sync 自然更新
        logger.info(f"WEB UI | 重命名种子 {hash[:8]} -> {name}")

    # 队列调整动作 -> QbApi 方法映射(qB 端点语义: top/bottom 置顶/置底, up/down 相邻交换)
    _QUEUE_ACTIONS = {
        "top": "torrents_top_priority",
        "up": "torrents_increase_priority",
        "down": "torrents_decrease_priority",
        "bottom": "torrents_bottom_priority",
    }

    def _cmd_queue_torrent(self, hash: str, action: str = ""):
        method = self._QUEUE_ACTIONS.get(action)
        if method is None:
            raise ValueError(f"未知队列动作: {action}(可选 top/up/down/bottom)")
        if self.store.get(hash) is None:
            return
        getattr(self.api, method)(torrent_hashes=[hash])
        logger.info(f"WEB UI | 种子 {hash[:8]} 队列调整: {action}")

    def _cmd_set_auto_tmm(self, hash: str, enable: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_set_auto_management(enable=enable, torrent_hashes=[hash])
            logger.info(f"WEB UI | 种子 {hash[:8]} 自动管理({'开' if enable else '关'})")

    def _cmd_add_trackers(self, hash: str, urls=None):
        if self.store.get(hash) is None:
            return
        url_list = [u for u in (urls or []) if u]
        if not url_list:
            raise ValueError("urls 不能为空")
        self.api.torrents_add_trackers(torrent_hash=hash, urls=url_list)
        logger.info(f"WEB UI | 种子 {hash[:8]} 添加 {len(url_list)} 个 tracker")

    def _cmd_edit_tracker(self, hash: str, orig_url: str = "", new_url: str = ""):
        if self.store.get(hash) is None:
            return
        if not orig_url or not new_url:
            raise ValueError("orig_url/new_url 均不能为空")
        self.api.torrents_edit_tracker(torrent_hash=hash, original_url=orig_url, new_url=new_url)
        logger.info(f"WEB UI | 种子 {hash[:8]} 编辑 tracker: {orig_url} -> {new_url}")

    def _cmd_remove_tracker(self, hash: str, url: str = ""):
        if self.store.get(hash) is None:
            return
        if not url:
            raise ValueError("url 不能为空")
        self.api.torrents_remove_trackers(torrent_hash=hash, urls=[url])
        logger.info(f"WEB UI | 种子 {hash[:8]} 移除 tracker: {url}")

    # qB 文件优先级合法值(0=不下载, 1=普通, 6=高, 7=最大)
    _FILE_PRIORITIES = frozenset((0, 1, 6, 7))

    def _cmd_set_file_priority(self, hash: str, indices=None, priority: int = 0):
        if self.store.get(hash) is None:
            return
        idx = [int(i) for i in (indices or [])]
        prio = int(priority)
        if not idx:
            raise ValueError("indices 不能为空")
        if prio not in self._FILE_PRIORITIES:
            raise ValueError(f"非法文件优先级: {priority}(可选 0/1/6/7)")
        self.api.torrents_file_priority(torrent_hash=hash, file_ids=idx, priority=prio)
        logger.info(f"WEB UI | 种子 {hash[:8]} 文件优先级: {idx} -> {prio}")

    def _cmd_rename_fs(self, hash: str, old_path: str = "", new_path: str = "", is_folder: bool = False):
        if self.store.get(hash) is None:
            return
        if not old_path or not new_path:
            raise ValueError("old_path/new_path 均不能为空")
        if is_folder:
            self.api.torrents_rename_folder(torrent_hash=hash, old_path=old_path, new_path=new_path)
        else:
            self.api.torrents_rename_file(torrent_hash=hash, old_path=old_path, new_path=new_path)
        logger.info(f"WEB UI | 种子 {hash[:8]} 重命名{'文件夹' if is_folder else '文件'}: {old_path} -> {new_path}")

    # 批量动作 -> API 调用(单次调用传全部 hashes, 不逐个循环; delete 透传 delete_files)
    _BULK_ACTIONS = {
        "pause":
            lambda api, hashes, delete_files: api.torrents_pause(torrent_hashes=hashes),
        "resume":
            lambda api, hashes, delete_files: api.torrents_resume(torrent_hashes=hashes),
        "recheck":
            lambda api, hashes, delete_files: api.torrents_recheck(torrent_hashes=hashes),
        "delete":
            lambda api, hashes, delete_files: api.torrents_delete(torrent_hashes=hashes, delete_files=delete_files),
    }

    def _cmd_bulk_torrents(
        self, hashes=None, action: str = "", cmd_id: str = "", delete_files: bool = False, keys=None
    ):
        """WEB UI 命令: 批量操作(单命令批量, 平铺视图多选); 回执由本 handler 聚合写

        - 未知 action / 空 hash 列表 -> error 回执
        - 不在快照中的 hash 跳过(删除守阵), 仍有缺失时回执 error 带缺失计数(部分成功也报错,
          前端可据列表刷新后重试); 全部命中 -> ok
        - API 只调一次: hashes 整体传给既有 api 调用(qB 端点原生接受批量)
        - 组键模式(DLG-02): keys 为分组 key 列表(tuple, Web 层已解码), 逐组展开成员
          (经 _group_hashes 按快照过滤, 级联全部在册成员)并与 hashes 合并去重; 组不存在或
          成员全部不在快照计一个缺失组, 缺失文案与种子缺失分列(纯 hash 模式文案不变, 前端契约保持)
        """
        req = [h for h in (hashes or []) if h]
        keys = [k for k in (keys or []) if k]
        fn = self._BULK_ACTIONS.get(action)
        if fn is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", f"未知批量动作: {action}(可选 pause/resume/recheck/delete)")
            return
        if not req and not keys:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供任何 hash 或组")
            return
        known = [h for h in req if self.store.get(h) is not None]
        missing = len(req) - len(known)
        seen = set(known)
        missing_groups = 0
        for key in keys:
            members = [h for h in self._group_hashes(key) if h not in seen]
            if members:
                seen.update(members)
                known.extend(members)
            else:
                missing_groups += 1
        if known:
            fn(self.api, known, delete_files)
        msgs = []
        if missing:
            msgs.append(f"{missing}/{len(req)} 个种子不存在或已被删除")
        if missing_groups:
            msgs.append(f"{missing_groups}/{len(keys)} 个组不存在或成员为空")
        if msgs:
            msg = "; ".join(msgs)
            if cmd_id:
                self._set_web_result(cmd_id, "error", msg)
            logger.warning(f"WEB UI | 批量 {action}({len(known)}个种子): {msg}")
        else:
            if cmd_id:
                self._set_web_result(cmd_id, "ok")
            logger.warning(f"WEB UI | 批量 {action}({len(known)}个种子, delete_files={delete_files})")

    def _cmd_reload_config(self, config: Config):
        self.apply_new_config(config)

    # ---------- 管理命令(R2B: 分类/标签/限速覆盖/添加种子) ----------

    def _cmd_create_category(self, name: str, save_path: str = ""):
        self.api.torrents_create_category(name=name, save_path=save_path or None)
        logger.info(f"WEB UI | 新建分类: {name}" + (f"(保存路径 {save_path})" if save_path else ""))

    def _cmd_edit_category(self, name: str, save_path: str = ""):
        self.api.torrents_edit_category(name=name, save_path=save_path or None)
        logger.info(f"WEB UI | 修改分类: {name} -> 保存路径 {save_path or '(未设置)'}")

    def _cmd_remove_categories(self, names=None):
        self.api.torrents_remove_categories(categories=names)
        logger.warning(f"WEB UI | 删除分类: {', '.join(names)}")

    def _cmd_create_tags(self, tags=None):
        self.api.torrents_create_tags(tags=tags)
        logger.info(f"WEB UI | 新建标签: {', '.join(tags)}")

    def _cmd_delete_tags(self, tags=None):
        self.api.torrents_delete_tags(tags=tags)
        logger.warning(f"WEB UI | 删除标签: {', '.join(tags)}")

    def _cmd_speed_override(self, upload_kib: int = 0, download_kib: int = 0):
        """全局限速手动覆盖(D2): 曲线启用时为"临时覆盖"——曲线任务下一档位切换写回目标值;
        曲线停用即常态设置。不做"暂停曲线接管"状态。"""
        self.api.set_global_speed_limits(upload_kib=int(upload_kib or 0), download_kib=int(download_kib or 0))
        logger.warning(f"WEB UI | 全局限速手动覆盖: 上 {upload_kib} / 下 {download_kib} KiB/s")

    def _cmd_add_torrents(
        self,
        files=None,
        urls=None,
        save_path: str = "",
        category: str = "",
        tags=None,
        paused: bool = False,
        skip_checking: bool = False,
        sequential: bool = False,
        first_last_piece_prio: bool = False,
        auto_tmm: bool = False,
        cmd_id: str = ""
    ):
        """WEB UI 添加种子: .torrent 原始 bytes 经命令队列传给主循环线程, 内存直交 qB(qbittorrent-api
        _normalize_torrent_files 原生支持 bytes) —— 零临时文件。

        回执由本 handler 依 qB 结果串写("Ok."=ok, 其余 error) —— "指令已发"与"qB 接受"分开;
        skip_checking 属高危选项, 前端默认关 + 警告, 此处照传(用户显式动作, 不做二次拦截)。"""
        kwargs = dict(
            save_path=save_path or None,
            category=category or None,
            tags=tags or None,
            is_paused=bool(paused),
            is_skip_checking=bool(skip_checking),
            is_sequential_download=bool(sequential),
            is_first_last_piece_priority=bool(first_last_piece_prio),
        )
        kwargs = {k: v for k, v in kwargs.items() if v not in (None, False)}
        if auto_tmm:
            kwargs["use_auto_torrent_management"] = True
        results = []
        if files:
            results.append(str(self.api.torrents_add(torrent_files=files, **kwargs)))
        if urls:
            results.append(str(self.api.torrents_add(urls=urls, **kwargs)))
        ok = bool(results) and all("Ok." in s for s in results)
        if cmd_id:
            if ok:
                self._set_web_result(cmd_id, "ok")
            else:
                self._set_web_result(cmd_id, "error", f"qB 未接受添加: {'; '.join(results) or '无结果'}")
        logger.warning(f"WEB UI | 添加种子: 文件 {len(files or [])} 个, 链接 {len(urls or [])} 条 -> {results}")
