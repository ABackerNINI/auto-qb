"""traffic_sample_mod 拆分件: 采样/块/刷新域 mixin(R5 move-only, 计划 26-11-02-2342 §07)。"""
import logging
import math
from collections.abc import Mapping
from typing import Optional

from ..traffic_store import TrafficV4Store, V4Sample, V4NullRun, V4ZeroRun, v4_block_slots

from .traffic_sample_common import (
    BlockBuffer,
    GLOBAL_SERIES_KEY,
    OpenRun,
    TrafficSamplePoint,
    _GLOBAL_FIELDS,
    _TORRENT_FIELDS,
    _TORRENT_KEY_PREFIX,
    _valid_counter,
)

logger = logging.getLogger("auto_qb.core.modules.traffic_sample_mod")


class _SampleBlocksMixin:
    # ---------- C1 生效与热重载联动(§3.5) ----------

    def _apply_interval(self, conf) -> float:
        """采样间隔现读与联动(C1, §3.5): 返回本轮生效间隔(失配向上取整到 main_tick 下一倍数
        + 告警一次(D5), 不拒采; 整数倍匹配的小数档(如 1.5s 配 main_tick=1.5s)原样生效不
        取整 —— 块头 interval_s 允许小数秒(2026-10-05 起; 修复 1.5/1.5 被整数秒口径静默
        抬到 2s)。
        sample_interval 变化 -> 关闭全部现块(旧块落盘, 新块带新 interval —— 新旧数据分块各有
        interval, A3 根因闭合)+ 记新 effective; main_tick 每轮现读。调用方(采样体)据此把
        下一次到期点推为 now + 返回值 —— issue 26-10-16-0954 起节拍由时钟线自持, 不再经
        「回写 task.interval」表达(采样已不在队列里), 量化口径逐字不变。"""
        main_tick = float(getattr(self._ctx.config, "main_tick", 0.0) or 0.0)
        sample_interval = float(conf.sample_interval)
        if main_tick > 0:
            multiple = math.ceil(sample_interval / main_tick - 1e-9)
            effective = multiple * main_tick  # 整数倍时恰等于配置值; 失配向上取整
        else:
            effective = sample_interval
        effective = max(1.0, effective)  # 块头 interval_s 同下限(配置校验已保证, 防御)
        signature = (sample_interval, main_tick)
        if signature != self._interval_signature:
            self._interval_signature = signature  # 配置对变化: 告警记忆复位(新失配新告警)
            self._ratio_warned = False
        if main_tick > 0 and abs(effective - sample_interval) > 1e-9 and not self._ratio_warned:
            logger.warning(
                f"流量采样 | sample_interval {sample_interval:g}s 非 main_tick {main_tick:g}s 整数倍, "
                f"实际节拍取整为 {effective:g}s(颗粒变粗不断线, 本失配只告警一次)"
            )
            self._ratio_warned = True
        if self._effective_interval is None:
            self._effective_interval = effective  # 进程首轮: 只立基线不开关块
        elif effective != self._effective_interval:
            logger.info(f"流量采样 | 采样率变化 -> {effective:g}s: 关闭全部现块, 新数据分块带新 interval")
            self._effective_interval = effective
            self._close_blocks_for_interval_change()
        return effective

    def _close_blocks_for_interval_change(self) -> None:
        """采样率变化关块(§3.5): 开放块内游程先封口(记录入旧块), 旧块全量落盘并复位 ——
        之后的记录以新 interval 开新块。无开放块的开放游程不封(将成为新块首记录)。"""
        for key in list(self._open_runs):
            buf = self._buffers.get(key)
            if buf is not None and buf.start_epoch is not None:
                self._seal_run(key)
        for key in list(self._buffers):
            if self._buffers[key].start_epoch is not None:
                self._flush_series(key, close_block=True)

    # ---------- 两系列采样 ----------

    def _sample_global(self, server_state, ts: float) -> None:
        """全局系列(恒采): server_state 直采; 缺失/空值走 n 游程不写 0(§03.5);
        零样本(速率 0,0)推进/开启 z 游程(v3 §3.2: 全局恒开, 无数据门)。"""
        getter = server_state.get if isinstance(server_state, Mapping) else (lambda name: None)
        readings = self._read_fields(_GLOBAL_FIELDS, getter)
        if readings is None:
            logger.debug("流量采样 | server_state 关键字段缺失/空值, 本轮全局按 n 游程槽处理")
            self._touch_null_run(GLOBAL_SERIES_KEY, ts)
            return
        dl_rate, up_rate, dl_total, up_total, _dl_session, _up_session = readings
        # 限速历史观测(plan 26-10-12-0535 D2): 主循环采样点顺带对比, 有变化才追加 ——
        # 零新增请求, 天然覆盖一切变化源(曲线模块/WebUI 手改/备用切换/qB 原生界面);
        # 失败内部降级(WARNING 节流不上抛), 不影响本轮流量采样。qB 在线才到这, 字段
        # 未知时记录器内部不猜不记(与 null 游程同理念)
        self._limits_rec.observe(server_state, ts, self._persistence_on)
        if dl_rate == 0 and up_rate == 0:
            self._advance_run(GLOBAL_SERIES_KEY, ts, "z", dl_total, up_total)
            return
        self.sample_series(GLOBAL_SERIES_KEY, ts, *readings)

    def _sample_torrents(self, store, ts: float) -> None:
        """单种系列(活跃过滤): dlspeed>0 or upspeed>0 才产 r; 零速/缺字段进 z/n 游程(§3.2)

        零样本: 已开游程直接推进(无需重读 totals); 无游程经数据门(目录判定 + 进程内缓存)才读字段开游程(totals 缺失不开新游程), 无数据(从未传输)整体
        跳过。null 仅活跃且缺字段时记 n 游程槽(先封开放游程, R2)。只读遍历 by_hash:
        handler 在主循环线程执行, 单线程不变式下迭代期无并发写(黄金法则 5)。
        """
        for record in store.by_hash.values():
            key = _TORRENT_KEY_PREFIX + record.hash
            if record.dlspeed > 0 or record.upspeed > 0:
                readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
                if readings is None:
                    logger.debug(f"流量采样 | 种子 {record.hash} 关键字段缺失/空值, 本轮按 n 游程槽处理")
                    self._touch_null_run(key, ts)
                    continue
                self.sample_series(key, ts, *readings)
                continue
            # 零样本: 已开游程直接推进; 否则数据门为门(目录判定)
            if key in self._open_runs:
                self._advance_run(key, ts, "z")
                continue
            if not self._torrent_has_data(record.hash):
                continue  # 从未传输的种子: 空态, 整体跳过(§3.2)
            readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
            if readings is None:
                continue  # 开新游程需要 totals 快照; 缺失不开(空闲不出 null 槽)
            dl_rate, up_rate, dl_total, up_total, _dl_session, _up_session = readings
            if dl_rate == 0 and up_rate == 0:
                self._advance_run(key, ts, "z", dl_total, up_total)
            else:  # 防御: 活跃过滤与字段读数口径漂移时按非零样本处理, 绝不把活跃读数吞进游程
                self.sample_series(key, ts, *readings)

    def _torrent_has_data(self, infohash: str) -> bool:
        """单种数据门(§3.2): 「种子目录存在且含 >=1 个 .dat」+ 进程内缓存

        缓存: 本进程确认有数据(含已有缓冲 —— 有记录即动过)后恒 True(目录只增), 确认无数据
        后恒 False(数据只由本进程写出), 稳态零目录 IO; dry_run 不做目录判定(零落盘口径)。
        """
        key = _TORRENT_KEY_PREFIX + infohash
        if key in self._has_data or key in self._buffers:
            self._has_data.add(key)
            return True
        if key in self._no_data or not self._persistence_on or not self._ctx.config.data_dir:
            self._no_data.add(key)
            return False
        has = self._get_v4_store().series_has_data(key)
        if has:
            self._has_data.add(key)
        else:
            self._no_data.add(key)
        return has

    @staticmethod
    def _read_fields(fields, getter) -> Optional[tuple]:
        """按 fields 顺序经 getter 读六字段; 任一字段缺失/空值 => None(调用方走 null 点),
        绝不用 0 充数(§03.5)。getter 以字段名取值(dict.get / getattr 皆可)"""
        values = tuple(getter(name) for name in fields)
        if not all(_valid_counter(v) for v in values):
            return None
        return values

    # ---------- 产出缝(v4: buffer 记录) ----------

    def sample_series(
        self, key: str, ts: float, dl_rate, up_rate, dl_total, up_total, dl_session, up_session
    ) -> TrafficSamplePoint:
        """单系列单轮非零采样点产出(plan §03.3「每系列每轮产出采样点」的单一出口)

        触发 (1): 非零样本到达先封开放游程(任意型)再出 r 记录 —— 同轮两记录, 文件序 =
        时间序; 封口把本样本读数作为 z 游程末端锚点交下去(形态 D, plan 26-10-16-1509 §04:
        「处理 z 行时已知末端值」 = 调用方手里这个值)。差分基线推进 + 增量计算(§03.4): 基线为空(重启后首样)只立基线不出增量;
        cur < last 判计数器重置(该点增量记 null + INFO 记录), 绝不产负增量。
        r 记录进 BlockBuffer(v3 §3.1), 随批量 flush 落盘; latest 镜像照常推进。
        """
        self._round_keys.add(key)
        self._seal_run(key, dl_total, up_total)
        base = self._baselines.get(key)
        if base is None:
            dl_inc = None  # 基线为空: 首个采样只立基线不出增量(首窗 null, §03.4)
            up_inc = None
        else:
            dl_inc = self._delta(key, "下载", dl_total, base["dl_total"])
            up_inc = self._delta(key, "上传", up_total, base["up_total"])
        self._baselines[key] = {"dl_total": dl_total, "up_total": up_total}
        point = TrafficSamplePoint(
            ts=ts,
            dl_rate=dl_rate,
            up_rate=up_rate,
            dl_total=dl_total,
            up_total=up_total,
            dl_session=dl_session,
            up_session=up_session,
            dl_inc=dl_inc,
            up_inc=up_inc,
        )
        self.latest[key] = point
        self._append_record(
            key,
            V4Sample(dl_rate=int(dl_rate), up_rate=int(up_rate), dl_total=int(dl_total), up_total=int(up_total)),
            ts,
            ts,
        )
        return point

    def _touch_null_run(self, key: str, ts: float) -> None:
        """null 点(断连 / 关键字段缺失)v3 处理(§3.2): 先封开放游程(z 覆盖不得横跨断连期,
        R2)再推进/开启 n 游程; latest 镜像置全 None 点(§05.2 全局 null 语义), 基线不动。"""
        point = TrafficSamplePoint(
            ts=ts,
            dl_rate=None,
            up_rate=None,
            dl_total=None,
            up_total=None,
            dl_session=None,
            up_session=None,
            dl_inc=None,
            up_inc=None,
        )
        self.latest[key] = point
        self._round_keys.add(key)
        self._advance_run(key, ts, "n")

    def _seal_run(self, key: str, end_dl: Optional[int] = None, end_up: Optional[int] = None) -> None:
        """封口开放游程(v3 §3.2, 各触发共同出口): 封口 = 成为 buffer 记录(不单独落盘;
        跨 flush 滞留内存, 随下次封口或 stop() 落盘)。dt 基准在 _append_record 按块头/
        非块头解析(链上锚点定约, §09.2)。无开放游程零操作。

        形态 D(plan 26-10-16-1509 §04): z 记录的末端锚点(end_dl/end_up)按「调用方手上
        的实测样本 > 游程内最后一条零样本读数 > 开启快照」解析(见 _resolve_run_end), 随
        记录落盘进 z 行末端列并供 agg 摊配; 封口触发共五条路径, 不传参的路径(stop() /
        改间隔关块等)走游程跟踪值兜底。n 游程无观测不携带。"""
        run = self._open_runs.pop(key, None)
        if run is None:
            return
        if run.kind == "n":
            rec = V4NullRun(run_len=run.samples)
        else:
            dl_end, up_end = self._resolve_run_end(run, end_dl, end_up)
            rec = V4ZeroRun(
                run_len=run.samples,
                dl_total=run.dl_total,
                up_total=run.up_total,
                dl_total_end=dl_end,
                up_total_end=up_end,
            )
        self._append_record(key, rec, run.start, run.last_seen)

    @staticmethod
    def _resolve_run_end(run: OpenRun, end_dl: Optional[int], end_up: Optional[int]) -> tuple:
        """z 游程封口末端锚点解析(形态 D 单点): 显式传入(触发封口的实测样本) > 游程内
        最后一条零样本读数 > 开启快照(显式退化)。末端值低于开启快照时按开启快照钳制 ——
        游程内计数器重置的落差不是增长(随后的重置关块逻辑会另立基线), 且保证 z 行末端列
        delta 非负(与冻结列的免费校验同源); 单槽游程(跨度退化)由摊配函数恒取开启快照。"""
        dl0, up0 = run.dl_total, run.up_total
        if end_dl is None or end_up is None:
            end_dl, end_up = run.last_dl_total, run.last_up_total
        if end_dl is None or end_up is None:
            end_dl, end_up = dl0, up0
        return (max(int(end_dl), dl0), max(int(end_up), up0))

    def _seal_all_runs(self) -> None:
        """封全部开放游程(stop() 钩子 / S2b 聚合封口接缝): 逐系列封口成 buffer 记录。"""
        for key in list(self._open_runs):
            self._seal_run(key)

    # ---------- 批量落盘(§3.3) ----------

    def _get_v4_store(self) -> TrafficV4Store:
        """写侧存储惰性构造(路径纯计算不触盘; data_dir 就绪由调用方保证)"""
        if self._v4store is None:
            self._v4store = TrafficV4Store(self._ctx.config.data_dir)
        return self._v4store

    def _close_block_and_reopen(
        self, key: str, rec, start_ts: float, end_ts: float, reset_log: Optional[str] = None
    ) -> None:
        """关块重开骨架单点(issue 26-10-11-0207 R10): 三个触发原因(00:00 硬切 / n-only
        前缀拆块 / 计数器重置)同构 —— _flush_series(close_block=True) 落盘旧块后本记录
        递归走 _append_record(成为新块首); reset_log 非空时先记一条审计(计数器重置专用)。
        调用方紧跟 return(分派在 _append_record 的新块首路径)。"""
        if reset_log:
            logger.info(reset_log)
        self._flush_series(key, close_block=True)
        self._append_record(key, rec, start_ts, end_ts)

    def _flush_series(self, key: str, close_block: bool = False) -> None:
        """单系列批量落盘(§3.3): 单次 open("a") 写待写记录(块头在该块首次 flush 随批写入,
        跨 flush 的同块只写一次头; v4 B 行携带块基线, r/z 行 delta 序列化每批需基线 ——
        block_base = (dl_base, up_base) 随批传)。dry_run / data_dir 为空(防御)静默跳过写,
        内存状态照常推进。OSError 不上抛(观测数据丢失无一致性后果, §01.1), 连续失败只
        告警一次; 失败丢弃本块并复位块状态(dt 链卫生: 避免半块游标错位, 下次成功写起新块)。
        关块(v4 §01 关块状态机): close_block(00:00 硬切 / 改间隔 / 计数器重置 / n 前缀
        拆块)或关块谓词 flush ∧ has_r_row —— 纯空闲块(z/n)跨 flush 开放不关。关块只复位
        块状态, 开放 z/n 游程不动(留内存, 封口后按块首立基线开新块 —— 空闲段盘上恰
        1 条长 z 行, 空闲期主文件零写入)。"""
        buf = self._buffers.get(key)
        if buf is None:
            return
        if buf.records:
            if self._persistence_on and self._ctx.config.data_dir:
                header = None
                if buf.start_epoch is not None and not buf.header_written:
                    header = (buf.start_epoch, buf.interval_s)
                try:
                    self._get_v4_store().append_records(
                        key, buf.date_str, header, tuple(buf.records), (buf.dl_base, buf.up_base)
                    )
                    if header is not None:
                        buf.header_written = True
                    if key.startswith(_TORRENT_KEY_PREFIX):
                        self._has_data.add(key)  # 天文件已落盘: 数据门缓存翻真
                        self._no_data.discard(key)
                    self._persist_warned = False
                except OSError as e:
                    if self._persist_warned:
                        logger.debug(f"流量采样 | {key} 批量落盘失败(持续): {e}")
                    else:
                        logger.warning(f"流量采样 | {key} 批量落盘失败(本批数据丢失, 后续失败不再重复告警): {e}")
                        self._persist_warned = True
                    self._reset_block(buf)
            buf.records = []
            buf.slots = 0
        if close_block or buf.has_r_row:
            # 关块(谓词见 docstring): 块状态整体复位, 之后的记录按块首立基线开新块
            self._reset_block(buf)

    @staticmethod
    def _reset_block(buf: "BlockBuffer") -> None:
        """块状态整体复位 8 字段单点(issue 26-10-11-0207 R10): 落盘失败放弃与关块两处
        逐字同 —— 复位后记录按块首立基线开新块。slots/records 由调用方各自清(两者在
        失败路径不清)。"""
        buf.start_epoch = None
        buf.date_str = None
        buf.header_written = False
        buf.dl_base = None
        buf.up_base = None
        buf.has_r_row = False
        buf.last_dl_total = None
        buf.last_up_total = None

    def _maybe_flush_all(self, conf, now: float) -> None:
        """flush 驱动(§3.3): handler 内计时, now - last_flush >= flush_interval -> 全系列
        批量 flush + 聚合封口 + 种子淘汰(§4.2/§4.5 时点)。进程首轮只记时不提前 flush
        (批量优先; 崩溃窗口 <= flush_interval 不变)。暂停期间 handler 不跑、缓冲滞留,
        恢复后首轮补 flush —— 语义正确。"""
        if self._last_flush is None:
            self._last_flush = now  # 进程首轮: 只记时点不提前 flush(批量优先)
            return
        if now - self._last_flush < conf.flush_interval:
            return
        self._last_flush = now
        self._flush_all_series()
        self._maybe_evict(conf, now)
