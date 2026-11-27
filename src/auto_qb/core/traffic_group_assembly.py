"""traffic_group_assembly: 样本分组装配读侧纯函数(计划 26-11-18-0037 阶段 1; §03 读侧契约 = 单点)

v4 样本槽流(V4Slot 序列, 由 traffic_store_codec.v4_block_slots / v4_block_slots_from 展开;
聚合接缝经 traffic_grid.v4_series_slots 平展) -> 样本分组点列 —— 26-11-15-1104 挂钟桶面
(F2 归桶 / 桶值缓存 / 持有回填 / F3 尾桶持有)的替代读侧。与旧面的关系:
- 分组锚(k=1 与 k>1 两档, 26-11-27 S1a F3 改锚 —— 计划 26-11-26-2333 INV-3 后端半边):
  k=1 逐样本直通(组 = 单样本, 组键 = 窗内序号; 抖动样本不合并 —— 每样本恒一点);
  k>1 = 时间桶锚(单点 group_bucket): 组 = 样本 ts 落入的时间桶 floor(ts / (k*si)),
  桶相位 = epoch 原点、桶宽 = 组距标称 k x si —— 组界是纯 ts 函数, 与窗位置无关:
  滑动窗对账(30s GET)的已闭合组点逐位不动(同批样本恒同桶), 对账只补精度不改形状
  (S0 取证: 旧「窗内第 [i*k,(i+1)*k) 个样本」锚随窗沿平移整列换格, 30m 窗每 30s 对账
  dropped~407-410 即此根因, 报告 26-11-27-0526 症状3)。窗首跨界桶只收窗内成员
  (窗外样本弃入同旧面 g=None), 桶值随窗沿左移单点重写一次后随桶整体出窗 —— 有界,
  不再整列改写。stride 翻 k(缺口标记数变化)时桶宽整体重对齐 = 真换窗语义(前端 rewin,
  计划 F4 step 名义变化); 同 tick 采样的成员系列槽 ts 序列恒同 -> 逐成员分组点列同构
  保留(桶界同式同源), 组端点 Sigma 现算可用。
- 差分链 / 接缝摊配 / null 标记判定承袭旧面单点, 不重写: 摊配 = traffic_grid.
  _seam_spread_delta(原样提取件); 重置/基线缺失三层口径 = traffic_grid._bucket_delta;
  null 标记 = 旧 fold 的 n 槽(floor 取整 + last_was_null 去重)与块间真空(首槽声称覆盖
  接不住链终值, t = int(prev_chain_end))判定, 承袭为槽粒度(块内 dt 链连续 -> 与旧
  「块首判定」等价; 同秒真空+n 双标记折叠一点为新契约收紧, 详 _slot_null_marks)。
  !旧挂钟桶面(_V4SeriesFold / V4SeriesBucketCache / 持有回填)已随 T1c-2 退役删除。

契约要点(计划 §03 逐条):
- points = ({t, dl, up} | {t, dl: None, up: None}) 升序点列: 每点必带 t(真值点 = 组末样本
  ts, k=1 即样本 ts, k>1 即桶末样本 ts; 空值点 = floor(ts)), 空值点 = n 游程/块间真空
  折叠一点。旧「null 无 t 的定长桶数组」形态不出现。
- 输出形状 = 脊柱点列 + 活尾组点(INV-1/INV-3): 真值点按桶闭合二分 —— 已闭合桶(时间桶
  已被后继样本越过)为脊柱点(跨请求逐位不动), 末个真值点 = 活尾组点(进行中桶, 组内已落
  样本真实均值, 每 tick 随样本收敛一次); tail_open = points[-1] 是否活尾组点(按发射列
  尾点身份推导, k>1 且尾项为最高时间桶组点; k=1 直通窗尾点恒定不折叠 = False)。组闭合迁移: 后继样本落入新桶 -> 旧桶点即成
  脊柱(t/值逐位不变), 新桶点为活尾组点。
- 分组口径 k: 初值 = max(1, ceil(窗内预期样本数 / 500)); 窗内有缺口标记时上调直至
  「组点数 + 空值点数 <= 500」(MAX_RAW_POINTS, 模块常量非配置键 —— 黄金法则 4: 只有配置
  键才进 validate_config); k 上限 = 窗内实际样本数; 缺口标记数 >= 500 时预算数学不可达
  —— 按 k 上限交付并置 over_budget=True 如实标注(诚实优先于预算, 不静默), 缺口显式
  空值语义不弃。k=1 逐样本(1m/5m); k>1 组内均值 = Sigma delta / Sigma dt(与现行桶均值
  同口径: 端点归属 + 覆盖毫秒分母 + round 取整, 组键换时间桶); 组距标称 = k x si =
  时间桶宽(meta.interval_s 同源积, 前端活尾组折叠 S2/F1 与对账等价电池消费同式)。
- 尾组: 末组可不满 k(进行中), t = 最新样本 ts, 值 = 组内已落样本真实均值 —— 恒真值
  无克隆无持有(持有面随桶面退役; 每 tick 随样本更新由重装配自然承载)。
- 字节守恒: 差分链/totals 语义不变 —— 漏采区间字节含在后继样本快照差分里(短缝摊配
  回收 / 长缝断链丢弃, 诚实性同旧面), 分组只是重新划界, 不造字节不丢字节; totals =
  组粒度快照差分和: 逐样本相邻快照差分(_bucket_delta 三层口径: 计数器重置/基线缺失
  -> 逐向 None)按端点所属组求和, 重置/基线缺失贡献 0 不出洞(承袭 group_totals_points
  的「先差分再求和」组聚合口径)—— 求和项与分组粒度无关, Sigma(totals) 分组前后恒等,
  窗首组含窗外种子基线到窗首样本的差分(D3 窗首种子的 totals 面)。

设计纪律: 纯函数无时钟 —— t0/t1/采样间隔一律入参(幂等性黄金法则); 入参非法(槽乱序/
时间倒挂/窗口非法)fail-fast raise, 不静默修复。
"""
import math
from dataclasses import dataclass
from typing import Optional

