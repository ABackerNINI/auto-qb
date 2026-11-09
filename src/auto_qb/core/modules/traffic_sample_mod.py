"""TrafficSampleModule: qB 口径流量采样器(v4 写侧, plan 26-10-05-2200 B2 本棒接线;
前代 v3 语义 plan 26-10-04-1957, 行型/关块/结算定约以 v4 计划 §01 为准)

两系列周期采样, 全部读内存快照(1.5s 增量同步已在 store), 零新增 qB 请求:
- 全局(恒采, qB 在线即有值): store.server_state 六字段(瞬时速率对 + all-time 累计对 +
  会话累计对); 速率非零 -> r 记录, (0,0) -> z 游程, 断连/缺字段 -> n 游程;
- 单种(活跃过滤): record 六字段, 仅 dlspeed>0 or upspeed>0 才产 r; 零速/断连进 z/n 游程。

调度位置(issue 26-10-16-0954 实修): 采样是**传感器, 不是作业** —— 全程只读内存快照、零 qB
请求, 故不占任务队列(队列按 max_tasks_per_tick 限流的是 qB 请求预算面)。原先它作为
internal 全局任务与种子级任务同队, 到期判据是严格的 next_run 升序: 重启/热重载的种子级
任务补建(数百条立即到期)会把队列占满数十秒, 这期间 1.5s 采样一次都轮不到(实测 7/7 复现
37~55s 静默), 真实增长被压进单条记录的 dt, 读侧摊配成平线。改为挂**时钟线钩子**
on_task_line(任务线节拍, 每 main_tick 一次, 不受配额约束、不参与队列排序), 到期判定自持:
_next_sample_at = 上次采样时刻 + effective interval, 节拍口径与原先队列 interval 逐字一致。

写侧(§03 + v4 §01): 采样点不再逐行落盘, 进内存 BlockBuffer(每系列一个), 每 flush_interval
(默认 600s, handler 内计时)批量追加落盘到 <data_dir>/qb-traffic-v4/<系列>/<YYYY-MM-DD>.dat
(v4 块头基线 delta 格式: B 行携带块基线, r/z 行存相对基线的 delta, 内存 totals 恒绝对值;
序列化/解析纯函数单点在 core/traffic_store.py v4 纯函数区, 文件写入单点在同文件
TrafficV4Store)。
v2 写路径已随 S5 退役删除: 本模块不触旧目录 qb-traffic/ 与 qb-traffic-v3/(R2 留存不读)。

差分与重置规则(沿用 §03.4): 速率字段直采不差分; 累计差分对 all-time 对进行,
delta = max(0, cur - last); cur < last 判计数器重置(该点增量记 null + INFO, 基线更新为 cur),
绝不产负增量; 会话累计按快照存入采样点不差分不落盘。差分基线(baselines)进程内推进不落盘,
重启后首样只立基线不出增量(首窗 null)。存储侧重置口径(v4 §01 关块状态机): 带 totals 的
记录相对块内最近观测回落(cur < last)即强制关块重开, 新块基线 = 重置后 totals(首记录
delta = 0) —— 块内绝不出现负 delta(_append_record 单点)。

块生命周期与基线(v4 §01 定约):
- 基线立点: 块首带 totals 的记录(r 或 z)立块基线 = 该快照, 其 delta = 0; 块首为 n 游程
  -> n-only 前缀拆成 3 列 B 无基线块, 恢复传输的记录开新块立基线。
- 关块触发: 既有 00:00 硬切 / 改间隔 / 落盘失败复位, 新增计数器重置(cur < last)强制
  关块重开, 加关块谓词 flush ∧ has_r_row —— 纯空闲块(z/n)跨 flush 开放不关; 关块时开放
  游程不封(留内存, 封口后按块首立基线开新块)。

零值/null 游程(§3.2 + v4 §01「空闲封口」):
- 每系列至多一个开放游程(OpenRun, 主循环线程独占); 封口 = 成为 buffer 记录(不单独落盘),
  跨 flush 的开放游程滞留内存, 随下次封口或 stop() 落盘。
- 非 z 事件封口(v4, 取代 v3 时长/样本常态触发): 开放 z 游程按「非 z 事件」封口 ——
  恢复传输 / null 游程 / 计数器重置 / 00:00 / stop。空闲段盘上恰 1 条长 z 行, 空闲期
  主文件零写入(解析缓存全天有效); 代价(已知接受): 崩溃窗口 <= 当天已过时长, 丢失形态
  = 真空, avg/totals/max 无偏。
- 非零样本到达封任意型开放游程(同轮先游程后 r, 文件序 = 时间序); null 到达先封口再记 n
  (z 覆盖不得横跨断连期, R2); 00:00 跨天样本到达先封游程(块不跨天 —— 封 [start, 天界前
  末样本], 跨天样本开新游程)。封口时把「调用方手上的实测样本 > 游程内最后一条零样本
  读数 > 开启快照」作为 z 行末端锚点(形态 D, plan 26-10-16-1509 §04; 单点见 _resolve_run_end)。
  保险闸(N4, 防溢出非常态): 行程时长 >= ZRUN_FLUSH_S(86400s)
  或样本数 >= ZRUN_CAP_SAMPLES(86400, = ceil(86400/interval) 在 interval >= 1s 下的上界)
  —— 正常空闲段任何路径都不应触闸。
- 游程 dt_ms(§09.2 S1 定约): dt 基准 = 链上锚点(上一记录槽位时刻 = 写侧游标; 块首游程
  = B.start) —— 相邻游程之间的一次采样间隔并入后一游程的 dt_ms, 该读法下
  「缺省 = run_len x interval」恰为同一跨度的标称值; OpenRun.start 保留首样本实测时刻
  (保险闸时长判据基准), dt 基准在封口时按块头/非块头分别解析。

单种数据门(§3.2, v2 index 条目门退役): 「种子目录存在且含 >=1 个 .dat」(目录判定) +
  本进程已有缓冲/已确认有数据的系列缓存(零稳态 IO) —— 零样本仅在已有数据或已开游程时
  开启/延长游程, 从未传输种子零文件零游程。totals 快照固定在游程开启时刻(§3.4 沿用 ——
  raw 冻结列语义不变; 形态 D 的末端快照另落 z 行末端列, 见下「聚合分层」段)。

累积漂移触发 dt_ms(§2.3 写侧, 最易踩坑处 —— 判据必须用「累积漂移」):
- 写侧游标 projected_ts 严格镜像读侧 dt 链(上一记录槽位锚点); 每记录判
  |actual - (游标 + 标称推进)| > DRIFT_TOL_MS(250ms, D2) -> 本行写实测 dt_ms 并自然复位
  (游标被推到实测点)。禁止用「本行偏差」作判据 —— 稳态小漂移(d̄=150ms < tol)逐行判永不
  触发、误差照旧累积; 写后复位使稳态漂移自动退化周期性写, 空载(等间隔)保持稀疏零 dt 行。
- 时钟回拨单调钳制: dt_ms = max(1, 实测)(回拨行退回 1ms, 桶归属 max(ts, prev_ts) 属读侧
  S3); 暂停恢复/挂起/过载顺延: dt 取实测大值如实入行(「抖动是事实, 存储层不假装均匀」)。
- 块首记录亚秒余量: B.start = 块首记录实测 epoch 截断到整数秒, 块首 dt 列无语义不写
  (§02.3), 余量成为初始累积漂移由后续显式 dt 自然吸收。

flush 驱动与跨天切块(§3.3):
- 驱动点在采样 handler 内计时(now - last_flush >= flush_interval -> 全系列批量 flush),
  不引新线程(黄金法则 5), 不用 state.maybe_flush 主循环驱动点; 暂停期间 handler 不跑、
  缓冲滞留, 恢复后首轮补 flush。进程首轮只记时点不提前 flush(批量优先, 崩溃窗口
  <= flush_interval 拍板语义不变)。
- 批量写: 每系列单次 open("a") 写 N 行 + flush + fsync; 尾字节查补每 flush 仅一次;
  块头在该块首次 flush 时随批写入(块跨多次 flush 头只写一次; v4 B 行携带块基线,
  r/z 行 delta 序列化每批需基线 —— block_base 随批传)。
- 跨天切块(00:00 硬切, 本地时区): 记录日期 != 块日期 -> 旧块落盘(旧日期文件)+ 新文件新块头
  (interval 不变); 开放游程由跨天封口保证不跨天。落盘失败(OSError)丢弃本块并复位块状态
  (dt 链卫生: 下次成功写起新块, 避免半块游标错位), 连续失败只告警一次。
- 关块谓词(v4 §01): flush ∧ has_r_row —— 带 r 行的块随 flush 关闭(块生命周期常态
  = 一个 flush 窗, delta 被 flush 窗 x 速率封顶), 纯空闲块(z/n)跨 flush 开放不关。
- Q3 保险闸: 单系列缓冲槽数(r=1 / 游程=run_len) >= V4_BUFFER_SLOT_CAP(3600) 提前单独
  flush(防大种子库最坏 ~60MB 滞留; v4 谓词下带 r 行的块随本 flush 关闭)。
- dry_run: 缓冲与游程内存照常推进, flush 触发静默跳过写; enabled=false 不建任务零开销。

优雅退出 stop() 钩子(§3.4): 经 host.stop_all() 触发 —— 封全部开放游程 + 全量 flush +
聚合封口(完结层级照常检查落 agg); dry_run 短路; 幂等; OSError 按落盘失败口径告警不上抛。
qbmanager 的 finally 与 state.save 顺序不改。

聚合分层与恢复(S2b, §04): agg.dat(hour/day/month 9 列 + cov_s, 每系列一个, 追加混存;
行型与逐级派生 v4 不变, 仅跨块结算规则改 —— 见 _agg_feed/_agg_credit_day_file):
- 内存累计器(§4.1, 与 dt 链同源): _append_record 单点逐记录入账, 前向记账 —— 每记录
  到达时把 [上一槽, 本槽) 区间记到上一观测名下(上一记录的速率持有到本记录到达为止),
  槽位/跨度取写侧游标推进的同一计算结果(与落盘 dt 链严格同源); 块首信用经
  v4_block_gap_continuous 条件结算(连续边界把 [上一块末槽, 本块首槽) 按上一记录速率
  结算进覆盖, 崩溃/停机间隙真空 —— 00:00 边界既有每天约 2s 覆盖损失就此消除)。
  z 游程内部槽区间速率恒 0/totals 按「开启快照 -> 末端快照」逐槽线性摊配(形态 D,
  plan 26-10-16-1509 §04: 末端快照随 z 行末端列落盘, 在线/离线两路共用 v4_z_totals_ramp;
  无末端列(旧文件)或单槽游程 = 显式退化, 恒快照 = 旧语义), 逐槽均摊折叠为逐区间记账(聚合值
  等价); n 游程不贡献(null 期无观测, 信用清空)。hour 桶: 区间按小时界拆分入账, cov_s = Σ桶内覆盖
  (≤3600, v4_hour_agg), avg = dt 加权 —— dt_i ≡ interval_s 时严格退化为 v2 纯活跃桶公式
  (对照钉住), max 逐记录取大, totals 取级末快照(桶内最后入账区间的观测快照); 只有 null
  覆盖的小时不产 hour 行(空桶 = null)。day/month 累计器严格逐级(§4.1): hour 行封口并入
  day 累计器(v4_rollup_agg), day 行并入 month 累计器 —— day 不从 raw 直聚(cov_s 链只在
  逐级传递才完整)。同 epoch 行重封 = 替换累计器旧行(append 侧为追加行, 解析取最后一行)。
- 水位封口(§4.2): flush 时点(600s, _maybe_flush_all 驱动)顺序检查完结 —— 完结整小时
  append hour 行 → 完结本地日 append day 行 → 完结自然月 append month 行, 每系列每
  flush 合并一批 append(至多 +1 次 open)。水位 = agg 文件尾(不落内存): append 成功即
  水位推进, 崩溃于 append 后重启从文件尾恢复不重 append(§4.4)。暂停恢复跨多小时时
  pending 可含多日, 翻日/翻月由入账时点级联封口兜底(先封前一日/月再开新累计器)。
- 重启恢复与 catch-up(§4.3, 硬序: catch-up 必须先于裁剪): start() 逐系列扫 agg 文件尾
  一次 -> 恢复水位 + 从文件内行重建当日/当月累计器 -> catch-up 逐级补算 append:
  hour <- 读集内天文件 raw 逐槽前向记账(与在线记账同一口径)、day <- agg 内 hour 行、
  month <- day 行。恢复读集按需(plan 26-10-12-2010 D1, 与流量图数据方案同一契约):
  读集下界 = agg 水位所在日(v4_day_epoch(wm_hour)), 水位封口小时不读不重算 —— 常态
  1 个天文件、跨日界至多 2 个, 与 24h 流量图读侧同阶; rollup_window(默认 30d)只决定
  保留(D2: 1000000D 永久保留不动), 不决定启动读集。agg 无可用水位(缺失/损坏/无 hour
  行)时退回 now - rollup_window 全量兜底(D5: 诚实兜底不猜不静默, INFO 留痕)。停机超窗
  -> 天文件已删 -> 对应 hour/day 行缺失跳过不标注(图上真空, 与块间 gap 语义一致)。
  恢复末尾才做 hour 裁剪(硬序, 测试钉住: hour 到龄/day 未封 时 day 行不丢)。
- 裁剪与淘汰(§4.5): hour 行按 rollup_window 裁剪, piggyback hour 封口时点, 判据用内存
  最老行(零常规文件读), 存在到龄行才重写 + 无到龄零写(same_content 语义), tmp+fsync+
  os.replace 仅存于此(v3 常规写路径无原子重写); day/month 行不按龄裁剪(D7 永久)。
  种子淘汰 = 删超龄系列目录(天文件 + agg.dat), 龄期由天文件名日期直接算(v2 注册表
  机制退役), frozen 照删, 全局系列豁免; 触发点 = flush 时点(节流至多每
  EVICT_CHECK_INTERVAL_S 一次, 扫目录 IO 不随 600s flush 放大), 淘汰后同步清理该系列
  全部内存缓存(数据门/累计器/基线/镜像, 防陈旧门缓存复活已删系列)。
- dry_run: 累计器与水位封口内存照常推进; agg append 与裁剪/淘汰写操作静默跳过;
  stop() 聚合封口随 dry_run 短路; start() 恢复(catch-up 有写)dry_run 整体跳过。

C1 生效与热重载联动(§3.5): 采样体每轮现读 sample_interval_multiplier 与 main_tick,
生效间隔 = 倍数直乘 main_tick 秒(traffic_grid.effective_sample_interval 单点, 无取整无告警
—— 倍数语义下失配数学上不可能, plan 26-11-10-0252 D10); 块头 interval_s 允许小数秒。
检测生效间隔变化 -> 记新的 effective interval + 关闭全部现块(旧块落盘, 新块带新 interval
—— 新旧数据分块各有 interval); multiplier 与 main_tick 每轮现读, 任一变化同走本联动。
!issue 26-10-16-0954: 节拍不再靠「回写 task.interval」表达(采样已不在队列里), 改由时钟线
钩子按 effective interval 自持到期判定。

生命周期判定(S3 的 v2 注册表面)已随 S5 删除: v3 冻结语义 = 删种即不再产新块(不在
by_hash 本就无采样), 文件留存到按龄删除(淘汰属 S2b)。

线程模型(黄金法则 5): 采样体由时钟线钩子 on_task_line 在主循环线程执行(任务线节拍内,
队列 run_due 之后), buffers/baselines/latest/游程全部只在该线程读写, 无锁; 模块自身不
创建任何线程; 全部落盘写在采样调用链内。
活尾快照 live_tail(S6 验收追加)每轮采样末尾构建不可变 LiveTail 表整体替换引用, Web 线程
只读单引用无锁(ctx.web.set_traffic_view 同款快照发布先例; 读侧 traffic_qb 按请求现取该
引用, 故与视图发布先后无关)。快照两面: raw 面 = 未落盘记录 + 开放游程槽(v4_live_tail_slots
复原), agg 面 = 未封口部分行 + 开放游程合成段(_pending_agg_rows <- _open_run_hour_samples,
26-10-29 起) —— 两面同构, 空闲期都出 0 不出 null。

配置: config.qb_traffic(QbTraffic, 缺省 None = 未启用)。启用/停用与热重载全由采样体入口
现读判据承担(enabled=true 即时开采、运行期关闭即时短路), 不依赖队列重建相位; 未启用零
文件零目录零请求(每 main_tick 一次配置现读后短路)。

R5 拆分(计划 26-11-02-2342 §07)后的本文件: 保留模块协议说明、`TrafficSampleModule`
组合类与按 `auto_qb.core.modules.traffic_sample_mod.*` 打补丁所必需的方法
(`__init__` / 公开入口 / `_publish_live_tail`(读 time) / `_advance_run` 与
`_append_record`(读 v4_epoch_date_str) / `_recover_aggregates` 与 `_flush_all_series`(读 time));
常量/数据类/纯助手迁至 traffic_sample_common.py, 聚合域迁至 traffic_sample_agg.py,
采样/块/刷新域迁至 traffic_sample_blocks.py, 全部原有模块级名字在此重导出。
"""
import logging
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Optional

