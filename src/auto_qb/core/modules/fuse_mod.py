"""FuseModule: 已完成种子下载保险丝(极简版, 计划 26-11-03-0456 S2)

职责边界(§3.1 状态机 / §3.4 动作集合 / §3.5 批量 / §3.7 状态与自愈):
- 每轮刷新收尾(post 相位)只读扫描已加载快照, 零额外 HTTP; 写只发生在状态迁移时;
- armed    : 完成且 dl_limit==0 -> 批量写哨兵限速(config.download_fuse.download_limit);
             写后连续 _REARM_YIELD 拍仍读到 0(写失败或被外部清零, 不可区分)则让位转
             released, 不与用户在 qB 侧的操作互写(§3.7);
- triggered: 连续 confirm_ticks 拍 dlspeed>0 -> 批量 torrents_pause(唯一升级动作);
- released : 显式放行(CAS 恢复哨兵写入前的限速; 不自动 resume); 直到「离开完成态后重新完成
             且 dlspeed==0」才回 armed —— 一次放行覆盖整个补齐过程(§3.6);
- 已有非零限速的完成种子不写、只监控(条目在触发时按需创建, 无 monitor_only 状态);
- 种子消失即删条目; enabled=false 零动作零 qB 写; dry-run 零写零落状态。

S3 标签(§3.8): 固定名来自 config.download_fuse.fuse_tag, 只在状态迁移时写 ——
armed→triggered 与 pause 同拍批量加; 显式放行离开 triggered 与恢复限速同批删;
被外部移除只记一条日志、不自动重加(否则与清理任务互删成环); adopt 时标签兼作
「触发过的持久证据」: 完成 + dl_limit==fence + 暂停 + 带标签 -> 直接重建 triggered,
无标签仍重建 armed。所有标签读写都走 QbApi facade(登记自写期望, 不直连 raw client)。
"""
import logging
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from ..module import AppContext, BaseModule, PhaseEvent

logger = logging.getLogger(__name__)

STATE_KEY = "download_fuse"
STATUS_ARMED = "armed"
STATUS_TRIGGERED = "triggered"
STATUS_RELEASED = "released"

_BATCH = 100  # 批量写上限(§3.5 批 100 —— 常量而非配置键)
# armed 条目补齐哨兵的连续上限: dl_limit==0 无法区分「写失败」与「用户清零」; 连续超限
# 视为外部接管, 让位转 released(§3.7 不写回) —— 常量而非配置键, 与 _BATCH 同口径
_REARM_YIELD = 3
# 这些 state 下即使 progress==1 也不当作「已完成」(计划 §3.1 的排除项)
_NON_COMPLETE_STATES = frozenset(
    ("checkingDL", "checkingUP", "checkingResumeData", "moving", "allocating", "metaDL", "forcedMetaDL")
)
_PAUSED_STATES = frozenset(("pausedDL", "pausedUP", "stoppedDL", "stoppedUP"))


def _is_complete(rec: Any) -> bool:
    """完成态判定: progress==1 + amount_left==0 + 非校验/移动/元数据等过渡态"""
    return (
        float(getattr(rec, "progress", 0.0) or 0.0) >= 1.0 and int(getattr(rec, "amount_left", 0) or 0) == 0 and
        str(getattr(rec, "state", "") or "") not in _NON_COMPLETE_STATES
    )


def _is_paused(rec: Any) -> bool:
    return str(getattr(rec, "state", "") or "") in _PAUSED_STATES


