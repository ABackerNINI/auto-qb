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

C1 生效与热重载联动(§3.5): 采样体每轮现读 sample_interval 与 main_tick, 失配向上取整
到 main_tick 下一倍数 + 告警一次(D5: logger.warning + 已告警记忆防重复, 配置变化时记忆
复位), 不拒采; 整数倍匹配的小数档(1.5s 配 main_tick=1.5s)原样生效 —— 块头 interval_s
允许小数秒(2026-10-05 起; 修复小数档被整数秒口径静默抬到下一整秒)。
检测 sample_interval 变化 -> 记新的 effective interval + 关闭全部现块(旧块落盘, 新块带新
interval —— 新旧数据分块各有 interval); main_tick 每轮现读无需联动。
!issue 26-10-16-0954: 节拍不再靠「回写 task.interval」表达(采样已不在队列里), 改由时钟线
钩子按 effective interval 自持到期判定 —— 量化口径(ceil 到 main_tick 倍数)与块头 interval_s
语义逐字不变, 故读侧消费口径(栅格桶宽/窗口切分, 见 pitfalls/backend/task-interval-tick-
quantization.md)不受影响。

生命周期判定(S3 的 v2 注册表面)已随 S5 删除: v3 冻结语义 = 删种即不再产新块(不在
by_hash 本就无采样), 文件留存到按龄删除(淘汰属 S2b)。

线程模型(黄金法则 5): 采样体由时钟线钩子 on_task_line 在主循环线程执行(任务线节拍内,
队列 run_due 之后), buffers/baselines/latest/游程全部只在该线程读写, 无锁; 模块自身不
创建任何线程; 全部落盘写在采样调用链内。
活尾快照 live_tail(S6 验收追加)每轮采样末尾构建不可变 LiveTail 表整体替换引用, Web 线程
只读单引用无锁(ctx.web.set_traffic_view 同款快照发布先例; 读侧 traffic_qb 按请求现取该
引用, 故与视图发布先后无关)。

配置: config.qb_traffic(QbTraffic, 缺省 None = 未启用)。启用/停用与热重载全由采样体入口
现读判据承担(enabled=true 即时开采、运行期关闭即时短路), 不依赖队列重建相位; 未启用零
文件零目录零请求(每 main_tick 一次配置现读后短路)。
"""
import logging
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Optional

from ..module import AppContext, BaseModule
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

#: 全局系列键(对应流量存储 global/ 目录的系列标识)
GLOBAL_SERIES_KEY = "global"

#: 单种系列键前缀(对应流量存储 torrents/<infohash>/ 目录; infohash 即稳定身份键)
_TORRENT_KEY_PREFIX = "torrent:"

#: 全局系列采样字段(顺序 = dl_rate, up_rate, dl_total, up_total, dl_session, up_session)
_GLOBAL_FIELDS = ("dl_info_speed", "up_info_speed", "alltime_dl", "alltime_ul", "dl_info_data", "up_info_data")

#: 单种系列采样字段(顺序同上; record 属性)
_TORRENT_FIELDS = ("dlspeed", "upspeed", "downloaded", "uploaded", "downloaded_session", "uploaded_session")

#: 游程时间刷新封口阈值(秒, N4 天级保险闸): v4 起开放 z 游程正常封口走「非 z 事件」
#: (恢复传输 / null 游程 / 计数器重置 / 00:00 / stop —— §01「空闲封口」), 本阈值退役为
#: 防溢出保险闸(正常空闲段任何路径都不应触闸, 触闸即测试 bug); 模块常量非配置键
ZRUN_FLUSH_S = 86400

#: 游程样本数上限(N4 天级保险闸, 同上): = ceil(86400 / sample_interval) 在 sample_interval
#: >= 1s(配置校验下限 + _apply_interval max(1.0) 钳制)下的上界, 保证游程跨度不超天级
#: dt_ms 口径; 模块常量非配置键
ZRUN_CAP_SAMPLES = 86400

#: 单系列缓冲槽数上限(Q3 保险闸, plan 26-10-04-1957 §3.1): r 记录占 1 槽, 游程占 run_len
#: 槽; 达到即提前单独 flush(防大种子库最坏 ~60MB 滞留); 模块常量非配置键
V4_BUFFER_SLOT_CAP = 3600

#: 种子按龄淘汰扫描节流间隔(秒, §4.5: 触发点 = flush 时点, 扫目录 IO 节流至多每小时
#: 一次 —— 判据口径与触发频率解耦); 模块常量非配置键
EVICT_CHECK_INTERVAL_S = 3600


def _valid_counter(value) -> bool:
    """qB 计数字段合法性: 数值即合法(0 合法); None/缺失/布尔/非数值 = 空值(按 null 处理, 不写 0)"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class TrafficSamplePoint:
    """单系列单轮采样点(内存镜像形态): 全字段 None = null 点(断连/关键字段缺失)。

    v4 起本结构只是「最近一点」的排障镜像(latest), 落盘形态为 v4 块记录
    (V4Sample/V4ZeroRun/V4NullRun); dl_inc/up_inc 为相邻采样的 all-time 累计增量
    (差分), None = 首样立基线 / 计数器重置。
    """
    ts: float  # epoch 秒(采样时刻, 不对齐栅格 —— 抖动是事实, 存储层不假装均匀)
    dl_rate: Optional[int]  # 瞬时下载速率 bytes/s(直采)
    up_rate: Optional[int]  # 瞬时上传速率 bytes/s(直采)
    dl_total: Optional[int]  # all-time 下载累计快照 bytes(Prometheus 口径: 存快照)
    up_total: Optional[int]  # all-time 上传累计快照 bytes
    dl_session: Optional[int]  # 会话下载累计快照 bytes(qB 重启归零; 不落盘)
    up_session: Optional[int]  # 会话上传累计快照 bytes(不落盘)
    dl_inc: Optional[int]  # 相邻采样下载累计增量 bytes(max(0, cur-last); None = 首样/重置)
    up_inc: Optional[int]  # 相邻采样上传累计增量 bytes(同上)


