"""traffic_group_cache: 样本分组点列缓存(plan 26-11-18-0037 阶段 1 T1c-1; §03 读侧契约)

per (系列键, window) 缓存 assemble_group_points 的装配结果(points/totals/stride/
over_budget), 是 26-11-15-1104 桶值缓存(V4SeriesBucketCache, T1c-2 退役)的「改造转世」:
_V4BucketDayCursor 的「消费集 = 槽流前缀、只展新增槽」游标模式原样承袭, 折叠面从挂钟
桶累加器换成样本分组前缀和 —— 分组锚是「窗内第 i 个样本」(窗首样本 = 序号 0, T1a 装配
契约), 响应窗 [t0, t1) 随 now 平移, 窗内样本集两端同时变动(窗沿掉样本/尾端进样本),
组界随之整体平移 —— 「已闭合组不动」在滑动窗下不成立(k>1 时窗沿每掉一个样本全部组界
移一位), 因此本缓存不做组粒度封口, 而是把增量做在**样本粒度**:

- 槽流前缀逐样本的最终增量/覆盖/totals/断链旗以**前缀和数组**(array('q'/'d'), O(1) 追加)
  持久化; 重复请求只对新增槽做增量折叠(O(新增槽)), 组点列在响应期由前缀和按当前窗的
  组界(窗首样本序号 + g*k)O(组数) 现推 —— 组界怎么移(k 上调/窗沿平移)都只是前缀差分,
  与冷算逐位等价(同窗同输入 -> 同 points/totals/stride/over_budget, 新电池主断言,
  旧电池 test_cache_polling_bitwise_equivalent 的转世)。
- 尾组语义由前缀和自然承载: 尾组 = 末组(可不满 k), 其样本差分/覆盖随新增槽即时入账,
  每 tick 重推即更新 —— 无克隆无持有(§03 尾组恒真值)。
- 摊配回写面(等值游程闭合时 _seam_spread_delta 向游程项份额回写)是唯一的「已入账样本
  被后继槽改写」源: 等值游程的项构成槽流的**连续 pending 后缀** [r0, N)(闭合/弃摊前
  不定影), 闭合时才按份额定影入前缀和 —— 回写面天然限制在后缀内, 前缀和无需回改。
  响应期开放项按现值参与(delta = 0、覆盖入分母)与冷算的组累加器状态逐位同构。
- 活尾快照(S6, 每请求整体替换非追加)折在快照点上, 响应后 O(1) 回滚(截断到快照长度 +
  标量还原): 活尾槽绝不入持久态, 下轮由磁盘游标续展或重折, 不重不漏。

失效面(承袭旧桶缓存注清单):
(a) 天文件追加 = 增量(游标推进, 非失效); (b) 天文件结构性变化(裁剪重写/删除 —— 游标
校验不过)、游程锚点滑出回看界(sanitize 防御路径)= 整条目冷重建(同输入重算恒等);
(c) 配置变化(采样间隔 si 变更 -> 消费下界/预期样本数/k 整体改变)= 条目丢弃冷重建;
(c2) 读集前沿变化(最早读取日期更替, 差分链起点重锚)= 整条目冷重建(每条目每日至多
一次); (d) 组图成员集变化 = 成员各按自身系列键查表, 无组级缓存面; (e) 逐出 = LRU 上限。

已知边界(与旧桶缓存同 trade-off, 生产形态不可达): 天文件内 ts >= t1 的槽不展开不判定
(游标停驻, 下轮重展重判)—— 生产写侧样本 ts <= 落盘时刻 < 请求 now = t1, 磁盘链恒止于
窗尾之前; 若存在「未来槽」, 停驻块余量的停机洞标记/块界真空判定推迟到下轮, 活尾去重
基准 = 已展开磁盘链末槽 ts(= 全链末槽的同生产形态), 与旧桶缓存逐请求延迟同构。

线程模型: 单锁串行(V4DayCache / 旧桶缓存同款)—— 读侧被 Web 线程并发调用, 折叠/响应/
回滚全程持锁; 只读文件在调用方(锁外), 本类只读传入的解析产物 + 自身内存态, 单一写
线程假设(黄金法则 5)不涉及。
内存账: 常规条目驻留 = 窗内样本数 x 前缀和数组(ts 8B + 速率面两方向增量/覆盖 4 x 8B +
totals 和/计数 4 x 8B + broke 计数 8B, 约 73B/样本); 24h 活跃满窗(57600 样本)约
4.2MB/条目, 128 条最坏 ~540MB —— 换取温态 O(组数) 响应(旧桶缓存常规条目 0.1-0.5MB,
但 k>1 分组在滑动窗下无法封口, 这是分组锚的固有代价); 空闲长游程条目 = 开放项覆盖
前缀数组(8B/项, 无逐项 z 签名 —— all(z) 走 all_z 单点), compact 裁剪到窗界(评审 #6:
base 前开放项覆盖折入 cov[0] 前缀, 驻留 = 窗内样本 x 9B 约 0.5MB/条; 旧面游程项 4 元组
实测 18MB/条且裁到 t0-interval, 同界口径数组化后量级缩减), 闭合摊配经 run_prefix
算术守恒无瞬时全游程物化面(旧结构闭合需整游程入参); 裁剪地平线 = 窗首样本序号(死区
过半才切片压缩, 摊还 O(1))。解析产物内存不在此预算(归 V4DayCache 的
V4_DAY_CACHE_BUDGET_BYTES 字节预算管)。
"""
from array import array
from bisect import bisect_left
from collections import OrderedDict
from threading import Lock
from typing import Optional