from .traffic_grid import (
    _V4_SEAM_LOOKBACK_S,
    _V4_SEAM_NULL_S,
    _V4_VACUUM_EPS_S,
    _bucket_delta,
    _seam_spread_delta,
    v4_series_slots,
)
from .traffic_store import V4Slot

#: 组点 + 空值点共用预算(计划 §03 分组口径 / §04 阶段 0 常量表): 模块常量非配置键,
#: 与旧面 MAX_RAW_BUCKETS 同值的读侧预算口径换代(挂钟桶 -> 样本分组)。
MAX_RAW_POINTS = 500


@dataclass(frozen=True)
class GroupAssemblyResult:
    """样本分组装配结果(§03 读侧契约的响应面原料, 单系列)

    points = 样本分组点列(tuple of dict, 升序): 真值点 {"t", "dl", "up"}(dl/up = 组内均值
    bytes/s, round 取整; 逐向 None = 断链未知)与显式空值点 {"t", "dl": None, "up": None}
    (缺口); totals 与 points 等长同构: 组粒度快照差分和 {"t", "dl", "up"}(组内逐样本
    相邻快照差分求和, 逐向 None = 全部差分对基线缺失/重置)或 None(空值点)。stride =
    分组口径 k(组距标称 = k x 采样间隔, 供 meta schema=2 / stride=k —— meta 组装本身
    不在本模块); over_budget = 缺口标记数 >= MAX_RAW_POINTS 的超预算如实标注(k 已按
    上限交付, 空值语义不弃)。

    tail_open(26-11-27 S1a F3, 脊柱/活尾二分标注; 26-11-27 评审修复: 推导按发射列尾点
    身份, 不按 totals): points[-1] 是否活尾组点 —— k>1 且尾项为组点且其 t 属最高时间桶
    (进行中桶, 组内已落样本真实均值, 随样本收敛)时 True; 前端折叠与对账电池据此把列
    二分为脊柱 points[:-1] + 活尾 points[-1]。空值点与组点按 (t, kind) 升序合并、同刻
    空值点在前 —— 空值点与活尾组点相对次序由此唯一确定: 尾随空值点(t 大于活尾组点 t,
    如末槽 n 槽)居末时该空值点归脊柱且 tail_open=False; 整窗重置/链首(totals 全 None)
    不影响判定(组点身份不看 totals)。k=1 直通窗(尾点恒定不折叠)与无组点窗(纯缺口/
    空列)恒 False。脊柱点跨请求逐位不动(k>1 组键 = 时间桶, 与窗位置无关)是对账零形状
    改写(INV-3)的装配面保证。
    """

    points: tuple
    totals: tuple
    stride: int
    over_budget: bool
    tail_open: bool = False