@dataclass
class OpenRun:
    """开放游程(v3 §3.2, 内存态每系列至多一个): 连续零速或 null 观测段, 封口 = 成为
    buffer 记录(_seal_run)。主循环线程独占(黄金法则 5), 随进程消失(崩溃丢 <= ZRUN_FLUSH_S
    纯零信息); totals 快照固定在开启时刻(首个零样本的 all-time 对), 后续零样本不刷新。
    last_dl_total/last_up_total = 游程内最后一条零样本的读数(形态 D 封口末端锚点候选,
    plan 26-10-16-1509 §04: 封口时落进 z 行末端列); 只随「带 totals 的零样本推进」刷新
    —— 已开游程免重读字段的既有路径不刷新它, 封口时它仍是「封口时刻已知的最后观测」。
    """

    kind: str  # "z" | "n"(z = 零速游程, n = null 游程; 同系列同时至多一个, 换型先封口)
    start: float  # 首个零/null 样本实测时刻(触发 (3) 时长判据基准)
    last_seen: float  # 最后一个样本时刻(封口区间上界 = 游程实测终点)
    dl_total: int  # all-time 下载累计快照(开启时刻, 恒定不刷新; n 游程恒 0 不落盘)
    up_total: int  # all-time 上传累计快照(同上)
    samples: int  # 游程内样本计数(触发 (4) 判据 = 落盘 run_len)
    last_dl_total: int  # 游程内最后一条零样本的 all-time 下载读数(末端锚点候选; n 游程恒 0 不用)
    last_up_total: int  # 同上(上传)


@dataclass
class BlockBuffer:
    """v4 单系列写侧缓冲(§3.1 + v4 计划 §01 关块状态机): 当前块的待写记录 + dt 链写侧
    状态 + 块基线状态(主循环线程独占)

    projected_ts 是写侧游标, 严格镜像读侧 dt 链(上一记录槽位锚点): 每记录判
    |actual - (projected_ts + 标称推进)| > DRIFT_TOL_MS -> 写实测 dt_ms 并把游标推到
    实测点(自然复位); 否则游标推进标称值。块跨多次 flush: records 在 flush 时清空,
    start_epoch/interval_s/projected_ts/基线等块状态延续到关块(00:00 硬切 / 改间隔 /
    计数器重置 / flush ∧ has_r_row / 落盘失败复位)。

    v4 基线状态(§01「基线立点」): dl_base/up_base = 块内首个带 totals 观测的快照
    (块首 r 或 z 立基线, 其 delta = 0; 全 None = 无基线块 —— 块首 n 游程前缀, 3 列 B,
    仅 n 游程合法, 恢复传输的记录拆块另立基线); has_r_row = 块内已出现 r 行(关块谓词
    flush ∧ has_r_row —— 纯空闲块跨 flush 开放不关); last_dl_total/last_up_total =
    块内最近一次 totals 观测(计数器重置判定 cur < last —— 强制关块重开, 新块基线 =
    重置后 totals, 绝不产负 delta)。内存 totals 恒绝对值(delta 只在序列化时减基线)。
    """

    start_epoch: Optional[int]  # 本块首记录槽位 epoch 秒(B 行 start); None = 尚无开放块
    interval_s: float  # 本块采样间隔(秒, 块头 B 列; 允许小数秒; 开块时取生效间隔)
    date_str: Optional[str]  # 本块本地日期(YYYY-MM-DD; 块不跨天, 00:00 硬切)
    records: list  # 待写记录(V4Sample/V4ZeroRun/V4NullRun, 按槽序; flush 时清空)
    slots: int  # 待写槽数(r=1 / 游程=run_len; Q3 保险闸判据)
    prev_actual_ts: float  # 上一记录实测时刻(§3.1 结构字段; 回拨参照/诊断)
    projected_ts: float  # 写侧游标 = 上一记录槽位锚点(读侧 dt 链镜像; 漂移判据基准)
    header_written: bool  # 块头是否已随某次 flush 落盘(块头只写一次)
    dl_base: Optional[int]  # v4 块基线: 下载 all-time 快照(None = 无基线块, 与 up_base 成对)
    up_base: Optional[int]  # v4 块基线: 上传 all-time 快照(同上成对)
    has_r_row: bool  # 块内已出现 r 行(v4 关块谓词 flush ∧ has_r_row 的判据)
    last_dl_total: Optional[int]  # 块内最近 totals 观测(重置判定 cur < last; 与基线同点立)
    last_up_total: Optional[int]  # 同上(上传)