from .traffic_grid import (
    _V4_SEAM_NULL_S,
    _V4_VACUUM_EPS_S,
    _V4BucketDayCursor,
    _bucket_delta,
    _day_cursor_after,
    _seam_spread_delta,
    _v4_bucket_day_cursor_valid,
)
from .traffic_group_assembly import (
    GroupAssemblyResult,
    _check_window,
    _pick_stride,
    _slot_null_marks,
    group_null_lo,
)
from .traffic_store_codec import v4_block_slots_from

#: 前缀死区压缩阈(样本数): 死区(窗首样本序号之前的已定影前缀)达到该值且过半才切片,
#: 摊还 O(1) 追加; 阈值下单次切片成本(数万元素级)在温态预算内可忽略
_COMPACT_MIN_DEAD = 4096


class _DirRun:
    """单方向等值游程状态(分组游标): value/anchor_ts 承袭 _V4SeriesFold.run 形;
    r0 = 开放游程首项的样本绝对序号 —— 等值槽逐槽入列构成槽流连续 pending 后缀
    [r0, N), 闭合/弃摊时按摊配份额定影; cov = 开放项覆盖毫秒前缀和(cov[j] = Sigma
    前 j 项按 r0 对齐; cov[0] = **已裁前缀** —— compact 把 base 之前的开放项覆盖折入
    首元素(旧面 run[3] run_prefix 同手法, 评审 #6), 闭合摊配以 cov[0] 作 _seam_spread_delta
    的 run_prefix 入参, 累计算术守恒: 被裁项的 cum 权重保留、其份额弃入(冷算 g=None
    项 bucket_add 弃入同判)); all_z = 开放项 z 形签名的 **all(z) 真单点**(旧面逐项 z 的
    唯一消费点是 all(), 逐项同值展开判据逐位同; 空游程恒 True = 空 all() 真值同判);
    fin_delta/fin_cov = 已定影样本的增量/覆盖前缀和(与主样本数组同 base 对齐, 覆盖
    [base, r0), fin[j] = Sigma [base, base+j) —— 含跨裁剪死区的基线和, 区间查询恒尾差分)。"""

    __slots__ = ("value", "anchor_ts", "r0", "cov", "all_z", "fin_delta", "fin_cov")

    def __init__(self) -> None:
        self.value: Optional[int] = None
        self.anchor_ts: float = 0.0
        self.r0 = 0
        self.cov = array("q", [0])
        self.all_z = True
        self.fin_delta = array("q", [0])
        self.fin_cov = array("q", [0])


