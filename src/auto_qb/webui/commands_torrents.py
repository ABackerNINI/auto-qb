"""TorrentsMixin: 种子/分组动作域命令处理器

move-only 自 commands.py 切出(计划 26-11-02-2342 §07 R5), 未改语义。
"""
import time
from typing import List, Tuple

from ..infra.utils import VIRTUAL_TRACKER_PREFIXES, mask_tracker_url, sanitize_tracker_url

from .commands_common import (
    RC_DEFERRED_PREFIX,
    RC_FAIL_PREFIX,
    RC_UNCONFIRMED_PREFIX,
    REANNOUNCE_BACKGROUND_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    REANNOUNCE_DEFER_EARLY,
    REANNOUNCE_DEFER_MARGIN,
    REANNOUNCE_INACTIVE_SKIP,
    REANNOUNCE_WINDOW_CAP,
    _bulk_call_limits,
    is_deferred_receipt,
    logger,
    reannounce_blocked,
)


class TorrentsMixin:
    @staticmethod
    def _verdict_reannounce(trackers: list, baseline: dict, *, t0: float, tol: float, now: float) -> Tuple[str, str]:
        """判定单个种子强制汇报的结论(纯函数, 无 I/O 无宿主依赖) -> (state, reason)

        state: "confirmed"=已确认成功 / "rejected"=已确认失败(tracker 拒绝) / ""=仍无结论(pending)。
        reason: 结论原因文案; confirmed 可为空或简短证据(聚合回执 ok 桶不出文案), rejected 恒以
        RC_FAIL_PREFIX 开头。

        !!方向语义(事故根源, 不得回潮): next_announce 是 **Unix epoch 绝对秒**(qB 源码
        toSecondsSinceEpoch), 汇报成功 = next **前跳(变大)**; 旧实现把它当倒计时用
        (next 变小视为"被重置 = 成功")方向正好相反 —— "秒/毫秒通用"式臆测同罪。

        !!消解等待模型(plan 26-10-31-2354 D1/D2/D3; 事故 issue 26-10-31-1740): updating(旧版
        API 的 status==3 同义)在 announce 请求**发出前置位**(libtorrent torrent.cpp:3571),
        对成败零信息量 —— **任何模式下 updating 都不构成成功证据**。旧分支②「在途直证」是
        死端口 tracker +1ms 假 ok 的事故根源, 已全域废除; 判定等 updating 消解:
          成功 -> ③″ working 转换 / ③ epoch 前跳(正证据);
          失败 -> ④′ status 4/5/6 + msg(死端口 RST 立即落地, 不等超时/重试);
          消解不了 -> pending 到 deadline 由轮询侧落「未确认」诚实标签。

        逐行判定, 任一行命中即结论(①stopped 在轮询侧直判不进本函数):
          ④′ status in {4,5,6} 且 msg 非空 -> rejected(tracker 拒绝, 唯一可靠否定信号;
             qB 5.x 枚举细分 TrackerError=5/Unreachable=6, 旧版只产 4; **逐行先于③″③判** ——
             libtorrent failed() 按退避改写 next, 顺序反了会把重试排程误判成成功);
             status 4/5/6 但 msg 空 -> 不判败(歧义保守落 pending);
          ③″ status==2 且基线 status 非 None 非 2 -> confirmed(「tracker 状态转为 working」;
             失败路径产不出 working(qB 侧 verified && fails==0 才置 2), 强正证据; 从未联系行/
             曾失败行的唯一成功出口, plan D6);
          ③  (epoch 行) next > b_next + tol -> confirmed(主判据; 判定域限基线 status>=2 且
             b_next 非空, 规避未联系行 epoch 极值假前跳; 基线 min 同向前跳写入 reason 佐证,
             不作必要条件 —— min_announce 在请求发出时即赋值(torrent.cpp:3572), 不是干净的成功信号);
          其余 -> pending("")(含 updating/status==3 在途、min 窗口假瞬态、无变化行)。

        legacy 行(基线行无 next, qB < 5.2)与 epoch 行共用④′③″, 区别只在无③前跳判据
        (成功难证、失败可证); 超时由轮询侧落「未确认(旧版 qB 无 epoch 字段)」, 不假称成功
        —— 与 pitfalls/backend/effect-confirmation.md 的证据门控口径一致, 回执语义只承诺
        诚实标签。

        t0(指令登记时刻)当前判据未直接消费, 为 R1 干扰收窄预案(「前跳距指令 < 一 tick」)保留。
        """
        for t in trackers:
            url = str(t.get("url") or "")
            if url.startswith(VIRTUAL_TRACKER_PREFIXES):
                continue
            b = baseline.get(url) or {}
            b_status = b.get("status")
            b_next = b.get("next")
            b_min = b.get("min")
            status = t.get("status")
            msg = t.get("msg") or ""
            # ④′ 失败(tracker 拒绝, 唯一可靠否定信号; 两个模式同判, msg 空不武断判败;
            #    逐行先于③″③判 —— 失败退避同样前跳 next, 顺序反了会把重试排程误判成成功)
            if status in (4, 5, 6) and msg:
                return "rejected", RC_FAIL_PREFIX + msg
            # ③″ 成功正证据: 状态转为 working(失败路径产不出 working; plan D6; 原 legacy ③′ 收编)
            if status == 2 and b_status is not None and b_status != 2:
                return "confirmed", "tracker 状态转为 working"
            if b_next is None:
                continue  # legacy 行: 无前跳判据(②在途直证已废, plan D3)
            # ③ 主判据: epoch 前跳(判定域限基线 status>=2 且 b_next 非空)
            na = t.get("next_announce")
            if na is not None and b_status is not None and b_status >= 2 and na > b_next + tol:
                reason = f"epoch 前跳 +{na - b_next:.0f}s"
                cur_min = t.get("min_announce")
                if b_min is not None and cur_min is not None and cur_min > b_min + tol:
                    reason += f"(min 同前跳 +{cur_min - b_min:.0f}s 佐证)"
                return "confirmed", reason
        return "", ""

    def _group_empty_receipt(self, cmd_id: str, key: tuple, verb: str) -> None:
        """组命令空兜底(issue 26-10-31-1740): key 形状合法但 store 查无此组 / 成员已全部不在
        快照时, 不发指令之外还必须留痕 —— WARNING 日志 + 显式 error 回执, 不再静默 ok

        修复前 _group_action/_cmd_delete_group 空 hashes 直接返回, drain 侧 RESYNC 通路恒补
        ok 回执 —— 直调 API / 前端视图过期时「点了没反应」且零日志可查。两档文案区分根因:
        key 不在 store.groups = 组已解散或 key 传错(视图过期); 在但成员空 = 成员执行时刻已
        全部不在快照(对齐 _cmd_reannounce_group 既有口径, issue 26-10-06-0028 E-03)。
        """
        reason = "组不存在或已被解散" if key not in self.store.groups else "组内种子不存在或已被删除"
        logger.warning(f"WEB UI | {verb}整组跳过: {reason}({key[0]})")
        if cmd_id:
            self._set_web_result(cmd_id, "error", reason)

    def _group_action(self, key: tuple, method: str, verb: str, cmd_id: str = "") -> None:
        """整组动作单点: 取组内 hash -> 调 qB 方法 -> 一条日志; 空组走 _group_empty_receipt"""
        hashes = self._group_hashes(key)
        if hashes:
            getattr(self.api, method)(torrent_hashes=hashes)
            logger.info(f"WEB UI | {verb}整组({len(hashes)}个种子)")
        else:
            self._group_empty_receipt(cmd_id, key, verb)

    def _torrent_action(self, hash: str, method: str, verb: str, **kwargs) -> None:
        """单种子动作单点: 快照里还在才下发(删后点击静默忽略) -> 一条日志; kwargs 直传 qB 方法"""
        if self.store.get(hash) is None:
            return
        getattr(self.api, method)(torrent_hashes=[hash], **kwargs)
        logger.info(f"WEB UI | 种子 {hash[:8]} {verb}")

    def _cmd_pause_group(self, key: tuple, cmd_id: str = ""):
        self._group_action(key, "torrents_pause", "暂停", cmd_id)

    def _cmd_resume_group(self, key: tuple, cmd_id: str = ""):
        self._group_action(key, "torrents_resume", "开始", cmd_id)

    def _reannounce_active(self, hashes: List[str]) -> List[str]:
        """按快照状态过滤出真正可汇报的种子(第二道闸, 判据见 REANNOUNCE_BLOCKED_STATES)

        !取不到记录(hash 不在 store 快照)时**照发** —— 与判定层「解析不出不误拦」同口径。
        """
        return [h for h in hashes if not reannounce_blocked(self.store.get(h))]

    def _cmd_reannounce_group(self, key: tuple, cmd_id: str = ""):
        hashes = self._group_hashes(key)
        if hashes:
            # 投递收敛(qB 口径: 非活跃的发给引擎也是空转, 只会让确认层白等窗口后落假「未确认」)
            active = self._reannounce_active(hashes)
            if not active:
                if cmd_id:
                    self._set_web_result(
                        cmd_id,
                        "warn",
                        RC_UNCONFIRMED_PREFIX + f"组内 {len(hashes)} 个种子均非活跃, 已跳过",
                    )
                logger.info(f"WEB UI | 强制汇报跳过整组({len(hashes)}个种子均非活跃)")
                return
            self.api.torrents_reannounce(torrent_hashes=active)
            # 发送仅是"已下发指令"; 成功回执由 tracker 确认跟踪器在后续 tick 写入
            baseline, epoch_mode = self._trackers_baseline(active)
            self._register_reannounce_pending(cmd_id, active, baseline, epoch_mode)
            logger.info(
                f"WEB UI | 强制汇报整组({len(active)}/{len(hashes)}个种子活跃, "
                f"跳过 {len(hashes) - len(active)} 个非活跃), 等待 tracker 确认"
            )
        else:
            # 空 hashes: 组不存在(视图过期 / 直调传错 key)或成员已全部不在快照 —— 统一走空兜底
            # (WARNING 日志 + 显式 error 回执, 文案与判据单点在 _group_empty_receipt;
            # 旧的「仅 cmd_id 时写回执」口径 = issue 26-10-06-0028 E-03, 已收编进兜底)
            self._group_empty_receipt(cmd_id, key, "强制汇报")

    def _cmd_delete_group(self, key: tuple, delete_files: bool = False, cmd_id: str = ""):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_delete(torrent_hashes=hashes, delete_files=delete_files)
            logger.info(f"WEB UI | 删除整组({len(hashes)}个种子, delete_files={delete_files})")
        else:
            self._group_empty_receipt(cmd_id, key, "删除")

    def _cmd_pause_torrent(self, hash: str):
        self._torrent_action(hash, "torrents_pause", "暂停")

    def _cmd_resume_torrent(self, hash: str):
        self._torrent_action(hash, "torrents_resume", "开始")

    def _cmd_reannounce_torrent(self, hash: str, cmd_id: str = ""):
        rec = self.store.get(hash)
        if rec is None:
            # 种子已不存在: 无法汇报, 直接给失败回执(删除流程据此不删除)
            if cmd_id:
                self._set_web_result(cmd_id, "error", "种子不存在或已被删除")
            return
        if reannounce_blocked(rec):
            # 第二道闸(与 _cmd_reannounce_group 同判据): 前端 reannouncePlan 已收敛投递集合,
            # 走到这里说明"渲染到点击之间状态变了"或其它调用方直连端点 —— 不发指令, 给显式回执。
            if cmd_id:
                self._set_web_result(cmd_id, "warn", RC_UNCONFIRMED_PREFIX + REANNOUNCE_INACTIVE_SKIP)
            logger.info(f"WEB UI | 强制汇报跳过种子 {hash[:8]}: 非活跃(state={rec.state})")
            return
        self.api.torrents_reannounce(torrent_hashes=[hash])
        baseline, epoch_mode = self._trackers_baseline([hash])
        self._register_reannounce_pending(cmd_id, [hash], baseline, epoch_mode)
        logger.info(f"WEB UI | 强制汇报种子 {hash[:8]}, 等待 tracker 确认")

    def _register_reannounce_pending(self, cmd_id: str, hashes: List[str], baseline: dict, epoch_mode: bool) -> None:
        """登记汇报确认跟踪: 全部种子出结论(成功/失败/未确认)后聚合写该 cmd_id 的回执

        item 形状(消费方在 runtime.check_pending):
          done      是否已出结论
          status    结论桶: "ok"(confirmed) / "error"(rejected) / "warn"(未确认·停止/超时、已受理·推迟)
          reason    结论原因文案(聚合回执「前 3 条原因」的来源; ok 桶可为空)
          baseline  该种子基线 {url: {status, updating, next, min}}(形状见 _trackers_baseline)
          epoch_mode 该种子是否按 epoch 语义判定(D3, 随基线探测)
          t0        指令登记时刻(秒)
          deadline  item 级确认窗口截止期 = t0 + min(max(TIMEOUT, min_e - t0 + MARGIN), CAP);
                    min_e 为该种子 real 行基线 min 的最大值(无/缺为 0) —— 截止期从 entry 级
                    单一下沉到 item 级, 组内混合推迟/立即种子各自算账。

        注册时两个立即结论(不再进轮询):
          (a) store 快照 state_enum.is_stopped -> done+warn「未确认: 种子已停止...」
              (qB 对停止种子静默 no-op, 免白等窗口)。
              !投递面已收敛(前端 reannouncePlan + 后端 _reannounce_active 都不再投非活跃目标),
              故本支从"常规路径"退化成**竞态兜底**: 只有"过滤判活跃 -> 引擎执行前/注册前该种子
              转为停止"这一瞬态才会命中。保留不删 —— 它是确认层唯一的自洽出口, 删掉等于把
              竞态推回"白等 600s 后报未确认"。同类兜底还有 runtime.check_pending 的 item 级
              stopped 直判(那条仍是常规路径: 投递后用户在窗口内手动暂停)。
          (b) epoch 模式且 min_e - t0 > DEFER_EARLY -> done+warn「已受理: 推迟至 HH:MM」(D1
              早回执), 并把该种子登记进 web.reannounce_background(后台达 min_e 后核实, 只落日志;
              S0 实证 min 过期前 updating 是假瞬态, 不能进轮询判定)。
        """
        if not cmd_id:
            return  # 无回执需求的调用(直接构造 manager 的场景): 只发指令不跟踪
        t0 = time.time()
        items = {}
        deferred = {}
        for h in hashes:
            rows = baseline.get(h) or {}
            min_e = 0.0
            for row in rows.values():
                m = row.get("min")
                if m is not None and m > min_e:
                    min_e = float(m)
            deadline = t0 + min(
                max(REANNOUNCE_CONFIRM_TIMEOUT, min_e - t0 + REANNOUNCE_DEFER_MARGIN), REANNOUNCE_WINDOW_CAP
            )
            item = {
                "done": False,
                "status": "",
                "reason": "",
                "baseline": rows,
                "epoch_mode": bool(epoch_mode),
                "t0": t0,
                "deadline": deadline,
            }
            rec = self.store.get(h)
            if rec is not None and rec.state_enum.is_stopped:
                item["done"], item["status"] = True, "warn"
                item["reason"] = RC_UNCONFIRMED_PREFIX + "种子已停止, qB 静默忽略强制汇报"
            elif epoch_mode and min_e - t0 > REANNOUNCE_DEFER_EARLY:
                item["done"], item["status"] = True, "warn"
                # 推迟文案拼接: 常量稳定头 + min_e 本地时刻 HH:MM + 固定尾(§3.4, 拼接规则见常量组注释)
                item["reason"] = (
                    RC_DEFERRED_PREFIX + time.strftime("%H:%M", time.localtime(min_e)) + "(后台继续核实, 结果见日志)"
                )
                deferred[h] = {"min_e": min_e, "baseline": rows, "epoch_mode": bool(epoch_mode), "t0": t0}
            items[h] = item
        self.web.reannounce_pending[cmd_id] = {"items": items}
        if deferred:
            bg = self.web.reannounce_background
            for h, ent in deferred.items():
                while len(bg) >= REANNOUNCE_BACKGROUND_MAX:
                    oldest = next(iter(bg))
                    del bg[oldest]
                    logger.warning(f"WEB UI | 汇报后台核实队列已满({REANNOUNCE_BACKGROUND_MAX}), 丢弃最旧: {oldest[:8]}")
                bg[h] = ent

    def _cmd_delete_torrent(self, hash: str, delete_files: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_delete(torrent_hashes=[hash], delete_files=delete_files)
            logger.info(f"WEB UI | 删除种子 {hash[:8]}(delete_files={delete_files})")

    def _cmd_recheck_torrent(self, hash: str, cmd_id: str = ""):
        """WEB UI 命令: 重新校验单发 —— 经 ops 层提交(在途互斥 R1 + 在途登记), handler 只做回执映射

        ops 拒绝(校验进行中)时回执 error 带自解释文案; 种子不在快照给显式 error
        (与 reannounce_torrent 同口径, 旧版静默无回执易被误读为已执行)。
        """
        if self.store.get(hash) is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "种子不存在或已被删除")
            return
        r = self.ctx.ops.recheck(hash, source="web")  # plan kernel-module-refactor P4: 改走 ctx.ops
        if r.is_ok or r.is_pending:
            if cmd_id:
                self._set_web_result(cmd_id, "ok")
            logger.info(f"WEB UI | 重新校验种子 {hash[:8]}")
        else:
            if cmd_id:
                self._set_web_result(cmd_id, "error", r.message)
            logger.info(f"WEB UI | 重新校验拒绝 {hash[:8]}: {r.message}")

    def _cmd_skip_check_torrent(self, hash: str, cmd_id: str = "", force: bool = False):
        """WEB UI 命令: 右键跳检 —— 经 ops 层执行四阶段(与规则跳检同闸门/同去重/天然串行)

        阻塞 ~6s(删除->轮询->重加), 期间其它命令排队 —— 与规则跳检执行时现状一致;
        拒绝(今日已跳检过/种子已被移除/部分下载)回执 error 带自解释文案。
        force(plan 26-10-05-0314 S2): 透传 ops.skip_check —— 仅豁越 cls=force 的未过闸门
        (G5/G7 瞬态), cls=blocked 一律硬拒(即使带了 force); 缺省 False 行为零变化。
        """
        r = self.ctx.ops.skip_check(hash, source="web", force=force)  # plan kernel-module-refactor P4: 改走 ctx.ops
        if r.is_ok:
            if cmd_id:
                self._set_web_result(cmd_id, "ok")
            logger.info(f"WEB UI | 右键跳检完成 {hash[:8]}")
        else:
            if cmd_id:
                self._set_web_result(cmd_id, "error", r.message)
            logger.info(f"WEB UI | 右键跳检未执行 {hash[:8]}: {r.message}")

    def _cmd_skip_check_precheck(self, hashes=None, cmd_id: str = ""):
        """WEB UI 命令: 跳检预检(只读 dry-run, 计划 26-10-05-0314 S2) —— 转发 ops.skip_check_precheck
        并聚合回执, 判定数据经 truth 字段随 cmd 通道带出(前端 waitCmd 的既有数据位)

        ops 侧零副作用(T20): 不写 state、不 prune、无 qB 写 API —— 本 handler 只聚合计数,
        不触碰任何闸门/去重状态。回执形状: truth={results: [{hash, name, cls, reasons}],
        summary: {ok, force, blocked}}(summary 按单 hash 总 cls 计数, 与 ops 单条 cls 同名);
        未知 hash 透传 ops 的 gone/blocked verdict, 不改写不截断。
        """
        req = [str(h) for h in (hashes or []) if h]
        results = self.ctx.ops.skip_check_precheck(req)
        summary = {"ok": 0, "force": 0, "blocked": 0}
        for item in results:
            summary[item["cls"]] = summary.get(item["cls"], 0) + 1
        if cmd_id:
            self._set_web_result(cmd_id, "ok", truth={"results": results, "summary": summary})
        logger.info(
            f"WEB UI | 跳检预检({len(req)}个): 可跳检 {summary['ok']} / 可强制 {summary['force']} / 禁止 {summary['blocked']}"
        )

    def _cmd_relocate_precheck(self, hashes=None, location: str = "", cmd_id: str = ""):
        """WEB UI 命令: 整组迁移预检(只读 dry-run, 计划 26-10-18-1604 P2) —— 转发
        ctx.relocate.relocate_precheck 并聚合回执, 判定数据经 truth 字段随 cmd 通道带出

        ops 侧同款只读承诺(T20): 模块侧不写 state、无 qB 写 API —— 本 handler 只聚合计数。
        回执形状: truth={results: [逐组 item / gone 逐条], summary: {ok, confirm, blocked}}
        (summary 按单条 cls 计数, cls 命名与跳检预检同族: ok/confirm/blocked, confirm =
        需用户在确认框显式点头 —— 目录别名/长路径校正提议)。
        """
        req = [str(h) for h in (hashes or []) if h]
        results = self.ctx.relocate.relocate_precheck(req, location or "")
        summary = {"ok": 0, "confirm": 0, "blocked": 0}
        for item in results:
            summary[item["cls"]] = summary.get(item["cls"], 0) + 1
        if cmd_id:
            self._set_web_result(cmd_id, "ok", truth={"results": results, "summary": summary})
        logger.info(
            f"WEB UI | 迁移预检({len(req)}个): 可迁 {summary['ok']} / 需确认 {summary['confirm']} / 拒绝 {summary['blocked']}"
        )

    def _cmd_relocate_precheck_add(self, save_path: str = "", name: str = "", cmd_id: str = ""):
        """WEB UI 命令: 添加种子落点预检(§3.6.1, 只读) —— 转发 ctx.relocate.precheck_add

        回执形状: truth=单 item({cls, requested_path, actual_path, volume_free, reasons, notes});
        confirm 时前端弹「请求路径 -> 实际落点 -> 卷剩余」二次确认。
        """
        result = self.ctx.relocate.precheck_add(save_path or "", name or "")
        if cmd_id:
            self._set_web_result(cmd_id, "ok", truth=result)
        logger.info(
            f"WEB UI | 添加预检 {name or '<空>'} @ {save_path or '<空>'}: {result['cls']}" +
            (f" -> {result.get('actual_path')}" if result.get("actual_path") else "")
        )

    def _cmd_relocate_cancel(self, job_id: str = "", confirm: bool = False, cmd_id: str = ""):
        """WEB UI 命令: 撤销迁移(§3.5.1, 唯一会移动数据的旁支) —— 转发 ctx.relocate.relocate_cancel

        两步同模块口径: confirm 缺省/False 只回成本(cls=confirm, 带 cost: 字节数 + 从哪搬回哪),
        不碰数据; confirm=True 才删链接 + setLocation(mover, src)。回执形状: truth=模块返回的
        单 item({cls, cost, job_id, phase} 或 blocked 带 reasons)。
        """
        result = self.ctx.relocate.relocate_cancel(job_id or "", cost_confirmed=bool(confirm))
        if cmd_id:
            self._set_web_result(cmd_id, "ok", truth=result)
        logger.info(
            f"WEB UI | 撤销迁移 {job_id or '<空>'}(确认={bool(confirm)}): {result['cls']}" +
            (f" | 成本 {result.get('cost', {}).get('bytes')} 字节" if result.get("cost") else "")
        )

    def _cmd_super_seeding(self, hash: str, enable: bool = False):
        self._torrent_action(hash, "torrents_set_super_seeding", f"超级做种({'开' if enable else '关'})", enable=enable)

    def _cmd_force_start(self, hash: str, enable: bool = False):
        self._torrent_action(hash, "torrents_set_force_start", f"强制开始({'开' if enable else '关'})", enable=enable)

    def _relocate_receipt(self, cmd_id: str, items: list, what: str) -> None:
        """整组迁移执行回执(三入口共用): 判定数据经 truth 带出, 形态同迁移预检

        cls: started=已发起(qB 在搬) / skip=已在目标位置(幂等) / confirm=需二次确认
        (目录别名「以后新增也落新位置」)/ blocked=闸门拒绝。blocked 给 error 回执并带
        首条自解释原因, confirm 给 ok + truth(由前端据 summary 开确认框)。
        """
        summary = {"started": 0, "skip": 0, "confirm": 0, "blocked": 0}
        for it in items:
            summary[it.get("cls", "blocked")] = summary.get(it.get("cls", "blocked"), 0) + 1
        if not cmd_id:
            return
        if summary["blocked"] and not (summary["started"] or summary["skip"] or summary["confirm"]):
            reason = ""
            for it in items:
                for r in it.get("reasons") or []:
                    reason = r.get("text") or reason
                    break
                if reason:
                    break
            self._set_web_result(cmd_id, "error", reason or "整组迁移被闸门拒绝", truth={"results": items, "summary": summary})
            return
        self._set_web_result(cmd_id, "ok", truth={"results": items, "summary": summary})
        logger.info(
            f"WEB UI | {what}: 已发起 {summary['started']} / 幂等跳过 {summary['skip']} / 需确认 {summary['confirm']} / 拒绝 {summary['blocked']}"
        )

    def _relocate_armed(self) -> bool:
        """整组迁移是否已武装(三入口接线判据): 开 + 模块在 + qB 客户端在"""
        mod = getattr(self.ctx, "relocate", None)
        if mod is None:
            return False
        if not getattr(getattr(self.ctx.config, "relocate", None), "enabled", False):
            return False
        return self.ctx.api is not None and self.ctx.api.client is not None

    def _cmd_set_torrent_location(self, hash: str, location: str = "", cmd_id: str = "", confirm: bool = False):
        if self.store.get(hash) is None:
            return
        if not location:
            raise ValueError("location 不能为空")
        if self._relocate_armed():
            # 开: 走整组迁移闸门 + 执行体(字节一律由 qB 搬, auto-qb 只建别名与收尾)
            items = self.ctx.relocate.relocate_execute([hash], location, confirm=bool(confirm), origin="web")
            self._relocate_receipt(cmd_id, items, f"移动位置(整组迁移) {hash[:8]}")
            return
        self.api.torrents_set_location(torrent_hashes=[hash], location=location)
        # 组键含 save_path: 移动后下轮同步会按新 save_path 重归组(旧组解散/新组建立), 属预期行为
        logger.info(f"WEB UI | 种子 {hash[:8]} 移动保存路径 -> {location}(将按新路径重归组, 属预期)")

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

    def _cmd_remove_tracker(self, hash: str, url: str = ""):
        if self.store.get(hash) is None:
            return
        if not url:
            raise ValueError("url 不能为空")
        # S3 删除改道(plan 26-10-07-0055): 入参 url 是前端所持 mask 值(详情 API 只回 mask),
        # 而 qB 按原文精确匹配 —— 当场重取完整条目列表(运行在主循环线程内, 不破单一写线程假设),
        # 跳虚拟条目后逐条 mask 比对, 恰 1 命中才取该条原文传 qB; 原文是局部变量, 出作用域即弃,
        # 不进缓存/不落盘/不进响应/不进日志。命中 0 或 >=2 一律报错, 绝不猜。
        hits = []
        for t in (self.client.torrents_trackers(hash) or []):
            original = str(t.get("url") or "")
            if original.startswith(VIRTUAL_TRACKER_PREFIXES):
                continue
            if mask_tracker_url(original) == url:
                hits.append(original)
        if len(hits) != 1:
            raise ValueError("未找到该 tracker，请刷新后重试")
        self.api.torrents_remove_trackers(torrent_hash=hash, urls=[hits[0]])
        logger.info(f"WEB UI | 种子 {hash[:8]} 移除 tracker: {sanitize_tracker_url(url)}")

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
    # extra = {"tags": [...], "category": str}: add_tags/remove_tags/set_category 的载荷,
    # 其余动作忽略它(签名统一 4 参, 免得逐动作特判)。add_tags/remove_tags 的 tags 已在
    # 入口校验非空; set_category 的 category 允许空串(qB 语义 = 清除分类), None 时不会走到。
    # !recheck / skip_check 不在此表: 两者都走 _bulk_*_via_ops 逐个经 ops 层提交(R1 第二入口 /
    #   计划 26-10-02-1955 W3 —— recheck 在途过滤 + 登记 + 聚合回执; skip_check 逐 hash 串行,
    #   R2 复核/同日去重/备份/打标全在 ops 层原样生效; 直调 API 会给批量路径留下旁路)。
    # !limits/location(计划 26-10-02-1955 W2): qbapi 原生收 hash 列表, 一次调用传全 hashes,
    #   单次调用天然串行(单写线程); limits 只调有值方向(extra 里 None = 该方向不改, D3 拍板),
    #   快照同步(update_torrent_fields)在 QbApi 写方法内单点完成。
    _BULK_ACTIONS = {
        "pause":
            lambda api, hashes, delete_files, extra: api.torrents_pause(torrent_hashes=hashes),
        "resume":
            lambda api, hashes, delete_files, extra: api.torrents_resume(torrent_hashes=hashes),
        "delete":
            lambda api, hashes, delete_files, extra: api.
            torrents_delete(torrent_hashes=hashes, delete_files=delete_files),
        "add_tags":
            lambda api, hashes, delete_files, extra: api.torrents_add_tags(tags=extra["tags"], torrent_hashes=hashes),
        "remove_tags":
            lambda api, hashes, delete_files, extra: api.
            torrents_remove_tags(tags=extra["tags"], torrent_hashes=hashes),
        "set_category":
            lambda api, hashes, delete_files, extra: api.
            torrents_set_category(category=extra["category"], torrent_hashes=hashes),
        "limits":
            _bulk_call_limits,
        "location":
            lambda api, hashes, delete_files, extra: api.
            torrents_set_location(torrent_hashes=hashes, location=extra["location"]),
    }

    # 标签/分类动作(种子级): QbApi 侧已同步 store 快照(update_torrent_fields),
    # 走 bulk_torrents 的 RESYNC 补刷新让前端尽快看到新值。
    _TAG_ACTIONS = frozenset({"add_tags", "remove_tags"})

    def _cmd_bulk_torrents(
        self,
        hashes=None,
        action: str = "",
        cmd_id: str = "",
        delete_files: bool = False,
        keys=None,
        tags=None,
        category=None,
        up_limit=None,
        dl_limit=None,
        location=None,
        force: bool = False,
        confirm: bool = False,
    ):
        """WEB UI 命令: 批量操作(单命令批量, 平铺视图多选); 回执由本 handler 聚合写

        - 未知 action / 空 hash 列表 -> error 回执
        - recheck / skip_check 走 ops 层逐个提交(在途互斥+登记 / 跳检四阶段+守卫), 聚合回执带
          跳过与失败计数(_bulk_recheck_via_ops / _bulk_skip_check_via_ops); 其余动作单次 API
          调用传全部 hashes
        - skip_check 门控(计划 26-10-02-1955 W3, D2=是·fail-closed): web.skip_check_menu 关时
          拒单 error 回执(gate 读实时配置, 在任何展开/调用之前)
        - 不在快照中的 hash 跳过(删除守阵), 仍有缺失时回执 error 带缺失计数(部分成功也报错,
          前端可据列表刷新后重试); 全部命中 -> ok
        - API 只调一次: hashes 整体传给既有 api 调用(qB 端点原生接受批量)
        - 组键模式(DLG-02): keys 为分组 key 列表(tuple, Web 层已解码), 逐组展开成员
          (经 _group_hashes 按快照过滤, 级联全部在册成员)并与 hashes 合并去重; 组不存在或
          成员全部不在快照计一个缺失组, 缺失文案与种子缺失分列(纯 hash 模式文案不变, 前端契约保持)
        - 标签/分类动作: add_tags/remove_tags 需非空 tags; set_category 的 category 允许
          空串(清除分类), 未提供(None)才报错 —— 两者由 Web 层按"提供才透传"的同一约定组装
        - 限速/移动动作(计划 26-10-02-1955 W2): limits 只调有值方向(up/dl 传 None = 不改,
          0 = qB 语义的不限速, 合法), Web 层已拦负数; location 需非空路径 —— 缺值在
          handler 同样 error 回执(直投队列绕过路由校验时不得静默无操作)
        """
        req = [h for h in (hashes or []) if h]
        keys = [k for k in (keys or []) if k]
        fn = self._BULK_ACTIONS.get(action)
        # recheck / skip_check 不在 _BULK_ACTIONS(走 ops 层), 放行到 known 展开后分流(见下方分支)
        if fn is None and action not in ("recheck", "skip_check"):
            if cmd_id:
                self._set_web_result(
                    cmd_id, "error", f"未知批量动作: {action}"
                    f"(可选 pause/resume/recheck/skip_check/delete/add_tags/remove_tags/set_category/limits/location)"
                )
            return
        if action == "skip_check" and not self.ctx.config.web.skip_check_menu:
            # D2=是·fail-closed(计划 26-10-02-1955 W3): 菜单隐藏只是 UX, bulk 分派处同样拒单 ——
            # 读实时配置(ctx.config 引用现取, 热重载后立即生效, 不按值持有旧 Config ——
            # pitfalls/backend/hot-reload-held-config.md); rule 源跳检不受影响(gate 只在 web 入口)。
            if cmd_id:
                self._set_web_result(cmd_id, "error", "跳检菜单未启用(配置键 web.skip_check_menu)")
            return
        if not req and not keys:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供任何 hash 或组")
            return
        if action in self._TAG_ACTIONS and not [t for t in (tags or []) if t]:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供标签")
            return
        if action == "set_category" and category is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供分类(空串=清除分类)")
            return
        extra = {
            "tags": [t for t in (tags or []) if t],
            "category": category or "",
            "up_limit": up_limit,
            "dl_limit": dl_limit,
            "location": str(location or "").strip(),
        }
        if action == "limits" and extra["up_limit"] is None and extra["dl_limit"] is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供限速值(留空 = 不修改)")
            return
        if action == "location" and not extra["location"]:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供目标路径")
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
        if action == "recheck":
            # R1 第二入口(plan 26-09-30-0109): 批量 recheck 逐个经 ops 层提交, 不直调 API
            self._bulk_recheck_via_ops(known, cmd_id, missing, len(req), missing_groups, len(keys))
            return
        if action == "location" and self._relocate_armed():
            # 整组迁移开: 批量移动走同一闸门 + 执行体(多选按组拆开逐组判定, §3.2.1)
            items = self.ctx.relocate.relocate_execute(known, extra["location"], confirm=bool(confirm), origin="web")
            self._relocate_receipt(cmd_id, items, f"批量移动位置(整组迁移) {len(known)} 个")
            return
        if action == "skip_check":
            # 批量跳检(计划 26-10-02-1955 W3): 逐 hash 串行经 ops 层四阶段, 不直调 API;
            # force(计划 26-10-05-0314 S2)逐 hash 透传 —— 仅豁越 cls=force 闸门, blocked 照旧硬拒
            self._bulk_skip_check_via_ops(known, cmd_id, missing, len(req), missing_groups, len(keys), force=force)
            return
        if known:
            fn(self.api, known, delete_files, extra)
        msgs = []
        if missing:
            msgs.append(f"{missing}/{len(req)} 个种子不存在或已被删除")
        if missing_groups:
            msgs.append(f"{missing_groups}/{len(keys)} 个组不存在或成员为空")
        if msgs:
            msg = "; ".join(msgs)
            if cmd_id:
                self._set_web_result(cmd_id, "error", msg)
            logger.info(f"WEB UI | 批量 {action}({len(known)}个种子): {msg}")
        else:
            # !pause/resume 是例外(见 is_deferred_receipt): 它们的回执 + 真值登记由 drain 的
            #   defer_receipt 一并完成, handler 这里**不写** —— 否则回执双写, 且会挤掉 drain 的
            #   真值登记(report 26-10-11-2017 §6.2 落点 3)。其余动作仍是 handler 自写回执。
            if cmd_id and is_deferred_receipt("bulk_torrents", {"action": action}):
                self._set_web_result(cmd_id, "ok")
            logger.info(f"WEB UI | 批量 {action}({len(known)}个种子, delete_files={delete_files})")

    # ---------- 批量聚合回执的共用单点(issue webui-bulk-receipt-boilerplate-dup) ----------
    # 批量 recheck / 批量跳检的收口骨架此前各写一遍(缺失文案 + "; ".join + 有文案回 error 否则 ok
    # + 一条日志), 改回执口径要改两处; 两族的**分桶计数**仍各自保留(跳过语义不同: 计数 vs 按原因分桶)。

    def _bulk_missing_msgs(self, missing: int, n_req: int, missing_groups: int, n_keys: int) -> List[str]:
        """批量回执的「缺失」文案段单点(种子 + 组两条; 文案逐字不变)"""
        msgs = []
        if missing:
            msgs.append(f"{missing}/{n_req} 个种子不存在或已被删除")
        if missing_groups:
            msgs.append(f"{missing_groups}/{n_keys} 个组不存在或成员为空")
        return msgs

    def _bulk_receipt(self, cmd_id: str, msgs: List[str], ok_line: str, fail_line: str) -> None:
        """批量回执收口单点: 有异常文案 -> error + fail_line 日志; 全清 -> ok + ok_line 日志

        部分成功也报错(拒绝/跳过计数必须可见)是既有口径, 本单点不改写; ok/fail 两行日志文案
        由调用方给(各自的计数口径不同: recheck 说「提交」, 跳检说「成功」)。
        """
        if msgs:
            msg = "; ".join(msgs)
            if cmd_id:
                self._set_web_result(cmd_id, "error", msg)
            logger.info(f"WEB UI | {fail_line}: {msg}")
            return
        if cmd_id:
            self._set_web_result(cmd_id, "ok")
        logger.info(f"WEB UI | {ok_line}")

    def _bulk_recheck_via_ops(
        self,
        hashes: List[str],
        cmd_id: str,
        missing: int = 0,
        n_req: int = 0,
        missing_groups: int = 0,
        n_keys: int = 0,
    ) -> None:
        """批量 recheck 经 ops 层逐个提交(R1 第二入口): 在途互斥对每个 hash 生效, 聚合回执带跳过计数

        与单发同一提交点(ops_recheck, source="web"): 在途/校验中的 hash 被拒绝并计数,
        不重启其校验; 提交成功的 hash 经 ops 登记在途 -> 决策链 1.5 组内串行化可见。
        回执口径与 bulk 其余动作一致: 任何缺失/跳过/失败都进 error 文案(部分成功也报错,
        拒绝计数必须可见), 全部正常提交才 ok。失败按原因聚合(同因多目标只出一行)。
        """
        ok_n = skip_n = 0
        fail_buckets: dict = {}
        for h in hashes:
            r = self.ctx.ops.recheck(h, source="web")  # plan kernel-module-refactor P4: 改走 ctx.ops
            if r.is_skipped:
                skip_n += 1
            elif r.is_failed:
                fail_buckets[r.message] = fail_buckets.get(r.message, 0) + 1
            else:
                ok_n += 1
        fail_n = sum(fail_buckets.values())
        msgs = self._bulk_missing_msgs(missing, n_req, missing_groups, n_keys)
        if skip_n:
            msgs.append(f"{skip_n} 个校验进行中已跳过")
        for reason, n in fail_buckets.items():
            msgs.append(f"{n} 个发送失败: {reason}")
        self._bulk_receipt(
            cmd_id,
            msgs,
            ok_line=f"批量 recheck(提交 {ok_n} 个种子)",
            fail_line=f"批量 recheck(提交 {ok_n}, 跳过 {skip_n}, 失败 {fail_n})",
        )

    def _bulk_skip_check_via_ops(
        self,
        hashes: List[str],
        cmd_id: str,
        missing: int = 0,
        n_req: int = 0,
        missing_groups: int = 0,
        n_keys: int = 0,
        force: bool = False,
    ) -> None:
        """批量跳检: 逐 hash **异步提交**(ops.skip_submit), 全部终态后聚合写一条回执

        与单发同一提交点(ops._skip_begin): R2 实时复核 / 同日去重(skip_check_day 跨来源共享)/
        备份 / 闸门全部在 ops 层原样生效, 批量只是聚合层 —— 逐 hash 串行**提交**是单写线程假设的
        硬要求(pitfalls/backend/concurrency.md), 禁止并发扇出; 但相位推进不再占用命令 drain:
        每个 hash 只做前置与建 job(毫秒级), 后续由主循环微步调度并行推进(计划 26-10-21-1857 §4/§6)。
        回执在最后一个 job 终态时写入, 前端 waitCmd 拿到的仍是真实结果(只是晚 ~百毫秒), 契约不变。
        force(plan 26-10-05-0314 S2): 逐 hash 透传 —— 仅豁越 cls=force 的未过闸门, blocked 一律硬拒。
        跳过/失败均按原因聚合(同因多目标只出一行); 任何缺失/跳过/失败都进 error 文案(部分成功也报错)。
        """
        skip_buckets: dict = {}  # 跳过原因 -> 计数(dict 保插入序 = 首现序)
        fail_buckets: dict = {}  # 失败原因 -> 计数(同上; 同因多目标只出一行)
        counts = {"ok": 0}
        pending = {"n": 0}

        def finish_if_done() -> None:
            if pending["n"] > 0:
                return
            skip_n = sum(skip_buckets.values())
            fail_n = sum(fail_buckets.values())
            msgs = self._bulk_missing_msgs(missing, n_req, missing_groups, n_keys)
            for reason, n in skip_buckets.items():
                msgs.append(f"{n} 个跳过: {reason}")
            for reason, n in fail_buckets.items():
                msgs.append(f"{n} 个失败: {reason}")
            self._bulk_receipt(
                cmd_id,
                msgs,
                ok_line=f"批量跳检(成功 {counts['ok']} 个种子)",
                fail_line=f"批量跳检(成功 {counts['ok']}, 跳过 {skip_n}, 失败 {fail_n})",
            )

        def on_done(job) -> None:
            """相位机终态回调(主循环线程内): 计数并尝试收口"""
            r = job.result
            if r is not None and r.is_ok:
                counts["ok"] += 1
            elif r is not None and r.is_failed:
                fail_buckets[r.message] = fail_buckets.get(r.message, 0) + 1
            elif r is not None:
                skip_buckets[r.message] = skip_buckets.get(r.message, 0) + 1
            pending["n"] -= 1
            finish_if_done()

        for h in hashes:
            r = self.ctx.ops.skip_submit(h, source="web", force=force, on_done=on_done)
            if r.is_pending:
                pending["n"] += 1
            elif r.is_skipped:
                skip_buckets[r.message] = skip_buckets.get(r.message, 0) + 1
            elif r.is_failed:
                fail_buckets[r.message] = fail_buckets.get(r.message, 0) + 1
        finish_if_done()
