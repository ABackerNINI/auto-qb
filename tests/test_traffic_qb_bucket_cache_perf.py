"""test_traffic_qb_bucket_cache_perf 测试计划: A4 基准三面实测(计划 26-11-15-1104 §01 A4 /
§06 D5 / §07 R6, S2-2 交付面)—— 温态/冷态/组图 M=30, 端点级(QbTrafficChartApi)计时,
活跃 r 流与空闲 z 流双形态并列(取最劣口径报告)。

## 测试计划(每个测试函数一条)
- test_a4_bench_cold_and_warm_single_series_24h: 冷态 + 温态(全局/单种, 活跃形态)——
  24h 窗 @1.5s 采样全天活跃 r 流(最重冷算形态, 57600 槽), 冷态 = 全新缓存实例首拉
  (全量解析 + 全量折叠), 断言 < 1.5s(A4 一次性豁免线); 温态 = 假钟每拍 advance(2.0)
  (栅格随拍右移)+ 追加 1 条记录(增量折叠面), 60 拍 p95 断言 < 100ms(A4 判据本身)。
- test_a4_bench_idle_single_series_24h: 冷态 + 温态(单种, 空闲形态)—— 全天 z 游程流
  (游程项按槽入列/开放封口边界/闭合摊配发射的常态生产形态), 同线断言 + 游程项驻留
  量与单条目内存实测打印(评审轮1 #4 内存账)。
- test_a4_bench_group_m30_warm: 组图 M=30 活跃形态温态(成员史 2h/员, 活跃槽 4800 x 30
  = 144000 槽; 温态与史长无关)+ 冷态记录实测(豁免)—— T5 评审轮实测 ~400ms 未达 A4
  组图线, 根因 = V4DayCache 4MB 文本预算被 30 成员天文件挤出 LRU(每拍整天文件重解析);
  主会话拍板处置**选项 A**(26-11-16): V4_DAY_CACHE_BUDGET_BYTES 4MB -> 16MB, 复测
  温态 p95 = **11.15ms**(A4 线内)—— 断言钉 A4 判据本身(150ms)。
- test_a4_bench_group_m30_idle_warm: 组图 M=30 空闲形态温态 + 成员史 24h(游程项满窗
  驻留的最劣内存形态)—— 冷态记录实测, 游程项驻留总量与内存估算打印。A4 组图线
  150ms **未达**(实测 ~200-240ms), 主会话拍板**接受现状**(26-11-16 处置选项 F):
  形态 = 合成最劣(30 员全空闲 + 24h 全史同窗), 根因 = 纯空闲流永不封口 -> 全窗
  ~498 桶每请求走开放面重发射 + 游程表逐槽驻留的 fold.copy 整表拷贝(桶值缓存固有
  成本; 粗化/收缩保留窗改逐槽语义, 不采纳); 距 T5 前基线(全量现算 ~25.6s/请求)
  两个数量级。本用例按防回归 tripwire 线断言 —— **不是达标口径, 防后人误读**。

量法口径: time.perf_counter 包住端点调用(含 limits 附加与响应装配, 即端点全成本);
p95 = sorted[ceil(0.95*n)-1]; 假钟(FakeClock 实例)钉端点取时单点并逐拍 advance/freeze
真实推进(栅格随拍右移 —— 追加记录进增量折叠面, 非零增量纯命中); 轮询间向天文件真只
增追加 1 条(setup 期 writer 建好复用, 绝不重建空 writer 截断天文件)。单种两形态与
组图活跃的阈值断言 = A4 判据本身, 组图空闲 tripwire 线只防退化(拍板接受现状, 见上)
—— 合成流为 CPU 密集无真实网络/磁盘抖动; 实测数字以 pytest -s 输出为准誊写进计划
报告。writer 一律 interval_s=_SI
(块标称间隔须与栅格采样间隔同源: 缺省 2.0 时块首 z 游程按标称间隔摊槽, 读侧 dt 链
与写侧名义链漂移, 跨天块首游程与前天链尾倒挂会触发槽组时序守卫)。线程/时钟纪律:
假钟走 tests/clock.py 单点(monkeypatch tq.SYSTEM_CLOCK); 文件落 tmp_path(test.* 已
内置 TMPDIR, 不手工加前缀); 代码/断言零 emoji 零图形符号。
"""
import math
import sys
import time

