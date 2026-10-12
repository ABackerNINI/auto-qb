"""traffic_limits: qB 全局限速历史(记录器 + 读侧, plan 26-10-12-0535 §3-D3′/D3″)

流量图限速虚线从「拉取那一刻的当前值画满整窗」改为「按限速历史逐时段分段」—— 每段画在
各自时间区间内, 反映当时真实生效的 qB 全局限速; 缺记录的区间不画线、不猜测(D5)。本模块
收记录器(写侧)与读侧(窗口事件装配 + 解析缓存)两件, 落点在 qb-traffic-v4/limits/。

【事件语义】(D1/D2 拍板):
- 记录值 = 采样时刻 server_state 读到的**实际生效值**(上/下行分开, bytes/s, 0 = 不限速);
  不记限速曲线目标值 —— 手动保护跳过时目标并未写进 qB, 记目标会制造新的失真。备用限速
  生效期间读到的即生效值(qB server_state 的 dl_rate_limit/up_rate_limit 随备用切换给出
  实际值), 事件序列如实反映切回切出。
- 挂点 = 主循环流量采样点(traffic_sample_mod._sample_global 顺带调用), 每轮对比内存缓存
  的上一记录值, **有变化才追加事件**; 单线程(黄金法则 5)、零新增请求, 天然覆盖一切变化源
  (限速曲线模块 / WebUI 手动覆盖 / 备用限速切换 / qB 原生界面手改)。变化粒度 = 采样间隔。
- 字段未知(键缺失/None)本轮不记录不推进基线(与采样器 null 语义同理念: 不猜)。

【存储形态】(D3 两轮裁定终值 = 分天):
    <data_dir>/qb-traffic-v4/limits/<YYYY-MM-DD>.dat
  目录与流量数据一致(v4_root_dir 下), 天文件名与 v4 天文件同款日期格式(单点 V4_DATE_FORMAT)。
  limits/ 不是系列目录(v4_rel_dir_to_key 只认 global/ 与 torrents/<hash>), 系列扫描与整目录
  淘汰天然跳过它。**不淘汰**(保留与流量图最大保存范围 day/month 聚合行全保留对齐, D3;
  正常密度一天几十条, 体量天然有界)。行格式 = 追加写纯文本 CSV:
      <epoch_s>,<up_bytes_s>,<down_bytes_s>
  无头行无 key 行(单文件单写者、无换代语义, v4 头行门闩需求不存在; 未来改格式按行解析
  失败即豁免, 自然兼容)。
- 00:00 硬切新天文件(本地日界, 与 v4 关块同款触发), **新天首行 = 基线 carry**(上一生效值
  无条件写入, 值没变也写)—— 单看一个天文件自洽可读, 读侧拼接无需回溯前一天文件。
- 重启去重: 启动首轮若与当日文件末条相同则跳过(不产生假事件); 不同(或无文件)则写事件
  (记录起点 = 首次启用后的首个采样)。
- 失败降级: 追加 OSError -> WARNING(节流)+ 本轮不记**不上抛** —— 记录器是观测面, 丢失 =
  事件缺口, 读侧「延续语义」自然兜住; 不因它挂主循环。失败轮**不推进内存基线**(下一轮
  重试, 值不丢; 事件时刻延迟到恢复后首个采样, 误差 <= 停机时长, plan §5 已知边界)。
- 撕裂尾半行(崩溃残留)读侧跳过(与 traffic_store 坏行豁免同理念); 病态翻转(外部脚本级
  高频改限速)走**常量阈值 WARNING + 节流**护栏(照 _BAD_LINE_WARN_* 先例, 只告警不删数据
  —— 删了违背保留对齐语义)。

【读侧】(D3″): 按窗口日期集合只读涉及天文件(24h 窗常态 3 个 —— 多看一天供合成首事件
窥前文件末行 carry; 与流量 raw 段同形状), mtime_ns+size 键控解析缓存(照 V4DayCache 形状:
文件没变零解析, all 窗口不因总历史变大而多花解析)。装配口径:
    limits: [[ts, up, down], ...]  # 窗口内事件按时间升序
  首元素 = **合成事件**: 窗口起点时刻的生效值(<= t0 的最近事件, ts 记为 t0)—— 前端据此
  直接构段(段起点 = 事件 ts, 末段延伸到 now); 记录起点晚于窗口起点则首元素从首个真实
  事件开始, 起点前不给值(D5); 无任何记录 = 空列表。同值连续事件(跨天 carry 与前一值
  相同)在装配层去重 —— 线连续不分段, 段边界只出现在真实值变化处。

【线程模型】记录器只在主循环线程调用(黄金法则 5, 无锁); 读侧被 Web 线程并发调用 ——
缓存表用锁保护、解析(慢段)在锁外进行(并发重复解析无害, 后写胜; V4DayCache 同款)。
写侧(主循环)与读侧(Web)对同一文件无锁竞争: 最坏读到半行由撕裂尾豁免兜住。
"""
import logging
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping
from typing import Optional