from ...infra.clock import SYSTEM_CLOCK, Clock
from ..module import AppContext, BaseModule
from ..traffic_store import V4NullRun, V4Sample, V4ZeroRun
from ..traffic_limits import SpeedLimitRecorder
from ..traffic_store import (
    DRIFT_TOL_MS,
    HOUR_SECONDS,
    V4HourSample,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    LiveTail,
    LiveTailRun,
    TrafficV4Store,
    v4_block_agg_totals,
    v4_block_gap_continuous,
    v4_block_slots,
    v4_day_epoch,
    v4_epoch_date_str,
    v4_hour_agg,
    v4_merge_agg,
    v4_month_epoch,
    v4_rollup_agg,
    v4_z_totals_ramp,
)

logger = logging.getLogger(__name__)

# ---------- 拆分件重导出(公开面保持: 旧 import 路径全部继续可用) ----------
from .traffic_sample_common import (  # noqa: F401
    EVICT_CHECK_INTERVAL_S,
    GLOBAL_SERIES_KEY,
    ZRUN_CAP_SAMPLES,
    ZRUN_FLUSH_S,
    BlockBuffer,
    OpenRun,
    SeriesAgg,
    TrafficSamplePoint,
    _GLOBAL_FIELDS,
    _TORRENT_FIELDS,
    _TORRENT_KEY_PREFIX,
    V4_BUFFER_SLOT_CAP,
    _hour_spans,
    _record_slots,
    _valid_counter,
)
from .traffic_sample_agg import _SampleAggMixin, _open_run_hour_samples, _pending_agg_rows
from .traffic_sample_blocks import _SampleBlocksMixin