from auto_qb.infra.utils_paths import encode_group_key
from auto_qb.webui.server.traffic_qb import QbTrafficChartApi

from clock import FakeClock

from test_traffic_grid_bucket_cache import _SeriesWriter

_SI = 1.5  # 生产采样间隔(main_tick 1.5s)
_DAY = 86_400.0
_MIDNIGHT = 1_800_000_000 + 86_400  # 仿真锚点(固定 epoch, 非真本地午夜 —— 时区依赖,
# 仅作数据起点; 数据面 24h 必跨真实本地午夜 -> 两天文件面, 守卫/多天覆盖照常生效)


def _gen_active(writer: _SeriesWriter, start: float, seconds: float, reopen_every: int = 120) -> float:
    """活跃 r 流(每 si 一条, 速率缓变)—— 最重冷算/折叠形态; 每 reopen_every 条关块
    重开(对齐写侧按 flush 关块的块分布形态)。返回末记录时刻。"""
    t = start
    n = 0
    end = start + seconds
    while t < end:
        writer.r(t, 50_000 + (n % 7) * 3000, 20_000 + (n % 5) * 2000)
        n += 1
        t += _SI
        if n % reopen_every == 0:
            writer.reopen()
    writer.write()
    return t


def _gen_idle(writer: _SeriesWriter, start: float, seconds: float) -> float:
    """空闲 z 游程流(每 30s 一枚 z 记录, 槽数按实跨计算)—— 游程项按槽入列/开放游程
    跨满窗的常态生产形态。末记录按剩余跨度收尾(不跨日界不倒挂)。返回末记录时刻。"""
    t = start
    end = start + seconds
    while t < end:
        t_next = min(t + 30.0, end)
        n = max(1, int(round((t_next - t) / _SI)))
        writer.z(t_next, n)
        t = t_next
    writer.write()
    return t


def _make_api(tmp_path, members=None):
    """端点装配桩(真 V4DayCache/桶值缓存/真天文件, 无 live tail 宿主)"""
    from types import SimpleNamespace

    groups = {}
    if members is not None:
        groups[("bench", ("a.mkv", ))] = list(members)
    mgr = SimpleNamespace(
        config=SimpleNamespace(
            data_dir=str(tmp_path),
            main_tick=_SI,
            qb_traffic=SimpleNamespace(enabled=True, sample_interval_multiplier=1),
        ),
        store=SimpleNamespace(groups=groups),
        host=None,
    )
    return QbTrafficChartApi(mgr)


def _pctl(samples, q):
    """分位数单点: sorted[ceil(q*n)-1](p95 口径, 与报告一致)"""
    xs = sorted(samples)
    return xs[max(0, math.ceil(q * len(xs)) - 1)]


def _patch_clock(monkeypatch, start):
    """端点取时单点换假钟(实例返回给用例, 逐拍 advance/freeze 真实推进)"""
    clk = FakeClock(start=float(start))
    import auto_qb.webui.server.traffic_qb as tq

    monkeypatch.setattr(tq, "SYSTEM_CLOCK", clk)
    return clk


def _run_entry_stats(api, key, window):
    """单条目驻留账(游程项数 x 单项实测字节 -> MB 估算; 评审轮1 #4 内存账)"""
    ent = api._bucketcache._entries.get((key, window))
    if ent is None:
        return "no-entry"
    n_run = len(ent.fold.dl_run[2]) + len(ent.fold.up_run[2])
    per_item = 0
    if ent.fold.dl_run[2]:
        s = ent.fold.dl_run[2][0]
        per_item = sys.getsizeof(s) + sum(sys.getsizeof(x) for x in s if not isinstance(x, bool))
    return (
        f"游程项={n_run}(x{per_item}B≈{n_run * per_item / 1e6:.1f}MB) "
        f"封口={len(ent.sealed_keys)} 开放cell={len(ent.fold.cells)}"
    )