def _check_window(t0: float, t1: float, sample_interval_s: float) -> tuple:
    """窗口/采样间隔入参校验(fail-fast, 不静默修复): 三判据独立 —— 有限数值、t1 > t0、
    si > 0(违一即 raise)"""
    for name, v in (("t0", t0), ("t1", t1), ("sample_interval_s", sample_interval_s)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError(f"非法 {name}(须有限数值): {v!r}")
    if t1 <= t0:
        raise ValueError(f"窗口非法(须 t1 > t0): t0={t0!r} t1={t1!r}")
    if sample_interval_s <= 0:
        raise ValueError(f"非法 sample_interval_s(须正): {sample_interval_s!r}")
    return float(t0), float(t1), float(sample_interval_s)


def _guard_slot_order(slots: tuple) -> None:
    """槽流时序守卫(fail-fast, 判据承袭旧面 _guard_group_order): 槽 ts 非降(容差同
    _V4_VACUUM_EPS_S); 倒挂 = 输入槽流结构性异常(调用面槽序被破坏), fail-fast 拒装配,
    不静默产出负对跨的脏速率。同刻(及 -eps 带内)重复槽不拒 —— 输入契约: 槽流须已按 ts
    去重, 重叠去重是调用方义务(旧面活尾按 ts 精确去重同款); 未去重的重复槽按同刻病理
    面处理(对跨 0 -> 覆盖 0 不归因, 不炸), 但重复样本会计入组序号(分组锚错位), 该形态
    由调用方去重义务排除而非此处静默修复。!旧 is_hold 持有槽拒收支已随持有面退役删除
    (V4Slot.is_hold 字段同批退役 —— 新契约无持有面, §03: 尾组恒真值无克隆)。"""
    prev_ts = None
    for s in slots:
        if not isinstance(s, V4Slot):
            raise TypeError(f"非 V4Slot 槽: {type(s).__name__}")
        if prev_ts is not None and s.ts < prev_ts - _V4_VACUUM_EPS_S:
            raise ValueError(f"槽流时序倒挂: 槽 {s.ts!r} 先于前槽 {prev_ts!r}")
        prev_ts = s.ts


def _slot_null_marks(
    s: V4Slot, prev_chain_end: Optional[float], last_was_null: bool, null_lo: float, t0: float, t1: float, marks: list
) -> tuple:
    """槽级 null 标记判定单点(承袭 _V4SeriesFold.fold 的 n 槽判定与块间真空判定, 形态
    改为显式空值点): 判得的标记 t 追加进共享 marks 列表(已按 [t0, t1) 过滤), 返回
    (marked, last_was_null, mark_t) —— mark_t = 本槽判得的标记位置(末个判得者; 无判得
    = None), 供增量折叠面回写 marked_ts 断连面(旧 _V4SeriesFold.fold 的 marked_ts 语义:
    凡 null_lo <= t < t1 的标记都置位, 消费观测槽复位; 同秒去重/append 判据不影响置位)。

    - 块间真空: 本槽声称覆盖(dt_s)接不住链终值 -> t = int(prev_chain_end); 判定来源
      承袭, 形态改为显式空值点。按槽粒度判定: 块内 dt 链连续(ts - dt_s 恰接前槽), 只在
      块界/断口触发, 与旧「块首判定」等价(扫描与装配两遍共用本函数, 判定面单点不分叉)。
    - n 槽: 连续 null 槽折叠为一个空值点(t = floor(首槽 ts); last_was_null 去重 ——
      观测槽复位)。
    - 同秒折叠(新契约收紧, 评审 1): 真空标记与紧随 n 槽标记可 floor 到同一秒 —— 旧面
      两源互不去重会出同刻双空值点, 违背 §03「缺口折叠一点」; 此处按 t 去重(标记 t 全流
      非降: 真空 t = int(前槽 ts) <= floor(本槽 ts), 故与列表末项比较即全量去重), 不同秒
      的真空/n 标记各自保留(来源语义不混)。
    - marked 门 = [null_lo, t1)(断连面, 影响后继差分 broke/摊配 —— 旧面标记按同界入列、
      发射期窗过滤; 新契约入列面直接按 [t0, t1) 过滤, 链面语义同构)。
    """
    marked = False
    mark_t: Optional[int] = None
    if prev_chain_end is not None and s.ts - s.dt_s > prev_chain_end + _V4_VACUUM_EPS_S:
        t = int(prev_chain_end)
        if null_lo <= t < t1:
            marked = True
            mark_t = t
            if t >= t0 and (not marks or marks[-1] < t):
                marks.append(t)
    if s.obs is None:
        t = int(math.floor(s.ts))
        if null_lo <= t < t1 and not last_was_null:
            marked = True
            mark_t = t  # 末个判得者胜出(真空后随 n 槽, 与旧面 marked_ts 末次写入同序)
            if t >= t0 and (not marks or marks[-1] < t):
                marks.append(t)
        last_was_null = True
    else:
        last_was_null = False
    return marked, last_was_null, mark_t


def _pick_stride(n_samples: int, n_marks: int, expected: float) -> tuple:
    """分组口径 k 选取(§03): 初值 = max(1, ceil(窗内预期样本数 / 500)); 缺口标记把
    「组点数 + 空值点数 <= 500」顶破时上调至 ceil(n_samples / (500 - n_marks))(预算
    条件随 k 单调 -> 直接取最小达标 k, 与「逐步上调」同终点); k 上限 = 窗内实际样本数
    (超之无组点收益)。缺口标记数 >= 500: 预算数学不可达(组点恒 >= 1), 按 k 上限交付
    并置 over_budget 如实标注, 空值语义不弃。返回 (stride, over_budget)。"""
    k_init = max(1, math.ceil(expected / MAX_RAW_POINTS))
    if n_marks >= MAX_RAW_POINTS:
        return max(1, n_samples), True
    k_need = math.ceil(n_samples / (MAX_RAW_POINTS - n_marks)) if n_samples else 1
    return min(max(k_init, k_need, 1), max(1, n_samples)), False


def group_bucket(ts: float, stride: int, si: float) -> int:
    """k>1 组键单点(26-11-27 S1a F3, 计划 26-11-26-2333): 时间桶锚 floor(ts / (k*si)) ——
    桶相位 = epoch 原点, 桶宽 = 组距标称 k x si。装配(本模块)与分组缓存(响应期组界
    现推)两侧均须经本函数取桶键, 前端活尾组折叠(S2/F1)与对账等价电池(S1b)以
    meta.interval_s(= k x si 同源积, _meta 单点同式)复算同式 —— 禁止任何一侧重 derive
    (漂移无 fail-fast, 同 group_null_lo 评审纪律)。floor 约定: ts 恰落桶界归后桶
    (确定性单值); 前端 Math.floor 同式逐位一致(IEEE 754 double 同算)。"""
    return math.floor(ts / (stride * si))


def group_null_lo(t0: float, sample_interval_s: float) -> float:
    """装配消费下界单点(公开): t0 - si - 回看界 —— 差分链消费下界(null 标记判定界/窗外
    种子 D3 回看给足)与读窗起点(traffic_qb read_window 起点)三处同源引用本函数, 不得
    各自重derive(漂移无 fail-fast, 评审 #3)。入参须已经 _check_window 校验。"""
    return t0 - sample_interval_s - _V4_SEAM_LOOKBACK_S


def assemble_group_points(slots, t0: float, t1: float, sample_interval_s: float) -> GroupAssemblyResult:
    """样本槽流 -> 样本分组点列(§03 读侧契约核心装配; 纯函数, 无时钟)

    slots = V4Slot 升序序列(单系列的槽流前缀/全量皆可; 消费下界 = t0 - si - 回看界,
    与旧面 _v4_null_lo 同式 —— 窗首种子 D3: 窗外前缀只作差分基线, 不产组点, 窗内首样本
    对窗外基线的差分落在窗首组); t0/t1 = 响应窗 [t0, t1); sample_interval_s = 标称采样
    间隔(k 初值与消费下界用)。两遍结构: 轻扫描(标记集 + 窗内样本数 -> 选 k)与装配折叠
    (差分链 + 组累加), 标记判定两遍共用 _slot_null_marks 单点。

    消费规则(承袭 fold): obs 槽 ts >= t1 窗尾外不消费; ts < 消费下界不进差分链;
    n 槽不分界全走标记判定(旧面同构); prev_chain_end 逐槽推进(含未消费槽 —— 旧面
    块尾游标终值同构, 真空判定基准不丢块)。差分对逐向独立(delta/摊配/重置), 端点
    (本槽)归属其组; 窗外槽无组(键 None)—— 摊配份额弃入(旧面份额入窗外桶、发射期
    窗过滤不外发, 响应面非整体等价 —— 窗首组除外显差异, 详 bucket_add 注释); 窗首跨界
    桶只收窗内成员(窗外同桶样本弃入, 桶值随窗沿左移单点重写一次后随桶出窗, S1a F3
    有界改写面)。组值 =
    Sigma delta * 1000 / Sigma 覆盖毫秒(round 取整);
    组内无有效差分对时 0 线(无缝链首, D4)或 None(断链: 缝 > 停机洞阈值/断连标记)。
    totals = 组内逐样本相邻快照差分(_bucket_delta, 对上一已消费观测槽)求和, 窗首组含
    窗外种子差分; 求和项与 k 无关 -> Sigma(totals) 分组前后恒等(字节守恒对账锚)。
    """
    t0, t1, si = _check_window(t0, t1, sample_interval_s)
    slots = tuple(slots)
    _guard_slot_order(slots)
    null_lo = group_null_lo(t0, si)  # 差分链消费下界(单点 group_null_lo, 旧 _v4_null_lo 同式)
    # 第一遍(轻扫描): null 标记集 + 窗内样本数 —— 选 k 依据; 标记判定与装配遍共用单点
    marks: list = []
    n_samples = 0
    prev_chain_end = None
    last_was_null = False
    for s in slots:
        _marked, last_was_null, _mark_t = _slot_null_marks(s, prev_chain_end, last_was_null, null_lo, t0, t1, marks)
        prev_chain_end = s.ts
        if s.obs is not None and t0 <= s.ts < t1:
            n_samples += 1
    stride, over_budget = _pick_stride(n_samples, len(marks), (t1 - t0) / si)
    # 第二遍(装配折叠): 差分链 + 摊配(共用 _seam_spread_delta 提取件) + 组累加
    emit_marks: list = []  # 装配遍标记集(与扫描遍同判定单点重推, 发射合并序用)
    # 组累加器: [dl_sum, dl_cov_ms, up_sum, up_cov_ms, broke, end_ts, end_dl_snap, end_up_snap,
    #            tot_dl, tot_up] —— tot_* = 组粒度快照差分和(逐样本 _bucket_delta 求和,
    #            None = 组内该向差分全为基线缺失/重置; 求和项与 k 无关 -> Sigma 分组前后恒等)
    accs: dict = {}
    dl_run: list = [None, 0.0, [], 0]  # 逐向游程状态(旧面同构): [游程值, 锚点 ts, 等值游程项, 前缀覆盖毫秒]
    up_run: list = [None, 0.0, [], 0]
    prev_slot: Optional[tuple] = None  # 上一已消费观测槽 (ts, dl_total, up_total) —— 差分链
    prev_chain_end = None
    marked = False
    last_was_null = False
    n_win = 0  # 窗内样本序号(分组锚: 组 = 序号 // k)

    def bucket_add(key, d, share) -> None:
        """摊配份额入组(旧面 bucket_add 同款; 键 = 等值游程槽的组标识): 窗外槽(键 None)
        无组可入直接弃 —— 旧面份额入窗外桶、发射期窗过滤不外发; 除 floor 对齐窗首桶内
        t0 前样本的差分与份额带随旧面首桶外显外, 窗外份额两面均不外显(响应面非整体
        等价, 窗内份额归组面同构)。组累加器必已存在(份额只落已消费窗内槽的组, 时序
        单调先建后用; 旧面的逐出裁剪防御随桶缓存退役, 本模块全量现算无逐出)。"""
        if key is None:
            return
        e = accs[key]
        if d == 0:
            e[0] += share
        else:
            e[2] += share

    for s in slots:
        mark_hit, last_was_null, _mark_t = _slot_null_marks(
            s, prev_chain_end, last_was_null, null_lo, t0, t1, emit_marks
        )
        if mark_hit:
            marked = True
        prev_chain_end = s.ts
        o = s.obs
        if o is None:
            continue  # n 槽: 标记判定已在 _slot_null_marks, 无差分无组
        if s.ts < null_lo or s.ts >= t1:
            continue  # 差分链窗外回看界之外的槽 / 窗尾之后的槽不消费(旧面同判)
        dur_ms = 0 if prev_slot is None else int(round((s.ts - prev_slot[0]) * 1000))
        # 未观测秒 = 对跨 - 本槽声称覆盖(dt_s): 块内链式推进恒 0; 断口为正值
        unobs_ms = 0 if prev_slot is None else dur_ms - int(round(s.dt_s * 1000))
        # 覆盖时长(本对的分母/摊配份额权重)= min(对跨, 声称覆盖 dt): 连续链恒 = 对跨;
        # 含缝对只计声称覆盖 —— 缝秒不进分母(「未覆盖秒不归因」, 旧面同判)
        cov_ms_pair = dur_ms - max(0, unobs_ms)
        hole = unobs_ms > _V4_SEAM_NULL_S * 1000
        broke = unobs_ms > 0 or marked
        if s.ts >= t0:
            # 组键(26-11-27 S1a F3): k=1 逐样本直通(键 = 窗内序号, 抖动不合并);
            # k>1 = 时间桶锚(单点 group_bucket)—— 组界与窗位置无关, 已闭合桶跨请求
            # 逐位不动(INV-3 对账零形状改写); n_win 计数保留(k=1 键)
            g = n_win if stride == 1 else group_bucket(s.ts, stride, si)
            e = accs.get(g)
            if e is None:
                e = accs[g] = [0, 0, 0, 0, broke, s.ts, o[2], o[3], None, None]
            else:
                e[4] = e[4] or broke  # 断链旗跨同组后继槽存活(不清成 0 线, 旧面同判)
                # 快照取 ts 最晚者(同刻后到者优先, 旧面同判): eps 带内回退槽(ts 非降守卫
                # 放行的 -eps 抖动)不回写组末 ts/快照
                if s.ts >= e[5]:
                    e[5] = s.ts
                    e[6] = o[2]
                    e[7] = o[3]
            # totals 面: 本样本相邻快照差分(对上一已消费观测槽 —— 含窗外种子基线, 漏采
            # 区间字节含在后继样本快照差分里)按端点归属本组; 重置/基线缺失贡献 0 不出洞
            # (group_totals_points 同口径); 链上 n 槽不更新基线, 跨缺口差分承袭完整
            td = _bucket_delta(o[2], prev_slot[1]) if prev_slot is not None else None
            tu = _bucket_delta(o[3], prev_slot[2]) if prev_slot is not None else None
            if td is not None:
                e[8] = td if e[8] is None else e[8] + td
            if tu is not None:
                e[9] = tu if e[9] is None else e[9] + tu
            n_win += 1
        else:
            g = None  # 窗外前缀: 只作差分基线, 不计组序号不产组点(窗首种子 D3)
        is_z = s.is_zero
        for d, cur, run in ((0, o[2], dl_run), (1, o[3], up_run)):
            # 差分对逐向处理(端点归属: delta 记本槽所在组); 等值游程入列需 z 形签名
            value, _, run_list, run_prefix = run
            if value is None or hole or cur < value:
                # 游程立点: 基线缺失 / 停机洞(> 停机洞阈值, 宁可丢弃不摊配)/ 计数器重置
                run[0], run[1], run[2], run[3] = cur, s.ts, [], 0
                delta = None
            elif cur == value:
                run_list.append((g, cov_ms_pair, is_z, s.ts))
                delta = 0
            else:
                step = cur - value
                span_ms = int(round((s.ts - run[1]) * 1000))
                cov_ms = run_prefix + sum(dd for _, dd, _, _ in run_list) + cov_ms_pair
                delta = _seam_spread_delta(
                    d, step, span_ms, cov_ms, dur_ms, s.dt_s, marked, run_list, run_prefix, bucket_add
                )
                run[0], run[1], run[2], run[3] = cur, s.ts, [], 0
            if delta is not None and cov_ms_pair > 0 and g is not None:
                # 速率面入组(端点归属): 覆盖时长为 0(同刻病理槽序)不归因不造分母
                if d == 0:
                    e[0] += delta
                    e[1] += cov_ms_pair
                else:
                    e[2] += delta
                    e[3] += cov_ms_pair
        prev_slot = (s.ts, o[2], o[3])
        marked = False  # 断连面随观测槽消费复位(旧面同判; 未消费槽不复位)
    # 发射: 组点(t = 组末样本 ts; k>1 = 桶末样本 ts)与空值点合并升序, 同刻空值点在前(旧 emit 同判, 稳定);
    # totals 随点同构发射(组 = 累加器快照差分和, 空值点 = None)。空值点与活尾组点相对次序由该
    # 合并序唯一确定: 尾随空值点(t 大于活尾组点 t)居末; 活尾组点 = 最高时间桶组点(进行中桶),
    # 其余真值点 = 脊柱点
    items: list = []
    for g in sorted(accs):
        e = accs[g]
        dl = int(round(e[0] * 1000 / e[1])) if e[1] > 0 else (None if e[4] else 0)
        up = int(round(e[2] * 1000 / e[3])) if e[3] > 0 else (None if e[4] else 0)
        items.append((e[5], 1, {"t": e[5], "dl": dl, "up": up}, {"t": e[5], "dl": e[8], "up": e[9]}))
    for t in emit_marks:
        items.append((t, 0, {"t": t, "dl": None, "up": None}, None))
    items.sort(key=lambda it: (it[0], it[1]))
    points: list = []
    totals: list = []
    for _t, _kind, p, tot in items:
        points.append(p)
        totals.append(tot)
    # tail_open(26-11-27 评审修复): 恒等价于「points[-1] 是活尾组点」(前端二分契约脊柱
    # points[:-1] + 活尾 points[-1]) —— k>1 且列非空且尾项为组点(kind 1; 同刻空值点在前
    # 的合并序保证 t 相等时组点居末)且其 t = 最高时间桶组点 t。不用 any(totals) 推导,
    # 两可达形态失配: (1)尾随空值点居末(totals 有真值 -> True, 实际尾点是空值点); (2)整窗
    # 重置/链首 totals 全 None -> False, 实际尾点是活尾组点(未标注变动点破坏 INV-3)。
    live_tail_t = accs[max(accs)][5] if accs else None
    tail_open = bool(
        stride > 1 and items and live_tail_t is not None and items[-1][0] == live_tail_t and items[-1][1] == 1
    )
    return GroupAssemblyResult(
        points=tuple(points),
        totals=tuple(totals),
        stride=stride,
        over_budget=over_budget,
        tail_open=tail_open,
    )


def assemble_group_points_from_blocks(blocks, t0: float, t1: float, sample_interval_s: float) -> GroupAssemblyResult:
    """块序列便捷入口: 聚合接缝平展(v4_series_slots 复用, 块按 start_epoch 稳定排序逐块
    v4_block_slots 展开)后走 assemble_group_points —— 调用面亦可自行经 v4_block_slots_from
    游标续展喂槽流(增量装配, 阶段 1 后续任务接入)。"""
    return assemble_group_points(v4_series_slots(tuple(blocks)), t0, t1, sample_interval_s)