@dataclass
class SeriesAgg:
    """单系列聚合分层内存态(S2b §04, 主循环线程独占): 累计器 + 翻日/翻月状态 +
    裁剪判据。水位不在此 —— 水位 = agg 文件尾, append 成功即推进(§4.4)。

    pending: 未封口 hour 桶样本(hour_epoch -> V4HourSample 列表, 按时序); 常态只含
    当前小时, 暂停恢复跨多小时时可含多日(封口时逐桶检查完结)。同 epoch 桶重开
    (flush 恰在小时界后区间信用补记)时入账续接, 重封行替换累计器/文件旧行。
    open_credit: 区间信用 (槽位, dl_rate, up_rate, dl_total, up_total) —— 上一非 null
    槽的前向覆盖待下一记录首槽结算; None = 无信用(null 期/无观测)。块首(v4 起)经
    v4_block_gap_continuous 条件结算: 连续边界把 [上一块末槽, 本块首槽) 按上一记录
    速率入账, 崩溃/停机间隙真空(判定单点, 与离线 _agg_credit_day_file 同源)。
    day_epoch/day_hours: 开放日累计器(当日已封口 hour 行); month_epoch/month_days:
    开放自然月累计器(当月已封口 day 行)。严格逐级(§4.1), day 不从 raw 直聚。
    earliest_hour: agg 文件内最老 hour 行 epoch(裁剪判据, §4.5 —— 零常规文件读)。
    """

    pending: dict = field(default_factory=dict)
    open_credit: Optional[tuple] = None
    day_epoch: Optional[int] = None
    day_hours: list = field(default_factory=list)
    month_epoch: Optional[int] = None
    month_days: list = field(default_factory=list)
    earliest_hour: Optional[int] = None


def _record_slots(rec, anchor: float, cursor: float, block_head: bool) -> tuple:
    """单记录的槽位序列(绝对时刻浮点秒; 与块内槽位推算同一口径, 在线记账与恢复离线
    记账共用): r = [cursor]; z/n 游程非块首 = anchor + spacing*k (k=1..len, 末槽恰在
    cursor = 游程实测终点), 块首 = anchor + spacing*k (k=0..len-1, 首槽恰在
    B.start)。spacing 由 cursor-anchor 派生(显式 dt 或标称), 不重复解读 dt_ms。"""
    if isinstance(rec, V4Sample):
        return (float(cursor), )
    n = rec.run_len
    if block_head:
        if n == 1:
            return (float(anchor), )  # 块首单槽游程: 读侧零推进
        spacing = (cursor - anchor) / (n - 1)  # 端点含均摊(§09.2 定约)
        return tuple(anchor + spacing * k for k in range(n))
    spacing = (cursor - anchor) / n  # 均摊 span/run_len(§02.3)
    return tuple(anchor + spacing * k for k in range(1, n + 1))


def _pending_agg_rows(agg: "SeriesAgg", now: float) -> tuple:
    """聚合累计器 -> 活尾未封口部分行(S7, 2026-10-14; 模块级纯函数供单测探针)。

    agg.dat 只有**封口**行(hour 完结整小时 / day 完结本地日 / month 完结自然月才
    append), 未封口的当前桶只活在写侧累计器 —— 不发布则 3d/7d/30d(hour)/6mo/1y(day)/
    all(month)视图图尾停在最后一个封口桶(用户报「3 天及以上视图有真空: 只显示到
    14 日 0 点, 实际已到 1 点」的根因)。本函数把累计器里的当前桶部分聚合成 AggRow
    发布到活尾快照(LiveTail.pending_agg), 读侧按 epoch 与磁盘封口行合流。

    口径与写侧封口同源(三层各自当前桶):
    - hour: pending 各桶逐桶 v4_hour_agg(dt 加权); 含「已完成未 flush」的桶(flush
      时点未到)与开放当前小时; 已封桶的迟到补记残余也在 pending(写侧重封时
      _agg_merge_prev 合流, 读侧同样按 v4_merge_agg 合流, 两端口径一致);
    - day: 开放日累计器(当日已封 hour 行)+ 当日 pending 部分行 -> v4_rollup_agg;
      开放日 = agg.day_epoch(无封口小时时回落今日);
    - month: 开放月累计器(当月已封 day 行)+ 当月 day 部分行 -> v4_rollup_agg;
      开放月 = agg.month_epoch(无封口日时回落本月)。
    跨桶边界(暂停跨日/月恢复)按 epoch 归属过滤, 旧桶残余不并进新桶行。无样本/无
    有效覆盖的层级不出行(v4_hour_agg / v4_rollup_agg 的 ValueError 逐一跳过 ——
    空桶 = null 语义, 与封口路径同)。day/month 两级的本地日界/月界换算对**人工
    时钟**(测试把模块 time 钉在 1970 附近)在 Windows 上换出负 epoch -> OSError,
    按「该级不出行」处理(生产时钟恒为正不受影响; 纯增益面, 缺该级只回到修复前
    的形态)。
    """
    rows: list = []
    hour_partials: list = []
    for h in sorted(agg.pending):
        samples = agg.pending[h]
        if not samples:
            continue  # 空桶不留(全 null 覆盖的小时不产行, 与 _agg_flush_series 同)
        try:
            hour_partials.append(v4_hour_agg(h, tuple(samples)))
        except ValueError:
            continue  # 无有效覆盖: 不出行(桶 = null)
    rows.extend(hour_partials)
    try:
        day_epoch = agg.day_epoch if agg.day_epoch is not None else v4_day_epoch(now)
        day_children = list(agg.day_hours) + [r for r in hour_partials if v4_day_epoch(r.epoch) == day_epoch]
        if day_children:
            rows.append(v4_rollup_agg("day", day_epoch, tuple(day_children)))
    except (ValueError, OSError, OverflowError):
        pass  # 无有效覆盖 / 人工时钟的本地界换算失败: 该级不出行(见 docstring)
    try:
        month_epoch = agg.month_epoch if agg.month_epoch is not None else v4_month_epoch(now)
        month_children = list(agg.month_days
                             ) + [r for r in rows if r.kind == "day" and v4_month_epoch(r.epoch) == month_epoch]
        if month_children:
            rows.append(v4_rollup_agg("month", month_epoch, tuple(month_children)))
    except (ValueError, OSError, OverflowError):
        pass  # 同上
    return tuple(rows)


