"""WebUIRuntime 拆分: 命令消费 / 回执 / 真值推送 / 强制汇报确认跟踪。

move-only 自 runtime.py 切出(计划 26-11-02-2342 §07 R5), 未改语义; 由根 runtime.py 组合进 WebUIRuntime。
"""
import queue
import secrets
from typing import List, Optional

from .commands import (
    CMD_ID_COMMANDS,
    CMD_SLOW_MS,
    RC_UNCONFIRMED_PREFIX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    REANNOUNCE_JUMP_TOL,
    TRUTH_PUSH_CAP_MS,
    RESYNC_COMMANDS,
    SELF_POSTED_COMMANDS,
    _timing,
    is_deferred_receipt,
    qb_reject_text,
)
from .runtime_common import TRUTH_QUERY_CHUNK, WEB_RESULT_MAX, WEB_RESULT_TTL, logger


class CommandsMixin:
    # ------------------------------------------------------------------ 主循环接口

    def consume_commands(self) -> bool:
        """消费 WEB UI 控制命令; 返回本批是否含"改了 qB 种子状态"的命令(主循环据此补刷新)

        命令带 cmd_id: 执行完立即写回执(见 results), 供前端 /api/cmd/{id} 轮询。
        例外: reannounce 只发指令并登记确认跟踪(reannounce_pending), 回执由 check_pending()
        在 tracker 确认后写入 —— "已发送"不等于"汇报成功"; bulk/add 的回执由 handler 聚合写。

        !写序号必须在写回执**之前**自增: 前端拿到回执会立刻重取只读端点(如改完分类重取
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
                start_ts = self._clock.now()  # 出队即开始, 用于拆 wait_ms / exec_ms
                try:
                    # !按 (cmd, action) 分流判定: bulk_torrents 的 pause/resume 不走延迟回执族,
                    #   要落到下面的 defer_receipt(与单种同通路)。判定单点在 commands.is_deferred_receipt。
                    deferred = is_deferred_receipt(cmd, args)
                    # !cmd_id 的**传递**与"谁写回执"是两件事(见 commands.CMD_ID_COMMANDS):
                    #   bulk_torrents 的 pause/resume 回执由 drain 写, 但 handler 仍需 cmd_id
                    #   才能写错误回执(部分 hash 缺失 / 参数不合法)。
                    if cmd_id and cmd in CMD_ID_COMMANDS:
                        handlers[cmd](cmd_id=cmd_id, **args)
                    else:
                        handlers[cmd](**args)
                    # 自投递命令不计数: 它只是内部索引推进, 且频次高, 计进去会让缓存在
                    # 建索引期间完全失效
                    if cmd not in SELF_POSTED_COMMANDS:
                        self.write_seq += 1
                    timing = _timing(queued_ts, start_ts, self._clock)
                    # !`cmd_id not in self.results`: handler 可能已自写回执(bulk 部分 hash 缺失时
                    #   写的是 error) —— 那种情况 drain 不得再用 ok 覆盖(report 26-10-11-2017 §6.2)。
                    if cmd_id and not deferred and cmd_id not in self.results:
                        if cmd in RESYNC_COMMANDS:
                            # 改种子状态的命令 —— D2 现行语义(实现单点 = defer_receipt):
                            # **回执立即写**(只表示"命令已执行", 前端据此结束压暗, 撤下 10~20ms 级);
                            # **真值延后推**: flush_truths 直查 qB, 落地了才发 `truth` 事件,
                            # 前端据此结束"值覆盖"。旧语义(在这里扣住回执等真值)已废弃:
                            # 真机实测 qB 翻状态要 ~1.25s, 扣回执会把撤下钉死在 1.25s+(实测 2947ms)。
                            # 注: 回执到达时补刷新尚未跑, 前端此刻立刻 refresh 仍可能扑空一次,
                            # 扑空窗口实测 <10ms, 行上值覆盖由 hold 兜住不弹回(2026-10-30 实测锚点)。
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
                        self.set_result(cmd_id, "error", f"未知命令: {e}", _timing(queued_ts, start_ts, self._clock))
                except Exception as e:
                    # qB 业务拒绝(HTTP 4xx, 未启用 torrent 队列 / 名字已存在 ...) 是**用户这次
                    # 操作被 qB 拒绝**, 不是未预期异常: 前端已有可读回执, 用户看得懂, 不必弹窗
                    # (弹窗测试 -> WARNING, 无堆栈)。其余(网络 / 鉴权 / 代码 bug)仍按 ERROR +
                    # 堆栈记录。判据与文案单点在 commands.qb_reject_text, 这里只分流。
                    reason = qb_reject_text(e)
                    if reason is None:
                        logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
                        reason = str(e)
                    else:
                        logger.warning(f"WEB UI 命令被 qB 拒绝: {cmd}: {reason}")
                    if cmd_id:
                        self.set_result(cmd_id, "error", reason, _timing(queued_ts, start_ts, self._clock))
        except queue.Empty:
            pass
        return changed

    def _judge_reannounce(self, h: str, baseline: dict, *, t0: float, now: float) -> tuple:
        """读一次 trackers 并出结论(判定处置单点) -> (state, reason)

        `check_pending`(在途轮询确认)与 `_advance_reannounce_background`(推迟后台核实)两处
        同骨架「读 trackers -> host._verdict_reannounce」, 抽本单点后读失败口径一致:
        只 DEBUG, item 留在原处下 tick 重试, 不单次终局。
        qB 断连(host.client 为 None)不下读: 回 ("", "") = 无结论, 调用方照旧等恢复。
        """
        host = self._host
        if host.client is None:
            return "", ""
        trackers = host.client.torrents_trackers(h) or []
        return host._verdict_reannounce(trackers, baseline, t0=t0, tol=REANNOUNCE_JUMP_TOL, now=now)

    def check_pending(self) -> None:
        """每 tick 检查在途的强制汇报确认与推迟后台核实; 某 cmd_id 全部种子出结论后聚合写回执

        逐 item 推进(判定链, 见 commands._verdict_reannounce 的判定表·消解等待模型):
          item 级 deadline 超时 -> warn「未确认」(不再判「失败」) / store 快照 stopped 直判 ->
          qB 断连/读失败等待 / 调 _verdict_reannounce 出 confirmed(ok)/rejected(error)。
        全部 item 出结论后聚合三桶(D4=warn): 任一 error -> error; 否则任一 warn -> warn;
        全 ok -> ok, 文案「成功 X, 失败 Y, 未确认 Z: <前 3 条原因>」。
        推迟登记的后台核实(reannounce_background)同 tick 推进, 结论只落日志。
        """
        host = self._host
        if not self.reannounce_pending and not self.reannounce_background:
            return
        now = self._clock.now()
        self._advance_reannounce_background(now)
        if not self.reannounce_pending:
            return
        store = getattr(host, "store", None)
        finished = []
        for cmd_id, entry in self.reannounce_pending.items():
            for h, it in entry["items"].items():
                if it["done"]:
                    continue
                if now >= it["deadline"]:
                    # 超时落「未确认」(warn), 不与「失败」混淆; legacy 无 epoch 字段, 只承诺
                    # 「未观测到拒绝」的诚实标签
                    tail = (
                        "旧版 qB 无 epoch 字段, 仅未观测到拒绝" if not it.get("epoch_mode") else
                        f"{REANNOUNCE_CONFIRM_TIMEOUT:.0f}s 内未观测到 working 转换/epoch 前跳/拒绝证据"
                    )
                    it["done"], it["status"], it["reason"] = True, "warn", RC_UNCONFIRMED_PREFIX + tail
                    continue
                if store is not None:
                    rec = store.get(h)
                    if rec is not None and rec.state_enum.is_stopped:
                        # 用户在确认窗口内暂停了种子: qB 静默忽略强制汇报, 直判免白等
                        it["done"], it["status"] = True, "warn"
                        it["reason"] = RC_UNCONFIRMED_PREFIX + "种子已停止, qB 静默忽略强制汇报"
                        continue
                try:
                    state, reason = self._judge_reannounce(h, it["baseline"], t0=it["t0"], now=now)
                except Exception as e:
                    # 瞬时读失败(qB 断连抖动/超时, client 对象仍在)与「无结论」同处置: item 留在
                    # pending 等恢复, 下 tick 重试, deadline 到点落「未确认」。单次失败即终局会把
                    # 可能已成功的汇报报成「失败 N: 读取 tracker 状态失败」且不重试 —— 与
                    # _advance_reannounce_background 的 DEBUG+下 tick 重试口径对齐。
                    logger.debug(f"WEB UI | 强制汇报确认读取失败 {h[:8]}, 留待下 tick 重试: {e}")
                    continue
                if state == "confirmed":
                    it["done"], it["status"] = True, "ok"
                elif state == "rejected":
                    it["done"], it["status"], it["reason"] = True, "error", reason
                # 断连 / 无结论 / 读失败: item 留在 pending, deadline 到点落「未确认」(见上方超时分支)
            if all(it["done"] for it in entry["items"].values()):
                finished.append(cmd_id)
        for cmd_id in finished:
            entry = self.reannounce_pending.pop(cmd_id)
            items = list(entry["items"].values())
            ok_n = sum(1 for it in items if it["status"] == "ok")
            err_n = sum(1 for it in items if it["status"] == "error")
            warn_n = len(items) - ok_n - err_n
            msg = f"成功 {ok_n}, 失败 {err_n}, 未确认 {warn_n}"
            reasons = [it["reason"] for it in items if it["status"] != "ok" and it["reason"]]
            if reasons:
                msg += ": " + "; ".join(reasons[:3])
            # 逐目标结果随回执带出(计划 26-10-19-2007 D6/S5): items[hash] 里本来就有
            # {status, reason}, 聚合文案只留前 3 条原因、且把 hash 丢了 —— 前端因此无法在行上
            # 指出"哪几个失败"。这里原样带出, 不新增端点、不改任何判定逻辑。
            # !文案(msg)逐字不变: 前端三桶计数与文案契约测试钉的是它。
            truth = {
                "results":
                    [{
                        "hash": h,
                        "status": it["status"],
                        "reason": it["reason"],
                    } for h, it in entry["items"].items()]
            }
            if err_n:
                self.set_result(cmd_id, "error", msg, truth=truth)
                logger.warning(f"WEB UI | 强制汇报回执: {msg}")
            elif warn_n:
                self.set_result(cmd_id, "warn", msg, truth=truth)
                logger.info(f"WEB UI | 强制汇报回执: {msg}")
            else:
                self.set_result(cmd_id, "ok", truth=truth)
                logger.info(f"WEB UI | 强制汇报确认成功({ok_n}个种子)")

    def _advance_reannounce_background(self, now: float) -> None:
        """推进推迟登记的后台核实(D1): 达 min_e 后每 tick 读一次 trackers, 出结论只落日志

        登记面在 commands._register_reannounce_pending(已受理·推迟的 item); 本方法只消费:
        confirmed -> INFO 后移除 / rejected -> WARNING 后移除 / 逾时(min_e + TIMEOUT)未出结论
        静默移除(DEBUG)。断连 tick 跳过照旧, 逾时移除兜底(防种子被删等泄漏面, R5)。
        """
        if not self.reannounce_background:
            return
        for h in list(self.reannounce_background):
            bg = self.reannounce_background[h]
            if now < bg["min_e"]:
                continue
            if now >= bg["min_e"] + REANNOUNCE_CONFIRM_TIMEOUT:
                del self.reannounce_background[h]
                logger.debug(f"WEB UI | 推迟汇报后台核实逾时移除 {h[:8]}")
                continue
            try:
                state, reason = self._judge_reannounce(h, bg["baseline"], t0=bg["t0"], now=now)
            except Exception as e:
                logger.debug(f"WEB UI | 推迟汇报后台核实读取失败 {h[:8]}: {e}")
                continue
            if state == "confirmed":
                del self.reannounce_background[h]
                logger.info(f"WEB UI | 推迟汇报后台核实已确认 {h[:8]}: {reason or 'epoch 前跳'}")
            elif state == "rejected":
                del self.reannounce_background[h]
                logger.warning(f"WEB UI | 推迟汇报后台核实失败 {h[:8]}: {reason}")

    def flush_truths(self) -> None:
        """直查真值, 落地了就推 `truth` 事件; 未落地继续等(上限 TRUTH_PUSH_CAP_MS)

        !**必须无条件调用**(哪怕本轮没跑补刷新): 漏调会让前端一直挂着乐观值。
        !超时**不推**: 推一个未落地的真值 = 让前端采纳命令前的旧值 ⇒ 弹回。
          那种情况交给前端超时回滚, 且必须有明确 toast(不能静默)。
        """
        if not self.truth_pending:
            return
        pending, self.truth_pending = self.truth_pending, {}
        now = self._clock.now()
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
        ms = round((self._clock.now() - t0) * 1000, 1)
        # !正常耗时只打 DEBUG: 每条命令都会跑一次补刷新, 全打 INFO 会把日志刷满 ——
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
        now = self._clock.now()
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
        # !必须带上 cmd_id —— 前端按它匹配自己那条命令(多个命令可能同时在途)。
        self.notify("cmd", {**rec, "cmd_id": cmd_id})

    def defer_receipt(self, cmd_id: str, cmd: str, args: dict, timing: dict) -> None:
        """回执**立即**写 + 真值登记为"稍后推"(2026-09-20 D2 定案)

        !为什么不再"扣住回执等真值": 真机实测 qB 把状态翻过来要 **1258ms**, 而命令执行
          只要 2.7ms —— 扣着回执等, 撤下就被 qB 钉死在 1.25s+(实测撤下 2947ms)。
          拆成两步:
            1. 回执立刻发(只表示"命令已执行"), 前端据此**结束压暗** ⇒ 撤下降到 10~20ms;
            2. 真值继续直查, 落地了再推 `truth` 事件, 前端据此结束"值覆盖"。
        !回执**不带 truth**: 带上未落地的真值 = 让前端采纳命令**前**的旧值 ⇒ 弹回
          (4df80dc 那条红线)。真值只走 `truth` 事件, 且只有落地了才推。
        """
        self.set_result(cmd_id, "ok", timing=timing)
        self.truth_pending[cmd_id] = {
            "cmd": cmd,
            "args": dict(args or {}),
            "ts": self._clock.now(),
        }

    @staticmethod
    def _truth_landed(cmd: str, args: dict, truth: Optional[dict]) -> bool:
        """真值是否已**落地**(命令的效果是否已经在种子状态上体现)

        !与"命令执行成功"是两回事: `torrents/resume` 返回 200 时 qB 可能还没翻状态,
        补刷新读到的还是命令**前**的 paused。此时若把这种旧值发出去, 前端一旦采纳就会
        把行改回「已暂停」, 用户看到"乐观做种, 弹回暂停, 2 秒后变做种"(2026-09-20 真机回归)。
        现行语义(2026-09-20 D2 定案, 旧"扣住回执等真值落地再发"已废弃): 本函数只门控
        truth 事件推送 —— flush_truths 里落地了才推; 回执由 defer_receipt **立即**写且
        **不带 truth**, 不受本函数影响。
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

        !为什么必须直查(2026-09-20 定案):
          `store.by_hash` 来自 `/sync/maindata` **同步快照**, 按 qB 的节奏刷新 —— 真机实测命令后
          要等 6 轮 / **1362ms** 才在上面看到新状态(而命令本身只要 8.4ms), 这个数与
          `sync_interval = 1.5 # 与 qB 自带 WebUI(1500ms)同量级` 几乎重合 ⇒ 滞后来自快照刷新节奏。
          拿快照当"命令后的真值"就会读到命令**前**的旧值 —— 这正是"撤下要等 3s"的根源。
          改走 `torrents/info` 直查, 拿到的是 qB 的**实时**状态。

        !取不到就返回 **None（不回落快照）**: 回落会把"读不到"伪装成"读到了旧值",
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
                        truth[h] = {"kind": self._host.state_kind(t)}
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
            # !正常耗时只打 DEBUG: 每条命令都打, 全进 INFO 会把日志刷满 ——
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
        body["_queued_ts"] = self._clock.now()  # 埋点: 投递时刻, 回执据此拆出排队耗时
        cmd_id = secrets.token_hex(8)
        body["cmd_id"] = cmd_id
        self.commands.put((cmd, body))
        self._host.wake()  # 唤醒主循环立即消费(命令延迟从 0~main_tick 降到近乎 0)
        return {"queued": True, "cmd_id": cmd_id}