from .traffic_store import DAT_SUFFIX, _validate_date, v4_epoch_date_str, v4_root_dir, v4_window_dates

logger = logging.getLogger(__name__)

#: 限速历史目录名(相对 qb-traffic-v4/ 根; 非系列目录, 系列扫描/淘汰天然跳过)
LIMITS_DIR_NAME = "limits"

#: 同一文件追加失败告警的最小间隔(秒, 节流; 对齐 traffic_store._BAD_LINE_WARN_GAP_S)
_LIMITS_WARN_GAP_S = 3600.0

#: 病态翻转护栏阈值(单天事件数; 常量非配置键): 正常密度 = 跨天 carry 1 条/天 + 真实限速
#: 变化(曲线档位/手动/备用切换, 每天个位数到几十条); 超过它基本只可能是外部脚本按采样
#: 节拍高频翻转。只 WARNING 不删数据(删了违背保留对齐语义), 图面阶梯本身即诊断信息。
_LIMITS_DAILY_EVENT_WARN = 2000

#: 护栏告警节流间隔(秒)
_LIMITS_GUARD_WARN_GAP_S = 3600.0

#: 解析缓存条目上界(LRU; 天文件体量小, 按条目数逐出即可 —— 一年 366 条, 4096 约 11 年)
_LIMITS_CACHE_MAX_ENTRIES = 4096


def limits_day_path(data_dir: str, date_str: str) -> str:
    """本地日期串 -> 限速天文件路径(<data_dir>/qb-traffic-v4/limits/<YYYY-MM-DD>.dat);
    日期串非法 fail-fast(口径同 v4_day_file_path)"""
    _validate_date(date_str)
    return os.path.join(v4_root_dir(data_dir), LIMITS_DIR_NAME, date_str + DAT_SUFFIX)


def parse_limits_day_text(text: str) -> tuple:
    """限速天文件文本 -> 事件元组(纯函数; 升序, 与文件序一致)

    每行 3 列非负整数 <epoch_s>,<up>,<down>; 坏行(列数/非数值/负数)整行跳过(游标语义
    不存在 —— 每行自洽, 不传播); 撕裂尾半行(末行无换行)丢弃不解析(与 traffic_store
    坏行豁免同理念 —— 正常崩溃残留, 下一轮追加会先补换行)。无头行门闩(见模块 docstring)。
    返回 tuple[(ts, up, down), ...](文件序 = 时间序)。
    """
    events: list = []
    if not text:
        return ()
    lines = text.split("\n")
    if lines and not text.endswith("\n"):
        lines = lines[:-1]  # 撕裂尾半行: 丢弃(崩溃残留, 写侧下轮追加前已补换行)
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(",")
        if len(parts) != 3:
            continue
        try:
            ts = int(parts[0])
            up = int(parts[1])
            down = int(parts[2])
        except ValueError:
            continue
        if ts < 0 or up < 0 or down < 0:
            continue  # 负数列 = 损坏, 整行豁免
        events.append((ts, up, down))
    return tuple(events)


def _read_day_last_event(data_dir: str, date_str: str) -> Optional[tuple]:
    """读单天文件末条事件(记录器重启去重用; 一次性直读不走缓存): 缺失/空/读失败 = None"""
    try:
        with open(limits_day_path(data_dir, date_str), "r", encoding="utf-8", errors="replace") as f:
            events = parse_limits_day_text(f.read())
    except OSError:
        return None
    return events[-1] if events else None