def test_a4_bench_cold_and_warm_single_series_24h(tmp_path, monkeypatch):
    """A4 冷态(<1.5s 一次性)+ 温态 p95(<100ms): 24h 窗活跃流, 端点级实测"""
    key = "global"
    writer = _SeriesWriter(tmp_path, key, interval_s=_SI)  # 块标称间隔须与栅格采样间隔同源
    start = _MIDNIGHT - 3600.0
    t_end = _gen_active(writer, start, _DAY - 2 * _SI)
    api = _make_api(tmp_path)
    clk = _patch_clock(monkeypatch, t_end + 2.0)

    # 冷态: 全新缓存实例首拉(全量解析 + 全量折叠)—— A4 一次性豁免线 1.5s
    t0 = time.perf_counter()
    payload = api.payload_global("24h")
    cold = time.perf_counter() - t0
    assert len(payload["points"]) > 400  # 24h@174s 桶宽 = 497-498 桶(数据面非空态)
    assert cold < 1.5, f"冷态 {cold * 1000:.1f}ms 超 A4 一次性线 1500ms"

    # 温态: 假钟每拍 advance(2.0)(栅格右移)+ 追加 1 条(增量折叠面), 60 拍取 p95
    warm = []
    for _ in range(60):
        clk.advance(2.0)
        writer.r(clk.now() - 1.0, 60_000, 25_000)
        writer.write()
        t0 = time.perf_counter()
        api.payload_global("24h")
        warm.append(time.perf_counter() - t0)
    warm_p95 = _pctl(warm, 0.95)
    print(
        f"[A4 bench] 单种24h活跃 冷态={cold * 1000:.1f}ms(线1500) 温态p95={warm_p95 * 1000:.2f}ms(线100) "
        f"温态min={min(warm) * 1000:.2f} 中位={_pctl(warm, 0.5) * 1000:.2f} max={max(warm) * 1000:.2f}ms"
    )
    assert warm_p95 < 0.1, f"温态 p95 {warm_p95 * 1000:.2f}ms 超 A4 线 100ms"


def test_a4_bench_idle_single_series_24h(tmp_path, monkeypatch):
    """A4 单种空闲形态(全天 z 游程): 冷态 + 温态 p95 + 游程项驻留内存账"""
    key = "global"
    writer = _SeriesWriter(tmp_path, key, interval_s=_SI)  # 块标称间隔须与栅格采样间隔同源
    start = _MIDNIGHT - 3600.0
    t_end = _gen_idle(writer, start, _DAY - 2 * _SI)
    api = _make_api(tmp_path)
    clk = _patch_clock(monkeypatch, t_end + 2.0)

    t0 = time.perf_counter()
    payload = api.payload_global("24h")
    cold = time.perf_counter() - t0
    assert len(payload["points"]) > 400
    assert cold < 1.5, f"冷态 {cold * 1000:.1f}ms 超 A4 一次性线 1500ms"

    warm = []
    for _ in range(60):
        clk.advance(2.0)
        writer.z(clk.now() - 1.0, 1)
        writer.write()
        t0 = time.perf_counter()
        api.payload_global("24h")
        warm.append(time.perf_counter() - t0)
    warm_p95 = _pctl(warm, 0.95)
    print(
        f"[A4 bench] 单种24h空闲 冷态={cold * 1000:.1f}ms(线1500) 温态p95={warm_p95 * 1000:.2f}ms(线100) "
        f"温态min={min(warm) * 1000:.2f} 中位={_pctl(warm, 0.5) * 1000:.2f} max={max(warm) * 1000:.2f}ms; "
        f"{_run_entry_stats(api, key, '24h')}"
    )
    assert warm_p95 < 0.1, f"空闲温态 p95 {warm_p95 * 1000:.2f}ms 超 A4 线 100ms"