class TrafficSampleModule(_SampleAggMixin, _SampleBlocksMixin, BaseModule):
    """qb_traffic 模块: internal 采样任务自注册 + 两系列采样 + v4 块化批量落盘(S2a)"""

    name = "qb_traffic"

    def __init__(self, ctx: AppContext, clock: Optional[Clock] = None) -> None:
        self._ctx = ctx
        # 取时注入(D8): 采样节拍/游程时间戳用挂钟; 缺省单点经模块属性现取(测试可换假钟)
        self._clock = SYSTEM_CLOCK if clock is None else clock
        # 差分基线(§03.3): 系列键 -> {"dl_total", "up_total"}, 仅进程内推进不落盘;
        # 重启为空 -> 首个采样只立基线不出增量(首窗 null)。null 点不推进基线。
        self._baselines: dict = {}
        # 采样落点镜像: 系列键 -> 最近一个采样点(null 点含)。内存有界(与系列数同阶)。
        self.latest: dict = {}
        # 开放游程(v3 §3.2): 系列键 -> OpenRun, 每系列至多一个; 主循环线程独占
        self._open_runs: dict = {}
        # dry_run 语境旗标(start/handler 每轮设置): dry_run 缓冲游程照常推进, 落盘静默跳过
        self._persistence_on: bool = True
        # 落盘连续失败只告警一次(防断盘场景刷屏), 成功即复位
        self._persist_warned: bool = False
        # ---- 写侧状态(S2a) ----
        # 单系列写侧缓冲(§3.1): 系列键 -> BlockBuffer; 只对「有记录或开放块」系列存在
        self._buffers: dict = {}
        # 写侧存储(惰性构造: 首次 flush 才触盘)
        self._v4store: Optional[TrafficV4Store] = None
        # flush 驱动时点(None = 进程首轮只记时不 flush)
        self._last_flush: Optional[float] = None
        # 当前生效采样间隔(浮点秒, = multiplier * main_tick; 块头 interval 列口径, 允许小数秒)
        self._effective_interval: Optional[float] = None
        # 下一次采样到期点(时钟线钩子 on_task_line 的闸门判据; None = 首拍即采)
        # issue 26-10-16-0954: 采样已不在队列里, 到期判定自持(原先由 TaskQueue.next_run 承担)
        self._next_sample_at: Optional[float] = None
        # 单种数据门缓存(§3.2): 已确认有数据 / 确认无数据的系列键(零稳态目录 IO)
        self._has_data: set = set()
        self._no_data: set = set()
        # 本轮已采样系列键(shell 缓冲清理参照, handler 每轮清空)
        self._round_keys: set = set()
        # ---- 聚合分层状态(S2b) ----
        # 单系列聚合累计器(§4.1): 系列键 -> SeriesAgg; 采样入账 lazily 建, start 恢复预建
        self._agg_states: dict = {}
        # 封口失败已告警的系列键(节流: 同系列恢复前只告警一次; 见 _agg_reset_after_error)
        self._agg_warned: set = set()
        # 种子按龄淘汰上次扫描时点(节流 EVICT_CHECK_INTERVAL_S, §4.5)
        self._last_evict_check: Optional[float] = None
        # ---- 恢复埋点(§4.3, plan 26-10-12-2010: 消除静默, 读集有界可机检) ----
        # 上次 _recover_aggregates 的读集计数: 逐系列 {key: {"day_dates": 读集日期串,
        #   "bound": 下界来源("watermark" 水位日 / "fallback" 保留窗兜底), "new_hours":
        #   补算小时数, "slots": 逐槽入账槽数}}; 汇总 {"series", "day_files", "hours",
        #   "slots", "elapsed_s"}。供测试断言「读集有界」(机检事实, 不靠读日志目测);
        #   None = 未启用/未恢复(dry_run 或流量模块关闭)
        self.recovery_reads: Optional[dict] = None
        self.recovery_stats: Optional[dict] = None
        # ---- 活尾快照(S6 验收追加) ----
        # 系列键 -> LiveTail(未落盘 buffer 记录 + 开放游程的当轮冻结副本): handler 末尾
        # 整体替换引用, Web 线程只读单引用无锁(对齐 ctx.web.set_traffic_view 快照发布
        # 先例; 黄金法则 5 不破 —— 快照只读, 写仍单点在采样调用链内)
        self.live_tail: dict = {}
        # ---- 限速历史记录器(plan 26-10-12-0535 D2) ----
        # 主循环线程独占, _sample_global 顺带观测; data_dir 为空 = 禁用(observe 内防御);
        # dry_run 经 observe 的 persistence_on 旗标短路(与落盘同门)
        self._limits_rec = SpeedLimitRecorder(getattr(ctx.config, "data_dir", "") or "", clock=clock)

    def sections(self) -> tuple[str, ...]:
        return ("qb_traffic", )

    # ---------- 生命周期 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        self._persistence_on = not dry_run  # dry_run 全程零落盘(含 stop 钩子短路)
        self._next_sample_at = None  # 进程首拍即采(对齐原先「任务注册即到期」的启动语义)
        if not dry_run:
            # 聚合恢复 + catch-up(§4.3, 先于任何采样/flush; 含恢复末尾的 hour 裁剪 ——
            # 硬序: catch-up 先于裁剪)。dry_run 跳过(catch-up 有写, 恢复无内存意义)。
            self._recover_aggregates()

    # ---------- 时钟线(任务线节拍): 采样驱动 ----------

    def on_task_line(self, force: bool) -> None:
        """时钟线钩子(可选扩展点, 见 module.Module 契约): 每 main_tick 一拍被宿主调用,
        只做一件事 —— 到期闸门(未到 _next_sample_at 直接返回), 到点交采样体。

        !与同线其它钩子(webui 视图发布)无先后依赖: 本钩子只更新内存态(buffers/游程/
        live_tail), 读侧按请求现取 live_tail 引用, 视图何时发布都不影响采样可见性。
        异常口径与其余 loop hooks 一致(无隔离, 异常上抛主循环兜底)。
        """
        now = self._clock.now()
        if self._next_sample_at is not None and now < self._next_sample_at:
            return
        self.handle_traffic_sample(dry_run=not self._persistence_on)

    # ---------- 采样体 ----------

    def handle_traffic_sample(self, dry_run: bool) -> None:
        """一轮采样(时钟线到点调用; 测试可直调, 直调不受到期闸门约束): C1 间隔联动 +
        两系列采样(游程纪律) + flush 驱动 + 活尾发布, 全在调用线程内。收尾把下一次到期点
        推为 now + effective interval —— 时钟线据此把采样节拍量化到 main_tick 整数倍。
        """
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled:
            # 未启用/运行期被热重载关闭: 本轮不采样不动内存不落盘零请求(黄金法则 2);
            # 到期点不动 —— 重新启用后首拍即采
            return
        self._persistence_on = not dry_run  # dry_run 同口径不落盘(观测写盘属真实副作用)
        now = self._clock.now()
        self._round_keys.clear()
        effective = self._apply_interval(conf)  # C1(§3.5): 现读间隔 -> effective(失配告警 + 变化关块)
        self._next_sample_at = now + effective
        store = self._ctx.store
        if store.client is None:
            # qB 断连(重连退避期, qbmanager 置 client=None): 快照 stale —— 全局出 n 游程槽
            # (v3 §3.2: 现行断连 null 点改写为 n 游程占槽), 单种本轮不采样(停机洞由全局系列
            # 表达, §05.2); 缓冲滞留, flush 驱动照常
            self._touch_null_run(GLOBAL_SERIES_KEY, now)
            logger.debug("流量采样 | qB 断连, 本轮全局记 n 游程槽")
            self._maybe_flush_all(conf, now)
            self._publish_live_tail()
            return
        self._sample_global(store.server_state, now)
        self._sample_torrents(store, now)
        self._maybe_flush_all(conf, now)
        self._publish_live_tail()

    # ---------- 活尾快照发布(S6 验收追加) ----------

    def _publish_live_tail(self) -> None:
        """活尾快照发布(S6): 每轮 handler 末尾把「未落盘 buffer 记录 + 开放游程」冻结成
        不可变 LiveTail 表整体替换 self.live_tail 引用 —— 主线程单写, Web 线程只读单引用,
        无锁(set_traffic_view 同款快照发布)。读侧经 v4_live_tail_slots 复原绝对槽位
        (head_pending 整块复用块内推算 / 否则从写侧游标倒推), 槽 ts 与这些记录落盘后
        v4_block_slots 重算恒等(写侧游标严格镜像读侧链), 端点按 ts 精确去重 —— 快照与
        flush 的先后竞态不重不漏。records 只在 block_open 时发布(block_open=False 时
        读侧按块首游程形态定位开放游程, records 恒空)。

        S7(2026-10-14)追加 pending_agg: 聚合累计器的未封口当前桶部分行(开放 hour/
        day/month)随同一快照发布 —— agg 段窗(3d+)读侧合流它补图尾真空(活尾口径的
        agg 段平移)。发布面因此从 buffers|open_runs 扩到 _agg_states: flush 后
        records 虽已清空(磁盘接管 raw 面), 只要小时未封口, pending_agg 照常发布
        (agg 面)。部分行计算在主线程(纯函数读累计器, 无锁), AggRow 冻结不可变。

        26-10-29 追加开放游程合成段(plan 26-10-29-0231): 部分行不再只含「已落盘记录的
        信用」—— 空闲 z 游程未封口期间累计器 pending 为空, 图尾整段 null(跨天后从 00:00
        起尤甚)。_pending_agg_rows 现按 _open_run_hour_samples 把「未结算信用 + 开放
        游程」合成进 pending 副本, 与 raw 面 v4_live_tail_slots 的开放游程合成同构。
        """
        tails: dict = {}
        now = self._clock.now()
        for key in set(self._buffers) | set(self._open_runs) | set(self._agg_states):
            buf = self._buffers.get(key)
            run = self._open_runs.get(key)
            has_block = buf is not None and buf.start_epoch is not None
            records = tuple(buf.records) if has_block else ()
            agg = self._agg_states.get(key)
            pending_agg = _pending_agg_rows(agg, run, now) if agg is not None else ()
            if run is None and not records and not pending_agg:
                continue  # 无待写记录无开放游程无未封口聚合行: 无活尾信息(shell 缓冲不留快照)
            tails[key] = LiveTail(
                block_open=has_block,
                head_pending=has_block and not buf.header_written,
                start_epoch=buf.start_epoch if has_block else None,
                interval_s=(buf.interval_s if has_block and buf.interval_s else (self._effective_interval or 1)),
                projected_ts=buf.projected_ts if buf is not None else 0.0,
                records=records,
                open_run=(
                    LiveTailRun(
                        kind=run.kind,
                        start=run.start,
                        last_seen=run.last_seen,
                        dl_total=run.dl_total,
                        up_total=run.up_total,
                        samples=run.samples,
                    ) if run is not None else None
                ),
                pending_agg=pending_agg,
            )
        self.live_tail = tails

    # ---------- 开放游程(v3 §3.2) ----------

    def _advance_run(
        self, key: str, ts: float, kind: str, dl_total: Optional[int] = None, up_total: Optional[int] = None
    ) -> None:
        """零/null 样本推进/开启开放游程(§3.2): 零样本只动内存(不出记录/不动 baselines/
        latest), 封口判据 = 非 z 事件(换型/跨天, v4 §01「空闲封口」)与天级保险闸 (3)(4)
        (N4 —— 正常空闲段不应触闸); 已开游程只推进 last_seen 与 samples(无需重读 totals);
        带 totals 的零样本顺带刷新末端锚点候选(run.last_*, 形态 D); 坐拥实测样本的封口
        路径把手上的 totals 作为末端锚点交 _seal_run(拿不到的形态由游程跟踪值兜底);
        开 z 游程需要 totals 快照(缺失不开, 空闲不出 null 槽), n 游程无此要求。
        """
        run = self._open_runs.get(key)
        if run is not None:
            if run.kind != kind or v4_epoch_date_str(ts) != v4_epoch_date_str(run.last_seen):
                # 换型(触发 (2) R2)或 00:00 硬切: 游程不跨型不跨天; 封口用本轮样本读数兜底锚点
                self._seal_run(key, dl_total, up_total)
                run = None
        if run is None:
            if kind == "z" and (dl_total is None or up_total is None):
                return  # 开 z 游程需要 totals 快照; 缺失/非法不开新游程
            self._open_runs[key] = OpenRun(
                kind=kind,
                start=ts,
                last_seen=ts,
                dl_total=int(dl_total) if dl_total is not None else 0,
                up_total=int(up_total) if up_total is not None else 0,
                samples=1,
                last_dl_total=int(dl_total) if dl_total is not None else 0,
                last_up_total=int(up_total) if up_total is not None else 0,
            )
            return
        run.last_seen = ts
        run.samples += 1
        if dl_total is not None and up_total is not None:
            run.last_dl_total = int(dl_total)  # 形态 D: 末端锚点候选随实测零样本刷新
            run.last_up_total = int(up_total)
        if run.samples >= ZRUN_CAP_SAMPLES or ts - run.start >= ZRUN_FLUSH_S:
            self._seal_run(key, dl_total, up_total)

    def _append_record(self, key: str, rec: V4Sample | V4ZeroRun | V4NullRun, start_ts: float, end_ts: float) -> None:
        """单条 v4 记录进缓冲(§3.1/§2.3 写侧核心 + v4 计划 §01 关块状态机): 块开启 /
        00:00 跨天切块 / n-only 前缀拆块 / 计数器重置关块重开 / 累积漂移触发 dt_ms /
        Q3 保险闸, 全部在此单点。

        - 块首记录: B.start = start_ts 截断整数秒, 写侧游标镜像读侧 = B.start(块首亚秒
          余量成为初始累积漂移, 由后续显式 dt 自然吸收); 块首 r 与单槽游程不写 dt(无语义)。
          基线立点(§01): 块首带 totals 的记录(r 或 z)立块基线 = 该快照, 其 delta = 0;
          块首 n 游程不开基线(3 列 B 无基线块)。
        - n-only 前缀拆块(§01「基线立点」): 开放块尚无基线(块首为 n 游程)时到达带 totals
          的记录 -> 先把 n 前缀落盘成 3 列 B 无基线块并关块, 本记录开新块立基线。
        - 计数器重置(cur < 块内最近 totals 观测): 强制关块重开, 新块基线 = 重置后 totals
          (首记录 delta = 0) —— 块内绝不出现负 delta(§01「负 delta」免费校验的写侧排除
          机制; 判定基准用块内最近观测而非块基线, 覆盖回落点高于基线的重置)。
        - 非块首: 判据 = 累积漂移 |end_ts - (游标 + 标称推进)| > DRIFT_TOL_MS(250ms) ->
          本行写实测 dt_ms = max(1, round((end_ts - 游标) x 1000)) 并把游标推到实测点
          (自然复位; 时钟回拨钳制 dt_ms >= 1); 否则游标推进标称值。
        - 跨天(记录日期 != 块日期): 旧块落盘(旧日期文件)后本记录递归走新块首路径(游程
          不跨天由 _advance_run 的跨天封口保证, 此分支常态只服务 r/n 记录)。
        """
        buf = self._buffers.get(key)
        if buf is None:
            buf = self._buffers[key] = BlockBuffer(
                start_epoch=None,
                interval_s=0,
                date_str=None,
                records=[],
                slots=0,
                prev_actual_ts=0.0,
                projected_ts=0.0,
                header_written=False,
                dl_base=None,
                up_base=None,
                has_r_row=False,
                last_dl_total=None,
                last_up_total=None,
            )
        interval = self._effective_interval or 1
        tol_s = DRIFT_TOL_MS / 1000.0
        block_head = buf.start_epoch is None
        if not block_head:
            if buf.date_str != v4_epoch_date_str(end_ts):
                # 00:00 硬切(§3.3): 旧块先落盘(旧日期文件), 本记录成为新块首
                self._close_block_and_reopen(key, rec, start_ts, end_ts)
                return
            if isinstance(rec, (V4Sample, V4ZeroRun)):
                if buf.dl_base is None:
                    # n-only 前缀拆块(§01「基线立点」): 无基线块仅 n 游程合法, 恢复传输的
                    # 记录开新块立基线 —— 前缀先落盘成 3 列 B 无基线块
                    self._close_block_and_reopen(key, rec, start_ts, end_ts)
                    return
                if rec.dl_total < buf.last_dl_total or rec.up_total < buf.last_up_total:
                    # 计数器重置(cur < last, §01 关块状态机): 强制关块重开 —— 新块基线 =
                    # 重置后 totals, 首记录 delta = 0, 重置段绝不混入旧块产负 delta
                    self._close_block_and_reopen(
                        key,
                        rec,
                        start_ts,
                        end_ts,
                        reset_log=(
                            f"流量采样 | {key} 计数器回落({buf.last_dl_total}/{buf.last_up_total} -> "
                            f"{rec.dl_total}/{rec.up_total}), 强制关块重立基线"
                        ),
                    )
                    return
        if block_head:
            # 新块首记录(§3.1): B.start = 块首记录实测 epoch(整数秒); v4 基线状态清零重立
            buf.start_epoch = int(start_ts)
            buf.interval_s = interval
            buf.date_str = v4_epoch_date_str(start_ts)
            buf.header_written = False
            buf.dl_base = None
            buf.up_base = None
            buf.has_r_row = False
            buf.last_dl_total = None
            buf.last_up_total = None
            anchor = float(buf.start_epoch)
            if isinstance(rec, V4Sample):
                buf.records.append(rec)  # 块首 r 的 dt 列无语义, 不写(§02.3)
                buf.slots += 1
                buf.projected_ts = anchor
            elif rec.run_len == 1:
                buf.records.append(rec)  # 块首单槽游程: 读侧零推进, dt 无消费者 —— 不写
                buf.slots += 1
                buf.projected_ts = anchor  # 游标镜像读侧零推进(不落此行则链锚点残留在旧块)
            else:
                span = end_ts - anchor
                nominal = (rec.run_len - 1) * interval  # 块首游程无引导间隔(读侧标称口径)
                if abs(span - nominal) > tol_s:
                    dt_ms = max(1, int(round(span * 1000)))
                    rec = replace(rec, dt_ms=dt_ms)
                    buf.projected_ts = anchor + dt_ms / 1000.0
                else:
                    buf.projected_ts = anchor + nominal
                buf.records.append(rec)
                buf.slots += rec.run_len
            if isinstance(rec, (V4Sample, V4ZeroRun)):
                # 基线立点(§01): 块内首个带 totals 观测的快照, 块首记录 delta = 0
                buf.dl_base = rec.dl_total
                buf.up_base = rec.up_total
                buf.last_dl_total = rec.dl_total
                buf.last_up_total = rec.up_total
            if isinstance(rec, V4Sample):
                buf.has_r_row = True
            buf.prev_actual_ts = end_ts
        else:
            anchor = buf.projected_ts
            nominal = interval if isinstance(rec, V4Sample) else rec.run_len * interval
            drift = end_ts - (anchor + nominal)
            if abs(drift) > tol_s:
                # 累积漂移超容差(§2.3): 写实测 dt 并自然复位(游标推到实测点); 回拨钳制 >= 1
                dt_ms = max(1, int(round((end_ts - anchor) * 1000)))
                rec = replace(rec, dt_ms=dt_ms)
                buf.projected_ts = anchor + dt_ms / 1000.0
            else:
                buf.projected_ts = anchor + nominal
            buf.records.append(rec)
            buf.slots += 1 if isinstance(rec, V4Sample) else rec.run_len
            buf.prev_actual_ts = end_ts
            if isinstance(rec, V4Sample):
                buf.has_r_row = True
            if isinstance(rec, (V4Sample, V4ZeroRun)):
                buf.last_dl_total = rec.dl_total
                buf.last_up_total = rec.up_total
        # 聚合累计器入账(§4.1, S2b): 与 dt 链同源 —— anchor/cursor 取本次游标推进的
        # 同一结果; 跨块信用结算见 _agg_feed(v4 条件结算); 落盘失败丢弃整块时累计器
        # 保留已入账观测(观测面与 raw 面的已知偏差, 与「崩溃窗口丢缓冲 = 真空」口径独立)
        self._agg_feed(key, rec, anchor, buf.projected_ts, block_head, interval)
        if buf.slots >= V4_BUFFER_SLOT_CAP:
            self._flush_series(key)  # Q3 保险闸(§3.1): 超限提前 flush(v4 关块谓词下带 r 行的块随本 flush 关闭)

    def _flush_all_series(self) -> None:
        """全系列批量 flush(§3.3 驱动点; stop() 复用): 逐系列落盘待写记录; 聚合封口
        (§4.2: 完结层级检查 + agg append, S2b); 顺带做内存卫生 —— 无开放块、无待写
        记录、无开放游程且本轮未采样的 shell 缓冲清除。"""
        for key in list(self._buffers):
            self._flush_series(key)
        for key in list(self._buffers):
            buf = self._buffers[key]
            if buf.start_epoch is None and not buf.records and key not in self._open_runs and key not in self._round_keys:
                del self._buffers[key]
        self._agg_flush_all(self._clock.now())

    def _recover_aggregates(self) -> None:
        """重启恢复(§4.3): 扫现存系列, 逐系列恢复水位 + 重建累计器 + catch-up 补算
        (硬序: 补算 append 全部完成后才裁剪)。单系列失败(OSError)不阻断其它系列。

        读集按需(plan 26-10-12-2010 D1): 逐系列读集下界 = agg 水位所在日, 常态 1 个
        天文件、跨日界至多 2 个 —— 与 24h 流量图读侧契约同阶; 不打开流量图时的 0 文件
        由读侧轮询门控保证, 恢复读的是写侧缺口。起止各一条 INFO(消除静默) + 计数落
        self.recovery_reads / self.recovery_stats 供测试机检「读集有界」。"""
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled or not self._ctx.config.data_dir:
            return
        t0 = self._clock.now()
        store = self._get_v4_store()
        keys = store.series_keys()
        logger.info(f"流量采样 | 启动恢复开始: 启用态, {len(keys)} 个现存系列(读集 = agg 水位日 -> 今日, 按需口径)")
        reads: dict = {}
        total_files = 0
        total_hours = 0
        total_slots = 0
        for key in keys:
            try:
                reads[key] = self._recover_series(key, store, t0, conf.rollup_window)
                total_files += len(reads[key]["day_dates"])
                total_hours += reads[key]["new_hours"]
                total_slots += reads[key]["slots"]
            except OSError as e:
                logger.warning(f"流量采样 | {key} 聚合恢复失败(该系列按 agg 现状运行): {e}")
        elapsed = self._clock.now() - t0
        self.recovery_reads = reads
        self.recovery_stats = {
            "series": len(keys),
            "day_files": total_files,
            "hours": total_hours,
            "slots": total_slots,
            "elapsed_s": elapsed,
        }
        logger.info(
            f"流量采样 | 启动恢复完成: {len(keys)} 系列 / 读入天文件 {total_files} 个 / "
            f"补算小时 {total_hours} 个 / 入账槽 {total_slots} 个 / 耗时 {elapsed:.2f}s"
        )

    # ---------- 优雅退出 stop() 钩子(§3.4) ----------

    def stop(self) -> None:
        """stop 钩子(§3.4): 经 host.stop_all() 触发 —— 封全部开放游程 + 全量 flush +
        聚合封口(完结 hour/day/month 层级照常检查并落 agg; 未完结小时的累计器随进程
        消失, 重启经 catch-up 从天文件 raw 重建, 零丢失), 优雅退出零丢失(现行 v2 丢
        开放行程 <=600s 的语义在此闭合)。dry_run 短路(不落盘); 幂等(重复调用缓冲
        游程已空, 零副作用); OSError 按落盘失败口径告警不上抛。"""
        if not self._persistence_on:
            return  # dry_run: 不落盘(观测写盘属真实副作用)
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled or not self._ctx.config.data_dir:
            return
        self._seal_all_runs()
        self._flush_all_series()

    @staticmethod
    def _delta(key: str, direction: str, cur: Optional[int], last: Optional[int]) -> Optional[int]:
        """累计差分: delta = max(0, cur - last)(cur >= last 时天然非负);
        cur < last 判计数器重置: 该点增量记 null + INFO 记录(P6 真机验证重置语义靠它观察)。
        !「cur < last 判重置」口径的分层形态(issue 26-10-11-0207 R07/R10 登记, 保持分层
        不急合): 采样器本函数(判重置记 null) / 视图层 traffic_grid._bucket_delta(判重置
        记 null, 无日志) / 解析侧 v4 天文件负 delta 校验(delta 形态下直接记坏行) ——
        三层同一判据、各自语义, 改判据口径三处同步。"""
        if cur < last:
            logger.info(f"流量采样 | {key} {direction}累计计数器回落({last} -> {cur}), 判重置, 本点增量记 null")
            return None
        return cur - last