class SpeedLimitRecorder:
    """限速历史记录器(D2): 主循环线程独占, 采样点顺带对比, 有变化才追加

    状态(进程内, 不落盘): _last = 上一记录生效值(up, down)/None(未立基线); _last_date =
    上次成功写入的日期串(00:00 硬切判据)。失败轮两者都不推进(下一轮重试, 值不丢)。
    data_dir 为空(防御, 对齐 _feature_on 语义)= 记录器整体禁用(observe 零操作)。
    """
    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir or ""
        self._last: Optional[tuple] = None
        self._last_date: Optional[str] = None
        self._bootstrapped = False
        self._oswarn_ts = 0.0
        self._guard_ts = 0.0
        self._day_events = 0
        self._day_events_date: Optional[str] = None

    def observe(self, server_state, ts: float, persistence_on: bool = True) -> None:
        """采样点观测(主循环线程): 读生效值 -> 跨天硬切/carry -> 变化才追加

        persistence_on=False(dry_run)整体跳过 —— 观测写盘属真实副作用(与采样器 dry_run
        零落盘口径一致); 不推进任何内存状态(恢复真实运行后由重启去重口径对齐文件尾)。
        """
        if not self._data_dir or not persistence_on:
            return
        getter = server_state.get if isinstance(server_state, Mapping) else (lambda name: None)
        up = _pick_limit(getter("up_rate_limit"))
        down = _pick_limit(getter("dl_rate_limit"))
        if up is None or down is None:
            return  # 字段未知: 不猜不记不推进基线(与采样器 null 语义同理念)
        cur = (up, down)
        date_str = v4_epoch_date_str(ts)
        if not self._bootstrapped:
            self._bootstrapped = True
            self._bootstrap(date_str, ts, cur)
            return
        if date_str != self._last_date:
            # 00:00 硬切: 新天首行基线 carry(上一生效值无条件写入, 单天文件自洽可读);
            # _last 为 None(字段一直未知)无 carry, 首个可得值按普通事件写
            if self._last is not None and self._append(date_str, ts, self._last):
                self._last_date = date_str
        if self._last is None or cur != self._last:
            if self._append(date_str, ts, cur):
                self._last = cur
                self._last_date = date_str

    def _bootstrap(self, date_str: str, ts: float, cur: tuple) -> None:
        """启动首轮(重启去重): 与当日文件末条相同则跳过(不产生假事件); 不同/无记录写事件"""
        last = _read_day_last_event(self._data_dir, date_str)
        if last is not None and (last[1], last[2]) == cur:
            self._last = cur
            self._last_date = date_str
            return
        if self._append(date_str, ts, cur):
            self._last = cur
            self._last_date = date_str

    def _append(self, date_str: str, ts: float, value: tuple) -> bool:
        """追加一行(open("a") + flush + fsync, 对齐 traffic_store 追加纪律); OSError ->
        WARNING(节流)返回 False 不上抛(观测面降级, 见模块 docstring); 成功推进护栏计数"""
        path = limits_day_path(self._data_dir, date_str)
        line = f"{int(ts)},{int(value[0])},{int(value[1])}\n"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8", newline="\n") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        except OSError as exc:
            now = time.monotonic()
            if now - self._oswarn_ts >= _LIMITS_WARN_GAP_S:
                self._oswarn_ts = now
                logger.warning(f"限速历史 | {date_str}.dat 追加失败(本轮不记, 下轮重试): {exc}")
            return False
        self._guard_count(date_str)
        return True

    def _guard_count(self, date_str: str) -> None:
        """病态翻转护栏: 单天事件数超常量阈值 -> 节流 WARNING(只告警, 数据照记)"""
        if self._day_events_date != date_str:
            self._day_events_date = date_str
            self._day_events = 0
        self._day_events += 1
        if self._day_events > _LIMITS_DAILY_EVENT_WARN:
            now = time.monotonic()
            if now - self._guard_ts >= _LIMITS_GUARD_WARN_GAP_S:
                self._guard_ts = now
                logger.warning(f"限速历史 | {date_str} 事件数 {self._day_events} 超常(疑似外部高频改限速), "
                               "照常记录(文件增速上界 = 采样率 x 行宽)")