class TrafficSampleModule(BaseModule):
    """qb_traffic 模块: internal 采样任务自注册 + 两系列采样 + v4 块化批量落盘(S2a)"""

    name = "qb_traffic"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
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
        # 当前生效采样间隔(浮点秒, C1 失配归倍数后; 块头 interval 列口径, 允许小数秒)
        self._effective_interval: Optional[float] = None
        # 下一次采样到期点(时钟线钩子 on_task_line 的闸门判据; None = 首拍即采)
        # issue 26-10-16-0954: 采样已不在队列里, 到期判定自持(原先由 TaskQueue.next_run 承担)
        self._next_sample_at: Optional[float] = None
        # 失配告警记忆键(sample_interval, main_tick): 配置对变化时复位(同配对只告警一次, D5)
        self._interval_signature: Optional[tuple] = None
        self._ratio_warned: bool = False
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
        self._limits_rec = SpeedLimitRecorder(getattr(ctx.config, "data_dir", "") or "")

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
        now = time.time()
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
        now = time.time()
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
        """
        tails: dict = {}
        now = time.time()
        for key in set(self._buffers) | set(self._open_runs) | set(self._agg_states):
            buf = self._buffers.get(key)
            run = self._open_runs.get(key)
            has_block = buf is not None and buf.start_epoch is not None
            records = tuple(buf.records) if has_block else ()
            agg = self._agg_states.get(key)
            pending_agg = _pending_agg_rows(agg, now) if agg is not None else ()
            if run is None and not records and not pending_agg:
                continue  # 无待写记录无开放游程无未封口聚合行: 无活尾信息(shell 缓冲不留快照)
            tails[key] = LiveTail(
                block_open=has_block,
                head_pending=has_block and not buf.header_written,
                start_epoch=buf.start_epoch if has_block else None,
                interval_s=(buf.interval_s if buf is not None and buf.interval_s else (self._effective_interval or 1)),
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

    # ---------- 开放游程(v3 §3.2) ----------

    def _advance_run(self, key: str, ts: float, kind: str, dl_total=None, up_total=None) -> None:
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

    def _append_record(self, key: str, rec, start_ts: float, end_ts: float) -> None:
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
        self._agg_flush_all(time.time())

    # ---------- 聚合分层与恢复(S2b, §04) ----------

    def _agg_state(self, key: str) -> SeriesAgg:
        """单系列聚合累计器(lazily 建; 纯内存结构, dry_run 照常推进)"""
        agg = self._agg_states.get(key)
        if agg is None:
            agg = self._agg_states[key] = SeriesAgg()
        return agg

    def _agg_feed(self, key: str, rec, anchor: float, cursor: float, block_head: bool, interval_s: float) -> None:
        """聚合累计器逐记录入账(§4.1): 前向记账 —— 本记录到达时结算上一非 null 槽的
        前向覆盖 [信用槽位, 本记录首槽), 再入账本记录内部的游程槽区间(z 恒 0/n 不记),
        信用移到本记录末槽。槽位序列与落盘 dt 链同一游标推进结果(严格同源)。

        跨块覆盖结算(v4 计划 §01「覆盖结算」, 本棒起取代「块首清零信用」): 块首记录
        到达时不再无条件丢弃信用, 而经判定单点 v4_block_gap_continuous 结算 —— gap =
        本块首槽(B.start) - 上一块末槽(credit[0]), gap <= interval_s + DRIFT_TOL(250ms)
        -> 连续, 按上一记录速率把 [末槽, 首槽) 结算进信用; 否则真空(崩溃保护内核不动,
        不虚记覆盖)。与离线 _agg_credit_day_file 两路复用同一判定函数(镜像保证靠同源
        保持), 顺带消除现行 00:00 边界每天约 2s 的既有覆盖损失。"""
        agg = self._agg_state(key)
        credit = agg.open_credit
        slots = _record_slots(rec, anchor, cursor, block_head)
        if credit is not None and slots:
            if not block_head or v4_block_gap_continuous(credit[0], slots[0], interval_s):
                self._agg_credit_hours(agg.pending, credit[0], slots[0], credit[1], credit[2], credit[3], credit[4])
        if isinstance(rec, V4ZeroRun):
            # 游程内部槽区间: 速率恒 0; totals 按「开启快照 -> 末端快照」逐槽线性摊配
            # (形态 D, plan 26-10-16-1509 §04: 与离线 _agg_credit_day_file 共用同一纯函数;
            # 无末端列/末端低于开启 = 显式退化 -> 恒快照 = 旧语义)
            ramp = v4_z_totals_ramp(rec.dl_total, rec.up_total, rec.dl_total_end, rec.up_total_end, len(slots))
            for k in range(len(slots) - 1):
                self._agg_credit_hours(agg.pending, slots[k], slots[k + 1], 0, 0, ramp[k][0], ramp[k][1])
        if isinstance(rec, V4Sample):
            agg.open_credit = (float(cursor), rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total)
        elif isinstance(rec, V4ZeroRun):
            # 游程尾部信用 = 末端摊配值(ramp[-1] = v_{n-1} = 末端快照; 退化时 = 开启快照)
            agg.open_credit = (float(cursor), 0, 0, ramp[-1][0], ramp[-1][1])
        else:
            agg.open_credit = None  # n 游程: null 期无观测, 信用清空(其后区间不记)

    @staticmethod
    def _agg_credit_hours(
        pending: dict, start: float, end: float, dl: int, up: int, dl_total: int, up_total: int
    ) -> None:
        """区间 [start, end) 按小时界拆分入账(V4HourSample, dt = 桶内覆盖秒); 在线记账
        与恢复离线记账共用(离线传局部 dict)。末槽的信用区间跨小时界时自然拆分,
        hour 桶 cov 上界 3600 由 v4_hour_agg 收口。"""
        if end <= start:
            return
        cur = start
        while cur < end:
            h = int(cur) // HOUR_SECONDS * HOUR_SECONDS
            seg = min(end, h + HOUR_SECONDS) - cur
            pending.setdefault(h, []).append(V4HourSample(dl, up, dl_total, up_total, seg))
            cur += seg

    def _agg_flush_all(self, now: float) -> None:
        """全系列聚合封口(§4.2 flush 时点; stop() 复用 —— 未完结层级留累计器, 重启经
        catch-up 重建, 零丢失)。

        逐系列隔离(2026-10-13 真机取证): 单系列封口抛错只该影响该系列。此前异常一路上抛到
        handler, 于是 ①其余系列本轮也不封口 ②`_agg_append` 永不执行 = 全系列 agg 静默停写
        ③抛点在状态复位之前, 同一错每轮 flush 复现 —— 真机上一个系列抛「逐级聚合无有效
        覆盖」, 全系列小时行一个多小时没落盘。现在逐系列 catch + 善后(见
        _agg_reset_after_error), 单系列的问题不再放大成全局停写。"""
        for key in list(self._agg_states):
            try:
                self._agg_flush_series(key, now)
            except Exception as e:  # noqa: BLE001 —— 逐系列隔离即本函数职责(见 docstring)
                self._agg_reset_after_error(key, e)
            else:
                self._agg_warned.discard(key)  # 恢复健康: 下次再错重新告警一次

    def _agg_reset_after_error(self, key: str, err: Exception) -> None:
        """单系列封口失败善后(见 _agg_flush_all): 告警(同系列恢复前只一次, 免 6 次/分钟刷屏)
        + **重置该系列聚合累计器**。为什么重置: 抛点位于「本批行 append 之前」, 累计器里
        已封未落盘的行再也送不出去, 不重置就会每轮 flush 重抛同一错(真机复现)。重置后
        后续小时照常封口; 缺的那段由下次重启的 catch-up 从天文件重算补回(与「崩溃窗口丢
        缓冲 = 真空」同一诚实口径: 不猜、不静默 —— 告警行写明缺口出处)。"""
        if key not in self._agg_warned:
            self._agg_warned.add(key)
            logger.error(
                f"流量采样 | {key} 聚合封口失败(该系列聚合累计器已重置, 后续小时照常封口; "
                f"本段缺口待下次重启 catch-up 从天文件重算补回): {type(err).__name__}: {err}"
            )
        self._agg_states.pop(key, None)

    def _agg_flush_series(self, key: str, now: float) -> bool:
        """单系列聚合封口(§4.2): 完结整小时 -> hour 行 -> 完结本地日 -> day 行 ->
        完结自然月 -> month 行, 顺序检查; 产出行合并一批 append(每系列每 flush 至多
        +1 次 open)。dry_run / data_dir 空: 封口内存照常推进, 写静默跳过。hour 封口
        时点 piggyback 裁剪检查(§4.5)。返回是否实际写了 agg 文件(测试用)。"""
        agg = self._agg_states.get(key)
        if agg is None:
            return False
        rows = []
        for h in sorted(agg.pending):
            if h + HOUR_SECONDS > now:
                break  # 首个未完结小时即止(pending 按序, 之后只会更晚)
            samples = agg.pending.pop(h)
            if not samples:
                continue  # 空桶不留(全 null 覆盖的小时不产行, 空桶 = null)
            self._agg_ingest_hour(agg, v4_hour_agg(h, tuple(samples)), rows)
        if agg.day_epoch is not None and agg.day_hours and v4_day_epoch(now) > agg.day_epoch:
            self._agg_ingest_day(agg, v4_rollup_agg("day", agg.day_epoch, tuple(agg.day_hours)), rows)
            agg.day_epoch, agg.day_hours = None, []
        if agg.month_epoch is not None and agg.month_days and v4_month_epoch(now) > agg.month_epoch:
            rows.append(v4_rollup_agg("month", agg.month_epoch, tuple(agg.month_days)))
            agg.month_epoch, agg.month_days = None, []
        wrote = self._agg_append(key, tuple(rows))
        conf = self._ctx.config.qb_traffic
        if conf is not None and any(r.kind == "hour" for r in rows):
            self._agg_trim(key, agg, now, conf.rollup_window)  # piggyback hour 封口时点
        return wrote

    @staticmethod
    def _ingest_acc(row, cur_epoch, cur_rows, bucket_epoch_of, cascade) -> tuple:
        """聚合累计器并入骨架单点(issue 26-10-11-0207 R10): hour/day 两级同构 —— 首桶开
        累计器 / 同桶追加(同 epoch 重封替换, 传入行已由 _agg_merge_prev 合流过) / 翻桶先
        级联封口(cascade)再开新累计器。返回 (new_epoch, new_rows); 本行落批
        (rows_out.append)与 hour 的 earliest_hour 判据由调用方自理。"""
        e = bucket_epoch_of(row.epoch)
        if cur_epoch is None:
            return e, [row]
        if e == cur_epoch:
            rows = [h if h.epoch != row.epoch else row for h in cur_rows]
            if all(h.epoch != row.epoch for h in rows):
                rows.append(row)
            return cur_epoch, rows
        cascade(cur_epoch, cur_rows)
        return e, [row]

    @staticmethod
    def _agg_merge_prev(row, cur_epoch, cur_rows, bucket_epoch_of):
        """同桶重封的入库行(§04.2): 该 epoch 已在累计器里(小时封口后被迟到的补记重建又再
        封一次)时, 返回与已封行的**合流行**(v4_merge_agg), 否则原样返回本行。落批的必须是
        这个返回值 —— 解析按「同 epoch 取最后一行」, 落残余行等于读侧也只看到残余
        (2026-10-13 真机: 日行 cov_s 只留残余 44712 vs 全量 86400)。"""
        if cur_epoch is None or bucket_epoch_of(row.epoch) != cur_epoch:
            return row
        for h in cur_rows:
            if h.epoch == row.epoch:
                return v4_merge_agg(h, row)
        return row

    @staticmethod
    def _agg_ingest_hour(agg: SeriesAgg, row, rows_out: list) -> None:
        """完结 hour 行落批 + 并入 day 累计器(严格逐级): 入库行(首封或与已封行合流的重封行)
        随本批落盘(§4.2 完结整小时 append hour 行; 同 epoch 重封 = 追加**合流行**, 解析取
        最后一行 —— 落批必须是合流行, 否则读侧末行仍是残余); 同日追加; 同 epoch 重封与
        累计器旧行合流(v4_merge_agg); 翻日(暂停恢复跨多小时滞留)先级联封前一日再开新累计器。
        顺带维护 earliest_hour 裁剪判据(§4.5): 运行期才开始产数据的系列(全新安装 global /
        新种子 / 热重载启用)不经 _recover_series, 判据只能在此初始化 + min 更新, 否则
        _agg_trim 恒早退、agg.dat 无界增长(26-10-06-0028 C-01)。"""
        stored = TrafficSampleModule._agg_merge_prev(row, agg.day_epoch, agg.day_hours, v4_day_epoch)
        rows_out.append(stored)
        if agg.earliest_hour is None or row.epoch < agg.earliest_hour:
            agg.earliest_hour = row.epoch

        def cascade(close_epoch, close_rows) -> None:
            # 前一日随本行翻日封口(其末 hour 已过, 前一日必已完结)
            TrafficSampleModule._agg_ingest_day(agg, v4_rollup_agg("day", close_epoch, tuple(close_rows)), rows_out)

        agg.day_epoch, agg.day_hours = TrafficSampleModule._ingest_acc(
            stored, agg.day_epoch, agg.day_hours, v4_day_epoch, cascade
        )

    @staticmethod
    def _agg_ingest_day(agg: SeriesAgg, row, rows_out: list) -> None:
        """完结 day 行落批 + 并入 month 累计器(严格逐级): 入库行(首封, 或与已封行合流的
        重封行)随本批落盘(§4.2 完结本地日 append day 行; 同 epoch 重封 = 追加合流行); 同月
        追加 / 同 epoch 合流 / 翻月级联封前一月(语义同 _agg_ingest_hour)。"""
        stored = TrafficSampleModule._agg_merge_prev(row, agg.month_epoch, agg.month_days, v4_month_epoch)
        rows_out.append(stored)

        def cascade(close_epoch, close_rows) -> None:
            rows_out.append(v4_rollup_agg("month", close_epoch, tuple(close_rows)))

        agg.month_epoch, agg.month_days = TrafficSampleModule._ingest_acc(
            stored, agg.month_epoch, agg.month_days, v4_month_epoch, cascade
        )

    def _agg_append(self, key: str, rows: tuple) -> bool:
        """聚合行批量落盘(同款追加纪律, dry_run 静默跳过): OSError 按落盘失败口径
        告警不上抛(连续失败只告警一次, 与天文件共用记忆) —— 行随累计器丢失, 重启经
        catch-up 从天文件/agg 尾重建补算(幂等)。"""
        if not rows:
            return False
        if not self._persistence_on or not self._ctx.config.data_dir:
            return False  # dry_run: 封口内存照常推进, 写静默跳过
        try:
            self._get_v4_store().append_agg_rows(key, rows)
            self._persist_warned = False
            return True
        except OSError as e:
            if self._persist_warned:
                logger.debug(f"流量采样 | {key} agg 行落盘失败(持续): {e}")
            else:
                logger.warning(f"流量采样 | {key} agg 行落盘失败(本批聚合行丢失, 重启后补算): {e}")
                self._persist_warned = True
            return False

    def _agg_trim(self, key: str, agg: SeriesAgg, now: float, window: float) -> None:
        """hour 行按 rollup_window 裁剪(§4.5): 判据用内存最老行(零常规文件读), 存在
        到龄行才重写(无到龄零写 = same_content 语义); dry_run 静默跳过。"""
        if not self._persistence_on or not self._ctx.config.data_dir:
            return
        if agg.earliest_hour is None or now - agg.earliest_hour <= window:
            return  # 无到龄行(边界含): 不读不写
        try:
            agg.earliest_hour = self._get_v4_store().trim_agg_hours(key, now, window)
        except OSError as e:
            logger.warning(f"流量采样 | {key} agg 裁剪失败(原文件完好, 下轮重试): {e}")

    def _maybe_evict(self, conf, now: float) -> None:
        """种子按龄淘汰(§4.5, flush 时点): 扫描节流至多每 EVICT_CHECK_INTERVAL_S 一次
        (判据口径与触发频率解耦); 淘汰 = 删超龄系列目录, 返回键同步清理该系列全部内存
        缓存(数据门/累计器/基线/镜像/缓冲/游程 —— 防陈旧门缓存复活已删系列)。"""
        if not self._persistence_on or not self._ctx.config.data_dir:
            return  # dry_run: 淘汰写操作静默跳过
        if self._last_evict_check is not None and now - self._last_evict_check < EVICT_CHECK_INTERVAL_S:
            return
        self._last_evict_check = now
        try:
            evicted = self._get_v4_store().evict_expired_series(now, conf.rollup_window)
        except OSError as e:
            logger.warning(f"流量采样 | 种子淘汰扫描失败(下轮重试): {e}")
            return
        for key in evicted:
            self._agg_states.pop(key, None)
            self._has_data.discard(key)
            self._no_data.discard(key)
            self._baselines.pop(key, None)
            self.latest.pop(key, None)
            self._buffers.pop(key, None)
            self._open_runs.pop(key, None)
        if evicted:
            logger.info(f"流量采样 | 按龄淘汰超龄系列目录 {len(evicted)} 个(天文件 + agg.dat)")

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
        t0 = time.time()
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
        elapsed = time.time() - t0
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

    @staticmethod
    def _catch_up_level(children: list, bucket_epoch_of, cur_bucket: int, watermark: Optional[int], kind: str) -> tuple:
        """catch-up 逐级补算骨架单点(issue 26-10-11-0207 R10): day/month 两级同构 ——
        子行(存量 + 新补)按桶分组成本级行, 未完结的当前桶重建累计器、水位前已有行不重算
        (前向水位 §4.4)、其余完结桶补算 rollup 行(返回作上一级输入)。累计器字段名两级
        不同, 故 (补算行, 当前桶 epoch, 当前桶子行) 三元组返回由调用方落回 agg。"""
        buckets: dict = {}
        for c in children:
            buckets.setdefault(bucket_epoch_of(c.epoch), []).append(c)
        cur_epoch, cur_rows = None, []
        out = []
        for b in sorted(buckets):
            if b >= cur_bucket:
                cur_epoch, cur_rows = b, list(buckets[b])  # 当前桶累计器(未完结)
                continue
            if watermark is not None and b <= watermark:
                continue  # 已有行: 不重算
            out.append(v4_rollup_agg(kind, b, tuple(buckets[b])))
        return out, cur_epoch, cur_rows

    def _recover_series(self, key: str, store: TrafficV4Store, now: float, window: float) -> dict:
        """单系列恢复(§4.3/§4.4): 扫 agg 文尾 -> 水位(= 文件尾行, 不落内存不重 append)
        + 文件内行重建当日/当月累计器 -> catch-up 逐级补算 append(hour <- 读集内天文件
        raw 逐槽前向记账 / day <- agg 内 hour 行 / month <- day 行) -> 末尾才裁剪(硬序)。

        读集按需(plan 26-10-12-2010 D1): 读集下界 = agg 水位所在日
        [v4_day_epoch(wm_hour), 今日] —— 水位封口小时不读不重算(现判据 h <= wm_hour
        已在过滤), 读集常态 1 个天文件、跨日界至多 2 个, 与 24h 流量图读侧契约同阶;
        rollup_window 只决定保留(D2: 1000000D 永久保留不动), 不决定启动读集。为什么是
        「所在日」而非时刻: series_day_dates 按文件名日期过滤, 传 day(wm_hour) 恰好纳入
        水位当天天文件(水位之后的 raw 必落在该日或更晚文件 —— 天文件 00:00 硬切、块不跨天)。
        agg 无可用水位(wm_hour is None: 缺失/损坏/无 hour 行)时退回 now - window 全量
        兜底(D5: 无可信水位则不可判哪些小时已聚合, 全量重算 + INFO 留痕, 诚实兜底不猜)。
        停机超窗的天文件已删 -> 对应 hour/day 行缺失跳过不标注(图上真空, 与块间 gap 同)。

        返回读集埋点 {"day_dates", "bound", "new_hours", "slots"}(供 _recover_aggregates
        汇总与测试机检读集有界)。"""
        parsed = store.read_agg(key)
        agg = self._agg_state(key)
        agg.earliest_hour = parsed.hours[0].epoch if parsed.hours else None
        wm_hour = parsed.hours[-1].epoch if parsed.hours else None
        wm_day = parsed.days[-1].epoch if parsed.days else None
        wm_month = parsed.months[-1].epoch if parsed.months else None
        today = v4_day_epoch(now)
        cur_month = v4_month_epoch(now)
        # --- hour catch-up: 读集内天文件 raw 逐槽前向记账(与在线记账同一口径);
        # --- 跨天文件末槽上下文接力(00:00 边界连续时条件结算, 缺文件断链) ---
        hour_samples: dict = {}
        day_tail: Optional[tuple] = None
        if wm_hour is not None:
            lower = v4_day_epoch(wm_hour)  # 按需口径: 读集下界 = 水位所在日
            bound = "watermark"
        else:
            lower = now - window  # 兜底(D5): 无可信水位, 退回保留窗全量
            bound = "fallback"
            logger.info(f"流量采样 | {key} agg 无可用水位(缺失/损坏/无 hour 行), "
                        f"读集退回保留窗 now - rollup_window 全量兜底(D5)")
        slot_counts: list = []
        day_dates = store.series_day_dates(key, lower)
        for date in day_dates:
            parsed_day = store.read_day(key, date)
            if parsed_day is not None:
                day_tail = self._agg_credit_day_file(hour_samples, parsed_day, day_tail, slot_counts)
            else:
                day_tail = None  # 缺失文件: 结算上下文断链(其后间隙由 gap 判定兜底真空)
        if len(day_dates) > 2:
            src = f"水位日 {day_dates[0]} 陈旧(聚合持续未落盘?)" if bound == "watermark" else "fallback 保留窗全量"
            logger.info(f"流量采样 | {key} 读集 {len(day_dates)} 天(>2): 下界来源 = {src}(不影响正确性, 正确性由逐小时重算判据保证)")
        new_hours = []
        for h in sorted(hour_samples):
            if wm_hour is not None and h <= wm_hour:
                continue  # 水位之前已有行: 不重算(前向水位, §4.4)
            samples = hour_samples[h]
            if not samples:
                continue
            if h + HOUR_SECONDS <= now:
                new_hours.append(v4_hour_agg(h, tuple(samples)))  # 完结缺失小时 -> 补算行
            else:
                agg.pending[h] = list(samples)  # 开放小时 -> 重建累计器
        # --- 当日/当月累计器从文件内行重建 + day/month catch-up(严格逐级) ---
        new_days, agg.day_epoch, agg.day_hours = self._catch_up_level(
            list(parsed.hours) + new_hours, v4_day_epoch, today, wm_day, "day"
        )
        new_months, agg.month_epoch, agg.month_days = self._catch_up_level(
            list(parsed.days) + new_days, v4_month_epoch, cur_month, wm_month, "month"
        )
        rows = tuple(new_hours + new_days + new_months)
        if rows:
            self._agg_append(key, rows)  # catch-up 补算 append(幂等: 同 epoch 取最后一行)
        self._agg_trim(key, agg, now, window)  # 硬序: catch-up 全部落盘后才裁剪
        return {
            "day_dates": day_dates,
            "bound": bound,
            "new_hours": len(new_hours),
            "slots": sum(slot_counts),
        }

    @staticmethod
    def _slot_agg_obs(slot, agg_totals: Optional[tuple]) -> Optional[tuple]:
        """单槽的 agg 入账观测(离线恢复用, 形态 D 单点): z 槽 = (0, 0, 摊配 dl, 摊配 up)
        (v4_block_agg_totals 的逐槽值 —— 无末端列/单槽游程时 = 开启快照, 与旧语义逐位一致);
        r 槽 = 原 obs(速率 + 冻结 totals); n 槽 = None(null 期不贡献)。"""
        if slot.obs is None:
            return None
        if agg_totals is None:
            return slot.obs
        return (0, 0, agg_totals[0], agg_totals[1])

    @staticmethod
    def _agg_credit_day_file(
        hour_samples: dict,
        parsed_day,
        prev_tail: Optional[tuple] = None,
        slot_counter: Optional[list] = None
    ) -> Optional[tuple]:
        """单天文件逐槽前向记账(恢复离线侧): 逐块展开槽位(块内相邻槽区间 [slot_k,
        slot_k+1) 记 slot_k 的观测 —— r = 其速率 / z = 摊配值(v4_block_agg_totals) / n =
        null 不记), 与在线 _agg_feed 结算区间信用同一口径(槽位两路同源, z 的 agg totals
        两路共用 v4_z_totals_ramp)。

        跨块覆盖结算(v4 计划 §01「覆盖结算」, 与在线路复用判定单点 v4_block_gap_continuous):
        块间(含跨天文件 —— prev_tail 由 _recover_series 传入上一文件末槽上下文)gap =
        下一块首槽 - 上一块末槽, 连续(<= interval + DRIFT_TOL)则按上一槽速率把
        [末槽, 首槽) 结算进覆盖, 崩溃/停机间隙超容差为真空 —— 00:00 边界既有每天约 2s
        覆盖损失就此消除。prev_tail = (末槽 ts, obs) 或 None(无上下文/上文件缺链);
        返回本文件末槽上下文(末槽为 null 观测时 obs = None, 调用方结算侧自然跳过;
        z 末槽的 obs 为摊配末端值 —— 与在线 z 记录的尾部信用同值)。

        slot_counter 非 None(恢复埋点 §4.3, plan 26-10-12-2010)时按块追加各块槽数
        (读集成本的量级单点, 供计数属性断言); 不传 = 零影响(既有调用不变)。"""
        tail = prev_tail
        for block in parsed_day.blocks:
            slots = v4_block_slots(block)
            agg_totals = v4_block_agg_totals(block)  # 形态 D: z 槽摊配值(与 slots 等长同序)
            if slot_counter is not None:
                slot_counter.append(len(slots))
            if not slots:
                continue
            first = slots[0]
            if tail is not None and tail[1] is not None:
                if v4_block_gap_continuous(tail[0], first.ts, block.interval_s):
                    dl, up, dlt, upt = tail[1]
                    TrafficSampleModule._agg_credit_hours(hour_samples, tail[0], first.ts, dl, up, dlt, upt)
            for k in range(len(slots) - 1):
                cur, nxt = slots[k], slots[k + 1]
                obs = TrafficSampleModule._slot_agg_obs(cur, agg_totals[k])
                if obs is None:
                    continue  # n 槽: null 期不贡献
                TrafficSampleModule._agg_credit_hours(hour_samples, cur.ts, nxt.ts, *obs)
            tail = (slots[-1].ts, TrafficSampleModule._slot_agg_obs(slots[-1], agg_totals[-1]))
        return tail

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
    def _delta(key: str, direction: str, cur, last) -> Optional[int]:
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