def test_a4_bench_group_m30_warm(tmp_path, monkeypatch):
    """A4 组图 M=30 温态 p95(<150ms 硬线, 活跃形态)+ 冷态记录实测(豁免)"""
    members = [f"{i:032x}" for i in range(30)]
    writers = {}
    t_end = None
    for h in members:
        w = _SeriesWriter(tmp_path, "torrent:" + h, interval_s=_SI)  # 块标称间隔须与栅格采样间隔同源
        t_end = _gen_active(w, _MIDNIGHT - 7200.0, 7200.0 - 2 * _SI)
        writers[h] = w
    api = _make_api(tmp_path, members=members)
    key_text = encode_group_key(("bench", ("a.mkv", )))
    clk = _patch_clock(monkeypatch, t_end + 2.0)

    # 组图冷态(豁免, 记录实测; 成员史 2h/员)
    t0 = time.perf_counter()
    payload = api.payload_group(key_text, "24h")
    group_cold = time.perf_counter() - t0
    assert len(payload["points"]) > 400

    # 组图温态: 假钟每拍 advance + 30 成员各真只增追加 1 条(setup 期 writer 复用)
    warm = []
    for _ in range(40):
        clk.advance(2.0)
        for h in members:
            writers[h].r(clk.now() - 1.0, 60_000, 25_000)
            writers[h].write()
        t0 = time.perf_counter()
        api.payload_group(key_text, "24h")
        warm.append(time.perf_counter() - t0)
    warm_p95 = _pctl(warm, 0.95)
    print(
        f"[A4 bench] 组图M=30活跃 冷态(2h/员史)={group_cold * 1000:.1f}ms(记录, 豁免) "
        f"温态p95={warm_p95 * 1000:.2f}ms(线150) 温态min={min(warm) * 1000:.2f} "
        f"中位={_pctl(warm, 0.5) * 1000:.2f} max={max(warm) * 1000:.2f}ms"
    )
    # A4 组图线恢复达标(选项 A 拍板 26-11-16: 天缓存预算 4MB -> 16MB, 整组驻留全命中;
    # 曾实测 ~400ms -> 复测 p95 11.15ms)—— 断言钉 A4 判据本身
    assert warm_p95 < 0.15, f"组图温态 p95 {warm_p95 * 1000:.2f}ms 超 A4 线 150ms"


def test_a4_bench_group_m30_idle_warm(tmp_path, monkeypatch):
    """A4 组图 M=30 空闲形态温态(同硬线)+ 24h/员史游程项满窗驻留的内存账(最劣形态)"""
    members = [f"{i:032x}" for i in range(30)]
    writers = {}
    t_end = None
    for h in members:
        w = _SeriesWriter(tmp_path, "torrent:" + h, interval_s=_SI)  # 块标称间隔须与栅格采样间隔同源
        t_end = _gen_idle(w, _MIDNIGHT - 3600.0, _DAY - 2 * _SI)
        writers[h] = w
    api = _make_api(tmp_path, members=members)
    key_text = encode_group_key(("bench", ("a.mkv", )))
    clk = _patch_clock(monkeypatch, t_end + 2.0)

    t0 = time.perf_counter()
    payload = api.payload_group(key_text, "24h")
    group_cold = time.perf_counter() - t0
    assert len(payload["points"]) > 400

    warm = []
    for _ in range(40):
        clk.advance(2.0)
        for h in members:
            writers[h].z(clk.now() - 1.0, 1)
            writers[h].write()
        t0 = time.perf_counter()
        api.payload_group(key_text, "24h")
        warm.append(time.perf_counter() - t0)
    warm_p95 = _pctl(warm, 0.95)
    print(
        f"[A4 bench] 组图M=30空闲 冷态(24h/员史)={group_cold * 1000:.1f}ms(记录, 豁免) "
        f"温态p95={warm_p95 * 1000:.2f}ms(线150) 温态min={min(warm) * 1000:.2f} "
        f"中位={_pctl(warm, 0.5) * 1000:.2f} max={max(warm) * 1000:.2f}ms; "
        f"成员条目[{_run_entry_stats(api, 'torrent:' + members[0], '24h')}] (其余 29 员同量级 -> 组图驻留 x30)"
    )
    # tripwire 线(隔离实测 ~200-240ms; 并行 worker CPU 争用下 p95 实测 ~400ms —— 线取 600ms
    # = 隔离实测 x2.75 含并行负载因子, 对 25.6s 基线仍有 42x 判别力): A4 组图线 150ms 未达,
    # 主会话拍板接受现状(选项 F, 26-11-16): 合成最劣形态(30 员全空闲 + 24h 全史同窗),
    # 根因 = 纯空闲流永不封口 -> 全窗开放面重发射(桶值缓存固有成本), 距 T5 前基线 ~25.6s
    # 两个数量级 —— 此线只防退化, 不是达标口径, 防后人误读
    assert warm_p95 < 0.6, f"组图空闲温态 p95 {warm_p95 * 1000:.2f}ms 超 tripwire 线 600ms(拍板接受, 非达标)"