class LimitsCache:
    """限速天文件解析缓存(读侧, Web 线程调用): mtime_ns+size 键控, 照 V4DayCache 形状

    - 失效键 = os.stat 的 (st_mtime_ns, st_size): 天文件只在追加期变化(追加必变 size),
      未变即命中直接复用解析产物(不重读不重解析); 缺失/空文件也缓存(stat 键 = None 哨兵),
      文件此后出现自然失效。
    - 内存上界: 按条目数 LRU 逐出(_LIMITS_CACHE_MAX_ENTRIES; 单天体量 KB 级, 不按字节预算)。
    - 线程模型: 表操作持锁, 解析(慢段)在锁外(并发重复解析无害, 后写胜)。
    """
    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir or ""
        self._lock = threading.Lock()
        # date_str -> (stat 键 | None, 事件元组)
        self._entries: OrderedDict = OrderedDict()

    def read_day(self, date_str: str) -> tuple:
        """读单天事件(带缓存): 缺失/空文件 = (); 非法日期 fail-fast(路径纯计算)"""
        if not self._data_dir:
            return ()
        path = limits_day_path(self._data_dir, date_str)
        try:
            st = os.stat(path)
            stat_key = (st.st_mtime_ns, st.st_size)
        except OSError:
            stat_key = None  # 缺失哨兵
        with self._lock:
            ent = self._entries.get(date_str)
            if ent is not None and ent[0] == stat_key:
                self._entries.move_to_end(date_str)
                return ent[1]
        # 锁外解析(慢段; 缺失/空文件 = () 零 open(对齐 V4DayCache._read_parse 先例);
        # OSError(权限/竞态)按缺失处理: 观测面缺一文件 = 事件缺口, 不上抛端点)
        if stat_key is not None or os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    events = parse_limits_day_text(f.read())
            except OSError:
                events = ()
        else:
            events = ()
        with self._lock:
            self._entries[date_str] = (stat_key, events)
            self._entries.move_to_end(date_str)
            while len(self._entries) > _LIMITS_CACHE_MAX_ENTRIES:
                self._entries.popitem(last=False)
        return events


def limits_events_for_window(cache: LimitsCache, t0: float, t1: float) -> list:
    """窗口 [t0, t1) -> 限速事件序列(D3″ 装配单点; 纯装配, 文件访问全走缓存)

    - 日期集合 = v4_window_dates(t0 - 86400, t1): **多看一天** —— 合成首事件要窥窗口起点
      之前最近的事件, 它可能落在前一天文件末行(跨天 carry 保证单天文件自洽, 但窗口起点
      在当天日界之后时, <= t0 的最近事件可能仍是前一天写入的)。
    - 首元素 = 合成事件 [t0, up, down](<= t0 的最近事件值; 无则不合成 —— 记录起点晚于
      窗口起点, 起点前不给值, D5)。
    - 其后 = (t0, t1) 内的真实事件升序; **同值连续事件去重**(跨天 carry 与合成值相同时
      不出重复段 —— 段边界只出现在真实值变化处, 线连续)。
    - 无任何记录 = [](前端不画任何限速段)。
    """
    if t1 <= t0:
        return []
    events: list = []
    for d in sorted(v4_window_dates(t0 - 86400, t1)):
        events.extend(cache.read_day(d))
    out: list = []
    pre = None  # <= t0 的最近生效值(合成首事件候选; None = 记录起点晚于窗口起点, D5 不合成)
    dedup = None  # 去重游标(上一事件的值; 初值随 pre): 段边界只出现在真实值变化处
    for ts, up, down in events:
        val = (up, down)
        if ts <= t0:
            pre = val
            dedup = val
            continue
        if ts >= t1:
            break
        if dedup is None or val != dedup:
            out.append([ts, up, down])
        dedup = val
    if pre is not None:
        out.insert(0, [int(t0), pre[0], pre[1]])  # 合成首事件恒在首位, 与窗内事件互不污染
    return out


def _pick_limit(value) -> Optional[int]:
    """限速字段取值(None/缺失/空串 = 未知 -> None; 数值取整, 0 = 不限速合法):
    口径对齐前端 speedLimitBytes 的 pick(单点语义两端同源)"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