class FuseModule(BaseModule):
    """已完成种子下载保险丝: 三态状态机 + 哨兵限速 + 批量暂停(§3.1/§3.4/§3.5/§3.7)"""
    name = "fuse"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        self._dry_run = False
        # 无 state 条目的非零限速完成种子: 只在本轮内存里记连击(触发时才落条目)
        self._streak: Dict[str, int] = {}
        # 同名标签复用告警只记一次(§3.8 启动一次性; 读快照聚合, 零额外请求)
        self._tag_warned = False

    def sections(self) -> tuple[str, ...]:
        """配置面单点: download_fuse 段(S1 曾临时登记在 impact.KERNEL_SECTIONS, S2 迁出)"""
        return ("download_fuse", )

    def subscribe(self, phases) -> None:
        # 刷新收尾相位: 每轮快照已应用, 此时扫描零额外 HTTP(§04 Q6)
        phases.on("post", self._on_post)

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        self._dry_run = dry_run

    def stop(self) -> None:
        self._streak.clear()

    # ---------- 每拍扫描 ----------

    def _on_post(self, event: PhaseEvent) -> None:
        self._scan(dry_run=bool(event.payload.get("dry_run", False)))

    def _scan(self, dry_run: bool) -> None:
        if dry_run or self._dry_run:
            return
        cfg = self._ctx.config.download_fuse
        if not cfg.enabled:
            return  # enabled=false: 模块不动作、不写 qB、不建 state 域(回滚口径)
        api = self._ctx.api
        store = self._ctx.store
        if api is None or api.client is None or store is None or self._ctx.state is None:
            return

        entries = self._entries()
        self._drop_missing(entries, store)
        tag = cfg.fuse_tag
        self._warn_tag_reuse(store, tag)
        now = time.time()
        to_arm: List[str] = []
        to_adopt: List[str] = []
        to_pause: List[str] = []
        to_tag: List[str] = []

        for h, rec in list(store.by_hash.items()):
            dl_limit = int(rec.dl_limit or 0)
            dlspeed = int(rec.dlspeed or 0)
            ent = entries.get(h)
            if ent is None:
                self._scan_unmanaged(entries, h, rec, dl_limit, dlspeed, cfg, now, to_arm, to_adopt, to_pause, to_tag)
                continue
            self._advance(entries, h, rec, ent, dl_limit, dlspeed, cfg, now, store, to_arm, to_pause, to_tag)

        if to_adopt:
            # 零写: 只按证据重建条目(§3.7); 日志标注 adopt 便于与真武装区分
            logger.info(f"fuse: adopt {len(to_adopt)} 个已完成种子(dl_limit 已是哨兵值, 零写)")
        if to_arm:
            self._write_fence(api, to_arm, cfg.download_limit)
            logger.info(f"fuse: 武装 {len(to_arm)} 个完成种子(哨兵 {cfg.download_limit}B/s)")
        if to_pause:
            for chunk in self._chunks(to_pause):
                api.torrents_pause(torrent_hashes=chunk)
            # §3.5: 每拍最多一条汇总行, 单条明细在 DEBUG
            logger.warning(
                f"fuse: paused {len(to_pause)} torrents (batch) first={','.join(h[:8] for h in to_pause[:3])}"
            )
        if to_tag:
            # §3.8: 与 pause 同拍、按批一次请求; 已在快照带标签的不发请求(集合幂等)
            added = self._apply_tag_add(api, to_tag, tag, entries, store)
            if added:
                logger.warning(f"fuse: 打标签 {tag} 到 {added} 个触发种子(batch) first={','.join(h[:8] for h in to_tag[:3])}")

    def _warn_tag_reuse(self, store: Any, tag: str) -> None:
        """同名标签复用告警(§3.8): 读快照聚合, 不发额外请求; 只记一次"""
        if self._tag_warned:
            return
        self._tag_warned = True
        usage = store.tag_usage()
        if tag in usage:
            logger.warning(f"fuse: 标签 {tag} 已被 {usage[tag]} 个现有种子使用, 复用该定义(保留名, 请勿泛匹配)")

    def _scan_unmanaged(
        self, entries: Dict[str, dict], h: str, rec: Any, dl_limit: int, dlspeed: int, cfg: Any, now: float,
        to_arm: List[str], to_adopt: List[str], to_pause: List[str], to_tag: List[str]
    ) -> None:
        """无 state 条目的种子: 建条目(武装/adopt)或仅监控(§3.7 无 monitor_only 状态)"""
        complete = _is_complete(rec)
        if complete and dl_limit == 0:
            entries[h] = self._new_entry(h, rec, cfg.download_limit, STATUS_ARMED, now)
            to_arm.append(h)
            return
        if complete and cfg.download_limit > 0 and dl_limit == cfg.download_limit:
            # state 丢失自愈(§3.7/§3.8): 标签 = 「触发过」的持久证据
            # 完成 + 哨兵限速 + 暂停 + 带标签 -> 直接重建 triggered(零 qB 写)
            if _is_paused(rec) and cfg.fuse_tag in rec.tags_set:
                entries[h] = self._new_entry(h, rec, cfg.download_limit, STATUS_TRIGGERED, now, orig_limit=0)
                entries[h]["tagged"] = True
                entries[h]["reason"] = "adopt: 完成+哨兵限速+暂停+标签"
            else:
                # 只有哨兵限速证据 -> 按 armed 重建, 不写 qB。
                # pre_limit 未知, 按哨兵语义假定为 0(不限速) —— 放行时才可能写回 0。
                entries[h] = self._new_entry(h, rec, cfg.download_limit, STATUS_ARMED, now, orig_limit=0)
            to_adopt.append(h)
            return
        if complete and dlspeed > 0:
            # 已有非零限速(D07: 不写、只监控): 连击达标才暂停, 此时才建 triggered 条目
            streak = self._streak.get(h, 0) + 1
            if streak >= cfg.confirm_ticks:
                entries[h] = self._new_entry(h, rec, 0, STATUS_TRIGGERED, now, confirm_count=streak)
                entries[h]["reason"] = f"连续 {streak} 拍 dlspeed>0(已有限速 {dl_limit}B/s)"
                self._streak.pop(h, None)
                to_pause.append(h)
                to_tag.append(h)
            else:
                self._streak[h] = streak
            return
        self._streak.pop(h, None)

    def _advance(
        self, entries: Dict[str, dict], h: str, rec: Any, ent: dict, dl_limit: int, dlspeed: int, cfg: Any, now: float,
        store: Any, to_arm: List[str], to_pause: List[str], to_tag: List[str]
    ) -> None:
        """已有条目按状态推进(armed / triggered / released)"""
        status = ent.get("status")
        fence = int(ent.get("fence") or 0)
        if status == STATUS_ARMED:
            if dl_limit == 0:
                # 上次写失败/被外部清零(二者不可区分): 先幂等补齐(成功回写快照后下轮
                # dl_limit==fence, 计数清零); 连续 _REARM_YIELD 拍仍为 0 视为外部接管,
                # 让位转 released 不再互写(§3.7), 由显式放行兜底
                ent["rearm"] = int(ent.get("rearm") or 0) + 1
                if int(ent["rearm"]) >= _REARM_YIELD:
                    ent["status"] = STATUS_RELEASED
                    ent["confirm_count"] = 0
                    ent["was_incomplete"] = False
                    logger.warning(f"fuse: {h[:8]} 连续 {ent['rearm']} 拍 dl_limit==0(写失败或被外部清零), 让位转 released 不再补写")
                    return
                if int(ent["rearm"]) == 1:
                    logger.warning(
                        f"fuse: {h[:8]} dl_limit==0(写失败或被外部清零), 幂等补齐哨兵(连续 {ent['rearm']}/{_REARM_YIELD} 拍, 超限让位)"
                    )
                to_arm.append(h)
            elif fence and dl_limit != fence:
                # 外部改限速: 不写回, 只转 released(§3.7); 之后由显式放行兜底
                ent["status"] = STATUS_RELEASED
                ent["confirm_count"] = 0
                ent["was_incomplete"] = False
                logger.info(f"fuse: {h[:8]} 限速被外部改为 {dl_limit}B/s, 转 released(不写回)")
                return
            else:
                ent["rearm"] = 0  # 哨兵已在场(写成功回流), 补齐计数清零
            if dlspeed > 0:
                ent["confirm_count"] = int(ent.get("confirm_count") or 0) + 1
                if int(ent["confirm_count"]) >= int(cfg.confirm_ticks):
                    ent["status"] = STATUS_TRIGGERED
                    ent["reason"] = f"连续 {ent['confirm_count']} 拍 dlspeed>0"
                    to_pause.append(h)
                    to_tag.append(h)
                return
            ent["confirm_count"] = 0
            return
        if status == STATUS_TRIGGERED:
            # §3.8: 标签被外部移除只记一条日志, 不自动重加(与清理任务互删会成环)
            if ent.get("tagged") and cfg.fuse_tag not in rec.tags_set:
                ent["tagged"] = False
                logger.warning(f"fuse: {h[:8]} 标签 {cfg.fuse_tag} 已被外部移除, 不自动重加(triggered 仍由 state+暂停保证)")
            # 被外部启动(或暂停尚未回流)时再暂停一次; own_write 未回流期不重复下发(幂等)
            if dlspeed > 0 and not _is_paused(rec) and not store.own_write_pending(h, group=False):
                to_pause.append(h)
            return
        if status == STATUS_RELEASED:
            if not _is_complete(rec):
                # 「重新完成」的必要前提: 先观测到离开完成态(补齐/校验会先把 amount_left 抬起来)
                ent["was_incomplete"] = True
            elif ent.get("was_incomplete") and dlspeed == 0 and dl_limit == 0:
                entries[h] = self._new_entry(h, rec, cfg.download_limit, STATUS_ARMED, now)
                to_arm.append(h)
            return
        # 未知状态(历史脏数据): 丢弃后按无条目重新判定
        del entries[h]

    # ---------- 显式放行 ----------

    def release(self, hashes: Optional[Iterable[str]] = None, dry_run: bool = False) -> int:
        """显式放行保险丝条目(CAS 恢复哨兵写入前的限速; 不自动 resume)

        hashes=None = 放行 state 中的全部条目(等价 fuse release --all)。
        CAS: 当前限速仍等于条目记录的哨兵值才写回 orig_limit; 已被外部接管只标记不覆盖。
        dry_run 只打印计划, 不写 qB、不改 state。
        """
        state = self._ctx.state
        if state is None:
            return 0
        domain = state.data.get(STATE_KEY)
        entries = domain.get("entries") if isinstance(domain, dict) else None
        if not isinstance(entries, dict) or not entries:
            return 0
        wanted = None if hashes is None else {str(h).strip().lower() for h in hashes if str(h).strip()}
        targets = [
            h for h, ent in entries.items() if ent.get("status") != STATUS_RELEASED and (wanted is None or h in wanted)
        ]
        if not targets:
            return 0

        api = self._ctx.api
        store = self._ctx.store
        tag = self._ctx.config.download_fuse.fuse_tag
        if not dry_run and (api is None or api.client is None):
            logger.warning("fuse: 未连接 qB, 放行只标记 released 不写限速")
        writes: Dict[int, List[str]] = defaultdict(list)
        to_untag: List[str] = []
        for h in targets:
            ent = entries[h]
            fence = int(ent.get("fence") or 0)
            orig = int(ent.get("orig_limit") or 0)
            rec = store.get(h) if store is not None else None
            cur = int(rec.dl_limit or 0) if rec is not None else None
            if dry_run:
                logger.info(f"fuse: [dry-run] 将放行 {h[:8]} (fence={fence}, 当前={cur}, 恢复={orig})")
                continue
            if api is not None and api.client is not None and fence > 0 and cur == fence and orig != cur:
                writes[orig].append(h)
            else:
                logger.info(f"fuse: 放行 {h[:8]} 仅标记 released(CAS 不成立/无哨兵: fence={fence}, 当前={cur})")
            # §3.8: 离开 triggered 时摘标签(先写限速、后清标签, 下面的写循环在前)
            if ent.get("status") == STATUS_TRIGGERED and rec is not None and tag in rec.tags_set:
                to_untag.append(h)
            ent["status"] = STATUS_RELEASED
            ent["confirm_count"] = 0
            ent["was_incomplete"] = False
        if dry_run:
            return len(targets)
        for limit, group in writes.items():
            for chunk in self._chunks(group):
                api.torrents_set_download_limit(torrent_hashes=chunk, limit=limit)
        restored = sum(len(group) for group in writes.values())
        logger.info(f"fuse: 放行 {len(targets)} 个条目(其中 {restored} 个恢复原限速)")
        if to_untag:
            # 与上面写回侧同口径: 未连接时摘标签也跳过(标签保留, 只标记 released), 不发请求
            if api is None or api.client is None:
                logger.warning(f"fuse: 未连接 qB, 放行跳过摘标签 {tag} {len(to_untag)} 个(标签保留)")
            else:
                removed = self._apply_tag_remove(api, to_untag, tag, entries, store)
                if removed:
                    logger.info(f"fuse: 摘除标签 {tag} {removed} 个(放行)")
        return len(targets)

    # ---------- state / 批写 ----------

    def _entries(self) -> Dict[str, dict]:
        data = self._ctx.state.data
        domain = data.get(STATE_KEY)
        if not isinstance(domain, dict):
            domain = {}
            data[STATE_KEY] = domain
        entries = domain.get("entries")
        if not isinstance(entries, dict):
            entries = {}
            domain["entries"] = entries
        return entries

    def _drop_missing(self, entries: Dict[str, dict], store: Any) -> None:
        for h in list(entries):
            if h not in store.by_hash:
                del entries[h]
                self._streak.pop(h, None)

    @staticmethod
    def _new_entry(
        h: str,
        rec: Any,
        fence: int,
        status: str,
        now: float,
        confirm_count: int = 0,
        orig_limit: Optional[int] = None
    ) -> dict:
        """条目字段集: hash/status/fence/orig_limit/armed_at/confirm_count/rearm/tagged(+released 用的 was_incomplete)"""
        return {
            "hash": h,
            "status": status,
            "fence": int(fence),
            "orig_limit": int(rec.dl_limit or 0) if orig_limit is None else int(orig_limit),
            "armed_at": now,
            "confirm_count": int(confirm_count),
            "rearm": 0,  # 连续补齐哨兵计数(见 _REARM_YIELD); 哨兵回流即清零
            "was_incomplete": False,
            "tagged": False,  # S3: 是否已持有触发标签(外部移除后置 False, 不重加)
        }

    @staticmethod
    def _chunks(items: List[str]) -> Iterable[List[str]]:
        for i in range(0, len(items), _BATCH):
            yield items[i:i + _BATCH]

    def _write_fence(self, api: Any, hashes: List[str], fence: int) -> None:
        for chunk in self._chunks(hashes):
            api.torrents_set_download_limit(torrent_hashes=chunk, limit=fence)

    # ---------- 标签(§3.8, 一律走 QbApi facade) ----------

    def _apply_tag_add(self, api: Any, hashes: List[str], tag: str, entries: Dict[str, dict], store: Any) -> int:
        """批量加触发标签: 快照已带的短路(集合幂等), 其余按批一次请求; 返回实际请求数"""
        pending: List[str] = []
        for h in hashes:
            ent = entries.get(h)
            rec = store.get(h) if store is not None else None
            if rec is not None and tag in rec.tags_set:
                if ent is not None:
                    ent["tagged"] = True
                continue
            pending.append(h)
        for chunk in self._chunks(pending):
            api.torrents_add_tags(tags=[tag], torrent_hashes=chunk)
        for h in pending:
            ent = entries.get(h)
            if ent is not None:
                ent["tagged"] = True  # facade 已把 tags_add 合并进快照并登记自写期望
        return len(pending)

    def _apply_tag_remove(self, api: Any, hashes: List[str], tag: str, entries: Dict[str, dict], store: Any) -> int:
        """批量摘触发标签(只摘快照里真有的, 外部已移除的不发请求); 返回实际请求数"""
        pending: List[str] = []
        for h in hashes:
            rec = store.get(h) if store is not None else None
            if rec is None or tag not in rec.tags_set:
                continue
            pending.append(h)
        for chunk in self._chunks(pending):
            api.torrents_remove_tags(tags=[tag], torrent_hashes=chunk)
        for h in pending:
            ent = entries.get(h)
            if ent is not None:
                ent["tagged"] = False
        return len(pending)