class _GroupFoldState:
    """分组折叠持久状态(差分链/标记面标量 + 逐样本前缀和数组 + 两方向游程):
    样本绝对序号 = [0, N), base = 前缀数组对齐的绝对序号起点(裁剪压缩只前移 base,
    绝对序号恒定 —— 游程 r0/响应组界全按绝对序号运算)。"""

    __slots__ = (
        "prev_slot",
        "prev_chain_end",
        "last_was_null",
        "marked_ts",
        "dl",
        "up",
        "ts",
        "brk",
        "tdl",
        "tdlc",
        "tup",
        "tupc",
        "N",
        "base",
        "marks",
        "dips",
    )

    def __init__(self) -> None:
        self.prev_slot: Optional[tuple] = None  # 上一消费观测槽 (ts, dl_total, up_total) —— 差分链
        self.prev_chain_end: Optional[float] = None  # 末已见槽 ts(真空判定/活尾去重基准, 全槽推进)
        self.last_was_null = False  # n 游程折叠去重旗(全槽推进, 与窗界无关, 冷算同构)
        self.marked_ts: Optional[float] = None  # 自上一消费观测槽以来末个已判标记位置
        self.dl = _DirRun()
        self.up = _DirRun()
        self.ts = array("d")  # 样本 ts([base, N), 升序 —— 消费序 = 槽时序)
        self.brk = array("q", [0])  # broke 计数前缀(brk[j] = Sigma [base, base+j))
        self.tdl = array("q", [0])  # tot_dl 非 None 项之和前缀
        self.tdlc = array("q", [0])  # tot_dl 非 None 项计数前缀(None = 基线缺失/重置面)
        self.tup = array("q", [0])
        self.tupc = array("q", [0])
        self.N = 0
        self.base = 0
        self.marks: list = []  # 显式空值点 t 升序(入列面 t >= 当轮 t0, 响应前裁到存活面)
        self.dips: list = []  # ts 非降破例位置(绝对样本序号, 升序; eps 带内回退槽防御面
        # —— 冷算组末 t = 组内 ts 最晚者, 单调段末位即最晚, 破例组走稀疏表旁路全组取 max)

    # ---------- 前缀裁剪压缩(摊还 O(1)) ----------

    def compact(self, new_base: int) -> None:
        """前缀死区压缩: 数组对齐点前移到 new_base(响应窗首样本序号; 单调不减)。
        前缀和数组切片后首元素 = 跨死区的基线和, 区间查询公式(尾差分)不变式保持;
        切到空(开放游程 r0 已在新 base 之前, 无可保留定影项)保底末元素作基线和,
        使后续定影追加的衔接位(base + len - 1)恒成立; ts 为明值数组直切。
        开放游程项地平线裁剪(评审 #6, 旧面 run[3] 前缀承袭): base 之前的开放项覆盖
        折入 cov[0](= _seam_spread_delta 的 run_prefix 载体), del cov[:k] + r0 前移
        —— 被裁项 cum 权重保留(闭合摊配算术守恒)、份额弃入(被裁项恒在窗前沿之前,
        冷算 g=None 项 bucket_add 弃入同判); dips 同步裁剪(窗沿前破例位永不进组)。"""
        s = new_base - self.base
        if s <= 0:
            return
        self.ts = self.ts[s:]
        for name in ("brk", "tdl", "tdlc", "tup", "tupc"):
            a = getattr(self, name)
            cut = min(s, len(a) - 1)
            setattr(self, name, a[cut:])
        for run in (self.dl, self.up):
            for name in ("fin_delta", "fin_cov"):
                a = getattr(run, name)
                cut = min(s, len(a) - 1)
                setattr(run, name, a[cut:])
            k = min(max(0, new_base - run.r0), len(run.cov) - 1)  # base 前开放项数(裁剪面)
            if k:
                del run.cov[:k]  # cov[0] = 旧基线和 + 被裁项覆盖合计(= run_prefix)
                run.r0 += k
        if self.dips:
            del self.dips[:bisect_left(self.dips, new_base)]
        self.base = new_base

    # ---------- 批次时序守卫(fail-fast, 折叠前先验) ----------

    def guard_batch(self, slots: tuple, last: Optional[float] = None) -> Optional[float]:
        """槽批次时序守卫(_guard_slot_order 同款判据): 槽 ts 非降(容差 _V4_VACUUM_EPS_S)。
        !旧 is_hold 持有槽拒收支已随持有面退役删除(V4Slot.is_hold 字段同批退役 ——
        v4_live_tail_slots 复原即纯槽序, 持有延伸分支不存在)。last = 批前衔接锚(链上
        末槽 ts, 跨批次链式校验), 返回批末槽 ts 供下批续链。折叠前先验, 违一即 raise
        不落任何状态。"""
        if last is None:
            last = self.prev_chain_end
        for s in slots:
            if last is not None and s.ts < last - _V4_VACUUM_EPS_S:
                raise ValueError(f"槽流时序倒挂: 槽 {s.ts!r} 先于前槽 {last!r}")
            last = s.ts
        return last

    # ---------- 槽折叠(增量面唯一入口) ----------

    def feed(self, slots: tuple, t0: float, t1: float, null_lo: float) -> None:
        """槽批次折叠(语义 = assemble_group_points 槽循环的增量平移, 判读单点全部承袭:
        _slot_null_marks 标记判定 / _bucket_delta totals 差分 / _seam_spread_delta 摊配):
        - 标记面: 全槽判定(含窗外/窗尾外槽), 入列面 [null_lo, t1) 且 t >= t0, marks[-1]
          同秒去重 —— 调用方保证 marks 已裁到 [t0, ...) 存活面, 与冷算「每请求新列表 +
          全槽重判」的去重前驱逐位同构(历史标记 t >= t0 恒在列, 新标记判据逐位同);
          marked_ts 断连面 = 判得标记位置回写(凡 null_lo <= t < t1 含窗外标记, 末个
          判得者胜出), 跨 feed 批次(块界/天界/磁盘批->活尾批)存活, 消费观测槽复位
          —— 旧 _V4SeriesFold.fold 的 marked_ts 语义逐位对齐(评审 #4);
        - 消费面: obs 槽 null_lo <= ts < t1 才入样本(绝对序号 pos = N); prev_chain_end
          全槽推进; marked 随消费观测槽复位(窗尾外槽不复位, 冷算同判);
        - 速率面: 端点归属 = 样本自身序号, 组界留到响应期按前缀差分现推; 等值游程项
          pending(覆盖即时入开放分母, 份额闭合时定影), 其余即时定影。
        """
        prev_slot = self.prev_slot
        marked = self.marked_ts is not None
        marks = self.marks
        brk = self.brk
        tdl = self.tdl
        tdlc = self.tdlc
        tup = self.tup
        tupc = self.tupc
        ts_arr = self.ts
        for s in slots:
            mark_hit, self.last_was_null, mark_t = _slot_null_marks(
                s, self.prev_chain_end, self.last_was_null, null_lo, t0, t1, marks
            )
            if mark_t is not None:
                self.marked_ts = mark_t  # 断连面回写(旧面 marked_ts 语义: 凡判得即置位,
                # 含 t < t0 窗外标记 —— 跨 feed 批次存活, 消费观测槽复位; 评审 #4)
            marked = self.marked_ts is not None
            self.prev_chain_end = s.ts
            o = s.obs
            if o is None:
                continue  # n 槽: 标记判定已做, 无差分无样本
            if s.ts < null_lo or s.ts >= t1:
                continue  # 差分链窗外回看界之外 / 窗尾之后的槽不消费(冷算同判)
            pos = self.N
            dur_ms = 0 if prev_slot is None else int(round((s.ts - prev_slot[0]) * 1000))
            # 未观测秒 = 对跨 - 声称覆盖: 块内链式推进恒 0; 断口为正值
            unobs_ms = 0 if prev_slot is None else dur_ms - int(round(s.dt_s * 1000))
            # 覆盖时长(分母/摊配份额权重)= min(对跨, 声称覆盖): 连续链恒 = 对跨,
            # 含缝对只计声称覆盖 —— 缝秒不进分母(「未覆盖秒不归因」, 冷算同判)
            cov_ms_pair = dur_ms - max(0, unobs_ms)
            hole = unobs_ms > _V4_SEAM_NULL_S * 1000
            broke = unobs_ms > 0 or marked
            # totals 面: 本样本相邻快照差分(对上一消费观测槽, 含窗外种子基线)即时定影
            # (无摊配回写面); 重置/基线缺失贡献 0 不出洞, None 语义按计数前缀承载
            td = _bucket_delta(o[2], prev_slot[1]) if prev_slot is not None else None
            tu = _bucket_delta(o[3], prev_slot[2]) if prev_slot is not None else None
            ts_arr.append(s.ts)
            if pos > self.base and s.ts < ts_arr[-2]:
                self.dips.append(pos)  # ts 非降破例(eps 带内回退槽) —— 组末 t 旁路触发位(#5)
            brk.append(brk[-1] + (1 if broke else 0))
            tdl.append(tdl[-1] + (td if td is not None else 0))
            tdlc.append(tdlc[-1] + (1 if td is not None else 0))
            tup.append(tup[-1] + (tu if tu is not None else 0))
            tupc.append(tupc[-1] + (1 if tu is not None else 0))
            for d, cur, run in ((0, o[2], self.dl), (1, o[3], self.up)):
                if run.value is None or hole or cur < run.value:
                    # 游程立点: 基线缺失/停机洞(宁可丢弃不摊配)/计数器重置 —— 开放项
                    # 按 0 份额弃摊定影(其覆盖在入列时已计入开放分母, 冷算同构);
                    # 立点样本自身 delta = None 不入账(覆盖 0, 冷算同判)
                    self._close_run(run, pos, None)
                    run.value = cur
                    run.anchor_ts = s.ts
                    run.all_z = True
                    self._fin_append(run, pos, 0, 0)
                elif cur == run.value:
                    # 等值游程项入列(pending): 覆盖即时进开放分母, delta 份额留待闭合
                    run.cov.append(run.cov[-1] + cov_ms_pair)
                    run.all_z = run.all_z and s.is_zero  # all(z) 真单点(#7)
                else:
                    step = cur - run.value
                    span_ms = int(round((s.ts - run.anchor_ts) * 1000))
                    cov_ms = run.cov[-1] + cov_ms_pair
                    shares: dict = {}
                    run_items = self._run_items(run)
                    if run.cov[0]:
                        # 已裁前缀虚拟首项(评审 #6 算术守恒): 被裁项在冷算 run_list 中恒在
                        # (ts >= null_lo, 窗前沿之前 = g=None 项)—— 其份额冷算经
                        # bucket_add(None) 弃入但 acc 照常推进; 虚拟项以 key=None 重现该面
                        # (dd = 被裁项覆盖合计 = 冷算被裁段 cum 终值), 首保留项 share =
                        # target - 前缀累计目标, 与冷算逐位同(仅 run_prefix 入参的写法会把
                        # 被裁项份额质量错落到首保留项组)
                        run_items.insert(0, (None, run.cov[0], run.all_z, 0.0))
                    delta = _seam_spread_delta(
                        d,
                        step,
                        span_ms,
                        cov_ms,
                        dur_ms,
                        s.dt_s,
                        marked,
                        run_items,
                        0,
                        lambda k, _d, share: shares.__setitem__(k, share),
                    )
                    self._close_run(run, pos, shares)
                    run.value = cur
                    run.anchor_ts = s.ts
                    run.all_z = True
                    # 闭合样本即时定影: 摊配返回值(delta None = 断链不摊配)与覆盖同时
                    # 入账或同时不入(覆盖 0 不归因不造分母, 冷算同判)
                    if delta is not None and cov_ms_pair > 0:
                        self._fin_append(run, pos, delta, cov_ms_pair)
                    else:
                        self._fin_append(run, pos, 0, 0)
            prev_slot = (s.ts, o[2], o[3])
            self.marked_ts = None
            marked = False
            self.N = pos + 1
        self.prev_slot = prev_slot

    def _fin_append(self, run: _DirRun, pos: int, delta: int, cov: int) -> None:
        """样本 pos 的方向增量/覆盖定影入前缀(衔接位 = base + len - 1 恒 == pos)。"""
        run.fin_delta.append(run.fin_delta[-1] + delta)
        run.fin_cov.append(run.fin_cov[-1] + cov)
        run.r0 = pos + 1

    def _run_items(self, run: _DirRun) -> list:
        """开放游程项 -> _seam_spread_delta 入参形 (键 = 样本绝对序号, 覆盖毫秒, z 签名,
        ts 占位): 摊配算术只用覆盖与 all(z), ts 列不参与(占位 0.0, 避免跨 base 取值)。
        z 签名以 all_z 单点逐项展开(评审 #7: 旧面逐项 z 的唯一消费点是 all(), 逐项同值
        展开 all() 判据逐位同; 空游程走空列表分支, all() 空真值与 all_z 空真值同判)。"""
        cov = run.cov
        r0 = run.r0
        z = run.all_z
        return [(r0 + j, cov[j + 1] - cov[j], z, 0.0) for j in range(len(cov) - 1)]

    def _close_run(self, run: _DirRun, close_pos: int, shares: Optional[dict]) -> None:
        """开放游程项 [r0, close_pos) 定影: delta = 摊配份额(弃摊 = 0), 覆盖移入已定影
        前缀; base 之前的项(窗前沿已过, 响应面永不查询)不入前缀直接弃 —— 摊配份额对
        窗外项的弃入与冷算 bucket_add(key=None) 同判(窗沿单调, 已弃项永不被查询)。"""
        r0 = run.r0
        fd = run.fin_delta
        fc = run.fin_cov
        cov = run.cov
        start = r0 if r0 > self.base else self.base
        for pos in range(start, close_pos):
            j = pos - r0
            fd.append(fd[-1] + (shares.get(pos, 0) if shares else 0))  # 份额 0 的项不在表(冷算 if share 同判)
            fc.append(fc[-1] + cov[j + 1] - cov[j])
        run.r0 = close_pos
        # cov 闭合 = 对象替换非就地截断: 就地 del cov[1:] 会损毁「快照按长度还原」的
        # 回滚面(尾折闭合带开放项的游程后, 快照长度的开放项覆盖不可重建) —— 替换后
        # 旧数组对象原样存活, 快照按引用还原 + 尾折追加按长度截断即精确重建。新基线
        # 恒 0: 本闭合的 cov_ms 已消费全部开放项覆盖(含已裁前缀 —— 被裁项份额弃入、
        # cum 权重经 run_prefix 入账, 与冷算 g=None 项同判), 后继游程覆盖账 fresh 重开
        run.cov = array("q", (0, ))
        run.all_z = True

    # ---------- 响应推导(前缀差分, O(组数 + 标记数)) ----------

    def respond(self, t0: float, t1: float, si: float) -> GroupAssemblyResult:
        """当前窗 [t0, t1) 的分组点列推导(与冷算逐位等价的响应面):
        k 选取 = _pick_stride(窗内样本数, 窗内标记数, 预期样本数); 组 g = 窗内序号
        [g*k, (g+1)*k) 的样本区间 -> 前缀差分 -> 组值 = Sigma delta x 1000 / Sigma 覆盖
        (round 取整; 覆盖 0 时 broke 组 None / 无缝链首 0 线); 组点 t = 组末样本 ts;
        totals = 组内逐样本快照差分和(逐向 None = 全部基线缺失/重置); 显式空值点与组点
        按 (t, kind) 稳定合并(同刻空值在前, 冷算 items.sort 同判); 单方向前缀差分语义 =
        已定影段 [max(a, base), min(b, r0)) 的 fin 尾差分 + 开放段(等值 pending 项, delta
        恒 0)的开放覆盖尾差分。
        性能注: 本方法是温态每请求 O(组数) 主路径(A4 组图 = 成员数 x 组数), 前缀差分
        内联展开、数组/标量全部本地绑定、无标记窗跳过合并面。"""
        base = self.base
        ts = self.ts
        i_lo = base + bisect_left(ts, t0)
        n_win = self.N - i_lo
        marks = self.marks
        dips = self.dips
        stride, over_budget = _pick_stride(n_win, len(marks), (t1 - t0) / si)
        n_group = -(-n_win // stride) if n_win else 0
        brk = self.brk
        tdl = self.tdl
        tdlc = self.tdlc
        tup = self.tup
        tupc = self.tupc
        dl = self.dl
        up = self.up
        dl_fd = dl.fin_delta
        dl_fc = dl.fin_cov
        dl_oc = dl.cov
        dl_r0 = dl.r0
        up_fd = up.fin_delta
        up_fc = up.fin_cov
        up_oc = up.cov
        up_r0 = up.r0
        points: list = []
        totals: list = []
        for g in range(n_group):
            a = i_lo + g * stride
            b = a + stride
            if b > self.N:
                b = self.N
            ia = a - base
            ib = b - base
            # 组末 t = 组内 ts 最晚者(冷算 e[5] 判据): 单调段末位即最晚; eps 带内回退槽
            # (dips 破例位落组内)走旁路全组取 max(评审 #5, 稀疏表常态 O(1))
            t_end = ts[ib - 1]
            if dips:
                j = bisect_left(dips, a + 1)
                if j < len(dips) and dips[j] < b:
                    t_end = max(ts[ia:ib])
            # 单方向前缀差分(已定影段 [max(a,base), min(b,r0)) + 开放段覆盖; 开放段
            # delta 恒 0) —— 冷算组累加器同态的本地算术
            lo = ia if ia > 0 else 0
            hi = ib if ib < dl_r0 - base else dl_r0 - base
            if hi > lo:
                d_dl = dl_fd[hi] - dl_fd[lo]
                c_dl = dl_fc[hi] - dl_fc[lo]
            else:
                d_dl = 0
                c_dl = 0
            lo2 = ia + base if ia + base > dl_r0 else dl_r0
            if b > lo2:
                c_dl += dl_oc[b - dl_r0] - dl_oc[lo2 - dl_r0]
            hi = ib if ib < up_r0 - base else up_r0 - base
            if hi > lo:
                d_up = up_fd[hi] - up_fd[lo]
                c_up = up_fc[hi] - up_fc[lo]
            else:
                d_up = 0
                c_up = 0
            lo2 = ia + base if ia + base > up_r0 else up_r0
            if b > lo2:
                c_up += up_oc[b - up_r0] - up_oc[lo2 - up_r0]
            broke = brk[ib] - brk[ia] > 0
            dl_v = int(round(d_dl * 1000 / c_dl)) if c_dl > 0 else (None if broke else 0)
            up_v = int(round(d_up * 1000 / c_up)) if c_up > 0 else (None if broke else 0)
            tot_dl = tdl[ib] - tdl[ia] if tdlc[ib] > tdlc[ia] else None
            tot_up = tup[ib] - tup[ia] if tupc[ib] > tupc[ia] else None
            points.append({"t": t_end, "dl": dl_v, "up": up_v})
            totals.append({"t": t_end, "dl": tot_dl, "up": tot_up})
        if marks or dips:
            # 合并排序面: 显式空值点与组点按 (t, kind) 稳定合并(冷算 items.sort 同判);
            # dips 非空时组点 t 可非单调(eps 带回退组末), 无标记也须按 t 排序(冷算同)
            items = [(p["t"], 1, p, tt) for p, tt in zip(points, totals)]
            items += [(t, 0, {"t": t, "dl": None, "up": None}, None) for t in marks]
            items.sort(key=lambda it: (it[0], it[1]))
            points = [it[2] for it in items]
            totals = [it[3] for it in items]
        return GroupAssemblyResult(points=tuple(points), totals=tuple(totals), stride=stride, over_budget=over_budget)

    # ---------- 快照回滚(活尾折叠专用, O(1)) ----------

    def snapshot(self) -> tuple:
        """活尾折叠前快照: 全部可变面长度 + 标量 + 游程覆盖数组引用(回滚 = 截断 + 还原,
        O(1))。cov 按引用捕获: 闭合以对象替换实现(#6), 替换后的旧数组原样存活, 回滚
        按引用还原 + 尾折追加按长度截断即精确重建(评审 #6 连带修: 旧 in-place 截断面
        在「尾折闭合带开放项游程」时不可逆 —— 潜在状态损毁面一并消除)。"""
        return (
            self.prev_slot,
            self.prev_chain_end,
            self.last_was_null,
            self.marked_ts,
            self.N,
            len(self.ts),
            len(self.brk),
            len(self.tdl),
            len(self.tdlc),
            len(self.tup),
            len(self.tupc),
            len(self.marks),
            len(self.dips),
            self.dl.value,
            self.dl.anchor_ts,
            self.dl.r0,
            self.dl.cov,
            len(self.dl.cov),
            self.dl.all_z,
            len(self.dl.fin_delta),
            len(self.dl.fin_cov),
            self.up.value,
            self.up.anchor_ts,
            self.up.r0,
            self.up.cov,
            len(self.up.cov),
            self.up.all_z,
            len(self.up.fin_delta),
            len(self.up.fin_cov),
        )

    def rollback(self, snap: tuple) -> None:
        """还原到快照态(活尾折叠之后的一切变异弃置): 数组截断 + 标量还原 + cov 按引用
        还原(闭合对象替换的旧数组原样存活, 尾折 join 追加按长度截断即精确重建)。
        prev_chain_end 还原到磁盘推进值(活尾折叠期它的推进不入持久态, 下轮磁盘游标
        续展或重折活尾, 不重不漏)。"""
        (
            self.prev_slot, self.prev_chain_end, self.last_was_null, self.marked_ts, n, n_ts, n_brk, n_tdl, n_tdlc,
            n_tup, n_tupc, n_marks, n_dips, dl_v, dl_a, dl_r0, dl_cov, dl_ncov, dl_az, dl_nfd, dl_nfc, up_v, up_a,
            up_r0, up_cov, up_ncov, up_az, up_nfd, up_nfc
        ) = snap
        del self.ts[n_ts:]
        del self.brk[n_brk:]
        del self.tdl[n_tdl:]
        del self.tdlc[n_tdlc:]
        del self.tup[n_tup:]
        del self.tupc[n_tupc:]
        del self.marks[n_marks:]
        del self.dips[n_dips:]
        self.N = n
        for run, v, a, r0, cov_ref, ncov, az, nfd, nfc in (
            (self.dl, dl_v, dl_a, dl_r0, dl_cov, dl_ncov, dl_az, dl_nfd, dl_nfc),
            (self.up, up_v, up_a, up_r0, up_cov, up_ncov, up_az, up_nfd, up_nfc),
        ):
            run.value = v
            run.anchor_ts = a
            run.r0 = r0
            run.all_z = az
            run.cov = cov_ref  # 引用还原(闭合对象替换的旧数组原样存活, 见 snapshot)
            del run.cov[ncov:]  # 尾折 join 追加按长度截断
            del run.fin_delta[nfd:]
            del run.fin_cov[nfc:]


class _GroupCacheEntry:
    """分组点列缓存条目(系列键 x 窗): 采样间隔指纹 + 读集前沿锚 + 天游标 + 折叠态"""
    __slots__ = ("si", "first_date", "day_cursors", "st")

    def __init__(self, si: float, first_date: Optional[str]) -> None:
        self.si = si
        self.first_date = first_date
        self.day_cursors: dict = {}  # date_str -> _V4BucketDayCursor(槽流前缀消费游标)
        self.st = _GroupFoldState()


class V4SeriesGroupCache:
    """raw 段窗样本分组点列缓存(T1c-1, 计划 26-11-18-0037 §03; 桶值缓存的改造转世)

    - 键结构: (系列键, window) -> 条目; 条目内 = 天游标(_V4BucketDayCursor 承袭, 只展
      新增槽) + 分组折叠持久状态(逐样本前缀和)。响应窗 [t0, t1) 每请求现取(栅格随 now
      平移), 组界按窗首样本序号现推 —— 滑动窗/k 上调都只是前缀差分, 不重算全窗。
    - LRU 上限 = 128 条目(承袭旧桶缓存口径: 组图 M(可达 30) x 3 窗位 + 全局/单种余量;
      命中移队尾, 最久未用先逐出)。内存账见模块 docstring 与 entry_stats。
    - 逐位等价根基: 折叠面语义与 assemble_group_points 共用同一批判读单点(_slot_null_marks
      / _bucket_delta / _seam_spread_delta / _pick_stride), 持久状态 = 槽流前缀的纯函数
      (消费集恒为前缀: null_lo/t1 两界单调不减 —— null_lo 平移由 sanitize 对齐链基,
      锚点滑出回看界即冷重建); 活尾折在快照点上响应后回滚。同窗同输入 -> 同
      points/totals/stride/over_budget(新电池主断言逐拍对账)。
    - 多实例隔离: 缓存实例随 QbTrafficChartApi 每域 router 一份(构造期预建)—— 实例
      身份即隔离边界(qB 多实例不同 data_dir 天然不同实例), 键不需另含实例身份。
    """

    #: 条目数上界(LRU; 旧桶缓存 MAX_ENTRIES 同值承袭)
    MAX_ENTRIES = 128

    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._max = max(1, int(max_entries))
        self._lock = Lock()
        # (系列键, window) -> _GroupCacheEntry
        self._entries: "OrderedDict" = OrderedDict()

    def series_result(self, key: str, days: tuple, grid, raw_tail_slots: tuple, sample_interval: float) -> tuple:
        """单系列 raw 段窗 -> 样本分组装配结果(缓存命中/增量推进/冷重建三态合一)。

        days = V4DayCache.read_window 产物 ((date_str, V4ParsedDay | None), 日期升序);
        grid = 请求栅格(raw 段窗); raw_tail_slots = 活尾快照纯槽复原(v4_live_tail_slots
        的无 now 形态 —— 持有延伸分支已随持有面退役, 复原即纯槽序; 复原在调用方、
        去重在锁内); sample_interval = 生效采样间隔(配置指纹 + 消费下界/预期样本数入参)。
        返回
        (GroupAssemblyResult, blocks, tail_slots) —— blocks 供组端点空态判据
        (v4_earliest_row_ts 承袭)复用, tail_slots = 去重后的活尾槽序(空态判据计入)。
        OSError 不经过本类(调用方读文件在先), 读取竞态走端点 last-good 兜底(§08)。
        """
        if grid.segment != "raw":
            raise ValueError(f"分组点列缓存仅服务 raw 段窗: {grid.name!r}({grid.segment!r})")
        t0, t1, si = _check_window(grid.t0, grid.t1, sample_interval)
        null_lo = group_null_lo(t0, si)  # 消费下界单点(与装配内部同源, 评审 #3)
        blocks = tuple(blk for _d, parsed in days if parsed for blk in parsed.blocks)
        with self._lock:
            ck = (key, grid.name)
            ent = self._entries.get(ck)
            if ent is not None and ent.si != si:
                ent = None  # 配置面失效: 消费下界/预期样本数/k 整体改变, 冷重建(失效面 c)
            if ent is not None and (days[0][0] if days else None) != ent.first_date:
                ent = None  # 读集前沿变化: 差分链起点重锚, 冷重建(失效面 c2)
            if ent is None:
                ent = _GroupCacheEntry(si, days[0][0] if days else None)
                self._cold_seed(ent, days, t0, t1, null_lo)
            else:
                self._advance(ent, days, t0, t1, null_lo)
            st = ent.st
            if st.marks:
                del st.marks[:bisect_left(st.marks, t0)]  # 窗沿已过的标记退役(响应面死区)
            tail_slots = self._tail_slots(raw_tail_slots, st.prev_chain_end)
            snap = st.snapshot()
            if tail_slots:
                st.guard_batch(tail_slots)
                st.feed(tail_slots, t0, t1, null_lo)
            res = st.respond(t0, t1, si)
            st.rollback(snap)
            i_lo = st.base + bisect_left(st.ts, t0)
            dead = i_lo - st.base
            if dead >= _COMPACT_MIN_DEAD and dead * 2 >= st.N - st.base:
                st.compact(i_lo)
            self._entries[ck] = ent
            self._entries.move_to_end(ck)
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)
            return res, blocks, tail_slots

    def entry_stats(self, key: str, window: str) -> str:
        """单条目驻留账(内存打印面, 旧桶缓存 _response_points 形态对应件): 样本驻留数
        x 单样本前缀数组字节 + 开放游程项数(覆盖 8B + z 签名 1B)-> MB 估算(基准电池
        打印用; 前缀数组按元素字节计, 不逐对象取 sizeof)。"""
        with self._lock:
            ent = self._entries.get((key, window))
            if ent is None:
                return "no-entry"
            st = ent.st
            n = st.N - st.base
            n_run = (st.N - st.dl.r0) + (st.N - st.up.r0)
            bytes_est = n * 73 + n_run * 9
            return f"样本驻留={n}(约{bytes_est / 1e6:.2f}MB) 开放游程项={n_run} 标记={len(st.marks)} base={st.base}"

    # ---------- 内部(锁内调用) ----------

    def _tail_slots(self, raw_tail_slots: tuple, disk_end: Optional[float]) -> tuple:
        """活尾槽序 -> 去重后槽序(S6 读侧接缝, T1b _tail_slots_plain 的锁内面): 复原
        (v4_live_tail_slots 无 now 形态, 持有延伸分支已退役)在调用方, 本方法只做与磁盘链
        的按 ts 去重 —— 同 ts 槽 = 同一记录「写侧游标推进」与「落盘后重算」的恒等形态,
        保留严格更晚后缀即不重不漏(去重基准 = 已展开磁盘链末槽 prev_chain_end, 生产恒
        == 全链末槽, 见模块 docstring「已知边界」); 新装配契约要求槽流已按 ts 去重
        (重复槽会错位分组锚)。"""
        slots = raw_tail_slots
        if slots and disk_end is not None:
            slots = tuple(s for s in slots if s.ts > disk_end + _V4_VACUUM_EPS_S)
        return slots

    def _cold_seed(self, ent: _GroupCacheEntry, days: tuple, t0: float, t1: float, null_lo: float) -> None:
        """冷折叠(首次/失效重建): 全部天文件块展开至窗尾 + 折叠, 天游标随展开推进
        (_day_cursor_after 承袭); 停驻块余量(ts >= t1)不喂不判 —— 生产形态磁盘链恒
        止于 now 之前, 见模块 docstring「已知边界」。"""
        st = ent.st
        for date_str, parsed in days:
            cur = _V4BucketDayCursor()
            ent.day_cursors[date_str] = cur
            if parsed is None:
                continue
            last_i = len(parsed.blocks) - 1
            for i, blk in enumerate(parsed.blocks):
                slots, bcur, exhausted = v4_block_slots_from(blk, (0, 0, None, None, None), t1)
                if slots:
                    st.guard_batch(slots)
                    st.feed(slots, t0, t1, null_lo)
                _day_cursor_after(cur, blk, bcur, exhausted, i == last_i)

    def _advance(self, ent: _GroupCacheEntry, days: tuple, t0: float, t1: float, null_lo: float) -> None:
        """增量推进: 窗界再对齐(sanitize) -> 逐天校验游标 -> 只展开游标之后的槽组 -> 折叠。
        游标校验不过(结构性变化, 失效面 b)或游程锚点滑出回看界(sanitize 防御路径)=
        整条目冷重建(就地替换折叠态/游标, 同输入重算恒等)。展开批次先全量守卫再统一
        折叠(守卫 fail-fast 不落任何状态 —— 游标推进/折叠原子于校验通过)。"""
        st = ent.st
        if self._sanitize(st, null_lo):
            self._rebuild(ent, days, t0, t1, null_lo)
            return
        reset = False
        batches = []  # (slots, cur, blk, bcur, exhausted, is_last)
        for date_str, parsed in days:
            cur = ent.day_cursors.get(date_str)
            if cur is None:
                cur = ent.day_cursors[date_str] = _V4BucketDayCursor()  # 新日期(该天首读)
            if parsed is None:
                if cur.starts or cur.cur_start is not None:
                    reset = True  # 天文件消失(删除/移动) —— 结构性变化
                    break
                continue
            if not _v4_bucket_day_cursor_valid(cur, parsed.blocks):
                reset = True
                break
            blocks = parsed.blocks
            last_i = len(blocks) - 1
            n_done = len(cur.starts)
            if cur.cur_start is not None:
                blk = blocks[n_done]
                slots, bcur, exhausted = v4_block_slots_from(
                    blk, (cur.rec_idx, cur.slots_done, cur.last_ts, cur.run_base, cur.run_spacing), t1
                )
                batches.append((slots, cur, blk, bcur, exhausted, n_done == last_i))
                next_i = n_done + 1
            else:
                next_i = n_done
            for i in range(next_i, len(blocks)):
                blk = blocks[i]
                slots, bcur, exhausted = v4_block_slots_from(blk, (0, 0, None, None, None), t1)
                batches.append((slots, cur, blk, bcur, exhausted, i == last_i))
        if reset:
            self._rebuild(ent, days, t0, t1, null_lo)
            return
        # (无「已滑出读集的天游标退役」支: 读集日期收缩恒伴 days[0][0] 更替 -> c2
        # 冷重建先于本循环 —— 旧桶缓存的逐日退役面在本结构下不可达, 不留死代码)
        last = st.prev_chain_end
        for slots, *_rest in batches:
            last = st.guard_batch(slots, last)
        for _slots, cur, blk, bcur, exhausted, is_last in batches:
            _day_cursor_after(cur, blk, bcur, exhausted, is_last)
        for slots, *_rest in batches:
            if slots:
                st.feed(slots, t0, t1, null_lo)

    def _sanitize(self, st: _GroupFoldState, null_lo: float) -> bool:
        """增量折叠前的窗界再对齐(语义承袭 _V4SeriesFold.sanitize): 全量现算只消费
        ts >= null_lo 的槽 —— 基线槽/标记点已滑出回看界则清置(链首无基线/无标记同态);
        游程锚点滑出回看界返回 True = 调用方整条目冷重建(不做局部重建: 被裁项的覆盖
        累计与开放项摊配份额不可局部重推, 与全量现算非逐字段等价)。"""
        if st.prev_slot is not None and st.prev_slot[0] < null_lo:
            st.prev_slot = None
        if st.marked_ts is not None and st.marked_ts < null_lo:
            st.marked_ts = None
        for run in (st.dl, st.up):
            if run.value is None and run.r0 >= st.N:
                continue  # 未立游程(锚点 0.0 是初值哨兵, 非「滑出」)
            if run.anchor_ts < null_lo:
                return True
        return False

    def _rebuild(self, ent: _GroupCacheEntry, days: tuple, t0: float, t1: float, null_lo: float) -> None:
        """整条目冷重建(失效面 b 兜底): 清游标与折叠态, 同输入重算恒等。"""
        ent.day_cursors = {}
        ent.st = _GroupFoldState()
        self._cold_seed(ent, days, t0, t1, null_lo)
